from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, mean_signal, sum_signal, topic_distribution


class DomainEFeatureService(FeatureService):
    """Domain E — cyber, tech disruption, and information operations indicators.

    Uses GDELT Doc/Events data filtered to cyber/tech themes via signal_key conventions.
    Requirement trace: SwR-053 (Domain E feature extraction)
    """

    domain = "E"

    # Signal keys expected from GDELT-based normalization for domain E
    _SIGNAL_SPECS = {
        "E_cyber_mention_volume": "cyber_mention_count",
        "E_info_ops_tone": "info_ops_tone",
        "E_tech_disruption_signals": "tech_disruption_count",
    }

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        features: list[FeatureValue] = []
        for country_id in sorted({record.country_id for record in domain_records}):
            country_records = [record for record in domain_records if record.country_id == country_id]

            for feature_id, signal_key in self._SIGNAL_SPECS.items():
                signal_records = [r for r in country_records if r.signal_key == signal_key]
                if signal_key == "cyber_mention_count" or signal_key == "tech_disruption_count":
                    value = sum_signal(country_records, signal_key)
                else:
                    value = mean_signal(country_records, signal_key)

                # Live runtime fallback mappings:
                # - GDELT Doc (Domain E adapter) emits article_count/tone
                # - CISA KEV emits cyber_kev_* signals
                if (value is None or value == 0) and feature_id == "E_cyber_mention_volume":
                    signal_records = [r for r in country_records if r.signal_key in {"article_count", "cyber_kev_total"}]
                    value = (
                        sum_signal(country_records, "cyber_mention_count")
                        or sum_signal(country_records, "article_count")
                        or sum_signal(country_records, "cyber_kev_total")
                    )
                elif value is None and feature_id == "E_info_ops_tone":
                    signal_records = [r for r in country_records if r.signal_key == "tone"]
                    value = mean_signal(country_records, "tone")
                elif (value is None or value == 0) and feature_id == "E_tech_disruption_signals":
                    signal_records = [r for r in country_records if r.signal_key in {"tech_disruption_count", "cyber_kev_overdue_count", "cyber_kev_recent_count"}]
                    value = (
                        sum_signal(country_records, "tech_disruption_count")
                        or sum_signal(country_records, "cyber_kev_overdue_count")
                        or sum_signal(country_records, "cyber_kev_recent_count")
                    )

                if value is not None:
                    features.append(
                        build_feature_value(
                            feature_id,
                            self.domain,
                            value,
                            country_records,
                            freshness_records=signal_records or None,
                        )
                    )

            # E_source_diversity_cyber: distinct sources reporting domain E data
            source_ids = {record.provenance_source_id for record in country_records}
            total_records = float(len(country_records))
            source_diversity = float(len(source_ids)) / total_records if total_records else 0.0
            features.append(
                build_feature_value("E_source_diversity_cyber", self.domain, source_diversity, country_records)
            )

            # E_topic_distribution: topic distribution across domain E records
            topics = topic_distribution(country_records)
            if topics:
                features.append(
                    build_feature_value("E_topic_distribution", self.domain, topics, country_records)
                )

            # E_data_freshness: worst freshness across domain E records
            freshness_hours = max(
                float(record.quality_context.get("freshness_hours", 0) or 0) for record in country_records
            )
            features.append(
                build_feature_value("E_data_freshness", self.domain, int(freshness_hours), country_records)
            )
        return features
