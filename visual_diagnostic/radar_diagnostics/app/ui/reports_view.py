"""Reports & Exports tab implementation.
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


class ReportsView:
    """View component for generating and downloading reports and CSV exports."""

    def __init__(self, manager: SessionManager):
        self.manager = manager
        self.preview_container = None
        self.last_report_path = None

    def render(self):
        """Construct the Reports & Exports tab layout."""
        with ui.column().classes("w-full p-4 gap-4"):
            # 1. Export Action Cards
            with ui.card().classes("w-full panel-container"):
                ui.label("Laboratory Report & Data Export Actions").classes("panel-header")
                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    ui.button(
                        "Generate HTML Diagnostics Report",
                        icon="description",
                        on_click=self._handle_generate_html_report,
                    ).classes("btn-primary")

                    ui.button(
                        "Export Test Summaries CSV",
                        icon="table_chart",
                        on_click=self._handle_export_summary_csv,
                    ).props("outline color=primary")

                    ui.button(
                        "Export Anomalies List CSV",
                        icon="warning",
                        on_click=self._handle_export_anomalies_csv,
                    ).props("outline color=primary")

                    ui.button(
                        "Export Element Stability CSV",
                        icon="reorder",
                        on_click=self._handle_export_elements_csv,
                    ).props("outline color=primary")

                    ui.button(
                        "Export Frequency Stability CSV",
                        icon="bar_chart",
                        on_click=self._handle_export_frequencies_csv,
                    ).props("outline color=primary")

            # 2. Report Details & Status
            with ui.card().classes("w-full panel-container"):
                ui.label("Consolidated HTML Report Status").classes("panel-header")
                self.status_label = ui.label("No report generated yet during this session.").classes("text-gray-600 mb-2")
                self.link_container = ui.row().classes("items-center gap-2")

            # 3. Report Interactive Preview Container
            with ui.card().classes("w-full panel-container"):
                ui.label("Report Preview").classes("panel-header")
                self.preview_container = ui.column().classes("w-full min-h-[400px]")

        self.refresh()

    def refresh(self):
        """Refresh preview if report exists."""
        if self.last_report_path and os.path.isfile(self.last_report_path):
            self._render_preview()

    def _handle_generate_html_report(self):
        reports_dir = default_config.reports_dir
        os.makedirs(reports_dir, exist_ok=True)

        now_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"Radar_Diagnostics_Report_{self.manager.session_name}_{now_str}.html"
        full_path = os.path.join(reports_dir, filename)

        generate_html_report(self.manager, output_path=full_path)
        self.last_report_path = full_path

        self.status_label.text = f"Report successfully generated at: {full_path}"
        self.link_container.clear()
        with self.link_container:
            ui.button("Open Report in Browser", icon="open_in_new", on_click=lambda: ui.open(f"/reports/{filename}")).classes("btn-primary")
            ui.label(f"Size: {round(os.path.getsize(full_path) / 1024, 1)} KB").classes("text-sm text-gray-500 ml-2")

        ui.notify("HTML Diagnostics Report generated successfully!", type="positive")
        self._render_preview()

    def _render_preview(self):
        self.preview_container.clear()
        if not self.last_report_path or not os.path.isfile(self.last_report_path):
            return

        with open(self.last_report_path, "r", encoding="utf-8") as f:
            html_content = f.read()

        with self.preview_container:
            escaped_html = html_content.replace('"', '&quot;')
            ui.html(f'<iframe srcdoc="{escaped_html}" style="width:100%; height:600px; border:1px solid #E0E0E0; border-radius:4px;"></iframe>')

    def _handle_export_summary_csv(self):
        csv_str = export_test_summary_to_csv(self.manager)
        ui.download(csv_str.encode("utf-8"), filename=f"Test_Summary_{self.manager.session_name}.csv")
        ui.notify("Test summary exported to CSV.", type="positive")

    def _handle_export_anomalies_csv(self):
        anomalies = self.manager.get_all_anomalies()
        csv_str = export_anomalies_to_csv(anomalies)
        ui.download(csv_str.encode("utf-8"), filename=f"Anomalies_{self.manager.session_name}.csv")
        ui.notify(f"Exported {len(anomalies)} anomalies to CSV.", type="positive")

    def _handle_export_elements_csv(self):
        rankings = self.manager.get_element_rankings()
        csv_str = export_element_rankings_to_csv(rankings)
        ui.download(csv_str.encode("utf-8"), filename=f"Element_Stability_{self.manager.session_name}.csv")
        ui.notify(f"Exported {len(rankings)} element stability rankings to CSV.", type="positive")

    def _handle_export_frequencies_csv(self):
        rankings = self.manager.get_frequency_rankings()
        csv_str = export_frequency_rankings_to_csv(rankings)
        ui.download(csv_str.encode("utf-8"), filename=f"Frequency_Stability_{self.manager.session_name}.csv")
        ui.notify(f"Exported {len(rankings)} frequency stability rankings to CSV.", type="positive")
