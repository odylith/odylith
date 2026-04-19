"""Assessment scoring for the subagent router."""

from __future__ import annotations

from odylith.runtime.orchestration import subagent_router as router
from odylith.runtime.orchestration import subagent_router_assessment_context
from odylith.runtime.orchestration import subagent_router_signal_summary as signal_summary

request_with_consumer_write_policy = signal_summary.request_with_consumer_write_policy
_context_signal_summary = signal_summary._context_signal_summary


def assess_request(request: router.RouteRequest) -> router.TaskAssessment:
    prompt = signal_summary._normalize_string(request.prompt)
    criteria = " ".join(signal_summary._normalize_list(request.acceptance_criteria))
    validation_commands = signal_summary._normalize_list(request.validation_commands)
    text = f"{prompt} {criteria}".strip().lower()
    semantic_signals = router.infer_prompt_semantics(prompt, request.acceptance_criteria)
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
    explicit_paths = [*request.allowed_paths, *router.infer_explicit_paths(f"{prompt} {criteria}".strip())]
    explicit_path_count = len({token for token in explicit_paths if token})
    explicit_prefixes = {
        prefix
        for path in explicit_paths
        for prefix in router.surface_prefixes_for_path(path)
        if prefix
    }
    explicit_component_count = len({token for token in request.components if token})
    explicit_workstream_count = len({token for token in request.workstreams if token})
    feature_reasons: dict[str, list[str]] = {}

    phase_tokens = router._infer_phase_tokens(text, task_kind=request.task_kind, phase=request.phase)
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

    task_kind = request.task_kind or ("feature_implementation" if router._contains_any(text, router._FEATURE_KEYWORDS) else "")
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

    feature_implementation = task_kind == "feature_implementation" or router._contains_any(text, router._FEATURE_KEYWORDS)
    analysis_only_hint = request.task_kind in {"analysis", "review"} and not request.needs_write
    needs_write = bool(
        request.needs_write
        or (
            not analysis_only_hint
            and ("implementation" in phase_tokens or router._contains_any(text, router._WRITE_KEYWORDS))
        )
    )
    if analysis_only_hint:
        phase_tokens.discard("implementation")
    if (
        request.task_kind in {"analysis", "review"}
        and not needs_write
        and phase_tokens.issubset({"analysis", "review", "planning"})
        and not router._contains_any(text, ("coordinate", "rollout", "merge", "handoff", "integrate"))
    ):
        mixed_phase = False
    ambiguity = router._keyword_score(text, router._AMBIGUITY_KEYWORDS)
    if needs_write and not request.acceptance_criteria:
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("write task lacks explicit acceptance criteria")
    if "?" in prompt:
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt is framed as an open question")
    if open_ended_scope_hits >= 2:
        ambiguity = signal_summary._clamp_score(ambiguity + 1)
        feature_reasons.setdefault("ambiguity", []).append("prompt uses open-ended architecture or redesign language")

    blast_radius = router._keyword_score(text, router._RISK_KEYWORDS)
    if explicit_path_count >= 4:
        blast_radius = signal_summary._clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("many explicit paths broaden the slice")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        blast_radius = signal_summary._clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("multiple components or workstreams widen the blast radius")
    if docs_only_scope or tests_only_scope:
        blast_radius = signal_summary._clamp_score(blast_radius - 1)
        feature_reasons.setdefault("blast_radius", []).append("owned paths stay in docs/tests scope, which caps runtime blast radius")
    if high_risk_prefix_scope:
        blast_radius = signal_summary._clamp_score(blast_radius + 1)
        feature_reasons.setdefault("blast_radius", []).append("infra/contracts ownership raises blast radius")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        blast_radius = min(blast_radius, 2)
        feature_reasons.setdefault("blast_radius", []).append("docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation")

    context_breadth = signal_summary._clamp_score(
        (1 if explicit_path_count >= 2 else 0)
        + (1 if explicit_path_count >= 4 else 0)
        + (1 if explicit_component_count >= 2 else 0)
        + (1 if explicit_workstream_count >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 3 else 0)
        + (1 if mixed_phase else 0)
        + (1 if router._contains_any(text, ("cross-file", "cross repo", "repo-wide", "multiple files")) else 0)
        + (1 if open_ended_scope_hits >= 2 else 0)
    )
    if context_breadth:
        feature_reasons.setdefault("context_breadth", []).append("slice spans multiple paths, phases, or acceptance targets")

    coordination_cost = router._keyword_score(text, router._COORDINATION_KEYWORDS)
    if mixed_phase:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("prompt mixes planning/review/integration phases")
    if explicit_path_count >= 5:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("many touched paths imply coordination overhead")
    if explicit_component_count >= 2 or explicit_workstream_count >= 2:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("multiple components or workstreams increase coordination cost")
    if request.requires_multi_agent_adjudication:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 2)
        feature_reasons.setdefault("coordination_cost", []).append("request explicitly needs multi-agent adjudication")
    if open_ended_scope_hits >= 2:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("open-ended scope language increases coordination risk")
    if governance_only_scope and request.needs_write:
        coordination_cost = signal_summary._clamp_score(coordination_cost + 1)
        feature_reasons.setdefault("coordination_cost", []).append("governed artifact updates often require main-thread integration")

    reversibility_risk = router._keyword_score(text, router._REVERSIBILITY_KEYWORDS)
    if request.correctness_critical:
        reversibility_risk = signal_summary._clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("request explicitly marks correctness as critical")
    if docs_only_scope or tests_only_scope:
        reversibility_risk = signal_summary._clamp_score(reversibility_risk - 1)
        feature_reasons.setdefault("reversibility_risk", []).append("docs/tests-only ownership lowers reversibility risk")
    if high_risk_prefix_scope:
        reversibility_risk = signal_summary._clamp_score(reversibility_risk + 1)
        feature_reasons.setdefault("reversibility_risk", []).append("infra/contracts ownership raises reversibility risk")
    if (docs_only_scope or tests_only_scope) and not request.correctness_critical:
        reversibility_risk = min(reversibility_risk, 2)
        feature_reasons.setdefault("reversibility_risk", []).append(
            "docs/tests-only scope prevents runtime-risk nouns from forcing critical escalation"
        )

    mechanicalness = router._keyword_score(text, router._MECHANICAL_KEYWORDS)
    if explicit_path_count == 1:
        mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("single explicit path suggests a bounded slice")
    if bounded_scope_hits and explicit_path_count <= 3:
        mechanicalness = signal_summary._clamp_score(mechanicalness + 1)
        feature_reasons.setdefault("mechanicalness", []).append("prompt uses bounded-scope language")
    mechanicalness = signal_summary._clamp_score(
        mechanicalness
        - (1 if ambiguity >= 3 else 0)
        - (1 if blast_radius >= 3 else 0)
        - (1 if feature_implementation else 0)
        - (1 if open_ended_scope_hits >= 2 else 0)
    )

    write_scope_clarity = signal_summary._SCORE_MAX if not needs_write else 0
    if needs_write:
        if explicit_path_count >= 1:
            write_scope_clarity += 2
        if explicit_path_count >= 3:
            write_scope_clarity += 1
        if request.acceptance_criteria:
            write_scope_clarity += 1
        if bounded_scope_hits:
            write_scope_clarity += 1
        if router._contains_any(text, ("repo-wide", "broad refactor", "sweeping")):
            write_scope_clarity -= 2
        if mixed_phase:
            write_scope_clarity -= 1
        if open_ended_scope_hits >= 2:
            write_scope_clarity -= 1
        write_scope_clarity = signal_summary._clamp_score(write_scope_clarity)
    if write_scope_clarity < 2 and needs_write:
        feature_reasons.setdefault("write_scope_clarity", []).append("write ownership is weak or unbounded")

    acceptance_signal_count = sum(1 for token in router._VALIDATION_KEYWORDS if token in criteria.lower())
    acceptance_clarity = signal_summary._clamp_score(
        (1 if request.acceptance_criteria else 0)
        + (1 if len(request.acceptance_criteria) >= 2 else 0)
        + (1 if len(request.acceptance_criteria) >= 4 else 0)
        + (1 if acceptance_signal_count >= 1 else 0)
    )
    if needs_write and acceptance_clarity <= 1:
        feature_reasons.setdefault("acceptance_clarity", []).append("write slice lacks a strong acceptance contract")

    artifact_specificity = signal_summary._clamp_score(
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
    validation_signal_count = sum(1 for token in router._VALIDATION_KEYWORDS if token in validation_text)
    validation_clarity = signal_summary._clamp_score(
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

    latency_pressure = router._keyword_score(text, router._LATENCY_KEYWORDS)
    if request.latency_sensitive:
        latency_pressure = signal_summary._clamp_score(latency_pressure + 2)
        feature_reasons.setdefault("latency_pressure", []).append("request explicitly prefers low latency")

    requested_depth = router._keyword_score(text, router._DEPTH_KEYWORDS)
    accuracy_bias = 0
    if request.accuracy_preference in {"accuracy", "max_accuracy", "maximum_accuracy"}:
        accuracy_bias += 1
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"}:
        requested_depth = signal_summary._clamp_score(requested_depth + 2)
        accuracy_bias += 1
    if feature_implementation:
        accuracy_bias += 2
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append(
            "feature implementation leans toward stronger coding-optimized or GPT-5.4 profiles"
        )
    elif task_kind == "implementation":
        accuracy_bias += 1
    if request.correctness_critical:
        accuracy_bias += 1
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
    if diagnostic_hits >= 2:
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("diagnostic language suggests deeper synthesis or failure analysis")
    if synthesis_required:
        requested_depth = signal_summary._clamp_score(requested_depth + 1)
        feature_reasons.setdefault("requested_depth", []).append("prompt requires synthesis instead of isolated lookups")
    if request.accuracy_preference in {"max_accuracy", "maximum_accuracy"} and needs_write:
        accuracy_bias += 1
        feature_reasons.setdefault("requested_depth", []).append("operator explicitly prefers maximum accuracy for this write slice")

    state = subagent_router_assessment_context.AssessmentState(
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
        accuracy_bias=accuracy_bias,
        feature_reasons=feature_reasons,
    )
    subagent_router_assessment_context.apply_context_signal_adjustments(
        request=request,
        context_signal_summary=context_signal_summary,
        state=state,
        explicit_path_count=explicit_path_count,
        has_structured_handoff=has_structured_handoff,
        needs_write=needs_write,
    )
    ambiguity = state.ambiguity
    blast_radius = state.blast_radius
    context_breadth = state.context_breadth
    coordination_cost = state.coordination_cost
    reversibility_risk = state.reversibility_risk
    mechanicalness = state.mechanicalness
    write_scope_clarity = state.write_scope_clarity
    acceptance_clarity = state.acceptance_clarity
    artifact_specificity = state.artifact_specificity
    validation_clarity = state.validation_clarity
    latency_pressure = state.latency_pressure
    requested_depth = state.requested_depth
    accuracy_bias = state.accuracy_bias
    feature_reasons = state.feature_reasons
    base_confidence_boost = state.base_confidence_boost
    history_effective_yield_score = state.history_effective_yield_score
    history_high_yield_rate = state.history_high_yield_rate
    history_reliable_high_yield_rate = state.history_reliable_high_yield_rate
    history_yield_state = state.history_yield_state
    control_advisory_guarded = state.control_advisory_guarded
    packet_profile_guarded = state.packet_profile_guarded
    runtime_narrowing_required = state.runtime_narrowing_required
    correctness_critical = bool(
        request.correctness_critical
        or (reversibility_risk >= 3 and blast_radius >= 3)
        or router._contains_any(text, ("correctness", "must be right", "no regression"))
    )
    if needs_write and correctness_critical and validation_clarity == 0:
        feature_reasons.setdefault("validation_clarity", []).append("critical write slice lacks explicit validation commands or checks")
    task_family = router._classify_task_family(
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
    runtime_selection_mode = signal_summary._normalize_token(context_signal_summary["odylith_execution_selection_mode"])
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
    earned_depth = signal_summary._clamp_score(
        (1 if requested_depth >= 2 else 0)
        + (1 if accuracy_bias >= 2 or request.correctness_critical else 0)
        + (1 if strong_grounding else 0)
        + (1 if density_ready else 0)
        + (1 if runtime_selection_mode in router._RUNTIME_EARNED_DEPTH_SELECTION_MODES else 0)
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
    delegation_readiness = signal_summary._clamp_score(
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
        coordination_cost = signal_summary._clamp_score(coordination_cost - 1)
        feature_reasons.setdefault("context_signals", []).append(
            "The retained runtime contract kept this high-signal slice delegable despite elevated coordination language because the retained runtime contract is already bounded and route-ready"
        )
    base_confidence = signal_summary._clamp_score(
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
        base_confidence = signal_summary._clamp_score(base_confidence + 1)
    if delegation_readiness >= 3:
        base_confidence = signal_summary._clamp_score(base_confidence + 1)
    elif delegation_readiness <= 1 and needs_write and not request.correctness_critical:
        base_confidence = signal_summary._clamp_score(base_confidence - 1)
    if context_signal_summary["routing_confidence_level"] == "high":
        base_confidence = signal_summary._clamp_score(base_confidence + 1)
    elif context_signal_summary["routing_confidence_level"] == "low":
        base_confidence = signal_summary._clamp_score(base_confidence - 1)
    if base_confidence_boost:
        base_confidence = signal_summary._clamp_score(base_confidence + 1)

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
        base_confidence = signal_summary._clamp_score(base_confidence + 1)
        feature_reasons.setdefault("context_signals", []).append(
            "routing_handoff reported high parallel-safety confidence for the bounded slice"
        )
    if context_signal_summary["utility_score"] >= 3 and context_signal_summary["route_ready"]:
        base_confidence = signal_summary._clamp_score(base_confidence + 1)
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


    return router.TaskAssessment(
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
        accuracy_bias=signal_summary._clamp_score(accuracy_bias),
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
