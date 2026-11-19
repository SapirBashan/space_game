"""Plotly visual styling and color assignments for radar diagnostics.
"""

from typing import Dict, List, Optional
import plotly.graph_objects as go
from app.config import PALETTE, TEST_COLORS


def get_test_color(test_index: int) -> str:
    """Get a consistent high-contrast color for a test index."""
    return TEST_COLORS[test_index % len(TEST_COLORS)]


def apply_theme_layout(fig: go.Figure, title: str = "", height: int = 420) -> go.Figure:
    """Apply modern high-contrast engineering styling to a Plotly figure."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>" if title else "",
            font=dict(size=14, color=PALETTE["text_main"], family="-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"),
            x=0.015,
            y=0.96,
        ),
        paper_bgcolor=PALETTE["surface"],
        plot_bgcolor="#FFFFFF",
        height=height,
        margin=dict(l=55, r=25, t=45, b=45),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1.0,
            font=dict(size=11, color=PALETTE["text_main"], family="sans-serif"),
            bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor=PALETTE["border"],
            borderwidth=1,
        ),
        xaxis=dict(
            showgrid=True,
            gridcolor="#E2E8F0",
            gridwidth=1,
            zeroline=True,
            zerolinecolor=PALETTE["border"],
            zerolinewidth=1,
            linecolor=PALETTE["border"],
            linewidth=1,
            tickfont=dict(size=11, color=PALETTE["text_main"]),
            title_font=dict(size=12, color=PALETTE["text_secondary"], family="sans-serif"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#E2E8F0",
            gridwidth=1,
            zeroline=True,
            zerolinecolor=PALETTE["border"],
            zerolinewidth=1,
            linecolor=PALETTE["border"],
            linewidth=1,
            tickfont=dict(size=11, color=PALETTE["text_main"]),
            title_font=dict(size=12, color=PALETTE["text_secondary"], family="sans-serif"),
        ),
        hoverlabel=dict(
            bgcolor=PALETTE["surface"],
            font_size=12,
            font_family="sans-serif",
            bordercolor=PALETTE["primary"],
        ),
    )
    return fig
