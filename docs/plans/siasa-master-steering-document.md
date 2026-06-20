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
- broader governed runtime breadth is now materially proven through the full `mvp-complete` slice in code, tests, and fresh operational evidence
- the latest closure probe `RUN-OP-LATEST-G1-CLOSE-001` produced `country_set_id=MVP-COUNTRIES-LIVE-mvp-complete-v1`, `countries_with_updates=30/30`, `breadth_coverage_tag=breadth_full_slice_updated`, and policy gate verdict `pass`
- this means the repo-controlled G1 question (“can SIASA operationally cover the governed full MVP slice at all?”) is now answered yes

Remaining gap:
- no further meaningful repo-only G1 closure remains
- the remaining runtime delta is provider/source degradation truth (`SRC-GDELT-DOC`, `SRC-GDELT-DOC-E`) and release/readiness consequence handling, not unsupported governed breadth

Why it matters:
- G1 is no longer the main internal product frontier
- breadth proof is now operationally closed for the governed full-MVP slice even when release truth remains degraded by live-source outages

### G2. Credential-/provider-gated source activation

Current truth:
- code paths/adapters exist for source classes such as ReliefWeb and UCDP
- graceful degradation exists when credentials/registration are absent
- artifact-backed coverage evidence now distinguishes raw credential configuration from actual activation closure truth (`activated_with_live_evidence`, `configured_but_not_evidenced`, `credentialed_but_live_fetch_failed`, `external_blocker_present`)
- for the current environment, ReliefWeb remains externally blocked by missing approved appname and UCDP is not operationally evidenced via a configured token, so the remaining blocker is external/operator-side rather than an unimplemented repo slice

Remaining gap:
- no further meaningful repo-only G2 closure remains without external credentials/app registrations
- the next real G2 step is operational follow-through: provide valid credentials/registration and execute one governed live run that captures source-success evidence

Why it matters:
- “adapter exists” is not equivalent to “stakeholder-visible source breadth exists in operations”
- but after the new closure-truth surfaces, the remaining delta is now an external dependency handoff rather than an internal product-ambiguity problem

### G3. Operational evidence-lane normalization

Current truth:
- the repo now has one normalized operator/project-lead evidence lane that carries runtime breadth truth, release truth, verification posture, archived evidence pivots, handoff summaries, visible-slice exports, and explicit evidence freshness / authority status
- fresh closure evidence was captured with `RUN-OP-LATEST-G3-CLOSE-001` on `pilot_set=mvp-complete`, writing `build/run_artifacts/latest-g3-close-001` and `build/local_gui/latest-g3-close-001/index.html`
- that fresh bundle now explicitly reports `recorded_at`, `evidence_freshness_status=fresh_current`, and `evidence_lane_closure_status=evidence_lane_fresh_but_override_governed`, so steering can distinguish fresh authoritative degraded truth from stale or timestamp-ambiguous evidence

Remaining gap:
- no further meaningful repo-only G3 closure remains
- future G3 work, if any, should be probe-driven refinements on top of the now-authoritative lane rather than another open package family

Why it matters:
- a mature system needs not only code closure but fresh, reviewable, current operational evidence
- that repo-controlled need is now materially satisfied: SIASA can show whether the latest lane is fresh, authoritative, stale, or override-governed without opening raw JSON or reconstructing time context manually

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

### Priority 1 (materially closed): G4 Approval-to-distribution release lifecycle
Status: repo-controlled closed.
- WP-001: approval lifecycle record + artifact emission + GUI panel in release_package.html — Done
- WP-002: transition CLI (approve/approve_with_conditions/defer/reject/distribute) + Evidence-Lane in runs.html — Done
- Operator can now execute `python scripts/lifecycle_transition.py approve --record-path ...` and see the result in both release_package.html and runs.html
- No further default G4 slice is currently required

### Priority 2: External credentialed-source activation follow-through (triggered, not default)
Why conditional:
- repo-controlled G2 closure is materially complete: blockers, next actions, country scope, and activation-vs-evidence truth are explicit
- the next real step depends on external credential/app-registration availability rather than further internal implementation
- jump this back upward immediately if valid ReliefWeb/UCDP credentials become available

### Priority 3: Deferred architecture uplifts (G5)
Why last/default deferred:
- multi-user/server-backed architecture is valuable only if the target operating model explicitly requires it now
- no current external steering demand for G5

### Default next work (post-G4 closure)
With G1, G2 (repo-controlled), G3, and G4 all materially closed, the program frontier has shifted.

Current default internal track:
- validation realism depth / analyst handoff refinement on top of the now-closed replay-attention watchlist baseline

The remaining substantive internal next-step candidates are:
1. G4 follow-through hardening if live operational use reveals gaps (probe-driven, not speculative)
2. Broader runtime/source breadth expansion if a new country cluster or source class becomes the priority
3. G5 architecture decision only if multi-user deployment is now required by external steering
4. Validation realism depth (broader non-perfect historical replay portfolios and stronger analyst handoff/export surfaces) if interpretation quality is the bottleneck

Decision rule for next package selection:
- If no external trigger (credentials, operating-model change, new country demand) exists, the next default internal package should be the one with the highest stakeholder-visible impact from the candidates above
- Prefer probe-driven packages over speculative breadth expansion

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

### N1-WP-025
Name:
Propagate the new country-level dual C/E gap signal into latest-bundle verification and operational-latest summaries so broader governed runs can be validated and reviewed against that metric without opening raw digest JSON manually.

Closure achieved:
- `src/siasa/runs/latest_bundle_verification.py` now reads `countries_missing_both_ce` from `live_probe_evidence_digest.json`, verifies count/list consistency against `live_probe_policy_gate.json observed`, and returns `countries_missing_both_ce_count` plus `countries_missing_both_ce` in the machine-readable verification summary
- `src/siasa/runs/operational_latest.py` now propagates those verified fields into `verification_summary` and the fresh `operational_evidence_lane.json latest_summary`, so the bounded operator/runtime summary carries the same governed signal
- `tests/unit/test_latest_bundle_verification.py` now asserts accepted-summary propagation and rejects digest/gate mismatch on the new metric; `tests/unit/test_operational_latest.py` now asserts operational-latest propagation of the verified fields
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/latest_bundle_verification.py src/siasa/runs/operational_latest.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_latest_bundle_verification.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_governed_live_runtime.py tests/unit/test_live_probe_policy_gate.py -q` passed

### N1-WP-026
Name:
Make live-probe governance operator guidance explicitly country-specific for the dual C/E gap case so broader runtime triage does not stop at a generic aggregate warning.

Closure achieved:
- `src/siasa/readmodels/live_probe_evidence_digest.py` now upgrades governance to `amber` when `countries_missing_both_ce` is non-empty even without failed sources, stamps reason `countries_missing_both_ce_present`, and emits a country-specific `operator_next_action` such as `Increase structured Domain C/E coverage in countries missing both signals (POL).`
- failed-source actionability was also sharpened: `operator_next_action` now includes explicit failed source IDs when source outages are the primary issue
- `tests/unit/test_live_probe_evidence_digest.py` now asserts both the new country-specific dual-C/E action text and the enriched failed-source action text
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/live_probe_evidence_digest.py tests/unit/test_live_probe_evidence_digest.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_live_probe_evidence_digest.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_live_probe_policy_gate.py tests/unit/test_operational_latest.py tests/unit/test_governed_live_runtime.py -q` passed

### N1-WP-027
Name:
Fail-close latest-bundle verification on live-probe policy-gate failure by default, while preserving an explicit override path for degraded inspection use cases.

Closure achieved:
- `src/siasa/runs/latest_bundle_verification.py` now rejects `gate_verdict=fail` by default and only accepts it when `allow_policy_gate_fail=True`
- `src/siasa/runs/operational_latest.py` now threads `allow_policy_gate_fail` into bounded latest-bundle verification so operational-latest generation stays aligned with the governed live-probe gate contract
- `scripts/verify_latest_bundle.py` now exposes CLI flag `--allow-policy-gate-fail` for explicit degraded inspection mode
- `tests/unit/test_latest_bundle_verification.py` now asserts both default rejection and explicit acceptance of policy-gate fail bundles; `tests/unit/test_operational_latest.py` now asserts both default rejection and explicit acceptance in operational-latest flow under a constructed dual-C/E gap gate-fail scenario
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/latest_bundle_verification.py src/siasa/runs/operational_latest.py scripts/verify_latest_bundle.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_latest_bundle_verification.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_governed_live_runtime.py tests/unit/test_live_probe_policy_gate.py -q` passed

### N1-WP-028
Name:
Expose the explicit `allow_policy_gate_fail` degraded-inspection override on the operational-latest build CLI so automation and operators are not forced onto the Python API for parity with latest-bundle verification behavior.

Closure achieved:
- `scripts/build_operational_latest_bundle.py` now exposes CLI flag `--allow-policy-gate-fail`
- the operational-latest CLI now threads that flag into `build_operational_latest_bundle(..., allow_policy_gate_fail=...)`
- `tests/unit/test_build_operational_latest_bundle_script.py` now asserts the CLI passes the override into the builder and still emits the standard summary line
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile scripts/build_operational_latest_bundle.py tests/unit/test_build_operational_latest_bundle_script.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_build_operational_latest_bundle_script.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_latest_bundle_verification.py -q` passed

### N1-WP-029
Name:
Persist and expose explicit verification-override provenance for accepted degraded operational bundles so later reviewers can distinguish strict-mode closure from intentionally override-enabled inspection/runtime runs.

Closure achieved:
- `src/siasa/runs/latest_bundle_verification.py` now emits `verification_policy` plus ordered `enabled_verification_overrides` in bundle verification summaries
- `src/siasa/runs/operational_latest.py` now builds the same verification-policy view model, persists the flags through run-history writes, and surfaces them in `operational_evidence_lane.json` for both the latest bundle and loaded recent runs
- `src/siasa/data/storage.py` schema and `RunHistoryEntry` now persist `allow_partial_success`, `allow_failed_sources`, and `allow_policy_gate_fail` as explicit run-history provenance fields
- `tests/unit/test_storage_run_history.py`, `tests/unit/test_latest_bundle_verification.py`, and `tests/unit/test_operational_latest.py` now assert both strict-mode and override-enabled provenance behavior
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/data/storage.py src/siasa/runs/latest_bundle_verification.py src/siasa/runs/operational_latest.py tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_build_operational_latest_bundle_script.py -q` passed

### N1-WP-030
Name:
Expose strict-vs-override verification provenance directly in the runs GUI and visible-slice exports so project lead/operators can see at a glance whether an operational bundle is strict-mode or explicitly degraded/override-enabled.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `Verification mode` and `Enabled overrides` in the Operational Evidence Lane summary
- the recent operational-history table now includes explicit columns `Verification Mode` and `Enabled Overrides`
- visible-slice JSON and CSV export builders now carry `verification_mode` and `enabled_overrides`
- `tests/unit/test_local_gui.py` now seeds verification-policy fixture data and asserts the new GUI/export strings and search payload behavior
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_load_site_payload_from_artifacts_reads_persisted_json_bundle -q` passed
- adjacent runtime/storage regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_operational_latest.py tests/unit/test_storage_run_history.py -q` passed

### N1-WP-031
Name:
Expose verification-mode truth in the copied operational-history visible-slice summary so the smallest operator handoff surface preserves strict-vs-override governance context instead of dropping it.

Closure achieved:
- `src/siasa/gui/local_app.py` now extends `buildOperationalHistoryVisibleSummary()` with deterministic `verification=` and `overrides=` composition summaries derived from the currently visible rows
- the initial `operational-history-visible-summary` placeholder now matches the stronger copied-handoff contract (`verification=none | overrides=none` before any rows are visible)
- `tests/unit/test_local_gui.py` now asserts the new summary placeholder shape plus the generated helper output markers for verification/override composition
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_operational_latest.py tests/unit/test_storage_run_history.py -q` passed

### N1-WP-032
Name:
Expose machine-readable verification-mode composition in the operational-history visible-slice JSON payload so downstream audit/export consumers preserve strict-vs-override slice truth without row-by-row reconstruction.

Closure achieved:
- `src/siasa/gui/local_app.py` now extends `buildOperationalHistoryVisiblePayload()` with deterministic top-level `verification_mode_counts` and `override_profile_counts` aggregates derived from the currently visible rows
- per-row payload fields remain unchanged, but exported visible-slice JSON now also carries slice-level verification composition directly for machine consumers
- `tests/unit/test_local_gui.py` now asserts the new payload keys plus the helper wiring strings `verification_mode_counts: verificationModeCounts` and `override_profile_counts: overrideProfileCounts`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_operational_latest.py tests/unit/test_storage_run_history.py -q` passed

### N1-WP-033
Name:
Add a one-page executive steering view of the next large SIASA package families so project-lead communication can stay compact without creating a competing steering source.

Closure achieved:
- added `docs/plans/siasa-next-big-packages-executive-view.md` as a compact management-facing summary of the next major package families (`G1`, `G2`, `G4`, `G5`) with target state, user value, main risks, dependencies/gating, relative size, recommended order, and next bounded package focus
- updated `docs/plans/siasa-planning-audit-and-next-steps.md` to classify the new file as an active project-lead communication layer
- updated `docs/plans/siasa-stakeholder-fulfillment-roadmap.md` with a direct shortcut reference to the executive view while keeping the master steering document as the single execution authority
- validation evidence: targeted documentation check script passed and confirmed the new executive-view file plus expected headings/references; fulfillment recomputation remains `17/17 Done`, `100.0%`

### N1-WP-034
Name:
Expose governed slice country-coverage breadth truth in latest-bundle verification, persisted run history, and the operational evidence lane so broader-runtime value is visible as actual updated-country scope rather than only pilot-set naming.

Closure achieved:
- `src/siasa/runs/latest_bundle_verification.py` now validates and returns `countries_total`, `countries_with_updates`, `countries_without_updates_count`, and `countries_without_updates` from `system_status.json coverage`, with fail-closed checks against impossible count combinations
- `src/siasa/data/storage.py` and `RunHistoryEntry` now persist those breadth metrics through run history so broader-slice evidence remains historically comparable
- `src/siasa/runs/operational_latest.py` now propagates the same coverage-scope fields into `latest_summary` and `recent_runs` inside `operational_evidence_lane.json`
- `src/siasa/gui/local_app.py` now surfaces `Coverage scope` and countries-without-updates truth directly in the Operational Evidence Lane and in each archived history evidence cell
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/data/storage.py src/siasa/runs/latest_bundle_verification.py src/siasa/runs/operational_latest.py src/siasa/gui/local_app.py tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`23 passed`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_live_probe_policy_gate.py tests/unit/test_live_probe_evidence_digest.py -q` passed (`11 passed`)

### N1-WP-035
Name:
Expose the concrete countries-without-updates list in persisted run history and the operational evidence lane so broader-slice breadth loss can be audited and handed off by affected country, not only by aggregate count.

Closure achieved:
- `src/siasa/data/storage.py` and `RunHistoryEntry` now persist `countries_without_updates` as a historical JSON list alongside the breadth counts
- `src/siasa/runs/operational_latest.py` now propagates the same list into `latest_summary` and `recent_runs` inside `operational_evidence_lane.json`
- `src/siasa/gui/local_app.py` now renders `Countries without updates (...)` detail in the latest evidence lane, adds a concrete `Countries without updates: ...` line in each archived history evidence cell, and threads the missing-country IDs into the history search payload
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/data/storage.py src/siasa/runs/latest_bundle_verification.py src/siasa/runs/operational_latest.py src/siasa/gui/local_app.py tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_storage_run_history.py tests/unit/test_latest_bundle_verification.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`23 passed`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_live_probe_policy_gate.py tests/unit/test_live_probe_evidence_digest.py -q` passed (`11 passed`)

### N1-WP-036
Name:
Expose an explicit breadth-coverage qualification in the operational evidence lane so broader-runtime runs read immediately as full breadth proof, partial breadth proof, or non-usable breadth proof instead of requiring manual interpretation of counts and missing-country lists.

Closure achieved:
- `src/siasa/runs/operational_latest.py` now derives deterministic `breadth_coverage_tag` and `breadth_coverage_summary` from `countries_total`, `countries_with_updates`, and `countries_without_updates`
- `src/siasa/gui/local_app.py` now surfaces `Breadth coverage` plus a human-readable summary in the latest Operational Evidence Lane and renders the same posture in archived history evidence cells
- the history search payload now also includes the breadth-coverage tag/summary so slice discovery remains aligned with the newly surfaced posture
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/data/storage.py src/siasa/runs/operational_latest.py src/siasa/gui/local_app.py tests/unit/test_storage_run_history.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_storage_run_history.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`12 passed`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_latest_bundle_verification.py tests/unit/test_live_probe_policy_gate.py tests/unit/test_live_probe_evidence_digest.py -q` passed (`22 passed`)

### N1-WP-037
Name:
Propagate breadth-coverage posture composition into the copied visible-slice summary and machine-readable JSON export so operational-history handoff keeps breadth-proof truth without forcing row-by-row reconstruction.

Closure achieved:
- `src/siasa/gui/local_app.py` now stamps each `.operational-history-row` with `data-breadth-coverage-tag` and `data-breadth-coverage-summary`, making the breadth posture reusable by the client-side summary/export helpers instead of remaining buried only in rendered evidence text
- `buildOperationalHistoryVisibleSummary(...)` now includes deterministic `breadth=` composition beside triage / recency / verification / override composition, and the initial visible-slice placeholder now starts from `breadth=none`
- `buildOperationalHistoryVisiblePayload(...)` now emits top-level `breadth_coverage_counts` plus per-row `breadth_coverage_tag` / `breadth_coverage_summary`, so downstream audit/export consumers receive breadth-proof posture directly in the machine-readable visible slice
- `tests/unit/test_local_gui.py` now asserts the strengthened visible-slice summary contract and the new breadth-coverage payload wiring in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.42s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py -q` passed (`19 passed in 334.67s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1029.64s`)

### N1-WP-038
Name:
Propagate breadth-coverage posture into the visible-slice CSV export/copy path so spreadsheet and clipboard handoff preserve breadth-proof truth alongside the existing run/governance fields.

Closure achieved:
- `src/siasa/gui/local_app.py` now extends `buildOperationalHistoryVisibleCsv(...)` with CSV columns `breadth_coverage_tag` and `breadth_coverage_summary`
- the CSV builder now reads those two breadth fields from the row-level `data-breadth-coverage-*` attributes, keeping CSV export/copy causally aligned with the same visible-slice breadth posture already used by summary and JSON export
- `tests/unit/test_local_gui.py` now asserts the CSV builder wiring includes the new breadth columns and row-attribute lookups in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.01s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py -q` passed (`19 passed in 326.36s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1030.80s`)

### N1-WP-039
Name:
Expose visible-slice breadth composition counts directly in the runs GUI so operators can read the currently filtered breadth-proof mix without inferring it only from the copied summary or exported artifacts.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a dedicated `Visible breadth counts` surface via `operational-history-visible-breadth-counts`
- `applyOperationalHistoryTriageFilter()` now derives deterministic `breadthCounts` from the visible rows using the row-level `data-breadth-coverage-tag` attribute and updates the GUI summary alongside visible triage and recency counts
- `tests/unit/test_local_gui.py` now asserts the new visible breadth-count placeholder and DOM hook in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.10s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py -q` passed (`19 passed in 325.50s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1031.43s`)

### N1-WP-040
Name:
Expose visible-slice verification composition counts directly in the runs GUI so operators can read the currently filtered strict-vs-override mix without inferring it only from the copied summary or exported artifacts.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a dedicated `Visible verification counts` surface via `operational-history-visible-verification-counts`
- `applyOperationalHistoryTriageFilter()` now derives deterministic `verificationCounts` from the visible rows using the `Verification Mode` column and updates the GUI summary alongside visible triage / recency / breadth counts
- `tests/unit/test_local_gui.py` now asserts the new visible verification-count placeholder and DOM hook in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.07s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py -q` passed (`19 passed in 325.57s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1008.82s`)

### N1-WP-041
Name:
Expose visible-slice override-profile counts directly in the runs GUI so operators can read the currently filtered override mix without inferring it only from the copied summary or exported artifacts.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a dedicated `Visible override counts` surface via `operational-history-visible-override-counts`
- `applyOperationalHistoryTriageFilter()` now derives deterministic `overrideCounts` from the visible rows using the `Enabled Overrides` column and updates the GUI summary alongside visible triage / recency / breadth / verification counts
- `tests/unit/test_local_gui.py` now asserts the new visible override-count placeholder and DOM hook in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.08s`)
- focused regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py -q` passed (`19 passed in 334.71s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1027.45s`)

### N1-WP-042
Name:
Expose one compact visible-slice governance digest directly in the runs GUI so operators can scan the currently filtered triage / recency / breadth / verification / override posture in one line instead of manually combining five separate summaries.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders a dedicated `Visible governance digest` surface via `operational-history-visible-governance-digest`
- added `buildOperationalHistoryVisibleGovernanceDigest(...)`, which composes one deterministic on-page digest from the same visible-slice `triageCounts`, `recencyCounts`, `breadthCounts`, `verificationCounts`, and `overrideCounts` already maintained by `applyOperationalHistoryTriageFilter()`
- `applyOperationalHistoryTriageFilter()` now refreshes that digest whenever the visible archived-run slice changes, keeping the compact operator line causally aligned with the detailed count rows and export surfaces
- `tests/unit/test_local_gui.py` now asserts the new placeholder text, DOM hook, and helper wiring in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.59s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1023.28s`)

### N1-WP-043
Name:
Expose the compact visible-slice governance digest in the machine-readable visible JSON payload so downstream review/export consumers receive the same one-line governance synthesis already shown in the GUI.

Closure achieved:
- `src/siasa/gui/local_app.py` now derives `governanceDigest` inside `buildOperationalHistoryVisiblePayload()` from the existing `buildOperationalHistoryVisibleGovernanceDigest(...)` helper instead of duplicating a second aggregation path
- the visible-slice JSON payload now exports that compact synthesis as top-level `governance_digest` beside `triage_counts`, `recency_counts`, `breadth_coverage_counts`, `verification_mode_counts`, and `override_profile_counts`
- `tests/unit/test_local_gui.py` now asserts the new payload field plus helper wiring in generated `runs.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.57s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1032.76s`)

### N1-WP-044
Name:
Harden the 21-country `focus-complete` latest path so broader operational-latest runs terminate deterministically with explicit degraded-mode truth instead of risking ambiguous no-output stalls under GDELT load.

Closure achieved:
- `src/siasa/runs/live_runtime.py` now applies a dedicated 21-country GDELT profile for `focus-complete`-scale runs: `recent_export_count=4`, `max_records=4`, `inter_request_delay_seconds=4.0`, `max_retry_delay_seconds=90.0`, `request_timeout_seconds=60.0`, `max_full_fetch_retries=1`, and `full_fetch_retry_cooldown_seconds=60.0`
- `tests/unit/test_governed_live_runtime.py` now asserts that the 21-country `focus-complete` orchestrator uses that bounded runtime profile instead of the looser 11-country settings
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/live_runtime.py tests/unit/test_governed_live_runtime.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_governed_live_runtime.py -q` passed (`26 passed in 4.49s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1021.77s`)
- real runtime evidence now shows deterministic bounded behavior on the broader 21-country latest path: strict attempts `RUN-OP-LATEST-FOCUS-HARDEN-001` and `RUN-OP-LATEST-FOCUS-HARDEN-002` both terminated fail-closed with explicit `run_status=partial_success` instead of stalling silently
- degraded inspection closure evidence: `RUN-OP-LATEST-FOCUS-HARDEN-DEG-003` completed with `country_set_id=MVP-COUNTRIES-LIVE-focus-complete-v1`, `countries_with_updates=21/21`, `failed_sources=[SRC-GDELT-DOC,SRC-GDELT-DOC-E]`, artifact bundle `build/run_artifacts/latest-focus-complete-harden-deg-003`, and GUI `build/local_gui/latest-focus-complete-harden-deg-003/index.html`

### N1-WP-045
Name:
Make credential-gated source activation readiness explicit in artifact-backed coverage evidence so G2 starts from visible operational blockers rather than hidden environment assumptions.

Closure achieved:
- `src/siasa/runs/live_runtime.py` now derives credential-gated activation readiness rows for `SRC-UCDP-GED` and `SRC-RELIEFWEB`, including credential name, configured state, blocked reason, provider requirement, and applicable governed country scope
- `src/siasa/runs/orchestrator.py`, `src/siasa/runs/artifacts.py`, `src/siasa/readmodels/source_coverage.py`, and `src/siasa/readmodels/system_status.py` now persist those rows as machine-readable `source_activation_readiness` in artifact bundles
- `src/siasa/gui/local_app.py` now renders a dedicated `Credential-gated Source Activation Readiness` table in `coverage.html`
- `tests/unit/test_governed_live_runtime.py` now asserts the representative orchestrator exposes correct readiness rows (`UCDP` configured in test env, `ReliefWeb` blocked without appname)
- `tests/unit/test_local_gui.py` now asserts the coverage page renders the new readiness table and blocker fields
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/source_coverage.py src/siasa/readmodels/system_status.py src/siasa/runs/artifacts.py src/siasa/runs/orchestrator.py src/siasa/runs/live_runtime.py src/siasa/gui/local_app.py tests/unit/test_governed_live_runtime.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_governed_live_runtime.py -q` passed (`26 passed in 4.23s`)
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.61s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1015.77s`)
- runtime evidence in the current environment: with neither `RELIEFWEB_APPNAME` nor `UCDP_API_TOKEN` configured, representative degraded bundle `RUN-OP-LATEST-G2-READINESS-001` completed and now persists `source_activation_readiness` into `build/run_artifacts/latest-g2-readiness-001/readmodels/source_coverage.json` and `system_status.json`; generated GUI `build/local_gui/latest-g2-readiness-001/coverage.html` renders both sources as `blocked_missing_credentials`

### N1-WP-046
Name:
Turn credential-gated source readiness from passive blocker visibility into explicit activation follow-through guidance so G2 can move from “blocked” to “do this next” without reopening code or planning context.

Closure achieved:
- `src/siasa/runs/live_runtime.py` now stamps deterministic `activation_next_step` guidance into the `source_activation_readiness` rows for `SRC-UCDP-GED` and `SRC-RELIEFWEB`
- the guidance is source-specific and environment-truthful: UCDP points to setting `UCDP_API_TOKEN`, while ReliefWeb points to obtaining an approved appname, setting `RELIEFWEB_APPNAME`, and rerunning the governed live pipeline
- `src/siasa/gui/local_app.py` now extends the `Credential-gated Source Activation Readiness` table with a `Next Step` column plus explanatory text, making the first real activation action directly visible in `coverage.html`
- `tests/unit/test_governed_live_runtime.py` now asserts the representative orchestrator exposes the new machine-readable next-step guidance
- `tests/unit/test_local_gui.py` now asserts the coverage page renders the new `Next Step` contract and both source-specific guidance strings
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/live_runtime.py src/siasa/gui/local_app.py tests/unit/test_governed_live_runtime.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_governed_live_runtime.py -q` passed (`26 passed in 4.55s`)
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.59s`)

### N1-WP-047
Name:
Add a compact credential-gated activation readiness summary so G2 status can be scanned immediately from counts and source lists before reading the detailed readiness table.

Closure achieved:
- `src/siasa/readmodels/source_coverage.py` now derives machine-readable `source_activation_readiness_summary` from the existing readiness rows
- the summary exposes deterministic `total_sources`, `blocked_source_count`, `configured_ready_count`, `status_counts`, `blocked_sources`, and `configured_ready_sources`
- `src/siasa/gui/local_app.py` now renders a dedicated `Credential-gated Source Activation Readiness Summary` table in `coverage.html` ahead of the detailed readiness table
- the GUI summary makes G2 scanable as one compact activation snapshot instead of requiring row-by-row reading of the full table
- `tests/unit/test_readmodels_country_profile.py` now asserts the new summary contract exists even when no credential-gated sources are present
- `tests/unit/test_local_gui.py` now asserts the generated coverage page renders the new G2 summary panel, counts, and source-list fields
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/source_coverage.py src/siasa/gui/local_app.py tests/unit/test_readmodels_country_profile.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_readmodels_country_profile.py -q` passed (`4 passed in 0.04s`)
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.20s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1018.45s`)

### N1-WP-048
Name:
Expose blocked-vs-ready governed country scope directly in the compact credential-gated activation summary so G2 breadth impact is readable immediately, not only after opening per-source readiness rows.

Closure achieved:
- `src/siasa/readmodels/source_coverage.py` now extends `source_activation_readiness_summary` with deterministic `blocked_applicable_country_count`, `blocked_applicable_countries`, `configured_ready_applicable_country_count`, and `configured_ready_applicable_countries`
- `src/siasa/gui/local_app.py` now renders `Configured-ready country scope/count` and `Blocked country scope/count` in the `Credential-gated Source Activation Readiness Summary` table
- `tests/unit/test_readmodels_country_profile.py` now asserts the empty-summary contract includes the new country-scope fields
- `tests/unit/test_local_gui.py` now seeds and asserts blocked-country-scope rendering (`POL, UKR`) in `coverage.html`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/source_coverage.py src/siasa/gui/local_app.py tests/unit/test_readmodels_country_profile.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_readmodels_country_profile.py -q` passed (`4 passed in 0.12s`)
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 3.84s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1024.14s`)

### N1-WP-049
Name:
Close the repo-controlled G2 package by deriving explicit activation-closure truth from runtime evidence plus credential state, so the remaining delta is clearly external credential follow-through rather than another internal ambiguity slice.

Closure achieved:
- `src/siasa/readmodels/source_coverage.py` now enriches each `source_activation_readiness` row with `runtime_source_status`, `activation_evidence`, `closure_status`, and `closure_next_step`, derived from both credential readiness and current source runtime status
- the same readmodel now derives a stronger `source_activation_readiness_summary` with `closure_status_counts`, explicit source buckets (`activated_with_live_evidence`, `external_blocker_present`, `credentialed_but_live_fetch_failed`, `configured_but_not_evidenced`), plus top-level `overall_closure_status` and `operator_next_step`
- `src/siasa/gui/local_app.py` now renders G2 closure truth directly in `coverage.html`: summary rows for closure status / external blockers / pending evidence / live evidence, and detailed table columns `Runtime Source Status`, `Activation Evidence`, and `Closure Posture`
- `tests/unit/test_readmodels_country_profile.py` now covers both the empty no-G2 case and a mixed `activated_with_live_evidence` + `external_blocker_present` case; `tests/unit/test_local_gui.py` now asserts the new closure-truth summary rows, explanatory text, and detailed table columns/values
- steering interpretation is now explicit: in the current environment no valid `RELIEFWEB_APPNAME` is configured and no operationally evidenced UCDP token-backed run exists, so the remaining G2 delta is external/operator-side follow-through rather than a missing repo implementation slice
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/readmodels/source_coverage.py src/siasa/gui/local_app.py tests/unit/test_readmodels_country_profile.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_readmodels_country_profile.py -q` passed (`5 passed in 0.04s`)
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.65s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`480 passed in 1024.14s`)

### N1-WP-050
Name:
Close the repo-controlled G1 package by deriving explicit breadth-closure truth and capturing one fresh full-MVP operational proof that separates governed breadth completion from degraded release truth.

Closure achieved:
- fresh closure evidence was generated with `RUN-OP-LATEST-G1-CLOSE-001` on `pilot_set=mvp-complete`, writing `build/run_artifacts/latest-g1-close-001` and GUI `build/local_gui/latest-g1-close-001/index.html`
- that fresh run produced `country_set_id=MVP-COUNTRIES-LIVE-mvp-complete-v1`, `countries_with_updates=30/30`, `breadth_coverage_tag=breadth_full_slice_updated`, and policy gate verdict `pass`, proving the governed full-MVP breadth slice operationally updates end-to-end even under degraded live-source conditions
- `src/siasa/runs/operational_latest.py` now derives explicit `breadth_closure_status` / `breadth_closure_summary`, separating `breadth_operationally_closed_green`, `breadth_operationally_closed_but_runtime_degraded`, and not-yet-closed partial/no-update cases from the lower-level coverage counts
- `src/siasa/gui/local_app.py` now renders that breadth-closure truth in the Operational Evidence Lane and archived-history evidence cells so project lead/operators can read whether breadth itself is closed even when release truth is still blocked by live-source failures
- `tests/unit/test_operational_latest.py` now asserts both partial-slice not-yet-closed and full-slice breadth-closed behavior; `tests/unit/test_local_gui.py` now asserts the new breadth-closure strings in `runs.html`
- steering interpretation is now explicit: the remaining runtime problem shown by `RUN-OP-LATEST-G1-CLOSE-001` is source degradation (`SRC-GDELT-DOC`, `SRC-GDELT-DOC-E`) plus release/readiness consequences, not missing governed breadth support
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/operational_latest.py src/siasa/gui/local_app.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`8 passed in 2.27s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`481 passed in 1003.64s`)

### N1-WP-051
Name:
Close the repo-controlled G3 package by making evidence freshness / authority explicit in the normalized operational evidence lane and by capturing one fresh full-MVP evidence-lane closure bundle.

Closure achieved:
- fresh closure evidence was generated with `RUN-OP-LATEST-G3-CLOSE-001` on `pilot_set=mvp-complete`, writing `build/run_artifacts/latest-g3-close-001` and GUI `build/local_gui/latest-g3-close-001/index.html`
- that fresh run produced `country_set_id=MVP-COUNTRIES-LIVE-mvp-complete-v1`, `countries_with_updates=30/30`, `policy_gate_verdict=pass`, `evidence_freshness_status=fresh_current`, and `evidence_lane_closure_status=evidence_lane_fresh_but_override_governed`, so the latest lane now distinguishes fresh authoritative degraded truth from stale or timestamp-ambiguous evidence
- `src/siasa/runs/operational_latest.py` now stamps `recorded_at`, `evidence_freshness_status`, `evidence_freshness_summary`, `evidence_age_hours`, `evidence_lane_closure_status`, and `evidence_lane_closure_summary` into both `latest_summary` and archived `recent_runs`; the fallback path now also stamps a build-time timestamp when persisted history is unavailable
- `src/siasa/gui/local_app.py` now renders those freshness/authority signals directly in the latest Operational Evidence Lane and in archived history evidence cells, so project lead/operators can read whether the lane is fresh, authoritative, stale, or override-governed without opening raw JSON
- `tests/unit/test_operational_latest.py` now fixes deterministic `now_provider` coverage for both green and override-governed latest bundles and asserts the new freshness/authority fields; `tests/unit/test_local_gui.py` now asserts the rendered freshness/authority text in `runs.html`
- steering interpretation is now explicit: the remaining repo-controlled internal frontier is no longer evidence-lane ambiguity, but release/distribution lifecycle completion, while the latest full-MVP lane truth remains fresh and honestly degraded by live source failures (`SRC-GDELT-DOC`, `SRC-GDELT-DOC-E`)
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/runs/operational_latest.py src/siasa/gui/local_app.py tests/unit/test_operational_latest.py tests/unit/test_local_gui.py` passed
- targeted verification passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests/unit/test_operational_latest.py tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`8 passed in 2.20s`)
- full regression passed: `PYTHONPATH=src /opt/hermes/.venv/bin/pytest tests -q` passed (`481 passed in 1016.01s`)

Fallback reprioritization rule:
- if valid source credentials/registrations become available before the next release-lifecycle slice starts, reassess whether a credential-activation slice should jump ahead

### N1-WP-053
Name:
Close the second G4 bounded slice by adding operator-side lifecycle-transition logic (approve / approve_with_conditions / defer / reject / distribute with audit-trail stamping), a CLI script (`scripts/lifecycle_transition.py`), and Evidence-Lane integration so approval/distribution status is visible in `runs.html` alongside runtime truth.

Closure achieved:
- Extended `src/siasa/readmodels/approval_lifecycle.py` with `transition_lifecycle_record()`, `LifecycleTransitionError`, and `ALLOWED_TRANSITIONS`; state machine governs valid transitions between all six lifecycle states with deterministic audit-trail stamping per transition; exported from `src/siasa/readmodels/__init__.py`
- Added `scripts/lifecycle_transition.py` CLI with actions `approve`, `approve_with_conditions`, `defer`, `reject`, `distribute`, `status`; supports `--reviewer-id`, `--rationale`, `--conditions`, `--recipients`, `--bundle-artifacts`, `--note`, `--actor`, `--dry-run`, `--json`; live-tested full pending -> approved -> distributed chain
- Extended `src/siasa/gui/local_app.py` so `_render_runs()` now accepts `approval_lifecycle_view_model` and renders G4 Approval lifecycle state / overall / send-allowed / next-action directly in the Operational Evidence Lane in `runs.html`; `build_local_mvp_site()` passes the model through
- `tests/unit/test_lifecycle_transition.py` (20 tests): covers all state transitions, invalid action, disallowed transition, audit trail growth, CLI status/approve/full-lifecycle/invalid/dry-run/json
- `tests/unit/test_local_gui.py`: asserts `approval-lifecycle-lane-state`, `approval-lifecycle-lane-overall`, `approval-lifecycle-lane-next-action`, `G4 Approval lifecycle` rendered in `runs.html`
- targeted: 63 passed; full regression: 517 passed

Steering note:
G4 lifecycle record (WP-001) and transitions (WP-002) are now repo-closed. The operator can now run `scripts/lifecycle_transition.py approve --record-path ...` and the result is immediately visible in runs.html. Remaining G4 scope: optional notification/export hooks, wider CLI/workflow integration if needed, or closing G4 as materially complete and moving to the next program track.

### N1-WP-054
Name:
Advance validation realism depth by adding machine-readable visible-slice export for the Replay Attention Watchlist so analysts can hand off the currently filtered attention set as deterministic JSON instead of only prose summary text.

Closure achieved:
- `src/siasa/gui/local_app.py` now renders `replay-attention-export-json` and an inspection payload surface `replay-attention-visible-payload` in `validation.html`, extending the replay-attention controls beyond copy-link + copy-summary
- Added `getReplayAttentionVisibleCards()`, `buildReplayAttentionVisiblePayload(...)`, and `exportReplayAttentionVisiblePayload()` so the current visible card slice is exported in DOM order to `replay_attention_visible_slice.json`
- The payload now exposes deterministic top-level fields `visible_cases`, `case_ids`, `countries`, `attention_level_counts`, `verdict_counts`, and row-level entries containing `case_id`, `country_id`, `attention_level`, `review_verdict`, `replay_tier`, `attention_owner`, and `attention_reason`
- `applyReplayAttentionFilters()` now refreshes the on-page payload preview from the currently visible slice after filtering/sorting, keeping export content causally aligned with what the analyst sees
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed; targeted `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.63s`); focused regression `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py -q` passed (`21 passed in 107.46s`); full regression `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests -q` passed (`529 passed in 331.69s`)

Steering note:
This package confirms the current default internal track is validation realism depth / analyst handoff refinement rather than another repo-controlled G1/G2/G3/G4 closure slice. The next bounded default should stay in this validation-handoff family unless a new external trigger reprioritizes breadth, credentials, or operating model.

### N1-WP-055
Name:
Strengthen replay-attention analyst handoff by making the visible-slice JSON export state-carrying and by adding deterministic CSV export for the same currently visible card slice.

Closure achieved:
- `src/siasa/gui/local_app.py` now enriches `buildReplayAttentionVisiblePayload(...)` with `active_state`, `sort_mode`, `active_preset`, `share_link`, and a structured `filter_state` object so exported handoff payloads carry the exact active review posture, not only the visible rows
- Added `buildReplayAttentionShareUrl(state)` so copy-link, copy-summary, and JSON export reuse one deterministic replay-attention state URL builder
- Added `buildReplayAttentionVisibleCsv(...)` and `exportReplayAttentionVisibleCsv()`; `validation.html` now renders `replay-attention-export-csv`, and the current visible slice downloads as `replay_attention_visible_slice.csv` with MIME type `text/csv;charset=utf-8`
- CSV rows stay aligned with the visible card order and carry deterministic fields `case_id`, `country_id`, `attention_level`, `review_verdict`, `replay_tier`, `attention_owner`, and `attention_reason`
- validation evidence: `PYTHONPATH=src /opt/hermes/.venv/bin/python -m py_compile src/siasa/gui/local_app.py tests/unit/test_local_gui.py` passed; targeted `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py::test_build_local_mvp_site_creates_required_mvp_pages_and_exports -q` passed (`1 passed in 2.41s`); focused regression `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_local_gui.py -q` passed (`21 passed in 105.01s`); full regression `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests -q` passed (`529 passed in 335.90s`)

Steering note:
The replay-attention watchlist now supports both machine-readable JSON and spreadsheet-friendly CSV handoff while preserving the active analyst review context. The next bounded default should move from export surfaces toward stronger validation-to-action closure or deeper challenge-case realism, not another generic export-only slice.

### N1-WP-056
Name:
Re-sync the capability-matrix steering ledger with the master-steering baseline after replay-attention export follow-ons so planning truth does not overclaim analyst-handoff features that the repo has not actually implemented.

Closure achieved:
- `docs/plans/siasa-project-lead-capability-matrix.md` no longer claims unsupported replay-attention follow-ons for filename-metadata export naming, clipboard CSV, visible severity breakdown, enriched handoff CSV columns, or weak-evidence/mismatch advanced presets
- Added a regression guard in `tests/unit/test_readmodels_functional_fulfillment.py` that cross-checks the capability matrix against the current master-steering baseline through `N1-WP-055` / `VAL-WP-012`, preventing those stale replay-attention overclaims from silently reappearing
- steering interpretation is now re-aligned: the evidence ledger truthfully stops at the implemented replay-attention baseline (JSON export, state-carrying payload, CSV export, validation-to-annotation handoff, and existing verdict/tier filters) instead of implying extra export-only closure that the repo does not yet provide
- validation evidence: targeted `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_readmodels_functional_fulfillment.py::test_capability_matrix_steering_view_does_not_overclaim_replay_attention_follow_ons -q` passed; focused regression `PYTHONPATH=src /opt/hermes/.venv/bin/python -m pytest tests/unit/test_readmodels_functional_fulfillment.py -q` passed

Steering note:
This was a planning-governance hygiene tranche, not a new product-surface expansion. With steering truth repaired, the next bounded default should return to the active internal track: validation-to-action refinement or deeper challenge-case realism.

### N1-WP-057
Name:
Deepen challenge-case realism in the active validation track by extending the governed archival replay portfolio with three non-perfect extended-focus cases (`USA`, `DEU`, `EGY`) that preserve the mismatch/domain-gap/weak-evidence archetype balance while broadening challenge coverage beyond the earlier core-focus-heavy set.

Closure achieved:
- Added `VAL-USA-2024-CHALLENGE-001`, `VAL-DEU-2024-CHALLENGE-001`, and `VAL-EGY-2024-CHALLENGE-001` to `vmodel/verification/validation_reference_cases.yaml`, `validation_replay_inputs.yaml`, and `validation_archival_replay_manifest.yaml`, plus governed archival JSON bundles under `vmodel/verification/archival_replay_inputs/`
- Updated `tests/unit/test_archival_replay.py`, `tests/unit/test_historical_replay.py`, and `tests/unit/test_readmodels_validation_backtest.py` with exact live-computed 32-case snapshots/aggregates; targeted validation regression passed (`23 passed`) and full regression passed (`532 passed in 336.42s`)
- The governed validation portfolio now stands at `case_count=32` with balanced challenge types (`challenge_mismatch=3`, `challenge_domain_gap=3`, `challenge_weak_evidence=3`), `historical_alignment_mismatch=7`, `historical_alignment_with_gaps=5`, and `attention_case_count=11`
- Representative live probe evidence was refreshed via `RUN-LIVE-VAL-WP013-001`: `run_status=partial_success`, `failed_sources=[SRC-GDELT-DOC-E]`, `known_gaps=[]`, `release_verdict=ready`; the updated GUI evidence is visible in `build/local_gui/_val_wp013_probe_1/validation.html`
- Commit: `061ca70`

Steering note:
This keeps the program on the intended default internal track: validation realism depth / analyst handoff refinement. The next bounded default should now prefer either (a) stronger validation-to-action closure on top of the richer 32-case portfolio or (b) another challenge-case realism slice only if it adds a new archetype rather than just more of the same.

### N1-WP-058
Name:
Turn the readiness-facing analyst briefing into a context-carrying validation-to-action surface by attaching deterministic deep links for prioritized items and a direct prefilled annotation-draft handoff for validation-attention rows.

Closure achieved:
- Updated `src/siasa/gui/local_app.py` with reusable helpers `_annotation_prefill_href(...)` and `_is_safe_internal_navigation_href(...)`, then extended `_build_analyst_briefing_view_model(...)` so prioritized `country_gap`, `stale_priority`, `validation_attention`, `traceability_risk`, `operability_cluster`, and `stale_remediation_action_plan` rows now emit deterministic `target_href`
- Validation-attention briefing rows now additionally emit `action_label=Create Annotation Draft` plus a context-preserving `action_href` to `annotations.html`, carrying the same replay-attention prefill semantics already used from `validation.html`
- `_render_readiness(...)` now renders safe-gated `analyst-briefing-target-link` and `analyst-briefing-action-link` anchors in both the primary-focus summary and the analyst-briefing table instead of only static page-name text
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for contextual briefing links and readiness rendering; focused GUI regression passed (`23 passed in 108.20s`); full regression `534 passed in 345.76s`
- GUI evidence is visible in `build/local_gui/_val_wp014_briefing_links/readiness.html`
- Commit: `ad7dc96`

Steering note:
This closes the next bounded validation-to-action slice on top of the 32-case portfolio: analysts no longer need to manually reconstruct which Validation/Coverage state or annotation handoff belongs to the primary briefing item. The next bounded default should now prefer either another actionability-tightening slice around analyst execution context or a new challenge-case realism archetype if it adds genuinely new validation stress.

### N1-WP-059
Name:
Carry the new analyst-briefing execution context through the release/demo handoff package so reviewer-facing release guidance preserves exact focused navigation instead of degrading back to static page labels.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so release/demo package view models now preserve `primary_item_target_href`, `primary_item_action_href`, and row-level `target_href` / `action_href`
- Guided review step `C3-02` now follows contextual hrefs when available rather than falling back to plain `target_page`
- `render_release_demo_package_body(...)` now renders safe-gated `analyst-briefing-target-link` anchors in the package summary and prioritized-item table, plus action links when present, instead of only static page-name text
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for `release_demo_package.json` contextual href persistence and `release_package.html` link rendering; targeted regression passed (`2 passed in 2.43s`); focused GUI regression passed (`23 passed in 104.73s`); full regression `534 passed in 339.32s`
- GUI evidence is visible in `build/local_gui/_val_wp015_release_handoff_links_demo/release_package.html`
- Commit: `e5d3d05`

Steering note:
This closes the next analyst-execution-context gap after N1-WP-058: management/reviewer handoff now preserves the exact review navigation target instead of forcing manual reconstruction from static page labels. The next bounded default should prefer either a similarly small actionability-tightening slice around reviewer execution context or, if materially higher value emerges, a genuinely new challenge-case realism archetype.

---

### N1-WP-060
Name:
Harden the fallback-built reviewer/demo walkthrough so guided review steps preserve exact contextual Validation/Coverage navigation even when no prebuilt analyst-briefing view model is available.

Closure achieved:
- Updated fallback item reconstruction in `src/siasa/readmodels/release_demo_package.py` so `country_gap`, `validation_attention`, `traceability_risk`, `operability_cluster`, and `stale_priority` items emit contextual `target_href`s instead of generic page references
- Added `validation_focus_href` synthesis from the active validation view model so guided review step `C3-04` keeps a focused replay-attention/validation landing target even when the historical replay attention watchlist is absent
- Confirmed exported `release_demo_package.json` now carries the focused fallback-path reviewer sequence, including `validation.html#ra=...` for the validation posture step
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for fallback-path `review_sequence` and exported package href persistence; targeted regression passed (`2 passed in 2.43s`); focused GUI regression passed (`23 passed in 100.65s`); full regression `534 passed in 332.78s`
- GUI evidence is visible in `build/local_gui/_val_wp016_reviewer_flow_context/release_demo_package.json`
- Commit: `80c7a58`

Steering note:
This closes the remaining fallback-path reviewer-execution-context gap after N1-WP-059: reviewer/demo walkthroughs now preserve exact navigation focus even when assembled from the leaner fallback evidence path.

---

### N1-WP-061
Name:
Align the stakeholder-facing cover sheet `start_here` field with the already-contextual reviewer handoff so external reviewers begin at the exact primary-focus slice rather than a generic readiness entry point.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so `stakeholder_cover_sheet.start_here` now derives `page_name`, `page_label`, `href`, and `reason` from the current primary item (`target_href`, `target_page`, `recommended_next_check`) rather than hard-wiring gate posture as the first external entry point
- Confirmed the cover-sheet start point now stays aligned with the same contextual focus already preserved in `primary_item_target_href` and guided step `C3-02`
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` proving the exported fallback-path `release_demo_package.json` points `start_here` to the contextual country-gap href; targeted regression passed (`2 passed in 2.64s`); focused GUI regression passed (`23 passed in 106.06s`); full regression `534 passed in 336.64s`
- GUI evidence is visible in `build/local_gui/_val_wp017_cover_sheet_start_here_context/release_package.html`
- Commit: `695fa9c`

Steering note:
This closes the remaining stakeholder-cover-sheet handoff gap after N1-WP-060: the external package summary now starts at the same exact slice the reviewer package already identifies as most important, reducing one more manual navigation step in external review.

---

### N1-WP-062
Name:
Preserve direct next-action handoff inside the release/demo package by carrying validation-derived action links through the guided review sequence and stakeholder cover sheet, not only through the primary-focus summary and prioritized-item table.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so guided review steps `C3-02` and `C3-04` now preserve `action_label` / `action_href` when the active primary or validation-focus item already carries a direct action such as `Create Annotation Draft`
- `stakeholder_cover_sheet.start_here` now carries the same action metadata in addition to contextual navigation metadata, keeping the external handoff aligned with the actionable validation slice
- `render_release_demo_package_body(...)` now renders those direct action links in both the `Guided review sequence` table (`Page / action`) and the cover-sheet `Start here` line instead of leaving actionability only in earlier summary blocks
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for exported `release_demo_package.json` action-link persistence and rendered `release_package.html` action links; targeted regression passed (`1 passed in 1.33s`); focused GUI regression passed (`24 passed in 103.53s`); full regression passed (`535 passed in 335.77s`)
- Commit: `148dd8b`

Steering note:
This keeps the program on the current validation realism / analyst-handoff track and closes the next reviewer-execution-context gap after N1-WP-061: the release package now preserves not only where to inspect next, but also the direct follow-up action when the active validation slice already implies one.

---

### N1-WP-063
Name:
Propagate the active validation-derived follow-up action through the downstream release/export summary surfaces so reviewer handoff, external-share summary, decision-log export, and decision-packet seed stay actionable instead of preserving navigation context only.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so `reviewer_handoff_summary`, `decision_log_seed`, `stakeholder_cover_sheet.external_share_summary`, `decision_log_export_summary`, and `decision_packet_seed` now preserve `primary_follow_up_action_label` / `primary_follow_up_action_href` whenever the active primary item already carries a direct action such as `Create Annotation Draft`
- `render_release_demo_package_body(...)` now renders `Primary follow-up action` directly in the `Reviewer handoff and export summary` and `Decision packet seed` panels, so downstream management/export views no longer lose the actionable follow-up context already visible in guided-review and cover-sheet paths
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for machine-readable action propagation across these summary/export structures and for rendered `release_package.html` action-link visibility; targeted regression passed (`1 passed in 1.60s`); focused GUI regression passed (`24 passed in 108.96s`); full regression passed (`535 passed in 341.10s`)
- Commit: `eaa81a8`

Steering note:
This closes the next release/export actionability gap after N1-WP-062: downstream reviewer and stakeholder packet summaries now preserve not only the contextual slice and navigation target, but also the direct follow-up action for that slice.

---

### N1-WP-064
Name:
Make the propagated validation follow-up action directly visible as clickable links inside the export-oriented release-package summary panels instead of leaving those downstream summaries with raw href text or action metadata visible only in JSON.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so `stakeholder_cover_sheet.external_share_summary`, `decision_log_export_summary.requested_decision_linkage`, and `decision_log_export_summary.decision_entry_template` now render their propagated `primary_follow_up_action_*` fields as safe-gated clickable action links in `release_package.html`
- The generic list renderers for those summary structures now suppress duplicated raw href-string rows for `primary_follow_up_action_href` / `primary_follow_up_action_label`, preventing noisy export panels while preserving machine-readable metadata in the JSON payload
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for propagated href presence plus rendered action-link visibility/multiplicity (`Primary follow-up action`, `Decision-entry follow-up action`, repeated `Create Annotation Draft` links); targeted regression passed (`1 passed in 0.61s`); focused GUI regression passed (`24 passed in 104.71s`); full regression passed (`535 passed in 338.78s`)
- Commit: `e2e760a`

Steering note:
This closes the next downstream export-visibility gap after N1-WP-063: the release package’s export-facing summaries no longer hide the follow-up action in raw metadata, but surface it directly as executable reviewer/stakeholder links.

---

### N1-WP-065
Name:
Make the same propagated validation follow-up action directly visible in the remaining review-governance panels (`Review sign-off scaffold` and `Disposition-aware action routing`) so operator/reviewer execution context stays consistent across all release-package decision surfaces.

Closure achieved:
- Updated `src/siasa/readmodels/release_demo_package.py` so `review_signoff_scaffold` and `disposition_action_routing` now both preserve `primary_follow_up_action_label` / `primary_follow_up_action_href` whenever the active primary item already carries a direct action such as `Create Annotation Draft`
- `render_release_demo_package_body(...)` now renders explicit safe-gated `Primary follow-up action` links in both the `Review sign-off scaffold` and `Disposition-aware action routing` panels instead of leaving those governance views with only prose follow-up bullets
- Added RED/GREEN coverage in `tests/unit/test_local_gui.py` for machine-readable propagation into these structures plus increased rendered action-link visibility/multiplicity (`Primary follow-up action` count, repeated `Create Annotation Draft` links); targeted regression passed (`1 passed in 0.67s`); focused GUI regression passed (`24 passed in 113.61s`); full regression passed (`535 passed in 349.26s`)
- Commit: `47b08dd`

Steering note:
This closes the next remaining release-governance action-visibility gap after N1-WP-064: sign-off and disposition-routing panels now preserve the same executable follow-up action already visible in review, cover-sheet, export, and packet surfaces.

---

## 7. Trigger for the next steering pivot

Stay on the current steering path until one of these becomes true:
- approval/distribution lifecycle closure stops being the dominant remaining internal gap because a bounded G4 slice materially closes it
- valid ReliefWeb/UCDP credentials become available and external source activation becomes the highest-value bounded next slice
- fresh runtime evidence reveals a new truthful-steering defect in the now-closed evidence lane that materially reopens G3
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
- repo-controlled G1, G2, G3, and G4 are now materially closed for the current product baseline
- the next default work is selected from: G4 follow-through (probe-driven), broader runtime breadth, G5 architecture decision (only if operating model demands it), or validation realism depth
- external credential activation can jump ahead only if valid ReliefWeb/UCDP credentials become available
