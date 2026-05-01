from __future__ import annotations

from odylith.runtime.orchestration import subagent_signal_normalization as signals


def test_mapping_value_accepts_router_alias_tokens() -> None:
    payload = {"rc": "high", "ic": "medium", "cp": True}

    assert signals.mapping_value(payload, "routing_confidence") == "high"
    assert signals.mapping_value(payload, "intent_confidence") == "medium"
    assert signals.mapping_value(payload, "intent_critical_path") is True


def test_signal_normalization_handles_lists_mappings_and_nested_lookup() -> None:
    payload = {
        "Routing Handoff": {
            "recommended_commands": [" pytest ", "", "pytest"],
            "packet quality": {"cd": "high"},
        },
        "bad key": {},
    }

    normalized = signals.normalize_context_signals(payload)

    assert list(normalized.keys()) == ["Routing Handoff", "bad key"]
    assert signals.normalize_list([" path/a.py ", "", "path/a.py", " path/b.py "]) == [
        "path/a.py",
        "path/a.py",
        "path/b.py",
    ]
    assert signals.nested_mapping(normalized, "routing_handoff", "packet_quality") == {"cd": "high"}
    assert signals.context_lookup(normalized, "routing_handoff", "packet_quality", "context_density_level") == "high"


def test_normalized_rate_handles_booleans_ratios_percentages_and_invalid_values() -> None:
    assert signals.normalized_rate(True) == 1.0
    assert signals.normalized_rate(False) == 0.0
    assert signals.normalized_rate(0.25) == 0.25
    assert signals.normalized_rate(75) == 0.75
    assert signals.normalized_rate(250) == 1.0
    assert signals.normalized_rate("not-a-number") == 0.0


def test_count_or_list_len_prefers_stronger_explicit_or_inferred_count() -> None:
    assert signals.count_or_list_len({"items": ["a", "b"], "count": 1}, list_key="items", count_key="count") == 2
    assert signals.count_or_list_len({"items": "a", "count": 3}, list_key="items", count_key="count") == 3
