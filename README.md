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

## Getting your Fitbit data from Google

If you want to import historical Fitbit measurements, Google provides an export through **Google Takeout**.

1. Visit [Google Takeout](https://takeout.google.com/).
2. Deselect everything and then check **Fitbit**.
3. Follow the prompts to create your export. Google will email you a link when it is ready.
4. Download the exported ZIP file.
5. In the **Entries** page, use the *Import Fitbit ZIP* form to upload the file.
   The importer understands both the older `Weight.csv` file and the newer
   `weight-YYYY-MM-DD.json` files produced by Google Takeout. Any new rows are
   added automatically while existing ones are skipped.

For more details see [Google's help article](https://support.google.com/fitbit/answer/12554576).


FatBit Web replaces the old PyQt desktop application with a more accessible web interface.

The legacy GUI (`FatBit.py`) now supports loading exported data directly from ZIP
archives. Use **Load JSON/ZIP Files** and select your Fitbit export to import all
contained JSON entries automatically.

## Hosting on Raspberry Pi

A helper script `rpi_fatbit.py` is provided to simplify running the web app on a Raspberry Pi. Specify the desired port as an argument or use the optional `--prod` flag to run under gunicorn:

```bash
python rpi_fatbit.py 8080           # development server
python rpi_fatbit.py --prod 8080    # gunicorn, suitable for production
```

If no port is given, the default is 5000. When `--prod` is used the script
launches `gunicorn` with four workers; ensure `gunicorn` is installed first.

## Running on Windows

A convenience script `windows_run.py` simplifies setup on Windows. It installs
required packages using the active Python interpreter and then launches the app
on a chosen port.

```bash
python windows_run.py 8080  # hosts on http://0.0.0.0:8080/
```

If no port is supplied, the default is `5000`.
