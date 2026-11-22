"""File Diagnostics workspace for offline radar test logs.
Redesigned with modern engineering analytics aesthetics, compact dataset toolbar,
balanced KPI grid, expandable high-performance charts, and streamlined controls.
"""

import io
import os
from typing import Callable, Optional
from nicegui import events, ui

from app.core.csv_parser import parse_csv_content, parse_zip_archive
from app.core.session_manager import SessionManager
from app.ui.components import create_card_header, create_kpi_card, open_expanded_chart_dialog
from app.visualization.distributions import create_distribution_plot
from app.visualization.heatmaps import create_matrix_heatmap
from app.visualization.line_plots import (
    create_measurements_vs_elements_plot,
    create_measurements_vs_frequency_plot,
)


class FileDiagnosticsView:
    """View component rendering the offline File Diagnostics workspace."""

    def __init__(self, manager: SessionManager, on_update: Optional[Callable[[], None]] = None):
        self.manager = manager
        self.on_update = on_update

        # UI element references
        self.dataset_toolbar_container = None
        self.cards_container = None
        self.table_container = None
        self.chart_elem_container = None
        self.chart_freq_container = None
        self.chart_heat_container = None
        self.chart_dist_container = None
        self.anomalies_table_container = None
        self.dist_mode = "histogram"
        self.heatmap_test_id = None

        # Cached figures for modal expansion
        self._last_elem_fig = None
        self._last_freq_fig = None
        self._last_heat_fig = None
        self._last_dist_fig = None

    def render(self):
        """Construct the entire File Diagnostics tab layout."""
        with ui.column().classes("w-full gap-4"):
            # 1. Dataset Management Toolbar (Condensed when loaded, expanded when empty)
            self.dataset_toolbar_container = ui.column().classes("w-full")

            # 2. Diagnostics Filtering & Controls Panel
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center mb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("tune", size="18px", color="primary")
                        ui.label("Diagnostics Filter & Dimension Controls").classes("text-sm font-bold text-slate-800")
                    with ui.row().classes("items-center gap-2"):
                        ui.button("Select All Tests", on_click=self._select_all_tests).props("flat dense size=sm").classes("text-blue-600 font-semibold")
                        ui.button("Deselect All", on_click=self._deselect_all_tests).props("flat dense size=sm").classes("text-slate-500")

                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    # Data Type Selector
                    self.type_select = ui.select(
                        options=["AMP", "NOISE", "PHASE"],
                        value=self.manager.active_data_type,
                        label="Data Type",
                        on_change=self._handle_type_change,
                    ).props("outlined dense options-dense").classes("w-28")

                    # Phase display mode (only for PHASE)
                    self.phase_mode_select = ui.select(
                        options=["degrees", "radians", "unwrapped"],
                        value=self.manager.phase_display_mode,
                        label="Phase Mode",
                        on_change=self._handle_phase_mode_change,
                    ).props("outlined dense options-dense").classes("w-32")

                    # Primary Channel for Element Plot
                    dataset_freqs = self.manager.current_dataset.get_common_frequencies() or ["A"]
                    self.freq_select = ui.select(
                        options=dataset_freqs,
                        value=self.manager.focused_frequency,
                        label="Element Plot Ch",
                        on_change=self._handle_focused_freq_change,
                    ).props("outlined dense options-dense").classes("w-32")

                    # Element for Frequency Plot
                    dataset_elems = self.manager.current_dataset.get_common_elements() or [1]
                    self.elem_select = ui.select(
                        options=dataset_elems,
                        value=self.manager.focused_element,
                        label="Channel Plot Elem",
                        on_change=self._handle_focused_elem_change,
                    ).props("outlined dense options-dense").classes("w-32")

                    # Elements Count
                    self.elem_count_input = ui.number(
                        label="Elements",
                        value=len(self.manager.selected_element_ids),
                        min=1,
                        max=256,
                        step=1,
                        on_change=self._handle_elem_count_change,
                    ).props("outlined dense").classes("w-24")

                    # Frequencies Count
                    self.freq_count_input = ui.number(
                        label="Channels",
                        value=len(self.manager.selected_frequency_labels) or 64,
                        min=1,
                        max=64,
                        step=1,
                        on_change=self._handle_freq_count_change,
                    ).props("outlined dense").classes("w-24")

                    ui.button(
                        "Apply Filters",
                        icon="filter_alt",
                        on_click=self.refresh,
                    ).classes("btn-primary")

            # 3. Diagnostic Summary KPI Row
            self.cards_container = ui.element("div").classes("kpi-row")

            # 4. Loaded Test Summary Table (Directly visible list of loaded CSV tests)
            with ui.card().classes("app-card w-full"):
                create_card_header(
                    title="Test Summary Statistics (Loaded CSV Test Logs)",
                    subtitle="Per-test metrics, missing values, and threshold tolerance evaluations",
                    icon="table_chart",
                )
                self.table_container = ui.column().classes("w-full")

            # 5. Primary Chart: Measurements vs Elements (Full Width with Expand)
            with ui.card().classes("app-card w-full"):
                create_card_header(
                    title="Measurements vs Elements",
                    subtitle=f"Element response curve across {len(self.manager.selected_test_ids)} active test runs",
                    icon="show_chart",
                    on_expand=lambda: open_expanded_chart_dialog(
                        f"Measurements vs Elements (Channel {self.manager.focused_frequency})",
                        self._last_elem_fig,
                    ),
                )
                self.chart_elem_container = ui.column().classes("w-full")

            # 6. Responsive Two-Column Secondary Visualizations
            with ui.row().classes("w-full gap-4 items-start no-wrap flex-col lg:flex-row"):
                # Left: Measurements vs Frequency Channel
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title=f"Measurements vs Frequency (Element {self.manager.focused_element})",
                        subtitle="Channel spectrum across tests",
                        icon="stacked_line_chart",
                        on_expand=lambda: open_expanded_chart_dialog(
                            f"Measurements vs Frequency (Element {self.manager.focused_element})",
                            self._last_freq_fig,
                        ),
                    )
                    self.chart_freq_container = ui.column().classes("w-full")

                # Right: 2D Matrix Heatmap
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    with ui.row().classes("w-full justify-between items-center mb-3"):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("grid_on", size="20px", color="primary").classes("opacity-80")
                            ui.label("Matrix Heatmap (256x64)").classes("card-title m-0")
                        with ui.row().classes("items-center gap-2"):
                            self.heat_test_select = ui.select(
                                options=self.manager.current_dataset.get_test_ids() or ["No tests"],
                                value=self.heatmap_test_id,
                                on_change=self._handle_heat_test_change,
                            ).props("outlined dense options-dense").classes("w-32")
                            ui.button(
                                icon="open_in_full",
                                on_click=lambda: open_expanded_chart_dialog(
                                    f"Matrix Heatmap: {self.heatmap_test_id}",
                                    self._last_heat_fig,
                                ),
                            ).props("flat round dense size=sm").classes("text-slate-400 hover:text-blue-600").tooltip("Expand heatmap")

                    self.chart_heat_container = ui.column().classes("w-full")

            # 7. Secondary Analysis Section (Sub-tabs for Distribution and Outlier Anomalies)
            with ui.card().classes("app-card w-full"):
                with ui.tabs().classes("w-full border-b border-slate-200") as analysis_tabs:
                    tab_dist = ui.tab("Measurement Distribution", icon="bar_chart")
                    tab_anom = ui.tab("Threshold Violations & Outliers", icon="warning")

                with ui.tab_panels(analysis_tabs, value=tab_dist).classes("w-full p-2"):
                    with ui.tab_panel(tab_dist).classes("p-0"):
                        with ui.row().classes("w-full justify-end items-center gap-2 pt-2"):
                            ui.button("Histogram", on_click=lambda: self._set_dist_mode("histogram")).props(
                                "flat dense size=sm color=primary"
                            )
                            ui.button("Box Plots", on_click=lambda: self._set_dist_mode("box")).props(
                                "flat dense size=sm color=primary"
                            )
                        self.chart_dist_container = ui.column().classes("w-full")

                    with ui.tab_panel(tab_anom).classes("p-0"):
                        self.anomalies_table_container = ui.column().classes("w-full pt-2")

        # Initial render
        self.refresh()

    def refresh(self):
        """Update all data views, metrics cards, tables, and graphs."""
        self._update_dataset_toolbar()
        self._update_cards()
        self._update_summary_table()
        self._update_element_chart()
        self._update_frequency_chart()
        self._update_heatmap()
        self._update_distribution_chart()
        self._update_anomalies_table()
        self._update_control_options()

    def _update_dataset_toolbar(self):
        """Render clean import zone with direct drag & drop upload and sample buttons."""
        self.dataset_toolbar_container.clear()
        dataset = self.manager.current_dataset
        has_data = len(dataset.frames) > 0

        with self.dataset_toolbar_container:
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full items-center justify-between flex-wrap gap-3 mb-2"):
                    # Left: Dataset Status / Info
                    with ui.row().classes("items-center gap-3"):
                        ui.icon("folder_open", size="22px", color="primary")
                        if has_data:
                            with ui.column().classes("gap-0"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label("Active Dataset:").classes("text-xs font-bold text-slate-500 uppercase")
                                    ui.label(f"{len(dataset.frames)} Test Logs Loaded").classes("text-sm font-bold text-slate-800")
                                    ui.label(self.manager.active_data_type).classes("chip-info")
                                ui.label(f"Session: {self.manager.session_name} • 256 Elements × 64 Channels").classes("text-xs text-slate-500")
                        else:
                            with ui.column().classes("gap-0"):
                                ui.label("No Radar Dataset Loaded").classes("text-sm font-bold text-slate-800")
                                ui.label("Drag & drop CSV/ZIP files into the upload box below or load a sample dataset").classes("text-xs text-slate-500")

                    # Right: Sample quick load buttons & Clear
                    with ui.row().classes("items-center gap-2 flex-wrap"):
                        ui.button(
                            "Sample AMP",
                            icon="folder_special",
                            on_click=lambda: self._load_sample_data("AMP"),
                        ).classes("btn-secondary")

                        ui.button(
                            "Sample NOISE",
                            icon="grain",
                            on_click=lambda: self._load_sample_data("NOISE"),
                        ).classes("btn-secondary")

                        ui.button(
                            "Sample PHASE",
                            icon="rotate_right",
                            on_click=lambda: self._load_sample_data("PHASE"),
                        ).classes("btn-secondary")

                        if has_data:
                            ui.button(
                                "Clear All",
                                icon="delete_sweep",
                                on_click=self._clear_data,
                            ).props("flat dense").classes("text-red-600 hover:bg-red-50")

                # Direct Drag & Drop CSV / ZIP upload field
                ui.upload(
                    multiple=True,
                    auto_upload=True,
                    on_upload=self._handle_upload,
                    label="Drag & Drop CSV / ZIP files here or click to browse",
                ).props('accept=".csv,.zip"').classes("w-full border-2 border-dashed border-slate-200 rounded-lg p-1")

    def _open_upload_modal(self):
        """Open a clean upload modal dialog."""
        with ui.dialog() as dialog, ui.card().classes("app-card w-[540px]"):
            with ui.row().classes("w-full justify-between items-center mb-3"):
                with ui.row().classes("items-center gap-2"):
                    ui.icon("cloud_upload", size="20px", color="primary")
                    ui.label("Import Radar Test Files").classes("card-title m-0")
                ui.button(icon="close", on_click=dialog.close).props("flat round dense size=sm")

            ui.label("Upload individual test CSV files or ZIP archives containing multi-test matrices:").classes("text-xs text-slate-500 mb-3")

            ui.upload(
                multiple=True,
                auto_upload=True,
                on_upload=lambda e: self._handle_upload_and_close(e, dialog),
                label="Drag & Drop CSV / ZIP files here or click to browse",
            ).props('accept=".csv,.zip"').classes("w-full border-2 border-dashed border-slate-200 rounded-lg p-2")

        dialog.open()

    async def _handle_upload_and_close(self, e: events.UploadEventArguments, dialog):
        await self._handle_upload(e)
        dialog.close()

    def _update_control_options(self):
        """Update selector options based on loaded dataset."""
        dataset = self.manager.current_dataset
        common_freqs = dataset.get_common_frequencies()
        if common_freqs:
            self.freq_select.options = common_freqs
            if self.manager.focused_frequency not in common_freqs:
                self.manager.focused_frequency = common_freqs[0]
                self.freq_select.value = common_freqs[0]

        common_elems = dataset.get_common_elements()
        if common_elems:
            self.elem_select.options = common_elems
            if self.manager.focused_element not in common_elems:
                self.manager.focused_element = common_elems[0]
                self.elem_select.value = common_elems[0]

        test_ids = dataset.get_test_ids()
        self.heat_test_select.options = test_ids if test_ids else ["No tests"]
        if test_ids and (not self.heatmap_test_id or self.heatmap_test_id not in test_ids):
            self.heatmap_test_id = test_ids[0]
            self.heat_test_select.value = test_ids[0]

    def _update_cards(self):
        self.cards_container.clear()
        summary = self.manager.get_summary_metrics()

        cards_data = [
            ("Loaded Tests", str(summary.test_count), "", f"Mode: {summary.data_type}", False),
            ("Matrix Dimensions", f"{summary.element_count} × {summary.frequency_count}", "", "Elements × Freqs", False),
            ("Mean Measurement", f"{summary.overall_mean:.2f}", summary.unit, "Across all active cells", False),
            ("Standard Deviation", f"{summary.overall_std:.2f}", summary.unit, "Dataset dispersion", False),
            ("Min / Max Bounds", f"{summary.overall_min:.1f} / {summary.overall_max:.1f}", summary.unit, "Extreme readings", False),
            ("Violations & Outliers", str(summary.total_threshold_violations), "", "Tolerance breaches", summary.total_threshold_violations > 0),
        ]

        with self.cards_container:
            for label, val, unit, sub, is_alert in cards_data:
                create_kpi_card(label, val, unit=unit, subtext=sub, is_alert=is_alert)

    def _update_summary_table(self):
        self.table_container.clear()
        summary = self.manager.get_summary_metrics()

        columns = [
            {"name": "test_id", "label": "Test ID", "field": "test_id", "sortable": True, "align": "left"},
            {"name": "mean", "label": f"Mean ({summary.unit})", "field": "mean", "sortable": True, "align": "right"},
            {"name": "std_dev", "label": "Std Dev", "field": "std_dev", "sortable": True, "align": "right"},
            {"name": "min_val", "label": "Min", "field": "min_val", "sortable": True, "align": "right"},
            {"name": "max_val", "label": "Max", "field": "max_val", "sortable": True, "align": "right"},
            {"name": "median", "label": "Median", "field": "median", "sortable": True, "align": "right"},
            {"name": "missing", "label": "Missing", "field": "missing_count", "sortable": True, "align": "right"},
            {"name": "violations", "label": "Violations", "field": "threshold_violations", "sortable": True, "align": "right"},
            {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "center"},
        ]

        rows = [
            {
                "test_id": ts.test_id,
                "mean": f"{ts.mean:.2f}",
                "std_dev": f"{ts.std_dev:.2f}",
                "min_val": f"{ts.min_val:.2f}",
                "max_val": f"{ts.max_val:.2f}",
                "median": f"{ts.median:.2f}",
                "missing_count": ts.missing_count,
                "threshold_violations": ts.threshold_violations,
                "status": ts.status,
            }
            for ts in summary.test_summaries
        ]

        with self.table_container:
            if not rows:
                ui.label("No test logs loaded yet. Upload CSV files or click a Sample Dataset button above.").classes("text-slate-400 italic p-4 text-center")
            else:
                ui.table(columns=columns, rows=rows, row_key="test_id").props("dense flat bordered").classes("w-full")

    def _update_element_chart(self):
        self.chart_elem_container.clear()
        frames = self.manager.get_filtered_frames()
        self._last_elem_fig = create_measurements_vs_elements_plot(
            frames,
            frequency_label=self.manager.focused_frequency,
            focused_element=self.manager.focused_element,
            phase_mode=self.manager.phase_display_mode,
            thresholds=self.manager.thresholds,
            height=380,
            show_title=False,
        )
        with self.chart_elem_container:
            ui.plotly(self._last_elem_fig).classes("w-full")

    def _update_frequency_chart(self):
        self.chart_freq_container.clear()
        frames = self.manager.get_filtered_frames()
        self._last_freq_fig = create_measurements_vs_frequency_plot(
            frames,
            element_id=self.manager.focused_element,
            focused_frequency=self.manager.focused_frequency,
            phase_mode=self.manager.phase_display_mode,
            thresholds=self.manager.thresholds,
            height=340,
            show_title=False,
        )
        with self.chart_freq_container:
            ui.plotly(self._last_freq_fig).classes("w-full")

    def _update_heatmap(self):
        self.chart_heat_container.clear()
        dataset = self.manager.current_dataset
        test_frame = dataset.get_frame(self.heatmap_test_id) if self.heatmap_test_id else None
        if test_frame is None and dataset.frames:
            test_frame = next(iter(dataset.frames.values()))
            self.heatmap_test_id = test_frame.test_id

        self._last_heat_fig = create_matrix_heatmap(
            test_frame,
            phase_mode=self.manager.phase_display_mode,
            height=340,
            show_title=False,
        )
        with self.chart_heat_container:
            ui.plotly(self._last_heat_fig).classes("w-full")

    def _update_distribution_chart(self):
        self.chart_dist_container.clear()
        frames = self.manager.get_filtered_frames()
        self._last_dist_fig = create_distribution_plot(
            frames,
            phase_mode=self.manager.phase_display_mode,
            plot_type=self.dist_mode,
            thresholds=self.manager.thresholds,
            height=340,
            show_title=False,
        )
        with self.chart_dist_container:
            ui.plotly(self._last_dist_fig).classes("w-full")

    def _update_anomalies_table(self):
        self.anomalies_table_container.clear()
        anomalies = self.manager.get_all_anomalies()

        columns = [
            {"name": "test_id", "label": "Test ID", "field": "test_id", "sortable": True, "align": "left"},
            {"name": "elem", "label": "Element", "field": "element_id", "sortable": True, "align": "right"},
            {"name": "freq", "label": "Channel", "field": "frequency_label", "sortable": True, "align": "center"},
            {"name": "val", "label": "Measured", "field": "measured_value", "sortable": True, "align": "right"},
            {"name": "limit", "label": "Limit", "field": "expected_or_limit", "sortable": True, "align": "right"},
            {"name": "dev", "label": "Deviation", "field": "deviation", "sortable": True, "align": "right"},
            {"name": "severity", "label": "Severity", "field": "severity", "sortable": True, "align": "center"},
            {"name": "reason", "label": "Reason", "field": "reason", "align": "left"},
        ]

        rows = [
            {
                "test_id": a.test_id,
                "element_id": a.element_id,
                "frequency_label": a.frequency_label,
                "measured_value": f"{a.measured_value} {a.unit}",
                "expected_or_limit": f"{a.expected_or_limit} {a.unit}",
                "deviation": f"{a.deviation:+} {a.unit}",
                "severity": a.severity,
                "reason": a.reason,
            }
            for a in anomalies[:50]
        ]

        with self.anomalies_table_container:
            if not rows:
                ui.label("No abnormal measurements found. System nominal.").classes("text-emerald-600 font-semibold p-4")
            else:
                ui.table(columns=columns, rows=rows, pagination=10).props("dense flat bordered").classes("w-full")

    # Event handlers
    async def _handle_upload(self, e: events.UploadEventArguments):
        content = await e.content.read()
        name = e.name
        if name.lower().endswith(".zip"):
            frames, reports = parse_zip_archive(content, session_id=self.manager.session_name)
            for f in frames:
                self.manager.add_frames([f])
            ui.notify(f"Extracted and loaded {len(frames)} test log(s) from {name}", type="positive")
        else:
            frames, report = parse_csv_content(content, filename=name, session_id=self.manager.session_name)
            if frames:
                self.manager.add_frames(frames, report)
                ui.notify(f"Loaded {len(frames)} test(s) from {name}", type="positive")
            else:
                ui.notify(f"Failed to parse {name}: {'; '.join(report.errors)}", type="negative")
        self.refresh()
        if self.on_update:
            self.on_update()

    def _load_sample_data(self, data_type: str):
        from app.config import default_config
        sample_dir = os.path.join(default_config.sample_data_dir, data_type)
        if not os.path.exists(sample_dir):
            ui.notify(f"Sample data folder not found: {sample_dir}", type="negative")
            return

        loaded_count = 0
        for f in sorted(os.listdir(sample_dir)):
            if f.lower().endswith(".csv"):
                fpath = os.path.join(sample_dir, f)
                frames, report = parse_csv_content(fpath, filename=f, explicit_data_type=data_type)
                if frames:
                    self.manager.add_frames(frames, report)
                    loaded_count += len(frames)

        self.manager.set_active_data_type(data_type)
        self.type_select.value = data_type
        ui.notify(f"Loaded {loaded_count} sample {data_type} tests successfully!", type="positive")
        self.refresh()
        if self.on_update:
            self.on_update()

    def _clear_data(self):
        self.manager.clear_all()
        ui.notify("All loaded test files cleared.", type="info")
        self.refresh()
        if self.on_update:
            self.on_update()

    def _handle_type_change(self, e):
        self.manager.set_active_data_type(e.value)
        self.refresh()
        if self.on_update:
            self.on_update()

    def _handle_phase_mode_change(self, e):
        self.manager.phase_display_mode = e.value
        self.refresh()

    def _handle_elem_count_change(self, e):
        val = int(e.value or 256)
        all_elems = self.manager.current_dataset.get_common_elements() or list(range(1, 257))
        self.manager.selected_element_ids = all_elems[:val]
        self.refresh()

    def _handle_freq_count_change(self, e):
        val = int(e.value or 64)
        all_freqs = self.manager.current_dataset.get_common_frequencies() or []
        self.manager.selected_frequency_labels = all_freqs[:val]
        self.refresh()

    def _handle_focused_freq_change(self, e):
        self.manager.focused_frequency = e.value
        self._update_element_chart()

    def _handle_focused_elem_change(self, e):
        self.manager.focused_element = int(e.value)
        self._update_frequency_chart()
        self._update_element_chart()

    def _handle_heat_test_change(self, e):
        self.heatmap_test_id = e.value
        self._update_heatmap()

    def _set_dist_mode(self, mode: str):
        self.dist_mode = mode
        self._update_distribution_chart()

    def _select_all_tests(self):
        self.manager.selected_test_ids = list(self.manager.current_dataset.get_test_ids())
        self.refresh()

    def _deselect_all_tests(self):
        self.manager.selected_test_ids = []
        self.refresh()
