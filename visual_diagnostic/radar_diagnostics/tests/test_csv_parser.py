"""Automated unit tests for radar CSV parser, validators, and zip unpacking.
"""

import io
import os
import zipfile
import numpy as np
import pandas as pd
import pytest

from app.config import generate_frequency_labels
from app.core.csv_parser import (
    export_frame_to_csv,
    parse_csv_content,
    parse_zip_archive,
)
from app.models.radar_frame import RadarFrame


def test_standard_amp_csv():
    """Test parsing standard 256x64 AMP file with Element column."""
    freq_labels = generate_frequency_labels(64)
    data = {"Element": list(range(1, 257))}
    for fl in freq_labels:
        data[fl] = np.random.uniform(68.0, 72.0, size=256)

    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="AMP_Test_001.csv")

    assert report.is_valid is True
    assert len(frames) == 1
    frame = frames[0]
    assert frame.data_type == "AMP"
    assert frame.num_elements == 256
    assert frame.num_frequencies == 64
    assert frame.matrix.shape == (256, 64)
    assert frame.frequency_labels == freq_labels
    assert frame.element_ids == list(range(1, 257))


def test_standard_noise_csv():
    """Test parsing standard 256x64 NOISE file."""
    freq_labels = generate_frequency_labels(64)
    data = {"Element": list(range(1, 257))}
    for fl in freq_labels:
        data[fl] = np.random.uniform(10.0, 20.0, size=256)

    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="NOISE_Test_001.csv")

    assert report.is_valid is True
    assert len(frames) == 1
    assert frames[0].data_type == "NOISE"
    assert frames[0].unit == "dB"


def test_standard_phase_csv():
    """Test parsing standard 256x64 PHASE file."""
    freq_labels = generate_frequency_labels(64)
    data = {"Element": list(range(1, 257))}
    for fl in freq_labels:
        data[fl] = np.random.uniform(-np.pi, np.pi, size=256)

    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="PHASE_Test_001.csv")

    assert report.is_valid is True
    assert len(frames) == 1
    assert frames[0].data_type == "PHASE"
    assert frames[0].unit == "rad"


def test_csv_without_element_column():
    """Test CSV containing only the 64 frequency measurement columns (no Element column)."""
    freq_labels = generate_frequency_labels(64)
    data = {fl: np.random.uniform(69.0, 71.0, size=256) for fl in freq_labels}
    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="AMP_NoElement.csv")

    assert report.is_valid is True
    assert len(frames) == 1
    frame = frames[0]
    assert frame.num_elements == 256
    assert frame.element_ids == list(range(1, 257))


def test_combined_multi_test_csv():
    """Test combined multi-test CSV (TestID, Element, A, B, ...)."""
    freq_labels = generate_frequency_labels(64)
    rows = []
    for test_idx in [1, 2, 3]:
        for elem in range(1, 257):
            row = {"TestID": f"Test_{test_idx:02d}", "Element": elem}
            for fl in freq_labels:
                row[fl] = 70.0 + test_idx
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="AMP_Combined.csv")

    assert report.is_valid is True
    assert report.is_combined_format is True
    assert len(frames) == 3
    assert [f.test_id for f in frames] == ["Test_01", "Test_02", "Test_03"]
    assert frames[0].matrix.shape == (256, 64)


def test_missing_cells_and_non_finite_values():
    """Test that missing cells or NaNs are captured as warnings and handled safely."""
    freq_labels = generate_frequency_labels(64)
    data = {"Element": list(range(1, 257))}
    for fl in freq_labels:
        data[fl] = np.random.uniform(68.0, 72.0, size=256)

    # Inject NaNs
    data["A"][5] = np.nan
    data["B"][10] = np.nan

    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="AMP_Missing.csv")

    assert report.is_valid is True
    assert report.missing_count >= 2
    assert len(report.warnings) > 0
    assert np.isnan(frames[0].matrix[5, 0])


def test_flexible_dimensions():
    """Test that non-standard matrix dimensions (e.g. 128 elements x 32 freqs) are supported."""
    freq_labels = generate_frequency_labels(32)
    data = {"Element": list(range(1, 129))}
    for fl in freq_labels:
        data[fl] = np.random.uniform(65.0, 75.0, size=128)

    df = pd.DataFrame(data)
    csv_buf = io.StringIO()
    df.to_csv(csv_buf, index=False)

    frames, report = parse_csv_content(csv_buf.getvalue(), filename="AMP_128x32.csv")

    assert report.is_valid is True
    assert report.detected_elements == 128
    assert report.detected_frequencies == 32
    assert frames[0].matrix.shape == (128, 32)


def test_zip_archive_parsing():
    """Test unpacking and parsing multiple CSV files from a ZIP archive."""
    freq_labels = generate_frequency_labels(64)
    zip_buf = io.BytesIO()

    with zipfile.ZipFile(zip_buf, "w") as zf:
        for t in (1, 2):
            df = pd.DataFrame({"Element": list(range(1, 257))})
            for fl in freq_labels:
                df[fl] = 70.0 + t
            csv_str = df.to_csv(index=False)
            zf.writestr(f"AMP/AMP_Test_{t:03d}.csv", csv_str)

    zip_bytes = zip_buf.getvalue()
    frames, reports = parse_zip_archive(zip_bytes)

    assert len(frames) == 2
    assert len(reports) == 2
    assert frames[0].data_type == "AMP"
    assert frames[1].data_type == "AMP"
