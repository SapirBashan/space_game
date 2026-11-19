"""Automated unit tests for stream recording manager, disk persistence, and reloading.
"""

import json
import os
import shutil
import tempfile
import time
import numpy as np
import pytest

from app.core.csv_parser import parse_csv_content
from app.core.session_manager import SessionManager
from app.models.radar_frame import RadarFrame
from app.streaming.recording_manager import RecordingManager


@pytest.fixture
def temp_recordings_dir():
    temp_dir = tempfile.mkdtemp(prefix="test_radar_recordings_")
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_recording_lifecycle_and_csv_reloading(temp_recordings_dir):
    """Test start recording, saving frames to disk, stopping, and parsing CSVs back."""
    mgr = RecordingManager(base_recordings_dir=temp_recordings_dir)
    assert mgr.is_recording is False

    session = mgr.start_recording(session_id="unit_test_session")
    assert mgr.is_recording is True
    assert os.path.isdir(session.session_dir)

    # Feed frames
    elem_ids = list(range(1, 17))
    freq_labels = [f"Ch{j}" for j in range(8)]

    frame_amp = RadarFrame(
        timestamp="2026-11-19T12:00:00Z",
        sequence_number=1,
        session_id=session.session_id,
        test_id="Test_AMP_01",
        data_type="AMP",
        unit="dB",
        element_ids=elem_ids,
        frequency_labels=freq_labels,
        matrix=np.ones((16, 8)) * 71.5,
    )
    frame_noise = RadarFrame(
        timestamp="2026-11-19T12:00:01Z",
        sequence_number=2,
        session_id=session.session_id,
        test_id="Test_NOISE_01",
        data_type="NOISE",
        unit="dB",
        element_ids=elem_ids,
        frequency_labels=freq_labels,
        matrix=np.ones((16, 8)) * 14.2,
    )

    mgr.record_frame(frame_amp)
    mgr.record_frame(frame_noise)

    # Allow worker thread time to process
    time.sleep(0.5)

    completed_session = mgr.stop_recording()
    assert mgr.is_recording is False
    assert completed_session.total_frames == 2
    assert completed_session.frame_counts["AMP"] == 1
    assert completed_session.frame_counts["NOISE"] == 1

    # Verify metadata.json
    meta_path = os.path.join(session.session_dir, "metadata.json")
    assert os.path.isfile(meta_path)
    with open(meta_path) as f:
        meta = json.load(f)
    assert meta["session_id"] == "unit_test_session"
    assert meta["total_frames"] == 2

    # Verify CSV files exist on disk
    amp_csv = os.path.join(session.session_dir, "AMP", "AMP_Test_000001.csv")
    noise_csv = os.path.join(session.session_dir, "NOISE", "NOISE_Test_000001.csv")
    assert os.path.isfile(amp_csv)
    assert os.path.isfile(noise_csv)

    # Verify CSVs can be parsed back with the exact same CSV parser!
    reloaded_frames, report = parse_csv_content(amp_csv, filename="AMP_Test_000001.csv")
    assert report.is_valid is True
    assert len(reloaded_frames) == 1
    reloaded = reloaded_frames[0]
    assert reloaded.data_type == "AMP"
    assert reloaded.num_elements == 16
    assert reloaded.num_frequencies == 8
    assert np.allclose(reloaded.matrix, 71.5)

    # Test reloading the whole recorded session into SessionManager
    sm = SessionManager(session_name="Reload_Test")
    loaded_count = mgr.load_session_into_manager(session.session_dir, sm)
    assert loaded_count == 2
    assert "AMP" in sm.datasets
    assert len(sm.datasets["AMP"].frames) == 1
    assert len(sm.datasets["NOISE"].frames) == 1
