import json
import paho.mqtt.client as mqtt
from datetime import datetime, timedelta
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
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
    print("Unique timestamps in SOC data:", df_soc_resampled['timestamp'].unique())

    # Load and resample Grid data to 15-minute intervals
    df_grid = pd.read_sql_query("SELECT timestamp, grid_data FROM grid_data", conn)
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"])
    df_grid_resampled = df_grid.set_index("timestamp").resample("15T").mean().reset_index()
    print("Grid data headers:", df_grid_resampled.columns.tolist())
    print(df_grid_resampled.head())
    print("Unique timestamps in Grid data:", df_grid_resampled['timestamp'].unique())

    # Round the timestamps to the nearest 15 minutes in all DataFrames
    df_soc_resampled['timestamp'] = df_soc_resampled['timestamp'].dt.round('15T')
    print("SOC data after rounding timestamps:")
    print(df_soc_resampled.head())

    df_grid_resampled['timestamp'] = df_grid_resampled['timestamp'].dt.round('15T')
    print("Grid data after rounding timestamps:")
    print(df_grid_resampled.head())


    # Merge the DataFrames
    df_merged = pd.merge(df_soc_resampled, df_grid_resampled, on="timestamp", how="outer")
    df_merged.ffill(inplace=True)  # Forward fill to handle NaNs

    print("Merged DataFrame with SOC, Grid, and Cost data:")
    print(df_merged.head())
        # Add these columns to the merged DataFrame
    df_merged['minute_of_day'] = df_merged['timestamp'].dt.minute + df_merged['timestamp'].dt.hour * 60
    df_merged['hour_of_day'] = df_merged['timestamp'].dt.hour
    df_merged['day_of_week'] = df_merged['timestamp'].dt.dayofweek

    print("Merged DataFrame with added columns for model training:")
    print(df_merged.head())
        


    return df_merged



def train_model(df):
    print("Starting model training...")

    # Include 'Cost' in the features
    features = ["minute_of_day", "hour_of_day", "day_of_week", "Cost", "grid_data"]
    
    # Check if 'Cost' is in the DataFrame and handle if it's not
    if 'Cost' not in df.columns:
        df['Cost'] = 0  # You might want to handle this differently based on your data
    
    X = df[features]
    y = df["soc"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print("Model evaluation - Mean Squared Error: ", mse)

    return model


def predict_soc_for_day(start_date, end_date, df_rates_expanded):
    print("predict_soc_for_day called with start_date:", start_date, "end_date:", end_date)
    df = get_soc_data2()

    # Merge the rates data
    df = pd.merge(df, df_rates_expanded, on="timestamp", how="outer")
    df.ffill(inplace=True)  # Forward fill to handle NaNs

    # Add the 'Cost' feature only if it's missing
    if 'Cost' not in df.columns:
        df['Cost'] = 0

    model = train_model(df)

    # Convert start and end dates to datetime objects
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    print(f"Start timestamp: {start_timestamp}, End timestamp: {end_timestamp}")

    predictions = {}
    actions = {}
    min_soc_threshold = 10  # Minimum SOC to prevent full discharge
    charge_cost_threshold = 20.00  # Cost threshold for charging

    current_time = start_timestamp
    while current_time < end_timestamp:
        print(f"Processing for timestamp: {current_time}")
        matching_data = df[df["timestamp"] == pd.Timestamp(current_time)]

        if not matching_data.empty:
            row = matching_data.iloc[0]
            print(f"Matching data found for timestamp {current_time}: {row}")
            
            # Get the cost for the current timestamp from df_rates
            rate_matching = df_rates_expanded[(df_rates_expanded['timestamp'] >= current_time) & (df_rates_expanded['timestamp'] < current_time + timedelta(minutes=15))]
            if rate_matching.empty:
                print(f"No rate data found for timestamp {current_time}")
                current_rate = None
            else:
                current_rate = rate_matching['Cost'].iloc[0]
                print(f"Current rate for timestamp {current_time}: {current_rate}")

            features = {
                "minute_of_day": current_time.minute + current_time.hour * 60,
                "hour_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "Cost": current_rate,
                "grid_data": row["grid_data"],
            }

            target_data = pd.DataFrame([features])
            predicted_soc = model.predict(target_data)[0]
            predicted_soc = max(10, min(predicted_soc, 100))  # Ensuring SOC is within bounds
            predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = predicted_soc
            print(f"Predicted SOC for {current_time}: {predicted_soc}")

            # Decision logic for charging, discharging, or holding
            if predicted_soc < min_soc_threshold or (predicted_soc < 100 and current_rate < charge_cost_threshold):
                action = 'Charge'
            elif predicted_soc > min_soc_threshold and current_rate >= charge_cost_threshold:
                action = 'Discharge'
            else:
                action = 'Hold'
            print(f"Action for {current_time}: {action}")

            actions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = action

        else:
            print(f"No matching data for timestamp {current_time}")

        current_time += timedelta(minutes=15)

    return predictions, actions




def on_connect(client, userdata, flags, rc):
    print("FROM PREDICT Connected with result code " + str(rc))
    client.subscribe("battery_soc/request")


def on_message(client, userdata, msg):
    request_data = json.loads(msg.payload)
    start_date = request_data.get("start_date")
    end_date = request_data.get("end_date")
    if start_date and end_date:
        conn = sqlite3.connect(DATABASE_FILENAME)
        df_rates = pd.read_sql_query("SELECT * FROM rates_data", conn)
        df_rates["Date"] = pd.to_datetime(df_rates["Date"], format="%d-%m-%Y")
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

        predictions, actions = predict_soc_for_day(start_date, end_date, df_rates_expanded)
        client.publish("battery_soc/response", json.dumps({"predictions": predictions, "actions": actions}))

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