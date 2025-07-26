#!/bin/bash
# run_rpi.sh - Convenience script to host the FatBit web app on a Raspberry Pi.
#
# Usage: ./run_rpi.sh [PORT]
# If PORT is not provided, the app runs on 5000 by default.
#
# The script installs required Python packages (for the current user) and
# launches the Flask development server bound to all network interfaces so the
# application is reachable over the local network.
#
# Note: For production deployment you should use a WSGI server like gunicorn.

set -e

# Read the desired port from the first argument, defaulting to 5000 if omitted
PORT=${1:-5000}

# Install Python dependencies
pip install --user -r requirements.txt

# Tell Flask which application to run
export FLASK_APP=webapp

# Start the Flask development server accessible from other machines
flask run --host 0.0.0.0 --port "$PORT"
