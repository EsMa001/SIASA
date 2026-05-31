# SIASA

Structural Information & Activity Space Analysis under Uncertainty.

SIASA ist ein V-Model-light / requirements-as-code Repository mit importierter Stakeholder-Baseline aus der Arbeitsmappe `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx`.

## Aktueller Stand

- 668 importierte Stakeholder Requirements in `vmodel/requirements/stakeholder_requirements.yaml`
- importierte Projektkontext-Artefakte unter `vmodel/project/`, `vmodel/architecture/`, `vmodel/method/`, `vmodel/verification/` und `vmodel/traceability/`
- lesbare Spiegelung unter `docs/`
- funktionaler Python-Kern für Katalog, Adapter, Raw/Normalized Data, Features, Statuslogik, Snapshots, Reporting, Governance, Validation, Reprocessing und bidirektionale Traceability-Konsistenzchecks
- automatisierte Persistierung von Run-/Snapshot-/Report-/Read-Model-Artefakten in die GUI-kompatible Struktur `build/run_artifacts/latest`
- reale Exportdateien (`.md`, `.json`) pro Report unter `build/run_artifacts/latest/exports/` inklusive Download-Links in der lokalen GUI
- Validation-/Backtest-View als lokale GUI-Seite mit optionalem Artefakt-Load aus `readmodels/validation_backtest.json`
- Traceability-/Lineage-View als lokale GUI-Seite mit optionalem Artefakt-Load aus `readmodels/traceability_lineage.json`
- Analyst-Annotations-View als lokale GUI-Seite mit optionalem Artefakt-Load aus `readmodels/annotations.json`
- browser-lokaler Annotation-Workflow in der GUI mit Create/Edit/Filter/History-Flow, Quick-Links aus Country-/Domain-Seiten und JSON-Export für governed Persistierung
- analystenfreundliche Baseline-/Historical-Comparison-Summaries auf Trend- und Domain-Seiten für schnellere Interpretation von Delta, Peak und Verlaufskontext
- Traceability-/Lineage-Sicht jetzt zusätzlich mit Source-Dependency-Cluster-Kandidaten und expliziter Source-Origin-Groundwork-Tabelle als artefaktbasiertem Ausgangspunkt für spätere Herkunfts-/Ausbreitungsanalyse
- Readiness-Sicht jetzt zusätzlich mit einer expliziten Artifact Readiness Summary, damit Präsenz/Abwesenheit von `validation_backtest`, `traceability_lineage`, `repo_closure` und `annotations` sichtbar bleibt und nicht nur indirekt über Known Gaps erschlossen werden muss
- Demo-/Release-Readiness-View als lokale GUI-Seite inklusive Checklisten und `readiness.json`-Artefakt
- lokal ausführbare MVP-GUI-Baseline als statische HTML-Site unter `src/siasa/gui/local_app.py`

## Wichtige Einstiege

- `docs/imports/stakeholder_workbook_analysis.md`
- `docs/project/stakeholder_requirements_overview.md`
- `vmodel/requirements/stakeholder_requirements.yaml`
- `vmodel/verification/acceptance_criteria.yaml`
- `vmodel/project/data_sources.yaml`
- `vmodel/project/mvp_countries.yaml`
- `vmodel/method/feature_catalog.yaml`
- `vmodel/traceability/trace_links.yaml`
- `vmodel/traceability/implementation_file_links.yaml` – aktuell mit governed Slices `baseline-and-status-engines`, `catalog-and-ingestion-foundation`, `feature-computation-foundation`, `gui-readmodels-and-annotations`, `governance-and-run-controls`, `normalization-and-mapping`, `reporting-and-export`, `snapshot-and-lineage` und `validation-and-backtest`
- `src/siasa/traceability/consistency.py` – Slice-Closure und repoweite Closure-Aggregation (`build_requirement_closure_report`, `build_repo_closure_report`)
- `src/siasa/runs/reprocessing.py`
- `tests/unit/test_traceability_consistency.py`

## Verzeichnisstruktur

- `src/siasa/` – Python-Paket
- `tests/` – unit / integration / system / acceptance
- `tools/` – Validierungs- und Hilfsskripte
- `prompts/` – Prompts fuer kontrollierte Agent-/Coding-Workflows
- `vmodel/requirements/` – kanonische Requirements
- `vmodel/project/` – Projektkontext, Entscheidungen, Risiken, Quellen, Rollen, Laenderset
- `vmodel/architecture/` – Domänen, GUI-Seiten, Systemgrenzen
- `vmodel/method/` – Statusmodelle und Feature-Katalog
- `vmodel/verification/` – Akzeptanzkriterien und Validierungsmodell
- `vmodel/traceability/` – Traceability-Artefakte und Traceability-Zielmodell
- `src/siasa/traceability/` – Runtime-Lineage und bidirektionale Traceability-Consistency-Checks
- `docs/` – lesbare Spiegelung und Importanalyse

## Lokale GUI starten

Demo-Site generieren:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.gui.local_app --output-dir build/local_gui`

Persistierte Artefakte verwenden:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.gui.local_app --output-dir build/local_gui --artifacts-dir build/run_artifacts/latest`

Governed live-source runtime erzeugen:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.live_runtime --country-id UKR --country-id POL --run-id RUN-LIVE-MULTI-001 --output-dir build/run_artifacts/latest`

oder als repräsentatives Pilot-Subset:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.live_runtime --pilot-set representative --run-id RUN-LIVE-REP-001 --output-dir build/run_artifacts/latest`

oder als breiteres Core-Focus-Subset:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.live_runtime --pilot-set core-focus-broader --run-id RUN-LIVE-CORE-BROAD-001 --output-dir build/run_artifacts/latest`

oder als vollständiges aktuelles Core-Focus-Subset:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.live_runtime --pilot-set core-focus-complete --run-id RUN-LIVE-CORE-COMPLETE-001 --output-dir build/run_artifacts/latest`

oder nach Installation:

`siasa-live-runtime --country-id UKR --country-id POL --run-id RUN-LIVE-MULTI-001 --output-dir build/run_artifacts/latest`

Standard-Workflow fuer persistiertes `latest/` (AP-F05):

Linux/macOS:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/build_operational_latest_bundle.py --run-id RUN-LIVE-LATEST-001 --artifacts-dir build/run_artifacts/latest --gui-output-dir build/local_gui/latest --history-db build/run_history/latest_runs.sqlite`

Windows/PyCharm (PowerShell im Projekt-Root):

`$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe .\scripts\build_operational_latest_bundle.py --run-id RUN-LIVE-LATEST-001 --artifacts-dir build/run_artifacts/latest --gui-output-dir build/local_gui/latest --history-db build/run_history/latest_runs.sqlite`

Verifikation des `latest/` Bundles:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/verify_latest_bundle.py --artifacts-dir build/run_artifacts/latest`

Run-History (AP-N05) abfragen:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/query_run_history.py --history-db build/run_history/latest_runs.sqlite --limit 5`

Quellenstatus eines konkreten Runs:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/query_run_history.py --history-db build/run_history/latest_runs.sqlite --run-id RUN-LIVE-LATEST-001`

Domain-Score-Zeitreihe fuer ein Land:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/query_run_history.py --history-db build/run_history/latest_runs.sqlite --country UKR --domain A`

Aktuellste Domain-Scores fuer ein Land:

`PYTHONPATH=src /opt/hermes/.venv/bin/python scripts/query_run_history.py --history-db build/run_history/latest_runs.sqlite --country UKR`

Scheduler fuer taegliche automatische Runs starten (Linux/macOS):

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.scheduler --repo-root . --interval-hours 24 --pilot-set extended-focus-complete --artifacts-dir build/run_artifacts/latest --gui-output-dir build/local_gui/latest --history-db build/run_history/latest_runs.sqlite --log-file build/scheduler/scheduler.log`

Windows/PyCharm (PowerShell im Projekt-Root):

`$env:PYTHONPATH="src"; .\.venv\Scripts\python.exe -m siasa.runs.scheduler --repo-root . --interval-hours 24`

Optional mit Webhook-Alerting bei Fehlern:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.runs.scheduler --repo-root . --interval-hours 24 --alert-webhook https://hooks.example.com/siasa-alert`

Aktueller Runtime-Stand:
- der Runtime-Pfad unterstützt jetzt Single- und Multi-Country-Runs für die aktuell freigegebenen Live-Pilot-Länder `UKR`, `POL`, `ISR`, `TWN`, `RUS`, `CHN`, `IND`, `IRN`, `TUR`, `PAK`, `GEO`
- wiederhole `--country-id`, um mehrere Länder in einem Run zu verarbeiten
- alternativ wähle ein named `--pilot-set`:
  - `representative` = `UKR`, `POL`, `ISR`, `TWN`
  - `core-focus-initial` = `UKR`, `RUS`, `CHN`, `TWN`, `ISR`, `POL`
  - `core-focus-expanded` = `UKR`, `RUS`, `CHN`, `TWN`, `ISR`, `IND`, `POL`
  - `core-focus-broader` = `UKR`, `RUS`, `CHN`, `TWN`, `IRN`, `ISR`, `TUR`, `IND`, `POL`
  - `core-focus-complete` = `UKR`, `RUS`, `CHN`, `TWN`, `IRN`, `ISR`, `TUR`, `IND`, `PAK`, `GEO`, `POL`
- der Pilot ersetzt die bisherigen rein synthetischen `SRC-A` / `SRC-B` Latest-Artefakte durch reale Source-IDs (`WB-INDICATORS`, `SRC-GDELT-DOC`, `SRC-GDELT-EVENTS`, `SRC-GDACS`)
- reale Multi-Country-Runs bleiben quellenabhängig: einzelne Sources können weiterhin partiell fehlschlagen und als `partial_success` im Bundle erscheinen
- der governed Live-Runtime-Pfad erzeugt jetzt zusätzlich `readmodels/validation_backtest.json` als transparenten `runtime_support_check`; diese Sicht ist explizit keine historische Referenzfall-Backtest-Wertung, enthält jetzt aber eine fallübergreifende Portfolio-Summary über alle im Run validierbaren Länder, eine kuratierte Reference-Case-Library aus dem Repo, erste historische Reference-Review-/Evidence-Scoring-Felder für diese kuratierten Fälle und eine erste echte Replay-Schicht mit gemischter Basis: zwei Fälle (`VAL-UKR-2022-001`, `VAL-POL-2023-001`) laufen jetzt als `provider_backed_archival_replay` über governed Archiv-Inputs aus `validation_archival_replay_manifest.yaml`, während `VAL-ISR-2023-001` und `VAL-TWN-2024-001` vorerst explizit fixture-backed bleiben
- Country-Profile- und GUI-Sichten machen jetzt Priority Class, Selection Type, Source Depth und Domain Gaps pro Land explizit sichtbar
- `readmodels/system_status.json` enthält jetzt zusätzlich `country_coverage_visibility` mit Priority-Summary, Source-Depth-Bands, expliziten Country/Domain-Gap-Listen und einer aggregierten `remediation_watchlist` inklusive `priority_rank`/`priority_score` für Overview- und Coverage-Aggregationen
- die Startseite bietet jetzt einen `Priority Filter` sowie aggregierte Coverage-/Gap-Summaries; die Coverage-Ansicht zeigt zusätzlich eine `Country Coverage / Gap Matrix` mit Missing-Domain-Badges und eine priorisierte `Remediation Watchlist` mit Guidance-/Evidence-Links
- die Annotations-Sicht bietet jetzt zusätzlich einen browser-lokalen Create/Edit/Filter/History-Workflow mit Quick-Links aus Country-/Domain-Seiten und JSON-Export der Draft-Annotationen
- Missing Domains werden jetzt zusätzlich mit expliziten Ursacheinträgen ausgewiesen, z. B. `source_failed_this_run`, `no_usable_input_data` oder `not_configured_for_runtime`, inklusive zugehöriger Source-IDs
- optionale Artefaktlücken werden im Runtime-Bundle jetzt mit expliziten Gründen im `system_status.json` unter `artifact_status` codiert, z. B. `not_configured` oder `no_usable_input_data`

Die Artefaktstruktur wird durch den Python-Orchestrator automatisch geschrieben, wenn `DailyRunOrchestrator(..., artifacts_output_dir=Path("build/run_artifacts/latest"))` gesetzt ist.

oder über den Paket-Entry-Point nach Installation:

`siasa-local-gui --output-dir build/local_gui --artifacts-dir build/run_artifacts/latest`

Erwartete Artefaktstruktur unter `--artifacts-dir`:
- `snapshot.json`
- `readmodels/world_map.json`
- `readmodels/country_profiles/*.json`
- `readmodels/domain_details/*.json`
- `readmodels/source_coverage.json`
- `readmodels/system_status.json`
- `readmodels/validation_backtest.json`
- `readmodels/repo_closure.json`
- `readmodels/annotations.json`
- `reports/*.json`

Ohne `--artifacts-dir` verwendet die GUI weiterhin die Demo-Daten.

Danach `build/local_gui/index.html` im Browser öffnen.

Die MVP-GUI-Baseline deckt die Kernseiten aus den Anforderungen ab:
- World Anomaly Map / Global Overview
- Country Profile
- Domain Detail
- Source / Coverage View
- Report / Export View
- System Status / Runs
- Demo / Release Readiness

## Nächste sinnvolle Schritte

1. Repo-Closure-Details zusätzlich in einer dedizierten Traceability-/Governance-Sicht oder als Exportdatei pro Run aufschlüsseln.
2. Controlled reprocessing in Artefakt-/GUI-Statuspfade weiter durchziehen, falls daraus ein eigener Sichtbarkeits-Slice werden soll.
