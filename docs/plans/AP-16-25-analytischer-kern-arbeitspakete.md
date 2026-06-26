# SIASA Analytischer Kern — Arbeitspakete AP-16..AP-25

Quelle: Externe kritische Wuerdigung des analytischen Kerns (2026-06-24).
Befunde F1–F13 adressieren die fachliche Geschlossenheit der Entscheidungspipeline.
Governance: Schwellenwert-Festlegungen bleiben beim Projekteigner.

---

## Uebersicht

| AP-ID | Titel | Tier | Schliesst | Abhaengig von | Aufwand | Prio |
|-------|-------|------|-----------|---------------|---------|------|
| AP-16 | Skill-Messharness (Ground-Truth-Backtest) | 1 | F7,F8,F9 | — | M | P1 |
| AP-17 | Slow-Layer Streuung/z-Score | 1 | F3 (teil) | — | S | P1 |
| AP-18 | Reale Anomalie-Berechnung (Feature→Anomalie) | 1 | F1 | AP-16, AP-17 | M | P1 |
| AP-19 | Unsicherheit aus echten Quellen | 2 | F3 | AP-17 | M | P2 |
| AP-20 | Echte Abhaengigkeitsdetektion + Zentralitaet | 2 | F4 | AP-17 | L | P2 |
| AP-21 | Info-Epidemiologie mit echten Zeitstempeln | 2 | F5 | AP-20 | M | P2 |
| AP-22 | Fusion in Entscheidung zurueckfuehren + D5 | 2 | F2,F12 | AP-18, AP-20 | L | P2 |
| AP-23 | Provenance-Tiefe & In-Chain-Drift | 3 | F6 | — | M | P3 |
| AP-24 | Schwellen-Governance (Magic Numbers) | 3 | F11 | — | M | P3 |
| AP-25 | Fail-Loud-Policy fuer Analytikstufen | 3 | F10 | — | S | P3 |

---

## Tier 1 — Schluessel (ohne diese bleibt alles Uebrige bedeutungslos)

### AP-16: Skill-Messharness (Ground-Truth-Backtest)

**Ziel:** Instrument zur objektiven Bewertung jeder Modell-Aenderung.
Aus kuratierten Referenzfaellen echte Guete-Kennzahlen bilden.

**Befunde:** F7, F8, F9

**In-Scope:**
- Labeled Episodes mit bekanntem Ausgang + Onset-Datum
- Hit/Miss/False-Alarm-Berechnung, Vorlaufzeit, Brier-Score auf Bayes-Posterior
- Aggregat-Report (readmodels/skill_metrics.json)
- Regressionstest: bewusst verschlechtertes Modell senkt Score messbar
- Kennzahl im GUI-Validation-View sichtbar

**Out-of-Scope:** Aenderung der Scoring-Logik selbst (→ AP-18)

**Trace:** StR-358..381, neuer Algo ALGO-SKILL-01

**Akzeptanz:**
1. Ueber ≥4 Referenzfaelle wird je Kennzahl ein Wert ausgegeben
2. Bewusst verschlechtertes Modell senkt Score messbar (Regressionstest)
3. Kennzahl im GUI-Validation-View sichtbar

**Abhaengig von:** keine
**Aufwand:** M (3–5 PT)
**Risiko:** mittel (Label-Qualitaet der Faelle bestimmt Aussagekraft)

**Status (2026-06-26):** **Erledigt** — ALGO-SKILL-01 in `src/siasa/validation/skill_metrics.py`
(`compute_skill_metrics`: Detektionsrate aus `status_match`, mittlerer Domain-Match, gewichteter
Skill-Score in [0,1], deterministisch). Eingebettet ins Validation-Read-Model
(`read_model["skill_metrics"]`), als `readmodels/skill_metrics.json` (sort_keys) geschrieben und als
**Skill-Score-KPI** im GUI-Validation-View sichtbar. Regressionstest: bewusst verschlechtertes Modell
senkt den Score (Akzeptanz 2). Anker: SwR-039 (Statement). Tests: `tests/unit/test_skill_metrics.py` (6).
**Out-of-Scope → AP-28 (ALGO-SKILL-02):** Fehlalarmrate (braucht AP-27 S0-Negative), No-Skill-Baseline,
Vorlaufzeit, Brier-Score.

---

### AP-17: Slow-Layer um Streuung/z-Score erweitern

**Ziel:** Fehlende Standardabweichung liefern — Grundlage fuer saubere
Anomalie-Definition in σ.

**Befunde:** F3 (teilweise)

**In-Scope:**
- In multi_resolution.py rollierende Std (7d/30d) ergaenzen
- z-Score-Helfer: (value − rolling_mean) / rolling_std
- Unit-Tests fuer Randfaelle (zu wenig Punkte → None)

**Out-of-Scope:** Verdrahtung in den Analyzer (→ AP-18)

**Trace:** SwR-063 (Multi-Resolution), neuer Algo ALGO-ZSCORE-01

**Akzeptanz:**
1. Slow-Layer enthaelt std_7d, std_30d
2. z-Score bei konstanter Reihe = 0, bei Ausreisser > 0
3. Unit-Tests fuer Randfaelle (zu wenig Punkte → None)

**Abhaengig von:** keine
**Aufwand:** S (≤2 PT)
**Risiko:** niedrig

---

### AP-18: Reale Anomalie-Berechnung (Feature → Anomalie)

**Ziel:** Konstanten anomaly_score durch datengetriebene Groesse ersetzen.

**Befunde:** F1, entschaerft F7/F8

**In-Scope:**
- _default_domain_status_analyzer + Replay-Pendant umbauen:
  pro Domain aus Feature-Werten via compute_combined_baseline +
  compute_relative_anomaly einen z-normierten, beschraenkten Anomaliewert bilden
- Aggregation mehrerer Features pro Domain definieren
  (gewichtetes Mittel ueber Feature-Coverage)
- Anomaliewert nach oben beschraenkt (kein unbegrenztes D4)

**Out-of-Scope:** Streuungsschaetzung (→ AP-17 liefert σ)

**Trace:** SwR-021/022 (Domain-Status), neuer Algo ALGO-ANOM-01

**Akzeptanz:**
1. Auf Fixture mit variierendem Input variiert Status nachvollziehbar
2. Skill-Score aus AP-16 ≥ Baseline-Konstante
3. Anomaliewert ist nach oben beschraenkt

**Abhaengig von:** AP-16, AP-17
**Aufwand:** M (3–5 PT)
**Risiko:** mittel

**Status (2026-06-25):** Live-Pfad **erledigt** — ALGO-ANOM-01 in `src/siasa/scoring/anomaly.py`
(latest-Wert je signal_key z-genormt gegen Fenster-Mittel/-Std via `compute_zscore` / ALGO-ZSCORE-01 / AP-17,
coverage-gewichtet aggregiert, gekappt auf `ANOMALY_UPPER_BOUND=1.5`), verdrahtet in
`_default_domain_status_analyzer` (Orchestrator reicht die Domain-Records durch). Owner-Entscheid: z-Score
ueber Fenster-Records (Option A). Replay-Pendant (`_DOMAIN_ANOMALY_SCORES`) bewusst nach **AP-26** verschoben
(dort PIT-Zeitreihen-Umbau) — verhindert vorzeitigen S0-Kollaps der synthetischen Replay-Fixtures (F14/F15/F16).
Anker: SwR-048 (Statement + TC-SwR-048-001 → unit_test). Tests: `tests/unit/test_anomaly.py` (9 gruen).
V1-Grenze: Einzel-Snapshot-Bundles liefern ehrlich ~0; echte Tiefe ab AP-26/AP-30.

---

## Tier 2 — Fortgeschrittene Module real machen

### AP-19: Unsicherheit aus echten Quellen statt Coverage-Proxy

**Ziel:** F3 schliessen — Coverage-Komplement durch echte Unsicherheit ersetzen.

**Befunde:** F3

**In-Scope:**
- Feature-Unsicherheit aus Quell-Uneinigkeit (Varianz ueber beitragende Quellen)
  und Stichprobengroesse ableiten
- Stufen-Rauschen (10/15/5%) in governte Konfig ueberfuehren statt hartkodieren

**Out-of-Scope:** Rueckfuehrung der Unsicherheit in die Entscheidung (→ AP-22)

**Trace:** StR-051..056, neuer Algo ALGO-UNC-01

**Akzeptanz:**
1. Bei einer einzigen Quelle ist Unsicherheit definiert (kein 1−coverage-Artefakt)
2. Mehr widersprechende Quellen → groesseres CI

**Abhaengig von:** AP-17
**Aufwand:** M (3–5 PT)
**Risiko:** mittel

---

### AP-20: Echte Abhaengigkeitsdetektion + Zentralitaet

**Ziel:** F4 schliessen — Ko-Okkurrenz-Graph durch echte Korrelation ersetzen.

**Befunde:** F4

**In-Scope:**
- Kanten aus Lead-Lag-Korrelation der Quell-Zeitreihen statt Ko-Okkurrenz
  (timing_lag_hours endlich nutzen)
- Kopplungs-Schwelle statt reiner Zusammenhangskomponente
- InfluenceScore von Out-Degree auf iterative Zentralitaet
  (PageRank-light, abhaengigkeitsfrei) heben

**Out-of-Scope:** Fusions-Gewichtsaenderung (→ AP-22 nutzt Ergebnis)

**Trace:** StR-029..034, neuer Algo ALGO-DEP-02

**Akzeptanz:**
1. Zwei unkorrelierte Quellen bilden keine Kante
2. Treibende Quelle erhaelt hoehere Zentralitaet als getriebene
3. Kohaesion variiert (nicht konstant 1,0)

**Abhaengig von:** AP-17
**Aufwand:** L (>5 PT)
**Risiko:** mittel-hoch

---

### AP-21: Info-Epidemiologie mit echten Zeitstempeln

**Ziel:** F5 schliessen — Freshness durch echte Erstbeobachtungs-Zeitpunkte ersetzen.

**Befunde:** F5

**In-Scope:**
- Erstbeobachtungs-Zeitpunkt je (Quelle, Signal) durch Normalisierungsschicht
  tragen und als observed_at_hours verwenden
- Amplifikation daempfen wenn verstaerkende Quellen im selben
  Dependency-Cluster liegen (Kopplung an AP-20)

**Out-of-Scope:** Kausalinferenz (bleibt explizit ausgeschlossen)

**Trace:** StR-040..044, neuer Algo ALGO-EPI-02

**Akzeptanz:**
1. Spread-Sequenz folgt echten Zeitstempeln, nicht Freshness
2. Verstaerkung durch gekoppelte Quellen wird gedaempft ausgewiesen

**Abhaengig von:** AP-20
**Aufwand:** M (3–5 PT)
**Risiko:** mittel (haengt an Ingestion-Metadaten)

---

### AP-22: Fusion in die Entscheidung zurueckfuehren + D5 vereinheitlichen

**Ziel:** F2 und F12 schliessen — der teuerste, aber wirkungsvollste Schritt.

**Befunde:** F2, F12

**In-Scope:**
- Multi-Domain-Status (oder zumindest dessen Konfidenz) aus fuse_domain_evidence
  inkl. Widerspruchs-Flags und Quell-Kopplung ableiten
- D5 als orthogonales Widerspruchs-Flag modellieren statt als Status-Stufe,
  sodass der Bayes-Pfad die volle Statusspanne abdecken kann

**Out-of-Scope:** Neue Domains/Features

**Trace:** SwR-023/024 (Multi-Domain-Status), neuer Algo ALGO-FUSE-02

**Akzeptanz:**
1. Injizierter Domain-Widerspruch veraendert Status/Konfidenz nachweisbar
2. Bayes liefert fuer jeden erreichbaren Status eine Schaetzung (kein D5-Loch)
3. Skill-Score aus AP-16 nicht schlechter

**Abhaengig von:** AP-18, AP-20
**Aufwand:** L (>5 PT)
**Risiko:** hoch (aendert Entscheidungslogik — Schwellen-Festlegung beim Projekteigner)

---

## Tier 3 — Governance & Robustheit

### AP-23: Provenance-Tiefe & In-Chain-Drift

**Ziel:** F6 schliessen — Provenance von 5-Stufen-Template auf echte Kette erweitern.

**Befunde:** F6

**In-Scope:**
- Mapping-/Algorithmus-Versionen als Provenance-Node-Metadaten fuehren
- compare_provenance_runs um In-Chain-Diff (Transform/Version) erweitern,
  nicht nur Root-Sources

**Trace:** StR-035..039, neuer Algo ALGO-PROV-02

**Akzeptanz:**
1. Geaenderte Mapping-Version bei gleicher Quelle setzt lineage_changed = True

**Abhaengig von:** keine
**Aufwand:** M (3–5 PT)
**Risiko:** niedrig

---

### AP-24: Schwellen-Governance (Magic Numbers)

**Ziel:** F11 schliessen — alle Magic Numbers in versionierte Methoden-Konfig ziehen.

**Befunde:** F11

**In-Scope:**
- Alle Schwellenwerte in versionierte Methoden-Konfig unter vmodel/method/
  mit IDs ziehen
- Code/Tests referenzieren die IDs
- Die Werte selbst legt der Projekteigner fest — WP liefert nur den Mechanismus

**Trace:** querschnittlich, Algo-Register-Erweiterung

**Akzeptanz:**
1. Keine Schwelle mehr literal im Code
2. Jede Schwelle hat eine ID und einen Test der die Bindung prueft

**Abhaengig von:** laeuft neben Tier 1/2
**Aufwand:** M (3–5 PT)
**Risiko:** niedrig

**Status (2026-06-26): weitgehend erledigt (vorgezogen).** Governte Config `vmodel/project/scoring_thresholds.yaml`
(neben dem bestehenden `freshness_config.yaml`; **Abweichung von „vmodel/method/"** — bewusst, gleiches
Loader-Muster) + Loader `scoring/scoring_thresholds.py` mit Gettern; 7/8 Familien verdrahtet (behavior-preserving),
Bindungstests in `tests/unit/test_scoring_thresholds.py`. Akzeptanz 1+2 erfuellt. Erster literatur-gegruendeter Wert
gesetzt (Bayes-D3-Zentrum 0.65→0.75 = Band-Mittelpunkt, SHELF); restliche Wert-Aenderungen an AP-30/AP-28/Owner-Policy
gebunden (Detail: `HANDOFF.md` §⭐ + `docs/research/parameter-initialisierung.md`). Offen: Multi-Domain-S0–S6-
Aggregation noch dokumentiert (`wired_to_config: false`).

---

### AP-25: Fail-Loud-Policy fuer Analytikstufen

**Ziel:** F10 entschaerfen — stille Degradation sichtbar machen.

**Befunde:** F10

**In-Scope:**
- Stilles except→continue durch explizit protokollierte Degradation ersetzen
- Run-Level-Gate "analytische Vollstaendigkeit" das uebersprungene Stufen
  sichtbar macht (an artifact_status/Readiness anbinden)

**Trace:** Governance/Run-Controls, neuer Algo ALGO-RUNGATE-01

**Akzeptanz:**
1. Erzwungene Ausnahme in einer Stufe erscheint als expliziter
   Degradationseintrag, nicht als leeres Ergebnis

**Abhaengig von:** keine
**Aufwand:** S (≤2 PT)
**Risiko:** niedrig

**Status (2026-06-25):** **Erledigt** — ALGO-RUNGATE-01 in `src/siasa/runs/run_gate.py`
(record_degradation + build_analytical_completeness). Die 7 Analytikstufen (a-g) im Orchestrator fangen
geworfene Exceptions weiterhin ab, schreiben aber jetzt einen expliziten Degradationseintrag
(stage/exception_type/reason), aggregiert zu einem Run-Level-Verdict `analytical_completeness`
(complete/degraded), gespiegelt in `artifact_status["analytical_completeness"]` und in den
Readiness-`artifact_checks` (informativ, NICHT release-blockierend — Severity bleibt Owner-Hoheit).
ImportError-Zweige bleiben legitime Skips. Anker: SwR-044 (Statement). Tests:
`tests/unit/test_run_gate.py` (5) + Orchestrator-Integrationstest (erzwungene Fusion-Exception →
Degradationseintrag, Run bleibt success).

---

## Kritischer Pfad

```
AP-16 (Messharness)
     |
     v
AP-17 (σ/z-Score) ──> AP-18 (reale Anomalie)
                            |
          +-----------------+-----------------+
          v                 v                 v
     AP-19 (Unsich.)   AP-20 (Dependency)  AP-21 (Info-Epi)
                            |
                            v
                      AP-22 (Fusion → Entscheidung, D5)

AP-23/24/25 (Tier 3) laufen unabhaengig nebenher.
```

**Minimaler Wertschnitt (3 WPs):** AP-16 + AP-17 + AP-18.
Danach hat SIASA erstmals ein datengetriebenes Signal UND eine Zahl die sagt ob es taugt.

---

## Befund-Zuordnung

| Befund | Schwere | Beschreibung | Schliessendes AP |
|--------|---------|-------------|------------------|
| F1 | 1 | anomaly_score ist Konstante | AP-18 |
| F2 | 1 | Fortgeschrittene Module speisen Entscheidung nicht | AP-22 |
| F3 | 2 | Unsicherheit = Coverage-Komplement | AP-17 + AP-19 |
| F4 | 2 | Dependency-Graph ist Ko-Okkurrenz | AP-20 |
| F5 | 2 | Info-Epi nutzt Freshness statt Zeitstempel | AP-21 |
| F6 | 2 | Provenance ist festes Template | AP-23 |
| F7 | 3 | Backtest misst Veraenderung, nicht Korrektheit | AP-16 |
| F8 | 3 | Historical-Replay validiert Modell nicht | AP-16 + AP-18 |
| F9 | 3 | Keine aggregierte Guete-Kennzahl | AP-16 |
| F10 | 4 | Stille Degradation | AP-25 |
| F11 | 4 | Ungovernte Magic Numbers | AP-24 |
| F12 | 4 | D-Klassenmenge inkonsistent (D5) | AP-22 |
| F13 | 4 | Code-Smell Backtest (minor) | AP-16 (Nebenbefund) |
