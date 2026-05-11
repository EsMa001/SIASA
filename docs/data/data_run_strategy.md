# Daten- und Run-Strategie

Importierte Festlegungen zu Historie, Runs und Snapshots. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Data_Run_Strategy`.

| Baustein | Festlegung | Zweck |
| --- | --- | --- |
| Initialer Datenaufbau | Mindestens 3 Jahre historische Daten, soweit Quelle verfügbar. | Basis für Baselines, Jahresverläufe, Backtesting. |
| Täglicher Run | Neue Daten abrufen, Rohdaten speichern, normalisieren, Features berechnen, Status ableiten. | Erweitert Datenbank inkrementell. |
| Snapshot | Jeder erfolgreiche Run erzeugt einen versionierten Snapshot. | Reproduzierbarkeit und GUI-Zustand. |
| Partial Failure | Bei teilweise fehlgeschlagenem Run wird Quellenfehler explizit dokumentiert. | Kein irreführender Snapshot. |
| Reprocessing | Algorithmus-/Regel-/Taxonomieänderungen sollen Reprocessing ermöglichen. | Vergleichbarkeit alter und neuer Ergebnisse. |
| Traceability | Source → Raw → Normalized → Feature → D-Status → S-Status → Snapshot → Report. | Nachvollziehbarkeit bis zur Quelle. |
| Data Sufficiency | Vor Statusberechnung prüfen, ob Datenhistorie/Coverage reicht. | D0 oder geringe Confidence statt falsche Unauffälligkeit. |

