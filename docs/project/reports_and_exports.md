# Reports und Exporte

Importierte Report- und Exporttypen. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Reports_Exports`.

| Reporttyp | Erzeugung | Formate | Inhalt | Status |
| --- | --- | --- | --- | --- |
| Daily Global Snapshot | automatisch nach erfolgreichem täglichen Run | Markdown + JSON | Top-Statusänderungen, neue Auffälligkeiten, Datenlücken, Quellenfehler, Annotationen seit letztem Run | MVP Pflicht |
| Country Profile Report | manuell aus GUI | Markdown + JSON; PDF später | Land, Zeitraum, Domänenstatus, Treiber, Gegenindikatoren, Events, Unsicherheit, Annotationen | MVP Pflicht |
| Domain Report | manuell aus GUI | Markdown + CSV/JSON | Detailreport einer Domäne A–E für ein Land | MVP Pflicht für A/B/D |
| Event Report | manuell aus GUI | CSV/JSON/Markdown | Events, Quellen, Typen, Relevanz, Confidence, verlinkte Signale | MVP Pflicht |
| Coverage Report | manuell aus GUI | CSV/JSON/Markdown | Datenverfügbarkeit, Quellenfehler, Historie, Lücken, Datenqualität | MVP Pflicht |
| Lineage / Epidemiology Report | manuell aus GUI | JSON/Markdown | First Seen, Spread, Source Graph, Amplification, Mutation | Extended |
| Backtest Report | manuell aus GUI | Markdown + JSON | historische Rekonstruktion, Signalverlauf, Regeln, False Positive/Negative | Extended |
| Annotation Export | manuell | CSV/JSON | Analystenhinweise für Validierung/Review/Regelverbesserung | MVP Pflicht |

