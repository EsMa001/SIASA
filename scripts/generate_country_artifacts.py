#!/usr/bin/env python3
"""Generate country profile and domain detail artifacts for all 29 MVP countries."""
import json
import os
import pathlib

BASE = pathlib.Path("/opt/data/SIASA/sample_artifacts")
PROFILES_DIR = BASE / "readmodels" / "country_profiles"
DOMAIN_DIR = BASE / "readmodels" / "domain_details"
EXPORTS_DIR = BASE / "exports" / "country_profile"

# Existing countries (skip)
EXISTING = {"ISR", "POL", "TWN", "UKR"}

# Country data: (name, priority, selection_type, region, rationale, status, domains, domain_states)
# domain_states: A, B (optional), D (optional)
# Anomaly: D0=stable, D1=mild, D2=moderate, D3=elevated, D4=high, D5=critical
COUNTRIES = [
    # P1 Core Focus
    {
        "id": "RUS",
        "name": "Russia",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "Europe / Eurasia",
        "rationale": "Krieg, hybride Konflikte, Desinformation, geopolitische Eskalation",
        "status": "S4",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D3", "B": "D4", "D": "D3"},
        "drivers_A": True, "drivers_B": True, "drivers_D": True,
        "feature_A": {"A_news_volume": 18.0, "A_source_count": 4.0, "A_source_diversity_index": 0.75},
        "feature_B": {"B_event_count": 89.0, "B_violent_event_count": 52.0, "B_protest_event_count": 5.0,
                      "B_violent_event_share": 0.584, "B_disaster_alert_level": 1.0,
                      "B_event_type_distribution": {"conflict": 0.708, "violent": 0.584, "protest": 0.056}},
        "feature_D": {"D_trade_volume_change": -22.5, "D_gdp_growth": -3.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 4.0), ("article_count", "2026-04-22T10:15:00Z", 5.0),
                 ("article_count", "2026-04-20T09:00:00Z", 4.5), ("article_count", "2026-04-18T14:30:00Z", 3.8)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 63.0), ("violent_event_count", "2026-05-20T20:30:00Z", 52.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 5.0)],
        "ts_D": [("gdp_growth", "2024", -3.8), ("trade_volume_change", "2024", -22.5)],
        "linked_events": ["EVT-RUS-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 8.2}, {"label": "2026-04", "value": 4.1}, {"label": "2026-05", "value": 18.0}],
    },
    {
        "id": "CHN",
        "name": "China",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "Asia / Pacific",
        "rationale": "Taiwan-Spannung, Großmacht, Handelskrieg, Informationskontrolle",
        "status": "S3",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D2", "B": "D3", "D": "D2"},
        "feature_A": {"A_news_volume": 14.0, "A_source_count": 3.0, "A_source_diversity_index": 0.6},
        "feature_B": {"B_event_count": 45.0, "B_violent_event_count": 18.0, "B_protest_event_count": 8.0,
                      "B_violent_event_share": 0.4, "B_disaster_alert_level": 0.5,
                      "B_event_type_distribution": {"conflict": 0.6, "violent": 0.4, "protest": 0.178}},
        "feature_D": {"D_trade_volume_change": -5.2, "D_gdp_growth": 4.9, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 3.5), ("article_count", "2026-04-22T10:15:00Z", 3.8),
                 ("article_count", "2026-04-20T09:00:00Z", 3.2), ("article_count", "2026-04-18T14:30:00Z", 3.0)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 27.0), ("violent_event_count", "2026-05-20T20:30:00Z", 18.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 8.0)],
        "ts_D": [("gdp_growth", "2024", 4.9), ("trade_volume_change", "2024", -5.2)],
        "linked_events": ["EVT-CHN-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 5.5}, {"label": "2026-04", "value": 3.5}, {"label": "2026-05", "value": 14.0}],
    },
    {
        "id": "IRN",
        "name": "Iran",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "Middle East",
        "rationale": "Sanktionen, Proteste, Nuklearprogramm, regionale Spannungen",
        "status": "S3",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D2", "B": "D3", "D": "D2"},
        "feature_A": {"A_news_volume": 11.0, "A_source_count": 3.0, "A_source_diversity_index": 0.55},
        "feature_B": {"B_event_count": 38.0, "B_violent_event_count": 22.0, "B_protest_event_count": 12.0,
                      "B_violent_event_share": 0.579, "B_disaster_alert_level": 0.5,
                      "B_event_type_distribution": {"conflict": 0.421, "violent": 0.579, "protest": 0.316}},
        "feature_D": {"D_trade_volume_change": -18.0, "D_gdp_growth": 3.1, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.8), ("article_count", "2026-04-22T10:15:00Z", 3.1),
                 ("article_count", "2026-04-20T09:00:00Z", 2.5), ("article_count", "2026-04-18T14:30:00Z", 2.9)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 16.0), ("violent_event_count", "2026-05-20T20:30:00Z", 22.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 12.0)],
        "ts_D": [("gdp_growth", "2024", 3.1), ("trade_volume_change", "2024", -18.0)],
        "linked_events": ["EVT-IRN-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 4.8}, {"label": "2026-04", "value": 2.8}, {"label": "2026-05", "value": 11.0}],
    },
    {
        "id": "TUR",
        "name": "Turkey",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "Europe / Middle East",
        "rationale": "Geopolitische Brückenfunktion, Inflation, politische Instabilität",
        "status": "S2",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D1", "B": "D2", "D": "D2"},
        "feature_A": {"A_news_volume": 7.5, "A_source_count": 3.0, "A_source_diversity_index": 0.45},
        "feature_B": {"B_event_count": 24.0, "B_violent_event_count": 9.0, "B_protest_event_count": 7.0,
                      "B_violent_event_share": 0.375, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.375, "violent": 0.375, "protest": 0.292}},
        "feature_D": {"D_trade_volume_change": 2.8, "D_gdp_growth": 2.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.0), ("article_count", "2026-04-22T10:15:00Z", 1.8),
                 ("article_count", "2026-04-20T09:00:00Z", 2.2), ("article_count", "2026-04-18T14:30:00Z", 1.9)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 9.0), ("violent_event_count", "2026-05-20T20:30:00Z", 9.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 7.0)],
        "ts_D": [("gdp_growth", "2024", 2.5), ("trade_volume_change", "2024", 2.8)],
        "linked_events": ["EVT-TUR-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 3.2}, {"label": "2026-04", "value": 2.0}, {"label": "2026-05", "value": 7.5}],
    },
    {
        "id": "IND",
        "name": "India",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "South Asia",
        "rationale": "Regionale Großmacht, Grenzspannungen, innenpolitische Dynamik",
        "status": "S2",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D1", "B": "D2", "D": "D1"},
        "feature_A": {"A_news_volume": 8.0, "A_source_count": 3.0, "A_source_diversity_index": 0.5},
        "feature_B": {"B_event_count": 28.0, "B_violent_event_count": 10.0, "B_protest_event_count": 9.0,
                      "B_violent_event_share": 0.357, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.357, "violent": 0.357, "protest": 0.321}},
        "feature_D": {"D_trade_volume_change": 5.5, "D_gdp_growth": 6.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.2), ("article_count", "2026-04-22T10:15:00Z", 2.0),
                 ("article_count", "2026-04-20T09:00:00Z", 1.9), ("article_count", "2026-04-18T14:30:00Z", 2.1)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 10.0), ("violent_event_count", "2026-05-20T20:30:00Z", 10.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 9.0)],
        "ts_D": [("gdp_growth", "2024", 6.5), ("trade_volume_change", "2024", 5.5)],
        "linked_events": ["EVT-IND-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 3.8}, {"label": "2026-04", "value": 2.2}, {"label": "2026-05", "value": 8.0}],
    },
    {
        "id": "PAK",
        "name": "Pakistan",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "South Asia",
        "rationale": "Fragilität, Instabilität, wirtschaftliche Krise, Nuklearstaat",
        "status": "S3",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D2", "D": "D2"},
        "feature_A": {"A_news_volume": 9.0, "A_source_count": 2.0, "A_source_diversity_index": 0.4},
        "feature_D": {"D_trade_volume_change": -8.5, "D_gdp_growth": 1.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.5), ("article_count", "2026-04-22T10:15:00Z", 2.2),
                 ("article_count", "2026-04-20T09:00:00Z", 2.0), ("article_count", "2026-04-18T14:30:00Z", 2.3)],
        "ts_D": [("gdp_growth", "2024", 1.8), ("trade_volume_change", "2024", -8.5)],
        "linked_events": ["EVT-PAK-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 4.2}, {"label": "2026-04", "value": 2.5}, {"label": "2026-05", "value": 9.0}],
    },
    {
        "id": "GEO",
        "name": "Georgia",
        "priority": "P1",
        "selection_type": "Core Focus",
        "region": "Caucasus",
        "rationale": "Proteste, russischer Einfluss, EU-Annäherung, geopolitische Lage",
        "status": "S2",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D2", "D": "D1"},
        "feature_A": {"A_news_volume": 6.5, "A_source_count": 2.0, "A_source_diversity_index": 0.38},
        "feature_D": {"D_trade_volume_change": 3.2, "D_gdp_growth": 5.1, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.8), ("article_count", "2026-04-22T10:15:00Z", 1.6),
                 ("article_count", "2026-04-20T09:00:00Z", 1.9), ("article_count", "2026-04-18T14:30:00Z", 1.7)],
        "ts_D": [("gdp_growth", "2024", 5.1), ("trade_volume_change", "2024", 3.2)],
        "linked_events": ["EVT-GEO-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 2.8}, {"label": "2026-04", "value": 1.8}, {"label": "2026-05", "value": 6.5}],
    },
    # P2 Extended Focus
    {
        "id": "USA",
        "name": "United States",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "North America",
        "rationale": "Globale Führungsmacht, innenpolitische Polarisierung, Außenpolitik",
        "status": "S1",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D1", "D": "D0"},
        "feature_A": {"A_news_volume": 10.0, "A_source_count": 4.0, "A_source_diversity_index": 0.85},
        "feature_B": {"B_event_count": 18.0, "B_violent_event_count": 4.0, "B_protest_event_count": 8.0,
                      "B_violent_event_share": 0.222, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.222, "violent": 0.222, "protest": 0.444}},
        "feature_D": {"D_trade_volume_change": 1.2, "D_gdp_growth": 2.3, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.5), ("article_count", "2026-04-22T10:15:00Z", 2.8),
                 ("article_count", "2026-04-20T09:00:00Z", 2.3), ("article_count", "2026-04-18T14:30:00Z", 2.6)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 4.0), ("violent_event_count", "2026-05-20T20:30:00Z", 4.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 8.0)],
        "ts_D": [("gdp_growth", "2024", 2.3), ("trade_volume_change", "2024", 1.2)],
        "linked_events": ["EVT-USA-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 2.8}, {"label": "2026-04", "value": 2.5}, {"label": "2026-05", "value": 10.0}],
    },
    {
        "id": "DEU",
        "name": "Germany",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Europe",
        "rationale": "Zentrale EU-Macht, wirtschaftliche Bedeutung, geopolitischer Einfluss",
        "status": "S1",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D1", "D": "D1"},
        "feature_A": {"A_news_volume": 6.0, "A_source_count": 3.0, "A_source_diversity_index": 0.7},
        "feature_B": {"B_event_count": 12.0, "B_violent_event_count": 2.0, "B_protest_event_count": 5.0,
                      "B_violent_event_share": 0.167, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.167, "violent": 0.167, "protest": 0.417}},
        "feature_D": {"D_trade_volume_change": -0.8, "D_gdp_growth": 0.2, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.5), ("article_count", "2026-04-22T10:15:00Z", 1.8),
                 ("article_count", "2026-04-20T09:00:00Z", 1.6), ("article_count", "2026-04-18T14:30:00Z", 1.4)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 2.0), ("violent_event_count", "2026-05-20T20:30:00Z", 2.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 5.0)],
        "ts_D": [("gdp_growth", "2024", 0.2), ("trade_volume_change", "2024", -0.8)],
        "linked_events": ["EVT-DEU-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 1.8}, {"label": "2026-04", "value": 1.5}, {"label": "2026-05", "value": 6.0}],
    },
    {
        "id": "EST",
        "name": "Estonia",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Baltic / NATO",
        "rationale": "Cyber-Bedrohungen, NATO-Ostflanke, russischer Einfluss",
        "status": "S1",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D1", "D": "D0"},
        "feature_A": {"A_news_volume": 4.5, "A_source_count": 2.0, "A_source_diversity_index": 0.5},
        "feature_D": {"D_trade_volume_change": 1.5, "D_gdp_growth": 1.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.2), ("article_count", "2026-04-22T10:15:00Z", 1.1),
                 ("article_count", "2026-04-20T09:00:00Z", 1.3), ("article_count", "2026-04-18T14:30:00Z", 1.0)],
        "ts_D": [("gdp_growth", "2024", 1.8), ("trade_volume_change", "2024", 1.5)],
        "linked_events": ["EVT-EST-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 1.5}, {"label": "2026-04", "value": 1.2}, {"label": "2026-05", "value": 4.5}],
    },
    {
        "id": "FIN",
        "name": "Finland",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Nordic / NATO",
        "rationale": "Neue NATO-Mitglied, Grenze zu Russland, Sicherheitsrelevanz",
        "status": "S1",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 3.5, "A_source_count": 2.0, "A_source_diversity_index": 0.55},
        "feature_D": {"D_trade_volume_change": 1.2, "D_gdp_growth": 1.4, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.9), ("article_count", "2026-04-22T10:15:00Z", 1.0),
                 ("article_count", "2026-04-20T09:00:00Z", 0.8), ("article_count", "2026-04-18T14:30:00Z", 0.9)],
        "ts_D": [("gdp_growth", "2024", 1.4), ("trade_volume_change", "2024", 1.2)],
        "linked_events": ["EVT-FIN-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 1.2}, {"label": "2026-04", "value": 0.9}, {"label": "2026-05", "value": 3.5}],
    },
    {
        "id": "SAU",
        "name": "Saudi Arabia",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Middle East / Gulf",
        "rationale": "Energiepolitik, Vision 2030, regionale Machtdynamik",
        "status": "S1",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D1", "D": "D1"},
        "feature_A": {"A_news_volume": 5.5, "A_source_count": 3.0, "A_source_diversity_index": 0.45},
        "feature_B": {"B_event_count": 10.0, "B_violent_event_count": 3.0, "B_protest_event_count": 1.0,
                      "B_violent_event_share": 0.3, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.3, "violent": 0.3, "protest": 0.1}},
        "feature_D": {"D_trade_volume_change": 4.2, "D_gdp_growth": 2.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.4), ("article_count", "2026-04-22T10:15:00Z", 1.3),
                 ("article_count", "2026-04-20T09:00:00Z", 1.5), ("article_count", "2026-04-18T14:30:00Z", 1.2)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 3.0), ("violent_event_count", "2026-05-20T20:30:00Z", 3.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 1.0)],
        "ts_D": [("gdp_growth", "2024", 2.8), ("trade_volume_change", "2024", 4.2)],
        "linked_events": ["EVT-SAU-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 2.0}, {"label": "2026-04", "value": 1.4}, {"label": "2026-05", "value": 5.5}],
    },
    {
        "id": "QAT",
        "name": "Qatar",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Middle East / Gulf",
        "rationale": "Energiereserven, geopolitische Vermittlerrolle, Finanzinvestitionen",
        "status": "S1",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 3.0, "A_source_count": 2.0, "A_source_diversity_index": 0.4},
        "feature_D": {"D_trade_volume_change": 6.5, "D_gdp_growth": 3.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.8), ("article_count", "2026-04-22T10:15:00Z", 0.7),
                 ("article_count", "2026-04-20T09:00:00Z", 0.9), ("article_count", "2026-04-18T14:30:00Z", 0.8)],
        "ts_D": [("gdp_growth", "2024", 3.5), ("trade_volume_change", "2024", 6.5)],
        "linked_events": ["EVT-QAT-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 1.2}, {"label": "2026-04", "value": 0.8}, {"label": "2026-05", "value": 3.0}],
    },
    {
        "id": "NGA",
        "name": "Nigeria",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "West Africa",
        "rationale": "Fragilität, Sicherheitslage, wirtschaftliche Bedeutung, Bevölkerungsgröße",
        "status": "S2",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D1", "B": "D2", "D": "D2"},
        "feature_A": {"A_news_volume": 6.5, "A_source_count": 2.0, "A_source_diversity_index": 0.42},
        "feature_B": {"B_event_count": 22.0, "B_violent_event_count": 14.0, "B_protest_event_count": 4.0,
                      "B_violent_event_share": 0.636, "B_disaster_alert_level": 0.5,
                      "B_event_type_distribution": {"conflict": 0.636, "violent": 0.636, "protest": 0.182}},
        "feature_D": {"D_trade_volume_change": -3.5, "D_gdp_growth": 2.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.7), ("article_count", "2026-04-22T10:15:00Z", 1.5),
                 ("article_count", "2026-04-20T09:00:00Z", 1.8), ("article_count", "2026-04-18T14:30:00Z", 1.6)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 14.0), ("violent_event_count", "2026-05-20T20:30:00Z", 14.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 4.0)],
        "ts_D": [("gdp_growth", "2024", 2.5), ("trade_volume_change", "2024", -3.5)],
        "linked_events": ["EVT-NGA-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 3.0}, {"label": "2026-04", "value": 1.7}, {"label": "2026-05", "value": 6.5}],
    },
    {
        "id": "EGY",
        "name": "Egypt",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "North Africa / Middle East",
        "rationale": "Regionale Stabilität, wirtschaftliche Krise, Suezkanal, Grenze Gaza",
        "status": "S2",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D1", "B": "D2", "D": "D2"},
        "feature_A": {"A_news_volume": 7.0, "A_source_count": 2.0, "A_source_diversity_index": 0.38},
        "feature_B": {"B_event_count": 20.0, "B_violent_event_count": 8.0, "B_protest_event_count": 5.0,
                      "B_violent_event_share": 0.4, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.4, "violent": 0.4, "protest": 0.25}},
        "feature_D": {"D_trade_volume_change": -12.5, "D_gdp_growth": 2.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 1.8), ("article_count", "2026-04-22T10:15:00Z", 1.7),
                 ("article_count", "2026-04-20T09:00:00Z", 1.9), ("article_count", "2026-04-18T14:30:00Z", 1.6)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 8.0), ("violent_event_count", "2026-05-20T20:30:00Z", 8.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 5.0)],
        "ts_D": [("gdp_growth", "2024", 2.8), ("trade_volume_change", "2024", -12.5)],
        "linked_events": ["EVT-EGY-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 3.5}, {"label": "2026-04", "value": 1.8}, {"label": "2026-05", "value": 7.0}],
    },
    {
        "id": "SDN",
        "name": "Sudan",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "East Africa",
        "rationale": "Konflikt, humanitäre Krise, Bürgerkrieg seit 2023",
        "status": "S4",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D3", "B": "D4", "D": "D3"},
        "feature_A": {"A_news_volume": 12.0, "A_source_count": 2.0, "A_source_diversity_index": 0.35},
        "feature_B": {"B_event_count": 65.0, "B_violent_event_count": 48.0, "B_protest_event_count": 3.0,
                      "B_violent_event_share": 0.738, "B_disaster_alert_level": 1.0,
                      "B_event_type_distribution": {"conflict": 0.738, "violent": 0.738, "protest": 0.046}},
        "feature_D": {"D_trade_volume_change": -35.0, "D_gdp_growth": -7.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 3.2), ("article_count", "2026-04-22T10:15:00Z", 3.0),
                 ("article_count", "2026-04-20T09:00:00Z", 3.5), ("article_count", "2026-04-18T14:30:00Z", 2.9)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 48.0), ("violent_event_count", "2026-05-20T20:30:00Z", 48.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 3.0)],
        "ts_D": [("gdp_growth", "2024", -7.5), ("trade_volume_change", "2024", -35.0)],
        "linked_events": ["EVT-SDN-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 7.2}, {"label": "2026-04", "value": 3.2}, {"label": "2026-05", "value": 12.0}],
    },
    {
        "id": "MMR",
        "name": "Myanmar",
        "priority": "P2",
        "selection_type": "Extended Focus",
        "region": "Southeast Asia",
        "rationale": "Bürgerkrieg, Militärjunta, humanitäre Krise seit 2021",
        "status": "S4",
        "domains": ["A", "D"],  # A+D only
        "domain_states": {"A": "D3", "D": "D3"},
        "feature_A": {"A_news_volume": 10.5, "A_source_count": 2.0, "A_source_diversity_index": 0.3},
        "feature_D": {"D_trade_volume_change": -18.0, "D_gdp_growth": -2.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 2.8), ("article_count", "2026-04-22T10:15:00Z", 2.5),
                 ("article_count", "2026-04-20T09:00:00Z", 3.0), ("article_count", "2026-04-18T14:30:00Z", 2.6)],
        "ts_D": [("gdp_growth", "2024", -2.5), ("trade_volume_change", "2024", -18.0)],
        "linked_events": ["EVT-MMR-RUN-LIVE-20260520-2021"],
        "trends": [{"label": "2024", "value": 5.5}, {"label": "2026-04", "value": 2.8}, {"label": "2026-05", "value": 10.5}],
    },
    # P3 Control/Reference
    {
        "id": "CHE",
        "name": "Switzerland",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Western Europe",
        "rationale": "Stabiles Referenzland, hohe Pressefreiheit, neutraler Staat",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.5, "A_source_count": 3.0, "A_source_diversity_index": 0.9},
        "feature_B": {"B_event_count": 4.0, "B_violent_event_count": 0.0, "B_protest_event_count": 2.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.5}},
        "feature_D": {"D_trade_volume_change": 1.5, "D_gdp_growth": 1.2, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.6), ("article_count", "2026-04-22T10:15:00Z", 0.7),
                 ("article_count", "2026-04-20T09:00:00Z", 0.6), ("article_count", "2026-04-18T14:30:00Z", 0.5)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 2.0)],
        "ts_D": [("gdp_growth", "2024", 1.2), ("trade_volume_change", "2024", 1.5)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.5}, {"label": "2026-04", "value": 0.6}, {"label": "2026-05", "value": 2.5}],
    },
    {
        "id": "NLD",
        "name": "Netherlands",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Western Europe",
        "rationale": "Stabiles EU-Land, hohe Pressefreiheit, Referenzrahmen",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.8, "A_source_count": 3.0, "A_source_diversity_index": 0.88},
        "feature_B": {"B_event_count": 5.0, "B_violent_event_count": 0.0, "B_protest_event_count": 3.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.6}},
        "feature_D": {"D_trade_volume_change": 2.0, "D_gdp_growth": 1.8, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.7), ("article_count", "2026-04-22T10:15:00Z", 0.8),
                 ("article_count", "2026-04-20T09:00:00Z", 0.7), ("article_count", "2026-04-18T14:30:00Z", 0.6)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 3.0)],
        "ts_D": [("gdp_growth", "2024", 1.8), ("trade_volume_change", "2024", 2.0)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.6}, {"label": "2026-04", "value": 0.7}, {"label": "2026-05", "value": 2.8}],
    },
    {
        "id": "SWE",
        "name": "Sweden",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Nordic / NATO",
        "rationale": "Stabiles Referenzland, neues NATO-Mitglied, hohe Pressefreiheit",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.2, "A_source_count": 3.0, "A_source_diversity_index": 0.87},
        "feature_B": {"B_event_count": 4.0, "B_violent_event_count": 0.0, "B_protest_event_count": 2.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.5}},
        "feature_D": {"D_trade_volume_change": 1.8, "D_gdp_growth": 0.9, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.6), ("article_count", "2026-04-22T10:15:00Z", 0.5),
                 ("article_count", "2026-04-20T09:00:00Z", 0.6), ("article_count", "2026-04-18T14:30:00Z", 0.5)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 2.0)],
        "ts_D": [("gdp_growth", "2024", 0.9), ("trade_volume_change", "2024", 1.8)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.5}, {"label": "2026-04", "value": 0.6}, {"label": "2026-05", "value": 2.2}],
    },
    {
        "id": "NOR",
        "name": "Norway",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Nordic / NATO",
        "rationale": "Stabiles Referenzland, Energieexport, hohe Demokratiequalität",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.0, "A_source_count": 3.0, "A_source_diversity_index": 0.88},
        "feature_B": {"B_event_count": 3.0, "B_violent_event_count": 0.0, "B_protest_event_count": 1.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.333}},
        "feature_D": {"D_trade_volume_change": 3.5, "D_gdp_growth": 2.0, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.5), ("article_count", "2026-04-22T10:15:00Z", 0.6),
                 ("article_count", "2026-04-20T09:00:00Z", 0.5), ("article_count", "2026-04-18T14:30:00Z", 0.4)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 1.0)],
        "ts_D": [("gdp_growth", "2024", 2.0), ("trade_volume_change", "2024", 3.5)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.4}, {"label": "2026-04", "value": 0.5}, {"label": "2026-05", "value": 2.0}],
    },
    {
        "id": "CAN",
        "name": "Canada",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "North America",
        "rationale": "Stabiles demokratisches Referenzland, G7, Pressfreiheit",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 3.0, "A_source_count": 3.0, "A_source_diversity_index": 0.9},
        "feature_B": {"B_event_count": 5.0, "B_violent_event_count": 0.0, "B_protest_event_count": 3.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.6}},
        "feature_D": {"D_trade_volume_change": 1.8, "D_gdp_growth": 1.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.8), ("article_count", "2026-04-22T10:15:00Z", 0.7),
                 ("article_count", "2026-04-20T09:00:00Z", 0.8), ("article_count", "2026-04-18T14:30:00Z", 0.7)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 3.0)],
        "ts_D": [("gdp_growth", "2024", 1.5), ("trade_volume_change", "2024", 1.8)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.6}, {"label": "2026-04", "value": 0.8}, {"label": "2026-05", "value": 3.0}],
    },
    {
        "id": "AUS",
        "name": "Australia",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Pacific / Oceania",
        "rationale": "Stabiles Referenzland, Indo-Pazifik-Relevanz, Pressfreiheit",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.8, "A_source_count": 3.0, "A_source_diversity_index": 0.88},
        "feature_B": {"B_event_count": 4.0, "B_violent_event_count": 0.0, "B_protest_event_count": 2.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.5}},
        "feature_D": {"D_trade_volume_change": 2.2, "D_gdp_growth": 2.0, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.7), ("article_count", "2026-04-22T10:15:00Z", 0.8),
                 ("article_count", "2026-04-20T09:00:00Z", 0.7), ("article_count", "2026-04-18T14:30:00Z", 0.6)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 2.0)],
        "ts_D": [("gdp_growth", "2024", 2.0), ("trade_volume_change", "2024", 2.2)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.6}, {"label": "2026-04", "value": 0.7}, {"label": "2026-05", "value": 2.8}],
    },
    {
        "id": "NZL",
        "name": "New Zealand",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Pacific / Oceania",
        "rationale": "Stabiles Referenzland, Five Eyes, hohe Demokratiequalität",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 1.8, "A_source_count": 2.0, "A_source_diversity_index": 0.85},
        "feature_B": {"B_event_count": 3.0, "B_violent_event_count": 0.0, "B_protest_event_count": 1.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.333}},
        "feature_D": {"D_trade_volume_change": 1.5, "D_gdp_growth": 1.2, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.5), ("article_count", "2026-04-22T10:15:00Z", 0.4),
                 ("article_count", "2026-04-20T09:00:00Z", 0.5), ("article_count", "2026-04-18T14:30:00Z", 0.4)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 1.0)],
        "ts_D": [("gdp_growth", "2024", 1.2), ("trade_volume_change", "2024", 1.5)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.4}, {"label": "2026-04", "value": 0.5}, {"label": "2026-05", "value": 1.8}],
    },
    {
        "id": "PRT",
        "name": "Portugal",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Southern Europe",
        "rationale": "Stabiles EU- und NATO-Land, Referenzrahmen",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.0, "A_source_count": 2.0, "A_source_diversity_index": 0.8},
        "feature_B": {"B_event_count": 4.0, "B_violent_event_count": 0.0, "B_protest_event_count": 2.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.5}},
        "feature_D": {"D_trade_volume_change": 2.5, "D_gdp_growth": 2.2, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.5), ("article_count", "2026-04-22T10:15:00Z", 0.5),
                 ("article_count", "2026-04-20T09:00:00Z", 0.6), ("article_count", "2026-04-18T14:30:00Z", 0.4)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 2.0)],
        "ts_D": [("gdp_growth", "2024", 2.2), ("trade_volume_change", "2024", 2.5)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.4}, {"label": "2026-04", "value": 0.5}, {"label": "2026-05", "value": 2.0}],
    },
    {
        "id": "IRL",
        "name": "Ireland",
        "priority": "P3",
        "selection_type": "Control/Reference",
        "region": "Western Europe",
        "rationale": "Stabiles EU-Land, hohe Lebensqualität, Pressfreiheit, Referenzrahmen",
        "status": "S0",
        "domains": ["A", "B", "D"],
        "domain_states": {"A": "D0", "B": "D0", "D": "D0"},
        "feature_A": {"A_news_volume": 2.2, "A_source_count": 2.0, "A_source_diversity_index": 0.82},
        "feature_B": {"B_event_count": 4.0, "B_violent_event_count": 0.0, "B_protest_event_count": 2.0,
                      "B_violent_event_share": 0.0, "B_disaster_alert_level": 0.0,
                      "B_event_type_distribution": {"conflict": 0.0, "violent": 0.0, "protest": 0.5}},
        "feature_D": {"D_trade_volume_change": 3.0, "D_gdp_growth": 3.5, "D_macro_data_freshness": 8760},
        "ts_A": [("article_count", "2026-04-23T11:45:00Z", 0.6), ("article_count", "2026-04-22T10:15:00Z", 0.5),
                 ("article_count", "2026-04-20T09:00:00Z", 0.6), ("article_count", "2026-04-18T14:30:00Z", 0.5)],
        "ts_B": [("conflict_event_count", "2026-05-20T20:30:00Z", 0.0), ("violent_event_count", "2026-05-20T20:30:00Z", 0.0),
                 ("protest_event_count", "2026-05-20T20:30:00Z", 2.0)],
        "ts_D": [("gdp_growth", "2024", 3.5), ("trade_volume_change", "2024", 3.0)],
        "linked_events": [],
        "trends": [{"label": "2024", "value": 0.5}, {"label": "2026-04", "value": 0.6}, {"label": "2026-05", "value": 2.2}],
    },
]

A_DRIVERS = ["A_news_volume", "A_source_count", "A_source_diversity_index"]
B_DRIVERS = ["B_disaster_alert_level", "B_event_count", "B_event_type_distribution",
             "B_protest_event_count", "B_violent_event_count", "B_violent_event_share"]
D_DRIVERS = ["D_gdp_growth", "D_macro_data_freshness", "D_trade_volume_change"]


def build_drivers(domains):
    d = []
    if "A" in domains:
        d += A_DRIVERS
    if "B" in domains:
        d += B_DRIVERS
    if "D" in domains:
        d += D_DRIVERS
    return sorted(d)


def build_country_profile(c):
    domains = c["domains"]
    profile = {
        "annotations": [],
        "confidence": 1.0,
        "configured_domains": domains,
        "counter_indicators": [],
        "country_context": {
            "country_name": c["name"],
            "priority": c["priority"],
            "rationale": c["rationale"],
            "region": c["region"],
            "selection_type": c["selection_type"],
        },
        "country_id": c["id"],
        "coverage": 1.0,
        "domain_gap_summary": {
            "expected_domains": domains,
            "missing_domains": [],
            "observed_domains": domains,
        },
        "domain_states": c["domain_states"],
        "drivers": build_drivers(domains),
        "explanation_summary": None,
        "linked_events": c.get("linked_events", []),
        "multi_domain_status": c["status"],
        "source_depth": {
            "source_count": 3,
            "source_ids": ["SRC-GDELT-DOC", "SRC-GDELT-EVENTS", "WB-INDICATORS"],
        },
        "trends": {"yearly": c.get("trends", [])},
        "uncertainty": [],
    }
    # Adjust source_depth if fewer sources
    if "B" not in domains:
        profile["source_depth"]["source_count"] = 2
        profile["source_depth"]["source_ids"] = ["SRC-GDELT-DOC", "WB-INDICATORS"]
    return profile


def build_domain_A(c):
    fv = [{"coverage": 1.0, "feature_id": k, "value": v}
          for k, v in c["feature_A"].items()]
    anomaly = c["domain_states"]["A"]
    ts = [{"signal_key": sig, "timestamp": ts, "value": val}
          for sig, ts, val in c["ts_A"]]
    return {
        "annotations": [],
        "anomaly_state": anomaly,
        "baseline_comparison": {"current_window": c.get("feature_A", {}).get("A_news_volume", 1.0), "delta_to_baseline": 0.5},
        "country_id": c["id"],
        "domain": "A",
        "feature_values": fv,
        "source_context": [{"confidence": None, "freshness_hours": None, "history_horizon": "n/a",
                             "source_id": "SRC-GDELT-DOC", "status": "success"}],
        "time_series": ts,
        "uncertainty": ["freshness beyond threshold"],
    }


def build_domain_B(c):
    fv = []
    for k, v in c["feature_B"].items():
        fv.append({"coverage": 1.0, "feature_id": k, "value": v})
    anomaly = c["domain_states"]["B"]
    ts = [{"signal_key": sig, "timestamp": ts, "value": val}
          for sig, ts, val in c["ts_B"]]
    return {
        "annotations": [],
        "anomaly_state": anomaly,
        "baseline_comparison": {"current_window": c["feature_B"]["B_event_count"], "delta_to_baseline": 0.3},
        "country_id": c["id"],
        "domain": "B",
        "feature_values": fv,
        "source_context": [{"confidence": None, "freshness_hours": None, "history_horizon": "n/a",
                             "source_id": "SRC-GDELT-EVENTS", "status": "success"}],
        "time_series": ts,
        "uncertainty": [],
    }


def build_domain_D(c):
    fv = [{"coverage": 1.0, "feature_id": k, "value": v}
          for k, v in c["feature_D"].items()]
    anomaly = c["domain_states"]["D"]
    ts = [{"signal_key": sig, "timestamp": ts, "value": val}
          for sig, ts, val in c["ts_D"]]
    return {
        "annotations": [],
        "anomaly_state": anomaly,
        "baseline_comparison": {"current_window": c["feature_D"]["D_gdp_growth"], "delta_to_baseline": 0.1},
        "country_id": c["id"],
        "domain": "D",
        "feature_values": fv,
        "source_context": [{"confidence": None, "freshness_hours": None, "history_horizon": "n/a",
                             "source_id": "WB-INDICATORS", "status": "success"}],
        "time_series": ts,
        "uncertainty": [],
    }


def build_export_json(c):
    domains = c["domains"]
    return {
        "capability": "analysis",
        "contains_personal_data": False,
        "counter_indicators": [],
        "country_id": c["id"],
        "coverage": 1.0,
        "domain_states": c["domain_states"],
        "drivers": build_drivers(domains),
        "linked_events": c.get("linked_events", []),
        "multi_domain_status": c["status"],
        "uncertainty": [],
    }


def build_export_md(c):
    domains = c["domains"]
    drivers_str = ", ".join(build_drivers(domains))
    events_str = ", ".join(c.get("linked_events", [])) or "-"
    return (
        f"# Country Report: {c['id']}\n"
        f"Multi-domain status: {c['status']}\n"
        f"Coverage: 1.0\n"
        f"Drivers: {drivers_str}\n"
        f"Counter indicators: -\n"
        f"Uncertainty: -\n"
        f"Linked events: {events_str}"
    )


def write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"  Written: {path}")


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  Written: {path}")


created = 0

for c in COUNTRIES:
    cid = c["id"]
    if cid in EXISTING:
        print(f"  Skipping {cid} (already exists)")
        continue
    print(f"\n--- {cid} ({c['priority']}) ---")

    # Country profile
    profile = build_country_profile(c)
    write_json(str(PROFILES_DIR / f"{cid}.json"), profile)

    # Domain details
    domains = c["domains"]
    if "A" in domains:
        write_json(str(DOMAIN_DIR / f"{cid}__A.json"), build_domain_A(c))
    if "B" in domains:
        write_json(str(DOMAIN_DIR / f"{cid}__B.json"), build_domain_B(c))
    if "D" in domains:
        write_json(str(DOMAIN_DIR / f"{cid}__D.json"), build_domain_D(c))

    # Export files
    write_json(str(EXPORTS_DIR / f"REP-COUNTRY-{cid}.json"), build_export_json(c))
    write_text(str(EXPORTS_DIR / f"REP-COUNTRY-{cid}.md"), build_export_md(c))

    created += 1

print(f"\n✓ Created files for {created} countries.")
