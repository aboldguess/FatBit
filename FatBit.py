"""GUI based weight tracker."""

import sys
import json
import os
import sqlite3
import datetime
import pandas as pd
import matplotlib.pyplot as plt

from PyQt5 import QtWidgets, QtCore
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

class DataManager:
    """Simple wrapper around SQLite for storing weight entries."""

    def __init__(self, db_file="weight_data.db"):
        # Connect to the SQLite database file and ensure schema exists
        self.db_file = db_file
        self.conn = sqlite3.connect(self.db_file)
        self.create_table()

    def create_table(self):
        """Create table if it does not exist."""
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
        """Insert a new weight entry into the database."""
        query = """
        INSERT INTO entries (logId, date, time, timestamp, weight_kg, fat_percent, bmi, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        dt_str = entry['date'] + " " + entry['time']
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
            timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = dt_str
        self.conn.execute(query, (entry.get("logId"),
                                  entry.get("date"),
                                  entry.get("time"),
                                  timestamp,
                                  entry.get("weight_kg"),
                                  entry.get("fat"),
                                  entry.get("bmi"),
                                  entry.get("source")))
        self.conn.commit()

    def get_all_entries(self):
        """Return all entries ordered by timestamp as a DataFrame."""
        df = pd.read_sql_query("SELECT * FROM entries ORDER BY timestamp", self.conn)
        return df

    def update_entry(self, entry_id, updated_entry):
        """Update an existing entry identified by ``entry_id``."""
        query = """
        UPDATE entries
        SET logId=?, date=?, time=?, timestamp=?, weight_kg=?, fat_percent=?, bmi=?, source=?
        WHERE id=?
        """
        dt_str = updated_entry['date'] + " " + updated_entry['time']
        try:
            dt_obj = datetime.datetime.strptime(dt_str, "%m/%d/%y %H:%M:%S")
            timestamp = dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            timestamp = dt_str
        self.conn.execute(query, (updated_entry.get("logId"),
                                  updated_entry.get("date"),
                                  updated_entry.get("time"),
                                  timestamp,
                                  updated_entry.get("weight_kg"),
                                  updated_entry.get("fat"),
                                  updated_entry.get("bmi"),
                                  updated_entry.get("source"),
                                  entry_id))
        self.conn.commit()

    def delete_entry(self, entry_id):
        """Remove an entry from the database."""
        query = "DELETE FROM entries WHERE id=?"
        self.conn.execute(query, (entry_id,))
        self.conn.commit()

# A simple matplotlib canvas to embed plots into our PyQt5 app.
class MplCanvas(FigureCanvas):
    """Matplotlib canvas used for plotting inside the Qt application."""

    def __init__(self, parent=None, width=5, height=4, dpi=100):
        # Create a figure and an axes object then initialise the base class
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        super(MplCanvas, self).__init__(self.fig)

# MainWindow is the primary application window.
class MainWindow(QtWidgets.QMainWindow):
    """Primary application window."""

    def __init__(self):
        super(MainWindow, self).__init__()
        self.setWindowTitle("Weight Tracker")
        self.resize(1000, 600)
        # Manager handles persistence of data
        self.data_manager = DataManager()
        # User height (in meters) is used when calculating BMI
        self.user_height = None
        self.initUI()

    def initUI(self):
        """Build the UI: tabs for data, plots and settings."""
        self.tabs = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tabs)

        # --- Data tab ---
        # Contains the table of entries and buttons for data manipulation
        self.data_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.data_tab, "Data")
        self.data_layout = QtWidgets.QVBoxLayout(self.data_tab)

        self.table = QtWidgets.QTableWidget()
        self.data_layout.addWidget(self.table)

        btn_layout = QtWidgets.QHBoxLayout()
        self.load_btn = QtWidgets.QPushButton("Load JSON File(s)")
        self.load_btn.clicked.connect(self.load_files)
        btn_layout.addWidget(self.load_btn)
        self.add_btn = QtWidgets.QPushButton("Add Entry")
        self.add_btn.clicked.connect(self.add_entry)
        btn_layout.addWidget(self.add_btn)
        self.edit_btn = QtWidgets.QPushButton("Edit Entry")
        self.edit_btn.clicked.connect(self.edit_entry)
        btn_layout.addWidget(self.edit_btn)
        self.delete_btn = QtWidgets.QPushButton("Delete Entry")
        self.delete_btn.clicked.connect(self.delete_entry)
        btn_layout.addWidget(self.delete_btn)
        self.data_layout.addLayout(btn_layout)

        # --- Plot tab ---
        # Visualises weight data using Matplotlib
        self.plot_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.plot_tab, "Plots")
        self.plot_layout = QtWidgets.QVBoxLayout(self.plot_tab)

        self.plot_combo = QtWidgets.QComboBox()
        self.plot_combo.addItems(["Weight (kg) over Time", "BMI over Time", "Lean Mass (kg) over Time", "Body Fat (%) over Time"])
        self.plot_combo.currentIndexChanged.connect(self.update_plot)
        self.plot_layout.addWidget(self.plot_combo)

        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        self.plot_layout.addWidget(self.canvas)

        # --- Settings tab ---
        # Allows user to supply height so BMI can be recalculated
        self.settings_tab = QtWidgets.QWidget()
        self.tabs.addTab(self.settings_tab, "Settings")
        self.settings_layout = QtWidgets.QFormLayout(self.settings_tab)
        self.height_edit = QtWidgets.QLineEdit()
        self.height_edit.setPlaceholderText("e.g. 1.75")
        self.settings_layout.addRow("Height (m):", self.height_edit)
        self.save_settings_btn = QtWidgets.QPushButton("Save Settings")
        self.save_settings_btn.clicked.connect(self.save_settings)
        self.settings_layout.addWidget(self.save_settings_btn)

        self.refresh_table()

    def load_files(self):
        """Load JSON or ZIP archives containing Fitbit exports."""
        options = QtWidgets.QFileDialog.Options()
        # Allow selecting both raw JSON files and ZIP archives
        files, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            "Load JSON/ZIP Files",
            "",
            "JSON/ZIP Files (*.json *.zip);;All Files (*)",
            options=options,
        )

        if not files:
            return

        for file in files:
            try:
                if file.lower().endswith(".zip"):
                    # Support ZIP archives by iterating over contained JSON files
                    import zipfile

                    with zipfile.ZipFile(file) as zf:
                        for name in zf.namelist():
                            if name.lower().endswith(".json"):
                                with zf.open(name) as f:
                                    self._process_json_file(f)
                else:
                    # Regular JSON file on disk
                    with open(file, "r") as f:
                        self._process_json_file(f)
            except Exception as e:
                QtWidgets.QMessageBox.warning(
                    self, "Error", f"Failed to load file {file}: {str(e)}"
                )

        self.refresh_table()
        self.update_plot()

    def _process_json_file(self, file_handle):
        """Parse JSON weight entries from ``file_handle`` and save them."""
        data = json.load(file_handle)
        # Each file is expected to contain a list of entries
        for entry in data:
            weight = entry.get("weight", None)
            if weight is not None:
                # If weight > 100, assume it's in lbs and convert to kg
                weight_kg = weight * 0.45359237 if weight > 100 else weight
                entry["weight_kg"] = weight_kg

            # If a user height is set, recalc BMI; otherwise use imported value
            if self.user_height:
                entry["bmi"] = weight_kg / (self.user_height ** 2)
            else:
                entry["bmi"] = entry.get("bmi", None)

            # Persist the entry through the data manager
            self.data_manager.add_entry(entry)

    def refresh_table(self):
        """Refresh the table widget with entries from the database."""
        df = self.data_manager.get_all_entries()
        self.table.setRowCount(len(df))
        self.table.setColumnCount(len(df.columns))
        self.table.setHorizontalHeaderLabels(df.columns)
        for i in range(len(df)):
            for j in range(len(df.columns)):
                self.table.setItem(i, j, QtWidgets.QTableWidgetItem(str(df.iat[i, j])))
        self.table.resizeColumnsToContents()

    def add_entry(self):
        """Prompt the user for a new entry and insert it."""
        dialog = EntryDialog(self)
        if dialog.exec_():
            entry = dialog.get_data()
            # Manual entries are assumed to be entered in kg.
            entry["weight_kg"] = float(entry["weight_kg"])
            if self.user_height:
                entry["bmi"] = entry["weight_kg"] / (self.user_height ** 2)
            else:
                entry["bmi"] = None
            self.data_manager.add_entry(entry)
            self.refresh_table()
            self.update_plot()

    def edit_entry(self):
        """Edit the currently selected entry."""
        selected = self.table.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Select Entry", "Please select an entry to edit.")
            return
        row = selected[0].row()
        df = self.data_manager.get_all_entries()
        entry_id = df.iloc[row]['id']
        dialog = EntryDialog(self, prefill=df.iloc[row])
        if dialog.exec_():
            updated_entry = dialog.get_data()
            updated_entry["weight_kg"] = float(updated_entry["weight_kg"])
            if self.user_height:
                updated_entry["bmi"] = updated_entry["weight_kg"] / (self.user_height ** 2)
            else:
                updated_entry["bmi"] = None
            self.data_manager.update_entry(entry_id, updated_entry)
            self.refresh_table()
            self.update_plot()

    def delete_entry(self):
        """Delete the currently selected entry after confirmation."""
        selected = self.table.selectedItems()
        if not selected:
            QtWidgets.QMessageBox.information(self, "Select Entry", "Please select an entry to delete.")
            return
        row = selected[0].row()
        df = self.data_manager.get_all_entries()
        entry_id = df.iloc[row]['id']
        reply = QtWidgets.QMessageBox.question(self, "Delete Entry", "Are you sure you want to delete this entry?",
                                               QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            self.data_manager.delete_entry(entry_id)
            self.refresh_table()
            self.update_plot()

    def update_plot(self):
        """Update the matplotlib plot based on the selected plot type."""
        df = self.data_manager.get_all_entries()
        self.canvas.ax.clear()
        # Convert timestamp column to datetime
        try:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
        except Exception:
            pass

        plot_type = self.plot_combo.currentText()
        if plot_type == "Weight (kg) over Time":
            self.canvas.ax.plot(df['timestamp'], df['weight_kg'], marker='o')
            self.canvas.ax.set_ylabel("Weight (kg)")
        elif plot_type == "BMI over Time":
            self.canvas.ax.plot(df['timestamp'], df['bmi'], marker='o')
            self.canvas.ax.set_ylabel("BMI")
        elif plot_type == "Lean Mass (kg) over Time":
            if 'fat_percent' in df.columns:
                lean_mass = df['weight_kg'] * (1 - df['fat_percent'] / 100)
                self.canvas.ax.plot(df['timestamp'], lean_mass, marker='o')
                self.canvas.ax.set_ylabel("Lean Mass (kg)")
        elif plot_type == "Body Fat (%) over Time":
            self.canvas.ax.plot(df['timestamp'], df['fat_percent'], marker='o')
            self.canvas.ax.set_ylabel("Body Fat (%)")
        self.canvas.ax.set_xlabel("Time")
        self.canvas.ax.set_title(plot_type)
        self.canvas.fig.autofmt_xdate()
        self.canvas.draw()

    def save_settings(self):
        """Store the user's height for BMI calculations."""
        try:
            height = float(self.height_edit.text())
            self.user_height = height
            QtWidgets.QMessageBox.information(self, "Settings Saved", "Height updated.")
        except ValueError:
            QtWidgets.QMessageBox.warning(self, "Invalid Input", "Please enter a valid number for height.")

# Dialog for adding or editing an entry.
class EntryDialog(QtWidgets.QDialog):
    """Dialog used for creating or editing a single entry."""

    def __init__(self, parent=None, prefill=None):
        super(EntryDialog, self).__init__(parent)
        self.setWindowTitle("Entry")
        self.layout = QtWidgets.QFormLayout(self)

        self.logId_edit = QtWidgets.QLineEdit()
        self.date_edit = QtWidgets.QLineEdit()
        self.date_edit.setPlaceholderText("MM/DD/YY")
        self.time_edit = QtWidgets.QLineEdit()
        self.time_edit.setPlaceholderText("HH:MM:SS")
        self.weight_edit = QtWidgets.QLineEdit()
        self.weight_edit.setPlaceholderText("Weight in kg")
        self.fat_edit = QtWidgets.QLineEdit()
        self.fat_edit.setPlaceholderText("Body Fat (%)")
        self.source_edit = QtWidgets.QLineEdit()
        self.source_edit.setPlaceholderText("Manual")

        if prefill is not None:
            self.logId_edit.setText(str(prefill.get("logId", "")))
            self.date_edit.setText(str(prefill.get("date", "")))
            self.time_edit.setText(str(prefill.get("time", "")))
            self.weight_edit.setText(str(prefill.get("weight_kg", "")))
            self.fat_edit.setText(str(prefill.get("fat_percent", "")))
            self.source_edit.setText(str(prefill.get("source", "")))
        self.layout.addRow("Log ID:", self.logId_edit)
        self.layout.addRow("Date (MM/DD/YY):", self.date_edit)
        self.layout.addRow("Time (HH:MM:SS):", self.time_edit)
        self.layout.addRow("Weight (kg):", self.weight_edit)
        self.layout.addRow("Body Fat (%):", self.fat_edit)
        self.layout.addRow("Source:", self.source_edit)

        btns = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        self.buttonBox = QtWidgets.QDialogButtonBox(btns)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        self.layout.addWidget(self.buttonBox)

    def get_data(self):
        """Return the entered data as a dictionary."""
        return {
            "logId": int(self.logId_edit.text()) if self.logId_edit.text().isdigit() else None,
            "date": self.date_edit.text(),
            "time": self.time_edit.text(),
            "weight_kg": self.weight_edit.text(),
            "fat": float(self.fat_edit.text()) if self.fat_edit.text() else None,
            "bmi": None,
            "source": self.source_edit.text() if self.source_edit.text() else "Manual"
        }

if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
