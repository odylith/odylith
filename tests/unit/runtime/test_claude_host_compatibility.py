from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.common import claude_cli_capabilities
from odylith.runtime.surfaces import claude_host_compatibility


def _seed_repo(repo_root: Path) -> None:
    (repo_root / "CLAUDE.md").write_text("# Repo memory\n", encoding="utf-8")
    (repo_root / "AGENTS.md").write_text("# Repo guidance\n", encoding="utf-8")
    launcher_dir = repo_root / ".odylith" / "bin"
    launcher_dir.mkdir(parents=True, exist_ok=True)
    (launcher_dir / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    (repo_root / ".claude" / "commands").mkdir(parents=True, exist_ok=True)
    (repo_root / ".claude" / "commands" / "odylith-start.md").write_text("---\n", encoding="utf-8")


def _make_snapshot(
    *,
    tmp_path: Path,
    claude_available: bool = True,
    project_settings_present: bool = True,
    supports_project_hooks: bool = True,
    supports_subagent_hooks: bool = True,
    supports_pre_compact_hook: bool = True,
    supports_statusline_command: bool = True,
    supports_prompt_context_hook: bool = True,
    supports_prompt_teaser_hook: bool = True,
    supports_post_edit_checkpoint_hook: bool = True,
    supports_post_bash_checkpoint_hook: bool = True,
    supports_stop_summary_hook: bool = True,
    supports_post_tool_matchers: bool = True,
    supports_slash_commands: bool = True,
    overall_posture: str = "baseline_safe_assistant_visible_ready",
    baseline_ready: bool = True,
) -> claude_cli_capabilities.ClaudeCliCapabilitySnapshot:
    return claude_cli_capabilities.ClaudeCliCapabilitySnapshot(
        repo_root=str(tmp_path),
        claude_bin="claude",
        claude_available=claude_available,
        claude_version_raw="claude 1.0.30" if claude_available else "",
        claude_version="1.0.30" if claude_available else "",
        baseline_contract="CLAUDE.md + ./.odylith/bin/odylith",
        baseline_ready=baseline_ready,
        launcher_present=True,
        repo_claude_md_present=True,
        repo_agents_md_present=True,
        project_settings_present=project_settings_present,
        project_commands_present=True,
        project_agents_present=True,
        project_skills_present=True,
        project_assets_mode="first_class_project_surface",
        trusted_project_required=False,
        supports_project_hooks=supports_project_hooks,
        supports_subagent_hooks=supports_subagent_hooks,
        supports_pre_compact_hook=supports_pre_compact_hook,
        supports_statusline_command=supports_statusline_command,
        supports_prompt_context_hook=supports_prompt_context_hook,
        supports_prompt_teaser_hook=supports_prompt_teaser_hook,
        supports_post_edit_checkpoint_hook=supports_post_edit_checkpoint_hook,
        supports_post_bash_checkpoint_hook=supports_post_bash_checkpoint_hook,
        supports_stop_summary_hook=supports_stop_summary_hook,
        supports_post_tool_matchers=supports_post_tool_matchers,
        supports_slash_commands=supports_slash_commands,
        future_version_policy="capability_based_no_max_pin",
        overall_posture=overall_posture,
    )


def test_render_claude_compatibility_includes_capability_truth(tmp_path: Path) -> None:
    snapshot = _make_snapshot(tmp_path=tmp_path)
    rendered = claude_host_compatibility.render_claude_compatibility(snapshot)

    assert "Claude Code compatibility report" in rendered
    assert "Baseline contract: CLAUDE.md + ./.odylith/bin/odylith" in rendered
    assert "Claude CLI: claude 1.0.30" in rendered
    assert "Trusted project required for `.claude/` activation: no" in rendered
    assert "PreToolUse / PostToolUse hooks wired: yes" in rendered
    assert "UserPromptSubmit prompt-context hook wired: yes" in rendered
    assert "UserPromptSubmit prompt-teaser hook wired: yes" in rendered
    assert "PostToolUse post-edit-checkpoint hook wired for Write/Edit/MultiEdit: yes" in rendered
    assert "PostToolUse post-bash-checkpoint hook wired for Bash: yes" in rendered
    assert "Stop stop-summary hook wired: yes" in rendered
    assert "PreCompact hook wired: yes" in rendered
    assert "Statusline command wired: yes" in rendered
    assert "Subagent lifecycle hooks wired: yes" in rendered
    assert "Project slash commands present: yes" in rendered
    assert "Assistant-render fallback for chat-visible UX: yes" in rendered
    assert "Overall posture: baseline_safe_assistant_visible_ready" in rendered
    assert "may not hot-reload changed project settings" in rendered


def test_render_claude_compatibility_degrades_to_baseline_safe_when_claude_missing(tmp_path: Path) -> None:
    snapshot = _make_snapshot(
        tmp_path=tmp_path,
        claude_available=False,
        project_settings_present=False,
        supports_project_hooks=False,
        supports_subagent_hooks=False,
        supports_pre_compact_hook=False,
        supports_statusline_command=False,
        supports_prompt_context_hook=False,
        supports_prompt_teaser_hook=False,
        supports_post_edit_checkpoint_hook=False,
        supports_post_bash_checkpoint_hook=False,
        supports_stop_summary_hook=False,
        supports_post_tool_matchers=False,
        overall_posture="baseline_safe",
    )
    rendered = claude_host_compatibility.render_claude_compatibility(snapshot)

    assert "Claude CLI: not detected on PATH" in rendered
    assert "PreToolUse / PostToolUse hooks wired: no" in rendered
    assert "UserPromptSubmit prompt-context hook wired: no" in rendered
    assert "UserPromptSubmit prompt-teaser hook wired: no" in rendered
    assert "Overall posture: baseline_safe" in rendered


def test_main_emits_human_readable_report_when_baseline_ready(monkeypatch, tmp_path: Path, capsys) -> None:
    _seed_repo(tmp_path)
    snapshot = _make_snapshot(tmp_path=tmp_path)
    monkeypatch.setattr(
        claude_host_compatibility,
        "inspect_claude_compatibility",
        lambda *args, **kwargs: snapshot,
    )

    exit_code = claude_host_compatibility.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    captured = capsys.readouterr().out
    assert "Claude Code compatibility report" in captured
    assert "Overall posture: baseline_safe_assistant_visible_ready" in captured


def test_main_emits_json_payload_with_notes(monkeypatch, tmp_path: Path, capsys) -> None:
    _seed_repo(tmp_path)
    snapshot = _make_snapshot(tmp_path=tmp_path)
    monkeypatch.setattr(
        claude_host_compatibility,
        "inspect_claude_compatibility",
        lambda *args, **kwargs: snapshot,
    )

    exit_code = claude_host_compatibility.main(
        ["--repo-root", str(tmp_path), "--json", "--skip-version-probe"]
    )

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["claude_version"] == "1.0.30"
    assert payload["overall_posture"] == "baseline_safe_assistant_visible_ready"
    assert payload["trusted_project_required"] is False
    assert isinstance(payload["notes"], list)
    assert any("first-class project surfaces" in note for note in payload["notes"])


def test_main_returns_nonzero_when_baseline_not_ready(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    snapshot = _make_snapshot(tmp_path=tmp_path, baseline_ready=False, overall_posture="baseline_incomplete")
    monkeypatch.setattr(
        claude_host_compatibility,
        "inspect_claude_compatibility",
        lambda *args, **kwargs: snapshot,
    )

    exit_code = claude_host_compatibility.main(["--repo-root", str(tmp_path)])

    assert exit_code == 1
