from __future__ import annotations

from typing import Any, Mapping


def successful_outcome_present(summary: Mapping[str, Any] | None) -> bool:
    if not isinstance(summary, Mapping):
        return False
    return bool(
        float(summary.get("validation_success_rate", 0.0) or 0.0) > 0.0
        or float(summary.get("expectation_success_rate", 0.0) or 0.0) > 0.0
    )


def comparative_efficiency_guardrails_applicability(
    *,
    candidate_summary: Mapping[str, Any] | None,
    baseline_summary: Mapping[str, Any] | None,
) -> dict[str, Any]:
    candidate_has_success = successful_outcome_present(candidate_summary)
    baseline_has_success = successful_outcome_present(baseline_summary)
    applicable = candidate_has_success and baseline_has_success
    if applicable:
        reason = "matched_successful_outcomes_present"
    elif not candidate_has_success and not baseline_has_success:
        reason = "no_successful_outcomes_either_lane"
    elif not candidate_has_success:
        reason = "candidate_has_no_successful_outcomes"
    else:
        reason = "baseline_has_no_successful_outcomes"
    return {
        "applicable": applicable,
        "reason": reason,
        "candidate_successful_outcome_present": candidate_has_success,
        "baseline_successful_outcome_present": baseline_has_success,
    }
