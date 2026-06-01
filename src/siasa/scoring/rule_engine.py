"""SIASA rule-based assessment engine.

Evaluates configurable rules against domain/multi-domain scoring results
and produces annotation drafts when conditions match.

Key APIs:
- ``load_assessment_rules(path)`` — load YAML rule catalog
- ``evaluate_rules(rules, context)`` — evaluate rules against scoring context
- ``RuleEvaluationResult`` — matched rule + generated annotation

Requirement trace: AP-F20, StR-266..281 (Regelbasierte Bewertung)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class AssessmentRule:
    """A single assessment rule from the YAML catalog."""
    rule_id: str
    name: str
    description: str
    scope: str  # "domain" or "multi_domain"
    condition_field: str
    condition_operator: str  # "eq", "gt", "lt", "gte", "lte", "in", "not_eq"
    condition_value: Any
    output_severity: str
    output_annotation_type: str
    output_text_template: str
    output_tags: list[str]
    enabled: bool = True


@dataclass(frozen=True)
class RuleEvaluationResult:
    """Result of evaluating a single rule against a context."""
    rule_id: str
    rule_name: str
    matched: bool
    country_id: str
    domain: str
    severity: str
    annotation_text: str
    tags: list[str]


@dataclass(frozen=True)
class AssessmentContext:
    """Context for rule evaluation — one entry per country/domain."""
    country_id: str
    domain: str
    domain_status: str
    anomaly_score: float
    multi_domain_status: str = ""
    data_sufficiency: str = "unknown"


def load_assessment_rules(path: str | Path) -> list[AssessmentRule]:
    """Load assessment rules from a YAML file."""
    content = Path(path).read_text(encoding="utf-8")
    data = yaml.safe_load(content) or {}
    raw_rules = data.get("rules", [])
    if not isinstance(raw_rules, list):
        raise ValueError("assessment_rules.yaml: 'rules' must be a list")

    rules: list[AssessmentRule] = []
    seen_ids: set[str] = set()
    for entry in raw_rules:
        if not isinstance(entry, dict):
            continue
        rule_id = str(entry.get("rule_id", "")).strip()
        if not rule_id:
            raise ValueError("assessment rule requires a rule_id")
        if rule_id in seen_ids:
            raise ValueError(f"duplicate rule_id: {rule_id}")
        seen_ids.add(rule_id)

        condition = entry.get("condition", {})
        output = entry.get("output", {})

        rules.append(AssessmentRule(
            rule_id=rule_id,
            name=str(entry.get("name", "")),
            description=str(entry.get("description", "")),
            scope=str(entry.get("scope", "domain")),
            condition_field=str(condition.get("field", "")),
            condition_operator=str(condition.get("operator", "eq")),
            condition_value=condition.get("value"),
            output_severity=str(output.get("severity", "informational")),
            output_annotation_type=str(output.get("annotation_type", "automatic_assessment")),
            output_text_template=str(output.get("text_template", "")),
            output_tags=list(output.get("tags", [])),
            enabled=bool(entry.get("enabled", True)),
        ))

    return rules


def evaluate_rules(
    rules: list[AssessmentRule],
    contexts: list[AssessmentContext],
) -> list[RuleEvaluationResult]:
    """Evaluate all enabled rules against all contexts.

    Returns only matched results (where condition is true).
    """
    results: list[RuleEvaluationResult] = []

    for context in contexts:
        for rule in rules:
            if not rule.enabled:
                continue

            # Scope filtering
            if rule.scope == "multi_domain" and not context.multi_domain_status:
                continue

            # Get the field value from context
            actual_value = _get_context_field(context, rule.condition_field)
            if actual_value is None:
                continue

            # Evaluate condition
            matched = _evaluate_condition(actual_value, rule.condition_operator, rule.condition_value)
            if not matched:
                continue

            # Generate annotation text from template
            annotation_text = _render_template(rule.output_text_template, context)

            results.append(RuleEvaluationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                matched=True,
                country_id=context.country_id,
                domain=context.domain,
                severity=rule.output_severity,
                annotation_text=annotation_text,
                tags=list(rule.output_tags),
            ))

    return results


def _get_context_field(context: AssessmentContext, field: str) -> Any:
    """Extract a field value from an AssessmentContext."""
    field_map = {
        "domain_status": context.domain_status,
        "anomaly_score": context.anomaly_score,
        "multi_domain_status": context.multi_domain_status,
        "data_sufficiency": context.data_sufficiency,
        "domain": context.domain,
        "country_id": context.country_id,
    }
    return field_map.get(field)


def _evaluate_condition(actual: Any, operator: str, expected: Any) -> bool:
    """Evaluate a condition: actual <operator> expected."""
    if operator == "eq":
        return actual == expected
    elif operator == "not_eq":
        return actual != expected
    elif operator == "gt":
        return float(actual) > float(expected)
    elif operator == "lt":
        return float(actual) < float(expected)
    elif operator == "gte":
        return float(actual) >= float(expected)
    elif operator == "lte":
        return float(actual) <= float(expected)
    elif operator == "in":
        if isinstance(expected, list):
            return actual in expected
        return False
    else:
        return False


def _render_template(template: str, context: AssessmentContext) -> str:
    """Render a text template with context values."""
    try:
        return template.format(
            country_id=context.country_id,
            domain=context.domain,
            domain_status=context.domain_status,
            anomaly_score=context.anomaly_score,
            multi_domain_status=context.multi_domain_status,
            data_sufficiency=context.data_sufficiency,
        )
    except (KeyError, IndexError, ValueError):
        return template
