#!/usr/bin/env python3
"""Launcher for the PSP Radar Diagnostics GUI web application.
"""

import argparse
import os
import sys

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from app.config import default_config
import app.main  # Import to register routes and handlers
from nicegui import ui


import multiprocessing

def main():
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description="Launch PSP Radar Diagnostics Platform GUI")
    parser.add_argument("--host", default=default_config.gui_host, help="Bind host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=default_config.gui_port, help="Port to serve (default: 8080)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload on code change")
    args, _ = parser.parse_known_args()

    print(f"===========================================================")
    print(f" PSP Radar Diagnostics & Live Monitoring Platform")
    print(f" Dashboard URL: http://{args.host}:{args.port}")
    print(f" Default Simulated TCP Server Port: {default_config.tcp_server_port}")
    print(f"===========================================================")

    ui.run(
        host=args.host,
        port=args.port,
        title="PSP Radar Diagnostics",
        favicon="📡",
        show=False,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
