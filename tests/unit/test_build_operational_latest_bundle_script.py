from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_script_module():
    script_path = Path(__file__).resolve().parents[2] / "scripts" / "build_operational_latest_bundle.py"
    spec = importlib.util.spec_from_file_location("build_operational_latest_bundle_script", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_build_operational_latest_bundle_script_threads_policy_gate_override(monkeypatch, capsys) -> None:
    module = _load_script_module()
    calls: list[dict[str, object]] = []

    def fake_build_operational_latest_bundle(**kwargs):
        calls.append(kwargs)
        return {
            "run_status": "partial_success",
            "pilot_set": kwargs["pilot_set"],
            "artifacts_dir": str(kwargs["artifacts_dir"]),
            "gui_index": str(kwargs["gui_output_dir"] / "index.html"),
            "history_db": str(kwargs["history_db_path"]),
        }

    monkeypatch.setattr(module, "build_operational_latest_bundle", fake_build_operational_latest_bundle)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "build_operational_latest_bundle.py",
            "--run-id",
            "RUN-OP-LATEST-CLI-001",
            "--allow-policy-gate-fail",
        ],
    )

    assert module.main() == 0

    assert calls == [
        {
            "repo_root": Path("."),
            "run_id": "RUN-OP-LATEST-CLI-001",
            "pilot_set": module.DEFAULT_OPERATIONAL_LATEST_PILOT_SET,
            "artifacts_dir": Path("build/run_artifacts/latest"),
            "gui_output_dir": Path("build/local_gui/latest"),
            "history_db_path": Path("build/run_history/latest_runs.sqlite"),
            "allow_partial_success": False,
            "allow_failed_sources": False,
            "allow_policy_gate_fail": True,
        }
    ]
    stdout = capsys.readouterr().out
    assert "run_status=partial_success" in stdout
    assert "pilot_set=extended-focus-complete" in stdout
