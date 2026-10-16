"""Captured surface failures retain default or explicitly owned retry advice."""

from __future__ import annotations

from contextlib import contextmanager
import os
import sys

import pytest

from odylith.runtime.governance import owned_surface_refresh as refresh


@pytest.mark.parametrize("override", [(), ("compass", "log", "--repo-root", ".", "--complete")])
def test_retry_override_preserves_capture_compaction_and_defaults(tmp_path, monkeypatch, capfd, override):
    def noisy_refresh(**kwargs):
        assert kwargs == {"repo_root": tmp_path, "surfaces": ("compass",)}
        print("python progress", flush=True)
        print("python stderr", file=sys.stderr, flush=True)
        os.write(1, b"descriptor progress\n")
        os.write(2, b"descriptor error\n")
        return 7

    monkeypatch.setattr(refresh, "refresh_owned_surfaces", noisy_refresh)
    with pytest.raises(RuntimeError) as caught:
        refresh.raise_for_failed_refresh(repo_root=tmp_path, surface="compass", operation_label="Append",
                                         retry_command=override)
    output = capfd.readouterr()
    assert output.out == output.err == ""
    message = str(caught.value)
    assert "Refresh output: python progress python stderr descriptor progress descriptor error" in message
    if override:
        assert "odylith compass log --repo-root . --complete" in message
        assert "odylith compass refresh --repo-root . --wait" not in message
    else:
        assert "odylith compass refresh --repo-root . --wait" in message
        assert "--complete" not in message


def test_success_stays_quiet_with_retry_override(tmp_path, monkeypatch, capfd):
    def noisy_refresh(**kwargs):
        print("hidden success chatter")
        return 0

    monkeypatch.setattr(refresh, "refresh_owned_surfaces", noisy_refresh)
    refresh.raise_for_failed_refresh(repo_root=tmp_path, surface="compass", operation_label="Append",
                                     retry_command=("compass", "log", "--complete"))
    output = capfd.readouterr()
    assert output.out == output.err == ""


@pytest.mark.parametrize("failure", ["action", "on_results"])
def test_execution_oserror_never_replays_refresh(tmp_path, monkeypatch, failure):
    calls = []

    def observe(results):
        raise OSError("synthetic result observer failure")

    def action(**kwargs):
        calls.append(True)
        if failure == "action":
            raise OSError("synthetic action failure")
        kwargs["on_results"]([])
        return 0

    monkeypatch.setattr(refresh, "refresh_owned_surfaces", action)
    with pytest.raises(OSError, match="synthetic"):
        refresh.raise_for_failed_refresh(repo_root=tmp_path, surface="compass", operation_label="Append",
                                         on_results=observe)
    assert calls == [True]


def test_capture_setup_failure_falls_back_before_exactly_one_execution(tmp_path, monkeypatch, capsys):
    calls = []

    def unavailable_capture(**kwargs):
        raise OSError("synthetic capture setup unavailable")

    def action(**kwargs):
        calls.append(True)
        print("hidden fallback Python output")
        return 0

    monkeypatch.setattr(refresh.tempfile, "TemporaryFile", unavailable_capture)
    monkeypatch.setattr(refresh, "refresh_owned_surfaces", action)
    refresh.raise_for_failed_refresh(repo_root=tmp_path, surface="compass", operation_label="Append")
    assert calls == [True]
    assert capsys.readouterr().out == ""


def test_capture_cleanup_oserror_never_replays_completed_refresh(tmp_path, monkeypatch, capfd):
    calls = []
    delivered = []
    real_capture = refresh.tempfile.TemporaryFile

    @contextmanager
    def failed_cleanup(**kwargs):
        with real_capture(**kwargs) as captured:
            yield captured
        raise OSError("synthetic capture cleanup failure")

    def action(**kwargs):
        calls.append(True)
        print("hidden completed action")
        kwargs["on_results"]([{"status": "passed"}])
        return 0

    monkeypatch.setattr(refresh.tempfile, "TemporaryFile", failed_cleanup)
    monkeypatch.setattr(refresh, "refresh_owned_surfaces", action)
    with pytest.raises(OSError, match="capture cleanup"):
        refresh.raise_for_failed_refresh(repo_root=tmp_path, surface="compass", operation_label="Append",
                                         on_results=delivered.extend)
    assert calls == [True]
    assert delivered == [{"status": "passed"}]
    output = capfd.readouterr()
    assert output.out == output.err == ""


def test_action_snapshot_is_opt_in_and_does_not_change_default_result(tmp_path):
    from odylith.runtime.governance import sync_workstream_artifacts as sync

    action = {"rc": 0, "status": "passed", "state": {"request_id": "original"}}
    step = sync._execution_step("test", surface="compass", action=lambda: action)
    options = {"repo_root": tmp_path, "step": step, "runtime_mode": "auto", "run_impl": None}
    ordinary = sync._run_dashboard_refresh_step(**options)
    observed = sync._run_dashboard_refresh_step(**options, include_action_results=True)
    assert ordinary == {"rc": 0, "fallback_used": False, "status": "passed", "next_command": "", "failed_step": ""}
    action["state"]["request_id"] = "mutated"
    assert observed.pop("action_result")["state"]["request_id"] == "original"
    assert observed == ordinary
