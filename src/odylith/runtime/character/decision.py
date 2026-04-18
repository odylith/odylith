from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from odylith.runtime.character import budget
from odylith.runtime.character.affordance import rank_affordances
from odylith.runtime.character.benchmark import benchmark_tags_for_decision
from odylith.runtime.character.contract import (
    CHARACTER_CONTRACT,
    HARD_LAW_DECISIONS,
    HARD_LAWS,
    compact_mapping,
)
from odylith.runtime.character.laws import evaluate_hard_laws, violated_laws
from odylith.runtime.character.learning import learning_signal
from odylith.runtime.character.memory import practice_event_from_decision, safe_practice_strings
from odylith.runtime.character.pressure import observe_pressure
from odylith.runtime.character.proof import proof_obligation_for_decision
from odylith.runtime.character.stance import infer_stance_vector
from odylith.runtime.character.support import host_lane_support
from odylith.runtime.character.voice import intervention_candidate_for_decision


def _canonical_evidence(evidence: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = [
        {"index": index, "key": str(key), "value": value}
        for index, (key, value) in enumerate(evidence.items())
    ]
    return sorted(rows, key=lambda row: (row["key"], row["index"]))


def _decision_id(*, intent: str, host_family: str, lane: str, evidence: Mapping[str, Any]) -> str:
    material = json.dumps(
        {
            "evidence": _canonical_evidence(evidence),
            "host_family": host_family,
            "intent": intent,
            "lane": lane,
        },
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]
    return f"character:{host_family}:{lane}:{digest}"


def _supported_host_lane_law(support: Mapping[str, Any]) -> dict[str, Any] | None:
    if bool(support.get("semantic_contract_supported")):
        return None
    return {
        "law_id": "supported_host_lane",
        "label": HARD_LAWS["supported_host_lane"],
        "status": "violated",
        "evidence": "unsupported host family or execution lane",
        "recovery": "Choose Codex or Claude and dev, dev-maintainer, dogfood, or consumer before acting.",
    }


def evaluate_character_move(
    *,
    intent: str,
    host_family: str = "codex",
    lane: str = "dev",
    evidence: Mapping[str, Any] | None = None,
    source_refs: Sequence[str] = (),
) -> dict[str, Any]:
    started_at = budget.start_timer()
    facts = compact_mapping(evidence)
    support = host_lane_support(host_family=host_family, lane=lane)
    normalized_host = str(support.get("host_family", "")).strip() or "unknown"
    normalized_lane = str(support.get("lane", "")).strip() or "unknown"
    if normalized_lane and "lane" not in facts:
        facts["lane"] = normalized_lane
    pressure = observe_pressure(intent, evidence=facts)
    hard_laws = evaluate_hard_laws(intent, evidence=facts)
    support_law = _supported_host_lane_law(support)
    if support_law:
        hard_laws.append(support_law)
    violations = violated_laws(hard_laws)
    stance_vector = infer_stance_vector(pressure=pressure, hard_law_results=hard_laws, lane=normalized_lane)
    affordances = rank_affordances(pressure=pressure, hard_law_results=hard_laws)
    if violations:
        violated_decisions = {
            HARD_LAW_DECISIONS.get(str(row.get("law_id", "")).strip(), "defer")
            for row in violations
        }
        decision = "block" if "block" in violated_decisions else "defer"
    elif float(pressure.get("uncertainty", 1.0) or 1.0) >= 0.75:
        decision = "defer"
    else:
        decision = "admit"
    nearest = str(affordances[0].get("action", "")).strip() if affordances else "re_anchor"
    proof_obligation = proof_obligation_for_decision(violations=violations, pressure=pressure)
    runtime_budget = budget.runtime_budget(
        started_at=started_at,
        host_model_calls_allowed=bool(facts.get("operator_explicit_model_call")),
    )
    payload: dict[str, Any] = {
        "contract": CHARACTER_CONTRACT,
        "decision_id": _decision_id(
            intent=str(intent or ""),
            host_family=normalized_host,
            lane=normalized_lane,
            evidence=facts,
        ),
        "host_family": normalized_host,
        "lane": normalized_lane,
        "host_lane_support": support,
        "host_support": {
            "known_host": bool(support.get("known_host")),
            "semantic_contract_supported": bool(support.get("semantic_contract_supported")),
            "delegation_surface": str(support.get("delegation_surface", "")),
            "skill_surfaces": list(support.get("skill_surfaces", []))
            if isinstance(support.get("skill_surfaces"), list)
            else [],
        },
        "lane_support": {
            "known_lane": bool(support.get("known_lane")),
            "runtime_posture": str(support.get("runtime_posture", "")),
            "product_mutation_default": str(support.get("product_mutation_default", "")),
        },
        "pressure_observations": pressure["pressure_observations"],
        "known_archetype_matches": pressure["known_archetype_matches"],
        "unknown_pressure_features": pressure["unknown_pressure_features"],
        "stance_vector": stance_vector,
        "hard_law_results": hard_laws,
        "decision": decision,
        "ranked_tool_affordances": affordances,
        "forbidden_moves": [str(row.get("law_id", "")) for row in violations],
        "nearest_admissible_action": nearest,
        "proof_obligation": proof_obligation,
        "tribunal_signal": {
            "candidate": bool(pressure.get("features", {}).get("recurrence")),
            "reason": "recurring pressure pattern" if pressure.get("features", {}).get("recurrence") else "",
        },
        "intervention_candidate": intervention_candidate_for_decision(
            decision=decision,
            pressure=pressure,
            violations=violations,
            affordances=affordances,
        ),
        "uncertainty": pressure["uncertainty"],
        "latency_budget": runtime_budget,
        "credit_budget": runtime_budget["credit_budget"],
        "host_model_calls_allowed": runtime_budget["host_model_calls_allowed"],
        "source_refs": safe_practice_strings(source_refs, limit=12),
    }
    payload["learning_signal"] = learning_signal(
        decision=decision,
        pressure=pressure,
        hard_law_results=hard_laws,
        benchmark_tags=[*payload["known_archetype_matches"], "agent_operating_character"],
    )
    payload["practice_event"] = practice_event_from_decision(payload)
    payload["benchmark_tags"] = benchmark_tags_for_decision(payload)
    return payload
