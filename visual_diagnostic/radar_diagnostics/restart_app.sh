#!/bin/bash
pkill -f "python run_app.py"
cd /workspace/visual_diagnostic/radar_diagnostics
python run_app.py --port 8080 &
