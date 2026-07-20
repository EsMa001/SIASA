# Event-Set-Kuratierungsverfahren (AP-29 → AP-30)

Stand: 2026-06-26 · Zweck: ein **reproduzierbares, auditierbares Verfahren**, um das
Validierungs-Event-Set (gematchte Eskalations-/Kontroll-Paare, AP-29) mit **defensibler
Ground-Truth** zu füllen — nicht ad hoc. Begleitartefakte: `vmodel/verification/validation_event_set.yaml`
(Paare), `vmodel/verification/validation_reference_cases.yaml` (Labels), AP-27-Validator
`validate_reference_case_library`, AP-29-Konsistenztest.

> **Grundprinzip (Ehrlichkeit zuerst):** Es werden **ausschließlich real dokumentierte Ereignisse**
> als Ground-Truth kuratiert. Die synthetischen 2024-„strategic_posturing"-Platzhalter der Bibliothek
> sind **keine** zulässige Quelle. Jeder kuratierte Fall trägt eine Quellen-Provenienz und den Status
> `ratification_status: proposed` — die finale Ratifizierung gegen Primärquellen bleibt Owner-Hoheit.

---

## 1. Designprinzipien

1. **Matched-Pairs / Case-Control-Design** (Standard der Forecast-/Epidemiologie-Evaluation): jede
   Eskalation (Positivfall) wird mit einer **strukturell vergleichbaren ruhigen Kontrolle** (S0-Negativ)
   gepaart, damit die **Fehlalarmrate messbar** wird und Confounder kontrolliert sind.
2. **Ground-Truth aus dem öffentlichen Record, nicht aus dem Modell** (Anti-Zirkularität): Onset und
   Trajektorie stammen aus dokumentierten realen Ereignissen; `historical_observed_status` wird **nicht**
   mechanisch aus `expected_status` kopiert (der AP-27-Validator flaggt das bei Positivfällen).
3. **Nur verifizierte Fakten:** Onset-Daten und „ruhig"-Behauptungen werden gegen öffentliche Quellen
   **verifiziert** (nicht aus dem Gedächtnis gesetzt); die Quelle wird je Fall notiert.
4. **Owner-Ratifizierung:** Das Verfahren erzeugt einen **Vorschlag** (`ratification_status: proposed`).
   Der Owner ratifiziert/verfeinert jeden Fall gegen Primärquellen, bevor er als autoritativ gilt.

## 2. Auswahlkriterien — Eskalationen

Ein Eskalations-Kandidat ist zulässig, wenn er **alle** erfüllt:
1. Entspricht einem **real dokumentierten Ereignis** mit **eindeutigem öffentlichem Onset-Datum**.
2. **Multi-Domain** (≥2 `expected_domains`) — prüft Cross-Domain-Detektion.
3. **Gut bequellt** (≥3 `reference_sources` aus dem kanonischen Katalog SRC-GDELT-DOC/-EVENTS/SRC-GDACS/WB-INDICATORS).
4. **Diversität** über das Set: verschiedene Regionen + Eskalationstypen (nicht 3× dasselbe Muster).
5. Onset liegt **innerhalb** des Fall-Fensters (`time_start ≤ onset ≤ time_end`).

## 3. Auswahlkriterien — gematchte Kontrollen

1. **Ruhiges Fenster** (S0): ein Land/Zeitraum **ohne dokumentierte größere Eskalation** im Fenster.
   Vorrang: gleiches Land in nachweislich ruhigem Fenster; wo das für Konfliktzonen nicht möglich ist
   (sie sind selten „ruhig"), eine **strukturell vergleichbare stabile** Region/Periode (wie die
   bestehende CHE-Kontrolle). Diese Einschränkung wird je Kontrolle dokumentiert.
2. `expected_status: S0`, `expected_trajectory: [S0, S0, S0]`, `case_polarity: negative`.
3. Gleicher `reference_sources`-Katalog wie die Eskalationen (damit `assigned_sources` vergleichbar sind).
4. `dataset_split: holdout` (Kontrollen sind Evaluations-reserviert, nicht zum Tunen).

## 4. Onset, Trajektorie, Quellen

- **Onset** = das **dokumentierte Startdatum** der Eskalation (verifiziert, Quelle notiert), innerhalb des Fensters.
- **Eskalations-Trajektorie** = monotoner Anstieg konsistent zum `expected_status` (z. B. `[S0, S2, S3]`):
  Vor-Onset-Ruhe → Eskalation.
- **Kontroll-Trajektorie** = flach `[S0, S0, S0]`.
- **assigned_sources** (im Event-Set) ⊆ `reference_sources` des referenzierten Falls (AP-29-Schema).

## 5. Anti-Zirkularität & Governance

- `historical_observed_status` ist das reale Ergebnis, unabhängig von `expected_status` gesetzt; der
  AP-27-Validator flaggt Positivfälle, bei denen beide mechanisch gleich sind (Phase-4-Überanpassungsschutz).
- Split: Eskalationen können `tuning` oder `holdout` sein; die Kontrollen sind `holdout`.
- Jeder kuratierte Fall: **Provenienz-Notiz** (Basis für Onset/„ruhig") + `ratification_status: proposed`.

## 6. Validierungs-Gate (muss grün sein)

1. `validate_reference_case_library` besteht (Onset-im-Fenster, governter Split/Polarity, Anti-Zirkularität).
2. AP-29-Konsistenztest besteht (jedes Paar referenziert einen realen Fall, Eskalation = Positiv,
   Kontrolle = S0-Negativ, `assigned_sources ⊆ reference_sources`).
3. Reference-Summary-Count-Sync nachgezogen; Vollsuite grün.

---

## 7. Kuratierung — Ergebnis (v2, 8 Paare)

Status: **umgesetzt + erweitert (2026-06-26)**. Alle Onsets und alle In-Fenster-„Ruhe"-Aussagen gegen
öffentliche Quellen verifiziert (zwei Research-Workflows); jeder Fall `ratification_status: research_verified`
(Quelle je Fall in `validation_reference_cases.yaml`). AP-27-Validator: `is_valid=True`, 0 Onset-/Split-/
Polarity-Verstöße, `s0_negative_count=8`. AP-29-Konsistenztest grün.

**8 gematchte Paare (real, quellenbelegt; Kontrollen periodengematcht):**

| # | Eskalation | Onset | Gematchte Kontrolle (gleiche Periode, ruhig verifiziert) |
|---|---|---|---|
| 1 | UKR-2022 Invasion | 2022-02-24 | CHE 2024-Q2 (Schweiz) |
| 2 | ISR-2023 Gaza-Krieg | 2023-10-07 | OMN 2024-Q2 (Oman) |
| 3 | SDN-2023 RSF-SAF-Krieg | 2023-04-15 | GHA 2024-Q2 (Ghana) |
| 4 | AZE-2023 Berg-Karabach | 2023-09-19 | NOR 2023-Q3 (Norwegen) |
| 5 | NER-2023 Niger-Putsch | 2023-07-26 | BWA 2023-Q3 (Botswana) |
| 6 | AFG-2021 Kabul | 2021-08-15 | URY 2021-Q3 (Uruguay) |
| 7 | MMR-2021 Putsch | 2021-02-01 | CRI 2021-Q1 (Costa Rica) |
| 8 | SYR-2024 Sturz Assads | 2024-11-27 | JPN 2024-Q4 (Japan) |

**Quellen je Fall:** Onset- und Ruhe-Quellen stehen als Kommentar/`known_limitations` direkt am jeweiligen Fall
in `validation_reference_cases.yaml` (Eskalationen: Wikipedia/HRW; Kontrollen: Freedom House / nationale Quellen).
Jede Kontrolle wurde aktiv auf In-Fenster-Eskalationen geprüft (keine gefunden; z. B. Omans Anschlag 2024-07-15
und Ghanas Bawku-Eskalation ab Okt 2024 liegen *außerhalb* der Fenster).

**Methoden-Einschränkung (dokumentiert):** Konfliktzonen haben selten eigene „ruhige" Fenster — daher sind die
Kontrollen **strukturell vergleichbare stabile Länder derselben Periode**, nicht dieselben Länder. Mit
AP-30-Realdaten durch Vor-Onset-Fenster desselben Landes ersetzbar.

**Owner-Ratifizierung offen:** Auswahl + Onsets + Ruhe-Aussagen gegen Primärquellen **final** ratifizieren;
ggf. Kontrollen durch dieselben Länder in nachweislich ruhigen Fenstern ersetzen, sobald AP-30 echte Daten liefert.

## 8. Kuration v3 (2026-07-19, AP-34.4/34.5 — SwR-111/112)

**Anlass:** Fundament-Audit 2026-07 (Befunde A-08 Zirkularität, A-19 dekorativer Split) und die
dabei entdeckte v2-Split-Schieflage: *alle* Positiven lagen im Tuning-, *alle* Kontrollen im
Holdout-Split — eine Holdout-Evaluation hätte null Positive (Recall undefiniert), die Kalibrierung
null Kontrollen (Fehlalarmrate undefiniert) gehabt.

**Änderung 1 — stratifizierter Paar-Split (SwR-112):** Paare wandern geschlossen.
Tuning: Paare 1 (UKR–CHE), 3 (SDN–GHA), 7 (MMR–CRI), 8 (SYR–JPN) ·
Holdout: Paare 2 (ISR–OMN), 4 (AZE–NOR), 5 (NER–BWA), 6 (AFG–URY).
Beide Splits enthalten damit beide Klassen sowie Regionen- und Typ-Diversität (je ein Putsch,
je ein Staatskollaps). Durchsetzung: die Sensitivitäts-/Kalibrier-Kette schließt den
Holdout-Split aus (`scripts/threshold_sensitivity.py`); das Validierungs-Read-Model berichtet
Skill **je Split** und deklariert Holdout als Evaluations-Split.

**Änderung 2 — `observation_basis` je onset-datiertem Positivfall (SwR-111):** dokumentiert den
label-unabhängigen Beobachtungspfad, über den `historical_observed_status` bestimmt wurde.
Der Validator blockiert (`is_valid: false`) jeden onset-datierten Positivfall, dessen
Beobachtungs- und Soll-Label identisch sind, **ohne** dass eine solche Basis dokumentiert ist —
Gleichheit ist bei gut kuratierten Fällen legitim, stilles Label-Kopieren nicht mehr.
Zusätzlich zählt der Validator jetzt `ratification_status` aus (Feld war zuvor von keinem Code
gelesen, Audit A-20).

**Owner-Ratifizierung weiterhin offen** (unverändert aus v2); die v3-Änderungen sind
mechanik-/governance-seitig und ändern keine Fall-Labels.
