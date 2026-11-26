# PSP Radar Diagnostics - Operator Manual

Welcome to the **PSP (Phase Synchronized Processing) Radar Diagnostics** platform. This application is a laboratory-grade tool designed for radar engineers and technicians to analyze offline telemetry, monitor live TCP radar streams, and generate engineering reports.

---

## 🚀 Getting Started

This application is packaged as a standalone executable. You do not need to install Python, Node.js, or any external dependencies to run it.

### **Windows Users**
1. Extract the `.zip` or `.tar.gz` release folder to your local hard drive (e.g., `C:\PSP_Radar`).
2. Double-click the `PSP_Radar_Diagnostics.exe` file.
3. A black console window will open to start the backend engine. 
4. Your default web browser will automatically open to `http://localhost:8080`.

### **Linux Users**
1. Extract the release archive.
2. Open a terminal in the extracted directory and run `./PSP_Radar_Diagnostics`.
3. Your default web browser will automatically open to `http://localhost:8080`.

*(Note: If the browser does not open automatically, simply type `http://localhost:8080` into Chrome, Edge, or Firefox).*

---

## 🛠️ Platform Capabilities

The dashboard is divided into several specialized workspaces, accessible via the top tabs or the collapsible sidebar.

### 1. File Diagnostics (Offline Analysis)
Upload and inspect historical test logs.
* **Upload Data:** Drag and drop `.csv` files or packaged `.zip` datasets directly into the browser.
* **Heatmap View:** Interactive 256x64 2D color-mapped view of your matrix data (Amplitude, Noise, or Phase).
* **Cross-Section Graphs:** Click on the heatmap or use the dropdowns to view 1D slices (e.g., Signal vs Element, or Signal vs Frequency).
* **Anomaly Detection:** Automatically flags dead elements, saturated channels, and statistical outliers in a filterable table.

### 2. Live Monitoring (Real-Time TCP)
Connect directly to radar hardware or a network gateway.
* **TCP Connection:** Enter the IP address and Port of your radar data stream and click **Connect**.
* **Real-Time Feed:** Watch live scrolling matrices and rolling time-series charts as frames arrive (supports NDJSON format).
* **Disk Recording:** Click **Start Recording** to seamlessly save the live stream to a CSV file on your hard drive for later offline analysis.

### 3. Test Comparison
Compare hardware drift over time.
* **Select Baseline:** Choose a "Reference Test" from your loaded files.
* **Delta Analysis:** Instantly see the mathematical difference (Deltas) between the baseline and secondary tests.
* **Drift Detection:** Quickly isolate specific elements or frequencies that have degraded since the baseline measurement.

### 4. Reports & Exports
Generate physical laboratory documentation.
* **HTML Summary:** Click to generate a standalone, printable HTML report summarizing the current session's findings and anomalies.
* **CSV Export:** Export tables of flagged anomalies directly to Excel for further processing.

### 5. Settings & Thresholds
Tune the diagnostic engine's sensitivity. Changes apply immediately across all views.
* **Amplitude & Noise Limits:** Define the strict `Min (dB)` and `Max (dB)` engineering bounds. Elements outside these bounds will be marked FAIL.
* **Phase Circular Math:** Adjust the maximum permitted phase deviation (degrees) for shortest-angle mathematical processing.
* **MAD Sensitivity:** Tune the "Robust Z-Score" multiplier (default: 3.5). Lowering this number makes the outlier detection more aggressive at finding subtle abnormalities.

---
*Tip: The interface features a dual-navigation mode. You can toggle between "Top Tabs" and a "Collapsible Sidebar" using the buttons in the top right of the header. (Who knows, clicking the sidebar toggle enough times might even reveal a hidden diagnostic break!)*
