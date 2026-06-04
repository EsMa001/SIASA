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

### N1-WP-005
Name:
Add fresh-bundle deep links from the operational evidence lane into the exact readiness / coverage / release artifacts so an operator can pivot from summary truth to the governing evidence without manual file hunting.

Why this is the default next package:
- N1-WP-004 closed the truth-model gap by placing runtime governance and readiness/release truth side by side in the normal operator lane
- the next bounded improvement is navigation/actionability: turning that truth into one-click evidence pivot paths rather than another new metric layer
- this remains a small operator-facing closure slice inside G3 instead of reopening broader strategic work

Definition of done:
- operational evidence-lane latest/history surface exposes direct links to governing readiness / coverage / release evidence for the latest bundle
- targeted tests green
- full suite green
- capability matrix updated
- this master steering document updated if frontier changed
- commit + push completed

Fallback reprioritization rule:
- if valid source credentials/registrations become available before N1-WP-005 starts, reassess whether a credential-activation slice should jump ahead

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
