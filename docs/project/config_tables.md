# Konfigurationstabellen

Importierte Konfigurationsfestlegungen. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Config_Tables`.

| Konfigurationstyp | Wert | Bedeutung | Festlegung |
| --- | --- | --- | --- |
| Country Priority | P1 | Core Focus Countries | möglichst A–E, tiefe Analyse |
| Country Priority | P2 | Extended Focus Countries | A/B/D mindestens, C/E optional |
| Country Priority | P3 | Control / Reference Countries | Kontroll-/Referenzländer, reduzierte Signaltiefe |
| Source Status | Core | MVP-relevante Pflicht-/Primärquelle | soll aktiv integriert werden |
| Source Status | Extended | nutzbare Zusatzquelle | kann im MVP oder danach integriert werden |
| Source Status | Prepared Adapter | technisch vorbereiten, nicht MVP-abhängig | z. B. ACLED, AIS, Telegram, X |
| Current Window | 7d | Startkarten-Default | aktuelle 7-Tage-Auffälligkeit |
| Current Window | 24h / 30d / 90d / 365d | umschaltbare Alternativen | für Detailanalyse |
| Baseline Mode | Combined 30/90/365 | Default | kurz-, mittel- und langfristige Referenz |
| Evaluation Mode | Relative Baseline | Default | Land gegen eigene Historie |
| Evaluation Mode | Global Comparison | optional | Länderübergreifender Vergleich, mit Coverage/Confidence |
| Data Horizon | >=3 Jahre | historischer Initialaufbau | sofern Quelle verfügbar |
| Run Mode | Daily Incremental | täglicher Betrieb | neue Daten + Snapshot |
| Fusion Rule | No General Fusion Score | MVP-Regel | keine additive A–E-Fusion |
| Map Default | Multi-Domain Status | Startseite | regelbasierter S0–S6-Status |
| Annotation Review | unreviewed/draft vorbereitet | MVP ohne Freigabeprozess | Annotation überschreibt Status nicht |
| Public Access | none | MVP | keine öffentliche Nutzerrolle |

