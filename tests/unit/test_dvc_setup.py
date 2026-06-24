"""Tests for AP-13.5 — DVC-Setup und Versionierung.

Verifies:
- SwR-061: DVC initialization and pipeline definition consistency
  - .dvc/ directory exists with valid config
  - dvc.yaml defines the 4-stage pipeline (ingest, archive, features, training)
  - data/.gitignore excludes DVC-tracked directories
  - Pipeline stages have correct dependency chain
"""
from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_dvc_directory_exists() -> None:
    """.dvc/ directory must exist after dvc init."""
    assert (REPO_ROOT / ".dvc").is_dir(), ".dvc/ directory missing — run 'dvc init'"


def test_dvc_gitignore_exists() -> None:
    """.dvc/.gitignore must exist to exclude local cache."""
    gitignore = REPO_ROOT / ".dvc" / ".gitignore"
    assert gitignore.is_file()
    content = gitignore.read_text()
    assert "/tmp" in content
    assert "/cache" in content


def test_dvc_yaml_exists_and_is_valid() -> None:
    """dvc.yaml must exist and be valid YAML."""
    dvc_yaml = REPO_ROOT / "dvc.yaml"
    assert dvc_yaml.is_file(), "dvc.yaml missing"
    pipeline = yaml.safe_load(dvc_yaml.read_text())
    assert "stages" in pipeline


def test_dvc_pipeline_has_four_stages() -> None:
    """dvc.yaml must define the 4-stage pipeline: ingest, archive, features, training."""
    pipeline = yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text())
    stages = set(pipeline["stages"].keys())
    expected = {"ingest", "archive", "features", "training"}
    assert expected.issubset(stages), f"Missing stages: {expected - stages}"


def test_dvc_pipeline_stages_have_cmd() -> None:
    """Every pipeline stage must have a cmd field."""
    pipeline = yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text())
    for stage_name, stage_config in pipeline["stages"].items():
        assert "cmd" in stage_config, f"Stage '{stage_name}' missing cmd"


def test_dvc_pipeline_dependency_chain() -> None:
    """Pipeline stages must form a dependency chain: ingest → archive → features → training."""
    pipeline = yaml.safe_load((REPO_ROOT / "dvc.yaml").read_text())
    stages = pipeline["stages"]

    # archive depends on ingest output
    archive_deps = [str(d) for d in stages["archive"].get("deps", [])]
    assert any("run_artifacts" in d or "archive" in d for d in archive_deps), \
        f"archive stage must depend on ingest output, got: {archive_deps}"

    # features depends on archive output
    features_deps = [str(d) for d in stages["features"].get("deps", [])]
    assert any("archive" in d for d in features_deps), \
        f"features stage must depend on archive output, got: {features_deps}"

    # training depends on features output
    training_deps = [str(d) for d in stages["training"].get("deps", [])]
    assert any("features" in d for d in training_deps), \
        f"training stage must depend on features output, got: {training_deps}"


def test_data_gitignore_excludes_dvc_dirs() -> None:
    """data/.gitignore must exclude DVC-tracked directories."""
    gitignore = REPO_ROOT / "data" / ".gitignore"
    assert gitignore.is_file(), "data/.gitignore missing"
    content = gitignore.read_text()
    assert "/archive/" in content
    assert "/features/" in content
    assert "/training/" in content
