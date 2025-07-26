# FatBit Web

FatBit Web is a lightweight Flask application for tracking your weight and body fat measurements. Data is stored in a local SQLite database and visualised using Matplotlib. The interface lets you add, edit and delete entries as well as view basic plots and set your height for BMI calculations.

## Setup

1. **Install Python dependencies**
   ```bash
   pip install -r requirements.txt
   ```
2. **Run the application**
   ```bash
   python webapp.py
   ```
   The app runs on `http://127.0.0.1:5000/` by default.

## Deployment

For production deployment you can use any WSGI server such as `gunicorn`:

```bash
pip install gunicorn
gunicorn -w 4 webapp:app
```

Gunicorn requires a Unix-like environment. On Windows you can either run the
application directly with `python webapp.py` or use a WSGI server that supports
Windows, such as `waitress`.

Ensure the `weight_data.db` file is persisted between runs.

## Usage

- Navigate to the **Entries** page to add new measurements.
- Use **Plots** to see weight, BMI and other charts.
- Set your height in **Settings** to calculate BMI automatically.

FatBit Web replaces the old PyQt desktop application with a more accessible web interface.
