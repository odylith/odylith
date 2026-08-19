"""Independently challenge and seal one Greenfield material question."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from threading import Event
import time
from typing import Any

from greenfield_semantic_structured_host import (
    HostStageTimeout,
    elapsed_ms,
    run_structured_host,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_clarification_packet,
)


CLARIFICATION_AUTHOR_VERSION = "odylith.greenfield.clarification-author.v1"


class ClarificationStageIncomplete(RuntimeError):
    """Carry one attempted clarification-author call into terminal evidence."""

    def __init__(
        self, message: str, *, failure_kind: str, receipt: Mapping[str, Any]
    ) -> None:
        super().__init__(message)
        self.failure_kind = failure_kind
        self.receipt = dict(receipt)


def run_clarification_author(
    *,
    case_id: str,
    prompt_text: str,
    assessment: Mapping[str, Any],
    critic_run_id: str,
    host_profile: str,
    model: str,
    reasoning_effort: str,
    model_budget_seconds: int,
    output_path: Path,
    cancel_event: Event | None = None,
) -> dict[str, Any]:
    """Use a fresh host context to challenge, never rewrite, one question."""

    clarification = _mapping(
        assessment.get("clarification"), "materiality clarification"
    )
    field = _text(clarification.get("field"), "materiality field")
    question = _text(clarification.get("question"), "materiality question")
    challenge_prompt = (
        "Independently review one proposed material clarification. Use only the operator "
        "prompt and the typed materiality assessment below. Do not author a product graph, "
        "change the question, infer an answer, or use tools, files, prior candidates, validator "
        "errors, regex, fuzzy matching, or token heuristics. Approve only when the named field "
        "is materially unresolved, the exact question is source-grounded, and one answer would "
        "settle the graph boundary. Otherwise reject it.\n"
        f"OPERATOR_PROMPT\n{prompt_text}\nMATERIALITY_ASSESSMENT\n"
        f"{_json(assessment)}"
    )
    started_ns = time.monotonic_ns()
    try:
        candidate, usage, wall_ms = run_structured_host(
            schema=_challenge_schema(field=field, question=question),
            prompt=challenge_prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=model_budget_seconds,
            temporary_prefix="odylith-clarification-author-",
            cancel_event=cancel_event,
            host_profile=host_profile,
        )
        decision = require_clarification_author_decision(
            candidate,
            field=field,
            question=question,
        )
        author_run_id = "clarification-author:" + hashlib.sha256(
            _json(decision).encode("utf-8")
        ).hexdigest()
        packet = build_semantic_clarification_packet(
            assessment,
            prompt=prompt_text,
            critic_run_id=critic_run_id,
            author_run_id=author_run_id,
            critic_host_profile=host_profile,
        )
    except (HostStageTimeout, RuntimeError, ValueError) as error:
        failure_kind = (
            "deadline"
            if isinstance(error, HostStageTimeout)
            else "typed"
            if isinstance(error, ValueError)
            else "environment"
        )
        receipt = _receipt(
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            model_budget_seconds=model_budget_seconds,
            wall_ms=elapsed_ms(started_ns),
            usage={},
            prompt_text=challenge_prompt,
            decision=None,
            author_run_id="",
            packet=None,
            validation_status="failed",
            validation_error=str(error),
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
        raise ClarificationStageIncomplete(
            str(error), failure_kind=failure_kind, receipt=receipt
        ) from error
    receipt = _receipt(
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        model_budget_seconds=model_budget_seconds,
        wall_ms=wall_ms,
        usage=usage,
        prompt_text=challenge_prompt,
        decision=decision,
        author_run_id=author_run_id,
        packet=packet,
        validation_status="passed",
        validation_error="",
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _receipt(
    *,
    case_id: str,
    host_profile: str,
    model: str,
    reasoning_effort: str,
    model_budget_seconds: int,
    wall_ms: int,
    usage: Mapping[str, Any],
    prompt_text: str,
    decision: Mapping[str, Any] | None,
    author_run_id: str,
    packet: Mapping[str, Any] | None,
    validation_status: str,
    validation_error: str,
) -> dict[str, Any]:
    return {
        "version": CLARIFICATION_AUTHOR_VERSION,
        "stage": "clarification_author",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": wall_ms,
        "usage": dict(usage),
        "model_call_count": 1,
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "decision": dict(decision) if decision is not None else None,
        "author_run_id": author_run_id,
        "packet": dict(packet) if packet is not None else None,
        "validation_status": validation_status,
        "validation_error": validation_error,
    }


def require_clarification_author_decision(
    value: Any,
    *,
    field: str,
    question: str,
) -> dict[str, Any]:
    row = _mapping(value, "clarification author decision")
    expected = {
        "version",
        "decision",
        "field",
        "question",
        "evidence_support",
        "one_question_sufficient",
        "unsupported_additions",
        "rationale",
    }
    if set(row) != expected:
        raise ValueError("clarification author decision fields do not match its contract")
    if row.get("version") != CLARIFICATION_AUTHOR_VERSION:
        raise ValueError("clarification author decision version is unsupported")
    if row.get("field") != field or row.get("question") != question:
        raise ValueError("clarification author changed the proposed material question")
    if (
        row.get("decision") != "approve"
        or row.get("evidence_support") != "source_supported"
        or row.get("one_question_sufficient") is not True
        or row.get("unsupported_additions") != []
    ):
        raise ValueError("independent clarification author rejected the material question")
    _text(row.get("rationale"), "clarification author rationale")
    return dict(row)


def _challenge_schema(*, field: str, question: str) -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "version",
            "decision",
            "field",
            "question",
            "evidence_support",
            "one_question_sufficient",
            "unsupported_additions",
            "rationale",
        ],
        "properties": {
            "version": {"type": "string", "enum": [CLARIFICATION_AUTHOR_VERSION]},
            "decision": {"type": "string", "enum": ["approve", "reject"]},
            "field": {"type": "string", "enum": [field]},
            "question": {"type": "string", "enum": [question]},
            "evidence_support": {
                "type": "string",
                "enum": ["source_supported", "source_insufficient"],
            },
            "one_question_sufficient": {"type": "boolean"},
            "unsupported_additions": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": 0,
            },
            "rationale": {"type": "string", "minLength": 1, "maxLength": 1_000},
        },
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{label} must be non-empty")
    return text


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


__all__ = [
    "CLARIFICATION_AUTHOR_VERSION",
    "ClarificationStageIncomplete",
    "require_clarification_author_decision",
    "run_clarification_author",
]
