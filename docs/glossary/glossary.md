# Glossar

Importiertes Projektglossar. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Glossary`.

| Begriff | Definition |
| --- | --- |
| System | Analyse- und Beobachtungssystem zur strukturellen Analyse globaler Informations- und Aktivitätsräume unter Unsicherheit. |
| MVP | Erste lauffähige Version mit länderzentrierter Analyse, Core-Domänen A/B/D, selektiver C/E-Unterstützung, GUI, Reports, Annotationen, Traceability und Validierung. |
| Land / Country | Primäres Analyseobjekt des Systems, identifiziert über ISO-Codes und priorisiert in P1/P2/P3. |
| Country Set | Versionierte Liste betrachteter Länder inklusive Priorität, Region, Auswahltyp und Begründung. |
| P1-Land | Kernland mit hoher sicherheitspolitischer Relevanz und angestrebter tiefer Multi-Domain-Analyse. |
| P2-Land | Erweitertes Fokusland mit relevanter Analyse, aber ggf. reduzierter Integrationstiefe. |
| P3-Land | Kontroll-/Referenzland zur Einordnung normaler Dynamiken, Datenrauschen und Vergleichsmustern. |
| Domäne / Ebene | Analytische Quellen- und Signalgruppe: A Informationsraum, B Ereignisdaten, C physische Aktivität, D Wirtschafts-/Strukturdaten, E Cyber/Tech/InfoOps. |
| Domäne A | Informationsraum: News, Narrative, Tonalität, öffentliche Kommunikation, Statements, Social Media und Informationsausbreitung. |
| Domäne B | Ereignisdaten: Proteste, Gewalt, Konflikte, Katastrophen, humanitäre Ereignisse und beobachtbare Ereignisse. |
| Domäne C | Physische Aktivität: Satelliten-, Feuer-, Nachtlicht-, Verkehrs-, Infrastruktur- und Aktivitätsindikatoren. |
| Domäne D | Wirtschafts-/Strukturraum: makroökonomische, handels-, energie-, nahrungsmittel- und strukturbezogene Indikatoren. |
| Domäne E | Cyber / Tech / InfoOps: Cyber-, Outage-, CVE/KEV-, CERT-, technische und informationsoperative Signale. |
| Quelle / Source | Externer oder interner Ursprung von Daten, z. B. GDELT, UCDP, World Bank, NASA FIRMS. |
| Source Adapter | Softwarekomponente, die eine Quelle abruft und Daten in ein internes Format überführt. |
| Signal | Beobachtbare Größe aus einer Quelle oder Domäne, z. B. Newsvolumen, Ereignisanzahl, Inflation, Outage-Signal. |
| Feature | Berechnete, versionierte Analysegröße aus einem oder mehreren Signalen, z. B. A_news_volume_anomaly. |
| Baseline | Historische Referenz zur Bewertung, was für Land, Domäne, Quelle oder Feature normal ist. |
| Combined Baseline | Kombinierte Betrachtung von 30-/90-/365-Tage-Baselines. |
| Anomalie | Abweichung eines Signals oder Features von einer geeigneten Baseline; kein Beweis für Instabilität oder Ursache. |
| Coverage | Datenabdeckung einer Quelle, Domäne oder eines Landes. |
| Confidence | Belastbarkeit einer abgeleiteten Aussage unter Berücksichtigung von Datenqualität, Quellenlage, Historie, Aktualität und Unsicherheit. |
| Uncertainty | Unsicherheit durch Datenlücken, Bias, Quellenabhängigkeit, Semantik, Modellannahmen oder Interpretation. |
| D0 — nicht bewertbar | Datenlage reicht nicht für belastbare Bewertung. |
| D1 — unauffällig | Domänensignale liegen innerhalb der erwartbaren Baseline. |
| D2 — leicht auffällig | Geringe, beobachtungswürdige Abweichung. |
| D3 — deutlich auffällig | Robuste und relevante Abweichung von der Baseline. |
| D4 — stark auffällig | Sehr starke und belastbare Abweichung in der Domäne. |
| D5 — widersprüchlich / mehrdeutig | Signale innerhalb der Domäne widersprechen sich oder sind nicht eindeutig interpretierbar. |
| S0 — No relevant anomaly | Keine relevante Auffälligkeit in den bewertbaren Domänen. |
| S1 — Single-domain anomaly | Eine Domäne ist auffällig. |
| S2 — Strong single-domain anomaly | Eine Domäne ist stark auffällig. |
| S3 — Multi-domain alignment | Mehrere Domänen zeigen gleichzeitig auffällige Dynamiken. |
| S4 — High-confidence multi-domain anomaly | Mehrere Domänen sind deutlich/stark auffällig und Datenlage ist belastbar. |
| S5 — Contradictory / ambiguous pattern | Domänen widersprechen sich oder Interpretation ist mehrdeutig. |
| S6 — Data insufficient | Datenlage reicht nicht für belastbare Multi-Domain-Bewertung. |
| Source Lineage | Versuch, Ursprung und Verbreitungsweg einer Information, Meldung oder eines Narrativs nachzuzeichnen. |
| Informations-Epidemiologie | Analyse von Entstehung, Ausbreitung, Verstärkung, Mutation und Abklingen von Informationen, Narrativen oder Ereignismeldungen. |
| Run | Ausführung eines Daten- und Analyseprozesses, z. B. Daily Run oder historischer Backfill. |
| Backfill | Historischer Datenaufbau über vergangene Zeiträume, z. B. mindestens drei Jahre. |
| Snapshot | Gespeicherter Analysezustand eines Runs inklusive Datenstand, Statuswerten, Quellenstatus, Konfigurationen und Versionen. |
| Report | Exportierbare Darstellung von Analyseergebnissen, z. B. Daily Snapshot, Country Profile Report, Domain Report, Coverage Report oder Backtest Report. |
| Annotation | Manuelle Analystenkommentar- oder Kontextnotiz zu Land, Domäne, Signal, Event, Snapshot oder Report. |
| Referenzfall | Manuell kuratierter historischer Fall zur Validierung des Systems. |
| False Positive | System zeigt relevante Auffälligkeit, die sich bei Analyse als nicht plausibel oder irreführend herausstellt. |
| False Negative | Relevante historische Dynamik wird vom System nicht oder unzureichend sichtbar gemacht. |
| Personenbezogene Analyse | Analyse identifizierbarer Personen; im System nur streng begrenzt auf öffentliche/institutionelle Akteurskommunikation. |
| Attribution | Zuschreibung eines Ereignisses, Cybervorfalls oder einer Informationsoperation zu einem Akteur; nur mit Unsicherheitskontext zulässig. |

