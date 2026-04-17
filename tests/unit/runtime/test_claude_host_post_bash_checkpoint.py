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
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "_post_bash_bundle",
        lambda **kwargs: {},
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


def test_post_bash_checkpoint_emits_visible_observation_and_proposal(
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
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "_post_bash_bundle",
        lambda **kwargs: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "card",
                    "suppressed_reason": "",
                    "markdown_text": "**Odylith Observation:** The Bash edit is governed now.",
                    "plain_text": "Odylith Observation: The Bash edit is governed now.",
                },
                "proposal": {
                    "eligible": True,
                    "suppressed_reason": "",
                    "markdown_text": 'Odylith Proposal: preserve the chat-visible UX contract.\n\nTo apply, say "apply this proposal".',
                    "plain_text": "Odylith Proposal: preserve the chat-visible UX contract.",
                },
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** kept this grounded.",
                "plain_text": "Odylith Assist: kept this grounded.",
            },
        },
    )

    exit_code = claude_host_post_bash_checkpoint.main(["--repo-root", str(tmp_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert "**Odylith Observation:** The Bash edit is governed now." in payload["additionalContext"]
    assert "Odylith Proposal:" in payload["additionalContext"]
    assert "**Odylith Assist:** kept this grounded." in payload["additionalContext"]
    assert "**Odylith Observation:** The Bash edit is governed now." in payload["systemMessage"]
    assert "Odylith Proposal:" in payload["systemMessage"]
    assert "Odylith Assist:" not in payload["systemMessage"]


def test_post_bash_bundle_uses_recent_prompt_excerpt_not_intervention_summary(
    monkeypatch,
    tmp_path: Path,
) -> None:
    claude_host_post_bash_checkpoint.codex_host_post_bash_checkpoint.intervention_surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="capture_proposed",
        summary="Odylith Proposal pending.",
        session_id="claude-bash-memory",
        host_family="claude",
        intervention_key="iv-claude-bash",
        turn_phase="post_bash_checkpoint",
        prompt_excerpt="Keep the human prompt alive across Claude Bash checkpoints.",
        display_markdown="**Odylith Proposal**",
    )
    monkeypatch.setattr(
        claude_host_post_bash_checkpoint,
        "inferred_command_paths",
        lambda **kwargs: ["src/main.py"],
    )

    bundle = claude_host_post_bash_checkpoint._post_bash_bundle(
        project_dir=tmp_path,
        command="python -c \"open('src/main.py', 'w').write('x')\"",
        session_id="claude-bash-memory",
    )

    assert bundle["observation"]["prompt_excerpt"] == (
        "Keep the human prompt alive across Claude Bash checkpoints."
    )
