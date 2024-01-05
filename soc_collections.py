import sqlite3
import json
import paho.mqtt.client as mqtt
from datetime import datetime
import os
DATABASE_FILENAME = "soc_database.db"
print("hellow World")


def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    client.subscribe("battery_automation/soc_data")
    client.subscribe("battery_automation/grid_data")
    client.subscribe("battery_automation/rates_data")


def on_message(client, userdata, msg):
    print("Message received on topic: " + msg.topic)

    payload = json.loads(msg.payload)
    timestamp = payload.get("timestamp")

    # Check if the payload contains SoC data
    if "soc" in payload:
        soc = payload["soc"]
        print(f"Received SoC data: {soc} at {timestamp}")
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
        print(f"Received Grid data: {grid} at {timestamp}")
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
        print(f"Received Rates data at {timestamp}")

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
        print("Other message received")


def on_disconnect(client, userdata, rc):
    print("Disconnected with result code " + str(rc))


def on_log(client, userdata, level, buf):
    print("Log: ", buf)


# Set up MQTT client
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.on_disconnect = on_disconnect
client.on_log = on_log

# Set MQTT username and password (replace with your credentials)
mqtt_username = os.getenv('MQTT_USER', 'default_user')
mqtt_password = os.getenv('MQTT_PASSWORD', 'default_password')
mqtt_host = os.getenv('MQTT_HOST', '192.168.1.135')
mqtt_port = int(os.getenv('MQTT_PORT', 1883))

# Connect to MQTT broker (update with your broker's IP address and port)
try:
    client.connect("192.168.1.135", 1883, 60)
except Exception as e:
    print(f"Failed to connect to MQTT broker: {e}")
    exit(1)

# Loop forever, processing received messages
print("Starting MQTT loop...")
client.loop_forever()
