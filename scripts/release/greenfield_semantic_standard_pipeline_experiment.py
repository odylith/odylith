"""Run one holistic graph author under the strict standard deadline."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_authoring_wave import (
    AUTHOR_MAX_SECONDS,
    AuthoringWaveBudget,
    run_authoring_wave,
)
from greenfield_semantic_case_evidence import case_prompt
from greenfield_semantic_pipeline_receipts import (
    pipeline_receipt,
    write_receipt,
)
from greenfield_semantic_structured_host import elapsed_ms
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    STANDARD_COMPLETION_DEADLINE_SECONDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_intent_packet,
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)


DETERMINISTIC_RESERVE_SECONDS = 5
STANDARD_AUTHORING_SECONDS = AUTHOR_MAX_SECONDS


def standard_budget_contract() -> dict[str, Any]:
    """Return the measured 54+5 allocation strictly below 60 seconds."""

    critical_path = STANDARD_AUTHORING_SECONDS + DETERMINISTIC_RESERVE_SECONDS
    if critical_path >= STANDARD_COMPLETION_DEADLINE_SECONDS:
        raise RuntimeError("standard pipeline allocation does not finish before 60 seconds")
    return {
        "tier": "standard",
        "deadline_seconds": STANDARD_COMPLETION_DEADLINE_SECONDS,
        "comparison": "strictly_less_than",
        "semantic_authoring_seconds": STANDARD_AUTHORING_SECONDS,
        "source_meaning_author_max_seconds": AUTHOR_MAX_SECONDS,
        "successful_model_call_counts": {"commit": [1], "clarify": [1]},
        "source_authority": "one_unchanged_source_meaning_graph",
        "packet_and_transaction_reserve_seconds": DETERMINISTIC_RESERVE_SECONDS,
        "critical_path_seconds": critical_path,
        "retries": 0,
        "critics": 0,
        "selectors": 0,
        "merges": 0,
        "automatic_deep_tier": False,
        "topology_mode": "single_system",
    }


def run_standard_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    host_profile: str = "codex",
    _author_budget: int = STANDARD_AUTHORING_SECONDS,
    _deadline_seconds: int = STANDARD_COMPLETION_DEADLINE_SECONDS,
    _budget_contract: Mapping[str, Any] | None = None,
    _topology_mode: str = "single_system",
    _evidence_assignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one no-retry semantic call and deterministic completion."""

    standard_host_stage_profile(host_profile)
    started_ns = time.monotonic_ns()
    budget = dict(_budget_contract or standard_budget_contract())
    if _evidence_assignment is not None:
        budget["evidence_assignment"] = dict(_evidence_assignment)
    author, failure = run_authoring_wave(
        corpus_path=corpus_path,
        case_id=case_id,
        host_profile=host_profile,
        budget=AuthoringWaveBudget(
            author_seconds=min(AUTHOR_MAX_SECONDS, _author_budget),
            topology_mode=_topology_mode,
        ),
    )
    if failure is not None:
        failure_kind, failed_stage, message = failure
        outcome = (
            "standard_deadline_exceeded"
            if failure_kind == "deadline"
            else "typed_standard_failure"
            if failure_kind == "typed"
            else "environment_failure"
        )
        return write_receipt(
            output_path,
            pipeline_receipt(
                case_id=case_id,
                status="failed",
                outcome=outcome,
                wall_ms=elapsed_ms(started_ns),
                host_profile=host_profile,
                budget=budget,
                author=author,
                packet=None,
                transaction=None,
                failed_stage=failed_stage,
                failure=message,
            ),
        )
    assert author is not None
    prompt = case_prompt(corpus_path=corpus_path, case_id=case_id)
    try:
        packet = _finalize_author(prompt=prompt, author=author)
    except ValueError as error:
        return _failure(
            output_path=output_path,
            case_id=case_id,
            outcome="typed_standard_failure",
            started_ns=started_ns,
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=None,
            failed_stage="source_meaning_projection",
            failure=str(error),
        )
    if packet["semantic_intent"]["status"] == "clarification_required":
        wall_ms = elapsed_ms(started_ns)
        status = "completed" if wall_ms < _deadline_seconds * 1000 else "failed"
        return write_receipt(
            output_path,
            pipeline_receipt(
                case_id=case_id,
                status=status,
                outcome="clarify" if status == "completed" else "standard_deadline_exceeded",
                wall_ms=wall_ms,
                host_profile=host_profile,
                budget=budget,
                author=author,
                packet=packet,
                transaction=None,
                failed_stage="" if status == "completed" else "deadline",
                failure="" if status == "completed" else "clarification completed after 60 seconds",
            ),
        )
    if _remaining_ms(started_ns, _deadline_seconds) <= DETERMINISTIC_RESERVE_SECONDS * 1000:
        return write_receipt(
            output_path,
            pipeline_receipt(
                case_id=case_id,
                status="rescue_required",
                outcome="deterministic_finalize_required",
                wall_ms=elapsed_ms(started_ns),
                host_profile=host_profile,
                budget=budget,
                author=author,
                packet=packet,
                transaction=None,
                failed_stage="deadline",
                failure="standard path left no transaction-safe finalize budget",
            ),
        )
    try:
        with tempfile.TemporaryDirectory(
            prefix="odylith-standard-pipeline-"
        ) as temporary:
            transaction = _compile_packet(
                packet=packet,
                prompt=prompt,
                repo_root=Path(temporary) / "consumer",
            )
    except ValueError as error:
        return _failure(
            output_path=output_path,
            case_id=case_id,
            outcome="typed_standard_failure",
            started_ns=started_ns,
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=packet,
            failed_stage="transaction",
            failure=str(error),
        )
    except (ImportError, OSError, RuntimeError) as error:
        return _failure(
            output_path=output_path,
            case_id=case_id,
            outcome="environment_failure",
            started_ns=started_ns,
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=packet,
            failed_stage="transaction",
            failure=f"{type(error).__name__}: {error}",
        )
    wall_ms = elapsed_ms(started_ns)
    completed = wall_ms < _deadline_seconds * 1000
    return write_receipt(
        output_path,
        pipeline_receipt(
            case_id=case_id,
            status="completed" if completed else "rescue_required",
            outcome="commit" if completed else "deterministic_settlement_required",
            wall_ms=wall_ms,
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=packet,
            transaction=transaction,
            failed_stage="" if completed else "transaction_settlement",
            failure="" if completed else "transaction completed after 60 seconds",
        ),
    )


def _finalize_author(
    *, prompt: str, author: Mapping[str, Any]
) -> dict[str, Any]:
    return build_semantic_intent_packet(
        author["graph"], prompt=prompt, author_run=author["author_run"]
    )


def _compile_packet(
    *, packet: Mapping[str, Any], prompt: str, repo_root: Path
) -> dict[str, Any]:
    repo_root.mkdir(parents=True, exist_ok=True)
    verified = require_semantic_intent_packet(packet, prompt=prompt)
    authority = semantic_intent_authority(verified, prompt=prompt)
    proposal = build_verified_semantic_proposal_for_repo(
        repo_root=repo_root, authority=authority, release_selector="0.0.1"
    )
    transaction = compile_verified_semantic_transaction(
        repo_root=repo_root,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )
    summary = transaction.summary()
    if summary.get("verified") is not True:
        raise RuntimeError("production transaction is not verified")
    return {
        **summary,
        "review_package": dict(transaction.prewrite_package.proposal),
        "transaction_payload": product_create_transaction_to_dict(transaction),
    }


def _remaining_ms(started_ns: int, deadline_seconds: int) -> int:
    return max(0, deadline_seconds * 1000 - elapsed_ms(started_ns))


def _failure(
    *,
    output_path: Path,
    case_id: str,
    outcome: str,
    started_ns: int,
    host_profile: str,
    budget: Mapping[str, Any],
    author: Mapping[str, Any] | None,
    packet: Mapping[str, Any] | None,
    failed_stage: str,
    failure: str,
) -> dict[str, Any]:
    return write_receipt(
        output_path,
        pipeline_receipt(
            case_id=case_id,
            status="failed",
            outcome=outcome,
            wall_ms=elapsed_ms(started_ns),
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=packet,
            transaction=None,
            failed_stage=failed_stage,
            failure=failure,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--host-profile", choices=("codex", "claude"), default="codex")
    args = parser.parse_args(argv)
    receipt = run_standard_pipeline(
        corpus_path=args.corpus,
        case_id=args.case_id,
        output_path=args.output,
        host_profile=args.host_profile,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DETERMINISTIC_RESERVE_SECONDS",
    "STANDARD_AUTHORING_SECONDS",
    "_compile_packet",
    "_finalize_author",
    "run_standard_pipeline",
    "standard_budget_contract",
]
