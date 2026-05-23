# SIASA Release Go/No-Go Runbook

Ziel: Ein reproduzierbares, evidenzbasiertes Go/No-Go-Protokoll vor Demo/Release.

## 1) Pflicht-Eingänge

- `readiness`-Bewertung (Demo- und Release-Verdikt)
- `release_gate`-Bewertung (explizites Go/No-Go + Blocker)
- `traceability_integrity`-Bewertung (globaler Integritätszustand)
- `stakeholder_functional_closure`-Bewertung (19-ID-Focus-Cluster)
- `stakeholder_e2e_flow_coverage`-Bewertung (AP-04 Rollen-/Flow-Abdeckung)

Diese Artefakte werden maschinenlesbar erzeugt und im Evidence Pack dokumentiert.

## 2) CI-Gate (verbindlich)

CI führt aus:
- `PYTHONPATH=src python scripts/ci_release_gate_check.py`
- `PYTHONPATH=src python scripts/ci_stakeholder_closure_check.py`
- `PYTHONPATH=src python scripts/ci_stakeholder_e2e_flow_coverage_check.py`

Regel:
- `gate_verdict == "go"` -> Release-Gate-Schritt erfolgreich
- Stakeholder-Closure-Focus-Cluster vollständig (`covered_count=19`, `not_implemented_count=0`)
- AP-04 E2E-Flow-Gate vollständig (`flow_gap_count=0`, keine fehlenden Evidence-/Requirement-Refs, alle Stop-Kriterien pass)
- sonst -> CI-Schritt fehlschlagen (`no_go` oder Flow-/Closure-Gap blockiert Merge/Release)

## 3) Evidence Pack erzeugen

Lokal oder in CI:
- `PYTHONPATH=src python scripts/build_release_evidence_pack.py --output-dir build/release_evidence/latest`

Output:
- `build/release_evidence/latest/release_evidence_pack.json`
- `build/release_evidence/latest/release_evidence_pack.md`

## 4) Go/No-Go Entscheidungsvorlage

Entscheidungsregel:
- Go, wenn gleichzeitig:
  - `release_gate.gate_verdict == "go"`
  - `release_gate.blocker_count == 0`
  - `readiness.release_verdict == "ready"`
  - `traceability_integrity.summary.unhealthy_slice_count == 0`
  - `traceability_integrity.summary.closure_at_risk == 0`
  - `stakeholder_functional_closure.focus_gap_cluster.not_implemented_count == 0`
  - `stakeholder_e2e_flow_coverage.summary.flow_gap_count == 0`

Sonst:
- No-Go mit expliziten Blockern aus `release_gate.blockers`.

## 5) Protokoll-Template (manuell)

- Datum/Zeit (UTC):
- Commit SHA:
- Branch:
- Gate Verdict (`go|no_go`):
- Blocker Count:
- Blocker:
- Release Verdict:
- Demo Verdict:
- Traceability unhealthy slices:
- Traceability closure at risk:
- Stakeholder functional focus open IDs:
- Stakeholder E2E flow gaps:
- Entscheidung: Go / No-Go
- Nächste Maßnahme:

## 6) Failure Drill (verbindlich vor Release)

Ziel: Nachweisen, dass Governance im Fehlerfall wirklich auf `no_go` kippt und nicht nur im Happy Path grün ist.

Ausführung:
- `PYTHONPATH=src python scripts/release_failure_drill_check.py`
- optional Artifact-Pack für Review/UI-Nachweis:
  - `PYTHONPATH=src python scripts/build_release_failure_drill_pack.py --output-dir build/release_failure_drill/latest`
- optional GUI-Szenario-Bundles für visuelle Ready/No-Go-Prüfung:
  - `PYTHONPATH=src python scripts/build_release_failure_drill_gui_samples.py --output-dir build/release_failure_drill/gui_samples`

Geprüfte Negativ-Szenarien:
- synthetischer Known-Gap (`known_gaps_clear` muss als Blocker erscheinen, Gate = `no_go`)
- traceability closure risk (`traceability_integrity_clean` muss als Blocker erscheinen, Gate = `no_go`)
- geöffneter Stakeholder-Focus-Cluster (Readiness-Index-Gate `stakeholder_functional_focus_cluster_closed` muss fehlschlagen)
- geöffnete Stakeholder-E2E-Flow-Abdeckung (Readiness-Index-Gate `stakeholder_e2e_flows_covered` muss fehlschlagen)

Regel:
- Script-Exitcode `0` nur wenn alle Drill-Checks wie erwartet greifen.
- Script-Exitcode `!=0` blockiert Release bis Ursache korrigiert ist.

## 7) Hinweise

- Das Gate ist absichtlich streng: bei `no_go` keine Freigabe.
- Für Steering ist die Markdown-Zusammenfassung ausreichend; für Automatisierung immer JSON verwenden.