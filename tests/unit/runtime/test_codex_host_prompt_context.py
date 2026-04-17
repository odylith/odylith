from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.intervention_engine import surface_runtime
from odylith.runtime.surfaces import codex_host_prompt_context


def test_render_codex_prompt_context_uses_first_explicit_anchor(monkeypatch) -> None:
    seen: list[str] = []

    def _fake_context_summary(*, project_dir: str, ref: str, payload_override=None) -> str:
        del project_dir, payload_override
        seen.append(ref)
        return f"Odylith anchor {ref}: primary target src/example.py."

    monkeypatch.setattr(codex_host_prompt_context.codex_host_shared, "context_summary", _fake_context_summary)

    rendered = codex_host_prompt_context.render_codex_prompt_context(
        prompt="Check B-088 against CB-102 before touching D-030.",
        conversation_bundle_override={},
    )

    assert rendered == "Odylith anchor B-088: primary target src/example.py."
    assert seen == ["B-088"]


def test_render_codex_prompt_context_returns_empty_without_anchor() -> None:
    assert codex_host_prompt_context.render_codex_prompt_context(prompt="Explain the change.") == ""


def test_render_codex_prompt_context_can_surface_a_teaser_without_anchor() -> None:
    rendered = codex_host_prompt_context.render_codex_prompt_context(
        prompt="Design a conversation observation engine with governed proposal flow.",
        intervention_bundle_override={
            "candidate": {
                "stage": "teaser",
                "teaser_text": "Odylith is noticing governed truth take shape here.",
            }
        },
    )

    assert rendered == surface_runtime.wrap_live_text("Odylith is noticing governed truth take shape here.")


def test_codex_prompt_system_message_hard_fails_visible_for_zero_signals(tmp_path: Path) -> None:
    prompt = "ZERO signals in my chat. Odylith interventions NEED to be visible."

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt=prompt,
        session_id="codex-zero-signals",
    )
    bundle = codex_host_prompt_context._prompt_conversation_bundle(
        repo_root=str(tmp_path),
        prompt=prompt,
        session_id="codex-zero-signals",
    )
    observation = dict(bundle["observation"])

    assert rendered.startswith("---\n\n**Odylith Observation:** This is a visibility failure")
    assert observation["context_packet_summary"]["packet_state"] == "visibility_recovery"
    assert observation["execution_engine_summary"]["execution_engine_next_move"] == "recover.current_blocker"
    assert observation["memory_summary"]["visibility_complaint"] is True
    assert observation["tribunal_summary"]["source"] == "intervention_alignment_context"


def test_codex_prompt_system_message_replays_pending_chat_block(tmp_path: Path) -> None:
    surface_runtime.stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="intervention_card",
        summary="Pending prompt replay.",
        session_id="codex-prompt-replay",
        host_family="codex",
        intervention_key="codex-prompt-replay-key",
        turn_phase="post_bash_checkpoint",
        display_markdown="**Odylith Observation:** Prompt must carry this pending block.",
        delivery_channel="system_message_and_assistant_fallback",
        delivery_status="assistant_fallback_ready",
    )

    rendered = codex_host_prompt_context.render_codex_prompt_system_message(
        repo_root=str(tmp_path),
        prompt="Do we still have a visible block pending?",
        session_id="codex-prompt-replay",
    )

    assert rendered == "---\n\n**Odylith Observation:** Prompt must carry this pending block.\n\n---"


def test_main_writes_user_prompt_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Please inspect B-088 next."})),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.codex_host_shared,
        "context_summary",
        lambda **_: "Odylith anchor B-088: primary target src/odylith/cli.py.",
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {},
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "src/odylith/cli.py" in payload["hookSpecificOutput"]["additionalContext"]
    assert "systemMessage" not in payload


def test_main_surfaces_visible_teaser_in_system_message(monkeypatch, tmp_path: Path, capsys) -> None:
    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"prompt": "Design a conversation observation engine with governed proposal flow."})),
    )
    monkeypatch.setattr(
        codex_host_prompt_context.conversation_surface,
        "build_conversation_bundle",
        lambda **_: {
            "intervention_bundle": {
                "candidate": {
                    "stage": "teaser",
                    "teaser_text": (
                        "Odylith is tracking this signal: This conversation is ready to become governed truth."
                    ),
                }
            }
        },
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert payload["hookSpecificOutput"]["additionalContext"].startswith("Odylith visible delivery fallback:")
    assert "Odylith is tracking this signal:" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"].startswith(f"{surface_runtime.LIVE_BOUNDARY}\n\nOdylith is tracking this signal:")
    assert payload["systemMessage"].endswith(f"\n{surface_runtime.LIVE_BOUNDARY}")
