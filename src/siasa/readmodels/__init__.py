"""Query-side read models for SIASA."""

from .approval_lifecycle import (
    ApprovalLifecycleRecord,
    build_default_approval_lifecycle_record,
    build_approval_lifecycle_view_model,
    derive_lifecycle_status,
    load_approval_lifecycle_record,
    save_approval_lifecycle_record,
    transition_lifecycle_record,
    LifecycleTransitionError,
    ALLOWED_TRANSITIONS,
)
from .annotations import build_annotations_view_model
from .country_profile import build_country_profile_read_model
from .domain_detail import build_domain_detail_read_model
from .readiness import build_readiness_view_model
from .release_demo_package import build_release_demo_package_view_model, render_release_demo_package_body
from .release_evidence import (
    build_release_failure_drill_report,
    build_release_readiness_index,
    build_repo_release_gate_assessment,
    render_release_evidence_markdown,
)
from .release_gate import build_release_gate_view_model
from .source_coverage import build_source_coverage_read_model
from .stakeholder_functional_closure import build_stakeholder_functional_closure_report
from .stakeholder_e2e_flow_coverage import (
    build_stakeholder_e2e_flow_coverage_report,
    render_stakeholder_e2e_flow_coverage_markdown,
)
from .stakeholder_e2e_ui_smoke import build_stakeholder_e2e_ui_smoke_report
from .stakeholder_requirement_quality import (
    build_stakeholder_requirement_quality_report,
    render_stakeholder_requirement_quality_markdown,
)
from .stakeholder_system_traceability import (
    build_stakeholder_system_traceability_report,
    render_stakeholder_system_traceability_markdown,
)
from .stakeholder_verification_coverage import (
    build_stakeholder_verification_coverage_report,
    render_stakeholder_verification_coverage_markdown,
)
from .system_status import build_system_status_read_model
from .world_map import build_world_map_read_model

__all__ = [
    "build_annotations_view_model",
    "build_country_profile_read_model",
    "build_domain_detail_read_model",
    "build_readiness_view_model",
    "build_release_demo_package_view_model",
    "render_release_demo_package_body",
    "build_release_failure_drill_report",
    "build_release_readiness_index",
    "build_repo_release_gate_assessment",
    "render_release_evidence_markdown",
    "build_release_gate_view_model",
    "build_source_coverage_read_model",
    "build_stakeholder_functional_closure_report",
    "build_stakeholder_e2e_flow_coverage_report",
    "render_stakeholder_e2e_flow_coverage_markdown",
    "build_stakeholder_e2e_ui_smoke_report",
    "build_stakeholder_requirement_quality_report",
    "render_stakeholder_requirement_quality_markdown",
    "build_stakeholder_system_traceability_report",
    "render_stakeholder_system_traceability_markdown",
    "build_stakeholder_verification_coverage_report",
    "render_stakeholder_verification_coverage_markdown",
    "build_system_status_read_model",
    "build_world_map_read_model",
]
