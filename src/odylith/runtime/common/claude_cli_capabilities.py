"""Shared Claude CLI capability inspection and effective-settings rendering.

This module mirrors `codex_cli_capabilities.py` but for the Claude Code
host. It captures a deterministic frozen snapshot of the local Claude CLI
posture, the project-asset surface state in the repo, and the hook event
coverage that the Odylith `.claude/` contract relies on. Callers consume the
snapshot through `inspect_claude_cli_capabilities()` and the
`render_effective_claude_project_settings()` / `write_effective_claude_project_settings()`
helpers, just like the Codex equivalents.

The snapshot is intentionally narrow: it reads state and runs cheap probes
but never raises into the caller. Any failure degrades to a baseline-safe
posture so Odylith stays usable on Claude even when the Claude CLI is
missing, the local build is older, or a probe is unavailable.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text


_CLAUDE_VERSION_RE = re.compile(r"(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)")
_UNSUPPORTED_TOKENS = (
    "unexpected argument",
    "unrecognized subcommand",
    "unknown subcommand",
    "unknown command",
)
_PROJECT_DOC_FALLBACK_FILENAMES: tuple[str, ...] = ("CLAUDE.md", "AGENTS.md")
_BASELINE_CONTRACT = "CLAUDE.md + ./.odylith/bin/odylith"
_PROJECT_ASSETS_MODE = "first_class_project_surface"
_FUTURE_VERSION_POLICY = "capability_based_no_max_pin"
_DEFAULT_CLAUDE_BIN = "claude"


@dataclass(frozen=True)
class ClaudeCliCapabilitySnapshot:
    repo_root: str
    claude_bin: str
    claude_available: bool
    claude_version_raw: str
    claude_version: str
    baseline_contract: str
    baseline_ready: bool
    launcher_present: bool
    repo_claude_md_present: bool
    repo_agents_md_present: bool
    project_settings_present: bool
    project_commands_present: bool
    project_agents_present: bool
    project_skills_present: bool
    project_assets_mode: str
    trusted_project_required: bool
    supports_project_hooks: bool
    supports_subagent_hooks: bool
    supports_pre_compact_hook: bool
    supports_statusline_command: bool
    supports_post_tool_matchers: bool
    supports_slash_commands: bool
    future_version_policy: str
    overall_posture: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_repo_root(repo_root: Path | str) -> Path:
    return Path(repo_root).resolve()


def _run_claude_command(
    *,
    repo_root: Path,
    claude_bin: str,
    args: list[str],
    timeout: int = 10,
) -> subprocess.CompletedProcess[str] | None:
    """Run a Claude CLI command with cheap timeouts and a fail-soft return."""
    try:
        return subprocess.run(
            [claude_bin, *args],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except (FileNotFoundError, OSError, subprocess.SubprocessError):
        return None


def parse_claude_version(text: str) -> str:
    """Extract the first SemVer-shaped token from a Claude CLI `--version` line."""
    match = _CLAUDE_VERSION_RE.search(str(text or ""))
    if match:
        return str(match.group("version")).strip()
    tokens = str(text or "").strip().split()
    return tokens[-1] if tokens else ""


def _unsupported_probe(completed: subprocess.CompletedProcess[str] | None) -> bool:
    if completed is None:
        return False
    combined = f"{completed.stdout}\n{completed.stderr}".lower()
    return any(token in combined for token in _UNSUPPORTED_TOKENS)


def _project_settings_path(repo_root: Path) -> Path:
    return repo_root / ".claude" / "settings.json"


def _load_project_settings(repo_root: Path) -> dict[str, Any]:
    path = _project_settings_path(repo_root)
    if not path.is_file():
        return {}
    try:
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _hook_event_present(payload: dict[str, Any], event_name: str) -> bool:
    hooks = payload.get("hooks") if isinstance(payload, dict) else None
    if not isinstance(hooks, dict):
        return False
    bucket = hooks.get(event_name)
    if not isinstance(bucket, list):
        return False
    return bool(bucket)


@lru_cache(maxsize=32)
def _inspect_cached(repo_root: str, claude_bin: str, probe_version: bool) -> ClaudeCliCapabilitySnapshot:
    resolved_root = _resolve_repo_root(repo_root)
    launcher_present = (resolved_root / ".odylith" / "bin" / "odylith").is_file()
    repo_claude_md_present = (resolved_root / "CLAUDE.md").is_file()
    repo_agents_md_present = (resolved_root / "AGENTS.md").is_file()
    settings_payload = _load_project_settings(resolved_root)
    project_settings_present = bool(settings_payload)
    project_commands_present = any((resolved_root / ".claude" / "commands").glob("*.md")) if (
        resolved_root / ".claude" / "commands"
    ).is_dir() else False
    project_agents_present = any((resolved_root / ".claude" / "agents").glob("*.md")) if (
        resolved_root / ".claude" / "agents"
    ).is_dir() else False
    project_skills_present = any((resolved_root / ".claude" / "skills").rglob("SKILL.md")) if (
        resolved_root / ".claude" / "skills"
    ).is_dir() else False
    baseline_ready = launcher_present and (repo_claude_md_present or repo_agents_md_present)

    claude_available = False
    version_raw = ""
    version = ""
    if probe_version:
        version_run = _run_claude_command(repo_root=resolved_root, claude_bin=claude_bin, args=["--version"])
        if version_run is not None and version_run.returncode == 0 and not _unsupported_probe(version_run):
            claude_available = True
            version_raw = str(version_run.stdout or "").strip()
            version = parse_claude_version(version_raw)

    supports_project_hooks = _hook_event_present(settings_payload, "PreToolUse") or _hook_event_present(
        settings_payload, "PostToolUse"
    )
    supports_subagent_hooks = _hook_event_present(settings_payload, "SubagentStart") or _hook_event_present(
        settings_payload, "SubagentStop"
    )
    supports_pre_compact_hook = _hook_event_present(settings_payload, "PreCompact")
    supports_statusline_command = isinstance(settings_payload.get("statusLine"), dict) and bool(
        str((settings_payload.get("statusLine") or {}).get("command", "")).strip()
    )
    supports_post_tool_matchers = False
    if isinstance(settings_payload.get("hooks"), dict):
        post_tool = settings_payload["hooks"].get("PostToolUse")
        if isinstance(post_tool, list):
            for entry in post_tool:
                if not isinstance(entry, dict):
                    continue
                matcher = str(entry.get("matcher") or "").strip()
                if matcher and matcher != "*":
                    supports_post_tool_matchers = True
                    break
    supports_slash_commands = project_commands_present

    overall_posture = "baseline_incomplete"
    if baseline_ready:
        overall_posture = "baseline_safe"
        if project_settings_present:
            overall_posture = "baseline_safe_with_project_assets"
        if claude_available:
            overall_posture = "baseline_safe_with_local_claude_cli"
        if claude_available and project_settings_present:
            overall_posture = "baseline_safe_live_proven"

    return ClaudeCliCapabilitySnapshot(
        repo_root=str(resolved_root),
        claude_bin=claude_bin,
        claude_available=claude_available,
        claude_version_raw=version_raw,
        claude_version=version,
        baseline_contract=_BASELINE_CONTRACT,
        baseline_ready=baseline_ready,
        launcher_present=launcher_present,
        repo_claude_md_present=repo_claude_md_present,
        repo_agents_md_present=repo_agents_md_present,
        project_settings_present=project_settings_present,
        project_commands_present=project_commands_present,
        project_agents_present=project_agents_present,
        project_skills_present=project_skills_present,
        project_assets_mode=_PROJECT_ASSETS_MODE,
        trusted_project_required=False,
        supports_project_hooks=supports_project_hooks,
        supports_subagent_hooks=supports_subagent_hooks,
        supports_pre_compact_hook=supports_pre_compact_hook,
        supports_statusline_command=supports_statusline_command,
        supports_post_tool_matchers=supports_post_tool_matchers,
        supports_slash_commands=supports_slash_commands,
        future_version_policy=_FUTURE_VERSION_POLICY,
        overall_posture=overall_posture,
    )


def clear_claude_cli_capability_cache() -> None:
    _inspect_cached.cache_clear()


def inspect_claude_cli_capabilities(
    repo_root: Path | str = ".",
    *,
    claude_bin: str = _DEFAULT_CLAUDE_BIN,
    probe_version: bool = True,
) -> ClaudeCliCapabilitySnapshot:
    return _inspect_cached(
        str(_resolve_repo_root(repo_root)),
        str(claude_bin or _DEFAULT_CLAUDE_BIN).strip() or _DEFAULT_CLAUDE_BIN,
        bool(probe_version),
    )


_CLAUDE_PROJECT_DIR_TOKEN = "$CLAUDE_PROJECT_DIR"
_CLAUDE_LAUNCHER_INVOCATION = f'"{_CLAUDE_PROJECT_DIR_TOKEN}"/.odylith/bin/odylith'
_CLAUDE_STATUSLINE_INVOCATION = f'"{_CLAUDE_PROJECT_DIR_TOKEN}"/.claude/statusline.sh'


def _baked_hook_command(claude_command: str, *extra_flags: str) -> str:
    parts = [
        _CLAUDE_LAUNCHER_INVOCATION,
        "claude",
        claude_command,
        "--repo-root",
        f'"{_CLAUDE_PROJECT_DIR_TOKEN}"',
    ]
    parts.extend(extra_flags)
    return " ".join(parts)


_BAKED_HOOK_DEFAULT_PERMISSIONS_ALLOWLIST: tuple[str, ...] = (
    "Bash(./.odylith/bin/odylith start:*)",
    "Bash(./.odylith/bin/odylith context:*)",
    "Bash(./.odylith/bin/odylith query:*)",
    "Bash(./.odylith/bin/odylith version:*)",
    "Bash(./.odylith/bin/odylith doctor:*)",
    "Bash(./.odylith/bin/odylith sync:*)",
    "Bash(./.odylith/bin/odylith atlas:*)",
    "Bash(./.odylith/bin/odylith backlog:*)",
    "Bash(./.odylith/bin/odylith validate:*)",
    "Bash(./.odylith/bin/odylith governance:*)",
    "Bash(./.odylith/bin/odylith compass refresh:*)",
    "Bash(./.odylith/bin/odylith compass log:*)",
    "Bash(./.odylith/bin/odylith context-engine:*)",
    "Bash(./.odylith/bin/odylith claude:*)",
    "Bash(./.odylith/bin/odylith codex:*)",
)


def _baked_hooks_block() -> dict[str, Any]:
    """Return the canonical baked CLI-backed hook event map for Claude."""
    return {
        "SessionStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("session-start"),
                        "timeout": 30,
                    }
                ]
            }
        ],
        "SubagentStart": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("subagent-start"),
                        "timeout": 20,
                    }
                ]
            }
        ],
        "UserPromptSubmit": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("prompt-context"),
                        "timeout": 30,
                    }
                ]
            }
        ],
        "PreToolUse": [
            {
                "matcher": "Bash",
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("bash-guard"),
                        "timeout": 10,
                    }
                ],
            }
        ],
        "PostToolUse": [
            {
                "matcher": "Write|Edit|MultiEdit",
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("post-edit-checkpoint"),
                        "async": True,
                        "timeout": 180,
                    }
                ],
            }
        ],
        "PreCompact": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("pre-compact-snapshot", "--quiet"),
                        "timeout": 20,
                    }
                ]
            }
        ],
        "SubagentStop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("subagent-stop"),
                        "async": True,
                        "timeout": 30,
                    }
                ]
            }
        ],
        "Stop": [
            {
                "hooks": [
                    {
                        "type": "command",
                        "command": _baked_hook_command("stop-summary"),
                        "timeout": 20,
                    }
                ]
            }
        ],
    }


def render_effective_claude_project_settings(
    *,
    repo_root: Path | str = ".",
    capabilities: ClaudeCliCapabilitySnapshot | None = None,
) -> str:
    """Render the deterministic effective `.claude/settings.json` body for the repo.

    The renderer is a pure function of the resolved repo root and the
    capability snapshot. It must always produce identical output for the
    same inputs so that install-time writes are idempotent.
    """
    resolved_root = _resolve_repo_root(repo_root)
    snapshot = capabilities or inspect_claude_cli_capabilities(
        repo_root=resolved_root,
        probe_version=False,
    )
    permissions_allow = list(_BAKED_HOOK_DEFAULT_PERMISSIONS_ALLOWLIST)
    payload: dict[str, Any] = {
        "$schema": "https://json.schemastore.org/claude-code-settings.json",
        "permissions": {"allow": permissions_allow},
        "statusLine": {
            "type": "command",
            "command": _CLAUDE_STATUSLINE_INVOCATION,
            "padding": 0,
        },
        "hooks": _baked_hooks_block(),
    }
    # Touch the snapshot to keep linters honest about the parameter being
    # used; future capability-driven branches will gate hook entries here.
    _ = snapshot.baseline_contract
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_effective_claude_project_settings(
    *,
    repo_root: Path | str,
    capabilities: ClaudeCliCapabilitySnapshot | None = None,
) -> Path:
    """Write the deterministic effective `.claude/settings.json` to disk."""
    resolved_root = _resolve_repo_root(repo_root)
    target_path = _project_settings_path(resolved_root)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_text(
        target_path,
        render_effective_claude_project_settings(repo_root=resolved_root, capabilities=capabilities),
        encoding="utf-8",
    )
    return target_path
