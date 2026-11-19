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
    height: int = 420,
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
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Test-to-Baseline Difference Curve", height=height)

    stats = compute_difference_statistics(test_frame, ref_frame, phase_mode=phase_mode)
    unit = "deg" if test_frame.data_type == "PHASE" and phase_mode == "degrees" else test_frame.display_unit

    if frequency_label in test_frame.frequency_labels:
        col_idx = test_frame.frequency_labels.index(frequency_label)
        diff_y = stats.diff_matrix[:, col_idx]
    else:
        diff_y = stats.diff_matrix[:, 0]

    # Zero reference line
    fig.add_hline(y=0.0, line_dash="solid", line_color="#888888", line_width=1)

    fig.add_trace(go.Scatter(
        x=test_frame.element_ids,
        y=diff_y,
        mode="lines+markers",
        name=f"{test_frame.test_id} - {ref_frame.test_id}",
        line=dict(color=PALETTE["primary"], width=2),
        marker=dict(size=4, color=PALETTE["primary"]),
        hovertemplate=(
            f"<b>Diff: {test_frame.test_id} vs {ref_frame.test_id}</b><br>"
            "Element: %{x}<br>"
            f"Delta: %{{y:+.2f}} {unit}<br>"
            f"Channel: {frequency_label}"
            "<extra></extra>"
        ),
    ))

    # Metric annotations
    stats_text = f"Mean Diff: {stats.mean_diff:+.2f} {unit} | RMS Diff: {stats.rms_diff:.2f} {unit} | Max |Diff|: {stats.max_abs_diff:.2f} {unit}"
    fig.add_annotation(
        text=stats_text,
        xref="paper",
        yref="paper",
        x=0.02,
        y=0.98,
        showarrow=False,
        bgcolor="rgba(255, 255, 255, 0.85)",
        bordercolor=PALETTE["border"],
        borderwidth=1,
        font=dict(size=11, color=PALETTE["text_main"]),
    )

    title = f"Delta Curve: {test_frame.test_id} minus {ref_frame.test_id} (Channel {frequency_label})"
    apply_theme_layout(fig, title=title, height=height)
    fig.update_xaxes(title_text="Element Index")
    fig.update_yaxes(title_text=f"Delta [{unit}]")
    return fig


def create_element_stability_curve(
    stability: Optional[StabilityMetrics],
    element_ids: List[int],
    data_type: str = "AMP",
    height: int = 420,
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
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Per-Element Stability Across Tests", height=height)

    unit = "deg" if data_type == "PHASE" else "dB"
    mean_std_per_elem = np.nanmean(stability.std_matrix, axis=1)

    fig.add_trace(go.Bar(
        x=element_ids,
        y=mean_std_per_elem,
        name="Element Std Dev",
        marker_color=PALETTE["primary"],
        hovertemplate="Element: %{x}<br>Avg Std Dev: %{y:.3f} " + unit + "<extra></extra>",
    ))

    # Threshold indicator for high variance
    high_var_thresh = float(np.mean(mean_std_per_elem) + 2.0 * np.std(mean_std_per_elem))
    fig.add_hline(
        y=high_var_thresh,
        line_dash="dash",
        line_color=PALETTE["error"],
        annotation_text="High Variation Threshold (+2σ)",
        annotation_position="top right",
    )

    title = f"Per-Element Stability Across Tests ({data_type})"
    apply_theme_layout(fig, title=title, height=height)
    fig.update_xaxes(title_text="Radar Element Index")
    fig.update_yaxes(title_text=f"Std Dev Across Tests [{unit}]")
    return fig


def create_frequency_stability_curve(
    stability: Optional[StabilityMetrics],
    frequency_labels: List[str],
    data_type: str = "AMP",
    height: int = 420,
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
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Per-Frequency Stability Across Tests", height=height)

    unit = "deg" if data_type == "PHASE" else "dB"
    mean_std_per_freq = np.nanmean(stability.std_matrix, axis=0)

    fig.add_trace(go.Bar(
        x=frequency_labels,
        y=mean_std_per_freq,
        name="Channel Std Dev",
        marker_color=PALETTE["primary_hover"],
        hovertemplate="Channel: %{x}<br>Avg Std Dev: %{y:.3f} " + unit + "<extra></extra>",
    ))

    high_var_thresh = float(np.mean(mean_std_per_freq) + 2.0 * np.std(mean_std_per_freq))
    fig.add_hline(
        y=high_var_thresh,
        line_dash="dash",
        line_color=PALETTE["error"],
        annotation_text="High Noise Threshold (+2σ)",
        annotation_position="top right",
    )

    title = f"Per-Frequency Channel Stability Across Tests ({data_type})"
    apply_theme_layout(fig, title=title, height=height)
    fig.update_xaxes(title_text="Frequency Channel")
    fig.update_yaxes(title_text=f"Std Dev Across Tests [{unit}]")
    return fig
