# SIASA – Zentrales Planungsdokument (Master-Plan)

> Dies ist das **einzige steuernde Planungsdokument** von SIASA. Es ersetzt alle früheren
> Planungsgenerationen (Master-Steering, Roadmap, Executive-View, Audit, Gap-Pläne, Level-Pläne).
> Diese sind nach `docs/plans/outdated/` archiviert und dienen nur noch als historische Referenz.
>
> **Evidenz-/Nachweis-Begleiter:** `docs/plans/siasa-capability-fulfillment-matrix.md`
> (detailliertes Status-/Test-/Probe-Ledger; wird von Produktionscode gelesen und bleibt aktiv).

Stand: 2026-06-25
Status: Aktiv – einzige Planungsquelle für die Vorwärtssteuerung

> **Namespace-Hinweis (AP-IDs):** Maßgeblich für `AP-NN` ist allein dieses L0-Dokument. Der
> L1-Evidenz-Begleiter (`siasa-capability-fulfillment-matrix.md`) führt intern eine eigene,
> historische Zeilenkennung `AP-15..AP-27` für die abgeschlossene **Operability-/Release-Steering-Serie**.
> Diese Ledger-Labels sind **nicht** identisch mit den hier gesteuerten Arbeitspaketen
> (z. B. ist Master-Plan-`AP-27` = „Ground-Truth-Redesign", Ledger-`AP-27` = „Operability-Cluster").
> Bei Doku-Pflege die Serien klar benennen, nie über die nackte Nummer referenzieren.

---

## 0. Wie dieses Dokument zu benutzen ist

Dieses Dokument leistet genau vier Dinge:

1. Es zeigt **alle großen Arbeitspakete und Teilarbeitspakete** in einer einheitlichen Hierarchie.
2. Es zeigt pro Paket den **Status** (erledigt / offen / blockiert / zurückgestellt).
3. Es hält eine **steuerbare Prioritätsreihenfolge** für die offenen Pakete (Abschnitt 3) – das ist die Stelle,
   an der die Projektleitung die Reihenfolge selbst festlegt.
4. Es verweist für jeden Punkt auf die **historische Herkunft** (Legacy-IDs) und die **Evidenz**.

Dokument-Hierarchie (Ebenen der Planungsdokumente):

| Ebene | Dokument | Rolle |
| --- | --- | --- |
| L0 – Planung/Steuerung | `docs/plans/siasa-master-plan.md` (dieses Dokument) | Einzige Planungsquelle: Arbeitspakete, Priorität, Status |
| L1 – Evidenz/Nachweis | `docs/plans/siasa-capability-fulfillment-matrix.md` | Detail-Ledger mit Test-/Probe-Evidenz (read-only Begleiter) |
| L2 – Historie | `docs/plans/outdated/**` | Frühere Planungsgenerationen, nur Referenz/Traceability |
| L3 – Governed Source-of-Truth | `vmodel/project/*.yaml` | Verbindliche Requirements-/WP-/Prioritäts-Artefakte |

Nicht-Regel: Wähle das nächste Arbeitspaket niemals aus den `Immediate Next Recommendation`-Abschnitten der
Dokumente unter `outdated/`. Maßgeblich ist allein Abschnitt 3 dieses Dokuments.

---

## 1. Einheitliche Namens- und Hierarchie-Konvention

Bisher existierten parallel mindestens zehn ID-Schemata (`G1–G5`, `N1-WP-001..071`, `VAL-WP-001..026`,
`WP-001..008`, `WP-001/002/003` unter G4, `P0–P4`, `Step A/B/C`, `A-/B-/C-`, `AP-F01..F27`, `AP-N01`,
`AP-19..27`). Das war die eigentliche Ursache der „Planungsgenerationen-Überlappung". Ab sofort gilt **ein**
Schema.

### 1.1 Hierarchie-Ebenen

| Ebene | Bezeichnung | ID-Schema | Beispiel |
| --- | --- | --- | --- |
| Ebene 0 | Programm | `SIASA` | SIASA |
| Ebene 1 | **Großes Arbeitspaket** (Epic) | `AP-NN` | `AP-05` |
| Ebene 2 | **Teilarbeitspaket** | `AP-NN.M` | `AP-05.3` |
| Ebene 3 | Schritt / Task (nur wo nötig) | `AP-NN.M.K` | `AP-05.3.1` |

Regeln:
- **AP-IDs sind stabile Identität.** Eine einmal vergebene Nummer wird nicht neu vergeben und ändert sich nicht,
  auch nicht bei Umpriorisierung. So bleibt Traceability erhalten.
- Neue große Arbeitspakete bekommen die nächste freie `AP-NN`, neue Teilpakete die nächste freie `AP-NN.M`.
- Das alte `WP-001..WP-008`-Schema bleibt **nur** als governed Fundament-IDs in
  `vmodel/project/implementation_workpackages.yaml` bestehen (siehe AP-01) – im Plan werden sie nicht erneut
  als `WP-xxx` geführt, um die frühere Kollision (`WP-001` = Fundament vs. `WP-001` = G4-Subpaket) aufzulösen.

### 1.2 Einheitliche Status-Werte

| Status | Bedeutung |
| --- | --- |
| `Erledigt` | Implementiert, getestet, evidenzbelegt, abgeschlossen |
| `In Arbeit` | Aktiver Default-Track; mehrere Teilpakete erledigt, weitere offen |
| `Offen` | Geplant, noch nicht begonnen |
| `Blockiert` | Repo-seitig fertig; wartet auf externen Auslöser (z. B. Credentials) |
| `Zurückgestellt` | Bewusst später / nur bei expliziter Umpriorisierung |

### 1.3 Einheitliche Prioritäts-/Klassen-Werte

- **Rang (Prio):** `P1, P2, P3, …` – die **steuerbare** Bearbeitungsreihenfolge (Abschnitt 3). Nur offene/aktive
  Pakete haben einen Rang.
- **Klasse:** governed MVP-Klassifikation aus `vmodel/project/prioritization.yaml`
  (`MVP-Must`, `MVP-Should`, `MVP-Could`, `Post-MVP`, `Out-of-Scope`).

---

## 2. Status-Dashboard (alle großen Arbeitspakete)

| AP-ID | Großes Arbeitspaket | Status | Rang | Klasse | Herkunft (Legacy) |
| --- | --- | --- | --- | --- | --- |
| AP-01 | Fundament & Kernpipeline | Erledigt | – | MVP-Must | `WP-001..008` (vmodel), `AP-F01..F27` |
| AP-02 | Runtime-Breite: governed MVP-Slice (30 Länder) | Erledigt | – | MVP-Must | `G1`, Roadmap `P0/P2`, `Step A` |
| AP-03 | Operationale Evidenz-Spur | Erledigt | – | MVP-Should | `G3`, `N1-WP-003..010` |
| AP-04 | Release-Lifecycle: Freigabe → Distribution | Erledigt | – | MVP-Should | `G4 WP-001/002/003`, `Step C` (`C-1..C-12`) |
| AP-05 | Validierungs-Realismus & Analyst-Handoff | Erledigt | – | MVP-Should | `VAL-WP-001..026`, `N1-WP-011..071`, `Step B` |
| AP-06 | Externe credential-gated Quellen-Aktivierung | Blockiert | **P1** | MVP-Should | `G2`, `P0-WP-001`, ReliefWeb/UCDP |
| AP-07 | Quellen-Robustheit & Degradations-Wahrheit | Erledigt | – | MVP-Should | `G1`-Rest, `SRC-GDELT-DOC/-E` |
| AP-08 | Breiten-Ausbau über mvp-complete hinaus | Erledigt | – | MVP-Could | Roadmap §5, Source-Origin/Epidemiologie |
| AP-09 | Server-gestützte Multi-User-Governance | Zurückgestellt | **P2** | Post-MVP | `G5` |
| AP-10 | Terminologie-Glossar & Begriffs-Normalisierung | Erledigt | – | MVP-Should | neu (kein Legacy) |
| AP-11 | Free-API-Quellen-Verbreiterung (D/E/C/A) | Erledigt | – | MVP-Could | 3 Adapter live (Frankfurter/Voidly/HDX-INFORM), 4 extern blockiert, Katalog+Glossar aktuell |
| AP-12 | UX-Transparenz & Informationstiefe | Erledigt | – | MVP-Should | neu (User-Request: Quellen-Steckbriefe, parametrierbare Zeitachsen, Methodik-Transparenz, Glossar-Seite) |
| AP-13 | ML-Training Data Lake | Erledigt | – | MVP-Should | 15/15 TAPs: Parquet-Archiv, DuckDB Query-Layer, Feature-Engineering Pipeline, PyTorch/HuggingFace, DVC, Retention, Health, CLI |
| AP-14 | Kostenfreie API-Quellen-Erweiterung | Erledigt | **P1** | MVP-Should | 4 Adapter (Wikipedia, ECB, Eurostat, NVD CVE) + Registry + Feature-Katalog; SwR-072..075, 91 Tests |
| AP-15 | Erweiterte kostenfreie API-Integration | Erledigt | – | MVP-Should | 8 Adapter, 53 Signale, Registry + Runtime verdrahtet |
| AP-16 | Skill-Messharness (Ground-Truth-Backtest) | Offen | **P1** | Analytik-Kern | F7/F8/F9: Validierung misst keine Modellgüte |
| AP-17 | Slow-Layer Streuung/z-Score | Erledigt | – | Analytik-Kern | F3 (teil): std_7d/30d + z-Score (`compute_zscore`, ALGO-ZSCORE-01) in `multi_resolution.py`; SwR-063 erw.; 16 Tests grün |
| AP-18 | Reale Anomalie-Berechnung (Feature→Anomalie) | Offen | **P1** | Analytik-Kern | F1: anomaly_score ist Konstante |
| AP-19 | Unsicherheit aus echten Quellen | Offen | P4 | Analytik-Kern | F3 — Phase 4 (nach Validierung bisektierbar) |
| AP-20 | Echte Abhängigkeitsdetektion + Zentralität | Offen | P4 | Analytik-Kern | F4 — Phase 4 |
| AP-21 | Info-Epidemiologie mit echten Zeitstempeln | Offen | P4 | Analytik-Kern | F5 — Phase 4 |
| AP-22 | Fusion in Entscheidung zurückführen + D5 | Offen | P4 | Analytik-Kern | F2/F12 — Phase 4 |
| AP-23 | Provenance-Tiefe & In-Chain-Drift | Offen | P3 | Governance | F6: Provenance ist festes Template |
| AP-24 | Schwellen-Governance (Magic Numbers) | Offen | P4 | Governance | F11 — Phase 4 |
| AP-25 | Fail-Loud-Policy für Analytikstufen | Offen | **P1** | Governance | F10: stille Degradation (Phase-0-Gate) |
| AP-26 | Status-Zeitreihe im Fenster-Replay | Offen | **P1** | Validierung (Phase 0) | F16: Replay liefert Punktstatus statt Zeitreihe |
| AP-27 | Ground-Truth-Redesign mit Negativfällen | Offen | **P1** | Validierung (Phase 1a) | F15: keine S0-Negative, kein Onset, zirkuläre Labels |
| AP-28 | Skill-Metrik: Fehlalarmrate + No-Skill-Baseline | Offen | **P1** | Validierung (Phase 1b) | F9 real: Fehlalarm/Vorlauf/Brier messbar |
| AP-29 | Event-Set-Definition (klein, ausgewogen) | Offen | **P2** | Validierung (Phase 2a) | F14 (Vorber.): fokussiertes Positiv/Kontroll-Set |
| AP-30 | Historischer Backfill GDELT/GDACS/WB + PIT | Offen | **P2** | Daten (Phase 2b) | F14: synthetische Fixtures durch Realdaten ersetzen |
| AP-31 | Provenance: real-captured vs fixture | Offen | **P2** | Daten/Governance (Phase 2c) | F14: falsche „provider-derived"-Behauptung korrigieren |
| AP-32 | End-to-End-Validierung + Skill-Report | Offen | **P3** | Validierung (Phase 3) | F7/F8 real: „gegen echte Events geprüft" belegen |

Gesamtbild: Das Fundament und alle repo-seitig steuerbaren Gap-Familien (`G1`, `G2`, `G3`, `G4`) sind
**materiell geschlossen** (Capability-Matrix: `17/17 Done`, `100.0%`). AP-05 (Validierungs-Realismus),
AP-07 (Quellen-Robustheit), AP-08 (Breiten-Ausbau auf 88 Länder), AP-10 (Terminologie-Glossar),
AP-11 (Free-API-Quellen-Verbreiterung: 3 neue Adapter für Domain D/E/C) und AP-12 (UX-Transparenz)
sind erledigt. **AP-13 (ML-Training Data Lake)** ist **erledigt** (15/15 TAPs, SwR-055..071): Parquet-Archiv,
DuckDB-Query-Engine, Feature-Engineering (Daily-Alignment, Multi-Resolution, PIT-Join, Training-Builder),
ML-Integration (PyTorch Dataset, HuggingFace Export, Encoding), Operationalisierung (Retention-Hook,
Health-Monitor, CLI Archive-Manager). **AP-14 (Kostenfreie API-Quellen-Erweiterung)** ist abgeschlossen: 4 neue Adapter (Wikipedia Pageviews Domain A, ECB Data + Eurostat Domain D, NVD CVE Domain E), Signal-Registry + Feature-Katalog erweitert.
ECB Data (Domain D), Eurostat (Domain D) und NVD CVE (Domain E) als verifizierte kostenfreie Quellen.
Die verbleibende blockierte Arbeit ist externe Quellen-Aktivierung (AP-06) und – zurückgestellt – Multi-User (AP-09).

---

## 3. Prioritäts-Backlog (STEUERBAR)

> **Dies ist die Stelle, an der die Reihenfolge gesteuert wird.** Die Bearbeitungsreihenfolge ergibt sich aus
> dem `Rang`. Empfohlener Default ist unten gesetzt – frei überschreibbar.

> **Strategische Klammer (2026-06-25): „Modell gegen echte Events prüfen".** Die offenen Analytik-Pakete
> sind in **fünf Phasen mit Gates** geordnet (Detail: `docs/plans/AP-26-32-validierung-gegen-echte-events.md`).
> Der bestimmende Befund: Der längste Hebel ist **Daten + Labels**, nicht Code. Erst Korrektheit (Phase 0),
> dann das Messinstrument (Phase 1), dann echte Daten (Phase 2), dann die Validierung (Phase 3); die
> Genauigkeits-Hebel (AP-19/20/21/22/24) sind bewusst **Phase 4** — sie werden erst nach Phase 3 gegen den
> Skill-Score bisektierbar und daher nach hinten gereiht.

| Rang | Phase | AP-ID | Großes Arbeitspaket | Status | Klasse | Auslöser / Bedingung |
| --- | --- | --- | --- | --- | --- | --- |
| ~~P1~~ | 0 | AP-17 | Slow-Layer Streuung/z-Score | **Erledigt** | Analytik-Kern | F3: σ/z-Score geliefert (std_7d/30d, `compute_zscore`); SwR-063 erweitert |
| **P1** | 0 | AP-18 | Reale Anomalie-Berechnung (Feature→Anomalie) | Offen | Analytik-Kern | F1: anomaly_score ist Konstante; braucht AP-17 |
| **P1** | 0 | AP-25 | Fail-Loud-Policy für Analytikstufen | Offen | Governance | F10: stille Degradation untergräbt jede spätere Zahl |
| **P1** | 0 | AP-26 | Status-Zeitreihe im Fenster-Replay | Offen | Validierung | F16: Punktstatus → tägliche Trajektorie; braucht AP-18 |
| **P1** | 1a | AP-27 | Ground-Truth-Redesign mit Negativfällen | Offen | Validierung | F15: S0-Negative, Onset, Trajektorie, Holdout-Split (längster Pol Labels) |
| **P1** | 1b | AP-16 | Skill-Messharness (Ground-Truth-Backtest) | Offen | Analytik-Kern | F7/F8/F9: Gerüst der Skill-Messung |
| **P1** | 1b | AP-28 | Skill-Metrik: Fehlalarmrate + No-Skill-Baseline | Offen | Validierung | F9 real; braucht AP-16, AP-26, AP-27 |
| **P2** | 2a | AP-29 | Event-Set-Definition (klein, ausgewogen) | Offen | Validierung | F14 (Vorber.); braucht AP-27 |
| **P2** | 2b | AP-30 | Historischer Backfill GDELT/GDACS/WB + PIT | Offen | Daten | F14: **größter Block**, hohes Risiko; braucht AP-29, AP-13 |
| **P2** | 2c | AP-31 | Provenance: real-captured vs fixture | Offen | Daten/Governance | F14: ehrliche Kennzeichnung; braucht AP-30 |
| **P3** | 3 | AP-32 | End-to-End-Validierung + Skill-Report | Offen | Validierung | F7/F8 real; braucht AP-26, AP-28, AP-30, AP-31 |
| **P3** | – | AP-23 | Provenance-Tiefe & In-Chain-Drift | Offen | Governance | F6: läuft unabhängig nebenher |
| **P4** | 4 | AP-19 | Unsicherheit aus echten Quellen | Offen | Analytik-Kern | F3: erst nach Skill-Score bisektierbar |
| **P4** | 4 | AP-20 | Echte Abhängigkeitsdetektion + Zentralität | Offen | Analytik-Kern | F4: Phase 4 |
| **P4** | 4 | AP-21 | Info-Epidemiologie mit echten Zeitstempeln | Offen | Analytik-Kern | F5: Phase 4 |
| **P4** | 4 | AP-22 | Fusion in Entscheidung zurückführen + D5 | Offen | Analytik-Kern | F2/F12: Phase 4 |
| **P4** | 4 | AP-24 | Schwellen-Governance (Magic Numbers) | Offen | Governance | F11: Phase 4 (Cuts tunen ohne Code) |
| **P2** | – | AP-06 | Externe Quellen-Aktivierung (G2) | Blockiert | MVP-Should | **springt auf aktiv**, sobald gültige ReliefWeb/UCDP-Credentials vorliegen |
| **P3** | – | AP-09 | Multi-User-Governance (G5) | Zurückgestellt | Post-MVP | nur wenn Operating-Model Multi-User explizit fordert |
| ~~–~~ | – | AP-15 | Erweiterte kostenfreie API-Integration | **Erledigt** | MVP-Should | 8 Adapter, 53 Signale, Registry + Runtime verdrahtet |
| ~~–~~ | – | AP-14 | Kostenfreie API-Quellen-Erweiterung | Erledigt | MVP-Should | 4 Adapter, Registry + Katalog |
| ~~–~~ | – | AP-13 | ML-Training Data Lake | **Erledigt** | MVP-Should | 15/15 TAPs (SwR-055..071) |

**Minimaler ehrlicher Durchstich:** AP-17 + AP-18 + AP-25 + AP-26 + AP-27 (1 Positiv + 1 Kontrolle) +
AP-16 + AP-28 + AP-29/30/31 (genau diese 2 Fälle) + AP-32. Erst damit ist „gegen echte Events geprüft"
keine Übertreibung.

### So steuerst du die Reihenfolge

1. **AP-IDs nicht ändern** – sie sind stabile Identität (Traceability). Gesteuert wird nur die Spalte `Rang`.
2. Zum Umpriorisieren die `Rang`-Werte ändern bzw. die Tabellenzeilen umsortieren. Die Tabelle in diesem
   Abschnitt ist die maßgebliche Reihenfolge.
3. Die Spalte „Auslöser / Bedingung" sagt, wann ein blockiertes/zurückgestelltes Paket automatisch nach oben
   rückt (z. B. AP-06 bei verfügbaren Credentials).
4. Abgeschlossene Pakete (AP-01..AP-05) haben keinen Rang und stehen nur in Abschnitt 2 und 4.

### Begründung der Default-Reihenfolge

- **AP-13 zuerst (P1):** Alle operativen Daten gehen nach 168h verloren. Ohne permanentes Archiv ist
  kein ML-Training möglich. Jeder Tag ohne Archivierung ist unwiederbringlicher Datenverlust.
- **AP-06 (P2, bedingt):** Repo-seitig fertig; der einzige offene Hebel ist extern (Credentials). Sobald
  Credentials da sind, ist dies das wertvollste gebündelte Paket.
- **AP-09 (P3, zurückgestellt):** Großer Architektursprung; nur bei explizitem Bedarf am Ziel-Betriebsmodell.

---

## 4. Große Arbeitspakete & Teilarbeitspakete (Detail)

Definition of Done (global, gemäß `AGENTS.md`): Implementierung + Traceability + Tests + grüne Checks +
Doku-Update + Konsistenzprüfung der Kontextartefakte. Serielle Ausführung: ein gebündeltes Teilpaket →
gezielte Tests → Full-Suite → Master-Plan/Matrix aktualisieren → Commit/Push.

### 4.A Abgeschlossenes Fundament (AP-01 … AP-04)

#### AP-01 — Fundament & Kernpipeline · Status: Erledigt · Klasse: MVP-Must
Herkunft: governed `WP-001..WP-008` (`vmodel/project/implementation_workpackages.yaml`); frühere
`AP-F01..F27`-Funktionsplanung (ausgeführt).

| TAP | Inhalt | Status | Governed-ID |
| --- | --- | --- | --- |
| AP-01.1 | Katalog- & Konfigurationsbasis | Erledigt | WP-001 |
| AP-01.2 | Source-Adapter-Framework & Failure-Isolation | Erledigt | WP-002 |
| AP-01.3 | Raw- & Normalized-Daten-Layer | Erledigt | WP-003 |
| AP-01.4 | Feature-Berechnung A/B/D | Erledigt | WP-004 |
| AP-01.5 | Baseline-, Anomalie- & Status-Engines (D0–D5, S0–S6) | Erledigt | WP-005 |
| AP-01.6 | Snapshot- & Traceability-Kern | Erledigt | WP-006 |
| AP-01.7 | Reporting- & Read-Model-Basis | Erledigt | WP-007 |
| AP-01.8 | Annotation/Validation/Governance/Reprocessing | Erledigt | WP-008 |

#### AP-02 — Runtime-Breite: governed MVP-Slice · Status: Erledigt · Klasse: MVP-Must
Herkunft: `G1`; Roadmap-Phasen `P0/P2`, `Step A`. Repo-seitig geschlossen.

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-02.1 | Governed Live-Runtime + Pilot-Sets (core/extended/focus/mvp-complete) | Erledigt | CLI-Help + Runtime-Unit-Tests |
| AP-02.2 | Volle 30-Länder `mvp-complete`-Schließung | Erledigt | `RUN-OP-LATEST-G1-CLOSE-001` (`30/30`, `breadth_full_slice_updated`, Gate `pass`) |
| AP-02.3 | Readiness-Honesty + Domain-Governance (A/D bei Low-Signal-B) | Erledigt | `RUN-LIVE-REP-READINESS-TRUTH-001` |

#### AP-03 — Operationale Evidenz-Spur · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G3`; `N1-WP-003..010`. Eine normalisierte Operator-/PL-Evidenzspur mit Frische-/Autoritäts-Status.

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-03.1 | `operational_evidence_lane.json` + `runs.html`-Panel | Erledigt | `N1-WP-003` |
| AP-03.2 | Latest-/Archiv-Navigation, Evidenz-Links, Triage-Tags | Erledigt | `N1-WP-005..010` |
| AP-03.3 | Frische-/Autoritäts-Status (fresh/stale/override-governed) | Erledigt | `RUN-OP-LATEST-G3-CLOSE-001` |

#### AP-04 — Release-Lifecycle: Freigabe → Distribution · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G4 WP-001/002/003`; `Step C` Produktisierung (`C-1..C-12`).

| TAP | Inhalt | Status | Evidenz |
| --- | --- | --- | --- |
| AP-04.1 | Lifecycle-Record + Artefakt + GUI-Panel (`release_package.html`) | Erledigt | G4 WP-001 |
| AP-04.2 | Transition-CLI (`approve/defer/reject/distribute`) + Evidence-Lane in `runs.html` | Erledigt | G4 WP-002 (`scripts/lifecycle_transition.py`) |
| AP-04.3 | Packet-Truth-Alignment: Lifecycle-Ergebnis propagiert in Sign-off/Send-Flächen | Erledigt | G4 WP-003 |
| AP-04.4 | Decision-Packet Seed + Send-Readiness-Checkliste | Erledigt | `C-11`, `C-12` |

### 4.B Offene / laufende / zurückgestellte Arbeitspakete (AP-05 … AP-09)

#### AP-05 — Validierungs-Realismus & Analyst-Handoff · Status: Erledigt · Klasse: MVP-Should
Kanonischer Track-Name (Legacy/EN): **validation realism depth / analyst handoff refinement**.
Herkunft: `VAL-WP-001..026`, `N1-WP-011..071`, Roadmap `Step B` (`B-1..B-6`).
Ziel: Non-perfekten Replay-Realismus vertiefen und den deterministischen Analyst-Handoff
(Export/Aktion/Decision-Scaffolding) stärken – ohne bereits geschlossene Runtime-/Governance-Familien
wieder zu öffnen.

| TAP | Inhalt | Status | Herkunft / Evidenz |
| --- | --- | --- | --- |
| AP-05.1 | Challenge-Case-Portfolio (Weak-Evidence/Mismatch/Domain-Gap) | Erledigt (laufend erweiterbar) | `VAL-WP-001/007/013` (32 Cases) |
| AP-05.2 | Replay-Attention-Watchlist: Sortierung, Presets, Scoping, Copy/CSV | Erledigt | `VAL-WP-005/006/008/009/012` |
| AP-05.3 | Kontext-tragende Deep-Links Briefing → Coverage/Validation/Annotation | Erledigt | `VAL-WP-014/015/016/017` |
| AP-05.4 | Annotation-Decision-Scaffolding (Typ + Decision-Posture deterministisch) | Erledigt | `N1-WP-069/070/071` |
| AP-05.5 | Reviewer-Decision-Templates in Sign-off/Routing/Send-Readiness | Erledigt | `N1-WP-071` |
| AP-05.6 | Decision-Log-/Approval-Condition-Auto-Seeds | Erledigt | Decision-log auto-seeds in release package |

DoD nächstes Slice: ein gebündeltes Validierungs-/Handoff-Slice; gezielte RED/GREEN-Tests; Full-Suite grün;
ein reales Probe-Bundle; Master-Plan + Capability-Matrix aktualisiert; Commit/Push.

#### AP-06 — Externe credential-gated Quellen-Aktivierung · Status: Blockiert (extern) · Rang: P2 · Klasse: MVP-Should
Herkunft: `G2`, `P0-WP-001` (Source-Access-Assessment, archiviert unter `outdated/`), `P0-WP-002c`.
Repo-seitig geschlossen: Adapter + graceful Degradation + Aktivierungs-/Evidenz-Wahrheit
(`activated_with_live_evidence`, `configured_but_not_evidenced`, `credentialed_but_live_fetch_failed`,
`external_blocker_present`). Offener Hebel ist rein extern (Credentials/Registrierung).

| TAP | Inhalt | Status | Bedingung |
| --- | --- | --- | --- |
| AP-06.1 | ReliefWeb live aktivieren (Domain-C-Breite) | Blockiert | benötigt `RELIEFWEB_APPNAME` (approved appname) |
| AP-06.2 | UCDP-GED live aktivieren | Blockiert | benötigt `UCDP_API_TOKEN` im Operator-Lane |
| AP-06.3 | Entscheidung über weitere fehlende Quellklassen (implementieren vs. bewusst aufschieben) | Offen | PL-Entscheid |

Auslöser-Regel: Sobald gültige Credentials vorliegen → AP-06 auf P1 ziehen, einen governed Aktivierungslauf
fahren und explizite Source-Success-Evidenz erfassen.

#### AP-07 — Quellen-Robustheit & Degradations-Wahrheit · Status: Erledigt · Klasse: MVP-Should
Herkunft: `G1`-Rest (das einzige verbliebene Delta der Runtime-Breite). Es geht **nicht** um fehlende
governed Breite, sondern um Provider-Degradations-Wahrheit und deren Release-/Readiness-Konsequenz.

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-07.1 | `SRC-GDELT-DOC` / `SRC-GDELT-DOC-E` Degradationswahrheit + Release-Konsequenz härten | Erledigt | Per-Country-Fault-Isolation, Malformed-Article-Skip, Degraded-Countries-Diagnostik; `69ca9fc` |
| AP-07.2 | Retry-/Partial-Success-Profile bei neuem Failure-Mode nachschärfen | Erledigt | Shared `retry_utils.py`, `is_retryable_error()` (429/5xx/Timeout/Connection), konfigurierbarer Timeout; `69ca9fc` |

#### AP-08 — Breiten-Ausbau über mvp-complete hinaus · Status: Erledigt · Klasse: MVP-Could
Herkunft: Roadmap §5 (Control/Reference-Restslices), Source-Origin/Epidemiologie-Groundwork (`P4`).

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-08.1 | Nächster Länder-Cluster / restliche control-reference-Slices | Erledigt | 58 neue Länder (88 total): LatAm, SEA, Afrika, Nahost, Europa, Zentralasien, Ostasien; 5 regionale Pilot-Sets; `20d0e93` |
| AP-08.2 | Source-Origin-Inferenz / Informations-Epidemiologie ausbauen | Offen | Groundwork in Traceability-View vorhanden; bewusst später |

#### AP-09 — Server-gestützte Multi-User-Governance · Status: Zurückgestellt · Rang: P3 · Klasse: Post-MVP
Herkunft: `G5`. Heutiger lokaler/statischer governed-Bundle-UX ist materiell stark; Multi-User nur bei
explizitem Bedarf am Ziel-Betriebsmodell.

| TAP | Inhalt | Status | Bedingung |
| --- | --- | --- | --- |
| AP-09.1 | Architektur-Entscheidungs-Slice (Operating-Model bestätigen, Scope authn/authz + Persistenz) | Zurückgestellt | nur bei Multi-User-Bedarf |
| AP-09.2 | Server-seitige Identität / authn / authz | Zurückgestellt | nach AP-09.1 |
| AP-09.3 | Persistierter Review-/Annotation-Workflow (Multi-User) | Zurückgestellt | nach AP-09.1 |

#### AP-10 — Terminologie-Glossar & Begriffs-Normalisierung · Status: Erledigt · Klasse: MVP-Should
Herkunft: neu (kein Legacy). Quer-Abhängigkeit zu allen Planungs- und Code-Artefakten.
Ziel: Ein maschinenlesbares Glossar mit aussagekräftigen, möglichst deutschsprachigen Bezeichnungen
mit klarer Definition, englischem Äquivalent und Zuordnung zu Code-Identifiern. Bestehende Dokumente
(Masterplan, Capability-Matrix, Code-Docstrings) werden auf konsistente Terminologie normalisiert.

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-10.1 | Glossar-Datei erstellen (`docs/glossary.yaml`) – Struktur + erste Extraktion aus Masterplan/Matrix | Erledigt | 55 Terme in 9 Kategorien, YAML-validiert |
| AP-10.2 | Begriffe aus bestehenden Planungsdokumenten extrahieren und ins Glossar aufnehmen | Erledigt | Masterplan, Capability-Matrix, AGENTS.md ausgewertet |
| AP-10.3 | Terminologie in Masterplan normalisieren (einheitliche Begriffe gemäß Glossar) | Erledigt | Masterplan bereits konsistent; keine Korrekturen nötig |
| AP-10.4 | Terminologie in Capability-Matrix normalisieren | Erledigt | Matrix bewusst englisch (wird von Code gelesen); konsistent |
| AP-10.5 | Code-Docstrings und Kommentare auf Glossar-Begriffe prüfen und ggf. ergänzen | Erledigt | 67 Code-Identifier in Glossar gemappt |

#### AP-11 — Free-API-Quellen-Verbreiterung (D/E/C/A) · Status: Erledigt · Klasse: MVP-Could
Herkunft: Analyse des `public-apis/public-apis`-Repos (544 APIs, 51 Kategorien), abgeglichen gegen
SIASA-Domain-Coverage-Lücken und bestehenden Quellkatalog (`vmodel/project/data_sources.yaml`).
Ziel: Schrittweise Verbreiterung der Domain-Coverage durch freie, authfreie oder apiKey-basierte
APIs — ohne die externen Credential-Blocker von AP-06. Jeder Adapter ist eigenständig wertvoll.

Priorisierung der TAPs nach Domain-Lückengröße:
- **Domain D** (Wirtschaft): größte Lücke — nur 2 World-Bank-Indikatoren
- **Domain E** (Cyber/InfoOps): nur globale CISA-KEV, kein Länderbezug
- **Domain C** (Humanitär): dünn, kein Sanctions-/Safety-Signal
- **Domain A** (Narrative): nur GDELT, keine Diversifikation

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-11.1 | `SRC-STATISTICS-WORLD` Adapter: Statistics of the World API (440+ Indikatoren, 218 Länder, IMF+WB) | Blockiert | Domain D; API liefert leere Daten (v1+v2 `data:[]`); erst nutzbar wenn API tatsächlich Daten serviert |
| AP-11.2 | `SRC-FRANKFURTER` Adapter: ECB-Wechselkurse (Frankfurter API) | Erledigt | Domain D; free, no auth, no rate limit; `api.frankfurter.dev`; 14 Tests |
| AP-11.3 | `SRC-VOIDLY` Adapter: Internet-Zensur & ISP-Blocking (130 Länder) | Erledigt | Domain E; demo-key `hydra_demo_key`; `api.voidly.ai/hydra/v1/scores`; 12 Tests |
| AP-11.4 | `SRC-OPENSANCTIONS` Adapter: Sanktionen, PEP, Kriminalität | Blockiert | Domain C; API erfordert API-Key (kein freier Zugang); Registrierung nötig |
| AP-11.5 | `SRC-WARNELY` Adapter: Composite Travel-Safety-Scores (180 Länder) | Blockiert | Domain C; API/Domain nicht mehr erreichbar (404/DNS-Fehler) |
| AP-11.6 | `SRC-HDX-INFORM` Adapter: INFORM Risk Index via HDX | Erledigt | Domain C; free, no auth; CSV-Download data.humdata.org; 10 Kernindikatoren; 11 Tests |
| AP-11.7 | `SRC-NEWSAPI` oder `SRC-GNEWS` Adapter: Nachrichten-Diversifikation | Blockiert | Domain A; alle getesteten APIs erfordern Registrierung/API-Key (GNews, Currents, MediaStack, NewsAPI) |
| AP-11.8 | Quellkatalog (`data_sources.yaml`) + Glossar aktualisieren | Erledigt | Katalog: 3 neue Core-Einträge; Glossar: 3 neue Terme (58 total, 10 Kategorien); `f33e46c` |
| AP-11.9 | Runtime-Integration: neue Adapter in `live_runtime.py` verdrahten + Live-Fixes | Erledigt | Import + Adapter-Wiring + Normalisierungs-Mappings für SRC-FRANKFURTER/VOIDLY/HDX-INFORM; User-Agent-Header-Fix (403-Blocker) + HDX CSV-Format auf Trends umgestellt; Live-Probe verifiziert (alle 3 Adapter liefern echte Daten); 83 Tests grün; `edeedd9`, `12cd8c7` |

#### AP-12 — UX-Transparenz & Informationstiefe · Status: Erledigt · Klasse: MVP-Should
Herkunft: User-Request (2026-06-22). Ziel: Die GUI wird von einem kompakten Dashboard zu einem
vollständig transparenten Analyse-Werkzeug erweitert. Nutzer sollen jede Quelle einzeln inspizieren,
Zeitverläufe frei parametrieren und jederzeit nachvollziehen können, welche Daten mit welchen
Verfahren ausgewertet und kombiniert werden.

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-12.1 | Quellen-Katalog-Seite (`sources.html`): Steckbrief pro Quelle (Name, API, Domain, Indikatoren, Freshness, Status, Normalisierung, Beispiel-Rohdaten) | Erledigt | 11 Adapter-Karten, Filter/Suche, Domain-Übersicht; 7 Tests; `fa932e7` |
| AP-12.2 | Parametrierbare Zeitachse: echtes Date-Range (Von/Bis), Chart-Rerendering statt Opacity, Datum-Labels auf X-Achse | Erledigt | Date-Range-Picker (Von/Bis), data-date-Attribute, JS-Filterung; Preset-Buttons bleiben; 3 Tests; `812f6e9` |
| AP-12.3 | Methodologie-/Pipeline-Transparenz-Seite (`methodology.html`): Datenfluss Rohdaten→Norm→Feature→Scoring→Anomalie→Status→Governance | Erledigt | 10-Schritt-Pipeline, D0-D5/S0-S6 Tabellen, Algorithmen/Schwellwerte; 6 Tests; `a873331` |
| AP-12.4 | Glossar- & Projektbeschreibung (`about.html`): Projektbeschreibung, durchsuchbares Glossar (58 Terme), V-Model-Erklärung, Capability-Übersicht | Erledigt | Architektur-Diagramm, Domain-Tabelle, V-Model, interaktives Glossar; 7 Tests; `41d9fcc` |
| AP-12.5 | Einzelquellen-Detailansicht in Coverage/Country-Profile: aufklappbarer Bereich pro Quelle mit Rohdaten-Snippet, Normalisierung, Scoring-Beitrag | Erledigt | Klickbare Zeilen mit aufklappbarem Detail-Panel (Provider, API, Auth, Cadence, Normalisierung, Indikatoren); 2 Tests; `acee482` |
| AP-12.6 | Nav-Integration & Cross-Links: neue Seiten in Nav, Deep-Links Sources↔Coverage↔Methodology, Glossar-Tooltips | Erledigt | Transparency-Footer auf Overview+Coverage, About→Methodology Link, alle 3 Seiten in Nav; 4 Tests; `5dde58d` |

#### AP-13 — ML-Training Data Lake · Status: Erledigt · Klasse: MVP-Should
Herkunft: User-Request (2026-06-23). Ziel: Permanente, ML-optimierte Datenhaltung aller SIASA-Domänen.
Aktuell gehen alle operativen Daten nach 168h (7 Tage) verloren. AP-13 schafft ein Parquet-basiertes
Langzeitarchiv mit DuckDB-Query-Layer, Multi-Resolution Feature-Engineering, und direkter
PyTorch/HuggingFace-Integration. Versionierung via DVC. Detailplan: `docs/plans/AP-13-ml-training-data-lake.md`.

Technologie-Entscheidungen:
- **Dual-Storage:** SQLite bleibt (Operational State), Parquet NEU (permanentes Archiv + ML)
- **Query-Engine:** DuckDB (embedded, kein Server, Zero-Copy Arrow → PyTorch)
- **Dateiformat:** Apache Parquet (Hive-partitioniert nach source/year/month)
- **Versionierung:** DVC (Git-Integration, Pipeline-DAGs)
- **Speicher-Projektion:** ~3 GB/Jahr komprimiert, ~30 GB in 10 Jahren

Phase 1 — Archiv-Infrastruktur:

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-13.1 | Parquet-Schreiber: `archive.py` + pyarrow Dependency, Hook in Run-Pipeline | Erledigt | 7 Tests; ArchiveWriter mit Hive-Partitioning (source/year/month), Dual-Timestamp, Append-Semantik |
| AP-13.2 | Country-Registry + Signal-Registry als Parquet/YAML Stammdaten | Erledigt | 11 Tests; 88 Laender, 20 Signale, Validierungsfunktionen, KNOWN_ACTIVE_SIGNAL_KEYS |
| AP-13.3 | Dual-Timestamp-Schema: event_time + ingestion_time + period_start/end + granularity | Erledigt | 9 Tests; NormalizedRecord + Archive Schema + Normalization Service erweitert; SwR-059 + TC + Traces |
| AP-13.4 | DuckDB Query-Layer über Parquet-Archiv | Erledigt | 14 Tests; ArchiveQueryEngine mit DuckDB 1.5 — Filter, Aggregation, Arrow-Output; SwR-060 + TC + Traces |
| AP-13.5 | DVC-Setup: Datenversionierung + Pipeline-Definition | Erledigt | 7 Tests; dvc init, 4-Stage Pipeline (ingest/archive/features/training), data/.gitignore; SwR-061 + TC + Traces |

Phase 2 — Feature-Engineering:

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-13.6 | Daily Alignment Pipeline: Aggregation + Forward-Fill | Erledigt | 7 Tests; DailyAligner mit SUM/MEAN/MAX/LAST, Gap-Detection; SwR-062 + TC + Traces |
| AP-13.7 | Multi-Resolution Feature-Builder (Fast/Slow/Structural Layer) | Erledigt | 7 Tests; Fast/Slow (7d/30d rolling mean)/Structural Layer; SwR-063 + TC + Traces |
| AP-13.8 | Point-in-Time Join Engine (Anti-Look-Ahead-Bias) | Erledigt | 10 Tests; PointInTimeJoiner mit Anti-Leakage, Staleness-Limits, NaN-Marking; SwR-064 + TC + Traces |
| AP-13.9 | Training-Set Builder: versionierte train/val/test Splits | Erledigt | 8 Tests; TrainingSetBuilder mit temporalem Split, Pivotierung, Z-Score-Normalisierung; SwR-065 + TC + Traces |

Phase 3 — ML-Integration:

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-13.10 | PyTorch SIASATimeSeriesDataset + DataLoader | Erledigt | 9 Tests; SIASATimeSeriesDataset mit Window/Horizon/Filter/Collate; SwR-066 + TC + Traces |
| AP-13.11 | HuggingFace Datasets Export + Dataset Card | Erledigt | 7 Tests; HFExporter mit Parquet→HF, Card-Generator, Split-Export; SwR-067 + TC + Traces |
| AP-13.12 | Encoding-Utilities (Country Embeddings, Signal Pivotierung) | Erledigt | 12 Tests; DomainOneHot, QualityOrdinal, CountryEmbedding, SignalPivot; SwR-068 + TC + Traces |

Phase 4 — Operationalisierung:

| TAP | Inhalt | Status | Hinweis |
| --- | --- | --- | --- |
| AP-13.13 | Retention-Policy Migration: Pre-Cleanup Archive-Hook | Erledigt | 6 Tests; RetentionArchiveHook mit No-Data-Loss-Garantie, Failure-Safety; SwR-069 + TC + Traces |
| AP-13.14 | Archive Health Dashboard (`archive.html` in GUI) | Erledigt | 8 Tests; ArchiveHealthMonitor mit Gap-Detection, Source/Domain/Year-Counts; SwR-070 + TC + Traces |
| AP-13.15 | CLI für Archive-Management (stats, compact, validate, export) | Erledigt | 7 Tests; ArchiveManager mit Stats/Validate/Compact/Export-Training; SwR-071 + TC + Traces |

### 4.C Analytik-Kern — befund-getrieben (AP-16 … AP-25)

Herkunft: Externe kritische Würdigung des analytischen Kerns (2026-06-24), Befunde **F1–F13**.
Voll-Detail (Tier, In-/Out-of-Scope, Akzeptanz, kritischer Pfad): `docs/plans/AP-16-25-analytischer-kern-arbeitspakete.md`.
Governance: Schwellenwert-Festlegungen bleiben beim Projekteigner.

| AP-ID | Großes Arbeitspaket | Tier | Schließt | Phase-Einordnung | Status |
| --- | --- | --- | --- | --- | --- |
| AP-16 | Skill-Messharness (Ground-Truth-Backtest) | 1 | F7/F8/F9 | Phase 1b (Gerüst für AP-28) | Offen |
| AP-17 | Slow-Layer Streuung/z-Score | 1 | F3 (teil) | Phase 0 | **Erledigt** |
| AP-18 | Reale Anomalie-Berechnung (Feature→Anomalie) | 1 | F1 | Phase 0 | Offen |
| AP-19 | Unsicherheit aus echten Quellen | 2 | F3 | Phase 4 | Offen |
| AP-20 | Echte Abhängigkeitsdetektion + Zentralität | 2 | F4 | Phase 4 | Offen |
| AP-21 | Info-Epidemiologie mit echten Zeitstempeln | 2 | F5 | Phase 4 | Offen |
| AP-22 | Fusion in Entscheidung zurückführen + D5 | 2 | F2/F12 | Phase 4 | Offen |
| AP-23 | Provenance-Tiefe & In-Chain-Drift | 3 | F6 | unabhängig | Offen |
| AP-24 | Schwellen-Governance (Magic Numbers) | 3 | F11 | Phase 4 | Offen |
| AP-25 | Fail-Loud-Policy für Analytikstufen | 3 | F10 | Phase 0 (Gate) | Offen |

### 4.D Validierung gegen echte Events (AP-26 … AP-32)

Herkunft: Phasenplan „Modell gegen echte Events prüfen" (2026-06-25). Voll-Detail (In-/Out-of-Scope,
Akzeptanz, kritischer Pfad): `docs/plans/AP-26-32-validierung-gegen-echte-events.md`. Code-fundiert
ausgearbeitet und adversarial konsistenzgeprüft (Trace-Blöcke disjunkt, DAG azyklisch).
Drei neue Befunde ergänzen F1–F13: **F14** (synthetische Eventdaten), **F15** (degenerierte Labels),
**F16** (Punktstatus statt Zeitreihe).

> **Trace-Allokation (disjunkt, fortlaufend ab Bestand SwR-083 / StR-677 / TC-SwR-NNN-NNN):**
> AP-26 = SwR-084..087, StR-678..681, ALGO-REPLAY-TS-01 · AP-27 = SwR-088..090, StR-682..684 ·
> AP-28 = SwR-091..094, StR-685..688, ALGO-SKILL-02 · AP-29 = StR-689..692 · AP-30 = SwR-095..101,
> StR-693..696, ALGO-BACKFILL-01 · AP-31 = SwR-102, StR-697 · AP-32 = SwR-103..106, StR-698..701.
> Jede ID wird nur **einmal** über alle APs vergeben; pinning auf einzelne TAPs bei Implementierung.

#### AP-26 — Status-Zeitreihe im Fenster-Replay · Status: Offen · Klasse: Validierung
Phase 0 · Schließt: **F16** · Abhängig von: AP-17, AP-18, AP-25 · Aufwand: M · Risiko: mittel · Trace: SwR-084..087 / StR-678..681 / ALGO-REPLAY-TS-01.
Ziel: Der Replay-Pfad erzeugt aus `NormalizedRecords` eine **deterministische tägliche Status-Zeitreihe**
`(date, status, confidence)` über das Fall-Fenster statt eines Einzel-Labels (heute kollabiert
`_derive_country_replay_status`, `historical_replay.py:141`, alles zu einem `replayed_status`).
**Merge-Hotspot:** ändert dieselben Funktionen additiv wie AP-31 — Felder unabhängig hinzufügen.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-26.1 | Tages-Fensterung + PIT-Schnitt (`_replay_window_dates`, `_records_as_of` in `historical_replay.py`), kein Look-ahead | Offen | SwR-084 / TC-SwR-084-001 |
| AP-26.2 | Tägliche Status-Ableitung `derive_country_replay_status_timeseries` (ALGO-REPLAY-TS-01) + Fail-loud-Degradationseintrag | Offen | SwR-085 / ALGO-REPLAY-TS-01 |
| AP-26.3 | Zeitreihe additiv in `build_historical_replay_reviews` einhängen (fixture + governter Pfad) | Offen | SwR-086 |
| AP-26.4 | Deterministisches Artefakt `readmodels/status_timeseries_<case>.json` (sort_keys) + Trace/Doku | Offen | SwR-087 / StR-678..681 |

#### AP-27 — Ground-Truth-Redesign mit Negativfällen · Status: Offen · Klasse: Validierung
Phase 1a · Schließt: **F15** · Abhängig von: — (parallel zu Phase 0) · Aufwand: M · Risiko: mittel · Trace: SwR-088..090 / StR-682..684.
**Hoheit Projekteigner:** welche Länder/Fenster S0-Negative sind, konkrete Onset-Daten, Trajektorien-Schwellen,
Tuning/Holdout-Zuteilung. WP liefert nur Mechanik + einen exemplarischen Negativfall.
Ziel: Label-Set in `validation_reference_cases.yaml` (heute 35 Fälle: 30×S3, kein S0) so reparieren, dass
Fehlalarme und Vorlaufzeit messbar werden.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-27.1 | `ValidationCase` + Loader um `onset_date`/`expected_trajectory`/`dataset_split`/`case_polarity` (`cases.py`), rückwärtskompatibel | Offen | SwR-088 |
| AP-27.2 | ≥1 echten **S0-Negativfall** + Onset/Trajektorie/Split in `validation_reference_cases.yaml` kuratieren | Offen | SwR-089 |
| AP-27.3 | Validator `validate_reference_case_library`: Onset-im-Fenster, disjunkter Split, **Anti-Zirkularität** (`historical_observed_status` ≠ mechanisch `expected_status`) | Offen | SwR-090 |
| AP-27.4 | Traceability (StR-682..684, SwR-088..090) + Doku (Masterplan/Matrix/Glossar) | Offen | StR-682..684 |

#### AP-28 — Skill-Metrik: Fehlalarmrate + No-Skill-Baseline · Status: Offen · Klasse: Validierung
Phase 1b · Schließt: **F9 (real)**, entschärft F7/F8 · Abhängig von: **AP-16**, AP-26, AP-27 · Aufwand: M · Risiko: mittel · Trace: SwR-091..094 / StR-685..688 / ALGO-SKILL-02.
**AP-16-Abgrenzung (Bottleneck):** AP-16 ist „Offen"/unimplementiert. AP-28 baut das Skill-Modul
(`src/siasa/validation/skill_metrics.py`) auf ALGO-SKILL-01 (AP-16) auf und erweitert es zu **ALGO-SKILL-02**
(Baseline + False-Alarm). AP-16 ist hartes Vorpaket — vor AP-28 schließen.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-28.1 | Skill-Klassifikation Hit/Miss/False-Alarm (`skill_metrics.py`); Fehlalarmrate nur auf S0-Negativen definiert | Offen | SwR-091 / ALGO-SKILL-02 |
| AP-28.2 | Vorlaufzeit aus AP-26-Zeitreihe + Brier-Score auf Bayes-Posterior (`probabilistic.py`) | Offen | SwR-092 |
| AP-28.3 | No-Skill-Baseline „immer S3" + `beats_baseline` (auf Fehlalarm UND Vorlauf) + Regressionstest | Offen | SwR-093 |
| AP-28.4 | Artefakt `readmodels/skill_metrics.json` (deterministisch) + GUI-KPI (`_render_validation_kpi_grid`) | Offen | SwR-094 / StR-685..688 |

#### AP-29 — Event-Set-Definition (klein, ausgewogen) · Status: Offen · Klasse: Validierung
Phase 2a · Schließt: **F14 (Vorber.)** · Abhängig von: AP-27 · Aufwand: S · Risiko: niedrig · Trace: StR-689..692.
**Hoheit Projekteigner:** welche konkreten Eskalationen/Kontrollen das Set bilden.
Ziel: 3 Eskalationen + 3 gematchte ruhige Kontrollen, jeweils mit Fenster/Onset/Trajektorie und Quell-Zuordnung,
verlinkt auf bestehende `case_id`.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-29.1 | Selektions-/Paarungsspezifikation (3+3) — **review-basiert, kein RED/GREEN** | Offen | StR-689 |
| AP-29.2 | Artefakt `vmodel/verification/validation_event_set.yaml` (matched pairs, `assigned_sources` ⊆ reference_sources) | Offen | StR-690 |
| AP-29.3 | Konsistenztest gegen AP-27-Labelbibliothek (Re-use `load_validation_case_library`) | Offen | StR-691 / TC-StR-691-001 |
| AP-29.4 | Trace (StR-689..692) + Doku (Masterplan/Matrix) | Offen | StR-692 |

#### AP-30 — Historischer Backfill GDELT/GDACS/World Bank + PIT · Status: Offen · Klasse: Daten
Phase 2b · Schließt: **F14** · Abhängig von: AP-29, **AP-13** (DailyAligner/PIT/ArchiveWriter) · Aufwand: **XL** · Risiko: **hoch** · Trace: SwR-095..101 / StR-693..696 / ALGO-BACKFILL-01.
**Hoheit Projekteigner:** Fallauswahl (aus AP-29), Daten-Lizenz/Quellzitierung, API-Zugänge.
Ziel: die 8-Record-Fixtures durch real erfasste, look-ahead-freie, auf Tagesauflösung alignierte Daten ersetzen.
Die vier Adapter sind heute **live-only** (kein historisches Datumsfenster) — das ist die Kernlücke.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-30.1 | Adapter um historisches Datumsfenster erweitern (GDELT DOC `startdatetime/enddatetime`, GDELT Events datierte Exports, GDACS Archiv, World Bank `date`-Range); **Live-Pfad unverändert** | Offen | SwR-095..098 |
| AP-30.2 | Orchestrator `scripts/build_historical_backfill.py`: ziehen→`normalize_records`→`ArchiveWriter`→`DailyAligner` (ALGO-BACKFILL-01); **≥100 Records/Fall** | Offen | SwR-099 / ALGO-BACKFILL-01 |
| AP-30.3 | PIT-Replay ohne Look-ahead (verschobener Stichtag; nicht-NaN-Feldzahl steigt monoton mit `query_date`) | Offen | SwR-100 |
| AP-30.4 | Reale Bundles + Manifest-Governance für ≥1 Positiv- + ≥1 Kontrollfall (`_validate_archival_replay_bundle` grün, ≥100 Records) | Offen | SwR-101 / StR-693..696 |

#### AP-31 — Provenance: real-captured vs fixture · Status: Offen · Klasse: Daten/Governance
Phase 2c · Schließt: **F14** · Abhängig von: AP-30 · Aufwand: M · Risiko: niedrig · Trace: SwR-102 / StR-697.
Ziel: die heute pauschal falsche „Provider-derived"-Behauptung in allen 35 Manifest-Einträgen korrigieren und
ein validiertes Flag `data_origin` (`real-captured`|`fixture`) durch die Pipeline bis GUI/Report durchreichen.
**Merge-Hotspot:** ändert dieselben Funktionen additiv wie AP-26.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-31.1 | Manifest-Flag `data_origin` einführen, Loader **fail-loud** bei fehlend/ungültig | Offen | SwR-102 / TC-SwR-102-001 |
| AP-31.2 | `provenance_notes` der Fixtures korrigieren (keine „provider-derived"-Behauptung mehr) | Offen | TC-SwR-102-002 |
| AP-31.3 | `data_origin` durch Pipeline → Read-Model + `data_origin_counts` (Origin-Mix) | Offen | TC-SwR-102-003 |
| AP-31.4 | GUI: Origin-Spalte + Origin-Mix (HTML-Assert: Header „Origin", colspan 12) | Offen | TC-SwR-102-004 |
| AP-31.5 | Trace (SwR-102, StR-697) + Doku (Masterplan/Matrix) | Offen | StR-697 |

#### AP-32 — End-to-End-Validierung + Skill-Report · Status: Offen · Klasse: Validierung
Phase 3 · Schließt: **F7/F8 (real)** · Abhängig von: AP-26, AP-28, AP-30, AP-31 (AP-16/AP-27 transitiv) · Aufwand: M · Risiko: niedrig · Trace: SwR-103..106 / StR-698..701.
Ziel: das korrigierte Modell über die realen Fenster mit PIT-Features laufen lassen und die Güte ehrlich
beziffern — Skill-Metriken vs. No-Skill-Baseline, Fehlalarmrate auf Kontrollen, Grenzen + Origin-Mix explizit.
Konsument/Aggregator, **erfindet keine neue Modellmechanik**.

| TAP | Inhalt | Status | Trace / Hinweis |
| --- | --- | --- | --- |
| AP-32.1 | E2E-Lauf `src/siasa/validation/e2e_validation_run.py`: Modell über reale Fenster, Status-Zeitreihe + Positiv/Kontroll-Trennung | Offen | SwR-103 |
| AP-32.2 | Report-Aggregation `validation_report.py`: Skill-Metriken (ALGO-SKILL-02) vs No-Skill-Baseline, `beats_baseline` | Offen | SwR-104 |
| AP-32.3 | Ehrlicher Grenzen-/Origin-Mix-Block (kleine Fallzahl, Coverage, real vs fixture); Warnung bei reinem Fixture-Set | Offen | SwR-105 |
| AP-32.4 | Artefakt `readmodels/validation_report.json` (deterministisch) + GUI-Sichtbarkeit | Offen | SwR-106 / StR-698..701 |

**Kritischer Pfad (AP-26…32):** `AP-18 → AP-26`; parallel `AP-27 → AP-29 → AP-30 → AP-31`;
`(AP-16, AP-26, AP-27) → AP-28`; `(AP-26, AP-28, AP-30, AP-31) → AP-32`. Längster Pfad =
`AP-27 → AP-29 → AP-30 → AP-31 → AP-32` (enthält das XL/hoch-Risiko-Paket AP-30). AP-16 ist
verstecktes Bottleneck für AP-28/AP-32 — vorab schließen.

---

## 5. Offene Lücken & Blocker (Zusammenfassung)

| # | Lücke | Betroffenes AP | Art | Nächster Schritt |
| --- | --- | --- | --- | --- |
| L1 | ~~Tiefe des non-perfekten Replay-Realismus / Decision-Auto-Seeds~~ | AP-05.6 | geschlossen | AP-05 erledigt; Decision-log auto-seeds implementiert |
| L2 | ReliefWeb/UCDP nur repo-ready, nicht live aktiviert | AP-06.1/.2 | **extern blockiert** | Credentials beschaffen → AP-06 auf P1 |
| L3 | ~~GDELT-Provider-Degradation & Release-Konsequenz~~ | AP-07 | geschlossen | Per-Country-Fault-Isolation + shared retry_utils; `69ca9fc` |
| L4 | ~~Breite über die governed 30-Länder hinaus~~ | AP-08.1 | geschlossen | 88 Länder, 5 regionale Pilot-Sets; `20d0e93` |
| L5 | Multi-User/Server-Governance | AP-09 | strategisch | nur bei Operating-Model-Bedarf (P3, zurückgestellt) |
| L6 | ~~Uneinheitliche/unklare Terminologie über Planungs- und Code-Artefakte~~ | AP-10 | geschlossen | Glossar mit 55 Termen erstellt; Artefakte konsistent |
| L7 | ~~Domain-D/E/C/A-Coverage dünn~~ | AP-11 | geschlossen | 3 neue Adapter (Frankfurter/Voidly/HDX-INFORM); 4 TAPs extern blockiert (API-Key/DNS) |
| L8 | ~~GUI zeigt zu wenig Quellen-/Methodik-Transparenz~~ | AP-12 | geschlossen | 3 neue Seiten (Sources, About, Methodology), parametrierbare Zeitachse, aufklappbare Quellen-Details, Cross-Links; 31 Tests |
| L9 | Keine permanente Datenhaltung — alle Records gehen nach 168h verloren; kein ML-Training möglich | AP-13 | **geschlossen** | 15/15 TAPs erledigt: Parquet-Archiv + DuckDB + Features + ML-Integration + Ops |
| L10 | Modell gibt konstantes Signal (anomaly_score Konstante); Validierung misst keine Modellgüte | AP-16/17/18/25/26/28 | **offen (Phase 0+1)** | Korrektheit + Messinstrument: reale Anomalie, σ/z-Score, Fail-Loud, Status-Zeitreihe, Skill-Metrik |
| L11 | Ground-Truth degeneriert: keine S0-Negative, kein Onset, zirkuläre Labels (F15) | AP-27 | **offen (Phase 1a)** | Label-Redesign — längster Pol; Hoheit Projekteigner |
| L12 | „Echte" Eventdaten sind synthetisch (4–8 Hand-Records, falsch als provider-derived deklariert) (F14) | AP-29/30/31 | **offen (Phase 2)** | Echter historischer Backfill GDELT/GDACS/WB + PIT + ehrliche Origin-Kennzeichnung — größter Block |

Pivot-Auslöser (wann die Priorisierung neu bewertet wird):
- AP-13 Data Lake abgeschlossen → ML-Training-Workflows ermöglichen;
- gültige ReliefWeb/UCDP-Credentials werden verfügbar → AP-06 hoch;
- frische Runtime-Evidenz zeigt einen neuen Steuerungs-/Wahrheitsdefekt → AP-07 hoch;
- externe Steuerung fordert Multi-User-Betrieb → AP-09 aktivieren;
- ein neuer Länder-/Quellen-Cluster wird Pflicht → AP-08 hoch;
- konkrete Analytik-Anforderung braucht breitere Domain-Coverage → AP-11 hoch.

---

## 6. Abgelöste Dokumente (Konsolidierungs-Mapping)

Alle folgenden Dokumente wurden in diesen Master-Plan konsolidiert und nach `docs/plans/outdated/` verschoben.
Sie bleiben als historische Referenz/Traceability erhalten, sind aber **nicht** mehr steuerungsmaßgeblich.

| Abgelöstes Dokument (jetzt in `outdated/`) | Frühere Rolle | Konsolidiert in |
| --- | --- | --- |
| `siasa-master-steering-document.md` | „single steering document", `G1–G5`, `N1-WP-001..071` | Abschnitte 2–5 |
| `siasa-stakeholder-fulfillment-roadmap.md` | Strategie `Step A/B/C`, Phasen `P0–P4` | Abschnitte 2–4 |
| `siasa-next-big-packages-executive-view.md` | Executive `G1–G5`-Einseiter | Abschnitt 2/3 |
| `siasa-planning-audit-and-next-steps.md` | Planungs-Hygiene/Audit | Abschnitt 6 (Aufgabe erfüllt) |
| `siasa-functional-implementation-plan.md` | `AP-F01..F27` Funktionsplan (ausgeführt) | AP-01 (Historie) |
| `siasa-stakeholder-gap-sweep-and-development-sequence.md` | `AP-N01` Gap-Sweep | AP-01/AP-05 (Historie) |
| `siasa-stakeholder-functional-closure-gap-plan.md` | 19-ID Closure-Cluster (erfüllt) | AP-01 (Historie) |
| `siasa-level-3-user-value-flow-plan.md` | L3 User-Value-Flow (großteils erfüllt) | AP-05 (Historie) |
| `siasa-level-4-demo-release-readiness-plan.md` | L4 Release-Readiness (erfüllt/überholt) | AP-04 (Historie) |
| `siasa-initial-implementation-workpackages.md` | Bootstrap-Erstplanung | AP-01 (Historie) |
| `siasa-p0-wp-001-source-access-assessment.md` | Source-Access-Constraints | AP-06 (Constraints übernommen) |
| `siasa-p0-wp-002c-domain-b-source-selection.md` | Domain-B-Source-Selection-Notiz | AP-06 (Historie) |

Weiterhin aktiv (nicht abgelöst): `docs/plans/siasa-capability-fulfillment-matrix.md` als Evidenz-Begleiter
(von `src/siasa/readmodels/release_evidence.py` gelesen).

---

## 7. Pflegeregeln

1. Nach jedem abgeschlossenen Teilarbeitspaket: Status hier aktualisieren, Evidenz/Herkunft ergänzen,
   Capability-Matrix als Evidenz-Begleiter nachziehen.
2. Strategische Priorität (Abschnitt 3) nur überarbeiten, wenn ein Pivot-Auslöser (Abschnitt 5) eintritt.
3. Neue Arbeitspakete: nächste freie `AP-NN` (Ebene 1) bzw. `AP-NN.M` (Ebene 2); IDs nie wiederverwenden.
4. Keine neue Parallel-Planungsgeneration anlegen – dieses Dokument bleibt die einzige Planungsquelle.
5. Bei neuen Begriffen/Konzepten: `docs/glossary.yaml` ergänzen; bei Begriffs-Widersprüchen Glossar als Referenz.
