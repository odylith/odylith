"""Guidance Behavior Guidance Contracts helpers for the Odylith governance layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any


GUIDANCE_SURFACE_CONTRACT = "odylith_guidance_behavior_guidance_surfaces.v1"
VALIDATOR_COMMAND = "odylith validate guidance-behavior --repo-root ."
BENCHMARK_COMMAND = "odylith benchmark --profile quick --family guidance_behavior"
HOSTS = ("codex", "claude")
LANES = ("consumer", "pinned_dogfood", "source_local")
CHECK_ID = "guidance_behavior_guidance_surface_contract"

SURFACE_TOKEN_REQUIREMENTS: tuple[dict[str, Any], ...] = (
    {
        "path": "odylith/agents-guidelines/ODYLITH_CONTEXT_ENGINE.md",
        "tokens": (
            "Guidance Behavior",
            "compact `guidance_behavior_summary`",
            "full validator",
        ),
    },
    {
        "path": "odylith/agents-guidelines/VALIDATION_AND_TESTING.md",
        "tokens": (
            VALIDATOR_COMMAND,
            BENCHMARK_COMMAND,
            "consumer",
            "pinned dogfood",
            "source-local",
        ),
    },
    {
        "path": "odylith/agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md",
        "tokens": (
            "Guidance Behavior",
            "Context Engine",
            "Execution Engine",
            "Memory Contracts",
            "Tribunal",
            "benchmark",
        ),
    },
    {
        "path": "odylith/agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md",
        "tokens": (
            "guidance-bounded-delegation-contract",
            "owner",
            "goal",
            "expected output",
            "termination condition",
            "validation expectation",
        ),
    },
    {
        "path": "odylith/agents-guidelines/CODEX_HOST_CONTRACT.md",
        "tokens": (
            "Guidance Behavior",
            "Codex",
            "spawn_agent",
            VALIDATOR_COMMAND,
        ),
    },
    {
        "path": "odylith/agents-guidelines/CLAUDE_HOST_CONTRACT.md",
        "tokens": (
            "Guidance Behavior",
            "Claude",
            "Task-tool subagents",
            VALIDATOR_COMMAND,
        ),
    },
    {
        "path": "odylith/skills/odylith-guidance-behavior/SKILL.md",
        "tokens": (
            "Use this skill",
            VALIDATOR_COMMAND,
            BENCHMARK_COMMAND,
        ),
    },
    {
        "path": "odylith/skills/odylith-context-engine-operations/SKILL.md",
        "tokens": (
            "Guidance Behavior",
            "guidance_behavior_summary",
            "full validator",
        ),
    },
    {
        "path": "odylith/skills/odylith-subagent-orchestrator/SKILL.md",
        "tokens": (
            "guidance-bounded-delegation-contract",
            "owner",
            "goal",
            "expected output",
            "termination condition",
            "validation expectation",
        ),
    },
    {
        "path": ".agents/skills/odylith-guidance-behavior/SKILL.md",
        "tokens": (
            "description: Use when",
            "guidance behavior pressure cases",
        ),
    },
    {
        "path": ".claude/commands/odylith-guidance-behavior.md",
        "tokens": (
            VALIDATOR_COMMAND,
            "$ARGUMENTS",
        ),
    },
)


def _dedupe(values: list[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        token = str(value or "").strip()
        if not token or token in seen:
            continue
        seen.add(token)
        rows.append(token)
    return rows


def guidance_surface_contract_summary() -> dict[str, Any]:
    return {
        "contract": GUIDANCE_SURFACE_CONTRACT,
        "hosts": list(HOSTS),
        "lanes": list(LANES),
        "validator_command": VALIDATOR_COMMAND,
        "benchmark_command": BENCHMARK_COMMAND,
        "source_refs": [str(row["path"]) for row in SURFACE_TOKEN_REQUIREMENTS],
        "hot_path": {
            "full_validation": False,
            "provider_calls": False,
            "guidance_surface_scan": "validator_only",
        },
    }


def validate_guidance_surface_contracts(*, repo_root: Path) -> dict[str, Any]:
    failures: list[dict[str, str]] = []
    evidence: list[str] = []
    root = Path(repo_root)
    for requirement in SURFACE_TOKEN_REQUIREMENTS:
        relative_path = str(requirement.get("path", "")).strip()
        path = root / relative_path
        if not path.is_file():
            failures.append(
                {
                    "check_id": CHECK_ID,
                    "message": "required guidance behavior surface is missing",
                    "path": relative_path,
                }
            )
            continue
        text = path.read_text(encoding="utf-8")
        missing = [
            str(token)
            for token in requirement.get("tokens", ())
            if str(token) and str(token) not in text
        ]
        if missing:
            failures.append(
                {
                    "check_id": CHECK_ID,
                    "message": "guidance behavior surface is missing token(s): " + ", ".join(missing),
                    "path": relative_path,
                }
            )
            continue
        evidence.append(relative_path)
    summary = guidance_surface_contract_summary()
    return {
        "id": CHECK_ID,
        "status": "passed" if not failures else "failed",
        "contract": GUIDANCE_SURFACE_CONTRACT,
        "hosts": list(HOSTS),
        "lanes": list(LANES),
        "evidence": _dedupe(evidence),
        "source_refs": summary["source_refs"],
        "failures": failures,
    }


__all__ = [
    "BENCHMARK_COMMAND",
    "CHECK_ID",
    "GUIDANCE_SURFACE_CONTRACT",
    "HOSTS",
    "LANES",
    "VALIDATOR_COMMAND",
    "guidance_surface_contract_summary",
    "validate_guidance_surface_contracts",
]
