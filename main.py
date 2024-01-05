import subprocess
import os
# Run both scripts simultaneously
print('Starting the Scripts running simultaneously')
subprocess.Popen(["python", "soc_collections.py"])
subprocess.Popen(["python", "predict_soc.py"])


# Print all environment variables
for key, value in os.environ.items():
    print(f"{key}: {value}")
# Keep the main script running
while True:
    pass