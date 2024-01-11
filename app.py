from flask import Flask, render_template, request
import sqlite3
import json

app = Flask(__name__)

def get_db_path():
    with open('/data/options.json') as f:  # Path to Home Assistant add-on options
        options = json.load(f)
    return options.get('db_path', '/config/soc_database.db')  # Default if not set

@app.route('/', methods=['GET', 'POST'])
def index():
    db_path = get_db_path()  # Make sure you have defined this function
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch table names for the dropdown
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    # Ensure 'tables' is not empty before accessing it
    if tables:
        if request.method == 'POST':
            selected_table = request.form['table_select']
        else:
            selected_table = tables[0]['name']  # Accessing the first table's name

        cursor.execute(f"SELECT * FROM {selected_table}")
        data = [dict(row) for row in cursor.fetchall()]
    else:
        selected_table = None
        data = []

    cursor.close()
    conn.close()

    return render_template('index.html', tables=tables, data=data, selected_table=selected_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)