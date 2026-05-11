from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, mean_signal


class DomainDFeatureService(FeatureService):
    domain = "D"

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        feature_specs = {
            "D_trade_volume_change": "trade_volume_change",
            "D_energy_price_stress": "energy_price_stress",
            "D_gdp_growth": "gdp_growth",
            "D_food_price_proxy": "food_price_proxy",
        }

        features: list[FeatureValue] = []
        for feature_id, signal_key in feature_specs.items():
            value = mean_signal(domain_records, signal_key)
            if value is not None:
                features.append(build_feature_value(feature_id, self.domain, value, domain_records))

        freshness_hours = max(
            float(record.quality_context.get("freshness_hours", 0) or 0) for record in domain_records
        )
        features.append(build_feature_value("D_macro_data_freshness", self.domain, int(freshness_hours), domain_records))
        return features
