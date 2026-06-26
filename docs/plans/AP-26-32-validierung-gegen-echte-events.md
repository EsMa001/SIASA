# SIASA Validierung gegen echte Events — Arbeitspakete AP-26..AP-32

Quelle: Phasenplan "Modell gegen echte Events pruefen" (2026-06-25).
Leitet die fuenf Phasen (0..4) in ausfuehrbare Arbeitspakete ab und verzahnt sie
mit den bestehenden AP-16..AP-25.

**Bestimmender Befund:** Der laengste Hebel ist *Daten + Labels*, nicht Code.
Zwei neue Hauptbefunde ergaenzen F1..F13:

| Befund | Schwere | Beschreibung | Schliessendes AP |
|--------|---------|-------------|------------------|
| F14 | 1 | "Echte" Eventdaten sind synthetisch (4–8 hand-geschriebene Records, als `provider-derived` deklariert) | AP-30 + AP-31 |
| F15 | 1 | Ground-Truth degeneriert: keine Negative (kein S0), keine Onset-Daten, keine Trajektorien, zirkulaeres `historical_observed_status` | AP-27 |
| F16 | 2 | Replay liefert Punktstatus statt taeglicher Status-Zeitreihe | AP-26 |

**Governance:** Label-Kuratierung (AP-27), Schwellenwerte und Status-Uebergaenge
bleiben beim Projekteigner. Die WPs liefern Mechanik und Tests, nicht die
fachlichen Festlegungen.

---

## Uebersicht

| AP-ID | Phase | Titel | Schliesst | Abhaengig von | Aufwand | Prio | Laengster Pol? |
|-------|-------|-------|-----------|---------------|---------|------|----------------|
| AP-26 | 0 | Status-Zeitreihe im Fenster-Replay | F16 | AP-17, AP-18, AP-25 | M | P1 | — |
| AP-27 | 1a | Ground-Truth-Redesign mit Negativfaellen | F15 | — | M | P1 | **ja** |
| AP-28 | 1b | Skill-Metrik: Fehlalarmrate + No-Skill-Baseline | F9 (real) | AP-16, AP-26, AP-27 | M | P1 | — |
| AP-29 | 2a | Event-Set-Definition (klein, ausgewogen) | F14 (vorber.) | AP-27 | S | P2 | — |
| AP-30 | 2b | Historischer Backfill GDELT/GDACS/WB + PIT | F14 | AP-29, AP-13 | XL | P2 | **ja (groesster)** |
| AP-31 | 2c | Provenance & Kennzeichnung real-captured vs fixture | F14 | AP-30 | M | P2 | — |
| AP-32 | 3 | End-to-End-Validierung gegen echte Events + Skill-Report | F7,F8 (real) | AP-26, AP-28, AP-30, AP-31 | M | P3 | — |

> **Steuerung & TAP-Detail:** Maßgeblich für Priorität, Status und die Teilarbeitspaket-Zerlegung
> (AP-NN.M mit Trace-IDs/Akzeptanz) ist der Masterplan, Abschnitt 4.D (`docs/plans/siasa-master-plan.md`).
> Disjunkte Trace-Allokation: AP-26 = SwR-084..087/StR-678..681/ALGO-REPLAY-TS-01 · AP-27 = SwR-088..090/StR-682..684 ·
> AP-28 = SwR-091..094/StR-685..688/ALGO-SKILL-02 · AP-29 = StR-689..692 · AP-30 = SwR-095..101/StR-693..696/ALGO-BACKFILL-01 ·
> AP-31 = SwR-102/StR-697 · AP-32 = SwR-103..106/StR-698..701.

**Vorausgesetzte Bausteine (bereits als AP definiert, hier nur referenziert):**
- Phase 0 Kern: **AP-17** (σ/z-Score), **AP-18** (Feature→Anomalie), **AP-25** (Fail-Loud).
- Phase 1 Instrument-Basis: **AP-16** (Skill-Messharness) — wird durch AP-27/AP-28 erst aussagekraeftig.
- Phase 4 Iteration: **AP-19, AP-20, AP-21, AP-22, AP-24** — werden nach AP-32 gegen den Skill-Score bisektierbar.

---

## Phase 0 — Korrektheit herstellen *(Gate fuer alles Weitere)*

> Kern abgedeckt durch **AP-17 → AP-18 → AP-25**. Hier nur die *neue* Luecke:

### AP-26: Status-Zeitreihe im Fenster-Replay

**Ziel:** Der Replay-Pfad erzeugt aus gegebenen Records eine taegliche
Status-*Zeitreihe* ueber das Fenster — nicht nur ein Einzel-Label pro Fall.
Voraussetzung fuer Vorlaufzeit-Messung und Trajektorien-Bewertung.

**Befunde:** F16

**In-Scope:**
- `historical_replay.py` / `archival_replay.py`: pro Tag im Fenster
  PIT-Features ziehen und Status berechnen → Liste `(date, status, confidence)`
- Determinismus erhalten: zwei identische Laeufe erzeugen bit-gleiche Artefakte
- Artefakt `readmodels/status_timeseries_<case>.json`

**Out-of-Scope:** Anomalie-Logik (→ AP-18), Skill-Berechnung (→ AP-28)

**Trace:** SwR (Replay-Loader), neuer Algo ALGO-REPLAY-TS-01

**Akzeptanz:**
1. Auf Fixture mit variierendem Input aendert sich der Status ueber das Fenster nachvollziehbar
2. Zwei identische Laeufe erzeugen bit-gleiche Zeitreihen-Artefakte
3. Erzwungene Ausnahme in einer Stufe erscheint als expliziter Degradationseintrag (Kopplung AP-25)

**Abhaengig von:** AP-17 (σ/z-Score), AP-18 (reale Anomalie), AP-25 (Fail-Loud)
**Aufwand:** M (3–5 PT) · **Risiko:** mittel

**Gate Phase 0 (DoD gesamt):** variierender Input → nachvollziehbarer Statuswechsel;
bit-gleiche Artefakte bei Wiederholung; erzwungene Ausnahme = expliziter Degradationseintrag.

---

## Phase 1 — Messbarkeit schaffen *(das Instrument)*

### AP-27: Ground-Truth-Redesign mit Negativfaellen *(Domaenenarbeit, Hoheit Projekteigner)*

**Ziel:** Das Label-Set so reparieren, dass Fehlalarme ueberhaupt messbar werden.

**Befunde:** F15

**In-Scope:**
- **Negativfaelle ergaenzen:** ruhige Laender/Fenster mit erwartetem `S0`
  (z. B. CHE/NLD/CAN in ruhigen Quartalen — heute als S3 fehl-gelabelt).
  Ziel: ausgewogenes Positiv/Negativ-Verhaeltnis
- **Onset-Datum je Positivfall** statt nur Monatsfenster (Voraussetzung Vorlaufzeit)
- **Erwartete Trajektorie** statt Pauschal-Label: ruhig vor Onset, Eskalation danach
- Trennung **Tuning- vs. Holdout-Set** (verhindert Phase-4-Ueberanpassung)
- Zirkulaeres `historical_observed_status` aufloesen (nicht == `expected_status`)

**Out-of-Scope:** Skill-Berechnung (→ AP-28), echte Daten (→ AP-30)

**Trace:** `validation_reference_cases.yaml` (Schema-Erweiterung um onset/trajectory/split)

**Akzeptanz:**
1. Label-Set enthaelt ≥1 echten `S0`-Negativfall mit ruhiger erwarteter Trajektorie
2. Jeder Positivfall traegt ein Onset-Datum und eine Vor/Nach-Trajektorie
3. Tuning- und Holdout-Faelle sind disjunkt markiert
4. Schema-Validierungstest gruen

**Abhaengig von:** keine (laeuft parallel zu Phase 0) · **Hoheit:** Projekteigner
**Aufwand:** M (Kuratierung) · **Risiko:** mittel (Label-Qualitaet bestimmt die Aussagekraft des Gesamtvorhabens)

---

### AP-28: Skill-Metrik mit Fehlalarmrate + No-Skill-Baseline

**Status (2026-06-26): erledigt** (Commit `749b18c`). ALGO-SKILL-02 in
`validation/skill_metrics.py`: Fehlalarmrate (nur S0-Negative), Vorlaufzeit (AP-26-Zeitreihe +
Onset), Brier (S-Status-Proxy), No-Skill-Baseline „immer S3" + `beats_baseline`. V-Model
SwR-091..094/StR-685..688/ALGO-SKILL-02 + Count-Sync; Vollsuite 1161 passed. Zahlen werden erst
mit echten Labels + AP-30 aussagekraeftig (heute 35 S3-Positive + 1 S0-Negativ-Vorlage).

**Ziel:** AP-16 auf dem redesignten Labelset real machen — mit der Faehigkeit,
Fehlalarme zu erkennen und eine triviale Baseline zu schlagen.

**Befunde:** F9 (real geschlossen), entschaerft F7/F8

**In-Scope:**
- Auf AP-27-Labels: Detektionsrate (Recall), **Fehlalarmrate auf Negativfaellen**,
  Vorlaufzeit vor Onset, Brier-Score auf das Bayes-Posterior
- **No-Skill-Baseline ("immer S3")** mitberechnen — muss geschlagen werden
- Ausgabe `readmodels/skill_metrics.json`, Kennzahl im GUI-Validation-View

**Out-of-Scope:** Scoring-Logik selbst (→ AP-18), echte Daten (→ AP-30)

**Trace:** ALGO-SKILL-01 (AP-16) erweitert um Baseline + False-Alarm

**Akzeptanz:**
1. Bewusst verschlechtertes Modell senkt den Skill-Score messbar (Regressionstest)
2. "immer-S3"-Baseline erzielt hohe Status-Trefferquote, aber schlechte Fehlalarm-/Vorlaufbewertung
3. Fehlalarmrate ist nur dank AP-27-Negativfaellen > 0 definiert

**Abhaengig von:** AP-16, AP-26, AP-27
**Aufwand:** M (3–5 PT) · **Risiko:** mittel

**Gate Phase 1 (DoD):** verschlechtertes Modell → niedrigerer Score; Baseline wird
auf Fehlalarm/Vorlauf geschlagen (beweist: Metrik misst mehr als Status-Match).

---

## Phase 2 — Echte Eventdaten beschaffen *(der laengste Pol)*

### AP-29: Event-Set-Definition (klein, ausgewogen)

**Status (2026-06-26): Mechanik erledigt** (Commit `2abbd02`). Artefakt
`vmodel/verification/validation_event_set.yaml` (gematchte Eskalations-/Kontroll-Paare → AP-27-`case_id`)
+ Konsistenztest (`test_validation_cases.py`, re-use `load_validation_case_library`). StR-689..692 unter
SyR-026 (kein neuer SwR/TC); Count-Sync 688→692; Vollsuite 1162 passed. **1 Beispiel-Paar geseedet**
(UKR↔CHE) — die echte 3+3-Kuratierung (welche Eskalationen/Kontrollen) bleibt Owner-Hoheit und braucht
echte Negativ-Kontrollen (gated AP-30).

**Ziel:** Konkretes, kleines Event-Set festlegen statt vieler Fixtures.

**Befunde:** F14 (Vorbereitung)

**In-Scope:**
- z. B. 3 echte Eskalationen + 3 gematchte ruhige Kontrollen (gleiche Laender, ruhige Fenster)
- Pro Fall: Land, Fenster, Onset, erwartete Trajektorie (aus AP-27 abgeleitet)
- Quell-Zuordnung je Fall (SRC-GDELT-DOC/EVENTS, SRC-GDACS, WB-INDICATORS)

**Akzeptanz:**
1. Event-Set dokumentiert, jeder Positivfall hat eine gematchte Kontrolle
2. Jeder Fall verweist auf einen AP-27-Labeleintrag

**Abhaengig von:** AP-27 · **Aufwand:** S (≤2 PT) · **Risiko:** niedrig

---

### AP-30: Historischer Backfill GDELT/GDACS/WB + Point-in-Time

**Ziel:** Die 4–8-Record-Fixtures durch real erfasste historische Daten ersetzen.

**Befunde:** F14

**In-Scope:**
- Pro Fall/Fenster real ziehen und ueber die vorhandenen Adapter ins
  `NormalizedRecord`-Schema mappen:
  - GDELT (Events + GKG/DOC) — Volumen, Rate-Limits, Aggregation auf
    kanonische Tagesaufloesung via `DailyAligner`
  - GDACS (Disaster-Alerts), World Bank (Makro, jaehrlich → forward-fill)
- **Point-in-Time-Disziplin:** nur am Stichtag verfuegbare Daten (kein Look-ahead);
  `PointInTimeJoiner` mit echten Beobachtungszeitpunkten fuettern
- Roh-/Normalized-Bundles mit Manifest ablegen

**Out-of-Scope:** Umlabeln/Provenance-Korrektur (→ AP-31), Validierung (→ AP-32)

**Trace:** SRC-GDELT-*, SRC-GDACS, WB-INDICATORS; ALGO-BACKFILL-01

**Akzeptanz:**
1. Fuer ≥1 Positiv- und ≥1 Kontrollfall liegen real erfasste, normalisierte Bundles vor
2. Datenmengen plausibel (≥100 Records je Fall, Groessenordnungen ueber den 8-Record-Fixtures)
3. PIT-Replay laeuft end-to-end ohne Look-ahead (Test mit verschobenem Stichtag belegt das)

**Abhaengig von:** AP-29 (Event-Set), AP-13 (DailyAligner/PIT/ArchiveWriter)
**Aufwand:** XL (groesster Block) · **Risiko:** hoch (API-Zugaenge, Volumen, Schema-Mapping, Quellzitierung)

---

### AP-31: Provenance & ehrliche Kennzeichnung real-captured vs fixture

**Ziel:** Die heutige falsche "provider-derived"-Behauptung korrigieren und
real erfasste Daten sauber von Fixtures trennen.

**Befunde:** F14

**In-Scope:**
- Manifest-Flag `data_origin: real-captured | fixture` einfuehren und je Bundle setzen
- `provenance_notes` der bestehenden Fixtures korrigieren (kein "provider-derived" mehr)
- Readiness/artifact_status weist real vs. fixture sichtbar aus

**Akzeptanz:**
1. Jedes Bundle traegt ein eindeutiges Origin-Flag
2. Kein Fixture behauptet mehr faelschlich provider-Herkunft
3. GUI/Report zeigt den Origin-Mix des Validierungslaufs

**Abhaengig von:** AP-30 · **Aufwand:** S–M · **Risiko:** niedrig

**Gate Phase 2 (DoD):** ≥1 Positiv- + 1 Kontrollfall real & governt; PIT-Replay
ohne Look-ahead; plausible Datenmengen; korrekte Origin-Kennzeichnung.

---

## Phase 3 — Validierung gegen echte Events *(das Ziel)*

### AP-32: End-to-End-Validierung + Skill-Report

**Ziel:** Korrigiertes Modell ueber die realen Fenster laufen lassen und Guete beziffern.

**Befunde:** F7, F8 (real geschlossen)

**In-Scope:**
- Korrigiertes Modell (Phase 0 / AP-26) ueber reale Fenster (AP-30) mit PIT-Features
  → Status-Zeitreihe je Fall
- Skill-Metriken (AP-28): Detektion ueber Positive, Fehlalarm ueber Kontrollen,
  Vorlaufzeit vor Onset, Brier auf Posterior
- Vergleich gegen No-Skill-Baseline, **ehrlicher Report inkl. Grenzen**
  (kleine Fallzahl, Quellabdeckung)

**Akzeptanz:**
1. Validierungsreport schlaegt die "immer-S3"-Baseline
2. Messbare Fehlalarmrate auf den Kontrollen ausgewiesen
3. Report nennt explizit Grenzen und Origin-Mix der Daten

**Abhaengig von:** AP-26, AP-28, AP-30, AP-31
**Aufwand:** M · **Risiko:** niedrig (sofern Phase 0–2 sauber)

**Gate Phase 3 (DoD):** Erst mit diesem Report ist "gegen echte Events geprueft"
eine wahre Aussage.

---

## Phase 4 — Iterieren *(bestehende APs, jetzt bisektierbar)*

Nach AP-32 ist jede Aenderung gegen den Skill-Score messbar:
**AP-19** (echte Unsicherheit) · **AP-20** (Abhaengigkeit + Zentralitaet) ·
**AP-21** (Info-Epi, echte Zeitstempel) · **AP-22** (Fusion → Entscheidung, D5) ·
**AP-24** (Schwellen-Governance). AP-23 (Provenance-Tiefe) laeuft unabhaengig.

**Gate Phase 4 (DoD):** Jede Iteration weist eine Skill-Score-Differenz zum
Vorstand aus; Schwellenaenderungen laufen ueber governte Konfig, nicht ueber Code.

---

## Kritischer Pfad

```
Phase 0:  AP-17 ─┐
          AP-18 ─┼──► AP-26 (Status-Zeitreihe) ─┐
          AP-25 ─┘                               │
                                                 ├──► AP-32 ──► Phase 4
Phase 1:  AP-16 + AP-27 (Labels) ──► AP-28 ──────┤        (AP-19/20/21/22/24)
                       │                          │
Phase 2:               └──► AP-29 ─► AP-30 ─► AP-31
```

Zwei parallele laengste Pole (laut Phasenplan):
**AP-27 (Labels)** und **AP-30 (echte Daten)**. Beide koennen parallel zu Phase 0 starten.

**Minimaler ehrlicher Durchstich (kleinste wahre Konfiguration):**
AP-17 + AP-18 + AP-25 + **AP-26** + **AP-27** (1 Positiv + 1 Kontrolle) +
**AP-28** + **AP-29/30/31** (genau diese 2 Faelle) + **AP-32**.
Erst damit ist "gegen echte Events geprueft" keine Uebertreibung.

---

## Befund-Zuordnung (Ergaenzung zu F1..F13)

| Befund | Phase | Schliessendes AP |
|--------|-------|------------------|
| F14 — synthetische Eventdaten | 2 | AP-30 + AP-31 |
| F15 — degenerierte Labels (keine Negative) | 1a | AP-27 |
| F16 — Punktstatus statt Zeitreihe | 0 | AP-26 |
