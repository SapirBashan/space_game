"""Simulated Radar TCP Server.

Generates and broadcasts synthetic radar measurement matrices over TCP sockets
using the NDJSON protocol.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
import numpy as np

from app.config import default_config, generate_frequency_labels
from app.models.radar_frame import RadarFrame
from app.streaming.protocol import serialize_frame_to_bytes

logger = logging.getLogger("radar_mock_server")


class MockRadarServer:
    """Asynchronous TCP server emulating a C++ radar PSP data server."""

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        streaming_rate_hz: float = 1.0,
        data_mode: str = "AMP",  # 'AMP', 'NOISE', 'PHASE', 'MIXED'
        elements: int = 256,
        frequencies: int = 64,
        fault_injection_enabled: bool = True,
        random_seed: Optional[int] = 42,
    ):
        self.host = host
        self.port = port
        self.streaming_rate_hz = max(0.1, min(streaming_rate_hz, 50.0))
        self.data_mode = data_mode.upper()
        self.elements = elements
        self.frequencies = frequencies
        self.fault_injection_enabled = fault_injection_enabled
        
        if random_seed is not None:
            np.random.seed(random_seed)

        self.frequency_labels = generate_frequency_labels(self.frequencies)
        self.element_ids = list(range(1, self.elements + 1))

        self._server: Optional[asyncio.Server] = None
        self._clients: Set[asyncio.StreamWriter] = set()
        self._running: bool = False
        self._broadcast_task: Optional[asyncio.Task] = None
        self._sequence_number: int = 0
        self._frame_count: int = 0

    @property
    def is_running(self) -> bool:
        return self._running and self._server is not None

    @property
    def client_count(self) -> int:
        return len(self._clients)

    @property
    def frame_count(self) -> int:
        return self._frame_count

    async def start(self):
        """Start listening for TCP client connections and begin broadcast loop."""
        if self._running:
            return

        self._running = True
        self._server = await asyncio.start_server(
            self._handle_client,
            self.host,
            self.port,
        )
        logger.info(f"Mock Radar TCP Server listening on {self.host}:{self.port}")
        self._broadcast_task = asyncio.create_task(self._broadcast_loop())

    async def stop(self):
        """Stop broadcast loop and close server and all active client connections."""
        self._running = False
        if self._broadcast_task:
            self._broadcast_task.cancel()
            try:
                await self._broadcast_task
            except asyncio.CancelledError:
                pass

        for writer in list(self._clients):
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass
        self._clients.clear()

        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None
        logger.info("Mock Radar TCP Server stopped.")

    async def _handle_client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        """Handle incoming client connection."""
        peer = writer.get_extra_info("peername")
        logger.info(f"Client connected from {peer}")
        self._clients.add(writer)

        try:
            # Keep reading until client disconnects
            while self._running:
                data = await reader.read(1024)
                if not data:
                    break
        except (ConnectionResetError, asyncio.IncompleteReadError):
            pass
        finally:
            logger.info(f"Client disconnected: {peer}")
            self._clients.discard(writer)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    def _generate_frame(self) -> RadarFrame:
        """Synthesize next radar measurement matrix based on current mode and sequence."""
        self._sequence_number += 1
        seq = self._sequence_number
        self._frame_count += 1

        # Determine data type for this frame
        if self.data_mode == "MIXED":
            types = ["AMP", "NOISE", "PHASE"]
            curr_type = types[(seq - 1) % 3]
        else:
            curr_type = self.data_mode

        unit = "rad" if curr_type == "PHASE" else "dB"
        now_iso = datetime.now(timezone.utc).isoformat()
        test_id = f"LiveTest_{seq:06d}"

        elems = np.arange(self.elements)
        freqs = np.arange(self.frequencies)

        if curr_type == "AMP":
            base = 70.0 + 2.5 * np.cos(2 * np.pi * elems / 128.0)[:, None] + 1.8 * np.sin(2 * np.pi * freqs / 32.0)[None, :]
            noise = np.random.normal(0, 0.4, size=(self.elements, self.frequencies))
            matrix = base + noise
            if self.fault_injection_enabled:
                # Element 42 high spike
                if self.elements > 41:
                    matrix[41, :] += 8.5
                # Element 180 low gain
                if self.elements > 179:
                    matrix[179, :] -= 14.0

        elif curr_type == "NOISE":
            base = 15.0 + 1.0 * np.cos(2 * np.pi * elems / 64.0)[:, None] + 0.6 * np.sin(2 * np.pi * freqs / 16.0)[None, :]
            noise = np.random.normal(0, 0.8, size=(self.elements, self.frequencies))
            matrix = base + noise
            if self.fault_injection_enabled:
                # Channel K (index 10) high noise
                if self.frequencies > 10:
                    matrix[:, 10] += 13.5

        else:  # PHASE
            base = 0.05 * elems[:, None] + 0.08 * freqs[None, :] + 0.02 * seq
            noise = np.random.normal(0, 0.05, size=(self.elements, self.frequencies))
            raw_phase = base + noise
            if self.fault_injection_enabled:
                # Element 95 abrupt phase jump
                if self.elements > 94:
                    raw_phase[94, :] += 1.85
            # Wrap to [-pi, pi]
            matrix = (raw_phase + np.pi) % (2.0 * np.pi) - np.pi

        return RadarFrame(
            timestamp=now_iso,
            sequence_number=seq,
            session_id="mock_live_session",
            test_id=test_id,
            data_type=curr_type,
            unit=unit,
            element_ids=self.element_ids,
            frequency_labels=self.frequency_labels,
            matrix=np.round(matrix, 3),
            metadata={"generator": "MockRadarServer", "faults_injected": self.fault_injection_enabled},
        )

    async def _broadcast_loop(self):
        """Continuously generate and transmit frames to all connected TCP clients."""
        interval = 1.0 / self.streaming_rate_hz
        while self._running:
            try:
                frame = self._generate_frame()
                if self._clients:
                    payload_bytes = serialize_frame_to_bytes(frame)
                    dead_clients = []
                    for writer in self._clients:
                        try:
                            writer.write(payload_bytes)
                            await writer.drain()
                        except Exception:
                            dead_clients.append(writer)
                    for dw in dead_clients:
                        self._clients.discard(dw)
            except Exception as e:
                logger.error(f"Error in broadcast loop: {e}")

            await asyncio.sleep(interval)
