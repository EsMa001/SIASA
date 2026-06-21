# SIASA P0-WP-002c — Domain-B Source Selection After ReliefWeb Blocker

Goal: choose the next Domain-B source implementation candidate after the ReliefWeb V2 access blocker and make the selection traceable to existing Domain-B feature expectations.

Decision basis:
- `src/siasa/features/domain_b.py`
- `docs/method/feature_catalog.md`
- `vmodel/method/feature_catalog.yaml`
- `vmodel/requirements/software_requirements.yaml`
- `vmodel/project/data_sources.yaml`
- `docs/plans/siasa-p0-wp-001-source-access-assessment.md`
- live source-access findings from the current execution session

---

## 1. Core decision

The next Domain-B source to implement should be:
- `GDELT Events`

Recommended order after that:
1. `GDELT Events`
2. `GDACS`
3. `UCDP GED`
4. `ReliefWeb API` (after approved appname and explicit mapping decision)

---

## 2. Why this decision follows from the current codebase

### 2.1 What the current Domain-B feature service actually expects

The current implemented `DomainBFeatureService` consumes these signal keys:
- `conflict_event_count`
- `protest_event_count`
- `violent_event_count`
- `disaster_alert_level`

This means the next Domain-B source should preferably feed the current core signals directly, rather than requiring a new feature model first.

### 2.2 What the governed feature catalog says is Core vs Extended

The governed feature catalog marks these as especially relevant:
- Core:
  - `B_event_count`
  - `B_event_count_anomaly`
  - `B_event_type_distribution`
  - `B_violent_event_count`
  - `B_protest_event_count`
  - `B_geo_cluster_score`
- Extended:
  - `B_humanitarian_report_count`
  - `B_disaster_alert_level`

Important consequence:
- a source that supports conflict/protest/violence counts is a better immediate fit than a source that mainly supports humanitarian or disaster extensions

### 2.3 What the current source candidates best align with

#### GDELT Events
Strengths:
- explicitly governed as Domain-B core source
- open/open-data path in the catalog
- event-oriented by design
- best candidate to support the current implemented core event counters with minimal feature-model change
- analytically consistent with the already selected GDELT DOC A-domain path

Weaknesses:
- media-derived, not ground truth
- likely needs careful filtering/mapping by event type

Assessment:
- best near-term implementation candidate for Domain-B baseline

#### UCDP GED
Strengths:
- explicitly governed as Domain-B core source
- open alternative to ACLED
- historically stronger conflict grounding than media-derived event feeds

Weaknesses:
- current probe against `https://ucdpapi.pcr.uu.se/api/gedevents/25.1?pagesize=1` returned `401 Unauthorized`
- stronger fit for conflict/violence than for protest coverage
- therefore not the best next source for the full current B-core signal set

Assessment:
- strategically valuable, but no longer the next immediate implementation candidate until access/auth expectations are clarified

#### GDACS
Strengths:
- explicitly governed as Domain-B source
- directly fits `B_disaster_alert_level`
- open API posture in the governed catalog
- now the best unblocked next Domain-B candidate after UCDP returned `401 Unauthorized`

Weaknesses:
- aligns mainly with the disaster extension path, not with the current conflict/protest counters

Assessment:
- best next practical Domain-B source after GDELT Events because it remains unblocked and fits an existing implemented signal

#### ReliefWeb API
Strengths:
- strong humanitarian context source
- useful for `B_humanitarian_report_count` and broader crisis context

Weaknesses:
- current ReliefWeb V2 access requires pre-approved `appname`
- current repo has no governed mapping yet from ReliefWeb payloads into the implemented core Domain-B signals
- best fit is currently Extended, not Core

Assessment:
- not the next Domain-B source to implement
- should return only after access and signal mapping are explicit

---

## 3. Practical execution consequence

The next serial source work package after the completed World Bank and GDELT DOC slices should be:
- implement `GDELT Events` as the first Domain-B baseline source

Why:
- it fits the currently implemented Domain-B feature service best
- it is not blocked by provider-side approval like ReliefWeb
- it extends the existing GDELT family already started by `GDELTDocAdapter`
- it progresses the project toward real A+B+D coverage faster than a humanitarian/disaster-only source would

After that:
- use `GDACS` as the next unblocked disaster-alert baseline
- use `UCDP GED` after access/auth expectations are clarified to strengthen conflict credibility and depth
- use `ReliefWeb API` later for humanitarian-context enrichment once access is approved

---

## 4. Definition of done for this selection note

This note is complete when:
- the next Domain-B source choice is explicit
- the choice is tied to current implemented feature expectations
- ReliefWeb is explicitly deprioritized for current reasons, not silently forgotten
- the next implementation target is unambiguous: `GDELT Events`
