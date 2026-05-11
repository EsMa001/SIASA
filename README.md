# SIASA

Structural Information & Activity Space Analysis under Uncertainty.

SIASA ist ein V-Model-light / requirements-as-code Repository mit importierter Stakeholder-Baseline aus der Arbeitsmappe `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx`.

## Aktueller Stand

- 668 importierte Stakeholder Requirements in `vmodel/requirements/stakeholder_requirements.yaml`
- importierte Projektkontext-Artefakte unter `vmodel/project/`, `vmodel/architecture/`, `vmodel/method/`, `vmodel/verification/` und `vmodel/traceability/`
- lesbare Spiegelung unter `docs/`

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

## Nächste sinnvolle Schritte

1. Stakeholder Requirements in System Requirements schneiden.
2. Software Requirements für Datenzugang, Normalisierung, Status Engine, GUI und Reporting ableiten.
3. Validatoren und Trace-Matrix-Generator anlegen.
4. Erstes lauffähiges End-to-End-Arbeitspaket implementieren.
