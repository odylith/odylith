"""Validation and rendering support for confirmed project briefs."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

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


__all__ = [
    "PROJECT_BRIEF_SCHEMA_VERSION",
    "normalize_project_brief",
    "project_brief_issues",
]
