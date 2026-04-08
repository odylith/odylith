from __future__ import annotations

import contextlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest
from odylith.runtime.evaluation import odylith_benchmark_live_execution as live_execution
from odylith.runtime.reasoning import odylith_reasoning


def test_resolved_live_execution_contract_prefers_env_over_repo_and_ignores_user_defaults(tmp_path: Path) -> None:
    reasoning_path = tmp_path / odylith_reasoning.DEFAULT_REASONING_CONFIG_PATH
    reasoning_path.parent.mkdir(parents=True, exist_ok=True)
    reasoning_path.write_text(
        json.dumps(
            {
                "version": "v1",
                "model": "repo-model",
                "codex_reasoning_effort": "high",
                "codex_bin": "codex",
            }
        ),
        encoding="utf-8",
    )
    home_root = tmp_path / "home"
    codex_home = home_root / ".codex"
    codex_home.mkdir(parents=True, exist_ok=True)
    (codex_home / "config.toml").write_text(
        'model = "home-model"\nmodel_reasoning_effort = "xhigh"\n',
        encoding="utf-8",
    )
    contract = live_execution._resolved_live_execution_contract(  # noqa: SLF001
        repo_root=tmp_path,
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="config-model",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="medium",
        ),
        environ={
            "HOME": str(home_root),
            "ODYLITH_REASONING_MODEL": "env-model",
            "ODYLITH_REASONING_CODEX_REASONING_EFFORT": "low",
        },
    )

    assert contract["runner"] == "live_codex_cli"
    assert contract["model"] == "env-model"
    assert contract["reasoning_effort"] == "low"
    assert contract["codex_bin"]

    contract_without_env = live_execution._resolved_live_execution_contract(  # noqa: SLF001
        repo_root=tmp_path,
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="config-model",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="medium",
        ),
        environ={
            "HOME": str(home_root),
        },
    )

    assert contract_without_env["model"] == "repo-model"
    assert contract_without_env["reasoning_effort"] == "high"

    contract_with_defaults_only = live_execution._resolved_live_execution_contract(  # noqa: SLF001
        repo_root=tmp_path / "empty-repo",
        config=odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="config-model",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="high",
        ),
        environ={
            "HOME": str(home_root),
        },
    )

    assert contract_with_defaults_only["model"] == "config-model"
    assert contract_with_defaults_only["reasoning_effort"] == "medium"


def test_minimal_codex_config_text_disables_guidance_surfaces() -> None:
    config_text = live_execution._minimal_codex_config_text(  # noqa: SLF001
        execution_contract={
            "model": "gpt-5.4",
            "reasoning_effort": "xhigh",
        }
    )

    assert 'model = "gpt-5.4"' in config_text
    assert 'model_reasoning_effort = "xhigh"' in config_text
    assert 'approval_mode = "never"' in config_text
    assert "allow_login_shell = false" in config_text
    assert "plugins = {}" in config_text
    assert "mcp_servers = {}" in config_text
    assert "project_doc_max_bytes = 0" in config_text
    assert 'project_doc_fallback_filename = ""' in config_text
    assert "[features]" in config_text
    assert "multi_agent = false" in config_text


def test_resolved_live_timeout_budget_prefers_env_override_then_scenario_timeout() -> None:
    timeout_seconds, timeout_policy = live_execution._resolved_live_timeout_budget(  # noqa: SLF001
        scenario={
            "live_timeout_seconds": 210.0,
            "needs_write": True,
            "validation_commands": ["pytest -q"],
            "correctness_critical": True,
        },
        environ={"ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS": "150"},
    )

    assert timeout_seconds == 150.0
    assert timeout_policy == "env_override"

    timeout_seconds, timeout_policy = live_execution._resolved_live_timeout_budget(  # noqa: SLF001
        scenario={
            "live_timeout_seconds": 210.0,
            "needs_write": True,
            "validation_commands": ["pytest -q"],
            "correctness_critical": True,
        },
        environ={},
    )

    assert timeout_seconds == 210.0
    assert timeout_policy == "scenario_timeout"


def test_resolved_live_timeout_budget_allows_disabled_env_timeout() -> None:
    timeout_seconds, timeout_policy = live_execution._resolved_live_timeout_budget(  # noqa: SLF001
        scenario={"needs_write": True, "validation_commands": ["pytest -q"], "correctness_critical": True},
        environ={"ODYLITH_BENCHMARK_CODEX_TIMEOUT_SECONDS": "off"},
    )

    assert timeout_seconds is None
    assert timeout_policy == "env_disabled"

    assert live_execution._validator_timeout_seconds(  # noqa: SLF001
        environ={"ODYLITH_BENCHMARK_VALIDATOR_TIMEOUT_SECONDS": "none"}
    ) is None


def test_default_live_timeout_policy_uses_default_guardrail_when_scenario_has_no_budget() -> None:
    timeout_seconds, timeout_policy = live_execution._default_live_timeout_policy(  # noqa: SLF001
        {
            "needs_write": True,
            "validation_commands": ["pytest -q"],
            "correctness_critical": True,
        }
    )

    assert timeout_seconds == live_execution._DEFAULT_LIVE_TIMEOUT_SECONDS  # noqa: SLF001
    assert timeout_policy == "default_live_timeout"
    assert live_execution._validator_timeout_seconds(environ={}) is None  # noqa: SLF001


def test_odylith_focus_lines_prioritize_selected_files_and_docs() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "docs": [
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                        "tests/unit/runtime/test_odylith_benchmark_runner.py",
                    ]
                },
                "selection_state": "x:B-022",
                "route": {"route_ready": True},
            },
        }
    )

    joined = "\n".join(lines)
    assert "Odylith-selected starting files:" in joined
    assert "src/odylith/runtime/evaluation/odylith_benchmark_runner.py" in joined
    assert "Odylith-selected supporting docs/contracts:" in joined
    assert "docs/benchmarks/REVIEWER_GUIDE.md" in joined
    assert "Odylith considers this slice grounded." in joined
    assert "Read only the listed supporting docs/contracts before looking elsewhere." in joined
    assert "Treat references inside opened files as background" in joined
    assert "Do not run broad repo-wide searches, listings, or scans" in joined


def test_odylith_focus_lines_include_component_implementation_anchors() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "implementation_anchors": ["src/odylith/runtime/orchestration/subagent_router.py"],
            "docs": ["odylith/registry/source/components/subagent-router/CURRENT_SPEC.md"],
            "context_packet": {
                "anchors": {
                    "changed_paths": ["odylith/skills/subagent-router/SKILL.md"],
                },
                "selection_state": "x:B-022",
                "route": {"route_ready": True},
            },
        }
    )

    joined = "\n".join(lines)
    assert "src/odylith/runtime/orchestration/subagent_router.py" in joined
    assert "Read the listed implementation files before searching for code anywhere else." in joined


def test_odylith_focus_lines_fall_back_to_relevant_docs_and_selected_docs() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "relevant_docs": ["odylith/registry/source/components/benchmark/CURRENT_SPEC.md"],
            "context_packet": {
                "retrieval_plan": {
                    "selected_counts": "c1d2",
                    "selected_docs": ["docs/benchmarks/REVIEWER_GUIDE.md"],
                }
            },
        }
    )

    joined = "\n".join(lines)
    assert "Odylith-selected supporting docs/contracts:" in joined
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" in joined
    assert "docs/benchmarks/REVIEWER_GUIDE.md" in joined


def test_odylith_focus_lines_treat_curated_docs_as_authoritative() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "docs": ["docs/benchmarks/README.md"],
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": ["odylith/radar/radar.html"],
                }
            },
        }
    )

    joined = "\n".join(lines)
    assert "docs/benchmarks/README.md" in joined
    assert "odylith/radar/radar.html" not in joined


def test_odylith_focus_lines_do_not_render_doc_explicit_paths_as_starting_files() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "implementation_anchors": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "docs": ["docs/benchmarks/README.md"],
            "context_packet": {
                "anchors": {
                    "explicit_paths": [
                        "README.md",
                        "docs/benchmarks/README.md",
                    ]
                },
                "selection_state": "x:B-020",
                "route": {"route_ready": True},
            },
        }
    )

    joined = "\n".join(lines)
    assert "src/odylith/runtime/evaluation/odylith_benchmark_runner.py" in joined
    assert "- README.md" not in joined
    assert "docs/benchmarks/README.md" in joined


def test_odylith_focus_lines_render_architecture_required_reads() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "architecture_audit": {
                "changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"],
                "implementation_anchors": ["src/odylith/runtime/context_engine/odylith_context_engine.py"],
                "required_reads": [
                    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    "docs/benchmarks/REVIEWER_GUIDE.md",
                ],
            }
        }
    )

    joined = "\n".join(lines)
    assert "Odylith-selected starting files:" in joined
    assert "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md" in joined
    assert "src/odylith/runtime/context_engine/odylith_context_engine.py" in joined
    assert "Odylith-selected supporting docs/contracts:" in joined
    assert "odylith/registry/source/components/benchmark/CURRENT_SPEC.md" in joined
    assert "docs/benchmarks/REVIEWER_GUIDE.md" in joined


def test_odylith_focus_lines_render_strict_boundary_guidance() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "strict_boundary": True,
            "context_packet": {
                "anchors": {
                    "changed_paths": ["odylith/skills/subagent-router/SKILL.md"],
                },
                "selection_state": "x:B-022",
                "route": {"route_ready": True},
            },
        }
    )

    joined = "\n".join(lines)
    assert "strict bounded slice" in joined
    assert "do not open adjacent specs or implementation" in joined
    assert "generated artifacts" in joined
    assert "keep this slice local" in joined


def test_odylith_focus_lines_do_not_recommend_widening_for_strict_boundary() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "strict_boundary": True,
            "full_scan_recommended": True,
            "context_packet": {
                "anchors": {"changed_paths": ["README.md"]},
                "route": {"route_ready": False},
            },
        }
    )

    joined = "\n".join(lines)
    assert "did not fully ground this slice" not in joined
    assert "keep this slice local" in joined


def test_odylith_focus_lines_hide_supporting_docs_for_strict_boundary() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "strict_boundary": True,
            "docs": ["odylith/runtime/README.md"],
            "context_packet": {
                "anchors": {"changed_paths": ["odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md"]},
                "retrieval_plan": {"selected_docs": ["odylith/runtime/TRIBUNAL_AND_REMEDIATION.md"]},
            },
        }
    )

    joined = "\n".join(lines)
    assert "Odylith-selected supporting docs/contracts:" not in joined
    assert "odylith/runtime/README.md" not in joined
    assert "TRIBUNAL_AND_REMEDIATION" not in joined


def test_odylith_focus_lines_surface_boundary_hints_before_generic_guidance() -> None:
    lines = live_execution._odylith_focus_lines(  # noqa: SLF001
        {
            "docs": ["docs/benchmarks/README.md"],
            "implementation_anchors": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "boundary_hints": [
                "For benchmark publication slices, keep reads and edits on the listed benchmark contracts plus the runner/graphs anchors."
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                        "README.md",
                    ]
                },
                "selection_state": "x:B-020",
                "route": {"route_ready": True},
            },
        }
    )

    joined = "\n".join(lines)
    assert "For benchmark publication slices, keep reads and edits on the listed benchmark contracts plus the runner/graphs anchors." in joined


def test_agent_prompt_marks_selected_docs_as_approved_read_only_grounding() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "prompt": "Fix the benchmark runner.",
            "needs_write": True,
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "docs/benchmarks/REVIEWER_GUIDE.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"]
                }
            },
        },
        validation_commands=[],
    )

    assert "read-only references and the only approved read-only expansion beyond the anchors" in prompt
    assert "Read those listed docs/contracts before editing when they are present." in prompt
    assert "approved first-pass read list" in prompt
    assert "This is a write-backed slice. Do not conclude with a no-file-change completion unless the task explicitly allows it." in prompt
    assert "Do not rewrite policy, guidance, or wording just to restate a contract the grounded anchors already establish." in prompt
    assert "Before editing, prefer the smallest targeted local check" not in prompt
    assert "Do not follow links or references from opened docs or skills" in prompt
    assert "widen by one adjacent file at a time" in prompt
    assert "The benchmark harness will run these validation commands after your response." not in prompt


def test_agent_prompt_uses_known_starting_anchors_when_compact_payload_has_no_changed_paths() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "prompt": "Keep the explicit workstream slice bounded.",
            "needs_write": True,
            "changed_paths": ["odylith/skills/subagent-orchestrator/SKILL.md"],
            "acceptance_criteria": ["Keep the slice bounded to odylith/skills/subagent-orchestrator/SKILL.md."],
        },
        mode="odylith_on",
        prompt_payload={
            "context_packet": {
                "selection_state": "x:B-001",
                "route": {"route_ready": True},
            }
        },
        validation_commands=["odylith subagent-orchestrator --repo-root . --help"],
    )

    assert "Odylith-selected starting files:" in prompt
    assert "odylith/skills/subagent-orchestrator/SKILL.md" in prompt
    assert "hard working boundary" in prompt


def test_agent_prompt_uses_component_governance_noop_boundary_when_allowed() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "component_governance",
            "prompt": "Tighten the benchmark component and its proof lane so Registry, Atlas, and validation proof stay aligned.",
            "needs_write": True,
            "allow_noop_completion": True,
            "changed_paths": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/odylith-benchmark-proof-and-publication-lane.mmd",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "odylith/registry/source/component_registry.v1.json",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "odylith/atlas/source/catalog/diagrams.v1.json",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    ]
                }
            },
        },
        validation_commands=[
            "odylith validate component-registry --repo-root .",
            "odylith atlas render --repo-root . --check-only",
        ],
    )

    assert "If the listed component-governance validators already pass" in prompt
    assert "stop with no file changes" in prompt
    assert "Do not edit `src/odylith/cli.py`" in prompt
    assert "treat that as a bounded blocker to report" in prompt


def test_agent_prompt_uses_compass_noop_boundary_when_allowed() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "compass_brief_freshness",
            "prompt": "Improve Compass brief speed without making 24h or 48h narration stale across Atlas, Registry, Casebook, or audit-timeline updates.",
            "needs_write": True,
            "allow_noop_completion": True,
            "changed_paths": [
                "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
                "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "odylith/registry/source/components/compass/CURRENT_SPEC.md",
                "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "src/odylith/runtime/surfaces/compass_dashboard_runtime.py",
                    ]
                }
            },
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_compass_dashboard_runtime.py tests/unit/runtime/test_compass_standup_brief_narrator.py tests/unit/runtime/test_render_compass_dashboard.py",
        ],
    )

    assert "If the listed Compass freshness validators already pass" in prompt
    assert "stop with no file changes" in prompt


def test_agent_prompt_uses_consumer_profile_noop_boundary_when_allowed() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "consumer_profile_compatibility",
            "prompt": "Preserve explicit consumer truth roots and compatibility behavior instead of silently rebinding the repo to product defaults.",
            "needs_write": True,
            "allow_noop_completion": True,
            "changed_paths": [
                "src/odylith/runtime/common/consumer_profile.py",
                "tests/unit/runtime/test_consumer_profile.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "odylith/AGENTS.md",
                "odylith/registry/source/components/odylith/CURRENT_SPEC.md",
                "odylith/registry/source/components/registry/CURRENT_SPEC.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "src/odylith/runtime/common/consumer_profile.py",
                    ]
                }
            },
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_consumer_profile.py",
        ],
    )

    assert "If the listed consumer-profile validator already passes" in prompt
    assert "stop with no file changes" in prompt


def test_agent_prompt_uses_governed_surface_sync_noop_boundary_when_allowed() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "governed_surface_sync",
            "prompt": "Keep plan closeout path truth synchronized across delivery intelligence, Odylith surface reads, Compass, and Odylith.",
            "needs_write": True,
            "allow_noop_completion": True,
            "changed_paths": [
                "odylith/surfaces/GOVERNANCE_SURFACES.md",
                "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
                "odylith/radar/source/INDEX.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "odylith/surfaces/GOVERNANCE_SURFACES.md",
                "odylith/runtime/CONTEXT_ENGINE_OPERATIONS.md",
                "odylith/radar/source/INDEX.md",
            ],
            "context_packet": {
                "anchors": {
                    "changed_paths": [
                        "odylith/surfaces/GOVERNANCE_SURFACES.md",
                    ]
                }
            },
            "focused_local_check_results": [
                "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills: passed",
            ],
        },
        validation_commands=[
            "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
            "odylith context-engine --repo-root . status",
        ],
    )

    assert "If the listed sync validators already pass" in prompt
    assert "stop with no file changes" in prompt
    assert "These focused sync results already cover broader validator companions" in prompt
    assert "Do not use pre-existing dirty validator-companion files as a cue to widen" in prompt


def test_agent_prompt_keeps_changed_paths_visible_even_with_implementation_anchors() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "prompt": "Refresh the public benchmark proof without drifting from maintainer release rules.",
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "README.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "implementation_anchors": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "docs": ["docs/benchmarks/README.md"],
            "context_packet": {
                "selection_state": "x:B-020",
                "route": {"route_ready": True},
            },
        },
        validation_commands=[],
    )

    assert "Odylith grounding focus:" in prompt
    assert "README.md" in prompt
    assert "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md" in prompt


def test_agent_prompt_deemphasizes_release_publication_contract_anchors_and_hides_heavy_validators() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "prompt": "Refresh the public benchmark proof and publication surfaces only where needed.",
            "family": "release_publication",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "README.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            ],
            "validation_commands": [
                "odylith benchmark --repo-root .",
                "PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks",
                "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "implementation_anchors": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "docs": ["docs/benchmarks/README.md"],
            "context_packet": {
                "selection_state": "x:B-020",
                "route": {"route_ready": True},
            },
        },
        validation_commands=None,
    )

    assert "Scenario contract anchors (reference only):" in prompt
    assert "These anchors define the benchmark contract." in prompt
    assert "odylith benchmark --repo-root ." not in prompt
    assert "PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs" not in prompt
    assert "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py" in prompt
    assert "The harness will also run broader publication validators after your response" in prompt


def test_agent_prompt_treats_harness_validator_as_authoritative() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "prompt": "Fix the benchmark runner.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        },
        mode="odylith_on",
        prompt_payload={},
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"
        ],
    )

    assert "The benchmark harness will run these validation commands after your response." in prompt
    assert "do not rerun the full listed validator unless it is necessary to diagnose a failure." in prompt
    assert "If a listed validator is already narrow, prefer running that exact validator" in prompt
    assert "your final step must still be a single schema-valid JSON message" in prompt
    assert "Do not treat every file named inside those validators as a required first-pass read" in prompt
    assert "a validator-backed no-op is valid when the current tree already satisfies it" in prompt
    assert "A validator-backed no-op is fully acceptable for this task" in prompt
    assert "Before editing, prefer the smallest targeted local check" in prompt
    assert "stop with no file changes" in prompt
    assert "Keep the evidence cone tight and avoid broad repo scans" in prompt
    assert 'Emit exactly one JSON object with keys: "status", "summary", "changed_files"' in prompt


def test_agent_prompt_keeps_architecture_reviews_as_bounded_dossiers() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "architecture",
            "prompt": "Audit the Odylith benchmark honest-baseline contract.",
            "needs_write": False,
            "changed_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
            ],
            "required_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                "README.md",
                "docs/benchmarks/README.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "architecture_audit": {
                "changed_paths": [
                    "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                    "odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                ],
                "required_reads": [
                    "README.md",
                    "docs/benchmarks/README.md",
                    "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
                ],
            }
        },
        validation_commands=[],
    )

    assert "complete dossier unless an exact required path or concrete contradiction forces one adjacent read" in prompt
    assert "stop and emit the schema-valid JSON response instead of reopening the same files for extra corroboration" in prompt
    assert "Do not inspect release runbooks, Atlas or other component specs, benchmark skills, or broader benchmark helper sources" in prompt


def test_agent_prompt_surfaces_contract_code_paths_and_activation_no_op_guardrail() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "agent_activation",
            "prompt": "Repair install-time Odylith agent activation.",
            "needs_write": True,
            "changed_paths": [
                "src/odylith/install/agents.py",
                "src/odylith/install/manager.py",
                "tests/unit/install/test_agents.py",
            ],
            "required_paths": [
                "src/odylith/install/agents.py",
                "src/odylith/install/manager.py",
                "tests/unit/install/test_agents.py",
                "tests/integration/install/test_manager.py",
                "odylith/AGENTS.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": ["odylith/AGENTS.md"],
            "context_packet": {
                "selection_state": "x:B-016",
                "route": {"route_ready": True},
            },
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py"
        ],
    )

    assert "Grounded contract files:" in prompt
    assert "tests/integration/install/test_manager.py" in prompt
    assert "On agent-activation slices, if the focused install validators already pass on the grounded tree, stop with no file changes instead of rewriting install or AGENTS guidance wording." in prompt
    assert "If one of the listed focused install checks passes cleanly, do not widen into adjacent CLI, shell, dashboard, or routing surfaces unless the failure output points there directly." not in prompt


def test_agent_prompt_warns_install_slices_about_stripped_guidance_false_positives() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "install_upgrade_runtime",
            "prompt": "Repair install or upgrade behavior if needed.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/install/manager.py",
                "src/odylith/install/runtime.py",
            ],
            "focused_local_checks": [
                "Runtime subset: `tests/unit/install/test_runtime.py::test_legacy_consumer_launcher_bootstraps_plain_upgrade_via_installer`.",
            ],
        },
        mode="odylith_on",
        prompt_payload={"context_packet": {"selection_state": "x:B-005", "route": {"route_ready": True}}},
        validation_commands=[
            "odylith install --help",
            "PYTHONPATH=src .venv/bin/pytest -q tests/integration/install/test_manager.py tests/unit/install/test_runtime.py tests/unit/test_cli.py",
        ],
    )

    assert "Suggested first-pass local checks:" in prompt
    assert "Runtime subset:" in prompt
    assert "On this allow-no-op install slice, treat the listed focused checks as the approved first-pass proof path before opening broader runtime or guidance surfaces." in prompt
    assert "If one of the listed focused install checks passes cleanly, do not widen into adjacent CLI, shell, dashboard, or routing surfaces unless the failure output points there directly." in prompt
    assert "Do not run the full listed validator during first-pass diagnosis just to prove current truth on an allow-no-op task" in prompt
    assert "Do not treat missing repo `AGENTS.md` files or benchmark-managed pytest temp/cache paths during your own checks as product regressions on install slices" in prompt


def test_agent_prompt_uses_daemon_focused_checks_as_noop_boundary() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "daemon_security",
            "prompt": "Harden the daemon transport and repair path only if needed.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/context_engine/odylith_context_engine.py",
                "src/odylith/install/repair.py",
                "tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py",
            ],
            "focused_local_checks": [
                "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={"context_packet": {"selection_state": "x:B-014", "route": {"route_ready": True}}},
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_context_engine_daemon_hardening.py tests/unit/install/test_repair.py"
        ],
    )

    assert "On this allow-no-op daemon slice, treat the listed focused checks as the approved first-pass proof path before changing transport, auth-token, or shutdown code." in prompt
    assert "If the focused daemon validator passes cleanly, do not rewrite auth-token persistence, socket transport, or stop-path logic unless a grounded contradiction remains." in prompt
    assert "On daemon-security slices, if the focused daemon validator already passes on the grounded tree, stop with no file changes instead of rewriting auth-token persistence, socket transport, or daemon shutdown flow." in prompt
    assert "A validator-backed no-op is fully acceptable for this task" in prompt


def test_agent_prompt_uses_activation_focused_checks_as_first_pass_boundary() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "agent_activation",
            "prompt": "Repair install-time Odylith agent activation.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/install/agents.py",
                "src/odylith/install/manager.py",
                "tests/unit/install/test_agents.py",
            ],
            "focused_local_checks": [
                "Unit AGENTS block subset: `tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills`.",
            ],
        },
        mode="odylith_on",
        prompt_payload={"context_packet": {"selection_state": "x:B-016", "route": {"route_ready": True}}},
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py"
        ],
    )

    assert "On this allow-no-op install slice, treat the listed focused checks as the approved first-pass proof path before opening broader runtime or guidance surfaces." in prompt
    assert "If one of the listed focused install checks passes cleanly, do not widen into adjacent CLI, shell, dashboard, or routing surfaces unless the failure output points there directly." in prompt


def test_agent_prompt_surfaces_focused_check_results_as_current_workspace_evidence() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "agent_activation",
            "prompt": "Repair install-time Odylith agent activation.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/install/agents.py",
                "src/odylith/install/manager.py",
                "tests/unit/install/test_agents.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": ["odylith/AGENTS.md"],
            "focused_local_check_results": [
                "passed: tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills",
            ]
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/install/test_agents.py tests/integration/install/test_manager.py"
        ],
    )

    assert "Current workspace focused-check results:" in prompt
    assert "passed: tests/unit/install/test_agents.py::test_managed_block_defaults_consumers_to_odylith_guidance_and_skills" in prompt
    assert "Treat these focused-check results as current workspace evidence." in prompt
    assert "The listed supporting docs/contracts are already represented in the focused-check evidence; do not reopen them unless a grounded contradiction or validator failure points there directly." in prompt


def test_agent_prompt_write_backed_non_noop_slice_blocks_no_file_change_completion() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "validation_heavy_fix",
            "prompt": "Rework the benchmark runner gate without widening into docs edits.",
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "tests/unit/runtime/test_odylith_benchmark_runner.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": [
                "docs/benchmarks/REVIEWER_GUIDE.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            ],
            "boundary_hints": [
                "For validation-heavy benchmark fixes, keep writable changes on the listed runtime and test anchors. Treat reviewer docs, Registry specs, and maintainer benchmark guidance as read-only references; do not edit README or benchmark docs unless they are explicit changed or required paths."
            ],
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py"
        ],
    )

    assert "This is a write-backed slice. Do not conclude with a no-file-change completion unless the task explicitly allows it." in prompt
    assert "If that focused check fails, keep the fix on the listed writable anchors and rerun the narrow validator before widening." in prompt
    assert "prefer a validator-backed no-op over speculative rewrites" not in prompt
    assert "stop with no file changes" not in prompt


def test_agent_prompt_validation_heavy_fix_uses_focused_check_noop_boundary() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "validation_heavy_fix",
            "prompt": "Keep the benchmark runner gate honest without rewriting passing expectations.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
                "tests/unit/runtime/test_odylith_benchmark_runner.py",
            ],
            "focused_local_checks": [
                "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py::test_run_benchmarks_publishes_conservative_multi_profile_view",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "boundary_hints": [
                "For validation-heavy benchmark fixes, keep writable changes on the listed runtime and test anchors. Treat reviewer docs, Registry specs, and maintainer benchmark guidance as read-only references; do not edit README or benchmark docs unless they are explicit changed or required paths."
            ],
            "focused_local_check_results": [
                "passed: tests/unit/runtime/test_odylith_benchmark_runner.py::test_run_benchmarks_publishes_conservative_multi_profile_view",
            ],
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py tests/unit/runtime/test_odylith_benchmark_graphs.py"
        ],
    )

    assert "If that focused check passes and the grounded anchors already match the task contract, stop with no file changes." in prompt
    assert "If the focused benchmark check passes, treat that as current workspace truth and do not rewrite benchmark expectation literals" in prompt
    assert "On validation-heavy benchmark gate slices, if the focused runner validator already passes on the grounded tree, stop with no file changes" in prompt
    assert "A validator-backed no-op is fully acceptable for this task" in prompt


def test_agent_prompt_browser_slice_treats_html_as_rendered_read_only_evidence() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "browser_surface_reliability",
            "prompt": "Repair the browser contract without drifting into rendered HTML edits.",
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/surfaces/render_tooling_dashboard.py",
                "src/odylith/runtime/surfaces/shell_onboarding.py",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
            ],
        },
        mode="odylith_on",
        prompt_payload={
            "docs": ["odylith/index.html"],
            "boundary_hints": [
                "For shell/browser regressions, keep writable changes on the listed source renderers, onboarding or CLI sources, and browser tests. Treat odylith/*.html shell pages as rendered read surfaces or validator outputs, not primary edit targets, unless a listed changed path or validator failure points there directly."
            ],
        },
        validation_commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py"
        ],
    )

    assert "rendered read surfaces or validator outputs, not primary edit targets" in prompt
    assert "restore that path or remove test-only stubs first" in prompt
    assert "Do not inspect benchmark runner, prompt, or evaluation sources on browser slices" in prompt
    assert "many unrelated repo files outside the grounded slice" in prompt
    assert "extra spotlight, reopen-pill, or onboarding-state checks" in prompt
    assert "preserve that helper and update it in place" in prompt
    assert "do not unmock or introduce live `sync_workstream_artifacts.main` calls" in prompt
    assert "Treat install-state persistence and upgrade spotlight storage under `src/odylith/install/` as out of scope" in prompt
    assert "Do not invent ad hoc Python or shell probes that import `odylith.install.state`" in prompt
    assert "Ignore unrelated benchmark runner, prompt, reasoning, and benchmark-doc files" in prompt


def test_agent_prompt_merge_heavy_slice_allows_successful_bounded_noop_closeout() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "merge_heavy_change",
            "prompt": "Handle a merge-heavy router plus governed-doc slice without underestimating coordination or validation pressure.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "odylith/skills/subagent-router/SKILL.md",
                "odylith/runtime/SUBAGENT_OPERATIONS.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={},
        validation_commands=[
            "odylith subagent-router --repo-root . --help",
            "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
        ],
    )

    assert "finish successfully with no file changes" in prompt
    assert "not as a blocker for this bounded no-op closeout" in prompt


def test_agent_prompt_release_publication_forbids_absolute_workspace_paths() -> None:
    prompt = live_execution._agent_prompt(  # noqa: SLF001
        scenario={
            "family": "release_publication",
            "prompt": "Refresh the benchmark publication surfaces only where needed.",
            "allow_noop_completion": True,
            "needs_write": True,
            "changed_paths": [
                "README.md",
                "docs/benchmarks/README.md",
                "odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md",
            ],
        },
        mode="odylith_on",
        prompt_payload={},
        validation_commands=[
            "odylith benchmark --repo-root .",
            "PYTHONPATH=src .venv/bin/python -m odylith.runtime.evaluation.odylith_benchmark_graphs --report .odylith/runtime/odylith-benchmarks/latest.v1.json --out-dir docs/benchmarks",
        ],
    )

    assert "never use `/tmp` or other absolute workspace paths" in prompt


def test_write_expectation_satisfied_accepts_validator_backed_noop_completion() -> None:
    assert live_execution._write_expectation_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["src/odylith/install/manager.py"],
            "allow_noop_completion": True,
        },
        candidate_write_paths=[],
        validators_passed=True,
    )
    assert not live_execution._write_expectation_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["src/odylith/install/manager.py"],
            "allow_noop_completion": True,
        },
        candidate_write_paths=[],
        validators_passed=False,
    )


def test_successful_noop_precision_metrics_zeroes_expected_writes_for_valid_noop() -> None:
    metrics = live_execution._successful_noop_precision_metrics(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["src/odylith/install/manager.py"],
            "allow_noop_completion": True,
        },
        precision_metrics={
            "expected_write_path_count": 1,
            "candidate_write_path_count": 0,
            "candidate_write_paths": [],
            "write_surface_precision": 0.0,
            "unnecessary_widening_count": 0,
            "unnecessary_widening_rate": 0.0,
            "unnecessary_widening_paths": [],
        },
        candidate_write_paths=[],
        validators_passed=True,
    )

    assert metrics["expected_write_path_count"] == 0
    assert metrics["candidate_write_path_count"] == 0
    assert metrics["candidate_write_paths"] == []
    assert metrics["write_surface_precision"] == 1.0


def test_validator_backed_noop_completion_accepts_benign_blocked_closeout() -> None:
    assert live_execution._validator_backed_completion_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["odylith/runtime/SUBAGENT_OPERATIONS.md"],
            "allow_noop_completion": True,
        },
        structured_output={
            "status": "blocked",
            "summary": "No file changes were made. The bounded router/doc slice already appears consistent.",
            "validation_summary": "out-of-scope stale registry specs elsewhere in the repo",
            "notes": [],
        },
        status="blocked",
        candidate_write_paths=[],
        validators_passed=True,
        required_path_misses=[],
    )


def test_validator_backed_noop_completion_rejects_non_benign_blocked_status() -> None:
    assert not live_execution._validator_backed_completion_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["odylith/runtime/SUBAGENT_OPERATIONS.md"],
            "allow_noop_completion": True,
        },
        structured_output={
            "status": "blocked",
            "summary": "Need a real code fix before this slice is ready.",
            "validation_summary": "focused validator still fails",
            "notes": [],
        },
        status="blocked",
        candidate_write_paths=[],
        validators_passed=True,
        required_path_misses=[],
    )


def test_validator_backed_completion_accepts_benign_blocked_write_with_passed_validator() -> None:
    assert live_execution._validator_backed_completion_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": ["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
            "allow_noop_completion": True,
        },
        structured_output={
            "status": "blocked",
            "summary": "Tightened the release-publication runner support-doc ordering for the bounded publication slice.",
            "validation_summary": "The focused validator passed, but sandbox PermissionError cleanup failures remained under the benchmark harness temp root outside the edited slice.",
            "notes": [
                "The local worktree already had unrelated modifications outside the edited slice; they were left untouched.",
            ],
        },
        status="blocked",
        candidate_write_paths=["src/odylith/runtime/evaluation/odylith_benchmark_runner.py"],
        validators_passed=True,
        required_path_misses=[],
    )


def test_validator_backed_completion_accepts_import_error_outside_allowed_slice() -> None:
    assert live_execution._validator_backed_completion_satisfied(  # noqa: SLF001
        scenario={
            "needs_write": True,
            "changed_paths": [
                "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
                "tests/unit/runtime/test_compass_dashboard_runtime.py",
            ],
            "allow_noop_completion": True,
        },
        structured_output={
            "status": "blocked",
            "summary": "Reduced Compass brief cache churn while preserving invalidation when cross-surface evidence changes.",
            "validation_summary": "The listed validator did not complete because an ImportError in the workspace is outside the allowed slice.",
            "notes": [
                "Validation is blocked by a pre-existing workspace import error; the missing module is absent in the workspace outside the allowed slice.",
            ],
        },
        status="blocked",
        candidate_write_paths=[
            "src/odylith/runtime/surfaces/compass_standup_brief_narrator.py",
            "tests/unit/runtime/test_compass_dashboard_runtime.py",
        ],
        validators_passed=True,
        required_path_misses=[],
    )


def test_focused_noop_validator_proxy_accepts_out_of_slice_workspace_drift() -> None:
    assert live_execution._focused_noop_validator_proxy_allowed(  # noqa: SLF001
        scenario={
            "family": "governed_surface_sync",
            "allow_noop_completion": True,
            "focused_local_checks": [
                "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
                "odylith context-engine --repo-root . status",
            ],
            "validation_commands": [
                "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
                "odylith context-engine --repo-root . status",
            ],
        },
        structured_output={
            "status": "blocked",
            "summary": "No file changes were made. Validator-backed completion is blocked by out-of-slice workspace drift: missing finished-plan targets referenced from Radar idea docs and stale Registry generated artifacts.",
            "validation_summary": "The grounded anchors already satisfy the closeout path truth, but no minimal in-slice edit can make the listed validators pass.",
            "notes": [
                "The blocking contradiction is outside the permitted writable slice.",
            ],
        },
        candidate_write_paths=[],
        required_path_misses=[],
        focused_check_result={"status": "passed"},
        validator_result={"status": "failed"},
    )


def test_focused_noop_validator_proxy_rejects_when_focused_checks_do_not_cover_validator() -> None:
    assert not live_execution._focused_noop_validator_proxy_allowed(  # noqa: SLF001
        scenario={
            "family": "consumer_profile_compatibility",
            "allow_noop_completion": True,
            "focused_local_checks": [
                "odylith context-engine --repo-root . status",
            ],
            "validation_commands": [
                "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
                "odylith context-engine --repo-root . status",
            ],
        },
        structured_output={
            "status": "blocked",
            "summary": "No file changes were made. Validator-backed completion is blocked by out-of-slice workspace drift.",
            "validation_summary": "The grounded anchors already satisfy the closeout path truth, but no minimal in-slice edit can make the listed validators pass.",
            "notes": [
                "The blocking contradiction is outside the permitted writable slice.",
            ],
        },
        candidate_write_paths=[],
        required_path_misses=[],
        focused_check_result={"status": "passed"},
        validator_result={"status": "failed"},
    )


def test_focused_noop_validator_proxy_accepts_completed_noop_with_out_of_slice_validator_drift() -> None:
    assert live_execution._focused_noop_validator_proxy_allowed(  # noqa: SLF001
        scenario={
            "family": "governed_surface_sync",
            "allow_noop_completion": True,
            "focused_local_checks": [
                "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_sync_cli_compat.py::test_governed_surface_closeout_path_truth_stays_normalized_across_runtime_readers",
            ],
            "validation_commands": [
                "odylith sync --repo-root . --check-only --registry-policy-mode enforce-critical --enforce-deep-skills",
                "odylith context-engine --repo-root . status",
            ],
        },
        structured_output={
            "status": "completed",
            "summary": "No-op completion. The grounded governance surfaces and runtime reader already keep plan closeout path truth aligned on `odylith/technical-plans/done` across Radar, Compass-facing runtime reads, and Odylith surface references.",
            "validation_summary": "The broad sync validator still fails after the focused closeout-path proof.",
            "notes": [
                "No file changes were needed for this governed-surface sync slice.",
            ],
        },
        candidate_write_paths=[],
        required_path_misses=[],
        focused_check_result={"status": "passed"},
        validator_result={
            "status": "failed",
            "results": [
                {
                    "stdout_tail": "Check Registry component spec requirements without rewriting governed truth. ?? odylith/registry/source/components/benchmark/CURRENT_SPEC.md",
                    "stderr_tail": "",
                }
            ],
        },
    )


def test_estimated_initial_prompt_tokens_uses_utf8_byte_budget() -> None:
    assert live_execution._estimated_initial_prompt_tokens("") == 0  # noqa: SLF001
    assert live_execution._estimated_initial_prompt_tokens("abcd") == 1  # noqa: SLF001
    assert live_execution._estimated_initial_prompt_tokens("abcdefgh") == 2  # noqa: SLF001


def test_sandbox_validation_commands_rewrite_repo_venv_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".venv" / "bin").mkdir(parents=True, exist_ok=True)

    commands = live_execution._sandbox_validation_commands(  # noqa: SLF001
        repo_root=repo_root,
        commands=[
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py",
            "./.venv/bin/python -m pytest -q",
        ],
    )

    venv_bin = str((repo_root / ".venv" / "bin").resolve())
    assert commands[0].startswith(f"PYTHONPATH=src {venv_bin}/pytest")
    assert commands[1].startswith(f"{venv_bin}/python -m pytest")


def test_sandbox_validation_commands_rewrite_odylith_cli_to_source_local_runtime(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / ".venv" / "bin").mkdir(parents=True, exist_ok=True)

    commands = live_execution._sandbox_validation_commands(  # noqa: SLF001
        repo_root=repo_root,
        commands=[
            "odylith validate component-registry --repo-root .",
            "PYTHONPATH=src odylith atlas render --repo-root . --check-only",
        ],
    )

    venv_bin = str((repo_root / ".venv" / "bin").resolve())
    assert commands[0] == f"PYTHONPATH=src {venv_bin}/python src/odylith/cli.py validate component-registry --repo-root ."
    assert commands[1] == f"PYTHONPATH=src {venv_bin}/python src/odylith/cli.py atlas render --repo-root . --check-only"


def test_sandbox_process_env_uses_local_cache_and_temp_roots(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("PYENV_ROOT", "/tmp/pyenv")
    monkeypatch.setenv("GH_CONFIG_DIR", "/tmp/gh")
    monkeypatch.setenv("CODEX_THREAD_ID", "thread-123")
    codex_home_root = tmp_path / "codex-home"
    repo_root = tmp_path / "repo"
    sandbox_root = tmp_path / "sandbox"
    codex_home_root.mkdir(parents=True, exist_ok=True)
    (repo_root / ".venv" / "bin").mkdir(parents=True, exist_ok=True)

    env = live_execution._sandbox_process_env(  # noqa: SLF001
        repo_root=repo_root,
        execution_contract={"codex_bin": "codex"},
        codex_home_root=codex_home_root,
        sandbox_root=sandbox_root,
    )

    assert env["HOME"] == str(codex_home_root)
    assert env["PATH"].split(":")[0] == str((repo_root / ".venv" / "bin").resolve())
    assert env["XDG_CACHE_HOME"].startswith(str(sandbox_root))
    assert env["XDG_CONFIG_HOME"].startswith(str(sandbox_root))
    assert env["XDG_DATA_HOME"].startswith(str(sandbox_root))
    assert env["XDG_STATE_HOME"].startswith(str(sandbox_root))
    assert env["CODEX_SQLITE_HOME"].startswith(str(sandbox_root))
    assert env["PYTHONNOUSERSITE"] == "1"
    assert env["PYTHONPYCACHEPREFIX"].startswith(str(sandbox_root))
    assert env["TMPDIR"].startswith(str(sandbox_root))
    assert "--basetemp=" in env["PYTEST_ADDOPTS"]
    assert "cache_dir=" in env["PYTEST_ADDOPTS"]
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["BASH_ENV"].startswith(str(sandbox_root))
    assert env["CODEX_THREAD_ID"] == "thread-123"
    assert "PYENV_ROOT" not in env
    assert "GH_CONFIG_DIR" not in env


def test_codex_exec_command_disables_plugins_multi_agent_and_personality(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(live_execution.shutil, "which", lambda binary: f"/usr/bin/{binary}")

    command = live_execution._codex_exec_command(  # noqa: SLF001
        execution_contract={"codex_bin": "codex", "model": "gpt-5.4", "reasoning_effort": "high"},
        workspace_root=tmp_path,
        schema_path=tmp_path / "schema.json",
        output_path=tmp_path / "out.json",
    )

    assert command[0].endswith("codex")
    assert command[1] == "exec"
    assert ["--disable", "plugins"] == command[2:4]
    assert "--disable" in command and "multi_agent" in command and "personality" in command


def test_run_validators_uses_non_login_bash(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, object] = {}

    def _fake_run_subprocess_capture(*, command, cwd, env=None, input_text=None, timeout_seconds=None):  # type: ignore[no-untyped-def]
        seen["args"] = list(command)
        seen["cwd"] = cwd
        seen["env"] = dict(env or {})
        seen["input_text"] = input_text
        seen["timeout_seconds"] = timeout_seconds
        return subprocess.CompletedProcess(args=list(command), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(live_execution, "_run_subprocess_capture", _fake_run_subprocess_capture)

    live_execution._run_validators(  # noqa: SLF001
        workspace_root=tmp_path,
        commands=["echo ok"],
        environ={"PATH": "/usr/bin:/bin"},
    )

    assert seen["args"] == ["/bin/bash", "-c", "echo ok"]
    assert seen["cwd"] == tmp_path
    assert seen["input_text"] is None


def test_run_validators_treats_recursive_benchmark_skip_as_neutral(monkeypatch, tmp_path: Path) -> None:
    def _fake_run_subprocess_capture(*, command, cwd, env=None, input_text=None, timeout_seconds=None):  # type: ignore[no-untyped-def]
        del cwd, env, input_text, timeout_seconds
        if "pytest -q" in " ".join(command):
            return subprocess.CompletedProcess(args=list(command), returncode=0, stdout="", stderr="")
        raise AssertionError(f"unexpected command: {command}")

    monkeypatch.setattr(live_execution, "_run_subprocess_capture", _fake_run_subprocess_capture)

    result = live_execution._run_validators(  # noqa: SLF001
        workspace_root=tmp_path,
        commands=[
            "odylith benchmark --repo-root .",
            "PYTHONPATH=src .venv/bin/pytest -q tests/unit/runtime/test_odylith_benchmark_runner.py",
        ],
        environ={"PATH": "/usr/bin:/bin"},
    )

    assert result["status"] == "passed"
    assert result["passed_count"] == 1
    assert result["skipped_count"] == 1


def test_run_validators_reports_missing_workspace_as_failed_result(tmp_path: Path) -> None:
    result = live_execution._run_validators(  # noqa: SLF001
        workspace_root=tmp_path / "missing-workspace",
        commands=["echo ok"],
        environ={"PATH": "/usr/bin:/bin"},
    )

    assert result["status"] == "failed"
    assert result["failed_count"] == 1
    assert result["results"] == [
        {
            "command": "echo ok",
            "status": "failed",
            "reason": "workspace_root_missing",
            "exit_code": None,
            "duration_ms": 0.0,
            "stdout_tail": "",
            "stderr_tail": f"Benchmark workspace is missing: {(tmp_path / 'missing-workspace').resolve()}",
        }
    ]


def test_run_subprocess_capture_kills_orphaned_process_group_on_timeout(tmp_path: Path) -> None:
    marker = "odylith-benchmark-timeout-child-marker"
    command = [
        sys.executable,
        "-c",
        (
            "import subprocess, sys, time; "
            f"subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)', {marker!r}]); "
            "time.sleep(30)"
        ),
    ]

    with pytest.raises(subprocess.TimeoutExpired):
        live_execution._run_subprocess_capture(  # noqa: SLF001
            command=command,
            cwd=tmp_path,
            timeout_seconds=0.2,
        )

    deadline = time.time() + 3.0
    while time.time() < deadline:
        completed = subprocess.run(
            ["ps", "-axo", "command="],
            text=True,
            capture_output=True,
            check=False,
        )
        if marker not in str(completed.stdout or ""):
            break
        time.sleep(0.1)
    else:
        pytest.fail("timed-out benchmark child marker remained alive after process-group cleanup")


def test_provision_workspace_odylith_root_copies_minimal_state(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    (repo_root / ".odylith" / "bin").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "runtime" / "odylith-benchmarks").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "cache" / "releases").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "subagent_orchestrator" / "decision-ledgers").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "compass").mkdir(parents=True, exist_ok=True)
    (repo_root / ".odylith" / "bin" / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo_root / ".odylith" / "install.json").write_text("{}", encoding="utf-8")
    (repo_root / ".odylith" / "reasoning.config.v1.json").write_text("{}", encoding="utf-8")
    (repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest.v1.json").write_text("{}", encoding="utf-8")
    (repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-proof.v1.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (repo_root / ".odylith" / "runtime" / "odylith-benchmarks" / "latest-diagnostic.v1.json").write_text(
        "{}",
        encoding="utf-8",
    )

    live_execution._provision_workspace_odylith_root(  # noqa: SLF001
        repo_root=repo_root,
        workspace_root=workspace_root,
    )

    target_root = workspace_root / ".odylith"
    assert target_root.is_dir()
    assert (target_root / "bin" / "odylith").is_file()
    assert not (target_root / "bin").is_symlink()
    assert (target_root / "install.json").is_file()
    assert (target_root / "reasoning.config.v1.json").is_file()
    assert (target_root / "runtime" / "odylith-benchmarks").is_dir()
    assert (target_root / "runtime" / "odylith-benchmarks" / "latest.v1.json").is_file()
    assert (target_root / "runtime" / "odylith-benchmarks" / "latest-proof.v1.json").is_file()
    assert (target_root / "runtime" / "odylith-benchmarks" / "latest-diagnostic.v1.json").is_file()
    assert (target_root / "cache" / "releases").is_dir()
    assert (target_root / "subagent_orchestrator" / "decision-ledgers").is_dir()


def test_workspace_strip_paths_keeps_truth_bearing_repo_docs(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    (repo_root / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
    (repo_root / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    (repo_root / ".cursor").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "casebook" / "bugs").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "casebook" / "bugs" / "AGENTS.md").write_text("nested instructions\n", encoding="utf-8")
    truth_doc = repo_root / "odylith" / "maintainer" / "agents-guidelines" / "RELEASE_BENCHMARKS.md"
    truth_doc.parent.mkdir(parents=True, exist_ok=True)
    truth_doc.write_text("benchmark truth\n", encoding="utf-8")
    skill_doc = repo_root / "odylith" / "skills" / "registry-spec-sync" / "SKILL.md"
    skill_doc.parent.mkdir(parents=True, exist_ok=True)
    skill_doc.write_text("repo skill truth\n", encoding="utf-8")

    rows = live_execution._workspace_strip_paths(repo_root=repo_root)  # noqa: SLF001

    assert Path("AGENTS.md") in rows
    assert Path(".cursor") in rows
    assert Path("odylith/casebook/bugs/AGENTS.md") in rows
    assert Path("odylith/maintainer/agents-guidelines") not in rows
    assert Path("odylith/maintainer/agents-guidelines/RELEASE_BENCHMARKS.md") not in rows
    assert Path("odylith/skills") not in rows
    assert Path("odylith/skills/registry-spec-sync/SKILL.md") not in rows


def test_workspace_strip_paths_preserves_explicit_task_anchors(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    (repo_root / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    nested = repo_root / "odylith" / "casebook" / "bugs" / "AGENTS.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("nested instructions\n", encoding="utf-8")

    rows = live_execution._workspace_strip_paths(  # noqa: SLF001
        repo_root=repo_root,
        preserve_paths=["AGENTS.md", "odylith/casebook/bugs/AGENTS.md"],
    )

    assert Path("AGENTS.md") not in rows
    assert Path("odylith/casebook/bugs/AGENTS.md") not in rows


def test_live_workspace_preserve_paths_include_snapshot_validator_companions() -> None:
    rows = live_execution._live_workspace_preserve_paths(  # noqa: SLF001
        explicit_task_paths=[
            "odylith/radar/source/INDEX.md",
            "odylith/radar/source/INDEX.md",
        ],
        snapshot_paths=[
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        ],
    )

    assert rows == [
        "odylith/radar/source/INDEX.md",
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
    ]


def test_run_live_scenario_preserves_snapshot_validator_paths_for_self_reference_strip(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    captured_preserve_paths: list[str] = []

    def _fake_self_reference_strip_paths(*, repo_root: Path, scenario, preserve_paths):  # type: ignore[no-untyped-def]
        del repo_root, scenario
        captured_preserve_paths.extend(preserve_paths)
        raise RuntimeError("stop-after-strip")

    monkeypatch.setattr(live_execution, "_workspace_strip_paths", lambda **kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(
        live_execution,
        "_scenario_workspace_self_reference_strip_paths",
        _fake_self_reference_strip_paths,
    )
    monkeypatch.setattr(
        live_execution.odylith_reasoning,
        "reasoning_config_from_env",
        lambda **kwargs: odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="gpt-5.4",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="medium",
        ),
    )
    monkeypatch.setattr(
        live_execution,
        "_resolved_live_execution_contract",
        lambda **kwargs: {
            "runner": "live_codex_cli",
            "codex_bin": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
        },
    )

    with pytest.raises(RuntimeError, match="stop-after-strip"):
        live_execution.run_live_scenario(
            repo_root=repo_root,
            scenario={
                "family": "governed_surface_sync",
                "prompt": "Preserve validator runtime companions.",
                "changed_paths": ["odylith/radar/source/INDEX.md"],
                "required_paths": ["odylith/radar/source/INDEX.md"],
                "validation_commands": ["odylith sync --repo-root . --check-only"],
                "needs_write": False,
            },
            mode="odylith_on",
            packet_source="benchmark_packet",
            prompt_payload={},
            snapshot_paths=[
                "odylith/radar/source/INDEX.md",
                "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
            ],
        )

    assert "odylith/radar/source/INDEX.md" in captured_preserve_paths
    assert "src/odylith/runtime/evaluation/odylith_benchmark_runner.py" in captured_preserve_paths


def test_restore_workspace_validator_truth_restores_stripped_files_only(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    truth_root = tmp_path / "validator-truth"
    workspace_root.mkdir(parents=True, exist_ok=True)
    truth_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "AGENTS.md").write_text("stale instructions\n", encoding="utf-8")
    (truth_root / "AGENTS.md").write_text("root instructions\n", encoding="utf-8")
    nested = truth_root / "odylith" / "casebook" / "bugs" / "AGENTS.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("nested instructions\n", encoding="utf-8")

    strip_paths = [Path("AGENTS.md"), Path("odylith/casebook/bugs/AGENTS.md"), Path(".cursor")]
    live_execution._restore_workspace_validator_truth(  # noqa: SLF001
        truth_root=truth_root,
        workspace_root=workspace_root,
        strip_paths=strip_paths,
    )

    assert (workspace_root / "AGENTS.md").read_text(encoding="utf-8") == "root instructions\n"
    assert (workspace_root / "odylith" / "casebook" / "bugs" / "AGENTS.md").read_text(encoding="utf-8") == (
        "nested instructions\n"
    )
    assert not (workspace_root / ".cursor").exists()


def test_capture_workspace_validator_truth_copies_scoped_workspace_files_only(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    truth_root = tmp_path / "validator-truth"
    workspace_root.mkdir(parents=True, exist_ok=True)
    truth_root.mkdir(parents=True, exist_ok=True)
    (workspace_root / "AGENTS.md").write_text("scoped root truth\n", encoding="utf-8")
    nested = workspace_root / "odylith" / "AGENTS.md"
    nested.parent.mkdir(parents=True, exist_ok=True)
    nested.write_text("scoped odylith truth\n", encoding="utf-8")
    (workspace_root / ".cursor").mkdir(parents=True, exist_ok=True)

    live_execution._capture_workspace_validator_truth(  # noqa: SLF001
        workspace_root=workspace_root,
        truth_root=truth_root,
        strip_paths=[Path("AGENTS.md"), Path("odylith/AGENTS.md"), Path(".cursor")],
    )

    assert (truth_root / "AGENTS.md").read_text(encoding="utf-8") == "scoped root truth\n"
    assert (truth_root / "odylith" / "AGENTS.md").read_text(encoding="utf-8") == "scoped odylith truth\n"
    assert not (truth_root / ".cursor").exists()


def test_restore_workspace_validator_truth_noops_when_workspace_root_is_missing(tmp_path: Path) -> None:
    workspace_root = tmp_path / "missing-workspace"
    truth_root = tmp_path / "truth"
    (truth_root / "AGENTS.md").parent.mkdir(parents=True, exist_ok=True)
    (truth_root / "AGENTS.md").write_text("restored truth\n", encoding="utf-8")

    live_execution._restore_workspace_validator_truth(  # noqa: SLF001
        workspace_root=workspace_root,
        truth_root=truth_root,
        strip_paths=[Path("AGENTS.md")],
    )

    assert not workspace_root.exists()


def test_run_live_scenario_returns_failed_payload_when_workspace_disappears_midflight(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir(parents=True, exist_ok=True)
    workspace_root = tmp_path / "workspace"
    truth_root = tmp_path / "truth"
    workspace_root.mkdir(parents=True, exist_ok=True)
    truth_root.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def _fake_temporary_worktree(*, repo_root: Path, strip_paths, snapshot_paths):  # type: ignore[no-untyped-def]
        del repo_root, strip_paths, snapshot_paths
        yield workspace_root, truth_root

    @contextlib.contextmanager
    def _fake_temporary_codex_home(*, execution_contract, environ=None):  # type: ignore[no-untyped-def]
        del execution_contract, environ
        yield tmp_path / "codex-home"

    def _fake_run_subprocess_capture(*, command, cwd, env=None, input_text=None, timeout_seconds=None):  # type: ignore[no-untyped-def]
        del command, env, input_text, timeout_seconds
        shutil.rmtree(cwd)
        raise FileNotFoundError(str(cwd))

    monkeypatch.setattr(live_execution, "_temporary_worktree", _fake_temporary_worktree)
    monkeypatch.setattr(live_execution, "_temporary_codex_home", _fake_temporary_codex_home)
    monkeypatch.setattr(live_execution, "_workspace_strip_paths", lambda **kwargs: [])  # type: ignore[arg-type]
    monkeypatch.setattr(live_execution, "_sandbox_process_env", lambda **kwargs: {"PATH": "/usr/bin:/bin"})  # type: ignore[arg-type]
    monkeypatch.setattr(
        live_execution,
        "_codex_exec_command",
        lambda **kwargs: ["codex", "exec", "--skip-git-repo-check", "-C", str(workspace_root)],  # type: ignore[arg-type]
    )
    monkeypatch.setattr(live_execution, "_agent_prompt", lambda **kwargs: "prompt")  # type: ignore[arg-type]
    monkeypatch.setattr(live_execution, "_run_subprocess_capture", _fake_run_subprocess_capture)
    monkeypatch.setattr(
        live_execution.odylith_reasoning,
        "reasoning_config_from_env",
        lambda **kwargs: odylith_reasoning.ReasoningConfig(
            mode="auto",
            provider="codex-cli",
            model="gpt-5.4",
            base_url="",
            api_key="",
            scope_cap=5,
            timeout_seconds=20.0,
            codex_bin="codex",
            codex_reasoning_effort="medium",
        ),
    )
    monkeypatch.setattr(
        live_execution,
        "_resolved_live_execution_contract",
        lambda **kwargs: {
            "runner": "live_codex_cli",
            "codex_bin": "codex",
            "model": "gpt-5.4",
            "reasoning_effort": "medium",
        },
    )

    result = live_execution.run_live_scenario(
        repo_root=repo_root,
        scenario={
            "prompt": "Probe workspace disappearance handling.",
            "required_paths": [],
            "validation_commands": [],
            "needs_write": False,
        },
        mode="odylith_on",
        packet_source="benchmark_packet",
        prompt_payload={},
        snapshot_paths=[],
    )

    assert result["packet"]["live_status"] == "failed"
    assert result["expectation_ok"] is False
    assert result["validation_results"]["status"] == "not_applicable"
    assert result["live_execution"]["failure_artifacts"]["workspace_state_post_codex"]["workspace_root_exists"] is False
    assert result["live_execution"]["failure_artifacts"]["workspace_state_pre_validator"]["workspace_root_exists"] is False


def test_overlay_workspace_repo_snapshot_applies_dirty_tracked_and_untracked_changes(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    repo_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / "tracked.txt").write_text("base\n", encoding="utf-8")
    (repo_root / "removed.txt").write_text("remove\n", encoding="utf-8")
    subprocess.run(["git", "add", "tracked.txt", "removed.txt"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    (workspace_root / "tracked.txt").write_text("base\n", encoding="utf-8")
    (workspace_root / "removed.txt").write_text("remove\n", encoding="utf-8")

    (repo_root / "tracked.txt").write_text("dirty\n", encoding="utf-8")
    (repo_root / "newfile.txt").write_text("new\n", encoding="utf-8")
    (repo_root / "removed.txt").unlink()

    live_execution._overlay_workspace_repo_snapshot(  # noqa: SLF001
        repo_root=repo_root,
        workspace_root=workspace_root,
    )

    assert (workspace_root / "tracked.txt").read_text(encoding="utf-8") == "dirty\n"
    assert (workspace_root / "newfile.txt").read_text(encoding="utf-8") == "new\n"
    assert not (workspace_root / "removed.txt").exists()


def test_overlay_workspace_repo_snapshot_limits_dirty_overlay_to_allowed_paths(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    workspace_root = tmp_path / "workspace"
    repo_root.mkdir(parents=True, exist_ok=True)
    workspace_root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=repo_root, text=True, capture_output=True, check=True)
    subprocess.run(["git", "config", "user.email", "bench@example.com"], cwd=repo_root, check=True)
    subprocess.run(["git", "config", "user.name", "Benchmark"], cwd=repo_root, check=True)
    (repo_root / "keep.txt").write_text("base keep\n", encoding="utf-8")
    (repo_root / "drop.txt").write_text("base drop\n", encoding="utf-8")
    subprocess.run(["git", "add", "keep.txt", "drop.txt"], cwd=repo_root, check=True)
    subprocess.run(["git", "commit", "-m", "base"], cwd=repo_root, text=True, capture_output=True, check=True)

    (workspace_root / "keep.txt").write_text("base keep\n", encoding="utf-8")
    (workspace_root / "drop.txt").write_text("base drop\n", encoding="utf-8")
    (repo_root / "keep.txt").write_text("dirty keep\n", encoding="utf-8")
    (repo_root / "drop.txt").write_text("dirty drop\n", encoding="utf-8")

    live_execution._overlay_workspace_repo_snapshot(  # noqa: SLF001
        repo_root=repo_root,
        workspace_root=workspace_root,
        allowed_paths=["keep.txt"],
    )

    assert (workspace_root / "keep.txt").read_text(encoding="utf-8") == "dirty keep\n"
    assert (workspace_root / "drop.txt").read_text(encoding="utf-8") == "base drop\n"


def test_observed_paths_from_events_ignores_transitive_paths_in_file_content_output(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    guide = workspace_root / "docs" / "benchmarks" / "REVIEWER_GUIDE.md"
    readme = workspace_root / "README.md"
    svg = workspace_root / "docs" / "benchmarks" / "odylith-benchmark-frontier.svg"
    guide.parent.mkdir(parents=True, exist_ok=True)
    guide.write_text("guide\n", encoding="utf-8")
    readme.write_text("readme\n", encoding="utf-8")
    svg.write_text("<svg />\n", encoding="utf-8")

    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[
            {
                "item": {
                    "type": "command_execution",
                    "command": "/bin/bash -c \"sed -n '1,200p' docs/benchmarks/REVIEWER_GUIDE.md\"",
                    "aggregated_output": "See README.md and docs/benchmarks/odylith-benchmark-frontier.svg for more.\n",
                }
            }
        ],
        workspace_root=workspace_root,
        structured_output={"changed_files": []},
    )

    assert observed == ["docs/benchmarks/REVIEWER_GUIDE.md"]


def test_observed_paths_from_events_keeps_paths_from_listing_output(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    reviewer = workspace_root / "docs" / "benchmarks" / "REVIEWER_GUIDE.md"
    bench_readme = workspace_root / "docs" / "benchmarks" / "README.md"
    reviewer.parent.mkdir(parents=True, exist_ok=True)
    reviewer.write_text("guide\n", encoding="utf-8")
    bench_readme.write_text("bench readme\n", encoding="utf-8")

    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[
            {
                "item": {
                    "type": "command_execution",
                    "command": "/bin/bash -c \"rg -n 'benchmark' docs/benchmarks\"",
                    "aggregated_output": (
                        "docs/benchmarks/REVIEWER_GUIDE.md:1:Reviewer guidance\n"
                        "docs/benchmarks/README.md:2:Benchmark methodology\n"
                    ),
                }
            }
        ],
        workspace_root=workspace_root,
        structured_output={"changed_files": []},
    )

    assert observed == ["docs/benchmarks/REVIEWER_GUIDE.md", "docs/benchmarks/README.md"]


def test_observed_paths_from_events_ignores_transitive_markdown_links_in_grep_output(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    radar_index = workspace_root / "odylith" / "radar" / "source" / "INDEX.md"
    idea_one = (
        workspace_root
        / "odylith"
        / "radar"
        / "source"
        / "ideas"
        / "2026-03"
        / "2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md"
    )
    idea_two = (
        workspace_root
        / "odylith"
        / "radar"
        / "source"
        / "ideas"
        / "2026-03"
        / "2026-03-31-odylith-raw-codex-baseline-and-four-lane-benchmark-table.md"
    )
    radar_index.parent.mkdir(parents=True, exist_ok=True)
    idea_one.parent.mkdir(parents=True, exist_ok=True)
    radar_index.write_text("index\n", encoding="utf-8")
    idea_one.write_text("idea one\n", encoding="utf-8")
    idea_two.write_text("idea two\n", encoding="utf-8")

    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[
            {
                "item": {
                    "type": "command_execution",
                    "command": "/bin/bash -c \"rg -n 'B-02[12]' odylith/radar/source/INDEX.md\"",
                    "aggregated_output": (
                        "odylith/radar/source/INDEX.md:120:- [B-021]"
                        "(odylith/radar/source/ideas/2026-03/2026-03-29-odylith-complex-repo-benchmark-corpus-expansion-and-frontier-improvement.md)\n"
                        "odylith/radar/source/INDEX.md:121:- [B-022]"
                        "(odylith/radar/source/ideas/2026-03/2026-03-31-odylith-raw-codex-baseline-and-four-lane-benchmark-table.md)\n"
                    ),
                }
            }
        ],
        workspace_root=workspace_root,
        structured_output={"changed_files": []},
    )

    assert observed == ["odylith/radar/source/INDEX.md"]


def test_resolve_workspace_file_ignores_enametoolong_path_component(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    workspace_root.mkdir(parents=True, exist_ok=True)

    resolved = live_execution._resolve_workspace_file(  # noqa: SLF001
        "a" * 300,
        workspace_root=workspace_root,
    )

    assert resolved == ""


def test_observed_paths_from_events_ignores_invalid_changed_file_tokens(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    readme = workspace_root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("ok\n", encoding="utf-8")

    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[
            {
                "item": {
                    "type": "file_change",
                    "changes": [
                        {"path": "a" * 300},
                        {"path": "README.md"},
                    ],
                }
            }
        ],
        workspace_root=workspace_root,
        structured_output={"changed_files": ["b" * 300]},
    )

    assert observed == ["README.md"]


def test_candidate_write_paths_include_structured_output_changed_files_when_events_are_missing(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    browser_test = workspace_root / "tests" / "integration" / "runtime" / "test_tooling_dashboard_onboarding_browser.py"
    browser_test.parent.mkdir(parents=True, exist_ok=True)
    browser_test.write_text("def test_browser():\n    assert True\n", encoding="utf-8")

    candidate_write_paths = live_execution._candidate_write_paths(  # noqa: SLF001
        events=[],
        workspace_root=workspace_root,
        structured_output={
            "changed_files": [
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "missing.py",
                "a" * 300,
            ]
        },
    )

    assert candidate_write_paths == ["tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py"]


def test_workspace_state_changed_paths_dedupes_git_status_and_differences() -> None:
    changed_paths = live_execution._workspace_state_changed_paths(  # noqa: SLF001
        workspace_state={
            "git_status_paths": [
                "README.md",
                "docs/benchmarks/README.md",
                "README.md",
            ],
            "differences": [
                {"path": "docs/benchmarks/README.md", "status": "different_file"},
                {"path": "src/odylith/runtime/evaluation/odylith_benchmark_runner.py", "status": "workspace_extra"},
                {"path": "ignored.txt", "status": "same"},
            ],
        }
    )

    assert changed_paths == [
        "README.md",
        "docs/benchmarks/README.md",
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
    ]


def test_workspace_state_delta_paths_ignores_unchanged_preexisting_dirty_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    readme = workspace_root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("dirty before\n", encoding="utf-8")

    baseline = {
        "git_status_paths": ["README.md"],
        "fingerprints": {
            "README.md": live_execution._workspace_file_fingerprint(  # noqa: SLF001
                workspace_root=workspace_root,
                relative_path="README.md",
            )
        },
    }
    workspace_state = {
        "git_status_paths": ["README.md"],
        "differences": [{"path": "README.md", "status": "different_file"}],
    }

    changed_paths = live_execution._workspace_state_delta_paths(  # noqa: SLF001
        baseline=baseline,
        workspace_root=workspace_root,
        workspace_state=workspace_state,
    )

    assert changed_paths == []


def test_workspace_state_delta_paths_detects_new_and_modified_dirty_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    readme = workspace_root / "README.md"
    readme.parent.mkdir(parents=True, exist_ok=True)
    readme.write_text("dirty before\n", encoding="utf-8")

    baseline = {
        "git_status_paths": ["README.md"],
        "fingerprints": {
            "README.md": live_execution._workspace_file_fingerprint(  # noqa: SLF001
                workspace_root=workspace_root,
                relative_path="README.md",
            )
        },
    }

    readme.write_text("dirty after\n", encoding="utf-8")
    browser_test = workspace_root / "tests" / "integration" / "runtime" / "test_tooling_dashboard_onboarding_browser.py"
    browser_test.parent.mkdir(parents=True, exist_ok=True)
    browser_test.write_text("def test_browser():\n    assert True\n", encoding="utf-8")

    workspace_state = {
        "git_status_paths": [
            "README.md",
            "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
        ],
        "differences": [
            {"path": "README.md", "status": "different_file"},
            {
                "path": "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                "status": "workspace_extra",
            },
        ],
    }

    changed_paths = live_execution._workspace_state_delta_paths(  # noqa: SLF001
        baseline=baseline,
        workspace_root=workspace_root,
        workspace_state=workspace_state,
    )

    assert changed_paths == [
        "README.md",
        "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
    ]


def test_workspace_state_delta_paths_ignores_preexisting_workspace_noise(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "README.md").parent.mkdir(parents=True, exist_ok=True)
    (workspace_root / "README.md").write_text("dirty before\n", encoding="utf-8")
    browser_test = workspace_root / "tests" / "integration" / "runtime" / "test_tooling_dashboard_onboarding_browser.py"
    browser_test.parent.mkdir(parents=True, exist_ok=True)
    browser_test.write_text("def test_browser():\n    assert True\n", encoding="utf-8")

    changed_paths = live_execution._workspace_state_delta_paths(  # noqa: SLF001
        baseline={
            "git_status_paths": [
                "AGENTS.md",
                "README.md",
            ],
            "fingerprints": {
                "AGENTS.md": "missing",
                "README.md": live_execution._workspace_file_fingerprint(  # noqa: SLF001
                    workspace_root=workspace_root,
                    relative_path="README.md",
                ),
            },
        },
        workspace_root=workspace_root,
        workspace_state={
            "git_status_paths": [
                "AGENTS.md",
                "README.md",
                "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
            ],
            "differences": [
                {"path": "AGENTS.md", "status": "workspace_missing"},
                {"path": "README.md", "status": "different_file"},
                {
                    "path": "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
                    "status": "different_file",
                },
            ],
        },
    )

    assert changed_paths == ["tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py"]


def test_meaningful_candidate_write_paths_filters_benchmark_temp_and_env_noise() -> None:
    changed_paths = live_execution._meaningful_candidate_write_paths(  # noqa: SLF001
        [
            ".pytest-tmp/test_browser/current",
            ".pytest_cache/v/cache/lastfailed",
            ".tmp-pytest-browser-contract/test_build_release_spotlight_fcurrent",
            ".tmp-pytest-cache-browser-contract/CACHEDIR.TAG",
            ".tmp-benchmark-publication-proof-graphs/odylith-benchmark-frontier.svg",
            ".venv/bin/pytest",
            "tmp/pytest/test_render_graph_assets_prefe0/odylith-benchmark-frontier.svg",
            "tmp/pytest/test_render_graph_assets_prefecurrent",
            "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
            "src/odylith/runtime/surfaces/shell_onboarding.py",
        ]
    )

    assert changed_paths == [
        "tests/integration/runtime/test_tooling_dashboard_onboarding_browser.py",
        "src/odylith/runtime/surfaces/shell_onboarding.py",
    ]


def test_observed_paths_from_events_include_prompt_selected_grounding_surfaces(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    (workspace_root / "src" / "odylith" / "install").mkdir(parents=True, exist_ok=True)
    (workspace_root / "odylith" / "agents-guidelines").mkdir(parents=True, exist_ok=True)
    (workspace_root / "odylith" / "skills" / "subagent-orchestrator").mkdir(parents=True, exist_ok=True)
    (workspace_root / "src" / "odylith" / "install" / "agents.py").write_text("agents\n", encoding="utf-8")
    (workspace_root / "odylith" / "AGENTS.md").write_text("odylith\n", encoding="utf-8")
    (workspace_root / "odylith" / "agents-guidelines" / "SUBAGENT_ROUTING_AND_ORCHESTRATION.md").write_text(
        "routing\n",
        encoding="utf-8",
    )
    (workspace_root / "odylith" / "skills" / "subagent-orchestrator" / "SKILL.md").write_text(
        "skill\n",
        encoding="utf-8",
    )

    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[],
        workspace_root=workspace_root,
        structured_output={"changed_files": []},
        prompt_payload={
            "docs": ["odylith/AGENTS.md"],
            "implementation_anchors": ["src/odylith/install/agents.py"],
            "context_packet": {
                "retrieval_plan": {
                    "selected_docs": [
                        "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
                        "odylith/skills/subagent-orchestrator/SKILL.md",
                    ]
                }
            },
        },
    )

    assert observed == [
        "odylith/AGENTS.md",
        "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        "odylith/skills/subagent-orchestrator/SKILL.md",
        "src/odylith/install/agents.py",
    ]


def test_observed_paths_from_events_ignores_prompt_supplied_validation_commands(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspace"
    benchmark_runner_test = workspace_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_runner.py"
    benchmark_graphs_test = workspace_root / "tests" / "unit" / "runtime" / "test_odylith_benchmark_graphs.py"
    reviewer = workspace_root / "docs" / "benchmarks" / "REVIEWER_GUIDE.md"
    benchmark_runner_test.parent.mkdir(parents=True, exist_ok=True)
    reviewer.parent.mkdir(parents=True, exist_ok=True)
    benchmark_runner_test.write_text("def test_runner():\n    assert True\n", encoding="utf-8")
    benchmark_graphs_test.write_text("def test_graphs():\n    assert True\n", encoding="utf-8")
    reviewer.write_text("guide\n", encoding="utf-8")

    validator_command = (
        "PYTHONPATH=src .venv/bin/pytest -q "
        "tests/unit/runtime/test_odylith_benchmark_runner.py "
        "tests/unit/runtime/test_odylith_benchmark_graphs.py"
    )
    observed = live_execution._observed_paths_from_events(  # noqa: SLF001
        events=[
            {
                "item": {
                    "type": "command_execution",
                    "command": validator_command,
                    "aggregated_output": (
                        "tests/unit/runtime/test_odylith_benchmark_runner.py::test_release\n"
                        "tests/unit/runtime/test_odylith_benchmark_graphs.py::test_heatmap\n"
                    ),
                }
            }
        ],
        workspace_root=workspace_root,
        structured_output={"changed_files": []},
        prompt_payload={"docs": ["docs/benchmarks/REVIEWER_GUIDE.md"]},
        excluded_commands=[validator_command],
        neutral_paths=[
            "tests/unit/runtime/test_odylith_benchmark_runner.py",
            "tests/unit/runtime/test_odylith_benchmark_graphs.py",
        ],
    )

    assert observed == ["docs/benchmarks/REVIEWER_GUIDE.md"]


def test_structured_output_recovers_from_agent_message_event_when_last_message_file_is_missing(tmp_path: Path) -> None:
    output = live_execution._structured_output(  # noqa: SLF001
        tmp_path / "missing.json",
        stream_text=(
            '{"type":"thread.started","thread_id":"abc"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"blocked\\",\\"summary\\":\\"probe\\",\\"changed_files\\":[],\\"validation_commands_run\\":[],\\"validation_summary\\":\\"probe\\",\\"notes\\":[]}"}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":5}}\n'
        ),
    )

    assert output["status"] == "blocked"
    assert output["summary"] == "probe"
    assert output["validation_summary"] == "probe"


def test_structured_output_recovers_json_from_fenced_agent_message_event(tmp_path: Path) -> None:
    output = live_execution._structured_output(  # noqa: SLF001
        tmp_path / "missing.json",
        stream_text=(
            '{"type":"thread.started","thread_id":"abc"}\n'
            '{"type":"item.completed","item":{"type":"agent_message","text":"Final status:\\n```json\\n{\\"status\\":\\"completed\\",\\"summary\\":\\"kept bounded truth aligned\\",\\"changed_files\\":[],\\"validation_commands_run\\":[],\\"validation_summary\\":\\"passed\\",\\"notes\\":[]}\\n```"}}\n'
            '{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":5}}\n'
        ),
    )

    assert output["status"] == "completed"
    assert output["summary"] == "kept bounded truth aligned"
    assert output["validation_summary"] == "passed"


def test_structured_output_recovers_from_top_level_agent_message_event(tmp_path: Path) -> None:
    output = live_execution._structured_output(  # noqa: SLF001
        tmp_path / "missing.json",
        stream_text=(
            '{"type":"agent_message","text":"{\\"status\\":\\"completed\\",\\"summary\\":\\"kept bounded truth aligned\\",'
            '\\"changed_files\\":[],\\"validation_commands_run\\":[],\\"validation_summary\\":\\"passed\\",\\"notes\\":[]}"}\n'
        ),
    )

    assert output["status"] == "completed"
    assert output["validation_summary"] == "passed"


def test_structured_output_recovers_from_unreadable_file_via_event_stream(tmp_path: Path) -> None:
    output_path = tmp_path / "result.json"
    output_path.write_text("Final status:\n```json\nnot valid\n```", encoding="utf-8")

    output = live_execution._structured_output(  # noqa: SLF001
        output_path,
        stream_text=(
            '{"type":"item.completed","item":{"type":"agent_message","text":"{\\"status\\":\\"blocked\\",\\"summary\\":\\"probe\\",'
            '\\"changed_files\\":[],\\"validation_commands_run\\":[],\\"validation_summary\\":\\"probe\\",\\"notes\\":[]}"}}\n'
        ),
    )

    assert output["status"] == "blocked"
    assert output["summary"] == "probe"


def test_structured_output_recovers_plain_json_from_stream_text_when_events_are_unavailable(tmp_path: Path) -> None:
    output = live_execution._structured_output(  # noqa: SLF001
        tmp_path / "missing.json",
        stream_text=(
            '{"status":"completed","summary":"plain stdout fallback","changed_files":[],"validation_commands_run":[],"validation_summary":"passed","notes":[]}'
        ),
    )

    assert output["status"] == "completed"
    assert output["summary"] == "plain stdout fallback"


def test_structured_output_reports_missing_schema_when_no_file_or_agent_message_exists(tmp_path: Path) -> None:
    output = live_execution._structured_output(  # noqa: SLF001
        tmp_path / "missing.json",
        stream_text='{"type":"turn.completed","usage":{"input_tokens":12,"output_tokens":5}}\n',
    )

    assert output["status"] == "failed"
    assert output["validation_summary"] == "missing_schema_output"
