"""Capability-based Claude Code compatibility reporting for Odylith.

Mirrors `codex_host_compatibility.py`. Reads the deterministic capability
snapshot produced by `claude_cli_capabilities.inspect_claude_cli_capabilities`
and renders either a human-readable report or a JSON payload. The exit code
maps to `baseline_ready` so install-time and CI invocations can gate on the
same fail-soft semantics as the Codex compatibility surface.
"""

from __future__ import annotations

import argparse
import json
import sys

from odylith.runtime.common import claude_cli_capabilities


ClaudeCompatibilityReport = claude_cli_capabilities.ClaudeCliCapabilitySnapshot
inspect_claude_compatibility = claude_cli_capabilities.inspect_claude_cli_capabilities
parse_claude_version = claude_cli_capabilities.parse_claude_version
_run_claude_command = claude_cli_capabilities._run_claude_command  # noqa: SLF001


def _report_notes(report: ClaudeCompatibilityReport) -> list[str]:
    notes = [
        "Core Odylith support on Claude Code is the repo-root CLAUDE.md/AGENTS.md contract plus `./.odylith/bin/odylith`.",
        "Repo-scoped `.claude/` settings, hooks, slash commands, subagents, and skills are first-class project surfaces and ship with the install.",
        "Claude Code project assets do not require a trusted-project approval gate; checked-in `.claude/settings.json` activates immediately.",
        "Version compatibility is capability-based and does not pin a maximum Claude CLI version.",
    ]
    if report.claude_available and report.claude_version:
        notes.append(f"Local Claude CLI detected: `claude {report.claude_version}`.")
    elif not report.claude_available:
        notes.append("Local Claude CLI was not detected on PATH during this compatibility check.")
    if report.project_settings_present:
        notes.append("`.claude/settings.json` is present in the repo root and drives the project surface posture.")
    else:
        notes.append("`.claude/settings.json` was not detected; the install-time renderer will materialize it on the next install or sync.")
    if report.supports_project_hooks:
        notes.append("Project hook events (`PreToolUse` / `PostToolUse`) are wired in `.claude/settings.json`.")
    else:
        notes.append("Project hook events (`PreToolUse` / `PostToolUse`) are not yet wired in `.claude/settings.json`.")
    if report.supports_subagent_hooks:
        notes.append("Subagent lifecycle hooks (`SubagentStart` / `SubagentStop`) are wired for Claude project subagents.")
    else:
        notes.append("Subagent lifecycle hooks (`SubagentStart` / `SubagentStop`) are not yet wired for Claude project subagents.")
    if report.supports_pre_compact_hook:
        notes.append("Claude `PreCompact` hook is wired and routes to the Odylith CLI snapshot writer.")
    else:
        notes.append("Claude `PreCompact` hook is not wired; the Odylith CLI snapshot writer is available but not yet attached.")
    if report.supports_statusline_command:
        notes.append("`statusLine.command` is wired in `.claude/settings.json`.")
    else:
        notes.append("`statusLine.command` is not yet wired; the Odylith CLI statusline renderer is available but not attached.")
    if report.supports_post_tool_matchers:
        notes.append("`PostToolUse` hooks declare a non-wildcard matcher (e.g. `Write|Edit|MultiEdit`).")
    else:
        notes.append("`PostToolUse` hooks do not declare a non-wildcard matcher; selective post-edit refresh is not yet active.")
    if report.supports_slash_commands:
        notes.append("Project slash commands are present under `.claude/commands/`.")
    else:
        notes.append("No project slash commands were detected under `.claude/commands/`.")
    if report.project_agents_present:
        notes.append("Project subagents are present under `.claude/agents/`.")
    if report.project_skills_present:
        notes.append("Claude-discoverable Odylith skills are present under `.claude/skills/`.")
    return notes


def render_claude_compatibility(report: ClaudeCompatibilityReport) -> str:
    lines = [
        "Claude Code compatibility report",
        f"Baseline contract: {report.baseline_contract}",
        f"Baseline ready: {'yes' if report.baseline_ready else 'no'}",
        f"Claude CLI: {report.claude_version_raw or 'not detected on PATH'}",
        f"Project settings: {'present' if report.project_settings_present else 'missing'} ({report.project_assets_mode})",
        f"Project commands: {'present' if report.project_commands_present else 'missing'}",
        f"Project subagents: {'present' if report.project_agents_present else 'missing'}",
        f"Project skills: {'present' if report.project_skills_present else 'missing'}",
        f"Trusted project required for `.claude/` activation: {'yes' if report.trusted_project_required else 'no'}",
        f"PreToolUse / PostToolUse hooks wired: {'yes' if report.supports_project_hooks else 'no'}",
        f"PostToolUse non-wildcard matcher present: {'yes' if report.supports_post_tool_matchers else 'no'}",
        f"Subagent lifecycle hooks wired: {'yes' if report.supports_subagent_hooks else 'no'}",
        f"PreCompact hook wired: {'yes' if report.supports_pre_compact_hook else 'no'}",
        f"Statusline command wired: {'yes' if report.supports_statusline_command else 'no'}",
        f"Project slash commands present: {'yes' if report.supports_slash_commands else 'no'}",
        f"Version policy: {report.future_version_policy}",
        f"Overall posture: {report.overall_posture}",
        "Notes:",
    ]
    lines.extend(f"- {note}" for note in _report_notes(report))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude compatibility",
        description="Inspect baseline-safe Odylith compatibility with the local Claude Code CLI and project surfaces.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith and Claude inspection.")
    parser.add_argument("--claude-bin", default="claude", help="Claude CLI binary to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit the compatibility report as JSON.")
    parser.add_argument(
        "--skip-version-probe",
        action="store_true",
        help="Skip the live `claude --version` probe and report static capability signals only.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    report = inspect_claude_compatibility(
        args.repo_root,
        claude_bin=args.claude_bin,
        probe_version=not bool(args.skip_version_probe),
    )
    if args.json:
        payload = report.to_dict()
        payload["notes"] = _report_notes(report)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"{render_claude_compatibility(report)}\n")
    return 0 if report.baseline_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
