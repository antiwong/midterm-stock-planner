#!/usr/bin/env python3
"""Generate a single-page HTML report for a regression test run.

Produces a self-contained HTML file with embedded Plotly charts, summary
statistics, feature leaderboard, guard metrics, and analysis text.

Usage:
    # Generate report for a specific regression test
    python scripts/generate_regression_report.py <regression_id>

    # Generate report and open in browser
    python scripts/generate_regression_report.py <regression_id> --open

    # List available regression tests
    python scripts/generate_regression_report.py --list

    # Custom output path
    python scripts/generate_regression_report.py <regression_id> -o output/my_report.html
"""

import argparse
import json
import sys
import webbrowser
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.regression.database import RegressionDatabase
from src.regression.metrics import check_guard_metrics


# ---------------------------------------------------------------------------
# Color palette (matches dashboard)
# ---------------------------------------------------------------------------
COLORS = {
    "primary": "#E8735A",
    "bg": "#faf8f6",
    "card": "#ffffff",
    "border": "#ece3e7",
    "dark": "#2b2a2f",
    "muted": "#7a6f73",
    "success": "#10b981",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "blue": "#6366f1",
    "cyan": "#06b6d4",
}

CHART_CATEGORICAL = ["#6366f1", "#06b6d4", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6"]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_regression_data(db: RegressionDatabase, regression_id: str) -> dict:
    """Load all data for a regression test."""
    test = db.get_regression_test(regression_id)
    if not test:
        raise ValueError(f"Regression test not found: {regression_id}")

    steps = db.get_regression_steps(regression_id)
    leaderboard = db.get_feature_leaderboard(regression_id)

    # Parse JSON fields in steps
    for s in steps:
        for field in ["metrics_json", "significance_json", "feature_importance_json",
                       "feature_set_json", "feature_columns_json", "tuned_params_json"]:
            raw = s.get(field)
            if raw and isinstance(raw, str):
                try:
                    s[field.replace("_json", "")] = json.loads(raw)
                except (json.JSONDecodeError, TypeError):
                    s[field.replace("_json", "")] = None
            else:
                s[field.replace("_json", "")] = raw

    return {"test": test, "steps": steps, "leaderboard": leaderboard}


# ---------------------------------------------------------------------------
# Chart builders (return Plotly HTML fragments)
# ---------------------------------------------------------------------------

def _fig_to_html(fig: go.Figure, div_id: str = "") -> str:
    """Convert a Plotly figure to an embeddable HTML div (no full page wrapper)."""
    return fig.to_html(
        full_html=False,
        include_plotlyjs=False,
        div_id=div_id,
        config={"displayModeBar": True, "responsive": True},
    )


def build_cumulative_chart(steps: list) -> str:
    """Sharpe Ratio + Rank IC progression chart."""
    df = pd.DataFrame([{
        "step": s["step_number"],
        "feature": s["feature_added"],
        "sharpe": s.get("sharpe_ratio", 0) or 0,
        "rank_ic": s.get("mean_rank_ic", 0) or 0,
        "excess_return": s.get("excess_return", 0) or 0,
    } for s in steps])

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Scatter(
        x=df["feature"], y=df["sharpe"],
        mode="lines+markers", name="Sharpe Ratio",
        line=dict(color=CHART_CATEGORICAL[0], width=3),
        marker=dict(size=10, line=dict(width=2, color="white")),
        hovertemplate="<b>%{x}</b><br>Sharpe: %{y:.4f}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["feature"], y=df["rank_ic"],
        mode="lines+markers", name="Rank IC",
        line=dict(color=CHART_CATEGORICAL[1], width=3),
        marker=dict(size=10, line=dict(width=2, color="white")),
        hovertemplate="<b>%{x}</b><br>Rank IC: %{y:.4f}<extra></extra>",
    ), secondary_y=True)

    # Find and annotate peak Sharpe
    if len(df) > 0:
        peak_idx = df["sharpe"].idxmax()
        fig.add_annotation(
            x=df.loc[peak_idx, "feature"], y=df.loc[peak_idx, "sharpe"],
            text=f"Peak: {df.loc[peak_idx, 'sharpe']:.3f}",
            showarrow=True, arrowhead=2, arrowcolor=COLORS["primary"],
            font=dict(size=12, color=COLORS["primary"], family="Inter"),
            bgcolor="white", bordercolor=COLORS["primary"], borderwidth=1,
        )

    fig.update_layout(
        yaxis_title="Sharpe Ratio", yaxis2_title="Rank IC",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=13, family="Inter")),
        height=420, margin=dict(t=50, b=80, l=60, r=60),
        hovermode="x unified",
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(tickangle=-35, gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
    )

    return _fig_to_html(fig, "chart-cumulative")


def build_marginal_sharpe_chart(leaderboard: list) -> str:
    """Horizontal bar chart of marginal Sharpe contribution per feature."""
    df = pd.DataFrame(leaderboard)
    if df.empty or "marginal_sharpe" not in df.columns:
        return "<p>No leaderboard data.</p>"

    df = df.sort_values("marginal_sharpe", ascending=True)
    colors = [COLORS["success"] if v >= 0 else COLORS["danger"]
              for v in df["marginal_sharpe"]]

    fig = go.Figure(go.Bar(
        x=df["marginal_sharpe"], y=df["feature_name"],
        orientation="h", marker_color=colors,
        text=[f"{v:+.3f}" for v in df["marginal_sharpe"]],
        textposition="outside", textfont=dict(size=12, family="Inter"),
        hovertemplate="<b>%{y}</b><br>Marginal Sharpe: %{x:+.4f}<extra></extra>",
    ))

    fig.add_vline(x=0, line_dash="dash", line_color=COLORS["muted"], line_width=1)

    fig.update_layout(
        xaxis_title="Marginal Sharpe Contribution",
        yaxis_title="",
        height=max(300, len(df) * 45),
        margin=dict(t=20, b=40, l=140, r=80),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(gridcolor="#f0f0f0", zeroline=False),
    )

    return _fig_to_html(fig, "chart-marginal")


def build_importance_chart(steps: list) -> str:
    """Stacked bar chart showing feature importance at each step."""
    data = []
    for s in steps:
        fi = s.get("feature_importance")
        if fi and isinstance(fi, dict):
            total = sum(fi.values()) or 1.0
            for col, imp in sorted(fi.items(), key=lambda x: -x[1])[:15]:
                data.append({
                    "step": s["feature_added"],
                    "column": col,
                    "importance_pct": (imp / total) * 100,
                })

    if not data:
        return "<p>No feature importance data.</p>"

    df = pd.DataFrame(data)
    # Get top 12 features by mean importance
    top_cols = df.groupby("column")["importance_pct"].mean().nlargest(12).index.tolist()
    df = df[df["column"].isin(top_cols)]

    fig = go.Figure()
    step_order = [s["feature_added"] for s in steps]
    for i, col in enumerate(top_cols):
        col_data = df[df["column"] == col]
        fig.add_trace(go.Bar(
            x=col_data["step"], y=col_data["importance_pct"],
            name=col, marker_color=CHART_CATEGORICAL[i % len(CHART_CATEGORICAL)],
            hovertemplate="<b>%{x}</b><br>%{fullData.name}: %{y:.1f}%<extra></extra>",
        ))

    fig.update_layout(
        barmode="stack",
        yaxis_title="Feature Importance (%)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=11, family="Inter")),
        height=420, margin=dict(t=60, b=80, l=60, r=30),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(tickangle=-35, categoryorder="array", categoryarray=step_order),
        yaxis=dict(gridcolor="#f0f0f0"),
    )

    return _fig_to_html(fig, "chart-importance")


def build_guard_metrics_chart(steps: list) -> str:
    """Dual-axis chart showing max drawdown and overfitting ratio across steps."""
    data = []
    for s in steps:
        m = s.get("metrics") or {}
        data.append({
            "step": s["feature_added"],
            "max_drawdown": m.get("max_drawdown", 0) or 0,
            "train_test_ratio": m.get("train_test_sharpe_ratio", 0) or 0,
        })

    df = pd.DataFrame(data)
    if df.empty:
        return "<p>No guard metric data.</p>"

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(go.Bar(
        x=df["step"], y=df["max_drawdown"],
        name="Max Drawdown", marker_color=COLORS["danger"],
        opacity=0.7,
        hovertemplate="<b>%{x}</b><br>Max DD: %{y:.2%}<extra></extra>",
    ), secondary_y=False)

    fig.add_trace(go.Scatter(
        x=df["step"], y=df["train_test_ratio"],
        mode="lines+markers", name="Train/Test Sharpe Ratio",
        line=dict(color=COLORS["warning"], width=2),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Ratio: %{y:.1f}x<extra></extra>",
    ), secondary_y=True)

    # Threshold lines
    fig.add_hline(y=-0.30, line_dash="dot", line_color=COLORS["danger"],
                  annotation_text="DD Threshold (-30%)", secondary_y=False)
    fig.add_hline(y=2.5, line_dash="dot", line_color=COLORS["warning"],
                  annotation_text="Overfit Threshold (2.5x)", secondary_y=True)

    fig.update_layout(
        yaxis_title="Max Drawdown", yaxis2_title="Train/Test Sharpe Ratio",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                    font=dict(size=13, family="Inter")),
        height=420, margin=dict(t=50, b=80, l=60, r=60),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(tickangle=-35, gridcolor="#f0f0f0"),
        yaxis=dict(gridcolor="#f0f0f0"),
    )

    return _fig_to_html(fig, "chart-guard")


def build_sharpe_vs_ic_chart(leaderboard: list) -> str:
    """Scatter plot: marginal Sharpe vs marginal IC, sized by importance."""
    df = pd.DataFrame(leaderboard)
    if df.empty:
        return "<p>No leaderboard data.</p>"

    df["importance_pct"] = df["feature_importance_pct"].fillna(0) * 100
    df["significant"] = df["is_significant"].fillna(0).map({1: "Significant", 0: "Not Significant", True: "Significant", False: "Not Significant"})

    fig = go.Figure()

    for sig_label, color in [("Significant", COLORS["primary"]), ("Not Significant", COLORS["muted"])]:
        mask = df["significant"] == sig_label
        sub = df[mask]
        if sub.empty:
            continue
        fig.add_trace(go.Scatter(
            x=sub["marginal_rank_ic"], y=sub["marginal_sharpe"],
            mode="markers+text", name=sig_label,
            text=sub["feature_name"],
            textposition="top center", textfont=dict(size=11, family="Inter"),
            marker=dict(
                size=sub["importance_pct"].clip(5, 40),
                color=color, opacity=0.8,
                line=dict(width=2, color="white"),
            ),
            hovertemplate="<b>%{text}</b><br>Marginal IC: %{x:.4f}<br>Marginal Sharpe: %{y:+.4f}<br><extra></extra>",
        ))

    fig.add_hline(y=0, line_dash="dash", line_color="#ccc")
    fig.add_vline(x=0, line_dash="dash", line_color="#ccc")

    fig.update_layout(
        xaxis_title="Marginal Rank IC",
        yaxis_title="Marginal Sharpe",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5),
        height=450, margin=dict(t=50, b=50, l=60, r=30),
        plot_bgcolor="white", paper_bgcolor="white",
        xaxis=dict(gridcolor="#f0f0f0", zeroline=False),
        yaxis=dict(gridcolor="#f0f0f0", zeroline=False),
    )

    return _fig_to_html(fig, "chart-scatter")


# ---------------------------------------------------------------------------
# HTML template
# ---------------------------------------------------------------------------

def build_html_report(data: dict) -> str:
    """Build a complete single-page HTML report."""
    test = data["test"]
    steps = data["steps"]
    leaderboard = data["leaderboard"]

    regression_id = test.get("regression_id", "unknown")
    name = test.get("name", "Regression Test")
    created = (test.get("created_at") or "")[:19]
    duration = test.get("duration_seconds", 0) or 0
    mins, secs = divmod(int(duration), 60)

    baseline = steps[0] if steps else {}
    final = steps[-1] if steps else {}
    b_sharpe = baseline.get("sharpe_ratio", 0) or 0
    f_sharpe = final.get("sharpe_ratio", 0) or 0
    b_ic = baseline.get("mean_rank_ic", 0) or 0
    f_ic = final.get("mean_rank_ic", 0) or 0
    best_feat = test.get("best_feature", "N/A")
    best_ms = test.get("best_marginal_sharpe", 0) or 0

    # Find peak step
    peak_sharpe = 0
    peak_step = ""
    for s in steps:
        sr = s.get("sharpe_ratio", 0) or 0
        if sr > peak_sharpe:
            peak_sharpe = sr
            peak_step = s["feature_added"]

    # Build charts
    chart_cumulative = build_cumulative_chart(steps)
    chart_marginal = build_marginal_sharpe_chart(leaderboard)
    chart_importance = build_importance_chart(steps)
    chart_guard = build_guard_metrics_chart(steps)
    chart_scatter = build_sharpe_vs_ic_chart(leaderboard)

    # Build step table rows
    step_rows = ""
    for s in steps:
        step = s["step_number"]
        feat = s["feature_added"]
        sharpe = s.get("sharpe_ratio", 0) or 0
        rank_ic = s.get("mean_rank_ic", 0) or 0
        m_sharpe = s.get("marginal_sharpe")
        m_sharpe_str = f"{m_sharpe:+.4f}" if m_sharpe is not None else "—"

        sig = s.get("significance") or {}
        p_val = sig.get("rank_ic_paired_ttest", {}).get("p_value")
        p_str = f"{p_val:.4f}" if p_val is not None else "—"
        is_sig = sig.get("rank_ic_paired_ttest", {}).get("significant", False)
        sig_badge = '<span class="badge badge-sig">SIG</span>' if is_sig else '<span class="badge badge-ns">ns</span>' if p_val is not None else "—"

        # Row color
        row_class = ""
        if m_sharpe is not None and m_sharpe > 0.05:
            row_class = ' class="row-positive"'
        elif m_sharpe is not None and m_sharpe < -0.05:
            row_class = ' class="row-negative"'

        step_rows += f"""<tr{row_class}>
            <td>{step}</td><td><strong>{feat}</strong></td>
            <td>{sharpe:.4f}</td><td>{rank_ic:.4f}</td>
            <td>{m_sharpe_str}</td><td>{p_str}</td><td>{sig_badge}</td>
        </tr>\n"""

    # Build leaderboard rows
    lb_rows = ""
    for i, feat in enumerate(leaderboard, 1):
        ms = feat.get("marginal_sharpe", 0) or 0
        mi = feat.get("marginal_rank_ic", 0) or 0
        imp = (feat.get("feature_importance_pct", 0) or 0) * 100
        sig = "YES" if feat.get("is_significant") else "no"
        color = COLORS["success"] if ms > 0 else COLORS["danger"] if ms < 0 else COLORS["muted"]
        lb_rows += f"""<tr>
            <td>{i}</td><td><strong>{feat['feature_name']}</strong></td>
            <td style="color:{color}">{ms:+.4f}</td><td>{mi:+.4f}</td>
            <td>{imp:.1f}%</td><td>{sig}</td>
        </tr>\n"""

    # Guard violations
    guard_rows = ""
    for s in steps:
        m = s.get("metrics") or {}
        if m:
            violations = check_guard_metrics(m)
            for v in violations:
                guard_rows += f"""<tr>
                    <td>{s['step_number']}</td><td>{s['feature_added']}</td>
                    <td>{v['metric']}</td><td>{v['value']:.4f}</td>
                    <td>{v['threshold']}</td>
                </tr>\n"""

    guard_section = ""
    if guard_rows:
        guard_section = f"""
        <section class="card">
            <h2>Guard Metric Violations</h2>
            <p class="caption">Metrics exceeding safety thresholds. These indicate potential overfitting or excessive risk.</p>
            <div class="table-wrap">
            <table>
                <thead><tr><th>Step</th><th>Feature</th><th>Metric</th><th>Value</th><th>Threshold</th></tr></thead>
                <tbody>{guard_rows}</tbody>
            </table>
            </div>
        </section>
        """

    # Recommendations
    positive_feats = [f["feature_name"] for f in leaderboard
                      if (f.get("marginal_sharpe") or 0) > 0 and f.get("is_significant")]
    negative_feats = [f["feature_name"] for f in leaderboard
                      if (f.get("marginal_sharpe") or 0) < -0.05 and f.get("is_significant")]
    neutral_feats = [f["feature_name"] for f in leaderboard
                     if not f.get("is_significant") and f["feature_name"] not in positive_feats + negative_feats]

    rec_html = "<ul>"
    if positive_feats:
        rec_html += f'<li><strong style="color:{COLORS["success"]}">Keep:</strong> {", ".join(positive_feats)} — statistically significant positive contribution</li>'
    if negative_feats:
        rec_html += f'<li><strong style="color:{COLORS["danger"]}">Remove:</strong> {", ".join(negative_feats)} — statistically significant negative contribution</li>'
    if neutral_feats:
        rec_html += f'<li><strong style="color:{COLORS["muted"]}">Evaluate:</strong> {", ".join(neutral_feats)} — not statistically significant</li>'
    rec_html += "</ul>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Regression Report — {name}</title>
<script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after {{ box-sizing: border-box; }}
  body {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    background: {COLORS['bg']};
    color: {COLORS['dark']};
    margin: 0; padding: 0;
    line-height: 1.6;
  }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1.5rem; }}

  /* Header */
  header {{
    background: linear-gradient(135deg, {COLORS['dark']} 0%, #1a1a2e 100%);
    color: white; padding: 2.5rem 0;
  }}
  header .container {{ display: flex; justify-content: space-between; align-items: flex-end; flex-wrap: wrap; gap: 1rem; }}
  header h1 {{ font-size: 1.8rem; font-weight: 700; margin: 0; letter-spacing: -0.03em; }}
  header .subtitle {{ color: rgba(255,255,255,0.5); font-size: 0.85rem; margin-top: 0.3rem; letter-spacing: 0.05em; text-transform: uppercase; }}
  header .meta {{ text-align: right; color: rgba(255,255,255,0.6); font-size: 0.85rem; }}
  header .meta strong {{ color: white; }}

  /* KPI cards */
  .kpi-grid {{
    display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: 1rem; margin: -2rem 0 2rem;
    position: relative; z-index: 1;
  }}
  .kpi {{
    background: white; border-radius: 12px; padding: 1.25rem 1.5rem;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border-left: 4px solid {COLORS['border']};
  }}
  .kpi.highlight {{ border-left-color: {COLORS['primary']}; }}
  .kpi-label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.08em; color: {COLORS['muted']}; margin-bottom: 0.3rem; }}
  .kpi-value {{ font-size: 1.5rem; font-weight: 700; color: {COLORS['dark']}; }}
  .kpi-delta {{ font-size: 0.8rem; margin-top: 0.15rem; }}
  .kpi-delta.pos {{ color: {COLORS['success']}; }}
  .kpi-delta.neg {{ color: {COLORS['danger']}; }}

  /* Cards */
  .card {{
    background: white; border-radius: 12px; padding: 1.75rem 2rem;
    box-shadow: 0 1px 8px rgba(0,0,0,0.04);
    margin-bottom: 1.75rem;
  }}
  .card h2 {{
    font-size: 1.15rem; font-weight: 700; margin: 0 0 0.25rem;
    color: {COLORS['dark']}; letter-spacing: -0.02em;
  }}
  .card .caption {{
    font-size: 0.82rem; color: {COLORS['muted']}; margin: 0 0 1.25rem;
  }}

  /* Tables */
  .table-wrap {{ overflow-x: auto; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
  th {{
    text-align: left; padding: 0.6rem 0.75rem;
    border-bottom: 2px solid {COLORS['border']};
    font-weight: 600; color: {COLORS['muted']};
    font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.06em;
  }}
  td {{ padding: 0.55rem 0.75rem; border-bottom: 1px solid {COLORS['border']}; }}
  tr:hover td {{ background: {COLORS['bg']}; }}
  tr.row-positive td {{ background: rgba(16,185,129,0.04); }}
  tr.row-negative td {{ background: rgba(239,68,68,0.04); }}

  /* Badges */
  .badge {{
    display: inline-block; padding: 0.15rem 0.5rem; border-radius: 6px;
    font-size: 0.7rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
  }}
  .badge-sig {{ background: rgba(16,185,129,0.12); color: {COLORS['success']}; }}
  .badge-ns {{ background: rgba(122,111,115,0.1); color: {COLORS['muted']}; }}

  /* Recommendations */
  .rec-card {{
    background: linear-gradient(135deg, rgba(232,115,90,0.05), rgba(232,115,90,0.02));
    border: 1px solid rgba(232,115,90,0.15);
  }}
  .rec-card ul {{ margin: 0.5rem 0; padding-left: 1.5rem; }}
  .rec-card li {{ margin-bottom: 0.4rem; font-size: 0.9rem; }}

  /* Footer */
  footer {{
    text-align: center; padding: 2rem 0; color: {COLORS['muted']};
    font-size: 0.75rem; border-top: 1px solid {COLORS['border']};
    margin-top: 2rem;
  }}

  /* Two-column layout for charts */
  .chart-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 1.75rem;
  }}
  @media (max-width: 900px) {{
    .chart-grid {{ grid-template-columns: 1fr; }}
  }}
  .chart-grid .card {{ margin-bottom: 0; }}

  /* Plotly responsive */
  .js-plotly-plot {{ width: 100% !important; }}
</style>
</head>
<body>

<header>
  <div class="container">
    <div>
      <h1>{name}</h1>
      <div class="subtitle">Feature Regression Test Report</div>
    </div>
    <div class="meta">
      <div><strong>{regression_id}</strong></div>
      <div>{created} &nbsp;·&nbsp; {mins}m {secs}s</div>
    </div>
  </div>
</header>

<div class="container">

  <!-- KPI Cards -->
  <div class="kpi-grid">
    <div class="kpi">
      <div class="kpi-label">Baseline Sharpe</div>
      <div class="kpi-value">{b_sharpe:.3f}</div>
    </div>
    <div class="kpi highlight">
      <div class="kpi-label">Final Sharpe</div>
      <div class="kpi-value">{f_sharpe:.3f}</div>
      <div class="kpi-delta {'pos' if f_sharpe > b_sharpe else 'neg'}">{f_sharpe - b_sharpe:+.3f}</div>
    </div>
    <div class="kpi highlight">
      <div class="kpi-label">Peak Sharpe</div>
      <div class="kpi-value">{peak_sharpe:.3f}</div>
      <div class="kpi-delta pos">at +{peak_step}</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Baseline Rank IC</div>
      <div class="kpi-value">{b_ic:.3f}</div>
    </div>
    <div class="kpi highlight">
      <div class="kpi-label">Final Rank IC</div>
      <div class="kpi-value">{f_ic:.3f}</div>
      <div class="kpi-delta {'pos' if f_ic > b_ic else 'neg'}">{f_ic - b_ic:+.3f}</div>
    </div>
    <div class="kpi">
      <div class="kpi-label">Best Feature</div>
      <div class="kpi-value" style="font-size:1.15rem">{best_feat}</div>
      <div class="kpi-delta pos">{best_ms:+.3f} Sharpe</div>
    </div>
  </div>

  <!-- Cumulative Performance Chart -->
  <section class="card">
    <h2>Cumulative Performance</h2>
    <p class="caption">Sharpe Ratio and Rank IC progression as features are added sequentially. The peak marks the optimal stopping point.</p>
    {chart_cumulative}
  </section>

  <!-- Two-column charts -->
  <div class="chart-grid">
    <section class="card">
      <h2>Marginal Sharpe Contribution</h2>
      <p class="caption">Each feature's individual contribution to Sharpe ratio. Green = positive, Red = negative.</p>
      {chart_marginal}
    </section>
    <section class="card">
      <h2>Sharpe vs IC Tradeoff</h2>
      <p class="caption">Features plotted by marginal Sharpe vs marginal Rank IC. Bubble size = model importance.</p>
      {chart_scatter}
    </section>
  </div>

  <!-- Feature Importance -->
  <section class="card">
    <h2>Feature Importance Across Steps</h2>
    <p class="caption">How LightGBM allocates model capacity (gain-based importance) as features are added. Features consuming large capacity but hurting Sharpe indicate overfitting.</p>
    {chart_importance}
  </section>

  <!-- Guard Metrics -->
  <section class="card">
    <h2>Guard Metrics: Drawdown & Overfitting</h2>
    <p class="caption">Max drawdown (bars) and train/test Sharpe ratio (line) at each step. Dotted lines show safety thresholds. Ratios above 2.5x suggest overfitting.</p>
    {chart_guard}
  </section>

  <!-- Step-by-Step Table -->
  <section class="card">
    <h2>Step-by-Step Results</h2>
    <p class="caption">Detailed metrics at each feature addition step. Green rows improved Sharpe by &gt;0.05, red rows worsened it.</p>
    <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Step</th><th>Feature</th><th>Sharpe</th><th>Rank IC</th><th>Δ Sharpe</th><th>p-value</th><th>Sig?</th></tr>
      </thead>
      <tbody>{step_rows}</tbody>
    </table>
    </div>
  </section>

  <!-- Leaderboard -->
  <section class="card">
    <h2>Feature Contribution Leaderboard</h2>
    <p class="caption">Features ranked by marginal Sharpe contribution. Importance % shows how much model capacity each feature consumes.</p>
    <div class="table-wrap">
    <table>
      <thead>
        <tr><th>Rank</th><th>Feature</th><th>Marginal Sharpe</th><th>Marginal IC</th><th>Importance</th><th>Significant?</th></tr>
      </thead>
      <tbody>{lb_rows}</tbody>
    </table>
    </div>
  </section>

  <!-- Guard Violations -->
  {guard_section}

  <!-- Recommendations -->
  <section class="card rec-card">
    <h2>Recommendations</h2>
    <p class="caption">Based on statistical significance tests and marginal contribution analysis.</p>
    {rec_html}
  </section>

</div>

<footer>
  Generated {datetime.now().strftime('%Y-%m-%d %H:%M')} &nbsp;·&nbsp; QuantaAlpha Regression Testing Framework
</footer>

</body>
</html>"""

    return html


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Generate a single-page HTML report for a regression test run.",
    )
    parser.add_argument("regression_id", nargs="?", help="Regression test ID")
    parser.add_argument("-o", "--output", help="Output HTML path (default: output/regression/<id>/report.html)")
    parser.add_argument("--open", action="store_true", help="Open report in browser after generating")
    parser.add_argument("--list", action="store_true", help="List available regression tests")
    parser.add_argument("--db", default="data/runs.db", help="Database path")
    args = parser.parse_args()

    db = RegressionDatabase(db_path=args.db)

    if args.list:
        tests = db.list_regression_tests()
        if not tests:
            print("No regression tests found.")
            return
        print(f"\n{'ID':<45} {'Name':<30} {'Status':<12} {'Sharpe':<10} {'Date'}")
        print("-" * 110)
        for t in tests:
            rid = t.get("regression_id", "")
            name = t.get("name", "")[:28]
            status = t.get("status", "")
            sharpe = t.get("final_sharpe")
            sharpe_str = f"{sharpe:.4f}" if sharpe is not None else "N/A"
            date = (t.get("created_at") or "")[:19]
            print(f"{rid:<45} {name:<30} {status:<12} {sharpe_str:<10} {date}")
        return

    if not args.regression_id:
        # Default to most recent completed test
        tests = db.list_regression_tests()
        completed = [t for t in tests if t.get("status") == "completed"]
        if not completed:
            print("No completed regression tests. Use --list to see all tests.")
            sys.exit(1)
        args.regression_id = completed[0]["regression_id"]
        print(f"Using most recent: {args.regression_id}")

    # Load data
    data = load_regression_data(db, args.regression_id)

    # Determine output path
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output") / "regression" / args.regression_id / "report.html"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Generate report
    html = build_html_report(data)
    output_path.write_text(html, encoding="utf-8")
    print(f"Report generated: {output_path}")
    print(f"  Size: {output_path.stat().st_size / 1024:.0f} KB")

    # Also copy to results folder
    results_dir = Path("output") / "results"
    test_name = data["test"].get("name", "").replace(" ", "_").lower()
    date_prefix = (data["test"].get("created_at") or "")[:10].replace("-", "")
    results_folder = results_dir / f"{args.regression_id}"
    results_folder.mkdir(parents=True, exist_ok=True)

    results_report = results_folder / "report.html"
    results_report.write_text(html, encoding="utf-8")
    print(f"  Also saved to: {results_report}")

    if args.open:
        webbrowser.open(f"file://{output_path.resolve()}")


if __name__ == "__main__":
    main()
