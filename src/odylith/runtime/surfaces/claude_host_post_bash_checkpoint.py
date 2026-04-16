"""Claude Code PostToolUse checkpoint for edit-like Bash tool calls.

Claude's direct Write/Edit/MultiEdit tools already route through
``claude post-edit-checkpoint``. This companion hook covers Bash calls that
write files through shell commands, inline scripts, or apply-patch style
payloads so Claude gets the same visible Observation/Proposal checkpoint
coverage as Codex.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.surfaces import claude_host_shared
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint
from odylith.runtime.surfaces import codex_host_shared


def command_from_payload(payload: dict[str, Any]) -> str:
    """Return the shell command represented by a Claude Bash hook payload."""

    return codex_host_shared.command_from_hook_payload(payload)


def should_checkpoint(command: str) -> bool:
    return codex_host_post_bash_checkpoint.should_checkpoint(command)


def command_scoped_governed_paths(*, project_dir: Path | str, command: str) -> list[str]:
    return codex_host_post_bash_checkpoint.command_scoped_governed_paths(
        project_dir=project_dir,
        command=command,
    )


def refresh_governance(*, project_dir: Path | str, paths: list[str]) -> dict[str, str] | None:
    return codex_host_post_bash_checkpoint.refresh_governance(
        project_dir=project_dir,
        paths=paths,
    )


def inferred_command_paths(*, project_dir: Path | str, command: str) -> list[str]:
    return codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=project_dir,
        command=command,
    )


def _post_bash_bundle(
    *,
    project_dir: Path,
    command: str,
    session_id: str = "",
) -> dict[str, Any]:
    changed_paths = inferred_command_paths(project_dir=project_dir, command=command)
    if not changed_paths:
        return {}
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=project_dir,
        host_family="claude",
        turn_phase="post_bash_checkpoint",
        session_id=session_id,
        changed_paths=changed_paths,
    )


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude post-bash-checkpoint",
        description="Nudge Odylith checkpointing after edit-like Claude Bash tool calls.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith governance refresh.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude PostToolUse Bash payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    command = command_from_payload(payload)
    if not should_checkpoint(command):
        return 0

    claude_host_shared.run_odylith(
        project_dir=repo_root,
        args=["start", "--repo-root", "."],
        timeout=20,
    )

    session_id = claude_host_shared.hook_session_id(payload)
    changed = command_scoped_governed_paths(project_dir=repo_root, command=command)
    governance_message = refresh_governance(project_dir=repo_root, paths=changed)
    bundle = _post_bash_bundle(
        project_dir=repo_root,
        command=command,
        session_id=session_id,
    )
    developer_context = (
        host_surface_runtime.render_developer_context(
            bundle,
            markdown=True,
            include_proposal=True,
            include_closeout=True,
        )
        if bundle
        else ""
    )
    live_intervention = (
        host_surface_runtime.render_visible_live_intervention(
            bundle,
            markdown=True,
            include_proposal=True,
        )
        if bundle
        else ""
    )
    if bundle and developer_context:
        conversation_surface.append_intervention_events(
            repo_root=repo_root,
            bundle=bundle,
            include_proposal=True,
            delivery_channel="system_message_and_assistant_fallback",
            delivery_status="assistant_fallback_ready",
            render_surface="claude_post_tool_use",
        )
    payload_out = host_surface_runtime.claude_post_tool_payload(
        developer_context=developer_context,
        system_message=host_surface_runtime.compose_checkpoint_system_message(
            live_intervention=live_intervention,
            governance_status=_normalize_string((governance_message or {}).get("systemMessage")),
        ),
    )
    if payload_out:
        sys.stdout.write(json.dumps(payload_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
