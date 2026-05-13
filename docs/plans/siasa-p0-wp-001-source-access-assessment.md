# SIASA P0-WP-001 — Governed Source-Access Assessment

Goal: create the governed source-access matrix required by `docs/plans/siasa-stakeholder-gap-sweep-and-development-sequence.md` and `docs/plans/siasa-stakeholder-fulfillment-roadmap.md`, so the next implementation work packages start from explicit source-access facts instead of assumptions.

Scope: this assessment is repo-grounded. It uses the governed source catalog and surrounding assumptions/decisions. It does not yet claim live network validation against each provider endpoint. Live technical verification belongs to P0-WP-002 and the first real adapter implementations.

Primary evidence base:
- `vmodel/project/data_sources.yaml`
- `vmodel/project/assumptions.yaml`
- `vmodel/project/decisions.yaml`
- `vmodel/project/config_tables.yaml`
- `src/siasa/adapters/`
- `src/siasa/runs/orchestrator.py`
- `src/siasa/runs/artifacts.py`
- `pyproject.toml`
- `docs/plans/siasa-stakeholder-gap-sweep-and-development-sequence.md`
- `docs/plans/siasa-stakeholder-fulfillment-roadmap.md`

---

## 1. Core findings

### 1.1 Current repo reality

The repo currently has:
- a governed source catalog
- adapter abstractions (`SourceAdapter`, `FetchResult`, fetch metadata)
- orchestration and artifact generation structure
- no concrete live source adapter implementations under `src/siasa/adapters/`

Therefore the current source situation is:
- governed concept: present
- technical integration scaffolding: present
- real productive source access: not yet implemented

### 1.2 Catalog-scale summary

The governed source catalog currently contains `38` candidate sources across domains `A`, `B`, `C`, `D`, and `E`.

Status distribution from the governed catalog:
- `Core`: 5
- `Core/Extended`: 6
- `Extended`: 14
- `Selektiv P1`: 7
- `Extended/Selektiv P1`: 1
- `Prepared Adapter`: 4
- `Prepared/Extended`: 1

This confirms an important planning fact:
- the catalog breadth is already large
- but the near-term implementation path must focus on a much smaller first-wave subset

### 1.3 Access-risk pattern

From the governed catalog and assumptions, the source landscape separates into four practical groups:

1. Direct public / low-friction candidates
- best first implementation targets
- typically open API / open data / public download

2. Public but integration-shaped candidates
- technically usable, but schema/history/query model is less straightforward
- good second wave after first adapters are proven

3. Registration / API-key / provider-friction candidates
- viable, but not ideal for the first real-source slice

4. Governance-constrained or intentionally deferred candidates
- legal, cost, access, or policy reasons make them bad first-wave targets
- these should not block MVP-core progress

### 1.4 Recommended first-wave principle

Because current implemented feature logic is strongest in domains A, B, and D, and because SIASA currently lacks any live source adapters, the first live integrations should maximize:
- low access friction
- high governance clarity
- stable historical availability
- direct fit to already implemented A/B/D feature and readmodel paths
- low new dependency pressure in the Python project

That leads to this first-wave recommendation:
- Wave 1A: World Bank Indicators API
- Wave 1B: ReliefWeb API
- Wave 1C: GDELT 2.0 Events/GKG/DOC API

Rationale:
- together they cover D, B, and A
- all three are governed as open or low-friction sources
- they avoid the access blockers explicitly attached to ACLED, X, Telegram, AIS, etc.
- they create the minimum credible real-source basis for later multi-country artifact generation

---

## 2. Assessment dimensions used in the matrix

### 2.1 Access class
- A0 = direct public access appears feasible from governed artifacts
- A1 = registration or API key likely needed
- A2 = legal / cost / policy / operational clarification needed first
- A3 = intentionally deferred by current MVP governance

### 2.2 Integration readiness
- R0 = no implementation exists yet
- R1 = good first-wave candidate
- R2 = viable second-wave candidate
- R3 = later/extended candidate
- R4 = defer until governance or access constraints are resolved

### 2.3 Delivery wave semantics
- Wave 1 = implement immediately after this assessment
- Wave 2 = implement after first live-source path is proven
- Wave 3 = later extended/optional integration
- Hold = not for near-term execution

---

## 3. Current technical constraints for source implementation

Observed from the repo:
- `src/siasa/adapters/` contains only `base.py`, `fetch_metadata.py`, and `__init__.py`
- `pyproject.toml` currently declares only `PyYAML` as runtime dependency
- this means first adapters should prefer Python stdlib or very small dependency growth
- current features exist for domains `A`, `B`, and `D`, but not at comparable maturity for `C` and `E`
- current latest artifact bundle is too small to validate stakeholder breadth, so first sources should support multi-country evidence quickly

Implementation consequence:
- do not start P0-WP-002 with a high-friction provider
- do not start with prepared/deferred sources just because they are analytically attractive
- do not expand into C/E before at least one real A/B/D path is operational

---

## 4. Governed source-access matrix

| Domain | Source | Catalog status | Repo-governed access reading | Access class | Current repo integration state | Recommended readiness | Delivery wave | Recommendation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | GDELT 2.0 Events/GKG/DOC API | Core | `frei/open data` | A0 | no adapter implementation | R1 | Wave 1 | Strong first-wave candidate for information-domain live input |
| A | RSS / News Feeds | Core | `frei/websiteabhängig` | A0 | no adapter implementation | R2 | Wave 2 | Useful, but feed curation/normalization complexity is higher than one stable API |
| A | Offizielle Regierungs-/Institutionenfeeds | Core/Extended | `frei, kuratiert` | A0 | no adapter implementation | R2 | Wave 2 | Good curated signal path after first generic A-source is working |
| A | Media Cloud | Extended | `API/Registrierung möglich` | A1 | no adapter implementation | R3 | Wave 3 | Valuable, but not first-wave due to registration friction |
| A/E | EUvsDisinfo | Extended | `öffentlich` | A0 | no adapter implementation | R3 | Wave 3 | Useful for later A/E specialization, not first MVP-core live slice |
| A | Reddit / Mastodon | Extended | `API/Regeln` | A1 | no adapter implementation | R3 | Wave 3 | Governance and platform-rule complexity; later only |
| A | Telegram | Prepared Adapter | `technisch/rechtlich prüfen` | A2 | intentionally not implemented | R4 | Hold | Do not use in first phases |
| A | X/Twitter | Prepared Adapter | `API/Kosten` | A2 | intentionally not implemented | R4 | Hold | Do not use in first phases |
| B | UCDP GED | Core | `frei/API/Download` | A0 | no adapter implementation | R2 | Wave 2 | Good second-wave B-source, especially for historically grounded conflict evidence |
| B | GDELT Events | Core | `frei/open data` | A0 | no adapter implementation | R2 | Wave 2 | Strong candidate, but sequence after one initial GDELT A path avoids too much provider complexity at once |
| B | ReliefWeb API | Core/Extended | `frei/API` | A0 | no adapter implementation | R1 | Wave 1 | Excellent first-wave B-source: open, humanitarian, country-oriented, useful for artifact breadth |
| B | GDACS | Core/Extended | `frei/API` | A0 | no adapter implementation | R2 | Wave 2 | Good second-wave disaster/shock source |
| B | INFORM Risk Index | Extended | `öffentlich` | A0 | no adapter implementation | R3 | Wave 3 | More structural than daily-run oriented; later |
| B | Global Terrorism Database | Extended | `öffentlich/Download prüfen` | A1 | no adapter implementation | R3 | Wave 3 | Historical validation value, but not ideal first-run source |
| B | ACLED | Prepared Adapter | `kein Zugriff im MVP` | A3 | intentionally deferred by decision D-014 | R4 | Hold | Explicitly out of MVP dependency path |
| C | NASA FIRMS | Selektiv P1 | `frei/API` | A0 | no adapter implementation | R3 | Wave 3 | Viable later selective P1 source after core A/B/D is stable |
| C | VIIRS / Black Marble Nighttime Lights | Selektiv P1 | `frei/earthdata` | A1 | no adapter implementation | R3 | Wave 3 | Valuable, but not first-wave complexity fit |
| C | Copernicus / Sentinel | Selektiv P1 | `frei/API` | A0 | no adapter implementation | R3 | Wave 3 | Data-intensive; defer until core pipeline proves out |
| C | OpenSky Network | Extended/Selektiv P1 | `API/Registrierung` | A1 | no adapter implementation | R3 | Wave 3 | Registration and selective P1 character make it later work |
| C | AIS-Schiffsdaten | Prepared Adapter | `oft nicht frei` | A2 | intentionally not implemented | R4 | Hold | Not appropriate for near-term MVP-core progress |
| C | OpenStreetMap / HOT OSM | Extended | `frei` | A0 | no adapter implementation | R3 | Wave 3 | Better as context enrichment than first operational signal source |
| D | World Bank Indicators API | Core | `frei/API` | A0 | no adapter implementation | R1 | Wave 1 | Best first-wave D-source: stable, low-friction, broad country coverage |
| D | IMF Data API / SDMX | Core/Extended | `frei/API` | A0 | no adapter implementation | R2 | Wave 2 | Strong second-wave D-source after one simpler macro source is integrated |
| D | UN Comtrade | Core/Extended | `API-Key/Limits` | A1 | no adapter implementation | R3 | Wave 3 | Useful later; avoid early key/limit friction |
| D | FAOSTAT | Core/Extended | `frei/API` | A0 | no adapter implementation | R2 | Wave 2 | Good second-wave structural/economic source |
| D | OECD Data Explorer | Extended | `API` | A1 | no adapter implementation | R3 | Wave 3 | Useful mainly for extended/control-country analysis |
| D | Our World in Data | Extended | `frei` | A0 | no adapter implementation | R3 | Wave 3 | Useful as curated enrichment, not first live source |
| D | FRED | Extended | `API` | A1 | no adapter implementation | R3 | Wave 3 | Coverage varies by country; later |
| D | ECB Data Portal | Extended | `API` | A1 | no adapter implementation | R3 | Wave 3 | Regionally useful, but not first global candidate |
| D | EIA / IEA öffentliche Daten | Extended | `Lizenz/API prüfen` | A2 | no adapter implementation | R4 | Hold | Clarify license and access before any implementation |
| D | ENTSO-E Transparency Platform | Extended | `Registrierung/API` | A1 | no adapter implementation | R3 | Wave 3 | Later Europe-focused enhancement |
| E | CISA KEV Catalog | Selektiv P1 | `frei CSV/JSON` | A0 | no adapter implementation | R3 | Wave 3 | Good later selective E-source once E-domain work starts |
| E | NVD CVE API | Selektiv P1 | `frei/API` | A0 | no adapter implementation | R3 | Wave 3 | Useful later, but country attribution challenge makes it not first-wave |
| E | Cloudflare Radar / Outage Center | Selektiv P1 | `API/öffentlich` | A0 | no adapter implementation | R3 | Wave 3 | Later outage-focused E-source |
| E | Google Transparency Report Traffic | Selektiv P1 | `öffentlich` | A0 | no adapter implementation | R3 | Wave 3 | Later independent disruption signal |
| E | nationale CERT/CSIRT Feeds | Extended | `frei/kuratiert` | A0 | no adapter implementation | R3 | Wave 3 | Curation-heavy; later |
| E | Shadowserver | Prepared/Extended | `Zugriff prüfen` | A2 | intentionally not implemented | R4 | Hold | Defer until access/governance are explicit |
| E | Abuse.ch Feeds | Extended | `frei` | A0 | no adapter implementation | R3 | Wave 3 | Good later E-enrichment candidate |

---

## 5. Recommended implementation order after P0-WP-001

## Wave 1 — minimum credible live-source baseline for SIASA

### 5.1 First source: World Bank Indicators API
Why first:
- domain D is already implemented in the feature stack
- broad country coverage
- stable open API
- minimal governance ambiguity
- easy to demonstrate real multi-country structural coverage quickly

Expected gain:
- first real-source-backed multi-country breadth in artifacts
- low implementation friction
- strong base for country coverage expansion

### 5.2 Second source: ReliefWeb API
Why second:
- strong country-oriented crisis/event context for domain B
- open API with practical analytical value
- complements World Bank well without relying on high-friction providers

Expected gain:
- real B-domain live input
- humanitarian/event signal context that is easier to explain in GUI and reports

### 5.3 Third source: GDELT 2.0 Events/GKG/DOC API
Why third:
- high value for domain A and potentially B-related information context
- open-data path
- analytically central for the project vision

Why not necessarily first:
- broader schema/query complexity than World Bank
- better implemented once one simpler source path and one event-oriented source path already work

Expected gain:
- first real information-domain path
- strong basis for Daily Global Review realism

---

## 6. Recommended second-wave order

After Wave 1 is stable:
- UCDP GED
- GDACS
- IMF Data API / SDMX
- FAOSTAT
- Offizielle Regierungs-/Institutionenfeeds
- GDELT Events

Purpose of Wave 2:
- deepen B and D
- add robustness and triangulation
- improve historical and cross-country evidence quality

---

## 7. Explicit defer / hold list

These should not be near-term blockers for SIASA MVP closure:
- ACLED
- Telegram
- X/Twitter
- AIS-Schiffsdaten
- Shadowserver
- EIA / IEA until access/licensing is clarified

Reason:
- current governance or access posture makes them poor first-wave choices
- SIASA can make substantial stakeholder-progress without them

---

## 8. Immediate execution recommendation

The next serial work packages should be:

1. P0-WP-002a
- implement `World Bank Indicators API` adapter end-to-end

2. P0-WP-002b
- implement `ReliefWeb API` adapter end-to-end

3. P0-WP-002c
- implement `GDELT 2.0 Events/GKG/DOC API` adapter end-to-end

Only after those three are working should SIASA move to:
- artifact completeness closure
- representative multi-country bundle generation
- major GUI visualization work

---

## 9. Definition of done for P0-WP-001

P0-WP-001 is complete when:
- the source-access matrix exists as a governed document
- each catalog source has an explicit access/readiness classification
- the first live-source candidates are selected with rationale
- deferred/high-friction sources are explicitly called out
- the roadmap and gap-sweep documents reference this assessment as the execution baseline for P0-WP-002
