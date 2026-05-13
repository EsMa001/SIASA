# Use Cases

Importierte priorisierte Use Cases. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Use_Cases`.

| Use Case ID | Name | Ziel | MVP | Primäre GUI-Seite | Mindestfunktionen |
| --- | --- | --- | --- | --- | --- |
| UC-001 | Daily Global Review | Tägliche Weltkarten-/Statusübersicht prüfen; welche Länder zeigen neue Auffälligkeiten? | ja | World Anomaly Map | Karte; aktive/anomale Domänen; Datenlücken; Top-Statusänderungen; Drill-down nur auf verfügbare Country Profiles ohne dead links |
| UC-002 | Country Deep Dive | Land auswählen und erklären, warum es auffällig, unauffällig oder nicht bewertbar ist. | ja | Country Profile | D0–D5 je Domäne; Treiber; Gegenindikatoren; Jahresverläufe; Events; Annotation; aus der Startseite erreichbar und mit funktionierender Rücknavigation |
| UC-003 | Source/Coverage Review | Datenlage, Quellenstatus, Historientiefe, Ausfälle und Confidence prüfen. | ja | Source / Coverage View | Quellenstatus; Datenlücken; Historie; failed sources; ACLED prepared adapter sichtbar |
| UC-004 | Report Export | Ergebnisse reproduzierbar für Dokumentation, Validierung oder Veröffentlichung exportieren. | ja | Report / Export View | Daily Snapshot automatisch; Country/Domain/Coverage manuell; IDs und Unsicherheit im Report |
| UC-005 | Backtest / Validation | Historische Referenzfälle prüfen und erwartete vs. beobachtete Muster vergleichen. | MVP-Should | Backtest / Validation View | Referenzfälle; Domänenmuster; FP/FN Hinweise; Export |
| UC-006 | Rule Tuning | Regeln und Schwellen anpassen; zunächst Admin-only über Konfigurationsdateien. | Post-MVP/Should | Admin / Config | Ruleset-Versionierung; Test gegen Referenzfälle |

