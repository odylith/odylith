"""Quality-lens repair ownership contract for greenfield pre-confirm review."""

from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_generated_text as clean_text


QUALITY_LENS_SEMANTIC_REPAIR_CHECKS = frozenset(
    {
        "complete_first_path",
        "domain_term_coverage",
        "proof_boundary",
        "state_object",
        "system_boundary",
        "visible_result",
    }
)
QUALITY_LENS_PLAN_REPAIR_CHECKS = frozenset(
    {
        "atlas_topology",
        "component_topology",
        "decision_boundary",
        "first_release_scope",
        "high_risk_assumptions",
        "implementation_readiness",
        "measurable_success",
    }
)
QUALITY_LENS_GATE_ONLY_CHECKS = frozenset({"component_specs", "prewrite_safety", "validation_evidence"})
QUALITY_LENS_REPAIR_OWNER_BY_CHECK = {
    **{check: "semantic_model_compiler" for check in QUALITY_LENS_SEMANTIC_REPAIR_CHECKS},
    **{check: "artifact_plan_projector" for check in QUALITY_LENS_PLAN_REPAIR_CHECKS},
    **{check: "prewrite_gate" for check in QUALITY_LENS_GATE_ONLY_CHECKS},
}


def quality_lens_repair_owner(check_name: str) -> str:
    """Return the typed repair owner for one reviewer-lens check."""

    return QUALITY_LENS_REPAIR_OWNER_BY_CHECK.get(clean_text(check_name), "")


__all__ = [
    "QUALITY_LENS_GATE_ONLY_CHECKS",
    "QUALITY_LENS_PLAN_REPAIR_CHECKS",
    "QUALITY_LENS_REPAIR_OWNER_BY_CHECK",
    "QUALITY_LENS_SEMANTIC_REPAIR_CHECKS",
    "quality_lens_repair_owner",
]
