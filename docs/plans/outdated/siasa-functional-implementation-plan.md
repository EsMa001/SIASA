# SIASA Funktionale Implementierungslücken — Umsetzungsplan

> Erstellt: 2026-05-30
> Basis: 417 funktionale Stakeholder-Anforderungen in 39 Kategorien
> Methode: Kategorie-für-Kategorie Bewertung gegen aktuellen Code, Adapter, Features, GUI, Tests

---

## 1. Quantifizierung der funktionalen Gaps

| Status | StR-Anzahl | Anteil | Bedeutung |
| --- | --- | --- | --- |
| Done | 105 | 25% | Materiell umgesetzt, Stakeholder-Erwartung erfüllt |
| Partial | 188 | 45% | Struktur vorhanden, inhaltlich lückenhaft |
| Weak | 66 | 16% | Nur Vorbereitung, kein echtes Produktverhalten |
| Missing | 58 | 14% | Nicht implementiert |
| **Gesamt** | **417** | **100%** | |

**312 von 417 funktionalen StR (75%) haben substantielle Implementierungslücken.**

---

## 2. Gap-Zuordnung zu Implementierungsblöcken

Die 312 offenen funktionalen StR clustern in 8 Implementierungsblöcke:

### Block 1: Domain C/E Feature-Extraktion und Integration (67 StR)
**Betroffene Kategorien:**
- A Grundziel und Scope: 7 StR (StR-001..007)
- R MVP-Domänenumfang: 9 StR (StR-188..196)
- U Einbindung C/E in Multi-Domain-Status: 10 StR (StR-245..254)
- V Domänenstatus D0-D5: 11 StR (StR-255..265) — automatisch mit C/E
- Y Analyse-Funktionsrahmen A-E: 17 StR (StR-311..327)
- Z MVP Feature Set: 13 StR (StR-328..340)

**Was fehlt konkret:**
- `src/siasa/features/domain_c.py` existiert nicht
- `src/siasa/features/domain_e.py` existiert nicht
- Gating in `multi_domain_status.py` (Zeile 23) ist inert ohne C/E-Features
- GUI zeigt keine aktiven/inaktiven Domänen-Indikatoren

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F01 | `domain_c.py`: Feature-Extraktion für physische Aktivität/Social aus GDACS-Daten. Features: `C_event_count`, `C_event_severity_mean`, `C_affected_population`, `C_geographic_spread`. Pattern von `domain_a.py` übernehmen. | Keine | M |
| AP-F02 | `domain_e.py`: Feature-Extraktion für Cyber/Tech/InfoOps aus GDELT Doc (Themenfilter cyber/tech). Features: `E_cyber_mention_volume`, `E_info_ops_tone`, `E_tech_disruption_signals`, `E_source_diversity_cyber`. | Keine | M |
| AP-F03 | C/E-Integration: Orchestrator-Pipeline erweitern, Data-Sufficiency-Gating für C/E (StR-250), `optional_domain_gates` befüllen, GUI-Anzeige aktive/inaktive Domänen (StR-251/252), "nicht bewertbar" vs "unauffällig" (StR-253). | AP-F01, AP-F02 | M |
| AP-F04 | Baseline-Erweiterung auf C/E: `baselines.py` für 5-Domänen-Baselines erweitern, Anomaly Scoring für C/E. | AP-F03 | S |

---

### Block 2: Betrieb, Automatisierung, Datenbank (60 StR)
**Betroffene Kategorien:**
- Betrieb & Automatisierung: 47 StR (StR-474..520) — KOMPLETT FEHLEND
- P Datenbank und tägliche Runs: 13 StR (StR-135..147)

**Was fehlt konkret:**
- Keine Datenbank (weder SQLite noch PostgreSQL)
- Kein Scheduler (kein cron, kein Celery, kein interner Scheduler)
- Kein Monitoring, keine Health-Checks, keine Alerts
- Kein automatisches Recovery bei Fehlern
- Kein Deployment-Konzept
- `build/run_artifacts/latest/` ist leer — kein persistierter Run-Zyklus

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F05 | Persistierter `latest` Run-Zyklus: Standardbefehl, der `build/run_artifacts/latest/` vollständig befüllt. README-Doku für Windows/PyCharm. Verifikationsskript. | AP-F03 (damit C/E im Run) | S |
| AP-F06 | SQLite Run-History: `src/siasa/data/storage.py` mit Run-Metadaten, Domain-Scores pro Land, Source-Fetch-Ergebnisse. Zeitreihen-Abfragen. | AP-F05 | L |
| AP-F07 | Scheduler: Tägliche automatische Runs, `latest/` Rotation, Fehler-Erkennung, Basic Alerting (Logfile + optional E-Mail/Webhook). | AP-F06 | L |
| AP-F08 | Health-Monitoring: Liveness-Check, Source-Availability-Check, Staleness-Monitor, Status-Endpoint oder Status-File. | AP-F07 | M |

---

### Block 3: Historischer Datenhorizont und Validierung (43 StR)
**Betroffene Kategorien:**
- P Historischer Datenhorizont und Data Sufficiency: 14 StR (StR-148..161)
- Validierung & Backtesting: 24 StR (StR-358..381)
- L Validierung und Backtesting: 5 StR (StR-062..066)

**Was fehlt konkret:**
- Keine historische Datenspeicherung (Zeitreihen)
- Keine konfigurierbare historische Horizonte
- Kein automatisiertes Regressions-Backtesting
- Kein Live-Retrospektiv-Validation gegen echte Zeitreihen

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F09 | Historischer Data Layer: Zeitreihen-Storage in SQLite, konfigurierbarer Horizont pro Domäne/Quelle. | AP-F06 | M |
| AP-F10 | Automatisiertes Backtesting: Pipeline, die historische Daten gegen aktuelle Scoring-Logik laufen lässt, Ergebnisse vergleicht, Regressions-Report generiert. | AP-F09 | L |
| AP-F11 | Konfigurierbare Freshness-Windows: Per Domäne/Quelle einstellbar statt hardcoded 168h. | AP-F09 | S |

---

### Block 4: Quellen-Erweiterung (26 StR)
**Betroffene Kategorien:**
- B Quellenklassen: 5 StR (StR-008..012)
- S Datenquellenverwaltung und ACLED: 10 StR (StR-205..214)
- S Festgelegte Datenquellen: 11 StR (StR-215..225)

**Was fehlt konkret:**
- Nur 4 von vielen spezifizierten Quellen implementiert
- ACLED: Zugang eingeschränkt (API-Key erforderlich)
- ReliefWeb: ab Nov 2025 appname-Registrierung nötig (HTTP 403)
- Social Media, akademische Quellen, Cyber-Feeds fehlen

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F12 | ACLED-Adapter oder Alternative (z.B. UCDP für Konfliktdaten). | Zugangsklärung | M |
| AP-F13 | Zusätzlicher Domain-C-Adapter (z.B. UNHCR, IOM für Flucht/Migration). | Keine | M |
| AP-F14 | Zusätzlicher Domain-E-Adapter (z.B. Shodan, GreyNoise für Cyber-Indikatoren oder Mediabias für Info-Ops). | Zugangsklärung | M |
| AP-F15 | ReliefWeb appname-Registrierung und Adapter-Aktivierung. | Registrierung | S |

---

### Block 5: GUI Interaktivität und Visualisierung (36 StR)
**Betroffene Kategorien:**
- N GUI Weltkarte und Score-Modi: 10 StR (StR-101..110)
- N GUI Nutzungsmodi: 8 StR (StR-081..088)
- O Kartenbaseline und Vergleichsskala: 7 StR (StR-111..117)
- O Multi-Window-Baselines: 11 StR (StR-118..128)

**Was fehlt konkret:**
- SVG-Karte ist schematisch, keine echte Geo-Projektion
- Kein Zoom/Pan, kein Score-Mode-Switching auf der Karte
- Keine Multi-Window-Parallelansichten
- Kein Temporal-Slider für historischen Vergleich
- Kein dynamischer Moduswechsel (Rollen)

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F16 | Interaktive Weltkarte: SVG-Map erweitern um Zoom/Pan, Hover-Tooltips, Click-to-Drill, Score-Overlay-Wechsel. | AP-F05 (befüllte Daten) | L |
| AP-F17 | Enhanced Trend Charts: Zoom, Pan, Multi-Series Overlay, Time-Range-Selektion. | AP-F09 (hist. Daten) | M |
| AP-F18 | Multi-Window Baseline Comparison: Parallelansicht verschiedener Zeitfenster. | AP-F09, AP-F17 | M |
| AP-F19 | Dynamischer Rollenwechsel: Ohne Neu-Generierung zwischen Rollen wechseln. | Keine | M |

---

### Block 6: Regelbasierte Bewertung und Reports (26 StR)
**Betroffene Kategorien:**
- W Regelbasierte Bewertung und Annotationen: 16 StR (StR-266..281)
- X Automatische und manuelle Reports: 10 StR (StR-301..310)

**Was fehlt konkret:**
- Keine regelbasierte automatische Bewertung (nur manuelle Annotationen)
- Keine automatische Report-Generierung, kein Scheduling

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F20 | Regelbasiertes Bewertungsmodul: Konfigurierbarer Regelkatalog (YAML), automatische Bewertung bei Run, Ergebnisse in Annotationen. | AP-F03 (5-Domänen) | L |
| AP-F21 | Automatische Report-Generierung: Täglicher Snapshot-Report, Anomalie-Report, konfigurierbare Report-Templates. | AP-F07 (Scheduler) | M |

---

### Block 7: Advanced Analytics (22 StR)
**Betroffene Kategorien:**
- F Informationsabhängigkeiten und Quellencluster: 6 StR (StR-029..034)
- I Evidenzfusion und Cross-Domain-Kontrastierung: 6 StR (StR-045..050)
- H Informations-Epidemiologie: 5 StR (StR-040..044)
- G Source Lineage: 5 StR (StR-035..039)

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F22 | Cross-Domain Evidence Fusion: Explizite Widerspruchserkennung A vs D, Evidenz-Gewichtung, Fusion-Logik. | AP-F03 (5-Domänen) | L |
| AP-F23 | Dependency Graph & Cluster: Quellenabhängigkeiten als Graph, Cluster-Detektion, Einfluss-Quantifizierung. | AP-F09 | L |
| AP-F24 | Provenance Graph: Vollständiger Herkunftsnachweis mit Cross-Run-Vergleich. | AP-F09 | M |
| AP-F25 | Informations-Epidemiologie: Spread-Path-Modelling, Amplification Detection. | AP-F09, AP-F14 | L |

---

### Block 8: Probabilistik und Unsicherheit (11 StR)
**Betroffene Kategorien:**
- K Probabilistische Zustandsmodellierung: 5 StR (StR-057..061)
- J Unsicherheit und Explainability: 6 StR (StR-051..056)

**Arbeitspakete:**
| AP | Scope | Voraussetzung | Komplexität |
| --- | --- | --- | --- |
| AP-F26 | Probabilistisches Scoring: Bayesianische D-Status-Klassifikation, Übergangswahrscheinlichkeiten, Konfidenzintervalle als Alternative/Ergänzung zum Threshold-Modell. | AP-F09 (hist. Daten für Training) | L |
| AP-F27 | Quantitative Unsicherheitspropagation: Unsicherheit von Source → Feature → Domain → Multi-Domain durchreichen mit expliziten Konfidenzintervallen. | AP-F26 | L |

---

## 3. Priorisierte serielle Umsetzungsreihenfolge

### Phase 1: Inhaltliche Vollständigkeit (67 StR)
> Ziel: Alle 5 Domänen liefern Features und fließen in Multi-Domain-Status

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 1 | AP-F01: Domain C Feature Extraction | 17 | M | 17 |
| 2 | AP-F02: Domain E Feature Extraction | 13 | M | 30 |
| 3 | AP-F03: C/E Multi-Domain Integration | 20 | M | 50 |
| 4 | AP-F04: Baseline-Erweiterung C/E | 5 | S | 55 |
| 5 | AP-F05: Persistierter Latest Run | 12 | S | 67 |

### Phase 2: Datenfundament (60 StR)
> Ziel: Persistierte Runs, historische Daten, automatischer Betrieb

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 6 | AP-F06: SQLite Run-History | 14 | L | 81 |
| 7 | AP-F07: Scheduler | 47 | L | 128 |
| 8 | AP-F08: Health-Monitoring | inkl. | M | 128 |
| 9 | AP-F09: Historischer Data Layer | 14 | M | 142 |
| 10 | AP-F11: Konfig. Freshness-Windows | 6 | S | 148 |

### Phase 3: Quellen-Erweiterung (26 StR)
> Ziel: Mindestens 6-8 Quellen, breitere Quellenklassen

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 11 | AP-F12: ACLED/UCDP Adapter | 10 | M | 158 |
| 12 | AP-F13: Domain C Add. Source | 5 | M | 163 |
| 13 | AP-F14: Domain E Add. Source | 5 | M | 168 |
| 14 | AP-F15: ReliefWeb Aktivierung | 6 | S | 174 |

### Phase 4: Validierung und Backtesting (43 StR)
> Ziel: Automatisiertes Backtesting gegen historische Zeitreihen

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 15 | AP-F10: Automatisiertes Backtesting | 29 | L | 203 |
| 16 | AP-F20: Regelbasierte Bewertung | 16 | L | 219 |
| 17 | AP-F21: Automatische Reports | 10 | M | 229 |

### Phase 5: GUI Interaktivität (36 StR)
> Ziel: Interaktive Karte, Charts, Multi-Window

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 18 | AP-F16: Interaktive Weltkarte | 10 | L | 239 |
| 19 | AP-F17: Enhanced Trend Charts | 7 | M | 246 |
| 20 | AP-F18: Multi-Window Comparison | 11 | M | 257 |
| 21 | AP-F19: Dynamischer Rollenwechsel | 8 | M | 265 |

### Phase 6: Advanced Analytics (33 StR)
> Ziel: Cross-Domain Fusion, Epidemiologie, Probabilistik

| Schritt | AP | StR-Impact | Komplexität | Kumulativ geschlossen |
| --- | --- | --- | --- | --- |
| 22 | AP-F22: Cross-Domain Fusion | 6 | L | 271 |
| 23 | AP-F23: Dependency Graph | 6 | L | 277 |
| 24 | AP-F24: Provenance Graph | 5 | M | 282 |
| 25 | AP-F25: Epidemiologie | 5 | L | 287 |
| 26 | AP-F26: Probabilistisches Scoring | 5 | L | 292 |
| 27 | AP-F27: Unsicherheitspropagation | 6 | L | 298 |

---

## 4. Zusammenfassung

| Phase | StR geschlossen | Kumulativ | Anteil von 312 |
| --- | --- | --- | --- |
| Phase 1: Inhaltliche Vollständigkeit | 67 | 67 | 21% |
| Phase 2: Datenfundament | 81 | 148 | 47% |
| Phase 3: Quellen-Erweiterung | 26 | 174 | 56% |
| Phase 4: Validierung + Regelwerk | 55 | 229 | 73% |
| Phase 5: GUI Interaktivität | 36 | 265 | 85% |
| Phase 6: Advanced Analytics | 33 | 298 | 96% |

Die restlichen ~14 StR werden durch Seiteneffekte der obigen Pakete mit abgedeckt (z.B. Server-Side Auth als optionale Ergänzung zu AP-F19).

**Erster AP: AP-F01 Domain C Feature Extraction**

---

## 5. Detailbewertung pro funktionale Kategorie

| Kategorie | StR | IDs | Status | Was existiert | Was fehlt | Umsetzung durch |
| --- | --- | --- | --- | --- | --- | --- |
| A Grundziel und Scope | 7 | StR-001..007 | Partial | Lageverständnis für A/B/D | C/E fehlt → nur 3/5 Domänen | AP-F01/F02/F03 |
| AA Nutzerrollen | 10 | StR-341..350 | Partial | Rollen in GUI | Kein Server-Auth | AP-F19 + post-MVP |
| B Quellenklassen | 5 | StR-008..012 | Partial | 4 Adapter | Social/Cyber/Academic fehlt | AP-F12..F15 |
| Betrieb & Automatisierung | 47 | StR-474..520 | Missing | Manueller Run | Alles fehlt | AP-F06/F07/F08 |
| C Quellenkatalog | 5 | StR-013..017 | Done | Catalog vorhanden | — | — |
| D Country Profile | 6 | StR-018..023 | Done | Profile komplett | — | — |
| E Baselines/Anomalien | 5 | StR-024..028 | Partial | Baselines A/B/D | C/E fehlt | AP-F04 |
| F Info-Abhängigkeiten | 6 | StR-029..034 | Weak | Coupling Candidates | Kein Graph | AP-F23 |
| G Source Lineage | 5 | StR-035..039 | Partial | Lineage-Records | Kein Provenance-Graph | AP-F24 |
| H Info-Epidemiologie | 5 | StR-040..044 | Weak | First-Observed | Kein Spread-Path | AP-F25 |
| I Evidenzfusion | 6 | StR-045..050 | Missing | Nur Aggregation | Keine Fusion/Kontrast | AP-F22 |
| J Unsicherheit | 6 | StR-051..056 | Partial | Text-Indikatoren | Keine Quantifizierung | AP-F27 |
| K Probabilistik | 5 | StR-057..061 | Missing | Threshold-basiert | Keine Probabilistik | AP-F26 |
| L Validierung | 5 | StR-062..066 | Partial | Archival Replay | Kein auto. Backtesting | AP-F10 |
| N GUI Grundanf. | 10 | StR-071..080 | Done | HTML GUI komplett | — | — |
| N GUI Modi | 8 | StR-081..088 | Partial | Rollen-Modi | Kein dyn. Wechsel | AP-F19 |
| N GUI Seiten | 12 | StR-089..100 | Done | Alle Seiten da | — | — |
| N GUI Weltkarte | 10 | StR-101..110 | Partial | SVG-Map | Kein Zoom/Pan/Overlay | AP-F16 |
| O Aktualitätsfenster | 6 | StR-129..134 | Partial | Freshness Overlays | Nicht konfigurierbar | AP-F11 |
| O Kartenbaseline | 7 | StR-111..117 | Partial | Text-Vergleich | Kein Visual Diff | AP-F17 |
| O Multi-Window | 11 | StR-118..128 | Weak | Single-Window | Keine Parallel-Views | AP-F18 |
| P DB + Runs | 13 | StR-135..147 | Weak | Orchestrator | Keine DB/Scheduler | AP-F06/F07 |
| P Hist. Horizont | 14 | StR-148..161 | Partial | Sufficiency Checks | Keine Zeitreihen | AP-F09 |
| Q Länderauswahl | 17 | StR-162..178 | Done | Pilot Sets | — | — |
| Q Priorisierung | 9 | StR-179..187 | Done | Priority Model | — | — |
| Q Länderset v0.1 | 8 | StR-197..204 | Done | Konfiguration da | — | — |
| R Domänenumfang | 9 | StR-188..196 | Partial | A/B/D | C/E fehlt | AP-F01/F02 |
| S ACLED | 10 | StR-205..214 | Weak | Framework | ACLED fehlt | AP-F12 |
| S Festgelegte Quellen | 11 | StR-215..225 | Weak | 4 Adapter | Viele fehlen | AP-F13..F15 |
| T Anti-Fusion | 10 | StR-226..235 | Done | Guardrails da | — | — |
| U Multi-Domain | 9 | StR-236..244 | Done | S0-S6 | — | — |
| U C/E-Integration | 10 | StR-245..254 | Weak | Gating-Code inert | C/E Features fehlen | AP-F01/F02/F03 |
| V D0-D5 | 11 | StR-255..265 | Partial | A/B/D komplett | C/E fehlt | AP-F01/F02 |
| Val. & Backtesting | 24 | StR-358..381 | Partial | 23-Case Replay | Kein auto. Backtesting | AP-F10 |
| W Regelb. Bewertung | 16 | StR-266..281 | Partial | Annotationen | Keine Regeln | AP-F20 |
| W Annot. ohne Review | 9 | StR-282..290 | Done | Umgesetzt | — | — |
| X Report/Export | 10 | StR-291..300 | Done | Views da | — | — |
| X Auto-Reports | 10 | StR-301..310 | Partial | Manuell | Keine Automatik | AP-F21 |
| Y Funktionsrahmen | 17 | StR-311..327 | Partial | A/B/D Features | C/E fehlt | AP-F01/F02 |
| Z MVP Features | 13 | StR-328..340 | Partial | A/B/D | C/E fehlt | AP-F01/F02 |
