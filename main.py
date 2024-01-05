import subprocess

# Run both scripts simultaneously
print('Starting the Scripts running simultaneously')
subprocess.Popen(["python", "soc_collections.py"])
subprocess.Popen(["python", "predict_soc.py"])

# Keep the main script running
while True:
    pass