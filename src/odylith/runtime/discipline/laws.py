"""Translate extracted discipline signals into canonical hard-law result rows.

The discipline layer uses this module as a small, deterministic projection step:
signal extraction turns free-form intent plus optional runtime evidence into
structured facts/features, and this file turns that structure into the stable
row shape consumed by validators, interventions, and reporting surfaces.
"""

from __future__ import annotations

from typing import Any, Mapping

from odylith.runtime.discipline.contract import HARD_LAWS, HARD_LAW_RECOVERY_CUES
from odylith.runtime.discipline.signals import extract_intent_signals


def _law(law_id: str, *, applicable: bool, passed: bool, evidence: str, recovery: str) -> dict[str, Any]:
    """Build the shared result payload for one hard law evaluation.

    The status model is intentionally three-valued:
    - ``not_applicable`` means the prompt/evidence never activated the law.
    - ``passed`` means the law became relevant and the available facts satisfied it.
    - ``violated`` means the law became relevant and the available facts failed it.

    Downstream callers rely on that distinction so a quiet prompt does not look as
    if it explicitly satisfied every law in the contract.
    """
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
    """Evaluate the deterministic hard-law set against prompt intent and evidence."""
    signals = extract_intent_signals(intent, evidence=evidence)
    # Signal extraction returns loosely typed mappings because evidence can come
    # from multiple runtime surfaces. We copy only mapping-shaped payloads into
    # plain dicts once so the per-law checks stay simple and side-effect free.
    facts = dict(signals.get("facts", {})) if isinstance(signals.get("facts"), Mapping) else {}
    features = dict(signals.get("features", {})) if isinstance(signals.get("features"), Mapping) else {}
    # Queue context alone is not enough to trip the adoption law. The contract is
    # narrower: the law only applies when the prompt both references a queue-like
    # source and tries to turn that source into an implementation instruction.
    queue_applicable = (bool(signals.get("queue_mention")) or bool(facts.get("queue_visible"))) and bool(
        signals.get("queue_adoption")
    )

    return [
        # CLI-first only matters when the prompt pressures a governed surface that
        # already has an owning writer; otherwise the law stays intentionally quiet.
        _law(
            "cli_first_governed_truth",
            applicable=bool(features.get("governed_truth_risk")),
            passed=not bool(features.get("governed_truth_risk")) or bool(facts.get("used_cli_writer") or facts.get("cli_first_path")),
            evidence="governed truth writer exists" if bool(features.get("governed_truth_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["cli_first_governed_truth"],
        ),
        # Completion language is treated as a stronger claim than mere progress
        # reporting, so once that language appears we require fresh proof evidence.
        _law(
            "fresh_proof_completion",
            applicable=bool(signals.get("completion_claim")),
            passed=not bool(signals.get("completion_claim")) or bool(facts.get("fresh_proof")),
            evidence="completion language detected" if bool(signals.get("completion_claim")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["fresh_proof_completion"],
        ),
        # Visibility claims need proof that reaches a human-visible surface, not
        # just internal hook state. A rendered fallback counts because it satisfies
        # the same operator-facing obligation explicitly.
        _law(
            "visible_intervention_proof",
            applicable=bool(features.get("visibility_risk")),
            passed=not bool(features.get("visibility_risk")) or bool(facts.get("visible_proof") or facts.get("rendered_fallback")),
            evidence="visible intervention claim detected" if bool(features.get("visibility_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["visible_intervention_proof"],
        ),
        # The queue law is scoped to adoption pressure, not passive discussion of
        # backlog state, so the evidence text only appears for the narrower case.
        _law(
            "queue_non_adoption",
            applicable=queue_applicable,
            passed=not queue_applicable or bool(facts.get("queue_authorized")),
            evidence="queue-like prompt detected" if queue_applicable else "",
            recovery=HARD_LAW_RECOVERY_CUES["queue_non_adoption"],
        ),
        # Delegation is blocked only when the prompt pressures delegation without
        # the route-ready contract facts that make a bounded leaf safe to spawn.
        _law(
            "bounded_delegation",
            applicable=bool(features.get("delegation_risk")),
            passed=not bool(features.get("delegation_risk")) or bool(facts.get("delegation_contract_ready")),
            evidence="delegation pressure detected" if bool(features.get("delegation_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["bounded_delegation"],
        ),
        # Public or release-shaped claims need benchmark proof because they escape
        # the local conversation and become durable product assertions.
        _law(
            "benchmark_public_claim",
            applicable=bool(features.get("benchmark_claim_risk")),
            passed=not bool(features.get("benchmark_claim_risk")) or bool(facts.get("benchmark_proof")),
            evidence="public/release claim pressure detected" if bool(features.get("benchmark_claim_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["benchmark_public_claim"],
        ),
        # Consumer-lane mutation is guarded separately from general governed-truth
        # writes because it is about product-boundary authority, not just tooling.
        _law(
            "consumer_mutation_guard",
            applicable=bool(signals.get("consumer_mutation_risk")),
            passed=not bool(signals.get("consumer_mutation_risk")) or bool(facts.get("consumer_mutation_authorized")),
            evidence="consumer-lane product mutation risk detected" if bool(signals.get("consumer_mutation_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["consumer_mutation_guard"],
        ),
        # Credit protection is phrased as a law because deterministic discipline
        # checks must not quietly escalate into paid model execution.
        _law(
            "explicit_model_credit",
            applicable=bool(features.get("credit_risk")),
            passed=not bool(features.get("credit_risk")) or bool(facts.get("operator_explicit_model_call")),
            evidence="model-credit pressure detected" if bool(features.get("credit_risk")) else "",
            recovery=HARD_LAW_RECOVERY_CUES["explicit_model_credit"],
        ),
    ]


def violated_laws(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return only the rows that represent an active contract violation."""
    return [row for row in results if row.get("status") == "violated"]
