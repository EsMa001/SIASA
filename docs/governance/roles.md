# Rollenmodell

Importierte Rollen, Rechte und Grenzen. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Roles`.

| Rolle | Status | Rechte / Aufgaben | Grenzen |
| --- | --- | --- | --- |
| Admin/Developer | MVP Pflicht | Quellen, Adapter, Ländersets, Regeln, Runs, Reprocessing, Datenbank, Systemkonfiguration | Daten löschen/ändern, Reprocessing starten, Quellen deaktivieren/aktivieren, Regeln versionieren |
| Analyst | MVP Pflicht | GUI-Analyse, Drill-downs, Annotationen, Reports, Export | Darf automatische Statuswerte nicht überschreiben; Annotationen werden daneben dokumentiert |
| Viewer/Reader | Optional vorbereitet | Read-only Zugriff auf Dashboards/Reports | Keine Annotationen, keine Konfigurationsänderungen |
| Public User | Nicht MVP | Keine öffentliche Nutzung im MVP | Public Dashboard/Website explizit ausgeschlossen |

