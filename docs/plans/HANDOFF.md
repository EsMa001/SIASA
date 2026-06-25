# SIASA — Session-Handoff (Stand 2026-06-25)

> Zweck: Diese Datei trägt den **handlungsrelevanten Kontext** einer vorherigen Claude-Code-Session
> auf einen anderen Rechner (CLI-Sessions/Memory/Tasks synchronisieren NICHT über Geräte — nur Git tut das).
> Auf dem anderen Rechner: `git pull` + frische `claude`-Session + diese Datei lesen.

Branch: `hermes/repo-scaffold` (= Main-Branch des Projekts; Commits gehen direkt hierauf).

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
1. **SwR-Count-Drift:** `software_requirements.yaml` metadata `software_requirement_count: 77`, real **83** (kosmetisch; Tests prüfen 83). Beim nächsten Requirements-Schritt mit-anheben (in #8 vorgesehen).
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
Entweder **#8 (V-Model-Verankerung + Count-Sync)** als Planning-Commit (entsperrt AP-26/27 und behebt den SwR-Drift), **AP-18** (reale Anomalie — direkter funktionaler Hebel, baut auf AP-17 auf), oder die **3 Verifikations-Routen** (SyR-051/052/053) schließen. Mit dem Nutzer abstimmen.
