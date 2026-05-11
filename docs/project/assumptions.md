# Annahmen

Importierte Projektannahmen. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Assumptions`.

| ID | Kategorie | Annahme |
| --- | --- | --- |
| AS-001 | Daten | Für die MVP-Länder sind ausreichend Open-Source-Daten in Core-Domänen A, B und D verfügbar. |
| AS-002 | Daten | Für viele Quellen ist ein historischer Datenhorizont von mindestens 3 Jahren verfügbar. |
| AS-003 | Daten | Nicht alle Quellen liefern für alle Länder gleich gute Datenqualität. |
| AS-004 | Daten | Quellenhistorie, Datenlücken und Aktualität unterscheiden sich je Quelle erheblich. |
| AS-005 | Daten | Externe Datenquellen können Schnittstellen, Nutzungsbedingungen oder Datenformate ändern. |
| AS-006 | Daten | Einige Quellen sind nur mit API-Key, Registrierung oder Rate Limits nutzbar. |
| AS-007 | Daten | ACLED steht im MVP nicht als verfügbare Core-Quelle zur Verfügung und wird nur als Prepared Adapter vorgesehen. |
| AS-008 | Daten | GDELT, UCDP, World Bank, IMF und weitere Quellen reichen aus, um einen ersten methodischen MVP aufzubauen. |
| AS-009 | Methodik | A–E messen unterschiedliche, nicht direkt gleichartige Phänomene. |
| AS-010 | Methodik | Direkte additive Fusion zu einem allgemeinen Gesamt-Score ist im MVP nicht belastbar. |
| AS-011 | Methodik | Domänenspezifische Analyse mit regelbasierter Cross-Domain-Kontrastierung ist für den MVP geeigneter als ein komplexes probabilistisches Modell. |
| AS-012 | Methodik | Relative Baselines je Land sind im Default aussagekräftiger als direkte globale Vergleiche. |
| AS-013 | Methodik | Multi-Window-Baseline mit 30/90/365 Tagen ist robuster als ein einzelnes Baseline-Fenster. |
| AS-014 | Methodik | D0–D5 je Domäne und S0–S6 als Multi-Domain-Status reichen für den MVP als erklärbares Statusmodell aus. |
| AS-015 | Methodik | Analysten-Annotationen verbessern die Bewertung, überschreiben automatische Statuswerte im MVP aber nicht. |
| AS-016 | Betrieb | Der MVP wird zunächst lokal betrieben. |
| AS-017 | Betrieb | Tägliche Runs können über einfachen Scheduler/Cron-artigen Mechanismus ausgeführt werden. |
| AS-018 | Betrieb | Performance ist im MVP weniger kritisch als Nachvollziehbarkeit, Robustheit und Traceability. |
| AS-019 | Betrieb | Docker-/Containerfähigkeit ist sinnvoll, Hochverfügbarkeit aber nicht erforderlich. |
| AS-020 | Betrieb | Hermes wird höchstens später als kontrollierter Orchestrator genutzt. |
| AS-021 | Nutzer/Governance | Der MVP wird primär durch Admin/Developer und Analyst genutzt. |
| AS-022 | Nutzer/Governance | Es gibt im MVP keine öffentliche Nutzerrolle. |
| AS-023 | Nutzer/Governance | Personenbezogene Analyse ist nur begrenzt für öffentliche/institutionelle Akteurskommunikation relevant. |
| AS-024 | Nutzer/Governance | Reports werden im MVP nicht automatisch öffentlich veröffentlicht. |
| AS-025 | Nutzer/Governance | Öffentliche Nutzung oder Veröffentlichung erfordert später eine zusätzliche Review-Stufe. |

