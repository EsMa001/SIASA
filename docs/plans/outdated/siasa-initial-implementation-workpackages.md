# SIASA Initial Implementation Work Packages

> **For Hermes:** Use subagent-driven-development skill to implement this plan task-by-task.

**Goal:** Convert the newly derived software-requirements baseline into executable, prioritized implementation work packages for the first delivery cycle.

**Architecture:** The work packages follow the software design decomposition DDS-001..DDS-012 and prioritize the minimum end-to-end analytical backbone first: catalog/config -> adapters -> raw/normalized data -> features -> baseline/status -> snapshots -> reporting/read models -> annotation/validation/governance.

**Tech Stack:** Python 3.11+, YAML-governed requirements artifacts, pytest, repository-local V-Model-light workflow.

---

## Prioritization rationale

The software baseline now contains 45 software requirements and 12 software design elements. The first execution cycle should establish the minimum analytical spine that enables a daily run with governed inputs, explainable status generation, and reproducible snapshots.

Priority order:
1. Catalog/config baseline
2. Source adapters and failure isolation
3. Raw/normalized data layer
4. Feature computation A/B/D
5. Baseline + D0-D5 + S0-S6
6. Snapshot + traceability core
7. Reporting/read models
8. Annotation/validation/governance/reprocessing

## Work package summary

| WP | Priority | Focus | SwR count | Depends on |
|---|---|---|---:|---|
| WP-001 | P1 | Catalog and configuration baseline | 3 | - |
| WP-002 | P1 | Source adapter framework and failure isolation | 5 | WP-001 |
| WP-003 | P1 | Raw and normalized data layer | 4 | WP-001, WP-002 |
| WP-004 | P1 | Feature computation baseline for A/B/D | 6 | WP-003 |
| WP-005 | P1 | Baseline, anomaly, and status engines | 8 | WP-004 |
| WP-006 | P1 | Snapshot and traceability core | 3 | WP-002, WP-003, WP-005 |
| WP-007 | P2 | Reporting and read-model baseline | 8 | WP-006 |
| WP-008 | P2 | Annotation, validation, governance, and reprocessing controls | 8 | WP-006 |

## WP-001 Catalog and configuration baseline

**Objective:** Make source catalog, country-set, and configuration artifacts loadable and versioned in code.

**SwR:** SwR-001, SwR-002, SwR-003

**DDS:** DDS-001

**Suggested files:**
- Create: `src/siasa/catalog/models.py`
- Create: `src/siasa/catalog/loaders.py`
- Create: `tests/unit/test_catalog_models.py`
- Create: `tests/unit/test_catalog_loaders.py`

**Verification target:**
- `TC-SwR-001-001`
- `TC-SwR-002-001`
- `TC-SwR-003-001`

**Exit condition:**
- governed YAML artifacts load into validated internal models
- versioned country set and configuration tables are queryable in code

## WP-002 Source adapter framework and failure isolation

**Objective:** Create the reusable adapter interface, fetch metadata persistence, and per-source failure isolation behavior.

**SwR:** SwR-004, SwR-005, SwR-006, SwR-043, SwR-044

**DDS:** DDS-002, DDS-012

**Suggested files:**
- Create: `src/siasa/adapters/base.py`
- Create: `src/siasa/runs/run_state.py`
- Create: `src/siasa/adapters/fetch_metadata.py`
- Create: `tests/unit/test_adapter_base.py`
- Create: `tests/unit/test_run_state.py`

**Verification target:**
- adapter interface works consistently
- failed source produces `partial_success` instead of uncontrolled abort

## WP-003 Raw and normalized data layer

**Objective:** Establish raw/reference persistence, normalized analytical schema, and normalization mapping versioning.

**SwR:** SwR-007, SwR-008, SwR-009, SwR-010

**DDS:** DDS-003

**Suggested files:**
- Create: `src/siasa/data/raw_models.py`
- Create: `src/siasa/data/normalized_models.py`
- Create: `src/siasa/data/normalization_mappings.py`
- Create: `tests/unit/test_raw_models.py`
- Create: `tests/unit/test_normalized_models.py`

**Verification target:**
- raw/reference storage policy hooks are testable
- normalized records carry provenance and quality context

## WP-004 Feature computation baseline for A/B/D

**Objective:** Implement the shared feature framework and MVP feature services for domains A, B, and D.

**SwR:** SwR-011, SwR-012, SwR-013, SwR-014, SwR-015, SwR-016

**DDS:** DDS-004

**Suggested files:**
- Create: `src/siasa/features/base.py`
- Create: `src/siasa/features/domain_a.py`
- Create: `src/siasa/features/domain_b.py`
- Create: `src/siasa/features/domain_d.py`
- Create: `tests/unit/test_features_domain_a.py`
- Create: `tests/unit/test_features_domain_b.py`
- Create: `tests/unit/test_features_domain_d.py`

**Verification target:**
- shared feature computation interface exists
- A/B/D feature services emit coverage/confidence-ready outputs

## WP-005 Baseline, anomaly, and status engines

**Objective:** Implement relative baseline logic, data sufficiency evaluation, D0-D5, and S0-S6 rule engines.

**SwR:** SwR-017 .. SwR-024

**DDS:** DDS-005, DDS-006

**Suggested files:**
- Create: `src/siasa/scoring/baselines.py`
- Create: `src/siasa/scoring/data_sufficiency.py`
- Create: `src/siasa/scoring/domain_status.py`
- Create: `src/siasa/scoring/multi_domain_status.py`
- Create: `tests/unit/test_baselines.py`
- Create: `tests/unit/test_domain_status.py`
- Create: `tests/unit/test_multi_domain_status.py`

**Verification target:**
- rule tests cover D0-D5 and S0-S6
- selective C/E inclusion is governed by sufficiency rules

## WP-006 Snapshot and traceability core

**Objective:** Implement versioned snapshots and stable lineage identifiers across the analytical pipeline.

**SwR:** SwR-025, SwR-026, SwR-027

**DDS:** DDS-007

**Suggested files:**
- Create: `src/siasa/snapshots/models.py`
- Create: `src/siasa/snapshots/service.py`
- Create: `src/siasa/traceability/lineage.py`
- Create: `tests/unit/test_snapshot_models.py`
- Create: `tests/unit/test_snapshot_service.py`

**Verification target:**
- successful and partial-success runs produce versioned snapshots
- lineage identifiers connect upstream and downstream artifacts

## WP-007 Reporting and read-model baseline

**Objective:** Implement daily/global reporting and the first query-side read models for map, country profile, and source/coverage views.

**SwR:** SwR-028 .. SwR-035

**DDS:** DDS-008, DDS-009

**Suggested files:**
- Create: `src/siasa/reporting/daily_snapshot.py`
- Create: `src/siasa/reporting/country_report.py`
- Create: `src/siasa/readmodels/world_map.py`
- Create: `src/siasa/readmodels/country_profile.py`
- Create: `src/siasa/readmodels/source_coverage.py`
- Create: `tests/unit/test_reporting_daily_snapshot.py`
- Create: `tests/unit/test_readmodels_country_profile.py`

**Verification target:**
- governed report generators exist
- read models expose enough context for the defined GUI views

## WP-008 Annotation, validation, governance, and reprocessing controls

**Objective:** Implement annotation services, validation-case handling, role/governance hooks, and controlled reprocessing.

**SwR:** SwR-036 .. SwR-045 (remaining relevant set)

**DDS:** DDS-010, DDS-011, DDS-012

**Suggested files:**
- Create: `src/siasa/annotations/models.py`
- Create: `src/siasa/validation/cases.py`
- Create: `src/siasa/governance/roles.py`
- Create: `src/siasa/governance/export_policy.py`
- Create: `src/siasa/runs/reprocessing.py`
- Create: `tests/unit/test_annotations.py`
- Create: `tests/unit/test_validation_cases.py`
- Create: `tests/unit/test_governance_guards.py`

**Verification target:**
- annotation and validation services are persisted and queryable
- governance boundaries are enforced in code pathways
- reprocessing is controlled and version-aware

## Recommended execution order

Execute first delivery cycle in this order:
1. WP-001
2. WP-002
3. WP-003
4. WP-004
5. WP-005
6. WP-006
7. WP-007
8. WP-008

## Immediate recommendation

Start with WP-001 because it is low-risk, schema-driven, and unlocks every later work package.
