"""End-to-end integration test for the entire PSP Radar Diagnostics Platform.
"""

import asyncio
import os
import shutil
import tempfile
import pytest

from app.config import default_config
from app.core.csv_parser import parse_csv_content
from app.core.session_manager import SessionManager
from app.reports.report_generator import generate_html_report
from app.streaming.mock_server import MockRadarServer
from app.streaming.recording_manager import RecordingManager
from app.streaming.tcp_client import RadarTcpClient


@pytest.mark.asyncio
async def test_full_platform_end_to_end():
    """Execute complete workflow:
    1. Ingest synthetic CSV files
    2. Run anomaly detection and verify ground truth faults
    3. Start mock TCP server
    4. Connect live TCP client and stream frames
    5. Record live frames to disk
    6. Reload recorded session into diagnostics
    7. Generate HTML report
    """
    # 1. Ingest synthetic CSV files
    sm = SessionManager(session_name="Integration_Test_Session")
    sample_dir = default_config.sample_data_dir
    amp_dir = os.path.join(sample_dir, "AMP")

    assert os.path.isdir(amp_dir), "Sample data not found. Run generate_sample_data.py first."

    loaded_amp = 0
    for fname in sorted(os.listdir(amp_dir)):
        if fname.endswith(".csv"):
            fpath = os.path.join(amp_dir, fname)
            frames, report = parse_csv_content(fpath, filename=fname, explicit_data_type="AMP")
            if frames:
                sm.add_frames(frames, report)
                loaded_amp += len(frames)

    assert loaded_amp == 10
    assert sm.current_dataset.test_count == 10

    # 2. Run diagnostics & verify ground-truth faults
    summary = sm.get_summary_metrics()
    assert summary.test_count == 10
    assert summary.element_count == 256
    assert summary.frequency_count == 64
    assert summary.overall_mean > 65.0 and summary.overall_mean < 75.0

    anomalies = sm.get_all_anomalies()
    # Check that injected fault at Element 42 (AMP Test 4) is detected
    elem_42_anoms = [a for a in anomalies if a.element_id == 42 and a.test_id == "AMP_Test_004"]
    assert len(elem_42_anoms) > 0, "Failed to detect injected fault on Element 42"

    # Check that injected dead element at Element 180 (AMP Test 7) is detected
    elem_180_anoms = [a for a in anomalies if a.element_id == 180 and a.test_id == "AMP_Test_007"]
    assert len(elem_180_anoms) > 0, "Failed to detect injected dead element 180"

    # Element rankings
    elem_rankings = sm.get_element_rankings()
    assert len(elem_rankings) == 256

    # 3. Start mock TCP server on test port
    test_port = 8995
    server = MockRadarServer(
        host="127.0.0.1",
        port=test_port,
        streaming_rate_hz=10.0,
        elements=256,
        frequencies=64,
        fault_injection_enabled=True,
    )
    await server.start()

    # 4. Connect TCP client
    client = RadarTcpClient(host="127.0.0.1", port=test_port)
    temp_rec_dir = tempfile.mkdtemp(prefix="integ_recordings_")
    rec_mgr = RecordingManager(base_recordings_dir=temp_rec_dir)

    client.add_frame_callback(rec_mgr.record_frame)

    try:
        await client.connect()
        assert client.is_connected is True

        # 5. Start live recording
        rec_session = rec_mgr.start_recording(session_id="integ_live_session")
        assert rec_mgr.is_recording is True

        # Wait to record at least 5 frames
        for _ in range(30):
            if rec_mgr.recorded_frames_count >= 5:
                break
            await asyncio.sleep(0.1)

        assert rec_mgr.recorded_frames_count >= 5

        # 6. Stop recording
        completed_session = rec_mgr.stop_recording()
        assert completed_session.total_frames >= 5

        # Reload recorded session into SessionManager
        live_sm = SessionManager(session_name="Live_Reloaded_Session")
        reloaded_count = rec_mgr.load_session_into_manager(completed_session.session_dir, live_sm)
        assert reloaded_count >= 5
        assert live_sm.current_dataset.test_count >= 5

        # 7. Generate consolidated HTML report
        report_output_path = os.path.join(temp_rec_dir, "test_report.html")
        report_html = generate_html_report(sm, output_path=report_output_path)
        assert os.path.isfile(report_output_path)
        assert "PSP RADAR DIAGNOSTICS REPORT" in report_html
        assert "AMP_Test_001" in report_html

    finally:
        await client.disconnect()
        await server.stop()
        shutil.rmtree(temp_rec_dir, ignore_errors=True)
