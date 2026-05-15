"""Validation for host-reasoned greenfield governance proposals."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_project_brief import project_brief_issues
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import project_intelligence_issues
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import domain_intelligence_issues
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
    capture(lambda: _require_nonempty_sequence(proposal, "assumptions"))
    capture(lambda: _require_nonempty_sequence(proposal, "open_questions"))
    risks = capture(lambda: _require_nonempty_sequence(proposal, "risks"))
    if isinstance(risks, list):
        issues.extend(_risk_quality_issues(risks))
    capture(lambda: _require_nonempty_sequence(proposal, "validation_strategy"))
    project_brief = capture(lambda: _require_mapping(proposal, "project_brief"))
    if isinstance(project_brief, Mapping):
        for issue in project_brief_issues(project_brief):
            issues.append(issue)
    project_intelligence = capture(lambda: _require_mapping(proposal, "project_intelligence"))
    if isinstance(project_intelligence, Mapping):
        for issue in project_intelligence_issues(project_intelligence):
            issues.append(issue)
    issues.extend(greenfield_quality_issues(proposal))
    program = capture(lambda: _require_mapping(proposal, "program"))
    if isinstance(program, Mapping):
        capture(lambda: _validate_program(program))
    capture(lambda: _require_mapping(proposal, "release_plan"))
    backlog = capture(lambda: _require_nonempty_sequence(proposal, "backlog"))
    components = capture(lambda: _require_nonempty_sequence(proposal, "components"))
    diagrams = capture(lambda: _require_nonempty_sequence(proposal, "diagrams"))
    if isinstance(backlog, list):
        issues.extend(_backlog_program_parent_issues(backlog, proposal))
        for index, row in enumerate(backlog, start=1):
            capture(lambda row=row, index=index: _validate_backlog_row(row, index))
    if isinstance(components, list):
        for index, row in enumerate(components, start=1):
            capture(lambda row=row, index=index: _validate_component_row(row, index))
    if isinstance(diagrams, list):
        capture(lambda: _validate_diagrams(diagrams))
    issues.extend(project_intelligence_binding_issues(proposal))
    return _dedupe_issues(issues)


def format_proposal_issue_report(label: str, issues: list[str] | tuple[str, ...]) -> str:
    rows = _dedupe_issues(issues)
    bullets = "\n".join(f"- {issue}" for issue in rows)
    return (
        f"greenfield proposal {label} failed with {len(rows)} issue(s):\n"
        f"{bullets}\n"
        "Remediation:\n"
        "- auto-enrichment: Odylith already normalized aliases, list-shaped fields, safe dependency/interface defaults, "
        "and default release fields before this check.\n"
        "- needs operator/proposal input: every issue above still needs richer project-specific content before governed writes."
    )


def _dedupe_issues(issues: list[str] | tuple[str, ...]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for issue in issues:
        token = str(issue or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        result.append(token)
    return result


def _risk_quality_issues(risks: list[Any]) -> list[str]:
    boilerplate = (
        "Starting implementation without a named product spine",
        "Security, privacy, accessibility, and operational risks can be under-modeled in broad greenfield prompts",
    )
    issues: list[str] = []
    for index, row in enumerate(risks, start=1):
        text = _risk_text(row)
        if any(phrase in text for phrase in boilerplate):
            issues.append(
                f"proposal risks[{index}] uses generic greenfield boilerplate instead of project-specific risk"
            )
    return issues


def _risk_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return " ".join(str(nested or "") for nested in value.values())
    return str(value or "")


def _backlog_program_parent_issues(backlog: list[Any], proposal: Mapping[str, Any]) -> list[str]:
    mapping_rows = [row for row in backlog if isinstance(row, Mapping)]
    program = proposal.get("program", {}) if isinstance(proposal.get("program"), Mapping) else {}
    waves = [row for row in program.get("waves", []) if isinstance(row, Mapping)] if isinstance(program.get("waves"), list) else []
    if len(mapping_rows) < 2 or not waves:
        return []
    first = mapping_rows[0]
    row_type = str(first.get("workstream_type", "")).strip().casefold()
    if row_type in {"umbrella", "program", "parent", "program_parent"}:
        return []
    return [
        "proposal backlog must include a proposal-authored program parent as the first row; "
        "Odylith will not synthesize an umbrella workstream from child rows"
    ]


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


def _validate_backlog_row(row: Any, index: int) -> None:
    if not isinstance(row, Mapping):
        raise ValueError(f"backlog row {index} must be an object")
    for key in ("title", "problem", "customer", "opportunity", "product_view", "recommended_first_slice"):
        min_words = 2 if key == "title" else 1 if key == "customer" else 6
        _require_text(row, key, owner=f"backlog row {index}", min_words=min_words)
    _validate_rationale_lines(row, index)
    metrics = [str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()]
    if len(metrics) < 2:
        raise ValueError(f"backlog row {index} must include at least two success_metrics")
    for metric_index, metric in enumerate(metrics, start=1):
        if _meaningful_word_count(metric) < 4:
            raise ValueError(f"backlog row {index} success_metrics[{metric_index}] is too shallow")
    intelligence_issues = domain_intelligence_issues(row.get("domain_intelligence"), owner=f"backlog row {index}")
    if intelligence_issues:
        raise ValueError("; ".join(intelligence_issues))
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
        if _meaningful_word_count(line) < 7:
            raise ValueError(f"backlog row {index} rationale_lines[{line_index}] is too shallow")


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
