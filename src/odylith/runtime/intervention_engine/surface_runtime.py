from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.intervention_engine import stream_state


_STOP_RECOVERABLE_LIVE_KINDS: tuple[str, ...] = (
    "capture_proposed",
    "intervention_card",
    "ambient_signal",
    "intervention_teaser",
)
_STOP_RECOVERY_SKIP_STATUSES: frozenset[str] = frozenset({"manual_visible"})
_STOP_RECOVERY_SKIP_CHANNELS: frozenset[str] = frozenset({"manual_visible_command", "stop_one_shot_guard"})


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_block_string(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    rows: list[str] = []
    blank_run = 0
    for raw_line in text.split("\n"):
        line = str(raw_line).rstrip()
        if not line.strip():
            blank_run += 1
            if blank_run > 1:
                continue
            rows.append("")
            continue
        blank_run = 0
        rows.append(line)
    return "\n".join(rows).strip()


def _normalize_string_list(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        token = _normalize_string(value)
        return [token] if token else []
    rows: list[str] = []
    seen: set[str] = set()
    for item in value:
        token = _normalize_string(item)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _ref_rows(kind: str, values: Sequence[str]) -> list[dict[str, str]]:
    return [
        {"kind": kind, "id": token, "path": "", "label": token}
        for token in _normalize_string_list(values)
    ]


def recent_session_summary(*, repo_root: Path, session_id: str) -> str:
    normalized_session = _normalize_string(session_id)
    if not normalized_session:
        return ""
    for row in reversed(
        stream_state.load_recent_intervention_events(
            repo_root=repo_root,
            limit=40,
            session_id=normalized_session,
        )
    ):
        summary = _normalize_string(row.get("summary"))
        if summary:
            return summary
    return ""


def recent_session_prompt_excerpt(*, repo_root: Path, session_id: str) -> str:
    normalized_session = _normalize_string(session_id)
    if not normalized_session:
        return ""
    for row in reversed(
        stream_state.load_recent_intervention_events(
            repo_root=repo_root,
            limit=200,
            session_id=normalized_session,
        )
    ):
        prompt_excerpt = _normalize_string(row.get("prompt_excerpt"))
        if prompt_excerpt:
            return prompt_excerpt
    return ""


def recent_session_changed_paths(*, repo_root: Path, session_id: str, limit: int = 80) -> list[str]:
    normalized_session = _normalize_string(session_id)
    if not normalized_session:
        return []
    rows: list[str] = []
    seen: set[str] = set()
    for event in reversed(
        stream_state.load_recent_intervention_events(
            repo_root=repo_root,
            limit=max(1, int(limit)),
            session_id=normalized_session,
        )
    ):
        for token in _normalize_string_list(event.get("artifacts")):
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows[:12]


def recent_session_ids(
    *,
    repo_root: Path,
    session_id: str,
    field: str,
    limit: int = 80,
) -> list[str]:
    normalized_session = _normalize_string(session_id)
    if not normalized_session:
        return []
    wanted = _normalize_string(field)
    rows: list[str] = []
    seen: set[str] = set()
    for event in reversed(
        stream_state.load_recent_intervention_events(
            repo_root=repo_root,
            limit=max(1, int(limit)),
            session_id=normalized_session,
        )
    ):
        for token in _normalize_string_list(event.get(wanted)):
            if token in seen:
                continue
            seen.add(token)
            rows.append(token)
    return rows[:8]


def recent_session_live_markdown(*, repo_root: Path, session_id: str, limit: int = 120) -> str:
    """Return the latest non-closeout live beat that Stop can replay visibly.

    Checkpoint hook channels are not equally visible across hosts. Stop is the
    proven one-shot continuation lane, so it may replay an earlier generated
    Ambient/Observation/Proposal/teaser beat when that beat has not already
    been explicitly rendered by the manual-visible or Stop lanes.
    """

    normalized_session = _normalize_string(session_id)
    if not normalized_session:
        return ""
    for event in reversed(
        stream_state.load_recent_intervention_events(
            repo_root=repo_root,
            limit=max(1, int(limit)),
            session_id=normalized_session,
        )
    ):
        kind = _normalize_string(event.get("kind")).lower()
        if kind not in _STOP_RECOVERABLE_LIVE_KINDS:
            continue
        if _normalize_string(event.get("turn_phase")).lower() == "stop_summary":
            continue
        if _normalize_string(event.get("delivery_status")).lower() in _STOP_RECOVERY_SKIP_STATUSES:
            continue
        if _normalize_string(event.get("delivery_channel")).lower() in _STOP_RECOVERY_SKIP_CHANNELS:
            continue
        display = _normalize_block_string(event.get("display_markdown")) or _normalize_block_string(event.get("display_plain"))
        if display:
            return display
        summary = _normalize_string(event.get("summary"))
        if summary:
            return summary
    return ""


def observation_envelope(
    *,
    host_family: str,
    turn_phase: str,
    session_id: str = "",
    prompt_excerpt: str = "",
    assistant_summary: str = "",
    changed_paths: Sequence[str] = (),
    workstreams: Sequence[str] = (),
    components: Sequence[str] = (),
    bugs: Sequence[str] = (),
    diagrams: Sequence[str] = (),
    packet_summary: Mapping[str, Any] | None = None,
    delivery_snapshot: Mapping[str, Any] | None = None,
    active_target_refs: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    refs: list[dict[str, str]] = []
    refs.extend(_ref_rows("workstream", workstreams))
    refs.extend(_ref_rows("component", components))
    refs.extend(_ref_rows("bug", bugs))
    refs.extend(_ref_rows("diagram", diagrams))
    for row in active_target_refs:
        if not isinstance(row, Mapping):
            continue
        refs.append(
            {
                "kind": _normalize_string(row.get("kind")),
                "id": _normalize_string(row.get("id")),
                "path": _normalize_string(row.get("path")),
                "label": _normalize_string(row.get("label")) or _normalize_string(row.get("id")),
            }
        )
    return {
        "host_family": _normalize_string(host_family).lower(),
        "session_id": _normalize_string(session_id) or agent_runtime_contract.default_host_session_id(),
        "turn_phase": _normalize_string(turn_phase).lower(),
        "prompt_excerpt": _normalize_string(prompt_excerpt),
        "assistant_summary": _normalize_string(assistant_summary),
        "changed_paths": _normalize_string_list(changed_paths),
        "packet_summary": _mapping(packet_summary),
        "delivery_snapshot": _mapping(delivery_snapshot),
        "active_target_refs": refs,
    }


def teaser_text(bundle: Mapping[str, Any]) -> str:
    candidate = _mapping(bundle.get("candidate"))
    if _normalize_string(candidate.get("stage")) != "teaser":
        return ""
    if _normalize_string(candidate.get("suppressed_reason")):
        return ""
    return _normalize_string(candidate.get("teaser_text"))


def render_blocks(
    bundle: Mapping[str, Any],
    *,
    markdown: bool,
    include_proposal: bool,
) -> str:
    candidate = _mapping(bundle.get("candidate"))
    proposal = _mapping(bundle.get("proposal"))
    parts: list[str] = []
    candidate_stage = _normalize_string(candidate.get("stage"))
    candidate_allowed = candidate_stage == "card" and not _normalize_string(candidate.get("suppressed_reason"))
    proposal_allowed = (
        include_proposal
        and bool(proposal.get("eligible"))
        and not _normalize_string(proposal.get("suppressed_reason"))
    )
    if candidate_allowed:
        parts.append(
            _normalize_block_string(candidate.get("markdown_text" if markdown else "plain_text"))
        )
    if proposal_allowed:
        parts.append(
            _normalize_block_string(proposal.get("markdown_text" if markdown else "plain_text"))
        )
    return "\n\n".join(part for part in parts if part).strip()


def append_bundle_events(
    *,
    repo_root: Path,
    bundle: Mapping[str, Any],
    include_proposal: bool,
    delivery_channel: str = "",
    delivery_status: str = "",
    render_surface: str = "",
    delivery_latency_ms: float | None = None,
) -> list[str]:
    observation = _mapping(bundle.get("observation"))
    candidate = _mapping(bundle.get("candidate"))
    proposal = _mapping(bundle.get("proposal"))
    target_refs = observation.get("active_target_refs")
    refs = target_refs if isinstance(target_refs, list) else []
    workstreams = [
        _normalize_string(row.get("id"))
        for row in refs
        if isinstance(row, Mapping) and _normalize_string(row.get("kind")).lower() == "workstream"
    ]
    components = [
        _normalize_string(row.get("id"))
        for row in refs
        if isinstance(row, Mapping) and _normalize_string(row.get("kind")).lower() == "component"
    ]
    prompt_excerpt = _normalize_string(observation.get("prompt_excerpt"))
    assistant_summary = _normalize_string(observation.get("assistant_summary"))
    events: list[str] = []
    stage = _normalize_string(candidate.get("stage")).lower()
    candidate_key = _normalize_string(candidate.get("key")) or _normalize_string(proposal.get("key"))
    moment = _mapping(candidate.get("moment"))
    semantic_signature = proposal.get("semantic_signature")
    if not isinstance(semantic_signature, list):
        semantic_signature = moment.get("semantic_signature")
    if stage == "teaser" and not _normalize_string(candidate.get("suppressed_reason")) and _normalize_string(candidate.get("teaser_text")):
        stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="intervention_teaser",
            summary=_normalize_string(candidate.get("teaser_text")),
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=candidate_key,
            turn_phase=_normalize_string(observation.get("turn_phase")),
            workstreams=workstreams,
            artifacts=_normalize_string_list(observation.get("changed_paths")),
            components=components,
            display_plain=_normalize_string(candidate.get("teaser_text")),
            prompt_excerpt=prompt_excerpt,
            assistant_summary=assistant_summary,
            moment_kind=_normalize_string(moment.get("kind")),
            semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
        )
        events.append("intervention_teaser")
    if stage == "card" and not _normalize_string(candidate.get("suppressed_reason")) and _normalize_string(candidate.get("markdown_text")):
        stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="intervention_card",
            summary=_normalize_string(candidate.get("headline")) or "Odylith Observation",
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=candidate_key,
            turn_phase=_normalize_string(observation.get("turn_phase")),
            workstreams=workstreams,
            artifacts=_normalize_string_list(observation.get("changed_paths")),
            components=components,
            display_markdown=_normalize_block_string(candidate.get("markdown_text")),
            display_plain=_normalize_block_string(candidate.get("plain_text")),
            prompt_excerpt=prompt_excerpt,
            assistant_summary=assistant_summary,
            moment_kind=_normalize_string(moment.get("kind")),
            semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
        )
        events.append("intervention_card")
    if (
        include_proposal
        and bool(proposal.get("eligible"))
        and not _normalize_string(proposal.get("suppressed_reason"))
        and _normalize_string(proposal.get("markdown_text"))
    ):
        stream_state.append_intervention_event(
            repo_root=repo_root,
            kind="capture_proposed",
            summary=_normalize_string(proposal.get("summary")) or "Odylith Proposal",
            session_id=_normalize_string(observation.get("session_id")),
            host_family=_normalize_string(observation.get("host_family")),
            intervention_key=_normalize_string(proposal.get("key")) or candidate_key,
            turn_phase=_normalize_string(observation.get("turn_phase")),
            workstreams=workstreams,
            artifacts=_normalize_string_list(observation.get("changed_paths")),
            components=components,
            action_surfaces=_normalize_string_list(proposal.get("action_surfaces")),
            display_markdown=_normalize_block_string(proposal.get("markdown_text")),
            display_plain=_normalize_block_string(proposal.get("plain_text")),
            confirmation_text=_normalize_string(proposal.get("confirmation_text")),
            proposal_status="pending",
            prompt_excerpt=prompt_excerpt,
            assistant_summary=assistant_summary,
            moment_kind=_normalize_string(moment.get("kind")),
            semantic_signature=semantic_signature if isinstance(semantic_signature, list) else (),
            delivery_channel=delivery_channel,
            delivery_status=delivery_status,
            render_surface=render_surface,
            delivery_latency_ms=delivery_latency_ms,
        )
        events.append("capture_proposed")
    return events
