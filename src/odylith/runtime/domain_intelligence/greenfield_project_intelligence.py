"""Project-intelligence contracts for confirmed greenfield proposals."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values


PROJECT_INTELLIGENCE_SCHEMA_VERSION = "odylith.greenfield.project_intelligence.v1"
PROJECT_WORKSTREAM_SECTION_TITLE = "Project Requirements"

PROJECT_INTELLIGENCE_LAYERS: tuple[str, ...] = (
    "intent",
    "scope",
    "ontology",
    "state",
    "operators",
    "constraints",
    "source_of_truth_map",
    "evidence",
    "decisions",
    "assumptions",
    "topology",
    "invariants",
    "risks",
    "validation_obligations",
    "artifacts",
    "owners",
    "execution_memory",
    "metrics",
    "change_model",
    "invalidation_rules",
    "conflict_model",
    "transfer_priors",
)

_LAYER_LABELS = {
    "intent": "Intent",
    "scope": "Scope",
    "ontology": "Ontology",
    "state": "State",
    "operators": "Operators",
    "constraints": "Constraints",
    "source_of_truth_map": "Source Of Truth",
    "evidence": "Evidence",
    "decisions": "Decisions",
    "assumptions": "Assumptions",
    "topology": "Topology",
    "invariants": "Invariants",
    "risks": "Risks",
    "validation_obligations": "Validation",
    "artifacts": "Artifacts",
    "owners": "Owners",
    "execution_memory": "Memory",
    "metrics": "Metrics",
    "change_model": "Change",
    "invalidation_rules": "Invalidation Rules",
    "conflict_model": "Conflicts",
    "transfer_priors": "Transfer",
}

_PREVIEW_LAYER_LIMITS = {
    "intent": 6,
    "scope": 4,
    "ontology": 5,
    "state": 5,
    "operators": 5,
    "constraints": 4,
    "source_of_truth_map": 4,
    "evidence": 4,
    "decisions": 4,
    "assumptions": 3,
    "topology": 5,
    "invariants": 4,
    "risks": 4,
    "validation_obligations": 4,
    "artifacts": 4,
    "owners": 4,
    "execution_memory": 4,
    "metrics": 4,
    "change_model": 4,
    "invalidation_rules": 4,
    "conflict_model": 3,
    "transfer_priors": 3,
}


def normalize_project_intelligence(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
    domain_profile: Any | None = None,
    project_brief: Mapping[str, Any] | None = None,
    program: Mapping[str, Any] | None = None,
    release_plan: Mapping[str, Any] | None = None,
    components: Sequence[Any] = (),
    diagrams: Sequence[Any] = (),
    observed_source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize proposal project intelligence without inferring content."""

    _ = intent, release_selector, domain_profile, project_brief, program, release_plan, components, diagrams, observed_source
    if not isinstance(value, Mapping):
        return {}
    result = dict(value)
    result.setdefault("schema_version", PROJECT_INTELLIGENCE_SCHEMA_VERSION)
    result["control_surface_summary"] = _row_list(result.get("control_surface_summary"))
    result["customization_flow"] = _row_list(result.get("customization_flow"))
    for key in PROJECT_INTELLIGENCE_LAYERS:
        result[key] = _row_list(result.get(key))
    return result


def project_intelligence_issues(value: Any) -> list[str]:
    """Return validation issues for the proposal project intelligence object."""

    if not isinstance(value, Mapping):
        return ["proposal `project_intelligence` must be an object"]
    issues: list[str] = []
    _require_text(value, "purpose", issues=issues, min_words=12)
    _require_text(value, "coding_posture", issues=issues, min_words=14)
    if len(_row_list(value.get("control_surface_summary"))) < 5:
        issues.append("proposal `project_intelligence.control_surface_summary` must include at least five control-surface rows")
    if len(_row_list(value.get("customization_flow"))) < 4:
        issues.append("proposal `project_intelligence.customization_flow` must include at least four operator-visible steps")
    for key in PROJECT_INTELLIGENCE_LAYERS:
        rows = _row_list(value.get(key))
        minimum = 3 if key in {"intent", "ontology", "operators", "validation_obligations", "topology"} else 2
        if len(rows) < minimum:
            issues.append(f"proposal `project_intelligence.{key}` must include at least {minimum} rows")
        elif any(_word_count(row) < 5 for row in rows[:minimum]):
            issues.append(f"proposal `project_intelligence.{key}` contains shallow rows")
    return issues


def render_project_intelligence_section(value: Any, *, preview: bool = False) -> str:
    """Render project intelligence as Markdown for proposal text or records."""

    if not isinstance(value, Mapping):
        return ""
    lines: list[str] = []
    purpose = clean_text(value.get("purpose"))
    coding_posture = clean_text(value.get("coding_posture"))
    if purpose:
        lines.append(purpose)
    if coding_posture:
        lines.extend(["", f"**Coding posture:** {coding_posture}"])
    _append_layer(lines, "Product Requirements", value.get("control_surface_summary"), limit=5 if preview else 0)
    _append_layer(lines, "Customization Flow", value.get("customization_flow"), limit=5 if preview else 0)
    for key in PROJECT_INTELLIGENCE_LAYERS:
        _append_layer(lines, _LAYER_LABELS[key], value.get(key), limit=_preview_layer_limit(key) if preview else 0)
    return "\n".join(lines).strip()


def _preview_layer_limit(key: str) -> int:
    return _PREVIEW_LAYER_LIMITS.get(key, 2)


def _append_layer(lines: list[str], label: str, value: Any, *, limit: int) -> None:
    rows = _row_list(value)
    if limit:
        rows = rows[:limit]
    if not rows:
        return
    if lines:
        lines.append("")
    lines.append(f"### {label}")
    lines.extend(f"- {row}" for row in rows)


def _row_list(value: Any) -> list[str]:
    if isinstance(value, str):
        token = clean_text(value)
        return [token] if token else []
    rows = [clean_text(item) for item in text_values(value)]
    return [row for row in rows if row]


def _require_text(value: Mapping[str, Any], key: str, *, issues: list[str], min_words: int) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(f"proposal `project_intelligence.{key}` must be non-empty")
        return
    if _word_count(text) < min_words:
        issues.append(f"proposal `project_intelligence.{key}` must contain at least {min_words} meaningful words")


def _word_count(value: str) -> int:
    return len([part for part in clean_text(value).replace("/", " ").split() if part.strip()])


__all__ = [
    "PROJECT_INTELLIGENCE_SCHEMA_VERSION",
    "PROJECT_WORKSTREAM_SECTION_TITLE",
    "PROJECT_INTELLIGENCE_LAYERS",
    "normalize_project_intelligence",
    "project_intelligence_issues",
    "render_project_intelligence_section",
]
