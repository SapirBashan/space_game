# PSP Radar Diagnostics — Streaming Protocol Specification (v1.0)

This document defines the application-level network protocol used to stream radar PSP measurement matrices from a radar server (e.g., C++ production server or Python mock server) to the PSP Radar Diagnostics platform.

---

## 1. Transport and Framing

- **Transport Layer**: TCP Sockets (IPv4 or IPv6 stream).
- **Default Port**: `8765` (configurable).
- **Framing**: Newline-Delimited JSON (**NDJSON**).
- **Encoding**: UTF-8.
- **Delimiter**: Unix newline `\n` (`0x0A`).
- **Direction**: Server streams messages to connected clients; client does not need to send heartbeats, though sockets remain full duplex.

---

## 2. Message Schema

Each frame represents one complete radar measurement matrix transmitted as a single line:

```json
{
  "protocol_version": 1,
  "message_type": "radar_frame",
  "sequence": 1042,
  "timestamp": "2026-11-19T14:30:00.123Z",
  "session_id": "session_001",
  "test_id": "test_001",
  "data_type": "AMP",
  "unit": "dB",
  "elements": 256,
  "frequencies": 64,
  "frequency_labels": ["A", "B", "C", ..., "BL"],
  "element_ids": [1, 2, 3, ..., 256],
  "data": [
    [68.5, 71.3, ..., 72.1],
    [70.5, 69.4, ..., 70.7],
    ...
  ],
  "metadata": {
    "temperature_c": 42.1,
    "attenuation_db": 0.0
  }
}
```

### Field Definitions

| Field | Type | Description |
|---|---|---|
| `protocol_version` | integer | Must be `1`. |
| `message_type` | string | Must be `"radar_frame"`. |
| `sequence` | integer | Monotonically increasing sequence number (used to detect packet drops/gaps). |
| `timestamp` | string | ISO 8601 UTC timestamp (`YYYY-MM-DDTHH:MM:SS.sssZ`). |
| `session_id` | string | Identifier of the test session or run. |
| `test_id` | string | Unique test identifier (e.g. `"test_001"`). |
| `data_type` | string | `"AMP"`, `"NOISE"`, or `"PHASE"`. |
| `unit` | string | Raw unit on the wire: `"dB"` for AMP/NOISE, `"rad"` for PHASE. |
| `elements` | integer | Number of rows (standard is `256`). |
| `frequencies` | integer | Number of columns (standard is `64`). |
| `frequency_labels`| array[str] | Labels for columns: `["A", "B", ..., "BL"]`. |
| `element_ids` | array[int] | IDs for rows: `[1, 2, ..., 256]`. |
| `data` | array[array[float]] | 2D numerical matrix of shape `[elements][frequencies]`. |
| `metadata` | object | Optional dictionary for auxiliary engineering telemetry. |

---

## 3. Matrix Orientation and Numerical Conventions

1. **Orientation**:
   - `data[i][j]` corresponds to **Element row `i`** and **Frequency channel `j`**.
   - Outer dimension = Elements (size 256).
   - Inner dimension = Frequency channels (size 64).
   - Total numerical values per message = 16,384 floats.
2. **Units on the Wire**:
   - `AMP`: dB values (logarithmic power).
   - `NOISE`: dB values.
   - `PHASE`: **Radians** in the range `[-π, +π]`.
   - *Note*: The diagnostics GUI presentation layer converts radians to degrees (`deg = rad * 180 / π`) automatically. Do not convert to degrees on the server side.

---

## 4. C++ Implementation Reference

Below is a complete, working example in C++17 showing how a C++ radar service can serialize and send a frame over a standard POSIX TCP socket using `nlohmann::json`.

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <iomanip>
#include <sstream>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <nlohmann/json.hpp>

using json = nlohmann::json;

// Helper to get ISO 8601 UTC timestamp
std::string get_iso_timestamp() {
    auto now = std::chrono::system_clock::now();
    auto itt = std::chrono::system_clock::to_time_t(now);
    std::ostringstream ss;
    ss << std::put_time(gmtime(&itt), "%FT%TZ");
    return ss.str();
}

// Generate channel labels A..BL
std::vector<std::string> generate_channel_labels(size_t count = 64) {
    std::vector<std::string> labels;
    std::string alpha = "ABCDEFGHIJKLMNOPQRSTUVWXYZ";
    for (char c : alpha) {
        labels.push_back(std::string(1, c));
        if (labels.size() == count) return labels;
    }
    for (char c1 : alpha) {
        for (char c2 : alpha) {
            labels.push_back(std::string{c1, c2});
            if (labels.size() == count) return labels;
        }
    }
    return labels;
}

// Function to construct and send a radar frame over a connected TCP socket fd
bool send_radar_frame(int socket_fd, 
                      uint64_t sequence,
                      const std::string& test_id,
                      const std::string& data_type,
                      const std::string& unit,
                      const std::vector<std::vector<double>>& matrix) 
{
    size_t num_elements = matrix.size();
    size_t num_freqs = matrix.empty() ? 0 : matrix[0].size();

    std::vector<int> element_ids(num_elements);
    for (size_t i = 0; i < num_elements; ++i) element_ids[i] = static_cast<int>(i + 1);

    json frame;
    frame["protocol_version"] = 1;
    frame["message_type"] = "radar_frame";
    frame["sequence"] = sequence;
    frame["timestamp"] = get_iso_timestamp();
    frame["session_id"] = "live_radar_session";
    frame["test_id"] = test_id;
    frame["data_type"] = data_type; // "AMP", "NOISE", or "PHASE"
    frame["unit"] = unit;           // "dB" or "rad"
    frame["elements"] = num_elements;
    frame["frequencies"] = num_freqs;
    frame["frequency_labels"] = generate_channel_labels(num_freqs);
    frame["element_ids"] = element_ids;
    frame["data"] = matrix;
    frame["metadata"] = json::object();

    // Serialize to compact JSON and append newline delimiter
    std::string wire_msg = frame.dump() + "\n";

    // Send complete message over socket
    size_t total_sent = 0;
    while (total_sent < wire_msg.size()) {
        ssize_t sent = send(socket_fd, wire_msg.data() + total_sent, wire_msg.size() - total_sent, 0);
        if (sent < 0) {
            std::cerr << "Socket write error" << std::endl;
            return false;
        }
        total_sent += sent;
    }
    return true;
}
```

---

## 5. Future Binary Protocol Migration

The application layer encapsulates stream reception in `app/streaming/protocol.py`. When high-bandwidth streaming (>50 Hz) is required:
1. A fixed 32-byte header can be defined:
   - Magic bytes (`0x52 0x41 0x44 0x52` -> "RADR")
   - Protocol version (uint16)
   - Sequence number (uint64)
   - Data type enum (uint8: 0=AMP, 1=NOISE, 2=PHASE)
   - Element count (uint16)
   - Frequency count (uint16)
   - Timestamp epoch microseconds (uint64)
2. Followed by a contiguous array of IEEE 754 float32 values (256 × 64 × 4 bytes = 65,536 bytes).
3. The Python `StreamBuffer` and C++ server can support version negotiation transparently.
