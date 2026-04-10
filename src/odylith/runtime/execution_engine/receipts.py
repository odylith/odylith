from __future__ import annotations

from odylith.runtime.execution_engine.contract import ExternalDependencyState
from odylith.runtime.execution_engine.contract import ResumeHandle
from odylith.runtime.execution_engine.contract import SemanticReceipt

_SEMANTIC_STATUS_MAP = {
    "queued": "queued",
    "pending": "queued",
    "building": "building",
    "running": "building",
    "awaiting_callback": "awaiting_callback",
    "callback": "awaiting_callback",
    "waiting_approval": "waiting_approval",
    "approval_required": "waiting_approval",
    "blocked_on_token_refresh": "blocked_on_token_refresh",
    "token_refresh": "blocked_on_token_refresh",
    "success": "succeeded",
    "succeeded": "succeeded",
    "failed": "failed",
    "cancelled": "cancelled",
}


def normalize_external_dependency_state(
    *,
    source: str,
    raw_status: str,
    external_id: str,
    detail: str = "",
) -> ExternalDependencyState:
    token = str(raw_status or "").strip().lower().replace(" ", "_")
    semantic_status = _SEMANTIC_STATUS_MAP.get(token, token or "unknown")
    return ExternalDependencyState(
        source=str(source or "").strip(),
        external_id=str(external_id or "").strip(),
        semantic_status=semantic_status,
        detail=str(detail or "").strip(),
    )


def emit_semantic_receipt(
    *,
    action: str,
    scope_fingerprint: str,
    causal_parent: str = "",
    external_state: ExternalDependencyState | None = None,
    resume_token: str = "",
    expected_next_states: tuple[str, ...] | list[str] = (),
) -> SemanticReceipt:
    normalized_resume_token = str(resume_token or "").strip() or f"resume:{scope_fingerprint}"
    return SemanticReceipt(
        action=str(action or "").strip(),
        scope_fingerprint=str(scope_fingerprint or "").strip(),
        causal_parent=str(causal_parent or "").strip(),
        resume_token=normalized_resume_token,
        expected_next_states=tuple(str(item).strip() for item in expected_next_states if str(item).strip()),
        external_state=external_state,
    )


def reattach_receipt(receipt: SemanticReceipt) -> ResumeHandle:
    return ResumeHandle(
        resume_token=receipt.resume_token,
        external_id=receipt.external_state.external_id if receipt.external_state is not None else "",
        source=receipt.external_state.source if receipt.external_state is not None else "",
    )
