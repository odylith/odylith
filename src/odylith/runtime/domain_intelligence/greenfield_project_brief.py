"""Validation and rendering support for confirmed project briefs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_text_list


PROJECT_BRIEF_SCHEMA_VERSION = "odylith.greenfield.project_brief.v1"


def normalize_project_brief(
    value: Any,
    *,
    intent: Mapping[str, Any],
    release_selector: str,
) -> dict[str, Any]:
    """Normalize a proposal project brief without manufacturing content."""

    _ = intent, release_selector
    if not isinstance(value, Mapping):
        return {}

    result = dict(value)
    result.setdefault("schema_version", PROJECT_BRIEF_SCHEMA_VERSION)
    result["blueprint_sections"] = _normalize_brief_rows(
        result.get("blueprint_sections"),
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    result["customization_options"] = _normalize_brief_rows(
        result.get("customization_options") or result.get("direction_options"),
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    result["customization_prompts"] = normalize_text_list(result.get("customization_prompts"))
    result["pre_coding_checkpoints"] = _normalize_brief_rows(
        result.get("pre_coding_checkpoints") or result.get("checkpoints"),
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    result["coding_readiness_gates"] = normalize_text_list(result.get("coding_readiness_gates"))
    result["host_independent_paths"] = _normalize_brief_rows(
        result.get("host_independent_paths"),
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return result


def project_brief_issues(value: Any) -> list[str]:
    """Return validation issues for the proposal project-first brief."""

    issues: list[str] = []
    if not isinstance(value, Mapping):
        return ["proposal `project_brief` must be an object"]
    _require_text(value, "purpose", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_text(value, "operating_principle", owner="proposal `project_brief`", issues=issues, min_words=12)
    _require_text(value, "project_outcome", owner="proposal `project_brief`", issues=issues, min_words=10)
    _require_rows(
        value.get("blueprint_sections"),
        owner="proposal `project_brief.blueprint_sections`",
        issues=issues,
        min_rows=4,
        required_keys=("section", "must_capture", "why_it_matters"),
    )
    _require_rows(
        value.get("customization_options"),
        owner="proposal `project_brief.customization_options`",
        issues=issues,
        min_rows=5,
        required_keys=("id", "decision", "recommended", "choices", "impact"),
    )
    _require_rows(
        value.get("pre_coding_checkpoints"),
        owner="proposal `project_brief.pre_coding_checkpoints`",
        issues=issues,
        min_rows=4,
        required_keys=("checkpoint", "operator_question", "done_when"),
    )
    prompts = normalize_text_list(value.get("customization_prompts"))
    if len(prompts) < 3:
        issues.append("proposal `project_brief.customization_prompts` must include at least three host-independent examples")
    elif any(_word_count(prompt) < 6 for prompt in prompts):
        issues.append("proposal `project_brief.customization_prompts` contains a shallow example")
    gates = normalize_text_list(value.get("coding_readiness_gates"))
    if len(gates) < 4:
        issues.append("proposal `project_brief.coding_readiness_gates` must include at least four gates")
    elif any(_word_count(gate) < 6 for gate in gates):
        issues.append("proposal `project_brief.coding_readiness_gates` contains a shallow gate")
    _require_rows(
        value.get("host_independent_paths"),
        owner="proposal `project_brief.host_independent_paths`",
        issues=issues,
        min_rows=3,
        required_keys=("path", "command", "works_in", "use_when"),
    )
    return issues


def render_project_brief_lines(project_brief: Mapping[str, Any]) -> list[str]:
    """Render the project-first brief used in proposal review text."""

    if not project_brief:
        return []
    lines: list[str] = []
    principle = clean_text(project_brief.get("operating_principle"))
    outcome = clean_text(project_brief.get("project_outcome"))
    posture = clean_text(project_brief.get("review_posture"))
    if outcome:
        lines.append(f"- outcome: {outcome}")
    if principle:
        lines.append(f"- principle: {principle}")
    if posture:
        lines.append(f"- review posture: {posture}")
    blueprint_lines = _blueprint_section_lines(project_brief.get("blueprint_sections"))
    if blueprint_lines:
        lines.extend(["- project design board:"])
        lines.extend(f"  - {line}" for line in blueprint_lines[:7])
    option_lines = _project_option_lines(project_brief.get("customization_options"))
    if option_lines:
        lines.extend(["- choose before coding:"])
        lines.extend(f"  - {line}" for line in option_lines[:8])
    prompt_lines = _text_list_lines(project_brief.get("customization_prompts"))
    if prompt_lines:
        lines.extend(["- customize by saying:"])
        lines.extend(f"  - {line}" for line in prompt_lines[:4])
    checkpoint_lines = _project_checkpoint_lines(project_brief.get("pre_coding_checkpoints"))
    if checkpoint_lines:
        lines.extend(["- checkpoints:"])
        lines.extend(f"  - {line}" for line in checkpoint_lines[:5])
    gates = _text_list_lines(project_brief.get("coding_readiness_gates"))
    if gates:
        lines.extend(["- coding readiness gates:"])
        lines.extend(f"  - {gate}" for gate in gates[:5])
    paths = _project_path_lines(project_brief.get("host_independent_paths"))
    if paths:
        lines.extend(["- host-independent customization paths:"])
        lines.extend(f"  - {line}" for line in paths[:3])
    return lines


def _normalize_brief_rows(value: Any, *, required_keys: Sequence[str]) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    rows: list[dict[str, Any]] = []
    for raw in value:
        if not isinstance(raw, Mapping):
            continue
        row = dict(raw)
        if any(_has_text_or_list(row.get(key)) for key in required_keys):
            rows.append(row)
    return rows


def _has_text_or_list(value: Any) -> bool:
    if isinstance(value, list):
        return any(clean_text(item) for item in value)
    return bool(clean_text(value))


def _require_rows(
    value: Any,
    *,
    owner: str,
    issues: list[str],
    min_rows: int,
    required_keys: Sequence[str],
) -> None:
    if not isinstance(value, list) or len(value) < min_rows:
        issues.append(f"{owner} must include at least {min_rows} rows")
        return
    for index, raw in enumerate(value, start=1):
        if not isinstance(raw, Mapping):
            issues.append(f"{owner}[{index}] must be an object")
            continue
        for key in required_keys:
            if not _has_text_or_list(raw.get(key)):
                issues.append(f"{owner}[{index}] `{key}` must be non-empty")


def _require_text(value: Mapping[str, Any], key: str, *, owner: str, issues: list[str], min_words: int) -> None:
    text = clean_text(value.get(key))
    if not text:
        issues.append(f"{owner} `{key}` must be non-empty")
        return
    if _word_count(text) < min_words:
        issues.append(f"{owner} `{key}` must contain at least {min_words} meaningful words")


def _word_count(value: str) -> int:
    return len([part for part in clean_text(value).replace("/", " ").split() if part.strip()])


def _blueprint_section_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        section = clean_text(row.get("section"))
        must_capture = clean_text(row.get("must_capture"))
        why = clean_text(row.get("why_it_matters"))
        if section and must_capture:
            suffix = f" Why: {why}" if why else ""
            lines.append(f"{section}: {must_capture}{suffix}")
    return lines


def _project_option_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        decision = clean_text(row.get("decision"))
        recommended = clean_text(row.get("recommended"))
        choices = row.get("choices", [])
        rendered_choices = (
            ", ".join(clean_text(item) for item in choices if clean_text(item))
            if isinstance(choices, list)
            else clean_text(choices)
        )
        impact = clean_text(row.get("impact"))
        if decision and recommended:
            suffix = f" Choices: {rendered_choices}." if rendered_choices else ""
            impact_text = f" Impact: {impact}" if impact else ""
            lines.append(f"{decision}: {recommended}{suffix}{impact_text}")
    return lines


def _text_list_lines(value: Any) -> list[str]:
    return [clean_text(item) for item in value if clean_text(item)] if isinstance(value, list) else []


def _project_checkpoint_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        checkpoint = clean_text(row.get("checkpoint"))
        question = clean_text(row.get("operator_question"))
        done_when = clean_text(row.get("done_when"))
        if checkpoint and question:
            lines.append(f"{checkpoint}: {question} Done when: {done_when}")
    return lines


def _project_path_lines(value: Any) -> list[str]:
    lines: list[str] = []
    for row in mapping_rows(value):
        path = clean_text(row.get("path"))
        command = clean_text(row.get("command"))
        works_in = clean_text(row.get("works_in"))
        if path and command:
            lines.append(f"{path}: `{command}` ({works_in})")
    return lines


__all__ = [
    "PROJECT_BRIEF_SCHEMA_VERSION",
    "normalize_project_brief",
    "project_brief_issues",
    "render_project_brief_lines",
]
