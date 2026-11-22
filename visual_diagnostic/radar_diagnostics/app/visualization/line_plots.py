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
    height: int = 380,
    show_title: bool = False,
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
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height)

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
            mode="lines",
            name=frame.test_id,
            line=dict(color=color, width=1.75),
            hovertemplate=(
                f"<b>{frame.test_id}</b><br>"
                "Element: %{x}<br>"
                f"Value: %{{y:.2f}} {unit}<br>"
                f"Channel: {frequency_label}"
                "<extra></extra>"
            ),
        ))

    # Add subtle threshold reference lines if configured
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            fig.add_hline(
                y=thresholds.amp_min_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
                annotation_text=f"Min ({thresholds.amp_min_db} dB)",
                annotation_position="bottom right",
                annotation_font=dict(size=10, color="#DC2626"),
            )
            fig.add_hline(
                y=thresholds.amp_max_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
                annotation_text=f"Max ({thresholds.amp_max_db} dB)",
                annotation_position="top right",
                annotation_font=dict(size=10, color="#DC2626"),
            )
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            fig.add_hline(
                y=thresholds.noise_max_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
                annotation_text=f"Max ({thresholds.noise_max_db} dB)",
                annotation_position="top right",
                annotation_font=dict(size=10, color="#DC2626"),
            )

    # Highlight focused element if provided
    if focused_element is not None:
        fig.add_vline(
            x=focused_element,
            line_dash="dash",
            line_color="#0891B2",
            line_width=1.5,
            annotation_text=f"Elem {focused_element}",
            annotation_position="top left",
            annotation_font=dict(size=10, color="#0891B2"),
        )

    title_str = f"Measurements vs Elements (Channel: {frequency_label})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height)
    
    # Clean major ticks every 25 or 50 elements
    if frames and frames[0].element_ids:
        elem_count = len(frames[0].element_ids)
        step = 25 if elem_count <= 128 else 50
        tick_vals = list(range(1, elem_count + 1, step))
        if elem_count not in tick_vals:
            tick_vals.append(elem_count)
        fig.update_xaxes(
            title_text="Radar Element Index",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=[str(v) for v in tick_vals],
        )
    else:
        fig.update_xaxes(title_text="Radar Element Index")

    fig.update_yaxes(title_text=f"{data_type} [{unit}]")
    return fig


def create_measurements_vs_frequency_plot(
    frames: List[RadarFrame],
    element_id: int = 1,
    focused_frequency: Optional[str] = None,
    phase_mode: str = "degrees",
    thresholds: Optional[ThresholdSettings] = None,
    height: int = 340,
    show_title: bool = False,
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
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height)

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
            x=list(range(len(frame.frequency_labels))),
            y=y_vals,
            mode="lines",
            name=frame.test_id,
            line=dict(color=color, width=1.75),
            hovertemplate=(
                f"<b>{frame.test_id}</b><br>"
                "Channel: %{customdata}<br>"
                f"Value: %{{y:.2f}} {unit}<br>"
                f"Element: {element_id}"
                "<extra></extra>"
            ),
            customdata=frame.frequency_labels,
        ))

    # Add subtle threshold lines if configured
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            fig.add_hline(
                y=thresholds.amp_min_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
            )
            fig.add_hline(
                y=thresholds.amp_max_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
            )
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            fig.add_hline(
                y=thresholds.noise_max_db,
                line_dash="dot",
                line_color="#DC2626",
                line_width=1.2,
            )

    # Highlight focused frequency channel
    if focused_frequency and focused_frequency in frames[0].frequency_labels:
        freq_idx = frames[0].frequency_labels.index(focused_frequency)
        fig.add_vline(
            x=freq_idx,
            line_dash="dash",
            line_color="#0891B2",
            line_width=1.5,
            annotation_text=f"Ch {focused_frequency}",
            annotation_position="top left",
            annotation_font=dict(size=10, color="#0891B2"),
        )

    title_str = f"Measurements vs Frequency (Element: {element_id})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height)

    # Clean frequency channel ticks: show every 4th or 8th label to eliminate crowding
    if frames and frames[0].frequency_labels:
        labels = frames[0].frequency_labels
        step = 4 if len(labels) <= 32 else 8
        tick_indices = list(range(0, len(labels), step))
        if (len(labels) - 1) not in tick_indices:
            tick_indices.append(len(labels) - 1)
        fig.update_xaxes(
            title_text="Frequency Channel",
            tickmode="array",
            tickvals=tick_indices,
            ticktext=[labels[i] for i in tick_indices],
        )
    else:
        fig.update_xaxes(title_text="Frequency Channel")

    fig.update_yaxes(title_text=f"{data_type} [{unit}]")
    return fig
