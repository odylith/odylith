from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.execution_engine import runtime_lane_policy


FAMILY = "execution_engine"


def _token(value: Any) -> str:
    return str(value or "").strip()


def _packet(row: Mapping[str, Any]) -> dict[str, Any]:
    return dict(row.get("packet", {})) if isinstance(row.get("packet"), Mapping) else {}


def _expectation_details(row: Mapping[str, Any]) -> dict[str, Any]:
    return (
        dict(row.get("expectation_details", {}))
        if isinstance(row.get("expectation_details"), Mapping)
        else {}
    )


def _family(row: Mapping[str, Any]) -> str:
    return _token(row.get("scenario_family") or row.get("family")).lower().replace("-", "_")


def _expected_tokens(details: Mapping[str, Any], field_name: str) -> set[str]:
    expected = details.get(f"expected_{field_name}")
    if isinstance(expected, list):
        return {str(token).strip() for token in expected if str(token).strip()}
    token = _token(expected)
    return {token} if token else set()


def _has_expected_bool(details: Mapping[str, Any], field_name: str) -> bool:
    return f"expected_{field_name}" in details


def _backed(row: Mapping[str, Any]) -> bool:
    details = _expectation_details(row)
    packet = _packet(row)
    return bool(
        _family(row) == FAMILY
        or packet.get("execution_engine_present")
        or any(str(key).startswith("expected_execution_engine_") for key in details)
    )


def _rate(flags: Sequence[bool]) -> float:
    values = [1.0 if bool(flag) else 0.0 for flag in flags]
    if not values:
        return 0.0
    return round(sum(values) / max(1, len(values)), 3)


def summary_from_rows(scenario_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [row for row in scenario_rows if isinstance(row, Mapping) and _backed(row)]
    present: list[bool] = []
    resume_token_present: list[bool] = []
    outcome_accuracy: list[bool] = []
    mode_accuracy: list[bool] = []
    next_move_accuracy: list[bool] = []
    closure_accuracy: list[bool] = []
    wait_status_accuracy: list[bool] = []
    validation_accuracy: list[bool] = []
    current_phase_accuracy: list[bool] = []
    last_successful_phase_accuracy: list[bool] = []
    authoritative_lane_accuracy: list[bool] = []
    target_lane_accuracy: list[bool] = []
    resume_token_accuracy: list[bool] = []
    host_family_accuracy: list[bool] = []
    model_family_accuracy: list[bool] = []
    requires_reanchor_accuracy: list[bool] = []
    false_admit: list[bool] = []
    false_deny: list[bool] = []
    delegation_guard_accuracy: list[bool] = []
    parallelism_guard_accuracy: list[bool] = []

    outcome_backed_count = 0
    mode_backed_count = 0
    next_move_backed_count = 0
    closure_backed_count = 0
    wait_status_backed_count = 0
    validation_backed_count = 0
    current_phase_backed_count = 0
    last_successful_phase_backed_count = 0
    authoritative_lane_backed_count = 0
    target_lane_backed_count = 0
    resume_token_backed_count = 0
    host_family_backed_count = 0
    model_family_backed_count = 0
    reanchor_backed_count = 0
    delegation_guard_backed_count = 0
    parallelism_guard_backed_count = 0

    for row in rows:
        packet = _packet(row)
        details = _expectation_details(row)

        present.append(bool(packet.get("execution_engine_present")))
        if bool(packet.get("execution_engine_present")):
            resume_token_present.append(bool(_token(packet.get("execution_engine_resume_token"))))

        for field_name, backed_count, values in (
            ("execution_engine_outcome", "outcome", outcome_accuracy),
            ("execution_engine_mode", "mode", mode_accuracy),
            ("execution_engine_next_move", "next_move", next_move_accuracy),
            ("execution_engine_closure", "closure", closure_accuracy),
            ("execution_engine_wait_status", "wait_status", wait_status_accuracy),
            ("execution_engine_validation_archetype", "validation", validation_accuracy),
            ("execution_engine_current_phase", "current_phase", current_phase_accuracy),
            (
                "execution_engine_last_successful_phase",
                "last_successful_phase",
                last_successful_phase_accuracy,
            ),
            (
                "execution_engine_authoritative_lane",
                "authoritative_lane",
                authoritative_lane_accuracy,
            ),
            ("execution_engine_target_lane", "target_lane", target_lane_accuracy),
            ("execution_engine_resume_token", "resume_token", resume_token_accuracy),
            ("execution_engine_host_family", "host_family", host_family_accuracy),
            ("execution_engine_model_family", "model_family", model_family_accuracy),
        ):
            expected = _expected_tokens(details, field_name)
            if not expected:
                continue
            observed = _token(packet.get(field_name))
            values.append(observed in expected)
            if field_name == "execution_engine_outcome":
                false_admit.append(observed == "admit" and "admit" not in expected)
                false_deny.append("admit" in expected and observed in {"deny", "defer"})
            if backed_count == "outcome":
                outcome_backed_count += 1
            elif backed_count == "mode":
                mode_backed_count += 1
            elif backed_count == "next_move":
                next_move_backed_count += 1
            elif backed_count == "closure":
                closure_backed_count += 1
            elif backed_count == "wait_status":
                wait_status_backed_count += 1
            elif backed_count == "validation":
                validation_backed_count += 1
            elif backed_count == "current_phase":
                current_phase_backed_count += 1
            elif backed_count == "last_successful_phase":
                last_successful_phase_backed_count += 1
            elif backed_count == "authoritative_lane":
                authoritative_lane_backed_count += 1
            elif backed_count == "target_lane":
                target_lane_backed_count += 1
            elif backed_count == "resume_token":
                resume_token_backed_count += 1
            elif backed_count == "host_family":
                host_family_backed_count += 1
            elif backed_count == "model_family":
                model_family_backed_count += 1

        field_name = "execution_engine_requires_reanchor"
        if _has_expected_bool(details, field_name):
            reanchor_backed_count += 1
            requires_reanchor_accuracy.append(
                bool(packet.get(field_name)) == bool(details.get(f"expected_{field_name}"))
            )
        field_name = "execution_engine_delegation_guard_blocked"
        if _has_expected_bool(details, field_name):
            delegation_guard_backed_count += 1
            delegation_guard_accuracy.append(
                bool(runtime_lane_policy.delegation_guard(packet).blocked)
                == bool(details.get(f"expected_{field_name}"))
            )
        field_name = "execution_engine_parallelism_guard_blocked"
        if _has_expected_bool(details, field_name):
            parallelism_guard_backed_count += 1
            parallelism_guard_accuracy.append(
                bool(runtime_lane_policy.parallelism_guard(packet).blocked)
                == bool(details.get(f"expected_{field_name}"))
            )

    return {
        "execution_engine_backed_scenario_count": len(rows),
        "execution_engine_present_rate": _rate(present),
        "execution_engine_resume_token_present_rate": _rate(resume_token_present),
        "execution_engine_expected_outcome_count": outcome_backed_count,
        "execution_engine_expected_mode_count": mode_backed_count,
        "execution_engine_expected_next_move_count": next_move_backed_count,
        "execution_engine_expected_closure_count": closure_backed_count,
        "execution_engine_expected_wait_status_count": wait_status_backed_count,
        "execution_engine_expected_validation_archetype_count": validation_backed_count,
        "execution_engine_expected_current_phase_count": current_phase_backed_count,
        "execution_engine_expected_last_successful_phase_count": last_successful_phase_backed_count,
        "execution_engine_expected_authoritative_lane_count": authoritative_lane_backed_count,
        "execution_engine_expected_target_lane_count": target_lane_backed_count,
        "execution_engine_expected_resume_token_count": resume_token_backed_count,
        "execution_engine_expected_host_family_count": host_family_backed_count,
        "execution_engine_expected_model_family_count": model_family_backed_count,
        "execution_engine_expected_reanchor_count": reanchor_backed_count,
        "execution_engine_expected_delegation_guard_count": delegation_guard_backed_count,
        "execution_engine_expected_parallelism_guard_count": parallelism_guard_backed_count,
        "execution_engine_false_admit_rate": _rate(false_admit),
        "execution_engine_false_deny_rate": _rate(false_deny),
        "execution_engine_outcome_accuracy_rate": _rate(outcome_accuracy),
        "execution_engine_mode_accuracy_rate": _rate(mode_accuracy),
        "execution_engine_next_move_accuracy_rate": _rate(next_move_accuracy),
        "execution_engine_closure_accuracy_rate": _rate(closure_accuracy),
        "execution_engine_wait_status_accuracy_rate": _rate(wait_status_accuracy),
        "execution_engine_validation_archetype_accuracy_rate": _rate(validation_accuracy),
        "execution_engine_current_phase_accuracy_rate": _rate(current_phase_accuracy),
        "execution_engine_last_successful_phase_accuracy_rate": _rate(
            last_successful_phase_accuracy
        ),
        "execution_engine_authoritative_lane_accuracy_rate": _rate(
            authoritative_lane_accuracy
        ),
        "execution_engine_target_lane_accuracy_rate": _rate(target_lane_accuracy),
        "execution_engine_resume_token_accuracy_rate": _rate(resume_token_accuracy),
        "execution_engine_host_family_accuracy_rate": _rate(host_family_accuracy),
        "execution_engine_model_family_accuracy_rate": _rate(model_family_accuracy),
        "execution_engine_reanchor_accuracy_rate": _rate(requires_reanchor_accuracy),
        "execution_engine_delegation_guard_accuracy_rate": _rate(
            delegation_guard_accuracy
        ),
        "execution_engine_parallelism_guard_accuracy_rate": _rate(
            parallelism_guard_accuracy
        ),
    }


def comparison(*, candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "execution_engine_present_rate_delta": round(
            float(candidate.get("execution_engine_present_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_present_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_resume_token_present_delta": round(
            float(candidate.get("execution_engine_resume_token_present_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_resume_token_present_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_outcome_accuracy_delta": round(
            float(candidate.get("execution_engine_outcome_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_outcome_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_false_admit_rate_delta": round(
            float(candidate.get("execution_engine_false_admit_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_false_admit_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_false_deny_rate_delta": round(
            float(candidate.get("execution_engine_false_deny_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_false_deny_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_mode_accuracy_delta": round(
            float(candidate.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_next_move_accuracy_delta": round(
            float(candidate.get("execution_engine_next_move_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_next_move_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_closure_accuracy_delta": round(
            float(candidate.get("execution_engine_closure_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_closure_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_wait_status_accuracy_delta": round(
            float(candidate.get("execution_engine_wait_status_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_wait_status_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_validation_archetype_accuracy_delta": round(
            float(candidate.get("execution_engine_validation_archetype_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_validation_archetype_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_current_phase_accuracy_delta": round(
            float(candidate.get("execution_engine_current_phase_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_current_phase_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_last_successful_phase_accuracy_delta": round(
            float(candidate.get("execution_engine_last_successful_phase_accuracy_rate", 0.0) or 0.0)
            - float(
                baseline.get("execution_engine_last_successful_phase_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_authoritative_lane_accuracy_delta": round(
            float(candidate.get("execution_engine_authoritative_lane_accuracy_rate", 0.0) or 0.0)
            - float(
                baseline.get("execution_engine_authoritative_lane_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_target_lane_accuracy_delta": round(
            float(candidate.get("execution_engine_target_lane_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_target_lane_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_resume_token_accuracy_delta": round(
            float(candidate.get("execution_engine_resume_token_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_resume_token_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_host_family_accuracy_delta": round(
            float(candidate.get("execution_engine_host_family_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_host_family_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_model_family_accuracy_delta": round(
            float(candidate.get("execution_engine_model_family_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_model_family_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_reanchor_accuracy_delta": round(
            float(candidate.get("execution_engine_reanchor_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_reanchor_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_delegation_guard_accuracy_delta": round(
            float(candidate.get("execution_engine_delegation_guard_accuracy_rate", 0.0) or 0.0)
            - float(
                baseline.get("execution_engine_delegation_guard_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_parallelism_guard_accuracy_delta": round(
            float(candidate.get("execution_engine_parallelism_guard_accuracy_rate", 0.0) or 0.0)
            - float(
                baseline.get("execution_engine_parallelism_guard_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
    }


LOWER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "execution_engine_false_admit_rate",
        "execution_engine_false_deny_rate",
    }
)
HIGHER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "execution_engine_present_rate",
        "execution_engine_resume_token_present_rate",
        "execution_engine_outcome_accuracy_rate",
        "execution_engine_mode_accuracy_rate",
        "execution_engine_next_move_accuracy_rate",
        "execution_engine_closure_accuracy_rate",
        "execution_engine_wait_status_accuracy_rate",
        "execution_engine_validation_archetype_accuracy_rate",
        "execution_engine_current_phase_accuracy_rate",
        "execution_engine_last_successful_phase_accuracy_rate",
        "execution_engine_authoritative_lane_accuracy_rate",
        "execution_engine_target_lane_accuracy_rate",
        "execution_engine_resume_token_accuracy_rate",
        "execution_engine_host_family_accuracy_rate",
        "execution_engine_model_family_accuracy_rate",
        "execution_engine_reanchor_accuracy_rate",
        "execution_engine_delegation_guard_accuracy_rate",
        "execution_engine_parallelism_guard_accuracy_rate",
    }
)
