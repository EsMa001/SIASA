# Risiken

Importiertes Risikoregister. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Risks`.

| ID | Kategorie | Risiko | Beschreibung | Gegenmaßnahme | Wahrscheinlichkeit | Schweregrad | Priorität |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R-001 | Daten | Quellen fallen aus | APIs ändern sich, Rate Limits greifen, Quellen sind temporär nicht erreichbar. | Source Adapter robust bauen; partial_success; Logs; Coverage-Anzeige. | High | Medium | hoch |
| R-002 | Daten | Datenhistorie reicht nicht aus | Manche Quellen liefern keine 3 Jahre Historie. | Datenhorizont je Quelle dokumentieren; D0/Coverage-Einschränkung. | Medium | Medium | mittel |
| R-003 | Daten | Datenqualität variiert stark | Länder sind unterschiedlich gut beobachtbar. | Coverage-/Confidence-Score je Land/Domäne/Quelle. | High | High | hoch |
| R-004 | Daten | Medienbias dominiert | Ebene A misst Sichtbarkeit statt Realität. | A nie isoliert als reale Eskalation interpretieren; Cross-Domain-Kontrastierung. | High | High | sehr hoch |
| R-005 | Daten | Ereignisdaten sind unvollständig | B-Daten können regional verzögert oder lückenhaft sein. | Meldeverzug, Quellenvergleich, Unsicherheitsflags. | Medium | High | hoch |
| R-006 | Daten | C/E-Daten schwer interpretierbar | Physische/Cyber-Signale sind oft nicht eindeutig länderspezifisch. | C/E nur bei ausreichender Datenqualität statusrelevant einbeziehen. | High | Medium | hoch |
| R-007 | Daten | Quellenabhängigkeit erzeugt Scheinevidenz | Mehrere Quellen replizieren dieselbe Ursprungsaussage. | Source Dependency, Duplicate Ratio, First-Seen-/Lineage-Logik. | High | High | sehr hoch |
| R-008 | Methodik | Scheingenauigkeit | Statuswerte wirken präziser, als die Datenlage erlaubt. | Keine Gesamt-Score-Fusion; Unsicherheit sichtbar machen. | Medium | High | hoch |
| R-009 | Methodik | Fehlinterpretation der Weltkarte | Kartenfarben werden als objektive Krisenbewertung gelesen. | Legende, Methodentext, Status statt Risiko-Score. | Medium | High | hoch |
| R-010 | Methodik | Schleichende Eskalation wird normalisiert | Kurze Baselines übernehmen langsame Verschlechterung als neuen Normalzustand. | 30/90/365-Kombination und mehrjährige Historie. | Medium | Medium | mittel |
| R-011 | Methodik | Akute Dynamiken werden geglättet | Lange Baselines übersehen kurzfristige Auffälligkeiten. | 7-Tage-Aktualitätsfenster plus 30-Tage-Komponente. | Medium | Medium | mittel |
| R-012 | Methodik | Cross-Domain-Kontrastierung wird überinterpretiert | Gleichzeitige Auffälligkeit wird fälschlich als Kausalität gelesen. | Darstellung als Alignment, nicht als Ursache. | Medium | High | hoch |
| R-013 | Methodik | D5 wird falsch verstanden | Widersprüchliche Daten werden als hoher Risikostatus gelesen. | D5 als Mehrdeutigkeitsstatus klar kennzeichnen. | Medium | Medium | mittel |
| R-014 | Methodik | Backtests erzeugen rückblickende Scheinsicherheit | Historische Daten werden mit heutiger Kenntnis interpretiert. | MVP-Backtest klar als nicht Point-in-Time markieren. | Medium | High | hoch |
| R-015 | Technik | Scope Creep | Zu viele Quellen, Länder, Features und GUI-Seiten überladen den MVP. | MVP-Must/Should/Could/Post-MVP-Priorisierung. | High | High | sehr hoch |
| R-016 | Technik | Datenmodell wird zu komplex | A–E, Features, Status, Snapshots, Reports und Annotationen erzeugen hohe Komplexität. | Saubere IDs, Versionierung, modulare Datenebenen. | Medium | High | hoch |
| R-017 | Technik | Reprocessing überschreibt Ergebnisse | Alte Analysezustände gehen verloren. | No silent overwrite, neue Ergebnisversionen. | Medium | High | hoch |
| R-018 | Technik | GUI wird zu früh aufwendig | Visualisierung verschlingt Aufwand vor Daten-/Analysevalidierung. | Erst funktional-transparente GUI; Design später. | Medium | Medium | mittel |
| R-019 | Technik | Performanceprobleme bei Historie | 3 Jahre Daten × 30 Länder × viele Quellen kann groß werden. | Inkrementelle Verarbeitung, Feature-Caching, Datenbankindizes. | Medium | Medium | mittel |
| R-020 | Technik | Secrets gelangen in Code/Repo | API-Keys oder Tokens werden versehentlich versioniert. | .env, Secret-Handling, Gitignore, Konfigurationsprüfung. | Medium | High | hoch |
| R-021 | Governance | Urheberrechtsproblem durch News-Speicherung | Volltexte oder lange Auszüge könnten lizenzproblematisch sein. | Metadaten/URLs/Features statt Volltext speichern. | Medium | High | hoch |
| R-022 | Governance | Social-Media-Daten missbräuchlich nutzbar | Rohdaten könnten Profiling ermöglichen. | Aggregation, IDs statt Rohdaten, keine Nutzerprofile. | Medium | High | hoch |
| R-023 | Governance | Personenbezogene Analyse driftet | Öffentliche Akteursanalyse könnte zu Personentracking werden. | Begrenzung auf öffentliche/institutionelle Akteure; keine Privatpersonen. | Medium | Critical | sehr hoch |
| R-024 | Ethik | System wird operativ missverstanden | Ergebnisse werden als Handlungsempfehlung interpretiert. | Ethikleitplanken, Reports mit Unsicherheit, keine Handlungsvorschläge. | Medium | High | hoch |
| R-025 | Ethik | Cyber-/InfoOps-Attribution überzogen | Technische Signale werden vorschnell Akteuren zugeschrieben. | Attribution-Risk-Flag, keine Schuldzuschreibung ohne Evidenz. | Medium | High | hoch |
| R-026 | Ethik | Öffentliche Exporte enthalten sensible Details | Reports könnten personenbezogene oder missbräuchlich nutzbare Details enthalten. | Export-Governance, Review vor Veröffentlichung. | Medium | High | hoch |
| R-027 | Validierung | Referenzfälle sind biased | Nur bekannte dramatische Ereignisse werden gewählt. | Mischung aus Positiv-, Negativ- und Kontrollfällen. | Medium | Medium | mittel |
| R-028 | Validierung | False Positives werden unterschätzt | System wirkt gut, obwohl es zu oft Alarm schlägt. | False-Positive-Dokumentation verpflichtend. | Medium | High | hoch |
| R-029 | Validierung | False Negatives werden übersehen | Relevante Ereignisse werden nicht erkannt. | False-Negative-Dokumentation und Annotationen. | Medium | High | hoch |
| R-030 | Validierung | Validierung bleibt rein narrativ | Keine strukturierten Kriterien. | Einfache Metriken: Domain Match, Lead/Lag, Explainability, Data Sufficiency. | Medium | Medium | mittel |
| R-031 | Validierung | Backtests als Prognosebeweis missverstanden | Rückblickende Erkennung wird als Prognosefähigkeit gelesen. | Methodische Einschränkung in Reports ausweisen. | Medium | High | hoch |

