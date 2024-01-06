#!/bin/bash
echo "Starting the LuxPowerControl service..."


# Initialize the database
echo "Initializing the database..."
python /opt/init_db.py

echo "LuxPower Control & DB Add-on started successfully."

run_with_restart() {
    SCRIPT=$1
    until python $SCRIPT; do
        echo "Script $SCRIPT crashed with exit code $?. Respawning.." >&2
        sleep 1
    done
}
echo "Starting Python scripts..."
# Start your Python scripts with auto-restart
run_with_restart "/opt/soc_collections.py" > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &
run_with_restart "/opt/predict_soc.py" > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &
run_with_restart "/opt/db_cleanup.py" > >(tee -a /proc/1/fd/1) 2> >(tee -a /proc/1/fd/2) &

echo "LuxPower Control & DB Add-on started successfully."
# Wait for the processes to complete
wait
