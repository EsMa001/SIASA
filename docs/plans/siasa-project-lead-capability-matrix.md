# SIASA Project-Lead Capability Matrix

> For Hermes: maintain this document after every completed serial work package. Update capability status only when there is repo evidence, verification evidence, and a committed package that materially changes stakeholder-visible functionality.

Goal: give the project lead a fast, evidence-backed view of (1) what is implemented, (2) what is only partly implemented or merely prepared, and (3) what is still materially open.

Architecture: this matrix sits above code-level details. It maps stakeholder-facing capabilities to concrete repo evidence, test evidence, and work packages so progress can be tracked as capability maturity instead of raw file churn.

Tech stack / evidence base: `docs/plans/siasa-stakeholder-fulfillment-roadmap.md`, `docs/plans/siasa-stakeholder-gap-sweep-and-development-sequence.md`, `src/siasa/**`, `tests/**`, and current governed artifacts under `build/run_artifacts/latest`.

---

## 1. How to use this matrix

### Status semantics
- `Done` = materially usable in the current product/repo baseline; verified and committed
- `Partial` = meaningful capability exists, but stakeholder intent is only partly fulfilled
- `Weak` = structural preparation exists, but practical product capability is still thin
- `Missing` = materially not implemented yet
- `Deferred by intent` = intentionally later/post-MVP unless reprioritized

### Evidence rule
A capability must not be marked `Done` based only on code structure.
It should only be marked `Done` when all three exist:
1. product/runtime evidence
2. verification evidence
3. committed package evidence

### Work-package status rule
For project steering, use these work-package states:
- `Open` = not started
- `In Progress` = active serial package right now
- `Verified` = implemented and verified locally, but not yet committed/pushed
- `Done` = verified, committed, and pushed

---

## 2. Current project-lead capability matrix

| Capability | Stakeholder focus | Current status | What exists now | What is still missing | Product / runtime evidence | Verification evidence | Last completed work package | Next planned work package |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| World overview and anomaly navigation | Fast global anomaly orientation with drill-down | Partial | Interactive overview page, country drill-down links, map-facing visualization layer, overview controls | Still limited by current runtime breadth and latest-bundle population | `build/local_gui/index.html`, `build/run_artifacts/latest/readmodels/world_map.json`, `src/siasa/gui/local_app.py` | GUI generation tests in `tests/unit/test_local_gui.py` | Earlier P3 GUI hardening packages | P2 breadth/runtime continuation as needed |
| Country drill-down and explanation | Understand why a country is in its current state | Done | Country profile page, explanation summary, drivers, uncertainty, gap context, links to domain pages and annotations | Richer historical comparison on country reasoning can still improve later | `countries/*.html` generation in `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py` | Earlier country-profile GUI package | P4-WP-002 for richer comparison overlays |
| Domain deep dive and trend interpretation | Inspect domain-specific time series and drivers | Partial | Domain detail pages, trend views, feature values, source context, anomaly state, and analyst-friendly baseline/historical summaries now exist | Broader source/runtime breadth still limits how representative these views are across the full stakeholder scope | `domains/*.html`, `trends.html`, `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py`, browser verification | `P4-WP-002` current package | `P4-WP-003` |
| Cross-country comparison | Compare multiple countries in one analyst flow | Done | Dedicated comparison page with coverage/confidence comparison and controls | Runtime breadth still limits practical representativeness | `comparison.html`, `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py` | Earlier P3 comparison package | Later breadth/runtime packages |
| Source trust / coverage / gap transparency | Review source status, failures, confidence, freshness, and remediation guidance | Done | Coverage view, degraded sources, remediation watchlist, freshness overlays, source-depth summaries | Broader live-source evidence can still deepen practical value | `coverage.html`, `readmodels/system_status.json`, `src/siasa/runs/artifacts.py` | `tests/unit/test_run_artifacts.py`, `tests/unit/test_local_gui.py` | `8c3537d feat: add freshness overlays to coverage views` | Later live-source/runtime hardening |
| Validation / backtest review | Compare expected vs observed outcomes with governed evidence | Partial | Validation page exists, latest governed bundle currently carries `validation_backtest`, and readiness now exposes explicit artifact presence/absence status | Runtime honesty is improved, but release readiness is still blocked by real source failures and the validation view remains a runtime-support check rather than a historical reference-case library | `validation.html`, `readiness.html`, `build/local_gui/readiness.json`, `readmodels/system_status.json`, `readmodels/validation_backtest.json` | Validation-related tests in repo; full suite passing; browser verification | `P1` current closure slice | Broader live-source/runtime hardening |
| Traceability / lineage visibility | Follow evidence path from source to status/report | Done | Dedicated traceability page, lineage records in artifacts, and richer source-groundwork summaries now exist | Full source-origin inference and spread-path modeling are still future work | `traceability.html`, lineage readmodels, `src/siasa/readmodels/traceability*.py`, `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py` and related unit tests | `P4-WP-003` current package | P1/P2 runtime honesty or breadth package |
| Source dependency / source-origin groundwork | Surface coupling candidates and explicitly show what is still missing for origin inference | Partial | Traceability view now exposes dependency cluster candidates and an artifact-backed source-origin groundwork table | No earliest-known-source inference, propagation path modeling, or information epidemiology yet | `traceability.html`, `traceability_lineage.json`, `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py`, browser verification, full suite pass | `P4-WP-003` current package | Later source-origin / epidemiology extension |
| Reports / exports | Generate and inspect governed output artifacts | Partial | Export/report view exists, exported files are linked and copied, evidence summary visible | More interactive report generation and richer scoping UX still open | `reports.html`, export files under generated GUI output | `tests/unit/test_local_gui.py` | Earlier report/export baseline package | Later analyst workflow package |
| Analyst annotation visibility | See annotation context in country/domain/global views | Done | Annotation page, contextual rendering on country/domain pages, linked annotation details | Future review/admin workflows may still extend this | `annotations.html`, country/domain annotation sections | `tests/unit/test_local_gui.py` | Earlier annotation visibility package | None immediately required |
| Analyst annotation create/edit workflow | Operationally create/edit/filter/history/export annotations in GUI | Done | Browser-local create/edit/filter/history workflow, contextual quick links from country/domain pages, JSON export, prefilled workflow entry | Future governed server-side persistence/review flow may still come later | `annotations.html`, quick links from `countries/*.html` and `domains/*.html`, `src/siasa/gui/local_app.py` | `tests/unit/test_local_gui.py`, browser verification, full suite pass | `884659b [verified] feat: add local annotation workflow` | Optional later review/admin workflow |
| Historical / baseline comparison overlays | Explain status/trend deltas against baseline and history in an analyst-friendly way | Done | Trend rows now include historical comparison summaries and domain detail pages now include structured comparison-vs-baseline plus historical-window context | Broader country-level explanation overlays can still be extended later, but the targeted trend/domain gap is closed for the current GUI baseline | Trend/domain GUI pages in `src/siasa/gui/local_app.py`, generated `trends.html` and `domains/*.html` | `tests/unit/test_local_gui.py`, browser verification, full suite pass | `P4-WP-002` current package | `P4-WP-003` |
| Real source access | Productive use of real external sources | Partial | Source-access assessment and governed live runtime pilot exist; real adapter baselines exist for selected sources | Full production-grade breadth and stable access across intended source classes remains incomplete | Current roadmap status in `docs/plans/siasa-stakeholder-fulfillment-roadmap.md`, live runtime code under `src/siasa/runs/live_runtime.py` | Repo tests plus earlier runtime validation work | P0 readiness and pilot packages already advanced | Broader live-source/runtime hardening |
| Representative multi-country runtime breadth | More than one governed country materially supported in latest outputs | Partial | Multi-country runtime/artifact path works; current repo evidence now includes a successful representative 4-country probe path and annual-macro freshness no longer collapses Domain D into false insufficiency | Still not stable enough to treat representative breadth as routinely reproducible in latest outputs because external GDELT DOC throttling can still force partial-success runs | Runtime code under `src/siasa/runs/live_runtime.py`, probe artifacts under `build/run_artifacts/_probe_next` / `_probe_dfresh`, and readmodels such as `world_map.json` | Full suite pass, runtime-related tests, controlled live probe evidence | Recent P2 runtime hardening packages | Further live-source/runtime hardening |
| Role-based UI behavior | Functions change by user role / permission model | Weak | Requirement/governance hooks exist conceptually | No materially exposed role-based behavior in current GUI | Requirements/roadmap evidence, limited/no GUI behavior | No strong product-level role-behavior verification | None materially closed yet | Later role-behavior package |
| Rich analyst cockpit beyond static-view baseline | Dashboard-like exploratory product experience | Partial | Current GUI is materially richer than before: controls, comparisons, overlays, annotation workflow, readiness, traceability | Still generated as a static HTML artifact viewer rather than a fully stateful application | `src/siasa/gui/local_app.py`, generated `build/local_gui/*.html` | GUI tests and browser verifications | Multiple P3/P4 packages | Depends on later strategic direction |

---

## 3. Current work-package steering view

| Work package | Purpose | Current state | Evidence of closure / current truth | Capability impact |
| --- | --- | --- | --- | --- |
| P2 live-runtime hardening: annual macro freshness horizon | Stop annual World Bank macro inputs from being treated as false freshness failures under daily-style sufficiency thresholds | Done | World Bank records now carry an explicit annual freshness horizon, feature confidence preserves it, sufficiency evaluation respects it, targeted tests pass, and controlled live probes show Domain D can now remain D1 instead of collapsing to D0 | Removes one misleading insufficiency source and makes representative live probes materially more truthful |
| P2 live-runtime hardening: GDELT DOC query budget and pacing | Reduce representative multi-country runtime fragility from GDELT DOC rate limiting | Done | Live runtime now configures conservative per-country GDELT DOC record budgets and inter-request pacing, with targeted adapter/runtime tests and full-suite pass | Narrows one concrete live-source instability cause without overclaiming full runtime closure |
| P0 real-source-access readiness | Determine which real sources can be integrated honestly and under what constraints | Done (materially advanced) | Source-access assessment exists; live runtime pilot exists in repo/roadmap | Raised `Real source access` from Weak toward Partial |
| P1 artifact-complete MVP | Ensure latest bundle contains the governed evidence artifacts needed for honest readiness claims | Partial | Artifact presence/absence is now explicit and current governed bundles can carry `validation_backtest`; remaining gap is operational stability of the latest live bundle rather than silent artifact omission | Keeps `Validation / backtest review` honest while shifting the remaining focus toward runtime robustness |
| P2 data-complete country coverage MVP | Move from narrow proof to representative multi-country runtime coverage | Partial | Current repo evidence now includes representative 4-country probe success, but reproducibility is still sensitive to external live-source throttling | `Representative multi-country runtime breadth` remains Partial until repeated latest-bundle runs are stable |
| P3 visual analyst GUI MVP | Build practical GUI usability, controls, comparisons, and visual navigation | Strongly advanced | Roadmap status snapshot records trends, map visualization, controls, comparison, uncertainty/coverage views | Raised multiple analyst-facing capabilities to Done/Partial |
| P4-WP-001 source-gap transparency overlays | Make coverage/freshness/gap remediation visible in overview/map/coverage flows | Done | Commit `8c3537d` and passing tests | Closed major transparency gap |
| P3-WP-005 annotation create/edit workflow | Make annotations operationally editable in the static local GUI | Done | Commit `884659b`, passing tests, browser verification | Closed major analyst workflow gap |
| P4-WP-002 richer baseline/historical overlays | Improve interpretation quality in trend/domain views | Done | Commit `8160ef2`, passing tests, full-suite pass, and browser verification confirm analyst-friendly baseline/historical summaries on trend and domain views | Closed the targeted interpretation gap for the current static GUI baseline |
| P4-WP-003 source-dependency / source-origin groundwork | Improve analyst visibility into coupled sources and make origin-inference gaps explicit | Done | Current work tree adds dependency cluster candidates and source-origin groundwork tables to traceability view, with passing tests, full-suite pass, and browser verification | Closed the intended groundwork slice without overclaiming full origin inference |

---

## 4. Project-lead reading guide

If you want to know:

### What is implemented?
Look for capability status `Done` and confirm that the evidence columns point to:
- generated GUI/runtime outputs
- tests
- a completed work package / commit

### What is only partly begun?
Look for `Partial` or `Weak`:
- `Partial` = meaningful capability exists, but a stakeholder would still hit a practical limit
- `Weak` = mostly structure/preparation, not robust practical use

### What is still completely open?
Look for `Missing`.
In the current matrix, very few top-level areas are truly blank; most remaining gaps are now `Partial` rather than `Missing`.
That is a useful sign of progress, but it also means prioritization must focus on the highest-value remaining deltas, not on creating more thin surface area.

---

## 5. Immediate steering recommendation

Current serial recommendation becomes:
- next work package: GDELT DOC live-runtime resilience and latest-bundle stabilization

Why this is next:
- the annual-macro freshness issue is now corrected, so Domain D no longer creates false D0/S6 outcomes in representative live probes
- controlled representative probe evidence now shows 4-country breadth is technically reachable, but external `SRC-GDELT-DOC` throttling still causes intermittent partial-success runs
- this means the biggest remaining delta is no longer macro-data honesty, but reproducible end-to-end latest-bundle stability under live conditions

After that, reassess whether the largest remaining project-lead gap is:
- runtime/artifact completeness (`P1` closure), or
- representative country breadth (`P2` continuation)

That reassessment should be based on the matrix above, not on raw code churn.
