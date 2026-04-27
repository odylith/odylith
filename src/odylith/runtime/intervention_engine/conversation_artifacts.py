"""Artifact resolution for Odylith conversation closeouts."""

from __future__ import annotations

from pathlib import Path
import re
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.governance import agent_governance_intelligence as governance
from odylith.runtime.intervention_engine import conversation_common
from odylith.runtime.surfaces import dashboard_shell_links


_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")
_BUG_ID_RE = re.compile(r"^CB-\d{3,}$")
_DIAGRAM_ID_RE = re.compile(r"^D-\d{3,}$")
_COMPONENT_SPEC_RE = re.compile(
    r"^odylith/registry/source/components/(?P<component>[A-Za-z0-9._-]+)/CURRENT_SPEC\.md$"
)
_RADAR_IDEA_PREFIX = "odylith/radar/source/ideas/"
_PLAN_PREFIX = "odylith/technical-plans/"
_BUG_PREFIX = "odylith/casebook/bugs/"
_ATLAS_PREFIX = "odylith/atlas/source/"
_RECURSIVE_PATH_KEYS = (
    "idea_file",
    "promoted_to_plan",
    "plan_path",
    "path",
    "source_path",
    "relative_path",
    "spec_ref",
    "bug_path",
    "diagram_path",
)


def is_workstream_id(value: str) -> bool:
    return bool(_WORKSTREAM_ID_RE.match(_normalize_string(value)))


def is_bug_id(value: str) -> bool:
    return bool(_BUG_ID_RE.match(_normalize_string(value)))


def is_diagram_id(value: str) -> bool:
    return bool(_DIAGRAM_ID_RE.match(_normalize_string(value)))


def artifact_kind(entity_id: str) -> str:
    if is_workstream_id(entity_id):
        return "workstream"
    if is_bug_id(entity_id):
        return "bug"
    if is_diagram_id(entity_id):
        return "diagram"
    return "component"


def artifact_href(kind: str, entity_id: str) -> str:
    if kind == "workstream":
        return dashboard_shell_links.shell_href(tab="radar", workstream=entity_id)
    if kind == "bug":
        return dashboard_shell_links.shell_href(tab="casebook", bug=entity_id)
    if kind == "diagram":
        return dashboard_shell_links.shell_href(tab="atlas", diagram=entity_id)
    return dashboard_shell_links.shell_href(tab="registry", component=entity_id)


def artifact_ref(kind: str, entity_id: str, *, source_paths: Sequence[str] = ()) -> dict[str, Any]:
    href = artifact_href(kind, entity_id)
    return {
        "kind": kind,
        "id": entity_id,
        "href": href,
        "markdown_ref": f"[{entity_id}]({href})" if href else entity_id,
        "plain_ref": entity_id,
        "source_paths": conversation_common.dedupe_strings(source_paths),
    }


def normalize_repo_paths(*, repo_root: Path | None, values: Sequence[str]) -> list[str]:
    if repo_root is not None:
        return governance.normalize_changed_paths(repo_root=repo_root, values=values)
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _normalize_string(raw).lstrip("./")
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def path_matches(path_ref: str, candidate: str) -> bool:
    path_token = _normalize_string(path_ref).lstrip("./")
    candidate_token = _normalize_string(candidate).lstrip("./")
    if not path_token or not candidate_token:
        return False
    return (
        path_token == candidate_token
        or path_token.endswith(candidate_token)
        or candidate_token.endswith(path_token)
    )


def context_artifact_rows(*, repo_root: Path | None, value: Any) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    def walk(node: Any) -> None:
        if isinstance(node, Mapping):
            workstream_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("idea_id", "workstream_id", "entity_id", "selected_id")
                    if is_workstream_id(_normalize_string(node.get(key)))
                ),
                "",
            )
            if workstream_id:
                paths = normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(artifact_ref("workstream", workstream_id, source_paths=paths))

            bug_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("bug_key", "bug_id", "entity_id")
                    if is_bug_id(_normalize_string(node.get(key)))
                ),
                "",
            )
            if bug_id:
                paths = normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(artifact_ref("bug", bug_id, source_paths=paths))

            diagram_id = next(
                (
                    _normalize_string(node.get(key))
                    for key in ("diagram_id", "entity_id", "selected_id")
                    if is_diagram_id(_normalize_string(node.get(key)))
                ),
                "",
            )
            if diagram_id:
                paths = normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(artifact_ref("diagram", diagram_id, source_paths=paths))

            component_id = _normalize_string(node.get("component_id"))
            if component_id:
                paths = normalize_repo_paths(
                    repo_root=repo_root,
                    values=[_normalize_string(node.get(key)) for key in _RECURSIVE_PATH_KEYS],
                )
                rows.append(artifact_ref("component", component_id, source_paths=paths))

            for nested in node.values():
                walk(nested)
            return
        if isinstance(node, Sequence) and not isinstance(node, (str, bytes, bytearray)):
            for nested in node:
                walk(nested)

    walk(value)
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(row)
    return deduped


def proof_ref_artifact(row: Mapping[str, Any]) -> dict[str, Any] | None:
    kind = _normalize_token(row.get("kind"))
    value = _normalize_string(row.get("value"))
    if kind == "workstream" and is_workstream_id(value):
        return artifact_ref("workstream", value)
    if kind == "diagram" and is_diagram_id(value):
        return artifact_ref("diagram", value)
    if kind in {"component", "bug"}:
        token = value.split(":", 1)[-1] if ":" in value else value
        if kind == "component" and token:
            return artifact_ref("component", token)
        if kind == "bug" and is_bug_id(token):
            return artifact_ref("bug", token)
    return None


def request_anchor_artifacts(
    *,
    request: Any,
    repo_root: Path | None,
    context_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    rows.extend(
        artifact_ref("workstream", entity_id)
        for entity_id in conversation_common.dedupe_strings(
            [
                _normalize_string(token)
                for token in conversation_common.field(request, "workstreams") or []
                if is_workstream_id(_normalize_string(token))
            ]
        )
    )
    rows.extend(
        artifact_ref("component", entity_id)
        for entity_id in conversation_common.dedupe_strings(
            [
                _normalize_string(token)
                for token in conversation_common.field(request, "components") or []
                if _normalize_string(token)
            ]
        )
    )
    seen = {(row["kind"], row["id"]) for row in rows}
    for row in context_rows:
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            continue
        if key[0] not in {"workstream", "component", "diagram", "bug"}:
            continue
        rows.append(dict(row))
        seen.add(key)
    return rows[:4]


def resolve_updated_artifacts(
    *,
    repo_root: Path | None,
    request: Any,
    final_changed_paths: Sequence[str],
    context_rows: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    normalized_paths = normalize_repo_paths(repo_root=repo_root, values=final_changed_paths)
    context_rows = list(context_rows) if context_rows is not None else context_artifact_rows(
        repo_root=repo_root,
        value=conversation_common.request_context_payload(request),
    )
    request_workstreams = [
        _normalize_string(token)
        for token in conversation_common.field(request, "workstreams") or []
        if is_workstream_id(_normalize_string(token))
    ]
    request_components = [
        _normalize_string(token)
        for token in conversation_common.field(request, "components") or []
        if _normalize_string(token)
    ]
    request_diagrams = [row["id"] for row in context_rows if row["kind"] == "diagram"]
    request_bugs = [row["id"] for row in context_rows if row["kind"] == "bug"]
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()

    def add(row: dict[str, Any] | None) -> None:
        if not row:
            return
        key = (str(row.get("kind")), str(row.get("id")))
        if key in seen:
            return
        seen.add(key)
        rows.append(row)

    for path_ref in normalized_paths:
        component_match = _COMPONENT_SPEC_RE.match(path_ref)
        if component_match:
            add(artifact_ref("component", component_match.group("component"), source_paths=[path_ref]))
            continue
        if path_ref.startswith((_RADAR_IDEA_PREFIX, _PLAN_PREFIX)):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "workstream"
                    and any(path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = conversation_common.dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_workstreams) == 1:
                add(artifact_ref("workstream", request_workstreams[0], source_paths=[path_ref]))
            continue
        if path_ref.startswith(_BUG_PREFIX):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "bug"
                    and any(path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = conversation_common.dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_bugs) == 1:
                add(artifact_ref("bug", request_bugs[0], source_paths=[path_ref]))
            continue
        if path_ref.startswith(_ATLAS_PREFIX):
            exact = next(
                (
                    dict(row)
                    for row in context_rows
                    if row.get("kind") == "diagram"
                    and any(path_matches(path_ref, candidate) for candidate in row.get("source_paths", []))
                ),
                None,
            )
            if exact is not None:
                exact["source_paths"] = conversation_common.dedupe_strings([*exact.get("source_paths", []), path_ref])
                add(exact)
                continue
            if len(request_diagrams) == 1:
                add(artifact_ref("diagram", request_diagrams[0], source_paths=[path_ref]))
            continue
        if path_ref == "odylith/registry/source/component_registry.v1.json" and len(request_components) == 1:
            add(artifact_ref("component", request_components[0], source_paths=[path_ref]))

    return rows[:4]


def artifact_phrase(rows: Sequence[Mapping[str, Any]]) -> tuple[str, str]:
    if not rows:
        return "", ""
    markdown = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in rows])
    plain = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in rows])
    return f"updating {markdown}", f"updating {plain}"


def affected_contract_rows(
    *,
    updated_artifacts: Sequence[Mapping[str, Any]],
    request: Any,
    repo_root: Path | None,
    context_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    allowed_kinds = {"workstream", "component", "diagram", "bug"}

    def add(row: Mapping[str, Any]) -> None:
        kind = _normalize_token(row.get("kind"))
        entity_id = _normalize_string(row.get("id"))
        if kind not in allowed_kinds or not entity_id:
            return
        key = (kind, entity_id)
        if key in seen:
            return
        seen.add(key)
        rows.append(dict(row))

    for row in updated_artifacts:
        if isinstance(row, Mapping):
            add(row)
    for row in request_anchor_artifacts(
        request=request,
        repo_root=repo_root,
        context_rows=context_rows,
    ):
        add(row)
    return rows[:4]


def affected_contract_phrase(rows: Sequence[Mapping[str, Any]], *, verb: str) -> tuple[str, str]:
    if not rows:
        return "", ""
    markdown = conversation_common.join_items([str(row.get("markdown_ref", "")).strip() for row in rows])
    plain = conversation_common.join_items([str(row.get("plain_ref", "")).strip() for row in rows])
    return f"{verb} affected governance contracts {markdown}", f"{verb} affected governance contracts {plain}"
