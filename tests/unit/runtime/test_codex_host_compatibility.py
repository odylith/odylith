"""Regression coverage for Codex host capability inspection and rendering."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from odylith.runtime.common import codex_cli_capabilities
from odylith.runtime.surfaces import codex_host_compatibility


def _seed_repo(repo_root: Path) -> None:
    """Create the minimum repo-local Codex asset surface needed for tests."""
    (repo_root / "AGENTS.md").write_text("# Repo Guidance\n\nUse Odylith first.\n", encoding="utf-8")
    launcher = repo_root / ".odylith" / "bin"
    launcher.mkdir(parents=True, exist_ok=True)
    (launcher / "odylith").write_text("#!/bin/sh\n", encoding="utf-8")
    codex_root = repo_root / ".codex"
    (codex_root / "agents").mkdir(parents=True, exist_ok=True)
    (codex_root / "config.toml").write_text("project_root_markers = [\".git\"]\n", encoding="utf-8")
    (codex_root / "hooks.json").write_text(
        json.dumps(
            {
                "UserPromptSubmit": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "./.odylith/bin/odylith codex prompt-context --repo-root .",
                            }
                        ]
                    }
                ],
                "PostToolUse": [
                    {
                        "matcher": "Bash",
                        "hooks": [
                            {
                                "type": "command",
                                "command": "./.odylith/bin/odylith codex post-bash-checkpoint --repo-root .",
                            }
                        ],
                    }
                ],
                "Stop": [
                    {
                        "hooks": [
                            {
                                "type": "command",
                                "command": "./.odylith/bin/odylith codex stop-summary --repo-root .",
                            }
                        ]
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    (codex_root / "agents" / "example.toml").write_text("name = \"example\"\n", encoding="utf-8")
    skill_root = repo_root / ".agents" / "skills" / "example"
    skill_root.mkdir(parents=True, exist_ok=True)
    (skill_root / "SKILL.md").write_text("# Skill\n", encoding="utf-8")


def test_parse_feature_flags_handles_multiword_status() -> None:
    parsed = codex_host_compatibility.parse_feature_flags(
        "codex_hooks  under development  true\nmulti_agent  stable  true\n"
    )

    assert parsed["codex_hooks"] == {"stability": "under development", "enabled": True}
    assert parsed["multi_agent"] == {"stability": "stable", "enabled": True}


def test_inspect_codex_compatibility_marks_local_0119_build_assistant_visible_ready(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path)

    def _fake_run(*, repo_root: Path, codex_bin: str, args: list[str], timeout: int = 10):
        del repo_root, codex_bin, timeout
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.119.0-alpha.28\n", stderr="")
        if args == ["features", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex_hooks  under development  true\n", stderr="")
        if args == ["debug", "prompt-input"]:
            return subprocess.CompletedProcess(args, 0, stdout='{"text":"# Repo Guidance"}\n', stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", _fake_run)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    report = codex_host_compatibility.inspect_codex_compatibility(tmp_path)

    assert report.codex_available is True
    assert report.codex_version == "0.119.0-alpha.28"
    assert report.hooks_feature_known is True
    assert report.hooks_feature_enabled is True
    assert report.supports_user_prompt_submit_hook is True
    assert report.supports_post_bash_checkpoint_hook is True
    assert report.supports_stop_summary_hook is True
    assert report.prompt_input_probe_passed is True
    assert report.repo_guidance_detected is True
    assert report.overall_posture == "baseline_safe_assistant_visible_ready"


def test_inspect_codex_compatibility_does_not_call_repo_guidance_probe_hook_visibility(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    (tmp_path / ".codex" / "hooks.json").write_text("{}", encoding="utf-8")

    def _fake_run(*, repo_root: Path, codex_bin: str, args: list[str], timeout: int = 10):
        del repo_root, codex_bin, timeout
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.119.0-alpha.28\n", stderr="")
        if args == ["features", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex_hooks  under development  true\n", stderr="")
        if args == ["debug", "prompt-input"]:
            return subprocess.CompletedProcess(args, 0, stdout='{"text":"# Repo Guidance"}\n', stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", _fake_run)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    report = codex_host_compatibility.inspect_codex_compatibility(tmp_path)
    rendered = codex_host_compatibility.render_codex_compatibility(report)

    assert report.prompt_input_probe_passed is True
    assert report.repo_guidance_detected is True
    assert report.supports_user_prompt_submit_hook is False
    assert report.supports_post_bash_checkpoint_hook is False
    assert report.supports_stop_summary_hook is False
    assert report.overall_posture == "baseline_safe_with_best_effort_project_assets"
    assert "hook wiring is incomplete" in rendered
    assert "separate visibility proof" in rendered


def test_inspect_codex_compatibility_accepts_bash_only_checkpoint_matcher(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)
    payload = json.loads((tmp_path / ".codex" / "hooks.json").read_text(encoding="utf-8"))
    payload["PostToolUse"][0]["matcher"] = "Bash"
    (tmp_path / ".codex" / "hooks.json").write_text(json.dumps(payload), encoding="utf-8")

    def _fake_run(*, repo_root: Path, codex_bin: str, args: list[str], timeout: int = 10):
        del repo_root, codex_bin, timeout
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.119.0-alpha.28\n", stderr="")
        if args == ["features", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex_hooks  under development  true\n", stderr="")
        if args == ["debug", "prompt-input"]:
            return subprocess.CompletedProcess(args, 0, stdout='{"text":"# Repo Guidance"}\n', stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", _fake_run)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    report = codex_host_compatibility.inspect_codex_compatibility(tmp_path)
    rendered = codex_host_compatibility.render_codex_compatibility(report)

    assert report.supports_user_prompt_submit_hook is True
    assert report.supports_post_bash_checkpoint_hook is True
    assert report.supports_stop_summary_hook is True
    assert report.overall_posture == "baseline_safe_assistant_visible_ready"
    assert "PostToolUse post-bash-checkpoint hook wired for Bash: yes" in rendered
    assert "assistant-render fallback" in rendered
    assert "may not hot-reload changed hooks" in rendered


def test_inspect_codex_compatibility_marks_assistant_visible_ready_without_prompt_probe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    _seed_repo(tmp_path)

    def _fake_run(*, repo_root: Path, codex_bin: str, args: list[str], timeout: int = 10):
        del repo_root, codex_bin, timeout
        if args == ["--version"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex-cli 0.119.0-alpha.28\n", stderr="")
        if args == ["features", "list"]:
            return subprocess.CompletedProcess(args, 0, stdout="codex_hooks  under development  true\n", stderr="")
        raise AssertionError(args)

    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", _fake_run)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    report = codex_host_compatibility.inspect_codex_compatibility(tmp_path, probe_prompt_input=False)

    assert report.prompt_input_probe_supported is False
    assert report.prompt_input_probe_passed is False
    assert report.repo_guidance_detected is False
    assert report.overall_posture == "baseline_safe_assistant_visible_ready"


def test_inspect_codex_compatibility_stays_baseline_safe_when_codex_is_missing(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(codex_cli_capabilities, "_run_codex_command", lambda **_: None)
    codex_cli_capabilities.clear_codex_cli_capability_cache()

    report = codex_host_compatibility.inspect_codex_compatibility(tmp_path)

    assert report.baseline_ready is True
    assert report.codex_available is False
    assert report.prompt_input_probe_supported is False
    assert report.overall_posture == "baseline_safe"


def test_render_effective_codex_project_config_omits_hooks_when_not_supported(monkeypatch, tmp_path: Path) -> None:
    _seed_repo(tmp_path)
    monkeypatch.setattr(
        codex_cli_capabilities,
        "inspect_codex_cli_capabilities",
        lambda *args, **kwargs: codex_cli_capabilities.CodexCliCapabilitySnapshot(
            repo_root=str(tmp_path),
            codex_bin="codex",
            codex_available=False,
            codex_version_raw="",
            codex_version="",
            baseline_contract="AGENTS.md + ./.odylith/bin/odylith",
            baseline_ready=True,
            launcher_present=True,
            repo_agents_present=True,
            codex_project_assets_present=True,
            codex_skill_shims_present=True,
            project_assets_mode="best_effort_enhancements",
            trusted_project_required=True,
            hooks_feature_known=False,
            hooks_feature_enabled=None,
            supports_user_prompt_submit_hook=False,
            supports_post_bash_checkpoint_hook=False,
            supports_stop_summary_hook=False,
            prompt_input_probe_supported=False,
            prompt_input_probe_passed=False,
            repo_guidance_detected=False,
            future_version_policy="capability_based_no_max_pin",
            overall_posture="baseline_safe",
        ),
    )

    rendered = codex_cli_capabilities.render_effective_codex_project_config(repo_root=tmp_path)

    assert "[features]" not in rendered
    assert "codex_hooks" not in rendered


def test_main_emits_json_report(monkeypatch, tmp_path: Path, capsys) -> None:
    _seed_repo(tmp_path)

    monkeypatch.setattr(
        codex_host_compatibility,
        "inspect_codex_compatibility",
        lambda *args, **kwargs: codex_host_compatibility.CodexCompatibilityReport(
            repo_root=str(tmp_path),
            codex_bin="codex",
            codex_available=True,
            codex_version_raw="codex-cli 0.119.0-alpha.28",
            codex_version="0.119.0-alpha.28",
            baseline_contract="AGENTS.md + ./.odylith/bin/odylith",
            baseline_ready=True,
            launcher_present=True,
            repo_agents_present=True,
            codex_project_assets_present=True,
            codex_skill_shims_present=True,
            project_assets_mode="best_effort_enhancements",
            trusted_project_required=True,
            hooks_feature_known=True,
            hooks_feature_enabled=True,
            supports_user_prompt_submit_hook=True,
            supports_post_bash_checkpoint_hook=True,
            supports_stop_summary_hook=True,
            prompt_input_probe_supported=True,
            prompt_input_probe_passed=True,
            repo_guidance_detected=True,
            future_version_policy="capability_based_no_max_pin",
            overall_posture="baseline_safe_assistant_visible_ready",
        ),
    )

    exit_code = codex_host_compatibility.main(["--repo-root", str(tmp_path), "--json"])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["codex_version"] == "0.119.0-alpha.28"
    assert payload["overall_posture"] == "baseline_safe_assistant_visible_ready"
    assert payload["supports_user_prompt_submit_hook"] is True
    assert payload["supports_post_bash_checkpoint_hook"] is True
    assert payload["supports_stop_summary_hook"] is True
