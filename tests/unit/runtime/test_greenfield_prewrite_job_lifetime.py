"""Transient compilation must not own detached Compass narration jobs."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence.greenfield_prewrite_stage_root import (
    staged_greenfield_prewrite_root,
)
from odylith.runtime.surfaces import compass_refresh_contract as contract
from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance


def _enqueue(root: Path) -> dict:
    return maintenance.enqueue_request(
        repo_root=root,
        generated_utc="2026-09-07T00:00:00Z",
        runtime_input_fingerprint="compiled-input",
        global_fact_packets={"24h": {"window": "24h"}},
        global_briefs={},
        scoped_fact_packets={},
        scoped_briefs={},
        scope_signals={},
    )


def test_prewrite_does_not_enqueue_background_narration(tmp_path: Path) -> None:
    with staged_greenfield_prewrite_root(tmp_path) as stage:
        assert _enqueue(stage) == {}
        assert not maintenance.maintenance_request_path(repo_root=stage).exists()


def test_prewrite_does_not_launch_existing_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_DISABLE", raising=False)
    monkeypatch.setenv("ODYLITH_COMPASS_STANDUP_BACKGROUND_ALLOW_IN_TESTS", "1")
    monkeypatch.setattr(maintenance, "_maintenance_worker_pids", lambda **_: [])
    monkeypatch.setattr(maintenance, "_pid_alive", lambda _: False)
    monkeypatch.setattr(maintenance, "_worker_epoch", lambda **_: "test-epoch")
    calls = []

    def spawn(*args, **kwargs):
        calls.append((args, kwargs))
        return SimpleNamespace(pid=4242)

    with staged_greenfield_prewrite_root(tmp_path) as stage:
        request = maintenance.maintenance_request_path(repo_root=stage)
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(
            '{"global":{"24h":{"fingerprint":"staged-input","fact_packet":{"window":"24h"}}}}',
            encoding="utf-8",
        )
        monkeypatch.setattr(maintenance.subprocess, "Popen", spawn)
        assert maintenance.maybe_spawn_background(repo_root=stage) == 0
        assert calls == []

    assert _enqueue(tmp_path)
    assert maintenance.maybe_spawn_background(repo_root=tmp_path) == 4242
    assert len(calls) == 1
    assert calls[0][1]["cwd"] == str(tmp_path)


def test_transient_refresh_lifetime_is_root_scoped_nested_and_exception_safe(tmp_path: Path) -> None:
    stage = tmp_path / "staged"
    live = tmp_path / "live"
    with pytest.raises(RuntimeError, match="stop compilation"):
        with contract.transient_refresh_root(repo_root=stage):
            with contract.transient_refresh_root(repo_root=stage):
                assert not contract.background_maintenance_allowed(repo_root=stage)
                assert contract.background_maintenance_allowed(repo_root=live)
            assert not contract.background_maintenance_allowed(repo_root=stage)
            with ThreadPoolExecutor(max_workers=1) as pool:
                assert not pool.submit(contract.background_maintenance_allowed, repo_root=stage).result()
            raise RuntimeError("stop compilation")
    assert contract.background_maintenance_allowed(repo_root=stage)
