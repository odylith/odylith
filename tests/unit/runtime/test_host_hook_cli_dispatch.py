from __future__ import annotations

import io
import json
from pathlib import Path

from odylith import cli
from odylith.runtime.surfaces import claude_host_post_bash_checkpoint
from odylith.runtime.surfaces import claude_host_post_edit_checkpoint
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint


def test_codex_post_bash_checkpoint_cli_dispatch_emits_visible_intervention(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    radar = tmp_path / "odylith" / "radar" / "source" / "ideas"
    radar.mkdir(parents=True)
    (radar / "visible-intervention.md").write_text("Backlog: B-096\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
                    },
                    "session_id": "cli-bash-1",
                }
            )
        ),
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
                    "markdown_text": "**Odylith Observation:** Radar already owns this slice.",
                    "plain_text": "Odylith Observation: Radar already owns this slice.",
                },
                "proposal": {
                    "eligible": True,
                    "suppressed_reason": "",
                    "markdown_text": '-----\nOdylith Proposal: Preserve the chat-visible UX contract.\n\n- Radar: extend B-096.\n\nTo apply, say "apply this proposal".\n-----',
                    "plain_text": 'Odylith Proposal: Preserve the chat-visible UX contract.',
                },
            },
            "closeout_bundle": {
                "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
                "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
            },
        },
    )

    exit_code = cli.main(["codex", "post-bash-checkpoint", "--repo-root", str(tmp_path)])

    payload = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "**Odylith Observation:** Radar already owns this slice." in payload["hookSpecificOutput"]["additionalContext"]
    assert "Odylith Proposal:" in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract." not in payload["hookSpecificOutput"]["additionalContext"]
    assert "**Odylith Observation:** Radar already owns this slice." in payload["systemMessage"]
    assert "Odylith Proposal:" in payload["systemMessage"]
    assert "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract." not in payload["systemMessage"]


def test_claude_post_edit_checkpoint_cli_dispatch_stays_silent_on_success(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    target = tmp_path / "src" / "main.py"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("print('hi')\n", encoding="utf-8")
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(target)},
                    "session_id": "cli-edit-1",
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )

    exit_code = cli.main(["claude", "post-edit-checkpoint", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_claude_post_bash_checkpoint_cli_dispatch_stays_silent_on_success(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
                    },
                    "session_id": "cli-claude-bash-1",
                }
            )
        ),
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

    exit_code = cli.main(["claude", "post-bash-checkpoint", "--repo-root", str(tmp_path)])

    assert exit_code == 0
    assert capsys.readouterr().out == ""
