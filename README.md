# SIASA

SIASA ist ein neues Projekt-Repository mit V-Model-light / requirements-as-code Grundgeruest.

## Ziel der Initialstruktur

Dieses Repository enthaelt die minimal notwendige Grundstruktur fuer:
- Stakeholder Requirements
- System Requirements
- Software Requirements
- Change Requests
- Architekturartefakte
- Verifikationsartefakte
- Traceability
- Python-Implementierung unter `src/`
- Tests auf mehreren Ebenen

## Verzeichnisstruktur

- `src/siasa/` – Python-Paket
- `tests/` – unit / integration / system / acceptance
- `tools/` – Validierungs- und Hilfsskripte
- `prompts/` – Prompts fuer kontrollierte Agent-/Coding-Workflows
- `vmodel/` – Requirements, Change, Architektur, Verification, Traceability, Baselines
- `.github/workflows/` – CI

## Naechste sinnvolle Schritte

1. Stakeholder Requirements konkretisieren
2. Validatoren und Matrixgenerator anlegen
3. CI aktivieren
4. erstes Beispiel `StR -> SyR -> SwR -> Test -> Code` durchziehen
