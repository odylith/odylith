from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.character.contract import HARD_LAWS, HARD_LAW_RECOVERY_CUES
from odylith.runtime.character.signals import extract_intent_signals


def _law(law_id: str, *, applicable: bool, passed: bool, evidence: str, recovery: str) -> dict[str, Any]:
    status = "not_applicable"
    if applicable:
        status = "passed" if passed else "violated"
    return {
        "law_id": law_id,
        "label": HARD_LAWS[law_id],
        "status": status,
        "evidence": evidence,
        "recovery": recovery,
    }


def evaluate_hard_laws(intent: str, *, evidence: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    signals = extract_intent_signals(intent, evidence=evidence)
    facts = dict(signals.get("facts", {})) if isinstance(signals.get("facts"), Mapping) else {}
    features = dict(signals.get("features", {})) if isinstance(signals.get("features"), Mapping) else {}
    queue_applicable = (bool(signals.get("queue_mention")) or bool(facts.get("queue_visible"))) and bool(
        signals.get("queue_adoption")
    )

    return [
        _law(
            "cli_first_governed_truth",
            applicable=bool(features.get("governed_truth_risk")),
            passed=not bool(features.get("governed_truth_risk")) or bool(facts.get("used_cli_writer") or facts.get("cli_first_path")),
            evidence="governed truth writer exists" if bool(features.get("governed_truth_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["cli_first_governed_truth"],
        ),
        _law(
            "fresh_proof_completion",
            applicable=bool(signals.get("completion_claim")),
            passed=not bool(signals.get("completion_claim")) or bool(facts.get("fresh_proof")),
            evidence="completion language detected" if bool(signals.get("completion_claim")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["fresh_proof_completion"],
        ),
        _law(
            "visible_intervention_proof",
            applicable=bool(features.get("visibility_risk")),
            passed=not bool(features.get("visibility_risk")) or bool(facts.get("visible_proof") or facts.get("rendered_fallback")),
            evidence="visible intervention claim detected" if bool(features.get("visibility_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["visible_intervention_proof"],
        ),
        _law(
            "queue_non_adoption",
            applicable=queue_applicable,
            passed=not queue_applicable or bool(facts.get("queue_authorized")),
            evidence="queue-like prompt detected" if queue_applicable else "",
            recovery=HARD_LAW_RECOVERY_CUES["queue_non_adoption"],
        ),
        _law(
            "bounded_delegation",
            applicable=bool(features.get("delegation_risk")),
            passed=not bool(features.get("delegation_risk")) or bool(facts.get("delegation_contract_ready")),
            evidence="delegation pressure detected" if bool(features.get("delegation_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["bounded_delegation"],
        ),
        _law(
            "benchmark_public_claim",
            applicable=bool(features.get("benchmark_claim_risk")),
            passed=not bool(features.get("benchmark_claim_risk")) or bool(facts.get("benchmark_proof")),
            evidence="public/release claim pressure detected" if bool(features.get("benchmark_claim_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["benchmark_public_claim"],
        ),
        _law(
            "consumer_mutation_guard",
            applicable=bool(signals.get("consumer_mutation_risk")),
            passed=not bool(signals.get("consumer_mutation_risk")) or bool(facts.get("consumer_mutation_authorized")),
            evidence="consumer-lane product mutation risk detected" if bool(signals.get("consumer_mutation_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["consumer_mutation_guard"],
        ),
        _law(
            "explicit_model_credit",
            applicable=bool(features.get("credit_risk")),
            passed=not bool(features.get("credit_risk")) or bool(facts.get("operator_explicit_model_call")),
            evidence="model-credit pressure detected" if bool(features.get("credit_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["explicit_model_credit"],
        ),
    ]


def violated_laws(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row for row in results if row.get("status") == "violated"]
