"""Automated unit tests for TCP streaming protocol, mock server, and client.
"""

import asyncio
import json
import numpy as np
import pytest

from app.models.radar_frame import RadarFrame
from app.streaming.mock_server import MockRadarServer
from app.streaming.protocol import (
    FRAME_DELIMITER,
    ProtocolError,
    StreamBuffer,
    parse_frame_from_json,
    serialize_frame_to_bytes,
)
from app.streaming.tcp_client import ConnectionState, RadarTcpClient


@pytest.fixture
def dummy_frame():
    return RadarFrame(
        timestamp="2026-11-19T12:00:00Z",
        sequence_number=42,
        session_id="stream_test",
        test_id="Test_Stream_42",
        data_type="AMP",
        unit="dB",
        element_ids=[1, 2],
        frequency_labels=["A", "B"],
        matrix=np.array([[70.1, 71.2], [69.5, 70.8]]),
    )


def test_protocol_serialization_roundtrip(dummy_frame):
    """Test that a frame serialized to bytes can be parsed back with exact values."""
    wire_bytes = serialize_frame_to_bytes(dummy_frame)
    assert wire_bytes.endswith(FRAME_DELIMITER)

    # Parse JSON from wire
    payload = json.loads(wire_bytes.decode("utf-8").strip())
    recovered_frame = parse_frame_from_json(payload)

    assert recovered_frame.sequence_number == dummy_frame.sequence_number
    assert recovered_frame.test_id == dummy_frame.test_id
    assert recovered_frame.data_type == dummy_frame.data_type
    assert np.allclose(recovered_frame.matrix, dummy_frame.matrix)


def test_stream_buffer_partial_reads(dummy_frame):
    """Verify StreamBuffer safely handles arbitrary TCP chunks and partial reads."""
    wire_bytes = serialize_frame_to_bytes(dummy_frame)
    buffer = StreamBuffer()

    # Split message in half
    mid = len(wire_bytes) // 2
    part1 = wire_bytes[:mid]
    part2 = wire_bytes[mid:]

    # Feed first part -> should yield 0 complete frames
    frames1 = buffer.feed(part1)
    assert len(frames1) == 0

    # Feed second part -> should yield exactly 1 complete frame
    frames2 = buffer.feed(part2)
    assert len(frames2) == 1
    assert frames2[0].sequence_number == 42


def test_stream_buffer_rejects_malformed_json():
    """Verify StreamBuffer raises ProtocolError on malformed message and does not crash."""
    buffer = StreamBuffer()
    with pytest.raises(ProtocolError):
        buffer.feed(b"INVALID_NOT_JSON\n")


@pytest.mark.asyncio
async def test_mock_server_and_client_communication():
    """Test end-to-end TCP streaming from MockRadarServer to RadarTcpClient."""
    server_port = 8991
    server = MockRadarServer(
        host="127.0.0.1",
        port=server_port,
        streaming_rate_hz=10.0,  # Fast 10 Hz for quick testing
        elements=16,
        frequencies=8,
    )
    await server.start()

    client = RadarTcpClient(host="127.0.0.1", port=server_port, timeout_seconds=2.0)
    received_frames = []

    def on_frame(f):
        received_frames.append(f)

    client.add_frame_callback(on_frame)

    try:
        await client.connect()
        assert client.is_connected is True

        # Wait to receive a few frames
        for _ in range(20):
            if len(received_frames) >= 3:
                break
            await asyncio.sleep(0.1)

        assert len(received_frames) >= 3
        first = received_frames[0]
        assert first.matrix.shape == (16, 8)
        assert client.frames_received >= 3
        assert client.sequence_gaps == 0

    finally:
        await client.disconnect()
        await server.stop()
