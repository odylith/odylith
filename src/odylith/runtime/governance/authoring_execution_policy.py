"""Authoring Execution Policy helpers for the Odylith governance layer."""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import replace
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine import contradictions as contradictions_engine
from odylith.runtime.execution_engine import policy as execution_policy
from odylith.runtime.execution_engine.contract import AdmissibilityDecision
from odylith.runtime.execution_engine.contract import ContradictionRecord
from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExecutionMode
from odylith.runtime.execution_engine.contract import HardConstraint
from odylith.runtime.execution_engine.contract import detect_execution_host_profile


@dataclass(frozen=True)
class GovernedAuthoringDecision:
    contract: ExecutionContract
    contradictions: tuple[ContradictionRecord, ...]
    admissibility: AdmissibilityDecision

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract": self.contract.to_dict(),
            "contradictions": [row.to_dict() for row in self.contradictions],
            "admissibility": self.admissibility.to_dict(),
        }


def evaluate_governed_authoring_action(
    *,
    action: str,
    objective: str,
    authoritative_lane: str,
    target_scope: Sequence[str],
    requested_scope: Sequence[str] = (),
    governed_scope: Sequence[str] = (),
    environment: str = "repo_local",
    resource_set: Sequence[str] = (),
    success_criteria: Sequence[str] = (),
    validation_plan: Sequence[str] = (),
    allowed_moves: Sequence[str] = (),
    forbidden_moves: Sequence[str] = (),
    external_dependencies: Sequence[str] = (),
    critical_path: Sequence[str] = (),
    user_instructions: Sequence[str] = (),
    docs: Sequence[str] = (),
    live_state: Sequence[str] = (),
    extra_contradictions: Sequence[ContradictionRecord] = (),
    execution_mode: ExecutionMode = "implement",
    denial_count: int = 0,
    off_contract_count: int = 0,
    preferred_alternative: str = "",
    model_name: str = "",
    host_candidates: Sequence[Any] = (),
    environ: Mapping[str, str] | None = None,
) -> GovernedAuthoringDecision:
    scope_tokens = tuple(str(item).strip() for item in governed_scope if str(item).strip())
    hard_constraints: tuple[HardConstraint, ...] = ()
    if authoritative_lane or scope_tokens:
        hard_constraints = (
            HardConstraint(
                constraint_id="HC-authoritative-governed-scope",
                source="authoritative_contract",
                label="stay within the authoritative governed authoring scope",
                required_lane=str(authoritative_lane or "").strip(),
                required_scope=scope_tokens,
                notes="Governed mutations must stay inside the active authoritative authoring lane and scope.",
            ),
        )
    contract = ExecutionContract.create(
        objective=objective,
        authoritative_lane=authoritative_lane,
        target_scope=list(target_scope),
        environment=environment,
        resource_set=list(resource_set),
        success_criteria=list(success_criteria),
        validation_plan=list(validation_plan),
        allowed_moves=list(allowed_moves),
        forbidden_moves=list(forbidden_moves),
        external_dependencies=list(external_dependencies),
        critical_path=list(critical_path),
        hard_constraints=hard_constraints,
        host_profile=detect_execution_host_profile(
            *tuple(host_candidates),
            model_name=model_name,
            environ=environ,
        ),
        execution_mode=execution_mode,
    )
    if user_instructions:
        contract = execution_policy.promote_instruction_constraints(
            contract,
            instructions=list(user_instructions),
        )
    contradictions = (
        *contradictions_engine.detect_contradictions(
            contract,
            intended_action=action,
            user_instructions=user_instructions,
            docs=docs,
            live_state=live_state,
        ),
        *tuple(extra_contradictions),
    )
    admissibility = execution_policy.evaluate_admissibility(
        contract,
        action,
        requested_scope=list(requested_scope),
        contradictions=contradictions,
        denial_count=denial_count,
        off_contract_count=off_contract_count,
    )
    if preferred_alternative and admissibility.outcome != "admit":
        admissibility = replace(admissibility, nearest_admissible_alternative=preferred_alternative)
    return GovernedAuthoringDecision(
        contract=contract,
        contradictions=tuple(contradictions),
        admissibility=admissibility,
    )


def enforce_governed_authoring_action(decision: GovernedAuthoringDecision) -> None:
    admissibility = decision.admissibility
    if admissibility.outcome == "admit":
        return
    violated = ", ".join(admissibility.violated_preconditions) or "unspecified_precondition"
    alternative = admissibility.nearest_admissible_alternative or "re_anchor"
    raise ValueError(
        f"action `{admissibility.action}` is `{admissibility.outcome}`: {admissibility.rationale}; "
        f"violated precondition: {violated}; "
        f"nearest admissible alternative: {alternative}"
    )
