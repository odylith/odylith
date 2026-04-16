from __future__ import annotations

from odylith import cli
from odylith.runtime.surfaces import host_visible_intervention


def _bundle() -> dict[str, object]:
    return {
        "intervention_bundle": {
            "candidate": {
                "stage": "card",
                "suppressed_reason": "",
                "markdown_text": "**Odylith Observation:** The host hid the hook, so the assistant speaks it.",
                "plain_text": "Odylith Observation: The host hid the hook, so the assistant speaks it.",
            },
            "proposal": {
                "eligible": True,
                "suppressed_reason": "",
                "markdown_text": (
                    "-----\n"
                    "Odylith Proposal: Preserve the chat-visible UX contract.\n\n"
                    "- Registry: update the host visibility contract.\n\n"
                    "To apply, say \"apply this proposal\".\n"
                    "-----"
                ),
                "plain_text": "Odylith Proposal: Preserve the chat-visible UX contract.",
            },
        },
        "closeout_bundle": {
            "markdown_text": "**Odylith Assist:** kept the visible path alive.",
            "plain_text": "Odylith Assist: kept the visible path alive.",
        },
    }


def test_visible_intervention_renders_live_markdown_without_assist(monkeypatch) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        host_family="codex",
        phase="post_bash_checkpoint",
        changed_paths=["src/example.py"],
    )

    assert "**Odylith Observation:**" in rendered
    assert "Odylith Proposal:" in rendered
    assert "Odylith Assist:" not in rendered


def test_visible_intervention_renders_stop_assist(monkeypatch) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    rendered = host_visible_intervention.render_visible_intervention(
        host_family="claude",
        phase="stop_summary",
        summary="Implemented the visible fallback.",
    )

    assert "**Odylith Observation:**" in rendered
    assert "**Odylith Assist:** kept the visible path alive." in rendered


def test_stop_visible_intervention_recovers_assist_from_summary_validation(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="stop_summary",
        summary="Validation passed with 551 tests after the visible intervention fallback landed.",
        include_closeout=True,
    )

    assert "**Odylith Assist:** kept the proof tight" in rendered
    assert "closing with 1 focused check" in rendered


def test_visible_intervention_operator_visibility_failure_is_never_silent(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="codex",
        phase="prompt_submit",
        prompt="I do not think it is working",
    )

    assert rendered.startswith("**Odylith Observation:** This is a visibility failure")
    assert "show the Odylith Markdown directly" in rendered


def test_visible_intervention_replaces_generic_teaser_for_visibility_failure(tmp_path) -> None:
    rendered = host_visible_intervention.render_visible_intervention(
        repo_root=tmp_path,
        host_family="claude",
        phase="prompt_submit",
        prompt="Dude, I still do not see any Odylith Observation, Proposal, Ambient, or Assist in chat.",
    )

    assert rendered.startswith("**Odylith Observation:** This is a visibility failure")
    assert "Claude may be computing intervention payloads" in rendered
    assert "One more corroborating signal" not in rendered


def test_codex_visible_intervention_cli_dispatches_plain_markdown(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    exit_code = cli.main(
        [
            "codex",
            "visible-intervention",
            "--repo-root",
            ".",
            "--phase",
            "post_bash_checkpoint",
            "--changed-path",
            "src/example.py",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert output.startswith("**Odylith Observation:**")
    assert "Odylith Proposal:" in output
    assert not output.lstrip().startswith("{")


def test_claude_visible_intervention_cli_dispatches_plain_markdown(monkeypatch, capsys) -> None:
    monkeypatch.setattr(
        host_visible_intervention.host_surface_runtime,
        "compose_host_conversation_bundle",
        lambda **kwargs: _bundle(),
    )

    exit_code = cli.main(
        [
            "claude",
            "visible-intervention",
            "--repo-root",
            ".",
            "--phase",
            "stop_summary",
            "--summary",
            "Implemented the visible fallback.",
        ]
    )

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "**Odylith Assist:** kept the visible path alive." in output
    assert not output.lstrip().startswith("{")
