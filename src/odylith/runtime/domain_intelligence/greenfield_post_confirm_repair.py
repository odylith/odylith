"""Mechanical cleanup for greenfield post-confirm artifact drafts."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_draft_repair_projection
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import build_greenfield_package_report
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import CONFIRMED_DANGLING_WORDS
from odylith.runtime.domain_intelligence.greenfield_text import strip_dangling_word_tail


_DEFAULT_PACKAGE_REPAIR_PASSES = 4
_MECHANICAL_COPY_ACTION = "Apply only explicitly safe mechanical cleanup, then rerun the same typed review gates."
_SEMANTIC_PAYLOAD_FIELDS = ("replacement_fact", "decision_ledger_entry", "proof_obligation_delta")
_SCALAR_CLAUSE_SPLIT_RE = re.compile(r"([,;.!?])\s*")
_MARKDOWN_LINK_TARGET_RE = re.compile(r"\]\(([^)\s]+)\)")
_VERSION_TOKEN_RE = re.compile(r"\b\d+(?:\.\d+){1,4}\b")
_PROTECTED_INLINE_PREFIX = "__ODYLITH_INLINE_ROUTE_"
_STRUCTURAL_COPY_KEYS = frozenset(
    {
        "category",
        "component",
        "components",
        "created",
        "date",
        "diagrams",
        "href",
        "id",
        "kind",
        "origin",
        "owner",
        "path",
        "paths",
        "product_layer",
        "qualification",
        "release",
        "schema_version",
        "slug",
        "slugs",
        "source",
        "sources",
        "status",
        "uri",
        "url",
        "version",
        "workstreams",
    }
)
_STRUCTURAL_COPY_KEY_SUFFIXES = (
    "_id",
    "_ids",
    "_path",
    "_paths",
    "_slug",
    "_slugs",
    "_uri",
    "_uris",
    "_url",
    "_urls",
    "_version",
)


@dataclass(frozen=True)
class GreenfieldPackageRepairResult:
    package: GreenfieldCompletionPackage
    initial_report: GreenfieldCompletionReport
    report: GreenfieldCompletionReport
    passes: int
    changed: bool


@dataclass(frozen=True)
class _ArtifactDraftRepairOperation:
    projection: str
    target_path: str


def repair_greenfield_package_until_clean(
    package: GreenfieldCompletionPackage,
    *,
    max_passes: int = _DEFAULT_PACKAGE_REPAIR_PASSES,
) -> GreenfieldPackageRepairResult:
    """Apply only typed safe artifact-draft repairs until the report stabilizes."""

    current = package
    report = build_greenfield_package_report(current)
    initial_report = report
    changed = False
    for pass_index in range(max(0, max_passes) + 1):
        if report.passed:
            return GreenfieldPackageRepairResult(current, initial_report, report, pass_index, changed)
        if pass_index >= max_passes:
            break
        repaired = repair_greenfield_package_once(
            current,
            patchset_request=patchset_request_from_findings(report.findings).to_dict(),
        )
        if repaired == current:
            break
        changed = True
        current = repaired
        report = build_greenfield_package_report(current)
    return GreenfieldPackageRepairResult(current, initial_report, report, min(max_passes, pass_index), changed)


def repair_greenfield_package_once(
    package: GreenfieldCompletionPackage,
    *,
    patchset_request: Mapping[str, Any] | None = None,
) -> GreenfieldCompletionPackage:
    """Apply one deterministic pass only to PatchSet-authorized draft projections."""

    request = patchset_request or patchset_request_from_findings(
        build_greenfield_package_report(package).findings
    ).to_dict()
    operations = _safe_package_repair_operations(request)
    if not operations:
        return package

    updates: dict[str, Any] = {}
    for operation in operations:
        _apply_artifact_draft_repair(package, updates=updates, operation=operation)
    return replace(package, **updates) if updates else package


def _safe_package_repair_operations(patchset_request: Mapping[str, Any]) -> tuple[_ArtifactDraftRepairOperation, ...]:
    operations = patchset_request.get("operations") if isinstance(patchset_request, Mapping) else ()
    if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes, bytearray)):
        return ()
    repair_operations: list[_ArtifactDraftRepairOperation] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        if str(operation.get("target_layer", "")).strip() != "artifact_draft_set":
            continue
        if str(operation.get("issue_code", "")).strip() != "generated_copy_quality":
            continue
        if str(operation.get("operation_kind", "")).strip() != "artifact_draft_mechanical_copy":
            continue
        if str(operation.get("repair_owner", "")).strip() != "artifact_draft_cleaner":
            continue
        if str(operation.get("requested_action", "")).strip() != _MECHANICAL_COPY_ACTION:
            continue
        if any(str(operation.get(field, "")).strip() for field in _SEMANTIC_PAYLOAD_FIELDS):
            continue
        target_path = str(operation.get("target_path", "")).strip()
        if not _exact_artifact_draft_target_path(target_path):
            continue
        affected = operation.get("affected_projections")
        if not isinstance(affected, Sequence) or isinstance(affected, (str, bytes, bytearray)):
            continue
        for projection in (artifact_draft_repair_projection(item) for item in affected):
            if projection:
                repair_operations.append(_ArtifactDraftRepairOperation(projection=projection, target_path=target_path))
    return tuple(dict.fromkeys(repair_operations))


def _exact_artifact_draft_target_path(value: str) -> bool:
    if value in {
        "prewrite_package.backlog_result.backlog_index_text",
        "prewrite_package.project_brief_preview",
        "prewrite_package.next_steps_preview",
    }:
        return True
    return value.startswith(
        (
            "prewrite_package.rendered_component_specs::",
            "prewrite_package.rendered_atlas_sources::",
            "prewrite_package.backlog_result.idea_files::",
        )
    )


def _apply_artifact_draft_repair(
    package: GreenfieldCompletionPackage,
    *,
    updates: dict[str, Any],
    operation: _ArtifactDraftRepairOperation,
) -> None:
    target_path = operation.target_path
    if operation.projection == "registry" and target_path.startswith("prewrite_package.rendered_component_specs::"):
        key = target_path.split("::", 1)[1]
        current = updates.get("rendered_component_specs", package.rendered_component_specs)
        updates["rendered_component_specs"] = _repair_mapping_entry(current, key)
        return
    if operation.projection == "atlas" and target_path.startswith("prewrite_package.rendered_atlas_sources::"):
        key = target_path.split("::", 1)[1]
        current = updates.get("rendered_atlas_sources", package.rendered_atlas_sources)
        updates["rendered_atlas_sources"] = _repair_mapping_entry(current, key)
        return
    if operation.projection == "radar" and target_path.startswith("prewrite_package.backlog_result.idea_files::"):
        key = target_path.split("::", 1)[1]
        current = updates.get("backlog_result", package.backlog_result)
        updates["backlog_result"] = _repair_nested_mapping_entry(current, "idea_files", key)
        return
    if operation.projection == "radar" and target_path == "prewrite_package.backlog_result.backlog_index_text":
        current = updates.get("backlog_result", package.backlog_result)
        updates["backlog_result"] = _repair_mapping_entry(current, "backlog_index_text")
        return
    if operation.projection == "project_brief" and target_path == "prewrite_package.project_brief_preview":
        updates["project_brief_preview"] = _repair_optional_mapping(
            updates.get("project_brief_preview", package.project_brief_preview)
        )
        return
    if operation.projection == "next_steps" and target_path == "prewrite_package.next_steps_preview":
        updates["next_steps_preview"] = _repair_optional_mapping(
            updates.get("next_steps_preview", package.next_steps_preview)
        )


def _repair_mapping_entry(value: Mapping[str, Any] | None, key: str) -> Mapping[str, Any] | None:
    if value is None or key not in value:
        return value
    repaired = dict(value)
    repaired[key] = _repair_tree(value[key], key=key)
    return repaired


def _repair_nested_mapping_entry(
    value: Mapping[str, Any] | None,
    mapping_key: str,
    key: str,
) -> Mapping[str, Any] | None:
    if value is None:
        return value
    child = value.get(mapping_key)
    if not isinstance(child, Mapping) or key not in child:
        return value
    repaired = dict(value)
    child_repaired = dict(child)
    child_repaired[key] = _repair_tree(child[key], key=key)
    repaired[mapping_key] = child_repaired
    return repaired


def _repair_optional_mapping(value: Mapping[str, Any] | None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    repaired = _repair_tree(value)
    return repaired if isinstance(repaired, Mapping) else value


def _repair_tree(value: Any, *, key: str = "") -> Any:
    if isinstance(value, str):
        if _structural_copy_value(key=key, value=value):
            return value
        return _repair_public_copy(value)
    if isinstance(value, Mapping):
        return {item_key: _repair_tree(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(_repair_tree(item, key=key) for item in value)
    if isinstance(value, list):
        return [_repair_tree(item, key=key) for item in value]
    return value


def _structural_copy_value(*, key: str, value: str) -> bool:
    field = str(key or "").strip().casefold()
    if field in _STRUCTURAL_COPY_KEYS or field.endswith(_STRUCTURAL_COPY_KEY_SUFFIXES):
        return True
    text = str(value or "").strip()
    if not text:
        return False
    return bool(("://" in text or "/" in text) and not any(char.isspace() for char in text))


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
    text = str(value)
    text = re.sub(r"\b(?P<word>[A-Za-z][A-Za-z0-9'-]*)\s+(?P=word)\b", r"\g<word>", text, flags=re.IGNORECASE)
    return _repair_dangling_tail(text)


def _repair_dangling_tail(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    if not any(char.isspace() for char in text):
        return text
    if not any(char.isalpha() for char in text):
        return text
    if _looks_like_verification_command(text) or _looks_like_structured_diagram_line(text):
        return text
    return _repair_dangling_clause_tails(text)


def _looks_like_verification_command(value: str) -> bool:
    text = str(value or "").strip()
    return text.startswith(("./", "odylith ", "python ", "python3 ", "bash ", "git "))


def _looks_like_structured_diagram_line(value: str) -> bool:
    text = str(value or "").strip()
    if text.startswith(("flowchart ", "graph ", "sequenceDiagram", "stateDiagram", "classDiagram", "journey")):
        return True
    return bool(
        "-->" in text
        or "---" in text
        or "->" in text
        or re.match(r"^[A-Za-z0-9_-]+\s*(?:\[|\(|\{)", text)
        or re.match(r"^[A-Za-z0-9_-]+\\s*::", text)
    )


def _repair_dangling_clause_tails(value: str) -> str:
    text = str(value or "").strip()
    protected_text, protected_spans = _protect_structured_inline_routes(text)
    pieces = _SCALAR_CLAUSE_SPLIT_RE.split(protected_text)
    if len(pieces) <= 1:
        return _restore_structured_inline_routes(_strip_terminal_dangling_tail(protected_text), protected_spans)
    repaired: list[str] = []
    index = 0
    while index < len(pieces):
        segment = pieces[index]
        separator = pieces[index + 1] if index + 1 < len(pieces) else ""
        cleaned = _strip_terminal_dangling_tail(segment)
        if cleaned:
            repaired.append(cleaned)
            if separator:
                repaired.append(separator)
                if index + 2 < len(pieces):
                    repaired.append(" ")
        elif separator and repaired:
            repaired.append(separator)
            if index + 2 < len(pieces):
                repaired.append(" ")
        index += 2
    rendered = re.sub(r"\s+([,;.!?])", r"\1", "".join(repaired)).strip()
    return _restore_structured_inline_routes(rendered, protected_spans)


def _protect_structured_inline_routes(value: str) -> tuple[str, tuple[str, ...]]:
    spans: list[str] = []

    def replace_markdown_target(match: re.Match[str]) -> str:
        spans.append(match.group(1))
        return f"]({_PROTECTED_INLINE_PREFIX}{len(spans) - 1}__)"

    def replace_version_token(match: re.Match[str]) -> str:
        spans.append(match.group(0))
        return f"{_PROTECTED_INLINE_PREFIX}{len(spans) - 1}__"

    protected = _MARKDOWN_LINK_TARGET_RE.sub(replace_markdown_target, value)
    protected = _VERSION_TOKEN_RE.sub(replace_version_token, protected)
    return protected, tuple(spans)


def _restore_structured_inline_routes(value: str, spans: Sequence[str]) -> str:
    text = value
    for index, span in enumerate(spans):
        text = text.replace(f"{_PROTECTED_INLINE_PREFIX}{index}__", span)
    return text


def _strip_terminal_dangling_tail(value: str) -> str:
    text = str(value or "").strip()
    if not text:
        return text
    terminal = text[-1] if text[-1] in ".!?" else ""
    repaired = strip_dangling_word_tail(
        text,
        dangling_words=CONFIRMED_DANGLING_WORDS,
        rstrip_chars=" ,;:.",
    )
    if repaired and terminal and repaired[-1] not in ".!?":
        return f"{repaired}{terminal}"
    return repaired


__all__ = [
    "GreenfieldPackageRepairResult",
    "repair_greenfield_package_once",
    "repair_greenfield_package_until_clean",
]
