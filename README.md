# SIASA

Structural Information & Activity Space Analysis under Uncertainty.

SIASA ist ein V-Model-light / requirements-as-code Repository mit importierter Stakeholder-Baseline aus der Arbeitsmappe `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx`.

## Aktueller Stand

- 668 importierte Stakeholder Requirements in `vmodel/requirements/stakeholder_requirements.yaml`
- importierte Projektkontext-Artefakte unter `vmodel/project/`, `vmodel/architecture/`, `vmodel/method/`, `vmodel/verification/` und `vmodel/traceability/`
- lesbare Spiegelung unter `docs/`
- funktionaler Python-Kern für Katalog, Adapter, Raw/Normalized Data, Features, Statuslogik, Snapshots, Reporting, Governance, Validation und Reprocessing
- lokal ausführbare MVP-GUI-Baseline als statische HTML-Site unter `src/siasa/gui/local_app.py`

## Wichtige Einstiege

- `docs/imports/stakeholder_workbook_analysis.md`
- `docs/project/stakeholder_requirements_overview.md`
- `vmodel/requirements/stakeholder_requirements.yaml`
- `vmodel/verification/acceptance_criteria.yaml`
- `vmodel/project/data_sources.yaml`
- `vmodel/project/mvp_countries.yaml`
- `vmodel/method/feature_catalog.yaml`

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
- `docs/` – lesbare Spiegelung und Importanalyse

## Lokale GUI starten

Demo-Site generieren:

`PYTHONPATH=src /opt/hermes/.venv/bin/python -m siasa.gui.local_app --output-dir build/local_gui`

oder über den Paket-Entry-Point nach Installation:

`siasa-local-gui --output-dir build/local_gui`

Danach `build/local_gui/index.html` im Browser öffnen.

Die MVP-GUI-Baseline deckt die Kernseiten aus den Anforderungen ab:
- World Anomaly Map / Global Overview
- Country Profile
- Domain Detail
- Source / Coverage View
- Report / Export View
- System Status / Runs

## Nächste sinnvolle Schritte

1. GUI-Baseline an persistierte Run-/Snapshot-Artefakte anbinden statt Demo-Daten.
2. Current Events, Yearly Trend und Validation/Backtest Views ergänzen.
3. Traceability- und Exportpfade bis GUI-Interaktionen durchziehen.
4. Weitere Stakeholder-Anforderungen iterativ über System-/Software-/Test-Artefakte schließen.
