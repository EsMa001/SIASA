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

## 7. Erste Kuratierung (v1) — Ergebnis

Status: **umgesetzt (2026-06-26)**. Alle Fakten gegen öffentliche Quellen verifiziert (Research-Workflow),
jeder Fall `ratification_status: proposed`. AP-27-Validator: `is_valid=True`, 0 Onset-/Split-/Polarity-Verstöße,
`s0_negative_count=3`. AP-29-Konsistenztest grün.

**3 gematchte Paare (real, quellenbelegt):**

| Paar | Eskalation | Onset (verifiziert) | Quelle | Gematchte Kontrolle (Q2-2024, ruhig verifiziert) |
|---|---|---|---|---|
| 1 | VAL-UKR-2022-001 (Invasion) | 2022-02-24 | en.wikipedia.org/wiki/2022_Russian_invasion_of_Ukraine | VAL-CHE-2024-NEGATIVE-001 (Schweiz) |
| 2 | VAL-ISR-2023-001 (Gaza-Krieg) | 2023-10-07 | en.wikipedia.org/wiki/October_7_Hamas-led_attack_on_Israel | VAL-OMN-2024-NEGATIVE-001 (Oman, **neu**) |
| 3 | VAL-SDN-2023-001 (RSF-SAF-Krieg, **neu**) | 2023-04-15 | hrw.org breaking-news 2023-04-15 | VAL-GHA-2024-NEGATIVE-001 (Ghana, **neu**) |

**Kontroll-Verifikation:** alle drei Q2-2024-Fenster aktiv auf größere Eskalationen geprüft → keine im Fenster
(Oman: Muscat-Anschlag 2024-07-15 liegt *außerhalb*; Ghana: Bawku-Eskalationen ab Okt 2024 *außerhalb*).

**Methoden-Einschränkung (dokumentiert):** Konfliktzonen haben selten eigene „ruhige" Fenster — daher sind die
Kontrollen **strukturell vergleichbare stabile** Länder (Europa / Golf / Westafrika), nicht dieselben Länder.
Diese Schwäche des Matchings wird mit AP-30-Realdaten adressierbar (Vor-Onset-Fenster desselben Landes).

**Owner-Ratifizierung offen:** Auswahl + Onsets gegen Primärquellen prüfen; ggf. Kontrollen durch dieselben
Länder in nachweislich ruhigen Fenstern ersetzen, sobald AP-30 echte Daten liefert.
