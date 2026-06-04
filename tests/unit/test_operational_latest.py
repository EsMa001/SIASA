from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from siasa.runs.operational_latest import DEFAULT_OPERATIONAL_LATEST_PILOT_SET, build_operational_latest_bundle


@dataclass
class FakeSourceResult:
    source_id: str
    status: str
    diagnostics: str = ""


@dataclass
class FakeRunState:
    run_id: str
    status: str
    failed_sources: list[str]
    source_results: list[FakeSourceResult]


@dataclass
class FakeArtifactBundle:
    output_dir: Path


@dataclass
class FakePipelineResult:
    run_state: FakeRunState
    artifact_bundle: FakeArtifactBundle


class RecordingPipelineRunner:
    def __init__(self, result: FakePipelineResult) -> None:
        self.result = result
        self.calls: list[dict[str, object]] = []

    def __call__(self, **kwargs):
        self.calls.append(kwargs)
        return self.result


class RecordingGuiBuilder:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, *, artifacts_dir: Path, output_dir: Path) -> Path:
        self.calls.append({"artifacts_dir": artifacts_dir, "output_dir": output_dir})
        return output_dir / "index.html"


class RecordingRunHistoryWriter:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def __call__(self, db_path: Path, **kwargs) -> None:
        self.calls.append({"db_path": db_path, **kwargs})


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_minimal_artifacts(
    artifact_dir: Path,
    *,
    run_id: str,
    run_status: str,
    failed_sources: list[str],
    country_set_id: str,
) -> None:
    (artifact_dir / "readmodels" / "country_profiles").mkdir(parents=True, exist_ok=True)
    (artifact_dir / "snapshot.json").write_text(json.dumps({"snapshot_id": "SNAP-001"}), encoding="utf-8")
    (artifact_dir / "readmodels" / "system_status.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "run_status": run_status,
                "failed_sources": failed_sources,
                "country_set_id": country_set_id,
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "readmodels" / "world_map.json").write_text(
        json.dumps(
            {
                "active_domains": ["A", "B", "C", "D", "E"],
                "countries": [
                    {
                        "country_id": "UKR",
                        "status": "warning",
                        "active_domains": ["A", "B", "C", "D", "E"],
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (artifact_dir / "readmodels" / "country_profiles" / "UKR.json").write_text(
        json.dumps(
            {
                "country_id": "UKR",
                "domain_states": {"A": "D1", "B": "D1", "D": "D1", "E": "D0"},
            }
        ),
        encoding="utf-8",
    )


def _write_policy_file(repo_root: Path) -> None:
    policy_path = repo_root / "vmodel" / "project" / "live_probe_policy_profiles.yaml"
    policy_path.parent.mkdir(parents=True, exist_ok=True)
    policy_path.write_text(
        "profiles:\n"
        "  standard:\n"
        "    min_combined_ce_ratio: 0.5\n"
        "    allowed_verdicts: [green, amber]\n"
        "    max_failed_sources: 3\n",
        encoding="utf-8",
    )


def test_operational_latest_bundle_defaults_to_extended_focus_complete() -> None:
    assert DEFAULT_OPERATIONAL_LATEST_PILOT_SET == "extended-focus-complete"


def test_build_operational_latest_bundle_uses_extended_focus_complete_and_builds_gui(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    gui_dir = tmp_path / "gui"
    _write_policy_file(tmp_path)
    _write_minimal_artifacts(
        artifact_dir,
        run_id="RUN-OP-LATEST-001",
        run_status="success",
        failed_sources=[],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
    )
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(
                run_id="RUN-OP-LATEST-001",
                status="success",
                failed_sources=[],
                source_results=[
                    FakeSourceResult(source_id="WB-INDICATORS", status="success"),
                    FakeSourceResult(source_id="SRC-GDELT-DOC", status="success"),
                ],
            ),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )
    gui_builder = RecordingGuiBuilder()
    run_history_writer = RecordingRunHistoryWriter()

    result = build_operational_latest_bundle(
        repo_root=tmp_path,
        run_id="RUN-OP-LATEST-001",
        artifacts_dir=artifact_dir,
        gui_output_dir=gui_dir,
        pipeline_runner=runner,
        gui_builder=gui_builder,
        run_history_writer=run_history_writer,
    )

    assert runner.calls == [
        {
            "repo_root": tmp_path,
            "run_id": "RUN-OP-LATEST-001",
            "pilot_set": "extended-focus-complete",
            "output_dir": artifact_dir,
        }
    ]
    assert gui_builder.calls == [
        {
            "artifacts_dir": artifact_dir,
            "output_dir": gui_dir,
        }
    ]
    assert run_history_writer.calls == [
        {
            "db_path": tmp_path / "build/run_history/latest_runs.sqlite",
            "run_id": "RUN-OP-LATEST-001",
            "run_status": "success",
            "pilot_set": "extended-focus-complete",
            "artifacts_dir": artifact_dir,
            "gui_index": gui_dir / "index.html",
            "failed_sources": [],
            "source_results": [
                {"source_id": "WB-INDICATORS", "status": "success", "diagnostics": ""},
                {"source_id": "SRC-GDELT-DOC", "status": "success", "diagnostics": ""},
            ],
        }
    ]
    assert result["pilot_set"] == "extended-focus-complete"
    assert result["run_status"] == "success"
    assert result["artifacts_dir"] == artifact_dir
    assert result["gui_index"] == gui_dir / "index.html"
    assert result["history_db"] == tmp_path / "build/run_history/latest_runs.sqlite"
    assert result["policy_gate_verdict"] == "pass"
    assert result["verification_summary"]["country_set_id"] == "MVP-COUNTRIES-LIVE-extended-focus-complete-v1"
    digest = _read_json(result["digest_path"])
    assert digest["run_context"]["run_id"] == "RUN-OP-LATEST-001"
    assert digest["run_context"]["country_set_id"] == "MVP-COUNTRIES-LIVE-extended-focus-complete-v1"
    gate = _read_json(result["policy_gate_path"])
    assert gate["gate_verdict"] == "pass"


def test_build_operational_latest_bundle_fails_closed_on_non_success_run(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    _write_minimal_artifacts(
        artifact_dir,
        run_id="RUN-OP-LATEST-001",
        run_status="partial_success",
        failed_sources=["SRC-GDELT-DOC"],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
    )
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(
                run_id="RUN-OP-LATEST-001",
                status="partial_success",
                failed_sources=["SRC-GDELT-DOC"],
                source_results=[
                    FakeSourceResult(source_id="WB-INDICATORS", status="success"),
                    FakeSourceResult(source_id="SRC-GDELT-DOC", status="failed", diagnostics="timeout"),
                ],
            ),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )
    gui_builder = RecordingGuiBuilder()
    run_history_writer = RecordingRunHistoryWriter()

    try:
        build_operational_latest_bundle(
            repo_root=tmp_path,
            run_id="RUN-OP-LATEST-001",
            artifacts_dir=artifact_dir,
            gui_output_dir=tmp_path / "gui",
            pipeline_runner=runner,
            gui_builder=gui_builder,
            run_history_writer=run_history_writer,
        )
    except ValueError as exc:
        assert "run_status=partial_success" in str(exc)
        assert "allowed_statuses=['success']" in str(exc)
    else:
        raise AssertionError("Expected non-success operational latest build to fail closed")

    assert gui_builder.calls == []
    assert run_history_writer.calls == []


def test_build_operational_latest_bundle_fails_closed_on_failed_sources_even_when_status_success(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    _write_minimal_artifacts(
        artifact_dir,
        run_id="RUN-OP-LATEST-002",
        run_status="success",
        failed_sources=["SRC-GDELT-DOC"],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
    )
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(
                run_id="RUN-OP-LATEST-002",
                status="success",
                failed_sources=["SRC-GDELT-DOC"],
                source_results=[
                    FakeSourceResult(source_id="WB-INDICATORS", status="success"),
                    FakeSourceResult(source_id="SRC-GDELT-DOC", status="failed", diagnostics="timeout"),
                ],
            ),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )

    try:
        build_operational_latest_bundle(
            repo_root=tmp_path,
            run_id="RUN-OP-LATEST-002",
            artifacts_dir=artifact_dir,
            gui_output_dir=tmp_path / "gui",
            pipeline_runner=runner,
        )
    except ValueError as exc:
        assert "failed_sources=['SRC-GDELT-DOC']" in str(exc)
    else:
        raise AssertionError("Expected run with failed_sources to fail closed")


def test_build_operational_latest_bundle_allows_degraded_runtime_when_explicitly_enabled(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    gui_dir = tmp_path / "gui"
    _write_policy_file(tmp_path)
    _write_minimal_artifacts(
        artifact_dir,
        run_id="RUN-OP-LATEST-003",
        run_status="partial_success",
        failed_sources=["SRC-GDELT-DOC"],
        country_set_id="MVP-COUNTRIES-LIVE-extended-focus-complete-v1",
    )
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(
                run_id="RUN-OP-LATEST-003",
                status="partial_success",
                failed_sources=["SRC-GDELT-DOC"],
                source_results=[
                    FakeSourceResult(source_id="WB-INDICATORS", status="success"),
                    FakeSourceResult(source_id="SRC-GDELT-DOC", status="failed", diagnostics="timeout"),
                ],
            ),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )
    gui_builder = RecordingGuiBuilder()
    run_history_writer = RecordingRunHistoryWriter()

    result = build_operational_latest_bundle(
        repo_root=tmp_path,
        run_id="RUN-OP-LATEST-003",
        artifacts_dir=artifact_dir,
        gui_output_dir=gui_dir,
        allow_partial_success=True,
        allow_failed_sources=True,
        pipeline_runner=runner,
        gui_builder=gui_builder,
        run_history_writer=run_history_writer,
    )

    assert result["run_status"] == "partial_success"
    assert gui_builder.calls == [{"artifacts_dir": artifact_dir, "output_dir": gui_dir}]
    assert run_history_writer.calls[0]["failed_sources"] == ["SRC-GDELT-DOC"]
    assert result["policy_gate_verdict"] == "pass"
