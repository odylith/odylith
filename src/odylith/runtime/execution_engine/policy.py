from __future__ import annotations

from dataclasses import replace

from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExecutionFrontier
from odylith.runtime.execution_engine.contract import ExternalDependencyState
from odylith.runtime.execution_engine.contract import HardConstraint
from odylith.runtime.execution_engine.contract import ResourceClosure
from odylith.runtime.execution_engine.contract import SemanticReceipt
from odylith.runtime.execution_engine.history_rules import canonicalize_history_rule


def promote_user_correction(
    contract: ExecutionContract,
    *,
    constraint_id: str,
    label: str,
    required_lane: str = "",
    required_scope: tuple[str, ...] | list[str] = (),
    forbidden_moves: tuple[str, ...] | list[str] = (),
    notes: str = "",
) -> ExecutionContract:
    new_constraint = HardConstraint(
        constraint_id=str(constraint_id or "").strip(),
        source="user_correction",
        label=str(label or "").strip(),
        required_lane=str(required_lane or "").strip(),
        required_scope=tuple(str(item).strip() for item in required_scope if str(item).strip()),
        forbidden_moves=tuple(str(item).strip() for item in forbidden_moves if str(item).strip()),
        notes=str(notes or "").strip(),
    )
    return replace(contract, hard_constraints=(*contract.hard_constraints, new_constraint))


def promote_instruction_constraints(
    contract: ExecutionContract,
    *,
    instructions: tuple[str, ...] | list[str] = (),
) -> ExecutionContract:
    updated = contract
    for index, raw_instruction in enumerate(instructions, start=1):
        instruction = str(raw_instruction or "").strip()
        normalized = instruction.lower()
        if not instruction:
            continue
        if any(phrase in normalized for phrase in ("do not use", "don't use", "never use", "do not touch")):
            if "do not use" in normalized:
                forbidden = normalized.split("do not use", 1)[1].strip()
            elif "don't use" in normalized:
                forbidden = normalized.split("don't use", 1)[1].strip()
            elif "never use" in normalized:
                forbidden = normalized.split("never use", 1)[1].strip()
            else:
                forbidden = normalized.split("do not touch", 1)[1].strip()
            forbidden = forbidden.strip("`'\"")
            if not forbidden:
                continue
            updated = promote_user_correction(
                updated,
                constraint_id=f"HC-inline-{index}",
                label=instruction,
                forbidden_moves=[forbidden],
                notes="Promoted from inline user instruction.",
            )
            continue
        if any(phrase in normalized for phrase in ("only use", "use only", "only touch", "stay on")):
            if "only use" in normalized:
                required = normalized.split("only use", 1)[1].strip()
            elif "use only" in normalized:
                required = normalized.split("use only", 1)[1].strip()
            elif "only touch" in normalized:
                required = normalized.split("only touch", 1)[1].strip()
            else:
                required = normalized.split("stay on", 1)[1].strip()
            required = required.strip("`'\"")
            required_lane = updated.authoritative_lane if "lane" in required else ""
            required_scope = [required] if required and required_lane == "" else []
            updated = promote_user_correction(
                updated,
                constraint_id=f"HC-inline-{index}",
                label=instruction,
                required_lane=required_lane,
                required_scope=required_scope,
                notes="Promoted from inline user instruction.",
            )
            continue
        if "authoritative lane" in normalized:
            updated = promote_user_correction(
                updated,
                constraint_id=f"HC-inline-{index}",
                label=instruction,
                required_lane=updated.authoritative_lane,
                notes="Promoted from inline authoritative-lane instruction.",
            )
    return updated


def _is_exploration_action(action_token: str) -> bool:
    return action_token.startswith(("explore", "search", "rediscover", "inspect"))


def _is_delegation_action(action_token: str) -> bool:
    return action_token.startswith(("delegate", "parallel", "fanout")) or "parallel" in action_token


def _is_mutating_action(action_token: str) -> bool:
    return action_token.startswith(("mutate", "deploy", "delete", "implement", "write", "assign", "gate"))


def evaluate_admissibility(
    contract: ExecutionContract,
    action: str,
    *,
    requested_scope: tuple[str, ...] | list[str] = (),
    contradictions: tuple[ContradictionRecord, ...] | list[ContradictionRecord] = (),
    frontier: ExecutionFrontier | None = None,
    closure: ResourceClosure | None = None,
    external_state: ExternalDependencyState | None = None,
    receipt: SemanticReceipt | None = None,
    history_rule_hits: tuple[str, ...] | list[str] = (),
    denial_count: int = 0,
    off_contract_count: int = 0,
) -> AdmissibilityDecision:
    requested_scope_tokens = {str(item).strip() for item in requested_scope if str(item).strip()}
    action_token = str(action or "").strip()
    violated: list[str] = []
    alternative = ""
    outcome = "admit"
    rationale = "action is admissible under the active execution contract"
    pressure_signals: list[str] = []

    blocking_contradictions = [row for row in contradictions if row.blocks_execution]
    if blocking_contradictions:
        pressure_signals.append("contradiction_pressure")
    if blocking_contradictions and (_is_mutating_action(action_token) or _is_delegation_action(action_token)):
        outcome = "defer"
        rationale = "blocking contradiction is still open; re-anchor before executing a mutating move"
        violated.append(blocking_contradictions[0].claim)
        alternative = "re_anchor"

    if action_token in contract.forbidden_moves:
        outcome = "deny"
        rationale = "action is explicitly forbidden by the active contract"
        violated.append(f"forbidden_move:{action_token}")

    if contract.allowed_moves and action_token not in contract.allowed_moves:
        outcome = "deny"
        rationale = "action is outside the contract's allowed move set"
        violated.append(f"not_allowed:{action_token}")
        alternative = contract.allowed_moves[0]

    if contract.execution_mode in {"verify", "recover"} and _is_exploration_action(action_token):
        outcome = "deny"
        rationale = f"`{contract.execution_mode}` mode does not allow side exploration by default"
        violated.append(f"mode_budget:{contract.execution_mode}")
        alternative = contract.allowed_moves[0] if contract.allowed_moves else "verify_current_frontier"

    if contract.execution_mode in {"verify", "recover"} and _is_delegation_action(action_token):
        outcome = "deny"
        rationale = f"`{contract.execution_mode}` mode does not allow delegated fan-out while the critical path is active"
        violated.append(f"critical_path:{contract.execution_mode}")
        alternative = contract.allowed_moves[0] if contract.allowed_moves else "inspect.current_frontier"

    if contract.host_profile is not None and not contract.host_profile.supports_native_spawn and action_token.startswith(
        "delegate"
    ):
        outcome = "deny"
        rationale = "detected host profile does not support native delegated execution"
        violated.append("host_capability:native_spawn")
        alternative = (
            "bounded_task_subagent"
            if contract.host_profile is not None and contract.host_profile.host_family == "claude"
            else "main_thread_followup"
        )

    if contract.authoritative_lane:
        for constraint in contract.hard_constraints:
            if constraint.required_lane and contract.authoritative_lane != constraint.required_lane:
                outcome = "deny"
                rationale = "active contract no longer satisfies a promoted hard lane constraint"
                violated.append(f"required_lane:{constraint.required_lane}")
        if "local_fixture" in action_token and "authoritative" in contract.authoritative_lane:
            outcome = "deny"
            rationale = "action leaves the authoritative lane"
            violated.append("lane_drift:local_fixture")
            alternative = contract.allowed_moves[0] if contract.allowed_moves else "stay_on_authoritative_lane"

    for constraint in contract.hard_constraints:
        if any(
            action_token == forbidden_move or forbidden_move in action_token
            for forbidden_move in constraint.forbidden_moves
        ):
            outcome = "deny"
            rationale = "action violates a promoted hard user constraint"
            violated.append(f"hard_constraint:{constraint.constraint_id}")
            if not alternative:
                alternative = contract.allowed_moves[0] if contract.allowed_moves else "re_anchor"
        if constraint.required_scope and requested_scope_tokens:
            required_scope = {str(item).strip() for item in constraint.required_scope if str(item).strip()}
            if not requested_scope_tokens.issubset(required_scope):
                outcome = "deny"
                rationale = "requested scope falls outside a promoted hard scope constraint"
                violated.append(f"required_scope:{constraint.constraint_id}")
            if not alternative:
                alternative = "reduce_scope_to_contract"

    if closure is not None and closure.classification in {"incomplete", "destructive"}:
        pressure_signals.append(f"closure:{closure.classification}")
        if _is_mutating_action(action_token) or _is_delegation_action(action_token):
            outcome = "deny"
            rationale = "requested action is not admissible until the active scope is closure-safe"
            violated.append(f"closure:{closure.classification}")
            if not alternative:
                alternative = "reduce_scope_to_contract"

    if external_state is not None and external_state.semantic_status not in {"succeeded", "failed", "cancelled", "complete"}:
        pressure_signals.append(f"wait:{external_state.semantic_status}")
        if action_token not in {"resume.external_dependency", "re_anchor", "verify.selected_matrix"}:
            outcome = "defer"
            rationale = "an external dependency is still in flight; resume it instead of starting a new branch"
            violated.append(f"wait_status:{external_state.semantic_status}")
            alternative = "resume.external_dependency"

    if action_token == "resume.external_dependency" and (
        external_state is None or not str(receipt.resume_token if receipt is not None else "").strip()
    ):
        outcome = "deny"
        rationale = "resume was requested, but there is no live receipt to reattach to"
        violated.append("resume_handle:missing")
        if not alternative:
            alternative = contract.allowed_moves[0] if contract.allowed_moves else "re_anchor"

    normalized_history_hits = {
        canonicalize_history_rule(hit) for hit in history_rule_hits if canonicalize_history_rule(hit)
    }

    if "contradiction_blocked_preflight" in normalized_history_hits and (
        _is_mutating_action(action_token) or _is_delegation_action(action_token)
    ):
        pressure_signals.append("history:contradiction_blocked_preflight")
        outcome = "defer"
        rationale = "the current slice already matches a contradiction-blocked failure class; re-anchor first"
        violated.append("history_rule:contradiction_blocked_preflight")
        if not alternative:
            alternative = "re_anchor"

    if "user_correction_requires_promotion" in normalized_history_hits and (
        _is_mutating_action(action_token) or _is_delegation_action(action_token)
    ):
        pressure_signals.append("history:user_correction_requires_promotion")
        outcome = "defer"
        rationale = "the current slice still needs hard user constraints promoted before new execution"
        violated.append("history_rule:user_correction_requires_promotion")
        if not alternative:
            alternative = "re_anchor"

    if "lane_drift_preflight" in normalized_history_hits and ("fixture" in action_token or "local_" in action_token):
        pressure_signals.append("history:lane_drift_preflight")
        outcome = "deny"
        rationale = "the current slice already matches a known lane-drift failure class"
        violated.append("history_rule:lane_drift_preflight")
        if not alternative:
            alternative = contract.allowed_moves[0] if contract.allowed_moves else "stay_on_authoritative_lane"

    if "repeated_rediscovery_detected" in normalized_history_hits and _is_exploration_action(action_token):
        pressure_signals.append("history:repeated_rediscovery_detected")
        outcome = "deny"
        rationale = "the current slice already hit a repeated rediscovery rule; re-anchor instead of re-exploring"
        violated.append("history_rule:repeated_rediscovery_detected")
        if not alternative:
            alternative = "re_anchor"

    if "destructive_subset_blocked" in normalized_history_hits and _is_mutating_action(action_token):
        pressure_signals.append("history:destructive_subset_blocked")
        outcome = "deny"
        rationale = "the current slice matches a known destructive-subset failure class"
        violated.append("history_rule:destructive_subset_blocked")
        if not alternative:
            alternative = "reduce_scope_to_contract"

    if frontier is not None and contract.execution_mode in {"verify", "recover"} and frontier.active_blocker and _is_mutating_action(action_token):
        pressure_signals.append("frontier:blocker_active")
        if contract.host_profile is not None and not contract.host_profile.supports_interrupt:
            pressure_signals.append("host:no_interrupt")
        outcome = "defer"
        rationale = "the frontier still has an active blocker; clear it before starting new mutation work"
        violated.append("frontier:blocker_active")
        if not alternative:
            alternative = frontier.truthful_next_move or "recover_current_blocker"

    if denial_count > 0:
        pressure_signals.append(f"denials:{int(denial_count)}")
    if off_contract_count > 0:
        pressure_signals.append(f"off_contract:{int(off_contract_count)}")
    if len(blocking_contradictions) > 1:
        pressure_signals.append(f"blocking_contradictions:{len(blocking_contradictions)}")
    requires_reanchor = (
        denial_count >= 2
        or off_contract_count >= 2
        or bool(blocking_contradictions)
        or "repeated_rediscovery_detected" in normalized_history_hits
    )
    return AdmissibilityDecision(
        outcome=outcome,
        action=action_token,
        rationale=rationale,
        violated_preconditions=tuple(violated),
        nearest_admissible_alternative=alternative,
        requires_reanchor=requires_reanchor,
        host_hints=contract.host_profile.execution_hints if contract.host_profile is not None else (),
        pressure_signals=tuple(dict.fromkeys(signal for signal in pressure_signals if signal)),
    )
