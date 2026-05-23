# SIASA Model Routing Matrix (Governance Standard)

Zweck: Modellwahl je Arbeitspaket verbindlich standardisieren, damit High-Level-Entscheidungen mit maximaler Qualität getroffen werden und Implementierungskosten kontrolliert bleiben.

Geltung: Dieses Dokument ist für alle kommenden SIASA-Tasks als Standard zu verwenden.

## 1) Routing-Prinzip

- High-level Denken (Ambiguität, Priorisierung, Risiko, Governance-Logik): modernstes verfügbares Modell (z. B. 5.5-Klasse).
- Umsetzung (Code, Tests, CI, YAML/JSON-Änderungen): Codex/implementierungsnahes Modell.
- Reine Format-/Fleißarbeit: kleineres Modell.

## 2) AP-basierte Modellzuordnung

### AP-01 — Stakeholder-Anforderungen normieren und schärfen
- Task-Typ: Ambiguitätsauflösung, testbare Akzeptanzkriterien
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3 für strukturierte Artefakt-Updates
- Stop-Kriterien:
  1. Jede aktive StR hat messbares Akzeptanzkriterium
  2. Keine unoperationalisierten Begriffe
  3. Review-Stichprobe ohne offene Unklarheit
- Max-Iterationen: 3 fachliche Runden + 1 Finalisierung

### AP-02 — Traceability StR->SyR->SwR->TC
- Task-Typ: semantisches Mapping + Link-Härtung
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. 0 missing Pfade
  2. 0 orphan mappings
  3. Konsistenztests grün
- Max-Iterationen: 2 Mapping-Runden + 2 Fix-Runden

### AP-03 — Verifikationsabdeckung pro Anforderung
- Task-Typ: Teststrategie, Failure-Modes, Abdeckung
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. Jede relevante StR hat mind. einen automatisierten Nachweis
  2. Targeted + Full Suite grün
  3. Traceability auf Tests vollständig
- Max-Iterationen: 2 Strategie-Runden + 3 Implementierungsrunden

### AP-04 — Stakeholder-End-to-End-Flows
- Task-Typ: Rollenflows, Happy-/Failure-Path-Definition
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. Priorisierte Kernflows vollständig modelliert
  2. E2E-Suite grün
  3. Flow-Evidence in GUI/Artifacts sichtbar
- Max-Iterationen: 2 Design-Runden + 3 Umsetzungsrunden

### AP-05 — Release-Gate-Härtung
- Task-Typ: Gate-Logik, Blocker-Semantik, No-Go-Regeln
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. Positive Runs -> go
  2. Injektierte Negativfälle -> no_go
  3. CI fail-closed nachweisbar
- Max-Iterationen: 2 Logikrunden + 2 CI-Fixrunden

### AP-06 — Evidence-Pack-Standard
- Task-Typ: Informationsarchitektur, Entscheidungsfähigkeit
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. JSON stabil maschinenlesbar
  2. MD/GUI entscheidungsfähig lesbar
  3. Go/No-Go ohne Zusatzinterpretation
- Max-Iterationen: 2 Struktur-Runden + 2 Implementierungsrunden

### AP-07 — Drift-Kontrolle
- Task-Typ: Metrik-/Threshold-Design, Monitoring-Regeln
- Primärmodell: 5.5-Klasse
- Fallback: 5.4-Klasse
- Execute-Modell: Codex 5.3
- Stop-Kriterien:
  1. Delta-Checks laufen regelmäßig
  2. Neue Lücken erzeugen Action-Items
  3. Praktikable Signalqualität (keine Alert-Fatigue)
- Max-Iterationen: 2 Design-Runden + 2 Tuning-Runden

## 3) Verbindliche Routing-Regeln

1. Erst Entscheidung, dann Umsetzung:
   - Zuerst 5.5-Decision-Artefakt (Regeln/Kriterien/Prioritäten), danach Codex-Ausführung.
2. Kein Modellmix in einem Einzelschritt:
   - Ein Schritt hat ein Primärziel und genau eine Modellklasse.
3. Wechselpunkt:
   - Bei Wechsel von "Was/Warum" zu "Wie im Code" auf Codex wechseln.
4. Eskalation:
   - Wenn Codex 2x am selben konzeptionellen Punkt scheitert -> zurück zu 5.5.
5. Kostenkontrolle:
   - 5.5 nur für Entscheidungsknoten, Bulk-Änderungen mit Codex.

## 4) DoD je Arbeitspaket

Ein AP ist nur Done, wenn:
1. fachliche Stop-Kriterien erfüllt,
2. Tests/Gates grün,
3. Evidenzartefakte aktualisiert,
4. Commit + Push erfolgt.

## 5) Operative Parameter

- 5.5-Decision-Tasks: max 3 Turns
- Codex-Implementierungsloops: max 3 Loops
- Danach zwingend: Scope-Split oder Blocker-Dokumentation

## 6) Anwendung für kommende Aufgaben

Für alle kommenden SIASA-Aufgaben ist vor Start jedes AP explizit zu dokumentieren:
- gewähltes Primärmodell,
- Fallback,
- Stop-Kriterien,
- Iterationsbudget.

Diese Angaben gehören in den jeweiligen Task-Prebrief und in die Abschlussmeldung des AP.