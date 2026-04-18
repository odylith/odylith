"""Frontier helpers for the Odylith execution engine layer."""

from __future__ import annotations

from odylith.runtime.execution_engine.contract import ExecutionEvent
from odylith.runtime.execution_engine.contract import ExecutionFrontier
from odylith.runtime.execution_engine.contract import ExecutionMode
from odylith.runtime.execution_engine.contract import ResumeHandle

_TERMINAL_EXTERNAL_STATUSES = {"succeeded", "failed", "cancelled", "complete"}


def derive_execution_frontier(
    events: tuple[ExecutionEvent, ...] | list[ExecutionEvent],
    *,
    default_mode: ExecutionMode = "implement",
) -> ExecutionFrontier:
    current_phase = ""
    last_successful_phase = ""
    active_blocker = ""
    truthful_next_move = ""
    execution_mode: ExecutionMode = default_mode
    in_flight_ids: list[str] = []
    resume_handles: list[ResumeHandle] = []

    for event in events:
        if event.phase:
            current_phase = event.phase
        if event.successful and event.phase:
            last_successful_phase = event.phase
            active_blocker = ""
        if event.blocker:
            active_blocker = event.blocker
        if event.next_move:
            truthful_next_move = event.next_move
        if event.execution_mode:
            execution_mode = str(event.execution_mode).strip() or default_mode
        if event.external_state is not None:
            if (
                event.external_state.external_id
                and event.external_state.semantic_status not in _TERMINAL_EXTERNAL_STATUSES
            ):
                in_flight_ids.append(event.external_state.external_id)
        if event.receipt is not None and event.receipt.resume_token:
            external_id = ""
            if event.receipt.external_state is not None:
                external_id = event.receipt.external_state.external_id
                if external_id and event.receipt.external_state.semantic_status not in _TERMINAL_EXTERNAL_STATUSES:
                    in_flight_ids.append(external_id)
            resume_handles.append(
                ResumeHandle(
                    resume_token=event.receipt.resume_token,
                    external_id=external_id,
                    source=event.receipt.external_state.source if event.receipt.external_state is not None else "",
                )
            )

    if not truthful_next_move:
        if active_blocker:
            truthful_next_move = "recover_current_blocker"
        elif current_phase:
            truthful_next_move = f"continue:{current_phase}"
        else:
            truthful_next_move = "re_anchor"

    deduped_ids = tuple(dict.fromkeys(in_flight_ids))
    deduped_handles: list[ResumeHandle] = []
    seen_tokens: set[str] = set()
    for handle in resume_handles:
        if handle.resume_token in seen_tokens:
            continue
        seen_tokens.add(handle.resume_token)
        deduped_handles.append(handle)

    return ExecutionFrontier(
        current_phase=current_phase,
        last_successful_phase=last_successful_phase,
        active_blocker=active_blocker,
        in_flight_external_ids=deduped_ids,
        resume_handles=tuple(deduped_handles),
        truthful_next_move=truthful_next_move,
        execution_mode=execution_mode,
    )
