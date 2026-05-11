from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, sum_signal


class DomainBFeatureService(FeatureService):
    domain = "B"

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        conflict_count = sum_signal(domain_records, "conflict_event_count")
        protest_count = sum_signal(domain_records, "protest_event_count")
        violent_count = sum_signal(domain_records, "violent_event_count")
        disaster_alert_level = max(
            (record.value for record in domain_records if record.signal_key == "disaster_alert_level"),
            default=0.0,
        )
        event_count = conflict_count + protest_count + violent_count
        violent_share = violent_count / event_count if event_count else 0.0
        distribution = {
            key: value / event_count
            for key, value in {
                "conflict": conflict_count,
                "protest": protest_count,
                "violent": violent_count,
            }.items()
            if value > 0 and event_count
        }

        features = [
            build_feature_value("B_event_count", self.domain, event_count, domain_records),
            build_feature_value("B_violent_event_count", self.domain, violent_count, domain_records),
            build_feature_value("B_protest_event_count", self.domain, protest_count, domain_records),
            build_feature_value("B_violent_event_share", self.domain, violent_share, domain_records),
            build_feature_value("B_disaster_alert_level", self.domain, disaster_alert_level, domain_records),
        ]
        if distribution:
            features.append(build_feature_value("B_event_type_distribution", self.domain, distribution, domain_records))
        return features
