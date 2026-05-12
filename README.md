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
- `vmodel/traceability/implementation_file_links.yaml`
- `src/siasa/traceability/consistency.py`

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

## Nächste sinnvolle Schritte

1. Governed Traceability-Slices über weitere Requirement-Bereiche ausweiten.
2. Maschinell berechenbaren Closure-Status pro Requirement aus Requirements, Trace-Links, Datei-/Test-Zuordnung und Testergebnissen ableiten.
