from __future__ import annotations

import io
import json
from pathlib import Path

from odylith import cli
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import voice
from odylith.runtime.intervention_engine.contract import GovernanceFact
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


def test_prompt_hooks_never_replay_a_stale_multi_item_bundle_as_the_answer(tmp_path: Path) -> None:
    stale_blocks = (
        "**Odylith Insight:** Compass is carrying the sharper operator risk.",
        "**Odylith Insight:** B-001 is an active Radar lane.",
        "**Odylith Insight:** `execution-engine` is the live Registry boundary.",
        "**Odylith Risks:** Capture the final reviewed checkpoint for B-002.",
        "**Odylith Assist:** updating affected governance contracts, then keeping the slice bounded.",
    )
    for host_family, session_id, turn_phase in (
        ("codex", "codex-stale-wall", "post_bash_checkpoint"),
        ("claude", "claude-stale-wall", "post_edit_checkpoint"),
    ):
        for index, display in enumerate(stale_blocks):
            stream_state.append_intervention_event(
                repo_root=tmp_path,
                kind="assist_closeout" if "Assist" in display else "ambient_signal",
                summary=f"Stale replay row {index}.",
                session_id=session_id,
                host_family=host_family,
                intervention_key=f"{session_id}-{index}",
                turn_phase=turn_phase,
                display_markdown=display,
                delivery_channel="system_message_and_assistant_fallback",
                delivery_status="assistant_fallback_ready",
            )

    prompt = "How are we doing against the Greenfield goal?"
    rendered = (
        codex_host_prompt_context.render_codex_prompt_system_message(
            repo_root=str(tmp_path),
            prompt=prompt,
            session_id="codex-stale-wall",
        ),
        claude_host_prompt_context.render_prompt_system_message(
            repo_root=tmp_path,
            prompt=prompt,
            session_id="claude-stale-wall",
        ),
    )

    for message in rendered:
        assert all(stale not in message for stale in stale_blocks)
        assert message.count("**Odylith ") <= 1


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


def test_cross_host_prompt_preserves_complete_generated_teaser() -> None:
    fact = GovernanceFact(
        kind="history",
        headline="Casebook records the earlier incomplete proof.",
        detail=(
            "The earlier check covered the normal observation path and its selected "
            "evidence together with the unchanged confirmation boundary for this turn, "
            "but the empty and degraded cases still need fresh verification before "
            "any completion claim can be made, so this result does not authorize a release."
        ),
    )
    _headline, _markdown_text, _plain_text, teaser = voice.render_observation(
        facts=[fact], proposal_actions=[],
    )
    intervention = {"candidate": {"stage": "teaser", "teaser_text": teaser}}
    prompt = "Design a conversation observation engine with governed proposal flow."

    codex_text = codex_host_prompt_context.render_codex_prompt_context(
        prompt=prompt, intervention_bundle_override=intervention,
    )
    claude_text = claude_host_prompt_context.render_prompt_context(
        prompt=prompt, intervention_bundle_override=intervention,
    )

    assert codex_text == claude_text
    assert f"Odylith Observation: {fact.headline} Why it matters: {fact.detail}" in codex_text


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
