"""Deterministic reviewer-lens gates for confirmed greenfield packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


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
    lenses: dict[str, Any] = {}
    issues: list[str] = []
    for lens_name in QUALITY_LENS_NAMES:
        checks = lens_checks[lens_name]
        lens_issues = [check["issue"] for check in checks if check["status"] != "passed"]
        issues.extend(lens_issues)
        lenses[lens_name] = {
            "status": "failed" if lens_issues else "passed",
            "checks": checks,
            "issues": lens_issues,
        }
    issues = unique_text(issues)
    return {
        "version": QUALITY_LENS_VERSION,
        "status": "failed" if issues else "passed",
        "lenses": lenses,
        "issues": issues,
    }


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
    visible_result = normalize_string(first_path.get("visible_result")) or normalize_string(intent.get("proof_boundary"))
    backlog_rows = mapping_rows(proposal.get("backlog"))
    assumptions = mapping_rows(proposal.get("assumptions"))
    ambiguities = _rows_or_text_values(proposal.get("open_questions"))
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
                and len(events) >= 3
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
    diagrams = mapping_rows(proposal.get("diagrams"))
    atlas_sources = _as_mapping(getattr(package, "rendered_atlas_sources", None))
    internal_systems = _rows_or_text_values(domain.get("internal_systems")) or _rows_or_text_values(
        intent.get("internal_systems")
    )
    external_systems = _rows_or_text_values(domain.get("external_systems")) or _rows_or_text_values(
        intent.get("external_systems")
    )
    external_boundary_known = "external_systems" in domain or "external_systems" in intent
    return [
        _check(
            bool(normalize_string(intent.get("state_object"))),
            "state_object",
            "accepted state object present",
            "quality lens architect missing accepted state object",
        ),
        _check(
            len(components) >= 3 and len(internal_systems) >= 2,
            "component_topology",
            f"{len(components)} active component(s), {len(internal_systems)} internal system(s)",
            "quality lens architect missing component topology from internal systems",
        ),
        _check(
            len(diagrams) >= 4 and len(atlas_sources) == len(diagrams),
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
    return [
        _check(
            component_spec_evidence_count >= len(components) >= 3,
            "component_specs",
            f"{component_spec_evidence_count} spec or preview evidence row(s) for {len(components)} active component(s)",
            "quality lens engineer missing rendered component specs",
        ),
        _check(
            bool(normalize_string(next_steps.get("implementation_prompt")))
            and len(text_values(next_steps.get("verification_commands"))) >= 1
            and len(text_values(next_steps.get("coding_readiness_gates"))) >= 3,
            "implementation_readiness",
            "implementation prompt, verification commands, and coding-readiness gates inspected",
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
            not program_result or normalize_string(program_result.get("dry_run")).casefold() in {"true", "1"},
            "prewrite_safety",
            "prewrite program dry-run evidence inspected",
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
        if _terms(normalize_string(row.get("statement"))) & rendered_terms
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
    return {
        "name": name,
        "status": "passed" if condition else "failed",
        "evidence": evidence,
        "issue": "" if condition else issue,
    }


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


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "QUALITY_LENS_NAMES",
    "QUALITY_LENS_VERSION",
    "build_greenfield_quality_lens_report",
    "greenfield_quality_lens_issues",
]
