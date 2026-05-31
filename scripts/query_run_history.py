from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.data.storage import load_recent_runs, load_source_results_for_run, load_country_domain_time_series, load_latest_country_scores


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect SIASA operational latest run-history SQLite")
    parser.add_argument("--history-db", default="build/run_history/latest_runs.sqlite", help="Path to SQLite run-history DB")
    parser.add_argument("--limit", type=int, default=10, help="Number of recent runs to return")
    parser.add_argument("--run-id", default=None, help="Optional run_id to include source-level results")
    parser.add_argument("--country", default=None, help="Country ID for domain score queries (e.g. UKR)")
    parser.add_argument("--domain", default=None, help="Domain for time-series query (e.g. A, B, D)")
    args = parser.parse_args()

    db_path = Path(args.history_db)
    payload: dict = {"history_db": str(db_path)}

    if args.country and args.domain:
        ts = load_country_domain_time_series(db_path, country_id=args.country, domain=args.domain, limit=args.limit)
        payload["time_series"] = [entry.__dict__ for entry in ts]
    elif args.country:
        latest = load_latest_country_scores(db_path, country_id=args.country)
        payload["latest_country_scores"] = [entry.__dict__ for entry in latest]
    else:
        recent_runs = [entry.__dict__ for entry in load_recent_runs(db_path, limit=args.limit)]
        payload["recent_runs"] = recent_runs

    if args.run_id:
        payload["source_results"] = [
            entry.__dict__ for entry in load_source_results_for_run(db_path, run_id=args.run_id)
        ]

    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
