"""Benchmark Odylith against honest live Codex CLI baseline modes.

This module keeps the benchmark harness local-first and non-destructive:

- it reuses the seeded optimization corpus that already defines high-signal task
  families;
- it toggles Odylith through environment overrides instead of mutating tracked
  repo state;
- it writes machine-readable benchmark reports under `.odylith/runtime/`; and
- it produces one compact comparison summary suitable for `status` and operator
  readouts.
"""

from __future__ import annotations

import ast
import concurrent.futures
import contextlib
import datetime as dt
import errno
import fcntl
import hashlib
import inspect
import json
import multiprocessing
import os
from pathlib import Path
import re
import secrets
import shlex
import shutil
import signal
import statistics
import subprocess
import sys
import tempfile
import time
import tomllib
from typing import Any, Iterator, Mapping, Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.evaluation import benchmark_group_summaries
from odylith.runtime.evaluation import odylith_benchmark_isolation
from odylith.runtime.evaluation import odylith_benchmark_context_engine
from odylith.runtime.evaluation import odylith_benchmark_execution_engine
from odylith.runtime.evaluation import odylith_benchmark_guardrails
from odylith.runtime.evaluation import odylith_benchmark_live_diagnostics
from odylith.runtime.evaluation import odylith_benchmark_live_execution
from odylith.runtime.evaluation import odylith_benchmark_proof_discipline
from odylith.runtime.evaluation import odylith_benchmark_prompt_payloads
from odylith.runtime.common import odylith_benchmark_contract
from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import governance_signal_codec
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.context_engine import path_bundle_codec
from odylith.runtime.character import runtime as character_runtime
from odylith.runtime.governance import guidance_behavior_runtime
from odylith.runtime.orchestration import subagent_orchestrator
from odylith.runtime.orchestration import subagent_router as leaf_router

REPORT_CONTRACT = "odylith_benchmark_report.v1"
REPORT_VERSION = "v1"
PROGRESS_CONTRACT = "odylith_benchmark_progress.v1"
PROGRESS_VERSION = "v1"
ACTIVE_RUNS_CONTRACT = "odylith_benchmark_active_runs.v1"
ACTIVE_RUNS_VERSION = "v1"
LIVE_COMPARISON_CONTRACT = "full_product_assistance_vs_raw_agent"
LEGACY_LIVE_COMPARISON_CONTRACT = "live_end_to_end"
DIAGNOSTIC_COMPARISON_CONTRACT = "internal_packet_prompt_diagnostic"
BENCHMARK_PROFILE_QUICK = "quick"
BENCHMARK_PROFILE_PROOF = "proof"
BENCHMARK_PROFILE_DIAGNOSTIC = "diagnostic"
_ODYLITH_ON_MODE = "odylith_on"
_ODYLITH_ON_NO_FANOUT_MODE = "odylith_on_no_fanout"
_REPO_SCAN_BASELINE_MODE = "odylith_repo_scan_baseline"
_RAW_AGENT_BASELINE_MODE = "raw_agent_baseline"
_ODYLITH_OFF_ALIAS = "odylith_off"
_LEGACY_REPO_SCAN_BASELINE_MODE = "full_scan_baseline"
BENCHMARK_PROFILES: tuple[str, ...] = (
    BENCHMARK_PROFILE_QUICK,
    BENCHMARK_PROFILE_PROOF,
    BENCHMARK_PROFILE_DIAGNOSTIC,
)
DEFAULT_MODES: tuple[str, ...] = (
    _ODYLITH_ON_MODE,
    _RAW_AGENT_BASELINE_MODE,
)
DIAGNOSTIC_CONTROL_MODES: tuple[str, ...] = (
    _ODYLITH_ON_NO_FANOUT_MODE,
    _REPO_SCAN_BASELINE_MODE,
)
DEFAULT_BENCHMARK_PROFILE = BENCHMARK_PROFILE_PROOF
DEFAULT_CLI_BENCHMARK_PROFILE = BENCHMARK_PROFILE_QUICK
PUBLIC_CLI_MODES: tuple[str, ...] = (
    _ODYLITH_ON_MODE,
    _ODYLITH_OFF_ALIAS,
    _ODYLITH_ON_NO_FANOUT_MODE,
    _REPO_SCAN_BASELINE_MODE,
)
_PUBLIC_PUBLISHED_MODE_ORDER: tuple[str, ...] = (
    _ODYLITH_ON_MODE,
    _RAW_AGENT_BASELINE_MODE,
)
_MODE_ALIASES = {
    _LEGACY_REPO_SCAN_BASELINE_MODE: _REPO_SCAN_BASELINE_MODE,
    _ODYLITH_OFF_ALIAS: _RAW_AGENT_BASELINE_MODE,
}
_VALID_MODES = frozenset((*DEFAULT_MODES, *DIAGNOSTIC_CONTROL_MODES, *_MODE_ALIASES.keys()))
DEFAULT_CACHE_PROFILES: tuple[str, ...] = ("warm", "cold")
_VALID_CACHE_PROFILES = frozenset({"warm", "cold"})
_FAMILY_ALIASES = {
    "discipline": "agent_operating_character",
    "odylith-discipline": "agent_operating_character",
    "odylith_discipline": "agent_operating_character",
}
_LOCAL_ONLY_QUICK_FAMILIES = frozenset({"guidance_behavior", "agent_operating_character"})
_MIN_BENCHMARK_RUNTIME_FREE_BYTES = 256 * 1024 * 1024
_RUNTIME_POSTURE_MANAGED_HELPER_ENV = "ODYLITH_BENCHMARK_RUNTIME_POSTURE_MANAGED_HELPER"
_VALID_PACKET_SOURCES = frozenset({"adaptive", "impact", "governance_slice", "session_brief", "bootstrap_session"})
_ANALYSIS_FAMILIES = frozenset({"analysis", "architecture", "broad_shared_scope"})
_WRITE_FAMILIES = frozenset(
    {
        "api_contract_evolution",
        "cross_file_feature",
        "destructive_scope_control",
        "docs_code_closeout",
        "exact_anchor_recall",
        "external_dependency_recovery",
        "explicit_workstream",
        "merge_heavy_change",
        "orchestration_feedback",
        "orchestration_intelligence",
        "stateful_bug_recovery",
        "validation_heavy_fix",
    }
)
_GOVERNANCE_SLICE_FAMILIES = frozenset(
    {
        "docs_code_closeout",
        "explicit_workstream",
        "governed_surface_sync",
        "install_upgrade_runtime",
        "release_publication",
        "daemon_security",
        "component_governance",
        "agent_activation",
        "cross_surface_governance_sync",
        "execution_engine",
        "live_proof_discipline",
    }
)
_CORRECTNESS_CRITICAL_FAMILIES = frozenset(
    {
        "destructive_scope_control",
        "external_dependency_recovery",
        "merge_heavy_change",
        "stateful_bug_recovery",
        "validation_heavy_fix",
    }
)
_MECHANISM_HEAVY_IMPLEMENTATION_FAMILIES = frozenset(
    {
        "broad_shared_scope",
        "context_engine_grounding",
        "execution_engine",
        "exact_anchor_recall",
        "exact_path_ambiguity",
        "explicit_workstream",
        "orchestration_feedback",
        "orchestration_intelligence",
        "retrieval_miss_recovery",
    }
)
_SERIOUS_IMPLEMENTATION_SCENARIO_MIN = 60
_SERIOUS_WRITE_PLUS_VALIDATOR_SCENARIO_MIN = 35
_SERIOUS_CORRECTNESS_CRITICAL_SCENARIO_MIN = 12
_SERIOUS_MECHANISM_HEAVY_IMPLEMENTATION_MAX_RATIO = 0.40
_SERIOUS_REQUIRED_FAMILIES = frozenset(
    {
        "api_contract_evolution",
        "stateful_bug_recovery",
        "external_dependency_recovery",
        "destructive_scope_control",
    }
)
_REPORT_FILENAME = "latest.v1.json"
_PROGRESS_FILENAME = "in-progress.v1.json"
_ACTIVE_RUNS_FILENAME = "active-runs.v1.json"
_BENCHMARK_WARM_CACHE_SECONDS = 30.0
_BENCHMARK_ADOPTION_PROOF_SAMPLE_TIMEOUT_SECONDS = 60.0
_BENCHMARK_ADOPTION_PROOF_TERMINATION_GRACE_SECONDS = 1.0
_BENCHMARK_LOCK_KEY = "odylith-benchmark-runner"


class BenchmarkRunInterrupted(RuntimeError):
    """Raised when a benchmark run receives a termination-style interrupt."""


@contextlib.contextmanager
def _benchmark_interrupt_guard() -> Iterator[None]:
    handlers: list[tuple[int, Any]] = []

    def _handler(signum: int, _frame: Any) -> None:
        signal_name = getattr(signal.Signals(signum), "name", str(signum))
        raise BenchmarkRunInterrupted(f"received {signal_name}")

    if multiprocessing.current_process().name == "MainProcess":
        for signum in (signal.SIGTERM, signal.SIGINT):
            if any(existing == signum for existing, _ in handlers):
                continue
            with contextlib.suppress(OSError, RuntimeError, ValueError):
                previous = signal.getsignal(signum)
                signal.signal(signum, _handler)
                handlers.append((signum, previous))
        sighup = getattr(signal, "SIGHUP", None)
        if sighup is not None and not any(existing == sighup for existing, _ in handlers):
            with contextlib.suppress(OSError, RuntimeError, ValueError):
                previous = signal.getsignal(sighup)
                signal.signal(sighup, signal.SIG_IGN)
                handlers.append((sighup, previous))
    try:
        yield
    finally:
        for signum, previous in reversed(handlers):
            with contextlib.suppress(OSError, RuntimeError, ValueError):
                signal.signal(signum, previous)

_PROMPT_PAYLOAD_KEYS = frozenset({"context_packet", "narrowing_guidance", "docs", "relevant_docs"})
_RUNTIME_CONTRACT_KEYS = frozenset(
    {
        "retrieval_plan",
        "guidance_brief",
        "working_memory_tiers",
        "packet_quality",
        "routing_handoff",
        "evidence_pack",
        "packet_metrics",
        "packet_budget",
        "adaptive_packet_profile",
    }
)
_LOWER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "hallucinated_surface_rate",
        "median_latency_ms",
        "avg_latency_ms",
        "p95_latency_ms",
        "median_instrumented_reasoning_duration_ms",
        "avg_instrumented_reasoning_duration_ms",
        "p95_instrumented_reasoning_duration_ms",
        "median_uninstrumented_overhead_ms",
        "avg_uninstrumented_overhead_ms",
        "p95_uninstrumented_overhead_ms",
        "latency_probe_spread_ms",
        "median_initial_prompt_tokens",
        "avg_initial_prompt_tokens",
        "median_effective_tokens",
        "avg_effective_tokens",
        "median_total_payload_tokens",
        "avg_total_payload_tokens",
        "median_runtime_contract_tokens",
        "avg_runtime_contract_tokens",
        "median_operator_diag_tokens",
        "avg_operator_diag_tokens",
        "avg_delegated_leaf_count",
        "odylith_requires_widening_rate",
        "odylith_mixed_local_fallback_rate",
        "unnecessary_widening_rate",
        *odylith_benchmark_proof_discipline.LOWER_BETTER_SUMMARY_FIELDS,
        *odylith_benchmark_context_engine.LOWER_BETTER_SUMMARY_FIELDS,
        *odylith_benchmark_execution_engine.LOWER_BETTER_SUMMARY_FIELDS,
    }
)
_HIGHER_BETTER_SUMMARY_FIELDS = frozenset(
    {
        "required_path_precision_rate",
        "required_path_recall_rate",
        "validation_success_rate",
        "expectation_success_rate",
        "within_budget_rate",
        "route_ready_rate",
        "odylith_packet_present_rate",
        "odylith_auto_grounded_rate",
        "odylith_grounded_rate",
        "odylith_grounded_delegate_rate",
        "odylith_workspace_daemon_reuse_rate",
        "odylith_session_namespaced_rate",
        "critical_required_path_recall_rate",
        "critical_validation_success_rate",
        "write_surface_precision_rate",
        *odylith_benchmark_proof_discipline.HIGHER_BETTER_SUMMARY_FIELDS,
        *odylith_benchmark_context_engine.HIGHER_BETTER_SUMMARY_FIELDS,
        *odylith_benchmark_execution_engine.HIGHER_BETTER_SUMMARY_FIELDS,
    }
)
_LOWER_BETTER_RESULT_FIELDS = frozenset(
    {
        "hallucinated_surface_rate",
        "latency_ms",
        "instrumented_reasoning_duration_ms",
        "uninstrumented_overhead_ms",
        "initial_prompt_estimated_tokens",
        "effective_estimated_tokens",
        "codex_prompt_estimated_tokens",
        "total_payload_estimated_tokens",
        "runtime_contract_estimated_tokens",
        "operator_diag_estimated_tokens",
        "unnecessary_widening_rate",
    }
)
_HIGHER_BETTER_RESULT_FIELDS = frozenset(
    {
        "required_path_precision",
        "required_path_recall",
        "validation_success_proxy",
        "write_surface_precision",
    }
)
_BASELINE_MODE = _RAW_AGENT_BASELINE_MODE
_SENSITIVE_SINGLETON_FAMILY_LATENCY_FAMILIES = frozenset(
    {
        "exact_path_ambiguity",
        "retrieval_miss_recovery",
    }
)
_SENSITIVE_SINGLETON_FAMILY_LATENCY_PROBE_MODES: tuple[str, ...] = (
    _ODYLITH_ON_MODE,
    _RAW_AGENT_BASELINE_MODE,
)
_SENSITIVE_SINGLETON_FAMILY_LATENCY_SAMPLE_COUNT = 3
_SENSITIVE_SINGLETON_FAMILY_LATENCY_MAX_SPREAD_MS = 8.0
_PUBLISHED_PROFILE_LATENCY_TIE_TOLERANCE_MS = 0.4
_PUBLISHED_PROFILE_PROMPT_TIE_TOLERANCE = 8.0
_PUBLISHED_PROFILE_TOTAL_PAYLOAD_TIE_TOLERANCE = 16.0
_QUICK_PROFILE_MAX_SCENARIOS = 4
_QUICK_PROFILE_SENTINEL_CASE_IDS = (
    "benchmark-live-comparison-contract-and-report-schema",
    "execution-engine-contract-verify-closure-discipline",
    "claude-bash-guard-destructive-command-blocking",
    "context-engine-broad-scope-fail-closed",
)
_LIVE_MATCHED_PAIR_MAX_WORKERS = 2
_SECONDARY_LATENCY_GUARDRAIL_MAX_DELTA_MS = 15.0
_SECONDARY_ARCHITECTURE_LATENCY_GUARDRAIL_MAX_DELTA_MS = 15.0
_SECONDARY_PROMPT_TOKEN_GUARDRAIL_MAX_DELTA = 64.0
_SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA = 96.0
_SECONDARY_WITHIN_BUDGET_RATE_MIN = 0.8
_BENCHMARK_TEMP_MARKER = "odylith-benchmark-"
_BENCHMARK_LIVE_WORKTREE_MARKER = "odylith-benchmark-live-"
_BENCHMARK_RUNTIME_TEMP_DIRECTORY_PREFIXES: tuple[str, ...] = (
    _BENCHMARK_LIVE_WORKTREE_MARKER,
    "odylith-benchmark-codex-",
    "odylith-benchmark-codex-home-",
)
_VALIDATION_COMPANION_FILE_SUFFIXES = frozenset(
    {
        ".css",
        ".html",
        ".js",
        ".json",
        ".md",
        ".mmd",
        ".png",
        ".py",
        ".svg",
        ".toml",
        ".txt",
    }
)
_ACCEPTANCE_CHECK_LABELS = {
    "memory_backend_standardized": "runtime memory backend is not standardized on the LanceDB/Tantivy contract",
    "memory_backed_retrieval_ready": "benchmark ran without an active local LanceDB/Tantivy retrieval substrate",
    "required_path_recall_not_worse": "grounding recall fell below the raw baseline",
    "required_path_precision_not_worse": "grounding precision fell below the raw baseline",
    "hallucinated_surface_not_worse": "observed-surface drift is worse than the raw baseline",
    "validation_success_not_worse": "validation success fell below the raw baseline",
    "write_surface_precision_not_worse": "write-surface precision fell below the raw baseline",
    "unnecessary_widening_not_worse": "unnecessary write-surface widening is worse than the raw baseline",
    "critical_required_path_recall_not_worse": "critical-path recall fell below the raw baseline",
    "critical_validation_success_not_worse": "critical validation success fell below the raw baseline",
    "live_execution_contract_match": "odylith_on and odylith_off did not use the same Codex CLI model and reasoning contract",
    "expectation_success_not_worse": "execution fit fell below the raw baseline",
    "candidate_expectation_success_positive": "odylith_on did not finish any sampled live task successfully",
    "candidate_validation_success_positive": "odylith_on did not reach any validator-backed successful outcome on sampled validation-backed work",
    "candidate_critical_required_path_recall_positive": "odylith_on missed every critical required path on sampled critical work",
    "candidate_critical_validation_success_positive": "odylith_on did not reach any successful critical validator-backed outcome",
    "proof_false_clearance_healthy": "proof-state claimed live clearance before the hosted frontier advanced",
    "proof_frontier_gate_accurate": "proof-state frontier gating is inconsistent with the observed live frontier",
    "proof_claim_guard_accurate": "claim guard is labeling proof tiers inconsistently",
    "proof_same_fingerprint_reuse_accurate": "same-fingerprint live failures are not reopening the same blocker seam consistently",
    "context_engine_packet_source_accurate": "Context Engine benchmark slices chose the wrong packet lane",
    "context_engine_selection_state_accurate": "Context Engine benchmark slices resolved the wrong scope-selection state",
    "context_engine_workstream_accurate": "Context Engine benchmark slices resolved the wrong workstream anchor",
    "context_engine_ambiguity_fail_closed": "Context Engine benchmark slices do not stay fail-closed on ambiguous scope",
    "context_engine_session_namespaced": "Context Engine runtime-backed benchmark slices are not keeping sessions namespaced",
    "execution_engine_present": "execution-engine benchmark slices are missing the execution-engine snapshot",
    "execution_engine_resume_token_present": "execution-engine benchmark slices are missing resume-token coverage",
    "execution_engine_false_admit_zero": "execution-engine benchmark slices still falsely admit blocked actions",
    "execution_engine_false_deny_zero": "execution-engine benchmark slices still falsely deny admissible actions",
    "execution_engine_outcome_accurate": "execution-engine benchmark slices resolved the wrong admissibility outcome",
    "execution_engine_mode_accurate": "execution-engine benchmark slices resolved the wrong execution mode",
    "execution_engine_next_move_accurate": "execution-engine benchmark slices resolved the wrong truthful next move",
    "execution_engine_closure_accurate": "execution-engine benchmark slices resolved the wrong closure posture",
    "execution_engine_wait_status_accurate": "execution-engine benchmark slices resolved the wrong semantic wait status",
    "execution_engine_validation_accurate": "execution-engine benchmark slices resolved the wrong validation archetype",
    "execution_engine_current_phase_accurate": "execution-engine benchmark slices resolved the wrong current phase",
    "execution_engine_last_successful_phase_accurate": "execution-engine benchmark slices resolved the wrong last successful phase",
    "execution_engine_authoritative_lane_accurate": "execution-engine benchmark slices resolved the wrong authoritative lane",
    "execution_engine_target_lane_accurate": "execution-engine benchmark slices resolved the wrong target lane",
    "execution_engine_resume_token_accurate": "execution-engine benchmark slices resolved the wrong resume token",
    "execution_engine_host_family_accurate": "execution-engine benchmark slices resolved the wrong host family",
    "execution_engine_model_family_accurate": "execution-engine benchmark slices resolved the wrong model family",
    "execution_engine_component_id_accurate": "execution-engine benchmark slices resolved the wrong canonical engine component id",
    "execution_engine_canonical_component_id_accurate": "execution-engine benchmark slices resolved the wrong canonical component id",
    "execution_engine_identity_status_accurate": "execution-engine benchmark slices resolved the wrong identity status",
    "execution_engine_target_component_status_accurate": "execution-engine benchmark slices resolved the wrong target component status",
    "execution_engine_snapshot_reuse_status_accurate": "execution-engine benchmark slices resolved the wrong snapshot reuse posture",
    "execution_engine_reanchor_accurate": "execution-engine benchmark slices resolved the wrong re-anchor requirement",
    "execution_engine_delegation_guard_accurate": "execution-engine benchmark slices resolved the wrong delegation guard posture",
    "execution_engine_parallelism_guard_accurate": "execution-engine benchmark slices resolved the wrong parallelism guard posture",
    "explicit_workstream_expectation_positive": "explicit workstream scenarios lost expectation coverage",
    "critical_metric_coverage_complete": "critical metric coverage is incomplete",
    "selected_cache_profiles_clear_gate": "selected cache profiles do not all clear the hard quality gate",
    "latency_within_guardrail": "median latency exceeds the +15 ms guardrail",
    "prompt_delta_within_guardrail": "median prompt cost exceeds the +64-token guardrail",
    "total_payload_delta_within_guardrail": "median total payload exceeds the +96-token guardrail",
    "bootstrap_payload_delta_within_guardrail": "median bootstrap payload exceeds the +96-token guardrail",
    "tight_budget_behavior_healthy": "tighter-budget behavior fell below the 0.80 success floor",
    "architecture_latency_within_guardrail": "architecture latency exceeds the +15 ms guardrail",
    "widening_rate_healthy": "widening frequency exceeds the advisory threshold",
    "governance_packet_coverage_complete": "governance-family packet coverage is incomplete",
}
_PUBLIC_MODE_NAMES = {
    _ODYLITH_ON_MODE: _ODYLITH_ON_MODE,
    _ODYLITH_ON_NO_FANOUT_MODE: _ODYLITH_ON_NO_FANOUT_MODE,
    _REPO_SCAN_BASELINE_MODE: _REPO_SCAN_BASELINE_MODE,
    _LEGACY_REPO_SCAN_BASELINE_MODE: _REPO_SCAN_BASELINE_MODE,
    _ODYLITH_OFF_ALIAS: _ODYLITH_OFF_ALIAS,
    _RAW_AGENT_BASELINE_MODE: _ODYLITH_OFF_ALIAS,
}
_BENCHMARK_PROFILE_LABELS = {
    BENCHMARK_PROFILE_QUICK: "quick matched-pair developer lane",
    BENCHMARK_PROFILE_PROOF: "full publication proof lane",
    BENCHMARK_PROFILE_DIAGNOSTIC: "internal packet and prompt diagnostic lane",
}
_BENCHMARK_PROFILE_DESCRIPTIONS = {
    BENCHMARK_PROFILE_QUICK: (
        "Fast inner-loop signal: Odylith ON versus raw Codex CLI, warm cache only, "
        "and a bounded sentinel smoke subset unless the operator narrows explicitly."
    ),
    BENCHMARK_PROFILE_PROOF: (
        "Strict publication proof: the full benchmark corpus, warm and cold cache profiles, "
        "and the live end-to-end Odylith ON versus raw Codex CLI pair unless the operator narrows explicitly."
    ),
    BENCHMARK_PROFILE_DIAGNOSTIC: (
        "Internal tuning diagnostic: isolate Odylith packet and prompt creation versus the raw Codex CLI prompt bundle "
        "without running the live end-to-end Codex comparison."
    ),
}
_PROFILE_DEFAULT_MODES = {
    BENCHMARK_PROFILE_QUICK: (_ODYLITH_ON_MODE, _RAW_AGENT_BASELINE_MODE),
    BENCHMARK_PROFILE_PROOF: DEFAULT_MODES,
    BENCHMARK_PROFILE_DIAGNOSTIC: DEFAULT_MODES,
}
_PROFILE_DEFAULT_CACHE_PROFILES = {
    BENCHMARK_PROFILE_QUICK: ("warm",),
    BENCHMARK_PROFILE_PROOF: DEFAULT_CACHE_PROFILES,
    BENCHMARK_PROFILE_DIAGNOSTIC: ("warm",),
}
_MODE_ROLES = {
    _ODYLITH_ON_MODE: "primary candidate",
    _ODYLITH_ON_NO_FANOUT_MODE: "fanout-clamped Odylith",
    _REPO_SCAN_BASELINE_MODE: "repo-scan scaffold control",
    _RAW_AGENT_BASELINE_MODE: "odylith_off / raw Codex CLI honest baseline",
}
_PUBLISHED_TABLE_WHY_IT_MATTERS = {
    "lane_role": "Keeps the public claim honest: full Odylith scaffold versus raw Codex CLI on the same task.",
    "scenario_count": "Both lanes run the exact same corpus, so the comparison stays apples-to-apples.",
    "median_latency_ms": "Shows matched-pair benchmark time to valid outcome for the live run plus the harness validator, not interactive product latency.",
    "avg_latency_ms": "Shows the mean matched-pair benchmark time to valid outcome so long-tail slow cases stay visible.",
    "p95_latency_ms": "Shows the tail completion time for the slowest benchmark cases instead of letting the median hide them.",
    "median_instrumented_reasoning_duration_ms": "Shows time spent inside the live Codex CLI session itself.",
    "median_uninstrumented_overhead_ms": "Shows harness validator overhead added after the live Codex session completes.",
    "median_effective_tokens": "Shows full live Codex session input across the multi-turn run, not just the first prompt.",
    "median_total_payload_tokens": "Shows total live model-token spend across the multi-turn session.",
    "required_path_recall_rate": "Higher means Odylith finds more of the repo surfaces the task truly depends on.",
    "required_path_precision_rate": "Higher means Odylith keeps the evidence cone tighter and more relevant.",
    "hallucinated_surface_rate": "Lower means less made-up or unnecessary surface spread.",
    "validation_success_rate": "Higher means the lane more often reaches a validator-backed correct outcome.",
    "critical_required_path_recall_rate": "Protects high-stakes cases from missing critical repo truth.",
    "critical_validation_success_rate": "Protects critical changes from silent regressions.",
    "expectation_success_rate": "Higher means more scenarios finish the stated task contract on the live run.",
}


def _comparison_contract_label_bundle(comparison_contract: str) -> dict[str, str]:
    live = _is_live_comparison_contract(comparison_contract)
    if live:
        return {
            "lane_role_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["lane_role"],
            "scenario_count_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["scenario_count"],
            "latency_median": "Median time to valid outcome",
            "latency_avg": "Mean time to valid outcome",
            "latency_p95": "P95 time to valid outcome",
            "instrumented": "Median live agent runtime",
            "overhead": "Median validator overhead",
            "effective_tokens": "Median live session input tokens",
            "total_payload_tokens": "Median total model tokens",
            "validation_label": "Validation success rate",
            "critical_validation_label": "Critical validation success rate",
            "expectation_label": "Expectation success rate",
            "latency_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["median_latency_ms"],
            "latency_avg_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["avg_latency_ms"],
            "latency_p95_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["p95_latency_ms"],
            "instrumented_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["median_instrumented_reasoning_duration_ms"],
            "overhead_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["median_uninstrumented_overhead_ms"],
            "effective_tokens_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["median_effective_tokens"],
            "total_payload_tokens_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["median_total_payload_tokens"],
            "validation_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["validation_success_rate"],
            "critical_validation_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["critical_validation_success_rate"],
            "expectation_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["expectation_success_rate"],
        }
    return {
        "lane_role_why": "Keeps the internal diagnostic benchmark honest: full Odylith packet and prompt construction versus the raw Codex CLI prompt bundle on the same task.",
        "scenario_count_why": _PUBLISHED_TABLE_WHY_IT_MATTERS["scenario_count"],
        "latency_median": "Median packet time",
        "latency_avg": "Mean packet time",
        "latency_p95": "P95 packet time",
        "instrumented": "Median prompt-bundle build time",
        "overhead": "Median grounding validation overhead",
        "effective_tokens": "Median prompt-bundle input tokens",
        "total_payload_tokens": "Median total prompt-bundle payload tokens",
        "validation_label": "Validation-success proxy rate",
        "critical_validation_label": "Critical validation-success proxy rate",
        "expectation_label": "Expectation-success proxy rate",
        "latency_why": "Shows the packet construction time on the internal diagnostic benchmark before any live Codex session begins.",
        "latency_avg_why": "Shows the mean packet time so slow prompt-build cases stay visible.",
        "latency_p95_why": "Shows the long-tail packet time instead of hiding it behind the median.",
        "instrumented_why": "Shows time spent inside Odylith packet construction and prompt shaping on the internal diagnostic benchmark.",
        "overhead_why": "Shows post-build grounding harness overhead such as validation and accounting.",
        "effective_tokens_why": "Shows the model-facing prompt-bundle input size on the internal diagnostic benchmark.",
        "total_payload_tokens_why": "Shows the full grounding payload size across prompt, runtime contract, and operator diagnostics.",
        "validation_why": "Higher means the internal diagnostic benchmark more often satisfies the benchmark validator proxy before any live Codex session begins.",
        "critical_validation_why": "Protects critical grounding cases from missing packet-level validator proxy truth.",
        "expectation_why": "Higher means more scenarios satisfy the stated task contract on the internal diagnostic benchmark before model execution begins.",
    }


def _normalize_mode(mode: str) -> str:
    token = str(mode or "").strip()
    return _MODE_ALIASES.get(token, token)


def _normalize_benchmark_profile(profile: str) -> str:
    token = str(profile or "").strip().lower()
    if token in BENCHMARK_PROFILES:
        return token
    return DEFAULT_BENCHMARK_PROFILE


def _benchmark_profile_label(profile: str) -> str:
    normalized = _normalize_benchmark_profile(profile)
    return str(_BENCHMARK_PROFILE_LABELS.get(normalized, normalized)).strip() or normalized


def _benchmark_profile_description(profile: str) -> str:
    normalized = _normalize_benchmark_profile(profile)
    return str(_BENCHMARK_PROFILE_DESCRIPTIONS.get(normalized, "")).strip()


def _public_mode_name(mode: str) -> str:
    return _PUBLIC_MODE_NAMES.get(_normalize_mode(mode), _normalize_mode(mode))


def _table_header_mode_name(mode: str) -> str:
    return _public_mode_name(mode)


def _acceptance_hard_quality_gate_cleared(acceptance: Mapping[str, Any] | None) -> bool:
    if not isinstance(acceptance, Mapping):
        return False
    if "hard_quality_gate_cleared" in acceptance:
        return bool(acceptance.get("hard_quality_gate_cleared"))
    return str(acceptance.get("status", "")).strip() == "provisional_pass"


def _acceptance_failure_labels(tokens: Sequence[str]) -> list[str]:
    labels: list[str] = []
    for token in tokens:
        key = str(token).strip()
        if not key:
            continue
        label = _ACCEPTANCE_CHECK_LABELS.get(key, key.replace("_", " "))
        if label not in labels:
            labels.append(label)
    return labels


def _is_repo_scan_baseline_mode(mode: str) -> bool:
    return _normalize_mode(mode) == _REPO_SCAN_BASELINE_MODE


def _is_raw_agent_baseline_mode(mode: str) -> bool:
    return _normalize_mode(mode) == _RAW_AGENT_BASELINE_MODE


def _is_no_fanout_mode(mode: str) -> bool:
    return _normalize_mode(mode) == _ODYLITH_ON_NO_FANOUT_MODE


def _mode_uses_odylith(mode: str) -> bool:
    return _normalize_mode(mode) in {_ODYLITH_ON_MODE, _ODYLITH_ON_NO_FANOUT_MODE}


def _mode_supports_architecture_dossier(mode: str) -> bool:
    return _mode_uses_odylith(mode)


def _mode_contract_label(mode: str) -> str:
    return str(_MODE_ROLES.get(_normalize_mode(mode), _public_mode_name(mode))).strip() or _public_mode_name(mode)


def _mode_key_candidates(mode: str) -> tuple[str, ...]:
    normalized = _normalize_mode(mode)
    candidates = [normalized]
    raw = str(mode or "").strip()
    if raw and raw not in candidates:
        candidates.append(raw)
    if normalized == _REPO_SCAN_BASELINE_MODE and _LEGACY_REPO_SCAN_BASELINE_MODE not in candidates:
        candidates.append(_LEGACY_REPO_SCAN_BASELINE_MODE)
    return tuple(candidates)


def _lookup_mode_mapping(mapping: Mapping[str, Any], mode: str) -> Any:
    for candidate in _mode_key_candidates(mode):
        if candidate in mapping:
            return mapping[candidate]
    return None


def _raw_prompt_bundle(*, scenario: Mapping[str, Any]) -> dict[str, Any]:
    bundle = {
        "prompt": str(scenario.get("prompt", "")).strip(),
    }
    acceptance = [str(token).strip() for token in scenario.get("acceptance_criteria", []) if str(token).strip()]
    if acceptance:
        bundle["acceptance_criteria"] = acceptance
    return bundle


_PROMPT_VISIBLE_PATH_PATTERN = re.compile(
    r"`([^`\n]+)`|(?<![A-Za-z0-9_])([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)+|[A-Za-z0-9_.-]+\.(?:css|html|js|json|md|mmd|png|py|svg|toml|txt))(?=$|[\s`'\"),.:;\]])"
)


def _raw_prompt_visible_paths(*, repo_root: Path, raw_prompt: Mapping[str, Any]) -> list[str]:
    return odylith_benchmark_live_diagnostics.raw_prompt_visible_paths(
        repo_root=repo_root,
        raw_prompt=raw_prompt,
    )


def _is_live_comparison_contract(comparison_contract: str) -> bool:
    token = str(comparison_contract or "").strip()
    return token in {LIVE_COMPARISON_CONTRACT, LEGACY_LIVE_COMPARISON_CONTRACT}


def _comparison_contract_details(comparison_contract: str) -> dict[str, Any]:
    if _is_live_comparison_contract(comparison_contract):
        return {
            "primary_claim": LIVE_COMPARISON_CONTRACT,
            "odylith_on_affordances": [
                "grounding_packet",
                "selected_docs_and_repo_anchors",
                "execution_engine_posture_and_truthful_next_move",
                "scenario_declared_focused_local_checks",
                "preflight_focused_check_results_when_executed_in_disposable_workspace",
                "bounded_orchestration_and_recovery_policy",
            ],
            "raw_agent_affordances": [
                "same_host_cli_model",
                "same_reasoning_effort",
                "same_sandbox_and_approval_contract",
                "same_disposable_workspace_shape",
                "same_validation_commands",
                "raw_prompt_visible_repo_anchors_only",
            ],
        }
    return {
        "primary_claim": DIAGNOSTIC_COMPARISON_CONTRACT,
        "odylith_on_affordances": [
            "packet_and_prompt_construction",
            "selected_docs_and_repo_anchors",
            "bounded_packet_scaffold",
        ],
        "raw_agent_affordances": [
            "raw_prompt_bundle",
        ],
    }


def _raw_agent_orchestration_summary() -> dict[str, Any]:
    return {
        "native_mode": "local_only",
        "mode": "local_only",
        "delegate": False,
        "leaf_count": 0,
        "native_leaf_count": 0,
        "parallel_safety": "local_only",
        "manual_review_recommended": True,
        "clamped_no_fanout": False,
        "local_only_reasons": ["raw_agent_baseline_no_scaffolding"],
        "odylith_adoption": {},
    }


def _utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def benchmark_root(*, repo_root: Path) -> Path:
    return (Path(repo_root).resolve() / ".odylith" / "runtime" / "odylith-benchmarks").resolve()


def profile_latest_report_path(*, repo_root: Path, benchmark_profile: str) -> Path:
    profile = _normalize_benchmark_profile(benchmark_profile)
    return (benchmark_root(repo_root=repo_root) / f"latest-{profile}.v1.json").resolve()


def latest_report_path(*, repo_root: Path, benchmark_profile: str | None = None) -> Path:
    if benchmark_profile:
        return profile_latest_report_path(repo_root=repo_root, benchmark_profile=benchmark_profile)
    return (benchmark_root(repo_root=repo_root) / _REPORT_FILENAME).resolve()


def history_report_path(*, repo_root: Path, report_id: str) -> Path:
    token = str(report_id or "").strip() or "odylith-benchmark"
    return (benchmark_root(repo_root=repo_root) / f"{token}.json").resolve()


def progress_report_path(*, repo_root: Path) -> Path:
    return (benchmark_root(repo_root=repo_root) / _PROGRESS_FILENAME).resolve()


def active_runs_path(*, repo_root: Path) -> Path:
    return (benchmark_root(repo_root=repo_root) / _ACTIVE_RUNS_FILENAME).resolve()


def _benchmark_runtime_lock_path(*, repo_root: Path, target: Path) -> Path:
    token = hashlib.sha256(str(target.resolve()).encode("utf-8")).hexdigest()[:24]
    return (benchmark_root(repo_root=repo_root) / ".locks" / f"{token}.lock").resolve()


def _human_bytes_label(value: float) -> str:
    amount = max(0.0, float(value or 0.0))
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    index = 0
    while amount >= 1024.0 and index < len(units) - 1:
        amount /= 1024.0
        index += 1
    if index == 0:
        return f"{int(amount)} {units[index]}"
    return f"{amount:.1f} {units[index]}"


def _benchmark_runtime_storage_status(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    target = benchmark_root(repo_root=root)
    usage_root = target if target.exists() else root
    usage = shutil.disk_usage(str(usage_root))
    return {
        "path": str(usage_root),
        "free_bytes": int(usage.free),
        "used_bytes": int(usage.used),
        "total_bytes": int(usage.total),
    }


def _benchmark_runtime_storage_error(*, repo_root: Path) -> RuntimeError:
    status = _benchmark_runtime_storage_status(repo_root=repo_root)
    benchmark_path = benchmark_root(repo_root=Path(repo_root).resolve())
    free_label = _human_bytes_label(status.get("free_bytes", 0))
    minimum_label = _human_bytes_label(_MIN_BENCHMARK_RUNTIME_FREE_BYTES)
    return RuntimeError(
        "benchmark runtime free space is too low to create progress, lock, and disposable workspace artifacts: "
        f"{free_label} available at `{status.get('path', '')}`; need at least {minimum_label}. "
        f"Clear stale benchmark runtime history under `{benchmark_path}` or reclaim local cache/runtime space before rerunning."
    )


def _require_benchmark_runtime_space(*, repo_root: Path) -> dict[str, Any]:
    status = _benchmark_runtime_storage_status(repo_root=repo_root)
    if int(status.get("free_bytes", 0) or 0) < _MIN_BENCHMARK_RUNTIME_FREE_BYTES:
        raise _benchmark_runtime_storage_error(repo_root=repo_root)
    return status


@contextlib.contextmanager
def _benchmark_runtime_file_lock(*, repo_root: Path, target: Path) -> Iterator[Path]:
    lock_path = _benchmark_runtime_lock_path(repo_root=repo_root, target=target)
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        with lock_path.open("a+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield lock_path
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            raise _benchmark_runtime_storage_error(repo_root=repo_root) from exc
        raise


def _benchmark_runtime_write_json_if_changed(
    *,
    repo_root: Path,
    path: Path,
    payload: Any,
) -> bool:
    target = Path(path).resolve()
    rendered = json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with _benchmark_runtime_file_lock(repo_root=repo_root, target=target):
            existing = None
            if target.is_file():
                with contextlib.suppress(OSError):
                    existing = target.read_text(encoding="utf-8")
            if existing == rendered:
                return False
            target.parent.mkdir(parents=True, exist_ok=True)
            fd, temp_name = tempfile.mkstemp(prefix=f".{target.name}.", dir=str(target.parent))
            temp_path = Path(temp_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(rendered)
                os.replace(temp_path, target)
            finally:
                if temp_path.exists():
                    with contextlib.suppress(OSError):
                        temp_path.unlink()
            return True
    except OSError as exc:
        if exc.errno == errno.ENOSPC:
            raise _benchmark_runtime_storage_error(repo_root=repo_root) from exc
        raise


def _benchmark_runtime_remove_file(*, repo_root: Path, path: Path) -> bool:
    target = Path(path).resolve()
    with _benchmark_runtime_file_lock(repo_root=repo_root, target=target):
        if not target.exists():
            return False
        with contextlib.suppress(OSError):
            target.unlink()
        return not target.exists()


def _active_run_token(value: Any, *, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "").strip()).strip("-.")
    return token or fallback


def _active_run_progress_path(
    *,
    repo_root: Path,
    report_id: str,
    benchmark_profile: str,
    shard_index: int,
    shard_count: int,
    owning_pid: int,
) -> Path:
    filename = (
        f"progress-{_active_run_token(report_id, fallback='benchmark')}"
        f"-{_active_run_token(benchmark_profile, fallback='proof')}"
        f"-s{max(1, int(shard_index)):02d}-of-{max(1, int(shard_count)):02d}"
        f"-pid{max(0, int(owning_pid))}.v1.json"
    )
    return (benchmark_root(repo_root=repo_root) / filename).resolve()


def _active_run_identity(progress: Mapping[str, Any]) -> tuple[str, str, int, int, int]:
    return (
        str(progress.get("report_id", "")).strip(),
        _normalize_benchmark_profile(str(progress.get("benchmark_profile", "")).strip()),
        max(1, int(progress.get("shard_index", 1) or 1)),
        max(1, int(progress.get("shard_count", 1) or 1)),
        max(0, int(progress.get("owning_pid", 0) or 0)),
    )


def _history_report_for_progress(*, repo_root: Path, progress: Mapping[str, Any]) -> Path:
    return history_report_path(
        repo_root=Path(repo_root).resolve(),
        report_id=str(progress.get("report_id", "")).strip(),
    )


def _history_report_exists_for_progress(*, repo_root: Path, progress: Mapping[str, Any]) -> bool:
    explicit_path = Path(str(progress.get("history_report_path", "")).strip()) if str(progress.get("history_report_path", "")).strip() else None
    if explicit_path is not None and explicit_path.is_file():
        return True
    return _history_report_for_progress(repo_root=repo_root, progress=progress).is_file()


def _active_run_entry(*, repo_root: Path, progress: Mapping[str, Any]) -> dict[str, Any]:
    report_id, benchmark_profile, shard_index, shard_count, owning_pid = _active_run_identity(progress)
    progress_path = _active_run_progress_path(
        repo_root=repo_root,
        report_id=report_id,
        benchmark_profile=benchmark_profile,
        shard_index=shard_index,
        shard_count=shard_count,
        owning_pid=owning_pid,
    )
    return {
        "report_id": report_id,
        "benchmark_profile": benchmark_profile,
        "comparison_contract": str(progress.get("comparison_contract", "")).strip(),
        "repo_root": str(Path(repo_root).resolve()),
        "started_utc": str(progress.get("started_utc", "")).strip(),
        "updated_utc": str(progress.get("updated_utc", "")).strip(),
        "status": str(progress.get("status", "")).strip() or "running",
        "shard_index": shard_index,
        "shard_count": shard_count,
        "owning_pid": owning_pid,
        "progress_path": str(progress_path),
    }


def _load_active_runs(repo_root: Path) -> list[dict[str, Any]]:
    payload = odylith_context_cache.read_json_object(active_runs_path(repo_root=repo_root))
    rows = payload.get("runs") if isinstance(payload.get("runs"), list) else []
    normalized_rows = [dict(row) for row in rows if isinstance(row, Mapping)]
    if normalized_rows:
        return normalized_rows
    root = Path(repo_root).resolve()
    benchmark_runtime_present = bool(
        _benchmark_owned_codex_process_ids()
        or _benchmark_temp_worktrees(repo_root=root)
        or _benchmark_temp_directories(repo_root=root)
    )
    recovered: dict[tuple[str, str, int, int, int], dict[str, Any]] = {}
    benchmark_dir = benchmark_root(repo_root=root)
    if not benchmark_dir.is_dir():
        return []
    with contextlib.suppress(OSError):
        for progress_path in sorted(benchmark_dir.glob("progress-*.json")):
            payload = odylith_context_cache.read_json_object(progress_path)
            if not isinstance(payload, Mapping):
                continue
            progress = dict(payload)
            status = str(progress.get("status", "")).strip() or "running"
            if status != "running":
                continue
            identity = _active_run_identity(progress)
            owning_pid = identity[-1]
            if owning_pid > 0:
                if not _process_exists(owning_pid):
                    continue
            elif not benchmark_runtime_present:
                continue
            entry = _active_run_entry(repo_root=root, progress=progress)
            entry["progress_path"] = str(progress_path.resolve())
            recovered[identity] = entry
    return sorted(
        recovered.values(),
        key=lambda row: (
            str(row.get("updated_utc", "")).strip(),
            str(row.get("report_id", "")).strip(),
            int(row.get("shard_index", 1) or 1),
        ),
        reverse=True,
    )


def _write_active_runs(*, repo_root: Path, runs: Sequence[Mapping[str, Any]]) -> None:
    path = active_runs_path(repo_root=repo_root)
    normalized_runs = [
        dict(row)
        for row in runs
        if isinstance(row, Mapping) and str(row.get("report_id", "")).strip()
    ]
    if not normalized_runs:
        _benchmark_runtime_remove_file(repo_root=repo_root, path=path)
        return
    payload = {
        "contract": ACTIVE_RUNS_CONTRACT,
        "version": ACTIVE_RUNS_VERSION,
        "repo_root": str(Path(repo_root).resolve()),
        "updated_utc": _utc_now(),
        "runs": normalized_runs,
    }
    _benchmark_runtime_write_json_if_changed(
        repo_root=repo_root,
        path=path,
        payload=payload,
    )


def _sync_active_run_progress(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
) -> None:
    root = Path(repo_root).resolve()
    report_id, benchmark_profile, shard_index, shard_count, owning_pid = _active_run_identity(payload)
    progress_path = _active_run_progress_path(
        repo_root=root,
        report_id=report_id,
        benchmark_profile=benchmark_profile,
        shard_index=shard_index,
        shard_count=shard_count,
        owning_pid=owning_pid,
    )
    _benchmark_runtime_write_json_if_changed(
        repo_root=root,
        path=progress_path,
        payload=dict(payload),
    )
    status = str(payload.get("status", "")).strip() or "running"
    active_runs_file = active_runs_path(repo_root=root)
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(active_runs_file)):
        runs = [
            row
            for row in _load_active_runs(root)
            if (
                str(row.get("report_id", "")).strip(),
                _normalize_benchmark_profile(str(row.get("benchmark_profile", "")).strip()),
                max(1, int(row.get("shard_index", 1) or 1)),
                max(1, int(row.get("shard_count", 1) or 1)),
                max(0, int(row.get("owning_pid", 0) or 0)),
            )
            != (report_id, benchmark_profile, shard_index, shard_count, owning_pid)
        ]
        if status == "running":
            runs.append(_active_run_entry(repo_root=root, progress=payload))
        runs.sort(
            key=lambda row: (
                str(row.get("updated_utc", "")).strip(),
                str(row.get("report_id", "")).strip(),
                int(row.get("shard_index", 1) or 1),
            ),
            reverse=True,
        )
        _write_active_runs(repo_root=root, runs=runs)


def _clear_active_run_progress(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
) -> None:
    root = Path(repo_root).resolve()
    report_id, benchmark_profile, shard_index, shard_count, owning_pid = _active_run_identity(payload)
    progress_path = _active_run_progress_path(
        repo_root=root,
        report_id=report_id,
        benchmark_profile=benchmark_profile,
        shard_index=shard_index,
        shard_count=shard_count,
        owning_pid=owning_pid,
    )
    if _history_report_exists_for_progress(repo_root=root, progress=payload):
        _benchmark_runtime_remove_file(repo_root=root, path=progress_path)
    else:
        _benchmark_runtime_write_json_if_changed(
            repo_root=root,
            path=progress_path,
            payload=dict(payload),
        )
    active_runs_file = active_runs_path(repo_root=root)
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(active_runs_file)):
        runs = [
            row
            for row in _load_active_runs(root)
            if (
                str(row.get("report_id", "")).strip(),
                _normalize_benchmark_profile(str(row.get("benchmark_profile", "")).strip()),
                max(1, int(row.get("shard_index", 1) or 1)),
                max(1, int(row.get("shard_count", 1) or 1)),
                max(0, int(row.get("owning_pid", 0) or 0)),
            )
            != (report_id, benchmark_profile, shard_index, shard_count, owning_pid)
        ]
        _write_active_runs(repo_root=root, runs=runs)


def _tree_identity_from_progress_payload(*, repo_root: Path, progress_payload: Mapping[str, Any]) -> dict[str, Any]:
    selection = (
        dict(progress_payload.get("selection", {}))
        if isinstance(progress_payload.get("selection"), Mapping)
        else {}
    )
    current = benchmark_tree_identity(repo_root=repo_root, selection=selection)
    return {
        "git_branch": str(progress_payload.get("git_branch", "")).strip() or str(current.get("git_branch", "")).strip(),
        "git_commit": str(progress_payload.get("git_commit", "")).strip() or str(current.get("git_commit", "")).strip(),
        "git_dirty": bool(progress_payload.get("git_dirty", current.get("git_dirty"))),
        "repo_dirty_paths": [
            str(token).strip()
            for token in progress_payload.get("repo_dirty_paths", current.get("repo_dirty_paths", []))
            if isinstance(progress_payload.get("repo_dirty_paths", current.get("repo_dirty_paths", [])), list)
            and str(token).strip()
        ],
        "selection_fingerprint": str(progress_payload.get("selection_fingerprint", "")).strip()
        or str(current.get("selection_fingerprint", "")).strip(),
        "corpus_fingerprint": str(progress_payload.get("corpus_fingerprint", "")).strip()
        or str(current.get("corpus_fingerprint", "")).strip(),
        "snapshot_overlay_fingerprint": str(progress_payload.get("snapshot_overlay_fingerprint", "")).strip()
        or str(current.get("snapshot_overlay_fingerprint", "")).strip(),
        "source_posture": str(progress_payload.get("source_posture", "")).strip()
        or str(current.get("source_posture", "")).strip(),
    }


def _reconstruct_progress_selection(
    *,
    repo_root: Path,
    progress_payload: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], Mapping[str, Any]]:
    selection = (
        dict(progress_payload.get("selection", {}))
        if isinstance(progress_payload.get("selection"), Mapping)
        else {}
    )
    benchmark_profile = str(progress_payload.get("benchmark_profile", "")).strip() or str(
        selection.get("benchmark_profile", "")
    ).strip()
    case_ids = [
        str(token).strip()
        for token in selection.get("case_ids", selection.get("scenario_ids", []))
        if isinstance(selection.get("case_ids", selection.get("scenario_ids", [])), list) and str(token).strip()
    ]
    families = [
        str(token).strip()
        for token in selection.get("family_filters", [])
        if isinstance(selection.get("family_filters"), list) and str(token).strip()
    ]
    shard_count = max(
        1,
        int(progress_payload.get("shard_count", selection.get("shard_count", 1)) or 1),
    )
    shard_index = max(
        1,
        int(progress_payload.get("shard_index", selection.get("shard_index", 1)) or 1),
    )
    limit = max(0, int(selection.get("limit", 0) or 0))
    all_scenarios = load_benchmark_scenarios(repo_root=repo_root)
    selection_state = _resolve_benchmark_scenario_selection(
        all_scenarios=all_scenarios,
        benchmark_profile=benchmark_profile,
        case_ids=case_ids,
        families=families,
        shard_count=shard_count,
        shard_index=shard_index,
        limit=limit,
    )
    return (
        [dict(row) for row in selection_state.get("scenarios", [])],
        [dict(row) for row in selection_state.get("all_scenarios", [])],
        selection_state,
    )


def _persist_orphaned_progress_failed_report(
    *,
    repo_root: Path,
    progress_payload: Mapping[str, Any],
    error: BaseException | str,
) -> bool:
    root = Path(repo_root).resolve()
    history_path = _history_report_for_progress(repo_root=root, progress=progress_payload)
    if history_path.is_file():
        return False
    corpus = odylith_context_cache.read_json_object(store.optimization_evaluation_corpus_path(repo_root=root))
    corpus_contract = odylith_benchmark_contract.benchmark_corpus_contract(corpus)
    scenarios, all_scenarios, selection_state = _reconstruct_progress_selection(
        repo_root=root,
        progress_payload=progress_payload,
    )
    payload = dict(progress_payload)
    payload.update(
        {
            "updated_utc": _utc_now(),
            "status": "failed",
            "phase": "orphaned_progress_recovery",
            "error": _benchmark_exception_text(error),
            "selection_strategy": str(progress_payload.get("selection_strategy", "")).strip()
            or str(selection_state.get("selection_strategy", "")).strip()
            or "manual_selection",
        }
    )
    tree_identity = _tree_identity_from_progress_payload(repo_root=root, progress_payload=payload)
    report = _failed_benchmark_report(
        repo_root=root,
        report_id=str(payload.get("report_id", "")).strip(),
        benchmark_profile=str(payload.get("benchmark_profile", "")).strip(),
        comparison_contract=str(payload.get("comparison_contract", "")).strip(),
        modes=[
            str(token).strip()
            for token in payload.get("modes", [])
            if isinstance(payload.get("modes"), list) and str(token).strip()
        ],
        cache_profiles=[
            str(token).strip()
            for token in payload.get("cache_profiles", [])
            if isinstance(payload.get("cache_profiles"), list) and str(token).strip()
        ],
        primary_cache_profile=str(payload.get("primary_cache_profile", "")).strip(),
        scenarios=scenarios,
        all_scenarios=all_scenarios,
        progress_payload=payload,
        selection_strategy=str(payload.get("selection_strategy", "")).strip() or "manual_selection",
        latest_eligible=bool(payload.get("latest_eligible")),
        startup_hygiene={},
        corpus_contract=corpus_contract,
        tree_identity=tree_identity,
        error=error,
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=history_path,
        payload=report,
        lock_key=str(history_path),
    )
    return True


def _fingerprint_json_payload(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(json.dumps(dict(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def _call_with_supported_kwargs(function: Any, /, **kwargs: Any) -> Any:
    try:
        signature = inspect.signature(function)
    except (TypeError, ValueError):
        return function(**kwargs)
    if any(parameter.kind == inspect.Parameter.VAR_KEYWORD for parameter in signature.parameters.values()):
        return function(**kwargs)
    supported = {
        key: value
        for key, value in kwargs.items()
        if key in signature.parameters
    }
    return function(**supported)


def _selection_fingerprint(selection: Mapping[str, Any]) -> str:
    return _fingerprint_json_payload(selection)


def _safe_resolve_path(path: Path) -> Path | None:
    with contextlib.suppress(OSError, RuntimeError):
        return Path(path).resolve()
    return None


def _snapshot_overlay_fingerprint(*, repo_root: Path, snapshot_paths: Sequence[str]) -> str:
    normalized_paths = _dedupe_path_strings(snapshot_paths)
    if not normalized_paths:
        return ""
    existing_paths = [
        str(path)
        for path in (
            _safe_resolve_path(Path(repo_root).resolve() / token)
            for token in normalized_paths
        )
        if path is not None and path.exists()
    ]
    if not existing_paths:
        return ""
    return odylith_context_cache.fingerprint_paths(existing_paths)


def _benchmark_source_posture(*, repo_root: Path) -> str:
    with contextlib.suppress(Exception):
        from odylith.install.manager import version_status

        status = version_status(repo_root=repo_root)
        posture = str(getattr(status, "posture", "") or "").strip()
        runtime_source = str(getattr(status, "runtime_source", "") or "").strip()
        if posture and runtime_source:
            return f"{posture}:{runtime_source}"
        if posture:
            return posture
        if runtime_source:
            return runtime_source
    return "unknown"


def benchmark_tree_identity(
    *,
    repo_root: Path,
    selection: Mapping[str, Any],
    snapshot_paths: Sequence[str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    return {
        "git_branch": str(store._git_branch_name(repo_root=root) or "").strip(),  # noqa: SLF001
        "git_commit": str(store._git_head_oid(repo_root=root) or "").strip(),  # noqa: SLF001
        "git_dirty": bool(_dirty_repo_paths(root)),
        "repo_dirty_paths": _dirty_repo_paths(root),
        "selection_fingerprint": _selection_fingerprint(selection),
        "corpus_fingerprint": odylith_context_cache.fingerprint_paths(
            [store.optimization_evaluation_corpus_path(repo_root=root)]
        ),
        "snapshot_overlay_fingerprint": _snapshot_overlay_fingerprint(repo_root=root, snapshot_paths=snapshot_paths),
        "source_posture": _benchmark_source_posture(repo_root=root),
    }


def benchmark_report_matches_current_tree(*, repo_root: Path, report: Mapping[str, Any]) -> bool:
    if not isinstance(report, Mapping):
        return False
    selection = dict(report.get("selection", {})) if isinstance(report.get("selection"), Mapping) else {}
    snapshot_paths = (
        [str(token).strip() for token in report.get("snapshot_overlay_paths", []) if str(token).strip()]
        if isinstance(report.get("snapshot_overlay_paths"), list)
        else []
    )
    current = benchmark_tree_identity(repo_root=repo_root, selection=selection, snapshot_paths=snapshot_paths)
    for key in (
        "git_branch",
        "git_commit",
        "git_dirty",
        "repo_dirty_paths",
        "selection_fingerprint",
        "corpus_fingerprint",
        "snapshot_overlay_fingerprint",
        "source_posture",
    ):
        if report.get(key) != current.get(key):
            return False
    return True


def load_latest_benchmark_report(*, repo_root: Path, benchmark_profile: str | None = None) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    path = latest_report_path(repo_root=root, benchmark_profile=benchmark_profile)
    report = odylith_context_cache.read_json_object(path)
    if report or not benchmark_profile:
        return report
    normalized_profile = _normalize_benchmark_profile(benchmark_profile)
    if normalized_profile != BENCHMARK_PROFILE_PROOF:
        return {}
    canonical_path = latest_report_path(repo_root=root)
    canonical_report = odylith_context_cache.read_json_object(canonical_path)
    if not canonical_report:
        return {}
    canonical_profile = _normalize_benchmark_profile(
        str(canonical_report.get("benchmark_profile", "")).strip() or BENCHMARK_PROFILE_PROOF
    )
    if canonical_profile != BENCHMARK_PROFILE_PROOF:
        return {}
    return canonical_report


def load_benchmark_progress(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    _prune_stale_benchmark_progress(repo_root=root, clear_shared_progress=False)
    active_entries = _load_active_runs(root)
    if active_entries:
        grouped_payloads: dict[str, list[dict[str, Any]]] = {}
        for entry in active_entries:
            progress_path = Path(str(entry.get("progress_path", "")).strip())
            if not progress_path.is_file():
                continue
            payload = odylith_context_cache.read_json_object(progress_path)
            if not payload:
                continue
            grouped_payloads.setdefault(str(payload.get("report_id", "")).strip(), []).append(payload)
        if grouped_payloads:
            selected_group = max(
                grouped_payloads.values(),
                key=lambda rows: max(str(row.get("updated_utc", "")).strip() for row in rows),
            )
            latest_payload = max(selected_group, key=lambda row: str(row.get("updated_utc", "")).strip())
            return {
                **dict(latest_payload),
                "aggregate_source": "active_runs",
                "active_shard_count": len(selected_group),
                "active_shard_indices": sorted(
                    {max(1, int(row.get("shard_index", 1) or 1)) for row in selected_group}
                ),
                "scenario_count": sum(int(row.get("scenario_count", 0) or 0) for row in selected_group),
                "total_results": sum(int(row.get("total_results", 0) or 0) for row in selected_group),
                "completed_cache_profiles": sum(int(row.get("completed_cache_profiles", 0) or 0) for row in selected_group),
                "completed_scenarios": sum(int(row.get("completed_scenarios", 0) or 0) for row in selected_group),
                "completed_results": sum(int(row.get("completed_results", 0) or 0) for row in selected_group),
                "started_utc": min(str(row.get("started_utc", "")).strip() for row in selected_group),
                "updated_utc": max(str(row.get("updated_utc", "")).strip() for row in selected_group),
            }
    shared_payload = odylith_context_cache.read_json_object(progress_report_path(repo_root=root))
    return shared_payload if isinstance(shared_payload, Mapping) else {}


def _benchmark_exception_text(exc: BaseException | str) -> str:
    if isinstance(exc, BaseException):
        return f"{type(exc).__name__}: {exc}"
    return str(exc).strip() or "benchmark runner exception"


def _scenario_exception_result(
    *,
    scenario: Mapping[str, Any],
    mode: str,
    error: BaseException | str,
    live_runner: bool = False,
    packet_source: str = "",
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    required_paths = [str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()]
    supporting_paths = _scenario_supporting_paths(scenario)
    critical_paths = [str(token).strip() for token in scenario.get("critical_paths", []) if str(token).strip()]
    expected_write_paths = _scenario_expected_write_paths(scenario)
    command_count = len([str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()])
    error_text = _benchmark_exception_text(error)
    resolved_packet_source = (
        str(packet_source).strip()
        or ("raw_codex_cli" if normalized_mode == _RAW_AGENT_BASELINE_MODE else "benchmark_exception")
    )
    result: dict[str, Any] = {
        "kind": str(scenario.get("kind", "")).strip() or "packet",
        "mode": normalized_mode,
        "packet_source": resolved_packet_source,
        "latency_ms": 0.0,
        "packet": {
            "within_budget": False,
            "route_ready": False,
            "live_status": "failed",
        }
        if live_runner or _is_live_public_mode(normalized_mode)
        else {"within_budget": False, "route_ready": False},
        "expectation_ok": False,
        "expectation_details": {
            "live_runner": bool(live_runner or _is_live_public_mode(normalized_mode)),
            "codex_status": "failed" if live_runner or _is_live_public_mode(normalized_mode) else "not_applicable",
            "validator_status": "failed",
            "validator_status_basis": "benchmark_exception",
            "structured_summary": error_text,
            "validator_backed_noop_completion": False,
            "validator_backed_completion": False,
            "benchmark_exception": error_text,
        },
        "required_path_recall": 1.0 if not required_paths else 0.0,
        "required_path_misses": required_paths,
        "critical_path_misses": critical_paths,
        "observed_paths": [],
        "observed_path_sources": [],
        "observed_path_count": 0,
        "supporting_path_count": len(supporting_paths),
        "supporting_path_hits": [],
        "required_path_precision_basis": "required_plus_supporting_paths" if supporting_paths else "required_paths",
        "required_path_precision": 1.0 if not required_paths and not supporting_paths else 0.0,
        "hallucinated_surface_count": 0,
        "hallucinated_surface_rate": 0.0,
        "hallucinated_surfaces": [],
        "expected_write_path_count": len(expected_write_paths),
        "candidate_write_path_count": 0,
        "candidate_write_paths": [],
        "write_surface_precision": 1.0 if not expected_write_paths else 0.0,
        "unnecessary_widening_count": 0,
        "unnecessary_widening_rate": 0.0,
        "unnecessary_widening_paths": [],
        "selected_doc_count": 0,
        "selected_test_count": 0,
        "selected_command_count": 0,
        "strict_gate_command_count": command_count,
        "effective_estimated_tokens": 0,
        "total_payload_estimated_tokens": 0,
        "validation_success_proxy": 0.0,
        "validation_results": {
            "status": "failed",
            "status_basis": "benchmark_exception",
            "duration_ms": 0.0,
            "results": [],
            "summary": error_text,
        },
        "preflight_evidence_mode": "none",
        "preflight_evidence_commands": [],
        "preflight_evidence_result_status": "not_applicable",
        "full_scan": {},
        "orchestration": {"leaf_count": 0},
        "benchmark_exception": error_text,
    }
    if live_runner or _is_live_public_mode(normalized_mode):
        result["live_execution"] = {
            "exit_code": 1,
            "structured_output": {
                "status": "failed",
                "summary": error_text,
                "changed_files": [],
                "validation_commands_run": [],
                "validation_summary": "benchmark_exception",
                "notes": [],
            },
            "stdout_tail": "",
            "stderr_tail": error_text,
            "preflight_evidence_mode": "none",
            "preflight_evidence_commands": [],
            "preflight_evidence_result_status": "not_applicable",
            "observed_path_sources": [],
            "failure_artifacts": {
                "tracked_paths": [*required_paths, *expected_write_paths],
                "workspace_state_post_codex": {},
                "workspace_state_pre_validator": {},
            },
            "benchmark_exception": error_text,
        }
    return result


def _benchmark_owned_codex_process_ids() -> list[int]:
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        completed = subprocess.run(
            ["ps", "-ax", "-o", "pid=,command="],
            text=True,
            capture_output=True,
            check=False,
        )
        if int(completed.returncode or 0) != 0:
            return []
        rows: list[int] = []
        for raw in str(completed.stdout or "").splitlines():
            line = raw.strip()
            if not line:
                continue
            pid_token, _, command = line.partition(" ")
            with contextlib.suppress(ValueError):
                pid = int(pid_token)
                if pid <= 0 or "codex exec" not in command or _BENCHMARK_TEMP_MARKER not in command:
                    continue
                rows.append(pid)
        return sorted(set(rows))
    return []


def _process_exists(pid: int) -> bool:
    with contextlib.suppress(ProcessLookupError):
        os.kill(int(pid), 0)
        return True
    return False


def _terminate_processes(*, pids: Sequence[int]) -> dict[str, Any]:
    requested = sorted({int(pid) for pid in pids if int(pid) > 0})
    if not requested:
        return {
            "requested_pid_count": 0,
            "terminated_pid_count": 0,
            "forced_pid_count": 0,
            "remaining_pid_count": 0,
            "terminated_pids": [],
            "forced_pids": [],
            "remaining_pids": [],
        }
    for pid in requested:
        with contextlib.suppress(ProcessLookupError):
            os.kill(pid, signal.SIGTERM)
    time.sleep(0.2)
    remaining = [pid for pid in requested if _process_exists(pid)]
    forced: list[int] = []
    if remaining:
        for pid in remaining:
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
                forced.append(pid)
        time.sleep(0.2)
    still_running = [pid for pid in requested if _process_exists(pid)]
    terminated = [pid for pid in requested if pid not in still_running]
    return {
        "requested_pid_count": len(requested),
        "terminated_pid_count": len(terminated),
        "forced_pid_count": len(forced),
        "remaining_pid_count": len(still_running),
        "terminated_pids": terminated,
        "forced_pids": forced,
        "remaining_pids": still_running,
    }


def _is_benchmark_temp_worktree(path: Path) -> bool:
    resolved = Path(path).resolve()
    if _BENCHMARK_LIVE_WORKTREE_MARKER in resolved.as_posix():
        return True
    return any(part.startswith(_BENCHMARK_LIVE_WORKTREE_MARKER) for part in resolved.parts)


def _benchmark_temp_worktrees(*, repo_root: Path) -> list[Path]:
    rows: list[Path] = []
    seen: set[Path] = set()
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        completed = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=str(Path(repo_root).resolve()),
            text=True,
            capture_output=True,
            check=False,
        )
        if int(completed.returncode or 0) == 0:
            for raw in str(completed.stdout or "").splitlines():
                if not raw.startswith("worktree "):
                    continue
                candidate = Path(raw.split(" ", 1)[1].strip()).resolve()
                if candidate not in seen and _is_benchmark_temp_worktree(candidate):
                    seen.add(candidate)
                    rows.append(candidate)
    clone_parent = odylith_benchmark_isolation.benchmark_workspace_parent(
        repo_root=Path(repo_root).resolve(),
        create=False,
    )
    if clone_parent.is_dir():
        with contextlib.suppress(OSError):
            for child in clone_parent.iterdir():
                if not child.is_dir() or not child.name.startswith(_BENCHMARK_LIVE_WORKTREE_MARKER):
                    continue
                resolved = child.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                rows.append(resolved)
    return sorted(rows)


def _cleanup_benchmark_worktrees(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    removed: list[str] = []
    failed: list[str] = []
    for worktree in _benchmark_temp_worktrees(repo_root=root):
        detached_clone_workspace = (worktree / "workspace" / ".git").resolve()
        if detached_clone_workspace.exists():
            with contextlib.suppress(OSError):
                shutil.rmtree(worktree)
            if not worktree.exists():
                removed.append(str(worktree))
            else:
                failed.append(str(worktree))
            continue
        completed = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree)],
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        )
        if int(completed.returncode or 0) == 0:
            removed.append(str(worktree))
        else:
            failed.append(str(worktree))
    subprocess.run(
        ["git", "worktree", "prune"],
        cwd=str(root),
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "removed_worktree_count": len(removed),
        "failed_worktree_count": len(failed),
        "removed_worktrees": removed,
        "failed_worktrees": failed,
    }


def _benchmark_runtime_temp_root(*, repo_root: Path) -> Path:
    return (
        Path(repo_root).resolve()
        / ".odylith"
        / "runtime"
        / "odylith-benchmark-temp"
    ).resolve()


def _benchmark_temp_directory_roots(*, repo_root: Path) -> list[Path]:
    return [_benchmark_runtime_temp_root(repo_root=repo_root)]


def _benchmark_temp_directories(*, repo_root: Path) -> list[Path]:
    rows: list[Path] = []
    seen: set[Path] = set()
    for root in _benchmark_temp_directory_roots(repo_root=repo_root):
        if not root.is_dir():
            continue
        with contextlib.suppress(OSError):
            for child in root.iterdir():
                name = child.name
                if not any(name.startswith(prefix) for prefix in _BENCHMARK_RUNTIME_TEMP_DIRECTORY_PREFIXES):
                    continue
                with contextlib.suppress(OSError, RuntimeError):
                    resolved = child.resolve()
                    if resolved in seen or not resolved.is_dir():
                        continue
                    seen.add(resolved)
                    rows.append(resolved)
    return sorted(rows)


def _prune_stale_benchmark_progress(*, repo_root: Path, clear_shared_progress: bool) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    active_runs_file = active_runs_path(repo_root=root)
    with odylith_context_cache.advisory_lock(repo_root=root, key=str(active_runs_file)):
        active_entries = _load_active_runs(root)
        active_runtime_present = bool(
            _benchmark_owned_codex_process_ids()
            or _benchmark_temp_worktrees(repo_root=root)
            or _benchmark_temp_directories(repo_root=root)
        )
        stale_entries: list[dict[str, Any]] = []
        retained_entries: list[dict[str, Any]] = []
        synthesized_failed_reports: list[str] = []
        processed_progress_paths: set[Path] = set()
        for entry in active_entries:
            status = str(entry.get("status", "")).strip() or "running"
            owning_pid = max(0, int(entry.get("owning_pid", 0) or 0))
            progress_path = Path(str(entry.get("progress_path", "")).strip())
            progress_payload = (
                odylith_context_cache.read_json_object(progress_path)
                if progress_path and progress_path.exists()
                else {}
            )
            if progress_path:
                processed_progress_paths.add(progress_path.resolve())
            if status != "running":
                if not _history_report_exists_for_progress(
                    repo_root=root,
                    progress=progress_payload if isinstance(progress_payload, Mapping) and progress_payload else entry,
                ):
                    if _persist_orphaned_progress_failed_report(
                        repo_root=root,
                        progress_payload=progress_payload if isinstance(progress_payload, Mapping) and progress_payload else entry,
                        error=BenchmarkRunInterrupted("benchmark shard entered teardown without a persisted final report"),
                    ):
                        synthesized_failed_reports.append(str(entry.get("report_id", "")).strip())
                stale_entries.append(entry)
                continue
            if progress_path and not progress_path.exists():
                if not _history_report_exists_for_progress(repo_root=root, progress=entry):
                    if _persist_orphaned_progress_failed_report(
                        repo_root=root,
                        progress_payload=entry,
                        error=BenchmarkRunInterrupted("process lost progress state before persisting final report"),
                    ):
                        synthesized_failed_reports.append(str(entry.get("report_id", "")).strip())
                stale_entries.append(entry)
                continue
            if owning_pid > 0 and _process_exists(owning_pid):
                retained_entries.append(entry)
                continue
            if owning_pid <= 0 and active_runtime_present:
                retained_entries.append(entry)
                continue
            if not _history_report_exists_for_progress(
                repo_root=root,
                progress=progress_payload if isinstance(progress_payload, Mapping) and progress_payload else entry,
            ):
                if _persist_orphaned_progress_failed_report(
                    repo_root=root,
                    progress_payload=progress_payload if isinstance(progress_payload, Mapping) and progress_payload else entry,
                    error=BenchmarkRunInterrupted("benchmark process exited before persisting final report"),
                ):
                    synthesized_failed_reports.append(str(entry.get("report_id", "")).strip())
            stale_entries.append(entry)
        benchmark_dir = benchmark_root(repo_root=root)
        if benchmark_dir.is_dir():
            with contextlib.suppress(OSError):
                for progress_path in benchmark_dir.glob("progress-*.json"):
                    resolved_progress_path = progress_path.resolve()
                    if resolved_progress_path in processed_progress_paths:
                        continue
                    progress_payload = odylith_context_cache.read_json_object(progress_path)
                    if not isinstance(progress_payload, Mapping):
                        continue
                    status = str(progress_payload.get("status", "")).strip() or "running"
                    owning_pid = max(0, int(progress_payload.get("owning_pid", 0) or 0))
                    running = status == "running" and ((owning_pid > 0 and _process_exists(owning_pid)) or (owning_pid <= 0 and active_runtime_present))
                    if running:
                        continue
                    if not _history_report_exists_for_progress(repo_root=root, progress=progress_payload):
                        if _persist_orphaned_progress_failed_report(
                            repo_root=root,
                            progress_payload=progress_payload,
                            error=BenchmarkRunInterrupted("benchmark process exited before persisting final report"),
                        ):
                            synthesized_failed_reports.append(str(progress_payload.get("report_id", "")).strip())
                    if _history_report_exists_for_progress(repo_root=root, progress=progress_payload):
                        _benchmark_runtime_remove_file(repo_root=root, path=progress_path)
        if stale_entries:
            for entry in stale_entries:
                progress_path = Path(str(entry.get("progress_path", "")).strip())
                if progress_path.exists() and _history_report_exists_for_progress(repo_root=root, progress=entry):
                    _benchmark_runtime_remove_file(repo_root=root, path=progress_path)
            _write_active_runs(repo_root=root, runs=retained_entries)
    shared_progress_path = progress_report_path(repo_root=root)
    stale_shared_progress_cleared = False
    shared_payload = odylith_context_cache.read_json_object(shared_progress_path)
    shared_pid = max(0, int(shared_payload.get("owning_pid", 0) or 0)) if isinstance(shared_payload, Mapping) else 0
    shared_running = bool(isinstance(shared_payload, Mapping) and str(shared_payload.get("status", "")).strip() == "running")
    shared_stale = bool(
        clear_shared_progress
        or (shared_running and shared_pid > 0 and not _process_exists(shared_pid) and not active_runtime_present)
        or (shared_running and shared_pid <= 0 and not active_runtime_present)
    )
    if shared_stale and isinstance(shared_payload, Mapping) and not _history_report_exists_for_progress(repo_root=root, progress=shared_payload):
        _persist_orphaned_progress_failed_report(
            repo_root=root,
            progress_payload=shared_payload,
            error=BenchmarkRunInterrupted("benchmark process exited before persisting final report"),
        )
    if shared_stale and shared_progress_path.exists():
        with odylith_context_cache.advisory_lock(repo_root=root, key=str(shared_progress_path)):
            if shared_progress_path.exists():
                shared_progress_path.unlink()
                stale_shared_progress_cleared = True
    return {
        "removed_active_run_count": len(stale_entries),
        "removed_active_runs": stale_entries,
        "stale_shared_progress_cleared": stale_shared_progress_cleared,
        "active_run_count": len(retained_entries),
        "active_runtime_present": active_runtime_present,
        "synthesized_failed_report_count": len(synthesized_failed_reports),
        "synthesized_failed_reports": synthesized_failed_reports,
    }


def _cleanup_benchmark_temp_directories(*, repo_root: Path) -> dict[str, Any]:
    removed: list[str] = []
    failed: list[str] = []
    for directory in _benchmark_temp_directories(repo_root=repo_root):
        with contextlib.suppress(OSError):
            shutil.rmtree(directory)
            removed.append(str(directory))
            continue
        failed.append(str(directory))
    return {
        "removed_temp_directory_count": len(removed),
        "failed_temp_directory_count": len(failed),
        "removed_temp_directories": removed,
        "failed_temp_directories": failed,
    }


def _cleanup_stale_benchmark_state(
    *,
    repo_root: Path,
    clear_progress: bool,
    allow_destructive_runtime_cleanup: bool = True,
    ignore_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    progress_cleanup = _prune_stale_benchmark_progress(repo_root=root, clear_shared_progress=clear_progress)
    blocking_active_run_count = int(progress_cleanup.get("active_run_count", 0) or 0)
    if isinstance(ignore_progress, Mapping):
        blocking_active_run_count = int(
            _benchmark_runtime_hygiene_snapshot(repo_root=root, ignore_progress=ignore_progress).get(
                "active_run_count",
                blocking_active_run_count,
            )
            or 0
        )
    if blocking_active_run_count > 0:
        return {
            "stale_progress_cleared": bool(progress_cleanup.get("stale_shared_progress_cleared")),
            "progress_cleanup": {**progress_cleanup, "blocking_active_run_count": blocking_active_run_count},
            "process_cleanup": {
                "requested_pid_count": 0,
                "terminated_pid_count": 0,
                "forced_pid_count": 0,
                "remaining_pid_count": 0,
                "terminated_pids": [],
                "forced_pids": [],
                "remaining_pids": [],
                "skipped_due_to_active_runs": True,
            },
            "worktree_cleanup": {
                "removed_worktree_count": 0,
                "failed_worktree_count": 0,
                "removed_worktrees": [],
                "failed_worktrees": [],
                "skipped_due_to_active_runs": True,
            },
            "temp_directory_cleanup": {
                "removed_temp_directory_count": 0,
                "failed_temp_directory_count": 0,
                "removed_temp_directories": [],
                "failed_temp_directories": [],
                "skipped_due_to_active_runs": True,
            },
        }
    if bool(progress_cleanup.get("active_runtime_present")) and not allow_destructive_runtime_cleanup:
        return {
            "stale_progress_cleared": bool(progress_cleanup.get("stale_shared_progress_cleared")),
            "progress_cleanup": progress_cleanup,
            "process_cleanup": {
                "requested_pid_count": 0,
                "terminated_pid_count": 0,
                "forced_pid_count": 0,
                "remaining_pid_count": 0,
                "terminated_pids": [],
                "forced_pids": [],
                "remaining_pids": [],
                "skipped_due_to_unowned_sharded_runtime": True,
            },
            "worktree_cleanup": {
                "removed_worktree_count": 0,
                "failed_worktree_count": 0,
                "removed_worktrees": [],
                "failed_worktrees": [],
                "skipped_due_to_unowned_sharded_runtime": True,
            },
            "temp_directory_cleanup": {
                "removed_temp_directory_count": 0,
                "failed_temp_directory_count": 0,
                "removed_temp_directories": [],
                "failed_temp_directories": [],
                "skipped_due_to_unowned_sharded_runtime": True,
            },
        }
    process_cleanup = _terminate_processes(pids=_benchmark_owned_codex_process_ids())
    worktree_cleanup = _cleanup_benchmark_worktrees(repo_root=root)
    temp_directory_cleanup = _cleanup_benchmark_temp_directories(repo_root=root)
    return {
        "stale_progress_cleared": bool(progress_cleanup.get("stale_shared_progress_cleared")),
        "progress_cleanup": progress_cleanup,
        "process_cleanup": process_cleanup,
        "worktree_cleanup": worktree_cleanup,
        "temp_directory_cleanup": temp_directory_cleanup,
    }


def _benchmark_runtime_hygiene_snapshot(
    *,
    repo_root: Path,
    ignore_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    owned_process_ids = _benchmark_owned_codex_process_ids()
    temp_worktrees = [str(path) for path in _benchmark_temp_worktrees(repo_root=root)]
    temp_directories = [str(path) for path in _benchmark_temp_directories(repo_root=root)]
    active_runs = _load_active_runs(root)
    ignored_active_run_count = 0
    if isinstance(ignore_progress, Mapping):
        ignored_identity = _active_run_identity(ignore_progress)
        filtered_active_runs: list[dict[str, Any]] = []
        for entry in active_runs:
            entry_identity = (
                str(entry.get("report_id", "")).strip(),
                _normalize_benchmark_profile(str(entry.get("benchmark_profile", "")).strip()),
                max(1, int(entry.get("shard_index", 1) or 1)),
                max(1, int(entry.get("shard_count", 1) or 1)),
                max(0, int(entry.get("owning_pid", 0) or 0)),
            )
            if entry_identity == ignored_identity:
                ignored_active_run_count += 1
                continue
            filtered_active_runs.append(entry)
        active_runs = filtered_active_runs
    return {
        "owned_codex_process_count": len(owned_process_ids),
        "owned_codex_process_ids": owned_process_ids,
        "temp_worktree_count": len(temp_worktrees),
        "temp_worktrees": temp_worktrees,
        "temp_directory_count": len(temp_directories),
        "temp_directories": temp_directories,
        "active_run_count": len(active_runs),
        "ignored_active_run_count": ignored_active_run_count,
    }


def _enforce_diagnostic_runtime_hygiene(
    *,
    repo_root: Path,
    ignore_progress: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    hygiene = _benchmark_runtime_hygiene_snapshot(repo_root=repo_root, ignore_progress=ignore_progress)
    if (
        not hygiene["owned_codex_process_count"]
        and not hygiene["temp_worktree_count"]
        and not hygiene["temp_directory_count"]
        and not hygiene["active_run_count"]
    ):
        return hygiene
    cleanup = _cleanup_stale_benchmark_state(
        repo_root=repo_root,
        clear_progress=False,
        ignore_progress=ignore_progress,
    )
    raise RuntimeError(
        "diagnostic benchmark contamination detected: "
        f"owned_codex_process_count={hygiene['owned_codex_process_count']} "
        f"temp_worktree_count={hygiene['temp_worktree_count']} "
        f"temp_directory_count={hygiene['temp_directory_count']} "
        f"active_run_count={hygiene['active_run_count']} "
        f"cleanup={json.dumps(cleanup, sort_keys=True)}"
    )


def compact_report_summary(report: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(report, Mapping):
        return {}
    stored_summary = dict(report.get("published_summary", {})) if isinstance(report.get("published_summary"), Mapping) else {}
    acceptance = dict(report.get("acceptance", {})) if isinstance(report.get("acceptance"), Mapping) else {}
    comparison_contract = str(report.get("comparison_contract", "")).strip()
    comparison_contract_details = (
        dict(report.get("comparison_contract_details", {}))
        if isinstance(report.get("comparison_contract_details"), Mapping)
        else _comparison_contract_details(comparison_contract)
        if comparison_contract
        else {}
    )
    comparison = (
        dict(report.get("published_comparison", {}))
        if isinstance(report.get("published_comparison"), Mapping)
        else dict(report.get("primary_comparison", {}))
        if isinstance(report.get("primary_comparison"), Mapping)
        else {}
    )
    candidate_mode = _normalize_mode(str(comparison.get("candidate_mode", "")).strip() or _ODYLITH_ON_MODE)
    mode_summaries = (
        dict(report.get("published_mode_summaries", {}))
        if isinstance(report.get("published_mode_summaries"), Mapping)
        else dict(report.get("mode_summaries", {}))
        if isinstance(report.get("mode_summaries"), Mapping)
        else {}
    )
    candidate_summary = (
        dict(mode_summaries.get(candidate_mode, {}))
        if isinstance(mode_summaries.get(candidate_mode), Mapping)
        else dict(mode_summaries.get(_LEGACY_REPO_SCAN_BASELINE_MODE, {}))
        if candidate_mode == _REPO_SCAN_BASELINE_MODE and isinstance(mode_summaries.get(_LEGACY_REPO_SCAN_BASELINE_MODE), Mapping)
        else {}
    )
    runtime_posture = dict(report.get("runtime_posture", {})) if isinstance(report.get("runtime_posture"), Mapping) else {}
    adoption_proof = dict(report.get("adoption_proof", {})) if isinstance(report.get("adoption_proof"), Mapping) else {}
    robustness = dict(report.get("robustness_summary", {})) if isinstance(report.get("robustness_summary"), Mapping) else {}
    corpus_contract = dict(report.get("corpus_contract", {})) if isinstance(report.get("corpus_contract"), Mapping) else {}
    corpus_composition = (
        dict(report.get("corpus_composition", {}))
        if isinstance(report.get("corpus_composition"), Mapping)
        else {}
    )
    selection = dict(report.get("selection", {})) if isinstance(report.get("selection"), Mapping) else {}
    fairness_findings = [
        str(token).strip()
        for token in report.get("fairness_findings", [])
        if isinstance(report.get("fairness_findings"), list) and str(token).strip()
    ]
    observed_path_sources = [
        str(token).strip()
        for token in report.get("observed_path_sources", [])
        if isinstance(report.get("observed_path_sources"), list) and str(token).strip()
    ]
    preflight_evidence_modes = [
        str(token).strip()
        for token in report.get("preflight_evidence_modes", [])
        if isinstance(report.get("preflight_evidence_modes"), list) and str(token).strip()
    ]
    adoption_proof_sample_size = int(adoption_proof.get("sample_size", 0) or 0)
    adoption_proof_auto_grounded_rate = float(adoption_proof.get("auto_grounded_rate", 0.0) or 0.0)
    adoption_proof_requires_widening_rate = float(adoption_proof.get("requires_widening_rate", 0.0) or 0.0)
    adoption_proof_grounded_delegate_rate = float(adoption_proof.get("grounded_delegate_rate", 0.0) or 0.0)
    adoption_proof_workspace_daemon_reused_rate = float(
        adoption_proof.get("workspace_daemon_reused_rate", 0.0) or 0.0
    )
    adoption_proof_session_namespaced_rate = float(adoption_proof.get("session_namespaced_rate", 0.0) or 0.0)
    packet_source_summaries = (
        dict(report.get("published_packet_source_summaries", {}))
        if isinstance(report.get("published_packet_source_summaries"), Mapping)
        else {}
    )
    packet_source_deltas = (
        dict(report.get("published_packet_source_deltas", {}))
        if isinstance(report.get("published_packet_source_deltas"), Mapping)
        else {}
    )
    full_pair_timing_summary = (
        dict(report.get("full_pair_timing_summary", {}))
        if isinstance(report.get("full_pair_timing_summary"), Mapping)
        else {}
    )
    published_pair_timing_summary = (
        dict(report.get("published_pair_timing_summary", {}))
        if isinstance(report.get("published_pair_timing_summary"), Mapping)
        else {}
    )
    bootstrap_summary = (
        dict(_lookup_mode_mapping(dict(packet_source_summaries.get("bootstrap_session", {})), candidate_mode) or {})
        if isinstance(packet_source_summaries.get("bootstrap_session"), Mapping)
        else {}
    )
    bootstrap_delta = (
        dict(packet_source_deltas.get("bootstrap_session", {}))
        if isinstance(packet_source_deltas.get("bootstrap_session"), Mapping)
        else {}
    )
    summary = {
        "report_id": str(report.get("report_id", "")).strip(),
        "benchmark_profile": _normalize_benchmark_profile(str(report.get("benchmark_profile", "")).strip()),
        "benchmark_profile_label": _benchmark_profile_label(str(report.get("benchmark_profile", "")).strip()),
        "git_branch": str(report.get("git_branch", "")).strip(),
        "git_commit": str(report.get("git_commit", "")).strip(),
        "git_dirty": bool(report.get("git_dirty")),
        "source_posture": str(report.get("source_posture", "")).strip(),
        "current_tree_identity_match": benchmark_report_matches_current_tree(
            repo_root=Path(str(report.get("repo_root", "")).strip() or "."),
            report=report,
        )
        if str(report.get("repo_root", "")).strip()
        else False,
        "selection_strategy": str(report.get("selection_strategy", "")).strip()
        or str(selection.get("selection_strategy", "")).strip()
        or "manual_selection",
        "generated_utc": str(report.get("generated_utc", "")).strip(),
        "status": str(acceptance.get("status", "")).strip() or "unavailable",
        "hard_quality_gate_cleared": bool(acceptance.get("hard_quality_gate_cleared")),
        "secondary_guardrails_cleared": bool(acceptance.get("secondary_guardrails_cleared")),
        "advisory_checks_cleared": bool(acceptance.get("advisory_checks_cleared")),
        "scenario_count": int(report.get("scenario_count", 0) or 0),
        "evaluated_mode_count": len(report.get("mode_summaries", {})) if isinstance(report.get("mode_summaries"), Mapping) else 0,
        "primary_cache_profile": str(report.get("primary_cache_profile", "")).strip() or "warm",
        "cache_profile_count": len(report.get("cache_profiles", [])) if isinstance(report.get("cache_profiles"), list) else 0,
        "published_view_strategy": str(report.get("published_view_strategy", "")).strip() or "primary_profile",
        "published_cache_profiles": [
            str(token).strip()
            for token in report.get("published_cache_profiles", [])
            if str(token).strip()
        ]
        if isinstance(report.get("published_cache_profiles"), list)
        else [],
        "comparison_contract": comparison_contract,
        "comparison_primary_claim": str(comparison_contract_details.get("primary_claim", "")).strip(),
        "candidate_mode": _public_mode_name(str(comparison.get("candidate_mode", "")).strip()),
        "baseline_mode": _public_mode_name(str(comparison.get("baseline_mode", "")).strip()),
        "latency_delta_ms": float(comparison.get("median_latency_delta_ms", 0.0) or 0.0),
        "avg_latency_delta_ms": float(comparison.get("avg_latency_delta_ms", 0.0) or 0.0),
        "p95_latency_delta_ms": float(comparison.get("p95_latency_delta_ms", 0.0) or 0.0),
        "token_delta": float(
            comparison.get("median_prompt_token_delta", comparison.get("median_token_delta", 0.0)) or 0.0
        ),
        "prompt_token_delta": float(
            comparison.get("median_prompt_token_delta", comparison.get("median_token_delta", 0.0)) or 0.0
        ),
        "total_payload_token_delta": float(comparison.get("median_total_payload_token_delta", 0.0) or 0.0),
        "runtime_contract_token_delta": float(comparison.get("median_runtime_contract_token_delta", 0.0) or 0.0),
        "operator_diag_token_delta": float(comparison.get("median_operator_diag_token_delta", 0.0) or 0.0),
        "observed_path_count_delta": float(comparison.get("median_observed_path_count_delta", 0.0) or 0.0),
        "selected_doc_count_delta": float(comparison.get("median_selected_doc_count_delta", 0.0) or 0.0),
        "selected_command_count_delta": float(comparison.get("median_selected_command_count_delta", 0.0) or 0.0),
        "required_path_recall_delta": float(comparison.get("required_path_recall_delta", 0.0) or 0.0),
        "required_path_precision_delta": float(comparison.get("required_path_precision_delta", 0.0) or 0.0),
        "hallucinated_surface_rate_delta": float(comparison.get("hallucinated_surface_rate_delta", 0.0) or 0.0),
        "validation_success_delta": float(comparison.get("validation_success_delta", 0.0) or 0.0),
        "route_ready_validation_success_delta": float(
            comparison.get("route_ready_validation_success_delta", 0.0) or 0.0
        ),
        "route_ready_expectation_success_delta": float(
            comparison.get("route_ready_expectation_success_delta", 0.0) or 0.0
        ),
        "write_surface_precision_delta": float(comparison.get("write_surface_precision_delta", 0.0) or 0.0),
        "unnecessary_widening_rate_delta": float(comparison.get("unnecessary_widening_rate_delta", 0.0) or 0.0),
        "critical_required_path_recall_delta": float(comparison.get("critical_required_path_recall_delta", 0.0) or 0.0),
        "critical_validation_success_delta": float(comparison.get("critical_validation_success_delta", 0.0) or 0.0),
        "expectation_success_delta": float(comparison.get("expectation_success_delta", 0.0) or 0.0),
        "required_path_precision_rate": float(candidate_summary.get("required_path_precision_rate", 0.0) or 0.0),
        "hallucinated_surface_rate": float(candidate_summary.get("hallucinated_surface_rate", 0.0) or 0.0),
        "odylith_median_observed_path_count": float(candidate_summary.get("median_observed_path_count", 0.0) or 0.0),
        "odylith_median_selected_doc_count": float(candidate_summary.get("median_selected_doc_count", 0.0) or 0.0),
        "odylith_median_selected_command_count": float(candidate_summary.get("median_selected_command_count", 0.0) or 0.0),
        "odylith_route_ready_validation_success_rate": float(
            candidate_summary.get("route_ready_validation_success_rate", 0.0) or 0.0
        ),
        "odylith_route_ready_expectation_success_rate": float(
            candidate_summary.get("route_ready_expectation_success_rate", 0.0) or 0.0
        ),
        "write_surface_precision_rate": float(candidate_summary.get("write_surface_precision_rate", 0.0) or 0.0),
        "unnecessary_widening_rate": float(candidate_summary.get("unnecessary_widening_rate", 0.0) or 0.0),
        "odylith_packet_present_rate": float(candidate_summary.get("odylith_packet_present_rate", 0.0) or 0.0),
        "odylith_auto_grounded_rate": (
            adoption_proof_auto_grounded_rate
            if adoption_proof_sample_size > 0
            else float(candidate_summary.get("odylith_auto_grounded_rate", 0.0) or 0.0)
        ),
        "odylith_requires_widening_rate": (
            adoption_proof_requires_widening_rate
            if adoption_proof_sample_size > 0
            else float(candidate_summary.get("odylith_requires_widening_rate", 0.0) or 0.0)
        ),
        "odylith_grounded_delegate_rate": (
            adoption_proof_grounded_delegate_rate
            if adoption_proof_sample_size > 0
            else float(candidate_summary.get("odylith_grounded_delegate_rate", 0.0) or 0.0)
        ),
        "odylith_workspace_daemon_reuse_rate": (
            adoption_proof_workspace_daemon_reused_rate
            if adoption_proof_sample_size > 0
            else float(candidate_summary.get("odylith_workspace_daemon_reuse_rate", 0.0) or 0.0)
        ),
        "odylith_session_namespaced_rate": (
            adoption_proof_session_namespaced_rate
            if adoption_proof_sample_size > 0
            else float(candidate_summary.get("odylith_session_namespaced_rate", 0.0) or 0.0)
        ),
        "runtime_memory_standardization_state": str(runtime_posture.get("memory_standardization_state", "")).strip(),
        "runtime_memory_backed_retrieval_ready": bool(runtime_posture.get("memory_backed_retrieval_ready")),
        "runtime_memory_storage": str(
            dict(runtime_posture.get("memory_backend_actual", {})).get("storage", "")
        ).strip()
        if isinstance(runtime_posture.get("memory_backend_actual"), Mapping)
        else "",
        "runtime_memory_sparse_recall": str(
            dict(runtime_posture.get("memory_backend_actual", {})).get("sparse_recall", "")
        ).strip()
        if isinstance(runtime_posture.get("memory_backend_actual"), Mapping)
        else "",
        "runtime_memory_projection_scope": str(runtime_posture.get("memory_projection_scope", "")).strip(),
        "runtime_memory_indexed_entity_count": int(runtime_posture.get("memory_indexed_entity_count", 0) or 0),
        "runtime_memory_evidence_document_count": int(
            runtime_posture.get("memory_evidence_document_count", 0) or 0
        ),
        "runtime_repo_scan_degraded_fallback_rate": float(
            runtime_posture.get("repo_scan_degraded_fallback_rate", 0.0) or 0.0
        ),
        "runtime_hard_grounding_failure_rate": float(
            runtime_posture.get("hard_grounding_failure_rate", 0.0) or 0.0
        ),
        "runtime_soft_widening_rate": float(
            runtime_posture.get("soft_widening_rate", 0.0) or 0.0
        ),
        "runtime_visible_fallback_receipt_rate": float(
            runtime_posture.get("visible_fallback_receipt_rate", 0.0) or 0.0
        ),
        "runtime_governance_runtime_first_usage_rate": float(
            runtime_posture.get("governance_runtime_first_usage_rate", 0.0) or 0.0
        ),
        "runtime_remote_retrieval_status": str(runtime_posture.get("remote_retrieval_status", "")).strip() or "disabled",
        "runtime_remote_retrieval_mode": str(runtime_posture.get("remote_retrieval_mode", "")).strip() or "disabled",
        "runtime_remote_retrieval_enabled": bool(runtime_posture.get("remote_retrieval_enabled")),
        "runtime_route_ready_rate": float(runtime_posture.get("route_ready_rate", 0.0) or 0.0),
        "runtime_native_spawn_ready_rate": float(runtime_posture.get("native_spawn_ready_rate", 0.0) or 0.0),
        "runtime_architecture_covered_case_count": int(
            runtime_posture.get("architecture_covered_case_count", 0) or 0
        ),
        "runtime_architecture_satisfied_case_count": int(
            runtime_posture.get("architecture_satisfied_case_count", 0) or 0
        ),
        "bootstrap_session_scenario_count": int(bootstrap_summary.get("scenario_count", 0) or 0),
        "bootstrap_session_prompt_token_delta": float(
            bootstrap_delta.get("median_prompt_token_delta", bootstrap_delta.get("median_token_delta", 0.0)) or 0.0
        ),
        "bootstrap_session_total_payload_token_delta": float(
            bootstrap_delta.get("median_total_payload_token_delta", 0.0) or 0.0
        ),
        "adoption_proof_sample_size": adoption_proof_sample_size,
        "adoption_proof_auto_grounded_rate": adoption_proof_auto_grounded_rate,
        "adoption_proof_requires_widening_rate": adoption_proof_requires_widening_rate,
        "adoption_proof_grounded_delegate_rate": adoption_proof_grounded_delegate_rate,
        "adoption_proof_workspace_daemon_reused_rate": adoption_proof_workspace_daemon_reused_rate,
        "adoption_proof_session_namespaced_rate": adoption_proof_session_namespaced_rate,
        "robustness_selected_cache_profile_count": int(
            robustness.get("selected_cache_profile_count", 0) or 0
        ),
        "robustness_selected_cache_profile_pass_rate": float(
            robustness.get("selected_cache_profile_pass_rate", 0.0) or 0.0
        ),
        "robustness_warm_cold_consistency_cleared": bool(
            robustness.get("warm_cold_consistency_cleared")
        ),
        "robustness_rerun_stability_state": str(robustness.get("rerun_stability_state", "")).strip() or "not_measured",
        "robustness_rerun_probe_family_count": int(robustness.get("rerun_probe_family_count", 0) or 0),
        "robustness_rerun_probe_scenario_count": int(robustness.get("rerun_probe_scenario_count", 0) or 0),
        "robustness_rerun_probe_mode_count": int(robustness.get("rerun_probe_mode_count", 0) or 0),
        "robustness_rerun_probe_sample_count": int(robustness.get("rerun_probe_sample_count", 0) or 0),
        "robustness_rerun_probe_latency_pass_rate": float(
            robustness.get("rerun_probe_latency_pass_rate", 0.0) or 0.0
        ),
        "robustness_rerun_probe_quality_consistency_pass_rate": float(
            robustness.get("rerun_probe_quality_consistency_pass_rate", 0.0) or 0.0
        ),
        "robustness_rerun_probe_worst_latency_spread_ms": float(
            robustness.get("rerun_probe_worst_latency_spread_ms", 0.0) or 0.0
        ),
        "robustness_candidate_latency_spread_ms": float(
            robustness.get("candidate_latency_spread_ms", 0.0) or 0.0
        ),
        "robustness_candidate_prompt_token_spread": float(
            robustness.get("candidate_prompt_token_spread", 0.0) or 0.0
        ),
        "robustness_candidate_required_path_precision_spread": float(
            robustness.get("candidate_required_path_precision_spread", 0.0) or 0.0
        ),
        "robustness_candidate_write_surface_precision_spread": float(
            robustness.get("candidate_write_surface_precision_spread", 0.0) or 0.0
        ),
        "corpus_contract_status": str(corpus_contract.get("status", "")).strip(),
        "corpus_packet_scenario_key": str(corpus_contract.get("packet_scenario_key", "")).strip(),
        "corpus_architecture_scenario_key": str(corpus_contract.get("architecture_scenario_key", "")).strip(),
        "fairness_contract_passed": bool(report.get("fairness_contract_passed")),
        "fairness_finding_count": len(fairness_findings),
        "fairness_findings": fairness_findings[:4],
        "observed_path_sources": observed_path_sources,
        "preflight_evidence_mode": str(report.get("preflight_evidence_mode", "")).strip(),
        "preflight_evidence_modes": preflight_evidence_modes,
        "corpus_seriousness_floor_passed": bool(corpus_composition.get("seriousness_floor_passed")),
        "corpus_full_coverage_rate": float(corpus_composition.get("full_corpus_coverage_rate", 0.0) or 0.0),
        "corpus_full_selected": bool(corpus_composition.get("full_corpus_selected")),
        "corpus_implementation_scenario_count": int(corpus_composition.get("implementation_scenario_count", 0) or 0),
        "corpus_write_plus_validator_scenario_count": int(
            corpus_composition.get("write_plus_validator_scenario_count", 0) or 0
        ),
        "corpus_correctness_critical_scenario_count": int(
            corpus_composition.get("correctness_critical_scenario_count", 0) or 0
        ),
        "corpus_mechanism_heavy_implementation_ratio": float(
            corpus_composition.get("mechanism_heavy_implementation_ratio", 0.0) or 0.0
        ),
        "weak_families": [
            str(token).strip()
            for token in acceptance.get("weak_families", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("weak_families"), list)
        else [],
        "hard_gate_failures": [
            str(token).strip()
            for token in acceptance.get("hard_gate_failures", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("hard_gate_failures"), list)
        else [],
        "hard_gate_failure_labels": [
            str(token).strip()
            for token in acceptance.get("hard_gate_failure_labels", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("hard_gate_failure_labels"), list)
        else [],
        "secondary_guardrail_failures": [
            str(token).strip()
            for token in acceptance.get("secondary_guardrail_failures", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("secondary_guardrail_failures"), list)
        else [],
        "secondary_guardrail_failure_labels": [
            str(token).strip()
            for token in acceptance.get("secondary_guardrail_failure_labels", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("secondary_guardrail_failure_labels"), list)
        else [],
        "advisory_failures": [
            str(token).strip()
            for token in acceptance.get("advisory_failures", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("advisory_failures"), list)
        else [],
        "advisory_failure_labels": [
            str(token).strip()
            for token in acceptance.get("advisory_failure_labels", [])
            if str(token).strip()
        ][:6]
        if isinstance(acceptance.get("advisory_failure_labels"), list)
        else [],
        "selection_family_filters": [
            str(token).strip()
            for token in selection.get("family_filters", [])
            if str(token).strip()
        ]
        if isinstance(selection.get("family_filters", []), list)
        else [],
        "selection_shard_count": int(selection.get("shard_count", 1) or 1),
        "selection_shard_index": int(selection.get("shard_index", 1) or 1),
        "full_pair_count": int(full_pair_timing_summary.get("pair_count", 0) or 0),
        "full_pair_median_wall_clock_ms": float(full_pair_timing_summary.get("median_pair_wall_clock_ms", 0.0) or 0.0),
        "full_pair_avg_wall_clock_ms": float(full_pair_timing_summary.get("avg_pair_wall_clock_ms", 0.0) or 0.0),
        "full_pair_p95_wall_clock_ms": float(full_pair_timing_summary.get("p95_pair_wall_clock_ms", 0.0) or 0.0),
        "full_pair_total_wall_clock_ms": float(full_pair_timing_summary.get("total_pair_wall_clock_ms", 0.0) or 0.0),
        "published_pair_count": int(published_pair_timing_summary.get("pair_count", 0) or 0),
        "published_pair_median_wall_clock_ms": float(
            published_pair_timing_summary.get("median_pair_wall_clock_ms", 0.0) or 0.0
        ),
        "published_pair_avg_wall_clock_ms": float(
            published_pair_timing_summary.get("avg_pair_wall_clock_ms", 0.0) or 0.0
        ),
        "published_pair_p95_wall_clock_ms": float(
            published_pair_timing_summary.get("p95_pair_wall_clock_ms", 0.0) or 0.0
        ),
        "published_pair_total_wall_clock_ms": float(
            published_pair_timing_summary.get("total_pair_wall_clock_ms", 0.0) or 0.0
        ),
        "notes": [
            str(token).strip()
            for token in acceptance.get("notes", [])
            if str(token).strip()
        ][:4]
        if isinstance(acceptance.get("notes"), list)
        else [],
    }
    if stored_summary:
        summary.update(
            {
                key: value
                for key, value in stored_summary.items()
                if str(key).strip()
            }
        )
    return summary


def compact_progress_summary(progress: Mapping[str, Any] | None) -> dict[str, Any]:
    if not isinstance(progress, Mapping):
        return {}
    return {
        "report_id": str(progress.get("report_id", "")).strip(),
        "benchmark_profile": _normalize_benchmark_profile(str(progress.get("benchmark_profile", "")).strip()),
        "status": str(progress.get("status", "")).strip() or "unknown",
        "started_utc": str(progress.get("started_utc", "")).strip(),
        "updated_utc": str(progress.get("updated_utc", "")).strip(),
        "scenario_count": int(progress.get("scenario_count", 0) or 0),
        "total_results": int(progress.get("total_results", 0) or 0),
        "primary_cache_profile": str(progress.get("primary_cache_profile", "")).strip() or "warm",
        "current_cache_profile": str(progress.get("current_cache_profile", "")).strip(),
        "completed_scenarios": int(progress.get("completed_scenarios", 0) or 0),
        "completed_results": int(progress.get("completed_results", 0) or 0),
        "current_scenario_id": str(progress.get("current_scenario_id", "")).strip(),
        "current_mode": str(progress.get("current_mode", "")).strip(),
        "selection_strategy": str(progress.get("selection_strategy", "")).strip() or "manual_selection",
        "shard_count": int(progress.get("shard_count", 1) or 1),
        "shard_index": int(progress.get("shard_index", 1) or 1),
        "latest_eligible": bool(progress.get("latest_eligible")),
    }


def _product_version_from_pyproject(*, repo_root: Path) -> str:
    path = Path(repo_root).resolve() / "pyproject.toml"
    if not path.is_file():
        return ""
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return ""
    project = payload.get("project")
    if not isinstance(project, Mapping):
        return ""
    return str(project.get("version") or "").strip()


def _dedupe_strings(values: Sequence[Any]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = str(raw or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _deep_merge_mapping(base: Mapping[str, Any], overlay: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for raw_key, overlay_value in overlay.items():
        key = str(raw_key).strip()
        if not key:
            continue
        base_value = merged.get(key)
        if isinstance(base_value, Mapping) and isinstance(overlay_value, Mapping):
            merged[key] = _deep_merge_mapping(base_value, overlay_value)
            continue
        merged[key] = overlay_value
    return merged


_PACKET_FIXTURE_ALLOWED_KEYS = frozenset(
    {
        "agent_stream_state",
        "context_packet",
        "docs",
        "execution_stream_state",
        "external_dependency",
        "github_actions",
        "host_candidates",
        "host_runtime",
        "presentation_policy",
        "proof_state",
        "relevant_docs",
        "routing_handoff",
        "session",
        "target_resolution",
        "turn_context",
    }
)


def _scenario_packet_fixture(scenario: Mapping[str, Any]) -> dict[str, Any]:
    fixture = _mapping(scenario.get("packet_fixture"))
    if not fixture:
        return {}
    return {
        key: value
        for key, value in fixture.items()
        if str(key).strip() in _PACKET_FIXTURE_ALLOWED_KEYS and value not in ("", [], {}, None)
    }


def _apply_packet_fixture(
    *,
    payload: Mapping[str, Any],
    scenario: Mapping[str, Any],
    packet_source: str,
) -> dict[str, Any]:
    fixture = _scenario_packet_fixture(scenario)
    merged = dict(payload)
    if packet_source in {"impact", "governance_slice"} and not str(merged.get("packet_kind", "")).strip():
        merged["packet_kind"] = packet_source
    if fixture:
        merged = _deep_merge_mapping(merged, fixture)
    if not fixture and "packet_kind" not in merged:
        return odylith_benchmark_execution_engine.enrich_packet_payload_for_execution_engine_family(
            payload=merged,
            scenario=scenario,
        )
    merged.pop("execution_engine", None)
    context_packet = _mapping(merged.get("context_packet"))
    if context_packet:
        context_packet.pop("execution_engine", None)
        merged["context_packet"] = context_packet
    return odylith_benchmark_execution_engine.enrich_packet_payload_for_execution_engine_family(
        payload=merged,
        scenario=scenario,
    )


def _scenario_priority_rank(priority: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(str(priority or "").strip().lower(), 9)


def _scenario_selection_sort_key(scenario: Mapping[str, Any]) -> tuple[int, str, str]:
    return (
        _scenario_priority_rank(str(scenario.get("priority", "")).strip()),
        str(scenario.get("family", "")).strip(),
        str(scenario.get("scenario_id", "")).strip(),
    )


def _normalize_family_filter(value: str) -> str:
    token = str(value or "").strip()
    if not token:
        return ""
    alias = token.lower().replace(" ", "_")
    return _FAMILY_ALIASES.get(token, _FAMILY_ALIASES.get(alias, _FAMILY_ALIASES.get(alias.replace("_", "-"), token)))


def _normalize_family_filters(families: Sequence[str]) -> list[str]:
    return _dedupe_strings([_normalize_family_filter(str(token)) for token in families if str(token).strip()])


def _representative_family_smoke_scenarios(*, scenarios: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    representatives: dict[str, dict[str, Any]] = {}
    for raw in scenarios:
        scenario = dict(raw)
        family = str(scenario.get("family", "")).strip()
        if not family:
            continue
        existing = representatives.get(family)
        if existing is None or _scenario_selection_sort_key(scenario) < _scenario_selection_sort_key(existing):
            representatives[family] = scenario
    selected = sorted(representatives.values(), key=_scenario_selection_sort_key)
    return [dict(row) for row in selected[:_QUICK_PROFILE_MAX_SCENARIOS]]


def _quick_profile_smoke_scenarios(*, scenarios: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Keep the default live smoke bounded while still covering current-head risk seams."""
    by_id = {
        str(row.get("scenario_id", "")).strip(): dict(row)
        for row in scenarios
        if str(row.get("scenario_id", "")).strip()
    }
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for scenario_id in _QUICK_PROFILE_SENTINEL_CASE_IDS:
        row = by_id.get(scenario_id)
        if row is None:
            continue
        selected.append(dict(row))
        seen.add(scenario_id)
    if len(selected) < _QUICK_PROFILE_MAX_SCENARIOS:
        for row in _representative_family_smoke_scenarios(scenarios=scenarios):
            scenario_id = str(row.get("scenario_id", "")).strip()
            if not scenario_id or scenario_id in seen:
                continue
            selected.append(dict(row))
            seen.add(scenario_id)
            if len(selected) >= _QUICK_PROFILE_MAX_SCENARIOS:
                break
    return selected[:_QUICK_PROFILE_MAX_SCENARIOS]


def _apply_scenario_shard(
    *,
    scenarios: Sequence[Mapping[str, Any]],
    shard_count: int,
    shard_index: int,
) -> list[dict[str, Any]]:
    if shard_count <= 1:
        return [dict(row) for row in scenarios]
    if shard_count < 1:
        raise ValueError("`shard_count` must be at least 1.")
    if shard_index < 1 or shard_index > shard_count:
        raise ValueError("`shard_index` must be between 1 and `shard_count` inclusive.")
    selected: list[dict[str, Any]] = []
    for index, raw in enumerate(scenarios, start=1):
        if ((index - 1) % shard_count) + 1 != shard_index:
            continue
        selected.append(dict(raw))
    return selected


def _paths_from_match(match_spec: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for key in ("paths_all", "paths_any", "paths"):
        value = match_spec.get(key, [])
        if not isinstance(value, list):
            continue
        rows.extend(str(token).strip() for token in value if str(token).strip())
    return _dedupe_strings(rows)


def _default_prompt(*, label: str, summary: str, changed_paths: Sequence[str], architecture: bool) -> str:
    if summary:
        return summary
    if changed_paths:
        prefix = "Audit the architecture impact for" if architecture else "Implement and validate the slice touching"
        return f"{prefix} {', '.join(changed_paths[:3])}."
    return label or ("Architecture benchmark slice" if architecture else "Odylith benchmark slice")


def _default_acceptance_criteria(
    *,
    changed_paths: Sequence[str],
    architecture: bool,
) -> list[str]:
    criteria: list[str] = []
    if architecture:
        criteria.append("Keep the slice structurally grounded and fail closed on weak coverage.")
    else:
        criteria.append("Stay within packet budget while preserving grounded evidence.")
    if changed_paths:
        criteria.append(f"Keep the slice bounded to {', '.join(changed_paths[:3])}.")
    return criteria


def _scenario_from_case(*, case: Mapping[str, Any], architecture: bool) -> dict[str, Any]:
    match_spec = dict(case.get("match", {})) if isinstance(case.get("match"), Mapping) else {}
    benchmark_spec = dict(case.get("benchmark", {})) if isinstance(case.get("benchmark"), Mapping) else {}
    changed_paths = _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in benchmark_spec.get("paths", [])
                if isinstance(benchmark_spec.get("paths"), list) and str(token).strip()
            ),
            *_paths_from_match(match_spec),
        ]
    )
    workstream = str(benchmark_spec.get("workstream", "")).strip().upper() or str(match_spec.get("workstream", "")).strip().upper()
    component = str(benchmark_spec.get("component", "")).strip().lower() or str(match_spec.get("component", "")).strip().lower()
    family = str(case.get("family", "")).strip() or ("architecture" if architecture else "analysis")
    needs_write = bool(benchmark_spec.get("needs_write")) if "needs_write" in benchmark_spec else bool(changed_paths and family in _WRITE_FAMILIES and not architecture)
    default_intent = "analysis benchmark" if architecture or family in _ANALYSIS_FAMILIES or not needs_write else "implementation benchmark"
    validation_commands = (
        _dedupe_strings(benchmark_spec.get("validation_commands", []))
        if isinstance(benchmark_spec.get("validation_commands"), list)
        else []
    )
    explicit_expected_write_paths = (
        _dedupe_strings(benchmark_spec.get("expected_write_paths", []))
        if isinstance(benchmark_spec.get("expected_write_paths"), list)
        else []
    )
    supporting_paths = (
        _dedupe_strings(benchmark_spec.get("supporting_paths", []))
        if isinstance(benchmark_spec.get("supporting_paths"), list)
        else []
    )
    focused_local_checks = (
        _dedupe_strings(benchmark_spec.get("focused_local_checks", []))
        if isinstance(benchmark_spec.get("focused_local_checks"), list)
        else []
    )
    correctness_critical = (
        bool(benchmark_spec.get("correctness_critical"))
        if "correctness_critical" in benchmark_spec
        else family in _CORRECTNESS_CRITICAL_FAMILIES
    )
    if correctness_critical and not validation_commands:
        correctness_critical = False
    required_paths = _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in benchmark_spec.get("required_paths", [])
                if isinstance(benchmark_spec.get("required_paths"), list) and str(token).strip()
            ),
            *changed_paths,
        ]
    )
    expected_write_paths = explicit_expected_write_paths if needs_write else []
    if needs_write and not expected_write_paths:
        expected_write_paths = list(changed_paths)
    critical_paths = _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in benchmark_spec.get("critical_paths", [])
                if isinstance(benchmark_spec.get("critical_paths"), list) and str(token).strip()
            ),
            *required_paths,
        ]
    )
    live_timeout_seconds = 0.0
    if "live_timeout_seconds" in benchmark_spec:
        with contextlib.suppress(TypeError, ValueError):
            live_timeout_seconds = max(0.0, float(benchmark_spec.get("live_timeout_seconds") or 0.0))
    allow_noop_completion = bool(benchmark_spec.get("allow_noop_completion"))
    packet_fixture = _mapping(benchmark_spec.get("packet_fixture"))
    return {
        "scenario_id": str(case.get("case_id", "")).strip() or hashlib.sha256(
            json.dumps(case, sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:12],
        "kind": "architecture" if architecture else "packet",
        "label": str(case.get("label", "")).strip() or str(case.get("case_id", "")).strip(),
        "summary": str(case.get("summary", "")).strip(),
        "family": family,
        "priority": str(case.get("priority", "medium")).strip().lower() or "medium",
        "changed_paths": changed_paths,
        "workstream": workstream,
        "component": component,
        "domains_any": _dedupe_strings(match_spec.get("domains_any", [])) if isinstance(match_spec.get("domains_any"), list) else [],
        "prompt": str(benchmark_spec.get("prompt", "")).strip()
        or _default_prompt(
            label=str(case.get("label", "")).strip(),
            summary=str(case.get("summary", "")).strip(),
            changed_paths=changed_paths,
            architecture=architecture,
        ),
        "intent": str(benchmark_spec.get("intent", "")).strip() or ("architecture review" if architecture else default_intent),
        "acceptance_criteria": _dedupe_strings(benchmark_spec.get("acceptance_criteria", []))
        if isinstance(benchmark_spec.get("acceptance_criteria"), list)
        else _default_acceptance_criteria(changed_paths=changed_paths, architecture=architecture),
        "validation_commands": validation_commands,
        "focused_local_checks": focused_local_checks,
        "required_paths": required_paths,
        "supporting_paths": supporting_paths,
        "expected_write_paths": expected_write_paths,
        "critical_paths": critical_paths,
        "needs_write": needs_write,
        "allow_noop_completion": allow_noop_completion,
        "correctness_critical": correctness_critical,
        "live_timeout_seconds": live_timeout_seconds,
        "packet_source": str(benchmark_spec.get("packet_source", "")).strip(),
        "packet_fixture": packet_fixture,
        "expect": dict(case.get("expect", {})) if isinstance(case.get("expect"), Mapping) else {},
        "match": match_spec,
    }


def load_benchmark_scenarios(
    *,
    repo_root: Path,
    case_ids: Sequence[str] = (),
    limit: int = 0,
) -> list[dict[str, Any]]:
    corpus = odylith_context_cache.read_json_object(store.optimization_evaluation_corpus_path(repo_root=repo_root))
    selected = {str(token).strip() for token in case_ids if str(token).strip()}
    scenarios: list[dict[str, Any]] = []
    for raw in odylith_benchmark_contract.packet_benchmark_scenarios(corpus):
        if not isinstance(raw, Mapping):
            continue
        scenario = _scenario_from_case(case=raw, architecture=False)
        if selected and scenario["scenario_id"] not in selected:
            continue
        scenarios.append(scenario)
    for raw in odylith_benchmark_contract.architecture_benchmark_scenarios(corpus):
        if not isinstance(raw, Mapping):
            continue
        scenario = _scenario_from_case(case=raw, architecture=True)
        if selected and scenario["scenario_id"] not in selected:
            continue
        scenarios.append(scenario)
    scenarios.sort(key=lambda row: ({"critical": 0, "high": 1, "medium": 2, "low": 3}.get(row["priority"], 9), row["scenario_id"]))
    if limit > 0:
        scenarios = scenarios[: max(1, int(limit))]
    return scenarios


def _resolve_benchmark_scenario_selection(
    *,
    all_scenarios: Sequence[Mapping[str, Any]],
    benchmark_profile: str,
    case_ids: Sequence[str] = (),
    families: Sequence[str] = (),
    shard_count: int = 1,
    shard_index: int = 1,
    limit: int = 0,
) -> dict[str, Any]:
    normalized_profile = _normalize_benchmark_profile(benchmark_profile)
    normalized_shard_count = max(1, int(shard_count or 1))
    normalized_shard_index = max(1, int(shard_index or 1))
    selected_case_ids = {str(token).strip() for token in case_ids if str(token).strip()}
    selected_families = set(_normalize_family_filters(families))
    all_case_ids = {
        str(row.get("scenario_id", "")).strip()
        for row in all_scenarios
        if str(row.get("scenario_id", "")).strip()
    }
    base_scenarios = [
        dict(row)
        for row in all_scenarios
        if (not selected_case_ids or str(row.get("scenario_id", "")).strip() in selected_case_ids)
        and (not selected_families or str(row.get("family", "")).strip() in selected_families)
    ]
    profile_default_narrowing = ""
    if (
        normalized_profile == BENCHMARK_PROFILE_QUICK
        and not selected_case_ids
        and not selected_families
        and int(limit) <= 0
        and normalized_shard_count <= 1
    ):
        scenarios = _quick_profile_smoke_scenarios(scenarios=base_scenarios)
        profile_default_narrowing = "quick_sentinel_smoke"
    else:
        scenarios = [dict(row) for row in base_scenarios]
    scenarios = _apply_scenario_shard(
        scenarios=scenarios,
        shard_count=normalized_shard_count,
        shard_index=normalized_shard_index,
    )
    if limit > 0:
        scenarios = scenarios[: max(1, int(limit))]
    explicit_full_selection = bool(selected_case_ids) and selected_case_ids == all_case_ids and not selected_families
    full_corpus_selected = bool(
        not profile_default_narrowing
        and int(limit) <= 0
        and normalized_shard_count <= 1
        and ((not selected_case_ids and not selected_families and len(scenarios) == len(all_scenarios)) or explicit_full_selection)
    )
    selection_strategy = "full_corpus"
    if profile_default_narrowing:
        selection_strategy = profile_default_narrowing
    elif selected_case_ids or selected_families or normalized_shard_count > 1 or int(limit) > 0:
        selection_strategy = "manual_selection"
    return {
        "all_case_ids": all_case_ids,
        "selected_case_ids": selected_case_ids,
        "selected_families": selected_families,
        "profile_default_narrowing": profile_default_narrowing,
        "full_corpus_selected": full_corpus_selected,
        "selection_strategy": selection_strategy,
        "scenarios": scenarios,
        "all_scenarios": [dict(row) for row in all_scenarios],
    }


@contextlib.contextmanager
def _odylith_enabled_override(enabled: bool) -> Iterator[None]:
    keys = ("ODYLITH_ENABLED", "ODYLITH_ENABLED")
    prior = {key: os.environ.get(key) for key in keys}
    token = "1" if enabled else "0"
    for key in keys:
        os.environ[key] = token
    try:
        yield
    finally:
        for key, value in prior.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _existing_repo_paths(*, repo_root: Path, paths: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in paths:
        token = str(raw or "").strip()
        if not token:
            continue
        if (Path(repo_root).resolve() / token).exists():
            rows.append(token)
    return _dedupe_strings(rows)


def _estimate_json_tokens(payload: Any) -> int:
    if payload in ({}, [], "", None):
        return 0
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    if not encoded:
        return 0
    return max(1, len(encoded) // 4)


def _subset_payload(payload: Mapping[str, Any], *, keys: set[str]) -> dict[str, Any]:
    return {
        str(key): value
        for key, value in payload.items()
        if str(key) in keys and value not in ("", [], {}, None)
    }


def _artifact_token_map(payload: Mapping[str, Any], *, keys: Sequence[str]) -> dict[str, int]:
    artifact_tokens: dict[str, int] = {}
    for raw_key in keys:
        key = str(raw_key).strip()
        if not key:
            continue
        value = payload.get(key)
        if value in ("", [], {}, None):
            continue
        artifact_tokens[key] = _estimate_json_tokens({key: value})
    return artifact_tokens


def _packet_source_for_scenario(scenario: Mapping[str, Any]) -> str:
    explicit_source = str(scenario.get("packet_source", "")).strip()
    if explicit_source in _VALID_PACKET_SOURCES:
        return explicit_source
    family = str(scenario.get("family", "")).strip().replace("-", "_")
    if family in _GOVERNANCE_SLICE_FAMILIES:
        return "governance_slice"
    return "impact"


def _benchmark_session_namespace(
    *,
    scenario: Mapping[str, Any],
    mode: str,
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> str:
    normalized_mode = _normalize_mode(mode)
    return (
        f"benchmark-{_active_run_token(report_id, fallback='report')}"
        f"-s{max(1, int(shard_index))}-of-{max(1, int(shard_count))}"
        f"-{_active_run_token(cache_profile, fallback='warm')}"
        f"-{_active_run_token(str(scenario.get('scenario_id', '')).strip(), fallback='scenario')}"
        f"-{_active_run_token(normalized_mode, fallback='mode')}"
    )


def _build_packet_payload(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    existing_paths: Sequence[str],
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> tuple[str, dict[str, Any], dict[str, Any]]:
    normalized_mode = _normalize_mode(mode)
    requested_source = _packet_source_for_scenario(scenario)
    benchmark_session_id = _benchmark_session_namespace(
        scenario=scenario,
        mode=normalized_mode,
        report_id=report_id,
        cache_profile=cache_profile,
        shard_index=shard_index,
        shard_count=shard_count,
    )
    claimed_paths = list(existing_paths)
    if not _mode_uses_odylith(normalized_mode):
        stage = "repo_scan_baseline" if _is_repo_scan_baseline_mode(normalized_mode) else "raw_agent_baseline"
        return (
            normalized_mode,
            {},
            {
                "stage": stage,
                "initial_source": normalized_mode,
                "final_source": normalized_mode,
                "auto_escalated": False,
                "reasons": [],
            },
        )
    with _odylith_enabled_override(True):
        if requested_source == "governance_slice":
            payload = store.build_governance_slice(
                repo_root=repo_root,
                changed_paths=existing_paths,
                workstream=str(scenario.get("workstream", "")).strip(),
                component=str(scenario.get("component", "")).strip(),
                use_working_tree=False,
                working_tree_scope="session",
                session_id=benchmark_session_id,
                claimed_paths=[],
                runtime_mode="local",
                delivery_profile=agent_runtime_contract.AGENT_HOT_PATH_PROFILE,
                family_hint=str(scenario.get("family", "")).strip(),
                intent=str(scenario.get("intent", "")).strip(),
                validation_command_hints=[
                    str(token).strip()
                    for token in scenario.get("validation_commands", [])
                    if str(token).strip()
                ],
            )
            adaptive_escalation = {
                "stage": "governance_slice",
                "initial_source": "governance_slice",
                "final_source": "governance_slice",
                "auto_escalated": False,
                "reasons": [],
            }
            packet_source = "governance_slice"
        elif requested_source == "session_brief":
            payload = store.build_session_brief(
                repo_root=repo_root,
                changed_paths=existing_paths,
                use_working_tree=False,
                working_tree_scope="session",
                runtime_mode="local",
                session_id=benchmark_session_id,
                workstream=str(scenario.get("workstream", "")).strip(),
                intent=str(scenario.get("intent", "")).strip(),
                delivery_profile=agent_runtime_contract.AGENT_HOT_PATH_PROFILE,
                family_hint=str(scenario.get("family", "")).strip(),
                claimed_paths=claimed_paths,
                validation_command_hints=[
                    str(token).strip()
                    for token in scenario.get("validation_commands", [])
                    if str(token).strip()
                ],
                retain_impact_internal_context=False,
                skip_impact_runtime_warmup=True,
            )
            adaptive_escalation = {
                "stage": "session_brief",
                "initial_source": "session_brief",
                "final_source": "session_brief",
                "auto_escalated": False,
                "reasons": [],
            }
            packet_source = "session_brief"
        elif requested_source == "bootstrap_session":
            payload = store.build_session_bootstrap(
                repo_root=repo_root,
                changed_paths=existing_paths,
                use_working_tree=False,
                working_tree_scope="session",
                runtime_mode="local",
                session_id=benchmark_session_id,
                workstream=str(scenario.get("workstream", "")).strip(),
                intent=str(scenario.get("intent", "")).strip(),
                delivery_profile=agent_runtime_contract.AGENT_HOT_PATH_PROFILE,
                family_hint=str(scenario.get("family", "")).strip(),
                claimed_paths=claimed_paths,
                validation_command_hints=[
                    str(token).strip()
                    for token in scenario.get("validation_commands", [])
                    if str(token).strip()
                ],
                retain_impact_internal_context=False,
                skip_impact_runtime_warmup=True,
            )
            adaptive_escalation = {
                "stage": "bootstrap_session",
                "initial_source": "bootstrap_session",
                "final_source": "bootstrap_session",
                "auto_escalated": False,
                "reasons": [],
            }
            packet_source = "bootstrap_session"
        else:
            adaptive = store.build_adaptive_coding_packet(
                repo_root=repo_root,
                changed_paths=existing_paths,
                working_tree_scope="session",
                session_id=benchmark_session_id,
                claimed_paths=claimed_paths,
                runtime_mode="local",
                intent=str(scenario.get("intent", "")).strip(),
                family_hint=str(scenario.get("family", "")).strip(),
                workstream_hint=str(scenario.get("workstream", "")).strip(),
                validation_command_hints=[
                    str(token).strip()
                    for token in scenario.get("validation_commands", [])
                    if str(token).strip()
                ],
            )
            payload = dict(adaptive.get("payload", {})) if isinstance(adaptive.get("payload"), Mapping) else {}
            packet_source = str(adaptive.get("packet_source", "")).strip() or requested_source
            adaptive_escalation = (
                dict(adaptive.get("adaptive_escalation", {}))
                if isinstance(adaptive.get("adaptive_escalation"), Mapping)
                else {}
            )
    selector_diagnostics = (
        dict(payload.pop("benchmark_selector_diagnostics", {}))
        if isinstance(payload.get("benchmark_selector_diagnostics"), Mapping)
        else {}
    )
    if selector_diagnostics:
        adaptive_escalation["benchmark_selector_diagnostics"] = selector_diagnostics
    return packet_source, payload, adaptive_escalation


def _packet_token_breakdown(
    *,
    payload: Mapping[str, Any],
    packet_source: str,
    mode: str,
    full_scan: Mapping[str, Any],
    raw_prompt: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    if _is_repo_scan_baseline_mode(normalized_mode):
        prompt_tokens = _estimate_json_tokens(full_scan)
        return {
            "effective_estimated_tokens": prompt_tokens,
            "effective_token_basis": "codex_prompt_bundle",
            "codex_prompt_estimated_tokens": prompt_tokens,
            "total_payload_estimated_tokens": prompt_tokens,
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {"full_scan": prompt_tokens},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "packet_source": _REPO_SCAN_BASELINE_MODE,
        }
    if _is_raw_agent_baseline_mode(normalized_mode):
        raw_prompt_payload = dict(raw_prompt or {})
        prompt_tokens = _estimate_json_tokens(raw_prompt_payload)
        return {
            "effective_estimated_tokens": prompt_tokens,
            "effective_token_basis": "codex_prompt_bundle",
            "codex_prompt_estimated_tokens": prompt_tokens,
            "total_payload_estimated_tokens": prompt_tokens,
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {"raw_prompt": prompt_tokens},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "packet_source": _RAW_AGENT_BASELINE_MODE,
        }
    prompt_keys = set(_PROMPT_PAYLOAD_KEYS)
    if not isinstance(payload.get("narrowing_guidance"), Mapping):
        prompt_keys.discard("narrowing_guidance")
    prompt_payload = _subset_payload(payload, keys=prompt_keys)
    runtime_payload = _subset_payload(payload, keys=set(_RUNTIME_CONTRACT_KEYS))
    operator_keys = {
        str(key)
        for key, value in payload.items()
        if str(key) not in prompt_keys and str(key) not in _RUNTIME_CONTRACT_KEYS and value not in ("", [], {}, None)
    }
    operator_payload = _subset_payload(payload, keys=operator_keys)
    prompt_tokens = _estimate_json_tokens(prompt_payload)
    prompt_artifacts = _artifact_token_map(payload, keys=sorted(prompt_keys))
    runtime_contract_artifacts = _artifact_token_map(payload, keys=sorted(_RUNTIME_CONTRACT_KEYS))
    operator_diag_artifacts = _artifact_token_map(payload, keys=sorted(operator_keys))
    return {
        "effective_estimated_tokens": prompt_tokens,
        "effective_token_basis": "codex_prompt_bundle",
        "codex_prompt_estimated_tokens": prompt_tokens,
        "total_payload_estimated_tokens": _estimate_json_tokens(payload),
        "runtime_contract_estimated_tokens": _estimate_json_tokens(runtime_payload),
        "operator_diag_estimated_tokens": _estimate_json_tokens(operator_payload),
        "prompt_artifact_tokens": prompt_artifacts,
        "runtime_contract_artifact_tokens": runtime_contract_artifacts,
        "operator_diag_artifact_tokens": operator_diag_artifacts,
        "packet_source": packet_source,
    }


def _recent_reasoning_timing_index(*, repo_root: Path, limit: int = 256) -> dict[str, dict[str, Any]]:
    rows = store.odylith_control_state.load_timing_rows(repo_root=repo_root, limit=max(16, int(limit)))  # noqa: SLF001
    return {
        str(row.get("timing_id", "")).strip(): dict(row)
        for row in rows
        if isinstance(row, Mapping)
        and str(row.get("timing_id", "")).strip()
        and str(row.get("category", "")).strip() == "reasoning"
    }


def _timing_trace(
    *,
    repo_root: Path,
    before: Mapping[str, Mapping[str, Any]],
    operations: Sequence[str],
) -> dict[str, Any]:
    target_operations = {str(token).strip() for token in operations if str(token).strip()}
    after = _recent_reasoning_timing_index(repo_root=repo_root)
    rows = [
        dict(row)
        for timing_id, row in after.items()
        if timing_id not in before and str(row.get("operation", "")).strip() in target_operations
    ]
    rows.sort(key=lambda row: str(row.get("ts_iso", "")).strip())
    operation_trace: dict[str, dict[str, Any]] = {}
    for row in rows:
        operation = str(row.get("operation", "")).strip()
        if not operation:
            continue
        metadata = dict(row.get("metadata", {})) if isinstance(row.get("metadata"), Mapping) else {}
        operation_trace[operation] = {
            "duration_ms": round(float(row.get("duration_ms", 0.0) or 0.0), 3),
            "stage_timings": {
                str(key).strip(): round(float(value or 0.0), 3)
                for key, value in dict(metadata.get("stage_timings", {})).items()
                if str(key).strip()
            }
            if isinstance(metadata.get("stage_timings"), Mapping)
            else {},
            "metadata": {
                key: value
                for key, value in {
                    "packet_state": str(metadata.get("packet_state", "")).strip(),
                    "family_hint": str(metadata.get("family_hint", "")).strip(),
                    "confidence_tier": str(metadata.get("confidence_tier", "")).strip(),
                    "full_scan_recommended": bool(metadata.get("full_scan_recommended")),
                }.items()
                if value not in ("", [], {}, None, False)
            },
        }
    return {
        "operation_count": len(operation_trace),
        "operations": operation_trace,
    }


def _latency_measurement_fields(
    *,
    latency_ms: float,
    timing_trace: Mapping[str, Any] | None,
) -> dict[str, float]:
    operations = (
        dict(timing_trace.get("operations", {}))
        if isinstance(timing_trace, Mapping) and isinstance(timing_trace.get("operations"), Mapping)
        else {}
    )
    instrumented_total = round(
        sum(
            float(dict(payload).get("duration_ms", 0.0) or 0.0)
            for payload in operations.values()
            if isinstance(payload, Mapping)
        ),
        3,
    )
    uninstrumented_overhead = round(max(float(latency_ms or 0.0) - instrumented_total, 0.0), 3)
    return {
        "instrumented_reasoning_duration_ms": instrumented_total,
        "uninstrumented_overhead_ms": uninstrumented_overhead,
    }


def _governance_candidate_paths(packet_payload: Mapping[str, Any]) -> list[str]:
    governance_obligations = _benchmark_governance_obligations(packet_payload)
    touched_workstreams = governance_obligations.get("touched_workstreams", [])
    touched_components = governance_obligations.get("touched_components", [])
    required_diagrams = governance_obligations.get("required_diagrams", [])
    closeout_docs = governance_obligations.get("closeout_docs", [])
    rows: list[str] = []
    if isinstance(touched_workstreams, list):
        for row in touched_workstreams:
            if not isinstance(row, Mapping):
                continue
            metadata = dict(row.get("metadata", {})) if isinstance(row.get("metadata"), Mapping) else {}
            for key in ("path",):
                token = str(row.get(key, "")).strip()
                if token:
                    rows.append(token)
            promoted_to_plan = str(metadata.get("promoted_to_plan", "")).strip()
            if promoted_to_plan:
                rows.append(promoted_to_plan)
    if isinstance(touched_components, list):
        rows.extend(
            str(row.get("path", "")).strip()
            for row in touched_components
            if isinstance(row, Mapping) and str(row.get("path", "")).strip()
        )
    if isinstance(required_diagrams, list):
        for row in required_diagrams:
            if isinstance(row, Mapping):
                for key in ("path", "source_mmd"):
                    token = str(row.get(key, "")).strip()
                    if token:
                        rows.append(token)
            else:
                token = str(row).strip()
                if token:
                    rows.append(token)
    if isinstance(closeout_docs, list):
        rows.extend(str(token).strip() for token in closeout_docs if str(token).strip())
    return _dedupe_strings(rows)


def _embedded_governance_signal(packet_payload: Mapping[str, Any]) -> dict[str, Any]:
    context_packet = dict(packet_payload.get("context_packet", {})) if isinstance(packet_payload.get("context_packet"), Mapping) else {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    return governance_signal_codec.expand_governance_signal(
        dict(route.get("governance", {})) if isinstance(route.get("governance"), Mapping) else {}
    )


def _benchmark_governance_obligations(packet_payload: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(packet_payload.get("governance_obligations"), Mapping):
        return dict(packet_payload.get("governance_obligations", {}))
    governance = _embedded_governance_signal(packet_payload)
    compact: dict[str, Any] = {}
    for key in (
        "touched_workstream_count",
        "primary_workstream_id",
        "touched_component_count",
        "primary_component_id",
        "required_diagram_count",
        "linked_bug_count",
        "closeout_doc_count",
        "workstream_state_action_count",
    ):
        value = governance.get(key)
        if value not in ("", [], {}, None, False):
            compact[key] = value
    return compact


def _orchestration_request_payload(
    *,
    scenario: Mapping[str, Any],
    packet_payload: Mapping[str, Any],
) -> dict[str, Any]:
    context_packet = dict(packet_payload.get("context_packet", {})) if isinstance(packet_payload.get("context_packet"), Mapping) else {}
    session_payload = dict(packet_payload.get("session", {})) if isinstance(packet_payload.get("session"), Mapping) else {}
    impact_summary = dict(packet_payload.get("impact_summary", {})) if isinstance(packet_payload.get("impact_summary"), Mapping) else {}
    top_level_components = [
        str(row.get("component_id", "")).strip()
        for row in packet_payload.get("components", [])
        if isinstance(packet_payload.get("components"), list) and isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
    ]
    components = [
        str(row.get("component_id", "")).strip()
        for row in impact_summary.get("components", [])
        if isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
    ] if isinstance(impact_summary.get("components"), list) else []
    governance_obligations = _benchmark_governance_obligations(packet_payload)
    governance_workstreams = [
        str(row.get("entity_id", "")).strip()
        for row in governance_obligations.get("touched_workstreams", [])
        if isinstance(governance_obligations.get("touched_workstreams"), list) and isinstance(row, Mapping) and str(row.get("entity_id", "")).strip()
    ]
    primary_governance_workstream = str(governance_obligations.get("primary_workstream_id", "")).strip()
    primary_governance_component = str(governance_obligations.get("primary_component_id", "")).strip()
    recommended_commands = _dedupe_strings(
        [
            *(
                str(token).strip()
                for token in scenario.get("validation_commands", [])
                if str(token).strip()
            ),
            *(
                str(token).strip()
                for token in packet_payload.get("recommended_commands", [])
                if isinstance(packet_payload.get("recommended_commands"), list) and str(token).strip()
            ),
        ]
    )
    correctness_critical = bool(scenario.get("correctness_critical")) and bool(recommended_commands)
    family = str(scenario.get("family", "")).strip()
    analysis_task = str(scenario.get("kind", "")).strip() == "architecture" or family in _ANALYSIS_FAMILIES or not bool(scenario.get("needs_write"))
    scope_paths = _scenario_expected_write_paths(scenario) if bool(scenario.get("needs_write")) else [
        str(token).strip()
        for token in scenario.get("changed_paths", [])
        if str(token).strip()
    ]
    candidate_paths = _dedupe_strings(
        [
            *scope_paths,
            *_governance_candidate_paths(packet_payload),
        ]
    )
    request_payload = {
        "prompt": str(scenario.get("prompt", "")).strip(),
        "acceptance_criteria": [str(token).strip() for token in scenario.get("acceptance_criteria", []) if str(token).strip()],
        "candidate_paths": candidate_paths,
        "workstreams": _dedupe_strings(
            [
                str(scenario.get("workstream", "")).strip(),
                primary_governance_workstream,
                *governance_workstreams,
            ]
        ),
        "components": _dedupe_strings([primary_governance_component, *components, *top_level_components]),
        "validation_commands": recommended_commands,
        "accuracy_preference": "accuracy",
        "repo_work": True,
        "task_kind": "analysis" if analysis_task else "implementation",
        "phase": "analysis" if analysis_task else "implementation",
        "needs_write": bool(scenario.get("needs_write")),
        "correctness_critical": correctness_critical,
        "evidence_cone_grounded": not bool(
            packet_payload.get("full_scan_recommended")
            or context_packet.get("full_scan_recommended")
        ),
    }
    for key in ("routing_handoff", "context_packet", "evidence_pack", "optimization_snapshot", "architecture_audit", "session"):
        value = packet_payload.get(key)
        if isinstance(value, Mapping) and value:
            request_payload[key] = dict(value)
    if session_payload and "session" not in request_payload:
        request_payload["session"] = session_payload
    return request_payload


def _decision_summary(
    *,
    decision: subagent_orchestrator.OrchestrationDecision,
    mode: str,
) -> dict[str, Any]:
    leaf_count = len(decision.subtasks)
    native_mode = str(decision.mode or "").strip()
    effective_mode = native_mode
    effective_leaf_count = leaf_count
    clamped = False
    if _is_no_fanout_mode(mode) and native_mode in {"parallel_batch", "serial_batch"}:
        effective_mode = "single_leaf" if leaf_count else "local_only"
        effective_leaf_count = min(1, leaf_count) if leaf_count else 0
        clamped = True
    odylith_adoption = dict(decision.odylith_adoption) if isinstance(decision.odylith_adoption, Mapping) else {}
    return {
        "native_mode": native_mode,
        "mode": effective_mode,
        "delegate": bool(decision.delegate),
        "leaf_count": effective_leaf_count,
        "native_leaf_count": leaf_count,
        "parallel_safety": str(decision.parallel_safety or "").strip(),
        "manual_review_recommended": bool(decision.manual_review_recommended),
        "clamped_no_fanout": clamped,
        "local_only_reasons": [str(token).strip() for token in decision.local_only_reasons if str(token).strip()][:4],
        "odylith_adoption": odylith_adoption,
    }


def _request_payload_odylith_adoption(request_payload: Mapping[str, Any]) -> dict[str, Any]:
    routing_handoff = (
        dict(request_payload.get("routing_handoff", {}))
        if isinstance(request_payload.get("routing_handoff"), Mapping)
        else {}
    )
    context_packet = (
        dict(request_payload.get("context_packet", {}))
        if isinstance(request_payload.get("context_packet"), Mapping)
        else {}
    )
    session_payload = (
        dict(request_payload.get("session", {}))
        if isinstance(request_payload.get("session"), Mapping)
        else {}
    )
    architecture_audit = (
        dict(request_payload.get("architecture_audit", {}))
        if isinstance(request_payload.get("architecture_audit"), Mapping)
        else {}
    )
    evidence_pack = (
        dict(request_payload.get("evidence_pack", {}))
        if isinstance(request_payload.get("evidence_pack"), Mapping)
        else {}
    )
    auto_grounding = (
        dict(request_payload.get("orchestration_auto_grounding", {}))
        if isinstance(request_payload.get("orchestration_auto_grounding"), Mapping)
        else {}
    )
    if not any((routing_handoff, context_packet, architecture_audit, evidence_pack)):
        return {}
    route = dict(context_packet.get("route", {})) if isinstance(context_packet.get("route"), Mapping) else {}
    packet_quality = (
        dict(context_packet.get("packet_quality", {}))
        if isinstance(context_packet.get("packet_quality"), Mapping)
        else {}
    )
    diagram_watch_gaps = architecture_audit.get("diagram_watch_gaps", [])
    diagram_watch_gap_count = len(diagram_watch_gaps) if isinstance(diagram_watch_gaps, list) else 0
    full_scan_recommended = bool(
        auto_grounding.get("full_scan_recommended")
        or context_packet.get("full_scan_recommended")
        or architecture_audit.get("full_scan_recommended")
    )
    selection_state = str(context_packet.get("selection_state", "")).strip()
    routing_confidence = (
        str(routing_handoff.get("routing_confidence", "")).strip()
        or str(packet_quality.get("routing_confidence", "")).strip()
    )
    session_namespace = (
        str(session_payload.get("session_namespace", "")).strip()
        or str(session_payload.get("session_id", "")).strip()
        or str(context_packet.get("session_id", "")).strip()
    )
    route_ready = bool(routing_handoff.get("route_ready") or route.get("route_ready"))
    native_spawn_ready = bool(routing_handoff.get("native_spawn_ready") or route.get("native_spawn_ready"))
    narrowing_required = bool(routing_handoff.get("narrowing_required") or route.get("narrowing_required"))
    auto_grounding_applied = bool(auto_grounding.get("applied"))
    grounded = bool(
        not full_scan_recommended
        and diagram_watch_gap_count <= 0
        and (
            bool(request_payload.get("evidence_cone_grounded"))
            or bool(auto_grounding.get("grounded"))
            or route_ready
            or native_spawn_ready
            or selection_state.startswith("x:")
            or selection_state in {"explicit", "inferred_confident"}
            or routing_confidence in {"medium", "high"}
        )
    )
    grounding_source = "auto_grounded" if auto_grounding_applied else "supplied_packet"
    packet_kind = str(context_packet.get("packet_kind", "")).strip()
    operation = (
        str(auto_grounding.get("operation", "")).strip()
        or str(request_payload.get("odylith_operation", "")).strip()
        or packet_kind
    )
    return {
        "packet_present": True,
        "grounding_source": grounding_source,
        "auto_grounding_applied": auto_grounding_applied,
        "operation": operation,
        "packet_kind": packet_kind or operation,
        "grounded": grounded,
        "route_ready": route_ready,
        "native_spawn_ready": native_spawn_ready,
        "narrowing_required": narrowing_required,
        "full_scan_recommended": full_scan_recommended,
        "diagram_watch_gap_count": diagram_watch_gap_count,
        "requires_widening": bool(full_scan_recommended or diagram_watch_gap_count > 0),
        "selection_state": selection_state,
        "routing_confidence": routing_confidence,
        "runtime_source": "none",
        "runtime_transport": "none",
        "workspace_daemon_reused": False,
        "session_namespace": session_namespace,
        "session_namespaced": bool(session_namespace),
        "mixed_local_fallback": False,
    }


def _orchestration_error_summary(
    *,
    error: leaf_router.RouterInputError,
    mode: str,
    request_payload: Mapping[str, Any],
) -> dict[str, Any]:
    summary = {
        "native_mode": "local_only",
        "mode": "local_only",
        "delegate": False,
        "leaf_count": 0,
        "native_leaf_count": 0,
        "parallel_safety": "local_only",
        "manual_review_recommended": True,
        "clamped_no_fanout": _is_no_fanout_mode(mode),
        "local_only_reasons": ["benchmark_orchestration_contract_gap"],
        "odylith_adoption": _request_payload_odylith_adoption(request_payload),
        "error": error.as_payload(),
    }
    return summary


def _safe_orchestration_summary(
    *,
    request_payload: Mapping[str, Any],
    repo_root: Path,
    mode: str,
) -> dict[str, Any]:
    try:
        decision = subagent_orchestrator.orchestrate_prompt(
            subagent_orchestrator.orchestration_request_from_mapping(request_payload),
            repo_root=repo_root,
        )
    except leaf_router.RouterInputError as error:
        return _orchestration_error_summary(error=error, mode=mode, request_payload=request_payload)
    return _decision_summary(decision=decision, mode=mode)


class _BenchmarkAdoptionProofTimeout(RuntimeError):
    """Raised when a benchmark adoption-proof sample exceeds its hard timeout."""


def _adoption_proof_timeout_seconds() -> float:
    raw_value = str(os.environ.get("ODYLITH_BENCHMARK_ADOPTION_PROOF_TIMEOUT_SECONDS", "")).strip()
    if not raw_value:
        return _BENCHMARK_ADOPTION_PROOF_SAMPLE_TIMEOUT_SECONDS
    with contextlib.suppress(ValueError):
        return max(0.0, float(raw_value))
    return _BENCHMARK_ADOPTION_PROOF_SAMPLE_TIMEOUT_SECONDS


def _adoption_proof_summary_worker(
    *,
    request_payload: Mapping[str, Any],
    repo_root_str: str,
    mode: str,
    send_conn: Any,
) -> None:
    with contextlib.suppress(OSError):
        os.setsid()
    payload: dict[str, Any]
    try:
        payload = {
            "ok": True,
            "summary": _safe_orchestration_summary(
                request_payload=request_payload,
                repo_root=Path(repo_root_str),
                mode=mode,
            ),
        }
    except Exception as error:  # pragma: no cover - exercised via parent process wrapper
        payload = {
            "ok": False,
            "error_type": error.__class__.__name__,
            "message": str(error).strip(),
        }
    with contextlib.suppress(BrokenPipeError, EOFError, OSError):
        send_conn.send(payload)
    with contextlib.suppress(OSError):
        send_conn.close()


def _terminate_process_group(*, pid: int) -> None:
    target = max(0, int(pid))
    if target <= 0:
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(target, signal.SIGTERM)
    time.sleep(_BENCHMARK_ADOPTION_PROOF_TERMINATION_GRACE_SECONDS)
    if not _process_exists(target):
        return
    with contextlib.suppress(ProcessLookupError, PermissionError):
        os.killpg(target, signal.SIGKILL)
    time.sleep(_BENCHMARK_ADOPTION_PROOF_TERMINATION_GRACE_SECONDS)


def _spawn_safe_main_module_available() -> bool:
    main_module = sys.modules.get("__main__")
    main_file = str(getattr(main_module, "__file__", "") or "").strip()
    return bool(main_file and Path(main_file).is_file())


def _bounded_orchestration_summary(
    *,
    request_payload: Mapping[str, Any],
    repo_root: Path,
    mode: str,
    timeout_seconds: float | None = None,
) -> dict[str, Any]:
    timeout = (
        _adoption_proof_timeout_seconds()
        if timeout_seconds is None
        else max(0.0, float(timeout_seconds))
    )
    if timeout <= 0 or not _spawn_safe_main_module_available():
        return _safe_orchestration_summary(
            request_payload=request_payload,
            repo_root=repo_root,
            mode=mode,
        )
    root = Path(repo_root).resolve()
    context = multiprocessing.get_context("spawn")
    recv_conn, send_conn = context.Pipe(duplex=False)
    process = context.Process(
        target=_adoption_proof_summary_worker,
        kwargs={
            "request_payload": dict(request_payload),
            "repo_root_str": str(root),
            "mode": mode,
            "send_conn": send_conn,
        },
        name="odylith-benchmark-adoption-proof",
    )
    process.start()
    send_conn.close()
    process.join(timeout)
    if process.is_alive():
        _terminate_process_group(pid=int(process.pid or 0))
        process.join(_BENCHMARK_ADOPTION_PROOF_TERMINATION_GRACE_SECONDS)
        if process.is_alive():
            with contextlib.suppress(ProcessLookupError, OSError, ValueError):
                process.kill()
            process.join(_BENCHMARK_ADOPTION_PROOF_TERMINATION_GRACE_SECONDS)
        _terminate_processes(pids=_benchmark_owned_codex_process_ids())
        with contextlib.suppress(OSError):
            recv_conn.close()
        raise _BenchmarkAdoptionProofTimeout(
            f"benchmark adoption-proof sample exceeded {timeout:.1f}s"
        )
    payload: dict[str, Any] = {}
    if recv_conn.poll():
        raw = recv_conn.recv()
        if isinstance(raw, Mapping):
            payload = dict(raw)
    with contextlib.suppress(OSError):
        recv_conn.close()
    exitcode = int(process.exitcode or 0)
    if bool(payload.get("ok")):
        summary = payload.get("summary")
        return dict(summary) if isinstance(summary, Mapping) else {}
    if payload:
        error_type = str(payload.get("error_type", "")).strip() or "RuntimeError"
        message = str(payload.get("message", "")).strip() or "benchmark adoption-proof sample failed"
        raise RuntimeError(f"{error_type}: {message}")
    if exitcode != 0:
        raise RuntimeError(f"benchmark adoption-proof sample exited with code {exitcode}")
    raise RuntimeError("benchmark adoption-proof sample exited without returning a summary")


def _observed_packet_paths(payload: Mapping[str, Any]) -> list[str]:
    rows: list[str] = []
    for key in ("changed_paths", "explicit_paths", "relevant_docs", "docs"):
        value = payload.get(key, [])
        if isinstance(value, list):
            rows.extend(path_bundle_codec.expand_path_rows(value))
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    guidance_behavior_summary = guidance_behavior_runtime.summary_from_sources(payload, context_packet, limit=6)
    if guidance_behavior_summary:
        related_refs = guidance_behavior_summary.get("related_guidance_refs", [])
        if isinstance(related_refs, list):
            rows.extend(path_bundle_codec.expand_path_rows(related_refs))
        source_refs = guidance_behavior_summary.get("source_refs", [])
        if isinstance(source_refs, list):
            rows.extend(
                path
                for path in path_bundle_codec.expand_path_rows(source_refs)
                if path.endswith("guidance-behavior-evaluation-corpus.v1.json")
            )
    character_summary = character_runtime.summary_from_sources(payload, context_packet, limit=6)
    if character_summary:
        source_refs = character_summary.get("source_refs", [])
        if isinstance(source_refs, list):
            rows.extend(
                path
                for path in path_bundle_codec.expand_path_rows(source_refs)
                if path.endswith("agent-operating-character-evaluation-corpus.v1.json")
            )
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    for key in ("changed_paths", "explicit_paths"):
        value = anchors.get(key, [])
        if isinstance(value, list):
            rows.extend(path_bundle_codec.expand_path_rows(value))
    for row in payload.get("recommended_tests", []):
        if isinstance(row, Mapping):
            for key in ("test_path", "path"):
                token = str(row.get(key, "")).strip()
                if token:
                    rows.append(token)
    architecture_audit = dict(payload.get("architecture_audit", {})) if isinstance(payload.get("architecture_audit"), Mapping) else {}
    for key in ("changed_paths", "required_reads"):
        value = architecture_audit.get(key, [])
        if isinstance(value, list):
            rows.extend(str(token).strip() for token in value if str(token).strip())
    impact_summary = dict(payload.get("impact_summary", {})) if isinstance(payload.get("impact_summary"), Mapping) else {}
    for row in impact_summary.get("guidance_brief", []):
        if not isinstance(row, Mapping):
            continue
        for key in ("canonical_source", "chunk_path"):
            token = str(row.get(key, "")).strip()
            if token:
                rows.append(token)
    fallback_scan = dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {}
    if isinstance(fallback_scan.get("results"), list):
        rows.extend(
            str(row.get("path", "")).strip()
            for row in fallback_scan.get("results", [])
            if isinstance(row, Mapping) and str(row.get("path", "")).strip()
        )
    governance_obligations = _benchmark_governance_obligations(payload)
    if isinstance(governance_obligations.get("closeout_docs"), list):
        rows.extend(str(token).strip() for token in governance_obligations.get("closeout_docs", []) if str(token).strip())
    if isinstance(payload.get("components"), list):
        rows.extend(
            str(row.get("path", "")).strip()
            for row in payload.get("components", [])
            if isinstance(row, Mapping) and str(row.get("path", "")).strip()
        )
    if isinstance(payload.get("diagrams"), list):
        for row in payload.get("diagrams", []):
            if not isinstance(row, Mapping):
                continue
            for key in ("source_mmd", "path", "source_svg", "source_png"):
                token = str(row.get(key, "")).strip()
                if token:
                    rows.append(token)
    return _dedupe_strings(rows)


def _path_recall(
    *,
    required_paths: Sequence[str],
    observed_paths: Sequence[str],
) -> tuple[float, list[str]]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    if not required:
        return 1.0, []
    misses = sorted(required.difference(observed))
    return round((len(required) - len(misses)) / max(1, len(required)), 3), misses


def _scenario_supporting_paths(scenario: Mapping[str, Any]) -> list[str]:
    raw_paths = scenario.get("supporting_paths", [])
    if not isinstance(raw_paths, list):
        return []
    return _dedupe_strings([str(token).strip() for token in raw_paths if str(token).strip()])


def _scenario_expected_write_paths(scenario: Mapping[str, Any]) -> list[str]:
    if not bool(scenario.get("needs_write")):
        return []
    raw_expected = scenario.get("expected_write_paths", [])
    explicit = _dedupe_strings(
        [str(token).strip() for token in raw_expected if str(token).strip()]
        if isinstance(raw_expected, list)
        else []
    )
    if explicit:
        return explicit
    raw_changed = scenario.get("changed_paths", [])
    if not isinstance(raw_changed, list):
        return []
    return _dedupe_strings(
        [str(token).strip() for token in raw_changed if str(token).strip()]
    )


def _precision_metrics(
    *,
    required_paths: Sequence[str],
    supporting_paths: Sequence[str] = (),
    observed_paths: Sequence[str],
    expected_write_paths: Sequence[str],
    candidate_write_paths: Sequence[str],
) -> dict[str, Any]:
    required = {str(token).strip() for token in required_paths if str(token).strip()}
    supporting = {str(token).strip() for token in supporting_paths if str(token).strip()}
    relevant = required.union(supporting)
    observed = {str(token).strip() for token in observed_paths if str(token).strip()}
    expected_write = {str(token).strip() for token in expected_write_paths if str(token).strip()}
    candidate_write = {str(token).strip() for token in candidate_write_paths if str(token).strip()}

    observed_supporting = sorted(supporting.intersection(observed))
    observed_relevant = sorted(relevant.intersection(observed))
    hallucinated_surfaces = sorted(observed.difference(relevant))
    required_path_precision = (
        round(len(observed_relevant) / max(1, len(observed)), 3)
        if observed
        else 1.0
        if not relevant
        else 0.0
    )
    hallucinated_surface_rate = (
        round(len(hallucinated_surfaces) / max(1, len(observed)), 3)
        if observed
        else 0.0
    )

    matched_write_paths = sorted(expected_write.intersection(candidate_write))
    unnecessary_widening_paths = sorted(candidate_write.difference(expected_write))
    write_surface_precision = (
        round(len(matched_write_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 1.0
        if not expected_write
        else 0.0
    )
    unnecessary_widening_rate = (
        round(len(unnecessary_widening_paths) / max(1, len(candidate_write)), 3)
        if candidate_write
        else 0.0
    )

    return {
        "observed_path_count": len(observed),
        "supporting_path_count": len(supporting),
        "supporting_path_hits": observed_supporting[:12],
        "required_path_precision_basis": "required_plus_supporting_paths" if supporting else "required_paths",
        "required_path_precision": required_path_precision,
        "hallucinated_surface_count": len(hallucinated_surfaces),
        "hallucinated_surface_rate": hallucinated_surface_rate,
        "hallucinated_surfaces": hallucinated_surfaces[:12],
        "expected_write_path_count": len(expected_write),
        "candidate_write_path_count": len(candidate_write),
        "candidate_write_paths": sorted(candidate_write)[:12],
        "write_surface_precision": write_surface_precision,
        "unnecessary_widening_count": len(unnecessary_widening_paths),
        "unnecessary_widening_rate": unnecessary_widening_rate,
        "unnecessary_widening_paths": unnecessary_widening_paths[:12],
    }


def _packet_result(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    changed_paths = [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
    existing_paths = _existing_repo_paths(repo_root=repo_root, paths=changed_paths)
    timing_before = _recent_reasoning_timing_index(repo_root=repo_root)
    started_at = time.perf_counter()
    packet_source, payload, adaptive_escalation = _build_packet_payload(
        repo_root=repo_root,
        scenario=scenario,
        mode=mode,
        existing_paths=existing_paths,
        report_id=report_id,
        cache_profile=cache_profile,
        shard_index=shard_index,
        shard_count=shard_count,
    )
    payload = _apply_packet_fixture(payload=payload, scenario=scenario, packet_source=packet_source)
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    timing_trace = _timing_trace(
        repo_root=repo_root,
        before=timing_before,
        operations=("impact", "governance_slice", "session_brief", "bootstrap_session", "architecture"),
    )
    packet_summary = store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001
    packet_summary["packet_source"] = packet_source
    measurement_payload = dict(payload)
    supplemented_doc_count = 0
    if _mode_uses_odylith(normalized_mode):
        prompt_keys = set(_PROMPT_PAYLOAD_KEYS)
        if not isinstance(payload.get("narrowing_guidance"), Mapping):
            prompt_keys.discard("narrowing_guidance")
        full_prompt_payload = dict(payload)
        full_prompt_payload.setdefault("components", [])
        full_prompt_payload.setdefault("docs", [])
        supplemented_prompt_payload = odylith_benchmark_prompt_payloads.supplement_live_prompt_payload(
            repo_root=repo_root,
            scenario=scenario,
            prompt_payload=_subset_payload(payload, keys=prompt_keys),
            packet_source=packet_source,
            changed_paths=existing_paths,
            full_payload=full_prompt_payload,
        )
        measurement_payload.update(supplemented_prompt_payload)
        supplemented_doc_count = len(
            [
                str(token).strip()
                for token in supplemented_prompt_payload.get("docs", [])
                if isinstance(supplemented_prompt_payload.get("docs"), list) and str(token).strip()
            ]
        )
    expectation_ok, expectation_details = store._packet_satisfies_evaluation_expectations(  # noqa: SLF001
        packet_summary,
        dict(scenario.get("expect", {})),
    )
    if _is_repo_scan_baseline_mode(normalized_mode):
        full_scan = store._full_scan_guidance(  # noqa: SLF001
            repo_root=repo_root,
            reason="benchmark_repo_scan_baseline",
            query=str(scenario.get("prompt", "")).strip(),
            changed_paths=existing_paths,
            perform_scan=True,
            result_limit=12,
        )
    else:
        full_scan = {
            "performed": False,
            "terms": [],
            "roots": [],
            "commands": [],
            "results": [],
            "reason": "",
            "reason_message": "",
            "changed_paths": list(existing_paths),
        }
    raw_prompt = _raw_prompt_bundle(scenario=scenario) if _is_raw_agent_baseline_mode(normalized_mode) else {}
    raw_prompt_visible_paths = _raw_prompt_visible_paths(repo_root=repo_root, raw_prompt=raw_prompt) if raw_prompt else []
    observed_paths = _dedupe_strings(
        [
            *_observed_packet_paths(measurement_payload),
            *(
                str(row.get("path", "")).strip()
                for row in full_scan.get("results", [])
                if isinstance(full_scan.get("results"), list) and isinstance(row, Mapping) and str(row.get("path", "")).strip()
            ),
            *raw_prompt_visible_paths,
        ]
    )
    required_path_recall, required_path_misses = _path_recall(
        required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
        observed_paths=observed_paths,
    )
    _critical_recall, critical_path_misses = _path_recall(
        required_paths=[str(token).strip() for token in scenario.get("critical_paths", []) if str(token).strip()],
        observed_paths=observed_paths,
    )
    orchestration_payload = _orchestration_request_payload(scenario=scenario, packet_payload=payload)
    decision_summary = (
        _raw_agent_orchestration_summary()
        if _is_raw_agent_baseline_mode(normalized_mode)
        else _safe_orchestration_summary(
            request_payload=orchestration_payload,
            repo_root=repo_root,
            mode=normalized_mode,
        )
    )
    expected_write_paths = _scenario_expected_write_paths(scenario)
    candidate_write_paths = (
        _dedupe_strings(orchestration_payload.get("candidate_paths", []))
        if bool(scenario.get("needs_write")) and isinstance(orchestration_payload.get("candidate_paths"), list)
        else []
    )
    precision_metrics = _precision_metrics(
        required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
        supporting_paths=_scenario_supporting_paths(scenario),
        observed_paths=observed_paths,
        expected_write_paths=expected_write_paths,
        candidate_write_paths=candidate_write_paths,
    )
    token_breakdown = _packet_token_breakdown(
        payload=measurement_payload,
        packet_source=packet_source,
        mode=normalized_mode,
        full_scan=full_scan,
        raw_prompt=raw_prompt,
    )
    latency_fields = _latency_measurement_fields(latency_ms=duration_ms, timing_trace=timing_trace)
    return {
        "kind": "packet",
        "mode": normalized_mode,
        "packet_source": str(token_breakdown.get("packet_source", packet_source)).strip() or packet_source,
        "latency_ms": duration_ms,
        "context_engine_packet_build_ms": duration_ms,
        "instrumented_reasoning_duration_ms": float(
            latency_fields.get("instrumented_reasoning_duration_ms", 0.0) or 0.0
        ),
        "uninstrumented_overhead_ms": float(latency_fields.get("uninstrumented_overhead_ms", 0.0) or 0.0),
        "packet": packet_summary,
        "expectation_ok": expectation_ok,
        "expectation_details": expectation_details,
        "required_path_recall": required_path_recall,
        "required_path_misses": required_path_misses,
        "critical_path_misses": critical_path_misses,
        "observed_paths": observed_paths[:12],
        "observed_path_count": int(precision_metrics.get("observed_path_count", 0) or 0),
        "required_path_precision": float(precision_metrics.get("required_path_precision", 0.0) or 0.0),
        "hallucinated_surface_count": int(precision_metrics.get("hallucinated_surface_count", 0) or 0),
        "hallucinated_surface_rate": float(precision_metrics.get("hallucinated_surface_rate", 0.0) or 0.0),
        "hallucinated_surfaces": list(precision_metrics.get("hallucinated_surfaces", []))
        if isinstance(precision_metrics.get("hallucinated_surfaces"), list)
        else [],
        "expected_write_path_count": int(precision_metrics.get("expected_write_path_count", 0) or 0),
        "candidate_write_path_count": int(precision_metrics.get("candidate_write_path_count", 0) or 0),
        "candidate_write_paths": list(precision_metrics.get("candidate_write_paths", []))
        if isinstance(precision_metrics.get("candidate_write_paths"), list)
        else [],
        "write_surface_precision": float(precision_metrics.get("write_surface_precision", 0.0) or 0.0),
        "unnecessary_widening_count": int(precision_metrics.get("unnecessary_widening_count", 0) or 0),
        "unnecessary_widening_rate": float(precision_metrics.get("unnecessary_widening_rate", 0.0) or 0.0),
        "unnecessary_widening_paths": list(precision_metrics.get("unnecessary_widening_paths", []))
        if isinstance(precision_metrics.get("unnecessary_widening_paths"), list)
        else [],
        "selected_doc_count": max(
            int(packet_summary.get("selected_doc_count", 0) or 0),
            supplemented_doc_count,
        ),
        "selected_test_count": int(packet_summary.get("selected_test_count", 0) or 0),
        "selected_command_count": int(packet_summary.get("selected_command_count", 0) or 0),
        "strict_gate_command_count": int(packet_summary.get("strict_gate_command_count", 0) or 0),
        "effective_estimated_tokens": int(token_breakdown.get("effective_estimated_tokens", 0) or 0),
        "effective_token_basis": str(token_breakdown.get("effective_token_basis", "")).strip() or "codex_prompt_bundle",
        "codex_prompt_estimated_tokens": int(token_breakdown.get("codex_prompt_estimated_tokens", 0) or 0),
        "total_payload_estimated_tokens": int(token_breakdown.get("total_payload_estimated_tokens", 0) or 0),
        "runtime_contract_estimated_tokens": int(token_breakdown.get("runtime_contract_estimated_tokens", 0) or 0),
        "operator_diag_estimated_tokens": int(token_breakdown.get("operator_diag_estimated_tokens", 0) or 0),
        "prompt_artifact_tokens": dict(token_breakdown.get("prompt_artifact_tokens", {}))
        if isinstance(token_breakdown.get("prompt_artifact_tokens"), Mapping)
        else {},
        "runtime_contract_artifact_tokens": dict(token_breakdown.get("runtime_contract_artifact_tokens", {}))
        if isinstance(token_breakdown.get("runtime_contract_artifact_tokens"), Mapping)
        else {},
        "operator_diag_artifact_tokens": dict(token_breakdown.get("operator_diag_artifact_tokens", {}))
        if isinstance(token_breakdown.get("operator_diag_artifact_tokens"), Mapping)
        else {},
        "selector_diagnostics": dict(adaptive_escalation.get("benchmark_selector_diagnostics", {}))
        if isinstance(adaptive_escalation.get("benchmark_selector_diagnostics"), Mapping)
        else {},
        "adaptive_escalation": adaptive_escalation,
        "validation_success_proxy": 1.0 if not critical_path_misses and expectation_ok else 0.0,
        "full_scan": full_scan,
        "orchestration": decision_summary,
        "timing_trace": timing_trace,
    }


def _architecture_expectation_result(
    *,
    payload: Mapping[str, Any],
    expect_spec: Mapping[str, Any],
) -> tuple[bool, dict[str, Any]]:
    coverage = dict(payload.get("coverage", {})) if isinstance(payload.get("coverage"), Mapping) else {}
    execution_hint = dict(payload.get("execution_hint", {})) if isinstance(payload.get("execution_hint"), Mapping) else {}
    authority_graph = dict(payload.get("authority_graph", {})) if isinstance(payload.get("authority_graph"), Mapping) else {}
    pseudo_timing = {
        "metadata": {
            "resolved": bool(payload.get("resolved")),
            "confidence_tier": str(coverage.get("confidence_tier", "")).strip(),
            "full_scan_recommended": bool(payload.get("full_scan_recommended")),
            "contract_touchpoint_count": int(payload.get("contract_touchpoint_count", 0) or 0),
            "execution_hint_mode": str(execution_hint.get("mode", "")).strip(),
            "risk_tier": str(execution_hint.get("risk_tier", "")).strip(),
            "authority_graph_edge_count": int(
                dict(authority_graph.get("counts", {})).get("edges", 0) or 0
            )
            if isinstance(authority_graph.get("counts"), Mapping)
            else 0,
        }
    }
    return store._architecture_timing_satisfies_evaluation_expectations(  # noqa: SLF001
        pseudo_timing,
        expect_spec,
    )


def _architecture_result(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    changed_paths = [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
    existing_paths = _existing_repo_paths(repo_root=repo_root, paths=changed_paths)
    if _is_repo_scan_baseline_mode(normalized_mode):
        started_at = time.perf_counter()
        full_scan = store._full_scan_guidance(  # noqa: SLF001
            repo_root=repo_root,
            reason="benchmark_architecture_repo_scan_baseline",
            query=str(scenario.get("prompt", "")).strip(),
            changed_paths=existing_paths,
            perform_scan=True,
            result_limit=12,
        )
        duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
        latency_fields = _latency_measurement_fields(latency_ms=duration_ms, timing_trace={})
        observed_paths = [
            str(row.get("path", "")).strip()
            for row in full_scan.get("results", [])
            if isinstance(full_scan.get("results"), list) and isinstance(row, Mapping) and str(row.get("path", "")).strip()
        ]
        required_path_recall, required_path_misses = _path_recall(
            required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
            observed_paths=observed_paths,
        )
        precision_metrics = _precision_metrics(
            required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
            supporting_paths=_scenario_supporting_paths(scenario),
            observed_paths=observed_paths,
            expected_write_paths=[],
            candidate_write_paths=[],
        )
        full_scan_bytes = len(json.dumps(full_scan, sort_keys=True, ensure_ascii=False).encode("utf-8"))
        return {
            "kind": "architecture",
            "mode": normalized_mode,
            "packet_source": "architecture_repo_scan_baseline",
            "latency_ms": duration_ms,
            "instrumented_reasoning_duration_ms": float(
                latency_fields.get("instrumented_reasoning_duration_ms", 0.0) or 0.0
            ),
            "uninstrumented_overhead_ms": float(latency_fields.get("uninstrumented_overhead_ms", 0.0) or 0.0),
            "dossier": {},
            "expectation_ok": False,
            "expectation_details": {
                "baseline_mode": "repo_scan_only",
                "note": "Raw repo scan baseline does not produce an architecture dossier; compare Odylith dossier quality against this repo-scan-only control.",
            },
            "required_path_recall": required_path_recall,
            "required_path_misses": required_path_misses,
            "critical_path_misses": required_path_misses,
            "observed_paths": observed_paths[:12],
            "observed_path_count": int(precision_metrics.get("observed_path_count", 0) or 0),
            "required_path_precision": float(precision_metrics.get("required_path_precision", 0.0) or 0.0),
            "hallucinated_surface_count": int(precision_metrics.get("hallucinated_surface_count", 0) or 0),
            "hallucinated_surface_rate": float(precision_metrics.get("hallucinated_surface_rate", 0.0) or 0.0),
            "hallucinated_surfaces": list(precision_metrics.get("hallucinated_surfaces", []))
            if isinstance(precision_metrics.get("hallucinated_surfaces"), list)
            else [],
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "unnecessary_widening_paths": [],
            "selected_doc_count": 0,
            "selected_test_count": 0,
            "selected_command_count": 0,
            "strict_gate_command_count": 0,
            "effective_estimated_tokens": max(1, full_scan_bytes // 4),
            "effective_token_basis": "codex_prompt_bundle",
            "codex_prompt_estimated_tokens": max(1, full_scan_bytes // 4),
            "total_payload_estimated_tokens": max(1, full_scan_bytes // 4),
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {"full_scan": max(1, full_scan_bytes // 4)},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "selector_diagnostics": {},
            "architecture_compaction_applied": False,
            "adaptive_escalation": {
                "stage": "full_scan_fallback",
                "initial_source": _REPO_SCAN_BASELINE_MODE,
                "final_source": _REPO_SCAN_BASELINE_MODE,
                "auto_escalated": False,
                "reasons": [],
            },
            "validation_success_proxy": 1.0 if not required_path_misses else 0.0,
            "full_scan": full_scan,
            "orchestration": {
                "native_mode": "local_only",
                "mode": "local_only",
                "delegate": False,
                "leaf_count": 0,
                "native_leaf_count": 0,
                "parallel_safety": "local_only",
                "manual_review_recommended": True,
                "clamped_no_fanout": _is_no_fanout_mode(normalized_mode),
                "local_only_reasons": ["baseline_repo_scan_only"],
            },
        }
    if _is_raw_agent_baseline_mode(normalized_mode):
        raw_prompt = _raw_prompt_bundle(scenario=scenario)
        raw_prompt_tokens = _estimate_json_tokens(raw_prompt)
        observed_paths = _raw_prompt_visible_paths(repo_root=repo_root, raw_prompt=raw_prompt)
        required_path_recall, required_path_misses = _path_recall(
            required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
            observed_paths=observed_paths,
        )
        _critical_recall, critical_path_misses = _path_recall(
            required_paths=[str(token).strip() for token in scenario.get("critical_paths", []) if str(token).strip()],
            observed_paths=observed_paths,
        )
        precision_metrics = _precision_metrics(
            required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
            supporting_paths=_scenario_supporting_paths(scenario),
            observed_paths=observed_paths,
            expected_write_paths=[],
            candidate_write_paths=[],
        )
        return {
            "kind": "architecture",
            "mode": normalized_mode,
            "packet_source": "architecture_raw_agent_baseline",
            "latency_ms": 0.0,
            "instrumented_reasoning_duration_ms": 0.0,
            "uninstrumented_overhead_ms": 0.0,
            "dossier": {},
            "expectation_ok": False,
            "expectation_details": {
                "baseline_mode": "raw_agent_only",
                "note": "Raw agent baseline does not produce an architecture dossier or repo-scan grounding; compare Odylith dossier quality against this prompt-only control.",
            },
            "required_path_recall": required_path_recall,
            "required_path_misses": required_path_misses,
            "critical_path_misses": critical_path_misses,
            "observed_paths": observed_paths[:12],
            "observed_path_count": int(precision_metrics.get("observed_path_count", 0) or 0),
            "required_path_precision": float(precision_metrics.get("required_path_precision", 0.0) or 0.0),
            "hallucinated_surface_count": int(precision_metrics.get("hallucinated_surface_count", 0) or 0),
            "hallucinated_surface_rate": float(precision_metrics.get("hallucinated_surface_rate", 0.0) or 0.0),
            "hallucinated_surfaces": list(precision_metrics.get("hallucinated_surfaces", []))
            if isinstance(precision_metrics.get("hallucinated_surfaces"), list)
            else [],
            "expected_write_path_count": 0,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 1.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "unnecessary_widening_paths": [],
            "selected_doc_count": 0,
            "selected_test_count": 0,
            "selected_command_count": 0,
            "strict_gate_command_count": 0,
            "effective_estimated_tokens": raw_prompt_tokens,
            "effective_token_basis": "codex_prompt_bundle",
            "codex_prompt_estimated_tokens": raw_prompt_tokens,
            "total_payload_estimated_tokens": raw_prompt_tokens,
            "runtime_contract_estimated_tokens": 0,
            "operator_diag_estimated_tokens": 0,
            "prompt_artifact_tokens": {"raw_prompt": raw_prompt_tokens},
            "runtime_contract_artifact_tokens": {},
            "operator_diag_artifact_tokens": {},
            "selector_diagnostics": {},
            "architecture_compaction_applied": False,
            "adaptive_escalation": {
                "stage": "raw_agent_baseline",
                "initial_source": _RAW_AGENT_BASELINE_MODE,
                "final_source": _RAW_AGENT_BASELINE_MODE,
                "auto_escalated": False,
                "reasons": [],
            },
            "validation_success_proxy": 0.0,
            "full_scan": {
                "performed": False,
                "terms": [],
                "roots": [],
                "commands": [],
                "results": [],
                "reason": "raw_agent_baseline",
                "reason_message": "Prompt-only raw baseline does not precompute repo scan grounding.",
                "changed_paths": list(existing_paths),
            },
            "orchestration": _raw_agent_orchestration_summary(),
            "timing_trace": {},
        }
    timing_before = _recent_reasoning_timing_index(repo_root=repo_root)
    started_at = time.perf_counter()
    with _odylith_enabled_override(True):
        payload = store.build_architecture_audit(
            repo_root=repo_root,
            changed_paths=existing_paths,
            runtime_mode="local",
            detail_level="packet",
        )
    duration_ms = round((time.perf_counter() - started_at) * 1000.0, 3)
    timing_trace = _timing_trace(
        repo_root=repo_root,
        before=timing_before,
        operations=("architecture",),
    )
    expectation_ok, expectation_details = _architecture_expectation_result(
        payload=payload,
        expect_spec=dict(scenario.get("expect", {})),
    )
    observed_paths = _dedupe_strings(
        [
            *existing_paths,
            *(
                str(token).strip()
                for token in payload.get("required_reads", [])
                if isinstance(payload.get("required_reads"), list) and str(token).strip()
            ),
            *(
                str(row.get("path", "")).strip()
                for row in payload.get("linked_components", [])
                if isinstance(payload.get("linked_components"), list) and isinstance(row, Mapping) and str(row.get("path", "")).strip()
            ),
            *(
                str(row.get("source_mmd", "")).strip()
                for row in payload.get("linked_diagrams", [])
                if isinstance(payload.get("linked_diagrams"), list) and isinstance(row, Mapping) and str(row.get("source_mmd", "")).strip()
            ),
            *(
                str(row.get("path", "")).strip()
                for row in payload.get("linked_diagrams", [])
                if isinstance(payload.get("linked_diagrams"), list) and isinstance(row, Mapping) and str(row.get("path", "")).strip()
            ),
        ]
    )
    required_path_recall, required_path_misses = _path_recall(
        required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
        observed_paths=observed_paths,
    )
    request_payload = {
        "prompt": str(scenario.get("prompt", "")).strip(),
        "acceptance_criteria": [str(token).strip() for token in scenario.get("acceptance_criteria", []) if str(token).strip()],
        "candidate_paths": existing_paths,
        "workstreams": [],
        "components": [
            str(row.get("component_id", "")).strip()
            for row in payload.get("linked_components", [])
            if isinstance(payload.get("linked_components"), list) and isinstance(row, Mapping) and str(row.get("component_id", "")).strip()
        ],
        "validation_commands": [],
        "accuracy_preference": "accuracy",
        "repo_work": True,
        "task_kind": "analysis",
        "phase": "analysis",
        "needs_write": False,
        "correctness_critical": False,
        "evidence_cone_grounded": not bool(payload.get("full_scan_recommended")),
        "architecture_audit": dict(payload),
    }
    decision_summary = _safe_orchestration_summary(
        request_payload=request_payload,
        repo_root=repo_root,
        mode=normalized_mode,
    )
    precision_metrics = _precision_metrics(
        required_paths=[str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()],
        supporting_paths=_scenario_supporting_paths(scenario),
        observed_paths=observed_paths,
        expected_write_paths=[],
        candidate_write_paths=[],
    )
    compact_payload = store._compact_packet_level_architecture_audit(payload)  # noqa: SLF001
    architecture_compaction_applied = True
    encoded = json.dumps(compact_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    latency_fields = _latency_measurement_fields(latency_ms=duration_ms, timing_trace=timing_trace)
    return {
        "kind": "architecture",
        "mode": normalized_mode,
        "packet_source": "architecture_dossier",
        "latency_ms": duration_ms,
        "instrumented_reasoning_duration_ms": float(
            latency_fields.get("instrumented_reasoning_duration_ms", 0.0) or 0.0
        ),
        "uninstrumented_overhead_ms": float(latency_fields.get("uninstrumented_overhead_ms", 0.0) or 0.0),
        "dossier": compact_payload,
        "expectation_ok": expectation_ok,
        "expectation_details": expectation_details,
        "required_path_recall": required_path_recall,
        "required_path_misses": required_path_misses,
        "critical_path_misses": required_path_misses,
        "observed_paths": observed_paths[:12],
        "observed_path_count": int(precision_metrics.get("observed_path_count", 0) or 0),
        "required_path_precision": float(precision_metrics.get("required_path_precision", 0.0) or 0.0),
        "hallucinated_surface_count": int(precision_metrics.get("hallucinated_surface_count", 0) or 0),
        "hallucinated_surface_rate": float(precision_metrics.get("hallucinated_surface_rate", 0.0) or 0.0),
        "hallucinated_surfaces": list(precision_metrics.get("hallucinated_surfaces", []))
        if isinstance(precision_metrics.get("hallucinated_surfaces"), list)
        else [],
        "expected_write_path_count": 0,
        "candidate_write_path_count": 0,
        "candidate_write_paths": [],
        "write_surface_precision": 1.0,
        "unnecessary_widening_count": 0,
        "unnecessary_widening_rate": 0.0,
        "unnecessary_widening_paths": [],
        "effective_estimated_tokens": max(1, len(encoded) // 4),
        "effective_token_basis": "codex_prompt_bundle",
        "codex_prompt_estimated_tokens": max(1, len(encoded) // 4),
        "total_payload_estimated_tokens": max(1, len(encoded) // 4),
        "runtime_contract_estimated_tokens": 0,
        "operator_diag_estimated_tokens": 0,
        "prompt_artifact_tokens": {"architecture_audit": max(1, len(encoded) // 4)},
        "runtime_contract_artifact_tokens": {},
        "operator_diag_artifact_tokens": {},
        "selector_diagnostics": {},
        "architecture_compaction_applied": architecture_compaction_applied,
        "adaptive_escalation": {
            "stage": "architecture_packet",
            "initial_source": "architecture_audit",
            "final_source": "architecture_audit",
            "auto_escalated": False,
            "reasons": [],
        },
        "validation_success_proxy": 1.0 if expectation_ok else 0.0,
        "full_scan": dict(payload.get("fallback_scan", {})) if isinstance(payload.get("fallback_scan"), Mapping) else {},
        "orchestration": decision_summary,
        "timing_trace": timing_trace,
    }


def _is_live_public_mode(mode: str) -> bool:
    return _normalize_mode(mode) in {_ODYLITH_ON_MODE, _RAW_AGENT_BASELINE_MODE}


def _benchmark_profile_uses_live_public_modes(profile: str) -> bool:
    return str(profile).strip() in {BENCHMARK_PROFILE_QUICK, BENCHMARK_PROFILE_PROOF}


def _profile_uses_live_public_modes_for_selection(
    *,
    profile: str,
    selected_families: Sequence[str],
) -> bool:
    families = {str(token).strip() for token in selected_families if str(token).strip()}
    if str(profile).strip() == BENCHMARK_PROFILE_QUICK and families and families.issubset(_LOCAL_ONLY_QUICK_FAMILIES):
        return False
    return _benchmark_profile_uses_live_public_modes(profile)


def _cache_profiles_for_selection(
    *,
    profile: str,
    selected_families: Sequence[str],
    cache_profiles: Sequence[str],
    explicit_cache_profile_selection: bool,
) -> list[str]:
    families = {str(token).strip() for token in selected_families if str(token).strip()}
    if (
        not explicit_cache_profile_selection
        and str(profile).strip() == BENCHMARK_PROFILE_QUICK
        and families
        and families.issubset(_LOCAL_ONLY_QUICK_FAMILIES)
    ):
        return ["cold"]
    return [str(token).strip() for token in cache_profiles if str(token).strip()]


def _dedupe_path_strings(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    rows: list[str] = []
    for raw in values:
        token = str(raw or "").strip().replace("\\", "/")
        if not token:
            continue
        while token.startswith("./"):
            token = token[2:]
        normalized = Path(token).as_posix()
        if normalized in seen:
            continue
        seen.add(normalized)
        rows.append(normalized)
    return rows


def _existing_repo_file_paths(*, repo_root: Path, candidates: Sequence[str]) -> list[str]:
    root = Path(repo_root).resolve()
    rows: list[str] = []
    for raw in candidates:
        token = str(raw or "").strip()
        if not token:
            continue
        candidate = (root / token).resolve()
        with contextlib.suppress(ValueError):
            if candidate.is_file():
                rows.append(candidate.relative_to(root).as_posix())
    return _dedupe_path_strings(rows)


def _validation_command_file_paths(*, repo_root: Path, commands: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for raw in commands:
        command = str(raw or "").strip()
        if not command:
            continue
        with contextlib.suppress(ValueError):
            tokens = shlex.split(command)
            for token in tokens:
                if token.startswith("-") or "=" in token:
                    continue
                normalized_token = token.rstrip(",:;])}")
                if "::" in normalized_token:
                    normalized_token = normalized_token.split("::", 1)[0]
                rows.append(normalized_token)
    return _existing_repo_file_paths(repo_root=repo_root, candidates=rows)


def _source_local_cli_snapshot_paths(*, repo_root: Path, commands: Sequence[str]) -> list[str]:
    if not any(re.match(r"^(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)*odylith(?:\s|$)", str(raw or "").strip()) for raw in commands):
        return []
    root = Path(repo_root).resolve()
    candidate = root / "src" / "odylith" / "cli.py"
    if not candidate.is_file():
        return []
    return [candidate.relative_to(root).as_posix()]


def _path_expression_literal(node: ast.AST) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return str(node.value or "").strip().replace("\\", "/")
    if isinstance(node, ast.Name):
        return ""
    if isinstance(node, ast.Call):
        func = node.func
        func_name = ""
        if isinstance(func, ast.Name):
            func_name = str(func.id or "").strip()
        elif isinstance(func, ast.Attribute):
            func_name = str(func.attr or "").strip()
        if func_name == "Path" and node.args:
            seed = _path_expression_literal(node.args[0])
            return seed
        return ""
    if not isinstance(node, ast.BinOp) or not isinstance(node.op, ast.Div):
        return ""
    left = _path_expression_literal(node.left)
    right = _path_expression_literal(node.right)
    if not right:
        return left
    if not left:
        return right
    return f"{left.rstrip('/')}/{right.lstrip('/')}"


def _validation_companion_file_paths(*, repo_root: Path, validation_paths: Sequence[str]) -> list[str]:
    root = Path(repo_root).resolve()
    rows: list[str] = []
    validation_names = {Path(str(raw_path or "").strip()).name for raw_path in validation_paths if str(raw_path or "").strip()}
    if validation_names.intersection({"test_odylith_benchmark_runner.py", "test_odylith_benchmark_graphs.py"}):
        corpus_path = store.optimization_evaluation_corpus_path(repo_root=root)
        with contextlib.suppress(ValueError):
            rows.append(corpus_path.relative_to(root).as_posix())
        rows.append("src/odylith/bundle/assets/odylith/runtime/source/optimization-evaluation-corpus.v1.json")
    for raw_path in validation_paths:
        path = str(raw_path or "").strip()
        candidate = root / path
        if not candidate.is_file() or candidate.suffix != ".py":
            continue
        try:
            tree = ast.parse(candidate.read_text(encoding="utf-8"))
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        literal_candidates: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            token = str(node.value or "").strip().replace("\\", "/")
            if (
                not token
                or len(token) > 200
                or "://" in token
                or "\n" in token
                or "\r" in token
            ):
                continue
            suffix = Path(token).suffix.lower()
            if suffix not in _VALIDATION_COMPANION_FILE_SUFFIXES:
                continue
            literal_candidates.append(token)
        for node in ast.walk(tree):
            token = _path_expression_literal(node)
            if (
                not token
                or len(token) > 200
                or "://" in token
                or "\n" in token
                or "\r" in token
            ):
                continue
            suffix = Path(token).suffix.lower()
            if suffix not in _VALIDATION_COMPANION_FILE_SUFFIXES:
                continue
            literal_candidates.append(token)
        rows.extend(_existing_repo_file_paths(repo_root=root, candidates=literal_candidates))
        rows.extend(
            target
            for target in (
                _repo_python_module_path(repo_root=root, module_name=module_name)
                for module_name in _imported_python_module_candidates(repo_root=root, path=path)
            )
            if target
        )
    return _dedupe_path_strings(rows)


def _dirty_repo_paths(repo_root: Path) -> list[str]:
    root = Path(repo_root).resolve()
    rows: list[str] = []
    for command in (
        ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", "HEAD", "--"],
        ["git", "ls-files", "--others", "--exclude-standard"],
    ):
        completed = subprocess.run(
            command,
            cwd=str(root),
            text=True,
            capture_output=True,
            check=False,
        )
        if int(completed.returncode or 0) != 0:
            continue
        rows.extend(str(line).strip() for line in str(completed.stdout or "").splitlines() if str(line).strip())
    return _dedupe_path_strings(rows)


def _expand_same_package_dirty_paths(*, repo_root: Path, snapshot_paths: Sequence[str]) -> list[str]:
    base_paths = _dedupe_path_strings(snapshot_paths)
    package_dirs = {
        Path(path).parent.as_posix()
        for path in base_paths
        if str(path).endswith(".py") and Path(path).as_posix().startswith("src/")
    }
    if not package_dirs:
        return base_paths
    generic_name_tokens = {
        "odylith",
        "runtime",
        "render",
        "test",
        "tests",
        "unit",
        "integration",
        "src",
        "current",
        "spec",
    }

    def _path_name_tokens(path: str) -> set[str]:
        stem = Path(path).stem.lower()
        return {
            token
            for token in re.split(r"[^a-z0-9]+", stem)
            if len(token) >= 3 and token not in generic_name_tokens
        }

    seed_tokens_by_dir: dict[str, list[set[str]]] = {}
    for path in base_paths:
        candidate = Path(path)
        if candidate.suffix != ".py":
            continue
        parent = candidate.parent.as_posix()
        if parent not in package_dirs:
            continue
        seed_tokens = _path_name_tokens(candidate.as_posix())
        if seed_tokens:
            seed_tokens_by_dir.setdefault(parent, []).append(seed_tokens)

    expanded: list[str] = list(base_paths)
    candidate_rows: dict[str, list[tuple[int, str]]] = {}
    for dirty_path in _dirty_repo_paths(repo_root):
        candidate = Path(dirty_path)
        if candidate.suffix != ".py":
            continue
        parent = candidate.parent.as_posix()
        if parent not in package_dirs or candidate.as_posix() in base_paths:
            continue
        candidate_tokens = _path_name_tokens(candidate.as_posix())
        if not candidate_tokens:
            continue
        relevance = max(
            (
                len(candidate_tokens.intersection(seed_tokens))
                for seed_tokens in seed_tokens_by_dir.get(parent, [])
                if seed_tokens
            ),
            default=0,
        )
        if relevance < 2:
            continue
        candidate_rows.setdefault(parent, []).append((relevance, candidate.as_posix()))
    for parent in sorted(candidate_rows):
        for _score, path in sorted(candidate_rows[parent], key=lambda item: (-item[0], item[1]))[:4]:
            expanded.append(path)
    return _dedupe_path_strings(expanded)


def _python_module_name_from_repo_path(path: str) -> str:
    candidate = Path(str(path or "").strip())
    if candidate.suffix != ".py":
        return ""
    parts = candidate.with_suffix("").parts
    if not parts:
        return ""
    if parts[0] == "src":
        parts = parts[1:]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(str(token).strip() for token in parts if str(token).strip())


def _repo_python_module_path(*, repo_root: Path, module_name: str) -> str:
    token = str(module_name or "").strip()
    if not token:
        return ""
    root = Path(repo_root).resolve()
    module_path = root / "src" / Path(*token.split("."))
    file_candidate = module_path.with_suffix(".py")
    if file_candidate.is_file():
        return file_candidate.relative_to(root).as_posix()
    package_init = module_path / "__init__.py"
    if package_init.is_file():
        return package_init.relative_to(root).as_posix()
    return ""


def _imported_python_module_candidates(*, repo_root: Path, path: str) -> list[str]:
    root = Path(repo_root).resolve()
    candidate = root / str(path or "").strip()
    if not candidate.is_file() or candidate.suffix != ".py":
        return []
    try:
        tree = ast.parse(candidate.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return []

    current_module = _python_module_name_from_repo_path(path)
    current_package_parts = current_module.split(".")[:-1] if current_module else []
    rows: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                token = str(getattr(alias, "name", "") or "").strip()
                if token:
                    rows.append(token)
            continue
        if not isinstance(node, ast.ImportFrom):
            continue
        base_module = str(node.module or "").strip()
        if int(getattr(node, "level", 0) or 0) > 0:
            keep = max(0, len(current_package_parts) - int(getattr(node, "level", 0) or 0) + 1)
            anchor_parts = current_package_parts[:keep]
        else:
            anchor_parts = []
        base_parts = [*anchor_parts, *(base_module.split(".") if base_module else [])]
        if base_parts:
            rows.append(".".join(base_parts))
        for alias in node.names:
            alias_name = str(getattr(alias, "name", "") or "").strip()
            if not alias_name or alias_name == "*":
                continue
            if base_parts:
                rows.append(".".join([*base_parts, alias_name]))
    return _dedupe_path_strings(rows)


def _expand_dirty_import_dependency_paths(*, repo_root: Path, snapshot_paths: Sequence[str]) -> list[str]:
    base_paths = _dedupe_path_strings(snapshot_paths)
    dirty_python_paths = {
        path
        for path in _dirty_repo_paths(repo_root)
        if Path(path).suffix == ".py" and Path(path).as_posix().startswith(("src/", "tests/"))
    }
    if not dirty_python_paths:
        return base_paths

    expanded = list(base_paths)
    pending = [
        path
        for path in base_paths
        if Path(path).suffix == ".py"
    ]
    seen_paths = set(expanded)
    scanned_paths: set[str] = set()
    scan_budget = 256

    while pending and scan_budget > 0:
        current = pending.pop()
        if current in scanned_paths:
            continue
        scanned_paths.add(current)
        scan_budget -= 1
        for module_name in _imported_python_module_candidates(repo_root=repo_root, path=current):
            target = _repo_python_module_path(repo_root=repo_root, module_name=module_name)
            if not target:
                continue
            if target not in scanned_paths:
                pending.append(target)
            if target not in dirty_python_paths or target in seen_paths:
                continue
            seen_paths.add(target)
            expanded.append(target)
    return _dedupe_path_strings(expanded)


def _expand_governance_validator_snapshot_paths(*, repo_root: Path, snapshot_paths: Sequence[str]) -> list[str]:
    base_paths = _dedupe_path_strings(snapshot_paths)
    if not base_paths:
        return base_paths
    base_path_set = set(base_paths)
    dirty_paths = _dirty_repo_paths(repo_root)
    if not dirty_paths:
        return base_paths

    expanded = list(base_paths)

    if "odylith/registry/source/component_registry.v1.json" in base_path_set:
        for path in dirty_paths:
            token = str(path or "").strip()
            if not token:
                continue
            if token.startswith("odylith/registry/source/components/") or token.startswith("odylith/radar/source/ideas/"):
                expanded.append(token)
                continue
            if token == "odylith/atlas/source/catalog/diagrams.v1.json":
                expanded.append(token)

    if any(
        token == "odylith/atlas/source/catalog/diagrams.v1.json"
        or (token.startswith("odylith/atlas/source/") and Path(token).suffix.lower() == ".mmd")
        for token in base_path_set
    ):
        for path in dirty_paths:
            token = str(path or "").strip()
            if not token or not token.startswith("odylith/atlas/source/"):
                continue
            if Path(token).suffix.lower() not in {".json", ".mmd"}:
                continue
            expanded.append(token)

    return _dedupe_path_strings(expanded)


def _sync_validator_requested(commands: Sequence[str]) -> bool:
    for raw_command in commands:
        token = str(raw_command or "").strip()
        if not token:
            continue
        if re.match(r"^(?:[A-Za-z_][A-Za-z0-9_]*=[^\s]+\s+)*odylith\s+sync(?:\s|$)", token):
            return True
    return False


def _expand_sync_validator_snapshot_paths(
    *,
    repo_root: Path,
    snapshot_paths: Sequence[str],
    validation_commands: Sequence[str],
) -> list[str]:
    base_paths = _dedupe_path_strings(snapshot_paths)
    if not _sync_validator_requested(validation_commands):
        return base_paths

    root = Path(repo_root).resolve()
    expanded = list(base_paths)
    expanded.extend(
        _existing_repo_file_paths(
            repo_root=root,
            candidates=[
                "odylith/radar/source/INDEX.md",
                "odylith/technical-plans/INDEX.md",
                "odylith/registry/source/component_registry.v1.json",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/runtime/delivery_intelligence.v4.json",
                "odylith/casebook/bugs/INDEX.md",
            ],
        )
    )
    for path in _dirty_repo_paths(root):
        token = str(path or "").strip()
        if not token:
            continue
        if token.startswith(
            (
                "odylith/radar/source/ideas/",
                "odylith/technical-plans/in-progress/",
                "odylith/registry/source/components/",
            )
        ):
            expanded.append(token)
    return _dedupe_path_strings(expanded)


def _atlas_render_check_requested(commands: Sequence[str]) -> bool:
    for raw_command in commands:
        token = str(raw_command or "").strip()
        if not token:
            continue
        if "atlas render" in token and "--check-only" in token:
            return True
    return False


def _expand_atlas_catalog_reference_snapshot_paths(
    *,
    repo_root: Path,
    snapshot_paths: Sequence[str],
    validation_commands: Sequence[str],
) -> list[str]:
    base_paths = _dedupe_path_strings(snapshot_paths)
    if "odylith/atlas/source/catalog/diagrams.v1.json" not in set(base_paths):
        return base_paths
    root = Path(repo_root).resolve()
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return base_paths
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return base_paths
    diagrams = payload.get("diagrams", [])
    if not isinstance(diagrams, list):
        return base_paths

    selected_mmds = {
        token
        for token in base_paths
        if token.startswith("odylith/atlas/source/") and Path(token).suffix.lower() == ".mmd"
    }
    atlas_render_check = _atlas_render_check_requested(validation_commands)
    reference_candidates: list[str] = []
    for raw_row in diagrams:
        if not isinstance(raw_row, Mapping):
            continue
        source_mmd = str(raw_row.get("source_mmd", "") or "").strip()
        if atlas_render_check:
            for key in ("source_mmd", "source_svg", "source_png"):
                token = str(raw_row.get(key, "") or "").strip()
                if token:
                    reference_candidates.append(token)
        if selected_mmds and source_mmd not in selected_mmds:
            continue
        for key in ("change_watch_paths", "related_plans", "related_docs", "related_code", "related_backlog"):
            value = raw_row.get(key)
            if not isinstance(value, list):
                continue
            reference_candidates.extend(str(token).strip() for token in value if str(token).strip())
    companion_paths = _existing_repo_file_paths(repo_root=root, candidates=reference_candidates)
    return _dedupe_path_strings([*base_paths, *companion_paths])


def _prompt_payload_snapshot_paths(prompt_payload: Mapping[str, Any] | None) -> list[str]:
    payload = dict(prompt_payload or {})
    context_packet = dict(payload.get("context_packet", {})) if isinstance(payload.get("context_packet"), Mapping) else {}
    anchors = dict(context_packet.get("anchors", {})) if isinstance(context_packet.get("anchors"), Mapping) else {}
    retrieval_plan = (
        dict(context_packet.get("retrieval_plan", {}))
        if isinstance(context_packet.get("retrieval_plan"), Mapping)
        else {}
    )
    architecture_audit = (
        dict(payload.get("architecture_audit", {}))
        if isinstance(payload.get("architecture_audit"), Mapping)
        else {}
    )
    rows: list[str] = []
    for value in (
        payload.get("changed_paths"),
        payload.get("docs"),
        payload.get("relevant_docs"),
        payload.get("implementation_anchors"),
        anchors.get("changed_paths"),
        anchors.get("explicit_paths"),
        retrieval_plan.get("selected_docs"),
        architecture_audit.get("changed_paths"),
        architecture_audit.get("required_reads"),
        architecture_audit.get("implementation_anchors"),
    ):
        if not isinstance(value, list):
            continue
        rows.extend(str(token).strip() for token in value if str(token).strip())
    return _dedupe_path_strings(rows)


def _live_workspace_snapshot_paths(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    prompt_payload: Mapping[str, Any] | None = None,
) -> list[str]:
    focused_local_checks = (
        [str(token).strip() for token in scenario.get("focused_local_checks", []) if str(token).strip()]
        if isinstance(scenario.get("focused_local_checks"), list)
        else []
    )
    validation_commands = (
        [str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()]
        if isinstance(scenario.get("validation_commands"), list)
        else []
    )
    snapshot_commands = _dedupe_strings([*validation_commands, *focused_local_checks])
    scenario_paths = _dedupe_path_strings(
        [
            *(
                [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
                if isinstance(scenario.get("changed_paths"), list)
                else []
            ),
            *(
                [str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()]
                if isinstance(scenario.get("required_paths"), list)
                else []
            ),
        ]
    )
    validation_paths = _validation_command_file_paths(
        repo_root=repo_root,
        commands=snapshot_commands,
    )
    source_local_cli_paths = _source_local_cli_snapshot_paths(
        repo_root=repo_root,
        commands=snapshot_commands,
    )
    validation_companion_paths = _validation_companion_file_paths(
        repo_root=repo_root,
        validation_paths=validation_paths,
    )
    prompt_paths = _existing_repo_file_paths(
        repo_root=repo_root,
        candidates=_prompt_payload_snapshot_paths(prompt_payload),
    )
    return _expand_dirty_import_dependency_paths(
        repo_root=repo_root,
        snapshot_paths=_expand_atlas_catalog_reference_snapshot_paths(
            repo_root=repo_root,
            validation_commands=validation_commands,
            snapshot_paths=_expand_governance_validator_snapshot_paths(
                repo_root=repo_root,
                snapshot_paths=_expand_sync_validator_snapshot_paths(
                    repo_root=repo_root,
                    validation_commands=validation_commands,
                    snapshot_paths=_expand_same_package_dirty_paths(
                        repo_root=repo_root,
                        snapshot_paths=[
                            *scenario_paths,
                            *validation_paths,
                            *source_local_cli_paths,
                            *validation_companion_paths,
                            *prompt_paths,
                        ],
                    ),
                ),
            ),
        ),
    )


def _prepare_live_scenario_request(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    benchmark_profile: str,
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    if not _is_live_public_mode(normalized_mode):
        raise ValueError(f"Unsupported live benchmark mode: {mode}")
    changed_paths = [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
    existing_paths = _existing_repo_paths(repo_root=repo_root, paths=changed_paths)
    if str(scenario.get("kind", "")).strip() == "architecture":
        prompt_payload: dict[str, Any] = {}
        packet_source = "raw_codex_cli"
        if normalized_mode == _ODYLITH_ON_MODE:
            with _odylith_enabled_override(True):
                audit_payload = store.build_architecture_audit(
                    repo_root=repo_root,
                    changed_paths=existing_paths,
                    runtime_mode="local",
                    detail_level="full",
                )
            prompt_payload = odylith_benchmark_prompt_payloads.supplement_live_prompt_payload(
                repo_root=repo_root,
                scenario=scenario,
                prompt_payload={
                    "architecture_audit": store._compact_packet_level_architecture_audit(audit_payload),  # noqa: SLF001
                },
                packet_source="architecture_dossier",
                changed_paths=existing_paths,
                full_payload=audit_payload,
            )
            packet_source = "architecture_dossier"
        return {
            "repo_root": repo_root,
            "scenario": dict(scenario),
            "mode": normalized_mode,
            "benchmark_profile": _normalize_benchmark_profile(benchmark_profile),
            "packet_source": packet_source,
            "prompt_payload": prompt_payload,
        }
    prompt_payload = {}
    packet_source = "raw_codex_cli"
    if normalized_mode == _ODYLITH_ON_MODE:
        packet_source, payload, _adaptive_escalation = _build_packet_payload(
            repo_root=repo_root,
            scenario=scenario,
            mode=normalized_mode,
            existing_paths=existing_paths,
            report_id=report_id,
            cache_profile=cache_profile,
            shard_index=shard_index,
            shard_count=shard_count,
        )
        payload = _apply_packet_fixture(payload=payload, scenario=scenario, packet_source=packet_source)
        prompt_keys = set(_PROMPT_PAYLOAD_KEYS)
        if not isinstance(payload.get("narrowing_guidance"), Mapping):
            prompt_keys.discard("narrowing_guidance")
        prompt_payload = _subset_payload(payload, keys=prompt_keys)
        prompt_payload = odylith_benchmark_prompt_payloads.supplement_live_prompt_payload(
            repo_root=repo_root,
            scenario=scenario,
            prompt_payload=prompt_payload,
            packet_source=packet_source,
            changed_paths=existing_paths,
            full_payload=payload,
        )
    return {
        "repo_root": repo_root,
        "scenario": dict(scenario),
        "mode": normalized_mode,
        "benchmark_profile": _normalize_benchmark_profile(benchmark_profile),
        "benchmark_session_namespace": _benchmark_session_namespace(
            scenario=scenario,
            mode=normalized_mode,
            report_id=report_id,
            cache_profile=cache_profile,
            shard_index=shard_index,
            shard_count=shard_count,
        ),
        "packet_source": packet_source,
        "prompt_payload": prompt_payload,
        "packet_summary": (
            store._packet_summary_from_bootstrap_payload(payload)  # noqa: SLF001
            if normalized_mode == _ODYLITH_ON_MODE
            else {}
        ),
    }


def _run_prepared_live_scenario(prepared_request: Mapping[str, Any]) -> dict[str, Any]:
    benchmark_profile = _normalize_benchmark_profile(str(prepared_request.get("benchmark_profile", "")).strip())
    if benchmark_profile == BENCHMARK_PROFILE_DIAGNOSTIC:
        raise RuntimeError("diagnostic benchmark attempted live Codex execution")
    result = odylith_benchmark_live_execution.run_live_scenario(
        repo_root=Path(prepared_request.get("repo_root", ".")),
        scenario=dict(prepared_request.get("scenario", {})),
        mode=str(prepared_request.get("mode", "")).strip(),
        benchmark_profile=benchmark_profile,
        benchmark_session_namespace=str(prepared_request.get("benchmark_session_namespace", "")).strip(),
        packet_source=str(prepared_request.get("packet_source", "")).strip() or "raw_codex_cli",
        prompt_payload=dict(prepared_request.get("prompt_payload", {}))
        if isinstance(prepared_request.get("prompt_payload"), Mapping)
        else {},
        packet_summary=dict(prepared_request.get("packet_summary", {}))
        if isinstance(prepared_request.get("packet_summary"), Mapping)
        else {},
        snapshot_paths=[
            str(token).strip()
            for token in prepared_request.get("snapshot_paths", [])
            if str(token).strip()
        ]
        if isinstance(prepared_request.get("snapshot_paths"), list)
        else None,
    )
    live_execution = dict(result.get("live_execution", {})) if isinstance(result.get("live_execution"), Mapping) else {}
    paired_modes = [
        str(token).strip()
        for token in prepared_request.get("paired_modes", [])
        if str(token).strip()
    ] if isinstance(prepared_request.get("paired_modes"), list) else []
    live_execution.update(
        {
            "matched_pair_batch": bool(prepared_request.get("matched_pair_batch")),
            "matched_pair_batch_size": int(prepared_request.get("matched_pair_batch_size", 1) or 1),
            "matched_pair_modes": paired_modes,
            "latency_measurement_basis": (
                "matched_pair_contended_validated_task_cycle"
                if bool(prepared_request.get("matched_pair_batch"))
                else str(live_execution.get("latency_measurement_basis", "")).strip() or "validated_task_cycle"
            ),
        }
    )
    result["live_execution"] = live_execution
    return result


def _result_snapshot_overlay_paths(result: Mapping[str, Any]) -> list[str]:
    live_execution = dict(result.get("live_execution", {})) if isinstance(result.get("live_execution"), Mapping) else {}
    return [
        str(token).strip()
        for token in live_execution.get("effective_snapshot_paths", [])
        if isinstance(live_execution.get("effective_snapshot_paths"), list) and str(token).strip()
    ]


def _report_snapshot_overlay_paths(scenario_reports: Sequence[Mapping[str, Any]]) -> list[str]:
    return _dedupe_strings(
        [
            token
            for scenario_report in scenario_reports
            if isinstance(scenario_report, Mapping)
            for result in scenario_report.get("results", [])
            if isinstance(scenario_report.get("results"), list) and isinstance(result, Mapping)
            for token in _result_snapshot_overlay_paths(result)
        ]
    )


def _run_live_scenario_batch(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    modes: Sequence[str],
    benchmark_profile: str,
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> dict[str, dict[str, Any]]:
    live_modes = [_normalize_mode(str(token).strip()) for token in modes if _is_live_public_mode(str(token).strip())]
    ordered_live_modes = list(dict.fromkeys(live_modes))
    prepared_requests: list[dict[str, Any]] = []
    request_by_mode: dict[str, dict[str, Any]] = {}
    results: dict[str, dict[str, Any]] = {}
    for mode in ordered_live_modes:
        try:
            request = _prepare_live_scenario_request(
                repo_root=repo_root,
                scenario=scenario,
                mode=mode,
                benchmark_profile=benchmark_profile,
                report_id=report_id,
                cache_profile=cache_profile,
                shard_index=shard_index,
                shard_count=shard_count,
            )
        except Exception as exc:
            results[mode] = _scenario_exception_result(
                scenario=scenario,
                mode=mode,
                error=exc,
                live_runner=True,
            )
            continue
        prepared_requests.append(request)
        request_by_mode[mode] = request
    matched_pair_batch = len(prepared_requests) > 1
    paired_modes = [str(request.get("mode", "")).strip() for request in prepared_requests if str(request.get("mode", "")).strip()]
    for request in prepared_requests:
        request["matched_pair_batch"] = matched_pair_batch
        request["matched_pair_batch_size"] = len(prepared_requests)
        request["paired_modes"] = list(paired_modes)
    shared_snapshot_paths = _dedupe_path_strings(
        [
            path
            for request in prepared_requests
            for path in _live_workspace_snapshot_paths(
                repo_root=repo_root,
                scenario=dict(request.get("scenario", {})),
                prompt_payload=dict(request.get("prompt_payload", {}))
                if isinstance(request.get("prompt_payload"), Mapping)
                else {},
            )
        ]
    )
    for request in prepared_requests:
        request["snapshot_paths"] = list(shared_snapshot_paths)
    if not prepared_requests:
        return results
    if len(prepared_requests) == 1:
        only_request = prepared_requests[0]
        only_mode = str(only_request.get("mode", "")).strip()
        try:
            results[only_mode] = _run_prepared_live_scenario(only_request)
        except Exception as exc:
            results[only_mode] = _scenario_exception_result(
                scenario=scenario,
                mode=only_mode,
                error=exc,
                live_runner=True,
                packet_source=str(only_request.get("packet_source", "")).strip(),
            )
        return results
    with concurrent.futures.ThreadPoolExecutor(max_workers=min(_LIVE_MATCHED_PAIR_MAX_WORKERS, len(prepared_requests))) as executor:
        future_by_mode = {
            str(request.get("mode", "")).strip(): executor.submit(_run_prepared_live_scenario, request)
            for request in prepared_requests
        }
        for mode in ordered_live_modes:
            if mode in results:
                continue
            request = request_by_mode.get(mode, {})
            future = future_by_mode.get(mode)
            if future is None:
                results[mode] = _scenario_exception_result(
                    scenario=scenario,
                    mode=mode,
                    error="live benchmark batch did not schedule this mode",
                    live_runner=True,
                    packet_source=str(request.get("packet_source", "")).strip(),
                )
                continue
            try:
                results[mode] = future.result()
            except Exception as exc:
                results[mode] = _scenario_exception_result(
                    scenario=scenario,
                    mode=mode,
                    error=exc,
                    live_runner=True,
                    packet_source=str(request.get("packet_source", "")).strip(),
                )
    return results


def _run_scenario_mode(
    *,
    repo_root: Path,
    scenario: Mapping[str, Any],
    mode: str,
    benchmark_profile: str = BENCHMARK_PROFILE_PROOF,
    report_id: str = "",
    cache_profile: str = "",
    shard_index: int = 1,
    shard_count: int = 1,
) -> dict[str, Any]:
    normalized_mode = _normalize_mode(mode)
    if (
        _benchmark_profile_uses_live_public_modes(benchmark_profile)
        and odylith_benchmark_live_execution.run_live_scenario
        and _is_live_public_mode(normalized_mode)
    ):
        prepared_request = _prepare_live_scenario_request(
            repo_root=repo_root,
            scenario=scenario,
            mode=normalized_mode,
            benchmark_profile=benchmark_profile,
            report_id=report_id,
            cache_profile=cache_profile,
            shard_index=shard_index,
            shard_count=shard_count,
        )
        return _run_prepared_live_scenario(prepared_request)
    if str(scenario.get("kind", "")).strip() == "architecture":
        return _architecture_result(repo_root=repo_root, scenario=scenario, mode=mode)
    return _packet_result(
        repo_root=repo_root,
        scenario=scenario,
        mode=mode,
        report_id=report_id,
        cache_profile=cache_profile,
        shard_index=shard_index,
        shard_count=shard_count,
    )


def _median(values: Sequence[float]) -> float:
    rows = [float(value) for value in values]
    if not rows:
        return 0.0
    return round(float(statistics.median(rows)), 3)


def _avg(values: Sequence[float]) -> float:
    rows = [float(value) for value in values]
    if not rows:
        return 0.0
    return round(sum(rows) / max(1, len(rows)), 3)


def _percentile(values: Sequence[float], quantile: float) -> float:
    rows = sorted(float(value) for value in values)
    if not rows:
        return 0.0
    if len(rows) == 1:
        return round(rows[0], 3)
    bounded = max(0.0, min(1.0, float(quantile)))
    index = (len(rows) - 1) * bounded
    lower = int(index)
    upper = min(lower + 1, len(rows) - 1)
    fraction = index - lower
    value = rows[lower] * (1.0 - fraction) + rows[upper] * fraction
    return round(value, 3)


def _sum(values: Sequence[float]) -> float:
    rows = [float(value) for value in values]
    if not rows:
        return 0.0
    return round(sum(rows), 3)


def _rate(values: Sequence[bool]) -> float:
    rows = [1.0 if bool(value) else 0.0 for value in values]
    return _avg(rows)


def _stage_latency_summary(scenario_rows: Sequence[Mapping[str, Any]]) -> dict[str, dict[str, float]]:
    samples: dict[str, list[float]] = {}
    for row in scenario_rows:
        timing_trace = dict(row.get("timing_trace", {})) if isinstance(row.get("timing_trace"), Mapping) else {}
        operations = timing_trace.get("operations", {})
        if not isinstance(operations, Mapping):
            continue
        for operation, payload in operations.items():
            if not isinstance(payload, Mapping):
                continue
            duration_ms = float(payload.get("duration_ms", 0.0) or 0.0)
            operation_key = f"{str(operation).strip()}.total"
            samples.setdefault(operation_key, []).append(duration_ms)
            stage_timings = payload.get("stage_timings", {})
            if not isinstance(stage_timings, Mapping):
                continue
            for stage_name, stage_duration in stage_timings.items():
                key = f"{str(operation).strip()}.{str(stage_name).strip()}"
                samples.setdefault(key, []).append(float(stage_duration or 0.0))
    return {
        key: {
            "median_ms": _median(values),
            "avg_ms": _avg(values),
        }
        for key, values in sorted(samples.items())
        if values
    }


def _artifact_token_summary(
    scenario_rows: Sequence[Mapping[str, Any]],
    *,
    field_name: str,
) -> dict[str, dict[str, float]]:
    samples: dict[str, list[float]] = {}
    for row in scenario_rows:
        artifact_tokens = dict(row.get(field_name, {})) if isinstance(row.get(field_name), Mapping) else {}
        for artifact_name, token_count in artifact_tokens.items():
            name = str(artifact_name).strip()
            if not name:
                continue
            samples.setdefault(name, []).append(float(token_count or 0.0))
    return {
        name: {
            "median_tokens": _median(values),
            "avg_tokens": _avg(values),
        }
        for name, values in sorted(samples.items())
        if values
    }


def _distribution_summary(scenario_rows: Sequence[Mapping[str, Any]], *, field_name: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in scenario_rows:
        payload = dict(row.get(field_name, {})) if isinstance(row.get(field_name), Mapping) else {}
        token = str(payload.get("stage", "")).strip() or "unspecified"
        counts[token] = counts.get(token, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def _orchestration_adoption_distribution(
    scenario_rows: Sequence[Mapping[str, Any]],
    *,
    field_name: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in scenario_rows:
        orchestration = dict(row.get("orchestration", {})) if isinstance(row.get("orchestration"), Mapping) else {}
        adoption = dict(orchestration.get("odylith_adoption", {})) if isinstance(orchestration.get("odylith_adoption"), Mapping) else {}
        token = str(adoption.get(field_name, "")).strip() or "none"
        counts[token] = counts.get(token, 0) + 1
    return {key: counts[key] for key in sorted(counts)}


def _mode_execution_contract(mode_rows: Mapping[str, Sequence[Mapping[str, Any]]], *, mode: str) -> dict[str, Any]:
    rows = _lookup_mode_mapping(mode_rows, mode)
    if not isinstance(rows, Sequence):
        return {}
    for row in rows:
        if not isinstance(row, Mapping):
            continue
        payload = dict(row.get("execution_contract", {})) if isinstance(row.get("execution_contract"), Mapping) else {}
        if payload:
            return payload
    return {}


def _live_execution_contracts(mode_rows: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, dict[str, Any]]:
    contracts: dict[str, dict[str, Any]] = {}
    for mode in (_ODYLITH_ON_MODE, _BASELINE_MODE):
        payload = _mode_execution_contract(mode_rows, mode=mode)
        if payload:
            contracts[mode] = payload
    return contracts


def _live_execution_contract_match(execution_contracts: Mapping[str, Mapping[str, Any]] | None) -> bool:
    if not isinstance(execution_contracts, Mapping):
        return True
    candidate = dict(_lookup_mode_mapping(execution_contracts, _ODYLITH_ON_MODE) or {})
    baseline = dict(_lookup_mode_mapping(execution_contracts, _BASELINE_MODE) or {})
    if not candidate or not baseline:
        return True
    fields = ("runner", "codex_bin", "model", "reasoning_effort")
    return all(str(candidate.get(field, "")).strip() == str(baseline.get(field, "")).strip() for field in fields)


def _mode_summary(*, mode: str, scenario_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    latencies = [float(row.get("latency_ms", 0.0) or 0.0) for row in scenario_rows]
    instrumented_latencies = [float(row.get("instrumented_reasoning_duration_ms", 0.0) or 0.0) for row in scenario_rows]
    uninstrumented_overhead = [float(row.get("uninstrumented_overhead_ms", 0.0) or 0.0) for row in scenario_rows]
    initial_prompt_tokens = [float(row.get("initial_prompt_estimated_tokens", 0.0) or 0.0) for row in scenario_rows]
    tokens = [float(row.get("effective_estimated_tokens", 0.0) or 0.0) for row in scenario_rows]
    total_payload_tokens = [
        float(row.get("total_payload_estimated_tokens", row.get("effective_estimated_tokens", 0.0)) or 0.0)
        for row in scenario_rows
    ]
    runtime_contract_tokens = [
        float(row.get("runtime_contract_estimated_tokens", 0.0) or 0.0)
        for row in scenario_rows
    ]
    operator_diag_tokens = [
        float(row.get("operator_diag_estimated_tokens", 0.0) or 0.0)
        for row in scenario_rows
    ]
    observed_path_counts = [int(row.get("observed_path_count", 0) or 0) for row in scenario_rows]
    candidate_write_path_counts = [int(row.get("candidate_write_path_count", 0) or 0) for row in scenario_rows]
    recalls = [float(row.get("required_path_recall", 0.0) or 0.0) for row in scenario_rows]
    expectation_success = [
        bool(row.get("expectation_ok"))
        for row in scenario_rows
        if str(row.get("kind", "")).strip() != "architecture" or _mode_supports_architecture_dossier(mode)
    ]
    packet_rows = [row for row in scenario_rows if str(row.get("kind", "")).strip() == "packet"]
    architecture_rows = [row for row in scenario_rows if str(row.get("kind", "")).strip() == "architecture"]
    within_budget = [
        bool(dict(row.get("packet", {})).get("within_budget"))
        for row in packet_rows
        if isinstance(row.get("packet"), Mapping)
    ]
    route_ready = [
        bool(dict(row.get("packet", {})).get("route_ready"))
        for row in packet_rows
        if isinstance(row.get("packet"), Mapping)
    ]
    route_ready_rows = [
        row
        for row in packet_rows
        if isinstance(row.get("packet"), Mapping) and bool(dict(row.get("packet", {})).get("route_ready"))
    ]
    route_ready_validation_success = [
        bool(float(row.get("validation_success_proxy", 0.0) or 0.0) >= 1.0)
        for row in route_ready_rows
        if int(row.get("validation_command_count", 0) or 0) > 0
    ]
    route_ready_expectation_success = [bool(row.get("expectation_ok")) for row in route_ready_rows]
    leaf_counts = [int(dict(row.get("orchestration", {})).get("leaf_count", 0) or 0) for row in scenario_rows]
    odylith_adoption_rows = [
        dict(dict(row.get("orchestration", {})).get("odylith_adoption", {}))
        for row in scenario_rows
        if isinstance(row.get("orchestration"), Mapping)
        and isinstance(dict(row.get("orchestration", {})).get("odylith_adoption"), Mapping)
    ]
    odylith_packet_present = [bool(row.get("packet_present")) for row in odylith_adoption_rows]
    odylith_auto_grounded = [bool(row.get("auto_grounding_applied")) for row in odylith_adoption_rows]
    odylith_requires_widening = [bool(row.get("requires_widening")) for row in odylith_adoption_rows]
    odylith_grounded = [bool(row.get("grounded")) for row in odylith_adoption_rows]
    odylith_grounded_delegate = [bool(row.get("grounded_delegate")) for row in odylith_adoption_rows]
    odylith_workspace_daemon_reused = [bool(row.get("workspace_daemon_reused")) for row in odylith_adoption_rows]
    odylith_session_namespaced = [bool(row.get("session_namespaced")) for row in odylith_adoption_rows]
    odylith_mixed_local_fallback = [bool(row.get("mixed_local_fallback")) for row in odylith_adoption_rows]
    required_path_backed_rows = [row for row in scenario_rows if int(row.get("required_path_count", 0) or 0) > 0]
    required_path_precision = [float(row.get("required_path_precision", 0.0) or 0.0) for row in required_path_backed_rows]
    hallucinated_surface_rates = [float(row.get("hallucinated_surface_rate", 0.0) or 0.0) for row in required_path_backed_rows]
    validation_backed_rows = [row for row in scenario_rows if int(row.get("validation_command_count", 0) or 0) > 0]
    validation_success = [
        bool(float(row.get("validation_success_proxy", 0.0) or 0.0) >= 1.0)
        for row in validation_backed_rows
    ]
    write_surface_backed_rows = [row for row in scenario_rows if int(row.get("expected_write_path_count", 0) or 0) > 0]
    write_surface_precision = [float(row.get("write_surface_precision", 0.0) or 0.0) for row in write_surface_backed_rows]
    unnecessary_widening = [float(row.get("unnecessary_widening_rate", 0.0) or 0.0) for row in write_surface_backed_rows]
    correctness_critical_rows = [row for row in scenario_rows if bool(row.get("correctness_critical"))]
    critical_required_path_backed_rows = [row for row in correctness_critical_rows if int(row.get("required_path_count", 0) or 0) > 0]
    critical_validation_backed_rows = [row for row in correctness_critical_rows if int(row.get("validation_command_count", 0) or 0) > 0]
    critical_recalls = [float(row.get("required_path_recall", 0.0) or 0.0) for row in critical_required_path_backed_rows]
    critical_validation_success = [
        bool(float(row.get("validation_success_proxy", 0.0) or 0.0) >= 1.0)
        for row in critical_validation_backed_rows
    ]
    selector_diagnostics = [
        dict(row.get("selector_diagnostics", {}))
        for row in scenario_rows
        if isinstance(row.get("selector_diagnostics"), Mapping)
    ]
    fast_selector_hits = [
        bool(diag.get("fast_selector_used") or diag.get("component_fast_selector_used"))
        for diag in selector_diagnostics
    ]
    selector_cache_hits = [
        bool(diag.get("selector_cache_hit") or diag.get("component_selector_cache_hit"))
        for diag in selector_diagnostics
    ]
    workstream_selector_hits = [bool(diag.get("fast_selector_used")) for diag in selector_diagnostics]
    component_selector_hits = [bool(diag.get("component_fast_selector_used")) for diag in selector_diagnostics]
    architecture_compaction_applied = [bool(row.get("architecture_compaction_applied")) for row in architecture_rows]
    summary = {
        "mode": mode,
        "scenario_count": len(scenario_rows),
        "packet_scenario_count": len(packet_rows),
        "architecture_scenario_count": len(architecture_rows),
        "median_latency_ms": _median(latencies),
        "avg_latency_ms": _avg(latencies),
        "p95_latency_ms": _percentile(latencies, 0.95),
        "median_instrumented_reasoning_duration_ms": _median(instrumented_latencies),
        "avg_instrumented_reasoning_duration_ms": _avg(instrumented_latencies),
        "p95_instrumented_reasoning_duration_ms": _percentile(instrumented_latencies, 0.95),
        "median_uninstrumented_overhead_ms": _median(uninstrumented_overhead),
        "avg_uninstrumented_overhead_ms": _avg(uninstrumented_overhead),
        "p95_uninstrumented_overhead_ms": _percentile(uninstrumented_overhead, 0.95),
        "median_initial_prompt_tokens": _median(initial_prompt_tokens),
        "avg_initial_prompt_tokens": _avg(initial_prompt_tokens),
        "median_effective_tokens": _median(tokens),
        "avg_effective_tokens": _avg(tokens),
        "effective_token_basis": str(scenario_rows[0].get("effective_token_basis", "")).strip() if scenario_rows else "",
        "median_total_payload_tokens": _median(total_payload_tokens),
        "avg_total_payload_tokens": _avg(total_payload_tokens),
        "median_runtime_contract_tokens": _median(runtime_contract_tokens),
        "avg_runtime_contract_tokens": _avg(runtime_contract_tokens),
        "median_operator_diag_tokens": _median(operator_diag_tokens),
        "avg_operator_diag_tokens": _avg(operator_diag_tokens),
        "median_observed_path_count": _median(observed_path_counts),
        "avg_observed_path_count": _avg(observed_path_counts),
        "median_candidate_write_path_count": _median(candidate_write_path_counts),
        "avg_candidate_write_path_count": _avg(candidate_write_path_counts),
        "median_selected_doc_count": _median([int(row.get("selected_doc_count", 0) or 0) for row in packet_rows]),
        "avg_selected_doc_count": _avg([int(row.get("selected_doc_count", 0) or 0) for row in packet_rows]),
        "median_selected_command_count": _median([int(row.get("selected_command_count", 0) or 0) for row in packet_rows]),
        "avg_selected_command_count": _avg([int(row.get("selected_command_count", 0) or 0) for row in packet_rows]),
        "required_path_recall_rate": _avg(recalls),
        "required_path_precision_rate": _avg(required_path_precision),
        "hallucinated_surface_rate": _avg(hallucinated_surface_rates),
        "validation_success_rate": _rate(validation_success),
        "expectation_success_rate": _rate(expectation_success),
        "write_surface_precision_rate": _avg(write_surface_precision),
        "unnecessary_widening_rate": _avg(unnecessary_widening),
        "within_budget_rate": _rate(within_budget),
        "route_ready_rate": _rate(route_ready),
        "route_ready_validation_success_rate": _rate(route_ready_validation_success),
        "route_ready_expectation_success_rate": _rate(route_ready_expectation_success),
        "avg_delegated_leaf_count": _avg(leaf_counts),
        "odylith_packet_present_rate": _rate(odylith_packet_present),
        "odylith_auto_grounded_rate": _rate(odylith_auto_grounded),
        "odylith_requires_widening_rate": _rate(odylith_requires_widening),
        "odylith_grounded_rate": _rate(odylith_grounded),
        "odylith_grounded_delegate_rate": _rate(odylith_grounded_delegate),
        "odylith_workspace_daemon_reuse_rate": _rate(odylith_workspace_daemon_reused),
        "odylith_session_namespaced_rate": _rate(odylith_session_namespaced),
        "odylith_mixed_local_fallback_rate": _rate(odylith_mixed_local_fallback),
        "required_path_backed_scenario_count": len(required_path_backed_rows),
        "validation_backed_scenario_count": len(validation_backed_rows),
        "write_surface_backed_scenario_count": len(write_surface_backed_rows),
        "correctness_critical_scenario_count": len(correctness_critical_rows),
        "critical_required_path_backed_scenario_count": len(critical_required_path_backed_rows),
        "critical_validation_backed_scenario_count": len(critical_validation_backed_rows),
        "critical_required_path_recall_rate": _avg(critical_recalls),
        "critical_validation_success_rate": _rate(critical_validation_success),
        "fast_selector_hit_rate": _rate(fast_selector_hits),
        "hot_path_selector_cache_hit_rate": _rate(selector_cache_hits),
        "workstream_fast_selector_hit_rate": _rate(workstream_selector_hits),
        "component_fast_selector_hit_rate": _rate(component_selector_hits),
        "compact_architecture_applied_rate": _rate(architecture_compaction_applied),
        "stage_latency_summary": _stage_latency_summary(scenario_rows),
        "prompt_artifact_summary": _artifact_token_summary(scenario_rows, field_name="prompt_artifact_tokens"),
        "runtime_contract_artifact_summary": _artifact_token_summary(
            scenario_rows,
            field_name="runtime_contract_artifact_tokens",
        ),
        "operator_diag_artifact_summary": _artifact_token_summary(
            scenario_rows,
            field_name="operator_diag_artifact_tokens",
        ),
        "escalation_stage_distribution": _distribution_summary(
            scenario_rows,
            field_name="adaptive_escalation",
        ),
        "odylith_grounding_source_distribution": _orchestration_adoption_distribution(
            scenario_rows,
            field_name="grounding_source",
        ),
        "odylith_operation_distribution": _orchestration_adoption_distribution(
            scenario_rows,
            field_name="operation",
        ),
        "odylith_runtime_source_distribution": _orchestration_adoption_distribution(
            scenario_rows,
            field_name="runtime_source",
        ),
        "odylith_runtime_transport_distribution": _orchestration_adoption_distribution(
            scenario_rows,
            field_name="runtime_transport",
        ),
    }
    summary.update(odylith_benchmark_proof_discipline.summary_from_rows(scenario_rows))
    summary.update(odylith_benchmark_context_engine.summary_from_rows(scenario_rows))
    summary.update(odylith_benchmark_execution_engine.summary_from_rows(scenario_rows))
    return summary


def _result_wall_clock_ms(result: Mapping[str, Any]) -> float:
    live_execution = dict(result.get("live_execution", {})) if isinstance(result.get("live_execution"), Mapping) else {}
    return round(float(live_execution.get("wall_clock_ms", result.get("latency_ms", 0.0)) or 0.0), 3)


def _pair_timing_summary(
    *,
    scenarios: Sequence[Mapping[str, Any]],
    candidate_mode: str,
    baseline_mode: str,
) -> dict[str, Any]:
    pair_wall_clock_ms: list[float] = []
    serial_lane_clock_ms: list[float] = []
    candidate_lane_clock_ms: list[float] = []
    baseline_lane_clock_ms: list[float] = []
    for scenario in scenarios:
        if not isinstance(scenario, Mapping):
            continue
        results = scenario.get("results", [])
        if not isinstance(results, Sequence):
            continue
        result_map = {
            _normalize_mode(str(result.get("mode", "")).strip()): dict(result)
            for result in results
            if isinstance(result, Mapping) and str(result.get("mode", "")).strip()
        }
        candidate_result = result_map.get(_normalize_mode(candidate_mode))
        baseline_result = result_map.get(_normalize_mode(baseline_mode))
        if not candidate_result or not baseline_result:
            continue
        candidate_ms = _result_wall_clock_ms(candidate_result)
        baseline_ms = _result_wall_clock_ms(baseline_result)
        candidate_lane_clock_ms.append(candidate_ms)
        baseline_lane_clock_ms.append(baseline_ms)
        serial_lane_clock_ms.append(round(candidate_ms + baseline_ms, 3))
        pair_wall_clock_ms.append(round(max(candidate_ms, baseline_ms), 3))
    if not pair_wall_clock_ms:
        return {
            "pair_count": 0,
            "median_pair_wall_clock_ms": 0.0,
            "avg_pair_wall_clock_ms": 0.0,
            "p95_pair_wall_clock_ms": 0.0,
            "max_pair_wall_clock_ms": 0.0,
            "total_pair_wall_clock_ms": 0.0,
            "avg_serial_lane_clock_ms": 0.0,
            "total_serial_lane_clock_ms": 0.0,
            "avg_candidate_lane_clock_ms": 0.0,
            "avg_baseline_lane_clock_ms": 0.0,
        }
    return {
        "pair_count": len(pair_wall_clock_ms),
        "median_pair_wall_clock_ms": _median(pair_wall_clock_ms),
        "avg_pair_wall_clock_ms": _avg(pair_wall_clock_ms),
        "p95_pair_wall_clock_ms": _percentile(pair_wall_clock_ms, 0.95),
        "max_pair_wall_clock_ms": round(max(pair_wall_clock_ms), 3),
        "total_pair_wall_clock_ms": _sum(pair_wall_clock_ms),
        "avg_serial_lane_clock_ms": _avg(serial_lane_clock_ms),
        "total_serial_lane_clock_ms": _sum(serial_lane_clock_ms),
        "avg_candidate_lane_clock_ms": _avg(candidate_lane_clock_ms),
        "avg_baseline_lane_clock_ms": _avg(baseline_lane_clock_ms),
    }


def _corpus_summary(*, scenarios: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    packet_rows = [row for row in scenarios if str(row.get("kind", "")).strip() == "packet"]
    architecture_rows = [row for row in scenarios if str(row.get("kind", "")).strip() == "architecture"]
    required_path_backed = [row for row in scenarios if row.get("required_paths")]
    validation_backed = [row for row in scenarios if row.get("validation_commands")]
    write_surface_backed = [row for row in scenarios if bool(row.get("needs_write")) and row.get("changed_paths")]
    correctness_critical = [row for row in scenarios if bool(row.get("correctness_critical"))]
    critical_required_path_backed = [row for row in correctness_critical if row.get("required_paths")]
    critical_validation_backed = [row for row in correctness_critical if row.get("validation_commands")]
    write_plus_validator_rows = [
        row for row in packet_rows if bool(row.get("needs_write")) and row.get("validation_commands")
    ]
    implementation_family_counts: dict[str, int] = {}
    for row in packet_rows:
        family = str(row.get("family", "")).strip()
        if not family:
            continue
        implementation_family_counts[family] = implementation_family_counts.get(family, 0) + 1
    mechanism_heavy_rows = [
        row
        for row in packet_rows
        if str(row.get("family", "")).strip() in _MECHANISM_HEAVY_IMPLEMENTATION_FAMILIES
    ]
    required_family_counts = {
        family: int(implementation_family_counts.get(family, 0) or 0)
        for family in sorted(_SERIOUS_REQUIRED_FAMILIES)
    }
    return {
        "scenario_count": len(scenarios),
        "packet_scenario_count": len(packet_rows),
        "architecture_scenario_count": len(architecture_rows),
        "implementation_scenario_count": len(packet_rows),
        "family_count": len({str(row.get("family", "")).strip() for row in scenarios if str(row.get("family", "")).strip()}),
        "required_path_backed_scenario_count": len(required_path_backed),
        "validation_backed_scenario_count": len(validation_backed),
        "write_surface_backed_scenario_count": len(write_surface_backed),
        "write_plus_validator_scenario_count": len(write_plus_validator_rows),
        "correctness_critical_scenario_count": len(correctness_critical),
        "critical_required_path_backed_scenario_count": len(critical_required_path_backed),
        "critical_validation_backed_scenario_count": len(critical_validation_backed),
        "implementation_family_counts": implementation_family_counts,
        "mechanism_heavy_implementation_scenario_count": len(mechanism_heavy_rows),
        "mechanism_heavy_implementation_ratio": round(
            len(mechanism_heavy_rows) / max(1, len(packet_rows)),
            3,
        ),
        "required_family_counts": required_family_counts,
    }


def _corpus_composition(*, scenarios: Sequence[Mapping[str, Any]], available_scenarios: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summary = _corpus_summary(scenarios=scenarios)
    implementation_count = int(summary.get("implementation_scenario_count", 0) or 0)
    mechanism_ratio = float(summary.get("mechanism_heavy_implementation_ratio", 0.0) or 0.0)
    required_family_counts = (
        dict(summary.get("required_family_counts", {}))
        if isinstance(summary.get("required_family_counts"), Mapping)
        else {}
    )
    findings: list[str] = []
    if implementation_count < _SERIOUS_IMPLEMENTATION_SCENARIO_MIN:
        findings.append(
            f"implementation_scenario_count={implementation_count} is below the seriousness floor {_SERIOUS_IMPLEMENTATION_SCENARIO_MIN}"
        )
    write_plus_validator = int(summary.get("write_plus_validator_scenario_count", 0) or 0)
    if write_plus_validator < _SERIOUS_WRITE_PLUS_VALIDATOR_SCENARIO_MIN:
        findings.append(
            f"write_plus_validator_scenario_count={write_plus_validator} is below the seriousness floor {_SERIOUS_WRITE_PLUS_VALIDATOR_SCENARIO_MIN}"
        )
    correctness_critical = int(summary.get("correctness_critical_scenario_count", 0) or 0)
    if correctness_critical < _SERIOUS_CORRECTNESS_CRITICAL_SCENARIO_MIN:
        findings.append(
            f"correctness_critical_scenario_count={correctness_critical} is below the seriousness floor {_SERIOUS_CORRECTNESS_CRITICAL_SCENARIO_MIN}"
        )
    if mechanism_ratio > _SERIOUS_MECHANISM_HEAVY_IMPLEMENTATION_MAX_RATIO:
        findings.append(
            "mechanism_heavy_implementation_ratio="
            f"{mechanism_ratio:.3f} exceeds the seriousness ceiling {_SERIOUS_MECHANISM_HEAVY_IMPLEMENTATION_MAX_RATIO:.2f}"
        )
    missing_required_families = [
        family for family in sorted(_SERIOUS_REQUIRED_FAMILIES) if int(required_family_counts.get(family, 0) or 0) <= 0
    ]
    if missing_required_families:
        findings.append("required serious families missing: " + ", ".join(missing_required_families))
    available_count = len(list(available_scenarios))
    selected_count = len(list(scenarios))
    full_corpus_coverage = round(selected_count / max(1, available_count), 3)
    if available_count and selected_count != available_count:
        findings.append(
            f"published selection covers {selected_count}/{available_count} tracked scenarios instead of the full current corpus"
        )
    return {
        "implementation_scenario_count": implementation_count,
        "write_plus_validator_scenario_count": write_plus_validator,
        "correctness_critical_scenario_count": correctness_critical,
        "mechanism_heavy_implementation_scenario_count": int(
            summary.get("mechanism_heavy_implementation_scenario_count", 0) or 0
        ),
        "mechanism_heavy_implementation_ratio": mechanism_ratio,
        "required_family_counts": required_family_counts,
        "required_serious_families": sorted(_SERIOUS_REQUIRED_FAMILIES),
        "full_corpus_selected": selected_count == available_count if available_count else False,
        "selected_scenario_count": selected_count,
        "available_scenario_count": available_count,
        "full_corpus_coverage_rate": full_corpus_coverage,
        "seriousness_floor_passed": not findings,
        "findings": findings,
    }


def _fairness_findings(
    *,
    repo_root: Path,
    comparison_contract: str,
    published_scenarios: Sequence[Mapping[str, Any]],
) -> list[str]:
    if not _is_live_comparison_contract(comparison_contract):
        return []
    findings: list[str] = []
    for scenario in published_scenarios:
        scenario_id = str(scenario.get("scenario_id", "")).strip() or str(scenario.get("label", "")).strip() or "scenario"
        raw_prompt_visible_expected = bool(
            odylith_benchmark_live_diagnostics.raw_prompt_visible_paths(
                repo_root=repo_root,
                raw_prompt={
                    "prompt": str(scenario.get("prompt", "")).strip(),
                    "acceptance_criteria": [
                        str(token).strip()
                        for token in scenario.get("acceptance_criteria", [])
                        if str(token).strip()
                    ],
                },
            )
        )
        for result in scenario.get("results", []):
            if not isinstance(result, Mapping):
                continue
            mode = _normalize_mode(str(result.get("mode", "")).strip())
            sources = {
                str(token).strip()
                for token in result.get("observed_path_sources", [])
                if isinstance(result.get("observed_path_sources"), list) and str(token).strip()
            }
            preflight_mode = str(result.get("preflight_evidence_mode", "")).strip()
            if mode == _RAW_AGENT_BASELINE_MODE and preflight_mode not in {"", "none"}:
                findings.append(
                    f"{scenario_id}/{mode} exposes unexpected preflight evidence mode `{preflight_mode}`"
                )
            if mode == _RAW_AGENT_BASELINE_MODE and raw_prompt_visible_expected and "raw_prompt_visible_paths" not in sources:
                findings.append(
                    f"{scenario_id}/{mode} is missing raw prompt-visible path attribution"
                )
            if mode == _ODYLITH_ON_MODE and preflight_mode not in {
                "",
                "none",
                "scenario_declared_focused_local_checks",
            }:
                findings.append(
                    f"{scenario_id}/{mode} uses undeclared preflight evidence mode `{preflight_mode}`"
                )
    return _dedupe_strings(findings)


def _proof_request_from_scenario(
    *,
    scenario: Mapping[str, Any],
    operation: str,
    sample_id: str,
) -> dict[str, Any]:
    changed_paths = [str(token).strip() for token in scenario.get("changed_paths", []) if str(token).strip()]
    candidate_paths = list(changed_paths)
    if operation == "governance_slice" and "odylith/index.html" not in candidate_paths:
        candidate_paths.append("odylith/index.html")
    validation_commands = [str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()]
    return {
        "prompt": str(scenario.get("prompt", "")).strip() or str(scenario.get("summary", "")).strip() or str(scenario.get("label", "")).strip(),
        "acceptance_criteria": [str(token).strip() for token in scenario.get("acceptance_criteria", []) if str(token).strip()],
        "candidate_paths": candidate_paths,
        "workstreams": [str(scenario.get("workstream", "")).strip()] if str(scenario.get("workstream", "")).strip() else [],
        "components": [str(scenario.get("component", "")).strip()] if str(scenario.get("component", "")).strip() else [],
        "validation_commands": validation_commands,
        "accuracy_preference": "accuracy",
        "repo_work": True,
        "task_kind": "analysis" if str(scenario.get("kind", "")).strip() == "architecture" or not bool(scenario.get("needs_write")) else "implementation",
        "phase": "analysis" if str(scenario.get("kind", "")).strip() == "architecture" or not bool(scenario.get("needs_write")) else "implementation",
        "needs_write": bool(scenario.get("needs_write")),
        "correctness_critical": bool(scenario.get("correctness_critical")),
        "evidence_cone_grounded": False,
        "odylith_operation": operation,
        "session_id": f"benchmark-proof-{sample_id}",
        "claimed_paths": candidate_paths[:3],
        "use_working_tree": True,
        "working_tree_scope": "session",
    }


def _persist_adoption_proof_ledger(
    *,
    repo_root: Path,
    sample_id: str,
    request_payload: Mapping[str, Any],
    summary: Mapping[str, Any],
) -> None:
    adoption = (
        dict(summary.get("odylith_adoption", {}))
        if isinstance(summary.get("odylith_adoption"), Mapping)
        else {}
    )
    if not adoption:
        return
    recorded_at = _utc_now()
    decision_id = f"benchmark-proof-{sample_id}"
    path = subagent_orchestrator.decision_ledger_path(
        repo_root=Path(repo_root).resolve(),
        decision_id=decision_id,
    )
    odylith_context_cache.write_json_if_changed(
        repo_root=Path(repo_root).resolve(),
        path=path,
        payload={
            "decision_id": decision_id,
            "recorded_at": recorded_at,
            "updated_at": recorded_at,
            "source": "odylith_benchmark_adoption_proof",
            "request_summary": {
                "prompt": str(request_payload.get("prompt", "")).strip(),
                "candidate_paths": [
                    str(token).strip()
                    for token in request_payload.get("candidate_paths", [])
                    if str(token).strip()
                ]
                if isinstance(request_payload.get("candidate_paths"), list)
                else [],
                "odylith_operation": str(request_payload.get("odylith_operation", "")).strip(),
            },
            "decision_summary": {
                "odylith_adoption": adoption,
            },
        },
        lock_key=str(path),
    )


@contextlib.contextmanager
def _benchmark_proof_daemon(repo_root: Path) -> Iterator[bool]:
    root = Path(repo_root).resolve()
    if store.runtime_daemon_transport(repo_root=root) is not None:
        yield False
        return
    from odylith.runtime.context_engine import odylith_context_engine

    auth_token = secrets.token_urlsafe(24)
    server = odylith_context_engine._RuntimeDaemonServer(repo_root=root, auth_token=auth_token)  # noqa: SLF001
    odylith_context_engine._write_pid(repo_root=root)  # noqa: SLF001
    odylith_context_engine._write_daemon_metadata(  # noqa: SLF001
        repo_root=root,
        spawn_reason="explicit",
        idle_timeout_seconds=0,
        auth_token=auth_token,
    )
    server.start()
    try:
        yield True
    finally:
        server.close()
        odylith_context_engine._clear_pid(repo_root=root)  # noqa: SLF001
        odylith_context_engine._clear_daemon_metadata(repo_root=root)  # noqa: SLF001


def _live_adoption_proof_scenarios(
    *,
    scenarios: Sequence[Mapping[str, Any]],
) -> list[tuple[str, dict[str, Any]]]:
    governance = [
        dict(row)
        for row in scenarios
        if str(row.get("kind", "")).strip() == "packet"
        and _packet_source_for_scenario(row) == "governance_slice"
    ]
    architecture = [
        dict(row)
        for row in scenarios
        if str(row.get("kind", "")).strip() == "architecture"
    ]
    impact = [
        dict(row)
        for row in scenarios
        if str(row.get("kind", "")).strip() == "packet"
        and _packet_source_for_scenario(row) == "impact"
        and str(row.get("family", "")).strip() not in {
            "broad_shared_scope",
            "exact_path_ambiguity",
            "retrieval_miss_recovery",
        }
    ]
    ordered: list[tuple[str, dict[str, Any]]] = []
    ordered.extend(("impact", row) for row in impact[:6])
    ordered.extend(("governance_slice", row) for row in governance[:3])
    ordered.extend(("architecture", row) for row in architecture[:3])
    return ordered[:12]


def _runtime_posture_summary(*, repo_root: Path) -> dict[str, Any]:
    optimization = store.load_runtime_optimization_snapshot(repo_root=repo_root)
    evaluation = store.load_runtime_evaluation_snapshot(repo_root=repo_root)
    memory = store.load_runtime_memory_snapshot(
        repo_root=repo_root,
        optimization_snapshot=optimization,
        evaluation_snapshot=evaluation,
    )
    backend_transition = dict(memory.get("backend_transition", {})) if isinstance(memory.get("backend_transition"), Mapping) else {}
    actual_backend = dict(backend_transition.get("actual_local_backend", {})) if isinstance(backend_transition.get("actual_local_backend"), Mapping) else {}
    target_backend = dict(backend_transition.get("target_local_backend", {})) if isinstance(backend_transition.get("target_local_backend"), Mapping) else {}
    local_backend_status = dict(backend_transition.get("local_backend_status", {})) if isinstance(backend_transition.get("local_backend_status"), Mapping) else {}
    signature = dict(backend_transition.get("signature", {})) if isinstance(backend_transition.get("signature"), Mapping) else {}
    degraded_fallback = dict(memory.get("repo_scan_degraded_fallback", {})) if isinstance(memory.get("repo_scan_degraded_fallback"), Mapping) else {}
    governance_runtime_first = dict(memory.get("governance_runtime_first", {})) if isinstance(memory.get("governance_runtime_first"), Mapping) else {}
    entity_counts = dict(memory.get("entity_counts", {})) if isinstance(memory.get("entity_counts"), Mapping) else {}
    remote_retrieval = dict(memory.get("remote_retrieval", {})) if isinstance(memory.get("remote_retrieval"), Mapping) else {}
    quality_posture = dict(optimization.get("quality_posture", {})) if isinstance(optimization.get("quality_posture"), Mapping) else {}
    architecture = dict(evaluation.get("architecture", {})) if isinstance(evaluation.get("architecture"), Mapping) else {}
    storage = str(actual_backend.get("storage", "")).strip()
    sparse_recall = str(actual_backend.get("sparse_recall", "")).strip()
    projection_scope = str(signature.get("projection_scope", "")).strip()
    indexed_entities = int(entity_counts.get("indexed_entity_count", 0) or 0)
    evidence_documents = int(entity_counts.get("evidence_documents", 0) or 0)
    memory_backed_retrieval_ready = bool(local_backend_status.get("ready")) and storage == "lance_local_columnar" and sparse_recall == "tantivy_sparse_recall" and indexed_entities > 0 and evidence_documents > 0
    payload = {
        "memory_standardization_state": str(backend_transition.get("status", "")).strip(),
        "memory_backend_actual": {
            "storage": storage,
            "sparse_recall": sparse_recall,
        },
        "memory_backend_target": {
            "storage": str(target_backend.get("storage", "")).strip(),
            "sparse_recall": str(target_backend.get("sparse_recall", "")).strip(),
        },
        "memory_backed_retrieval_ready": memory_backed_retrieval_ready,
        "memory_local_backend_ready": bool(local_backend_status.get("ready")),
        "memory_projection_scope": projection_scope,
        "memory_indexed_entity_count": indexed_entities,
        "memory_evidence_document_count": evidence_documents,
        "remote_retrieval_enabled": bool(remote_retrieval.get("enabled")),
        "remote_retrieval_configured": bool(remote_retrieval.get("configured")),
        "remote_retrieval_mode": str(remote_retrieval.get("mode", "")).strip() or "disabled",
        "remote_retrieval_provider": str(remote_retrieval.get("provider", "")).strip(),
        "remote_retrieval_status": str(remote_retrieval.get("status", "")).strip() or "disabled",
        "repo_scan_degraded_fallback_rate": float(
            degraded_fallback.get("repo_scan_degraded_fallback_rate", 0.0) or 0.0
        ),
        "repo_scan_degraded_reason_distribution": dict(
            degraded_fallback.get("repo_scan_degraded_reason_distribution", {})
        )
        if isinstance(degraded_fallback.get("repo_scan_degraded_reason_distribution"), Mapping)
        else {},
        "governance_runtime_first_usage_rate": float(governance_runtime_first.get("usage_rate", 0.0) or 0.0),
        "governance_runtime_first_fallback_rate": float(governance_runtime_first.get("fallback_rate", 0.0) or 0.0),
        "governance_runtime_first_fallback_reason_distribution": dict(
            governance_runtime_first.get("fallback_reason_distribution", {})
        )
        if isinstance(governance_runtime_first.get("fallback_reason_distribution"), Mapping)
        else {},
        "route_ready_rate": float(quality_posture.get("route_ready_rate", 0.0) or 0.0),
        "native_spawn_ready_rate": float(quality_posture.get("native_spawn_ready_rate", 0.0) or 0.0),
        "architecture_covered_case_count": int(architecture.get("covered_case_count", 0) or 0),
        "architecture_satisfied_case_count": int(architecture.get("satisfied_case_count", 0) or 0),
        "architecture_coverage_rate": float(architecture.get("coverage_rate", 0.0) or 0.0),
        "architecture_satisfaction_rate": float(architecture.get("satisfaction_rate", 0.0) or 0.0),
    }
    if payload["memory_backed_retrieval_ready"]:
        return payload
    managed_payload = _managed_runtime_posture_summary(repo_root=repo_root)
    if not managed_payload:
        return payload
    managed_actual_backend = (
        dict(managed_payload.get("memory_backend_actual", {}))
        if isinstance(managed_payload.get("memory_backend_actual"), Mapping)
        else {}
    )
    if (
        bool(managed_payload.get("memory_backed_retrieval_ready"))
        and bool(managed_payload.get("memory_local_backend_ready"))
        and str(managed_actual_backend.get("storage", "")).strip() == "lance_local_columnar"
        and str(managed_actual_backend.get("sparse_recall", "")).strip() == "tantivy_sparse_recall"
    ):
        return managed_payload
    return payload


def _run_live_adoption_proof(
    *,
    repo_root: Path,
    scenarios: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    proof_rows = _live_adoption_proof_scenarios(scenarios=scenarios)
    results: list[dict[str, Any]] = []
    timeout_seconds = _adoption_proof_timeout_seconds()
    attempted_sample_count = 0
    degraded_samples: list[dict[str, Any]] = []
    with _benchmark_proof_daemon(repo_root):
        for index, (operation, scenario) in enumerate(proof_rows, start=1):
            sample_id = f"{index:02d}-{str(scenario.get('scenario_id', '')).strip() or operation}"
            request_payload = _proof_request_from_scenario(
                scenario=scenario,
                operation=operation,
                sample_id=sample_id,
            )
            attempted_sample_count += 1
            try:
                summary = _bounded_orchestration_summary(
                    request_payload=request_payload,
                    repo_root=repo_root,
                    mode="odylith_on",
                    timeout_seconds=timeout_seconds,
                )
            except _BenchmarkAdoptionProofTimeout as error:
                degraded_samples.append(
                    {
                        "sample_id": sample_id,
                        "operation": operation,
                        "reason": "timeout",
                        "message": str(error).strip(),
                    }
                )
                break
            except Exception as error:
                degraded_samples.append(
                    {
                        "sample_id": sample_id,
                        "operation": operation,
                        "reason": "error",
                        "message": f"{error.__class__.__name__}: {str(error).strip()}".strip(": "),
                    }
                )
                break
            _persist_adoption_proof_ledger(
                repo_root=repo_root,
                sample_id=sample_id,
                request_payload=request_payload,
                summary=summary,
            )
            adoption = dict(summary.get("odylith_adoption", {})) if isinstance(summary.get("odylith_adoption"), Mapping) else {}
            results.append(adoption)

    degradation_reason_distribution: dict[str, int] = {}
    for row in degraded_samples:
        reason = str(row.get("reason", "")).strip() or "error"
        degradation_reason_distribution[reason] = degradation_reason_distribution.get(reason, 0) + 1

    def _rate(field_name: str) -> float:
        if not results:
            return 0.0
        return round(sum(1 for row in results if bool(row.get(field_name))) / max(1, len(results)), 3)

    payload = {
        "planned_sample_size": len(proof_rows),
        "attempted_sample_count": attempted_sample_count,
        "sample_size": len(results),
        "packet_present_rate": _rate("packet_present"),
        "auto_grounded_rate": _rate("auto_grounding_applied"),
        "route_ready_rate": _rate("route_ready"),
        "native_spawn_ready_rate": _rate("native_spawn_ready"),
        "requires_widening_rate": _rate("requires_widening"),
        "grounded_delegate_rate": _rate("grounded_delegate"),
        "workspace_daemon_reused_rate": _rate("workspace_daemon_reused"),
        "session_namespaced_rate": _rate("session_namespaced"),
        "sample_timeout_seconds": timeout_seconds,
        "degraded": bool(degraded_samples),
        "timed_out_sample_count": degradation_reason_distribution.get("timeout", 0),
        "failed_sample_count": degradation_reason_distribution.get("error", 0),
        "aborted_sample_count": max(0, len(proof_rows) - attempted_sample_count),
        "degradation_reason_distribution": degradation_reason_distribution,
        "degraded_samples": degraded_samples[:3],
        "operation_distribution": _orchestration_adoption_distribution(
            [{"orchestration": {"odylith_adoption": row}} for row in results],
            field_name="operation",
        ),
        "grounding_source_distribution": _orchestration_adoption_distribution(
            [{"orchestration": {"odylith_adoption": row}} for row in results],
            field_name="grounding_source",
        ),
        "runtime_source_distribution": _orchestration_adoption_distribution(
            [{"orchestration": {"odylith_adoption": row}} for row in results],
            field_name="runtime_source",
        ),
    }
    if int(payload.get("sample_size", 0) or 0) > 0:
        store.persist_orchestration_adoption_snapshot(
            repo_root=repo_root,
            snapshot=payload,
            source="benchmark_live_adoption_proof",
        )
    return payload


def _runtime_posture_python_candidates(*, repo_root: Path) -> list[Path]:
    root = Path(repo_root).resolve()
    rows = [
        root / ".odylith" / "runtime" / "current" / "bin" / "python",
        root / ".venv" / "bin" / "python",
    ]
    deduped: list[Path] = []
    seen: set[str] = set()
    for candidate in rows:
        token = str(candidate.resolve()) if candidate.exists() else str(candidate)
        if token in seen:
            continue
        seen.add(token)
        deduped.append(candidate)
    return deduped


def _managed_runtime_posture_summary(*, repo_root: Path) -> dict[str, Any] | None:
    if os.environ.get(_RUNTIME_POSTURE_MANAGED_HELPER_ENV) == "1":
        return None
    root = Path(repo_root).resolve()
    current_python = Path(sys.executable).resolve()
    script = (
        "import json\n"
        "from pathlib import Path\n"
        "from odylith.runtime.evaluation import odylith_benchmark_runner as runner\n"
        f"print(json.dumps(runner._runtime_posture_summary(repo_root=Path({str(root)!r})), sort_keys=True))\n"
    )
    for candidate in _runtime_posture_python_candidates(repo_root=root):
        if not candidate.is_file():
            continue
        with contextlib.suppress(OSError):
            if candidate.resolve() == current_python:
                continue
        env = os.environ.copy()
        existing_pythonpath = str(env.get("PYTHONPATH", "")).strip()
        env["PYTHONPATH"] = os.pathsep.join(
            token
            for token in [str((root / "src").resolve()), existing_pythonpath]
            if token
        )
        env[_RUNTIME_POSTURE_MANAGED_HELPER_ENV] = "1"
        completed = subprocess.run(  # noqa: S603
            [str(candidate), "-c", script],
            cwd=root,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0:
            continue
        output = str(completed.stdout or "").strip().splitlines()
        if not output:
            continue
        with contextlib.suppress(json.JSONDecodeError):
            payload = json.loads(output[-1])
            if isinstance(payload, Mapping):
                return dict(payload)
    return None


def _prime_benchmark_runtime_cache(*, repo_root: Path) -> None:
    root = Path(repo_root).resolve()
    store.warm_projections(repo_root=root, reason="benchmark", scope="full")
    store.prime_reasoning_projection_cache(repo_root=root)
    guidance_catalog = store.tooling_guidance_catalog.load_guidance_catalog(repo_root=root)
    guidance_chunk_count = int(guidance_catalog.get("chunk_count", 0) or 0)
    guidance_source_doc_count = int(guidance_catalog.get("source_doc_count", 0) or 0)
    guidance_task_family_count = int(guidance_catalog.get("task_family_count", 0) or 0)
    if guidance_chunk_count <= 0 or guidance_source_doc_count <= 0 or guidance_task_family_count <= 0:
        raise RuntimeError(
            "Benchmark warm cache requires a populated guidance catalog before proof runs."
        )
    store._judgment_memory_snapshot_cached(repo_root=root)  # noqa: SLF001
    store._git_branch_name(repo_root=root)  # noqa: SLF001
    store._git_head_oid(repo_root=root)  # noqa: SLF001
    memory_snapshot = store.load_runtime_memory_snapshot(repo_root=root)
    backend_transition = (
        dict(memory_snapshot.get("backend_transition", {}))
        if isinstance(memory_snapshot.get("backend_transition"), Mapping)
        else {}
    )
    actual_backend = (
        dict(backend_transition.get("actual_local_backend", {}))
        if isinstance(backend_transition.get("actual_local_backend"), Mapping)
        else {}
    )
    local_backend_status = (
        dict(backend_transition.get("local_backend_status", {}))
        if isinstance(backend_transition.get("local_backend_status"), Mapping)
        else {}
    )
    entity_counts = (
        dict(memory_snapshot.get("entity_counts", {}))
        if isinstance(memory_snapshot.get("entity_counts"), Mapping)
        else {}
    )
    if not (
        bool(local_backend_status.get("ready"))
        and str(actual_backend.get("storage", "")).strip() == "lance_local_columnar"
        and str(actual_backend.get("sparse_recall", "")).strip() == "tantivy_sparse_recall"
        and int(entity_counts.get("indexed_entity_count", 0) or 0) > 0
        and int(entity_counts.get("evidence_documents", 0) or 0) > 0
    ):
        raise RuntimeError(
            "Benchmark warm cache requires an active local LanceDB/Tantivy memory substrate before proof runs."
        )
    cache_until = time.monotonic() + _BENCHMARK_WARM_CACHE_SECONDS
    full_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="full")
    reasoning_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="reasoning")
    default_fingerprint = store.projection_input_fingerprint(repo_root=root, scope="default")
    store._PROCESS_WARM_CACHE[f"{root}:full"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:full"] = full_fingerprint  # noqa: SLF001
    store._PROCESS_WARM_CACHE[f"{root}:reasoning"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:reasoning"] = reasoning_fingerprint  # noqa: SLF001
    store._PROCESS_WARM_CACHE[f"{root}:default"] = cache_until  # noqa: SLF001
    store._PROCESS_WARM_CACHE_FINGERPRINTS[f"{root}:default"] = default_fingerprint  # noqa: SLF001


def _normalize_cache_profiles(cache_profiles: Sequence[str]) -> list[str]:
    normalized = [str(token).strip().lower() for token in cache_profiles if str(token).strip().lower() in _VALID_CACHE_PROFILES]
    if not normalized:
        normalized = list(DEFAULT_CACHE_PROFILES)
    ordered: list[str] = []
    seen: set[str] = set()
    for token in normalized:
        if token in seen:
            continue
        seen.add(token)
        ordered.append(token)
    return ordered


def _primary_cache_profile(cache_profiles: Sequence[str]) -> str:
    normalized = _normalize_cache_profiles(cache_profiles)
    return "warm" if "warm" in normalized else normalized[0]


def _prepare_benchmark_runtime_cache(*, repo_root: Path, cache_profile: str) -> None:
    profile = str(cache_profile or "warm").strip().lower() or "warm"
    store.clear_runtime_process_caches(repo_root=repo_root)
    if profile == "warm":
        _prime_benchmark_runtime_cache(repo_root=repo_root)


def _benchmark_report_id(
    *,
    generated_utc: str,
    modes: Sequence[str],
    scenario_ids: Sequence[str],
    cache_profiles: Sequence[str],
) -> str:
    return hashlib.sha256(
        json.dumps(
            {
                "generated_utc": generated_utc,
                "modes": [str(token).strip() for token in modes if str(token).strip()],
                "scenario_ids": [str(token).strip() for token in scenario_ids if str(token).strip()],
                "cache_profiles": [str(token).strip() for token in cache_profiles if str(token).strip()],
            },
            sort_keys=True,
            ensure_ascii=False,
        ).encode("utf-8")
    ).hexdigest()[:16]


def _write_progress(
    *,
    repo_root: Path,
    payload: Mapping[str, Any],
    write_shared: bool = True,
) -> None:
    root = Path(repo_root).resolve()
    _sync_active_run_progress(repo_root=root, payload=payload)
    if not write_shared:
        return
    odylith_context_cache.write_json_if_changed(
        repo_root=root,
        path=progress_report_path(repo_root=root),
        payload=dict(payload),
        lock_key=str(progress_report_path(repo_root=root)),
    )


def _clear_progress(*, repo_root: Path) -> None:
    path = progress_report_path(repo_root=repo_root)
    with odylith_context_cache.advisory_lock(repo_root=repo_root, key=str(path)):
        if path.exists():
            path.unlink()


def _failed_benchmark_report(
    *,
    repo_root: Path,
    report_id: str,
    benchmark_profile: str,
    comparison_contract: str,
    modes: Sequence[str],
    cache_profiles: Sequence[str],
    primary_cache_profile: str,
    scenarios: Sequence[Mapping[str, Any]],
    all_scenarios: Sequence[Mapping[str, Any]],
    progress_payload: Mapping[str, Any],
    selection_strategy: str,
    latest_eligible: bool,
    startup_hygiene: Mapping[str, Any],
    corpus_contract: Mapping[str, Any],
    tree_identity: Mapping[str, Any],
    error: BaseException | str,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    normalized_profile = _normalize_benchmark_profile(benchmark_profile)
    error_text = _benchmark_exception_text(error)
    generated_utc = str(progress_payload.get("updated_utc", "")).strip() or _utc_now()
    acceptance = {
        "status": "failed",
        "hard_quality_gate_cleared": False,
        "secondary_guardrails_cleared": False,
        "advisory_checks_cleared": False,
        "checks": {
            "benchmark_run_completed": False,
        },
        "hard_gate_failures": ["benchmark_run_completed"],
        "hard_gate_failure_labels": [error_text],
        "secondary_guardrail_failures": [],
        "secondary_guardrail_failure_labels": [],
        "advisory_failures": [],
        "advisory_failure_labels": [],
        "weak_families": [],
        "advisory_families": [],
        "notes": [f"Benchmark run aborted before report completion: {error_text}"],
    }
    report: dict[str, Any] = {
        "contract": REPORT_CONTRACT,
        "version": REPORT_VERSION,
        "report_id": str(report_id).strip(),
        "repo_root": str(root),
        "benchmark_profile": normalized_profile,
        "benchmark_profile_label": _benchmark_profile_label(normalized_profile),
        "benchmark_profile_description": _benchmark_profile_description(normalized_profile),
        "comparison_contract": str(comparison_contract).strip(),
        "comparison_contract_details": _comparison_contract_details(str(comparison_contract).strip()),
        "generated_utc": generated_utc,
        "started_utc": str(progress_payload.get("started_utc", "")).strip() or generated_utc,
        "modes": list(modes),
        "cache_profiles": list(cache_profiles),
        "primary_cache_profile": str(primary_cache_profile).strip() or "warm",
        "selection_strategy": str(selection_strategy).strip() or "manual_selection",
        "product_version": _product_version_from_pyproject(repo_root=root),
        "corpus_path": str(store.optimization_evaluation_corpus_path(repo_root=root)),
        "git_branch": str(tree_identity.get("git_branch", "")).strip(),
        "git_commit": str(tree_identity.get("git_commit", "")).strip(),
        "git_dirty": bool(tree_identity.get("git_dirty")),
        "repo_dirty_paths": [
            str(token).strip()
            for token in tree_identity.get("repo_dirty_paths", [])
            if isinstance(tree_identity.get("repo_dirty_paths"), list) and str(token).strip()
        ],
        "selection_fingerprint": str(tree_identity.get("selection_fingerprint", "")).strip(),
        "corpus_fingerprint": str(tree_identity.get("corpus_fingerprint", "")).strip(),
        "snapshot_overlay_fingerprint": str(tree_identity.get("snapshot_overlay_fingerprint", "")).strip(),
        "snapshot_overlay_paths": [],
        "source_posture": str(tree_identity.get("source_posture", "")).strip(),
        "scenario_count": len(scenarios),
        "selection": dict(progress_payload.get("selection", {}))
        if isinstance(progress_payload.get("selection"), Mapping)
        else {},
        "latest_eligible": bool(latest_eligible),
        "scenarios": [],
        "published_scenarios": [],
        "cache_profile_scenarios": {},
        "cache_profile_summaries": {},
        "cache_profile_reports": {},
        "cache_profile_mode_rows": {},
        "singleton_family_latency_probes": {},
        "mode_summaries": {},
        "published_mode_summaries": {},
        "published_mode_table": {},
        "published_mode_table_markdown": _published_mode_table_markdown({}),
        "published_pair_timing_summary": {},
        "full_pair_timing_summary": {},
        "tracked_mode_table": {},
        "tracked_mode_table_markdown": _published_mode_table_markdown({}),
        "family_summaries": {},
        "published_family_summaries": {},
        "packet_source_summaries": {},
        "published_packet_source_summaries": {},
        "execution_contracts": {},
        "family_deltas": {},
        "published_family_deltas": {},
        "packet_source_deltas": {},
        "published_packet_source_deltas": {},
        "primary_comparison": {},
        "published_comparison": {},
        "comparison": {},
        "adoption_proof": {},
        "runtime_posture": {},
        "startup_hygiene": dict(startup_hygiene),
        "final_hygiene": {},
        "robustness_summary": {},
        "corpus_contract": dict(corpus_contract),
        "corpus_composition": _corpus_composition(
            scenarios=scenarios,
            available_scenarios=all_scenarios,
        ),
        "fairness_contract_passed": True,
        "fairness_findings": [],
        "observed_path_sources": [],
        "preflight_evidence_mode": "none",
        "preflight_evidence_commands": [],
        "preflight_evidence_result_status": "not_applicable",
        "preflight_evidence_modes": [],
        "status": "failed",
        "acceptance": acceptance,
        "error": error_text,
    }
    report["published_summary"] = compact_report_summary(report)
    report["summary_text"] = _render_report_summary(report)
    return report


def _family_summaries(
    *,
    modes: Sequence[str],
    mode_rows: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, dict[str, dict[str, Any]]]:
    family_names = sorted(
        {
            str(row.get("scenario_family", "")).strip()
            for rows in mode_rows.values()
            for row in rows
            if str(row.get("scenario_family", "")).strip()
        }
    )
    summaries: dict[str, dict[str, dict[str, Any]]] = {}
    for family in family_names:
        summaries[family] = {}
        for mode in modes:
            family_rows = [
                row
                for row in mode_rows.get(mode, [])
                if str(row.get("scenario_family", "")).strip() == family
            ]
            summaries[family][mode] = _mode_summary(mode=mode, scenario_rows=family_rows)
    return summaries


def _summary_comparison(
    *,
    candidate_mode: str,
    baseline_mode: str,
    mode_summaries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    candidate_payload = _lookup_mode_mapping(mode_summaries, candidate_mode)
    baseline_payload = _lookup_mode_mapping(mode_summaries, baseline_mode)
    candidate = dict(candidate_payload) if isinstance(candidate_payload, Mapping) else {}
    baseline = dict(baseline_payload) if isinstance(baseline_payload, Mapping) else {}
    comparison = {
        "candidate_mode": _public_mode_name(candidate_mode),
        "baseline_mode": _public_mode_name(baseline_mode),
        "median_latency_delta_ms": round(
            float(candidate.get("median_latency_ms", 0.0) or 0.0) - float(baseline.get("median_latency_ms", 0.0) or 0.0),
            3,
        ),
        "avg_latency_delta_ms": round(
            float(candidate.get("avg_latency_ms", 0.0) or 0.0) - float(baseline.get("avg_latency_ms", 0.0) or 0.0),
            3,
        ),
        "p95_latency_delta_ms": round(
            float(candidate.get("p95_latency_ms", 0.0) or 0.0) - float(baseline.get("p95_latency_ms", 0.0) or 0.0),
            3,
        ),
        "median_initial_prompt_token_delta": round(
            float(candidate.get("median_initial_prompt_tokens", 0.0) or 0.0)
            - float(baseline.get("median_initial_prompt_tokens", 0.0) or 0.0),
            3,
        ),
        "median_token_delta": round(
            float(candidate.get("median_effective_tokens", 0.0) or 0.0) - float(baseline.get("median_effective_tokens", 0.0) or 0.0),
            3,
        ),
        "median_prompt_token_delta": round(
            float(candidate.get("median_effective_tokens", 0.0) or 0.0)
            - float(baseline.get("median_effective_tokens", 0.0) or 0.0),
            3,
        ),
        "median_total_payload_token_delta": round(
            float(candidate.get("median_total_payload_tokens", 0.0) or 0.0)
            - float(baseline.get("median_total_payload_tokens", 0.0) or 0.0),
            3,
        ),
        "median_runtime_contract_token_delta": round(
            float(candidate.get("median_runtime_contract_tokens", 0.0) or 0.0)
            - float(baseline.get("median_runtime_contract_tokens", 0.0) or 0.0),
            3,
        ),
        "median_operator_diag_token_delta": round(
            float(candidate.get("median_operator_diag_tokens", 0.0) or 0.0)
            - float(baseline.get("median_operator_diag_tokens", 0.0) or 0.0),
            3,
        ),
        "median_observed_path_count_delta": round(
            float(candidate.get("median_observed_path_count", 0.0) or 0.0)
            - float(baseline.get("median_observed_path_count", 0.0) or 0.0),
            3,
        ),
        "median_candidate_write_path_count_delta": round(
            float(candidate.get("median_candidate_write_path_count", 0.0) or 0.0)
            - float(baseline.get("median_candidate_write_path_count", 0.0) or 0.0),
            3,
        ),
        "median_selected_doc_count_delta": round(
            float(candidate.get("median_selected_doc_count", 0.0) or 0.0)
            - float(baseline.get("median_selected_doc_count", 0.0) or 0.0),
            3,
        ),
        "median_selected_command_count_delta": round(
            float(candidate.get("median_selected_command_count", 0.0) or 0.0)
            - float(baseline.get("median_selected_command_count", 0.0) or 0.0),
            3,
        ),
        "required_path_recall_delta": round(
            float(candidate.get("required_path_recall_rate", 0.0) or 0.0) - float(baseline.get("required_path_recall_rate", 0.0) or 0.0),
            3,
        ),
        "required_path_precision_delta": round(
            float(candidate.get("required_path_precision_rate", 0.0) or 0.0)
            - float(baseline.get("required_path_precision_rate", 0.0) or 0.0),
            3,
        ),
        "hallucinated_surface_rate_delta": round(
            float(candidate.get("hallucinated_surface_rate", 0.0) or 0.0)
            - float(baseline.get("hallucinated_surface_rate", 0.0) or 0.0),
            3,
        ),
        "validation_success_delta": round(
            float(candidate.get("validation_success_rate", 0.0) or 0.0) - float(baseline.get("validation_success_rate", 0.0) or 0.0),
            3,
        ),
        "write_surface_precision_delta": round(
            float(candidate.get("write_surface_precision_rate", 0.0) or 0.0)
            - float(baseline.get("write_surface_precision_rate", 0.0) or 0.0),
            3,
        ),
        "unnecessary_widening_rate_delta": round(
            float(candidate.get("unnecessary_widening_rate", 0.0) or 0.0)
            - float(baseline.get("unnecessary_widening_rate", 0.0) or 0.0),
            3,
        ),
        "critical_required_path_recall_delta": round(
            float(candidate.get("critical_required_path_recall_rate", 0.0) or 0.0)
            - float(baseline.get("critical_required_path_recall_rate", 0.0) or 0.0),
            3,
        ),
        "critical_validation_success_delta": round(
            float(candidate.get("critical_validation_success_rate", 0.0) or 0.0)
            - float(baseline.get("critical_validation_success_rate", 0.0) or 0.0),
            3,
        ),
        "expectation_success_delta": round(
            float(candidate.get("expectation_success_rate", 0.0) or 0.0) - float(baseline.get("expectation_success_rate", 0.0) or 0.0),
            3,
        ),
        "route_ready_validation_success_delta": round(
            float(candidate.get("route_ready_validation_success_rate", 0.0) or 0.0)
            - float(baseline.get("route_ready_validation_success_rate", 0.0) or 0.0),
            3,
        ),
        "route_ready_expectation_success_delta": round(
            float(candidate.get("route_ready_expectation_success_rate", 0.0) or 0.0)
            - float(baseline.get("route_ready_expectation_success_rate", 0.0) or 0.0),
            3,
        ),
    }
    comparison.update(
        odylith_benchmark_proof_discipline.comparison(
            candidate=candidate,
            baseline=baseline,
        )
    )
    comparison.update(
        odylith_benchmark_context_engine.comparison(
            candidate=candidate,
            baseline=baseline,
        )
    )
    comparison.update(
        odylith_benchmark_execution_engine.comparison(
            candidate=candidate,
            baseline=baseline,
        )
    )
    return comparison


def _primary_comparison(
    *,
    candidate_mode: str,
    baseline_mode: str,
    mode_summaries: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    return _summary_comparison(
        candidate_mode=candidate_mode,
        baseline_mode=baseline_mode,
        mode_summaries=mode_summaries,
    )


def _family_deltas(
    *,
    candidate_mode: str,
    baseline_mode: str,
    family_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]],
) -> dict[str, dict[str, Any]]:
    deltas: dict[str, dict[str, Any]] = {}
    for family, summaries in family_summaries.items():
        if not isinstance(summaries, Mapping):
            continue
        comparison = _summary_comparison(
            candidate_mode=candidate_mode,
            baseline_mode=baseline_mode,
            mode_summaries=summaries,
        )
        candidate_payload = _lookup_mode_mapping(summaries, candidate_mode)
        candidate = dict(candidate_payload) if isinstance(candidate_payload, Mapping) else {}
        comparison.update(
            {
                "family": str(family).strip(),
                "scenario_count": int(candidate.get("scenario_count", 0) or 0),
                "correctness_critical_scenario_count": int(
                    candidate.get("correctness_critical_scenario_count", 0) or 0
                ),
            }
        )
        deltas[str(family).strip()] = comparison
    return deltas

def _human_duration_label(milliseconds: float) -> str:
    ms = abs(float(milliseconds or 0.0))
    seconds = ms / 1000.0
    if seconds >= 3600.0:
        hours = int(seconds // 3600.0)
        minutes = int((seconds % 3600.0) // 60.0)
        return f"{hours}h {minutes:02d}m"
    if seconds >= 60.0:
        minutes = int(seconds // 60.0)
        remaining_seconds = int(round(seconds - (minutes * 60.0)))
        if remaining_seconds == 60:
            minutes += 1
            remaining_seconds = 0
        return f"{minutes}m {remaining_seconds:02d}s"
    if seconds >= 10.0:
        return f"{int(round(seconds))}s"
    if seconds >= 1.0:
        return f"{seconds:.2f}s"
    if ms >= 1.0:
        return f"{int(round(ms))} ms"
    return f"{ms:.3f} ms"


def _human_number_label(value: float) -> str:
    number = float(value or 0.0)
    if abs(number - round(number)) < 1e-9:
        return f"{int(round(number)):,}"
    return f"{number:,.1f}"


def _humanized_proof_table_enabled(comparison_contract: str) -> bool:
    return _is_live_comparison_contract(comparison_contract)


def _format_mode_table_value(*, field: str, value: Any, comparison_contract: str = "") -> str:
    if _humanized_proof_table_enabled(comparison_contract) and field.endswith("_ms"):
        return _human_duration_label(float(value or 0.0))
    if _humanized_proof_table_enabled(comparison_contract) and "tokens" in field:
        return _human_number_label(float(value or 0.0))
    if field.endswith("_ms"):
        return f"{float(value or 0.0):.3f} ms"
    if "tokens" in field:
        return f"{float(value or 0.0):.1f}"
    if field.endswith("_count"):
        return f"{int(value or 0)}"
    return f"{float(value or 0.0):.3f}"


def _format_mode_table_delta(
    *,
    field: str,
    candidate_value: Any,
    baseline_value: Any,
    comparison_contract: str = "",
) -> str:
    if field == "lane_role":
        return "full Odylith vs raw agent"
    delta = float(candidate_value or 0.0) - float(baseline_value or 0.0)
    if _humanized_proof_table_enabled(comparison_contract) and field.endswith("_ms"):
        human_abs = _human_duration_label(delta)
        formatted = f"{'+' if delta >= 0.0 else '-'}{human_abs}"
    elif _humanized_proof_table_enabled(comparison_contract) and "tokens" in field:
        human_abs = _human_number_label(abs(delta))
        formatted = f"{'+' if delta >= 0.0 else '-'}{human_abs}"
    elif field.endswith("_ms"):
        formatted = f"{delta:+.3f} ms"
    elif "tokens" in field:
        formatted = f"{delta:+.1f}"
    elif field.endswith("_count"):
        formatted = f"{int(round(delta)):+d}"
    else:
        formatted = f"{delta:+.3f}"
    if field in _LOWER_BETTER_SUMMARY_FIELDS:
        if delta < 0.0:
            return f'<strong style="color:#137333;">{formatted}</strong>'
        if delta > 0.0:
            return f'<span style="color:#c5221f;">{formatted}</span>'
        return formatted
    if field in _HIGHER_BETTER_SUMMARY_FIELDS:
        if delta > 0.0:
            return f'<strong style="color:#137333;">{formatted}</strong>'
        if delta < 0.0:
            return f'<span style="color:#c5221f;">{formatted}</span>'
        return formatted
    if field.endswith("_ms"):
        return f'<span style="color:#c5221f;">{formatted}</span>' if delta > 0.0 else formatted
    return formatted


def _published_mode_table(
    *,
    mode_summaries: Mapping[str, Mapping[str, Any]],
    mode_order: Sequence[str],
    candidate_mode: str = "",
    baseline_mode: str = "",
    comparison_contract: str = "",
) -> dict[str, Any]:
    ordered_modes = [mode for mode in mode_order if isinstance(_lookup_mode_mapping(mode_summaries, mode), Mapping)]
    candidate_summary_payload = _lookup_mode_mapping(mode_summaries, candidate_mode) if candidate_mode else {}
    baseline_summary_payload = _lookup_mode_mapping(mode_summaries, baseline_mode) if baseline_mode else {}
    candidate_summary = dict(candidate_summary_payload) if isinstance(candidate_summary_payload, Mapping) else {}
    baseline_summary = dict(baseline_summary_payload) if isinstance(baseline_summary_payload, Mapping) else {}
    include_delta_columns = bool(candidate_summary and baseline_summary)
    labels = _comparison_contract_label_bundle(comparison_contract)
    rows: list[dict[str, Any]] = []
    row_specs = (
        ("lane_role", "Lane role"),
        ("scenario_count", "Scenario count"),
        ("median_latency_ms", labels["latency_median"]),
        ("avg_latency_ms", labels["latency_avg"]),
        ("p95_latency_ms", labels["latency_p95"]),
        ("median_instrumented_reasoning_duration_ms", labels["instrumented"]),
        ("median_uninstrumented_overhead_ms", labels["overhead"]),
        ("median_effective_tokens", labels["effective_tokens"]),
        ("median_total_payload_tokens", labels["total_payload_tokens"]),
        ("required_path_recall_rate", "Required-path recall rate"),
        ("required_path_precision_rate", "Required-path precision rate"),
        ("hallucinated_surface_rate", "Hallucinated-surface rate"),
        ("validation_success_rate", labels["validation_label"]),
        ("critical_required_path_recall_rate", "Critical required-path recall rate"),
        ("critical_validation_success_rate", labels["critical_validation_label"]),
        ("expectation_success_rate", labels["expectation_label"]),
    )
    for field, label in row_specs:
        values: dict[str, str] = {}
        for mode in ordered_modes:
            public_name = _public_mode_name(mode)
            if field == "lane_role":
                values[public_name] = _MODE_ROLES.get(mode, public_name)
                continue
            summary_payload = _lookup_mode_mapping(mode_summaries, mode)
            summary = dict(summary_payload) if isinstance(summary_payload, Mapping) else {}
            values[public_name] = _format_mode_table_value(
                field=field,
                value=summary.get(field, 0.0),
                comparison_contract=comparison_contract,
            )
        row_payload = {"metric": field, "label": label, "values": values}
        if include_delta_columns:
            why_it_matters = _PUBLISHED_TABLE_WHY_IT_MATTERS.get(field, "")
            if field == "lane_role":
                why_it_matters = labels["lane_role_why"]
            elif field == "scenario_count":
                why_it_matters = labels["scenario_count_why"]
            elif field == "median_latency_ms":
                why_it_matters = labels["latency_why"]
            elif field == "avg_latency_ms":
                why_it_matters = labels["latency_avg_why"]
            elif field == "p95_latency_ms":
                why_it_matters = labels["latency_p95_why"]
            elif field == "median_instrumented_reasoning_duration_ms":
                why_it_matters = labels["instrumented_why"]
            elif field == "median_uninstrumented_overhead_ms":
                why_it_matters = labels["overhead_why"]
            elif field == "median_effective_tokens":
                why_it_matters = labels["effective_tokens_why"]
            elif field == "median_total_payload_tokens":
                why_it_matters = labels["total_payload_tokens_why"]
            elif field == "validation_success_rate":
                why_it_matters = labels["validation_why"]
            elif field == "critical_validation_success_rate":
                why_it_matters = labels["critical_validation_why"]
            elif field == "expectation_success_rate":
                why_it_matters = labels["expectation_why"]
            row_payload["delta"] = _format_mode_table_delta(
                field=field,
                candidate_value=candidate_summary.get(field, _MODE_ROLES.get(candidate_mode, "")),
                baseline_value=baseline_summary.get(field, _MODE_ROLES.get(baseline_mode, "")),
                comparison_contract=comparison_contract,
            )
            row_payload["why_it_matters"] = why_it_matters
        rows.append(row_payload)
    return {
        "mode_order": [_public_mode_name(mode) for mode in ordered_modes],
        "display_mode_order": [_table_header_mode_name(mode) for mode in ordered_modes],
        "delta_header": "Delta" if include_delta_columns else "",
        "why_it_matters_header": "Why It Matters" if include_delta_columns else "",
        "rows": rows,
    }


def _published_mode_table_markdown(table: Mapping[str, Any]) -> str:
    mode_order = [str(token).strip() for token in table.get("mode_order", []) if str(token).strip()]
    if not mode_order:
        return ""
    display_mode_order = [str(token).strip() for token in table.get("display_mode_order", []) if str(token).strip()]
    if len(display_mode_order) != len(mode_order):
        display_mode_order = list(mode_order)
    delta_header = str(table.get("delta_header", "")).strip()
    why_header = str(table.get("why_it_matters_header", "")).strip()
    trailing_headers = [token for token in (delta_header, why_header) if token]
    header = "| Signal | " + " | ".join([*display_mode_order, *trailing_headers]) + " |"
    separator = "| --- | " + " | ".join("---" for _ in [*mode_order, *trailing_headers]) + " |"
    body: list[str] = [header, separator]
    for row in table.get("rows", []):
        if not isinstance(row, Mapping):
            continue
        label = str(row.get("label", "")).strip()
        values = dict(row.get("values", {})) if isinstance(row.get("values"), Mapping) else {}
        cells = [label, *(str(values.get(mode, "")).strip() for mode in mode_order)]
        if delta_header:
            cells.append(str(row.get("delta", "")).strip())
        if why_header:
            cells.append(str(row.get("why_it_matters", "")).strip())
        body.append("| " + " | ".join(cells) + " |")
    return "\n".join(body)


def _metric_spread(
    *,
    cache_profile_summaries: Mapping[str, Mapping[str, Any]],
    mode: str,
    field: str,
) -> float:
    values: list[float] = []
    for summary in cache_profile_summaries.values():
        if not isinstance(summary, Mapping):
            continue
        mode_summaries = dict(summary.get("mode_summaries", {})) if isinstance(summary.get("mode_summaries"), Mapping) else {}
        mode_summary_payload = _lookup_mode_mapping(mode_summaries, mode)
        mode_summary = dict(mode_summary_payload) if isinstance(mode_summary_payload, Mapping) else {}
        if field not in mode_summary:
            continue
        values.append(float(mode_summary.get(field, 0.0) or 0.0))
    if not values:
        return 0.0
    return round(max(values) - min(values), 3)


def _robustness_summary(
    *,
    cache_profile_summaries: Mapping[str, Mapping[str, Any]],
    candidate_mode: str,
    latency_probes: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    profiles = [
        str(profile).strip()
        for profile in cache_profile_summaries.keys()
        if str(profile).strip()
    ]
    passed = [
        _acceptance_hard_quality_gate_cleared(dict(summary.get("acceptance", {})))
        for summary in cache_profile_summaries.values()
        if isinstance(summary, Mapping)
    ]
    probe_rows = [
        dict(probe)
        for probe in dict(latency_probes or {}).values()
        if isinstance(probe, Mapping)
    ]
    mode_probe_rows = [
        dict(summary)
        for probe in probe_rows
        for summary in dict(probe.get("modes", {})).values()
        if isinstance(probe.get("modes"), Mapping) and isinstance(summary, Mapping)
    ]
    latency_stability_results = [bool(row.get("latency_stability_cleared")) for row in mode_probe_rows]
    quality_consistency_results = [bool(row.get("quality_consistency_cleared")) for row in mode_probe_rows]
    rerun_state = "not_measured"
    if mode_probe_rows:
        rerun_state = "measured_pass" if all(latency_stability_results) else "measured_attention"
    return {
        "selected_cache_profile_count": len(profiles),
        "selected_cache_profiles": profiles,
        "selected_cache_profile_pass_rate": _rate(passed),
        "warm_cold_consistency_cleared": bool(passed) and all(passed),
        "candidate_latency_spread_ms": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="median_latency_ms",
        ),
        "candidate_prompt_token_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="median_effective_tokens",
        ),
        "candidate_required_path_recall_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="required_path_recall_rate",
        ),
        "candidate_required_path_precision_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="required_path_precision_rate",
        ),
        "candidate_validation_success_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="validation_success_rate",
        ),
        "candidate_expectation_success_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="expectation_success_rate",
        ),
        "candidate_write_surface_precision_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="write_surface_precision_rate",
        ),
        "candidate_hallucinated_surface_rate_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="hallucinated_surface_rate",
        ),
        "candidate_unnecessary_widening_rate_spread": _metric_spread(
            cache_profile_summaries=cache_profile_summaries,
            mode=candidate_mode,
            field="unnecessary_widening_rate",
        ),
        "rerun_stability_state": rerun_state,
        "rerun_probe_family_count": len(
            {
                str(probe.get("family", "")).strip()
                for probe in probe_rows
                if str(probe.get("family", "")).strip()
            }
        ),
        "rerun_probe_scenario_count": len(
            {
                str(probe.get("scenario_id", "")).strip()
                for probe in probe_rows
                if str(probe.get("scenario_id", "")).strip()
            }
        ),
        "rerun_probe_mode_count": len(mode_probe_rows),
        "rerun_probe_sample_count": sum(int(row.get("sample_count", 0) or 0) for row in mode_probe_rows),
        "rerun_probe_latency_pass_rate": _rate(latency_stability_results),
        "rerun_probe_quality_consistency_pass_rate": _rate(quality_consistency_results),
        "rerun_probe_worst_latency_spread_ms": max(
            (float(row.get("latency_probe_spread_ms", 0.0) or 0.0) for row in mode_probe_rows),
            default=0.0,
        ),
        "stale_cache_recovery_state": "not_measured",
        "dirty_worktree_recovery_state": "not_measured",
        "conflicting_governance_recovery_state": "not_measured",
        "partial_failure_recovery_state": "not_measured",
    }


def _all_values_equal(values: Sequence[Any]) -> bool:
    if not values:
        return True
    first = values[0]
    return all(value == first for value in values[1:])


def _singleton_family_counts(*, scenarios: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for scenario in scenarios:
        family = str(scenario.get("family", "")).strip()
        if not family:
            continue
        counts[family] = counts.get(family, 0) + 1
    return counts


def _sensitive_singleton_latency_probe_candidates(
    *,
    scenarios: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for scenario in scenarios:
        family = str(scenario.get("family", "")).strip()
        if family not in _SENSITIVE_SINGLETON_FAMILY_LATENCY_FAMILIES:
            continue
        candidates.append(dict(scenario))
    return candidates


def _latency_probe_summary(
    *,
    mode: str,
    sample_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    latencies = [float(row.get("latency_ms", 0.0) or 0.0) for row in sample_rows]
    instrumented = [float(row.get("instrumented_reasoning_duration_ms", 0.0) or 0.0) for row in sample_rows]
    overhead = [float(row.get("uninstrumented_overhead_ms", 0.0) or 0.0) for row in sample_rows]
    precision = [float(row.get("required_path_precision", 0.0) or 0.0) for row in sample_rows]
    recall = [float(row.get("required_path_recall", 0.0) or 0.0) for row in sample_rows]
    validation = [float(row.get("validation_success_proxy", 0.0) or 0.0) for row in sample_rows]
    expectation = [bool(row.get("expectation_ok")) for row in sample_rows]
    spread = round(max(latencies) - min(latencies), 3) if latencies else 0.0
    quality_consistency = bool(
        _all_values_equal(precision)
        and _all_values_equal(recall)
        and _all_values_equal(validation)
        and _all_values_equal(expectation)
    )
    return {
        "mode": str(mode).strip(),
        "sample_count": len(sample_rows),
        "median_latency_ms": _median(latencies),
        "avg_latency_ms": _avg(latencies),
        "latency_probe_spread_ms": spread,
        "median_instrumented_reasoning_duration_ms": _median(instrumented),
        "avg_instrumented_reasoning_duration_ms": _avg(instrumented),
        "median_uninstrumented_overhead_ms": _median(overhead),
        "avg_uninstrumented_overhead_ms": _avg(overhead),
        "latency_samples_ms": [round(value, 3) for value in latencies],
        "quality_consistency_cleared": quality_consistency,
        "latency_stability_cleared": quality_consistency and spread <= _SENSITIVE_SINGLETON_FAMILY_LATENCY_MAX_SPREAD_MS,
        "latency_measurement_basis": "singleton_rerun_median",
    }


def _singleton_family_latency_probes(
    *,
    repo_root: Path,
    scenarios: Sequence[Mapping[str, Any]],
    modes: Sequence[str],
    cache_profiles: Sequence[str],
    benchmark_profile: str,
) -> dict[str, dict[str, Any]]:
    probes: dict[str, dict[str, Any]] = {}
    candidates = _sensitive_singleton_latency_probe_candidates(scenarios=scenarios)
    if not candidates:
        return probes
    probe_modes = [
        _normalize_mode(str(mode).strip())
        for mode in modes
        if _normalize_mode(str(mode).strip()) in _SENSITIVE_SINGLETON_FAMILY_LATENCY_PROBE_MODES
    ]
    if not probe_modes:
        probe_modes = list(_SENSITIVE_SINGLETON_FAMILY_LATENCY_PROBE_MODES)
    for scenario in candidates:
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        family = str(scenario.get("family", "")).strip()
        if not scenario_id or not family:
            continue
        for cache_profile in cache_profiles:
            profile = str(cache_profile).strip()
            if not profile:
                continue
            probe_key = f"{profile}:{scenario_id}"
            mode_summaries: dict[str, Any] = {}
            for mode in probe_modes:
                normalized_mode = str(mode).strip()
                if not normalized_mode:
                    continue
                sample_rows: list[dict[str, Any]] = []
                for _ in range(_SENSITIVE_SINGLETON_FAMILY_LATENCY_SAMPLE_COUNT):
                    _prepare_benchmark_runtime_cache(repo_root=repo_root, cache_profile=profile)
                    sample_rows.append(
                        _run_scenario_mode(
                            repo_root=repo_root,
                            scenario=scenario,
                            mode=normalized_mode,
                            benchmark_profile=benchmark_profile,
                        )
                    )
                mode_summaries[normalized_mode] = _latency_probe_summary(
                    mode=normalized_mode,
                    sample_rows=sample_rows,
                )
            probes[probe_key] = {
                "scenario_id": scenario_id,
                "family": family,
                "label": str(scenario.get("label", "")).strip(),
                "cache_profile": profile,
                "sample_count": _SENSITIVE_SINGLETON_FAMILY_LATENCY_SAMPLE_COUNT,
                "modes": mode_summaries,
            }
    return probes


def _latency_probe_can_override_reported_latency(
    *,
    reported_latency_ms: Any,
    probe_latency_ms: Any,
) -> bool:
    reported = float(reported_latency_ms or 0.0)
    probe = float(probe_latency_ms or 0.0)
    if reported <= 0.0 or probe <= 0.0:
        return True
    return probe <= max(
        reported * 2.0,
        reported + _SENSITIVE_SINGLETON_FAMILY_LATENCY_MAX_SPREAD_MS,
    )


def _apply_singleton_family_latency_probes(
    *,
    family_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]],
    latency_probes: Mapping[str, Mapping[str, Any]],
    cache_profile: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    updated: dict[str, dict[str, dict[str, Any]]] = {
        str(family).strip(): {
            str(mode).strip(): dict(summary)
            for mode, summary in family_modes.items()
            if str(mode).strip() and isinstance(summary, Mapping)
        }
        for family, family_modes in family_summaries.items()
        if str(family).strip() and isinstance(family_modes, Mapping)
    }
    for probe in latency_probes.values():
        if not isinstance(probe, Mapping):
            continue
        if str(probe.get("cache_profile", "")).strip() != str(cache_profile).strip():
            continue
        family = str(probe.get("family", "")).strip()
        if not family or family not in updated:
            continue
        modes = dict(probe.get("modes", {})) if isinstance(probe.get("modes"), Mapping) else {}
        family_modes = dict(updated.get(family, {}))
        for mode, probe_summary in modes.items():
            target_mode = next((candidate for candidate in _mode_key_candidates(mode) if candidate in family_modes), "")
            if not isinstance(probe_summary, Mapping) or not target_mode:
                continue
            if not bool(probe_summary.get("latency_stability_cleared")):
                continue
            summary = dict(family_modes.get(target_mode, {}))
            if not _latency_probe_can_override_reported_latency(
                reported_latency_ms=summary.get("median_latency_ms", 0.0),
                probe_latency_ms=probe_summary.get("median_latency_ms", 0.0),
            ):
                continue
            summary["median_latency_ms"] = float(probe_summary.get("median_latency_ms", summary.get("median_latency_ms", 0.0)) or 0.0)
            summary["avg_latency_ms"] = float(probe_summary.get("avg_latency_ms", summary.get("avg_latency_ms", 0.0)) or 0.0)
            summary["median_instrumented_reasoning_duration_ms"] = float(
                probe_summary.get(
                    "median_instrumented_reasoning_duration_ms",
                    summary.get("median_instrumented_reasoning_duration_ms", 0.0),
                )
                or 0.0
            )
            summary["avg_instrumented_reasoning_duration_ms"] = float(
                probe_summary.get(
                    "avg_instrumented_reasoning_duration_ms",
                    summary.get("avg_instrumented_reasoning_duration_ms", 0.0),
                )
                or 0.0
            )
            summary["median_uninstrumented_overhead_ms"] = float(
                probe_summary.get(
                    "median_uninstrumented_overhead_ms",
                    summary.get("median_uninstrumented_overhead_ms", 0.0),
                )
                or 0.0
            )
            summary["avg_uninstrumented_overhead_ms"] = float(
                probe_summary.get(
                    "avg_uninstrumented_overhead_ms",
                    summary.get("avg_uninstrumented_overhead_ms", 0.0),
                )
                or 0.0
            )
            summary["latency_probe_sample_count"] = int(probe_summary.get("sample_count", 0) or 0)
            summary["latency_probe_spread_ms"] = float(probe_summary.get("latency_probe_spread_ms", 0.0) or 0.0)
            summary["latency_measurement_basis"] = str(
                probe_summary.get("latency_measurement_basis", "singleton_rerun_median")
            ).strip() or "singleton_rerun_median"
            summary["latency_stability_cleared"] = bool(probe_summary.get("latency_stability_cleared"))
            summary["quality_consistency_cleared"] = bool(probe_summary.get("quality_consistency_cleared"))
            family_modes[target_mode] = summary
        updated[family] = family_modes
    return updated


def _apply_singleton_latency_probes_to_published_scenarios(
    *,
    published_scenarios: Sequence[Mapping[str, Any]],
    latency_probes: Mapping[str, Mapping[str, Any]],
) -> list[dict[str, Any]]:
    updated_rows: list[dict[str, Any]] = []
    for scenario_report in published_scenarios:
        report_row = dict(scenario_report)
        scenario_id = str(report_row.get("scenario_id", "")).strip()
        published_profile = str(report_row.get("published_source_cache_profile", "")).strip()
        probe = dict(latency_probes.get(f"{published_profile}:{scenario_id}", {}))
        probe_modes = dict(probe.get("modes", {})) if isinstance(probe.get("modes"), Mapping) else {}
        updated_results: list[dict[str, Any]] = []
        for result in report_row.get("results", []):
            result_row = dict(result) if isinstance(result, Mapping) else {}
            mode = str(result_row.get("mode", "")).strip()
            probe_summary_payload = _lookup_mode_mapping(probe_modes, mode)
            probe_summary = dict(probe_summary_payload) if isinstance(probe_summary_payload, Mapping) else {}
            if probe_summary and bool(probe_summary.get("latency_stability_cleared")):
                if not _latency_probe_can_override_reported_latency(
                    reported_latency_ms=result_row.get("latency_ms", 0.0),
                    probe_latency_ms=probe_summary.get("median_latency_ms", 0.0),
                ):
                    updated_results.append(result_row)
                    continue
                result_row["latency_ms"] = float(probe_summary.get("median_latency_ms", result_row.get("latency_ms", 0.0)) or 0.0)
                result_row["instrumented_reasoning_duration_ms"] = float(
                    probe_summary.get(
                        "median_instrumented_reasoning_duration_ms",
                        result_row.get("instrumented_reasoning_duration_ms", 0.0),
                    )
                    or 0.0
                )
                result_row["uninstrumented_overhead_ms"] = float(
                    probe_summary.get(
                        "median_uninstrumented_overhead_ms",
                        result_row.get("uninstrumented_overhead_ms", 0.0),
                    )
                    or 0.0
                )
                result_row["latency_measurement_basis"] = str(
                    probe_summary.get("latency_measurement_basis", "singleton_rerun_median")
                ).strip() or "singleton_rerun_median"
                result_row["latency_probe_sample_count"] = int(probe_summary.get("sample_count", 0) or 0)
                result_row["latency_probe_spread_ms"] = float(probe_summary.get("latency_probe_spread_ms", 0.0) or 0.0)
                result_row["latency_stability_cleared"] = True
            updated_results.append(result_row)
        report_row["results"] = updated_results
        updated_rows.append(report_row)
    return updated_rows


def _conservative_numeric_value(
    *,
    field: str,
    mode: str,
    values: Sequence[Any],
) -> int | float:
    numeric_values = [float(value or 0.0) for value in values]
    if not numeric_values:
        return 0.0
    lower_better = field in _LOWER_BETTER_SUMMARY_FIELDS
    higher_better = field in _HIGHER_BETTER_SUMMARY_FIELDS
    baseline_mode = str(mode).strip() == _BASELINE_MODE
    if lower_better:
        chosen = min(numeric_values) if baseline_mode else max(numeric_values)
    elif higher_better:
        chosen = max(numeric_values) if baseline_mode else min(numeric_values)
    elif field.endswith("_count"):
        chosen = max(numeric_values)
        return int(round(chosen))
    else:
        chosen = numeric_values[0]
    integral = all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in values
    )
    if integral:
        return int(round(chosen))
    return round(chosen, 3)


def _aggregate_mode_summary(
    *,
    mode: str,
    profile_summaries: Sequence[Mapping[str, Any]],
    primary_summary: Mapping[str, Any],
) -> dict[str, Any]:
    if not profile_summaries:
        return {}
    aggregated: dict[str, Any] = {}
    keys = {
        str(key)
        for summary in profile_summaries
        for key in summary.keys()
        if str(key).strip()
    }
    for key in sorted(keys):
        values = [
            summary.get(key)
            for summary in profile_summaries
            if key in summary and summary.get(key) not in ("", [], {}, None)
        ]
        if not values:
            continue
        if all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            aggregated[key] = _conservative_numeric_value(field=key, mode=mode, values=values)
            continue
        if _all_values_equal(values):
            aggregated[key] = values[0]
            continue
        if key == "mode":
            aggregated[key] = str(mode).strip()
            continue
        if key in primary_summary and primary_summary.get(key) not in ("", [], {}, None):
            aggregated[key] = primary_summary.get(key)
            continue
        aggregated[key] = values[0]
    return aggregated


def _aggregate_family_summaries(
    *,
    modes: Sequence[str],
    cache_profile_summaries: Mapping[str, Mapping[str, Any]],
    primary_cache_profile: str,
) -> dict[str, dict[str, dict[str, Any]]]:
    family_names = sorted(
        {
            str(family).strip()
            for summary in cache_profile_summaries.values()
            if isinstance(summary, Mapping)
            for family in dict(summary.get("family_summaries", {})).keys()
            if str(family).strip()
        }
    )
    primary_families = (
        dict(dict(cache_profile_summaries.get(primary_cache_profile, {})).get("family_summaries", {}))
        if isinstance(cache_profile_summaries.get(primary_cache_profile), Mapping)
        else {}
    )
    aggregated: dict[str, dict[str, dict[str, Any]]] = {}
    for family in family_names:
        family_modes: dict[str, dict[str, Any]] = {}
        primary_family_modes = (
            dict(primary_families.get(family, {}))
            if isinstance(primary_families.get(family), Mapping)
            else {}
        )
        for mode in modes:
            profile_mode_summaries = [
                dict(dict(profile_summary.get("family_summaries", {})).get(family, {})).get(mode, {})
                for profile_summary in cache_profile_summaries.values()
                if isinstance(profile_summary, Mapping)
                and isinstance(dict(profile_summary.get("family_summaries", {})).get(family), Mapping)
                and isinstance(dict(dict(profile_summary.get("family_summaries", {})).get(family, {})).get(mode), Mapping)
            ]
            profile_mode_summaries = [
                dict(summary)
                for summary in profile_mode_summaries
                if isinstance(summary, Mapping)
            ]
            if not profile_mode_summaries:
                continue
            primary_mode_summary = (
                dict(primary_family_modes.get(mode, {}))
                if isinstance(primary_family_modes.get(mode), Mapping)
                else {}
            )
            family_modes[mode] = _aggregate_mode_summary(
                mode=mode,
                profile_summaries=profile_mode_summaries,
                primary_summary=primary_mode_summary,
            )
        if family_modes:
            aggregated[family] = family_modes
    return aggregated


def _conservative_result_metric(
    *,
    field: str,
    mode: str,
    values: Sequence[Any],
) -> int | float:
    numeric_values = [float(value or 0.0) for value in values]
    if not numeric_values:
        return 0.0
    lower_better = field in _LOWER_BETTER_RESULT_FIELDS
    higher_better = field in _HIGHER_BETTER_RESULT_FIELDS
    baseline_mode = str(mode).strip() == _BASELINE_MODE
    if lower_better:
        chosen = min(numeric_values) if baseline_mode else max(numeric_values)
    elif higher_better:
        chosen = max(numeric_values) if baseline_mode else min(numeric_values)
    else:
        chosen = numeric_values[0]
    integral = all(
        isinstance(value, int) and not isinstance(value, bool)
        for value in values
    )
    if integral:
        return int(round(chosen))
    return round(chosen, 3)


def _published_profile_metrics_within_tie_tolerance(
    *,
    primary_score: Sequence[float],
    selected_score: Sequence[float],
) -> bool:
    primary = [float(value or 0.0) for value in primary_score]
    selected = [float(value or 0.0) for value in selected_score]
    if len(primary) < 5 or len(selected) < 5:
        return False
    return (
        primary[3] == selected[3]
        and primary[4] == selected[4]
        and abs(primary[0] - selected[0]) <= _PUBLISHED_PROFILE_LATENCY_TIE_TOLERANCE_MS
        and abs(primary[1] - selected[1]) <= _PUBLISHED_PROFILE_PROMPT_TIE_TOLERANCE
        and abs(primary[2] - selected[2]) <= _PUBLISHED_PROFILE_TOTAL_PAYLOAD_TIE_TOLERANCE
    )


def _aggregate_published_scenarios(
    *,
    scenarios: Sequence[Mapping[str, Any]],
    modes: Sequence[str],
    cache_profiles: Sequence[str],
    cache_profile_reports: Mapping[str, Sequence[Mapping[str, Any]]],
) -> list[dict[str, Any]]:
    indexed: dict[str, dict[str, Mapping[str, Any]]] = {}
    for profile, rows in cache_profile_reports.items():
        if not isinstance(rows, Sequence):
            continue
        indexed[str(profile).strip()] = {
            str(row.get("scenario_id", "")).strip(): row
            for row in rows
            if isinstance(row, Mapping) and str(row.get("scenario_id", "")).strip()
        }
    published: list[dict[str, Any]] = []
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id", "")).strip()
        if not scenario_id:
            continue
        profile_candidates: list[tuple[tuple[float, float, float, float, float], str, Mapping[str, Any]]] = []
        for profile in cache_profiles:
            base_row = indexed.get(str(profile).strip(), {}).get(scenario_id)
            if not isinstance(base_row, Mapping):
                continue
            results = {
                str(row.get("mode", "")).strip(): row
                for row in base_row.get("results", [])
                if isinstance(row, Mapping) and str(row.get("mode", "")).strip()
            }
            candidate_payload = _lookup_mode_mapping(results, _ODYLITH_ON_MODE)
            baseline_payload = _lookup_mode_mapping(results, _BASELINE_MODE)
            if not isinstance(candidate_payload, Mapping) or not isinstance(baseline_payload, Mapping):
                profile_candidates.append(((0.0, 0.0, 0.0, 0.0, 0.0), str(profile).strip(), base_row))
                continue
            candidate = dict(candidate_payload)
            baseline = dict(baseline_payload)
            profile_candidates.append(
                (
                    (
                        round(float(candidate.get("latency_ms", 0.0) or 0.0) - float(baseline.get("latency_ms", 0.0) or 0.0), 3),
                        round(
                            float(candidate.get("effective_estimated_tokens", candidate.get("codex_prompt_estimated_tokens", 0.0)) or 0.0)
                            - float(baseline.get("effective_estimated_tokens", baseline.get("codex_prompt_estimated_tokens", 0.0)) or 0.0),
                            3,
                        ),
                        round(
                            float(candidate.get("total_payload_estimated_tokens", candidate.get("effective_estimated_tokens", 0.0)) or 0.0)
                            - float(baseline.get("total_payload_estimated_tokens", baseline.get("effective_estimated_tokens", 0.0)) or 0.0),
                            3,
                        ),
                        round(
                            float(baseline.get("required_path_recall", 0.0) or 0.0)
                            - float(candidate.get("required_path_recall", 0.0) or 0.0),
                            3,
                        ),
                        round(
                            float(baseline.get("validation_success_proxy", 0.0) or 0.0)
                            - float(candidate.get("validation_success_proxy", 0.0) or 0.0),
                            3,
                        ),
                    ),
                    str(profile).strip(),
                    base_row,
                )
            )
        if not profile_candidates:
            continue
        _score, selected_profile, selected_row = max(profile_candidates, key=lambda row: row[0])
        primary_profile = str(cache_profiles[0]).strip() if cache_profiles else ""
        primary_candidate = next((row for row in profile_candidates if row[1] == primary_profile), None)
        if (
            primary_candidate is not None
            and primary_profile
            and selected_profile != primary_profile
            and _published_profile_metrics_within_tie_tolerance(
                primary_score=primary_candidate[0],
                selected_score=_score,
            )
        ):
            _score, selected_profile, selected_row = primary_candidate
        report_row = {
            key: value
            for key, value in dict(selected_row).items()
        }
        report_row["cache_profile"] = "conservative_multi_profile"
        report_row["published_source_cache_profile"] = selected_profile
        report_row["published_selection_strategy"] = "worst_same_profile_comparison"
        published.append(report_row)
    return published


def _published_view_strategy(*, cache_profiles: Sequence[str]) -> str:
    normalized = [str(token).strip() for token in cache_profiles if str(token).strip()]
    return "conservative_multi_profile" if len(normalized) > 1 else "single_profile"


def _acceptance(
    *,
    mode_summaries: Mapping[str, Mapping[str, Any]],
    primary_comparison: Mapping[str, Any],
    family_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]],
    corpus_summary: Mapping[str, Any],
    fairness_findings: Sequence[str] = (),
    runtime_posture: Mapping[str, Any] | None = None,
    packet_source_summaries: Mapping[str, Mapping[str, Mapping[str, Any]]] | None = None,
    cache_profile_summaries: Mapping[str, Mapping[str, Any]] | None = None,
    execution_contracts: Mapping[str, Mapping[str, Any]] | None = None,
    comparison_contract: str = "",
) -> dict[str, Any]:
    candidate_payload = _lookup_mode_mapping(mode_summaries, _ODYLITH_ON_MODE)
    baseline_payload = _lookup_mode_mapping(mode_summaries, _BASELINE_MODE)
    candidate = dict(candidate_payload) if isinstance(candidate_payload, Mapping) else {}
    baseline = dict(baseline_payload) if isinstance(baseline_payload, Mapping) else {}
    architecture_candidate = (
        dict(_lookup_mode_mapping(dict(family_summaries.get("architecture", {})), _ODYLITH_ON_MODE) or {})
        if isinstance(family_summaries.get("architecture"), Mapping)
        else {}
    )
    architecture_baseline = (
        dict(_lookup_mode_mapping(dict(family_summaries.get("architecture", {})), _BASELINE_MODE) or {})
        if isinstance(family_summaries.get("architecture"), Mapping)
        else {}
    )
    explicit_workstream_candidate = (
        dict(_lookup_mode_mapping(dict(family_summaries.get("explicit_workstream", {})), _ODYLITH_ON_MODE) or {})
        if isinstance(family_summaries.get("explicit_workstream"), Mapping)
        else {}
    )
    governance_packet_coverage_complete = all(
        float(
            dict(_lookup_mode_mapping(dict(family_summaries.get(family, {})), _ODYLITH_ON_MODE) or {}).get("odylith_packet_present_rate", 0.0)
            or 0.0
        )
        >= 1.0
        for family in _GOVERNANCE_SLICE_FAMILIES
        if isinstance(family_summaries.get(family), Mapping)
    )
    prompt_token_delta = float(
        primary_comparison.get(
            "median_prompt_token_delta",
            primary_comparison.get("median_token_delta", 0.0),
        )
        or 0.0
    )
    total_payload_delta = float(primary_comparison.get("median_total_payload_token_delta", 0.0) or 0.0)
    bootstrap_packet_source = (
        dict(packet_source_summaries.get("bootstrap_session", {}))
        if isinstance(packet_source_summaries, Mapping) and isinstance(packet_source_summaries.get("bootstrap_session"), Mapping)
        else {}
    )
    bootstrap_candidate = (
        dict(_lookup_mode_mapping(bootstrap_packet_source, _ODYLITH_ON_MODE) or {})
        if bootstrap_packet_source
        else {}
    )
    bootstrap_baseline = (
        dict(_lookup_mode_mapping(bootstrap_packet_source, _BASELINE_MODE) or {})
        if bootstrap_packet_source
        else {}
    )
    bootstrap_payload_delta = 0.0
    if bootstrap_candidate and bootstrap_baseline:
        bootstrap_payload_delta = float(bootstrap_candidate.get("median_total_payload_tokens", 0.0) or 0.0) - float(
            bootstrap_baseline.get("median_total_payload_tokens", 0.0) or 0.0
        )
    architecture_latency_delta = 0.0
    if architecture_candidate and architecture_baseline:
        architecture_latency_delta = float(architecture_candidate.get("median_latency_ms", 0.0) or 0.0) - float(
            architecture_baseline.get("median_latency_ms", 0.0) or 0.0
        )
    candidate_scenario_count = int(candidate.get("scenario_count", 0) or 0)
    candidate_validation_backed_scenario_count = int(candidate.get("validation_backed_scenario_count", 0) or 0)
    candidate_critical_required_path_backed_scenario_count = int(
        candidate.get("critical_required_path_backed_scenario_count", 0) or 0
    )
    candidate_critical_validation_backed_scenario_count = int(
        candidate.get("critical_validation_backed_scenario_count", 0) or 0
    )
    packet_budget_guardrail_applicable = int(candidate.get("packet_scenario_count", 0) or 0) > 0
    comparative_efficiency_guardrails = odylith_benchmark_guardrails.comparative_efficiency_guardrails_applicability(
        candidate_summary=candidate,
        baseline_summary=baseline,
    )
    runtime = dict(runtime_posture or {}) if isinstance(runtime_posture, Mapping) else {}
    runtime_memory_standardization_state = str(runtime.get("memory_standardization_state", "")).strip()
    runtime_memory_backed_retrieval_ready = runtime.get("memory_backed_retrieval_ready")
    if runtime_memory_backed_retrieval_ready is None:
        runtime_memory_backed_retrieval_ready = True
    comparative_efficiency_applicable = bool(comparative_efficiency_guardrails.get("applicable"))
    live_end_to_end_comparison = _is_live_comparison_contract(comparison_contract)
    comparative_latency_and_token_status_blocking = comparative_efficiency_applicable and not live_end_to_end_comparison

    hard_quality_checks = {
        "memory_backend_standardized": runtime_memory_standardization_state in {"", "standardized"},
        "memory_backed_retrieval_ready": bool(runtime_memory_backed_retrieval_ready),
        "required_path_recall_not_worse": float(primary_comparison.get("required_path_recall_delta", 0.0) or 0.0) >= 0.0,
        "required_path_precision_not_worse": float(primary_comparison.get("required_path_precision_delta", 0.0) or 0.0) >= 0.0,
        "hallucinated_surface_not_worse": float(primary_comparison.get("hallucinated_surface_rate_delta", 0.0) or 0.0) <= 0.0,
        "validation_success_not_worse": float(primary_comparison.get("validation_success_delta", 0.0) or 0.0) >= 0.0,
        "write_surface_precision_not_worse": (
            int(candidate.get("write_surface_backed_scenario_count", 0) or 0) == 0
            or float(primary_comparison.get("write_surface_precision_delta", 0.0) or 0.0) >= 0.0
        ),
        "unnecessary_widening_not_worse": (
            int(candidate.get("write_surface_backed_scenario_count", 0) or 0) == 0
            or float(primary_comparison.get("unnecessary_widening_rate_delta", 0.0) or 0.0) <= 0.0
        ),
        "critical_required_path_recall_not_worse": float(primary_comparison.get("critical_required_path_recall_delta", 0.0) or 0.0) >= 0.0,
        "critical_validation_success_not_worse": float(primary_comparison.get("critical_validation_success_delta", 0.0) or 0.0) >= 0.0,
        "live_execution_contract_match": _live_execution_contract_match(execution_contracts),
        "expectation_success_not_worse": float(primary_comparison.get("expectation_success_delta", 0.0) or 0.0) >= 0.0,
        "proof_false_clearance_healthy": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("false_clearance_rate", 0.0) or 0.0) <= 0.0
        ),
        "proof_frontier_gate_accurate": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_frontier_gate_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "proof_claim_guard_accurate": (
            int(candidate.get("proof_state_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_claim_guard_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "proof_same_fingerprint_reuse_accurate": (
            int(candidate.get("proof_same_fingerprint_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("proof_same_fingerprint_reuse_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_packet_source_accurate": (
            int(candidate.get("context_engine_expected_packet_source_count", 0) or 0) == 0
            or float(candidate.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_selection_state_accurate": (
            int(candidate.get("context_engine_expected_selection_state_count", 0) or 0) == 0
            or float(candidate.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_workstream_accurate": (
            int(candidate.get("context_engine_expected_workstream_count", 0) or 0) == 0
            or float(candidate.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_ambiguity_fail_closed": (
            int(candidate.get("context_engine_ambiguity_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0) >= 1.0
        ),
        "context_engine_session_namespaced": (
            int(candidate.get("context_engine_runtime_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("context_engine_session_namespace_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_present": (
            int(candidate.get("execution_engine_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_present_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_resume_token_present": (
            int(candidate.get("execution_engine_backed_scenario_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_resume_token_present_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_outcome_accurate": (
            int(candidate.get("execution_engine_expected_outcome_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_outcome_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_mode_accurate": (
            int(candidate.get("execution_engine_expected_mode_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0) >= 1.0
        ),
        "execution_engine_next_move_accurate": (
            int(candidate.get("execution_engine_expected_next_move_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_next_move_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_closure_accurate": (
            int(candidate.get("execution_engine_expected_closure_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_closure_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_wait_status_accurate": (
            int(candidate.get("execution_engine_expected_wait_status_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_wait_status_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_validation_accurate": (
            int(candidate.get("execution_engine_expected_validation_archetype_count", 0) or 0)
            == 0
            or float(
                candidate.get("execution_engine_validation_archetype_accuracy_rate", 0.0)
                or 0.0
            )
            >= 1.0
        ),
        "execution_engine_current_phase_accurate": (
            int(candidate.get("execution_engine_expected_current_phase_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_current_phase_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_last_successful_phase_accurate": (
            int(candidate.get("execution_engine_expected_last_successful_phase_count", 0) or 0)
            == 0
            or float(
                candidate.get(
                    "execution_engine_last_successful_phase_accuracy_rate", 0.0
                )
                or 0.0
            )
            >= 1.0
        ),
        "execution_engine_authoritative_lane_accurate": (
            int(candidate.get("execution_engine_expected_authoritative_lane_count", 0) or 0)
            == 0
            or float(
                candidate.get("execution_engine_authoritative_lane_accuracy_rate", 0.0)
                or 0.0
            )
            >= 1.0
        ),
        "execution_engine_target_lane_accurate": (
            int(candidate.get("execution_engine_expected_target_lane_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_target_lane_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_resume_token_accurate": (
            int(candidate.get("execution_engine_expected_resume_token_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_resume_token_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_host_family_accurate": (
            int(candidate.get("execution_engine_expected_host_family_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_host_family_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_model_family_accurate": (
            int(candidate.get("execution_engine_expected_model_family_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_model_family_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        "execution_engine_reanchor_accurate": (
            int(candidate.get("execution_engine_expected_reanchor_count", 0) or 0) == 0
            or float(candidate.get("execution_engine_reanchor_accuracy_rate", 0.0) or 0.0)
            >= 1.0
        ),
        **odylith_benchmark_execution_engine.acceptance_checks(candidate),
        "candidate_expectation_success_positive": (
            candidate_scenario_count == 0 or float(candidate.get("expectation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_validation_success_positive": (
            candidate_validation_backed_scenario_count == 0
            or float(candidate.get("validation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_critical_required_path_recall_positive": (
            candidate_critical_required_path_backed_scenario_count == 0
            or float(candidate.get("critical_required_path_recall_rate", 0.0) or 0.0) > 0.0
        ),
        "candidate_critical_validation_success_positive": (
            candidate_critical_validation_backed_scenario_count == 0
            or float(candidate.get("critical_validation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "explicit_workstream_expectation_positive": (
            not explicit_workstream_candidate
            or float(explicit_workstream_candidate.get("expectation_success_rate", 0.0) or 0.0) > 0.0
        ),
        "critical_metric_coverage_complete": (
            int(corpus_summary.get("correctness_critical_scenario_count", 0) or 0)
            == int(corpus_summary.get("critical_required_path_backed_scenario_count", 0) or 0)
            == int(corpus_summary.get("critical_validation_backed_scenario_count", 0) or 0)
        ),
        "fairness_contract_passed": not any(str(token).strip() for token in fairness_findings),
        "selected_cache_profiles_clear_gate": (
            True
            if not dict(cache_profile_summaries or {})
            else all(
                _acceptance_hard_quality_gate_cleared(dict(summary.get("acceptance", {})))
                for summary in dict(cache_profile_summaries or {}).values()
                if isinstance(summary, Mapping)
            )
        ),
    }
    secondary_guardrail_checks = {
        "latency_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or float(primary_comparison.get("median_latency_delta_ms", 0.0) or 0.0)
        <= _SECONDARY_LATENCY_GUARDRAIL_MAX_DELTA_MS,
        "prompt_delta_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or prompt_token_delta <= _SECONDARY_PROMPT_TOKEN_GUARDRAIL_MAX_DELTA,
        "total_payload_delta_within_guardrail": (not comparative_latency_and_token_status_blocking)
        or total_payload_delta <= _SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA,
        "bootstrap_payload_delta_within_guardrail": (
            not comparative_latency_and_token_status_blocking
            or not bootstrap_candidate
            or not bootstrap_baseline
            or bootstrap_payload_delta <= _SECONDARY_TOTAL_PAYLOAD_TOKEN_GUARDRAIL_MAX_DELTA
        ),
        "tight_budget_behavior_healthy": (not packet_budget_guardrail_applicable)
        or float(candidate.get("within_budget_rate", 0.0) or 0.0) >= _SECONDARY_WITHIN_BUDGET_RATE_MIN,
        "architecture_latency_within_guardrail": (
            not comparative_latency_and_token_status_blocking
            or not architecture_candidate
            or not architecture_baseline
            or not _mode_supports_architecture_dossier(_BASELINE_MODE)
            or architecture_latency_delta <= _SECONDARY_ARCHITECTURE_LATENCY_GUARDRAIL_MAX_DELTA_MS
        ),
    }
    advisory_checks = {
        "widening_rate_healthy": float(candidate.get("odylith_requires_widening_rate", 0.0) or 0.0) <= 0.15,
        "governance_packet_coverage_complete": governance_packet_coverage_complete,
    }
    checks = {
        **hard_quality_checks,
        **secondary_guardrail_checks,
        **advisory_checks,
        "packet_budget_healthy": secondary_guardrail_checks["tight_budget_behavior_healthy"],
        "architecture_not_slower": secondary_guardrail_checks["architecture_latency_within_guardrail"],
    }
    hard_quality_gate_cleared = all(hard_quality_checks.values()) if candidate and baseline else False
    secondary_guardrails_cleared = all(secondary_guardrail_checks.values()) if candidate and baseline else False
    advisory_checks_cleared = all(advisory_checks.values()) if candidate else False
    passed = hard_quality_gate_cleared and secondary_guardrails_cleared
    notes = []
    hard_gate_families: list[str] = []
    advisory_families: list[str] = []
    if not baseline:
        notes.append("`odylith_off` summary is unavailable; rerun with the raw Codex CLI lane enabled.")
    if fairness_findings:
        notes.append("Benchmark fairness contract findings are present; the published pair is not release-safe until they are resolved.")
    for family, family_modes in family_summaries.items():
        candidate_family_payload = _lookup_mode_mapping(family_modes, _ODYLITH_ON_MODE)
        baseline_family_payload = _lookup_mode_mapping(family_modes, _BASELINE_MODE)
        candidate_family = dict(candidate_family_payload) if isinstance(candidate_family_payload, Mapping) else {}
        baseline_family = dict(baseline_family_payload) if isinstance(baseline_family_payload, Mapping) else {}
        if not candidate_family or not baseline_family:
            continue
        if (
            float(candidate_family.get("required_path_recall_rate", 0.0) or 0.0) < float(baseline_family.get("required_path_recall_rate", 0.0) or 0.0)
            or float(candidate_family.get("required_path_precision_rate", 0.0) or 0.0) < float(baseline_family.get("required_path_precision_rate", 0.0) or 0.0)
            or float(candidate_family.get("hallucinated_surface_rate", 0.0) or 0.0) > float(baseline_family.get("hallucinated_surface_rate", 0.0) or 0.0)
            or float(candidate_family.get("validation_success_rate", 0.0) or 0.0) < float(baseline_family.get("validation_success_rate", 0.0) or 0.0)
            or float(candidate_family.get("expectation_success_rate", 0.0) or 0.0) < float(baseline_family.get("expectation_success_rate", 0.0) or 0.0)
            or float(candidate_family.get("false_clearance_rate", 0.0) or 0.0) > 0.0
            or (
                int(candidate_family.get("proof_state_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("proof_frontier_gate_accuracy_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("proof_state_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("proof_claim_guard_accuracy_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("proof_same_fingerprint_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("proof_same_fingerprint_reuse_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("context_engine_expected_packet_source_count", 0) or 0) > 0
                and float(candidate_family.get("context_engine_packet_source_accuracy_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("context_engine_expected_selection_state_count", 0) or 0) > 0
                and float(candidate_family.get("context_engine_selection_state_accuracy_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("context_engine_expected_workstream_count", 0) or 0) > 0
                and float(candidate_family.get("context_engine_workstream_accuracy_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("context_engine_ambiguity_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("context_engine_fail_closed_ambiguity_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("context_engine_runtime_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("context_engine_session_namespace_rate", 0.0) or 0.0) < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("execution_engine_present_rate", 0.0) or 0.0)
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_backed_scenario_count", 0) or 0) > 0
                and float(
                    candidate_family.get("execution_engine_resume_token_present_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_outcome_count", 0) or 0) > 0
                and float(
                    candidate_family.get("execution_engine_outcome_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_mode_count", 0) or 0) > 0
                and float(candidate_family.get("execution_engine_mode_accuracy_rate", 0.0) or 0.0)
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_next_move_count", 0) or 0) > 0
                and float(
                    candidate_family.get("execution_engine_next_move_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_closure_count", 0) or 0) > 0
                and float(
                    candidate_family.get("execution_engine_closure_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_wait_status_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_wait_status_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(
                    candidate_family.get("execution_engine_expected_validation_archetype_count", 0)
                    or 0
                )
                > 0
                and float(
                    candidate_family.get(
                        "execution_engine_validation_archetype_accuracy_rate", 0.0
                    )
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_current_phase_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_current_phase_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(
                    candidate_family.get("execution_engine_expected_last_successful_phase_count", 0)
                    or 0
                )
                > 0
                and float(
                    candidate_family.get(
                        "execution_engine_last_successful_phase_accuracy_rate", 0.0
                    )
                    or 0.0
                )
                < 1.0
            )
            or (
                int(
                    candidate_family.get("execution_engine_expected_authoritative_lane_count", 0)
                    or 0
                )
                > 0
                and float(
                    candidate_family.get(
                        "execution_engine_authoritative_lane_accuracy_rate", 0.0
                    )
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_target_lane_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_target_lane_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_resume_token_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_resume_token_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_host_family_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_host_family_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_model_family_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_model_family_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or (
                int(candidate_family.get("execution_engine_expected_reanchor_count", 0) or 0)
                > 0
                and float(
                    candidate_family.get("execution_engine_reanchor_accuracy_rate", 0.0)
                    or 0.0
                )
                < 1.0
            )
            or odylith_benchmark_execution_engine.quality_gate_failed(candidate_family)
            or (
                int(candidate_family.get("write_surface_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("write_surface_precision_rate", 0.0) or 0.0)
                < float(baseline_family.get("write_surface_precision_rate", 0.0) or 0.0)
            )
            or (
                int(candidate_family.get("write_surface_backed_scenario_count", 0) or 0) > 0
                and float(candidate_family.get("unnecessary_widening_rate", 0.0) or 0.0) > 0.15
            )
        ):
            hard_gate_families.append(family)
        if (
            family != "architecture"
            and float(candidate_family.get("odylith_requires_widening_rate", 0.0) or 0.0) > 0.15
        ) or (
            family in _GOVERNANCE_SLICE_FAMILIES
            and float(candidate_family.get("odylith_packet_present_rate", 0.0) or 0.0) < 1.0
        ):
            advisory_families.append(family)

    hard_gate_failures = [name for name, ok in hard_quality_checks.items() if not ok]
    secondary_guardrail_failures = [name for name, ok in secondary_guardrail_checks.items() if not ok]
    advisory_failures = [name for name, ok in advisory_checks.items() if not ok]
    hard_gate_failure_labels = _acceptance_failure_labels(hard_gate_failures)
    secondary_guardrail_failure_labels = _acceptance_failure_labels(secondary_guardrail_failures)
    advisory_failure_labels = _acceptance_failure_labels(advisory_failures)
    if hard_quality_gate_cleared:
        notes.append("Odylith clears the hard quality gate against `odylith_off` on this sampled corpus.")
    else:
        notes.append("Odylith has not yet cleared the hard quality gate against `odylith_off` on this sampled corpus.")
    if hard_gate_failure_labels:
        notes.append(
            "Hard-gate blockers: " + "; ".join(hard_gate_failure_labels[:4]) + "."
        )
    if not hard_quality_checks["candidate_expectation_success_positive"]:
        notes.append(
            "The sampled live run is not yet informative: `odylith_on` did not complete any benchmark task successfully end to end."
        )
    if not hard_quality_checks["candidate_validation_success_positive"]:
        notes.append(
            "No sampled validation-backed task produced a successful `odylith_on` outcome, so this run cannot publish as a benchmark win."
        )
    if not hard_quality_checks["candidate_critical_required_path_recall_positive"]:
        notes.append("Odylith still missed every sampled critical required path, so the critical slice is not benchmark-ready.")
    if not hard_quality_checks["candidate_critical_validation_success_positive"]:
        notes.append(
            "No sampled critical validator-backed task produced a successful `odylith_on` outcome, so the critical slice is not benchmark-ready."
        )
    if not hard_quality_checks["proof_false_clearance_healthy"]:
        notes.append(
            "Proof-state benchmark slices still allow false live-clearance claims before the hosted frontier advances."
        )
    if not hard_quality_checks["proof_frontier_gate_accurate"]:
        notes.append(
            "Proof-state frontier gating is inconsistent on the sampled proof-backed slices."
        )
    if not hard_quality_checks["proof_claim_guard_accurate"]:
        notes.append(
            "Proof-state claim tiers are still mislabeled on sampled proof-backed slices."
        )
    if not hard_quality_checks["proof_same_fingerprint_reuse_accurate"]:
        notes.append(
            "Same-fingerprint proof seams are not being reused consistently on sampled proof-backed slices."
        )
    if not hard_quality_checks["context_engine_packet_source_accurate"]:
        notes.append(
            "Context Engine benchmark slices are selecting the wrong packet lane on sampled grounding cases."
        )
    if not hard_quality_checks["context_engine_selection_state_accurate"]:
        notes.append(
            "Context Engine benchmark slices are mislabeling resolved versus ambiguous scope on sampled grounding cases."
        )
    if not hard_quality_checks["context_engine_workstream_accurate"]:
        notes.append(
            "Context Engine benchmark slices are resolving the wrong workstream anchor on sampled grounding cases."
        )
    if not hard_quality_checks["context_engine_ambiguity_fail_closed"]:
        notes.append(
            "Context Engine benchmark slices are not staying fail-closed when the sampled scope remains ambiguous."
        )
    if not hard_quality_checks["context_engine_session_namespaced"]:
        notes.append(
            "Context Engine runtime-backed benchmark slices are not keeping session state namespaced consistently."
        )
    if not hard_quality_checks["execution_engine_present"]:
        notes.append(
            "Execution Engine benchmark slices are dropping the execution-engine snapshot on sampled packet rows."
        )
    if not hard_quality_checks["execution_engine_resume_token_present"]:
        notes.append(
            "Execution Engine benchmark slices are not carrying resumability through a resume token consistently."
        )
    if not hard_quality_checks["execution_engine_outcome_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong admissibility outcome on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_mode_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong execution mode on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_next_move_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong truthful next move on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_closure_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong closure posture on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_wait_status_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong semantic wait state on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_validation_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong validation archetype on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_current_phase_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong current phase on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_last_successful_phase_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong last successful phase on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_authoritative_lane_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong authoritative lane on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_target_lane_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong target lane on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_resume_token_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong resume token on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_host_family_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong host family on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_model_family_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong model family on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_component_id_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong canonical engine component id on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_canonical_component_id_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong canonical component id on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_identity_status_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong identity status on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_target_component_status_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong target component status on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_snapshot_reuse_status_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong snapshot reuse posture on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_reanchor_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong re-anchor requirement on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_false_admit_zero"]:
        notes.append(
            "Execution Engine benchmark slices are still falsely admitting actions that should fail closed."
        )
    if not hard_quality_checks["execution_engine_false_deny_zero"]:
        notes.append(
            "Execution Engine benchmark slices are still falsely denying actions that should be admissible."
        )
    if not hard_quality_checks["execution_engine_delegation_guard_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong delegation guard posture on sampled execution rows."
        )
    if not hard_quality_checks["execution_engine_parallelism_guard_accurate"]:
        notes.append(
            "Execution Engine benchmark slices are resolving the wrong parallelism guard posture on sampled execution rows."
        )
    if not _live_execution_contract_match(execution_contracts):
        notes.append("`odylith_on` and `odylith_off` did not run on the same Codex CLI model/reasoning contract.")
    if hard_quality_checks["memory_backed_retrieval_ready"]:
        notes.append("Benchmark proof used active local LanceDB plus Tantivy retrieval memory.")
    else:
        notes.append("Benchmark ran without an active local LanceDB/Tantivy retrieval substrate.")
    if str(runtime.get("remote_retrieval_status", "")).strip() == "disabled":
        notes.append("Vespa is optional and currently disabled; the current benchmark proof is local-first, not remote-assisted.")
    elif bool(runtime.get("remote_retrieval_enabled")):
        notes.append(
            "Vespa remote retrieval is active in "
            + (str(runtime.get("remote_retrieval_mode", "")).strip() or "augment")
            + " mode for this benchmark posture."
        )
    if comparative_efficiency_applicable and not live_end_to_end_comparison:
        notes.append(
            "Relative latency and token-efficiency guardrails are active because both `odylith_on` and `odylith_off` produced successful outcomes on the sampled corpus."
        )
    elif comparative_efficiency_applicable and live_end_to_end_comparison:
        notes.append(
            "Live proof keeps benchmark time to valid outcome and full-session token spend published, but not status-blocking, because the public pair measures contention-shared matched-pair wall clock and multi-turn session accumulation rather than interactive product latency or initial prompt size."
        )
    else:
        reason = str(comparative_efficiency_guardrails.get("reason", "")).strip()
        if reason == "baseline_has_no_successful_outcomes":
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because `odylith_off` produced no successful outcomes on the sampled corpus."
            )
        elif reason == "candidate_has_no_successful_outcomes":
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because `odylith_on` produced no successful outcomes on the sampled corpus."
            )
        else:
            notes.append(
                "Relative latency and token-efficiency guardrails were not applied because the sampled corpus did not produce successful outcomes on both compared lanes."
            )
    if not packet_budget_guardrail_applicable:
        notes.append(
            "Tighter-budget behavior was not applied because the sampled corpus contains no packet-backed scenarios."
        )
    if secondary_guardrails_cleared:
        notes.append("Secondary latency, efficiency, and tighter-budget guardrails are within threshold on this sampled corpus.")
    elif secondary_guardrail_failure_labels:
        notes.append(
            "Secondary guardrails needing attention: " + "; ".join(secondary_guardrail_failure_labels[:4]) + "."
        )
    if float(primary_comparison.get("median_latency_delta_ms", 0.0) or 0.0) > 0.0:
        notes.append(
            "Odylith takes longer than raw Codex CLI to reach a valid outcome on the benchmark pair; this stays published as a secondary tradeoff and only blocks status when the comparative live-efficiency guardrail is actually status-blocking."
        )
    if prompt_token_delta > 0.0:
        notes.append(
            "Odylith uses more full-session input tokens than raw Codex CLI on the live run; that overhead stays visible, but it is not the same thing as initial prompt size."
        )
    if hard_gate_families:
        notes.append(f"Hard-gate families needing attention: {', '.join(hard_gate_families[:5])}.")
    failed_profiles = [
        str(profile).strip()
        for profile, summary in dict(cache_profile_summaries or {}).items()
        if isinstance(summary, Mapping)
        and not _acceptance_hard_quality_gate_cleared(dict(summary.get("acceptance", {})))
    ]
    if failed_profiles:
        notes.append(
            "Selected cache profiles still failing the hard quality gate: "
            + ", ".join(failed_profiles[:4])
            + "."
        )
    if total_payload_delta > 0.0:
        notes.append(
            f"Total runtime-contract payload is still heavier than baseline by {total_payload_delta:.3f} median tokens; that remains a published secondary cost and only blocks status when the comparative payload guardrail is applicable and breached."
        )
    if bootstrap_candidate and bootstrap_baseline and bootstrap_payload_delta > 0.0:
        notes.append(
            f"Bootstrap-session payload is still heavier than baseline by {bootstrap_payload_delta:.3f} median tokens; this first-turn tax now has its own benchmark guardrail."
        )
    if architecture_candidate and architecture_baseline and architecture_latency_delta > 0.0:
        notes.append(
            f"Architecture still takes {architecture_latency_delta:.3f}ms longer than baseline to reach a valid outcome in the published comparison view."
        )
    if float(candidate.get("odylith_requires_widening_rate", 0.0) or 0.0) > 0.15:
        notes.append(
            "Widening is still too frequent in the published candidate view; this stays published as advisory mechanism attention rather than the primary outcome gate."
        )
    if float(primary_comparison.get("hallucinated_surface_rate_delta", 0.0) or 0.0) > 0.0:
        notes.append("Published observed-surface drift is still worse than baseline; tighten the evidence cone before widening more families.")
    if int(candidate.get("write_surface_backed_scenario_count", 0) or 0) > 0 and float(
        primary_comparison.get("unnecessary_widening_rate_delta", 0.0) or 0.0
    ) > 0.0:
        notes.append("Published write-surface widening is still worse than baseline on scenarios that actually require writes.")
    if not governance_packet_coverage_complete:
        notes.append(
            "Governance-family packet coverage is incomplete; this stays published as advisory mechanism attention, not as the primary outcome gate."
        )
    if advisory_failure_labels:
        notes.append("Advisory mechanism checks needing attention: " + "; ".join(advisory_failure_labels[:4]) + ".")
    if advisory_families:
        notes.append("Advisory mechanism families needing attention: " + ", ".join(sorted(set(advisory_families))[:5]) + ".")
    if dict(cache_profile_summaries or {}) and hard_quality_checks["selected_cache_profiles_clear_gate"]:
        notes.append(
            "All selected cache profiles clear the hard quality gate, so the published result is not relying on a single flattering cache posture."
        )
    notes.append(
        "This harness blocks status on the hard quality gate first. In live proof, benchmark time to valid outcome and full-session token spend stay published as diagnostics, while tighter-budget behavior remains an active secondary guardrail."
    )
    return {
        "status": "provisional_pass" if passed else "hold",
        "hard_quality_gate_cleared": hard_quality_gate_cleared,
        "secondary_guardrails_cleared": secondary_guardrails_cleared,
        "advisory_checks_cleared": advisory_checks_cleared,
        "comparative_efficiency_guardrails_applicable": comparative_efficiency_applicable,
        "comparative_latency_and_token_status_blocking": comparative_latency_and_token_status_blocking,
        "comparative_efficiency_guardrail_reason": str(comparative_efficiency_guardrails.get("reason", "")).strip(),
        "packet_budget_guardrail_applicable": packet_budget_guardrail_applicable,
        "hard_quality_checks": hard_quality_checks,
        "secondary_guardrail_checks": secondary_guardrail_checks,
        "advisory_checks": advisory_checks,
        "hard_gate_failures": hard_gate_failures,
        "hard_gate_failure_labels": hard_gate_failure_labels,
        "secondary_guardrail_failures": secondary_guardrail_failures,
        "secondary_guardrail_failure_labels": secondary_guardrail_failure_labels,
        "advisory_failures": advisory_failures,
        "advisory_failure_labels": advisory_failure_labels,
        "checks": checks,
        "weak_families": hard_gate_families,
        "advisory_families": sorted(set(advisory_families)),
        "notes": notes,
    }


def _render_report_summary(report: Mapping[str, Any]) -> str:
    summary = compact_report_summary(report)
    if not summary:
        return "odylith benchmark report unavailable"
    return (
        "odylith benchmark\n"
        f"- report_id: {summary.get('report_id', '')}\n"
        f"- benchmark_profile: {summary.get('benchmark_profile', '')}\n"
        f"- benchmark_profile_label: {summary.get('benchmark_profile_label', '')}\n"
        f"- status: {summary.get('status', '')}\n"
        f"- scenarios: {int(summary.get('scenario_count', 0) or 0)}\n"
        f"- selection_strategy: {summary.get('selection_strategy', '') or 'manual_selection'}\n"
        f"- selection_family_filters: {', '.join(summary.get('selection_family_filters', [])) or '-'}\n"
        f"- selection_shard: {int(summary.get('selection_shard_index', 1) or 1)}/{int(summary.get('selection_shard_count', 1) or 1)}\n"
        f"- primary_cache_profile: {summary.get('primary_cache_profile', '')}\n"
        f"- published_view_strategy: {summary.get('published_view_strategy', '') or 'primary_profile'}\n"
        f"- published_cache_profiles: {', '.join(summary.get('published_cache_profiles', [])) or '-'}\n"
        f"- comparison_contract: {summary.get('comparison_contract', '') or '-'}\n"
        f"- comparison_primary_claim: {summary.get('comparison_primary_claim', '') or '-'}\n"
        f"- comparison: {summary.get('candidate_mode', '')} vs {summary.get('baseline_mode', '')}\n"
        f"- fairness_contract_passed: {bool(summary.get('fairness_contract_passed'))}\n"
        f"- fairness_findings: {', '.join(summary.get('fairness_findings', [])) or '-'}\n"
        f"- observed_path_sources: {', '.join(summary.get('observed_path_sources', [])) or '-'}\n"
        f"- preflight_evidence_modes: {', '.join(summary.get('preflight_evidence_modes', [])) or '-'}\n"
        f"- hard_quality_gate_cleared: {bool(summary.get('hard_quality_gate_cleared'))}\n"
        f"- hard_gate_failures: {', '.join(summary.get('hard_gate_failure_labels', [])) or '-'}\n"
        f"- secondary_guardrails_cleared: {bool(summary.get('secondary_guardrails_cleared'))}\n"
        f"- secondary_guardrail_failures: {', '.join(summary.get('secondary_guardrail_failure_labels', [])) or '-'}\n"
        f"- latency_delta_ms: {float(summary.get('latency_delta_ms', 0.0) or 0.0):.3f}\n"
        f"- avg_latency_delta_ms: {float(summary.get('avg_latency_delta_ms', 0.0) or 0.0):.3f}\n"
        f"- p95_latency_delta_ms: {float(summary.get('p95_latency_delta_ms', 0.0) or 0.0):.3f}\n"
        f"- full_pair_count: {int(summary.get('full_pair_count', 0) or 0)}\n"
        f"- full_pair_median_wall_clock_ms: {float(summary.get('full_pair_median_wall_clock_ms', 0.0) or 0.0):.3f}\n"
        f"- full_pair_p95_wall_clock_ms: {float(summary.get('full_pair_p95_wall_clock_ms', 0.0) or 0.0):.3f}\n"
        f"- full_pair_total_wall_clock_ms: {float(summary.get('full_pair_total_wall_clock_ms', 0.0) or 0.0):.3f}\n"
        f"- prompt_token_delta: {float(summary.get('prompt_token_delta', 0.0) or 0.0):.3f}\n"
        f"- total_payload_token_delta: {float(summary.get('total_payload_token_delta', 0.0) or 0.0):.3f}\n"
        f"- required_path_recall_delta: {float(summary.get('required_path_recall_delta', 0.0) or 0.0):.3f}\n"
        f"- required_path_precision_delta: {float(summary.get('required_path_precision_delta', 0.0) or 0.0):.3f}\n"
        f"- hallucinated_surface_rate_delta: {float(summary.get('hallucinated_surface_rate_delta', 0.0) or 0.0):.3f}\n"
        f"- validation_success_delta: {float(summary.get('validation_success_delta', 0.0) or 0.0):.3f}\n"
        f"- write_surface_precision_delta: {float(summary.get('write_surface_precision_delta', 0.0) or 0.0):.3f}\n"
        f"- unnecessary_widening_rate_delta: {float(summary.get('unnecessary_widening_rate_delta', 0.0) or 0.0):.3f}\n"
        f"- odylith_auto_grounded_rate: {float(summary.get('odylith_auto_grounded_rate', 0.0) or 0.0):.3f}\n"
        f"- odylith_requires_widening_rate: {float(summary.get('odylith_requires_widening_rate', 0.0) or 0.0):.3f}\n"
        f"- odylith_grounded_delegate_rate: {float(summary.get('odylith_grounded_delegate_rate', 0.0) or 0.0):.3f}\n"
        f"- critical_required_path_recall_delta: {float(summary.get('critical_required_path_recall_delta', 0.0) or 0.0):.3f}\n"
        f"- critical_validation_success_delta: {float(summary.get('critical_validation_success_delta', 0.0) or 0.0):.3f}\n"
        f"- robustness_warm_cold_consistency_cleared: {bool(summary.get('robustness_warm_cold_consistency_cleared'))}\n"
        f"- robustness_rerun_stability_state: {summary.get('robustness_rerun_stability_state', '')}\n"
        f"- runtime_memory_backed_retrieval_ready: {bool(summary.get('runtime_memory_backed_retrieval_ready'))}\n"
        f"- runtime_memory_backend: "
        f"{summary.get('runtime_memory_storage', '') or '-'} / {summary.get('runtime_memory_sparse_recall', '') or '-'}\n"
        f"- runtime_memory_indexed_entity_count: {int(summary.get('runtime_memory_indexed_entity_count', 0) or 0)}\n"
        f"- runtime_memory_evidence_document_count: {int(summary.get('runtime_memory_evidence_document_count', 0) or 0)}\n"
        f"- runtime_remote_retrieval: "
        f"{summary.get('runtime_remote_retrieval_status', '') or 'disabled'}"
        f"/{summary.get('runtime_remote_retrieval_mode', '') or 'disabled'}\n"
        f"- corpus_contract_status: {summary.get('corpus_contract_status', '')}\n"
        f"- corpus_seriousness_floor_passed: {bool(summary.get('corpus_seriousness_floor_passed'))}\n"
        f"- corpus_full_coverage_rate: {float(summary.get('corpus_full_coverage_rate', 0.0) or 0.0):.3f}\n"
        f"- corpus_implementation_scenario_count: {int(summary.get('corpus_implementation_scenario_count', 0) or 0)}\n"
        f"- corpus_write_plus_validator_scenario_count: {int(summary.get('corpus_write_plus_validator_scenario_count', 0) or 0)}\n"
        f"- corpus_correctness_critical_scenario_count: {int(summary.get('corpus_correctness_critical_scenario_count', 0) or 0)}"
    )


def run_benchmarks(
    *,
    repo_root: Path,
    modes: Sequence[str] = (),
    cache_profiles: Sequence[str] = (),
    case_ids: Sequence[str] = (),
    families: Sequence[str] = (),
    benchmark_profile: str = DEFAULT_BENCHMARK_PROFILE,
    shard_count: int = 1,
    shard_index: int = 1,
    limit: int = 0,
    write_report: bool = True,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    live_batching_available = (root / ".git").exists()
    normalized_profile = _normalize_benchmark_profile(benchmark_profile)
    normalized_shard_count = int(shard_count or 1)
    normalized_shard_index = int(shard_index or 1)
    requested_modes = [_normalize_mode(str(token).strip()) for token in modes if str(token).strip() in _VALID_MODES]
    explicit_mode_selection = bool(requested_modes)
    normalized_modes = list(dict.fromkeys(requested_modes)) or list(_PROFILE_DEFAULT_MODES[normalized_profile])
    requested_cache_profiles = [
        str(token).strip().lower() for token in cache_profiles if str(token).strip().lower() in _VALID_CACHE_PROFILES
    ]
    explicit_cache_profile_selection = bool(requested_cache_profiles)
    normalized_cache_profiles = (
        _normalize_cache_profiles(requested_cache_profiles)
        if explicit_cache_profile_selection
        else list(_PROFILE_DEFAULT_CACHE_PROFILES[normalized_profile])
    )
    primary_cache_profile = _primary_cache_profile(normalized_cache_profiles)
    corpus = odylith_context_cache.read_json_object(store.optimization_evaluation_corpus_path(repo_root=root))
    corpus_contract = odylith_benchmark_contract.benchmark_corpus_contract(corpus)
    all_scenarios = load_benchmark_scenarios(repo_root=root)
    selection_state = _resolve_benchmark_scenario_selection(
        all_scenarios=all_scenarios,
        benchmark_profile=normalized_profile,
        case_ids=case_ids,
        families=families,
        shard_count=normalized_shard_count,
        shard_index=normalized_shard_index,
        limit=limit,
    )
    all_case_ids = set(selection_state.get("all_case_ids", set()))
    selected_case_ids = set(selection_state.get("selected_case_ids", set()))
    selected_families = set(selection_state.get("selected_families", set()))
    profile_default_narrowing = str(selection_state.get("profile_default_narrowing", "")).strip()
    scenarios = [dict(row) for row in selection_state.get("scenarios", [])]
    if not scenarios:
        raise ValueError("No benchmark scenarios matched the requested selection.")
    normalized_cache_profiles = _cache_profiles_for_selection(
        profile=normalized_profile,
        selected_families=sorted(selected_families),
        cache_profiles=normalized_cache_profiles,
        explicit_cache_profile_selection=explicit_cache_profile_selection,
    )
    primary_cache_profile = _primary_cache_profile(normalized_cache_profiles)
    generated_utc = _utc_now()
    report_id = _benchmark_report_id(
        generated_utc=generated_utc,
        modes=normalized_modes,
        scenario_ids=[str(row.get("scenario_id", "")).strip() for row in scenarios],
        cache_profiles=normalized_cache_profiles,
    )
    full_corpus_selected = bool(selection_state.get("full_corpus_selected"))
    selection_strategy = str(selection_state.get("selection_strategy", "")).strip() or "manual_selection"
    latest_eligible = bool(
        normalized_profile == BENCHMARK_PROFILE_PROOF
        and full_corpus_selected
        and normalized_cache_profiles == list(DEFAULT_CACHE_PROFILES)
        and normalized_modes == list(DEFAULT_MODES)
    )
    profile_uses_live_public_modes = _profile_uses_live_public_modes_for_selection(
        profile=normalized_profile,
        selected_families=sorted(selected_families),
    )
    comparison_contract = (
        LIVE_COMPARISON_CONTRACT
        if profile_uses_live_public_modes
        else DIAGNOSTIC_COMPARISON_CONTRACT
    )
    total_results = len(scenarios) * len(normalized_modes) * len(normalized_cache_profiles)
    sharded_run = normalized_shard_count > 1
    lock_key = (
        f"{_BENCHMARK_LOCK_KEY}:{normalized_profile}:{normalized_shard_index}-of-{normalized_shard_count}"
        if sharded_run
        else _BENCHMARK_LOCK_KEY
    )
    with odylith_context_cache.advisory_lock(repo_root=root, key=lock_key), _benchmark_interrupt_guard():
        startup_hygiene = _cleanup_stale_benchmark_state(
            repo_root=root,
            clear_progress=not sharded_run,
            allow_destructive_runtime_cleanup=not sharded_run,
        )
        benchmark_runtime_storage = _require_benchmark_runtime_space(repo_root=root)
        progress_payload: dict[str, Any] = {
            "contract": PROGRESS_CONTRACT,
            "version": PROGRESS_VERSION,
            "report_id": report_id,
            "repo_root": str(root),
            "owning_pid": os.getpid(),
            "benchmark_profile": normalized_profile,
            "benchmark_profile_label": _benchmark_profile_label(normalized_profile),
            "benchmark_profile_description": _benchmark_profile_description(normalized_profile),
            "comparison_contract": comparison_contract,
            "started_utc": generated_utc,
            "updated_utc": generated_utc,
            "status": "running",
            "phase": "executing_scenarios",
            "modes": list(normalized_modes),
            "cache_profiles": list(normalized_cache_profiles),
            "primary_cache_profile": primary_cache_profile,
            "selection_strategy": selection_strategy,
            "shard_count": normalized_shard_count,
            "shard_index": normalized_shard_index,
            "scenario_count": len(scenarios),
            "total_results": total_results,
            "completed_cache_profiles": 0,
            "completed_scenarios": 0,
            "completed_results": 0,
            "current_cache_profile": "",
            "current_scenario_id": "",
            "current_mode": "",
            "latest_eligible": latest_eligible,
            "selection": {
                "case_ids": sorted(selected_case_ids),
                "scenario_ids": sorted(selected_case_ids),
                "family_filters": sorted(selected_families),
                "benchmark_profile": normalized_profile,
                "profile_default_narrowing": profile_default_narrowing,
                "selection_strategy": selection_strategy,
                "shard_count": normalized_shard_count,
                "shard_index": normalized_shard_index,
                "default_modes_applied": not explicit_mode_selection,
                "default_cache_profiles_applied": not explicit_cache_profile_selection,
                "limit": max(0, int(limit)),
                "full_corpus_selected": bool(full_corpus_selected),
                "available_scenario_count": len(all_scenarios),
                "cache_profiles": list(normalized_cache_profiles),
            },
            "benchmark_runtime_storage": dict(benchmark_runtime_storage),
        }
        initial_tree_identity = benchmark_tree_identity(
            repo_root=root,
            selection=dict(progress_payload.get("selection", {})),
        )
        progress_payload.update(
            {
                "git_branch": str(initial_tree_identity.get("git_branch", "")).strip(),
                "git_commit": str(initial_tree_identity.get("git_commit", "")).strip(),
                "git_dirty": bool(initial_tree_identity.get("git_dirty")),
                "repo_dirty_paths": [
                    str(token).strip()
                    for token in initial_tree_identity.get("repo_dirty_paths", [])
                    if isinstance(initial_tree_identity.get("repo_dirty_paths"), list) and str(token).strip()
                ],
                "selection_fingerprint": str(initial_tree_identity.get("selection_fingerprint", "")).strip(),
                "corpus_fingerprint": str(initial_tree_identity.get("corpus_fingerprint", "")).strip(),
                "snapshot_overlay_fingerprint": str(initial_tree_identity.get("snapshot_overlay_fingerprint", "")).strip(),
                "source_posture": str(initial_tree_identity.get("source_posture", "")).strip(),
            }
        )
        _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
        try:
            cache_profile_reports: dict[str, list[dict[str, Any]]] = {}
            cache_profile_mode_rows: dict[str, dict[str, list[dict[str, Any]]]] = {}
            completed_results = 0
            for profile_index, cache_profile in enumerate(normalized_cache_profiles, start=1):
                _prepare_benchmark_runtime_cache(repo_root=root, cache_profile=cache_profile)
                scenario_reports: list[dict[str, Any]] = []
                mode_rows: dict[str, list[dict[str, Any]]] = {mode: [] for mode in normalized_modes}
                use_live_public_modes = profile_uses_live_public_modes
                for scenario_index, scenario in enumerate(scenarios, start=1):
                    scenario_report = {
                        "cache_profile": cache_profile,
                        "scenario_id": scenario["scenario_id"],
                        "kind": scenario["kind"],
                        "label": scenario["label"],
                        "summary": scenario["summary"],
                        "family": scenario["family"],
                        "priority": scenario["priority"],
                        "prompt": str(scenario.get("prompt", "")).strip(),
                        "acceptance_criteria": list(scenario.get("acceptance_criteria", [])),
                        "required_paths": list(scenario.get("required_paths", [])),
                        "validation_commands": list(scenario.get("validation_commands", [])),
                        "needs_write": bool(scenario.get("needs_write")),
                        "changed_paths": list(scenario["changed_paths"]),
                        "workstream": scenario["workstream"],
                        "results": [],
                    }
                    live_batch_results: dict[str, dict[str, Any]] = {}
                    live_batch_modes = (
                        [normalized_mode for normalized_mode in normalized_modes if _is_live_public_mode(normalized_mode)]
                        if live_batching_available and use_live_public_modes and not sharded_run
                        else []
                    )
                    live_batch_executed = False
                    for mode in normalized_modes:
                        progress_payload.update(
                            {
                                "updated_utc": _utc_now(),
                                "phase": "executing_scenarios",
                                "current_cache_profile": cache_profile,
                                "current_scenario_id": str(scenario.get("scenario_id", "")).strip(),
                                "current_mode": str(mode).strip(),
                                "completed_cache_profiles": profile_index - 1,
                                "completed_scenarios": scenario_index - 1,
                                "completed_results": completed_results,
                            }
                        )
                        _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
                        normalized_mode = _normalize_mode(mode)
                        if normalized_mode in live_batch_modes:
                            if not live_batch_executed:
                                live_batch_results = _run_live_scenario_batch(
                                    repo_root=root,
                                    scenario=scenario,
                                    modes=live_batch_modes,
                                    benchmark_profile=normalized_profile,
                                    report_id=report_id,
                                    cache_profile=cache_profile,
                                    shard_index=normalized_shard_index,
                                    shard_count=normalized_shard_count,
                                )
                                live_batch_executed = True
                            result = dict(live_batch_results.get(normalized_mode, {}))
                            if not result:
                                raise RuntimeError(
                                    f"live benchmark batch did not produce a result for mode `{normalized_mode}`"
                                )
                        elif not use_live_public_modes and _is_live_public_mode(normalized_mode):
                            if str(scenario.get("kind", "")).strip() == "architecture":
                                result = _architecture_result(repo_root=root, scenario=scenario, mode=mode)
                            else:
                                result = _call_with_supported_kwargs(
                                    _packet_result,
                                    repo_root=root,
                                    scenario=scenario,
                                    mode=mode,
                                    report_id=report_id,
                                    cache_profile=cache_profile,
                                    shard_index=normalized_shard_index,
                                    shard_count=normalized_shard_count,
                                )
                        else:
                            result = _call_with_supported_kwargs(
                                _run_scenario_mode,
                                repo_root=root,
                                scenario=scenario,
                                mode=mode,
                                benchmark_profile=normalized_profile,
                                report_id=report_id,
                                cache_profile=cache_profile,
                                shard_index=normalized_shard_index,
                                shard_count=normalized_shard_count,
                            )
                        result["cache_profile"] = cache_profile
                        result["scenario_family"] = str(scenario.get("family", "")).strip()
                        result["scenario_priority"] = str(scenario.get("priority", "")).strip()
                        result["required_path_count"] = len([str(token).strip() for token in scenario.get("required_paths", []) if str(token).strip()])
                        result["validation_command_count"] = len(
                            [str(token).strip() for token in scenario.get("validation_commands", []) if str(token).strip()]
                        )
                        result["needs_write"] = bool(scenario.get("needs_write"))
                        result["correctness_critical"] = bool(scenario.get("correctness_critical"))
                        scenario_report["results"].append(result)
                        mode_rows.setdefault(mode, []).append(result)
                        completed_results += 1
                    scenario_reports.append(scenario_report)
                    progress_payload.update(
                        {
                            "updated_utc": _utc_now(),
                            "phase": "aggregating_results",
                            "current_cache_profile": cache_profile,
                            "completed_cache_profiles": profile_index - 1,
                            "completed_scenarios": scenario_index,
                            "completed_results": completed_results,
                        }
                    )
                    _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
                cache_profile_reports[cache_profile] = scenario_reports
                cache_profile_mode_rows[cache_profile] = mode_rows
            progress_payload.update(
                {
                    "updated_utc": _utc_now(),
                    "phase": "computing_post_run_metrics",
                    "current_cache_profile": "",
                    "current_scenario_id": "",
                    "current_mode": "",
                    "completed_cache_profiles": len(normalized_cache_profiles),
                    "completed_scenarios": len(scenarios),
                    "completed_results": completed_results,
                }
            )
            _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
            post_run_probe_eligible = bool(not sharded_run and selection_strategy == "full_corpus")
            latency_probes = (
                _singleton_family_latency_probes(
                    repo_root=root,
                    scenarios=scenarios,
                    modes=normalized_modes,
                    cache_profiles=normalized_cache_profiles,
                    benchmark_profile=normalized_profile,
                )
                if post_run_probe_eligible
                else {}
            )
            final_hygiene = (
                {}
                if sharded_run
                else _enforce_diagnostic_runtime_hygiene(repo_root=root, ignore_progress=progress_payload)
                if normalized_profile == BENCHMARK_PROFILE_DIAGNOSTIC
                else _benchmark_runtime_hygiene_snapshot(repo_root=root)
            )
            corpus_summary = _corpus_summary(scenarios=scenarios)
            corpus_composition = _corpus_composition(
                scenarios=scenarios,
                available_scenarios=all_scenarios,
            )
            primary_scenario_reports = cache_profile_reports.get(primary_cache_profile, [])
            primary_mode_rows = cache_profile_mode_rows.get(primary_cache_profile, {})
            mode_summaries = {
                mode: _mode_summary(mode=mode, scenario_rows=rows)
                for mode, rows in primary_mode_rows.items()
            }
            primary_comparison = _primary_comparison(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                mode_summaries=mode_summaries,
            )
            cache_profile_summaries: dict[str, dict[str, Any]] = {}
            for cache_profile in normalized_cache_profiles:
                profile_mode_rows = cache_profile_mode_rows.get(cache_profile, {})
                profile_mode_summaries = {
                    mode: _mode_summary(mode=mode, scenario_rows=rows)
                    for mode, rows in profile_mode_rows.items()
                }
                profile_family_summaries = _family_summaries(modes=normalized_modes, mode_rows=profile_mode_rows)
                profile_family_summaries = _apply_singleton_family_latency_probes(
                    family_summaries=profile_family_summaries,
                    latency_probes=latency_probes,
                    cache_profile=cache_profile,
                )
                profile_primary_comparison = _primary_comparison(
                    candidate_mode=_ODYLITH_ON_MODE,
                    baseline_mode=_BASELINE_MODE,
                    mode_summaries=profile_mode_summaries,
                )
                profile_fairness_findings = _fairness_findings(
                    repo_root=root,
                    comparison_contract=comparison_contract,
                    published_scenarios=cache_profile_reports.get(cache_profile, []),
                )
                profile_packet_source_summaries = benchmark_group_summaries.grouped_summaries(
                    modes=normalized_modes,
                    mode_rows=profile_mode_rows,
                    group_field="packet_source",
                    row_kind="packet",
                    summarize=_mode_summary,
                )
                profile_execution_contracts = _live_execution_contracts(profile_mode_rows)
                cache_profile_summaries[cache_profile] = {
                    "scenario_count": len(cache_profile_reports.get(cache_profile, [])),
                    "mode_summaries": profile_mode_summaries,
                    "family_summaries": profile_family_summaries,
                    "packet_source_summaries": profile_packet_source_summaries,
                    "execution_contracts": profile_execution_contracts,
                    "family_deltas": _family_deltas(
                        candidate_mode=_ODYLITH_ON_MODE,
                        baseline_mode=_BASELINE_MODE,
                        family_summaries=profile_family_summaries,
                    ),
                    "primary_comparison": profile_primary_comparison,
                    "fairness_contract_passed": not profile_fairness_findings,
                    "fairness_findings": profile_fairness_findings,
                    "acceptance": _acceptance(
                        mode_summaries=profile_mode_summaries,
                        primary_comparison=profile_primary_comparison,
                        family_summaries=profile_family_summaries,
                        corpus_summary=corpus_summary,
                        fairness_findings=profile_fairness_findings,
                        packet_source_summaries=profile_packet_source_summaries,
                        execution_contracts=profile_execution_contracts,
                        comparison_contract=comparison_contract,
                    ),
                }
            family_summaries = (
                dict(dict(cache_profile_summaries.get(primary_cache_profile, {})).get("family_summaries", {}))
                if isinstance(cache_profile_summaries.get(primary_cache_profile), Mapping)
                else {}
            )
            published_scenarios = _aggregate_published_scenarios(
                scenarios=scenarios,
                modes=normalized_modes,
                cache_profiles=normalized_cache_profiles,
                cache_profile_reports=cache_profile_reports,
            )
            published_scenarios = _apply_singleton_latency_probes_to_published_scenarios(
                published_scenarios=published_scenarios,
                latency_probes=latency_probes,
            )
            fairness_findings = _fairness_findings(
                repo_root=root,
                comparison_contract=comparison_contract,
                published_scenarios=published_scenarios,
            )
            published_mode_rows: dict[str, list[dict[str, Any]]] = {mode: [] for mode in normalized_modes}
            for scenario_report in published_scenarios:
                for result in scenario_report.get("results", []):
                    if not isinstance(result, Mapping):
                        continue
                    mode = str(result.get("mode", "")).strip()
                    if not mode:
                        continue
                    published_mode_rows.setdefault(mode, []).append(dict(result))
            published_mode_summaries = {
                mode: _mode_summary(mode=mode, scenario_rows=rows)
                for mode, rows in published_mode_rows.items()
            }
            published_family_summaries = _family_summaries(
                modes=normalized_modes,
                mode_rows=published_mode_rows,
            )
            packet_source_summaries = benchmark_group_summaries.grouped_summaries(
                modes=normalized_modes,
                mode_rows=primary_mode_rows,
                group_field="packet_source",
                row_kind="packet",
                summarize=_mode_summary,
            )
            published_packet_source_summaries = benchmark_group_summaries.grouped_summaries(
                modes=normalized_modes,
                mode_rows=published_mode_rows,
                group_field="packet_source",
                row_kind="packet",
                summarize=_mode_summary,
            )
            published_comparison = _primary_comparison(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                mode_summaries=published_mode_summaries,
            )
            published_execution_contracts = _live_execution_contracts(published_mode_rows)
            family_deltas = _family_deltas(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                family_summaries=family_summaries,
            )
            published_family_deltas = _family_deltas(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                family_summaries=published_family_summaries,
            )
            packet_source_deltas = benchmark_group_summaries.grouped_deltas(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                grouped_summaries=packet_source_summaries,
                compare=_summary_comparison,
            )
            published_packet_source_deltas = benchmark_group_summaries.grouped_deltas(
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                grouped_summaries=published_packet_source_summaries,
                compare=_summary_comparison,
            )
            adoption_proof = (
                _run_live_adoption_proof(repo_root=root, scenarios=scenarios)
                if post_run_probe_eligible
                else {}
            )
            runtime_posture = {} if sharded_run else _runtime_posture_summary(repo_root=root)
            if not sharded_run and int(adoption_proof.get("sample_size", 0) or 0) > 0:
                runtime_posture["route_ready_rate"] = float(adoption_proof.get("route_ready_rate", 0.0) or 0.0)
                runtime_posture["native_spawn_ready_rate"] = float(
                    adoption_proof.get("native_spawn_ready_rate", 0.0) or 0.0
                )
            acceptance = _acceptance(
                mode_summaries=published_mode_summaries,
                primary_comparison=published_comparison,
                family_summaries=published_family_summaries,
                corpus_summary=corpus_summary,
                fairness_findings=fairness_findings,
                runtime_posture=runtime_posture,
                packet_source_summaries=published_packet_source_summaries,
                cache_profile_summaries=cache_profile_summaries,
                execution_contracts=published_execution_contracts,
                comparison_contract=comparison_contract,
            )
            observed_path_sources = sorted(
                {
                    str(token).strip()
                    for scenario_report in published_scenarios
                    for result in scenario_report.get("results", [])
                    if isinstance(result, Mapping)
                    for token in result.get("observed_path_sources", [])
                    if isinstance(result.get("observed_path_sources"), list) and str(token).strip()
                }
            )
            preflight_evidence_modes = sorted(
                {
                    str(result.get("preflight_evidence_mode", "")).strip()
                    for scenario_report in published_scenarios
                    for result in scenario_report.get("results", [])
                    if isinstance(result, Mapping) and str(result.get("preflight_evidence_mode", "")).strip()
                }
            )
            preflight_evidence_commands = sorted(
                {
                    str(token).strip()
                    for scenario_report in published_scenarios
                    for result in scenario_report.get("results", [])
                    if isinstance(result, Mapping)
                    for token in result.get("preflight_evidence_commands", [])
                    if isinstance(result.get("preflight_evidence_commands"), list) and str(token).strip()
                }
            )
            preflight_evidence_result_statuses = sorted(
                {
                    str(result.get("preflight_evidence_result_status", "")).strip()
                    for scenario_report in published_scenarios
                    for result in scenario_report.get("results", [])
                    if isinstance(result, Mapping) and str(result.get("preflight_evidence_result_status", "")).strip()
                }
            )
            snapshot_overlay_paths = _report_snapshot_overlay_paths(published_scenarios)
            tree_identity = benchmark_tree_identity(
                repo_root=root,
                selection=dict(progress_payload.get("selection", {})),
                snapshot_paths=snapshot_overlay_paths,
            )
            robustness_summary = (
                {}
                if sharded_run
                else _robustness_summary(
                    cache_profile_summaries=cache_profile_summaries,
                    candidate_mode=_ODYLITH_ON_MODE,
                    latency_probes=latency_probes,
                )
            )
            published_mode_table = _published_mode_table(
                mode_summaries=published_mode_summaries,
                mode_order=_PUBLIC_PUBLISHED_MODE_ORDER,
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
                comparison_contract=comparison_contract,
            )
            published_pair_timing_summary = _pair_timing_summary(
                scenarios=published_scenarios,
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
            )
            full_pair_timing_summary = _pair_timing_summary(
                scenarios=[
                    scenario
                    for cache_profile in normalized_cache_profiles
                    for scenario in cache_profile_reports.get(cache_profile, [])
                    if isinstance(scenario, Mapping)
                ],
                candidate_mode=_ODYLITH_ON_MODE,
                baseline_mode=_BASELINE_MODE,
            )
            tracked_mode_table = _published_mode_table(
                mode_summaries=published_mode_summaries,
                mode_order=normalized_modes,
                comparison_contract=comparison_contract,
            )
            report = {
                "contract": REPORT_CONTRACT,
                "version": REPORT_VERSION,
                "generated_utc": generated_utc,
                "repo_root": str(root),
                "benchmark_profile": normalized_profile,
                "benchmark_profile_label": _benchmark_profile_label(normalized_profile),
                "benchmark_profile_description": _benchmark_profile_description(normalized_profile),
                "comparison_contract": comparison_contract,
                "comparison_contract_details": _comparison_contract_details(comparison_contract),
                "selection_strategy": selection_strategy,
                "product_version": _product_version_from_pyproject(repo_root=root),
                "corpus_path": str(store.optimization_evaluation_corpus_path(repo_root=root)),
                "git_branch": str(tree_identity.get("git_branch", "")).strip(),
                "git_commit": str(tree_identity.get("git_commit", "")).strip(),
                "git_dirty": bool(tree_identity.get("git_dirty")),
                "repo_dirty_paths": [
                    str(token).strip()
                    for token in tree_identity.get("repo_dirty_paths", [])
                    if isinstance(tree_identity.get("repo_dirty_paths"), list) and str(token).strip()
                ],
                "selection_fingerprint": str(tree_identity.get("selection_fingerprint", "")).strip(),
                "corpus_fingerprint": str(tree_identity.get("corpus_fingerprint", "")).strip(),
                "snapshot_overlay_fingerprint": str(tree_identity.get("snapshot_overlay_fingerprint", "")).strip(),
                "snapshot_overlay_paths": snapshot_overlay_paths,
                "source_posture": str(tree_identity.get("source_posture", "")).strip(),
                "scenario_count": len(primary_scenario_reports),
                "corpus_summary": corpus_summary,
                "corpus_composition": corpus_composition,
                "corpus_contract": corpus_contract,
                "fairness_contract_passed": not fairness_findings,
                "fairness_findings": fairness_findings,
                "observed_path_sources": observed_path_sources,
                "preflight_evidence_mode": preflight_evidence_modes[0]
                if len(preflight_evidence_modes) == 1
                else "mixed"
                if preflight_evidence_modes
                else "none",
                "preflight_evidence_commands": preflight_evidence_commands,
                "preflight_evidence_result_status": preflight_evidence_result_statuses[0]
                if len(preflight_evidence_result_statuses) == 1
                else "mixed"
                if preflight_evidence_result_statuses
                else "not_applicable",
                "preflight_evidence_modes": preflight_evidence_modes,
                "modes": normalized_modes,
                "cache_profiles": list(normalized_cache_profiles),
                "primary_cache_profile": primary_cache_profile,
                "selection": {
                    "case_ids": sorted(selected_case_ids),
                    "scenario_ids": sorted(selected_case_ids),
                    "family_filters": sorted(selected_families),
                    "benchmark_profile": normalized_profile,
                    "profile_default_narrowing": profile_default_narrowing,
                    "selection_strategy": selection_strategy,
                    "shard_count": normalized_shard_count,
                    "shard_index": normalized_shard_index,
                    "default_modes_applied": not explicit_mode_selection,
                    "default_cache_profiles_applied": not explicit_cache_profile_selection,
                    "limit": max(0, int(limit)),
                    "full_corpus_selected": bool(full_corpus_selected),
                    "available_scenario_count": len(all_scenarios),
                    "cache_profiles": list(normalized_cache_profiles),
                },
                "latest_eligible": latest_eligible,
                "scenarios": primary_scenario_reports,
                "published_view_strategy": _published_view_strategy(cache_profiles=normalized_cache_profiles),
                "published_cache_profiles": list(normalized_cache_profiles),
                "published_scenarios": published_scenarios,
                "cache_profile_scenarios": cache_profile_reports,
                "cache_profile_summaries": cache_profile_summaries,
                "singleton_family_latency_probes": latency_probes,
                "mode_summaries": mode_summaries,
                "published_mode_summaries": published_mode_summaries,
                "published_mode_table": published_mode_table,
                "published_mode_table_markdown": _published_mode_table_markdown(published_mode_table),
                "published_pair_timing_summary": published_pair_timing_summary,
                "full_pair_timing_summary": full_pair_timing_summary,
                "tracked_mode_table": tracked_mode_table,
                "tracked_mode_table_markdown": _published_mode_table_markdown(tracked_mode_table),
                "family_summaries": family_summaries,
                "published_family_summaries": published_family_summaries,
                "packet_source_summaries": packet_source_summaries,
                "published_packet_source_summaries": published_packet_source_summaries,
                "execution_contracts": published_execution_contracts,
                "family_deltas": family_deltas,
                "published_family_deltas": published_family_deltas,
                "packet_source_deltas": packet_source_deltas,
                "published_packet_source_deltas": published_packet_source_deltas,
                "primary_comparison": primary_comparison,
                "published_comparison": published_comparison,
                "comparison": published_comparison,
                "adoption_proof": adoption_proof,
                "runtime_posture": runtime_posture,
                "startup_hygiene": startup_hygiene,
                "final_hygiene": final_hygiene,
                "robustness_summary": robustness_summary,
                "status": str(acceptance.get("status", "")).strip() or "unknown",
                "acceptance": acceptance,
                "selection_family_filters": sorted(selected_families),
                "hard_quality_gate_cleared": bool(acceptance.get("hard_quality_gate_cleared")),
                "hard_gate_cleared": bool(acceptance.get("hard_quality_gate_cleared")),
                "hard_gate_failures": [
                    str(token).strip()
                    for token in acceptance.get("hard_gate_failures", [])
                    if isinstance(acceptance.get("hard_gate_failures"), list) and str(token).strip()
                ],
                "hard_gate_failure_labels": [
                    str(token).strip()
                    for token in acceptance.get("hard_gate_failure_labels", [])
                    if isinstance(acceptance.get("hard_gate_failure_labels"), list) and str(token).strip()
                ],
                "report_id": report_id,
            }
            report["published_summary"] = compact_report_summary(report)
            report["summary_text"] = _render_report_summary(report)
            history_path = history_report_path(repo_root=root, report_id=report_id)
            history_report_written = False
            if write_report:
                progress_payload.update(
                    {
                        "updated_utc": _utc_now(),
                        "phase": "persisting_report",
                    }
                )
                _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
                odylith_context_cache.write_json_if_changed(
                    repo_root=root,
                    path=history_path,
                    payload=report,
                    lock_key=str(history_path),
                )
                history_report_written = True
                progress_payload.update(
                    {
                        "history_report_path": str(history_path),
                        "history_report_written": True,
                    }
                )
                latest_path = latest_report_path(repo_root=root)
                profile_latest_path = latest_report_path(
                    repo_root=root,
                    benchmark_profile=normalized_profile,
                )
                publish_latest = not sharded_run and (
                    bool(report.get("latest_eligible"))
                    or (not latest_path.exists() and normalized_cache_profiles == list(DEFAULT_CACHE_PROFILES))
                )
                if not sharded_run:
                    odylith_context_cache.write_json_if_changed(
                        repo_root=root,
                        path=profile_latest_path,
                        payload=report,
                        lock_key=str(profile_latest_path),
                    )
                if publish_latest:
                    odylith_context_cache.write_json_if_changed(
                        repo_root=root,
                        path=latest_path,
                        payload=report,
                        lock_key=str(latest_path),
                    )
            progress_payload.update(
                {
                    "updated_utc": _utc_now(),
                    "phase": "final_cleanup",
                    "status": str(report.get("status", "")).strip() or "unknown",
                    "history_report_path": str(history_path),
                    "history_report_written": history_report_written,
                }
            )
            _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
            if not sharded_run:
                _clear_progress(repo_root=root)
            return report
        except BaseException as exc:
            progress_payload.update(
                {
                    "updated_utc": _utc_now(),
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            if write_report and not _history_report_exists_for_progress(repo_root=root, progress=progress_payload):
                failed_report = _failed_benchmark_report(
                    repo_root=root,
                    report_id=report_id,
                    benchmark_profile=normalized_profile,
                    comparison_contract=comparison_contract,
                    modes=normalized_modes,
                    cache_profiles=normalized_cache_profiles,
                    primary_cache_profile=primary_cache_profile,
                    scenarios=scenarios,
                    all_scenarios=all_scenarios,
                    progress_payload=progress_payload,
                    selection_strategy=selection_strategy,
                    latest_eligible=latest_eligible,
                    startup_hygiene=startup_hygiene,
                    corpus_contract=corpus_contract,
                    tree_identity=initial_tree_identity,
                    error=exc,
                )
                history_path = history_report_path(repo_root=root, report_id=report_id)
                odylith_context_cache.write_json_if_changed(
                    repo_root=root,
                    path=history_path,
                    payload=failed_report,
                    lock_key=str(history_path),
                )
                progress_payload.update(
                    {
                        "history_report_path": str(history_path),
                        "history_report_written": True,
                    }
                )
            _write_progress(repo_root=root, payload=progress_payload, write_shared=not sharded_run)
            raise
        finally:
            _clear_active_run_progress(repo_root=root, payload=progress_payload)
            _cleanup_stale_benchmark_state(
                repo_root=root,
                clear_progress=not sharded_run,
                allow_destructive_runtime_cleanup=not sharded_run,
            )


__all__ = [
    "BENCHMARK_PROFILES",
    "BENCHMARK_PROFILE_DIAGNOSTIC",
    "BENCHMARK_PROFILE_PROOF",
    "BENCHMARK_PROFILE_QUICK",
    "DEFAULT_CACHE_PROFILES",
    "DEFAULT_BENCHMARK_PROFILE",
    "DEFAULT_CLI_BENCHMARK_PROFILE",
    "DEFAULT_MODES",
    "DIAGNOSTIC_CONTROL_MODES",
    "PUBLIC_CLI_MODES",
    "PROGRESS_CONTRACT",
    "PROGRESS_VERSION",
    "REPORT_CONTRACT",
    "REPORT_VERSION",
    "benchmark_root",
    "compact_progress_summary",
    "compact_report_summary",
    "history_report_path",
    "load_benchmark_progress",
    "latest_report_path",
    "load_benchmark_scenarios",
    "load_latest_benchmark_report",
    "profile_latest_report_path",
    "progress_report_path",
    "run_benchmarks",
]
