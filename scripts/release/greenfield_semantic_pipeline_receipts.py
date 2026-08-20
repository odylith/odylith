"""Terminal receipt contracts for the bounded Greenfield production pipeline."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path
from typing import Any

from greenfield_semantic_release_support import greenfield_runtime_source_fingerprint
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    semantic_execution_evidence,
)


PIPELINE_VERSION = "odylith.greenfield.production-standard-pipeline.v14"
BOUNDED_PIPELINE_VERSION = "odylith.greenfield.production-bounded-pipeline.v14"


def pipeline_receipt(
    *, case_id: str, status: str, outcome: str, wall_ms: int,
    host_profile: str,
    budget: Mapping[str, Any], critic: Mapping[str, Any] | None,
    source: Mapping[str, Any] | None,
    author: Mapping[str, Any] | None, assessment: Mapping[str, Any] | None,
    finalized: Mapping[str, Any] | None, transaction: Mapping[str, Any] | None,
    failed_stage: str, failure: str,
) -> dict[str, Any]:
    model_call_count = _model_calls(critic) + _model_calls(source) + _model_calls(author)
    total_tokens = _token_total(critic) + _token_total(source) + _token_total(author)
    mechanism_execution = semantic_execution_evidence(
        host_profile=host_profile,
        tier=str(budget["tier"]),
        status=status,
        outcome=outcome,
        wall_ms=wall_ms,
        model_call_count=model_call_count,
        restart_count=0,
        implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        prior_standard_failure_sha256=str(
            budget.get("prior_standard_failure_sha256") or ""
        ),
    )
    return {
        "version": PIPELINE_VERSION,
        "case_id": case_id,
        "status": status,
        "outcome": outcome,
        "wall_ms": wall_ms,
        "budget": dict(budget),
        "materiality_critic": critic,
        "source_hypothesis": source,
        "final_graph_adjudication": author,
        "materiality_assessment": assessment,
        "packet": finalized.get("packet") if finalized else None,
        "transaction": transaction,
        "failed_stage": failed_stage,
        "failure": failure,
        "model_call_count": model_call_count,
        "restart_count": 0,
        "total_tokens": total_tokens,
        "mechanism_execution": mechanism_execution,
        "evidence_assignment": budget.get("evidence_assignment"),
    }


def bounded_receipt(
    *, case_id: str, tier: str, wall_ms: int, attempt: Mapping[str, Any],
) -> dict[str, Any]:
    attempt_execution = dict(attempt["mechanism_execution"])
    mechanism_execution = semantic_execution_evidence(
        host_profile=str(attempt_execution["host_profile"]),
        tier="rescue",
        status=str(attempt["status"]),
        outcome=str(attempt["outcome"]),
        wall_ms=wall_ms,
        model_call_count=int(attempt.get("model_call_count", 0)),
        restart_count=0,
        implementation_fingerprint_sha256=str(
            attempt_execution["implementation_fingerprint_sha256"]
        ),
        prior_standard_failure_sha256=str(
            attempt_execution["prior_standard_failure_sha256"]
        ),
    )
    return {
        "version": BOUNDED_PIPELINE_VERSION,
        "case_id": case_id,
        "tier": tier,
        "status": attempt["status"],
        "outcome": attempt["outcome"],
        "wall_ms": wall_ms,
        "attempt": dict(attempt),
        "model_call_count": int(attempt.get("model_call_count", 0)),
        "restart_count": 0,
        "total_tokens": int(attempt.get("total_tokens", 0)),
        "automatic_deep_tier": False,
        "mechanism_execution": mechanism_execution,
    }


def _token_total(value: Mapping[str, Any] | None) -> int:
    if not isinstance(value, Mapping) or not isinstance(value.get("usage"), Mapping):
        return 0
    usage = value["usage"]
    return int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))


def _model_calls(value: Mapping[str, Any] | None) -> int:
    return int(value.get("model_call_count", 0)) if isinstance(value, Mapping) else 0


def write_receipt(path: Path, receipt: dict[str, Any]) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return receipt


__all__ = [
    "BOUNDED_PIPELINE_VERSION", "PIPELINE_VERSION", "bounded_receipt",
    "pipeline_receipt", "write_receipt",
]
