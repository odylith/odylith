from __future__ import annotations

import io
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import codex_host_shared
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint
from odylith.runtime.surfaces import host_dirty_checkpoint


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


def test_post_bash_checkpoint_records_dirty_event_without_start(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        calls.append((str(project_dir), args, timeout))
        return None

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n"
                        "*** Begin Patch\n"
                        "*** Update File: src/main.py\n"
                        "@@\n"
                        "-old\n"
                        "+new\n"
                        "*** End Patch\n"
                        "PATCH"
                    },
                    "session_id": "codex-start-cold",
                }
            )
        ),
    )
    monkeypatch.setattr(codex_host_post_bash_checkpoint.codex_host_shared, "run_odylith", _fake_run_odylith)
    _patch_no_governed_changes(monkeypatch)

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == []
    events = host_dirty_checkpoint.read_dirty_events(
        repo_root=tmp_path,
        host_family="codex",
        session_id="codex-start-cold",
    )
    assert [event["paths"] for event in events] == [["src/main.py"]]


def test_post_bash_retains_scoped_governed_event_without_canonical_dispatch(
    monkeypatch, tmp_path: Path
) -> None:
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    target = "odylith/casebook/bugs/current.md"
    unrelated = "odylith/casebook/bugs/other.md"
    for relative in (target, unrelated):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# Recorded issue\n")
    subprocess.run(["git", "add", target, unrelated], cwd=tmp_path, check=True)
    before = {relative: (tmp_path / relative).read_bytes() for relative in (target, unrelated)}
    earlier_id = host_dirty_checkpoint.record_dirty_event(
        repo_root=tmp_path, host_family="codex", session_id="earlier-session",
        source="post_bash_checkpoint", paths=[unrelated], governed_paths=[unrelated],
    )
    monkeypatch.setattr(codex_host_shared, "load_payload", lambda: {
        "session_id": "native-post-bash-session",
        "tool_input": {"command": f"sed -i 's/issue/defect/' {target}"},
    })
    monkeypatch.setattr(codex_host_shared, "run_odylith", lambda **kwargs: (
        _ for _ in ()).throw(AssertionError("PostToolUse must not dispatch canonical work")))

    assert codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)]) == 0

    events = host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path, host_family="codex")
    assert len(events) == 2 and events[0]["id"] == earlier_id
    event = events[1]
    assert event["session_id"] == "native-post-bash-session"
    assert event["source"] == "post_bash_checkpoint"
    assert event["paths"] == event["governed_paths"] == [target]
    assert host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path, host_family="codex") == events
    assert {relative: (tmp_path / relative).read_bytes() for relative in before} == before


def test_post_bash_checkpoint_records_native_apply_patch_payload(monkeypatch, tmp_path: Path) -> None:
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
    assert calls == []
    assert observed_commands
    assert observed_commands[0].startswith("apply_patch <<'PATCH'")
    assert "src/odylith/runtime/intervention_engine/host_surface_runtime.py" in observed_commands[0]
    events = host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path, host_family="codex")
    assert events[0]["paths"] == ["src/odylith/runtime/intervention_engine/host_surface_runtime.py"]


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


def test_post_bash_checkpoint_keeps_pending_chat_replay_off_tool_path(monkeypatch, capsys, tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending checkpoint replay.",
        session_id="codex-post-replay",
        host_family="codex",
        intervention_key="codex-post-replay-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Checkpoint must carry this pending block.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"command": "apply_patch <<'PATCH'"},
                    "session_id": "codex-post-replay",
                }
            )
        ),
    )
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint.codex_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    _patch_no_governed_changes(monkeypatch)
    monkeypatch.setattr(
        codex_host_post_bash_checkpoint,
        "_post_bash_bundle",
        lambda **kwargs: {},
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""


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
    surface_runtime.stream_state.append_intervention_event(
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


def test_main_records_checkpoint_context_with_live_intervention_payload(
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
                    "markdown_text": "**Odylith Observation:** Codex kept the live intervention lane.",
                    "plain_text": "Odylith Observation: Codex kept the live intervention lane.",
                },
                "proposal": {"eligible": False, "suppressed_reason": ""},
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** Deferred checkpoint evidence stayed intact.",
                "plain_text": "Odylith Assist: Deferred checkpoint evidence stayed intact.",
            },
        },
    )

    exit_code = codex_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "**Odylith Observation:** Codex kept the live intervention lane." in payload["systemMessage"]
    assert "Odylith Assist:" not in payload["systemMessage"]
    intervention_events = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="bash-main",
    )
    assert intervention_events
    assert intervention_events[-1]["delivery_status"] == "assistant_render_required"
    assert intervention_events[-1]["delivery_channel"] == "assistant_visible_fallback"
    events = host_dirty_checkpoint.read_dirty_events(
        repo_root=tmp_path,
        host_family="codex",
        session_id="bash-main",
    )
    assert events[0]["paths"] == ["src/main.py"]


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
