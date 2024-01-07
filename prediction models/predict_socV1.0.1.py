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

# Constants
BATTERY_CAPACITY_KWH = 19.2  # Battery capacity in kWh
CHARGE_DISCHARGE_RATE_W = 3800  
MAX_CHARGE_RATE = CHARGE_DISCHARGE_RATE_W / 1000  # Charge rate in kW
MAX_DISCHARGE_RATE = CHARGE_DISCHARGE_RATE_W / 1000  # Discharge rate in kW
DATABASE_FILENAME = "/config/soc_database.db"
MIN_CHARGE_SOC = 20  # Minimum SOC to start charging
MAX_DISCHARGE_SOC = 80  # Maximum SOC to start discharging
CHARGE_COST_THRESHOLD = 20


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
        X, y, test_size=0.2, random_state=60
    )

    model = HistGradientBoostingRegressor(random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    print("Model evaluation - Mean Squared Error: ", mse)

    return model

def get_solar_data():
    print("Loading solar data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_solar = pd.read_sql_query("SELECT * FROM solar", conn)

    # Convert 'datetime' to a pandas datetime object
    df_solar["datetime"] = pd.to_datetime(df_solar["datetime"])

    # Ensure that 'pv_estimate' is numeric
    df_solar["pv_estimate"] = pd.to_numeric(df_solar["pv_estimate"], errors='coerce')

    # Set 'datetime' as the index and resample
    df_solar_resampled = df_solar.set_index("datetime").resample("15T").mean().reset_index()

    # Round the timestamps to the nearest 15 minutes
    df_solar_resampled['timestamp'] = df_solar_resampled['datetime'].dt.round('15T')

    return df_solar_resampled




def predict_soc_for_day(start_date, end_date, df_rates_expanded):
    print("predict_soc_for_day called with start_date:", start_date, "end_date:", end_date)
    
    # Fetch data from database and prepare it for processing
    df = get_soc_data2()
    df_solar_resampled = get_solar_data()
    df_merged = pd.merge(df, df_rates_expanded, on="timestamp", how="outer")
    df_merged = pd.merge(df_merged, df_solar_resampled, on="timestamp", how="outer")
    df_merged.ffill(inplace=True)

    model = train_model(df_merged)

    # Initialize variables for predictions and actions
    predictions = {}
    actions = {}
    total_charge_cost_pence = 0.0

    # Iterate through each time period
    current_time = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")
    while current_time < end_timestamp:
        matching_data = df_merged[df_merged["timestamp"] == pd.Timestamp(current_time)]

        if not matching_data.empty:
            row = matching_data.iloc[0]

            # Get current SOC from the database
            current_soc = row["soc"]

            # Extract necessary data for decision making
            solar_generation = row.get("pv_estimate", 0) / 2  # Solar data in kWh for 15 minutes
            net_grid_usage = row["grid_data"] - solar_generation  # Net grid usage in kWh
            current_rate = row.get("Cost", 0)

            # Predict SOC using the model
            features = {
                "minute_of_day": current_time.minute + current_time.hour * 60,
                "hour_of_day": current_time.hour,
                "day_of_week": current_time.weekday(),
                "Cost": current_rate,
                "grid_data": net_grid_usage,
            }
            predicted_soc = model.predict(pd.DataFrame([features]))[0]
            predicted_soc = max(10, min(predicted_soc, 100))  # Ensure SOC is within valid range

            # Decision logic for battery management
            if solar_generation > 0 and current_soc < MAX_DISCHARGE_SOC:
                action = 'Charge with Solar'
            elif solar_generation > 0 and net_grid_usage > 0 and current_soc > MIN_CHARGE_SOC:
                action = 'Discharge with Solar'
            elif solar_generation > 0 and current_soc == 100:
                action = 'Export Solar'
            elif current_soc < MIN_CHARGE_SOC or (current_soc < 100 and current_rate < CHARGE_COST_THRESHOLD):
                action = 'Charge from Grid'
                total_charge_cost_pence += current_rate * solar_generation * 1000  # Assuming rate is in pence per kWh
            elif current_soc > MIN_CHARGE_SOC and current_rate >= CHARGE_COST_THRESHOLD:
                action = 'Discharge'
            else:
                action = 'Hold'

            predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = predicted_soc
            actions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = action

        else:
            print(f"No matching data for timestamp {current_time}")

        current_time += timedelta(minutes=15)

    total_charge_cost_pounds = total_charge_cost_pence / 100
    print(f"Total estimated charge cost: £{total_charge_cost_pounds:.2f}")

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