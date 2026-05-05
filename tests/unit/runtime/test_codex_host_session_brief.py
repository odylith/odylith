from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

from odylith.runtime.surfaces import codex_host_shared
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
    assert "Interventions: Observation, Proposal, and Assist are armed" in rendered
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
    assert "Odylith startup substrate:" in rendered
    assert "cached runtime fast path" not in rendered


def test_render_codex_session_brief_sanitizes_start_narrowing_output() -> None:
    rendered = codex_host_session_brief.render_codex_session_brief(
        payload_override={},
        start_summary_override="odylith start\n- lane: fallback\n- reason: Need one code path.\n",
    )

    assert "Startup: needs a narrower target before implementation." in rendered
    assert "Name one code path, workstream, component, bug, or file." in rendered
    assert "fallback" not in rendered.casefold()
    assert "Need one code path" not in rendered


def test_codex_start_payload_requests_json_packet(monkeypatch, tmp_path: Path) -> None:
    calls: list[tuple[str, list[str], int]] = []

    def _fake_run_odylith(**kwargs: object) -> SimpleNamespace:
        calls.append(
            (
                str(kwargs["project_dir"]),
                list(kwargs["args"]),  # type: ignore[arg-type]
                int(kwargs["timeout"]),
            )
        )
        return SimpleNamespace(stdout='odylith start\n- lane: bootstrap\n{"packet_kind":"bootstrap_session"}')

    monkeypatch.setattr(codex_host_shared, "run_odylith", _fake_run_odylith)

    payload = codex_host_shared.start_payload(tmp_path)

    assert payload == {"packet_kind": "bootstrap_session"}
    assert calls == [(str(tmp_path), ["start", "--repo-root", ".", "--json"], 20)]


def test_render_codex_session_brief_uses_substrate_without_start(tmp_path: Path, monkeypatch) -> None:
    _write_runtime_snapshot(
        tmp_path,
        {
            "generated_utc": "2026-04-11T12:00:00Z",
            "execution_focus": {"global": {"headline": "h", "workstreams": ["B-088"]}},
        },
    )

    def _unexpected_start(**_: object) -> None:
        raise AssertionError("cached SessionStart fast path must not run odylith start")

    monkeypatch.setattr(codex_host_session_brief.codex_host_shared, "start_summary", _unexpected_start)
    monkeypatch.setattr(
        codex_host_session_brief.host_intervention_support,
        "session_start_substrate_context",
        lambda **_: "Odylith startup substrate: context=host_intervention_context/observing.",
    )

    rendered = codex_host_session_brief.render_codex_session_brief(tmp_path)

    assert "B-088" in rendered
    assert "Odylith startup substrate: context=host_intervention_context/observing." in rendered
    assert "cached runtime fast path" not in rendered


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
