"""File Diagnostics workspace for offline radar test logs.
Redesigned with modern engineering analytics aesthetics, compact dataset toolbar,
balanced KPI grid, expandable high-performance charts, and streamlined controls.
"""

import io
import os
from typing import Callable, Dict, Optional, Tuple
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

        # Checkbox picker state: controls are kept mounted while plots refresh.
        self.test_select_button = None
        self.test_select_menu = None
        self.test_select_summary = None
        self.test_select_all_checkbox = None
        self.test_search_input = None
        self.test_checkbox_container = None
        self.test_checkboxes: Dict[str, object] = {}
        self.test_checkbox_rows: Dict[str, object] = {}
        self._shown_test_ids: Tuple[str, ...] = ()
        self._test_context = None
        self._selection_explicitly_cleared = False
        self._syncing_test_picker = False

        # Cached figures for modal expansion
        self._last_elem_fig = None
        self._last_freq_fig = None
        self._last_heat_fig = None
        self._last_dist_fig = None

    def render(self):
        """Construct the entire File Diagnostics tab layout."""
        # Match the custom checkbox picker to NiceGUI/Quasar's outlined, dense
        # q-field controls. Unlike a multi-select with chips, this trigger stays
        # one line high regardless of how many tests are selected.
        ui.add_head_html("""<style>
            .psp-test-select-trigger.q-btn {
                box-sizing: border-box;
                height: 40px;
                min-height: 40px;
                padding: 0 9px;
                border: 1px solid rgba(0, 0, 0, 0.24);
                border-radius: 4px;
                background: #fff !important;
                color: #1f2937 !important;
                box-shadow: none !important;
                text-align: left;
            }
            .psp-test-select-trigger.q-btn:hover {
                border-color: rgba(0, 0, 0, 0.65);
            }
            .psp-test-select-trigger.q-btn:focus-visible {
                border: 2px solid #1976d2;
                padding: 0 8px;
                outline: none;
            }
            .psp-test-select-trigger .q-btn__content {
                width: 100%;
                justify-content: flex-start;
                align-items: center;
            }
            .psp-test-select-body {
                width: 100%;
                min-width: 0;
                text-align: left;
            }
            .psp-test-select-label {
                font-size: 10px;
                line-height: 13px;
                font-weight: 400;
                color: #64748b;
                white-space: nowrap;
            }
            .psp-test-select-summary {
                font-size: 14px;
                line-height: 18px;
                font-weight: 400;
                color: #111827;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
            }
            .psp-test-select-chevron { color: #64748b; flex-shrink: 0; }
        </style>""")
        with ui.column().classes("w-full gap-4"):
            # 1. Dataset Management Toolbar
            with ui.card().classes("app-card w-full"):
                self.dataset_info_container = ui.column().classes("w-full")
                ui.upload(
                    multiple=True,
                    auto_upload=True,
                    on_upload=self._handle_upload,
                    label="Drag & Drop CSV / ZIP files here or click to browse",
                ).props('accept=".csv,.zip"').classes("w-full border-2 border-dashed border-slate-200 rounded-lg p-1 mt-2")

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

                    # Custom checkbox selector styled exactly like the adjacent
                    # 40px-high outlined, dense Quasar fields: small label inside
                    # the outline, normal dark value text, neutral border/chevron.
                    # Keep the menu logic as-is so scrolling and live updates work.
                    with ui.column().classes("gap-0 shrink-0").style(
                        "width: 260px; max-width: 100%; height: 40px;"
                    ):
                        with ui.button().props("flat no-caps dense").classes(
                            "w-full psp-test-select-trigger"
                        ) as self.test_select_button:
                            with ui.column().classes("psp-test-select-body gap-0"):
                                ui.label("Selected Tests").classes("psp-test-select-label")
                                with ui.row().classes("w-full no-wrap items-center justify-between gap-2"):
                                    self.test_select_summary = ui.label("No Tests Selected").classes(
                                        "psp-test-select-summary"
                                    )
                                    ui.icon("arrow_drop_down", size="18px").classes(
                                        "psp-test-select-chevron"
                                    )

                            # QMenu is a floating overlay, not part of the filter panel's
                            # height. Do NOT use the auto-close prop: checkbox clicks
                            # should leave the dropdown open until the user is done.
                            with ui.menu().props('anchor="bottom left" self="top left"').style(
                                "width: 330px; max-width: calc(100vw - 32px);"
                            ) as self.test_select_menu:
                                with ui.column().classes("w-full gap-2 p-3"):
                                    self.test_search_input = ui.input(
                                        placeholder="Search tests...",
                                        on_change=lambda e: self._filter_test_checkboxes(e.value),
                                    ).props("outlined dense clearable").classes("w-full")

                                    with ui.row().classes("w-full items-center justify-between"):
                                        self.test_select_all_checkbox = ui.checkbox(
                                            "Select All",
                                            on_change=self._handle_select_all_checkbox,
                                        ).props("dense color=primary").classes("text-sm")
                                        ui.button("Clear", on_click=self._deselect_all_tests).props(
                                            "flat dense no-caps size=sm"
                                        ).classes("text-blue-600")

                                    ui.separator()
                                    # Native overflow ensures mouse wheel and touchpad
                                    # scrolling work for dozens/hundreds of test logs.
                                    self.test_checkbox_container = ui.column().classes(
                                        "w-full gap-0"
                                    ).style(
                                        "max-height: 280px; overflow-y: auto; overscroll-behavior: contain;"
                                    )
                                    self.test_search_empty_label = ui.label("No matching tests").classes(
                                        "text-xs text-slate-500 px-2"
                                    )
                                    self.test_search_empty_label.set_visibility(False)
                                    ui.separator()
                                    with ui.row().classes("w-full justify-end"):
                                        ui.button(
                                            "Done", on_click=self.test_select_menu.close,
                                        ).props("flat dense no-caps size=sm").classes("text-blue-600")

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
                    ).classes("btn-primary").style("height: 40px; min-height: 40px;")

            # 3. Diagnostic Summary KPI Row
            self.cards_container = ui.element("div").classes("kpi-row")

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

            # 7. Secondary Analysis Section (Sub-tabs for Test Summary, Distribution, and Outliers)
            with ui.card().classes("app-card w-full"):
                with ui.tabs().classes("w-full border-b border-slate-200") as analysis_tabs:
                    tab_summary = ui.tab("Test Summary Statistics", icon="table_chart")
                    tab_dist = ui.tab("Measurement Distribution", icon="bar_chart")
                    tab_anom = ui.tab("Threshold Violations & Outliers", icon="warning")

                with ui.tab_panels(analysis_tabs, value=tab_summary).classes("w-full p-2"):
                    with ui.tab_panel(tab_summary).classes("p-0"):
                        self.table_container = ui.column().classes("w-full pt-2")

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
        # Reconcile dataset/type changes before calculating chart statistics.
        self._update_control_options()
        self._update_dataset_toolbar()
        self._update_cards()
        self._update_summary_table()
        self._update_element_chart()
        self._update_frequency_chart()
        self._update_heatmap()
        self._update_distribution_chart()
        self._update_anomalies_table()

    def _update_dataset_toolbar(self):
        """Render clean import zone with dynamic sample buttons."""
        if not hasattr(self, 'dataset_info_container') or self.dataset_info_container is None:
            return
        self.dataset_info_container.clear()
        dataset = self.manager.current_dataset
        has_data = len(dataset.frames) > 0

        with self.dataset_info_container:
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
        """Synchronize available data and checkbox UI without losing explicit selections.

        This runs *before* graph and KPI updates. It only rebuilds checkbox
        elements when the actual list of test IDs changes, not on every toggle.
        """
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

        test_ids = list(dataset.get_test_ids())
        # A different data type or dataset object means a new choice context.
        context = (self.manager.active_data_type, id(dataset))
        context_changed = self._test_context is not None and context != self._test_context
        previous_options = self._shown_test_ids
        current_selection = list(self.manager.selected_test_ids or [])
        valid_selection = [tid for tid in test_ids if tid in current_selection]

        if context_changed:
            # Newly activated datasets default to all tests unless the SessionManager
            # has already selected valid test IDs for the new dataset.
            self._selection_explicitly_cleared = False
            if not valid_selection and test_ids:
                valid_selection = list(test_ids)
        elif (not current_selection and test_ids
              and not self._selection_explicitly_cleared):
            # First import with no manager-side default; an empty selection
            # explicitly requested by the user MUST NOT reach this branch.
            valid_selection = list(test_ids)
        elif (previous_options and set(current_selection) == set(previous_options)
              and not self._selection_explicitly_cleared
              and len(test_ids) > len(previous_options)
              and set(previous_options).issubset(test_ids)):
            # When new tests are appended while "all" was selected, keep "all".
            valid_selection = list(test_ids)

        if valid_selection != current_selection:
            self.manager.selected_test_ids = valid_selection

        self._test_context = context
        if tuple(test_ids) != self._shown_test_ids:
            self._shown_test_ids = tuple(test_ids)
            self._rebuild_test_checkboxes(test_ids)
        self._sync_test_checkboxes()

        # The heatmap shows a selected test. Keep it synchronized when choices
        # change instead of showing a test that was just excluded.
        active_ids = list(self.manager.selected_test_ids or [])
        heat_options = active_ids if active_ids else ["No tests selected"]
        self.heat_test_select.options = heat_options
        if self.heatmap_test_id not in active_ids:
            self.heatmap_test_id = active_ids[0] if active_ids else None
        if self.heat_test_select.value != (self.heatmap_test_id or "No tests selected"):
            self.heat_test_select.value = self.heatmap_test_id or "No tests selected"

    def _rebuild_test_checkboxes(self, test_ids):
        """Rebuild only when the available test list changes."""
        self._syncing_test_picker = True
        try:
            self.test_checkbox_container.clear()
            self.test_checkboxes.clear()
            self.test_checkbox_rows.clear()
            selected = set(self.manager.selected_test_ids or [])
            with self.test_checkbox_container:
                for test_id in test_ids:
                    with ui.row().classes("w-full items-center px-2 rounded hover:bg-blue-50") as row:
                        checkbox = ui.checkbox(
                            str(test_id),
                            value=test_id in selected,
                            on_change=lambda e, tid=test_id: self._handle_test_checkbox(tid, e.value),
                        ).props("dense color=primary").classes("w-full py-1 text-sm")
                    self.test_checkbox_rows[test_id] = row
                    self.test_checkboxes[test_id] = checkbox
        finally:
            self._syncing_test_picker = False
        self._filter_test_checkboxes(self.test_search_input.value or "")

    def _filter_test_checkboxes(self, search_text):
        """Filter visible rows without touching the selection or rebuilding the menu."""
        query = (search_text or "").strip().casefold()
        visible = 0
        for test_id, row in self.test_checkbox_rows.items():
            matches = query in str(test_id).casefold()
            row.set_visibility(matches)
            visible += int(matches)
        if hasattr(self, "test_search_empty_label"):
            self.test_search_empty_label.set_visibility(visible == 0)

    def _sync_test_checkboxes(self):
        """Update checkmarks and compact summary without triggering a selection loop."""
        selected = set(self.manager.selected_test_ids or [])
        total = len(self._shown_test_ids)
        count = sum(tid in selected for tid in self._shown_test_ids)
        if total == 0 or count == 0:
            summary = "No Tests Selected"
        elif count == total:
            summary = f"All Tests ({total})"
        else:
            summary = f"{count} of {total} Tests"
        self.test_select_summary.set_text(summary)
        self._syncing_test_picker = True
        try:
            for tid, checkbox in self.test_checkboxes.items():
                checked = tid in selected
                if checkbox.value != checked:
                    checkbox.value = checked
            all_selected = total > 0 and count == total
            if self.test_select_all_checkbox.value != all_selected:
                self.test_select_all_checkbox.value = all_selected
        finally:
            self._syncing_test_picker = False

    def _handle_test_checkbox(self, test_id: str, is_checked: bool):
        """Immediately apply a single test checkbox change, keeping the menu open."""
        if self._syncing_test_picker or test_id not in self._shown_test_ids:
            return
        selected = set(self.manager.selected_test_ids or [])
        if (test_id in selected) == bool(is_checked):
            return  # programmatic sync event, not a new user selection
        if is_checked:
            selected.add(test_id)
        else:
            selected.discard(test_id)
        self._apply_test_selection([tid for tid in self._shown_test_ids if tid in selected])

    def _handle_select_all_checkbox(self, e):
        """Toggle the Select All checkbox without reacting to programmatic sync."""
        if self._syncing_test_picker or not self._shown_test_ids:
            return
        current = set(self.manager.selected_test_ids or [])
        if e.value and len(current) != len(self._shown_test_ids):
            self._select_all_tests()
        elif not e.value and len(current) == len(self._shown_test_ids):
            self._deselect_all_tests()

    def _apply_test_selection(self, selected_ids):
        """Single source of truth for individual, bulk, and external selections."""
        available = set(self._shown_test_ids)
        selected = [tid for tid in dict.fromkeys(selected_ids) if tid in available]
        # Remember an explicit empty choice even if no tests were selected yet.
        # This prevents the next refresh from unexpectedly restoring "All Tests".
        self._selection_explicitly_cleared = not bool(selected)
        if selected == list(self.manager.selected_test_ids or []):
            self._sync_test_checkboxes()
            return
        self.manager.selected_test_ids = selected
        self._sync_test_checkboxes()
        # The menu and all checkboxes stay mounted while diagnostics refresh.
        self.refresh()
        if self.on_update:
            self.on_update()

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
        active_ids = set(self.manager.selected_test_ids or [])
        test_frame = (
            dataset.get_frame(self.heatmap_test_id)
            if self.heatmap_test_id and self.heatmap_test_id in active_ids
            else None
        )

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
        selected = set(self.manager.selected_test_ids or [])
        anomalies = [a for a in self.manager.get_all_anomalies() if a.test_id in selected]

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
        # Depending on NiceGUI version, it might be e.content or e.file or e.sender.
        # Let's inspect it to be safe, but usually it's just e.content.read()
        content = await e.content.read() if hasattr(e, 'content') else (await e.file.read() if hasattr(e, 'file') else None)
        if hasattr(e, 'name'):
            name = e.name
        elif hasattr(e, 'file') and hasattr(e.file, 'name'):
            name = e.file.name
        elif hasattr(e, 'content') and hasattr(e.content, 'name'):
            name = e.content.name
        else:
            name = "uploaded_file.csv"
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
        self._selection_explicitly_cleared = False
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
        self._selection_explicitly_cleared = False
        ui.notify(f"Loaded {loaded_count} sample {data_type} tests successfully!", type="positive")
        if self.type_select.value != data_type:
            self.type_select.value = data_type
        else:
            self.refresh()
            if self.on_update:
                self.on_update()

    def _clear_data(self):
        self.manager.clear_all()
        self._selection_explicitly_cleared = False
        ui.notify("All loaded test files cleared.", type="info")
        self.refresh()
        if self.on_update:
            self.on_update()

    def _handle_type_change(self, e):
        self.manager.set_active_data_type(e.value)
        self._selection_explicitly_cleared = False
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
        active_ids = set(self.manager.selected_test_ids or [])
        self.heatmap_test_id = e.value if e.value in active_ids else None
        self._update_heatmap()

    def _set_dist_mode(self, mode: str):
        self.dist_mode = mode
        self._update_distribution_chart()

    def _handle_test_selection_change(self, e):
        """Compatibility hook for any external code calling the old handler."""
        self._apply_test_selection(e.value or [])

    def _select_all_tests(self):
        self._apply_test_selection(list(self.manager.current_dataset.get_test_ids()))

    def _deselect_all_tests(self):
        self._apply_test_selection([])
