# SIASA Stakeholder Gap Sweep and Development Sequence

> For Hermes: planning/documentation only. No implementation in this work package. Use this document as the governing gap-analysis and execution-order baseline for the next serial work packages.

Goal: sweep the stakeholder requirement baseline end-to-end, identify what is substantively present, what is only structurally represented, what is still missing, and derive the step-by-step development sequence that should be executed next.

Architecture: this assessment distinguishes between (1) requirement/governance structure, (2) analytical core and governed artifacts, (3) actual runtime/data completeness, and (4) product-level GUI fulfillment. SIASA is already relatively strong in layers (1) and parts of (2), but still weak in real source access, multi-country artifact population, and rich analyst-facing GUI behavior.

Tech stack / evidence base: `vmodel/requirements/stakeholder_requirements.yaml`, `src/siasa/**`, `tests/**`, `docs/ui/gui_pages.md`, `docs/project/use_cases.md`, `docs/verification/level-1-to-4-acceptance-review.md`, current artifact bundle under `build/run_artifacts/latest`.

---

## 1. Assessment method

This is a complete sweep over the stakeholder list by requirement cluster/category, which together covers the full imported stakeholder baseline (`668` requirements across `51` categories).

Assessment states used here:
- Done: materially fulfilled in the current repo/product baseline
- Partial: key structure exists, but stakeholder intent is only partly fulfilled
- Weak: only thin structural preparation exists
- Missing: stakeholder intent is not materially fulfilled yet
- Deferred by intent: explicitly future-facing / optional / post-MVP, therefore not a current delivery gap unless promoted

Important interpretation:
- “Traceability closed” is not the same as “stakeholder expectation fulfilled”.
- “GUI page exists” is not the same as “product experience fulfilled”.
- “Prepared adapter” is not the same as “real source integration”.

---

## 2. Current repo evidence relevant to the sweep

Strong evidence already present:
- governed requirement, architecture, verification, traceability and glossary artifacts under `vmodel/`
- analytical core modules for baselines, domain status, multi-domain status, snapshots, lineage, reports, validation readmodels, annotations, reprocessing, export governance
- static local GUI generator in `src/siasa/gui/local_app.py`
- readmodels for world map, country profile, domain detail, source coverage, system status, validation, annotations
- tests around core logic and GUI generation
- acceptance review for Level 1–4 in `docs/verification/level-1-to-4-acceptance-review.md`

Key hard gaps confirmed from repo inspection:
- no concrete live source adapter implementations in `src/siasa/adapters/` beyond the abstract base/fetch metadata layer
- current `build/run_artifacts/latest/readmodels/world_map.json` contains only one country (`UKR`)
- current artifact-backed readiness still reports missing validation artifact in the latest bundle
- GUI is still a static HTML readmodel viewer, not a rich interactive analyst cockpit

---

## 3. Full stakeholder sweep by category

## A Grundziel und Scope (`StR-001`–`StR-007`) — Status: Partial

What exists:
- country-centric analytical framing is present in architecture and code
- multi-domain reasoning exists
- open-source orientation is present in source catalog and architecture

What is missing:
- use of genuinely heterogeneous live open-source inputs is not yet operationally proven
- current product experience still looks like a repo-driven MVP baseline rather than a broadly usable country-observation system

Gap to document:
- the scope is conceptually modeled correctly, but the runtime/data reality is still far below the intended breadth

Recommended next development:
- first close real-source-access readiness
- then drive multi-country artifact generation from real data

## B Quellenklassen (`StR-008`–`StR-012`) — Status: Weak

What exists:
- all five source classes A–E are modeled in `vmodel/project/data_sources.yaml`
- architecture and source-adapter abstraction allow future integration

What is missing:
- no concrete live adapters for the named external sources
- classes C and E are mostly planned/prepared, not materially integrated
- current operational evidence is largely synthetic/demo-oriented

Gap to document:
- source-class breadth is specified, but not productively connected

Recommended next development:
- source-by-source access matrix
- first live adapters for A/B/D core sources

## C Quellenkatalog und Metadaten (`StR-013`–`StR-017`) — Status: Partial

What exists:
- structured source catalog exists and is loadable
- governance metadata fields exist
- source coverage readmodel exists

What is missing:
- per-country dynamic assessment of source relevance/belastability is still shallow
- current source rows in latest artifacts are generic placeholders rather than governed real-source records

Gap to document:
- catalog exists as governance/config artifact, but operational source intelligence is still thin

Recommended next development:
- enrich source records with stable real source IDs, access class, quality, geography, and country relevance rules

## D Country Information & Activity Space Profile (`StR-018`–`StR-023`) — Status: Partial

What exists:
- country profile readmodel and GUI page
- multi-domain status, domain states, explanations, uncertainty, annotations, linked events/context

What is missing:
- broad country population in real artifacts
- real country comparison capability remains absent
- under-observed-country signaling is not yet a strong product feature

Gap to document:
- country profile exists for the limited available countries, but the portfolio-level country-observation promise is not yet fulfilled

Recommended next development:
- representative multi-country artifacts
- cross-country comparison work package

## E Baselines und Anomalien (`StR-024`–`StR-028`) — Status: Partial

What exists:
- baseline and scoring modules exist
- relative anomaly interpretation exists conceptually and in readmodels
- uncertainty/context are surfaced in several pages

What is missing:
- baseline behavior is not yet transparently explorable from the GUI
- anomaly classes are not yet visually communicated through charts/map overlays

Gap to document:
- anomaly logic exists structurally, but the stakeholder-visible anomaly experience is still underdeveloped

Recommended next development:
- expose baseline/anomaly evidence more clearly in GUI controls and visualizations

## F Informationsabhängigkeiten und Quellencluster (`StR-029`–`StR-034`) — Status: Missing

What exists:
- traceability and source-context tables exist

What is missing:
- no source dependency clustering
- no detection of replication vs independent evidence
- no semantic or temporal source coupling analysis

Gap to document:
- this is currently outside the implemented analytical core

Recommended next development:
- later dedicated source-dependency analysis slice after live source ingestion is working

## G Source Lineage (`StR-035`–`StR-039`) — Status: Partial

What exists:
- traceability/lineage from raw to report exists
- GUI lineage view exists

What is missing:
- source-origin inference is not implemented
- earliest known source / propagation path / origin uncertainty are not analytically modeled

Gap to document:
- current lineage is transformation lineage, not true source-origin lineage

Recommended next development:
- separate “source-origin lineage” work package after source-dependency groundwork

## H Informations-Epidemiologie (`StR-040`–`StR-044`) — Status: Missing

What exists:
- concept only in requirements/docs

What is missing:
- no spread timeline, cross-country spread, amplification, mutation, or persistence logic
- no GUI visualization for information spread

Gap to document:
- stakeholder intent exists, product capability does not yet exist

Recommended next development:
- treat as extended analytics after core source-access and core GUI closure

## I Evidenzfusion und Cross-Domain-Kontrastierung (`StR-045`–`StR-050`) — Status: Partial

What exists:
- non-naive multi-domain framing
- rule-based domain and multi-domain logic
- explicit rejection of simple additive global fusion score

What is missing:
- richer cross-domain contrast explanations in GUI
- explicit evidence fusion audit views beyond basic explanation blocks

Gap to document:
- architectural principle is present; rich analytical contrast UX is not yet there

Recommended next development:
- strengthen explanation and comparison views once multi-country artifacts exist

## J Unsicherheit und Explainability (`StR-051`–`StR-056`) — Status: Partial

What exists:
- uncertainty fields are modeled and surfaced
- drivers, counter indicators, explanation sections exist
- source failures and trust gaps are shown

What is missing:
- uncertainty is not yet unified into a strong cross-page model
- contradiction handling and explainability depth remain limited
- visualization of confidence / uncertainty is still weak

Gap to document:
- explainability baseline exists, but stakeholder-grade interpretability is only partly fulfilled

Recommended next development:
- introduce unified uncertainty model in GUI and reports
- later add confidence/coverage overlays and visual uncertainty cues

## K Probabilistische Zustandsmodellierung (`StR-057`–`StR-061`) — Status: Deferred by intent

What exists:
- requirements position it as optional / future-facing

What is missing:
- no probabilistic state model implementation

Gap to document:
- not a current blocker for MVP fulfillment unless these items are re-prioritized upward

Recommended next development:
- keep outside immediate roadmap until deterministic MVP is materially complete

## L Validierung und Backtesting (`StR-062`–`StR-066`) — Status: Partial

What exists:
- validation case model exists
- validation readmodel exists
- validation GUI page exists
- reprocessing comparison exists

What is missing:
- latest artifact bundle still lacks consistent validation artifact emission
- real historical replay depth is limited
- case volume is far below the desired baseline

Gap to document:
- validation capability exists structurally, but not yet as a robust artifact-backed product path

Recommended next development:
- close validation artifact generation first
- then expand reference-case catalog

## M Projekt- und Nutzungsziel (`StR-067`–`StR-070`) — Status: Partial

What exists:
- modular repo structure
- strong method/governance orientation
- educational/portfolio positioning fits current state

What is missing:
- visible product maturity still lags the stated ambition of a serious analytical showcase

Gap to document:
- foundation supports the stated project goal, but product completeness is still insufficient

Recommended next development:
- continue roadmap; no separate dedicated work package needed

## N GUI Grundanforderungen (`StR-071`–`StR-080`) — Status: Partial

What exists:
- GUI exists
- countries are primary object
- country profile exists
- several pages exist

What is missing:
- A–E are not broadly represented in practice
- time, baseline, anomaly and uncertainty are not yet strongly visualized
- interactivity is low

Gap to document:
- GUI baseline is present, but stakeholder-grade GUI fulfillment is not achieved

Recommended next development:
- visual analyst GUI phase (charts, map, controls)

## N GUI Nutzungsmodi (`StR-081`–`StR-088`) — Status: Partial

What exists:
- core use cases UC-001..UC-004 are now navigable
- drill-down and explanation flows exist

What is missing:
- no true exploratory interaction depth
- trace from aggregate to evidence exists only partially in product UX terms
- comparison and guided exploration are weak

Gap to document:
- navigation is available, but analyst workflow ergonomics are still basic

Recommended next development:
- strengthen filter/control/comparison workflows

## N GUI Seitenstruktur (`StR-089`–`StR-100`) — Status: Partial

What exists:
- multiple specialized pages exist
- readiness page exists
- source/coverage, system status, export, validation, annotations pages exist

What is missing:
- start page is not a real world map
- several pages still render primarily tables/text instead of stakeholder-expected visuals
- source-lineage/epidemiology and comparison views remain absent

Gap to document:
- page inventory is broadly present, but several pages are placeholders relative to stakeholder intent

Recommended next development:
- map page, chart page, comparison page, source-lineage page

## N GUI Weltkarte und Score-Modi (`StR-101`–`StR-110`) — Status: Missing

What exists:
- overview table with baseline mode text
- domain contribution info in readmodel

What is missing:
- no real world map
- no configurable map modes
- no meaningful score/overlay controls
- no multi-domain anomaly visualization on a geographic layer

Gap to document:
- one of the most visible stakeholder expectations is still not fulfilled

Recommended next development:
- dedicated world-map visualization work package after multi-country artifacts are available

## O Kartenbaseline und Vergleichsskala (`StR-111`–`StR-117`) — Status: Weak

What exists:
- baseline mode is represented textually
- scoring/baseline modules exist underneath

What is missing:
- no GUI switching between relative baseline and global comparison mode
- no explicit visual indication of comparison-scale semantics in a real map

Gap to document:
- baseline logic exists in architecture, but not as a stakeholder-usable GUI feature

Recommended next development:
- implement baseline/mode controls after charts/map foundation

## O Multi-Window-Baselines (`StR-118`–`StR-128`) — Status: Partial

What exists:
- current baseline language references combined 30/90/365 mode
- baseline logic modules exist

What is missing:
- no user-facing switching between 30/90/365 and other windows
- no strong visualization of short/mid/long-term divergence

Gap to document:
- method support is partial, UX support is weak

Recommended next development:
- expose multi-window controls and trend charts

## O Aktualitätsfenster (`StR-129`–`StR-134`) — Status: Weak

What exists:
- timeframe concepts appear in requirements and some readmodel data

What is missing:
- no working GUI control for 24h/7d/30d/90d/365d switching
- no visible distinction between freshness window and baseline window beyond text

Gap to document:
- core stakeholder control is not yet implemented

Recommended next development:
- add explicit timeframe selector in GUI phase

## P Datenbank und tägliche Runs (`StR-135`–`StR-147`) — Status: Weak

What exists:
- orchestrator, raw/normalized models, features, artifacts, incremental run concepts
- run artifact generation exists

What is missing:
- no proven historical database build from real sources
- no operationally proven daily ingestion pipeline over real external data
- current latest bundle does not demonstrate real incremental breadth

Gap to document:
- run architecture exists; real data operations do not yet exist at required maturity

Recommended next development:
- real source adapters, persistence model hardening, reproducible ingestion runs

## P Historischer Datenhorizont und Data Sufficiency (`StR-148`–`StR-161`) — Status: Partial

What exists:
- data sufficiency logic exists
- history horizon concept is surfaced in source coverage

What is missing:
- not yet backed by real multi-year source histories in the system
- data gaps across countries/sources/periods are not yet richly visualized

Gap to document:
- concept implemented, empirical historical basis not yet materially built

Recommended next development:
- real history ingestion for selected core sources
- gap visualizations in source coverage and map overlays

## Q MVP-Länderauswahl (`StR-162`–`StR-178`) — Status: Partial

What exists:
- versioned MVP country set exists in `vmodel/project/mvp_countries.yaml`
- configuration structure is in place

What is missing:
- runtime/artifact population does not yet reflect that broader configured set
- GUI/latest bundle does not expose anything close to the intended country breadth

Gap to document:
- configured breadth exists; delivered breadth does not

Recommended next development:
- diagnose why latest bundle contains only UKR
- generate real representative multi-country artifacts

## Q Länderpriorisierung (`StR-179`–`StR-187`) — Status: Partial

What exists:
- P1/P2/P3 prioritization exists in the configured country set

What is missing:
- prioritization is not yet a visible operational GUI dimension
- integration depth by priority class is not yet systematically reflected in artifact outputs

Gap to document:
- governance-level prioritization exists, product-level prioritization is weak

Recommended next development:
- expose priority class in world overview and coverage views

## R MVP-Domänenumfang (`StR-188`–`StR-196`) — Status: Partial

What exists:
- A/B/D are the strongest implemented domains in code (`features/domain_a.py`, `domain_b.py`, `domain_d.py`)
- C/E are explicitly selective/prepared in requirements

What is missing:
- no equivalent mature domain feature stack for C/E
- selective P1 behavior is not yet materially demonstrated in product outputs

Gap to document:
- core-domain intent is partly met; C/E integration remains largely future-facing

Recommended next development:
- do not expand C/E broadly before A/B/D + data access + multi-country are operational

## Q MVP-Länderset v0.1 (`StR-197`–`StR-204`) — Status: Weak

What exists:
- 30-country style configured set exists

What is missing:
- current generated outputs do not represent this set
- demo and latest artifacts show only tiny subsets

Gap to document:
- configured MVP set is not yet product-visible

Recommended next development:
- multi-country artifact work package is mandatory before claiming MVP breadth

## S Datenquellenverwaltung und ACLED (`StR-205`–`StR-214`) — Status: Partial

What exists:
- ACLED is correctly modeled as prepared/optional and not MVP-core
- source adapter abstraction exists
- governance metadata checks exist

What is missing:
- each real source as its own implemented adapter is not yet true in code
- source-specific metadata and adapter IDs are not yet operationally manifested end-to-end

Gap to document:
- governance intent is present; real source integration is not yet present

Recommended next development:
- adapter-by-adapter implementation starting with non-ACLED open sources

## S Festgelegte Datenquellen (`StR-215`–`StR-225`) — Status: Weak

What exists:
- target source list exists in requirements and `data_sources.yaml`

What is missing:
- GDELT / RSS / institutional feeds / UCDP / ReliefWeb / GDACS / World Bank / IMF / UN Comtrade / FAOSTAT are not yet visibly integrated as implemented live adapters

Gap to document:
- one of the largest substantive fulfillment gaps in the entire project

Recommended next development:
- choose first three feasible core sources and integrate them serially

## T Funktionsrahmen ohne General Fusion Score (`StR-226`–`StR-235`) — Status: Done to Partial

What exists:
- project explicitly avoids naive general fusion score
- domain-specific logic is present
- multi-domain logic is rule-based and non-additive in principle

What is missing:
- explanation UX can still be improved

Gap to document:
- concept largely fulfilled; only presentation/explanation quality remains

Recommended next development:
- no urgent dedicated package beyond later explainability polish

## U Multi-Domain-Status (`StR-236`–`StR-244`) — Status: Partial

What exists:
- rule-based multi-domain status exists
- contributing domains are shown
- status is part of world/country views

What is missing:
- real domain breadth and multi-country usage are still limited
- stakeholder-visible explanation of conflicts/coupling can be richer

Gap to document:
- mathematically/architecturally present; product breadth still lacking

Recommended next development:
- improve conflict explanation and multi-country visibility after P2

## U Einbindung C/E in Multi-Domain-Status (`StR-245`–`StR-254`) — Status: Weak

What exists:
- requirement intent and selective-domain framing

What is missing:
- no mature operational C/E contribution path demonstrated

Gap to document:
- currently mostly future-preparation, not substantive fulfillment

Recommended next development:
- defer until source access and core domains are materially complete

## V Domänenstatus D0-D5 (`StR-255`–`StR-265`) — Status: Partial to Done

What exists:
- domain status model exists
- D0–D5 logic and explanation are in place in the analytical core

What is missing:
- richer visual explanation in GUI
- broader domain coverage in practice

Gap to document:
- core modeling is strong; broad operational expression remains incomplete

Recommended next development:
- keep stable, improve visibility not logic first

## W Regelbasierte Bewertung und Annotationen (`StR-266`–`StR-281`) — Status: Partial

What exists:
- rule-based MVP direction is implemented
- annotation model exists
- rules/versions are represented in snapshots and traceability context

What is missing:
- rule editing/tuning workflow is not productized
- triggered-rule explanations can be richer in GUI
- annotation workflows are mostly read/display oriented

Gap to document:
- strong foundation, incomplete analyst tooling

Recommended next development:
- later admin/config workflow for rule tuning
- stronger explanation view per status decision

## W Annotationen ohne Review im MVP (`StR-282`–`StR-290`) — Status: Partial

What exists:
- annotation storage model exists
- annotations are visible in GUI
- review status field is modeled

What is missing:
- create/edit/filter/history workflow in the GUI is absent
- analyst-facing annotation operations are not yet operational

Gap to document:
- annotations exist as data structure and display, not yet as a usable analyst workflow

Recommended next development:
- dedicated annotation workflow package in GUI phase

## X Report und Export (`StR-291`–`StR-300`) — Status: Partial

What exists:
- report/export view exists
- JSON/Markdown support exists
- coverage/domain/event style report generators exist
- export governance exists

What is missing:
- report generation from GUI is still limited/simple
- richer export selection, timeframe/country/domain scoping, and PDF pipeline are not there

Gap to document:
- export baseline is real, but full stakeholder flexibility is not met

Recommended next development:
- stronger interactive report generation after GUI controls exist

## X Automatische und manuelle Reports (`StR-301`–`StR-310`) — Status: Partial

What exists:
- daily snapshot report exists
- manual reports exist in code
- evidence context is increasingly visible

What is missing:
- report breadth and UX remain basic
- event/domain/coverage reporting is not yet a polished analyst operation flow

Gap to document:
- report core exists; product workflow is still underpowered

Recommended next development:
- integrate report actions into richer GUI/use-case flows

## Y Analyse-Funktionsrahmen A-E (`StR-311`–`StR-327`) — Status: Partial

What exists:
- strong domain framing exists
- A/B/D have code-level feature implementations

What is missing:
- C/E do not yet have comparable maturity
- A/B/D themselves are not yet backed by real source breadth

Gap to document:
- domain framework is conceptually good, but asymmetrically implemented

Recommended next development:
- complete real-source-backed A/B/D first; postpone broad C/E ambition

## Z MVP Feature Set (`StR-328`–`StR-340`) — Status: Partial

What exists:
- feature modules for domains A/B/D
- feature values included in domain details

What is missing:
- feature-set management is not yet surfaced as a governed artifact/product feature set with visible priority and source coverage per feature
- broader feature catalog fulfillment across all intended domains is incomplete

Gap to document:
- implemented features exist, but “MVP feature set” is not yet materially fulfilled as a broad visible system capability

Recommended next development:
- establish visible feature inventory tied to source/domain/country coverage

## AA Nutzerrollen und Berechtigungen (`StR-341`–`StR-350`) — Status: Weak

What exists:
- role model exists in governance code
- action permissions are modeled

What is missing:
- role-specific GUI behavior is largely absent
- analyst/admin/viewer experience is not actually separated in the product

Gap to document:
- requirements are structurally recognized, not functionally delivered

Recommended next development:
- introduce role-aware UI once the core analyst workflows themselves are mature

## Use Cases (`StR-351`–`StR-357`) — Status: Partial

What exists:
- UC-001..UC-004 are explicitly supported in current GUI baseline
- UC-005 exists in baseline but artifact completeness is still weak

What is missing:
- UC-005 not yet robustly artifact-backed
- UC-006 rule tuning still not operationalized beyond config concepts

Gap to document:
- mandatory use cases are structurally present, but not all are product-strong yet

Recommended next development:
- strengthen validation use case first, rule-tuning later

## Validierung & Backtesting (`StR-358`–`StR-381`) — Status: Weak to Partial

What exists:
- one modeled validation path exists
- comparison and reprocessing baseline exist

What is missing:
- no evidence yet of 10–15 curated reference cases
- no visible per-P1-country validation library
- latest artifact gap still open

Gap to document:
- one of the largest remaining analytical-method gaps

Recommended next development:
- expand reference-case inventory after artifact gap is closed

## Qualitätsanforderungen (`StR-382`–`StR-416`) — Status: Partial to Done

What exists:
- traceability and governed evidence are among the strongest parts of the repo
- snapshot, lineage, repo closure, tests, version references exist

What is missing:
- some quality claims are stronger in governance than in real runtime breadth
- product-grade completeness across live data and GUI still lags behind governance completeness

Gap to document:
- quality/governance layer is ahead of product/runtime layer

Recommended next development:
- keep quality bar, but move effort into runtime/data/product gaps

## Daten-Governance / Lizenz / personenbezogene Analyse (`StR-417`–`StR-451`) — Status: Partial

What exists:
- export policy blocks personal-data exports and blocked capabilities
- source governance metadata validation exists
- deactivated/prepared sources are conceptually modeled

What is missing:
- source-specific legal/licensing handling is not yet operationally demonstrated per real adapter
- run/log/report handling for deactivated live sources is not yet proven with real source inventory

Gap to document:
- governance controls exist, but have not yet been stress-tested against real integrated source set

Recommended next development:
- fold governance checks into each new real adapter implementation

## Ethik & Missbrauchsbegrenzung (`StR-452`–`StR-473`) — Status: Partial

What exists:
- export governance blocks clearly out-of-scope capabilities
- project framing is explicitly analysis-oriented, not operational targeting

What is missing:
- user-facing ethics guidance in GUI/reports is still light
- broader misuse-prevention mechanisms are mostly governance/document-based, not product-enforced workflow design

Gap to document:
- baseline ethical controls exist, but product-level guardrails can be made more explicit

Recommended next development:
- add visible ethics/use-boundary cues in export/readiness/report flows later

## Betrieb & Automatisierung (`StR-474`–`StR-520`) — Status: Partial

What exists:
- local operation is supported
- Python project structure and tests exist
- artifact generation and local GUI build are reproducible enough for development

What is missing:
- no Dockerfile / container baseline found
- no proven scheduler/automation path over real source operations
- operational run/deploy hardening is still limited

Gap to document:
- local dev MVP exists; production-like operations are not yet fulfilled

Recommended next development:
- after core data/product closure, add containerization and scheduled-run packaging

## Traceability & Versionierung (`StR-521`–`StR-561`) — Status: Done to Partial

What exists:
- this is a strong area: requirement IDs, trace links, lineage, snapshots, repo closure, version references

What is missing:
- source adapter IDs / real source versioning become meaningful only once real adapters exist

Gap to document:
- structurally strong; a few parts await real source integration

Recommended next development:
- extend current traceability rigor into new adapters and data runs

## Definition of Done / MVP-Abnahme (`StR-562`–`StR-605`) — Status: Weak to Partial

What exists:
- some MVP baseline items are clearly fulfilled in governance and GUI baseline
- readiness view and acceptance review exist

What is missing:
- 30-country visibility is not fulfilled in product outputs
- 3-year historical data across core domains is not yet demonstrated
- real-source-backed A/B/D breadth is not yet demonstrated
- validation reference-case volume is not yet demonstrated
- true world map / charts / controls are not yet delivered

Gap to document:
- this category currently exposes the clearest difference between “repo baseline complete” and “stakeholder MVP complete”

Recommended next development:
- treat this category as the final acceptance gate, not as already achieved

## MVP-Priorisierung & Akzeptanzkriterien (`StR-606`–`StR-622`) — Status: Partial

What exists:
- prioritized use cases and MVP framing exist in docs and requirements

What is missing:
- the product still needs a more explicit acceptance dashboard against these items

Gap to document:
- prioritization exists; acceptance closure still needs a stronger operational checklist

Recommended next development:
- later add requirement-cluster acceptance board tied to roadmap completion

## Systemgrenzen / externe Systeme (`StR-623`–`StR-646`) — Status: Partial to Done

What exists:
- system boundary is well documented
- external sources are treated as dependencies, not internal components
- adapter-based boundary is architecturally correct

What is missing:
- live dependency handling and operational degradation logic are not yet fully demonstrated with real sources

Gap to document:
- boundary definition is strong; runtime proof remains incomplete

Recommended next development:
- validate boundary behavior during real-source integration phase

## Risiken & Annahmen (`StR-647`–`StR-660`) — Status: Done to Partial

What exists:
- assumptions and risks are documented in `vmodel/project/`

What is missing:
- some major risks are still not actively burned down, especially source access and runtime breadth

Gap to document:
- risk register exists, but must now drive execution order more explicitly

Recommended next development:
- update risk-driven prioritization after P0 access assessment

## Glossar / Begriffsdefinitionen (`StR-661`–`StR-668`) — Status: Partial to Done

What exists:
- glossary artifact exists
- governance vocabulary is already relatively controlled

What is missing:
- product/UI/report language should continue to be checked against glossary during future GUI expansion

Gap to document:
- low risk compared to runtime/product gaps

Recommended next development:
- keep maintained as supporting governance work

---

## 4. Cross-cutting missing content summary

The full sweep shows five dominant missing-content groups.

### Gap Group G1: Real source access and real data ingestion
This is the deepest factual gap.

Missing content:
- concrete adapters for real external sources
- credential/access classification and governance per source
- real fetched data replacing synthetic `SRC-A` / `SRC-B` placeholders
- real multi-country input breadth

Affected categories:
- B, C, P, P-history, S-data-sources, Systemgrenzen, Definition of Done

### Gap Group G2: Runtime completeness and representative artifact outputs
Missing content:
- complete latest bundle including validation artifact path
- artifact population for more than one country
- visible fulfillment of configured 30-country MVP intent

Affected categories:
- L, Q, P, Use Cases, Validation, Definition of Done

### Gap Group G3: Analyst-grade GUI instead of static HTML baseline
Missing content:
- real world map
- charts/plots
- time-window and baseline controls
- comparison workflows
- richer visual explanation and uncertainty display

Affected categories:
- N, O, D, J, X, Definition of Done

### Gap Group G4: Advanced source intelligence
Missing content:
- source dependency clustering
- origin/source lineage inference
- epidemiology/spread analysis

Affected categories:
- F, G, H

### Gap Group G5: Operational analyst workflows
Missing content:
- annotation create/edit/filter/history workflow
- role-aware UI behavior
- larger validation reference-case portfolio
- rule-tuning/admin workflows

Affected categories:
- AA, W, Use Cases, Validation, X

---

## 5. Development sequence that should now be executed step by step

This is the recommended serial order. Each work package should be fully completed with tests/validation before the next one begins.

## Phase P0 — Real-source-access readiness

### P0-WP-001: Build the governed source-access matrix
Objective:
- classify every stakeholder-relevant source as accessible now / requires credentials / legally constrained / deferred

Deliverables:
- source-access assessment document
- updated roadmap references
- recommended first live-source set
- implemented as `docs/plans/siasa-p0-wp-001-source-access-assessment.md`

Why first:
- without this, all later GUI/data work risks staying demo-based

### P0-WP-002: Implement first live core source adapter
Objective:
- integrate the first high-value real source with full governance metadata, tests, and artifact output

Recommended first source:
- GDELT or ReliefWeb, depending on access friction

Deliverables:
- concrete adapter under `src/siasa/adapters/`
- tests for fetch + normalization handoff
- artifacts showing real source provenance

### P0-WP-003: Add second and third live core sources
Objective:
- establish minimum real-source diversity for A/B/D

Recommended sources:
- one from A/B pair: GDELT + ReliefWeb/UCDP GED
- one from D: World Bank Indicators

Deliverables:
- three governed real source paths in operation
- source coverage readmodel populated by real source metadata

## Phase P1 — Runtime and artifact completeness

### P1-WP-001: Close validation artifact gap
Objective:
- always emit `validation_backtest.json` when governed validation inputs exist

### P1-WP-002: Explicitly encode artifact absence reasons
Objective:
- distinguish not-configured vs no-data vs not-yet-implemented

### P1-WP-003: Produce a real artifact-backed latest bundle
Objective:
- latest bundle should be a credible runtime output, not just a thin verification/demo subset

## Phase P2 — Multi-country system reality

### P2-WP-001: Diagnose single-country latest bundle root cause
Objective:
- determine why current latest bundle exposes only UKR despite broader country configuration

### P2-WP-002: Generate representative multi-country bundle
Objective:
- latest bundle should include a meaningful subset across P1/P2/P3 countries

Minimum acceptance target:
- multiple countries on overview
- multiple generated country profiles
- clear reflection of priority classes and available domain breadth

## Phase P3 — Visual analyst GUI closure

### P3-WP-001: Replace JSON/text trend blocks with charts
Objective:
- make yearly trends and domain detail analytically readable

### P3-WP-002: Implement real world-map entry page
Objective:
- fulfill the most visible GUI stakeholder expectation

### P3-WP-003: Implement baseline/time-window/domain controls
Objective:
- convert GUI from viewer to exploratory tool

### P3-WP-004: Add cross-country comparison page
Objective:
- support actual comparative analysis

### P3-WP-005: Improve uncertainty/coverage visualization
Objective:
- visually communicate confidence, data gaps, and coverage, not just textually

## Phase P4 — Analyst workflow completion

### P4-WP-001: Annotation create/edit/filter/history workflow
Objective:
- make annotations an operational analyst tool, not just a displayed artifact

### P4-WP-002: Role-aware GUI behavior
Objective:
- separate analyst/admin/viewer capabilities meaningfully

### P4-WP-003: Rule-tuning/admin workflow
Objective:
- operationalize UC-006 in a governed admin-only path

### P4-WP-004: Expand validation reference-case inventory
Objective:
- move from thin validation baseline toward stakeholder-expected backtest library

## Phase P5 — Advanced stakeholder features

### P5-WP-001: Source dependency clustering
### P5-WP-002: Source-origin lineage inference
### P5-WP-003: Information epidemiology / spread analysis
### P5-WP-004: Advanced export authoring and extended overlays

These should not be started before P0–P4 are materially complete.

---

## 6. Immediate next recommendation

The next execution step should be:

1. P0-WP-001 — Build the governed source-access matrix

Reason:
- the stakeholder sweep shows that the single biggest factual gap is not charts or map polish, but the lack of proven real-source integration
- without closing that, many later claims remain demo-like rather than product-like

After P0-WP-001, the next serial step should be:

2. P0-WP-002 — Implement the first live core source adapter

Only then should the team continue into runtime completeness and multi-country artifact closure.

---

## 7. Definition of “stakeholder-fulfilled SIASA” after this sweep

After this gap analysis, SIASA should only be described as broadly stakeholder-fulfilled when all of the following are true:

- real external source access is operational for the MVP-core source set
- latest artifacts are complete and validation-backed
- multi-country output materially reflects the configured MVP country set
- GUI offers a real world map, charts, and exploration controls
- core analyst workflows are operational, not only structurally visible
- advanced features remain clearly marked as extended if still pending

Until then, the accurate description is:
- strong governed analytical MVP baseline
- incomplete data/runtime/product fulfillment relative to the stakeholder ambition
