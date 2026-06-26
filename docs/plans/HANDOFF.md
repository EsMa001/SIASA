# SIASA — Session-Handoff (Stand 2026-06-26)

> Zweck: Diese Datei trägt den **handlungsrelevanten Kontext** einer vorherigen Claude-Code-Session
> auf einen anderen Rechner (CLI-Sessions/Memory/Tasks synchronisieren NICHT über Geräte — nur Git tut das).
> Auf dem anderen Rechner: `git pull` + frische `claude`-Session + diese Datei lesen.

Branch: `hermes/repo-scaffold` (= Main-Branch des Projekts; Commits gehen direkt hierauf).

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

**Letzte offene Phase-1-Baustelle: AP-28** (Skill-Metrik `ALGO-SKILL-02`) — erweitert ALGO-SKILL-01 um **Fehlalarmrate** (auf den S0-Negativen aus AP-27), **No-Skill-Baseline** („immer S3"), **Vorlaufzeit** (aus AP-26-Zeitreihe + Onset) und **Brier-Score**. Entsperrt (braucht AP-16 ✅, AP-26 ✅, AP-27 ✅). Trace: SwR-091..094 / StR-685..688 / ALGO-SKILL-02 (#8-Verankerung wie AP-26/27). Detail: Masterplan §4.D.

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
Phase 0 + AP-16 + AP-27 sind abgeschlossen (s. §0). Letzte offene Phase-1-Baustelle ist **AP-28** (Skill-Metrik `ALGO-SKILL-02`): erweitert die AP-16-Skill-Metrik um Fehlalarmrate (auf den AP-27-S0-Negativen), No-Skill-Baseline („immer S3"), Vorlaufzeit (AP-26-Zeitreihe + Onset) und Brier-Score; mit #8-Verankerung (SwR-091..094/StR-685..688/ALGO-SKILL-02 + Count-Sync, gleiche Mechanik wie AP-26/27). Danach Phase 2 (AP-29→30→31→32, echte Daten — größter Block AP-30). Alternativ offene Audit-Restpunkte aus §4 (3 Verifikations-Routen SyR-051/052/053; Cluster-B-Lokalgate). Hinweis: bevor AP-28 echte Fehlalarm-/Vorlauf-Zahlen liefert, sollte der Owner den echten S0-Negativ-/Onset-Labelsatz kuratieren (AP-27 lieferte nur die Mechanik + 1 Beispiel).
