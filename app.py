from flask import Flask, render_template, request
import sqlite3
import json
import sys
import logging

app.logger.addHandler(logging.StreamHandler(sys.stdout))
app.logger.setLevel(logging.DEBUG)

app = Flask(__name__)

def get_db_path():
    with open('/data/options.json') as f:  # Path to Home Assistant add-on options
        options = json.load(f)
    return options.get('db_path', '/config/soc_database.db')  # Default if not set

@app.route('/', methods=['GET', 'POST'])
def index():
    db_path = get_db_path()  # Make sure this function is defined to get the DB path
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    app.logger.debug(f"Request method: {request.method}")
    if request.method == 'POST':
        app.logger.debug("Handling POST request")

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    selected_table = request.form.get('table_select') if request.method == 'POST' else (tables[0]['name'] if tables else None)
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 30
    offset = (page - 1) * per_page

    if selected_table:
        cursor.execute(f"SELECT COUNT(*) FROM {selected_table}")
        total_rows = cursor.fetchone()[0]
        total_pages = (total_rows + per_page - 1) // per_page

        cursor.execute(f"SELECT * FROM {selected_table} LIMIT {per_page} OFFSET {offset}")
        data = [dict(row) for row in cursor.fetchall()]
    else:
        total_pages = 0
        data = []

    cursor.close()
    conn.close()

    return render_template('index.html', tables=tables, data=data, selected_table=selected_table, page=page, total_pages=total_pages)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)