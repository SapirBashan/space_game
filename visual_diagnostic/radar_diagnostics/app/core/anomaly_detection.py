"""Anomaly detection, threshold validation, and ranking for radar diagnostics.

Implements:
- Engineering threshold checking (PASS / WARNING / FAIL / NOT EVALUATED)
- Robust outlier detection using Median Absolute Deviation (MAD)
- Ranking of most unstable elements and frequencies
- Diagnostic anomaly records
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
import numpy as np

from app.config import ThresholdSettings
from app.core.phase_processing import circular_diff_deg
from app.core.statistics import StabilityMetrics
from app.models.radar_frame import RadarFrame


@dataclass
class AnomalyRecord:
    """Record describing a single detected measurement anomaly."""
    element_id: int
    element_index: int
    frequency_label: str
    frequency_index: int
    test_id: str
    measured_value: float
    expected_or_limit: float
    deviation: float
    unit: str
    severity: str  # 'FAIL', 'WARNING', 'OUTLIER'
    reason: str


@dataclass
class ElementRanking:
    """Ranking item for element stability or defect level."""
    element_id: int
    element_index: int
    std_dev: float
    spread: float
    max_baseline_dev: float
    anomaly_count: int
    status: str  # PASS, WARNING, FAIL


@dataclass
class FrequencyRanking:
    """Ranking item for frequency stability or noise level."""
    frequency_label: str
    frequency_index: int
    std_dev: float
    spread: float
    max_baseline_dev: float
    anomaly_count: int
    status: str


def detect_frame_anomalies(
    frame: RadarFrame,
    thresholds: ThresholdSettings,
    baseline_frame: Optional[RadarFrame] = None,
    phase_mode: str = "degrees",
) -> List[AnomalyRecord]:
    """Scan a RadarFrame for threshold violations and statistical outliers."""
    anomalies: List[AnomalyRecord] = []
    mat = frame.get_display_matrix(phase_mode=phase_mode)
    unit = frame.display_unit
    num_elems, num_freqs = mat.shape

    # 1. Engineering Threshold Checks
    if frame.data_type == "AMP" and thresholds.amp_limits_enabled:
        low_mask = mat < thresholds.amp_min_db
        high_mask = mat > thresholds.amp_max_db

        for i, j in zip(*np.where(low_mask)):
            anomalies.append(AnomalyRecord(
                element_id=frame.element_ids[i],
                element_index=int(i),
                frequency_label=frame.frequency_labels[j],
                frequency_index=int(j),
                test_id=frame.test_id,
                measured_value=round(float(mat[i, j]), 2),
                expected_or_limit=thresholds.amp_min_db,
                deviation=round(float(thresholds.amp_min_db - mat[i, j]), 2),
                unit=unit,
                severity="FAIL",
                reason=f"AMP below lower limit ({thresholds.amp_min_db} dB)",
            ))

        for i, j in zip(*np.where(high_mask)):
            anomalies.append(AnomalyRecord(
                element_id=frame.element_ids[i],
                element_index=int(i),
                frequency_label=frame.frequency_labels[j],
                frequency_index=int(j),
                test_id=frame.test_id,
                measured_value=round(float(mat[i, j]), 2),
                expected_or_limit=thresholds.amp_max_db,
                deviation=round(float(mat[i, j] - thresholds.amp_max_db), 2),
                unit=unit,
                severity="FAIL",
                reason=f"AMP exceeds upper limit ({thresholds.amp_max_db} dB)",
            ))

    elif frame.data_type == "NOISE" and thresholds.noise_limits_enabled:
        high_mask = mat > thresholds.noise_max_db
        for i, j in zip(*np.where(high_mask)):
            anomalies.append(AnomalyRecord(
                element_id=frame.element_ids[i],
                element_index=int(i),
                frequency_label=frame.frequency_labels[j],
                frequency_index=int(j),
                test_id=frame.test_id,
                measured_value=round(float(mat[i, j]), 2),
                expected_or_limit=thresholds.noise_max_db,
                deviation=round(float(mat[i, j] - thresholds.noise_max_db), 2),
                unit=unit,
                severity="FAIL",
                reason=f"NOISE exceeds threshold ({thresholds.noise_max_db} dB)",
            ))

    # Baseline Delta check
    if baseline_frame is not None and baseline_frame.test_id != frame.test_id:
        base_mat = baseline_frame.get_display_matrix(phase_mode=phase_mode)
        if frame.data_type == "PHASE" and phase_mode == "degrees":
            diff = circular_diff_deg(mat, base_mat)
        else:
            diff = mat - base_mat

        max_allowed_delta = (
            thresholds.amp_max_test_delta_db
            if frame.data_type == "AMP"
            else (thresholds.noise_max_test_delta_db if frame.data_type == "NOISE" else thresholds.phase_max_deviation_deg)
        )

        excess_mask = np.abs(diff) > max_allowed_delta
        for i, j in zip(*np.where(excess_mask)):
            anomalies.append(AnomalyRecord(
                element_id=frame.element_ids[i],
                element_index=int(i),
                frequency_label=frame.frequency_labels[j],
                frequency_index=int(j),
                test_id=frame.test_id,
                measured_value=round(float(mat[i, j]), 2),
                expected_or_limit=round(float(base_mat[i, j]), 2),
                deviation=round(float(diff[i, j]), 2),
                unit=unit,
                severity="WARNING",
                reason=f"Delta vs baseline exceeds {max_allowed_delta} {unit}",
            ))

    # 2. Robust Outlier Detection via MAD (Median Absolute Deviation)
    flat_vals = mat.flatten()
    valid_mask = ~np.isnan(flat_vals)
    valid_vals = flat_vals[valid_mask]
    
    if len(valid_vals) > 10:
        med = float(np.median(valid_vals))
        mad = float(np.median(np.abs(valid_vals - med)))
        if mad > 1e-6:
            mod_z = 0.6745 * np.abs(mat - med) / mad
            outlier_mask = mod_z > thresholds.mad_threshold
            
            # Record top outliers (avoid flooding with duplicates of threshold fails)
            for i, j in zip(*np.where(outlier_mask)):
                # If already recorded as FAIL, skip duplicate
                already_fail = any(
                    a.element_id == frame.element_ids[i] and a.frequency_label == frame.frequency_labels[j] and a.severity == "FAIL"
                    for a in anomalies
                )
                if not already_fail:
                    anomalies.append(AnomalyRecord(
                        element_id=frame.element_ids[i],
                        element_index=int(i),
                        frequency_label=frame.frequency_labels[j],
                        frequency_index=int(j),
                        test_id=frame.test_id,
                        measured_value=round(float(mat[i, j]), 2),
                        expected_or_limit=round(med, 2),
                        deviation=round(float(mat[i, j] - med), 2),
                        unit=unit,
                        severity="WARNING",
                        reason=f"Statistical outlier (MAD z-score={round(float(mod_z[i, j]), 2)} > {thresholds.mad_threshold})",
                    ))

    return anomalies


def rank_unstable_elements(
    stability: StabilityMetrics,
    element_ids: List[int],
    anomalies: Optional[List[AnomalyRecord]] = None,
    thresholds: Optional[ThresholdSettings] = None,
) -> List[ElementRanking]:
    """Rank elements according to their standard deviation across tests (most unstable first)."""
    # Average std dev across frequencies for each element
    mean_std_per_elem = np.nanmean(stability.std_matrix, axis=1)
    mean_spread_per_elem = np.nanmean(stability.peak_to_peak_matrix, axis=1)

    if stability.max_baseline_deviation_matrix is not None:
        mean_base_dev = np.nanmean(stability.max_baseline_deviation_matrix, axis=1)
    else:
        mean_base_dev = np.zeros(len(element_ids))

    anomaly_counts = {eid: 0 for eid in element_ids}
    if anomalies:
        for a in anomalies:
            anomaly_counts[a.element_id] = anomaly_counts.get(a.element_id, 0) + 1

    rankings: List[ElementRanking] = []
    for i, eid in enumerate(element_ids):
        std_val = float(mean_std_per_elem[i])
        spread_val = float(mean_spread_per_elem[i])
        base_dev_val = float(mean_base_dev[i])
        cnt = anomaly_counts.get(eid, 0)

        # Status determination
        if cnt > 10:
            status = "FAIL"
        elif cnt > 0 or std_val > 2.5:
            status = "WARNING"
        else:
            status = "PASS"

        rankings.append(ElementRanking(
            element_id=eid,
            element_index=i,
            std_dev=round(std_val, 3),
            spread=round(spread_val, 3),
            max_baseline_dev=round(base_dev_val, 3),
            anomaly_count=cnt,
            status=status,
        ))

    # Sort descending by std dev
    rankings.sort(key=lambda r: (r.anomaly_count, r.std_dev), reverse=True)
    return rankings


def rank_unstable_frequencies(
    stability: StabilityMetrics,
    frequency_labels: List[str],
    anomalies: Optional[List[AnomalyRecord]] = None,
) -> List[FrequencyRanking]:
    """Rank frequency channels according to their standard deviation across tests."""
    mean_std_per_freq = np.nanmean(stability.std_matrix, axis=0)
    mean_spread_per_freq = np.nanmean(stability.peak_to_peak_matrix, axis=0)

    if stability.max_baseline_deviation_matrix is not None:
        mean_base_dev = np.nanmean(stability.max_baseline_deviation_matrix, axis=0)
    else:
        mean_base_dev = np.zeros(len(frequency_labels))

    anomaly_counts = {fl: 0 for fl in frequency_labels}
    if anomalies:
        for a in anomalies:
            anomaly_counts[a.frequency_label] = anomaly_counts.get(a.frequency_label, 0) + 1

    rankings: List[FrequencyRanking] = []
    for j, fl in enumerate(frequency_labels):
        std_val = float(mean_std_per_freq[j])
        spread_val = float(mean_spread_per_freq[j])
        base_dev_val = float(mean_base_dev[j])
        cnt = anomaly_counts.get(fl, 0)

        if cnt > 10:
            status = "FAIL"
        elif cnt > 0 or std_val > 2.5:
            status = "WARNING"
        else:
            status = "PASS"

        rankings.append(FrequencyRanking(
            frequency_label=fl,
            frequency_index=j,
            std_dev=round(std_val, 3),
            spread=round(spread_val, 3),
            max_baseline_dev=round(base_dev_val, 3),
            anomaly_count=cnt,
            status=status,
        ))

    rankings.sort(key=lambda r: (r.anomaly_count, r.std_dev), reverse=True)
    return rankings
