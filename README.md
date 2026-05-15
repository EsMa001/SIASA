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

oder nach Installation:

`siasa-live-runtime --country-id UKR --country-id POL --run-id RUN-LIVE-MULTI-001 --output-dir build/run_artifacts/latest`

Aktueller Runtime-Stand:
- der Runtime-Pfad unterstützt jetzt Single- und Multi-Country-Runs für die aktuell freigegebenen Live-Pilot-Länder `UKR`, `POL`, `ISR`, `TWN`
- wiederhole `--country-id`, um mehrere Länder in einem Run zu verarbeiten
- der Pilot ersetzt die bisherigen rein synthetischen `SRC-A` / `SRC-B` Latest-Artefakte durch reale Source-IDs (`WB-INDICATORS`, `SRC-GDELT-DOC`, `SRC-GDELT-EVENTS`, `SRC-GDACS`)
- reale Multi-Country-Runs bleiben quellenabhängig: einzelne Sources können weiterhin partiell fehlschlagen und als `partial_success` im Bundle erscheinen
- der governed Live-Runtime-Pfad erzeugt jetzt zusätzlich `readmodels/validation_backtest.json` als transparenten `runtime_support_check`; diese Sicht ist explizit keine historische Referenzfall-Backtest-Wertung
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
