# Systemgrenzen

Importierte Systemgrenzen und Verantwortlichkeiten. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `System_Boundaries`.

| Bereich | Gehört zum System? | Beschreibung / Verantwortung |
| --- | --- | --- |
| Quellenkatalog | ja | Verwaltet Datenquellen, Status, Lizenzen, Metadaten. |
| Source Adapter | ja | Ruft externe Daten ab und kapselt Datenzugang. |
| Raw Data Store | ja | Speichert zulässige Roh-/Referenzdaten. |
| Normalization Layer | ja | Überführt Daten in internes Schema. |
| Feature Layer | ja | Berechnet domänenspezifische Features. |
| Baseline / Anomaly Engine | ja | Berechnet Baselines und Abweichungen. |
| Status Engine | ja | Berechnet D0–D5 und S0–S6. |
| Snapshot Management | ja | Speichert Analysezustände. |
| Reporting Layer | ja | Erzeugt Reports / Exporte. |
| GUI / Analysis Cockpit | ja | Zeigt Karte, Profile, Domänen, Coverage, Reports. |
| Annotation Store | ja | Speichert Analystenkommentare. |
| Validation / Backtest Module | ja | Verwaltet Referenzfälle und Backtests. |
| Externe Datenquellen | nein | Liefern Daten; Verfügbarkeit und Richtigkeit liegen außerhalb der Systemkontrolle. |
| Hermes / Agent | nein / vorbereitet | Späterer externer Orchestrator; keine autonome Veröffentlichung oder Regeländerung im MVP. |
| Öffentliche Webplattform | nein | Nicht Teil des MVP. |

