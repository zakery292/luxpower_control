#!/bin/bash
echo "Starting the LuxPowerControl service..."
# Define the path to the options.json file
CONFIG_PATH="/data/options.json"
echo "Config path: $CONFIG_PATH"

# Function to manually parse simple JSON
parse_json() {
    echo $1 | sed -e 's/.*"'$2'": *\([^,]*\).*/\1/' | sed -e 's/^"\(.*\)"$/\1/'
}

echo "Parsing options.json..."
# Read the MQTT configuration
CONFIG_CONTENT=$(cat $CONFIG_PATH)
MQTT_HOST=$(parse_json "$CONFIG_CONTENT" mqtt_host)
MQTT_PORT=$(parse_json "$CONFIG_CONTENT" mqtt_port)
MQTT_USER=$(parse_json "$CONFIG_CONTENT" mqtt_user)
MQTT_PASSWORD=$(parse_json "$CONFIG_CONTENT" mqtt_password)

echo "MQTT Configuration:"
echo "Host: $MQTT_HOST"
echo "Port: $MQTT_PORT"
echo "User: $MQTT_USER"
echo "Password: $MQTT_PASSWORD"

# Export these settings as environment variables
export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASSWORD

# Initialize the database
echo "Initializing the database..."
python /opt/init_db.py

# Start your Python scripts and redirect their output to stdout/stderr
echo "Starting Python scripts..."
python /opt/soc_collections.py > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &
python /opt/predict_soc.py > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &

echo "LuxPower Control & DB Add-on started successfully."

# Wait for the processes to complete
wait
