"""Validation for host-reasoned greenfield governance proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any


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
    """Return a checked host-authored Mermaid source string for one diagram."""

    raw = str(diagram.get("mermaid_source", "") or diagram.get("source", "")).strip()
    slug = str(diagram.get("slug", "<unknown>")).strip() or "<unknown>"
    if not raw:
        raise ValueError(f"diagram `{slug}` is missing host-authored mermaid_source")
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

    mode = str(proposal.get("mode", "")).strip()
    if mode not in _VALID_PROPOSAL_MODES:
        raise ValueError("greenfield apply requires a host-reasoned proposal, not a reasoning request or catalog output")
    _require_mapping(proposal, "intent")
    _require_mapping(proposal, "observed_source")
    _require_nonempty_sequence(proposal, "assumptions")
    _require_nonempty_sequence(proposal, "open_questions")
    _require_nonempty_sequence(proposal, "risks")
    _require_nonempty_sequence(proposal, "validation_strategy")
    program = _require_mapping(proposal, "program")
    _validate_program(program)
    _require_mapping(proposal, "release_plan")
    backlog = _require_nonempty_sequence(proposal, "backlog")
    components = _require_nonempty_sequence(proposal, "components")
    diagrams = _require_nonempty_sequence(proposal, "diagrams")
    for index, row in enumerate(backlog, start=1):
        _validate_backlog_row(row, index)
    for index, row in enumerate(components, start=1):
        _validate_component_row(row, index)
    _validate_diagrams(diagrams)


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
            f"diagram `{slug}` flowchart mermaid_source must define subtle classDef/style colors"
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


def _validate_backlog_row(row: Any, index: int) -> None:
    if not isinstance(row, Mapping):
        raise ValueError(f"backlog row {index} must be an object")
    for key in ("title", "problem", "customer", "opportunity", "product_view", "recommended_first_slice"):
        min_words = 2 if key == "title" else 1 if key == "customer" else 6
        _require_text(row, key, owner=f"backlog row {index}", min_words=min_words)
    metrics = [str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()]
    if len(metrics) < 2:
        raise ValueError(f"backlog row {index} must include at least two success_metrics")
    for metric_index, metric in enumerate(metrics, start=1):
        if _meaningful_word_count(metric) < 4:
            raise ValueError(f"backlog row {index} success_metrics[{metric_index}] is too shallow")
    _validate_evidence_tier(row, owner=f"backlog row {index}")


def _validate_program(program: Mapping[str, Any]) -> None:
    waves = program.get("waves")
    if not isinstance(waves, list) or not waves:
        raise ValueError("proposal `program.waves` must be a non-empty list")
    for index, row in enumerate(waves, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"program wave {index} must be an object")
        if not any(str(row.get(key, "")).strip() for key in ("label", "name", "wave_id", "wave")):
            raise ValueError(f"program wave {index} must include a label or wave id")
        if not any(str(row.get(key, "")).strip() for key in ("goal", "summary", "validation", "validation_gate", "exit_gate")):
            raise ValueError(f"program wave {index} must include a goal, summary, or validation gate")


def _validate_component_row(row: Any, index: int) -> None:
    if not isinstance(row, Mapping):
        raise ValueError(f"component row {index} must be an object")
    for key in ("component_id", "label", "kind", "intended_path", "responsibility", "status", "qualification"):
        _require_text(row, key, owner=f"component row {index}", min_words=6 if key == "responsibility" else 1)
    _validate_evidence_tier(row, owner=f"component row {index}")


def _validate_diagrams(diagrams: list[Any]) -> None:
    slugs: set[str] = set()
    sources: list[str] = []
    for index, row in enumerate(diagrams, start=1):
        if not isinstance(row, Mapping):
            raise ValueError(f"diagram row {index} must be an object")
        for key in ("slug", "title", "kind", "summary", "link_state"):
            _require_text(row, key, owner=f"diagram row {index}")
        _validate_diagram_components(row, index)
        slug = str(row.get("slug", "")).strip()
        if slug in slugs:
            raise ValueError(f"diagram slug `{slug}` appears more than once")
        slugs.add(slug)
        _validate_evidence_tier(row, owner=f"diagram row {index}")
        sources.append(_canonical_source(validated_mermaid_source(row)))
    if len(sources) > 1 and len(set(sources)) == 1:
        raise ValueError("greenfield proposal diagrams must not reuse identical Mermaid source")


def _validate_evidence_tier(row: Mapping[str, Any], *, owner: str) -> None:
    tier = str(row.get("evidence_tier", "")).strip()
    if tier not in _VALID_EVIDENCE_TIERS:
        raise ValueError(f"{owner} evidence_tier must be one of {sorted(_VALID_EVIDENCE_TIERS)}")


def _require_text(row: Mapping[str, Any], key: str, *, owner: str, min_words: int = 1) -> str:
    value = str(row.get(key, "")).strip()
    if not value:
        raise ValueError(f"{owner} `{key}` must be non-empty")
    if value.casefold() in _PLACEHOLDER_TOKENS:
        raise ValueError(f"{owner} `{key}` must not be placeholder text")
    if _meaningful_word_count(value) < min_words:
        raise ValueError(f"{owner} `{key}` must contain at least {min_words} meaningful words")
    return value


def _validate_diagram_components(row: Mapping[str, Any], index: int) -> None:
    components = row.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError(f"diagram row {index} must include related components")
    for component_index, component in enumerate(components, start=1):
        if not isinstance(component, Mapping):
            raise ValueError(f"diagram row {index} components[{component_index}] must be an object")
        _require_text(component, "name", owner=f"diagram row {index} components[{component_index}]", min_words=1)
        _require_text(component, "description", owner=f"diagram row {index} components[{component_index}]", min_words=4)


def _meaningful_word_count(value: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", str(value or "")))


def _canonical_source(source: str) -> str:
    without_comments = [line.strip() for line in source.splitlines() if line.strip() and not line.strip().startswith("%%")]
    return re.sub(r"\s+", " ", "\n".join(without_comments)).casefold()
