#!/usr/bin/env python3
"""Synthetic Radar Data Generator.

Generates realistic AMP, NOISE, and PHASE test matrices (256 elements x 64 frequencies)
with known, documented fault injections for diagnostic validation.
"""

import json
import os
import sys
import zipfile
import numpy as np
import pandas as pd

# Add project root to sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from app.config import generate_frequency_labels
from app.models.radar_frame import RadarFrame
from app.core.csv_parser import export_frame_to_csv


def generate_synthetic_amp_matrix(test_idx: int, num_elements: int = 256, num_freqs: int = 64) -> np.ndarray:
    """Generate realistic amplitude matrix in dB (centered ~70 dB)."""
    elements = np.arange(num_elements)
    freqs = np.arange(num_freqs)
    
    # Spatial cosine ripple across elements + frequency slope
    spatial_profile = 70.0 + 2.5 * np.cos(2 * np.pi * elements / 128.0)
    freq_profile = 1.8 * np.sin(2 * np.pi * freqs / 32.0)
    
    # 2D base matrix
    base = np.outer(spatial_profile, np.ones(num_freqs)) + np.outer(np.ones(num_elements), freq_profile)
    
    # Test-to-test drift & random Gaussian noise
    test_drift = 0.2 * np.sin(test_idx * 0.8)
    noise = np.random.normal(0, 0.4, size=(num_elements, num_freqs))
    
    matrix = base + test_drift + noise
    
    # Injected faults:
    # Test 4: Element 42 has a high amplitude spike
    if test_idx == 4:
        matrix[41, :] += 8.5
    # Test 7: Element 180 is defective/dead (low gain)
    if test_idx == 7:
        matrix[179, :] -= 14.0
    # Test 9: Element 120 has extra high variance
    if test_idx == 9:
        matrix[119, :] += np.random.normal(0, 4.0, size=num_freqs)

    return np.round(matrix, 2)


def generate_synthetic_noise_matrix(test_idx: int, num_elements: int = 256, num_freqs: int = 64) -> np.ndarray:
    """Generate realistic noise matrix in dB (centered ~15 dB)."""
    elements = np.arange(num_elements)
    freqs = np.arange(num_freqs)
    
    base = 15.0 + 1.2 * np.cos(2 * np.pi * elements / 64.0)[:, None] + 0.8 * np.sin(2 * np.pi * freqs / 16.0)[None, :]
    noise = np.random.normal(0, 0.8, size=(num_elements, num_freqs))
    matrix = base + noise
    
    # Injected faults:
    # Test 3: Frequency channel 'K' (index 10) is very noisy (+14 dB)
    if test_idx == 3:
        matrix[:, 10] += 14.0
    # Test 8: Element 64 is a noisy element (+11 dB)
    if test_idx == 8:
        matrix[63, :] += 11.0

    return np.round(matrix, 2)


def generate_synthetic_phase_matrix(test_idx: int, num_elements: int = 256, num_freqs: int = 64) -> np.ndarray:
    """Generate realistic phase matrix in radians [-pi, pi]."""
    elements = np.arange(num_elements)
    freqs = np.arange(num_freqs)
    
    # Linear phase gradient across elements and frequencies
    phase_slope_elem = 0.05 * elements[:, None]
    phase_slope_freq = 0.08 * freqs[None, :]
    
    base = phase_slope_elem + phase_slope_freq + 0.05 * test_idx
    noise = np.random.normal(0, 0.06, size=(num_elements, num_freqs))
    raw_phase = base + noise
    
    # Injected faults:
    # Test 6: Element 95 has an abrupt phase shift (+1.9 radians ~ +109 degrees)
    if test_idx == 6:
        raw_phase[94, :] += 1.9

    # Wrap to [-pi, pi]
    wrapped = (raw_phase + np.pi) % (2.0 * np.pi) - np.pi
    return np.round(wrapped, 4)


def main():
    np.random.seed(42)
    output_dir = os.path.join(PROJECT_ROOT, "sample_data")
    os.makedirs(output_dir, exist_ok=True)
    
    amp_dir = os.path.join(output_dir, "AMP")
    noise_dir = os.path.join(output_dir, "NOISE")
    phase_dir = os.path.join(output_dir, "PHASE")
    combined_dir = os.path.join(output_dir, "combined")

    for d in (amp_dir, noise_dir, phase_dir, combined_dir):
        os.makedirs(d, exist_ok=True)

    num_elements = 256
    num_freqs = 64
    num_tests = 10
    freq_labels = generate_frequency_labels(num_freqs)
    element_ids = list(range(1, num_elements + 1))

    ground_truth = {
        "description": "Ground truth injected anomalies for testing radar diagnostics",
        "parameters": {
            "num_elements": num_elements,
            "num_frequencies": num_freqs,
            "num_tests": num_tests,
            "frequency_labels": freq_labels,
        },
        "injected_faults": [
            {
                "data_type": "AMP",
                "test_id": "AMP_Test_004",
                "element_id": 42,
                "type": "amplitude_spike",
                "magnitude": "+8.5 dB",
                "expected_severity": "FAIL",
                "description": "Abnormal high gain element exceeding upper AMP threshold",
            },
            {
                "data_type": "AMP",
                "test_id": "AMP_Test_007",
                "element_id": 180,
                "type": "dead_element",
                "magnitude": "-14.0 dB",
                "expected_severity": "FAIL",
                "description": "Defective low gain element below lower AMP threshold",
            },
            {
                "data_type": "AMP",
                "test_id": "AMP_Test_009",
                "element_id": 120,
                "type": "unstable_variance",
                "magnitude": "high variance",
                "expected_severity": "WARNING",
                "description": "High element variance across frequencies",
            },
            {
                "data_type": "NOISE",
                "test_id": "NOISE_Test_003",
                "frequency_label": "K",
                "frequency_index": 10,
                "type": "noisy_frequency_channel",
                "magnitude": "+14.0 dB",
                "expected_severity": "FAIL",
                "description": "Interference/spurious channel exceeding NOISE threshold",
            },
            {
                "data_type": "NOISE",
                "test_id": "NOISE_Test_008",
                "element_id": 64,
                "type": "noisy_element",
                "magnitude": "+11.0 dB",
                "expected_severity": "WARNING",
                "description": "Excessive noise element",
            },
            {
                "data_type": "PHASE",
                "test_id": "PHASE_Test_006",
                "element_id": 95,
                "type": "phase_offset_jump",
                "magnitude": "+1.9 rad (+108.8 deg)",
                "expected_severity": "FAIL",
                "description": "Phase discontinuity / hardware phase offset",
            },
        ],
    }

    # Generate AMP tests
    amp_frames = []
    print("Generating AMP tests...")
    for t in range(1, num_tests + 1):
        mat = generate_synthetic_amp_matrix(t, num_elements, num_freqs)
        test_id = f"AMP_Test_{t:03d}"
        filename = f"{test_id}.csv"
        path = os.path.join(amp_dir, filename)
        
        frame = RadarFrame(
            timestamp=f"2026-11-19T10:{t:02d}:00Z",
            sequence_number=t,
            session_id="sample_session",
            test_id=test_id,
            data_type="AMP",
            unit="dB",
            element_ids=element_ids,
            frequency_labels=freq_labels,
            matrix=mat,
            metadata={"filename": filename},
        )
        export_frame_to_csv(frame, path, include_element_col=False, include_header=False)
        amp_frames.append(frame)

    # Generate NOISE tests
    noise_frames = []
    print("Generating NOISE tests...")
    for t in range(1, num_tests + 1):
        mat = generate_synthetic_noise_matrix(t, num_elements, num_freqs)
        test_id = f"NOISE_Test_{t:03d}"
        filename = f"{test_id}.csv"
        path = os.path.join(noise_dir, filename)
        
        frame = RadarFrame(
            timestamp=f"2026-11-19T11:{t:02d}:00Z",
            sequence_number=t,
            session_id="sample_session",
            test_id=test_id,
            data_type="NOISE",
            unit="dB",
            element_ids=element_ids,
            frequency_labels=freq_labels,
            matrix=mat,
            metadata={"filename": filename},
        )
        export_frame_to_csv(frame, path, include_element_col=False, include_header=False)
        noise_frames.append(frame)

    # Generate PHASE tests
    phase_frames = []
    print("Generating PHASE tests...")
    for t in range(1, num_tests + 1):
        mat = generate_synthetic_phase_matrix(t, num_elements, num_freqs)
        test_id = f"PHASE_Test_{t:03d}"
        filename = f"{test_id}.csv"
        path = os.path.join(phase_dir, filename)
        
        frame = RadarFrame(
            timestamp=f"2026-11-19T12:{t:02d}:00Z",
            sequence_number=t,
            session_id="sample_session",
            test_id=test_id,
            data_type="PHASE",
            unit="rad",
            element_ids=element_ids,
            frequency_labels=freq_labels,
            matrix=mat,
            metadata={"filename": filename},
        )
        export_frame_to_csv(frame, path, include_element_col=False, include_header=False)
        phase_frames.append(frame)

    # Generate combined multi-test CSVs
    print("Generating combined multi-test CSVs...")
    for dt, frames in [("AMP", amp_frames), ("NOISE", noise_frames), ("PHASE", phase_frames)]:
        combined_rows = []
        for f in frames:
            for i, eid in enumerate(f.element_ids):
                row = {"TestID": f.test_id, "Element": eid}
                for j, fl in enumerate(f.frequency_labels):
                    row[fl] = f.matrix[i, j]
                combined_rows.append(row)
        comb_df = pd.DataFrame(combined_rows)
        comb_path = os.path.join(combined_dir, f"{dt}_All_Tests.csv")
        comb_df.to_csv(comb_path, index=False)

    # Write ground truth JSON
    gt_path = os.path.join(output_dir, "ground_truth.json")
    with open(gt_path, "w") as f:
        json.dump(ground_truth, f, indent=2)
    print(f"Saved ground truth metadata to: {gt_path}")

    # Generate sample_dataset.zip containing all AMP, NOISE, PHASE files
    zip_path = os.path.join(output_dir, "sample_dataset.zip")
    print(f"Creating ZIP archive: {zip_path}...")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for dt_dir in [amp_dir, noise_dir, phase_dir]:
            for root, _, files in os.walk(dt_dir):
                for file in files:
                    full_p = os.path.join(root, file)
                    rel_p = os.path.relpath(full_p, output_dir)
                    zf.write(full_p, arcname=rel_p)
        # Also include combined
        for file in os.listdir(combined_dir):
            full_p = os.path.join(combined_dir, file)
            zf.write(full_p, arcname=os.path.join("combined", file))
        zf.write(gt_path, arcname="ground_truth.json")

    print(f"Sample data generation complete! Output located at: {output_dir}")


if __name__ == "__main__":
    main()
