"""TCP Streaming Protocol implementation for Radar PSP frames.

Protocol Specification:
- Transport: TCP Stream
- Framing: Newline-delimited UTF-8 JSON (NDJSON)
- Standard Frame Schema:
  {
    "protocol_version": 1,
    "message_type": "radar_frame",
    "sequence": 101,
    "timestamp": "2026-11-19T12:00:00.000Z",
    "session_id": "session_001",
    "test_id": "test_001",
    "data_type": "AMP",   // "AMP", "NOISE", "PHASE"
    "unit": "dB",         // "dB" for AMP/NOISE, "rad" for PHASE on wire
    "elements": 256,
    "frequencies": 64,
    "frequency_labels": ["A", "B", ..., "BL"],
    "element_ids": [1, 2, ..., 256],
    "data": [[...], ...], // 256 rows x 64 columns
    "metadata": {}
  }
"""

import json
from typing import Any, Dict, List, Optional, Tuple
import numpy as np

from app.models.radar_frame import RadarFrame


PROTOCOL_VERSION = 1
FRAME_DELIMITER = b"\n"


class ProtocolError(Exception):
    """Raised when incoming streaming data violates protocol framing or schema."""
    pass


def serialize_frame_to_bytes(frame: RadarFrame) -> bytes:
    """Serialize a RadarFrame into a newline-terminated UTF-8 JSON message."""
    payload = frame.to_dict()
    payload["protocol_version"] = PROTOCOL_VERSION
    data_str = json.dumps(payload, separators=(",", ":"))
    return data_str.encode("utf-8") + FRAME_DELIMITER


def parse_frame_from_json(payload: Dict[str, Any]) -> RadarFrame:
    """Parse and validate a dictionary payload into a RadarFrame."""
    if payload.get("message_type") != "radar_frame":
        raise ProtocolError(f"Unexpected message_type: '{payload.get('message_type')}'")

    version = payload.get("protocol_version", 1)
    if version != PROTOCOL_VERSION:
        raise ProtocolError(f"Unsupported protocol version {version} (expected {PROTOCOL_VERSION})")

    required_fields = ["sequence", "timestamp", "data_type", "unit", "elements", "frequencies", "data"]
    for req in required_fields:
        if req not in payload:
            raise ProtocolError(f"Missing required field in radar frame: '{req}'")

    return RadarFrame.from_dict(payload)


class StreamBuffer:
    """Buffer to assemble streaming TCP chunks into complete delimited messages.
    
    Handles partial socket reads and arbitrary chunk boundaries safely.
    """

    def __init__(self, max_buffer_size_bytes: int = 10 * 1024 * 1024):
        self._buffer = bytearray()
        self.max_buffer_size = max_buffer_size_bytes

    def feed(self, chunk: bytes) -> List[RadarFrame]:
        """Feed newly received socket bytes and extract any complete frames."""
        self._buffer.extend(chunk)
        if len(self._buffer) > self.max_buffer_size:
            # Prevent buffer overflow / DOS attacks
            self._buffer.clear()
            raise ProtocolError("Stream buffer exceeded maximum allowed size (cleared)")

        frames: List[RadarFrame] = []
        while True:
            delimiter_idx = self._buffer.find(FRAME_DELIMITER)
            if delimiter_idx == -1:
                break

            line_bytes = bytes(self._buffer[:delimiter_idx])
            del self._buffer[: delimiter_idx + len(FRAME_DELIMITER)]

            line_str = line_bytes.strip().decode("utf-8")
            if not line_str:
                continue

            try:
                payload = json.loads(line_str)
                frame = parse_frame_from_json(payload)
                frames.append(frame)
            except Exception as e:
                # Log or re-raise protocol error
                raise ProtocolError(f"Failed to decode frame JSON: {str(e)}") from e

        return frames

    def clear(self):
        self._buffer.clear()
