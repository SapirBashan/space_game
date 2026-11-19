"""Recording Manager for live radar streams.

Manages recording sessions to disk, asynchronous background disk writes,
metadata generation, and seamless reloading into File Diagnostics.
"""

import json
import logging
import os
import queue
import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.config import default_config
from app.core.csv_parser import export_frame_to_csv, parse_csv_content
from app.core.session_manager import SessionManager
from app.models.radar_frame import RadarFrame

logger = logging.getLogger("recording_manager")


class RecordingSession:
    """Represents an active or completed recording session."""

    def __init__(self, session_id: str, base_dir: str):
        self.session_id: str = session_id
        self.session_dir: str = os.path.join(base_dir, session_id)
        self.start_time: str = datetime.now(timezone.utc).isoformat()
        self.end_time: Optional[str] = None
        self.frame_counts: Dict[str, int] = {"AMP": 0, "NOISE": 0, "PHASE": 0}
        self.total_frames: int = 0
        self.frame_records: List[Dict[str, Any]] = []

        # Create subdirectories
        for dt in ("AMP", "NOISE", "PHASE"):
            os.makedirs(os.path.join(self.session_dir, dt), exist_ok=True)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "session_dir": self.session_dir,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_frames": self.total_frames,
            "frame_counts": self.frame_counts,
            "frames": self.frame_records,
        }

    def save_metadata(self):
        meta_path = os.path.join(self.session_dir, "metadata.json")
        with open(meta_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)


class RecordingManager:
    """Handles asynchronous recording of live radar streams to disk."""

    def __init__(self, base_recordings_dir: Optional[str] = None):
        self.base_dir = base_recordings_dir or default_config.recordings_dir
        os.makedirs(self.base_dir, exist_ok=True)

        self._is_recording: bool = False
        self._current_session: Optional[RecordingSession] = None
        self._record_queue: queue.Queue = queue.Queue(maxsize=1000)
        self._writer_thread: Optional[threading.Thread] = None
        self._start_epoch: float = 0.0

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def current_session(self) -> Optional[RecordingSession]:
        return self._current_session

    @property
    def recorded_frames_count(self) -> int:
        return self._current_session.total_frames if self._current_session else 0

    @property
    def elapsed_seconds(self) -> float:
        if not self._is_recording or self._start_epoch == 0.0:
            return 0.0
        return round(time.time() - self._start_epoch, 1)

    def start_recording(self, session_id: Optional[str] = None) -> RecordingSession:
        """Begin a new recording session."""
        if self._is_recording:
            return self._current_session

        timestamp_str = datetime.now().strftime("%Y_%m_%d_%H%M%S")
        sid = session_id or f"session_{timestamp_str}"
        self._current_session = RecordingSession(sid, self.base_dir)
        self._is_recording = True
        self._start_epoch = time.time()

        # Start background worker thread for disk writes
        self._writer_thread = threading.Thread(target=self._disk_writer_worker, daemon=True)
        self._writer_thread.start()
        logger.info(f"Started recording session: {sid} in {self._current_session.session_dir}")
        return self._current_session

    def record_frame(self, frame: RadarFrame):
        """Queue a frame for recording if recording is currently active."""
        if not self._is_recording:
            return
        try:
            self._record_queue.put_nowait(frame)
        except queue.Full:
            logger.warning("Recording queue is full! Frame dropped from disk recording.")

    def stop_recording(self) -> Optional[RecordingSession]:
        """Stop current recording session, flush pending disk writes, and finalize."""
        if not self._is_recording:
            return self._current_session

        self._is_recording = False
        session = self._current_session

        # Signal worker thread to finish
        self._record_queue.put(None)
        if self._writer_thread:
            self._writer_thread.join(timeout=5.0)
            self._writer_thread = None

        if session:
            session.end_time = datetime.now(timezone.utc).isoformat()
            session.save_metadata()
            logger.info(f"Recording stopped. Saved {session.total_frames} frames to {session.session_dir}")

        return session

    def _disk_writer_worker(self):
        """Background worker consuming frames from the queue and writing CSVs."""
        while True:
            try:
                frame = self._record_queue.get(timeout=0.5)
                if frame is None:
                    # Termination sentinel
                    self._record_queue.task_done()
                    break

                session = self._current_session
                if session:
                    dt = frame.data_type
                    session.total_frames += 1
                    session.frame_counts[dt] = session.frame_counts.get(dt, 0) + 1
                    seq_in_type = session.frame_counts[dt]

                    filename = f"{dt}_Test_{seq_in_type:06d}.csv"
                    csv_path = os.path.join(session.session_dir, dt, filename)

                    # Write frame to standard raw CSV (no extra headers or element column)
                    export_frame_to_csv(frame, csv_path, include_element_col=False, include_header=False)

                    session.frame_records.append({
                        "filename": filename,
                        "data_type": dt,
                        "sequence": frame.sequence_number,
                        "timestamp": frame.timestamp,
                        "test_id": frame.test_id,
                        "path": os.path.relpath(csv_path, session.session_dir),
                    })

                self._record_queue.task_done()
            except queue.Empty:
                if not self._is_recording:
                    break
            except Exception as e:
                logger.error(f"Error saving recorded frame to disk: {e}")

    def list_recorded_sessions(self) -> List[Dict[str, Any]]:
        """List all past recording sessions stored in the recordings directory."""
        sessions = []
        if not os.path.exists(self.base_dir):
            return []

        for name in sorted(os.listdir(self.base_dir), reverse=True):
            s_dir = os.path.join(self.base_dir, name)
            meta_path = os.path.join(s_dir, "metadata.json")
            if os.path.isdir(s_dir) and os.path.isfile(meta_path):
                try:
                    with open(meta_path, "r") as f:
                        meta = json.load(f)
                    sessions.append(meta)
                except Exception:
                    pass
        return sessions

    def load_session_into_manager(
        self,
        session_id_or_path: str,
        session_manager: SessionManager,
    ) -> int:
        """Load an entire recorded session into the SessionManager for file diagnostics."""
        if os.path.isdir(session_id_or_path):
            session_dir = session_id_or_path
        else:
            session_dir = os.path.join(self.base_dir, session_id_or_path)

        if not os.path.exists(session_dir):
            raise FileNotFoundError(f"Recording session directory not found: {session_dir}")

        total_loaded = 0
        for dt in ("AMP", "NOISE", "PHASE"):
            dt_dir = os.path.join(session_dir, dt)
            if not os.path.isdir(dt_dir):
                continue

            for fname in sorted(os.listdir(dt_dir)):
                if fname.lower().endswith(".csv"):
                    fpath = os.path.join(dt_dir, fname)
                    frames, report = parse_csv_content(
                        fpath,
                        filename=fname,
                        explicit_data_type=dt,
                        session_id=os.path.basename(session_dir),
                    )
                    if frames:
                        session_manager.add_frames(frames, report)
                        total_loaded += len(frames)

        return total_loaded
