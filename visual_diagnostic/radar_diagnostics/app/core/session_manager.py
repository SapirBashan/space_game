"""Session and dataset state management for the radar diagnostics application.
"""

from typing import Callable, Dict, List, Optional, Set
import numpy as np

from app.config import ThresholdSettings, default_config
from app.core.anomaly_detection import (
    AnomalyRecord,
    ElementRanking,
    FrequencyRanking,
    detect_frame_anomalies,
    rank_unstable_elements,
    rank_unstable_frequencies,
)
from app.core.data_validator import ValidationReport
from app.core.statistics import (
    DatasetSummaryMetrics,
    StabilityMetrics,
    TestSummaryMetrics,
    compute_cross_test_stability,
    compute_difference_statistics,
    compute_frame_summary,
)
from app.models.radar_frame import RadarDataset, RadarFrame


class SessionManager:
    """Central state manager for offline diagnostics and loaded datasets."""

    def __init__(self, session_name: str = "Default_Session"):
        self.session_name: str = session_name
        self.thresholds: ThresholdSettings = default_config.thresholds
        
        # Datasets mapped by data_type: {"AMP": RadarDataset, "NOISE": ..., "PHASE": ...}
        self.datasets: Dict[str, RadarDataset] = {
            "AMP": RadarDataset(session_id=session_name, data_type="AMP"),
            "NOISE": RadarDataset(session_id=session_name, data_type="NOISE"),
            "PHASE": RadarDataset(session_id=session_name, data_type="PHASE"),
        }
        
        # Validation reports per loaded file
        self.reports: List[ValidationReport] = []
        
        # Current active data type in view
        self.active_data_type: str = "AMP"
        
        # Active selections/filters
        self.selected_test_ids: List[str] = []
        self.baseline_test_id: Optional[str] = None
        self.comparison_test_id: Optional[str] = None
        
        # Elements selection: list of 1-based element IDs
        self.selected_element_ids: List[int] = list(range(1, 257))
        # Frequency selection: list of frequency label strings
        self.selected_frequency_labels: List[str] = []
        
        # Single selections for focused plots
        self.focused_frequency: str = "A"
        self.focused_element: int = 1
        
        # Phase display options: 'degrees', 'radians', 'unwrapped'
        self.phase_display_mode: str = "degrees"

        # Change listeners
        self._change_listeners: List[Callable[[], None]] = []

    def subscribe(self, listener: Callable[[], None]):
        """Register a callback for state change events."""
        if listener not in self._change_listeners:
            self._change_listeners.append(listener)

    def notify_changes(self):
        """Invoke all registered state change listeners."""
        for listener in self._change_listeners:
            try:
                listener()
            except Exception:
                pass

    @property
    def current_dataset(self) -> RadarDataset:
        return self.datasets[self.active_data_type]

    def add_frames(self, frames: List[RadarFrame], report: Optional[ValidationReport] = None):
        """Add parsed frames to their corresponding datasets."""
        for frame in frames:
            dtype = frame.data_type
            if dtype not in self.datasets:
                self.datasets[dtype] = RadarDataset(session_id=self.session_name, data_type=dtype)
            self.datasets[dtype].add_frame(frame)

        if report:
            self.reports.append(report)

        # By default, select all available tests in the active dataset
        self.selected_test_ids = list(self.current_dataset.get_test_ids())
        self._refresh_selections()
        self.notify_changes()

    def remove_file(self, filename: str):
        """Remove all frames associated with a given filename."""
        self.reports = [r for r in self.reports if r.filename != filename]
        for dtype, dataset in self.datasets.items():
            to_remove = [
                tid for tid, frame in dataset.frames.items()
                if frame.metadata.get("filename") == filename
            ]
            for tid in to_remove:
                del dataset.frames[tid]
        self._refresh_selections()
        self.notify_changes()

    def clear_all(self):
        """Clear all loaded datasets and reports."""
        for dtype in self.datasets:
            self.datasets[dtype].frames.clear()
        self.reports.clear()
        self.selected_test_ids.clear()
        self.baseline_test_id = None
        self.comparison_test_id = None
        self.notify_changes()

    def set_active_data_type(self, data_type: str):
        """Switch current active data type view (AMP, NOISE, PHASE)."""
        dt = data_type.upper()
        if dt in self.datasets:
            self.active_data_type = dt
            self.selected_test_ids = list(self.current_dataset.get_test_ids())
            self._refresh_selections()
            self.notify_changes()

    def _refresh_selections(self):
        """Ensure test IDs, element IDs, and frequency labels remain valid."""
        dataset = self.current_dataset
        available_tests = dataset.get_test_ids()
        
        # Retain selected tests that still exist, or select all by default
        if not self.selected_test_ids or not any(t in available_tests for t in self.selected_test_ids):
            self.selected_test_ids = list(available_tests)
        else:
            self.selected_test_ids = [t for t in self.selected_test_ids if t in available_tests]

        # Update baseline & comparison
        if available_tests:
            if not self.baseline_test_id or self.baseline_test_id not in available_tests:
                self.baseline_test_id = available_tests[0]
            if not self.comparison_test_id or self.comparison_test_id not in available_tests:
                self.comparison_test_id = available_tests[1] if len(available_tests) > 1 else available_tests[0]
        else:
            self.baseline_test_id = None
            self.comparison_test_id = None

        # Frequencies & Elements
        common_freqs = dataset.get_common_frequencies()
        if common_freqs:
            if not self.selected_frequency_labels or not any(f in common_freqs for f in self.selected_frequency_labels):
                self.selected_frequency_labels = list(common_freqs)
            if self.focused_frequency not in common_freqs:
                self.focused_frequency = common_freqs[0]

        common_elems = dataset.get_common_elements()
        if common_elems:
            if not self.selected_element_ids or not any(e in common_elems for e in self.selected_element_ids):
                self.selected_element_ids = list(common_elems)
            if self.focused_element not in common_elems:
                self.focused_element = common_elems[0]

    def get_filtered_frames(self) -> List[RadarFrame]:
        """Return selected frames with element and frequency filters applied."""
        dataset = self.current_dataset
        if not dataset.frames or not self.selected_test_ids:
            return []

        common_elems = dataset.get_common_elements()
        common_freqs = dataset.get_common_frequencies()

        # Map selected IDs to indices
        elem_indices = [
            i for i, eid in enumerate(common_elems)
            if eid in self.selected_element_ids
        ]
        freq_indices = [
            j for j, fl in enumerate(common_freqs)
            if fl in self.selected_frequency_labels
        ]

        filtered = []
        for tid in self.selected_test_ids:
            frame = dataset.get_frame(tid)
            if frame:
                filtered.append(frame.subset(elem_indices, freq_indices))
        return filtered

    def get_baseline_frame(self) -> Optional[RadarFrame]:
        if not self.baseline_test_id:
            return None
        return self.current_dataset.get_frame(self.baseline_test_id)

    def get_filtered_baseline_frame(self) -> Optional[RadarFrame]:
        """Return the baseline frame with current element/frequency filters applied."""
        base_frame = self.get_baseline_frame()
        if not base_frame:
            return None
            
        dataset = self.current_dataset
        common_elems = dataset.get_common_elements()
        common_freqs = dataset.get_common_frequencies()

        elem_indices = [
            i for i, eid in enumerate(common_elems)
            if eid in self.selected_element_ids
        ]
        freq_indices = [
            j for j, fl in enumerate(common_freqs)
            if fl in self.selected_frequency_labels
        ]
        return base_frame.subset(elem_indices, freq_indices)

    def get_comparison_frame(self) -> Optional[RadarFrame]:
        if not self.comparison_test_id:
            return None
        return self.current_dataset.get_frame(self.comparison_test_id)

    def get_summary_metrics(self) -> DatasetSummaryMetrics:
        """Compute full summary metrics across all currently selected tests."""
        frames = self.get_filtered_frames()
        data_type = self.active_data_type
        unit = "deg" if data_type == "PHASE" else "dB"

        if not frames:
            return DatasetSummaryMetrics(
                data_type=data_type,
                unit=unit,
                test_count=0,
                element_count=len(self.selected_element_ids),
                frequency_count=len(self.selected_frequency_labels),
                total_measurements=0,
                overall_mean=0.0,
                overall_std=0.0,
                overall_min=0.0,
                overall_max=0.0,
                total_missing_invalid=0,
                total_threshold_violations=0,
                test_summaries=[],
            )

        test_summaries: List[TestSummaryMetrics] = []
        all_anomalies: List[AnomalyRecord] = []
        base_frame = self.get_filtered_baseline_frame()

        for f in frames:
            anoms = detect_frame_anomalies(
                f,
                thresholds=self.thresholds,
                baseline_frame=base_frame,
                phase_mode=self.phase_display_mode,
            )
            all_anomalies.extend(anoms)
            fail_count = sum(1 for a in anoms if a.severity == "FAIL")
            status = "FAIL" if fail_count > 0 else ("WARNING" if len(anoms) > 0 else "PASS")

            ts = compute_frame_summary(
                f,
                threshold_violations=fail_count,
                status=status,
                phase_mode=self.phase_display_mode,
            )
            test_summaries.append(ts)

        # Global aggregations
        matrices = [f.get_display_matrix(phase_mode=self.phase_display_mode) for f in frames]
        concat = np.concatenate([m.flatten() for m in matrices])
        valid = concat[~np.isnan(concat)]

        if len(valid) > 0:
            if data_type == "PHASE" and self.phase_display_mode == "degrees":
                from app.core.phase_processing import circular_mean_deg, circular_std_deg
                ov_mean = round(float(circular_mean_deg(valid)), 2)
                ov_std = round(float(circular_std_deg(valid)), 2)
            else:
                ov_mean = round(float(np.mean(valid)), 2)
                ov_std = round(float(np.std(valid)), 2)
            ov_min = round(float(np.min(valid)), 2)
            ov_max = round(float(np.max(valid)), 2)
        else:
            ov_mean, ov_std, ov_min, ov_max = 0.0, 0.0, 0.0, 0.0

        total_missing = int(np.isnan(concat).sum())
        total_fails = sum(ts.threshold_violations for ts in test_summaries)

        return DatasetSummaryMetrics(
            data_type=data_type,
            unit=unit,
            test_count=len(frames),
            element_count=frames[0].num_elements if frames else 0,
            frequency_count=frames[0].num_frequencies if frames else 0,
            total_measurements=len(concat),
            overall_mean=ov_mean,
            overall_std=ov_std,
            overall_min=ov_min,
            overall_max=ov_max,
            total_missing_invalid=total_missing,
            total_threshold_violations=total_fails,
            test_summaries=test_summaries,
        )

    def get_all_anomalies(self) -> List[AnomalyRecord]:
        """Collect all detected anomalies across selected tests."""
        frames = self.get_filtered_frames()
        base_frame = self.get_baseline_frame()
        all_anoms: List[AnomalyRecord] = []
        for f in frames:
            anoms = detect_frame_anomalies(
                f,
                thresholds=self.thresholds,
                baseline_frame=base_frame,
                phase_mode=self.phase_display_mode,
            )
            all_anoms.extend(anoms)
        return all_anoms

    def get_stability_metrics(self) -> Optional[StabilityMetrics]:
        """Compute stability metrics across selected tests."""
        frames = self.get_filtered_frames()
        if len(frames) < 2:
            return None
        return compute_cross_test_stability(
            frames,
            baseline_frame=self.get_baseline_frame(),
            phase_mode=self.phase_display_mode,
        )

    def get_element_rankings(self) -> List[ElementRanking]:
        """Return element ranking from most unstable to most stable."""
        stability = self.get_stability_metrics()
        frames = self.get_filtered_frames()
        if not stability or not frames:
            return []
        anomalies = self.get_all_anomalies()
        return rank_unstable_elements(
            stability,
            element_ids=frames[0].element_ids,
            anomalies=anomalies,
            thresholds=self.thresholds,
        )

    def get_frequency_rankings(self) -> List[FrequencyRanking]:
        """Return frequency ranking from most unstable to most stable."""
        stability = self.get_stability_metrics()
        frames = self.get_filtered_frames()
        if not stability or not frames:
            return []
        anomalies = self.get_all_anomalies()
        return rank_unstable_frequencies(
            stability,
            frequency_labels=frames[0].frequency_labels,
            anomalies=anomalies,
        )
