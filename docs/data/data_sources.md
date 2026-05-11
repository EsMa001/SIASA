# Datenquellenkatalog

Importierter Quellenkatalog. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Data_Sources`.

| Ebene | Quelle | Status | Signale | Zugriff | Historie | Bemerkung |
| --- | --- | --- | --- | --- | --- | --- |
| A | GDELT 2.0 Events/GKG/DOC API | Core | Newsvolumen, Tonalität, Themen, Akteure, Orte, Quellen, Narrative | frei/open data | >=3 Jahre möglich | zentral für A; medienabhängig |
| A | RSS / News Feeds | Core | aktuelle Nachrichten je Land/Thema | frei/websiteabhängig | oft begrenzt | gut für Daily Runs, schwächer für Historie |
| A | Offizielle Regierungs-/Institutionenfeeds | Core/Extended | Statements, Warnungen, Diplomatie, Sanktionen | frei, kuratiert | quellenabhängig | wertvoll für offizielle Signale |
| A | Media Cloud | Extended | Medienökosysteme, Story-Diffusion | API/Registrierung möglich | prüfen | gut für Informationsflussanalyse |
| A/E | EUvsDisinfo | Extended | Desinformationsfälle, InfoOps-Narrative | öffentlich | prüfen | Schnittstelle A/E |
| A | Reddit / Mastodon | Extended | öffentliche Diskussionsdynamik | API/Regeln | begrenzt | selektiv und vorsichtig |
| A | Telegram | Prepared Adapter | Konfliktkommunikation, Propaganda | technisch/rechtlich prüfen | unklar | nicht MVP-Core |
| A | X/Twitter | Prepared Adapter | schnelle Eliten-/Narrativkommunikation | API/Kosten | unklar | nicht MVP-Core |
| B | UCDP GED | Core | organisierte Gewalt, Konfliktereignisse, Geodaten, Todeszahlen | frei/API/Download | mehrjährig | offene Alternative zu ACLED |
| B | GDELT Events | Core | medienextrahierte Ereignisse nach CAMEO | frei/open data | >=3 Jahre möglich | nicht Ground Truth, medienabhängig |
| B | ReliefWeb API | Core/Extended | humanitäre Krisen, Länderberichte, Lageberichte | frei/API | mehrjährig | humanitärer Kontext |
| B | GDACS | Core/Extended | Naturkatastrophen, Alerts, Krisenereignisse | frei/API | mehrjährig prüfen | Disaster-/Shock-Komponente |
| B | INFORM Risk Index | Extended | strukturelles humanitäres Risiko | öffentlich | jährlich | struktureller Kontext |
| B | Global Terrorism Database | Extended | Terrorismusereignisse historisch | öffentlich/Download prüfen | langjährig | historische Validierung |
| B | ACLED | Prepared Adapter | politische Gewalt, Proteste, Konflikte | kein Zugriff im MVP | abhängig von Zugang | Adapter vorbereiten, deaktiviert |
| C | NASA FIRMS | Selektiv P1 | aktive Feuer, thermische Anomalien | frei/API | mehrjährig prüfen | Konflikt-/Katastrophenindikator |
| C | VIIRS / Black Marble Nighttime Lights | Selektiv P1 | Nachtlicht, Strom-/Aktivitätsänderungen | frei/earthdata | mehrjährig | langsamere physische Kontextsignale |
| C | Copernicus / Sentinel | Selektiv P1 | Satellitenbasierte Infrastruktur-/Umweltindikatoren | frei/API | mehrjährig | datenintensiv |
| C | OpenSky Network | Extended/Selektiv P1 | ADS-B Flugbewegungen | API/Registrierung | abhängig vom Zugriff | selektiv einsetzen |
| C | AIS-Schiffsdaten | Prepared Adapter | maritime Aktivität, Häfen, Routen | oft nicht frei | unklar | später prüfen |
| C | OpenStreetMap / HOT OSM | Extended | Infrastruktur-/Kontextdaten | frei | statisch/historie begrenzt | Kontext statt tägliches Signal |
| D | World Bank Indicators API | Core | Makroindikatoren, Bevölkerung, Entwicklung, Struktur | frei/API | langjährig | Basisquelle |
| D | IMF Data API / SDMX | Core/Extended | Makroökonomie, Zahlungsbilanz, Wechselkurse, Finanzdaten | frei/API | langjährig | für viele Länder |
| D | UN Comtrade | Core/Extended | Import/Export, Handelsströme, Abhängigkeiten | API-Key/Limits | langjährig | Handelsabhängigkeiten |
| D | FAOSTAT | Core/Extended | Nahrung, Landwirtschaft, Versorgung | frei/API | langjährig | Food-Stress |
| D | OECD Data Explorer | Extended | OECD-Länder, Wirtschaft, Arbeit, Energie | API | langjährig | OECD-/Kontrollländer |
| D | Our World in Data | Extended | kuratierte globale Zeitreihen | frei | variiert | schnelle Prototypen/Kontext |
| D | FRED | Extended | Finanz-/Makrozeitreihen | API | variiert | Abdeckung je Land unterschiedlich |
| D | ECB Data Portal | Extended | Eurozone, Wechselkurse, Finanzmärkte | API | mehrjährig | EU-/Euro-Kontext |
| D | EIA / IEA öffentliche Daten | Extended | Energieproduktion, Verbrauch, Öl/Gas | Lizenz/API prüfen | variiert | Energieindikatoren |
| D | ENTSO-E Transparency Platform | Extended | europäische Stromsystemdaten | Registrierung/API | mehrjährig | KRITIS/Energie Europa |
| E | CISA KEV Catalog | Selektiv P1 | bekannte aktiv ausgenutzte Schwachstellen | frei CSV/JSON | seit Katalogbeginn | globales Expositionssignal |
| E | NVD CVE API | Selektiv P1 | CVEs, CVSS, Vulnerability Trends | frei/API | langjährig | nicht automatisch länderspezifisch |
| E | Cloudflare Radar / Outage Center | Selektiv P1 | Internet-Outages, Traffic-Anomalien | API/öffentlich | prüfen | technische Störungen |
| E | Google Transparency Report Traffic | Selektiv P1 | Traffic-Rückgänge, regionale Zugangsprobleme | öffentlich | prüfen | unabhängiges Disruption-Signal |
| E | nationale CERT/CSIRT Feeds | Extended | nationale Cyberwarnungen | frei/kuratiert | quellenabhängig | für P1/P2 kuratieren |
| E | Shadowserver | Prepared/Extended | Security-Telemetrie, exposed services, botnet/sinkhole | Zugriff prüfen | unklar | später prüfen |
| E | Abuse.ch Feeds | Extended | Malware-/Botnet-Indikatoren | frei | mehrjährig prüfen | eher globale Threat Intelligence |

