import sqlite3
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import os
DATABASE_FILENAME = "/config/soc_database.db"


def on_connect(client, userdata, flags, rc):
    print("SOLAR COLLECTIONS Connected with result code " + str(rc))
    client.subscribe("battery_automation/solar")

def on_message(client, userdata, msg):
    print("SOLAR COLLECTIONS Message received on topic: " + msg.topic)
    # Check if the payload contains solar data
    msg.topic == "battery_automation/solar"
    solar_data_list = json.loads(msg.payload.decode('utf-8'))
    print(f"SOLAR COLLECTIONS  Received solar data")

    conn = sqlite3.connect(DATABASE_FILENAME)
    cursor = conn.cursor()

    try:
        for solar_data in solar_data_list:
            # Extract individual solar data
            period_start = solar_data["period_start"]
            pv_estimate = solar_data["pv_estimate"]

            print(f"Inserting solar data: {period_start}, {pv_estimate}")

            # Convert period_start to a datetime object and format it as needed
            period_start_dt = datetime.fromisoformat(period_start)
            formatted_period_start = period_start_dt.strftime('%Y-%m-%d %H:%M:%S')

            # Insert or update the solar data in the database
            cursor.execute(
                """
                INSERT INTO solar (datetime, pv_estimate)
                VALUES (?, ?)
                ON CONFLICT (datetime)
                DO UPDATE SET pv_estimate = excluded.pv_estimate
                WHERE solar.pv_estimate <> excluded.pv_estimate
                """,
                (formatted_period_start, pv_estimate),
            )
            print("Inserted or updated solar data")

        conn.commit()
    except Exception as e:
        print(f"Error inserting solar data: {e}")
    finally:
        conn.close()

def on_disconnect(client, userdata, rc):
    print("SOLAR COLLECTIONS  Disconnected with result code " + str(rc))


def on_log(client, userdata, level, buf):
    print("SOLAR COLLECTIONS  Log: ", buf)

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
print(f'SOLAR COLLECTIONS  Connecting to MQTT Broker at {mqtt_host}:{mqtt_port} with username {mqtt_user}')
print('This is from SOLAR COLLECTIONS.py')

# Connect to MQTT broker
try:
    client.connect(mqtt_host, mqtt_port, 60)  # Use variables for host and port
except Exception as e:
    print(f"SOLAR COLLECTIONS  Failed to connect to MQTT broker: {e}")
    exit(1)

# Start the loop
client.loop_forever()