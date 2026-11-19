"""Main application layout and tab navigation controller.
"""

import os
from typing import Optional
from nicegui import app, ui

from app.config import default_config
from app.core.session_manager import SessionManager
from app.streaming.recording_manager import RecordingManager
from app.streaming.tcp_client import ConnectionState, RadarTcpClient
from app.ui.comparison import TestComparisonView
from app.ui.file_diagnostics import FileDiagnosticsView
from app.ui.live_stream import LiveStreamView
from app.ui.reports_view import ReportsView
from app.ui.settings_view import SettingsView


class AppLayout:
    """Master layout orchestrator controlling header, navigation tabs, and sub-views."""

    def __init__(
        self,
        session_manager: SessionManager,
        tcp_client: RadarTcpClient,
        recording_manager: RecordingManager,
    ):
        self.session_manager = session_manager
        self.tcp_client = tcp_client
        self.recording_manager = recording_manager

        # Sub-views
        self.file_diag_view = FileDiagnosticsView(
            self.session_manager,
            on_update=self._on_data_updated,
        )
        self.live_stream_view = LiveStreamView(
            self.tcp_client,
            self.recording_manager,
            self.session_manager,
            on_switch_tab=self.switch_to_tab,
        )
        self.comparison_view = TestComparisonView(
            self.session_manager,
            on_update=self._on_data_updated,
        )
        self.reports_view = ReportsView(self.session_manager)
        self.settings_view = SettingsView(
            self.session_manager,
            on_update=self._on_data_updated,
        )

        self.tabs_component = None
        self.header_conn_badge = None
        self.header_rec_badge = None
        self.header_source_badge = None

    def build_ui(self):
        """Construct the entire application DOM."""
        # Include custom CSS
        css_path = os.path.join(default_config.base_dir, "app", "static", "styles.css")
        if os.path.isfile(css_path):
            with open(css_path, "r") as f:
                ui.add_head_html(f"<style>{f.read()}</style>")

        # 1. Global Persistent Blue Header (approx 62px tall)
        with ui.header().classes("app-header"):
            with ui.row().classes("items-center gap-3"):
                ui.icon("radar", size="30px", color="white")
                ui.label("PSP RADAR DIAGNOSTICS").classes("app-title")
                ui.label("Laboratory Analysis & Live Monitoring Platform").classes("text-xs text-blue-100 hidden sm:block")

            with ui.row().classes("items-center gap-4"):
                # Data Source Indicator
                with ui.row().classes("items-center gap-1"):
                    ui.label("Source:").classes("text-xs font-semibold opacity-80")
                    self.header_source_badge = ui.label("CSV").classes("status-badge bg-blue-900 text-white")

                # Connection Indicator
                with ui.row().classes("items-center gap-1"):
                    ui.label("TCP:").classes("text-xs font-semibold opacity-80")
                    self.header_conn_badge = ui.label("DISCONNECTED").classes("status-badge status-disconnected")

                # Recording Indicator
                with ui.row().classes("items-center gap-1"):
                    ui.label("Recording:").classes("text-xs font-semibold opacity-80")
                    self.header_rec_badge = ui.label("OFF").classes("status-badge bg-gray-600 text-white")

                ui.separator().props("vertical").classes("h-6 bg-blue-300 opacity-50")
                ui.label(f"Session: {self.session_manager.session_name}").classes("text-xs font-semibold")

        # 2. Main Navigation Tabs
        with ui.tabs().classes("w-full q-tabs") as self.tabs_component:
            self.tab_file_diag = ui.tab("File Diagnostics", icon="analytics")
            self.tab_live_stream = ui.tab("Live Stream & Recording", icon="stream")
            self.tab_comparison = ui.tab("Test Comparison", icon="compare_arrows")
            self.tab_reports = ui.tab("Reports & Exports", icon="assessment")
            self.tab_settings = ui.tab("Settings", icon="tune")

        # 3. Tab Panels
        with ui.tab_panels(self.tabs_component, value=self.tab_file_diag).classes("w-full"):
            with ui.tab_panel(self.tab_file_diag).classes("p-0"):
                self.file_diag_view.render()

            with ui.tab_panel(self.tab_live_stream).classes("p-0"):
                self.live_stream_view.render()

            with ui.tab_panel(self.tab_comparison).classes("p-0"):
                self.comparison_view.render()

            with ui.tab_panel(self.tab_reports).classes("p-0"):
                self.reports_view.render()

            with ui.tab_panel(self.tab_settings).classes("p-0"):
                self.settings_view.render()

        # Header status updater timer
        ui.timer(1.0, self._update_header_status)

    def switch_to_tab(self, tab_name: str):
        """Programmatically switch active tab."""
        tab_map = {
            "file_diagnostics": self.tab_file_diag,
            "live_stream": self.tab_live_stream,
            "comparison": self.tab_comparison,
            "reports": self.tab_reports,
            "settings": self.tab_settings,
        }
        if tab_name in tab_map and self.tabs_component:
            self.tabs_component.value = tab_map[tab_name]

    def _update_header_status(self):
        """Update badges in global header."""
        # Connection
        if self.tcp_client.is_connected:
            self.header_conn_badge.text = "CONNECTED"
            self.header_conn_badge.classes("status-connected", remove="status-disconnected bg-amber-600 bg-red-600")
            self.header_source_badge.text = "LIVE TCP"
            self.header_source_badge.classes("bg-green-800 text-white", remove="bg-blue-900")
        elif self.tcp_client.state == ConnectionState.CONNECTING:
            self.header_conn_badge.text = "CONNECTING"
            self.header_conn_badge.classes("bg-amber-600 text-white", remove="status-connected status-disconnected")
        elif self.tcp_client.state == ConnectionState.ERROR:
            self.header_conn_badge.text = "ERROR"
            self.header_conn_badge.classes("bg-red-600 text-white", remove="status-connected status-disconnected")
        else:
            self.header_conn_badge.text = "DISCONNECTED"
            self.header_conn_badge.classes("status-disconnected", remove="status-connected bg-amber-600 bg-red-600")
            self.header_source_badge.text = "CSV"
            self.header_source_badge.classes("bg-blue-900 text-white", remove="bg-green-800")

        # Recording
        if self.recording_manager.is_recording:
            self.header_rec_badge.text = "REC ON"
            self.header_rec_badge.classes("status-recording", remove="bg-gray-600")
        else:
            self.header_rec_badge.text = "OFF"
            self.header_rec_badge.classes("bg-gray-600 text-white", remove="status-recording")

    def _on_data_updated(self):
        """Propagate state change to all diagnostic views."""
        self.file_diag_view.refresh()
        self.comparison_view.refresh()
        self.reports_view.refresh()
