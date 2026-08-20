"""Run one source challenge followed by immutable-source graph completion."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
import hashlib
import json
from pathlib import Path
from threading import Event
import time
from typing import Any, Callable

from greenfield_semantic_source_graph_author import (
    StructuredSourceHypothesisRejected,
    run_partitioned_graph_hypothesis,
    run_source_graph_hypothesis,
)
from greenfield_semantic_structured_host import HostStageCancelled
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
)


EXPERIMENT_VERSION = "odylith.greenfield.production-standard-stage.v8"


class CompletionStageIncomplete(ValueError):
    """Carry an admitted source graph into a completion-only failure receipt."""

    def __init__(self, message: str, *, receipt: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.receipt = dict(receipt)


class ReusableSourcePairDisagreement(ValueError):
    """Carry two structured hypotheses past a typed source or completion dispute."""

    def __init__(
        self,
        message: str,
        *,
        source: Mapping[str, Any],
        source_adjudication: Mapping[str, Any] | None,
        dispute: str,
    ) -> None:
        super().__init__(message)
        self.source = dict(source)
        self.source_adjudication = (
            dict(source_adjudication) if source_adjudication is not None else None
        )
        self.dispute = dispute


def run_hedged_source_graph_hypothesis_case(
    *, corpus_path: Path, case_id: str, model: str, reasoning_effort: str,
    output_path: Path, model_budget_seconds: int,
    cancel_event: Event | None = None,
    host_profile: str = "codex",
    candidate_validator: Callable[[Mapping[str, Any], str], None] | None = None,
) -> dict[str, Any]:
    """Bind dedicated source truth to the parallel full-graph completion."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
    started_ns = time.monotonic_ns()
    run_cancellations = (Event(), Event())
    attempts: list[dict[str, Any]] = []

    def full_graph_hypothesis() -> dict[str, Any]:
        return run_partitioned_graph_hypothesis(
            prompt_text=prompt_text,
            evidence_catalog=evidence_catalog,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=model_budget_seconds,
            cancel_event=run_cancellations[0],
            host_profile=host_profile,
        )

    def source_only_hypothesis() -> dict[str, Any]:
        return run_source_graph_hypothesis(
            prompt_text=prompt_text,
            evidence_catalog=evidence_catalog,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=model_budget_seconds,
            cancel_event=run_cancellations[1],
            host_profile=host_profile,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        full_future = executor.submit(full_graph_hypothesis)
        source_future = executor.submit(source_only_hypothesis)
        try:
            full = _wait_for_hypothesis(
                full_future,
                cancel_event=cancel_event,
                run_cancellations=run_cancellations,
            )
        except Exception as error:
            attempts.append(_failed_hypothesis_run(0, "full_graph"))
            if candidate_validator is None:
                for event in run_cancellations:
                    event.set()
                _settle_unused_hypothesis(source_future)
                raise error
            try:
                source_only = _wait_for_hypothesis(
                    source_future,
                    cancel_event=cancel_event,
                    run_cancellations=run_cancellations,
                )
            except StructuredSourceHypothesisRejected as source_error:
                source_only = {
                    "source": source_error.source,
                    "usage": source_error.usage,
                    "wall_ms": source_error.wall_ms,
                    "prompt_text": source_error.prompt_text,
                }
            except Exception:
                raise error
            source_candidate = {
                "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
                "source": _mapping(
                    source_only.get("source"), "source-only graph hypothesis"
                ),
                "completion": {},
            }
            try:
                _require_candidate(
                    candidate_validator, source_candidate, "source_only"
                )
            except ReusableSourcePairDisagreement as source_error:
                attempts.append(
                    _completed_hypothesis_run(
                        1, "source_only", source_only,
                        status="source_pair_disagreement", error=source_error,
                    )
                )
                receipt = _source_pair_handoff_receipt(
                    case_id=case_id,
                    host_profile=host_profile,
                    model=model,
                    reasoning_effort=reasoning_effort,
                    model_budget_seconds=model_budget_seconds,
                    started_ns=started_ns,
                    attempts=attempts,
                    source_only=source_only,
                    hypothesis_candidates=(
                        {"run_index": 1, "hypothesis_mode": "source_only",
                         "candidate": source_candidate},
                    ),
                    source=source_error.source,
                    source_adjudication=source_error.source_adjudication,
                    dispute=source_error.dispute,
                    selected_run_index=(
                        1 if source_error.source_adjudication is not None else None
                    ),
                    validation_status="reusable_source_handoff",
                )
                _write(output_path, receipt)
                raise CompletionStageIncomplete(
                    "completed source authority requires bounded graph completion",
                    receipt=receipt,
                ) from error
            raise error

        full_candidate = _mapping(
            full.get("candidate"), "partitioned full-graph hypothesis"
        )
        full_error: ValueError | None = None
        try:
            _require_candidate(candidate_validator, full_candidate, "full_graph")
        except ValueError as error:
            full_error = error
            attempts.append(
                _completed_hypothesis_run(
                    0, "full_graph", full, status="comparison_rejected", error=error
                )
            )
        else:
            attempts.append(
                _completed_hypothesis_run(0, "full_graph", full, status="comparison_passed")
            )
        try:
            source_only = _wait_for_hypothesis(
                source_future,
                cancel_event=cancel_event,
                run_cancellations=run_cancellations,
            )
        except StructuredSourceHypothesisRejected as error:
            source_only = {
                "source": error.source,
                "usage": error.usage,
                "wall_ms": error.wall_ms,
                "prompt_text": error.prompt_text,
            }
            if full_error is not None:
                raise full_error
            attempts.append(
                _completed_hypothesis_run(
                    1,
                    "source_only",
                    source_only,
                    status="source_pair_disagreement",
                    error=error,
                )
            )
            paired_candidate = {
                "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
                "source": error.source,
                "completion": _mapping(
                    full_candidate.get("completion"),
                    "full-graph completion hypothesis",
                ),
            }
            receipt = _source_pair_handoff_receipt(
                case_id=case_id,
                host_profile=host_profile,
                model=model,
                reasoning_effort=reasoning_effort,
                model_budget_seconds=model_budget_seconds,
                started_ns=started_ns,
                attempts=attempts,
                source_only=source_only,
                hypothesis_candidates=(
                    {"run_index": 0, "hypothesis_mode": "full_graph",
                     "candidate": full_candidate},
                    {"run_index": 1, "hypothesis_mode": "source_only",
                     "candidate": paired_candidate},
                ),
                source=error.source,
                source_adjudication=None,
                dispute="source_authority",
                selected_run_index=None,
                validation_status="reusable_source_pair",
            )
            _write(output_path, receipt)
            raise CompletionStageIncomplete(
                "structured source hypotheses require bounded pair adjudication",
                receipt=receipt,
            ) from error
        except Exception:
            attempts.append(_failed_hypothesis_run(1, "source_only"))
            if full_error is not None:
                raise full_error
            raise
        paired_candidate = {
            "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
            "source": _mapping(
                source_only.get("source"), "source-only graph hypothesis"
            ),
            "completion": _mapping(
                full_candidate.get("completion"), "full-graph completion hypothesis"
            ),
        }
        try:
            _require_candidate(candidate_validator, paired_candidate, "source_only")
        except ReusableSourcePairDisagreement as error:
            attempts.append(
                _completed_hypothesis_run(
                    1,
                    "source_only",
                    source_only,
                    status="source_pair_disagreement",
                    error=error,
                )
            )
            receipt = _source_pair_handoff_receipt(
                case_id=case_id,
                host_profile=host_profile,
                model=model,
                reasoning_effort=reasoning_effort,
                model_budget_seconds=model_budget_seconds,
                started_ns=started_ns,
                attempts=attempts,
                source_only=source_only,
                hypothesis_candidates=(
                    {"run_index": 0, "hypothesis_mode": "full_graph",
                     "candidate": full_candidate},
                    {"run_index": 1, "hypothesis_mode": "source_only",
                     "candidate": paired_candidate},
                ),
                source=error.source,
                source_adjudication=error.source_adjudication,
                dispute=error.dispute,
                selected_run_index=1,
                validation_status="reusable_source_pair",
            )
            _write(output_path, receipt)
            raise CompletionStageIncomplete(
                "validated source authority requires bounded completion adjudication",
                receipt=receipt,
            ) from error
        attempts.append(
            _completed_hypothesis_run(
                1, "source_only", source_only, status="selected"
            )
        )
        reasoning = {
            "candidate": paired_candidate,
            "wall_ms": max(int(full["wall_ms"]), int(source_only["wall_ms"])),
            "usage": _combined_usage(
                _mapping(full.get("usage"), "full-graph usage"),
                _mapping(source_only.get("usage"), "source-only usage"),
            ),
            "prompt_text": str(source_only["prompt_text"]),
        }
        winner_index = 1
    candidate = _mapping(
        reasoning.get("candidate"), "partitioned full-graph hypothesis"
    )
    source = _mapping(candidate.get("source"), "whole-source hypothesis")
    receipt = _stage_receipt(
        stage="source_hypothesis",
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        model_budget_seconds=model_budget_seconds,
        wall_ms=max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000),
        usage=_combined_usage(
            *(
                _mapping(attempt.get("usage"), "source hypothesis usage")
                for attempt in attempts
            )
        ),
        prompt_text=str(reasoning["prompt_text"]),
        candidate=candidate,
    )
    receipt["model_call_count"] = 2
    receipt["hypothesis_runs"] = sorted(
        attempts, key=lambda attempt: int(attempt["run_index"])
    )
    receipt["selected_run_index"] = winner_index
    receipt["source"] = source
    receipt["partitioned_candidate"] = candidate
    receipt["partitioned_candidates"] = [
        {
            "run_index": 0,
            "hypothesis_mode": "full_graph",
            "candidate": full_candidate,
            "wall_ms": int(full["wall_ms"]),
            "usage": dict(_mapping(full.get("usage"), "full-graph usage")),
            "prompt_text": str(full["prompt_text"]),
        },
        {
            "run_index": 1,
            "hypothesis_mode": "source_only",
            "candidate": paired_candidate,
            "wall_ms": int(source_only["wall_ms"]),
            "usage": dict(
                _mapping(source_only.get("usage"), "source-only usage")
            ),
            "prompt_text": str(source_only["prompt_text"]),
        },
    ]
    receipt["validation_status"] = "passed"
    receipt["validation_error"] = ""
    _write(output_path, receipt)
    return receipt


def _wait_for_hypothesis(
    future: Future[dict[str, Any]],
    *,
    cancel_event: Event | None,
    run_cancellations: tuple[Event, Event],
) -> dict[str, Any]:
    """Wait while forwarding an outer clarification or deadline cancellation."""

    while True:
        if cancel_event is not None and cancel_event.is_set():
            for event in run_cancellations:
                event.set()
        try:
            return future.result(timeout=0.05)
        except FutureTimeout:
            continue


def _source_pair_handoff_receipt(
    *, case_id: str, host_profile: str, model: str, reasoning_effort: str,
    model_budget_seconds: int, started_ns: int,
    attempts: Sequence[Mapping[str, Any]], source_only: Mapping[str, Any],
    hypothesis_candidates: Sequence[Mapping[str, Any]],
    source: Mapping[str, Any], source_adjudication: Mapping[str, Any] | None,
    dispute: str, selected_run_index: int | None, validation_status: str,
) -> dict[str, Any]:
    receipt = _stage_receipt(
        stage="source_hypothesis",
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        model_budget_seconds=model_budget_seconds,
        wall_ms=max(
            1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000
        ),
        usage=_combined_usage(
            *(
                _mapping(attempt.get("usage"), "source hypothesis usage")
                for attempt in attempts
            )
        ),
        prompt_text=str(source_only["prompt_text"]),
        candidate=_mapping(
            hypothesis_candidates[-1].get("candidate"), "handoff candidate"
        ),
    )
    receipt.update(
        {
            "model_call_count": 2,
            "hypothesis_runs": sorted(
                (dict(attempt) for attempt in attempts),
                key=lambda attempt: int(attempt["run_index"]),
            ),
            "selected_run_index": selected_run_index,
            "source": dict(source),
            "source_candidate_adjudication": (
                dict(source_adjudication)
                if source_adjudication is not None
                else None
            ),
            "source_pair_dispute": dispute,
            "hypothesis_candidates": [dict(row) for row in hypothesis_candidates],
            "validation_status": validation_status,
            "validation_error": str(attempts[-1].get("validation_error") or ""),
        }
    )
    return receipt


def _require_candidate(
    validator: Callable[[Mapping[str, Any], str], None] | None,
    candidate: Mapping[str, Any],
    hypothesis_mode: str,
) -> None:
    if validator is not None:
        validator(candidate, hypothesis_mode)


def _completed_hypothesis_run(
    run_index: int,
    hypothesis_mode: str,
    result: Mapping[str, Any],
    *,
    status: str,
    error: Exception | None = None,
) -> dict[str, Any]:
    row = {
        "run_index": run_index,
        "hypothesis_mode": hypothesis_mode,
        "status": status,
        "wall_ms": int(result["wall_ms"]),
        "usage": dict(_mapping(result.get("usage"), "hypothesis usage")),
    }
    if error is not None:
        row["validation_error"] = str(error)
    return row


def _failed_hypothesis_run(run_index: int, hypothesis_mode: str) -> dict[str, Any]:
    return {
        "run_index": run_index,
        "hypothesis_mode": hypothesis_mode,
        "status": "failed",
        "usage": {},
    }


def _settle_unused_hypothesis(
    future: Future[dict[str, Any]],
    *,
    run_index: int = 1,
    hypothesis_mode: str = "source_only",
) -> dict[str, Any]:
    try:
        result = future.result()
    except HostStageCancelled:
        return {
            "run_index": run_index,
            "hypothesis_mode": hypothesis_mode,
            "status": "cancelled",
            "usage": {},
        }
    except Exception:
        return {
            "run_index": run_index,
            "hypothesis_mode": hypothesis_mode,
            "status": "failed_not_selected",
            "usage": {},
        }
    return _completed_hypothesis_run(
        run_index,
        hypothesis_mode,
        result,
        status="completed_not_selected",
    )


def case_prompt(*, corpus_path: Path, case_id: str) -> str:
    """Load one development prompt without reading expected annotations."""

    corpus = _mapping(json.loads(corpus_path.read_text(encoding="utf-8")), "corpus")
    cases = _rows(corpus.get("cases"), "corpus cases")
    matches = [row for row in cases if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise RuntimeError(f"development corpus does not contain one case: {case_id}")
    prompt = str(matches[0].get("prompt") or "").strip()
    if not prompt:
        raise RuntimeError("development case prompt is empty")
    return prompt


def _combined_usage(*rows: Mapping[str, Any]) -> dict[str, int]:
    keys = {key for row in rows for key, value in row.items() if isinstance(value, int)}
    return {key: sum(int(row.get(key, 0)) for row in rows) for key in sorted(keys)}


def _stage_receipt(
    *, stage: str, case_id: str, host_profile: str, model: str,
    reasoning_effort: str,
    model_budget_seconds: int, wall_ms: int, usage: Mapping[str, Any],
    prompt_text: str, candidate: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "version": EXPERIMENT_VERSION,
        "stage": stage,
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": wall_ms,
        "usage": dict(usage),
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "candidate": dict(candidate),
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


__all__ = [
    "CompletionStageIncomplete", "ReusableSourcePairDisagreement", "case_prompt",
    "run_hedged_source_graph_hypothesis_case",
]
