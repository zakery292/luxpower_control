import sqlite3

# Define the full path for the database file
DATABASE_FILENAME = "/opt/soc_database.db"
print("Creating database with file name " + DATABASE_FILENAME)

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
print(f"Database created with the file name {DATABASE_FILENAME}")