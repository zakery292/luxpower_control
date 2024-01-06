#!/bin/bash
echo "Starting the LuxPowerControl service..."
# Define the path to the options.json file
CONFIG_PATH="/data/options.json"
echo "Config path: $CONFIG_PATH"

# Function to manually parse simple JSON
parse_json() {
    key=$1
    config=$2
    pattern="\"$key\": \"([^\"]*)\""
    if [[ $config =~ $pattern ]]; then
        echo "${BASH_REMATCH[1]}"
    else
        echo "Error: Key $key not found in JSON config."
    fi
}

echo "Parsing options.json..."
# Read the MQTT configuration
CONFIG_CONTENT=$(cat $CONFIG_PATH)
MQTT_HOST=$(parse_json "mqtt_host" "$CONFIG_CONTENT")
MQTT_PORT=$(parse_json "mqtt_port" "$CONFIG_CONTENT")
MQTT_USER=$(parse_json "mqtt_user" "$CONFIG_CONTENT")
MQTT_PASSWORD=$(parse_json "mqtt_password" "$CONFIG_CONTENT")

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
