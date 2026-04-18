from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import LEARNING_CONTRACT


def _fingerprint(*parts: Any) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update(str(part or "").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def learning_signal(
    *,
    decision: str,
    pressure: Mapping[str, Any],
    hard_law_results: Sequence[Mapping[str, Any]],
    benchmark_tags: Sequence[str],
) -> dict[str, Any]:
    violations = [row for row in hard_law_results if row.get("status") == "violated"]
    observations = [str(item) for item in pressure.get("pressure_observations", []) if str(item).strip()]
    recurrence = bool(pressure.get("features", {}).get("recurrence"))
    if violations and any(row.get("law_id") in {"fresh_proof_completion", "benchmark_public_claim"} for row in violations):
        outcome = "blocked_until_proof"
        retention = "benchmark_pressure"
    elif violations and any(row.get("law_id") in {"visible_intervention_proof", "explicit_model_credit"} for row in violations):
        outcome = "blocked_until_proof"
        retention = "benchmark_pressure"
    elif violations:
        outcome = "nudged_and_recovered"
        retention = "durable_practice"
    elif pressure.get("uncertainty", 1.0) >= 0.75:
        outcome = "suppressed_as_noise"
        retention = "noise_suppressed"
    elif recurrence:
        outcome = "escalated_to_tribunal"
        retention = "tribunal_doctrine_candidate"
    else:
        outcome = "handled_silently"
        retention = "hot_recent"
    if recurrence and retention in {"benchmark_pressure", "durable_practice"}:
        retention = "tribunal_doctrine_candidate"
    durable_requires_proof = retention != "hot_recent"
    return {
        "contract": LEARNING_CONTRACT,
        "outcome": outcome,
        "retention_class": retention,
        "tribunal_candidate": recurrence,
        "pressure_features": observations,
        "decision": decision,
        "benchmark_tags": list(benchmark_tags),
        "fingerprint": _fingerprint(decision, "|".join(observations), "|".join(benchmark_tags)),
        "raw_transcript_retained": False,
        "secrets_retained": False,
        "durable_requires_proof": durable_requires_proof,
        "durable_update_allowed": not durable_requires_proof,
        "promotion_gate": "validator_benchmark_or_tribunal" if durable_requires_proof else "session_local",
    }
