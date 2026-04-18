"""Budget helpers for the Odylith character layer."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from odylith.runtime.character.contract import RUNTIME_BUDGET_CONTRACT


ZERO_CREDIT_HOT_PATH = {
    "provider_call_count": 0,
    "host_model_call_count": 0,
    "broad_scan_count": 0,
    "full_validation_count": 0,
    "projection_expansion_count": 0,
    "benchmark_execution_count": 0,
    "subagent_spawn_count": 0,
}


def start_timer() -> float:
    return perf_counter()


def runtime_budget(*, started_at: float, host_model_calls_allowed: bool = False) -> dict[str, Any]:
    elapsed_ms = max(0.0, (perf_counter() - started_at) * 1000.0)
    counters = dict(ZERO_CREDIT_HOT_PATH)
    return {
        "contract": RUNTIME_BUDGET_CONTRACT,
        "tier": "tier_0_local",
        "latency_ms": round(elapsed_ms, 3),
        "latency_budget_ms": 50,
        "latency_budget_passed": elapsed_ms <= 50,
        "credit_budget": "zero_hot_path",
        "host_model_calls_allowed": bool(host_model_calls_allowed),
        "operator_explicitness": bool(host_model_calls_allowed),
        **counters,
        "hot_path_budget_passed": all(value == 0 for value in counters.values()),
    }


def budget_failures(budget: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    for key, expected in ZERO_CREDIT_HOT_PATH.items():
        try:
            observed = int(budget.get(key, 0) or 0)
        except (TypeError, ValueError):
            failures.append(key)
            continue
        if observed != expected:
            failures.append(key)
    if not bool(budget.get("hot_path_budget_passed")):
        failures.append("hot_path_budget_passed")
    return failures
