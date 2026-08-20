"""Continue the active Greenfield mechanism after one reusable standard handoff."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_authoring_wave import (
    run_final_adjudication_from_hypotheses,
)
from greenfield_semantic_pipeline_receipts import (
    bounded_receipt,
    pipeline_receipt,
    write_receipt,
)
from greenfield_semantic_release_support import (
    greenfield_runtime_source_fingerprint,
    mapping,
)
from greenfield_semantic_standard_path_experiment import case_prompt
from greenfield_semantic_source_pair_adjudicator import (
    run_source_pair_adjudication,
)
from greenfield_semantic_standard_pipeline_experiment import (
    DETERMINISTIC_RESERVE_SECONDS,
    MIN_STANDARD_AUTHOR_SECONDS,
    _assessment_result,
    _compile_packet,
    _critic_run_id,
    _finalize_author,
    _materiality_run_id,
)
from greenfield_semantic_structured_host import HostStageTimeout, elapsed_ms
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    RESCUE_COMPLETION_DEADLINE_SECONDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    require_reusable_standard_handoff,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_clarification_packet,
)


def rescue_budget_contract(
    *, prior_standard_failure_sha256: str, prior_standard_wall_ms: int
) -> dict[str, Any]:
    """Allocate only the unused portion of the cumulative 90-second envelope."""

    remaining_ms = RESCUE_COMPLETION_DEADLINE_SECONDS * 1000 - prior_standard_wall_ms
    final_seconds = (remaining_ms - DETERMINISTIC_RESERVE_SECONDS * 1000) // 1000
    if final_seconds < MIN_STANDARD_AUTHOR_SECONDS:
        raise ValueError("standard handoff leaves no bounded rescue adjudication budget")
    return {
        "tier": "rescue",
        "deadline_seconds": RESCUE_COMPLETION_DEADLINE_SECONDS,
        "comparison": "less_than_or_equal",
        "reused_standard_hypotheses": True,
        "continuation_final_adjudication_seconds": final_seconds,
        "packet_and_transaction_reserve_seconds": DETERMINISTIC_RESERVE_SECONDS,
        "cumulative_prior_standard_wall_ms": prior_standard_wall_ms,
        "critical_path_ms": (
            prior_standard_wall_ms
            + final_seconds * 1000
            + DETERMINISTIC_RESERVE_SECONDS * 1000
        ),
        "retries": 0,
        "automatic_deep_tier": False,
        "topology_mode": "adaptive",
        "prior_standard_failure_sha256": prior_standard_failure_sha256,
    }


def run_rescue_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    standard_failure_receipt: Mapping[str, Any],
    host_profile: str = "codex",
    final_adjudicator_model: str = "",
    final_adjudicator_reasoning_effort: str = "",
    evidence_assignment: Mapping[str, Any] | None = None,
    **retired_stage_overrides: str,
) -> dict[str, Any]:
    """Continue once from two validated hypotheses; never restart the first wave."""

    if any(retired_stage_overrides.values()):
        raise ValueError("rescue cannot replace or rerun standard hypotheses")
    predecessor = dict(standard_failure_receipt)
    predecessor_sha256 = require_reusable_standard_handoff(
        predecessor, case_id=case_id
    )
    prior_execution = mapping(
        predecessor.get("mechanism_execution"), "standard execution evidence"
    )
    if prior_execution.get(
        "implementation_fingerprint_sha256"
    ) != greenfield_runtime_source_fingerprint():
        raise ValueError("rescue handoff was produced by different implementation bytes")
    if prior_execution.get("host_profile") != host_profile:
        raise ValueError("rescue host profile differs from its standard handoff")
    prior_wall_ms = int(predecessor.get("wall_ms") or -1)
    if prior_wall_ms != int(prior_execution.get("wall_ms") or -2):
        raise ValueError("rescue predecessor wall time is inconsistent")
    critic = mapping(predecessor.get("materiality_critic"), "materiality critic")
    source = mapping(predecessor.get("source_hypothesis"), "source hypothesis")
    profile = standard_host_stage_profile(host_profile)
    model = final_adjudicator_model or profile["final_adjudicator_model"]
    reasoning_effort = (
        final_adjudicator_reasoning_effort
        or profile["final_adjudicator_reasoning_effort"]
    )
    budget = rescue_budget_contract(
        prior_standard_failure_sha256=predecessor_sha256,
        prior_standard_wall_ms=prior_wall_ms,
    )
    if evidence_assignment is not None:
        budget["evidence_assignment"] = dict(evidence_assignment)
    continuation_started_ns = time.monotonic_ns()
    if predecessor.get("failed_stage") == "graph_completion":
        try:
            author = run_source_pair_adjudication(
                corpus_path=corpus_path,
                case_id=case_id,
                critic=critic,
                source_receipt=source,
                host_profile=host_profile,
                model=model,
                reasoning_effort=reasoning_effort,
                budget_seconds=int(
                    budget["continuation_final_adjudication_seconds"]
                ),
            )
            failure = None
        except HostStageTimeout as error:
            author = None
            failure = ("deadline", "final_graph_adjudication", str(error))
        except ValueError as error:
            author = None
            failure = ("typed", "final_graph_adjudication", str(error))
        except RuntimeError as error:
            author = None
            failure = ("environment", "final_graph_adjudication", str(error))
    else:
        author, failure = run_final_adjudication_from_hypotheses(
            corpus_path=corpus_path,
            case_id=case_id,
            critic=critic,
            source=source,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=int(
                budget["continuation_final_adjudication_seconds"]
            ),
            topology_mode="adaptive",
        )
    if failure is not None:
        kind, stage, message = failure
        return _bounded_result(
            output_path=output_path,
            case_id=case_id,
            prior_wall_ms=prior_wall_ms,
            continuation_started_ns=continuation_started_ns,
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=None,
            finalized=None,
            transaction=None,
            status="failed",
            outcome={
                "deadline": "rescue_deadline_exceeded",
                "typed": "typed_rescue_failure",
                "environment": "environment_failure",
            }[kind],
            failed_stage=stage,
            failure=message,
        )
    prompt = case_prompt(corpus_path=corpus_path, case_id=case_id)
    assessment, assessment_error = _assessment_result(
        corpus_path=corpus_path,
        case_id=case_id,
        source=mapping(author, "final graph adjudication"),
    )
    if assessment_error:
        return _bounded_result(
            output_path=output_path,
            case_id=case_id,
            prior_wall_ms=prior_wall_ms,
            continuation_started_ns=continuation_started_ns,
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=None,
            finalized=None,
            transaction=None,
            status="failed",
            outcome="typed_rescue_failure",
            failed_stage="materiality_critic",
            failure=assessment_error,
        )
    try:
        if assessment["decision"] == "clarification_required":
            finalized = {
                "packet": build_semantic_clarification_packet(
                    assessment,
                    prompt=prompt,
                    critic_run_id=_critic_run_id(critic),
                    author_run_id=_materiality_run_id(
                        mapping(author, "final graph adjudication")
                    ),
                    critic_host_profile=host_profile,
                )
            }
            transaction = None
            outcome = "clarify"
        else:
            finalized = _finalize_author(
                case_id=case_id,
                prompt=prompt,
                assessment=assessment,
                author=mapping(author, "final graph adjudication"),
                critic_run_id=_critic_run_id(critic),
                semantic_host_profile=host_profile,
            )
            with tempfile.TemporaryDirectory(prefix="odylith-rescue-continuation-") as temporary:
                transaction = _compile_packet(
                    packet=finalized["packet"],
                    prompt=prompt,
                    repo_root=Path(temporary) / "consumer",
                )
            outcome = "commit"
    except ValueError as error:
        return _bounded_result(
            output_path=output_path,
            case_id=case_id,
            prior_wall_ms=prior_wall_ms,
            continuation_started_ns=continuation_started_ns,
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=assessment,
            finalized=None,
            transaction=None,
            status="failed",
            outcome="typed_rescue_failure",
            failed_stage="graph_completion",
            failure=str(error),
        )
    except (ImportError, OSError, RuntimeError) as error:
        return _bounded_result(
            output_path=output_path,
            case_id=case_id,
            prior_wall_ms=prior_wall_ms,
            continuation_started_ns=continuation_started_ns,
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=assessment,
            finalized=None,
            transaction=None,
            status="failed",
            outcome="environment_failure",
            failed_stage="transaction",
            failure=f"{type(error).__name__}: {error}",
        )
    total_wall_ms = prior_wall_ms + elapsed_ms(continuation_started_ns)
    completed = total_wall_ms <= RESCUE_COMPLETION_DEADLINE_SECONDS * 1000
    return _bounded_result(
        output_path=output_path,
        case_id=case_id,
        prior_wall_ms=prior_wall_ms,
        continuation_started_ns=continuation_started_ns,
        host_profile=host_profile,
        budget=budget,
        critic=critic,
        source=source,
        author=author,
        assessment=assessment,
        finalized=finalized,
        transaction=transaction,
        status="completed" if completed else "failed",
        outcome=outcome if completed else "rescue_deadline_exceeded",
        failed_stage="" if completed else "deadline",
        failure="" if completed else "rescue continuation completed after 90 seconds",
    )


def _bounded_result(
    *,
    output_path: Path,
    case_id: str,
    prior_wall_ms: int,
    continuation_started_ns: int,
    host_profile: str,
    budget: Mapping[str, Any],
    critic: Mapping[str, Any],
    source: Mapping[str, Any],
    author: Mapping[str, Any] | None,
    assessment: Mapping[str, Any] | None,
    finalized: Mapping[str, Any] | None,
    transaction: Mapping[str, Any] | None,
    status: str,
    outcome: str,
    failed_stage: str,
    failure: str,
) -> dict[str, Any]:
    total_wall_ms = prior_wall_ms + elapsed_ms(continuation_started_ns)
    attempt = pipeline_receipt(
        case_id=case_id,
        status=status,
        outcome=outcome,
        wall_ms=total_wall_ms,
        host_profile=host_profile,
        budget=budget,
        critic=critic,
        source=source,
        author=author,
        assessment=assessment,
        finalized=finalized,
        transaction=transaction,
        failed_stage=failed_stage,
        failure=failure,
    )
    return write_receipt(
        output_path,
        bounded_receipt(
            case_id=case_id,
            tier="rescue" if status == "completed" else "failed",
            wall_ms=total_wall_ms,
            attempt=attempt,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--standard-failure", type=Path, required=True)
    parser.add_argument("--host-profile", choices=("codex", "claude"), default="codex")
    args = parser.parse_args(argv)
    receipt = run_rescue_pipeline(
        corpus_path=args.corpus,
        case_id=args.case_id,
        output_path=args.output,
        standard_failure_receipt=json.loads(
            args.standard_failure.read_text(encoding="utf-8")
        ),
        host_profile=args.host_profile,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["rescue_budget_contract", "run_rescue_pipeline"]
