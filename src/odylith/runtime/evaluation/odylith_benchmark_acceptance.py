"""Acceptance gate helpers for benchmark publication proof and live reporting."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import benchmark_metric_helpers
from odylith.runtime.evaluation import odylith_benchmark_execution_engine
from odylith.runtime.evaluation import odylith_benchmark_guardrails

_SECONDARY_LATENCY_GUARDRAIL_MAX_DELTA_MS = 15.0
_SECONDARY_ARCHITECTURE_LATENCY_GUARDRAIL_MAX_DELTA_MS = 15.0
_SECONDARY_PROMPT_TOKEN_GUARDRAIL_MAX_DELTA = 64.0
_SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA = 96.0
_SECONDARY_WITHIN_BUDGET_RATE_MIN = 0.8

_ACCEPTANCE_CHECK_LABELS = {
    "memory_backend_standardized": "runtime memory backend is not standardized on the LanceDB/Tantivy contract",
    "memory_backed_retrieval_ready": "benchmark ran without an active local LanceDB/Tantivy retrieval substrate",
    "required_path_recall_not_worse": "grounding recall fell below the raw baseline",
    "required_path_precision_not_worse": "grounding precision fell below the raw baseline",
    "hallucinated_surface_not_worse": "observed-surface drift is worse than the raw baseline",
    "validation_success_not_worse": "validation success fell below the raw baseline",
    "write_surface_precision_not_worse": "write-surface precision fell below the raw baseline",
    "unnecessary_widening_not_worse": "unnecessary write-surface widening is worse than the raw baseline",
    "critical_required_path_recall_not_worse": "critical-path recall fell below the raw baseline",
    "critical_validation_success_not_worse": "critical validation success fell below the raw baseline",
    "live_execution_contract_match": "odylith_on and odylith_off did not use the same Codex CLI model and reasoning contract",
    "expectation_success_not_worse": "execution fit fell below the raw baseline",
    "candidate_expectation_success_positive": "odylith_on did not finish any sampled live task successfully",
    "candidate_validation_success_positive": "odylith_on did not reach any validator-backed successful outcome on sampled validation-backed work",
    "candidate_critical_required_path_recall_positive": "odylith_on missed every critical required path on sampled critical work",
    "candidate_critical_validation_success_positive": "odylith_on did not reach any successful critical validator-backed outcome",
    "proof_false_clearance_healthy": "proof-state claimed live clearance before the hosted frontier advanced",
    "proof_frontier_gate_accurate": "proof-state frontier gating is inconsistent with the observed live frontier",
    "proof_claim_guard_accurate": "claim guard is labeling proof tiers inconsistently",
    "proof_same_fingerprint_reuse_accurate": "same-fingerprint live failures are not reopening the same blocker seam consistently",
    "context_engine_packet_source_accurate": "Context Engine benchmark slices chose the wrong packet lane",
    "context_engine_selection_state_accurate": "Context Engine benchmark slices resolved the wrong scope-selection state",
    "context_engine_workstream_accurate": "Context Engine benchmark slices resolved the wrong workstream anchor",
    "context_engine_ambiguity_fail_closed": "Context Engine benchmark slices do not stay fail-closed on ambiguous scope",
    "context_engine_session_namespaced": "Context Engine runtime-backed benchmark slices are not keeping sessions namespaced",
    "execution_engine_present": "execution-engine benchmark slices are missing the execution-engine snapshot",
    "execution_engine_resume_token_present": "execution-engine benchmark slices are missing resume-token coverage",
    "execution_engine_false_admit_zero": "execution-engine benchmark slices still falsely admit blocked actions",
    "execution_engine_false_deny_zero": "execution-engine benchmark slices still falsely deny admissible actions",
    "execution_engine_outcome_accurate": "execution-engine benchmark slices resolved the wrong admissibility outcome",
    "execution_engine_mode_accurate": "execution-engine benchmark slices resolved the wrong execution mode",
    "execution_engine_next_move_accurate": "execution-engine benchmark slices resolved the wrong truthful next move",
    "execution_engine_closure_accurate": "execution-engine benchmark slices resolved the wrong closure posture",
    "execution_engine_wait_status_accurate": "execution-engine benchmark slices resolved the wrong semantic wait status",
    "execution_engine_validation_accurate": "execution-engine benchmark slices resolved the wrong validation archetype",
    "execution_engine_current_phase_accurate": "execution-engine benchmark slices resolved the wrong current phase",
    "execution_engine_last_successful_phase_accurate": "execution-engine benchmark slices resolved the wrong last successful phase",
    "execution_engine_authoritative_lane_accurate": "execution-engine benchmark slices resolved the wrong authoritative lane",
    "execution_engine_target_lane_accurate": "execution-engine benchmark slices resolved the wrong target lane",
    "execution_engine_resume_token_accurate": "execution-engine benchmark slices resolved the wrong resume token",
    "execution_engine_host_family_accurate": "execution-engine benchmark slices resolved the wrong host family",
    "execution_engine_model_family_accurate": "execution-engine benchmark slices resolved the wrong model family",
    "execution_engine_component_id_accurate": "execution-engine benchmark slices resolved the wrong canonical engine component id",
    "execution_engine_canonical_component_id_accurate": "execution-engine benchmark slices resolved the wrong canonical component id",
    "execution_engine_identity_status_accurate": "execution-engine benchmark slices resolved the wrong identity status",
    "execution_engine_target_component_status_accurate": "execution-engine benchmark slices resolved the wrong target component status",
    "execution_engine_snapshot_reuse_status_accurate": "execution-engine benchmark slices resolved the wrong snapshot reuse posture",
    "execution_engine_reanchor_accurate": "execution-engine benchmark slices resolved the wrong re-anchor requirement",
    "execution_engine_delegation_guard_accurate": "execution-engine benchmark slices resolved the wrong delegation guard posture",
    "execution_engine_parallelism_guard_accurate": "execution-engine benchmark slices resolved the wrong parallelism guard posture",
    "explicit_workstream_expectation_positive": "explicit workstream scenarios lost expectation coverage",
    "critical_metric_coverage_complete": "critical metric coverage is incomplete",
    "selected_cache_profiles_clear_gate": "selected cache profiles do not all clear the hard quality gate",
    "latency_within_guardrail": "median latency exceeds the +15 ms guardrail",
    "prompt_delta_within_guardrail": "median prompt cost exceeds the +64-token guardrail",
    "total_payload_delta_within_guardrail": "median total payload exceeds the +96-token guardrail",
    "bootstrap_payload_delta_within_guardrail": "median bootstrap payload exceeds the +96-token guardrail",
    "tight_budget_behavior_healthy": "tighter-budget behavior fell below the 0.80 success floor",
    "architecture_latency_within_guardrail": "architecture latency exceeds the +15 ms guardrail",
    "widening_rate_healthy": "widening frequency exceeds the advisory threshold",
    "governance_packet_coverage_complete": "governance-family packet coverage is incomplete",
}

_HARD_CHECK_FAILURE_NOTES = {
    "candidate_expectation_success_positive": "The sampled live run is not yet informative: `odylith_on` did not complete any benchmark task successfully end to end.",
    "candidate_validation_success_positive": "No sampled validation-backed task produced a successful `odylith_on` outcome, so this run cannot publish as a benchmark win.",
    "candidate_critical_required_path_recall_positive": "Odylith still missed every sampled critical required path, so the critical slice is not benchmark-ready.",
    "candidate_critical_validation_success_positive": "No sampled critical validator-backed task produced a successful `odylith_on` outcome, so the critical slice is not benchmark-ready.",
    "proof_false_clearance_healthy": "Proof-state benchmark slices still allow false live-clearance claims before the hosted frontier advances.",
    "proof_frontier_gate_accurate": "Proof-state frontier gating is inconsistent on the sampled proof-backed slices.",
    "proof_claim_guard_accurate": "Proof-state claim tiers are still mislabeled on sampled proof-backed slices.",
    "proof_same_fingerprint_reuse_accurate": "Same-fingerprint proof seams are not being reused consistently on sampled proof-backed slices.",
    "context_engine_packet_source_accurate": "Context Engine benchmark slices are selecting the wrong packet lane on sampled grounding cases.",
    "context_engine_selection_state_accurate": "Context Engine benchmark slices are mislabeling resolved versus ambiguous scope on sampled grounding cases.",
    "context_engine_workstream_accurate": "Context Engine benchmark slices are resolving the wrong workstream anchor on sampled grounding cases.",
    "context_engine_ambiguity_fail_closed": "Context Engine benchmark slices are not staying fail-closed when the sampled scope remains ambiguous.",
    "context_engine_session_namespaced": "Context Engine runtime-backed benchmark slices are not keeping session state namespaced consistently.",
    "execution_engine_present": "Execution Engine benchmark slices are dropping the execution-engine snapshot on sampled packet rows.",
    "execution_engine_resume_token_present": "Execution Engine benchmark slices are not carrying resumability through a resume token consistently.",
    "execution_engine_outcome_accurate": "Execution Engine benchmark slices are resolving the wrong admissibility outcome on sampled execution rows.",
    "execution_engine_mode_accurate": "Execution Engine benchmark slices are resolving the wrong execution mode on sampled execution rows.",
    "execution_engine_next_move_accurate": "Execution Engine benchmark slices are resolving the wrong truthful next move on sampled execution rows.",
    "execution_engine_closure_accurate": "Execution Engine benchmark slices are resolving the wrong closure posture on sampled execution rows.",
    "execution_engine_wait_status_accurate": "Execution Engine benchmark slices are resolving the wrong semantic wait state on sampled execution rows.",
    "execution_engine_validation_accurate": "Execution Engine benchmark slices are resolving the wrong validation archetype on sampled execution rows.",
    "execution_engine_current_phase_accurate": "Execution Engine benchmark slices are resolving the wrong current phase on sampled execution rows.",
    "execution_engine_last_successful_phase_accurate": "Execution Engine benchmark slices are resolving the wrong last successful phase on sampled execution rows.",
    "execution_engine_authoritative_lane_accurate": "Execution Engine benchmark slices are resolving the wrong authoritative lane on sampled execution rows.",
    "execution_engine_target_lane_accurate": "Execution Engine benchmark slices are resolving the wrong target lane on sampled execution rows.",
    "execution_engine_resume_token_accurate": "Execution Engine benchmark slices are resolving the wrong resume token on sampled execution rows.",
    "execution_engine_host_family_accurate": "Execution Engine benchmark slices are resolving the wrong host family on sampled execution rows.",
    "execution_engine_model_family_accurate": "Execution Engine benchmark slices are resolving the wrong model family on sampled execution rows.",
    "execution_engine_component_id_accurate": "Execution Engine benchmark slices are resolving the wrong canonical engine component id on sampled execution rows.",
    "execution_engine_canonical_component_id_accurate": "Execution Engine benchmark slices are resolving the wrong canonical component id on sampled execution rows.",
    "execution_engine_identity_status_accurate": "Execution Engine benchmark slices are resolving the wrong identity status on sampled execution rows.",
    "execution_engine_target_component_status_accurate": "Execution Engine benchmark slices are resolving the wrong target component status on sampled execution rows.",
    "execution_engine_snapshot_reuse_status_accurate": "Execution Engine benchmark slices are resolving the wrong snapshot reuse posture on sampled execution rows.",
    "execution_engine_reanchor_accurate": "Execution Engine benchmark slices are resolving the wrong re-anchor requirement on sampled execution rows.",
    "execution_engine_false_admit_zero": "Execution Engine benchmark slices are still falsely admitting actions that should fail closed.",
    "execution_engine_false_deny_zero": "Execution Engine benchmark slices are still falsely denying actions that should be admissible.",
    "execution_engine_delegation_guard_accurate": "Execution Engine benchmark slices are resolving the wrong delegation guard posture on sampled execution rows.",
    "execution_engine_parallelism_guard_accurate": "Execution Engine benchmark slices are resolving the wrong parallelism guard posture on sampled execution rows.",
}

ModeLookup = Callable[[Mapping[str, Any], str], Any]
ModeSupportCheck = Callable[[str], bool]


def acceptance_hard_quality_gate_cleared(acceptance: Mapping[str, Any] | None) -> bool:
    if not isinstance(acceptance, Mapping):
        return False
    if "hard_quality_gate_cleared" in acceptance:
        return bool(acceptance.get("hard_quality_gate_cleared"))
    return str(acceptance.get("status", "")).strip() == "provisional_pass"


def acceptance_failure_labels(tokens: Sequence[str]) -> list[str]:
    labels: list[str] = []
    for token in tokens:
        key = str(token).strip()
        if not key:
            continue
        label = _ACCEPTANCE_CHECK_LABELS.get(key, key.replace("_", " "))
        if label not in labels:
            labels.append(label)
    return labels


def live_execution_contract_match(
    execution_contracts: Mapping[str, Mapping[str, Any]] | None,
    *,
    lookup_mode_mapping: ModeLookup,
    candidate_mode: str,
    baseline_mode: str,
) -> bool:
    if not isinstance(execution_contracts, Mapping):
        return True
    candidate = dict(lookup_mode_mapping(execution_contracts, candidate_mode) or {})
    baseline = dict(lookup_mode_mapping(execution_contracts, baseline_mode) or {})
    if not candidate or not baseline:
        return True
    fields = ("runner", "codex_bin", "model", "reasoning_effort")
    return all(str(candidate.get(field, "")).strip() == str(baseline.get(field, "")).strip() for field in fields)


def _lookup_mode_dict(
    summary_mapping: Mapping[str, Any] | Any,
    *,
    mode: str,
    lookup_mode_mapping: ModeLookup,
) -> dict[str, Any]:
    if not isinstance(summary_mapping, Mapping):
        return {}
    payload = lookup_mode_mapping(summary_mapping, mode)
    return dict(payload) if isinstance(payload, Mapping) else {}


def _family_quality_gate_failed(
    *,
    candidate_family: Mapping[str, Any],
    baseline_family: Mapping[str, Any],
    quality_gate_failed: bool,
) -> bool:
    return (
        float(candidate_family.get("required_path_recall_rate", 0.0) or 0.0)
        < float(baseline_family.get("required_path_recall_rate", 0.0) or 0.0)
        or float(candidate_family.get("required_path_precision_rate", 0.0) or 0.0)
        < float(baseline_family.get("required_path_precision_rate", 0.0) or 0.0)
        or float(candidate_family.get("hallucinated_surface_rate", 0.0) or 0.0)
        > float(baseline_family.get("hallucinated_surface_rate", 0.0) or 0.0)
        or float(candidate_family.get("validation_success_rate", 0.0) or 0.0)
        < float(baseline_family.get("validation_success_rate", 0.0) or 0.0)
        or float(candidate_family.get("expectation_success_rate", 0.0) or 0.0)
        < float(baseline_family.get("expectation_success_rate", 0.0) or 0.0)
        or float(candidate_family.get("false_clearance_rate", 0.0) or 0.0) > 0.0
        or (
            int(candidate_family.get("proof_state_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("proof_frontier_gate_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("proof_state_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("proof_claim_guard_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("proof_same_fingerprint_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("proof_same_fingerprint_reuse_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("context_engine_expected_packet_source_count", 0) or 0) > 0
            and float(candidate_family.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("context_engine_expected_selection_state_count", 0) or 0) > 0
            and float(candidate_family.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("context_engine_expected_workstream_count", 0) or 0) > 0
            and float(candidate_family.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("context_engine_ambiguity_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("context_engine_runtime_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("context_engine_session_namespace_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_present_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_resume_token_present_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_outcome_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_outcome_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_mode_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_next_move_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_next_move_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_closure_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_closure_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_wait_status_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_wait_status_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_validation_archetype_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_validation_archetype_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_current_phase_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_current_phase_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_last_successful_phase_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_last_successful_phase_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_authoritative_lane_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_authoritative_lane_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_target_lane_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_target_lane_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_resume_token_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_resume_token_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_host_family_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_host_family_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_model_family_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_model_family_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or (
            int(candidate_family.get("execution_engine_expected_reanchor_count", 0) or 0) > 0
            and float(candidate_family.get("execution_engine_reanchor_accuracy_rate", 0.0) or 0.0) < 1.0
        )
        or quality_gate_failed
        or (
            int(candidate_family.get("write_surface_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("write_surface_precision_rate", 0.0) or 0.0)
            < float(baseline_family.get("write_surface_precision_rate", 0.0) or 0.0)
        )
        or (
            int(candidate_family.get("write_surface_backed_scenario_count", 0) or 0) > 0
            and float(candidate_family.get("unnecessary_widening_rate", 0.0) or 0.0) > 0.15
        )
    )


def _append_failed_check_notes(
    notes: list[str],
    checks: Mapping[str, bool],
) -> None:
    for key, message in _HARD_CHECK_FAILURE_NOTES.items():
        if checks.get(key, True):
            continue
        notes.append(message)


def build_acceptance(
    *,
    mode_summaries: Mapping[str, Mapping[str, Any]],
    primary_comparison: Mapping[str, Any],
    family_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]],
    corpus_summary: Mapping[str, Any],
    fairness_findings: Sequence[str] = (),
    runtime_posture: Mapping[str, Any] | None = None,
    packet_source_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    cache_profile_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    execution_contracts: Mapping[str, Mapping[str, Any]] | None = None,
    comparison_contract: str = "",
    candidate_mode: str,
    baseline_mode: str,
    governance_slice_families: Sequence[str],
    live_comparison_contracts: Sequence[str],
    lookup_mode_mapping: ModeLookup,
    mode_supports_architecture_dossier: ModeSupportCheck,
) -> dict[str, Any]:
    candidate = _lookup_mode_dict(mode_summaries, mode=candidate_mode, lookup_mode_mapping=lookup_mode_mapping)
    baseline = _lookup_mode_dict(mode_summaries, mode=baseline_mode, lookup_mode_mapping=lookup_mode_mapping)
    architecture_candidate = _lookup_mode_dict(
        family_summaries.get("architecture", {}),
        mode=candidate_mode,
        lookup_mode_mapping=lookup_mode_mapping,
    )
    architecture_baseline = _lookup_mode_dict(
        family_summaries.get("architecture", {}),
        mode=baseline_mode,
        lookup_mode_mapping=lookup_mode_mapping,
    )
    explicit_workstream_candidate = _lookup_mode_dict(
        family_summaries.get("explicit_workstream", {}),
        mode=candidate_mode,
        lookup_mode_mapping=lookup_mode_mapping,
    )
    governance_packet_coverage_complete = all(
        float(
            _lookup_mode_dict(
                family_summaries.get(family, {}),
                mode=candidate_mode,
                lookup_mode_mapping=lookup_mode_mapping,
            ).get("odylith_packet_present_rate", 0.0)
            or 0.0
        )
        >= 1.0
        for family in governance_slice_families
        if isinstance(family_summaries.get(family), Mapping)
    )
    prompt_token_delta = float(
        primary_comparison.get("median_prompt_token_delta", primary_comparison.get("median_token_delta", 0.0))
        or 0.0
    )
    total_payload_delta = float(primary_comparison.get("median_total_payload_token_delta", 0.0) or 0.0)
    bootstrap_packet_source = (
        dict(packet_source_summaries.get("bootstrap_session", {}))
        if isinstance(packet_source_summaries, Mapping)
        and isinstance(packet_source_summaries.get("bootstrap_session"), Mapping)
        else {}
    )
    bootstrap_candidate = _lookup_mode_dict(
        bootstrap_packet_source,
        mode=candidate_mode,
        lookup_mode_mapping=lookup_mode_mapping,
    )
    bootstrap_baseline = _lookup_mode_dict(
        bootstrap_packet_source,
        mode=baseline_mode,
        lookup_mode_mapping=lookup_mode_mapping,
    )
    bootstrap_payload_delta = 0.0
    if bootstrap_candidate and bootstrap_baseline:
        bootstrap_payload_delta = benchmark_metric_helpers.summary_delta(
            bootstrap_candidate,
            bootstrap_baseline,
            "median_total_payload_tokens",
        )
    architecture_latency_delta = 0.0
    if architecture_candidate and architecture_baseline:
        architecture_latency_delta = benchmark_metric_helpers.summary_delta(
            architecture_candidate,
            architecture_baseline,
            "median_latency_ms",
        )

    candidate_scenario_count = int(candidate.get("scenario_count", 0) or 0)
    candidate_validation_backed_scenario_count = int(candidate.get("validation_backed_scenario_count", 0) or 0)
    candidate_critical_required_path_backed_scenario_count = int(
        candidate.get("critical_required_path_backed_scenario_count", 0) or 0
    )
    candidate_critical_validation_backed_scenario_count = int(
        candidate.get("critical_validation_backed_scenario_count", 0) or 0
    )
    packet_budget_guardrail_applicable = int(candidate.get("packet_scenario_count", 0) or 0) > 0
    comparative_efficiency_guardrails = odylith_benchmark_guardrails.comparative_efficiency_guardrails_applicability(
        candidate_summary=candidate,
        baseline_summary=baseline,
    )
    runtime = dict(runtime_posture or {}) if isinstance(runtime_posture, Mapping) else {}
    runtime_memory_standardization_state = str(runtime.get("memory_standardization_state", "")).strip()
    runtime_memory_backed_retrieval_ready = runtime.get("memory_backed_retrieval_ready")
    if runtime_memory_backed_retrieval_ready is None:
        runtime_memory_backed_retrieval_ready = True
    comparative_efficiency_applicable = bool(comparative_efficiency_guardrails.get("applicable"))
    live_end_to_end_comparison = str(comparison_contract or "").strip() in {
        str(token).strip() for token in live_comparison_contracts if str(token).strip()
    }
    comparative_latency_and_token_status_blocking = comparative_efficiency_applicable and not live_end_to_end_comparison

    hard_quality_checks = {
        "memory_backend_standardized": runtime_memory_standardization_state in {"", "standardized"},
        "memory_backed_retrieval_ready": bool(runtime_memory_backed_retrieval_ready),
        "required_path_recall_not_worse": float(primary_comparison.get("required_path_recall_delta", 0.0) or 0.0) >= 0.0,
        "required_path_precision_not_worse": float(primary_comparison.get("required_path_precision_delta", 0.0) or 0.0) >= 0.0,
        "hallucinated_surface_not_worse": float(primary_comparison.get("hallucinated_surface_rate_delta", 0.0) or 0.0) <= 0.0,
        "validation_success_not_worse": float(primary_comparison.get("validation_success_delta", 0.0) or 0.0) >= 0.0,
        "write_surface_precision_not_worse": (
            int(candidate.get("write_surface_backed_scenario_count", 0) or 0) == 0
            or float(primary_comparison.get("write_surface_precision_delta", 0.0) or 0.0) >= 0.0
        ),
        "unnecessary_widening_not_worse": (
            int(candidate.get("write_surface_backed_scenario_count", 0) or 0) == 0
            or float(primary_comparison.get("unnecessary_widening_rate_delta", 0.0) or 0.0) <= 0.0
        ),
        "critical_required_path_recall_not_worse": float(primary_comparison.get("critical_required_path_recall_delta", 0.0) or 0.0) >= 0.0,
        "critical_validation_success_not_worse": float(primary_comparison.get("critical_validation_success_delta", 0.0) or 0.0) >= 0.0,
        "live_execution_contract_match": live_execution_contract_match(
            execution_contracts,
            lookup_mode_mapping=lookup_mode_mapping,
            candidate_mode=candidate_mode,
            baseline_mode=baseline_mode,
        ),
        "expectation_success_not_worse": float(primary_comparison.get("expectation_success_delta", 0.0) or 0.0) >= 0.0,
        "proof_false_clearance_healthy": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("false_clearance_rate", 0.0) or 0.0) <= 0.0
        ),
        "proof_frontier_gate_accurate": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_frontier_gate_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "proof_claim_guard_accurate": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_claim_guard_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "proof_same_fingerprint_reuse_accurate": (
            int(candidate.get("proof_same_fingerprint_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_same_fingerprint_reuse_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_packet_source_accurate": (
            int(candidate.get("context_engine_expected_packet_source_count", 0) or 0) == 0
            or float(candidate.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_selection_state_accurate": (
            int(candidate.get("context_engine_expected_selection_state_count", 0) or 0) == 0
            or float(candidate.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_workstream_accurate": (
            int(candidate.get("context_engine_expected_workstream_count", 0) or 0) == 0
            or float(candidate.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_ambiguity_fail_closed": (
            int(candidate.get("context_engine_ambiguity_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_session_namespaced": (
            int(candidate.get("context_engine_runtime_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("context_engine_session_namespace_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_present": (
            int(candidate.get("execution_engine_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_present_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_resume_token_present": (
            int(candidate.get("execution_engine_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_resume_token_present_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_outcome_accurate": (
            int(candidate.get("execution_engine_expected_outcome_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_outcome_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_mode_accurate": (
            int(candidate.get("execution_engine_expected_mode_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_next_move_accurate": (
            int(candidate.get("execution_engine_expected_next_move_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_next_move_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_closure_accurate": (
            int(candidate.get("execution_engine_expected_closure_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_closure_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_wait_status_accurate": (
            int(candidate.get("execution_engine_expected_wait_status_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_wait_status_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_validation_accurate": (
            int(candidate.get("execution_engine_expected_validation_archetype_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_validation_archetype_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_current_phase_accurate": (
            int(candidate.get("execution_engine_expected_current_phase_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_current_phase_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_last_successful_phase_accurate": (
            int(candidate.get("execution_engine_expected_last_successful_phase_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_last_successful_phase_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_authoritative_lane_accurate": (
            int(candidate.get("execution_engine_expected_authoritative_lane_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_authoritative_lane_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_target_lane_accurate": (
            int(candidate.get("execution_engine_expected_target_lane_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_target_lane_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_resume_token_accurate": (
            int(candidate.get("execution_engine_expected_resume_token_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_resume_token_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_host_family_accurate": (
            int(candidate.get("execution_engine_expected_host_family_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_host_family_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_model_family_accurate": (
            int(candidate.get("execution_engine_expected_model_family_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_model_family_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_reanchor_accurate": (
            int(candidate.get("execution_engine_expected_reanchor_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_reanchor_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        **odylith_benchmark_execution_engine.acceptance_checks(candidate),
        "candidate_expectation_success_positive": (
            candidate_scenario_count == 0
            or float(candidate.get("expectation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_validation_success_positive": (
            candidate_validation_backed_scenario_count == 0
            or float(candidate.get("validation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_critical_required_path_recall_positive": (
            candidate_critical_required_path_backed_scenario_count == 0
            or float(candidate.get("critical_required_path_recall_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_critical_validation_success_positive": (
            candidate_critical_validation_backed_scenario_count == 0
            or float(candidate.get("critical_validation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "explicit_workstream_expectation_positive": (
            not explicit_workstream_candidate
            or float(explicit_workstream_candidate.get("expectation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "critical_metric_coverage_complete": (
            int(corpus_summary.get("correctness_critical_scenario_count", 0) or 0)
            == int(corpus_summary.get("critical_required_path_backed_scenario_count", 0) or 0)
            == int(corpus_summary.get("critical_validation_backed_scenario_count", 0) or 0)
        ),
        "fairness_contract_passed": not any(str(token).strip() for token in fairness_findings),
        "selected_cache_profiles_clear_gate": (
            True
            if not dict(cache_profile_summaries or {})
            else all(
                acceptance_hard_quality_gate_cleared(dict(summary.get("acceptance", {})))
                for summary in dict(cache_profile_summaries or {}).values()
                if isinstance(summary, Mapping)
            )
        ),
    }
    secondary_guardrail_checks = {
        "latency_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or float(primary_comparison.get("median_latency_delta_ms", 0.0) or 0.0)
        <= _SECONDARY_LATENCY_GUARDRAIL_MAX_DELTA_MS,
        "prompt_delta_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or prompt_token_delta <= _SECONDARY_PROMPT_TOKEN_GUARDRAIL_MAX_DELTA,
        "total_payload_delta_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or total_payload_delta <= _SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA,
        "bootstrap_payload_delta_within_guardrail": (
            not comparative_latency_and_token_status_blocking
            or not bootstrap_candidate
            or not bootstrap_baseline
            or bootstrap_payload_delta <= _SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA
        ),
        "tight_budget_behavior_healthy": (not packet_budget_guardrail_applicable)
        or float(candidate.get("within_budget_rate", 0.0) or 0.0) >= _SECONDARY_WITHIN_BUDGET_RATE_MIN,
        "architecture_latency_within_guardrail": (
            not comparative_latency_and_token_status_blocking
            or not architecture_candidate
            or not architecture_baseline
            or not mode_supports_architecture_dossier(baseline_mode)
            or architecture_latency_delta <= _SECONDARY_ARCHITECTURE_LATENCY_GUARDRAIL_MAX_DELTA_MS
        ),
    }
    advisory_checks = {
        "widening_rate_healthy": float(candidate.get("odylith_requires_widening_rate", 0.0) or 0.0) <= 0.15,
        "governance_packet_coverage_complete": governance_packet_coverage_complete,
    }
    checks = {
        **hard_quality_checks,
        **secondary_guardrail_checks,
        **advisory_checks,
        "packet_budget_healthy": secondary_guardrail_checks["tight_budget_behavior_healthy"],
        "architecture_not_slower": secondary_guardrail_checks["architecture_latency_within_guardrail"],
    }
    hard_quality_gate_cleared = all(hard_quality_checks.values()) if candidate and baseline else False
    secondary_guardrails_cleared = all(secondary_guardrail_checks.values()) if candidate and baseline else False
    advisory_checks_cleared = all(advisory_checks.values()) if candidate else False
    passed = hard_quality_gate_cleared and secondary_guardrails_cleared

    notes: list[str] = []
    hard_gate_families: list[str] = []
    advisory_families: list[str] = []
    if not baseline:
        notes.append("`odylith_off` summary is unavailable; rerun with the raw Codex CLI lane enabled.")
    if fairness_findings:
        notes.append("Benchmark fairness contract findings are present; the published pair is not release-safe until they are resolved.")

    for family, family_modes in family_summaries.items():
        candidate_family = _lookup_mode_dict(
            family_modes,
            mode=candidate_mode,
            lookup_mode_mapping=lookup_mode_mapping,
        )
        baseline_family = _lookup_mode_dict(
            family_modes,
            mode=baseline_mode,
            lookup_mode_mapping=lookup_mode_mapping,
        )
        if not candidate_family or not baseline_family:
            continue
        if _family_quality_gate_failed(
            candidate_family=candidate_family,
            baseline_family=baseline_family,
            quality_gate_failed=odylith_benchmark_execution_engine.quality_gate_failed(candidate_family),
        ):
            hard_gate_families.append(family)
        if (
            family != "architecture"
            and float(candidate_family.get("odylith_requires_widening_rate", 0.0) or 0.0) > 0.15
        ) or (
            family in governance_slice_families
            and float(candidate_family.get("odylith_packet_present_rate", 0.0) or 0.0) < 1.0
        ):
            advisory_families.append(family)

    hard_gate_failures = [name for name, ok in hard_quality_checks.items() if not ok]
    secondary_guardrail_failures = [name for name, ok in secondary_guardrail_checks.items() if not ok]
    advisory_failures = [name for name, ok in advisory_checks.items() if not ok]
    hard_gate_failure_labels = acceptance_failure_labels(hard_gate_failures)
    secondary_guardrail_failure_labels = acceptance_failure_labels(secondary_guardrail_failures)
    advisory_failure_labels = acceptance_failure_labels(advisory_failures)

    if hard_quality_gate_cleared:
        notes.append("Odylith clears the hard quality gate against `odylith_off` on this sampled corpus.")
    else:
        notes.append("Odylith has not yet cleared the hard quality gate against `odylith_off` on this sampled corpus.")
    if hard_gate_failure_labels:
        notes.append("Hard-gate blockers: " + "; ".join(hard_gate_failure_labels[:4]) + ".")
    _append_failed_check_notes(notes, hard_quality_checks)

    if not hard_quality_checks["live_execution_contract_match"]:
        notes.append("`odylith_on` and `odylith_off` did not run on the same Codex CLI model/reasoning contract.")
    if hard_quality_checks["memory_backed_retrieval_ready"]:
        notes.append("Benchmark proof used active local LanceDB plus Tantivy retrieval memory.")
    else:
        notes.append("Benchmark ran without an active local LanceDB/Tantivy retrieval substrate.")
    if str(runtime.get("remote_retrieval_status", "")).strip() == "disabled":
        notes.append("Vespa is optional and currently disabled; the current benchmark proof is local-first, not remote-assisted.")
    elif bool(runtime.get("remote_retrieval_enabled")):
        notes.append(
            "Vespa remote retrieval is active in "
            + (str(runtime.get("remote_retrieval_mode", "")).strip() or "augment")
            + " mode for this benchmark posture."
        )
    if comparative_efficiency_applicable and not live_end_to_end_comparison:
        notes.append(
            "Relative latency and token-efficiency guardrails are active because both `odylith_on` and `odylith_off` produced successful outcomes on the sampled corpus."
        )
    elif comparative_efficiency_applicable and live_end_to_end_comparison:
        notes.append(
            "Live proof keeps benchmark time to valid outcome and full-session token spend published, but not status-blocking, because the public pair measures contention-shared matched-pair wall clock and multi-turn session accumulation rather than interactive product latency or initial prompt size."
        )
    else:
        reason = str(comparative_efficiency_guardrails.get("reason", "")).strip()
        if reason == "baseline_has_no_successful_outcomes":
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because `odylith_off` produced no successful outcomes on the sampled corpus."
            )
        elif reason == "candidate_has_no_successful_outcomes":
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because `odylith_on` produced no successful outcomes on the sampled corpus."
            )
        else:
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because the sampled corpus did not produce successful outcomes on both compared lanes."
            )
    if not packet_budget_guardrail_applicable:
        notes.append("Tighter-budget behavior was not applied because the sampled corpus contains no packet-backed scenarios.")
    if secondary_guardrails_cleared:
        notes.append("Secondary latency, efficiency, and tighter-budget guardrails are within threshold on this sampled corpus.")
    elif secondary_guardrail_failure_labels:
        notes.append("Secondary guardrails needing attention: " + "; ".join(secondary_guardrail_failure_labels[:4]) + ".")
    if float(primary_comparison.get("median_latency_delta_ms", 0.0) or 0.0) > 0.0:
        notes.append(
            "Odylith takes longer than raw Codex CLI to reach a valid outcome on the benchmark pair; this stays published as a secondary tradeoff and only blocks status when the comparative live-efficiency guardrail is actually status-blocking."
        )
    if prompt_token_delta > 0.0:
        notes.append(
            "Odylith uses more full-session input tokens than raw Codex CLI on the live run; that overhead stays visible, but it is not the same thing as initial prompt size."
        )
    if hard_gate_families:
        notes.append(f"Hard-gate families needing attention: {', '.join(hard_gate_families[:5])}.")

    failed_profiles = [
        str(profile).strip()
        for profile, summary in dict(cache_profile_summaries or {}).items()
        if isinstance(summary, Mapping)
        and not acceptance_hard_quality_gate_cleared(dict(summary.get("acceptance", {})))
    ]
    if failed_profiles:
        notes.append("Selected cache profiles still failing the hard quality gate: " + ", ".join(failed_profiles[:4]) + ".")
    if total_payload_delta > 0.0:
        notes.append(
            f"Total runtime-contract payload is still heavier than baseline by {total_payload_delta:.3f} median tokens; that remains a published secondary cost and only blocks status when the comparative payload guardrail is applicable and breached."
        )
    if bootstrap_candidate and bootstrap_baseline and bootstrap_payload_delta > 0.0:
        notes.append(
            f"Bootstrap-session payload is still heavier than baseline by {bootstrap_payload_delta:.3f} median tokens; this first-turn tax now has its own benchmark guardrail."
        )
    if architecture_candidate and architecture_baseline and architecture_latency_delta > 0.0:
        notes.append(
            f"Architecture still takes {architecture_latency_delta:.3f}ms longer than baseline to reach a valid outcome in the published comparison view."
        )
    if float(candidate.get("odylith_requires_widening_rate", 0.0) or 0.0) > 0.15:
        notes.append(
            "Widening is still too frequent in the published candidate view; this stays published as advisory mechanism attention rather than the primary outcome gate."
        )
    if float(primary_comparison.get("hallucinated_surface_rate_delta", 0.0) or 0.0) > 0.0:
        notes.append("Published observed-surface drift is still worse than baseline; tighten the evidence cone before widening more families.")
    if (
        int(candidate.get("write_surface_backed_scenario_count", 0) or 0) > 0
        and float(primary_comparison.get("unnecessary_widening_rate_delta", 0.0) or 0.0) > 0.0
    ):
        notes.append("Published write-surface widening is still worse than baseline on scenarios that actually require writes.")
    if not governance_packet_coverage_complete:
        notes.append(
            "Governance-family packet coverage is incomplete; this stays published as advisory mechanism attention, not as the primary outcome gate."
        )
    if advisory_failure_labels:
        notes.append("Advisory mechanism checks needing attention: " + "; ".join(advisory_failure_labels[:4]) + ".")
    if advisory_families:
        notes.append("Advisory mechanism families needing attention: " + ", ".join(sorted(set(advisory_families))[:5]) + ".")
    if dict(cache_profile_summaries or {}) and hard_quality_checks["selected_cache_profiles_clear_gate"]:
        notes.append(
            "All selected cache profiles clear the hard quality gate, so the published result is not relying on a single flattering cache posture."
        )
    notes.append(
        "This harness blocks status on the hard quality gate first. In live proof, benchmark time to valid outcome and full-session token spend stay published as diagnostics, while tighter-budget behavior remains an active secondary guardrail."
    )
    return {
        "status": "provisional_pass" if passed else "hold",
        "hard_quality_gate_cleared": hard_quality_gate_cleared,
        "secondary_guardrails_cleared": secondary_guardrails_cleared,
        "advisory_checks_cleared": advisory_checks_cleared,
        "comparative_efficiency_guardrails_applicable": comparative_efficiency_applicable,
        "comparative_latency_and_token_status_blocking": comparative_latency_and_token_status_blocking,
        "comparative_efficiency_guardrail_reason": str(comparative_efficiency_guardrails.get("reason", "")).strip(),
        "packet_budget_guardrail_applicable": packet_budget_guardrail_applicable,
        "hard_quality_checks": hard_quality_checks,
        "secondary_guardrail_checks": secondary_guardrail_checks,
        "advisory_checks": advisory_checks,
        "hard_gate_failures": hard_gate_failures,
        "hard_gate_failure_labels": hard_gate_failure_labels,
        "secondary_guardrail_failures": secondary_guardrail_failures,
        "secondary_guardrail_failure_labels": secondary_guardrail_failure_labels,
        "advisory_failures": advisory_failures,
        "advisory_failure_labels": advisory_failure_labels,
        "checks": checks,
        "weak_families": hard_gate_families,
        "advisory_families": sorted(set(advisory_families)),
        "notes": notes,
    }


__all__ = [
    "acceptance_failure_labels",
    "acceptance_hard_quality_gate_cleared",
    "build_acceptance",
    "live_execution_contract_match",
]
