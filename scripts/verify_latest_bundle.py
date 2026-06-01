from __future__ import annotations

import argparse
import json
from pathlib import Path

from siasa.runs.latest_bundle_verification import verify_latest_bundle


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SIASA build/run_artifacts/latest bundle")
    parser.add_argument("--artifacts-dir", default="build/run_artifacts/latest", help="Path to latest artifacts directory")
    parser.add_argument(
        "--allow-partial-success",
        action="store_true",
        help="Accept run_status=partial_success in addition to success.",
    )
    parser.add_argument(
        "--allow-failed-sources",
        action="store_true",
        help="Allow non-empty failed_sources list when run_status is acceptable.",
    )
    args = parser.parse_args()

    summary = verify_latest_bundle(
        Path(args.artifacts_dir),
        allow_partial_success=args.allow_partial_success,
        allow_failed_sources=args.allow_failed_sources,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
