"""Main application layout featuring modern collapsible dark navy sidebar,
slim header with compact telemetry indicators, and responsive workspace canvas.
"""

import os
from typing import Dict, Optional
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
    """Master layout orchestrator controlling sidebar navigation, slim header, and views."""

    PAGES = {
        "file_diagnostics": {
            "title": "File Diagnostics",
            "subtitle": "Analyze radar measurements across elements, frequencies, and test runs.",
            "icon": "analytics",
        },
        "live_stream": {
            "title": "Live Monitoring",
            "subtitle": "Real-time radar telemetry streaming, high-frequency recording, and matrix inspection.",
            "icon": "sensors",
        },
        "comparison": {
            "title": "Test Comparison",
            "subtitle": "Cross-test delta evaluations, element drift, and frequency stability analysis.",
            "icon": "compare_arrows",
        },
        "reports": {
            "title": "Reports & Exports",
            "subtitle": "Generate laboratory diagnostics HTML summaries and export measurement CSVs.",
            "icon": "description",
        },
        "settings": {
            "title": "Settings & Thresholds",
            "subtitle": "Configure amplitude/noise bounds, phase unwrapping, and MAD outlier sensitivity.",
            "icon": "tune",
        },
    }

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

        self.current_page_key = "file_diagnostics"
        self.is_sidebar_collapsed = False

        # DOM References
        self.sidebar_elem = None
        self.sidebar_brand_text = None
        self.nav_buttons: Dict[str, ui.element] = {}
        self.nav_labels: Dict[str, ui.element] = {}
        self.view_containers: Dict[str, ui.column] = {}

        self.header_page_title = None
        self.header_source_text = None
        self.header_tcp_dot = None
        self.header_tcp_text = None
        self.header_rec_dot = None
        self.header_rec_text = None

    def build_ui(self):
        """Construct the entire application DOM."""
        # Include custom CSS tokens and font styles
        css_path = os.path.join(default_config.base_dir, "app", "static", "styles.css")
        if os.path.isfile(css_path):
            with open(css_path, "r") as f:
                ui.add_head_html(f"<style>{f.read()}</style>")

        # Root Application Shell (Full browser width & height, zero outer margins)
        with ui.row().classes("app-shell no-wrap p-0 m-0 w-full h-screen max-h-screen overflow-hidden items-stretch"):
            # 1. Collapsible Dark Navy Sidebar (Touches absolute left edge)
            with ui.column().classes("app-sidebar p-0 m-0") as self.sidebar_elem:
                # Brand Header
                with ui.row().classes("sidebar-brand no-wrap w-full items-center"):
                    ui.icon("radar", size="26px", color="white").classes("flex-shrink-0")
                    self.sidebar_brand_text = ui.label("PSP Radar Diagnostics").classes("sidebar-brand-title")

                # Navigation Menu Items
                with ui.column().classes("sidebar-nav"):
                    for key, info in self.PAGES.items():
                        is_active = (key == self.current_page_key)
                        active_cls = "nav-item nav-item--active" if is_active else "nav-item"
                        with ui.row().classes(f"{active_cls} no-wrap w-full") as nav_row:
                            ui.icon(info["icon"], size="20px").classes("flex-shrink-0")
                            lbl = ui.label(info["title"]).classes("text-sm flex-grow")
                            self.nav_labels[key] = lbl
                            nav_row.on("click", lambda _, k=key: self.switch_to_tab(k))
                            self.nav_buttons[key] = nav_row

                # Sidebar Collapse Toggle Footer
                with ui.row().classes("sidebar-footer w-full justify-end items-center"):
                    self.btn_collapse = ui.button(
                        icon="menu_open",
                        on_click=self._toggle_sidebar,
                    ).props("flat round dense").classes("text-slate-400 hover:text-white").tooltip("Toggle sidebar width")

            # 2. Main Viewport (Spans all remaining horizontal space from sidebar to right edge)
            with ui.column().classes("main-viewport p-0 m-0 w-full min-w-0 items-stretch"):
                # Professional Full-Width Top Header (64px tall, stretches to very right edge)
                with ui.row().classes("top-header w-full justify-between items-center no-wrap"):
                    # Left: Dynamically updated page title
                    cur_info = self.PAGES[self.current_page_key]
                    self.header_page_title = ui.label(cur_info["title"]).classes("header-page-title")

                    # Right: Status Indicators (SOURCE, CONNECTED/DISCONNECTED, REC: ON/OFF)
                    with ui.row().classes("items-center gap-3 no-wrap"):
                        # 1. Source Indicator
                        with ui.row().classes("header-status-item no-wrap"):
                            self.header_source_text = ui.label("SOURCE: CSV").classes("header-status-text")

                        # 2. Connection Indicator
                        with ui.row().classes("header-status-item no-wrap"):
                            self.header_tcp_dot = ui.element("span").classes("status-dot dot-disconnected")
                            self.header_tcp_text = ui.label("DISCONNECTED").classes("header-status-text")

                        # 3. Recording Indicator
                        with ui.row().classes("header-status-item no-wrap"):
                            self.header_rec_dot = ui.element("span").classes("status-dot")
                            self.header_rec_text = ui.label("REC: OFF").classes("header-status-text")

                # Main Content Canvas (Fills full width, no artificial max-width constraints)
                with ui.column().classes("content-canvas w-full min-w-0 items-stretch"):
                    # Page 1: File Diagnostics
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["file_diagnostics"]:
                        self.file_diag_view.render()

                    # Page 2: Live Monitoring
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["live_stream"]:
                        self.live_stream_view.render()

                    # Page 3: Test Comparison
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["comparison"]:
                        self.comparison_view.render()

                    # Page 4: Reports & Exports
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["reports"]:
                        self.reports_view.render()

                    # Page 5: Settings & Thresholds
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["settings"]:
                        self.settings_view.render()

        # Set initial visibility
        self._update_view_visibility()

        # Periodic header telemetry timer (1 Hz)
        ui.timer(1.0, self._update_header_status)

    def switch_to_tab(self, page_key: str):
        """Programmatically switch active page and update UI indicators."""
        if page_key in self.PAGES:
            self.current_page_key = page_key

            # Update header page title dynamically
            page_info = self.PAGES[page_key]
            if self.header_page_title:
                self.header_page_title.text = page_info["title"]

            # Update sidebar active nav styling
            for key, btn in self.nav_buttons.items():
                if key == page_key:
                    btn.classes("nav-item--active", remove="text-slate-400")
                else:
                    btn.classes(remove="nav-item--active")

            # Update visibility of view containers
            self._update_view_visibility()

    def _update_view_visibility(self):
        """Toggle DOM visibility between views without re-mounting components."""
        for key, container in self.view_containers.items():
            container.set_visibility(key == self.current_page_key)

    def _toggle_sidebar(self):
        """Collapse or expand the left navigation sidebar."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        if self.is_sidebar_collapsed:
            self.sidebar_elem.classes("sidebar--collapsed")
            self.sidebar_brand_text.set_visibility(False)
            self.btn_collapse.props("icon=menu")
            for lbl in self.nav_labels.values():
                lbl.set_visibility(False)
        else:
            self.sidebar_elem.classes(remove="sidebar--collapsed")
            self.sidebar_brand_text.set_visibility(True)
            self.btn_collapse.props("icon=menu_open")
            for lbl in self.nav_labels.values():
                lbl.set_visibility(True)

    def _update_header_status(self):
        """Update telemetry badges in top header."""
        if not self.header_tcp_text or not self.header_source_text:
            return

        # Source & Connection Status
        if self.tcp_client.is_connected:
            self.header_source_text.text = "SOURCE: LIVE TCP"
            self.header_source_text.classes("text-emerald-700 font-bold", remove="text-slate-700 font-semibold")
            self.header_tcp_text.text = "CONNECTED"
            self.header_tcp_text.classes("text-emerald-700 font-bold", remove="text-slate-600 text-amber-600")
            self.header_tcp_dot.classes("dot-connected", remove="dot-disconnected dot-connecting dot-error")
        elif self.tcp_client.state == ConnectionState.CONNECTING:
            self.header_source_text.text = "SOURCE: CSV"
            self.header_source_text.classes("text-slate-700 font-semibold", remove="text-emerald-700 font-bold")
            self.header_tcp_text.text = "CONNECTING"
            self.header_tcp_text.classes("text-amber-600 font-semibold", remove="text-emerald-700 text-slate-600")
            self.header_tcp_dot.classes("dot-connecting", remove="dot-connected dot-disconnected dot-error")
        elif self.tcp_client.state == ConnectionState.ERROR:
            self.header_source_text.text = "SOURCE: CSV"
            self.header_source_text.classes("text-slate-700 font-semibold", remove="text-emerald-700 font-bold")
            self.header_tcp_text.text = "DISCONNECTED"
            self.header_tcp_text.classes("text-slate-600 font-semibold", remove="text-emerald-700 text-amber-600")
            self.header_tcp_dot.classes("dot-error", remove="dot-connected dot-disconnected dot-connecting")
        else:
            self.header_source_text.text = "SOURCE: CSV"
            self.header_source_text.classes("text-slate-700 font-semibold", remove="text-emerald-700 font-bold")
            self.header_tcp_text.text = "DISCONNECTED"
            self.header_tcp_text.classes("text-slate-600 font-semibold", remove="text-emerald-700 text-amber-600")
            self.header_tcp_dot.classes("dot-disconnected", remove="dot-connected dot-connecting dot-error")

        # Recording Status
        if self.recording_manager.is_recording:
            self.header_rec_text.text = "REC: ON"
            self.header_rec_text.classes("text-red-600 font-bold", remove="text-slate-600 font-semibold")
            self.header_rec_dot.classes("dot-recording")
        else:
            self.header_rec_text.text = "REC: OFF"
            self.header_rec_text.classes("text-slate-600 font-semibold", remove="text-red-600 font-bold")
            self.header_rec_dot.classes(remove="dot-recording")

    def _on_data_updated(self):
        """Propagate state change to all diagnostic views."""
        self.file_diag_view.refresh()
        self.comparison_view.refresh()
        self.reports_view.refresh()
