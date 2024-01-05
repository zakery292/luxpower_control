# File: predict_soc_for_day_mqtt.py

import json
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.pipeline import make_pipeline
import numpy as np
import os

DATABASE_FILENAME = "soc_database.db"


def get_soc_data2():
    print("Loading data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)

    # Load SOC data and resample to 30-minute intervals
    df_soc = pd.read_sql_query("SELECT * FROM soc_data", conn)
    df_soc["timestamp"] = pd.to_datetime(df_soc["timestamp"], format="mixed")
    df_soc["minute_of_day"] = df_soc[
        "timestamp"
    ].dt.minute  # Create minute_of_day column
    df_soc["hour_of_day"] = df_soc["timestamp"].dt.hour  # Create hour_of_day column
    df_soc["day_of_week"] = df_soc["timestamp"].dt.dayofweek
    df_soc.ffill(inplace=True)  # Create day_of_week column
    df_soc_resampled = (
        df_soc.set_index("timestamp").resample("30T").mean().reset_index()
    )
    print("SOC data loaded and resampled.")
    print(df_soc_resampled.head())
    # Load Grid data and resample to 30-minute intervals
    df_grid = pd.read_sql_query("SELECT timestamp, grid_data FROM grid_data", conn)
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"], format="mixed")

    # Ensure grid_data is numeric
    df_grid["grid_data"] = pd.to_numeric(df_grid["grid_data"], errors="coerce")
    df_soc.ffill(inplace=True)
    df_grid_resampled = (
        df_grid.set_index("timestamp").resample("30T").mean().reset_index()
    )
    print("Grid data loaded and resampled.")
    print(df_grid_resampled.head())
    # Load Rates data
    df_rates = pd.read_sql_query("SELECT * FROM rates_data", conn)
    df_rates["Date"] = pd.to_datetime(df_rates["Date"], format="%d-%m-%Y")
    df_rates["StartTime"] = pd.to_datetime(
        df_rates["StartTime"], format="%H:%M:%S"
    ).dt.time
    df_rates["EndTime"] = pd.to_datetime(df_rates["EndTime"], format="%H:%M:%S").dt.time
    df_rates["Cost"] = df_rates["Cost"].str.rstrip("p").astype(float)
    print("Rates data loaded.")
    print(df_rates.head())
    # Merge SOC and Grid data
    df_merged = pd.merge(
        df_soc_resampled, df_grid_resampled, on="timestamp", how="outer"
    )
    print("SOC and Grid data merged.")
    print(df_merged.head())

    # Function to find the matching rate for each timestamp
    def get_rate_for_timestamp(row):
        rate_row = df_rates[
            (df_rates["StartTime"] <= row["timestamp"].time())
            & (df_rates["EndTime"] > row["timestamp"].time())
        ]
        return rate_row["Cost"].iloc[0] if not rate_row.empty else np.nan

    # Apply the function to get rates
    df_merged["Cost"] = df_merged.apply(get_rate_for_timestamp, axis=1)
    print("Merged SOC, Grid, and Rates data.")
    print(df_merged.head())

    # Add minute_of_day, hour_of_day, and day_of_week columns
    df_merged["minute_of_day"] = df_merged["timestamp"].dt.minute
    df_merged["hour_of_day"] = df_merged["timestamp"].dt.hour
    df_merged["day_of_week"] = df_merged["timestamp"].dt.dayofweek

    # Handle missing values using forward fill
    df_merged.ffill(inplace=True)
    print("NaN values handled.")

    return df_merged


def train_model(df):
    print("Starting model training...")
    features = ["minute_of_day", "hour_of_day", "day_of_week", "Cost", "grid_data"]
    X = df[features]
    y = df["soc"]

    # Impute missing values with mean
    imputer = SimpleImputer(strategy="mean")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=65
    )

    # Create a pipeline with imputer and model
    model = make_pipeline(
        imputer, RandomForestRegressor(n_estimators=200, random_state=42)
    )
    model.fit(X_train, y_train)
    return model


def predict_soc_for_day(target_date):
    print("predict_soc_for_day called with target_date:", target_date)
    df = get_soc_data2()
    print("Data fetched from get_soc_data2")
    model = train_model(df)
    print("Model trained")

    # Get rates data for the target date
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_rates = pd.read_sql_query(
        f"SELECT * FROM rates_data WHERE Date = '{target_date}'", conn
    )
    df_rates["Cost"] = df_rates["Cost"].str.rstrip("p").astype(float)

    # Get grid data for the target date
    df_grid = pd.read_sql_query(
        f"SELECT timestamp, grid_data FROM grid_data WHERE Date(timestamp) = '{target_date}'",
        conn,
    )
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"], format="mixed")

    start_time = datetime.strptime(target_date, "%Y-%m-%d")
    end_time = start_time + timedelta(days=1)

    predictions = {}
    current_time = start_time
    while current_time < end_time:
        target_minute = current_time.minute
        target_hour = current_time.hour
        target_day_of_week = current_time.weekday()

        # Find the corresponding cost data for the current time
        matching_rate = df_rates[
            (df_rates["StartTime"] <= current_time.time())
            & (df_rates["EndTime"] > current_time.time())
        ]
        if not matching_rate.empty:
            cost = matching_rate.iloc[0]["Cost"]
        else:
            cost = 0  # Default value if no matching rate is found

        # Find the corresponding grid data for the current time
        matching_grid = df_grid[df_grid["timestamp"] == current_time]
        grid_data = matching_grid["grid_data"].iloc[0] if not matching_grid.empty else 0

        # Construct the prediction input with all features
        target_data = pd.DataFrame(
            {
                "minute_of_day": [target_minute],
                "hour_of_day": [target_hour],
                "day_of_week": [target_day_of_week],
                "Cost": [cost],
                "grid_data": [grid_data],
            }
        )
        print("Predicting for timestamp:", current_time)
        predicted_soc = model.predict(target_data)[0]
        print("Prediction:", predicted_soc)
        # Ensure SOC stays within 10-100% range
        predicted_soc = max(10, min(predicted_soc, 100))
        timestamp = current_time.strftime("%Y-%m-%d %H:%M:%S")
        predictions[timestamp] = {"date": timestamp, "soc": predicted_soc}

        current_time += timedelta(minutes=15)

    return predictions


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("battery_soc/request")


def on_message(client, userdata, msg):
    request_data = json.loads(msg.payload)
    target_date = request_data.get("target_date")
    if target_date:
        predictions = predict_soc_for_day(target_date)
        client.publish("battery_soc/response", json.dumps(predictions))


client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
# Set MQTT username and password (replace with your credentials)
mqtt_username = os.getenv('MQTT_USER', 'default_user')
mqtt_password = os.getenv('MQTT_PASSWORD', 'default_password')
mqtt_host = os.getenv('MQTT_HOST', '192.168.1.135')
mqtt_port = int(os.getenv('MQTT_PORT', 1883))

client.username_pw_set(mqtt_username, password=mqtt_password)
client.connect(mqtt_host, mqtt_port, 60)
client.loop_forever()
