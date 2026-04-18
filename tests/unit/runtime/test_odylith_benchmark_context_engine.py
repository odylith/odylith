"""Coverage for context-engine benchmark summary helpers and contracts."""

from __future__ import annotations

from pathlib import Path

from odylith.runtime.evaluation import odylith_benchmark_context_engine
from odylith.runtime.evaluation import odylith_benchmark_prompt_family_rules
from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_taxonomy
from odylith.runtime.context_engine import odylith_context_engine_store as store


REPO_ROOT = Path(__file__).resolve().parents[3]


def test_context_engine_family_is_curated_and_taxonomized() -> None:
    assert odylith_benchmark_prompt_family_rules.family_zero_support_doc_expansion("context_engine_grounding") is True
    assert odylith_benchmark_prompt_family_rules.family_uses_curated_doc_overrides("context_engine_grounding") is True
    assert odylith_benchmark_prompt_family_rules.family_anchors_all_required_docs("context_engine_grounding") is True
    assert (
        odylith_benchmark_prompt_family_rules.support_doc_family_rank(
            path="odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
            family="context_engine_grounding",
        )
        == 0
    )
    assert odylith_benchmark_taxonomy.family_group_label("context_engine_grounding") == "Grounding / Orchestration Control"


def test_mode_summary_aggregates_context_engine_metrics() -> None:
    summary = runner._mode_summary(  # noqa: SLF001
        mode="odylith_on",
        scenario_rows=[
            {
                "kind": "packet",
                "scenario_family": "context_engine_grounding",
                "packet_source": "impact",
                "latency_ms": 8.0,
                "effective_estimated_tokens": 64,
                "packet": {
                    "packet_source": "impact",
                    "packet_kind": "impact",
                    "packet_state": "compact",
                    "selection_state": "explicit",
                    "workstream": "B-067",
                    "within_budget": True,
                    "route_ready": True,
                    "native_spawn_ready": True,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_packet_source": ["impact"],
                    "expected_selection_state": ["explicit"],
                    "expected_workstream": ["B-067"],
                },
                "orchestration": {
                    "odylith_adoption": {
                        "session_namespace": "benchmark-session-a",
                        "session_namespaced": True,
                    }
                },
            },
            {
                "kind": "packet",
                "scenario_family": "context_engine_grounding",
                "packet_source": "impact",
                "latency_ms": 9.0,
                "effective_estimated_tokens": 60,
                "packet": {
                    "packet_source": "impact",
                    "packet_kind": "impact",
                    "packet_state": "gated_broad_scope",
                    "selection_state": "none",
                    "within_budget": True,
                    "route_ready": False,
                    "native_spawn_ready": False,
                },
                "expectation_ok": True,
                "expectation_details": {
                    "expected_packet_source": ["impact"],
                    "expected_selection_state": ["none"],
                },
                "orchestration": {
                    "odylith_adoption": {
                        "session_namespace": "benchmark-session-b",
                        "session_namespaced": False,
                    }
                },
            },
        ],
    )

    assert summary["context_engine_backed_scenario_count"] == 2
    assert summary["context_engine_expected_packet_source_count"] == 2
    assert summary["context_engine_expected_selection_state_count"] == 2
    assert summary["context_engine_expected_workstream_count"] == 1
    assert summary["context_engine_ambiguity_backed_scenario_count"] == 1
    assert summary["context_engine_runtime_backed_scenario_count"] == 2
    assert summary["context_engine_packet_source_accuracy_rate"] == 1.0
    assert summary["context_engine_selection_state_accuracy_rate"] == 1.0
    assert summary["context_engine_workstream_accuracy_rate"] == 1.0
    assert summary["context_engine_fail_closed_ambiguity_rate"] == 1.0
    assert summary["context_engine_session_namespace_rate"] == 0.5


def test_context_engine_session_namespace_only_counts_runtime_backed_rows() -> None:
    summary = odylith_benchmark_context_engine.summary_from_rows(
        [
            {
                "scenario_family": "context_engine_grounding",
                "packet": {
                    "selection_state": "explicit",
                    "route_ready": True,
                    "native_spawn_ready": True,
                },
                "expectation_details": {
                    "expected_selection_state": ["explicit"],
                },
                "orchestration": {
                    "odylith_adoption": {
                        "runtime_source": "none",
                        "runtime_transport": "none",
                        "session_namespaced": False,
                    }
                },
            }
        ]
    )

    assert summary["context_engine_runtime_backed_scenario_count"] == 0
    assert summary["context_engine_session_namespace_rate"] == 0.0


def test_summary_comparison_includes_context_engine_deltas() -> None:
    comparison = runner._summary_comparison(  # noqa: SLF001
        candidate_mode="odylith_on",
        baseline_mode="raw_agent_baseline",
        mode_summaries={
            "odylith_on": {
                "context_engine_packet_source_accuracy_rate": 1.0,
                "context_engine_selection_state_accuracy_rate": 1.0,
                "context_engine_workstream_accuracy_rate": 1.0,
                "context_engine_fail_closed_ambiguity_rate": 1.0,
                "context_engine_session_namespace_rate": 1.0,
            },
            "raw_agent_baseline": {
                "context_engine_packet_source_accuracy_rate": 0.0,
                "context_engine_selection_state_accuracy_rate": 0.0,
                "context_engine_workstream_accuracy_rate": 0.0,
                "context_engine_fail_closed_ambiguity_rate": 0.0,
                "context_engine_session_namespace_rate": 0.0,
            },
        },
    )

    assert comparison["context_engine_packet_source_accuracy_delta"] == 1.0
    assert comparison["context_engine_selection_state_accuracy_delta"] == 1.0
    assert comparison["context_engine_workstream_accuracy_delta"] == 1.0
    assert comparison["context_engine_fail_closed_ambiguity_delta"] == 1.0
    assert comparison["context_engine_session_namespace_delta"] == 1.0


def test_acceptance_holds_on_context_engine_scope_regressions() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "context_engine_expected_packet_source_count": 1,
                "context_engine_expected_selection_state_count": 1,
                "context_engine_expected_workstream_count": 1,
                "context_engine_ambiguity_backed_scenario_count": 1,
                "context_engine_runtime_backed_scenario_count": 1,
                "context_engine_packet_source_accuracy_rate": 0.0,
                "context_engine_selection_state_accuracy_rate": 0.0,
                "context_engine_workstream_accuracy_rate": 0.0,
                "context_engine_fail_closed_ambiguity_rate": 0.0,
                "context_engine_session_namespace_rate": 0.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "context_engine_expected_packet_source_count": 1,
                "context_engine_expected_selection_state_count": 1,
                "context_engine_expected_workstream_count": 1,
                "context_engine_ambiguity_backed_scenario_count": 1,
                "context_engine_runtime_backed_scenario_count": 1,
                "context_engine_packet_source_accuracy_rate": 1.0,
                "context_engine_selection_state_accuracy_rate": 1.0,
                "context_engine_workstream_accuracy_rate": 1.0,
                "context_engine_fail_closed_ambiguity_rate": 1.0,
                "context_engine_session_namespace_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "required_path_precision_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "validation_success_delta": 0.0,
            "write_surface_precision_delta": 0.0,
            "unnecessary_widening_rate_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 0.0,
            "median_prompt_token_delta": 0.0,
            "median_total_payload_token_delta": 0.0,
            "context_engine_packet_source_accuracy_delta": -1.0,
            "context_engine_selection_state_accuracy_delta": -1.0,
            "context_engine_workstream_accuracy_delta": -1.0,
            "context_engine_fail_closed_ambiguity_delta": -1.0,
            "context_engine_session_namespace_delta": -1.0,
        },
        family_summaries={
            "context_engine_grounding": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "context_engine_expected_packet_source_count": 1,
                    "context_engine_expected_selection_state_count": 1,
                    "context_engine_expected_workstream_count": 1,
                    "context_engine_ambiguity_backed_scenario_count": 1,
                    "context_engine_runtime_backed_scenario_count": 1,
                    "context_engine_packet_source_accuracy_rate": 0.0,
                    "context_engine_selection_state_accuracy_rate": 0.0,
                    "context_engine_workstream_accuracy_rate": 0.0,
                    "context_engine_fail_closed_ambiguity_rate": 0.0,
                    "context_engine_session_namespace_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "context_engine_expected_packet_source_count": 1,
                    "context_engine_expected_selection_state_count": 1,
                    "context_engine_expected_workstream_count": 1,
                    "context_engine_ambiguity_backed_scenario_count": 1,
                    "context_engine_runtime_backed_scenario_count": 1,
                    "context_engine_packet_source_accuracy_rate": 1.0,
                    "context_engine_selection_state_accuracy_rate": 1.0,
                    "context_engine_workstream_accuracy_rate": 1.0,
                    "context_engine_fail_closed_ambiguity_rate": 1.0,
                    "context_engine_session_namespace_rate": 1.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["context_engine_packet_source_accurate"] is False
    assert acceptance["checks"]["context_engine_selection_state_accurate"] is False
    assert acceptance["checks"]["context_engine_workstream_accurate"] is False
    assert acceptance["checks"]["context_engine_ambiguity_fail_closed"] is False
    assert acceptance["checks"]["context_engine_session_namespaced"] is False
    assert "context_engine_grounding" in acceptance["weak_families"]


def test_context_engine_family_packet_exposes_current_repo_scope_contract() -> None:
    scenario = {
        "scenario_id": "probe-context-engine-split",
        "family": "context_engine_grounding",
        "packet_source": "adaptive",
        "changed_paths": [
            "src/odylith/runtime/context_engine/odylith_context_engine_projection_query_runtime.py",
            "src/odylith/runtime/context_engine/odylith_context_engine_packet_summary_runtime.py",
            "tests/unit/runtime/test_context_engine_split_hardening.py",
        ],
        "workstream": "B-067",
        "component": "odylith-context-engine",
        "validation_commands": [
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_context_engine_split_hardening.py"
        ],
        "intent": "implementation validation",
        "kind": "packet",
        "needs_write": False,
    }

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert summary["packet_kind"] == "impact"
    assert summary["packet_state"] == "compact"
    assert summary["selection_state"] == "explicit"
    assert summary["workstream"] == "B-067"
    assert summary["route_ready"] is True


def test_context_engine_family_packet_stays_fail_closed_on_broad_scope() -> None:
    scenario = {
        "scenario_id": "probe-context-engine-broad",
        "family": "context_engine_grounding",
        "packet_source": "adaptive",
        "changed_paths": [
            "AGENTS.md",
            "odylith/AGENTS.md",
        ],
        "validation_commands": [],
        "intent": "analysis benchmark",
        "kind": "packet",
        "needs_write": False,
    }

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert summary["packet_kind"] == "impact"
    assert summary["packet_state"] == "gated_broad_scope"
    assert summary["selection_state"] == "none"
    assert summary["route_ready"] is False
    assert summary["native_spawn_ready"] is False


def test_context_engine_summary_helper_tracks_fail_closed_ambiguity_rows() -> None:
    summary = odylith_benchmark_context_engine.summary_from_rows(
        [
            {
                "scenario_family": "context_engine_grounding",
                "packet_source": "impact",
                "packet": {
                    "selection_state": "none",
                    "route_ready": False,
                    "native_spawn_ready": False,
                },
                "expectation_details": {
                    "expected_packet_source": ["impact"],
                    "expected_selection_state": ["none"],
                },
            }
        ]
    )

    assert summary["context_engine_ambiguity_backed_scenario_count"] == 1
    assert summary["context_engine_fail_closed_ambiguity_rate"] == 1.0
