# SIASA Stakeholder Functional Closure Gap Plan

Zweck:
- Schließt die aktuell identifizierten Traceability-Lücken bei funktionalen Stakeholder-Anforderungen.
- Fokus: Anforderungen mit StR->SyR-Link, aber ohne nachweisbaren SwR-Closure.

Ausgangsbasis (repo-ermittelt):
- Funktionale StR mit SyR-Ableitung: 224
- Nachweisbar umgesetzt: 205
- Nicht nachweisbar: 19
- Analyse-Artefakte:
  - `build/analysis/stakeholder_functional_implementation_status.json`
  - `build/analysis/stakeholder_functional_implementation_status.csv`


## 1) Lückenliste und vorgeschlagene Schließung

Konvention für neue Einträge:
- Neue Software Requirements (Vorschlag): `SwR-046` ... `SwR-051`
- Neue Test-Spezifikationen (Vorschlag): `TC-SwR-046-001` ...

| Cluster | Betroffene Stakeholder Requirements | Aktueller Gap-Typ | Vorgeschlagene neue SwR | Vorgeschlagene Test-Specs |
|---|---|---|---|---|
| Mission/Scope-Grundfunktion | StR-001, StR-002, StR-004 | Auf SyR-Ebene (`SyR-001`,`SyR-002`) vorhanden, aber kein expliziter SwR-Nachweis | SwR-046 Country-centric multi-domain assessment output contract (A/B/C/D/E, country-centric views, structured situation assessment artifacts) | TC-SwR-046-001 artifact contract check; TC-SwR-046-002 country-centric projection check |
| No-deterministic / no-naive-fusion | StR-007, StR-226..230 | `SyR-003` ohne abgeleiteten SwR-Closure | SwR-047 Non-deterministic and anti-naive-fusion guardrails (forbid deterministic prediction outputs and naive additive A-E fusion pathway) | TC-SwR-047-001 prediction pathway negative test; TC-SwR-047-002 no-general-fusion-score artifact/UI scan |
| Baseline-/Anomalie-Grundforderung | StR-024, StR-025 | Über `SyR-001` nur implizit, kein expliziter SwR-Beleg | SwR-048 Relative-baseline anomaly evaluation requirement (signals must be evaluated relative to historical/country/domain/source baselines) | TC-SwR-048-001 baseline-relative scoring test; TC-SwR-048-002 anomaly detection regression set |
| Historische Datenbasis + täglicher Lauf | StR-135..142 | `SyR-008` ohne SwR-Zuordnung; damit fehlender Closure-Nachweis | SwR-049 Historical data foundation minimum horizon policy (>=3 years where available, explicit short-horizon declaration); SwR-050 Daily incremental run and snapshot production contract; SwR-051 Layered data-state separation (raw/normalized/features/status/reports) | TC-SwR-049-001 horizon policy verification; TC-SwR-050-001 daily run artifact sequence test; TC-SwR-050-002 snapshot reproducibility manifest test; TC-SwR-051-001 data-layer separation integrity test |


## 2) Konkrete normative Entwürfe (für nächste Implementierungs-PR)

### SwR-046 (neu)
The software shall produce country-centric multi-domain assessment artifacts that explicitly separate and expose domains A, B, C, D, and E for structured situation understanding.

### SwR-047 (neu)
The software shall prevent deterministic event-prediction outputs and shall prevent naive additive cross-domain A-E fusion-score pathways in the governed MVP baseline.

### SwR-048 (neu)
The software shall evaluate signal abnormality relative to historical, country-specific, domain-specific, and source-specific baselines, not by absolute raw magnitude alone.

### SwR-049 (neu)
The software shall maintain a governed historical data foundation with a target horizon of at least three years for core sources where available, and shall explicitly record shorter-horizon constraints per source.

### SwR-050 (neu)
The software shall execute daily incremental runs that fetch, normalize, persist, and snapshot new data and shall emit run and snapshot manifests for reproducibility.

### SwR-051 (neu)
The software shall preserve explicit layer separation across raw data, normalized data, features, status/score outputs, and report/export artifacts.


## 3) Empfohlene Reihenfolge zur Umsetzung (seriell)

1. PR-1 (Governance closure):
   - `vmodel/requirements/software_requirements.yaml`: SwR-046..051 ergänzen
   - `vmodel/verification/test_specifications.yaml`: neue TC-SwR-046..051 ergänzen

2. PR-2 (Evidence closure):
   - Neue/ergänzte Unit-/Integration-Tests in `tests/unit/` für die neuen Test-Spec-Claims
   - Traceability-/Closure-Checker laufen lassen

3. PR-3 (Claim closure):
   - Stakeholder-Closure-Analyse erneut erzeugen
   - Erwartung: 19/19 Lücken von `nicht_nachweisbar` -> `umgesetzt`


## 4) Akzeptanzkriterium für diesen Plan

Der Plan gilt als abgeschlossen, wenn:
- alle 19 StR aus dieser Datei über SyR->SwR->Tests auf `closed` nachweisbar sind,
- und `build/analysis/stakeholder_functional_implementation_status.json` keine `nicht_nachweisbar`-Einträge mehr enthält.