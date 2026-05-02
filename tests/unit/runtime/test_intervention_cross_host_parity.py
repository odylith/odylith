from __future__ import annotations

import io
import json
from pathlib import Path

from odylith import cli
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.surfaces import claude_host_post_edit_checkpoint
from odylith.runtime.surfaces import claude_host_post_bash_checkpoint
from odylith.runtime.surfaces import claude_host_prompt_context
from odylith.runtime.surfaces import claude_host_prompt_teaser
from odylith.runtime.surfaces import claude_host_stop_summary
from odylith.runtime.surfaces import codex_host_post_bash_checkpoint
from odylith.runtime.surfaces import codex_host_prompt_context
from odylith.runtime.surfaces import codex_host_stop_summary
from odylith.runtime.surfaces import host_intervention_support


def _shared_checkpoint_bundle() -> dict[str, object]:
    return {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "key": "iv-parity",
                "suppressed_reason": "",
                "markdown_text": (
                    "**Odylith Observation:** Radar already has a governed slice here, "
                    "so this should keep moving through the same governed thread."
                ),
                "plain_text": (
                    "Odylith Observation: Radar already has a governed slice here, "
                    "so this should keep moving through the same governed thread."
                ),
            },
            "proposal": {
                "eligible": True,
                "suppressed_reason": "",
                "markdown_text": (
                    "-----\n"
                    "Odylith Proposal: Preserve the chat-visible UX contract.\n\n"
                    "- Radar: extend B-096.\n"
                    "- Registry: refresh governance-intervention-engine.\n\n"
                    "To apply, say \"apply this proposal\".\n"
                    "-----"
                ),
                "plain_text": (
                    "Odylith Proposal: Preserve the chat-visible UX contract."
                ),
            },
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
            "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
        },
    }


def test_cross_host_prompt_teaser_rendering_stays_consistent() -> None:
    prompt = "Design a conversation observation engine with governed proposal flow."
    intervention = {
        "candidate": {
            "stage": "teaser",
            "teaser_text": (
                "Odylith Observation: Casebook needs real failure evidence before it writes. "
                    "Why it matters: The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt."
            ),
        }
    }

    codex_text = codex_host_prompt_context.render_codex_prompt_context(
        prompt=prompt,
        intervention_bundle_override=intervention,
    )
    claude_text = claude_host_prompt_context.render_prompt_context(
        prompt=prompt,
        intervention_bundle_override=intervention,
    )

    assert codex_text == claude_text


def test_cross_host_prompt_submit_system_message_stays_quiet_without_feedback() -> None:
    prompt = "Make the intervention visibility path reliable."
    bundle = {
        "observation": {
            "host_family": "codex",
            "turn_phase": "prompt_submit",
            "session_id": "prompt-assist-parity",
            "prompt_excerpt": prompt,
        },
        "intervention_bundle": {
            "candidate": {"stage": "none", "suppressed_reason": "not_selected"},
            "proposal": {"eligible": False, "suppressed_reason": "not_selected"},
        },
    }

    codex_text = codex_host_prompt_context.render_codex_prompt_system_message(
        prompt=prompt,
        session_id="prompt-assist-parity",
        conversation_bundle_override=bundle,
    )
    claude_text = claude_host_prompt_teaser.render_prompt_teaser(
        prompt=prompt,
        session_id="prompt-assist-parity",
        conversation_bundle_override=bundle,
    )

    assert codex_text == claude_text
    assert codex_text == ""
    assert codex_host_prompt_context.render_codex_prompt_system_message(prompt="Odylith, help.") == ""
    assert claude_host_prompt_teaser.render_prompt_teaser(prompt="Odylith, help.") == ""


def test_cross_host_prompt_cli_payload_stays_consistent_for_same_teaser(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    intervention = {
        "candidate": {
            "stage": "teaser",
            "teaser_text": (
                "Odylith Observation: Casebook needs real failure evidence before it writes. "
                    "Why it matters: The prompt still contains a placeholder; ask for the actual command output or frame the item as Radar debt."
            ),
        }
    }
    bundle = {"intervention_bundle": intervention}

    monkeypatch.setattr(
        host_intervention_support.conversation_surface,
        "build_conversation_bundle",
        lambda **_: bundle,
    )

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "Design a conversation observation engine with governed proposal flow.",
                    "session_id": "prompt-parity-1",
                }
            )
        ),
    )
    assert cli.main(["codex", "prompt-context", "--repo-root", str(tmp_path)]) == 0
    codex_payload = json.loads(capsys.readouterr().out)
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "prompt": "Design a conversation observation engine with governed proposal flow.",
                    "session_id": "prompt-parity-1",
                }
            )
        ),
    )
    assert cli.main(["claude", "prompt-teaser", "--repo-root", str(tmp_path)]) == 0
    claude_visible_text = capsys.readouterr().out

    assert codex_payload["hookSpecificOutput"]["additionalContext"].startswith("Odylith visible delivery recovery:")
    assert claude_visible_text in codex_payload["hookSpecificOutput"]["additionalContext"]
    assert codex_payload["systemMessage"] == claude_visible_text
    assert "**Odylith Assist:**" not in claude_visible_text
    assert not claude_visible_text.lstrip().startswith("{")
    codex_events = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
    )
    assert not any(row.get("kind") == "assist_closeout" for row in codex_events)


def test_cross_host_checkpoint_cli_dispatch_surfaces_codex_live_only_and_keeps_claude_silent(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    bundle = _shared_checkpoint_bundle()

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
                    },
                    "session_id": "checkpoint-parity-1",
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
        lambda **kwargs: bundle,
    )

    assert cli.main(["codex", "post-bash-checkpoint", "--repo-root", str(tmp_path)]) == 0
    codex_payload = json.loads(capsys.readouterr().out)
    codex_context = codex_payload["hookSpecificOutput"]["additionalContext"]
    assert codex_payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "Odylith visible delivery recovery:" in codex_context
    assert "Odylith Observation:" in codex_context
    assert "Odylith Proposal:" in codex_context
    assert "Odylith Assist:" not in codex_context
    assert "Odylith Assist:" not in codex_payload["systemMessage"]

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_input": {"file_path": str(tmp_path / "src" / "main.py")},
                    "session_id": "checkpoint-parity-1",
                }
            )
        ),
    )
    monkeypatch.setattr(
        claude_host_post_edit_checkpoint.claude_host_shared,
        "run_odylith",
        lambda **kwargs: None,
    )

    assert cli.main(["claude", "post-edit-checkpoint", "--repo-root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(
            json.dumps(
                {
                    "tool_name": "Bash",
                    "tool_input": {
                        "command": "apply_patch <<'PATCH'\n*** Begin Patch\n*** Update File: src/main.py\n@@\n-old\n+new\n*** End Patch\nPATCH"
                    },
                    "session_id": "checkpoint-parity-1",
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

    assert cli.main(["claude", "post-bash-checkpoint", "--repo-root", str(tmp_path)]) == 0
    assert capsys.readouterr().out == ""


def test_cross_host_stop_rendering_stays_consistent_for_same_bundle(tmp_path: Path) -> None:
    bundle = {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The signal is real.",
                "plain_text": "Odylith Observation: The signal is real.",
            },
            "proposal": {"eligible": False, "suppressed_reason": ""},
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** B-096 stayed tied to the refreshed intervention contract.",
            "plain_text": "Odylith Assist: B-096 stayed tied to the refreshed intervention contract.",
        },
    }

    codex_text = codex_host_stop_summary.render_codex_stop_summary(
        str(tmp_path),
        message="Implemented the engine slice.",
        session_id="stop-parity-1",
        conversation_bundle_override=bundle,
    )
    claude_text = claude_host_stop_summary.render_stop_summary(
        repo_root=tmp_path,
        payload={
            "last_assistant_message": "Implemented the engine slice.",
            "session_id": "stop-parity-1",
        },
        conversation_bundle_override=bundle,
    )

    assert codex_text == claude_text
