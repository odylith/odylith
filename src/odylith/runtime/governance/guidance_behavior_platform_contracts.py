"""Guidance Behavior Platform Contracts helpers for the Odylith governance layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping


PLATFORM_CONTRACT = "odylith_guidance_behavior_platform_end_to_end.v1"
CHECK_ID = "guidance_behavior_platform_end_to_end"

PLATFORM_CONTRACTS: tuple[dict[str, Any], ...] = (
    {
        "domain": "benchmark_eval",
        "purpose": (
            "The guidance_behavior family stays inside the existing benchmark/eval path with "
            "curated low-latency support docs and no separate public proof lane."
        ),
        "source_tokens": {
            "src/odylith/runtime/evaluation/odylith_benchmark_taxonomy.py": (
                "guidance_behavior",
                "Grounding / Orchestration Control",
            ),
            "src/odylith/runtime/evaluation/odylith_benchmark_prompt_family_rules.py": (
                "guidance_behavior",
                "guidance-behavior-evaluation-corpus.v1.json",
                "validate_guidance_behavior.py",
            ),
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py": (
                "guidance_behavior_runtime.summary_from_sources",
                "_profile_uses_live_public_modes_for_selection",
                "_cache_profiles_for_selection",
            ),
            "src/odylith/runtime/evaluation/odylith_benchmark_isolation.py": (
                "_BENCHMARK_SELF_REFERENCE_GLOBS",
                "guidance-behavior-evaluation-corpus.v1.json",
                "optimization-evaluation-corpus.v1.json",
            ),
            "tests/unit/runtime/test_odylith_benchmark_corpus.py": (
                "guidance_behavior_family_filter_selects_only_guidance_cases",
                "guidance_behavior_family_is_curated_low_latency_and_taxonomized",
                "guidance_behavior_observed_paths_include_runtime_summary_sources",
            ),
        },
    },
    {
        "domain": "host_lane_bundle_mirrors",
        "purpose": (
            "Codex, Claude, product-repo dogfood, source-local maintainer mode, and installed "
            "consumer lanes receive the same guidance-behavior skill and command surfaces."
        ),
        "source_tokens": {
            ".agents/skills/odylith-guidance-behavior/SKILL.md": (
                "description: Use when",
                "@../../../odylith/skills/odylith-guidance-behavior/SKILL.md",
            ),
            ".claude/skills/odylith-guidance-behavior/SKILL.md": (
                "description: Use when",
                "@../../../odylith/skills/odylith-guidance-behavior/SKILL.md",
            ),
            ".claude/commands/odylith-guidance-behavior.md": (
                "odylith validate guidance-behavior --repo-root .",
                "odylith benchmark --profile quick --family guidance_behavior",
            ),
            "src/odylith/bundle/assets/project-root/.agents/skills/odylith-guidance-behavior/SKILL.md": (
                "description: Use when",
                "@../../../odylith/skills/odylith-guidance-behavior/SKILL.md",
            ),
            "src/odylith/bundle/assets/project-root/.claude/skills/odylith-guidance-behavior/SKILL.md": (
                "description: Use when",
                "@../../../odylith/skills/odylith-guidance-behavior/SKILL.md",
            ),
            "src/odylith/bundle/assets/project-root/.claude/commands/odylith-guidance-behavior.md": (
                "odylith validate guidance-behavior --repo-root .",
                "odylith benchmark --profile quick --family guidance_behavior",
            ),
            "odylith/skills/odylith-guidance-behavior/SKILL.md": (
                "Keep Codex and Claude behavior aligned",
                "consumer lane",
                "pinned dogfood",
                "source-local",
            ),
            "src/odylith/bundle/assets/odylith/skills/odylith-guidance-behavior/SKILL.md": (
                "Keep Codex and Claude behavior aligned",
                "consumer lane",
                "pinned dogfood",
                "source-local",
            ),
            "src/odylith/install/agents.py": (
                "guidance behavior pressure cases",
                "odylith validate guidance-behavior --repo-root .",
                "odylith benchmark --profile quick --family guidance_behavior",
            ),
            "src/odylith/install/manager.py": (
                "guidance behavior pressure cases",
                "odylith validate guidance-behavior --repo-root .",
                "odylith benchmark --profile quick --family guidance_behavior",
            ),
            "src/odylith/runtime/governance/guidance_behavior_platform_contracts.py": (
                "ODYLITH_BUNDLE_MIRROR_PARITY_PATHS",
                "PROJECT_ROOT_BUNDLE_MIRROR_PARITY_PATHS",
                "platform source bundle parity mirror is stale",
            ),
            "tests/unit/runtime/test_validate_guidance_behavior.py": (
                "test_platform_lint_rejects_stale_source_bundle_mirrors",
                "ODYLITH_BUNDLE_MIRROR_PARITY_PATHS",
            ),
        },
    },
    {
        "domain": "hot_path_efficiency",
        "purpose": (
            "The guidance_behavior packet path carries compact cross-layer proof while avoiding "
            "projection-store opens, host capability probes, delivery-ledger reads, session widening, "
            "and full validation on the live hot path."
        ),
        "source_tokens": {
            "src/odylith/runtime/context_engine/odylith_context_engine_packet_adaptive_runtime.py": (
                "skip_runtime_warmup=family == \"guidance_behavior\"",
            ),
            "src/odylith/runtime/context_engine/odylith_context_engine_grounding_runtime.py": (
                "projection_connection_required",
                "connection = _connect(root) if projection_connection_required else None",
            ),
            "src/odylith/runtime/context_engine/odylith_context_engine_hot_path_delivery_runtime.py": (
                "_hot_path_guidance_behavior_validator_available",
                "_hot_path_selected_validation_count",
            ),
            "src/odylith/runtime/context_engine/tooling_context_packet_builder.py": (
                "has_candidate_anchor",
                "return proof_state.resolve_scope_collection_proof_state([])",
            ),
            "src/odylith/runtime/context_engine/tooling_context_routing.py": (
                "native_spawn_probe_needed",
                "execution_profile_probe_needed",
            ),
            "src/odylith/runtime/execution_engine/runtime_surface_governance.py": (
                "guidance_behavior_summary_present",
                "ExecutionHostProfile.detected",
            ),
            "tests/unit/runtime/test_context_engine_split_hardening.py": (
                "test_adaptive_guidance_behavior_packet_skips_runtime_warmup",
                "test_guidance_behavior_impact_packet_avoids_projection_connection",
            ),
            "tests/unit/runtime/test_odylith_benchmark_corpus.py": (
                "test_guidance_behavior_validator_summary_prevents_hot_path_widening",
            ),
            "tests/unit/runtime/test_tooling_context_packet_builder.py": (
                "test_packet_proof_state_avoids_delivery_artifact_when_no_anchor_exists",
            ),
            "tests/unit/runtime/test_tooling_context_routing.py": (
                "test_build_routing_handoff_avoids_host_probe_when_delegate_gates_fail",
                "test_native_spawn_execution_ready_avoids_host_probe_when_delegate_gates_fail",
            ),
            "tests/unit/runtime/test_execution_engine.py": (
                "test_execution_engine_guidance_behavior_narrowing_snapshot_avoids_host_probe",
            ),
        },
    },
)

ODYLITH_BUNDLE_MIRROR_PARITY_PATHS: tuple[str, ...] = (
    "odylith/AGENTS.md",
    "odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md",
    "odylith/agents-guidelines/CODEX_HOST_CONTRACT.md",
    "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
    "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
    "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
    "odylith/agents-guidelines/VALIDATION_AND_TESTING.md",
    "odylith/radar/source/programs/B-096.execution-waves.v1.json",
    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
    "odylith/registry/source/components/compass/CURRENT_SPEC.md",
    "odylith/registry/source/components/execution-engine/CURRENT_SPEC.md",
    "odylith/registry/source/components/governance-intervention-engine/CURRENT_SPEC.md",
    "odylith/registry/source/components/odylith-context-engine/CURRENT_SPEC.md",
    "odylith/registry/source/components/odylith-memory-contracts/CURRENT_SPEC.md",
    "odylith/registry/source/components/tribunal/CURRENT_SPEC.md",
    "odylith/runtime/source/guidance-behavior-evaluation-corpus.v1.json",
    "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
    "odylith/skills/odylith-context-engine-operations/SKILL.md",
    "odylith/skills/odylith-guidance-behavior/SKILL.md",
    "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
)

PROJECT_ROOT_BUNDLE_MIRROR_PARITY_PATHS: tuple[str, ...] = (
    ".agents/skills/odylith-guidance-behavior/SKILL.md",
    ".claude/commands/odylith-guidance-behavior.md",
    ".claude/skills/odylith-guidance-behavior/SKILL.md",
)


def _dedupe_strings(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def platform_contract_summary() -> dict[str, Any]:
    source_refs = _dedupe_strings(
        [
            path
            for contract in PLATFORM_CONTRACTS
            for path in dict(contract.get("source_tokens", {})).keys()
        ]
    )
    return {
        "contract": PLATFORM_CONTRACT,
        "domains": [str(contract.get("domain", "")).strip() for contract in PLATFORM_CONTRACTS],
        "source_refs": source_refs,
        "bundle_mirror_refs": list(ODYLITH_BUNDLE_MIRROR_PARITY_PATHS),
        "project_root_bundle_mirror_refs": list(PROJECT_ROOT_BUNDLE_MIRROR_PARITY_PATHS),
        "hot_path": {
            "full_validation": False,
            "provider_calls": False,
            "repo_wide_scan": False,
            "summary_only": True,
        },
    }


def _odylith_bundle_mirror_path(relative_path: str) -> str:
    prefix = "odylith/"
    if not relative_path.startswith(prefix):
        return ""
    return f"src/odylith/bundle/assets/odylith/{relative_path[len(prefix):]}"


def _project_root_bundle_mirror_path(relative_path: str) -> str:
    return f"src/odylith/bundle/assets/project-root/{relative_path}"


def _append_mirror_parity_failures(
    *,
    repo_root: Path,
    failures: list[dict[str, str]],
    evidence: list[str],
) -> None:
    for relative_path in ODYLITH_BUNDLE_MIRROR_PARITY_PATHS:
        mirror_relative_path = _odylith_bundle_mirror_path(relative_path)
        if not mirror_relative_path:
            continue
        _append_one_mirror_parity_failure(
            repo_root=repo_root,
            failures=failures,
            evidence=evidence,
            relative_path=relative_path,
            mirror_relative_path=mirror_relative_path,
        )
    for relative_path in PROJECT_ROOT_BUNDLE_MIRROR_PARITY_PATHS:
        _append_one_mirror_parity_failure(
            repo_root=repo_root,
            failures=failures,
            evidence=evidence,
            relative_path=relative_path,
            mirror_relative_path=_project_root_bundle_mirror_path(relative_path),
        )


def _append_one_mirror_parity_failure(
    *,
    repo_root: Path,
    failures: list[dict[str, str]],
    evidence: list[str],
    relative_path: str,
    mirror_relative_path: str,
) -> None:
    live_path = repo_root / relative_path
    mirror_path = repo_root / mirror_relative_path
    if not live_path.is_file():
        failures.append(
            {
                "check_id": CHECK_ID,
                "message": "platform source bundle parity live file is missing",
                "path": relative_path,
            }
        )
        return
    if not mirror_path.is_file():
        failures.append(
            {
                "check_id": CHECK_ID,
                "message": "platform source bundle parity mirror file is missing",
                "path": mirror_relative_path,
            }
        )
        return
    if live_path.read_bytes() != mirror_path.read_bytes():
        failures.append(
            {
                "check_id": CHECK_ID,
                "message": "platform source bundle parity mirror is stale",
                "path": mirror_relative_path,
            }
        )
        return
    evidence.append(mirror_relative_path)


def validate_platform_contracts(*, repo_root: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    evidence: list[str] = []
    for contract in PLATFORM_CONTRACTS:
        domain = str(contract.get("domain", "")).strip()
        source_tokens = contract.get("source_tokens", {})
        if not isinstance(source_tokens, Mapping):
            failures.append(
                {
                    "check_id": CHECK_ID,
                    "message": f"platform domain `{domain}` does not declare source token checks",
                }
            )
            continue
        for raw_path, raw_tokens in source_tokens.items():
            relative_path = str(raw_path or "").strip()
            path = repo_root / relative_path
            if not path.is_file():
                failures.append(
                    {
                        "check_id": CHECK_ID,
                        "message": f"platform domain `{domain}` integration file is missing",
                        "path": relative_path,
                    }
                )
                continue
            text = path.read_text(encoding="utf-8")
            missing_tokens = [
                str(token)
                for token in raw_tokens
                if str(token) and str(token) not in text
            ]
            if missing_tokens:
                failures.append(
                    {
                        "check_id": CHECK_ID,
                        "message": f"platform domain `{domain}` is missing integration token(s): {', '.join(missing_tokens)}",
                        "path": relative_path,
                    }
                )
                continue
            evidence.append(relative_path)
    _append_mirror_parity_failures(repo_root=repo_root, failures=failures, evidence=evidence)
    summary = platform_contract_summary()
    return {
        "id": CHECK_ID,
        "status": "passed" if not failures else "failed",
        "contract": PLATFORM_CONTRACT,
        "domains": summary["domains"],
        "evidence": _dedupe_strings(evidence),
        "failures": failures,
    }


__all__ = [
    "CHECK_ID",
    "PLATFORM_CONTRACT",
    "PLATFORM_CONTRACTS",
    "platform_contract_summary",
    "validate_platform_contracts",
]
