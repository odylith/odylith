from __future__ import annotations

import io
import json
from pathlib import Path

from odylith.runtime.surfaces import claude_host_subagent_start


def _write_runtime_snapshot(repo_root: Path) -> None:
    runtime_dir = repo_root / "odylith" / "compass" / "runtime"
    runtime_dir.mkdir(parents=True, exist_ok=True)
    (runtime_dir / "current.v1.json").write_text(
        json.dumps(
            {
                "generated_utc": "2026-04-11T12:00:00Z",
                "execution_focus": {
                    "global": {
                        "headline": "Claude hardening is live for B-083",
                        "workstreams": ["B-083"],
                    }
                },
                "current_workstreams": [
                    {"idea_id": "B-083", "title": "Claude support hardening"},
                ],
                "verified_scoped_workstreams": {"24h": ["B-083"]},
                "next_actions": [
                    {"idea_id": "B-083", "action": "Finish hooks and memory bridge"},
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_render_subagent_payload_returns_canonical_hook_shape(tmp_path: Path) -> None:
    _write_runtime_snapshot(tmp_path)

    rendered = claude_host_subagent_start.render_subagent_payload(
        repo_root=tmp_path,
        agent_type="odylith-workstream",
    )

    assert rendered is not None
    assert rendered["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    additional = rendered["hookSpecificOutput"]["additionalContext"]
    assert "Claude hardening is live for B-083" in additional
    assert "B-083" in additional


def test_render_subagent_payload_falls_back_to_baseline_guidance_without_snapshot(tmp_path: Path) -> None:
    rendered = claude_host_subagent_start.render_subagent_payload(
        repo_root=tmp_path,
        agent_type="odylith-workstream",
    )

    assert rendered is not None
    additional = rendered["hookSpecificOutput"]["additionalContext"]
    assert "Odylith subagent grounding:" in additional
    assert "Live focus:" not in additional
    assert "Active workstreams:" not in additional
    assert "Keep nearest `AGENTS.md` and `CLAUDE.md` guidance" in additional
    assert "Agent-specific constraint:" in additional


def test_main_writes_subagent_start_hook_json(monkeypatch, tmp_path: Path, capsys) -> None:
    _write_runtime_snapshot(tmp_path)

    monkeypatch.setattr(
        "sys.stdin",
        io.StringIO(json.dumps({"agent_type": "odylith-workstream"})),
    )

    exit_code = claude_host_subagent_start.main(["--repo-root", str(tmp_path)])

    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["hookSpecificOutput"]["hookEventName"] == "SubagentStart"
    assert "Claude hardening is live for B-083" in payload["hookSpecificOutput"]["additionalContext"]
