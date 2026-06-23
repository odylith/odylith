"""Role-quality judgment for rendered greenfield governance artifacts.

The checks here are domain-neutral. They look for semantic composition
failures that a product manager, architect, engineer, or domain reviewer would
reject: action/object collisions, finite/base drift, noun-slot fragments, and
scope inversions.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
import re
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def greenfield_artifact_judgment_issues(package: Any) -> list[str]:
    """Return role-oriented quality failures for a rendered greenfield package."""

    issues: list[str] = []
    for identity, text in _artifact_texts(package):
        lowered = text.casefold()
        issues.extend(_product_manager_issues(identity, lowered))
        issues.extend(_architect_issues(identity, lowered))
        issues.extend(_engineer_issues(identity, lowered))
        issues.extend(_domain_reviewer_issues(identity, lowered))
    return unique_text(issues)


def _artifact_texts(package: Any) -> Iterable[tuple[str, str]]:
    backlog_result = _mapping(getattr(package, "backlog_result", None))
    for path, text in _mapping(backlog_result.get("idea_files")).items():
        yield f"Radar workstream `{path}`", normalize_string(text)
    index = normalize_string(backlog_result.get("backlog_index_text"))
    if index:
        yield "Radar index `INDEX.md`", index
    for name, text in _mapping(getattr(package, "rendered_component_specs", None)).items():
        yield f"Registry component spec `{name}`", normalize_string(text)
    for path, text in _mapping(getattr(package, "rendered_atlas_sources", None)).items():
        yield f"Atlas Mermaid `{path}`", normalize_string(text)
    for label in ("project_brief_preview", "next_steps_preview"):
        text = normalize_string(getattr(package, label, None))
        if text:
            yield f"Greenfield preview `{label}`", text


def _mapping(value: Any) -> dict[Any, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _product_manager_issues(identity: str, lowered: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"\breview\s+(?:a|an|the)\s+reviewed\s+\w+", lowered):
        issues.append(f"{identity} repeats an outcome modifier inside the user review action")
    if re.search(r"\b(?:use|reach|review|see)\s+(?:a|an|the)\s+\w+\s+(?:sees|views|receives|gets|reads)\b", lowered):
        issues.append(f"{identity} embeds a terminal user action inside the visible-result object")
    if re.search(r"\b(?:can|could|should|must|will|would)\s+\w+\s+(?:controls|turns|assigns|tracks|captures)\b", lowered):
        issues.append(f"{identity} presents internal processing as a user capability")
    return issues


def _architect_issues(identity: str, lowered: str) -> list[str]:
    issues: list[str] = []
    if _has_contract_fragment_tuple(lowered):
        issues.append(f"{identity} contains component-contract noun slots built from clipped phrase fragments")
    if _abstract_contract_noun_run(lowered) >= 3:
        issues.append(f"{identity} contains adjacent abstract contract nouns without a governing relation")
    return issues


def _engineer_issues(identity: str, lowered: str) -> list[str]:
    issues: list[str] = []
    if re.search(r"\b(?:can|could|should|must|will|would)\s+\w+\s+(?:controls|turns|assigns|tracks|captures)\b", lowered):
        issues.append(f"{identity} has modal/base-form drift in an action chain")
    if re.search(r"\b(?:controls|turns|assigns|tracks|captures)\s+[^.]{0,80}\s+with\s+success\b", lowered):
        issues.append(f"{identity} uses implementation-operation text as a success metric")
    return issues


def _domain_reviewer_issues(identity: str, lowered: str) -> list[str]:
    if re.search(r"\bnot\s+later\b", lowered) and re.search(r"\bdeferred\s+for\s+now\b|\bwaits?\s+for\b", lowered):
        return [f"{identity} turns a requirement stated as `not later` into deferred scope"]
    return []


def _has_contract_fragment_tuple(lowered: str) -> bool:
    if re.search(r"\bcovers?\s+(?!the\b|a\b|an\b)\w+\s+\w+\b", lowered):
        return True
    if re.search(r"\bgate\s+\w+\s+\w+\s+(?:result|status|state)\b", lowered):
        return True
    return False


def _abstract_contract_noun_run(lowered: str) -> int:
    abstract = {"approval", "approvals", "gate", "gates", "name", "result", "status", "story"}
    best = 0
    current = 0
    for token in re.findall(r"[a-z]+", lowered):
        if token in abstract:
            current += 1
            best = max(best, current)
            continue
        current = 0
    return best


__all__ = ["greenfield_artifact_judgment_issues"]
