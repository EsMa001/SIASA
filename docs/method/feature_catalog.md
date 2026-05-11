# Feature-Katalog

Importierter Feature-Katalog. Quelle: `stakeholder_requirements_information_space_mvp_v0_4 (1).xlsx` / Sheet `Feature_Set`.

| Domäne | Feature ID | Feature | Bedeutung | Priorität |
| --- | --- | --- | --- | --- |
| A | A_news_volume | Newsvolumen | Anzahl relevanter Meldungen zu einem Land | Core |
| A | A_news_volume_anomaly | Newsvolumen-Anomalie | Abweichung vom normalen Medienaufkommen | Core |
| A | A_source_count | Quellenanzahl | Anzahl unterschiedlicher berichtender Quellen | Core |
| A | A_source_diversity_index | Quellenvielfalt | Misst, ob viele unabhängige Quellen berichten | Core |
| A | A_source_dependency_score | Quellenabhängigkeit | Hinweis auf Replikation/geringe Unabhängigkeit | Extended |
| A | A_duplicate_story_ratio | Duplikat-/Replikationsanteil | Anteil ähnlicher/gleicher Meldungen | Extended |
| A | A_first_seen_source | Erste beobachtete Quelle | Ursprung oder früheste bekannte Quelle | Extended |
| A | A_amplification_factor | Verstärkungsgrad | Wie stark sich ein Thema ausbreitet | Extended |
| A | A_persistence_score | Persistenz | Wie lange ein Thema sichtbar bleibt | Extended |
| A | A_tone_mean | Mittlere Tonalität | Durchschnittliche Tonalität der Berichterstattung | Core |
| A | A_tone_shift | Tonalitätsverschiebung | Veränderung der Sprache gegenüber Baseline | Core |
| A | A_negative_tone_share | Negativer Tonanteil | Anteil stark negativer Berichterstattung | Extended |
| A | A_topic_distribution | Themenverteilung | Welche Themen dominieren | Core |
| A | A_topic_shift_score | Themenverschiebung | Änderung der Themenstruktur | Core |
| A | A_narrative_cluster_count | Narrativcluster | Anzahl erkannter semantischer Cluster | Advanced |
| A | A_narrative_shift_score | Narrativverschiebung | Neue oder stark veränderte Narrative | Advanced |
| A | A_official_statement_count | Offizielle Statements | Anzahl relevanter offizieller Erklärungen | Extended |
| A | A_official_escalation_signal | Eskalative offizielle Sprache | Drohungen, Warnungen, Sanktionen, Vorwürfe | Extended |
| A | A_cross_country_spread | Länderübergreifende Ausbreitung | Ob ein Thema in andere Länderkontexte springt | Advanced |
| A | A_information_velocity | Informationsgeschwindigkeit | Geschwindigkeit der Verbreitung | Advanced |
| B | B_event_count | Ereignisanzahl | Anzahl relevanter Ereignisse | Core |
| B | B_event_count_anomaly | Ereignisanomalie | Abweichung von normaler Ereignisfrequenz | Core |
| B | B_event_type_distribution | Ereignistypen | Protest, Gewalt, Konflikt, Katastrophe, humanitär | Core |
| B | B_event_type_shift | Ereignistypwechsel | Ungewöhnliche Veränderung der Ereignisarten | Extended |
| B | B_violent_event_count | Gewaltsame Ereignisse | Anzahl Gewalt-/Konfliktereignisse | Core |
| B | B_violent_event_share | Gewaltanteil | Anteil gewaltsamer Ereignisse | Extended |
| B | B_fatality_count | Todesfälle | Aggregierte Todeszahlen, soweit verfügbar | Extended |
| B | B_fatality_anomaly | Todesfallanomalie | Abweichung zur historischen Schwere | Extended |
| B | B_protest_event_count | Protestereignisse | Anzahl Protest-/Mobilisierungsereignisse | Core |
| B | B_protest_anomaly | Protestanomalie | Ungewöhnlicher Protestanstieg | Core |
| B | B_geo_cluster_score | Geografische Clusterung | Räumliche Häufung von Ereignissen | Core |
| B | B_temporal_cluster_score | Zeitliche Clusterung | Ereignisse häufen sich kurzfristig | Advanced |
| B | B_event_novelty_score | Ereignisneuheit | Ungewöhnlicher Ereignistyp für dieses Land | Advanced |
| B | B_humanitarian_report_count | Humanitäre Berichte | Relevante ReliefWeb-/Krisenberichte | Extended |
| B | B_disaster_alert_level | Katastrophenwarnniveau | GDACS-/Disaster-Signal | Extended |
| B | B_event_source_agreement | Quellenübereinstimmung | Ob verschiedene Quellen ähnliche Ereignisse melden | Extended |
| B | B_reporting_delay_estimate | Meldeverzug | Erwartete Verzögerung der Ereignisquellen | Advanced |
| C | C_fire_count | Feuer-/Thermalereignisse | Anzahl FIRMS-Detektionen | Selective P1 Core |
| C | C_fire_anomaly | Feueranomalie | Abweichung von saisonaler Feuerbaseline | Selective P1 Core |
| C | C_fire_cluster_score | Feuercluster | Räumliche Häufung thermischer Signale | Selective P1 Core |
| C | C_nightlight_delta | Nachtlichtänderung | Veränderung von Lichtemissionen | Selective P1 Core |
| C | C_nightlight_drop_anomaly | Nachtlichtabfall | Möglicher Hinweis auf Strom-/Aktivitätsausfall | Selective P1 Core |
| C | C_air_traffic_volume | Flugverkehrsvolumen | Anzahl sichtbarer Flugbewegungen | Selective P1 Extended |
| C | C_air_traffic_change | Flugverkehrsänderung | Abweichung von Normalmuster | Selective P1 Extended |
| C | C_airspace_disruption_signal | Luftraumstörung | Ungewöhnliche Reduktion/Umlenkung | Selective P1 Extended |
| C | C_port_activity_proxy | Hafenaktivität | Später über AIS/Proxy-Daten | Prepared/Later |
| C | C_maritime_route_change | Maritime Routenänderung | Später über AIS | Prepared/Later |
| C | C_infrastructure_disruption_signal | Infrastrukturstörung | Physische Hinweise auf Ausfälle/Schäden | Prepared/Later |
| C | C_environmental_shock_signal | Umwelt-/Naturereignis | Dürre, Hochwasser, Feuer, Sturm | Selective P1 Extended |
| C | C_physical_signal_confidence | Signalbelastbarkeit | Qualität der physischen Beobachtung | Meta |
| C | C_interpretation_uncertainty | Interpretationsunsicherheit | Routine vs. Auffälligkeit unklar | Meta |
| D | D_inflation_yoy | Inflation | Preisstress | Core |
| D | D_inflation_anomaly | Inflationsanomalie | Abweichung von eigener Historie | Core |
| D | D_exchange_rate_change | Wechselkursänderung | Währungsstress | Core |
| D | D_exchange_rate_volatility | Wechselkursvolatilität | Instabilität der Währung | Core |
| D | D_gdp_growth | Wirtschaftswachstum | Makroökonomischer Kontext | Core |
| D | D_unemployment_rate | Arbeitslosigkeit | Sozialer/wirtschaftlicher Druck | Core |
| D | D_food_price_proxy | Nahrungsmittelstress | Preis-/Versorgungsdruck | Extended |
| D | D_food_import_dependency | Nahrungsmittelabhängigkeit | Importabhängigkeit | Extended |
| D | D_energy_import_dependency | Energieabhängigkeit | Strukturelle Energieverwundbarkeit | Extended |
| D | D_energy_price_stress | Energiepreisstress | Energiepreisdruck, soweit verfügbar | Extended |
| D | D_trade_volume_change | Handelsvolumenänderung | Veränderung Import/Export | Extended |
| D | D_trade_concentration_index | Handelskonzentration | Abhängigkeit von wenigen Partnern | Extended |
| D | D_commodity_exposure_score | Rohstoffexposition | Verwundbarkeit gegenüber Rohstoffpreisen | Advanced |
| D | D_current_account_signal | Leistungsbilanzsignal | Externer Finanzdruck | Advanced |
| D | D_debt_stress_proxy | Schuldendruck | Struktureller Finanzstress | Advanced |
| D | D_structural_vulnerability_index | Strukturelle Vulnerabilität | Zusammenfassender D-interner Kontextindikator | Advanced |
| D | D_macro_data_freshness | Aktualität Makrodaten | Viele D-Daten sind verzögert | Meta |
| D | D_revision_uncertainty | Revisionsunsicherheit | Spätere Datenkorrekturen möglich | Meta |
| E | E_outage_count | Internet-/Service-Outages | Anzahl technischer Störungen | Selective P1 Core |
| E | E_outage_anomaly | Outage-Anomalie | Ungewöhnliche Häufung/Stärke | Selective P1 Core |
| E | E_traffic_drop_magnitude | Traffic-Rückgang | Ausmaß eines Internet-Traffic-Einbruchs | Selective P1 Core |
| E | E_traffic_drop_duration | Dauer des Rückgangs | Persistenz einer Störung | Selective P1 Extended |
| E | E_cloudflare_outage_signal | Cloudflare-Signal | Technische Störung laut Cloudflare | Selective P1 Core |
| E | E_google_traffic_disruption | Google-Traffic-Signal | Regionale Traffic-Anomalie | Selective P1 Core |
| E | E_cve_count | CVE-Anzahl | Schwachstellenaktivität | Selective P1 Extended |
| E | E_high_severity_cve_count | Schwere CVEs | CVSS-/Severity-basierte Zählung | Selective P1 Extended |
| E | E_kev_count | KEV-Anzahl | Bekannte aktiv ausgenutzte Schwachstellen | Selective P1 Extended |
| E | E_kev_trend | KEV-Trend | Veränderung aktiver Exploit-Dynamik | Selective P1 Extended |
| E | E_cert_advisory_count | CERT-Warnungen | Nationale/regionale Warnmeldungen | Selective P1 Extended |
| E | E_infoops_case_count | InfoOps-Fälle | Desinformations-/Kampagnenfälle | Advanced |
| E | E_technical_source_agreement | Technische Quellenübereinstimmung | Mehrere technische Quellen bestätigen Signal | Advanced |
| E | E_country_attribution_uncertainty | Länderzuordnungsunsicherheit | Belastbarkeit des Länderbezugs | Advanced |
| E | E_attribution_risk_flag | Attribution-Risk-Flag | Warnt vor vorschneller Zuschreibung | Advanced |
| E | E_technical_signal_confidence | Technische Confidence | Belastbarkeit der technischen Signale | Meta |
| X | X_domain_coverage_score | Datenabdeckung je Domäne | Coverage der Domäne | Meta Core |
| X | X_domain_confidence_score | Belastbarkeit je Domäne | Confidence der Domänenbewertung | Meta Core |
| X | X_domain_uncertainty_score | Unsicherheit je Domäne | Gesamtunsicherheit | Meta Core |
| X | X_data_freshness_score | Datenaktualität | Aktualität der Daten | Meta Core |
| X | X_historical_depth_score | Historische Tiefe | Verfügbare Historie | Meta Core |
| X | X_missing_data_flag | Datenlücken | Fehlende Daten | Meta Core |
| X | X_source_failure_flag | Quellenfehler | Fehlgeschlagene Quelle | Meta Core |
| X | X_source_dependency_score | Quellenabhängigkeit | Redundanz/Abhängigkeit | Meta Extended |
| X | X_cross_domain_alignment_flag | Cross-Domain-Alignment | Mehrere Domänen auffällig | Meta Core |
| X | X_cross_domain_contradiction_flag | Cross-Domain-Widerspruch | Domänen widersprechen sich | Meta Core |
| X | X_active_domains | Bewertbare Domänen | Aktive Domänen | Meta Core |
| X | X_anomalous_domains | Auffällige Domänen | Domänen mit D2-D4 | Meta Core |
| X | X_unavailable_domains | Nicht bewertbare Domänen | D0-Domänen | Meta Core |
| X | X_status_driver_list | Statustreiber | Wichtigste Treiber | Meta Core |
| X | X_counter_signal_list | Gegenindikatoren | Widersprechende Signale | Meta Core |
| X | X_annotation_count | Annotationenzahl | Anzahl Analystenhinweise | Meta Extended |
| X | X_recent_annotation_flag | Neue Annotation | Neue relevante Annotation vorhanden | Meta Extended |

