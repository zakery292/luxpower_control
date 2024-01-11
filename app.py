from flask import Flask, render_template, request
import sqlite3
import json

app = Flask(__name__)

def get_db_path():
    with open('/data/config.yaml') as f:  # Path to Home Assistant add-on options
        options = json.load(f)
    return options.get('db_path', 'default_db_path.db')  # Default if not set

@app.route('/', methods=['GET', 'POST'])
def index():
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Get table names for dropdown
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    selected_table = request.form.get('table_select') if request.method == 'POST' else tables[0][0]
    cursor.execute(f"SELECT * FROM {selected_table}")
    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('index.html', tables=tables, data=data, selected_table=selected_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
