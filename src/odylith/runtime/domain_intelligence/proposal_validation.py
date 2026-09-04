"""Validation for host-reasoned greenfield governance proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    first_path_relations_from_intent,
)
from odylith.runtime.domain_intelligence.greenfield_authored_proposal import (
    authored_projection_parity_issues,
)
from odylith.runtime.domain_intelligence.greenfield_scalar_values import (
    scalar_word_count as word_count,
)
from odylith.runtime.domain_intelligence.project_intelligence_binding import project_intelligence_binding_issues


_ALLOWED_MERMAID_PREFIXES = (
    "flowchart ",
    "flowchart\n",
    "graph ",
    "graph\n",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "stateDiagram-v2",
    "erDiagram",
    "journey",
    "gantt",
    "mindmap",
    "timeline",
    "quadrantChart",
    "xychart-beta",
    "block-beta",
    "architecture-beta",
    "packet-beta",
    "sankey-beta",
    "pie",
    "gitGraph",
)

_VALID_EVIDENCE_TIERS = {"observed_source", "user_intent", "odylith_assumption"}
_VALID_PROPOSAL_MODES = {"host_reasoned_greenfield_proposal", "host_reasoned_proposal"}
_PLACEHOLDER_TOKENS = {"", "-", "n/a", "na", "none", "tbd", "todo"}
_FLOWCHART_PREFIXES = ("flowchart ", "flowchart\n", "graph ", "graph\n")
_LONG_LABEL_RE = re.compile(r'\["([^"]{72,})"\]|\[([^\]]{72,})\]|\|([^|]{72,})\|')


def validated_mermaid_source(diagram: Mapping[str, Any]) -> str:
    """Return a checked proposal Mermaid source string for one diagram."""

    raw = str(diagram.get("mermaid_source", "") or diagram.get("source", "")).strip()
    slug = str(diagram.get("slug", "<unknown>")).strip() or "<unknown>"
    if not raw:
        raise ValueError(f"diagram `{slug}` is missing proposal mermaid_source")
    if len(raw) > 16000:
        raise ValueError(f"diagram `{slug}` mermaid_source is too large")
    lowered = raw.casefold()
    if "<script" in lowered or "javascript:" in lowered:
        raise ValueError(f"diagram `{slug}` mermaid_source contains unsafe markup")
    first_content = _first_content_line(raw)
    if not any(first_content.startswith(prefix) for prefix in _ALLOWED_MERMAID_PREFIXES):
        raise ValueError(f"diagram `{slug}` mermaid_source must start with a Mermaid diagram declaration")
    _validate_visual_contract(source=raw, slug=slug, first_content=first_content)
    return raw.rstrip() + "\n"


def validate_host_reasoned_proposal(proposal: Mapping[str, Any]) -> None:
    """Fail before writes when a greenfield proposal is incomplete or generic."""

    issues = collect_host_reasoned_proposal_issues(proposal)
    if issues:
        raise ValueError(format_proposal_issue_report("validation", issues))


def collect_host_reasoned_proposal_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Return all proposal validation issues found in one pass."""

    intent_value = proposal.get("intent")
    intent = intent_value if isinstance(intent_value, Mapping) else {}
    model_authored = (
        proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
        and bool(first_path_relations_from_intent(intent))
    )
    if not model_authored:
        return ["greenfield proposal validation requires a sealed authored projection"]

    issues: list[str] = []

    def capture(callback: Any) -> Any:
        try:
            return callback()
        except ValueError as exc:
            issues.append(str(exc))
            return None

    mode = str(proposal.get("mode", "")).strip()
    if mode not in _VALID_PROPOSAL_MODES:
        issues.append("greenfield apply requires a host-reasoned proposal, not a reasoning request or catalog output")
    capture(lambda: _require_mapping(proposal, "intent"))
    capture(lambda: _require_mapping(proposal, "observed_source"))
    capture(lambda: _require_sequence(proposal, "assumptions"))
    capture(lambda: _require_sequence(proposal, "open_questions"))
    capture(lambda: _require_sequence(proposal, "risks"))
    capture(lambda: _require_nonempty_sequence(proposal, "validation_strategy"))
    project_brief = capture(lambda: _require_mapping(proposal, "project_brief"))
    if isinstance(project_brief, Mapping):
        capture(lambda: _validate_authored_project_brief(project_brief))
    project_intelligence = capture(lambda: _require_mapping(proposal, "project_intelligence"))
    if isinstance(project_intelligence, Mapping):
        capture(lambda: _validate_authored_project_intelligence(project_intelligence))
    capture(lambda: _require_mapping(proposal, "release_plan"))
    backlog = capture(lambda: _require_nonempty_sequence(proposal, "backlog"))
    components = capture(lambda: _require_nonempty_sequence(proposal, "components"))
    diagrams = capture(lambda: _require_nonempty_sequence(proposal, "diagrams"))
    if isinstance(backlog, list):
        for index, row in enumerate(backlog, start=1):
            capture(lambda row=row, index=index: _validate_backlog_row(row, index, model_authored=model_authored))
    if isinstance(components, list):
        for index, row in enumerate(components, start=1):
            capture(lambda row=row, index=index: _validate_component_row(row, index, model_authored=model_authored))
    if isinstance(diagrams, list):
        capture(lambda: _validate_diagrams(diagrams, model_authored=model_authored))
    issues.extend(authored_projection_parity_issues(proposal))
    issues.extend(project_intelligence_binding_issues(proposal))
    return _dedupe_issues(issues)


def format_proposal_issue_report(label: str, issues: list[str] | tuple[str, ...]) -> str:
    rows = _dedupe_issues(issues)
    bullets = "\n".join(f"- {issue}" for issue in rows)
    if str(label).casefold() == "validation":
        remediation = "- needs operator/proposal input: provide the missing or underspecified product facts before governed writes."
    else:
        remediation = "- internal repair required: fix the pre-confirm semantic model, renderers, or quality gate before governed writes."
    return (
        f"greenfield proposal {label} failed with {len(rows)} issue(s):\n"
        f"{bullets}\n"
        "Remediation:\n"
        "- auto-enrichment: Odylith already normalized aliases, list-shaped fields, safe dependency/interface defaults, "
        "and default release fields before this check.\n"
        f"{remediation}"
    )


def _dedupe_issues(issues: list[str] | tuple[str, ...]) -> list[str]:
    return dedupe_strings(issues)


def _first_content_line(source: str) -> str:
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("%%"):
            return stripped
    return ""


def _validate_visual_contract(*, source: str, slug: str, first_content: str) -> None:
    if not any(first_content.startswith(prefix) for prefix in _FLOWCHART_PREFIXES):
        return
    if not re.search(
        r"^\s*(?:classDef|style)\s+.*(?:fill|stroke)\s*:",
        source,
        flags=re.IGNORECASE | re.MULTILINE,
    ):
        raise ValueError(
            f"diagram `{slug}` flowchart mermaid_source must define semantic classDef/style colors"
        )
    long_label = _first_long_unwrapped_label(source)
    if long_label:
        raise ValueError(
            f"diagram `{slug}` flowchart mermaid_source has an overlong label; wrap long labels with <br/>"
        )


def _first_long_unwrapped_label(source: str) -> str:
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("%%") or "<br" in stripped.casefold():
            continue
        if stripped.casefold().startswith(("classdef ", "style ", "linkstyle ")):
            continue
        match = _LONG_LABEL_RE.search(stripped)
        if match is None:
            continue
        label = next((group for group in match.groups() if group), "")
        if label:
            return label
    return ""


def _require_mapping(proposal: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = proposal.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"proposal `{key}` must be an object")
    return value


def _require_nonempty_sequence(proposal: Mapping[str, Any], key: str) -> list[Any]:
    value = proposal.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"proposal `{key}` must be a non-empty list")
    return value


def _require_sequence(proposal: Mapping[str, Any], key: str) -> list[Any]:
    value = proposal.get(key)
    if not isinstance(value, list):
        raise ValueError(f"proposal `{key}` must be a list")
    return value


def _validate_backlog_row(row: Any, index: int, *, model_authored: bool = False) -> None:
    if not isinstance(row, Mapping):
        raise ValueError(f"backlog row {index} must be an object")
    for key in ("title", "problem", "customer", "opportunity", "product_view", "recommended_first_slice"):
        min_words = 1 if model_authored else 2 if key == "title" else 1 if key == "customer" else 6
        _require_text(
            row,
            key,
            owner=f"backlog row {index}",
            min_words=min_words,
            legacy_copy_checks=not model_authored,
        )
    if not model_authored:
        _validate_rationale_lines(row, index)
    metrics = [str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()]
    if len(metrics) < (1 if model_authored else 2):
        raise ValueError(f"backlog row {index} must include at least two success_metrics")
    for metric_index, metric in enumerate(metrics, start=1):
        if model_authored:
            continue
        if word_count(metric) < 4:
            raise ValueError(f"backlog row {index} success_metrics[{metric_index}] is too shallow")
    _validate_evidence_tier(row, owner=f"backlog row {index}")


def _validate_rationale_lines(row: Mapping[str, Any], index: int) -> None:
    raw_lines = row.get("rationale_lines", [])
    if isinstance(raw_lines, str):
        lines = [line.strip() for line in raw_lines.splitlines() if line.strip()]
    else:
        lines = [str(item).strip() for item in raw_lines if str(item).strip()] if isinstance(raw_lines, list) else []
    if not lines:
        raise ValueError(
            f"backlog row {index} must include proposal-authored rationale_lines; Odylith will not synthesize ranking rationale"
        )
    joined = "\n".join(line.casefold() for line in lines)
    for marker in (
        "- why now:",
        "- expected outcome:",
        "- tradeoff:",
        "- deferred for now:",
        "- ranking basis:",
    ):
        if marker not in joined:
            raise ValueError(f"backlog row {index} rationale_lines must include `{marker}`")
    for line_index, line in enumerate(lines, start=1):
        if word_count(line) < 7:
            raise ValueError(f"backlog row {index} rationale_lines[{line_index}] is too shallow")


def _validate_component_row(row: Any, index: int, *, model_authored: bool = False) -> None:
    if not isinstance(row, Mapping):
        raise ValueError(f"component row {index} must be an object")
    for key in ("component_id", "label", "kind", "intended_path", "responsibility", "status", "qualification"):
        _require_text(
            row,
            key,
            owner=f"component row {index}",
            min_words=1 if model_authored else 6 if key == "responsibility" else 1,
            legacy_copy_checks=not model_authored,
        )
    if model_authored:
        contract = row.get("component_contract")
        if row.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN or not isinstance(contract, Mapping):
            raise ValueError(f"component row {index} must preserve the authored typed projection contract")
    _validate_evidence_tier(row, owner=f"component row {index}")


def _validate_authored_project_brief(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != "odylith.greenfield.project_brief.v1":
        raise ValueError("model-authored project brief has an unsupported schema version")
    for key in ("purpose", "project_outcome"):
        _require_text(
            value,
            key,
            owner="model-authored project brief",
            legacy_copy_checks=False,
        )
    if not isinstance(value.get("blueprint_sections"), list) or not value.get("blueprint_sections"):
        raise ValueError("model-authored project brief must include typed blueprint sections")


def _validate_authored_project_intelligence(value: Mapping[str, Any]) -> None:
    if value.get("schema_version") != "odylith.greenfield.project_intelligence.v1":
        raise ValueError("model-authored project intelligence has an unsupported schema version")
    if value.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
        raise ValueError("model-authored project intelligence must preserve its projection origin")
    _require_text(
        value,
        "purpose",
        owner="model-authored project intelligence",
        legacy_copy_checks=False,
    )


def _validate_diagrams(diagrams: list[Any], *, model_authored: bool = False) -> None:
    slugs: set[str] = set()
    sources: list[str] = []
    for index, row in enumerate(diagrams, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"diagram row {index} must be an object")
        for key in ("slug", "title", "kind", "summary", "link_state"):
            _require_text(
                row,
                key,
                owner=f"diagram row {index}",
                legacy_copy_checks=not model_authored,
            )
        _validate_diagram_components(
            row,
            index,
            legacy_copy_checks=not model_authored,
        )
        slug = str(row.get("slug", "")).strip()
        if slug in slugs:
            raise ValueError(f"diagram slug `{slug}` appears more than once")
        slugs.add(slug)
        _validate_evidence_tier(row, owner=f"diagram row {index}")
        sources.append(_canonical_source(validated_mermaid_source(row)))
    if len(sources) > 1 and len(set(sources)) == 1:
        raise ValueError("greenfield proposal diagrams must not reuse identical Mermaid source")


def require_distinct_supplied_diagram_sources(value: object) -> None:
    """Reject explicit duplicate topology before pre-confirm rendering begins."""

    if not isinstance(value, list) or len(value) < 2:
        return
    supplied = [
        _canonical_source(str(row.get("mermaid_source", "") or row.get("source", "")))
        for row in value
        if isinstance(row, Mapping) and str(row.get("mermaid_source", "") or row.get("source", "")).strip()
    ]
    if len(supplied) == len(value) and len(set(supplied)) == 1:
        raise ValueError("greenfield proposal diagrams must not reuse identical Mermaid source")


def _validate_evidence_tier(row: Mapping[str, Any], *, owner: str) -> None:
    tier = str(row.get("evidence_tier", "")).strip()
    if tier not in _VALID_EVIDENCE_TIERS:
        raise ValueError(f"{owner} evidence_tier must be one of {sorted(_VALID_EVIDENCE_TIERS)}")


def _require_text(
    row: Mapping[str, Any],
    key: str,
    *,
    owner: str,
    min_words: int = 1,
    legacy_copy_checks: bool = True,
) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{owner} `{key}` must be non-empty")
    if legacy_copy_checks and value.casefold() in _PLACEHOLDER_TOKENS:
        raise ValueError(f"{owner} `{key}` must not be placeholder text")
    if legacy_copy_checks and word_count(value) < min_words:
        raise ValueError(f"{owner} `{key}` must contain at least {min_words} meaningful words")
    return value


def _validate_diagram_components(
    row: Mapping[str, Any],
    index: int,
    *,
    legacy_copy_checks: bool = True,
) -> None:
    components = row.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError(f"diagram row {index} must include related components")
    for component_index, component in enumerate(components, start=1):
        if not isinstance(component, Mapping):
            raise ValueError(f"diagram row {index} components[{component_index}] must be an object")
        _require_text(
            component,
            "name",
            owner=f"diagram row {index} components[{component_index}]",
            min_words=1,
            legacy_copy_checks=legacy_copy_checks,
        )
        _require_text(
            component,
            "description",
            owner=f"diagram row {index} components[{component_index}]",
            min_words=4,
            legacy_copy_checks=legacy_copy_checks,
        )


def _canonical_source(source: str) -> str:
    without_comments = [line.strip() for line in source.splitlines() if line.strip() and not line.strip().startswith("%%")]
    return re.sub(r"\s+", " ", "\n".join(without_comments)).casefold()
