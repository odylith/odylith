from __future__ import annotations

from odylith.runtime.execution_engine.contract import ExecutionContract
from odylith.runtime.execution_engine.contract import ValidationMatrix

_CRUD_CHECKS = ("one", "many", "all", "delete", "idempotency", "resume", "observability")
_DEPLOY_CHECKS = ("submit", "progress", "status", "verification", "logs", "recovery")


def synthesize_validation_matrix(contract: ExecutionContract) -> ValidationMatrix:
    corpus = " ".join(
        [
            contract.objective,
            " ".join(contract.validation_plan),
            " ".join(contract.success_criteria),
            " ".join(contract.resource_set),
        ]
    ).lower()
    if any(token in corpus for token in ("crud", "create", "update", "delete", "idempotent")):
        checks = _CRUD_CHECKS
        archetype = "crud"
    elif any(token in corpus for token in ("deploy", "rollout", "release", "ship", "cell")):
        checks = _DEPLOY_CHECKS
        archetype = "deploy"
    else:
        checks = tuple(contract.validation_plan) or ("status", "verification", "observability")
        archetype = "generic"
    return ValidationMatrix(archetype=archetype, checks=checks, minimum_pass_count=len(checks))
