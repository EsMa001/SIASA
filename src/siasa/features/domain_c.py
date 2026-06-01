from __future__ import annotations

from siasa.data.normalized_models import NormalizedRecord

from .base import FeatureService, FeatureValue, build_feature_value, mean_signal, sum_signal


class DomainCFeatureService(FeatureService):
    """Domain C — physical activity, disaster events, and social disruption indicators.

    Requirement trace: SwR-052 (Domain C feature extraction)
    """

    domain = "C"

    def compute(self, records: list[NormalizedRecord]) -> list[FeatureValue]:
        domain_records = [record for record in records if record.domain == self.domain]
        if not domain_records:
            return []

        features: list[FeatureValue] = []
        for country_id in sorted({record.country_id for record in domain_records}):
            country_records = [record for record in domain_records if record.country_id == country_id]

            # C_event_count: total number of physical/disaster/displacement signals
            event_count = sum_signal(country_records, "disaster_alert_level")
            if not event_count:
                # Fallback for displacement-oriented Domain C sources (e.g. UNHCR/ReliefWeb)
                event_count = (
                    sum_signal(country_records, "displacement_total")
                    or sum_signal(country_records, "humanitarian_report_count")
                    or float(len(country_records))
                )
            alert_records = [r for r in country_records if r.signal_key == "disaster_alert_level"]
            features.append(
                build_feature_value(
                    "C_event_count",
                    self.domain,
                    event_count,
                    country_records,
                    freshness_records=alert_records or None,
                )
            )

            # C_event_severity_mean: average severity/alert level
            severity_mean = mean_signal(country_records, "disaster_alert_level")
            if severity_mean is not None:
                features.append(
                    build_feature_value(
                        "C_event_severity_mean",
                        self.domain,
                        severity_mean,
                        country_records,
                        freshness_records=alert_records or None,
                    )
                )

            # C_max_alert_level: highest alert level observed (worst case)
            alert_values = [
                record.value for record in country_records if record.signal_key == "disaster_alert_level"
            ]
            if alert_values:
                features.append(
                    build_feature_value(
                        "C_max_alert_level",
                        self.domain,
                        max(alert_values),
                        country_records,
                        freshness_records=alert_records or None,
                    )
                )

            # C_affected_source_count: number of distinct provenance sources reporting events
            source_count = float(len({record.provenance_source_id for record in country_records}))
            features.append(
                build_feature_value("C_affected_source_count", self.domain, source_count, country_records)
            )

            # C_displacement_total: latest forced-displacement signal when available
            displacement_total = sum_signal(country_records, "displacement_total")
            if displacement_total is not None and displacement_total > 0:
                displacement_records = [r for r in country_records if r.signal_key == "displacement_total"]
                features.append(
                    build_feature_value(
                        "C_displacement_total",
                        self.domain,
                        displacement_total,
                        country_records,
                        freshness_records=displacement_records or None,
                    )
                )

            # C_data_freshness: worst freshness across domain C records for this country
            freshness_hours = max(
                float(record.quality_context.get("freshness_hours", 0) or 0) for record in country_records
            )
            features.append(
                build_feature_value("C_data_freshness", self.domain, int(freshness_hours), country_records)
            )
        return features
