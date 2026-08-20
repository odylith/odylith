"""Run the production Greenfield mechanism under standard and rescue deadlines."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_authoring_wave import AuthoringWaveBudget, run_authoring_wave
from greenfield_semantic_standard_path_experiment import (
    case_prompt,
)
from greenfield_semantic_pipeline_receipts import (
    PIPELINE_VERSION,
    pipeline_receipt as _receipt,
    write_receipt as _write_receipt,
)
from greenfield_semantic_release_support import mapping
from greenfield_semantic_structured_host import elapsed_ms
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    STANDARD_COMPLETION_DEADLINE_SECONDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    build_semantic_clarification_packet,
    build_semantic_intent_packet,
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_candidates_from_catalog,
    atomic_source_candidates_without_discarded,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    assemble_parallel_materiality_assessment,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)


PARALLEL_HYPOTHESIS_HOST_TIMEOUT_SECONDS = 48
SEMANTIC_AUTHORING_SHARED_SECONDS = 48
CLARIFICATION_AUTHORING_SHARED_SECONDS = 58
DETERMINISTIC_RESERVE_SECONDS = 11
CLARIFICATION_FINALIZE_RESERVE_SECONDS = 1
MIN_STANDARD_AUTHOR_SECONDS = 20


def standard_budget_contract() -> dict[str, Any]:
    """Return the non-negotiable standard allocation including transaction work."""
    commit_path = SEMANTIC_AUTHORING_SHARED_SECONDS + DETERMINISTIC_RESERVE_SECONDS
    clarification_path = (
        CLARIFICATION_AUTHORING_SHARED_SECONDS
        + CLARIFICATION_FINALIZE_RESERVE_SECONDS
    )
    critical_path = max(commit_path, clarification_path)
    if critical_path >= STANDARD_COMPLETION_DEADLINE_SECONDS:
        raise RuntimeError("standard pipeline allocation does not finish before 60 seconds")
    return {
        "tier": "standard",
        "deadline_seconds": STANDARD_COMPLETION_DEADLINE_SECONDS,
        "comparison": "strictly_less_than",
        "parallel_model_host_timeout_seconds": (
            PARALLEL_HYPOTHESIS_HOST_TIMEOUT_SECONDS
        ),
        "all_model_calls_start_at_entry": True,
        "standard_model_call_count": 3,
        "commit_semantic_authoring_shared_seconds": SEMANTIC_AUTHORING_SHARED_SECONDS,
        "clarification_semantic_authoring_shared_seconds": (
            CLARIFICATION_AUTHORING_SHARED_SECONDS
        ),
        "candidate_admission": "paired_source_and_completion_end_to_end_packet",
        "packet_and_transaction_reserve_seconds": DETERMINISTIC_RESERVE_SECONDS,
        "clarification_packet_reserve_seconds": CLARIFICATION_FINALIZE_RESERVE_SECONDS,
        "critical_path_seconds": critical_path,
        "retries": 0,
        "automatic_deep_tier": False,
        "topology_mode": "single_system",
    }


def run_standard_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    host_profile: str = "codex",
    critic_model: str = "",
    critic_reasoning_effort: str = "",
    source_hypothesis_model: str = "",
    source_hypothesis_reasoning_effort: str = "",
    final_adjudicator_model: str = "",
    final_adjudicator_reasoning_effort: str = "",
    _first_wave_budget: int = PARALLEL_HYPOTHESIS_HOST_TIMEOUT_SECONDS,
    _semantic_budget: int = SEMANTIC_AUTHORING_SHARED_SECONDS,
    _clarification_semantic_budget: int = CLARIFICATION_AUTHORING_SHARED_SECONDS,
    _deadline_seconds: int = STANDARD_COMPLETION_DEADLINE_SECONDS,
    _budget_contract: Mapping[str, Any] | None = None,
    _topology_mode: str = "single_system",
    _evidence_assignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one no-retry attempt and return a terminal or typed rescue handoff."""

    profile = standard_host_stage_profile(host_profile)
    critic_model = critic_model or profile["critic_model"]
    critic_reasoning_effort = critic_reasoning_effort or profile["critic_reasoning_effort"]
    source_hypothesis_model = (
        source_hypothesis_model or profile["source_hypothesis_model"]
    )
    source_hypothesis_reasoning_effort = (
        source_hypothesis_reasoning_effort
        or profile["source_hypothesis_reasoning_effort"]
    )
    final_adjudicator_model = (
        final_adjudicator_model or profile["final_adjudicator_model"]
    )
    final_adjudicator_reasoning_effort = (
        final_adjudicator_reasoning_effort
        or profile["final_adjudicator_reasoning_effort"]
    )
    started_ns = time.monotonic_ns()
    budget = dict(_budget_contract or standard_budget_contract())
    if _evidence_assignment is not None:
        budget["evidence_assignment"] = dict(_evidence_assignment)
    with tempfile.TemporaryDirectory(prefix="odylith-standard-pipeline-") as temporary:
        root = Path(temporary)
        critic, source, author, failure = run_authoring_wave(
            corpus_path=corpus_path,
            case_id=case_id,
            root=root,
            host_profile=host_profile,
            critic_model=critic_model,
            critic_reasoning_effort=critic_reasoning_effort,
            source_hypothesis_model=source_hypothesis_model,
            source_hypothesis_reasoning_effort=source_hypothesis_reasoning_effort,
            final_adjudicator_model=final_adjudicator_model,
            final_adjudicator_reasoning_effort=final_adjudicator_reasoning_effort,
            budget=AuthoringWaveBudget(
                first_wave_seconds=_first_wave_budget,
                commit_semantic_seconds=_semantic_budget,
                clarification_semantic_seconds=_clarification_semantic_budget,
                topology_mode=_topology_mode,
            ),
        )
        if failure is not None:
            failure_kind, failed_stage, message = failure
            status = "rescue_required" if failure_kind == "handoff" else "failed"
            outcome = (
                "typed_standard_handoff"
                if failure_kind == "handoff" and failed_stage == "graph_completion"
                else "standard_deadline_exceeded"
                if failure_kind in {"handoff", "deadline"}
                else "typed_standard_failure"
                if failure_kind == "typed"
                else "environment_failure"
            )
            return _write_receipt(
                output_path,
                _receipt(
                    case_id=case_id,
                    status=status,
                    outcome=outcome,
                    wall_ms=elapsed_ms(started_ns),
                    host_profile=host_profile,
                    budget=budget,
                    critic=critic,
                    source=source,
                    author=author,
                    assessment=None,
                    finalized=None,
                    transaction=None,
                    failed_stage=failed_stage,
                    failure=message,
                ),
            )
        assessment, assessment_error = _assessment_result(
            corpus_path=corpus_path,
            case_id=case_id,
            source=mapping(author, "final graph adjudication"),
        )
        if assessment_error:
            return _terminal_failure(
                output_path=output_path,
                case_id=case_id,
                status="rescue_required",
                outcome="typed_standard_failure",
                started_ns=started_ns,
                host_profile=host_profile,
                budget=budget,
                critic=critic,
                source=source,
                author=author,
                assessment=None,
                failed_stage="materiality_critic",
                failure=assessment_error,
            )
        if assessment["decision"] == "clarification_required":
            prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
            packet = build_semantic_clarification_packet(
                assessment,
                prompt=prompt_text,
                critic_run_id=_critic_run_id(mapping(critic, "materiality critic")),
                author_run_id=_materiality_run_id(
                    mapping(author, "final graph adjudication")
                ),
                critic_host_profile=host_profile,
            )
            return _write_receipt(
                output_path,
                _receipt(
                    case_id=case_id,
                    status="completed",
                    outcome="clarify",
                    wall_ms=elapsed_ms(started_ns),
                    host_profile=host_profile,
                    budget=budget,
                    critic=critic,
                    source=source,
                    author=author,
                    assessment=assessment,
                    finalized={"packet": packet},
                    transaction=None,
                    failed_stage="",
                    failure="",
                ),
            )
        if _remaining_finalize_seconds(started_ns, _deadline_seconds) <= DETERMINISTIC_RESERVE_SECONDS:
            return _terminal_failure(
                output_path=output_path,
                case_id=case_id,
                status="failed",
                outcome="standard_deadline_exhausted",
                started_ns=started_ns,
                host_profile=host_profile,
                budget=budget,
                critic=critic,
                source=source,
                author=author,
                assessment=assessment,
                failed_stage="deadline",
                failure="standard path left no transaction-safe finalize budget",
            )
        try:
            finalized = _finalize_author(
                case_id=case_id,
                prompt=case_prompt(corpus_path=corpus_path, case_id=case_id),
                assessment=assessment,
                author=mapping(author, "final graph adjudication"),
                critic_run_id=_critic_run_id(mapping(critic, "materiality critic")),
                semantic_host_profile=host_profile,
            )
        except ValueError as error:
            return _terminal_failure(
                output_path=output_path,
                case_id=case_id,
                status="rescue_required",
                outcome="typed_standard_failure",
                started_ns=started_ns,
                host_profile=host_profile,
                budget=budget,
                critic=critic,
                source=source,
                author=author,
                assessment=assessment,
                failed_stage="graph_completion",
                failure=str(error),
            )
        try:
            transaction = _compile_packet(
                packet=finalized["packet"],
                prompt=case_prompt(corpus_path=corpus_path, case_id=case_id),
                repo_root=root / "consumer",
            )
        except ValueError as error:
            return _terminal_failure(
                output_path=output_path,
                case_id=case_id,
                status="rescue_required",
                outcome="typed_standard_failure",
                started_ns=started_ns,
                host_profile=host_profile,
                budget=budget,
                critic=critic,
                source=source,
                author=author,
                assessment=assessment,
                failed_stage="graph_completion",
                failure=str(error),
            )
        except RuntimeError as error:
            return _write_receipt(
                output_path,
                _receipt(
                    case_id=case_id,
                    status="failed",
                    outcome="environment_failure",
                    wall_ms=elapsed_ms(started_ns),
                    host_profile=host_profile,
                    budget=budget,
                    critic=critic,
                    source=source,
                    author=author,
                    assessment=assessment,
                    finalized=finalized,
                    transaction=None,
                    failed_stage="transaction",
                    failure=str(error),
                ),
            )
        except (ImportError, OSError) as error:
            return _write_receipt(
                output_path,
                _receipt(
                    case_id=case_id,
                    status="failed",
                    outcome="environment_failure",
                    wall_ms=elapsed_ms(started_ns),
                    host_profile=host_profile,
                    budget=budget,
                    critic=critic,
                    source=source,
                    author=author,
                    assessment=assessment,
                    finalized=finalized,
                    transaction=None,
                    failed_stage="transaction",
                    failure=f"{type(error).__name__}: {error}",
                ),
            )
    wall_ms = elapsed_ms(started_ns)
    within_deadline = (
        wall_ms < _deadline_seconds * 1000
        if _deadline_seconds == STANDARD_COMPLETION_DEADLINE_SECONDS
        else wall_ms <= _deadline_seconds * 1000
    )
    status = "completed" if within_deadline else "failed"
    return _write_receipt(
        output_path,
        _receipt(
            case_id=case_id,
            status=status,
            outcome="commit" if status == "completed" else "standard_deadline_exceeded",
            wall_ms=wall_ms,
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=assessment,
            finalized=finalized,
            transaction=transaction,
            failed_stage="" if status == "completed" else "deadline",
            failure="" if status == "completed" else "transaction completed after 60 seconds",
        ),
    )


def _assessment_result(
    *, corpus_path: Path, case_id: str, source: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    try:
        return _assemble_assessment(
            corpus_path=corpus_path, case_id=case_id, source=source
        ), ""
    except ValueError as error:
        return {}, str(error)


def _assemble_assessment(
    *, corpus_path: Path, case_id: str, source: Mapping[str, Any]
) -> dict[str, Any]:
    evidence_sources = {
        "operator_prompt": case_prompt(corpus_path=corpus_path, case_id=case_id),
        "operator_edit": "",
    }
    discarded = source.get("discarded_source_refs")
    if not isinstance(discarded, list):
        raise ValueError("final graph discarded evidence is malformed")
    candidates = atomic_source_candidates_without_discarded(
        atomic_source_candidates_from_catalog(
            semantic_evidence_block_catalog(evidence_sources)
        ),
        discarded_source_refs=discarded,
        evidence_sources=evidence_sources,
    )
    return assemble_parallel_materiality_assessment(
        source.get("materiality_decision"),
        candidates,
        evidence_sources=evidence_sources,
    )


def _finalize_author(
    *,
    case_id: str,
    prompt: str,
    assessment: Mapping[str, Any],
    author: Mapping[str, Any],
    critic_run_id: str,
    semantic_host_profile: str,
) -> dict[str, Any]:
    author_candidate = mapping(author.get("candidate"), "author candidate")
    author_output = mapping(
        author.get("compiled_author_output"), "compiled partitioned author output"
    )
    candidate_sha256 = hashlib.sha256(
        json.dumps(
            author_candidate, ensure_ascii=False, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    ).hexdigest()
    packet = build_semantic_intent_packet(
        assessment,
        author_output,
        prompt=prompt,
        critic_run_id=critic_run_id,
        author_run_id=f"standard:{case_id}:partitioned-graph-author:{candidate_sha256}",
        critic_host_profile=semantic_host_profile,
    )
    return {
        **author,
        "compiled_author_output_sha256": hashlib.sha256(
            json.dumps(
                author_output, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            ).encode("utf-8")
        ).hexdigest(),
        "packet": packet,
    }


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
        repo_root=repo_root, proposal=proposal, release_selector="0.0.1"
    )
    summary = transaction.summary()
    if summary.get("verified") is not True:
        raise RuntimeError("production transaction is not verified")
    return {
        **summary,
        "review_package": dict(transaction.proposal),
        "transaction_payload": product_create_transaction_to_dict(transaction),
    }


def _remaining_finalize_seconds(started_ns: int, deadline_seconds: int) -> int:
    remaining_ms = deadline_seconds * 1000 - elapsed_ms(started_ns)
    return max(0, remaining_ms // 1000)


def _terminal_failure(
    *,
    output_path: Path,
    case_id: str,
    status: str,
    outcome: str,
    started_ns: int,
    host_profile: str,
    budget: Mapping[str, Any],
    critic: Mapping[str, Any] | None,
    source: Mapping[str, Any] | None,
    assessment: Mapping[str, Any] | None,
    failed_stage: str,
    failure: str,
    author: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return _write_receipt(
        output_path,
        _receipt(
            case_id=case_id,
            status=status,
            outcome=outcome,
            wall_ms=elapsed_ms(started_ns),
            host_profile=host_profile,
            budget=budget,
            critic=critic,
            source=source,
            author=author,
            assessment=assessment,
            finalized=None,
            transaction=None,
            failed_stage=failed_stage,
            failure=failure,
        ),
    )


def _materiality_run_id(author: Mapping[str, Any]) -> str:
    value = str(author.get("adjudicator_run_id") or "").strip()
    if not value.startswith(
        ("standard:partitioned-graph-author:", "standard:clarification-author:")
    ):
        raise RuntimeError("final graph lacks its adjudicator authority run")
    return value


def _critic_run_id(critic: Mapping[str, Any]) -> str:
    decision = mapping(critic.get("decision"), "materiality critic decision")
    payload = json.dumps(
        decision, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    )
    return "standard:materiality-critic:" + hashlib.sha256(
        payload.encode("utf-8")
    ).hexdigest()


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
