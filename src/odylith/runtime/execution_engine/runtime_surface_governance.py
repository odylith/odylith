from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine import contradictions as contradictions_engine
from odylith.runtime.execution_engine import frontier as frontier_engine
from odylith.runtime.execution_engine import policy as policy_engine
from odylith.runtime.execution_engine import receipts as receipts_engine
from odylith.runtime.execution_engine import resource_closure as resource_closure_engine
from odylith.runtime.execution_engine import validation as validation_engine
from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import DiagnosticAnchor
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExecutionEvent
from odylith.runtime.execution_engine.contract import ExecutionMode
from odylith.runtime.execution_engine.contract import ExternalDependencyState
from odylith.runtime.execution_engine.contract import ResourceClosure
from odylith.runtime.execution_engine.contract import SemanticReceipt
from odylith.runtime.execution_engine.contract import TargetCandidate
from odylith.runtime.execution_engine.contract import TargetResolution
from odylith.runtime.execution_engine.contract import TurnContext
from odylith.runtime.execution_engine.contract import TurnPresentationPolicy
from odylith.runtime.execution_engine.contract import ValidationMatrix
from odylith.runtime.execution_engine.contract import detect_execution_host_profile
from odylith.runtime.governance import proof_state as proof_state_runtime


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _string(value: Any) -> str:
    return str(value or "").strip()


def _strings(*values: Any) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if not isinstance(value, list):
            continue
        for item in value:
            token = _string(item)
            if not token or token in seen:
                continue
            seen.add(token)
            ordered.append(token)
    return tuple(ordered)


def _turn_context(value: Any) -> TurnContext | None:
    payload = _mapping(value)
    if not payload:
        return None
    return TurnContext(
        intent=_string(payload.get("intent")),
        surfaces=_strings(payload.get("surfaces")),
        visible_text=_strings(payload.get("visible_text")),
        active_tab=_string(payload.get("active_tab")),
        user_turn_id=_string(payload.get("user_turn_id")),
        supersedes_turn_id=_string(payload.get("supersedes_turn_id")),
    )


def _presentation_policy(value: Any) -> TurnPresentationPolicy | None:
    payload = _mapping(value)
    if not payload:
        return None
    return TurnPresentationPolicy(
        commentary_mode=_string(payload.get("commentary_mode")),
        suppress_routing_receipts=bool(payload.get("suppress_routing_receipts")),
        surface_fast_lane=bool(payload.get("surface_fast_lane")),
    )


def _target_resolution(value: Any) -> TargetResolution | None:
    payload = _mapping(value)
    if not payload:
        return None
    candidate_targets = tuple(
        TargetCandidate(
            path=_string(row.get("path")),
            source=_string(row.get("source")),
            reason=_string(row.get("reason")),
            surface=_string(row.get("surface")),
            writable=bool(row.get("writable")),
        )
        for row in payload.get("candidate_targets", [])
        if isinstance(row, Mapping) and _string(row.get("path"))
    )
    diagnostic_anchors = tuple(
        DiagnosticAnchor(
            kind=_string(row.get("kind")),
            value=_string(row.get("value")),
            label=_string(row.get("label")),
            path=_string(row.get("path")),
            surface=_string(row.get("surface")),
            source=_string(row.get("source")),
        )
        for row in payload.get("diagnostic_anchors", [])
        if isinstance(row, Mapping) and _string(row.get("value"))
    )
    return TargetResolution(
        lane=_string(payload.get("lane")),
        candidate_targets=candidate_targets,
        diagnostic_anchors=diagnostic_anchors,
        has_writable_targets=bool(payload.get("has_writable_targets")),
        requires_more_consumer_context=bool(payload.get("requires_more_consumer_context")),
        consumer_failover=_string(payload.get("consumer_failover")),
    )


def _event_id(index: int, suffix: str) -> str:
    return f"eg-{index:02d}-{suffix}"


def _infer_execution_mode(
    *,
    packet_kind: str,
    packet_state: str,
    route_ready: bool,
    full_scan_recommended: bool,
    active_blocker: str,
    validation_signal: bool,
) -> ExecutionMode:
    if active_blocker:
        return "recover"
    if validation_signal or packet_kind == "governance_slice":
        return "verify"
    if full_scan_recommended or packet_state.startswith("gated_") or not route_ready:
        return "explore"
    return "implement"


def _objective(
    *,
    packet_kind: str,
    workstream: str,
    path_tokens: Sequence[str],
    route_ready: bool,
) -> str:
    if not route_ready:
        if workstream:
            return f"narrow `{workstream}` to one admissible execution frontier"
        if path_tokens:
            return f"narrow the active slice to one admissible path frontier around `{path_tokens[0]}`"
        return "re-anchor to one admissible execution frontier"
    if workstream:
        return f"execute `{workstream}` on the authoritative lane"
    if path_tokens:
        return f"execute the grounded slice around `{path_tokens[0]}`"
    return f"execute the `{packet_kind or 'active'}` slice on the authoritative lane"


def _authoritative_lane(*, packet_kind: str, route_ready: bool) -> str:
    if route_ready:
        return f"context_engine.{packet_kind or 'packet'}.authoritative"
    return f"context_engine.{packet_kind or 'packet'}.narrowing"


def _success_criteria(
    *,
    route_ready: bool,
    full_scan_recommended: bool,
    proof_state: Mapping[str, Any],
    validation_signal: bool,
) -> tuple[str, ...]:
    criteria: list[str] = []
    if full_scan_recommended or not route_ready:
        criteria.append("one truthful next move remains after narrowing")
    if route_ready:
        criteria.append("next move stays on the authoritative lane")
    frontier_phase = _string(proof_state.get("frontier_phase"))
    if frontier_phase:
        criteria.append(f"frontier advances beyond `{frontier_phase}`")
    if validation_signal:
        criteria.append("validation matrix is satisfied before closeout")
    if not criteria:
        criteria.append("execution remains contract-admissible")
    return tuple(criteria)


def _validation_plan(
    *,
    recommended_tests: Sequence[str],
    recommended_commands: Sequence[str],
    strict_gate_command_count: int,
    plan_binding_required: bool,
    governed_surface_sync_required: bool,
    validation_signal: bool,
) -> tuple[str, ...]:
    plan: list[str] = []
    if recommended_tests:
        plan.append("tests")
    if recommended_commands:
        plan.append("commands")
    if strict_gate_command_count > 0:
        plan.append("strict_gate_commands")
    if plan_binding_required:
        plan.append("plan_binding")
    if governed_surface_sync_required:
        plan.append("governed_surface_sync")
    if validation_signal and not plan:
        plan.extend(("status", "verification"))
    if not plan:
        plan.append("status")
    return tuple(dict.fromkeys(plan))


def _allowed_moves(
    *,
    execution_mode: ExecutionMode,
    route_ready: bool,
    full_scan_recommended: bool,
    host_supports_native_spawn: bool,
    has_external_wait: bool,
) -> tuple[str, ...]:
    moves = ["re_anchor"]
    if execution_mode == "recover":
        moves.extend(("recover.current_blocker", "inspect.current_frontier"))
    elif execution_mode == "verify":
        moves.extend(("verify.selected_matrix", "inspect.current_frontier"))
    elif execution_mode == "explore" or full_scan_recommended or not route_ready:
        moves.extend(("explore.narrow_scope", "inspect.current_frontier"))
    else:
        moves.extend(("implement.target_scope", "verify.selected_matrix"))
    if has_external_wait:
        moves.append("resume.external_dependency")
    if host_supports_native_spawn and route_ready and execution_mode == "implement":
        moves.append("delegate.parallel_workers")
    return tuple(dict.fromkeys(moves))


def _forbidden_moves(
    *,
    execution_mode: ExecutionMode,
    route_ready: bool,
    host_supports_native_spawn: bool,
) -> tuple[str, ...]:
    moves: list[str] = []
    if execution_mode in {"verify", "recover"}:
        moves.extend(("explore.broad_reset", "search.from_scratch"))
    if not route_ready:
        moves.extend(("implement.target_scope", "delegate.parallel_workers"))
    if not host_supports_native_spawn:
        moves.append("delegate.parallel_workers")
    return tuple(dict.fromkeys(moves))


def _next_move(
    *,
    execution_mode: ExecutionMode,
    route_ready: bool,
    full_scan_recommended: bool,
    external_state: ExternalDependencyState | None,
) -> str:
    if external_state is not None and external_state.semantic_status not in {"succeeded", "failed", "cancelled", "complete"}:
        return "resume.external_dependency"
    if execution_mode == "recover":
        return "recover.current_blocker"
    if execution_mode == "verify":
        return "verify.selected_matrix"
    if execution_mode == "explore" or full_scan_recommended or not route_ready:
        return "explore.narrow_scope"
    return "implement.target_scope"


def _nearby_actions(
    *,
    primary_action: str,
    execution_mode: ExecutionMode,
    host_supports_native_spawn: bool,
) -> tuple[str, ...]:
    candidates = [
        "explore.broad_reset",
        "implement.target_scope",
        "verify.selected_matrix",
        "recover.current_blocker",
        "resume.external_dependency",
        "delegate.parallel_workers" if host_supports_native_spawn else "delegate.parallel_workers",
    ]
    return tuple(token for token in dict.fromkeys(candidates) if token != primary_action)


def _infer_dependency_graph(
    *,
    requested: Sequence[str],
    recommended_tests: Sequence[str],
    relevant_docs: Sequence[str],
) -> dict[str, tuple[str, ...]]:
    graph: dict[str, tuple[str, ...]] = {}
    if not requested:
        return graph
    companion_rows: list[str] = []
    companion_rows.extend(_strings(list(recommended_tests)))
    companion_rows.extend(token for token in _strings(list(relevant_docs)) if token not in companion_rows)
    if not companion_rows:
        return graph
    for token in requested:
        if token.startswith("src/"):
            graph[token] = tuple(companion_rows[:2])
    return graph


def _infer_external_dependency_state(
    *,
    proof_state: Mapping[str, Any],
    workstream: str,
    session_id: str,
) -> ExternalDependencyState | None:
    blocker = _string(proof_state.get("current_blocker"))
    token = blocker.lower()
    if "token refresh" in token:
        raw_status = "blocked_on_token_refresh"
    elif "approval" in token:
        raw_status = "waiting_approval"
    elif "callback" in token:
        raw_status = "awaiting_callback"
    elif "queued" in token:
        raw_status = "queued"
    elif "build" in token or "deploy" in token or "running" in token:
        raw_status = "building"
    else:
        raw_status = ""
    if not raw_status:
        return None
    external_id = _string(proof_state.get("lane_id")) or session_id or workstream
    return receipts_engine.normalize_external_dependency_state(
        source="proof_state",
        raw_status=raw_status,
        external_id=external_id,
        detail=blocker,
    )


def _history_rule_hits(
    *,
    closure: ResourceClosure,
    admissibility: AdmissibilityDecision,
    contradictions: Sequence[ContradictionRecord],
    proof_same_fingerprint_reopened: bool,
) -> tuple[str, ...]:
    hits: list[str] = []
    if closure.classification == "incomplete":
        hits.append("partial_scope_requires_closure")
    if closure.classification == "destructive":
        hits.append("destructive_subset_blocked")
    if proof_same_fingerprint_reopened:
        hits.append("repeated_rediscovery_detected")
    if any(row.blocks_execution for row in contradictions):
        hits.append("contradiction_blocked_preflight")
    if admissibility.requires_reanchor:
        hits.append("reanchor_triggered")
    return tuple(dict.fromkeys(hits))


def build_packet_execution_governance_snapshot(
    payload: Mapping[str, Any],
    *,
    context_packet: Mapping[str, Any] | None = None,
    routing_handoff: Mapping[str, Any] | None = None,
    host_candidates: Sequence[Any] = (),
    environ: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    context = _mapping(context_packet) or _mapping(payload.get("context_packet"))
    handoff = _mapping(routing_handoff) or _mapping(payload.get("routing_handoff"))
    session = _mapping(payload.get("session"))
    anchors = _mapping(context.get("anchors"))
    route = _mapping(context.get("route"))
    turn_context = _turn_context(payload.get("turn_context") or session.get("turn_context"))
    presentation_policy = _presentation_policy(payload.get("presentation_policy"))
    target_resolution = _target_resolution(payload.get("target_resolution"))
    proof_state = proof_state_runtime.normalize_proof_state(
        payload.get("proof_state")
    ) or proof_state_runtime.normalize_proof_state(context.get("proof_state"))
    proof_reopen = proof_state_runtime.proof_reopen_signal(proof_state) if proof_state else {}
    packet_kind = _string(payload.get("packet_kind")) or _string(context.get("packet_kind")) or "packet"
    packet_state = _string(payload.get("context_packet_state")) or _string(context.get("packet_state"))
    workstream = _string(payload.get("ws")) or _string(session.get("workstream"))
    session_id = _string(session.get("session_id"))
    changed_paths = _strings(payload.get("changed_paths"), anchors.get("changed_paths"))
    explicit_paths = _strings(payload.get("explicit_paths"), anchors.get("explicit_paths"))
    claimed_paths = _strings(session.get("claimed_paths"))
    path_tokens = tuple(dict.fromkeys([*changed_paths, *explicit_paths, *claimed_paths]))
    route_ready = bool(handoff.get("route_ready") or route.get("route_ready"))
    native_spawn_ready = bool(handoff.get("native_spawn_ready") or route.get("native_spawn_ready"))
    full_scan_recommended = bool(payload.get("full_scan_recommended") or context.get("full_scan_recommended"))
    full_scan_reason = _string(payload.get("full_scan_reason")) or _string(context.get("full_scan_reason"))
    validation_bundle = _mapping(payload.get("validation_bundle"))
    recommended_tests = _strings(
        [
            _string(row.get("path"))
            for row in payload.get("recommended_tests", [])
            if isinstance(row, Mapping)
        ]
    )
    recommended_commands = _strings(payload.get("recommended_commands"))
    relevant_docs = _strings(payload.get("relevant_docs"), payload.get("docs"))
    strict_gate_command_count = int(validation_bundle.get("strict_gate_command_count", 0) or 0)
    if strict_gate_command_count <= 0:
        strict_gate_command_count = len(_strings(validation_bundle.get("strict_gate_commands")))
    plan_binding_required = bool(validation_bundle.get("plan_binding_required"))
    governed_surface_sync_required = bool(validation_bundle.get("governed_surface_sync_required"))
    validation_signal = bool(
        strict_gate_command_count
        or plan_binding_required
        or governed_surface_sync_required
        or recommended_tests
        or recommended_commands
        or packet_kind == "governance_slice"
    )
    host_profile = detect_execution_host_profile(
        *tuple(host_candidates),
        model_name=_string(_mapping(context.get("execution_profile")).get("model")),
        environ=environ,
    )
    active_blocker = _string(proof_state.get("current_blocker")) or full_scan_reason
    external_state = _infer_external_dependency_state(
        proof_state=proof_state,
        workstream=workstream,
        session_id=session_id,
    )
    execution_mode = _infer_execution_mode(
        packet_kind=packet_kind,
        packet_state=packet_state,
        route_ready=route_ready,
        full_scan_recommended=full_scan_recommended,
        active_blocker=active_blocker,
        validation_signal=validation_signal,
    )
    objective = _objective(
        packet_kind=packet_kind,
        workstream=workstream,
        path_tokens=path_tokens,
        route_ready=route_ready,
    )
    allowed_moves = _allowed_moves(
        execution_mode=execution_mode,
        route_ready=route_ready,
        full_scan_recommended=full_scan_recommended,
        host_supports_native_spawn=bool(host_profile.supports_native_spawn and native_spawn_ready),
        has_external_wait=external_state is not None,
    )
    primary_action = _next_move(
        execution_mode=execution_mode,
        route_ready=route_ready,
        full_scan_recommended=full_scan_recommended,
        external_state=external_state,
    )
    contract = ExecutionContract.create(
        objective=objective,
        authoritative_lane=_authoritative_lane(packet_kind=packet_kind, route_ready=route_ready),
        target_scope=list(path_tokens or ([workstream] if workstream else [])),
        environment="repo_local",
        resource_set=list(path_tokens or ([workstream] if workstream else [])),
        success_criteria=list(
            _success_criteria(
                route_ready=route_ready,
                full_scan_recommended=full_scan_recommended,
                proof_state=proof_state,
                validation_signal=validation_signal,
            )
        ),
        validation_plan=list(
            _validation_plan(
                recommended_tests=recommended_tests,
                recommended_commands=recommended_commands,
                strict_gate_command_count=strict_gate_command_count,
                plan_binding_required=plan_binding_required,
                governed_surface_sync_required=governed_surface_sync_required,
                validation_signal=validation_signal,
            )
        ),
        allowed_moves=list(allowed_moves),
        forbidden_moves=list(
            _forbidden_moves(
                execution_mode=execution_mode,
                route_ready=route_ready,
                host_supports_native_spawn=bool(host_profile.supports_native_spawn and native_spawn_ready),
            )
        ),
        external_dependencies=list([external_state.source] if external_state is not None else []),
        critical_path=list(path_tokens[:4] or ([workstream] if workstream else [packet_kind])),
        host_profile=host_profile,
        turn_context=turn_context,
        target_resolution=target_resolution,
        presentation_policy=presentation_policy,
        execution_mode=execution_mode,
    )
    contradictions = contradictions_engine.detect_contradictions(
        contract,
        intended_action=primary_action,
        docs=[f"forbidden:{full_scan_reason}"] if full_scan_reason in {"local_fixture", "fixture"} else [],
        live_state=[external_state.detail] if external_state is not None else [],
    )
    dependency_graph = _infer_dependency_graph(
        requested=path_tokens or tuple([workstream] if workstream else []),
        recommended_tests=recommended_tests,
        relevant_docs=relevant_docs,
    )
    closure = resource_closure_engine.classify_resource_closure(
        path_tokens or tuple([workstream] if workstream else [packet_kind]),
        dependency_graph=dependency_graph,
    )
    validation_matrix = validation_engine.synthesize_validation_matrix(contract)
    receipt = receipts_engine.emit_semantic_receipt(
        action=primary_action,
        scope_fingerprint="|".join(path_tokens[:4] or ([workstream] if workstream else [packet_kind])),
        causal_parent=_string(proof_state.get("failure_fingerprint")) or session_id,
        external_state=external_state,
        resume_token=f"resume:{session_id or workstream or packet_kind}",
        expected_next_states=(
            [external_state.semantic_status] if external_state is not None else [validation_matrix.archetype]
        ),
    )
    events = [
        ExecutionEvent(
            event_id=_event_id(1, "phase"),
            event_type="packet_summary",
            phase=_string(proof_state.get("frontier_phase")) or execution_mode,
            successful=bool(route_ready and not active_blocker),
            blocker=active_blocker,
            next_move=primary_action,
            execution_mode=execution_mode,
            external_state=external_state,
            receipt=receipt,
        )
    ]
    if turn_context is not None and turn_context.supersedes_turn_id:
        events.insert(
            0,
            ExecutionEvent(
                event_id=_event_id(0, "superseded"),
                event_type="turn_superseded",
                phase="supersession",
                successful=True,
                next_move=primary_action,
                execution_mode=execution_mode,
            ),
        )
    if _string(proof_state.get("first_failing_phase")):
        events.insert(
            0,
            ExecutionEvent(
                event_id=_event_id(0, "proof"),
                event_type="proof_state",
                phase=_string(proof_state.get("first_failing_phase")),
                successful=not bool(active_blocker),
                next_move=primary_action,
                execution_mode=execution_mode,
            ),
        )
    frontier = frontier_engine.derive_execution_frontier(events, default_mode=execution_mode)
    admissibility = policy_engine.evaluate_admissibility(
        contract,
        primary_action,
        requested_scope=list(path_tokens),
        contradictions=contradictions,
    )
    nearby_denials = [
        decision.to_dict()
        for decision in (
            policy_engine.evaluate_admissibility(
                contract,
                candidate,
                requested_scope=list(path_tokens),
                contradictions=contradictions,
            )
            for candidate in _nearby_actions(
                primary_action=primary_action,
                execution_mode=execution_mode,
                host_supports_native_spawn=bool(host_profile.supports_native_spawn and native_spawn_ready),
            )
        )
        if decision.outcome != "admit"
    ][:3]
    history_rule_hits = _history_rule_hits(
        closure=closure,
        admissibility=admissibility,
        contradictions=contradictions,
        proof_same_fingerprint_reopened=bool(proof_reopen.get("same_fingerprint_reopened")),
    )
    return {
        "contract": contract.to_dict(),
        "admissibility": admissibility.to_dict(),
        "frontier": frontier.to_dict(),
        "resource_closure": closure.to_dict(),
        "validation_matrix": validation_matrix.to_dict(),
        "contradictions": [row.to_dict() for row in contradictions],
        "external_dependency": external_state.to_dict() if external_state is not None else {},
        "receipt": receipt.to_dict(),
        "resume_handle": receipts_engine.reattach_receipt(receipt).to_dict(),
        "history_rule_hits": list(history_rule_hits),
        "nearby_denials": nearby_denials,
    }


def compact_execution_governance_snapshot(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    contract = _mapping(snapshot.get("contract"))
    admissibility = _mapping(snapshot.get("admissibility"))
    frontier = _mapping(snapshot.get("frontier"))
    closure = _mapping(snapshot.get("resource_closure"))
    validation = _mapping(snapshot.get("validation_matrix"))
    external_dependency = _mapping(snapshot.get("external_dependency"))
    receipt = _mapping(snapshot.get("receipt"))
    host_profile = _mapping(contract.get("host_profile"))
    turn_context = _mapping(contract.get("turn_context"))
    target_resolution = _mapping(contract.get("target_resolution"))
    presentation_policy = _mapping(contract.get("presentation_policy"))
    nearby_denials = [
        {
            key: value
            for key, value in {
                "action": _string(row.get("action")),
                "outcome": _string(row.get("outcome")),
                "rationale": _string(row.get("rationale")),
                "alternative": _string(row.get("nearest_admissible_alternative")),
            }.items()
            if value not in ("", [], {}, None)
        }
        for row in snapshot.get("nearby_denials", [])
        if isinstance(row, Mapping)
    ]
    return {
        key: value
        for key, value in {
            "present": True,
            "objective": _string(contract.get("objective")),
            "authoritative_lane": _string(contract.get("authoritative_lane")),
            "mode": _string(frontier.get("execution_mode")) or _string(contract.get("execution_mode")),
            "host_family": _string(host_profile.get("host_family")),
            "model_family": _string(host_profile.get("model_family")),
            "outcome": _string(admissibility.get("outcome")),
            "rationale": _string(admissibility.get("rationale")),
            "requires_reanchor": bool(admissibility.get("requires_reanchor")),
            "next_move": _string(frontier.get("truthful_next_move")),
            "current_phase": _string(frontier.get("current_phase")),
            "last_successful_phase": _string(frontier.get("last_successful_phase")),
            "blocker": _string(frontier.get("active_blocker")),
            "closure": _string(closure.get("classification")),
            "wait_status": _string(external_dependency.get("semantic_status")),
            "wait_detail": _string(external_dependency.get("detail")),
            "resume_token": _string(receipt.get("resume_token")),
            "validation_archetype": _string(validation.get("archetype")),
            "validation_minimum_pass_count": int(validation.get("minimum_pass_count", 0) or 0),
            "contradiction_count": len(
                [row for row in snapshot.get("contradictions", []) if isinstance(row, Mapping)]
            ),
            "history_rule_count": len(
                [row for row in snapshot.get("history_rule_hits", []) if _string(row)]
            ),
            "history_rule_hits": [
                token for token in snapshot.get("history_rule_hits", []) if _string(token)
            ][:3],
            "nearby_denials": nearby_denials[:2],
            "turn_intent": _string(turn_context.get("intent")),
            "turn_active_tab": _string(turn_context.get("active_tab")),
            "turn_user_turn_id": _string(turn_context.get("user_turn_id")),
            "turn_supersedes_turn_id": _string(turn_context.get("supersedes_turn_id")),
            "turn_surface_count": len(_strings(turn_context.get("surfaces"))),
            "turn_visible_text_count": len(_strings(turn_context.get("visible_text"))),
            "target_lane": _string(target_resolution.get("lane")),
            "candidate_target_count": len(
                [row for row in target_resolution.get("candidate_targets", []) if isinstance(row, Mapping)]
            ),
            "diagnostic_anchor_count": len(
                [row for row in target_resolution.get("diagnostic_anchors", []) if isinstance(row, Mapping)]
            ),
            "has_writable_targets": bool(target_resolution.get("has_writable_targets")),
            "requires_more_consumer_context": bool(target_resolution.get("requires_more_consumer_context")),
            "consumer_failover": _string(target_resolution.get("consumer_failover")),
            "commentary_mode": _string(presentation_policy.get("commentary_mode")),
            "suppress_routing_receipts": bool(presentation_policy.get("suppress_routing_receipts")),
            "surface_fast_lane": bool(presentation_policy.get("surface_fast_lane")),
        }.items()
        if value not in ("", [], {}, None, 0)
    }


def summary_fields_from_execution_governance(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    if not snapshot:
        return {}
    if "contract" in snapshot:
        compact = compact_execution_governance_snapshot(snapshot)
    else:
        compact = dict(snapshot)
    return {
        "execution_governance_present": bool(compact.get("present", True)),
        "execution_governance_objective": _string(compact.get("objective")),
        "execution_governance_authoritative_lane": _string(compact.get("authoritative_lane")),
        "execution_governance_outcome": _string(compact.get("outcome")),
        "execution_governance_requires_reanchor": bool(compact.get("requires_reanchor")),
        "execution_governance_mode": _string(compact.get("mode")),
        "execution_governance_next_move": _string(compact.get("next_move")),
        "execution_governance_current_phase": _string(compact.get("current_phase")),
        "execution_governance_last_successful_phase": _string(compact.get("last_successful_phase")),
        "execution_governance_blocker": _string(compact.get("blocker")),
        "execution_governance_closure": _string(compact.get("closure")),
        "execution_governance_wait_status": _string(compact.get("wait_status")),
        "execution_governance_wait_detail": _string(compact.get("wait_detail")),
        "execution_governance_resume_token": _string(compact.get("resume_token")),
        "execution_governance_validation_archetype": _string(compact.get("validation_archetype")),
        "execution_governance_validation_minimum_pass_count": int(
            compact.get("validation_minimum_pass_count", 0) or 0
        ),
        "execution_governance_contradiction_count": int(compact.get("contradiction_count", 0) or 0),
        "execution_governance_history_rule_count": int(compact.get("history_rule_count", 0) or 0),
        "execution_governance_host_family": _string(compact.get("host_family")),
        "execution_governance_model_family": _string(compact.get("model_family")),
        "execution_governance_turn_intent": _string(compact.get("turn_intent")),
        "execution_governance_turn_active_tab": _string(compact.get("turn_active_tab")),
        "execution_governance_turn_user_turn_id": _string(compact.get("turn_user_turn_id")),
        "execution_governance_turn_supersedes_turn_id": _string(compact.get("turn_supersedes_turn_id")),
        "execution_governance_turn_surface_count": int(compact.get("turn_surface_count", 0) or 0),
        "execution_governance_turn_visible_text_count": int(
            compact.get("turn_visible_text_count", 0) or 0
        ),
        "execution_governance_target_lane": _string(compact.get("target_lane")),
        "execution_governance_candidate_target_count": int(
            compact.get("candidate_target_count", 0) or 0
        ),
        "execution_governance_diagnostic_anchor_count": int(
            compact.get("diagnostic_anchor_count", 0) or 0
        ),
        "execution_governance_has_writable_targets": bool(compact.get("has_writable_targets")),
        "execution_governance_requires_more_consumer_context": bool(
            compact.get("requires_more_consumer_context")
        ),
        "execution_governance_consumer_failover": _string(compact.get("consumer_failover")),
        "execution_governance_commentary_mode": _string(compact.get("commentary_mode")),
        "execution_governance_suppress_routing_receipts": bool(
            compact.get("suppress_routing_receipts")
        ),
        "execution_governance_surface_fast_lane": bool(compact.get("surface_fast_lane")),
    }


__all__ = [
    "build_packet_execution_governance_snapshot",
    "compact_execution_governance_snapshot",
    "summary_fields_from_execution_governance",
]
