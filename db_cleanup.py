import sqlite3
from datetime import datetime, time
from apscheduler.schedulers.background import BackgroundScheduler

def delete_old_data():
    DATABASE_FILENAME = "/luxpowercontrol_db/soc_database.db"
    with sqlite3.connect(DATABASE_FILENAME) as conn:
        cursor = conn.cursor()
        
        # Calculate the date 4 weeks ago
        four_weeks_ago = (datetime.datetime.now() - datetime.timedelta(weeks=4)).strftime('%Y-%m-%d %H:%M:%S')

        # Delete data older than 4 weeks from each table
        cursor.execute("DELETE FROM rates_data WHERE Date < ?", (four_weeks_ago,))
        cursor.execute("DELETE FROM soc_data WHERE timestamp < ?", (four_weeks_ago,))
        cursor.execute("DELETE FROM grid_data WHERE timestamp < ?", (four_weeks_ago,))

        conn.commit()

# Set up the scheduler to run the delete_old_data function every day
scheduler = BackgroundScheduler()
scheduler.add_job(delete_old_data, 'interval', days=1)
scheduler.start()

# Keep the script running
try:
    while True:
        time.sleep(2)
except (KeyboardInterrupt, SystemExit):
    scheduler.shutdown()
