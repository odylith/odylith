"""Shared Odylith benchmark corpus and report contract helpers."""

from __future__ import annotations

from typing import Any, Mapping

_PACKET_SCENARIO_KEYS: tuple[str, ...] = ("scenarios", "cases")
_ARCHITECTURE_SCENARIO_KEYS: tuple[str, ...] = ("architecture_scenarios", "architecture_cases")


def _scenario_rows(
    corpus: Mapping[str, Any] | None,
    *,
    keys: tuple[str, ...],
) -> tuple[str, list[dict[str, Any]]]:
    if not isinstance(corpus, Mapping):
        return keys[0], []
    for key in keys:
        value = corpus.get(key)
        if isinstance(value, list):
            return key, [dict(row) for row in value if isinstance(row, Mapping)]
    return keys[0], []


def packet_benchmark_scenarios(corpus: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return packet benchmark scenarios while tolerating legacy corpus keys."""

    _selected_key, rows = _scenario_rows(corpus, keys=_PACKET_SCENARIO_KEYS)
    return rows


def architecture_benchmark_scenarios(corpus: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    """Return architecture benchmark scenarios while tolerating legacy corpus keys."""

    _selected_key, rows = _scenario_rows(corpus, keys=_ARCHITECTURE_SCENARIO_KEYS)
    return rows


def benchmark_corpus_contract(corpus: Mapping[str, Any] | None) -> dict[str, Any]:
    """Describe which benchmark corpus keys are present and selected."""

    packet_key, packet_rows = _scenario_rows(corpus, keys=_PACKET_SCENARIO_KEYS)
    architecture_key, architecture_rows = _scenario_rows(corpus, keys=_ARCHITECTURE_SCENARIO_KEYS)
    canonical_packet_present = isinstance(dict(corpus or {}).get("scenarios"), list)
    canonical_architecture_present = isinstance(dict(corpus or {}).get("architecture_scenarios"), list)
    legacy_packet_present = isinstance(dict(corpus or {}).get("cases"), list)
    legacy_architecture_present = isinstance(dict(corpus or {}).get("architecture_cases"), list)
    if canonical_packet_present and canonical_architecture_present:
        status = "canonical"
    elif legacy_packet_present or legacy_architecture_present:
        status = "legacy_alias"
    else:
        status = "unseeded"
    if (canonical_packet_present and legacy_packet_present) or (
        canonical_architecture_present and legacy_architecture_present
    ):
        status = "mixed_alias"
    return {
        "status": status,
        "packet_scenario_key": packet_key,
        "architecture_scenario_key": architecture_key,
        "packet_scenario_count": len(packet_rows),
        "architecture_scenario_count": len(architecture_rows),
        "canonical_packet_key_present": canonical_packet_present,
        "canonical_architecture_key_present": canonical_architecture_present,
        "legacy_packet_key_present": legacy_packet_present,
        "legacy_architecture_key_present": legacy_architecture_present,
    }


__all__ = [
    "architecture_benchmark_scenarios",
    "benchmark_corpus_contract",
    "packet_benchmark_scenarios",
]
