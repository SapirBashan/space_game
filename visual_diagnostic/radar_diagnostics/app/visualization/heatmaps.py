"""Heatmap visualizers for 2D radar measurement matrices, differences, and stability.
"""

from typing import List, Optional
import numpy as np
import plotly.graph_objects as go

from app.core.statistics import StabilityMetrics, compute_difference_matrix
from app.models.radar_frame import RadarFrame
from app.visualization.color_palette import apply_theme_layout


def _thin_axes(fig: go.Figure, freq_labels: List[str], element_ids: List[int]):
    """Apply clean, uncrowded major ticks to heatmap axes."""
    if freq_labels:
        step = 4 if len(freq_labels) <= 32 else 8
        tick_indices = list(range(0, len(freq_labels), step))
        if (len(freq_labels) - 1) not in tick_indices:
            tick_indices.append(len(freq_labels) - 1)
        fig.update_xaxes(
            title_text="Frequency Channel",
            tickmode="array",
            tickvals=[freq_labels[i] for i in tick_indices],
            ticktext=[freq_labels[i] for i in tick_indices],
        )

    if element_ids:
        elem_count = len(element_ids)
        step = 25 if elem_count <= 128 else 50
        tick_vals = list(range(1, elem_count + 1, step))
        if elem_count not in tick_vals:
            tick_vals.append(elem_count)
        fig.update_yaxes(
            title_text="Element Index",
            autorange="reversed",
            tickmode="array",
            tickvals=tick_vals,
            ticktext=[str(v) for v in tick_vals],
        )


def create_matrix_heatmap(
    frame: Optional[RadarFrame],
    phase_mode: str = "degrees",
    height: int = 360,
    show_title: bool = False,
) -> go.Figure:
    """Create a 2D heatmap of elements vs frequencies for a radar test."""
    fig = go.Figure()

    if frame is None:
        fig.add_annotation(
            text="No test frame available",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height, show_legend=False)

    mat = frame.get_display_matrix(phase_mode=phase_mode)
    unit = "deg" if frame.data_type == "PHASE" and phase_mode == "degrees" else frame.display_unit

    if frame.data_type == "PHASE" and phase_mode == "degrees":
        colorscale = "Twilight"
        zmin, zmax = -180.0, 180.0
    elif frame.data_type == "NOISE":
        colorscale = "Cividis"
        zmin, zmax = None, None
    else:  # AMP
        colorscale = "Viridis"
        zmin, zmax = None, None

    heatmap = go.Heatmap(
        x=frame.frequency_labels,
        y=frame.element_ids,
        z=mat,
        colorscale=colorscale,
        zmin=zmin,
        zmax=zmax,
        colorbar=dict(
            title=dict(text=f"[{unit}]", side="top", font=dict(size=11, color="#475569")),
            len=0.88,
            thickness=13,
            tickfont=dict(size=10, color="#64748B"),
        ),
        hovertemplate=(
            f"<b>{frame.test_id}</b><br>"
            "Element: %{y}<br>"
            "Channel: %{x}<br>"
            f"Value: %{{z:.2f}} {unit}"
            "<extra></extra>"
        ),
    )
    fig.add_trace(heatmap)

    title_str = f"Matrix Heatmap: {frame.test_id}" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)
    _thin_axes(fig, frame.frequency_labels, frame.element_ids)
    return fig


def create_difference_heatmap(
    test_frame: Optional[RadarFrame],
    ref_frame: Optional[RadarFrame],
    phase_mode: str = "degrees",
    height: int = 360,
    show_title: bool = False,
) -> go.Figure:
    """Create a diverging difference heatmap: test_frame - ref_frame."""
    fig = go.Figure()

    if test_frame is None or ref_frame is None:
        fig.add_annotation(
            text="Select both a test and a baseline reference to view differences",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=13, color="#94A3B8"),
        )
        return apply_theme_layout(fig, height=height, show_legend=False)

    diff_mat = compute_difference_matrix(test_frame, ref_frame, phase_mode=phase_mode)
    unit = "deg" if test_frame.data_type == "PHASE" and phase_mode == "degrees" else test_frame.display_unit

    max_abs = float(np.nanmax(np.abs(diff_mat))) if diff_mat.size > 0 else 1.0
    if max_abs == 0:
        max_abs = 1.0

    heatmap = go.Heatmap(
        x=test_frame.frequency_labels,
        y=test_frame.element_ids,
        z=diff_mat,
        colorscale="RdBu_r",
        zmid=0.0,
        zmin=-max_abs,
        zmax=max_abs,
        colorbar=dict(
            title=dict(text=f"Delta [{unit}]", side="top", font=dict(size=11, color="#475569")),
            len=0.88,
            thickness=13,
            tickfont=dict(size=10, color="#64748B"),
        ),
        hovertemplate=(
            f"<b>Diff: {test_frame.test_id} vs {ref_frame.test_id}</b><br>"
            "Element: %{y}<br>"
            "Channel: %{x}<br>"
            f"Delta: %{{z:+.2f}} {unit}"
            "<extra></extra>"
        ),
    )
    fig.add_trace(heatmap)

    title_str = f"Difference: {test_frame.test_id} minus {ref_frame.test_id}" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)
    _thin_axes(fig, test_frame.frequency_labels, test_frame.element_ids)
    return fig


def create_stability_heatmap(
    stability: Optional[StabilityMetrics],
    element_ids: List[int],
    frequency_labels: List[str],
    data_type: str = "AMP",
    height: int = 360,
    show_title: bool = False,
) -> go.Figure:
    """Create a heatmap displaying the standard deviation across tests."""
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
    heatmap = go.Heatmap(
        x=frequency_labels,
        y=element_ids,
        z=stability.std_matrix,
        colorscale="Hot_r",
        colorbar=dict(
            title=dict(text=f"Std [{unit}]", side="top", font=dict(size=11, color="#475569")),
            len=0.88,
            thickness=13,
            tickfont=dict(size=10, color="#64748B"),
        ),
        hovertemplate=(
            "<b>Stability Std Dev</b><br>"
            "Element: %{y}<br>"
            "Channel: %{x}<br>"
            f"Std Dev: %{{z:.2f}} {unit}"
            "<extra></extra>"
        ),
    )
    fig.add_trace(heatmap)

    title_str = f"Cross-Test Std Dev ({data_type})" if show_title else ""
    apply_theme_layout(fig, title=title_str, height=height, show_legend=False)
    _thin_axes(fig, frequency_labels, element_ids)
    return fig
