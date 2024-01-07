import json
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_squared_error

# Constants
DATABASE_FILENAME = "/config/soc_database.db"

# Functions to load data from the database
def get_soc_data():
    print("Loading SOC data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_soc = pd.read_sql_query("SELECT * FROM soc_data", conn)
    df_soc["timestamp"] = pd.to_datetime(df_soc["timestamp"])
    df_soc_resampled = df_soc.set_index("timestamp").resample("15T").ffill().bfill().reset_index()
    print("SOC data headers:", df_soc_resampled.columns.tolist())
    print(df_soc_resampled.head(4))
    return df_soc_resampled

def get_grid_data():
    print("Loading Grid data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_grid = pd.read_sql_query("SELECT timestamp, grid_data FROM grid_data", conn)
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"])
    df_grid_resampled = df_grid.set_index("timestamp").resample("15T").mean().reset_index()
    print("Grid data headers:", df_grid_resampled.columns.tolist())
    print(df_grid_resampled.head(4))
    return df_grid_resampled

def get_solar_data(start_date, end_date):
    print("Loading Solar data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_solar = pd.read_sql_query("SELECT * FROM solar", conn)
    df_solar["datetime"] = pd.to_datetime(df_solar["datetime"])
    
    # Filter the data for the specified date range
    df_solar = df_solar[(df_solar['datetime'] >= start_date) & (df_solar['datetime'] <= end_date)]
    
    df_solar_resampled = df_solar.set_index("datetime").resample("15T").mean().reset_index()
    df_solar_resampled['pv_estimate'] = df_solar_resampled['pv_estimate'].fillna(0).div(2)
    df_solar_resampled = df_solar_resampled.rename(columns={"datetime": "timestamp"})
    print("Solar data headers:", df_solar_resampled.columns.tolist())
    print(df_solar_resampled.head(4))
    return df_solar_resampled

def get_rates_data(start_date, end_date):
    print("Loading rates data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)

    df_rates = pd.read_sql_query("SELECT * FROM rates_data", conn)
    df_rates["Date"] = pd.to_datetime(df_rates["Date"], format="%d-%m-%Y")

    # Filter the data for the specified date range
    df_rates = df_rates[(df_rates['Date'] >= start_date) & (df_rates['Date'] <= end_date)]

    df_rates["StartTime"] = pd.to_datetime(df_rates["StartTime"]).dt.time
    df_rates["EndTime"] = pd.to_datetime(df_rates["EndTime"]).dt.time
    df_rates["Cost"] = pd.to_numeric(df_rates["Cost"].str.rstrip("p"), errors='coerce')

    expanded_rates = []
    for _, row in df_rates.iterrows():
        start_time = datetime.combine(row["Date"], row["StartTime"])
        end_time = datetime.combine(row["Date"], row["EndTime"])
        while start_time < end_time:
            expanded_rates.append({"timestamp": start_time, "Cost": row["Cost"]})
            start_time += timedelta(minutes=15)
    
    df_rates_expanded = pd.DataFrame(expanded_rates)
    print(df_rates_expanded.head(4))
    return df_rates_expanded


def train_model(df):
    print("Starting model training...")
    features = ["minute_of_day", "hour_of_day", "day_of_week", "Cost", "grid_data", "pv_estimate"]
    X = df[features]
    y = df["soc"]

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=60)
    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print("Model evaluation - Mean Squared Error:", mse)
    return model


def predict_soc_for_day(start_date, end_date, model, df_soc, df_grid):
    print("Predicting SOC for the day...")
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    # Fetch solar and rates data for the specified date range
    df_solar = get_solar_data(start_date, end_date)
    df_rates = get_rates_data(start_date, end_date)

    # Merge all data
    df_merged = pd.merge(df_soc, df_grid, on="timestamp", how="outer")
    df_merged = pd.merge(df_merged, df_solar, on="timestamp", how="outer")
    df_merged = pd.merge(df_merged, df_rates, on="timestamp", how="outer")
    df_merged.ffill(inplace=True)  # Forward fill to handle NaNs
    print("Headers after final merge with Rates data:", df_merged.head(4))

    predictions = {}
    current_time = start_timestamp
    while current_time < end_timestamp:
        matching_rows = df_merged[df_merged["timestamp"] == current_time]
        if not matching_rows.empty:
            row = matching_rows.iloc[0]
            features = {
                "minute_of_day": current_time.minute + current_time.hour * 60,
                "hour_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "Cost": row.get("Cost", 0),
                "grid_data": row.get("grid_data", 0),
                "pv_estimate": row.get("pv_estimate", 0)
            }
            predicted_soc = model.predict(pd.DataFrame([features]))[0]
            predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = max(0, min(predicted_soc, 100))
        else:
            print(f"No data for timestamp: {current_time}")
            predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = None
        current_time += timedelta(minutes=15)

    return predictions

# MQTT Client Functions

def get_mqtt_config():
    config_path = '/data/options.json'
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config['mqtt_host'], int(config['mqtt_port']), config['mqtt_user'], config['mqtt_password']
    except Exception as e:
        print(f"Error reading MQTT configuration: {e}")
        # Default values if the configuration file is not found or there's an error
        return '192.168.1.135', 1883, 'default_user', 'default_password'


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("battery_soc/request")

def on_message(client, userdata, msg):
    request_data = json.loads(msg.payload)
    start_date = request_data.get("start_date")
    end_date = request_data.get("end_date")
    if start_date and end_date:
        # Fetch data
        df_soc = get_soc_data()
        df_grid = get_grid_data()
        df_solar = get_solar_data(start_date, end_date)  # Now accepts start and end date
        df_rates = get_rates_data(start_date, end_date)  # Now accepts start and end date

        # Train the model with the merged data
        df_merged = pd.merge(df_soc, df_grid, on="timestamp", how="outer")
        df_merged = pd.merge(df_merged, df_solar, on="timestamp", how="outer")
        df_merged = pd.merge(df_merged, df_rates, on="timestamp", how="outer")
        df_merged.ffill(inplace=True)  # Forward fill to handle NaNs
        model = train_model(df_merged)

        # Predict SOC for the specified date range
        predictions = predict_soc_for_day(start_date, end_date, model, df_soc, df_grid)
        client.publish("battery_soc/response", json.dumps({"predictions": predictions}))

def on_disconnect(client, userdata, rc):
    print("Disconnected with result code " + str(rc))

def on_log(client, userdata, level, buf):
    print("Log:", buf)

# MQTT Configuration and Client Setup
mqtt_host, mqtt_port, mqtt_user, mqtt_password = get_mqtt_config()
client = mqtt.Client()
client.username_pw_set(mqtt_user, password=mqtt_password)
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log = on_log

try:
    client.connect(mqtt_host, mqtt_port, 60)
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    exit(1)

client.loop_forever()
