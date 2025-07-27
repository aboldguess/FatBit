#!/usr/bin/env python3
"""Run the FatBit web app on a Raspberry Pi.

This helper script can start the built-in Flask development server or
launch a production-grade WSGI server (``gunicorn``) when the
``--prod`` flag is supplied.

Usage:
    python rpi_fatbit.py [--prod] [PORT]

``PORT`` sets the listening port; if omitted, ``5000`` is used.
"""

import argparse
import subprocess

from webapp import app


def parse_args() -> argparse.Namespace:
    """Parse command line options."""
    parser = argparse.ArgumentParser(description="Run FatBit on a Pi")
    parser.add_argument(
        "port",
        nargs="?",
        default=5000,
        type=int,
        help="Port to bind the server on",
    )
    parser.add_argument(
        "--prod",
        action="store_true",
        help="Use gunicorn instead of the Flask development server",
    )
    return parser.parse_args()


def run_prod(port: int) -> None:
    """Launch the app using gunicorn with four workers."""
    try:
        subprocess.check_call(
            ["gunicorn", "-w", "4", "-b", f"0.0.0.0:{port}", "webapp:app"]
        )
    except FileNotFoundError:
        print("gunicorn is not installed. Install it with 'pip install gunicorn'.")


def run_dev(port: int) -> None:
    """Run the Flask development server accessible on the network."""
    app.run(host="0.0.0.0", port=port, debug=False)


def main() -> None:
    """Entry point that chooses production or development mode."""
    args = parse_args()
    if args.prod:
        run_prod(args.port)
    else:
        run_dev(args.port)


if __name__ == "__main__":
    main()
