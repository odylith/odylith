"""Fixpoint repair for rendered greenfield post-confirm packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_text import normalize_cover_article_language
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


_DEFAULT_PACKAGE_REPAIR_PASSES = 4
_FINITE_TO_BASE = {
    "adds": "add",
    "captures": "capture",
    "chooses": "choose",
    "creates": "create",
    "enters": "enter",
    "logs": "log",
    "marks": "mark",
    "notes": "note",
    "opens": "open",
    "records": "record",
    "reviews": "review",
    "saves": "save",
    "selects": "select",
    "submits": "submit",
    "updates": "update",
}
_BASE_ACTIONS = "|".join(re.escape(value) for value in sorted(set(_FINITE_TO_BASE.values()), key=len, reverse=True))
_FINITE_ACTIONS = "|".join(re.escape(value) for value in sorted(_FINITE_TO_BASE, key=len, reverse=True))


@dataclass(frozen=True)
class GreenfieldPackageRepairResult:
    package: GreenfieldCompletionPackage
    initial_report: GreenfieldCompletionReport
    report: GreenfieldCompletionReport
    passes: int
    changed: bool


def repair_greenfield_package_until_clean(
    package: GreenfieldCompletionPackage,
    *,
    max_passes: int = _DEFAULT_PACKAGE_REPAIR_PASSES,
) -> GreenfieldPackageRepairResult:
    """Repair fixable rendered-package defects until the report reaches a stable state."""

    current = package
    report = build_greenfield_package_report(current)
    initial_report = report
    changed = False
    for pass_index in range(max(0, max_passes) + 1):
        if report.passed:
            return GreenfieldPackageRepairResult(current, initial_report, report, pass_index, changed)
        if pass_index >= max_passes:
            break
        repaired = repair_greenfield_package_once(current)
        if repaired == current:
            break
        changed = True
        current = repaired
        report = build_greenfield_package_report(current)
    return GreenfieldPackageRepairResult(current, initial_report, report, min(max_passes, pass_index), changed)


def repair_greenfield_package_once(package: GreenfieldCompletionPackage) -> GreenfieldCompletionPackage:
    """Apply one deterministic repair pass to human-visible rendered package surfaces."""

    return replace(
        package,
        rendered_component_specs=_repair_optional_mapping(package.rendered_component_specs),
        rendered_atlas_sources=_repair_optional_mapping(package.rendered_atlas_sources),
        component_registry_preview=tuple(_repair_tree(row) for row in package.component_registry_preview),
        project_brief_preview=_repair_optional_mapping(package.project_brief_preview),
        accepted_project_preview=_repair_optional_mapping(package.accepted_project_preview),
        compass_memory_preview=_repair_optional_mapping(package.compass_memory_preview),
        next_steps_preview=_repair_optional_mapping(package.next_steps_preview),
        backlog_result=_repair_optional_mapping(package.backlog_result),
        program_result=_repair_optional_mapping(package.program_result),
        release_target_result=_repair_optional_mapping(package.release_target_result),
        release_assignment_result=_repair_optional_mapping(package.release_assignment_result),
    )


def _repair_optional_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    repaired = _repair_tree(value)
    return repaired if isinstance(repaired, Mapping) else value


def _repair_tree(value: Any) -> Any:
    if isinstance(value, str):
        return _repair_public_copy(value)
    if isinstance(value, Mapping):
        return {key: _repair_tree(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_repair_tree(item) for item in value)
    if isinstance(value, list):
        return [_repair_tree(item) for item in value]
    return value


def _repair_public_copy(value: str) -> str:
    text = str(value)
    if "\n" in text or "\r" in text:
        return "".join(_repair_public_copy_line(line) for line in text.splitlines(keepends=True))
    return _repair_public_copy_line(text)


def _repair_public_copy_line(value: str) -> str:
    newline = ""
    text = value
    if text.endswith("\r\n"):
        text = text[:-2]
        newline = "\r\n"
    elif text.endswith("\n") or text.endswith("\r"):
        newline = text[-1]
        text = text[:-1]
    leading = re.match(r"^[^\S\r\n]*", text).group(0)
    body = text[len(leading) :]
    if not body:
        return f"{leading}{newline}"
    text = f"{leading}{_repair_public_copy_scalar(body)}"
    return f"{text}{newline}"


def _repair_public_copy_scalar(value: str) -> str:
    text = normalize_visible_result_language(str(value))
    text = normalize_cover_article_language(text)
    text = re.sub(r"\b(?P<word>[A-Za-z][A-Za-z0-9'-]*)\s+(?P=word)\b", r"\g<word>", text, flags=re.IGNORECASE)
    text = _repair_responsibility_verb_pairs(text)
    text = re.sub(
        rf"\b(?P<modifier>[a-z]+ly)\s+(?P<verb>{_FINITE_ACTIONS})\b"
        rf"(?P<body>[^.!?;]{{0,160}}\b(?:and|or)\s+(?:{_BASE_ACTIONS})\b)",
        lambda match: f"{match.group('modifier')} {_FINITE_TO_BASE[match.group('verb').casefold()]}{match.group('body')}",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        rf"\b(?P<context>can|could|may|might|must|shall|should|to|will|would)\s+(?P<verb>{_FINITE_ACTIONS})\b",
        lambda match: f"{match.group('context')} {_FINITE_TO_BASE[match.group('verb').casefold()]}",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _repair_responsibility_verb_pairs(value: str) -> str:
    text = value
    text = re.sub(
        r"\b(?P<head>owns?)\s+(?:continues?|keeps?|maintains?|sustains?)\b\s*",
        lambda match: f"{match.group('head')} ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?P<head>maintains?)\s+(?:continues?|defines?|keeps?|maintains?|sustains?)\b\s*",
        lambda match: f"{match.group('head')} ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?P<head>preserves?)\s+handles?\b\s*",
        lambda match: f"{match.group('head')} ",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"[^\S\r\n]{2,}", " ", text)


__all__ = [
    "GreenfieldPackageRepairResult",
    "repair_greenfield_package_once",
    "repair_greenfield_package_until_clean",
]
