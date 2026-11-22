"""Test Comparison workspace for analyzing radar test-to-baseline deltas,
cross-test stability distributions, and element/channel hardware divergence.
"""

from typing import Callable, Optional
from nicegui import ui

from app.core.session_manager import SessionManager
from app.core.statistics import compute_difference_statistics
from app.ui.components import create_card_header, create_kpi_card, open_expanded_chart_dialog
from app.visualization.comparison_plots import (
    create_element_stability_curve,
    create_frequency_stability_curve,
    create_test_difference_curve,
)
from app.visualization.heatmaps import (
    create_difference_heatmap,
    create_stability_heatmap,
)


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

        # Cached figures for modal expansion
        self._last_diff_curve_fig = None
        self._last_diff_heat_fig = None
        self._last_stab_heat_fig = None
        self._last_elem_stab_fig = None
        self._last_freq_stab_fig = None

    def render(self):
        """Construct the Test Comparison tab layout."""
        with ui.column().classes("w-full gap-4"):
            # 1. Comparison Toolbar Card
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center mb-2"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("compare_arrows", size="20px", color="primary")
                        ui.label("Test-to-Test Baseline Comparison Setup").classes("card-title m-0")
                    ui.label("Isolate manufacturing variance, channel drift, and phase jumps").classes("text-xs text-slate-500 hidden sm:block")

                with ui.row().classes("w-full items-center gap-3 flex-wrap"):
                    dataset = self.manager.current_dataset
                    test_ids = dataset.get_test_ids() or ["No tests"]

                    self.ref_select = ui.select(
                        options=test_ids,
                        value=self.manager.baseline_test_id,
                        label="Baseline Reference Test",
                        on_change=self._handle_ref_change,
                    ).props("outlined dense options-dense").classes("w-48")

                    self.comp_select = ui.select(
                        options=test_ids,
                        value=self.manager.comparison_test_id,
                        label="Comparison Target Test",
                        on_change=self._handle_comp_change,
                    ).props("outlined dense options-dense").classes("w-48")

                    dataset_freqs = dataset.get_common_frequencies() or ["A"]
                    self.freq_select = ui.select(
                        options=dataset_freqs,
                        value=self.manager.focused_frequency,
                        label="Channel for Delta Curve",
                        on_change=self._handle_freq_change,
                    ).props("outlined dense options-dense").classes("w-36")

                    ui.button(
                        "Recalculate Deltas",
                        icon="refresh",
                        on_click=self.refresh,
                    ).classes("btn-primary")

            # 2. Difference Statistics KPI Row
            self.cards_container = ui.element("div").classes("kpi-row")

            # 3. Main Analytical Workspace: Delta Curve & 2D Divergence Heatmap
            with ui.row().classes("w-full gap-4 items-start no-wrap flex-col lg:flex-row"):
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title=f"Delta Curve across Elements (Channel {self.manager.focused_frequency})",
                        subtitle="Target test minus baseline reference",
                        icon="show_chart",
                        on_expand=lambda: open_expanded_chart_dialog(
                            f"Delta Curve: {self.manager.comparison_test_id} vs {self.manager.baseline_test_id}",
                            self._last_diff_curve_fig,
                        ),
                    )
                    self.chart_diff_curve_container = ui.column().classes("w-full")

                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="2D Difference Heatmap (256×64)",
                        subtitle="Full element-by-channel divergence",
                        icon="grid_on",
                        on_expand=lambda: open_expanded_chart_dialog(
                            f"Difference Heatmap: {self.manager.comparison_test_id} minus {self.manager.baseline_test_id}",
                            self._last_diff_heat_fig,
                        ),
                    )
                    self.chart_diff_heat_container = ui.column().classes("w-full")

            # 4. Multi-Test Stability Heatmap
            with ui.card().classes("app-card w-full"):
                create_card_header(
                    title="Cross-Test Stability Heatmap (Std Dev across All Tests)",
                    subtitle="Highlights matrix regions with high measurement volatility",
                    icon="grain",
                    on_expand=lambda: open_expanded_chart_dialog(
                        "Cross-Test Stability Heatmap",
                        self._last_stab_heat_fig,
                    ),
                )
                self.chart_stab_heat_container = ui.column().classes("w-full")

            # 5. Side-by-Side Consistency Profiles
            with ui.row().classes("w-full gap-4 items-start no-wrap flex-col lg:flex-row"):
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="Per-Element Consistency across Tests",
                        subtitle="Average standard deviation per element",
                        icon="bar_chart",
                        on_expand=lambda: open_expanded_chart_dialog(
                            "Per-Element Stability across Tests",
                            self._last_elem_stab_fig,
                        ),
                    )
                    self.chart_elem_stab_container = ui.column().classes("w-full")

                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="Per-Frequency Channel Consistency across Tests",
                        subtitle="Average standard deviation per channel",
                        icon="bar_chart",
                        on_expand=lambda: open_expanded_chart_dialog(
                            "Per-Frequency Channel Stability",
                            self._last_freq_stab_fig,
                        ),
                    )
                    self.chart_freq_stab_container = ui.column().classes("w-full")

            # 6. Stability Rankings Tables (Interactive Click-to-Focus)
            with ui.row().classes("w-full gap-4 items-start no-wrap flex-col lg:flex-row"):
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="Most Unstable Elements Ranking",
                        subtitle="Sorted by dispersion across test runs (click to focus)",
                        icon="leaderboard",
                    )
                    self.elem_ranking_container = ui.column().classes("w-full")

                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="Most Unstable Frequency Channels Ranking",
                        subtitle="Sorted by channel variance (click to focus)",
                        icon="leaderboard",
                    )
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
                ("Baseline Reference", ref_frame.test_id, "", "Anchor test", False),
                ("Comparison Target", comp_frame.test_id, "", "Evaluated test", False),
                ("Mean Difference", f"{stats.mean_diff:+.2f}", unit, "Average offset", False),
                ("RMS Difference", f"{stats.rms_diff:.2f}", unit, "Root mean square", False),
                ("Max |Difference|", f"{stats.max_abs_diff:.2f}", unit, "Peak divergence", False),
                ("Std of Deltas", f"{stats.std_diff:.2f}", unit, "Delta dispersion", False),
            ]
        else:
            cards = [
                ("Baseline Reference", "None", "", "No baseline", False),
                ("Comparison Target", "None", "", "No target", False),
                ("Mean Difference", f"0.00", unit, "Average offset", False),
                ("RMS Difference", f"0.00", unit, "Root mean square", False),
                ("Max |Difference|", f"0.00", unit, "Peak divergence", False),
                ("Std of Deltas", f"0.00", unit, "Delta dispersion", False),
            ]

        with self.cards_container:
            for label, val, u, sub, is_alert in cards:
                create_kpi_card(label, val, unit=u, subtext=sub, is_alert=is_alert)

    def _update_diff_curve(self):
        self.chart_diff_curve_container.clear()
        ref_frame = self.manager.get_baseline_frame()
        comp_frame = self.manager.get_comparison_frame()
        self._last_diff_curve_fig = create_test_difference_curve(
            comp_frame,
            ref_frame,
            frequency_label=self.manager.focused_frequency,
            phase_mode=self.manager.phase_display_mode,
            height=340,
            show_title=False,
        )
        with self.chart_diff_curve_container:
            ui.plotly(self._last_diff_curve_fig).classes("w-full")

    def _update_diff_heatmap(self):
        self.chart_diff_heat_container.clear()
        ref_frame = self.manager.get_baseline_frame()
        comp_frame = self.manager.get_comparison_frame()
        self._last_diff_heat_fig = create_difference_heatmap(
            comp_frame,
            ref_frame,
            phase_mode=self.manager.phase_display_mode,
            height=340,
            show_title=False,
        )
        with self.chart_diff_heat_container:
            ui.plotly(self._last_diff_heat_fig).classes("w-full")

    def _update_stability_charts(self):
        self.chart_stab_heat_container.clear()
        self.chart_elem_stab_container.clear()
        self.chart_freq_stab_container.clear()

        frames = self.manager.get_filtered_frames()
        if len(frames) < 2:
            msg = "At least 2 tests must be loaded to calculate cross-test stability metrics."
            for c in (self.chart_stab_heat_container, self.chart_elem_stab_container, self.chart_freq_stab_container):
                with c:
                    ui.label(msg).classes("text-slate-400 italic p-3 text-center")
            return

        stability = self.manager.get_stability_metrics()
        elem_ids = frames[0].element_ids
        freq_labels = frames[0].frequency_labels
        data_type = self.manager.active_data_type

        # Stability heatmap
        self._last_stab_heat_fig = create_stability_heatmap(
            stability, elem_ids, freq_labels, data_type=data_type, height=340, show_title=False
        )
        with self.chart_stab_heat_container:
            ui.plotly(self._last_stab_heat_fig).classes("w-full")

        # Element stability curve
        self._last_elem_stab_fig = create_element_stability_curve(
            stability, elem_ids, data_type=data_type, height=320, show_title=False
        )
        with self.chart_elem_stab_container:
            ui.plotly(self._last_elem_stab_fig).classes("w-full")

        # Frequency stability curve
        self._last_freq_stab_fig = create_frequency_stability_curve(
            stability, freq_labels, data_type=data_type, height=320, show_title=False
        )
        with self.chart_freq_stab_container:
            ui.plotly(self._last_freq_stab_fig).classes("w-full")

    def _update_rankings(self):
        self.elem_ranking_container.clear()
        self.freq_ranking_container.clear()

        elem_rankings = self.manager.get_element_rankings()
        freq_rankings = self.manager.get_frequency_rankings()
        unit = "deg" if self.manager.active_data_type == "PHASE" else "dB"

        elem_cols = [
            {"name": "elem", "label": "Element", "field": "element_id", "sortable": True, "align": "left"},
            {"name": "std", "label": f"Avg Std Dev ({unit})", "field": "std_dev", "sortable": True, "align": "right"},
            {"name": "spread", "label": f"Spread ({unit})", "field": "spread", "sortable": True, "align": "right"},
            {"name": "anoms", "label": "Anomalies", "field": "anomaly_count", "sortable": True, "align": "right"},
            {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "center"},
        ]
        elem_rows = [
            {
                "raw_id": r.element_id,
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
                ui.label("No element ranking data available.").classes("text-slate-400 italic p-3")
            else:
                table_e = ui.table(columns=elem_cols, rows=elem_rows, pagination=6).props("dense flat bordered").classes("w-full cursor-pointer")
                table_e.on("rowClick", lambda e: self._on_element_row_clicked(e))

        freq_cols = [
            {"name": "freq", "label": "Channel", "field": "frequency_label", "sortable": True, "align": "left"},
            {"name": "std", "label": f"Avg Std Dev ({unit})", "field": "std_dev", "sortable": True, "align": "right"},
            {"name": "spread", "label": f"Spread ({unit})", "field": "spread", "sortable": True, "align": "right"},
            {"name": "anoms", "label": "Anomalies", "field": "anomaly_count", "sortable": True, "align": "right"},
            {"name": "status", "label": "Status", "field": "status", "sortable": True, "align": "center"},
        ]
        freq_rows = [
            {
                "raw_label": r.frequency_label,
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
                ui.label("No frequency ranking data available.").classes("text-slate-400 italic p-3")
            else:
                table_f = ui.table(columns=freq_cols, rows=freq_rows, pagination=6).props("dense flat bordered").classes("w-full cursor-pointer")
                table_f.on("rowClick", lambda e: self._on_frequency_row_clicked(e))

    def _on_element_row_clicked(self, e):
        """Focus selected element from table click."""
        try:
            row_data = e.args[1]
            raw_id = row_data.get("raw_id")
            if raw_id is not None:
                self.manager.focused_element = int(raw_id)
                ui.notify(f"Focused Element {raw_id}", type="info")
                if self.on_update:
                    self.on_update()
        except Exception:
            pass

    def _on_frequency_row_clicked(self, e):
        """Focus selected channel from table click."""
        try:
            row_data = e.args[1]
            raw_label = row_data.get("raw_label")
            if raw_label:
                self.manager.focused_frequency = raw_label
                self.freq_select.value = raw_label
                self._update_diff_curve()
                ui.notify(f"Focused Channel {raw_label}", type="info")
        except Exception:
            pass

    def _handle_ref_change(self, e):
        self.manager.baseline_test_id = e.value
        self.refresh()

    def _handle_comp_change(self, e):
        self.manager.comparison_test_id = e.value
        self.refresh()

    def _handle_freq_change(self, e):
        self.manager.focused_frequency = e.value
        self._update_diff_curve()
