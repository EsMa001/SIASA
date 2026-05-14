from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, mean_signal, sum_signal, topic_distribution


class DomainAFeatureService(FeatureService):
    domain = "A"

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        features: list[FeatureValue] = []
        for country_id in sorted({record.country_id for record in domain_records}):
            country_records = [record for record in domain_records if record.country_id == country_id]
            news_volume = sum_signal(country_records, "article_count")
            source_count = float(len({record.provenance_source_id for record in country_records}))
            source_diversity = source_count / news_volume if news_volume else 0.0
            tone_mean = mean_signal(country_records, "tone")
            topics = topic_distribution(country_records)

            features.extend(
                [
                    build_feature_value("A_news_volume", self.domain, news_volume, country_records),
                    build_feature_value("A_source_count", self.domain, source_count, country_records),
                    build_feature_value("A_source_diversity_index", self.domain, source_diversity, country_records),
                ]
            )
            if tone_mean is not None:
                features.append(build_feature_value("A_tone_mean", self.domain, tone_mean, country_records))
            if topics:
                features.append(build_feature_value("A_topic_distribution", self.domain, topics, country_records))
        return features
