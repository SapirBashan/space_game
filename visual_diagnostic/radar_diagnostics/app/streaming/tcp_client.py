"""Async TCP Client for receiving live radar measurement frames.

Handles network connections, framing via StreamBuffer, rolling display buffer,
sequence gap detection, and status tracking.
"""

import asyncio
from collections import deque
from datetime import datetime, timezone
import logging
import time
from typing import Callable, Deque, List, Optional
import numpy as np

from app.models.radar_frame import RadarFrame
from app.streaming.protocol import StreamBuffer

logger = logging.getLogger("radar_tcp_client")


class ConnectionState:
    DISCONNECTED = "DISCONNECTED"
    CONNECTING = "CONNECTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class RadarTcpClient:
    """Robust TCP client consuming radar streams."""

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8765,
        timeout_seconds: float = 5.0,
        buffer_max_frames: int = 100,
    ):
        self.host = host
        self.port = port
        self.timeout_seconds = timeout_seconds
        self.buffer_max_frames = buffer_max_frames

        self._state: str = ConnectionState.DISCONNECTED
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None
        self._receive_task: Optional[asyncio.Task] = None
        self._stream_buffer = StreamBuffer()

        # Rolling frame buffer
        self.frame_buffer: Deque[RadarFrame] = deque(maxlen=buffer_max_frames)

        # Metrics & diagnostics
        self.frames_received: int = 0
        self.last_sequence: Optional[int] = None
        self.sequence_gaps: int = 0
        self.last_packet_timestamp: Optional[str] = None
        self.last_error_message: Optional[str] = None
        
        # Frame rate calculation
        self._frame_timestamps: Deque[float] = deque(maxlen=20)
        self.approx_frame_rate: float = 0.0

        # Callbacks
        self._frame_callbacks: List[Callable[[RadarFrame], None]] = []
        self._state_callbacks: List[Callable[[str], None]] = []

    @property
    def state(self) -> str:
        return self._state

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    @property
    def latest_frame(self) -> Optional[RadarFrame]:
        return self.frame_buffer[-1] if self.frame_buffer else None

    def add_frame_callback(self, cb: Callable[[RadarFrame], None]):
        if cb not in self._frame_callbacks:
            self._frame_callbacks.append(cb)

    def add_state_callback(self, cb: Callable[[str], None]):
        if cb not in self._state_callbacks:
            self._state_callbacks.append(cb)

    def _set_state(self, new_state: str):
        if self._state != new_state:
            self._state = new_state
            for cb in self._state_callbacks:
                try:
                    cb(new_state)
                except Exception:
                    pass

    async def connect(self, host: Optional[str] = None, port: Optional[int] = None):
        """Initiate connection to the radar TCP server."""
        if host:
            self.host = host
        if port:
            self.port = port

        if self._state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            return

        self._set_state(ConnectionState.CONNECTING)
        self.last_error_message = None

        try:
            self._reader, self._writer = await asyncio.wait_for(
                asyncio.open_connection(self.host, self.port),
                timeout=self.timeout_seconds,
            )
            self._set_state(ConnectionState.CONNECTED)
            self._stream_buffer.clear()
            self._receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"Connected to radar TCP server at {self.host}:{self.port}")
        except Exception as e:
            self.last_error_message = str(e)
            self._set_state(ConnectionState.ERROR)
            logger.error(f"Failed to connect to {self.host}:{self.port}: {e}")

    async def disconnect(self):
        """Disconnect cleanly from the radar server."""
        self._set_state(ConnectionState.DISCONNECTED)
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._writer:
            try:
                self._writer.close()
                await self._writer.wait_closed()
            except Exception:
                pass
            self._writer = None
        self._reader = None
        logger.info("Radar TCP Client disconnected.")

    async def _receive_loop(self):
        """Background task receiving chunks from socket and extracting frames."""
        chunk_size = 64 * 1024  # 64 KB read buffer
        while self._state == ConnectionState.CONNECTED and self._reader:
            try:
                chunk = await self._reader.read(chunk_size)
                if not chunk:
                    # Connection closed by server
                    logger.warning("Server closed connection.")
                    self._set_state(ConnectionState.DISCONNECTED)
                    break

                frames = self._stream_buffer.feed(chunk)
                now_t = time.time()
                for frame in frames:
                    self._process_incoming_frame(frame, now_t)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error reading from socket: {e}")
                self.last_error_message = str(e)
                self._set_state(ConnectionState.ERROR)
                break

    def _process_incoming_frame(self, frame: RadarFrame, arrival_time: float):
        """Handle a fully parsed incoming radar frame."""
        self.frames_received += 1
        self.last_packet_timestamp = frame.timestamp

        # Gap detection
        if self.last_sequence is not None:
            expected_seq = self.last_sequence + 1
            if frame.sequence_number > expected_seq:
                gap = frame.sequence_number - expected_seq
                self.sequence_gaps += gap
                logger.warning(f"Detected sequence gap of {gap} frames (expected {expected_seq}, got {frame.sequence_number})")
        self.last_sequence = frame.sequence_number

        # Frame rate calculation
        self._frame_timestamps.append(arrival_time)
        if len(self._frame_timestamps) >= 2:
            dt = self._frame_timestamps[-1] - self._frame_timestamps[0]
            if dt > 0:
                self.approx_frame_rate = round((len(self._frame_timestamps) - 1) / dt, 2)

        # Buffer frame
        self.frame_buffer.append(frame)

        # Notify callbacks
        for cb in self._frame_callbacks:
            try:
                cb(frame)
            except Exception as e:
                logger.error(f"Error in frame callback: {e}")
