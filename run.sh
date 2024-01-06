#!/bin/bash
echo "Starting LuxPower Control & DB Add-on..."
# Define the path to the options.json file

CONFIG_PATH="/data/options.json"

# Check if the options.json file exists
if [ ! -f "$CONFIG_PATH" ]; then
    echo "Configuration file not found: $CONFIG_PATH"
    exit 1
fi
echo "Reading MQTT configuration..."
# Use jq to parse the MQTT configuration options
MQTT_HOST=$(jq --raw-output '.mqtt_host' "$CONFIG_PATH")
MQTT_PORT=$(jq --raw-output '.mqtt_port' "$CONFIG_PATH")
MQTT_USER=$(jq --raw-output '.mqtt_user' "$CONFIG_PATH")
MQTT_PASSWORD=$(jq --raw-output '.mqtt_password' "$CONFIG_PATH")

# Export these settings as environment variables
export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASSWORD

# Debug: Print the MQTT configuration
echo "MQTT Configuration:"
echo "Host: $MQTT_HOST"
echo "Port: $MQTT_PORT"
echo "User: $MQTT_USER"

echo "Initializing the database..."

python ./init_db.py

echo "Starting Python scripts..."

# Run your Python scripts here, e.g.,
python /path/to/your/soc_collections.py &
python /path/to/your/predict_soc.py &


# Log script startup completion
echo "LuxPower Control & DB Add-on started successfully."
# Wait for the processes to complete
wait