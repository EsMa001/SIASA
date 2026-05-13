# SIASA Level 4 – Demo- und Release-Readiness

Ziel: Die nun umgesetzten Level-3-Nutzerflüsse in einen vorführbaren und freigabefähigen Zustand überführen.

## Umgesetzter Scope

Level 4 wird in diesem Repo als Kombination aus operativer GUI-Sicht und dokumentierter Readiness-Checkliste umgesetzt:

1. Demo-/Release-Readiness-View in der lokalen GUI
   - zentrale Seite `readiness.html`
   - Demo-Flow-Checkliste
   - Evidenz-Checkliste
   - bekannte Release-Gaps
   - Demo- und Release-Verdikt
   - Run-/Snapshot-Bezug

2. Maschinenlesbares Readiness-Artefakt
   - `readiness.json` im generierten GUI-Bundle
   - geeignet für spätere Automation oder Release-Gates

3. Repo-Dokumentation aktualisiert
   - GUI-Seitenbeschreibung ergänzt
   - README um Readiness-View/Artefakt ergänzt

## Readiness-Logik

Die Readiness-Sicht trennt bewusst zwei Ebenen:

- Demo Verdict
  - bewertet, ob der geführte Vorführpfad vorhanden ist
  - zentrale Flows: Home, Country Profile, Domain Detail, Source / Coverage, Report / Export, Validation / Backtest

- Release Verdict
  - berücksichtigt bekannte Gaps vor Auslieferung
  - z. B. `failed_source:*`, `missing_source:*`, explizite `data_gaps`

Damit wird sichtbar gemacht:
- etwas kann demo-fähig sein,
- aber wegen dokumentierter Daten- oder Betriebsgrenzen noch nicht release-frei.

## Erwartete Bedienung

1. GUI erzeugen
2. `readiness.html` öffnen
3. Demo-Flow-Checkliste prüfen
4. Evidenz-Checkliste prüfen
5. bekannte Gaps gegen Demo-/Release-Ziel bewerten
6. bei Bedarf in die verlinkten Kernseiten zurückspringen

## Validierung

- Unit-/GUI-Tests für Generierung und Inhalt der Readiness-Seite
- CLI-/Artefakt-Load-Test
- Full test suite
- Browser-Smoke der Readiness-Seite

## Ergebnis

Level 4 liefert damit keinen bloßen Textplan, sondern ein konkret ausführbares Readiness-Artefakt im Produkt selbst.