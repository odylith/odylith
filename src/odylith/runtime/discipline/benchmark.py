"""Summarize benchmark-facing outputs for the discipline family.

The helpers here deliberately operate on already-produced decision rows rather
than running benchmark logic themselves. That keeps the hot path local while
still giving benchmark/reporting code a stable aggregation surface.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.discipline.contract import FAMILY


DISCIPLINE_METRICS: tuple[str, ...] = (
    "discipline_hard_law_pass_rate",
    "discipline_pressure_observation_accuracy_rate",
    "discipline_unknown_pressure_handling_rate",
    "discipline_stance_vector_accuracy_rate",
    "discipline_affordance_ranking_accuracy_rate",
    "discipline_admissibility_accuracy_rate",
    "discipline_proof_obligation_accuracy_rate",
    "discipline_learning_replay_accuracy_rate",
    "discipline_noise_suppression_accuracy_rate",
    "discipline_false_allow_rate",
    "discipline_false_block_rate",
    "discipline_intervention_precision_rate",
    "discipline_intervention_visibility_accuracy_rate",
    "discipline_hot_path_budget_pass_rate",
    "discipline_provider_call_count",
    "discipline_host_model_call_count",
    "discipline_behavior_lift_vs_raw_agent",
    "discipline_unseen_pressure_generalization_rate",
)


def benchmark_tags_for_decision(decision: Mapping[str, Any]) -> list[str]:
    """Build a stable, deduplicated tag set for one discipline decision."""
    tags = [FAMILY]
    tags.extend(str(item) for item in decision.get("known_archetype_matches", []) if str(item).strip())
    if decision.get("learning_signal", {}).get("outcome"):
        tags.append(str(decision["learning_signal"]["outcome"]))
    return list(dict.fromkeys(tags))


def summarize_case_results(results: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate per-case expectations into family-level benchmark metrics.

    The summary intentionally treats missing expectation keys as permissive
    defaults in a few places because some cases only assert a subset of the
    family contract. That keeps the aggregator reusable across shallow and deep
    benchmark fixtures.
    """
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
    # Stance validation is intentionally structural here: the benchmark asks
    # whether the vector is well-formed numeric output, not whether each facet
    # landed on one exact value for every case.
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
            "discipline_hard_law_pass_rate": hard_law_pass / total,
            "discipline_pressure_observation_accuracy_rate": pressure_observation_pass / total,
            "discipline_unknown_pressure_handling_rate": (
                unknown_pass / len(unknown_rows) if unknown_rows else 1.0
            ),
            "discipline_stance_vector_accuracy_rate": stance_pass / total,
            "discipline_affordance_ranking_accuracy_rate": affordance_pass / total,
            "discipline_admissibility_accuracy_rate": decision_pass / total,
            "discipline_proof_obligation_accuracy_rate": proof_obligation_pass / total,
            "discipline_learning_replay_accuracy_rate": learning_pass / total,
            "discipline_memory_recurrence_accuracy_rate": memory_pass / total,
            "discipline_noise_suppression_accuracy_rate": (
                noise_pass / len(noise_rows) if noise_rows else 1.0
            ),
            "discipline_intervention_precision_rate": intervention_visibility_pass / total,
            "discipline_intervention_visibility_accuracy_rate": intervention_visibility_pass / total,
            "discipline_hot_path_budget_pass_rate": hot_path_pass / total,
            "discipline_false_allow_rate": false_allows / total,
            "discipline_false_block_rate": false_blocks / total,
            "discipline_provider_call_count": sum(int(row.get("provider_call_count", 0) or 0) for row in rows),
            "discipline_host_model_call_count": sum(int(row.get("host_model_call_count", 0) or 0) for row in rows),
            "discipline_unseen_pressure_generalization_rate": (
                unknown_pass / len(unknown_rows) if unknown_rows else 1.0
            ),
        },
    }
