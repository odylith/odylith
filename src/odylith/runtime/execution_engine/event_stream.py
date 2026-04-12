from __future__ import annotations

from typing import Sequence

from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ExecutionEvent
from odylith.runtime.execution_engine.contract import ExecutionMode
from odylith.runtime.execution_engine.contract import ExternalDependencyState
from odylith.runtime.execution_engine.contract import ResourceClosure
from odylith.runtime.execution_engine.contract import SemanticReceipt


def _event_id(index: int, suffix: str) -> str:
    return f"eg-{index:02d}-{suffix}"


def build_execution_event_stream(
    *,
    current_phase: str,
    last_successful_phase: str,
    blocker: str,
    next_move: str,
    execution_mode: ExecutionMode,
    admissibility: AdmissibilityDecision,
    contradictions: Sequence[ContradictionRecord] = (),
    history_rule_hits: Sequence[str] = (),
    closure: ResourceClosure | None = None,
    external_state: ExternalDependencyState | None = None,
    receipt: SemanticReceipt | None = None,
    context_pressure: str = "",
) -> tuple[ExecutionEvent, ...]:
    events: list[ExecutionEvent] = []
    if last_successful_phase:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "last-success"),
                event_type="last_successful_phase",
                phase=last_successful_phase,
                successful=True,
                next_move=next_move,
                execution_mode=execution_mode,
            )
        )
    if contradictions:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "contradictions"),
                event_type="contradiction_pressure",
                phase=current_phase,
                blocker=blocker,
                next_move=next_move,
                execution_mode=execution_mode,
                pressure_signals=tuple(
                    dict.fromkeys(
                        row.category or row.source or "contradiction"
                        for row in contradictions
                    )
                ),
            )
        )
    if history_rule_hits:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "history-rules"),
                event_type="history_rule_pressure",
                phase=current_phase,
                blocker=blocker,
                next_move=next_move,
                execution_mode=execution_mode,
                pressure_signals=tuple(
                    dict.fromkeys(str(hit).strip() for hit in history_rule_hits if str(hit).strip())
                ),
            )
        )
    if closure is not None and closure.classification in {"incomplete", "destructive"}:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "closure"),
                event_type="resource_closure",
                phase=current_phase,
                blocker=blocker,
                next_move=next_move,
                execution_mode=execution_mode,
                pressure_signals=(f"closure:{closure.classification}",),
            )
        )
    if external_state is not None and external_state.semantic_status not in {"succeeded", "failed", "cancelled", "complete"}:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "wait"),
                event_type="external_dependency_wait",
                phase=current_phase,
                blocker=external_state.detail or blocker,
                next_move="resume.external_dependency",
                execution_mode=execution_mode,
                pressure_signals=(f"wait:{external_state.semantic_status}",),
                external_state=external_state,
                receipt=receipt,
            )
        )
    if context_pressure in {"high", "critical"}:
        events.append(
            ExecutionEvent(
                event_id=_event_id(len(events), "context-pressure"),
                event_type="context_pressure",
                phase=current_phase,
                blocker=blocker,
                next_move=next_move,
                execution_mode=execution_mode,
                pressure_signals=(f"context_pressure:{context_pressure}",),
            )
        )
    events.append(
        ExecutionEvent(
            event_id=_event_id(len(events), "decision"),
            event_type="admissibility_decision",
            phase=current_phase,
            successful=admissibility.outcome == "admit" and not blocker,
            blocker=blocker,
            next_move=next_move,
            execution_mode=execution_mode,
            pressure_signals=admissibility.pressure_signals,
            external_state=external_state,
            receipt=receipt,
        )
    )
    return tuple(events)
