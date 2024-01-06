import sqlite3
import os

# Define the full path for the database file inside the Docker container
DATABASE_FILENAME = "addon_config:/soc_database.db"
print("Checking if database exists...")

# Check if the database file exists
if not os.path.exists(DATABASE_FILENAME):
    print("No database found. Creating a new one...")
else:
    print("Existing database found. Continuing...")

conn = sqlite3.connect(DATABASE_FILENAME)
cursor = conn.cursor()

# Create tables
cursor.execute('''CREATE TABLE IF NOT EXISTS rates_data (
                    Date TEXT, 
                    StartTime TEXT, 
                    EndTime TEXT, 
                    Cost REAL, 
                    PRIMARY KEY (Date, StartTime, EndTime))''')

cursor.execute('''CREATE TABLE IF NOT EXISTS soc_data (
                    timestamp TEXT PRIMARY KEY, 
                    soc REAL)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS grid_data (
                    timestamp TEXT PRIMARY KEY, 
                    grid_data REAL)''')

conn.commit()
conn.close()
print(f"Database operation completed. File: {DATABASE_FILENAME}")