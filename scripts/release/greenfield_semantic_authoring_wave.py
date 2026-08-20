"""Own the bounded pre-seal Greenfield semantic authoring wave."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from threading import Event
from typing import Any

from greenfield_semantic_materiality_screen_experiment import run_screen
from greenfield_semantic_final_graph_author import run_final_graph_adjudication
from greenfield_semantic_pipeline_receipts import select_source_hypothesis_run
from greenfield_semantic_release_support import canonical_sha256, mapping
from greenfield_semantic_standard_path_experiment import (
    CompletionStageIncomplete,
    ReusableSourcePairDisagreement,
    case_prompt,
    run_hedged_source_graph_hypothesis_case,
)
from greenfield_semantic_structured_host import HostStageCancelled, HostStageTimeout
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import semantic_evidence_block_catalog
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
    compile_partitioned_authoring_graph,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_final_adjudication import (
    clarification_from_source_ambiguity,
    remove_discarded_materiality_refs,
    settle_independently_confirmed_discarded_materiality_refs,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_candidates_from_catalog,
    atomic_source_candidates_without_discarded,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import build_semantic_intent_packet
from odylith.runtime.domain_intelligence.greenfield_semantic_policy_edge_alignment import (
    align_completion_policy_edges,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_partition_custody import (
    completion_without_discarded_citations,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    align_source_policy_kinds_to_materiality,
    assemble_parallel_materiality_assessment,
    materiality_policy_conflict_refs,
    policy_kind_disagreement_clarification,
    require_materiality_source_coverage,
    settle_independently_confirmed_policy_kinds,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import compile_source_partitioned_graph
from odylith.runtime.domain_intelligence.greenfield_semantic_source_hypothesis_comparison import (
    admit_source_only_authority,
    independent_source_materiality_observation,
    independently_confirmed_discarded_refs,
    independently_confirmed_material_ambiguity,
    materiality_handoff_source,
    source_candidate_discarded_refs,
    source_candidate_material_ambiguity,
    source_candidate_policy_kind_assignments,
    source_materiality_candidates,
    source_ref_identity,
)
@dataclass(frozen=True)
class AuthoringWaveBudget:
    """Time and topology available to one zero-retry semantic wave."""

    first_wave_seconds: int
    commit_semantic_seconds: int
    clarification_semantic_seconds: int
    topology_mode: str


def run_authoring_wave(
    *,
    corpus_path: Path,
    case_id: str,
    root: Path,
    host_profile: str,
    critic_model: str,
    critic_reasoning_effort: str,
    source_hypothesis_model: str,
    source_hypothesis_reasoning_effort: str,
    final_adjudicator_model: str,
    final_adjudicator_reasoning_effort: str,
    budget: AuthoringWaveBudget,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None, tuple[str, str, str] | None]:
    """Run one independent materiality critic and two graph authors at entry."""

    cancel_source = Event()
    first_graph_discarded_refs: list[dict[str, Any]] | None = None
    first_material_ambiguity: dict[str, Any] | None = None
    first_policy_assignments: dict[tuple[str, str, int], str | None] | None = None
    confirmed_discarded_refs: list[dict[str, Any]] = []
    settled_materiality_decision: dict[str, Any] | None = None
    independent_source_resolution: dict[str, Any] | None = None
    with ThreadPoolExecutor(max_workers=2) as executor:
        prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
        critic_future = executor.submit(
            run_screen,
            corpus_path=corpus_path,
            case_id=case_id,
            model=critic_model,
            reasoning_effort=critic_reasoning_effort,
            output_path=root / "critic.json",
            model_budget_seconds=budget.first_wave_seconds,
            host_profile=host_profile,
        )

        def validate_partitioned_candidate(
            candidate: Mapping[str, Any], hypothesis_mode: str
        ) -> None:
            nonlocal first_graph_discarded_refs, first_material_ambiguity
            nonlocal first_policy_assignments
            nonlocal settled_materiality_decision, independent_source_resolution
            critic_receipt = mapping(
                critic_future.result(), "materiality critic"
            )
            raw_decision = mapping(
                critic_receipt.get("decision"), "materiality hypothesis"
            )
            decision = raw_decision
            ambiguity = source_candidate_material_ambiguity(candidate)
            if hypothesis_mode == "full_graph":
                first_material_ambiguity = ambiguity
            confirmed_ambiguity = None
            if hypothesis_mode == "source_only":
                confirmed_ambiguity = independently_confirmed_material_ambiguity(
                    first_material_ambiguity, ambiguity
                )
            if confirmed_ambiguity is not None:
                compile_source_partitioned_graph(
                    mapping(candidate.get("source"), "partitioned source hypothesis")
                )
                decision = clarification_from_source_ambiguity(
                    raw_decision, ambiguity=confirmed_ambiguity
                )
                settled_materiality_decision = decision
                independent_source_resolution = {
                    "status": "independently_confirmed_source_material_ambiguity",
                    "materiality_field": confirmed_ambiguity["materiality_field"],
                    "source_refs": [dict(ref) for ref in confirmed_ambiguity["source_refs"]],
                }
                return
            conflict_refs = materiality_policy_conflict_refs(raw_decision)
            evidence_sources = {
                "operator_prompt": prompt_text,
                "operator_edit": "",
            }
            policy_assignments = source_candidate_policy_kind_assignments(
                candidate,
                conflict_refs=conflict_refs,
                evidence_sources=evidence_sources,
            )
            if hypothesis_mode == "full_graph":
                first_policy_assignments = policy_assignments
            elif conflict_refs:
                first_assignments = first_policy_assignments or {}
                agreed = {
                    key: kind
                    for key, kind in policy_assignments.items()
                    if kind is not None and first_assignments.get(key) == kind
                }
                if len(agreed) == len(conflict_refs):
                    decision = settle_independently_confirmed_policy_kinds(
                        raw_decision,
                        assignments=agreed,
                    )
                    independent_source_resolution = {
                        "status": "policy_kind_agreed",
                        "assignments": [
                            {
                                "source_ref": dict(ref),
                                "policy_kind": agreed[source_ref_identity(ref)],
                            }
                            for ref in conflict_refs
                        ],
                    }
                else:
                    decision = policy_kind_disagreement_clarification(
                        raw_decision,
                        source_refs=conflict_refs,
                    )
                    independent_source_resolution = {
                        "status": "policy_kind_clarification",
                        "source_refs": [dict(ref) for ref in conflict_refs],
                    }
            candidate_refs = source_candidate_discarded_refs(candidate)
            if hypothesis_mode == "full_graph":
                first_graph_discarded_refs = candidate_refs
                decision = _materiality_without_candidate_discards(
                    decision, candidate, prompt_text=prompt_text
                )
            else:
                confirmed = independently_confirmed_discarded_refs(
                    first_graph_discarded_refs or [],
                    candidate_refs,
                    evidence_sources=evidence_sources,
                )
                if confirmed:
                    confirmed_discarded_refs[:] = confirmed
                    decision = settle_independently_confirmed_discarded_materiality_refs(
                        decision,
                        discarded_source_refs=confirmed,
                        evidence_sources=evidence_sources,
                    )
                else:
                    decision = _materiality_without_candidate_discards(
                        decision, candidate, prompt_text=prompt_text
                    )
                if conflict_refs or confirmed:
                    settled_materiality_decision = decision
            if _critic_predicts_clarification(critic_receipt):
                return
            if decision["outcome"]["decision"] == "clarification_required":
                return
            if hypothesis_mode == "source_only":
                admitted_source: dict[str, Any] | None = None
                source_adjudication: dict[str, Any] | None = None
                try:
                    admitted_source, source_adjudication = (
                        admit_source_only_authority(
                            candidate,
                            decision=decision,
                            evidence_sources={
                                "operator_prompt": prompt_text,
                                "operator_edit": "",
                            },
                        )
                    )
                    admit_partitioned_candidate(
                        candidate,
                        decision=decision,
                        prompt_text=prompt_text,
                        host_profile=host_profile,
                    )
                except ValueError as error:
                    source = candidate.get("source")
                    if not isinstance(source, Mapping):
                        raise
                    raise ReusableSourcePairDisagreement(
                        str(error),
                        source=admitted_source or source,
                        source_adjudication=source_adjudication,
                        dispute=(
                            "completion"
                            if admitted_source is not None
                            else "source_authority"
                        ),
                    ) from error
                return
            admit_partitioned_candidate(
                candidate,
                decision=decision,
                prompt_text=prompt_text,
                host_profile=host_profile,
            )

        source_future = executor.submit(
            run_hedged_source_graph_hypothesis_case,
            corpus_path=corpus_path,
            case_id=case_id,
            model=source_hypothesis_model,
            reasoning_effort=source_hypothesis_reasoning_effort,
            output_path=root / "source.json",
            model_budget_seconds=budget.first_wave_seconds,
            cancel_event=cancel_source,
            host_profile=host_profile,
            candidate_validator=validate_partitioned_candidate,
        )

        try:
            critic = critic_future.result()
        except HostStageTimeout as error:
            source_attempt = _cancel_and_settle(
                cancel_source,
                source_future,
                case_id=case_id,
                host_profile=host_profile,
                model=source_hypothesis_model,
                reasoning_effort=source_hypothesis_reasoning_effort,
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
                model=source_hypothesis_model,
                reasoning_effort=source_hypothesis_reasoning_effort,
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
                model=source_hypothesis_model,
                reasoning_effort=source_hypothesis_reasoning_effort,
            )
            return _failed_critic_receipt(error, host_profile), source_attempt, None, (
                "environment", "materiality_critic", str(error)
            )
        source_handoff_message = ""
        try:
            source = {**source_future.result(), "authority_used": False}
            if confirmed_discarded_refs:
                source["independently_confirmed_discarded_source_refs"] = [
                    dict(row) for row in confirmed_discarded_refs
                ]
        except CompletionStageIncomplete as error:
            source = {**error.receipt, "authority_used": False}
            source_handoff_message = str(error)
        except HostStageTimeout as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "deadline", "source_hypothesis", str(error)
            )
        except HostStageCancelled as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "environment", "source_hypothesis", str(error)
            )
        except ValueError as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "typed", "source_hypothesis", str(error)
            )
        except RuntimeError as error:
            return critic, _failed_source_receipt(error, host_profile), None, (
                "environment", "source_hypothesis", str(error)
            )
        if settled_materiality_decision is not None:
            critic = {
                **critic,
                "initial_decision": critic["decision"],
                "decision": settled_materiality_decision,
                "independent_source_resolution": independent_source_resolution,
            }
        observation = independent_source_materiality_observation(
            source_materiality_candidates(source),
            decision=mapping(critic.get("decision"), "materiality hypothesis"),
        )
        if observation is not None:
            source = materiality_handoff_source(source, observation=observation)
            return critic, source, None, (
                "handoff",
                "graph_completion",
                "independent typed sources challenge the materiality critic",
            )
        if source_handoff_message:
            return critic, source, None, (
                "handoff", "graph_completion", source_handoff_message
            )
        if _critic_predicts_clarification(critic):
            return critic, source, _clarification_author_receipt(
                critic=critic,
                case_id=case_id,
                host_profile=host_profile,
                model=source_hypothesis_model,
                reasoning_effort=source_hypothesis_reasoning_effort,
                model_budget_seconds=budget.first_wave_seconds,
            ), None
    try:
        source, author = _partitioned_author_receipt(
            source,
            critic=critic,
            prompt_text=prompt_text,
            case_id=case_id,
            host_profile=host_profile,
            model=source_hypothesis_model,
            reasoning_effort=source_hypothesis_reasoning_effort,
            model_budget_seconds=budget.first_wave_seconds,
        )
        return critic, source, author, None
    except ValueError as error:
        return critic, source, None, (
            "handoff", "partitioned_graph_admission", str(error)
        )


def _clarification_author_receipt(
    *, critic: Mapping[str, Any], case_id: str, host_profile: str,
    model: str, reasoning_effort: str, model_budget_seconds: int,
) -> dict[str, Any]:
    decision = mapping(critic.get("decision"), "materiality critic decision")
    return {
        "stage": "partitioned_graph_admission",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": 0,
        "usage": {},
        "model_call_count": 0,
        "materiality_decision": decision,
        "source_status": "not_applicable",
        "findings": [],
        "discarded_source_refs": [],
        "source_candidate_rejections": [],
        "candidate": None,
        "compiled_author_output": None,
        "validation_status": "passed",
        "validation_error": "",
        "adjudicator_run_id": (
            "standard:clarification-author:" + canonical_sha256(decision)
        ),
    }


def _partitioned_author_receipt(
    source_receipt: Mapping[str, Any], *, critic: Mapping[str, Any],
    prompt_text: str, case_id: str, host_profile: str, model: str,
    reasoning_effort: str,
    model_budget_seconds: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    candidate_rows = source_receipt.get("partitioned_candidates")
    if not isinstance(candidate_rows, list) or not candidate_rows:
        raise ValueError("partitioned graph hypotheses are missing")
    raw_decision = mapping(critic.get("decision"), "materiality hypothesis")
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
    selected_row: dict[str, Any] | None = None
    selected_candidate: dict[str, Any] | None = None
    selected_decision: dict[str, Any] | None = None
    selected_assessment: dict[str, Any] | None = None
    failures: list[str] = []
    confirmed_discards = source_receipt.get(
        "independently_confirmed_discarded_source_refs"
    )
    if confirmed_discards is not None and (
        not isinstance(confirmed_discards, list)
        or any(not isinstance(row, Mapping) for row in confirmed_discards)
    ):
        raise ValueError("independently confirmed discarded evidence is malformed")
    for raw_row in candidate_rows:
        row = mapping(raw_row, "partitioned graph run")
        candidate = mapping(row.get("candidate"), "partitioned graph hypothesis")
        candidate_discards = source_candidate_discarded_refs(candidate)
        confirmed = independently_confirmed_discarded_refs(
            confirmed_discards or [],
            candidate_discards,
            evidence_sources=evidence_sources,
        )
        decision = (
            settle_independently_confirmed_discarded_materiality_refs(
                raw_decision,
                discarded_source_refs=confirmed,
                evidence_sources=evidence_sources,
            )
            if confirmed
            else _materiality_without_candidate_discards(
                raw_decision, candidate, prompt_text=prompt_text
            )
        )
        source_candidates = atomic_source_candidates_without_discarded(
            atomic_source_candidates_from_catalog(evidence_catalog),
            discarded_source_refs=source_candidate_discarded_refs(candidate),
            evidence_sources=evidence_sources,
        )
        assessment = assemble_parallel_materiality_assessment(
            decision,
            source_candidates,
            evidence_sources=evidence_sources,
        )
        try:
            if not _critic_predicts_clarification(critic):
                admit_partitioned_candidate(
                    candidate, decision=decision, prompt_text=prompt_text,
                    assessment=assessment, host_profile=host_profile,
                )
        except ValueError as error:
            failures.append(f"run {row.get('run_index')}: {error}")
            continue
        selected_row = row
        selected_candidate = candidate
        selected_decision = decision
        selected_assessment = assessment
        break
    if (
        selected_row is None or selected_candidate is None
        or selected_decision is None or selected_assessment is None
    ):
        raise ValueError("; ".join(failures) or "no partitioned graph was admitted")
    decision = selected_decision
    assessment = selected_assessment
    raw_candidate = selected_candidate
    if raw_candidate.get("version") != SEMANTIC_PARTITIONED_AUTHOR_VERSION:
        raise ValueError("partitioned graph hypothesis uses an unsupported version")
    if _critic_predicts_clarification(critic):
        admitted_candidate = raw_candidate
        source = compile_source_partitioned_graph(
            mapping(raw_candidate.get("source"), "partitioned source hypothesis")
        )
        rejected_candidates: list[dict[str, Any]] = []
    else:
        (
            admitted_candidate, source, rejected_candidates, compiled_author_output,
        ) = admit_partitioned_candidate(
            raw_candidate,
            decision=decision,
            prompt_text=prompt_text,
            assessment=assessment,
            host_profile=host_profile,
        )
    if _critic_predicts_clarification(critic):
        compiled_author_output = None
    completion = mapping(
        admitted_candidate.get("completion"), "partitioned completion hypothesis"
    )
    candidate = {"source": source, "completion": completion}
    receipt = {
        "stage": "partitioned_graph_admission",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": 0,
        "usage": {},
        "model_call_count": 0,
        "materiality_decision": decision,
        "source_status": (
            "not_applicable" if _critic_predicts_clarification(critic) else "approved"
        ),
        "findings": [],
        "discarded_source_refs": source_candidate_discarded_refs(raw_candidate),
        "source_candidate_rejections": rejected_candidates,
        "candidate": candidate,
        "compiled_author_output": compiled_author_output,
        "validation_status": "passed",
        "validation_error": "",
    }
    receipt["adjudicator_run_id"] = (
        "standard:partitioned-graph-author:"
        + canonical_sha256(
            {"materiality_decision": decision, "candidate": candidate}
        )
    )
    selected_source = select_source_hypothesis_run(
        source_receipt, selected_run_index=int(selected_row["run_index"]))
    selected_source["partitioned_candidate"] = admitted_candidate
    selected_source["source"] = mapping(
        admitted_candidate.get("source"), "selected partitioned source"
    )
    selected_source["admission_failures"] = failures
    return selected_source, receipt


def admit_partitioned_candidate(
    candidate: Mapping[str, Any], *, decision: Mapping[str, Any],
    prompt_text: str, host_profile: str,
    assessment: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    """Preserve source facts while enforcing critic-owned policy and coverage."""

    if candidate.get("version") != SEMANTIC_PARTITIONED_AUTHOR_VERSION:
        raise ValueError("partitioned graph hypothesis uses an unsupported version")
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    source_hypothesis = mapping(
        candidate.get("source"), "partitioned source hypothesis"
    )
    rejections: list[dict[str, Any]] = []
    unaligned_source = source_hypothesis
    provisional_source = compile_source_partitioned_graph(unaligned_source)
    admitted_source = align_source_policy_kinds_to_materiality(
        unaligned_source, decision
    )
    source = compile_source_partitioned_graph(admitted_source)
    require_materiality_source_coverage(
        decision, source, evidence_sources=evidence_sources
    )
    if assessment is None:
        evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
        source_candidates = atomic_source_candidates_without_discarded(
            atomic_source_candidates_from_catalog(evidence_catalog),
            discarded_source_refs=source_candidate_discarded_refs(candidate),
            evidence_sources=evidence_sources,
        )
        assessment = assemble_parallel_materiality_assessment(
            decision,
            source_candidates,
            evidence_sources=evidence_sources,
        )
    boundary = mapping(
        source_hypothesis.get("boundary"), "partitioned source boundary"
    )
    completion_candidate = completion_without_discarded_citations(
        boundary.get("discarded_evidence"), candidate.get("completion")
    )
    completion = align_completion_policy_edges(
        completion_candidate,
        provisional_source=provisional_source,
        settled_source=source,
        evidence_sources=evidence_sources,
    )
    admitted_candidate = {
        **dict(candidate), "source": admitted_source, "completion": completion,
    }
    author_output = compile_partitioned_authoring_graph(
        admitted_candidate,
        assessment=assessment,
        evidence_sources=evidence_sources,
    )
    build_semantic_intent_packet(
        assessment,
        author_output,
        prompt=prompt_text,
        critic_run_id="admission:materiality-critic",
        author_run_id="admission:partitioned-graph-author",
        critic_host_profile=host_profile,
    )
    return (
        admitted_candidate,
        source,
        [dict(row) for row in rejections],
        author_output,
    )


def _materiality_without_candidate_discards(
    decision: Mapping[str, Any], candidate: Mapping[str, Any], *, prompt_text: str,
) -> dict[str, Any]:
    return remove_discarded_materiality_refs(
        decision,
        discarded_source_refs=source_candidate_discarded_refs(candidate),
        evidence_sources={"operator_prompt": prompt_text, "operator_edit": ""},
    )


def run_final_adjudication_from_hypotheses(
    *,
    corpus_path: Path,
    case_id: str,
    critic: Mapping[str, Any],
    source: Mapping[str, Any],
    host_profile: str,
    model: str,
    reasoning_effort: str,
    budget_seconds: int,
    topology_mode: str,
) -> tuple[dict[str, Any] | None, tuple[str, str, str] | None]:
    """Adjudicate one sealed critic/source pair without recreating either hypothesis."""

    try:
        prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
        evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
        result = run_final_graph_adjudication(
            prompt_text=prompt_text,
            evidence_catalog=semantic_evidence_block_catalog(evidence_sources),
            materiality_hypothesis=mapping(
                critic.get("decision"), "materiality hypothesis"
            ),
            source_hypothesis=mapping(source.get("source"), "source hypothesis"),
            evidence_sources=evidence_sources,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            topology_mode=topology_mode,
            host_profile=host_profile,
        )
        author = _final_receipt(
            result,
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            model_budget_seconds=budget_seconds,
        )
        if (
            author.get("source_status") != "approved"
            and not _final_decision_is_clarification(author)
        ):
            return author, (
                "typed",
                "final_graph_adjudication",
                "final adjudicator rejected the typed source candidate",
            )
    except HostStageTimeout as error:
        return None, ("deadline", "final_graph_adjudication", str(error))
    except ValueError as error:
        return None, ("typed", "final_graph_adjudication", str(error))
    except RuntimeError as error:
        return None, ("environment", "final_graph_adjudication", str(error))
    return author, None


def _critic_predicts_clarification(value: Mapping[str, Any]) -> bool:
    decision = value.get("decision")
    outcome = decision.get("outcome") if isinstance(decision, Mapping) else None
    return (
        isinstance(outcome, Mapping)
        and outcome.get("decision") == "clarification_required"
    )


def _final_decision_is_clarification(value: Mapping[str, Any]) -> bool:
    decision = value.get("materiality_decision")
    return isinstance(decision, Mapping) and _critic_predicts_clarification(
        {"decision": decision}
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
            "stage": "source_hypothesis",
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
        "stage": "source_hypothesis",
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


def _final_receipt(
    value: Mapping[str, Any], *, case_id: str, host_profile: str,
    model: str, reasoning_effort: str, model_budget_seconds: int,
) -> dict[str, Any]:
    decision = mapping(value.get("decision"), "final materiality decision")
    adjudication = mapping(value.get("adjudication"), "final graph adjudication")
    receipt = {
        "stage": "final_graph_adjudication",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": int(value.get("wall_ms") or 0),
        "usage": mapping(value.get("usage"), "final adjudication usage"),
        "model_call_count": 1,
        "materiality_decision": decision,
        "source_status": adjudication.get("source_status"),
        "findings": adjudication.get("findings"),
        "discarded_source_refs": adjudication.get("discarded_source_refs"),
        "source_candidate_rejections": list(
            value.get("source_candidate_rejections") or []
        ),
        "candidate": adjudication,
        "validation_status": "passed",
        "validation_error": "",
    }
    receipt["adjudicator_run_id"] = (
        "standard:final-graph-adjudicator:"
        + canonical_sha256(
            {"materiality_decision": decision, "adjudication": adjudication}
        )
    )
    return receipt


__all__ = [
    "AuthoringWaveBudget",
    "admit_partitioned_candidate",
    "run_authoring_wave",
    "run_final_adjudication_from_hypotheses",
]
