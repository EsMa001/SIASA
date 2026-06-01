"""Tests for the rule-based assessment engine."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from siasa.scoring.rule_engine import (
    AssessmentContext,
    AssessmentRule,
    RuleEvaluationResult,
    evaluate_rules,
    load_assessment_rules,
    _evaluate_condition,
)


_SAMPLE_RULES_YAML = """\
schema_version: "1.0"
rules:
  - rule_id: "RULE-D-001"
    name: "Critical domain status"
    scope: "domain"
    condition:
      field: "domain_status"
      operator: "eq"
      value: "D4"
    output:
      severity: "critical"
      annotation_type: "automatic_assessment"
      text_template: "Domain {domain} reached D4 for {country_id}"
      tags: ["rule_engine", "D4"]
    enabled: true

  - rule_id: "RULE-A-001"
    name: "High anomaly score"
    scope: "domain"
    condition:
      field: "anomaly_score"
      operator: "gt"
      value: 0.8
    output:
      severity: "high"
      annotation_type: "automatic_assessment"
      text_template: "Domain {domain} anomaly {anomaly_score:.2f} > 0.8 for {country_id}"
      tags: ["rule_engine", "high_anomaly"]
    enabled: true

  - rule_id: "RULE-M-001"
    name: "Critical multi-domain"
    scope: "multi_domain"
    condition:
      field: "multi_domain_status"
      operator: "in"
      value: ["S5", "S6"]
    output:
      severity: "critical"
      annotation_type: "automatic_assessment"
      text_template: "Country {country_id} reached {multi_domain_status}"
      tags: ["rule_engine", "critical_multi"]
    enabled: true

  - rule_id: "RULE-DISABLED"
    name: "Disabled rule"
    scope: "domain"
    condition:
      field: "domain_status"
      operator: "eq"
      value: "D1"
    output:
      severity: "low"
      annotation_type: "automatic_assessment"
      text_template: "Should not fire"
      tags: ["disabled"]
    enabled: false
"""


class TestLoadAssessmentRules:
    """Tests for YAML rule loading."""

    def test_load_sample_rules(self):
        path = Path(tempfile.mktemp(suffix=".yaml"))
        path.write_text(_SAMPLE_RULES_YAML, encoding="utf-8")

        rules = load_assessment_rules(path)

        assert len(rules) == 4
        assert rules[0].rule_id == "RULE-D-001"
        assert rules[0].scope == "domain"
        assert rules[0].condition_field == "domain_status"
        assert rules[0].condition_operator == "eq"
        assert rules[0].condition_value == "D4"
        assert rules[0].output_severity == "critical"
        assert rules[0].enabled is True

    def test_load_real_config(self):
        """Smoke test: load the governed assessment_rules.yaml."""
        path = Path("vmodel/project/assessment_rules.yaml")
        if not path.exists():
            pytest.skip("governed config not available")

        rules = load_assessment_rules(path)

        assert len(rules) >= 5
        rule_ids = {r.rule_id for r in rules}
        assert "RULE-D-001" in rule_ids

    def test_duplicate_rule_id_rejected(self):
        yaml_content = """\
rules:
  - rule_id: "DUPE"
    name: "A"
    scope: "domain"
    condition: {field: "domain_status", operator: "eq", value: "D4"}
    output: {severity: "high", text_template: "test", tags: []}
  - rule_id: "DUPE"
    name: "B"
    scope: "domain"
    condition: {field: "domain_status", operator: "eq", value: "D3"}
    output: {severity: "medium", text_template: "test", tags: []}
"""
        path = Path(tempfile.mktemp(suffix=".yaml"))
        path.write_text(yaml_content, encoding="utf-8")

        with pytest.raises(ValueError, match="duplicate"):
            load_assessment_rules(path)


class TestEvaluateRules:
    """Tests for rule evaluation against contexts."""

    def _load_sample_rules(self) -> list[AssessmentRule]:
        path = Path(tempfile.mktemp(suffix=".yaml"))
        path.write_text(_SAMPLE_RULES_YAML, encoding="utf-8")
        return load_assessment_rules(path)

    def test_d4_triggers_critical_rule(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="UKR", domain="A",
                domain_status="D4", anomaly_score=1.2,
                multi_domain_status="S4",
            ),
        ]

        results = evaluate_rules(rules, contexts)

        d4_results = [r for r in results if r.rule_id == "RULE-D-001"]
        assert len(d4_results) == 1
        assert d4_results[0].severity == "critical"
        assert d4_results[0].country_id == "UKR"
        assert "D4" in d4_results[0].annotation_text

    def test_high_anomaly_triggers(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="UKR", domain="B",
                domain_status="D3", anomaly_score=0.9,
            ),
        ]

        results = evaluate_rules(rules, contexts)

        anomaly_results = [r for r in results if r.rule_id == "RULE-A-001"]
        assert len(anomaly_results) == 1
        assert "0.90" in anomaly_results[0].annotation_text

    def test_multi_domain_rule_triggers(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="UKR", domain="multi",
                domain_status="", anomaly_score=0.0,
                multi_domain_status="S5",
            ),
        ]

        results = evaluate_rules(rules, contexts)

        multi_results = [r for r in results if r.rule_id == "RULE-M-001"]
        assert len(multi_results) == 1
        assert "S5" in multi_results[0].annotation_text

    def test_disabled_rule_does_not_fire(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="POL", domain="A",
                domain_status="D1", anomaly_score=0.1,
            ),
        ]

        results = evaluate_rules(rules, contexts)

        disabled_results = [r for r in results if r.rule_id == "RULE-DISABLED"]
        assert len(disabled_results) == 0

    def test_no_match_returns_empty(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="POL", domain="A",
                domain_status="D1", anomaly_score=0.1,
            ),
        ]

        results = evaluate_rules(rules, contexts)

        # D1 with low anomaly should not trigger any enabled rule
        assert len(results) == 0

    def test_multiple_rules_fire_for_same_context(self):
        """D4 with high anomaly should trigger both D4 rule and anomaly rule."""
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(
                country_id="UKR", domain="A",
                domain_status="D4", anomaly_score=1.5,
            ),
        ]

        results = evaluate_rules(rules, contexts)

        rule_ids = {r.rule_id for r in results}
        assert "RULE-D-001" in rule_ids
        assert "RULE-A-001" in rule_ids

    def test_multi_country_evaluation(self):
        rules = self._load_sample_rules()
        contexts = [
            AssessmentContext(country_id="UKR", domain="A", domain_status="D4", anomaly_score=1.2),
            AssessmentContext(country_id="POL", domain="A", domain_status="D1", anomaly_score=0.1),
            AssessmentContext(country_id="ISR", domain="B", domain_status="D3", anomaly_score=0.9),
        ]

        results = evaluate_rules(rules, contexts)

        ukr_results = [r for r in results if r.country_id == "UKR"]
        pol_results = [r for r in results if r.country_id == "POL"]
        isr_results = [r for r in results if r.country_id == "ISR"]

        assert len(ukr_results) >= 2  # D4 + high anomaly
        assert len(pol_results) == 0  # D1, low anomaly
        assert len(isr_results) >= 1  # high anomaly


class TestEvaluateCondition:
    """Tests for individual condition operators."""

    def test_eq(self):
        assert _evaluate_condition("D4", "eq", "D4") is True
        assert _evaluate_condition("D3", "eq", "D4") is False

    def test_not_eq(self):
        assert _evaluate_condition("D3", "not_eq", "D4") is True
        assert _evaluate_condition("D4", "not_eq", "D4") is False

    def test_gt(self):
        assert _evaluate_condition(0.9, "gt", 0.8) is True
        assert _evaluate_condition(0.8, "gt", 0.8) is False

    def test_lt(self):
        assert _evaluate_condition(0.5, "lt", 0.8) is True
        assert _evaluate_condition(0.9, "lt", 0.8) is False

    def test_gte(self):
        assert _evaluate_condition(0.8, "gte", 0.8) is True
        assert _evaluate_condition(0.7, "gte", 0.8) is False

    def test_lte(self):
        assert _evaluate_condition(0.8, "lte", 0.8) is True
        assert _evaluate_condition(0.9, "lte", 0.8) is False

    def test_in_operator(self):
        assert _evaluate_condition("S5", "in", ["S5", "S6"]) is True
        assert _evaluate_condition("S3", "in", ["S5", "S6"]) is False

    def test_unknown_operator(self):
        assert _evaluate_condition("x", "unknown_op", "y") is False
