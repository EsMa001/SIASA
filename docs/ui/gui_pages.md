# GUI-Seiten

Geplante GUI-Seiten und ihr MVP-Status. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `GUI_Pages`.

| Seite | Zweck | Inhalt | MVP-Status |
| --- | --- | --- | --- |
| Startseite / World Anomaly Map | Globale Orientierung | Weltkarte mit Multi-Domain-Status, Filter für Domänen/Zeiträume/Baselines, Drill-down nur auf verfügbare Länderansichten ohne dead links. | MVP Pflicht |
| Global Overview | Gesamtübersicht | Länder-Ranking, Domain-Matrix, Coverage/Confidence-Matrix, Statusänderungen. | MVP Pflicht |
| Country Profile | Länderanalyse | Country Summary, Domänenstatus A–E, Current Events, Jahresverläufe, Treiber, Gegenindikatoren, Unsicherheit; über unterstützten Drill-down erreichbar und mit funktionierender Rücknavigation. | MVP Pflicht |
| Domain Detail A–E | Domänentiefe | Detailanalyse der jeweiligen Domäne mit Zeitreihen, Features, Quellen, D0–D5-Begründung. | MVP Pflicht für A/B/D; C/E selektiv |
| Yearly Trend Page | Jahresverläufe | 12-Monats-Graphen, historische Vergleichsjahre, Baselines, Event Overlays. | MVP Pflicht |
| Current Events Page | Ereignisnachvollzug | Eventliste, Typ, Quelle, Relevanz, Confidence, Deduplizierung, verlinkte Signale. | MVP Pflicht |
| Source / Coverage Page | Datenlage | Quellenliste, Coverage, Quality, Update Latency, Bias Notes, Missing Sources. | MVP Pflicht |
| Source Lineage / Epidemiology | Informationsausbreitung | First Seen, Spread Timeline, Source Graph, Amplification, Mutation, Cross-Country Spread. | MVP vorbereitet / Extended |
| Cross-Country Comparison | Ländervergleich | Vergleichsmatrix, Similarity Clustering, Domain/Coverage/Trend Comparison. | MVP Extended |
| Backtest / Validation | Validierung | Historischer Zeitraum, Replay-Modus, damalige Signale, False Positive/Negative, Algorithmusversion. | MVP vorbereitet / Extended |
| Report / Export View | Export | Daily Snapshot, Country/Domain/Event/Coverage/Backtest Reports als Markdown/JSON/CSV. | MVP Pflicht |
| System Status / Runs | Betrieb | Last Run, Quellenstatus, Fehler, Datenfrische, Snapshot ID, Reprocessing-Status. | MVP Pflicht |
| Demo / Release Readiness | Vorführung und Freigabe | Demo-Flow-Checkliste, Evidenz-Checkliste, bekannte Release-Gaps, Run-/Snapshot-Bezug und Readiness-Verdikte. | MVP für Demo-/Release-Readiness |

