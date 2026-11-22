"""Comparison and stability curve visualizations for radar diagnostics.
"""

from typing import List, Optional
import numpy as np
import plotly.graph_objects as go

from app.core.statistics import StabilityMetrics, compute_difference_statistics
from app.models.radar_frame import RadarFrame
from app.visualization.color_palette import apply_theme_layout, PALETTE


def create_test_difference_curve(
    test_frame: Optional[RadarFrame],
    ref_frame: Optional[RadarFrame],
    frequency_label: str = "A",
    phase_mode: str = "degrees",
    height: int = 340,
    show_title: bool = False,
) -> go.Figure:
    """Plot difference between test_frame and baseline reference across elements for a frequency."""
    fig = go.Figure()

    if test_frame is None or ref_frame is None:
        fig.add_annotation(
            text="Select both a test and a baseline reference",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height, show_legend=False)

    stats = compute_difference_statistics(test_frame, ref_frame, phase_mode=phase_mode)
    unit = "deg" if test_frame.data_type == "PHASE" and phase_mode == "degrees" else test_frame.display_unit

    if frequency_label in test_frame.frequency_labels:
        col_idx = test_frame.frequency_labels.index(frequency_label)
        diff_y = stats.diff_matrix[:, col_idx]
    else:
        diff_y = stats.diff_matrix[:, 0]

    # Zero reference line
    fig.add_hline(y=0.0, line_dash="solid", line_color="#CBD5E1", line_width=1.2)

    fig.add_trace(go.Scatter(
        x=test_frame.element_ids,
        y=diff_y,
        mode="lines",
        name=f"{test_frame.test_id} - {ref_frame.test_id}",
        line=dict(color=PALETTE["primary"], width=2),
        hovertemplate=(
            f"<b>Diff: {test_frame.test_id} vs {ref_frame.test_id}</b><br>"
            "Element: %{x}<br>"
            f"Delta: %{{y:+.2f}} {unit}<br>"
            f"Channel: {frequency_label}"
            "<extra></extra>"
        ),
    ))

    title_str = f"Delta Curve: {test_frame.test_id} minus {ref_frame.test_id} (Channel {frequency_label})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)

    if test_frame.element_ids:
        elem_count = len(test_frame.element_ids)
        step = 25 if elem_count <= 128 else 50
        tick_vals = list(range(1, elem_count + 1, step))
        if elem_count not in tick_vals:
            tick_vals.append(elem_count)
        fig.update_xaxes(
            title_text="Element Index",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=[str(v) for v in tick_vals],
        )
    else:
        fig.update_xaxes(title_text="Element Index")

    fig.update_yaxes(title_text=f"Delta [{unit}]")
    return fig


def create_element_stability_curve(
    stability: Optional[StabilityMetrics],
    element_ids: List[int],
    data_type: str = "AMP",
    height: int = 340,
    show_title: bool = False,
) -> go.Figure:
    """Plot average standard deviation per element across all tests."""
    fig = go.Figure()

    if stability is None:
        fig.add_annotation(
            text="Need at least 2 tests to compute stability",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height, show_legend=False)

    unit = "deg" if data_type == "PHASE" else "dB"
    mean_std_per_elem = np.nanmean(stability.std_matrix, axis=1)

    fig.add_trace(go.Bar(
        x=element_ids,
        y=mean_std_per_elem,
        name="Element Std Dev",
        marker_color=PALETTE["primary"],
        hovertemplate="Element: %{x}<br>Avg Std Dev: %{y:.3f} " + unit + "<extra></extra>",
    ))

    high_var_thresh = float(np.mean(mean_std_per_elem) + 2.0 * np.std(mean_std_per_elem))
    fig.add_hline(
        y=high_var_thresh,
        line_dash="dot",
        line_color=PALETTE["error"],
        line_width=1.2,
        annotation_text="High Variation (+2σ)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=PALETTE["error"]),
    )

    title_str = f"Per-Element Stability Across Tests ({data_type})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)

    if element_ids:
        elem_count = len(element_ids)
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

    fig.update_yaxes(title_text=f"Std Dev [{unit}]")
    return fig


def create_frequency_stability_curve(
    stability: Optional[StabilityMetrics],
    frequency_labels: List[str],
    data_type: str = "AMP",
    height: int = 340,
    show_title: bool = False,
) -> go.Figure:
    """Plot average standard deviation per frequency channel across all tests."""
    fig = go.Figure()

    if stability is None:
        fig.add_annotation(
            text="Need at least 2 tests to compute stability",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height, show_legend=False)

    unit = "deg" if data_type == "PHASE" else "dB"
    mean_std_per_freq = np.nanmean(stability.std_matrix, axis=0)

    fig.add_trace(go.Bar(
        x=list(range(len(frequency_labels))),
        y=mean_std_per_freq,
        name="Channel Std Dev",
        marker_color=PALETTE["primary_hover"],
        hovertemplate="Channel: %{customdata}<br>Avg Std Dev: %{y:.3f} " + unit + "<extra></extra>",
        customdata=frequency_labels,
    ))

    high_var_thresh = float(np.mean(mean_std_per_freq) + 2.0 * np.std(mean_std_per_freq))
    fig.add_hline(
        y=high_var_thresh,
        line_dash="dot",
        line_color=PALETTE["error"],
        line_width=1.2,
        annotation_text="High Noise (+2σ)",
        annotation_position="top right",
        annotation_font=dict(size=10, color=PALETTE["error"]),
    )

    title_str = f"Per-Frequency Channel Stability Across Tests ({data_type})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)

    if frequency_labels:
        labels = frequency_labels
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

    fig.update_yaxes(title_text=f"Std Dev [{unit}]")
    return fig
