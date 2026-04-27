"""Validation helpers for the Odylith execution engine layer."""

from __future__ import annotations

from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ExternalDependencyState
from odylith.runtime.execution_engine.contract import ResourceClosure
from odylith.runtime.execution_engine.contract import ValidationMatrix

_CRUD_CHECKS = ("one", "many", "all", "delete", "idempotency", "resume", "observability")
_DEPLOY_CHECKS = ("submit", "progress", "status", "verification", "logs", "recovery")
_VERIFY_CHECKS = ("status", "verification", "observability")
_RECOVER_CHECKS = ("status", "logs", "recovery", "resume")


def synthesize_validation_matrix(
    contract: ExecutionContract,
    *,
    resource_closure: ResourceClosure | None = None,
    external_state: ExternalDependencyState | None = None,
) -> ValidationMatrix:
    corpus = " ".join(
        [
            contract.objective,
            " ".join(contract.validation_plan),
            " ".join(contract.success_criteria),
            " ".join(contract.resource_set),
            " ".join(contract.critical_path),
        ]
    ).lower()
    derived_from: list[str] = ["contract"]
    if resource_closure is not None:
        corpus = f"{corpus} {resource_closure.classification}"
        derived_from.append(f"closure:{resource_closure.classification}")
    if external_state is not None:
        corpus = f"{corpus} {external_state.semantic_status} {external_state.source}"
        derived_from.append(f"external:{external_state.semantic_status}")

    if contract.execution_mode == "recover":
        checks = _RECOVER_CHECKS
        archetype = "recover"
        derived_from.append("mode:recover")
    elif contract.execution_mode == "verify":
        checks = _VERIFY_CHECKS
        archetype = "verify"
        derived_from.append("mode:verify")
    elif any(token in corpus for token in ("crud", "create", "update", "delete", "idempotent")):
        checks = _CRUD_CHECKS
        archetype = "crud"
        derived_from.append("archetype:crud")
    elif any(token in corpus for token in ("deploy", "rollout", "release", "ship", "cell")):
        checks = _DEPLOY_CHECKS
        archetype = "deploy"
        derived_from.append("archetype:deploy")
    else:
        checks = tuple(contract.validation_plan) or _VERIFY_CHECKS
        archetype = "generic"
        derived_from.append("archetype:generic")

    if resource_closure is not None and resource_closure.classification in {"incomplete", "destructive"}:
        checks = tuple(dict.fromkeys([*checks, "closure"]))
    if external_state is not None and external_state.semantic_status not in {"succeeded", "failed", "cancelled", "complete"}:
        checks = tuple(dict.fromkeys([*checks, "resume"]))

    return ValidationMatrix(
        archetype=archetype,
        checks=checks,
        minimum_pass_count=len(checks),
        derived_from=tuple(dict.fromkeys(derived_from)),
    )
