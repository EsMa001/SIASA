from pathlib import Path

import yaml

from siasa.traceability.consistency import (
    build_repo_closure_report,
    build_requirement_closure_report,
    build_traceability_integrity_report,
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
    assert report["summary"] == {"closed": 12, "at_risk": 0}
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



def test_governed_snapshot_and_lineage_traceability_slice_definition_validates_cleanly() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    slice_definition = load_traceability_slice_definition(
        repo_root=repo_root,
        slice_id="snapshot-and-lineage",
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



def test_build_requirement_closure_report_for_snapshot_and_lineage_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="snapshot-and-lineage")

    assert report["slice_id"] == "snapshot-and-lineage"
    assert report["summary"] == {"closed": 3, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == ["SwR-025", "SwR-026", "SwR-027"]
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-025-001"]
    assert "src/siasa/snapshots/models.py" in report["requirements"][0]["code_paths"]
    assert "src/siasa/runs/artifacts.py" in report["requirements"][0]["code_paths"]
    assert "tests/unit/test_snapshot_service.py" in report["requirements"][0]["test_paths"]
    assert report["requirements"][1]["verifying_test_specs"] == ["TC-SwR-026-001"]
    assert "src/siasa/snapshots/service.py" in report["requirements"][1]["code_paths"]
    assert "src/siasa/runs/orchestrator.py" in report["requirements"][1]["code_paths"]
    assert "tests/unit/test_run_orchestrator.py" in report["requirements"][1]["test_paths"]
    assert report["requirements"][2]["verifying_test_specs"] == ["TC-SwR-027-001"]
    assert "src/siasa/traceability/lineage.py" in report["requirements"][2]["code_paths"]
    assert "tests/unit/test_run_artifacts.py" in report["requirements"][2]["test_paths"]



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

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="validation-and-backtest")

    assert report["slice_id"] == "validation-and-backtest"
    assert report["summary"] == {"closed": 13, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == ["SwR-038", "SwR-039", "SwR-084", "SwR-085", "SwR-086", "SwR-087", "SwR-088", "SwR-089", "SwR-090", "SwR-091", "SwR-092", "SwR-093", "SwR-094"]
    assert report["requirements"][0]["closure_status"] == "closed"
    assert report["requirements"][0]["trace_links_present"] is True
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-038-001"]
    assert "src/siasa/validation/cases.py" in report["requirements"][0]["code_paths"]
    assert "tests/unit/test_validation_cases.py" in report["requirements"][0]["test_paths"]
    assert report["requirements"][1]["requirement_id"] == "SwR-039"
    assert "src/siasa/readmodels/validation_backtest.py" in report["requirements"][1]["code_paths"]
    assert "tests/unit/test_readmodels_validation_backtest.py" in report["requirements"][1]["test_paths"]



def test_build_requirement_closure_report_for_catalog_and_ingestion_foundation_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="catalog-and-ingestion-foundation")

    assert report["slice_id"] == "catalog-and-ingestion-foundation"
    assert report["summary"] == {"closed": 11, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == [
        "SwR-001",
        "SwR-002",
        "SwR-003",
        "SwR-004",
        "SwR-005",
        "SwR-006",
        "SwR-007",
        "SwR-008",
        "SwR-052",
        "SwR-053",
        "SwR-054",
    ]
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-001-001"]
    assert "src/siasa/catalog/loaders.py" in report["requirements"][0]["code_paths"]
    assert "tests/unit/test_catalog_models.py" in report["requirements"][0]["test_paths"]
    assert report["requirements"][4]["closure_status"] == "closed"
    assert "src/siasa/runs/orchestrator.py" in report["requirements"][4]["code_paths"]
    assert "tests/unit/test_run_orchestrator.py" in report["requirements"][4]["test_paths"]
    assert report["requirements"][7]["requirement_id"] == "SwR-008"
    assert "src/siasa/data/raw_models.py" in report["requirements"][7]["code_paths"]
    assert "tests/unit/test_data_models.py" in report["requirements"][7]["test_paths"]



def test_build_requirement_closure_report_for_normalization_and_mapping_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="normalization-and-mapping")

    assert report["slice_id"] == "normalization-and-mapping"
    assert report["summary"] == {"closed": 2, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == ["SwR-009", "SwR-010"]
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-009-001"]
    assert "src/siasa/data/normalization_service.py" in report["requirements"][0]["code_paths"]
    assert "tests/unit/test_normalization_service.py" in report["requirements"][0]["test_paths"]
    assert report["requirements"][1]["verifying_test_specs"] == ["TC-SwR-010-001"]
    assert "src/siasa/data/normalization_mappings.py" in report["requirements"][1]["code_paths"]
    assert "src/siasa/runs/orchestrator.py" in report["requirements"][1]["code_paths"]
    assert "tests/unit/test_run_orchestrator.py" in report["requirements"][1]["test_paths"]



def test_build_requirement_closure_report_for_feature_computation_foundation_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="feature-computation-foundation")

    assert report["slice_id"] == "feature-computation-foundation"
    assert report["summary"] == {"closed": 6, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == [
        "SwR-011",
        "SwR-012",
        "SwR-013",
        "SwR-014",
        "SwR-015",
        "SwR-016",
    ]
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-011-001"]
    assert "src/siasa/features/base.py" in report["requirements"][0]["code_paths"]
    assert "tests/unit/test_features_base.py" in report["requirements"][0]["test_paths"]
    assert report["requirements"][4]["verifying_test_specs"] == ["TC-SwR-015-001"]
    assert "tests/unit/test_features_domain_a.py" in report["requirements"][4]["test_paths"]
    assert report["requirements"][5]["verifying_test_specs"] == ["TC-SwR-016-001"]
    assert "tests/unit/test_features_base.py" in report["requirements"][5]["test_paths"]



def test_build_requirement_closure_report_for_baseline_and_status_engines_slice() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_requirement_closure_report(repo_root=repo_root, slice_id="baseline-and-status-engines")

    assert report["slice_id"] == "baseline-and-status-engines"
    assert report["summary"] == {"closed": 8, "at_risk": 0}
    assert [item["requirement_id"] for item in report["requirements"]] == [
        "SwR-017",
        "SwR-018",
        "SwR-019",
        "SwR-020",
        "SwR-021",
        "SwR-022",
        "SwR-023",
        "SwR-024",
    ]
    assert report["requirements"][0]["verifying_test_specs"] == ["TC-SwR-017-001"]
    assert "src/siasa/scoring/baselines.py" in report["requirements"][0]["code_paths"]
    assert report["requirements"][3]["verifying_test_specs"] == ["TC-SwR-020-001"]
    assert "tests/unit/test_data_sufficiency.py" in report["requirements"][3]["test_paths"]
    assert report["requirements"][6]["verifying_test_specs"] == ["TC-SwR-023-001"]
    assert "src/siasa/scoring/multi_domain_status.py" in report["requirements"][6]["code_paths"]
    assert report["requirements"][7]["verifying_test_specs"] == ["TC-SwR-024-001"]
    assert "tests/unit/test_multi_domain_status.py" in report["requirements"][7]["test_paths"]



def test_build_repo_closure_report_aggregates_all_governed_slices() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_repo_closure_report(repo_root=repo_root)

    assert report["summary"] == {
        "slice_count": 12,
        "requirement_count": 94,
        "closed": 94,
        "at_risk": 0,
    }
    assert report["slice_ids"] == [
        "ap-14-kostenfreie-api-quellen",
        "ap-15-erweiterte-api-integration",
        "baseline-and-status-engines",
        "catalog-and-ingestion-foundation",
        "feature-computation-foundation",
        "governance-and-run-controls",
        "gui-readmodels-and-annotations",
        "ml-training-data-lake",
        "normalization-and-mapping",
        "reporting-and-export",
        "snapshot-and-lineage",
        "validation-and-backtest",
    ]
    assert report["slices"][0]["slice_id"] == "ap-14-kostenfreie-api-quellen"
    assert report["slices"][0]["summary"] == {"closed": 4, "at_risk": 0}
    assert report["slices"][2]["slice_id"] == "baseline-and-status-engines"
    assert report["slices"][2]["summary"] == {"closed": 8, "at_risk": 0}
    assert report["slices"][10]["slice_id"] == "snapshot-and-lineage"
    assert report["slices"][10]["summary"] == {"closed": 3, "at_risk": 0}
    assert report["slices"][11]["slice_id"] == "validation-and-backtest"
    assert report["slices"][11]["summary"] == {"closed": 13, "at_risk": 0}


def test_build_traceability_integrity_report_is_globally_clean() -> None:
    repo_root = Path(__file__).resolve().parents[2]

    report = build_traceability_integrity_report(repo_root=repo_root)

    assert report["summary"] == {
        "requirement_count": 94,
        "mapped_requirement_count": 94,
        "missing_requirement_mapping_count": 0,
        "orphan_mapped_requirement_count": 0,
        "slice_count": 12,
        "unhealthy_slice_count": 0,
        "closure_at_risk": 0,
    }
    assert report["missing_requirement_mappings"] == []
    assert report["orphan_mapped_requirements"] == []
    assert report["unhealthy_slices"] == []
    assert report["repo_closure"]["summary"] == {
        "slice_count": 12,
        "requirement_count": 94,
        "closed": 94,
        "at_risk": 0,
    }


def test_functional_stakeholder_gap_cluster_has_explicit_stakeholder_to_software_closure_paths() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    payload = yaml.safe_load((repo_root / "vmodel" / "traceability" / "trace_links.yaml").read_text(encoding="utf-8"))
    links = payload["traceability"]["links"]

    syr_to_stakeholders: dict[str, set[str]] = {}
    swr_to_syrs: dict[str, set[str]] = {}
    for link in links:
        source_id = str(link.get("source_id", ""))
        relation = str(link.get("relation", ""))
        target_ids = {str(item) for item in link.get("target_ids", [])}
        if relation == "derives_from" and source_id.startswith("SyR-"):
            syr_to_stakeholders[source_id] = target_ids
        if relation == "derives_from" and source_id.startswith("SwR-"):
            swr_to_syrs[source_id] = target_ids

    stakeholder_gap_ids = {
        "StR-001",
        "StR-002",
        "StR-004",
        "StR-007",
        "StR-024",
        "StR-025",
        "StR-135",
        "StR-136",
        "StR-137",
        "StR-138",
        "StR-139",
        "StR-140",
        "StR-141",
        "StR-142",
        "StR-226",
        "StR-227",
        "StR-228",
        "StR-229",
        "StR-230",
    }
    closure_swr_ids = {"SwR-046", "SwR-047", "SwR-048", "SwR-049", "SwR-050", "SwR-051"}

    covered_stakeholders: set[str] = set()
    for swr_id in closure_swr_ids:
        derived_syrs = swr_to_syrs[swr_id]
        for syr_id in derived_syrs:
            covered_stakeholders.update(stakeholder_gap_ids.intersection(syr_to_stakeholders.get(syr_id, set())))

    assert covered_stakeholders == stakeholder_gap_ids
