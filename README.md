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
4. Download the exported ZIP and extract it. The weight log is located in `Takeout/Fitbit/Weight/Weight.csv`.
5. Import the CSV contents into FatBit using the entries page or by inserting the rows into the SQLite database.

For more details see [Google's help article](https://support.google.com/fitbit/answer/12554576).


FatBit Web replaces the old PyQt desktop application with a more accessible web interface.
