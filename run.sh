#!/usr/bin/env bashio

# Logging configuration and script start
echo "Starting LuxPower Control & DB Add-on..."

# Read the configuration options from Home Assistant
echo "Reading MQTT configuration..."
MQTT_HOST=$(bashio::config 'mqtt_host')
MQTT_PORT=$(bashio::config 'mqtt_port')
MQTT_USER=$(bashio::config 'mqtt_user')
MQTT_PASSWORD=$(bashio::config 'mqtt_password')

# Log the MQTT configuration (excluding password for security)
echo "MQTT Configuration:"
echo "Host: $MQTT_HOST"
echo "Port: $MQTT_PORT"
echo "User: $MQTT_USER"

# Export these settings as environment variables
export MQTT_HOST MQTT_PORT MQTT_USER MQTT_PASSWORD

# Initialize the database
echo "Initializing the database..."
python ./init_db.py

# Start your Python scripts
echo "Starting Python scripts..."
python ./soc_collections.py &
python ./predict_soc.py &

# Log script startup completion
echo "LuxPower Control & DB Add-on started successfully."

# Wait indefinitely to keep the container running
wait