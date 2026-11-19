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
    height: int = 420,
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
            font=dict(size=14, color="#888888"),
        )
        return apply_theme_layout(fig, "Statistical Distribution", height=height)

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
                opacity=0.65,
                nbinsx=40,
                hovertemplate=f"<b>{frame.test_id}</b><br>Value: %{{x:.2f}} {unit}<br>Count: %{{y}}<extra></extra>",
            ))

    if plot_type == "histogram":
        fig.update_layout(barmode="overlay")
        fig.update_xaxes(title_text=f"Measurement [{unit}]")
        fig.update_yaxes(title_text="Count")
        title = f"Measurement Distribution Histogram ({data_type})"
    else:
        fig.update_xaxes(title_text="Test")
        fig.update_yaxes(title_text=f"Measurement [{unit}]")
        title = f"Measurement Distribution Box Plots ({data_type})"

    # Threshold limits
    if thresholds:
        if data_type == "AMP" and thresholds.amp_limits_enabled:
            if plot_type == "histogram":
                fig.add_vline(x=thresholds.amp_min_db, line_dash="dash", line_color="#F44336")
                fig.add_vline(x=thresholds.amp_max_db, line_dash="dash", line_color="#F44336")
            else:
                fig.add_hline(y=thresholds.amp_min_db, line_dash="dash", line_color="#F44336")
                fig.add_hline(y=thresholds.amp_max_db, line_dash="dash", line_color="#F44336")
        elif data_type == "NOISE" and thresholds.noise_limits_enabled:
            if plot_type == "histogram":
                fig.add_vline(x=thresholds.noise_max_db, line_dash="dash", line_color="#F44336")
            else:
                fig.add_hline(y=thresholds.noise_max_db, line_dash="dash", line_color="#F44336")

    apply_theme_layout(fig, title=title, height=height)
    return fig
