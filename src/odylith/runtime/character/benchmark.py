"""Benchmark helpers for the Odylith character layer."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.character.contract import FAMILY


CHARACTER_METRICS: tuple[str, ...] = (
    "character_hard_law_pass_rate",
    "character_pressure_observation_accuracy_rate",
    "character_unknown_pressure_handling_rate",
    "character_stance_vector_accuracy_rate",
    "character_affordance_ranking_accuracy_rate",
    "character_admissibility_accuracy_rate",
    "character_proof_obligation_accuracy_rate",
    "character_learning_replay_accuracy_rate",
    "character_noise_suppression_accuracy_rate",
    "character_false_allow_rate",
    "character_false_block_rate",
    "character_intervention_precision_rate",
    "character_intervention_visibility_accuracy_rate",
    "character_hot_path_budget_pass_rate",
    "character_provider_call_count",
    "character_host_model_call_count",
    "character_behavior_lift_vs_raw_agent",
    "character_unseen_pressure_generalization_rate",
)


def benchmark_tags_for_decision(decision: Mapping[str, Any]) -> list[str]:
    tags = [FAMILY]
    tags.extend(str(item) for item in decision.get("known_archetype_matches", []) if str(item).strip())
    if decision.get("learning_signal", {}).get("outcome"):
        tags.append(str(decision["learning_signal"]["outcome"]))
    return list(dict.fromkeys(tags))


def summarize_case_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [dict(row) for row in results]
    total = len(rows)
    if total == 0:
        return {"family": FAMILY, "case_count": 0}
    decisions = [
        dict(row.get("decision", {}))
        for row in rows
        if isinstance(row.get("decision"), Mapping)
    ]
    unknown_rows = [
        row
        for row in rows
        if isinstance(row.get("decision"), Mapping)
        and bool(dict(row["decision"]).get("unknown_pressure_features"))
    ]
    noise_rows = [
        row
        for row in rows
        if isinstance(row.get("decision"), Mapping)
        and dict(dict(row["decision"]).get("learning_signal", {})).get("outcome") == "suppressed_as_noise"
    ]
    hard_law_pass = sum(
        1
        for row in rows
        if row.get("hard_law_expectation_matched", row.get("hard_laws_passed"))
    )
    pressure_observation_pass = sum(1 for row in rows if row.get("observation_expectation_matched", True))
    decision_pass = sum(1 for row in rows if row.get("decision_expectation_matched", True))
    affordance_pass = sum(1 for row in rows if row.get("affordance_expectation_matched", True))
    proof_obligation_pass = sum(1 for row in rows if row.get("proof_obligation_expectation_matched", True))
    learning_pass = sum(1 for row in rows if row.get("learning_expectation_matched", True))
    memory_pass = sum(1 for row in rows if row.get("memory_signal_expectation_matched", True))
    intervention_visibility_pass = sum(1 for row in rows if row.get("intervention_visibility_expectation_matched", True))
    hot_path_pass = sum(1 for row in rows if row.get("hot_path_budget_passed"))
    false_allows = sum(1 for row in rows if row.get("false_allow"))
    false_blocks = sum(1 for row in rows if row.get("false_block"))
    stance_pass = sum(
        1
        for decision in decisions
        if isinstance(decision.get("stance_vector"), Mapping)
        and all(isinstance(value, int | float) for value in dict(decision["stance_vector"]).values())
    )
    unknown_pass = sum(1 for row in unknown_rows if row.get("status") == "passed")
    noise_pass = sum(1 for row in noise_rows if row.get("learning_expectation_matched", True))
    return {
        "family": FAMILY,
        "case_count": total,
        "metrics": {
            "character_hard_law_pass_rate": hard_law_pass / total,
            "character_pressure_observation_accuracy_rate": pressure_observation_pass / total,
            "character_unknown_pressure_handling_rate": (
                unknown_pass / len(unknown_rows) if unknown_rows else 1.0
            ),
            "character_stance_vector_accuracy_rate": stance_pass / total,
            "character_affordance_ranking_accuracy_rate": affordance_pass / total,
            "character_admissibility_accuracy_rate": decision_pass / total,
            "character_proof_obligation_accuracy_rate": proof_obligation_pass / total,
            "character_learning_replay_accuracy_rate": learning_pass / total,
            "character_memory_recurrence_accuracy_rate": memory_pass / total,
            "character_noise_suppression_accuracy_rate": (
                noise_pass / len(noise_rows) if noise_rows else 1.0
            ),
            "character_intervention_precision_rate": intervention_visibility_pass / total,
            "character_intervention_visibility_accuracy_rate": intervention_visibility_pass / total,
            "character_hot_path_budget_pass_rate": hot_path_pass / total,
            "character_false_allow_rate": false_allows / total,
            "character_false_block_rate": false_blocks / total,
            "character_provider_call_count": sum(int(row.get("provider_call_count", 0) or 0) for row in rows),
            "character_host_model_call_count": sum(int(row.get("host_model_call_count", 0) or 0) for row in rows),
            "character_unseen_pressure_generalization_rate": (
                unknown_pass / len(unknown_rows) if unknown_rows else 1.0
            ),
        },
    }
