import sqlite3
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import os
DATABASE_FILENAME = "/config/soc_database.db"



def on_connect(client, userdata, flags, rc):
    print("SOC COLLECTIONS Connected with result code " + str(rc))
    client.subscribe("battery_automation/soc_data")
    client.subscribe("battery_automation/grid_data")
    client.subscribe("battery_automation/rates_data")


def on_message(client, userdata, msg):
    print("SOC COLLECTIONS Message received on topic: " + msg.topic)

    payload = json.loads(msg.payload)
    timestamp = payload.get("timestamp")

    # Check if the payload contains SoC data
    if "soc" in payload:
        soc = payload["soc"]
        print(f"SOC COLLECTIONS  Received SoC data: {soc} at {timestamp}")
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO soc_data (timestamp, soc) VALUES (?, ?)", (timestamp, soc)
        )
        conn.commit()
        conn.close()

    # Check if the payload contains grid data
    elif "grid" in payload:
        grid = payload["grid"]
        print(f"SOC COLLECTIONS  Received Grid data: {grid} at {timestamp}")
        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO grid_data (timestamp, grid_data) VALUES (?, ?)",
            (timestamp, grid),
        )
        conn.commit()
        conn.close()

    elif msg.topic == "battery_automation/rates_data":
        rates = payload.get("rates", [])  # Get the list of rates
        timestamp = payload.get(
            "timestamp", datetime.now().isoformat()
        )  # Use the provided timestamp
        print(f"SOC COLLECTIONS  Received Rates data at {timestamp}")

        conn = sqlite3.connect(DATABASE_FILENAME)
        cursor = conn.cursor()
        for rate in rates:
            # Extract individual rate data
            cost = rate.get("Cost", "")
            date = rate.get("Date", "")
            start_time = rate.get("Start Time", "")
            end_time = rate.get("End Time", "")

            # Insert or update the rates data in the database
            cursor.execute(
                """
                INSERT INTO rates_data (Date, StartTime, EndTime, Cost)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (Date, StartTime, EndTime)
                DO UPDATE SET Cost = excluded.cost
                """,
                (date, start_time, end_time, cost),
            )
        conn.commit()
        conn.close()
    else:
        print("SOC COLLECTIONS  Other message received")


def on_disconnect(client, userdata, rc):
    print("SOC COLLECTIONS  Disconnected with result code " + str(rc))


def on_log(client, userdata, level, buf):
    print("SOC COLLECTIONS  Log: ", buf)



# Function to read MQTT configuration from the options.json file
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
print(f'SOC COLLECTIONS  Connecting to MQTT Broker at {mqtt_host}:{mqtt_port} with username {mqtt_user}')
print('This is from soc_collections.py')

# Connect to MQTT broker
try:
    client.connect(mqtt_host, mqtt_port, 60)  # Use variables for host and port
except Exception as e:
    print(f"SOC COLLECTIONS  Failed to connect to MQTT broker: {e}")
    exit(1)

# Start the loop
client.loop_forever()