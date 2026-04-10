from __future__ import annotations

from typing import Any, Mapping, Sequence


FAMILY = "context_engine_grounding"


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
    return _token(row.get("scenario_family") or row.get("family"))


def _expected_tokens(details: Mapping[str, Any], field_name: str) -> set[str]:
    expected = details.get(f"expected_{field_name}")
    if isinstance(expected, list):
        return {str(token).strip() for token in expected if str(token).strip()}
    token = _token(expected)
    return {token} if token else set()


def _packet_source(row: Mapping[str, Any]) -> str:
    packet = _packet(row)
    return _token(row.get("packet_source")) or _token(packet.get("packet_source"))


def _runtime_adoption(row: Mapping[str, Any]) -> dict[str, Any]:
    orchestration = dict(row.get("orchestration", {})) if isinstance(row.get("orchestration"), Mapping) else {}
    return (
        dict(orchestration.get("odylith_adoption", {}))
        if isinstance(orchestration.get("odylith_adoption"), Mapping)
        else {}
    )


def _backed(row: Mapping[str, Any]) -> bool:
    details = _expectation_details(row)
    return bool(
        _family(row) == FAMILY
        or _expected_tokens(details, "packet_source")
        or _expected_tokens(details, "selection_state")
        or _expected_tokens(details, "workstream")
    )


def _rate(flags: Sequence[bool]) -> float:
    values = [1.0 if bool(flag) else 0.0 for flag in flags]
    if not values:
        return 0.0
    return round(sum(values) / max(1, len(values)), 3)


def summary_from_rows(scenario_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [row for row in scenario_rows if isinstance(row, Mapping) and _backed(row)]
    packet_source_accuracy: list[bool] = []
    selection_state_accuracy: list[bool] = []
    workstream_accuracy: list[bool] = []
    ambiguity_fail_closed: list[bool] = []
    session_namespaced: list[bool] = []
    packet_source_backed_count = 0
    selection_state_backed_count = 0
    workstream_backed_count = 0
    ambiguity_backed_count = 0
    runtime_backed_count = 0

    for row in rows:
        packet = _packet(row)
        details = _expectation_details(row)

        expected_packet_sources = _expected_tokens(details, "packet_source")
        if expected_packet_sources:
            packet_source_backed_count += 1
            packet_source_accuracy.append(_packet_source(row) in expected_packet_sources)

        expected_selection_states = _expected_tokens(details, "selection_state")
        observed_selection_state = _token(packet.get("selection_state"))
        if expected_selection_states:
            selection_state_backed_count += 1
            selection_state_accuracy.append(observed_selection_state in expected_selection_states)
            if expected_selection_states.intersection({"ambiguous", "none"}):
                ambiguity_backed_count += 1
                ambiguity_fail_closed.append(
                    not bool(packet.get("route_ready")) and not bool(packet.get("native_spawn_ready"))
                )

        expected_workstreams = _expected_tokens(details, "workstream")
        if expected_workstreams:
            workstream_backed_count += 1
            workstream_accuracy.append(_token(packet.get("workstream")) in expected_workstreams)

        adoption = _runtime_adoption(row)
        if adoption:
            runtime_backed_count += 1
            session_namespaced.append(bool(adoption.get("session_namespaced")))

    return {
        "context_engine_backed_scenario_count": len(rows),
        "context_engine_expected_packet_source_count": packet_source_backed_count,
        "context_engine_expected_selection_state_count": selection_state_backed_count,
        "context_engine_expected_workstream_count": workstream_backed_count,
        "context_engine_ambiguity_backed_scenario_count": ambiguity_backed_count,
        "context_engine_runtime_backed_scenario_count": runtime_backed_count,
        "context_engine_packet_source_accuracy_rate": _rate(packet_source_accuracy),
        "context_engine_selection_state_accuracy_rate": _rate(selection_state_accuracy),
        "context_engine_workstream_accuracy_rate": _rate(workstream_accuracy),
        "context_engine_fail_closed_ambiguity_rate": _rate(ambiguity_fail_closed),
        "context_engine_session_namespace_rate": _rate(session_namespaced),
    }


def comparison(*, candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "context_engine_packet_source_accuracy_delta": round(
            float(candidate.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "context_engine_selection_state_accuracy_delta": round(
            float(candidate.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "context_engine_workstream_accuracy_delta": round(
            float(candidate.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0)
            - float(baseline.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0),
            3,
        ),
        "context_engine_fail_closed_ambiguity_delta": round(
            float(candidate.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0)
            - float(baseline.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0),
            3,
        ),
        "context_engine_session_namespace_delta": round(
            float(candidate.get("context_engine_session_namespace_rate", 0.0) or 0.0)
            - float(baseline.get("context_engine_session_namespace_rate", 0.0) or 0.0),
            3,
        ),
    }


LOWER_BETTER_SUMMARY_FIELDS = frozenset()
HIGHER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "context_engine_packet_source_accuracy_rate",
        "context_engine_selection_state_accuracy_rate",
        "context_engine_workstream_accuracy_rate",
        "context_engine_fail_closed_ambiguity_rate",
        "context_engine_session_namespace_rate",
    }
)
