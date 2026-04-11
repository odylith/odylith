from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import codex_host_session_brief


def _write_runtime_snapshot(repo_root: Path, payload: dict) -> None:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(json.dumps(payload), encoding="utf-8")


def test_render_codex_session_brief_includes_focus_actions_and_startup(tmp_path: Path) -> None:
    payload = {
        "generated_utc": "2026-04-11T12:00:00Z",
        "execution_focus": {
            "global": {
                "headline": "Codex parity is moving",
                "workstreams": ["B-088", "B-087"],
            }
        },
        "next_actions": [
            {"idea_id": "B-088", "action": "Bake the Codex host runtime into src/odylith."},
        ],
        "risks": {"traceability_warnings": ["Target-release wording is still ambiguous on one active surface."]},
    }

    rendered = codex_host_session_brief.render_codex_session_brief(
        payload_override=payload,
        start_summary_override="Selection: focused on B-088.",
    )

    assert "Headline: Codex parity is moving" in rendered
    assert "Active workstreams: B-088, B-087" in rendered
    assert "Brief freshness:" in rendered
    assert "Next actions:" in rendered
    assert "- B-088: Bake the Codex host runtime into src/odylith." in rendered
    assert "Risks:" in rendered
    assert "Startup: Selection: focused on B-088." in rendered


def test_render_codex_session_brief_degrades_without_snapshot(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    rendered = codex_host_session_brief.render_codex_session_brief(
        repo_root,
        payload_override=None,
        start_summary_override="",
    )
    assert "Active workstreams: (not present in Compass runtime snapshot)" in rendered


def test_main_writes_session_start_hook_json(tmp_path: Path, capsys) -> None:
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-088"]}},
        },
    )

    exit_code = codex_host_session_brief.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SessionStart"
    assert "B-088" in payload["hookSpecificOutput"]["additionalContext"]
