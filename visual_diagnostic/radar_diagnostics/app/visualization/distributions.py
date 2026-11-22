"""Statistical distribution visualizations: histograms and box plots.
"""

from typing import List, Optional
import numpy as np
import plotly.graph_objects as go

from app.config import ThresholdSettings
from app.models.radar_frame import RadarFrame
from app.visualization.color_palette import apply_theme_layout, get_test_color


def create_distribution_plot(
    frames: List[RadarFrame],
    phase_mode: str = "degrees",
    plot_type: str = "histogram",  # 'histogram' or 'box'
    thresholds: Optional[ThresholdSettings] = None,
    height: int = 340,
    show_title: bool = False,
) -> go.Figure:
    """Create a statistical distribution plot (histogram or box plots) across selected tests."""
    fig = go.Figure()

    if not frames:
        fig.add_annotation(
            text="No data selected for distribution analysis",
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
        flat_vals = mat.flatten()
        valid_vals = flat_vals[~np.isnan(flat_vals)]
        color = get_test_color(idx)

        if plot_type == "box":
            fig.add_trace(go.Box(
                y=valid_vals,
                name=frame.test_id,
                marker_color=color,
                boxpoints="outliers",
                jitter=0.2,
                pointpos=-1.8,
            ))
        else:
            fig.add_trace(go.Histogram(
                x=valid_vals,
                name=frame.test_id,
                marker_color=color,
                opacity=0.6,
                nbinsx=40,
                hovertemplate=f"<b>{frame.test_id}</b><br>Value: %{{x:.2f}} {unit}<br>Count: %{{y}}<extra></extra>",
            ))

    if plot_type == "histogram":
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(title_text=f"Measurement [{unit}]")
        fig.update_yaxes(title_text="Count")
        title_str = f"Distribution Histogram ({data_type})" if show_title else ""
    else:
        fig.update_xaxes(title_text="Test ID")
        fig.update_yaxes(title_text=f"Measurement [{unit}]")
        title_str = f"Distribution Box Plots ({data_type})" if show_title else ""

    # Threshold limits
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            if plot_type == "histogram":
                fig.add_vline(x=thresholds.amp_min_db, line_dash="dot", line_color="#DC2626", line_width=1.2)
                fig.add_vline(x=thresholds.amp_max_db, line_dash="dot", line_color="#DC2626", line_width=1.2)
            else:
                fig.add_hline(y=thresholds.amp_min_db, line_dash="dot", line_color="#DC2626", line_width=1.2)
                fig.add_hline(y=thresholds.amp_max_db, line_dash="dot", line_color="#DC2626", line_width=1.2)
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            if plot_type == "histogram":
                fig.add_vline(x=thresholds.noise_max_db, line_dash="dot", line_color="#DC2626", line_width=1.2)
            else:
                fig.add_hline(y=thresholds.noise_max_db, line_dash="dot", line_color="#DC2626", line_width=1.2)

    apply_theme_layout(fig, title=title_str, height=height)
    return fig
