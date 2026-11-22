"""Reusable UI widgets and design system components for PSP Radar Diagnostics.
"""

from typing import Callable, Optional
from nicegui import ui
import plotly.graph_objects as go


def create_card_header(
    title: str,
    subtitle: str = "",
    icon: Optional[str] = None,
    on_expand: Optional[Callable[[], None]] = None,
):
    """Render a clean, standard card header row with title, subtitle, and optional expand action."""
    with ui.row().classes("w-full justify-between items-center mb-3"):
        with ui.column().classes("gap-0"):
            with ui.row().classes("items-center gap-2"):
                if icon:
                    ui.icon(icon, size="20px", color="primary").classes("opacity-80")
                ui.label(title).classes("card-title m-0")
            if subtitle:
                ui.label(subtitle).classes("card-subtitle")

        if on_expand:
            ui.button(
                icon="open_in_full",
                on_click=on_expand,
            ).props("flat round dense size=sm").classes("text-slate-400 hover:text-blue-600").tooltip("Expand chart to full modal view")


def create_kpi_card(
    label: str,
    value: str,
    unit: str = "",
    subtext: str = "",
    is_alert: bool = False,
):
    """Render a modern, uniform KPI metric card with tabular typography."""
    with ui.card().classes("kpi-card"):
        ui.label(label).classes("kpi-label")
        with ui.row().classes("items-baseline gap-1"):
            val_classes = "kpi-val text-red-600" if is_alert else "kpi-val"
            ui.label(value).classes(val_classes)
            if unit:
                ui.label(unit).classes("kpi-unit")
        if subtext:
            ui.label(subtext).classes("kpi-sub")


def render_status_chip(status: str):
    """Render a modern semantic status chip with badge styling."""
    status_upper = str(status).upper()
    if status_upper in ["PASS", "OK", "STABLE", "CONNECTED", "REC ON"]:
        ui.label(status_upper).classes("chip-pass")
    elif status_upper in ["WARNING", "WARN", "DRIFT", "CONNECTING"]:
        ui.label(status_upper).classes("chip-warn")
    elif status_upper in ["FAIL", "ERROR", "DISCONNECTED", "UNSTABLE"]:
        ui.label(status_upper).classes("chip-fail")
    else:
        ui.label(status_upper).classes("chip-info")


def open_expanded_chart_dialog(title: str, fig: go.Figure):
    """Display an expanded full-size chart inside a high-detail modal dialog."""
    # Clone and increase height for expanded view
    expanded_fig = go.Figure(fig)
    expanded_fig.update_layout(height=650, margin=dict(l=60, r=30, t=50, b=50))

    with ui.dialog() as dialog, ui.card().classes("modal-chart-card"):
        with ui.row().classes("w-full justify-between items-center pb-2 border-b border-slate-200 mb-3"):
            with ui.row().classes("items-center gap-2"):
                ui.icon("analytics", size="22px", color="primary")
                ui.label(title).classes("text-base font-bold text-slate-800")
            ui.button(icon="close", on_click=dialog.close).props("flat round dense size=md")

        ui.plotly(expanded_fig).classes("w-full")
    dialog.open()
