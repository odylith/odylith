from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import time

import pytest

from odylith.runtime.common import compass_log_continuation as continuation
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.surfaces import codex_host_shared, codex_host_stop_summary, host_dirty_checkpoint
from tests.unit.runtime.test_compass_log_continuation import PREFIX, _publish_prefix
from tests.unit.runtime.test_component_registry_intelligence import _seed_registry_repo
from tests.unit.runtime.test_greenfield_managed_mutation_boundary import _active_repository


pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX native Stop budget")
_SESSION_ID = "stop-budget-test"
_MESSAGE = "Implemented the bounded Stop hook and validated the focused process ownership regression tests."


def _configure_stop(monkeypatch, tmp_path: Path, *, budget: float = 0.5) -> str:
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text(
        f"#!{sys.executable}\n"
        "from pathlib import Path\n"
        "Path('unexpected-dispatch').write_text('Stop dispatched a canonical command')\n",
    )
    launcher.chmod(0o755)
    event_id = host_dirty_checkpoint.record_dirty_event(
        repo_root=tmp_path, host_family="codex", session_id=_SESSION_ID, source="test",
        governed_paths=["odylith/casebook/bugs/example.md"],
    )
    monkeypatch.setattr(codex_host_stop_summary, "_STOP_BUDGET_SECONDS", budget)
    monkeypatch.setattr(codex_host_shared, "load_payload",
                        lambda: {"session_id": _SESSION_ID, "last_assistant_message": _MESSAGE})
    monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery", lambda **kwargs: [])
    return event_id


def test_stop_retains_dirty_events_and_summary_without_dispatch(monkeypatch, tmp_path: Path, capsys) -> None:
    event_id = _configure_stop(monkeypatch, tmp_path)
    started = time.monotonic()
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert time.monotonic() - started < 1.5
    assert capsys.readouterr().out == ""
    assert not (tmp_path / "unexpected-dispatch").exists()
    assert [row["id"] for row in host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)] == [event_id]
    events = host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)
    assert len(events) == 1 and events[0]["event"]["summary"] == _MESSAGE
    assert events[0]["event"]["session_id"] == _SESSION_ID


@pytest.mark.parametrize("phase", ["load_payload", "capture", "confirmation"])
def test_stop_whole_scope_interrupts_local_work_without_false_durability_claim(
    monkeypatch, tmp_path: Path, capsys, phase: str,
) -> None:
    event_id = _configure_stop(monkeypatch, tmp_path, budget=0.4)
    if phase == "load_payload":
        monkeypatch.setattr(codex_host_shared, "load_payload", lambda: time.sleep(30))
    elif phase == "capture":
        monkeypatch.setattr(host_dirty_checkpoint, "capture_stop_summary", lambda **kwargs: time.sleep(30))
    else:
        monkeypatch.setattr(codex_host_stop_summary.host_surface_runtime, "confirm_assistant_chat_delivery",
                            lambda **kwargs: time.sleep(30))
    started = time.monotonic()
    assert codex_host_stop_summary.main(["--repo-root", str(tmp_path)]) == 0
    assert time.monotonic() - started < 1.5
    payload = json.loads(capsys.readouterr().out)
    assert "may not be saved" in payload["systemMessage"] and "decision" not in payload
    assert not (tmp_path / "unexpected-dispatch").exists()
    assert [row["id"] for row in host_dirty_checkpoint.read_dirty_events(repo_root=tmp_path)] == [event_id]
    events = host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)
    assert len(events) == (1 if phase == "confirmation" else 0)
    if events:
        assert events[0]["event"]["summary"] == _MESSAGE


def _tree_bytes(directory: Path) -> dict[str, tuple[bytes, int]]:
    return {str(path.relative_to(directory)): (path.read_bytes(), stat.S_IMODE(path.stat().st_mode))
            for path in directory.rglob("*") if path.is_file()}


@pytest.mark.parametrize("render_delay", [0, 30], ids=["no-delay", "post-append-timeout"])
def test_stop_preserves_active_publication_and_exact_pending_event(tmp_path: Path, render_delay: int) -> None:
    repo, _ = _active_repository(tmp_path)

    def prerequisites(descriptor):
        _seed_registry_repo(repo)
        for relative, data in {
            "odylith/casebook/bugs/INDEX.md": "# Bugs\n",
            "odylith/radar/traceability-graph.v1.json": "{}\n",
        }.items():
            path = repo / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["synthetic-stop-fixture-setup"], operation=prerequisites,
    ) == 0
    _publish_prefix(repo)
    baseline = generations.require_greenfield_working_generation(repo)
    canonical_before = _tree_bytes(repo / "odylith")
    immutable_before = _tree_bytes(baseline.repository_root)
    launcher = repo / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True, exist_ok=True)
    source_root = Path(__file__).resolve().parents[3] / "src"
    launcher.write_text(
        f"#!{sys.executable}\n"
        "import contextlib,hashlib,json,sys,time\nfrom pathlib import Path\n"
        f"sys.path.insert(0, {str(source_root)!r})\n"
        "from odylith.runtime.surfaces import codex_host_stop_summary as stop\n"
        "if sys.argv[1:3] == ['codex','stop-summary']:\n"
        "    stop._STOP_BUDGET_SECONDS = 6\n"
        "    stop.host_surface_runtime.confirm_assistant_chat_delivery = lambda **kwargs: []\n"
        "    raise SystemExit(stop.main(sys.argv[3:]))\n"
        "if sys.argv[1:3] == ['compass','log']:\n"
        "    from odylith import cli\n"
        "    from odylith.runtime.common import compass_log_continuation as continuation\n"
        "    from odylith.runtime.surfaces import compass_refresh_runtime as refresh\n"
        "    root=Path.cwd(); entry_before=(root/'odylith/index.html').read_bytes()\n"
        "    def delayed_render(**kwargs):\n"
        "        receipt=json.loads((root/continuation.RECEIPT_PATH).read_text())\n"
        "        stream=(root/continuation.STREAM_PATH).read_bytes()\n"
        "        marker={'phase':receipt['phase'],'before_stream':receipt['before_stream'],\n"
        "                'after_stream':receipt['after_stream'],'actual_stream_sha256':hashlib.sha256(stream).hexdigest(),\n"
        "                'entry_unchanged':(root/'odylith/index.html').read_bytes()==entry_before,\n"
        "                'event':receipt['event']}\n"
        "        (root/'actual-append-marker.json').write_text(json.dumps(marker))\n"
        f"        time.sleep({render_delay!r})\n"
        "    refresh._render_request=delayed_render\n"
        "    with (root/'compass-dispatch-output.log').open('w') as output:\n"
        "        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(output):\n"
        "            result=cli.main(sys.argv[1:])\n"
        "    raise SystemExit(result)\n"
        "raise SystemExit('unexpected fixture command')\n",
    )
    launcher.chmod(0o755)
    command = [str(launcher), "codex", "stop-summary", "--repo-root", str(repo)]
    started = time.monotonic()
    process = subprocess.Popen(command, cwd=repo, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        stdout, stderr = process.communicate(input=json.dumps({
            "session_id": _SESSION_ID, "last_assistant_message": _MESSAGE,
        }), timeout=20)
    finally:
        if process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=1)
    assert process.returncode == 0, stderr
    assert time.monotonic() - started < 20
    cli_output = repo / "compass-dispatch-output.log"
    if cli_output.exists():
        print("Real Compass CLI output: " + cli_output.read_text())
    marker_path = repo / "actual-append-marker.json"
    if marker_path.exists():
        marker = json.loads(marker_path.read_text())
        assert marker["phase"] == "appended" and marker["entry_unchanged"]
        assert marker["before_stream"]["sha256"] == hashlib.sha256(PREFIX).hexdigest()
        assert marker["after_stream"]["sha256"] == marker["actual_stream_sha256"]
        assert _MESSAGE in marker["event"]
        print("Real post-append cancellation marker: " + json.dumps(marker, sort_keys=True))
    # Real publication admission is the oracle, rather than a successful hook
    # exit, retained receipt, or stopped subprocess group alone.
    current = generations.require_greenfield_working_generation(repo)
    assert current.write_set_hash == baseline.write_set_hash
    assert _tree_bytes(repo / "odylith") == canonical_before
    assert _tree_bytes(baseline.repository_root) == immutable_before
    assert not marker_path.exists() and not (repo / continuation.RECEIPT_PATH).exists()
    assert (repo / continuation.STREAM_PATH).read_bytes() == PREFIX
    assert stat.S_IMODE((repo / continuation.STREAM_PATH).stat().st_mode) == 0o640
    events = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    assert len(events) == 1
    event = events[0]["event"]
    assert event["kind"] == "implementation" and event["summary"] == _MESSAGE
    assert event["session_id"] == _SESSION_ID and event["host_family"] == "codex"
    assert event["author"] == event["source"] == "assistant"
    assert event["ts_iso"] and event["transaction_id"] == "host-event-" + events[0]["id"]
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == events
    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["synthetic-stop-admission-check"], operation=lambda fd: 0,
    ) == 0
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == events
    assert stdout == stderr == ""


def test_native_stop_reserves_outer_hook_headroom() -> None:
    assert codex_host_stop_summary._STOP_BUDGET_SECONDS == 14
