"""Test Comparison tab implementation.
"""

from typing import Callable, Optional
from nicegui import ui

from app.core.session_manager import SessionManager
from app.core.statistics import compute_difference_statistics
from app.visualization.comparison_plots import (
    create_element_stability_curve,
    create_frequency_stability_curve,
    create_test_difference_curve,
)
from app.visualization.heatmaps import (
    create_difference_heatmap,
    create_stability_heatmap,
)
from app.visualization.line_plots import create_measurements_vs_elements_plot


class TestComparisonView:
    """View component rendering the Test Comparison workspace."""

    def __init__(self, manager: SessionManager, on_update: Optional[Callable[[], None]] = None):
        self.manager = manager
        self.on_update = on_update

        # UI container references
        self.cards_container = None
        self.chart_diff_curve_container = None
        self.chart_diff_heat_container = None
        self.chart_stab_heat_container = None
        self.chart_elem_stab_container = None
        self.chart_freq_stab_container = None
        self.elem_ranking_container = None
        self.freq_ranking_container = None

    def render(self):
        """Construct the Test Comparison tab layout."""
        with ui.column().classes("w-full p-4 gap-4"):
            # 1. Comparison Selectors & Controls
            with ui.card().classes("w-full panel-container"):
                ui.label("Test-to-Test Baseline Comparison Settings").classes("panel-header")
                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    dataset = self.manager.current_dataset
                    test_ids = dataset.get_test_ids() or ["No tests"]

                    self.ref_select = ui.select(
                        options=test_ids,
                        value=self.manager.baseline_test_id,
                        label="Baseline Reference Test",
                        on_change=self._handle_ref_change,
                    ).classes("w-52")

                    self.comp_select = ui.select(
                        options=test_ids,
                        value=self.manager.comparison_test_id,
                        label="Comparison Target Test",
                        on_change=self._handle_comp_change,
                    ).classes("w-52")

                    dataset_freqs = dataset.get_common_frequencies() or ["A"]
                    self.freq_select = ui.select(
                        options=dataset_freqs,
                        value=self.manager.focused_frequency,
                        label="Frequency Channel",
                        on_change=self._handle_freq_change,
                    ).classes("w-36")

                    ui.button("Recalculate Comparisons", icon="refresh", on_click=self.refresh).classes("btn-primary")

            # 2. Difference Statistics Summary Cards
            self.cards_container = ui.row().classes("w-full gap-4 flex-wrap")

            # 3. Difference Curve & Difference Heatmap
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Difference Curve Across Elements (Target minus Baseline)").classes("panel-header")
                    self.chart_diff_curve_container = ui.column().classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    ui.label("2D Difference Heatmap (Target minus Baseline)").classes("panel-header")
                    self.chart_diff_heat_container = ui.column().classes("w-full")

            # 4. Cross-Test Stability Heatmap & Consistency Curves
            with ui.card().classes("w-full panel-container"):
                ui.label("Cross-Test Stability Heatmap (Std Dev across All Tests)").classes("panel-header")
                self.chart_stab_heat_container = ui.column().classes("w-full")

            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Per-Element Consistency Across Tests").classes("panel-header")
                    self.chart_elem_stab_container = ui.column().classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Per-Frequency Consistency Across Tests").classes("panel-header")
                    self.chart_freq_stab_container = ui.column().classes("w-full")

            # 5. Stability Rankings Tables (Unstable Elements & Frequencies)
            with ui.row().classes("w-full gap-4 items-start"):
                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Most Unstable Elements Ranking").classes("panel-header")
                    self.elem_ranking_container = ui.column().classes("w-full")

                with ui.card().classes("flex-1 panel-container"):
                    ui.label("Most Unstable Frequency Channels Ranking").classes("panel-header")
                    self.freq_ranking_container = ui.column().classes("w-full")

        self.refresh()

    def refresh(self):
        """Update all comparison charts and tables."""
        dataset = self.manager.current_dataset
        test_ids = dataset.get_test_ids()
        if test_ids:
            self.ref_select.options = test_ids
            self.comp_select.options = test_ids
            if not self.manager.baseline_test_id or self.manager.baseline_test_id not in test_ids:
                self.manager.baseline_test_id = test_ids[0]
                self.ref_select.value = test_ids[0]
            if not self.manager.comparison_test_id or self.manager.comparison_test_id not in test_ids:
                self.manager.comparison_test_id = test_ids[1] if len(test_ids) > 1 else test_ids[0]
                self.comp_select.value = self.manager.comparison_test_id

        freqs = dataset.get_common_frequencies()
        if freqs:
            self.freq_select.options = freqs

        self._update_cards()
        self._update_diff_curve()
        self._update_diff_heatmap()
        self._update_stability_charts()
        self._update_rankings()

    def _update_cards(self):
        self.cards_container.clear()
        ref_frame = self.manager.get_baseline_frame()
        comp_frame = self.manager.get_comparison_frame()
        unit = "deg" if self.manager.active_data_type == "PHASE" else "dB"

        if ref_frame and comp_frame:
            stats = compute_difference_statistics(comp_frame, ref_frame, phase_mode=self.manager.phase_display_mode)
            cards = [
                ("Baseline Reference", ref_frame.test_id),
                ("Comparison Target", comp_frame.test_id),
                ("Mean Difference", f"{stats.mean_diff:+.2f} {unit}"),
                ("RMS Difference", f"{stats.rms_diff:.2f} {unit}"),
                ("Max |Difference|", f"{stats.max_abs_diff:.2f} {unit}"),
                ("Std of Differences", f"{stats.std_diff:.2f} {unit}"),
            ]
        else:
            cards = [
                ("Baseline Reference", "None"),
                ("Comparison Target", "None"),
                ("Mean Difference", f"0.00 {unit}"),
                ("RMS Difference", f"0.00 {unit}"),
                ("Max |Difference|", f"0.00 {unit}"),
                ("Std of Differences", f"0.00 {unit}"),
            ]

        with self.cards_container:
            for label, val in cards:
                with ui.card().classes("metric-card flex-1 min-w-[150px]"):
                    ui.label(label).classes("metric-title")
                    ui.label(val).classes("metric-val")

    def _update_diff_curve(self):
        self.chart_diff_curve_container.clear()
        ref_frame = self.manager.get_baseline_frame()
        comp_frame = self.manager.get_comparison_frame()
        fig = create_test_difference_curve(
            comp_frame,
            ref_frame,
            frequency_label=self.manager.focused_frequency,
            phase_mode=self.manager.phase_display_mode,
            height=380,
        )
        with self.chart_diff_curve_container:
            ui.plotly(fig).classes("w-full")

    def _update_diff_heatmap(self):
        self.chart_diff_heat_container.clear()
        ref_frame = self.manager.get_baseline_frame()
        comp_frame = self.manager.get_comparison_frame()
        fig = create_difference_heatmap(
            comp_frame,
            ref_frame,
            phase_mode=self.manager.phase_display_mode,
            height=380,
        )
        with self.chart_diff_heat_container:
            ui.plotly(fig).classes("w-full")

    def _update_stability_charts(self):
        self.chart_stab_heat_container.clear()
        self.chart_elem_stab_container.clear()
        self.chart_freq_stab_container.clear()

        frames = self.manager.get_filtered_frames()
        if len(frames) < 2:
            msg = "At least 2 tests must be loaded to calculate stability metrics."
            for c in (self.chart_stab_heat_container, self.chart_elem_stab_container, self.chart_freq_stab_container):
                with c:
                    ui.label(msg).classes("text-gray-500 italic p-4")
            return

        stability = self.manager.get_stability_metrics()
        elem_ids = frames[0].element_ids
        freq_labels = frames[0].frequency_labels
        data_type = self.manager.active_data_type

        # Stability heatmap
        fig_stab_heat = create_stability_heatmap(stability, elem_ids, freq_labels, data_type=data_type, height=360)
        with self.chart_stab_heat_container:
            ui.plotly(fig_stab_heat).classes("w-full")

        # Element stability curve
        fig_elem = create_element_stability_curve(stability, elem_ids, data_type=data_type, height=350)
        with self.chart_elem_stab_container:
            ui.plotly(fig_elem).classes("w-full")

        # Frequency stability curve
        fig_freq = create_frequency_stability_curve(stability, freq_labels, data_type=data_type, height=350)
        with self.chart_freq_stab_container:
            ui.plotly(fig_freq).classes("w-full")

    def _update_rankings(self):
        self.elem_ranking_container.clear()
        self.freq_ranking_container.clear()

        elem_rankings = self.manager.get_element_rankings()
        freq_rankings = self.manager.get_frequency_rankings()
        unit = "deg" if self.manager.active_data_type == "PHASE" else "dB"

        elem_cols = [
            {"name": "elem", "label": "Element", "field": "element_id", "sortable": True},
            {"name": "std", "label": f"Avg Std Dev ({unit})", "field": "std_dev", "sortable": True},
            {"name": "spread", "label": f"Spread ({unit})", "field": "spread", "sortable": True},
            {"name": "anoms", "label": "Anomalies", "field": "anomaly_count", "sortable": True},
            {"name": "status", "label": "Status", "field": "status", "sortable": True},
        ]
        elem_rows = [
            {
                "element_id": f"Element {r.element_id}",
                "std_dev": f"{r.std_dev:.3f}",
                "spread": f"{r.spread:.3f}",
                "anomaly_count": r.anomaly_count,
                "status": r.status,
            }
            for r in elem_rankings[:20]
        ]

        with self.elem_ranking_container:
            if not elem_rows:
                ui.label("No element ranking data available.").classes("text-gray-500 italic p-2")
            else:
                ui.table(columns=elem_cols, rows=elem_rows, pagination=5).classes("w-full")

        freq_cols = [
            {"name": "freq", "label": "Channel", "field": "frequency_label", "sortable": True},
            {"name": "std", "label": f"Avg Std Dev ({unit})", "field": "std_dev", "sortable": True},
            {"name": "spread", "label": f"Spread ({unit})", "field": "spread", "sortable": True},
            {"name": "anoms", "label": "Anomalies", "field": "anomaly_count", "sortable": True},
            {"name": "status", "label": "Status", "field": "status", "sortable": True},
        ]
        freq_rows = [
            {
                "frequency_label": f"Channel {r.frequency_label}",
                "std_dev": f"{r.std_dev:.3f}",
                "spread": f"{r.spread:.3f}",
                "anomaly_count": r.anomaly_count,
                "status": r.status,
            }
            for r in freq_rankings[:20]
        ]

        with self.freq_ranking_container:
            if not freq_rows:
                ui.label("No frequency ranking data available.").classes("text-gray-500 italic p-2")
            else:
                ui.table(columns=freq_cols, rows=freq_rows, pagination=5).classes("w-full")

    def _handle_ref_change(self, e):
        self.manager.baseline_test_id = e.value
        self.refresh()

    def _handle_comp_change(self, e):
        self.manager.comparison_test_id = e.value
        self.refresh()

    def _handle_freq_change(self, e):
        self.manager.focused_frequency = e.value
        self._update_diff_curve()
