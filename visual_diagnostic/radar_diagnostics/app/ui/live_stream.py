"""Live Stream & Recording tab implementation.

Provides glitch-free real-time telemetry streaming, green start recording controls,
and a live Excel-style spreadsheet inspector streaming data in real-time.
"""

import asyncio
from datetime import datetime
from typing import Callable, Dict, List, Optional
import numpy as np
import plotly.graph_objects as go
from nicegui import ui

from app.config import default_config, generate_frequency_labels
from app.core.session_manager import SessionManager
from app.models.radar_frame import RadarFrame
from app.streaming.recording_manager import RecordingManager
from app.streaming.tcp_client import ConnectionState, RadarTcpClient
from app.visualization.color_palette import PALETTE, apply_theme_layout
from app.visualization.heatmaps import create_matrix_heatmap
from app.visualization.line_plots import (
    create_measurements_vs_elements_plot,
    create_measurements_vs_frequency_plot,
)


class LiveStreamView:
    """View component rendering the live TCP stream and recording workspace."""

    def __init__(
        self,
        client: RadarTcpClient,
        recording_mgr: RecordingManager,
        session_manager: SessionManager,
        on_switch_tab: Optional[Callable[[str], None]] = None,
    ):
        self.client = client
        self.recording_mgr = recording_mgr
        self.session_manager = session_manager
        self.on_switch_tab = on_switch_tab

        self.is_paused: bool = False
        self.focused_freq: str = "A"
        self.focused_elem: int = 1
        self._last_rendered_seq: Optional[int] = None
        self.excel_channel_slice: str = "A - P (1-16)"

        # Rolling trend data (timestamps, means, mins, maxs)
        self.trend_times: List[str] = []
        self.trend_means: List[float] = []
        self.trend_mins: List[float] = []
        self.trend_maxs: List[float] = []
        self.max_trend_points: int = 50

        # UI element references
        self.status_badge = None
        self.rec_badge = None
        self.fps_label = None
        self.frames_label = None
        self.seq_label = None
        self.rec_frames_label = None
        self.rec_time_label = None

        # Persistent Plotly elements (updated in-place to prevent DOM glitching)
        self.plotly_heat = None
        self.plotly_elem = None
        self.plotly_freq = None
        self.plotly_trend = None

        # Excel streaming grid
        self.excel_table = None
        self.excel_frame_badge = None
        self.excel_cols: List[Dict] = []
        self.excel_rows: List[Dict] = []

        self.recordings_list_container = None

        # Wire client frame hook to recording manager
        self.client.add_frame_callback(self._on_incoming_frame)

    def render(self):
        """Construct the Live Stream & Recording tab layout."""
        with ui.column().classes("w-full p-4 gap-4"):
            # 1. TCP Server Connection & Control Panel
            with ui.card().classes("w-full panel-container"):
                ui.label("Radar Stream Connection & Recording Controls").classes("panel-header")
                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    self.host_input = ui.input(
                        label="Server IP / Hostname",
                        value=self.client.host,
                    ).classes("w-44")

                    self.port_input = ui.number(
                        label="Server Port",
                        value=self.client.port,
                        min=1024,
                        max=65535,
                        step=1,
                    ).classes("w-32")

                    self.btn_connect = ui.button(
                        "Connect",
                        icon="link",
                        on_click=self._handle_connect,
                    ).classes("btn-primary")

                    self.btn_disconnect = ui.button(
                        "Disconnect",
                        icon="link_off",
                        on_click=self._handle_disconnect,
                    ).props("outline color=grey")

                    ui.separator().props("vertical").classes("h-8 mx-2")

                    # User request: Start Recording button is bright green!
                    self.btn_start_rec = ui.button(
                        "Start Recording",
                        icon="fiber_manual_record",
                        on_click=self._handle_start_rec,
                    ).classes("btn-success")

                    self.btn_stop_rec = ui.button(
                        "Stop Recording",
                        icon="stop",
                        on_click=self._handle_stop_rec,
                    ).classes("btn-danger")

                    self.btn_pause = ui.button(
                        "Pause Display",
                        icon="pause",
                        on_click=self._toggle_pause,
                    ).props("outline color=primary")

            # 2. Live Telemetry & Status Cards
            with ui.row().classes("w-full gap-4 flex-wrap"):
                with ui.card().classes("metric-card flex-1 min-w-[150px]"):
                    ui.label("Connection Status").classes("metric-title")
                    self.status_badge = ui.label("DISCONNECTED").classes("metric-val text-gray-500 text-lg")

                with ui.card().classes("metric-card flex-1 min-w-[150px]"):
                    ui.label("Recording State").classes("metric-title")
                    self.rec_badge = ui.label("REC OFF").classes("metric-val text-gray-500 text-lg")

                with ui.card().classes("metric-card flex-1 min-w-[130px]"):
                    ui.label("Frame Rate").classes("metric-title")
                    self.fps_label = ui.label("0.0 fps").classes("metric-val")

                with ui.card().classes("metric-card flex-1 min-w-[130px]"):
                    ui.label("Frames Ingested").classes("metric-title")
                    self.frames_label = ui.label("0").classes("metric-val")

                with ui.card().classes("metric-card flex-1 min-w-[130px]"):
                    ui.label("Latest Seq / Gaps").classes("metric-title")
                    self.seq_label = ui.label("#0 / 0").classes("metric-val")

                with ui.card().classes("metric-card flex-1 min-w-[130px]"):
                    ui.label("Recorded Frames").classes("metric-title")
                    self.rec_frames_label = ui.label("0").classes("metric-val text-red-600")

                with ui.card().classes("metric-card flex-1 min-w-[130px]"):
                    ui.label("Rec Elapsed Time").classes("metric-title")
                    self.rec_time_label = ui.label("0.0s").classes("metric-val text-red-600")

            # 3. Live Excel Spreadsheet Stream Inspector (User Request)
            with ui.card().classes("w-full panel-container"):
                with ui.row().classes("w-full justify-between items-center mb-2"):
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("table_chart", size="24px", color="primary")
                        ui.label("Live Radar Matrix Stream (Excel View)").classes("panel-header m-0")
                        self.excel_frame_badge = ui.label("Waiting for stream...").classes(
                            "text-xs font-mono bg-slate-100 text-slate-700 px-3 py-1 rounded-full border border-slate-300"
                        )

                    with ui.row().classes("items-center gap-2"):
                        self.excel_channel_select = ui.select(
                            options=[
                                "A - P (1-16)",
                                "Q - AF (17-32)",
                                "AG - AV (33-48)",
                                "AW - BL (49-64)",
                                "All 64 Channels",
                            ],
                            value=self.excel_channel_slice,
                            label="Channel Window",
                            on_change=self._handle_channel_slice_change,
                        ).classes("w-48")

                # Build initial table columns
                self._rebuild_excel_columns()
                # Create the Quasar table once
                self.excel_table = ui.table(
                    columns=self.excel_cols,
                    rows=self.excel_rows,
                    row_key="element",
                    pagination={"rowsPerPage": 15},
                ).classes("w-full excel-table").props("dense flat bordered")

            # 4. Live Heatmap & Live Trend (Persistent Plotly Nodes - Zero Glitching)
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Live Radar Matrix Heatmap (Latest Frame)").classes("panel-header")
                    init_heat_fig = create_matrix_heatmap(None, phase_mode="degrees", height=360)
                    self.plotly_heat = ui.plotly(init_heat_fig).classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Live Signal Trend (Mean, Min, Max over Time)").classes("panel-header")
                    init_trend_fig = go.Figure()
                    apply_theme_layout(init_trend_fig, title="Live Measurement Trend", height=360)
                    self.plotly_trend = ui.plotly(init_trend_fig).classes("w-full")

            # 5. Live Cross-Section Plots (Element & Frequency)
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Live Element Profile").classes("panel-header")
                        self.live_freq_select = ui.select(
                            options=["A"],
                            value=self.focused_freq,
                            label="Channel",
                            on_change=lambda e: setattr(self, "focused_freq", e.value),
                        ).classes("w-28")
                    init_elem_fig = create_measurements_vs_elements_plot([], height=340)
                    self.plotly_elem = ui.plotly(init_elem_fig).classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Live Frequency Spectrum").classes("panel-header")
                        self.live_elem_select = ui.select(
                            options=[1],
                            value=self.focused_elem,
                            label="Element",
                            on_change=lambda e: setattr(self, "focused_elem", int(e.value)),
                        ).classes("w-28")
                    init_freq_fig = create_measurements_vs_frequency_plot([], height=340)
                    self.plotly_freq = ui.plotly(init_freq_fig).classes("w-full")

            # 6. Saved Recording Sessions & Quick Load
            with ui.card().classes("w-full panel-container"):
                ui.label("Saved Recording Sessions on Disk").classes("panel-header")
                self.recordings_list_container = ui.column().classes("w-full")

        # Set up periodic UI update timer (2 Hz)
        ui.timer(default_config.live_gui_refresh_interval_sec, self._update_gui)
        self._refresh_recordings_list()

    def _rebuild_excel_columns(self):
        """Build column definitions for the Excel matrix inspector."""
        all_freqs = generate_frequency_labels(64)
        if self.excel_channel_slice == "A - P (1-16)":
            active_freqs = all_freqs[:16]
        elif self.excel_channel_slice == "Q - AF (17-32)":
            active_freqs = all_freqs[16:32]
        elif self.excel_channel_slice == "AG - AV (33-48)":
            active_freqs = all_freqs[32:48]
        elif self.excel_channel_slice == "AW - BL (49-64)":
            active_freqs = all_freqs[48:64]
        else:
            active_freqs = all_freqs

        cols = [
            {
                "name": "element",
                "label": "Element",
                "field": "element",
                "sortable": True,
                "align": "center",
                "classes": "bg-slate-100 font-bold text-slate-800",
                "headerClasses": "bg-slate-200 font-bold",
            }
        ]
        for f in active_freqs:
            cols.append({
                "name": f,
                "label": f,
                "field": f,
                "align": "right",
                "classes": "font-mono text-xs text-slate-700",
                "headerClasses": "bg-slate-100 font-bold text-slate-800",
            })
        self.excel_cols = cols
        self._active_slice_freqs = active_freqs

    def _handle_channel_slice_change(self, e):
        self.excel_channel_slice = e.value
        self._rebuild_excel_columns()
        if self.excel_table:
            self.excel_table.columns = self.excel_cols
        # Force redraw with latest frame
        self._last_rendered_seq = None

    def _on_incoming_frame(self, frame: RadarFrame):
        """Callback triggered on every incoming TCP frame."""
        # Record frame if active
        self.recording_mgr.record_frame(frame)

        # Update rolling trend data buffer
        mat = frame.get_display_matrix(phase_mode="degrees")
        valid = mat[~np.isnan(mat)]
        if len(valid) > 0:
            now_t = datetime.now().strftime("%H:%M:%S")
            self.trend_times.append(now_t)
            self.trend_means.append(round(float(np.mean(valid)), 2))
            self.trend_mins.append(round(float(np.min(valid)), 2))
            self.trend_maxs.append(round(float(np.max(valid)), 2))

            if len(self.trend_times) > self.max_trend_points:
                self.trend_times.pop(0)
                self.trend_means.pop(0)
                self.trend_mins.pop(0)
                self.trend_maxs.pop(0)

    def _update_gui(self):
        """Periodic refresh of status badges, telemetry cards, and in-place plots."""
        # 1. Update Connection Badge
        state = self.client.state
        if state == ConnectionState.CONNECTED:
            self.status_badge.text = "CONNECTED"
            self.status_badge.classes("text-green-600", remove="text-gray-500 text-amber-500 text-red-600")
            self.btn_connect.disable()
            self.btn_disconnect.enable()
        elif state == ConnectionState.CONNECTING:
            self.status_badge.text = "CONNECTING..."
            self.status_badge.classes("text-amber-500", remove="text-gray-500 text-green-600 text-red-600")
        elif state == ConnectionState.ERROR:
            self.status_badge.text = f"ERROR: {self.client.last_error_message or ''}"
            self.status_badge.classes("text-red-600", remove="text-gray-500 text-green-600 text-amber-500")
            self.btn_connect.enable()
            self.btn_disconnect.disable()
        else:
            self.status_badge.text = "DISCONNECTED"
            self.status_badge.classes("text-gray-500", remove="text-green-600 text-amber-500 text-red-600")
            self.btn_connect.enable()
            self.btn_disconnect.disable()

        # 2. Update Recording Controls
        if self.recording_mgr.is_recording:
            self.rec_badge.text = "RECORDING"
            self.rec_badge.classes("text-red-600 font-bold", remove="text-gray-500")
            self.rec_frames_label.text = str(self.recording_mgr.recorded_frames_count)
            self.rec_time_label.text = f"{self.recording_mgr.elapsed_seconds}s"
            self.btn_start_rec.disable()
            self.btn_stop_rec.enable()
        else:
            self.rec_badge.text = "REC OFF"
            self.rec_badge.classes("text-gray-500", remove="text-red-600 font-bold")
            self.btn_start_rec.enable()
            self.btn_stop_rec.disable()

        # Metrics
        self.fps_label.text = f"{self.client.approx_frame_rate} fps"
        self.frames_label.text = str(self.client.frames_received)
        last_seq = self.client.last_sequence or 0
        self.seq_label.text = f"#{last_seq} / {self.client.sequence_gaps}"

        # If paused or no new frame, do NOT recalculate heavy plots
        if self.is_paused:
            return

        frame = self.client.latest_frame
        if frame is None:
            return

        # Skip in-place update if this exact sequence was already rendered
        if frame.sequence_number == self._last_rendered_seq:
            return
        self._last_rendered_seq = frame.sequence_number

        # Update selector options if needed
        if self.live_freq_select.options != frame.frequency_labels:
            self.live_freq_select.options = frame.frequency_labels
        if self.live_elem_select.options != frame.element_ids:
            self.live_elem_select.options = frame.element_ids

        # 3. Update Excel-style Live Data Table
        mat_disp = frame.get_display_matrix(phase_mode="degrees")
        unit = frame.display_unit
        self.excel_frame_badge.text = f"Frame #{frame.sequence_number} [{frame.data_type} ({unit})] | {frame.timestamp[11:19]} UTC"

        excel_rows = []
        active_freqs = getattr(self, "_active_slice_freqs", frame.frequency_labels[:16])
        freq_indices = [frame.frequency_labels.index(f) for f in active_freqs if f in frame.frequency_labels]

        for i, eid in enumerate(frame.element_ids):
            row = {"element": f"{eid}"}
            for fl, j in zip(active_freqs, freq_indices):
                row[fl] = f"{mat_disp[i, j]:.2f}"
            excel_rows.append(row)

        if self.excel_table:
            self.excel_table.rows = excel_rows

        # 4. In-Place Plot Updates (Zero Glitching / No DOM Re-creation)
        fig_heat = create_matrix_heatmap(frame, phase_mode="degrees", height=360)
        self.plotly_heat.update_figure(fig_heat)

        fig_elem = create_measurements_vs_elements_plot(
            [frame],
            frequency_label=self.focused_freq,
            focused_element=self.focused_elem,
            phase_mode="degrees",
            height=340,
        )
        self.plotly_elem.update_figure(fig_elem)

        fig_freq = create_measurements_vs_frequency_plot(
            [frame],
            element_id=self.focused_elem,
            focused_frequency=self.focused_freq,
            phase_mode="degrees",
            height=340,
        )
        self.plotly_freq.update_figure(fig_freq)

        fig_trend = go.Figure()
        if self.trend_times:
            fig_trend.add_trace(go.Scatter(x=self.trend_times, y=self.trend_means, name="Mean", line=dict(color=PALETTE["primary"], width=2)))
            fig_trend.add_trace(go.Scatter(x=self.trend_times, y=self.trend_maxs, name="Max", line=dict(color="#FF7F0E", width=1, dash="dot")))
            fig_trend.add_trace(go.Scatter(x=self.trend_times, y=self.trend_mins, name="Min", line=dict(color="#059669", width=1, dash="dot")))
            fig_trend.update_xaxes(title_text="Time")
            fig_trend.update_yaxes(title_text=f"Measurement [{unit}]")
        apply_theme_layout(fig_trend, title="Live Measurement Trend", height=360)
        self.plotly_trend.update_figure(fig_trend)

    def _refresh_recordings_list(self):
        self.recordings_list_container.clear()
        sessions = self.recording_mgr.list_recorded_sessions()

        with self.recordings_list_container:
            if not sessions:
                ui.label("No recordings captured yet. Click 'Start Recording' above to record live data.").classes("text-gray-500 italic p-2")
                return

            for s in sessions:
                sid = s.get("session_id", "Unknown")
                total = s.get("total_frames", 0)
                st = s.get("start_time", "")[:19]
                counts = s.get("frame_counts", {})
                counts_str = f"AMP: {counts.get('AMP', 0)} | NOISE: {counts.get('NOISE', 0)} | PHASE: {counts.get('PHASE', 0)}"

                with ui.row().classes("w-full justify-between items-center p-3 border-b border-gray-200 hover:bg-gray-50"):
                    with ui.column().classes("gap-1"):
                        ui.label(f"Session: {sid}").classes("font-bold text-slate-800")
                        ui.label(f"Recorded at: {st} | Total Frames: {total} ({counts_str})").classes("text-xs text-gray-600")

                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            "Open in File Diagnostics",
                            icon="analytics",
                            on_click=lambda s_dir=s.get("session_dir"): self._load_recording_into_diagnostics(s_dir),
                        ).classes("btn-primary")

    def _load_recording_into_diagnostics(self, session_dir: str):
        try:
            count = self.recording_mgr.load_session_into_manager(session_dir, self.session_manager)
            ui.notify(f"Loaded {count} frames from recording into File Diagnostics!", type="positive")
            if self.on_switch_tab:
                self.on_switch_tab("file_diagnostics")
        except Exception as e:
            ui.notify(f"Error loading recording: {e}", type="negative")

    async def _handle_connect(self):
        host = self.host_input.value.strip() or "127.0.0.1"
        port = int(self.port_input.value or 8765)
        await self.client.connect(host=host, port=port)

    async def _handle_disconnect(self):
        await self.client.disconnect()

    def _handle_start_rec(self):
        session = self.recording_mgr.start_recording()
        ui.notify(f"Recording started: {session.session_id}", type="positive")

    def _handle_stop_rec(self):
        session = self.recording_mgr.stop_recording()
        if session:
            ui.notify(f"Recording stopped. Saved {session.total_frames} frames to disk.", type="info")
        self._refresh_recordings_list()

    def _toggle_pause(self):
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.btn_pause.text = "Resume Display"
            self.btn_pause.props("color=amber")
        else:
            self.btn_pause.text = "Pause Display"
            self.btn_pause.props("outline color=primary")
