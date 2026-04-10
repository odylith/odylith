from __future__ import annotations

from dataclasses import replace

from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import HardConstraint


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


def evaluate_admissibility(
    contract: ExecutionContract,
    action: str,
    *,
    requested_scope: tuple[str, ...] | list[str] = (),
    contradictions: tuple[ContradictionRecord, ...] | list[ContradictionRecord] = (),
    denial_count: int = 0,
    off_contract_count: int = 0,
) -> AdmissibilityDecision:
    requested_scope_tokens = {str(item).strip() for item in requested_scope if str(item).strip()}
    action_token = str(action or "").strip()
    violated: list[str] = []
    alternative = ""
    outcome = "admit"
    rationale = "action is admissible under the active execution contract"

    blocking_contradictions = [row for row in contradictions if row.blocks_execution]
    if blocking_contradictions and action_token.startswith(("mutate", "deploy", "delete", "delegate")):
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

    if contract.execution_mode in {"verify", "recover"} and action_token.startswith(("explore", "search", "rediscover")):
        outcome = "deny"
        rationale = f"`{contract.execution_mode}` mode does not allow side exploration by default"
        violated.append(f"mode_budget:{contract.execution_mode}")
        alternative = contract.allowed_moves[0] if contract.allowed_moves else "verify_current_frontier"

    if contract.host_profile is not None and not contract.host_profile.supports_native_spawn and action_token.startswith(
        "delegate"
    ):
        outcome = "deny"
        rationale = "detected host profile does not support native spawn for delegated execution"
        violated.append("host_capability:native_spawn")
        alternative = "main_thread_followup"

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
        if action_token in constraint.forbidden_moves:
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

    requires_reanchor = denial_count >= 2 or off_contract_count >= 2 or bool(blocking_contradictions)
    return AdmissibilityDecision(
        outcome=outcome,
        action=action_token,
        rationale=rationale,
        violated_preconditions=tuple(violated),
        nearest_admissible_alternative=alternative,
        requires_reanchor=requires_reanchor,
        host_hints=contract.host_profile.execution_hints if contract.host_profile is not None else (),
    )
