# SIASA Level 3 – User-Value-Flow Plan

> For Hermes: Execute this plan serially, one work package at a time, with TDD, validation, commit, and push after each completed package.

Goal: Re-prioritize the next SIASA delivery steps by user value and operational usability instead of only by technical component completeness.

Architecture: The codebase now has broad software-requirement coverage and a functioning static local GUI baseline. The next phase should therefore optimize for end-to-end user flows: discover anomalous countries, explain one country, inspect data quality, export evidence, and validate system behavior. The planning axis is no longer subsystem-first but analyst workflow-first.

Tech stack: Python 3.11+, pytest, static HTML GUI generator, governed YAML V-model artifacts, repository-local traceability workflow.

---

## Current context

Validated current baseline:
- broad governed Requirement -> Code -> Test closure is in place
- local static GUI bundle is generated and navigation-hardening was added
- GUI navigation dead-link and relative-path regressions are covered by tests
- current suite is green at the time of planning

Important implication:
- Level 1 improved practical GUI robustness
- Level 2 tightened requirements/verification to better reflect usability expectations
- Level 3 should now decide what to build next based on analyst value, not only architectural neatness

## Source artifacts used for this prioritization

- `docs/project/use_cases.md`
- `docs/ui/gui_pages.md`
- `docs/verification/acceptance_criteria.md`
- `vmodel/project/implementation_workpackages.yaml`
- `vmodel/requirements/system_requirements.yaml`
- `vmodel/requirements/software_requirements.yaml`

## Prioritization principle

Primary ranking criterion:
1. frequency and importance of analyst use
2. evidence/explainability value per additional implementation step
3. gap between currently possible and operationally useful behavior
4. dependency risk

This yields the following user-flow order:
1. UC-001 Daily Global Review
2. UC-002 Country Deep Dive
3. UC-003 Source/Coverage Review
4. UC-004 Report Export
5. UC-005 Backtest / Validation
6. UC-006 Rule Tuning

## Product recommendation

Do not expand the system uniformly across all pages.
Instead, concentrate the next cycle on making the first four MVP user flows operationally strong and demo-safe.

Recommendation:
- Cycle A: UC-001 + UC-002
- Cycle B: UC-003 + UC-004
- Cycle C: UC-005
- defer UC-006 until the first analyst workflow is stable enough to justify controlled tuning

---

## Work Package L3-WP-001: Daily Global Review operational hardening

Objective: Make the landing flow strong enough that an analyst can open the system, identify anomalies, and select supported drill-down targets with confidence.

Why first:
- default entry point
- highest discovery value
- strongest demo impact
- unlocks confidence in the rest of the GUI

Use cases:
- `UC-001`

Acceptance criteria most directly affected:
- `AC-008`
- `AC-011` (partially, via visible data gaps / failed sources)

Likely files to change:
- `src/siasa/gui/local_app.py`
- `src/siasa/readmodels/world_map.py`
- `src/siasa/readmodels/system_status.py`
- `tests/unit/test_local_gui.py`
- `tests/unit/test_run_artifacts.py`
- `docs/verification/acceptance_criteria.md` only if additional behavior must be clarified

Product outcomes:
- top status changes on the landing flow
- clearly visible unsupported / unavailable drill-down cases
- visible data-gap or failed-source context directly on overview entry flow
- no ambiguity whether a country is selectable, partially supported, or unsupported

Validation:
- targeted GUI tests for world overview states
- artifact-backed GUI generation test
- browser smoke through landing page and one supported drill-down

---

## Work Package L3-WP-002: Country Deep Dive explanation completeness

Objective: Make the Country Profile strong enough to answer “why is this country in this state?” without switching to raw artifacts.

Why second:
- most important explanatory user flow
- follows directly from anomaly discovery
- highest analyst value per page after the landing flow

Use cases:
- `UC-002`

Acceptance criteria most directly affected:
- `AC-009`
- `AC-010` (shared with domain detail)
- `AC-012` (annotation visibility where relevant)

Likely files to change:
- `src/siasa/gui/local_app.py`
- `src/siasa/readmodels/country_profile.py`
- `src/siasa/readmodels/domain_detail.py`
- `tests/unit/test_local_gui.py`
- `tests/unit/test_run_artifacts.py`

Product outcomes:
- explicit explanation grouping: drivers, counter-indicators, uncertainty, linked events
- clearer handoff from Country Profile to Domain Detail A/B/D
- annotation details visible in context, not only by ID
- stable back-navigation and cross-page context retention in the static GUI model

Validation:
- GUI tests for explanation sections
- generated-country-page link checks to domain pages
- browser smoke: index -> country -> back home

---

## Work Package L3-WP-003: Source/Coverage Review as trust layer

Objective: Make the data-trust flow strong enough that an analyst can decide whether a visible anomaly is well-supported.

Why third:
- directly supports interpretation quality
- reduces false confidence
- complements UC-001 and UC-002 without requiring new architectural layers

Use cases:
- `UC-003`

Acceptance criteria most directly affected:
- `AC-011`
- `AC-004` (visibility of failed sources)

Likely files to change:
- `src/siasa/gui/local_app.py`
- `src/siasa/readmodels/source_coverage.py`
- `src/siasa/readmodels/system_status.py`
- `tests/unit/test_local_gui.py`
- `tests/unit/test_run_artifacts.py`

Product outcomes:
- clearer presentation of missing sources, freshness, history depth, confidence, failures
- explicit cues about partial-success runs and trust limitations
- better connection between system-status and source/coverage reasoning

Validation:
- GUI tests for failed-source visibility and coverage presentation
- partial-success artifact bundle rendering checks

---

## Work Package L3-WP-004: Report Export usability and evidence packaging

Objective: Make report export a reliable analyst output flow rather than only an artifact dump.

Why fourth:
- high user value once anomaly discovery and explanation are stable
- enables documentation, sharing, review, and demo evidence

Use cases:
- `UC-004`

Acceptance criteria most directly affected:
- `AC-013`
- `AC-014`
- `AC-015` (partially, through export evidence clarity)

Likely files to change:
- `src/siasa/gui/local_app.py`
- `src/siasa/reporting/daily_snapshot.py`
- `src/siasa/reporting/country_report.py`
- `src/siasa/reporting/manual_reports.py`
- `src/siasa/runs/artifacts.py`
- `tests/unit/test_local_gui.py`
- `tests/unit/test_run_artifacts.py`

Product outcomes:
- export page makes available artifacts obvious and navigable
- export metadata emphasizes IDs, uncertainty, source-failure context
- stronger evidence bundle for external review/demo

Validation:
- export-link GUI tests
- artifact-bundle checks for expected report/export files

---

## Work Package L3-WP-005: Validation flow usable for analyst review

Objective: Upgrade Backtest / Validation from “prepared” to a credible review flow for curated reference cases.

Why fifth:
- valuable, but less central than daily review / deep dive / data trust / export
- more useful once core analyst interpretation flows are strong

Use cases:
- `UC-005`

Acceptance criteria most directly affected:
- `AC-016`

Likely files to change:
- `src/siasa/gui/local_app.py`
- `src/siasa/readmodels/validation_backtest.py`
- `src/siasa/validation/cases.py`
- `tests/unit/test_local_gui.py`
- `tests/unit/test_readmodels_validation_backtest.py`

Product outcomes:
- reference cases clearly visible and comparable
- expected vs observed patterns interpretable in GUI
- exportable validation evidence

Validation:
- validation-page rendering tests
- artifact-backed validation view test

---

## Explicitly deferred for now

### L3-Deferred-001: Rule Tuning UI / workflow

Reason for deferral:
- high governance risk
- lower immediate analyst value than using the system well
- should only begin once review, explanation, export, and validation flows are stable

Affected use case:
- `UC-006`

## Proposed execution order

1. L3-WP-001 Daily Global Review operational hardening
2. L3-WP-002 Country Deep Dive explanation completeness
3. L3-WP-003 Source/Coverage trust layer
4. L3-WP-004 Report Export usability
5. L3-WP-005 Validation flow usability
6. keep Rule Tuning deferred

## Definition of done for Level 3 planning

Level 3 is considered planned well enough when:
- the first four MVP analyst flows have a clear execution order
- each flow has explicit user value, affected ACs, and likely files
- the team can implement one flow at a time without reopening prioritization debates
- deferred items are explicit and justified

## Immediate recommendation

Start execution with L3-WP-001 Daily Global Review operational hardening.
It gives the highest user-visible value, improves demo readiness, and strengthens the system entry flow that all later analyst behavior depends on.
