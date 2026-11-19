# PSP Radar Diagnostics & Live Monitoring Platform

A laboratory-grade Python diagnostics platform for Radar Phase Synchronized Processing (PSP) matrices.

This platform allows radar engineers to analyze multi-test offline logs, monitor live high-rate TCP data streams, record telemetry to disk, diagnose element/channel stability, and generate comprehensive engineering reports.

---

## 🛰️ Architecture & Capabilities

- **3 Data Modes**:
  - `AMP` (Amplitude in dB)
  - `NOISE` (Noise in dB)
  - `PHASE` (Phase in radians on wire, displayed in degrees with circular arithmetic)
- **Standard Radar Matrix**: 256 Elements × 64 Frequencies (channels `A` through `BL`).
- **Offline File Diagnostics**: Drag-and-drop CSV upload, ZIP archive unpacking, multi-test comparisons, and MAD (Median Absolute Deviation) outlier detection.
- **Simulated & Production TCP Streaming**: C++-compatible TCP server emulating live radar streaming at 1–10+ Hz over NDJSON framing.
- **Real-time Recording & Reloading**: Asynchronous background disk persistence directly to standard CSV files, reloadable into File Diagnostics.
- **Interactive Visualizations**: High-performance Plotly charts styled with the engineering laboratory visual theme (`#1976D2`).
- **Reporting**: Consolidated HTML laboratory report generation and CSV exports.

---

## 🚀 Quick Start Guide

### 1. Setup Virtual Environment & Install Dependencies

```bash
cd /home/user/workspace/visual_diagnostic/radar_diagnostics

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install requirements
pip install -r requirements.txt
```

### 2. Generate Synthetic Test Datasets

Generate 10 AMP tests, 10 NOISE tests, 10 PHASE tests, combined multi-test CSVs, `sample_dataset.zip`, and ground truth metadata:

```bash
python scripts/generate_sample_data.py
```

Generated files are placed in `sample_data/`:
- `sample_data/AMP/` (AMP_Test_001.csv to AMP_Test_010.csv)
- `sample_data/NOISE/` (NOISE_Test_001.csv to NOISE_Test_010.csv)
- `sample_data/PHASE/` (PHASE_Test_001.csv to PHASE_Test_010.csv)
- `sample_data/combined/` (AMP_All_Tests.csv, NOISE_All_Tests.csv, PHASE_All_Tests.csv)
- `sample_data/sample_dataset.zip` (Ready for drag-and-drop testing)
- `sample_data/ground_truth.json` (Documented injected anomalies)

---

### 3. Launch the Mock Radar TCP Server

In a dedicated terminal, launch the simulated radar TCP server:

```bash
python run_mock_server.py --port 8765 --rate 1.0 --mode AMP
```

Options:
- `--host`: Bind address (default: `0.0.0.0`)
- `--port`: Port number (default: `8765`)
- `--rate`: Frame transmission frequency in Hz (default: `1.0`)
- `--mode`: `AMP`, `NOISE`, `PHASE`, or `MIXED`
- `--clean`: Run without injected faults

---

### 4. Launch the Web Application

In another terminal, launch the NiceGUI web dashboard:

```bash
python run_app.py --port 8080 --host 0.0.0.0
```

Open your browser to:
- Local: **`http://localhost:8080`**
- Google Cloud Workstation: Access port `8080` via Cloud Workstation port proxying.

---

## 🧪 Automated Testing

Execute the complete automated test suite (unit and integration):

```bash
pytest
```

All 26 automated tests verify:
- CSV parser format detection, ZIP archive ingestion, and handling of flexible dimensions
- Circular phase conversions, wrapping `[-180°, 180°)`, and shortest signed differences
- Statistical metrics, threshold checking, and MAD outlier detection
- TCP streaming protocol serialization, partial socket reads, and stream buffering
- Live stream recording and reloading into offline diagnostics
- Full end-to-end integration and anomaly discovery against ground-truth faults

---

## 💻 Integration with a Real C++ Radar Server

The streaming layer is designed as a drop-in network interface for an external C++ radar server.

Complete documentation and sample C++ socket serialization code is provided in:
- **[`docs/STREAMING_PROTOCOL.md`](docs/STREAMING_PROTOCOL.md)**

### Framing Summary
- **Protocol**: NDJSON (Newline-Delimited UTF-8 JSON)
- **Framing delimiter**: `\n` (`0x0A`)
- **Schema**:
  ```json
  {
    "protocol_version": 1,
    "message_type": "radar_frame",
    "sequence": 1,
    "timestamp": "2026-11-19T12:00:00Z",
    "session_id": "session_001",
    "test_id": "test_001",
    "data_type": "AMP",
    "unit": "dB",
    "elements": 256,
    "frequencies": 64,
    "frequency_labels": ["A", "B", ...],
    "element_ids": [1, 2, ...],
    "data": [[...], ...]
  }
  ```
- Matrix shape is always `(256, 64)` with axis 0 = elements, axis 1 = frequencies.
- AMP/NOISE must use dB values; PHASE must be transmitted in radians.

---

## 📊 User Experience Workflows

### Workflow A: Offline CSV Diagnostics
1. Navigate to **File Diagnostics**.
2. Click **Load Sample AMP Dataset** (or drag and drop CSV files / `sample_dataset.zip`).
3. Select frequency channel (e.g. `A`). Observe 10 distinct, overlaid test curves on the dB vs. Element graph.
4. Select individual elements to inspect frequency behavior.
5. Inspect the 2D matrix heatmap and statistical distributions.
6. Review the automatically generated anomalies table.

### Workflow B: Live Streaming & Recording
1. Start the simulated radar server (`python run_mock_server.py`).
2. Navigate to **Live Stream & Recording**.
3. Click **Connect** (connection badge turns green `CONNECTED`).
4. Watch incoming live heatmaps and signal trends update in real time.
5. Click **Start Recording**. Let 10+ frames record.
6. Click **Stop Recording**.
7. In the saved sessions table, click **Open in File Diagnostics** to immediately analyze the recorded data.

---

## 🎨 Theme & Engineering Palette

Adheres strictly to the laboratory SCSS color palette:
- **Primary Blue**: `#1976D2`
- **Button Hover**: `#125699`
- **Button Pressed**: `#0D47A1`
- **Page Background**: `#FAFAFA`
- **Panel Background**: `#F5F5F5`
- **Table Column Header**: `#EEEEEE`
- **Borders & Dividers**: `#E0E0E0`
- **White Surface**: `#FFFFFF`
- **Main Text**: `#333333`
- **Error Red**: `#F44336`
- **Warning Amber**: `#FFC107`
