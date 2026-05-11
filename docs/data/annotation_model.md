# Annotationsmodell

Importiertes Modell fuer Analysten-Annotationen. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Annotation_Model`.

| Feld | Bedeutung | Beispiel / Werte |
| --- | --- | --- |
| annotation_id | eindeutige ID | ANN-2026-000123 |
| created_at | Zeitstempel | 46153.572916666664 |
| author | Ersteller | analyst |
| scope | Bezugspunkt | country/domain/signal/event/snapshot |
| annotation_type | Typ | context_note / false_positive_note / source_quality_note / lineage_note / review_note |
| severity_assessment | fachliche Einschätzung | not_security_relevant / relevant / uncertain |
| confidence_assessment | Analysten-Confidence | low / medium / high |
| text | Freitext | News spike appears driven by replicated agency report. |
| tags | Schlagworte | source_dependency, possible_false_positive |
| linked_items | verknüpfte Objekte | SRC-GDELT, EVENT-CLUSTER-456 |
| review_status | vorbereitet, aber nicht verpflichtend | unreviewed / draft / reviewed / accepted / rejected |

