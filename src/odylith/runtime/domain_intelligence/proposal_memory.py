"""Durable memory records for accepted greenfield proposals.

Greenfield proposal application is confirmation gated. Once an operator accepts
a host-reasoned proposal, the project shape must stop being one chat response
and become durable acceptance evidence that later context and memory paths can
retrieve without re-asking the same scope questions.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import display_text
from odylith.runtime.common import log_compass_timeline_event
from odylith.runtime.common.value_coercion import dedupe_strings
from odylith.runtime.domain_intelligence import greenfield_source_casing
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import normalize_first_path
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import base_adverbial_note_action
from odylith.runtime.domain_intelligence.greenfield_project_brief import render_project_brief_lines
from odylith.runtime.domain_intelligence.greenfield_structural_copy import structural_copy_value
from odylith.runtime.domain_intelligence.greenfield_text import normalize_terminal_punctuation

ACCEPTED_PROJECT_SOURCE_PATH = "odylith/runtime/source/accepted-project.v1.json"
PROJECT_BRIEF_SOURCE_PATH = "odylith/runtime/source/project-brief.v1.md"


def _clean(value: Any) -> str:
    return display_text.strip_inline_markdown_emphasis(value)


def _first_nonempty(values: Sequence[str], *, limit: int, structural: bool = False) -> list[str]:
    if structural:
        return dedupe_strings((str(raw or "").strip() for raw in values), limit=limit)
    return dedupe_strings((_clean(raw) for raw in values), limit=limit)


def _intent(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    value = proposal.get("intent")
    return value if isinstance(value, Mapping) else {}


def _observed_source(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    value = proposal.get("observed_source")
    return value if isinstance(value, Mapping) else {}


def _release_label(*, release_selector: str, release_id: str) -> str:
    selector = _clean(release_selector)
    release = _clean(release_id)
    if selector and release:
        return f"{selector}->{release}"
    return selector or release or "none"


def _event_summary(
    *,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
) -> str:
    title = _clean(_intent(proposal).get("title")) or "Greenfield Project"
    return (
        f"Accepted greenfield proposal for {title}: "
        f"{len(backlog_items)} workstreams, {len(component_items)} planned components, "
        f"{len(diagram_ids)} architecture drafts, release {_release_label(release_selector=release_selector, release_id=release_id)}."
    )


def _event_context(proposal: Mapping[str, Any]) -> str:
    intent = _intent(proposal)
    source = _observed_source(proposal)
    assumptions = _first_nonempty(
        [
            _context_item_text(item, fields=("statement", "assumption", "summary", "title", "id"))
            for item in proposal.get("assumptions", [])
        ],
        limit=2,
    )
    questions = _first_nonempty(
        [
            _context_item_text(item, fields=("question", "statement", "summary", "title", "id"))
            for item in proposal.get("open_questions", [])
        ],
        limit=2,
    )
    parts = [
        f"reasoning_mode={_clean(intent.get('reasoning_mode')) or 'host_model_reasoned'}",
        f"source_posture={_clean(source.get('source_posture')) or 'unknown'}",
        "evidence_tier=user_intent",
    ]
    if assumptions:
        parts.append("assumptions=" + " | ".join(assumptions))
    if questions:
        parts.append("open_questions=" + " | ".join(questions))
    return "; ".join(parts)


def _context_item_text(value: Any, *, fields: Sequence[str]) -> str:
    if isinstance(value, Mapping):
        for field in fields:
            text = _clean(value.get(field))
            if text:
                return text
        return ""
    return _clean(value)


def _strip_memory_public_copy_emphasis(value: Any, *, key: str = "") -> Any:
    """Strip Markdown emphasis only from public prose, never typed memory fields."""

    if isinstance(value, str):
        return value if _structural_memory_value(key=key, value=value) else display_text.strip_inline_markdown_emphasis_tokens(value)
    if isinstance(value, Mapping):
        return {
            item_key: _strip_memory_public_copy_emphasis(item_value, key=str(item_key))
            for item_key, item_value in value.items()
        }
    if isinstance(value, list):
        return [_strip_memory_public_copy_emphasis(item, key=key) for item in value]
    if isinstance(value, tuple):
        return tuple(_strip_memory_public_copy_emphasis(item, key=key) for item in value)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray, str)):
        return [_strip_memory_public_copy_emphasis(item, key=key) for item in value]
    return value


def _structural_memory_value(*, key: str, value: str) -> bool:
    token = str(key or "").strip().casefold()
    if token in {"first_path", "raw_path"}:
        return False
    return structural_copy_value(key=token, value=value)


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
    """Build the Compass acceptance event shape without appending the stream."""

    workstream_ids = [_clean(row.get("idea_id")).upper() for row in backlog_items if _clean(row.get("idea_id"))]
    component_ids = [_clean(row.get("component_id")) for row in component_items if _clean(row.get("component_id"))]
    raw_artifacts = [
        PROJECT_BRIEF_SOURCE_PATH,
        *[str(row.get("idea_path", "")) for row in backlog_items if _clean(row.get("idea_path"))],
        *[str(row.get("spec_path", "")) for row in component_items if _clean(row.get("spec_path"))],
    ]
    artifacts = _first_nonempty(
        [_event_artifact_token(repo_root=repo_root, value=value) for value in raw_artifacts],
        limit=12,
        structural=True,
    )
    payload = {
        "version": "v1",
        "kind": "decision",
        "summary": _event_summary(
            proposal=proposal,
            backlog_items=backlog_items,
            component_items=component_items,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=release_id,
        ),
        "ts_iso": _clean(accepted_at) or "prewrite",
        "author": "odylith",
        "source": "domain-intelligence",
        "workstreams": workstream_ids,
        "artifacts": artifacts,
        "components": component_ids,
        "context": _event_context(proposal),
        "headline_hint": f"Greenfield proposal accepted for {_clean(_intent(proposal).get('title')) or 'Greenfield Project'}",
        "evidence_tier": "user_intent",
        "work_category": "governance",
    }
    return dict(_normalize_accepted_memory_copy(_strip_memory_public_copy_emphasis(payload)))


def _normalize_accepted_memory_copy(value: Any, *, key: str = "") -> Any:
    if isinstance(value, str):
        if _structural_memory_value(key=key, value=value):
            return value
        return normalize_terminal_punctuation(base_adverbial_note_action(value))
    if isinstance(value, Mapping):
        return {item_key: _normalize_accepted_memory_copy(item, key=str(item_key)) for item_key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_accepted_memory_copy(item, key=key) for item in value]
    if isinstance(value, tuple):
        return tuple(_normalize_accepted_memory_copy(item, key=key) for item in value)
    return value


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
) -> dict[str, Any]:
    """Build accepted-project memory payload before any durable write."""

    intent = _intent(proposal)
    payload = {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "evidence_tier": "user_intent",
        "accepted_at": _clean(accepted_at),
        "title": _clean(intent.get("title")) or "Greenfield Project",
        "source": "greenfield_apply",
        "proposal": _accepted_memory_proposal(proposal),
        "created": {
            "workstreams": [dict(row) for row in backlog_items],
            "components": [dict(row) for row in component_items],
            "diagrams": [str(item) for item in diagram_ids],
            "release_selector": _clean(release_selector),
            "release_id": _clean(release_id),
        },
        "source_launch": _source_launch_payload(source_launch_context),
        "validation_gate": dict(validation_gate or {}),
    }
    normalized = _normalize_accepted_memory_copy(_strip_memory_public_copy_emphasis(payload))
    source_text = greenfield_source_casing.proposal_source_casing_text(proposal)
    if source_text:
        normalized = greenfield_source_casing.restore_source_casing_in_public_copy(
            normalized,
            source_text=source_text,
        )
    return dict(normalized)


def _source_launch_payload(value: Mapping[str, Any] | None) -> dict[str, Any]:
    source = value if isinstance(value, Mapping) else {}
    allowed = (
        "project_workstream_id",
        "project_workstream_title",
        "start_workstream_id",
        "start_workstream_title",
        "first_wave",
        "release_selector",
        "implementation_prompt",
        "coding_readiness_gates",
        "validation_gates",
        "verification_commands",
    )
    payload: dict[str, Any] = {}
    for key in allowed:
        raw = source.get(key)
        if isinstance(raw, (list, tuple)):
            values = _first_nonempty([str(item) for item in raw], limit=8)
            if values:
                payload[key] = values
        else:
            text = _clean(raw)
            if text:
                payload[key] = text
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

    intent = _intent(proposal)
    title = _clean(intent.get("title")) or "Greenfield Project"
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    body_lines = render_project_brief_lines(brief)
    lines = [
        f"# {title} Project Brief",
        "",
        "- schema: odylith.greenfield.project_brief.v1",
        "- origin: greenfield",
        f"- accepted_at: {_clean(accepted_at) or 'prewrite'}",
        f"- release: {_release_label(release_selector=release_selector, release_id=release_id)}",
        f"- workstreams: {len(backlog_items)}",
        f"- components: {len(component_items)}",
        f"- diagrams: {len(diagram_ids)}",
        "",
        "## Brief",
        *(body_lines or ["- outcome: Accepted project brief was preserved in the accepted project record."]),
        "",
    ]
    text = "\n".join(lines)
    return display_text.strip_inline_markdown_emphasis_tokens(text).rstrip() + "\n"


def _accepted_memory_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return the proposal shape stored in accepted memory."""

    payload = copy.deepcopy(dict(proposal))
    first_path = _canonical_accepted_first_path(payload) or _normalized_first_path_from_events(payload)
    if not first_path:
        return payload

    intent = _mutable_child(payload, "intent")
    raw_first_path = _clean(intent.get("first_path"))
    intent["first_path"] = first_path
    summary = _clean(intent.get("summary"))
    if summary:
        if raw_first_path and raw_first_path in summary:
            summary = summary.replace(raw_first_path, first_path)
        else:
            marker = " stays bounded to: "
            index = summary.casefold().find(marker)
            if index >= 0:
                summary = f"{summary[: index + len(marker)]}{first_path}"
            elif first_path not in summary:
                summary = f"{summary.rstrip('.')} First path: {first_path}"
        intent["summary"] = summary

    semantic = _mutable_child(payload, "semantic_model")
    contract = _mutable_child(semantic, "first_path_contract")
    if contract:
        contract["raw_path"] = first_path
    return payload


def _canonical_accepted_first_path(proposal: Mapping[str, Any]) -> str:
    apply_input = proposal.get("apply_semantic_input") if isinstance(proposal.get("apply_semantic_input"), Mapping) else {}
    text = _clean(apply_input.get("first_path")) if isinstance(apply_input, Mapping) else ""
    if text:
        return normalize_first_path(text)
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    text = _clean(intent.get("first_path")) if isinstance(intent, Mapping) else ""
    return normalize_first_path(text) if text else ""


def _mutable_child(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if isinstance(value, Mapping):
        if isinstance(value, dict):
            return value
        child = dict(value)
    else:
        child = {}
    payload[key] = child
    return child


def _normalized_first_path_from_events(proposal: Mapping[str, Any]) -> str:
    semantic = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    contract = (
        semantic.get("first_path_contract")
        if isinstance(semantic.get("first_path_contract"), Mapping)
        else {}
    )
    events = contract.get("events") if isinstance(contract, Mapping) else ()
    if not isinstance(events, Sequence) or isinstance(events, (str, bytes, bytearray)):
        return ""
    sentences = _first_nonempty(
        [
            _clean(event.get("text") or event.get("mutation"))
            for event in events
            if isinstance(event, Mapping)
        ],
        limit=12,
    )
    return _join_sentences(sentences)


def _join_sentences(values: Sequence[str]) -> str:
    sentences = []
    for value in values:
        text = _clean(value).strip(" .")
        if text:
            sentences.append(f"{text}.")
    return " ".join(sentences)


def _write_accepted_project_source(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    validation_gate: Mapping[str, Any] | None,
    source_launch_context: Mapping[str, Any] | None = None,
    event: Mapping[str, Any],
) -> Path:
    """Write the accepted project source record consumed by Project and context."""

    path = _accepted_project_source_path(repo_root)
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector=release_selector,
        release_id=release_id,
        validation_gate=validation_gate,
        source_launch_context=source_launch_context,
        accepted_at=_clean(event.get("ts_iso")),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{json.dumps(payload, indent=2, sort_keys=True)}\n", encoding="utf-8")
    return path


def _write_project_brief_source(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str,
    release_id: str,
    event: Mapping[str, Any],
) -> Path:
    path = _project_brief_source_path(repo_root)
    payload = build_project_brief_source_markdown(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector=release_selector,
        release_id=release_id,
        accepted_at=_clean(event.get("ts_iso")),
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(payload, encoding="utf-8")
    return path


def record_compiled_greenfield_acceptance(
    *,
    repo_root: Path,
    accepted_project_preview: Mapping[str, Any],
    project_brief_record_text: str,
    compass_memory_preview: Mapping[str, Any],
) -> dict[str, Any]:
    """Persist precompiled greenfield memory without rebuilding product truth."""

    root = Path(repo_root).expanduser().resolve()
    event_preview = _json_ready_mapping(compass_memory_preview, label="compiled Compass memory preview")
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    existing_payload = _matching_exact_acceptance_event(stream_path=stream_path, event_preview=event_preview)
    reused_existing = existing_payload is not None
    payload = existing_payload or _append_compiled_acceptance_event(stream_path=stream_path, event_preview=event_preview)
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
    payload = _json_ready_mapping(accepted_project_preview, label="compiled accepted-project preview")
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


def record_greenfield_acceptance(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str = "",
    release_id: str = "",
    validation_gate: Mapping[str, Any] | None = None,
    tribunal: Mapping[str, Any] | None = None,
    source_launch_context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Append the accepted proposal shape to greenfield memory.

    The event is intentionally concise but richly linked: the progress view can show it as
    an acceptance decision, component records can map it back to planned components, and
    future Context Engine packets can retrieve the accepted intent, assumptions,
    and open questions from the agent-stream ledger.
    """

    root = Path(repo_root).expanduser().resolve()
    event_preview = build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector=release_selector,
        release_id=release_id,
    )
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    existing_payload = _matching_acceptance_event(repo_root=root, stream_path=stream_path, event_preview=event_preview)
    reused_existing = existing_payload is not None
    payload = existing_payload or log_compass_timeline_event.append_event(
        repo_root=root,
        stream_path=stream_path,
        kind="decision",
        summary=str(event_preview.get("summary", "")),
        workstream_values=[str(item) for item in event_preview.get("workstreams", [])],
        artifact_values=[str(item) for item in event_preview.get("artifacts", [])],
        component_values=[str(item) for item in event_preview.get("components", [])],
        author="odylith",
        source="domain-intelligence",
        context=str(event_preview.get("context", "")),
        headline_hint=str(event_preview.get("headline_hint", "")),
        evidence_tier="user_intent",
        work_category="governance",
    )
    accepted_project_path = _write_accepted_project_source(
        repo_root=root,
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector=release_selector,
        release_id=release_id,
        validation_gate=validation_gate or tribunal,
        source_launch_context=source_launch_context,
        event=payload,
    )
    project_brief_path = _write_project_brief_source(
        repo_root=root,
        proposal=proposal,
        backlog_items=backlog_items,
        component_items=component_items,
        diagram_ids=diagram_ids,
        release_selector=release_selector,
        release_id=release_id,
        event=payload,
    )
    return {
        "recorded": True,
        "reused_existing": reused_existing,
        "stream": str(stream_path),
        "accepted_project": str(accepted_project_path),
        "project_brief": str(project_brief_path),
        "event": payload,
    }


def _matching_acceptance_event(
    *,
    repo_root: Path,
    stream_path: Path,
    event_preview: Mapping[str, Any],
) -> dict[str, Any] | None:
    if not stream_path.is_file():
        return None
    expected = acceptance_event_signature(repo_root=repo_root, event=event_preview)
    for line in stream_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(event, Mapping):
            continue
        if acceptance_event_signature(repo_root=repo_root, event=event) == expected:
            return dict(event)
    return None


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


def acceptance_event_signature(*, repo_root: Path, event: Mapping[str, Any]) -> tuple[Any, ...]:
    """Return the deterministic Compass acceptance-event fields used for replay/readback."""

    return (
        _clean(event.get("kind")) or "decision",
        _clean(event.get("summary")),
        tuple(sorted(_clean(value).upper() for value in event.get("workstreams", []) if _clean(value))),
        tuple(sorted(_artifact_signature(repo_root=repo_root, value=value) for value in event.get("artifacts", []) if _clean(value))),
        tuple(sorted(_clean(value).casefold() for value in event.get("components", []) if _clean(value))),
        _clean(event.get("author")) or "odylith",
        _clean(event.get("source")) or "domain-intelligence",
        _clean(event.get("context")),
        _clean(event.get("headline_hint")),
        _clean(event.get("evidence_tier")) or "user_intent",
        _clean(event.get("work_category")) or "governance",
    )


def _artifact_signature(*, repo_root: Path, value: Any) -> str:
    token = _clean(value)
    if not token:
        return ""
    path = Path(token).expanduser()
    if path.is_absolute():
        try:
            return str(path.resolve().relative_to(repo_root))
        except ValueError:
            return str(path.resolve())
    return token[2:] if token.startswith("./") else token


def _event_artifact_token(*, repo_root: Path | None, value: Any) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    if repo_root is None:
        return token
    return _artifact_signature(repo_root=Path(repo_root).expanduser().resolve(), value=token)
