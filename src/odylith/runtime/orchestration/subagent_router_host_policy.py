"""Host-policy presentation helpers for subagent router decisions."""

from __future__ import annotations

from typing import Any, Mapping


def _claude_project_surface_wired(host_capabilities: Mapping[str, Any]) -> bool:
    return (
        bool(host_capabilities.get("supports_project_hooks"))
        and bool(host_capabilities.get("supports_subagent_hooks"))
        and bool(host_capabilities.get("supports_pre_compact_hook"))
        and bool(host_capabilities.get("supports_statusline_command"))
    )


def project_assets_activation_note(
    *,
    host_runtime: Any,
    host_capabilities: Mapping[str, Any],
) -> str:
    """Return the detailed host project-assets note for a routed contract."""
    runtime = str(host_runtime or "").strip()
    if runtime == "codex_cli":
        if bool(host_capabilities.get("supports_project_hooks")):
            return (
                "Local Codex capability probing reports project hooks support, so the managed `.codex/` lane "
                "remains an active best-effort enhancement alongside the baseline-safe AGENTS.md + launcher contract."
            )
        return (
            "Local Codex capability probing did not prove project hooks support, so keep the baseline-safe "
            "AGENTS.md + launcher lane authoritative and treat `.codex/` assets as optional enhancements until "
            "`odylith codex compatibility` reports otherwise."
        )
    if runtime == "claude_cli":
        if _claude_project_surface_wired(host_capabilities):
            return (
                "Local Claude capability probing reports the first-class `.claude/` project surface is wired "
                "(PreToolUse/PostToolUse, SubagentStart/Stop, PreCompact, statusline). The baked Odylith CLI "
                "dispatchers under `odylith claude ...` are the authoritative hook backends; treat "
                "`.claude/settings.json`, project subagents, slash commands, and skills as live grounding "
                "alongside the baseline-safe CLAUDE.md + launcher contract."
            )
        return (
            "Local Claude capability probing did not prove every first-class `.claude/` hook is wired. Keep the "
            "baseline-safe CLAUDE.md + launcher lane authoritative and run `odylith claude compatibility "
            "--repo-root .` to inspect which Claude hook events are still missing."
        )
    return ""


def host_capability_banner_line(
    *,
    host_runtime: Any,
    host_capabilities: Mapping[str, Any],
) -> str:
    """Return the compact host capability line for runtime banners."""
    runtime = str(host_runtime or "").strip()
    if runtime == "codex_cli":
        if bool(host_capabilities.get("supports_project_hooks")):
            return (
                "HOST CAPABILITY: Codex project hooks are supported locally; the managed `.codex/` lane can stay "
                "active as a best-effort enhancement."
            )
        return (
            "HOST CAPABILITY: Codex project hooks are not proven locally; the baseline-safe AGENTS.md + launcher "
            "lane stays authoritative."
        )
    if runtime == "claude_cli":
        if _claude_project_surface_wired(host_capabilities):
            return (
                "HOST CAPABILITY: Claude first-class `.claude/` hooks are wired locally "
                "(PreToolUse/PostToolUse, SubagentStart/Stop, PreCompact, statusline). The baked "
                "`odylith claude ...` CLI dispatchers are the active hook backends; keep the routed Task payload "
                "tied to that contract."
            )
        return (
            "HOST CAPABILITY: Not all first-class `.claude/` hooks are wired locally. Keep the baseline-safe "
            "CLAUDE.md + launcher lane authoritative and run `odylith claude compatibility --repo-root .` to "
            "surface which hook events are still missing."
        )
    return ""
