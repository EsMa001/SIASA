# SIASA Master Steering Document

> For Hermes: this is the single steering document for forward program control. Update it after every completed serial work package. Use it as the primary source for (1) current program truth, (2) remaining substantive stakeholder gaps, and (3) next serial package selection. Use the capability matrix as the detailed operational evidence companion, not as a second competing steering narrative.

Created: 2026-06-04
Status: Active master steering document

Goal: provide one authoritative steering view that replaces fragmented next-step logic across multiple historical planning generations.

Architecture: this document sits above the detailed capability matrix and historical planning artifacts. It consolidates current repo truth, remaining substantive stakeholder gaps, steering priorities, and the active serial execution path.

Tech stack / evidence base: `docs/plans/siasa-project-lead-capability-matrix.md`, `src/siasa/**`, `tests/**`, governed probe/runtime artifacts under `build/run_artifacts/**`, and current release/readiness productization surfaces.

---

## 1. How to use this document

Use this document for exactly four things:
1. decide what the project should do next
2. explain current state to project lead / stakeholders
3. prevent obsolete planning documents from reintroducing outdated next-step logic
4. keep capability closure, runtime breadth, and release/distribution closure causally separated

Use the following hierarchy:
- this document = single steering source for next-step selection
- `docs/plans/siasa-project-lead-capability-matrix.md` = detailed capability/evidence ledger
- historical planning docs = rationale/history only

Non-rule:
- do not select the next package from older `Immediate Next Recommendation` sections in historical plans

---

## 2. Current program truth

### 2.1 Current closure state

Current repo/program truth:
- capability matrix fulfillment is currently `17/17 Done`, `100.0%`
- the former major implementation-gap program (`AP-F01..AP-F27` style closure work) has been materially executed in the repo
- analyst GUI, governed validation, release/readiness governance, and release productization have all progressed far beyond the earlier planning baselines
- the broader governed pilot-set family (`extended-focus-complete`, `focus-complete`, `mvp-complete`) is now explicit in the live-runtime CLI help and covered by runtime unit tests, reducing mismatch between roadmap claims and user-facing runtime interface

This means:
- SIASA is no longer primarily in a “missing core implementation” phase
- SIASA is now primarily in a “practical breadth, source activation, operational evidence continuity, and final release lifecycle closure” phase

### 2.2 What is materially implemented now

The current baseline materially includes:
- world overview, country drill-down, domain deep dive, coverage/trust, reports/exports, validation, annotations, comparison, trends, role behavior
- Domain A/B/C/D/E implementation in code
- multiple governed source adapters including UCDP, UNHCR, CISA KEV, ReliefWeb integration-ready paths
- storage/history/scheduler/health-monitoring foundations
- backtesting, rules, auto-reports, cross-domain analytics, provenance/dependency/epidemiology/probabilistic/uncertainty modules
- release readiness, release gate, release evidence, release failure drill, operator remediation views, release package, decision packet seed, and decision-packet send-readiness checklist

### 2.3 What this does NOT yet mean

`17/17 Done` does NOT mean all stakeholder intent is exhausted in practice.
It means the currently defined capability rows are materially closed for the present product baseline.

The remaining substantive work is now concentrated in fewer higher-level practical gaps.

---

## 3. Remaining substantive stakeholder gaps

### G1. Runtime breadth beyond the already-proven governed subsets

Current truth:
- runtime breadth has progressed strongly
- but practical supported scope is still narrower than the full intended stakeholder breadth picture

Remaining gap:
- broader repeatable live runtime proof across the next bounded MVP/P2 country slices
- explicit honest handling of rate limits, partial success, and effective C/E usage under broader real runs

Why it matters:
- this is the largest remaining real product-reach gap
- it most directly affects whether SIASA is merely strong on curated/proven subsets or genuinely broader in operational usefulness

### G2. Credential-/provider-gated source activation

Current truth:
- code paths/adapters exist for source classes such as ReliefWeb and UCDP
- graceful degradation exists when credentials/registration are absent

Remaining gap:
- actual operational activation with valid credentials/app registrations
- source-class closure in real evidence, not only in repo structure

Why it matters:
- “adapter exists” is not equivalent to “stakeholder-visible source breadth exists in operations”

### G3. Operational evidence-lane normalization

Current truth:
- code exists for latest bundles, verification, scheduler, health monitoring, and digest/report artifacts
- but planning/steering can still drift between repo capability and currently fresh operational evidence

Remaining gap:
- one normalized authoritative operator/project-lead evidence lane
- reduced ambiguity between “implemented” and “currently evidenced in a fresh run bundle”

Why it matters:
- a mature system needs not only code closure but fresh, reviewable, current operational evidence

### G4. Approval-to-distribution release lifecycle closure

Current truth:
- release package and review/sign-off/productization stack are already strong
- current package can determine blocked vs internal-review-only vs send-ready packet states

Remaining gap:
- explicit lifecycle transition from pending sign-off to approved to distributed
- explicit closure artifact for actual review/distribution outcome

Why it matters:
- this is the remaining high-value Step-C closure path
- it closes the final gap between “prepared for decision” and “governed external release/distribution completed”

### G5. Optional server-backed multi-user governance

Current truth:
- the current local/static/governed bundle UX is materially strong

Remaining gap:
- server-backed authn/authz, shared persistence, reviewer workflows, multi-user control surfaces

Steering status:
- deferred by intent unless external steering reprioritizes toward multi-user operational deployment

---

## 4. Active steering priority order

The active serial priority order is now:

### Priority 1: Runtime breadth and live evidence expansion
Why first:
- largest remaining stakeholder-value gap
- increases real product reach rather than only improving already-strong presentation/governance surfaces
- best fits current SIASA maturity stage

### Priority 2: Credentialed source activation and source-class closure
Why second:
- converts integration-ready source classes into real operational value
- directly narrows the gap between code completeness and runtime evidence completeness

### Priority 3: Operational evidence-lane normalization
Why third:
- broader runs and newly activated sources need one authoritative, fresh evidence baseline
- improves operator/project-lead truthfulness and review efficiency

### Priority 4: Approval-to-distribution release closure
Why fourth:
- release/demo productization is already advanced
- the remaining useful increment is lifecycle completion, not another summary panel

### Priority 5: Deferred architecture uplifts
Why last/default deferred:
- multi-user/server-backed architecture is valuable only if the target operating model explicitly requires it now

---

## 5. Active serial execution model

All work should continue as strict bounded serial packages.

Each package must:
1. implement exactly one bounded slice
2. run targeted verification
3. run full-suite verification
4. update this master steering document if steering truth changed
5. update the capability matrix if evidence/status changed
6. commit and push

Do not reopen strategic planning every time.
Only revisit steering priority when:
- a package materially changes the frontier
- credentials become available that change source-activation priority
- runtime evidence shows a different root bottleneck than assumed

---

## 6. Current recommended next package

### N1-WP-001 (completed steering-truth sub-slice)
Name:
Expose and test the broader governed live-runtime pilot-set family (`extended-focus-complete`, `focus-complete`, `mvp-complete`) so runtime breadth claims are explicit in the CLI surface and protected by unit tests.

Closure achieved:
- live-runtime CLI help now lists the three broader named pilot sets explicitly
- unit coverage now verifies orchestrator support for `extended-focus-complete` and `focus-complete`
- pipeline pass-through coverage now verifies `mvp-complete` without explicit `country_ids`

### N1-WP-002 (completed broader live-probe closure slice)
Name:
Execute the next actual broader live probe slice on top of the now explicitly exposed/test-covered `extended-focus-complete` / `focus-complete` / `mvp-complete` pilot-set family, with explicit C/E evidence digest and honest partial-success semantics.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now auto-builds `readmodels/live_probe_evidence_digest.json` and `readmodels/live_probe_policy_gate.json` for operational latest bundles before persisting run-history metadata
- `src/siasa/runs/latest_bundle_verification.py` now requires these two machine-readable governance artifacts, verifies digest/gate alignment against `system_status.json`, and rejects bundles whose governed slice identity remains implicit
- targeted verification passed for the new operational-latest + bundle-verification contract (`24 passed` across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`)
- full regression passed (`472 passed in 978.14s`)
- one fresh broader real probe bundle was generated on `focus-complete` via `RUN-OP-LATEST-20260604T103448Z`
- the resulting real evidence shows honest degraded-mode governance rather than forced greenwashing: `run_status=partial_success`, `country_set_id=MVP-COUNTRIES-LIVE-focus-complete-v1`, `failed_sources=[SRC-GDELT-DOC, SRC-GDELT-DOC-E]`, `combined_ce_ratio=0.8571`, governance verdict `amber`, and policy gate verdict `pass`

### N1-WP-003 (completed operational evidence-lane normalization slice)
Name:
Normalize the operator/project-lead evidence lane on top of the new broader live-probe governance artifacts so the latest/history surfaces expose `country_set_id`, C/E ratio, governance verdict, and policy-gate outcome without requiring raw JSON inspection.

Closure achieved:
- `src/siasa/data/storage.py` now persists and reloads per-run evidence-lane governance fields in run history: `country_set_id`, `combined_ce_ratio`, `governance_verdict`, and `policy_gate_verdict`
- `src/siasa/runs/operational_latest.py` now writes `readmodels/operational_evidence_lane.json` with `latest_summary` plus recent run-history rows and seeds a fallback row when a custom writer does not persist to SQLite
- `src/siasa/gui/local_app.py` now loads that evidence-lane readmodel and renders it directly in `runs.html` via an `Operational Evidence Lane` panel plus a `Recent Operational History` table
- targeted verification passed (`47 passed in 311.75s`) across `test_storage_run_history.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 974.46s`)

### N1-WP-004 (completed readiness-truth evidence-lane slice)
Name:
Extend the normalized operational evidence lane so it also carries explicit readiness / release truth (`release_verdict`, `known_gaps`, and blocked-vs-degraded interpretation) alongside the runtime governance metrics.

Closure achieved:
- `src/siasa/data/storage.py` now persists and reloads readiness-lane summary fields in run history: `release_verdict`, `readiness_interpretation`, and `known_gap_count`
- `src/siasa/runs/operational_latest.py` now reads `readiness.json` from the artifact bundle and injects release truth into `operational_evidence_lane.json`: `release_verdict`, full `known_gaps`, `suppressed_known_gaps`, `known_gap_suppression_reason`, and a derived blocked-vs-degraded interpretation (`release_ready`, `degraded_but_release_ready`, `runtime_degraded_and_release_blocked`, etc.)
- `src/siasa/gui/local_app.py` now exposes that readiness truth directly in `runs.html` via KPI cards, evidence-lane summary text, latest-known-gaps detail, and recent-history columns for release verdict / readiness interpretation / known-gap count
- targeted verification passed (`47 passed in 312.85s`) across `test_storage_run_history.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 996.59s`)

### N1-WP-005 (completed latest-bundle evidence navigation slice)
Name:
Add fresh-bundle deep links from the operational evidence lane into the exact readiness / coverage / release artifacts so an operator can pivot from summary truth to the governing evidence without manual file hunting.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now stamps machine-readable `evidence_links` into `readmodels/operational_evidence_lane.json` for the latest bundle, covering coverage/readiness/release surfaces plus exported JSON artifacts (`coverage.html`, `source_coverage.json`, `system_status.json`, `readiness.html`, `readiness.json`, `release_package.html`, `release_demo_package.json`, `release_gate.json`)
- `src/siasa/gui/local_app.py` now exports `source_coverage.json` and `system_status.json` beside the generated GUI pages so those evidence links resolve inside the local bundle
- `src/siasa/gui/local_app.py` now renders a `Latest bundle evidence links` block in `runs.html` and adds an `Evidence` column in `Recent Operational History`, allowing one-click pivots from the evidence lane into the governing coverage/readiness/release artifacts for the latest bundle
- targeted verification passed (`43 passed in 319.55s`) across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 990.05s`)

### N1-WP-006 (completed archived-bundle history navigation slice)
Name:
Persist exact past-bundle artifact/gui paths in operational run history so recent-history rows can deep-link not only to the current latest bundle, but also to the exact archived bundle for each recorded run.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now carries `artifacts_dir`, `gui_index`, and per-row `evidence_links` into `recent_runs`, deriving deep links from each run’s own archived GUI bundle instead of only from the current latest bundle
- `src/siasa/gui/local_app.py` now renders the `Evidence` history column from each row’s own `evidence_links`, including direct `Bundle`, `Coverage`, `Readiness`, and `Release` pivots for archived runs
- targeted verification passed (`47 passed in 315.87s`) across `test_storage_run_history.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 983.10s`)

### N1-WP-007 (completed archived structured-evidence navigation slice)
Name:
Extend archived history evidence navigation to machine-readable per-run JSON artifacts and explicit bundle-root metadata so historical audits can pivot not only into rendered pages, but also into the exact archived structured evidence payloads.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now stamps absolute bundle-root metadata into `operational_evidence_lane.json` (`bundle_root`, `artifacts_dir`, `gui_index`) and derives per-run archived JSON links from each row’s own bundle root
- `src/siasa/gui/local_app.py` now renders latest-bundle root metadata in the evidence lane and enriches each history-row `Evidence` cell with both page links (`Bundle`, `Coverage`, `Readiness`, `Release`) and machine-readable JSON pivots (`Coverage JSON`, `System JSON`, `Readiness JSON`, `Release JSON`, `Gate JSON`) plus explicit `bundle_root` / `artifacts_dir` metadata
- targeted verification passed (`43 passed in 315.44s`) across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 1008.17s`)

### N1-WP-008 (completed archived evidence handoff-reference slice)
Name:
Add compact copy/shareable archived evidence references in history rows so operators can lift exact bundle/json references for external review or incident handoff without manual path assembly.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now stamps machine-readable `share_refs` alongside archived evidence links for both latest and historical rows, using compact reference strings such as `bundle:/...`, `coverage_json:/...`, `readiness_json:/...`, and `release_gate_json:/...`
- `src/siasa/gui/local_app.py` now renders a `Latest bundle share refs` block in the evidence lane and appends compact `<code>` handoff references to each history-row `Evidence` cell, so operators can lift exact archived references without reconstructing paths manually
- targeted verification passed (`43 passed in 326.85s`) across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 1012.78s`)

### N1-WP-009 (completed evidence handoff-summary slice)
Name:
Add concise run-level evidence handoff summaries in recent history so each archived row exposes one compact operator-facing sentence summarizing the bundle location and the primary JSON evidence targets for external review.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now stamps machine-readable `handoff_summary` text for latest and historical rows, summarizing the bundle path plus the primary structured evidence review targets (`readiness_json`, `coverage_json`, `release_gate_json`)
- `src/siasa/gui/local_app.py` now renders the latest-bundle `Handoff summary` in the evidence lane and appends a dedicated handoff-summary line to each history-row `Evidence` cell above the compact share refs
- targeted verification passed (`43 passed in 322.68s`) across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 992.78s`)

### N1-WP-010 (completed history triage-tag slice)
Name:
Add concise operator triage tags to history rows so archived runs can be skimmed quickly by handoff relevance (for example degraded-release-blocked vs ready-green) before opening detailed evidence.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now derives machine-readable review posture fields (`triage_tag`, `triage_summary`) for latest and archived runs from runtime status, governance verdict, policy gate, release verdict, readiness interpretation, known-gap count, and failed-source count
- the current bounded tag set now distinguishes at least `degraded_release_blocked`, `degraded_but_release_ready`, `ready_green`, and fallback `review_required`
- `src/siasa/gui/local_app.py` now surfaces the latest-bundle triage posture directly in the evidence lane and adds a dedicated `Triage Tag` history column plus inline per-row triage summary text in the `Evidence` cell
- targeted verification passed (`43 passed in 318.49s`) across `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, `test_scheduler.py`, and `test_local_gui.py`
- full regression passed (`472 passed in 994.16s`)

### N1-WP-011
Name:
Add compact operator-side filtering / counts by triage tag in recent operational history so archived runs can be narrowed quickly to blocked, degraded-but-ready, or green baselines without manual scanning.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a quick triage-control surface above the recent-history table with `operational-history-triage-filter`, static triage-tag counts, dynamic visible-run count, and a dynamic visible triage-count summary
- each recent-history row now carries `.operational-history-row` plus `data-triage-tag`, and `applyOperationalHistoryTriageFilter()` deterministically narrows the visible slice without touching the underlying evidence metadata
- `tests/unit/test_local_gui.py` now asserts the new controls, counts, row markers, and filter hook in generated `runs.html`
- targeted verification passed (`43 passed in 329.45s`) across `test_local_gui.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, and `test_scheduler.py`
- full regression passed (`472 passed in 1011.57s`)
- capability matrix updated
- this master steering document updated if frontier changed
- commit + push completed

### N1-WP-012
Name:
Expose explicit persisted recency timestamps in recent operational history so operators can read chronology directly from the evidence-lane table instead of inferring it from run IDs or bundle paths.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a `Recorded At` column in `operational-evidence-history-table` and fills each `.operational-history-row` from persisted `recorded_at`
- the table empty-state colspan was aligned with the expanded 14-column layout so no-history rendering remains structurally correct
- `tests/unit/test_local_gui.py` now asserts the new header plus deterministic rendered timestamps `2026-05-11T18:00:00Z` and `2026-05-10T18:00:00Z`
- targeted verification passed (`43 passed in 320.37s`) across `test_local_gui.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, and `test_scheduler.py`
- full regression passed (`472 passed in 1011.48s`)

### N1-WP-013
Name:
Expose relative recency deltas in recent operational history so archived runs are not only timestamped but also immediately readable as lag behind the freshest bundle.

Closure achieved:
- `src/siasa/gui/local_app.py` now computes the latest persisted `recorded_at` in `recent_runs` and renders a dedicated `Hours Behind Latest` column beside `Recorded At`
- each `.operational-history-row` now shows a deterministic relative lag such as `0h` for the freshest row and `24h` for the prior row, while preserving existing triage/evidence rendering
- `tests/unit/test_local_gui.py` now asserts the new header plus rendered lag values `0h` and `24h`
- targeted verification passed (`43 passed in 315.83s`) across `test_local_gui.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, and `test_scheduler.py`
- full regression passed (`472 passed in 984.15s`)

### N1-WP-014
Name:
Turn relative recency into a direct operator-side review control so archived runs can be narrowed immediately to `latest`, `last_24h`, or older chronology slices.

Closure achieved:
- `src/siasa/gui/local_app.py` now stamps each `.operational-history-row` with deterministic `data-recency-band` derived from `recorded_at` / `Hours Behind Latest`
- `runs.html` now renders `operational-history-recency-filter` plus static `operational-history-recency-counts` and dynamic `operational-history-visible-recency-counts` beside the existing triage controls
- `applyOperationalHistoryTriageFilter()` now combines triage-tag and recency-band filtering in one client-side pass and recomputes both visible triage counts and visible recency counts from the currently shown slice only
- `tests/unit/test_local_gui.py` now asserts the new filter, summaries, and deterministic fixture recency bands `latest` / `last_24h`
- targeted verification passed (`43 passed in 322.29s`) across `test_local_gui.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, and `test_scheduler.py`
- full regression passed (`472 passed in 990.35s`)

### N1-WP-015
Name:
Add explicit history ordering control so the operator can read the same filtered run slice newest-first, oldest-first, or grouped by triage posture without relying on one hardcoded table order.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-sort` with options `latest-first`, `oldest-first`, and `triage-tag-asc`
- each `.operational-history-row` now exposes stable sort metadata via `data-recorded-at` and numeric `data-hours-behind-latest`
- new client-side helper `sortOperationalHistoryRows()` reorders the `operational-evidence-history-table` body, and `applyOperationalHistoryTriageFilter()` now invokes it while preserving combined triage/recency filtering plus visible-slice summaries
- `tests/unit/test_local_gui.py` now asserts the new sort control, options, row metadata, and JS hook name
- targeted verification passed (`43 passed in 315.46s`) across `test_local_gui.py`, `test_operational_latest.py`, `test_latest_bundle_verification.py`, `test_live_probe_policy_gate.py`, and `test_scheduler.py`
- full regression passed (`472 passed in 986.68s`)

### N1-WP-016
Name:
Add free-text history discovery and explicit active-state/reset controls so operators can locate archived runs by run id / pilot set / posture / handoff wording and can always see the exact review slice they are looking at.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-text-filter`, `operational-history-reset`, and `operational-history-active-state` beside the existing triage/recency/sort controls in `runs.html`
- each `.operational-history-row` now exposes deterministic `data-history-search-text` compiled from run id, timestamp, pilot set, country-set identity, release posture, triage summary, and handoff summary so discovery stays client-side and testable
- `applyOperationalHistoryTriageFilter()` now combines triage-tag, recency-band, sort, and free-text predicates in one pass, while `renderOperationalHistoryActiveState()` and `resetOperationalHistoryFilters()` keep the current slice explicit and reproducible
- `tests/unit/test_local_gui.py` now asserts the new control IDs, placeholder text, active-state summary, row search payload, and JS hook names
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` (`1 passed in 1.97s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` (`24 passed in 0.24s`)

### N1-WP-017
Name:
Add shareable hash-state links for operational-history review controls so an operator can hand off the exact triage/recency/sort/search slice as one reproducible URL.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-copy-link` plus `operational-history-link-status` in the runs-view control bar
- the history filter block now supports `getOperationalHistoryState()`, `serializeOperationalHistoryState()`, `persistOperationalHistoryStateToHash()`, `applyOperationalHistoryStateFromHash()`, and `copyOperationalHistoryFilterLink()` with deterministic `#oh=` state covering triage, recency, sort, and free-text search
- `resetOperationalHistoryFilters()` now clears both control state and the hash-backed share state deterministically, while initial page load restores any incoming `#oh=` slice before applying the combined filter logic
- `tests/unit/test_local_gui.py` now asserts the new copy-link controls plus the hash-state function names and query keys (`oh_triage`, `oh_recency`, `oh_sort`, `oh_text`)
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-018
Name:
Add preset quick-link review modes for operational history so common audit intents can be reached in one click instead of being rebuilt manually from triage/recency/sort controls.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders preset buttons `operational-history-preset-blocked-review`, `operational-history-preset-latest-only`, `operational-history-preset-ready-green`, and `operational-history-preset-oldest-audit`
- new helper `applyOperationalHistoryPreset()` deterministically maps each preset onto the existing triage/recency/sort/text controls and reuses the existing share-hash flow
- preset application now surfaces explicit status text via `operational-history-link-status`, so operator handoff feedback is visible even before copying a link
- `tests/unit/test_local_gui.py` now asserts the preset control IDs, `data-operational-history-preset` markers, button labels, and `applyOperationalHistoryPreset()` hook
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-019
Name:
Add visible-slice handoff summary export for operational history so the exact currently visible archived-run slice can be copied as one compact deterministic summary.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-visible-summary` plus `operational-history-copy-summary` in the runs-view control block
- new helpers `buildOperationalHistoryVisibleSummary()` and `copyOperationalHistoryVisibleSummary()` summarize the currently visible rows as deterministic `visible_runs / run_ids / triage / recency` text and make it directly copyable
- `applyOperationalHistoryTriageFilter()` now recomputes the visible-slice handoff summary from the currently shown rows only, keeping the summary causally aligned with triage/recency/sort/search/preset state
- `tests/unit/test_local_gui.py` now asserts the new visible-summary control IDs and helper names
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-020
Name:
Add machine-readable visible-slice export for operational history so the exact currently visible archived-run slice can be downloaded as deterministic JSON, not only copied as prose summary.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-export-json` plus `operational-history-visible-payload`
- new helpers `buildOperationalHistoryVisiblePayload()` and `exportOperationalHistoryVisiblePayload()` materialize the current visible rows as structured JSON with `visible_runs`, ordered `run_ids`, sorted `triage_counts`, and sorted `recency_counts`, then download it as `operational_history_visible_slice.json`
- `applyOperationalHistoryTriageFilter()` now refreshes the machine-readable payload from the currently shown rows only, keeping it causally aligned with triage/recency/sort/search/preset state
- `tests/unit/test_local_gui.py` now asserts the new export control IDs plus the payload/helper names
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-021
Name:
Add row-level metadata to the visible-slice JSON export so downstream review can consume the exact currently visible operational-history rows without reopening the HTML table.

Closure achieved:
- `src/siasa/gui/local_app.py` now extends `buildOperationalHistoryVisiblePayload()` with deterministic `rows[]` entries carrying `run_id`, `recorded_at`, `hours_behind_latest`, `run_status`, `pilot_set`, `country_set_id`, `combined_ce_ratio`, `governance_verdict`, `policy_gate_verdict`, `release_verdict`, `readiness_interpretation`, `triage_tag`, `known_gap_count`, and `failed_source_count`
- the visible-slice JSON export therefore now carries both aggregate slice counts and the concrete per-run metadata rows for the currently shown slice
- `tests/unit/test_local_gui.py` now asserts the new row-level payload field names in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-022
Name:
Add CSV export for the visible operational-history slice so the current archived-run review subset is directly usable in spreadsheet and audit workflows alongside the JSON export.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-export-csv`
- new helpers `buildOperationalHistoryVisibleCsv()` and `exportOperationalHistoryVisibleCsv()` emit the current visible rows as deterministic CSV aligned to the rendered history table columns and download it as `operational_history_visible_slice.csv`
- the CSV export reuses the current visible slice, so export content remains causally aligned with triage/recency/sort/search/preset state
- `tests/unit/test_local_gui.py` now asserts the new CSV export control ID, helper names, MIME text, and filename
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-023
Name:
Add clipboard-copy support for the visible operational-history CSV slice so the currently filtered archived-run subset can be pasted directly into chat, tickets, and incident notes without a file-download round trip.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `operational-history-copy-csv` beside the existing visible-slice export controls in `runs.html`
- new helper `copyOperationalHistoryVisibleCsv()` reuses the existing deterministic `buildOperationalHistoryVisibleCsv()` output and copies the current visible slice via `navigator.clipboard.writeText(...)`
- the runs-view status surface now emits explicit copy feedback (`Visible CSV copied.` / `Visible CSV copy unavailable in this browser.`), keeping clipboard handoff semantics operator-visible and bounded
- `tests/unit/test_local_gui.py` now asserts the new copy control, helper hook, and clipboard status strings in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_scheduler.py -q` passed

### N1-WP-024
Name:
Add country-level dual C/E gap governance to the live-probe digest and policy gate so broader runtime slices cannot pass purely on aggregate combined C/E ratio while multiple countries still miss both structured Domain C and Domain E evidence.

Closure achieved:
- `src/siasa/readmodels/live_probe_evidence_digest.py` now emits deterministic country lists for `countries_missing_domain_c`, `countries_missing_domain_e`, `countries_missing_both_ce`, and `countries_with_full_ce` inside `ce_utilization`
- `src/siasa/readmodels/live_probe_policy_gate.py` now supports policy field `max_countries_missing_both_ce`, exports the same threshold in the gate result, and fail-closes with blocker `countries_missing_both_ce_above_threshold:*` when too many countries lack both C and E evidence
- `scripts/ci_live_probe_digest_gate_check.py` now exposes CLI override `--max-countries-missing-both-ce`, preserving profile-based governance while keeping runtime-specific overrides explicit
- `vmodel/project/live_probe_policy_profiles.yaml` now versions the new threshold by posture (`strict=0`, `standard=1`, `degraded=8`), and `tests/unit/test_operational_latest.py` fixture policy setup was synchronized to the new profile contract
- `tests/unit/test_live_probe_evidence_digest.py` now asserts the deterministic country-level gap lists; `tests/unit/test_live_probe_policy_gate.py` now asserts the new blocker and observed counters
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/live_probe_evidence_digest.py src/siasa/readmodels/live_probe_policy_gate.py scripts/ci_live_probe_digest_gate_check.py tests/unit/test_live_probe_evidence_digest.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_operational_latest.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_live_probe_evidence_digest.py tests/unit/test_live_probe_policy_gate.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_governed_live_runtime.py -q` passed

Fallback reprioritization rule:
- if valid source credentials/registrations become available before the next evidence-lane slice starts, reassess whether a credential-activation slice should jump ahead

---

## 7. Trigger for the next steering pivot

Stay on the current steering path until one of these becomes true:
- a broader runtime slice is successfully closed and the next largest gap becomes credentialed source activation
- valid ReliefWeb/UCDP credentials become available and activation becomes the highest-value bounded next slice
- operational evidence-lane inconsistency becomes the main blocker for truthful steering
- external steering explicitly prioritizes multi-user/server-backed deployment

Until then, do not reopen the old AP-F/AP-N/L3/L4 planning generations as active steering sources.

---

## 8. Historical-plan treatment rule

The following documents are historical/reference documents and must not be treated as current next-step steering authorities:
- `docs/plans/siasa-functional-implementation-plan.md`
- `docs/plans/siasa-stakeholder-gap-sweep-and-development-sequence.md`
- `docs/plans/siasa-stakeholder-functional-closure-gap-plan.md`
- `docs/plans/siasa-level-3-user-value-flow-plan.md`
- `docs/plans/siasa-level-4-demo-release-readiness-plan.md`
- `docs/plans/siasa-initial-implementation-workpackages.md`
- `docs/plans/siasa-p0-wp-001-source-access-assessment.md`
- `docs/plans/siasa-p0-wp-002c-domain-b-source-selection.md`

They remain useful only for:
- historical rationale
- traceability
- explaining how the current baseline was reached
- source-access constraint recall

---

## 9. Steering conclusion

SIASA no longer suffers from missing plans.
SIASA now suffers from planning-generation overlap.

Therefore the correct steering rule from now on is simple:
- this document is the single steering document
- the capability matrix is the detailed operational evidence companion
- the next default work stays on runtime/source breadth expansion
- release/distribution lifecycle closure follows after breadth/evidence normalization unless credentials change priority sooner
