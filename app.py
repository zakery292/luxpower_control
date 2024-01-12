from flask import Flask, render_template, request
import sqlite3
import json
import sys
import logging
from datetime import datetime

# Configure logging
app = Flask(__name__)
app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

# Function to get database path
def get_db_path():
    with open('/data/options.json') as f:
        options = json.load(f)
    return options.get('db_path', '/config/soc_database.db')

# Main route
@app.route('/', methods=['GET', 'POST'])
def index():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Handle table selection
    selected_table = request.form.get('table_select') if request.method == 'POST' else (tables[0]['name'] if tables else None)

    # Initialize variables
    total_rows = 0
    last_updated = None
    total_pages = 0
    data = []

    # Fetch data for selected table
    if selected_table:
        # Get total rows
        cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
        total_rows = cursor.fetchone()[0]

        # Calculate total pages for pagination
        total_pages = (total_rows + per_page - 1) // per_page

        # Get last updated timestamp (if your table has a timestamp column)
        cursor.execute(f"SELECT MAX(timestamp) FROM {selected_table}")
        last_updated_result = cursor.fetchone()[0]
        last_updated = datetime.fromisoformat(last_updated_result) if last_updated_result else None

        # Fetch data for current page
        cursor.execute(f"SELECT * FROM {selected_table} LIMIT {per_page} OFFSET {offset}")
        data = [dict(row) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    # Render template with all the data
    return render_template('index.html', tables=tables, data=data, selected_table=selected_table, page=page, total_pages=total_pages, total_rows=total_rows, last_updated=last_updated)

# Start the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
