"""Actual Compass result application obeys repository publication custody."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from odylith.runtime.domain_intelligence import greenfield_generation_state as state
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as mutations
from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff as views
from odylith.runtime.domain_intelligence import greenfield_repository_lock as locks
from odylith.runtime.domain_intelligence import greenfield_repository_write_set as write_sets
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import compass_standup_brief_maintenance as maintenance
from odylith.runtime.surfaces import compass_standup_brief_maintenance_worker as worker
from odylith.runtime.surfaces import compass_standup_brief_runtime_patch as briefs
from tests.unit.runtime.test_greenfield_generation_store import _publish


JSON_PATH = "odylith/compass/runtime/current.v1.json"
JS_PATH = "odylith/compass/runtime/current.v1.js"
GENERATED = "2026-03-03T12:00:00Z"
FINGERPRINT = "f" * 64
FAILURE = {
    "status": "unavailable", "source": "unavailable", "sections": [],
    "diagnostics": {"reason": "provider_error", "next_retry_utc": "2026-03-03T13:00:00Z"},
}


@pytest.fixture(autouse=True)
def no_provider_calls(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Applying an already computed Compass result must not call a provider")

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", forbidden)


@pytest.fixture
def published_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    current = repo / JSON_PATH
    current.parent.mkdir(parents=True)
    payload = {
        "generated_utc": GENERATED,
        "runtime_contract": {"input_fingerprint": FINGERPRINT},
        "standup_brief": {"24h": {"status": "unavailable", "sections": []}},
        "digest": {"24h": []}, "standup_brief_scoped": {}, "digest_scoped": {},
    }
    current.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    (repo / JS_PATH).write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (repo / "odylith/index.html").write_text("<!doctype html><title>Complete fixture</title>\n", encoding="utf-8")
    write_set = write_sets.compile_greenfield_repository_write_set(source_root=repo, staged_root=repo)
    baseline = generations.materialize_immutable_greenfield_generation(
        repo_root=repo, write_set=write_set,
        manifest_text=generations.compile_greenfield_generation_manifest(write_set),
    )
    _publish(repo, baseline, write_set)
    assert generations.require_greenfield_working_generation(repo).write_set_hash == baseline.write_set_hash
    return repo, baseline


def _patch(repo: Path, *, fingerprint: str = FINGERPRINT, generated: str = GENERATED, changed: bool = True) -> bool:
    return briefs.patch_current_runtime_payload(
        repo_root=repo, runtime_input_fingerprint=fingerprint, runtime_generated_utc=generated,
        global_results={}, scoped_results={}, global_failures={"24h": FAILURE} if changed else {},
    )


def _files(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        name: ((root / name).read_bytes(), (root / name).stat().st_mode)
        for name in ("odylith/index.html", JSON_PATH, JS_PATH)
    }


def _immutable_files(generation) -> dict[str, bytes]:
    return {
        path.relative_to(generation.generation_root).as_posix(): path.read_bytes()
        for path in generation.generation_root.rglob("*") if path.is_file()
    }


def test_actual_patcher_cannot_write_under_another_process_repository_lock(published_repo) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    immutable = _immutable_files(baseline)
    child_code = """
import json, sys
from pathlib import Path
from unittest.mock import patch
from odylith.runtime.domain_intelligence.greenfield_managed_mutation_boundary import GreenfieldManagedMutationBusyError
from odylith.runtime.domain_intelligence.greenfield_repository_lock import GreenfieldRepositoryBusyError
from tests.unit.runtime.test_compass_brief_publication import _patch, odylith_reasoning
with patch.object(odylith_reasoning, 'provider_from_config', side_effect=AssertionError('provider call')):
    try:
        changed = _patch(Path(sys.argv[1]))
    except (GreenfieldManagedMutationBusyError, GreenfieldRepositoryBusyError):
        changed = False
print(json.dumps({'changed': changed}))
"""
    with locks.greenfield_repository_lock(repo):
        result = subprocess.run(
            [sys.executable, "-B", "-c", child_code, str(repo)],
            capture_output=True, text=True, check=True, timeout=10,
        )
        assert _files(repo) == before, "A child patched managed bytes outside repository writer custody"
    assert json.loads(result.stdout)["changed"] is False
    assert _immutable_files(baseline) == immutable
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == baseline.write_set_hash


def test_successful_actual_patch_publishes_matching_successor_and_retains_old_view(published_repo) -> None:
    repo, baseline = published_repo
    immutable = _immutable_files(baseline)

    assert _patch(repo) is True

    successor = generations.pin_active_greenfield_generation(repo)
    assert successor.write_set_hash != baseline.write_set_hash, "The completed Compass patch was not published"
    assert generations.require_greenfield_working_generation(repo).write_set_hash == successor.write_set_hash
    assert views.canonical_current_project_root(repo) == (successor.repository_root, "active_generation")
    for name in (JSON_PATH, JS_PATH):
        assert (successor.repository_root / name).read_bytes() == (repo / name).read_bytes()
    assert json.loads((successor.repository_root / JSON_PATH).read_text())["standup_brief"]["24h"] == FAILURE
    assert _immutable_files(baseline) == immutable


def test_identical_result_does_not_publish_an_additional_generation(published_repo) -> None:
    repo, baseline = published_repo
    immutable = _immutable_files(baseline)
    assert _patch(repo) is True
    before = _files(repo)
    identity = state.active_generation_identity(repo)

    assert _patch(repo) is False

    assert _files(repo) == before
    assert state.active_generation_identity(repo) == identity
    assert _immutable_files(baseline) == immutable


@pytest.mark.parametrize("kind", ["empty_results", "wrong_fingerprint", "wrong_timestamp"])
def test_noop_or_stale_result_keeps_published_and_working_bytes(published_repo, kind: str) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    immutable = _immutable_files(baseline)
    identity = state.active_generation_identity(repo)

    assert _patch(
        repo, changed=kind != "empty_results",
        fingerprint="x" * 64 if kind == "wrong_fingerprint" else FINGERPRINT,
        generated="2026-03-03T11:59:59Z" if kind == "wrong_timestamp" else GENERATED,
    ) is False

    assert _files(repo) == before
    assert state.active_generation_identity(repo) == identity
    assert _immutable_files(baseline) == immutable
    assert generations.require_greenfield_working_generation(repo).write_set_hash == baseline.write_set_hash


@pytest.mark.parametrize("failed_path", [JSON_PATH, JS_PATH])
def test_failed_runtime_pair_keeps_old_canonical_generation_and_failure_evidence(
    published_repo, monkeypatch, failed_path: str,
) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    immutable = _immutable_files(baseline)
    identity = state.active_generation_identity(repo)
    actual_write = briefs.odylith_context_cache.write_text_if_changed
    writes = []

    def failing_write(*, repo_root, path, **kwargs):
        writes.append(Path(path).relative_to(repo_root).as_posix())
        if Path(path) == repo / failed_path:
            raise OSError("controlled runtime pair failure")
        return actual_write(repo_root=repo_root, path=path, **kwargs)

    monkeypatch.setattr(briefs.odylith_context_cache, "write_text_if_changed", failing_write)
    with pytest.raises(OSError, match="controlled runtime pair failure"):
        _patch(repo)

    assert writes == ([JSON_PATH] if failed_path == JSON_PATH else [JSON_PATH, JS_PATH])
    assert state.active_generation_identity(repo) == identity
    assert views.canonical_current_project_root(repo) == (baseline.repository_root, "active_generation")
    assert _immutable_files(baseline) == immutable
    assert (repo / "odylith/index.html").read_bytes() == before["odylith/index.html"][0]
    assert (repo / JS_PATH).read_bytes() == before[JS_PATH][0]
    if failed_path == JS_PATH:
        assert json.loads((repo / JSON_PATH).read_text())["standup_brief"]["24h"] == FAILURE
        with pytest.raises(generations.GreenfieldWorkingGenerationDriftError):
            generations.require_greenfield_working_generation(repo)
    else:
        assert _files(repo) == before


def test_busy_admission_precedes_any_current_payload_read(published_repo, monkeypatch) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    reads = []
    actual_load = briefs._load_json

    def tracked_load(path):
        reads.append(Path(path))
        return actual_load(path)

    monkeypatch.setattr(briefs, "_load_json", tracked_load)
    with locks.greenfield_repository_lock(repo):
        with pytest.raises(mutations.GreenfieldManagedMutationBusyError):
            _patch(repo)

    assert reads == []
    assert _files(repo) == before
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == baseline.write_set_hash


def test_current_payload_read_occurs_after_baseline_admission_under_lock(published_repo, monkeypatch) -> None:
    repo, _baseline = published_repo
    events = []
    actual_admit = generations.require_greenfield_working_generation
    actual_load = briefs._load_json

    def admitted(root):
        result = actual_admit(root)
        events.append("admitted")
        return result

    def read_under_custody(path):
        assert events == ["admitted"]
        with pytest.raises(locks.GreenfieldRepositoryBusyError):
            with locks.greenfield_repository_lock(repo):
                pytest.fail("Current payload was read without repository writer custody")
        events.append("current_read")
        return actual_load(path)

    monkeypatch.setattr(generations, "require_greenfield_working_generation", admitted)
    monkeypatch.setattr(briefs, "_load_json", read_under_custody)

    assert _patch(repo) is True

    assert events == ["admitted", "current_read"]


@pytest.mark.parametrize("failure_stage", ["after_image_materialization", "publication_switch"])
def test_failed_successor_preserves_old_canonical_and_computed_evidence(
    published_repo, monkeypatch, failure_stage: str,
) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    immutable = _immutable_files(baseline)
    identity = state.active_generation_identity(repo)
    cache = briefs.compass_standup_brief_narrator.standup_brief_cache_path(repo_root=repo)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(json.dumps({"entries": {FINGERPRINT: {"sections": [], "source": "cache"}}}) + "\n")
    cache.chmod(0o640)
    cache_before = (cache.read_bytes(), cache.stat().st_mode)
    attempted = []
    materialized = []
    actual_materialize = generations.materialize_immutable_greenfield_generation

    def record_materialized(**kwargs):
        candidate = actual_materialize(**kwargs)
        materialized.append(candidate)
        return candidate

    monkeypatch.setattr(generations, "materialize_immutable_greenfield_generation", record_materialized)
    if failure_stage == "after_image_materialization":
        actual_after_image = write_sets.materialize_compiled_greenfield_after_image

        def fail_after_image(**kwargs):
            actual_after_image(**kwargs)
            destination = kwargs["destination_root"]
            for name in (JSON_PATH, JS_PATH):
                assert (destination / name).read_bytes() == (repo / name).read_bytes()
            attempted.append("after_image_materialization")
            raise OSError("controlled successor materialization failure")

        monkeypatch.setattr(write_sets, "materialize_compiled_greenfield_after_image", fail_after_image)
    else:
        def fail_publication_switch(path, content):
            assert Path(path) == repo / "odylith/index.html"
            assert materialized and materialized[0].write_set_hash in content
            attempted.append("publication_switch")
            raise OSError("controlled successor publication failure")

        monkeypatch.setattr(state, "atomic_write_text", fail_publication_switch)

    with pytest.raises(OSError, match="controlled successor"):
        _patch(repo)

    assert attempted == [failure_stage]
    assert state.active_generation_identity(repo) == identity
    assert views.canonical_current_project_root(repo) == (baseline.repository_root, "active_generation")
    assert _immutable_files(baseline) == immutable
    assert (repo / "odylith/index.html").read_bytes() == before["odylith/index.html"][0]
    assert (repo / "odylith/index.html").stat().st_mode == before["odylith/index.html"][1]
    assert (cache.read_bytes(), cache.stat().st_mode) == cache_before
    current = json.loads((repo / JSON_PATH).read_text())
    assert current["standup_brief"]["24h"] == FAILURE
    assert (repo / JS_PATH).read_text() == "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(current, separators=(",", ":")) + ";\n"
    with pytest.raises(generations.GreenfieldWorkingGenerationDriftError):
        generations.require_greenfield_working_generation(repo)
    if failure_stage == "publication_switch":
        assert len(materialized) == 1
        candidate = generations.pin_greenfield_generation(repo_root=repo, write_set_hash=materialized[0].write_set_hash)
        assert candidate.write_set_hash != baseline.write_set_hash
        for name in (JSON_PATH, JS_PATH):
            assert (candidate.repository_root / name).read_bytes() == (repo / name).read_bytes()


@pytest.mark.parametrize("request_present", [False, True])
def test_inline_stamp_and_pure_projection_need_no_nested_writer(
    published_repo, monkeypatch, request_present: bool,
) -> None:
    repo, baseline = published_repo
    before = _files(repo)
    payload = json.loads((repo / JSON_PATH).read_text())
    payload["standup_brief"]["24h"]["fingerprint"] = "computed-fact"
    unmodified_payload = json.loads(json.dumps(payload))
    entries = {"global:24h": {"fingerprint": "computed-fact", "status": "skipped",
                              "diagnostics": {"reason": "skipped_not_worth_calling"}}}
    monkeypatch.setattr(worker, "load_state", lambda **kwargs: {"entries": entries})

    def no_nested_writer(**kwargs):
        pytest.fail("Inline stamp must not enter the detached result writer")

    monkeypatch.setattr(briefs, "patch_current_runtime_payload", no_nested_writer)
    request = worker.maintenance_request_path(repo_root=repo)
    if request_present:
        request.parent.mkdir(parents=True, exist_ok=True)
        request.write_text(json.dumps({"global": {"24h": {"fingerprint": "computed-fact", "fact_packet": {"fixture": True}}}}))

    with locks.greenfield_repository_lock(repo):
        maintenance.stamp_request_runtime_input_fingerprint(repo_root=repo, runtime_input_fingerprint=FINGERPRINT)
        projected = maintenance.apply_terminal_state_to_runtime_payload(
            repo_root=repo, payload=payload, runtime_input_fingerprint=FINGERPRINT,
        )

    assert projected["standup_brief"]["24h"]["diagnostics"]["reason"] == "skipped_not_worth_calling"
    assert payload == unmodified_payload
    assert _files(repo) == before
    assert generations.require_greenfield_working_generation(repo).write_set_hash == baseline.write_set_hash
    if request_present:
        assert json.loads(request.read_text())["runtime_input_fingerprint"] == FINGERPRINT
    else:
        assert not request.exists()


def test_obsolete_public_terminal_file_writer_is_absent() -> None:
    assert not hasattr(briefs, "patch_current_runtime_from_terminal_state")
