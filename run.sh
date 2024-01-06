#!/bin/bash
echo "Starting LuxPower Control & DB Add-on..."
# Define the path to the options.json file

CONFIG_PATH="/data/options.json"

# Function to manually parse simple JSON
parse_json() {
    echo $1 | sed -e 's/.*"'$2'":\([^,}]*\).*/\1/'
}

# Read the MQTT configuration
MQTT_HOST=$(parse_json "$(cat $CONFIG_PATH)" mqtt_host)
MQTT_PORT=$(parse_json "$(cat $CONFIG_PATH)" mqtt_port)
MQTT_USER=$(parse_json "$(cat $CONFIG_PATH)" mqtt_user)
MQTT_PASSWORD=$(parse_json "$(cat $CONFIG_PATH)" mqtt_password)

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