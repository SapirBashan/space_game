"""Automated unit tests for statistical calculations, anomaly detection, and ranking.
"""

import numpy as np
import pytest

from app.config import ThresholdSettings
from app.core.anomaly_detection import (
    detect_frame_anomalies,
    rank_unstable_elements,
    rank_unstable_frequencies,
)
from app.core.statistics import (
    compute_cross_test_stability,
    compute_difference_statistics,
    compute_frame_summary,
)
from app.models.radar_frame import RadarFrame


@pytest.fixture
def sample_frames():
    """Create three synthetic test frames for testing."""
    freq_labels = [f"F{i}" for i in range(64)]
    elem_ids = list(range(1, 257))

    frames = []
    for t in [1, 2, 3]:
        mat = np.full((256, 64), 70.0 + t * 0.5)
        # Element 42 has a spike in test 2
        if t == 2:
            mat[41, :] += 12.0
        frame = RadarFrame(
            timestamp="2026-11-19T10:00:00Z",
            sequence_number=t,
            session_id="test_sess",
            test_id=f"Test_{t}",
            data_type="AMP",
            unit="dB",
            element_ids=elem_ids,
            frequency_labels=freq_labels,
            matrix=mat,
        )
        frames.append(frame)
    return frames


def test_frame_summary_metrics(sample_frames):
    """Test frame summary statistics computation."""
    f1 = sample_frames[0]
    summary = compute_frame_summary(f1)

    assert summary.test_id == "Test_1"
    assert summary.mean == 70.5
    assert summary.min_val == 70.5
    assert summary.max_val == 70.5
    assert summary.std_dev == 0.0
    assert summary.missing_count == 0


def test_difference_statistics(sample_frames):
    """Test difference metrics between test and baseline reference."""
    f1 = sample_frames[0]  # values = 70.5
    f2 = sample_frames[1]  # values = 71.0, element 42 = 83.0

    diff_stats = compute_difference_statistics(f2, f1)
    # Most cells: 71.0 - 70.5 = 0.5
    # Element 42: 83.0 - 70.5 = 12.5
    assert np.isclose(diff_stats.max_abs_diff, 12.5)
    assert diff_stats.mean_diff > 0.5
    assert diff_stats.rms_diff > 0.5


def test_cross_test_stability(sample_frames):
    """Test standard deviation and peak-to-peak calculations across tests."""
    stability = compute_cross_test_stability(sample_frames, baseline_frame=sample_frames[0])

    assert stability.std_matrix.shape == (256, 64)
    assert stability.peak_to_peak_matrix.shape == (256, 64)
    # Element 42 (row 41) has much higher std dev than other elements
    elem_42_std = np.mean(stability.std_matrix[41, :])
    elem_0_std = np.mean(stability.std_matrix[0, :])
    assert elem_42_std > elem_0_std * 3.0


def test_anomaly_detection_thresholds(sample_frames):
    """Test engineering threshold violation detection."""
    f2 = sample_frames[1]  # Element 42 = 83.0 dB
    thresholds = ThresholdSettings(amp_max_db=80.0, amp_limits_enabled=True)

    anomalies = detect_frame_anomalies(f2, thresholds=thresholds)

    # Should flag element 42
    flagged = [a for a in anomalies if a.element_id == 42 and a.severity == "FAIL"]
    assert len(flagged) > 0
    assert "exceeds upper limit" in flagged[0].reason


def test_mad_outlier_detection():
    """Test robust Median Absolute Deviation outlier detection."""
    freq_labels = [f"F{i}" for i in range(64)]
    elem_ids = list(range(1, 257))

    mat = np.random.normal(70.0, 0.5, size=(256, 64))
    # Inject an outlier at element 10, channel 5
    mat[9, 4] = 85.0

    frame = RadarFrame(
        timestamp="2026-11-19T10:00:00Z",
        sequence_number=1,
        session_id="test_sess",
        test_id="Test_Outlier",
        data_type="AMP",
        unit="dB",
        element_ids=elem_ids,
        frequency_labels=freq_labels,
        matrix=mat,
    )

    thresholds = ThresholdSettings(mad_threshold=3.5, amp_limits_enabled=False)
    anomalies = detect_frame_anomalies(frame, thresholds=thresholds)

    outliers = [a for a in anomalies if a.element_id == 10 and a.frequency_label == "F4"]
    assert len(outliers) > 0
    assert "Statistical outlier" in outliers[0].reason


def test_element_ranking(sample_frames):
    """Test ranking unstable elements puts element 42 at the top."""
    stability = compute_cross_test_stability(sample_frames)
    elem_ids = sample_frames[0].element_ids
    rankings = rank_unstable_elements(stability, elem_ids)

    assert len(rankings) == 256
    # Element 42 should be #1 or near top
    top_element = rankings[0]
    assert top_element.element_id == 42
