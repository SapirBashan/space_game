"""Settings and Thresholds configuration workspace.
Redesigned with grouped engineering panels, aligned parameter inputs with units,
clear enable/disable toggles, and sticky action bar.
"""

from typing import Callable, Optional
from nicegui import ui

from app.config import ThresholdSettings
from app.core.session_manager import SessionManager
from app.ui.components import create_card_header


class SettingsView:
    """View component for tuning engineering thresholds, outlier sensitivity, and ports."""

    def __init__(self, manager: SessionManager, on_update: Optional[Callable[[], None]] = None):
        self.manager = manager
        self.on_update = on_update

    def render(self):
        """Construct the Settings tab layout."""
        th = self.manager.thresholds

        with ui.column().classes("w-full gap-4"):
            # Header info card
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("tune", size="22px", color="primary")
                        with ui.column().classes("gap-0"):
                            ui.label("Laboratory Thresholds & Diagnostic Configuration").classes("card-title m-0")
                            ui.label("Control PASS/FAIL criteria, anomaly detection sensitivity, and circular math parameters").classes("card-subtitle")
                    ui.label("Active Session").classes("chip-info")

            # 1. Amplitude (AMP) Engineering Limits
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 mb-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("signal_cellular_alt", size="18px", color="primary")
                        ui.label("Amplitude (AMP) Thresholds").classes("text-sm font-bold text-slate-800")
                    self.amp_enabled = ui.switch("Enable Evaluation", value=th.amp_limits_enabled).props("dense")

                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Min Acceptable Level").classes("text-xs font-semibold text-slate-700")
                        self.amp_min = ui.number(
                            value=th.amp_min_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Elements below this are flagged as weak/dead").classes("text-[11px] text-slate-400")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Max Acceptable Level").classes("text-xs font-semibold text-slate-700")
                        self.amp_max = ui.number(
                            value=th.amp_max_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Elements above this are flagged as saturated").classes("text-[11px] text-slate-400")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Max Cross-Test Delta").classes("text-xs font-semibold text-slate-700")
                        self.amp_delta = ui.number(
                            value=th.amp_max_test_delta_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Permitted amplitude drift between tests").classes("text-[11px] text-slate-400")

            # 2. Noise (NOISE) Engineering Limits
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 mb-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("grain", size="18px", color="primary")
                        ui.label("Noise (NOISE) Thresholds").classes("text-sm font-bold text-slate-800")
                    self.noise_enabled = ui.switch("Enable Evaluation", value=th.noise_limits_enabled).props("dense")

                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Min Acceptable Noise").classes("text-xs font-semibold text-slate-700")
                        self.noise_min = ui.number(
                            value=th.noise_min_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Floor noise reference").classes("text-[11px] text-slate-400")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Max Acceptable Noise").classes("text-xs font-semibold text-slate-700")
                        self.noise_max = ui.number(
                            value=th.noise_max_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Channels exceeding this are flagged as noisy").classes("text-[11px] text-slate-400")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Max Cross-Test Noise Delta").classes("text-xs font-semibold text-slate-700")
                        self.noise_delta = ui.number(
                            value=th.noise_max_test_delta_db,
                            step=0.5,
                            suffix="dB",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Permitted noise floor shift between tests").classes("text-[11px] text-slate-400")

            # 3. Phase (PHASE) Processing & Circular Limits
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 mb-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("rotate_right", size="18px", color="primary")
                        ui.label("Phase (PHASE) Circular Limits & Processing").classes("text-sm font-bold text-slate-800")
                    self.phase_enabled = ui.switch("Enable Evaluation", value=th.phase_limits_enabled).props("dense")

                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Max Circular Deviation").classes("text-xs font-semibold text-slate-700")
                        self.phase_max_dev = ui.number(
                            value=th.phase_max_deviation_deg,
                            step=1.0,
                            suffix="deg",
                        ).props("outlined dense").classes("w-full")
                        ui.label("Max shortest-angle deviation from baseline").classes("text-[11px] text-slate-400")

                    with ui.column().classes("flex-1 min-w-[200px] gap-1"):
                        ui.label("Default Unwrapping Axis").classes("text-xs font-semibold text-slate-700")
                        self.phase_axis = ui.select(
                            options=["frequency", "element"],
                            value=th.phase_unwrapping_axis,
                        ).props("outlined dense options-dense").classes("w-full")
                        ui.label("Dimension used for 1D phase unrolling").classes("text-[11px] text-slate-400")

            # 4. Statistical Outlier Detection (MAD Algorithm)
            with ui.card().classes("app-card w-full"):
                with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-100 mb-3"):
                    with ui.row().classes("items-center gap-2"):
                        ui.icon("analytics", size="18px", color="primary")
                        ui.label("Statistical Outlier Detection (MAD Algorithm)").classes("text-sm font-bold text-slate-800")
                    ui.label("Robust Z-Score").classes("text-xs font-mono text-slate-500")

                with ui.row().classes("w-full items-center gap-4 flex-wrap"):
                    with ui.column().classes("flex-1 min-w-[260px] gap-1"):
                        ui.label("Median Absolute Deviation (MAD) Multiplier").classes("text-xs font-semibold text-slate-700")
                        self.mad_thresh = ui.number(
                            value=th.mad_threshold,
                            step=0.1,
                            min=1.0,
                            max=10.0,
                        ).props("outlined dense").classes("w-full")
                        ui.label("Default: 3.5. Lower values (e.g. 2.5) increase sensitivity to subtle anomalies.").classes("text-[11px] text-slate-400")

            # 5. Sticky Action Bar
            with ui.card().classes("app-card w-full sticky bottom-4 shadow-lg border-blue-200 bg-white/95 backdrop-blur"):
                with ui.row().classes("w-full justify-between items-center"):
                    ui.label("Changes take effect immediately on all diagnostic views and charts.").classes("text-xs text-slate-500")
                    with ui.row().classes("items-center gap-2"):
                        ui.button("Restore Laboratory Defaults", icon="restore", on_click=self._restore_defaults).classes("btn-secondary")
                        ui.button("Save & Apply Settings", icon="check", on_click=self._save_settings).classes("btn-primary")

    def _save_settings(self):
        th = self.manager.thresholds
        th.amp_limits_enabled = self.amp_enabled.value
        th.amp_min_db = float(self.amp_min.value or 60.0)
        th.amp_max_db = float(self.amp_max.value or 80.0)
        th.amp_max_test_delta_db = float(self.amp_delta.value or 4.0)

        th.noise_limits_enabled = self.noise_enabled.value
        th.noise_max_db = float(self.noise_max.value or 30.0)
        th.noise_min_db = float(self.noise_min.value or 0.0)
        th.noise_max_test_delta_db = float(self.noise_delta.value or 5.0)

        th.phase_limits_enabled = self.phase_enabled.value
        th.phase_max_deviation_deg = float(self.phase_max_dev.value or 45.0)
        th.phase_unwrapping_axis = self.phase_axis.value

        th.mad_threshold = float(self.mad_thresh.value or 3.5)

        ui.notify("Diagnostic thresholds and settings applied!", type="positive")
        if self.on_update:
            self.on_update()

    def _restore_defaults(self):
        default_th = ThresholdSettings()
        self.amp_enabled.value = default_th.amp_limits_enabled
        self.amp_min.value = default_th.amp_min_db
        self.amp_max.value = default_th.amp_max_db
        self.amp_delta.value = default_th.amp_max_test_delta_db

        self.noise_enabled.value = default_th.noise_limits_enabled
        self.noise_max.value = default_th.noise_max_db
        self.noise_min.value = default_th.noise_min_db
        self.noise_delta.value = default_th.noise_max_test_delta_db

        self.phase_enabled.value = default_th.phase_limits_enabled
        self.phase_max_dev.value = default_th.phase_max_deviation_deg
        self.phase_axis.value = default_th.phase_unwrapping_axis

        self.mad_thresh.value = default_th.mad_threshold
        self._save_settings()
        ui.notify("Laboratory defaults restored.", type="info")
