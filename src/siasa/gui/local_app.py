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
from urllib.parse import quote, quote_plus

from siasa.catalog import load_country_set
from siasa.readmodels.readiness import build_readiness_view_model
from siasa.readmodels.release_demo_package import build_release_demo_package_view_model, render_release_demo_package_body
from siasa.readmodels.release_evidence import build_release_readiness_index, render_release_evidence_markdown
from siasa.readmodels.release_gate import build_release_gate_view_model
from siasa.readmodels.stakeholder_e2e_flow_coverage import build_stakeholder_e2e_flow_coverage_report
from siasa.readmodels.stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report
from siasa.readmodels.validation_backtest import build_historical_replay_summary
from siasa.traceability.consistency import build_repo_closure_report, build_traceability_integrity_report


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
        ('analytics.html', '🔬 Analytics'),
        ('validation.html', '✅ Validation'),
        ('traceability.html', '🔗 Traceability'),
        ('annotations.html', '📝 Annotations'),
        ('release_package.html', '📦 Release Package'),
        ('release_failure_drill.html', '🧪 Failure Drill'),
        ('reports.html', '📄 Reports'),
        ('runs.html', '⚙ System'),
        ('readiness.html', '🚦 Readiness'),
    ]
    nav_html = ''.join(
        f"<a href='{html.escape(nav_prefix + href)}'>{html.escape(label)}</a>"
        for href, label in nav_entries
        if href in available_pages
    )
    role_switcher = (
        "<div id='role-switcher' style='margin-left:auto;display:flex;align-items:center;gap:6px;'>"
        "<label for='role-select' style='font-size:10px;color:#6b7d99;font-family:Space Grotesk,monospace;text-transform:uppercase;letter-spacing:.08em;'>Role</label>"
        "<select id='role-select' style='background:#1a2540;color:#4edea3;border:1px solid #263050;padding:3px 8px;font-size:11px;font-family:Space Grotesk,monospace;border-radius:2px;cursor:pointer;'>"
        "<option value='analyst'>Analyst</option>"
        "<option value='admin'>Admin</option>"
        "<option value='viewer'>Viewer</option>"
        "</select>"
        "</div>"
    )
    role_js = (
        "<script>"
        "(function(){"
        "var sel=document.getElementById('role-select');"
        "if(!sel)return;"
        "function applyRole(role){"
        "document.body.dataset.activeRole=role;"
        "document.querySelectorAll('[data-role-min]').forEach(function(el){"
        "var min=el.dataset.roleMin;"
        "var show=(min==='viewer')||(min==='analyst'&&(role==='analyst'||role==='admin'))||(min==='admin'&&role==='admin');"
        "el.style.display=show?'':'none';"
        "});"
        "var navLinks=document.querySelectorAll('nav a');"
        "navLinks.forEach(function(a){"
        "var href=a.getAttribute('href')||'';"
        "var isOps=href.indexOf('annotations')>=0||href.indexOf('runs.')>=0||href.indexOf('readiness')>=0;"
        "a.style.display=(role==='viewer'&&isOps)?'none':'';"
        "});"
        "}"
        "sel.addEventListener('change',function(){applyRole(sel.value);});"
        "applyRole(sel.value);"
        "})();"
        "</script>"
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
        # === Download button ===
        ".btn-download{display:inline-block;background:rgba(56,139,253,.12);color:#8ed0ff;"
        "border:1px solid rgba(56,139,253,.3);border-radius:2px;padding:3px 10px;"
        "font-size:11px;font-weight:700;font-family:'Space Grotesk',monospace;"
        "text-transform:uppercase;letter-spacing:.05em;text-decoration:none;"
        "cursor:pointer;transition:background .15s,border-color .15s;}"
        ".btn-download:hover{background:rgba(56,139,253,.22);border-color:rgba(56,139,253,.6);color:#b0d8ff;text-decoration:none;}"
        # === Skip nav ===
        ".skip-nav{position:absolute;left:-9999px;top:0;z-index:9999;"
        "background:#388bfd;color:#fff;padding:4px 8px;border-radius:0 0 4px 0;font-size:13px;}"
        # === Accessibility & Responsive ===
        "*:focus-visible{outline:2px solid #388bfd;outline-offset:2px;}"
        "a:focus-visible{outline:2px solid #388bfd;}"
        "button:focus-visible{outline:2px solid #388bfd;}"
        "select:focus-visible{outline:2px solid #388bfd;}"
        "input:focus-visible{outline:2px solid #388bfd;}"
        # === Responsive tables ===
        ".table-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch;}"
        "@media(max-width:900px){"
        "nav ul{flex-wrap:wrap;gap:4px;}"
        ".kpi-grid{grid-template-columns:repeat(2,1fr);}"
        ".kpi-card{padding:8px 10px;}"
        "table{font-size:11px;}"
        ".panel{padding:10px;}}"
        "@media(max-width:600px){"
        "body{padding:8px;}"
        ".kpi-grid{grid-template-columns:1fr;}"
        "nav ul{gap:2px;}"
        "nav a{font-size:10px;padding:3px 6px;}}"
    )
    return (
        "<!DOCTYPE html>"
        "<html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>SIASA — {html.escape(title)}</title>"
        f"{font_link}"
        f"<style>{css}</style>"
        "</head><body>"
        "<a href='#main-content' class='skip-nav' onfocus=\"this.style.left='0'\" onblur=\"this.style.left='-9999px'\">Zum Inhalt springen</a>"
        f"<nav aria-label='Main navigation' style='display:flex;flex-wrap:wrap;align-items:center;'>{nav_html}{role_switcher}</nav>"
        "<div class='page-content'>"
        f"<main id='main-content'>"
        f"<h1>{html.escape(title)}</h1>"
        f"{body}"
        "</main>"
        "</div>"
        f"{role_js}"
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
            f"<circle cx='{x:.1f}' cy='{y:.1f}' r='4' fill='#0b1326' stroke='#4edea3' stroke-width='1.5' data-idx='{i}'>"
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


def _render_enhanced_trend_controls_js() -> str:
    """Return client-side JS for enhanced trend chart interactions.

    Adds per-chart zoom/pan via wheel+drag, time-range selection buttons,
    and multi-series toggle controls. Wired into trend page charts.
    """
    return """\
<script>
(function(){
  // Enhanced trend chart zoom/pan
  document.querySelectorAll('.trend-chart-block svg').forEach(function(svg){
    var scale=1, panX=0, panY=0, dragging=false, dsx=0, dsy=0, psx=0, psy=0;
    function apply(){ svg.style.transform='translate('+panX+'px,'+panY+'px) scale('+scale+')'; svg.style.transformOrigin='0 0'; }
    svg.parentElement.style.overflow='hidden';
    svg.style.cursor='grab';
    svg.addEventListener('wheel',function(e){
      e.preventDefault();
      var r=svg.getBoundingClientRect();
      var mx=e.clientX-r.left, my=e.clientY-r.top;
      var os=scale; scale*=e.deltaY<0?1.15:0.87; scale=Math.max(0.5,Math.min(scale,6));
      panX=mx-(mx-panX)*(scale/os); panY=my-(my-panY)*(scale/os); apply();
    },{passive:false});
    svg.addEventListener('mousedown',function(e){
      if(e.button!==0)return; dragging=true; dsx=e.clientX; dsy=e.clientY; psx=panX; psy=panY; svg.style.cursor='grabbing';
    });
    window.addEventListener('mousemove',function(e){ if(!dragging)return; panX=psx+(e.clientX-dsx); panY=psy+(e.clientY-dsy); apply(); });
    window.addEventListener('mouseup',function(){ dragging=false; if(svg.style.cursor==='grabbing') svg.style.cursor='grab'; });
  });
  // Time-range selection
  document.querySelectorAll('.trend-range-btn').forEach(function(btn){
    btn.addEventListener('click',function(){
      var parent=btn.closest('.trend-chart-block');
      if(!parent)return;
      parent.querySelectorAll('.trend-range-btn').forEach(function(b){
        b.style.color=b===btn?'#4edea3':'#6b7d99';
        b.style.borderColor=b===btn?'#4edea3':'#263050';
      });
      var range=btn.dataset.range;
      var dataPoints=parent.querySelectorAll('circle[data-idx]');
      var total=dataPoints.length;
      var cutoff=range==='6m'?Math.max(0,total-6):range==='1y'?Math.max(0,total-12):0;
      dataPoints.forEach(function(c){
        var idx=parseInt(c.dataset.idx||'0');
        c.style.opacity=idx>=cutoff?'1':'0.15';
      });
    });
  });
  // Multi-series toggle
  document.querySelectorAll('.trend-series-toggle').forEach(function(chk){
    chk.addEventListener('change',function(){
      var parent=chk.closest('.trend-chart-block');
      if(!parent)return;
      var series=chk.dataset.series;
      var visible=chk.checked;
      parent.querySelectorAll('[data-series=\"'+series+'\"]').forEach(function(el){
        el.style.display=visible?'':'none';
      });
    });
  });
})();
</script>"""



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



def _analyst_priority_sort_key(priority: str) -> int:
    priority_upper = priority.upper()
    if priority_upper == 'P1':
        return 0
    if priority_upper == 'P2':
        return 1
    if priority_upper == 'P3':
        return 2
    return 3



def _slugify_anchor_token(value: str) -> str:
    cleaned = re.sub(r'[^A-Za-z0-9._-]+', '-', str(value).strip())
    return cleaned.strip('-') or 'unknown'



def _coverage_prefill_href(*, country_id: str, focus_section: str, missing_domains: list[str] | None = None) -> str:
    query_parts = [
        f"focus_country={quote_plus(country_id)}",
        f"focus_section={quote_plus(focus_section)}",
    ]
    if missing_domains:
        query_parts.append(f"missing_domains={quote_plus(','.join(str(item) for item in missing_domains if str(item)))}")
    anchor_target = 'stale-priority' if focus_section == 'stale_priority' else 'country-gap'
    return f"coverage.html?{'&'.join(query_parts)}#{anchor_target}-{_slugify_anchor_token(country_id)}"



def _validation_prefill_href(*, country_id: str, case_id: str, attention_reason: str) -> str:
    hash_parts = [
        f"ra_reason={quote_plus(attention_reason)}",
        f"ra_text={quote_plus(f'{country_id} {case_id}')}",
    ]
    return f"validation.html#ra={'&'.join(hash_parts)}"



def _coverage_focus_row_attrs(*, country_id: str, focus_section: str, missing_domains: list[str] | None = None) -> str:
    attrs = [
        "class='coverage-focus-target'",
        f"data-focus-country='{html.escape(str(country_id))}'",
        f"data-focus-section='{html.escape(str(focus_section))}'",
    ]
    missing_domain_text = ','.join(str(item) for item in (missing_domains or []) if str(item))
    if missing_domain_text:
        attrs.append(f"data-missing-domains='{html.escape(missing_domain_text)}'")
    return ' '.join(attrs)



def _build_analyst_country_hotspot_matrix(
    *,
    system_status_read_model: dict[str, Any] | None = None,
    validation_view_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    visibility = _country_coverage_visibility_rows(system_status_read_model or {})
    validation_view_model = validation_view_model or {}
    hotspots: dict[str, dict[str, Any]] = {}

    def _country_row(country_id: str) -> dict[str, Any]:
        return hotspots.setdefault(
            country_id,
            {
                'country_id': country_id,
                'signals': set(),
                'priority': 'unassigned',
                'freshness_hours': None,
                'missing_domains': set(),
                'attention_case_ids': [],
                'attention_cases': [],
                'coverage_href': None,
            },
        )

    for row in visibility.get('country_gap_rows', []):
        if not isinstance(row, dict):
            continue
        country_id = str(row.get('country_id', 'UNKNOWN'))
        hotspot = _country_row(country_id)
        hotspot['signals'].add('country_gap')
        hotspot['priority'] = str(row.get('priority', hotspot.get('priority', 'unassigned')))
        hotspot['missing_domains'].update(str(item) for item in row.get('missing_domains', []) if str(item))
        hotspot['coverage_href'] = f"coverage.html#country-gap-{_slugify_anchor_token(country_id)}"
        if hotspot.get('freshness_hours') is None and row.get('freshness_hours') is not None:
            hotspot['freshness_hours'] = row.get('freshness_hours')

    for row in visibility.get('stale_priority_watchlist', []):
        if not isinstance(row, dict):
            continue
        country_id = str(row.get('country_id', 'UNKNOWN'))
        hotspot = _country_row(country_id)
        hotspot['signals'].add('stale_priority')
        hotspot['priority'] = str(row.get('priority', hotspot.get('priority', 'unassigned')))
        if hotspot.get('coverage_href') is None:
            hotspot['coverage_href'] = f"coverage.html#stale-priority-{_slugify_anchor_token(country_id)}"
        hotspot['freshness_hours'] = row.get('freshness_hours')

    historical_replay_summary = validation_view_model.get('historical_replay_summary', {})
    attention_cases = historical_replay_summary.get('attention_cases', []) if isinstance(historical_replay_summary, dict) else []
    for item in attention_cases:
        if not isinstance(item, dict):
            continue
        country_id = str(item.get('country_id', 'UNKNOWN'))
        hotspot = _country_row(country_id)
        hotspot['signals'].add('validation_attention')
        hotspot['attention_case_ids'].append(str(item.get('case_id', 'unknown')))
        hotspot['attention_cases'].append(dict(item))

    rows: list[dict[str, Any]] = []
    for country_id, hotspot in hotspots.items():
        signals = [signal for signal in ('country_gap', 'stale_priority', 'validation_attention') if signal in hotspot['signals']]
        attention_case_ids = sorted(hotspot['attention_case_ids'])
        top_attention_case = hotspot['attention_cases'][0] if hotspot['attention_cases'] else {}
        missing_domains = sorted(hotspot['missing_domains'])
        recommended_next_check = 'Coverage review'
        if 'country_gap' in hotspot['signals'] and 'validation_attention' in hotspot['signals']:
            recommended_next_check = 'Coverage + Validation review'
        elif 'validation_attention' in hotspot['signals']:
            recommended_next_check = 'Validation review'
        elif 'stale_priority' in hotspot['signals']:
            recommended_next_check = 'Coverage freshness review'
        rows.append(
            {
                'country_id': country_id,
                'signal_count': len(signals),
                'signals': signals,
                'priority': str(hotspot.get('priority', 'unassigned')),
                'freshness_hours': hotspot.get('freshness_hours'),
                'missing_domains': missing_domains,
                'attention_case_count': len(attention_case_ids),
                'top_attention_case_id': attention_case_ids[0] if attention_case_ids else None,
                'coverage_href': hotspot.get('coverage_href'),
                'validation_href': (
                    f"validation.html#attention-case-{_slugify_anchor_token(attention_case_ids[0])}"
                    if attention_case_ids else None
                ),
                'coverage_prefill_href': _coverage_prefill_href(
                    country_id=country_id,
                    focus_section='stale_priority' if 'stale_priority' in hotspot['signals'] and 'country_gap' not in hotspot['signals'] else 'country_gap',
                    missing_domains=missing_domains,
                ),
                'validation_prefill_href': (
                    _validation_prefill_href(
                        country_id=country_id,
                        case_id=str(top_attention_case.get('case_id', attention_case_ids[0] if attention_case_ids else 'unknown')),
                        attention_reason=str(top_attention_case.get('attention_reason', 'validation_attention')),
                    )
                    if attention_case_ids else None
                ),
                'recommended_next_check': recommended_next_check,
            }
        )

    rows.sort(
        key=lambda row: (
            -int(row.get('signal_count', 0)),
            _analyst_priority_sort_key(str(row.get('priority', 'unassigned'))),
            -int(row.get('attention_case_count', 0)),
            -(float(row.get('freshness_hours')) if isinstance(row.get('freshness_hours'), (int, float)) else -1.0),
            str(row.get('country_id', 'UNKNOWN')),
        )
    )
    return {
        'row_count': len(rows),
        'multi_signal_country_count': sum(1 for row in rows if int(row.get('signal_count', 0)) > 1),
        'rows': rows,
    }



def _build_analyst_briefing_view_model(
    *,
    readiness_view_model: dict[str, Any],
    release_gate_view_model: dict[str, Any] | None = None,
    operator_release_summary_view_model: dict[str, Any] | None = None,
    operator_blocker_causality_view_model: dict[str, Any] | None = None,
    operator_operability_cluster_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_action_plan_view_model: dict[str, Any] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    validation_view_model: dict[str, Any] | None = None,
    traceability_view_model: dict[str, Any] | None = None,
    repo_closure_view_model: dict[str, Any] | None = None,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    release_gate_view_model = release_gate_view_model or {}
    operator_release_summary_view_model = operator_release_summary_view_model or {}
    operator_blocker_causality_view_model = operator_blocker_causality_view_model or {}
    operator_operability_cluster_view_model = operator_operability_cluster_view_model or {}
    operator_stale_remediation_action_plan_view_model = operator_stale_remediation_action_plan_view_model or {}
    system_status_read_model = system_status_read_model or {}
    validation_view_model = validation_view_model or {}
    traceability_view_model = traceability_view_model or {}
    repo_closure_view_model = repo_closure_view_model or {}
    visibility = _country_coverage_visibility_rows(system_status_read_model)

    def _append_item(*, category: str, title: str, why_it_matters: str, recommended_next_check: str, evidence_source: str, target_page: str) -> None:
        items.append(
            {
                'category': category,
                'title': title,
                'why_it_matters': why_it_matters,
                'recommended_next_check': recommended_next_check,
                'evidence_source': evidence_source,
                'target_page': target_page,
            }
        )

    primary_root_cause_gate_id = operator_blocker_causality_view_model.get('primary_root_cause_gate_id')
    release_verdict = str(readiness_view_model.get('release_verdict', 'unknown')).lower()
    gate_verdict = str(release_gate_view_model.get('gate_verdict', 'unknown')).lower()
    release_not_green = release_verdict not in {'ready', 'pass', 'ok', 'green'} or gate_verdict not in {'go', 'ready', 'pass', 'ok', 'green'}
    if release_not_green and (primary_root_cause_gate_id or int(operator_release_summary_view_model.get('failed_gate_count', 0) or 0) > 0):
        root_cause_text = str(primary_root_cause_gate_id or 'release_gate_go')
        _append_item(
            category='release_blocker',
            title=f'Release blocker: {root_cause_text}',
            why_it_matters=f"Release verdict is {readiness_view_model.get('release_verdict', 'unknown')} and gate verdict is {release_gate_view_model.get('gate_verdict', 'unknown')}.",
            recommended_next_check=str(operator_blocker_causality_view_model.get('operator_next_action') or operator_release_summary_view_model.get('operator_next_action') or 'Inspect release blockers.'),
            evidence_source='release_evidence_assessment.json',
            target_page='readiness.html',
        )

    country_gap_rows = [row for row in visibility.get('country_gap_rows', []) if isinstance(row, dict)]
    if country_gap_rows:
        top_gap = country_gap_rows[0]
        gap_country = str(top_gap.get('country_id', 'UNKNOWN'))
        missing_domains = [str(domain) for domain in top_gap.get('missing_domains', [])]
        _append_item(
            category='country_gap',
            title=f"Country gap: {gap_country} missing {', '.join(missing_domains) or 'unknown domains'}",
            why_it_matters=f"Country coverage is incomplete for {gap_country}.",
            recommended_next_check='Inspect country/domain gap details and source diagnostics in Coverage.',
            evidence_source='system_status.json country_coverage_visibility.country_gap_rows',
            target_page='coverage.html',
        )

    historical_replay_summary = validation_view_model.get('historical_replay_summary', {})
    attention_cases = [item for item in historical_replay_summary.get('attention_cases', []) if isinstance(item, dict)] if isinstance(historical_replay_summary, dict) else []
    if attention_cases:
        top_case = attention_cases[0]
        _append_item(
            category='validation_attention',
            title=f"Validation attention: {top_case.get('case_id', 'unknown')}",
            why_it_matters=f"{top_case.get('country_id', 'unknown')} needs review because {top_case.get('attention_reason', 'validation_attention')}.",
            recommended_next_check=str(top_case.get('suggested_next_action', 'Review validation evidence.')),
            evidence_source='validation_backtest.json historical_replay_summary.attention_cases',
            target_page='validation.html',
        )

    traceability_summary = traceability_view_model.get('summary', {}) if isinstance(traceability_view_model, dict) else {}
    traceability_missing_mappings = int(traceability_summary.get('missing_requirement_mapping_count', 0) or 0)
    traceability_orphans = int(traceability_summary.get('orphan_mapped_requirement_count', 0) or 0)
    traceability_unhealthy_slices = int(traceability_summary.get('unhealthy_slice_count', 0) or 0)
    traceability_closure_at_risk = int(traceability_summary.get('closure_at_risk', 0) or 0)
    if traceability_missing_mappings or traceability_orphans or traceability_unhealthy_slices or traceability_closure_at_risk:
        traceability_title_parts = []
        if traceability_missing_mappings:
            traceability_title_parts.append(f"{traceability_missing_mappings} missing mappings")
        if traceability_unhealthy_slices:
            traceability_title_parts.append(f"{traceability_unhealthy_slices} unhealthy slices")
        if traceability_closure_at_risk:
            traceability_title_parts.append(f"{traceability_closure_at_risk} at-risk closures")
        if traceability_orphans:
            traceability_title_parts.append(f"{traceability_orphans} orphan mappings")
        _append_item(
            category='traceability_risk',
            title=f"Traceability risk: {', '.join(traceability_title_parts) or 'inspect integrity summary'}",
            why_it_matters=(
                "Traceability integrity still has "
                f"{traceability_missing_mappings} missing mappings, {traceability_unhealthy_slices} unhealthy slices, "
                f"and {traceability_closure_at_risk} closure-at-risk items."
            ),
            recommended_next_check='Inspect traceability.html and repo closure slice details.',
            evidence_source='traceability_lineage.json + repo_closure.json',
            target_page='traceability.html',
        )

    operator_operability_status = str(operator_operability_cluster_view_model.get('cluster_status', 'unknown')).lower()
    operator_operability_failed = int(operator_operability_cluster_view_model.get('failed_gate_count', 0) or 0)
    if operator_operability_cluster_view_model and (operator_operability_status not in {'healthy', 'green', 'ok', 'pass'} or operator_operability_failed > 0):
        _append_item(
            category='operability_cluster',
            title=f"Operability cluster: {operator_operability_status}",
            why_it_matters=(
                f"Stakeholder flows and browser gates are not fully green: {operator_operability_failed} failed gates reported."
            ),
            recommended_next_check=str(
                operator_operability_cluster_view_model.get('operator_next_action')
                or 'Review readiness and operability cluster details.'
            ),
            evidence_source='release_evidence_assessment.json operator_operability_cluster',
            target_page='readiness.html',
        )

    stale_priority_watchlist = [row for row in visibility.get('stale_priority_watchlist', []) if isinstance(row, dict)]
    if stale_priority_watchlist:
        top_stale = stale_priority_watchlist[0]
        _append_item(
            category='stale_priority',
            title=f"Stale priority: {top_stale.get('country_id', 'UNKNOWN')}",
            why_it_matters=f"Priority {top_stale.get('priority', 'n/a')} country has {top_stale.get('freshness_hours', 'n/a')} stale hours.",
            recommended_next_check='Inspect stale coverage priority queue and remediation watchlist.',
            evidence_source='system_status.json country_coverage_visibility.stale_priority_watchlist',
            target_page='coverage.html',
        )

    if operator_stale_remediation_action_plan_view_model:
        action_count = int(operator_stale_remediation_action_plan_view_model.get('action_count', 0) or 0)
        next_action_id = str(operator_stale_remediation_action_plan_view_model.get('next_action_id', 'n/a'))
        if action_count > 0:
            _append_item(
                category='stale_remediation_action_plan',
                title=f'Stale remediation action plan: {next_action_id}',
                why_it_matters=f"Stale-remediation planning still has {action_count} actionable steps queued.",
                recommended_next_check=str(operator_stale_remediation_action_plan_view_model.get('operator_next_action') or 'Review stale remediation action plan.'),
                evidence_source='release_failure_drill_report.json operator_stale_remediation_action_plan',
                target_page='readiness.html',
            )

    for rank, item in enumerate(items, start=1):
        item['rank'] = rank

    top_item = items[0] if items else {}
    target_page_counts: dict[str, int] = {}
    for item in items:
        target_page = str(item.get('target_page', 'n/a'))
        target_page_counts[target_page] = target_page_counts.get(target_page, 0) + 1

    return {
        'run_id': readiness_view_model.get('run_id'),
        'release_verdict': readiness_view_model.get('release_verdict'),
        'item_count': len(items),
        'release_blocker_count': sum(1 for item in items if item.get('category') == 'release_blocker'),
        'country_gap_count': sum(1 for item in items if item.get('category') == 'country_gap'),
        'validation_attention_count': sum(1 for item in items if item.get('category') == 'validation_attention'),
        'traceability_risk_count': sum(1 for item in items if item.get('category') == 'traceability_risk'),
        'operability_cluster_count': sum(1 for item in items if item.get('category') == 'operability_cluster'),
        'stale_priority_count': sum(1 for item in items if item.get('category') == 'stale_priority'),
        'stale_remediation_action_plan_count': sum(1 for item in items if item.get('category') == 'stale_remediation_action_plan'),
        'primary_item_title': top_item.get('title', 'n/a'),
        'primary_item_category': top_item.get('category', 'n/a'),
        'primary_item_target_page': top_item.get('target_page', 'n/a'),
        'primary_item_next_check': top_item.get('recommended_next_check', 'n/a'),
        'primary_item_evidence_source': top_item.get('evidence_source', 'n/a'),
        'target_page_counts': target_page_counts,
        'country_hotspot_matrix': _build_analyst_country_hotspot_matrix(
            system_status_read_model=system_status_read_model,
            validation_view_model=validation_view_model,
        ),
        'items': items,
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
        f"<tr {_coverage_focus_row_attrs(country_id=str(row.get('country_id', 'unknown')), focus_section='stale_priority')}>"
        f"<td>{html.escape(str(row.get('priority_rank', 'n/a')))}</td>"
        f"<td><span id='stale-priority-{html.escape(_slugify_anchor_token(str(row.get('country_id', 'unknown'))))}'>{html.escape(str(row.get('country_id', 'unknown')))}</span></td>"
        f"<td>{html.escape(str(row.get('priority', 'unassigned')))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('source_depth_band', 'minimal')))}</td>"
        "</tr>"
        for row in visibility.get('stale_priority_watchlist', [])
    ) or "<tr><td colspan='5'>No stale-country remediation priorities recorded.</td></tr>"
    return (
        "<h3 id='coverage-focus-section-stale-priority'>Stale Coverage Priority Queue</h3>"
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
        f"<tr {_coverage_focus_row_attrs(country_id=str(row.get('country_id', 'n/a')), focus_section='country_gap', missing_domains=list(row.get('missing_domains', [])))} >"
        f"<td><span id='country-gap-{html.escape(_slugify_anchor_token(str(row.get('country_id', 'n/a'))))}'>{html.escape(str(row.get('country_id', 'n/a')))}</span></td>"
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
        f"<tr {_coverage_focus_row_attrs(country_id=str(row.get('country_id', 'n/a')), focus_section='country_gap', missing_domains=list(row.get('missing_domains', [])))} >"
        f"<td><span id='country-gap-{html.escape(_slugify_anchor_token(str(row.get('country_id', 'n/a'))))}'>{html.escape(str(row.get('country_id', 'n/a')))}</span></td>"
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
        "<h3 id='coverage-focus-section-country-gap'>Country Coverage / Gap Matrix</h3>"
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
    from siasa.gui.world_map_paths import COUNTRY_PATHS  # type: ignore[import]

    metadata_lookup = _country_metadata_lookup()
    coverage_by_country = {
        str(row.get('country_id', 'UNKNOWN')): row
        for row in (coverage_visibility or {}).get('country_freshness_rows', [])
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
            'freshness_hours': str(country_visibility.get('freshness_hours', '')),
            'anomaly_score': str(country.get('anomaly_score', '')),
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

    # Build SVG path elements — all countries from Natural Earth
    # MVP (active) countries get status color; all others get neutral background fill
    path_elements: list[str] = []
    for iso3, (cname, path_d) in sorted(COUNTRY_PATHS.items()):
        data = country_data.get(iso3, {})
        has_data = iso3 in country_data
        fill = html.escape(data['color']) if has_data else '#1a2540'
        stroke = html.escape(data.get('freshness_color', '#263050')) if has_data else '#263050'
        stroke_w = '0.5' if not has_data else '0.7'
        href = html.escape(data.get('href', 'none'))
        status = html.escape(data.get('status', ''))
        freshness = html.escape(data.get('freshness_label', ''))
        anomaly_score = html.escape(data.get('anomaly_score', ''))
        freshness_hours = html.escape(data.get('freshness_hours', ''))
        css_class = 'country-mvp' if has_data else 'country-bg'
        cursor = 'pointer' if has_data else 'default'
        path_elements.append(
            f"<path id='country-{iso3}' class='{css_class}' "
            f"data-iso3='{iso3}' data-name='{html.escape(cname)}' "
            f"data-href='{href}' data-status='{status}' data-freshness='{freshness_hours}' "
            f"data-anomaly-score='{anomaly_score}' "
            f"d='{path_d}' fill='{fill}' stroke='{stroke}' stroke-width='{stroke_w}' "
            f"style='cursor:{cursor};transition:fill .15s,stroke .15s,stroke-width .15s;'>"
            f"<title>{html.escape(iso3)} — {html.escape(cname)}"
            + (f" — {status}" if status else "") +
            "</title></path>"
        )

    map_js = """\
<script>
(function(){
  var sel = null;
  var HOV_F = 'rgba(78,222,163,0.35)';
  var SEL_F = '#4edea3';
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
    el.style.fill = el.dataset.defFill || '#1a2540';
    el.style.stroke = el.dataset.defStroke || '#263050';
    el.style.strokeWidth = el.dataset.defSw || '0.5';
  }

  document.querySelectorAll('.country-mvp').forEach(function(el){
    el.dataset.defFill = el.getAttribute('fill');
    el.dataset.defStroke = el.getAttribute('stroke');
    el.dataset.defSw = el.getAttribute('stroke-width');

    el.addEventListener('mouseenter', function(){
      if(el !== sel){
        el.style.fill = HOV_F;
        el.style.stroke = HOV_S;
        el.style.strokeWidth = '1.5';
      }
      if(infoEl){ infoEl.textContent = el.dataset.name + ' (' + el.dataset.iso3 + ')' + (el.dataset.status ? ' — ' + el.dataset.status : ''); }
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
        el.style.strokeWidth = '2';
        sel = el;
        if(panelEl){ panelEl.style.display='flex'; }
        if(panelName){ panelName.textContent = el.dataset.name; }
        if(panelIso){ panelIso.textContent = el.dataset.iso3; }
        if(panelStatus){ panelStatus.textContent = el.dataset.status || '—'; }
        if(panelFresh){ panelFresh.textContent = el.dataset.freshness || '—'; }
        if(panelLink){
          var h = el.dataset.href;
          if(h && h !== 'none'){
            panelLink.innerHTML = '<a href="' + h + '" style="color:#4edea3;font-weight:600;">→ Country Profile</a>';
          } else {
            panelLink.innerHTML = '<span style="color:#6b7d99;">No profile available</span>';
          }
        }
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

    # Graticule lines (subtle grid every 30°)
    graticule_lines = []
    for lon in range(-180, 181, 30):
        x = (lon + 180) * (960 / 360)
        graticule_lines.append(
            f"<line x1='{x:.0f}' y1='0' x2='{x:.0f}' y2='500' "
            f"stroke='rgba(78,222,163,.04)' stroke-width='0.5'/>"
        )
    for lat in range(-90, 91, 30):
        y = (90 - lat) * (500 / 180)
        graticule_lines.append(
            f"<line x1='0' y1='{y:.0f}' x2='960' y2='{y:.0f}' "
            f"stroke='rgba(78,222,163,.04)' stroke-width='0.5'/>"
        )
    # Equator highlight
    graticule_lines.append(
        "<line x1='0' y1='250' x2='960' y2='250' "
        "stroke='rgba(78,222,163,.1)' stroke-width='0.5'/>"
    )

    # Region labels (repositioned for proper equirectangular)
    region_labels = [
        (85, 460, "N.AMERICA"),
        (330, 115, "EUROPE"),
        (610, 145, "ASIA"),
        (295, 310, "AFRICA"),
        (740, 415, "OCEANIA"),
        (145, 330, "S.AMERICA"),
    ]
    label_els = "".join(
        f"<text x='{x}' y='{y}' font-size='8' fill='rgba(78,222,163,.25)' "
        f"font-family='Space Grotesk,monospace' font-weight='700' "
        f"letter-spacing='.12em'>{lbl}</text>"
        for x, y, lbl in region_labels
    )

    svg_html = (
        f"<svg id='world-map-svg' viewBox='0 0 960 500' "
        f"style='width:100%;max-width:960px;height:auto;display:block;"
        f"background:#0b1326;border:1px solid rgba(78,222,163,.1);"
        f"border-radius:2px;cursor:default;' "
        f"role='img' aria-label='SIASA World Anomaly Map'>"
        f"<rect width='960' height='500' fill='#0b1326'/>"
        + "".join(graticule_lines)
        + "".join(path_elements)
        + label_els
        + f"</svg>"
        + map_js
    )

    overlay_controls = (
        "<div id='map-overlay-controls' style='display:flex;gap:6px;margin-bottom:8px;'>"
        "<button class='map-overlay-btn' data-overlay='status' style='background:#1a2540;color:#4edea3;border:1px solid #4edea3;padding:4px 10px;border-radius:2px;cursor:pointer;font-size:11px;font-family:Space Grotesk,monospace;font-weight:700;'>Status</button>"
        "<button class='map-overlay-btn' data-overlay='anomaly' style='background:#1a2540;color:#6b7d99;border:1px solid #263050;padding:4px 10px;border-radius:2px;cursor:pointer;font-size:11px;font-family:Space Grotesk,monospace;'>Anomaly Score</button>"
        "<button class='map-overlay-btn' data-overlay='freshness' style='background:#1a2540;color:#6b7d99;border:1px solid #263050;padding:4px 10px;border-radius:2px;cursor:pointer;font-size:11px;font-family:Space Grotesk,monospace;'>Freshness</button>"
        "<button id='map-zoom-reset' style='background:#1a2540;color:#6b7d99;border:1px solid #263050;padding:4px 10px;border-radius:2px;cursor:pointer;font-size:11px;font-family:Space Grotesk,monospace;margin-left:auto;'>Reset Zoom</button>"
        "</div>"
    )
    tooltip_el = (
        "<div id='map-tooltip' style='display:none;position:fixed;z-index:9999;pointer-events:none;"
        "background:rgba(15,24,40,0.95);border:1px solid rgba(78,222,163,0.4);border-radius:3px;"
        "padding:6px 10px;font-size:11px;color:#dae2fd;font-family:Space Grotesk,monospace;"
        "max-width:220px;box-shadow:0 2px 8px rgba(0,0,0,0.4);'></div>"
    )
    zoom_pan_js = """\
<script>
(function(){
  var container = document.getElementById('map-zoom-container');
  var svgEl = document.getElementById('world-map-svg');
  var tooltip = document.getElementById('map-tooltip');
  if(!container || !svgEl) return;
  var scale = 1, panX = 0, panY = 0, dragging = false, dragStartX = 0, dragStartY = 0, panStartX = 0, panStartY = 0;
  function applyTransform(){ svgEl.style.transform = 'translate('+panX+'px,'+panY+'px) scale('+scale+')'; svgEl.style.transformOrigin = '0 0'; }
  container.addEventListener('wheel', function(e){
    e.preventDefault();
    var rect = container.getBoundingClientRect();
    var mx = e.clientX - rect.left, my = e.clientY - rect.top;
    var oldScale = scale;
    scale *= e.deltaY < 0 ? 1.15 : 0.87;
    scale = Math.max(0.5, Math.min(scale, 8));
    panX = mx - (mx - panX) * (scale / oldScale);
    panY = my - (my - panY) * (scale / oldScale);
    applyTransform();
  }, {passive:false});
  container.addEventListener('mousedown', function(e){
    if(e.button !== 0) return;
    dragging = true; dragStartX = e.clientX; dragStartY = e.clientY;
    panStartX = panX; panStartY = panY;
    container.style.cursor = 'grabbing';
  });
  window.addEventListener('mousemove', function(e){
    if(!dragging) return;
    panX = panStartX + (e.clientX - dragStartX);
    panY = panStartY + (e.clientY - dragStartY);
    applyTransform();
  });
  window.addEventListener('mouseup', function(){ dragging = false; container.style.cursor = 'grab'; });
  var resetBtn = document.getElementById('map-zoom-reset');
  if(resetBtn){ resetBtn.addEventListener('click', function(){ scale=1; panX=0; panY=0; applyTransform(); }); }
  // Tooltip on hover
  document.querySelectorAll('.country-mvp').forEach(function(el){
    el.addEventListener('mousemove', function(e){
      if(!tooltip) return;
      var lines = '<b>' + (el.dataset.name||'') + '</b> (' + (el.dataset.iso3||'') + ')';
      if(el.dataset.status) lines += '<br>Status: <span style=\"color:#e3b341;\">' + el.dataset.status + '</span>';
      if(el.dataset.anomalyScore) lines += '<br>Anomaly: ' + el.dataset.anomalyScore;
      if(el.dataset.freshness) lines += '<br>Freshness: ' + el.dataset.freshness + 'h';
      tooltip.innerHTML = lines;
      tooltip.style.display = 'block';
      tooltip.style.left = (e.clientX + 12) + 'px';
      tooltip.style.top = (e.clientY - 10) + 'px';
    });
    el.addEventListener('mouseleave', function(){ if(tooltip) tooltip.style.display = 'none'; });
  });
  // Overlay switcher
  var STATUS_FILLS = {}; document.querySelectorAll('.country-mvp').forEach(function(el){ STATUS_FILLS[el.dataset.iso3] = el.dataset.defFill || el.getAttribute('fill'); });
  var ANOMALY_COLORS = {'0':'#1a3a2a','1':'#2a5a3a','2':'#4a7a2a','3':'#8a8a1a','4':'#aa5a1a','5':'#cc2a1a'};
  var FRESH_COLORS = {'fresh':'#1a5a3a','stale':'#8a5a1a','very_stale':'#aa2a1a','unknown':'#1a2540'};
  function anomalyBucket(s){ var v=parseFloat(s); if(isNaN(v)) return '0'; if(v<0.2) return '0'; if(v<0.4) return '1'; if(v<0.6) return '2'; if(v<0.8) return '3'; if(v<1.0) return '4'; return '5'; }
  function freshBucket(s){ var v=parseInt(s); if(isNaN(v)) return 'unknown'; if(v<48) return 'fresh'; if(v<168) return 'stale'; return 'very_stale'; }
  function applyOverlay(mode){
    document.querySelectorAll('.map-overlay-btn').forEach(function(b){
      if(b.dataset.overlay === mode){ b.style.color='#4edea3'; b.style.borderColor='#4edea3'; b.style.fontWeight='700'; }
      else { b.style.color='#6b7d99'; b.style.borderColor='#263050'; b.style.fontWeight='400'; }
    });
    document.querySelectorAll('.country-mvp').forEach(function(el){
      var newFill;
      if(mode === 'status'){ newFill = STATUS_FILLS[el.dataset.iso3] || '#1a2540'; }
      else if(mode === 'anomaly'){ newFill = ANOMALY_COLORS[anomalyBucket(el.dataset.anomalyScore||'0')] || '#1a2540'; }
      else if(mode === 'freshness'){ newFill = FRESH_COLORS[freshBucket(el.dataset.freshness||'')] || '#1a2540'; }
      else { newFill = STATUS_FILLS[el.dataset.iso3] || '#1a2540'; }
      el.style.fill = newFill;
      el.dataset.defFill = newFill;
    });
  }
  document.querySelectorAll('.map-overlay-btn').forEach(function(btn){
    btn.addEventListener('click', function(){ applyOverlay(btn.dataset.overlay); });
  });
})();
</script>"""

    return (
        "<p style='font-size:11px;color:#6b7d99;margin-bottom:6px;font-family:Space Grotesk,monospace;'>"
        "Hover to identify · Click to select · Scroll to zoom · Drag to pan · Use overlay buttons to switch coloring</p>"
        + overlay_controls
        + tooltip_el
        + "<div id='map-zoom-container' style='overflow:hidden;max-width:960px;border-radius:2px;cursor:grab;'>"
        + info_panel
        + svg_html
        + "</div>"
        + zoom_pan_js
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
    operational_evidence_lane_path = readmodels_dir / 'operational_evidence_lane.json'
    if operational_evidence_lane_path.exists():
        operational_evidence_lane = _load_json(operational_evidence_lane_path)
        if isinstance(operational_evidence_lane, dict):
            system_status_read_model['operational_evidence_lane'] = operational_evidence_lane

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
    release_demo_package_view_model = None
    release_demo_package_view_path = readmodels_dir / 'release_demo_package.json'
    if release_demo_package_view_path.exists():
        release_demo_package_view_model = _load_json(release_demo_package_view_path)
    release_failure_drill_report_view_model = None
    release_gate_view_model = None
    release_gate_view_path = readmodels_dir / 'release_gate.json'
    if release_gate_view_path.exists():
        release_gate_view_model = _load_json(release_gate_view_path)
    stakeholder_functional_closure_view_model = None
    stakeholder_functional_closure_view_path = readmodels_dir / 'stakeholder_functional_closure.json'
    if stakeholder_functional_closure_view_path.exists():
        stakeholder_functional_closure_view_model = _load_json(stakeholder_functional_closure_view_path)
    stakeholder_e2e_flow_coverage_view_model = None
    stakeholder_e2e_flow_coverage_view_path = readmodels_dir / 'stakeholder_e2e_flow_coverage.json'
    if stakeholder_e2e_flow_coverage_view_path.exists():
        stakeholder_e2e_flow_coverage_view_model = _load_json(stakeholder_e2e_flow_coverage_view_path)
    release_readiness_index_view_model = None
    release_readiness_index_view_path = readmodels_dir / 'release_readiness_index.json'
    if release_readiness_index_view_path.exists():
        release_readiness_index_view_model = _load_json(release_readiness_index_view_path)

    stakeholder_e2e_ui_smoke_view_model = None
    stakeholder_e2e_ui_smoke_view_path = readmodels_dir / 'stakeholder_e2e_ui_smoke.json'
    if stakeholder_e2e_ui_smoke_view_path.exists():
        stakeholder_e2e_ui_smoke_view_model = _load_json(stakeholder_e2e_ui_smoke_view_path)

    operator_release_summary_view_model = None
    operator_blocker_causality_view_model = None
    operator_operability_cluster_view_model = None
    release_evidence_assessment_path = readmodels_dir / 'release_evidence_assessment.json'
    if release_evidence_assessment_path.exists():
        release_evidence_assessment = _load_json(release_evidence_assessment_path)
        if isinstance(release_evidence_assessment, dict):
            maybe_operator_summary = release_evidence_assessment.get('operator_release_summary')
            if isinstance(maybe_operator_summary, dict):
                operator_release_summary_view_model = maybe_operator_summary
            maybe_operator_blocker_causality = release_evidence_assessment.get('operator_blocker_causality')
            if isinstance(maybe_operator_blocker_causality, dict):
                operator_blocker_causality_view_model = maybe_operator_blocker_causality
            maybe_operator_operability_cluster = release_evidence_assessment.get('operator_operability_cluster')
            if isinstance(maybe_operator_operability_cluster, dict):
                operator_operability_cluster_view_model = maybe_operator_operability_cluster

    operator_failure_drill_digest_view_model = None
    operator_failure_drill_trend_baseline_view_model = None
    operator_recurrence_aware_remediation_prioritization_view_model = None
    operator_failure_drill_delta_ledger_view_model = None
    operator_remediation_execution_loop_view_model = None
    operator_stale_remediation_closure_drill_view_model = None
    operator_stale_remediation_action_plan_view_model = None
    release_failure_drill_report_path = readmodels_dir / 'release_failure_drill_report.json'
    if release_failure_drill_report_path.exists():
        release_failure_drill_report = _load_json(release_failure_drill_report_path)
        if isinstance(release_failure_drill_report, dict):
            release_failure_drill_report_view_model = release_failure_drill_report
            maybe_operator_digest = release_failure_drill_report.get('operator_failure_drill_digest')
            if isinstance(maybe_operator_digest, dict):
                operator_failure_drill_digest_view_model = maybe_operator_digest
            maybe_operator_trend_baseline = release_failure_drill_report.get('operator_failure_drill_trend_baseline')
            if isinstance(maybe_operator_trend_baseline, dict):
                operator_failure_drill_trend_baseline_view_model = maybe_operator_trend_baseline
            maybe_operator_prioritization = release_failure_drill_report.get('operator_recurrence_aware_remediation_prioritization')
            if isinstance(maybe_operator_prioritization, dict):
                operator_recurrence_aware_remediation_prioritization_view_model = maybe_operator_prioritization
            maybe_operator_delta_ledger = release_failure_drill_report.get('operator_failure_drill_delta_ledger')
            if isinstance(maybe_operator_delta_ledger, dict):
                operator_failure_drill_delta_ledger_view_model = maybe_operator_delta_ledger
            maybe_operator_execution_loop = release_failure_drill_report.get('operator_remediation_execution_loop')
            if isinstance(maybe_operator_execution_loop, dict):
                operator_remediation_execution_loop_view_model = maybe_operator_execution_loop
            maybe_operator_stale_closure = release_failure_drill_report.get('operator_stale_remediation_closure_drill')
            if isinstance(maybe_operator_stale_closure, dict):
                operator_stale_remediation_closure_drill_view_model = maybe_operator_stale_closure
            maybe_operator_stale_action_plan = release_failure_drill_report.get('operator_stale_remediation_action_plan')
            if isinstance(maybe_operator_stale_action_plan, dict):
                operator_stale_remediation_action_plan_view_model = maybe_operator_stale_action_plan

    # Load analytics artifacts (Phase 4-6 module outputs)
    analytics_view_model: dict[str, Any] | None = None
    analytics_dir = artifacts_dir / 'analytics'
    if analytics_dir.exists():
        def _load_analytics_json(name: str) -> Any:
            p = analytics_dir / name
            return _load_json(p) if p.exists() else None
        fusion = _load_analytics_json('cross_domain_fusion.json')
        bayesian = _load_analytics_json('bayesian_estimates.json')
        uncertainty = _load_analytics_json('uncertainty_budgets.json')
        rule_evals = _load_analytics_json('rule_evaluations.json')
        dep_graph = _load_analytics_json('dependency_graph.json')
        prov_chain = _load_analytics_json('provenance_chain.json')
        epi = _load_analytics_json('info_epidemiology.json')
        if any(x is not None for x in [fusion, bayesian, uncertainty, rule_evals, dep_graph, prov_chain, epi]):
            analytics_view_model = {
                'cross_domain_fusion': fusion or {},
                'bayesian_estimates': bayesian or {},
                'uncertainty_budgets': uncertainty or {},
                'rule_evaluations': rule_evals or [],
                'dependency_graph': dep_graph or {},
                'provenance_chain': prov_chain or {},
                'info_epidemiology': epi or {},
            }

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
        'release_demo_package_view_model': release_demo_package_view_model,
        'release_failure_drill_report_view_model': release_failure_drill_report_view_model,
        'release_gate_view_model': release_gate_view_model,
        'stakeholder_functional_closure_view_model': stakeholder_functional_closure_view_model,
        'stakeholder_e2e_flow_coverage_view_model': stakeholder_e2e_flow_coverage_view_model,
        'release_readiness_index_view_model': release_readiness_index_view_model,
        'stakeholder_e2e_ui_smoke_view_model': stakeholder_e2e_ui_smoke_view_model,
        'operator_release_summary_view_model': operator_release_summary_view_model,
        'operator_blocker_causality_view_model': operator_blocker_causality_view_model,
        'operator_operability_cluster_view_model': operator_operability_cluster_view_model,
        'operator_failure_drill_digest_view_model': operator_failure_drill_digest_view_model,
        'operator_failure_drill_trend_baseline_view_model': operator_failure_drill_trend_baseline_view_model,
        'operator_recurrence_aware_remediation_prioritization_view_model': operator_recurrence_aware_remediation_prioritization_view_model,
        'operator_failure_drill_delta_ledger_view_model': operator_failure_drill_delta_ledger_view_model,
        'operator_remediation_execution_loop_view_model': operator_remediation_execution_loop_view_model,
        'operator_stale_remediation_closure_drill_view_model': operator_stale_remediation_closure_drill_view_model,
        'operator_stale_remediation_action_plan_view_model': operator_stale_remediation_action_plan_view_model,
        'analytics_view_model': analytics_view_model,
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
        "try{"
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
        "}catch(_err){return false;}"
        "}"
        "function copyOverviewFilterLink(){"
        "persistOverviewStateToHash();"
        "const status=document.getElementById('overview-link-status');"
        "const shareUrl=window.location.href;"
        "if(!navigator.clipboard||!navigator.clipboard.writeText){status.textContent='Link copy unavailable in this browser.';return;}"
        "navigator.clipboard.writeText(shareUrl).then(()=>{status.textContent='Overview link copied.';}).catch(()=>{status.textContent='Overview link copy failed.';});"
        "}"
        "function saveOverviewStateLocally(){"
        "try{"
        "window.localStorage.setItem('siasa_overview_state', JSON.stringify(getOverviewState()));"
        "document.getElementById('overview-link-status').textContent='Overview view saved.';"
        "}catch(_err){document.getElementById('overview-link-status').textContent='Overview view save unavailable.';}"
        "}"
        "function restoreOverviewStateLocally(){"
        "let saved='';"
        "try{saved=window.localStorage.getItem('siasa_overview_state')||'';}catch(_err){document.getElementById('overview-link-status').textContent='Overview view restore unavailable.';return;}"
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
    activation_summary = source_coverage_read_model.get('source_activation_readiness_summary', {})
    activation_status_counts = ', '.join(
        f"{status}: {count}"
        for status, count in sorted((activation_summary.get('status_counts') or {}).items())
    ) or 'none'
    activation_closure_counts = ', '.join(
        f"{status}: {count}"
        for status, count in sorted((activation_summary.get('closure_status_counts') or {}).items())
    ) or 'none'
    activation_summary_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(label))}</td>"
        f"<td>{html.escape(str(value))}</td>"
        "</tr>"
        for label, value in [
            ('Total credential-gated sources', activation_summary.get('total_sources', 0)),
            ('Configured ready', activation_summary.get('configured_ready_count', 0)),
            ('Blocked missing credentials', activation_summary.get('blocked_source_count', 0)),
            ('Status counts', activation_status_counts),
            ('G2 closure status', activation_summary.get('overall_closure_status', 'unknown')),
            ('Closure status counts', activation_closure_counts),
            (
                'Activated with live evidence',
                ', '.join(str(item) for item in activation_summary.get('activated_with_live_evidence_sources', [])) or 'none',
            ),
            (
                'Pending activation evidence',
                ', '.join(str(item) for item in activation_summary.get('pending_evidence_sources', [])) or 'none',
            ),
            (
                'Live fetch failed',
                ', '.join(str(item) for item in activation_summary.get('live_fetch_failed_sources', [])) or 'none',
            ),
            (
                'External blockers',
                ', '.join(str(item) for item in activation_summary.get('external_blocker_sources', [])) or 'none',
            ),
            (
                'Configured-ready sources',
                ', '.join(str(item) for item in activation_summary.get('configured_ready_sources', [])) or 'none',
            ),
            (
                'Configured-ready country scope',
                ', '.join(str(item) for item in activation_summary.get('configured_ready_applicable_countries', [])) or 'none',
            ),
            (
                'Configured-ready country count',
                activation_summary.get('configured_ready_applicable_country_count', 0),
            ),
            (
                'Blocked sources',
                ', '.join(str(item) for item in activation_summary.get('blocked_sources', [])) or 'none',
            ),
            (
                'Blocked country scope',
                ', '.join(str(item) for item in activation_summary.get('blocked_applicable_countries', [])) or 'none',
            ),
            (
                'Blocked country count',
                activation_summary.get('blocked_applicable_country_count', 0),
            ),
            ('Operator next step', activation_summary.get('operator_next_step', 'none')),
        ]
    )
    source_activation_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('source_id', '')))}</td>"
        f"<td>{html.escape(str(item.get('domain', '')))}</td>"
        f"<td>{html.escape(str(item.get('activation_status', '')))}</td>"
        f"<td>{html.escape(str(item.get('runtime_source_status', '')))}</td>"
        f"<td>{html.escape(str(item.get('activation_evidence', '')))}</td>"
        f"<td>{html.escape(str(item.get('closure_status', '')))}</td>"
        f"<td>{html.escape(str(item.get('credential_name', '')))}</td>"
        f"<td>{html.escape(str(item.get('configured', '')))}</td>"
        f"<td>{html.escape(str(item.get('provider_requirement', '')))}</td>"
        f"<td>{html.escape(', '.join(str(country_id) for country_id in item.get('applicable_country_ids', [])) or 'none')}</td>"
        f"<td>{html.escape(str(item.get('blocked_reason', '')))}</td>"
        f"<td>{html.escape(str(item.get('closure_next_step', item.get('activation_next_step', ''))))}</td>"
        "</tr>"
        for item in source_coverage_read_model.get('source_activation_readiness', [])
    ) or "<tr><td colspan='12'>No credential-gated source activation readiness recorded.</td></tr>"
    source_status_summary_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(status))}</td>"
        f"<td>{html.escape(str(count))}</td>"
        "</tr>"
        for status, count in sorted(source_coverage_read_model.get('source_status_summary', {}).items())
    ) or "<tr><td colspan='2'>No source status summary available.</td></tr>"
    coverage_focus_block = """
<h2>Source / Coverage View</h2>
<pre id='coverage-focus-summary' style='white-space:pre-wrap;background:#0d1117;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:10px;color:#c9d1d9;'>No coverage focus query parameters detected.</pre>
<style>.coverage-focus-target-active{background:rgba(78,222,163,.10);box-shadow:inset 0 0 0 1px rgba(78,222,163,.35);} .coverage-focus-target-dim{opacity:.55;} .coverage-focus-section-active{color:#4edea3;}</style>
<script>(function(){function applyCoverageFocusState(){const params=new URLSearchParams(window.location.search);const summary=document.getElementById('coverage-focus-summary');const focusCountry=(params.get('focus_country')||'').trim();const focusSection=(params.get('focus_section')||'').trim();const missingDomains=(params.get('missing_domains')||'').trim();const requestedDomains=missingDomains?missingDomains.split(',').map((item)=>item.trim()).filter(Boolean):[];const targets=Array.from(document.querySelectorAll('.coverage-focus-target'));const matchingTargets=targets.filter((row)=>{const rowCountry=(row.dataset.focusCountry||'').trim();const rowSection=(row.dataset.focusSection||'').trim();const rowMissing=(row.dataset.missingDomains||'').split(',').map((item)=>item.trim()).filter(Boolean);if(focusCountry&&rowCountry!==focusCountry){return false;}if(focusSection&&rowSection!==focusSection){return false;}if(requestedDomains.length&&!requestedDomains.every((domain)=>rowMissing.includes(domain))){return false;}return true;});targets.forEach((row)=>{row.classList.remove('coverage-focus-target-active','coverage-focus-target-dim');if(matchingTargets.length){if(matchingTargets.includes(row)){row.classList.add('coverage-focus-target-active');}else{row.classList.add('coverage-focus-target-dim');}}});const activeHeading=focusSection?document.getElementById(`coverage-focus-section-${focusSection.replace(/_/g,'-')}`):null;document.querySelectorAll("[id^='coverage-focus-section-']").forEach((node)=>node.classList.remove('coverage-focus-section-active'));if(activeHeading){activeHeading.classList.add('coverage-focus-section-active');}if(summary){if(!focusCountry&&!focusSection&&!missingDomains){summary.textContent='No coverage focus query parameters detected.';}else{const lines=['Coverage focus summary',`focus_country=${focusCountry||'n/a'}`,`focus_section=${focusSection||'n/a'}`,`missing_domains=${missingDomains||'n/a'}`,`focus_target_count=${matchingTargets.length}`];summary.textContent=lines.join('\n');}}const firstTarget=matchingTargets[0]||activeHeading;if(firstTarget&&typeof firstTarget.scrollIntoView==='function'){firstTarget.scrollIntoView({behavior:'smooth',block:'center'});}}if(document.readyState==='loading'){document.addEventListener('DOMContentLoaded',applyCoverageFocusState);}else{applyCoverageFocusState();}})();</script>
"""
    body = (
        coverage_focus_block
        + "<h3>Trust Summary</h3>"
        f"<p>Run status: <span class='status'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</span></p>"
        "<p>Source status summary keeps live, failed, degraded, and prepared-adapter access visible at a glance.</p>"
        "<table><thead><tr><th>Source Status</th><th>Count</th></tr></thead>"
        f"<tbody>{source_status_summary_rows}</tbody></table>"
        f"<h4>Data Gaps / Trust Limits</h4><ul>{trust_gaps}</ul>"
        f"<h4>Degraded Sources</h4><ul>{degraded_sources}</ul>"
        "<h4>Credential-gated Source Activation Readiness Summary</h4>"
        "<p>Provides a compact activation snapshot so operators can scan how many credential-gated sources are ready versus blocked before reading the detailed source table.</p>"
        "<p>The summary now also makes G2 closure truth explicit: whether sources are already evidenced live, still blocked externally, or still pending first governed activation evidence.</p>"
        "<table><thead><tr><th>Activation Summary</th><th>Value</th></tr></thead>"
        f"<tbody>{activation_summary_rows}</tbody></table>"
        "<h4>Credential-gated Source Activation Readiness</h4>"
        "<p>Shows whether provider-gated sources are operationally activatable in the current environment or still blocked by missing credentials/registrations.</p>"
        "<p>The table distinguishes raw activation status from runtime evidence truth (`Runtime Source Status`, `Activation Evidence`, `Closure Posture`) so configured credentials are not confused with proven live activation.</p>"
        "<p>The Next Step column turns each blocker/configured-ready state into the concrete follow-through action required for the first real credential-backed evidence run.</p>"
        "<table><thead><tr><th>Source</th><th>Domain</th><th>Activation Status</th><th>Runtime Source Status</th><th>Activation Evidence</th><th>Closure Posture</th><th>Credential</th><th>Configured</th><th>Provider Requirement</th><th>Applicable Countries</th><th>Blocked Reason</th><th>Next Step</th></tr></thead>"
        f"<tbody>{source_activation_rows}</tbody></table>"
        f"{_render_country_coverage_matrix(coverage_visibility)}"
        "<h3>Coverage / Confidence Matrix</h3>"
        "<p>Confidence Band highlights source trust at a glance while keeping freshness visible.</p>"
        "<div class='table-wrap'><table><thead><tr><th scope='col'>Source</th><th scope='col'>Confidence Band</th><th scope='col'>Confidence Meter</th><th scope='col'>Freshness (h)</th><th scope='col'>Status</th></tr></thead>"
        f"<tbody>{matrix_rows}</tbody></table></div>"
        "<div class='table-wrap'><table><thead><tr><th scope='col'>Source</th><th scope='col'>Status</th><th scope='col'>History Horizon</th><th scope='col'>Freshness (h)</th><th scope='col'>Confidence</th><th scope='col'>Record Count</th><th scope='col'>Diagnostics</th></tr></thead>"
        f"<tbody>{rows}</tbody></table></div>"
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
    def _fmt_size(size_bytes: Any) -> str:
        try:
            n = int(size_bytes)
        except (TypeError, ValueError):
            return ''
        if n < 1024:
            return f'{n} B'
        if n < 1024 * 1024:
            return f'{n // 1024} KB'
        return f'{n // (1024 * 1024)} MB'

    def _render_export_links(report_info: dict[str, Any]) -> str:
        export_links = ''.join(
            (
                f"<div><a href=\"{html.escape(str(export_file.get('href', export_file.get('relative_path', ''))))}\" download class='btn-download'>"
                f"&#9660; {html.escape(str(export_file.get('label', export_file.get('format', 'Download'))))}"
                + (f" <small>({html.escape(_fmt_size(export_file.get('size_bytes')))})</small>" if export_file.get('size_bytes') else '')
                + "</a></div>"
            )
            for export_file in report_info.get('export_files', [])
        )
        return export_links or '-'

    # Category mapping
    _CATEGORY_MAP = {
        'country_profile': 'Country Profiles',
        'domain_report': 'Domain Reports',
        'coverage': 'Coverage Reports',
        'coverage_report': 'Coverage Reports',
        'daily_snapshot': 'Daily Snapshots',
    }
    _CATEGORY_ORDER = ['Country Profiles', 'Domain Reports', 'Coverage Reports', 'Daily Snapshots', 'Other']

    report_types = sorted(report_catalog.keys())
    type_options = ''.join(
        f"<option value='{html.escape(report_type)}'>{html.escape(report_type)}</option>"
        for report_type in report_types
    )

    # Group by category
    categories: dict[str, list[tuple[str, Any]]] = {}
    for cat in _CATEGORY_ORDER:
        categories[cat] = []
    for report_type, report_info in sorted(report_catalog.items()):
        cat = _CATEGORY_MAP.get(report_type, 'Other')
        if cat not in categories:
            cat = 'Other'
        categories[cat].append((report_type, report_info))

    # Build all rows (flat list for filter script to work across groups)
    all_rows = ''.join(
        "<tr class='report-row' "
        f"data-report-type='{html.escape(report_type)}' "
        f"data-report-id='{html.escape(str(report_info.get('report_id', '')))}' "
        f"data-report-name='{html.escape(str(report_info.get('report_id', report_type)).lower())}' "
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

    # KPI bar
    _last_generated = ''
    for _ri in report_catalog.values():
        _ts = str(_ri.get('generated_at', _ri.get('snapshot_id', '')))
        if _ts and _ts > _last_generated:
            _last_generated = _ts
    kpi_bar = (
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Total Reports</span><div class='kpi-value'>{html.escape(str(len(report_catalog)))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Country Profiles</span><div class='kpi-value'>{html.escape(str(len(categories.get('Country Profiles', []))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Domain Reports</span><div class='kpi-value'>{html.escape(str(len(categories.get('Domain Reports', []))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Coverage Reports</span><div class='kpi-value'>{html.escape(str(len(categories.get('Coverage Reports', []))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Daily Snapshots</span><div class='kpi-value'>{html.escape(str(len(categories.get('Daily Snapshots', []))))}</div></div>"
        + (f"<div class='kpi-card'><span class='kpi-label'>Last Generated</span><div class='kpi-value' style='font-size:0.75rem;color:#6b7d99;'>{html.escape(_last_generated)}</div></div>" if _last_generated else '')
        + "</div>"
    )

    # Build grouped sections (hidden table rows are still in the DOM for the flat filter)
    grouped_sections = ''
    table_header = "<thead><tr><th scope='col'>Type</th><th scope='col'>Report ID</th><th scope='col'>Format</th><th scope='col'>Downloads</th><th scope='col'>Metadata</th></tr></thead>"
    for cat in _CATEGORY_ORDER:
        cat_items = categories.get(cat, [])
        if not cat_items:
            continue
        cat_rows = ''.join(
            "<tr class='report-row' "
            f"data-report-type='{html.escape(report_type)}' "
            f"data-report-id='{html.escape(str(report_info.get('report_id', '')))}' "
            f"data-report-name='{html.escape(str(report_info.get('report_id', report_type)).lower())}' "
            f"data-format='{html.escape(str(report_info.get('format', '')))}'>"
            f"<td>{html.escape(report_type)}</td>"
            f"<td>{html.escape(str(report_info.get('report_id', '')))}</td>"
            f"<td>{html.escape(str(report_info.get('format', '')))}</td>"
            f"<td>{_render_export_links(report_info)}</td>"
            f"<td>{html.escape(json.dumps({k: v for k, v in report_info.items() if k != 'export_files'}, sort_keys=True))}</td>"
            "</tr>"
            for report_type, report_info in cat_items
        )
        grouped_sections += (
            f"<details open><summary class='panel-header'>{html.escape(cat)} ({len(cat_items)})</summary>"
            f"<div class='table-wrap'><table>{table_header}<tbody>{cat_rows}</tbody></table></div>"
            "</details>"
        )

    filter_script = """
<script>
(function() {
  const typeFilter = document.getElementById('report-type-filter');
  const idFilter = document.getElementById('report-id-filter');
  const nameFilter = document.getElementById('report-name-search');
  const rows = Array.from(document.querySelectorAll('.report-row'));
  const visibleCount = document.getElementById('report-visible-count');

  function applyReportFilters() {
    const typeValue = (typeFilter ? typeFilter.value : '').trim().toLowerCase();
    const idValue = (idFilter ? idFilter.value : '').trim().toLowerCase();
    const nameValue = (nameFilter ? nameFilter.value : '').trim().toLowerCase();
    let count = 0;

    rows.forEach((row) => {
      const rowType = (row.getAttribute('data-report-type') || '').toLowerCase();
      const rowId = (row.getAttribute('data-report-id') || '').toLowerCase();
      const rowName = (row.getAttribute('data-report-name') || '').toLowerCase();
      const typeOk = !typeValue || rowType === typeValue;
      const idOk = !idValue || rowId.includes(idValue);
      const nameOk = !nameValue || rowName.includes(nameValue) || rowId.includes(nameValue) || rowType.includes(nameValue);
      const show = typeOk && idOk && nameOk;
      row.style.display = show ? '' : 'none';
      if (show) count += 1;
    });

    if (visibleCount) {
      visibleCount.textContent = String(count);
    }
  }

  if (typeFilter) typeFilter.addEventListener('change', applyReportFilters);
  if (idFilter) idFilter.addEventListener('input', applyReportFilters);
  if (nameFilter) nameFilter.addEventListener('input', applyReportFilters);
  applyReportFilters();
})();
</script>
"""
    body = (
        kpi_bar
        + "<h2>Report / Export View</h2>"
        "<h3>Evidence Summary</h3>"
        f"<p>Reports available: <strong>{html.escape(str(len(report_catalog)))}</strong></p>"
        f"<p>Download-ready artifacts: <strong>{html.escape(str(export_count))}</strong></p>"
        f"<ul>{evidence_items}</ul>"
        "<h3>Report Scope Controls</h3>"
        "<p>Filter reports by type and report ID to focus export review scope.</p>"
        "<div class='controls-bar'>"
        "<label for='report-name-search'>Search:</label> "
        "<input id='report-name-search' type='text' placeholder='Search reports...' aria-label='Search reports by name'/> "
        "<label for='report-type-filter'>Type:</label> "
        f"<select id='report-type-filter' aria-label='Filter by report type'><option value=''>All</option>{type_options}</select> "
        "<label for='report-id-filter'>Report ID contains:</label> "
        "<input id='report-id-filter' type='text' placeholder='e.g. REP-COVERAGE' aria-label='Filter by report ID'/>"
        "</div>"
        f"<p>Visible reports: <strong id='report-visible-count'>{html.escape(str(len(report_catalog)))}</strong></p>"
        + grouped_sections
        + "<details><summary class='panel-header'>All Reports (flat view)</summary>"
        f"<div class='table-wrap'><table><thead><tr><th scope='col'>Type</th><th scope='col'>Report ID</th><th scope='col'>Format</th><th scope='col'>Downloads</th><th scope='col'>Metadata</th></tr></thead>"
        f"<tbody>{all_rows}</tbody></table></div></details>"
        + filter_script
    )
    return _page("Report / Export View", body, nav_prefix=nav_prefix, available_pages=available_pages)



def _render_runs(system_status_read_model: dict[str, Any], repo_closure_view_model: dict[str, Any] | None = None, *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    def _render_evidence_link(label: str, href: Any) -> str:
        href_text = str(href or '').strip()
        if not href_text:
            return ''
        return f"<a href='{html.escape(href_text)}'>{html.escape(label)}</a>"

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
    evidence_lane = system_status_read_model.get('operational_evidence_lane', {})
    if not isinstance(evidence_lane, dict):
        evidence_lane = {}
    latest_summary = evidence_lane.get('latest_summary', {}) if isinstance(evidence_lane.get('latest_summary'), dict) else {}
    recent_runs = evidence_lane.get('recent_runs', []) if isinstance(evidence_lane.get('recent_runs'), list) else []
    combined_ce_ratio = latest_summary.get('combined_ce_ratio')
    combined_ce_ratio_text = (
        f"{float(combined_ce_ratio):.4f}"
        if isinstance(combined_ce_ratio, (int, float))
        else html.escape(str(combined_ce_ratio or 'n/a'))
    )
    governance_verdict = str(latest_summary.get('governance_verdict', 'n/a'))
    policy_gate_verdict = str(latest_summary.get('policy_gate_verdict', 'n/a'))
    release_verdict = str(latest_summary.get('release_verdict', 'n/a'))
    readiness_interpretation = str(latest_summary.get('readiness_interpretation', 'n/a'))
    known_gap_count = int(latest_summary.get('known_gap_count', 0) or 0)

    def _format_history_ratio(value: Any) -> str:
        return f"{float(value):.4f}" if isinstance(value, (int, float)) else str(value or 'n/a')

    operator_next_action = html.escape(str(latest_summary.get('operator_next_action', 'n/a')))
    verification_policy = latest_summary.get('verification_policy', {}) if isinstance(latest_summary.get('verification_policy'), dict) else {}
    verification_mode = str(verification_policy.get('mode') or 'n/a')
    enabled_verification_overrides = [
        str(item).strip()
        for item in (verification_policy.get('enabled_overrides') or [])
        if str(item).strip()
    ]
    verification_override_text = ', '.join(enabled_verification_overrides) if enabled_verification_overrides else 'none'
    evidence_links = latest_summary.get('evidence_links', {}) if isinstance(latest_summary.get('evidence_links'), dict) else {}
    latest_evidence_link_items = ''.join(
        f"<li>{link}</li>"
        for link in (
            _render_evidence_link('Bundle index', evidence_links.get('bundle_index_href')),
            _render_evidence_link('Coverage page', evidence_links.get('coverage_page_href')),
            _render_evidence_link('Coverage JSON', evidence_links.get('coverage_json_href')),
            _render_evidence_link('System status JSON', evidence_links.get('system_status_json_href')),
            _render_evidence_link('Readiness page', evidence_links.get('readiness_page_href')),
            _render_evidence_link('Readiness JSON', evidence_links.get('readiness_json_href')),
            _render_evidence_link('Release package page', evidence_links.get('release_package_page_href')),
            _render_evidence_link('Release package JSON', evidence_links.get('release_package_json_href')),
            _render_evidence_link('Release gate JSON', evidence_links.get('release_gate_json_href')),
        )
        if link
    ) or "<li>none</li>"
    latest_bundle_root = html.escape(str(latest_summary.get('bundle_root', 'n/a')))
    latest_artifacts_dir = html.escape(str(latest_summary.get('artifacts_dir', 'n/a')))
    latest_gui_index = html.escape(str(latest_summary.get('gui_index', 'n/a')))
    latest_share_refs = latest_summary.get('share_refs', {}) if isinstance(latest_summary.get('share_refs'), dict) else {}
    latest_share_ref_items = ''.join(
        f"<li><code>{html.escape(str(value))}</code></li>"
        for value in latest_share_refs.values()
        if str(value).strip()
    ) or "<li>none</li>"
    latest_handoff_summary = html.escape(str(latest_summary.get('handoff_summary', 'n/a')))
    latest_triage_tag = html.escape(str(latest_summary.get('triage_tag', 'n/a')))
    latest_triage_summary = html.escape(str(latest_summary.get('triage_summary', 'n/a')))
    latest_breadth_coverage_tag = html.escape(str(latest_summary.get('breadth_coverage_tag', 'n/a')))
    latest_breadth_coverage_summary = html.escape(str(latest_summary.get('breadth_coverage_summary', 'n/a')))

    def _render_history_evidence_cell(item: dict[str, Any]) -> str:
        item_links = item.get('evidence_links', {}) if isinstance(item.get('evidence_links'), dict) else {}
        page_links = ''.join(
            part
            for part in (
                _render_evidence_link('Bundle', item_links.get('bundle_index_href')),
                ' | ' if item_links.get('bundle_index_href') and item_links.get('coverage_page_href') else '',
                _render_evidence_link('Coverage', item_links.get('coverage_page_href')),
                ' | ' if (item_links.get('bundle_index_href') or item_links.get('coverage_page_href')) and item_links.get('readiness_page_href') else '',
                _render_evidence_link('Readiness', item_links.get('readiness_page_href')),
                ' | ' if (item_links.get('bundle_index_href') or item_links.get('coverage_page_href') or item_links.get('readiness_page_href')) and item_links.get('release_package_page_href') else '',
                _render_evidence_link('Release', item_links.get('release_package_page_href')),
            )
        )
        json_links = ''.join(
            part
            for part in (
                _render_evidence_link('Coverage JSON', item_links.get('coverage_json_href')),
                ' | ' if item_links.get('coverage_json_href') and item_links.get('system_status_json_href') else '',
                _render_evidence_link('System JSON', item_links.get('system_status_json_href')),
                ' | ' if (item_links.get('coverage_json_href') or item_links.get('system_status_json_href')) and item_links.get('readiness_json_href') else '',
                _render_evidence_link('Readiness JSON', item_links.get('readiness_json_href')),
                ' | ' if (item_links.get('coverage_json_href') or item_links.get('system_status_json_href') or item_links.get('readiness_json_href')) and item_links.get('release_package_json_href') else '',
                _render_evidence_link('Release JSON', item_links.get('release_package_json_href')),
                ' | ' if (item_links.get('coverage_json_href') or item_links.get('system_status_json_href') or item_links.get('readiness_json_href') or item_links.get('release_package_json_href')) and item_links.get('release_gate_json_href') else '',
                _render_evidence_link('Gate JSON', item_links.get('release_gate_json_href')),
            )
        )
        bundle_root = html.escape(str(item.get('bundle_root', 'n/a')))
        artifacts_dir = html.escape(str(item.get('artifacts_dir', 'n/a')))
        share_refs = item.get('share_refs', {}) if isinstance(item.get('share_refs'), dict) else {}
        share_refs_text = '<br>'.join(
            f"<code>{html.escape(str(value))}</code>"
            for value in share_refs.values()
            if str(value).strip()
        ) or 'n/a'
        handoff_summary = html.escape(str(item.get('handoff_summary', 'n/a')))
        triage_tag = html.escape(str(item.get('triage_tag', 'n/a')))
        triage_summary = html.escape(str(item.get('triage_summary', 'n/a')))
        countries_total = int(item.get('countries_total', 0) or 0)
        countries_with_updates = int(item.get('countries_with_updates', 0) or 0)
        countries_without_updates_count = int(item.get('countries_without_updates_count', 0) or 0)
        countries_without_updates = [str(value).strip() for value in (item.get('countries_without_updates') or []) if str(value).strip()]
        coverage_scope_summary = (
            f"Coverage scope: {countries_with_updates}/{countries_total} updated | without updates: {countries_without_updates_count}"
            if countries_total > 0
            else "Coverage scope: n/a"
        )
        coverage_scope_detail = (
            f"Countries without updates: {', '.join(countries_without_updates)}"
            if countries_without_updates
            else "Countries without updates: none"
        )
        breadth_coverage_tag = html.escape(str(item.get('breadth_coverage_tag', 'n/a')))
        breadth_coverage_summary = html.escape(str(item.get('breadth_coverage_summary', 'n/a')))
        return (
            f"<div>{page_links or 'n/a'}</div>"
            f"<div style='margin-top:4px;font-size:0.85em;'>{json_links or 'n/a'}</div>"
            f"<div class='history-bundle-meta' style='margin-top:4px;font-size:0.8em;color:#6b7d99;'>"
            f"bundle_root={bundle_root}<br>artifacts_dir={artifacts_dir}"
            "</div>"
            f"<div class='history-coverage-scope' style='margin-top:4px;font-size:0.8em;color:#9fb3d9;'>{html.escape(coverage_scope_summary)}</div>"
            f"<div class='history-coverage-gaps' style='margin-top:4px;font-size:0.8em;color:#9fb3d9;'>{html.escape(coverage_scope_detail)}</div>"
            f"<div class='history-breadth-coverage' style='margin-top:4px;font-size:0.8em;color:#9fb3d9;'><strong>{breadth_coverage_tag}</strong>: {breadth_coverage_summary}</div>"
            f"<div class='history-triage-summary' style='margin-top:4px;font-size:0.8em;color:#ffd479;'><strong>{triage_tag}</strong>: {triage_summary}</div>"
            f"<div class='history-handoff-summary' style='margin-top:4px;font-size:0.8em;color:#dae2fd;'>{handoff_summary}</div>"
            f"<div class='history-share-refs' style='margin-top:4px;font-size:0.8em;'>{share_refs_text}</div>"
        )

    recent_run_items = [item for item in recent_runs if isinstance(item, dict)]

    def _parse_history_timestamp(value: Any) -> datetime | None:
        text = str(value or '').strip()
        if not text:
            return None
        try:
            return datetime.fromisoformat(text.replace('Z', '+00:00'))
        except ValueError:
            return None

    latest_history_timestamp = max(
        (
            parsed_timestamp
            for item in recent_run_items
            if (parsed_timestamp := _parse_history_timestamp(item.get('recorded_at'))) is not None
        ),
        default=None,
    )
    def _classify_recency_band(parsed_recorded_at: datetime | None) -> str:
        if latest_history_timestamp is None or parsed_recorded_at is None:
            return 'n/a'
        delta_hours = max(0, int((latest_history_timestamp - parsed_recorded_at).total_seconds() // 3600))
        if delta_hours == 0:
            return 'latest'
        if delta_hours <= 24:
            return 'last_24h'
        return 'older'

    triage_tag_counts: dict[str, int] = {}
    recency_band_counts: dict[str, int] = {}
    for item in recent_run_items:
        triage_tag_key = str(item.get('triage_tag', 'n/a')).strip() or 'n/a'
        triage_tag_counts[triage_tag_key] = triage_tag_counts.get(triage_tag_key, 0) + 1
        recency_band_key = _classify_recency_band(_parse_history_timestamp(item.get('recorded_at')))
        recency_band_counts[recency_band_key] = recency_band_counts.get(recency_band_key, 0) + 1
    triage_tag_options = ''.join(
        f"<option value='{html.escape(tag)}'>{html.escape(tag)} ({count})</option>"
        for tag, count in sorted(triage_tag_counts.items())
    )
    recency_band_options = ''.join(
        f"<option value='{html.escape(band)}'>{html.escape(band)} ({count})</option>"
        for band, count in sorted(recency_band_counts.items())
    )
    triage_tag_count_summary = ' | '.join(
        f"{html.escape(tag)}: {count}"
        for tag, count in sorted(triage_tag_counts.items())
    ) or 'n/a'
    recency_band_count_summary = ' | '.join(
        f"{html.escape(band)}: {count}"
        for band, count in sorted(recency_band_counts.items())
    ) or 'n/a'
    def _render_recent_run_row(item: dict[str, Any]) -> str:
        parsed_recorded_at = _parse_history_timestamp(item.get('recorded_at'))
        recency_band = _classify_recency_band(parsed_recorded_at)
        if latest_history_timestamp is not None and parsed_recorded_at is not None:
            hours_behind_latest = f"{max(0, int((latest_history_timestamp - parsed_recorded_at).total_seconds() // 3600))}h"
        else:
            hours_behind_latest = 'n/a'
        history_search_text = ' '.join(
            str(value).strip()
            for value in (
                item.get('run_id', ''),
                item.get('recorded_at', ''),
                item.get('run_status', ''),
                item.get('pilot_set', ''),
                item.get('country_set_id', ''),
                item.get('countries_total', ''),
                item.get('countries_with_updates', ''),
                item.get('countries_without_updates_count', ''),
                ' '.join(str(value).strip() for value in (item.get('countries_without_updates') or []) if str(value).strip()),
                item.get('breadth_coverage_tag', ''),
                item.get('breadth_coverage_summary', ''),
                item.get('governance_verdict', ''),
                item.get('policy_gate_verdict', ''),
                item.get('release_verdict', ''),
                item.get('readiness_interpretation', ''),
                item.get('triage_tag', ''),
                item.get('triage_summary', ''),
                item.get('verification_policy', {}).get('mode', '') if isinstance(item.get('verification_policy'), dict) else '',
                ' '.join(
                    str(value).strip()
                    for value in (
                        (item.get('verification_policy', {}) or {}).get('enabled_overrides', [])
                        if isinstance(item.get('verification_policy'), dict) else []
                    )
                    if isinstance(value, str) and value.strip()
                ),
                item.get('handoff_summary', ''),
            )
            if str(value).strip()
        ).lower()
        return (
            "<tr class='operational-history-row' "
            f"data-triage-tag='{html.escape(str(item.get('triage_tag', 'n/a')))}' "
            f"data-recency-band='{html.escape(recency_band)}' "
            f"data-breadth-coverage-tag='{html.escape(str(item.get('breadth_coverage_tag', 'n/a')))}' "
            f"data-breadth-coverage-summary='{html.escape(str(item.get('breadth_coverage_summary', 'n/a')))}' "
            f"data-recorded-at='{html.escape(str(item.get('recorded_at', 'n/a')))}' "
            f"data-hours-behind-latest='{html.escape(hours_behind_latest.replace('h', '')) if hours_behind_latest.endswith('h') else html.escape(hours_behind_latest)}' "
            f"data-history-search-text='{html.escape(history_search_text)}'>"
            f"<td>{html.escape(str(item.get('run_id', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('recorded_at', 'n/a')))}</td>"
            f"<td>{html.escape(hours_behind_latest)}</td>"
            f"<td>{html.escape(str(item.get('run_status', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('pilot_set', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('country_set_id', 'n/a')))}</td>"
            f"<td>{html.escape(_format_history_ratio(item.get('combined_ce_ratio')))}</td>"
            f"<td>{html.escape(str(item.get('governance_verdict', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('policy_gate_verdict', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('release_verdict', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('readiness_interpretation', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('verification_policy', {}).get('mode', 'n/a') if isinstance(item.get('verification_policy'), dict) else 'n/a'))}</td>"
            f"<td>{html.escape(', '.join(str(value).strip() for value in ((item.get('verification_policy', {}) or {}).get('enabled_overrides', []) if isinstance(item.get('verification_policy'), dict) else []) if str(value).strip()) or 'none')}</td>"
            f"<td>{html.escape(str(item.get('triage_tag', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('known_gap_count', 'n/a')))}</td>"
            f"<td>{html.escape(str(item.get('failed_source_count', 'n/a')))}</td>"
            f"<td>{_render_history_evidence_cell(item)}</td>"
            "</tr>"
        )

    recent_run_rows = ''.join(
        _render_recent_run_row(item)
        for item in recent_run_items
    ) or "<tr><td colspan='17'>No operational history available.</td></tr>"
    operational_history_filter_script = """
<script>
(function() {
  const triageFilter = document.getElementById('operational-history-triage-filter');
  const recencyFilter = document.getElementById('operational-history-recency-filter');
  const sortControl = document.getElementById('operational-history-sort');
  const textFilter = document.getElementById('operational-history-text-filter');
  const resetButton = document.getElementById('operational-history-reset');
  const copyLinkButton = document.getElementById('operational-history-copy-link');
  const presetButtons = Array.from(document.querySelectorAll('[data-operational-history-preset]'));
  const copySummaryButton = document.getElementById('operational-history-copy-summary');
  const exportJsonButton = document.getElementById('operational-history-export-json');
  const exportCsvButton = document.getElementById('operational-history-export-csv');
  const copyCsvButton = document.getElementById('operational-history-copy-csv');
  const visibleSummaryNode = document.getElementById('operational-history-visible-summary');
  const visiblePayloadNode = document.getElementById('operational-history-visible-payload');
  const linkStatusNode = document.getElementById('operational-history-link-status');
  const activeStateSummary = document.getElementById('operational-history-active-state');
  const tableBody = document.querySelector('#operational-evidence-history-table tbody');
  const hashPrefix = 'oh=';
  const rows = Array.from(document.querySelectorAll('.operational-history-row'));
  const visibleCount = document.getElementById('operational-history-visible-count');
  const visibleTriageSummary = document.getElementById('operational-history-visible-triage-counts');
  const visibleRecencySummary = document.getElementById('operational-history-visible-recency-counts');
  const visibleBreadthSummary = document.getElementById('operational-history-visible-breadth-counts');
  const visibleVerificationSummary = document.getElementById('operational-history-visible-verification-counts');
  const visibleOverrideSummary = document.getElementById('operational-history-visible-override-counts');
  const visibleGovernanceDigest = document.getElementById('operational-history-visible-governance-digest');

  function sortOperationalHistoryRows() {
    const sortMode = (sortControl ? sortControl.value : 'latest-first').trim().toLowerCase();
    const sortedRows = rows.slice().sort((left, right) => {
      const leftHours = Number.parseInt(left.getAttribute('data-hours-behind-latest') || '999999', 10);
      const rightHours = Number.parseInt(right.getAttribute('data-hours-behind-latest') || '999999', 10);
      const leftTag = (left.getAttribute('data-triage-tag') || 'n/a').trim().toLowerCase();
      const rightTag = (right.getAttribute('data-triage-tag') || 'n/a').trim().toLowerCase();
      if (sortMode === 'oldest-first') {
        return rightHours - leftHours || leftTag.localeCompare(rightTag);
      }
      if (sortMode === 'triage-tag-asc') {
        return leftTag.localeCompare(rightTag) || leftHours - rightHours;
      }
      return leftHours - rightHours || leftTag.localeCompare(rightTag);
    });
    if (tableBody) {
      sortedRows.forEach((row) => tableBody.appendChild(row));
    }
  }

  function renderOperationalHistoryActiveState(selectedTag, selectedRecency, searchText, sortMode) {
    if (!activeStateSummary) {
      return;
    }
    const normalizedSearch = (searchText || '').trim().toLowerCase();
    const stateParts = [
      `triage=${selectedTag || 'all'}`,
      `recency=${selectedRecency || 'all'}`,
      `search=${normalizedSearch || 'none'}`,
      `sort=${sortMode || 'latest-first'}`,
    ];
    activeStateSummary.textContent = stateParts.join(' | ');
  }

  function resetOperationalHistoryFilters(options) {
    const persistHash = !options || options.persistHash !== false;
    if (triageFilter) triageFilter.value = 'all';
    if (recencyFilter) recencyFilter.value = 'all';
    if (sortControl) sortControl.value = 'latest-first';
    if (textFilter) textFilter.value = '';
    applyOperationalHistoryTriageFilter({persistHash});
  }

  function applyOperationalHistoryPreset(presetId) {
    const preset = (presetId || '').trim().toLowerCase();
    if (preset === 'blocked-review') {
      if (triageFilter) triageFilter.value = 'degraded_release_blocked';
      if (recencyFilter) recencyFilter.value = 'all';
      if (sortControl) sortControl.value = 'latest-first';
      if (textFilter) textFilter.value = '';
    } else if (preset === 'latest-only') {
      if (triageFilter) triageFilter.value = 'all';
      if (recencyFilter) recencyFilter.value = 'latest';
      if (sortControl) sortControl.value = 'latest-first';
      if (textFilter) textFilter.value = '';
    } else if (preset === 'ready-green') {
      if (triageFilter) triageFilter.value = 'ready_green';
      if (recencyFilter) recencyFilter.value = 'all';
      if (sortControl) sortControl.value = 'latest-first';
      if (textFilter) textFilter.value = '';
    } else if (preset === 'oldest-audit') {
      if (triageFilter) triageFilter.value = 'all';
      if (recencyFilter) recencyFilter.value = 'all';
      if (sortControl) sortControl.value = 'oldest-first';
      if (textFilter) textFilter.value = '';
    } else {
      resetOperationalHistoryFilters();
      return;
    }
    if (linkStatusNode) {
      linkStatusNode.textContent = `Preset applied: ${preset}.`;
    }
    applyOperationalHistoryTriageFilter();
  }

  function serializeOperationalHistoryState(state) {
    const params = new URLSearchParams();
    if (state.triage && state.triage !== 'all') { params.set('oh_triage', state.triage); }
    if (state.recency && state.recency !== 'all') { params.set('oh_recency', state.recency); }
    if (state.sort && state.sort !== 'latest-first') { params.set('oh_sort', state.sort); }
    if (state.text) { params.set('oh_text', state.text); }
    return params.toString();
  }

  function persistOperationalHistoryStateToHash(state) {
    const encoded = serializeOperationalHistoryState(state);
    const base = `${window.location.pathname}${window.location.search}`;
    if (!encoded) {
      window.history.replaceState(null, '', base);
      return;
    }
    window.history.replaceState(null, '', `${base}#${hashPrefix}${encoded}`);
  }

  function applyOperationalHistoryStateFromHash() {
    const rawHash = window.location.hash || '';
    if (!rawHash.startsWith(`#${hashPrefix}`)) {
      return false;
    }
    try {
      const params = new URLSearchParams(rawHash.slice(hashPrefix.length + 1));
      const triage = params.get('oh_triage');
      const recency = params.get('oh_recency');
      const sort = params.get('oh_sort');
      const text = params.get('oh_text');
      if (triage && triageFilter) { triageFilter.value = triage; }
      if (recency && recencyFilter) { recencyFilter.value = recency; }
      if (sort && sortControl) { sortControl.value = sort; }
      if (text && textFilter) { textFilter.value = text; }
      return true;
    } catch (_err) {
      return false;
    }
  }

  async function copyOperationalHistoryFilterLink() {
    const state = getOperationalHistoryState();
    const encoded = serializeOperationalHistoryState(state);
    const baseUrl = `${window.location.origin}${window.location.pathname}${window.location.search}`;
    const shareUrl = encoded ? `${baseUrl}#${hashPrefix}${encoded}` : baseUrl;
    if (!linkStatusNode) {
      return;
    }
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error('clipboard_unavailable');
      }
      await navigator.clipboard.writeText(shareUrl);
      linkStatusNode.textContent = 'History link copied.';
    } catch (_err) {
      linkStatusNode.textContent = 'History link copy unavailable in this browser.';
    }
  }

  function buildOperationalHistoryVisibleSummary(visibleRows, triageCounts, recencyCounts) {
    const runIds = visibleRows.map((row) => (row.children[0] ? row.children[0].textContent.trim() : 'n/a')).filter(Boolean);
    const triageSummary = Object.entries(triageCounts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([tag, count]) => `${tag}:${count}`)
      .join(', ') || 'none';
    const recencySummary = Object.entries(recencyCounts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([band, count]) => `${band}:${count}`)
      .join(', ') || 'none';
    const breadthSummary = Object.entries(
      visibleRows.reduce((counts, row) => {
        const breadthTag = (row.getAttribute('data-breadth-coverage-tag') || 'n/a').trim() || 'n/a';
        counts[breadthTag] = (counts[breadthTag] || 0) + 1;
        return counts;
      }, {})
    )
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([tag, count]) => `${tag}:${count}`)
      .join(', ') || 'none';
    const verificationModeSummary = Object.entries(
      visibleRows.reduce((counts, row) => {
        const mode = (row.children[11] ? row.children[11].textContent.trim() : 'n/a') || 'n/a';
        counts[mode] = (counts[mode] || 0) + 1;
        return counts;
      }, {})
    )
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([mode, count]) => `${mode}:${count}`)
      .join(', ') || 'none';
    const overrideSummary = Object.entries(
      visibleRows.reduce((counts, row) => {
        const overrides = (row.children[12] ? row.children[12].textContent.trim() : 'none') || 'none';
        counts[overrides] = (counts[overrides] || 0) + 1;
        return counts;
      }, {})
    )
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([overrides, count]) => `${overrides}:${count}`)
      .join(', ') || 'none';
    return `visible_runs=${visibleRows.length} | run_ids=${runIds.join(', ') || 'none'} | triage=${triageSummary} | recency=${recencySummary} | breadth=${breadthSummary} | verification=${verificationModeSummary} | overrides=${overrideSummary}`;
  }

  function buildOperationalHistoryVisibleGovernanceDigest(visibleRows, triageCounts, recencyCounts, breadthCounts, verificationCounts, overrideCounts) {
    const formatCounts = (counts) => Object.entries(counts)
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(([label, count]) => `${label}: ${count}`)
      .join(' | ') || 'none';
    return `${visibleRows.length} visible runs | triage: ${formatCounts(triageCounts)} | recency: ${formatCounts(recencyCounts)} | breadth: ${formatCounts(breadthCounts)} | verification: ${formatCounts(verificationCounts)} | overrides: ${formatCounts(overrideCounts)}`;
  }

  function buildOperationalHistoryVisiblePayload(visibleRows, triageCounts, recencyCounts) {
    const breadthCoverageCounts = Object.fromEntries(
      Object.entries(
        visibleRows.reduce((counts, row) => {
          const breadthTag = (row.getAttribute('data-breadth-coverage-tag') || 'n/a').trim() || 'n/a';
          counts[breadthTag] = (counts[breadthTag] || 0) + 1;
          return counts;
        }, {})
      ).sort((a, b) => a[0].localeCompare(b[0]))
    );
    const verificationModeCounts = Object.fromEntries(
      Object.entries(
        visibleRows.reduce((counts, row) => {
          const mode = (row.children[11] ? row.children[11].textContent.trim() : 'n/a') || 'n/a';
          counts[mode] = (counts[mode] || 0) + 1;
          return counts;
        }, {})
      ).sort((a, b) => a[0].localeCompare(b[0]))
    );
    const overrideProfileCounts = Object.fromEntries(
      Object.entries(
        visibleRows.reduce((counts, row) => {
          const overrides = (row.children[12] ? row.children[12].textContent.trim() : 'none') || 'none';
          counts[overrides] = (counts[overrides] || 0) + 1;
          return counts;
        }, {})
      ).sort((a, b) => a[0].localeCompare(b[0]))
    );
    const governanceDigest = buildOperationalHistoryVisibleGovernanceDigest(
      visibleRows,
      triageCounts,
      recencyCounts,
      breadthCoverageCounts,
      verificationModeCounts,
      overrideProfileCounts,
    );
    return {
      visible_runs: visibleRows.length,
      run_ids: visibleRows.map((row) => (row.children[0] ? row.children[0].textContent.trim() : 'n/a')).filter(Boolean),
      triage_counts: Object.fromEntries(Object.entries(triageCounts).sort((a, b) => a[0].localeCompare(b[0]))),
      recency_counts: Object.fromEntries(Object.entries(recencyCounts).sort((a, b) => a[0].localeCompare(b[0]))),
      breadth_coverage_counts: breadthCoverageCounts,
      verification_mode_counts: verificationModeCounts,
      override_profile_counts: overrideProfileCounts,
      governance_digest: governanceDigest,
      rows: visibleRows.map((row) => ({
        run_id: row.children[0] ? row.children[0].textContent.trim() : 'n/a',
        recorded_at: row.children[1] ? row.children[1].textContent.trim() : 'n/a',
        hours_behind_latest: row.children[2] ? row.children[2].textContent.trim() : 'n/a',
        run_status: row.children[3] ? row.children[3].textContent.trim() : 'n/a',
        pilot_set: row.children[4] ? row.children[4].textContent.trim() : 'n/a',
        country_set_id: row.children[5] ? row.children[5].textContent.trim() : 'n/a',
        combined_ce_ratio: row.children[6] ? row.children[6].textContent.trim() : 'n/a',
        governance_verdict: row.children[7] ? row.children[7].textContent.trim() : 'n/a',
        policy_gate_verdict: row.children[8] ? row.children[8].textContent.trim() : 'n/a',
        release_verdict: row.children[9] ? row.children[9].textContent.trim() : 'n/a',
        readiness_interpretation: row.children[10] ? row.children[10].textContent.trim() : 'n/a',
        verification_mode: row.children[11] ? row.children[11].textContent.trim() : 'n/a',
        enabled_overrides: row.children[12] ? row.children[12].textContent.trim() : 'n/a',
        triage_tag: row.children[13] ? row.children[13].textContent.trim() : 'n/a',
        known_gap_count: row.children[14] ? row.children[14].textContent.trim() : 'n/a',
        failed_source_count: row.children[15] ? row.children[15].textContent.trim() : 'n/a',
        breadth_coverage_tag: row.getAttribute('data-breadth-coverage-tag') || 'n/a',
        breadth_coverage_summary: row.getAttribute('data-breadth-coverage-summary') || 'n/a',
      })),
    };
  }

  async function copyOperationalHistoryVisibleSummary() {
    if (!visibleSummaryNode || !linkStatusNode) {
      return;
    }
    const summaryText = (visibleSummaryNode.textContent || '').trim();
    try {
      if (!navigator.clipboard || !navigator.clipboard.writeText) {
        throw new Error('clipboard_unavailable');
      }
      await navigator.clipboard.writeText(summaryText);
      linkStatusNode.textContent = 'Visible summary copied.';
    } catch (_err) {
      linkStatusNode.textContent = 'Visible summary copy unavailable in this browser.';
    }
  }

  function exportOperationalHistoryVisiblePayload() {
    if (!visiblePayloadNode || !linkStatusNode) {
      return;
    }
    const exportText = visiblePayloadNode.textContent || '{}';
    try {
      const blob = new Blob([exportText], { type: 'application/json' });
      const exportLink = document.createElement('a');
      exportLink.href = URL.createObjectURL(blob);
      exportLink.download = 'operational_history_visible_slice.json';
      exportLink.click();
      URL.revokeObjectURL(exportLink.href);
      linkStatusNode.textContent = 'Visible payload exported.';
    } catch (_err) {
      linkStatusNode.textContent = 'Visible payload export unavailable in this browser.';
    }
  }

  function buildOperationalHistoryVisibleCsv(visibleRows) {
    const header = [
      'run_id',
      'recorded_at',
      'hours_behind_latest',
      'run_status',
      'pilot_set',
      'country_set_id',
      'combined_ce_ratio',
      'governance_verdict',
      'policy_gate_verdict',
      'release_verdict',
      'readiness_interpretation',
      'verification_mode',
      'enabled_overrides',
      'triage_tag',
      'known_gap_count',
      'failed_source_count',
      'breadth_coverage_tag',
      'breadth_coverage_summary',
    ];
    const rowsCsv = visibleRows.map((row) => {
      const values = [
        row.children[0] ? row.children[0].textContent.trim() : 'n/a',
        row.children[1] ? row.children[1].textContent.trim() : 'n/a',
        row.children[2] ? row.children[2].textContent.trim() : 'n/a',
        row.children[3] ? row.children[3].textContent.trim() : 'n/a',
        row.children[4] ? row.children[4].textContent.trim() : 'n/a',
        row.children[5] ? row.children[5].textContent.trim() : 'n/a',
        row.children[6] ? row.children[6].textContent.trim() : 'n/a',
        row.children[7] ? row.children[7].textContent.trim() : 'n/a',
        row.children[8] ? row.children[8].textContent.trim() : 'n/a',
        row.children[9] ? row.children[9].textContent.trim() : 'n/a',
        row.children[10] ? row.children[10].textContent.trim() : 'n/a',
        row.children[11] ? row.children[11].textContent.trim() : 'n/a',
        row.children[12] ? row.children[12].textContent.trim() : 'n/a',
        row.children[13] ? row.children[13].textContent.trim() : 'n/a',
        row.children[14] ? row.children[14].textContent.trim() : 'n/a',
        row.children[15] ? row.children[15].textContent.trim() : 'n/a',
        row.getAttribute('data-breadth-coverage-tag') || 'n/a',
        row.getAttribute('data-breadth-coverage-summary') || 'n/a',
      ];
      return values.map((value) => {
        const escaped = String(value).replace(/"/g, '""');
        return `"${escaped}"`;
      }).join(',');
    });
    return [header.join(','), ...rowsCsv].join('\n');
  }

  function exportOperationalHistoryVisibleCsv() {
    if (!linkStatusNode) {
      return;
    }
    const visibleRows = Array.from(document.querySelectorAll('.operational-history-row')).filter((row) => row.style.display !== 'none');
    const exportText = buildOperationalHistoryVisibleCsv(visibleRows);
    try {
      const blob = new Blob([exportText], { type: 'text/csv;charset=utf-8' });
      const exportLink = document.createElement('a');
      exportLink.href = URL.createObjectURL(blob);
      exportLink.download = 'operational_history_visible_slice.csv';
      exportLink.click();
      URL.revokeObjectURL(exportLink.href);
      linkStatusNode.textContent = 'Visible CSV exported.';
    } catch (_err) {
      linkStatusNode.textContent = 'Visible CSV export unavailable in this browser.';
    }
  }

  async function copyOperationalHistoryVisibleCsv() {
    if (!linkStatusNode) {
      return;
    }
    const visibleRows = Array.from(document.querySelectorAll('.operational-history-row')).filter((row) => row.style.display !== 'none');
    const exportText = buildOperationalHistoryVisibleCsv(visibleRows);
    try {
      await navigator.clipboard.writeText(exportText);
      linkStatusNode.textContent = 'Visible CSV copied.';
    } catch (_err) {
      linkStatusNode.textContent = 'Visible CSV copy unavailable in this browser.';
    }
  }

  function getOperationalHistoryState() {
    return {
      triage: (triageFilter ? triageFilter.value : 'all').trim().toLowerCase(),
      recency: (recencyFilter ? recencyFilter.value : 'all').trim().toLowerCase(),
      sort: (sortControl ? sortControl.value : 'latest-first').trim().toLowerCase(),
      text: (textFilter ? textFilter.value : '').trim(),
    };
  }

  function applyOperationalHistoryTriageFilter(options) {
    const persistHash = !options || options.persistHash !== false;
    const state = getOperationalHistoryState();
    const selectedTag = state.triage;
    const selectedRecency = state.recency;
    const searchText = state.text.toLowerCase();
    const sortMode = state.sort;
    const triageCounts = {};
    const recencyCounts = {};
    const breadthCounts = {};
    const verificationCounts = {};
    const overrideCounts = {};
    const visibleRows = [];
    let visible = 0;

    rows.forEach((row) => {
      const rowTag = (row.getAttribute('data-triage-tag') || 'n/a').trim().toLowerCase();
      const rowRecency = (row.getAttribute('data-recency-band') || 'n/a').trim().toLowerCase();
      const rowSearchText = (row.getAttribute('data-history-search-text') || '').trim().toLowerCase();
      const matchesText = !searchText || rowSearchText.includes(searchText);
      const show = (selectedTag === 'all' || rowTag === selectedTag)
        && (selectedRecency === 'all' || rowRecency === selectedRecency)
        && matchesText;
      row.style.display = show ? '' : 'none';
      if (show) {
        visible += 1;
        visibleRows.push(row);
        triageCounts[rowTag] = (triageCounts[rowTag] || 0) + 1;
        recencyCounts[rowRecency] = (recencyCounts[rowRecency] || 0) + 1;
        const breadthTag = (row.getAttribute('data-breadth-coverage-tag') || 'n/a').trim() || 'n/a';
        breadthCounts[breadthTag] = (breadthCounts[breadthTag] || 0) + 1;
        const verificationMode = (row.children[11] ? row.children[11].textContent.trim() : 'n/a') || 'n/a';
        verificationCounts[verificationMode] = (verificationCounts[verificationMode] || 0) + 1;
        const overrideProfile = (row.children[12] ? row.children[12].textContent.trim() : 'none') || 'none';
        overrideCounts[overrideProfile] = (overrideCounts[overrideProfile] || 0) + 1;
      }
    });

    sortOperationalHistoryRows();
    renderOperationalHistoryActiveState(selectedTag, selectedRecency, searchText, sortMode);
    if (persistHash) {
      persistOperationalHistoryStateToHash(state);
    }

    if (visibleCount) {
      visibleCount.textContent = String(visible);
    }
    if (visibleTriageSummary) {
      const summary = Object.entries(triageCounts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([tag, count]) => `${tag}: ${count}`)
        .join(' | ');
      visibleTriageSummary.textContent = summary || 'none';
    }
    if (visibleRecencySummary) {
      const summary = Object.entries(recencyCounts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([band, count]) => `${band}: ${count}`)
        .join(' | ');
      visibleRecencySummary.textContent = summary || 'none';
    }
    if (visibleBreadthSummary) {
      const summary = Object.entries(breadthCounts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([tag, count]) => `${tag}: ${count}`)
        .join(' | ');
      visibleBreadthSummary.textContent = summary || 'none';
    }
    if (visibleVerificationSummary) {
      const summary = Object.entries(verificationCounts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([mode, count]) => `${mode}: ${count}`)
        .join(' | ');
      visibleVerificationSummary.textContent = summary || 'none';
    }
    if (visibleOverrideSummary) {
      const summary = Object.entries(overrideCounts)
        .sort((a, b) => a[0].localeCompare(b[0]))
        .map(([profile, count]) => `${profile}: ${count}`)
        .join(' | ');
      visibleOverrideSummary.textContent = summary || 'none';
    }
    if (visibleGovernanceDigest) {
      visibleGovernanceDigest.textContent = buildOperationalHistoryVisibleGovernanceDigest(
        visibleRows,
        triageCounts,
        recencyCounts,
        breadthCounts,
        verificationCounts,
        overrideCounts,
      );
    }
    if (visibleSummaryNode) {
      visibleSummaryNode.textContent = buildOperationalHistoryVisibleSummary(visibleRows, triageCounts, recencyCounts);
    }
    if (visiblePayloadNode) {
      visiblePayloadNode.textContent = JSON.stringify(buildOperationalHistoryVisiblePayload(visibleRows, triageCounts, recencyCounts), null, 2);
    }
  }

  if (triageFilter) triageFilter.addEventListener('change', applyOperationalHistoryTriageFilter);
  if (recencyFilter) recencyFilter.addEventListener('change', applyOperationalHistoryTriageFilter);
  if (sortControl) sortControl.addEventListener('change', applyOperationalHistoryTriageFilter);
  if (textFilter) textFilter.addEventListener('input', applyOperationalHistoryTriageFilter);
  if (resetButton) resetButton.addEventListener('click', () => resetOperationalHistoryFilters());
  if (copyLinkButton) copyLinkButton.addEventListener('click', copyOperationalHistoryFilterLink);
  if (copySummaryButton) copySummaryButton.addEventListener('click', copyOperationalHistoryVisibleSummary);
  if (exportJsonButton) exportJsonButton.addEventListener('click', exportOperationalHistoryVisiblePayload);
  if (exportCsvButton) exportCsvButton.addEventListener('click', exportOperationalHistoryVisibleCsv);
  if (copyCsvButton) copyCsvButton.addEventListener('click', copyOperationalHistoryVisibleCsv);
  presetButtons.forEach((button) => button.addEventListener('click', () => applyOperationalHistoryPreset(button.getAttribute('data-operational-history-preset') || '')));
  const loadedFromHash = applyOperationalHistoryStateFromHash();
  if (loadedFromHash && linkStatusNode) {
    linkStatusNode.textContent = 'History view loaded from link.';
  }
  applyOperationalHistoryTriageFilter({persistHash:false});
})();
</script>
"""
    latest_failed_sources = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in latest_summary.get('failed_sources', [])
    ) or "<li>none</li>"
    latest_known_gaps = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in latest_summary.get('known_gaps', [])
    ) or "<li>none</li>"
    latest_countries_without_updates = ''.join(
        f"<li>{html.escape(str(item))}</li>"
        for item in latest_summary.get('countries_without_updates', [])
    ) or "<li>none</li>"
    evidence_lane_section = (
        "<div class='panel' id='operational-evidence-lane'><div class='panel-header'>Operational Evidence Lane</div>"
        f"<p>Governed slice: <strong>{html.escape(str(latest_summary.get('country_set_id', 'n/a')))}</strong> | Coverage scope: <strong>{html.escape(str(latest_summary.get('countries_with_updates', 0)))}/{html.escape(str(latest_summary.get('countries_total', 0)))}</strong> updated | Countries without updates: <strong>{html.escape(str(latest_summary.get('countries_without_updates_count', 0)))}</strong> | Combined C/E ratio: <strong>{combined_ce_ratio_text}</strong> | Governance verdict: <strong>{html.escape(governance_verdict)}</strong> | Policy gate: <strong>{html.escape(policy_gate_verdict)}</strong></p>"
        f"<p>Breadth coverage: <strong>{latest_breadth_coverage_tag}</strong> | Summary: <strong>{latest_breadth_coverage_summary}</strong></p>"
        f"<p>Release verdict: <strong>{html.escape(release_verdict)}</strong> | Readiness interpretation: <strong>{html.escape(readiness_interpretation)}</strong> | Known gaps: <strong>{html.escape(str(known_gap_count))}</strong></p>"
        f"<p>Triage tag: <strong>{latest_triage_tag}</strong> | Triage summary: <strong>{latest_triage_summary}</strong></p>"
        f"<p>Verification mode: <strong>{html.escape(verification_mode)}</strong> | Enabled overrides: <strong>{html.escape(verification_override_text)}</strong></p>"
        f"<p>Operator next action: <strong>{operator_next_action}</strong></p>"
        f"<p>Bundle root: <strong>{latest_bundle_root}</strong> | GUI index: <strong>{latest_gui_index}</strong> | Artifacts dir: <strong>{latest_artifacts_dir}</strong></p>"
        f"<p>Handoff summary: <strong>{latest_handoff_summary}</strong></p>"
        f"<details><summary>Latest bundle evidence links</summary><ul>{latest_evidence_link_items}</ul></details>"
        f"<details><summary>Latest bundle share refs</summary><ul>{latest_share_ref_items}</ul></details>"
        f"<details><summary>Latest failed sources ({html.escape(str(latest_summary.get('failed_source_count', 0)))})</summary><ul>{latest_failed_sources}</ul></details>"
        f"<details><summary>Countries without updates ({html.escape(str(latest_summary.get('countries_without_updates_count', 0)))})</summary><ul>{latest_countries_without_updates}</ul></details>"
        f"<details><summary>Latest known gaps ({html.escape(str(known_gap_count))})</summary><ul>{latest_known_gaps}</ul></details>"
        "<h3>Recent Operational History</h3>"
        "<p>Quick triage controls help narrow archived runs by review posture before opening detailed evidence.</p>"
        "<div class='controls-bar'>"
        "<label for='operational-history-triage-filter'>Triage tag filter:</label> "
        f"<select id='operational-history-triage-filter'><option value='all'>All triage tags ({html.escape(str(len(recent_run_items)))})</option>{triage_tag_options}</select> "
        "<label for='operational-history-recency-filter'>Recency band filter:</label> "
        f"<select id='operational-history-recency-filter'><option value='all'>All recency bands ({html.escape(str(len(recent_run_items)))})</option>{recency_band_options}</select> "
        "<label for='operational-history-sort'>Sort:</label> "
        "<select id='operational-history-sort'><option value='latest-first'>Latest first</option><option value='oldest-first'>Oldest first</option><option value='triage-tag-asc'>Triage tag (A-Z)</option></select> "
        "<label for='operational-history-text-filter'>Search:</label> "
        "<input id='operational-history-text-filter' type='search' placeholder='run id, pilot set, triage, handoff'> "
        "<button type='button' id='operational-history-reset'>Reset</button> "
        "<button type='button' id='operational-history-copy-link'>Copy link</button> "
        "<button type='button' id='operational-history-copy-summary'>Copy visible summary</button> "
        "<button type='button' id='operational-history-export-json'>Export visible JSON</button> "
        "<button type='button' id='operational-history-export-csv'>Export visible CSV</button> "
        "<button type='button' id='operational-history-copy-csv'>Copy visible CSV</button> "
        "<button type='button' id='operational-history-preset-blocked-review' data-operational-history-preset='blocked-review'>Blocked review</button> "
        "<button type='button' id='operational-history-preset-latest-only' data-operational-history-preset='latest-only'>Latest only</button> "
        "<button type='button' id='operational-history-preset-ready-green' data-operational-history-preset='ready-green'>Ready green</button> "
        "<button type='button' id='operational-history-preset-oldest-audit' data-operational-history-preset='oldest-audit'>Oldest audit</button> "
        "<span id='operational-history-link-status' style='font-size:0.85em;color:#9fb3d9;'></span> "
        f"<span>Visible runs: <strong id='operational-history-visible-count'>{html.escape(str(len(recent_run_items)))}</strong></span>"
        "</div>"
        f"<p>Triage tag counts: <strong id='operational-history-triage-counts'>{triage_tag_count_summary}</strong></p>"
        f"<p>Recency band counts: <strong id='operational-history-recency-counts'>{recency_band_count_summary}</strong></p>"
        "<p>Active history filter state: <strong id='operational-history-active-state'>triage=all | recency=all | search=none | sort=latest-first</strong></p>"
        "<p>Visible slice summary: <strong id='operational-history-visible-summary'>visible_runs=0 | run_ids=none | triage=none | recency=none | breadth=none | verification=none | overrides=none</strong></p>"
        "<details><summary>Visible slice payload</summary><pre id='operational-history-visible-payload'>{}</pre></details>"
        "<p>Visible triage counts: <strong id='operational-history-visible-triage-counts'>n/a</strong></p>"
        "<p>Visible recency counts: <strong id='operational-history-visible-recency-counts'>n/a</strong></p>"
        "<p>Visible breadth counts: <strong id='operational-history-visible-breadth-counts'>n/a</strong></p>"
        "<p>Visible verification counts: <strong id='operational-history-visible-verification-counts'>n/a</strong></p>"
        "<p>Visible override counts: <strong id='operational-history-visible-override-counts'>n/a</strong></p>"
        "<p>Visible governance digest: <strong id='operational-history-visible-governance-digest'>0 visible runs | triage: none | recency: none | breadth: none | verification: none | overrides: none</strong></p>"
        "<table id='operational-evidence-history-table'><thead><tr><th>Run ID</th><th>Recorded At</th><th>Hours Behind Latest</th><th>Status</th><th>Pilot Set</th><th>Country Set</th><th>Combined C/E Ratio</th><th>Governance</th><th>Policy Gate</th><th>Release Verdict</th><th>Readiness Interpretation</th><th>Verification Mode</th><th>Enabled Overrides</th><th>Triage Tag</th><th>Known Gaps</th><th>Failed Sources</th><th>Evidence</th></tr></thead>"
        f"<tbody>{recent_run_rows}</tbody></table>{operational_history_filter_script}</div>"
    ) if latest_summary else ""
    _run_color = html.escape(_run_status_color(str(system_status_read_model.get('run_status', 'n/a'))))
    body = (
        # === KPI Header ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Run ID</span><div class='kpi-value' style='font-size:0.85rem;'>{html.escape(str(system_status_read_model.get('run_id', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Run Status</span><div class='kpi-value' style='color:{_run_color}'>{html.escape(str(system_status_read_model.get('run_status', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Last Run</span><div class='kpi-value' style='font-size:0.8rem;'>{html.escape(str(system_status_read_model.get('last_run', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Snapshot</span><div class='kpi-value' style='font-size:0.8rem;color:#6b7d99;'>{html.escape(str(system_status_read_model.get('snapshot_id', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Reprocessing</span><div class='kpi-value' style='font-size:0.8rem;'>{html.escape(str(system_status_read_model.get('reprocessing_status', 'n/a')))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Country Set</span><div class='kpi-value' style='font-size:0.7rem;'>{html.escape(str(latest_summary.get('country_set_id', system_status_read_model.get('country_set_id', 'n/a'))))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Combined C/E Ratio</span><div class='kpi-value'>{combined_ce_ratio_text}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Governance Verdict</span><div class='kpi-value'>{html.escape(governance_verdict)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Policy Gate</span><div class='kpi-value'>{html.escape(policy_gate_verdict)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Release Verdict</span><div class='kpi-value'>{html.escape(release_verdict)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Known Gaps</span><div class='kpi-value'>{html.escape(str(known_gap_count))}</div><div class='kpi-sub'>{html.escape(readiness_interpretation)}</div></div>"
        "</div>"
        f"{evidence_lane_section}"
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


def _render_readiness(
    readiness_view_model: dict[str, Any],
    release_gate_view_model: dict[str, Any] | None = None,
    stakeholder_functional_closure_view_model: dict[str, Any] | None = None,
    stakeholder_e2e_flow_coverage_view_model: dict[str, Any] | None = None,
    release_readiness_index_view_model: dict[str, Any] | None = None,
    stakeholder_e2e_ui_smoke_view_model: dict[str, Any] | None = None,
    operator_release_summary_view_model: dict[str, Any] | None = None,
    operator_blocker_causality_view_model: dict[str, Any] | None = None,
    operator_operability_cluster_view_model: dict[str, Any] | None = None,
    operator_failure_drill_digest_view_model: dict[str, Any] | None = None,
    operator_failure_drill_trend_baseline_view_model: dict[str, Any] | None = None,
    operator_recurrence_aware_remediation_prioritization_view_model: dict[str, Any] | None = None,
    operator_failure_drill_delta_ledger_view_model: dict[str, Any] | None = None,
    operator_remediation_execution_loop_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_closure_drill_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_action_plan_view_model: dict[str, Any] | None = None,
    analyst_briefing_view_model: dict[str, Any] | None = None,
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
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
    _gate_v = str((release_gate_view_model or {}).get('gate_verdict', 'n/a'))
    _gate_ok = _gate_v.lower() in ('go', 'ready', 'pass', 'ok', 'green')
    _gate_color = '#4edea3' if _gate_ok else '#ffb4ab'
    _gate_blockers = [str(item) for item in (release_gate_view_model or {}).get('blockers', [])]
    _gate_blocker_items = ''.join(f"<li>{html.escape(item)}</li>" for item in _gate_blockers) or "<li>none</li>"
    _stakeholder_focus = (stakeholder_functional_closure_view_model or {}).get('focus_gap_cluster', {})
    _stakeholder_covered = int(_stakeholder_focus.get('covered_count', 0)) if _stakeholder_focus else 0
    _stakeholder_open = int(_stakeholder_focus.get('not_implemented_count', 0)) if _stakeholder_focus else 0
    _stakeholder_closed = max(0, _stakeholder_covered - _stakeholder_open)
    _stakeholder_status = 'closed' if (_stakeholder_covered == 19 and _stakeholder_open == 0) else 'at_risk'
    _stakeholder_color = '#4edea3' if _stakeholder_status == 'closed' else '#ffb4ab'
    _stakeholder_open_ids = [str(item) for item in _stakeholder_focus.get('not_implemented_ids', [])] if _stakeholder_focus else []
    _stakeholder_open_items = ''.join(f"<li>{html.escape(item)}</li>" for item in _stakeholder_open_ids) or "<li>none</li>"
    _readiness_index = release_readiness_index_view_model or {}
    _readiness_passed = int(_readiness_index.get('passed_gates', 0)) if _readiness_index else 0
    _readiness_total = int(_readiness_index.get('total_gates', 0)) if _readiness_index else 0
    _readiness_percent = _readiness_index.get('percent', 'n/a') if _readiness_index else 'n/a'
    _readiness_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{'pass' if bool(item.get('passed')) else 'fail'}</td>"
        f"<td>{html.escape(str(item.get('detail', 'n/a')))}</td>"
        "</tr>"
        for item in _readiness_index.get('gates', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='3'>No readiness gates available.</td></tr>"
    _e2e_summary = (stakeholder_e2e_flow_coverage_view_model or {}).get('summary', {})
    _e2e_stop_criteria = (stakeholder_e2e_flow_coverage_view_model or {}).get('stop_criteria', {})
    _e2e_flow_count = int(_e2e_summary.get('flow_count', 0)) if _e2e_summary else 0
    _e2e_covered_flow_count = int(_e2e_summary.get('covered_flow_count', 0)) if _e2e_summary else 0
    _e2e_flow_gap_count = int(_e2e_summary.get('flow_gap_count', 0)) if _e2e_summary else 0
    _e2e_missing_evidence_refs = int(_e2e_summary.get('missing_evidence_ref_count', 0)) if _e2e_summary else 0
    _e2e_missing_requirement_refs = int(_e2e_summary.get('missing_requirement_ref_count', 0)) if _e2e_summary else 0
    _e2e_stop_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(key))}</td>"
        f"<td>{'pass' if bool(value) else 'fail'}</td>"
        "</tr>"
        for key, value in sorted(_e2e_stop_criteria.items())
    ) or "<tr><td colspan='2'>No AP-04 stop-criteria data available.</td></tr>"
    _e2e_ui_smoke = stakeholder_e2e_ui_smoke_view_model or {}
    _e2e_ui_smoke_flow_count = int(_e2e_ui_smoke.get('flow_count', 0)) if _e2e_ui_smoke else 0
    _e2e_ui_smoke_covered = int(_e2e_ui_smoke.get('covered_flow_count', 0)) if _e2e_ui_smoke else 0
    _e2e_ui_smoke_gaps = int(_e2e_ui_smoke.get('flow_gap_count', 0)) if _e2e_ui_smoke else 0
    _e2e_ui_smoke_stop = _e2e_ui_smoke.get('stop_criteria') if isinstance(_e2e_ui_smoke.get('stop_criteria'), dict) else {}
    _e2e_ui_smoke_stop_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(key))}</td>"
        f"<td>{'pass' if bool(value) else 'fail'}</td>"
        "</tr>"
        for key, value in sorted(_e2e_ui_smoke_stop.items())
    ) or "<tr><td colspan='2'>No AP-07 UI-smoke stop-criteria data available.</td></tr>"

    _operator_summary = operator_release_summary_view_model or {}
    _operator_failed_gate_count = int(_operator_summary.get('failed_gate_count', 0)) if _operator_summary else 0
    _operator_next_action = str(_operator_summary.get('operator_next_action', 'n/a')) if _operator_summary else 'n/a'
    _operator_failed_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('detail', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('remediation_hint', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_summary.get('failed_gates', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='3'>No AP-16 failed-gate entries available.</td></tr>"

    _operator_blocker_causality = operator_blocker_causality_view_model or {}
    _operator_primary_root_cause = str(_operator_blocker_causality.get('primary_root_cause_gate_id', 'none')) if _operator_blocker_causality.get('primary_root_cause_gate_id') is not None else 'none'
    _operator_root_causes = ', '.join(str(item) for item in _operator_blocker_causality.get('root_cause_gate_ids', [])) or 'none'
    _operator_derived_effects = ', '.join(str(item) for item in _operator_blocker_causality.get('derived_gate_ids', [])) or 'none'
    _operator_blocker_next_action = str(_operator_blocker_causality.get('operator_next_action', 'n/a')) if _operator_blocker_causality else 'n/a'
    _operator_blocker_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('gate_role', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('causal_detail', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_blocker_causality.get('causal_chain_rows', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='3'>No AP-26 blocker-chain rows available.</td></tr>"

    _operator_operability_cluster = operator_operability_cluster_view_model or {}
    _operator_operability_status = str(_operator_operability_cluster.get('cluster_status', 'n/a')) if _operator_operability_cluster else 'n/a'
    _operator_operability_covered = int(_operator_operability_cluster.get('covered_gate_count', 0)) if _operator_operability_cluster else 0
    _operator_operability_failed = int(_operator_operability_cluster.get('failed_gate_count', 0)) if _operator_operability_cluster else 0
    _operator_operability_next_action = str(_operator_operability_cluster.get('operator_next_action', 'n/a')) if _operator_operability_cluster else 'n/a'
    _operator_operability_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('gate_group', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('cluster_role', 'n/a')))}</td>"
        f"<td>{'pass' if bool(item.get('passed')) else 'fail'}</td>"
        "</tr>"
        for item in _operator_operability_cluster.get('cluster_rows', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='4'>No AP-27 operability-cluster rows available.</td></tr>"

    _operator_digest = operator_failure_drill_digest_view_model or {}
    _operator_digest_cluster_count = int(_operator_digest.get('cluster_count', 0)) if _operator_digest else 0
    _operator_digest_top_gate = str(_operator_digest.get('top_cluster_gate_id', 'n/a')) if _operator_digest else 'n/a'
    _operator_digest_next_action = str(_operator_digest.get('operator_next_action', 'n/a')) if _operator_digest else 'n/a'
    _operator_digest_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('scenario_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(s) for s in item.get('scenario_ids', [])))}</td>"
        f"<td>{html.escape(str(item.get('remediation_hint', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_digest.get('clusters', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='4'>No AP-17 drill digest clusters available.</td></tr>"

    _operator_trend_baseline = operator_failure_drill_trend_baseline_view_model or {}
    _operator_trend_snapshot_count = int(_operator_trend_baseline.get('snapshot_count', 0)) if _operator_trend_baseline else 0
    _operator_trend_top_gate = str(_operator_trend_baseline.get('top_recurring_gate_id', 'n/a')) if _operator_trend_baseline else 'n/a'
    _operator_trend_focus = str(_operator_trend_baseline.get('operator_focus', 'n/a')) if _operator_trend_baseline else 'n/a'
    _operator_trend_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('scenario_count', 0)))}</td>"
        f"<td>{html.escape(str(item.get('trend_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('trajectory', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('recurrence_ratio', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_trend_baseline.get('trend_rows', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='5'>No AP-19 trend baseline rows available.</td></tr>"

    _operator_prioritization = operator_recurrence_aware_remediation_prioritization_view_model or {}
    _operator_priority_count = int(_operator_prioritization.get('priority_count', 0)) if _operator_prioritization else 0
    _operator_priority_top_gate = str(_operator_prioritization.get('top_priority_gate_id', 'n/a')) if _operator_prioritization else 'n/a'
    _operator_priority_next_action = str(_operator_prioritization.get('operator_next_action', 'n/a')) if _operator_prioritization else 'n/a'
    _operator_priority_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('priority_score', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('urgency_boost', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('recommended_action', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_prioritization.get('priorities', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='5'>No AP-22 remediation priorities available.</td></tr>"

    _operator_delta_ledger = operator_failure_drill_delta_ledger_view_model or {}
    _operator_delta_snapshot_count = int(_operator_delta_ledger.get('snapshot_count', 0)) if _operator_delta_ledger else 0
    _operator_delta_top_regression_gate = str(_operator_delta_ledger.get('top_regression_gate_id', 'n/a')) if _operator_delta_ledger else 'n/a'
    _operator_delta_narrative = str(_operator_delta_ledger.get('operator_impact_narrative', 'n/a')) if _operator_delta_ledger else 'n/a'
    _operator_delta_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('movement_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('previous_scenario_count', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('current_scenario_count', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('scenario_delta', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_delta_ledger.get('delta_rows', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='5'>No AP-23 delta rows available.</td></tr>"

    _operator_execution_loop = operator_remediation_execution_loop_view_model or {}
    _operator_execution_action_count = int(_operator_execution_loop.get('action_count', 0)) if _operator_execution_loop else 0
    _operator_execution_open_action_count = int(_operator_execution_loop.get('open_action_count', 0)) if _operator_execution_loop else 0
    _operator_execution_next_action_id = str(_operator_execution_loop.get('next_action_id', 'n/a')) if _operator_execution_loop else 'n/a'
    _operator_execution_next_action = str(_operator_execution_loop.get('operator_next_action', 'n/a')) if _operator_execution_loop else 'n/a'
    _operator_execution_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('action_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('gate_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('priority_rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('current_movement_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('execution_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('closure_target', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_execution_loop.get('actions', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='6'>No AP-24 execution-loop actions available.</td></tr>"

    _operator_stale_closure = operator_stale_remediation_closure_drill_view_model or {}
    _operator_stale_closure_injected = _operator_stale_closure.get('stale_remediation_gap_injected') if isinstance(_operator_stale_closure.get('stale_remediation_gap_injected'), dict) else {}
    _operator_stale_closure_requires = bool(_operator_stale_closure_injected.get('requires_closure', False)) if _operator_stale_closure_injected else False
    _operator_stale_closure_guarded = bool(_operator_stale_closure_injected.get('closure_guarded', True)) if _operator_stale_closure_injected else True
    _operator_stale_closure_sla = _operator_stale_closure_injected.get('actionability_sla_hours', 'n/a') if _operator_stale_closure_injected else 'n/a'
    _operator_stale_closure_breach_count = int(_operator_stale_closure_injected.get('breach_count', 0)) if _operator_stale_closure_injected else 0
    _operator_stale_closure_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('reason', 'n/a')))}</td>"
        f"<td>{html.escape(str((item.get('item') or {}).get('priority_score', 'n/a')))}</td>"
        f"<td>{html.escape(str((item.get('item') or {}).get('unresolved_age_hours', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_stale_closure_injected.get('breaches', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='3'>No AP-20 stale-remediation breaches available.</td></tr>"

    _operator_stale_action_plan = operator_stale_remediation_action_plan_view_model or {}
    _operator_stale_action_count = int(_operator_stale_action_plan.get('action_count', 0)) if _operator_stale_action_plan else 0
    _operator_stale_next_action_id = str(_operator_stale_action_plan.get('next_action_id', 'n/a')) if _operator_stale_action_plan else 'n/a'
    _operator_stale_next_action = str(_operator_stale_action_plan.get('operator_next_action', 'n/a')) if _operator_stale_action_plan else 'n/a'
    _operator_stale_action_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('action_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('breach_reason', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('action_category', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('execution_status', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('closure_check', 'n/a')))}</td>"
        "</tr>"
        for item in _operator_stale_action_plan.get('actions', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='5'>No AP-25 stale-remediation action plan available.</td></tr>"

    _analyst_briefing = analyst_briefing_view_model or {}
    _analyst_briefing_items = [item for item in _analyst_briefing.get('items', []) if isinstance(item, dict)]
    _analyst_briefing_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(item.get('rank', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('category', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('title', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('why_it_matters', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('recommended_next_check', 'n/a')))}</td>"
        f"<td>{html.escape(str(item.get('target_page', 'n/a')))}</td>"
        "</tr>"
        for item in _analyst_briefing_items
    ) or "<tr><td colspan='6'>No analyst briefing items currently prioritized.</td></tr>"
    _analyst_hotspot_matrix = _analyst_briefing.get('country_hotspot_matrix', {}) if isinstance(_analyst_briefing.get('country_hotspot_matrix', {}), dict) else {}
    _analyst_hotspot_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(row.get('country_id', 'n/a')))}</td>"
        f"<td>{html.escape(str(row.get('signal_count', 0)))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('signals', [])) or 'none')}</td>"
        f"<td>{html.escape(str(row.get('priority', 'n/a')))}</td>"
        f"<td>{html.escape(', '.join(str(item) for item in row.get('missing_domains', [])) or 'none')}</td>"
        f"<td>{html.escape(str(row.get('attention_case_count', 0)))}</td>"
        f"<td>{html.escape(str(row.get('top_attention_case_id', 'n/a') or 'n/a'))}</td>"
        f"<td>{html.escape(_format_freshness(row.get('freshness_hours')))}</td>"
        f"<td>{html.escape(str(row.get('recommended_next_check', 'n/a')))}</td>"
        f"<td>{' | '.join(link for link in [
            (f"<a href=\"{html.escape(str(row.get('coverage_prefill_href') or row.get('coverage_href')))}\">Coverage</a>" if (row.get('coverage_prefill_href') or row.get('coverage_href')) else ''),
            (f"<a href=\"{html.escape(str(row.get('validation_prefill_href') or row.get('validation_href')))}\">Validation</a>" if (row.get('validation_prefill_href') or row.get('validation_href')) else ''),
        ] if link) or 'n/a'}</td>"
        "</tr>"
        for row in _analyst_hotspot_matrix.get('rows', [])
        if isinstance(row, dict)
    ) or "<tr><td colspan='10'>No country hotspots currently detected.</td></tr>"

    body = (
        # === KPI Header ===
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Demo Verdict</span><div class='kpi-value' style='color:{_demo_color}'>{html.escape(_demo_v)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Release Verdict</span><div class='kpi-value' style='color:{_rel_color}'>{html.escape(_rel_v)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Gate Verdict</span><div class='kpi-value' style='color:{_gate_color}'>{html.escape(_gate_v)}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Stakeholder Focus Closure</span><div class='kpi-value' style='color:{_stakeholder_color}'>{html.escape(_stakeholder_status)} ({html.escape(str(_stakeholder_closed))}/{html.escape(str(_stakeholder_covered))})</div></div>"
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
        "<div class='panel'><div class='panel-header'>Release Readiness Index</div>"
        f"<p>Passed Gates: <strong>{html.escape(str(_readiness_passed))}/{html.escape(str(_readiness_total))}</strong> ({html.escape(str(_readiness_percent))}%)</p>"
        "<table><thead><tr><th>Gate</th><th>Status</th><th>Detail</th></tr></thead>"
        f"<tbody>{_readiness_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Stakeholder E2E Flow Coverage (AP-04/AP-05)</div>"
        f"<p>Covered Flows: <strong>{html.escape(str(_e2e_covered_flow_count))}/{html.escape(str(_e2e_flow_count))}</strong> | Flow Gaps: {html.escape(str(_e2e_flow_gap_count))} | Missing Evidence Refs: {html.escape(str(_e2e_missing_evidence_refs))} | Missing Requirement Refs: {html.escape(str(_e2e_missing_requirement_refs))}</p>"
        "<table><thead><tr><th>Stop Criterion</th><th>Status</th></tr></thead>"
        f"<tbody>{_e2e_stop_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Stakeholder E2E UI Smoke Coverage (AP-07/AP-08)</div>"
        f"<p>Covered Flows: <strong>{html.escape(str(_e2e_ui_smoke_covered))}/{html.escape(str(_e2e_ui_smoke_flow_count))}</strong> | Flow Gaps: {html.escape(str(_e2e_ui_smoke_gaps))}</p>"
        "<table><thead><tr><th>UI Smoke Stop Criterion</th><th>Status</th></tr></thead>"
        f"<tbody>{_e2e_ui_smoke_stop_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Operator Release Steering (AP-16/AP-17/AP-19/AP-20/AP-22/AP-23/AP-24)</div>"
        f"<p>AP-16 failed gates: <strong>{html.escape(str(_operator_failed_gate_count))}</strong> | AP-16 next action: {html.escape(_operator_next_action)}</p>"
        "<table><thead><tr><th>AP-16 Gate</th><th>Detail</th><th>Remediation</th></tr></thead>"
        f"<tbody>{_operator_failed_rows}</tbody></table>"
        f"<p>AP-26 primary root cause: <strong>{html.escape(_operator_primary_root_cause)}</strong> | AP-26 root causes: {html.escape(_operator_root_causes)} | derived effects: {html.escape(_operator_derived_effects)} | AP-26 next action: {html.escape(_operator_blocker_next_action)}</p>"
        "<table><thead><tr><th>AP-26 Gate</th><th>Role</th><th>Causal Detail</th></tr></thead>"
        f"<tbody>{_operator_blocker_rows}</tbody></table>"
        f"<p>AP-27 cluster status: <strong>{html.escape(_operator_operability_status)}</strong> | AP-27 covered gates: <strong>{html.escape(str(_operator_operability_covered))}</strong> | failed gates: {html.escape(str(_operator_operability_failed))} | AP-27 next action: {html.escape(_operator_operability_next_action)}</p>"
        "<table><thead><tr><th>AP-27 Gate</th><th>Group</th><th>Cluster Role</th><th>Status</th></tr></thead>"
        f"<tbody>{_operator_operability_rows}</tbody></table>"
        f"<p>AP-17 cluster count: <strong>{html.escape(str(_operator_digest_cluster_count))}</strong> | Top cluster gate: {html.escape(_operator_digest_top_gate)} | AP-17 next action: {html.escape(_operator_digest_next_action)}</p>"
        "<table><thead><tr><th>AP-17 Gate</th><th>Scenario Count</th><th>Scenario IDs</th><th>Remediation</th></tr></thead>"
        f"<tbody>{_operator_digest_rows}</tbody></table>"
        f"<p>AP-19 trend snapshots: <strong>{html.escape(str(_operator_trend_snapshot_count))}</strong> | Top recurring gate: {html.escape(_operator_trend_top_gate)} | AP-19 focus: {html.escape(_operator_trend_focus)}</p>"
        "<table><thead><tr><th>AP-19 Gate</th><th>Scenario Count</th><th>Trend Status</th><th>Trajectory</th><th>Recurrence Ratio</th></tr></thead>"
        f"<tbody>{_operator_trend_rows}</tbody></table>"
        f"<p>AP-22 priority rows: <strong>{html.escape(str(_operator_priority_count))}</strong> | Top priority gate: {html.escape(_operator_priority_top_gate)} | AP-22 next action: {html.escape(_operator_priority_next_action)}</p>"
        "<table><thead><tr><th>AP-22 Rank</th><th>Gate</th><th>Priority Score</th><th>Urgency Boost</th><th>Recommended Action</th></tr></thead>"
        f"<tbody>{_operator_priority_rows}</tbody></table>"
        f"<p>AP-23 delta snapshot count: <strong>{html.escape(str(_operator_delta_snapshot_count))}</strong> | Top regression gate: {html.escape(_operator_delta_top_regression_gate)} | AP-23 impact: {html.escape(_operator_delta_narrative)}</p>"
        "<table><thead><tr><th>AP-23 Gate</th><th>Movement</th><th>Previous Count</th><th>Current Count</th><th>Delta</th></tr></thead>"
        f"<tbody>{_operator_delta_rows}</tbody></table>"
        f"<p>AP-24 open actions: <strong>{html.escape(str(_operator_execution_open_action_count))}</strong> / {html.escape(str(_operator_execution_action_count))} | Next action ID: {html.escape(_operator_execution_next_action_id)} | AP-24 next action: {html.escape(_operator_execution_next_action)}</p>"
        "<table><thead><tr><th>AP-24 Action ID</th><th>Gate</th><th>Priority Rank</th><th>Movement</th><th>Status</th><th>Closure Target</th></tr></thead>"
        f"<tbody>{_operator_execution_rows}</tbody></table>"
        f"<p>AP-25 stale actions: <strong>{html.escape(str(_operator_stale_action_count))}</strong> | Next action ID: {html.escape(_operator_stale_next_action_id)} | AP-25 next action: {html.escape(_operator_stale_next_action)}</p>"
        "<table><thead><tr><th>AP-25 Action ID</th><th>Breach Reason</th><th>Action Category</th><th>Status</th><th>Closure Check</th></tr></thead>"
        f"<tbody>{_operator_stale_action_rows}</tbody></table>"
        f"<p>AP-20 requires closure: <strong>{'yes' if _operator_stale_closure_requires else 'no'}</strong> | closure guarded: <strong>{'yes' if _operator_stale_closure_guarded else 'no'}</strong> | SLA hours: {html.escape(str(_operator_stale_closure_sla))} | breach count: {html.escape(str(_operator_stale_closure_breach_count))}</p>"
        "<table><thead><tr><th>AP-20 Breach Reason</th><th>Priority Score</th><th>Unresolved Age Hours</th></tr></thead>"
        f"<tbody>{_operator_stale_closure_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Analyst Briefing — What matters now?</div>"
        f"<p>Prioritized items: <strong>{html.escape(str(_analyst_briefing.get('item_count', 0)))}</strong> | release blockers: {html.escape(str(_analyst_briefing.get('release_blocker_count', 0)))} | country gaps: {html.escape(str(_analyst_briefing.get('country_gap_count', 0)))} | validation attention: {html.escape(str(_analyst_briefing.get('validation_attention_count', 0)))} | traceability risk: {html.escape(str(_analyst_briefing.get('traceability_risk_count', 0)))} | operability cluster: {html.escape(str(_analyst_briefing.get('operability_cluster_count', 0)))} | stale priorities: {html.escape(str(_analyst_briefing.get('stale_priority_count', 0)))} | stale remediation actions: {html.escape(str(_analyst_briefing.get('stale_remediation_action_plan_count', 0)))}</p>"
        f"<p>Primary focus: <strong>{html.escape(str(_analyst_briefing.get('primary_item_title', 'n/a')))}</strong> → {html.escape(str(_analyst_briefing.get('primary_item_target_page', 'n/a')))} | next check: {html.escape(str(_analyst_briefing.get('primary_item_next_check', 'n/a')))} | evidence: {html.escape(str(_analyst_briefing.get('primary_item_evidence_source', 'n/a')))}</p>"
        "<table><thead><tr><th>Rank</th><th>Category</th><th>Title</th><th>Why it matters</th><th>Recommended next check</th><th>Target page</th></tr></thead>"
        f"<tbody>{_analyst_briefing_rows}</tbody></table></div>"
        "<div class='panel'><div class='panel-header'>Analyst Hotspot Matrix — cross-signal convergence</div>"
        f"<p>Multi-signal countries: <strong>{html.escape(str(_analyst_hotspot_matrix.get('multi_signal_country_count', 0)))}</strong> / {html.escape(str(_analyst_hotspot_matrix.get('row_count', 0)))} | signals combine coverage gaps, validation attention, and stale-priority cues per country.</p>"
        "<table><thead><tr><th>Country</th><th>Signals</th><th>Signal Types</th><th>Priority</th><th>Missing Domains</th><th>Attention Cases</th><th>Top Case</th><th>Freshness</th><th>Recommended Next Check</th><th>Hotspot Links</th></tr></thead>"
        f"<tbody>{_analyst_hotspot_rows}</tbody></table></div>"
        # === Known Gaps ===
        "<div class='panel'><div class='panel-header'>Known Gaps Before Release</div>"
        f"<ul>{known_gap_items}</ul></div>"
        "<div class='panel'><div class='panel-header'>Release Gate Blockers</div>"
        f"<ul>{_gate_blocker_items}</ul></div>"
        "<div class='panel'><div class='panel-header'>Stakeholder Functional Closure Focus Cluster</div>"
        f"<p>Covered IDs: {html.escape(str(_stakeholder_covered))} / 19 | Open IDs: {html.escape(str(_stakeholder_open))}</p>"
        f"<ul>{_stakeholder_open_items}</ul></div>"
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
            f"<td><div class='trend-chart-block'><h4>Trend Chart</h4>"
            f"<div class='trend-range-controls' style='display:flex;gap:4px;margin-bottom:4px;'>"
            f"<button class='trend-range-btn' data-range='6m' style='background:#1a2540;color:#6b7d99;border:1px solid #263050;padding:2px 8px;border-radius:2px;cursor:pointer;font-size:10px;font-family:Space Grotesk,monospace;'>6M</button>"
            f"<button class='trend-range-btn' data-range='1y' style='background:#1a2540;color:#6b7d99;border:1px solid #263050;padding:2px 8px;border-radius:2px;cursor:pointer;font-size:10px;font-family:Space Grotesk,monospace;'>1Y</button>"
            f"<button class='trend-range-btn' data-range='all' style='background:#1a2540;color:#4edea3;border:1px solid #4edea3;padding:2px 8px;border-radius:2px;cursor:pointer;font-size:10px;font-family:Space Grotesk,monospace;'>All</button>"
            f"</div>"
            f"{_render_line_chart(yearly, label_key='label', chart_label=f'{country_id} yearly trend')}{_render_historical_comparison_summary(yearly, label_key='label')}</div><div class='trend-event-overlay' style='display:none'><h4>Event Overlay Summary</h4><ul>{event_overlay}</ul></div></td>"
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
        + _render_enhanced_trend_controls_js()
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
    mw_rows = []
    for country_id, profile in sorted(country_profile_read_models.items()):
        domain_states = profile.get('domain_states', {})
        domain_pairs = [f'{domain}:{status}' for domain, status in sorted(domain_states.items())]
        drivers = [str(item) for item in profile.get('drivers', [])]
        coverage_band = _ratio_band(profile.get('coverage'))
        confidence_band = _ratio_band(profile.get('confidence'))
        uncertainty_count = len(profile.get('uncertainty', []))
        coverage_value = profile.get('coverage')
        confidence_value = profile.get('confidence')
        rows.append(
            f"<tr class='comparison-row' data-country-id='{html.escape(country_id)}' data-status='{html.escape(str(profile.get('multi_domain_status', 'n/a')))}' data-coverage-band='{html.escape(coverage_band)}' data-confidence-band='{html.escape(confidence_band)}' data-uncertainty-count='{uncertainty_count}' data-coverage-value='{html.escape(str(coverage_value if coverage_value is not None else ''))}' data-confidence-value='{html.escape(str(confidence_value if confidence_value is not None else ''))}' data-drivers='{html.escape('|'.join(drivers))}'>"
            f"<td>{html.escape(country_id)}</td>"
            f"<td>{html.escape(str(profile.get('multi_domain_status', 'n/a')))}</td>"
            f"<td>{html.escape(', '.join(domain_pairs))}</td>"
            f"<td>{_render_metric_meter('Coverage', coverage_value, fill_color=_band_color(coverage_band))}</td>"
            f"<td>{_render_metric_meter('Confidence', confidence_value, fill_color=_band_color(confidence_band))}</td>"
            f"<td>{html.escape(', '.join(drivers))}</td>"
            f"<td>{_render_uncertainty_badges(profile.get('uncertainty', []))}</td>"
            "<td class='comparison-baseline-cell'>Global mode</td>"
            "</tr>"
        )
        mw_rows.append(
            f"mwData[{json.dumps(country_id)}]={{"
            f"status:{json.dumps(str(profile.get('multi_domain_status', 'n/a')))},"
            f"domains:{json.dumps(domain_pairs)},"
            f"coverage:{json.dumps(coverage_value)},"
            f"confidence:{json.dumps(confidence_value)},"
            f"drivers:{json.dumps(drivers)}"
            "};"
        )
    country_options = ''.join(
        f"<option value={chr(39)}{html.escape(cid)}{chr(39)}>{html.escape(cid)}</option>"
        for cid in sorted(country_profile_read_models)
    )
    body = (
        "<h2>Cross-Country Comparison</h2>"
        "<h3>Comparison controls</h3>"
        "<div style='display:flex;gap:12px;flex-wrap:wrap;align-items:end;'>"
        "<div><label for='comparison-filter'>Coverage / Uncertainty Focus</label> "
        "<select id='comparison-filter' name='comparison-filter'>"
        "<option value='all'>All countries</option>"
        "<option value='low_coverage'>Low coverage only</option>"
        "<option value='low_confidence'>Low confidence only</option>"
        "<option value='has_uncertainty'>With uncertainty flags</option>"
        "</select></div>"
        "<div><label for='comparison-mode'>Comparison Mode</label> "
        "<select id='comparison-mode' name='comparison-mode'>"
        "<option value='global'>Global comparison</option>"
        "<option value='relative_baseline'>Relative baseline</option>"
        "</select></div>"
        "<div id='comparison-baseline-controls' style='display:none;'><label for='comparison-baseline'>Baseline Country</label> "
        f"<select id='comparison-baseline' name='comparison-baseline'><option value=''>— select baseline —</option>{country_options}</select></div>"
        "</div>"
        "<p id='comparison-filter-result'>Selected Comparison Filter: all countries</p>"
        "<p id='comparison-mode-result'>Comparison mode: global</p>"
        "<div id='comparison-relative-summary' class='mini-section'><p style='margin:0;'>Global comparison mode active. Switch to relative baseline to quantify deltas against a chosen country.</p></div>"
        "<h3>Coverage / Confidence Comparison</h3>"
        "<table><thead><tr><th>Country</th><th>Multi-Domain Status</th><th>Domain States</th><th>Coverage</th><th>Confidence</th><th>Drivers</th><th>Uncertainty</th><th>Relative Baseline</th></tr></thead>"
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
        "var mwData={};"
        + ''.join(mw_rows)
        + "function formatSignedDelta(value){if(!Number.isFinite(value)){return 'n/a';}var sign=value>0?'+':'';return sign+value.toFixed(2);}"
        "function renderComparisonBaseline(){"
        "const mode=document.getElementById('comparison-mode').value;"
        "const baselineControls=document.getElementById('comparison-baseline-controls');"
        "const baselineSelect=document.getElementById('comparison-baseline');"
        "const summary=document.getElementById('comparison-relative-summary');"
        "const modeResult=document.getElementById('comparison-mode-result');"
        "baselineControls.style.display=mode==='relative_baseline'?'block':'none';"
        "if(mode!=='relative_baseline'){document.querySelectorAll('.comparison-baseline-cell').forEach((cell)=>{cell.textContent='Global mode';});summary.innerHTML='<p style=\"margin:0;\">Global comparison mode active. Switch to relative baseline to quantify deltas against a chosen country.</p>';modeResult.textContent='Comparison mode: global';return;}"
        "const baselineId=baselineSelect.value;"
        "if(!baselineId||!mwData[baselineId]){document.querySelectorAll('.comparison-baseline-cell').forEach((cell)=>{cell.textContent='Select baseline';});summary.innerHTML='<p style=\"margin:0;\">Relative baseline mode active. Select a baseline country to compare status, coverage, confidence, and shared drivers.</p>';modeResult.textContent='Comparison mode: relative_baseline';return;}"
        "const baseline=mwData[baselineId];"
        "summary.innerHTML='<strong>Relative Baseline Summary</strong><div style=\"margin-top:6px;font-size:12px;\">Baseline '+baselineId+' · status '+baseline.status+' · coverage '+(baseline.coverage===null?'n/a':Number(baseline.coverage).toFixed(2))+' · confidence '+(baseline.confidence===null?'n/a':Number(baseline.confidence).toFixed(2))+'</div>';"
        "document.querySelectorAll('.comparison-row').forEach((row)=>{"
        "const countryId=row.dataset.countryId;"
        "const cell=row.querySelector('.comparison-baseline-cell');"
        "if(countryId===baselineId){cell.textContent='Baseline reference';return;}"
        "const coverageValue=Number(row.dataset.coverageValue);"
        "const confidenceValue=Number(row.dataset.confidenceValue);"
        "const rowDrivers=(row.dataset.drivers||'').split('|').filter(Boolean);"
        "const sharedDrivers=rowDrivers.filter((driver)=>baseline.drivers.indexOf(driver)>=0).length;"
        "const statusDelta=row.dataset.status===baseline.status?'same status':'different status';"
        "const coverageDelta=formatSignedDelta(coverageValue-baseline.coverage);"
        "const confidenceDelta=formatSignedDelta(confidenceValue-baseline.confidence);"
        "cell.textContent='Status: '+statusDelta+' · Coverage Δ '+coverageDelta+' · Confidence Δ '+confidenceDelta+' · Shared drivers '+sharedDrivers+'/'+baseline.drivers.length;"
        "});"
        "modeResult.textContent='Comparison mode: relative_baseline';"
        "}"
        "document.getElementById('comparison-filter').addEventListener('change', applyComparisonFilters);"
        "document.getElementById('comparison-mode').addEventListener('change', renderComparisonBaseline);"
        "document.getElementById('comparison-baseline').addEventListener('change', renderComparisonBaseline);"
        "applyComparisonFilters();"
        "renderComparisonBaseline();"
        "</script>"
        "<h3>Multi-Window Parallel Comparison</h3>"
        "<p style='font-size:11px;color:#6b7d99;font-family:Space Grotesk,monospace;'>Select two countries to compare side-by-side.</p>"
        "<div id='multi-window-controls' style='display:flex;gap:12px;margin-bottom:12px;'>"
        "<div><label for='mw-country-left' style='font-size:11px;color:#6b7d99;'>Left Panel</label> "
        "<select id='mw-country-left' style='background:#1a2540;color:#dae2fd;border:1px solid #263050;padding:4px;font-size:11px;'>"
        f"<option value=''>— select —</option>{country_options}"
        "</select></div>"
        "<div><label for='mw-country-right' style='font-size:11px;color:#6b7d99;'>Right Panel</label> "
        "<select id='mw-country-right' style='background:#1a2540;color:#dae2fd;border:1px solid #263050;padding:4px;font-size:11px;'>"
        f"<option value=''>— select —</option>{country_options}"
        "</select></div>"
        "</div>"
        "<div id='multi-window-panels' style='display:grid;grid-template-columns:1fr 1fr;gap:12px;'>"
        "<div id='mw-panel-left' style='background:#0f1828;border:1px solid rgba(78,222,163,.15);border-radius:3px;padding:10px;min-height:100px;'>"
        "<p style='color:#6b7d99;font-size:11px;'>Select a country for left panel</p></div>"
        "<div id='mw-panel-right' style='background:#0f1828;border:1px solid rgba(78,222,163,.15);border-radius:3px;padding:10px;min-height:100px;'>"
        "<p style='color:#6b7d99;font-size:11px;'>Select a country for right panel</p></div>"
        "</div>"
        "<script>"
        "function renderMWPanel(panelId,cid){"
        "var p=document.getElementById(panelId);"
        "if(!p)return;"
        "if(!cid||!mwData[cid]){p.innerHTML='<p style=\"color:#6b7d99;font-size:11px;\">Select a country</p>';return;}"
        "var d=mwData[cid];"
        "var domains=Array.isArray(d.domains)?d.domains.join(', '):'n/a';"
        "var drivers=Array.isArray(d.drivers)?d.drivers.join(', '):'n/a';"
        "p.innerHTML='<h4 style=\"color:#4edea3;margin:0 0 8px;\">'+cid+'</h4>'"
        "+'<div style=\"font-size:12px;color:#dae2fd;\"><b>Status:</b> '+d.status+'<br><b>Domains:</b> '+domains+'<br><b>Coverage:</b> '+d.coverage+'<br><b>Confidence:</b> '+d.confidence+'<br><b>Drivers:</b> '+drivers+'</div>';}"
        "document.getElementById('mw-country-left').addEventListener('change',function(){renderMWPanel('mw-panel-left',this.value);});"
        "document.getElementById('mw-country-right').addEventListener('change',function(){renderMWPanel('mw-panel-right',this.value);});"
        "</script>"
    )
    return _page("Cross-Country Comparison", body, nav_prefix=nav_prefix, available_pages=available_pages)


def _verdict_badge(verdict: str) -> str:
    """Return a styled badge for a validation/replay verdict string."""
    v = str(verdict).lower()
    if v in ('match', 'full_match', 'confirmed', 'pass'):
        css = 'badge-green'
        icon = '✓'
    elif v in ('match_with_gaps', 'partial', 'partial_match', 'support_check'):
        css = 'badge-blue'
        icon = '~'
    elif v in ('mismatch', 'fail', 'failed', 'no_match'):
        css = 'badge-red'
        icon = '✗'
    elif v in ('pending', 'open', 'review', 'n/a', 'none', ''):
        css = 'badge-gray'
        icon = '?'
    else:
        css = 'badge-amber'
        icon = '!'
    label = html.escape(str(verdict))
    return f"<span class='badge {css}'>{icon} {label}</span>"


def _attention_level_badge(level: str) -> str:
    """Return a styled badge for an attention level."""
    l = str(level).lower()
    if 'high' in l or 'critical' in l:
        css = 'badge-red'
    elif 'medium' in l or 'moderate' in l:
        css = 'badge-amber'
    elif 'low' in l:
        css = 'badge-green'
    else:
        css = 'badge-gray'
    return f"<span class='badge {css}'>{html.escape(str(level))}</span>"


def _evidence_tier_badge(tier: str) -> str:
    """Return a styled badge for an evidence tier."""
    t = str(tier).lower()
    if t in ('high', 'tier_1', 'tier1', 'strong'):
        css = 'badge-green'
    elif t in ('medium', 'tier_2', 'tier2', 'moderate'):
        css = 'badge-blue'
    elif t in ('low', 'tier_3', 'tier3', 'weak'):
        css = 'badge-amber'
    elif t in ('insufficient', 'none', 'n/a', ''):
        css = 'badge-gray'
    else:
        css = 'badge-gray'
    return f"<span class='badge {css}'>{html.escape(str(tier))}</span>"


def _render_validation_kpi_grid(
    portfolio_summary: dict[str, Any],
    historical_replay_summary: dict[str, Any],
    historical_reference_review_summary: dict[str, Any],
    review_verdict: str,
) -> str:
    case_count = portfolio_summary.get('case_count', 0)
    countries = portfolio_summary.get('countries_covered', [])
    portfolio_gap_case_count = len([case for case in portfolio_summary.get('cases_with_gaps', []) if isinstance(case, dict)])
    replay_score = historical_replay_summary.get('average_replay_evidence_score', 'n/a')
    status_match = historical_replay_summary.get('status_match_count', 'n/a')
    attention_count = historical_replay_summary.get('attention_case_count', 0)
    avg_domain_match = historical_replay_summary.get('average_domain_match_ratio', 'n/a')
    ref_score = historical_reference_review_summary.get('average_evidence_score', 'n/a')

    verdict_badge = _verdict_badge(review_verdict)

    def _fmt_ratio(v: Any) -> str:
        try:
            return f"{float(v):.0%}"
        except (TypeError, ValueError):
            return str(v)

    attention_color = '#ffb4ab' if attention_count and int(attention_count) > 0 else '#4edea3'
    attention_style = f"style='color:{attention_color}'"

    return (
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Verdict</span>"
        f"<div class='kpi-value' style='font-size:1rem;padding-top:4px'>{verdict_badge}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Cases</span>"
        f"<div class='kpi-value'>{html.escape(str(case_count))}</div>"
        f"<div class='kpi-sub'>{html.escape(', '.join(str(c) for c in countries))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Avg Domain Match</span>"
        f"<div class='kpi-value'>{html.escape(_fmt_ratio(avg_domain_match))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Status Matches</span>"
        f"<div class='kpi-value'>{html.escape(str(status_match))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Replay Evidence Score</span>"
        f"<div class='kpi-value'>{html.escape(str(replay_score))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Ref. Evidence Score</span>"
        f"<div class='kpi-value'>{html.escape(str(ref_score))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Attention Cases</span>"
        f"<div class='kpi-value' {attention_style}>{html.escape(str(attention_count))}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Non-Perfect Cases</span>"
        f"<div class='kpi-value'>{html.escape(str(portfolio_gap_case_count))}</div></div>"
        "</div>"
    )


def _render_attention_case_cards(attention_cases: list[dict[str, Any]]) -> str:
    """Render replay attention cases as structured cards instead of a raw table row."""
    if not attention_cases:
        return "<p style='color:#6b7d99;font-size:12px;'>No attention cases flagged.</p>"
    cards = []
    for case in attention_cases:
        if not isinstance(case, dict):
            continue
        country_raw = str(case.get('country_id', 'n/a'))
        case_id_raw = str(case.get('case_id', 'n/a'))
        att_level_raw = str(case.get('attention_level', 'n/a'))
        reason_raw = str(case.get('attention_reason', 'n/a'))
        owner_raw = str(case.get('owner_hint', 'n/a'))
        verdict_raw = str(case.get('review_verdict', 'n/a'))
        tier_raw = str(case.get('replay_evidence_tier', 'n/a'))
        next_action_raw = str(case.get('suggested_next_action', 'n/a'))

        country = html.escape(country_raw)
        case_id = html.escape(case_id_raw)
        att_level = att_level_raw
        reason = html.escape(reason_raw)
        owner = html.escape(owner_raw)
        verdict = verdict_raw
        tier = tier_raw
        missing = [str(d) for d in case.get('missing_expected_domains', [])]
        unexpected = [str(d) for d in case.get('unexpected_observed_domains', [])]
        next_action = html.escape(next_action_raw)
        src_coverage = case.get('replay_source_coverage_ratio', None)

        missing_html = (
            "".join(f"<span class='badge badge-orange'>{html.escape(d)}</span> " for d in missing)
            if missing else "<span style='color:#6b7d99;font-size:11px;'>none</span>"
        )
        unexpected_html = (
            "".join(f"<span class='badge badge-amber'>{html.escape(d)}</span> " for d in unexpected)
            if unexpected else "<span style='color:#6b7d99;font-size:11px;'>none</span>"
        )

        src_cov_html = ""
        if src_coverage is not None:
            try:
                pct = f"{float(src_coverage):.0%}"
                src_cov_html = f"<span class='kpi-sub'>Source coverage: {html.escape(pct)}</span>"
            except (TypeError, ValueError):
                src_cov_html = f"<span class='kpi-sub'>Source coverage: {html.escape(str(src_coverage))}</span>"

        card_search_text = ' '.join(
            [
                country_raw,
                case_id_raw,
                reason_raw,
                owner_raw,
                verdict_raw,
                tier_raw,
                next_action_raw,
            ]
        ).strip().lower()
        cards.append(
            "<div class='panel replay-attention-card'"
            f" id='attention-case-{html.escape(_slugify_anchor_token(case_id_raw))}'"
            f" data-attention-level='{html.escape(att_level_raw.lower())}'"
            f" data-attention-owner='{html.escape(owner_raw.lower())}'"
            f" data-attention-reason='{html.escape(reason_raw.lower())}'"
            f" data-review-verdict='{html.escape(verdict_raw.lower())}'"
            f" data-replay-tier='{html.escape(tier_raw.lower())}'"
            f" data-card-search-text='{html.escape(card_search_text)}'"
            " style='border-left:3px solid rgba(255,180,171,.5);'>"
            "<div style='display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:8px;margin-bottom:10px;'>"
            f"<div><span class='mono' style='font-size:0.75rem;color:#4edea3;'>{country}</span>"
            f"<span style='color:#4b5778;margin:0 6px;'>·</span>"
            f"<span class='mono' style='font-size:0.75rem;color:#8b9ab8;'>{case_id}</span></div>"
            f"<div style='display:flex;gap:6px;flex-wrap:wrap;'>{_attention_level_badge(att_level)}"
            f"{_verdict_badge(verdict)}{_evidence_tier_badge(tier)}</div>"
            "</div>"
            f"<p style='margin:0 0 8px;color:#b9c7e0;'><strong>Reason:</strong> {reason}</p>"
            f"<p style='margin:0 0 6px;color:#b9c7e0;'><strong>Follow-up owner:</strong> {owner}</p>"
            f"<div style='margin:8px 0;'>"
            f"<span class='kpi-label' style='display:inline;margin-right:8px;'>Missing domains:</span>{missing_html}"
            f"</div>"
            f"<div style='margin:8px 0;'>"
            f"<span class='kpi-label' style='display:inline;margin-right:8px;'>Unexpected domains:</span>{unexpected_html}"
            f"</div>"
            f"<div style='margin-top:10px;padding-top:8px;border-top:1px solid rgba(78,222,163,.06);'>"
            f"<span class='kpi-label'>Suggested action:</span> "
            f"<span style='color:#dae2fd;font-size:12px;'>{next_action}</span>"
            f"{src_cov_html}"
            "</div>"
            "</div>"
        )
    return "".join(cards)


def _render_verdict_distribution_bars(verdict_counts: dict[str, int]) -> str:
    """Render a simple inline bar chart for verdict distributions."""
    if not verdict_counts:
        return "<p style='color:#6b7d99;font-size:12px;'>No data.</p>"
    total = sum(verdict_counts.values()) or 1
    rows = []
    for verdict, count in sorted(verdict_counts.items()):
        pct = count / total
        width = max(4, int(pct * 200))
        badge = _verdict_badge(verdict)
        bar_color = '#4edea3' if 'match' in verdict.lower() else '#ffb4ab' if 'mismatch' in verdict.lower() else '#8b9ab8'
        rows.append(
            "<div style='display:flex;align-items:center;gap:10px;margin:6px 0;'>"
            f"<div style='min-width:170px;'>{badge}</div>"
            f"<div style='background:{bar_color};height:6px;border-radius:1px;width:{width}px;opacity:.7;'></div>"
            f"<span style='color:#8b9ab8;font-size:11px;font-family:\"Space Grotesk\",monospace;'>{count}</span>"
            "</div>"
        )
    return "".join(rows)


def _render_validation(validation_view_model: dict[str, Any], *, nav_prefix: str = '', available_pages: set[str] | None = None) -> str:
    time_range = validation_view_model.get('time_range', {})
    can_create_annotation_drafts = available_pages is not None and 'annotations.html' in available_pages
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
    portfolio_gap_case_count = len([case for case in portfolio_summary.get('cases_with_gaps', []) if isinstance(case, dict)])
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
        + (
            f"<td><a class='replay-attention-create-annotation' href='annotations.html?scope=country&annotation_type=review_note&country_id={quote_plus(str(item.get('country_id', '')))}&case_id={quote_plus(str(item.get('case_id', '')))}&attention_reason={quote_plus(str(item.get('attention_reason', '')))}&owner_hint={quote_plus(str(item.get('owner_hint', '')))}&suggested_next_action={quote_plus(str(item.get('suggested_next_action', '')))}&attention_level={quote_plus(str(item.get('attention_level', '')))}&replay_evidence_tier={quote_plus(str(item.get('replay_evidence_tier', '')))}&review_verdict={quote_plus(str(item.get('review_verdict', '')))}&replay_evidence_score={quote_plus(str(item.get('replay_evidence_score', '')))}&domain_match_ratio={quote_plus(str(item.get('domain_match_ratio', '')))}&missing_expected_domains={quote_plus(','.join(str(domain) for domain in item.get('missing_expected_domains', [])))}&unexpected_observed_domains={quote_plus(','.join(str(domain) for domain in item.get('unexpected_observed_domains', [])))}&linked_item={quote_plus(str(item.get('case_id', '')))}'>Create Annotation Draft</a></td>"
            if can_create_annotation_drafts
            else "<td>Annotation workflow unavailable for this role</td>"
        )
        + "</tr>"
        for item in historical_replay_summary.get('attention_cases', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='10'>No replay attention cases recorded.</td></tr>"
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
    # --- KPI header ---
    kpi_grid = _render_validation_kpi_grid(
        portfolio_summary, historical_replay_summary, historical_reference_review_summary, review_verdict
    )

    # --- Case meta panel ---
    case_meta = (
        "<div class='panel'><div class='panel-header'>Active Case</div>"
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px 24px;'>"
        f"<div><span class='kpi-label'>Case ID</span><div class='mono' style='color:#4edea3;font-size:0.75rem;'>{html.escape(str(validation_view_model.get('case_id', 'n/a')))}</div></div>"
        f"<div><span class='kpi-label'>Country</span><div style='font-size:1rem;font-weight:600;color:#dae2fd;'>{html.escape(str(validation_view_model.get('country_id', 'n/a')))}</div></div>"
        f"<div><span class='kpi-label'>Case Name</span><div style='color:#b9c7e0;font-size:12px;'>{html.escape(str(validation_view_model.get('case_name', 'n/a')))}</div></div>"
        f"<div><span class='kpi-label'>Time Range</span><div class='mono' style='color:#8b9ab8;font-size:0.75rem;'>{html.escape(str(time_range.get('start', 'n/a')))} → {html.escape(str(time_range.get('end', 'n/a')))}</div></div>"
        f"<div><span class='kpi-label'>Verdict</span><div style='padding-top:4px;'>{_verdict_badge(review_verdict)}</div></div>"
        "</div></div>"
    )

    # --- Domain signal panel ---
    exp_badges = "".join(f"<span class='badge badge-blue'>{html.escape(d)}</span> " for d in expected_domains) or "<span style='color:#6b7d99;font-size:11px;'>none</span>"
    obs_badges = "".join(f"<span class='badge badge-green'>{html.escape(d)}</span> " for d in observed_domains) or "<span style='color:#6b7d99;font-size:11px;'>none</span>"
    missing_badges = (
        "".join(f"<span class='badge badge-orange'>{html.escape(str(item))}</span> " for item in missing_expected_domain_values)
        or "<span style='color:#6b7d99;font-size:11px;'>none</span>"
    )
    unexpected_badges = (
        "".join(f"<span class='badge badge-amber'>{html.escape(str(item))}</span> " for item in unexpected_observed_domain_values)
        or "<span style='color:#6b7d99;font-size:11px;'>none</span>"
    )
    domain_panel = (
        "<div class='panel'><div class='panel-header'>Domain Signal</div>"
        "<div style='display:grid;grid-template-columns:1fr 1fr;gap:16px;'>"
        f"<div><span class='kpi-label'>Expected</span><div style='margin-top:6px;'>{exp_badges}</div></div>"
        f"<div><span class='kpi-label'>Observed</span><div style='margin-top:6px;'>{obs_badges}</div></div>"
        "</div>"
        f"<div style='margin-top:12px;'><span class='kpi-label' style='margin-right:8px;'>Missing:</span>{missing_badges}</div>"
        f"<div style='margin-top:6px;'><span class='kpi-label' style='margin-right:8px;'>Unexpected:</span>{unexpected_badges}</div>"
        f"<div style='margin-top:12px;display:flex;gap:20px;'>"
        f"<span><span class='kpi-label'>Domain Match Ratio:</span> <strong style='color:#dae2fd;'>{html.escape(str(validation_view_model.get('domain_match_ratio', 'n/a')))}</strong></span>"
        f"<span><span class='kpi-label'>Status Match:</span> <strong style='color:#dae2fd;'>{html.escape(str(validation_view_model.get('status_match', 'n/a')))}</strong></span>"
        "</div>"
        "</div>"
    )

    # --- Goal & Context panel ---
    sources_list = "".join(f"<li>{html.escape(str(item))}</li>" for item in validation_view_model.get('reference_sources', []))
    metrics_list = "".join(f"<li>{html.escape(str(item))}</li>" for item in validation_view_model.get('validation_metrics', []))
    limitations_list = "".join(f"<li>{html.escape(str(item))}</li>" for item in validation_view_model.get('known_limitations', []))
    goal_panel = (
        "<details><summary>Validation Goal &amp; Context</summary>"
        "<div style='padding:12px 0;'>"
        f"<p><strong>Expected Pattern:</strong> {html.escape(str(validation_view_model.get('expected_pattern', 'n/a')))}</p>"
        f"<p><strong>Goal:</strong> {html.escape(str(validation_view_model.get('validation_goal', 'n/a')))}</p>"
        f"<h4>Reference Sources</h4><ul>{sources_list or '<li>none</li>'}</ul>"
        f"<h4>Validation Metrics</h4><ul>{metrics_list or '<li>none</li>'}</ul>"
        f"<h4>Known Limitations</h4><ul>{limitations_list or '<li>none</li>'}</ul>"
        "</div></details>"
    )

    # --- Portfolio panel ---
    portfolio_verdicts_html = _render_verdict_distribution_bars(portfolio_summary.get('review_verdict_counts') or {})

    def _domain_badges_blue(domains: list) -> str:
        return "".join(f"<span class='badge badge-blue' style='margin:1px;'>{html.escape(str(d))}</span>" for d in domains)

    def _domain_badges_green(domains: list) -> str:
        return "".join(f"<span class='badge badge-green' style='margin:1px;'>{html.escape(str(d))}</span>" for d in domains)

    portfolio_case_rows_enhanced = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;color:#4edea3;'>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{_verdict_badge(str(case.get('review_verdict', 'n/a')))}</td>"
        f"<td>{_domain_badges_blue(case.get('expected_domains', []))}</td>"
        f"<td>{_domain_badges_green(case.get('observed_domains', []))}</td>"
        "</tr>"
        for case in validation_cases
    ) or "<tr><td colspan='5' style='color:#6b7d99;'>No portfolio cases available.</td></tr>"
    portfolio_gap_cases = [case for case in portfolio_summary.get('cases_with_gaps', []) if isinstance(case, dict)]
    portfolio_gap_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;color:#4edea3;'>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td>{_verdict_badge(str(case.get('review_verdict', 'n/a')))}</td>"
        "</tr>"
        for case in portfolio_gap_cases
    ) or "<tr><td colspan='3' style='color:#6b7d99;'>No non-perfect portfolio cases recorded.</td></tr>"
    portfolio_panel = (
        "<div class='panel'><div class='panel-header'>Reference Case Portfolio</div>"
        f"<div style='display:flex;gap:24px;flex-wrap:wrap;margin-bottom:14px;'>"
        f"<div><span class='kpi-label'>Cases</span><strong style='color:#dae2fd;'> {html.escape(str(portfolio_summary.get('case_count', len(validation_cases))))}</strong></div>"
        f"<div><span class='kpi-label'>Countries</span><strong style='color:#dae2fd;'> {html.escape(', '.join(str(c) for c in portfolio_summary.get('countries_covered', [])))}</strong></div>"
        f"<div><span class='kpi-label'>Non-Perfect Cases</span><strong style='color:#ffb4ab;'> {html.escape(str(portfolio_gap_case_count))}</strong></div>"
        "</div>"
        f"<div style='margin-bottom:14px;'>{portfolio_verdicts_html}</div>"
        "<div class='table-container'><table><thead><tr><th>Country</th><th>Case ID</th><th>Verdict</th><th>Expected Domains</th><th>Observed Domains</th></tr></thead>"
        f"<tbody>{portfolio_case_rows_enhanced}</tbody></table></div>"
        "</div>"
    )
    realism_panel = (
        "<div class='panel'><div class='panel-header'>Validation Realism Snapshot</div>"
        f"<p style='color:#b9c7e0;font-size:12px;margin-bottom:10px;'>"
        f"Non-perfect portfolio cases require interpretive review before treating the replay portfolio as fully representative."
        f"</p>"
        f"<div class='table-container'><table><thead><tr><th>Country</th><th>Case ID</th><th>Verdict</th></tr></thead>"
        f"<tbody>{portfolio_gap_rows}</tbody></table></div>"
        "</div>"
    )

    # --- Reference Case Library ---
    ref_lib_rows = ''.join(
        "<tr>"
        f"<td>{html.escape(str(case.get('country_id', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;'>{html.escape(str(case.get('case_id', 'n/a')))}</td>"
        f"<td><span class='badge badge-gray'>{html.escape(str(case.get('case_type', 'n/a')))}</span></td>"
        f"<td style='color:#b9c7e0;'>{html.escape(str(case.get('case_name', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;color:#6b7d99;'>{html.escape(str((case.get('time_range') or {}).get('start', 'n/a')))} → {html.escape(str((case.get('time_range') or {}).get('end', 'n/a')))}</td>"
        f"<td>{_domain_badges_blue(case.get('expected_domains', []))}</td>"
        "</tr>"
        for case in reference_case_library
    ) or "<tr><td colspan='6' style='color:#6b7d99;'>No curated reference cases recorded.</td></tr>"
    ref_lib_time = reference_case_library_summary.get('time_range') or {}
    ref_lib_panel = (
        "<details><summary>Curated Reference Case Library "
        f"<span class='badge badge-gray' style='margin-left:8px;'>{html.escape(str(reference_case_library_summary.get('case_count', len(reference_case_library))))}</span></summary>"
        "<div style='padding:12px 0;'>"
        f"<p style='color:#6b7d99;font-size:11px;margin-bottom:10px;'>Time range: {html.escape(str(ref_lib_time.get('start', 'n/a')))} → {html.escape(str(ref_lib_time.get('end', 'n/a')))}</p>"
        "<div class='table-container'><table><thead><tr><th>Country</th><th>Case ID</th><th>Type</th><th>Case</th><th>Time Range</th><th>Expected Domains</th></tr></thead>"
        f"<tbody>{ref_lib_rows}</tbody></table></div>"
        "</div></details>"
    )

    # --- Historical Reference Reviews ---
    ref_verdict_bars = _render_verdict_distribution_bars(historical_reference_review_summary.get('review_verdict_counts') or {})
    hist_ref_rows_enhanced = ''.join(
        "<tr>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;'>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{_verdict_badge(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td>{_evidence_tier_badge(str(review.get('evidence_tier', 'n/a')))}</td>"
        f"<td style='color:#dae2fd;'>{html.escape(str(review.get('evidence_score', 'n/a')))}</td>"
        f"<td><span class='badge badge-gray'>{html.escape(str(review.get('expected_status', 'n/a')))}</span></td>"
        f"<td><span class='badge badge-blue'>{html.escape(str(review.get('historical_observed_status', 'n/a')))}</span></td>"
        "</tr>"
        for review in historical_reference_reviews
    ) or "<tr><td colspan='7' style='color:#6b7d99;'>No historical reference reviews recorded.</td></tr>"
    hist_ref_panel = (
        "<details><summary>Historical Reference Reviews "
        f"<span class='badge badge-gray' style='margin-left:8px;'>{len(historical_reference_reviews)}</span></summary>"
        "<div style='padding:12px 0;'>"
        f"<div style='margin-bottom:12px;'>{ref_verdict_bars}</div>"
        "<div class='table-container'><table><thead><tr><th>Country</th><th>Case ID</th><th>Verdict</th><th>Evidence Tier</th><th>Evidence Score</th><th>Expected Status</th><th>Historical Observed</th></tr></thead>"
        f"<tbody>{hist_ref_rows_enhanced}</tbody></table></div>"
        "</div></details>"
    )

    # --- Historical Replay Summary ---
    replay_verdict_bars = _render_verdict_distribution_bars(historical_replay_summary.get('review_verdict_counts') or {})
    replay_country_rows = ''.join(
        "<tr>"
        f"<td><strong>{html.escape(str(item.get('country_id', 'n/a')))}</strong></td>"
        f"<td>{html.escape(str(item.get('attention_case_count', 'n/a')))}</td>"
        f"<td>{_attention_level_badge(str(item.get('highest_attention_level', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;color:#8b9ab8;'>{html.escape(', '.join(str(cid) for cid in item.get('case_ids', [])) or 'none')}</td>"
        "</tr>"
        for item in historical_replay_summary.get('attention_country_summary', [])
        if isinstance(item, dict)
    ) or "<tr><td colspan='4' style='color:#6b7d99;'>No country attention summary recorded.</td></tr>"

    prov_ratio = historical_replay_summary.get('average_replay_provenance_completeness_ratio', 'n/a')
    src_ratio = historical_replay_summary.get('average_replay_source_coverage_ratio', 'n/a')
    try:
        prov_ratio_fmt = f"{float(prov_ratio):.0%}"
    except (TypeError, ValueError):
        prov_ratio_fmt = str(prov_ratio)
    try:
        src_ratio_fmt = f"{float(src_ratio):.0%}"
    except (TypeError, ValueError):
        src_ratio_fmt = str(src_ratio)

    replay_meta_grid = (
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:10px;margin-bottom:14px;'>"
        f"<div><span class='kpi-label'>Cases</span><strong style='color:#dae2fd;'> {html.escape(str(historical_replay_summary.get('case_count', 'n/a')))}</strong></div>"
        f"<div><span class='kpi-label'>Input Records</span><strong style='color:#dae2fd;'> {html.escape(str(historical_replay_summary.get('replay_input_record_total', 'n/a')))}</strong></div>"
        f"<div><span class='kpi-label'>Archival Files</span><strong style='color:#dae2fd;'> {html.escape(str(historical_replay_summary.get('archival_data_file_count', 'n/a')))}</strong></div>"
        f"<div><span class='kpi-label'>Source Coverage</span><strong style='color:#dae2fd;'> {html.escape(src_ratio_fmt)}</strong></div>"
        f"<div><span class='kpi-label'>Provenance</span><strong style='color:#dae2fd;'> {html.escape(prov_ratio_fmt)}</strong></div>"
        "</div>"
    )

    replay_summary_panel = (
        "<div class='panel'><div class='panel-header'>Historical Replay Summary</div>"
        f"{replay_meta_grid}"
        f"<div style='margin-bottom:12px;'>{replay_verdict_bars}</div>"
        "<div class='table-container'><table><thead><tr><th>Country</th><th>Attention Cases</th><th>Highest Level</th><th>Case IDs</th></tr></thead>"
        f"<tbody>{replay_country_rows}</tbody></table></div>"
        "</div>"
    )

    # --- Replay Attention Watchlist (cards + interactive scoping controls) ---
    attention_cases = [item for item in historical_replay_summary.get('attention_cases', []) if isinstance(item, dict)]
    attention_cards = _render_attention_case_cards(attention_cases)
    attention_count_val = historical_replay_summary.get('attention_case_count', 0)
    attention_badge = (
        f"<span class='badge badge-red' style='margin-left:8px;'>{html.escape(str(attention_count_val))} flagged</span>"
        if attention_count_val and int(attention_count_val) > 0
        else f"<span class='badge badge-green' style='margin-left:8px;'>0 flagged</span>"
    )
    attention_levels = sorted({str(item.get('attention_level', '')).strip().lower() for item in attention_cases if str(item.get('attention_level', '')).strip()})
    attention_owners = sorted({str(item.get('owner_hint', '')).strip().lower() for item in attention_cases if str(item.get('owner_hint', '')).strip()})
    attention_reasons = sorted({str(item.get('attention_reason', '')).strip().lower() for item in attention_cases if str(item.get('attention_reason', '')).strip()})
    attention_verdicts = sorted({str(item.get('review_verdict', '')).strip().lower() for item in attention_cases if str(item.get('review_verdict', '')).strip()})
    attention_tiers = sorted({str(item.get('replay_evidence_tier', '')).strip().lower() for item in attention_cases if str(item.get('replay_evidence_tier', '')).strip()})
    attention_level_options = ''.join(
        f"<option value='{html.escape(level)}'>{html.escape(level)}</option>"
        for level in attention_levels
    )
    attention_owner_options = ''.join(
        f"<option value='{html.escape(owner)}'>{html.escape(owner)}</option>"
        for owner in attention_owners
    )
    attention_reason_options = ''.join(
        f"<option value='{html.escape(reason)}'>{html.escape(reason)}</option>"
        for reason in attention_reasons
    )
    attention_verdict_options = ''.join(
        f"<option value='{html.escape(verdict)}'>{html.escape(verdict)}</option>"
        for verdict in attention_verdicts
    )
    attention_tier_options = ''.join(
        f"<option value='{html.escape(tier)}'>{html.escape(tier)}</option>"
        for tier in attention_tiers
    )
    attention_filter_script = """
<style>
.replay-attention-focus-active{box-shadow:0 0 0 1px rgba(78,222,163,.45), 0 0 18px rgba(78,222,163,.12);border-left-color:#4edea3 !important;background:rgba(78,222,163,.05);}
.replay-attention-focus-panel-active{border-color:rgba(78,222,163,.35);}
</style>
<script>
(function(){
  const levelFilter=document.getElementById('replay-attention-level-filter');
  const ownerFilter=document.getElementById('replay-attention-owner-filter');
  const reasonFilter=document.getElementById('replay-attention-reason-filter');
  const verdictFilter=document.getElementById('replay-attention-verdict-filter');
  const tierFilter=document.getElementById('replay-attention-tier-filter');
  const textFilter=document.getElementById('replay-attention-text-filter');
  const resetButton=document.getElementById('replay-attention-reset');
  const copyLinkButton=document.getElementById('replay-attention-copy-link');
  const visibleCountNode=document.getElementById('replay-attention-visible-count');
  const focusTargetCountNode=document.getElementById('replay-attention-focus-target-count');
  const activeStateNode=document.getElementById('replay-attention-active-state');
  const verdictBreakdownNode=document.getElementById('replay-attention-visible-verdict-breakdown');
  const linkStatusNode=document.getElementById('replay-attention-link-status');
  const attentionPanelNode=document.getElementById('replay-attention-panel');
  const cards=Array.from(document.querySelectorAll('.replay-attention-card'));
  const hashPrefix='ra=';

  function renderReplayAttentionActiveState(level, owner, reason, verdict, tier, text){
    const fragments=[];
    if(level && level!=='all'){fragments.push(`level=${level}`);}
    if(owner && owner!=='all'){fragments.push(`owner=${owner}`);}
    if(reason && reason!=='all'){fragments.push(`reason=${reason}`);}
    if(verdict && verdict!=='all'){fragments.push(`verdict=${verdict}`);}
    if(tier && tier!=='all'){fragments.push(`tier=${tier}`);}
    if(text){fragments.push(`text=${text}`);}
    if(!fragments.length){
      return 'Active: default';
    }
    return `Active: ${fragments.join(' | ')}`;
  }

  function getReplayAttentionState(){
    return {
      level: ((levelFilter&&levelFilter.value)||'all').toLowerCase(),
      owner: ((ownerFilter&&ownerFilter.value)||'all').toLowerCase(),
      reason: ((reasonFilter&&reasonFilter.value)||'all').toLowerCase(),
      verdict: ((verdictFilter&&verdictFilter.value)||'all').toLowerCase(),
      tier: ((tierFilter&&tierFilter.value)||'all').toLowerCase(),
      text: ((textFilter&&textFilter.value)||'').trim(),
    };
  }

  function hasReplayAttentionFocus(state){
    return Boolean(
      (state.level && state.level!=='all') ||
      (state.owner && state.owner!=='all') ||
      (state.reason && state.reason!=='all') ||
      (state.verdict && state.verdict!=='all') ||
      (state.tier && state.tier!=='all') ||
      state.text
    );
  }

  function serializeReplayAttentionState(state){
    const params=new URLSearchParams();
    if(state.level && state.level!=='all'){params.set('ra_level', state.level);}
    if(state.owner && state.owner!=='all'){params.set('ra_owner', state.owner);}
    if(state.reason && state.reason!=='all'){params.set('ra_reason', state.reason);}
    if(state.verdict && state.verdict!=='all'){params.set('ra_verdict', state.verdict);}
    if(state.tier && state.tier!=='all'){params.set('ra_tier', state.tier);}
    if(state.text){params.set('ra_text', state.text);}
    return params.toString();
  }

  function persistReplayAttentionStateToHash(state){
    const encoded=serializeReplayAttentionState(state);
    const base=`${window.location.pathname}${window.location.search}`;
    if(!encoded){
      window.history.replaceState(null, '', base);
      return;
    }
    window.history.replaceState(null, '', `${base}#${hashPrefix}${encoded}`);
  }

  function applyReplayAttentionStateFromHash(){
    const rawHash=window.location.hash||'';
    if(!rawHash.startsWith(`#${hashPrefix}`)){
      return;
    }
    const params=new URLSearchParams(rawHash.slice(hashPrefix.length+1));
    const level=params.get('ra_level');
    const owner=params.get('ra_owner');
    const reason=params.get('ra_reason');
    const verdict=params.get('ra_verdict');
    const tier=params.get('ra_tier');
    const text=params.get('ra_text');
    if(levelFilter && level){levelFilter.value=level;}
    if(ownerFilter && owner){ownerFilter.value=owner;}
    if(reasonFilter && reason){reasonFilter.value=reason;}
    if(verdictFilter && verdict){verdictFilter.value=verdict;}
    if(tierFilter && tier){tierFilter.value=tier;}
    if(textFilter && text!==null){textFilter.value=text;}
  }

  function setReplayAttentionLinkStatus(message){
    if(linkStatusNode){
      linkStatusNode.textContent=message;
    }
  }

  async function copyReplayAttentionFilterLink(){
    const state=getReplayAttentionState();
    const encoded=serializeReplayAttentionState(state);
    const baseUrl=`${window.location.origin}${window.location.pathname}${window.location.search}`;
    const shareUrl=encoded ? `${baseUrl}#${hashPrefix}${encoded}` : baseUrl;
    try {
      if(!navigator.clipboard||!navigator.clipboard.writeText){
        throw new Error('clipboard API unavailable');
      }
      await navigator.clipboard.writeText(shareUrl);
      setReplayAttentionLinkStatus('Replay attention link copied.');
    } catch (error) {
      setReplayAttentionLinkStatus('Replay attention link copy failed.');
    }
  }

  function applyReplayAttentionFocusState(state, matchingCards){
    const focusActive=hasReplayAttentionFocus(state);
    cards.forEach((card)=>card.classList.remove('replay-attention-focus-active'));
    if(attentionPanelNode){attentionPanelNode.classList.toggle('replay-attention-focus-panel-active', focusActive);}
    if(focusTargetCountNode){focusTargetCountNode.textContent=String(focusActive ? matchingCards.length : 0);}
    if(!focusActive){
      return;
    }
    matchingCards.forEach((card)=>card.classList.add('replay-attention-focus-active'));
    const firstCard=matchingCards[0];
    if(firstCard && typeof firstCard.scrollIntoView==='function'){
      firstCard.scrollIntoView({behavior:'smooth', block:'center'});
    }
  }

  function applyReplayAttentionFilters(options){
    const settings=options||{};
    const persistHash=settings.persistHash!==false;
    const state=getReplayAttentionState();
    const level=state.level;
    const owner=state.owner;
    const reason=state.reason;
    const verdict=state.verdict;
    const tier=state.tier;
    const text=state.text.toLowerCase();
    let visibleCount=0;
    const verdictCounts={};
    const matchingCards=[];
    cards.forEach((card)=>{
      const cardLevel=(card.dataset.attentionLevel||'').toLowerCase();
      const cardOwner=(card.dataset.attentionOwner||'').toLowerCase();
      const cardReason=(card.dataset.attentionReason||'').toLowerCase();
      const cardVerdict=(card.dataset.reviewVerdict||'').toLowerCase();
      const cardTier=(card.dataset.replayTier||'').toLowerCase();
      const cardSearchText=(card.dataset.cardSearchText||'').toLowerCase();
      const levelMatch=(level==='all'||cardLevel===level);
      const ownerMatch=(owner==='all'||cardOwner===owner);
      const reasonMatch=(reason==='all'||cardReason===reason);
      const verdictMatch=(verdict==='all'||cardVerdict===verdict);
      const tierMatch=(tier==='all'||cardTier===tier);
      const textMatch=(!text||cardSearchText.includes(text));
      const show=(levelMatch&&ownerMatch&&reasonMatch&&verdictMatch&&tierMatch&&textMatch);
      card.style.display=show?'':'none';
      if(show){
        visibleCount+=1;
        matchingCards.push(card);
        const key=cardVerdict||'n/a';
        verdictCounts[key]=(verdictCounts[key]||0)+1;
      }
    });
    if(visibleCountNode){visibleCountNode.textContent=String(visibleCount);}
    if(activeStateNode){activeStateNode.textContent=renderReplayAttentionActiveState(level, owner, reason, verdict, tier, text);}
    if(verdictBreakdownNode){
      const breakdown=Object.keys(verdictCounts).sort().map((key)=>`${key}=${verdictCounts[key]}`).join(' | ');
      verdictBreakdownNode.textContent=breakdown || 'none';
    }
    applyReplayAttentionFocusState(state, matchingCards);
    if(persistHash){
      persistReplayAttentionStateToHash(state);
    }
  }

  function resetReplayAttentionFilters(){
    if(levelFilter){levelFilter.value='all';}
    if(ownerFilter){ownerFilter.value='all';}
    if(reasonFilter){reasonFilter.value='all';}
    if(verdictFilter){verdictFilter.value='all';}
    if(tierFilter){tierFilter.value='all';}
    if(textFilter){textFilter.value='';}
    applyReplayAttentionFilters();
  }

  if(levelFilter){levelFilter.addEventListener('change', applyReplayAttentionFilters);}
  if(ownerFilter){ownerFilter.addEventListener('change', applyReplayAttentionFilters);}
  if(reasonFilter){reasonFilter.addEventListener('change', applyReplayAttentionFilters);}
  if(verdictFilter){verdictFilter.addEventListener('change', applyReplayAttentionFilters);}
  if(tierFilter){tierFilter.addEventListener('change', applyReplayAttentionFilters);}
  if(textFilter){textFilter.addEventListener('input', applyReplayAttentionFilters);}
  if(resetButton){resetButton.addEventListener('click', resetReplayAttentionFilters);}
  if(copyLinkButton){copyLinkButton.addEventListener('click', copyReplayAttentionFilterLink);}
  applyReplayAttentionStateFromHash();
  applyReplayAttentionFilters({persistHash:false});
})();
</script>
"""
    attention_panel = (
        f"<div class='panel' id='replay-attention-panel'><div class='panel-header'>Replay Attention Watchlist {attention_badge}</div>"
        "<div class='controls-bar'>"
        "<label for='replay-attention-level-filter'>Level</label>"
        f"<select id='replay-attention-level-filter'><option value='all'>All levels</option>{attention_level_options}</select>"
        "<label for='replay-attention-owner-filter'>Owner</label>"
        f"<select id='replay-attention-owner-filter'><option value='all'>All owners</option>{attention_owner_options}</select>"
        "<label for='replay-attention-reason-filter'>Reason</label>"
        f"<select id='replay-attention-reason-filter'><option value='all'>All reasons</option>{attention_reason_options}</select>"
        "<label for='replay-attention-verdict-filter'>Verdict</label>"
        f"<select id='replay-attention-verdict-filter'><option value='all'>All verdicts</option>{attention_verdict_options}</select>"
        "<label for='replay-attention-tier-filter'>Evidence tier</label>"
        f"<select id='replay-attention-tier-filter'><option value='all'>All tiers</option>{attention_tier_options}</select>"
        "<label for='replay-attention-text-filter'>Search</label>"
        "<input id='replay-attention-text-filter' type='text' placeholder='country, case, action...'/>"
        "<button id='replay-attention-reset' type='button'>Reset</button>"
        "<button id='replay-attention-copy-link' type='button'>Copy Link</button>"
        "</div>"
        "<p style='font-size:11px;color:#6b7d99;margin-bottom:10px;font-family:Space Grotesk,monospace;'>"
        "Visible attention cases: <strong id='replay-attention-visible-count'>0</strong> | "
        "Focus targets: <strong id='replay-attention-focus-target-count'>0</strong> | "
        "<span id='replay-attention-active-state'>Active: default</span> | "
        "Visible verdict mix: <span id='replay-attention-visible-verdict-breakdown'>none</span> | "
        "Link status: <span id='replay-attention-link-status'>ready</span>"
        "</p>"
        f"{attention_cards}"
        f"{attention_filter_script}"
        "</div>"
    )

    # --- Historical Replay Reviews (detail table, collapsible) ---
    historical_replay_countries = sorted({str(review.get('country_id', 'n/a')) for review in historical_replay_reviews})
    historical_replay_verdicts = sorted({str(review.get('review_verdict', 'n/a')) for review in historical_replay_reviews})
    historical_replay_bases = sorted({str(review.get('review_basis', 'n/a')) for review in historical_replay_reviews})
    historical_replay_country_options = ''.join(
        f"<option value='{html.escape(country.lower())}'>{html.escape(country)}</option>"
        for country in historical_replay_countries
    ) or "<option value='all'>All countries</option>"
    historical_replay_verdict_options = ''.join(
        f"<option value='{html.escape(verdict.lower())}'>{html.escape(verdict)}</option>"
        for verdict in historical_replay_verdicts
    ) or "<option value='all'>All verdicts</option>"
    historical_replay_basis_options = ''.join(
        f"<option value='{html.escape(basis.lower())}'>{html.escape(basis)}</option>"
        for basis in historical_replay_bases
    ) or "<option value='all'>All bases</option>"
    hist_replay_rows_enhanced = ''.join(
        "<tr class='historical-replay-row'"
        f" data-country='{html.escape(str(review.get('country_id', 'n/a')).lower())}'"
        f" data-verdict='{html.escape(str(review.get('review_verdict', 'n/a')).lower())}'"
        f" data-basis='{html.escape(str(review.get('review_basis', 'n/a')).lower())}'"
        f" data-search-text='{html.escape(' '.join(str(value) for value in [review.get('country_id', 'n/a'), review.get('case_id', 'n/a'), review.get('review_verdict', 'n/a'), review.get('review_basis', 'n/a'), review.get('replay_evidence_tier', 'n/a'), review.get('expected_status', 'n/a'), review.get('replayed_status', 'n/a'), ', '.join(str(item) for item in review.get('archival_data_files', []))]).lower())}'>"
        f"<td>{html.escape(str(review.get('country_id', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:11px;'>{html.escape(str(review.get('case_id', 'n/a')))}</td>"
        f"<td>{_verdict_badge(str(review.get('review_verdict', 'n/a')))}</td>"
        f"<td><span class='badge badge-gray'>{html.escape(str(review.get('review_basis', 'n/a')))}</span></td>"
        f"<td>{_evidence_tier_badge(str(review.get('replay_evidence_tier', 'n/a')))}</td>"
        f"<td style='color:#dae2fd;'>{html.escape(str(review.get('replay_evidence_score', 'n/a')))}</td>"
        f"<td><span class='badge badge-gray'>{html.escape(str(review.get('expected_status', 'n/a')))}</span></td>"
        f"<td><span class='badge badge-blue'>{html.escape(str(review.get('replayed_status', 'n/a')))}</span></td>"
        f"<td style='color:#8b9ab8;'>{html.escape(str(review.get('domain_match_ratio', 'n/a')))}</td>"
        f"<td style='color:#6b7d99;font-size:11px;'>{html.escape(str(review.get('replay_input_record_count', 'n/a')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#4b5778;'>{html.escape(', '.join(str(f) for f in review.get('archival_data_files', [])))}</td>"
        "</tr>"
        for review in historical_replay_reviews
    ) or "<tr><td colspan='11' style='color:#6b7d99;'>No historical replay reviews recorded.</td></tr>"
    replay_detail_panel = (
        "<details><summary>Historical Replay Reviews (Detail) "
        f"<span class='badge badge-gray' style='margin-left:8px;'>{len(historical_replay_reviews)}</span>"
        f"<span id='historical-replay-visible-count' class='badge badge-blue' style='margin-left:8px;'>Visible: {len(historical_replay_reviews)} / {len(historical_replay_reviews)}</span></summary>"
        "<div style='padding:12px 0;'>"
        "<div class='controls-bar' style='flex-wrap:wrap;gap:10px 12px;margin-bottom:12px;'>"
        f"<label style='display:flex;flex-direction:column;gap:4px;'>Country<select id='historical-replay-country-filter' onchange='applyHistoricalReplayFilters()'><option value='all'>All countries</option>{historical_replay_country_options}</select></label>"
        f"<label style='display:flex;flex-direction:column;gap:4px;'>Verdict<select id='historical-replay-verdict-filter' onchange='applyHistoricalReplayFilters()'><option value='all'>All verdicts</option>{historical_replay_verdict_options}</select></label>"
        f"<label style='display:flex;flex-direction:column;gap:4px;'>Basis<select id='historical-replay-basis-filter' onchange='applyHistoricalReplayFilters()'><option value='all'>All bases</option>{historical_replay_basis_options}</select></label>"
        "<label style='display:flex;flex-direction:column;gap:4px;min-width:240px;'>Search<input id='historical-replay-text-filter' type='search' placeholder='Case, status, source or file...' oninput='applyHistoricalReplayFilters()' style='padding:8px 10px;border-radius:6px;border:1px solid #2d3b57;background:#0f1520;color:#e8eefc;'></label>"
        "<button id='historical-replay-reset' type='button' onclick='resetHistoricalReplayFilters()' style='align-self:flex-end;'>Reset</button>"
        "<span id='historical-replay-active-state' class='badge badge-gray' style='align-self:flex-end;'>Active: default</span>"
        "<span id='historical-replay-visible-verdict-breakdown' class='badge badge-gray' style='align-self:flex-end;'>No visible replay reviews.</span>"
        "</div>"
        "<div class='table-container'><table><thead><tr>"
        "<th>Country</th><th>Case ID</th><th>Verdict</th><th>Basis</th><th>Evidence Tier</th>"
        "<th>Score</th><th>Expected Status</th><th>Replayed Status</th><th>Domain Match</th><th>Records</th><th>Archival Files</th>"
        "</tr></thead>"
        f"<tbody>{hist_replay_rows_enhanced}</tbody></table></div>"
        "<script>"
        "(function() {"
        "function historicalReplayRows() { return Array.from(document.querySelectorAll('.historical-replay-row')); }"
        "function valueOrAll(elementId) { var element = document.getElementById(elementId); return element ? String(element.value || 'all').toLowerCase() : 'all'; }"
        "function textOrEmpty(elementId) { var element = document.getElementById(elementId); return element ? String(element.value || '').trim().toLowerCase() : ''; }"
        "function renderHistoricalReplayActiveState(country, verdict, basis, text) {"
        "  var parts = [];"
        "  if (country && country !== 'all') { parts.push('country=' + country.toUpperCase()); }"
        "  if (verdict && verdict !== 'all') { parts.push('verdict=' + verdict); }"
        "  if (basis && basis !== 'all') { parts.push('basis=' + basis); }"
        "  if (text) { parts.push('text=' + text); }"
        "  var badge = document.getElementById('historical-replay-active-state');"
        "  if (badge) { badge.textContent = 'Active: ' + (parts.length ? parts.join(', ') : 'default'); }"
        "}"
        "function applyHistoricalReplayFilters() {"
        "  var country = valueOrAll('historical-replay-country-filter');"
        "  var verdict = valueOrAll('historical-replay-verdict-filter');"
        "  var basis = valueOrAll('historical-replay-basis-filter');"
        "  var text = textOrEmpty('historical-replay-text-filter');"
        "  var visible = 0;"
        "  var verdictCounts = {};"
        "  historicalReplayRows().forEach(function(row) {"
        "    var rowCountry = String(row.dataset.country || 'n/a');"
        "    var rowVerdict = String(row.dataset.verdict || 'n/a');"
        "    var rowBasis = String(row.dataset.basis || 'n/a');"
        "    var rowText = String(row.dataset.searchText || '');"
        "    var match = (country === 'all' || rowCountry === country) && (verdict === 'all' || rowVerdict === verdict) && (basis === 'all' || rowBasis === basis) && (!text || rowText.indexOf(text) !== -1);"
        "    row.style.display = match ? '' : 'none';"
        "    if (match) {"
        "      visible += 1;"
        "      verdictCounts[rowVerdict] = (verdictCounts[rowVerdict] || 0) + 1;"
        "    }"
        "  });"
        "  var countBadge = document.getElementById('historical-replay-visible-count');"
        "  if (countBadge) { countBadge.textContent = 'Visible: ' + visible + ' / ' + historicalReplayRows().length; }"
        "  var breakdown = document.getElementById('historical-replay-visible-verdict-breakdown');"
        "  if (breakdown) {"
        "    var verdictKeys = Object.keys(verdictCounts).sort();"
        "    breakdown.textContent = verdictKeys.length ? verdictKeys.map(function(key) { return key + ': ' + verdictCounts[key]; }).join(' | ') : 'No visible replay reviews.';"
        "  }"
        "  renderHistoricalReplayActiveState(country, verdict, basis, text);"
        "}"
        "function resetHistoricalReplayFilters() {"
        "  var country = document.getElementById('historical-replay-country-filter'); if (country) { country.value = 'all'; }"
        "  var verdict = document.getElementById('historical-replay-verdict-filter'); if (verdict) { verdict.value = 'all'; }"
        "  var basis = document.getElementById('historical-replay-basis-filter'); if (basis) { basis.value = 'all'; }"
        "  var text = document.getElementById('historical-replay-text-filter'); if (text) { text.value = ''; }"
        "  applyHistoricalReplayFilters();"
        "}"
        "window.applyHistoricalReplayFilters = applyHistoricalReplayFilters;"
        "window.resetHistoricalReplayFilters = resetHistoricalReplayFilters;"
        "if (document.readyState === 'loading') { document.addEventListener('DOMContentLoaded', applyHistoricalReplayFilters); } else { applyHistoricalReplayFilters(); }"
        "})();"
        "</script>"
        "</div></details>"
    )

    # --- Reprocessing (collapsible) ---
    changed_versions_html = ''.join(f"<li>{html.escape(str(item))}</li>" for item in reprocessing.get('changed_versions', [])) or "<li>none</li>"
    reprocessing_panel = (
        "<details><summary>Reprocessing Comparison</summary>"
        "<div style='padding:12px 0;'>"
        f"<h4>Changed Versions</h4><ul>{changed_versions_html}</ul>"
        f"{_json_block(reprocessing)}"
        "</div></details>"
    )

    body = (
        kpi_grid
        + case_meta
        + domain_panel
        + goal_panel
        + portfolio_panel
        + realism_panel
        + ref_lib_panel
        + hist_ref_panel
        + replay_summary_panel
        + attention_panel
        + replay_detail_panel
        + reprocessing_panel
    )
    return _page("Validation / Backtest", body, nav_prefix=nav_prefix, available_pages=available_pages)


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
    dependency_rows = _traceability_dependency_rows(lineage_records)
    origin_rows = _traceability_origin_rows(lineage_records)

    # --- KPI summary ---
    total_records = len(lineage_records)
    unique_sources = len(set(str(r.get('source_id', '')) for r in lineage_records if r.get('source_id')))
    unique_features = len(set(str(r.get('feature_id', '')) for r in lineage_records if r.get('feature_id')))
    unique_snapshots = len(set(str(r.get('snapshot_id', '')) for r in lineage_records if r.get('snapshot_id')))
    reports_count = len(set(str(r.get('report_id', '')) for r in lineage_records if r.get('report_id')))

    kpi_grid = (
        "<div class='kpi-grid'>"
        f"<div class='kpi-card'><span class='kpi-label'>Lineage Records</span><div class='kpi-value'>{total_records}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Sources</span><div class='kpi-value'>{unique_sources}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Features</span><div class='kpi-value'>{unique_features}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Snapshots</span><div class='kpi-value'>{unique_snapshots}</div></div>"
        f"<div class='kpi-card'><span class='kpi-label'>Reports</span><div class='kpi-value'>{reports_count}</div></div>"
        "</div>"
    )

    # --- Lineage pipeline visualization ---
    pipeline_html = (
        "<div class='panel'><div class='panel-header'>Data Pipeline Flow</div>"
        "<div style='display:flex;align-items:center;gap:0;flex-wrap:wrap;padding:12px 0;'>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(78,222,163,.25);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#4edea3;'>Source</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(142,208,255,.2);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#8ed0ff;'>Raw Record</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(142,208,255,.2);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#8ed0ff;'>Normalized</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(227,179,65,.2);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#e3b341;'>Feature</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(227,179,65,.2);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#e3b341;'>Domain Status</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(78,222,163,.15);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#6b9b7a;'>Multi-Domain</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(107,125,153,.25);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#8b9ab8;'>Snapshot</div>"
        "<div style='padding:0 8px;color:#4b5778;font-size:1.2rem;'>→</div>"
        "<div style='padding:8px 16px;background:#0f1828;border:1px solid rgba(107,125,153,.2);border-radius:2px;font-family:\"Space Grotesk\",monospace;font-size:0.75rem;color:#6b7d99;'>Report</div>"
        "</div></div>"
    )

    # --- Source-Origin panel — use origin_rows data enriched with observed_at ---
    # Build origin table directly (uses _traceability_origin_rows which has First Observed)
    origin_panel = (
        "<div class='panel'><div class='panel-header'>Source-Origin Groundwork</div>"
        "<p style='color:#6b7d99;font-size:11px;margin-bottom:12px;'>What the current lineage artifact can support. "
        "Origin inference from artifact-window observed timestamps with explicit uncertainty labels.</p>"
        "<div class='table-container'><table><thead><tr>"
        "<th>Source</th><th>Raw Records</th><th>Features</th><th>Reports</th>"
        "<th>First Observed (window)</th><th>Origin Inference Status</th><th>Origin Uncertainty</th>"
        "</tr></thead>"
        f"<tbody>{origin_rows}</tbody></table></div>"
        "</div>"
    )

    # --- Dependency cluster panel ---
    dependency_panel = (
        "<div class='panel'><div class='panel-header'>Source Dependency — Cluster Candidates</div>"
        "<p style='color:#6b7d99;font-size:11px;margin-bottom:12px;'>"
        "Features and domain statuses produced by multiple sources simultaneously — potential replication or shared dependency candidates.</p>"
        "<div class='table-container'><table><thead><tr>"
        "<th>Feature</th><th>Domain Status</th><th>Snapshot</th><th>Sources</th><th>Reports</th><th>Coupling Signal</th><th>Observed Lag (min)</th>"
        "</tr></thead>"
        f"<tbody>{dependency_rows}</tbody></table></div>"
        "</div>"
    )

    # --- Full lineage table (collapsible) ---
    lineage_rows = ''.join(
        "<tr>"
        f"<td class='mono' style='font-size:11px;color:#4edea3;'>{html.escape(str(record.get('source_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#8ed0ff;'>{html.escape(str(record.get('raw_record_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#8b9ab8;'>{html.escape(str(record.get('normalized_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#e3b341;'>{html.escape(str(record.get('feature_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#e3b341;'>{html.escape(str(record.get('domain_status_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#6b9b7a;'>{html.escape(str(record.get('multi_domain_status_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#8b9ab8;'>{html.escape(str(record.get('snapshot_id', '')))}</td>"
        f"<td class='mono' style='font-size:10px;color:#6b7d99;'>{html.escape(str(record.get('report_id', '')))}</td>"
        "</tr>"
        for record in lineage_records
    ) or "<tr><td colspan='8' style='color:#6b7d99;'>No lineage records.</td></tr>"
    lineage_detail_panel = (
        f"<details><summary>Full Lineage Records <span class='badge badge-gray' style='margin-left:8px;'>{total_records}</span></summary>"
        "<div style='padding:12px 0;'>"
        "<div class='table-container'><table><thead><tr>"
        "<th>Source</th><th>Raw</th><th>Normalized</th><th>Feature</th><th>Domain Status</th><th>Multi-Domain</th><th>Snapshot</th><th>Report</th>"
        "</tr></thead>"
        f"<tbody>{lineage_rows}</tbody></table></div>"
        "</div></details>"
    )

    body = kpi_grid + pipeline_html + origin_panel + dependency_panel + lineage_detail_panel
    return _page("Traceability / Lineage", body, nav_prefix=nav_prefix, available_pages=available_pages)


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
function renderReplayAttentionPrefillSummary(context, validation){
  const summaryElement = document.getElementById('replay-attention-prefill-summary');
  if (!summaryElement) { return; }
  const hasReplayContext = Boolean(context && (context.caseId || context.countryId || context.attentionReason || context.ownerHint || context.suggestedNextAction || context.attentionLevel || context.replayEvidenceTier || context.reviewVerdict));
  if (!hasReplayContext) {
    summaryElement.textContent = 'No replay-attention query parameters detected.';
    return;
  }
  const lines = [
    'Replay-attention prefill summary',
    `Linked item: ${context.linkedItem || 'n/a'}`,
    `Scope: ${context.scope || 'n/a'}`,
    `Annotation type: ${context.annotationType || 'n/a'}`,
    `Country: ${context.countryId || 'n/a'}`,
    `Case: ${context.caseId || 'n/a'}`,
    `Reason: ${context.attentionReason || 'n/a'}`,
    `Owner hint: ${context.ownerHint || 'n/a'}`,
    `Suggested next action: ${context.suggestedNextAction || 'n/a'}`,
    `Attention level: ${context.attentionLevel || 'n/a'}`,
    `Replay evidence tier: ${context.replayEvidenceTier || 'n/a'}`,
    `Review verdict: ${context.reviewVerdict || 'n/a'}`,
    `Replay evidence score: ${context.replayEvidenceScore || 'n/a'}`,
    `Domain match ratio: ${context.domainMatchRatio || 'n/a'}`,
    `Missing expected domains: ${context.missingExpectedDomains || 'n/a'}`,
    `Unexpected observed domains: ${context.unexpectedObservedDomains || 'n/a'}`,
  ];
  if (validation && validation.hasReplayContext) {
    if (validation.missing.length) {
      lines.push(`Integrity check: missing ${validation.missing.join(', ')}`);
    } else {
      lines.push('Integrity check: complete');
    }
  }
  summaryElement.textContent = lines.join('\n');
}
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
function collectReplayAttentionPrefillContextFromQuery(){
  const params = new URLSearchParams(window.location.search);
  return {
    linkedItem: params.get('linked_item') || '',
    scope: params.get('scope') || '',
    annotationType: params.get('annotation_type') || '',
    countryId: (params.get('country_id') || '').trim(),
    caseId: (params.get('case_id') || '').trim(),
    attentionReason: (params.get('attention_reason') || '').trim(),
    ownerHint: (params.get('owner_hint') || '').trim(),
    suggestedNextAction: (params.get('suggested_next_action') || '').trim(),
    attentionLevel: (params.get('attention_level') || '').trim().toLowerCase(),
    replayEvidenceTier: (params.get('replay_evidence_tier') || '').trim().toLowerCase(),
    reviewVerdict: (params.get('review_verdict') || '').trim().toLowerCase(),
    replayEvidenceScore: (params.get('replay_evidence_score') || '').trim(),
    domainMatchRatio: (params.get('domain_match_ratio') || '').trim(),
    missingExpectedDomains: (params.get('missing_expected_domains') || '').trim(),
    unexpectedObservedDomains: (params.get('unexpected_observed_domains') || '').trim(),
  };
}
function validateReplayAttentionPrefillContext(context){
  const hasReplayContext = Boolean(context.caseId || context.countryId || context.attentionReason || context.ownerHint || context.suggestedNextAction || context.attentionLevel || context.replayEvidenceTier || context.reviewVerdict);
  if (!hasReplayContext) { return { hasReplayContext: false, missing: [] }; }
  const required = ['countryId', 'caseId', 'attentionReason', 'ownerHint', 'suggestedNextAction', 'attentionLevel', 'replayEvidenceTier', 'reviewVerdict'];
  const missing = required.filter((key) => !String(context[key] || '').trim());
  return { hasReplayContext: true, missing: missing };
}
function prefillAnnotationFromQuery(){
  const context = collectReplayAttentionPrefillContextFromQuery();
  const linkedItem = context.linkedItem;
  const scope = context.scope;
  const annotationType = context.annotationType;
  const countryId = context.countryId;
  const caseId = context.caseId;
  const attentionReason = context.attentionReason;
  const ownerHint = context.ownerHint;
  const suggestedNextAction = context.suggestedNextAction;
  const attentionLevel = context.attentionLevel;
  const replayEvidenceTier = context.replayEvidenceTier;
  const reviewVerdict = context.reviewVerdict;
  const replayEvidenceScore = context.replayEvidenceScore;
  const domainMatchRatio = context.domainMatchRatio;
  const missingExpectedDomains = context.missingExpectedDomains;
  const unexpectedObservedDomains = context.unexpectedObservedDomains;
  if (scope) { document.getElementById('annotation-scope-input').value = scope; }
  if (annotationType) { document.getElementById('annotation-type-input').value = annotationType; }
  const linkedItems = [];
  if (linkedItem) { linkedItems.push(linkedItem); }
  if (countryId) { linkedItems.push(countryId); }
  if (caseId && !linkedItems.includes(caseId)) { linkedItems.push(caseId); }
  if (linkedItems.length) {
    document.getElementById('annotation-linked-items-input').value = linkedItems.join(', ');
  }
  const severityByAttentionLevel = { high: 'relevant', medium: 'uncertain', low: 'not_security_relevant' };
  if (attentionLevel && severityByAttentionLevel[attentionLevel]) {
    document.getElementById('annotation-severity-input').value = severityByAttentionLevel[attentionLevel];
  }
  const confidenceByReplayTier = { verified_replay_evidence: 'high', strong_replay_evidence: 'medium', weak_replay_evidence: 'low' };
  if (replayEvidenceTier && confidenceByReplayTier[replayEvidenceTier]) {
    document.getElementById('annotation-confidence-input').value = confidenceByReplayTier[replayEvidenceTier];
  }
  const reviewStatusByVerdict = {
    pass: 'reviewed',
    warning: 'draft',
    fail: 'rejected',
    insufficient_data: 'unreviewed',
  };
  if (reviewVerdict && reviewStatusByVerdict[reviewVerdict]) {
    document.getElementById('annotation-review-status-input').value = reviewStatusByVerdict[reviewVerdict];
  }
  const tagParts = ['replay_attention'];
  if (attentionReason) { tagParts.push(attentionReason); }
  if (replayEvidenceTier) { tagParts.push(replayEvidenceTier); }
  if (reviewVerdict) { tagParts.push(reviewVerdict); }
  if (missingExpectedDomains) {
    missingExpectedDomains.split(',').map((value) => value.trim()).filter(Boolean).forEach((domain) => tagParts.push(`missing_${domain.toLowerCase()}`));
  }
  if (unexpectedObservedDomains) {
    unexpectedObservedDomains.split(',').map((value) => value.trim()).filter(Boolean).forEach((domain) => tagParts.push(`unexpected_${domain.toLowerCase()}`));
  }
  if (ownerHint) { tagParts.push(ownerHint.replace(/\\s+/g, '_').toLowerCase()); }
  document.getElementById('annotation-tags-input').value = tagParts.join(', ');
  if (countryId || caseId || attentionReason || ownerHint || suggestedNextAction) {
    const evidenceParts = [];
    if (replayEvidenceTier) { evidenceParts.push(`tier=${replayEvidenceTier}`); }
    if (replayEvidenceScore) { evidenceParts.push(`score=${replayEvidenceScore}`); }
    if (domainMatchRatio) { evidenceParts.push(`domain_match_ratio=${domainMatchRatio}`); }
    if (missingExpectedDomains) { evidenceParts.push(`missing_expected_domains=${missingExpectedDomains}`); }
    if (unexpectedObservedDomains) { evidenceParts.push(`unexpected_observed_domains=${unexpectedObservedDomains}`); }
    const evidenceSummary = evidenceParts.length ? ` Replay evidence: ${evidenceParts.join(', ')}.` : '';
    const summary = [
      `Replay attention follow-up for ${caseId || 'case n/a'} (${countryId || 'country n/a'}).`,
      `Reason: ${attentionReason || 'n/a'}.`,
      `Owner: ${ownerHint || 'n/a'}.`,
      `Suggested next action: ${suggestedNextAction || 'n/a'}.`,
    ].join(' ') + evidenceSummary;
    document.getElementById('annotation-text-input').value = summary;
  }
  const replayContextValidation = validateReplayAttentionPrefillContext(context);
  renderReplayAttentionPrefillSummary(context, replayContextValidation);
  if (replayContextValidation.hasReplayContext && replayContextValidation.missing.length) {
    setWorkflowStatus(`Replay-attention prefill missing fields: ${replayContextValidation.missing.join(', ')}.`);
  }
  if (linkedItems.length) {
    setWorkflowStatus(`Prefilled workflow for ${linkedItems.join(', ')}.`);
    if (replayContextValidation.hasReplayContext && replayContextValidation.missing.length === 0) {
      setWorkflowStatus(`Prefilled replay-attention workflow for ${caseId || 'case n/a'} (${countryId || 'country n/a'}).`);
    }
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
    modal_html = """<div id="annotation-modal" role="dialog" aria-modal="true" aria-labelledby="modal-title"
     style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.7);z-index:1000;align-items:center;justify-content:center;">
  <div style="background:#161b22;border:1px solid rgba(78,222,163,.2);border-radius:6px;padding:24px;max-width:560px;width:90%;max-height:80vh;overflow-y:auto;">
    <h3 id="modal-title" style="color:#e6edf3;margin:0 0 16px;">Annotation</h3>
    <form id="annotation-form" onsubmit="saveAnnotation(event)">
      <input type="hidden" id="annotation-id" />
      <div style="margin-bottom:12px;">
        <label style="color:#8b949e;font-size:11px;display:block;margin-bottom:4px;">Country ID</label>
        <input id="ann-country" type="text" placeholder="e.g. UKR" maxlength="3"
          style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:6px 8px;font-size:13px;box-sizing:border-box;"
          aria-label="Country ID" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="color:#8b949e;font-size:11px;display:block;margin-bottom:4px;">Domain (optional)</label>
        <select id="ann-domain"
          style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:6px 8px;font-size:13px;">
          <option value="">&#8212; All Domains &#8212;</option>
          <option value="A">Domain A (Information Space)</option>
          <option value="B">Domain B (Activity / Events)</option>
          <option value="C">Domain C (Networks)</option>
          <option value="D">Domain D (Economic)</option>
          <option value="E">Domain E (Governance)</option>
        </select>
      </div>
      <div style="margin-bottom:12px;">
        <label style="color:#8b949e;font-size:11px;display:block;margin-bottom:4px;">Run ID (optional)</label>
        <input id="ann-run-id" type="text" placeholder="e.g. RUN-LIVE-20260520-2021"
          style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:6px 8px;font-size:13px;box-sizing:border-box;"
          aria-label="Run ID" />
      </div>
      <div style="margin-bottom:12px;">
        <label style="color:#8b949e;font-size:11px;display:block;margin-bottom:4px;">Note *</label>
        <textarea id="ann-note" rows="4" required placeholder="Enter analyst note..."
          style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:6px 8px;font-size:13px;resize:vertical;box-sizing:border-box;"
          aria-label="Note" ></textarea>
      </div>
      <div style="margin-bottom:12px;">
        <label style="color:#8b949e;font-size:11px;display:block;margin-bottom:4px;">Author</label>
        <input id="ann-author" type="text" placeholder="Analyst name"
          style="width:100%;background:#0d1117;color:#e6edf3;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:6px 8px;font-size:13px;box-sizing:border-box;"
          aria-label="Author" />
      </div>
      <div style="display:flex;gap:8px;justify-content:flex-end;">
        <button type="button" onclick="closeAnnotationModal()"
          style="background:transparent;color:#8b949e;border:1px solid rgba(139,148,158,.3);border-radius:4px;padding:6px 14px;cursor:pointer;font-size:12px;"
          aria-label="Cancel">Cancel</button>
        <button type="submit" class="btn-primary" aria-label="Save annotation">Save</button>
      </div>
    </form>
    <div id="modal-delete-zone" style="margin-top:12px;display:none;border-top:1px solid rgba(255,0,0,.2);padding-top:12px;">
      <button type="button" onclick="deleteAnnotation()"
        style="background:rgba(255,0,0,.1);color:#f85149;border:1px solid rgba(248,81,73,.3);border-radius:4px;padding:6px 14px;cursor:pointer;font-size:12px;"
        aria-label="Delete annotation">Delete Annotation</button>
    </div>
  </div>
</div>"""
    new_annotation_script = """
var SIASA_ANN_KEY = 'siasa_annotations';
function _getAnnotations() {
  try { return JSON.parse(localStorage.getItem(SIASA_ANN_KEY) || '[]'); } catch(e) { return []; }
}
function _saveAnnotations(arr) {
  localStorage.setItem(SIASA_ANN_KEY, JSON.stringify(arr));
}
function openAnnotationModal(id) {
  var modal = document.getElementById('annotation-modal');
  modal.style.display = 'flex';
  document.getElementById('modal-delete-zone').style.display = 'none';
  if (id) {
    var anns = _getAnnotations();
    var ann = anns.filter(function(a){ return a.id === id; })[0];
    if (ann) {
      document.getElementById('annotation-id').value = ann.id || '';
      document.getElementById('ann-country').value = ann.country_id || '';
      document.getElementById('ann-domain').value = ann.domain || '';
      document.getElementById('ann-run-id').value = ann.run_id || '';
      document.getElementById('ann-note').value = ann.note || '';
      document.getElementById('ann-author').value = ann.author || '';
      document.getElementById('modal-delete-zone').style.display = 'block';
      document.getElementById('modal-title').textContent = 'Edit Annotation';
    }
  } else {
    document.getElementById('annotation-form').reset();
    document.getElementById('annotation-id').value = '';
    document.getElementById('modal-title').textContent = 'New Annotation';
  }
  document.getElementById('ann-country').focus();
}
function closeAnnotationModal() {
  document.getElementById('annotation-modal').style.display = 'none';
}
function saveAnnotation(e) {
  e.preventDefault();
  var id = document.getElementById('annotation-id').value || ('ANN-' + Date.now());
  var anns = _getAnnotations();
  var existing = anns.findIndex(function(a){ return a.id === id; });
  var ann = {
    id: id,
    country_id: document.getElementById('ann-country').value.trim().toUpperCase(),
    domain: document.getElementById('ann-domain').value || null,
    run_id: document.getElementById('ann-run-id').value.trim() || null,
    note: document.getElementById('ann-note').value.trim(),
    author: document.getElementById('ann-author').value.trim() || 'Analyst',
    created_at: existing >= 0 ? anns[existing].created_at : new Date().toISOString(),
    updated_at: new Date().toISOString()
  };
  if (existing >= 0) { anns[existing] = ann; } else { anns.unshift(ann); }
  _saveAnnotations(anns);
  closeAnnotationModal();
  renderAnnotationList();
}
function deleteAnnotation() {
  var id = document.getElementById('annotation-id').value;
  if (!id) return;
  if (!confirm('Delete this annotation?')) return;
  var anns = _getAnnotations().filter(function(a){ return a.id !== id; });
  _saveAnnotations(anns);
  closeAnnotationModal();
  renderAnnotationList();
}
function renderAnnotationList() {
  var anns = _getAnnotations();
  var container = document.getElementById('annotation-list-container');
  if (!container) return;
  if (anns.length === 0) {
    container.innerHTML = '<p style="color:#8b949e;">No annotations yet. Click &quot;+ New Annotation&quot; to add one.</p>';
    return;
  }
  var html = '';
  anns.forEach(function(a) {
    html += '<div class="panel" style="margin-bottom:8px;border-left:3px solid #388bfd;">';
    html += '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">';
    html += '<span style="color:#388bfd;font-size:11px;font-weight:600;">' + (a.country_id || '\\u2014') + (a.domain ? ' / Domain ' + a.domain : '') + '</span>';
    html += '<button onclick="openAnnotationModal(\\'' + a.id + '\\')" style="background:transparent;color:#8b949e;border:1px solid rgba(139,148,158,.2);border-radius:3px;padding:2px 8px;cursor:pointer;font-size:11px;">Edit</button>';
    html += '</div>';
    html += '<p style="color:#e6edf3;margin:0 0 6px;font-size:13px;">' + (a.note || '') + '</p>';
    html += '<div style="color:#8b949e;font-size:10px;">' + (a.author || '') + ' \\u00b7 ' + (a.updated_at || '') + (a.run_id ? ' \\u00b7 ' + a.run_id : '') + '</div>';
    html += '</div>';
  });
  container.innerHTML = html;
}
document.addEventListener('DOMContentLoaded', renderAnnotationList);
document.getElementById('annotation-modal').addEventListener('click', function(e) {
  if (e.target === this) closeAnnotationModal();
});
"""
    body = ''.join(
        [
            "<h2>Analyst Annotations View</h2>",
            "<button onclick=\"openAnnotationModal()\" class=\"btn-primary\" aria-label=\"New annotation\">+ New Annotation</button>",
            f"<p>Total annotations: <strong>{html.escape(str(len(annotations_view_model.get('annotations', []))))}</strong></p>",
            "<h3>&#8212;&#8212; localStorage Annotations (live) &#8212;&#8212;</h3>",
            "<div id='annotation-list-container'><p style='color:#8b949e;'>Loading localStorage annotations...</p></div>",
            "<h3>Create / Edit Annotation Workflow</h3>",
            "<p>This static GUI keeps analyst draft annotations in the browser for create/edit/filter/history workflow support. Export the draft JSON for governed persistence into repo-backed artifacts.</p>",
            "<div id='annotation-workflow-status'></div>",
            "<h4>Replay-attention Prefill Summary</h4>",
            "<pre id='replay-attention-prefill-summary' style='white-space:pre-wrap;background:#0d1117;border:1px solid rgba(78,222,163,.2);border-radius:4px;padding:10px;color:#c9d1d9;'>No replay-attention query parameters detected.</pre>",
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
            "<h3>&#8212;&#8212; Artifact Annotations (from last run) &#8212;&#8212;</h3>",
            f"<h3>Annotation Details</h3>{_annotation_details_html([str(item.get('annotation_id')) for item in annotations_view_model.get('annotations', [])], annotations_view_model)}",
            "<h3>By Scope</h3>",
            "<table><thead><tr><th>Scope</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{scope_rows}</tbody></table>",
            "<h3>By Linked Item</h3>",
            "<table><thead><tr><th>Linked Item</th><th>Annotation IDs</th></tr></thead>",
            f"<tbody>{linked_item_rows}</tbody></table>",
            modal_html,
            f"<script id='annotation-seed-data' type='application/json'>{workflow_seed}</script>",
            workflow_script,
            f"<script>{new_annotation_script}</script>",
        ]
    )
    return _page("Analyst Annotations View", body, nav_prefix=nav_prefix, available_pages=available_pages)

def _normalize_ui_role(ui_role: str) -> str:
    normalized = ui_role.strip().lower()
    if normalized not in _UI_ROLES:
        raise ValueError(f"Unsupported ui_role '{ui_role}'. Expected one of: {', '.join(sorted(_UI_ROLES))}")
    return normalized


def _render_analytics(
    analytics_view_model: dict[str, Any],
    *,
    nav_prefix: str = '',
    available_pages: set[str] | None = None,
) -> str:
    """Render the Advanced Analytics page showing Phase 4-6 module outputs.

    Sections: Cross-Domain Fusion | Bayesian Estimates | Uncertainty Budgets |
    Rule Evaluations | Dependency Graph | Provenance Chain | Info Epidemiology.
    Requirement trace: AP-F22..F27, AP-INT-01..03.
    """
    fusion = analytics_view_model.get('cross_domain_fusion', {})
    bayesian = analytics_view_model.get('bayesian_estimates', {})
    uncertainty = analytics_view_model.get('uncertainty_budgets', {})
    rules = analytics_view_model.get('rule_evaluations', [])
    dep_graph = analytics_view_model.get('dependency_graph', {})
    provenance = analytics_view_model.get('provenance_chain', {})
    epidemiology = analytics_view_model.get('info_epidemiology', {})

    def _badge(text: str, color: str = '#4edea3') -> str:
        return (f"<span style='display:inline-block;margin:2px 4px;padding:2px 8px;"
                f"background:rgba(78,222,163,.10);color:{html.escape(color)};"
                f"border:1px solid rgba(78,222,163,.2);border-radius:3px;"
                f"font-size:11px;font-family:Space Grotesk,monospace;'>"
                f"{html.escape(str(text))}</span>")

    def _section(
        title: str,
        content: str,
        icon: str = '',
        *,
        section_id: str = '',
        role_min: str = 'viewer',
    ) -> str:
        sid = html.escape(section_id) if section_id else ''
        return (f"<div id='{sid}' class='analytics-section' data-role-min='{html.escape(role_min)}' "
                f"style='margin:24px 0;padding:20px;background:#1a2540;"
                f"border:1px solid #263050;border-radius:6px;'>"
                f"<h3 style='margin:0 0 16px 0;color:#4edea3;font-family:Space Grotesk,monospace;"
                f"font-size:14px;text-transform:uppercase;letter-spacing:.08em;'>"
                f"{html.escape(icon)} {html.escape(title)}</h3>"
                f"{content}</div>")

    # --- Cross-Domain Fusion ---
    fusion_rows = ''
    for country_id, fres in sorted(fusion.items()):
        if not isinstance(fres, dict):
            continue
        fused_score = fres.get('fused_score', '')
        confidence = fres.get('confidence', '')
        contradiction = fres.get('contradiction_detected', False)
        contras = fres.get('contradictions', [])
        contra_text = '; '.join(
            f"{c.get('domain_a','?')}/{c.get('domain_b','?')} gap={c.get('severity_gap','?')}"
            for c in contras if isinstance(c, dict)
        ) or 'none'
        badge_color = '#f87171' if contradiction else '#4edea3'
        fusion_rows += (
            f"<tr><td style='padding:6px 10px;font-weight:600;'>{html.escape(country_id)}</td>"
            f"<td style='padding:6px 10px;'>{round(float(fused_score), 3) if fused_score != '' else '-'}</td>"
            f"<td style='padding:6px 10px;'>{round(float(confidence), 3) if confidence != '' else '-'}</td>"
            f"<td style='padding:6px 10px;'>{_badge('YES' if contradiction else 'no', badge_color)}</td>"
            f"<td style='padding:6px 10px;font-size:11px;color:#8899bb;'>{html.escape(contra_text)}</td></tr>"
        )
    fusion_section = _section('Cross-Domain Fusion', (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Country</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Fused Score</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Confidence</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Contradiction</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Details</th></tr></thead>"
        f"<tbody>{fusion_rows or '<tr><td colspan=5 style=\"color:#6b7d99;padding:8px 10px;\">No fusion data available</td></tr>'}</tbody></table>"
    ), '🔀', section_id='analytics-cross-domain-fusion', role_min='viewer') if fusion else _section('Cross-Domain Fusion', '<p style="color:#6b7d99;">No data</p>', '🔀', section_id='analytics-cross-domain-fusion', role_min='viewer')

    # --- Bayesian Estimates ---
    bayes_rows = ''
    for country_id, domains in sorted(bayesian.items()):
        if not isinstance(domains, dict):
            continue
        for domain, est in sorted(domains.items()):
            if not isinstance(est, dict):
                continue
            map_st = est.get('map_status', '-')
            conf = est.get('confidence', '')
            ci = est.get('confidence_interval', ['-', '-'])
            ci_str = f"{ci[0]}..{ci[1]}" if isinstance(ci, list) and len(ci) == 2 else str(ci)
            bayes_rows += (
                f"<tr><td style='padding:5px 10px;'>{html.escape(country_id)}</td>"
                f"<td style='padding:5px 10px;'>{html.escape(domain)}</td>"
                f"<td style='padding:5px 10px;font-weight:600;'>{html.escape(str(map_st))}</td>"
                f"<td style='padding:5px 10px;'>{round(float(conf), 3) if conf != '' else '-'}</td>"
                f"<td style='padding:5px 10px;font-size:11px;color:#8899bb;'>{html.escape(ci_str)}</td></tr>"
            )
    bayes_section = _section('Bayesian Status Estimates', (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Country</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Domain</th>"
        f"<th style='padding:4px 10px;text-align:left;'>MAP Status</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Confidence</th>"
        f"<th style='padding:4px 10px;text-align:left;'>80% CI</th></tr></thead>"
        f"<tbody>{bayes_rows or '<tr><td colspan=5 style=\"color:#6b7d99;padding:8px 10px;\">No data</td></tr>'}</tbody></table>"
    ), '📊', section_id='analytics-bayesian-estimates', role_min='viewer') if bayesian else _section('Bayesian Status Estimates', '<p style="color:#6b7d99;">No data</p>', '📊', section_id='analytics-bayesian-estimates', role_min='viewer')

    # --- Uncertainty Budgets ---
    unc_rows = ''
    for country_id, budget in sorted(uncertainty.items()):
        if not isinstance(budget, dict):
            continue
        total_unc = budget.get('total_uncertainty', '')
        dominant = budget.get('dominant_stage', '-')
        prop_factor = budget.get('propagation_factor', '')
        unc_rows += (
            f"<tr><td style='padding:5px 10px;'>{html.escape(country_id)}</td>"
            f"<td style='padding:5px 10px;'>{round(float(total_unc), 4) if total_unc != '' else '-'}</td>"
            f"<td style='padding:5px 10px;'>{html.escape(str(dominant))}</td>"
            f"<td style='padding:5px 10px;'>{round(float(prop_factor), 3) if prop_factor != '' else '-'}</td></tr>"
        )
    unc_section = _section('Uncertainty Propagation', (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Country</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Total Uncertainty</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Dominant Stage</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Propagation Factor</th></tr></thead>"
        f"<tbody>{unc_rows or '<tr><td colspan=4 style=\"color:#6b7d99;padding:8px 10px;\">No data</td></tr>'}</tbody></table>"
    ), '⚖️', section_id='analytics-uncertainty-budgets', role_min='viewer') if uncertainty else _section('Uncertainty Propagation', '<p style="color:#6b7d99;">No data</p>', '⚖️', section_id='analytics-uncertainty-budgets', role_min='viewer')

    # --- Rule Evaluations ---
    matched_rules = [r for r in rules if isinstance(r, dict) and r.get('matched')]
    rule_rows = ''
    for r in sorted(matched_rules, key=lambda x: x.get('severity', '')):
        sev = r.get('severity', '-')
        sev_color = '#f87171' if sev == 'critical' else '#fbbf24' if sev == 'high' else '#4edea3'
        rule_rows += (
            f"<tr><td style='padding:5px 10px;'>{html.escape(r.get('country_id', '-'))}</td>"
            f"<td style='padding:5px 10px;'>{html.escape(r.get('domain', '-'))}</td>"
            f"<td style='padding:5px 10px;'>{html.escape(r.get('rule_id', '-'))}</td>"
            f"<td style='padding:5px 10px;'>{_badge(sev, sev_color)}</td>"
            f"<td style='padding:5px 10px;font-size:11px;color:#8899bb;max-width:300px;'>"
            f"{html.escape(str(r.get('annotation_text', ''))[:120])}</td></tr>"
        )
    rule_summary = f"{len(matched_rules)} matched / {len(rules)} evaluated"
    rule_section = _section(f'Rule Evaluations ({rule_summary})', (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Country</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Domain</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Rule</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Severity</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Annotation</th></tr></thead>"
        f"<tbody>{rule_rows or '<tr><td colspan=5 style=\"color:#6b7d99;padding:8px 10px;\">No rules matched</td></tr>'}</tbody></table>"
    ), '📋', section_id='analytics-rule-evaluations', role_min='analyst')

    # --- Dependency Graph ---
    dep_clusters = dep_graph.get('clusters', [])
    dep_sources = dep_graph.get('source_count', 0)
    dep_edges = dep_graph.get('edge_count', 0)
    cluster_html = ''
    for cl in dep_clusters[:10]:
        if not isinstance(cl, dict):
            continue
        sources = ', '.join(cl.get('sources', []))
        cluster_html += (
            f"<div style='margin:4px 0;padding:6px 10px;background:#10192e;border-radius:3px;font-size:11px;'>"
            f"<strong style='color:#4edea3;'>{html.escape(cl.get('cluster_id', '?'))}</strong>"
            f" &nbsp;|&nbsp; sources: {html.escape(sources)}"
            f" &nbsp;|&nbsp; cohesion: {round(float(cl.get('cohesion', 0)), 3)}</div>"
        )
    dep_section = _section(f'Source Dependency Graph ({dep_sources} sources, {dep_edges} edges)', (
        f"<p style='color:#8899bb;font-size:12px;margin:0 0 12px 0;'>{len(dep_clusters)} clusters detected</p>"
        f"{cluster_html or '<p style=\"color:#6b7d99;font-size:12px;\">No clusters (insufficient source coupling)</p>'}"
    ), '🕸️', section_id='analytics-dependency-graph', role_min='admin')

    # --- Provenance Chain ---
    prov_roots = provenance.get('root_sources', [])
    prov_leaves = provenance.get('leaf_outputs', [])
    prov_depth = provenance.get('depth', 0)
    prov_section = _section(f'Provenance Chain (depth={prov_depth})', (
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:16px;font-size:12px;'>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Root Sources ({len(prov_roots)})</h4>"
        f"{''.join(_badge(s) for s in prov_roots[:12]) or '<span style=\"color:#6b7d99;\">none</span>'}</div>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Leaf Outputs ({len(prov_leaves)})</h4>"
        f"{''.join(_badge(s, '#60a5fa') for s in prov_leaves[:12]) or '<span style=\"color:#6b7d99;\">none</span>'}</div>"
        f"</div>"
    ) if provenance else '<p style="color:#6b7d99;">No provenance data</p>', '📍', section_id='analytics-provenance-chain', role_min='admin')

    spread_paths = epidemiology.get('spread_paths', [])
    amp_events = epidemiology.get('amplification_events', [])
    lineage_root_badges = ''.join(_badge(s, '#93c5fd') for s in prov_roots[:8]) or '<span style="color:#6b7d99;">none</span>'
    lineage_leaf_badges = ''.join(_badge(s, '#a78bfa') for s in prov_leaves[:8]) or '<span style="color:#6b7d99;">none</span>'
    lineage_spread_rows = ''
    for sp in spread_paths[:5]:
        if not isinstance(sp, dict):
            continue
        seq = ' → '.join(str(item) for item in sp.get('source_sequence', [])) or 'n/a'
        lineage_spread_rows += (
            f"<div style='margin:4px 0;padding:6px 10px;background:#10192e;border-radius:3px;font-size:11px;'>"
            f"<strong style='color:#93c5fd;'>{html.escape(str(sp.get('signal_key', '?')))}</strong>"
            f" &nbsp;|&nbsp; {html.escape(seq)}"
            f" &nbsp;|&nbsp; spread={html.escape(str(sp.get('total_spread_hours', '?')))}h"
            f"</div>"
        )
    top_dep_cluster = dep_clusters[0] if dep_clusters and isinstance(dep_clusters[0], dict) else {}
    top_spread_path = spread_paths[0] if spread_paths and isinstance(spread_paths[0], dict) else {}
    top_amplification = amp_events[0] if amp_events and isinstance(amp_events[0], dict) else {}
    hotspot_rows = ''
    if top_dep_cluster:
        hotspot_rows += (
            "<tr>"
            "<td style='padding:6px 10px;'>Dependency cluster</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(top_dep_cluster.get('cluster_id', 'n/a')))}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(', '.join(str(item) for item in top_dep_cluster.get('sources', [])) or 'n/a')}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(round(float(top_dep_cluster.get('cohesion', 0)), 3)))}</td>"
            "</tr>"
        )
    if top_spread_path:
        hotspot_rows += (
            "<tr>"
            "<td style='padding:6px 10px;'>Spread path</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(top_spread_path.get('signal_key', 'n/a')))}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(' → '.join(str(item) for item in top_spread_path.get('source_sequence', [])) or 'n/a')}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(top_spread_path.get('total_spread_hours', 'n/a')))}h</td>"
            "</tr>"
        )
    if top_amplification:
        hotspot_rows += (
            "<tr>"
            "<td style='padding:6px 10px;'>Amplification event</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(top_amplification.get('signal_key', 'n/a')))}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(str(top_amplification.get('source_id', 'n/a')))}</td>"
            f"<td style='padding:6px 10px;'>×{html.escape(str(top_amplification.get('amplification_factor', 'n/a')))} @ {html.escape(str(top_amplification.get('lag_hours', 'n/a')))}h</td>"
            "</tr>"
        )
    lineage_section = _section(f'Source Lineage Visualization ({len(prov_roots)} roots, {len(prov_leaves)} leaves, {len(spread_paths)} spreads)', (
        f"<div style='display:grid;grid-template-columns:1fr;gap:16px;font-size:12px;'>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Provenance Flow</h4>"
        f"<div style='display:flex;flex-wrap:wrap;gap:6px;align-items:center;'>"
        f"{lineage_root_badges}"
        f"<span style='color:#6b7d99;font-size:13px;font-weight:700;'>→</span>"
        f"{lineage_leaf_badges}"
        f"</div>"
        f"<p style='color:#8899bb;font-size:11px;margin:8px 0 0 0;'>Depth: {html.escape(str(prov_depth))} | Roots: {len(prov_roots)} | Leaves: {len(prov_leaves)}</p></div>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Spread / Amplification Snapshots</h4>"
        f"{lineage_spread_rows or '<p style=\"color:#6b7d99;font-size:12px;\">None detected</p>'}</div>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Source Hotspot Matrix</h4>"
        f"<table id='analytics-source-hotspot-matrix' style='width:100%;border-collapse:collapse;font-size:11px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'><th style='padding:4px 10px;text-align:left;'>Type</th><th style='padding:4px 10px;text-align:left;'>Focus</th><th style='padding:4px 10px;text-align:left;'>Path / Members</th><th style='padding:4px 10px;text-align:left;'>Intensity</th></tr></thead>"
        f"<tbody>{hotspot_rows or '<tr><td colspan=4 style=\"color:#6b7d99;padding:8px 10px;\">No source hotspots available</td></tr>'}</tbody></table></div>"
        f"</div>"
    ), '🧭', section_id='analytics-source-lineage-visualization', role_min='analyst') if (provenance or epidemiology) else _section('Source Lineage Visualization', '<p style="color:#6b7d99;">No data</p>', '🧭', section_id='analytics-source-lineage-visualization', role_min='analyst')

    # --- Info Epidemiology ---
    spread_paths = epidemiology.get('spread_paths', [])
    amp_events = epidemiology.get('amplification_events', [])
    spread_html = ''
    for sp in spread_paths[:8]:
        if not isinstance(sp, dict):
            continue
        seq = ' → '.join(sp.get('source_sequence', []))
        spread_html += (
            f"<div style='margin:4px 0;padding:6px 10px;background:#10192e;border-radius:3px;font-size:11px;'>"
            f"<strong style='color:#a78bfa;'>{html.escape(sp.get('signal_key', '?'))}</strong>"
            f" &nbsp;|&nbsp; {html.escape(seq)}"
            f" &nbsp;|&nbsp; spread={sp.get('total_spread_hours', '?')}h</div>"
        )
    amp_html = ''
    for ae in amp_events[:6]:
        if not isinstance(ae, dict):
            continue
        amp_html += (
            f"<div style='margin:4px 0;padding:6px 10px;background:#10192e;border-radius:3px;font-size:11px;'>"
            f"<strong style='color:#fbbf24;'>{html.escape(ae.get('signal_key', '?'))}</strong>"
            f" via {html.escape(ae.get('source_id', '?'))}"
            f" &nbsp;×{ae.get('amplification_factor', '?')} @ {ae.get('lag_hours', '?')}h lag</div>"
        )
    epi_section = _section(f'Information Epidemiology ({len(spread_paths)} paths, {len(amp_events)} amplifications)', (
        f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:16px;'>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Spread Paths</h4>"
        f"{spread_html or '<p style=\"color:#6b7d99;font-size:12px;\">None detected</p>'}</div>"
        f"<div><h4 style='color:#6b7d99;margin:0 0 8px 0;font-size:11px;text-transform:uppercase;'>Amplification Events</h4>"
        f"{amp_html or '<p style=\"color:#6b7d99;font-size:12px;\">None detected</p>'}</div>"
        f"</div>"
    ), '🦠', section_id='analytics-info-epidemiology', role_min='analyst')

    analytics_controls = (
        "<div id='analytics-controls' class='panel' style='margin:0 0 18px 0;'>"
        "<div class='panel-header'>Analytics Navigation & Filter</div>"
        "<div class='controls-bar'>"
        "<a class='btn-download' href='#analytics-cross-domain-fusion'>Fusion</a>"
        "<a class='btn-download' href='#analytics-bayesian-estimates'>Bayesian</a>"
        "<a class='btn-download' href='#analytics-uncertainty-budgets'>Uncertainty</a>"
        "<a class='btn-download' href='#analytics-rule-evaluations'>Rules</a>"
        "<a class='btn-download' href='#analytics-dependency-graph'>Dependency</a>"
        "<a class='btn-download' href='#analytics-provenance-chain'>Provenance</a>"
        "<a class='btn-download' href='#analytics-source-lineage-visualization'>Lineage Visual</a>"
        "<a class='btn-download' href='#analytics-info-epidemiology'>Epidemiology</a>"
        "</div>"
        "<div class='controls-bar'>"
        "<label for='analytics-section-filter'>Section</label>"
        "<select id='analytics-section-filter'>"
        "<option value='all'>All</option>"
        "<option value='country'>Country-centric</option>"
        "<option value='rules'>Rule/decision</option>"
        "<option value='dependency'>Dependency/provenance</option>"
        "</select>"
        "<label for='analytics-text-filter'>Search</label>"
        "<input id='analytics-text-filter' type='text' placeholder='filter section title'>"
        "<button id='analytics-filter-reset' type='button'>Reset</button>"
        "</div>"
        "</div>"
    )
    analytics_filter_js = (
        "<script>"
        "(function(){"
        "var sel=document.getElementById('analytics-section-filter');"
        "var txt=document.getElementById('analytics-text-filter');"
        "var reset=document.getElementById('analytics-filter-reset');"
        "var sections=Array.from(document.querySelectorAll('.analytics-section'));"
        "var tags={"
        "'analytics-cross-domain-fusion':'country',"
        "'analytics-bayesian-estimates':'country',"
        "'analytics-uncertainty-budgets':'country',"
        "'analytics-rule-evaluations':'rules',"
        "'analytics-dependency-graph':'dependency',"
        "'analytics-provenance-chain':'dependency',"
        "'analytics-source-lineage-visualization':'dependency',"
        "'analytics-info-epidemiology':'rules'"
        "};"
        "function applyAnalyticsSectionFilter(){"
        "var mode=(sel&&sel.value)||'all';"
        "var q=((txt&&txt.value)||'').toLowerCase().trim();"
        "sections.forEach(function(sec){"
        "var id=sec.id||'';"
        "var tag=tags[id]||'country';"
        "var title=(sec.querySelector('h3')?.textContent||'').toLowerCase();"
        "var modeOk=(mode==='all'||mode===tag);"
        "var textOk=(!q||title.indexOf(q)>=0);"
        "sec.style.display=(modeOk&&textOk)?'':'none';"
        "});"
        "}"
        "if(sel) sel.addEventListener('change', applyAnalyticsSectionFilter);"
        "if(txt) txt.addEventListener('input', applyAnalyticsSectionFilter);"
        "if(reset) reset.addEventListener('click', function(){ if(sel) sel.value='all'; if(txt) txt.value=''; applyAnalyticsSectionFilter(); });"
        "applyAnalyticsSectionFilter();"
        "})();"
        "</script>"
    )

    body = (
        "<h2 style='color:#e2e8f0;margin:0 0 24px 0;font-family:Space Grotesk,monospace;'>Advanced Analytics</h2>"
        "<p style='color:#8899bb;font-size:13px;margin:0 0 24px 0;'>"
        "Phase 4-6 analytical module outputs: cross-domain fusion, probabilistic scoring, "
        "uncertainty propagation, rule-based assessment, dependency graph, provenance chain, "
        "source-lineage visualization, and information epidemiology.</p>"
        + analytics_controls
        + fusion_section
        + bayes_section
        + unc_section
        + rule_section
        + dep_section
        + prov_section
        + lineage_section
        + epi_section
        + analytics_filter_js
    )
    return _page('Advanced Analytics', body, nav_prefix=nav_prefix, available_pages=available_pages)


def _render_release_failure_drill_body(release_failure_drill_report_view_model: dict[str, Any] | None) -> str:
    if not release_failure_drill_report_view_model:
        return "<p style='color:#6b7d99;'>No release failure drill data available.</p>"

    checks = release_failure_drill_report_view_model.get('checks', {}) or {}
    scenarios = release_failure_drill_report_view_model.get('scenarios', {}) or {}
    failure_localization = release_failure_drill_report_view_model.get('failure_localization', {}) or {}
    operator_failure_drill_digest = release_failure_drill_report_view_model.get('operator_failure_drill_digest', {}) or {}
    operator_failure_drill_trend_baseline = release_failure_drill_report_view_model.get('operator_failure_drill_trend_baseline', {}) or {}
    operator_recurrence_aware_remediation_prioritization = release_failure_drill_report_view_model.get('operator_recurrence_aware_remediation_prioritization', {}) or {}
    operator_failure_drill_delta_ledger = release_failure_drill_report_view_model.get('operator_failure_drill_delta_ledger', {}) or {}
    operator_remediation_execution_loop = release_failure_drill_report_view_model.get('operator_remediation_execution_loop', {}) or {}
    operator_stale_remediation_action_plan = release_failure_drill_report_view_model.get('operator_stale_remediation_action_plan', {}) or {}
    operator_stale_remediation_closure_drill = release_failure_drill_report_view_model.get('operator_stale_remediation_closure_drill', {}) or {}

    check_pass_count = sum(1 for value in checks.values() if bool(value))
    check_total = len(checks)

    scenario_rows = ''
    for scenario_id, scenario_assessment in scenarios.items():
        release_gate = scenario_assessment.get('release_gate', {}) if isinstance(scenario_assessment, dict) else {}
        gate_verdict = str(release_gate.get('gate_verdict', 'n/a'))
        blocker_count = len(release_gate.get('blockers', []) or [])
        localization_count = len(failure_localization.get(scenario_id, []) or [])
        scenario_rows += (
            f"<tr>"
            f"<td style='padding:6px 10px;font-weight:600;'>{html.escape(str(scenario_id))}</td>"
            f"<td style='padding:6px 10px;'>{_badge(gate_verdict, '#4edea3' if gate_verdict == 'go' else '#f87171')}</td>"
            f"<td style='padding:6px 10px;'>{blocker_count}</td>"
            f"<td style='padding:6px 10px;'>{localization_count}</td>"
            f"</tr>"
        )

    localization_rows = ''
    for scenario_id, entries in failure_localization.items():
        if not entries:
            continue
        gate_ids = ', '.join(str(entry.get('gate_id', 'unknown')) for entry in entries)
        localization_rows += (
            f"<tr>"
            f"<td style='padding:6px 10px;font-weight:600;'>{html.escape(str(scenario_id))}</td>"
            f"<td style='padding:6px 10px;'>{html.escape(gate_ids)}</td>"
            f"</tr>"
        )

    digest_cluster_count = int(operator_failure_drill_digest.get('cluster_count', 0) or 0)
    digest_top_gate = str(operator_failure_drill_digest.get('top_cluster_gate_id', 'n/a'))
    trend_snapshot_count = int(operator_failure_drill_trend_baseline.get('snapshot_count', 0) or 0)
    trend_focus = str(operator_failure_drill_trend_baseline.get('operator_focus', 'n/a'))
    prioritization_count = int(operator_recurrence_aware_remediation_prioritization.get('priority_count', 0) or 0)
    delta_snapshot_count = int(operator_failure_drill_delta_ledger.get('snapshot_count', 0) or 0)
    delta_summary = html.escape(str(operator_failure_drill_delta_ledger.get('movement_summary', 'n/a')))
    execution_action_count = int(operator_remediation_execution_loop.get('action_count', 0) or 0)
    stale_action_count = int(operator_stale_remediation_action_plan.get('action_count', 0) or 0)
    stale_breach_count = int(operator_stale_remediation_closure_drill.get('stale_remediation_gap_injected', {}).get('breach_count', 0) or 0)

    release_evidence_markdown = html.escape(render_release_evidence_markdown(release_failure_drill_report_view_model))

    def _mini_section(title: str, content: str, icon: str, *, section_id: str, role_min: str) -> str:
        return (
            f"<div id='{html.escape(section_id)}' class='analytics-section' data-role-min='{html.escape(role_min)}' "
            f"style='margin:24px 0;padding:20px;background:#1a2540;border:1px solid #263050;border-radius:6px;'>"
            f"<h3 style='margin:0 0 16px 0;color:#4edea3;font-family:Space Grotesk,monospace;font-size:14px;text-transform:uppercase;letter-spacing:.08em;'>"
            f"{html.escape(icon)} {html.escape(title)}</h3>{content}</div>"
        )

    summary_html = (
        f"<div style='display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;font-size:12px;'>"
        f"<div><strong>drill_verdict</strong><br>{html.escape(str(release_failure_drill_report_view_model.get('drill_verdict', 'n/a')))}</div>"
        f"<div><strong>checks_passed</strong><br>{check_pass_count}/{check_total}</div>"
        f"<div><strong>scenarios</strong><br>{len(scenarios)}</div>"
        f"<div><strong>digest_clusters</strong><br>{digest_cluster_count} (top: {html.escape(digest_top_gate)})</div>"
        f"<div><strong>trend_snapshots</strong><br>{trend_snapshot_count} | focus: {html.escape(trend_focus)}</div>"
        f"<div><strong>priorities</strong><br>{prioritization_count} | delta snapshots: {delta_snapshot_count}</div>"
        f"<div><strong>execution actions</strong><br>{execution_action_count}</div>"
        f"<div><strong>stale action plan</strong><br>{stale_action_count} | breaches: {stale_breach_count}</div>"
        f"<div><strong>delta summary</strong><br>{delta_summary}</div>"
        f"</div>"
    )

    scenarios_html = (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Scenario</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Gate verdict</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Blockers</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Localized failures</th></tr></thead>"
        f"<tbody>{scenario_rows or '<tr><td colspan=4 style=\"color:#6b7d99;padding:8px 10px;\">No scenarios available</td></tr>'}</tbody></table>"
    )

    localization_html = (
        f"<table style='width:100%;border-collapse:collapse;font-size:12px;'>"
        f"<thead><tr style='color:#6b7d99;border-bottom:1px solid #263050;'>"
        f"<th style='padding:4px 10px;text-align:left;'>Scenario</th>"
        f"<th style='padding:4px 10px;text-align:left;'>Localized gate IDs</th></tr></thead>"
        f"<tbody>{localization_rows or '<tr><td colspan=2 style=\"color:#6b7d99;padding:8px 10px;\">No localized failures available</td></tr>'}</tbody></table>"
    )

    markdown_html = (
        "<pre style='white-space:pre-wrap;word-break:break-word;font-size:11px;line-height:1.5;"
        "background:#10192e;border:1px solid #263050;border-radius:4px;padding:14px;color:#c7d2fe;'>"
        f"{release_evidence_markdown}"
        "</pre>"
    )

    return (
        "<h2 style='color:#e2e8f0;margin:0 0 24px 0;font-family:Space Grotesk,monospace;'>Release / Failure Drill</h2>"
        "<p style='color:#8899bb;font-size:13px;margin:0 0 24px 0;'>"
        "Scenarioized release evidence, failure localization, and operator remediation outputs from the governed release-failure drill report.</p>"
        + _mini_section('Drill Summary', summary_html, '🧪', section_id='failure-drill-summary', role_min='viewer')
        + _mini_section('Scenario Matrix', scenarios_html, '🧩', section_id='failure-drill-scenarios', role_min='viewer')
        + _mini_section('Failure Localization', localization_html, '🎯', section_id='failure-drill-localization', role_min='analyst')
        + _mini_section('Evidence Pack Markdown', markdown_html, '📝', section_id='failure-drill-markdown', role_min='viewer')
    )


def build_local_mvp_site(
    *,
    output_dir: Path,
    world_map_read_model: dict[str, Any] | None = None,
    country_profile_read_models: dict[str, dict[str, Any]] | None = None,
    domain_detail_read_models: dict[tuple[str, str], dict[str, Any]] | None = None,
    source_coverage_read_model: dict[str, Any] | None = None,
    system_status_read_model: dict[str, Any] | None = None,
    report_catalog: dict[str, Any] | None = None,
    traceability_view_model: dict[str, Any] | None = None,
    annotations_view_model: dict[str, Any] | None = None,
    repo_closure_view_model: dict[str, Any] | None = None,
    validation_view_model: dict[str, Any] | None = None,
    readiness_view_model: dict[str, Any] | None = None,
    release_demo_package_view_model: dict[str, Any] | None = None,
    release_failure_drill_report_view_model: dict[str, Any] | None = None,
    release_gate_view_model: dict[str, Any] | None = None,
    stakeholder_functional_closure_view_model: dict[str, Any] | None = None,
    stakeholder_e2e_flow_coverage_view_model: dict[str, Any] | None = None,
    release_readiness_index_view_model: dict[str, Any] | None = None,
    stakeholder_e2e_ui_smoke_view_model: dict[str, Any] | None = None,
    operator_release_summary_view_model: dict[str, Any] | None = None,
    operator_blocker_causality_view_model: dict[str, Any] | None = None,
    operator_operability_cluster_view_model: dict[str, Any] | None = None,
    operator_failure_drill_digest_view_model: dict[str, Any] | None = None,
    operator_failure_drill_trend_baseline_view_model: dict[str, Any] | None = None,
    operator_recurrence_aware_remediation_prioritization_view_model: dict[str, Any] | None = None,
    operator_failure_drill_delta_ledger_view_model: dict[str, Any] | None = None,
    operator_remediation_execution_loop_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_closure_drill_view_model: dict[str, Any] | None = None,
    operator_stale_remediation_action_plan_view_model: dict[str, Any] | None = None,
    analyst_briefing_view_model: dict[str, Any] | None = None,
    analytics_view_model: dict[str, Any] | None = None,
    ui_role: str = 'analyst',
) -> SiteBuildResult:
    normalized_role = _normalize_ui_role(ui_role)

    world_map_read_model = world_map_read_model or {}
    country_profile_read_models = country_profile_read_models or {}
    domain_detail_read_models = domain_detail_read_models or {}
    source_coverage_read_model = source_coverage_read_model or {}
    system_status_read_model = system_status_read_model or {}
    report_catalog = report_catalog or {}

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
        'release_package.html',
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
    if analytics_view_model is not None:
        available_pages.add('analytics.html')
    if release_failure_drill_report_view_model is not None:
        available_pages.add('release_failure_drill.html')

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
    source_coverage_json_file = output_dir / 'source_coverage.json'
    source_coverage_json_file.write_text(json.dumps(source_coverage_read_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(source_coverage_json_file)

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
    system_status_json_file = output_dir / 'system_status.json'
    system_status_json_file.write_text(json.dumps(system_status_read_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(system_status_json_file)

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
    if analytics_view_model is not None:
        analytics_file = output_dir / 'analytics.html'
        analytics_file.write_text(_render_analytics(analytics_view_model, nav_prefix='', available_pages=available_pages), encoding='utf-8')
        generated_files.append(analytics_file)

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
    if release_gate_view_model is None:
        release_gate_view_model = build_release_gate_view_model(
            readiness_view_model=readiness_view_model,
            traceability_integrity_report=build_traceability_integrity_report(repo_root=Path(__file__).resolve().parents[3]),
        )
    if stakeholder_e2e_flow_coverage_view_model is None:
        stakeholder_e2e_flow_coverage_view_model = build_stakeholder_e2e_flow_coverage_report(
            repo_root=Path(__file__).resolve().parents[3]
        )
    if stakeholder_e2e_ui_smoke_view_model is None:
        stakeholder_e2e_ui_smoke_view_model = build_stakeholder_e2e_ui_smoke_report(repo_root=Path(__file__).resolve().parents[3])
    if release_readiness_index_view_model is None:
        release_readiness_index_view_model = build_release_readiness_index(
            repo_root=Path(__file__).resolve().parents[3],
            release_gate_view_model=release_gate_view_model,
            stakeholder_functional_closure_report=stakeholder_functional_closure_view_model or {},
            stakeholder_e2e_flow_coverage_report=stakeholder_e2e_flow_coverage_view_model,
            stakeholder_e2e_ui_smoke_report=stakeholder_e2e_ui_smoke_view_model,
        )
    if analyst_briefing_view_model is None:
        analyst_briefing_view_model = _build_analyst_briefing_view_model(
            readiness_view_model=readiness_view_model,
            release_gate_view_model=release_gate_view_model,
            operator_release_summary_view_model=operator_release_summary_view_model,
            operator_blocker_causality_view_model=operator_blocker_causality_view_model,
            operator_operability_cluster_view_model=operator_operability_cluster_view_model,
            operator_stale_remediation_action_plan_view_model=operator_stale_remediation_action_plan_view_model,
            system_status_read_model=system_status_read_model,
            validation_view_model=validation_view_model,
            traceability_view_model=traceability_view_model,
            repo_closure_view_model=repo_closure_view_model,
        )
    if release_demo_package_view_model is None:
        release_demo_package_view_model = build_release_demo_package_view_model(
            readiness_view_model=readiness_view_model,
            release_gate_view_model=release_gate_view_model,
            operator_release_summary_view_model=operator_release_summary_view_model,
            operator_blocker_causality_view_model=operator_blocker_causality_view_model,
            operator_operability_cluster_view_model=operator_operability_cluster_view_model,
            operator_stale_remediation_action_plan_view_model=operator_stale_remediation_action_plan_view_model,
            system_status_read_model=system_status_read_model,
            validation_view_model=validation_view_model,
            traceability_view_model=traceability_view_model,
            repo_closure_view_model=repo_closure_view_model,
            analyst_briefing_view_model=analyst_briefing_view_model,
            available_pages=available_pages,
        )

    readiness_file = output_dir / 'readiness.html'
    readiness_file.write_text(
        _render_readiness(
            readiness_view_model,
            release_gate_view_model,
            stakeholder_functional_closure_view_model,
            stakeholder_e2e_flow_coverage_view_model,
            release_readiness_index_view_model,
            stakeholder_e2e_ui_smoke_view_model,
            operator_release_summary_view_model,
            operator_blocker_causality_view_model,
            operator_operability_cluster_view_model,
            operator_failure_drill_digest_view_model,
            operator_failure_drill_trend_baseline_view_model,
            operator_recurrence_aware_remediation_prioritization_view_model,
            operator_failure_drill_delta_ledger_view_model,
            operator_remediation_execution_loop_view_model,
            operator_stale_remediation_closure_drill_view_model,
            operator_stale_remediation_action_plan_view_model,
            analyst_briefing_view_model,
            nav_prefix='',
            available_pages=available_pages,
        ),
        encoding='utf-8',
    )
    generated_files.append(readiness_file)
    readiness_json_file = output_dir / 'readiness.json'
    readiness_json_file.write_text(json.dumps(readiness_view_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(readiness_json_file)
    release_demo_package_file = output_dir / 'release_package.html'
    release_demo_package_file.write_text(
        _page('Release / Demo Package', render_release_demo_package_body(release_demo_package_view_model), nav_prefix='', available_pages=available_pages),
        encoding='utf-8',
    )
    generated_files.append(release_demo_package_file)
    release_demo_package_json_file = output_dir / 'release_demo_package.json'
    release_demo_package_json_file.write_text(json.dumps(release_demo_package_view_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(release_demo_package_json_file)
    if release_failure_drill_report_view_model is not None:
        release_failure_drill_file = output_dir / 'release_failure_drill.html'
        release_failure_drill_file.write_text(
            _page(
                'Release / Failure Drill',
                _render_release_failure_drill_body(release_failure_drill_report_view_model),
                nav_prefix='',
                available_pages=available_pages,
            ),
            encoding='utf-8',
        )
        generated_files.append(release_failure_drill_file)
        release_failure_drill_json_file = output_dir / 'release_failure_drill_report.json'
        release_failure_drill_json_file.write_text(
            json.dumps(release_failure_drill_report_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(release_failure_drill_json_file)
    release_gate_json_file = output_dir / 'release_gate.json'
    release_gate_json_file.write_text(json.dumps(release_gate_view_model, indent=2, sort_keys=True), encoding='utf-8')
    generated_files.append(release_gate_json_file)
    if stakeholder_functional_closure_view_model is not None:
        stakeholder_closure_json_file = output_dir / 'stakeholder_functional_closure.json'
        stakeholder_closure_json_file.write_text(
            json.dumps(stakeholder_functional_closure_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(stakeholder_closure_json_file)
    if stakeholder_e2e_flow_coverage_view_model is not None:
        stakeholder_e2e_flow_json_file = output_dir / 'stakeholder_e2e_flow_coverage.json'
        stakeholder_e2e_flow_json_file.write_text(
            json.dumps(stakeholder_e2e_flow_coverage_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(stakeholder_e2e_flow_json_file)
    if release_readiness_index_view_model is not None:
        release_readiness_index_json = output_dir / "release_readiness_index.json"
        release_readiness_index_json.write_text(
            json.dumps(release_readiness_index_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(release_readiness_index_json)

    if stakeholder_e2e_ui_smoke_view_model is not None:
        stakeholder_e2e_ui_smoke_json = output_dir / "stakeholder_e2e_ui_smoke.json"
        stakeholder_e2e_ui_smoke_json.write_text(
            json.dumps(stakeholder_e2e_ui_smoke_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(stakeholder_e2e_ui_smoke_json)

    if operator_release_summary_view_model is not None:
        operator_release_summary_json = output_dir / "operator_release_summary.json"
        operator_release_summary_json.write_text(
            json.dumps(operator_release_summary_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_release_summary_json)

    if operator_failure_drill_digest_view_model is not None:
        operator_failure_drill_digest_json = output_dir / "operator_failure_drill_digest.json"
        operator_failure_drill_digest_json.write_text(
            json.dumps(operator_failure_drill_digest_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_failure_drill_digest_json)

    if operator_failure_drill_trend_baseline_view_model is not None:
        operator_failure_drill_trend_baseline_json = output_dir / "operator_failure_drill_trend_baseline.json"
        operator_failure_drill_trend_baseline_json.write_text(
            json.dumps(operator_failure_drill_trend_baseline_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_failure_drill_trend_baseline_json)

    if operator_recurrence_aware_remediation_prioritization_view_model is not None:
        operator_recurrence_aware_remediation_prioritization_json = output_dir / "operator_recurrence_aware_remediation_prioritization.json"
        operator_recurrence_aware_remediation_prioritization_json.write_text(
            json.dumps(operator_recurrence_aware_remediation_prioritization_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_recurrence_aware_remediation_prioritization_json)

    if operator_failure_drill_delta_ledger_view_model is not None:
        operator_failure_drill_delta_ledger_json = output_dir / "operator_failure_drill_delta_ledger.json"
        operator_failure_drill_delta_ledger_json.write_text(
            json.dumps(operator_failure_drill_delta_ledger_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_failure_drill_delta_ledger_json)

    if operator_remediation_execution_loop_view_model is not None:
        operator_remediation_execution_loop_json = output_dir / "operator_remediation_execution_loop.json"
        operator_remediation_execution_loop_json.write_text(
            json.dumps(operator_remediation_execution_loop_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_remediation_execution_loop_json)

    if operator_stale_remediation_closure_drill_view_model is not None:
        operator_stale_remediation_closure_drill_json = output_dir / "operator_stale_remediation_closure_drill.json"
        operator_stale_remediation_closure_drill_json.write_text(
            json.dumps(operator_stale_remediation_closure_drill_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_stale_remediation_closure_drill_json)

    if operator_stale_remediation_action_plan_view_model is not None:
        operator_stale_remediation_action_plan_json = output_dir / "operator_stale_remediation_action_plan.json"
        operator_stale_remediation_action_plan_json.write_text(
            json.dumps(operator_stale_remediation_action_plan_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_stale_remediation_action_plan_json)

    if operator_operability_cluster_view_model is not None:
        operator_operability_cluster_json = output_dir / "operator_operability_cluster.json"
        operator_operability_cluster_json.write_text(
            json.dumps(operator_operability_cluster_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(operator_operability_cluster_json)

    if analyst_briefing_view_model is not None:
        analyst_briefing_json = output_dir / "analyst_briefing.json"
        analyst_briefing_json.write_text(
            json.dumps(analyst_briefing_view_model, indent=2, sort_keys=True),
            encoding='utf-8',
        )
        generated_files.append(analyst_briefing_json)

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
    parser.add_argument(
        '--skip-stakeholder-e2e-ui-smoke-report',
        action='store_true',
        help='Skip recursive UI smoke report generation (used internally by UI smoke builder subprocesses).',
    )
    args = parser.parse_args(argv)

    if args.artifacts_dir:
        payload = load_site_payload_from_artifacts(Path(args.artifacts_dir))
    else:
        payload = _demo_payload()

    if args.skip_stakeholder_e2e_ui_smoke_report:
        payload['stakeholder_e2e_ui_smoke_view_model'] = {
            'flow_count': 0,
            'covered_flow_count': 0,
            'flow_gap_count': 0,
            'flow_results': {},
            'stop_criteria': {},
        }

    result = build_local_mvp_site(output_dir=Path(args.output_dir), ui_role=args.ui_role, **payload)
    print(f'Generated SIASA local GUI at {result.output_dir / "index.html"}')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
