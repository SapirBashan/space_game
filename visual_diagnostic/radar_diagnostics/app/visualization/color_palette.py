"""Plotly visual styling and color assignments for radar diagnostics.
"""

from typing import Dict, List, Optional
import plotly.graph_objects as go
from app.config import PALETTE, TEST_COLORS


def get_test_color(test_index: int) -> str:
    """Get a consistent high-contrast color for a test index."""
    return TEST_COLORS[test_index % len(TEST_COLORS)]


def apply_theme_layout(
    fig: go.Figure,
    title: str = "",
    height: int = 380,
    show_legend: bool = True,
    margin_top: Optional[int] = None,
) -> go.Figure:
    """Apply modern engineering analytics styling (Grafana/Linear inspired) to a Plotly figure."""
    top_margin = margin_top if margin_top is not None else (36 if title else 24)
    if show_legend:
        top_margin = max(top_margin, 34)

    fig.update_layout(
        # We prefer card-level headers; if internal title is given, keep it clean and minimal
        title=dict(
            text=f"<span style='font-size: 13px; font-weight: 600; color: #142338;'>{title}</span>" if title else "",
            x=0.01,
            y=0.98,
        ),
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=50, r=20, t=top_margin, b=42),
        showlegend=show_legend,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color="#475569", family="'Inter', sans-serif"),
            bgcolor="rgba(255, 255, 255, 0.95)",
            bordercolor="#E2E8F0",
            borderwidth=1,
            itemsizing="constant",
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            gridwidth=1,
            zeroline=True,
            zerolinecolor="#E2E8F0",
            zerolinewidth=1,
            linecolor="#CBD5E1",
            linewidth=1,
            tickfont=dict(size=11, color="#64748B", family="'Inter', sans-serif"),
            title_font=dict(size=12, color="#475569", family="'Inter', sans-serif"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#F1F5F9",
            gridwidth=1,
            zeroline=True,
            zerolinecolor="#E2E8F0",
            zerolinewidth=1,
            linecolor="#CBD5E1",
            linewidth=1,
            tickfont=dict(size=11, color="#64748B", family="'Inter', sans-serif"),
            title_font=dict(size=12, color="#475569", family="'Inter', sans-serif"),
        ),
        hoverlabel=dict(
            bgcolor="#FFFFFF",
            font_size=12,
            font_family="'Inter', sans-serif",
            bordercolor="#2563EB",
        ),
        autosize=True,
    )
    return fig
