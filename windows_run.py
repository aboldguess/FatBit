#!/usr/bin/env python3
"""Utility to set up and run the FatBit web app on Windows.

This script installs required dependencies and launches the Flask
application bound to all network interfaces on a chosen port.

Usage::

    python windows_run.py [PORT]

When ``PORT`` is provided, the server will listen on that port.
If omitted, 5000 is used by default.
"""

import os
import subprocess
import sys


def main():
    """Install dependencies and start the Flask app."""
    port = 5000
    if len(sys.argv) > 1:
        try:
            # Parse the desired port from command line
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}. Using default {port}.")

    # Ensure required Python packages are installed. Using the running
    # Python interpreter guarantees that packages end up in the correct
    # environment.
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

    # DataManager in webapp.py creates the SQLite schema on first run, so
    # there is no separate database migration step. We simply start Flask.
    env = os.environ.copy()
    env["FLASK_APP"] = "webapp"

    print(f"Launching FatBit on port {port}...")
    subprocess.check_call([sys.executable, "-m", "flask", "run", "--host", "0.0.0.0", "--port", str(port)], env=env)


if __name__ == "__main__":
    main()
