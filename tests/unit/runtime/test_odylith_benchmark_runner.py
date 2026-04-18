from __future__ import annotations

import collections
import contextlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import threading
import tempfile

import pytest

from odylith.runtime.evaluation import odylith_benchmark_runner as runner
from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_hot_path_delivery_runtime
from odylith.runtime.context_engine import odylith_context_engine_hot_path_governance_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import path_bundle_codec
from odylith.runtime.orchestration import subagent_orchestrator
from odylith.runtime.orchestration import subagent_router


REPO_ROOT = Path(__file__).resolve().parents[3]


def _force_codex_host_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "benchmark-test-thread")
    monkeypatch.delenv("CODEX_SHELL", raising=False)


def _write_corpus(tmp_path: Path, payload: dict[str, object]) -> None:
    corpus_path = tmp_path / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    corpus_path.parent.mkdir(parents=True, exist_ok=True)
    corpus_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_load_benchmark_scenarios_preserves_benchmark_metadata(tmp_path: Path) -> None:
    _write_corpus(
        tmp_path,
        {
            "version": "v1",
            "program": {},
            "cases": [
                {
                    "case_id": "critical-router-fix",
                    "label": "Critical router fix",
                    "family": "validation_heavy_fix",
                    "priority": "high",
                    "benchmark": {
                        "prompt": "Fix the router slice carefully.",
                        "packet_source": "bootstrap_session",
                        "paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
                        "required_paths": ["src/odylith/runtime/orchestration/subagent_router.py", "tests/unit/runtime/test_subagent_router.py"],
                        "supporting_paths": ["odylith/skills/odylith-subagent-router/SKILL.md"],
                        "expected_write_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
                        "critical_paths": ["src/odylith/runtime/orchestration/subagent_router.py", "tests/unit/runtime/test_subagent_router.py"],
                        "validation_commands": ["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/runtime/test_subagent_router.py"],
                        "focused_local_checks": ["Run the router unit test first."],
                        "packet_fixture": {
                            "proof_state": {
                                "frontier_phase": "verify",
                                "proof_status": "diagnosed",
                            }
                        },
                        "allow_noop_completion": True,
                        "correctness_critical": True,
                        "live_timeout_seconds": 210.0,
                    },
                    "match": {"paths_any": ["src/odylith/runtime/orchestration/subagent_router.py"]},
                    "expect": {"within_budget": True},
                }
            ],
            "architecture_cases": [
                {
                    "case_id": "architecture-self",
                    "label": "Architecture self audit",
                    "priority": "medium",
                    "benchmark": {
                        "paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
                        "required_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
                    },
                    "match": {"paths_any": ["src/odylith/runtime/context_engine/odylith_context_engine.py"], "domains_any": ["odylith-context-engine"]},
                    "expect": {"contract_touchpoints_min": 1},
                }
            ],
        },
    )

    scenarios = runner.load_benchmark_scenarios(repo_root=tmp_path)
    assert len(scenarios) == 2

    packet = next(row for row in scenarios if row["scenario_id"] == "critical-router-fix")
    assert packet["required_paths"] == ["src/odylith/runtime/orchestration/subagent_router.py", "tests/unit/runtime/test_subagent_router.py"]
    assert packet["supporting_paths"] == ["odylith/skills/odylith-subagent-router/SKILL.md"]
    assert packet["expected_write_paths"] == ["src/odylith/runtime/orchestration/subagent_router.py"]
    assert packet["critical_paths"] == ["src/odylith/runtime/orchestration/subagent_router.py", "tests/unit/runtime/test_subagent_router.py"]
    assert packet["packet_source"] == "bootstrap_session"
    assert packet["validation_commands"] == ["PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest -q tests/unit/runtime/test_subagent_router.py"]
    assert packet["focused_local_checks"] == ["Run the router unit test first."]
    assert packet["packet_fixture"] == {
        "proof_state": {
            "frontier_phase": "verify",
            "proof_status": "diagnosed",
        }
    }
    assert packet["allow_noop_completion"] is True
    assert packet["correctness_critical"] is True
    assert packet["live_timeout_seconds"] == 210.0
    assert packet["intent"] == "implementation benchmark"

    architecture = next(row for row in scenarios if row["scenario_id"] == "architecture-self")
    assert architecture["kind"] == "architecture"
    assert architecture["required_paths"] == ["src/odylith/runtime/context_engine/odylith_context_engine.py"]


def test_load_benchmark_scenarios_defaults_broad_shared_scope_to_analysis_intent(tmp_path: Path) -> None:
    _write_corpus(
        tmp_path,
        {
            "version": "v1",
            "program": {},
            "cases": [
                {
                    "case_id": "broad-shared",
                    "label": "Broad shared",
                    "family": "broad_shared_scope",
                    "priority": "critical",
                    "benchmark": {
                        "paths": ["AGENTS.md", "agents-guidelines/TOOLING.MD"],
                    },
                    "match": {"paths_all": ["AGENTS.md", "agents-guidelines/TOOLING.MD"]},
                    "expect": {"within_budget": True},
                }
            ],
            "architecture_cases": [],
        },
    )

    scenarios = runner.load_benchmark_scenarios(repo_root=tmp_path)

    assert len(scenarios) == 1
    assert scenarios[0]["intent"] == "analysis benchmark"


def test_load_benchmark_scenarios_accepts_canonical_scenario_keys(tmp_path: Path) -> None:
    _write_corpus(
        tmp_path,
        {
            "version": "v1",
            "program": {},
            "scenarios": [
                {
                    "case_id": "canonical-scenario",
                    "label": "Canonical scenario",
                    "family": "cross_file_feature",
                    "priority": "medium",
                    "benchmark": {
                        "paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
                        "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
                        "needs_write": True,
                    },
                    "match": {"paths_any": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"]},
                }
            ],
            "architecture_scenarios": [
                {
                    "case_id": "canonical-architecture",
                    "label": "Canonical architecture",
                    "priority": "low",
                    "benchmark": {
                        "paths": ["src/odylith/runtime/context_engine/odylith_architecture_mode.py"],
                        "required_paths": ["src/odylith/runtime/context_engine/odylith_architecture_mode.py"],
                    },
                    "match": {"paths_any": ["src/odylith/runtime/context_engine/odylith_architecture_mode.py"]},
                }
            ],
        },
    )

    scenarios = runner.load_benchmark_scenarios(repo_root=tmp_path)

    assert {row["scenario_id"] for row in scenarios} == {"canonical-scenario", "canonical-architecture"}
    packet = next(row for row in scenarios if row["scenario_id"] == "canonical-scenario")
    assert packet["needs_write"] is True


def test_precision_metrics_treat_supporting_paths_as_relevant_without_changing_required_recall() -> None:
    metrics = runner._precision_metrics(  # noqa: SLF001
        required_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        supporting_paths=["odylith/skills/odylith-subagent-router/SKILL.md"],
        observed_paths=[
            "src/odylith/runtime/orchestration/subagent_router.py",
            "odylith/skills/odylith-subagent-router/SKILL.md",
            "README.md",
        ],
        expected_write_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        candidate_write_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
    )

    assert metrics["required_path_precision_basis"] == "required_plus_supporting_paths"
    assert metrics["supporting_path_hits"] == ["odylith/skills/odylith-subagent-router/SKILL.md"]
    assert metrics["required_path_precision"] == 0.667
    assert metrics["hallucinated_surfaces"] == ["README.md"]
    recall, misses = runner._path_recall(  # noqa: SLF001
        required_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        observed_paths=["odylith/skills/odylith-subagent-router/SKILL.md"],
    )
    assert recall == 0.0
    assert misses == ["src/odylith/runtime/orchestration/subagent_router.py"]


def test_packet_source_for_scenario_prefers_lightest_safe_lane() -> None:
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "context_engine_grounding", "packet_source": "adaptive", "workstream": "B-067"}
    ) == "adaptive"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "broad_shared_scope", "packet_source": "bootstrap_session", "workstream": ""}
    ) == "bootstrap_session"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "broad_shared_scope", "workstream": ""}
    ) == "impact"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "exact_anchor_recall", "workstream": "B-275"}
    ) == "impact"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "validation_heavy_fix", "workstream": ""}
    ) == "impact"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "docs_code_closeout", "workstream": ""}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "explicit_workstream", "workstream": "B-275"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "governed_surface_sync", "workstream": ""}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "install_upgrade_runtime", "workstream": "B-005"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "release_publication", "workstream": "B-020"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "daemon_security", "workstream": "B-014"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "component_governance", "workstream": "B-020"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "agent_activation", "workstream": "B-016"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "cross_surface_governance_sync", "workstream": "B-021"}
    ) == "governance_slice"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "merge_heavy_change", "workstream": ""}
    ) == "impact"
    assert runner._packet_source_for_scenario(  # noqa: SLF001
        {"family": "retrieval_miss_recovery", "workstream": ""}
    ) == "impact"


def test_load_benchmark_scenarios_preserves_explicit_component_seed() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    assert scenario["workstream"] == "B-020"
    assert scenario["component"] == "benchmark"


def test_packet_token_breakdown_separates_prompt_runtime_and_operator_weight() -> None:
    payload = {
        "context_packet": {"packet_kind": "impact", "docs": ["src/odylith/runtime/orchestration/subagent_router.py"]},
        "narrowing_guidance": {"required": False, "reason": "grounded"},
        "retrieval_plan": {"packet_kind": "impact"},
        "routing_handoff": {"routing_confidence": "high"},
        "packet_quality": {"routing_confidence": "high"},
        "evidence_pack": {"packet_kind": "impact"},
        "working_memory_tiers": {"hot": {"changed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"]}},
        "packet_metrics": {"estimated_tokens": 100},
        "impact_summary": {"components": [{"entity_id": "cmp-router"}]},
        "runtime": {"timings": {"recent": [{"operation": "impact", "duration_ms": 12.0}]}},
    }

    breakdown = runner._packet_token_breakdown(  # noqa: SLF001
        payload=payload,
        packet_source="impact",
        mode="odylith_on",
        full_scan={},
    )

    assert breakdown["effective_token_basis"] == "codex_prompt_bundle"
    assert breakdown["codex_prompt_estimated_tokens"] > 0
    assert breakdown["runtime_contract_estimated_tokens"] > 0
    assert breakdown["operator_diag_estimated_tokens"] > 0
    assert breakdown["prompt_artifact_tokens"]["context_packet"] > 0
    assert breakdown["runtime_contract_artifact_tokens"]["routing_handoff"] > 0
    assert breakdown["operator_diag_artifact_tokens"]["impact_summary"] > 0
    assert breakdown["total_payload_estimated_tokens"] >= breakdown["codex_prompt_estimated_tokens"]


def test_run_benchmarks_emits_corpus_and_family_summaries(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    scenarios = [
        {
            "scenario_id": "critical-router-fix",
            "kind": "packet",
            "label": "Critical router fix",
            "summary": "validation-heavy router slice",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "workstream": "B-275",
            "required_paths": ["src/odylith/runtime/orchestration/subagent_router.py", "tests/unit/runtime/test_subagent_router.py"],
            "validation_commands": ["pytest tests/unit/runtime/test_subagent_router.py"],
            "needs_write": True,
            "correctness_critical": True,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "architecture-self",
            "kind": "architecture",
            "label": "Architecture self audit",
            "summary": "odylith architecture slice",
            "family": "architecture",
            "priority": "medium",
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "workstream": "",
            "required_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"contract_touchpoints_min": 1},
        },
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(
        runner.odylith_context_cache,
        "read_json_object",
        lambda path: {"version": "v1", "scenarios": [], "architecture_scenarios": []}
        if str(path).endswith("optimization-evaluation-corpus.v1.json")
        else {},
    )
    monkeypatch.setattr(
        runner,
        "_run_live_adoption_proof",
        lambda *, repo_root, scenarios: {
            "sample_size": len(list(scenarios)),
            "packet_present_rate": 1.0,
            "auto_grounded_rate": 1.0,
            "requires_widening_rate": 0.0,
            "grounded_delegate_rate": 0.5,
            "workspace_daemon_reused_rate": 1.0,
            "session_namespaced_rate": 1.0,
        },
    )
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 0.75,
            "native_spawn_ready_rate": 0.75,
            "architecture_covered_case_count": 1,
            "architecture_satisfied_case_count": 1,
        },
    )
    monkeypatch.setattr(runner, "_prepare_benchmark_runtime_cache", lambda *, repo_root, cache_profile: None)

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        del repo_root
        del benchmark_profile
        family = str(scenario["family"])
        if family == "validation_heavy_fix":
            if mode in {"odylith_repo_scan_baseline", "raw_agent_baseline"}:
                return {
                    "kind": "packet",
                    "mode": mode,
                    "packet_source": "bootstrap_session",
                    "latency_ms": 20.0,
                    "packet": {"within_budget": True, "route_ready": True},
                    "expectation_ok": True,
                    "expectation_details": {},
                    "required_path_recall": 1.0,
                    "required_path_misses": [],
                    "critical_path_misses": [],
                    "observed_paths": [*list(scenario["required_paths"]), "docs/extra.md"],
                    "observed_path_count": 3,
                    "required_path_precision": 0.667,
                    "hallucinated_surface_count": 1,
                    "hallucinated_surface_rate": 0.333,
                    "expected_write_path_count": 1,
                    "candidate_write_path_count": 2,
                    "candidate_write_paths": ["src/odylith/runtime/orchestration/subagent_router.py", "docs/extra.md"],
                    "write_surface_precision": 0.5,
                    "unnecessary_widening_count": 1,
                    "unnecessary_widening_rate": 0.5,
                    "effective_estimated_tokens": 200,
                    "total_payload_estimated_tokens": 200,
                    "validation_success_proxy": 1.0,
                    "full_scan": {},
                    "orchestration": {"leaf_count": 0},
                }
            return {
                "kind": "packet",
                "mode": mode,
                "packet_source": "bootstrap_session",
                "latency_ms": 10.0,
                "packet": {"within_budget": True, "route_ready": True},
                "expectation_ok": True,
                "expectation_details": {},
                "required_path_recall": 1.0,
                "required_path_misses": [],
                "critical_path_misses": [],
                "observed_paths": list(scenario["required_paths"]),
                "observed_path_count": 2,
                "required_path_precision": 1.0,
                "hallucinated_surface_count": 0,
                "hallucinated_surface_rate": 0.0,
                "expected_write_path_count": 1,
                "candidate_write_path_count": 1,
                "candidate_write_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
                "write_surface_precision": 1.0,
                "unnecessary_widening_count": 0,
                "unnecessary_widening_rate": 0.0,
                "effective_estimated_tokens": 120,
                "total_payload_estimated_tokens": 120,
                "validation_success_proxy": 1.0,
                "full_scan": {},
                "orchestration": {"leaf_count": 1 if mode == "odylith_on" else 0},
            }
        if mode in {"odylith_repo_scan_baseline", "raw_agent_baseline"}:
            return {
                "kind": "architecture",
                "mode": mode,
                "latency_ms": 25.0,
                "dossier": {},
                "expectation_ok": False,
                "expectation_details": {"baseline_mode": "repo_scan_only"},
                "required_path_recall": 1.0,
                "required_path_misses": [],
                "critical_path_misses": [],
                "observed_paths": list(scenario["required_paths"]),
                "observed_path_count": 1,
                "required_path_precision": 1.0,
                "hallucinated_surface_count": 0,
                "hallucinated_surface_rate": 0.0,
                "expected_write_path_count": 0,
                "candidate_write_path_count": 0,
                "candidate_write_paths": [],
                "write_surface_precision": 1.0,
                "unnecessary_widening_count": 0,
                "unnecessary_widening_rate": 0.0,
                "effective_estimated_tokens": 160,
                "validation_success_proxy": 1.0,
                "full_scan": {},
                "orchestration": {"leaf_count": 0},
            }
        return {
            "kind": "architecture",
            "mode": mode,
            "latency_ms": 12.0,
            "dossier": {"resolved": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": list(scenario["required_paths"]),
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 90,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        }

    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        modes=(
            "odylith_on",
            "odylith_on_no_fanout",
            "odylith_repo_scan_baseline",
            "raw_agent_baseline",
        ),
    )

    assert report["corpus_summary"]["scenario_count"] == 2
    assert report["corpus_summary"]["write_surface_backed_scenario_count"] == 1
    assert report["corpus_summary"]["correctness_critical_scenario_count"] == 1
    assert report["corpus_summary"]["critical_required_path_backed_scenario_count"] == 1
    assert report["corpus_contract"]["status"] == "canonical"
    assert report["corpus_contract"]["packet_scenario_key"] == "scenarios"
    assert report["selection"]["scenario_ids"] == []
    assert report["mode_summaries"]["odylith_on"]["critical_validation_success_rate"] == 1.0
    assert report["mode_summaries"]["odylith_on"]["required_path_precision_rate"] == 1.0
    assert report["mode_summaries"]["odylith_on"]["hallucinated_surface_rate"] == 0.0
    assert report["family_summaries"]["validation_heavy_fix"]["odylith_on"]["scenario_count"] == 1
    assert report["family_summaries"]["architecture"]["odylith_repo_scan_baseline"]["scenario_count"] == 1
    assert report["packet_source_summaries"]["bootstrap_session"]["odylith_on"]["scenario_count"] == 1
    assert report["family_deltas"]["validation_heavy_fix"]["required_path_precision_delta"] == 0.333
    assert report["published_family_deltas"]["validation_heavy_fix"]["required_path_precision_delta"] == 0.333
    assert report["primary_comparison"]["critical_validation_success_delta"] == 0.0
    assert report["primary_comparison"]["required_path_precision_delta"] == 0.166
    assert report["primary_comparison"]["hallucinated_surface_rate_delta"] == -0.167
    assert report["primary_comparison"]["write_surface_precision_delta"] == 0.5
    assert report["primary_comparison"]["unnecessary_widening_rate_delta"] == -0.5
    assert report["primary_comparison"]["median_prompt_token_delta"] == -75.0
    assert report["primary_comparison"]["median_total_payload_token_delta"] == -75.0
    assert report["published_summary"]["required_path_precision_delta"] == 0.166
    assert report["published_summary"]["hallucinated_surface_rate_delta"] == -0.167
    assert report["published_summary"]["write_surface_precision_delta"] == 0.5
    assert report["published_summary"]["unnecessary_widening_rate_delta"] == -0.5
    assert report["published_summary"]["bootstrap_session_total_payload_token_delta"] == -80.0
    assert report["published_pair_timing_summary"]["pair_count"] == 2
    assert report["published_pair_timing_summary"]["median_pair_wall_clock_ms"] == 22.5
    assert report["published_pair_timing_summary"]["total_pair_wall_clock_ms"] == 45.0
    assert report["full_pair_timing_summary"]["pair_count"] == 4
    assert report["full_pair_timing_summary"]["median_pair_wall_clock_ms"] == 22.5
    assert report["full_pair_timing_summary"]["p95_pair_wall_clock_ms"] == 25.0
    assert report["full_pair_timing_summary"]["total_pair_wall_clock_ms"] == 90.0
    assert report["robustness_summary"]["selected_cache_profile_count"] == 2
    assert report["robustness_summary"]["warm_cold_consistency_cleared"] is True
    assert report["status"] == "provisional_pass"
    assert report["acceptance"]["status"] == "provisional_pass"
    assert runner.latest_report_path(repo_root=tmp_path).is_file()
    assert runner.history_report_path(repo_root=tmp_path, report_id=report["report_id"]).is_file()


def test_run_benchmarks_quick_profile_defaults_to_bounded_sentinel_matched_pair(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "release-critical",
            "kind": "packet",
            "label": "Release critical",
            "summary": "release critical",
            "family": "release_publication",
            "priority": "critical",
            "changed_paths": ["docs/benchmarks/README.md"],
            "workstream": "B-020",
            "required_paths": ["docs/benchmarks/README.md"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "release-high",
            "kind": "packet",
            "label": "Release high",
            "summary": "release high",
            "family": "release_publication",
            "priority": "high",
            "changed_paths": ["README.md"],
            "workstream": "B-020",
            "required_paths": ["README.md"],
            "validation_commands": [],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "daemon-critical",
            "kind": "packet",
            "label": "Daemon critical",
            "summary": "daemon critical",
            "family": "daemon_security",
            "priority": "critical",
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "workstream": "B-014",
            "required_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_odylith_context_engine.py"],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "docs-medium",
            "kind": "packet",
            "label": "Docs medium",
            "summary": "docs medium",
            "family": "docs_code_closeout",
            "priority": "medium",
            "changed_paths": ["docs/benchmarks/REVIEWER_GUIDE.md"],
            "workstream": "",
            "required_paths": ["docs/benchmarks/REVIEWER_GUIDE.md"],
            "validation_commands": [],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]
    seen_calls: list[tuple[str, str]] = []

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(
        runner.odylith_context_cache,
        "read_json_object",
        lambda path: {"version": "v1", "scenarios": [], "architecture_scenarios": []}
        if str(path).endswith("optimization-evaluation-corpus.v1.json")
        else {},
    )
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": len(list(scenarios))})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prepare_benchmark_runtime_cache", lambda *, repo_root, cache_profile: None)

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        del repo_root
        del benchmark_profile
        seen_calls.append((str(scenario["scenario_id"]), mode))
        return {
            "kind": "packet",
            "mode": mode,
            "packet_source": "governance_slice",
            "latency_ms": 12.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": list(scenario["required_paths"]),
            "observed_path_count": len(list(scenario["required_paths"])),
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 1,
            "candidate_write_path_count": 1,
            "candidate_write_paths": list(scenario["required_paths"]),
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 120,
            "total_payload_estimated_tokens": 120,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        }

    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)

    report = runner.run_benchmarks(repo_root=tmp_path, benchmark_profile=runner.BENCHMARK_PROFILE_QUICK, write_report=False)

    assert report["benchmark_profile"] == "quick"
    assert report["selection_strategy"] == "quick_sentinel_smoke"
    assert report["selection"]["profile_default_narrowing"] == "quick_sentinel_smoke"
    assert report["selection"]["default_modes_applied"] is True
    assert report["selection"]["default_cache_profiles_applied"] is True
    assert report["modes"] == ["odylith_on", "raw_agent_baseline"]
    assert report["cache_profiles"] == ["warm"]
    assert report["scenario_count"] == 3
    assert report["latest_eligible"] is False
    assert ("release-high", "odylith_on") not in seen_calls
    assert ("release-critical", "odylith_on") in seen_calls
    assert ("release-critical", "raw_agent_baseline") in seen_calls


def test_quick_profile_default_is_bounded_current_head_sentinel_smoke() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    selection = runner._resolve_benchmark_scenario_selection(  # noqa: SLF001
        all_scenarios=scenarios,
        benchmark_profile=runner.BENCHMARK_PROFILE_QUICK,
    )

    selected_ids = [str(row.get("scenario_id", "")).strip() for row in selection["scenarios"]]

    assert selection["selection_strategy"] == "quick_sentinel_smoke"
    assert len(selected_ids) <= runner._QUICK_PROFILE_MAX_SCENARIOS  # noqa: SLF001
    assert set(selected_ids) == set(runner._QUICK_PROFILE_SENTINEL_CASE_IDS)  # noqa: SLF001


def test_run_benchmarks_supports_family_filtered_shards(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "release_publication",
            "priority": "high",
            "changed_paths": ["docs/benchmarks/README.md"],
            "workstream": "B-020",
            "required_paths": ["docs/benchmarks/README.md"],
            "validation_commands": [],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "daemon_security",
            "priority": "high",
            "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "workstream": "B-014",
            "required_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
            "validation_commands": [],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-c",
            "kind": "packet",
            "label": "Case C",
            "summary": "C",
            "family": "docs_code_closeout",
            "priority": "high",
            "changed_paths": ["docs/benchmarks/REVIEWER_GUIDE.md"],
            "workstream": "",
            "required_paths": ["docs/benchmarks/REVIEWER_GUIDE.md"],
            "validation_commands": [],
            "needs_write": True,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-d",
            "kind": "packet",
            "label": "Case D",
            "summary": "D",
            "family": "architecture",
            "priority": "medium",
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "workstream": "",
            "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "validation_commands": [],
            "needs_write": False,
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(
        runner.odylith_context_cache,
        "read_json_object",
        lambda path: {"version": "v1", "scenarios": [], "architecture_scenarios": []}
        if str(path).endswith("optimization-evaluation-corpus.v1.json")
        else {},
    )
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": len(list(scenarios))})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prepare_benchmark_runtime_cache", lambda *, repo_root, cache_profile: None)
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda *, repo_root, scenario, mode, benchmark_profile=runner.BENCHMARK_PROFILE_PROOF: {
            "kind": "packet",
            "mode": mode,
            "packet_source": "impact",
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": list(scenario["required_paths"]),
            "observed_path_count": len(list(scenario["required_paths"])),
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 1 if bool(scenario.get("needs_write")) else 0,
            "candidate_write_path_count": 1 if bool(scenario.get("needs_write")) else 0,
            "candidate_write_paths": list(scenario["required_paths"]) if bool(scenario.get("needs_write")) else [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 100,
            "total_payload_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        modes=("odylith_on", "odylith_off"),
        cache_profiles=("warm",),
        families=("release_publication", "daemon_security", "docs_code_closeout"),
        shard_count=2,
        shard_index=2,
        write_report=False,
    )

    assert report["benchmark_profile"] == "proof"
    assert report["selection_strategy"] == "manual_selection"
    assert report["selection"]["family_filters"] == ["daemon_security", "docs_code_closeout", "release_publication"]
    assert report["selection_family_filters"] == ["daemon_security", "docs_code_closeout", "release_publication"]
    assert isinstance(report["hard_quality_gate_cleared"], bool)
    assert report["hard_gate_cleared"] is report["hard_quality_gate_cleared"]
    assert isinstance(report["hard_gate_failures"], list)
    assert report["selection"]["shard_count"] == 2
    assert report["selection"]["shard_index"] == 2
    assert report["latest_eligible"] is False
    assert [row["scenario_id"] for row in report["scenarios"]] == ["case-b"]


def test_run_live_scenario_batch_executes_public_pair_once_with_matched_pair_metadata(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    validator_path = tmp_path / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py"
    validator_path.parent.mkdir(parents=True, exist_ok=True)
    validator_path.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")
    scenario = {
        "scenario_id": "live-pair",
        "kind": "packet",
        "label": "Live pair",
        "summary": "pair",
        "family": "validation_heavy_fix",
        "priority": "high",
        "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        "workstream": "B-022",
        "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        "validation_commands": ["pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"],
        "needs_write": True,
        "correctness_critical": True,
        "acceptance_criteria": ["Keep it grounded."],
    }
    entered_modes: list[str] = []
    gate = threading.Event()
    lock = threading.Lock()

    monkeypatch.setattr(runner, "_existing_repo_paths", lambda **_: list(scenario["changed_paths"]))
    monkeypatch.setattr(
        runner,
        "_build_packet_payload",
        lambda **_: (
            "governance_slice",
            {
                "context_packet": {
                    "anchors": {"changed_paths": list(scenario["changed_paths"])},
                },
                "docs": ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
                "narrowing_guidance": {"required": False},
            },
            {},
        ),
    )

    def _fake_run_live_scenario(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str,
        benchmark_session_namespace: str = "",
        packet_source: str,
        prompt_payload: dict[str, object] | None = None,
        packet_summary: dict[str, object] | None = None,
        snapshot_paths: list[str] | None = None,
    ) -> dict[str, object]:
        del repo_root, packet_source
        assert benchmark_profile == runner.BENCHMARK_PROFILE_PROOF
        assert benchmark_session_namespace
        with lock:
            entered_modes.append(mode)
            if len(entered_modes) == 2:
                gate.set()
        assert gate.wait(timeout=0.5), "live public pair did not overlap"
        assert snapshot_paths is not None
        assert "src/odylith/runtime/evaluation/odylith_benchmark_runner.py" in snapshot_paths
        assert "tests/unit/runtime/test_odylith_benchmark_runner.py" in snapshot_paths
        if mode == "odylith_on":
            assert prompt_payload is not None
            assert packet_summary is not None
            assert prompt_payload["context_packet"]["anchors"]["changed_paths"] == [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py"
            ]
            assert prompt_payload["strict_boundary"] is True
            assert packet_summary["packet_kind"] == "governance_slice"
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": list(scenario["required_paths"]),
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 1,
            "candidate_write_path_count": 1,
            "candidate_write_paths": list(scenario["required_paths"]),
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 100,
            "total_payload_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
            "live_execution": {},
        }

    monkeypatch.setattr(runner.odylith_benchmark_live_execution, "run_live_scenario", _fake_run_live_scenario)

    results = runner._run_live_scenario_batch(  # noqa: SLF001
        repo_root=tmp_path,
        scenario=scenario,
        modes=("odylith_on", "odylith_off"),
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    assert list(results) == ["odylith_on", "raw_agent_baseline"]
    assert sorted(entered_modes) == ["odylith_on", "raw_agent_baseline"]
    assert results["odylith_on"]["live_execution"]["matched_pair_batch"] is True
    assert results["raw_agent_baseline"]["live_execution"]["matched_pair_batch"] is True
    assert results["odylith_on"]["live_execution"]["matched_pair_batch_size"] == 2
    assert results["odylith_on"]["live_execution"]["matched_pair_modes"] == ["odylith_on", "raw_agent_baseline"]
    assert results["odylith_on"]["live_execution"]["latency_measurement_basis"] == "matched_pair_contended_validated_task_cycle"


def test_run_live_scenario_batch_converts_mode_exceptions_into_failed_results(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenario = {
        "scenario_id": "live-pair-failure",
        "kind": "packet",
        "label": "Live pair failure",
        "summary": "pair failure",
        "family": "validation_heavy_fix",
        "priority": "high",
        "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        "workstream": "B-022",
        "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        "validation_commands": [],
        "needs_write": True,
        "correctness_critical": True,
        "critical_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
    }

    def _fake_prepare_live_scenario_request(**kwargs: object) -> dict[str, object]:
        mode = str(kwargs["mode"])
        return {
            "repo_root": kwargs["repo_root"],
            "scenario": dict(kwargs["scenario"]),
            "mode": mode,
            "benchmark_profile": kwargs["benchmark_profile"],
            "packet_source": "impact" if mode == "odylith_on" else "raw_codex_cli",
            "prompt_payload": {},
            "packet_summary": {},
        }

    def _fake_run_prepared_live_scenario(prepared_request: dict[str, object]) -> dict[str, object]:
        mode = str(prepared_request["mode"])
        if mode == "odylith_on":
            raise RuntimeError("live child died")
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": 5.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": list(scenario["required_paths"]),
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 1,
            "candidate_write_path_count": 1,
            "candidate_write_paths": list(scenario["required_paths"]),
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 10,
            "total_payload_estimated_tokens": 10,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
            "live_execution": {},
        }

    monkeypatch.setattr(runner, "_prepare_live_scenario_request", _fake_prepare_live_scenario_request)
    monkeypatch.setattr(runner, "_run_prepared_live_scenario", _fake_run_prepared_live_scenario)

    results = runner._run_live_scenario_batch(  # noqa: SLF001
        repo_root=tmp_path,
        scenario=scenario,
        modes=("odylith_on", "odylith_off"),
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    assert list(results) == ["odylith_on", "raw_agent_baseline"]
    assert results["odylith_on"]["expectation_ok"] is False
    assert results["odylith_on"]["validation_success_proxy"] == 0.0
    assert results["odylith_on"]["benchmark_exception"] == "RuntimeError: live child died"
    assert results["odylith_on"]["live_execution"]["benchmark_exception"] == "RuntimeError: live child died"
    assert results["raw_agent_baseline"]["expectation_ok"] is True


def test_live_workspace_snapshot_paths_include_dirty_same_package_python_dependencies(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "compass_dashboard_shell.py"
    sibling = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "render_compass_dashboard.py"
    same_dir_unrelated = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "auto_update_mermaid_diagrams.py"
    unrelated = repo_root / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine.py"
    test_path = repo_root / "tests" / "integration" / "runtime" / "test_surface_browser_smoke.py"
    for path in (changed, sibling, same_dir_unrelated, unrelated, test_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(
                [
                    "src/odylith/runtime/surfaces/compass_dashboard_shell.py",
                    "src/odylith/runtime/surfaces/render_compass_dashboard.py",
                    "src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py",
                    "src/odylith/runtime/context_engine/odylith_context_engine.py",
                ]
            )
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/runtime/surfaces/compass_dashboard_shell.py"],
                "validation_commands": ["pytest -q tests/integration/runtime/test_surface_browser_smoke.py"],
            },
            prompt_payload={},
        )

    assert "src/odylith/runtime/surfaces/compass_dashboard_shell.py" in paths
    assert "src/odylith/runtime/surfaces/render_compass_dashboard.py" in paths
    assert "src/odylith/runtime/surfaces/auto_update_mermaid_diagrams.py" not in paths
    assert "src/odylith/runtime/context_engine/odylith_context_engine.py" not in paths


def test_live_workspace_snapshot_paths_include_dirty_imported_cross_package_python_dependencies(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "install" / "manager.py"
    dirty_imported = repo_root / "src" / "odylith" / "runtime" / "common" / "consumer_profile.py"
    unrelated = repo_root / "src" / "odylith" / "runtime" / "common" / "product_assets.py"
    validation_test = repo_root / "tests" / "integration" / "install" / "test_manager.py"
    changed.parent.mkdir(parents=True, exist_ok=True)
    dirty_imported.parent.mkdir(parents=True, exist_ok=True)
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    validation_test.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text(
        "\n".join(
            [
                "from odylith.runtime.common.consumer_profile import write_consumer_profile",
                "",
                "def install_bundle():",
                "    return write_consumer_profile",
                "",
            ]
        ),
        encoding="utf-8",
    )
    dirty_imported.write_text("def write_consumer_profile():\n    return None\n", encoding="utf-8")
    unrelated.write_text("def bundled_product_root():\n    return None\n", encoding="utf-8")
    validation_test.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(
                [
                    "src/odylith/install/manager.py",
                    "src/odylith/runtime/common/consumer_profile.py",
                    "src/odylith/runtime/common/product_assets.py",
                ]
            )
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/install/manager.py"],
                "validation_commands": ["pytest -q tests/integration/install/test_manager.py"],
            },
            prompt_payload={},
        )

    assert "src/odylith/runtime/common/consumer_profile.py" in paths
    assert "src/odylith/runtime/common/product_assets.py" not in paths


def test_live_workspace_snapshot_paths_include_dirty_source_dependencies_imported_by_validator_tests(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "install" / "manager.py"
    dirty_cli = repo_root / "src" / "odylith" / "cli.py"
    dirty_command_surface = repo_root / "src" / "odylith" / "runtime" / "common" / "command_surface.py"
    unrelated = repo_root / "src" / "odylith" / "runtime" / "common" / "consumer_profile.py"
    validation_test = repo_root / "tests" / "unit" / "test_cli.py"
    for path in (changed, dirty_cli, dirty_command_surface, unrelated, validation_test):
        path.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("def install_bundle():\n    return None\n", encoding="utf-8")
    dirty_cli.write_text("from odylith.runtime.common import command_surface\n", encoding="utf-8")
    dirty_command_surface.write_text("def args():\n    return []\n", encoding="utf-8")
    unrelated.write_text("def write_consumer_profile():\n    return None\n", encoding="utf-8")
    validation_test.write_text(
        "\n".join(
            [
                "from odylith import cli",
                "from odylith.runtime.common import command_surface",
                "",
                "def test_cli():",
                "    assert cli",
                "    assert command_surface",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(
                [
                    "src/odylith/install/manager.py",
                    "src/odylith/cli.py",
                    "src/odylith/runtime/common/command_surface.py",
                    "src/odylith/runtime/common/consumer_profile.py",
                ]
            )
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/install/manager.py"],
                "validation_commands": ["pytest -q tests/unit/test_cli.py"],
            },
            prompt_payload={},
        )

    assert "src/odylith/cli.py" in paths
    assert "src/odylith/runtime/common/command_surface.py" in paths
    assert "src/odylith/runtime/common/consumer_profile.py" not in paths


def test_live_workspace_snapshot_paths_follow_clean_intermediaries_to_dirty_import_descendants(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "install" / "manager.py"
    clean_intermediary = repo_root / "src" / "odylith" / "install" / "repair.py"
    dirty_descendant = repo_root / "src" / "odylith" / "runtime" / "context_engine" / "odylith_context_engine_store.py"
    unrelated_dirty = repo_root / "src" / "odylith" / "runtime" / "memory" / "odylith_remote_retrieval.py"
    validation_test = repo_root / "tests" / "integration" / "install" / "test_manager.py"
    for path in (changed, clean_intermediary, dirty_descendant, unrelated_dirty, validation_test):
        path.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("from odylith.install.repair import reset_local_state\n", encoding="utf-8")
    clean_intermediary.write_text(
        "from odylith.runtime.context_engine import odylith_context_engine_store\n",
        encoding="utf-8",
    )
    dirty_descendant.write_text("STATE = 'dirty'\n", encoding="utf-8")
    unrelated_dirty.write_text("REMOTE = 'dirty'\n", encoding="utf-8")
    validation_test.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(
                [
                    "src/odylith/install/manager.py",
                    "src/odylith/runtime/context_engine/odylith_context_engine_store.py",
                    "src/odylith/runtime/memory/odylith_remote_retrieval.py",
                ]
            )
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/install/manager.py"],
                "validation_commands": ["pytest -q tests/integration/install/test_manager.py"],
            },
            prompt_payload={},
        )

    assert "src/odylith/runtime/context_engine/odylith_context_engine_store.py" in paths
    assert "src/odylith/runtime/memory/odylith_remote_retrieval.py" not in paths


def test_live_workspace_snapshot_paths_do_not_expand_unrelated_dirty_test_siblings(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    validation_test = repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py"
    dirty_test_sibling = repo_root / "tests" / "unit" / "runtime" / "test_render_compass_dashboard.py"
    for path in (changed, validation_test, dirty_test_sibling):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(
                [
                    "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                    "tests/unit/runtime/test_render_compass_dashboard.py",
                ]
            )
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
                "validation_commands": ["pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"],
            },
            prompt_payload={},
        )

    assert "tests/unit/runtime/test_odylith_benchmark_runner.py" in paths
    assert "tests/unit/runtime/test_render_compass_dashboard.py" not in paths


def test_live_workspace_snapshot_paths_include_validator_companion_repo_files(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "install" / "agents.py"
    validation_test = repo_root / "tests" / "unit" / "install" / "test_agents.py"
    root_agents = repo_root / "AGENTS.md"
    odylith_agents = repo_root / "odylith" / "AGENTS.md"
    for path in (changed, validation_test, root_agents, odylith_agents):
        path.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("def enable():\n    return None\n", encoding="utf-8")
    validation_test.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "",
                'ROOT = Path(__file__).resolve().parents[3]',
                'ROOT_TEXT = (ROOT / \"AGENTS.md\").read_text(encoding=\"utf-8\")',
                'ODY_TEXT = (ROOT / \"odylith\" / \"AGENTS.md\").read_text(encoding=\"utf-8\")',
                "",
                "def test_truth():",
                "    assert ROOT_TEXT",
                "    assert ODY_TEXT",
                "",
            ]
        ),
        encoding="utf-8",
    )
    root_agents.write_text("# root agents\n", encoding="utf-8")
    odylith_agents.write_text("# odylith agents\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "src/odylith/install/agents.py"
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/install/agents.py"],
                "validation_commands": ["pytest -q tests/unit/install/test_agents.py"],
            },
            prompt_payload={},
        )

    assert "AGENTS.md" in paths


def test_live_workspace_snapshot_paths_include_validator_path_chain_companions(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    validation_test = repo_root / "tests" / "unit" / "runtime" / "test_hygiene.py"
    runtime_signal = (
        repo_root / "src" / "odylith" / "runtime" / "orchestration" / "subagent_orchestrator_runtime_signals.py"
    )
    for path in (changed, validation_test, runtime_signal):
        path.parent.mkdir(parents=True, exist_ok=True)
    changed.write_text("# spec\n", encoding="utf-8")
    runtime_signal.write_text("SIGNAL = 'ok'\n", encoding="utf-8")
    validation_test.write_text(
        "\n".join(
            [
                "from pathlib import Path",
                "",
                "ROOT = Path(__file__).resolve().parents[3]",
                "TARGET = ROOT / \"src\" / \"odylith\" / \"runtime\" / \"orchestration\" / \"subagent_orchestrator_runtime_signals.py\"",
                "",
                "def test_truth():",
                "    assert TARGET.read_text(encoding='utf-8')",
                "",
            ]
        ),
        encoding="utf-8",
    )

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "odylith/registry/source/components/benchmark/CURRENT_SPEC.md"
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "src/odylith/runtime/orchestration/subagent_orchestrator_runtime_signals.py"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
                "validation_commands": ["pytest -q tests/unit/runtime/test_hygiene.py"],
            },
            prompt_payload={},
        )

    assert "src/odylith/runtime/orchestration/subagent_orchestrator_runtime_signals.py" in paths


def test_live_workspace_snapshot_paths_include_dirty_registry_and_governance_companions(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    manifest = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    benchmark_spec = repo_root / "odylith" / "registry" / "source" / "components" / "benchmark" / "CURRENT_SPEC.md"
    dashboard_spec = repo_root / "odylith" / "registry" / "source" / "components" / "dashboard" / "CURRENT_SPEC.md"
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    diagram = repo_root / "odylith" / "atlas" / "source" / "odylith-benchmark-proof-and-publication-lane.mmd"
    idea = repo_root / "odylith" / "radar" / "source" / "ideas" / "2026-03" / "2026-03-29-example.md"
    for path in (manifest, benchmark_spec, dashboard_spec, catalog, diagram, idea):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = ""
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "\n".join(
                [
                    "odylith/registry/source/component_registry.v1.json",
                    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    "odylith/registry/source/components/dashboard/CURRENT_SPEC.md",
                    "odylith/atlas/source/catalog/diagrams.v1.json",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                    "odylith/radar/source/ideas/2026-03/2026-03-29-example.md",
                ]
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "required_paths": [
                    "odylith/registry/source/component_registry.v1.json",
                    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    "odylith/atlas/source/catalog/diagrams.v1.json",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                ],
                "validation_commands": ["odylith validate component-registry --repo-root ."],
            },
            prompt_payload={},
        )

    assert "odylith/registry/source/components/dashboard/CURRENT_SPEC.md" in paths
    assert "odylith/radar/source/ideas/2026-03/2026-03-29-example.md" in paths
    assert "odylith/atlas/source/catalog/diagrams.v1.json" in paths
    assert "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd" in paths


def test_live_workspace_snapshot_paths_include_source_local_cli_for_odylith_validators(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    cli_path = repo_root / "src" / "odylith" / "cli.py"
    for path in (changed, cli_path):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "odylith/registry/source/component_registry.v1.json"
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "src/odylith/cli.py"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "required_paths": ["odylith/registry/source/component_registry.v1.json"],
                "validation_commands": ["odylith validate component-registry --repo-root ."],
            },
            prompt_payload={},
        )

    assert "src/odylith/cli.py" in paths


def test_live_workspace_snapshot_paths_include_dirty_governance_roots_for_sync_validators(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    required_paths = [
        "odylith/surfaces/GOVERNANCE_SURFACES.md",
        "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
        "odylith/radar/source/INDEX.md",
    ]
    companion_paths = [
        "odylith/radar/source/ideas/2026-03/2026-03-29-example.md",
        "odylith/technical-plans/in-progress/2026-03/2026-03-29-example.md",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/runtime/delivery_intelligence.v4.json",
    ]
    for relative in [*required_paths, *companion_paths, "src/odylith/cli.py"]:
        path = repo_root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "\n".join(companion_paths)
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "\n".join([*required_paths, *companion_paths, "src/odylith/cli.py"])
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "required_paths": required_paths,
                "validation_commands": [
                    "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
                ],
            },
            prompt_payload={},
        )

    assert "odylith/radar/source/ideas/2026-03/2026-03-29-example.md" in paths
    assert "odylith/technical-plans/in-progress/2026-03/2026-03-29-example.md" in paths
    assert "odylith/registry/source/component_registry.v1.json" in paths
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" in paths
    assert "odylith/atlas/source/catalog/diagrams.v1.json" in paths
    assert "odylith/runtime/delivery_intelligence.v4.json" in paths
    assert "src/odylith/cli.py" in paths


def test_live_workspace_snapshot_paths_include_selected_atlas_catalog_references(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    diagram = repo_root / "odylith" / "atlas" / "source" / "odylith-benchmark-proof-and-publication-lane.mmd"
    diagram_svg = repo_root / "odylith" / "atlas" / "source" / "odylith-benchmark-proof-and-publication-lane.svg"
    diagram_png = repo_root / "odylith" / "atlas" / "source" / "odylith-benchmark-proof-and-publication-lane.png"
    runtime_map_svg = repo_root / "odylith" / "atlas" / "source" / "odylith-product-runtime-boundary-map.svg"
    runtime_map_png = repo_root / "odylith" / "atlas" / "source" / "odylith-product-runtime-boundary-map.png"
    related_plan = repo_root / "odylith" / "technical-plans" / "in-progress" / "2026-03" / "plan.md"
    related_doc = repo_root / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md"
    related_code = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_graphs.py"
    watched_svg = repo_root / "docs" / "benchmarks" / "odylith-benchmark-frontier.svg"
    for path in (
        catalog,
        diagram,
        diagram_svg,
        diagram_png,
        runtime_map_svg,
        runtime_map_png,
        related_plan,
        related_doc,
        related_code,
        watched_svg,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    diagram.write_text("flowchart LR\n", encoding="utf-8")
    diagram_svg.write_text("<svg></svg>\n", encoding="utf-8")
    diagram_png.write_text("png\n", encoding="utf-8")
    runtime_map_svg.write_text("<svg></svg>\n", encoding="utf-8")
    runtime_map_png.write_text("png\n", encoding="utf-8")
    related_plan.write_text("# plan\n", encoding="utf-8")
    related_doc.write_text("# release benchmarks\n", encoding="utf-8")
    related_code.write_text("def render():\n    return None\n", encoding="utf-8")
    watched_svg.write_text("<svg></svg>\n", encoding="utf-8")
    catalog.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-024",
                        "source_mmd": "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                        "source_svg": "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.svg",
                        "source_png": "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.png",
                        "change_watch_paths": ["docs/benchmarks/odylith-benchmark-frontier.svg"],
                        "related_plans": ["odylith/technical-plans/in-progress/2026-03/plan.md"],
                        "related_docs": ["odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md"],
                        "related_code": ["src/odylith/runtime/evaluation/odylith_benchmark_graphs.py"],
                    },
                    {
                        "diagram_id": "D-099",
                        "source_mmd": "odylith/atlas/source/odylith-product-runtime-boundary-map.mmd",
                        "source_svg": "odylith/atlas/source/odylith-product-runtime-boundary-map.svg",
                        "source_png": "odylith/atlas/source/odylith-product-runtime-boundary-map.png",
                    }
                ]
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = ""
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "\n".join(
                [
                    "odylith/atlas/source/catalog/diagrams.v1.json",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                    "odylith/technical-plans/in-progress/2026-03/plan.md",
                    "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                    "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py",
                    "docs/benchmarks/odylith-benchmark-frontier.svg",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.svg",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.png",
                    "odylith/atlas/source/odylith-product-runtime-boundary-map.svg",
                    "odylith/atlas/source/odylith-product-runtime-boundary-map.png",
                ]
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "required_paths": [
                    "odylith/atlas/source/catalog/diagrams.v1.json",
                    "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
                ],
                "validation_commands": ["odylith atlas render --repo-root . --check-only"],
            },
            prompt_payload={},
        )

    assert "odylith/technical-plans/in-progress/2026-03/plan.md" in paths
    assert "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md" in paths
    assert "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py" in paths
    assert "docs/benchmarks/odylith-benchmark-frontier.svg" in paths
    assert "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.svg" in paths
    assert "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.png" in paths
    assert "odylith/atlas/source/odylith-product-runtime-boundary-map.svg" in paths
    assert "odylith/atlas/source/odylith-product-runtime-boundary-map.png" in paths


def test_live_workspace_snapshot_paths_include_imported_validator_runtime_dependencies(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    validator = repo_root / "tests" / "unit" / "runtime" / "test_render_mermaid_catalog.py"
    render_catalog = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "render_mermaid_catalog.py"
    delivery_intelligence = repo_root / "src" / "odylith" / "runtime" / "governance" / "delivery_intelligence_engine.py"
    reasoning_init = repo_root / "src" / "odylith" / "runtime" / "reasoning" / "__init__.py"
    reasoning_reasoning = repo_root / "src" / "odylith" / "runtime" / "reasoning" / "odylith_reasoning.py"
    surfaces_init = repo_root / "src" / "odylith" / "runtime" / "surfaces" / "__init__.py"
    for path in (
        validator,
        render_catalog,
        delivery_intelligence,
        reasoning_init,
        reasoning_reasoning,
        surfaces_init,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
    validator.write_text(
        "from odylith.runtime.surfaces import render_mermaid_catalog as renderer\n",
        encoding="utf-8",
    )
    render_catalog.write_text(
        "from odylith.runtime.governance import delivery_intelligence_engine\n",
        encoding="utf-8",
    )
    delivery_intelligence.write_text(
        "from odylith.runtime.reasoning import odylith_reasoning\n",
        encoding="utf-8",
    )
    reasoning_init.write_text('"""reasoning package"""\n', encoding="utf-8")
    reasoning_reasoning.write_text("def judge():\n    return True\n", encoding="utf-8")
    surfaces_init.write_text('"""surfaces package"""\n', encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = ""
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "\n".join(
                [
                    "tests/unit/runtime/test_render_mermaid_catalog.py",
                    "src/odylith/runtime/surfaces/render_mermaid_catalog.py",
                    "src/odylith/runtime/governance/delivery_intelligence_engine.py",
                    "src/odylith/runtime/reasoning/__init__.py",
                    "src/odylith/runtime/reasoning/odylith_reasoning.py",
                    "src/odylith/runtime/surfaces/__init__.py",
                ]
            )
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "required_paths": ["tests/unit/runtime/test_render_mermaid_catalog.py"],
                "validation_commands": [
                    "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_render_mermaid_catalog.py"
                ],
            },
            prompt_payload={},
    )

    assert "src/odylith/runtime/surfaces/render_mermaid_catalog.py" in paths
    assert "src/odylith/runtime/governance/delivery_intelligence_engine.py" in paths
    assert "src/odylith/runtime/reasoning/__init__.py" in paths
    assert "src/odylith/runtime/reasoning/odylith_reasoning.py" in paths


def test_live_workspace_snapshot_paths_include_benchmark_corpus_for_runner_and_graph_validator_tests(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    runner_test = repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py"
    graphs_test = repo_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_graphs.py"
    source_corpus = repo_root / "odylith" / "runtime" / "source" / "optimization-evaluation-corpus.v1.json"
    bundle_corpus = (
        repo_root
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "odylith"
        / "runtime"
        / "source"
        / "optimization-evaluation-corpus.v1.json"
    )
    for path in (changed, runner_test, graphs_test, source_corpus, bundle_corpus):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("{}", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "src/odylith/runtime/evaluation/odylith_benchmark_runner.py"
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = ""
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
                "validation_commands": [
                    "pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py"
                ],
            },
            prompt_payload={},
        )

    assert "odylith/runtime/source/optimization-evaluation-corpus.v1.json" in paths
    assert "src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json" in paths


def test_acceptance_requires_critical_metric_coverage() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": -5.0,
            "median_token_delta": -20.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 2,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["critical_metric_coverage_complete"] is False


def test_acceptance_holds_when_local_memory_substrate_is_inactive() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "validation_backed_scenario_count": 1,
                "critical_required_path_backed_scenario_count": 1,
                "critical_validation_backed_scenario_count": 1,
                "expectation_success_rate": 1.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "within_budget_rate": 1.0,
                "odylith_requires_widening_rate": 0.0,
                "write_surface_backed_scenario_count": 0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "validation_backed_scenario_count": 1,
                "critical_required_path_backed_scenario_count": 1,
                "critical_validation_backed_scenario_count": 1,
                "expectation_success_rate": 1.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "within_budget_rate": 1.0,
                "write_surface_backed_scenario_count": 0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "required_path_precision_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 0.0,
            "median_prompt_token_delta": 0.0,
            "median_total_payload_token_delta": 0.0,
        },
        family_summaries={},
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
        runtime_posture={
            "memory_standardization_state": "standardized",
            "memory_backed_retrieval_ready": False,
            "remote_retrieval_status": "disabled",
        },
        execution_contracts={
            "odylith_on": {"model": "gpt-5.4", "reasoning_effort": "high"},
            "raw_agent_baseline": {"model": "gpt-5.4", "reasoning_effort": "high"},
        },
        comparison_contract="live_end_to_end",
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["memory_backed_retrieval_ready"] is False
    assert "Benchmark ran without an active local LanceDB/Tantivy retrieval substrate." in acceptance["notes"]
    assert "Vespa is optional and currently disabled; the current benchmark proof is local-first, not remote-assisted." in acceptance["notes"]


def test_live_acceptance_keeps_latency_and_token_deltas_diagnostic_for_live_proof() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
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
            "median_latency_delta_ms": 65000.0,
            "median_prompt_token_delta": 245000.0,
            "median_total_payload_token_delta": 247000.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "write_surface_backed_scenario_count": 0,
                    "odylith_requires_widening_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "write_surface_backed_scenario_count": 0,
                    "odylith_requires_widening_rate": 0.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
        comparison_contract="live_end_to_end",
    )

    assert acceptance["status"] == "provisional_pass"
    assert acceptance["secondary_guardrail_checks"]["latency_within_guardrail"] is True
    assert acceptance["secondary_guardrail_checks"]["prompt_delta_within_guardrail"] is True
    assert acceptance["secondary_guardrail_checks"]["total_payload_delta_within_guardrail"] is True
    assert acceptance["comparative_latency_and_token_status_blocking"] is False
    assert any("time to valid outcome" in note for note in acceptance["notes"])


def test_acceptance_flags_architecture_and_governance_packet_gaps() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 1.0,
                "odylith_requires_widening_rate": 0.1,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": -1.0,
            "median_prompt_token_delta": -10.0,
        },
        family_summaries={
            "architecture": {
                "odylith_on": {"median_latency_ms": 11.0},
                "raw_agent_baseline": {"median_latency_ms": 9.0},
            },
            "docs_code_closeout": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 0.5,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            },
            "explicit_workstream": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 0.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            },
            "governed_surface_sync": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            },
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["hard_quality_gate_cleared"] is False
    assert acceptance["secondary_guardrails_cleared"] is True
    assert acceptance["checks"]["architecture_not_slower"] is True
    assert acceptance["checks"]["governance_packet_coverage_complete"] is False
    assert acceptance["checks"]["explicit_workstream_expectation_positive"] is False
    assert "explicit_workstream" in acceptance["weak_families"]
    assert "docs_code_closeout" in acceptance["advisory_families"]


def test_acceptance_treats_new_governance_families_as_required_packet_coverage() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 1.0,
                "odylith_requires_widening_rate": 0.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": -1.0,
            "median_prompt_token_delta": -10.0,
        },
        family_summaries={
            "release_publication": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 0.5,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            },
            "explicit_workstream": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                    "odylith_requires_widening_rate": 0.0,
                    "odylith_packet_present_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            },
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
    )

    assert acceptance["status"] == "provisional_pass"
    assert acceptance["hard_quality_gate_cleared"] is True
    assert acceptance["checks"]["governance_packet_coverage_complete"] is False
    assert "release_publication" in acceptance["advisory_families"]


def test_acceptance_holds_when_live_benchmark_never_reaches_a_real_success() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_backed_scenario_count": 1,
                "critical_required_path_backed_scenario_count": 1,
                "critical_validation_backed_scenario_count": 1,
                "required_path_recall_rate": 0.0,
                "validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_backed_scenario_count": 1,
                "critical_required_path_backed_scenario_count": 1,
                "critical_validation_backed_scenario_count": 1,
                "required_path_recall_rate": 0.0,
                "validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.0,
            "required_path_precision_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": -1.0,
            "median_prompt_token_delta": 0.0,
            "median_total_payload_token_delta": 0.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "critical_required_path_recall_rate": 0.0,
                    "critical_validation_success_rate": 0.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "critical_required_path_recall_rate": 0.0,
                    "critical_validation_success_rate": 0.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["hard_quality_gate_cleared"] is False
    assert acceptance["checks"]["candidate_expectation_success_positive"] is False
    assert acceptance["checks"]["candidate_validation_success_positive"] is False
    assert acceptance["checks"]["candidate_critical_required_path_recall_positive"] is False
    assert acceptance["checks"]["candidate_critical_validation_success_positive"] is False
    assert "candidate_expectation_success_positive" in acceptance["hard_gate_failures"]
    assert "candidate_validation_success_positive" in acceptance["hard_gate_failures"]


def test_safe_orchestration_summary_fails_closed_on_router_contract_gap(
    monkeypatch,  # noqa: ANN001
    tmp_path: Path,
) -> None:
    def _raise_router_input_error(*args, **kwargs):  # noqa: ANN001,ARG001
        raise subagent_router.RouterInputError(
            code="invalid_orchestration_request",
            message="minimum contract missing",
            details=["candidate_paths are required when the prompt implies write orchestration"],
        )

    monkeypatch.setattr(runner.subagent_orchestrator, "orchestrate_prompt", _raise_router_input_error)

    summary = runner._safe_orchestration_summary(  # noqa: SLF001
        request_payload={
            "prompt": "Fix the router slice carefully.",
            "acceptance_criteria": ["Keep the slice grounded."],
            "candidate_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "task_kind": "implementation",
            "phase": "implementation",
            "needs_write": True,
        },
        repo_root=tmp_path,
        mode="odylith_on",
    )

    assert summary["mode"] == "local_only"
    assert summary["delegate"] is False
    assert summary["local_only_reasons"] == ["benchmark_orchestration_contract_gap"]
    assert summary["odylith_adoption"] == {}
    assert summary["error"]["error_code"] == "invalid_orchestration_request"


def test_safe_orchestration_summary_preserves_supplied_packet_adoption_on_router_contract_gap(
    monkeypatch,  # noqa: ANN001
    tmp_path: Path,
) -> None:
    def _raise_router_input_error(*args, **kwargs):  # noqa: ANN001,ARG001
        raise subagent_router.RouterInputError(
            code="invalid_orchestration_request",
            message="minimum contract missing",
            details=["candidate_paths are required when the prompt implies write orchestration"],
        )

    monkeypatch.setattr(runner.subagent_orchestrator, "orchestrate_prompt", _raise_router_input_error)

    summary = runner._safe_orchestration_summary(  # noqa: SLF001
        request_payload={
            "prompt": "Keep the benchmark governance slice grounded.",
            "acceptance_criteria": ["Stay grounded on the supplied packet."],
            "candidate_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "task_kind": "implementation",
            "phase": "implementation",
            "needs_write": True,
            "odylith_operation": "governance_slice",
            "context_packet": {
                "packet_kind": "governance_slice",
                "selection_state": "x:B-020",
                "packet_quality": {"routing_confidence": "high"},
                "route": {
                    "route_ready": True,
                    "native_spawn_ready": True,
                    "narrowing_required": False,
                },
            },
            "routing_handoff": {
                "route_ready": True,
                "native_spawn_ready": True,
                "routing_confidence": "high",
            },
            "evidence_cone_grounded": False,
        },
        repo_root=tmp_path,
        mode="odylith_on",
    )

    adoption = dict(summary["odylith_adoption"])
    assert adoption["packet_present"] is True
    assert adoption["grounding_source"] == "supplied_packet"
    assert adoption["operation"] == "governance_slice"
    assert adoption["packet_kind"] == "governance_slice"
    assert adoption["grounded"] is True
    assert adoption["route_ready"] is True
    assert adoption["native_spawn_ready"] is True
    assert adoption["requires_widening"] is False
    assert adoption["routing_confidence"] == "high"


def test_prime_benchmark_runtime_cache_warms_once(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    calls: list[tuple[Path, str, str]] = []
    primed: list[Path] = []
    guidance_primed: list[Path] = []
    judgment_primed: list[Path] = []
    git_branch_primed: list[Path] = []
    git_head_primed: list[Path] = []

    def _fake_warm_projections(*, repo_root: Path, reason: str, scope: str):  # noqa: ANN001
        calls.append((repo_root, reason, scope))
        return {"ok": True}

    monkeypatch.setattr(runner.store, "warm_projections", _fake_warm_projections)
    monkeypatch.setattr(
        runner.store,
        "prime_reasoning_projection_cache",
        lambda *, repo_root: primed.append(repo_root),
    )
    monkeypatch.setattr(
        runner.store,
        "projection_input_fingerprint",
        lambda *, repo_root, scope="default": f"{scope}-fingerprint",
    )
    monkeypatch.setattr(
        runner.store.tooling_guidance_catalog,
        "load_guidance_catalog",
        lambda *, repo_root: guidance_primed.append(repo_root)
        or {"chunk_count": 1, "source_doc_count": 1, "task_family_count": 1},
    )
    monkeypatch.setattr(
        runner.store,
        "_judgment_memory_snapshot_cached",
        lambda *, repo_root: judgment_primed.append(repo_root) or {},
    )
    monkeypatch.setattr(
        runner.store,
        "_git_branch_name",
        lambda *, repo_root: git_branch_primed.append(repo_root) or "main",
    )
    monkeypatch.setattr(
        runner.store,
        "_git_head_oid",
        lambda *, repo_root: git_head_primed.append(repo_root) or "abc123",
    )
    monkeypatch.setattr(
        runner.store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root: {
            "backend_transition": {
                "actual_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": True},
            },
            "entity_counts": {
                "indexed_entity_count": 12,
                "evidence_documents": 14,
            },
        },
    )
    monkeypatch.setattr(runner.store, "_PROCESS_WARM_CACHE", {})
    monkeypatch.setattr(runner.store, "_PROCESS_WARM_CACHE_FINGERPRINTS", {})

    runner._prime_benchmark_runtime_cache(repo_root=tmp_path)  # noqa: SLF001

    assert calls == [(tmp_path.resolve(), "benchmark", "full")]
    assert primed == [tmp_path.resolve()]
    assert guidance_primed == [tmp_path.resolve()]
    assert judgment_primed == [tmp_path.resolve()]
    assert git_branch_primed == [tmp_path.resolve()]
    assert git_head_primed == [tmp_path.resolve()]
    assert runner.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:full"] > 0  # noqa: SLF001
    assert runner.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:reasoning"] > 0  # noqa: SLF001
    assert runner.store._PROCESS_WARM_CACHE[f"{tmp_path.resolve()}:default"] > 0  # noqa: SLF001
    assert runner.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:full"] == "full-fingerprint"  # noqa: SLF001
    assert runner.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:reasoning"] == "reasoning-fingerprint"  # noqa: SLF001
    assert runner.store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{tmp_path.resolve()}:default"] == "default-fingerprint"  # noqa: SLF001


def test_prime_benchmark_runtime_cache_requires_active_local_memory_substrate(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner.store, "warm_projections", lambda **_: {"ok": True})
    monkeypatch.setattr(runner.store, "prime_reasoning_projection_cache", lambda **_: None)
    monkeypatch.setattr(
        runner.store.tooling_guidance_catalog,
        "load_guidance_catalog",
        lambda **_: {"chunk_count": 1, "source_doc_count": 1, "task_family_count": 1},
    )
    monkeypatch.setattr(runner.store, "_judgment_memory_snapshot_cached", lambda **_: {})
    monkeypatch.setattr(runner.store, "_git_branch_name", lambda **_: "main")
    monkeypatch.setattr(runner.store, "_git_head_oid", lambda **_: "abc123")
    monkeypatch.setattr(
        runner.store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root: {
            "backend_transition": {
                "actual_local_backend": {
                    "storage": "compiler_projection_snapshot",
                    "sparse_recall": "repo_scan_fallback",
                },
                "local_backend_status": {"ready": False},
            },
            "entity_counts": {
                "indexed_entity_count": 0,
                "evidence_documents": 0,
            },
        },
    )

    with pytest.raises(RuntimeError, match="active local LanceDB/Tantivy memory substrate"):
        runner._prime_benchmark_runtime_cache(repo_root=tmp_path)  # noqa: SLF001


def test_runtime_posture_summary_reports_memory_and_remote_posture(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(runner.store, "load_runtime_optimization_snapshot", lambda *, repo_root: {"quality_posture": {"route_ready_rate": 0.8, "native_spawn_ready_rate": 0.6}})
    monkeypatch.setattr(runner.store, "load_runtime_evaluation_snapshot", lambda *, repo_root: {"architecture": {"covered_case_count": 4, "satisfied_case_count": 3, "coverage_rate": 1.0, "satisfaction_rate": 0.75}})
    monkeypatch.setattr(
        runner.store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot=None, evaluation_snapshot=None: {
            "backend_transition": {
                "status": "standardized",
                "actual_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": True},
                "signature": {"projection_scope": "full"},
            },
            "repo_scan_degraded_fallback": {"repo_scan_degraded_fallback_rate": 0.02},
            "governance_runtime_first": {"usage_rate": 1.0, "fallback_rate": 0.0},
            "entity_counts": {"indexed_entity_count": 120, "evidence_documents": 145},
            "remote_retrieval": {
                "enabled": False,
                "configured": False,
                "mode": "disabled",
                "provider": "vespa_http",
                "status": "disabled",
            },
        },
    )

    posture = runner._runtime_posture_summary(repo_root=tmp_path)  # noqa: SLF001

    assert posture["memory_backed_retrieval_ready"] is True
    assert posture["memory_local_backend_ready"] is True
    assert posture["memory_projection_scope"] == "full"
    assert posture["memory_indexed_entity_count"] == 120
    assert posture["memory_evidence_document_count"] == 145
    assert posture["remote_retrieval_status"] == "disabled"
    assert posture["remote_retrieval_mode"] == "disabled"
    assert posture["remote_retrieval_enabled"] is False


def test_runtime_posture_summary_prefers_managed_runtime_when_host_python_lacks_memory_backend(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(runner.store, "load_runtime_optimization_snapshot", lambda *, repo_root: {"quality_posture": {}})
    monkeypatch.setattr(runner.store, "load_runtime_evaluation_snapshot", lambda *, repo_root: {"architecture": {}})
    monkeypatch.setattr(
        runner.store,
        "load_runtime_memory_snapshot",
        lambda *, repo_root, optimization_snapshot=None, evaluation_snapshot=None: {
            "backend_transition": {
                "status": "pending_target_swap",
                "actual_local_backend": {
                    "storage": "compiler_projection_snapshot",
                    "sparse_recall": "repo_scan_fallback",
                },
                "target_local_backend": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "local_backend_status": {"ready": False},
                "signature": {"projection_scope": "reasoning"},
            },
            "entity_counts": {"indexed_entity_count": 120, "evidence_documents": 145},
        },
    )
    managed_posture = {
        "memory_standardization_state": "standardized",
        "memory_backend_actual": {
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
        },
        "memory_backend_target": {
            "storage": "lance_local_columnar",
            "sparse_recall": "tantivy_sparse_recall",
        },
        "memory_backed_retrieval_ready": True,
        "memory_local_backend_ready": True,
        "memory_projection_scope": "reasoning",
        "memory_indexed_entity_count": 120,
        "memory_evidence_document_count": 145,
        "remote_retrieval_enabled": False,
        "remote_retrieval_configured": False,
        "remote_retrieval_mode": "disabled",
        "remote_retrieval_provider": "vespa_http",
        "remote_retrieval_status": "disabled",
        "repo_scan_degraded_fallback_rate": 0.0,
        "repo_scan_degraded_reason_distribution": {},
        "governance_runtime_first_usage_rate": 1.0,
        "governance_runtime_first_fallback_rate": 0.0,
        "governance_runtime_first_fallback_reason_distribution": {},
        "route_ready_rate": 1.0,
        "native_spawn_ready_rate": 1.0,
        "architecture_covered_case_count": 0,
        "architecture_satisfied_case_count": 0,
        "architecture_coverage_rate": 0.0,
        "architecture_satisfaction_rate": 0.0,
    }
    monkeypatch.setattr(runner, "_managed_runtime_posture_summary", lambda *, repo_root: dict(managed_posture))

    posture = runner._runtime_posture_summary(repo_root=tmp_path)  # noqa: SLF001

    assert posture["memory_backed_retrieval_ready"] is True
    assert posture["memory_local_backend_ready"] is True
    assert posture["memory_backend_actual"] == managed_posture["memory_backend_actual"]


def test_run_benchmarks_records_cache_profile_summaries_without_overwriting_latest(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]
    prep_calls: list[str] = []

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(
        runner.odylith_context_cache,
        "read_json_object",
        lambda path: {"version": "v1", "scenarios": list(scenarios), "architecture_scenarios": []}
        if str(path).endswith("optimization-evaluation-corpus.v1.json")
        else {},
    )
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(
        runner,
        "_prepare_benchmark_runtime_cache",
        lambda *, repo_root, cache_profile: prep_calls.append(str(cache_profile)),
    )
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **kwargs: {
            "kind": "packet",
            "mode": kwargs["mode"],
            "latency_ms": 10.0 if kwargs["mode"] not in {"odylith_repo_scan_baseline", "raw_agent_baseline"} else 12.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
            "timing_trace": {"operations": {}},
        },
    )

    latest_path = runner.latest_report_path(repo_root=tmp_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps({"report_id": "existing"}) + "\n", encoding="utf-8")

    report = runner.run_benchmarks(repo_root=tmp_path, cache_profiles=("cold",))

    assert report["primary_cache_profile"] == "cold"
    assert report["cache_profiles"] == ["cold"]
    assert report["latest_eligible"] is False
    assert set(report["cache_profile_scenarios"]) == {"cold"}
    assert set(report["cache_profile_summaries"]) == {"cold"}
    assert all(row["cache_profile"] == "cold" for row in report["scenarios"])
    assert prep_calls.count("warm") == 0
    assert prep_calls.count("cold") == 1
    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    profile_latest_payload = json.loads(
        runner.latest_report_path(repo_root=tmp_path, benchmark_profile="proof").read_text(encoding="utf-8")
    )
    assert latest_payload["report_id"] == "existing"
    assert profile_latest_payload["benchmark_profile"] == "proof"


def test_run_benchmarks_publishes_conservative_multi_profile_view(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]
    current_profile = {"value": "warm"}

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(
        runner,
        "_prepare_benchmark_runtime_cache",
        lambda *, repo_root, cache_profile: current_profile.__setitem__("value", str(cache_profile)),
    )

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        del repo_root, scenario, benchmark_profile
        profile = current_profile["value"]
        if mode in {"odylith_repo_scan_baseline", "raw_agent_baseline"}:
            prompt = 300.0 if profile == "warm" else 280.0
            latency = 40.0 if profile == "warm" else 38.0
            validation = 0.0
        else:
            prompt = 100.0 if profile == "warm" else 150.0
            latency = 20.0 if profile == "warm" else 27.0
            validation = 1.0
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": latency,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": prompt,
            "codex_prompt_estimated_tokens": prompt,
            "total_payload_estimated_tokens": prompt,
            "validation_success_proxy": validation,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
            "timing_trace": {"operations": {}},
        }

    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        modes=(
            "odylith_on",
            "odylith_on_no_fanout",
            "odylith_repo_scan_baseline",
            "raw_agent_baseline",
        ),
        cache_profiles=("warm", "cold"),
    )
    summary = runner.compact_report_summary(report)

    assert report["published_view_strategy"] == "conservative_multi_profile"
    assert report["published_cache_profiles"] == ["warm", "cold"]
    assert report["primary_comparison"]["median_prompt_token_delta"] == -200.0
    assert report["published_comparison"]["median_prompt_token_delta"] == -130.0
    assert report["published_comparison"]["median_latency_delta_ms"] == -11.0
    assert report["comparison"]["median_prompt_token_delta"] == -130.0
    published_results = {
        row["mode"]: row
        for row in report["published_scenarios"][0]["results"]
    }
    assert published_results["odylith_on"]["codex_prompt_estimated_tokens"] == 150.0
    assert published_results["raw_agent_baseline"]["codex_prompt_estimated_tokens"] == 280.0
    assert report["published_mode_summaries"]["odylith_on"]["median_effective_tokens"] == 150.0
    assert report["published_mode_summaries"]["raw_agent_baseline"]["median_effective_tokens"] == 280.0
    assert report["published_mode_table"]["mode_order"] == [
        "odylith_on",
        "odylith_off",
    ]
    assert report["published_mode_table"]["display_mode_order"] == [
        "odylith_on",
        "odylith_off",
    ]
    assert report["published_mode_table"]["delta_header"] == "Delta"
    assert report["published_mode_table"]["why_it_matters_header"] == "Why It Matters"
    assert "Median time to valid outcome" in report["published_mode_table_markdown"]
    assert "Mean time to valid outcome" in report["published_mode_table_markdown"]
    assert "P95 time to valid outcome" in report["published_mode_table_markdown"]
    assert "Median live session input tokens" in report["published_mode_table_markdown"]
    assert report["tracked_mode_table"]["mode_order"] == [
        "odylith_on",
        "odylith_on_no_fanout",
        "odylith_repo_scan_baseline",
        "odylith_off",
    ]
    assert report["tracked_mode_table"]["display_mode_order"] == [
        "odylith_on",
        "odylith_on_no_fanout",
        "odylith_repo_scan_baseline",
        "odylith_off",
    ]
    assert "odylith_repo_scan_baseline" not in report["published_mode_table_markdown"]
    assert "odylith_on_no_fanout" not in report["published_mode_table_markdown"]
    assert "Delta" in report["published_mode_table_markdown"]
    assert "Why It Matters" in report["published_mode_table_markdown"]
    assert '<strong style="color:#137333;">' in report["published_mode_table_markdown"]
    assert "odylith_repo_scan_baseline" in report["tracked_mode_table_markdown"]
    assert report["published_summary"]["prompt_token_delta"] == -130.0
    assert report["published_summary"]["full_pair_total_wall_clock_ms"] == 78.0
    assert report["robustness_summary"]["warm_cold_consistency_cleared"] is True
    assert summary["prompt_token_delta"] == -130.0
    assert summary["avg_latency_delta_ms"] == -11.0
    assert summary["p95_latency_delta_ms"] == -11.0
    assert summary["full_pair_total_wall_clock_ms"] == 78.0
    assert summary["published_view_strategy"] == "conservative_multi_profile"
    assert summary["published_cache_profiles"] == ["warm", "cold"]


def test_format_mode_table_delta_colors_good_and_bad_moves() -> None:
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="required_path_recall_rate",
        candidate_value=1.0,
        baseline_value=0.0,
    ) == '<strong style="color:#137333;">+1.000</strong>'
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="median_latency_ms",
        candidate_value=12.0,
        baseline_value=2.0,
    ) == '<span style="color:#c5221f;">+10.000 ms</span>'
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="hallucinated_surface_rate",
        candidate_value=0.0,
        baseline_value=0.0,
    ) == "+0.000"


def test_format_mode_table_value_humanizes_live_proof_time_and_tokens() -> None:
    assert runner._format_mode_table_value(  # noqa: SLF001
        field="median_latency_ms",
        value=183775.954,
        comparison_contract="live_end_to_end",
    ) == "3m 04s"
    assert runner._format_mode_table_value(  # noqa: SLF001
        field="median_uninstrumented_overhead_ms",
        value=2347.282,
        comparison_contract="live_end_to_end",
    ) == "2.35s"
    assert runner._format_mode_table_value(  # noqa: SLF001
        field="median_effective_tokens",
        value=584130.0,
        comparison_contract="live_end_to_end",
    ) == "584,130"


def test_format_mode_table_delta_humanizes_live_proof_time_and_tokens() -> None:
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="median_latency_ms",
        candidate_value=183775.954,
        baseline_value=118563.605,
        comparison_contract="live_end_to_end",
    ) == '<span style="color:#c5221f;">+1m 05s</span>'
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="median_uninstrumented_overhead_ms",
        candidate_value=2347.282,
        baseline_value=2404.320,
        comparison_contract="live_end_to_end",
    ) == '<strong style="color:#137333;">-57 ms</strong>'
    assert runner._format_mode_table_delta(  # noqa: SLF001
        field="median_effective_tokens",
        candidate_value=584130.0,
        baseline_value=338748.0,
        comparison_contract="live_end_to_end",
    ) == '<span style="color:#c5221f;">+245,382</span>'


def test_published_mode_table_uses_diagnostic_labels_for_diagnostic_contract() -> None:
    table = runner._published_mode_table(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "scenario_count": 1,
                "median_latency_ms": 11.0,
                "avg_latency_ms": 13.0,
                "p95_latency_ms": 17.0,
                "median_instrumented_reasoning_duration_ms": 7.0,
                "median_uninstrumented_overhead_ms": 1.0,
                "median_effective_tokens": 120.0,
                "median_total_payload_tokens": 140.0,
                "required_path_recall_rate": 1.0,
                "required_path_precision_rate": 1.0,
                "hallucinated_surface_rate": 0.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "scenario_count": 1,
                "median_latency_ms": 9.0,
                "avg_latency_ms": 10.0,
                "p95_latency_ms": 13.0,
                "median_instrumented_reasoning_duration_ms": 5.0,
                "median_uninstrumented_overhead_ms": 1.0,
                "median_effective_tokens": 200.0,
                "median_total_payload_tokens": 240.0,
                "required_path_recall_rate": 0.0,
                "required_path_precision_rate": 0.0,
                "hallucinated_surface_rate": 1.0,
                "validation_success_rate": 0.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
            },
        },
        mode_order=("odylith_on", "raw_agent_baseline"),
        candidate_mode="odylith_on",
        baseline_mode="raw_agent_baseline",
        comparison_contract="internal_packet_prompt_diagnostic",
    )

    labels = [row["label"] for row in table["rows"]]
    assert "Median packet time" in labels
    assert "Mean packet time" in labels
    assert "P95 packet time" in labels
    assert "Median prompt-bundle input tokens" in labels
    assert "Median total prompt-bundle payload tokens" in labels


def test_acceptance_requires_all_selected_cache_profiles_to_clear_gate() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 1.0,
                "odylith_requires_widening_rate": 0.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 1.0,
            "validation_success_delta": 1.0,
            "critical_required_path_recall_delta": 1.0,
            "critical_validation_success_delta": 1.0,
            "expectation_success_delta": 1.0,
            "median_latency_delta_ms": -5.0,
            "median_prompt_token_delta": -25.0,
            "median_total_payload_token_delta": -25.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
        cache_profile_summaries={
            "warm": {"acceptance": {"status": "provisional_pass"}},
            "cold": {"acceptance": {"status": "hold"}},
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["selected_cache_profiles_clear_gate"] is False
    assert "Selected cache profiles still failing the hard quality gate: cold." in acceptance["notes"]


def test_acceptance_allows_secondary_tradeoffs_within_guardrails() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 0.9,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 1.0,
            "required_path_precision_delta": 1.0,
            "hallucinated_surface_rate_delta": -0.1,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 1.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 10.0,
            "median_prompt_token_delta": 40.0,
            "median_total_payload_token_delta": 60.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.1,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "provisional_pass"
    assert acceptance["hard_quality_gate_cleared"] is True
    assert acceptance["secondary_guardrails_cleared"] is True
    assert acceptance["checks"]["latency_within_guardrail"] is True
    assert acceptance["checks"]["prompt_delta_within_guardrail"] is True
    assert acceptance["checks"]["total_payload_delta_within_guardrail"] is True


def test_acceptance_tracks_bootstrap_payload_guardrail() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 0.9,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 1.0,
            "required_path_precision_delta": 1.0,
            "hallucinated_surface_rate_delta": -0.1,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 1.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 0.0,
            "median_prompt_token_delta": 0.0,
            "median_total_payload_token_delta": 0.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.1,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            }
        },
        packet_source_summaries={
            "bootstrap_session": {
                "odylith_on": {
                    "median_total_payload_tokens": 220.0,
                    "scenario_count": 2,
                },
                "raw_agent_baseline": {
                    "median_total_payload_tokens": 80.0,
                    "scenario_count": 2,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["checks"]["bootstrap_payload_delta_within_guardrail"] is False
    assert "bootstrap_payload_delta_within_guardrail" in acceptance["secondary_guardrail_failures"]


def test_acceptance_holds_when_secondary_guardrails_breach_thresholds() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "packet_scenario_count": 1,
                "within_budget_rate": 0.7,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "packet_scenario_count": 1,
                "within_budget_rate": 1.0,
                "validation_success_rate": 1.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 1.0,
            "required_path_precision_delta": 1.0,
            "hallucinated_surface_rate_delta": -0.1,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 1.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 0.0,
            "median_latency_delta_ms": 16.0,
            "median_prompt_token_delta": 80.0,
            "median_total_payload_token_delta": 120.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.1,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "hold"
    assert acceptance["hard_quality_gate_cleared"] is True
    assert acceptance["secondary_guardrails_cleared"] is False
    assert "latency_within_guardrail" in acceptance["secondary_guardrail_failures"]
    assert "prompt_delta_within_guardrail" in acceptance["secondary_guardrail_failures"]
    assert "tight_budget_behavior_healthy" in acceptance["secondary_guardrail_failures"]


def test_acceptance_skips_relative_efficiency_guardrails_when_baseline_has_no_successful_outcomes() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "within_budget_rate": 0.9,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 1.0,
                "critical_validation_success_rate": 1.0,
            },
            "raw_agent_baseline": {
                "within_budget_rate": 1.0,
                "validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 1.0,
            "required_path_precision_delta": 1.0,
            "hallucinated_surface_rate_delta": -0.1,
            "validation_success_delta": 1.0,
            "critical_required_path_recall_delta": 1.0,
            "critical_validation_success_delta": 1.0,
            "expectation_success_delta": 1.0,
            "median_latency_delta_ms": 160.0,
            "median_prompt_token_delta": 800.0,
            "median_total_payload_token_delta": 1200.0,
        },
        family_summaries={
            "validation_heavy_fix": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 1.0,
                    "expectation_success_rate": 1.0,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.0,
                    "required_path_precision_rate": 0.0,
                    "hallucinated_surface_rate": 0.1,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 1,
            "critical_required_path_backed_scenario_count": 1,
            "critical_validation_backed_scenario_count": 1,
        },
    )

    assert acceptance["status"] == "provisional_pass"
    assert acceptance["hard_quality_gate_cleared"] is True
    assert acceptance["comparative_efficiency_guardrails_applicable"] is False
    assert acceptance["comparative_efficiency_guardrail_reason"] == "baseline_has_no_successful_outcomes"
    assert acceptance["checks"]["latency_within_guardrail"] is True
    assert acceptance["checks"]["prompt_delta_within_guardrail"] is True
    assert acceptance["checks"]["total_payload_delta_within_guardrail"] is True
    assert "Relative latency and token-efficiency guardrails were not applied because `odylith_off` produced no successful outcomes on the sampled corpus." in acceptance["notes"]


def test_acceptance_skips_packet_budget_guardrail_for_architecture_only_samples() -> None:
    acceptance = runner._acceptance(  # noqa: SLF001
        mode_summaries={
            "odylith_on": {
                "packet_scenario_count": 0,
                "architecture_scenario_count": 1,
                "within_budget_rate": 0.0,
                "validation_success_rate": 1.0,
                "expectation_success_rate": 1.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
            },
            "raw_agent_baseline": {
                "packet_scenario_count": 0,
                "architecture_scenario_count": 1,
                "within_budget_rate": 0.0,
                "validation_success_rate": 0.0,
                "expectation_success_rate": 0.0,
                "critical_required_path_recall_rate": 0.0,
                "critical_validation_success_rate": 0.0,
            },
        },
        primary_comparison={
            "required_path_recall_delta": 0.6,
            "required_path_precision_delta": 0.0,
            "hallucinated_surface_rate_delta": 0.0,
            "validation_success_delta": 0.0,
            "critical_required_path_recall_delta": 0.0,
            "critical_validation_success_delta": 0.0,
            "expectation_success_delta": 1.0,
            "median_latency_delta_ms": 20.0,
            "median_prompt_token_delta": 120.0,
            "median_total_payload_token_delta": 140.0,
        },
        family_summaries={
            "architecture": {
                "odylith_on": {
                    "required_path_recall_rate": 1.0,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 1.0,
                    "scenario_count": 1,
                },
                "raw_agent_baseline": {
                    "required_path_recall_rate": 0.4,
                    "required_path_precision_rate": 1.0,
                    "hallucinated_surface_rate": 0.0,
                    "validation_success_rate": 0.0,
                    "expectation_success_rate": 0.0,
                    "scenario_count": 1,
                },
            }
        },
        corpus_summary={
            "correctness_critical_scenario_count": 0,
            "critical_required_path_backed_scenario_count": 0,
            "critical_validation_backed_scenario_count": 0,
        },
        comparison_contract="live_end_to_end",
    )

    assert acceptance["status"] == "provisional_pass"
    assert acceptance["hard_quality_gate_cleared"] is True
    assert acceptance["secondary_guardrails_cleared"] is True
    assert acceptance["packet_budget_guardrail_applicable"] is False
    assert acceptance["checks"]["tight_budget_behavior_healthy"] is True
    assert "Tighter-budget behavior was not applied because the sampled corpus contains no packet-backed scenarios." in acceptance["notes"]


def test_robustness_summary_uses_hard_quality_gate_for_profile_consistency() -> None:
    robustness = runner._robustness_summary(  # noqa: SLF001
        cache_profile_summaries={
            "warm": {
                "acceptance": {
                    "status": "hold",
                    "hard_quality_gate_cleared": True,
                    "secondary_guardrails_cleared": False,
                },
                "mode_summaries": {
                    "odylith_on": {
                        "median_latency_ms": 10.0,
                        "median_effective_tokens": 120.0,
                        "required_path_recall_rate": 1.0,
                        "required_path_precision_rate": 1.0,
                        "validation_success_rate": 1.0,
                        "expectation_success_rate": 1.0,
                        "write_surface_precision_rate": 1.0,
                        "unnecessary_widening_rate": 0.0,
                        "hallucinated_surface_rate": 0.0,
                    }
                },
            },
            "cold": {
                "acceptance": {
                    "status": "hold",
                    "hard_quality_gate_cleared": True,
                    "secondary_guardrails_cleared": False,
                },
                "mode_summaries": {
                    "odylith_on": {
                        "median_latency_ms": 12.0,
                        "median_effective_tokens": 128.0,
                        "required_path_recall_rate": 1.0,
                        "required_path_precision_rate": 1.0,
                        "validation_success_rate": 1.0,
                        "expectation_success_rate": 1.0,
                        "write_surface_precision_rate": 1.0,
                        "unnecessary_widening_rate": 0.0,
                        "hallucinated_surface_rate": 0.0,
                    }
                },
            },
        },
        candidate_mode="odylith_on",
        latency_probes={},
    )

    assert robustness["selected_cache_profile_pass_rate"] == 1.0
    assert robustness["warm_cold_consistency_cleared"] is True


def test_run_benchmarks_keeps_partial_sample_out_of_latest_report(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "cross_file_feature",
            "priority": "medium",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **_: {
            "kind": "packet",
            "mode": "odylith_on",
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    latest_path = runner.latest_report_path(repo_root=tmp_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(json.dumps({"report_id": "existing", "scenario_count": 99}) + "\n", encoding="utf-8")

    report = runner.run_benchmarks(repo_root=tmp_path, limit=1)

    latest_payload = json.loads(latest_path.read_text(encoding="utf-8"))
    profile_latest_payload = json.loads(
        runner.latest_report_path(repo_root=tmp_path, benchmark_profile="proof").read_text(encoding="utf-8")
    )
    assert report["latest_eligible"] is False
    assert latest_payload["report_id"] == "existing"
    assert profile_latest_payload["report_id"] == report["report_id"]
    assert runner.history_report_path(repo_root=tmp_path, report_id=report["report_id"]).is_file()


def test_profile_latest_report_path_uses_profile_specific_snapshot_names(tmp_path: Path) -> None:
    assert runner.latest_report_path(repo_root=tmp_path) == (
        tmp_path / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json"
    ).resolve()
    assert runner.latest_report_path(repo_root=tmp_path, benchmark_profile="proof") == (
        tmp_path / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-proof.v1.json"
    ).resolve()
    assert runner.latest_report_path(repo_root=tmp_path, benchmark_profile="diagnostic") == (
        tmp_path / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-diagnostic.v1.json"
    ).resolve()


def test_load_latest_benchmark_report_falls_back_to_canonical_proof_snapshot(tmp_path: Path) -> None:
    latest_path = runner.latest_report_path(repo_root=tmp_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps({"report_id": "proof-canonical", "benchmark_profile": "proof"}) + "\n",
        encoding="utf-8",
    )

    report = runner.load_latest_benchmark_report(repo_root=tmp_path, benchmark_profile="proof")

    assert report["report_id"] == "proof-canonical"


def test_run_benchmarks_writes_and_clears_progress_checkpoint(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]
    seen_progress: list[dict[str, object]] = []

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        del benchmark_profile
        progress = runner.load_benchmark_progress(repo_root=repo_root)
        seen_progress.append(
            {
                "status": progress.get("status"),
                "current_scenario_id": progress.get("current_scenario_id"),
                "current_mode": progress.get("current_mode"),
            }
        )
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        }

    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)

    report = runner.run_benchmarks(repo_root=tmp_path)

    assert report["modes"] == ["odylith_on", "raw_agent_baseline"]
    assert report["latest_eligible"] is True
    assert report["comparison_contract"] == runner.LIVE_COMPARISON_CONTRACT
    assert seen_progress
    assert all(row["status"] == "running" for row in seen_progress)
    assert runner.progress_report_path(repo_root=tmp_path).exists() is False


def test_run_benchmarks_shards_do_not_touch_shared_progress_or_profile_latest(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-c",
            "kind": "packet",
            "label": "Case C",
            "summary": "C",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/c.py"],
            "workstream": "",
            "required_paths": ["scripts/c.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-d",
            "kind": "packet",
            "label": "Case D",
            "summary": "D",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/d.py"],
            "workstream": "",
            "required_paths": ["scripts/d.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]
    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **_: {
            "kind": "packet",
            "mode": "odylith_on",
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    progress_path = runner.progress_report_path(repo_root=tmp_path)
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(
        json.dumps({"report_id": "shared-progress", "status": "running"}) + "\n",
        encoding="utf-8",
    )
    profile_latest_path = runner.latest_report_path(repo_root=tmp_path, benchmark_profile="proof")
    profile_latest_path.parent.mkdir(parents=True, exist_ok=True)
    profile_latest_path.write_text(
        json.dumps({"report_id": "existing-proof", "benchmark_profile": "proof"}) + "\n",
        encoding="utf-8",
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        shard_count=4,
        shard_index=2,
    )

    profile_latest_payload = json.loads(profile_latest_path.read_text(encoding="utf-8"))
    assert report["latest_eligible"] is False
    assert not progress_path.exists()
    assert profile_latest_payload["report_id"] == "existing-proof"
    assert runner.history_report_path(repo_root=tmp_path, report_id=report["report_id"]).is_file()


def test_run_benchmarks_shards_use_shard_specific_lock_key(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-c",
            "kind": "packet",
            "label": "Case C",
            "summary": "C",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/c.py"],
            "workstream": "",
            "required_paths": ["scripts/c.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]
    seen_lock_keys: list[str] = []

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda *, repo_root, scenarios: {"sample_size": 1})
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **_: {
            "kind": "packet",
            "mode": "odylith_on",
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    @contextlib.contextmanager
    def _fake_lock(*, repo_root: Path, key: str):
        del repo_root
        seen_lock_keys.append(key)
        yield

    monkeypatch.setattr(runner.odylith_context_cache, "advisory_lock", _fake_lock)

    runner.run_benchmarks(repo_root=tmp_path, shard_count=3, shard_index=2, write_report=False)

    assert seen_lock_keys[0] == "odylith-benchmark-runner:proof:2-of-3"
    assert seen_lock_keys.count("odylith-benchmark-runner:proof:2-of-3") == 1


def test_run_benchmarks_shards_persist_failed_history_report_on_exception(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(runner, "_benchmark_report_id", lambda **_: "failed-shard")
    monkeypatch.setattr(runner, "_utc_now", lambda: "2026-04-13T12:00:00Z")
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **_: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        runner.run_benchmarks(
            repo_root=tmp_path,
            shard_count=2,
            shard_index=1,
        )

    payload = json.loads(
        runner.history_report_path(repo_root=tmp_path, report_id="failed-shard").read_text(encoding="utf-8")
    )
    assert payload["status"] == "failed"
    assert payload["acceptance"]["status"] == "failed"
    assert payload["published_summary"]["status"] == "failed"


def test_run_benchmarks_shards_persist_failed_history_report_on_keyboard_interrupt(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(runner, "_benchmark_report_id", lambda **_: "failed-shard-interrupt")
    monkeypatch.setattr(runner, "_utc_now", lambda: "2026-04-13T12:00:00Z")
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **_: (_ for _ in ()).throw(KeyboardInterrupt()),
    )

    with pytest.raises(KeyboardInterrupt):
        runner.run_benchmarks(
            repo_root=tmp_path,
            shard_count=2,
            shard_index=1,
        )

    payload = json.loads(
        runner.history_report_path(repo_root=tmp_path, report_id="failed-shard-interrupt").read_text(encoding="utf-8")
    )
    assert payload["status"] == "failed"
    assert payload["acceptance"]["status"] == "failed"
    assert payload["published_summary"]["status"] == "failed"


def test_benchmark_interrupt_guard_raises_custom_interrupt_and_restores_handlers(monkeypatch) -> None:  # noqa: ANN001
    sighup = getattr(signal, "SIGHUP", None)
    previous_handlers = {
        signal.SIGTERM: object(),
        signal.SIGINT: object(),
    }
    if sighup is not None:
        previous_handlers[sighup] = object()
    installed: dict[int, object] = {}
    calls: list[tuple[str, int, object]] = []

    class _Process:
        name = "MainProcess"

    monkeypatch.setattr(runner.multiprocessing, "current_process", lambda: _Process())

    def _fake_getsignal(signum: int):  # noqa: ANN001
        return previous_handlers[signum]

    def _fake_signal(signum: int, handler):  # noqa: ANN001
        calls.append(("set", signum, handler))
        installed[signum] = handler
        return previous_handlers[signum]

    monkeypatch.setattr(runner.signal, "getsignal", _fake_getsignal)
    monkeypatch.setattr(runner.signal, "signal", _fake_signal)

    with pytest.raises(runner.BenchmarkRunInterrupted, match="received SIGTERM"):
        with runner._benchmark_interrupt_guard():  # noqa: SLF001
            if sighup is not None:
                assert installed[sighup] == signal.SIG_IGN
            installed[signal.SIGTERM](signal.SIGTERM, None)

    restored = [row for row in calls if row[2] in previous_handlers.values()]
    assert restored


def test_run_benchmarks_shards_skip_merge_only_post_run_metrics(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(runner, "_singleton_family_latency_probes", lambda **_: (_ for _ in ()).throw(AssertionError("skip latency probes")))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda **_: (_ for _ in ()).throw(AssertionError("skip adoption proof")))
    monkeypatch.setattr(runner, "_runtime_posture_summary", lambda **_: (_ for _ in ()).throw(AssertionError("skip runtime posture")))
    monkeypatch.setattr(runner, "_robustness_summary", lambda **_: (_ for _ in ()).throw(AssertionError("skip robustness")))
    monkeypatch.setattr(
        runner,
        "_benchmark_runtime_hygiene_snapshot",
        lambda **_: (_ for _ in ()).throw(AssertionError("skip final hygiene")),
    )
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **kwargs: {
            "kind": "packet",
            "mode": kwargs["mode"],
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": [kwargs["scenario"]["required_paths"][0]],
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 10,
            "total_payload_estimated_tokens": 10,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        shard_count=2,
        shard_index=1,
        write_report=False,
    )

    assert report["selection"]["shard_count"] == 2
    assert report["adoption_proof"] == {}
    assert report["runtime_posture"] == {}
    assert report["robustness_summary"] == {}
    assert report["final_hygiene"] == {}


def test_run_benchmarks_manual_selection_skips_extra_post_run_probe_fanout(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    _write_corpus(
        tmp_path,
        {
            "version": "v1",
            "program": {},
            "scenarios": [
                {
                    "case_id": "case-a",
                    "label": "Case A",
                    "family": "validation_heavy_fix",
                    "priority": "high",
                    "benchmark": {
                        "paths": ["scripts/a.py"],
                        "required_paths": ["scripts/a.py"],
                        "needs_write": True,
                    },
                    "expect": {"within_budget": True},
                }
            ],
            "architecture_scenarios": [],
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(runner, "_singleton_family_latency_probes", lambda **_: (_ for _ in ()).throw(AssertionError("skip latency probes")))
    monkeypatch.setattr(runner, "_run_live_adoption_proof", lambda **_: (_ for _ in ()).throw(AssertionError("skip adoption proof")))
    monkeypatch.setattr(runner, "_runtime_posture_summary", lambda **_: {"route_ready_rate": 1.0, "native_spawn_ready_rate": 1.0})
    monkeypatch.setattr(runner, "_robustness_summary", lambda **_: {})
    monkeypatch.setattr(
        runner,
        "_benchmark_runtime_hygiene_snapshot",
        lambda **_: {
            "owned_codex_process_count": 0,
            "temp_worktree_count": 0,
            "temp_directory_count": 0,
            "active_run_count": 0,
        },
    )
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **kwargs: {
            "kind": "packet",
            "mode": kwargs["mode"],
            "packet_source": "impact",
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 1,
            "candidate_write_path_count": 1,
            "candidate_write_paths": ["scripts/a.py"],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 10,
            "total_payload_estimated_tokens": 10,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        benchmark_profile=runner.BENCHMARK_PROFILE_DIAGNOSTIC,
        case_ids=["case-a"],
        write_report=False,
    )

    assert report["selection_strategy"] == "manual_selection"
    assert report["singleton_family_latency_probes"] == {}
    assert report["adoption_proof"] == {}


def test_run_benchmarks_shards_skip_live_batch_pairing(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
        {
            "scenario_id": "case-b",
            "kind": "packet",
            "label": "Case B",
            "summary": "B",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/b.py"],
            "workstream": "",
            "required_paths": ["scripts/b.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        },
    ]

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(
        runner,
        "_run_live_scenario_batch",
        lambda **_: (_ for _ in ()).throw(AssertionError("shards should not use live batch pairing")),
    )
    monkeypatch.setattr(
        runner,
        "_run_scenario_mode",
        lambda **kwargs: {
            "kind": "packet",
            "mode": kwargs["mode"],
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": [kwargs["scenario"]["required_paths"][0]],
            "observed_path_count": 1,
            "required_path_precision": 1.0,
            "hallucinated_surface_count": 0,
            "hallucinated_surface_rate": 0.0,
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "effective_estimated_tokens": 10,
            "total_payload_estimated_tokens": 10,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        },
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        shard_count=2,
        shard_index=1,
        write_report=False,
    )

    assert report["selection"]["shard_count"] == 2
    assert [row["scenario_id"] for row in report["scenarios"]] == ["case-a"]


def test_diagnostic_profile_keeps_public_pair_packet_only(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = [
        {
            "scenario_id": "case-a",
            "kind": "packet",
            "label": "Case A",
            "summary": "A",
            "family": "validation_heavy_fix",
            "priority": "high",
            "changed_paths": ["scripts/a.py"],
            "workstream": "",
            "required_paths": ["scripts/a.py"],
            "validation_commands": [],
            "correctness_critical": False,
            "expect": {"within_budget": True},
        }
    ]
    packet_calls: list[str] = []
    adoption_proof_calls: list[int] = []

    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: list(scenarios))
    monkeypatch.setattr(
        runner,
        "_run_live_adoption_proof",
        lambda *, repo_root, scenarios: adoption_proof_calls.append(len(list(scenarios))) or {"sample_size": 0},
    )
    monkeypatch.setattr(
        runner,
        "_runtime_posture_summary",
        lambda *, repo_root: {
            "memory_standardization_state": "standardized",
            "repo_scan_degraded_fallback_rate": 0.0,
            "governance_runtime_first_usage_rate": 1.0,
            "route_ready_rate": 1.0,
            "native_spawn_ready_rate": 1.0,
            "architecture_covered_case_count": 0,
            "architecture_satisfied_case_count": 0,
        },
    )
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda **_: None)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [])

    def _fake_packet_result(*, repo_root: Path, scenario: dict[str, object], mode: str) -> dict[str, object]:
        packet_calls.append(mode)
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": 10.0,
            "packet": {"within_budget": True, "route_ready": True},
            "expectation_ok": True,
            "expectation_details": {},
            "required_path_recall": 1.0,
            "required_path_misses": [],
            "critical_path_misses": [],
            "observed_paths": ["scripts/a.py"],
            "effective_estimated_tokens": 100,
            "validation_success_proxy": 1.0,
            "full_scan": {},
            "orchestration": {"leaf_count": 0},
        }

    monkeypatch.setattr(runner, "_packet_result", _fake_packet_result)
    monkeypatch.setattr(
        runner.odylith_benchmark_live_execution,
        "run_live_scenario",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("diagnostic profile should not invoke live Codex")),
    )

    report = runner.run_benchmarks(
        repo_root=tmp_path,
        benchmark_profile=runner.BENCHMARK_PROFILE_DIAGNOSTIC,
        write_report=False,
    )

    assert report["benchmark_profile"] == "diagnostic"
    assert report["modes"] == ["odylith_on", "raw_agent_baseline"]
    assert report["cache_profiles"] == ["warm"]
    assert report["latest_eligible"] is False
    assert report["comparison_contract"] == "internal_packet_prompt_diagnostic"
    assert packet_calls == ["odylith_on", "raw_agent_baseline"]
    assert adoption_proof_calls == [1]


def test_build_packet_payload_uses_family_based_fast_path(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    adaptive_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        runner.store,
        "build_adaptive_coding_packet",
        lambda **kwargs: adaptive_calls.append(dict(kwargs))
        or {
            "packet_source": (
                "session_brief"
                if kwargs.get("family_hint") == "validation_heavy_fix"
                else "impact"
            ),
            "payload": {"packet_metrics": {}, "packet_quality": {}, "routing_handoff": {}, "context_packet": {}},
            "adaptive_escalation": {
                "stage": "session_brief_rescue"
                if kwargs.get("family_hint") == "validation_heavy_fix"
                else "full_scan_fallback"
                if kwargs.get("family_hint") == "broad_shared_scope"
                else "session_brief_rescue"
            },
        },
    )

    source, _payload, escalation = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "family": "validation_heavy_fix",
            "workstream": "",
            "intent": "implementation benchmark",
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_router.py"],
        },
        mode="odylith_on",
        existing_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
    )
    assert source == "session_brief"
    assert escalation["stage"] == "session_brief_rescue"
    assert adaptive_calls
    assert adaptive_calls[0]["intent"] == "implementation benchmark"
    assert adaptive_calls[0]["validation_command_hints"] == ["pytest -q tests/unit/runtime/test_subagent_router.py"]

    adaptive_calls.clear()
    source, _payload, escalation = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={"family": "exact_anchor_recall", "workstream": "B-275", "intent": "implementation benchmark"},
        mode="odylith_on",
        existing_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
    )
    assert source == "impact"
    assert escalation["stage"] == "session_brief_rescue"
    assert adaptive_calls and adaptive_calls[0]["workstream_hint"] == "B-275"

    adaptive_calls.clear()
    source, _payload, _escalation = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={"family": "broad_shared_scope", "workstream": "", "intent": "analysis benchmark"},
        mode="odylith_on",
        existing_paths=["AGENTS.md"],
    )
    assert source == "impact"
    assert adaptive_calls and adaptive_calls[0]["family_hint"] == "broad_shared_scope"

    adaptive_calls.clear()
    source, _payload, _escalation = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "family": "retrieval_miss_recovery",
            "workstream": "",
            "intent": "implementation benchmark",
            "validation_commands": ["pytest -q tests/unit/runtime/test_odylith_context_engine.py -k miss_recovery"],
        },
        mode="odylith_on",
        existing_paths=["src/odylith/runtime/context_engine/odylith_context_engine_store.py"],
    )
    assert source == "impact"
    assert adaptive_calls
    assert adaptive_calls[0]["intent"] == "implementation benchmark"
    assert adaptive_calls[0]["family_hint"] == "retrieval_miss_recovery"
    assert adaptive_calls[0]["validation_command_hints"] == [
        "pytest -q tests/unit/runtime/test_odylith_context_engine.py -k miss_recovery"
    ]


def test_build_packet_payload_uses_hot_path_governance_slice(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    governance_calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        runner.store,
        "build_governance_slice",
        lambda **kwargs: governance_calls.append(dict(kwargs))
        or {
            "packet_metrics": {"within_budget": True},
            "routing_handoff": {},
            "context_packet": {"packet_state": "compact"},
        },
    )

    source, _payload, escalation = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "family": "docs_code_closeout",
            "intent": "implementation benchmark",
            "validation_commands": ["pytest -q tests/unit/runtime/test_render_registry_dashboard.py"],
        },
        mode="odylith_on",
        existing_paths=["src/odylith/runtime/surfaces/render_registry_dashboard.py", "odylith/registry/source/components/registry/CURRENT_SPEC.md"],
    )

    assert source == "governance_slice"
    assert escalation["stage"] == "governance_slice"
    assert governance_calls
    assert governance_calls[0]["delivery_profile"] == "agent_hot_path"
    assert governance_calls[0]["intent"] == "implementation benchmark"
    assert governance_calls[0]["validation_command_hints"] == [
        "pytest -q tests/unit/runtime/test_render_registry_dashboard.py"
    ]


def test_timing_trace_preserves_stage_timings_and_family_metadata(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(
        runner,
        "_recent_reasoning_timing_index",
        lambda **kwargs: {
            "timing-1": {
                "timing_id": "timing-1",
                "ts_iso": "2026-03-24T01:02:03Z",
                "operation": "impact",
                "duration_ms": 17.25,
                "metadata": {
                    "packet_state": "compact",
                    "family_hint": "validation_heavy_fix",
                    "stage_timings": {
                        "path_scope": 1.2,
                        "selection": 3.4,
                    },
                },
            }
        },
    )

    trace = runner._timing_trace(  # noqa: SLF001
        repo_root=tmp_path,
        before={},
        operations=("impact",),
    )

    assert trace["operation_count"] == 1
    assert trace["operations"]["impact"]["duration_ms"] == 17.25
    assert trace["operations"]["impact"]["stage_timings"]["path_scope"] == 1.2
    assert trace["operations"]["impact"]["metadata"]["family_hint"] == "validation_heavy_fix"


def test_orchestration_request_payload_preserves_raw_packet_siblings() -> None:
    payload = runner._orchestration_request_payload(  # noqa: SLF001
        scenario={
            "prompt": "Implement the bounded slice in src/odylith/runtime/orchestration/subagent_router.py.",
            "acceptance_criteria": ["Update the implementation", "Keep the tests green"],
            "changed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_subagent_router.py"],
            "family": "validation_heavy_fix",
            "kind": "packet",
            "needs_write": True,
            "correctness_critical": True,
            "workstream": "B-275",
        },
        packet_payload={
            "routing_handoff": {"packet_kind": "impact", "route_ready": True},
            "context_packet": {"packet_kind": "impact", "full_scan_recommended": False},
            "evidence_pack": {"packet_kind": "impact"},
            "optimization_snapshot": {"speed_mode": "compact"},
            "architecture_audit": {"linked_components": []},
        },
    )

    assert "context_signals" not in payload
    assert payload["routing_handoff"]["packet_kind"] == "impact"
    assert payload["context_packet"]["packet_kind"] == "impact"
    assert payload["evidence_pack"]["packet_kind"] == "impact"
    assert payload["optimization_snapshot"]["speed_mode"] == "compact"
    assert payload["architecture_audit"]["linked_components"] == []


def test_orchestration_request_payload_adds_governance_closeout_candidate_paths() -> None:
    payload = runner._orchestration_request_payload(  # noqa: SLF001
        scenario={
            "prompt": "Close out the registry slice and keep governed artifacts accurate.",
            "acceptance_criteria": ["Refresh the registry docs and keep traceability truthful"],
            "changed_paths": ["src/odylith/runtime/surfaces/render_registry_dashboard.py", "odylith/registry/source/components/registry/CURRENT_SPEC.md"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_render_registry_dashboard.py"],
            "family": "docs_code_closeout",
            "kind": "packet",
            "needs_write": True,
            "correctness_critical": False,
            "workstream": "",
        },
        packet_payload={
            "governance_obligations": {
                "touched_workstreams": [
                    {
                        "entity_id": "B-268",
                        "path": "odylith/radar/source/ideas/2026-03/example.md",
                        "metadata": {"promoted_to_plan": "odylith/technical-plans/done/2026-03/example.md"},
                    }
                ],
                "touched_components": [
                    {"component_id": "registry", "path": "odylith/registry/source/components/registry/CURRENT_SPEC.md"},
                ],
                "required_diagrams": [
                    {"diagram_id": "D-035", "source_mmd": "odylith/atlas/source/registry.mmd"},
                ],
                "closeout_docs": [
                    "odylith/casebook/bugs/2026-03-24-control-plane-read-scope-and-auth-escape-hatch-gap.md",
                ],
            },
        },
    )

    assert "odylith/casebook/bugs/2026-03-24-control-plane-read-scope-and-auth-escape-hatch-gap.md" in payload["candidate_paths"]
    assert "odylith/technical-plans/done/2026-03/example.md" in payload["candidate_paths"]
    assert "odylith/atlas/source/registry.mmd" in payload["candidate_paths"]


def test_orchestration_request_payload_uses_expected_write_paths_for_action_scope() -> None:
    payload = runner._orchestration_request_payload(  # noqa: SLF001
        scenario={
            "prompt": "Work the router/orchestrator implementation slice.",
            "changed_paths": [
                "odylith/skills/odylith-subagent-router/SKILL.md",
                "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
            ],
            "expected_write_paths": [
                "src/odylith/runtime/orchestration/subagent_router.py",
                "src/odylith/runtime/orchestration/subagent_orchestrator.py",
            ],
            "validation_commands": ["odylith subagent-router --repo-root . --help"],
            "family": "cross_file_feature",
            "kind": "packet",
            "needs_write": True,
            "correctness_critical": False,
            "workstream": "B-001",
        },
        packet_payload={},
    )

    assert payload["candidate_paths"] == [
        "src/odylith/runtime/orchestration/subagent_router.py",
        "src/odylith/runtime/orchestration/subagent_orchestrator.py",
    ]


def test_mode_summary_aggregates_stage_latency_summary() -> None:
    summary = runner._mode_summary(  # noqa: SLF001
        mode="odylith_on",
        scenario_rows=[
            {
                "kind": "packet",
                "latency_ms": 12.0,
                "effective_estimated_tokens": 100,
                "total_payload_estimated_tokens": 120,
                "runtime_contract_estimated_tokens": 20,
                "operator_diag_estimated_tokens": 5,
                "runtime_contract_artifact_tokens": {"routing_handoff": 12, "packet_metrics": 8},
                "operator_diag_artifact_tokens": {"impact_summary": 5},
                "prompt_artifact_tokens": {"context_packet": 100},
                "adaptive_escalation": {"stage": "compact_success"},
                "required_path_recall": 1.0,
                "validation_success_proxy": 1.0,
                "expectation_ok": True,
                "packet": {"within_budget": True, "route_ready": True},
                "orchestration": {
                    "leaf_count": 1,
                    "odylith_adoption": {
                        "packet_present": True,
                        "auto_grounding_applied": True,
                        "requires_widening": False,
                        "grounded": True,
                        "grounded_delegate": True,
                        "grounding_source": "auto_grounded",
                        "operation": "impact",
                        "runtime_source": "workspace_daemon",
                        "runtime_transport": "unix",
                        "workspace_daemon_reused": True,
                        "session_namespaced": True,
                        "mixed_local_fallback": False,
                    },
                },
                "required_path_count": 1,
                "validation_command_count": 1,
                "correctness_critical": True,
                "timing_trace": {
                    "operations": {
                        "impact": {
                            "duration_ms": 12.0,
                            "stage_timings": {
                                "path_scope": 1.0,
                                "selection": 4.0,
                            },
                        }
                    }
                },
            },
            {
                "kind": "packet",
                "latency_ms": 18.0,
                "effective_estimated_tokens": 90,
                "total_payload_estimated_tokens": 110,
                "runtime_contract_estimated_tokens": 18,
                "operator_diag_estimated_tokens": 4,
                "runtime_contract_artifact_tokens": {"routing_handoff": 10, "packet_metrics": 8},
                "operator_diag_artifact_tokens": {"impact_summary": 4},
                "prompt_artifact_tokens": {"context_packet": 90},
                "adaptive_escalation": {"stage": "session_brief_rescue"},
                "required_path_recall": 1.0,
                "validation_success_proxy": 1.0,
                "expectation_ok": True,
                "packet": {"within_budget": True, "route_ready": False},
                "orchestration": {
                    "leaf_count": 0,
                    "odylith_adoption": {
                        "packet_present": True,
                        "auto_grounding_applied": False,
                        "requires_widening": True,
                        "grounded": False,
                        "grounded_delegate": False,
                        "grounding_source": "supplied_packet",
                        "operation": "session_brief",
                        "runtime_source": "local_process",
                        "runtime_transport": "local",
                        "workspace_daemon_reused": False,
                        "session_namespaced": False,
                        "mixed_local_fallback": False,
                    },
                },
                "required_path_count": 1,
                "validation_command_count": 1,
                "correctness_critical": True,
                "timing_trace": {
                    "operations": {
                        "impact": {
                            "duration_ms": 18.0,
                            "stage_timings": {
                                "path_scope": 3.0,
                                "selection": 6.0,
                            },
                        }
                    }
                },
            },
        ],
    )

    assert summary["stage_latency_summary"]["impact.total"]["median_ms"] == 15.0
    assert summary["stage_latency_summary"]["impact.path_scope"]["median_ms"] == 2.0
    assert summary["stage_latency_summary"]["impact.selection"]["avg_ms"] == 5.0
    assert summary["runtime_contract_artifact_summary"]["routing_handoff"]["median_tokens"] == 11.0
    assert summary["operator_diag_artifact_summary"]["impact_summary"]["avg_tokens"] == 4.5
    assert summary["escalation_stage_distribution"] == {
        "compact_success": 1,
        "session_brief_rescue": 1,
    }
    assert summary["odylith_packet_present_rate"] == 1.0
    assert summary["odylith_auto_grounded_rate"] == 0.5
    assert summary["odylith_requires_widening_rate"] == 0.5
    assert summary["odylith_grounded_delegate_rate"] == 0.5
    assert summary["odylith_workspace_daemon_reuse_rate"] == 0.5
    assert summary["odylith_session_namespaced_rate"] == 0.5
    assert summary["odylith_mixed_local_fallback_rate"] == 0.0
    assert summary["odylith_grounding_source_distribution"] == {
        "auto_grounded": 1,
        "supplied_packet": 1,
    }
    assert summary["odylith_operation_distribution"] == {
        "impact": 1,
        "session_brief": 1,
    }
    assert summary["odylith_runtime_source_distribution"] == {
        "local_process": 1,
        "workspace_daemon": 1,
    }
    assert summary["odylith_runtime_transport_distribution"] == {
        "local": 1,
        "unix": 1,
    }


def test_compact_report_summary_includes_candidate_odylith_adoption_rates() -> None:
    summary = runner.compact_report_summary(
        {
            "report_id": "report-123",
            "generated_utc": "2026-03-24T12:00:00Z",
            "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
            "comparison_contract_details": runner._comparison_contract_details(runner.LIVE_COMPARISON_CONTRACT),  # noqa: SLF001
            "acceptance": {"status": "provisional_pass"},
            "scenario_count": 4,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "fairness_contract_passed": True,
            "fairness_findings": [],
            "observed_path_sources": ["odylith_prompt_payload", "raw_prompt_visible_paths"],
            "preflight_evidence_mode": "mixed",
            "preflight_evidence_modes": ["none", "scenario_declared_focused_local_checks"],
            "mode_summaries": {
                "odylith_on": {
                    "odylith_packet_present_rate": 1.0,
                    "odylith_auto_grounded_rate": 0.75,
                    "odylith_requires_widening_rate": 0.25,
                    "odylith_grounded_delegate_rate": 0.5,
                    "odylith_workspace_daemon_reuse_rate": 0.5,
                    "odylith_session_namespaced_rate": 0.25,
                }
            },
            "primary_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
                "median_latency_delta_ms": -9.0,
                "median_prompt_token_delta": -11.0,
                "median_total_payload_token_delta": -9.0,
                "required_path_recall_delta": 0.05,
                "validation_success_delta": 0.1,
                "critical_required_path_recall_delta": 0.1,
                "critical_validation_success_delta": 0.2,
                "expectation_success_delta": 0.25,
            },
            "published_mode_summaries": {
                "odylith_on": {
                    "odylith_packet_present_rate": 0.9,
                    "odylith_auto_grounded_rate": 0.5,
                    "odylith_requires_widening_rate": 0.5,
                    "odylith_grounded_delegate_rate": 0.25,
                    "odylith_workspace_daemon_reuse_rate": 0.25,
                    "odylith_session_namespaced_rate": 0.25,
                }
            },
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
                "median_latency_delta_ms": -12.0,
                "median_prompt_token_delta": -20.0,
                "median_total_payload_token_delta": -10.0,
                "required_path_recall_delta": 0.1,
                "required_path_precision_delta": 0.2,
                "hallucinated_surface_rate_delta": -0.2,
                "validation_success_delta": 0.2,
                "write_surface_precision_delta": 0.15,
                "unnecessary_widening_rate_delta": -0.15,
                "critical_required_path_recall_delta": 0.3,
                "critical_validation_success_delta": 0.4,
                "expectation_success_delta": 0.5,
            },
            "published_packet_source_summaries": {
                "bootstrap_session": {
                    "odylith_on": {
                        "scenario_count": 2,
                    }
                }
            },
            "published_packet_source_deltas": {
                "bootstrap_session": {
                    "candidate_mode": "odylith_on",
                    "baseline_mode": "raw_agent_baseline",
                    "median_prompt_token_delta": -18.0,
                    "median_total_payload_token_delta": -32.0,
                }
            },
            "runtime_posture": {
                "memory_standardization_state": "standardized",
                "memory_backed_retrieval_ready": True,
                "memory_backend_actual": {
                    "storage": "lance_local_columnar",
                    "sparse_recall": "tantivy_sparse_recall",
                },
                "memory_projection_scope": "full",
                "memory_indexed_entity_count": 1534,
                "memory_evidence_document_count": 1575,
                "repo_scan_degraded_fallback_rate": 0.15,
                "hard_grounding_failure_rate": 0.05,
                "soft_widening_rate": 0.2,
                "visible_fallback_receipt_rate": 0.01,
                "governance_runtime_first_usage_rate": 1.0,
                "remote_retrieval_status": "disabled",
                "remote_retrieval_mode": "disabled",
                "remote_retrieval_enabled": False,
                "route_ready_rate": 0.75,
                "native_spawn_ready_rate": 0.5,
                "architecture_covered_case_count": 3,
                "architecture_satisfied_case_count": 3,
            },
            "adoption_proof": {
                "sample_size": 12,
                "auto_grounded_rate": 1.0,
                "requires_widening_rate": 0.083,
                "grounded_delegate_rate": 0.917,
                "workspace_daemon_reused_rate": 0.75,
                "session_namespaced_rate": 1.0,
            },
            "robustness_summary": {
                "selected_cache_profile_count": 2,
                "selected_cache_profile_pass_rate": 1.0,
                "warm_cold_consistency_cleared": True,
                "rerun_stability_state": "measured_pass",
                "rerun_probe_family_count": 1,
                "rerun_probe_scenario_count": 1,
                "rerun_probe_mode_count": 2,
                "rerun_probe_sample_count": 10,
                "rerun_probe_latency_pass_rate": 1.0,
                "rerun_probe_quality_consistency_pass_rate": 1.0,
                "rerun_probe_worst_latency_spread_ms": 2.5,
                "candidate_latency_spread_ms": 4.0,
                "candidate_prompt_token_spread": 20.0,
                "candidate_required_path_precision_spread": 0.1,
                "candidate_write_surface_precision_spread": 0.05,
            },
            "corpus_contract": {
                "status": "canonical",
                "packet_scenario_key": "scenarios",
                "architecture_scenario_key": "architecture_scenarios",
            },
            "corpus_composition": {
                "seriousness_floor_passed": True,
                "full_corpus_coverage_rate": 1.0,
                "full_corpus_selected": True,
                "implementation_scenario_count": 60,
                "write_plus_validator_scenario_count": 43,
                "correctness_critical_scenario_count": 18,
                "mechanism_heavy_implementation_ratio": 0.3,
            },
        }
    )

    assert summary["comparison_contract"] == runner.LIVE_COMPARISON_CONTRACT
    assert summary["comparison_primary_claim"] == "full_product_assistance_vs_raw_agent"
    assert summary["odylith_packet_present_rate"] == 0.9
    assert summary["required_path_precision_delta"] == 0.2
    assert summary["hallucinated_surface_rate_delta"] == -0.2
    assert summary["write_surface_precision_delta"] == 0.15
    assert summary["unnecessary_widening_rate_delta"] == -0.15
    assert summary["odylith_auto_grounded_rate"] == 1.0
    assert summary["odylith_requires_widening_rate"] == 0.083
    assert summary["odylith_grounded_delegate_rate"] == 0.917
    assert summary["odylith_workspace_daemon_reuse_rate"] == 0.75
    assert summary["odylith_session_namespaced_rate"] == 1.0
    assert summary["runtime_memory_standardization_state"] == "standardized"
    assert summary["runtime_memory_backed_retrieval_ready"] is True
    assert summary["runtime_memory_storage"] == "lance_local_columnar"
    assert summary["runtime_memory_sparse_recall"] == "tantivy_sparse_recall"
    assert summary["runtime_memory_projection_scope"] == "full"
    assert summary["runtime_memory_indexed_entity_count"] == 1534
    assert summary["runtime_memory_evidence_document_count"] == 1575
    assert summary["runtime_repo_scan_degraded_fallback_rate"] == 0.15
    assert summary["runtime_hard_grounding_failure_rate"] == 0.05
    assert summary["runtime_soft_widening_rate"] == 0.2
    assert summary["runtime_visible_fallback_receipt_rate"] == 0.01
    assert summary["runtime_governance_runtime_first_usage_rate"] == 1.0
    assert summary["runtime_remote_retrieval_status"] == "disabled"
    assert summary["runtime_remote_retrieval_mode"] == "disabled"
    assert summary["runtime_remote_retrieval_enabled"] is False
    assert summary["runtime_route_ready_rate"] == 0.75
    assert summary["runtime_native_spawn_ready_rate"] == 0.5
    assert summary["runtime_architecture_covered_case_count"] == 3
    assert summary["runtime_architecture_satisfied_case_count"] == 3
    assert summary["bootstrap_session_scenario_count"] == 2
    assert summary["bootstrap_session_prompt_token_delta"] == -18.0
    assert summary["bootstrap_session_total_payload_token_delta"] == -32.0
    assert summary["adoption_proof_sample_size"] == 12
    assert summary["adoption_proof_auto_grounded_rate"] == 1.0
    assert summary["adoption_proof_requires_widening_rate"] == 0.083
    assert summary["adoption_proof_grounded_delegate_rate"] == 0.917
    assert summary["adoption_proof_workspace_daemon_reused_rate"] == 0.75
    assert summary["adoption_proof_session_namespaced_rate"] == 1.0
    assert summary["robustness_selected_cache_profile_count"] == 2
    assert summary["robustness_selected_cache_profile_pass_rate"] == 1.0
    assert summary["robustness_warm_cold_consistency_cleared"] is True
    assert summary["robustness_rerun_stability_state"] == "measured_pass"
    assert summary["robustness_rerun_probe_family_count"] == 1
    assert summary["robustness_rerun_probe_scenario_count"] == 1
    assert summary["robustness_rerun_probe_mode_count"] == 2
    assert summary["robustness_rerun_probe_sample_count"] == 10
    assert summary["robustness_rerun_probe_latency_pass_rate"] == 1.0
    assert summary["robustness_rerun_probe_quality_consistency_pass_rate"] == 1.0
    assert summary["robustness_rerun_probe_worst_latency_spread_ms"] == 2.5
    assert summary["corpus_contract_status"] == "canonical"
    assert summary["corpus_packet_scenario_key"] == "scenarios"
    assert summary["corpus_architecture_scenario_key"] == "architecture_scenarios"
    assert summary["fairness_contract_passed"] is True
    assert summary["fairness_finding_count"] == 0
    assert summary["observed_path_sources"] == ["odylith_prompt_payload", "raw_prompt_visible_paths"]
    assert summary["preflight_evidence_modes"] == ["none", "scenario_declared_focused_local_checks"]
    assert summary["corpus_seriousness_floor_passed"] is True
    assert summary["corpus_full_coverage_rate"] == 1.0
    assert summary["corpus_implementation_scenario_count"] == 60
    assert summary["corpus_write_plus_validator_scenario_count"] == 43
    assert summary["corpus_correctness_critical_scenario_count"] == 18
    assert summary["corpus_mechanism_heavy_implementation_ratio"] == 0.3
    assert summary["prompt_token_delta"] == -20.0
    assert summary["published_view_strategy"] == "conservative_multi_profile"
    assert summary["published_cache_profiles"] == ["warm", "cold"]


def test_render_report_summary_includes_fairness_and_corpus_contract_fields() -> None:
    report_text = runner._render_report_summary(  # noqa: SLF001
        {
            "report_id": "report-123",
            "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
            "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
            "comparison_contract_details": runner._comparison_contract_details(runner.LIVE_COMPARISON_CONTRACT),  # noqa: SLF001
            "acceptance": {
                "status": "provisional_pass",
                "hard_quality_gate_cleared": True,
                "secondary_guardrails_cleared": True,
                "hard_gate_failure_labels": [],
                "secondary_guardrail_failure_labels": [],
            },
            "scenario_count": 65,
            "published_view_strategy": "conservative_multi_profile",
            "published_cache_profiles": ["warm", "cold"],
            "published_comparison": {
                "candidate_mode": "odylith_on",
                "baseline_mode": "raw_agent_baseline",
            },
            "corpus_contract": {"status": "canonical"},
            "corpus_composition": {
                "seriousness_floor_passed": True,
                "full_corpus_coverage_rate": 1.0,
                "implementation_scenario_count": 60,
                "write_plus_validator_scenario_count": 43,
                "correctness_critical_scenario_count": 18,
            },
            "fairness_contract_passed": True,
            "fairness_findings": [],
            "observed_path_sources": ["odylith_prompt_payload", "raw_prompt_visible_paths"],
            "preflight_evidence_modes": ["none", "scenario_declared_focused_local_checks"],
        }
    )

    assert "- comparison_contract: full_product_assistance_vs_raw_agent" in report_text
    assert "- fairness_contract_passed: True" in report_text
    assert "- observed_path_sources: odylith_prompt_payload, raw_prompt_visible_paths" in report_text
    assert "- preflight_evidence_modes: none, scenario_declared_focused_local_checks" in report_text
    assert "- corpus_seriousness_floor_passed: True" in report_text
    assert "- corpus_implementation_scenario_count: 60" in report_text


def test_latency_measurement_fields_expose_uninstrumented_overhead() -> None:
    fields = runner._latency_measurement_fields(  # noqa: SLF001
        latency_ms=38.234,
        timing_trace={
            "operations": {
                "impact": {"duration_ms": 8.577},
            }
        },
    )

    assert fields == {
        "instrumented_reasoning_duration_ms": 8.577,
        "uninstrumented_overhead_ms": 29.657,
    }


def test_singleton_family_latency_probes_stabilize_sensitive_family_latency(monkeypatch) -> None:  # noqa: ANN001
    prepare_calls: list[str] = []

    def _fake_prepare(*, repo_root: Path, cache_profile: str) -> None:
        del repo_root
        prepare_calls.append(cache_profile)

    sample_latencies = {
        ("warm", "odylith_on"): [11.633, 11.981, 11.051, 11.2, 11.4],
        ("warm", "raw_agent_baseline"): [21.248, 24.036, 24.328, 24.1, 24.4],
        ("cold", "odylith_on"): [1342.625, 1432.755, 1344.57, 1341.0, 1343.0],
        ("cold", "raw_agent_baseline"): [1347.536, 1400.826, 1364.699, 1348.0, 1350.0],
    }
    call_index = {key: 0 for key in sample_latencies}

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        del repo_root, scenario
        assert benchmark_profile == runner.BENCHMARK_PROFILE_PROOF
        profile = prepare_calls[-1]
        key = (profile, mode)
        idx = call_index[key]
        call_index[key] += 1
        latency = sample_latencies[key][idx]
        return {
            "kind": "packet",
            "mode": mode,
            "latency_ms": latency,
            "instrumented_reasoning_duration_ms": 9.0,
            "uninstrumented_overhead_ms": round(latency - 9.0, 3),
            "required_path_precision": 1.0 if mode == "odylith_on" else 0.0,
            "required_path_recall": 1.0 if mode == "odylith_on" else 0.0,
            "validation_success_proxy": 1.0 if mode == "odylith_on" else 0.0,
            "expectation_ok": mode == "odylith_on",
        }

    monkeypatch.setattr(runner, "_prepare_benchmark_runtime_cache", _fake_prepare)
    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)

    scenario = {
        "scenario_id": "runtime-path-ambiguity",
        "label": "Exact runtime path ambiguity remains bounded",
        "family": "exact_path_ambiguity",
        "kind": "packet",
    }
    probes = runner._singleton_family_latency_probes(  # noqa: SLF001
        repo_root=Path("/tmp/odylith"),
        scenarios=[scenario],
        modes=["odylith_on", "raw_agent_baseline"],
        cache_profiles=["warm", "cold"],
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    warm_probe = probes["warm:runtime-path-ambiguity"]["modes"]["odylith_on"]
    assert warm_probe["sample_count"] == 3
    assert warm_probe["median_latency_ms"] == 11.633
    assert warm_probe["latency_probe_spread_ms"] == 0.93
    assert warm_probe["quality_consistency_cleared"] is True
    assert warm_probe["latency_stability_cleared"] is True

    family_summaries = {
        "exact_path_ambiguity": {
            "odylith_on": {"median_latency_ms": 38.234, "avg_latency_ms": 38.234},
            "raw_agent_baseline": {"median_latency_ms": 24.853, "avg_latency_ms": 24.853},
        }
    }
    stabilized = runner._apply_singleton_family_latency_probes(  # noqa: SLF001
        family_summaries=family_summaries,
        latency_probes=probes,
        cache_profile="warm",
    )

    assert stabilized["exact_path_ambiguity"]["odylith_on"]["median_latency_ms"] == 11.633
    assert stabilized["exact_path_ambiguity"]["odylith_on"]["latency_measurement_basis"] == "singleton_rerun_median"
    assert stabilized["exact_path_ambiguity"]["odylith_on"]["latency_probe_sample_count"] == 3
    assert stabilized["exact_path_ambiguity"]["odylith_on"]["latency_stability_cleared"] is True

    unchanged_cold = runner._apply_singleton_family_latency_probes(  # noqa: SLF001
        family_summaries=family_summaries,
        latency_probes=probes,
        cache_profile="cold",
    )
    assert unchanged_cold["exact_path_ambiguity"]["odylith_on"]["median_latency_ms"] == 38.234

    published = runner._apply_singleton_latency_probes_to_published_scenarios(  # noqa: SLF001
        published_scenarios=[
            {
                "scenario_id": "runtime-path-ambiguity",
                "published_source_cache_profile": "warm",
                "results": [
                    {"mode": "odylith_on", "latency_ms": 38.234},
                    {"mode": "raw_agent_baseline", "latency_ms": 24.853},
                ],
            },
            {
                "scenario_id": "runtime-path-ambiguity",
                "published_source_cache_profile": "cold",
                "results": [
                    {"mode": "odylith_on", "latency_ms": 1432.755},
                    {"mode": "raw_agent_baseline", "latency_ms": 1400.826},
                ],
            },
        ],
        latency_probes=probes,
    )
    assert published[0]["results"][0]["latency_ms"] == 11.633
    assert published[0]["results"][1]["latency_ms"] == 24.036
    assert published[1]["results"][0]["latency_ms"] == 1432.755

    robustness = runner._robustness_summary(  # noqa: SLF001
        cache_profile_summaries={},
        candidate_mode="odylith_on",
        latency_probes=probes,
    )

    assert robustness["rerun_stability_state"] == "measured_attention"
    assert robustness["rerun_probe_family_count"] == 1
    assert robustness["rerun_probe_scenario_count"] == 1
    assert robustness["rerun_probe_mode_count"] == 4
    assert robustness["rerun_probe_sample_count"] == 12


def test_sensitive_latency_probe_candidates_include_multi_scenario_sensitive_families() -> None:
    candidates = runner._sensitive_singleton_latency_probe_candidates(  # noqa: SLF001
        scenarios=[
            {
                "scenario_id": "runtime-path-ambiguity",
                "label": "Runtime path ambiguity",
                "family": "exact_path_ambiguity",
                "kind": "packet",
            },
            {
                "scenario_id": "session-brief-runtime-path-ambiguity",
                "label": "Session brief runtime path ambiguity",
                "family": "exact_path_ambiguity",
                "kind": "packet",
            },
            {
                "scenario_id": "wave4-runtime-sparse-miss-recovery",
                "label": "Sparse miss recovery",
                "family": "retrieval_miss_recovery",
                "kind": "packet",
            },
            {
                "scenario_id": "shell-and-compass-browser-reliability",
                "label": "Browser reliability",
                "family": "browser_surface_reliability",
                "kind": "packet",
            },
        ]
    )

    assert [row["scenario_id"] for row in candidates] == [
        "runtime-path-ambiguity",
        "session-brief-runtime-path-ambiguity",
        "wave4-runtime-sparse-miss-recovery",
    ]


def test_singleton_latency_probe_does_not_override_published_latency_when_probe_is_detached_outlier() -> None:
    published = runner._apply_singleton_latency_probes_to_published_scenarios(  # noqa: SLF001
        published_scenarios=[
            {
                "scenario_id": "session-brief-runtime-path-ambiguity",
                "published_source_cache_profile": "cold",
                "results": [
                    {"mode": "odylith_on", "latency_ms": 5.983},
                    {"mode": "raw_agent_baseline", "latency_ms": 0.001},
                ],
            }
        ],
        latency_probes={
            "cold:session-brief-runtime-path-ambiguity": {
                "cache_profile": "cold",
                "scenario_id": "session-brief-runtime-path-ambiguity",
                "modes": {
                    "odylith_on": {
                        "sample_count": 3,
                        "median_latency_ms": 148.544,
                        "latency_probe_spread_ms": 2.119,
                        "latency_stability_cleared": True,
                        "quality_consistency_cleared": True,
                    },
                    "raw_agent_baseline": {
                        "sample_count": 3,
                        "median_latency_ms": 0.001,
                        "latency_probe_spread_ms": 0.002,
                        "latency_stability_cleared": True,
                        "quality_consistency_cleared": True,
                    },
                },
            }
        },
    )

    assert published[0]["results"][0]["latency_ms"] == 5.983
    assert published[0]["results"][1]["latency_ms"] == 0.001


def test_aggregate_published_scenarios_prefers_primary_profile_on_near_tie() -> None:
    published = runner._aggregate_published_scenarios(  # noqa: SLF001
        scenarios=[{"scenario_id": "closeout-surface-path-normalization"}],
        modes=["odylith_on", "raw_agent_baseline"],
        cache_profiles=["warm", "cold"],
        cache_profile_reports={
            "warm": [
                {
                    "scenario_id": "closeout-surface-path-normalization",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "latency_ms": 5.277,
                            "effective_estimated_tokens": 120,
                            "total_payload_estimated_tokens": 160,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "latency_ms": 0.003,
                            "effective_estimated_tokens": 90,
                            "total_payload_estimated_tokens": 130,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                }
            ],
            "cold": [
                {
                    "scenario_id": "closeout-surface-path-normalization",
                    "results": [
                        {
                            "mode": "odylith_on",
                            "latency_ms": 5.658,
                            "effective_estimated_tokens": 120,
                            "total_payload_estimated_tokens": 160,
                            "required_path_recall": 1.0,
                            "validation_success_proxy": 1.0,
                        },
                        {
                            "mode": "raw_agent_baseline",
                            "latency_ms": 0.003,
                            "effective_estimated_tokens": 90,
                            "total_payload_estimated_tokens": 130,
                            "required_path_recall": 0.0,
                            "validation_success_proxy": 0.0,
                        },
                    ],
                }
            ],
        },
    )

    assert published[0]["published_source_cache_profile"] == "warm"


def test_run_live_adoption_proof_aggregates_seed_only_orchestration_results(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(runner, "_benchmark_proof_daemon", lambda repo_root: contextlib.nullcontext(True))
    seen_requests: list[dict[str, object]] = []
    persisted: dict[str, object] = {}

    def _fake_orchestration_summary(
        *,
        request_payload: dict[str, object],
        repo_root: Path,
        mode: str,
        timeout_seconds: float | None = None,
    ) -> dict[str, object]:
        del repo_root, mode, timeout_seconds
        seen_requests.append(dict(request_payload))
        operation = str(request_payload.get("odylith_operation", "")).strip()
        widened = operation == "architecture"
        return {
            "odylith_adoption": {
                "packet_present": True,
                "auto_grounding_applied": True,
                "route_ready": not widened,
                "native_spawn_ready": not widened,
                "requires_widening": widened,
                "grounded_delegate": not widened,
                "workspace_daemon_reused": True,
                "session_namespaced": True,
                "operation": operation,
                "grounding_source": "auto_grounded",
                "runtime_source": "workspace_daemon",
            }
        }

    monkeypatch.setattr(runner, "_bounded_orchestration_summary", _fake_orchestration_summary)
    monkeypatch.setattr(
        runner.store,
        "persist_orchestration_adoption_snapshot",
        lambda *, repo_root, snapshot, source: (
            persisted.update({"repo_root": repo_root, "snapshot": dict(snapshot), "source": source})
            or dict(snapshot)
        ),
    )

    proof = runner._run_live_adoption_proof(  # noqa: SLF001
        repo_root=tmp_path,
        scenarios=[
            {"scenario_id": "impact-1", "kind": "packet", "family": "validation_heavy_fix", "changed_paths": ["scripts/a.py"]},
            {"scenario_id": "impact-2", "kind": "packet", "family": "cross_file_feature", "changed_paths": ["scripts/b.py"]},
            {"scenario_id": "impact-3", "kind": "packet", "family": "merge_heavy_change", "changed_paths": ["scripts/c.py"]},
            {"scenario_id": "impact-4", "kind": "packet", "family": "orchestration_feedback", "changed_paths": ["scripts/d.py"]},
            {"scenario_id": "impact-5", "kind": "packet", "family": "retrieval_miss_recovery", "changed_paths": ["scripts/e.py"]},
            {"scenario_id": "impact-6", "kind": "packet", "family": "dashboard_surface", "changed_paths": ["scripts/f.py"]},
            {"scenario_id": "impact-7", "kind": "packet", "family": "orchestration_intelligence", "changed_paths": ["scripts/g.py"]},
            {"scenario_id": "gov-1", "kind": "packet", "family": "docs_code_closeout", "changed_paths": ["docs/a.md"]},
            {"scenario_id": "gov-2", "kind": "packet", "family": "explicit_workstream", "changed_paths": ["odylith/technical-plans/a.md"]},
            {"scenario_id": "gov-3", "kind": "packet", "family": "governed_surface_sync", "changed_paths": ["tools/a.json"]},
            {"scenario_id": "arch-1", "kind": "architecture", "family": "architecture", "changed_paths": ["consumer/gateway.py"]},
            {"scenario_id": "arch-2", "kind": "architecture", "family": "architecture", "changed_paths": ["consumer/control_plane/jobs_cutover.py"]},
            {"scenario_id": "arch-3", "kind": "architecture", "family": "architecture", "changed_paths": ["src/odylith/runtime/context_engine/odylith_context_engine.py"]},
        ],
    )

    assert proof["sample_size"] == 12
    assert proof["packet_present_rate"] == 1.0
    assert proof["auto_grounded_rate"] == 1.0
    assert proof["route_ready_rate"] == 0.75
    assert proof["native_spawn_ready_rate"] == 0.75
    assert proof["requires_widening_rate"] == 0.25
    assert proof["workspace_daemon_reused_rate"] == 1.0
    assert proof["session_namespaced_rate"] == 1.0
    assert proof["operation_distribution"] == {
        "architecture": 3,
        "governance_slice": 3,
        "impact": 6,
    }
    assert persisted["source"] == "benchmark_live_adoption_proof"
    assert persisted["snapshot"]["sample_size"] == 12
    gov_request = next(
        request for request in seen_requests if str(request.get("odylith_operation", "")).strip() == "governance_slice"
    )
    assert "odylith/index.html" in gov_request["candidate_paths"]


def test_run_live_adoption_proof_degrades_cleanly_when_a_sample_times_out(
    tmp_path: Path,
    monkeypatch,  # noqa: ANN001
) -> None:
    monkeypatch.setattr(runner, "_benchmark_proof_daemon", lambda repo_root: contextlib.nullcontext(True))
    monkeypatch.setattr(runner, "_adoption_proof_timeout_seconds", lambda: 1.5)
    persisted = False

    def _raise_timeout(**_: object) -> dict[str, object]:
        raise runner._BenchmarkAdoptionProofTimeout("benchmark adoption-proof sample exceeded 1.5s")  # noqa: SLF001

    monkeypatch.setattr(runner, "_bounded_orchestration_summary", _raise_timeout)
    monkeypatch.setattr(
        runner.store,
        "persist_orchestration_adoption_snapshot",
        lambda **_: (_ for _ in ()).throw(AssertionError("snapshot should not persist when no sample completes")),
    )

    proof = runner._run_live_adoption_proof(  # noqa: SLF001
        repo_root=tmp_path,
        scenarios=[
            {"scenario_id": "impact-1", "kind": "packet", "family": "validation_heavy_fix", "changed_paths": ["scripts/a.py"]},
            {"scenario_id": "gov-1", "kind": "packet", "family": "docs_code_closeout", "changed_paths": ["docs/a.md"]},
        ],
    )

    assert persisted is False
    assert proof["planned_sample_size"] == 2
    assert proof["attempted_sample_count"] == 1
    assert proof["sample_size"] == 0
    assert proof["sample_timeout_seconds"] == 1.5
    assert proof["degraded"] is True
    assert proof["timed_out_sample_count"] == 1
    assert proof["failed_sample_count"] == 0
    assert proof["aborted_sample_count"] == 1
    assert proof["degradation_reason_distribution"] == {"timeout": 1}
    assert proof["degraded_samples"] == [
        {
            "sample_id": "01-impact-1",
            "operation": "impact",
            "reason": "timeout",
            "message": "benchmark adoption-proof sample exceeded 1.5s",
        }
    ]
    assert proof["route_ready_rate"] == 0.0


def test_proof_request_adds_governed_surface_path_for_governance_slice() -> None:
    request = runner._proof_request_from_scenario(  # noqa: SLF001
        scenario={
            "scenario_id": "docs-closeout",
            "kind": "packet",
            "family": "docs_code_closeout",
            "prompt": "Close out the governed docs slice.",
            "changed_paths": ["odylith/runtime/EXAMPLE_SPEC.md", "scripts/render_example_dashboard.py"],
            "needs_write": True,
        },
        operation="governance_slice",
        sample_id="01-docs-closeout",
    )

    assert "odylith/index.html" in request["candidate_paths"]
    assert "odylith/index.html" in request["claimed_paths"]


def test_proof_request_from_live_explicit_workstream_scenario_stays_orchestration_valid() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "wave3-explicit-workstream")

    request = runner._proof_request_from_scenario(  # noqa: SLF001
        scenario=scenario,
        operation=runner._packet_source_for_scenario(scenario),  # noqa: SLF001
        sample_id="proof-explicit",
    )

    assert request["workstreams"] == ["B-001"]
    assert subagent_orchestrator._implied_write_surface_errors(  # noqa: SLF001
        subagent_orchestrator.OrchestrationRequest(**request)
    ) == []


def test_live_validation_heavy_proof_slice_delegates_when_grounded(monkeypatch: pytest.MonkeyPatch) -> None:
    # After the execution-engine critical-path guard landed, these
    # scenarios stay local because the governance layer classifies them as
    # verify-mode critical paths. The test still proves the orchestrator
    # produces a valid summary from the live scenario corpus; the original
    # "delegates" assertion is updated to match the live contract.
    for key in list(os.environ):
        if key.startswith("CLAUDE_CODE") or key == "CLAUDE_CODE":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("__CFBundleIdentifier", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "test-thread-id")

    repo_root = REPO_ROOT
    scenarios = runner.load_benchmark_scenarios(repo_root=repo_root)
    scenario = next(row for row in scenarios if row["scenario_id"] == "validation-heavy-router-fix")

    summary = runner._safe_orchestration_summary(  # noqa: SLF001
        request_payload=runner._proof_request_from_scenario(  # noqa: SLF001
            scenario=scenario,
            operation=runner._packet_source_for_scenario(scenario),  # noqa: SLF001
            sample_id="proof-validation-heavy",
        ),
        repo_root=repo_root,
        mode="odylith_on",
    )

    assert summary["delegate"] is False
    assert summary["mode"] == "local_only"
    assert "execution-engine-critical-path" in summary.get("local_only_reasons", [])


def test_live_explicit_workstream_proof_slice_delegates_when_grounded(monkeypatch: pytest.MonkeyPatch) -> None:
    # Same governance-critical-path shift as the validation-heavy test above.
    for key in list(os.environ):
        if key.startswith("CLAUDE_CODE") or key == "CLAUDE_CODE":
            monkeypatch.delenv(key, raising=False)
    monkeypatch.delenv("__CFBundleIdentifier", raising=False)
    monkeypatch.setenv("CODEX_THREAD_ID", "test-thread-id")

    repo_root = REPO_ROOT
    scenarios = runner.load_benchmark_scenarios(repo_root=repo_root)
    scenario = next(row for row in scenarios if row["scenario_id"] == "wave3-explicit-workstream")

    summary = runner._safe_orchestration_summary(  # noqa: SLF001
        request_payload=runner._proof_request_from_scenario(  # noqa: SLF001
            scenario=scenario,
            operation=runner._packet_source_for_scenario(scenario),  # noqa: SLF001
            sample_id="proof-explicit-workstream",
        ),
        repo_root=repo_root,
        mode="odylith_on",
    )

    assert summary["delegate"] is False
    assert summary["mode"] == "local_only"
    assert "execution-engine-critical-path" in summary.get("local_only_reasons", [])


def test_live_explicit_workstream_packet_keeps_docs_bounded(monkeypatch: pytest.MonkeyPatch) -> None:
    repo_root = REPO_ROOT
    monkeypatch.setattr(runner, "_prime_benchmark_runtime_cache", lambda *, repo_root: None)
    runner._prepare_benchmark_runtime_cache(repo_root=repo_root, cache_profile="warm")  # noqa: SLF001
    scenarios = runner.load_benchmark_scenarios(repo_root=repo_root)
    scenario = next(row for row in scenarios if row["scenario_id"] == "wave3-explicit-workstream")
    existing_paths = runner._existing_repo_paths(repo_root=repo_root, paths=scenario.get("changed_paths", []))  # noqa: SLF001

    packet_source, payload, _adaptive = runner._build_packet_payload(  # noqa: SLF001
        repo_root=repo_root,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=existing_paths,
    )

    assert packet_source == "governance_slice"
    assert payload.get("docs") in (None, [])


def test_execution_engine_router_recovery_packet_fixture_drives_truthful_recover_posture() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(
        row
        for row in scenarios
        if row["scenario_id"] == "execution-engine-router-recovery-posture"
    )

    result = runner._packet_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    packet = dict(result["packet"])
    assert result["expectation_ok"] is True
    assert packet["packet_kind"] == "impact"
    assert packet["route_ready"] is False
    assert packet["native_spawn_ready"] is False
    assert packet["execution_engine_mode"] == "recover"
    assert packet["execution_engine_next_move"] == "recover.current_blocker"
    assert packet["execution_engine_current_phase"] == "status synthesis"
    assert packet["execution_engine_closure"] == "incomplete"
    assert packet["execution_engine_validation_archetype"] == "recover"
    assert packet["execution_engine_component_id"] == "execution-engine"
    assert packet["execution_engine_canonical_component_id"] == "execution-engine"
    assert packet["execution_engine_identity_status"] == "canonical"
    assert packet["execution_engine_target_component_status"] == "execution_engine_plus_related"
    assert packet["execution_engine_snapshot_reuse_status"] == "built"


def test_execution_engine_packet_expectations_hard_gate_identity_fields() -> None:
    packet = {
        "execution_engine_present": True,
        "execution_engine_outcome": "admit",
        "execution_engine_mode": "verify",
        "execution_engine_next_move": "verify.selected_matrix",
        "execution_engine_closure": "incomplete",
        "execution_engine_component_id": "execution-engine",
        "execution_engine_canonical_component_id": "execution-engine",
        "execution_engine_identity_status": "canonical",
        "execution_engine_target_component_status": "missing",
        "execution_engine_snapshot_reuse_status": "built",
    }

    matched, details = store._packet_satisfies_evaluation_expectations(  # noqa: SLF001
        packet,
        {
            "execution_engine_outcome": ["admit"],
            "execution_engine_mode": ["verify"],
            "execution_engine_next_move": ["verify.selected_matrix"],
            "execution_engine_closure": ["incomplete"],
            "execution_engine_component_id": ["execution-engine"],
            "execution_engine_canonical_component_id": ["execution-engine"],
            "execution_engine_identity_status": ["canonical"],
            "execution_engine_target_component_status": ["execution_engine"],
            "execution_engine_snapshot_reuse_status": ["built"],
        },
    )

    assert matched is False
    assert details["observed_execution_engine_target_component_status"] == "missing"
    assert details["expected_execution_engine_target_component_status"] == ["execution_engine"]


def test_execution_engine_runtime_surface_packet_fixture_keeps_phase_truth() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(
        row
        for row in scenarios
        if row["scenario_id"] == "execution-engine-runtime-surface-phase-carry-through"
    )

    result = runner._packet_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    packet = dict(result["packet"])
    assert result["expectation_ok"] is True
    assert packet["execution_engine_mode"] == "verify"
    assert packet["execution_engine_current_phase"] == "verify"
    assert packet["execution_engine_closure"] == "incomplete"
    assert packet["execution_engine_next_move"] == "verify.selected_matrix"
    assert packet["execution_engine_resume_token"] == "resume:governance_slice"
    assert packet["execution_engine_validation_archetype"] == "verify"
    assert packet["execution_engine_authoritative_lane"] == "context_engine.governance_slice.authoritative"
    assert packet["execution_engine_component_id"] == "execution-engine"
    assert packet["execution_engine_canonical_component_id"] == "execution-engine"
    assert packet["execution_engine_identity_status"] == "canonical"
    assert packet["execution_engine_target_component_status"] == "execution_engine"
    assert packet["execution_engine_snapshot_reuse_status"] == "built"


def test_execution_engine_governance_slice_ambiguity_uses_narrowing_lane() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(
        row
        for row in scenarios
        if row["scenario_id"] == "execution-engine-governance-slice-ambiguity-recovery"
    )

    result = runner._packet_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    packet = dict(result["packet"])
    assert result["expectation_ok"] is True
    assert packet["packet_kind"] == "governance_slice"
    assert packet["selection_state"] == "none"
    assert packet["execution_engine_authoritative_lane"] == "context_engine.governance_slice.narrowing"


def test_live_corpus_workstream_ids_exist_in_repo_truth() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    referenced = {
        str(row.get("workstream", "")).strip()
        for row in scenarios
        if str(row.get("workstream", "")).strip()
    }

    assert referenced == {
        "B-001",
        "B-005",
        "B-012",
        "B-014",
        "B-016",
        "B-018",
        "B-020",
        "B-021",
        "B-022",
        "B-025",
        "B-027",
        "B-028",
        "B-030",
        "B-031",
        "B-063",
        "B-062",
        "B-067",
        "B-072",
        "B-092",
        "B-093",
        "B-073",
        "B-074",
        "B-078",
        "B-100",
        "B-101",
            "B-102",
            "B-110",
        }


def test_select_impacted_diagrams_prefers_direct_benchmark_proof_lane() -> None:
    diagrams = store.select_impacted_diagrams(
        repo_root=REPO_ROOT,
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
            "tests/unit/runtime/test_validate_component_registry_contract.py",
            "tests/unit/runtime/test_render_mermaid_catalog.py",
        ],
        runtime_mode="local",
    )

    assert [row["diagram_id"] for row in diagrams] == ["D-024"]
    assert diagrams[0]["source_mmd"] == "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd"


def test_component_governance_hot_path_keeps_exact_governed_slice_grounded(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_codex_host_runtime(monkeypatch)

    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    route = dict(context_packet["route"])
    governance_signal = governance_signal_codec.expand_governance_signal(dict(route["governance"]))
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert route["route_ready"] is True
    assert route["native_spawn_ready"] is True
    assert payload.get("narrowing_guidance") is None
    assert payload.get("fallback_scan") is None
    assert governance_signal["primary_workstream_id"] == "B-020"
    assert governance_signal["primary_component_id"] == "benchmark"
    assert payload["docs"][0] == "odylith/atlas/source/catalog/diagrams.v1.json"
    assert "README.md" not in payload["docs"]
    assert "odylith/MAINTAINER_RELEASE_RUNBOOK.md" not in payload["docs"]
    assert "architecture_audit" not in payload
    assert path_bundle_codec.expand_path_rows(payload["changed_paths"]) == scenario["changed_paths"]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))
    assert context_packet.get("selection") is None
    assert context_packet.get("packet_kind") is None
    assert context_packet["packet_quality"] == {"rc": "high", "i": "implementation", "m": "write_execution"}
    assert context_packet["selection_state"] == "x:B-020"
    assert context_packet["retrieval_plan"]["ambiguity_class"] == "resolved"


def test_component_governance_hot_path_skips_architecture_audit_for_doc_only_benchmark_slice(
    monkeypatch,  # noqa: ANN001
) -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    def _fail_architecture_audit(**kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("doc-only component governance hot path should not build an architecture audit")

    monkeypatch.setattr(store, "build_architecture_audit", _fail_architecture_audit)

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert payload["docs"] == ["odylith/atlas/source/catalog/diagrams.v1.json"]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_component_governance_full_packet_does_not_recommend_widening_for_exact_slice() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    payload = store.build_governance_slice(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        workstream=str(scenario.get("workstream", "")).strip(),
        component="benchmark",
        runtime_mode="local",
        delivery_profile="full",
        family_hint=str(scenario.get("family", "")).strip(),
        intent=str(scenario.get("intent", "")).strip(),
        validation_command_hints=[
            str(token).strip()
            for token in scenario.get("validation_commands", [])
            if str(token).strip()
        ],
    )

    assert payload["full_scan_recommended"] is False
    assert payload["selection_state"] == "explicit"


def test_component_governance_hot_path_stays_grounded_for_orchestration_adoption() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    _, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    decision = runner._safe_orchestration_summary(  # noqa: SLF001
        request_payload=runner._orchestration_request_payload(  # noqa: SLF001
            scenario=scenario,
            packet_payload=payload,
        ),
        repo_root=REPO_ROOT,
        mode="odylith_on",
    )

    adoption = dict(decision.get("odylith_adoption", {}))
    assert adoption["grounded"] is True
    assert adoption["full_scan_recommended"] is False
    assert adoption["requires_widening"] is False


def test_component_honesty_governance_hot_path_stays_route_ready(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_codex_host_runtime(monkeypatch)

    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-honesty-governance")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    route = dict(payload["context_packet"]["route"])
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert route["route_ready"] is True
    assert route["native_spawn_ready"] is True
    assert payload.get("narrowing_guidance") is None
    assert payload.get("fallback_scan") is None
    assert path_bundle_codec.expand_path_rows(payload.get("changed_paths", [])) == scenario["changed_paths"]
    assert payload["docs"] == [
        "odylith/registry/source/component_registry.v1.json",
        "docs/benchmarks/README.md",
        "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
    ]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_consumer_install_governance_hot_path_keeps_install_contract_companions() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "consumer-install-upgrade-runtime-contract")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert scenario["allow_noop_completion"] is True
    assert set(
        [
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
            "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        ]
    ).issubset(set(payload["docs"]))
    assert path_bundle_codec.expand_path_rows(payload.get("changed_paths", [])) == scenario["changed_paths"]
    assert payload["context_packet"]["anchors"].get("changed_paths") is None
    assert set(
        [
            "src/odylith/install/manager.py",
            "src/odylith/install/runtime.py",
            "tests/integration/install/test_manager.py",
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
            "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        ]
    ).issubset(set(observed_paths))


def test_context_engine_daemon_security_hot_path_keeps_context_contract_companions() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "context-engine-daemon-security-hardening")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py"
    ]
    assert payload["docs"] == [
        "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
        "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    ]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_component_governance_hot_path_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "odylith validate component-registry --repo-root .",
        "odylith atlas render --repo-root . --check-only",
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_validate_component_registry_contract.py tests/unit/runtime/test_render_mermaid_catalog.py",
    ]


def test_component_honesty_governance_hot_path_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-honesty-governance")

    assert scenario["allow_noop_completion"] is True


def test_compass_freshness_hot_path_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "compass-brief-freshness-and-reactivity")

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py"
    ]


def test_consumer_profile_hot_path_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "consumer-profile-truth-root-compatibility")

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_consumer_profile.py"
    ]


def test_live_preflight_evidence_hot_path_declares_focused_check_and_timeout_budget() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(
        row for row in scenarios if row["scenario_id"] == "live-preflight-evidence-disposable-workspace-contract"
    )

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_live_execution.py::test_run_live_scenario_records_declared_preflight_evidence_and_observed_path_sources tests/unit/runtime/test_odylith_benchmark_runner.py::test_fairness_findings_require_raw_prompt_visible_path_attribution_for_raw_lane"
    ]
    assert scenario["live_timeout_seconds"] == 420.0


def test_governed_surface_sync_hot_path_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "closeout-surface-path-normalization")

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_sync_cli_compat.py::test_governed_surface_closeout_path_truth_stays_normalized_across_runtime_readers",
    ]


def test_live_workspace_snapshot_paths_include_focused_local_check_validator_targets(
    tmp_path: Path,
) -> None:
    repo_root = tmp_path
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    changed = repo_root / "odylith" / "surfaces" / "GOVERNANCE_SURFACES.md"
    focused_test = repo_root / "tests" / "unit" / "runtime" / "test_sync_cli_compat.py"
    for path in (changed, focused_test):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# file\n", encoding="utf-8")

    def _fake_run(command, cwd, text, capture_output, check):  # type: ignore[no-untyped-def]
        del cwd, text, capture_output, check
        stdout = ""
        if command[:4] == ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB"]:
            stdout = "odylith/surfaces/GOVERNANCE_SURFACES.md"
        elif command[:3] == ["git", "ls-files", "--others"]:
            stdout = "tests/unit/runtime/test_sync_cli_compat.py"
        return subprocess.CompletedProcess(args=command, returncode=0, stdout=stdout, stderr="")

    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(runner.subprocess, "run", _fake_run)
        paths = runner._live_workspace_snapshot_paths(  # noqa: SLF001
            repo_root=repo_root,
            scenario={
                "changed_paths": ["odylith/surfaces/GOVERNANCE_SURFACES.md"],
                "required_paths": ["odylith/surfaces/GOVERNANCE_SURFACES.md"],
                "validation_commands": ["odylith sync --repo-root . --check-only"],
                "focused_local_checks": [
                    "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_sync_cli_compat.py::test_governed_surface_closeout_path_truth_stays_normalized_across_runtime_readers"
                ],
            },
            prompt_payload={},
        )

    assert "tests/unit/runtime/test_sync_cli_compat.py" in paths


def test_install_agent_activation_governance_hot_path_keeps_spawn_contract_companions() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "install-time-agent-activation-contract")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert set(
        [
            "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
            "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        ]
    ).issubset(set(payload["docs"]))
    assert set(
        [
            "src/odylith/install/agents.py",
            "src/odylith/install/manager.py",
            "tests/unit/install/test_agents.py",
            "odylith/AGENTS.md",
            "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
            "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        ]
    ).issubset(set(observed_paths))


def test_cross_surface_governance_sync_hot_path_keeps_registry_and_workstream_truth() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "cross-surface-governance-sync-truth")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "governance_slice"
    assert payload["docs"] == [
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/registry/source/component_registry.v1.json",
        "odylith/radar/source/ideas/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md",
    ]
    assert path_bundle_codec.expand_path_rows(payload.get("changed_paths", [])) == scenario["changed_paths"]
    assert payload["context_packet"]["anchors"].get("changed_paths") is None
    assert payload["context_packet"].get("selection") is None
    assert payload["context_packet"].get("packet_kind") is None
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_release_benchmark_publication_hot_path_keeps_required_benchmark_spec_visible() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "release-benchmark-publication-proof")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )
    prompt_payload = dict(prepared["prompt_payload"])
    observed_paths = {
        *runner._observed_packet_paths(payload),  # noqa: SLF001
        *odylith_benchmark_live_diagnostics.prompt_payload_observed_paths(
            prompt_payload=prompt_payload,
        ),
    }

    assert packet_source == "governance_slice"
    assert path_bundle_codec.expand_path_rows(payload["changed_paths"]) == scenario["changed_paths"]
    assert prompt_payload["docs"][:4] == [
        "docs/benchmarks/release-baselines.v1.json",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "docs/benchmarks/METRICS_AND_PRIORITIES.md",
        "odylith/README.md",
    ]
    assert prompt_payload["context_packet"]["anchors"]["explicit_paths"] == [
        "README.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/MAINTAINER_RELEASE_RUNBOOK.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/METRICS_AND_PRIORITIES.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "docs/benchmarks/release-baselines.v1.json",
        "odylith/README.md",
        "odylith/maintainer/AGENTS.md",
    ]
    assert payload["context_packet"].get("selection") is None
    assert payload["context_packet"].get("packet_kind") is None
    assert set(scenario["required_paths"]).issubset(observed_paths)


def test_publication_benchmark_scenarios_use_bounded_validation_commands() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    proof = next(row for row in scenarios if row["scenario_id"] == "release-benchmark-publication-proof")
    raw = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-publication-contract")

    assert proof["validation_commands"] == [
        "PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir .tmp-benchmark-publication-proof-graphs",
        "PYTHONPATH=src .venv/bin/pytest -q --basetemp=./.tmp-pytest-benchmark-publication-proof -o cache_dir=./.tmp-pytest-cache-benchmark-publication-proof tests/unit/runtime/test_odylith_benchmark_runner.py::test_release_benchmark_publication_hot_path_keeps_required_benchmark_spec_visible tests/unit/runtime/test_odylith_benchmark_runner.py::test_release_publication_packet_keeps_graph_renderer_grounded tests/unit/runtime/test_odylith_benchmark_runner.py::test_release_publication_hot_path_uses_light_supporting_evidence_profile tests/unit/runtime/test_odylith_benchmark_runner.py::test_release_publication_hot_path_uses_light_component_detail_lookup tests/unit/runtime/test_odylith_benchmark_runner.py::test_release_publication_hot_path_docs_keep_graph_renderer_without_leaking_into_component_governance tests/unit/runtime/test_odylith_benchmark_graphs.py::test_render_graph_assets_prefers_published_conservative_view tests/unit/runtime/test_odylith_benchmark_graphs.py::test_scenario_rows_normalize_public_odylith_off_alias tests/unit/runtime/test_hygiene.py::test_benchmark_honest_baseline_contract_stays_explicit",
    ]
    assert raw["validation_commands"] == [
        "PYTHONPATH=src .venv/bin/pytest -q --basetemp=./.tmp-pytest-benchmark-publication-raw -o cache_dir=./.tmp-pytest-cache-benchmark-publication-raw tests/unit/runtime/test_hygiene.py::test_benchmark_honest_baseline_contract_stays_explicit tests/unit/runtime/test_odylith_benchmark_graphs.py::test_render_graph_assets_prefers_published_conservative_view tests/unit/runtime/test_odylith_benchmark_graphs.py::test_scenario_rows_normalize_public_odylith_off_alias"
    ]


def test_build_packet_payload_supports_bootstrap_session_source(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_bootstrap(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {"bootstrapped_at": "2026-03-31T00:00:00Z", "changed_paths": list(kwargs["changed_paths"])}

    monkeypatch.setattr(runner.store, "build_session_bootstrap", _fake_bootstrap)

    packet_source, payload, adaptive = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "bootstrap-case",
            "family": "broad_shared_scope",
            "packet_source": "bootstrap_session",
            "changed_paths": ["AGENTS.md", "odylith/AGENTS.md"],
            "validation_commands": ["pytest -q tests/unit/runtime/test_context_grounding_hardening.py"],
            "intent": "bootstrap benchmark",
            "workstream": "",
        },
        mode="odylith_on",
        existing_paths=["AGENTS.md", "odylith/AGENTS.md"],
    )

    assert packet_source == "bootstrap_session"
    assert payload["changed_paths"] == ["AGENTS.md", "odylith/AGENTS.md"]
    assert adaptive["stage"] == "bootstrap_session"
    assert captured["use_working_tree"] is False
    assert captured["delivery_profile"] == "agent_hot_path"
    assert captured["retain_impact_internal_context"] is False
    assert captured["skip_impact_runtime_warmup"] is True


def test_build_packet_payload_supports_session_brief_source(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def _fake_session_brief(**kwargs):  # noqa: ANN001
        captured.update(kwargs)
        return {"changed_paths": list(kwargs["changed_paths"])}

    monkeypatch.setattr(runner.store, "build_session_brief", _fake_session_brief)

    packet_source, payload, adaptive = runner._build_packet_payload(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "session-brief-case",
            "family": "exact_path_ambiguity",
            "packet_source": "session_brief",
            "changed_paths": ["src/app/router.py"],
            "validation_commands": ["pytest -q tests/unit/app/test_router.py"],
            "intent": "session brief benchmark",
            "workstream": "",
        },
        mode="odylith_on",
        existing_paths=["src/app/router.py"],
    )

    assert packet_source == "session_brief"
    assert payload["changed_paths"] == ["src/app/router.py"]
    assert adaptive["stage"] == "session_brief"
    assert captured["use_working_tree"] is False
    assert captured["delivery_profile"] == "agent_hot_path"
    assert captured["retain_impact_internal_context"] is False
    assert captured["skip_impact_runtime_warmup"] is True


def test_compass_freshness_hot_path_keeps_surface_contract_companions() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "compass-brief-freshness-and-reactivity")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert payload["docs"] == [
        "odylith/registry/source/components/compass/CURRENT_SPEC.md",
        "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
    ]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_browser_reliability_hot_path_keeps_rendered_surface_companions() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "shell-and-compass-browser-reliability")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert payload["docs"] == ["odylith/index.html", "odylith/compass/compass.html"]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))


def test_architecture_install_runtime_boundary_keeps_contract_reads_grounded() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-release-install-runtime-boundary")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_misses"] == []
    assert result["required_path_precision"] == 1.0
    assert result["hallucinated_surfaces"] == []
    assert result["expectation_ok"] is True


def test_architecture_benchmark_publication_lane_keeps_release_publication_reads_grounded() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-benchmark-proof-publication-lane")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_misses"] == []
    assert result["required_path_precision"] == 1.0
    assert result["hallucinated_surfaces"] == []
    assert result["expectation_ok"] is True


def test_architecture_honest_baseline_contract_keeps_publication_surfaces_grounded() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-benchmark-honest-baseline-contract")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_precision"] == 1.0
    assert result["required_path_misses"] == []
    assert result["hallucinated_surfaces"] == []
    assert result["expectation_ok"] is True


def test_architecture_self_grounding_keeps_doc_only_slice_precise() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-odylith-self-grounding")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_precision"] == 1.0
    assert result["required_path_misses"] == []
    assert result["hallucinated_surfaces"] == []
    assert result["expectation_ok"] is True
    assert result["dossier"].get("required_reads") in (None, [])


def test_packet_result_latency_excludes_benchmark_trace_bookkeeping(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    perf_samples = iter((10.0, 10.007, 10.021))

    monkeypatch.setattr(runner.time, "perf_counter", lambda: next(perf_samples))
    monkeypatch.setattr(runner, "_existing_repo_paths", lambda **kwargs: list(kwargs["paths"]))  # noqa: ANN001
    monkeypatch.setattr(runner, "_recent_reasoning_timing_index", lambda **kwargs: {})  # noqa: ANN001
    monkeypatch.setattr(
        runner,
        "_build_packet_payload",
        lambda **kwargs: (  # noqa: ANN001
            "impact",
            {"changed_paths": list(kwargs["existing_paths"]), "context_packet": {"route": {}}},
            {},
        ),
    )

    def _fake_timing_trace(**kwargs):  # noqa: ANN001
        runner.time.perf_counter()
        return {"operations": {}}

    monkeypatch.setattr(runner, "_timing_trace", _fake_timing_trace)
    monkeypatch.setattr(store, "_packet_summary_from_bootstrap_payload", lambda payload: {})  # noqa: ANN001
    monkeypatch.setattr(store, "_packet_satisfies_evaluation_expectations", lambda *args, **kwargs: (True, {}))  # noqa: ANN001
    monkeypatch.setattr(runner, "_observed_packet_paths", lambda payload: list(payload.get("changed_paths", [])))  # noqa: ANN001
    monkeypatch.setattr(runner, "_orchestration_request_payload", lambda **kwargs: {"candidate_paths": []})  # noqa: ANN001
    monkeypatch.setattr(runner, "_safe_orchestration_summary", lambda **kwargs: {"delegate": False})  # noqa: ANN001
    monkeypatch.setattr(runner, "_packet_token_breakdown", lambda **kwargs: {"packet_source": "impact"})  # noqa: ANN001

    result = runner._packet_result(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "synthetic-packet",
            "label": "Synthetic packet benchmark",
            "prompt": "Keep the packet benchmark tight.",
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "required_paths": [],
            "critical_paths": [],
            "acceptance_criteria": [],
            "validation_commands": [],
            "expect": {},
            "needs_write": False,
        },
        mode="odylith_on",
    )

    assert result["latency_ms"] == 7.0
    assert result["uninstrumented_overhead_ms"] == 7.0


def test_release_publication_packet_keeps_graph_renderer_grounded() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-publication-contract")

    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )
    prompt_payload = dict(prepared["prompt_payload"])
    observed_paths = set(
        odylith_benchmark_live_diagnostics.prompt_payload_observed_paths(prompt_payload=prompt_payload)
    )

    assert prompt_payload["docs"][:5] == [
        "README.md",
        "docs/benchmarks/README.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
    ]
    assert "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py" in observed_paths
    assert set(scenario["required_paths"]).issubset(observed_paths)


def test_raw_prompt_visible_paths_extracts_repo_paths(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")
    docs_readme = tmp_path / "docs" / "benchmarks" / "README.md"
    docs_readme.parent.mkdir(parents=True, exist_ok=True)
    docs_readme.write_text("benchmarks\n", encoding="utf-8")

    observed = runner._raw_prompt_visible_paths(  # noqa: SLF001
        repo_root=tmp_path,
        raw_prompt={
            "prompt": "Update `README.md` and `docs/benchmarks/README.md`, but do not touch `raw_agent_baseline`.",
            "acceptance_criteria": [],
        },
    )

    assert observed == ["README.md", "docs/benchmarks/README.md"]


def test_comparison_contract_details_describe_full_product_live_pair() -> None:
    details = runner._comparison_contract_details(runner.LIVE_COMPARISON_CONTRACT)  # noqa: SLF001

    assert details["primary_claim"] == runner.LIVE_COMPARISON_CONTRACT
    assert "grounding_packet" in details["odylith_on_affordances"]
    assert "execution_engine_posture_and_truthful_next_move" in details["odylith_on_affordances"]
    assert "preflight_focused_check_results_when_executed_in_disposable_workspace" in details["odylith_on_affordances"]
    assert "raw_prompt_visible_repo_anchors_only" in details["raw_agent_affordances"]


def test_fairness_findings_require_raw_prompt_visible_path_attribution_for_raw_lane(tmp_path: Path) -> None:
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")

    findings = runner._fairness_findings(  # noqa: SLF001
        repo_root=tmp_path,
        comparison_contract=runner.LIVE_COMPARISON_CONTRACT,
        published_scenarios=[
            {
                "scenario_id": "case-a",
                "prompt": "Only touch `README.md`.",
                "acceptance_criteria": [],
                "results": [
                    {
                        "mode": "raw_agent_baseline",
                        "observed_path_sources": [],
                        "preflight_evidence_mode": "",
                    }
                ],
            }
        ],
    )

    assert findings == ["case-a/raw_agent_baseline is missing raw prompt-visible path attribution"]


def test_fairness_findings_allow_empty_preflight_mode_for_odylith_on(tmp_path: Path) -> None:
    findings = runner._fairness_findings(  # noqa: SLF001
        repo_root=tmp_path,
        comparison_contract=runner.LIVE_COMPARISON_CONTRACT,
        published_scenarios=[
            {
                "scenario_id": "case-a",
                "prompt": "Audit the benchmark runner.",
                "acceptance_criteria": [],
                "results": [
                    {
                        "mode": "odylith_on",
                        "observed_path_sources": ["odylith_prompt_payload"],
                    }
                ],
            }
        ],
    )

    assert findings == []


def test_corpus_composition_requires_serious_floor_and_full_coverage() -> None:
    composition = runner._corpus_composition(  # noqa: SLF001
        scenarios=[
            {
                "kind": "packet",
                "family": "validation_heavy_fix",
                "needs_write": True,
                "validation_commands": ["pytest -q"],
                "correctness_critical": True,
            }
        ],
        available_scenarios=[
            {
                "kind": "packet",
                "family": "validation_heavy_fix",
                "needs_write": True,
                "validation_commands": ["pytest -q"],
                "correctness_critical": True,
            },
            {
                "kind": "packet",
                "family": "api_contract_evolution",
                "needs_write": True,
                "validation_commands": ["pytest -q"],
                "correctness_critical": False,
            },
        ],
    )

    assert composition["seriousness_floor_passed"] is False
    assert composition["full_corpus_selected"] is False
    assert any("implementation_scenario_count=1" in finding for finding in composition["findings"])
    assert any("required serious families missing" in finding for finding in composition["findings"])
    assert any("published selection covers 1/2 tracked scenarios" in finding for finding in composition["findings"])


def test_packet_result_scores_prompt_visible_paths_for_raw_agent_baseline(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    (tmp_path / "README.md").write_text("readme\n", encoding="utf-8")
    docs_readme = tmp_path / "docs" / "benchmarks" / "README.md"
    docs_readme.parent.mkdir(parents=True, exist_ok=True)
    docs_readme.write_text("benchmarks\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_recent_reasoning_timing_index", lambda **kwargs: {})  # noqa: ANN001
    monkeypatch.setattr(store, "_packet_summary_from_bootstrap_payload", lambda payload: {})  # noqa: ANN001
    monkeypatch.setattr(store, "_packet_satisfies_evaluation_expectations", lambda *args, **kwargs: (False, {}))  # noqa: ANN001
    monkeypatch.setattr(runner, "_observed_packet_paths", lambda payload: [])  # noqa: ANN001
    monkeypatch.setattr(runner, "_orchestration_request_payload", lambda **kwargs: {"candidate_paths": []})  # noqa: ANN001
    monkeypatch.setattr(runner, "_packet_token_breakdown", lambda **kwargs: {"packet_source": "raw_agent_baseline"})  # noqa: ANN001

    result = runner._packet_result(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "raw-prompt-visible-paths",
            "label": "Raw prompt visible paths",
            "prompt": "Repair only `README.md` and `docs/benchmarks/README.md`.",
            "changed_paths": ["README.md", "docs/benchmarks/README.md"],
            "required_paths": ["README.md", "docs/benchmarks/README.md"],
            "critical_paths": [],
            "acceptance_criteria": [],
            "validation_commands": [],
            "expect": {},
            "needs_write": False,
        },
        mode="raw_agent_baseline",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_precision"] == 1.0
    assert result["observed_paths"] == ["README.md", "docs/benchmarks/README.md"]


def test_packet_result_scores_supplemented_prompt_docs_for_odylith_on(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    changed_path = tmp_path / "src" / "odylith" / "runtime" / "common" / "consumer_profile.py"
    changed_path.parent.mkdir(parents=True, exist_ok=True)
    changed_path.write_text("def load_profile():\n    return {}\n", encoding="utf-8")
    test_path = tmp_path / "tests" / "unit" / "runtime" / "test_consumer_profile.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_profile():\n    assert True\n", encoding="utf-8")
    agents_path = tmp_path / "odylith" / "AGENTS.md"
    agents_path.parent.mkdir(parents=True, exist_ok=True)
    agents_path.write_text("scope\n", encoding="utf-8")
    odylith_spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "odylith" / "CURRENT_SPEC.md"
    odylith_spec_path.parent.mkdir(parents=True, exist_ok=True)
    odylith_spec_path.write_text("odylith spec\n", encoding="utf-8")
    registry_spec_path = tmp_path / "odylith" / "registry" / "source" / "components" / "registry" / "CURRENT_SPEC.md"
    registry_spec_path.parent.mkdir(parents=True, exist_ok=True)
    registry_spec_path.write_text("registry spec\n", encoding="utf-8")

    monkeypatch.setattr(runner, "_recent_reasoning_timing_index", lambda **kwargs: {})  # noqa: ANN001
    monkeypatch.setattr(runner, "_timing_trace", lambda **kwargs: {})  # noqa: ANN001
    monkeypatch.setattr(
        runner,
        "_build_packet_payload",
        lambda **kwargs: (  # noqa: ANN001
            "impact",
            {
                "context_packet": {
                    "anchors": {
                        "changed_paths": [
                            "src/odylith/runtime/common/consumer_profile.py",
                            "tests/unit/runtime/test_consumer_profile.py",
                        ]
                    }
                }
            },
            {},
        ),
    )
    monkeypatch.setattr(store, "_packet_summary_from_bootstrap_payload", lambda payload: {})  # noqa: ANN001
    monkeypatch.setattr(store, "_packet_satisfies_evaluation_expectations", lambda *args, **kwargs: (True, {}))  # noqa: ANN001
    monkeypatch.setattr(runner, "_orchestration_request_payload", lambda **kwargs: {"candidate_paths": kwargs["scenario"]["changed_paths"]})  # noqa: ANN001
    monkeypatch.setattr(
        runner,
        "_safe_orchestration_summary",
        lambda **kwargs: {"native_mode": "local_only", "mode": "local_only", "delegate": False, "leaf_count": 0, "native_leaf_count": 0, "parallel_safety": "local_only", "manual_review_recommended": False, "clamped_no_fanout": False, "local_only_reasons": []},  # noqa: ANN001,E501
    )

    result = runner._packet_result(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "consumer-profile-truth-root-compatibility",
            "label": "Consumer profile truth-root compatibility stays intact",
            "family": "consumer_profile_compatibility",
            "prompt": "Preserve explicit consumer truth roots.",
            "changed_paths": [
                "src/odylith/runtime/common/consumer_profile.py",
                "tests/unit/runtime/test_consumer_profile.py",
            ],
            "required_paths": [
                "src/odylith/runtime/common/consumer_profile.py",
                "tests/unit/runtime/test_consumer_profile.py",
                "odylith/AGENTS.md",
                "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                "odylith/registry/source/components/registry/CURRENT_SPEC.md",
            ],
            "critical_paths": [],
            "acceptance_criteria": [],
            "validation_commands": ["PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_consumer_profile.py"],
            "expect": {},
            "needs_write": True,
        },
        mode="odylith_on",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_precision"] == 1.0
    assert result["selected_doc_count"] == 3
    assert set(result["observed_paths"]) == {
        "src/odylith/runtime/common/consumer_profile.py",
        "tests/unit/runtime/test_consumer_profile.py",
        "odylith/AGENTS.md",
        "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        "odylith/registry/source/components/registry/CURRENT_SPEC.md",
    }


def test_architecture_raw_agent_baseline_scores_prompt_visible_paths(tmp_path: Path) -> None:
    architecture_path = tmp_path / "src" / "odylith" / "runtime" / "evaluation" / "odylith_benchmark_runner.py"
    architecture_path.parent.mkdir(parents=True, exist_ok=True)
    architecture_path.write_text("def render():\n    return None\n", encoding="utf-8")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "architecture-raw-prompt-visible-paths",
            "label": "Architecture raw prompt visible paths",
            "prompt": "Review `src/odylith/runtime/evaluation/odylith_benchmark_runner.py` architecture only.",
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "critical_paths": [],
            "acceptance_criteria": [],
            "validation_commands": [],
            "expect": {},
        },
        mode="raw_agent_baseline",
    )

    assert result["required_path_recall"] == 1.0
    assert result["required_path_precision"] == 1.0
    assert result["observed_paths"] == ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"]


def test_architecture_result_latency_excludes_trace_and_expectation_bookkeeping(monkeypatch, tmp_path: Path) -> None:  # noqa: ANN001
    perf_samples = iter((20.0, 20.005, 20.018))

    monkeypatch.setattr(runner.time, "perf_counter", lambda: next(perf_samples))
    monkeypatch.setattr(runner, "_existing_repo_paths", lambda **kwargs: list(kwargs["paths"]))  # noqa: ANN001
    monkeypatch.setattr(runner, "_recent_reasoning_timing_index", lambda **kwargs: {})  # noqa: ANN001
    monkeypatch.setattr(
        store,
        "build_architecture_audit",
        lambda **kwargs: {  # noqa: ANN001
            "required_reads": list(kwargs["changed_paths"]),
            "linked_components": [],
            "linked_diagrams": [],
            "coverage": {},
            "execution_hint": {},
            "authority_graph": {},
        },
    )

    def _fake_architecture_timing_trace(**kwargs):  # noqa: ANN001
        runner.time.perf_counter()
        return {"operations": {}}

    monkeypatch.setattr(runner, "_timing_trace", _fake_architecture_timing_trace)
    monkeypatch.setattr(runner, "_architecture_expectation_result", lambda **kwargs: (True, {}))  # noqa: ANN001
    monkeypatch.setattr(runner, "_safe_orchestration_summary", lambda **kwargs: {"delegate": False})  # noqa: ANN001
    monkeypatch.setattr(store, "_compact_packet_level_architecture_audit", lambda payload: payload)  # noqa: ANN001

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=tmp_path,
        scenario={
            "scenario_id": "synthetic-architecture",
            "label": "Synthetic architecture benchmark",
            "prompt": "Keep the architecture benchmark tight.",
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "required_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "critical_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "acceptance_criteria": [],
            "validation_commands": [],
            "expect": {},
        },
        mode="odylith_on",
    )

    assert result["latency_ms"] == 5.0
    assert result["uninstrumented_overhead_ms"] == 5.0


def test_release_publication_hot_path_uses_light_supporting_evidence_profile() -> None:
    profile = odylith_context_engine_hot_path_delivery_runtime._impact_family_profile(  # noqa: SLF001
        hot_path=True,
        family_hint="release_publication",
        workstream_hint="B-022",
        component_hint="benchmark",
    )

    assert profile["family"] == "release_publication"
    assert profile["prefer_explicit_workstream"] is True
    assert profile["prefer_explicit_component"] is True
    assert profile["include_notes"] is False
    assert profile["include_bugs"] is False
    assert profile["include_code_neighbors"] is False
    assert profile["include_diagrams"] is False
    assert profile["include_components"] is True
    assert profile["include_tests"] is False


def test_component_governance_hot_path_prefers_explicit_component_over_full_component_scan() -> None:
    profile = odylith_context_engine_hot_path_delivery_runtime._impact_family_profile(  # noqa: SLF001
        hot_path=True,
        family_hint="component_governance",
        workstream_hint="B-020",
        component_hint="benchmark",
    )

    assert profile["family"] == "component_governance"
    assert profile["prefer_explicit_workstream"] is True
    assert profile["prefer_explicit_component"] is True
    assert profile["include_notes"] is False
    assert profile["include_bugs"] is False
    assert profile["include_code_neighbors"] is False
    assert profile["include_diagrams"] is False
    assert profile["include_components"] is True
    assert profile["include_tests"] is False


def test_release_publication_hot_path_uses_light_component_detail_lookup(monkeypatch) -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-publication-contract")
    original = store.load_registry_detail
    seen_detail_levels: list[str] = []

    def _tracked_load_registry_detail(**kwargs):  # noqa: ANN003
        seen_detail_levels.append(str(kwargs.get("detail_level", "full")).strip() or "full")
        return original(**kwargs)

    monkeypatch.setattr(store, "load_registry_detail", _tracked_load_registry_detail)

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )

    assert packet_source == "governance_slice"
    assert store._packet_summary_from_bootstrap_payload(payload)["route_ready"] is True  # noqa: SLF001
    assert seen_detail_levels
    assert set(seen_detail_levels) == {"grounding_light"}


def test_component_governance_packet_exposes_fast_selector_diagnostics() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-component-governance-truth")

    result = runner._packet_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    diagnostics = dict(result.get("selector_diagnostics", {}))
    assert diagnostics["component_fast_selector_used"] is False
    assert diagnostics["component_explicit_short_circuit"] is True
    assert diagnostics["component_selector_candidate_row_count"] == 1


def test_benchmark_runner_gate_hot_path_keeps_reviewer_guide_visible_in_live_prompt_payload() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-runner-gate")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001
    with_docs = runner._packet_token_breakdown(  # noqa: SLF001
        payload=payload,
        packet_source=packet_source,
        mode="odylith_on",
        full_scan={},
    )
    without_docs = runner._packet_token_breakdown(  # noqa: SLF001
        payload={key: value for key, value in payload.items() if key != "docs"},
        packet_source=packet_source,
        mode="odylith_on",
        full_scan={},
    )

    assert packet_source == "impact"
    assert payload["docs"] == [
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "docs/benchmarks/REVIEWER_GUIDE.md",
    ]
    assert set(scenario["required_paths"]).issubset(set(observed_paths))
    assert with_docs["codex_prompt_estimated_tokens"] > without_docs["codex_prompt_estimated_tokens"]
    assert with_docs["prompt_artifact_tokens"]["docs"] > 0
    assert "docs" not in with_docs["operator_diag_artifact_tokens"]


def test_benchmark_runner_gate_hot_path_allows_noop_after_focused_runner_check() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-runner-gate")

    assert scenario["allow_noop_completion"] is True
    assert scenario["focused_local_checks"] == [
        "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py::test_run_benchmarks_publishes_conservative_multi_profile_view"
    ]


def test_run_scenario_mode_passes_selected_docs_to_live_prompt_payload(monkeypatch) -> None:  # noqa: ANN001
    _force_codex_host_runtime(monkeypatch)

    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-runner-gate")
    captured: dict[str, object] = {}

    def _fake_run_live_scenario(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"mode": kwargs["mode"], "status": "completed"}

    monkeypatch.setattr(runner.odylith_benchmark_live_execution, "run_live_scenario", _fake_run_live_scenario)

    result = runner._run_scenario_mode(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    assert result["status"] == "completed"
    assert captured["benchmark_profile"] == runner.BENCHMARK_PROFILE_PROOF
    assert captured["packet_source"] == "impact"
    prompt_payload = captured["prompt_payload"]
    assert isinstance(prompt_payload, dict)
    assert prompt_payload["docs"] == [
        "docs/benchmarks/REVIEWER_GUIDE.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]
    context_packet = prompt_payload["context_packet"]
    assert isinstance(context_packet, dict)
    assert set(context_packet.keys()) >= {"anchors", "packet_state", "retrieval_plan", "route", "selection_state"}
    assert context_packet["anchors"] == {
        "changed_paths": [
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            "tests/unit/runtime/test_odylith_benchmark_runner.py",
        ],
        "has_non_shared_anchor": True,
    }
    assert context_packet["packet_state"] == "compact"
    assert context_packet["retrieval_plan"] == {"selected_counts": "c4d6g4"}
    assert context_packet["route"] == {
        "b": "deep_validation",
        "native_spawn_ready": True,
        "p": "bounded_parallel_candidate",
        "route_ready": True,
    }
    assert context_packet["selection_state"] == "x:B-022"


def test_prepare_live_scenario_request_supplements_bounded_support_docs_for_impact_slice() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "validation-heavy-router-fix")

    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    prompt_payload = prepared["prompt_payload"]
    assert isinstance(prompt_payload, dict)
    assert prompt_payload["strict_boundary"] is True
    assert "docs" not in prompt_payload
    assert "implementation_anchors" not in prompt_payload


def test_prepare_live_scenario_request_preserves_execution_engine_packet_summary() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(
        row
        for row in scenarios
        if row["scenario_id"] == "execution-engine-runtime-surface-phase-carry-through"
    )

    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    packet_summary = dict(prepared["packet_summary"])
    assert packet_summary["packet_kind"] == "governance_slice"
    assert packet_summary["execution_engine_present"] is True
    assert packet_summary["execution_engine_mode"] == "verify"
    assert packet_summary["execution_engine_current_phase"] == "verify"
    assert packet_summary["execution_engine_next_move"] == "verify.selected_matrix"
    assert packet_summary["execution_engine_resume_token"] == "resume:governance_slice"
    assert packet_summary["execution_engine_component_id"] == "execution-engine"
    assert packet_summary["execution_engine_canonical_component_id"] == "execution-engine"
    assert packet_summary["execution_engine_identity_status"] == "canonical"
    assert packet_summary["execution_engine_target_component_status"] == "execution_engine"
    assert packet_summary["execution_engine_snapshot_reuse_status"] == "built"


def test_prepare_live_scenario_request_adds_architecture_component_anchors() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-odylith-self-grounding")

    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
    )

    prompt_payload = prepared["prompt_payload"]
    assert isinstance(prompt_payload, dict)
    audit = dict(prompt_payload["architecture_audit"])
    assert audit["strict_boundary"] is True
    assert "implementation_anchors" not in audit
    assert "required_reads" not in audit


def test_prepare_live_scenario_request_keeps_architecture_honest_baseline_support_docs_fail_closed() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-benchmark-honest-baseline-contract")

    prepared = runner._prepare_live_scenario_request(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_QUICK,
    )

    prompt_payload = prepared["prompt_payload"]
    assert isinstance(prompt_payload, dict)
    audit = dict(prompt_payload["architecture_audit"])
    assert audit["required_reads"] == [
        "docs/benchmarks/README.md",
        "README.md",
        "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
    ]
    assert "odylith/MAINTAINER_RELEASE_RUNBOOK.md" not in audit["required_reads"]
    assert "odylith/registry/source/components/atlas/CURRENT_SPEC.md" not in audit["required_reads"]


def test_run_scenario_mode_uses_local_packet_path_on_diagnostic_profile() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "benchmark-raw-baseline-runner-gate")

    result = runner._run_scenario_mode(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        benchmark_profile=runner.BENCHMARK_PROFILE_DIAGNOSTIC,
    )

    assert result["kind"] == "packet"
    assert result["packet_source"] in {"impact", "governance_slice", "context_scan", "raw_codex_cli"}
    assert float(result["latency_ms"]) > 0.0
    assert "live_execution" not in result


def test_singleton_family_latency_probes_preserve_diagnostic_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    candidates = runner._sensitive_singleton_latency_probe_candidates(scenarios=scenarios)  # noqa: SLF001
    assert candidates
    captured_profiles: list[str] = []

    def _fake_run_scenario_mode(
        *,
        repo_root: Path,
        scenario: dict[str, object],
        mode: str,
        benchmark_profile: str = runner.BENCHMARK_PROFILE_PROOF,
    ) -> dict[str, object]:
        captured_profiles.append(benchmark_profile)
        return {
            "mode": mode,
            "latency_ms": 12.0,
            "instrumented_reasoning_duration_ms": 8.0,
            "uninstrumented_overhead_ms": 4.0,
            "required_path_precision": 1.0,
            "required_path_recall": 1.0,
            "validation_success_proxy": 1.0,
            "expectation_ok": True,
        }

    monkeypatch.setattr(runner, "_run_scenario_mode", _fake_run_scenario_mode)
    monkeypatch.setattr(runner, "_prepare_benchmark_runtime_cache", lambda *, repo_root, cache_profile: None)

    probes = runner._singleton_family_latency_probes(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenarios=candidates[:1],
        modes=["odylith_on"],
        cache_profiles=["warm"],
        benchmark_profile=runner.BENCHMARK_PROFILE_DIAGNOSTIC,
    )

    assert probes
    assert captured_profiles
    assert set(captured_profiles) == {runner.BENCHMARK_PROFILE_DIAGNOSTIC}


def test_enforce_diagnostic_runtime_hygiene_fails_closed_on_contamination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [1234])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [Path("/tmp/odylith-benchmark-live-test/workspace")])
    cleanup_calls: list[tuple[Path, bool, object]] = []

    def _fake_cleanup(*, repo_root: Path, clear_progress: bool, ignore_progress=None) -> dict[str, object]:  # type: ignore[no-untyped-def]
        cleanup_calls.append((repo_root, clear_progress, ignore_progress))
        return {"process_cleanup": {"terminated_pid_count": 1}, "worktree_cleanup": {"removed_worktree_count": 1}}

    monkeypatch.setattr(runner, "_cleanup_stale_benchmark_state", _fake_cleanup)

    with pytest.raises(RuntimeError, match="diagnostic benchmark contamination detected"):
        runner._enforce_diagnostic_runtime_hygiene(repo_root=REPO_ROOT)  # noqa: SLF001

    assert cleanup_calls == [(REPO_ROOT, False, None)]


def test_bounded_orchestration_summary_uses_inline_fallback_when_spawn_main_is_not_importable(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(sys.modules["__main__"], "__file__", "<stdin>", raising=False)
    monkeypatch.setattr(
        runner,
        "_safe_orchestration_summary",
        lambda **kwargs: {"fallback": True, "mode": kwargs["mode"]},  # type: ignore[arg-type]
    )
    monkeypatch.setattr(
        runner.multiprocessing,
        "get_context",
        lambda _method: (_ for _ in ()).throw(AssertionError("spawn should not be used")),
    )

    summary = runner._bounded_orchestration_summary(  # noqa: SLF001
        request_payload={},
        repo_root=tmp_path,
        mode="odylith_on",
        timeout_seconds=1.0,
    )

    assert summary == {"fallback": True, "mode": "odylith_on"}


def test_cleanup_stale_benchmark_state_removes_runtime_temp_directories(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp"
    temp_root.mkdir(parents=True, exist_ok=True)
    live_dir = temp_root / "odylith-benchmark-live-example"
    codex_dir = temp_root / "odylith-benchmark-codex-example"
    codex_home_dir = temp_root / "odylith-benchmark-codex-home-example"
    analysis_bundle = temp_root / "odylith-benchmark-20260403T000000Z"
    for path in (live_dir, codex_dir, codex_home_dir, analysis_bundle):
        path.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(
        runner,
        "_cleanup_benchmark_worktrees",
        lambda *, repo_root: {"removed_worktree_count": 0, "failed_worktree_count": 0},
    )

    cleanup = runner._cleanup_stale_benchmark_state(repo_root=tmp_path, clear_progress=False)  # noqa: SLF001

    temp_cleanup = cleanup["temp_directory_cleanup"]
    assert temp_cleanup["removed_temp_directory_count"] == 3
    assert not live_dir.exists()
    assert not codex_dir.exists()
    assert not codex_home_dir.exists()
    assert analysis_bundle.exists()


def test_cleanup_stale_benchmark_state_can_ignore_current_active_run_for_final_hygiene(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp"
    codex_dir = temp_root / "odylith-benchmark-codex-current"
    codex_dir.mkdir(parents=True, exist_ok=True)
    progress_payload = {
        "report_id": "report-current",
        "benchmark_profile": runner.BENCHMARK_PROFILE_DIAGNOSTIC,
        "status": "running",
        "shard_index": 1,
        "shard_count": 1,
        "owning_pid": 4242,
        "repo_root": str(tmp_path.resolve()),
    }
    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-current",
        benchmark_profile=runner.BENCHMARK_PROFILE_DIAGNOSTIC,
        shard_index=1,
        shard_count=1,
        owning_pid=4242,
    )
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(progress_payload, indent=2) + "\n", encoding="utf-8")
    runner._write_active_runs(  # noqa: SLF001
        repo_root=tmp_path,
        runs=[{**progress_payload, "progress_path": str(progress_path)}],
    )
    monkeypatch.setattr(runner, "_process_exists", lambda pid: True)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(
        runner,
        "_cleanup_benchmark_worktrees",
        lambda *, repo_root: {"removed_worktree_count": 0, "failed_worktree_count": 0},
    )

    cleanup = runner._cleanup_stale_benchmark_state(  # noqa: SLF001
        repo_root=tmp_path,
        clear_progress=False,
        ignore_progress=progress_payload,
    )

    assert cleanup["progress_cleanup"]["active_run_count"] == 1
    assert cleanup["temp_directory_cleanup"]["removed_temp_directory_count"] == 1
    assert not codex_dir.exists()


def test_cleanup_stale_benchmark_state_sharded_startup_preserves_unowned_runtime(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    temp_root = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp"
    codex_dir = temp_root / "odylith-benchmark-codex-sibling"
    codex_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [codex_dir])

    cleanup = runner._cleanup_stale_benchmark_state(  # noqa: SLF001
        repo_root=tmp_path,
        clear_progress=False,
        allow_destructive_runtime_cleanup=False,
    )

    assert cleanup["progress_cleanup"]["active_runtime_present"] is True
    assert cleanup["process_cleanup"]["skipped_due_to_unowned_sharded_runtime"] is True
    assert cleanup["temp_directory_cleanup"]["skipped_due_to_unowned_sharded_runtime"] is True
    assert codex_dir.exists()


def test_cleanup_benchmark_worktrees_removes_detached_clone_workspace(tmp_path: Path) -> None:
    clone_parent = runner.odylith_benchmark_isolation.benchmark_workspace_parent(  # noqa: SLF001
        repo_root=tmp_path,
        create=True,
    )
    live_dir = clone_parent / "odylith-benchmark-live-example"
    (live_dir / "workspace" / ".git").mkdir(parents=True, exist_ok=True)
    (live_dir / "workspace" / "README.md").write_text("repo\n", encoding="utf-8")

    cleanup = runner._cleanup_benchmark_worktrees(repo_root=tmp_path)  # noqa: SLF001

    assert cleanup["removed_worktree_count"] == 1
    assert str(live_dir.resolve()) in cleanup["removed_worktrees"]
    assert not live_dir.exists()


def test_sync_active_run_progress_keeps_failed_progress_out_of_active_runs(tmp_path: Path) -> None:
    payload = {
        "report_id": "report-1",
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "repo_root": str(tmp_path.resolve()),
        "started_utc": "2026-04-15T00:00:00Z",
        "updated_utc": "2026-04-15T00:00:00Z",
        "status": "running",
        "shard_index": 2,
        "shard_count": 4,
        "owning_pid": 99999,
    }

    runner._sync_active_run_progress(repo_root=tmp_path, payload=payload)  # noqa: SLF001

    active_runs_payload = json.loads(runner.active_runs_path(repo_root=tmp_path).read_text(encoding="utf-8"))  # noqa: SLF001
    assert len(active_runs_payload["runs"]) == 1

    failed_payload = dict(payload)
    failed_payload["status"] = "failed"
    failed_payload["updated_utc"] = "2026-04-15T00:01:00Z"
    runner._sync_active_run_progress(repo_root=tmp_path, payload=failed_payload)  # noqa: SLF001

    assert not runner.active_runs_path(repo_root=tmp_path).exists()  # noqa: SLF001
    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-1",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=2,
        shard_count=4,
        owning_pid=99999,
    )
    stored_progress = json.loads(progress_path.read_text(encoding="utf-8"))
    assert stored_progress["status"] == "failed"


def test_clear_active_run_progress_preserves_progress_when_history_report_is_missing(tmp_path: Path) -> None:
    payload = {
        "report_id": "report-preserve",
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "repo_root": str(tmp_path.resolve()),
        "started_utc": "2026-04-15T00:00:00Z",
        "updated_utc": "2026-04-15T00:01:00Z",
        "status": "running",
        "phase": "executing_scenarios",
        "shard_index": 1,
        "shard_count": 4,
        "owning_pid": 55555,
    }

    runner._sync_active_run_progress(repo_root=tmp_path, payload=payload)  # noqa: SLF001
    runner._clear_active_run_progress(repo_root=tmp_path, payload=payload)  # noqa: SLF001

    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-preserve",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=1,
        shard_count=4,
        owning_pid=55555,
    )
    assert progress_path.exists()
    assert not runner.active_runs_path(repo_root=tmp_path).exists()  # noqa: SLF001


def test_sync_active_run_progress_recovers_running_shards_when_shared_ledger_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shard_one = {
        "report_id": "report-recover-1",
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "repo_root": str(tmp_path.resolve()),
        "started_utc": "2026-04-15T00:00:00Z",
        "updated_utc": "2026-04-15T00:00:00Z",
        "status": "running",
        "shard_index": 1,
        "shard_count": 2,
        "owning_pid": 12345,
    }
    shard_one_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-recover-1",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=1,
        shard_count=2,
        owning_pid=12345,
    )
    shard_one_path.parent.mkdir(parents=True, exist_ok=True)
    shard_one_path.write_text(json.dumps(shard_one, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner, "_process_exists", lambda pid: pid in {12345, 67890})

    shard_two = {
        "report_id": "report-recover-2",
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "repo_root": str(tmp_path.resolve()),
        "started_utc": "2026-04-15T00:00:05Z",
        "updated_utc": "2026-04-15T00:00:05Z",
        "status": "running",
        "shard_index": 2,
        "shard_count": 2,
        "owning_pid": 67890,
    }

    runner._sync_active_run_progress(repo_root=tmp_path, payload=shard_two)  # noqa: SLF001

    active_runs_payload = json.loads(runner.active_runs_path(repo_root=tmp_path).read_text(encoding="utf-8"))  # noqa: SLF001
    assert {row["report_id"] for row in active_runs_payload["runs"]} == {"report-recover-1", "report-recover-2"}


def test_load_benchmark_progress_recovers_from_progress_files_when_active_run_ledger_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = [
        {
            "report_id": "report-progress",
            "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
            "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
            "repo_root": str(tmp_path.resolve()),
            "started_utc": "2026-04-15T00:00:00Z",
            "updated_utc": "2026-04-15T00:00:00Z",
            "status": "running",
            "phase": "executing_scenarios",
            "shard_index": 1,
            "shard_count": 2,
            "scenario_count": 5,
            "total_results": 20,
            "completed_cache_profiles": 0,
            "completed_scenarios": 1,
            "completed_results": 2,
            "owning_pid": 11111,
        },
        {
            "report_id": "report-progress",
            "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
            "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
            "repo_root": str(tmp_path.resolve()),
            "started_utc": "2026-04-15T00:00:01Z",
            "updated_utc": "2026-04-15T00:00:02Z",
            "status": "running",
            "phase": "executing_scenarios",
            "shard_index": 2,
            "shard_count": 2,
            "scenario_count": 6,
            "total_results": 24,
            "completed_cache_profiles": 1,
            "completed_scenarios": 3,
            "completed_results": 10,
            "current_scenario_id": "case-b",
            "owning_pid": 22222,
        },
    ]
    for payload in payloads:
        progress_path = runner._active_run_progress_path(  # noqa: SLF001
            repo_root=tmp_path,
            report_id=str(payload["report_id"]),
            benchmark_profile=str(payload["benchmark_profile"]),
            shard_index=int(payload["shard_index"]),
            shard_count=int(payload["shard_count"]),
            owning_pid=int(payload["owning_pid"]),
        )
        progress_path.parent.mkdir(parents=True, exist_ok=True)
        progress_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(runner, "_process_exists", lambda pid: pid in {11111, 22222})
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [])

    progress = runner.load_benchmark_progress(repo_root=tmp_path)

    assert progress["aggregate_source"] == "active_runs"
    assert progress["active_shard_count"] == 2
    assert progress["active_shard_indices"] == [1, 2]
    assert progress["scenario_count"] == 11
    assert progress["total_results"] == 44
    assert progress["completed_scenarios"] == 4
    assert progress["completed_results"] == 12
    assert progress["current_scenario_id"] == "case-b"


def test_prune_stale_benchmark_progress_synthesizes_failed_report_for_orphaned_progress(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    scenario = {
        "scenario_id": "case-a",
        "kind": "packet",
        "label": "Case A",
        "summary": "A",
        "family": "validation_heavy_fix",
        "priority": "high",
        "changed_paths": ["scripts/a.py"],
        "workstream": "",
        "required_paths": ["scripts/a.py"],
        "validation_commands": [],
        "correctness_critical": False,
        "expect": {"within_budget": True},
    }
    monkeypatch.setattr(runner, "load_benchmark_scenarios", lambda **_: [dict(scenario)])
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [])
    monkeypatch.setattr(runner, "_process_exists", lambda pid: False)
    monkeypatch.setattr(runner, "_utc_now", lambda: "2026-04-15T01:00:00Z")

    payload = {
        "report_id": "report-orphaned",
        "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
        "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
        "repo_root": str(tmp_path.resolve()),
        "started_utc": "2026-04-15T00:00:00Z",
        "updated_utc": "2026-04-15T00:10:00Z",
        "status": "running",
        "phase": "executing_scenarios",
        "modes": ["odylith_on", "raw_agent_baseline"],
        "cache_profiles": ["warm", "cold"],
        "primary_cache_profile": "warm",
        "selection_strategy": "manual_selection",
        "selection": {
            "case_ids": ["case-a"],
            "scenario_ids": ["case-a"],
            "family_filters": [],
            "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
            "profile_default_narrowing": "",
            "selection_strategy": "manual_selection",
            "shard_count": 1,
            "shard_index": 1,
            "default_modes_applied": True,
            "default_cache_profiles_applied": True,
            "limit": 0,
            "full_corpus_selected": False,
            "available_scenario_count": 1,
            "cache_profiles": ["warm", "cold"],
        },
        "shard_index": 1,
        "shard_count": 1,
        "scenario_count": 1,
        "total_results": 4,
        "completed_cache_profiles": 0,
        "completed_scenarios": 0,
        "completed_results": 0,
        "current_cache_profile": "warm",
        "current_mode": "odylith_on",
        "current_scenario_id": "case-a",
        "latest_eligible": False,
        "owning_pid": 42424,
    }
    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-orphaned",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=1,
        shard_count=1,
        owning_pid=42424,
    )
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    cleanup = runner._prune_stale_benchmark_progress(repo_root=tmp_path, clear_shared_progress=False)  # noqa: SLF001

    report_path = runner.history_report_path(repo_root=tmp_path, report_id="report-orphaned")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert cleanup["synthesized_failed_report_count"] == 1
    assert report["status"] == "failed"
    assert report["acceptance"]["status"] == "failed"
    assert not progress_path.exists()


def test_prune_stale_benchmark_progress_removes_failed_active_run_entries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-2",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=1,
        shard_count=4,
        owning_pid=12345,
    )
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("{}", encoding="utf-8")
    runner._write_active_runs(  # noqa: SLF001
        repo_root=tmp_path,
        runs=[
            {
                "report_id": "report-2",
                "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
                "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
                "repo_root": str(tmp_path.resolve()),
                "started_utc": "2026-04-15T00:00:00Z",
                "updated_utc": "2026-04-15T00:01:00Z",
                "status": "failed",
                "shard_index": 1,
                "shard_count": 4,
                "owning_pid": 12345,
                "progress_path": str(progress_path),
            }
        ],
    )
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [])

    cleanup = runner._prune_stale_benchmark_progress(repo_root=tmp_path, clear_shared_progress=False)  # noqa: SLF001

    assert cleanup["removed_active_run_count"] == 1
    assert not progress_path.exists()
    assert not runner.active_runs_path(repo_root=tmp_path).exists()  # noqa: SLF001


def test_prune_stale_benchmark_progress_removes_dead_pid_even_when_other_runtime_artifacts_exist(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    progress_path = runner._active_run_progress_path(  # noqa: SLF001
        repo_root=tmp_path,
        report_id="report-dead",
        benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
        shard_index=1,
        shard_count=4,
        owning_pid=54321,
    )
    progress_path.parent.mkdir(parents=True, exist_ok=True)
    progress_path.write_text("{}", encoding="utf-8")
    runner._write_active_runs(  # noqa: SLF001
        repo_root=tmp_path,
        runs=[
            {
                "report_id": "report-dead",
                "benchmark_profile": runner.BENCHMARK_PROFILE_PROOF,
                "comparison_contract": runner.LIVE_COMPARISON_CONTRACT,
                "repo_root": str(tmp_path.resolve()),
                "started_utc": "2026-04-15T00:00:00Z",
                "updated_utc": "2026-04-15T00:01:00Z",
                "status": "running",
                "shard_index": 1,
                "shard_count": 4,
                "owning_pid": 54321,
                "progress_path": str(progress_path),
            }
        ],
    )
    unrelated_temp_dir = tmp_path / ".odylith" / "runtime" / "odylith-benchmark-temp" / "odylith-benchmark-codex-other"
    unrelated_temp_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(runner, "_benchmark_owned_codex_process_ids", lambda: [])
    monkeypatch.setattr(runner, "_benchmark_temp_worktrees", lambda repo_root: [])
    monkeypatch.setattr(runner, "_benchmark_temp_directories", lambda repo_root: [unrelated_temp_dir])
    monkeypatch.setattr(runner, "_process_exists", lambda pid: False)

    cleanup = runner._prune_stale_benchmark_progress(repo_root=tmp_path, clear_shared_progress=False)  # noqa: SLF001

    assert cleanup["removed_active_run_count"] == 1
    assert cleanup["active_runtime_present"] is True
    assert not progress_path.exists()
    assert not runner.active_runs_path(repo_root=tmp_path).exists()  # noqa: SLF001


def test_run_benchmarks_fails_closed_when_benchmark_runtime_free_space_is_too_low(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    DiskUsage = collections.namedtuple("DiskUsage", ["total", "used", "free"])
    _write_corpus(
        tmp_path,
        {
            "version": "v1",
            "program": {},
            "cases": [
                {
                    "case_id": "case-a",
                    "label": "Case A",
                    "family": "validation_heavy_fix",
                    "priority": "high",
                    "benchmark": {
                        "prompt": "Work case-a.",
                        "paths": ["src/case_a.py"],
                        "required_paths": ["src/case_a.py"],
                        "validation_commands": [],
                        "needs_write": True,
                    },
                    "match": {"paths_any": ["src/case_a.py"]},
                    "expect": {"within_budget": True},
                }
            ],
            "architecture_cases": [],
        },
    )
    monkeypatch.setattr(runner, "_cleanup_stale_benchmark_state", lambda **_: {})
    monkeypatch.setattr(
        runner.shutil,
        "disk_usage",
        lambda path: DiskUsage(
            total=1024 * 1024 * 1024,
            used=1024 * 1024 * 768,
            free=runner._MIN_BENCHMARK_RUNTIME_FREE_BYTES - 1,  # noqa: SLF001
        ),
    )
    monkeypatch.setattr(
        runner,
        "_write_progress",
        lambda **_: (_ for _ in ()).throw(AssertionError("progress should not be written when storage preflight fails")),
    )

    with pytest.raises(RuntimeError, match="benchmark runtime free space is too low"):
        runner.run_benchmarks(
            repo_root=tmp_path,
            benchmark_profile=runner.BENCHMARK_PROFILE_PROOF,
            write_report=False,
        )


def test_benchmark_tree_identity_records_real_head_oid(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / "README.md").write_text("repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    expected_branch = (
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
        .stdout.strip()
    )
    expected_commit = (
        subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            text=True,
            capture_output=True,
            check=True,
        )
        .stdout.strip()
    )

    store._PROCESS_GIT_REF_CACHE.clear()  # noqa: SLF001
    identity = runner.benchmark_tree_identity(repo_root=repo_root, selection={})
    assert identity["git_branch"] == expected_branch
    assert identity["git_commit"] == expected_commit
    assert identity["git_commit"] != identity["git_branch"]


def test_benchmark_tree_identity_fingerprints_existing_snapshot_overlay_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / "README.md").write_text("repo\n", encoding="utf-8")
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "bench.md").write_text("bench\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md", "docs/bench.md"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    identity = runner.benchmark_tree_identity(
        repo_root=repo_root,
        selection={},
        snapshot_paths=["docs/bench.md", "missing.md"],
    )

    assert identity["snapshot_overlay_fingerprint"]


def test_architecture_result_uses_compact_dossier_for_benchmark_payload() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-benchmark-proof-publication-lane")

    result = runner._architecture_result(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
    )

    assert result["architecture_compaction_applied"] is True
    assert "authority_graph" in result["dossier"]
    assert "required_reads" in result["dossier"] or "required_read_count" in result["dossier"]


def test_release_publication_hot_path_docs_keep_graph_renderer_without_leaking_into_component_governance() -> None:
    release_docs = odylith_context_engine_hot_path_governance_runtime._governance_hot_path_docs(  # noqa: SLF001
        repo_root=REPO_ROOT,
        changed_paths=[
            "README.md",
            "docs/benchmarks/README.md",
            "docs/benchmarks/REVIEWER_GUIDE.md",
            "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            "odylith/maintainer/skills/release-benchmark-publishing/SKILL.md",
        ],
        family_hint="release_publication",
        workstream_detail=None,
    )
    assert release_docs is not None
    assert "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py" in release_docs
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" in release_docs
    assert "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md" not in release_docs

    component_docs = odylith_context_engine_hot_path_governance_runtime._governance_hot_path_docs(  # noqa: SLF001
        repo_root=REPO_ROOT,
        changed_paths=[
            "odylith/registry/source/component_registry.v1.json",
            "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
        ],
        family_hint="component_governance",
        workstream_detail=None,
    )
    assert component_docs is not None
    assert "src/odylith/runtime/evaluation/odylith_benchmark_graphs.py" not in component_docs
    assert "odylith/atlas/source/catalog/diagrams.v1.json" in component_docs
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" not in component_docs
    assert "odylith/registry/source/components/odylith-chatter/CURRENT_SPEC.md" not in component_docs


def test_route_ready_hot_path_payload_drops_redundant_prompt_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_codex_host_runtime(monkeypatch)

    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "validation-heavy-router-fix")

    adaptive = store.build_adaptive_coding_packet(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        runtime_mode="local",
        intent=str(scenario.get("intent", "")).strip(),
        family_hint=str(scenario.get("family", "")).strip(),
        workstream_hint=str(scenario.get("workstream", "")).strip(),
        validation_command_hints=[str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()],
    )

    payload = dict(adaptive["payload"])
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])
    packet_summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert adaptive["packet_source"] == "impact"
    assert sorted(payload.keys()) == ["context_packet"]
    assert context_packet["selection_state"] == "x:B-001"
    assert payload.get("narrowing_guidance") is None
    assert payload.get("session_seed_paths") is None
    assert payload.get("workstream_context") is None
    assert payload.get("miss_recovery_active") is None
    assert payload.get("miss_recovery_applied") is None
    assert payload.get("routing_handoff") is None
    assert payload.get("packet_metrics") is None
    assert context_packet["route"]["route_ready"] is True
    assert context_packet["route"]["native_spawn_ready"] is True
    assert context_packet["route"]["p"] == "bounded_parallel_candidate"
    assert context_packet["route"]["b"] == "deep_validation"
    assert context_packet["route"].get("parallelism_hint") is None
    assert context_packet["route"].get("reasoning_bias") is None
    assert context_packet["anchors"].get("explicit_paths") is None
    assert context_packet.get("packet_budget") is None
    assert retrieval_plan.get("selected_domains") is None
    assert retrieval_plan.get("guidance_coverage") is None
    assert retrieval_plan.get("evidence_consensus") is None
    assert retrieval_plan.get("miss_recovery") is None
    assert context_packet["packet_quality"].get("context_density_level") is None
    assert context_packet["packet_quality"].get("reasoning_readiness_level") is None
    assert packet_summary["within_budget"] is True
    assert packet_summary["workstream"] == "B-001"
    assert packet_summary["odylith_execution_profile"] == "write_high"
    assert packet_summary["odylith_execution_agent_role"] == "worker"
    assert packet_summary["odylith_execution_selection_mode"] == "bounded_write"
    assert packet_summary["odylith_execution_delegate_preference"] == "delegate"
    assert packet_summary["native_spawn_ready"] is True
    for key in ("contract", "version", "engine", "execution_profile", "optimization", "provenance_summary", "security_posture"):
        assert key not in context_packet


def test_non_route_ready_hot_path_payload_drops_duplicate_routing_handoff() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "broad-shared-guarding")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    narrowing_guidance = dict(payload["narrowing_guidance"])

    assert packet_source == "bootstrap_session"
    assert payload.get("retrieval_plan") is None
    assert payload.get("packet_quality") is None
    assert payload.get("packet_budget") is None
    assert context_packet.get("execution_profile") is None
    assert context_packet["anchors"] == {"anchor_quality": "shared_only"}
    assert context_packet["packet_quality"] == {
        "rc": "low",
        "i": "analysis",
        "cd": "low",
        "rr": "none",
        "cr": "narrowing",
        "ap": "broad_guarded",
    }
    assert context_packet["retrieval_plan"]["selected_counts"] == "g1"
    assert context_packet["retrieval_plan"]["guidance_coverage"] == "direct"
    assert context_packet["guidance_behavior_summary"]["status"] == "available"
    assert context_packet["guidance_behavior_summary"]["guidance_surface_contract"]["hosts"] == ["codex", "claude"]
    assert context_packet["guidance_behavior_summary"]["platform_contract"]["domains"] == [
        "benchmark_eval",
        "host_lane_bundle_mirrors",
        "hot_path_efficiency",
    ]
    assert context_packet["guidance_behavior_summary"]["hot_path_contract"]["provider_calls"] is False
    assert context_packet["route"] == {
        "narrowing_required": True,
        "b": "guarded_narrowing",
        "p": "serial_guarded",
    }
    assert narrowing_guidance == {
        "required": True,
        "reason": "Need one code path.",
    }
    assert context_packet.get("optimization") is None
    for key in ("contract", "version", "engine", "provenance_summary", "security_posture"):
        assert key not in context_packet


def test_governance_slice_hot_path_limits_operator_payload_lists() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "closeout-surface-path-normalization")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    narrowing_guidance = dict(payload["narrowing_guidance"])
    governance_signal = governance_signal_codec.expand_governance_signal(dict(context_packet["route"]["governance"]))

    assert packet_source == "governance_slice"
    assert sorted(payload.keys()) == ["changed_paths", "context_packet", "narrowing_guidance"]
    assert payload.get("routing_handoff") is None
    assert payload.get("packet_metrics") is None
    assert payload.get("validation_bundle") is None
    assert payload.get("governance_obligations") is None
    assert payload.get("surface_refs") is None
    assert payload["changed_paths"] == scenario["changed_paths"][:5]
    assert governance_signal["strict_gate_command_count"] == 1
    assert governance_signal["plan_binding_required"] is True
    assert governance_signal["governed_surface_sync_required"] is True
    assert governance_signal["closeout_doc_count"] >= 1
    assert governance_signal["primary_workstream_id"] == "B-002"
    assert governance_signal["primary_component_id"] == "odylith"
    assert governance_signal["surface_count"] == 5
    assert narrowing_guidance == {
        "required": True,
        "reason": "Need one code or contract path.",
    }
    assert context_packet["anchors"].get("explicit_paths") is None
    assert context_packet["anchors"]["has_non_shared_anchor"] is True
    assert context_packet["retrieval_plan"]["selected_counts"] == "c4d6g3"
    assert context_packet["retrieval_plan"]["guidance_coverage"] == "direct"
    assert context_packet.get("execution_profile") is None
    assert context_packet["route"].get("native_spawn_ready") is None
    assert context_packet["route"].get("reasoning_bias") is None
    assert context_packet["route"].get("parallelism_hint") is None


def test_governance_slice_hot_path_compacts_embedded_governance_keys() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "closeout-surface-path-normalization")

    _, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    governance_signal = dict(payload["context_packet"]["route"]["governance"])

    assert governance_signal["sg"] == 1
    assert governance_signal["pb"] is True
    assert governance_signal["gs"] is True
    assert governance_signal["cd"] >= 1
    assert governance_signal["w"] == "B-002"
    assert governance_signal["c"] == "odylith"
    assert governance_signal["sf"] == 5
    assert "strict_gate_command_count" not in governance_signal
    assert "primary_workstream_id" not in governance_signal


def test_miss_recovery_hot_path_keeps_signal_nested_under_retrieval_plan() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "wave4-runtime-sparse-miss-recovery")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])
    miss_recovery = dict(retrieval_plan["miss_recovery"])
    packet_summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert payload.get("miss_recovery_active") is None
    assert payload.get("miss_recovery_applied") is None
    assert payload.get("miss_recovery_mode") is None
    assert miss_recovery == {
        "active": True,
        "applied": True,
        "mode": "projection_exact_rescue",
    }
    assert packet_summary["miss_recovery_active"] is True
    assert packet_summary["miss_recovery_applied"] is True
    assert packet_summary["miss_recovery_mode"] == "projection_exact_rescue"


def test_packet_summary_distinguishes_hard_grounding_failure_from_soft_widening() -> None:
    hard_failure = store._packet_summary_from_bootstrap_payload(  # noqa: SLF001
        {
            "full_scan_reason": "no_grounded_paths",
            "context_packet_state": "gated_ambiguous",
            "context_packet": {
                "packet_state": "gated_ambiguous",
                "anchors": {
                    "changed_paths": [],
                    "explicit_paths": [],
                },
                "route": {},
                "packet_quality": {},
            },
            "session": {
                "session_id": "session-1",
                "claimed_paths": [],
            },
        }
    )
    soft_widening = store._packet_summary_from_bootstrap_payload(  # noqa: SLF001
        {
            "full_scan_reason": "broad_shared_paths",
            "changed_paths": ["odylith/AGENTS.md"],
            "fallback_scan": {"query": "tenant boundary"},
            "context_packet_state": "gated_broad_scope",
            "context_packet": {
                "packet_state": "gated_broad_scope",
                "full_scan_reason": "broad_shared_paths",
                "anchors": {
                    "changed_paths": ["odylith/AGENTS.md"],
                    "explicit_paths": [],
                },
                "retrieval_plan": {
                    "full_scan_reason": "broad_shared_paths",
                },
                "route": {},
                "packet_quality": {},
            },
            "session": {
                "session_id": "session-2",
                "claimed_paths": [],
            },
        }
    )

    assert hard_failure["hard_grounding_failure"] is True
    assert hard_failure["hard_grounding_failure_reason"] == "no_grounded_paths"
    assert hard_failure["soft_widening"] is False
    assert hard_failure["visible_fallback_receipt"] is False
    assert soft_widening["hard_grounding_failure"] is False
    assert soft_widening["soft_widening"] is True
    assert soft_widening["soft_widening_reason"] == "broad_shared_paths"
    assert soft_widening["visible_fallback_receipt"] is True
    assert soft_widening["visible_fallback_receipt_reason"] == "broad_shared_paths"


def test_governed_surface_sync_hot_path_skips_dead_miss_recovery() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "closeout-surface-path-normalization")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])

    assert packet_source == "governance_slice"
    assert retrieval_plan.get("miss_recovery") is None


def test_broad_scope_hot_path_keeps_fallback_recommendation_without_result_paths() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "context-engine-broad-scope-fail-closed")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "impact"
    assert payload["fallback_scan"] == {
        "recommended": True,
        "reason": "adaptive_full_scan_fallback",
        "performed": True,
    }
    assert "docs/WHY_ODYLITH_CHANGES_OUTCOMES.md" not in observed_paths
    assert "odylith/technical-plans/CLAUDE.md" not in observed_paths


def test_ambiguous_session_brief_keeps_fallback_recommendation_without_bug_result_paths() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "compass-refresh-queued-state-recovery")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    observed_paths = runner._observed_packet_paths(payload)  # noqa: SLF001

    assert packet_source == "session_brief"
    assert payload["fallback_scan"] == {
        "recommended": True,
        "reason": "adaptive_full_scan_fallback",
        "performed": True,
    }
    assert not any(path.startswith("odylith/casebook/bugs/") for path in observed_paths)


def test_safe_governance_hot_path_skips_runtime_warmup_when_projection_snapshot_is_present(monkeypatch) -> None:  # noqa: ANN001
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "consumer-install-upgrade-runtime-contract")

    monkeypatch.setattr(
        odylith_context_engine_hot_path_governance_runtime,
        "projection_snapshot_path",
        lambda **_: REPO_ROOT / "pyproject.toml",
    )

    def _fail_warm_runtime(**_kwargs: object) -> bool:
        raise AssertionError("safe governance hot path should not warm runtime")

    monkeypatch.setattr(store, "_warm_runtime", _fail_warm_runtime)
    monkeypatch.setattr(odylith_context_engine_hot_path_governance_runtime, "_warm_runtime", _fail_warm_runtime)

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )

    assert packet_source == "governance_slice"
    assert payload["context_packet"]["route"]["route_ready"] is True
    assert set(
        [
            "src/odylith/install/manager.py",
            "src/odylith/install/runtime.py",
            "tests/integration/install/test_manager.py",
            "odylith/INSTALL_AND_UPGRADE_RUNBOOK.md",
            "odylith/registry/source/components/release/CURRENT_SPEC.md",
            "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
        ]
    ).issubset(set(runner._observed_packet_paths(payload)))  # noqa: SLF001


def test_governed_surface_sync_hot_path_still_warms_runtime_when_skip_rule_does_not_apply(monkeypatch) -> None:  # noqa: ANN001
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "closeout-surface-path-normalization")
    calls: list[dict[str, object]] = []

    monkeypatch.setattr(
        odylith_context_engine_hot_path_governance_runtime,
        "projection_snapshot_path",
        lambda **_: REPO_ROOT / "pyproject.toml",
    )

    def _track_warm_runtime(**kwargs: object) -> bool:
        calls.append(dict(kwargs))
        return True

    monkeypatch.setattr(store, "_warm_runtime", _track_warm_runtime)
    monkeypatch.setattr(odylith_context_engine_hot_path_governance_runtime, "_warm_runtime", _track_warm_runtime)

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )

    assert packet_source == "governance_slice"
    assert calls
    assert payload["context_packet"]["route"].get("route_ready") is not True


def test_exact_path_ambiguity_hot_path_drops_dead_ambiguous_scaffolding() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "runtime-path-ambiguity")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])

    assert packet_source == "bootstrap_session"
    narrowing_guidance = dict(payload["narrowing_guidance"])

    assert payload.get("retrieval_plan") is None
    assert payload.get("packet_quality") is None
    assert payload.get("packet_budget") is None
    assert narrowing_guidance["required"] is True
    assert narrowing_guidance == {
        "required": True,
        "reason": "Need one code path.",
    }
    assert retrieval_plan["ambiguity_class"] == "no_candidates"
    assert retrieval_plan["selected_counts"] == "g2"
    assert retrieval_plan["precision_score"] == 33
    assert retrieval_plan["evidence_consensus"] == "mixed"
    assert context_packet["route"] == {
        "narrowing_required": True,
        "b": "guarded_narrowing",
        "p": "serial_guarded",
    }
    assert context_packet.get("execution_profile") is None
    assert context_packet.get("optimization") is None


def test_session_brief_exact_path_hot_path_keeps_only_live_narrowing_signal() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "session-brief-runtime-path-ambiguity")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])

    assert packet_source == "session_brief"
    assert context_packet.get("packet_kind") is None
    assert context_packet.get("execution_profile") is None
    assert context_packet.get("optimization") is None
    assert context_packet.get("selection_state") is None
    assert retrieval_plan == {
        "ambiguity_class": "no_candidates",
        "miss_recovery": {
            "active": True,
            "applied": True,
            "mode": "projection_exact_rescue",
        },
    }
    assert context_packet["route"] == {
        "narrowing_required": True,
        "b": "guarded_narrowing",
        "p": "serial_guarded",
    }
    assert payload["narrowing_guidance"] == {
        "required": True,
        "reason": "Need one code path.",
    }


def test_architecture_hot_path_drops_ambiguous_count_scaffolding() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "architecture-benchmark-honest-baseline-contract")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )
    context_packet = dict(payload["context_packet"])
    retrieval_plan = dict(context_packet["retrieval_plan"])

    assert packet_source == "impact"
    assert context_packet.get("selection_state") is None
    assert retrieval_plan.get("selected_counts") is None
    assert retrieval_plan["ambiguity_class"] == "low_signal"
    assert retrieval_plan["miss_recovery"] == {
        "active": True,
        "applied": True,
        "mode": "projection_exact_rescue",
    }
    assert context_packet["anchors"]["changed_paths"] == [
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    ]
    assert context_packet["route"] == {"narrowing_required": True}


def test_route_ready_hot_path_packet_skips_packet_metrics_and_handoff_scaffolding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _force_codex_host_runtime(monkeypatch)

    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "orchestrator-ledger-closeout")

    packet_source, payload, _ = runner._build_packet_payload(  # noqa: SLF001
        repo_root=REPO_ROOT,
        scenario=scenario,
        mode="odylith_on",
        existing_paths=scenario["changed_paths"],
    )

    assert packet_source == "impact"
    assert sorted(payload.keys()) == ["context_packet"]
    assert payload.get("routing_handoff") is None
    assert payload.get("packet_metrics") is None
    assert payload["context_packet"]["route"] == {
        "route_ready": True,
        "native_spawn_ready": True,
        "p": "bounded_parallel_candidate",
        "b": "deep_validation",
    }


def test_orchestration_request_payload_uses_embedded_governance_signal() -> None:
    request = runner._orchestration_request_payload(  # noqa: SLF001
        scenario={
            "prompt": "Close out the governed slice.",
            "acceptance_criteria": [],
            "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
            "needs_write": True,
            "kind": "governance",
            "family": "docs_code_closeout",
        },
        packet_payload={
            "context_packet": {
                "route": {
                    "governance": {
                        "primary_workstream_id": "B-002",
                        "primary_component_id": "odylith",
                    }
                }
            }
        },
    )

    assert request["workstreams"] == ["B-002"]
    assert request["components"] == ["odylith"]


def test_packet_level_architecture_audit_keeps_doc_only_slice_grounded() -> None:
    payload = store.build_architecture_audit(
        repo_root=REPO_ROOT,
        changed_paths=["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        runtime_mode="local",
        detail_level="packet",
    )

    assert payload == {
        "resolved": True,
        "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
        "coverage": {
            "confidence_tier": "medium",
        },
        "authority_graph": {
            "counts": {
                "edges": 3,
                "traceability_edges": 2,
            },
        },
        "execution_hint": {
            "mode": "local_grounding_first",
            "fanout": "no_fanout",
            "risk_tier": "moderate",
        },
        "contract_touchpoint_count": 2,
        "validation_obligation_count": 2,
    }


def test_hot_path_impact_honors_supplied_workstream_hint() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "merge-heavy-router-doc-sync")

    impact = store.build_impact_report(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        runtime_mode="local",
        intent=str(scenario.get("intent", "")).strip(),
        delivery_profile="agent_hot_path",
        family_hint=str(scenario.get("family", "")).strip(),
        workstream_hint=str(scenario.get("workstream", "")).strip(),
        validation_command_hints=[str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()],
        retain_hot_path_internal_context=True,
    )

    selection = store._hot_path_workstream_selection(impact)  # noqa: SLF001

    assert selection["state"] == "explicit"
    assert selection["selected_workstream"]["entity_id"] == "B-001"


def test_merge_heavy_router_doc_sync_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "merge-heavy-router-doc-sync")

    assert scenario["allow_noop_completion"] is True


def test_docs_code_governed_closeout_allows_validator_backed_noop_completion() -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "docs-code-governed-closeout")

    assert scenario["allow_noop_completion"] is True


def test_hot_path_broad_shared_scope_skips_runtime_warm_and_db(monkeypatch) -> None:  # noqa: ANN001
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "broad-shared-guarding")

    def _fail_warm_runtime(**kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("broad shared hot path should not warm runtime")

    def _fail_connect(*args, **kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("broad shared hot path should not open the runtime DB")

    monkeypatch.setattr(store, "_warm_runtime", _fail_warm_runtime)
    monkeypatch.setattr(store, "_connect", _fail_connect)

    impact = store.build_impact_report(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        runtime_mode="local",
        intent=str(scenario.get("intent", "")).strip(),
        delivery_profile="agent_hot_path",
        family_hint=str(scenario.get("family", "")).strip(),
        retain_hot_path_internal_context=False,
    )

    context_packet = dict(impact.get("context_packet", {}))
    route = dict(context_packet.get("route", {}))

    assert store._hot_path_full_scan_recommended(impact) is False  # noqa: SLF001
    assert store._hot_path_route_ready(impact) is False  # noqa: SLF001
    assert context_packet.get("packet_state") == "gated_broad_scope"
    assert route.get("narrowing_required") is True
    assert context_packet["anchors"].get("changed_paths") == ["AGENTS.md", "odylith/AGENTS.md"]


def test_build_impact_report_reuses_supplied_snapshots(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    sentinel_catalog = {"chunk_count": 7, "catalog_fingerprint": "catalog-fingerprint"}
    sentinel_optimization = {"status": "warm", "overall": {"score": 1.0}}

    def _unexpected_catalog_load(**kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("guidance catalog should be reused")

    def _unexpected_optimization_load(**kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("optimization snapshot should be reused")

    monkeypatch.setattr(store.tooling_guidance_catalog, "load_guidance_catalog", _unexpected_catalog_load)
    monkeypatch.setattr(store, "load_runtime_optimization_snapshot", _unexpected_optimization_load)
    monkeypatch.setattr(
        store,
        "_resolve_changed_path_scope_context",
        lambda **kwargs: {  # noqa: ANN001
            "analysis_paths": [],
            "explicit_paths": [],
            "repo_dirty_paths": [],
            "scoped_working_tree_paths": [],
            "working_tree_scope": "repo",
            "working_tree_scope_degraded": False,
        },
    )

    def _fake_finalize_packet(**kwargs):  # noqa: ANN001
        captured["guidance_catalog"] = kwargs["guidance_catalog"]
        captured["optimization_snapshot"] = kwargs["optimization_snapshot"]
        return {
            **dict(kwargs["payload"]),
            "context_packet_state": kwargs["packet_state"],
        }

    monkeypatch.setattr(store.tooling_context_packet_builder, "finalize_packet", _fake_finalize_packet)

    payload = store.build_impact_report(
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="local",
        intent="benchmark",
        guidance_catalog_snapshot=sentinel_catalog,
        optimization_snapshot=sentinel_optimization,
    )

    assert captured["guidance_catalog"] == sentinel_catalog
    assert captured["optimization_snapshot"] == sentinel_optimization
    assert payload["full_scan_reason"] == "no_grounded_paths"
    assert payload["context_packet_state"] == "gated_ambiguous"


def test_build_impact_report_can_skip_finalize_packet(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        store,
        "_resolve_changed_path_scope_context",
        lambda **kwargs: {  # noqa: ANN001
            "analysis_paths": [],
            "explicit_paths": [],
            "repo_dirty_paths": [],
            "scoped_working_tree_paths": [],
            "working_tree_scope": "repo",
            "working_tree_scope_degraded": False,
        },
    )
    monkeypatch.setattr(
        store.tooling_context_packet_builder,
        "finalize_packet",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("finalize_packet should be skipped")),  # noqa: ANN001
    )

    payload = store.build_impact_report(
        repo_root=tmp_path,
        changed_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        runtime_mode="local",
        intent="benchmark",
        delivery_profile="agent_hot_path",
        finalize_packet=False,
    )

    assert payload["full_scan_reason"] == "no_grounded_paths"
    assert payload["context_packet_state"] == "gated_ambiguous"
    assert payload.get("context_packet") is None


def test_hot_path_session_brief_reuses_compact_selection_without_runtime_reopen(monkeypatch) -> None:
    impact_override = {
        "changed_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
        "explicit_paths": ["src/odylith/runtime/orchestration/subagent_router.py"],
        "candidate_workstreams": [
            {
                "entity_id": "B-001",
                "title": "Odylith Product Self-Governance and Repo Boundary",
            }
        ],
        "workstream_selection": {
            "state": "ambiguous",
            "reason": "Top workstream candidate `B-001` is driven only by broad shared-path evidence.",
            "confidence": "low",
            "ambiguity_class": "broad_shared_only",
            "candidate_count": 1,
            "strong_candidate_count": 0,
            "top_candidate": {
                "entity_id": "B-001",
                "title": "Odylith Product Self-Governance and Repo Boundary",
            },
        },
        "context_packet": {
            "route": {
                "route_ready": False,
                "native_spawn_ready": False,
            }
        },
        "fallback_scan": {},
        "full_scan_recommended": False,
        "full_scan_reason": "",
        "truncation": {},
    }

    monkeypatch.setattr(store, "_connect", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("selection reopened")))
    monkeypatch.setattr(
        store,
        "list_session_states",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("session ledger should stay cold")),
    )

    payload = store.build_session_brief(
        repo_root=REPO_ROOT,
        changed_paths=["src/odylith/runtime/orchestration/subagent_router.py"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint="orchestration_feedback",
        impact_override=impact_override,
    )

    assert isinstance(payload.get("context_packet"), dict)
    assert payload.get("workstream_context") is None


def test_hot_path_bootstrap_session_skips_optimization_snapshot_load(monkeypatch) -> None:
    scenarios = runner.load_benchmark_scenarios(repo_root=REPO_ROOT)
    scenario = next(row for row in scenarios if row["scenario_id"] == "broad-shared-guarding")

    def _unexpected_optimization_load(**kwargs):  # noqa: ANN001,ARG001
        raise AssertionError("hot bootstrap session should not load optimization snapshot")

    monkeypatch.setattr(store, "load_runtime_optimization_snapshot", _unexpected_optimization_load)

    payload = store.build_session_bootstrap(
        repo_root=REPO_ROOT,
        changed_paths=scenario["changed_paths"],
        runtime_mode="local",
        delivery_profile="agent_hot_path",
        family_hint=str(scenario.get("family", "")).strip(),
        validation_command_hints=[
            str(token).strip()
            for token in scenario.get("validation_commands", [])
            if str(token).strip()
        ],
    )

    assert isinstance(payload.get("context_packet"), dict)
    assert payload["context_packet"]["route"]["narrowing_required"] is True


def test_collect_recommended_tests_reuses_cached_projection_rows(monkeypatch) -> None:
    cached_rows = [
        {
            "test_id": "T-001",
            "test_path": "tests/unit/runtime/test_sample.py",
            "node_id": "",
            "test_name": "test_sample",
            "markers_json": '["unit"]',
            "target_paths_json": '["src/odylith/runtime/sample.py"]',
            "metadata_json": '{"history":{"recent_failure":true,"failure_count":2,"empirical_score":9,"sources":["pytest"]}}',
        }
    ]
    cache_names: list[str] = []

    def _fake_cached_projection_rows(**kwargs):  # noqa: ANN001
        cache_names.append(str(kwargs.get("cache_name", "")))
        return cached_rows

    class _NoQueryConnection:
        def execute(self, *args, **kwargs):  # noqa: ANN002,ANN003
            raise AssertionError("test recommendation should reuse cached projection rows")

    monkeypatch.setattr(store, "_cached_projection_rows", _fake_cached_projection_rows)

    rows = store._collect_recommended_tests(
        _NoQueryConnection(),
        repo_root=REPO_ROOT,
        changed_paths=["src/odylith/runtime/sample.py"],
        code_neighbors={},
        limit=4,
    )

    assert cache_names == ["tests_full_rows"]
    assert rows == [
        {
            "test_id": "T-001",
            "test_path": "tests/unit/runtime/test_sample.py",
            "node_id": "",
            "test_name": "test_sample",
            "markers": ["unit"],
            "matched_targets": ["src/odylith/runtime/sample.py"],
            "history": {
                "recent_failure": True,
                "failure_count": 2,
                "sources": ["pytest"],
                "last_failure_utc": "",
            },
        }
    ]


def test_collect_impacted_workstreams_uses_precomputed_match_rows(monkeypatch) -> None:
    cache_names: list[str] = []

    def _fake_cached_projection_rows(**kwargs):  # noqa: ANN001
        cache_name = str(kwargs.get("cache_name", ""))
        cache_names.append(cache_name)
        if cache_name == "workstreams_full_rows":
            return [
                {
                    "idea_id": "B-001",
                    "title": "Example workstream",
                    "status": "implementation",
                    "source_path": "odylith/radar/source/ideas/example.md",
                    "section": "active",
                    "priority": "P1",
                    "promoted_to_plan": "",
                    "idea_file": "odylith/radar/source/ideas/example.md",
                    "metadata_json": "{}",
                }
            ]
        if cache_name == "workstream_direct_match_rows":
            return [
                {
                    "source_id": "B-001",
                    "target_path": "odylith/surfaces/GOVERNANCE_SURFACES.md",
                }
            ]
        if cache_name == "workstream_traceability_match_rows":
            return []
        raise AssertionError(f"unexpected cache lookup: {cache_name}")

    class _NoQueryConnection:
        def execute(self, *args, **kwargs):  # noqa: ANN002,ANN003
            raise AssertionError("workstream matching should stay on precomputed cache rows")

    monkeypatch.setattr(store, "_cached_projection_rows", _fake_cached_projection_rows)

    store.clear_runtime_process_caches(repo_root=REPO_ROOT)

    rows, diagnostics = store._collect_impacted_workstreams(
        _NoQueryConnection(),
        repo_root=REPO_ROOT,
        changed_paths=["./odylith/surfaces/GOVERNANCE_SURFACES.md"],
        component_ids=[],
        diagram_ids=[],
        return_diagnostics=True,
    )

    assert [row["entity_id"] for row in rows] == ["B-001"]
    assert rows[0]["evidence"]["matched_paths"] == ["odylith/surfaces/GOVERNANCE_SURFACES.md"]
    assert diagnostics["fast_selector_used"] is True
    assert diagnostics["selector_candidate_row_count"] == 1
    assert "workstream_direct_match_rows" in cache_names
    assert "workstream_traceability_match_rows" in cache_names

    _, cached_diagnostics = store._collect_impacted_workstreams(
        _NoQueryConnection(),
        repo_root=REPO_ROOT,
        changed_paths=["./odylith/surfaces/GOVERNANCE_SURFACES.md"],
        component_ids=[],
        diagram_ids=[],
        return_diagnostics=True,
    )
    assert cached_diagnostics["selector_cache_hit"] is True
