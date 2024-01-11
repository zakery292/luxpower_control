import sqlite3
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import os
import threading

DATABASE_FILENAME = "/config/soc_database.db"
db_lock = threading.Lock()

# Establish a database connection
try:
    conn = sqlite3.connect(DATABASE_FILENAME, check_same_thread=False)
except Exception as e:
    print(f"Error connecting to the database: {e}")
    exit(1)

def execute_db_query(query, parameters=()):
    with db_lock:
        try:
            cursor = conn.cursor()
            cursor.execute(query, parameters)
            conn.commit()
        except Exception as e:
            print(f"Database error: {e}")
            conn.rollback()

def on_connect(client, userdata, flags, rc):
    print("SOC COLLECTIONS Connected with result code " + str(rc))
    client.subscribe("battery_automation/soc_data")
    client.subscribe("battery_automation/grid_data")
    client.subscribe("battery_automation/rates_data")

def on_message(client, userdata, msg):
    print("SOC COLLECTIONS Message received on topic: " + msg.topic)
    payload = json.loads(msg.payload)
    timestamp = payload.get("timestamp")

    if "soc" in payload:
        soc = payload["soc"]
        print(f"SOC COLLECTIONS Received SoC data: {soc} at {timestamp}")
        execute_db_query("INSERT INTO soc_data (timestamp, soc) VALUES (?, ?)", (timestamp, soc))

    elif "grid" in payload:
        grid = payload["grid"]
        print(f"SOC COLLECTIONS Received Grid data: {grid} at {timestamp}")
        execute_db_query("INSERT INTO grid_data (timestamp, grid_data) VALUES (?, ?)", (timestamp, grid))

    elif msg.topic == "battery_automation/rates_data":
        rates = payload.get("rates", [])
        print(f"SOC COLLECTIONS Received Rates data at {timestamp}")

        for rate in rates:
            cost = rate.get("Cost", "")
            date = rate.get("Date", "")
            start_time = rate.get("Start Time", "")
            end_time = rate.get("End Time", "")
            print(f"Inserting rate: {date}, {start_time}, {end_time}, {cost}")
            execute_db_query("""
                INSERT INTO rates_data (Date, StartTime, EndTime, Cost)
                VALUES (?, ?, ?, ?)
                ON CONFLICT (Date, StartTime, EndTime)
                DO UPDATE SET Cost = excluded.cost
                WHERE rates_data.Cost <> excluded.cost
                """, (date, start_time, end_time, cost))

def on_disconnect(client, userdata, rc):
    print("SOC COLLECTIONS Disconnected with result code " + str(rc))
    conn.close()

def on_log(client, userdata, level, buf):
    print("SOC COLLECTIONS Log: ", buf)

def get_mqtt_config():
    config_path = '/data/options.json'
    try:
        with open(config_path, 'r') as file:
            config = json.load(file)
        return config['mqtt_host'], int(config['mqtt_port']), config['mqtt_user'], config['mqtt_password']
    except Exception as e:
        print(f"Error reading MQTT configuration: {e}")
        return '192.168.1.135', 1883, 'default_user', 'default_password'

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
    print(f"SOC COLLECTIONS Failed to connect to MQTT broker: {e}")
    conn.close()
    exit(1)

client.loop_forever()
