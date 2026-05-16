# SIASA Stakeholder-Fulfillment Roadmap

> For Hermes: execute serially, one work package at a time, with TDD, validation, commit, and push after each completed package.

Goal: turn the current requirements-driven SIASA MVP baseline into a program that substantively satisfies the stakeholder GUI and analyst-workflow expectations, not only the current static read-model baseline.

Architecture: the backend/artifact core is already significantly stronger than the GUI. The roadmap therefore separates three layers: (1) analytical core and governed artifacts, (2) artifact completeness and end-to-end run outputs, (3) rich analyst GUI behavior and visual interaction. Work should continue in that order to avoid building a visually impressive GUI on top of incomplete runtime evidence.

Tech stack: Python 3.11+, pytest, static HTML GUI generator, governed YAML V-model artifacts, repository-local traceability workflow.

---

## 1. Current state matrix: what exists vs what is still missing

| Area | Stakeholder expectation | Current implementation state | Evidence / notes | Gap classification |
| --- | --- | --- | --- | --- |
| World overview / world map | World map, anomaly overview, drill-down | Partially present | Static HTML overview table exists; no real map rendering | Missing visual layer |
| Country coverage breadth | Many governed countries visible and explorable | Weak | Current demo payload shows UKR + POL; current latest artifact bundle shows only UKR in `world_map.json` | Missing artifact population |
| Real source access | Productive access to genuine external data sources | Weak | Source catalog and adapter framework exist, but no concrete live source adapter implementations are present in `src/siasa/adapters/`; several sources are explicitly only `Prepared Adapter` or require API access/registration | Foundational access gap |
| Country drill-down | Country profile reachable from overview | Present | Working drill-down for generated country pages; dead links suppressed | Mostly done |
| Country explanation | Why-country explanation, drivers, counter-indicators, uncertainty | Present | Explanation summary + grouped explanation sections implemented | Mostly done |
| Domain deep dive | Domain A/B/D detail pages | Present but selective | Domain detail pages exist only where read models are generated | Partial coverage |
| Graphs / plots | Graphs, chart-based trends, anomaly visuals | Absent | Time series shown as text/JSON blocks, not charts | Missing feature |
| Real world map visualization | Colored geographic map | Absent | No map widget, no geo rendering | Missing feature |
| Filters / controls | Domain/time/baseline switching, exploratory controls | Absent | Static pages only, mostly links | Missing feature |
| Cross-country comparison | Compare multiple countries | Absent | No dedicated comparison mode/page | Missing feature |
| Source / coverage trust layer | Source status, confidence, failures, gaps | Present | Trust summary, degraded sources, failures, missing sources visible | Mostly done |
| Source lineage / epidemiology visualization | Spread / amplification / source graph | Absent | Only traceability table exists | Missing feature |
| Reports / exports | Daily snapshot + manual exports with evidence context | Present | Export page and exported files exist | Mostly done |
| Validation / backtest review | Validation cases and expected-vs-observed review | Present in GUI baseline, incomplete in artifacts | Validation page exists; latest artifact bundle still lacks `validation_backtest.json` | Artifact gap |
| Analyst annotations visibility | Show analyst annotations in GUI | Present | Dedicated page and contextual rendering exist | Mostly done |
| Annotation creation/editing in GUI | Create/manage annotations in GUI | Absent | Read-only visibility only | Missing feature |
| Traceability / lineage | Follow evidence path from source to status/report | Present | Traceability page exists and artifact path is implemented | Mostly done |
| Release/demo readiness | Explicit readiness page and machine-readable status | Present | `readiness.html` + `readiness.json` implemented | Done, still depends on artifact completeness |
| Role-based UI behavior | Role-specific available functions | Mostly absent | Hooks exist in software requirements area, but no real GUI behavior exposed | Missing feature |
| GUI richness | Dashboard-like analyst tool instead of static report pages | Absent | Current GUI is a static HTML bundle viewer | Missing feature |

---

## 2. Important interpretation for future work

The current program is not “nothing”; it is also not “the intended full product.”

What is already strong:
- governed requirements, traceability, tests, and repo closure
- core analytical artifact generation
- reporting/export baseline
- snapshot/lineage/governance/readiness structure
- stable static GUI baseline for core analyst flows

What is still weak:
- artifact completeness in the regular `latest` bundle
- country breadth in actual generated runs
- rich GUI interaction and visual analytics
- several stakeholder GUI ambitions are only structurally represented, not truly fulfilled in the product experience

Therefore the next work must not be random GUI polishing. It should follow a staged closure path.

---

## 3. Recommended target operating model

To get from the current state to stakeholder fulfillment, work in 5 serial program increments:

0. Real-source-access readiness
1. Artifact-complete MVP
2. Data-complete country coverage MVP
3. Visual analyst GUI MVP
4. Advanced stakeholder features / extended analytics

Only after (0), (1), and (2) does it make sense to invest heavily in (3).

## 3a. Current execution status snapshot

Current repo-evidenced status on branch `hermes/repo-scaffold`:

- P0 is materially advanced:
  - source-access assessment exists
  - real adapter baselines exist for World Bank, GDELT DOC, GDELT Events, and GDACS
  - governed live runtime pilot exists
- P1 is still not fully closed:
  - latest bundle still lacks `readmodels/validation_backtest.json`
  - readiness still reports `missing_validation_artifact`
- P2 is partly closed, but not yet stakeholder-complete:
  - multi-country runtime/artifact path works
  - latest bundle currently proves `POL` and `UKR`
  - this is operationally meaningful, but still not representative breadth
- P3 is strongly advanced:
  - artifact-backed trend charts exist
  - world-map visualization exists
  - controls exist and are interactive
  - cross-country comparison exists
  - coverage/confidence/uncertainty visualization exists
  - semantic view projections and trend event overlays exist
- P4 is now partly advanced:
  - source-gap transparency is visible through country gap watchlists, remediation watchlists, priority/depth summaries, and freshness overlays in overview/map-facing views
  - analyst annotation create/edit workflow is still absent
  - baseline/historical comparison overlays beyond the current trend view are still open

Interpretation:
- the old roadmap order was correct as a program scaffold
- however, execution has now overtaken parts of the document
- the critical remaining gap is no longer “basic GUI existence”, but the mismatch between a relatively rich GUI and still-incomplete runtime breadth / validation completeness

## 3b. Updated planning horizon

For time planning, the remaining work should be treated in three bands rather than as one flat backlog:

- Near-term closure band:
  - close the remaining runtime honesty gaps that still block a clean readiness claim
- Mid-term breadth band:
  - expand from the current 2-country proof to a representative MVP country subset
- Later analyst-depth band:
  - add operational annotation workflows and the first advanced source-intelligence features

Practical recommendation for serial pacing:
- 1 small cleanup package
- 2 to 4 medium runtime/breadth packages
- then 2 larger analyst-workflow/content packages

---

## 4. Serial implementation roadmap

## Phase P0: Establish real-source-access readiness

Objective: determine which stakeholder-relevant external sources are actually accessible now, which require credentials/registration/legal clarification, and which can be integrated first as real governed MVP inputs.

### P0-WP-001: Source-by-source access and integration assessment
Objective: classify each candidate source as (a) directly accessible now, (b) accessible after API key / registration setup, (c) legally or operationally constrained, or (d) intentionally deferred.

Expected outcome:
- no ambiguity about whether SIASA currently runs on demo data or real live inputs
- a governed source-access matrix exists for implementation planning
- first real-source integration candidates are selected on evidence, not assumption

Likely files:
- `vmodel/project/data_sources.yaml`
- `docs/plans/siasa-stakeholder-fulfillment-roadmap.md`
- optional follow-up decision / assumption artifacts under `vmodel/project/`

Validation:
- each source classified with access mode and integration readiness
- explicit list of MVP-core sources that can be connected next

Assessment artifact produced:
- `docs/plans/siasa-p0-wp-001-source-access-assessment.md`

### P0-WP-002: Implement first real core source adapters
Objective: connect the first technically feasible and high-value real sources so the system starts producing governed artifacts from genuine external data rather than only demo/test payloads.

Recommended first candidates:
- GDELT
- ReliefWeb or UCDP GED
- World Bank Indicators API

Expected outcome:
- at least one end-to-end run uses real fetched source data
- real source identifiers replace purely synthetic `SRC-A` / `SRC-B` placeholders in the first governed slice
- creates the basis for meaningful multi-country artifact generation in P2

Likely files:
- `src/siasa/adapters/`
- `src/siasa/runs/orchestrator.py`
- `src/siasa/runs/artifacts.py`
- source catalog / governance artifacts under `vmodel/`
- unit tests for adapter and orchestrator integration

Validation:
- adapter-level fetch tests
- governed run with real-source metadata
- resulting artifact bundle shows real source provenance

---

## Phase P1: Close remaining artifact and runtime completeness gaps

Objective: make the `build/run_artifacts/latest` bundle complete enough that the readiness view reflects real system capability instead of missing runtime outputs.

### P1-WP-001: Always emit validation artifact when validation support is configured
Objective: ensure `validation_backtest.json` is consistently generated or explicitly omitted under governed conditions.

Expected outcome:
- readiness no longer blocks on `missing_validation_artifact` for normal governed runs
- validation page works from real latest artifacts, not only demo/test payloads

Likely files:
- `src/siasa/runs/artifacts.py`
- `src/siasa/readmodels/validation_backtest.py`
- `tests/unit/test_run_artifacts.py`
- `tests/unit/test_local_gui.py`

Validation:
- targeted artifact test
- latest bundle GUI build
- readiness page must no longer report `missing_validation_artifact` when validation inputs exist

### P1-WP-002: Make latest bundle explicitly report why optional artifacts are absent
Objective: distinguish “not implemented”, “not configured”, and “no input data” for optional artifacts.

Expected outcome:
- readiness gaps become operationally meaningful
- avoids ambiguity in demos and acceptance review

Likely files:
- `src/siasa/runs/artifacts.py`
- `src/siasa/gui/local_app.py`
- `tests/unit/test_run_artifacts.py`
- `tests/unit/test_local_gui.py`

---

## Phase P2: Expand actual country/data coverage so the GUI reflects a real multi-country system

Objective: ensure the generated artifacts contain more than a toy subset of countries.

### P2-WP-001: Diagnose why latest bundle currently contains only UKR
Objective: determine whether the limitation comes from fixture data, orchestrator setup, country-set selection, or missing source data propagation.

Expected outcome:
- root cause documented
- a controlled path to multi-country artifact generation

Likely files:
- `src/siasa/runs/orchestrator.py`
- `src/siasa/runs/artifacts.py`
- country-set/config artifacts under `vmodel/` and config loaders
- `tests/unit/test_run_orchestrator.py`
- `tests/unit/test_run_artifacts.py`

### P2-WP-002: Generate a representative multi-country artifact bundle
Objective: make latest artifacts contain a meaningful MVP subset of countries, not only UKR.

Expected outcome:
- world overview becomes product-like
- readiness/demo can use real multi-country evidence
- user can understand breadth of the system from the GUI

Success criteria:
- `world_map.json` contains a representative multi-country set
- multiple country profiles generated
- country deep dives exist for more than one country

---

## Phase P3: Upgrade static HTML baseline into a true analyst-facing GUI

Objective: move from “static report bundle” to “usable analyst tool”.

### P3-WP-001: Real chart rendering for trends and domain detail
Objective: replace JSON/text-only data blocks with actual visual charts.

Expected outcome:
- Yearly Trend Page becomes visually meaningful
- Domain detail becomes easier to interpret

Likely files:
- `src/siasa/gui/local_app.py`
- possibly add lightweight chart assets or embedded JS
- `tests/unit/test_local_gui.py`

### P3-WP-002: World map visualization layer
Objective: replace the current overview table-only entry with a real visual map representation.

Expected outcome:
- stakeholder expectation for map-based entry view is materially met
- anomaly discovery becomes intuitive

Important constraint:
- keep static/local-first execution unless requirements force a richer web app stack

### P3-WP-003: Filter and mode controls
Objective: add at least the highest-value controls:
- domain selection
- baseline mode selection
- time-window selection

Expected outcome:
- GUI supports exploration, not only reading

### P3-WP-004: Cross-country comparison page
Objective: support comparative analysis across countries.

Expected outcome:
- closes one major stakeholder gap
- helps justify multi-country backend breadth once P2 is done

### P3-WP-005: Annotation workflows beyond read-only visibility
Objective: add creation/edit/edit-history handling for analyst annotations.

Expected outcome:
- analyst role becomes operational in the GUI, not only visible in stored artifacts

---

## Phase P4: Extended stakeholder features

Objective: close the sophisticated but lower-priority stakeholder expectations after the core analyst product is already usable.

### Candidate work packages
- Source lineage / epidemiology visualization
- global comparison mode vs relative-baseline mode
- visual overlays for confidence / coverage / data gaps
- richer role-aware UI behavior
- source-dependency and information-spread visualizations
- advanced report authoring / custom export workflows

These should come after P1–P3, not before.

---

## 5. Concrete recommended next execution order

The old order should now be updated to the current repo state.

Recommended serial order from here:

1. P3-WP-005 — annotation create/edit workflows
   - size: medium to large
   - reason: this is now the main remaining analyst-workflow gap inside the GUI layer
2. P4-WP-002 — baseline / historical comparison overlays on trends and domain views
   - size: medium
   - reason: strengthens anomaly interpretation instead of only showing current state and freshness
3. P4-WP-003 — source-dependency / source-origin groundwork
   - size: large
   - reason: this opens the door to stakeholder categories F/G/H without overclaiming today
4. broader live-source/runtime hardening beyond the current governed pilot subset
   - size: medium to large
   - reason: remaining operational issues are now mostly source/runtime robustness rather than missing GUI transparency structure

Suggested planning cadence:
- next work package: annotation workflow closure
- following 1 to 2 work packages: richer interpretation overlays
- after that: source-origin / dependency groundwork and runtime hardening

This updated order is recommended because breadth, transparency, and core GUI usability are now materially stronger than this document originally assumed.

---

## 6. Definition of “stakeholder requirements all fulfilled” for this repo

For this project, we should only claim broad stakeholder fulfillment when all of the following are true:

1. Runtime/artifact completeness
- latest bundle contains the governed evidence artifacts consistently

2. Representative breadth
- multiple countries are present in real runs and GUI output

3. Core analyst usability
- anomaly discovery, country deep dive, source trust review, report export, validation review all work from real artifacts

4. Visual fulfillment
- world map and graphs are real visualizations, not placeholder tables/JSON dumps

5. Interactive fulfillment
- key stakeholder controls exist in the GUI

6. Extended transparency
- traceability, uncertainty, annotations, and evidence path remain first-class and visible

Only then is the program close to the stakeholder intent, not merely the current MVP baseline.

---

## 7. Immediate recommendation

Next serial work package should be: P1-WP-001.

Current rationale:
- latest artifact-backed readiness still shows `missing_validation_artifact`
- this is the cleanest remaining mismatch between visible GUI maturity and actual runtime completeness
- it is smaller and lower-risk than immediately pushing breadth or advanced analytics
- once closed, the roadmap can move into breadth expansion with a cleaner release baseline

After that, proceed directly with P1-WP-002 and then the first breadth package (P2-WP-003).
