"""Extracted assessment scoring for the subagent router."""

from __future__ import annotations

from odylith.runtime.orchestration import subagent_router
from odylith.runtime.orchestration import subagent_router_signal_summary

request_with_consumer_write_policy = subagent_router_signal_summary.request_with_consumer_write_policy
_context_signal_summary = subagent_router_signal_summary._context_signal_summary
_normalize_string = subagent_router_signal_summary._normalize_string
_normalize_list = subagent_router_signal_summary._normalize_list
_normalize_token = subagent_router_signal_summary._normalize_token
_clamp_score = subagent_router_signal_summary._clamp_score
_int_value = subagent_router_signal_summary._int_value
_context_signal_score = subagent_router_signal_summary._context_signal_score
_context_signal_bool = subagent_router_signal_summary._context_signal_bool
_scaled_numeric_signal = subagent_router_signal_summary._scaled_numeric_signal
_normalized_rate = subagent_router_signal_summary._normalized_rate
_latency_pressure_signal = subagent_router_signal_summary._latency_pressure_signal
_infer_prompt_semantics = subagent_router_signal_summary._infer_prompt_semantics
_infer_explicit_paths = subagent_router_signal_summary._infer_explicit_paths
_surface_prefixes_for_path = subagent_router_signal_summary._surface_prefixes_for_path
_infer_phase_tokens = subagent_router_signal_summary._infer_phase_tokens
_contains_any = subagent_router_signal_summary._contains_any
_keyword_score = subagent_router_signal_summary._keyword_score
_router_profile_from_token = subagent_router_signal_summary._router_profile_from_token
_classify_task_family = subagent_router_signal_summary._classify_task_family
_FEATURE_KEYWORDS = subagent_router_signal_summary._FEATURE_KEYWORDS
_WRITE_KEYWORDS = subagent_router_signal_summary._WRITE_KEYWORDS
_AMBIGUITY_KEYWORDS = subagent_router_signal_summary._AMBIGUITY_KEYWORDS
_RISK_KEYWORDS = subagent_router_signal_summary._RISK_KEYWORDS
_COORDINATION_KEYWORDS = subagent_router_signal_summary._COORDINATION_KEYWORDS
_REVERSIBILITY_KEYWORDS = subagent_router_signal_summary._REVERSIBILITY_KEYWORDS
_MECHANICAL_KEYWORDS = subagent_router_signal_summary._MECHANICAL_KEYWORDS
_VALIDATION_KEYWORDS = subagent_router_signal_summary._VALIDATION_KEYWORDS
_LATENCY_KEYWORDS = subagent_router_signal_summary._LATENCY_KEYWORDS
_DEPTH_KEYWORDS = subagent_router_signal_summary._DEPTH_KEYWORDS
_RUNTIME_EARNED_DEPTH_SELECTION_MODES = subagent_router_signal_summary._RUNTIME_EARNED_DEPTH_SELECTION_MODES
_SCORE_MAX = subagent_router_signal_summary._SCORE_MAX
TaskAssessment = subagent_router.TaskAssessment
RouterProfile = subagent_router.RouterProfile


def assess_request(request: subagent_router.RouteRequest) -> subagent_router.TaskAssessment:
    prompt = _normalize_string(request.prompt)
    criteria = " ".join(_normalize_list(request.acceptance_criteria))
    validation_commands = _normalize_list(request.validation_commands)
    text = f"{prompt} {criteria}".strip().lower()
    semantic_signals = _infer_prompt_semantics(prompt, request.acceptance_criteria)
    context_signal_summary = _context_signal_summary(request)
    has_structured_handoff = any(
        (
            context_signal_summary["support_leaf"],
            context_signal_summary["primary_leaf"],
            context_signal_summary["route_ready"],
            bool(context_signal_summary["routing_confidence_level"]),
            bool(context_signal_summary["parallelism_hint"]),
            bool(context_signal_summary["scope_role"]),
            context_signal_summary["spawn_worthiness_score"] > 0,
            context_signal_summary["merge_burden_score"] > 0,
            context_signal_summary["dependency_depth_score"] > 0,
        )
    )
    explicit_paths = [*request.allowed_paths, *_infer_explicit_paths(f"{prompt} {criteria}".strip())]
    explicit_path_count = len({token for token in explicit_paths if token})
    explicit_prefixes = {
        prefix
        for path in explicit_paths
        for prefix in _surface_prefixes_for_path(path)
        if prefix
    }
    explicit_component_count = len({token for token in request.components if token})
    explicit_workstream_count = len({token for token in request.workstreams if token})
    feature_reasons: dict[str, list[str]] = {}

    phase_tokens = _infer_phase_tokens(text, task_kind=request.task_kind, phase=request.phase)
    mixed_phase = len(phase_tokens.intersection({"implementation", "analysis", "review", "planning"})) >= 2
    bounded_scope_hits = len(semantic_signals.get("bounded_scope", []))
    open_ended_scope_hits = len(semantic_signals.get("open_ended_scope", []))
    diagnostic_hits = len(semantic_signals.get("diagnostic", []))
    synthesis_required = bool(semantic_signals.get("synthesis_required"))
    docs_surface_prefixes = {"docs", "skills", "agents-guidelines"}
    docs_only_scope = bool(explicit_prefixes.intersection(docs_surface_prefixes)) and explicit_prefixes.difference(
        {"odylith"}
    ).issubset(docs_surface_prefixes)
    tests_only_scope = bool(explicit_prefixes) and explicit_prefixes.issubset({"tests", "mocks"})
    governance_only_scope = "odylith" in explicit_prefixes and explicit_prefixes.issubset(
        {"odylith", "docs", "skills", "agents-guidelines"}
    )
    high_risk_prefix_scope = bool(explicit_prefixes.intersection({"infra", "contracts"}))

    task_kind = request.task_kind or ("feature_implementation" if _contains_any(text, _FEATURE_KEYWORDS) else "")
    if not task_kind:
        if "implementation" in phase_tokens and "review" not in phase_tokens and "planning" not in phase_tokens:
            task_kind = "implementation"
        elif "planning" in phase_tokens:
            task_kind = "planning"
        elif "review" in phase_tokens:
            task_kind = "review"
        elif "analysis" in phase_tokens:
            task_kind = "analysis"
        else:
            task_kind = "analysis"

    feature_implementation = task_kind == "feature_implementation" or _contains_any(text, _FEATURE_KEYWORDS)
    analysis_only_hint = request.task_kind in {"analysis", "review"} and not request.needs_write
    needs_write = bool(
        request.needs_write
        or (
            not analysis_only_hint
            and ("implementation" in phase_tokens or _contains_any(text, _WRITE_KEYWORDS))
        )
    )
    if analysis_only_hint:
        phase_tokens.discard("implementation")
    if (
        request.task_kind in {"analysis", "review"}
        and not needs_write
        and phase_tokens.issubset({"analysis", "review", "planning"})
        and not _contains_any(text, ("coordinate", "rollout", "merge", "handoff", "integrate"))
    ):
        mixed_phase = False
    ambiguity = _keyword_score(text, _AMBIGUITY_KEYWORDS)
    if needs_write and not request.acceptance_criteria:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("write task lacks explicit acceptance criteria")
    if "?" in prompt:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt is framed as an open question")
    if open_ended_scope_hits >= 2:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt uses open-ended architecture or redesign language")

    blast_radius = _keyword_score(text, _RISK_KEYWORDS)
    if explicit_path_count >= 4:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("many explicit paths broaden the slice")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("multiple components or workstreams widen the blast radius")
    if docs_only_scope or tests_only_scope:
        blast_radius = _clamp_score(blast_radius - 1)
        feature_reasons.setdefault("blast_radius", []).append("owned paths stay in docs/tests scope, which caps runtime blast radius")
    if high_risk_prefix_scope:
        blast_radius = _clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("infra/contracts ownership raises blast radius")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        blast_radius = min(blast_radius, 2)
        feature_reasons.setdefault("blast_radius", []).append("docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation")

    context_breadth = _clamp_score(
        (1 if explicit_path_count >= 2 else 0)
        + (1 if explicit_path_count >= 4 else 0)
        + (1 if explicit_component_count >= 2 else 0)
        + (1 if explicit_workstream_count >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 3 else 0)
        + (1 if mixed_phase else 0)
        + (1 if _contains_any(text, ("cross-file", "cross repo", "repo-wide", "multiple files")) else 0)
        + (1 if open_ended_scope_hits >= 2 else 0)
    )
    if context_breadth:
        feature_reasons.setdefault("context_breadth", []).append("slice spans multiple paths, phases, or acceptance targets")

    coordination_cost = _keyword_score(text, _COORDINATION_KEYWORDS)
    if mixed_phase:
        coordination_cost = _clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("prompt mixes planning/review/integration phases")
    if explicit_path_count >= 5:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("many touched paths imply coordination overhead")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("multiple components or workstreams increase coordination cost")
    if request.requires_multi_agent_adjudication:
        coordination_cost = _clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("request explicitly needs multi-agent adjudication")
    if open_ended_scope_hits >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("open-ended scope language increases coordination risk")
    if governance_only_scope and request.needs_write:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("governed artifact updates often require main-thread integration")

    reversibility_risk = _keyword_score(text, _REVERSIBILITY_KEYWORDS)
    if request.correctness_critical:
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("request explicitly marks correctness as critical")
    if docs_only_scope or tests_only_scope:
        reversibility_risk = _clamp_score(reversibility_risk - 1)
        feature_reasons.setdefault("reversibility_risk", []).append("docs/tests-only ownership lowers reversibility risk")
    if high_risk_prefix_scope:
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("infra/contracts ownership raises reversibility risk")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        reversibility_risk = min(reversibility_risk, 2)
        feature_reasons.setdefault("reversibility_risk", []).append(
            "docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation"
        )

    mechanicalness = _keyword_score(text, _MECHANICAL_KEYWORDS)
    if explicit_path_count == 1:
        mechanicalness = _clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("single explicit path suggests a bounded slice")
    if bounded_scope_hits and explicit_path_count <= 3:
        mechanicalness = _clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("prompt uses bounded-scope language")
    mechanicalness = _clamp_score(
        mechanicalness
        - (1 if ambiguity >= 3 else 0)
        - (1 if blast_radius >= 3 else 0)
        - (1 if feature_implementation else 0)
        - (1 if open_ended_scope_hits >= 2 else 0)
    )

    write_scope_clarity = _SCORE_MAX if not needs_write else 0
    if needs_write:
        if explicit_path_count >= 1:
            write_scope_clarity += 2
        if explicit_path_count >= 3:
            write_scope_clarity += 1
        if request.acceptance_criteria:
            write_scope_clarity += 1
        if bounded_scope_hits:
            write_scope_clarity += 1
        if _contains_any(text, ("repo-wide", "broad refactor", "sweeping")):
            write_scope_clarity -= 2
        if mixed_phase:
            write_scope_clarity -= 1
        if open_ended_scope_hits >= 2:
            write_scope_clarity -= 1
        write_scope_clarity = _clamp_score(write_scope_clarity)
    if write_scope_clarity < 2 and needs_write:
        feature_reasons.setdefault("write_scope_clarity", []).append("write ownership is weak or unbounded")

    acceptance_signal_count = sum(1 for token in _VALIDATION_KEYWORDS if token in criteria.lower())
    acceptance_clarity = _clamp_score(
        (1 if request.acceptance_criteria else 0)
        + (1 if len(request.acceptance_criteria) >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 4 else 0)
        + (1 if acceptance_signal_count >= 1 else 0)
    )
    if needs_write and acceptance_clarity <= 1:
        feature_reasons.setdefault("acceptance_clarity", []).append("write slice lacks a strong acceptance contract")

    artifact_specificity = _clamp_score(
        (1 if explicit_path_count or request.artifacts else 0)
        + (1 if 1 <= explicit_path_count <= 3 else 0)
        + (1 if request.artifacts else 0)
        + (1 if explicit_component_count or explicit_workstream_count else 0)
        + (1 if bounded_scope_hits else 0)
        - (1 if explicit_path_count >= 6 else 0)
        - (1 if open_ended_scope_hits >= 2 else 0)
    )
    if needs_write and artifact_specificity <= 1:
        feature_reasons.setdefault("artifact_specificity", []).append("few explicit artifacts or paths anchor the slice")

    validation_text = " ".join([criteria, *validation_commands]).lower()
    validation_signal_count = sum(1 for token in _VALIDATION_KEYWORDS if token in validation_text)
    validation_clarity = _clamp_score(
        (1 if validation_signal_count >= 1 else 0)
        + (1 if validation_commands else 0)
        + (1 if len(validation_commands) >= 2 or validation_signal_count >= 2 else 0)
        + (
            1
            if any(
                command.startswith(("pytest", "make ", "python -m pytest", "hatch run pytest"))
                for command in validation_commands
            )
            else 0
        )
    )

    latency_pressure = _keyword_score(text, _LATENCY_KEYWORDS)
    if request.latency_sensitive:
        latency_pressure = _clamp_score(latency_pressure + 2)
        feature_reasons.setdefault("latency_pressure", []).append("request explicitly prefers low latency")

    requested_depth = _keyword_score(text, _DEPTH_KEYWORDS)
    accuracy_bias = 0
    if request.accuracy_preference in {"accuracy", "max_accuracy", "maximum_accuracy"}:
        accuracy_bias += 1
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"}:
        requested_depth = _clamp_score(requested_depth + 2)
        accuracy_bias += 1
    if feature_implementation:
        accuracy_bias += 2
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "feature implementation leans toward stronger coding-optimized or GPT-5.4 profiles"
        )
    elif task_kind == "implementation":
        accuracy_bias += 1
    if request.correctness_critical:
        accuracy_bias += 1
        requested_depth = _clamp_score(requested_depth + 1)
    if diagnostic_hits >= 2:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("diagnostic language suggests deeper synthesis or failure analysis")
    if synthesis_required:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("prompt requires synthesis instead of isolated lookups")
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"} and needs_write:
        accuracy_bias += 1
        feature_reasons.setdefault("requested_depth", []).append("operator explicitly prefers maximum accuracy for this write slice")

    base_confidence_boost = False
    if context_signal_summary["grounding_score"] >= 3 and context_signal_summary["evidence_quality_score"] >= 3:
        ambiguity = _clamp_score(ambiguity - 1)
        feature_reasons.setdefault("grounding", []).append(
            "routing_handoff reported grounded high-quality evidence, so ambiguity was reduced"
        )
    if context_signal_summary["actionability_score"] >= 3:
        if needs_write:
            write_scope_clarity = _clamp_score(write_scope_clarity + 1)
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported actionable bounded context for this slice"
        )
    if context_signal_summary["validation_burden_score"] >= 3:
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "routing_handoff reported a heavier validation burden that merits deeper reasoning"
        )
    if context_signal_summary["coordination_score"] >= 3:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append(
            "routing_handoff reported higher coordination or merge burden than the prompt alone exposed"
        )
    if context_signal_summary["risk_score"] >= 3:
        blast_radius = _clamp_score(blast_radius + 1)
        reversibility_risk = _clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported elevated correctness or change risk"
        )
    if context_signal_summary["utility_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported a high-value retained context set for this slice"
        )
    if context_signal_summary["token_efficiency_score"] >= 3:
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported strong evidence value per retained token"
        )
    if context_signal_summary["optimization_health_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime optimization posture shows the retained packet is compact and healthy"
        )
    history_budget_reliable = bool(
        context_signal_summary["optimization_within_budget_rate"] >= 0.75
        and context_signal_summary["optimization_high_utility_rate"] >= 0.5
    )
    history_execution_reliable = bool(
        context_signal_summary["optimization_route_ready_rate"] >= 0.5
        and context_signal_summary["optimization_native_spawn_ready_rate"] >= 0.5
        and context_signal_summary["optimization_runtime_backed_execution_rate"] >= 0.5
    )
    history_deep_reasoning_reliable = bool(
        context_signal_summary["optimization_deep_reasoning_ready_rate"] >= 0.5
        and context_signal_summary["optimization_avg_context_density_score"] >= 2.0
        and context_signal_summary["optimization_avg_reasoning_readiness_score"] >= 2.0
    )
    history_prefers_local = bool(
        context_signal_summary["optimization_hold_local_rate"] >= 0.5
        and context_signal_summary["optimization_hold_local_rate"]
        > context_signal_summary["optimization_delegated_lane_rate"]
    )
    history_effective_yield_score = max(
        0.0,
        min(1.0, float(context_signal_summary["optimization_avg_effective_yield_score"] or 0.0)),
    )
    history_high_yield_rate = _normalized_rate(context_signal_summary["optimization_high_yield_rate"])
    history_reliable_high_yield_rate = _normalized_rate(
        context_signal_summary["optimization_reliable_high_yield_rate"]
    )
    history_yield_state = _normalize_token(context_signal_summary["optimization_yield_state"])
    control_advisory_state = context_signal_summary["control_advisory_state"]
    control_advisory_confidence_score = context_signal_summary["control_advisory_confidence_score"]
    control_advisory_reasoning_mode = context_signal_summary["control_advisory_reasoning_mode"]
    control_advisory_depth = context_signal_summary["control_advisory_depth"]
    control_advisory_delegation = context_signal_summary["control_advisory_delegation"]
    control_advisory_parallelism = context_signal_summary["control_advisory_parallelism"]
    control_advisory_packet_strategy = context_signal_summary["control_advisory_packet_strategy"]
    control_advisory_budget_mode = context_signal_summary["control_advisory_budget_mode"]
    control_advisory_retrieval_focus = context_signal_summary["control_advisory_retrieval_focus"]
    control_advisory_speed_mode = context_signal_summary["control_advisory_speed_mode"]
    packet_strategy = context_signal_summary["packet_strategy"]
    budget_mode = context_signal_summary["budget_mode"]
    retrieval_focus = context_signal_summary["retrieval_focus"]
    speed_mode = context_signal_summary["speed_mode"]
    packet_reliability = context_signal_summary["packet_reliability"]
    selection_bias = context_signal_summary["selection_bias"]
    control_advisory_freshness_bucket = context_signal_summary["control_advisory_freshness_bucket"]
    control_advisory_evidence_strength_score = context_signal_summary["control_advisory_evidence_strength_score"]
    control_advisory_signal_conflict = bool(context_signal_summary["control_advisory_signal_conflict"])
    control_advisory_sample_balance = context_signal_summary["control_advisory_sample_balance"]
    control_advisory_present = bool(
        control_advisory_state
        or control_advisory_reasoning_mode
        or control_advisory_depth
        or control_advisory_delegation
        or control_advisory_parallelism
        or control_advisory_packet_strategy
        or control_advisory_budget_mode
        or control_advisory_retrieval_focus
        or control_advisory_speed_mode
        or control_advisory_freshness_bucket
        or control_advisory_confidence_score > 0
        or control_advisory_evidence_strength_score > 0
        or control_advisory_signal_conflict
        or control_advisory_sample_balance not in {"", "none"}
    )
    control_advisory_reliable = bool(
        control_advisory_present
        and control_advisory_confidence_score >= 3
        and control_advisory_evidence_strength_score >= 3
        and control_advisory_freshness_bucket in {"fresh", "recent"}
        and not control_advisory_signal_conflict
    )
    control_advisory_guarded = bool(
        control_advisory_present
        and (
            control_advisory_freshness_bucket in {"aging", "stale"}
            or control_advisory_evidence_strength_score <= 1
            or control_advisory_signal_conflict
            or control_advisory_sample_balance in {"thin", "none"}
        )
    )
    packet_profile_present = bool(
        packet_strategy
        or budget_mode
        or retrieval_focus
        or speed_mode
        or packet_reliability
        or selection_bias
    )
    packet_profile_reliable = packet_reliability == "reliable"
    packet_profile_guarded = packet_reliability == "guarded"
    if control_advisory_guarded:
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are fresh-evidence guarded, so the router reduced trust in historical promotion signals until newer or better-balanced outcomes accumulate"
        )
    elif packet_profile_guarded and not control_advisory_present:
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical and requested_depth >= 2:
            requested_depth = _clamp_score(requested_depth - 1)
        if accuracy_bias >= 2:
            accuracy_bias = _clamp_score(accuracy_bias - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet was assembled under guarded reliability, so the router stayed conservative until fresher packet evidence lands"
        )
    if history_budget_reliable:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "optimization history shows recent packets stay within budget while retaining useful evidence"
        )
    if history_execution_reliable:
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "optimization history shows recent route-ready slices also stay native-spawn-ready under runtime-backed control"
        )
    if (
        history_deep_reasoning_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "optimization history shows deeper delegated reasoning stays grounded, budget-safe, and runtime-backed on similar slices"
        )
    elif (
        not request.correctness_critical
        and requested_depth >= 3
        and 0.0 < context_signal_summary["optimization_deep_reasoning_ready_rate"] < 0.5
        and context_signal_summary["optimization_within_budget_rate"] < 0.5
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "recent optimization history shows deeper delegated reasoning still overruns budget or lacks readiness on similar slices"
        )
    if history_prefers_local and (context_signal_summary["narrowing_required"] or not context_signal_summary["route_ready"]):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent optimization history still trends toward hold-local execution while narrowing remains unresolved"
        )
    if (
        context_signal_summary["optimization_packet_alignment_state"] == "drifting"
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        accuracy_bias = _clamp_score(accuracy_bias - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packetizer alignment is drifting from the measured advisory loop, so the router reduced depth until packet shaping stabilizes again"
        )
    evaluation_depth_promote = context_signal_summary["evaluation_control_depth"] == "promote_when_grounded"
    evaluation_narrow_first = context_signal_summary["evaluation_control_depth"] == "narrow_first"
    evaluation_hold_local_bias = context_signal_summary["evaluation_control_delegation"] == "hold_local_bias"
    evaluation_parallel_guarded = context_signal_summary["evaluation_control_parallelism"] == "guarded"
    evaluation_precision_first = context_signal_summary["evaluation_control_packet_strategy"] == "precision_first"
    evaluation_decision_quality_score = _normalized_rate(
        context_signal_summary["evaluation_decision_quality_score"]
    )
    evaluation_decision_quality_state = _normalize_token(
        context_signal_summary["evaluation_decision_quality_state"]
    )
    evaluation_decision_quality_confidence = _clamp_score(
        context_signal_summary["evaluation_decision_quality_confidence_score"]
    )
    evaluation_closeout_observation_rate = _normalized_rate(
        context_signal_summary["evaluation_closeout_observation_rate"]
    )
    evaluation_delegation_regret_rate = _normalized_rate(
        context_signal_summary["evaluation_delegation_regret_rate"]
    )
    evaluation_followup_churn_rate = _normalized_rate(
        context_signal_summary["evaluation_followup_churn_rate"]
    )
    evaluation_merge_underestimate_rate = _normalized_rate(
        context_signal_summary["evaluation_merge_underestimate_rate"]
    )
    evaluation_validation_underestimate_rate = _normalized_rate(
        context_signal_summary["evaluation_validation_underestimate_rate"]
    )
    decision_quality_reliable = bool(
        evaluation_decision_quality_confidence >= 3
        and evaluation_closeout_observation_rate >= 0.34
        and evaluation_decision_quality_state not in {"bootstrap", "insufficient"}
    )
    decision_quality_fragile = bool(
        decision_quality_reliable
        and (
            evaluation_decision_quality_state == "fragile"
            or evaluation_decision_quality_score < 0.55
        )
    )
    decision_quality_trusted = bool(
        decision_quality_reliable
        and evaluation_decision_quality_state == "trusted"
        and evaluation_decision_quality_score >= 0.72
    )
    if (
        control_advisory_depth == "promote_when_grounded"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and not context_signal_summary["narrowing_required"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently endorse deeper reasoning on grounded route-ready slices"
        )
    if control_advisory_depth == "narrow_first" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer narrow-first execution because recent outcomes are still unstable"
        )
    if (
        decision_quality_reliable
        and evaluation_validation_underestimate_rate >= 0.25
        and not request.correctness_critical
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is still underpredicting validation pressure on recent delegated slices, so the router tightened depth until validation calibration improves"
        )
    elif (
        not decision_quality_reliable
        and (
            evaluation_delegation_regret_rate >= 0.25
            or evaluation_followup_churn_rate >= 0.25
            or evaluation_merge_underestimate_rate >= 0.2
            or evaluation_validation_underestimate_rate >= 0.25
        )
    ):
        feature_reasons.setdefault("context_signals", []).append(
            "decision-quality outcome evidence is still thin or only partially closed out, so the router kept regret and calibration metrics advisory-only for now"
        )
    if (
        control_advisory_reasoning_mode == "earn_depth"
        and control_advisory_reliable
        and context_signal_summary["grounding_score"] >= 3
        and context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories say deeper reasoning has to be earned, and this slice currently meets that bar"
        )
    elif control_advisory_reasoning_mode == "guarded_narrowing" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories still want guarded narrowing before spending extra depth"
        )
    if (
        control_advisory_delegation == "hold_local_bias"
        and (context_signal_summary["narrowing_required"] or ambiguity >= 2)
    ):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently bias toward hold-local or tighter delegated slices"
        )
    elif (
        control_advisory_delegation == "runtime_backed_delegate"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["expected_delegation_value_score"] >= 3
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently trust runtime-backed delegation on slices with strong delegation value"
        )
    if (
        decision_quality_reliable
        and (
            evaluation_delegation_regret_rate >= 0.25
            or evaluation_followup_churn_rate >= 0.25
        )
    ):
        coordination_cost = _clamp_score(coordination_cost + 1)
        if not request.correctness_critical:
            requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence shows delegation regret or follow-up churn after execution, so the router is biasing toward tighter delegated scope"
        )
    if control_advisory_parallelism == "guarded" and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are guarding parallelism because recent execution still shows merge risk"
        )
    if decision_quality_reliable and evaluation_merge_underestimate_rate >= 0.2 and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is still underpredicting merge burden on recent delegated slices, so the router is staying conservative on fan-out"
        )
    if decision_quality_fragile and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "trusted execution-outcome evidence is currently fragile overall, so the router reduced depth and coordination until closeout quality improves"
        )
    elif (
        decision_quality_trusted
        and context_signal_summary["route_ready"]
        and context_signal_summary["expected_delegation_value_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "trusted recent execution outcomes show delegated slices are closing cleanly, so the router kept the route confident on this grounded slice"
        )
    if control_advisory_packet_strategy == "precision_first" and context_signal_summary["context_density_score"] <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently prefer precision-first packets over spending depth on shallow evidence cones"
        )
    if (
        control_advisory_budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are in tight-budget mode, so the router reduced early reasoning spend"
        )
    elif (
        control_advisory_budget_mode == "spend_when_grounded"
        and control_advisory_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "Control advisories allow extra depth when the slice is grounded and route-ready"
        )
    if control_advisory_speed_mode == "accelerate_grounded" and control_advisory_reliable and context_signal_summary["route_ready"]:
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently favor faster execution on grounded slices"
        )
    elif control_advisory_speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories currently conserve spend because recent packets are not paying back extra speed/depth"
        )
    if (
        history_effective_yield_score >= 0.72
        and history_high_yield_rate >= 0.6
        and history_reliable_high_yield_rate >= 0.5
        and context_signal_summary["route_ready"]
        and context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("requested_depth", []).append(
            "recent packets are earning strong grounded signal per budget, so the router allowed extra depth on this route-ready slice"
        )
    elif history_yield_state == "wasteful" and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent packets are still low-yield for their spend, so the router reduced depth until denser grounded evidence returns"
        )
    if control_advisory_retrieval_focus == "expand_coverage" and artifact_specificity <= 2:
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want broader evidence coverage before the router commits to a narrow delegated slice"
        )
    elif control_advisory_retrieval_focus == "precision_repair" and artifact_specificity <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories want tighter anchor repair before extra reasoning depth"
        )
    if (
        not control_advisory_present
        and packet_profile_present
        and packet_strategy == "precision_first"
        and context_signal_summary["context_density_score"] <= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained packet is already in precision-first mode, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        not control_advisory_reliable
        and budget_mode == "tight"
        and not request.correctness_critical
        and requested_depth >= 2
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        latency_pressure = _clamp_score(latency_pressure + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is already budget-tight, so the router reduced early reasoning spend"
        )
    if not control_advisory_reliable and speed_mode == "conserve" and not request.correctness_critical:
        latency_pressure = _clamp_score(latency_pressure + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is in conserve mode, so the router kept execution spend disciplined"
        )
    elif (
        not control_advisory_guarded
        and speed_mode == "accelerate_grounded"
        and packet_profile_reliable
        and context_signal_summary["route_ready"]
        and context_signal_summary["grounding_score"] >= 3
        and not context_signal_summary["narrowing_required"]
    ):
        latency_pressure = _clamp_score(latency_pressure - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the current retained packet is reliable and accelerate-grounded, so the router allowed faster execution posture"
        )
    if (
        not control_advisory_present
        and retrieval_focus == "expand_coverage"
        and artifact_specificity <= 2
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained packet still wants broader evidence coverage before the router narrows into a specialized delegated slice"
        )
    if (
        control_advisory_state in {"improving", "stable"}
        and control_advisory_reliable
        and not context_signal_summary["narrowing_required"]
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Control advisories are confident and stable enough to raise router trust in the current bounded slice"
        )
    if (
        evaluation_depth_promote
        and context_signal_summary["route_ready"]
        and not context_signal_summary["narrowing_required"]
        and context_signal_summary["grounding_score"] >= 3
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is improving and currently endorses deeper reasoning on grounded route-ready slices"
        )
    if evaluation_narrow_first and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers narrow-first control because recent benchmark or execution outcomes are not stable enough"
        )
    if evaluation_hold_local_bias and (context_signal_summary["narrowing_required"] or ambiguity >= 2):
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated delegation outcomes are not yet stable, so the router biased toward hold-local or tighter delegated slices"
        )
    if evaluation_parallel_guarded and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence is guarding parallelism because recent orchestration outcomes showed merge or false-parallel regressions"
        )
    if evaluation_precision_first and context_signal_summary["context_density_score"] <= 2:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent execution evidence currently prefers precision-first packets, so the router avoided spending extra depth on a still-shallow evidence cone"
        )
    if (
        context_signal_summary["evaluation_router_acceptance_rate"] >= 0.7
        and context_signal_summary["evaluation_benchmark_satisfaction_rate"] >= 0.6
        and context_signal_summary["evaluation_learning_state"] == "improving"
    ):
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "Recent benchmark-linked execution outcomes are improving, so the router trusted the current bounded slice more strongly"
        )
    elif (
        context_signal_summary["evaluation_router_failure_rate"] >= 0.35
        or context_signal_summary["evaluation_router_escalation_rate"] >= 0.25
    ) and not request.correctness_critical:
        requested_depth = _clamp_score(requested_depth - 1)
        base_confidence_boost = False
        feature_reasons.setdefault("context_signals", []).append(
            "Recent evaluated router outcomes are still unstable, so the router stayed more conservative on first-pass delegation depth"
        )
    if (
        request.latency_sensitive
        and context_signal_summary["optimization_latency_pressure_score"] >= 3
        and not request.correctness_critical
    ):
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "recent timing history is already under latency pressure, so the router avoided spending extra depth early"
        )
    if (
        context_signal_summary["optimization_high_execution_confidence_rate"] >= 0.5
        and context_signal_summary["odylith_execution_confidence_score"] >= 3
    ):
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "recent runtime-backed execution recommendations have been consistently high-confidence"
        )
    if context_signal_summary["provenance_score"] >= 2:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime memory contracts carried explicit provenance for the retained evidence set"
        )
    if context_signal_summary["contract_count"] >= 3:
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "multiple typed runtime contracts were available, which reduced interpretation ambiguity"
        )
    if (
        context_signal_summary["bounded_governance_delegate_candidate"]
        and not request.correctness_critical
    ):
        coordination_cost = _clamp_score(coordination_cost - 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        validation_clarity = _clamp_score(validation_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "the retained governance closeout contract kept this bounded slice execution-ready despite the broader packet staying conservative"
        )
    if (
        context_signal_summary["context_packet_state"].startswith("gated_")
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime context packet remained gated, so the router preserved a narrower posture"
        )
    if context_signal_summary["redacted_sensitive_count"] >= 1:
        feature_reasons.setdefault("context_signals", []).append(
            "runtime contracts already redacted sensitive paths from the retained evidence pack"
        )
    if context_signal_summary["intent_confidence_score"] >= 2:
        intent_family = context_signal_summary["intent_family"]
        if intent_family == "implementation" and needs_write:
            artifact_specificity = _clamp_score(artifact_specificity + 1)
            if context_signal_summary["intent_explicit"]:
                write_scope_clarity = _clamp_score(write_scope_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried an implementation-first intent profile for this bounded write slice"
            )
        elif intent_family == "validation":
            validation_clarity = _clamp_score(validation_clarity + 1)
            requested_depth = _clamp_score(requested_depth + 1)
            accuracy_bias = _clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried a validation-first intent profile for this slice"
            )
        elif intent_family in {"diagnosis", "analysis", "architecture", "review"} and not needs_write:
            requested_depth = _clamp_score(requested_depth + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "runtime handoff carried an analysis-heavy intent profile that benefits from deeper synthesis"
            )
        elif intent_family == "docs" and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            blast_radius = _clamp_score(blast_radius - 1)
            reversibility_risk = _clamp_score(reversibility_risk - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a docs-alignment intent profile, so the router treated the slice as more mechanical"
            )
        elif intent_family == "governance" and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff carried a governance-closeout intent profile for this slice"
                if not context_signal_summary["bounded_governance_delegate_candidate"]
                else "runtime handoff carried an explicit governance closeout contract, so the router treated bounded delegation as execution-ready"
            )
    if context_signal_summary["intent_critical_path"] == "narrow_first":
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as narrow-first, so the router stayed conservative"
        )
    elif context_signal_summary["intent_critical_path"] == "implementation_first" and needs_write:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked implementation as the critical path for this slice"
        )
    elif context_signal_summary["intent_critical_path"] == "analysis_first" and not needs_write:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff marked analysis as the critical path for this read-heavy slice"
        )
    elif context_signal_summary["intent_critical_path"] == "docs_after_write" and not request.correctness_critical:
        mechanicalness = _clamp_score(mechanicalness + 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked docs alignment as a post-write follow-up, which favors lighter support routing"
        )
    elif context_signal_summary["intent_critical_path"] == "governance_local":
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
            validation_clarity = _clamp_score(validation_clarity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, but the retained validation and closeout contract was explicit enough to keep bounded delegation safe"
            )
        else:
            coordination_cost = _clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "runtime handoff marked governance closeout as the critical path, so the router preserved coordination margin"
            )
    if context_signal_summary["primary_leaf"]:
        if needs_write:
            write_scope_clarity = _clamp_score(write_scope_clarity + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a primary implementation leaf with explicit owned paths"
        )
    if context_signal_summary["support_leaf"] and not request.correctness_critical:
        mechanicalness = _clamp_score(mechanicalness + 1)
        blast_radius = _clamp_score(blast_radius - 1)
        reversibility_risk = _clamp_score(reversibility_risk - 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this as a support leaf, so the router downshifted toward lighter support tiers"
        )
    if context_signal_summary["reasoning_bias"] == "deep_validation":
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff requested deep validation reasoning for this bounded slice"
        )
    elif context_signal_summary["reasoning_bias"] == "accuracy_first" and needs_write:
        requested_depth = _clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "runtime handoff preferred an accuracy-first reasoning posture for this write slice"
        )
    elif (
        context_signal_summary["reasoning_bias"] == "guarded_narrowing"
        and not context_signal_summary["bounded_governance_delegate_candidate"]
    ):
        ambiguity = _clamp_score(ambiguity + 1)
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff stayed in guarded narrowing mode, so the router treated the slice as less settled"
        )
    if (
        context_signal_summary["reasoning_readiness_score"] >= 3
        and context_signal_summary["context_density_score"] >= 2
        and context_signal_summary["route_ready"]
    ):
        requested_depth = _clamp_score(requested_depth + 1)
        accuracy_bias = _clamp_score(accuracy_bias + 1)
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported dense grounded context with high reasoning readiness, so the router allowed deeper bounded reasoning"
        )
    elif context_signal_summary["context_density_score"] <= 1 and context_signal_summary["narrowing_required"]:
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported shallow context density while narrowing is still required, so the router avoided spending extra depth early"
        )
    if context_signal_summary["evidence_diversity_score"] >= 2:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff retained evidence from multiple distinct domains, which improved confidence in the bounded evidence cone"
        )
    if has_structured_handoff and context_signal_summary["spawn_worthiness_score"] >= 3:
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        acceptance_clarity = _clamp_score(acceptance_clarity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this leaf as highly spawn-worthy relative to its merge cost"
        )
    elif (
        has_structured_handoff
        and context_signal_summary["support_leaf"]
        and context_signal_summary["spawn_worthiness_score"] <= 1
        and not request.correctness_critical
    ):
        mechanicalness = _clamp_score(mechanicalness + 1)
        requested_depth = _clamp_score(requested_depth - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "orchestration marked this support slice as low spawn-worthiness, so the router stayed light"
        )
    if context_signal_summary["routing_confidence_level"] == "high":
        artifact_specificity = _clamp_score(artifact_specificity + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported high routing confidence for the retained evidence set"
        )
    elif context_signal_summary["routing_confidence_level"] == "low":
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported low routing confidence, which increases routing conservatism"
        )
    if context_signal_summary["parallelism_hint"] == "bounded_parallel_candidate":
        base_confidence_boost = True
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as a bounded parallel candidate"
        )
    elif context_signal_summary["parallelism_hint"] == "support_followup":
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff marked the slice as follow-up support work rather than critical-path execution"
        )
    if context_signal_summary["parallelism_hint"] in {"serial_preferred", "serial_guarded"} and explicit_path_count >= 2:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff preferred serial execution for this multi-path slice"
        )
    if has_structured_handoff and context_signal_summary["merge_burden_score"] >= 3:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff reported elevated merge burden for this slice"
        )
    odylith_recommended_profile = _router_profile_from_token(context_signal_summary["odylith_execution_profile"])
    odylith_execution_confidence = int(context_signal_summary["odylith_execution_confidence_score"] or 0)
    if odylith_recommended_profile is not None and odylith_execution_confidence >= 2:
        if odylith_recommended_profile in {
            RouterProfile.CODEX_HIGH,
            RouterProfile.GPT54_HIGH,
            RouterProfile.GPT54_XHIGH,
        }:
            requested_depth = _clamp_score(requested_depth + 1)
            accuracy_bias = _clamp_score(accuracy_bias + 1)
            feature_reasons.setdefault("requested_depth", []).append(
                "odylith execution profile recommended a deeper coding or GPT-5.4 tier for this bounded slice"
            )
        elif odylith_recommended_profile in {
            RouterProfile.MINI_MEDIUM,
            RouterProfile.SPARK_MEDIUM,
        } and context_signal_summary["support_leaf"] and not request.correctness_critical:
            mechanicalness = _clamp_score(mechanicalness + 1)
            requested_depth = _clamp_score(requested_depth - 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile marked this slice as a lighter support or scout lane"
            )
        if (
            context_signal_summary["odylith_execution_delegate_preference"] == "hold_local"
            and (
                needs_write
                or odylith_recommended_profile is RouterProfile.MAIN_THREAD
                or context_signal_summary["odylith_execution_selection_mode"] in {"narrow_first", "guarded_narrowing"}
            )
        ):
            coordination_cost = _clamp_score(coordination_cost + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile still preferred local narrowing before bounded spawn"
            )
        if odylith_execution_confidence >= 3:
            base_confidence_boost = True
            artifact_specificity = _clamp_score(artifact_specificity + 1)
            feature_reasons.setdefault("context_signals", []).append(
                "odylith execution profile carried a high-confidence runtime recommendation for the delegated tier"
            )
    runtime_narrowing_required = bool(context_signal_summary["narrowing_required"] and not request.evidence_cone_grounded)
    if context_signal_summary["route_ready"]:
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff was already route-ready for native delegation"
        )
        if context_signal_summary["bounded_governance_delegate_candidate"]:
            validation_clarity = _clamp_score(validation_clarity + 1)
            acceptance_clarity = _clamp_score(acceptance_clarity + 1)
            base_confidence_boost = True
            feature_reasons.setdefault("context_signals", []).append(
                "governance closeout stayed route-ready with explicit plan-binding, validation, and sync obligations"
            )
    elif has_structured_handoff and context_signal_summary["spawn_worthiness_score"] <= 1:
        coordination_cost = _clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "runtime handoff treated the slice as only conditionally route-ready, so the router stayed conservative"
        )

    correctness_critical = bool(
        request.correctness_critical
        or (reversibility_risk >= 3 and blast_radius >= 3)
        or _contains_any(text, ("correctness", "must be right", "no regression"))
    )
    if needs_write and correctness_critical and validation_clarity == 0:
        feature_reasons.setdefault("validation_clarity", []).append("critical write slice lacks explicit validation commands or checks")
    task_family = _classify_task_family(
        task_kind=task_kind,
        needs_write=needs_write,
        correctness_critical=correctness_critical,
        feature_implementation=feature_implementation,
        mixed_phase=mixed_phase,
        ambiguity=ambiguity,
        blast_radius=blast_radius,
        reversibility_risk=reversibility_risk,
        mechanicalness=mechanicalness,
        coordination_cost=coordination_cost,
    )
    runtime_selection_mode = _normalize_token(context_signal_summary["odylith_execution_selection_mode"])
    route_ready_now = bool(context_signal_summary["route_ready"] and not context_signal_summary["narrowing_required"])
    strong_grounding = bool(
        route_ready_now
        and context_signal_summary["grounding_score"] >= 3
        and context_signal_summary["evidence_quality_score"] >= 3
    )
    density_ready = bool(
        context_signal_summary["context_density_score"] >= 3
        and context_signal_summary["reasoning_readiness_score"] >= 3
    )
    expected_high_value = bool(
        context_signal_summary["expected_delegation_value_score"] >= 3
        or context_signal_summary["spawn_worthiness_score"] >= 3
    )
    earned_depth = _clamp_score(
        (1 if requested_depth >= 2 else 0)
        + (1 if accuracy_bias >= 2 or request.correctness_critical else 0)
        + (1 if strong_grounding else 0)
        + (1 if density_ready else 0)
        + (1 if runtime_selection_mode in _RUNTIME_EARNED_DEPTH_SELECTION_MODES else 0)
        + (1 if expected_high_value else 0)
        + (
            1
            if history_effective_yield_score >= 0.72
            and history_high_yield_rate >= 0.6
            and history_reliable_high_yield_rate >= 0.5
            else 0
        )
        - (1 if context_signal_summary["narrowing_required"] else 0)
        - (1 if ambiguity >= 3 and not request.correctness_critical else 0)
        - (1 if control_advisory_guarded or packet_profile_guarded else 0)
        - (1 if history_yield_state == "wasteful" and not request.correctness_critical else 0)
    )
    delegation_readiness = _clamp_score(
        (1 if route_ready_now else 0)
        + (1 if context_signal_summary["native_spawn_ready"] else 0)
        + (1 if expected_high_value else 0)
        + (1 if write_scope_clarity >= 3 or not needs_write else 0)
        + (1 if acceptance_clarity >= 2 else 0)
        + (1 if artifact_specificity >= 2 else 0)
        + (1 if context_signal_summary["parallelism_score"] >= 3 and explicit_path_count >= 2 else 0)
        - (1 if ambiguity >= 3 else 0)
        - (1 if coordination_cost >= 3 else 0)
        - (1 if context_signal_summary["narrowing_required"] else 0)
        - (1 if context_signal_summary["merge_burden_score"] >= 3 and not request.correctness_critical else 0)
        - (1 if control_advisory_guarded or packet_profile_guarded else 0)
    )
    high_coordination_delegate_candidate = bool(
        context_signal_summary["route_ready"]
        and context_signal_summary["native_spawn_ready"]
        and not context_signal_summary["narrowing_required"]
        and earned_depth >= 3
        and delegation_readiness >= 3
        and context_signal_summary["spawn_worthiness_score"] >= 2
        and context_signal_summary["merge_burden_score"] <= 2
        and explicit_path_count <= 3
    )
    if high_coordination_delegate_candidate and coordination_cost >= 3:
        coordination_cost = _clamp_score(coordination_cost - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "The retained runtime contract kept this high-signal slice delegable despite elevated coordination language because the retained runtime contract is already bounded and route-ready"
        )
    base_confidence = _clamp_score(
        1
        + (1 if acceptance_clarity >= 2 else 0)
        + (1 if artifact_specificity >= 2 else 0)
        + (1 if validation_clarity >= 2 or not needs_write else 0)
        + (1 if write_scope_clarity >= 3 else 0)
        - (1 if ambiguity >= 3 else 0)
        - (1 if mixed_phase else 0)
        - (1 if coordination_cost >= 3 else 0)
    )
    if earned_depth >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
    if delegation_readiness >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
    elif delegation_readiness <= 1 and needs_write and not request.correctness_critical:
        base_confidence = _clamp_score(base_confidence - 1)
    if context_signal_summary["routing_confidence_level"] == "high":
        base_confidence = _clamp_score(base_confidence + 1)
    elif context_signal_summary["routing_confidence_level"] == "low":
        base_confidence = _clamp_score(base_confidence - 1)
    if base_confidence_boost:
        base_confidence = _clamp_score(base_confidence + 1)

    hard_gate_hits: list[str] = []
    if runtime_narrowing_required:
        hard_gate_hits.append("runtime-narrowing-required")
    if coordination_cost >= 4 and not (
        (
            context_signal_summary["bounded_governance_delegate_candidate"]
            or high_coordination_delegate_candidate
        )
        and context_signal_summary["route_ready"]
        and context_signal_summary["native_spawn_ready"]
        and not context_signal_summary["narrowing_required"]
    ):
        hard_gate_hits.append("coordination-cost-high")
    if request.requires_multi_agent_adjudication:
        hard_gate_hits.append("multi-agent-adjudication")
    if mixed_phase and needs_write and coordination_cost >= 4:
        hard_gate_hits.append("mixed-phase-write-slice")
    if needs_write and write_scope_clarity <= 1:
        hard_gate_hits.append("unclear-write-scope")
    if needs_write and correctness_critical and acceptance_clarity <= 1 and validation_clarity == 0:
        hard_gate_hits.append("critical-write-under-specified")
    if needs_write and explicit_component_count >= 2 and explicit_path_count == 0:
        hard_gate_hits.append("cross-surface-ownership-unclear")
    if request.evolving_context_required and not request.evidence_cone_grounded:
        hard_gate_hits.append("evolving-context-required")
    if context_signal_summary["consumer_odylith_write_blocked"]:
        hard_gate_hits.append("consumer-odylith-diagnosis-and-handoff-only")
        feature_reasons.setdefault("context_signals", []).append(
            "consumer write policy keeps Odylith product issues in diagnosis-and-handoff mode instead of local mutation"
        )
    if request.evolving_context_required and request.evidence_cone_grounded:
        feature_reasons.setdefault("grounding", []).append(
            "the evidence cone was already grounded locally, so evolving context does not stay a hard delegation refusal"
        )
    if context_signal_summary["parallelism_score"] >= 3:
        base_confidence = _clamp_score(base_confidence + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported high parallel-safety confidence for the bounded slice"
        )
    if context_signal_summary["utility_score"] >= 3 and context_signal_summary["route_ready"]:
        base_confidence = _clamp_score(base_confidence + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "utility-aware handoff indicated the retained context is both high-value and route-ready"
        )
    if context_signal_summary["native_spawn_ready"]:
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff marked the slice as ready for native spawn payload emission"
        )
    if context_signal_summary["same_prefix_disjoint_exception"]:
        feature_reasons.setdefault("context_signals", []).append(
            "same-prefix disjointness was asserted in structured orchestration metadata"
        )
    if earned_depth >= 3:
        feature_reasons.setdefault("requested_depth", []).append(
            "The retained runtime contract judged that this slice earned stronger reasoning because the retained evidence is grounded, dense, and high-value"
        )
    if delegation_readiness >= 3:
        feature_reasons.setdefault("context_signals", []).append(
            "The retained runtime contract judged the current slice as delegation-ready because ownership, validation, and runtime readiness are all strong"
        )

    return TaskAssessment(
        prompt=prompt,
        task_kind=task_kind,
        task_family=task_family,
        phase=request.phase or ("mixed" if mixed_phase else next(iter(phase_tokens), "")),
        needs_write=needs_write,
        correctness_critical=correctness_critical,
        feature_implementation=feature_implementation,
        mixed_phase=mixed_phase,
        requires_multi_agent_adjudication=request.requires_multi_agent_adjudication,
        evolving_context_required=request.evolving_context_required,
        evidence_cone_grounded=request.evidence_cone_grounded,
        ambiguity=ambiguity,
        blast_radius=blast_radius,
        context_breadth=context_breadth,
        coordination_cost=coordination_cost,
        reversibility_risk=reversibility_risk,
        mechanicalness=mechanicalness,
        write_scope_clarity=write_scope_clarity,
        acceptance_clarity=acceptance_clarity,
        artifact_specificity=artifact_specificity,
        validation_clarity=validation_clarity,
        latency_pressure=latency_pressure,
        requested_depth=requested_depth,
        accuracy_bias=_clamp_score(accuracy_bias),
        earned_depth=earned_depth,
        delegation_readiness=delegation_readiness,
        base_confidence=base_confidence,
        accuracy_preference=request.accuracy_preference,
        phase_tokens=sorted(phase_tokens),
        semantic_signals=semantic_signals,
        hard_gate_hits=hard_gate_hits,
        feature_reasons=feature_reasons,
        context_signal_summary=context_signal_summary,
    )
