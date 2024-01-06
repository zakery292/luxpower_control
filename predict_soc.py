import json
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.experimental import enable_hist_gradient_boosting  # noqa
from sklearn.ensemble import HistGradientBoostingRegressor
import numpy as np
from dateutil import parser
from sklearn.metrics import mean_squared_error


DATABASE_FILENAME = "/config/soc_database.db"


def get_soc_data2():
    print("FROM PREDICT Loading data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)

    # Load and resample SOC data to 15-minute intervals
    df_soc = pd.read_sql_query("SELECT * FROM soc_data", conn)
    df_soc["timestamp"] = pd.to_datetime(df_soc["timestamp"])
    df_soc_resampled = df_soc.set_index("timestamp").resample("15T").mean().reset_index()
    print("SOC data headers:", df_soc_resampled.columns.tolist())
    print(df_soc_resampled.head())

    # Load and resample Grid data to 15-minute intervals
    df_grid = pd.read_sql_query("SELECT timestamp, grid_data FROM grid_data", conn)
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"])
    df_grid_resampled = df_grid.set_index("timestamp").resample("15T").mean().reset_index()
    print("Grid data headers:", df_grid_resampled.columns.tolist())
    print(df_grid_resampled.head())

    # Load and process Rates data
    df_rates = pd.read_sql_query("SELECT * FROM rates_data", conn)
    df_rates["Date"] = pd.to_datetime(df_rates["Date"], format="%d-%m-%Y")
    df_rates["StartTime"] = pd.to_datetime(df_rates["StartTime"]).dt.time
    df_rates["EndTime"] = pd.to_datetime(df_rates["EndTime"]).dt.time
    df_rates["Cost"] = pd.to_numeric(df_rates["Cost"].str.rstrip("p"), errors='coerce')
    print("Rates data headers:", df_rates.columns.tolist())
    print(df_rates.head())

    # Expand Rates data to 15-minute intervals
    expanded_rates = []
    for _, row in df_rates.iterrows():
        start_time = datetime.combine(row["Date"], row["StartTime"])
        end_time = datetime.combine(row["Date"], row["EndTime"])
        while start_time < end_time:
            expanded_rates.append({"timestamp": start_time, "Cost": row["Cost"]})
            start_time += timedelta(minutes=15)
    df_rates_expanded = pd.DataFrame(expanded_rates)
    print("Expanded Rates data headers:", df_rates_expanded.columns.tolist())
    print(df_rates_expanded.head())
    # Ensure that the timestamps are rounded to the nearest 15 minutes for all dataframes
    df_soc_resampled['timestamp'] = df_soc_resampled['timestamp'].dt.round('15T')
    df_grid_resampled['timestamp'] = df_grid_resampled['timestamp'].dt.round('15T')
    df_rates_expanded['timestamp'] = df_rates_expanded['timestamp'].dt.round('15T')

    # Merge SOC, Grid, and Expanded Rates data
    df_merged = pd.merge(df_soc_resampled, df_grid_resampled, on="timestamp", how="outer")
    df_merged = pd.merge(df_merged, df_rates_expanded, on="timestamp", how="outer")

    # Forward fill to handle NaNs
    df_merged.ffill(inplace=True)
    
    
    print("Merged data headers:", df_merged.columns.tolist())
    print(df_merged.head())

    return df_merged



def train_model(df):
    print("Starting model training...")
    features = ["minute_of_day", "hour_of_day", "day_of_week", "Cost", "grid_data"]
    X = df[features]
    y = df["soc"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    # Evaluate the model
    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print("Model evaluation - Mean Squared Error: ", mse)

    return model


def predict_soc_for_day(start_date, end_date):
    print("predict_soc_for_day called with start_date:", start_date, "end_date:", end_date)
    df = get_soc_data2()
    model = train_model(df)

    # Define the night cost threshold
    night_cost_threshold = 20.00  # Example value, adjust as needed
    min_soc_threshold = 10  # Minimum SOC to prevent full discharge

    # Convert start and end dates to datetime objects
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    predictions = {}
    current_time = start_timestamp
    while current_time < end_timestamp:
        matching_data = df[df["timestamp"] == pd.Timestamp(current_time)]

        if not matching_data.empty:
            row = matching_data.iloc[0]
            features = {
                "minute_of_day": current_time.minute + current_time.hour * 60,
                "hour_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "Cost": row["Cost"],
                "grid_data": row["grid_data"],
            }

            target_data = pd.DataFrame([features])
            predicted_soc = model.predict(target_data)[0]
            predicted_soc = max(10, min(predicted_soc, 100))  # Ensuring SOC is within bounds

            predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = predicted_soc

        current_time += timedelta(minutes=15)

    actions = {}
    for timestamp_str, predicted_soc in predictions.items():
        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        cost = df.loc[df['timestamp'] == pd.Timestamp(timestamp), 'Cost'].item()

        if predicted_soc < min_soc_threshold:
            action = 'Charge'
        elif cost < night_cost_threshold:
            action = 'Charge'
        else:
            action = 'Hold'

        actions[timestamp_str] = action

    return predictions, actions



def on_connect(client, userdata, flags, rc):
    print("FROM PREDICT Connected with result code " + str(rc))
    client.subscribe("battery_soc/request")


def on_message(client, userdata, msg):
    request_data = json.loads(msg.payload)
    start_date = request_data.get("start_date")
    end_date = request_data.get("end_date")
    if start_date and end_date:
        predictions = predict_soc_for_day(start_date, end_date)
        client.publish("battery_soc/response", json.dumps(predictions))
def on_disconnect(client, userdata, rc):
    print("FROM PREDICT Disconnected with result code " + str(rc))


def on_log(client, userdata, level, buf):
    print("FROM PREDICT Log: ", buf)

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

# Get MQTT configuration
mqtt_host, mqtt_port, mqtt_user, mqtt_password = get_mqtt_config()

# Set up MQTT client
client = mqtt.Client()
client.username_pw_set(mqtt_user, password=mqtt_password)  # Set username and password
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log = on_log
print(f'SOC PREDICT  Connecting to MQTT Broker at {mqtt_host}:{mqtt_port} with username {mqtt_user}')
print('This is from predict_soc.py')

# Connect to MQTT broker
try:
    client.connect(mqtt_host, mqtt_port, 60)  # Use variables for host and port
except Exception as e:
    print(f"SOC PREDICT Failed to connect to MQTT broker: {e}")
    exit(1)

# Start the loop
client.loop_forever()