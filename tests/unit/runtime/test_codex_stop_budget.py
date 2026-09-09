from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time

import pytest

from odylith.runtime.surfaces import codex_host_shared, codex_host_stop_summary, host_dirty_checkpoint


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX native Stop budget")
_SESSION_ID = "stop-budget-test"
_MESSAGE = "Implemented the bounded Stop hook and validated the focused process ownership regression tests."


def _configure_stop(monkeypatch, tmp_path: Path, *, sleeps: dict[str, float], budget: float = 0.5) -> str:
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        f"#!{sys.executable}\n"
        "import sys,time\n"
        "from pathlib import Path\n"
        "phase = sys.argv[1]\n"
        "with Path('phases.log').open('a') as stream: stream.write(phase + '\\n')\n"
        f"time.sleep({sleeps!r}.get(phase, 0))\n",
    )
    launcher.chmod(0o755)
    event_id = host_dirty_checkpoint.record_dirty_event(
        repo_root=tmp_path,
        host_family="codex",
        session_id=_SESSION_ID,
        source="test",
        governed_paths=["odylith/casebook/bugs/example.md"],
    )
    monkeypatch.setattr(codex_host_stop_summary, "_STOP_BUDGET_SECONDS", budget)
    monkeypatch.setattr(
        codex_host_shared, "load_payload",
        lambda: {"session_id": _SESSION_ID, "last_assistant_message": _MESSAGE},
    )
    monkeypatch.setattr(codex_host_stop_summary, "_stop_intervention_bundle", lambda **kwargs: {})
    monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery", lambda **kwargs: [])
    monkeypatch.setattr(codex_host_stop_summary.visibility_replay, "replayable_chat_markdown", lambda **kwargs: "")
    return event_id


@pytest.mark.parametrize("sleeps, expected_phases", [
    ({"start": 30}, ["start"]),
    ({"start": 0.15, "sync": 30}, ["start", "sync"]),
])
def test_stop_expiry_keeps_dirty_events_and_does_not_start_later_phases(
    monkeypatch, tmp_path: Path, capsys, sleeps: dict[str, float], expected_phases: list[str],
) -> None:
    event_id = _configure_stop(monkeypatch, tmp_path, sleeps=sleeps)
    started = time.monotonic()
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert time.monotonic() - started < 1.5
    payload = json.loads(capsys.readouterr().out)
    assert "deferred" in payload["systemMessage"]
    assert "queued" in payload["systemMessage"]
    assert "decision" not in payload
    assert (tmp_path / "phases.log").read_text().splitlines() == expected_phases
    assert [row["id"] for row in host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)] == [event_id]


def test_stop_success_settles_events_and_runs_all_phases(monkeypatch, tmp_path: Path, capsys) -> None:
    _configure_stop(monkeypatch, tmp_path, sleeps={}, budget=2)
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert (tmp_path / "phases.log").read_text().splitlines() == ["start", "sync", "compass"]
    assert host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path) == []
    assert capsys.readouterr().out == ""


def test_stop_logging_shares_remaining_budget_after_successful_sync(monkeypatch, tmp_path: Path, capsys) -> None:
    _configure_stop(monkeypatch, tmp_path, sleeps={"start": 0.1, "sync": 0.1, "compass": 30}, budget=1)
    rendered = []
    monkeypatch.setattr(codex_host_stop_summary, "_stop_intervention_bundle", lambda **kwargs: rendered.append(True))
    started = time.monotonic()
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert time.monotonic() - started < 2
    assert "deferred" in json.loads(capsys.readouterr().out)["systemMessage"]
    assert host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path) == []
    assert (tmp_path / "phases.log").read_text().splitlines() == ["start", "sync", "compass"]
    assert rendered == []


@pytest.mark.parametrize("phase", ["load_payload", "render"])
def test_stop_whole_scope_interrupts_local_work(monkeypatch, tmp_path: Path, capsys, phase: str) -> None:
    _configure_stop(monkeypatch, tmp_path, sleeps={}, budget=0.4)
    if phase == "load_payload":
        monkeypatch.setattr(codex_host_shared, "load_payload", lambda: time.sleep(30))
    else:
        monkeypatch.setattr(codex_host_stop_summary, "_stop_intervention_bundle", lambda **kwargs: time.sleep(30))
    started = time.monotonic()
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert time.monotonic() - started < 1.5
    assert "decision" not in json.loads(capsys.readouterr().out)
    if phase == "load_payload":
        assert not (tmp_path / "phases.log").exists()
        assert host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)


def test_native_stop_reserves_outer_hook_headroom() -> None:
    assert codex_host_stop_summary._STOP_BUDGET_SECONDS == 14
