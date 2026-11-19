"""Settings and Thresholds configuration tab implementation.
"""

from typing import Callable, Optional
from nicegui import ui

from app.config import ThresholdSettings
from app.core.session_manager import SessionManager


class SettingsView:
    """View component for tuning engineering thresholds, outlier sensitivity, and ports."""

    def __init__(self, manager: SessionManager, on_update: Optional[Callable[[], None]] = None):
        self.manager = manager
        self.on_update = on_update

    def render(self):
        """Construct the Settings tab layout."""
        th = self.manager.thresholds

        with ui.column().classes("w-full p-4 gap-4"):
            # 1. Amplitude (AMP) Engineering Limits
            with ui.card().classes("w-full panel-container"):
                ui.label("Amplitude (AMP) Thresholds").classes("panel-header")
                with ui.row().classes("w-full items-center gap-6 flex-wrap"):
                    self.amp_enabled = ui.switch("Enable AMP Limits Evaluation", value=th.amp_limits_enabled)

                    self.amp_min = ui.number(
                        label="Min Acceptable AMP (dB)",
                        value=th.amp_min_db,
                        step=0.5,
                    ).classes("w-48")

                    self.amp_max = ui.number(
                        label="Max Acceptable AMP (dB)",
                        value=th.amp_max_db,
                        step=0.5,
                    ).classes("w-48")

                    self.amp_delta = ui.number(
                        label="Max Cross-Test Delta (dB)",
                        value=th.amp_max_test_delta_db,
                        step=0.5,
                    ).classes("w-48")

            # 2. Noise (NOISE) Engineering Limits
            with ui.card().classes("w-full panel-container"):
                ui.label("Noise (NOISE) Thresholds").classes("panel-header")
                with ui.row().classes("w-full items-center gap-6 flex-wrap"):
                    self.noise_enabled = ui.switch("Enable NOISE Limits Evaluation", value=th.noise_limits_enabled)

                    self.noise_max = ui.number(
                        label="Max Acceptable Noise (dB)",
                        value=th.noise_max_db,
                        step=0.5,
                    ).classes("w-48")

                    self.noise_min = ui.number(
                        label="Min Acceptable Noise (dB)",
                        value=th.noise_min_db,
                        step=0.5,
                    ).classes("w-48")

                    self.noise_delta = ui.number(
                        label="Max Cross-Test Delta (dB)",
                        value=th.noise_max_test_delta_db,
                        step=0.5,
                    ).classes("w-48")

            # 3. Phase (PHASE) Circular Limits
            with ui.card().classes("w-full panel-container"):
                ui.label("Phase (PHASE) Thresholds & Processing").classes("panel-header")
                with ui.row().classes("w-full items-center gap-6 flex-wrap"):
                    self.phase_enabled = ui.switch("Enable PHASE Limits Evaluation", value=th.phase_limits_enabled)

                    self.phase_max_dev = ui.number(
                        label="Max Circular Deviation (deg)",
                        value=th.phase_max_deviation_deg,
                        step=1.0,
                    ).classes("w-52")

                    self.phase_axis = ui.select(
                        options=["frequency", "element"],
                        value=th.phase_unwrapping_axis,
                        label="Default Unwrapping Axis",
                    ).classes("w-48")

            # 4. Outlier Detection Sensitivity
            with ui.card().classes("w-full panel-container"):
                ui.label("Statistical Outlier Detection (MAD Algorithm)").classes("panel-header")
                with ui.row().classes("w-full items-center gap-6 flex-wrap"):
                    self.mad_thresh = ui.number(
                        label="Median Absolute Deviation Multiplier (Z-score)",
                        value=th.mad_threshold,
                        step=0.1,
                        min=1.0,
                        max=10.0,
                    ).classes("w-64")
                    ui.label("Standard threshold: 3.5. Lower values increase anomaly sensitivity.").classes("text-sm text-gray-500 italic")

            # 5. Actions
            with ui.row().classes("items-center gap-4 mt-2"):
                ui.button("Save & Apply Settings", icon="save", on_click=self._save_settings).classes("btn-primary")
                ui.button("Restore Laboratory Defaults", icon="restore", on_click=self._restore_defaults).props("outline color=grey")

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
