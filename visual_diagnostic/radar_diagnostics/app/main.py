"""Main application entry point initializing NiceGUI and FastAPI.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from nicegui import app, ui

from app.config import default_config
from app.core.session_manager import SessionManager
from app.streaming.recording_manager import RecordingManager
from app.streaming.tcp_client import RadarTcpClient
from app.ui.layout import AppLayout


# Initialize core singletons
session_manager = SessionManager(session_name="PSP_Lab_Session")
tcp_client = RadarTcpClient(
    host="127.0.0.1",
    port=default_config.tcp_server_port,
    timeout_seconds=default_config.tcp_timeout_seconds,
    buffer_max_frames=default_config.live_buffer_max_frames,
)
recording_manager = RecordingManager(base_recordings_dir=default_config.recordings_dir)

# Mount static directories for reports and assets
os.makedirs(default_config.reports_dir, exist_ok=True)
app.mount("/reports", StaticFiles(directory=default_config.reports_dir), name="reports")

static_dir = os.path.join(default_config.base_dir, "app", "static")
game_dir = os.path.join(default_config.base_dir, "app", "game")
if os.path.isdir(game_dir):
    app.mount("/game", StaticFiles(directory=game_dir, html=True), name="game")

if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@ui.page("/")
def index_page():
    """Main dashboard page."""
    ui.page_title("PSP Radar Diagnostics & Live Monitoring")
    ui.query(".nicegui-content").classes("p-0 m-0 w-full max-w-full h-screen max-h-screen overflow-hidden items-stretch gap-0")
    layout = AppLayout(
        session_manager=session_manager,
        tcp_client=tcp_client,
        recording_manager=recording_manager,
    )
    layout.build_ui()


@app.on_event("shutdown")
async def on_shutdown():
    """Clean up active network connections and recordings on server stop."""
    if tcp_client.is_connected:
        await tcp_client.disconnect()
    if recording_manager.is_recording:
        recording_manager.stop_recording()
