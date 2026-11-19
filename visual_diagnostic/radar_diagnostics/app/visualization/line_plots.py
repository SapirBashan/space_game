"""Interactive line plots for element-wise and frequency-wise radar diagnostics.
"""

from typing import List, Optional
import numpy as np
import plotly.graph_objects as go

from app.config import ThresholdSettings
from app.models.radar_frame import RadarFrame
from app.visualization.color_palette import apply_theme_layout, get_test_color


def create_measurements_vs_elements_plot(
    frames: List[RadarFrame],
    frequency_label: str = "A",
    focused_element: Optional[int] = None,
    phase_mode: str = "degrees",
    thresholds: Optional[ThresholdSettings] = None,
    height: int = 420,
) -> go.Figure:
    """Plot measurements across all radar elements for a selected frequency channel."""
    fig = go.Figure()

    if not frames:
        fig.add_annotation(
            text="No data loaded or selected",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Measurements vs Elements", height=height)

    data_type = frames[0].data_type
    unit = "deg" if data_type == "PHASE" and phase_mode == "degrees" else frames[0].display_unit

    for idx, frame in enumerate(frames):
        mat = frame.get_display_matrix(phase_mode=phase_mode)
        if frequency_label in frame.frequency_labels:
            col_idx = frame.frequency_labels.index(frequency_label)
            y_vals = mat[:, col_idx]
        else:
            y_vals = mat[:, 0]

        color = get_test_color(idx)
        fig.add_trace(go.Scatter(
            x=frame.element_ids,
            y=y_vals,
            mode="lines+markers",
            name=frame.test_id,
            line=dict(color=color, width=1.8),
            marker=dict(size=4, color=color),
            hovertemplate=(
                f"<b>{frame.test_id}</b><br>"
                "Element: %{x}<br>"
                f"Value: %{{y:.2f}} {unit}<br>"
                f"Channel: {frequency_label}"
                "<extra></extra>"
            ),
        ))

    # Add threshold reference lines if configured
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            fig.add_hline(
                y=thresholds.amp_min_db,
                line_dash="dash",
                line_color="#F44336",
                annotation_text=f"Min Limit ({thresholds.amp_min_db} dB)",
                annotation_position="bottom right",
            )
            fig.add_hline(
                y=thresholds.amp_max_db,
                line_dash="dash",
                line_color="#F44336",
                annotation_text=f"Max Limit ({thresholds.amp_max_db} dB)",
                annotation_position="top right",
            )
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            fig.add_hline(
                y=thresholds.noise_max_db,
                line_dash="dash",
                line_color="#F44336",
                annotation_text=f"Max Noise ({thresholds.noise_max_db} dB)",
                annotation_position="top right",
            )

    # Highlight focused element if provided
    if focused_element is not None:
        fig.add_vline(
            x=focused_element,
            line_dash="dot",
            line_color="#FFC107",
            line_width=2,
            annotation_text=f"Elem {focused_element}",
            annotation_position="top left",
        )

    title = f"Measurements vs Elements (Frequency Channel: {frequency_label})"
    apply_theme_layout(fig, title=title, height=height)
    fig.update_xaxes(title_text="Radar Element Index")
    fig.update_yaxes(title_text=f"{data_type} [{unit}]")
    return fig


def create_measurements_vs_frequency_plot(
    frames: List[RadarFrame],
    element_id: int = 1,
    focused_frequency: Optional[str] = None,
    phase_mode: str = "degrees",
    thresholds: Optional[ThresholdSettings] = None,
    height: int = 420,
) -> go.Figure:
    """Plot measurements across all frequency channels for a selected radar element."""
    fig = go.Figure()

    if not frames:
        fig.add_annotation(
            text="No data loaded or selected",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Measurements vs Frequency", height=height)

    data_type = frames[0].data_type
    unit = "deg" if data_type == "PHASE" and phase_mode == "degrees" else frames[0].display_unit

    for idx, frame in enumerate(frames):
        mat = frame.get_display_matrix(phase_mode=phase_mode)
        if element_id in frame.element_ids:
            row_idx = frame.element_ids.index(element_id)
            y_vals = mat[row_idx, :]
        else:
            y_vals = mat[0, :]

        color = get_test_color(idx)
        fig.add_trace(go.Scatter(
            x=frame.frequency_labels,
            y=y_vals,
            mode="lines+markers",
            name=frame.test_id,
            line=dict(color=color, width=1.8),
            marker=dict(size=4, color=color),
            hovertemplate=(
                f"<b>{frame.test_id}</b><br>"
                "Channel: %{x}<br>"
                f"Value: %{{y:.2f}} {unit}<br>"
                f"Element: {element_id}"
                "<extra></extra>"
            ),
        ))

    # Add threshold reference lines if configured
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            fig.add_hline(
                y=thresholds.amp_min_db,
                line_dash="dash",
                line_color="#F44336",
            )
            fig.add_hline(
                y=thresholds.amp_max_db,
                line_dash="dash",
                line_color="#F44336",
            )
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            fig.add_hline(
                y=thresholds.noise_max_db,
                line_dash="dash",
                line_color="#F44336",
            )

    # Highlight focused frequency if provided
    if focused_frequency and focused_frequency in frames[0].frequency_labels:
        freq_idx = frames[0].frequency_labels.index(focused_frequency)
        fig.add_vline(
            x=freq_idx,
            line_dash="dot",
            line_color="#FFC107",
            line_width=2,
            annotation_text=f"Freq {focused_frequency}",
            annotation_position="top left",
        )

    title = f"Measurements vs Frequency (Element: {element_id})"
    apply_theme_layout(fig, title=title, height=height)
    fig.update_xaxes(title_text="Frequency Channel")
    fig.update_yaxes(title_text=f"{data_type} [{unit}]")
    return fig
