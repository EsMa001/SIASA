#!/usr/bin/env python3
"""Update world_map.json and system_status.json for all 30 MVP countries."""
import json
import pathlib

BASE = pathlib.Path("/opt/data/SIASA/sample_artifacts")

# All country data for world_map: (id, status, domains)
ALL_COUNTRIES = [
    # P1 Core Focus
    {"id": "UKR", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "RUS", "status": "S4", "domains": ["A", "B", "D"]},
    {"id": "CHN", "status": "S3", "domains": ["A", "B", "D"]},
    {"id": "TWN", "status": "S1", "domains": ["A", "B"]},
    {"id": "IRN", "status": "S3", "domains": ["A", "B", "D"]},
    {"id": "ISR", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "TUR", "status": "S2", "domains": ["A", "B", "D"]},
    {"id": "IND", "status": "S2", "domains": ["A", "B", "D"]},
    {"id": "PAK", "status": "S3", "domains": ["A", "D"]},
    {"id": "GEO", "status": "S2", "domains": ["A", "D"]},
    # P2 Extended Focus
    {"id": "USA", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "DEU", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "POL", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "EST", "status": "S1", "domains": ["A", "D"]},
    {"id": "FIN", "status": "S1", "domains": ["A", "D"]},
    {"id": "SAU", "status": "S1", "domains": ["A", "B", "D"]},
    {"id": "QAT", "status": "S1", "domains": ["A", "D"]},
    {"id": "NGA", "status": "S2", "domains": ["A", "B", "D"]},
    {"id": "EGY", "status": "S2", "domains": ["A", "B", "D"]},
    {"id": "SDN", "status": "S4", "domains": ["A", "B", "D"]},
    {"id": "MMR", "status": "S4", "domains": ["A", "D"]},
    # P3 Control/Reference
    {"id": "CHE", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "NLD", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "SWE", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "NOR", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "CAN", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "AUS", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "NZL", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "PRT", "status": "S0", "domains": ["A", "B", "D"]},
    {"id": "IRL", "status": "S0", "domains": ["A", "B", "D"]},
]

PRIORITY_MAP = {
    "UKR": "P1", "RUS": "P1", "CHN": "P1", "TWN": "P1", "IRN": "P1", "ISR": "P1",
    "TUR": "P1", "IND": "P1", "PAK": "P1", "GEO": "P1",
    "USA": "P2", "DEU": "P2", "POL": "P2", "EST": "P2", "FIN": "P2",
    "SAU": "P2", "QAT": "P2", "NGA": "P2", "EGY": "P2", "SDN": "P2", "MMR": "P2",
    "CHE": "P3", "NLD": "P3", "SWE": "P3", "NOR": "P3", "CAN": "P3",
    "AUS": "P3", "NZL": "P3", "PRT": "P3", "IRL": "P3",
}

# 1. Update world_map.json
world_map = {
    "active_domains": ["A", "B", "D"],
    "baseline_mode": "Combined 30/90/365",
    "countries": [
        {
            "active_domains": c["domains"],
            "country_id": c["id"],
            "drill_down_target": f"/countries/{c['id']}",
            "status": c["status"],
        }
        for c in ALL_COUNTRIES
    ],
}

wm_path = BASE / "readmodels" / "world_map.json"
with open(wm_path, "w", encoding="utf-8") as f:
    json.dump(world_map, f, indent=2, ensure_ascii=False)
print(f"Updated: {wm_path}")

# 2. Update system_status.json
all_ids = [c["id"] for c in ALL_COUNTRIES]
p1_ids = [cid for cid in all_ids if PRIORITY_MAP[cid] == "P1"]
p2_ids = [cid for cid in all_ids if PRIORITY_MAP[cid] == "P2"]
p3_ids = [cid for cid in all_ids if PRIORITY_MAP[cid] == "P3"]

# Build available_reports list
available_reports = []
for cid in all_ids:
    available_reports.append(f"REP-COUNTRY-{cid}")

# Add coverage and snapshot reports
available_reports += [
    "REP-COVERAGE-RUN-LIVE-20260520-2021",
    "REP-DAILY-SNAP-RUN-LIVE-20260520-2021-v1",
]

# Add domain reports for originally existing countries
for cid, domains in [
    ("ISR", ["A", "B", "D"]), ("POL", ["A", "B", "D"]),
    ("TWN", ["A", "B"]), ("UKR", ["A", "B", "D"])
]:
    for dom in domains:
        available_reports.append(f"REP-DOMAIN-{cid}-{dom}")

# Add event reports for originally existing countries
for cid in ["ISR", "POL", "TWN", "UKR"]:
    available_reports.append(f"REP-EVENT-EVT-{cid}-RUN-LIVE-20260520-2021")

available_reports.sort()

system_status = {
    "active_domains": ["A", "B", "D"],
    "artifact_status": {
        "annotations": {"reason": None, "status": "present"},
        "repo_closure": {"reason": None, "status": "present"},
        "traceability_lineage": {"reason": None, "status": "present"},
        "validation_backtest": {"reason": None, "status": "present"},
    },
    "available_reports": available_reports,
    "country_coverage_visibility": {
        "country_freshness_rows": [
            {
                "country_id": cid,
                "freshness_band": "stale",
                "freshness_hours": 8760.0,
                "priority": PRIORITY_MAP[cid],
                "source_depth_band": "moderate",
            }
            for cid in all_ids
        ],
        "country_gap_rows": [],
        "freshness_band_summary": [
            {"band": "fresh", "countries": [], "country_count": 0},
            {"band": "aging", "countries": [], "country_count": 0},
            {"band": "stale", "countries": all_ids, "country_count": len(all_ids)},
            {"band": "unknown", "countries": [], "country_count": 0},
        ],
        "missing_domain_totals": {},
        "priority_summary": [
            {"countries": p1_ids, "country_count": len(p1_ids), "priority": "P1"},
            {"countries": p2_ids, "country_count": len(p2_ids), "priority": "P2"},
            {"countries": p3_ids, "country_count": len(p3_ids), "priority": "P3"},
        ],
        "remediation_watchlist": [],
        "source_depth_band_summary": [
            {"band": "minimal", "countries": [], "country_count": 0},
            {"band": "moderate", "countries": all_ids, "country_count": len(all_ids)},
            {"band": "deep", "countries": [], "country_count": 0},
        ],
    },
    "coverage": {
        "countries_total": len(all_ids),
        "countries_with_updates": len(all_ids),
        "countries_without_updates": [],
    },
    "data_gaps": [],
    "failed_sources": [],
    "last_run": "RUN-LIVE-20260520-2021",
    "reprocessing_status": "idle",
    "run_id": "RUN-LIVE-20260520-2021",
    "run_status": "success",
    "snapshot_id": "SNAP-RUN-LIVE-20260520-2021-v1",
    "top_status_changes": [],
}

ss_path = BASE / "readmodels" / "system_status.json"
with open(ss_path, "w", encoding="utf-8") as f:
    json.dump(system_status, f, indent=2, ensure_ascii=False)
print(f"Updated: {ss_path}")

print(f"\n✓ world_map: {len(all_ids)} countries")
print(f"✓ system_status: {len(available_reports)} available_reports")
print(f"  P1: {p1_ids}")
print(f"  P2: {p2_ids}")
print(f"  P3: {p3_ids}")
