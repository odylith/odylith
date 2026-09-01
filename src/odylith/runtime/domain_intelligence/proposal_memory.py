"""Durable structural memory for accepted model-authored Greenfield packages.

Pre-confirm staging copies verified typed intent into memory previews. The
commit path writes those already compiled records exactly and never rebuilds
canonical meaning from prose.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common.repo_path_resolver import display_repo_path
from odylith.runtime.domain_intelligence.greenfield_authored_memory import (
    render_authored_project_brief_lines,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    GreenfieldAuthoredSemanticsError,
    authored_projection_relations,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)

ACCEPTED_PROJECT_SOURCE_PATH = "odylith/runtime/source/accepted-project.v1.json"
PROJECT_BRIEF_SOURCE_PATH = "odylith/runtime/source/project-brief.v1.md"


def _structural_token(value: Any) -> str:
    return str(value or "").strip()


def _require_authored_relations(proposal: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    relations = authored_projection_relations(proposal)
    if not relations:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield acceptance memory requires model-authored typed intent"
        )
    return relations


def _durable_memory_row(row: Mapping[str, Any], *, repo_root: Path | None) -> dict[str, Any]:
    """Keep governed artifact links portable across staged and committed workspaces."""

    payload = dict(row)
    for key in ("idea_path", "registry_path", "spec_path"):
        if payload.get(key):
            payload[key] = (
                display_repo_path(repo_root=repo_root, value=str(payload[key]))
                if repo_root is not None
                else str(payload[key]).strip()
            )
    return payload


def _intent(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    value = proposal.get("intent")
    return value if isinstance(value, Mapping) else {}


def _authored_title(proposal: Mapping[str, Any]) -> str:
    title = _intent(proposal).get("title")
    if not isinstance(title, str) or not title.strip():
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield acceptance memory is missing its authored project title"
        )
    return title


def _release_label(*, release_selector: str, release_id: str) -> str:
    selector = _structural_token(release_selector)
    release = _structural_token(release_id)
    if selector and release:
        return f"{selector}->{release}"
    return selector or release or "none"


def _accepted_project_source_path(repo_root: Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ACCEPTED_PROJECT_SOURCE_PATH


def _project_brief_source_path(repo_root: Path) -> Path:
    return Path(repo_root).expanduser().resolve() / PROJECT_BRIEF_SOURCE_PATH


def build_greenfield_acceptance_event_preview(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    accepted_at: str = "prewrite",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Copy one verified authored package into its Compass acceptance preview."""

    _require_authored_relations(proposal)
    workstream_ids = [
        _structural_token(row.get("idea_id")).upper()
        for row in backlog_items
        if _structural_token(row.get("idea_id"))
    ]
    component_ids = [
        _structural_token(row.get("component_id"))
        for row in component_items
        if _structural_token(row.get("component_id"))
    ]
    raw_artifacts = [
        PROJECT_BRIEF_SOURCE_PATH,
        *[
            str(row.get("idea_path", ""))
            for row in backlog_items
            if _structural_token(row.get("idea_path"))
        ],
        *[
            str(row.get("spec_path", ""))
            for row in component_items
            if _structural_token(row.get("spec_path"))
        ],
    ]
    artifacts = list(
        dict.fromkeys(
            token
            for value in raw_artifacts
            if (token := _event_artifact_token(repo_root=repo_root, value=value))
        )
    )
    exact_title = _authored_title(proposal)
    return {
        "version": "v1",
        "kind": "decision",
        "summary": "Accepted the sealed model-authored Greenfield package.",
        "ts_iso": _structural_token(accepted_at) or "prewrite",
        "author": "odylith",
        "source": "domain-intelligence",
        "workstreams": workstream_ids,
        "artifacts": artifacts,
        "components": component_ids,
        "context": "projection_origin=model_authored_typed_intent; evidence_tier=user_intent",
        "headline_hint": f"Greenfield package accepted: {exact_title}",
        "evidence_tier": "user_intent",
        "work_category": "governance",
    }


def build_accepted_project_source_payload(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    validation_gate: Mapping[str, Any] | None,
    source_launch_context: Mapping[str, Any] | None = None,
    accepted_at: str = "",
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Copy verified authored intent into accepted-project memory before write."""

    _require_authored_relations(proposal)
    payload = {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "evidence_tier": "user_intent",
        "accepted_at": _structural_token(accepted_at),
        "title": _authored_title(proposal),
        "source": "greenfield_apply",
        "proposal": _accepted_memory_proposal(proposal),
        "created": {
            "workstreams": [
                _durable_memory_row(row, repo_root=repo_root) for row in backlog_items
            ],
            "components": [
                _durable_memory_row(row, repo_root=repo_root) for row in component_items
            ],
            "diagrams": [str(item) for item in diagram_ids],
            "release_selector": _structural_token(release_selector),
            "release_id": _structural_token(release_id),
        },
        "source_launch": _source_launch_payload(source_launch_context),
        "validation_gate": dict(validation_gate or {}),
    }
    return payload


def _source_launch_payload(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    allowed = (
        "project_workstream_id",
        "project_workstream_title",
        "start_workstream_id",
        "start_workstream_title",
        "release_selector",
        "implementation_prompt",
        "coding_readiness_gates",
        "validation_gates",
        "verification_commands",
        "coding_readiness_contract",
    )
    payload: dict[str, Any] = {}
    for key in allowed:
        raw = source.get(key)
        if raw is None or raw == "" or raw == [] or raw == () or raw == {}:
            continue
        payload[key] = copy.deepcopy(raw)
    return payload


def build_project_brief_source_markdown(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    accepted_at: str = "",
) -> str:
    """Build the durable human-readable project brief artifact."""

    _require_authored_relations(proposal)
    title = _authored_title(proposal)
    brief = (
        proposal.get("project_brief")
        if isinstance(proposal.get("project_brief"), Mapping)
        else {}
    )
    body_lines = render_authored_project_brief_lines(brief)
    if not body_lines:
        raise GreenfieldAuthoredSemanticsError(
            "Greenfield acceptance memory is missing its authored project brief"
        )
    lines = [
        f"# {title} Project Brief",
        "",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
        f"- accepted_at: {_structural_token(accepted_at) or 'prewrite'}",
        f"- release: {_release_label(release_selector=release_selector, release_id=release_id)}",
        f"- workstreams: {len(backlog_items)}",
        f"- components: {len(component_items)}",
        f"- diagrams: {len(diagram_ids)}",
        "",
        "## Brief",
        *body_lines,
        "",
    ]
    text = "\n".join(lines)
    return text.rstrip() + "\n"


def _accepted_memory_proposal(
    proposal: Mapping[str, Any],
) -> dict[str, Any]:
    """Return the exact authored proposal shape stored in accepted memory."""

    _require_authored_relations(proposal)
    payload = copy.deepcopy(dict(proposal))
    payload.pop(PRODUCT_INTENT_AUTHORITY_KEY, None)
    return payload


def record_compiled_greenfield_acceptance(
    *,
    repo_root: Path,
    accepted_project_preview: Mapping[str, Any],
    project_brief_record_text: str,
    compass_memory_preview: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist precompiled greenfield memory without rebuilding product truth."""

    root = Path(repo_root).expanduser().resolve()
    event_preview = _json_ready_mapping(
        compass_memory_preview,
        label="compiled Compass memory preview",
    )
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    existing_payload = _matching_exact_acceptance_event(
        stream_path=stream_path,
        event_preview=event_preview,
    )
    reused_existing = existing_payload is not None
    payload = existing_payload or _append_compiled_acceptance_event(
        stream_path=stream_path,
        event_preview=event_preview,
    )
    accepted_project_path = _write_compiled_accepted_project_source(
        repo_root=root,
        accepted_project_preview=accepted_project_preview,
    )
    project_brief_path = _write_compiled_project_brief_source(
        repo_root=root,
        project_brief_record_text=project_brief_record_text,
    )
    return {
        "recorded": True,
        "reused_existing": reused_existing,
        "stream": str(stream_path),
        "accepted_project": str(accepted_project_path),
        "project_brief": str(project_brief_path),
        "event": payload,
    }


def _write_compiled_accepted_project_source(
    *,
    repo_root: Path,
    accepted_project_preview: Mapping[str, Any],
) -> Path:
    path = _accepted_project_source_path(repo_root)
    payload = _json_ready_mapping(
        accepted_project_preview,
        label="compiled accepted-project preview",
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return path


def _write_compiled_project_brief_source(
    *,
    repo_root: Path,
    project_brief_record_text: str,
) -> Path:
    path = _project_brief_source_path(repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(project_brief_record_text or ""), encoding="utf-8")
    return path


def compiled_project_brief_record_text(text: str, *, accepted_at: str) -> str:
    return _project_brief_with_accepted_at(text, accepted_at=accepted_at)


def _project_brief_with_accepted_at(text: str, *, accepted_at: str) -> str:
    lines = str(text or "").rstrip().splitlines()
    updated: list[str] = []
    replaced = False
    for line in lines:
        if line.startswith("- accepted_at: "):
            updated.append(f"- accepted_at: {accepted_at or 'prewrite'}")
            replaced = True
        else:
            updated.append(line)
    if not replaced:
        updated.insert(0, f"- accepted_at: {accepted_at or 'prewrite'}")
    return "\n".join(updated).rstrip() + "\n"


def _matching_exact_acceptance_event(
    *,
    stream_path: Path,
    event_preview: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not stream_path.is_file():
        return None
    expected = _json_ready_mapping(event_preview, label="compiled Compass memory preview")
    for line in stream_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        actual = _json_ready_mapping(event, label="persisted Compass memory event")
        if actual == expected:
            return dict(actual)
    return None


def _append_compiled_acceptance_event(
    *,
    stream_path: Path,
    event_preview: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _json_ready_mapping(event_preview, label="compiled Compass memory preview")
    for key in ("kind", "summary", "ts_iso"):
        if not str(payload.get(key, "")).strip():
            raise ValueError(f"compiled Compass memory preview is missing {key}")
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    with stream_path.open("a", encoding="utf-8") as handle:
        handle.write(f"{json.dumps(payload, sort_keys=True)}\n")
    return dict(payload)


def _json_ready_mapping(value: Mapping[str, Any], *, label: str) -> dict[str, Any]:
    try:
        normalized = json.loads(json.dumps(dict(value or {}), sort_keys=True))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} is not JSON-serializable") from exc
    return normalized if isinstance(normalized, dict) else {}


def _event_artifact_token(*, repo_root: Path | None, value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if repo_root is None:
        return token
    return display_repo_path(repo_root=Path(repo_root), value=token)
