from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.context_engine import execution_engine_handshake
from odylith.runtime.execution_engine import runtime_lane_policy


FAMILY = "execution_engine"
CANONICAL_COMPONENT_ID = execution_engine_handshake.CANONICAL_EXECUTION_ENGINE_COMPONENT_ID


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


def _append_component_token(tokens: list[str], value: Any) -> None:
    token = _token(value)
    if token and token not in tokens:
        tokens.append(token)


def _append_component_tokens(tokens: list[str], value: Any) -> None:
    if isinstance(value, str):
        _append_component_token(tokens, value)
        return
    if isinstance(value, Mapping):
        for key in (
            "component",
            "component_id",
            "canonical_component_id",
            "requested_component",
            "requested_component_id",
            "primary_component_id",
        ):
            _append_component_token(tokens, value.get(key))
        for key in ("components", "component_ids", "related_component_ids", "linked_component_ids"):
            _append_component_tokens(tokens, value.get(key))
        return
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        for item in value:
            _append_component_tokens(tokens, item)


def _component_key(value: Any) -> str:
    return _token(value).lower().replace("_", "-")


def _target_component_status_for(target_component: str) -> str:
    target_key = _component_key(target_component)
    if target_key in execution_engine_handshake.NONCANONICAL_EXECUTION_ENGINE_COMPONENT_IDS:
        return "blocked_noncanonical_execution_engine"
    if target_key == CANONICAL_COMPONENT_ID:
        return "execution_engine"
    return "execution_engine_plus_related"


def _execution_snapshot_matches_target(
    snapshot: Mapping[str, Any],
    *,
    expected_target_status: str,
) -> bool:
    return bool(
        _token(snapshot.get("component_id")) == CANONICAL_COMPONENT_ID
        and _token(snapshot.get("canonical_component_id")) == CANONICAL_COMPONENT_ID
        and _token(snapshot.get("target_component_status")) == expected_target_status
        and _token(snapshot.get("identity_status"))
        in {"canonical", "blocked_noncanonical_target"}
    )


def enrich_packet_payload_for_execution_engine_family(
    *,
    payload: Mapping[str, Any],
    scenario: Mapping[str, Any],
) -> dict[str, Any]:
    """Stamp benchmark packet payloads with canonical execution-engine identity.

    Execution-engine benchmark slices sometimes exercise related components such
    as the router. The canonical engine identity must still be present so packet
    summaries, hard gates, and downstream host policy evaluate the Execution
    Engine handshake instead of silently treating the target as missing.
    """
    enriched = dict(payload)
    if _family(scenario) != FAMILY:
        return enriched

    scenario_component = _token(scenario.get("component"))
    target_component = scenario_component or CANONICAL_COMPONENT_ID
    expected_target_status = _target_component_status_for(target_component)
    existing_execution = (
        dict(enriched.get("execution_engine", {}))
        if isinstance(enriched.get("execution_engine"), Mapping)
        else {}
    )
    if existing_execution and not _execution_snapshot_matches_target(
        existing_execution,
        expected_target_status=expected_target_status,
    ):
        enriched.pop("execution_engine", None)
    context_packet = (
        dict(enriched.get("context_packet", {}))
        if isinstance(enriched.get("context_packet"), Mapping)
        else {}
    )
    context_execution = (
        dict(context_packet.get("execution_engine", {}))
        if isinstance(context_packet.get("execution_engine"), Mapping)
        else {}
    )
    if context_execution and not _execution_snapshot_matches_target(
        context_execution,
        expected_target_status=expected_target_status,
    ):
        context_packet.pop("execution_engine", None)
    if context_packet:
        enriched["context_packet"] = context_packet
    enriched["component"] = target_component
    enriched["component_id"] = CANONICAL_COMPONENT_ID
    enriched["canonical_component_id"] = CANONICAL_COMPONENT_ID

    related_component_ids: list[str] = []
    _append_component_tokens(related_component_ids, enriched.get("related_component_ids"))
    if target_component != CANONICAL_COMPONENT_ID:
        _append_component_token(related_component_ids, CANONICAL_COMPONENT_ID)
    if related_component_ids:
        enriched["related_component_ids"] = related_component_ids[:8]

    component_ids: list[str] = []
    _append_component_token(component_ids, target_component)
    _append_component_token(component_ids, CANONICAL_COMPONENT_ID)
    _append_component_tokens(component_ids, enriched.get("component_ids"))
    _append_component_tokens(component_ids, enriched.get("related_component_ids"))
    enriched["component_ids"] = component_ids[:8]
    related_component_ids = [token for token in component_ids if token != target_component]
    if related_component_ids:
        enriched["related_component_ids"] = related_component_ids[:8]

    target_resolution = (
        dict(enriched.get("target_resolution", {}))
        if isinstance(enriched.get("target_resolution"), Mapping)
        else {}
    )
    candidate_targets = [
        dict(row) if isinstance(row, Mapping) else row
        for row in target_resolution.get("candidate_targets", [])
        if row not in ("", [], {}, None)
    ] if isinstance(target_resolution.get("candidate_targets"), list) else []
    existing_target_keys = {
        _component_key(row.get("value") or row.get("component_id") or row.get("entity_id"))
        for row in candidate_targets
        if isinstance(row, Mapping)
    }
    if _component_key(target_component) not in existing_target_keys:
        candidate_targets.insert(
            0,
            {
                "kind": "component",
                "value": target_component,
                "canonical_component_id": CANONICAL_COMPONENT_ID,
                "source": "benchmark.execution_engine",
            },
        )
    target_resolution["candidate_targets"] = candidate_targets[:8]
    enriched["target_resolution"] = target_resolution
    return enriched


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


def _number(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _median(values: Sequence[float]) -> float:
    numbers = sorted(value for value in values if value >= 0.0)
    if not numbers:
        return 0.0
    midpoint = len(numbers) // 2
    if len(numbers) % 2:
        return round(numbers[midpoint], 3)
    return round((numbers[midpoint - 1] + numbers[midpoint]) / 2.0, 3)


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
    component_id_accuracy: list[bool] = []
    canonical_component_id_accuracy: list[bool] = []
    identity_status_accuracy: list[bool] = []
    target_component_status_accuracy: list[bool] = []
    snapshot_reuse_status_accuracy: list[bool] = []
    requires_reanchor_accuracy: list[bool] = []
    false_admit: list[bool] = []
    false_deny: list[bool] = []
    delegation_guard_accuracy: list[bool] = []
    parallelism_guard_accuracy: list[bool] = []
    context_packet_build_ms: list[float] = []
    snapshot_duration_ms: list[float] = []
    prompt_bundle_tokens: list[float] = []
    runtime_contract_tokens: list[float] = []
    total_payload_tokens: list[float] = []

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
    component_id_backed_count = 0
    canonical_component_id_backed_count = 0
    identity_status_backed_count = 0
    target_component_status_backed_count = 0
    snapshot_reuse_status_backed_count = 0
    reanchor_backed_count = 0
    delegation_guard_backed_count = 0
    parallelism_guard_backed_count = 0

    for row in rows:
        packet = _packet(row)
        details = _expectation_details(row)

        present.append(bool(packet.get("execution_engine_present")))
        context_packet_build_ms.append(_number(row.get("context_engine_packet_build_ms") or row.get("latency_ms")))
        snapshot_duration_ms.append(_number(packet.get("execution_engine_snapshot_duration_ms")))
        prompt_bundle_tokens.append(_number(row.get("effective_estimated_tokens")))
        runtime_contract_tokens.append(
            _number(
                row.get("runtime_contract_estimated_tokens")
                or packet.get("execution_engine_runtime_contract_estimated_tokens")
            )
        )
        total_payload_tokens.append(
            _number(
                row.get("total_payload_estimated_tokens")
                or packet.get("execution_engine_total_payload_estimated_tokens")
            )
        )
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
            ("execution_engine_component_id", "component_id", component_id_accuracy),
            (
                "execution_engine_canonical_component_id",
                "canonical_component_id",
                canonical_component_id_accuracy,
            ),
            (
                "execution_engine_identity_status",
                "identity_status",
                identity_status_accuracy,
            ),
            (
                "execution_engine_target_component_status",
                "target_component_status",
                target_component_status_accuracy,
            ),
            (
                "execution_engine_snapshot_reuse_status",
                "snapshot_reuse_status",
                snapshot_reuse_status_accuracy,
            ),
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
            elif backed_count == "component_id":
                component_id_backed_count += 1
            elif backed_count == "canonical_component_id":
                canonical_component_id_backed_count += 1
            elif backed_count == "identity_status":
                identity_status_backed_count += 1
            elif backed_count == "target_component_status":
                target_component_status_backed_count += 1
            elif backed_count == "snapshot_reuse_status":
                snapshot_reuse_status_backed_count += 1

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
        "execution_engine_expected_component_id_count": component_id_backed_count,
        "execution_engine_expected_canonical_component_id_count": canonical_component_id_backed_count,
        "execution_engine_expected_identity_status_count": identity_status_backed_count,
        "execution_engine_expected_target_component_status_count": target_component_status_backed_count,
        "execution_engine_expected_snapshot_reuse_status_count": snapshot_reuse_status_backed_count,
        "execution_engine_expected_reanchor_count": reanchor_backed_count,
        "execution_engine_expected_delegation_guard_count": delegation_guard_backed_count,
        "execution_engine_expected_parallelism_guard_count": parallelism_guard_backed_count,
        "execution_engine_median_context_packet_build_ms": _median(context_packet_build_ms),
        "execution_engine_median_snapshot_duration_ms": _median(snapshot_duration_ms),
        "execution_engine_median_prompt_bundle_tokens": _median(prompt_bundle_tokens),
        "execution_engine_median_runtime_contract_tokens": _median(runtime_contract_tokens),
        "execution_engine_median_total_payload_tokens": _median(total_payload_tokens),
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
        "execution_engine_component_id_accuracy_rate": _rate(component_id_accuracy),
        "execution_engine_canonical_component_id_accuracy_rate": _rate(canonical_component_id_accuracy),
        "execution_engine_identity_status_accuracy_rate": _rate(identity_status_accuracy),
        "execution_engine_target_component_status_accuracy_rate": _rate(
            target_component_status_accuracy
        ),
        "execution_engine_snapshot_reuse_status_accuracy_rate": _rate(
            snapshot_reuse_status_accuracy
        ),
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
        "execution_engine_component_id_accuracy_delta": round(
            float(candidate.get("execution_engine_component_id_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_component_id_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_canonical_component_id_accuracy_delta": round(
            float(
                candidate.get("execution_engine_canonical_component_id_accuracy_rate", 0.0)
                or 0.0
            )
            - float(
                baseline.get("execution_engine_canonical_component_id_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_identity_status_accuracy_delta": round(
            float(candidate.get("execution_engine_identity_status_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("execution_engine_identity_status_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "execution_engine_target_component_status_accuracy_delta": round(
            float(
                candidate.get("execution_engine_target_component_status_accuracy_rate", 0.0)
                or 0.0
            )
            - float(
                baseline.get("execution_engine_target_component_status_accuracy_rate", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_snapshot_reuse_status_accuracy_delta": round(
            float(
                candidate.get("execution_engine_snapshot_reuse_status_accuracy_rate", 0.0)
                or 0.0
            )
            - float(
                baseline.get("execution_engine_snapshot_reuse_status_accuracy_rate", 0.0)
                or 0.0
            ),
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
        "execution_engine_median_context_packet_build_ms_delta": round(
            float(candidate.get("execution_engine_median_context_packet_build_ms", 0.0) or 0.0)
            - float(
                baseline.get("execution_engine_median_context_packet_build_ms", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_median_snapshot_duration_ms_delta": round(
            float(candidate.get("execution_engine_median_snapshot_duration_ms", 0.0) or 0.0)
            - float(baseline.get("execution_engine_median_snapshot_duration_ms", 0.0) or 0.0),
            3,
        ),
        "execution_engine_median_prompt_bundle_tokens_delta": round(
            float(candidate.get("execution_engine_median_prompt_bundle_tokens", 0.0) or 0.0)
            - float(baseline.get("execution_engine_median_prompt_bundle_tokens", 0.0) or 0.0),
            3,
        ),
        "execution_engine_median_runtime_contract_tokens_delta": round(
            float(
                candidate.get("execution_engine_median_runtime_contract_tokens", 0.0)
                or 0.0
            )
            - float(
                baseline.get("execution_engine_median_runtime_contract_tokens", 0.0)
                or 0.0
            ),
            3,
        ),
        "execution_engine_median_total_payload_tokens_delta": round(
            float(candidate.get("execution_engine_median_total_payload_tokens", 0.0) or 0.0)
            - float(baseline.get("execution_engine_median_total_payload_tokens", 0.0) or 0.0),
            3,
        ),
    }


def acceptance_checks(summary: Mapping[str, Any]) -> dict[str, bool]:
    backed_count = int(summary.get("execution_engine_backed_scenario_count", 0) or 0)

    def expected_clear(count_field: str, rate_field: str) -> bool:
        return int(summary.get(count_field, 0) or 0) == 0 or float(
            summary.get(rate_field, 0.0) or 0.0
        ) >= 1.0

    return {
        "execution_engine_present": backed_count == 0
        or float(summary.get("execution_engine_present_rate", 0.0) or 0.0) >= 1.0,
        "execution_engine_resume_token_present": backed_count == 0
        or float(summary.get("execution_engine_resume_token_present_rate", 0.0) or 0.0)
        >= 1.0,
        "execution_engine_false_admit_zero": backed_count == 0
        or float(summary.get("execution_engine_false_admit_rate", 0.0) or 0.0) <= 0.0,
        "execution_engine_false_deny_zero": backed_count == 0
        or float(summary.get("execution_engine_false_deny_rate", 0.0) or 0.0) <= 0.0,
        "execution_engine_outcome_accurate": expected_clear(
            "execution_engine_expected_outcome_count",
            "execution_engine_outcome_accuracy_rate",
        ),
        "execution_engine_mode_accurate": expected_clear(
            "execution_engine_expected_mode_count",
            "execution_engine_mode_accuracy_rate",
        ),
        "execution_engine_next_move_accurate": expected_clear(
            "execution_engine_expected_next_move_count",
            "execution_engine_next_move_accuracy_rate",
        ),
        "execution_engine_closure_accurate": expected_clear(
            "execution_engine_expected_closure_count",
            "execution_engine_closure_accuracy_rate",
        ),
        "execution_engine_wait_status_accurate": expected_clear(
            "execution_engine_expected_wait_status_count",
            "execution_engine_wait_status_accuracy_rate",
        ),
        "execution_engine_validation_accurate": expected_clear(
            "execution_engine_expected_validation_archetype_count",
            "execution_engine_validation_archetype_accuracy_rate",
        ),
        "execution_engine_current_phase_accurate": expected_clear(
            "execution_engine_expected_current_phase_count",
            "execution_engine_current_phase_accuracy_rate",
        ),
        "execution_engine_last_successful_phase_accurate": expected_clear(
            "execution_engine_expected_last_successful_phase_count",
            "execution_engine_last_successful_phase_accuracy_rate",
        ),
        "execution_engine_authoritative_lane_accurate": expected_clear(
            "execution_engine_expected_authoritative_lane_count",
            "execution_engine_authoritative_lane_accuracy_rate",
        ),
        "execution_engine_target_lane_accurate": expected_clear(
            "execution_engine_expected_target_lane_count",
            "execution_engine_target_lane_accuracy_rate",
        ),
        "execution_engine_resume_token_accurate": expected_clear(
            "execution_engine_expected_resume_token_count",
            "execution_engine_resume_token_accuracy_rate",
        ),
        "execution_engine_host_family_accurate": expected_clear(
            "execution_engine_expected_host_family_count",
            "execution_engine_host_family_accuracy_rate",
        ),
        "execution_engine_model_family_accurate": expected_clear(
            "execution_engine_expected_model_family_count",
            "execution_engine_model_family_accuracy_rate",
        ),
        "execution_engine_component_id_accurate": expected_clear(
            "execution_engine_expected_component_id_count",
            "execution_engine_component_id_accuracy_rate",
        ),
        "execution_engine_canonical_component_id_accurate": expected_clear(
            "execution_engine_expected_canonical_component_id_count",
            "execution_engine_canonical_component_id_accuracy_rate",
        ),
        "execution_engine_identity_status_accurate": expected_clear(
            "execution_engine_expected_identity_status_count",
            "execution_engine_identity_status_accuracy_rate",
        ),
        "execution_engine_target_component_status_accurate": expected_clear(
            "execution_engine_expected_target_component_status_count",
            "execution_engine_target_component_status_accuracy_rate",
        ),
        "execution_engine_snapshot_reuse_status_accurate": expected_clear(
            "execution_engine_expected_snapshot_reuse_status_count",
            "execution_engine_snapshot_reuse_status_accuracy_rate",
        ),
        "execution_engine_reanchor_accurate": expected_clear(
            "execution_engine_expected_reanchor_count",
            "execution_engine_reanchor_accuracy_rate",
        ),
        "execution_engine_delegation_guard_accurate": expected_clear(
            "execution_engine_expected_delegation_guard_count",
            "execution_engine_delegation_guard_accuracy_rate",
        ),
        "execution_engine_parallelism_guard_accurate": expected_clear(
            "execution_engine_expected_parallelism_guard_count",
            "execution_engine_parallelism_guard_accuracy_rate",
        ),
    }


def quality_gate_failed(summary: Mapping[str, Any]) -> bool:
    return any(not ok for ok in acceptance_checks(summary).values())


LOWER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "execution_engine_false_admit_rate",
        "execution_engine_false_deny_rate",
        "execution_engine_median_context_packet_build_ms",
        "execution_engine_median_snapshot_duration_ms",
        "execution_engine_median_prompt_bundle_tokens",
        "execution_engine_median_runtime_contract_tokens",
        "execution_engine_median_total_payload_tokens",
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
        "execution_engine_component_id_accuracy_rate",
        "execution_engine_canonical_component_id_accuracy_rate",
        "execution_engine_identity_status_accuracy_rate",
        "execution_engine_target_component_status_accuracy_rate",
        "execution_engine_snapshot_reuse_status_accuracy_rate",
        "execution_engine_reanchor_accuracy_rate",
        "execution_engine_delegation_guard_accuracy_rate",
        "execution_engine_parallelism_guard_accuracy_rate",
    }
)
