from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
HOOKS_ROOT = ROOT / ".claude" / "hooks"


def _write_fake_launcher(repo_root: Path, call_log: Path) -> None:
    launcher = repo_root / ".odylith" / "bin" / "odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    launcher.write_text(
        "\n".join(
            [
                "#!/usr/bin/env python3",
                "from __future__ import annotations",
                "",
                "import json",
                "import os",
                "from pathlib import Path",
                "import sys",
                "",
                "log_path = Path(os.environ['ODYLITH_HOOK_CALLS'])",
                "log_path.parent.mkdir(parents=True, exist_ok=True)",
                "with log_path.open('a', encoding='utf-8') as handle:",
                "    handle.write(json.dumps({'argv': sys.argv[1:]}, sort_keys=True) + '\\n')",
                "args = sys.argv[1:]",
                "if args[:1] == ['start']:",
                "    print('Odylith ready for this repo.')",
                "    print(json.dumps({'selection_reason': 'focused on B-083', 'relevant_docs': ['odylith/CLAUDE.md'], 'recommended_commands': ['./.odylith/bin/odylith context --repo-root . B-083']}))",
                "elif args[:2] == ['compass', 'log']:",
                "    print('logged')",
                "else:",
                "    print('{}')",
                "raise SystemExit(0)",
                "",
            ]
        ),
        encoding="utf-8",
    )
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR)


def _write_current_snapshot(repo_root: Path) -> None:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-04-11T12:00:00Z",
                "execution_focus": {
                    "global": {
                        "headline": "Claude hardening is live for B-083",
                        "workstreams": ["B-083", "B-071"],
                    }
                },
                "current_workstreams": [
                    {"idea_id": "B-083", "title": "Claude support hardening"},
                    {"idea_id": "B-071", "title": "Scope signal ladder"},
                ],
                "verified_scoped_workstreams": {"24h": ["B-083", "B-071"]},
                "next_actions": [
                    {"idea_id": "B-083", "action": "Finish hooks and memory bridge"},
                    {"idea_id": "B-071", "action": "Keep scope signal deterministic"},
                ],
                "risks": {"traceability_warnings": ["B-083 traceability needs a clean sync pass."]},
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _run_hook(script_name: str, repo_root: Path, *, payload: dict[str, object] | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    return subprocess.run(
        [sys.executable, str(HOOKS_ROOT / script_name), str(repo_root)],
        cwd=str(repo_root),
        input=json.dumps(payload or {}),
        capture_output=True,
        text=True,
        check=False,
        env=merged_env,
    )


def test_show_me_prompt_guard_routes_first_demo_without_launcher(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed = _run_hook(
        "show-me-prompt-guard.py",
        repo_root,
        payload={"prompt": "Odylith, show me what you can do."},
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    payload = json.loads(completed.stdout)
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "odylith-show-me" in additional_context
    assert "PYTHONPATH=src python -m odylith.cli show --repo-root ." in additional_context
    assert "stdout only" in additional_context
    assert "`intervention-status`, `visible-intervention`" in additional_context
    assert "launcher-state explanations" in additional_context


def test_show_me_prompt_guard_stays_silent_for_unrelated_prompts(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()

    completed = _run_hook(
        "show-me-prompt-guard.py",
        repo_root,
        payload={"prompt": "Please fix the dashboard tests."},
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
    assert completed.stderr == ""


def test_session_start_hook_refreshes_claude_auto_memory(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    call_log = tmp_path / "calls.jsonl"
    config_root = tmp_path / "claude-config"
    _write_fake_launcher(repo_root, call_log)
    _write_current_snapshot(repo_root)

    completed = _run_hook(
        "session-start-ground.py",
        repo_root,
        env={
            "ODYLITH_HOOK_CALLS": str(call_log),
            "CLAUDE_CONFIG_DIR": str(config_root),
        },
    )

    assert completed.returncode == 0
    assert "Odylith startup: selection: focused on B-083" in completed.stdout

    project_dirs = sorted((config_root / "projects").iterdir())
    assert len(project_dirs) == 1
    memory_dir = project_dirs[0] / "memory"
    memory_index = memory_dir / "MEMORY.md"
    governed_note = memory_dir / "odylith-governed-brief.md"
    assert memory_index.is_file()
    assert governed_note.is_file()
    index_text = memory_index.read_text(encoding="utf-8")
    note_text = governed_note.read_text(encoding="utf-8")
    assert "@odylith-governed-brief.md" in index_text
    assert "Claude hardening is live for B-083" in note_text
    assert "B-083: Claude support hardening" in note_text
    assert "Finish hooks and memory bridge" in note_text

    memory_index.write_text("## Personal\n- keep me\n\n" + index_text, encoding="utf-8")
    completed = _run_hook(
        "session-start-ground.py",
        repo_root,
        env={
            "ODYLITH_HOOK_CALLS": str(call_log),
            "CLAUDE_CONFIG_DIR": str(config_root),
        },
    )
    assert completed.returncode == 0
    refreshed_text = memory_index.read_text(encoding="utf-8")
    assert "## Personal" in refreshed_text
    assert refreshed_text.count("<!-- odylith-auto-memory:start -->") == 1


def test_subagent_start_hook_injects_odlyith_slice_context(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _write_current_snapshot(repo_root)

    completed = _run_hook(
        "subagent-start-ground.py",
        repo_root,
        payload={"agent_type": "odylith-registry-scribe"},
    )

    assert completed.returncode == 0
    payload = json.loads(completed.stdout)
    additional_context = payload["hookSpecificOutput"]["additionalContext"]
    assert "Claude hardening is live for B-083" in additional_context
    assert "B-083: Claude support hardening" in additional_context
    assert "CURRENT_SPEC.md" in additional_context


def test_stop_hook_logs_meaningful_turns_to_compass(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    call_log = tmp_path / "calls.jsonl"
    _write_fake_launcher(repo_root, call_log)

    completed = _run_hook(
        "log-stop-summary.py",
        repo_root,
        payload={
            "last_assistant_message": (
                "Updated CLAUDE assets and validated focused runtime tests for B-083. "
                "Validation passed on the install and runtime slices."
            )
        },
        env={"ODYLITH_HOOK_CALLS": str(call_log)},
    )

    assert completed.returncode == 0
    rows = [json.loads(line) for line in call_log.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    argv = rows[0]["argv"]
    assert argv[:2] == ["compass", "log"]
    assert "--summary" in argv
    assert "B-083" in argv


def test_subagent_stop_hook_appends_host_neutral_agent_stream_event(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    (repo_root / "odylith" / "compass" / "runtime").mkdir(parents=True, exist_ok=True)

    completed = _run_hook(
        "log-subagent-stop.py",
        repo_root,
        payload={
            "agent_id": "agent-123",
            "agent_type": "odylith-workstream",
            "session_id": "session-456",
            "last_assistant_message": (
                "Updated the scoped CLAUDE companions and validated the focused bundle "
                "and install tests for B-083."
            ),
        },
    )

    assert completed.returncode == 0
    stream_path = repo_root / "odylith" / "compass" / "runtime" / "agent-stream.v1.jsonl"
    rows = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert len(rows) == 1
    event = rows[0]
    assert event["kind"] == "subagent_stop"
    assert event["agent_type"] == "odylith-workstream"
    assert event["summary"] == "Updated the scoped CLAUDE companions and validated the focused bundle and install tests for B-083."
    assert event["workstreams"] == ["B-083"]
