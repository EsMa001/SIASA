from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

import yaml


TraceabilitySliceResult = dict[str, Any]


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected top-level mapping in {path}")
    return data


def _load_trace_links(repo_root: Path) -> list[dict[str, Any]]:
    payload = _load_yaml(repo_root / "vmodel" / "traceability" / "trace_links.yaml")
    links = payload.get("traceability", {}).get("links", [])
    if not isinstance(links, list):
        raise ValueError("traceability.links must be a list")
    return [link for link in links if isinstance(link, dict)]


def load_traceability_slice_definition(*, repo_root: Path, slice_id: str) -> dict[str, Any]:
    payload = _load_yaml(repo_root / "vmodel" / "traceability" / "implementation_file_links.yaml")
    slices = payload.get("implementation_slices", {})
    if not isinstance(slices, dict):
        raise ValueError("implementation_slices must be a mapping")
    slice_definition = slices.get(slice_id)
    if not isinstance(slice_definition, dict):
        raise ValueError(f"Traceability slice {slice_id} is not defined")
    return {
        "requirement_ids": [str(item) for item in slice_definition.get("requirement_ids", [])],
        "implementation_map": {
            str(requirement_id): {
                "code_paths": [str(path) for path in mapping.get("code_paths", [])],
                "test_paths": [str(path) for path in mapping.get("test_paths", [])],
            }
            for requirement_id, mapping in slice_definition.get("implementation_map", {}).items()
            if isinstance(mapping, dict)
        },
        "known_code_paths": [str(path) for path in slice_definition.get("known_code_paths", [])],
        "known_test_paths": [str(path) for path in slice_definition.get("known_test_paths", [])],
    }


def _build_trace_index(trace_links: list[dict[str, Any]]) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[str]]]:
    by_source: dict[str, list[dict[str, Any]]] = defaultdict(list)
    requirement_to_tests: dict[str, list[str]] = defaultdict(list)
    for link in trace_links:
        source_id = str(link.get("source_id", ""))
        by_source[source_id].append(link)
        if str(link.get("relation")) != "verifies":
            continue
        for target_id in link.get("target_ids", []):
            target = str(target_id)
            if target.startswith("SwR-"):
                requirement_to_tests[target].append(source_id)
    return dict(by_source), dict(requirement_to_tests)


def validate_traceability_slice(
    *,
    repo_root: Path,
    requirement_ids: list[str],
    implementation_map: dict[str, dict[str, list[str]]],
    known_code_paths: list[str] | None = None,
    known_test_paths: list[str] | None = None,
) -> TraceabilitySliceResult:
    trace_links = _load_trace_links(repo_root)
    links_by_source, requirement_to_tests = _build_trace_index(trace_links)

    missing_requirements: list[str] = []
    missing_trace_links: list[str] = []
    missing_code_paths: dict[str, list[str]] = {}
    missing_test_paths: dict[str, list[str]] = {}
    missing_files: list[str] = []
    reverse_index: dict[str, list[str]] = defaultdict(list)

    for requirement_id in requirement_ids:
        requirement_entry = implementation_map.get(requirement_id)
        if requirement_entry is None:
            missing_requirements.append(requirement_id)
            continue

        requirement_links = links_by_source.get(requirement_id, [])
        verifying_tests = requirement_to_tests.get(requirement_id, [])
        if not requirement_links or not verifying_tests:
            missing_trace_links.append(requirement_id)

        code_paths = [str(path) for path in requirement_entry.get("code_paths", [])]
        test_paths = [str(path) for path in requirement_entry.get("test_paths", [])]

        if not code_paths:
            missing_code_paths[requirement_id] = []
        if not test_paths:
            missing_test_paths[requirement_id] = verifying_tests

        for relative_path in code_paths + test_paths:
            absolute_path = repo_root / relative_path
            if not absolute_path.exists():
                missing_files.append(relative_path)
            reverse_index[relative_path].append(requirement_id)

    tracked_code_paths = sorted({path for entry in implementation_map.values() for path in entry.get("code_paths", [])})
    tracked_test_paths = sorted({path for entry in implementation_map.values() for path in entry.get("test_paths", [])})
    known_code_paths = sorted(set(known_code_paths or tracked_code_paths))
    known_test_paths = sorted(set(known_test_paths or tracked_test_paths))

    unmapped_code_paths = [path for path in known_code_paths if path not in reverse_index]
    unmapped_test_paths = [path for path in known_test_paths if path not in reverse_index]

    return {
        "requirement_ids": list(requirement_ids),
        "missing_requirements": sorted(missing_requirements),
        "missing_trace_links": sorted(missing_trace_links),
        "missing_code_paths": missing_code_paths,
        "missing_test_paths": missing_test_paths,
        "missing_files": sorted(set(missing_files)),
        "requirement_to_tests": {requirement_id: requirement_to_tests.get(requirement_id, []) for requirement_id in requirement_ids},
        "reverse_index": {path: sorted(requirement_ids) for path, requirement_ids in reverse_index.items()},
        "unmapped_code_paths": unmapped_code_paths,
        "unmapped_test_paths": unmapped_test_paths,
    }
