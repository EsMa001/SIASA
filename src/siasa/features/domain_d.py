from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, mean_signal


class DomainDFeatureService(FeatureService):
    domain = "D"

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        features: list[FeatureValue] = []
        feature_specs = {
            "D_trade_volume_change": "trade_volume_change",
            "D_energy_price_stress": "energy_price_stress",
            "D_gdp_growth": "gdp_growth",
            "D_food_price_proxy": "food_price_proxy",
        }

        for country_id in sorted({record.country_id for record in domain_records}):
            country_records = [record for record in domain_records if record.country_id == country_id]
            for feature_id, signal_key in feature_specs.items():
                signal_records = [record for record in country_records if record.signal_key == signal_key]
                value = mean_signal(country_records, signal_key)
                if value is not None:
                    features.append(
                        build_feature_value(
                            feature_id,
                            self.domain,
                            value,
                            country_records,
                            freshness_records=signal_records,
                        )
                    )

            freshness_hours = max(
                float(record.quality_context.get("freshness_hours", 0) or 0) for record in country_records
            )
            features.append(
                build_feature_value("D_macro_data_freshness", self.domain, int(freshness_hours), country_records)
            )
        return features
