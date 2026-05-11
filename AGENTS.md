# AGENTS.md

## Mission
Develop SIASA requirements-driven from the governed artifacts in this repository.

## Project meaning
SIASA = Structural Information & Activity Space Analysis under Uncertainty.
The project is a country-centric analytical system for structured assessment of global information and activity spaces under uncertainty.

## Non-negotiable rules
1. Work requirements-driven.
2. Keep traceability between requirements, methods, algorithms, code, tests, runs, and reports.
3. Develop tests with implementation.
4. Work in small, reviewable steps.
5. Prefer simple, explainable logic in V1/MVP.
6. Preserve separation of source catalog, raw data, normalized data, features, domain status, multi-domain status, snapshots, annotations, and reports.
7. If requirements are missing, contradictory, or unclear, document the gap before implementation.
8. Respect not only requirements, but also non-goals, decisions, assumptions, risks, principles, system boundaries, use cases, roles, acceptance criteria, traceability model, and validation model.
9. Do not introduce a naive global additive instability score across domains A-E unless requirements are explicitly changed.
10. Treat uncertainty, coverage, confidence, source dependency, and data sufficiency as first-class artifacts.

## Source-of-truth areas
- `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` as raw stakeholder source input
- `vmodel/requirements/`
- `vmodel/project/`
- `vmodel/architecture/`
- `vmodel/method/`
- `vmodel/verification/`
- `vmodel/traceability/`
- `docs/imports/stakeholder_workbook_analysis.md`
- `README.md`

## Required contextual artifacts to respect
- non-goals
- decisions
- domain model A-E
- data source catalog and access constraints
- MVP country set and priorities P1/P2/P3
- status models D0-D5 and S0-S6
- feature catalog
- GUI pages and role model
- reports/exports
- data run strategy and annotation model
- configuration tables
- acceptance criteria
- assumptions and risks
- governance and ethics principles
- system boundaries
- glossary and validation model

## Traceability conventions
- `StR-*` stakeholder requirements
- `SyR-*` system requirements
- `SwR-*` software requirements
- `DDS-*` design decisions / software design items
- `TC-*` test cases
- `ATC-*` acceptance test cases
- `NG-*` non-goals
- `AC-*` acceptance criteria
- `AS-*` assumptions
- `R-*` risks
- `D-*` project decisions
- `DG-*` / `EP-*` governance and ethics principles
- `UC-*` use cases

## Definition of done
A work item is done only if:
- implementation exists where required
- traceability exists
- tests exist / were updated
- relevant checks passed
- documentation was updated
- affected context artifacts were checked for consistency
