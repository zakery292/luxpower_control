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
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    conn.row_factory = sqlite3.Row  # Make rows accessible like dictionaries
    cursor = conn.cursor()
    
    if request.method == 'POST':
        selected_table = request.form['table_select']
    else:
        selected_table = tables[0][0] if tables else None

    if selected_table:
        cursor.execute(f"SELECT * FROM {selected_table}")
        data = [dict(row) for row in cursor.fetchall()]
    else:
        data = []

    cursor.close()
    conn.close()

    return render_template('index.html', tables=tables, data=data, selected_table=selected_table)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)