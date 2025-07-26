from flask import Flask, render_template, request, redirect, url_for, flash
import os
import json
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-GUI backend for matplotlib
import matplotlib.pyplot as plt
import sqlite3
import datetime
import zipfile

# ---------------------------
# Data persistence utilities
# ---------------------------
class DataManager:
    """Lightweight wrapper around SQLite for storing weight entries."""

    def __init__(self, db_file="weight_data.db"):
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file, check_same_thread=False)
        self.create_table()
        self.height = None

    def create_table(self):
        """Create the entries table if needed."""
        query = """
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            logId INTEGER,
            date TEXT,
            time TEXT,
            timestamp TEXT,
            weight_kg REAL,
            fat_percent REAL,
            bmi REAL,
            source TEXT
        )
        """
        self.conn.execute(query)
        self.conn.commit()

    def add_entry(self, entry):
        """Insert a new weight entry."""
        query = """
        INSERT INTO entries (logId, date, time, timestamp, weight_kg, fat_percent, bmi, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        dt_str = f"{entry['date']} {entry['time']}"
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
            timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = dt_str
        self.conn.execute(query, (
            entry.get("logId"),
            entry.get("date"),
            entry.get("time"),
            timestamp,
            entry.get("weight_kg"),
            entry.get("fat_percent"),
            entry.get("bmi"),
            entry.get("source")
        ))
        self.conn.commit()

    def entry_exists(self, log_id, timestamp):
        """Return True if an entry with the same ``logId`` or ``timestamp`` exists."""
        if log_id is not None:
            cur = self.conn.execute(
                "SELECT 1 FROM entries WHERE logId=?", (log_id,)
            )
            if cur.fetchone():
                return True
        cur = self.conn.execute(
            "SELECT 1 FROM entries WHERE timestamp=?", (timestamp,)
        )
        return cur.fetchone() is not None

    def get_all_entries(self):
        """Return all entries as a pandas DataFrame."""
        return pd.read_sql_query("SELECT * FROM entries ORDER BY timestamp", self.conn)

    def update_entry(self, entry_id, updated_entry):
        """Update an existing entry."""
        query = """
        UPDATE entries
        SET logId=?, date=?, time=?, timestamp=?, weight_kg=?, fat_percent=?, bmi=?, source=?
        WHERE id=?
        """
        dt_str = f"{updated_entry['date']} {updated_entry['time']}"
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
            timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = dt_str
        self.conn.execute(query, (
            updated_entry.get("logId"),
            updated_entry.get("date"),
            updated_entry.get("time"),
            timestamp,
            updated_entry.get("weight_kg"),
            updated_entry.get("fat_percent"),
            updated_entry.get("bmi"),
            updated_entry.get("source"),
            entry_id
        ))
        self.conn.commit()

    def delete_entry(self, entry_id):
        """Remove an entry from the database."""
        self.conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
        self.conn.commit()

    def add_if_new(self, entry):
        """Add ``entry`` only if it does not already exist."""
        dt_str = f"{entry['date']} {entry['time']}"
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
            timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = dt_str
        if not self.entry_exists(entry.get("logId"), timestamp):
            self.add_entry(entry)
            return True
        return False

# -----------------------
# Flask application setup
# -----------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'change-me'

# Use a global DataManager instance
data_manager = DataManager()


def import_fitbit_zip(file_obj, source="Fitbit"):
    """Import weight entries from a Fitbit export ZIP file.

    Only new entries (based on ``logId`` or timestamp) are stored. Returns the
    number of newly added rows.
    """
    new_count = 0
    with zipfile.ZipFile(file_obj) as zf:
        names = zf.namelist()

        # ------------------------------
        # First try the older Weight.csv
        # ------------------------------
        weight_csv = next((n for n in names if n.endswith("Weight.csv")), None)
        if weight_csv:
            with zf.open(weight_csv) as csv_file:
                df = pd.read_csv(csv_file)
                # Normalise column names to simplify lookup
                df.columns = [c.strip().lower() for c in df.columns]

                for _, row in df.iterrows():
                    date_val = row.get("date")
                    time_val = row.get("time", "00:00:00")
                    weight = row.get("weight") or row.get("weight (kg)")
                    if weight is None:
                        continue
                    weight_kg = float(weight)
                    if weight_kg > 200:  # values >200 are likely lbs
                        weight_kg *= 0.45359237

                    entry = {
                        "logId": row.get("logid"),
                        "date": datetime.datetime.strptime(str(date_val), "%Y-%m-%d").strftime("%m/%d/%y")
                        if isinstance(date_val, str) and "-" in date_val else str(date_val),
                        "time": str(time_val),
                        "weight_kg": weight_kg,
                        "fat_percent": row.get("fat"),
                        "bmi": row.get("bmi"),
                        "source": source,
                    }

                    if data_manager.add_if_new(entry):
                        new_count += 1
            return new_count

        # ------------------------------------------------------------
        # No Weight.csv found - look for newer JSON files (weight-*.json)
        # ------------------------------------------------------------
        json_files = [n for n in names if n.lower().endswith('.json') and os.path.basename(n).lower().startswith('weight-')]
        if not json_files:
            raise ValueError("No weight data found in ZIP")

        for name in json_files:
            with zf.open(name) as json_file:
                data = json.load(json_file)

            # Some exports wrap the list of entries in a dict. Attempt to
            # locate the list automatically.
            if isinstance(data, dict):
                list_val = None
                for val in data.values():
                    if isinstance(val, list):
                        list_val = val
                        break
                data = list_val if list_val is not None else [data]

            if not isinstance(data, list):
                data = [data]

            for row in data:
                date_val = row.get('date') or row.get('dateTime')
                time_val = row.get('time', '00:00:00')
                weight = (row.get('weight') or row.get('weight_kg') or
                          row.get('weight (kg)'))
                if weight is None or date_val is None:
                    continue
                weight_kg = float(weight)
                if weight_kg > 200:
                    weight_kg *= 0.45359237

                entry = {
                    'logId': row.get('logId') or row.get('logid'),
                    'date': datetime.datetime.strptime(str(date_val), "%Y-%m-%d").strftime("%m/%d/%y")
                    if isinstance(date_val, str) and '-' in str(date_val) else str(date_val),
                    'time': str(time_val),
                    'weight_kg': weight_kg,
                    'fat_percent': row.get('fat') or row.get('fat_percent'),
                    'bmi': row.get('bmi'),
                    'source': source,
                }

                if data_manager.add_if_new(entry):
                    new_count += 1

    return new_count

@app.route('/')
def index():
    """Display all entries and allow basic operations."""
    df = data_manager.get_all_entries()
    # Convert the data frame to an HTML table string. This string will be
    # injected directly into the template so the browser renders a nice table.
    table_html = df.to_html(classes='table table-striped', index=False)
    return render_template('index.html', table=table_html,
                           titles=df.columns.values,
                           datetime=datetime)

@app.route('/add', methods=['POST'])
def add_entry():
    """Add a new weight entry from the submitted form."""
    entry = {
        'logId': request.form.get('logId', type=int),
        'date': request.form['date'],
        'time': request.form['time'],
        'weight_kg': request.form.get('weight_kg', type=float),
        'fat_percent': request.form.get('fat_percent', type=float),
        'bmi': None,
        'source': request.form.get('source', 'Manual')
    }
    if data_manager.height:
        entry['bmi'] = entry['weight_kg'] / (data_manager.height ** 2)
    data_manager.add_entry(entry)
    flash('Entry added', 'success')
    return redirect(url_for('index'))


@app.route('/import', methods=['POST'])
def import_zip_route():
    """Handle Fitbit ZIP uploads from the web form."""
    file = request.files.get('zipfile')
    source = request.form.get('source', 'Fitbit')
    if not file or not file.filename.lower().endswith('.zip'):
        flash('Please upload a valid .zip file', 'danger')
        return redirect(url_for('index'))
    try:
        added = import_fitbit_zip(file, source)
        flash(f'Imported {added} new entries', 'success')
    except Exception as exc:
        flash(f'Import failed: {exc}', 'danger')
    return redirect(url_for('index'))

@app.route('/delete/<int:entry_id>', methods=['POST'])
def delete_entry(entry_id):
    """Delete an entry by ID."""
    data_manager.delete_entry(entry_id)
    flash('Entry deleted', 'info')
    return redirect(url_for('index'))

@app.route('/edit/<int:entry_id>', methods=['GET', 'POST'])
def edit_entry(entry_id):
    """Edit an existing entry."""
    df = data_manager.get_all_entries()
    row = df[df['id'] == entry_id].iloc[0]
    if request.method == 'POST':
        updated = {
            'logId': request.form.get('logId', type=int),
            'date': request.form['date'],
            'time': request.form['time'],
            'weight_kg': request.form.get('weight_kg', type=float),
            'fat_percent': request.form.get('fat_percent', type=float),
            'bmi': None,
            'source': request.form.get('source', 'Manual')
        }
        if data_manager.height:
            updated['bmi'] = updated['weight_kg'] / (data_manager.height ** 2)
        data_manager.update_entry(entry_id, updated)
        flash('Entry updated', 'success')
        return redirect(url_for('index'))
    return render_template('edit.html', entry=row)

@app.route('/settings', methods=['GET', 'POST'])
def settings():
    """Manage user settings such as height used for BMI."""
    if request.method == 'POST':
        try:
            data_manager.height = float(request.form['height'])
            flash('Height saved', 'success')
        except ValueError:
            flash('Invalid height', 'danger')
    return render_template('settings.html', height=data_manager.height)

@app.route('/plot/<plot_type>.png')
def plot_png(plot_type):
    """Generate matplotlib plot based on selected type."""
    df = data_manager.get_all_entries()
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    fig, ax = plt.subplots()
    if plot_type == 'weight':
        ax.plot(df['timestamp'], df['weight_kg'], marker='o')
        ax.set_ylabel('Weight (kg)')
    elif plot_type == 'bmi':
        ax.plot(df['timestamp'], df['bmi'], marker='o')
        ax.set_ylabel('BMI')
    elif plot_type == 'lean':
        lean = df['weight_kg'] * (1 - df['fat_percent'] / 100)
        ax.plot(df['timestamp'], lean, marker='o')
        ax.set_ylabel('Lean Mass (kg)')
    elif plot_type == 'fat':
        ax.plot(df['timestamp'], df['fat_percent'], marker='o')
        ax.set_ylabel('Body Fat (%)')
    ax.set_xlabel('Time')
    ax.set_title(plot_type.title())
    fig.autofmt_xdate()

    # Render plot to PNG image in memory
    import io
    output = io.BytesIO()
    plt.savefig(output, format='png')
    plt.close(fig)
    output.seek(0)
    from flask import send_file
    return send_file(output, mimetype='image/png')

@app.route('/plots')
def plots():
    """Page with all plots displayed."""
    return render_template('plots.html')

if __name__ == '__main__':
    # Debug mode should be disabled in production
    app.run(debug=True)
