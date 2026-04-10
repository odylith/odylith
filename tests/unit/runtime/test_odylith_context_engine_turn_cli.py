from __future__ import annotations

from pathlib import Path

from odylith.runtime.context_engine import odylith_context_engine


def test_session_brief_cli_preserves_turn_context_fields(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        odylith_context_engine,
        "_run_session_brief",
        lambda **kwargs: captured.update(kwargs) or 0,
    )

    rc = odylith_context_engine.main(
        [
            "--repo-root",
            str(tmp_path),
            "session-brief",
            "--intent",
            'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"',
            "--surface",
            "compass",
            "--visible-text",
            "Task Contract, Event Ledger, and Hard-Constraint Promotion",
            "--active-tab",
            "releases",
            "--user-turn-id",
            "turn-2",
            "--supersedes-turn-id",
            "turn-1",
        ]
    )

    assert rc == 0
    assert captured["intent"] == 'Move the current release label next to the title "Task Contract, Event Ledger, and Hard-Constraint Promotion"'
    assert captured["surfaces"] == ["compass"]
    assert captured["visible_text"] == ["Task Contract, Event Ledger, and Hard-Constraint Promotion"]
    assert captured["active_tab"] == "releases"
    assert captured["user_turn_id"] == "turn-2"
    assert captured["supersedes_turn_id"] == "turn-1"


def test_bootstrap_session_cli_preserves_turn_context_fields(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        odylith_context_engine,
        "_run_bootstrap_session",
        lambda **kwargs: captured.update(kwargs) or 0,
    )

    rc = odylith_context_engine.main(
        [
            "--repo-root",
            str(tmp_path),
            "bootstrap-session",
            "--intent",
            "Why doesn't this admin panel take full width?",
            "--surface",
            "compass",
            "--visible-text",
            "Current release",
            "--active-tab",
            "releases",
            "--user-turn-id",
            "turn-3",
            "--supersedes-turn-id",
            "turn-2",
        ]
    )

    assert rc == 0
    assert captured["intent"] == "Why doesn't this admin panel take full width?"
    assert captured["surfaces"] == ["compass"]
    assert captured["visible_text"] == ["Current release"]
    assert captured["active_tab"] == "releases"
    assert captured["user_turn_id"] == "turn-3"
    assert captured["supersedes_turn_id"] == "turn-2"
