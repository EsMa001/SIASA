# Akzeptanzkriterien

Zentrale MVP-Akzeptanzkriterien aus der Stakeholder-Arbeitsmappe. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Acceptance_Criteria`.

| AC ID | Verknüpfte Anforderungen | Kriterium | Prüfmethode | Akzeptiert, wenn | Priorität |
| --- | --- | --- | --- | --- | --- |
| AC-001 | StR-162..178; StR-562..563 | Versioniertes MVP-Länderset existiert. | Konfigurationsreview | Jedes Land hat ISO-Code, P1/P2/P3, Auswahltyp, Region und Auswahlbegründung. | MVP-Must |
| AC-002 | StR-135..154; StR-491..496; StR-564..567 | Historische Datenbasis ist aufgebaut. | Datenbankprüfung + Coverage Report | Für Core-Quellen A/B/D wurden mindestens 3 Jahre geladen, soweit verfügbar; kürzere Historien dokumentiert. | MVP-Must |
| AC-003 | StR-138..147; StR-481..490; StR-592..597 | Täglicher inkrementeller Run ausführbar. | Testlauf | Neue Daten werden abgerufen, normalisiert, gespeichert, Features berechnet, Statuswerte erzeugt und Snapshot gespeichert. | MVP-Must |
| AC-004 | StR-392..396; StR-497..503 | Ausfall einzelner Quellen bricht Gesamtrun nicht unkontrolliert ab. | Fehlersimulation / Mock Source Failure | Run wird als partial_success gespeichert; Quelle in GUI, Logs und Snapshot sichtbar. | MVP-Must |
| AC-005 | StR-255..265; StR-568 | D0–D5 werden regelbasiert berechnet. | Regeltest + GUI-Prüfung | Für bewertbare Domänen A/B/D entsteht D0–D5 mit Treibern, Datenqualität und Regelverweis. | MVP-Must |
| AC-006 | StR-236..254; StR-569..574 | S0–S6 wird regelbasiert aus Domänenstatus abgeleitet. | Regeltest | S0–S6 ist reproduzierbar ableitbar und beitragende Domänen sind sichtbar. | MVP-Must |
| AC-007 | StR-226..235; StR-570 | Kein allgemeiner Gesamt-Risiko-Score wird erzeugt. | Code-/GUI-/Report-Review | System zeigt Domänenstatus und Multi-Domain-Status, aber keinen additiven A–E-Instabilitätswert. | MVP-Must |
| AC-008 | StR-089..117; StR-575..578 | Startseite zeigt Weltkarte. | GUI-Test | Karte färbt Länder nach Multi-Domain-Status, nutzt relative Baseline und erlaubt Drill-down. | MVP-Must |
| AC-009 | StR-018..023; StR-579 | Country Profile ist verfügbar. | GUI-Test | Landesprofil zeigt Multi-Domain-Status, D0–D5 je Domäne, Treiber, Gegenindikatoren, Coverage, Confidence und Events. | MVP-Must |
| AC-010 | StR-311..327; StR-580 | Detailansichten für A/B/D existieren. | GUI-Test | A/B/D zeigen Zeitreihen, Feature-Werte, Baselines, Anomalien, Treiber und Unsicherheiten. | MVP-Must |
| AC-011 | StR-013..017; StR-583..584 | Datenlage ist transparent. | GUI-Test | Quellenstatus, Historie, Datenfrische, Coverage, Confidence und failed sources sichtbar. | MVP-Must |
| AC-012 | StR-270..290; StR-585 | Analysten-Annotationen sind möglich. | GUI-Test + Datenbankprüfung | Annotationen zu Land/Domäne/Signal/Event/Snapshot werden gespeichert und angezeigt, ohne Status zu überschreiben. | MVP-Must |
| AC-013 | StR-301..310; StR-586..591 | Automatischer Daily Snapshot wird erzeugt. | Run-Test + Report-Review | Nach erfolgreichem/teilweise erfolgreichem Run entsteht Markdown- und JSON-Snapshot mit IDs, Statusänderungen, Datenlücken und Quellenfehlern. | MVP-Must |
| AC-014 | StR-291..310; StR-588..591 | Detailreports sind exportierbar. | GUI-Test | Country Profile, Domain Report und Coverage Report sind manuell als Markdown/JSON/CSV exportierbar. | MVP-Must |
| AC-015 | StR-382..391; StR-521..561 | Evidenzpfad ist nachvollziehbar. | Traceability-Review | Statuswert ist über Snapshot → Regel → Feature → Daten → Quelle rückverfolgbar. | MVP-Must |
| AC-016 | StR-358..381; StR-600..605 | Historische Referenzfälle sind prüfbar. | Backtest-Review | 10–15 Referenzfälle angelegt und mindestens ein Fall zeigt erwartete vs. beobachtete Domänenmuster. | MVP-Must |
| AC-017 | StR-417..451 | Daten-Governance ist dokumentiert. | Quellenkatalog- und Export-Review | Jede Quelle besitzt Lizenz-/Nutzungsinfos; personenbezogene Analyse nur für öffentliche/institutionelle Akteure mit Zweckbindung. | MVP-Must |
| AC-018 | StR-452..473 | Missbrauchsgrenzen sind berücksichtigt. | Funktionsreview | Keine Funktionen für Zielauswahl, operative Empfehlung, Desinformationsoptimierung, personenbezogenes Targeting oder ungeprüfte öffentliche Reports. | MVP-Must |

