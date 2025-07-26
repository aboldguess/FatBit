#!/usr/bin/env python3
"""Simple helper script to host the FatBit web application on a Raspberry Pi.

Usage:
    python rpi_server.py [PORT]

When a PORT is provided, the app will bind to that port on all interfaces
(`0.0.0.0`). If no port is specified, 5000 is used by default.

This script can be run after installing the requirements with
```
pip install -r requirements.txt
```
"""

import sys

from webapp import app


def main():
    """Entry point for the Raspberry Pi server runner."""
    port = 5000
    if len(sys.argv) > 1:
        try:
            # Read port number from the first command line argument
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}. Using default {port}.")

    # Run the Flask application accessible on the network
    # ``host='0.0.0.0'`` exposes it to other machines on the LAN
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
