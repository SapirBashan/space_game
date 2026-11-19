
"""Radar data models for measurements, frames, and test datasets.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np


@dataclass
class RadarFrame:
    """Represents a single radar PSP measurement matrix and metadata.

    Internal convention:
    - matrix shape is (num_elements, num_frequencies), axis 0 = elements, axis 1 = frequencies.
    - Raw units: AMP = dB, NOISE = dB, PHASE = radians.
    """
    timestamp: str
    sequence_number: int
    session_id: str
    test_id: str
    data_type: str  # 'AMP', 'NOISE', 'PHASE'
    unit: str  # 'dB' or 'rad'
    element_ids: List[int]
    frequency_labels: List[str]
    matrix: np.ndarray  # shape: (elements, frequencies)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.data_type = self.data_type.upper()
        if not isinstance(self.matrix, np.ndarray):
            self.matrix = np.array(self.matrix, dtype=np.float64)
        else:
            self.matrix = self.matrix.astype(np.float64)

        if self.matrix.ndim != 2:
            raise ValueError(f"Matrix must be 2D (elements x frequencies), got shape {self.matrix.shape}")

        if len(self.element_ids) != self.matrix.shape[0]:
            raise ValueError(
                f"Element IDs count ({len(self.element_ids)}) does not match matrix rows ({self.matrix.shape[0]})"
            )

        if len(self.frequency_labels) != self.matrix.shape[1]:
            raise ValueError(
                f"Frequency labels count ({len(self.frequency_labels)}) does not match matrix columns ({self.matrix.shape[1]})"
            )

    @property
    def num_elements(self) -> int:
        return self.matrix.shape[0]

    @property
    def num_frequencies(self) -> int:
        return self.matrix.shape[1]

    @property
    def display_unit(self) -> str:
        """Unit used for human-facing display and plots."""
        if self.data_type == "PHASE":
            return "deg"
        return "dB"

    def get_display_matrix(self, phase_mode: str = "degrees") -> np.ndarray:
        """Get the matrix converted for display.

        Args:
            phase_mode: 'degrees' (wrapped to [-180, 180)), 'radians' (raw),
                        or 'unwrapped' (unwrapped along frequency axis).
        """
        if self.data_type != "PHASE":
            return self.matrix.copy()

        if phase_mode == "radians":
            return self.matrix.copy()

        # Convert radians to degrees
        deg = self.matrix * (180.0 / np.pi)

        if phase_mode == "unwrapped":
            # Unwrap along frequency axis (axis 1)
            unwrapped_rad = np.unwrap(self.matrix, axis=1)
            return unwrapped_rad * (180.0 / np.pi)

        # Wrapped to [-180, 180) degrees
        wrapped_deg = (deg + 180.0) % 360.0 - 180.0
        return wrapped_deg

    def subset(self, element_indices: Optional[List[int]] = None, freq_indices: Optional[List[int]] = None) -> "RadarFrame":
        """Return a new RadarFrame containing only the selected elements and frequencies."""
        sub_matrix = self.matrix
        sub_elements = self.element_ids
        sub_freqs = self.frequency_labels

        if element_indices is not None and len(element_indices) > 0:
            sub_matrix = sub_matrix[element_indices, :]
            sub_elements = [self.element_ids[i] for i in element_indices]

        if freq_indices is not None and len(freq_indices) > 0:
            sub_matrix = sub_matrix[:, freq_indices]
            sub_freqs = [self.frequency_labels[j] for j in freq_indices]

        return RadarFrame(
            timestamp=self.timestamp,
            sequence_number=self.sequence_number,
            session_id=self.session_id,
            test_id=self.test_id,
            data_type=self.data_type,
            unit=self.unit,
            element_ids=sub_elements,
            frequency_labels=sub_freqs,
            matrix=sub_matrix,
            metadata=self.metadata.copy(),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert frame to dictionary suitable for JSON serialization."""
        return {
            "protocol_version": 1,
            "message_type": "radar_frame",
            "sequence": self.sequence_number,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
            "test_id": self.test_id,
            "data_type": self.data_type,
            "unit": self.unit,
            "elements": self.num_elements,
            "frequencies": self.num_frequencies,
            "frequency_labels": self.frequency_labels,
            "element_ids": self.element_ids,
            "data": self.matrix.tolist(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RadarFrame":
        """Construct a RadarFrame from a dictionary."""
        matrix = np.array(data["data"], dtype=np.float64)
        elements_count = data.get("elements", matrix.shape[0])
        freq_count = data.get("frequencies", matrix.shape[1])

        element_ids = data.get("element_ids")
        if element_ids is None:
            element_ids = list(range(1, elements_count + 1))

        freq_labels = data.get("frequency_labels")
        if freq_labels is None:
            from app.config import generate_frequency_labels
            freq_labels = generate_frequency_labels(freq_count)

        return cls(
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            sequence_number=data.get("sequence", 0),
            session_id=data.get("session_id", "default_session"),
            test_id=data.get("test_id", "test_001"),
            data_type=data.get("data_type", "AMP"),
            unit=data.get("unit", "dB"),
            element_ids=element_ids,
            frequency_labels=freq_labels,
            matrix=matrix,
            metadata=data.get("metadata", {}),
        )


@dataclass
class RadarDataset:
    """Collection of RadarFrames belonging to a single dataset session and data type."""
    session_id: str
    data_type: str
    frames: Dict[str, RadarFrame] = field(default_factory=dict)  # keyed by test_id

    def add_frame(self, frame: RadarFrame):
        if frame.data_type != self.data_type:
            raise ValueError(
                f"Cannot add frame with data_type '{frame.data_type}' to dataset with data_type '{self.data_type}'"
            )
        self.frames[frame.test_id] = frame

    def get_test_ids(self) -> List[str]:
        return list(self.frames.keys())

    @property
    def test_count(self) -> int:
        return len(self.frames)

    def get_frame(self, test_id: str) -> Optional[RadarFrame]:
        return self.frames.get(test_id)

    def get_common_elements(self) -> List[int]:
        if not self.frames:
            return []
        first_frame = next(iter(self.frames.values()))
        return first_frame.element_ids

    def get_common_frequencies(self) -> List[str]:
        if not self.frames:
            return []
        first_frame = next(iter(self.frames.values()))
        return first_frame.frequency_labels
