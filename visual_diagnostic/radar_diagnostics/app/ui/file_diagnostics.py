"""File Diagnostics tab implementation for offline radar test logs.
"""

import io
import os
from typing import Callable, Optional
from nicegui import ui, events

from app.core.csv_parser import parse_csv_content, parse_zip_archive
from app.core.session_manager import SessionManager
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
        self.cards_container = None
        self.table_container = None
        self.chart_elem_container = None
        self.chart_freq_container = None
        self.chart_heat_container = None
        self.chart_dist_container = None
        self.anomalies_table_container = None
        self.dist_mode = "histogram"
        self.heatmap_test_id = None

    def render(self):
        """Construct the entire File Diagnostics tab layout."""
        with ui.column().classes("w-full p-4 gap-4"):
            # 1. Upload & Sample Data Section
            with ui.card().classes("w-full panel-container"):
                ui.label("1. Import Radar Test CSV Files").classes("panel-header")
                with ui.row().classes("w-full items-center justify-between gap-4"):
                    with ui.column().classes("flex-grow"):
                        ui.upload(
                            multiple=True,
                            auto_upload=True,
                            on_upload=self._handle_upload,
                            label="Drag & Drop CSV / ZIP files here or click to browse",
                        ).props('accept=".csv,.zip"').classes("w-full")

                    with ui.row().classes("items-center gap-2"):
                        ui.button(
                            "Load Sample AMP Dataset",
                            icon="folder_special",
                            on_click=lambda: self._load_sample_data("AMP"),
                        ).classes("btn-primary")
                        ui.button(
                            "Load Sample NOISE",
                            icon="grain",
                            on_click=lambda: self._load_sample_data("NOISE"),
                        ).props("outline color=primary")
                        ui.button(
                            "Load Sample PHASE",
                            icon="rotate_right",
                            on_click=lambda: self._load_sample_data("PHASE"),
                        ).props("outline color=primary")
                        ui.button(
                            "Clear All",
                            icon="delete_sweep",
                            on_click=self._clear_data,
                        ).classes("btn-danger")

            # 2. Filtering & Configuration Controls
            with ui.card().classes("w-full panel-container"):
                ui.label("2. Diagnostics Filtering & Controls").classes("panel-header")
                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    # Data Type Selector
                    self.type_select = ui.select(
                        options=["AMP", "NOISE", "PHASE"],
                        value=self.manager.active_data_type,
                        label="Data Type",
                        on_change=self._handle_type_change,
                    ).classes("w-32")

                    # Phase display mode (only for PHASE)
                    self.phase_mode_select = ui.select(
                        options=["degrees", "radians", "unwrapped"],
                        value=self.manager.phase_display_mode,
                        label="Phase Mode",
                        on_change=self._handle_phase_mode_change,
                    ).classes("w-36")

                    # Number of elements
                    self.elem_count_input = ui.number(
                        label="Elements Count",
                        value=len(self.manager.selected_element_ids),
                        min=1,
                        max=256,
                        step=1,
                        on_change=self._handle_elem_count_change,
                    ).classes("w-36")

                    # Number of frequencies
                    self.freq_count_input = ui.number(
                        label="Frequencies Count",
                        value=len(self.manager.selected_frequency_labels) or 64,
                        min=1,
                        max=64,
                        step=1,
                        on_change=self._handle_freq_count_change,
                    ).classes("w-36")

                    # Frequency channel selector for main element plot
                    dataset_freqs = self.manager.current_dataset.get_common_frequencies() or ["A"]
                    self.freq_select = ui.select(
                        options=dataset_freqs,
                        value=self.manager.focused_frequency,
                        label="Channel for Element Plot",
                        on_change=self._handle_focused_freq_change,
                    ).classes("w-44")

                    # Element selector for frequency plot
                    dataset_elems = self.manager.current_dataset.get_common_elements() or [1]
                    self.elem_select = ui.select(
                        options=dataset_elems,
                        value=self.manager.focused_element,
                        label="Element for Channel Plot",
                        on_change=self._handle_focused_elem_change,
                    ).classes("w-44")

                    with ui.row().classes("items-center gap-2"):
                        ui.button("Select All Tests", on_click=self._select_all_tests).props("small flat")
                        ui.button("Deselect All", on_click=self._deselect_all_tests).props("small flat")
                        ui.button("Apply Filters", icon="filter_alt", on_click=self.refresh).classes("btn-primary")

            # 3. Diagnostic Summary Metric Cards
            self.cards_container = ui.row().classes("w-full gap-4 flex-wrap")

            # 4. Individual Test Summary Table
            with ui.card().classes("w-full panel-container"):
                ui.label("Test Summary Statistics").classes("panel-header")
                self.table_container = ui.column().classes("w-full")

            # 5. Interactive Graphs Section
            # Main plot: Measurements vs Elements (Full Width)
            with ui.card().classes("w-full panel-container"):
                ui.label("Main Graph: Measurements vs Elements across Selected Tests").classes("panel-header")
                self.chart_elem_container = ui.column().classes("w-full")

            # 2-column grid for Frequency Plot and Matrix Heatmap
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Measurements vs Frequency Channel").classes("panel-header")
                    self.chart_freq_container = ui.column().classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Matrix Heatmap (Elements x Frequencies)").classes("panel-header")
                        self.heat_test_select = ui.select(
                            options=self.manager.current_dataset.get_test_ids() or ["No tests"],
                            value=self.heatmap_test_id,
                            label="Heatmap Test",
                            on_change=self._handle_heat_test_change,
                        ).classes("w-44")
                    self.chart_heat_container = ui.column().classes("w-full")

            # 6. Statistical Distribution & Anomaly Records
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    with ui.row().classes("w-full justify-between items-center"):
                        ui.label("Measurement Value Distribution").classes("panel-header")
                        with ui.row().classes("items-center gap-2"):
                            ui.button("Histogram", on_click=lambda: self._set_dist_mode("histogram")).props("small flat")
                            ui.button("Box Plots", on_click=lambda: self._set_dist_mode("box")).props("small flat")
                    self.chart_dist_container = ui.column().classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Abnormal Measurements & Threshold Violations").classes("panel-header")
                    self.anomalies_table_container = ui.column().classes("w-full")

        # Initial render
        self.refresh()

    def refresh(self):
        """Update all data views, metrics cards, tables, and graphs."""
        self._update_cards()
        self._update_summary_table()
        self._update_element_chart()
        self._update_frequency_chart()
        self._update_heatmap()
        self._update_distribution_chart()
        self._update_anomalies_table()
        self._update_control_options()

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
            ("Data Type", f"{summary.data_type} ({summary.unit})"),
            ("Loaded Tests", str(summary.test_count)),
            ("Elements x Freqs", f"{summary.element_count} x {summary.frequency_count}"),
            ("Mean Measurement", f"{summary.overall_mean:.2f} {summary.unit}"),
            ("Min / Max", f"{summary.overall_min:.1f} / {summary.overall_max:.1f}"),
            ("Std Dev", f"{summary.overall_std:.2f} {summary.unit}"),
            ("Missing / Invalid", str(summary.total_missing_invalid)),
            ("Threshold Violations", str(summary.total_threshold_violations)),
        ]

        with self.cards_container:
            for label, val in cards_data:
                with ui.card().classes("metric-card flex-1 min-w-[150px]"):
                    ui.label(label).classes("metric-title")
                    val_color = "text-red-600" if label == "Threshold Violations" and int(val) > 0 else ""
                    ui.label(val).classes(f"metric-val {val_color}")

    def _update_summary_table(self):
        self.table_container.clear()
        summary = self.manager.get_summary_metrics()

        columns = [
            {"name": "test_id", "label": "Test ID", "field": "test_id", "sortable": True},
            {"name": "mean", "label": f"Mean ({summary.unit})", "field": "mean", "sortable": True},
            {"name": "std_dev", "label": "Std Dev", "field": "std_dev", "sortable": True},
            {"name": "min_val", "label": "Min", "field": "min_val", "sortable": True},
            {"name": "max_val", "label": "Max", "field": "max_val", "sortable": True},
            {"name": "median", "label": "Median", "field": "median", "sortable": True},
            {"name": "missing", "label": "Missing", "field": "missing_count", "sortable": True},
            {"name": "violations", "label": "Violations", "field": "threshold_violations", "sortable": True},
            {"name": "status", "label": "Status", "field": "status", "sortable": True},
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
                ui.label("No test logs loaded yet. Upload CSV files or click 'Load Sample Dataset' above.").classes("text-gray-500 italic p-4")
            else:
                ui.table(columns=columns, rows=rows, row_key="test_id").classes("w-full")

    def _update_element_chart(self):
        self.chart_elem_container.clear()
        frames = self.manager.get_filtered_frames()
        fig = create_measurements_vs_elements_plot(
            frames,
            frequency_label=self.manager.focused_frequency,
            focused_element=self.manager.focused_element,
            phase_mode=self.manager.phase_display_mode,
            thresholds=self.manager.thresholds,
            height=430,
        )
        with self.chart_elem_container:
            ui.plotly(fig).classes("w-full")

    def _update_frequency_chart(self):
        self.chart_freq_container.clear()
        frames = self.manager.get_filtered_frames()
        fig = create_measurements_vs_frequency_plot(
            frames,
            element_id=self.manager.focused_element,
            focused_frequency=self.manager.focused_frequency,
            phase_mode=self.manager.phase_display_mode,
            thresholds=self.manager.thresholds,
            height=400,
        )
        with self.chart_freq_container:
            ui.plotly(fig).classes("w-full")

    def _update_heatmap(self):
        self.chart_heat_container.clear()
        dataset = self.manager.current_dataset
        test_frame = dataset.get_frame(self.heatmap_test_id) if self.heatmap_test_id else None
        if test_frame is None and dataset.frames:
            test_frame = next(iter(dataset.frames.values()))
            self.heatmap_test_id = test_frame.test_id

        fig = create_matrix_heatmap(
            test_frame,
            phase_mode=self.manager.phase_display_mode,
            height=400,
        )
        with self.chart_heat_container:
            ui.plotly(fig).classes("w-full")

    def _update_distribution_chart(self):
        self.chart_dist_container.clear()
        frames = self.manager.get_filtered_frames()
        fig = create_distribution_plot(
            frames,
            phase_mode=self.manager.phase_display_mode,
            plot_type=self.dist_mode,
            thresholds=self.manager.thresholds,
            height=380,
        )
        with self.chart_dist_container:
            ui.plotly(fig).classes("w-full")

    def _update_anomalies_table(self):
        self.anomalies_table_container.clear()
        anomalies = self.manager.get_all_anomalies()

        columns = [
            {"name": "test_id", "label": "Test", "field": "test_id", "sortable": True},
            {"name": "elem", "label": "Element", "field": "element_id", "sortable": True},
            {"name": "freq", "label": "Channel", "field": "frequency_label", "sortable": True},
            {"name": "val", "label": "Measured", "field": "measured_value", "sortable": True},
            {"name": "limit", "label": "Limit", "field": "expected_or_limit", "sortable": True},
            {"name": "dev", "label": "Deviation", "field": "deviation", "sortable": True},
            {"name": "severity", "label": "Severity", "field": "severity", "sortable": True},
            {"name": "reason", "label": "Reason", "field": "reason"},
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
                ui.label("No abnormal measurements found. System nominal.").classes("text-green-600 font-semibold p-4")
            else:
                ui.table(columns=columns, rows=rows, pagination=10).classes("w-full")

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
