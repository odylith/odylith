"""Workstream-intelligence contracts for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


SECTION_TITLE = "Domain Intelligence"

_REQUIRED_LAYERS = (
    "intent",
    "scope",
    "ontology",
    "state",
    "operators",
    "constraints",
    "source_of_truth_map",
    "evidence_model",
    "decisions",
    "assumptions",
    "topology",
    "invariants",
    "risks",
    "validation_obligations",
    "artifacts",
    "authority",
    "owners",
    "execution_memory",
    "metrics",
    "change_model",
    "invalidation_rules",
    "conflict_model",
    "transfer_priors",
)

_LAYER_LABELS = {
    "intent": "Intent And Outcome",
    "scope": "Scope And Boundary",
    "ontology": "Domain Ontology",
    "state": "State Model",
    "operators": "Allowed Operators",
    "constraints": "Constraints And Boundary Conditions",
    "source_of_truth_map": "Source Of Truth Map",
    "evidence_model": "Evidence Model",
    "decisions": "Decision History",
    "assumptions": "Assumptions And Uncertainty",
    "topology": "Dependency Topology",
    "invariants": "Invariants",
    "risks": "Risk Register",
    "validation_obligations": "Validation Obligations",
    "artifacts": "Work Products And Artifact Contracts",
    "authority": "Stakeholders And Authority",
    "owners": "Ownership Map",
    "execution_memory": "Memory And Prior Executions",
    "metrics": "Metrics And Observables",
    "change_model": "Change Model",
    "invalidation_rules": "Invalidation Rules",
    "conflict_model": "Conflict Model",
    "transfer_priors": "Reuse And Transfer Priors",
}


def enrich_backlog_rows(
    rows: Sequence[Any],
    *,
    intent: Mapping[str, Any],
    program: Mapping[str, Any],
    release_plan: Mapping[str, Any],
    validation_strategy: Sequence[Any],
    security_compliance: Any,
    components: Sequence[Any],
    diagrams: Sequence[Any],
    domain_profile: Any | None = None,
) -> list[Any]:
    """Preserve proposal workstream intelligence without synthesis."""

    _ = intent, program, release_plan, validation_strategy, security_compliance, components, diagrams, domain_profile
    return [dict(row) if isinstance(row, Mapping) else row for row in rows]


def render_domain_intelligence_section(value: Any) -> str:
    """Render a domain-intelligence mapping as workstream Markdown."""

    if not isinstance(value, Mapping):
        return ""
    lines: list[str] = []
    summary = clean_text(value.get("summary"))
    if summary:
        lines.append(summary)
    for key in _REQUIRED_LAYERS:
        rendered = _render_layer(value.get(key))
        if not rendered:
            continue
        if lines:
            lines.append("")
        lines.append(f"### {_LAYER_LABELS[key]}")
        lines.extend(rendered)
    return "\n".join(lines).strip()


def domain_intelligence_issues(value: Any, *, owner: str) -> list[str]:
    """Return actionable validation issues for one proposal payload."""

    if not isinstance(value, Mapping):
        return [f"{owner} must include domain_intelligence object"]
    issues: list[str] = []
    for key in _REQUIRED_LAYERS:
        nested = value.get(key)
        if not _layer_has_depth(nested):
            issues.append(f"{owner} domain_intelligence.{key} is missing or too shallow")
    if len(_list_values(value.get("ontology"))) < 4:
        issues.append(f"{owner} domain_intelligence.ontology must define at least four domain terms")
    if len(_list_values(value.get("operators"))) < 3:
        issues.append(f"{owner} domain_intelligence.operators must define at least three state-changing operations")
    if len(_list_values(value.get("validation_obligations"))) < 3:
        issues.append(f"{owner} domain_intelligence.validation_obligations must define at least three proof gates")
    duplicate_terms = _duplicate_ontology_terms(value.get("ontology"))
    if duplicate_terms:
        issues.append(
            f"{owner} domain_intelligence.ontology repeats operational term(s): {', '.join(duplicate_terms)}"
        )
    if _contains_malformed_ownership_phrase(value):
        issues.append(f"{owner} domain_intelligence contains malformed ownership phrase")
    return issues


def _render_layer(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        rows: list[str] = []
        for key, nested in value.items():
            rendered = "; ".join(text_values(nested))
            if rendered:
                rows.append(f"- {clean_text(key)}: {rendered}")
        return rows
    values = _list_values(value)
    return [f"- {item}" for item in values if item]


def _list_values(value: Any) -> list[str]:
    return [clean_text(item) for item in text_values(value) if clean_text(item)]


def _layer_has_depth(value: Any) -> bool:
    text = " ".join(text_values(value)).strip()
    return len(text.split()) >= 8


def _duplicate_ontology_terms(value: Any) -> list[str]:
    seen: dict[str, str] = {}
    duplicates: list[str] = []
    for row in _list_values(value):
        label = clean_text(row.split(":", 1)[0] if ":" in row else row)
        key = _ontology_term_key(row)
        if not key:
            continue
        if key in seen and seen[key] not in duplicates:
            duplicates.append(seen[key])
        else:
            seen[key] = label
    return duplicates


def _ontology_term_key(value: str) -> str:
    text = clean_text(value)
    label = text.split(":", 1)[0] if ":" in text else text
    return label.casefold()


def _contains_malformed_ownership_phrase(value: Any) -> bool:
    for token in text_values(value):
        lowered = token.casefold()
        if " owns own " in f" {lowered} " or " owns owns " in f" {lowered} ":
            return True
    return False


__all__ = [
    "SECTION_TITLE",
    "domain_intelligence_issues",
    "enrich_backlog_rows",
    "render_domain_intelligence_section",
]
