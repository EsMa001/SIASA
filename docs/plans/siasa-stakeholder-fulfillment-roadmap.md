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
| Source lineage / epidemiology visualization | Spread / amplification / source graph | Present | Analytics page now includes a dedicated source-lineage visualization section with provenance flow, spread snapshots, and epidemiology anchors; dependency/provenance analytics were already present | Mostly done |
| Reports / exports | Daily snapshot + manual exports with evidence context | Present | Export page and exported files exist | Mostly done |
| Validation / backtest review | Validation cases and expected-vs-observed review | Present in GUI baseline and governed artifacts | Validation page exists; latest artifact bundle carries both `validation_backtest.json` and `readiness.json`, the validation artifact exposes a curated reference-case library beside the runtime-support portfolio, surfaces historical reference-review / evidence-scoring outputs for those curated cases, carries full curated-library `provider_backed_archival_replay`, surfaces archival provenance details such as replay source coverage and archival data-file metadata, renders replay evidence score/tier plus source/provenance coverage ratios, includes governed challenge cases that produce partial and mismatch replay outcomes instead of only perfect matches, broadens the curated governed library from 4 to 21 countries / 23 cases by adding `RUS`, `CHN`, `IND`, `IRN`, `TUR`, `USA`, `DEU`, `EST`, `FIN`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`, `PAK`, and `GEO` reference cases, and exposes an analyst-facing replay attention layer with both a watchlist and an aggregated summary by level/reason/owner/country concentration for the non-perfect cases | Runtime-support depth is no longer only conceptual and replay interpretation is materially stronger and more realistic; the next future work shifts from tranche-completion breadth toward either broader MVP/P2 runtime scope or richer analyst interpretation beyond the current attention-summary/watchlist layer |
| Analyst annotations visibility | Show analyst annotations in GUI | Present | Dedicated page and contextual rendering exist | Mostly done |
| Annotation creation/editing in GUI | Create/manage annotations in GUI | Absent | Read-only visibility only | Missing feature |
| Traceability / lineage | Follow evidence path from source to status/report | Present | Traceability page exists and artifact path is implemented | Mostly done |
| Release/demo readiness | Explicit readiness page and machine-readable status | Present | `readiness.html` + `readiness.json` implemented, and governed latest bundles now persist `readmodels/readiness.json` | Done |
| Role-based UI behavior | Role-specific available functions | Present | Local GUI now supports explicit role profiles (`viewer`,`analyst`,`admin`) with role-gated navigation and page generation (`--ui-role`) | Server-side identity/permission governance still future work |
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
  - the previously unstable `mvp-complete` 30-country tranche is now closed with deterministic runtime behavior under live-source rate limits (retry-delay caps + large-set runtime profile) and ready-state evidence: `RUN-LIVE-MVP-COMPLETE-014` (`run_status=partial_success`, `failed_sources=SRC-GDELT-DOC`, `known_gaps=[]`, `release_verdict=ready`) plus GUI `build/local_gui/_mvp_complete_probe_14`
  - readiness governance transparency is now hardened: readiness outputs include both filtered `known_gaps` and explicit suppression traceability via `suppressed_known_gaps` + `known_gap_suppression_reason`; closure evidence from representative probe `RUN-LIVE-REP-READINESS-TRUTH-001` (`run_status=success`, `failed_sources=none`, `known_gaps=[]`, `suppressed_known_gaps=[]`, `release_verdict=ready`) plus GUI `build/local_gui/_rep_readiness_truth_1`
  - stale-coverage operator actionability is now hardened: `country_coverage_visibility` includes `stale_priority_summary` + ranked `stale_priority_watchlist`, and GUI coverage views render a dedicated “Stale Coverage Priority Queue”; closure evidence from `RUN-LIVE-REP-FRESH-QUEUE-002` (`run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `known_gaps=[]`, `release_verdict=ready`) plus GUI `build/local_gui/_rep_fresh_queue_2`
  - role-based GUI behavior is now materially implemented: `--ui-role` (`viewer`,`analyst`,`admin`) enables role-gated navigation/page generation; representative closure evidence `RUN-LIVE-REP-ROLE-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `known_gaps=[]`, `release_verdict=ready`) plus dual role bundles `build/local_gui/_rep_role_1_analyst` and `build/local_gui/_rep_role_1_viewer`
  - report/export scoping UX is now materially interactive: `reports.html` now provides type/id filters and visible-row count for governed report catalogs; closure evidence `RUN-LIVE-REP-REPORT-SCOPE-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `known_gaps=[]`, `release_verdict=ready`) plus GUI bundle `build/local_gui/_rep_report_scope_1`
  - domain deep-dive interpretation UX is now materially interactive: domain detail views provide feature/source scoping controls with visible-row counters and filtered tables; closure evidence `RUN-LIVE-REP-DOMAIN-DEEP-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `known_gaps=[]`, `release_verdict=ready`) plus GUI bundle `build/local_gui/_rep_domain_deep_1`
- P3 is strongly advanced:
  - artifact-backed trend charts exist
  - world-map visualization exists
  - controls exist and are interactive
  - cross-country comparison exists
  - coverage/confidence/uncertainty visualization exists
  - semantic view projections and trend event overlays exist
- P4 is now materially advanced:
  - source-gap transparency is visible through country gap watchlists, remediation watchlists, priority/depth summaries, freshness overlays, and the structured source-status summary in overview/map-facing views
  - analyst annotation create/edit workflow now exists as a governed static-site workflow baseline
  - baseline/historical comparison overlays on trends and domain views now exist as analyst-friendly comparison summaries
  - source-dependency cluster candidates and explicit source-origin groundwork are now visible in the traceability view
- project-lead fulfillment steering is now explicit and reproducible:
  - new functional stakeholder-fulfillment estimator is available in code (`src/siasa/readmodels/functional_fulfillment.py`) with unit tests
  - default weighted steering estimate from the current capability matrix is now `100.0%` (`Done=16`, `Partial=0`, `Weak=0`, `N=16`)

Interpretation:
- the old roadmap order was correct as a program scaffold
- however, execution has now overtaken parts of the document
- capability closure and release readiness must be steered as two distinct signals: capability matrix completion answers "implemented scope", while release-readiness gates/failure drills answer "operationally safe to release"
- with matrix fulfillment now at `100.0%` (`Done=16/16`), the immediate risk is metric conflation rather than missing top-level capability rows
- AP-22 is now closed: release-failure drill now emits recurrence-aware remediation prioritization (`operator_recurrence_aware_remediation_prioritization`) that combines AP-19 recurrence baseline with AP-20 stale-remediation closure urgency, and readiness GUI surfaces AP-22 ranked remediation rows.
- AP-23 is now closed: release-failure drill now also emits `operator_failure_drill_delta_ledger`, compares against the prior persisted drill summary when available, classifies movement rows (`new_issue/improved/regressed/resolved/steady`), and renders an operator impact narrative in readiness GUI and drill outputs.
- AP-24 is now closed: `operator_remediation_execution_loop` turns ranked priorities into explicit next-up/queued action records with closure targets and evidence sources.
- AP-25 is now closed: stale-remediation closure breaches are translated into an explicit operator action plan (`operator_stale_remediation_action_plan`) with deterministic next-up/queued actions, action categories, and closure checks such as `priority_score > 0` and `unresolved_age_hours <= 72.0`.
- AP-26 is now closed: release evidence now emits `operator_blocker_causality`, separating primary root causes from derived release effects and surfacing the causal chain directly in markdown evidence and readiness GUI.
- AP-27 is now closed: stakeholder-flow and browser governance gates are now consolidated into one operator-facing `operator_operability_cluster`, so path health is readable as one coherent operability package in evidence and readiness GUI.
- next serial planning focus should now be chosen after AP-27 closure review.
- the current validation view is now richer than a single-country runtime-support check because the artifact carries a multi-case portfolio summary, a curated repo-backed reference-case library now broadened from 4 to 21 countries / 23 cases (`UKR`, `RUS`, `CHN`, `IND`, `IRN`, `ISR`, `TUR`, `USA`, `DEU`, `EST`, `FIN`, `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, `MMR`, `POL`, `PAK`, `GEO`, `TWN`), historical reference-review / evidence-scoring outputs, a governed provider-backed archival replay layer across that broadened library, explicit archival provenance/accountability metadata, replay evidence score/tier interpretation, first governed challenge cases with partial and mismatch replay outcomes, a replay attention layer that summarizes non-perfect cases by level/reason/owner/country concentration instead of leaving only raw review rows, and interactive scoping controls on the historical replay detail table (country/verdict/basis/text + visible counts)

## 3b. Updated planning horizon

This roadmap should remain the central planning document for the next program steps.
The capability matrix stays the operational companion for evidence/status tracking, but the roadmap should hold the main forward plan and its rationale.

For time planning, the remaining work should now be organized as an explicit A -> B -> C sequence rather than as a flat backlog.

### Step A: Runtime- and source-breadth expansion

Objective: increase real operational breadth so SIASA is not only governance-strong on the current representative/core subsets, but demonstrably useful across a broader live country/source scope.

What this step should contain:
- expand beyond the current representative and already-closed governed subsets toward the next meaningful MVP/P2 country clusters
- strengthen real-source robustness where broader runs still depend on transient provider behavior or narrow country slices
- keep every expansion package evidence-driven: tests, real live run, generated GUI, and updated planning evidence

Why Step A comes first:
- it increases actual product reach, not only internal governance clarity
- it reduces the remaining risk that the system is strong mainly on known/curated subsets
- it creates the broader artifact basis on which later analyst-depth work will have more practical value

Expected outcome of Step A:
- wider real multi-country runtime evidence
- clearer statement of practical supported scope
- stronger confidence that the current product scales beyond the already-proven subsets

Current Step-A closure status:
- AP-A1 completed: operational `latest` is now built from the broader governed `extended-focus-complete` 11-country set
- live closure evidence: `RUN-LIVE-EXT-FOCUS-LATEST-005`
- artifact evidence: `build/run_artifacts/latest/readmodels/readiness.json` reports `release_verdict=ready`, `known_gaps=[]`
- explicit degraded-mode evidence: `RUN-LIVE-FOCUS-LATEST-DEG-001` completed with `run_status=partial_success`, `pilot_set=focus-complete`, and preserved `build/run_artifacts/latest_focus_complete_degraded/` + `build/local_gui/latest_focus_complete_degraded/` outputs when `allow_partial_success` and `allow_failed_sources` were enabled
- GUI evidence: `build/local_gui/latest/index.html`
- implementation hardening added broader-run GDELT DOC recovery budget (`max_retry_delay_seconds=180`, full-batch retry cooldown `120s`) plus broader-run request timeout (`90s`) so the 11-country `latest` path is operationally stable
- ReliefWeb runtime breadth is now code-wired but provider-gated: governed live runtime activates `SRC-RELIEFWEB` automatically only when `RELIEFWEB_APPNAME` is configured, so Domain-C breadth can grow without breaking default runs in unregistered environments
- UCDP runtime breadth is now also credential-gated: governed live runtime activates `SRC-UCDP-GED` only when `UCDP_API_TOKEN` is configured, which removes default false-failures in uncredentialed representative runs; representative probe `RUN-LIVE-REP-UCDP-GATE-001` reduced `failed_sources` to only `SRC-GDELT-DOC-E`
- representative GDELT-doc stabilization is now operationally bounded: the Domain-E `SRC-GDELT-DOC-E` branch uses a shallower multi-country retry profile (`max_retries=1`, `max_retry_delay_seconds=20.0`) so representative probes now complete deterministically under renewed 429 pressure; closure evidence `RUN-LIVE-REP-DOC-E-STAB-003` finished within the foreground timeout with explicit `failed_sources=SRC-GDELT-DOC,SRC-GDELT-DOC-E` instead of reproducing the earlier no-output stall

### Step B: Analyst interpretation and actionability depth

Objective: turn the now governance-strong and broader runtime/artifact base into a more directly useful analyst tool with clearer interpretation, prioritization, and next-action guidance.

What this step should contain:
- strengthen analyst-facing synthesis from readiness, validation, replay, traceability, and operability signals
- reduce the number of separate pages/signals an analyst must mentally combine
- add compact decision-oriented views that explain what matters now, why it matters, and what should be reviewed next

Why Step B follows Step A:
- analyst-depth becomes more valuable when it summarizes a broader real runtime scope rather than only a narrow slice
- it converts breadth and evidence into practical human decision support
- it is a higher-value next move than continuing to add more low-level governance layers

Expected outcome of Step B:
- stronger analyst workflow usability
- faster interpretation of system state and validation findings
- clearer project-lead and analyst handoff between evidence and action

Current Step-B progress:
- B-1 completed: Analyst briefing "What matters now?" now condenses existing runtime evidence into one readiness-facing summary
- B-2 completed: The briefing now also synthesizes traceability and operability signals, adds a primary-focus line, and surfaces the most actionable next page/check in the readiness view
- B-3 completed: The cross-country comparison page now supports a relative-baseline mode so analysts can compare status/coverage/confidence deltas and shared-driver overlap against a chosen reference country
- B-4 completed: The analytics lineage surface now includes a source-hotspot matrix that summarizes the top dependency cluster, spread path, and amplification event in one scan-oriented block
- current GUI evidence: `build/local_gui/latest/readiness.html`
- current comparison evidence: `build/local_gui/latest/comparison.html`
- current analytics evidence: `build/local_gui/latest/analytics.html`
- current exported briefing artifact: `build/local_gui/latest/analyst_briefing.json`
- current live evidence basis: `RUN-LIVE-EXT-FOCUS-LATEST-005`
- current summary fields explicitly separate release blockers, country gaps, validation-attention cases, traceability risks, operability-cluster risks, and stale-priority/stale-remediation items, each with recommended next check and target page
- B-2 completed: a country-centric hotspot convergence matrix now combines coverage gaps, validation-attention cases, and stale-priority cues per country into one deterministic analyst action board
- current B-2 artifact fields: `country_hotspot_matrix.row_count`, `multi_signal_country_count`, and ranked rows with `country_id`, `signal_count`, `missing_domains`, `attention_case_count`, `top_attention_case_id`, `freshness_hours`, `recommended_next_check`
- current B-2 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`486 passed`)
- B-3 completed: hotspot rows now expose direct anchored handoff links into Coverage and Validation so the matrix becomes an executable follow-up surface rather than only a summary table
- current B-3 artifact fields: `coverage_href`, `validation_href`, readiness `Hotspot Links` column, coverage anchors `country-gap-<ISO3>` / `stale-priority-<ISO3>`, and validation anchors `attention-case-<CASE_ID>`
- current B-3 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)
- B-4 completed: hotspot handoff links now also carry prefilled analyst context into the target page instead of only jumping to a static anchor
- current B-4 artifact fields: `coverage_prefill_href`, `validation_prefill_href`, Coverage `coverage-focus-summary`, and Validation replay-attention hash-prefill reuse via `#ra=...`
- current B-4 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)
- B-5 completed: Coverage prefill handoffs now land in a visibly focused state instead of only showing passive query metadata
- current B-5 artifact fields: row-level `coverage-focus-target` metadata (`data-focus-country`, `data-focus-section`, `data-missing-domains`), focus-section anchors `coverage-focus-section-stale-priority` / `coverage-focus-section-country-gap`, JS hook `applyCoverageFocusState()`, summary field `focus_target_count`, and CSS states `coverage-focus-target-active` / `coverage-focus-target-dim`
- current B-5 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)
- B-6 completed: Validation prefill handoffs now land on a visibly emphasized replay-attention slice instead of only applying hidden hash-filter state
- current B-6 artifact fields: `replay-attention-panel`, focus summary KPI `replay-attention-focus-target-count`, helpers `hasReplayAttentionFocus()` / `applyReplayAttentionFocusState()`, CSS states `replay-attention-focus-active` / `replay-attention-focus-panel-active`, and first-target auto-scroll for hash-prefilled replay-attention focus
- current B-6 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)

### Step C: Demo/release productization

Objective: turn the technically and analytically stronger baseline into a cleanly reviewable, reproducible, stakeholder-facing demo/release package.

What this step should contain:
- define and harden a curated demo/review path across the most important product flows
- package the most important readiness/evidence/operability signals into a presentation- and decision-ready form
- ensure the resulting release/demo bundle is reproducible, reviewable, and understandable for non-developer stakeholders

Why Step C follows Step B:
- productization has the highest value once real breadth and analyst usefulness are both stronger
- it avoids polishing a package whose practical reach or interpretation depth is still too thin
- it makes the later release/demonstration step much more credible

Expected outcome of Step C:
- decision-ready demo/release package
- clearer stakeholder communication of current product value and limitations
- stronger management/review readiness

Current Step-C progress:
- C-1 completed: a dedicated Release / Demo Package surface now bundles readiness, gate, traceability, validation, and operability signals into one reviewable package
- C-2 completed: a dedicated Release / Failure Drill page now surfaces baseline and no-go drill scenarios as a separate reviewable operator surface
- C-3 completed: the Release / Demo Package now includes a guided stakeholder review sequence instead of only static summary panels
- C-4 completed: the Release / Demo Package now includes an executive decision summary with explicit recommendation, confidence, blockers, strongest evidence, and limitations
- C-5 completed: the Release / Demo Package now includes an explicit reviewer handoff/export summary for next-role routing and decision-log seeding
- current GUI evidence: `build/local_gui/latest/release_package.html`
- current drill GUI evidence: `build/local_gui/latest/release_failure_drill.html`
- current machine-readable package artifact: `build/local_gui/latest/release_demo_package.json`
- current machine-readable drill artifact: `build/local_gui/latest/readmodels/release_failure_drill_report.json`
- current C-3 artifact fields: `review_sequence` with steps `C3-01..C3-06`, phase/objective/reviewer-question/expected-signal fields, and rendered `Guided review sequence` panel in `release_package.html`
- current C-4 artifact fields: `executive_decision_summary` with `recommendation`, `decision_confidence`, `decision_basis`, `review_completion_signal`, `top_blockers`, `strongest_evidence_points`, and `explicit_limitations`
- current C-5 artifact fields: `reviewer_handoff_summary` with `next_reviewer_role`, `canonical_handoff_artifact`, `secondary_artifacts`, `share_now`, and `decision_log_seed`
- current implementation evidence: `src/siasa/readmodels/release_demo_package.py`, `src/siasa/readmodels/release_evidence.py`, `src/siasa/gui/local_app.py`
- current C-3 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)
- current C-4 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)
- current C-5 validation evidence: `tests/unit/test_local_gui.py` plus full-suite pass (`467 passed`)

### Recommended serial execution rule

Use the following priority order unless new external steering changes it:
- first: Step A (Runtime- and source-breadth expansion)
- second: Step B (Analyst interpretation and actionability depth)
- third: Step C (Demo/release productization)

Interpretation:
- Step A increases real product reach
- Step B increases practical analyst value
- Step C increases presentation/release readiness

This preserves one central planning logic while still allowing the capability matrix to track concrete evidence package by package.

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
Objective: add creation/edit/edit-history handling for analyst annotations, including replay-attention prefill summary and integrity feedback.

Expected outcome:
- analyst role becomes operational in the GUI, not only visible in stored artifacts, and can verify the replay-attention handoff context before saving

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
   - reason: validation baseline is already strong (23 cases / 21 countries), so further depth should remain selective and analyst-value-driven; replay-attention handoff observability now makes the annotation transition more explicit
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

Next serial work package should now be selected from runtime/source breadth expansion, since validation realism depth has just been made explicit in the GUI and the current validation replay scoping is already closed.

Current rationale:
- the annotation create/edit workflow gap has been closed with a governed static-site workflow baseline
- the replay-attention annotation handoff now also includes a visible prefill summary and integrity status before save, reducing hidden context loss in the browser-local workflow
- the trend/domain baseline-historical interpretation gap has been closed for the current static GUI baseline
- the comparison workflow now also supports reference-relative interpretation, so analysts can compare countries against an explicit baseline instead of only scanning a flat list
- the source-lineage / epidemiology package is now also more scan-oriented because the strongest dependency/spread/amplification hotspots are summarized in one matrix instead of requiring analysts to read multiple separate blocks
- runtime/source breadth has also advanced one more step on the real-source side: ReliefWeb is no longer only an isolated adapter but a governed live-runtime option once provider registration exists
- runtime/source breadth has also become more honest in no-credential environments: UCDP no longer appears as a default failed live source when no token is configured, leaving the remaining representative instability isolated to `SRC-GDELT-DOC-E`
- the first source-dependency / source-origin groundwork slice is now also present in the traceability view without overclaiming full origin inference
- the readiness-honesty closure slice is now also in place: artifact presence/absence is explicit and `validation_backtest` is visibly present in the current latest bundle
- the latest runtime-hardening slice (`d7f6a85`) now also retries isolated `SRC-GDELT-EVENTS` partial-success failures and is backed by representative live evidence (`RUN-LIVE-REP-RETRY-EVT-001`: `run_status=success`, `failed_sources=none`, `countries_with_updates=4/4`, `release_verdict=ready`)
- the first truly new-country extended-focus runtime slice is now ready-state repo-evidenced with `--pilot-set extended-focus-energy-initial` and probe `RUN-LIVE-EXT-ENERGY-INIT-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=3/3`, `known_gaps=[]`, `release_verdict=ready`) plus generated GUI `build/local_gui/_ext_energy_init_probe_1`
- the next new-country extended-focus runtime tranche is now also closed in ready-state evidence with `--pilot-set extended-focus-crisis-initial` and probe `RUN-LIVE-EXT-CRISIS-INIT-001` (`run_status=success`, `failed_sources=none`, `countries_with_updates=3/3`, `known_gaps=[]`, `release_verdict=ready`) plus generated GUI `build/local_gui/_ext_crisis_init_probe_1`
- runtime support now includes `SAU`, `QAT`, `EGY`, `NGA`, `SDN`, and `MMR` with governed mappings, expected domains, pilot-set semantics, and regression coverage
- the validation realism snapshot is now explicit in the GUI: non-perfect portfolio cases are surfaced with a dedicated KPI and snapshot table instead of remaining buried in the detail table
- with this tranche now closed without known gaps, the next package should move to runtime/source breadth expansion (or the next highest-value governed breadth package called out by the matrix)

After that, proceed with the strongest remaining breadth package indicated by the capability matrix.
