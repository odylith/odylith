"""Benchmark summary helpers for the live proof-discipline family."""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from odylith.runtime.evaluation import benchmark_metric_helpers


def _token(value: Any) -> str:
    """Normalize arbitrary values into stripped comparison tokens."""
    return str(value or "").strip()


def _packet(row: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the benchmark packet payload as a mutable mapping copy."""
    return dict(row.get("packet", {})) if isinstance(row.get("packet"), Mapping) else {}


def _expectation_details(row: Mapping[str, Any]) -> dict[str, Any]:
    """Extract structured expectation details from a benchmark row."""
    return (
        dict(row.get("expectation_details", {}))
        if isinstance(row.get("expectation_details"), Mapping)
        else {}
    )


def _family(row: Mapping[str, Any]) -> str:
    """Return the declared scenario family for a benchmark row."""
    return _token(row.get("scenario_family") or row.get("family"))


def _has_expectation_key(details: Mapping[str, Any], prefix: str) -> bool:
    """Return whether expectation details contain fields with the given prefix."""
    return any(str(key).startswith(prefix) for key in details)


def _proof_backed(row: Mapping[str, Any]) -> bool:
    """Return whether the row carries proof-discipline benchmark evidence."""
    packet = _packet(row)
    details = _expectation_details(row)
    return bool(
        _family(row) == "live_proof_discipline"
        or packet.get("proof_state_present")
        or _has_expectation_key(details, "expected_proof_")
        or _has_expectation_key(details, "expected_claim_guard_")
    )


def _expected_highest_truthful_claim(*, proof_status: str, hosted_frontier_advanced: bool) -> str:
    """Return the truthful claim label implied by the proof-state packet."""
    if hosted_frontier_advanced:
        return "fixed live"
    return {
        "diagnosed": "diagnosed",
        "fixed_in_code": "fixed in code",
        "unit_tested": "unit-tested",
        "preview_tested": "preview-tested",
        "deployed": "deployed",
        "live_verified": "fixed live",
        "falsified_live": "falsified live",
    }.get(proof_status, "diagnosed")


def _expected_frontier_advanced(packet: Mapping[str, Any]) -> bool:
    """Return whether the packet implies a hosted frontier advancement."""
    proof_status = _token(packet.get("proof_status"))
    if proof_status == "live_verified":
        return True
    if proof_status != "deployed":
        return False
    first_phase = _token(packet.get("proof_first_failing_phase"))
    frontier_phase = _token(packet.get("proof_frontier_phase"))
    return bool(first_phase and frontier_phase and frontier_phase != first_phase)


def summary_from_rows(scenario_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize proof-discipline accuracy from benchmark rows."""
    proof_rows = [row for row in scenario_rows if isinstance(row, Mapping) and _proof_backed(row)]
    packets = [_packet(row) for row in proof_rows if _packet(row)]
    proof_present = [bool(packet.get("proof_state_present")) for packet in packets]
    false_clearance = [
        _token(packet.get("claim_guard_highest_truthful_claim")) == "fixed live"
        and not bool(packet.get("claim_guard_hosted_frontier_advanced"))
        for packet in packets
        if bool(packet.get("proof_state_present"))
    ]
    frontier_gate = [
        bool(packet.get("claim_guard_hosted_frontier_advanced")) == _expected_frontier_advanced(packet)
        for packet in packets
        if bool(packet.get("proof_state_present"))
    ]
    claim_guard = [
        _token(packet.get("claim_guard_highest_truthful_claim"))
        == _expected_highest_truthful_claim(
            proof_status=_token(packet.get("proof_status")),
            hosted_frontier_advanced=bool(packet.get("claim_guard_hosted_frontier_advanced")),
        )
        for packet in packets
        if bool(packet.get("proof_state_present"))
    ]
    same_fingerprint_reuse = [
        (
            not bool(packet.get("claim_guard_same_fingerprint_as_last_falsification"))
            or bool(packet.get("proof_same_fingerprint_reopened"))
        )
        for packet in packets
        if bool(packet.get("proof_state_present"))
    ]
    same_fingerprint_rows = [
        packet
        for packet in packets
        if bool(packet.get("proof_state_present"))
        and (
            bool(packet.get("claim_guard_same_fingerprint_as_last_falsification"))
            or bool(packet.get("proof_same_fingerprint_reopened"))
        )
    ]
    return {
        "proof_discipline_backed_scenario_count": len(proof_rows),
        "proof_state_backed_scenario_count": len([packet for packet in packets if bool(packet.get("proof_state_present"))]),
        "proof_same_fingerprint_backed_scenario_count": len(same_fingerprint_rows),
        "proof_state_present_rate": benchmark_metric_helpers.boolean_rate(proof_present),
        "false_clearance_rate": benchmark_metric_helpers.boolean_rate(false_clearance),
        "proof_frontier_gate_accuracy_rate": benchmark_metric_helpers.boolean_rate(frontier_gate),
        "proof_claim_guard_accuracy_rate": benchmark_metric_helpers.boolean_rate(claim_guard),
        "proof_same_fingerprint_reuse_rate": benchmark_metric_helpers.boolean_rate(
            same_fingerprint_reuse
        ),
    }


def comparison(*, candidate: Mapping[str, Any], baseline: Mapping[str, Any]) -> dict[str, Any]:
    """Compare candidate and baseline proof-discipline family summaries."""
    return benchmark_metric_helpers.summary_deltas(
        candidate=candidate,
        baseline=baseline,
        field_map={
            "proof_state_present_rate_delta": "proof_state_present_rate",
            "false_clearance_rate_delta": "false_clearance_rate",
            "proof_frontier_gate_accuracy_delta": "proof_frontier_gate_accuracy_rate",
            "proof_claim_guard_accuracy_delta": "proof_claim_guard_accuracy_rate",
            "proof_same_fingerprint_reuse_delta": "proof_same_fingerprint_reuse_rate",
        },
    )


LOWER_BETTER_SUMMARY_FIELDS = frozenset({"false_clearance_rate"})
HIGHER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "proof_state_present_rate",
        "proof_frontier_gate_accuracy_rate",
        "proof_claim_guard_accuracy_rate",
        "proof_same_fingerprint_reuse_rate",
    }
)
