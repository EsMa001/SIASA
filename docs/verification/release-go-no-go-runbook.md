# SIASA Release Go/No-Go Runbook

Ziel: Ein reproduzierbares, evidenzbasiertes Go/No-Go-Protokoll vor Demo/Release.

## 1) Pflicht-Eingänge

- `readiness`-Bewertung (Demo- und Release-Verdikt)
- `release_gate`-Bewertung (explizites Go/No-Go + Blocker)
- `traceability_integrity`-Bewertung (globaler Integritätszustand)

Diese Artefakte werden maschinenlesbar erzeugt und im Evidence Pack dokumentiert.

## 2) CI-Gate (verbindlich)

CI führt aus:
- `PYTHONPATH=src python scripts/ci_release_gate_check.py`

Regel:
- `gate_verdict == "go"` -> CI-Schritt erfolgreich
- sonst -> CI-Schritt fehlschlagen (`no_go` blockiert Merge/Release)

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
- Entscheidung: Go / No-Go
- Nächste Maßnahme:

## 6) Hinweise

- Das Gate ist absichtlich streng: bei `no_go` keine Freigabe.
- Für Steering ist die Markdown-Zusammenfassung ausreichend; für Automatisierung immer JSON verwenden.