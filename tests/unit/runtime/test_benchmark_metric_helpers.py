"""Coverage for shared benchmark metric helper functions."""

from __future__ import annotations

from odylith.runtime.evaluation import benchmark_metric_helpers


def test_boolean_rate_handles_empty_and_mixed_rows() -> None:
    assert benchmark_metric_helpers.boolean_rate([]) == 0.0
    assert benchmark_metric_helpers.boolean_rate([True, False, True]) == 0.667


def test_summary_delta_coerces_missing_and_string_values() -> None:
    assert (
        benchmark_metric_helpers.summary_delta(
            {"metric": "2.5"},
            {"metric": 1.0},
            "metric",
        )
        == 1.5
    )
    assert benchmark_metric_helpers.summary_delta({}, {}, "metric") == 0.0


def test_numeric_value_uses_fallbacks_and_invalid_values_fail_closed() -> None:
    assert benchmark_metric_helpers.numeric_value(
        {"primary": "", "fallback": "4.25"},
        "primary",
        fallback_fields=("fallback",),
    ) == 4.25
    assert benchmark_metric_helpers.numeric_value(
        {"primary": "nope"},
        "primary",
    ) == 0.0


def test_numeric_delta_supports_fallbacks_and_mismatched_fields() -> None:
    assert (
        benchmark_metric_helpers.numeric_delta(
            {"effective_estimated_tokens": "", "codex_prompt_estimated_tokens": 12},
            {"effective_estimated_tokens": 5},
            candidate_field="effective_estimated_tokens",
            candidate_fallback_fields=("codex_prompt_estimated_tokens",),
        )
        == 7.0
    )
    assert (
        benchmark_metric_helpers.numeric_delta(
            {"candidate_latency": 9.5},
            {"baseline_latency": 6.0},
            candidate_field="candidate_latency",
            baseline_field="baseline_latency",
        )
        == 3.5
    )


def test_summary_deltas_maps_output_names_to_summary_fields() -> None:
    assert benchmark_metric_helpers.summary_deltas(
        candidate={"candidate_rate": 0.9, "latency_ms": 12.0},
        baseline={"candidate_rate": 0.4, "latency_ms": 10.0},
        field_map={
            "candidate_rate_delta": "candidate_rate",
            "latency_delta_ms": "latency_ms",
        },
    ) == {
        "candidate_rate_delta": 0.5,
        "latency_delta_ms": 2.0,
    }
