"""Capability-based Codex compatibility reporting for Odylith."""

from __future__ import annotations

import argparse
import json
import sys

from odylith.runtime.common import codex_cli_capabilities


CodexCompatibilityReport = codex_cli_capabilities.CodexCliCapabilitySnapshot
inspect_codex_compatibility = codex_cli_capabilities.inspect_codex_cli_capabilities
parse_codex_version = codex_cli_capabilities.parse_codex_version
parse_feature_flags = codex_cli_capabilities.parse_feature_flags
_run_codex_command = codex_cli_capabilities._run_codex_command  # noqa: SLF001


def _report_notes(report: CodexCompatibilityReport) -> list[str]:
    notes = [
        "Core Odylith support on Codex is the repo-root AGENTS.md contract plus `./.odylith/bin/odylith`.",
        "Repo-scoped `.codex/` and `.agents/skills/` surfaces are best-effort enhancements and must not be required for core operation.",
        "Trusted-project approval is required before `.codex/hooks.json` and `.codex/agents/*.toml` activate in Codex.",
        "Existing Codex sessions may not hot-reload changed hooks, guidance, or source-local runtime code; restart the session or render `odylith codex visible-intervention` directly before claiming another open chat is visibly active.",
        "Version compatibility is capability-based and does not pin a maximum Codex version.",
    ]
    if report.codex_available and report.codex_version:
        notes.append(f"Local Codex CLI detected: `codex-cli {report.codex_version}`.")
    elif not report.codex_available:
        notes.append("Local Codex CLI was not detected on PATH during this compatibility check.")
    if report.hooks_feature_known:
        notes.append(
            "Local feature registry reports `features.codex_hooks = "
            + ("true`." if report.hooks_feature_enabled else "false`.")
        )
    else:
        notes.append("Local feature registry did not expose a trusted `codex_hooks` capability signal.")
    if (
        report.supports_user_prompt_submit_hook
        and report.supports_post_bash_checkpoint_hook
        and report.supports_stop_summary_hook
    ):
        notes.append(
            "Codex intervention hooks are wired for prompt teaser, Bash checkpoint Observation/Proposal, and Stop closeout sources."
        )
        notes.append(
            "Chat visibility is completed by the assistant-render fallback inside `additionalContext`; hook `systemMessage` alone is not treated as a visible-chat proof."
        )
    else:
        missing = []
        if not report.supports_user_prompt_submit_hook:
            missing.append("UserPromptSubmit prompt-context")
        if not report.supports_post_bash_checkpoint_hook:
            missing.append("PostToolUse post-bash-checkpoint with Bash matcher coverage")
        if not report.supports_stop_summary_hook:
            missing.append("Stop stop-summary")
        notes.append("Codex intervention hook wiring is incomplete: missing " + ", ".join(missing) + ".")
    if report.prompt_input_probe_passed and report.repo_guidance_detected:
        notes.append(
            "A live `codex debug prompt-input` probe succeeded and included the repo-root AGENTS contract; hook wiring above is the separate visibility proof for intervention output."
        )
    elif report.prompt_input_probe_passed:
        notes.append("A live `codex debug prompt-input` probe succeeded, but the repo-root AGENTS token was not detected verbatim.")
    elif report.prompt_input_probe_supported:
        notes.append("A live `codex debug prompt-input` probe is available locally but did not pass in this run.")
    else:
        notes.append("A live `codex debug prompt-input` probe was not available from the detected Codex build.")
    return notes


def render_codex_compatibility(report: CodexCompatibilityReport) -> str:
    hooks_label = (
        "enabled"
        if report.hooks_feature_enabled is True
        else "disabled" if report.hooks_feature_enabled is False else "unknown"
    )
    probe_label = (
        "passed with repo guidance detected"
        if report.prompt_input_probe_passed and report.repo_guidance_detected
        else "passed"
        if report.prompt_input_probe_passed
        else "not available"
        if not report.prompt_input_probe_supported
        else "did not pass"
    )
    lines = [
        "Codex compatibility report",
        f"Baseline contract: {report.baseline_contract}",
        f"Baseline ready: {'yes' if report.baseline_ready else 'no'}",
        f"Codex CLI: {report.codex_version_raw or 'not detected on PATH'}",
        f"Project assets: {'present' if report.codex_project_assets_present else 'missing'} ({report.project_assets_mode})",
        f"Skill shims: {'present' if report.codex_skill_shims_present else 'missing'}",
        f"Trusted project required for `.codex/` activation: {'yes' if report.trusted_project_required else 'no'}",
        f"Hooks feature: {hooks_label}",
        f"UserPromptSubmit prompt-context hook wired: {'yes' if report.supports_user_prompt_submit_hook else 'no'}",
        f"PostToolUse post-bash-checkpoint hook wired for Bash: {'yes' if report.supports_post_bash_checkpoint_hook else 'no'}",
        f"Stop stop-summary hook wired: {'yes' if report.supports_stop_summary_hook else 'no'}",
        "Assistant-render fallback for chat-visible UX: yes",
        f"Live prompt-input probe: {probe_label}",
        f"Version policy: {report.future_version_policy}",
        f"Overall posture: {report.overall_posture}",
        "Notes:",
    ]
    lines.extend(f"- {note}" for note in _report_notes(report))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex compatibility",
        description="Inspect baseline-safe Odylith compatibility with the local Codex CLI.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith and Codex inspection.")
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI binary to inspect.")
    parser.add_argument("--json", action="store_true", help="Emit the compatibility report as JSON.")
    parser.add_argument(
        "--skip-prompt-input-probe",
        action="store_true",
        help="Skip the live `codex debug prompt-input` probe and report static capability signals only.",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    report = inspect_codex_compatibility(
        args.repo_root,
        codex_bin=args.codex_bin,
        probe_prompt_input=not bool(args.skip_prompt_input_probe),
    )
    if args.json:
        payload = report.to_dict()
        payload["notes"] = _report_notes(report)
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    else:
        sys.stdout.write(f"{render_codex_compatibility(report)}\n")
    return 0 if report.baseline_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
