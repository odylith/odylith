from __future__ import annotations

import io
import json

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

    assert rendered == "Odylith is noticing governed truth take shape here."


def test_main_writes_user_prompt_hook_json(monkeypatch, capsys) -> None:
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

    exit_code = codex_host_prompt_context.main(["--repo-root", "."])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "src/odylith/cli.py" in payload["hookSpecificOutput"]["additionalContext"]
    assert "systemMessage" not in payload


def test_main_surfaces_visible_teaser_in_system_message(monkeypatch, capsys) -> None:
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
                        "Odylith can already see governed truth starting to crystallize here. "
                        "One more corroborating signal and it can turn that into a proposal."
                    ),
                }
            }
        },
    )

    exit_code = codex_host_prompt_context.main(["--repo-root", "."])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert payload["hookSpecificOutput"]["additionalContext"].startswith("Odylith visible delivery fallback:")
    assert "Odylith can already" in payload["hookSpecificOutput"]["additionalContext"]
    assert payload["systemMessage"].startswith("Odylith can already")
