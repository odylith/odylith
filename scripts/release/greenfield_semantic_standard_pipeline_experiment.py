"""Run the production Greenfield mechanism under standard and rescue deadlines."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import tempfile
from threading import Event
import time
from typing import Any

from greenfield_semantic_clarification_author import (
    ClarificationStageIncomplete,
    run_clarification_author,
)
from greenfield_semantic_materiality_screen_experiment import run_screen
from greenfield_semantic_standard_path_experiment import (
    CompletionStageIncomplete,
    case_prompt,
    run_graph_completion_case,
    run_source_graph_case,
    source_graph,
)
from greenfield_semantic_pipeline_receipts import (
    PIPELINE_VERSION,
    pipeline_receipt as _receipt,
    write_receipt as _write_receipt,
)
from greenfield_semantic_structured_host import (
    HostStageCancelled,
    HostStageTimeout,
    elapsed_ms,
)
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
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_candidates_from_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    compile_partitioned_authoring_graph,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    admit_source_candidates_by_materiality,
    assemble_parallel_materiality_assessment,
    require_materiality_source_coverage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    compile_source_partitioned_graph,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)


PARALLEL_FIRST_WAVE_SECONDS = 34
SEMANTIC_AUTHORING_SHARED_SECONDS = 54
DETERMINISTIC_RESERVE_SECONDS = 5
MIN_STANDARD_AUTHOR_SECONDS = 20


def standard_budget_contract() -> dict[str, Any]:
    """Return the non-negotiable standard allocation including transaction work."""
    critical_path = SEMANTIC_AUTHORING_SHARED_SECONDS + DETERMINISTIC_RESERVE_SECONDS
    if critical_path >= STANDARD_COMPLETION_DEADLINE_SECONDS:
        raise RuntimeError("standard pipeline allocation does not finish before 60 seconds")
    return {
        "tier": "standard",
        "deadline_seconds": STANDARD_COMPLETION_DEADLINE_SECONDS,
        "comparison": "strictly_less_than",
        "parallel_materiality_and_source_seconds": PARALLEL_FIRST_WAVE_SECONDS,
        "semantic_authoring_shared_seconds": SEMANTIC_AUTHORING_SHARED_SECONDS,
        "post_first_wave_completion_seconds": "remaining shared semantic budget",
        "packet_and_transaction_reserve_seconds": DETERMINISTIC_RESERVE_SECONDS,
        "critical_path_seconds": critical_path,
        "retries": 0,
        "automatic_deep_tier": False,
        "minimum_standard_author_seconds": MIN_STANDARD_AUTHOR_SECONDS,
        "completion_topology": "single_system",
    }


def run_standard_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    host_profile: str = "codex",
    critic_model: str = "",
    critic_reasoning_effort: str = "",
    source_model: str = "",
    source_reasoning_effort: str = "",
    author_model: str = "",
    author_reasoning_effort: str = "",
    _first_wave_budget: int = PARALLEL_FIRST_WAVE_SECONDS,
    _semantic_budget: int = SEMANTIC_AUTHORING_SHARED_SECONDS,
    _deadline_seconds: int = STANDARD_COMPLETION_DEADLINE_SECONDS,
    _budget_contract: Mapping[str, Any] | None = None,
    _completion_topology: str = "single_system",
    _evidence_assignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run one no-retry attempt and return a terminal or typed rescue handoff."""

    profile = standard_host_stage_profile(host_profile)
    critic_model = critic_model or profile["critic_model"]
    critic_reasoning_effort = critic_reasoning_effort or profile["critic_reasoning_effort"]
    source_model = source_model or profile["source_model"]
    source_reasoning_effort = source_reasoning_effort or profile["source_reasoning_effort"]
    author_model = author_model or profile["completion_model"]
    author_reasoning_effort = author_reasoning_effort or profile["completion_reasoning_effort"]
    started_ns = time.monotonic_ns()
    budget = dict(_budget_contract or standard_budget_contract())
    if _evidence_assignment is not None:
        budget["evidence_assignment"] = dict(_evidence_assignment)
    with tempfile.TemporaryDirectory(prefix="odylith-standard-pipeline-") as temporary:
        root = Path(temporary)
        critic, source, author, failure = _authoring_wave(
            corpus_path=corpus_path,
            case_id=case_id,
            root=root,
            host_profile=host_profile,
            critic_model=critic_model,
            critic_reasoning_effort=critic_reasoning_effort,
            source_model=source_model,
            source_reasoning_effort=source_reasoning_effort,
            author_model=author_model,
            author_reasoning_effort=author_reasoning_effort,
            first_wave_budget=_first_wave_budget,
            semantic_budget=_semantic_budget,
            completion_topology=_completion_topology,
        )
        if failure is not None:
            failure_kind, failed_stage, message = failure
            status = "rescue_required" if failure_kind == "typed" else "failed"
            outcome = (
                "typed_standard_failure"
                if failure_kind == "typed"
                else "standard_deadline_exceeded"
                if failure_kind == "deadline"
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
            critic=_required_mapping(critic, "semantic critic"),
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
            author_budget = (
                _remaining_finalize_seconds(started_ns, _deadline_seconds)
                - DETERMINISTIC_RESERVE_SECONDS
            )
            if author_budget <= 0:
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
                    assessment=assessment,
                    failed_stage="deadline",
                    failure="standard path left no clarification-author budget",
                )
            try:
                author = run_clarification_author(
                    case_id=case_id,
                    prompt_text=case_prompt(
                        corpus_path=corpus_path, case_id=case_id
                    ),
                    assessment=assessment,
                    critic_run_id=_critic_run_id(
                        _required_mapping(critic, "semantic critic")
                    ),
                    host_profile=host_profile,
                    model=author_model,
                    reasoning_effort=author_reasoning_effort,
                    model_budget_seconds=author_budget,
                    output_path=root / "clarification-author.json",
                )
            except ClarificationStageIncomplete as error:
                status = "rescue_required" if error.failure_kind == "typed" else "failed"
                outcome = (
                    "typed_standard_failure"
                    if error.failure_kind == "typed"
                    else "standard_deadline_exceeded"
                    if error.failure_kind == "deadline"
                    else "environment_failure"
                )
                return _terminal_failure(
                    output_path=output_path,
                    case_id=case_id,
                    status=status,
                    outcome=outcome,
                    started_ns=started_ns,
                    host_profile=host_profile,
                    budget=budget,
                    critic=critic,
                    source=source,
                    author=error.receipt,
                    assessment=assessment,
                    failed_stage="clarification_author",
                    failure=str(error),
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
                    finalized={"packet": author["packet"]},
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
                author=_required_mapping(author, "partitioned author"),
                critic_run_id=_critic_run_id(
                    _required_mapping(critic, "semantic critic")
                ),
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


def _authoring_wave(
    *,
    corpus_path: Path,
    case_id: str,
    root: Path,
    host_profile: str,
    critic_model: str,
    critic_reasoning_effort: str,
    source_model: str,
    source_reasoning_effort: str,
    author_model: str,
    author_reasoning_effort: str,
    first_wave_budget: int,
    semantic_budget: int,
    completion_topology: str,
) -> tuple[
    dict[str, Any] | None,
    dict[str, Any] | None,
    dict[str, Any] | None,
    tuple[str, str, str] | None,
]:
    first_wave_started_ns = time.monotonic_ns()
    cancel_source = Event()
    with ThreadPoolExecutor(max_workers=2) as executor:
        critic_future = executor.submit(
            run_screen,
            corpus_path=corpus_path,
            case_id=case_id,
            model=critic_model,
            reasoning_effort=critic_reasoning_effort,
            output_path=root / "critic.json",
            model_budget_seconds=first_wave_budget,
            host_profile=host_profile,
        )
        source_future = executor.submit(
            run_source_graph_case,
            corpus_path=corpus_path,
            case_id=case_id,
            model=source_model,
            reasoning_effort=source_reasoning_effort,
            output_path=root / "source.json",
            model_budget_seconds=first_wave_budget,
            cancel_event=cancel_source,
            host_profile=host_profile,
        )
        try:
            critic = critic_future.result()
        except HostStageTimeout as error:
            source_attempt = _cancel_and_settle(
                cancel_source,
                source_future,
                case_id=case_id,
                host_profile=host_profile,
                model=source_model,
                reasoning_effort=source_reasoning_effort,
            )
            return _failed_critic_receipt(error, host_profile), source_attempt, None, (
                "deadline", "materiality_critic", str(error)
            )
        except ValueError as error:
            source_attempt = _cancel_and_settle(
                cancel_source,
                source_future,
                case_id=case_id,
                host_profile=host_profile,
                model=source_model,
                reasoning_effort=source_reasoning_effort,
            )
            return _failed_critic_receipt(error, host_profile), source_attempt, None, (
                "typed", "materiality_critic", str(error)
            )
        except RuntimeError as error:
            source_attempt = _cancel_and_settle(
                cancel_source,
                source_future,
                case_id=case_id,
                host_profile=host_profile,
                model=source_model,
                reasoning_effort=source_reasoning_effort,
            )
            return _failed_critic_receipt(error, host_profile), source_attempt, None, (
                "environment", "materiality_critic", str(error)
            )
        critic_decision = str(
            critic.get("decision", {}).get("outcome", {}).get("decision") or ""
        )
        if critic_decision == "clarification_required":
            source_attempt = _cancel_and_settle(
                cancel_source,
                source_future,
                case_id=case_id,
                host_profile=host_profile,
                model=source_model,
                reasoning_effort=source_reasoning_effort,
            )
            return critic, source_attempt, None, None
        try:
            source = {**source_future.result(), "authority_used": True}
            evidence_sources = {
                "operator_prompt": case_prompt(
                    corpus_path=corpus_path, case_id=case_id
                ),
                "operator_edit": "",
            }
            admission = admit_source_candidates_by_materiality(
                critic.get("decision"),
                source_graph(source),
                evidence_sources=evidence_sources,
            )
            admitted_source = _required_mapping(
                admission.get("source"), "admitted source graph"
            )
            source["admission"] = {
                key: value for key, value in admission.items() if key != "source"
            }
            require_materiality_source_coverage(
                critic.get("decision"),
                compile_source_partitioned_graph(admitted_source),
                evidence_sources=evidence_sources,
            )
        except HostStageTimeout as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "deadline", "source_graph", str(error)
            )
        except HostStageCancelled as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "environment", "source_graph", str(error)
            )
        except ValueError as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "typed", "source_graph", str(error)
            )
        except RuntimeError as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "environment", "source_graph", str(error)
            )
    first_wave_seconds = (elapsed_ms(first_wave_started_ns) + 999) // 1000
    author_budget = semantic_budget - first_wave_seconds
    if author_budget < MIN_STANDARD_AUTHOR_SECONDS:
        return critic, source, None, (
            "typed", "graph_completion",
            "validated parallel first wave requires the rescue completion tier",
        )
    try:
        author = run_graph_completion_case(
            corpus_path=corpus_path,
            case_id=case_id,
            model=author_model,
            reasoning_effort=author_reasoning_effort,
            output_path=root / "author.json",
            model_budget_seconds=author_budget,
            resume_source=admitted_source,
            materiality_decision=_required_mapping(
                critic.get("decision"), "materiality decision"
            ),
            completion_topology=completion_topology,
            host_profile=host_profile,
        )
    except CompletionStageIncomplete as error:
        return critic, source, dict(error.receipt), (
            "typed", "graph_completion", str(error)
        )
    except HostStageTimeout as error:
        return critic, source, None, ("deadline", "graph_completion", str(error))
    except ValueError as error:
        return critic, source, None, ("typed", "graph_completion", str(error))
    except RuntimeError as error:
        return critic, source, None, ("environment", "graph_completion", str(error))
    return critic, source, author, None


def _assessment_result(
    *, corpus_path: Path, case_id: str, critic: Mapping[str, Any]
) -> tuple[dict[str, Any], str]:
    try:
        return _assemble_assessment(
            corpus_path=corpus_path, case_id=case_id, critic=critic
        ), ""
    except ValueError as error:
        return {}, str(error)


def _assemble_assessment(
    *, corpus_path: Path, case_id: str, critic: Mapping[str, Any]
) -> dict[str, Any]:
    evidence_sources = {
        "operator_prompt": case_prompt(corpus_path=corpus_path, case_id=case_id),
        "operator_edit": "",
    }
    return assemble_parallel_materiality_assessment(
        critic.get("decision"),
        atomic_source_candidates_from_catalog(
            semantic_evidence_block_catalog(evidence_sources)
        ),
        evidence_sources=evidence_sources,
    )


def _cancel_and_settle(
    cancel_event: Event,
    future: Any,
    *,
    case_id: str,
    host_profile: str,
    model: str,
    reasoning_effort: str,
) -> dict[str, Any]:
    cancel_event.set()
    try:
        return {**future.result(), "authority_used": False}
    except (RuntimeError, ValueError) as error:
        return {
            "stage": "source_graph",
            "case_id": case_id,
            "host_profile": host_profile,
            "model": model,
            "reasoning_effort": reasoning_effort,
            "authority_used": False,
            "validation_status": "cancelled",
            "validation_error": str(error),
            "model_call_count": 2,
            "usage": {},
        }


def _failed_source_receipt(error: Exception, host_profile: str) -> dict[str, Any]:
    return {
        "stage": "source_graph",
        "host_profile": host_profile,
        "authority_used": False,
        "validation_status": "failed",
        "validation_error": str(error),
        "model_call_count": 2,
        "usage": {},
    }


def _failed_critic_receipt(error: Exception, host_profile: str) -> dict[str, Any]:
    return {
        "stage": "materiality_critic",
        "host_profile": host_profile,
        "validation_status": "failed",
        "validation_error": str(error),
        "model_call_count": 1,
        "usage": {},
    }


def _finalize_author(
    *,
    case_id: str,
    prompt: str,
    assessment: Mapping[str, Any],
    author: Mapping[str, Any],
    critic_run_id: str,
    semantic_host_profile: str,
) -> dict[str, Any]:
    author_candidate = _required_mapping(author.get("candidate"), "author candidate")
    evidence_sources = {"operator_prompt": prompt, "operator_edit": ""}
    author_output = compile_partitioned_authoring_graph(
        author_candidate,
        assessment=assessment,
        evidence_sources=evidence_sources,
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
        author_run_id=f"standard:{case_id}:partitioned-author:{candidate_sha256}",
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


def _critic_run_id(critic: Mapping[str, Any]) -> str:
    payload = json.dumps(
        {"decision": critic.get("decision"), "candidates": critic.get("candidate")},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "standard:semantic-critic:" + hashlib.sha256(payload.encode()).hexdigest()


def _required_mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} is unavailable")
    return dict(value)


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
