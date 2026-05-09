"""Durable memory records for accepted greenfield proposals.

Greenfield proposal application is confirmation gated. Once an operator accepts
a host-reasoned proposal, the project shape must stop being one chat response
and become durable acceptance evidence that later context and memory paths can
retrieve without re-asking the same scope questions.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import log_compass_timeline_event


def _clean(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _first_nonempty(values: Sequence[str], *, limit: int) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = _clean(raw)
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
        if len(rows) >= limit:
            break
    return rows


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
    assumptions = _first_nonempty([str(item) for item in proposal.get("assumptions", []) if _clean(item)], limit=2)
    questions = _first_nonempty([str(item) for item in proposal.get("open_questions", []) if _clean(item)], limit=2)
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


def record_greenfield_acceptance(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    backlog_items: Sequence[Mapping[str, Any]],
    component_items: Sequence[Mapping[str, Any]],
    diagram_ids: Sequence[str],
    release_selector: str = "",
    release_id: str = "",
) -> dict[str, Any]:
    """Append the accepted proposal shape to greenfield memory.

    The event is intentionally concise but richly linked: the progress view can show it as
    an acceptance decision, component records can map it back to planned components, and
    future Context Engine packets can retrieve the accepted intent, assumptions,
    and open questions from the agent-stream ledger.
    """

    root = Path(repo_root).expanduser().resolve()
    workstream_ids = [_clean(row.get("idea_id")).upper() for row in backlog_items if _clean(row.get("idea_id"))]
    component_ids = [_clean(row.get("component_id")) for row in component_items if _clean(row.get("component_id"))]
    artifacts = _first_nonempty(
        [
            *[str(row.get("idea_path", "")) for row in backlog_items if _clean(row.get("idea_path"))],
            *[str(row.get("spec_path", "")) for row in component_items if _clean(row.get("spec_path"))],
        ],
        limit=12,
    )
    stream_path = root / agent_runtime_contract.AGENT_STREAM_PATH
    payload = log_compass_timeline_event.append_event(
        repo_root=root,
        stream_path=stream_path,
        kind="decision",
        summary=_event_summary(
            proposal=proposal,
            backlog_items=backlog_items,
            component_items=component_items,
            diagram_ids=diagram_ids,
            release_selector=release_selector,
            release_id=release_id,
        ),
        workstream_values=workstream_ids,
        artifact_values=artifacts,
        component_values=component_ids,
        author="odylith",
        source="domain-intelligence",
        context=_event_context(proposal),
        headline_hint=f"Greenfield proposal accepted for {_clean(_intent(proposal).get('title')) or 'Greenfield Project'}",
        evidence_tier="user_intent",
        work_category="governance",
    )
    return {
        "recorded": True,
        "stream": str(stream_path),
        "event": payload,
    }
