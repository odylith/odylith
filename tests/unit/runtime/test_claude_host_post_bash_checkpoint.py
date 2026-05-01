from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import claude_host_post_bash_checkpoint


def _patch_stdin(monkeypatch, command: str, *, session_id: str = "claude-bash-1") -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {"command": command},
                    "session_id": session_id,
                }
            )
        ),
    )


def test_post_bash_checkpoint_runs_start_for_edit_like_bash(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(*, project_dir, args, timeout=20):
        calls.append((str(project_dir), list(args), timeout))
        return None

    _patch_stdin(monkeypatch, "python -c \"open('src/main.py', 'w').write('x')\"")
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint.claude_host_shared,
        "run_odylith",
        _fake_run_odylith,
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "refresh_governance",
        lambda **kwargs: None,
    )

    exit_code = claude_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == [(str(tmp_path), ["start", "--repo-root", "."], 20)]


def test_post_bash_checkpoint_skips_non_edit_like_bash(monkeypatch, tmp_path: Path) -> None:
    calls: list[bool] = []

    _patch_stdin(monkeypatch, "pytest -q")
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: calls.append(True),
    )

    exit_code = claude_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert calls == []


def test_post_bash_checkpoint_stays_silent_on_success(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    _patch_stdin(
        monkeypatch,
        "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH",
        session_id="claude-bash-visible",
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda **kwargs: [],
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "refresh_governance",
        lambda **kwargs: None,
    )

    exit_code = claude_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_post_bash_checkpoint_emits_compact_failure_only(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    _patch_stdin(
        monkeypatch,
        "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: odylith/radar/source/item.md\n@@\n-old\n+new\n*** End Patch\nPATCH",
        session_id="claude-bash-failure",
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "command_scoped_governed_paths",
        lambda **kwargs: ["odylith/radar/source/item.md"],
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "refresh_governance",
        lambda **kwargs: {"systemMessage": "Odylith governance refresh failed after Bash edit: validate failure"},
    )

    exit_code = claude_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert set(payload) == {"systemMessage"}
    assert "validate failure" in payload["systemMessage"]
    assert "Odylith Observation" not in payload["systemMessage"]
    assert "Odylith Proposal" not in payload["systemMessage"]
