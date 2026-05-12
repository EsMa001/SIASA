from pathlib import Path

from siasa.traceability.consistency import (
    build_requirement_closure_report,
    load_traceability_slice_definition,
    validate_traceability_slice,
)


def test_validate_traceability_slice_for_gui_and_annotation_requirements() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=["SwR-032", "SwR-033", "SwR-034", "SwR-035", "SwR-036", "SwR-037"],
        implementation_map={
            "SwR-032": {
                "code_paths": ["src/siasa/readmodels/world_map.py", "src/siasa/gui/local_app.py"],
                "test_paths": ["tests/unit/test_local_gui.py"],
            },
            "SwR-033": {
                "code_paths": ["src/siasa/readmodels/country_profile.py", "src/siasa/gui/local_app.py"],
                "test_paths": ["tests/unit/test_local_gui.py"],
            },
            "SwR-034": {
                "code_paths": ["src/siasa/readmodels/domain_detail.py", "src/siasa/gui/local_app.py"],
                "test_paths": ["tests/unit/test_local_gui.py"],
            },
            "SwR-035": {
                "code_paths": ["src/siasa/readmodels/source_coverage.py", "src/siasa/gui/local_app.py"],
                "test_paths": ["tests/unit/test_local_gui.py"],
            },
            "SwR-036": {
                "code_paths": [
                    "src/siasa/annotations/models.py",
                    "src/siasa/readmodels/annotations.py",
                    "src/siasa/runs/artifacts.py",
                    "src/siasa/runs/orchestrator.py",
                    "src/siasa/gui/local_app.py",
                ],
                "test_paths": ["tests/unit/test_annotations.py", "tests/unit/test_local_gui.py", "tests/unit/test_run_artifacts.py"],
            },
            "SwR-037": {
                "code_paths": ["src/siasa/annotations/models.py", "src/siasa/gui/local_app.py", "src/siasa/runs/artifacts.py"],
                "test_paths": ["tests/unit/test_annotations.py", "tests/unit/test_run_artifacts.py"],
            },
        },
    )

    assert result["missing_requirements"] == []
    assert result["missing_trace_links"] == []
    assert result["missing_code_paths"] == {}
    assert result["missing_test_paths"] == {}
    assert result["missing_files"] == []
    assert result["unmapped_code_paths"] == []
    assert result["unmapped_test_paths"] == []
    assert result["requirement_to_tests"]["SwR-036"] == ["TC-SwR-036-001"]
    assert sorted(result["reverse_index"]["src/siasa/gui/local_app.py"]) == ["SwR-032", "SwR-033", "SwR-034", "SwR-035", "SwR-036", "SwR-037"]


def test_validate_traceability_slice_reports_missing_verification_and_reverse_mapping_gaps() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=["SwR-032"],
        implementation_map={
            "SwR-032": {
                "code_paths": ["src/siasa/readmodels/world_map.py"],
                "test_paths": [],
            }
        },
        known_code_paths=["src/siasa/readmodels/world_map.py", "src/siasa/gui/local_app.py"],
    )

    assert result["missing_test_paths"] == {"SwR-032": ["TC-SwR-032-001"]}
    assert result["unmapped_code_paths"] == ["src/siasa/gui/local_app.py"]


def test_governed_gui_annotation_traceability_slice_definition_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    slice_definition = load_traceability_slice_definition(
        repo_root=repo_root,
        slice_id="gui-readmodels-and-annotations",
    )

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=slice_definition["requirement_ids"],
        implementation_map=slice_definition["implementation_map"],
        known_code_paths=slice_definition["known_code_paths"],
        known_test_paths=slice_definition["known_test_paths"],
    )

    assert result["missing_requirements"] == []
    assert result["missing_trace_links"] == []
    assert result["missing_code_paths"] == {}
    assert result["missing_test_paths"] == {}
    assert result["missing_files"] == []
    assert result["unmapped_code_paths"] == []
    assert result["unmapped_test_paths"] == []


def test_build_requirement_closure_report_for_governed_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(
        repo_root=repo_root,
        slice_id="gui-readmodels-and-annotations",
    )

    assert report["slice_id"] == "gui-readmodels-and-annotations"
    assert report["summary"] == {"closed": 6, "at_risk": 0}
    assert report["requirements"][0]["requirement_id"] == "SwR-032"
    assert report["requirements"][0]["closure_status"] == "closed"
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-032-001"]
    assert report["requirements"][4]["requirement_id"] == "SwR-036"
    assert report["requirements"][4]["closure_status"] == "closed"
    assert "src/siasa/readmodels/annotations.py" in report["requirements"][4]["code_paths"]


def test_build_requirement_closure_report_marks_requirement_at_risk_when_verification_is_missing() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(
        repo_root=repo_root,
        slice_definition={
            "requirement_ids": ["SwR-032"],
            "implementation_map": {
                "SwR-032": {
                    "code_paths": ["src/siasa/readmodels/world_map.py"],
                    "test_paths": [],
                }
            },
            "known_code_paths": ["src/siasa/readmodels/world_map.py"],
            "known_test_paths": [],
        },
        slice_id="incomplete-slice",
    )

    assert report["summary"] == {"closed": 0, "at_risk": 1}
    assert report["requirements"] == [
        {
            "requirement_id": "SwR-032",
            "closure_status": "at_risk",
            "trace_links_present": True,
            "verifying_test_specs": ["TC-SwR-032-001"],
            "code_paths": ["src/siasa/readmodels/world_map.py"],
            "test_paths": [],
            "missing_files": [],
            "issues": ["missing_test_paths"],
        }
    ]



def test_governed_governance_and_run_controls_traceability_slice_definition_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    slice_definition = load_traceability_slice_definition(
        repo_root=repo_root,
        slice_id="governance-and-run-controls",
    )

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=slice_definition["requirement_ids"],
        implementation_map=slice_definition["implementation_map"],
        known_code_paths=slice_definition["known_code_paths"],
        known_test_paths=slice_definition["known_test_paths"],
    )

    assert result["missing_requirements"] == []
    assert result["missing_trace_links"] == []
    assert result["missing_code_paths"] == {}
    assert result["missing_test_paths"] == {}
    assert result["missing_files"] == []
    assert result["unmapped_code_paths"] == []
    assert result["unmapped_test_paths"] == []



def test_build_requirement_closure_report_for_governance_and_run_controls_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(
        repo_root=repo_root,
        slice_id="governance-and-run-controls",
    )

    assert report["slice_id"] == "governance-and-run-controls"
    assert report["summary"] == {"closed": 6, "at_risk": 0}
    assert report["requirements"][0]["requirement_id"] == "SwR-040"
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-040-001"]
    assert "src/siasa/governance/roles.py" in report["requirements"][0]["code_paths"]
    assert report["requirements"][4]["requirement_id"] == "SwR-044"
    assert "tests/unit/test_run_artifacts.py" in report["requirements"][4]["test_paths"]
    assert report["requirements"][5]["requirement_id"] == "SwR-045"
    assert report["requirements"][5]["closure_status"] == "closed"
    assert report["requirements"][5]["verifying_test_specs"] == ["TC-SwR-045-001"]
    assert "src/siasa/governance/roles.py" in report["requirements"][5]["code_paths"]
    assert "tests/unit/test_governance_guards.py" in report["requirements"][5]["test_paths"]
    assert "tests/unit/test_reprocessing_workflow.py" in report["requirements"][5]["test_paths"]



def test_governed_reporting_and_export_traceability_slice_definition_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    slice_definition = load_traceability_slice_definition(
        repo_root=repo_root,
        slice_id="reporting-and-export",
    )

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=slice_definition["requirement_ids"],
        implementation_map=slice_definition["implementation_map"],
        known_code_paths=slice_definition["known_code_paths"],
        known_test_paths=slice_definition["known_test_paths"],
    )

    assert result["missing_requirements"] == []
    assert result["missing_trace_links"] == []
    assert result["missing_code_paths"] == {}
    assert result["missing_test_paths"] == {}
    assert result["missing_files"] == []
    assert result["unmapped_code_paths"] == []
    assert result["unmapped_test_paths"] == []



def test_build_requirement_closure_report_for_reporting_and_export_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(
        repo_root=repo_root,
        slice_id="reporting-and-export",
    )

    assert report["slice_id"] == "reporting-and-export"
    assert report["summary"] == {"closed": 4, "at_risk": 0}
    assert report["requirements"][0]["requirement_id"] == "SwR-028"
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-028-001"]
    assert "src/siasa/reporting/daily_snapshot.py" in report["requirements"][0]["code_paths"]
    assert report["requirements"][2]["requirement_id"] == "SwR-030"
    assert "src/siasa/reporting/manual_reports.py" in report["requirements"][2]["code_paths"]
    assert "tests/unit/test_reporting_manual_reports.py" in report["requirements"][2]["test_paths"]
    assert report["requirements"][3]["requirement_id"] == "SwR-031"
    assert "src/siasa/governance/export_policy.py" in report["requirements"][3]["code_paths"]



def test_governed_validation_and_backtest_traceability_slice_definition_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    slice_definition = load_traceability_slice_definition(
        repo_root=repo_root,
        slice_id="validation-and-backtest",
    )

    result = validate_traceability_slice(
        repo_root=repo_root,
        requirement_ids=slice_definition["requirement_ids"],
        implementation_map=slice_definition["implementation_map"],
        known_code_paths=slice_definition["known_code_paths"],
        known_test_paths=slice_definition["known_test_paths"],
    )

    assert result["missing_requirements"] == []
    assert result["missing_trace_links"] == []
    assert result["missing_code_paths"] == {}
    assert result["missing_test_paths"] == {}
    assert result["missing_files"] == []
    assert result["unmapped_code_paths"] == []
    assert result["unmapped_test_paths"] == []



def test_build_requirement_closure_report_for_validation_and_backtest_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(
        repo_root=repo_root,
        slice_id="validation-and-backtest",
    )

    assert report["slice_id"] == "validation-and-backtest"
    assert report["summary"] == {"closed": 2, "at_risk": 0}
    assert report["requirements"][0]["requirement_id"] == "SwR-038"
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-038-001"]
    assert "src/siasa/validation/cases.py" in report["requirements"][0]["code_paths"]
    assert report["requirements"][1]["requirement_id"] == "SwR-039"
    assert "src/siasa/readmodels/validation_backtest.py" in report["requirements"][1]["code_paths"]
    assert "tests/unit/test_readmodels_validation_backtest.py" in report["requirements"][1]["test_paths"]
