from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint


def _patch_stdin(monkeypatch, command: str) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": command}})),
    )


def _patch_no_governed_changes(monkeypatch) -> None:
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda *, project_dir, command: [],
    )


def test_post_bash_checkpoint_runs_start_for_edit_like_commands(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        calls.append((str(project_dir), args, timeout))
        return None

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"command": "apply_patch <<'PATCH'"},
                    "session_id": "codex-start-cold",
                }
            )
        ),
    )
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    _patch_no_governed_changes(monkeypatch)

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == [(str(tmp_path), ["start", "--repo-root", "."], 20)]


def test_post_bash_checkpoint_skips_start_when_cache_is_warm(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []
    session_id = "codex-start-warm"

    codex_host_post_bash_checkpoint.record_start_grounding_attempt(
        project_dir=tmp_path,
        session_id=session_id,
        completed=subprocess.CompletedProcess(args=["odylith", "start"], returncode=1),
        now_seconds=1000.0,
    )
    monkeypatch.setattr(codex_host_post_bash_checkpoint.time, "time", lambda: 1010.0)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_input": {"command": "apply_patch <<'PATCH'"}, "session_id": session_id})),
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: calls.append((str(kwargs["project_dir"]), kwargs["args"], kwargs["timeout"])),
    )
    _patch_no_governed_changes(monkeypatch)

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == []


def test_start_grounding_cache_collapses_process_fallback_sessions(tmp_path: Path) -> None:
    codex_host_post_bash_checkpoint.record_start_grounding_attempt(
        project_dir=tmp_path,
        session_id="agent-111",
        completed=subprocess.CompletedProcess(args=["odylith", "start"], returncode=1),
        now_seconds=1000.0,
    )

    assert not codex_host_post_bash_checkpoint.should_run_start_grounding(
        project_dir=tmp_path,
        session_id="agent-222",
        now_seconds=1010.0,
    )


def test_start_grounding_cache_expires(tmp_path: Path) -> None:
    codex_host_post_bash_checkpoint.record_start_grounding_attempt(
        project_dir=tmp_path,
        session_id="codex-start-stale",
        completed=subprocess.CompletedProcess(args=["odylith", "start"], returncode=0),
        now_seconds=1000.0,
    )

    assert codex_host_post_bash_checkpoint.should_run_start_grounding(
        project_dir=tmp_path,
        session_id="codex-start-stale",
        now_seconds=1000.0 + codex_host_post_bash_checkpoint._START_GROUND_CACHE_TTL_SECONDS + 1,
    )


def test_post_bash_checkpoint_runs_start_for_native_apply_patch_payload(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []
    observed_commands: list[str] = []
    patch = (
        "*** Begin Patch\n"
        "*** Update File: src/odylith/runtime/intervention_engine/host_surface_runtime.py\n"
        "@@\n"
        "-old\n"
        "+new\n"
        "*** End Patch\n"
    )

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"tool_name": "apply_patch", "tool_input": {"patch": patch}})),
    )

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        calls.append((str(project_dir), args, timeout))
        return None

    def _fake_command_scoped_governed_paths(*, project_dir, command):
        del project_dir
        observed_commands.append(command)
        return []

    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        _fake_command_scoped_governed_paths,
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == [(str(tmp_path), ["start", "--repo-root", "."], 20)]
    assert observed_commands
    assert observed_commands[0].startswith("apply_patch <<'PATCH'")
    assert "src/odylith/runtime/intervention_engine/host_surface_runtime.py" in observed_commands[0]


def test_post_bash_checkpoint_skips_non_edit_like_commands(monkeypatch) -> None:
    calls: list[tuple[str, list[str], int]] = []

    _patch_stdin(monkeypatch, "pytest -q")
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: calls.append((str(kwargs["project_dir"]), kwargs["args"], kwargs["timeout"])),
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", "/tmp/repo"])

    assert exit_code == 0
    assert calls == []


def test_codex_command_from_hook_payload_supports_exec_command_cmd() -> None:
    payload = {"tool_name": "exec_command", "tool_input": {"cmd": "python3 -c 'open(\"src/foo.py\", \"w\").write(\"x\")'"}}

    assert codex_host_shared.command_from_hook_payload(payload) == payload["tool_input"]["cmd"]


def test_codex_command_from_hook_payload_supports_arguments_json() -> None:
    payload = {
        "tool_name": "exec_command",
        "arguments": json.dumps({"cmd": "python3 -c 'open(\"src/foo.py\", \"w\").write(\"x\")'"}),
    }

    assert codex_host_shared.command_from_hook_payload(payload) == json.loads(payload["arguments"])["cmd"]


def test_post_bash_checkpoint_runs_selective_sync_when_governed_paths_change(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        calls.append((str(project_dir), list(args), timeout))
        if args and args[0] == "sync":
            return SimpleNamespace(returncode=0, stdout="", stderr="")
        return None

    _patch_stdin(monkeypatch, "apply_patch <<'PATCH'")
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda *, project_dir, command: [
            "odylith/casebook/bugs/2026-04-14-example.md",
            "odylith/radar/source/INDEX.md",
        ],
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    assert len(calls) == 2
    assert calls[0][1] == ["start", "--repo-root", "."]
    sync_project_dir, sync_args, sync_timeout = calls[1]
    assert sync_args[0:2] == ["sync", "--repo-root"]
    assert sync_args[3:5] == ["--impact-mode", "selective"]
    assert sync_args[5:] == [
        "odylith/casebook/bugs/2026-04-14-example.md",
        "odylith/radar/source/INDEX.md",
    ]
    assert sync_timeout == 180

    payload = json.loads(out)
    assert "systemMessage" in payload
    assert "completed" in payload["systemMessage"]
    assert "odylith/casebook/bugs/2026-04-14-example.md" in payload["systemMessage"]


def test_post_bash_checkpoint_emits_failure_message_on_selective_sync_error(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    def _fake_run_odylith(*, project_dir, args, timeout=20):
        if args and args[0] == "sync":
            return SimpleNamespace(returncode=2, stdout="", stderr="validate failure\n")
        return None

    _patch_stdin(monkeypatch, "apply_patch <<'PATCH'")
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda *, project_dir, command: ["odylith/casebook/bugs/2026-04-14-example.md"],
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    # Fail-soft: exits 0 even when sync fails, emits systemMessage describing failure.
    assert exit_code == 0
    payload = json.loads(out)
    assert "failed" in payload["systemMessage"]
    assert "validate failure" in payload["systemMessage"]


def test_post_bash_checkpoint_emits_skipped_message_when_launcher_unavailable(
    monkeypatch, capsys, tmp_path: Path
) -> None:
    def _fake_run_odylith(*, project_dir, args, timeout=20):
        return None  # Launcher not available.

    _patch_stdin(monkeypatch, "sed -i 's/foo/bar/g' odylith/casebook/bugs/foo.md")
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda *, project_dir, command: ["odylith/casebook/bugs/foo.md"],
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])
    out = capsys.readouterr().out

    assert exit_code == 0
    payload = json.loads(out)
    assert "skipped" in payload["systemMessage"]


def test_governed_changed_paths_parses_porcelain_z_output(monkeypatch, tmp_path: Path) -> None:
    # Simulate git status --porcelain -z output with a mix of:
    # - modified governed bug markdown (should match)
    # - modified guidance companion AGENTS.md (should be filtered out)
    # - untracked governed plan markdown (should match)
    # - modified non-governed source file (should be filtered out)
    # - a rename with an old-path trailing record that must be skipped
    porcelain_z = (
        " M odylith/casebook/bugs/foo.md\x00"
        " M odylith/radar/source/AGENTS.md\x00"
        "?? odylith/technical-plans/in-progress/2026-04/new-plan.md\x00"
        " M src/odylith/cli.py\x00"
        "R  odylith/casebook/bugs/new-name.md\x00"
        "odylith/casebook/bugs/old-name.md\x00"
    )

    def _fake_subprocess_run(args, **kwargs):
        assert args == ["git", "status", "--porcelain", "-z"]
        return SimpleNamespace(returncode=0, stdout=porcelain_z, stderr="")

    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.subprocess,
        "run",
        _fake_subprocess_run,
    )

    paths = codex_host_post_bash_checkpoint.governed_changed_paths(project_dir=tmp_path)

    assert paths == [
        "odylith/casebook/bugs/foo.md",
        "odylith/technical-plans/in-progress/2026-04/new-plan.md",
        "odylith/casebook/bugs/new-name.md",
        "odylith/casebook/bugs/old-name.md",
    ]


def test_governed_changed_paths_fails_soft_on_git_error(monkeypatch, tmp_path: Path) -> None:
    def _fake_subprocess_run(args, **kwargs):
        raise subprocess.SubprocessError("git not available")

    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.subprocess,
        "run",
        _fake_subprocess_run,
    )

    paths = codex_host_post_bash_checkpoint.governed_changed_paths(project_dir=tmp_path)
    assert paths == []


def test_governed_changed_paths_fails_soft_on_nonzero_git_returncode(
    monkeypatch, tmp_path: Path
) -> None:
    def _fake_subprocess_run(args, **kwargs):
        return SimpleNamespace(returncode=128, stdout="", stderr="fatal: not a git repo")

    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.subprocess,
        "run",
        _fake_subprocess_run,
    )

    paths = codex_host_post_bash_checkpoint.governed_changed_paths(project_dir=tmp_path)
    assert paths == []


def test_governed_changed_paths_keeps_old_governed_path_for_rename_out_of_truth(
    monkeypatch, tmp_path: Path
) -> None:
    porcelain_z = "R  docs/foo.md\x00odylith/casebook/bugs/foo.md\x00"

    def _fake_subprocess_run(args, **kwargs):
        assert args == ["git", "status", "--porcelain", "-z"]
        return SimpleNamespace(returncode=0, stdout=porcelain_z, stderr="")

    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.subprocess,
        "run",
        _fake_subprocess_run,
    )

    paths = codex_host_post_bash_checkpoint.governed_changed_paths(project_dir=tmp_path)

    assert paths == ["odylith/casebook/bugs/foo.md"]


def test_command_scoped_governed_paths_intersects_dirty_set_with_command_targets(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "dirty_governed_paths",
        lambda *, project_dir: [
            "odylith/casebook/bugs/2026-04-14-example.md",
            "odylith/radar/source/INDEX.md",
        ],
    )

    command = """apply_patch <<'PATCH'
*** Begin Patch
*** Update File: odylith/casebook/bugs/2026-04-14-example.md
@@
-old
+new
*** End Patch
PATCH"""

    paths = codex_host_post_bash_checkpoint.command_scoped_governed_paths(
        project_dir=tmp_path,
        command=command,
    )

    assert paths == ["odylith/casebook/bugs/2026-04-14-example.md"]


def test_post_bash_bundle_uses_recent_prompt_excerpt_not_intervention_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    codex_host_post_bash_checkpoint.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="bash-1",
        host_family="codex",
        intervention_key="iv-bash-1",
        turn_phase="post_edit_checkpoint",
        prompt_excerpt="Preserve the human prompt across bash checkpoints.",
        display_markdown="**Odylith Proposal**",
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "inferred_command_paths",
        lambda *, project_dir, command: ["src/odylith/runtime/intervention_engine/engine.py"],
    )

    bundle = codex_host_post_bash_checkpoint._post_bash_bundle(
        project_dir=tmp_path,
        command="apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/odylith/runtime/intervention_engine/engine.py\n@@\n-old\n+new\n*** End Patch\nPATCH",
        session_id="bash-1",
    )

    assert bundle["observation"]["prompt_excerpt"] == "Preserve the human prompt across bash checkpoints."


def test_main_routes_checkpoint_context_through_additional_context(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "load_payload",
        lambda: {
            "tool_input": {
                "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
            },
            "session_id": "bash-main",
        },
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "should_checkpoint",
        lambda command: True,
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "_post_bash_bundle",
        lambda **kwargs: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "card",
                    "suppressed_reason": "",
                    "markdown_text": "**Odylith Observation:** The signal is real.",
                    "plain_text": "Odylith Observation: The signal is real.",
                },
                "proposal": {
                    "eligible": True,
                    "suppressed_reason": "",
                    "markdown_text": 'Odylith Proposal: Odylith is proposing one clean governed bundle for this moment.\n\nTo apply, say "apply this proposal".',
                    "plain_text": "Odylith Proposal: one clean governed bundle.",
                },
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "**Odylith Observation:** The signal is real." in payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith Proposal:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Assist:** kept this grounded." in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Observation:** The signal is real." in payload["systemMessage"]
    assert "Odylith Proposal:" in payload["systemMessage"]
    assert "Odylith Assist:" not in payload["systemMessage"]


def test_command_scoped_governed_paths_skips_repo_wide_dirty_files_when_command_lacks_exact_target(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "dirty_governed_paths",
        lambda *, project_dir: [
            "odylith/casebook/bugs/2026-04-14-example.md",
            "odylith/radar/source/INDEX.md",
        ],
    )

    paths = codex_host_post_bash_checkpoint.command_scoped_governed_paths(
        project_dir=tmp_path,
        command="python -c \"from pathlib import Path; Path('src/odylith/cli.py').write_text('x')\"",
    )

    assert paths == []


def test_inferred_command_paths_ignores_shell_tail_after_copy(tmp_path: Path) -> None:
    paths = codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=tmp_path,
        command="cp src/a.py odylith/radar/source/INDEX.md && echo done",
    )

    assert paths == ["odylith/radar/source/INDEX.md"]


def test_inferred_command_paths_ignores_redirection_tail_after_sed(tmp_path: Path) -> None:
    paths = codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=tmp_path,
        command="sed -i 's/a/b/' odylith/casebook/bugs/foo.md >/dev/null",
    )

    assert paths == ["odylith/casebook/bugs/foo.md"]


def test_command_scoped_governed_paths_refreshes_move_out_of_governed_truth(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "dirty_governed_paths",
        lambda *, project_dir: ["odylith/casebook/bugs/foo.md"],
    )

    paths = codex_host_post_bash_checkpoint.command_scoped_governed_paths(
        project_dir=tmp_path,
        command="mv odylith/casebook/bugs/foo.md docs/foo.md",
    )

    assert paths == ["odylith/casebook/bugs/foo.md"]


def test_inferred_command_paths_detects_python_inline_write_target(tmp_path: Path) -> None:
    paths = codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=tmp_path,
        command=(
            "python -c \"from pathlib import Path; "
            "Path('odylith/casebook/bugs/foo.md').write_text('x')\""
        ),
    )

    assert paths == ["odylith/casebook/bugs/foo.md"]


def test_inferred_command_paths_detects_node_inline_write_target(tmp_path: Path) -> None:
    paths = codex_host_post_bash_checkpoint.inferred_command_paths(
        project_dir=tmp_path,
        command="node -e \"require('fs').writeFileSync('odylith/radar/source/INDEX.md', 'x')\"",
    )

    assert paths == ["odylith/radar/source/INDEX.md"]
