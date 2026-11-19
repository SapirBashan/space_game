"""Diagnostics Report and CSV Export Generators.

Generates comprehensive HTML laboratory reports with embedded Plotly charts
and CSV exports of processed statistics, element rankings, and anomaly records.
"""

import io
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional
import pandas as pd

from app.config import default_config
from app.core.anomaly_detection import AnomalyRecord, ElementRanking, FrequencyRanking
from app.core.session_manager import SessionManager
from app.visualization.comparison_plots import create_element_stability_curve
from app.visualization.heatmaps import create_matrix_heatmap
from app.visualization.line_plots import create_measurements_vs_elements_plot


def export_anomalies_to_csv(anomalies: List[AnomalyRecord]) -> str:
    """Serialize anomaly records into CSV string."""
    rows = []
    for a in anomalies:
        rows.append({
            "TestID": a.test_id,
            "ElementID": a.element_id,
            "FrequencyChannel": a.frequency_label,
            "MeasuredValue": a.measured_value,
            "ExpectedOrLimit": a.expected_or_limit,
            "Deviation": a.deviation,
            "Unit": a.unit,
            "Severity": a.severity,
            "Reason": a.reason,
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_element_rankings_to_csv(rankings: List[ElementRanking]) -> str:
    """Serialize element rankings into CSV string."""
    rows = []
    for r in rankings:
        rows.append({
            "ElementID": r.element_id,
            "ElementIndex": r.element_index,
            "StdDevAcrossTests": r.std_dev,
            "Spread": r.spread,
            "MaxBaselineDeviation": r.max_baseline_dev,
            "AnomalyCount": r.anomaly_count,
            "Status": r.status,
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_frequency_rankings_to_csv(rankings: List[FrequencyRanking]) -> str:
    """Serialize frequency channel rankings into CSV string."""
    rows = []
    for r in rankings:
        rows.append({
            "FrequencyChannel": r.frequency_label,
            "FrequencyIndex": r.frequency_index,
            "StdDevAcrossTests": r.std_dev,
            "Spread": r.spread,
            "MaxBaselineDeviation": r.max_baseline_dev,
            "AnomalyCount": r.anomaly_count,
            "Status": r.status,
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def export_test_summary_to_csv(manager: SessionManager) -> str:
    """Serialize test summary metrics table into CSV string."""
    summary = manager.get_summary_metrics()
    rows = []
    for ts in summary.test_summaries:
        rows.append({
            "TestID": ts.test_id,
            "DataType": ts.data_type,
            "Unit": ts.unit,
            "Mean": ts.mean,
            "StdDev": ts.std_dev,
            "Min": ts.min_val,
            "Max": ts.max_val,
            "Median": ts.median,
            "MissingCount": ts.missing_count,
            "ThresholdViolations": ts.threshold_violations,
            "Status": ts.status,
        })
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def generate_html_report(manager: SessionManager, output_path: Optional[str] = None) -> str:
    """Generate a comprehensive HTML engineering report with embedded Plotly visualizations."""
    summary = manager.get_summary_metrics()
    anomalies = manager.get_all_anomalies()
    elem_rankings = manager.get_element_rankings()
    freq_rankings = manager.get_frequency_rankings()
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    frames = manager.get_filtered_frames()
    first_frame = frames[0] if frames else None

    # Generate embedded charts
    chart_elem_html = ""
    chart_heat_html = ""
    chart_stab_html = ""

    if frames:
        fig_elem = create_measurements_vs_elements_plot(
            frames,
            frequency_label=manager.focused_frequency,
            thresholds=manager.thresholds,
            height=380,
        )
        chart_elem_html = fig_elem.to_html(full_html=False, include_plotlyjs="cdn")

        fig_heat = create_matrix_heatmap(first_frame, height=380)
        chart_heat_html = fig_heat.to_html(full_html=False, include_plotlyjs=False)

        stability = manager.get_stability_metrics()
        if stability:
            fig_stab = create_element_stability_curve(stability, first_frame.element_ids, data_type=manager.active_data_type, height=380)
            chart_stab_html = fig_stab.to_html(full_html=False, include_plotlyjs=False)

    # Build test summary table rows
    test_rows_html = ""
    for ts in summary.test_summaries:
        badge_color = "#4CAF50" if ts.status == "PASS" else ("#FFC107" if ts.status == "WARNING" else "#F44336")
        test_rows_html += f"""
        <tr>
            <td><b>{ts.test_id}</b></td>
            <td>{ts.mean:.2f}</td>
            <td>{ts.std_dev:.2f}</td>
            <td>{ts.min_val:.2f}</td>
            <td>{ts.max_val:.2f}</td>
            <td>{ts.median:.2f}</td>
            <td>{ts.missing_count}</td>
            <td>{ts.threshold_violations}</td>
            <td><span style="background-color:{badge_color}; color:white; padding:2px 8px; border-radius:4px; font-size:11px; font-weight:bold;">{ts.status}</span></td>
        </tr>
        """

    # Build anomaly rows (top 20)
    anomaly_rows_html = ""
    for a in anomalies[:25]:
        badge_color = "#F44336" if a.severity == "FAIL" else "#FFC107"
        anomaly_rows_html += f"""
        <tr>
            <td>{a.test_id}</td>
            <td>{a.element_id}</td>
            <td>{a.frequency_label}</td>
            <td>{a.measured_value} {a.unit}</td>
            <td>{a.expected_or_limit} {a.unit}</td>
            <td>{a.deviation:+} {a.unit}</td>
            <td><span style="background-color:{badge_color}; color:white; padding:2px 6px; border-radius:4px; font-size:11px;">{a.severity}</span></td>
            <td>{a.reason}</td>
        </tr>
        """

    # Top unstable elements
    unstable_elem_rows = ""
    for r in elem_rankings[:10]:
        badge_color = "#4CAF50" if r.status == "PASS" else ("#FFC107" if r.status == "WARNING" else "#F44336")
        unstable_elem_rows += f"""
        <tr>
            <td><b>Element {r.element_id}</b></td>
            <td>{r.std_dev:.3f}</td>
            <td>{r.spread:.3f}</td>
            <td>{r.max_baseline_dev:.3f}</td>
            <td>{r.anomaly_count}</td>
            <td><span style="background-color:{badge_color}; color:white; padding:2px 6px; border-radius:4px; font-size:11px;">{r.status}</span></td>
        </tr>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>PSP Radar Diagnostics Report - {manager.session_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
            background-color: #FAFAFA;
            color: #333333;
            margin: 0;
            padding: 24px;
        }}
        .header {{
            background-color: #1976D2;
            color: #FFFFFF;
            padding: 20px 24px;
            border-radius: 6px;
            margin-bottom: 24px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header h1 {{
            margin: 0 0 6px 0;
            font-size: 22px;
            letter-spacing: 0.5px;
        }}
        .header-meta {{
            font-size: 13px;
            opacity: 0.9;
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .card {{
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 16px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .card-label {{
            font-size: 12px;
            color: #666666;
            text-transform: uppercase;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .card-value {{
            font-size: 20px;
            font-weight: bold;
            color: #1976D2;
        }}
        .section {{
            background-color: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 20px;
            margin-bottom: 24px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #1976D2;
            margin-top: 0;
            margin-bottom: 16px;
            border-bottom: 2px solid #E0E0E0;
            padding-bottom: 8px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 8px;
        }}
        th {{
            background-color: #EEEEEE;
            color: #333333;
            text-align: left;
            padding: 8px 12px;
            border: 1px solid #E0E0E0;
        }}
        td {{
            padding: 8px 12px;
            border: 1px solid #E0E0E0;
        }}
        tr:nth-child(even) {{
            background-color: #F9F9F9;
        }}
        .chart-box {{
            margin-bottom: 20px;
            background: #FFFFFF;
            border: 1px solid #E0E0E0;
            border-radius: 6px;
            padding: 12px;
        }}
    </style>
</head>
<body>

    <div class="header">
        <h1>PSP RADAR DIAGNOSTICS REPORT</h1>
        <div class="header-meta">
            Session: <b>{manager.session_name}</b> | Data Type: <b>{manager.active_data_type}</b> ({summary.unit}) | Generated: {now_str}
        </div>
    </div>

    <div class="grid">
        <div class="card">
            <div class="card-label">Tests Loaded</div>
            <div class="card-value">{summary.test_count}</div>
        </div>
        <div class="card">
            <div class="card-label">Elements x Freqs</div>
            <div class="card-value">{summary.element_count} x {summary.frequency_count}</div>
        </div>
        <div class="card">
            <div class="card-label">Overall Mean</div>
            <div class="card-value">{summary.overall_mean:.2f} {summary.unit}</div>
        </div>
        <div class="card">
            <div class="card-label">Overall Std Dev</div>
            <div class="card-value">{summary.overall_std:.2f} {summary.unit}</div>
        </div>
        <div class="card">
            <div class="card-label">Threshold Violations</div>
            <div class="card-value" style="color: {'#F44336' if summary.total_threshold_violations > 0 else '#4CAF50'};">
                {summary.total_threshold_violations}
            </div>
        </div>
    </div>

    <div class="section">
        <div class="section-title">Individual Test Summaries</div>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Mean ({summary.unit})</th>
                    <th>Std Dev</th>
                    <th>Min</th>
                    <th>Max</th>
                    <th>Median</th>
                    <th>Missing</th>
                    <th>Violations</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {test_rows_html or '<tr><td colspan="9">No tests evaluated.</td></tr>'}
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Diagnostic Visualizations</div>
        <div class="chart-box">{chart_elem_html}</div>
        <div class="chart-box">{chart_heat_html}</div>
        {f'<div class="chart-box">{chart_stab_html}</div>' if chart_stab_html else ''}
    </div>

    <div class="section">
        <div class="section-title">Most Unstable Elements Ranking</div>
        <table>
            <thead>
                <tr>
                    <th>Element</th>
                    <th>Avg Std Dev</th>
                    <th>Peak-to-Peak Spread</th>
                    <th>Max Baseline Dev</th>
                    <th>Anomaly Count</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
                {unstable_elem_rows or '<tr><td colspan="6">Insufficient tests for stability analysis.</td></tr>'}
            </tbody>
        </table>
    </div>

    <div class="section">
        <div class="section-title">Detected Measurement Anomalies (Top 25)</div>
        <table>
            <thead>
                <tr>
                    <th>Test ID</th>
                    <th>Element</th>
                    <th>Channel</th>
                    <th>Measured</th>
                    <th>Limit / Baseline</th>
                    <th>Deviation</th>
                    <th>Severity</th>
                    <th>Diagnostic Reason</th>
                </tr>
            </thead>
            <tbody>
                {anomaly_rows_html or '<tr><td colspan="8">No anomalies detected within configured limits.</td></tr>'}
            </tbody>
        </table>
    </div>

</body>
</html>
    """

    if output_path:
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)

    return html
