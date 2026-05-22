# SIASA Stakeholder-Fulfillment Roadmap

> For Hermes: execute serially, one work package at a time, with TDD, validation, commit, and push after each completed package.

Goal: turn the current requirements-driven SIASA MVP baseline into a program that substantively satisfies the stakeholder GUI and analyst-workflow expectations, not only the current static read-model baseline.

Architecture: the backend/artifact core is already significantly stronger than the GUI. The roadmap therefore separates three layers: (1) analytical core and governed artifacts, (2) artifact completeness and end-to-end run outputs, (3) rich analyst GUI behavior and visual interaction. Work should continue in that order to avoid building a visually impressive GUI on top of incomplete runtime evidence.

Tech stack: Python 3.11+, pytest, static HTML GUI generator, governed YAML V-model artifacts, repository-local traceability workflow.

---

## 1. Current state matrix: what exists vs what is still missing

For project-lead steering, use `docs/plans/siasa-project-lead-capability-matrix.md` as the operational companion to this roadmap. The roadmap stays strategic; the capability matrix tracks what is Done / Partial / Weak / Missing with evidence and work-package linkage.

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
| Validation / backtest review | Validation cases and expected-vs-observed review | Present in GUI baseline and governed artifacts | Validation page exists; latest artifact bundle carries both `validation_backtest.json` and `readiness.json`, the validation artifact exposes a curated reference-case library beside the runtime-support portfolio, surfaces historical reference-review / evidence-scoring outputs for those curated cases, carries full curated-library `provider_backed_archival_replay`, surfaces archival provenance details such as replay source coverage and archival data-file metadata, renders replay evidence score/tier plus source/provenance coverage ratios, includes governed challenge cases that produce partial and mismatch replay outcomes instead of only perfect matches, broadens the curated governed library from 4 to 21 countries / 23 cases by adding `RUS`, `CHN`, `IND`, `IRN`, `TUR`, `USA`, `DEU`, `EST`, `FIN`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`, `PAK`, and `GEO` reference cases, and exposes an analyst-facing replay attention layer with both a watchlist and an aggregated summary by level/reason/owner/country concentration for the non-perfect cases | Runtime-support depth is no longer only conceptual and replay interpretation is materially stronger and more realistic; the next future work shifts from tranche-completion breadth toward either broader MVP/P2 runtime scope or richer analyst interpretation beyond the current attention-summary/watchlist layer |
| Analyst annotations visibility | Show analyst annotations in GUI | Present | Dedicated page and contextual rendering exist | Mostly done |
| Annotation creation/editing in GUI | Create/manage annotations in GUI | Absent | Read-only visibility only | Missing feature |
| Traceability / lineage | Follow evidence path from source to status/report | Present | Traceability page exists and artifact path is implemented | Mostly done |
| Release/demo readiness | Explicit readiness page and machine-readable status | Present | `readiness.html` + `readiness.json` implemented, and governed latest bundles now persist `readmodels/readiness.json` | Done |
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
- P1 is now materially closed for the current governed pilot:
  - latest bundle persists `readmodels/validation_backtest.json`
  - latest bundle also persists machine-readable `readmodels/readiness.json`
  - GUI artifact loads can reuse the persisted readiness model instead of recomputing from scratch
- P2 is materially closed for the current representative pilot and now broadened by wider governed subsets:
  - multi-country runtime/artifact path works
  - representative evidence covers `UKR`, `POL`, `ISR`, and `TWN`
  - TWN is explicitly scoped to A/B in the governed pilot rather than surfacing as a misleading D-gap
  - a broader named `core-focus-initial` pilot set runs successfully with `UKR`, `RUS`, `CHN`, `TWN`, `ISR`, and `POL`
  - a further `core-focus-expanded` subset adds `IND`
  - a `core-focus-broader` subset adds `IRN` and `TUR`
  - a new `core-focus-complete` subset now also adds `PAK` and `GEO`, and this 11-country subset has a successful `release_verdict=ready` probe
  - extended-focus slices (`extended-focus-initial`, `extended-focus-broader`, `extended-focus-energy-initial`, `extended-focus-crisis-initial`) are closed with ready-state probes
  - the new consolidated `extended-focus-complete` set is now also closed with ready-state evidence (`USA`, `DEU`, `EST`, `FIN`, `POL`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`) and explicit `EST`/`MMR` domain governance as `A/D` for readiness honesty in low-signal Domain-B windows
  - a larger `focus-complete` set now consolidates core-focus-complete + extended-focus-complete into one 21-country governed run (`UKR`, `RUS`, `CHN`, `TWN`, `IRN`, `ISR`, `TUR`, `IND`, `PAK`, `GEO`, `POL`, `USA`, `DEU`, `EST`, `FIN`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`) with successful `release_verdict=ready`; `GEO` and `QAT` are now also governed as `A/D` for readiness honesty under low-signal Domain-B windows
  - control/reference breadth is now also consolidated in a successful `release_verdict=ready` complete set (`control-reference-complete`: `NOR`, `CHE`, `SWE`, `NLD`, `IRL`, `PRT`, `NZL`, `CAN`, `AUS`) with `NOR` and `PRT` governed as `A/D` to avoid misleading low-signal Domain-B gaps
- P3 is strongly advanced:
  - artifact-backed trend charts exist
  - world-map visualization exists
  - controls exist and are interactive
  - cross-country comparison exists
  - coverage/confidence/uncertainty visualization exists
  - semantic view projections and trend event overlays exist
- P4 is now materially advanced:
  - source-gap transparency is visible through country gap watchlists, remediation watchlists, priority/depth summaries, and freshness overlays in overview/map-facing views
  - analyst annotation create/edit workflow now exists as a governed static-site workflow baseline
  - baseline/historical comparison overlays on trends and domain views now exist as analyst-friendly comparison summaries
  - source-dependency cluster candidates and explicit source-origin groundwork are now visible in the traceability view

Interpretation:
- the old roadmap order was correct as a program scaffold
- however, execution has now overtaken parts of the document
- the critical remaining gap is no longer missing artifact completeness inside the current governed pilot, but how far runtime breadth and the validation/reference-case depth should be expanded next
- the current validation view is now richer than a single-country runtime-support check because the artifact carries a multi-case portfolio summary, a curated repo-backed reference-case library now broadened from 4 to 21 countries / 23 cases (`UKR`, `RUS`, `CHN`, `IND`, `IRN`, `ISR`, `TUR`, `USA`, `DEU`, `EST`, `FIN`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`, `POL`, `PAK`, `GEO`, `TWN`), historical reference-review / evidence-scoring outputs, a governed provider-backed archival replay layer across that broadened library, explicit archival provenance/accountability metadata, replay evidence score/tier interpretation, first governed challenge cases with partial and mismatch replay outcomes, and now also a replay attention layer that summarizes non-perfect cases by level/reason/owner/country concentration instead of leaving only raw review rows

## 3b. Updated planning horizon

For time planning, the remaining work should be treated in three bands rather than as one flat backlog:

- Near-term closure band:
  - reassess the next serial priority between broader MVP/P2 live-runtime breadth beyond the current core-focus subsets and deeper governed validation interpretation now that the obvious extended-focus validation-breadth tranches are closed
- Mid-term breadth/depth band:
  - expand from the current representative / `core-focus-initial` / `core-focus-expanded` / `core-focus-broader` / `core-focus-complete` governed subsets toward wider MVP coverage and/or deeper governed validation evidence
- Later analyst-depth band:
  - add operational annotation workflows and the first advanced source-intelligence features

Practical recommendation for serial pacing:
- small cleanup package now closed: latest-bundle output hygiene
- next: 2 to 4 medium runtime/breadth packages
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

1. First control/reference runtime slice beyond the now-closed crisis tranche (recommended tranche: `CHE`, `NLD`, `SWE`)
   - size: medium to large
   - reason: the new-country extended-focus crisis tranche (`NGA`, `SDN`, `MMR`) is now closed in ready-state evidence, so the next value step is extending governed support into the first control/reference cluster
2. Follow-up runtime robustness package(s) only if the next breadth probes expose a concrete new failure mode
   - size: small to medium
   - reason: hardening remains probe-driven and targeted (no speculative broad retry expansion)
3. Next validation interpretation/depth package
   - size: medium
   - reason: validation baseline is already strong (23 cases / 21 countries), so further depth should remain selective and analyst-value-driven
4. Later source-origin / epidemiology extension package(s)
   - size: large
   - reason: groundwork exists, but full origin inference and information-spread analysis remain intentionally later

Suggested planning cadence:
- next work package: first control/reference runtime slice (`CHE`, `NLD`, `SWE`) with governed mapping/tests/probe evidence
- following 1 package: targeted robustness follow-up only if probe evidence from that tranche demands it
- after that: deeper analyst interpretation / source-origin features based on capability-matrix priority

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

Next serial work package should be: first control/reference runtime integration tranche (`CHE`, `NLD`, `SWE`) with governed support, tests, and live probe evidence.

Current rationale:
- the annotation create/edit workflow gap has been closed with a governed static-site workflow baseline
- the trend/domain baseline-historical interpretation gap has been closed for the current static GUI baseline
- the first source-dependency / source-origin groundwork slice is now also present in the traceability view without overclaiming full origin inference
- the readiness-honesty closure slice is now also in place: artifact presence/absence is explicit and `validation_backtest` is visibly present in the current latest bundle
- the latest runtime-hardening slice (`d7f6a85`) now also retries isolated `SRC-GDELT-EVENTS` partial-success failures and is backed by representative live evidence (`RUN-LIVE-REP-RETRY-EVT-001`: `run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `release_verdict=ready`)
- the first truly new-country extended-focus runtime slice is now ready-state repo-evidenced with `--pilot-set extended-focus-energy-initial` and probe `RUN-LIVE-EXT-ENERGY-INIT-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=3/3`, `known_gaps=[]`, `release_verdict=ready`) plus generated GUI `build/local_gui/_ext_energy_init_probe_1`
- the next new-country extended-focus runtime tranche is now also closed in ready-state evidence with `--pilot-set extended-focus-crisis-initial` and probe `RUN-LIVE-EXT-CRISIS-INIT-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=3/3`, `known_gaps=[]`, `release_verdict=ready`) plus generated GUI `build/local_gui/_ext_crisis_init_probe_1`
- runtime support now includes `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, and `MMR` with governed mappings, expected domains, pilot-set semantics, and regression coverage
- with this tranche now closed without known gaps, the next package should move to the first control/reference runtime slice (`CHE`, `NLD`, `SWE`)

After that, proceed with the strongest remaining breadth package indicated by the capability matrix.
