#!/bin/bash
# Start the Angular development server
cd /workspace/space_game
npm start -- --host 0.0.0.0 --port 4200 --disable-host-check &
# Start the Radar Diagnostics app
cd /workspace/visual_diagnostic/radar_diagnostics
source .venv/bin/activate
python run_app.py --port 8080 --host 0.0.0.0
