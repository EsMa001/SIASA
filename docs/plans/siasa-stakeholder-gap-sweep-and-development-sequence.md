# SIASA Stakeholder Gap Sweep and Development Sequence

> Updated: 2026-05-30 — full repo-grounded re-assessment
> Previous version: initial sweep from May 2026 sessions
> Method: category-by-category StR baseline vs repo evidence, distinguishing structural/governance from substantive fulfillment

---

## 1. Baseline

- **668 active stakeholder requirements** across **51 categories**
- **50 system requirements** (SyR-001..050)
- **51 software requirements** (SwR-001..051)
- **294 unit tests**, all passing
- **4 real adapters**: World Bank, GDELT Doc, GDELT Events, GDACS
- **3 feature domains implemented**: A (Political/Media), B (Economic), D (Security)
- **0 feature domains for C** (Physical Activity/Social) and **E** (Cyber/InfoOps)
- **GUI**: static HTML generator with SVG line charts, SVG world map (181-line path data), interactive controls, role-based generation
- **No persistent `latest` runtime artifacts** — all probes were temporary
- **No database layer** — all state is file/artifact-based
- **No scheduler/automation** — runs are manual
- **No probabilistic state modeling** beyond threshold-based D0–D5 classification
- **No evidence fusion / cross-domain contrasting** logic
- **No information epidemiology** beyond first-observed coupling candidates

---

## 2. Category-by-Category Assessment

### Status key
- `Done` — materially fulfilled in current product
- `Partial` — meaningful capability exists, stakeholder intent partly fulfilled
- `Weak` — structural preparation, but not real product capability
- `Missing` — not materially implemented
- `Deferred` — intentionally post-MVP

---

### A Grundziel und Scope (StR-001..007) — Partial
**What exists:** Structured country-level assessment for domains A/B/D; multi-domain status; country profiles
**What is missing:** Domains C/E not yet integrated; full 5-domain Lageverständnis not achievable
**Gap:** C/E domain gap prevents holistic country assessment

### B Quellenklassen (StR-008..012) — Partial
**What exists:** 4 real adapters covering government statistics, news/media, event data, disaster alerts
**What is missing:** Social media, academic, OSINT/cyber, HUMINT-proxy source classes not covered
**Gap:** Source diversity significantly below stakeholder expectation

### C Quellenkatalog und Metadaten (StR-013..017) — Done
**What exists:** `catalog/models.py`, `catalog/loaders.py`, source metadata in YAML
**Gap:** None material

### D Country Information & Activity Space Profile (StR-018..023) — Done
**What exists:** Country profile pages, drill-down, explanation, drivers, uncertainty
**Gap:** Richer with C/E inclusion later

### E Baselines und Anomalien (StR-024..028) — Partial
**What exists:** `scoring/baselines.py`, anomaly scoring, baseline comparison in GUI
**What is missing:** Baselines only cover A/B/D domains; no baseline concept for C/E
**Gap:** Incomplete domain coverage

### F Informationsabhängigkeiten und Quellencluster (StR-029..034) — Weak
**What exists:** Coupling candidates, first-observed source classification in traceability
**What is missing:** Real dependency graph, cluster detection, influence quantification
**Gap:** Only groundwork exists

### G Source Lineage (StR-035..039) — Partial
**What exists:** Traceability page, lineage records, source-origin inference
**What is missing:** Full provenance graph, cross-run lineage comparison
**Gap:** Read-only, no interactive exploration

### H Informations-Epidemiologie (StR-040..044) — Weak
**What exists:** First-observed timestamps, coupling candidates
**What is missing:** Spread-path modeling, amplification detection, information flow graphs
**Gap:** Only conceptual groundwork

### I Evidenzfusion und Cross-Domain-Kontrastierung (StR-045..050) — Missing
**What exists:** Multi-domain status derives from individual domain statuses
**What is missing:** Explicit cross-domain contradiction detection, evidence weighting, fusion logic
**Gap:** No implementation beyond simple aggregation

### J Unsicherheit und Explainability (StR-051..056) — Partial
**What exists:** Uncertainty indicators in domain status, data sufficiency reasons, explanation summaries
**What is missing:** Quantified uncertainty propagation, confidence intervals, explainability beyond text
**Gap:** Descriptive but not quantitative

### K Probabilistische Zustandsmodellierung (StR-057..061) — Missing
**What exists:** Threshold-based D0–D5/S0–S6 classification
**What is missing:** Bayesian state models, transition probabilities, probabilistic forecasting
**Gap:** Entirely threshold-based, no probabilistic methods

### L Validierung und Backtesting (StR-062..066) — Partial
**What exists:** Archival replay with 23 curated reference cases across 21 countries
**What is missing:** Time-series-based backtesting, automated retrospective validation
**Gap:** Replay-based validation, not true historical backtesting

### M Projekt- und Nutzungsziel (StR-067..070) — Done
**What exists:** Project documentation, use cases, goals
**Gap:** None material

### N GUI Grundanforderungen (StR-071..080) — Done
**What exists:** HTML GUI with navigation, controls, role-based views, accessibility
**Gap:** Static generator, not interactive SPA

### N GUI Nutzungsmodi (StR-081..088) — Partial
**What exists:** Role-based modes (viewer/analyst/admin), filter controls
**What is missing:** Live interactive mode switching, collaborative features
**Gap:** Static generation per role, not dynamic switching

### N GUI Seitenstruktur (StR-089..100) — Done
**What exists:** All major page types implemented
**Gap:** None material

### N GUI Weltkarte und Score-Modi (StR-101..110) — Partial
**What exists:** SVG world map with region-anchored markers, color-coded status
**What is missing:** Real geographic projection, zoom/pan, overlay switching between score modes
**Gap:** Schematic map, not interactive cartographic visualization

### O Kartenbaseline und Vergleichsskala (StR-111..117) — Partial
**What exists:** Historical comparison summaries, baseline context in domain views
**What is missing:** Visual diff overlays, animated temporal comparison
**Gap:** Text-based comparison, not visual

### O Multi-Window-Baselines (StR-118..128) — Weak
**What exists:** Single-window baseline comparison
**What is missing:** Multi-window parallel views, temporal slider
**Gap:** No multi-window capability

### O Aktualitätsfenster (StR-129..134) — Partial
**What exists:** Freshness overlays, staleness thresholds, data sufficiency checks
**What is missing:** Configurable freshness windows per domain/source
**Gap:** Hardcoded thresholds

### P Datenbank und tägliche Runs (StR-135..147) — Weak
**What exists:** Orchestrator, artifact generation, run state tracking
**What is missing:** No database, no scheduler, no automated daily runs
**Gap:** File-based only, fully manual execution

### P Historischer Datenhorizont und Data Sufficiency (StR-148..161) — Partial
**What exists:** Data sufficiency scoring, coverage/freshness checks, threshold logic
**What is missing:** Historical data storage, time-series accumulation, configurable horizons
**Gap:** No persistent historical data layer

### Q MVP-Länderauswahl / Länderpriorisierung / MVP-Länderset (StR-162..204) — Done
**What exists:** Governed pilot sets from 4 to 30 countries, priority model, mvp_countries.yaml
**Gap:** Runtime breadth can still expand

### R MVP-Domänenumfang (StR-188..196) — Partial
**What exists:** A/B/D fully implemented
**What is missing:** C/E feature extraction not implemented
**Gap:** 2 of 5 domains missing

### S Datenquellenverwaltung und ACLED / Festgelegte Datenquellen (StR-205..225) — Weak
**What exists:** Source catalog, 4 adapter implementations
**What is missing:** ACLED adapter (access restricted), many specified sources not integrated
**Gap:** Large source coverage gap

### T Funktionsrahmen ohne General Fusion Score (StR-226..235) — Done
**What exists:** Per-domain status, multi-domain status without naive fusion, explicit anti-fusion guardrails
**Gap:** None material (anti-fusion is intentional)

### U Multi-Domain-Status (StR-236..244) — Done
**What exists:** Multi-domain derivation S0–S6, domain inclusion tracking
**Gap:** More meaningful with C/E

### U Einbindung C/E in Multi-Domain-Status (StR-245..254) — Weak
**What exists:** Gating logic in `multi_domain_status.py` (line 23: C/E filtered unless gate=True)
**What is missing:** No `domain_c.py`, no `domain_e.py`, so gates can never activate
**Gap:** Infrastructure exists but is inert without feature extraction

### V Domänenstatus D0-D5 (StR-255..265) — Done
**What exists:** Full D0–D5 classification, sufficiency gating, contradiction detection
**Gap:** Only for A/B/D

### W Regelbasierte Bewertung und Annotationen (StR-266..290) — Done
**What exists:** Annotation models, create/edit/filter/export workflow, contextual rendering
**Gap:** No server-side persistence/review

### X Report und Export / Automatische und manuelle Reports (StR-291..310) — Partial
**What exists:** Report/export views, exported files, report scoping controls
**What is missing:** Automated report generation, scheduled distribution
**Gap:** Manual only

### Y Analyse-Funktionsrahmen A-E (StR-311..327) — Partial
**What exists:** Feature services for A/B/D, feature catalog concept
**What is missing:** Feature services for C/E
**Gap:** 2 of 5 domains

### Z MVP Feature Set (StR-328..340) — Partial
**What exists:** Core features for A/B/D
**What is missing:** C/E features
**Gap:** Incomplete domain coverage

### AA Nutzerrollen und Berechtigungen (StR-341..350) — Partial
**What exists:** Role-based GUI generation (viewer/analyst/admin)
**What is missing:** Server-side auth, permission persistence
**Gap:** Client-side only

### Use Cases (StR-351..357) — Done
**What exists:** Use case documentation, aligned implementation
**Gap:** None material

### Validierung & Backtesting (StR-358..381) — Partial
**What exists:** 23-case archival replay, attention watchlist, portfolio summary
**What is missing:** Automated regression backtesting, live retrospective validation
**Gap:** Curated-only, not automated

### Qualitätsanforderungen (StR-382..416) — Done
**What exists:** Test suite, CI gates, traceability, quality plan
**Gap:** None material

### Daten-Governance / Lizenz / personenbezogene Analyse (StR-417..451) — Partial
**What exists:** Export policy, governance module, license awareness in catalog
**What is missing:** Automated compliance checks, GDPR workflow
**Gap:** Policy documented but not enforced programmatically

### Ethik & Missbrauchsbegrenzung (StR-452..473) — Weak
**What exists:** Ethics principles documented, anti-naive-score guardrails
**What is missing:** Runtime ethics enforcement, bias detection, audit logging
**Gap:** Documentation only

### Betrieb & Automatisierung (StR-474..520) — Missing
**What exists:** Manual run capability
**What is missing:** Scheduler, monitoring, alerting, health checks, automated recovery, deployment
**Gap:** No operational automation at all (47 requirements)

### Traceability & Versionierung (StR-521..561) — Done
**What exists:** Full V-model traceability, trace links, validation scripts, CI gates
**Gap:** None material

### Definition of Done / MVP-Abnahme (StR-562..605) — Partial
**What exists:** Quality gates, release evidence, failure drills
**What is missing:** Some acceptance criteria depend on C/E and automation capabilities
**Gap:** Blocked by upstream gaps

### MVP-Priorisierung & Akzeptanzkriterien (StR-606..622) — Done
**What exists:** Priority model, acceptance criteria refs
**Gap:** None material

### Systemgrenzen / externe Systeme (StR-623..646) — Done
**What exists:** System boundary documentation, adapter abstraction
**Gap:** None material

### Risiken & Annahmen (StR-647..660) — Done
**What exists:** Risk/assumption documentation
**Gap:** None material

### Glossar / Begriffsdefinitionen (StR-661..668) — Done
**What exists:** Glossary
**Gap:** None material

---

## 3. Cross-Cutting Gap Groups

### Gap Group 1: Domain C/E Feature Gap (~50 StR affected)
**Categories:** R, U (C/E), Y, Z, plus indirect impact on A, E, V
**Root cause:** `domain_c.py` and `domain_e.py` do not exist
**Impact:** Multi-domain status runs on 3/5 domains; C/E gating in multi_domain_status.py is inert
**Severity:** HIGH — blocks holistic country assessment

### Gap Group 2: Operations & Automation Gap (47 StR)
**Categories:** Betrieb & Automatisierung
**Root cause:** No scheduler, no database, no monitoring
**Impact:** System cannot operate unattended; no daily run cycle
**Severity:** HIGH — blocks operational deployment

### Gap Group 3: Source Coverage Gap (~21 StR)
**Categories:** B, S (ACLED + Festgelegte Quellen)
**Root cause:** Only 4 of many specified sources integrated
**Impact:** Feature extraction quality limited by source diversity
**Severity:** MEDIUM — existing sources sufficient for A/B/D MVP

### Gap Group 4: Advanced Analytics Gap (~22 StR)
**Categories:** I (Evidenzfusion), K (Probabilistik), H (Epidemiologie)
**Root cause:** No implementation beyond simple aggregation/thresholds
**Impact:** No cross-domain contrasting, no probabilistic forecasting, no information flow modeling
**Severity:** MEDIUM — post-MVP enrichment, not blocking core use

### Gap Group 5: Persistent Data & Historical Depth Gap (~27 StR)
**Categories:** P (Datenbank + Historischer Horizont), O (Multi-Window)
**Root cause:** No database, no time-series accumulation
**Impact:** No historical trend analysis, no multi-window comparison
**Severity:** MEDIUM — limits analyst depth but not basic function

### Gap Group 6: GUI Interactivity Gap (~20 StR)
**Categories:** N (Weltkarte/Score-Modi), O (Multi-Window)
**Root cause:** Static HTML generation, no interactive map/chart framework
**Impact:** Analyst experience below expectation for exploration tasks
**Severity:** LOW-MEDIUM — existing SVG charts/map are functional baseline

---

## 4. Serial Development Sequence

Foundation → Content → Experience → Advanced

### Phase 1: Content Completeness (close the domain gap)
1. **AP-N01** — Domain C feature extraction
2. **AP-N02** — Domain E feature extraction
3. **AP-N03** — C/E integration into multi-domain status + GUI transparency

### Phase 2: Runtime & Data Foundation
4. **AP-N04** — Persistent `latest` run cycle (reproducible on Windows/PyCharm)
5. **AP-N05** — Lightweight data persistence layer (SQLite or structured file store)
6. **AP-N06** — Automated daily run scheduler

### Phase 3: Source Breadth
7. **AP-N07** — ACLED adapter (if access obtainable) or alternative security source
8. **AP-N08** — Additional Domain C/E sources

### Phase 4: Analyst Experience
9. **AP-N09** — Interactive world map (Leaflet/D3 or enhanced SVG)
10. **AP-N10** — Enhanced trend visualization (time-series charts with zoom)
11. **AP-N11** — Multi-window baseline comparison

### Phase 5: Advanced Analytics (post-MVP)
12. **AP-N12** — Cross-domain evidence fusion / contrasting
13. **AP-N13** — Probabilistic state modeling
14. **AP-N14** — Information epidemiology depth

---

## 5. Work Package Definitions

### AP-N01: Domain C Feature Extraction
**Scope:** Implement `src/siasa/features/domain_c.py` following the `FeatureService` pattern from domain_a/b/d. Domain C = physical activity / social indicators. Use GDACS data (already available) as primary input. Extract features: event_count, event_severity_mean, affected_population, geographic_spread.
**Prerequisites:** None — adapters and feature base exist
**Deliverables:** `domain_c.py`, `test_features_domain_c.py`, SwR derivation, traceability update
**Complexity:** M
**StR coverage:** StR-188..196 (partial), StR-245..254 (partial), StR-311..327 (partial)

### AP-N02: Domain E Feature Extraction
**Scope:** Implement `src/siasa/features/domain_e.py`. Domain E = cyber/tech/info-ops. Use GDELT Doc (already available) as primary input, filtering for cyber/tech themes. Extract features: cyber_mention_volume, info_ops_tone, tech_disruption_signals, source_diversity_cyber.
**Prerequisites:** None
**Deliverables:** `domain_e.py`, `test_features_domain_e.py`, SwR derivation, traceability update
**Complexity:** M
**StR coverage:** StR-188..196 (partial), StR-245..254 (partial), StR-311..327 (partial)

### AP-N03: C/E Multi-Domain Integration
**Scope:** Wire domain_c and domain_e into the orchestrator pipeline. Implement data-sufficiency gating for C/E (StR-250). Update GUI to show active/inactive domain indicators (StR-251/252). Implement "nicht bewertbar" vs "unauffällig" distinction (StR-253).
**Prerequisites:** AP-N01, AP-N02
**Deliverables:** Updated orchestrator, multi_domain_status integration, GUI domain indicators, tests
**Complexity:** M
**StR coverage:** StR-245..254 (full closure)

### AP-N04: Persistent Latest Run Cycle
**Scope:** Ensure `build/run_artifacts/latest/` is populated by a standard run command and persists across sessions. Document the exact PyCharm/Windows command. Verify all readmodels are written.
**Prerequisites:** AP-N03 (to include C/E in the run)
**Deliverables:** Updated run command, README section, verification script, populated latest/
**Complexity:** S
**StR coverage:** StR-135..147 (partial)

### AP-N05: Lightweight Data Persistence
**Scope:** Add SQLite-based run history storage. Store run metadata, per-country domain scores, and source fetch results. Enable time-series queries for trend analysis.
**Prerequisites:** AP-N04
**Deliverables:** `src/siasa/data/storage.py`, migration script, query API, tests
**Complexity:** L
**StR coverage:** StR-135..161 (partial)

### AP-N06: Automated Daily Run Scheduler
**Scope:** Add a scheduler that triggers daily runs, writes latest/, detects failures, sends basic alerts.
**Prerequisites:** AP-N05
**Deliverables:** Scheduler module, configuration, health check, alert mechanism
**Complexity:** L
**StR coverage:** StR-474..520 (partial)

### AP-N07: Additional Security Source Adapter
**Scope:** Implement ACLED adapter (if API access obtainable) or alternative conflict/security data source for Domain D enrichment and Domain C support.
**Prerequisites:** None (can run parallel after AP-N03)
**Deliverables:** New adapter, tests, source catalog update
**Complexity:** M
**StR coverage:** StR-205..225 (partial)

### AP-N08: Additional Domain C/E Sources
**Scope:** Add at least one additional source per domain (C: humanitarian/social, E: cyber threat feeds) to improve coverage.
**Prerequisites:** AP-N01, AP-N02
**Deliverables:** New adapters, tests, coverage improvement evidence
**Complexity:** L
**StR coverage:** StR-008..012, StR-205..225

### AP-N09: Interactive World Map
**Scope:** Replace or enhance current SVG map with interactive capabilities: click-to-drill-down, hover tooltips, zoom regions, score-mode overlay switching.
**Prerequisites:** AP-N04 (needs populated data)
**Deliverables:** Enhanced map component, integration tests, browser verification
**Complexity:** L
**StR coverage:** StR-101..110

### AP-N10: Enhanced Trend Visualization
**Scope:** Upgrade existing SVG line charts with zoom, pan, multi-series overlay, and temporal range selection.
**Prerequisites:** AP-N05 (needs historical data)
**Deliverables:** Enhanced chart component, integration tests
**Complexity:** M
**StR coverage:** StR-118..128 (partial)

### AP-N11: Multi-Window Baseline Comparison
**Scope:** Implement parallel-view comparison of different time windows for the same country/domain.
**Prerequisites:** AP-N05, AP-N10
**Deliverables:** Comparison view, tests
**Complexity:** M
**StR coverage:** StR-118..128

### AP-N12: Cross-Domain Evidence Fusion
**Scope:** Implement explicit cross-domain contrasting (e.g., economic stability vs security instability) with contradiction detection and evidence weighting.
**Prerequisites:** AP-N03 (all 5 domains)
**Deliverables:** Fusion module, tests, GUI integration
**Complexity:** L
**StR coverage:** StR-045..050

### AP-N13: Probabilistic State Modeling
**Scope:** Replace threshold-based D0–D5 with probabilistic state estimation (e.g., Bayesian classification or HMM-based transitions).
**Prerequisites:** AP-N05 (needs historical data for training)
**Deliverables:** Probabilistic scoring module, comparison with threshold baseline, tests
**Complexity:** L
**StR coverage:** StR-057..061

### AP-N14: Information Epidemiology Depth
**Scope:** Implement spread-path modeling, amplification detection, source influence quantification.
**Prerequisites:** AP-N05, AP-N08
**Deliverables:** Epidemiology module, visualization, tests
**Complexity:** L
**StR coverage:** StR-040..044

---

## 6. Immediate Next Recommendation

**Start with AP-N01 (Domain C Feature Extraction)**

Rationale:
1. Closes the single largest content gap (2/5 domains missing)
2. High feasibility — adapter data (GDACS) already available, feature pattern well-established
3. Unblocks AP-N02, AP-N03, and eventually all 5-domain capability
4. Directly addresses ~50 stakeholder requirements that depend on C/E
5. No external dependencies (no new API access needed)

---

## 7. Definition of Stakeholder-Fulfilled State

SIASA is stakeholder-fulfilled when:
1. All 5 domains (A–E) produce governed feature outputs
2. Multi-domain status reflects actual 5-domain assessment
3. At least the MVP country set produces daily, reproducible runs
4. Runtime artifacts persist and accumulate historical depth
5. The GUI provides interactive country/domain/trend exploration
6. Validation covers all domains with curated and automated cases
7. Operations run unattended with monitoring and alerting
8. Source coverage includes the specified core source classes
