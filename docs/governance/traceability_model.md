# Traceability-Modell

Importiertes Traceability-Zielmodell. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Traceability_Model`.

| Ebene | Beschreibung | Mindestmetadaten |
| --- | --- | --- |
| Source | Datenquelle im Quellenkatalog | source_id, domain, status, access, license, history |
| Raw Data | Unveränderte Quellendaten | raw_record_id, source_id, fetched_at, raw_payload/reference |
| Normalized Data | Einheitliches länder-/zeitbezogenes Format | normalized_id, country_id, timestamp, event/signal fields |
| Feature | Extrahierter Indikator | feature_id, value, window, baseline, confidence, coverage |
| Domain Status | D0–D5 je Domäne | domain_status_id, domain, rule_version, drivers, uncertainty |
| Multi-Domain Status | S0–S6 je Land/Snapshot | status_id, active_domains, anomalous_domains, rule_trigger |
| Snapshot | Versionierter Analysezustand | snapshot_id, run_id, country_set, algorithm_version, data_version |
| Report | Exportierter Bericht | report_id, snapshot_id, report_type, format, generated_at |
| Annotation | Manuelle Kontextnotiz | annotation_id, author, scope, tags, review_status |

