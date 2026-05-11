# Analyse der importierten Stakeholder-Arbeitsmappe

Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx`

## Kurzfazit

- Projektname laut Quelle: Structural Information & Activity Space Analysis under Uncertainty
- Stakeholder-Anforderungen: 668
- Nicht-Ziele: 71
- Projektentscheidungen: 27
- Datenquellen: 38
- MVP-Länder: 30
- Features im Feature-Katalog: 102
- Zentrale Akzeptanzkriterien: 18
- Risiken: 31

## Inhaltliche Einordnung

- Die Arbeitsmappe enthaelt nicht nur Stakeholder Requirements, sondern bereits ein breites Projektbasiswissen fuer Scope, Nicht-Ziele, Entscheidungen, Datenquellen, Laenderset, Statuslogik, GUI, Betrieb, Risiken, Prinzipien, Traceability und Validierung.
- Fuer SIASA ist diese Mappe damit nicht nur Inputmaterial, sondern eine initiale fachliche Baseline.
- Die kanonischen Stakeholder Requirements wurden in `vmodel/requirements/stakeholder_requirements.yaml` ueberfuehrt.
- Die zusaetzlichen Projektinformationen wurden in eigenstaendige Artefakte unter `vmodel/project/`, `vmodel/architecture/`, `vmodel/method/`, `vmodel/verification/` und `vmodel/traceability/` ueberfuehrt.

## Sheet-Inventar

| Sheet | Zeilen |
|---|---:|
| Overview | 14 |
| Stakeholder_Reqs | 668 |
| Non_Goals | 71 |
| Decisions | 27 |
| Domains | 5 |
| Data_Sources | 38 |
| MVP_Countries | 30 |
| Status_Models | 13 |
| Feature_Set | 102 |
| GUI_Pages | 12 |
| Roles | 4 |
| Reports_Exports | 8 |
| Data_Run_Strategy | 7 |
| Annotation_Model | 11 |
| Config_Tables | 17 |
| Traceability_Model | 9 |
| Use_Cases | 6 |
| Acceptance_Criteria | 18 |
| Prioritization | 5 |
| Assumptions | 25 |
| Risks | 31 |
| Principles | 34 |
| System_Boundaries | 15 |
| Glossary | 48 |
| Validation_Model | 11 |

## Stakeholder-Requirements-Analyse

### Verteilung nach Kategorie

| Kategorie | Anzahl |
|---|---:|
| Betrieb & Automatisierung | 47 |
| Definition of Done / MVP-Abnahme | 44 |
| Traceability & Versionierung | 41 |
| Qualitätsanforderungen | 35 |
| Daten-Governance / Lizenz / personenbezogene Analyse | 35 |
| Validierung & Backtesting | 24 |
| Systemgrenzen / externe Systeme | 24 |
| Ethik & Missbrauchsbegrenzung | 22 |
| Q MVP-Länderauswahl | 17 |
| Y Analyse-Funktionsrahmen A-E | 17 |
| MVP-Priorisierung & Akzeptanzkriterien | 17 |
| W Regelbasierte Bewertung und Annotationen | 16 |
| P Historischer Datenhorizont und Data Sufficiency | 14 |
| Risiken & Annahmen | 14 |
| P Datenbank und tägliche Runs | 13 |
| Z MVP Feature Set | 13 |
| N GUI Seitenstruktur | 12 |
| O Multi-Window-Baselines | 11 |
| S Festgelegte Datenquellen | 11 |
| V Domänenstatus D0-D5 | 11 |
| N GUI Grundanforderungen | 10 |
| N GUI Weltkarte und Score-Modi | 10 |
| S Datenquellenverwaltung und ACLED | 10 |
| T Funktionsrahmen ohne General Fusion Score | 10 |
| U Einbindung C/E in Multi-Domain-Status | 10 |
| X Report und Export | 10 |
| X Automatische und manuelle Reports | 10 |
| AA Nutzerrollen und Berechtigungen | 10 |
| Q Länderpriorisierung | 9 |
| R MVP-Domänenumfang | 9 |
| U Multi-Domain-Status | 9 |
| W Annotationen ohne Review im MVP | 9 |
| N GUI Nutzungsmodi | 8 |
| Q MVP-Länderset v0.1 | 8 |
| Glossar / Begriffsdefinitionen | 8 |
| A Grundziel und Scope | 7 |
| O Kartenbaseline und Vergleichsskala | 7 |
| Use Cases | 7 |
| D Country Information & Activity Space Profile | 6 |
| F Informationsabhängigkeiten und Quellencluster | 6 |
| I Evidenzfusion und Cross-Domain-Kontrastierung | 6 |
| J Unsicherheit und Explainability | 6 |
| O Aktualitätsfenster | 6 |
| B Quellenklassen | 5 |
| C Quellenkatalog und Metadaten | 5 |
| E Baselines und Anomalien | 5 |
| G Source Lineage | 5 |
| H Informations-Epidemiologie | 5 |
| K Probabilistische Zustandsmodellierung | 5 |
| L Validierung und Backtesting | 5 |
| M Projekt- und Nutzungsziel | 4 |

### Verteilung nach Quellstatus

| Quellstatus | Anzahl |
|---|---:|
| aktiv | 668 |

### Verteilung nach Priorität

| Priorität | Anzahl |
|---|---:|
| TBD / aus v0.3 | 350 |
| MVP-Must | 291 |
| MVP-Should | 16 |
| Post-MVP | 11 |

### Verteilung nach Phase

| Phase | Anzahl |
|---|---:|
| MVP/Post-MVP prüfen | 350 |
| MVP v1 | 318 |

## Weitere Schwerpunkte

### Datenquellen nach Status

| Status | Anzahl |
|---|---:|
| Core | 5 |
| Core/Extended | 6 |
| Extended | 14 |
| Prepared Adapter | 4 |
| Selektiv P1 | 7 |
| Extended/Selektiv P1 | 1 |
| Prepared/Extended | 1 |

### Länderpriorisierung

| Priorität | Anzahl |
|---|---:|
| P1 | 10 |
| P2 | 11 |
| P3 | 9 |

### Feature-Katalog nach Domäne

| Domäne | Anzahl Features |
|---|---:|
| A | 20 |
| B | 17 |
| C | 14 |
| D | 18 |
| E | 16 |
| X | 17 |

### Akzeptanzkriterien nach Priorität

| Priorität | Anzahl |
|---|---:|
| MVP-Must | 18 |

### Risiken nach Priorität

| Priorität | Anzahl |
|---|---:|
| hoch | 19 |
| mittel | 8 |
| sehr hoch | 4 |

### Prinzipien nach Kategorie

| Kategorie | Anzahl |
|---|---:|
| Daten-Governance | 10 |
| Ethik | 10 |
| Betrieb | 8 |
| Traceability | 6 |

## Importentscheidungen

- Alle 668 Stakeholder Requirements wurden mit ihren Original-IDs (`StR-*`) uebernommen.
- Der Quellstatus `aktiv` wurde als `accepted` uebernommen; der Originalwert bleibt als `source_status` erhalten.
- Die zentralen Akzeptanzkriterien wurden nach `vmodel/verification/acceptance_criteria.yaml` ueberfuehrt und pro Requirement ueber `acceptance_criteria_refs` verlinkt, sofern in der Arbeitsmappe explizit referenziert.
- Nicht-Ziele, Entscheidungen, Prinzipien, Risiken, Annahmen, Systemgrenzen, Use Cases und weitere Strukturinformationen wurden als eigenstaendige Artefakte abgelegt, damit sie in spaeteren Ableitungen nicht verloren gehen.
