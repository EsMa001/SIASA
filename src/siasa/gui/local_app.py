from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote

from siasa.catalog import load_country_set
from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.validation_backtest import build_historical_replay_summary
from siasa.traceability.consistency import build_repo_closure_report


SitePayload = dict[str, Any]
_UI_ROLES = {'viewer', 'analyst', 'admin'}


@dataclass(frozen=True)
class SiteBuildResult:
    output_dir: Path
    generated_files: list[Path]


def _page(title: str, body: str, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    available_pages = available_pages or set()
    nav_entries = [
        ('index.html', '🌍 Overview'),
        ('coverage.html', '📡 Coverage'),
        ('trends.html', '📈 Trends'),
        ('events.html', '⚡ Events'),
        ('comparison.html', '🔀 Comparison'),
        ('validation.html', '✅ Validation'),
        ('traceability.html', '🔗 Traceability'),
        ('annotations.html', '📝 Annotations'),
        ('reports.html', '📄 Reports'),
        ('runs.html', '⚙ System'),
        ('readiness.html', '🚦 Readiness'),
    ]
    nav_html = ''.join(
        f"<a href='{html.escape(nav_prefix + href)}'>{html.escape(label)}</a>"
        for href, label in nav_entries
        if href in available_pages
    )
    # Google Fonts: Inter (narrative) + Space Grotesk (machine-data labels)
    font_link = (
        "<link rel='preconnect' href='https://fonts.googleapis.com'>"
        "<link rel='preconnect' href='https://fonts.gstatic.com' crossorigin>"
        "<link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&amp;"
        "family=Space+Grotesk:wght@400;500;600;700&display=swap' rel='stylesheet'>"
    )
    css = (
        # === Reset & Base ===
        "*{box-sizing:border-box;margin:0;padding:0;}"
        # Surface depth stack (AEGIS-inspired, no shadows — depth via color only):
        # #060e20 lowest → #0b1326 base → #131b2e container-low → #171f33 container
        # → #222a3d container-high → #2d3449 container-highest
        "body{font-family:'Inter',-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;"
        "background:#0b1326;color:#dae2fd;font-size:14px;line-height:1.5;min-height:100vh;}"
        # Data / machine-text font — IDs, codes, timestamps, labels
        ".mono,code,pre,th,.kpi-label,.badge,figcaption,"
        ".panel-header{font-family:'Space Grotesk','Cascadia Code','Fira Code',monospace;}"
        # === Navigation (topbar) ===
        "nav{position:sticky;top:0;z-index:100;"
        "background:rgba(11,19,38,.85);backdrop-filter:blur(16px);"
        "-webkit-backdrop-filter:blur(16px);"
        "border-bottom:1px solid rgba(78,222,163,.08);"
        "padding:0 24px;height:52px;display:flex;align-items:center;gap:2px;overflow-x:auto;}"
        # Brand mark left
        "nav::before{content:'SIASA';font-family:'Space Grotesk',monospace;"
        "font-size:11px;font-weight:700;letter-spacing:.18em;color:#4edea3;"
        "margin-right:20px;white-space:nowrap;}"
        "nav a{color:#8b9ab8;text-decoration:none;font-size:12px;font-weight:500;"
        "font-family:'Space Grotesk',monospace;letter-spacing:.04em;"
        "padding:5px 11px;border-radius:2px;white-space:nowrap;"
        "transition:color .15s,background .15s;border:1px solid transparent;}"
        "nav a:hover{color:#dae2fd;background:#171f33;border-color:rgba(78,222,163,.15);}"
        # === Page wrapper ===
        ".page-content{padding:28px 32px;max-width:1600px;margin:0 auto;}"
        # === Headings ===
        "h1{font-size:1.3rem;font-weight:700;color:#dae2fd;margin-bottom:24px;"
        "padding-bottom:14px;border-bottom:1px solid rgba(78,222,163,.12);"
        "display:flex;align-items:center;gap:10px;}"
        # HUD accent bar on h1
        "h1::before{content:'';display:inline-block;width:3px;height:1.1em;"
        "background:#4edea3;border-radius:1px;flex-shrink:0;}"
        "h2{font-size:1rem;font-weight:600;color:#b9c7e0;margin:24px 0 12px;}"
        "h3{font-size:0.75rem;font-weight:700;color:#6b7d99;text-transform:uppercase;"
        "letter-spacing:.1em;margin:16px 0 8px;font-family:'Space Grotesk',monospace;}"
        "h4{font-size:0.75rem;font-weight:600;color:#6b7d99;margin:12px 0 6px;}"
        # === Panels — HUD corner marker via ::before ===
        ".panel{background:#131b2e;border:1px solid rgba(78,222,163,.1);"
        "border-radius:2px;padding:16px;margin-bottom:16px;position:relative;}"
        ".panel::before{content:'';position:absolute;top:0;left:0;"
        "width:16px;height:2px;background:#4edea3;border-radius:0;}"
        ".panel-header{font-size:0.7rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.1em;color:#6b7d99;margin-bottom:12px;padding-bottom:8px;"
        "border-bottom:1px solid rgba(78,222,163,.08);}"
        # === KPI grid ===
        ".kpi-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));"
        "gap:12px;margin-bottom:24px;}"
        ".kpi-card{background:#131b2e;border:1px solid rgba(78,222,163,.1);"
        "border-radius:2px;padding:16px;position:relative;}"
        ".kpi-card::before{content:'';position:absolute;top:0;left:0;"
        "width:16px;height:2px;background:#4edea3;}"
        ".kpi-label{font-size:0.65rem;font-weight:700;text-transform:uppercase;"
        "letter-spacing:.12em;color:#6b7d99;margin-bottom:6px;display:block;}"
        ".kpi-value{font-size:1.6rem;font-weight:700;color:#dae2fd;line-height:1.1;"
        "font-family:'Inter',sans-serif;}"
        ".kpi-sub{font-size:0.7rem;color:#6b7d99;margin-top:5px;}"
        # === Tables ===
        "table{border-collapse:collapse;width:100%;margin:8px 0;}"
        "thead th{background:#0f1828;color:#6b7d99;font-size:10px;font-weight:700;"
        "text-transform:uppercase;letter-spacing:.1em;padding:8px 12px;"
        "border-bottom:1px solid rgba(78,222,163,.15);text-align:left;white-space:nowrap;}"
        "tbody td{padding:8px 12px;border-bottom:1px solid rgba(255,255,255,.04);"
        "font-size:13px;color:#dae2fd;vertical-align:top;}"
        "tbody tr:hover td{background:#171f33;}"
        "th,td{text-align:left;}"
        ".table-container{overflow-x:auto;border:1px solid rgba(78,222,163,.1);"
        "border-radius:2px;}"
        # === Code & Pre ===
        "code{background:#0f1828;color:#4edea3;padding:2px 7px;border-radius:2px;"
        "font-size:12px;border:1px solid rgba(78,222,163,.2);}"
        "pre{background:#0f1828;color:#4edea3;padding:16px;border-radius:2px;overflow-x:auto;"
        "font-size:12px;border:1px solid rgba(78,222,163,.15);line-height:1.7;}"
        # === Status & Badges ===
        ".status{font-weight:700;font-family:'Space Grotesk',monospace;}"
        ".badge{display:inline-block;padding:2px 7px;border-radius:2px;font-size:10px;"
        "font-weight:700;border:1px solid;line-height:1.7;white-space:nowrap;"
        "letter-spacing:.05em;text-transform:uppercase;}"
        ".badge-red{color:#ffb4ab;border-color:rgba(255,180,171,.3);background:rgba(255,180,171,.08);}"
        ".badge-orange{color:#ffb347;border-color:rgba(255,179,71,.3);background:rgba(255,179,71,.08);}"
        ".badge-amber{color:#e3b341;border-color:rgba(227,179,65,.3);background:rgba(227,179,65,.08);}"
        ".badge-green{color:#4edea3;border-color:rgba(78,222,163,.3);background:rgba(78,222,163,.08);}"
        ".badge-blue{color:#8ed0ff;border-color:rgba(142,208,255,.3);background:rgba(142,208,255,.08);}"
        ".badge-gray{color:#6b7d99;border-color:rgba(107,125,153,.3);background:rgba(107,125,153,.08);}"
        # === Uncertainty badges ===
        ".uncertainty-badge{display:inline-block;margin:2px 4px 2px 0;padding:2px 8px;"
        "border-radius:2px;background:rgba(255,180,171,.08);color:#ffb4ab;"
        "border:1px solid rgba(255,180,171,.25);font-size:10px;font-weight:600;"
        "font-family:'Space Grotesk',monospace;text-transform:uppercase;letter-spacing:.05em;}"
        ".uncertainty-none{background:rgba(107,125,153,.08);color:#6b7d99;"
        "border:1px solid rgba(107,125,153,.2);}"
        # === Metric meter ===
        ".metric-meter{margin:12px 0;max-width:320px;}"
        ".metric-meter-header{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:6px;}"
        ".metric-meter-label{font-size:11px;color:#6b7d99;font-weight:600;text-transform:uppercase;letter-spacing:.06em;}"
        ".metric-meter-value{font-size:13px;font-weight:700;font-family:'Space Grotesk',monospace;}"
        ".metric-meter-band{font-size:10px;font-weight:400;color:#6b7d99;}"
        # === Charts ===
        ".chart-figure{margin:16px 0;}"
        ".chart-label{font-size:11px;color:#6b7d99;margin-bottom:8px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:.06em;display:block;}"
        ".chart-empty{font-size:12px;color:#6b7d99;padding:16px;background:#1c2740;"
        "border-radius:6px;border:1px solid rgba(78,222,163,.1);}"
        # === Lists ===
        "ul,ol{padding-left:18px;margin:6px 0;}"
        "li{margin:3px 0;color:#b9c7e0;font-size:13px;}"
        # === Links ===
        "a{color:#4edea3;text-decoration:none;}"
        "a:hover{color:#6ffbbe;text-decoration:underline;}"
        # === Figures / charts ===
        "figure{margin:12px 0;}"
        "figcaption{font-size:11px;color:#6b7d99;margin-bottom:6px;font-weight:600;"
        "text-transform:uppercase;letter-spacing:.08em;}"
        # === Misc ===
        "hr{border:none;border-top:1px solid rgba(78,222,163,.08);margin:16px 0;}"
        "p{color:#b9c7e0;font-size:13px;margin:6px 0;}"
        "strong{color:#dae2fd;font-weight:600;}"
        "details{margin:8px 0;}"
        "summary{cursor:pointer;color:#4edea3;font-size:13px;font-weight:600;"
        "font-family:'Space Grotesk',monospace;padding:4px 0;letter-spacing:.03em;}"
        "summary:hover{color:#6ffbbe;}"
        # === Scrollbar (thin, dark) ===
        "::-webkit-scrollbar{width:4px;height:4px;}"
        "::-webkit-scrollbar-track{background:#0b1326;}"
        "::-webkit-scrollbar-thumb{background:#2d3449;border-radius:2px;}"
        "::-webkit-scrollbar-thumb:hover{background:#4edea3;}"
        # === Form Controls ===
        "label{font-size:11px;font-weight:600;color:#6b7d99;text-transform:uppercase;"
        "letter-spacing:.08em;margin-right:4px;font-family:'Space Grotesk',monospace;}"
        "select,input[type='text'],textarea{"
        "background:#0f1828;color:#dae2fd;border:1px solid rgba(78,222,163,.2);"
        "border-radius:2px;padding:5px 10px;font-size:12px;font-family:'Space Grotesk',monospace;"
        "outline:none;transition:border-color .15s;margin-right:12px;margin-bottom:6px;}"
        "select:focus,input[type='text']:focus,textarea:focus{"
        "border-color:rgba(78,222,163,.6);box-shadow:0 0 0 2px rgba(78,222,163,.08);}"
        "select option{background:#0f1828;color:#dae2fd;}"
        "button,input[type='submit']{"
        "background:rgba(78,222,163,.1);color:#4edea3;border:1px solid rgba(78,222,163,.3);"
        "border-radius:2px;padding:5px 14px;font-size:11px;font-weight:700;"
        "font-family:'Space Grotesk',monospace;text-transform:uppercase;letter-spacing:.06em;"
        "cursor:pointer;transition:background .15s,border-color .15s;}"
        "button:hover,input[type='submit']:hover{"
        "background:rgba(78,222,163,.18);border-color:rgba(78,222,163,.6);}"
        # === Controls bar ===
        ".controls-bar{display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:12px 0 4px;}"
    )
    return (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>SIASA — {html.escape(title)}</title>"
        f"{font_link}"
        f"<style>{css}</style>"
        "</head><body>"
        f"<nav>{nav_html}</nav>"
        "<div class='page-content'>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</div>"
        "</body></html>"
    )


def _json_block(data: Any) -> str:
    return f"<pre>{html.escape(json.dumps(data, indent=2, sort_keys=True))}</pre>"



def _coerce_chart_points(series: list[Any], *, label_key: str) -> list[tuple[str, float]]:
    points: list[tuple[str, float]] = []
    for index, item in enumerate(series, start=1):
        if isinstance(item, dict):
            value = item.get('value')
            label = item.get(label_key) or item.get('label') or index
            if isinstance(value, (int, float)):
                points.append((str(label), float(value)))
            continue
        if isinstance(item, (int, float)):
            points.append((str(index), float(item)))
    return points



def _trend_labels(series: list[Any], *, label_key: str) -> list[str]:
    labels: list[str] = []
    for index, item in enumerate(series, start=1):
        if isinstance(item, dict):
            label = item.get(label_key) or item.get('label')
            if label is not None:
                labels.append(str(label))
            continue
        if isinstance(item, str):
            labels.append(item)
            continue
        if isinstance(item, (int, float)):
            labels.append(str(index))
    return labels



def _render_line_chart(series: list[Any], *, label_key: str, chart_label: str) -> str:
    points = _coerce_chart_points(series, label_key=label_key)
    if not points:
        return "<div class='chart-empty'>No chartable data available.</div>"

    width = 560
    height = 180
    pad_left = 52    # room for Y-axis labels
    pad_right = 16
    pad_top = 16
    pad_bottom = 36  # room for X-axis labels

    values = [v for _, v in points]
    min_value = min(values)
    max_value = max(values)
    value_range = max_value - min_value

    uw = max(width - pad_left - pad_right, 1)
    uh = max(height - pad_top - pad_bottom, 1)

    def to_xy(index: int, value: float) -> tuple[float, float]:
        x = pad_left if len(points) == 1 else pad_left + uw * index / (len(points) - 1)
        y = pad_top + uh / 2 if value_range == 0 else pad_top + ((max_value - value) / value_range) * uh
        return x, y

    # --- grid lines (4 horizontal) ---
    grid_lines: list[str] = []
    y_labels: list[str] = []
    steps = 4
    for i in range(steps + 1):
        gv = min_value + value_range * i / steps if value_range else min_value
        gy = pad_top + uh * (1 - i / steps)
        grid_lines.append(
            f"<line x1='{pad_left}' y1='{gy:.1f}' x2='{width - pad_right}' y2='{gy:.1f}' "
            f"stroke='rgba(78,222,163,.10)' stroke-width='1' stroke-dasharray='4 3'/>"
        )
        y_labels.append(
            f"<text x='{pad_left - 6}' y='{gy + 4:.1f}' text-anchor='end' "
            f"font-size='9' fill='#4a6480' font-family='Space Grotesk,monospace'>{gv:.1f}</text>"
        )

    # --- area fill ---
    coords: list[str] = []
    circles: list[str] = []
    x_labels: list[str] = []
    for i, (lbl, val) in enumerate(points):
        x, y = to_xy(i, val)
        coords.append(f"{x:.1f},{y:.1f}")
        circles.append(
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='#0b1326' stroke='#4edea3' stroke-width='1.5'>"
            f"<title>{html.escape(lbl)}: {val:.2f}</title></circle>"
        )
        # x-axis label (every point, rotated if many)
        anchor = 'middle' if len(points) <= 6 else 'end'
        rotate = '' if len(points) <= 6 else f" transform='rotate(-35,{x:.1f},{height - pad_bottom + 14})'"
        x_labels.append(
            f"<text x='{x:.1f}' y='{height - pad_bottom + 14}' text-anchor='{anchor}'"
            f" font-size='9' fill='#4a6480' font-family='Space Grotesk,monospace'{rotate}>"
            f"{html.escape(lbl[:10])}</text>"
        )

    # area polygon (line + bottom fill)
    bx0, _ = to_xy(0, values[0])
    bxN, _ = to_xy(len(points) - 1, values[-1])
    area_points = (
        f"{bx0:.1f},{height - pad_bottom} "
        + ' '.join(coords)
        + f" {bxN:.1f},{height - pad_bottom}"
    )

    return (
        f"<figure class='chart-figure'>"
        f"<figcaption class='chart-label'>{html.escape(chart_label)}</figcaption>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' style='max-width:{width}px;' "
        f"role='img' aria-label='{html.escape(chart_label)}' "
        f"style='display:block;background:#0b1326;border-radius:6px;border:1px solid rgba(78,222,163,.15);'>"
        # grid
        + ''.join(grid_lines)
        # axes
        + f"<line x1='{pad_left}' y1='{pad_top}' x2='{pad_left}' y2='{height - pad_bottom}' stroke='rgba(78,222,163,.25)' stroke-width='1'/>"
        + f"<line x1='{pad_left}' y1='{height - pad_bottom}' x2='{width - pad_right}' y2='{height - pad_bottom}' stroke='rgba(78,222,163,.25)' stroke-width='1'/>"
        # area
        + f"<polygon points='{area_points}' fill='rgba(78,222,163,.07)'/>"
        # line
        + f"<polyline fill='none' stroke='#4edea3' stroke-width='2' stroke-linejoin='round' points='{' '.join(coords)}'/>"
        # dots
        + ''.join(circles)
        # labels
        + ''.join(y_labels)
        + ''.join(x_labels)
        + "</svg></figure>"
    )



def _delta_band(value: Any) -> str:
    if not isinstance(value, (int, float)):
        return 'unknown'
    numeric = float(value)
    if numeric >= 0.25:
        return 'strong increase'
    if numeric >= 0.05:
        return 'increase'
    if numeric > -0.05:
        return 'stable'
    if numeric > -0.25:
        return 'decrease'
    return 'strong decrease'



def _render_historical_comparison_summary(series: list[Any], *, label_key: str) -> str:
    points = _coerce_chart_points(series, label_key=label_key)
    if not points:
        return "<p>No historical comparison summary available.</p>"

    first_label, first_value = points[0]
    last_label, last_value = points[-1]
    peak_label, peak_value = max(points, key=lambda item: item[1])
    trough_label, trough_value = min(points, key=lambda item: item[1])
    net_change = last_value - first_value
    return (
        "<h4>Historical Comparison Summary</h4>"
        "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Current vs First Label</td><td>{html.escape(last_label)} vs {html.escape(first_label)}</td></tr>"
        f"<tr><td>Net Change</td><td>{net_change:.2f}</td></tr>"
        f"<tr><td>Peak Label</td><td>{html.escape(peak_label)}</td></tr>"
        f"<tr><td>Peak Value</td><td>{peak_value:.2f}</td></tr>"
        f"<tr><td>Lowest Label</td><td>{html.escape(trough_label)}</td></tr>"
        f"<tr><td>Lowest Value</td><td>{trough_value:.2f}</td></tr>"
        f"<tr><td>Observation Count</td><td>{len(points)}</td></tr>"
        "</tbody></table>"
    )



def _render_baseline_comparison_summary(baseline_comparison: dict[str, Any], time_series: list[Any]) -> str:
    current_window = baseline_comparison.get('current_window')
    baseline_30d = baseline_comparison.get('baseline_30d')
    delta_to_baseline = baseline_comparison.get('delta_to_baseline')
    return (
        "<h3>Comparison vs Baseline</h3>"
        "<table><thead><tr><th>Metric</th><th>Value</th></tr></thead><tbody>"
        f"<tr><td>Current Window</td><td>{html.escape(str(current_window))}</td></tr>"
        f"<tr><td>30d Baseline</td><td>{html.escape(str(baseline_30d))}</td></tr>"
        f"<tr><td>Delta to Baseline</td><td>{html.escape(str(delta_to_baseline))}</td></tr>"
        f"<tr><td>Baseline Delta Band</td><td>{html.escape(_delta_band(delta_to_baseline))}</td></tr>"
        "</tbody></table>"
        "<h3>Historical Window Context</h3>"
        f"{_render_historical_comparison_summary(time_series, label_key='timestamp')}"
    )



def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))



def _country_metadata_lookup() -> dict[str, dict[str, str]]:
    repo_root = Path(__file__).resolve().parents[3]
    country_set_path = repo_root / 'vmodel' / 'project' / 'mvp_countries.yaml'
    lookup: dict[str, dict[str, str]] = {}
    for record in load_country_set(country_set_path):
        lookup[record.iso3] = {
            'country_name': record.country_name,
            'priority': record.priority,
            'selection_type': record.selection_type,
            'region': record.region,
            'rationale': record.rationale,
        }
    return lookup



def _region_anchor(region: str) -> tuple[float, float]:
    normalized = region.lower()
    if 'europe' in normalized:
        return (180.0, 70.0)
    if 'middle east' in normalized:
        return (205.0, 120.0)
    if 'asia' in normalized:
        return (255.0, 90.0)
    if 'africa' in normalized:
        return (185.0, 155.0)
    if 'north america' in normalized:
        return (75.0, 85.0)
    if 'oceania' in normalized or 'indo-pacific' in normalized:
        return (290.0, 170.0)
    return (155.0, 115.0)



def _status_color(status: str) -> str:
    # AEGIS-inspired escalation scale:
    # S0-S1 = grey (no data / unvalidated)
    # S2 = amber (low confidence)
    # S3 = gold (moderate signal)
    # S4 = orange (meaningful signal)
    # S5 = salmon-red (strong signal / alert)
    # S6 = bright red (confirmed / critical)
    # Emerald (#4edea3) reserved for nominal/stable status indicators
    return {
        'S0': '#6b7d99',   # grey — unknown / no data
        'S1': '#8b9ab8',   # light grey — data present, unvalidated
        'S2': '#e3b341',   # amber — low confidence
        'S3': '#ffb347',   # gold/orange — moderate signal
        'S4': '#e3602b',   # orange — meaningful signal
        'S5': '#ffb4ab',   # salmon — strong signal / alert
        'S6': '#ff6b6b',   # bright red — confirmed / critical
    }.get(status, '#6b7d99')



def _coerce_ratio(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return max(0.0, min(float(value), 1.0))
    return None



def _ratio_band(value: Any) -> str:
    ratio = _coerce_ratio(value)
    if ratio is None:
        return 'unknown'
    if ratio >= 0.8:
        return 'high'
    if ratio >= 0.5:
        return 'medium'
    return 'low'



def _band_color(band: str) -> str:
    return {
        'high':    '#3fb950',   # green — good coverage / stable
        'medium':  '#d29922',   # amber — partial
        'low':     '#f85149',   # red — weak / critical gap
        'unknown': '#6e7681',   # grey — no data
    }.get(band, '#6e7681')



def _freshness_band(value: Any) -> str:
    if value is None:
        return 'unknown'
    if isinstance(value, bool):
        return 'unknown'
    if isinstance(value, (int, float)):
        if float(value) <= 24.0:
            return 'fresh'
        if float(value) <= 168.0:
            return 'aging'
        return 'stale'
    return 'unknown'



def _freshness_band_color(band: str) -> str:
    return {
        'fresh':   '#3fb950',   # green
        'aging':   '#d29922',   # amber
        'stale':   '#f85149',   # red
        'unknown': '#6e7681',   # grey
    }.get(band, '#6e7681')


def _run_status_color(status: str) -> str:
    """Color for system run_status values."""
    s = status.lower()
    if s in ('ok', 'success', 'complete', 'completed', 'done'):
        return '#4edea3'   # emerald — nominal
    if s in ('running', 'in_progress', 'pending'):
        return '#8ed0ff'   # blue — active
    if s in ('warning', 'partial', 'degraded'):
        return '#e3b341'   # amber — warning
    if s in ('error', 'failed', 'failure', 'critical'):
        return '#ffb4ab'   # salmon — error
    return '#6b7d99'       # grey — unknown



def _format_freshness(value: Any) -> str:
    band = _freshness_band(value)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return band
    hours = int(value) if float(value).is_integer() else round(float(value), 1)
    return f'{band} ({hours}h)'



def _render_metric_meter(label: str, value: Any, *, fill_color: str) -> str:
    ratio = _coerce_ratio(value)
    band = _ratio_band(value)
    percent = int(round((ratio or 0.0) * 100))
    value_label = 'N/A' if ratio is None else f'{ratio:.2f}'
    width = 300
    height = 28
    fill_width = int(round((ratio or 0.0) * width))
    # band label color
    band_color = {'high': '#4edea3', 'medium': '#d29922', 'low': '#f85149', 'unknown': '#6e7681'}.get(band, '#6e7681')
    return (
        f"<div class='metric-meter'>"
        f"<div class='metric-meter-header'>"
        f"<span class='metric-meter-label'>{html.escape(label)}</span>"
        f"<span class='metric-meter-value' style='color:{band_color};'>{html.escape(value_label)}"
        f" <span class='metric-meter-band'>({html.escape(band)})</span></span>"
        f"</div>"
        f"<svg viewBox='0 0 {width} {height}' width='100%' style='max-width:{width}px;display:block;' "
        f"role='img' aria-label='{html.escape(label)} meter'>"
        f"<rect x='0' y='0' width='{width}' height='{height}' rx='4' fill='#1c2740'></rect>"
        f"<rect x='0' y='0' width='{fill_width}' height='{height}' rx='4' fill='{html.escape(fill_color)}' opacity='0.85'></rect>"
        f"<rect x='0' y='0' width='{width}' height='{height}' rx='4' fill='none' stroke='rgba(78,222,163,.15)' stroke-width='1'></rect>"
        f"<text x='{width // 2}' y='19' text-anchor='middle' font-size='11' font-weight='600' "
        f"fill='#dae2fd' font-family='Space Grotesk,monospace'>{percent}%</text>"
        f"</svg>"
        f"</div>"
    )



def _render_uncertainty_badges(items: list[Any]) -> str:
    labels = [str(item) for item in items if str(item)]
    if not labels:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        f"<span class='uncertainty-badge'>{html.escape(label)}</span>"
        for label in labels
    )



def _source_depth_band(source_count: Any) -> str:
    try:
        count = int(source_count)
    except (TypeError, ValueError):
        count = 0
    if count <= 1:
        return 'minimal'
    if count <= 3:
        return 'moderate'
    return 'deep'



def _render_missing_domain_badges(items: list[Any]) -> str:
    labels = [str(item) for item in items if str(item)]
    if not labels:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        f"<span class='uncertainty-badge'>missing:{html.escape(label)}</span>"
        for label in labels
    )



def _source_anchor_id(source_id: str) -> str:
    return f"source-{source_id}"



def _render_gap_details(gap_details: list[dict[str, Any]], *, coverage_href_prefix: str = 'coverage.html') -> str:
    if not gap_details:
        return "<span class='uncertainty-badge uncertainty-none'>none</span>"
    return ''.join(
        "<div class='gap-detail'>"
        f"<strong>{html.escape(str(detail.get('domain', 'UNKNOWN')))}</strong>: "
        f"{html.escape(str(detail.get('reason', 'unknown')))}"
        f" | sources={''.join(_render_gap_source_link(source_id, coverage_href_prefix) for source_id in detail.get('source_ids', [])) or 'none'}"
        f"{_render_gap_diagnostics(detail.get('diagnostics_by_source', {}))}"
        f"{_render_source_reason_details(list(detail.get('source_reason_details', [])))}"
        "</div>"
        for detail in gap_details
    )



def _render_gap_source_link(source_id: Any, coverage_href_prefix: str) -> str:
    source_label = str(source_id)
    href = f"{coverage_href_prefix}#{_source_anchor_id(source_label)}"
    return f"<a href='{html.escape(href)}'>{html.escape(source_label)}</a> "



def _render_gap_diagnostics(diagnostics_by_source: dict[str, Any]) -> str:
    if not diagnostics_by_source:
        return ''
    diagnostics = '; '.join(
        f"{source_id}: {diagnostic}"
        for source_id, diagnostic in diagnostics_by_source.items()
    )
    return f" | diagnostics={html.escape(diagnostics)}"



def _render_source_reason_details(source_reason_details: list[dict[str, Any]]) -> str:
    if not source_reason_details:
        return ''
    parts = []
    for detail in source_reason_details:
        source_id = html.escape(str(detail.get('source_id', 'UNKNOWN')))
        reason = html.escape(str(detail.get('reason', 'unknown')))
        diagnostics = html.escape(str(detail.get('diagnostics', '')))
        action_category = html.escape(str(detail.get('action_category', 'unknown')))
        severity = html.escape(str(detail.get('severity', 'low')))
        suffix = f" ({diagnostics})" if diagnostics else ''
        parts.append(f"{source_id}: {reason} | action={action_category} | severity={severity}{suffix}")
    return f" | source_causes={'; '.join(parts)}"



def _country_coverage_visibility_rows(system_status_read_model: dict[str, Any]) -> dict[str, Any]:
    visibility = system_status_read_model.get('country_coverage_visibility', {})
    if not isinstance(visibility, dict):
        return {
        'priority_summary': [],
        'source_depth_band_summary': [],
        'freshness_band_summary': [],
        'country_freshness_rows': [],
        'country_gap_rows': [],
        'missing_domain_totals': {},
        'remediation_watchlist': [],
        'stale_priority_summary': {},
        'stale_priority_watchlist': [],
    }
    return {
        'priority_summary': list(visibility.get('priority_summary', [])),
        'source_depth_band_summary': list(visibility.get('source_depth_band_summary', [])),
        'freshness_band_summary': list(visibility.get('freshness_band_summary', [])),
        'country_freshness_rows': list(visibility.get('country_freshness_rows', [])),
        'country_gap_rows': list(visibility.get('country_gap_rows', [])),
        'missing_domain_totals': dict(visibility.get('missing_domain_totals', {})),
        'remediation_watchlist': list(visibility.get('remediation_watchlist', [])),
        'stale_priority_summary': dict(visibility.get('stale_priority_summary', {})),
        'stale_priority_watchlist': list(visibility.get('stale_priority_watchlist', [])),
    }



def _render_remediation_watchlist(visibility: dict[str, Any]) -> str:
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('priority_rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority_score', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('action_category', 'unknown')))}</td>"
        f"<td>severity={html.escape(str(row.get('severity', 'low')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('source_ids', [])) or 'none')}</td>"
        f"<td>{html.escape(str(row.get('suggested_next_action', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('owner_hint', 'n/a')))}</td>"
        f"<td>{_render_watchlist_evidence_link(str(row.get('evidence_link', '')))}</td>"
        "</tr>"
        for row in visibility.get('remediation_watchlist', [])
    ) or "<tr><td colspan='11'>No remediation priorities recorded.</td></tr>"
    return (
        "<h3>Remediation Watchlist</h3>"
        "<p>Aggregated action categories highlight which operational problem classes should be addressed first.</p>"
        "<table><thead><tr><th>Priority Rank</th><th>Priority Score</th><th>Action Category</th><th>Severity</th><th>Countries</th><th>Sources</th><th>Country IDs</th><th>Source IDs</th><th>Suggested Next Action</th><th>Owner Hint</th><th>Evidence</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )



def _render_watchlist_evidence_link(evidence_link: str) -> str:
    if not evidence_link:
        return 'n/a'
    if not _is_safe_internal_evidence_link(evidence_link):
        return 'invalid evidence link'
    escaped = html.escape(evidence_link)
    return f"<a href='{escaped}'>{escaped}</a>"



def _is_safe_internal_evidence_link(evidence_link: str) -> bool:
    return bool(re.fullmatch(r"coverage\.html(?:#source-[A-Za-z0-9_.-]+)?", evidence_link))



def _render_stale_priority_watchlist(visibility: dict[str, Any]) -> str:
    summary = visibility.get('stale_priority_summary', {})
    stale_count = int(summary.get('stale_country_count', 0)) if isinstance(summary, dict) else 0
    p1_count = int(summary.get('p1_stale_count', 0)) if isinstance(summary, dict) else 0
    p2_count = int(summary.get('p2_stale_count', 0)) if isinstance(summary, dict) else 0
    p3_count = int(summary.get('p3_stale_count', 0)) if isinstance(summary, dict) else 0
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('priority_rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_id', 'unknown')))}</td>"
        f"<td>{html.escape(str(row.get('priority', 'unassigned')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'minimal')))}</td>"
        "</tr>"
        for row in visibility.get('stale_priority_watchlist', [])
    ) or "<tr><td colspan='5'>No stale-country remediation priorities recorded.</td></tr>"
    return (
        "<h3>Stale Coverage Priority Queue</h3>"
        f"<p>Stale countries: {stale_count} | P1={p1_count}, P2={p2_count}, P3={p3_count}. Prioritized by stakeholder priority then staleness.</p>"
        "<table><thead><tr><th>Rank</th><th>Country</th><th>Priority</th><th>Freshness</th><th>Depth Band</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )



def _render_country_coverage_visibility(visibility: dict[str, Any]) -> str:
    priority_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('priority_summary', [])
    ) or "<tr><td colspan='3'>No priority coverage summary available.</td></tr>"
    depth_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('source_depth_band_summary', [])
    ) or "<tr><td colspan='3'>No source depth summary available.</td></tr>"
    freshness_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('freshness_band_summary', [])
    ) or "<tr><td colspan='3'>No freshness summary available.</td></tr>"
    gap_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'n/a')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{_render_missing_domain_badges(list(row.get('missing_domains', [])))}</td>"
        f"<td>{_render_gap_details(list(row.get('gap_details', [])))}</td>"
        "</tr>"
        for row in visibility.get('country_gap_rows', [])
    ) or "<tr><td colspan='7'>No explicit country domain gaps recorded.</td></tr>"
    missing_domain_totals = ''.join(
        f"<li>{html.escape(str(domain))}: {html.escape(str(count))}</li>"
        for domain, count in sorted(visibility.get('missing_domain_totals', {}).items())
    ) or '<li>none</li>'
    return (
        "<h3>Priority Coverage Summary</h3>"
        "<table><thead><tr><th>Priority</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{priority_rows}</tbody></table>"
        "<h3>Source Depth Band Summary</h3>"
        "<table><thead><tr><th>Depth Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{depth_rows}</tbody></table>"
        "<h3>Freshness Band Summary</h3>"
        "<table><thead><tr><th>Freshness Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{freshness_rows}</tbody></table>"
        f"{_render_stale_priority_watchlist(visibility)}"
        f"{_render_remediation_watchlist(visibility)}"
        "<h3>Country Coverage / Gap Watchlist</h3>"
        f"<div><strong>Missing domain totals</strong><ul>{missing_domain_totals}</ul></div>"
        "<table><thead><tr><th>Country</th><th>Priority</th><th>Depth Band</th><th>Freshness</th><th>Source Count</th><th>Missing Domains</th><th>Gap Cause</th></tr></thead>"
        f"<tbody>{gap_rows}</tbody></table>"
    )



def _render_country_coverage_matrix(visibility: dict[str, Any]) -> str:
    freshness_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('band', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('country_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('countries', [])) or 'none')}</td>"
        "</tr>"
        for row in visibility.get('freshness_band_summary', [])
    ) or "<tr><td colspan='3'>No freshness summary available.</td></tr>"
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'n/a')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('missing_domain_count', 0)))}</td>"
        f"<td>{_render_missing_domain_badges(list(row.get('missing_domains', [])))}</td>"
        f"<td>{_render_gap_details(list(row.get('gap_details', [])))}</td>"
        "</tr>"
        for row in visibility.get('country_gap_rows', [])
    ) or "<tr><td colspan='8'>No per-country coverage gaps recorded.</td></tr>"
    return (
        f"{_render_stale_priority_watchlist(visibility)}"
        f"{_render_remediation_watchlist(visibility)}"
        "<h3>Freshness Band Summary</h3>"
        "<table><thead><tr><th>Freshness Band</th><th>Countries</th><th>Country IDs</th></tr></thead>"
        f"<tbody>{freshness_rows}</tbody></table>"
        "<h3>Country Coverage / Gap Matrix</h3>"
        "<p>Priority, source depth, explicit missing-domain badges, and freshness bands stay visible alongside source-level coverage.</p>"
        "<table><thead><tr><th>Country</th><th>Priority</th><th>Depth Band</th><th>Freshness</th><th>Source Count</th><th>Gap Count</th><th>Missing Domains</th><th>Gap Cause</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
    )



def _render_country_trust_visualization(country_profile_read_models: dict[str, dict[str, Any]]) -> str:
    if not country_profile_read_models:
        return "<p>No country trust metrics available.</p>"

    rows: list[str] = []
    svg_rows: list[str] = []
    for index, (country_id, profile) in enumerate(sorted(country_profile_read_models.items())):
        coverage = profile.get('coverage')
        confidence = profile.get('confidence')
        coverage_ratio = _coerce_ratio(coverage) or 0.0
        confidence_ratio = _coerce_ratio(confidence) or 0.0
        y = 28 + (index * 26)
        svg_rows.append(
            f"<text x='8' y='{y + 11}' font-size='9' fill='#b9c7e0' font-family='Space Grotesk,monospace'>{html.escape(country_id)}</text>"
            f"<rect x='64' y='{y}' width='100' height='8' rx='1' fill='#2d3449'></rect>"
            f"<rect x='64' y='{y}' width='{int(round(coverage_ratio * 100))}' height='8' rx='1' fill='{html.escape(_band_color(_ratio_band(coverage)))}'></rect>"
            f"<rect x='182' y='{y}' width='100' height='8' rx='1' fill='#2d3449'></rect>"
            f"<rect x='182' y='{y}' width='{int(round(confidence_ratio * 100))}' height='8' rx='1' fill='{html.escape(_band_color(_ratio_band(confidence)))}'></rect>"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(str(coverage))}</td>"
            f"<td>{html.escape(_ratio_band(coverage))}</td>"
            f"<td>{html.escape(str(confidence))}</td>"
            f"<td>{html.escape(_ratio_band(confidence))}</td>"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    chart_height = max(72, 40 + (len(country_profile_read_models) * 26))
    return (
        "<h3>Coverage / Confidence Visualization</h3>"
        "<p>Coverage and confidence are rendered as country-level trust bars so gaps remain visually explicit.</p>"
        "<svg viewBox='0 0 300 {height}' width='300' height='{height}' role='img' aria-label='Coverage and confidence by country' style='background:#0f1828;border:1px solid rgba(78,222,163,.12);border-radius:2px;display:block;padding:4px;'>"
        "<text x='64' y='16' font-size='9' fill='#4edea3' font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.08em'>COVERAGE</text>"
        "<text x='182' y='16' font-size='9' fill='#4edea3' font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.08em'>CONFIDENCE</text>"
        "{rows}"
        "</svg>"
        "<table><thead><tr><th>Country</th><th>Coverage</th><th>Coverage Band</th><th>Confidence</th><th>Confidence Band</th><th>Uncertainty</th></tr></thead>"
        "<tbody>{table_rows}</tbody></table>"
    ).format(height=chart_height, rows=''.join(svg_rows), table_rows=''.join(rows))



def _render_domain_projection(country_profile_read_models: dict[str, dict[str, Any]], active_domains: list[str]) -> str:
    if not country_profile_read_models or not active_domains:
        return "<p>No domain projection data available.</p>"

    rows: list[str] = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        domain_cells = ''.join(
            f"<td class='domain-projection-value'>{html.escape(str(profile.get('domain_states', {}).get(domain, 'n/a')))}</td>"
            for domain in active_domains
        )
        rows.append(
            f"<tr class='domain-projection-row' data-country-id='{html.escape(country_id)}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"{domain_cells}"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    header_cells = ''.join(f"<th>{html.escape(domain)} Status</th>" for domain in active_domains)
    return (
        "<h3>Domain Projection View</h3>"
        "<p>Domain-specific projection makes the active domain status slice explicit per visible country.</p>"
        f"<table id='domain-projection-table'><thead><tr><th>Country</th>{header_cells}<th>Uncertainty</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )



def _render_world_map_visualization(
    world_map_read_model: dict[str, Any],
    available_country_ids: set[str],
    coverage_visibility: dict[str, Any] | None = None,
) -> str:
    metadata_lookup = _country_metadata_lookup()
    coverage_by_country = {
        str(row.get('country_id', 'UNKNOWN')): row
        for row in (coverage_visibility or {}).get('country_freshness_rows', [])\
    }

    # Build status/freshness/href lookup per country from readmodel
    country_data: dict[str, dict[str, Any]] = {}
    for country in world_map_read_model.get('countries', []):
        country_id = str(country.get('country_id', 'UNKNOWN'))
        status = str(country.get('status', 'n/a'))
        country_visibility = coverage_by_country.get(country_id, {})
        freshness_label = _format_freshness(country_visibility.get('freshness_hours'))
        freshness_band = _freshness_band(country_visibility.get('freshness_hours'))
        metadata = metadata_lookup.get(country_id, {})
        href = f"countries/{country_id}.html" if country_id in available_country_ids else "none"
        country_data[country_id] = {
            'status': status,
            'freshness_label': freshness_label,
            'freshness_band': freshness_band,
            'color': _status_color(status),
            'freshness_color': _freshness_band_color(freshness_band),
            'href': href,
            'name': metadata.get('country_name', country_id),
            'region': str(metadata.get('region', 'n/a')),
            'priority': str(metadata.get('priority', 'n/a')),
        }

    # Legend table
    legend_rows: list[str] = []
    for country_id, data in sorted(country_data.items()):
        legend_rows.append(
            "<tr>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(data['name'])}</td>"
            f"<td>{html.escape(data['region'])}</td>"
            f"<td>{html.escape(data['priority'])}</td>"
            f"<td>{html.escape(data['freshness_label'])}</td>"
            "<td><span class='status' style='color:" + html.escape(data['color']) + f"'>{html.escape(data['status'])}</span></td>"
            "</tr>"
        )

    # Equirectangular projection helper
    def pt(lon: float, lat: float) -> str:
        x = (lon + 180) * (960 / 360)
        y = (90 - lat) * (500 / 180)
        return f"{x:.1f},{y:.1f}"

    def poly(coords: list[tuple[float, float]]) -> str:
        return "M " + " L ".join(pt(lon, lat) for lon, lat in coords) + " Z"

    def mpoly(polygons: list[list[tuple[float, float]]]) -> str:
        return " ".join(poly(p) for p in polygons)

    # MVP country path definitions (Equirectangular, viewBox 0 0 960 500)
    mvp_paths: dict[str, tuple[str, str]] = {
        "UKR": ("Ukraine", poly([(22.1,52.3),(24.0,52.7),(27.5,51.6),(30.2,51.5),(33.8,52.3),(35.5,52.0),(38.2,50.0),(37.4,47.0),(35.0,45.3),(33.5,44.0),(31.2,45.5),(28.0,45.5),(24.9,45.8),(23.2,48.0),(22.1,48.4),(22.6,50.4)])),
        "RUS": ("Russia", mpoly([[(28,72),(40,74),(55,73),(70,73),(85,74),(100,76),(120,74),(140,74),(160,72),(175,68),(180,65),(175,60),(170,58),(165,55),(155,52),(145,48),(140,45),(135,43),(130,42),(125,48),(120,50),(115,53),(105,51),(95,52),(85,55),(80,60),(75,63),(68,65),(60,60),(55,57),(50,54),(45,50),(42,47),(40,43),(38,47),(33,55),(30,60),(27,65),(28,72)],[(19.6,54.4),(22.8,54.4),(22.8,54.8),(19.6,54.8)]])),
        "CHN": ("China", poly([(73,39),(80,45),(87,49),(92,48),(97,50),(103,48),(110,44),(120,47),(125,48),(130,43),(131,42),(128,38),(122,32),(120,26),(117,22),(108,18),(104,21),(100,22),(97,25),(92,28),(86,28),(80,32),(75,35),(73,39)])),
        "TWN": ("Taiwan", poly([(120.0,25.3),(121.9,25.0),(122.0,23.5),(120.8,21.9),(120.0,22.5),(120.0,25.3)])),
        "IRN": ("Iran", poly([(44,39),(47,40),(50,39),(54,37),(60,36),(63,35),(60,31),(58,26),(55,25),(52,27),(48,30),(45,32),(44,34),(44,39)])),
        "ISR": ("Israel", poly([(34.3,33.1),(35.9,33.2),(35.9,32.5),(35.2,31.2),(34.9,29.5),(34.3,30.0),(34.3,33.1)])),
        "TUR": ("Turkey", poly([(26,42),(29,43),(33,42),(36,42),(40,41),(44,40),(44,37),(40,35),(36,36),(33,36),(29,37),(26,38),(26,40),(26,42)])),
        "IND": ("India", poly([(68,23),(72,22),(74,21),(78,19),(80,14),(80,10),(77,8),(76,10),(72,15),(68,22),(67,25),(70,28),(74,31),(76,35),(78,35),(80,33),(84,28),(87,26),(92,23),(90,22),(87,24),(86,20),(82,16),(78,10),(76,8),(72,10),(68,20),(68,23)])),
        "PAK": ("Pakistan", poly([(61,37),(65,37),(68,35),(72,35),(74,32),(73,28),(68,23),(64,25),(60,25),(58,28),(60,30),(60,34),(61,37)])),
        "GEO": ("Georgia", poly([(40.0,43.6),(41.7,43.5),(44.0,43.0),(46.5,41.2),(45.7,41.0),(42.5,41.5),(41.0,41.8),(40.0,42.5),(40.0,43.6)])),
        "USA": ("United States", mpoly([[(-124,49),(-105,49),(-97,49),(-85,47),(-75,45),(-71,45),(-70,43),(-67,45),(-70,47),(-67,44),(-69,41),(-74,40),(-75,36),(-77,35),(-80,32),(-85,30),(-88,30),(-90,29),(-95,29),(-97,26),(-100,28),(-104,29),(-108,31),(-112,31),(-117,33),(-118,34),(-122,37),(-124,40),(-124,46),(-124,49)],[(-170,71),(-160,72),(-155,60),(-150,58),(-145,60),(-135,60),(-140,58),(-155,55),(-165,55),(-170,60),(-170,71)]])),
        "DEU": ("Germany", poly([(6.1,51.0),(7.0,52.8),(8.5,53.5),(10.0,55.0),(12.0,54.5),(14.5,54.0),(14.5,51.0),(13.0,50.5),(12.5,48.0),(13.8,48.0),(12.0,47.5),(10.0,47.5),(7.5,47.5),(6.8,49.5),(6.1,51.0)])),
        "POL": ("Poland", poly([(14.1,54.0),(18.5,54.5),(22.0,54.5),(24.0,54.3),(23.5,52.0),(24.0,50.5),(22.5,49.0),(18.5,50.0),(15.5,50.8),(14.1,51.5),(14.1,54.0)])),
        "EST": ("Estonia", poly([(21.8,57.5),(24.0,57.7),(27.0,57.5),(28.0,59.0),(26.0,59.7),(22.5,59.5),(21.8,58.5),(21.8,57.5)])),
        "FIN": ("Finland", poly([(20.0,60.0),(22.0,60.5),(25.0,60.3),(28.0,65.0),(29.5,70.0),(27.0,70.0),(25.0,68.5),(24.0,65.0),(22.0,63.0),(20.0,63.5),(20.0,60.0)])),
        "SAU": ("Saudi Arabia", poly([(36.5,29.0),(38.0,26.0),(42.0,22.0),(45.0,19.0),(49.0,18.5),(52.0,19.0),(55.0,22.0),(55.5,24.5),(53.0,25.0),(51.0,25.5),(48.0,28.0),(45.5,29.0),(42.5,31.0),(38.5,32.0),(36.5,29.0)])),
        "QAT": ("Qatar", poly([(50.7,24.5),(51.7,24.7),(51.7,25.4),(51.2,26.2),(50.8,25.8),(50.7,24.5)])),
        "NGA": ("Nigeria", poly([(3.0,6.5),(5.0,4.3),(8.5,4.5),(9.0,4.0),(10.0,4.5),(13.5,5.5),(14.5,11.0),(14.0,13.5),(12.5,13.0),(11.0,13.5),(10.0,13.0),(8.0,12.5),(4.0,10.0),(2.7,6.5),(3.0,6.5)])),
        "EGY": ("Egypt", poly([(25.0,22.0),(35.0,22.0),(36.9,22.0),(36.9,24.0),(34.0,29.5),(32.5,31.5),(31.0,31.5),(28.0,31.0),(25.0,31.5),(25.0,22.0)])),
        "SDN": ("Sudan", poly([(23.5,22.0),(36.5,22.0),(37.5,20.0),(38.5,15.5),(36.5,12.0),(35.0,11.5),(34.0,10.5),(33.0,9.5),(28.0,9.5),(24.0,10.0),(23.5,15.0),(23.5,20.0),(23.5,22.0)])),
        "MMR": ("Myanmar", poly([(92.5,28.0),(97.0,28.0),(98.5,26.0),(99.5,22.0),(100.0,20.0),(100.5,19.0),(99.0,18.0),(97.5,16.0),(97.5,14.0),(98.5,10.5),(98.0,10.0),(97.0,14.0),(96.0,16.0),(94.0,19.0),(92.5,22.0),(92.5,28.0)])),
        "CHE": ("Switzerland", poly([(6.0,47.5),(7.0,47.6),(8.2,48.0),(10.5,47.4),(10.5,46.8),(9.5,46.5),(8.0,46.0),(6.5,46.4),(6.0,47.5)])),
        "NLD": ("Netherlands", poly([(3.3,51.4),(4.5,51.5),(5.5,52.0),(7.0,53.2),(6.5,53.5),(5.0,53.5),(4.5,53.0),(3.5,52.5),(3.3,51.9),(3.3,51.4)])),
        "SWE": ("Sweden", poly([(11.0,56.0),(12.5,56.5),(14.0,57.5),(15.0,60.0),(16.0,62.0),(17.5,64.0),(18.0,68.5),(20.0,69.0),(22.0,68.0),(22.0,65.0),(18.0,62.0),(16.0,58.5),(14.5,56.5),(12.0,55.5),(11.0,55.5),(11.0,56.0)])),
        "NOR": ("Norway", poly([(4.5,58.0),(5.5,59.0),(7.0,60.0),(8.0,63.0),(13.0,65.5),(16.0,69.0),(20.0,71.0),(28.0,71.5),(30.0,70.5),(28.0,69.5),(25.0,68.5),(22.0,68.0),(20.0,69.0),(18.0,68.5),(17.5,64.0),(16.0,62.0),(15.0,60.0),(12.0,58.5),(8.0,58.0),(4.5,58.0)])),
        "CAN": ("Canada", mpoly([[(-140,60),(-115,60),(-100,60),(-85,62),(-75,62),(-65,60),(-60,47),(-65,45),(-70,46),(-75,45),(-80,43),(-83,42),(-83,45),(-88,48),(-92,48),(-100,49),(-110,49),(-120,49),(-124,49),(-130,55),(-135,58),(-140,60)]])),
        "AUS": ("Australia", poly([(114,-22),(117,-21),(122,-18),(128,-14),(135,-12),(137,-13),(140,-15),(143,-13),(145,-18),(147,-19),(150,-22),(152,-25),(153,-28),(150,-33),(147,-38),(143,-39),(140,-36),(136,-35),(130,-33),(126,-34),(122,-34),(115,-34),(113,-30),(114,-25),(114,-22)])),
        "NZL": ("New Zealand", mpoly([[(172,-34),(175,-37),(178,-38),(177,-40),(175,-41),(173,-40),(172,-38),(172,-34)],[(166,-46),(168,-47),(170,-46),(172,-44),(172,-42),(171,-41),(169,-43),(166,-45),(166,-46)]])),
        "PRT": ("Portugal", poly([(-9.5,41.8),(-7.5,42.0),(-7.0,40.0),(-7.5,38.0),(-8.0,37.0),(-9.5,37.0),(-9.5,38.5),(-9.2,41.0),(-9.5,41.8)])),
        "IRL": ("Ireland", poly([(-10.0,51.5),(-8.0,51.5),(-6.0,52.0),(-6.2,53.5),(-7.5,55.2),(-8.5,55.5),(-10.0,54.0),(-10.5,52.5),(-10.0,51.5)])),
    }

    # Build country path elements with dynamic status colors
    path_elements: list[str] = []
    for iso3, (cname, path_d) in mvp_paths.items():
        data = country_data.get(iso3, {})
        status_color = html.escape(data.get('color', '#1c2740'))
        freshness_color = html.escape(data.get('freshness_color', '#2d3a52'))
        href = html.escape(data.get('href', 'none'))
        status = html.escape(data.get('status', 'n/a'))
        freshness = html.escape(data.get('freshness_label', 'n/a'))
        has_data = iso3 in country_data
        fill = status_color if has_data else '#1c2740'
        stroke = freshness_color if has_data else '#2d3a52'
        path_elements.append(
            f"<path id='country-{iso3}' class='country-mvp' "
            f"data-iso3='{iso3}' data-name='{html.escape(cname)}' "
            f"data-href='{href}' data-status='{status}' data-freshness='{freshness}' "
            f"d='{path_d}' fill='{fill}' stroke='{stroke}' stroke-width='0.7' "
            f"style='cursor:pointer;transition:fill .15s,stroke .15s,stroke-width .15s;'>"
            f"<title>{html.escape(iso3)} — {html.escape(cname)} — {status}</title></path>"
        )

    # World background continents (non-MVP, very rough)
    other_bg = (
        # South America
        "M100,175 L130,175 L145,195 L140,240 L130,280 L120,300 L100,290 L90,260 L85,230 L90,200 Z "
        # Africa (excluding MVP overlap)
        "M200,165 L245,155 L265,175 L268,215 L255,255 L235,285 L210,280 L192,240 L188,200 Z "
        # Central/South/Southeast Asia background
        "M450,120 L480,115 L510,120 L520,145 L500,160 L470,155 L450,140 Z "
        # Japan
        "M783,120 L790,130 L787,148 L781,138 Z M780,148 L788,153 L783,168 L775,157 Z "
        # Korea
        "M765,128 L775,123 L778,138 L770,143 Z "
        # Southeast Asia background
        "M680,175 L710,170 L715,195 L705,215 L700,228 L695,215 L686,198 Z "
        "M700,228 L707,238 L705,252 L698,245 Z "
        # Indonesia
        "M718,248 L742,245 L748,255 L730,260 Z M746,253 L772,248 L775,258 L755,263 Z "
        # Central Asia
        "M510,108 L572,97 L602,112 L612,133 L582,143 L538,138 L510,128 Z "
        # Afghanistan
        "M588,143 L622,138 L637,153 L627,168 L598,168 L578,158 Z "
        # East Africa
        "M288,212 L312,202 L327,213 L322,238 L305,253 L288,243 Z "
        # West Africa
        "M182,208 L218,202 L232,213 L227,233 L198,238 L178,228 Z "
    )

    map_js = """
<script>
(function(){
  var sel = null;
  var DEF_F = null; // will be set per country from data
  var HOV_F = 'rgba(78,222,163,0.35)';
  var SEL_F = '#4edea3';
  var DEF_S = null;
  var HOV_S = '#4edea3';
  var SEL_S = '#6ffbbe';

  var infoEl = document.getElementById('map-country-info');
  var panelEl = document.getElementById('map-country-panel');
  var panelName = document.getElementById('map-panel-name');
  var panelIso = document.getElementById('map-panel-iso3');
  var panelStatus = document.getElementById('map-panel-status');
  var panelFresh = document.getElementById('map-panel-freshness');
  var panelLink = document.getElementById('map-panel-link');

  function resetEl(el){
    el.style.fill = el.dataset.defFill || '#1c2740';
    el.style.stroke = el.dataset.defStroke || '#2d3a52';
    el.style.strokeWidth = '0.7';
  }

  document.querySelectorAll('.country-mvp').forEach(function(el){
    el.dataset.defFill = el.getAttribute('fill');
    el.dataset.defStroke = el.getAttribute('stroke');

    el.addEventListener('mouseenter', function(){
      if(el !== sel){
        el.style.fill = HOV_F;
        el.style.stroke = HOV_S;
        el.style.strokeWidth = '1.5';
      }
      if(infoEl){ infoEl.textContent = el.dataset.name + ' (' + el.dataset.iso3 + ') — ' + el.dataset.status; }
    });
    el.addEventListener('mouseleave', function(){
      if(el !== sel){ resetEl(el); }
      if(infoEl){ infoEl.textContent = ''; }
    });
    el.addEventListener('click', function(e){
      e.stopPropagation();
      if(sel && sel !== el){ resetEl(sel); }
      if(sel === el){
        resetEl(el); sel = null;
        if(panelEl){ panelEl.style.display='none'; }
      } else {
        el.style.fill = SEL_F;
        el.style.stroke = SEL_S;
        el.style.strokeWidth = '2.5';
        sel = el;
        if(panelEl){ panelEl.style.display='flex'; }
        if(panelName){ panelName.textContent = el.dataset.name; }
        if(panelIso){ panelIso.textContent = el.dataset.iso3; }
        if(panelStatus){ panelStatus.textContent = el.dataset.status; }
        if(panelFresh){ panelFresh.textContent = el.dataset.freshness; }
        if(panelLink){
          var h = el.dataset.href;
          if(h && h !== 'none'){
            panelLink.innerHTML = '<a href="' + h + '" style="color:#4edea3;font-weight:600;">→ Country Profile</a>';
          } else {
            panelLink.innerHTML = '<span style="color:#6b7d99;">No profile available</span>';
          }
        }
        // Sync overview table: highlight matching row
        document.querySelectorAll('.overview-row').forEach(function(row){
          if(row.dataset.countryId === el.dataset.iso3){
            row.style.background = 'rgba(78,222,163,0.08)';
            row.scrollIntoView({behavior:'smooth', block:'nearest'});
          } else {
            row.style.background = '';
          }
        });
      }
    });
  });
  // Click background → deselect
  var svg = document.getElementById('world-map-svg');
  if(svg){ svg.addEventListener('click', function(){
    if(sel){ resetEl(sel); sel=null; }
    if(panelEl){ panelEl.style.display='none'; }
    document.querySelectorAll('.overview-row').forEach(function(r){ r.style.background=''; });
  }); }
})();
</script>"""

    # Info panel HTML
    info_panel = (
        "<div style='display:flex;align-items:center;gap:8px;padding:6px 0 4px;min-height:22px;'>"
        "<span id='map-country-info' style='font-size:11px;color:#4edea3;"
        "font-family:Space Grotesk,monospace;letter-spacing:.04em;'></span>"
        "</div>"
        "<div id='map-country-panel' style='display:none;flex-direction:row;"
        "align-items:center;gap:16px;padding:10px 14px;background:#0f1828;"
        "border:1px solid rgba(78,222,163,.2);border-radius:2px;margin-bottom:10px;'>"
        "<div style='border-left:2px solid #4edea3;padding-left:12px;'>"
        "<div id='map-panel-name' style='font-size:1rem;font-weight:700;color:#dae2fd;'></div>"
        "<div id='map-panel-iso3' style='font-size:11px;color:#4edea3;"
        "font-family:Space Grotesk,monospace;letter-spacing:.1em;margin-top:2px;'></div>"
        "</div>"
        "<div style='flex:1;'>"
        "<div style='font-size:11px;color:#6b7d99;font-family:Space Grotesk,monospace;"
        "text-transform:uppercase;letter-spacing:.08em;'>Status</div>"
        "<div id='map-panel-status' style='font-size:13px;color:#e3b341;font-weight:600;'></div>"
        "</div>"
        "<div style='flex:1;'>"
        "<div style='font-size:11px;color:#6b7d99;font-family:Space Grotesk,monospace;"
        "text-transform:uppercase;letter-spacing:.08em;'>Freshness</div>"
        "<div id='map-panel-freshness' style='font-size:13px;color:#b9c7e0;'></div>"
        "</div>"
        "<div id='map-panel-link' style='margin-left:auto;'></div>"
        "</div>"
    )

    svg_html = (
        f"<svg id='world-map-svg' viewBox='0 0 960 500' "
        f"style='width:100%;max-width:960px;height:auto;display:block;"
        f"background:#0b1326;border:1px solid rgba(78,222,163,.1);"
        f"border-radius:2px;cursor:default;' "
        f"role='img' aria-label='SIASA World Anomaly Map'>"
        f"<rect width='960' height='500' fill='#0b1326'/>"
        # Ocean grid lines (subtle)
        f"<line x1='0' y1='250' x2='960' y2='250' stroke='rgba(78,222,163,.06)' stroke-width='0.5'/>"
        f"<line x1='480' y1='0' x2='480' y2='500' stroke='rgba(78,222,163,.06)' stroke-width='0.5'/>"
        # Non-MVP continents
        f"<path d='{other_bg}' fill='#131b2e' stroke='#0f1828' stroke-width='0.5'/>"
        # MVP country paths
        + "".join(path_elements) +
        # Region labels
        f"<text x='50' y='175' font-size='8' fill='rgba(78,222,163,.35)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.12em'>N.AMERICA</text>"
        f"<text x='290' y='115' font-size='8' fill='rgba(78,222,163,.35)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.12em'>EUROPE</text>"
        f"<text x='590' y='135' font-size='8' fill='rgba(78,222,163,.35)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.12em'>ASIA</text>"
        f"<text x='290' y='255' font-size='8' fill='rgba(78,222,163,.35)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.1em'>AFRICA</text>"
        f"<text x='700' y='380' font-size='8' fill='rgba(78,222,163,.35)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' letter-spacing='.1em'>OCEANIA</text>"
        f"</svg>"
        f"{map_js}"
    )

    return (
        "<p style='font-size:11px;color:#6b7d99;margin-bottom:6px;font-family:Space Grotesk,monospace;'>"
        "Hover to identify · Click to select &amp; highlight country profile · Click background to deselect</p>"
        + info_panel
        + svg_html
        + "<h3>Country Status Legend</h3>"
        + "<table><thead><tr><th>ISO3</th><th>Name</th><th>Region</th>"
        + "<th>Priority</th><th>Freshness</th><th>Status</th></tr></thead>"
        + f"<tbody>{''.join(legend_rows)}</tbody></table>"
    )




def _annotation_index(annotations_view_model: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if annotations_view_model is None:
        return {}
    return {
        str(annotation.get('annotation_id')): annotation
        for annotation in annotations_view_model.get('annotations', [])
    }



def _trend_filter_options(country_profile_read_models: dict[str, dict[str, Any]]) -> list[str]:
    labels: set[str] = set()
    for profile in country_profile_read_models.values():
        labels.update(_trend_labels(profile.get('trends', {}).get('yearly', []), label_key='label'))
    return sorted(labels)



def _annotation_details_html(annotation_ids: list[str], annotations_view_model: dict[str, Any] | None) -> str:
    annotation_lookup = _annotation_index(annotations_view_model)
    if not annotation_ids:
        return "<p>No annotations.</p>"

    rows: list[str] = []
    for annotation_id in annotation_ids:
        annotation = annotation_lookup.get(str(annotation_id))
        if annotation is None:
            rows.append(
                "<tr>"
                f"<td>{html.escape(str(annotation_id))}</td>"
                "<td colspan='6'>Annotation details unavailable.</td>"
                "</tr>"
            )
            continue
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(annotation.get('annotation_id', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('scope', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('annotation_type', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('author', '')))}</td>"
            f"<td>{html.escape(str(annotation.get('review_status', '')))}</td>"
            f"<td>{html.escape(', '.join(str(item) for item in annotation.get('linked_items', [])))}</td>"
            f"<td>{html.escape(str(annotation.get('text', '')))}</td>"
            "</tr>"
        )
    return (
        "<table><thead><tr><th>ID</th><th>Scope</th><th>Type</th><th>Author</th><th>Review</th><th>Linked Items</th><th>Text</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
    )



def _annotation_workflow_href(*, nav_prefix: str, scope: str, linked_item: str, annotation_type: str) -> str:
    query = (
        f"scope={quote(scope, safe='')}"
        f"&linked_item={quote(linked_item, safe='')}"
        f"&annotation_type={quote(annotation_type, safe='')}"
    )
    return f"{nav_prefix}annotations.html?{query}"



def _annotation_workflow_seed(annotations_view_model: dict[str, Any]) -> str:
    payload = {
        'annotations': list(annotations_view_model.get('annotations', [])),
        'allowed_scopes': ['country', 'domain', 'signal', 'event', 'snapshot'],
        'allowed_annotation_types': ['context_note', 'false_positive_note', 'source_quality_note', 'lineage_note', 'review_note'],
        'allowed_severity_assessments': ['not_security_relevant', 'relevant', 'uncertain'],
        'allowed_confidence_assessments': ['low', 'medium', 'high'],
        'allowed_review_statuses': ['unreviewed', 'draft', 'reviewed', 'accepted', 'rejected'],
    }
    return json.dumps(payload, sort_keys=True).replace('</', '<\\/')



def load_site_payload_from_artifacts(artifacts_dir: Path) -> SitePayload:
    snapshot = _load_json(artifacts_dir / 'snapshot.json')

    readmodels_dir = artifacts_dir / 'readmodels'
    world_map_read_model = _load_json(readmodels_dir / 'world_map.json')
    source_coverage_read_model = _load_json(readmodels_dir / 'source_coverage.json')
    system_status_read_model = _load_json(readmodels_dir / 'system_status.json')
    system_status_read_model.setdefault('run_id', snapshot.get('run_id'))
    system_status_read_model.setdefault('run_status', snapshot.get('status'))
    system_status_read_model.setdefault('snapshot_id', snapshot.get('snapshot_id'))
    system_status_read_model.setdefault('active_domains', snapshot.get('active_domains', []))

    country_profile_read_models = {
        country_file.stem: _load_json(country_file)
        for country_file in sorted((readmodels_dir / 'country_profiles').glob('*.json'))
    }
    domain_detail_read_models = {
        (str(read_model['country_id']), str(read_model['domain'])): read_model
        for read_model in (
            _load_json(domain_file)
            for domain_file in sorted((readmodels_dir / 'domain_details').glob('*.json'))
        )
    }
    report_catalog = {
        report_file.stem: _load_json(report_file)
        for report_file in sorted((artifacts_dir / 'reports').glob('*.json'))
    }
    validation_view_model = None
    validation_view_path = readmodels_dir / 'validation_backtest.json'
    if validation_view_path.exists():
        validation_view_model = _load_json(validation_view_path)
    traceability_view_model = None
    traceability_view_path = readmodels_dir / 'traceability_lineage.json'
    if traceability_view_path.exists():
        traceability_view_model = _load_json(traceability_view_path)
    repo_closure_view_model = None
    repo_closure_view_path = readmodels_dir / 'repo_closure.json'
    if repo_closure_view_path.exists():
        repo_closure_view_model = _load_json(repo_closure_view_path)
    else:
        repo_closure_view_model = build_repo_closure_report(repo_root=Path(__file__).resolve().parents[3])
    annotations_view_model = None
    annotations_view_path = readmodels_dir / 'annotations.json'
    if annotations_view_path.exists():
        annotations_view_model = _load_json(annotations_view_path)
    else:
        annotations_view_model = {'annotations': [], 'by_scope': {}, 'by_linked_item': {}}
    readiness_view_model = None
    readiness_view_path = readmodels_dir / 'readiness.json'
    if readiness_view_path.exists():
        readiness_view_model = _load_json(readiness_view_path)

    return {
        'world_map_read_model': world_map_read_model,
        'country_profile_read_models': country_profile_read_models,
        'domain_detail_read_models': domain_detail_read_models,
        'source_coverage_read_model': source_coverage_read_model,
        'report_catalog': report_catalog,
        'system_status_read_model': system_status_read_model,
        'validation_view_model': validation_view_model,
        'traceability_view_model': traceability_view_model,
        'repo_closure_view_model': repo_closure_view_model,
        'annotations_view_model': annotations_view_model,
        'readiness_view_model': readiness_view_model,
    }


def _render_index(
    world_map_read_model: dict[str, Any],
    available_country_ids: set[str] | None = None,
    country_profile_read_models: dict[str, dict[str, Any]] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    rows = []
    available_country_ids = available_country_ids or set()
    country_profile_read_models = country_profile_read_models or {}
    system_status_read_model = system_status_read_model or {}
    coverage_visibility = _country_coverage_visibility_rows(system_status_read_model)
    coverage_by_country = {
        str(row.get('country_id', 'UNKNOWN')): row
        for row in coverage_visibility.get('country_freshness_rows', [])
    }
    trend_options = _trend_filter_options(country_profile_read_models)
    for country in world_map_read_model.get("countries", []):
        country_id = str(country["country_id"])
        status = str(country["status"])
        active_domains = [str(domain) for domain in country.get('active_domains', [])]
        country_profile = country_profile_read_models.get(country_id, {})
        country_context = country_profile.get('country_context', {})
        source_depth = country_profile.get('source_depth', {})
        domain_gap_summary = country_profile.get('domain_gap_summary', {})
        trend_labels = ','.join(
            _trend_labels(
                country_profile.get('trends', {}).get('yearly', []),
                label_key='label',
            )
        )
        domain_state_attributes = ''.join(
            f" data-domain-{html.escape(domain.lower())}-status='{html.escape(str(country_profile.get('domain_states', {}).get(domain, 'n/a')))}'"
            for domain in world_map_read_model.get('active_domains', [])
        )
        has_country_page = country_id in available_country_ids
        country_cell = (
            f"<a href='countries/{html.escape(country_id)}.html'>{html.escape(country_id)}</a>"
            if has_country_page
            else html.escape(country_id)
        )
        drill_down_cell = f"countries/{html.escape(country_id)}.html" if has_country_page else "not available"
        support_status = "supported" if has_country_page else "not available"
        source_ids = [str(item) for item in source_depth.get('source_ids', [])]
        source_depth_band = _source_depth_band(source_depth.get('source_count', 0))
        freshness_entry = coverage_by_country.get(country_id, {})
        freshness_hours = freshness_entry.get('freshness_hours')
        freshness_band = _freshness_band(freshness_hours)
        missing_domains = [str(item) for item in domain_gap_summary.get('missing_domains', [])]
        rows.append(
            f"<tr class='overview-row' data-country-id='{html.escape(country_id)}' data-active-domains='{html.escape(','.join(active_domains))}' data-status='{html.escape(status)}' data-trend-labels='{html.escape(trend_labels)}' data-priority='{html.escape(str(country_context.get('priority', 'n/a')))}' data-source-depth-band='{html.escape(source_depth_band)}' data-freshness-band='{html.escape(freshness_band)}' data-missing-domain-count='{html.escape(str(len(missing_domains)))}'{domain_state_attributes}>"
            f"<td>{country_cell}</td>"
            f"<td>{html.escape(support_status)}</td>"
            f"<td>{html.escape(str(country_context.get('priority', 'n/a')))}</td>"
            f"<td class='status'>{html.escape(status)}</td>"
            f"<td>{html.escape(', '.join(active_domains))}</td>"
            f"<td>{html.escape(str(source_depth.get('source_count', 0)))} ({html.escape(', '.join(source_ids) or 'none')})</td>"
            f"<td>{html.escape(source_depth_band)}</td>"
            f"<td>{html.escape(_format_freshness(freshness_hours))}</td>"
            f"<td>{_render_missing_domain_badges(missing_domains)}</td>"
            f"<td>{drill_down_cell}</td>"
            "</tr>"
        )

    top_status_changes_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(change.get('country_id', '')))}</td>"
        f"<td>{html.escape(str(change.get('from_status', 'n/a')))} → {html.escape(str(change.get('to_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(change.get('direction', 'n/a')))}</td>"
        "</tr>"
        for change in system_status_read_model.get('top_status_changes', [])
    ) or "<tr><td colspan='3'>No status changes recorded.</td></tr>"
    data_gap_items = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('data_gaps', [])
    ) or "<li>none</li>"
    failed_sources = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('failed_sources', [])
    ) or "<li>none</li>"

    controls_html = (
        "<h3>Baseline / View Controls</h3>"
        f"<p>Baseline Mode: <strong>{html.escape(str(world_map_read_model.get('baseline_mode', 'unknown')))}</strong></p>"
        "<label for='priority-filter'>Priority Filter</label> "
        "<select id='priority-filter' name='priority-filter'>"
        "<option value='all'>All priorities</option>"
        + ''.join(
            f"<option value='{html.escape(str(row.get('priority', 'n/a')))}'>{html.escape(str(row.get('priority', 'n/a')))}</option>"
            for row in coverage_visibility.get('priority_summary', [])
        )
        + "</select> "
        "<label for='domain-filter'>Domain Filter</label> "
        "<select id='domain-filter' name='domain-filter'>"
        "<option value='all'>All active domains</option>"
        + ''.join(
            f"<option value='{html.escape(domain)}'>{html.escape(domain)}</option>"
            for domain in world_map_read_model.get('active_domains', [])
        )
        + "</select> "
        "<label for='time-window'>Time Window</label> "
        "<select id='time-window' name='time-window'><option value='all'>All trend labels</option>"
        + ''.join(
            f"<option value='{html.escape(label)}'>{html.escape(label)}</option>"
            for label in trend_options
        )
        + "</select> "
        "<label for='status-filter'>Status Filter</label> "
        "<select id='status-filter' name='status-filter'><option value='all'>All statuses</option><option value='S1'>S1</option><option value='S2'>S2</option><option value='S3'>S3</option><option value='S4'>S4</option></select> "
        "<label for='country-search'>Country Search</label> "
        "<input id='country-search' type='text' placeholder='e.g. UKR or POL'/> "
        "<button id='overview-save-state' type='button'>Save View</button> "
        "<button id='overview-restore-state' type='button'>Restore View</button> "
        "<button id='overview-copy-link' type='button'>Copy View Link</button> "
        "<span id='overview-link-status' style='font-size:11px;color:#6b7d99;font-family:Space Grotesk,monospace;'></span> "
        "<label for='view-mode'>View Mode</label> "
        "<select id='view-mode' name='view-mode'>"
        "<option value='multi-domain'>Multi-domain status</option>"
        "<option value='coverage'>Coverage emphasis</option>"
        + ''.join(
            f"<option value='domain-{html.escape(domain)}'>Domain {html.escape(domain)} projection</option>"
            for domain in world_map_read_model.get('active_domains', [])
        )
        + "</select>"
    )

    body = (
        # === KPI Header Zone ===
        f"<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Run Status</span><div class='kpi-value' style='font-size:1rem;color:{html.escape(_run_status_color(str(system_status_read_model.get('run_status','n/a'))))}'>{html.escape(str(system_status_read_model.get('run_status','n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Countries Monitored</span><div class='kpi-value'>{html.escape(str(len(world_map_read_model.get('countries',[]))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Active Domains</span><div class='kpi-value'>{html.escape(', '.join(world_map_read_model.get('active_domains',[])) or 'n/a')}</div><div class='kpi-sub'>A–E domain slices</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Baseline Mode</span><div class='kpi-value' style='font-size:0.85rem;'>{html.escape(str(world_map_read_model.get('baseline_mode','unknown')))}</div></div>"
        "<div class='kpi-card'><span class='kpi-label'>Failed Sources</span><div class='kpi-value' style='color:" + ("#ffb4ab" if system_status_read_model.get("failed_sources") else "#4edea3") + f"'>{html.escape(str(len(system_status_read_model.get('failed_sources',[]))))}</div></div>"
        "<div class='kpi-card'><span class='kpi-label'>Data Gaps</span><div class='kpi-value' style='color:" + ("#e3b341" if system_status_read_model.get("data_gaps") else "#4edea3") + f"'>{html.escape(str(len(system_status_read_model.get('data_gaps',[]))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Snapshot</span><div class='kpi-value' style='font-size:0.75rem;color:#6b7d99;'>{html.escape(str(system_status_read_model.get('snapshot_id','n/a')))}</div></div>"
        f"</div>"
        # === Status Changes ===
        f"<div class='panel'><div class='panel-header'>Top Status Changes</div>"
        "<table><thead><tr><th>Country</th><th>Status Change</th><th>Direction</th></tr></thead>"
        f"<tbody>{top_status_changes_rows}</tbody></table></div>"
        # === Failed Sources / Data Gaps (collapsible) ===
        f"<details><summary>Failed Sources ({len(system_status_read_model.get('failed_sources',[]))})</summary><ul>{failed_sources}</ul></details>"
        f"<details><summary>Data Gaps / Trust Limits ({len(system_status_read_model.get('data_gaps',[]))})</summary><ul>{data_gap_items}</ul></details>"
        # === World Anomaly Map ===
        f"<div class='panel'><div class='panel-header'>World Anomaly Map — {html.escape(str(world_map_read_model.get('baseline_mode','unknown')))} Baseline</div>"
        f"<div class='controls-bar'>{controls_html}</div>"
        "<p id='overview-filter-result' style='font-size:11px;color:#6b7d99;margin-top:8px;font-family:Space Grotesk,monospace;'>Selected Time Window: all trend labels | View Mode: multi-domain status</p>"
        "<p id='overview-visible-count' style='font-size:11px;color:#6b7d99;margin-top:4px;font-family:Space Grotesk,monospace;'>Visible countries: 0</p>"
        f"<div id='map-visualization-block'>{_render_world_map_visualization(world_map_read_model, available_country_ids, coverage_visibility)}</div>"
        f"<div id='coverage-visualization-block' style='display:none'>{_render_country_trust_visualization(country_profile_read_models)}</div>"
        f"<div id='domain-projection-block' style='display:none'>{_render_domain_projection(country_profile_read_models, [str(domain) for domain in world_map_read_model.get('active_domains', [])])}</div>"
        f"</div>"
        # === Coverage Visibility ===
        f"<div class='panel'><div class='panel-header'>Coverage Visibility</div>{_render_country_coverage_visibility(coverage_visibility)}</div>"
        # === Global Overview Table ===
        f"<div class='panel'><div class='panel-header'>Global Overview — All Countries</div>"
        "<div class='table-container'><table id='overview-table'><thead><tr><th>Country</th><th>Support</th><th>Priority</th><th>Multi-Domain Status</th><th>Active Domains</th><th>Source Depth</th><th>Depth Band</th><th>Freshness</th><th>Domain Gaps</th><th>Drill-down</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table></div></div>"
        "<script>"
        "function getOverviewState(){"
        "return {"
        "priority:document.getElementById('priority-filter').value,"
        "domain:document.getElementById('domain-filter').value,"
        "time:document.getElementById('time-window').value,"
        "status:document.getElementById('status-filter').value,"
        "search:document.getElementById('country-search').value||'',"
        "view:document.getElementById('view-mode').value"
        "};"
        "}"
        "function applyOverviewState(state){"
        "if(!state||typeof state!=='object'){return false;}"
        "if(state.priority!==undefined){document.getElementById('priority-filter').value=state.priority;}"
        "if(state.domain!==undefined){document.getElementById('domain-filter').value=state.domain;}"
        "if(state.time!==undefined){document.getElementById('time-window').value=state.time;}"
        "if(state.status!==undefined){document.getElementById('status-filter').value=state.status;}"
        "if(state.search!==undefined){document.getElementById('country-search').value=state.search;}"
        "if(state.view!==undefined){document.getElementById('view-mode').value=state.view;}"
        "return true;"
        "}"
        "function persistOverviewStateToHash(){"
        "const state=getOverviewState();"
        "const params=new URLSearchParams();"
        "params.set('ov_priority',state.priority);"
        "params.set('ov_domain',state.domain);"
        "params.set('ov_time',state.time);"
        "params.set('ov_status',state.status);"
        "params.set('ov_search',state.search);"
        "params.set('ov_view',state.view);"
        "window.location.hash='ov='+encodeURIComponent(params.toString());"
        "}"
        "function applyOverviewStateFromHash(){"
        "const hash=(window.location.hash||'').replace(/^#/, '');"
        "if(!hash.startsWith('ov=')){return false;}"
        "const raw=decodeURIComponent(hash.slice(3));"
        "const params=new URLSearchParams(raw);"
        "return applyOverviewState({"
        "priority:params.get('ov_priority')||'all',"
        "domain:params.get('ov_domain')||'all',"
        "time:params.get('ov_time')||'all',"
        "status:params.get('ov_status')||'all',"
        "search:params.get('ov_search')||'',"
        "view:params.get('ov_view')||'multi-domain'"
        "});"
        "}"
        "function copyOverviewFilterLink(){"
        "persistOverviewStateToHash();"
        "const status=document.getElementById('overview-link-status');"
        "const shareUrl=window.location.href;"
        "if(!navigator.clipboard||!navigator.clipboard.writeText){status.textContent='Link copy unavailable in this browser.';return;}"
        "navigator.clipboard.writeText(shareUrl).then(()=>{status.textContent='Overview link copied.';}).catch(()=>{status.textContent='Overview link copy failed.';});"
        "}"
        "function saveOverviewStateLocally(){"
        "window.localStorage.setItem('siasa_overview_state', JSON.stringify(getOverviewState()));"
        "document.getElementById('overview-link-status').textContent='Overview view saved.';"
        "}"
        "function restoreOverviewStateLocally(){"
        "const saved=window.localStorage.getItem('siasa_overview_state');"
        "if(!saved){document.getElementById('overview-link-status').textContent='No saved overview view found.';return;}"
        "try{"
        "const parsed=JSON.parse(saved);"
        "applyOverviewState(parsed);"
        "applyOverviewFilters();"
        "document.getElementById('overview-link-status').textContent='Overview view restored.';"
        "}catch(_err){document.getElementById('overview-link-status').textContent='Saved overview view is invalid.';}"
        "}"
        "function applyOverviewViewMode(){"
        "const viewMode=document.getElementById('view-mode').value;"
        "const showCoverage=viewMode==='coverage';"
        "const showDomain=viewMode.startsWith('domain-');"
        "const selectedDomain=showDomain?viewMode.replace('domain-','').toUpperCase():'';"
        "document.getElementById('map-visualization-block').style.display=(!showCoverage&&!showDomain)?'':'none';"
        "document.getElementById('coverage-visualization-block').style.display=showCoverage?'':'none';"
        "document.getElementById('domain-projection-block').style.display=showDomain?'':'none';"
        "document.querySelectorAll('.domain-projection-value').forEach((cell)=>{cell.style.display='';});"
        "if(showDomain){"
        "const headers=Array.from(document.querySelectorAll('#domain-projection-table thead th'));"
        "headers.forEach((header,index)=>{if(index===0||index===headers.length-1){header.style.display='';return;} const domainLabel=(header.textContent||'').split(' ')[0]; header.style.display=(domainLabel===selectedDomain)?'':'none';});"
        "document.querySelectorAll('#domain-projection-table tbody tr').forEach((row)=>{const domainAStatus=row.dataset.domainAStatus||''; const domainBStatus=row.dataset.domainBStatus||''; const domainDStatus=row.dataset.domainDStatus||''; row.querySelectorAll('.domain-projection-value').forEach((cell,index)=>{const mapped=['A','B','D','C','E'][index]||''; cell.style.display=(mapped===selectedDomain)?'':'none';}); row.style.display=row.style.display==='none'?'none':'';});"
        "}"
        "}"
        "function applyOverviewFilters(){"
        "const priority=document.getElementById('priority-filter').value;"
        "const domain=document.getElementById('domain-filter').value;"
        "const timeWindow=document.getElementById('time-window').value;"
        "const status=document.getElementById('status-filter').value;"
        "const countrySearch=(document.getElementById('country-search').value||'').trim().toUpperCase();"
        "const viewMode=document.getElementById('view-mode').value;"
        "let visibleCount=0;"
        "document.querySelectorAll('.overview-row').forEach((row)=>{"
        "const rowPriority=row.dataset.priority||'';"
        "const rowStatus=row.dataset.status||'';"
        "const rowCountry=(row.dataset.countryId||'').toUpperCase();"
        "const domains=(row.dataset.activeDomains||'').split(',').filter(Boolean);"
        "const trendLabels=(row.dataset.trendLabels||'').split(',').filter(Boolean);"
        "const priorityMatch=(priority==='all'||rowPriority===priority);"
        "const domainMatch=(domain==='all'||domains.includes(domain));"
        "const timeMatch=(timeWindow==='all'||trendLabels.includes(timeWindow));"
        "const statusMatch=(status==='all'||rowStatus===status);"
        "const searchMatch=(!countrySearch||rowCountry.indexOf(countrySearch)!==-1);"
        "const visible=(priorityMatch&&domainMatch&&timeMatch&&statusMatch&&searchMatch);"
        "row.style.display=visible?'':'none';"
        "if(visible){visibleCount+=1;}"
        "});"
        "document.querySelectorAll('.domain-projection-row').forEach((row)=>{"
        "const sourceRow=document.querySelector(`.overview-row[data-country-id='${row.dataset.countryId}']`);"
        "row.dataset.domainAStatus=sourceRow?.dataset.domainAStatus||'';"
        "row.dataset.domainBStatus=sourceRow?.dataset.domainBStatus||'';"
        "row.dataset.domainDStatus=sourceRow?.dataset.domainDStatus||'';"
        "row.style.display=(sourceRow&&sourceRow.style.display!=='none')?'':'none';"
        "});"
        "applyOverviewViewMode();"
        "const resultText='Priority Filter: '+priority+' | Status Filter: '+status+' | Country Search: '+(countrySearch||'all')+' | Selected Time Window: '+timeWindow+' | View Mode: '+viewMode;"
        "document.getElementById('overview-filter-result').textContent=resultText;"
        "document.getElementById('overview-visible-count').textContent='Visible countries: '+visibleCount;"
        "}"
        "document.getElementById('priority-filter').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('domain-filter').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('time-window').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('status-filter').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('country-search').addEventListener('input', applyOverviewFilters);"
        "document.getElementById('view-mode').addEventListener('change', applyOverviewFilters);"
        "document.getElementById('overview-save-state').addEventListener('click', saveOverviewStateLocally);"
        "document.getElementById('overview-restore-state').addEventListener('click', restoreOverviewStateLocally);"
        "document.getElementById('overview-copy-link').addEventListener('click', copyOverviewFilterLink);"
        "if(applyOverviewStateFromHash()){document.getElementById('overview-link-status').textContent='Overview view loaded from link.';}"
        "applyOverviewFilters();"
        "</script>"
    )
    return _page("World Anomaly Map / Global Overview", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_country(
    country_profile: dict[str, Any],
    annotations_view_model: dict[str, Any] | None = None,
    available_domain_targets: dict[str, str] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    domain_rows = ''.join(
        f"<tr><td>{html.escape(domain)}</td><td>{html.escape(status)}</td></tr>"
        for domain, status in country_profile.get('domain_states', {}).items()
    )
    annotation_ids = [str(item) for item in country_profile.get('annotations', [])]
    available_domain_targets = available_domain_targets or {}
    domain_link_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(domain)}</td>"
        f"<td><a href='{html.escape(target)}'>{html.escape(domain)} detail</a></td>"
        "</tr>"
        if target
        else "<tr>"
             f"<td>{html.escape(domain)}</td>"
             f"<td>{html.escape(domain)} — not available</td>"
             "</tr>"
        for domain, target in (
            (domain, available_domain_targets.get(domain))
            for domain in country_profile.get('domain_states', {}).keys()
        )
    )
    explanation_summary = country_profile.get('explanation_summary') or 'No explanation summary available.'
    country_context = country_profile.get('country_context', {})
    source_depth = country_profile.get('source_depth', {})
    domain_gap_summary = country_profile.get('domain_gap_summary', {})
    source_ids = [str(item) for item in source_depth.get('source_ids', [])]
    missing_domains = [str(item) for item in domain_gap_summary.get('missing_domains', [])]
    gap_details = [dict(item) for item in domain_gap_summary.get('gap_details', []) if isinstance(item, dict)]
    country_id = str(country_profile.get('country_id', 'UNKNOWN'))
    annotation_workflow_href = _annotation_workflow_href(
        nav_prefix=nav_prefix,
        scope='country',
        linked_item=country_id,
        annotation_type='context_note',
    )
    annotation_workflow_link_html = (
        f"<p><a href='{html.escape(annotation_workflow_href)}'>Open Annotation Workflow for this Country</a></p>"
        if annotations_view_model is not None and available_pages is not None and 'annotations.html' in available_pages
        else ''
    )
    # Pre-compute styled KPI values to avoid f-string quote conflicts
    _md_status = str(country_profile.get('multi_domain_status', 'S0'))
    _md_color = html.escape(_status_color(_md_status))
    _cov_band = _ratio_band(country_profile.get('coverage'))
    _con_band = _ratio_band(country_profile.get('confidence'))
    _cov_color = html.escape(_band_color(_cov_band))
    _con_color = html.escape(_band_color(_con_band))

    trust_summary_html = (
        "<h3>Trust / Uncertainty Summary</h3>"
        f"<p>Coverage band: <strong>{html.escape(_cov_band)}</strong> | Confidence band: <strong>{html.escape(_con_band)}</strong></p>"
        f"<h4>Coverage Meter</h4>{_render_metric_meter('Coverage', country_profile.get('coverage'), fill_color=_band_color(_cov_band))}"
        f"<h4>Confidence Meter</h4>{_render_metric_meter('Confidence', country_profile.get('confidence'), fill_color=_band_color(_con_band))}"
        f"<h4>Uncertainty Flags</h4><div>{_render_uncertainty_badges(country_profile.get('uncertainty', []))}</div>"
    )
    body = (
        # === KPI Header Zone ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Country</span><div class='kpi-value' style='font-size:1.1rem;'>{html.escape(str(country_profile.get('country_id', 'UNKNOWN')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Multi-Domain Status</span><div class='kpi-value' style='font-size:1rem;color:{_md_color}'>{html.escape(_md_status)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Priority</span><div class='kpi-value'>{html.escape(str(country_context.get('priority', 'n/a')))}</div><div class='kpi-sub'>{html.escape(str(country_context.get('region', 'n/a')))} · {html.escape(str(country_context.get('selection_type', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Coverage</span><div class='kpi-value' style='color:{_cov_color}'>{html.escape(_cov_band)}</div><div class='kpi-sub'>{html.escape(str(country_profile.get('coverage','n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Confidence</span><div class='kpi-value' style='color:{_con_color}'>{html.escape(_con_band)}</div><div class='kpi-sub'>{html.escape(str(country_profile.get('confidence','n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Sources</span><div class='kpi-value'>{html.escape(str(source_depth.get('source_count', 0)))}</div><div class='kpi-sub'>{html.escape(_source_depth_band(source_depth.get('source_count', 0)))}</div></div>"
        "</div>"
        # === Trust / Uncertainty ===
        "<div class='panel'><div class='panel-header'>Trust / Uncertainty</div>"
        f"{_render_metric_meter('Coverage', country_profile.get('coverage'), fill_color=_band_color(_cov_band))}"
        f"{_render_metric_meter('Confidence', country_profile.get('confidence'), fill_color=_band_color(_con_band))}"
        f"<div style='margin-top:8px;'>{_render_uncertainty_badges(country_profile.get('uncertainty', []))}</div>"
        "</div>"
        # === Domain States ===
        "<div class='panel'><div class='panel-header'>Domain States</div>"
        "<table><thead><tr><th>Domain</th><th>Status</th></tr></thead>"
        f"<tbody>{domain_rows}</tbody></table>"
        "<h3>Domain Deep Dives</h3>"
        "<table><thead><tr><th>Domain</th><th>Detail</th></tr></thead>"
        f"<tbody>{domain_link_rows}</tbody></table></div>"
        # === Explanation ===
        "<div class='panel'><div class='panel-header'>Analysis Path — Why is this country in this state?</div>"
        f"<p>{html.escape(str(explanation_summary))}</p>"
        f"<h3>Drivers</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('drivers', []))}</ul>"
        f"<h3>Counter Indicators</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('counter_indicators', []))}</ul>"
        f"<h3>Linked Events</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in country_profile.get('linked_events', []))}</ul>"
        "</div>"
        # === Source Depth & Gaps ===
        "<div class='panel'><div class='panel-header'>Source Depth &amp; Domain Gaps</div>"
        f"<p>Sources: <strong>{html.escape(str(source_depth.get('source_count', 0)))}</strong> | Depth: <strong>{html.escape(_source_depth_band(source_depth.get('source_count', 0)))}</strong></p>"
        f"<ul>{''.join(f'<li>{html.escape(item)}</li>' for item in source_ids) or '<li>none</li>'}</ul>"
        "<h3>Domain Gap Summary</h3>"
        f"<p>Expected: {html.escape(', '.join(str(item) for item in domain_gap_summary.get('expected_domains', [])) or 'none')} | "
        f"Observed: {html.escape(', '.join(str(item) for item in domain_gap_summary.get('observed_domains', [])) or 'none')} | "
        f"Missing: {_render_missing_domain_badges(missing_domains)}</p>"
        f"<h4>Gap Cause Details</h4>{_render_gap_details(gap_details, coverage_href_prefix='../coverage.html')}"
        "</div>"
        # === Annotations ===
        f"{annotation_workflow_link_html}"
        "<div class='panel'><div class='panel-header'>Analyst Annotations</div>"
        f"<p>Annotation IDs: {html.escape(', '.join(annotation_ids) or 'none')}</p>"
        f"{_annotation_details_html(annotation_ids, annotations_view_model)}"
        "</div>"
        # === Trends (collapsible) ===
        f"<details><summary>Trends (raw data)</summary>{_json_block(country_profile.get('trends', {}))}</details>"
    )
    return _page(f"Country Profile - {country_profile.get('country_id', 'UNKNOWN')}", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_domain_detail(domain_detail: dict[str, Any], annotations_view_model: dict[str, Any] | None = None, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    annotation_ids = [str(item) for item in domain_detail.get('annotations', [])]
    if not annotation_ids and annotations_view_model is not None:
        linked_item_key = f"{domain_detail.get('country_id', 'UNKNOWN')}:{domain_detail.get('domain', 'UNKNOWN')}"
        annotation_ids = [
            str(item)
            for item in annotations_view_model.get('by_linked_item', {}).get(linked_item_key, [])
        ]
    time_series = domain_detail.get('time_series', [])
    feature_values = domain_detail.get('feature_values', [])
    source_context = domain_detail.get('source_context', [])
    feature_rows = ''.join(
        "<tr class='domain-feature-row' "
        f"data-feature-id='{html.escape(str(item.get('feature_id', '')))}' "
        f"data-feature-coverage='{html.escape(str(item.get('coverage', '')))}'>"
        f"<td>{html.escape(str(item.get('feature_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('value', '')))}</td>"
        f"<td>{html.escape(str(item.get('coverage', '')))}</td>"
        "</tr>"
        for item in feature_values
    ) or "<tr><td colspan='3'>No feature values available.</td></tr>"
    source_rows = ''.join(
        "<tr class='domain-source-row' "
        f"data-source-id='{html.escape(str(item.get('source_id', '')))}'>"
        f"<td>{html.escape(str(item.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('status', '')))}</td>"
        f"<td>{html.escape(str(item.get('freshness_hours', '')))}</td>"
        f"<td>{html.escape(str(item.get('history_horizon', '')))}</td>"
        "</tr>"
        for item in source_context
    ) or "<tr><td colspan='4'>No source context available.</td></tr>"
    feature_options = ''.join(
        f"<option value='{html.escape(str(item.get('feature_id', '')))}'>{html.escape(str(item.get('feature_id', '')))}</option>"
        for item in feature_values
        if item.get('feature_id')
    )
    source_options = ''.join(
        f"<option value='{html.escape(str(item.get('source_id', '')))}'>{html.escape(str(item.get('source_id', '')))}</option>"
        for item in source_context
        if item.get('source_id')
    )
    domain_linked_item = f"{domain_detail.get('country_id', 'UNKNOWN')}:{domain_detail.get('domain', 'UNKNOWN')}"
    annotation_workflow_href = _annotation_workflow_href(
        nav_prefix=nav_prefix,
        scope='domain',
        linked_item=domain_linked_item,
        annotation_type='lineage_note',
    )
    annotation_workflow_link_html = (
        f"<p><a href='{html.escape(annotation_workflow_href)}'>Open Annotation Workflow for this Domain</a></p>"
        if annotations_view_model is not None and available_pages is not None and 'annotations.html' in available_pages
        else ''
    )
    body = (
        "<h2>Domain Detail</h2>"
        f"<p>Country: <strong>{html.escape(str(domain_detail.get('country_id', 'UNKNOWN')))}</strong></p>"
        f"<p>Domain: <strong>{html.escape(str(domain_detail.get('domain', 'UNKNOWN')))}</strong></p>"
        f"<p>Anomaly state: <span class='status'>{html.escape(str(domain_detail.get('anomaly_state', 'n/a')))}</span></p>"
        "<h3>Domain Deep-Dive Controls</h3>"
        "<label for='domain-feature-filter'>Feature:</label> "
        f"<select id='domain-feature-filter'><option value='all'>All features</option>{feature_options}</select> "
        "<label for='domain-source-filter'>Source:</label> "
        f"<select id='domain-source-filter'><option value='all'>All sources</option>{source_options}</select>"
        "<p>Visible features: <strong id='domain-feature-visible-count'>0</strong> | Visible sources: <strong id='domain-source-visible-count'>0</strong></p>"
        f"<h3>Time Series Chart</h3>{_render_line_chart(time_series, label_key='timestamp', chart_label='Domain time series') }"
        f"<h3>Time Series</h3>{_json_block(time_series)}"
        f"{_render_baseline_comparison_summary(domain_detail.get('baseline_comparison', {}), time_series)}"
        f"<h3>Raw Baseline Comparison Payload</h3>{_json_block(domain_detail.get('baseline_comparison', {}))}"
        "<h3>Feature Values Table</h3>"
        "<table><thead><tr><th>Feature ID</th><th>Value</th><th>Coverage</th></tr></thead>"
        f"<tbody>{feature_rows}</tbody></table>"
        "<h3>Source Context Table</h3>"
        "<table><thead><tr><th>Source ID</th><th>Status</th><th>Freshness (h)</th><th>History Horizon</th></tr></thead>"
        f"<tbody>{source_rows}</tbody></table>"
        f"<h3>Uncertainty</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in domain_detail.get('uncertainty', []))}</ul>"
        f"<h3>Annotation IDs</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in annotation_ids)}</ul>"
        f"{annotation_workflow_link_html}"
        f"<h3>Annotation Details</h3>{_annotation_details_html(annotation_ids, annotations_view_model)}"
        "<script>"
        "(function(){"
        "const featureFilter=document.getElementById('domain-feature-filter');"
        "const sourceFilter=document.getElementById('domain-source-filter');"
        "const featureRows=Array.from(document.querySelectorAll('.domain-feature-row'));"
        "const sourceRows=Array.from(document.querySelectorAll('.domain-source-row'));"
        "const featureCount=document.getElementById('domain-feature-visible-count');"
        "const sourceCount=document.getElementById('domain-source-visible-count');"
        "function applyDomainFilters(){"
        "const featureValue=featureFilter?featureFilter.value:'all';"
        "const sourceValue=sourceFilter?sourceFilter.value:'all';"
        "let featureVisible=0;"
        "let sourceVisible=0;"
        "featureRows.forEach((row)=>{const show=(featureValue==='all'||row.dataset.featureId===featureValue);row.style.display=show?'':'none';if(show)featureVisible+=1;});"
        "sourceRows.forEach((row)=>{const show=(sourceValue==='all'||row.dataset.sourceId===sourceValue);row.style.display=show?'':'none';if(show)sourceVisible+=1;});"
        "if(featureCount){featureCount.textContent=String(featureVisible);}"
        "if(sourceCount){sourceCount.textContent=String(sourceVisible);}"
        "}"
        "if(featureFilter){featureFilter.addEventListener('change',applyDomainFilters);}"
        "if(sourceFilter){sourceFilter.addEventListener('change',applyDomainFilters);}"
        "applyDomainFilters();"
        "})();"
        "</script>"
    )
    return _page(
        f"Domain Detail - {domain_detail.get('country_id', 'UNKNOWN')} / {domain_detail.get('domain', 'UNKNOWN')}",
        body,
        nav_prefix=nav_prefix,
        available_pages=available_pages,
    )


def _render_source_coverage(
    source_coverage_read_model: dict[str, Any],
    system_status_read_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    rows = ''.join(
        "<tr>"
        f"<td id='{html.escape(_source_anchor_id(str(source.get('source_id', ''))))}'>{html.escape(str(source.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(source.get('status', '')))}</td>"
        f"<td>{html.escape(str(source.get('history_horizon', '')))}</td>"
        f"<td>{html.escape(str(source.get('freshness_hours', '')))}</td>"
        f"<td>{html.escape(str(source.get('confidence', '')))}</td>"
        f"<td>{html.escape(str(source.get('record_count', '')))}</td>"
        f"<td>{html.escape(str(source.get('diagnostics', '')))}</td>"
        "</tr>"
        for source in source_coverage_read_model.get('sources', [])
    )
    matrix_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(source.get('source_id', '')))}</td>"
        f"<td>{html.escape(_ratio_band(source.get('confidence')))}</td>"
        f"<td>{_render_metric_meter('Confidence', source.get('confidence'), fill_color=_band_color(_ratio_band(source.get('confidence'))))}</td>"
        f"<td>{html.escape(str(source.get('freshness_hours', 'n/a')))}</td>"
        f"<td>{html.escape(str(source.get('status', '')))}</td>"
        "</tr>"
        for source in source_coverage_read_model.get('sources', [])
    ) or "<tr><td colspan='5'>No source metrics available.</td></tr>"
    system_status_read_model = system_status_read_model or {}
    coverage_visibility = _country_coverage_visibility_rows(system_status_read_model)
    trust_gaps = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in system_status_read_model.get('data_gaps', [])
    ) or "<li>none</li>"
    degraded_sources = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in source_coverage_read_model.get('degraded_sources', [])
    ) or "<li>none</li>"
    body = (
        "<h2>Source / Coverage View</h2>"
        "<h3>Trust Summary</h3>"
        f"<p>Run status: <span class='status'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</span></p>"
        f"<p>Status summary: {html.escape(str(source_coverage_read_model.get('source_status_summary', {})))}</p>"
        f"<h4>Data Gaps / Trust Limits</h4><ul>{trust_gaps}</ul>"
        f"<h4>Degraded Sources</h4><ul>{degraded_sources}</ul>"
        f"{_render_country_coverage_matrix(coverage_visibility)}"
        "<h3>Coverage / Confidence Matrix</h3>"
        "<p>Confidence Band highlights source trust at a glance while keeping freshness visible.</p>"
        "<table><thead><tr><th>Source</th><th>Confidence Band</th><th>Confidence Meter</th><th>Freshness (h)</th><th>Status</th></tr></thead>"
        f"<tbody>{matrix_rows}</tbody></table>"
        "<table><thead><tr><th>Source</th><th>Status</th><th>History Horizon</th><th>Freshness (h)</th><th>Confidence</th><th>Record Count</th><th>Diagnostics</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"<h3>Failed Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('failed_sources', []))}</ul>"
        f"<h3>Missing Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in source_coverage_read_model.get('missing_sources', []))}</ul>"
    )
    return _page("Source / Coverage View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _prepare_report_catalog(report_catalog: dict[str, Any], output_dir: Path) -> tuple[dict[str, dict[str, Any]], list[Path]]:
    prepared_catalog: dict[str, dict[str, Any]] = {}
    copied_files: list[Path] = []
    for report_type, report_info in sorted(report_catalog.items()):
        prepared_info = dict(report_info)
        prepared_exports: list[dict[str, Any]] = []
        for export_file in report_info.get('export_files', []):
            relative_path = Path(str(export_file.get('relative_path', f"exports/{Path(str(export_file.get('path', 'export'))).name}")))
            source_path = Path(str(export_file.get('path', '')))
            destination_path = output_dir / relative_path
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            if source_path.exists():
                shutil.copy2(source_path, destination_path)
                copied_files.append(destination_path)
            prepared_export = dict(export_file)
            prepared_export['href'] = relative_path.as_posix()
            prepared_exports.append(prepared_export)
        prepared_info['export_files'] = prepared_exports
        prepared_catalog[report_type] = prepared_info
    return prepared_catalog, copied_files


def _render_reports(report_catalog: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    def _render_export_links(report_info: dict[str, Any]) -> str:
        export_links = ''.join(
            (
                f"<div><a href=\"{html.escape(str(export_file.get('href', export_file.get('relative_path', ''))))}\">"
                f"{html.escape(str(export_file.get('label', export_file.get('format', 'download'))))}</a></div>"
            )
            for export_file in report_info.get('export_files', [])
        )
        return export_links or '-'

    report_types = sorted(report_catalog.keys())
    type_options = ''.join(
        f"<option value='{html.escape(report_type)}'>{html.escape(report_type)}</option>"
        for report_type in report_types
    )

    rows = ''.join(
        "<tr class='report-row' "
        f"data-report-type='{html.escape(report_type)}' "
        f"data-report-id='{html.escape(str(report_info.get('report_id', '')))}' "
        f"data-format='{html.escape(str(report_info.get('format', '')))}'>"
        f"<td>{html.escape(report_type)}</td>"
        f"<td>{html.escape(str(report_info.get('report_id', '')))}</td>"
        f"<td>{html.escape(str(report_info.get('format', '')))}</td>"
        f"<td>{_render_export_links(report_info)}</td>"
        f"<td>{html.escape(json.dumps({k: v for k, v in report_info.items() if k != 'export_files'}, sort_keys=True))}</td>"
        "</tr>"
        for report_type, report_info in sorted(report_catalog.items())
    )
    export_count = sum(len(report_info.get('export_files', [])) for report_info in report_catalog.values())
    evidence_items = ''.join(
        "<li>"
        f"{html.escape(str(report_info.get('report_id', report_type)))}"
        f" | snapshot={html.escape(str(report_info.get('snapshot_id', 'n/a')))}"
        f" | uncertainty={html.escape(', '.join(str(item) for item in report_info.get('uncertainty', [])) or 'none')}"
        f" | failed_sources={html.escape(', '.join(str(item) for item in report_info.get('failed_sources', [])) or 'none')}"
        "</li>"
        for report_type, report_info in sorted(report_catalog.items())
    ) or "<li>none</li>"
    filter_script = """
<script>
(function() {
  const typeFilter = document.getElementById('report-type-filter');
  const idFilter = document.getElementById('report-id-filter');
  const rows = Array.from(document.querySelectorAll('.report-row'));
  const visibleCount = document.getElementById('report-visible-count');

  function applyReportFilters() {
    const typeValue = (typeFilter?.value || '').trim().toLowerCase();
    const idValue = (idFilter?.value || '').trim().toLowerCase();
    let count = 0;

    rows.forEach((row) => {
      const rowType = (row.getAttribute('data-report-type') || '').toLowerCase();
      const rowId = (row.getAttribute('data-report-id') || '').toLowerCase();
      const typeOk = !typeValue || rowType === typeValue;
      const idOk = !idValue || rowId.includes(idValue);
      const show = typeOk && idOk;
      row.style.display = show ? '' : 'none';
      if (show) count += 1;
    });

    if (visibleCount) {
      visibleCount.textContent = String(count);
    }
  }

  if (typeFilter) typeFilter.addEventListener('change', applyReportFilters);
  if (idFilter) idFilter.addEventListener('input', applyReportFilters);
  applyReportFilters();
})();
</script>
"""
    body = (
        "<h2>Report / Export View</h2>"
        "<h3>Evidence Summary</h3>"
        f"<p>Reports available: <strong>{html.escape(str(len(report_catalog)))}</strong></p>"
        f"<p>Download-ready artifacts: <strong>{html.escape(str(export_count))}</strong></p>"
        f"<ul>{evidence_items}</ul>"
        "<h3>Report Scope Controls</h3>"
        "<p>Filter reports by type and report ID to focus export review scope.</p>"
        "<label for='report-type-filter'>Type:</label> "
        f"<select id='report-type-filter'><option value=''>All</option>{type_options}</select> "
        "<label for='report-id-filter'>Report ID contains:</label> "
        "<input id='report-id-filter' type='text' placeholder='e.g. REP-COVERAGE'/>"
        f"<p>Visible reports: <strong id='report-visible-count'>{html.escape(str(len(report_catalog)))}</strong></p>"
        "<table><thead><tr><th>Type</th><th>Report ID</th><th>Format</th><th>Downloads</th><th>Metadata</th></tr></thead>"
        f"<tbody>{rows}</tbody></table>"
        f"{filter_script}"
    )
    return _page("Report / Export View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_runs(system_status_read_model: dict[str, Any], repo_closure_view_model: dict[str, Any] | None = None, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    repo_closure_section = ""
    if repo_closure_view_model is not None:
        repo_closure_rows = ''.join(
            "<tr>"
            f"<td>{html.escape(str(slice_report.get('slice_id', '')))}</td>"
            f"<td>{html.escape(str(slice_report.get('summary', {}).get('closed', 'n/a')))}</td>"
            f"<td>{html.escape(str(slice_report.get('summary', {}).get('at_risk', 'n/a')))}</td>"
            "</tr>"
            for slice_report in repo_closure_view_model.get('slices', [])
        )
        summary = repo_closure_view_model.get('summary', {})
        repo_closure_section = (
            "<h3>Repo Closure Summary</h3>"
            f"<p>Slices: <strong>{html.escape(str(summary.get('slice_count', 'n/a')))}</strong></p>"
            f"<p>Requirements: <strong>{html.escape(str(summary.get('requirement_count', 'n/a')))}</strong></p>"
            f"<p>Closed: <strong>{html.escape(str(summary.get('closed', 'n/a')))}</strong> | At risk: <strong>{html.escape(str(summary.get('at_risk', 'n/a')))}</strong></p>"
            "<table><thead><tr><th>Slice</th><th>Closed</th><th>At Risk</th></tr></thead>"
            f"<tbody>{repo_closure_rows}</tbody></table>"
        )
    _run_color = html.escape(_run_status_color(str(system_status_read_model.get('run_status', 'n/a'))))
    body = (
        # === KPI Header ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Run ID</span><div class='kpi-value' style='font-size:0.85rem;'>{html.escape(str(system_status_read_model.get('run_id', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Run Status</span><div class='kpi-value' style='color:{_run_color}'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Last Run</span><div class='kpi-value' style='font-size:0.8rem;'>{html.escape(str(system_status_read_model.get('last_run', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Snapshot</span><div class='kpi-value' style='font-size:0.8rem;color:#6b7d99;'>{html.escape(str(system_status_read_model.get('snapshot_id', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Reprocessing</span><div class='kpi-value' style='font-size:0.8rem;'>{html.escape(str(system_status_read_model.get('reprocessing_status', 'n/a')))}</div></div>"
        "</div>"
        # === Coverage ===
        "<div class='panel'><div class='panel-header'>Coverage</div>"
        f"<details><summary>Coverage Details</summary>{_json_block(system_status_read_model.get('coverage', {}))}</details>"
        "</div>"
        # === Issues ===
        "<div class='panel'><div class='panel-header'>Failed Sources &amp; Available Reports</div>"
        f"<h3>Failed Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in system_status_read_model.get('failed_sources', []))}</ul>"
        f"<h3>Available Reports</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in system_status_read_model.get('available_reports', []))}</ul>"
        "</div>"
        f"{repo_closure_section}"
    )
    return _page("System Status / Runs", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_readiness(readiness_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    def _artifact_status_text(check: dict[str, Any]) -> str:
        status = str(check.get('status', 'unknown'))
        reason = check.get('reason')
        return status if not reason else f"{status} ({reason})"

    demo_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('label', '')))}</td>"
        f"<td>{html.escape('ready' if bool(check.get('ready')) else 'missing')}</td>"
        "</tr>"
        for check in readiness_view_model.get('demo_checks', [])
    )
    evidence_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('label', '')))}</td>"
        f"<td>{html.escape('ready' if bool(check.get('ready')) else 'missing')}</td>"
        "</tr>"
        for check in readiness_view_model.get('evidence_checks', [])
    )
    artifact_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(check.get('artifact', '')))}</td>"
        f"<td>{html.escape(_artifact_status_text(check))}</td>"
        "</tr>"
        for check in readiness_view_model.get('artifact_checks', [])
    )
    known_gap_items = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in readiness_view_model.get('known_gaps', [])
    ) or "<li>none</li>"
    _demo_v = str(readiness_view_model.get('demo_verdict', 'n/a'))
    _rel_v = str(readiness_view_model.get('release_verdict', 'n/a'))
    _demo_ok = _demo_v.lower() in ('ready', 'pass', 'ok', 'green')
    _rel_ok = _rel_v.lower() in ('ready', 'pass', 'ok', 'green')
    _demo_color = '#4edea3' if _demo_ok else ('#e3b341' if 'partial' in _demo_v.lower() else '#ffb4ab')
    _rel_color = '#4edea3' if _rel_ok else ('#e3b341' if 'partial' in _rel_v.lower() else '#ffb4ab')

    body = (
        # === KPI Header ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Demo Verdict</span><div class='kpi-value' style='color:{_demo_color}'>{html.escape(_demo_v)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Release Verdict</span><div class='kpi-value' style='color:{_rel_color}'>{html.escape(_rel_v)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Country Profiles</span><div class='kpi-value'>{html.escape(str(readiness_view_model.get('country_profile_count', 0)))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Domain Details</span><div class='kpi-value'>{html.escape(str(readiness_view_model.get('domain_detail_count', 0)))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Reports</span><div class='kpi-value'>{html.escape(str(readiness_view_model.get('report_count', 0)))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Run ID</span><div class='kpi-value' style='font-size:0.75rem;color:#6b7d99;'>{html.escape(str(readiness_view_model.get('run_id', 'n/a')))}</div></div>"
        "</div>"
        # === Checklists ===
        "<div class='panel'><div class='panel-header'>Demo Flow Checklist</div>"
        "<table><thead><tr><th>Flow Step</th><th>Status</th></tr></thead>"
        f"<tbody>{demo_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Evidence Checklist</div>"
        "<table><thead><tr><th>Evidence</th><th>Status</th></tr></thead>"
        f"<tbody>{evidence_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Artifact Readiness</div>"
        "<table><thead><tr><th>Artifact</th><th>Status</th></tr></thead>"
        f"<tbody>{artifact_rows}</tbody></table></div>"
        # === Known Gaps ===
        "<div class='panel'><div class='panel-header'>Known Gaps Before Release</div>"
        f"<ul>{known_gap_items}</ul></div>"
    )
    return _page("Demo / Release Readiness", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_trends(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    country_options = []
    trend_options = _trend_filter_options(country_profile_read_models)
    trend_option_tags = ''.join(
        f"<option value='{html.escape(label)}'>{html.escape(label)}</option>"
        for label in trend_options
    )
    for country_id, profile in sorted(country_profile_read_models.items()):
        yearly = profile.get('trends', {}).get('yearly', [])
        labels = ','.join(_trend_labels(yearly, label_key='label'))
        event_ids = [str(item) for item in profile.get('linked_events', [])]
        event_overlay = ''.join(f"<li>{html.escape(event_id)}</li>" for event_id in event_ids) or "<li>none</li>"
        rows.append(
            f"<tr class='trend-row' data-country-id='{html.escape(country_id)}' data-trend-labels='{html.escape(labels)}' data-event-ids='{html.escape(','.join(event_ids))}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td><div class='trend-chart-block'><h4>Trend Chart</h4>{_render_line_chart(yearly, label_key='label', chart_label=f'{country_id} yearly trend')}{_render_historical_comparison_summary(yearly, label_key='label')}</div><div class='trend-event-overlay' style='display:none'><h4>Event Overlay Summary</h4><ul>{event_overlay}</ul></div></td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            "</tr>"
        )
        country_options.append(f"<option value='{html.escape(country_id)}'>{html.escape(country_id)}</option>")
    body = (
        "<h2>Yearly Trend Page</h2>"
        "<h3>Trend Controls</h3>"
        "<label for='trend-country-filter'>Country Filter</label> "
        "<select id='trend-country-filter' name='trend-country-filter'><option value='all'>All countries</option>"
        f"{''.join(country_options)}</select> "
        "<label for='trend-time-window'>Time Window</label> "
        "<select id='trend-time-window' name='trend-time-window'><option value='all'>All labels</option>"
        f"{trend_option_tags}</select> "
        "<label for='trend-view-mode'>Trend View Mode</label> "
        "<select id='trend-view-mode' name='trend-view-mode'><option value='chart'>Chart view</option><option value='events'>Event overlay view</option></select>"
        "<p id='trend-filter-result'>Selected Trend Window: all labels</p>"
        "<table id='trend-table'><thead><tr><th>Country</th><th>Yearly Trend</th><th>Current Multi-Domain Status</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<script>"
        "function applyTrendViewMode(){"
        "const mode=document.getElementById('trend-view-mode').value;"
        "document.querySelectorAll('.trend-row').forEach((row)=>{"
        "const chart=row.querySelector('.trend-chart-block');"
        "const overlay=row.querySelector('.trend-event-overlay');"
        "if(chart){chart.style.display=mode==='events'?'none':'';}"
        "if(overlay){overlay.style.display=mode==='events'?'':'none';}"
        "});"
        "}"
        "function applyTrendFilters(){"
        "const country=document.getElementById('trend-country-filter').value;"
        "const windowValue=document.getElementById('trend-time-window').value;"
        "document.querySelectorAll('.trend-row').forEach((row)=>{"
        "const labels=(row.dataset.trendLabels||'').split(',').filter(Boolean);"
        "const matchesCountry=(country==='all'||row.dataset.countryId===country);"
        "const matchesWindow=(windowValue==='all'||labels.includes(windowValue));"
        "row.style.display=(matchesCountry&&matchesWindow)?'':'none';"
        "});"
        "applyTrendViewMode();"
        "document.getElementById('trend-filter-result').textContent='Selected Trend Window: '+windowValue;"
        "}"
        "document.getElementById('trend-country-filter').addEventListener('change', applyTrendFilters);"
        "document.getElementById('trend-time-window').addEventListener('change', applyTrendFilters);"
        "document.getElementById('trend-view-mode').addEventListener('change', applyTrendViewMode);"
        "applyTrendFilters();"
        "</script>"
    )
    return _page("Yearly Trend Page", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_events(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    country_options = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        country_options.append(f"<option value='{html.escape(country_id)}'>{html.escape(country_id)}</option>")
        for event_id in profile.get('linked_events', []):
            rows.append(
                f"<tr class='event-row' data-country-id='{html.escape(country_id)}' data-event-id='{html.escape(str(event_id))}'>"
                f"<td>{html.escape(country_id)}</td>"
                f"<td>{html.escape(str(event_id))}</td>"
                f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
                "</tr>"
            )
    body = (
        # === KPI Header ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Countries</span><div class='kpi-value'>{html.escape(str(len(country_profile_read_models)))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Total Events</span><div class='kpi-value'>{html.escape(str(sum(len(p.get('linked_events',[])) for p in country_profile_read_models.values())))}</div></div>"
        "</div>"
        "<div class='panel'><div class='panel-header'>Event Controls</div>"
        "<div class='controls-bar'>"
        "<label for='event-country-filter'>Country</label>"
        "<select id='event-country-filter' name='event-country-filter'><option value='all'>All countries</option>"
        f"{''.join(country_options)}</select>"
        "<span id='event-filter-result' style='font-size:11px;color:#6b7d99;font-family:Space Grotesk,monospace;'></span>"
        "</div></div>"
        "<div class='panel'><div class='panel-header'>Event List</div>"
        "<div class='table-container'><table id='event-table'><thead><tr>"
        "<th>Country</th><th>Event ID</th><th>Context Status</th>"
        "</tr></thead><tbody>"
        + ("".join(rows) if rows else "<tr><td colspan=3 style='color:#6b7d99;'>No events recorded in current dataset.</td></tr>")
        + "</tbody></table></div></div>"
        "<script>"
        "function applyEventFilters(){"
        "const country=document.getElementById('event-country-filter').value;"
        "document.querySelectorAll('.event-row').forEach((row)=>{"
        "const show=(country==='all'||row.dataset.countryId===country);"
        "row.style.display=show?'':'none';"
        "});"
        "var n=document.querySelectorAll('.event-row:not([style*=none])').length;"
        "document.getElementById('event-filter-result').textContent=n+' event'+(n!==1?'s':'')+(country!=='all'?' for '+country:'');"
        "}"
        "document.getElementById('event-country-filter').addEventListener('change', applyEventFilters);"
        "applyEventFilters();"
        "</script>"
    )
    return _page("Current Events Page", body, nav_prefix=nav_prefix, available_pages=available_pages)



def _render_comparison(country_profile_read_models: dict[str, dict[str, Any]], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        domain_states = profile.get('domain_states', {})
        coverage_band = _ratio_band(profile.get('coverage'))
        confidence_band = _ratio_band(profile.get('confidence'))
        uncertainty_count = len(profile.get('uncertainty', []))
        rows.append(
            f"<tr class='comparison-row' data-country-id='{html.escape(country_id)}' data-coverage-band='{html.escape(coverage_band)}' data-confidence-band='{html.escape(confidence_band)}' data-uncertainty-count='{uncertainty_count}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            f"<td>{html.escape(', '.join(f'{domain}:{status}' for domain, status in sorted(domain_states.items())))}</td>"
            f"<td>{_render_metric_meter('Coverage', profile.get('coverage'), fill_color=_band_color(coverage_band))}</td>"
            f"<td>{_render_metric_meter('Confidence', profile.get('confidence'), fill_color=_band_color(confidence_band))}</td>"
            f"<td>{html.escape(', '.join(str(item) for item in profile.get('drivers', [])))}</td>"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "</tr>"
        )
    body = (
        "<h2>Cross-Country Comparison</h2>"
        "<h3>Comparison controls</h3>"
        "<label for='comparison-filter'>Coverage / Uncertainty Focus</label> "
        "<select id='comparison-filter' name='comparison-filter'>"
        "<option value='all'>All countries</option>"
        "<option value='low_coverage'>Low coverage only</option>"
        "<option value='low_confidence'>Low confidence only</option>"
        "<option value='has_uncertainty'>With uncertainty flags</option>"
        "</select>"
        "<p id='comparison-filter-result'>Selected Comparison Filter: all countries</p>"
        "<h3>Coverage / Confidence Comparison</h3>"
        "<table><thead><tr><th>Country</th><th>Multi-Domain Status</th><th>Domain States</th><th>Coverage</th><th>Confidence</th><th>Drivers</th><th>Uncertainty</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        "<script>"
        "function applyComparisonFilters(){"
        "const mode=document.getElementById('comparison-filter').value;"
        "document.querySelectorAll('.comparison-row').forEach((row)=>{"
        "const lowCoverage=row.dataset.coverageBand==='low';"
        "const lowConfidence=row.dataset.confidenceBand==='low';"
        "const hasUncertainty=Number(row.dataset.uncertaintyCount||'0')>0;"
        "const show=(mode==='all'||(mode==='low_coverage'&&lowCoverage)||(mode==='low_confidence'&&lowConfidence)||(mode==='has_uncertainty'&&hasUncertainty));"
        "row.style.display=show?'':'none';"
        "});"
        "document.getElementById('comparison-filter-result').textContent='Selected Comparison Filter: '+mode;"
        "}"
        "document.getElementById('comparison-filter').addEventListener('change', applyComparisonFilters);"
        "applyComparisonFilters();"
        "</script>"
    )
    return _page("Cross-Country Comparison", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_validation(validation_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    time_range = validation_view_model.get('time_range', {})
    reprocessing = validation_view_model.get('reprocessing_comparison', {})
    expected_domains = [str(item) for item in validation_view_model.get('expected_domains', [])]
    observed_domains = [str(item) for item in validation_view_model.get('observed_domains', [])]
    missing_expected_domain_values = validation_view_model.get('missing_expected_domains')
    if missing_expected_domain_values is None:
        missing_expected_domain_values = [domain for domain in expected_domains if domain not in observed_domains]
    unexpected_observed_domain_values = validation_view_model.get('unexpected_observed_domains')
    if unexpected_observed_domain_values is None:
        unexpected_observed_domain_values = [domain for domain in observed_domains if domain not in expected_domains]
    review_verdict = validation_view_model.get('review_verdict')
    if review_verdict is None:
        status_match = validation_view_model.get('status_match')
        if status_match and not missing_expected_domain_values and not unexpected_observed_domain_values:
            review_verdict = 'match'
        elif status_match:
            review_verdict = 'match_with_gaps'
        else:
            review_verdict = 'mismatch'
    validation_cases = [item for item in validation_view_model.get('validation_cases', []) if isinstance(item, dict)]
    portfolio_summary = validation_view_model.get('portfolio_summary', {}) if isinstance(validation_view_model.get('portfolio_summary', {}), dict) else {}
    reference_case_library = [item for item in validation_view_model.get('reference_case_library', []) if isinstance(item, dict)]
    reference_case_library_summary = (
        validation_view_model.get('reference_case_library_summary', {})
        if isinstance(validation_view_model.get('reference_case_library_summary', {}), dict)
        else {}
    )
    historical_reference_reviews = [
        item for item in validation_view_model.get('historical_reference_reviews', []) if isinstance(item, dict)
    ]
    historical_reference_review_summary = (
        validation_view_model.get('historical_reference_review_summary', {})
        if isinstance(validation_view_model.get('historical_reference_review_summary', {}), dict)
        else {}
    )
    historical_replay_reviews = [
        item for item in validation_view_model.get('historical_replay_reviews', []) if isinstance(item, dict)
    ]
    historical_replay_summary = (
        validation_view_model.get('historical_replay_summary', {})
        if isinstance(validation_view_model.get('historical_replay_summary', {}), dict)
        else {}
    )
    if historical_replay_reviews and not historical_replay_summary.get('attention_cases'):
        historical_replay_summary = {
            **historical_replay_summary,
            **build_historical_replay_summary(historical_replay_reviews),
        }
    verdict_count_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((portfolio_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No portfolio verdict counts.</td></tr>"
    portfolio_case_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('expected_domains', [])))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('observed_domains', [])))}</td>"
        "</tr>"
        for case in validation_cases
    ) or "<tr><td colspan='5'>No portfolio cases available.</td></tr>"
    reference_case_type_rows = ''.join(
        f"<tr><td>{html.escape(str(case_type))}</td><td>{html.escape(str(count))}</td></tr>"
        for case_type, count in sorted((reference_case_library_summary.get('case_type_counts') or {}).items())
    ) or "<tr><td colspan='2'>No case types recorded.</td></tr>"
    reference_case_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_type', 'n/a')))}</td>"
        f"<td>{html.escape(str(case.get('case_name', 'n/a')))}</td>"
        f"<td>{html.escape(str((case.get('time_range') or {}).get('start', 'n/a')))} to {html.escape(str((case.get('time_range') or {}).get('end', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in case.get('expected_domains', [])))}</td>"
        "</tr>"
        for case in reference_case_library
    ) or "<tr><td colspan='6'>No curated reference cases recorded.</td></tr>"
    historical_reference_verdict_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((historical_reference_review_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No historical review verdicts recorded.</td></tr>"
    historical_reference_tier_rows = ''.join(
        f"<tr><td>{html.escape(str(tier))}</td><td>{html.escape(str(count))}</td></tr>"
        for tier, count in sorted((historical_reference_review_summary.get('evidence_tier_counts') or {}).items())
    ) or "<tr><td colspan='2'>No evidence tiers recorded.</td></tr>"
    historical_reference_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('evidence_score', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('expected_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('historical_observed_status', 'n/a')))}</td>"
        "</tr>"
        for review in historical_reference_reviews
    ) or "<tr><td colspan='7'>No historical reference reviews recorded.</td></tr>"
    historical_replay_verdict_rows = ''.join(
        f"<tr><td>{html.escape(str(verdict))}</td><td>{html.escape(str(count))}</td></tr>"
        for verdict, count in sorted((historical_replay_summary.get('review_verdict_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay verdicts recorded.</td></tr>"
    historical_replay_basis_rows = ''.join(
        f"<tr><td>{html.escape(str(basis))}</td><td>{html.escape(str(count))}</td></tr>"
        for basis, count in sorted((historical_replay_summary.get('review_basis_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay bases recorded.</td></tr>"
    historical_replay_source_coverage_rows = ''.join(
        f"<tr><td>{html.escape(str(source_id))}</td><td>{html.escape(str(count))}</td></tr>"
        for source_id, count in sorted((historical_replay_summary.get('replay_input_source_coverage_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay source coverage recorded.</td></tr>"
    historical_replay_evidence_tier_rows = ''.join(
        f"<tr><td>{html.escape(str(tier))}</td><td>{html.escape(str(count))}</td></tr>"
        for tier, count in sorted((historical_replay_summary.get('replay_evidence_tier_counts') or {}).items())
    ) or "<tr><td colspan='2'>No replay evidence tiers recorded.</td></tr>"
    replay_attention_level_rows = ''.join(
        f"<tr><td>{html.escape(str(level))}</td><td>{html.escape(str(count))}</td></tr>"
        for level, count in sorted((historical_replay_summary.get('attention_level_counts') or {}).items())
    ) or "<tr><td colspan='2'>No attention levels recorded.</td></tr>"
    replay_attention_reason_rows = ''.join(
        f"<tr><td>{html.escape(str(reason))}</td><td>{html.escape(str(count))}</td></tr>"
        for reason, count in sorted((historical_replay_summary.get('attention_reason_counts') or {}).items())
    ) or "<tr><td colspan='2'>No attention reasons recorded.</td></tr>"
    replay_attention_owner_rows = ''.join(
        f"<tr><td>{html.escape(str(owner))}</td><td>{html.escape(str(count))}</td></tr>"
        for owner, count in sorted((historical_replay_summary.get('attention_owner_counts') or {}).items())
    ) or "<tr><td colspan='2'>No follow-up owners recorded.</td></tr>"
    replay_attention_country_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_case_count', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('highest_attention_level', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(case_id) for case_id in item.get('case_ids', [])) or 'none')}</td>"
        "</tr>"
        for item in historical_replay_summary.get('attention_country_summary', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='4'>No country attention summary recorded.</td></tr>"
    replay_attention_rows = ''.join(
        "<tr class='replay-attention-row'"
        f" data-attention-level='{html.escape(str(item.get('attention_level', 'n/a')).lower())}'"
        f" data-attention-owner='{html.escape(str(item.get('owner_hint', 'n/a')).lower())}'"
        f" data-attention-reason='{html.escape(str(item.get('attention_reason', 'n/a')).lower())}'>"
        f"<td>{html.escape(str(item.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_level', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('attention_reason', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('owner_hint', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('replay_evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape('missing=' + (', '.join(str(domain) for domain in item.get('missing_expected_domains', [])) or 'none') + '; unexpected=' + (', '.join(str(domain) for domain in item.get('unexpected_observed_domains', [])) or 'none'))}</td>"
        f"<td>{html.escape(str(item.get('suggested_next_action', 'n/a')))}</td>"
        "</tr>"
        for item in historical_replay_summary.get('attention_cases', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='9'>No replay attention cases recorded.</td></tr>"
    historical_replay_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('review_basis', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_evidence_tier', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_evidence_score', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in review.get('replay_input_source_ids', [])))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in review.get('archival_data_files', [])))}</td>"
        f"<td>{html.escape(str(review.get('expected_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replayed_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('domain_match_ratio', 'n/a')))}</td>"
        f"<td>{html.escape(str(review.get('replay_input_record_count', 'n/a')))}</td>"
        "</tr>"
        for review in historical_replay_reviews
    ) or "<tr><td colspan='12'>No historical replay reviews recorded.</td></tr>"
    changed_versions = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in reprocessing.get('changed_versions', [])
    ) or "<li>none</li>"
    missing_expected_domains = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in missing_expected_domain_values
    ) or "<li>none</li>"
    unexpected_observed_domains = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in unexpected_observed_domain_values
    ) or "<li>none</li>"
    body = (
        "<h2>Validation / Backtest View</h2>"
        f"<p>Case ID: <strong>{html.escape(str(validation_view_model.get('case_id', 'n/a')))}</strong></p>"
        f"<p>Country: <strong>{html.escape(str(validation_view_model.get('country_id', 'n/a')))}</strong></p>"
        f"<p>Case: {html.escape(str(validation_view_model.get('case_name', 'n/a')))}</p>"
        f"<p>Time Range: {html.escape(str(time_range.get('start', 'n/a')))} to {html.escape(str(time_range.get('end', 'n/a')))}</p>"
        "<h3>Review Summary</h3>"
        f"<p>Review verdict: <strong>{html.escape(str(review_verdict))}</strong></p>"
        f"<p>Expected Domains: {html.escape(', '.join(expected_domains))}</p>"
        f"<p>Observed Domains: {html.escape(', '.join(observed_domains))}</p>"
        f"<p>Domain Match Ratio: {html.escape(str(validation_view_model.get('domain_match_ratio', 'n/a')))}</p>"
        f"<p>Status Match: {html.escape(str(validation_view_model.get('status_match', 'n/a')))}</p>"
        f"<h4>Missing Expected Domains</h4><ul>{missing_expected_domains}</ul>"
        f"<h4>Unexpected Observed Domains</h4><ul>{unexpected_observed_domains}</ul>"
        f"<h3>Expected Pattern</h3><p>{html.escape(str(validation_view_model.get('expected_pattern', 'n/a')))}</p>"
        f"<h3>Validation Goal</h3><p>{html.escape(str(validation_view_model.get('validation_goal', 'n/a')))}</p>"
        f"<h3>Reference Sources</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('reference_sources', []))}</ul>"
        f"<h3>Validation Metrics</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('validation_metrics', []))}</ul>"
        f"<h3>Known Limitations</h3><ul>{''.join(f'<li>{html.escape(str(item))}</li>' for item in validation_view_model.get('known_limitations', []))}</ul>"
        "<h3>Reference Case Portfolio Summary</h3>"
        f"<p>Validation Cases: <strong>{html.escape(str(portfolio_summary.get('case_count', len(validation_cases))))}</strong></p>"
        f"<p>Countries Covered: {html.escape(', '.join(str(item) for item in portfolio_summary.get('countries_covered', [])))}</p>"
        "<table><thead><tr><th>Review Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{verdict_count_rows}</tbody></table>"
        "<h3>Validation Case Portfolio</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Review Verdict</th><th>Expected Domains</th><th>Observed Domains</th></tr></thead>"
        f"<tbody>{portfolio_case_rows}</tbody></table>"
        "<h3>Curated Reference Case Library</h3>"
        f"<p>Library Cases: <strong>{html.escape(str(reference_case_library_summary.get('case_count', len(reference_case_library))))}</strong></p>"
        f"<p>Countries Covered: {html.escape(', '.join(str(item) for item in reference_case_library_summary.get('countries_covered', [])))}</p>"
        f"<p>Library Time Range: {html.escape(str((reference_case_library_summary.get('time_range') or {}).get('start', 'n/a')))} to {html.escape(str((reference_case_library_summary.get('time_range') or {}).get('end', 'n/a')))}</p>"
        "<table><thead><tr><th>Case Type</th><th>Count</th></tr></thead>"
        f"<tbody>{reference_case_type_rows}</tbody></table>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Case Type</th><th>Case</th><th>Time Range</th><th>Expected Domains</th></tr></thead>"
        f"<tbody>{reference_case_rows}</tbody></table>"
        "<h3>Historical Reference Review Summary</h3>"
        f"<p>Average Evidence Score: <strong>{html.escape(str(historical_reference_review_summary.get('average_evidence_score', 'n/a')))}</strong></p>"
        "<table><thead><tr><th>Review Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_reference_verdict_rows}</tbody></table>"
        "<table><thead><tr><th>Evidence Tier</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_reference_tier_rows}</tbody></table>"
        "<h3>Historical Reference Reviews</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Review Verdict</th><th>Evidence Tier</th><th>Evidence Score</th><th>Expected Status</th><th>Historical Observed Status</th></tr></thead>"
        f"<tbody>{historical_reference_rows}</tbody></table>"
        "<h3>Historical Replay Summary</h3>"
        f"<p>Average Domain Match Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_domain_match_ratio', 'n/a')))}</strong></p>"
        f"<p>Status Match Count: <strong>{html.escape(str(historical_replay_summary.get('status_match_count', 'n/a')))}</strong></p>"
        f"<p>Average Replay Evidence Score: <strong>{html.escape(str(historical_replay_summary.get('average_replay_evidence_score', 'n/a')))}</strong></p>"
        f"<p>Average Replay Source Coverage Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_replay_source_coverage_ratio', 'n/a')))}</strong></p>"
        f"<p>Average Replay Provenance Completeness Ratio: <strong>{html.escape(str(historical_replay_summary.get('average_replay_provenance_completeness_ratio', 'n/a')))}</strong></p>"
        f"<p>Replay Input Record Total: <strong>{html.escape(str(historical_replay_summary.get('replay_input_record_total', 'n/a')))}</strong></p>"
        f"<p>Archival Data Files: <strong>{html.escape(str(historical_replay_summary.get('archival_data_file_count', 'n/a')))}</strong></p>"
        "<table><thead><tr><th>Replay Verdict</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_verdict_rows}</tbody></table>"
        "<table><thead><tr><th>Replay Basis</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_basis_rows}</tbody></table>"
        "<h4>Replay Evidence Tiers</h4>"
        "<table><thead><tr><th>Evidence Tier</th><th>Count</th></tr></thead>"
        f"<tbody>{historical_replay_evidence_tier_rows}</tbody></table>"
        "<h4>Replay Source Coverage</h4>"
        "<table><thead><tr><th>Source</th><th>Case Count</th></tr></thead>"
        f"<tbody>{historical_replay_source_coverage_rows}</tbody></table>"
        "<h4>Replay Attention Summary</h4>"
        "<table><thead><tr><th>Attention Level</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_level_rows}</tbody></table>"
        "<table><thead><tr><th>Reason</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_reason_rows}</tbody></table>"
        "<table><thead><tr><th>Follow-up Owner</th><th>Count</th></tr></thead>"
        f"<tbody>{replay_attention_owner_rows}</tbody></table>"
        "<h5>Attention by Country</h5>"
        "<table><thead><tr><th>Country</th><th>Attention Cases</th><th>Highest Attention Level</th><th>Case IDs</th></tr></thead>"
        f"<tbody>{replay_attention_country_rows}</tbody></table>"
        "<h4>Replay Attention Watchlist</h4>"
        f"<p>Attention Cases: <strong>{html.escape(str(historical_replay_summary.get('attention_case_count', 0)))}</strong></p>"
        "<div><label for='replay-attention-level-filter'>Attention level:</label> "
        "<input id='replay-attention-level-filter' type='text' placeholder='e.g. high'/> "
        "<label for='replay-attention-owner-filter'>Owner:</label> "
        "<input id='replay-attention-owner-filter' type='text' placeholder='e.g. validation governance'/> "
        "<label for='replay-attention-reason-filter'>Reason:</label> "
        "<input id='replay-attention-reason-filter' type='text' placeholder='e.g. domain_coverage_gap'/> "
        "<label for='replay-attention-text-filter'>Search:</label> "
        "<input id='replay-attention-text-filter' type='text' placeholder='country, case, action...'/> "
        "<label for='replay-attention-sort'>Sort:</label> "
        "<select id='replay-attention-sort'><option value='default'>Default</option><option value='level-desc'>Level (high→low)</option><option value='level-asc'>Level (low→high)</option><option value='country-asc'>Country (A→Z)</option><option value='case-asc'>Case ID (A→Z)</option></select> "
        "<button id='replay-attention-reset' type='button'>Reset filters</button> "
        "<button id='replay-attention-export-csv' type='button'>Export visible as CSV</button> "
        "<button id='replay-attention-copy-csv' type='button'>Copy visible CSV</button> "
        "<button id='replay-attention-copy-link' type='button'>Copy filter link</button> "
        "<span id='replay-attention-copy-status'></span> "
        "<span id='replay-attention-link-status'></span> "
        "<label for='replay-attention-preset'>Quick preset:</label> "
        "<select id='replay-attention-preset'><option value='none'>None</option><option value='high-only'>High only</option><option value='governance-only'>Governance only</option><option value='domain-gap-only'>Domain gap only</option></select> "
        "<span id='replay-attention-visible-count'></span> "
        "<span id='replay-attention-visible-breakdown'></span></div>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Attention Level</th><th>Reason</th><th>Follow-up Owner</th><th>Replay Verdict</th><th>Replay Evidence Tier</th><th>Gap Signals</th><th>Suggested Next Action</th></tr></thead>"
        f"<tbody>{replay_attention_rows}</tbody></table>"
        "<script>"
        "(function(){"
        "const levelInput=document.getElementById('replay-attention-level-filter');"
        "const ownerInput=document.getElementById('replay-attention-owner-filter');"
        "const reasonInput=document.getElementById('replay-attention-reason-filter');"
        "const textInput=document.getElementById('replay-attention-text-filter');"
        "const sortSelect=document.getElementById('replay-attention-sort');"
        "const resetButton=document.getElementById('replay-attention-reset');"
        "const exportCsvButton=document.getElementById('replay-attention-export-csv');"
        "const copyCsvButton=document.getElementById('replay-attention-copy-csv');"
        "const copyLinkButton=document.getElementById('replay-attention-copy-link');"
        "const copyStatus=document.getElementById('replay-attention-copy-status');"
        "const linkStatus=document.getElementById('replay-attention-link-status');"
        "const presetSelect=document.getElementById('replay-attention-preset');"
        "const countEl=document.getElementById('replay-attention-visible-count');"
        "const breakdownEl=document.getElementById('replay-attention-visible-breakdown');"
        "const rows=Array.from(document.querySelectorAll('tr.replay-attention-row'));"
        "const levelRank={high:3,medium:2,low:1};"
        "const defaultOrder=rows.slice();"
        "const tbody=(rows[0]&&rows[0].parentElement)||null;"
        "function rowCellValue(row,index){const cell=row.cells[index];return (cell&&cell.textContent||'').trim().toLowerCase();}"
        "function csvEscape(value){const text=String(value||'');if(/[\",\n]/.test(text)){return '"'+text.replace(/"/g,'""')+'"';}return text;}"
        "function exportVisibleReplayAttentionCsv(){"
        "const visibleRows=rows.filter(function(row){return row.style.display!=='none';});"
        "const header=['country_id','case_id','attention_level','attention_reason','owner_hint','review_verdict','replay_evidence_tier','gap_signals','suggested_next_action'];"
        "const lines=[header.join(',')];"
        "visibleRows.forEach(function(row){"
        "const cols=Array.from(row.cells).map(function(cell){return (cell&&cell.textContent||'').trim();});"
        "lines.push(cols.map(csvEscape).join(','));"
        "});"
        "const csvContent=lines.join('\\n');"
        "const blob=new Blob([csvContent],{type:'text/csv;charset=utf-8;'});"
        "const url=URL.createObjectURL(blob);"
        "const link=document.createElement('a');"
        "const preset=(presetSelect&&presetSelect.value&&presetSelect.value!=='none')?presetSelect.value:'all';"
        "const sortKey=(sortSelect&&sortSelect.value)?sortSelect.value:'default';"
        "const filename='replay_attention_watchlist_'+preset+'_'+sortKey+'.csv';"
        "link.href=url;"
        "link.download=filename;"
        "document.body.appendChild(link);"
        "link.click();"
        "document.body.removeChild(link);"
        "URL.revokeObjectURL(url);"
        "}"
        "function buildVisibleReplayAttentionCsvText(){"
        "const visibleRows=rows.filter(function(row){return row.style.display!=='none';});"
        "const header=['country_id','case_id','attention_level','attention_reason','owner_hint','review_verdict','replay_evidence_tier','gap_signals','suggested_next_action'];"
        "const lines=[header.join(',')];"
        "visibleRows.forEach(function(row){"
        "const cols=Array.from(row.cells).map(function(cell){return (cell&&cell.textContent||'').trim();});"
        "lines.push(cols.map(csvEscape).join(','));"
        "});"
        "return lines.join('\\n');"
        "}"
        "function copyVisibleReplayAttentionCsv(){"
        "const csvText=buildVisibleReplayAttentionCsvText();"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(csvText).then(function(){if(copyStatus){copyStatus.textContent='Copied CSV';}}).catch(function(){if(copyStatus){copyStatus.textContent='Copy failed';}});"
        "}else{"
        "if(copyStatus){copyStatus.textContent='Clipboard API unavailable';}"
        "}"
        "}"
        "function buildReplayAttentionShareUrl(){"
        "const current=new URL(window.location.href);"
        "const params=new URLSearchParams();"
        "const level=(levelInput&&levelInput.value||'').trim();"
        "const owner=(ownerInput&&ownerInput.value||'').trim();"
        "const reason=(reasonInput&&reasonInput.value||'').trim();"
        "const text=(textInput&&textInput.value||'').trim();"
        "const sort=(sortSelect&&sortSelect.value||'default').trim();"
        "const preset=(presetSelect&&presetSelect.value||'none').trim();"
        "if(level){params.set('ra_level',level);}"
        "if(owner){params.set('ra_owner',owner);}"
        "if(reason){params.set('ra_reason',reason);}"
        "if(text){params.set('ra_text',text);}"
        "if(sort&&sort!=='default'){params.set('ra_sort',sort);}"
        "if(preset&&preset!=='none'){params.set('ra_preset',preset);}"
        "const query=params.toString();"
        "current.hash=query?('ra='+encodeURIComponent(query)):'';"
        "return current.toString();"
        "}"
        "function persistReplayAttentionStateToHash(){"
        "const current=new URL(window.location.href);"
        "const params=new URLSearchParams();"
        "const level=(levelInput&&levelInput.value||'').trim();"
        "const owner=(ownerInput&&ownerInput.value||'').trim();"
        "const reason=(reasonInput&&reasonInput.value||'').trim();"
        "const text=(textInput&&textInput.value||'').trim();"
        "const sort=(sortSelect&&sortSelect.value||'default').trim();"
        "const preset=(presetSelect&&presetSelect.value||'none').trim();"
        "if(level){params.set('ra_level',level);}"
        "if(owner){params.set('ra_owner',owner);}"
        "if(reason){params.set('ra_reason',reason);}"
        "if(text){params.set('ra_text',text);}"
        "if(sort&&sort!=='default'){params.set('ra_sort',sort);}"
        "if(preset&&preset!=='none'){params.set('ra_preset',preset);}"
        "const query=params.toString();"
        "const newHash=query?('#ra='+encodeURIComponent(query)):'';"
        "if(window.location.hash!==newHash){history.replaceState(null,'',current.pathname+current.search+newHash);}"
        "}"
        "function applyReplayAttentionStateFromHash(){"
        "const hash=(window.location.hash||'').replace(/^#/,'');"
        "if(hash.indexOf('ra=')!==0){return;}"
        "let decoded='';"
        "try{decoded=decodeURIComponent(hash.slice(3));}catch(_err){decoded='';}"
        "if(!decoded){return;}"
        "const params=new URLSearchParams(decoded);"
        "const setIfPresent=function(el,key){if(el&&params.get(key)!==null){el.value=params.get(key)||'';}};"
        "setIfPresent(levelInput,'ra_level');"
        "setIfPresent(ownerInput,'ra_owner');"
        "setIfPresent(reasonInput,'ra_reason');"
        "setIfPresent(textInput,'ra_text');"
        "setIfPresent(sortSelect,'ra_sort');"
        "setIfPresent(presetSelect,'ra_preset');"
        "}"
        "function copyReplayAttentionFilterLink(){"
        "const shareUrl=buildReplayAttentionShareUrl();"
        "if(navigator.clipboard&&navigator.clipboard.writeText){"
        "navigator.clipboard.writeText(shareUrl).then(function(){if(linkStatus){linkStatus.textContent='Copied link';}}).catch(function(){if(linkStatus){linkStatus.textContent='Copy link failed';}});"
        "}else{"
        "if(linkStatus){linkStatus.textContent='Clipboard API unavailable';}"
        "}"
        "}"
        "function applyReplayAttentionFilters(){"
        "const level=(levelInput&&levelInput.value||'').trim().toLowerCase();"
        "const owner=(ownerInput&&ownerInput.value||'').trim().toLowerCase();"
        "const reason=(reasonInput&&reasonInput.value||'').trim().toLowerCase();"
        "const text=(textInput&&textInput.value||'').trim().toLowerCase();"
        "const sortKey=(sortSelect&&sortSelect.value)?sortSelect.value:'default';"
        "let visible=0;"
        "let visibleHigh=0;"
        "let visibleMedium=0;"
        "let visibleLow=0;"
        "rows.forEach(function(row){"
        "const rowLevel=(row.getAttribute('data-attention-level')||'').toLowerCase();"
        "const rowOwner=(row.getAttribute('data-attention-owner')||'').toLowerCase();"
        "const rowReason=(row.getAttribute('data-attention-reason')||'').toLowerCase();"
        "const rowText=(row.textContent||'').toLowerCase();"
        "const matches=(!level||rowLevel.indexOf(level)!==-1)&&(!owner||rowOwner.indexOf(owner)!==-1)&&(!reason||rowReason.indexOf(reason)!==-1)&&(!text||rowText.indexOf(text)!==-1);"
        "row.style.display=matches?'':'none';"
        "if(matches){visible+=1;if(rowLevel==='high'){visibleHigh+=1;}else if(rowLevel==='medium'){visibleMedium+=1;}else if(rowLevel==='low'){visibleLow+=1;}}"
        "});"
        "if(tbody){"
        "const sorted=rows.slice().sort(function(a,b){"
        "if(sortKey==='level-desc'){return (levelRank[rowCellValue(b,2)]||0)-(levelRank[rowCellValue(a,2)]||0);}"
        "if(sortKey==='level-asc'){return (levelRank[rowCellValue(a,2)]||0)-(levelRank[rowCellValue(b,2)]||0);}"
        "if(sortKey==='country-asc'){return rowCellValue(a,0).localeCompare(rowCellValue(b,0));}"
        "if(sortKey==='case-asc'){return rowCellValue(a,1).localeCompare(rowCellValue(b,1));}"
        "return defaultOrder.indexOf(a)-defaultOrder.indexOf(b);"
        "});"
        "sorted.forEach(function(row){tbody.appendChild(row);});"
        "}"
        "if(countEl){countEl.textContent='Visible attention rows: '+visible;}"
        "if(breakdownEl){breakdownEl.textContent='(high='+visibleHigh+', medium='+visibleMedium+', low='+visibleLow+')';}"
        "persistReplayAttentionStateToHash();"
        "}"
        "if(levelInput){levelInput.addEventListener('input',function(){if(presetSelect){presetSelect.value='none';}applyReplayAttentionFilters();});}"
        "if(ownerInput){ownerInput.addEventListener('input',function(){if(presetSelect){presetSelect.value='none';}applyReplayAttentionFilters();});}"
        "if(reasonInput){reasonInput.addEventListener('input',function(){if(presetSelect){presetSelect.value='none';}applyReplayAttentionFilters();});}"
        "if(textInput){textInput.addEventListener('input',function(){if(presetSelect){presetSelect.value='none';}applyReplayAttentionFilters();});}"
        "if(sortSelect){sortSelect.addEventListener('change',applyReplayAttentionFilters);}"
        "if(presetSelect){presetSelect.addEventListener('change',function(){"
        "const preset=presetSelect.value||'none';"
        "if(preset==='high-only'){if(levelInput){levelInput.value='high';}if(ownerInput){ownerInput.value='';}if(reasonInput){reasonInput.value='';}if(textInput){textInput.value='';}}"
        "else if(preset==='governance-only'){if(levelInput){levelInput.value='';}if(ownerInput){ownerInput.value='validation governance';}if(reasonInput){reasonInput.value='';}if(textInput){textInput.value='';}}"
        "else if(preset==='domain-gap-only'){if(levelInput){levelInput.value='';}if(ownerInput){ownerInput.value='';}if(reasonInput){reasonInput.value='domain_coverage_gap';}if(textInput){textInput.value='';}}"
        "else {if(levelInput){levelInput.value='';}if(ownerInput){ownerInput.value='';}if(reasonInput){reasonInput.value='';}if(textInput){textInput.value='';}}"
        "applyReplayAttentionFilters();"
        "});}"
        "if(resetButton){resetButton.addEventListener('click',function(){if(levelInput){levelInput.value='';}if(ownerInput){ownerInput.value='';}if(reasonInput){reasonInput.value='';}if(textInput){textInput.value='';}if(sortSelect){sortSelect.value='default';}if(presetSelect){presetSelect.value='none';}applyReplayAttentionFilters();});}"
        "if(exportCsvButton){exportCsvButton.addEventListener('click',exportVisibleReplayAttentionCsv);}"
        "if(copyCsvButton){copyCsvButton.addEventListener('click',copyVisibleReplayAttentionCsv);}"
        "if(copyLinkButton){copyLinkButton.addEventListener('click',copyReplayAttentionFilterLink);}"
        "applyReplayAttentionStateFromHash();"
        "applyReplayAttentionFilters();"
        "})();"
        "</script>"
        "<h3>Historical Replay Reviews</h3>"
        "<table><thead><tr><th>Country</th><th>Case ID</th><th>Replay Verdict</th><th>Replay Basis</th><th>Replay Evidence Tier</th><th>Replay Evidence Score</th><th>Replay Sources</th><th>Archival Data Files</th><th>Expected Status</th><th>Replayed Status</th><th>Domain Match Ratio</th><th>Replay Input Records</th></tr></thead>"
        f"<tbody>{historical_replay_rows}</tbody></table>"
        "<h3>Changed Versions</h3>"
        f"<ul>{changed_versions}</ul>"
        f"<h3>Reprocessing Comparison</h3>{_json_block(reprocessing)}"
    )
    return _page("Validation / Backtest View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _parse_traceability_timestamp(value: str) -> datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    if text.endswith('Z'):
        text = f"{text[:-1]}+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None



def _traceability_dependency_rows(lineage_records: list[dict[str, Any]]) -> str:
    clusters: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in lineage_records:
        feature_id = str(record.get('feature_id', ''))
        domain_status_id = str(record.get('domain_status_id', ''))
        snapshot_id = str(record.get('snapshot_id', ''))
        cluster_key = (feature_id, domain_status_id, snapshot_id)
        entry = clusters.setdefault(
            cluster_key,
            {
                'feature_id': feature_id,
                'domain_status_id': domain_status_id,
                'snapshot_id': snapshot_id,
                'source_ids': set(),
                'report_ids': set(),
                'observed_times': [],
            },
        )
        entry['source_ids'].add(str(record.get('source_id', '')))
        if record.get('report_id'):
            entry['report_ids'].add(str(record.get('report_id')))
        observed_at = _parse_traceability_timestamp(str(record.get('observed_at') or ''))
        if observed_at is not None:
            entry['observed_times'].append(observed_at)
    rows = []
    for cluster in clusters.values():
        source_ids = sorted(source_id for source_id in cluster['source_ids'] if source_id)
        if len(source_ids) < 2:
            continue
        lag_minutes = 'n/a'
        coupling_signal = 'replication_or_shared_dependency_candidate'
        observed_times = cluster['observed_times']
        if len(observed_times) >= 2:
            lag_seconds = (max(observed_times) - min(observed_times)).total_seconds()
            lag_minutes = str(int(round(lag_seconds / 60.0)))
            coupling_signal = 'tight_temporal_coupling_candidate' if lag_seconds <= 3600 else 'shared_dependency_candidate_with_lag'
        rows.append(
            "<tr>"
            f"<td>{html.escape(cluster['feature_id'])}</td>"
            f"<td>{html.escape(cluster['domain_status_id'])}</td>"
            f"<td>{html.escape(cluster['snapshot_id'])}</td>"
            f"<td>{html.escape(', '.join(source_ids))}</td>"
            f"<td>{html.escape(', '.join(sorted(cluster['report_ids'])) or 'n/a')}</td>"
            f"<td>{html.escape(coupling_signal)}</td>"
            f"<td>{html.escape(lag_minutes)}</td>"
            "</tr>"
        )
    return ''.join(rows) or "<tr><td colspan='7'>No dependency cluster candidates in current lineage artifact.</td></tr>"



def _traceability_origin_rows(lineage_records: list[dict[str, Any]]) -> str:
    by_source: dict[str, dict[str, Any]] = {}
    source_first_seen: dict[str, datetime] = {}
    for record in lineage_records:
        source_id = str(record.get('source_id', ''))
        entry = by_source.setdefault(
            source_id,
            {
                'raw_record_ids': set(),
                'feature_ids': set(),
                'report_ids': set(),
            },
        )
        entry['raw_record_ids'].add(str(record.get('raw_record_id', '')))
        entry['feature_ids'].add(str(record.get('feature_id', '')))
        if record.get('report_id'):
            entry['report_ids'].add(str(record.get('report_id')))
        observed_at = _parse_traceability_timestamp(str(record.get('observed_at') or ''))
        if observed_at is not None:
            current = source_first_seen.get(source_id)
            if current is None or observed_at < current:
                source_first_seen[source_id] = observed_at
    earliest_seen = min(source_first_seen.values()) if source_first_seen else None
    earliest_sources = {
        source_id
        for source_id, observed_at in source_first_seen.items()
        if earliest_seen is not None and observed_at == earliest_seen
    }
    rows = []
    for source_id, entry in sorted(by_source.items()):
        first_seen = source_first_seen.get(source_id)
        if first_seen is None:
            inference_status = 'insufficient_timestamp_evidence'
            uncertainty = 'no observed_at timestamps available for this source in current artifact window'
            first_seen_text = 'n/a'
        elif len(earliest_sources) == 1 and source_id in earliest_sources:
            inference_status = 'earliest_observed_source_in_window'
            uncertainty = 'artifact-window inference only; does not prove true global origin'
            first_seen_text = first_seen.isoformat()
        elif source_id in earliest_sources:
            inference_status = 'co-earliest_observed_sources_in_window'
            uncertainty = 'multiple sources share same first-seen timestamp; origin remains ambiguous'
            first_seen_text = first_seen.isoformat()
        else:
            inference_status = 'later_observed_source_in_window'
            uncertainty = 'appears after earliest observed source(s); may still reflect upstream coupling'
            first_seen_text = first_seen.isoformat()
        rows.append(
            "<tr>"
            f"<td>{html.escape(source_id)}</td>"
            f"<td>{len([item for item in entry['raw_record_ids'] if item])}</td>"
            f"<td>{len([item for item in entry['feature_ids'] if item])}</td>"
            f"<td>{html.escape(', '.join(sorted(item for item in entry['report_ids'] if item)) or 'n/a')}</td>"
            f"<td>{html.escape(first_seen_text)}</td>"
            f"<td>{html.escape(inference_status)}</td>"
            f"<td>{html.escape(uncertainty)}</td>"
            "</tr>"
        )
    return ''.join(rows) or "<tr><td colspan='7'>No source-origin groundwork available.</td></tr>"



def _render_traceability(traceability_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    lineage_records = [record for record in traceability_view_model.get('lineage_records', []) if isinstance(record, dict)]
    rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(record.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('raw_record_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('normalized_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('feature_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('domain_status_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('multi_domain_status_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('snapshot_id', '')))}</td>"
        f"<td>{html.escape(str(record.get('report_id', '')))}</td>"
        "</tr>"
        for record in lineage_records
    )
    dependency_rows = _traceability_dependency_rows(lineage_records)
    origin_rows = _traceability_origin_rows(lineage_records)
    body = (
        "<div class='panel'><div class='panel-header'>Lineage Records</div>"
        "<div class='table-container'><table><thead><tr><th>Source</th><th>Raw</th><th>Normalized</th><th>Feature</th><th>Domain Status</th><th>Multi-Domain Status</th><th>Snapshot</th><th>Report</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div></div>"
        "<div class='panel'><div class='panel-header'>Source Dependency Groundwork — Cluster Candidates</div>"
        "<p>Features and domain statuses produced by multiple sources simultaneously — potential replication/shared-dependency signals with timing-lag context where observed timestamps exist.</p>"
        "<div class='table-container'><table><thead><tr><th>Feature</th><th>Domain Status</th><th>Snapshot</th><th>Sources</th><th>Reports</th><th>Coupling Signal</th><th>Observed Lag (min)</th></tr></thead>"
        f"<tbody>{dependency_rows}</tbody></table></div></div>"
        "<div class='panel'><div class='panel-header'>Source-Origin Groundwork</div>"
        "<p>Origin inference from current artifact-window observed timestamps (`observed_at`) with explicit uncertainty labels.</p>"
        "<div class='table-container'><table><thead><tr><th>Source</th><th>Raw Records</th><th>Features</th><th>Reports</th><th>First Observed (window)</th><th>Origin Inference Status</th><th>Origin Uncertainty</th></tr></thead>"
        f"<tbody>{origin_rows}</tbody></table></div></div>"
    )
    return _page("Traceability / Lineage View", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_annotations(annotations_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    scope_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(scope))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in annotation_ids))}</td>"
        "</tr>"
        for scope, annotation_ids in sorted(annotations_view_model.get('by_scope', {}).items())
    )
    linked_item_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(linked_item))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in annotation_ids))}</td>"
        "</tr>"
        for linked_item, annotation_ids in sorted(annotations_view_model.get('by_linked_item', {}).items())
    )
    workflow_seed = _annotation_workflow_seed(annotations_view_model)
    workflow_script = """
<script>
const annotationSeed = JSON.parse((document.getElementById('annotation-seed-data')?.textContent || '{}'));
const annotationStoreKey = 'siasa_annotation_workflow_v1';
const annotationHistoryStoreKey = 'siasa_annotation_workflow_history_v1';
function readStoredAnnotations(){ try { return JSON.parse(window.localStorage.getItem(annotationStoreKey) || '[]'); } catch (error) { return []; } }
function writeStoredAnnotations(items){ window.localStorage.setItem(annotationStoreKey, JSON.stringify(items)); }
function readStoredHistory(){ try { return JSON.parse(window.localStorage.getItem(annotationHistoryStoreKey) || '[]'); } catch (error) { return []; } }
function writeStoredHistory(items){ window.localStorage.setItem(annotationHistoryStoreKey, JSON.stringify(items)); }
function annotationLinkedItems(annotation){ return Array.isArray(annotation.linked_items) ? annotation.linked_items : []; }
function annotationDraftSource(annotation){ return String(annotation._draft_source || 'artifact'); }
function escapeAnnotationHtml(value){
  return String(value ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}
function mergedAnnotationsById(){
  const artifactItems = Array.isArray(annotationSeed.annotations) ? annotationSeed.annotations : [];
  const draftItems = readStoredAnnotations();
  const merged = new Map(artifactItems.map((item) => [String(item.annotation_id), item]));
  draftItems.forEach((item) => merged.set(String(item.annotation_id), item));
  return merged;
}
function currentEditorAnnotation(){
  return {
    annotation_id: (document.getElementById('annotation-id-input').value || '').trim(),
    created_at: (document.getElementById('annotation-created-at-input').value || '').trim(),
    author: (document.getElementById('annotation-author-input').value || '').trim(),
    scope: document.getElementById('annotation-scope-input').value,
    annotation_type: document.getElementById('annotation-type-input').value,
    severity_assessment: document.getElementById('annotation-severity-input').value,
    confidence_assessment: document.getElementById('annotation-confidence-input').value,
    text: (document.getElementById('annotation-text-input').value || '').trim(),
    tags: (document.getElementById('annotation-tags-input').value || '').split(',').map((item) => item.trim()).filter(Boolean),
    linked_items: (document.getElementById('annotation-linked-items-input').value || '').split(',').map((item) => item.trim()).filter(Boolean),
    review_status: document.getElementById('annotation-review-status-input').value,
    _draft_source: 'local_draft',
  };
}
function generatedDraftId(){ return `ANN-DRAFT-${Date.now()}`; }
function setWorkflowStatus(message){ document.getElementById('annotation-workflow-status').textContent = message; }
function loadAnnotationIntoEditor(annotationId){
  const all = Array.from(mergedAnnotationsById().values());
  const selected = all.find((item) => String(item.annotation_id) === String(annotationId));
  if (!selected) { return; }
  document.getElementById('annotation-id-input').value = selected.annotation_id || '';
  document.getElementById('annotation-created-at-input').value = selected.created_at || '';
  document.getElementById('annotation-author-input').value = selected.author || '';
  document.getElementById('annotation-scope-input').value = selected.scope || 'country';
  document.getElementById('annotation-type-input').value = selected.annotation_type || 'context_note';
  document.getElementById('annotation-severity-input').value = selected.severity_assessment || 'uncertain';
  document.getElementById('annotation-confidence-input').value = selected.confidence_assessment || 'medium';
  document.getElementById('annotation-review-status-input').value = selected.review_status || 'draft';
  document.getElementById('annotation-linked-items-input').value = annotationLinkedItems(selected).join(', ');
  document.getElementById('annotation-tags-input').value = (Array.isArray(selected.tags) ? selected.tags : []).join(', ');
  document.getElementById('annotation-text-input').value = selected.text || '';
  setWorkflowStatus(`Loaded annotation ${selected.annotation_id} into editor.`);
}
function prefillAnnotationFromQuery(){
  const params = new URLSearchParams(window.location.search);
  const linkedItem = params.get('linked_item') || '';
  const scope = params.get('scope') || '';
  const annotationType = params.get('annotation_type') || '';
  if (scope) { document.getElementById('annotation-scope-input').value = scope; }
  if (annotationType) { document.getElementById('annotation-type-input').value = annotationType; }
  if (linkedItem) {
    document.getElementById('annotation-linked-items-input').value = linkedItem;
    setWorkflowStatus(`Prefilled workflow for ${linkedItem}.`);
  }
}
function renderAnnotationWorkflow(){
  const merged = Array.from(mergedAnnotationsById().values());
  const scopeFilter = document.getElementById('annotation-scope-filter').value;
  const reviewFilter = document.getElementById('annotation-review-filter').value;
  const linkedItemNeedle = (document.getElementById('annotation-linked-item-filter').value || '').trim().toLowerCase();
  const filtered = merged.filter((annotation) => {
    const scopeOk = scopeFilter === 'all' || String(annotation.scope || '') === scopeFilter;
    const reviewOk = reviewFilter === 'all' || String(annotation.review_status || '') === reviewFilter;
    const linkedItems = annotationLinkedItems(annotation).join(', ').toLowerCase();
    const linkedOk = !linkedItemNeedle || linkedItems.includes(linkedItemNeedle) || String(annotation.annotation_id || '').toLowerCase().includes(linkedItemNeedle);
    return scopeOk && reviewOk && linkedOk;
  });
  document.getElementById('annotation-workflow-table-body').innerHTML = filtered.map((annotation) => `
    <tr>
      <td>${escapeAnnotationHtml(annotation.annotation_id || '')}</td>
      <td>${escapeAnnotationHtml(annotation.scope || '')}</td>
      <td>${escapeAnnotationHtml(annotation.annotation_type || '')}</td>
      <td>${escapeAnnotationHtml(annotation.review_status || '')}</td>
      <td>${escapeAnnotationHtml(annotation.author || '')}</td>
      <td>${escapeAnnotationHtml(annotationLinkedItems(annotation).join(', '))}</td>
      <td>${escapeAnnotationHtml(annotationDraftSource(annotation))}</td>
      <td><button type="button" class="annotation-edit-button" data-annotation-id="${escapeAnnotationHtml(annotation.annotation_id || '')}">Edit</button></td>
    </tr>`).join('') || '<tr><td colspan="8">No annotations match the current filters.</td></tr>';
  document.querySelectorAll('.annotation-edit-button').forEach((button) => button.addEventListener('click', () => loadAnnotationIntoEditor(button.getAttribute('data-annotation-id') || '')));
  const history = readStoredHistory();
  document.getElementById('annotation-history-table-body').innerHTML = history.map((entry) => `
    <tr>
      <td>${escapeAnnotationHtml(entry.saved_at || '')}</td>
      <td>${escapeAnnotationHtml(entry.annotation_id || '')}</td>
      <td>${escapeAnnotationHtml(entry.action || '')}</td>
      <td>${escapeAnnotationHtml((entry.linked_items || []).join(', '))}</td>
    </tr>`).join('') || '<tr><td colspan="4">No draft history recorded.</td></tr>';
  document.getElementById('annotation-draft-export').textContent = JSON.stringify(readStoredAnnotations(), null, 2);
}
document.getElementById('annotation-editor-form').addEventListener('submit', (event) => {
  event.preventDefault();
  const annotation = currentEditorAnnotation();
  if (!annotation.annotation_id) { annotation.annotation_id = generatedDraftId(); }
  if (!annotation.created_at) { annotation.created_at = new Date().toISOString(); }
  if (!annotation.author) { annotation.author = 'analyst'; }
  const drafts = readStoredAnnotations();
  const existingIndex = drafts.findIndex((item) => String(item.annotation_id) === String(annotation.annotation_id));
  const action = existingIndex >= 0 ? 'updated' : 'created';
  if (existingIndex >= 0) { drafts[existingIndex] = annotation; } else { drafts.push(annotation); }
  writeStoredAnnotations(drafts);
  const history = readStoredHistory();
  history.unshift({ saved_at: new Date().toISOString(), annotation_id: annotation.annotation_id, action: action, linked_items: annotation.linked_items });
  writeStoredHistory(history.slice(0, 25));
  document.getElementById('annotation-id-input').value = annotation.annotation_id;
  document.getElementById('annotation-created-at-input').value = annotation.created_at;
  setWorkflowStatus(`Draft annotation ${annotation.annotation_id} ${action}.`);
  renderAnnotationWorkflow();
});
document.getElementById('annotation-reset-editor').addEventListener('click', () => {
  document.getElementById('annotation-editor-form').reset();
  document.getElementById('annotation-id-input').value = '';
  document.getElementById('annotation-created-at-input').value = '';
  prefillAnnotationFromQuery();
  setWorkflowStatus('Annotation editor reset.');
});
document.getElementById('annotation-export-drafts').addEventListener('click', () => {
  const exportText = JSON.stringify(readStoredAnnotations(), null, 2);
  document.getElementById('annotation-draft-export').textContent = exportText;
  const blob = new Blob([exportText], { type: 'application/json' });
  const exportLink = document.createElement('a');
  exportLink.href = URL.createObjectURL(blob);
  exportLink.download = 'annotation_drafts.json';
  exportLink.click();
  URL.revokeObjectURL(exportLink.href);
  setWorkflowStatus('Draft annotations exported as JSON.');
});
document.getElementById('annotation-scope-filter').addEventListener('change', renderAnnotationWorkflow);
document.getElementById('annotation-review-filter').addEventListener('change', renderAnnotationWorkflow);
document.getElementById('annotation-linked-item-filter').addEventListener('input', renderAnnotationWorkflow);
prefillAnnotationFromQuery();
renderAnnotationWorkflow();
</script>
"""
    body = ''.join(
        [
            "<h2>Analyst Annotations View</h2>",
            f"<p>Total annotations: <strong>{html.escape(str(len(annotations_view_model.get('annotations', []))))}</strong></p>",
            "<h3>Create / Edit Annotation Workflow</h3>",
            "<p>This static GUI keeps analyst draft annotations in the browser for create/edit/filter/history workflow support. Export the draft JSON for governed persistence into repo-backed artifacts.</p>",
            "<div id='annotation-workflow-status'></div>",
            "<h4>Workflow Filters</h4>",
            "<label for='annotation-scope-filter'>Scope Filter</label> ",
            "<select id='annotation-scope-filter'><option value='all'>All scopes</option><option value='country'>country</option><option value='domain'>domain</option><option value='signal'>signal</option><option value='event'>event</option><option value='snapshot'>snapshot</option></select> ",
            "<label for='annotation-review-filter'>Review Filter</label> ",
            "<select id='annotation-review-filter'><option value='all'>All review states</option><option value='unreviewed'>unreviewed</option><option value='draft'>draft</option><option value='reviewed'>reviewed</option><option value='accepted'>accepted</option><option value='rejected'>rejected</option></select> ",
            "<label for='annotation-linked-item-filter'>Linked Item Filter</label> ",
            "<input id='annotation-linked-item-filter' type='text' placeholder='UKR / UKR:A / SNAP-...' />",
            "<h4>Annotation Registry</h4>",
            "<table id='annotation-workflow-table'><thead><tr><th>ID</th><th>Scope</th><th>Type</th><th>Review</th><th>Author</th><th>Linked Items</th><th>Draft Source</th><th>Action</th></tr></thead><tbody id='annotation-workflow-table-body'></tbody></table>",
            "<h4>Draft Editor</h4>",
            "<form id='annotation-editor-form'>",
            "<p><label for='annotation-id-input'>Annotation ID</label><br><input id='annotation-id-input' type='text' placeholder='ANN-DRAFT-...' /></p>",
            "<p><label for='annotation-created-at-input'>Created At</label><br><input id='annotation-created-at-input' type='text' placeholder='2026-05-16T06:45:00Z' /></p>",
            "<p><label for='annotation-author-input'>Author</label><br><input id='annotation-author-input' type='text' placeholder='analyst' /></p>",
            "<p><label for='annotation-scope-input'>Scope</label><br><select id='annotation-scope-input'><option value='country'>country</option><option value='domain'>domain</option><option value='signal'>signal</option><option value='event'>event</option><option value='snapshot'>snapshot</option></select></p>",
            "<p><label for='annotation-type-input'>Annotation Type</label><br><select id='annotation-type-input'><option value='context_note'>context_note</option><option value='false_positive_note'>false_positive_note</option><option value='source_quality_note'>source_quality_note</option><option value='lineage_note'>lineage_note</option><option value='review_note'>review_note</option></select></p>",
            "<p><label for='annotation-severity-input'>Severity Assessment</label><br><select id='annotation-severity-input'><option value='not_security_relevant'>not_security_relevant</option><option value='relevant'>relevant</option><option value='uncertain'>uncertain</option></select></p>",
            "<p><label for='annotation-confidence-input'>Confidence Assessment</label><br><select id='annotation-confidence-input'><option value='low'>low</option><option value='medium'>medium</option><option value='high'>high</option></select></p>",
            "<p><label for='annotation-review-status-input'>Review Status</label><br><select id='annotation-review-status-input'><option value='unreviewed'>unreviewed</option><option value='draft'>draft</option><option value='reviewed'>reviewed</option><option value='accepted'>accepted</option><option value='rejected'>rejected</option></select></p>",
            "<p><label for='annotation-linked-items-input'>Linked Items (comma separated)</label><br><input id='annotation-linked-items-input' type='text' placeholder='UKR, UKR:A, SNAP-RUN-...' /></p>",
            "<p><label for='annotation-tags-input'>Tags (comma separated)</label><br><input id='annotation-tags-input' type='text' placeholder='source_dependency, review' /></p>",
            "<p><label for='annotation-text-input'>Annotation Text</label><br><textarea id='annotation-text-input' rows='6' cols='80' placeholder='Analyst note...'></textarea></p>",
            "<p><button id='annotation-save-draft' type='submit'>Save Draft Annotation</button> <button id='annotation-reset-editor' type='button'>Reset Editor</button> <button id='annotation-export-drafts' type='button'>Export Draft Annotations</button></p>",
            "</form>",
            "<h4>Draft Export</h4><pre id='annotation-draft-export'>[]</pre>",
            "<h4>Draft History</h4>",
            "<table id='annotation-history-table'><thead><tr><th>Saved At</th><th>Annotation ID</th><th>Action</th><th>Linked Items</th></tr></thead><tbody id='annotation-history-table-body'></tbody></table>",
            f"<h3>Annotation Details</h3>{_annotation_details_html([str(item.get('annotation_id')) for item in annotations_view_model.get('annotations', [])], annotations_view_model)}",
            "<h3>By Scope</h3>",
            "<table><thead><tr><th>Scope</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{scope_rows}</tbody></table>",
            "<h3>By Linked Item</h3>",
            "<table><thead><tr><th>Linked Item</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{linked_item_rows}</tbody></table>",
            f"<script id='annotation-seed-data' type='application/json'>{workflow_seed}</script>",
            workflow_script,
        ]
    )
    return _page("Analyst Annotations View", body, nav_prefix=nav_prefix, available_pages=available_pages)

def _normalize_ui_role(ui_role: str) -> str:
    normalized = ui_role.strip().lower()
    if normalized not in _UI_ROLES:
        raise ValueError(f"Unsupported ui_role '{ui_role}'. Expected one of: {', '.join(sorted(_UI_ROLES))}")
    return normalized


def build_local_mvp_site(
    output_dir: Path,
    *,
    world_map_read_model: dict[str, Any],
    country_profile_read_models: dict[str, dict[str, Any]],
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]],
    source_coverage_read_model: dict[str, Any],
    report_catalog: dict[str, dict[str, Any]],
    system_status_read_model: dict[str, Any],
    validation_view_model: dict[str, Any] | None = None,
    traceability_view_model: dict[str, Any] | None = None,
    repo_closure_view_model: dict[str, Any] | None = None,
    annotations_view_model: dict[str, Any] | None = None,
    readiness_view_model: dict[str, Any] | None = None,
    ui_role: str = 'analyst',
) -> SiteBuildResult:
    normalized_role = _normalize_ui_role(ui_role)

    output_dir.mkdir(parents=True, exist_ok=True)
    countries_dir = output_dir / 'countries'
    domains_dir = output_dir / 'domains'
    countries_dir.mkdir(exist_ok=True)
    domains_dir.mkdir(exist_ok=True)

    generated_files: list[Path] = []
    available_pages = {
        'index.html',
        'coverage.html',
        'reports.html',
        'runs.html',
        'trends.html',
        'events.html',
        'comparison.html',
        'readiness.html',
    }

    if normalized_role == 'viewer':
        available_pages.discard('reports.html')
        available_pages.discard('runs.html')

    if validation_view_model is not None:
        available_pages.add('validation.html')
    if traceability_view_model is not None:
        available_pages.add('traceability.html')
    if annotations_view_model is not None and normalized_role in {'analyst', 'admin'}:
        available_pages.add('annotations.html')

    index_file = output_dir / 'index.html'
    index_file.write_text(
        _render_index(
            world_map_read_model,
            available_country_ids=set(country_profile_read_models),
            country_profile_read_models=country_profile_read_models,
            system_status_read_model=system_status_read_model,
            nav_prefix='',
            available_pages=available_pages,
        ),
        encoding='utf-8',
    )
    generated_files.append(index_file)

    available_domain_targets_by_country: dict[str, dict[str, str]] = {}
    for (country_id, domain) in domain_detail_read_models:
        available_domain_targets_by_country.setdefault(country_id, {})[domain] = f"../domains/{country_id}-{domain}.html"

    for country_id, read_model in country_profile_read_models.items():
        country_file = countries_dir / f'{country_id}.html'
        country_file.write_text(
            _render_country(
                read_model,
                annotations_view_model,
                available_domain_targets=available_domain_targets_by_country.get(country_id, {}),
                nav_prefix='../',
                available_pages=available_pages,
            ),
            encoding='utf-8',
        )
        generated_files.append(country_file)

    for (country_id, domain), read_model in domain_detail_read_models.items():
        domain_file = domains_dir / f'{country_id}-{domain}.html'
        domain_file.write_text(
            _render_domain_detail(
                read_model,
                annotations_view_model,
                nav_prefix='../',
                available_pages=available_pages,
            ),
            encoding='utf-8',
        )
        generated_files.append(domain_file)

    coverage_file = output_dir / 'coverage.html'
    coverage_file.write_text(
        _render_source_coverage(
            source_coverage_read_model,
            system_status_read_model=system_status_read_model,
            nav_prefix='',
            available_pages=available_pages,
        ),
        encoding='utf-8',
    )
    generated_files.append(coverage_file)

    prepared_report_catalog, copied_export_files = _prepare_report_catalog(report_catalog, output_dir)
    generated_files.extend(copied_export_files)
    if 'reports.html' in available_pages:
        reports_file = output_dir / 'reports.html'
        reports_file.write_text(_render_reports(prepared_report_catalog, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(reports_file)

    if 'runs.html' in available_pages:
        runs_file = output_dir / 'runs.html'
        runs_file.write_text(_render_runs(system_status_read_model, repo_closure_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(runs_file)

    trends_file = output_dir / 'trends.html'
    trends_file.write_text(_render_trends(country_profile_read_models, nav_prefix='', available_pages=available_pages), encoding='utf-8')
    generated_files.append(trends_file)

    events_file = output_dir / 'events.html'
    events_file.write_text(_render_events(country_profile_read_models, nav_prefix='', available_pages=available_pages), encoding='utf-8')
    generated_files.append(events_file)

    comparison_file = output_dir / 'comparison.html'
    comparison_file.write_text(_render_comparison(country_profile_read_models, nav_prefix='', available_pages=available_pages), encoding='utf-8')
    generated_files.append(comparison_file)

    if validation_view_model is not None:
        validation_file = output_dir / 'validation.html'
        validation_file.write_text(_render_validation(validation_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(validation_file)

    if traceability_view_model is not None:
        traceability_file = output_dir / 'traceability.html'
        traceability_file.write_text(_render_traceability(traceability_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(traceability_file)

    if annotations_view_model is not None and 'annotations.html' in available_pages:
        annotations_file = output_dir / 'annotations.html'
        annotations_file.write_text(_render_annotations(annotations_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(annotations_file)

    if readiness_view_model is None:
        readiness_view_model = build_readiness_view_model(
            country_profile_read_models=country_profile_read_models,
            domain_detail_read_models=domain_detail_read_models,
            report_catalog=prepared_report_catalog,
            system_status_read_model=system_status_read_model,
            source_coverage_read_model=source_coverage_read_model,
            validation_view_model=validation_view_model,
            traceability_view_model=traceability_view_model,
            annotations_view_model=annotations_view_model,
            repo_closure_view_model=repo_closure_view_model,
            available_pages=available_pages,
        )
    readiness_file = output_dir / 'readiness.html'
    readiness_file.write_text(_render_readiness(readiness_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
    generated_files.append(readiness_file)
    readiness_json_file = output_dir / 'readiness.json'
    readiness_json_file.write_text(json.dumps(readiness_view_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(readiness_json_file)

    return SiteBuildResult(output_dir=output_dir, generated_files=generated_files)


def _demo_payload() -> dict[str, Any]:
    return {
        'world_map_read_model': {
            'baseline_mode': 'Combined 30/90/365',
            'active_domains': ['A', 'B', 'D'],
            'countries': [
                {'country_id': 'UKR', 'status': 'S3', 'active_domains': ['A', 'B', 'D'], 'drill_down_target': '/countries/UKR'},
                {'country_id': 'POL', 'status': 'S1', 'active_domains': ['A', 'D'], 'drill_down_target': '/countries/POL'},
            ],
        },
        'country_profile_read_models': {
            'UKR': {
                'country_id': 'UKR',
                'multi_domain_status': 'S3',
                'domain_states': {'A': 'D3', 'B': 'D2', 'D': 'D1'},
                'trends': {'yearly': ['2025-11', '2025-12', '2026-01']},
                'drivers': ['A_news_volume'],
                'linked_events': ['EVT-001'],
                'coverage': 0.84,
                'confidence': 0.73,
                'counter_indicators': ['D_macro_stability'],
                'uncertainty': ['partial_success'],
                'annotations': ['ANN-001'],
            }
        },
        'domain_detail_read_models': {
            ('UKR', 'A'): {
                'country_id': 'UKR',
                'domain': 'A',
                'time_series': [{'timestamp': '2026-05-11', 'value': 0.67}],
                'baseline_comparison': {'current_window': 0.67, 'baseline_30d': 0.31, 'delta_to_baseline': 0.36},
                'feature_values': [{'feature_id': 'A_article_count', 'value': 12.0, 'coverage': 0.9}],
                'source_context': [{'source_id': 'SRC-A', 'freshness_hours': 6, 'history_horizon': '3y', 'status': 'success'}],
                'anomaly_state': 'D3',
                'uncertainty': ['source_bias_possible'],
                'annotations': ['ANN-002'],
            }
        },
        'source_coverage_read_model': {
            'sources': [
                {'source_id': 'SRC-A', 'status': 'success', 'history_horizon': '3y', 'freshness_hours': 6, 'confidence': 0.9},
                {'source_id': 'ACLED', 'status': 'prepared_adapter', 'history_horizon': 'n/a', 'freshness_hours': None, 'confidence': None},
            ],
            'failed_sources': ['SRC-B'],
            'missing_sources': ['SRC-C'],
        },
        'report_catalog': {
            'daily_snapshot': {'format': 'Markdown + JSON', 'report_id': 'REP-DAILY-RUN-200', 'uncertainty': ['partial_success']},
            'country_profile': {'format': 'Markdown + JSON', 'report_id': 'REP-COUNTRY-UKR', 'country_id': 'UKR'},
            'coverage_report': {'format': 'Markdown + JSON + CSV', 'report_id': 'REP-COVERAGE-001'},
        },
        'system_status_read_model': {
            'run_id': 'RUN-200',
            'run_status': 'partial_success',
            'active_domains': ['A', 'B', 'D'],
            'coverage': {'countries_total': 30, 'countries_with_updates': 27},
            'failed_sources': ['SRC-B'],
            'available_reports': ['REP-DAILY-RUN-200', 'REP-COUNTRY-UKR'],
            'snapshot_id': 'SNAP-RUN-200-v1',
            'reprocessing_status': 'idle',
            'last_run': '2026-05-11T18:00:00Z',
        },
        'validation_view_model': {
            'case_id': 'VAL-UKR-2022-001',
            'country_id': 'UKR',
            'case_name': 'Escalation reference case',
            'time_range': {'start': '2022-02-01', 'end': '2022-03-01'},
            'expected_domains': ['A', 'B', 'D'],
            'observed_domains': ['A', 'B'],
            'domain_match_ratio': 2 / 3,
            'status_match': True,
            'expected_pattern': 'Aligned information, event, and economic stress escalation.',
            'validation_goal': 'Check multi-domain alignment detection.',
            'reference_sources': ['SRC-A', 'SRC-B'],
            'validation_metrics': ['Domain Match', 'Status Match'],
            'known_limitations': ['historical coverage incomplete'],
            'reprocessing_comparison': {'prior_snapshot_id': 'SNAP-RUN-001-v1', 'new_snapshot_id': 'SNAP-RUN-001-v2', 'changed_versions': ['rule_version']},
        },
        'annotations_view_model': {
            'annotations': [
                {
                    'annotation_id': 'ANN-001',
                    'created_at': '2026-05-11T18:05:00Z',
                    'author': 'analyst',
                    'scope': 'country',
                    'annotation_type': 'context_note',
                    'severity_assessment': 'relevant',
                    'confidence_assessment': 'medium',
                    'text': 'Replicated agency report likely inflated country-level signal volume.',
                    'tags': ['source_dependency'],
                    'linked_items': ['UKR'],
                    'review_status': 'draft',
                },
                {
                    'annotation_id': 'ANN-002',
                    'created_at': '2026-05-11T18:06:00Z',
                    'author': 'analyst',
                    'scope': 'domain',
                    'annotation_type': 'lineage_note',
                    'severity_assessment': 'uncertain',
                    'confidence_assessment': 'high',
                    'text': 'Domain A spike is traceable to two closely coupled source clusters.',
                    'tags': ['lineage'],
                    'linked_items': ['UKR:A', 'A_article_count'],
                    'review_status': 'reviewed',
                },
            ],
            'by_scope': {'country': ['ANN-001'], 'domain': ['ANN-002']},
            'by_linked_item': {'UKR': ['ANN-001'], 'UKR:A': ['ANN-002'], 'A_article_count': ['ANN-002']},
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description='Build a local SIASA MVP GUI site.')
    parser.add_argument('--output-dir', default='build/local_gui', help='Target directory for generated HTML files.')
    parser.add_argument(
        '--artifacts-dir',
        default=None,
        help='Optional directory containing persisted snapshot, report, and read-model JSON artifacts.',
    )
    parser.add_argument(
        '--ui-role',
        default='analyst',
        choices=sorted(_UI_ROLES),
        help='Role-based GUI profile to apply when generating pages.',
    )
    args = parser.parse_args(argv)

    if args.artifacts_dir:
        payload = load_site_payload_from_artifacts(Path(args.artifacts_dir))
    else:
        payload = _demo_payload()
    result = build_local_mvp_site(output_dir=Path(args.output_dir), ui_role=args.ui_role, **payload)
    print(f'Generated SIASA local GUI at {result.output_dir / "index.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
