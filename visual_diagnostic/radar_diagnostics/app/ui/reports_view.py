"""Reports & Exports workspace for compiling consolidated HTML laboratory reports
and exporting structured telemetry logs and anomaly metrics as CSV.
"""

import os
from datetime import datetime
from nicegui import ui

from app.config import default_config
from app.core.session_manager import SessionManager
from app.reports.report_generator import (
    export_anomalies_to_csv,
    export_element_rankings_to_csv,
    export_frequency_rankings_to_csv,
    export_test_summary_to_csv,
    generate_html_report,
)
from app.ui.components import create_card_header


class ReportsView:
    """View component for generating and downloading reports and CSV exports."""

    def __init__(self, manager: SessionManager):
        self.manager = manager
        self.preview_container = None
        self.status_container = None
        self.last_report_path = None
        self.last_report_filename = None

    def render(self):
        """Construct the Reports & Exports tab layout."""
        with ui.column().classes("w-full gap-4"):
            # 2-Column Responsive Workspace: Config on Left, Preview on Right
            with ui.row().classes("w-full gap-4 items-start no-wrap flex-col lg:flex-row"):
                # Left Column: Report Setup & Export Actions (approx 420px wide)
                with ui.column().classes("w-full lg:w-[420px] gap-4 flex-shrink-0"):
                    # Report Configuration Card
                    with ui.card().classes("app-card w-full"):
                        create_card_header(
                            title="Laboratory Report Setup",
                            subtitle="Configure summary parameters & sections",
                            icon="assessment",
                        )

                        with ui.column().classes("w-full gap-3"):
                            # Current context
                            with ui.row().classes("w-full justify-between items-center p-2.5 bg-slate-50 rounded-lg border border-slate-200"):
                                with ui.column().classes("gap-0"):
                                    ui.label("Active Session").classes("text-[10px] font-bold text-slate-400 uppercase")
                                    ui.label(self.manager.session_name).classes("text-xs font-bold text-slate-800")
                                ui.label(self.manager.active_data_type).classes("chip-info")

                            self.report_title_input = ui.input(
                                label="Report Title",
                                value=f"PSP Radar Diagnostics Summary ({self.manager.active_data_type})",
                            ).props("outlined dense").classes("w-full")

                            ui.label("Included Report Sections:").classes("text-xs font-bold text-slate-700 uppercase mt-1")
                            with ui.column().classes("gap-1.5 pl-1"):
                                self.chk_summary = ui.checkbox("Statistical Metric Summaries", value=True).props("dense size=sm")
                                self.chk_charts = ui.checkbox("Embedded Element & Channel Plots", value=True).props("dense size=sm")
                                self.chk_anom = ui.checkbox("Anomaly Records & Tolerance Violations", value=True).props("dense size=sm")
                                self.chk_stability = ui.checkbox("Cross-Test Stability & Rankings", value=True).props("dense size=sm")

                            # Primary Action Button
                            ui.button(
                                "Generate Diagnostics Report",
                                icon="auto_graph",
                                on_click=self._handle_generate_html_report,
                            ).classes("btn-primary w-full py-2.5 mt-2")

                    # Structured CSV Exports Card
                    with ui.card().classes("app-card w-full"):
                        create_card_header(
                            title="Export Raw Data",
                            subtitle="Download tabular metrics as standard CSV",
                            icon="file_download",
                        )

                        with ui.column().classes("w-full gap-2"):
                            with ui.row().classes("w-full justify-between items-center p-2 rounded-lg hover:bg-slate-50 transition-colors"):
                                with ui.column().classes("gap-0"):
                                    ui.label("Test Summaries CSV").classes("text-xs font-bold text-slate-800")
                                    ui.label("Aggregated means, std dev, min/max per test").classes("text-[11px] text-slate-500")
                                ui.button(
                                    "Export",
                                    icon="download",
                                    on_click=self._handle_export_summary_csv,
                                ).classes("btn-secondary")

                            with ui.row().classes("w-full justify-between items-center p-2 rounded-lg hover:bg-slate-50 transition-colors"):
                                with ui.column().classes("gap-0"):
                                    ui.label("Anomalies List CSV").classes("text-xs font-bold text-slate-800")
                                    ui.label("Detailed log of threshold breaches").classes("text-[11px] text-slate-500")
                                ui.button(
                                    "Export",
                                    icon="download",
                                    on_click=self._handle_export_anomalies_csv,
                                ).classes("btn-secondary")

                            with ui.row().classes("w-full justify-between items-center p-2 rounded-lg hover:bg-slate-50 transition-colors"):
                                with ui.column().classes("gap-0"):
                                    ui.label("Element Stability CSV").classes("text-xs font-bold text-slate-800")
                                    ui.label("Per-element variance across test runs").classes("text-[11px] text-slate-500")
                                ui.button(
                                    "Export",
                                    icon="download",
                                    on_click=self._handle_export_elements_csv,
                                ).classes("btn-secondary")

                            with ui.row().classes("w-full justify-between items-center p-2 rounded-lg hover:bg-slate-50 transition-colors"):
                                with ui.column().classes("gap-0"):
                                    ui.label("Frequency Stability CSV").classes("text-xs font-bold text-slate-800")
                                    ui.label("Per-channel variance across test runs").classes("text-[11px] text-slate-500")
                                ui.button(
                                    "Export",
                                    icon="download",
                                    on_click=self._handle_export_frequencies_csv,
                                ).classes("btn-secondary")

                # Right Column: Interactive Report Preview & Status Panel
                with ui.card().classes("app-card flex-1 min-w-0 w-full"):
                    create_card_header(
                        title="Consolidated Report Preview",
                        subtitle="Standalone laboratory HTML document preview",
                        icon="preview",
                    )

                    self.status_container = ui.column().classes("w-full mb-3")
                    self.preview_container = ui.column().classes("w-full min-h-[500px]")

        self.refresh()

    def refresh(self):
        """Refresh preview if report exists."""
        self._update_status_and_preview()

    def _update_status_and_preview(self):
        if not self.status_container or not self.preview_container:
            return

        self.status_container.clear()
        self.preview_container.clear()

        if self.last_report_path and os.path.isfile(self.last_report_path):
            file_size_kb = round(os.path.getsize(self.last_report_path) / 1024, 1)
            filename = self.last_report_filename or os.path.basename(self.last_report_path)

            with self.status_container:
                with ui.row().classes("w-full justify-between items-center p-3 bg-emerald-50 rounded-lg border border-emerald-200"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("check_circle", color="positive", size="20px")
                        with ui.column().classes("gap-0"):
                            ui.label("Report Generated Successfully").classes("text-xs font-bold text-emerald-900")
                            ui.label(f"{filename} • {file_size_kb} KB").classes("text-xs text-emerald-700")

                    ui.button(
                        "Open in New Tab",
                        icon="open_in_new",
                        on_click=lambda: ui.open(f"/reports/{filename}"),
                    ).classes("btn-primary")

            with self.preview_container:
                # Embedded iframe preview of the generated HTML report
                ui.html(
                    f'<iframe src="/reports/{filename}" class="w-full h-[580px] rounded-lg border border-slate-200"></iframe>'
                ).classes("w-full")
        else:
            with self.preview_container:
                with ui.column().classes("w-full items-center justify-center p-12 text-center text-slate-400 gap-3 border border-dashed border-slate-200 rounded-lg"):
                    ui.icon("description", size="48px").classes("opacity-40")
                    ui.label("No Report Generated Yet").classes("text-base font-bold text-slate-600")
                    ui.label(
                        "Click 'Generate Diagnostics Report' on the left to compile an interactive HTML document with embedded Plotly charts, anomaly tables, and distribution metrics."
                    ).classes("text-xs max-w-[460px] text-slate-500 leading-relaxed")

    def _handle_generate_html_report(self):
        reports_dir = default_config.reports_dir
        os.makedirs(reports_dir, exist_ok=True)

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Radar_Report_{self.manager.session_name}_{now_str}.html"
        full_path = os.path.join(reports_dir, filename)

        generate_html_report(self.manager, output_path=full_path)
        self.last_report_path = full_path
        self.last_report_filename = filename

        ui.notify("HTML Diagnostics Report generated successfully!", type="positive")
        self._update_status_and_preview()

    def _handle_export_summary_csv(self):
        summary = self.manager.get_summary_metrics()
        csv_data = export_test_summary_to_csv(summary)
        ui.download(csv_data.encode("utf-8"), filename=f"Test_Summaries_{self.manager.session_name}.csv")
        ui.notify("Exported test summaries CSV", type="positive")

    def _handle_export_anomalies_csv(self):
        anomalies = self.manager.get_all_anomalies()
        csv_data = export_anomalies_to_csv(anomalies)
        ui.download(csv_data.encode("utf-8"), filename=f"Anomalies_{self.manager.session_name}.csv")
        ui.notify("Exported anomalies CSV", type="positive")

    def _handle_export_elements_csv(self):
        rankings = self.manager.get_element_rankings()
        csv_data = export_element_rankings_to_csv(rankings)
        ui.download(csv_data.encode("utf-8"), filename=f"Element_Stability_{self.manager.session_name}.csv")
        ui.notify("Exported element stability CSV", type="positive")

    def _handle_export_frequencies_csv(self):
        rankings = self.manager.get_frequency_rankings()
        csv_data = export_frequency_rankings_to_csv(rankings)
        ui.download(csv_data.encode("utf-8"), filename=f"Frequency_Stability_{self.manager.session_name}.csv")
        ui.notify("Exported frequency stability CSV", type="positive")
