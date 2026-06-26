# SIASA — Session-Handoff (Stand 2026-06-26)

> Zweck: Diese Datei trägt den **handlungsrelevanten Kontext** einer vorherigen Claude-Code-Session
> auf einen anderen Rechner (CLI-Sessions/Memory/Tasks synchronisieren NICHT über Geräte — nur Git tut das).
> Auf dem anderen Rechner: `git pull` + frische `claude`-Session + diese Datei lesen.

Branch: `hermes/repo-scaffold` (= Main-Branch des Projekts; Commits gehen direkt hierauf).

---

## ⭐ Update 2026-06-26 (neueste) — AP-24 Schwellen-Governance vorgezogen (F11)

AP-24 (Plan: Phase 4) auf Nutzer-Wunsch vorgezogen: die hartcodierten Analytik-„Magic Numbers" sind jetzt eine
governte, wissenschaftlich begründete Single-Source-of-Truth. Grundlage: Tiefenrecherche + 2-Runden-Verifikation
(`docs/research/parameter-initialisierung.md`).

| Commit | Inhalt |
|--------|--------|
| `19dfe2a` | Research-Doc: zitierte Karte aller 8 Parameter-Familien (Methode/Default/Referenz) — INFORM, OECD/JRC, SPC, GUM, ViEWS, SHELF, R₀ |
| `d6b6d65` | Governte Config `vmodel/project/scoring_thresholds.yaml` + Loader `scoring/scoring_thresholds.py` (gecacht, graceful Fallback); Anomalie + D-Status-Cutpoints verdrahtet. Anker SwR-021 |
| `e7ec45c` | Sensitivitäts-Tool `scripts/threshold_sensitivity.py` (OAT-Sweep, rankt Schwellen nach Skill-Einfluss) |
| `f156210` | d1_max-Fixture-Kalibrierung: Optimum-Plateau [0.05–0.30]; 0.20 gut platziert |
| `12d6d49` | **Restliche 6 Familien verdrahtet** (Daten-Suffizienz, Bayes, Fusion, Unsicherheit, Skill/Validierung, Info-Epi) — behavior-preserving; SwR-020/022/039/047 erweitert |
| `aa0ecae` | 2. Verifikationsrunde: SPC 3σ+WECO, GUM RSS+k, Brier-Skill-Score, SHELF, NATO-Admiralty **bestätigt**; R₀ uncertain |
| `69b9993` | **Erster echter Wert gesetzt:** Bayes-D3-Likelihood-Zentrum 0.65 → 0.75 (Band-Mittelpunkt, SHELF) |

**Stand:** 7/8 Familien live verdrahtet (lesen aus der Config, Fallback = Ist-Werte); nur die Multi-Domain-
S0–S6-Aggregation bleibt dokumentiert (`wired_to_config: false`). Vollsuite **1154 passed**. Jede Familie hat
`current`/`recommended_initial`/`rationale`/`reference`(/`applied`) im `governance_record`. AP-24-Akzeptanz erfüllt
(keine literalen Schwellen mehr in den 8 Modulen außer Struktur-Konstanten; Bindungstests in `test_scoring_thresholds.py`).

**Methodik der Wert-Wahl (wichtig):** Nur Werte setzen, für die die *bestätigte* Literatur eine *konkrete*,
*datenunabhängige* Vorgabe hat. Bisher genau einer: Bayes-D3 → Band-Mittelpunkt. D4 bleibt am Schwellen-Anker 1.0;
σ=0.2 bleibt bis Elicitation (Literatur gibt Prozess, keinen Wert). z=1.645 (Familie 6) ist bereits GUM-konform → keine Änderung nötig.

**Aufgeschoben — NICHT „auf gut Glück" setzen (Gates):**
- **An AP-30 (echte z-Score-Anomalien) gebunden:** Familie 1 D-Cutpoints → σ-Vielfache (1/2/3σ) + Bound→3σ +
  min_series_points→~20; Familie 4 σ-Kalibrierung; Familie 3 min_features→σ-Kopplung. Heute ändern bricht die
  Fixture-Validierung (Fixture-Scores sind keine echten z-Scores; d1_max-Sweep: ≥0.35 → Skill-Kollaps).
  → Sobald AP-30 läuft: `scripts/threshold_sensitivity.py` neu fahren + σ-Cutpoints/σ datenbasiert setzen.
- **Struktureller Umbau (AP-28):** Familie 7 Skill-Blend 0.6/0.4 → separate Standardmetriken (Brier, BSS vs.
  No-Skill-Baseline, POD/FAR/AUC/Lead-Time) — bestätigt (CAWCR), aber neue Berechnung statt eines Werts.
- **Struktureller Umbau:** Familie 8 Amplifikation 1.5× → R₀-/Wachstumsraten-Kriterium (R₀ war „uncertain").

**Offene Owner-Policy-Entscheidungen (literatur-vorbereitet, brauchen nur ein Ja):**
- **Familie 6 CI:** 90 % (z=1.645, aktuell, GUM-konform) vs. 95 % (z=1.96) — reine Konvention.
- **Familie 2 Aggregation:** S0–S6-Zähl-Regel beibehalten (nicht-kompensatorisch, vertretbar) vs. auf
  INFORM-artiges **geometrisches Mittel** + ROUNDUP-Cutpoints umstellen (prinzipientreuer, aber Verhaltensänderung).
- **Familie 5 Fusion:** 3-stufige Reliabilität (1.0/0.6/0.2) auf die **NATO-Admiralty-6-Stufen** mappen
  (bestätigt); konkrete 6 Gewichte bleiben Owner-Werturteil.

---

## 0. Update 2026-06-26 — Phase 0 (Korrektheit-Gate) abgeschlossen

| Commit | Inhalt |
|--------|--------|
| `9d4e269` | **AP-18** reale Anomalie `ALGO-ANOM-01` (z-Score über Fenster-Records, coverage-gewichtet, gekappt) — **Live-Pfad**; Replay-Pendant bewusst nach AP-26 verschoben |
| `44e4e74` | **AP-25** Fail-Loud `ALGO-RUNGATE-01` (7 Analytikstufen → explizite Degradationseinträge in artifact_status/Readiness, NICHT release-blockierend) |
| `f11d56b` | **AP-26 #8** Verankerung: StR-678..681 / SwR-084..087 / TC / `ALGO-REPLAY-TS-01` + Count-Sync (StR→681, SwR→87, TC→137; alle Invarianten 0); SwR-Count-Drift behoben (77→87) |
| `f50a9be` | **AP-26 Code** Replay-Status-Zeitreihe `ALGO-REPLAY-TS-01` (PIT-Tageszeitreihe via ALGO-ANOM-01, deterministisch, fail-loud) + per-Case-Artefakt (SwR-087) |

Arbeitsweise je Tranche: V-Model-Anker → RED/GREEN → targeted Tests → Full-Suite (1132 passed, nur vorbestehende/Umgebungs-Failures) → Fresh-Eyes-Verifikation (alle PASS, 0 blocking) → scoped Commit + Push.

**Owner-Entscheide (in dieser Session getroffen + dokumentiert):**
- AP-18-Anomalie = z-Score über Fenster-Records (Option A).
- AP-18-Replay-Site bewusst nach AP-26 verschoben; in AP-26 nutzt nur die **neue Zeitreihe** ALGO-ANOM-01, der **Legacy-Punktstatus bleibt Konstante** (`_DOMAIN_ANOMALY_SCORES`) bis AP-30 — verhindert S0-Kollaps der synthetischen Fixtures.
- #8 nur auf **AP-26 begrenzt**; AP-27..32 bleiben plan-reserviert (Verankerung je Phase).

**Bekannte Umgebungs-Failures (nicht Code-Regression, auf pristine HEAD identisch):** 5× `test_hf_export` + `test_ml_datasets` + `test_ap13_e2e` (fehlendes optionales `datasets`/`torch`); `test_storage_run_history` (Windows-Pfad-Separator); `test_validation_replay_depth_probe` (`case_count` 11≠4 wegen stale lokalem `build/`-Artefakt).

**Phase 1 (Instrument) — Fortschritt:**
- ✅ `9d7be21` **AP-16** Skill-Messharness `ALGO-SKILL-01` (`validation/skill_metrics.py`): Detektionsrate/Domain-Match/Skill-Score aus Replay-Reviews → `skill_metrics.json` + GUI-Skill-Score-KPI; Regressionstest. Anker SwR-039 (kein Count-Sync). Fehlalarm/Vorlauf/Brier → AP-28.
- ✅ `791a389` **AP-27** Ground-Truth-Redesign (Mechanik): `ValidationCase`-Schema (onset/trajectory/split/polarity, backward-kompatibel) + `validate_reference_case_library` (Onset-im-Fenster, Split/Polarity, Anti-Zirkularität) + **1 exemplarischer S0-Fall** `VAL-CHE-2024-NEGATIVE-001` (Vorlage). #8-Verankerung SwR-088..090/StR-682..684 + Count-Sync (StR→684, SwR→90, TC→140, alle Invarianten 0). **Echte Label-Kuratierung (welche S0-Negative, Onset-Daten) bleibt Owner-Hoheit.**

**Phase 1 abgeschlossen** — ✅ `749b18c` **AP-28** Skill-Metrik `ALGO-SKILL-02`: **Fehlalarmrate** (nur auf S0-Negativen), **No-Skill-Baseline** („immer S3") + `beats_baseline`, **Vorlaufzeit** (AP-26-Zeitreihe + Onset) und **Brier-Score** (S-Status-Proxy fürs Posterior). Reviews um polarity/onset/trajectory angereichert; neue Metriken in `skill_metrics.json` + GUI-Fehlalarm-KPI. #8-Verankerung SwR-091..094/StR-685..688/ALGO-SKILL-02 + Count-Sync (StR→688, SwR→94, alle Invarianten 0; die Probe fing 7 von der statischen Map verpasste Count-Assertions über 6 Dateien). Fresh-Eyes-Review (Algorithmus/V-Model/Blast-Radius) clean; Vollsuite 1161 passed. **Vorbehalt:** Zahlen werden erst mit echten Labels + AP-30 aussagekräftig (heute: 35 S3-Positive + 1 S0-Negativ-Vorlage).

---

## 1. Was diese Session getan hat (alle auf `origin`)

| Commit | Inhalt |
|--------|--------|
| `d2f7f20` | AP-26..32 „Validierung gegen echte Events" in Masterplan integriert (Dashboard, Backlog §3, Detail §4.D) + Begleitdoc |
| `a41bb49` | **AP-17** Slow-Layer Streuung/z-Score (std_7d/30d + `compute_zscore`/ALGO-ZSCORE-01) — **erledigt** |
| `b4dbd87` | pytest-xdist + `addopts = "-n auto"` (Suite-Parallelisierung) |
| `64ed813` | utf-8 Encoding-Fix (273 Stellen; Windows-cp1252-Bug; 33→6 Tests) |
| `e6e0ea3` | **StR-162..671 wiederhergestellt** (Regression aus `eda53ac`); 677 StR, 0 verwaiste Refs |

---

## 2. Arbeitsweise (Memory reist NICHT mit — hier verankert; Details: `AGENTS.md` + die 41 Projekt-Skills)

- **Kein Code ohne Anforderung (V-Model Phase D zuerst):** StR→SyR→SwR→TC in `vmodel/` verankern (+ `trace_links.yaml`, `implementation_file_links.yaml` + Stubs), bevor Code entsteht.
- **TDD:** RED (Test schlägt aus erwartetem Grund fehl) → GREEN (minimal) → Full-Suite.
- **Serielle Tranche:** ein gebündeltes Teilpaket → targeted Tests → Full-Suite → Masterplan/Matrix-Status nachziehen → **ein** scoped Commit + Push. Vorher `git pull --ff-only`.
- **Count-Sync:** beim Hinzufügen von Requirements `*_count`-Metadata UND hartkodierte Count-Assertions (mehrere Testdateien) anheben; mit `grep -c '^- id: SwR-'` verifizieren, nicht der Metadata vertrauen.
- **Pre-Commit-Verifikation** mit frischem Blick (kein Agent prüft eigene Arbeit).
- **Skills NICHT in den Masterplan schreiben** (ausdrückliche Nutzer-Vorgabe) — sie steuern das *Wie*, nicht den Inhalt.

## 2b. Tests schnell halten (wichtig — Memory reist nicht mit)
- venv: `.venv312` (Windows). Repo liegt auf **OneDrive** → Datei-I/O-Tests sind dort **sehr langsam**.
- Während TDD **nur betroffene Tests** (`pytest tests/unit/test_<modul>.py`, oft <1 s). Full-Suite **einmal** am Ende.
- Full-Suite parallel: `-n auto` (pytest-xdist ist dev-Dep). Lokal Temp aus OneDrive ziehen: `--basetemp=C:/Temp/siasa-pytest`.
- **Env-Preflight einmal vorab:** `pip install -e .[dev]` (pyarrow, duckdb, pytest-xdist); torch ist optionales `ml`-Extra (Test `test_ml_datasets.py` braucht es).

---

## 3. Offener Backlog (entspricht den Session-Tasks #1–#9; in Abhängigkeitsreihenfolge)

**Vorbedingung:**
- **AP-26..32 V-Model-Verankerung + Count-Sync** (#8) — reiner Planning-Commit (StR/SyR/SwR/TC/trace_links/implementation_file_links + Stubs + ALGO-IDs governt) VOR dem ersten Code von AP-26/27. Enthält auch den SwR-Count-Drift-Fix (s.u.).

**Phase 0 (Korrektheit-Gate):** AP-17 ✅ erledigt · **AP-18** (reale Anomalie, ersetzt Konstante `live_runtime.py:760`) · AP-25 (Fail-Loud) · **AP-26** (Status-Zeitreihe im Replay, #1).
**Phase 1 (Instrument):** AP-16 (Skill-Harness) · **AP-27** (Ground-Truth-Redesign, S0-Negative, #2) · **AP-28** (Skill-Metrik + No-Skill-Baseline, #3).
**Phase 2 (echte Daten):** **AP-29** (Event-Set, #4) → **AP-30** (Backfill GDELT/GDACS/WB + PIT, größter Block, #5) → **AP-31** (Provenance real vs fixture, #6).
**Phase 3:** **AP-32** (End-to-End-Validierung + Skill-Report, #7).
**Phase 4 (nach Validierung):** AP-19/20/21/22/24.

Detail: `docs/plans/siasa-master-plan.md` (§3 Backlog, §4.C/§4.D) · `docs/plans/AP-26-32-validierung-gegen-echte-events.md` · `docs/plans/AP-16-25-analytischer-kern-arbeitspakete.md`.

---

## 4. Bekannte Fehler / Audit-Lücken (Stand V-Model-Audit 2026-06-25)

**Strukturell (Traceability ist nach dem StR-Restore gesund: 677 StR, 0 verwaiste Refs, SwR→TC 83/83, Slices 12/12 closed):**
1. **SwR-Count-Drift:** ~~metadata 77 vs real 83~~ — **behoben in #8 (`f11d56b`):** `software_requirement_count` = 87 (real 87, nach AP-26 SwR-084..087).
2. **3 Verifikations-Routen-Lücken:** `verification stop_criteria` 3× False — **SyR-051/052/053** ohne Routen-Klassifikation/System-TC + 3 StR ohne Verifikationsroute. Nuance: SyR-051/052/053 werden von SwR-063 abgeleitet, der Klassifizierer erkennt sie aber nicht als software-route. Pre-existing AP-03-Gap.
3. **Cluster B:** `stakeholder_e2e_ui_smoke`-Gate scheitert **lokal**, weil `build/run_artifacts/`-Bundle fehlt (gitignored) → 1 roter Test lokal (`test_release_failure_drill...detects_expected_failure_modes`). Auf CI (Bundle vorhanden) voraussichtlich grün. Fix-Option: ui_smoke-Readmodel/Test härten (fehlendes Bundle = expliziter Preflight-Skip statt stillem Gate-Fail).

**Funktional (die eigentliche offene Baustelle — Kette verdrahtet, Code noch nicht „richtig"):**
- F1: `anomaly_score` ist Konstante (`live_runtime.py:760`) → AP-18.
- F14/F15/F16: synthetische Eventdaten, degenerierte Labels (kein S0), Punktstatus statt Zeitreihe → AP-27/30/31/26.
- Vom Analytik-Kern ist nur AP-17 erledigt; AP-16, AP-18–AP-32 offen.

---

## 5. Gotchas (nicht erneut reintreten)
- **`eda53ac` löschte 510 StR** (StR-162..671) und ließ 528 Referenzen verwaisen → in `e6e0ea3` wiederhergestellt. **Nicht erneut löschen.** Bei künftigen StR-Änderungen Cross-Check gegen `trace_links.yaml`/`system_requirements.yaml`/`stakeholder_e2e_flows.yaml`.
- **AP-ID-Namespace:** Master-Plan-`AP-NN` ≠ Ledger-`AP-NN` der `siasa-capability-fulfillment-matrix.md` (eigene Operability-Serie). Nie über die nackte Nummer referenzieren.
- **Encoding:** Text-Datei-I/O immer mit `encoding="utf-8"` (Windows-Default ist cp1252).
- **Datei-Encoding** der `vmodel/`-YAMLs: UTF-8 mit **CRLF** — bei Skripten erhalten.

---

## 6. Empfohlener nächster Schritt
Phase 0 + **Phase 1 vollständig** (AP-16/26/27/28) + **AP-29** (Mechanik `2abbd02` + **erste Kuratierung v1** `aa01f09`: 3 gematchte Real-Event-Paare nach `docs/plans/event-set-curation-procedure.md`, alle Onsets/Kontrollen quellenverifiziert, `ratification_status: proposed`) sind abgeschlossen. **Nächster Schritt: AP-30** (historischer Backfill GDELT/GDACS/WB + Point-in-Time — **größter Block, hohes Risiko**: API-Zugänge, Volumen, Schema-Mapping, Quellzitierung; braucht AP-13 DailyAligner/PIT) → AP-31 → AP-32. Erst echte Daten machen die AP-28-Skill-Zahlen **und** die an AP-30 gebundenen AP-24-Schwellen (s. §⭐) aussagekräftig. **Owner-Vorbedingungen:** (a) die kuratierte v1 **ratifizieren** (3 Paare gegen Primärquellen prüfen; ggf. Kontrollen durch Vor-Onset-Fenster derselben Länder ersetzen) und (b) für AP-30 Fallauswahl + Daten-Lizenz/Quellzitierung + API-Zugänge bereitstellen. Alternativ ohne Owner-Input: Audit-Restpunkte aus §4 (3 Verifikations-Routen SyR-051/052/053; Cluster-B-Lokalgate) oder die AP-24-Owner-Policy-Entscheidungen (§⭐).
