from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from siasa.runs.operational_latest import DEFAULT_OPERATIONAL_LATEST_PILOT_SET, build_operational_latest_bundle


@dataclass
class FakeRunState:
    run_id: str
    status: str
    failed_sources: list[str]


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


def test_operational_latest_bundle_defaults_to_extended_focus_complete() -> None:
    assert DEFAULT_OPERATIONAL_LATEST_PILOT_SET == "extended-focus-complete"


def test_build_operational_latest_bundle_uses_extended_focus_complete_and_builds_gui(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    gui_dir = tmp_path / "gui"
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(run_id="RUN-OP-LATEST-001", status="success", failed_sources=[]),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )
    gui_builder = RecordingGuiBuilder()

    result = build_operational_latest_bundle(
        repo_root=tmp_path,
        run_id="RUN-OP-LATEST-001",
        artifacts_dir=artifact_dir,
        gui_output_dir=gui_dir,
        pipeline_runner=runner,
        gui_builder=gui_builder,
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
    assert result["pilot_set"] == "extended-focus-complete"
    assert result["run_status"] == "success"
    assert result["artifacts_dir"] == artifact_dir
    assert result["gui_index"] == gui_dir / "index.html"


def test_build_operational_latest_bundle_fails_closed_on_non_success_run(tmp_path: Path) -> None:
    artifact_dir = tmp_path / "artifacts"
    runner = RecordingPipelineRunner(
        FakePipelineResult(
            run_state=FakeRunState(run_id="RUN-OP-LATEST-001", status="partial_success", failed_sources=["SRC-GDELT-DOC"]),
            artifact_bundle=FakeArtifactBundle(output_dir=artifact_dir),
        )
    )
    gui_builder = RecordingGuiBuilder()

    try:
        build_operational_latest_bundle(
            repo_root=tmp_path,
            run_id="RUN-OP-LATEST-001",
            artifacts_dir=artifact_dir,
            gui_output_dir=tmp_path / "gui",
            pipeline_runner=runner,
            gui_builder=gui_builder,
        )
    except ValueError as exc:
        assert "run_status=partial_success" in str(exc)
        assert "SRC-GDELT-DOC" in str(exc)
    else:
        raise AssertionError("Expected non-success operational latest build to fail closed")

    assert gui_builder.calls == []
