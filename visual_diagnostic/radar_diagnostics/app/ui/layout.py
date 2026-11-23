"""PSP Radar Diagnostics application shell.

Supports two interchangeable navigation modes:
  * Top tabs with the PNG brand at the top-left of the header.
  * Collapsible dark sidebar with the same PNG brand at its top-left.

Both navigators switch the *same* mounted view containers, so changing layout
never recreates charts, data sessions, or live-stream/recording components.
"""

import os
from typing import Dict, Literal

from nicegui import ui

from app.config import default_config
from app.core.session_manager import SessionManager
from app.streaming.recording_manager import RecordingManager
from app.streaming.tcp_client import ConnectionState, RadarTcpClient
from app.ui.comparison import TestComparisonView
from app.ui.file_diagnostics import FileDiagnosticsView
from app.ui.live_stream import LiveStreamView
from app.ui.reports_view import ReportsView
from app.ui.settings_view import SettingsView


# Deliberately loaded after existing styles.css, so the new shell can override
# old width, margin, and flex settings without changing any radar-specific CSS.
NAVIGATION_CSS = r"""
:root {
    --psp-navy: #101d32;
    --psp-sidebar-active: #1e3b61;
    --psp-accent: #2563eb;
    --psp-canvas: #f4f7fb;
    --psp-divider: #e2e8f0;
    --psp-text: #142338;
    --psp-muted: #64748b;
}
html, body, #q-app {
    width: 100%;
    min-height: 100%;
    margin: 0 !important;
    padding: 0 !important;
    overflow-x: hidden;
}
.nicegui-content {
    padding: 0 !important;
    margin: 0 !important;
    width: 100% !important;
    max-width: none !important;
    min-height: 100dvh;
}
.dual-nav-shell.app-shell {
    display: flex !important;
    flex-direction: row !important;
    align-items: stretch !important;
    gap: 0 !important;
    width: 100% !important;
    max-width: none !important;
    height: 100dvh !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    overflow: hidden !important;
}
.dual-sidebar.app-sidebar {
    flex: 0 0 236px !important;
    width: 236px !important;
    min-width: 236px !important;
    height: 100dvh !important;
    min-height: 0 !important;
    gap: 0 !important;
    padding: 0 !important;
    margin: 0 !important;
    background: var(--psp-navy);
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: width .18s ease, flex-basis .18s ease, min-width .18s ease;
}
.dual-sidebar.app-sidebar.sidebar--collapsed {
    flex-basis: 68px !important;
    width: 68px !important;
    min-width: 68px !important;
}
.dual-sidebar-brand {
    width: 100%;
    height: 66px;
    min-height: 66px;
    padding: 0 16px;
    display: flex;
    align-items: center;
    overflow: hidden;
    border-bottom: 1px solid rgba(255, 255, 255, .09);
}
.dual-sidebar.app-sidebar.sidebar--collapsed .dual-sidebar-brand {
    padding: 0 16px;
}
.dual-sidebar-logo-wrap {
    flex-shrink: 0;
    width: 204px;
    height: 36px;
    overflow: hidden;
}
.dual-sidebar.app-sidebar.sidebar--collapsed .dual-sidebar-logo-wrap {
    width: 36px;
}
.dual-sidebar-logo {
    width: 204px !important;
    height: 36px !important;
    max-width: none !important;
}
.dual-sidebar-nav {
    width: 100%;
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    gap: 3px !important;
    padding: 24px 12px;
}
.dual-sidebar-nav .dual-side-link.nav-item {
    width: 100%;
    min-height: 40px;
    padding: 0 12px !important;
    display: flex;
    align-items: center;
    gap: 12px !important;
    color: #a9bdd8;
    border-radius: 9px;
    cursor: pointer;
    user-select: none;
    transition: background .15s, color .15s;
}
.dual-sidebar-nav .dual-side-link.nav-item:hover,
.dual-sidebar-nav .dual-side-link.nav-item:focus-visible {
    background: rgba(255, 255, 255, .09);
    color: #fff;
    outline: none;
}
.dual-sidebar-nav .dual-side-link.nav-item.nav-item--active {
    background: var(--psp-sidebar-active);
    color: #fff;
    box-shadow: inset 3px 0 0 var(--psp-accent);
}
.dual-sidebar.app-sidebar.sidebar--collapsed .dual-sidebar-nav {
    padding-left: 10px;
    padding-right: 10px;
}
.dual-sidebar.app-sidebar.sidebar--collapsed .dual-side-link.nav-item {
    justify-content: center;
    padding: 0 8px !important;
}
.dual-sidebar-footer {
    width: 100%;
    min-height: 48px;
    padding: 6px 12px;
    display: flex;
    align-items: center;
    justify-content: flex-end;
    border-top: 1px solid rgba(255, 255, 255, .09);
}
.dual-main.main-viewport {
    flex: 1 1 0% !important;
    width: auto !important;
    min-width: 0 !important;
    max-width: none !important;
    height: 100dvh !important;
    min-height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
    gap: 0 !important;
    background: var(--psp-canvas);
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
.dual-top-header.top-header {
    flex: 0 0 auto;
    min-height: 64px;
    width: 100% !important;
    max-width: none !important;
    padding: 0 24px !important;
    margin: 0 !important;
    background: #fff;
    border-bottom: 1px solid var(--psp-divider);
    display: flex;
    flex-wrap: nowrap;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
}
.dual-header-left,
.dual-header-right,
.dual-header-statuses {
    display: flex;
    align-items: center;
    gap: 14px;
    min-width: 0;
}
.dual-header-left { flex: 1 1 auto; }
.dual-header-right { flex: 0 1 auto; justify-content: flex-end; }
.dual-header-brand {
    display: flex;
    align-items: center;
    height: 44px;
    width: 205px;
    flex: 0 0 auto;
    overflow: hidden;
}
.dual-header-brand-logo {
    width: 205px !important;
    height: 36px !important;
    max-width: none !important;
}
.dual-header-title.header-page-title {
    font-size: 18px;
    font-weight: 650;
    color: var(--psp-text);
    white-space: nowrap;
}
.dual-header-statuses .header-status-item {
    display: flex;
    align-items: center;
    gap: 6px;
    white-space: nowrap;
    background: #f8fafc;
    border: 1px solid var(--psp-divider);
    border-radius: 100px;
    padding: 5px 10px;
}
.dual-header-statuses .header-status-text {
    font-size: 11px;
    letter-spacing: .02em;
    white-space: nowrap;
}
.dual-mode-switch {
    display: flex;
    align-items: center;
    flex-wrap: nowrap;
    gap: 4px;
    border: 1px solid var(--psp-divider);
    background: #f8fafc;
    padding: 3px;
    border-radius: 9px;
}
.dual-mode-switch .q-btn.dual-mode-button {
    min-height: 30px;
    padding: 0 9px;
    color: #64748b;
    border-radius: 6px;
    font-size: 12px;
    box-shadow: none;
}
.dual-mode-switch .q-btn.dual-mode-button.mode-active {
    background: #fff;
    color: #1d4ed8;
    box-shadow: 0 1px 4px #0f172a16;
}
.dual-top-tabs {
    flex: 0 0 52px;
    width: 100%;
    min-height: 52px;
    display: flex;
    align-items: stretch;
    gap: 2px;
    padding: 0 16px;
    overflow-x: auto;
    overflow-y: hidden;
    white-space: nowrap;
    background: #fff;
    border-bottom: 1px solid var(--psp-divider);
}
.dual-top-tabs .q-btn.dual-tab-button {
    flex-shrink: 0;
    border-radius: 0;
    border-bottom: 3px solid transparent;
    min-height: 52px;
    padding: 0 16px;
    font-size: 13px;
    font-weight: 500;
    color: var(--psp-muted);
    box-shadow: none;
}
.dual-top-tabs .q-btn.dual-tab-button:hover {
    color: var(--psp-accent);
    background: #f8fbff;
}
.dual-top-tabs .q-btn.dual-tab-button.dual-tab-active {
    color: #1d4ed8;
    background: #f4f8ff;
    border-bottom-color: var(--psp-accent);
    font-weight: 600;
}
.dual-content.content-canvas {
    flex: 1 1 auto !important;
    min-height: 0 !important;
    min-width: 0 !important;
    max-width: none !important;
    width: 100% !important;
    overflow-x: hidden !important;
    overflow-y: auto !important;
    margin: 0 !important;
    padding: 20px 22px !important;
    gap: 0 !important;
    align-items: stretch;
}
.dual-content > * { min-width: 0; max-width: 100%; }
@media (max-width: 1060px) {
    .dual-top-header.top-header { flex-wrap: wrap; padding: 10px 16px !important; }
    .dual-header-left { min-width: 0; }
    .dual-header-right { width: 100%; justify-content: space-between; flex-wrap: wrap; }
    .dual-content.content-canvas { padding: 14px !important; }
}
@media (max-width: 720px) {
    .dual-top-header.top-header { gap: 8px; }
    .dual-header-statuses { gap: 5px; flex-wrap: wrap; }
    .dual-header-brand { width: 160px; }
    .dual-header-brand-logo { width: 205px !important; }
    .dual-header-title.header-page-title { font-size: 16px; }
    .dual-top-tabs { padding: 0 8px; }
    .dual-top-tabs .q-btn.dual-tab-button { padding: 0 10px; }
}
"""


class AppLayout:
    """Shared application state and two interchangeable navigation layouts."""

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
        initial_navigation_mode: Literal["tabs", "sidebar"] = "sidebar",
    ):
        self.session_manager = session_manager
        self.tcp_client = tcp_client
        self.recording_manager = recording_manager

        # Keep the existing view objects. Never recreate them while switching layout.
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
        self.navigation_mode = initial_navigation_mode if initial_navigation_mode in ("tabs", "sidebar") else "tabs"
        self.is_sidebar_collapsed = False

        self.sidebar_elem = None
        self.sidebar_logo = None
        self.top_tabs_bar = None
        self.header_brand = None
        self.sidebar_mode_button = None
        self.tabs_mode_button = None
        self.btn_collapse = None

        self.nav_buttons: Dict[str, ui.element] = {}
        self.nav_labels: Dict[str, ui.element] = {}
        self.tab_buttons: Dict[str, ui.button] = {}
        self.view_containers: Dict[str, ui.column] = {}

        self.header_page_title = None
        self.header_source_text = None
        self.header_tcp_dot = None
        self.header_tcp_text = None
        self.header_rec_dot = None
        self.header_rec_text = None

    def build_ui(self):
        """Create both navigation controls and one shared set of content views."""
        css_path = os.path.join(default_config.base_dir, "app", "static", "styles.css")
        if os.path.isfile(css_path):
            with open(css_path, "r", encoding="utf-8") as css_file:
                ui.add_head_html(f"<style>{css_file.read()}</style>")

        ui.add_head_html(f"<style>{NAVIGATION_CSS}</style>")

        with ui.row().classes("app-shell dual-nav-shell no-wrap p-0 m-0"):
            # SIDEBAR MODE: PNG logo is anchored in the upper-left corner.
            with ui.column().classes("app-sidebar dual-sidebar") as self.sidebar_elem:
                with ui.row().classes("dual-sidebar-brand"):
                    with ui.element("div").classes("dual-sidebar-logo-wrap"):
                        self.sidebar_logo = ui.image("/static/logo.png").classes("dual-sidebar-logo")

                with ui.column().classes("sidebar-nav dual-sidebar-nav"):
                    for key, info in self.PAGES.items():
                        with ui.row().classes("nav-item dual-side-link no-wrap") as item:
                            ui.icon(info["icon"], size="19px").classes("flex-shrink-0")
                            label = ui.label(info["title"]).classes("text-sm flex-grow")
                            self.nav_labels[key] = label
                            item.on("click", lambda _, k=key: self.switch_to_tab(k))
                            item.on("keydown.enter", lambda _, k=key: self.switch_to_tab(k))
                            item.props("tabindex=0 role=button")
                            self.nav_buttons[key] = item

                with ui.row().classes("sidebar-footer dual-sidebar-footer"):
                    self.btn_collapse = ui.button(
                        icon="menu_open", on_click=self._toggle_sidebar,
                    ).props("flat round dense").classes("text-slate-300").tooltip("Collapse or expand sidebar")

            # The main viewport expands to 100% width in top-tabs mode.
            with ui.column().classes("main-viewport dual-main"):
                # SHARED HEADER: PNG logo is visible here in top-tabs mode.
                with ui.row().classes("top-header dual-top-header"):
                    with ui.row().classes("dual-header-left no-wrap"):
                        with ui.row().classes("dual-header-brand") as self.header_brand:
                            ui.image("/workspace/visual_diagnostic/radar_diagnostics/app/ui/6419_logo_-_black-removebg.png").classes("dual-header-brand-logo")
                        self.header_page_title = ui.label(
                            self.PAGES[self.current_page_key]["title"]
                        ).classes("header-page-title dual-header-title")

                    with ui.row().classes("dual-header-right"):
                        with ui.row().classes("dual-header-statuses"):
                            with ui.row().classes("header-status-item no-wrap"):
                                self.header_source_text = ui.label("SOURCE: CSV").classes("header-status-text")
                            with ui.row().classes("header-status-item no-wrap"):
                                self.header_tcp_dot = ui.element("span").classes("status-dot dot-disconnected")
                                self.header_tcp_text = ui.label("DISCONNECTED").classes("header-status-text")
                            with ui.row().classes("header-status-item no-wrap"):
                                self.header_rec_dot = ui.element("span").classes("status-dot")
                                self.header_rec_text = ui.label("REC: OFF").classes("header-status-text")

                        # Visible and functional in BOTH layouts.
                        with ui.row().classes("dual-mode-switch"):
                            self.tabs_mode_button = ui.button(
                                "Tabs", icon="tab", on_click=lambda: self.set_navigation_mode("tabs")
                            ).props("flat no-caps dense").classes("dual-mode-button").tooltip("Top tabs navigation")
                            self.sidebar_mode_button = ui.button(
                                "Sidebar", icon="view_sidebar", on_click=lambda: self.set_navigation_mode("sidebar")
                            ).props("flat no-caps dense").classes("dual-mode-button").tooltip("Sidebar navigation")

                # TOP TABS MODE: clickable navigation appears beneath the header.
                with ui.row().classes("dual-top-tabs no-wrap") as self.top_tabs_bar:
                    for key, info in self.PAGES.items():
                        self.tab_buttons[key] = ui.button(
                            info["title"],
                            icon=info["icon"],
                            on_click=lambda _, k=key: self.switch_to_tab(k),
                        ).props("flat no-caps").classes("dual-tab-button")

                # IMPORTANT: The 5 pages are only rendered once, in shared containers.
                with ui.column().classes("content-canvas dual-content"):
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["file_diagnostics"]:
                        self.file_diag_view.render()
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["live_stream"]:
                        self.live_stream_view.render()
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["comparison"]:
                        self.comparison_view.render()
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["reports"]:
                        self.reports_view.render()
                    with ui.column().classes("w-full gap-4 min-w-0 items-stretch") as self.view_containers["settings"]:
                        self.settings_view.render()

        self._update_view_visibility()
        self._sync_active_navigation()
        self._apply_navigation_mode(resize=False)
        self._update_header_status()
        ui.timer(1.0, self._update_header_status)

    def set_navigation_mode(self, mode: Literal["tabs", "sidebar"]):
        """Switch navigation chrome without recreating the active page."""
        if mode not in ("tabs", "sidebar"):
            raise ValueError("Navigation mode must be 'tabs' or 'sidebar'")
        self.navigation_mode = mode
        self._apply_navigation_mode()

    def _apply_navigation_mode(self, resize: bool = True):
        if self.sidebar_elem is None:
            return
        using_sidebar = self.navigation_mode == "sidebar"
        self.sidebar_elem.set_visibility(using_sidebar)
        self.top_tabs_bar.set_visibility(not using_sidebar)
        self.header_brand.set_visibility(not using_sidebar)
        if using_sidebar:
            self.sidebar_mode_button.classes(add="mode-active")
            self.tabs_mode_button.classes(remove="mode-active")
        else:
            self.tabs_mode_button.classes(add="mode-active")
            self.sidebar_mode_button.classes(remove="mode-active")
        if resize:
            self._request_chart_resize()

    def switch_to_tab(self, page_key: str):
        """Works from either top tabs or sidebar; preserves existing view state."""
        if page_key not in self.PAGES:
            return
        self.current_page_key = page_key
        if self.header_page_title is not None:
            self.header_page_title.text = self.PAGES[page_key]["title"]
        self._sync_active_navigation()
        self._update_view_visibility()
        self._request_chart_resize()

    def _sync_active_navigation(self):
        for key, item in self.nav_buttons.items():
            if key == self.current_page_key:
                item.classes(add="nav-item--active")
            else:
                item.classes(remove="nav-item--active")
        for key, item in self.tab_buttons.items():
            if key == self.current_page_key:
                item.classes(add="dual-tab-active")
            else:
                item.classes(remove="dual-tab-active")

    def _update_view_visibility(self):
        for key, container in self.view_containers.items():
            container.set_visibility(key == self.current_page_key)

    def _toggle_sidebar(self):
        """Keep the brand PNG visible (icon portion) in collapsed mode."""
        self.is_sidebar_collapsed = not self.is_sidebar_collapsed
        if self.is_sidebar_collapsed:
            self.sidebar_elem.classes(add="sidebar--collapsed")
            self.btn_collapse.props("icon=menu")
            for label in self.nav_labels.values():
                label.set_visibility(False)
        else:
            self.sidebar_elem.classes(remove="sidebar--collapsed")
            self.btn_collapse.props("icon=menu_open")
            for label in self.nav_labels.values():
                label.set_visibility(True)
        self._request_chart_resize()

    @staticmethod
    def _request_chart_resize():
        """Prompt responsive Plotly charts to recalculate after layout changes."""
        ui.run_javascript(
            'setTimeout(() => window.dispatchEvent(new Event("resize")), 220)'
        )

    def _update_header_status(self):
        if self.header_tcp_text is None:
            return

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

        if self.recording_manager.is_recording:
            self.header_rec_text.text = "REC: ON"
            self.header_rec_text.classes("text-red-600 font-bold", remove="text-slate-600 font-semibold")
            self.header_rec_dot.classes("dot-recording")
        else:
            self.header_rec_text.text = "REC: OFF"
            self.header_rec_text.classes("text-slate-600 font-semibold", remove="text-red-600 font-bold")
            self.header_rec_dot.classes(remove="dot-recording")

    def _on_data_updated(self):
        self.file_diag_view.refresh()
        self.comparison_view.refresh()
        self.reports_view.refresh()
