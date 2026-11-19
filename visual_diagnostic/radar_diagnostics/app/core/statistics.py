"""Statistical analysis routines for radar PSP measurement matrices.

Provides:
- Global summary metrics (arithmetic and circular)
- Test-to-test difference metrics
- Cross-test stability metrics (standard deviation, spread, baseline deviation)
- Per-element and per-frequency aggregations
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
import numpy as np

from app.core.phase_processing import (
    circular_diff_deg,
    circular_mean_deg,
    circular_std_deg,
    wrap_deg_180,
)
from app.models.radar_frame import RadarFrame


@dataclass
class TestSummaryMetrics:
    """Summary metrics for a single test."""
    test_id: str
    data_type: str
    unit: str
    mean: float
    std_dev: float
    min_val: float
    max_val: float
    median: float
    missing_count: int
    threshold_violations: int = 0
    status: str = "PASS"  # PASS, WARNING, FAIL, NOT EVALUATED


@dataclass
class DatasetSummaryMetrics:
    """Global summary metrics across all loaded tests."""
    data_type: str
    unit: str
    test_count: int
    element_count: int
    frequency_count: int
    total_measurements: int
    overall_mean: float
    overall_std: float
    overall_min: float
    overall_max: float
    total_missing_invalid: int
    total_threshold_violations: int
    test_summaries: List[TestSummaryMetrics]


def compute_frame_summary(
    frame: RadarFrame,
    threshold_violations: int = 0,
    status: str = "PASS",
    phase_mode: str = "degrees",
) -> TestSummaryMetrics:
    """Compute basic statistical summary metrics for a single RadarFrame."""
    mat = frame.get_display_matrix(phase_mode=phase_mode)
    unit = frame.display_unit
    nan_count = int(np.isnan(mat).sum())

    if frame.data_type == "PHASE" and phase_mode == "degrees":
        # Circular statistics
        mean_val = float(circular_mean_deg(mat))
        std_val = float(circular_std_deg(mat))
        min_val = float(np.nanmin(mat))
        max_val = float(np.nanmax(mat))
        median_val = float(np.nanmedian(mat))
    else:
        mean_val = float(np.nanmean(mat))
        std_val = float(np.nanstd(mat))
        min_val = float(np.nanmin(mat))
        max_val = float(np.nanmax(mat))
        median_val = float(np.nanmedian(mat))

    return TestSummaryMetrics(
        test_id=frame.test_id,
        data_type=frame.data_type,
        unit=unit,
        mean=round(mean_val, 2),
        std_dev=round(std_val, 2),
        min_val=round(min_val, 2),
        max_val=round(max_val, 2),
        median=round(median_val, 2),
        missing_count=nan_count,
        threshold_violations=threshold_violations,
        status=status,
    )


def compute_difference_matrix(
    test_frame: RadarFrame,
    ref_frame: RadarFrame,
    phase_mode: str = "degrees",
) -> np.ndarray:
    """Calculate the difference matrix (test_frame - ref_frame).
    
    For PHASE in degrees, uses the shortest signed circular difference in [-180, 180).
    """
    mat_test = test_frame.get_display_matrix(phase_mode=phase_mode)
    mat_ref = ref_frame.get_display_matrix(phase_mode=phase_mode)

    if test_frame.data_type == "PHASE" and phase_mode == "degrees":
        return circular_diff_deg(mat_test, mat_ref)
    return mat_test - mat_ref


@dataclass
class DifferenceStatistics:
    """Statistical summary of test-to-test differences."""
    mean_diff: float
    max_abs_diff: float
    rms_diff: float
    std_diff: float
    diff_matrix: np.ndarray


def compute_difference_statistics(
    test_frame: RadarFrame,
    ref_frame: RadarFrame,
    phase_mode: str = "degrees",
) -> DifferenceStatistics:
    """Compute difference statistics between a test and a baseline reference."""
    diff_mat = compute_difference_matrix(test_frame, ref_frame, phase_mode=phase_mode)
    
    valid_diff = diff_mat[~np.isnan(diff_mat)]
    if len(valid_diff) == 0:
        return DifferenceStatistics(
            mean_diff=0.0,
            max_abs_diff=0.0,
            rms_diff=0.0,
            std_diff=0.0,
            diff_matrix=diff_mat,
        )

    if test_frame.data_type == "PHASE" and phase_mode == "degrees":
        mean_d = float(circular_mean_deg(valid_diff))
        std_d = float(circular_std_deg(valid_diff))
    else:
        mean_d = float(np.mean(valid_diff))
        std_d = float(np.std(valid_diff))

    rms_d = float(np.sqrt(np.mean(valid_diff**2)))
    max_abs_d = float(np.max(np.abs(valid_diff)))

    return DifferenceStatistics(
        mean_diff=round(mean_d, 2),
        max_abs_diff=round(max_abs_d, 2),
        rms_diff=round(rms_d, 2),
        std_diff=round(std_d, 2),
        diff_matrix=diff_mat,
    )


@dataclass
class StabilityMetrics:
    """Cross-test stability metrics across elements and frequencies."""
    mean_matrix: np.ndarray
    std_matrix: np.ndarray
    peak_to_peak_matrix: np.ndarray
    max_baseline_deviation_matrix: Optional[np.ndarray] = None


def compute_cross_test_stability(
    frames: List[RadarFrame],
    baseline_frame: Optional[RadarFrame] = None,
    phase_mode: str = "degrees",
) -> StabilityMetrics:
    """Compute stability matrices across multiple tests.
    
    Output matrices have shape (num_elements, num_frequencies).
    """
    if not frames:
        raise ValueError("Cannot compute stability across an empty list of frames.")

    data_type = frames[0].data_type
    matrices = [f.get_display_matrix(phase_mode=phase_mode) for f in frames]
    stack = np.stack(matrices, axis=0)  # (N_tests, N_elements, N_frequencies)

    if data_type == "PHASE" and phase_mode == "degrees":
        mean_mat = circular_mean_deg(stack, axis=0)
        std_mat = circular_std_deg(stack, axis=0)
        # Circular peak-to-peak approximation (max angular difference from circular mean)
        diff_from_mean = circular_diff_deg(stack, np.expand_dims(mean_mat, axis=0))
        p2p_mat = np.nanmax(diff_from_mean, axis=0) - np.nanmin(diff_from_mean, axis=0)
    else:
        mean_mat = np.nanmean(stack, axis=0)
        std_mat = np.nanstd(stack, axis=0)
        p2p_mat = np.nanmax(stack, axis=0) - np.nanmin(stack, axis=0)

    max_base_dev = None
    if baseline_frame is not None:
        base_mat = baseline_frame.get_display_matrix(phase_mode=phase_mode)
        if data_type == "PHASE" and phase_mode == "degrees":
            diffs = circular_diff_deg(stack, np.expand_dims(base_mat, axis=0))
        else:
            diffs = stack - np.expand_dims(base_mat, axis=0)
        max_base_dev = np.nanmax(np.abs(diffs), axis=0)

    return StabilityMetrics(
        mean_matrix=mean_mat,
        std_matrix=std_mat,
        peak_to_peak_matrix=p2p_mat,
        max_baseline_deviation_matrix=max_base_dev,
    )
