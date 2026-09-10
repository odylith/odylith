"""Private-fixture contracts for detached result replay and request custody."""

from __future__ import annotations

import json
from pathlib import Path
import signal
import subprocess
import sys
import time

import pytest

from odylith.runtime.domain_intelligence.greenfield_managed_mutation_boundary import (
    GreenfieldManagedMutationBusyError,
)
from odylith.runtime.domain_intelligence.greenfield_repository_lock import greenfield_repository_lock
from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance
from odylith.runtime.surfaces import compass_standup_brief_maintenance_worker as worker
from odylith.runtime.surfaces import compass_standup_brief_narrator as narrator


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def _fixture(root: Path) -> tuple[dict, dict]:
    facts = [
        {"id": f"F-{index}", "section_key": key, "kind": "checkpoint", "text": f"Verified {label.lower()} checkpoint."}
        for index, (key, label) in enumerate(narrator.STANDUP_BRIEF_SECTIONS)
    ]
    packet = {
        "version": "v1", "window": "24h", "scope": {"mode": "global"},
        "summary": {"freshness": {"bucket": "recent"}}, "facts": facts,
        "sections": [{"key": key, "label": label, "facts": [facts[index]]}
                     for index, (key, label) in enumerate(narrator.STANDUP_BRIEF_SECTIONS)],
    }
    fingerprint = narrator.standup_brief_fingerprint(fact_packet=packet)
    brief = {
        "schema_version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "status": "ready", "source": "provider", "fingerprint": fingerprint,
        "generated_utc": "2026-09-10T01:00:00Z",
        "sections": [{"key": key, "label": label, "bullets": [
            {"text": facts[index]["text"], "fact_ids": [facts[index]["id"]]}
        ]} for index, (key, label) in enumerate(narrator.STANDUP_BRIEF_SECTIONS)],
        "evidence_lookup": {fact["id"]: fact for fact in facts},
    }
    request = {
        "version": "v1", "generated_utc": brief["generated_utc"],
        "runtime_input_fingerprint": "runtime-one",
        "global": {"24h": {"fingerprint": fingerprint, "fact_packet": packet}}, "scoped": {},
    }
    _write(worker.maintenance_request_path(repo_root=root), request)
    _write(root / "odylith/compass/runtime/current.v1.json", {
        "generated_utc": request["generated_utc"],
        "runtime_contract": {"input_fingerprint": "runtime-one"},
        "standup_brief": {"24h": {"status": "unavailable", "fingerprint": fingerprint}},
        "standup_brief_scoped": {}, "digest": {}, "digest_scoped": {},
    })
    return request, brief


def _cache(root: Path, request: dict, brief: dict) -> bytes:
    _write(narrator.standup_brief_cache_path(repo_root=root), {
        "version": narrator.STANDUP_BRIEF_SCHEMA_VERSION,
        "entries": {brief["fingerprint"]: brief},
    })
    assert narrator.has_reusable_cached_brief(
        repo_root=root, fact_packet=request["global"]["24h"]["fact_packet"],
    )
    return narrator.standup_brief_cache_path(repo_root=root).read_bytes()


def _forbid_provider(**_kwargs):
    raise AssertionError("ready cache replay consulted provider availability")


def test_exact_cache_replays_before_provider_availability(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    cache_bytes = _cache(tmp_path, request, brief)
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", _forbid_provider)
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["patched_current_runtime"] is True
    assert result["request_retained"] is False
    current = json.loads((tmp_path / "odylith/compass/runtime/current.v1.json").read_text())
    assert current["standup_brief"]["24h"]["sections"] == brief["sections"]
    assert current["standup_brief"]["24h"]["source"] == "cache"
    assert narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes() == cache_bytes


@pytest.mark.parametrize("failure", [GreenfieldManagedMutationBusyError, RuntimeError])
def test_failed_application_retains_computed_cache_and_original_request(tmp_path, monkeypatch, failure):
    request, brief = _fixture(tmp_path)
    request_path = worker.maintenance_request_path(repo_root=tmp_path)
    original = request_path.read_bytes()
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())

    def compute(**_kwargs):
        _cache(tmp_path, request, brief)
        return {"global": {"24h": brief}, "scoped": {}}

    monkeypatch.setattr(maintenance.compass_standup_brief_batch, "build_brief_bundle", compute)
    actual_patch = maintenance._patch_current_runtime_payload

    def fail(**_kwargs):
        raise failure("publication unavailable")

    monkeypatch.setattr(maintenance, "_patch_current_runtime_payload", fail)
    try:
        maintenance.run_pending_request(repo_root=tmp_path)
    except failure:
        pass
    assert request_path.exists(), "finally deleted the request before publication succeeded"
    assert request_path.read_bytes() == original
    cache_bytes = narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes()
    monkeypatch.setattr(maintenance, "_patch_current_runtime_payload", actual_patch)
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", _forbid_provider)
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["patched_current_runtime"] is True
    assert narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes() == cache_bytes


@pytest.mark.parametrize("apply_fails", [False, True])
def test_new_foreground_request_survives_old_worker_cleanup(tmp_path, monkeypatch, apply_fails):
    request, brief = _fixture(tmp_path)
    newer = {**request, "generated_utc": "2026-09-10T02:00:00Z", "runtime_input_fingerprint": "runtime-two"}
    request_path = worker.maintenance_request_path(repo_root=tmp_path)
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())

    def compute(**_kwargs):
        _write(request_path, newer)
        return {"global": {"24h": brief}, "scoped": {}}

    def publish(**_kwargs):
        if apply_fails:
            raise RuntimeError("publication failed")
        return True

    monkeypatch.setattr(maintenance.compass_standup_brief_batch, "build_brief_bundle", compute)
    monkeypatch.setattr(maintenance, "_patch_current_runtime_payload", publish)
    try:
        maintenance.run_pending_request(repo_root=tmp_path)
    except RuntimeError:
        pass
    assert request_path.exists(), "old cleanup removed newer foreground request"
    assert json.loads(request_path.read_text()) == newer


def test_actual_busy_admission_replays_cache_without_provider_work(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    cache_bytes = _cache(tmp_path, request, brief)
    request_path = worker.maintenance_request_path(repo_root=tmp_path)
    request_bytes = request_path.read_bytes()
    current_path = tmp_path / "odylith/compass/runtime/current.v1.json"
    current_bytes = current_path.read_bytes()
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", _forbid_provider)
    with greenfield_repository_lock(tmp_path):
        result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["publication_status"] == "busy"
    assert result["request_retained"] is True
    assert current_path.read_bytes() == current_bytes
    assert request_path.read_bytes() == request_bytes
    assert narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes() == cache_bytes
    assert worker.load_state(repo_root=tmp_path)["entries"]["global:24h"]["status"] == "ready"
    assert maintenance.run_pending_request(repo_root=tmp_path)["patched_current_runtime"] is True


def test_newer_unresolved_request_is_not_rewritten_with_old_failed_slots(tmp_path, monkeypatch):
    request, _brief = _fixture(tmp_path)
    request_path = worker.maintenance_request_path(repo_root=tmp_path)
    newer = {**request, "runtime_input_fingerprint": "newer", "global": {},
             "scoped": {"48h": {"B-702": {"fingerprint": "new-facts", "fact_packet": {"scope": "new"}}}}}
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())

    def compute(**_kwargs):
        worker.replace_request(repo_root=tmp_path, payload=newer)
        return {"global": {}, "scoped": {}}

    monkeypatch.setattr(maintenance.compass_standup_brief_batch, "build_brief_bundle", compute)
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["request_retained"] is True
    assert json.loads(request_path.read_text()) == newer


def test_backoff_failure_application_reuses_recorded_diagnostics(tmp_path, monkeypatch):
    request, _brief = _fixture(tmp_path)
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: None)
    patch = maintenance._patch_current_runtime_payload

    def busy(**_kwargs):
        raise GreenfieldManagedMutationBusyError("occupied")

    monkeypatch.setattr(maintenance, "_patch_current_runtime_payload", busy)
    assert maintenance.run_pending_request(repo_root=tmp_path)["publication_status"] == "busy"
    original = worker.load_state(repo_root=tmp_path)["entries"]["global:24h"]
    monkeypatch.setattr(maintenance, "_patch_current_runtime_payload", patch)
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["patched_current_runtime"] is True
    assert result["request_retained"] is True
    assert worker.load_state(repo_root=tmp_path)["entries"]["global:24h"] == original
    current = json.loads((tmp_path / "odylith/compass/runtime/current.v1.json").read_text())
    diagnostics = current["standup_brief"]["24h"]["diagnostics"]
    assert diagnostics["provider_failure_code"] == "provider_unavailable"
    assert diagnostics["next_retry_utc"] == original["next_retry_utc"]


def test_scoped_exact_cache_does_not_get_downgraded_by_unavailable_global_provider(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    cache_bytes = _cache(tmp_path, request, brief)
    scoped = request["global"]["24h"]
    request = {**request, "global": {"48h": {"fingerprint": "uncached", "fact_packet": {"scope": "new"}}},
               "scoped": {"24h": {"B-702": scoped}}}
    worker.replace_request(repo_root=tmp_path, payload=request)
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: None)
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["warmed"] == 1
    assert result["failed"] == 1
    current = json.loads((tmp_path / "odylith/compass/runtime/current.v1.json").read_text())
    assert current["standup_brief_scoped"]["24h"]["B-702"]["sections"] == brief["sections"]
    pending = json.loads(worker.maintenance_request_path(repo_root=tmp_path).read_text())
    assert pending["global"] == request["global"]
    assert pending["scoped"] == {}
    assert narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes() == cache_bytes


def test_same_window_cached_scope_and_new_provider_scope_both_publish(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    _cache(tmp_path, request, brief)
    cached = request["global"]["24h"]
    request = {**request, "global": {}, "scoped": {"24h": {
        "B-702": cached, "B-703": {"fingerprint": "new-facts", "fact_packet": {"scope": "new"}},
    }}}
    worker.replace_request(repo_root=tmp_path, payload=request)
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance.compass_standup_brief_batch, "build_brief_bundle", lambda **_kwargs: {
        "global": {}, "scoped": {"24h": {"B-703": {**brief, "fingerprint": "new-facts"}}},
    })
    result = maintenance.run_pending_request(repo_root=tmp_path)
    assert result["warmed"] == 2
    current = json.loads((tmp_path / "odylith/compass/runtime/current.v1.json").read_text())
    assert set(current["standup_brief_scoped"]["24h"]) == {"B-702", "B-703"}
    assert current["standup_brief_scoped"]["24h"]["B-702"]["source"] == "cache"
    assert current["standup_brief_scoped"]["24h"]["B-703"]["source"] == "provider"


def test_actual_busy_skipped_result_replays_without_provider_and_then_drains(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    monkeypatch.setattr(maintenance, "_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", lambda **_kwargs: object())
    monkeypatch.setattr(maintenance.compass_standup_brief_batch, "build_brief_bundle", lambda **_kwargs: {
        "global": {"24h": {"status": "unavailable", "source": "unavailable", "fingerprint": brief["fingerprint"],
                           "diagnostics": {"reason": "skipped_not_worth_calling"}}}, "scoped": {},
    })
    with greenfield_repository_lock(tmp_path):
        first = maintenance.run_pending_request(repo_root=tmp_path)
    assert first["publication_status"] == "busy"
    assert first["request_retained"] is True
    assert worker.load_state(repo_root=tmp_path)["entries"]["global:24h"]["status"] == "skipped"
    monkeypatch.setattr(maintenance, "_provider_for_cheap_config", _forbid_provider)
    second = maintenance.run_pending_request(repo_root=tmp_path)
    assert second["request_retained"] is False
    assert second["patched_current_runtime"] is True
    current = json.loads((tmp_path / "odylith/compass/runtime/current.v1.json").read_text())
    assert current["standup_brief"]["24h"]["diagnostics"]["reason"] == "skipped_not_worth_calling"


def test_private_child_worker_retains_busy_request_and_exits_before_replacement(tmp_path, monkeypatch):
    request, brief = _fixture(tmp_path)
    cache_bytes = _cache(tmp_path, request, brief)
    with greenfield_repository_lock(tmp_path):
        child = subprocess.Popen(
            [sys.executable, "-m", "odylith.runtime.surfaces.compass_standup_brief_maintenance",
             "--repo-root", str(tmp_path)],
            env=worker.worker_env(), stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        )
        try:
            deadline = time.monotonic() + 5.0
            state = {}
            while time.monotonic() < deadline and child.poll() is None:
                state = worker.load_state(repo_root=tmp_path)
                if state.get("entries", {}).get("global:24h", {}).get("status") == "ready":
                    break
                time.sleep(0.02)
            assert child.poll() is None
            assert state["active_pid"] == child.pid
            assert state["entries"]["global:24h"]["status"] == "ready"
            # This test owns the child, so polling also performs its parent's wait/reap.
            monkeypatch.setattr(worker, "pid_alive", lambda pid: pid == child.pid and child.poll() is None)
            assert worker.terminate_worker(child.pid, repo_root=tmp_path) is True
            assert child.wait(timeout=2) == -signal.SIGTERM
        finally:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=2)
    assert json.loads(worker.maintenance_request_path(repo_root=tmp_path).read_text()) == request
    assert narrator.standup_brief_cache_path(repo_root=tmp_path).read_bytes() == cache_bytes
