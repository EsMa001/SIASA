# AGENTS.md

## Mission
Develop SIASA requirements-driven from the governed artifacts in this repository.

## Non-negotiable rules
1. Work requirements-driven.
2. Keep traceability between requirements, algorithms, code, and tests.
3. Develop tests with implementation.
4. Work in small, reviewable steps.
5. Prefer simple, explainable logic in V1.
6. Preserve separation of raw data, features, scores, and presentation / outputs where applicable.
7. If requirements are missing or unclear, document the gap before implementation.

## Source-of-truth areas
- `vmodel/requirements/`
- `vmodel/change/`
- `vmodel/architecture/`
- `vmodel/verification/`
- `vmodel/traceability/`
- `README.md`

## Traceability conventions
- `StR-*` stakeholder requirements
- `SyR-*` system requirements
- `SwR-*` software requirements
- `DDS-*` design decisions / software design items
- `TC-*` test cases
- `ATC-*` acceptance test cases

## Definition of done
A work item is done only if:
- implementation exists
- traceability exists
- tests exist / were updated
- relevant checks passed
- documentation was updated
