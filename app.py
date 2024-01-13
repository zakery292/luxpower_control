from flask import Flask, render_template, request, jsonify
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
    data = []

    if selected_table:
        # Get total rows
        cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
        total_rows = cursor.fetchone()[0]

        # Get last updated timestamp (if your table has a timestamp column)
        cursor.execute(f"SELECT MAX(timestamp) FROM {selected_table}")
        last_updated_result = cursor.fetchone()[0]
        last_updated = datetime.fromisoformat(last_updated_result) if last_updated_result else None

        # Fetch initial data set (e.g., first 30 rows)
        cursor.execute(f"SELECT * FROM {selected_table} LIMIT 30")
        data = [dict(row) for row in cursor.fetchall()]

    cursor.close()
    conn.close()

    return render_template('index.html', tables=tables, data=data, selected_table=selected_table, total_rows=total_rows, last_updated=last_updated)

# Route for loading more data
@app.route('/load-more', methods=['GET'])
def load_more():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    selected_table = request.args.get('table')
    offset = int(request.args.get('offset', 0))
    limit = 30  # Define how many rows to load per request

    if selected_table:
        # Fetch additional data based on offset
        cursor.execute(f"SELECT FROM {selected_table} LIMIT {limit} OFFSET {offset}")
        more_data = [dict(row) for row in cursor.fetchall()]

        cursor.close()
        conn.close()

    return jsonify(more_data)



# Start the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
