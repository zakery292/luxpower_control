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
    return df_soc.set_index("timestamp").resample("15T").mean().reset_index()

def get_grid_data():
    print("Loading Grid data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_grid = pd.read_sql_query("SELECT timestamp, grid_data FROM grid_data", conn)
    df_grid["timestamp"] = pd.to_datetime(df_grid["timestamp"])
    return df_grid.set_index("timestamp").resample("15T").mean().reset_index()

def get_solar_data():
    print("Loading Solar data from database...")
    conn = sqlite3.connect(DATABASE_FILENAME)
    df_solar = pd.read_sql_query("SELECT * FROM solar", conn)
    df_solar["datetime"] = pd.to_datetime(df_solar["datetime"])
    return df_solar.set_index("datetime").resample("15T").mean().reset_index()

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

def prepare_data():
    df_soc = get_soc_data()
    df_grid = get_grid_data()
    df_solar = get_solar_data()
    
    # Change 'datetime' to 'timestamp' in df_solar for consistent merging
    df_solar = df_solar.rename(columns={"datetime": "timestamp"})

    # Merge and preprocess data
    df_merged = pd.merge(df_soc, df_grid, on="timestamp", how="outer")
    df_merged = pd.merge(df_merged, df_solar, on="timestamp", how="outer")
    df_merged.ffill(inplace=True)  # Forward fill to handle NaNs
    df_merged['minute_of_day'] = df_merged['timestamp'].dt.minute + df_merged['timestamp'].dt.hour * 60
    df_merged['hour_of_day'] = df_merged['timestamp'].dt.hour
    df_merged['day_of_week'] = df_merged['timestamp'].dt.weekday()
    return df_merged
def predict_soc_for_day(start_date, end_date, model, df):
    print("Predicting SOC for the day...")
    start_timestamp = datetime.strptime(start_date, "%Y-%m-%d %H:%M:%S")
    end_timestamp = datetime.strptime(end_date, "%Y-%m-%d %H:%M:%S")

    predictions = {}
    current_time = start_timestamp
    while current_time < end_timestamp:
        row = df[df["timestamp"] == current_time].iloc[0]
        features = {
            "minute_of_day": current_time.minute + current_time.hour * 60,
            "hour_of_day": current_time.hour,
            "day_of_week": current_time.weekday(),
            "Cost": row["Cost"],
            "grid_data": row["grid_data"],
            "pv_estimate": row["pv_estimate"]
        }
        predicted_soc = model.predict(pd.DataFrame([features]))[0]
        predictions[current_time.strftime("%Y-%m-%d %H:%M:%S")] = max(0, min(predicted_soc, 100))
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
        df = prepare_data()
        model = train_model(df)
        predictions = predict_soc_for_day(start_date, end_date, model, df)
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
