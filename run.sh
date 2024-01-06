#!/bin/bash
echo "Starting the LuxPowerControl service..."

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
