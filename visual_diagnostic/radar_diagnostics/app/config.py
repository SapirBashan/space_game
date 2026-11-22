"""Configuration module for PSP Radar Diagnostics.

Contains application settings, radar matrix conventions, color palettes,
and diagnostic threshold configurations.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import os


# Modern Technical Dashboard Color Palette (Grafana / Linear Inspired)
PALETTE = {
    "sidebar_bg": "#101D32",       # Dark navy sidebar
    "sidebar_hover": "#1C304C",    # Dark navy hover
    "sidebar_active": "#1E3A5F",   # Active navigation item background
    "primary": "#2563EB",          # Modern electric blue
    "primary_hover": "#1D4ED8",    # Darker blue on hover
    "primary_pressed": "#1E40AF",  # Pressed blue
    "primary_accent": "#0891B2",   # Cyan accent for live data
    "bg_page": "#F4F7FB",          # Soft slate-gray canvas
    "bg_panel": "#FFFFFF",         # Pure white card surface
    "table_header": "#F8FAFC",     # Light slate table header
    "border": "#E2E8F0",           # Subtle crisp border
    "border_light": "#F1F5F9",     # Very light border / divider
    "surface": "#FFFFFF",          # Pure white card surface
    "text_main": "#142338",        # Deep navy/slate text
    "text_secondary": "#64748B",   # Muted slate text
    "text_muted": "#94A3B8",       # Very light secondary text
    "error": "#DC2626",            # Modern vivid red
    "warning": "#D97706",          # Modern amber
    "success": "#059669",          # Modern emerald green
    "live_accent": "#0891B2",      # Cyan accent
    "accent_azure": "#EFF6FF",     # Soft light blue highlight
    "terminal_bg": "#0B1120",      # Obsidian terminal background
}

# Categorical high-contrast palette for distinct test overlays (up to 16 tests)
TEST_COLORS = [
    "#2563EB",  # Electric Blue
    "#EA580C",  # Vibrant Orange
    "#059669",  # Emerald Green
    "#DC2626",  # Crimson Red
    "#7C3AED",  # Deep Violet
    "#0891B2",  # Cyan Blue
    "#DB2777",  # Deep Rose
    "#475569",  # Slate Grey
    "#D97706",  # Amber Gold
    "#0D9488",  # Teal Cyan
    "#9333EA",  # Rich Purple
    "#B91C1C",  # Dark Crimson
    "#0284C7",  # Ocean Sky Blue
    "#16A34A",  # Forest Green
    "#C2410C",  # Rust Orange
    "#4F46E5",  # Indigo
]


def generate_frequency_labels(count: int = 64) -> List[str]:
    """Generate standard radar frequency channel labels (A..Z, AA..AZ, BA..BL)."""
    labels = []
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    
    # 1-letter labels (A-Z: 26)
    for c in alphabet:
        labels.append(c)
        if len(labels) == count:
            return labels
            
    # 2-letter labels (AA-AZ, BA-BZ, etc.)
    for c1 in alphabet:
        for c2 in alphabet:
            labels.append(f"{c1}{c2}")
            if len(labels) == count:
                return labels
                
    return labels


@dataclass
class ThresholdSettings:
    """Configurable diagnostic threshold limits."""
    # AMP thresholds (in dB)
    amp_min_db: float = 60.0
    amp_max_db: float = 80.0
    amp_max_test_delta_db: float = 4.0
    
    # NOISE thresholds (in dB)
    noise_max_db: float = 30.0
    noise_min_db: float = 0.0
    noise_max_test_delta_db: float = 5.0
    
    # PHASE thresholds (in degrees)
    phase_max_deviation_deg: float = 45.0
    phase_unwrapping_axis: str = "frequency"  # 'element' or 'frequency'
    
    # Statistical Outlier Detection (MAD sensitivity multiplier)
    mad_threshold: float = 3.5
    
    # Engineering Limits Enable Flags (PASS/FAIL vs NOT EVALUATED)
    amp_limits_enabled: bool = True
    noise_limits_enabled: bool = True
    phase_limits_enabled: bool = True


@dataclass
class AppConfig:
    """Master application configuration."""
    # Networking
    gui_host: str = os.getenv("RADAR_GUI_HOST", "0.0.0.0")
    gui_port: int = int(os.getenv("RADAR_GUI_PORT", "8080"))
    
    tcp_server_host: str = os.getenv("RADAR_TCP_HOST", "0.0.0.0")
    tcp_server_port: int = int(os.getenv("RADAR_TCP_PORT", "8765"))
    tcp_timeout_seconds: float = 5.0
    
    # Matrix Dimensions
    default_elements: int = 256
    default_frequencies: int = 64
    
    # Live Streaming Buffer
    live_buffer_max_frames: int = 100
    live_gui_refresh_interval_sec: float = 0.5  # limit GUI refresh to 2 Hz to conserve CPU
    
    # Paths
    base_dir: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    recordings_dir: str = os.path.join(base_dir, "recordings")
    sample_data_dir: str = os.path.join(base_dir, "sample_data")
    reports_dir: str = os.path.join(base_dir, "reports_output")
    
    # Thresholds
    thresholds: ThresholdSettings = field(default_factory=ThresholdSettings)
    
    # Frequency mapping (optional mapping from label to MHz/GHz)
    frequency_mapping_hz: Dict[str, float] = field(default_factory=dict)


# Default global instance
default_config = AppConfig()
