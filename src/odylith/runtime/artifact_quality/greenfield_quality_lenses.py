"""Deterministic reviewer-lens gates for confirmed greenfield packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import quality_lens_repair_owner
from odylith.runtime.reasoning.tribunal_lens import tribunal_lens_check
from odylith.runtime.reasoning.tribunal_lens import tribunal_lens_report


QUALITY_LENS_VERSION = "greenfield-quality-lenses-v1"
QUALITY_LENS_NAMES = ("product_manager", "architect", "engineer", "domain_expert")
_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "artifact",
        "component",
        "complete",
        "confirm",
        "created",
        "evidence",
        "first",
        "greenfield",
        "internal",
        "operator",
        "path",
        "product",
        "proof",
        "record",
        "release",
        "state",
        "system",
        "user",
        "workstream",
    }
)
_CHECK_TARGETS = {
    "complete_first_path": {
        "role": "Product manager",
        "surface": "product_manager",
        "target_path": "semantic_model.first_path_contract",
        "semantic_node_id": "SemanticModelIR.first_path_contract",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
    "measurable_success": {
        "role": "Product manager",
        "surface": "radar",
        "target_path": "proposal.backlog.success_metrics",
        "semantic_node_id": "ArtifactPlanIR.radar",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "first_release_scope": {
        "role": "Product manager",
        "surface": "release",
        "target_path": "proposal.release_plan",
        "semantic_node_id": "ArtifactPlanIR.release_plan",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "decision_boundary": {
        "role": "Product manager",
        "surface": "product_manager",
        "target_path": "proposal.assumptions",
        "semantic_node_id": "ArtifactPlanIR.assumptions",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "state_object": {
        "role": "Architect",
        "surface": "architect",
        "target_path": "semantic_model.domain_ontology.state_object",
        "semantic_node_id": "SemanticModelIR.domain_ontology.state_object",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
    "component_topology": {
        "role": "Architect",
        "surface": "registry",
        "target_path": "proposal.components",
        "semantic_node_id": "ArtifactPlanIR.registry",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "atlas_topology": {
        "role": "Architect",
        "surface": "atlas",
        "target_path": "proposal.diagrams",
        "semantic_node_id": "ArtifactPlanIR.atlas",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "system_boundary": {
        "role": "Architect",
        "surface": "architect",
        "target_path": "semantic_model.domain_ontology.external_systems",
        "semantic_node_id": "SemanticModelIR.domain_ontology.external_systems",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
    "component_specs": {
        "role": "Engineer",
        "surface": "registry",
        "target_path": "prewrite_package.registry.specs",
        "semantic_node_id": "ArtifactDraftSet.registry",
        "repairability": "unrepairable",
        "owner": "prewrite_gate",
    },
    "implementation_readiness": {
        "role": "Engineer",
        "surface": "engineer",
        "target_path": "prewrite_package.next_steps",
        "semantic_node_id": "ArtifactPlanIR.next_steps",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "validation_evidence": {
        "role": "Engineer",
        "surface": "engineer",
        "target_path": "prewrite_package.validation",
        "semantic_node_id": "ArtifactDraftSet.validation",
        "repairability": "unrepairable",
        "owner": "prewrite_gate",
    },
    "prewrite_safety": {
        "role": "Engineer",
        "surface": "engineer",
        "target_path": "prewrite_package.program",
        "semantic_node_id": "ArtifactDraftSet.program",
        "repairability": "unrepairable",
        "owner": "prewrite_gate",
    },
    "proof_boundary": {
        "role": "Domain expert",
        "surface": "domain_expert",
        "target_path": "semantic_model.domain_ontology.proof_boundary",
        "semantic_node_id": "SemanticModelIR.domain_ontology.proof_boundary",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
    "domain_term_coverage": {
        "role": "Domain expert",
        "surface": "domain_expert",
        "target_path": "semantic_model.domain_ontology",
        "semantic_node_id": "SemanticModelIR.domain_ontology",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
    "high_risk_assumptions": {
        "role": "Domain expert",
        "surface": "domain_expert",
        "target_path": "proposal.assumptions",
        "semantic_node_id": "ArtifactPlanIR.assumptions",
        "repairability": "plan_patch",
        "owner": "artifact_plan_projector",
    },
    "visible_result": {
        "role": "Domain expert",
        "surface": "domain_expert",
        "target_path": "semantic_model.first_path_contract.visible_result",
        "semantic_node_id": "SemanticModelIR.first_path_contract.visible_result",
        "repairability": "semantic_patch",
        "owner": "semantic_model_compiler",
    },
}


def build_greenfield_quality_lens_report(package: Any) -> dict[str, Any]:
    """Return pass/fail evidence for PM, architect, engineer, and domain lenses."""

    proposal = _as_mapping(getattr(package, "proposal", None))
    semantic = _as_mapping(proposal.get("semantic_model"))
    rendered_text = _rendered_text(package)
    lens_checks = {
        "product_manager": _product_manager_checks(package, proposal, semantic),
        "architect": _architect_checks(package, proposal, semantic),
        "engineer": _engineer_checks(package, proposal),
        "domain_expert": _domain_expert_checks(package, proposal, semantic, rendered_text),
    }
    return tribunal_lens_report(lens_checks, version=QUALITY_LENS_VERSION)


def greenfield_quality_lens_issues(package: Any) -> list[str]:
    """Return issue strings suitable for the post-confirm completion gate."""

    report = build_greenfield_quality_lens_report(package)
    return [str(issue) for issue in report.get("issues", []) if str(issue).strip()]


def _product_manager_checks(
    package: Any,
    proposal: Mapping[str, Any],
    semantic: Mapping[str, Any],
) -> list[dict[str, str]]:
    intent = _as_mapping(proposal.get("intent"))
    first_path = _as_mapping(semantic.get("first_path_contract"))
    diagram_graph = _as_mapping(semantic.get("diagram_event_graph"))
    events = [row for row in first_path.get("events", []) if isinstance(row, Mapping)] or [
        row for row in diagram_graph.get("events", []) if isinstance(row, Mapping)
    ]
    capability = normalize_string(first_path.get("capability")) or normalize_string(intent.get("first_path"))
    visible_result = normalize_string(first_path.get("visible_result"))
    backlog_rows = mapping_rows(proposal.get("backlog"))
    assumptions = _rows_or_text_values(proposal.get("assumptions"))
    ambiguities = _rows_or_text_values(proposal.get("open_questions"))
    required_events = 3 if _strict_confirmed_create_payload(proposal) else 2
    release_ids = tuple(
        str(item).strip()
        for item in getattr(package, "release_workstream_ids", ())
        if str(item).strip()
    )
    return [
        _check(
            bool(
                capability
                and visible_result
                and len(events) >= required_events
            ),
            "complete_first_path",
            f"{len(events)} first-path event(s), capability and visible result present",
            "quality lens product_manager missing complete first-path capability, events, or visible result",
        ),
        _check(
            any(len(text_values(row.get("success_metrics"))) >= 2 for row in backlog_rows),
            "measurable_success",
            f"{len(backlog_rows)} workstream contract(s) inspected for success metrics",
            "quality lens product_manager missing measurable success metrics",
        ),
        _check(
            not normalize_string(getattr(package, "release_selector", "")) or bool(release_ids),
            "first_release_scope",
            f"{len(release_ids)} first-release workstream id(s)",
            "quality lens product_manager missing first-release workstream scope",
        ),
        _check(
            len(assumptions) >= 2 and len(ambiguities) >= 1,
            "decision_boundary",
            f"{len(assumptions)} assumption(s), {len(ambiguities)} ambiguity row(s)",
            "quality lens product_manager missing assumptions or ambiguity boundary",
        ),
    ]


def _architect_checks(
    package: Any,
    proposal: Mapping[str, Any],
    semantic: Mapping[str, Any],
) -> list[dict[str, str]]:
    intent = _as_mapping(proposal.get("intent"))
    domain = _as_mapping(semantic.get("domain_ontology"))
    components = _active_component_rows(proposal)
    component_rows = mapping_rows(proposal.get("components"))
    diagrams = mapping_rows(proposal.get("diagrams"))
    atlas_sources = _as_mapping(getattr(package, "rendered_atlas_sources", None))
    strict_create = _strict_confirmed_create_payload(proposal)
    required_diagrams = 4 if strict_create else 2
    internal_systems = _rows_or_text_values(domain.get("internal_systems")) or _rows_or_text_values(
        intent.get("internal_systems")
    )
    external_systems = _rows_or_text_values(domain.get("external_systems")) or _rows_or_text_values(
        intent.get("external_systems")
    )
    external_boundary_known = bool(external_systems)
    state_object = normalize_string(intent.get("state_object")) or normalize_string(domain.get("state_object"))
    component_topology_complete = _component_topology_covers_internal_systems(
        internal_systems,
        component_rows=component_rows,
    )
    return [
        _check(
            bool(state_object),
            "state_object",
            "accepted state object present",
            "quality lens architect missing accepted state object",
        ),
        _check(
            component_topology_complete,
            "component_topology",
            f"{len(components)} active component(s), {len(component_rows)} component row(s), {len(internal_systems)} internal system(s)",
            "quality lens architect missing component topology from internal systems",
        ),
        _check(
            len(diagrams) >= required_diagrams and len(atlas_sources) == len(diagrams),
            "atlas_topology",
            f"{len(atlas_sources)} rendered Atlas source(s) for {len(diagrams)} diagram contract(s)",
            "quality lens architect missing rendered Atlas topology coverage",
        ),
        _check(
            external_boundary_known,
            "system_boundary",
            f"{len(external_systems)} external system boundary row(s)",
            "quality lens architect missing explicit external system boundary",
        ),
    ]


def _engineer_checks(package: Any, proposal: Mapping[str, Any]) -> list[dict[str, str]]:
    components = _active_component_rows(proposal)
    specs = _as_mapping(getattr(package, "rendered_component_specs", None))
    component_preview = [row for row in getattr(package, "component_registry_preview", ()) if isinstance(row, Mapping)]
    component_spec_evidence_count = len(specs) if specs else len(component_preview)
    next_steps = _as_mapping(getattr(package, "next_steps_preview", None))
    backlog_result = _as_mapping(getattr(package, "backlog_result", None))
    program_result = _as_mapping(getattr(package, "program_result", None))
    prewrite_safety = _as_mapping(getattr(package, "prewrite_safety_preview", None))
    component_specs_complete = bool(components) and component_spec_evidence_count >= len(components)
    return [
        _check(
            component_specs_complete,
            "component_specs",
            f"{component_spec_evidence_count} spec or preview evidence row(s) for {len(components)} active component(s)",
            "quality lens engineer missing rendered component specs",
        ),
        _check(
            bool(normalize_string(next_steps.get("implementation_prompt")))
            and bool(normalize_string(next_steps.get("start_workstream_id")))
            and normalize_string(next_steps.get("start_workstream_id")).upper()
            in normalize_string(next_steps.get("implementation_prompt")).upper()
            and len(text_values(next_steps.get("verification_commands"))) >= 2
            and len(text_values(next_steps.get("coding_readiness_gates"))) >= 4,
            "implementation_readiness",
            "implementation prompt, governed start workstream, verification commands, and coding-readiness gates inspected",
            "quality lens engineer missing implementation readiness evidence",
        ),
        _check(
            _gate_status(_as_mapping(backlog_result.get("validation_gate"))) == "passed"
            and all(_gate_status(_as_mapping(row.get("validation_gate"))) == "passed" for row in component_preview),
            "validation_evidence",
            f"{len(component_preview)} component preview validation gate(s)",
            "quality lens engineer missing passed validation evidence",
        ),
        _check(
            _prewrite_safety_passed(program_result=program_result, prewrite_safety=prewrite_safety),
            "prewrite_safety",
            _prewrite_safety_evidence_summary(program_result=program_result, prewrite_safety=prewrite_safety),
            "quality lens engineer missing prewrite dry-run safety evidence",
        ),
    ]


def _domain_expert_checks(
    package: Any,
    proposal: Mapping[str, Any],
    semantic: Mapping[str, Any],
    rendered_text: str,
) -> list[dict[str, str]]:
    domain = _as_mapping(semantic.get("domain_ontology"))
    first_path = _as_mapping(semantic.get("first_path_contract"))
    proof_boundary = normalize_string(domain.get("proof_boundary"))
    rendered_terms = _terms(rendered_text)
    source_terms = _terms(
        " ".join(
            text_values(
                [
                    _as_mapping(proposal.get("intent")).get("state_object"),
                    first_path.get("capability"),
                    first_path.get("visible_result"),
                    proof_boundary,
                ]
            )
        )
    )
    high_risk_assumptions = [
        row
        for row in mapping_rows(proposal.get("assumptions"))
        if normalize_string(row.get("tier")).casefold() == "user_intent"
        and _high_risk_statement(normalize_string(row.get("statement")))
    ]
    covered_high_risk = [
        row
        for row in high_risk_assumptions
        if _high_risk_assumption_covered(normalize_string(row.get("statement")), rendered_terms)
    ]
    return [
        _check(
            bool(proof_boundary),
            "proof_boundary",
            "accepted proof boundary present",
            "quality lens domain_expert missing proof boundary",
        ),
        _check(
            not source_terms or len(source_terms & rendered_terms) >= min(4, max(2, len(source_terms) // 5)),
            "domain_term_coverage",
            f"{len(source_terms & rendered_terms)} domain term(s) carried into rendered artifacts",
            "quality lens domain_expert missing domain term coverage in rendered artifacts",
        ),
        _check(
            not high_risk_assumptions or len(covered_high_risk) == len(high_risk_assumptions),
            "high_risk_assumptions",
            f"{len(covered_high_risk)} of {len(high_risk_assumptions)} high-risk accepted assumption(s) covered",
            "quality lens domain_expert missing high-risk accepted assumption coverage",
        ),
        _check(
            bool(normalize_string(first_path.get("visible_result"))),
            "visible_result",
            "domain-facing visible result present",
            "quality lens domain_expert missing domain-facing visible result",
        ),
    ]


def _check(condition: bool, name: str, evidence: str, issue: str) -> dict[str, str]:
    meta = _CHECK_TARGETS.get(name, {})
    return tribunal_lens_check(
        lens=_lens_for_check(name),
        role=str(meta.get("role", "")),
        name=name,
        passed=condition,
        evidence=evidence,
        issue=issue,
        surface=str(meta.get("surface", "review_report")),
        target_path=str(meta.get("target_path", "")),
        projection_id="review_report",
        semantic_node_id=str(meta.get("semantic_node_id", "ReviewReport.quality_lenses")),
        severity="high",
        repairability=str(meta.get("repairability", "semantic_patch")),
        owner=quality_lens_repair_owner(name) or str(meta.get("owner", "quality_lens_contract")),
    ).to_dict()


def _lens_for_check(name: str) -> str:
    if name in {"complete_first_path", "measurable_success", "first_release_scope", "decision_boundary"}:
        return "product_manager"
    if name in {"state_object", "component_topology", "atlas_topology", "system_boundary"}:
        return "architect"
    if name in {"component_specs", "implementation_readiness", "validation_evidence", "prewrite_safety"}:
        return "engineer"
    return "domain_expert"


def _active_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in mapping_rows(proposal.get("components"))
        if normalize_string(row.get("component_id"))
        and normalize_string(row.get("release_scope")).casefold() not in {"deferred", "out_of_scope", "external"}
    ]
    return rows or [
        row
        for row in mapping_rows(proposal.get("components"))
        if normalize_string(row.get("component_id"))
    ]


def _component_topology_covers_internal_systems(
    internal_systems: Sequence[str],
    *,
    component_rows: Sequence[Mapping[str, Any]],
) -> bool:
    if len(internal_systems) < 2 or not component_rows:
        return False
    component_texts = [
        normalize_string(
            " ".join(
                text_values(
                    [
                        row.get("component_id"),
                        row.get("label"),
                        row.get("responsibility"),
                        row.get("boundary"),
                    ]
                )
            )
        )
        for row in component_rows
    ]
    return all(_system_has_component_coverage(system, component_texts=component_texts) for system in internal_systems)


def _system_has_component_coverage(system: str, *, component_texts: Sequence[str]) -> bool:
    system_terms = _topology_terms(system)
    if not system_terms:
        return False
    for component_text in component_texts:
        component_terms = _topology_terms(component_text)
        if len(system_terms & component_terms) >= min(2, len(system_terms)):
            return True
    return False


def _topology_terms(value: str) -> set[str]:
    return set(
        ordered_terms(
            value,
            stopwords=_TERM_STOPWORDS - {"evidence"},
            minimum=4,
            preserve_terms={"ai", "api", "ev", "glp", "ml", "sms", "ui", "ux"},
            stem_ing=True,
            stem_ing_minimum_length=5,
        )
    )


def _strict_confirmed_create_payload(proposal: Mapping[str, Any]) -> bool:
    intent = _as_mapping(proposal.get("intent"))
    return (
        normalize_string(intent.get("reasoning_mode")) == "odylith_confirmed_governed_proposal"
        and normalize_string(proposal.get("write_policy")) == "confirmed_intent_before_confirmed_create"
    )


def _rows_or_text_values(value: Any) -> list[str]:
    rows = mapping_rows(value)
    if rows:
        return [
            normalized
            for row in rows
            if (normalized := normalize_string(" ".join(text_values(row))))
        ]
    return [normalize_string(item) for item in text_values(value) if normalize_string(item)]


def _rendered_text(package: Any) -> str:
    return "\n".join(
        text_values(
            [
                getattr(package, "rendered_component_specs", None),
                getattr(package, "rendered_atlas_sources", None),
                getattr(package, "component_registry_preview", None),
                getattr(package, "project_brief_preview", None),
                getattr(package, "accepted_project_preview", None),
                getattr(package, "compass_memory_preview", None),
                getattr(package, "next_steps_preview", None),
                getattr(package, "backlog_result", None),
                getattr(package, "program_result", None),
                getattr(package, "release_target_result", None),
                getattr(package, "release_assignment_result", None),
            ]
        )
    )


def _terms(value: str) -> set[str]:
    return set(
        ordered_terms(
            value,
            stopwords=_TERM_STOPWORDS,
            minimum=4,
            preserve_terms={"ai", "api", "ev", "glp", "ml", "sms", "ui", "ux"},
            stem_ing=True,
            stem_ing_minimum_length=5,
        )
    )


def _high_risk_assumption_covered(statement: str, rendered_terms: set[str]) -> bool:
    terms = _terms(statement)
    if not terms:
        return True
    covered = terms & rendered_terms
    required = min(len(terms), min(3, max(2, len(terms) // 2)))
    return len(covered) >= required


def _high_risk_statement(value: str) -> bool:
    text = normalize_string(value).casefold()
    return any(
        token in text
        for token in (
            "authorized",
            "compliance",
            "diagnosis",
            "legal",
            "must",
            "only",
            "override",
            "privacy",
            "safety",
            "security",
            "strict",
        )
    )


def _gate_status(value: Mapping[str, Any]) -> str:
    return normalize_string(value.get("status")).casefold()


def _prewrite_safety_passed(
    *,
    program_result: Mapping[str, Any],
    prewrite_safety: Mapping[str, Any],
) -> bool:
    if normalize_string(prewrite_safety.get("status")).casefold() == "passed":
        checks = _as_mapping(prewrite_safety.get("checks"))
        return bool(checks) and all(bool(value) for value in checks.values())
    return bool(program_result) and normalize_string(program_result.get("dry_run")).casefold() in {"true", "1"}


def _prewrite_safety_evidence_summary(
    *,
    program_result: Mapping[str, Any],
    prewrite_safety: Mapping[str, Any],
) -> str:
    if prewrite_safety:
        checks = _as_mapping(prewrite_safety.get("checks"))
        passed = sum(1 for value in checks.values() if bool(value))
        return f"{passed} of {len(checks)} prewrite safety check(s) passed"
    if program_result:
        return "prewrite program dry-run evidence inspected"
    return "0 prewrite safety check(s) present"


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "QUALITY_LENS_NAMES",
    "QUALITY_LENS_VERSION",
    "build_greenfield_quality_lens_report",
    "greenfield_quality_lens_issues",
]
