#!/bin/bash
echo "Starting the LuxPowerControl service..."

echo "creating the directory for the database..."
# Define the directory path within the container
CONFIG_DIR="/luxpowercontrol_db"

# Check if the directory exists, and create it if it does not
if [ ! -d "$CONFIG_DIR" ]; then
    echo "Directory $CONFIG_DIR does not exist. Creating it..."
    mkdir -p "$CONFIG_DIR"
fi
echo "Directory $CONFIG_DIR exists."
# Initialize the database
echo "Initializing the database..."
python /opt/init_db.py

# Start your Python scripts and redirect their output to stdout/stderr
echo "Starting Python scripts..."
python /opt/soc_collections.py > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &
python /opt/predict_soc.py > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &
python /opt/init_db.py > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &

echo "LuxPower Control & DB Add-on started successfully."

# Wait for the processes to complete
wait
