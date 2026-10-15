"""Regression coverage for intervention event-stream state helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from odylith.runtime.context_engine import memory_record_policy
from odylith.runtime.intervention_engine import stream_state
from odylith.runtime.intervention_engine import continuity_runtime, delivery_ledger
from odylith.runtime.common import agent_runtime_contract, compass_host_events
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.surfaces import host_dirty_checkpoint
from tests.unit.runtime.test_greenfield_managed_mutation_boundary import _active_repository


class _OddObject:
    """Fixture object that forces metadata serialization onto the fallback path."""
    def __str__(self) -> str:
        return "odd-object"


def test_intervention_event_metadata_is_json_safe_and_cache_invalidates(tmp_path: Path) -> None:
    first = stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="First visible signal.",
        session_id="stream-meta",
        host_family="codex",
        display_markdown="**Odylith Insight:** First visible signal.",
        metadata={
            "set_payload": {"alpha", "beta"},
            "object_payload": _OddObject(),
            "nested": {"ok": True},
        },
    )
    rows_after_first = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="stream-meta",
    )
    second = stream_state.append_intervention_event(
        repo_root=tmp_path,
        kind="ambient_signal",
        summary="Second visible signal.",
        session_id="stream-meta",
        host_family="codex",
        display_markdown="**Odylith Insight:** Second visible signal.",
        metadata={"sequence": 2},
    )
    rows_after_second = stream_state.load_recent_intervention_events(
        repo_root=tmp_path,
        session_id="stream-meta",
    )

    assert first["metadata"]["object_payload"] == "odd-object"
    assert isinstance(first["metadata"]["set_payload"], str)
    assert first["metadata"]["nested"] == {"ok": True}
    assert second["metadata"] == {"sequence": 2}
    assert [row["summary"] for row in rows_after_first] == ["First visible signal."]
    assert [row["summary"] for row in rows_after_second] == [
        "First visible signal.",
        "Second visible signal.",
    ]


def test_intervention_event_rejects_unknown_kind_before_writing(tmp_path: Path) -> None:
    try:
        stream_state.append_intervention_event(
            repo_root=tmp_path,
            kind="debug_noise",
            summary="Should not write.",
        )
    except ValueError as exc:
        assert "unsupported intervention event kind" in str(exc)
    else:
        raise AssertionError("unsupported intervention event kind was accepted")

    assert stream_state.load_recent_intervention_events(repo_root=tmp_path) == []


def _pending_summary(root: Path, *, session="session-a", summary="The completed review still needs a clean gate.", stamp="2020-01-01T00:00:00Z") -> dict:
    event_id = host_dirty_checkpoint.record_compass_event(repo_root=root, event={
        "kind": "implementation", "summary": summary, "ts_iso": stamp,
        "session_id": session, "host_family": "codex", "source": "assistant",
    })
    return next(row for row in host_dirty_checkpoint.read_compass_events(repo_root=root) if row["id"] == event_id)


def test_session_memory_overlays_new_and_removed_pending_summary_on_warm_base(tmp_path, monkeypatch):
    calls = []
    original = stream_state.load_recent_intervention_events

    def counted(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(stream_state, "load_recent_intervention_events", counted)
    first = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert first["pending_summaries"] == [] and first["pending_summary_count"] == 0
    row = _pending_summary(tmp_path)
    other = _pending_summary(tmp_path, session="session-b", summary="Another session's claim must remain separate.")
    warm = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert [item["id"] for item in warm["pending_summaries"]] == [row["id"]]
    assert warm["pending_summary_count"] == 1 and warm["recent_event_count"] == 0
    assert len(calls) == 2
    base_key = (stream_state.event_cache_signature(repo_root=tmp_path), "session-a", 80)
    assert "pending_summaries" not in stream_state._SESSION_MEMORY_CACHE[base_key]
    assert [item["id"] for item in stream_state.session_memory_snapshot(
        repo_root=tmp_path, session_id="session-b",
    )["pending_summaries"]] == [other["id"]]
    assert stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="")["pending_summaries"] == []

    # Simulate the queue after governed promotion; a cached base must not resurrect it.
    host_dirty_checkpoint.event_store_path(tmp_path).write_text("")
    cleared = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert cleared["pending_summaries"] == [] and cleared["pending_summary_count"] == 0
    assert not cleared["pending_memory_error"]


def test_session_memory_bounds_rows_after_session_filter_without_clipping_summary(tmp_path):
    complete = "This sentence retains the exact source claim for later verification. " * 20 + "The release proof is pending."
    own = [_pending_summary(tmp_path, summary=complete + f" Item {n}.") for n in range(6)]
    for n in range(5):
        _pending_summary(tmp_path, session="session-b", stamp="2026-10-15T00:00:00Z", summary=f"Other-session claim {n}.")
    path = host_dirty_checkpoint.event_store_path(tmp_path)
    before = path.read_bytes()
    value = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert value["pending_summary_count"] == 4
    assert [row["id"] for row in value["pending_summaries"]] == [row["id"] for row in reversed(own[-4:])]
    for actual, expected in zip(value["pending_summaries"], reversed(own[-4:])):
        assert actual["summary"] == expected["event"]["summary"]
        assert actual["event"] == expected["event"]
        assert actual["session_id"] == expected["session_id"]
    assert path.read_bytes() == before
    assert len(host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)) == 11


def test_session_memory_pending_claim_keeps_original_age_and_unknown_authority(tmp_path):
    row = _pending_summary(tmp_path)
    first = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")["pending_summaries"][0]
    second = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")["pending_summaries"][0]
    assert first == second
    assert second["id"] == row["id"] and second["ts_iso"] == row["event"]["ts_iso"]
    assert second["recorded_utc"] == row["recorded_utc"]
    memory = second["memory_record"]
    assert memory["evidence_utc"] == row["event"]["ts_iso"]
    assert memory["observed_utc"] == row["recorded_utc"] and not memory["confirmed_utc"]
    assert second["authority"] == "unknown" and second["trust"] == "unverified"
    assert memory["role"] == "historical_learning" and memory["validity"] == "unknown"
    admission = memory_record_policy.assess(memory)
    assert admission["current_authority"] is False and admission["reason"] == "unknown_authority"
    assert admission["freshness"] == "cold"


@pytest.mark.parametrize("corruption", ["invalid_json", "invalid_session", "invalid_timestamp"])
def test_session_memory_corrupt_pending_queue_is_explicit_and_not_cached(tmp_path, corruption):
    row = _pending_summary(tmp_path)
    before = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert before["pending_summary_count"] == 1
    path = host_dirty_checkpoint.event_store_path(tmp_path)
    retained = path.read_bytes()
    if corruption == "invalid_json":
        path.write_text("{unfinished\n")
    else:
        if corruption == "invalid_session":
            row["event"]["session_id"] = "not-the-envelope-session"
        else:
            row["event"]["ts_iso"] = "not-a-timestamp"
        path.write_text(json.dumps(row) + "\n")
    corrupt = path.read_bytes()
    value = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert value["pending_summaries"] == [] and value["pending_summary_count"] == 0
    assert "unverified" in value["pending_memory_error"]
    assert path.read_bytes() == corrupt
    path.write_bytes(retained)
    recovered = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="session-a")
    assert recovered["pending_summary_count"] == 1 and not recovered["pending_memory_error"]


@pytest.mark.parametrize("kind", sorted(stream_state._INTERVENTION_EVENT_KINDS))
def test_unadmitted_intervention_keeps_active_canonical_generation_healthy(tmp_path, kind):
    repo, _ = _active_repository(tmp_path)
    selected = generations.require_greenfield_working_generation(repo)
    path = repo / agent_runtime_contract.AGENT_STREAM_PATH
    before = path.read_bytes() if path.exists() else None
    payload = stream_state.append_intervention_event(
        repo_root=repo, kind=kind, summary="Native PostToolUse retains its exact event.",
        session_id="post-tool-session", host_family="codex", turn_phase="checkpoint",
        intervention_key="native-moment", semantic_signature=["native-proof"],
        render_surface="codex_post_bash_checkpoint", delivery_status="assistant_render_required",
    )
    assert (path.read_bytes() if path.exists() else None) == before
    assert generations.require_greenfield_working_generation(repo).write_set_hash == selected.write_set_hash
    row, = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    assert {key: value for key, value in row["event"].items() if key != "transaction_id"} == payload
    assert stream_state.load_recent_intervention_events(repo_root=repo, session_id="post-tool-session") == [row["event"]]
    assert stream_state.load_recent_intervention_events(repo_root=repo, include_pending=False) == []
    assert stream_state.load_recent_intervention_events(repo_root=repo, session_id="another-session") == []


def test_real_admitted_writer_appends_and_publishes_intervention(tmp_path):
    repo, _ = _active_repository(tmp_path)
    previous = generations.require_greenfield_working_generation(repo)
    assert not boundary.canonical_event_writer_admitted(repo)

    def operation(descriptor):
        assert descriptor is not None and boundary.canonical_event_writer_admitted(repo)
        event = stream_state.append_intervention_event(
            repo_root=repo, kind="ambient_signal", summary="A real admitted writer records this event.",
            session_id="admitted-session", host_family="codex",
        )
        assert stream_state.load_recent_intervention_events(repo_root=repo) == [event]
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-intervention-writer"], operation=operation,
    ) == 0
    selected = generations.require_greenfield_working_generation(repo)
    assert selected.write_set_hash != previous.write_set_hash
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == []
    assert (selected.repository_root / agent_runtime_contract.AGENT_STREAM_PATH).read_bytes() == (repo / agent_runtime_contract.AGENT_STREAM_PATH).read_bytes()
    assert stream_state.event_cache_signature(repo_root=repo)[0][0] == (
        selected.repository_root / agent_runtime_contract.AGENT_STREAM_PATH
    ).as_posix()
    assert not boundary.canonical_event_writer_admitted(repo)


@pytest.mark.parametrize("failure", ["nonzero", "exception"])
def test_failed_admitted_append_is_invisible_outside_selected_publication(tmp_path, failure):
    repo, _ = _active_repository(tmp_path)
    selected = generations.pin_active_greenfield_generation(repo)
    published_entry = (repo / "odylith/index.html").read_bytes()
    before = stream_state.event_cache_signature(repo_root=repo)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == []
    assert stream_state.pending_proposal_state(repo_root=repo)["pending_count"] == 0

    def operation(descriptor):
        assert descriptor is not None and boundary.canonical_event_writer_admitted(repo)
        event = stream_state.append_intervention_event(
            repo_root=repo, kind="capture_proposed", summary="This failed writer has no published event.",
            session_id="failed-session", host_family="codex", intervention_key="failed-moment",
            semantic_signature=["unpublished-proof"],
        )
        assert stream_state.load_recent_intervention_events(repo_root=repo) == [event]
        assert stream_state.event_cache_signature(repo_root=repo) != before
        if failure == "exception":
            raise RuntimeError("admitted writer failed")
        return 1

    if failure == "exception":
        with pytest.raises(RuntimeError, match="admitted writer failed"):
            boundary.run_with_greenfield_managed_mutation_boundary(
                repo_root=repo, command_tokens=["fixture-failed-writer"], operation=operation,
            )
    else:
        assert boundary.run_with_greenfield_managed_mutation_boundary(
            repo_root=repo, command_tokens=["fixture-failed-writer"], operation=operation,
        ) == 1
    assert not boundary.canonical_event_writer_admitted(repo)
    assert (repo / "odylith/index.html").read_bytes() == published_entry
    assert generations.pin_active_greenfield_generation(repo).write_set_hash == selected.write_set_hash
    assert json.loads((repo / agent_runtime_contract.AGENT_STREAM_PATH).read_text())["intervention_key"] == "failed-moment"
    assert stream_state.event_cache_signature(repo_root=repo) == before
    assert stream_state.load_recent_intervention_events(repo_root=repo) == []
    assert stream_state.pending_proposal_state(repo_root=repo)["pending_count"] == 0
    assert delivery_ledger.delivery_snapshot(repo_root=repo, session_id="failed-session")["event_count"] == 0
    assert stream_state.session_memory_snapshot(repo_root=repo, session_id="failed-session")["recent_event_count"] == 0
    assert not continuity_runtime.moment_continuity_snapshot(
        repo_root=repo, session_id="failed-session", moment_key="failed-moment",
    )["proposal_pending"]

    stream_state.append_intervention_event(
        repo_root=repo, kind="capture_proposed", summary="The next native event remains available from the inbox.",
        session_id="failed-session", host_family="codex", intervention_key="queued-moment",
    )
    row, = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == [row["event"]]
    assert stream_state.pending_proposal_state(repo_root=repo)["pending_count"] == 1
    assert delivery_ledger.delivery_snapshot(repo_root=repo, session_id="failed-session")["event_count"] == 1
    assert stream_state.session_memory_snapshot(repo_root=repo, session_id="failed-session")["recent_event_count"] == 1
    assert continuity_runtime.moment_continuity_snapshot(
        repo_root=repo, session_id="failed-session", moment_key="queued-moment",
    )["proposal_pending"]


def test_read_only_boundary_cannot_admit_a_native_canonical_append(tmp_path):
    repo, _ = _active_repository(tmp_path)
    selected = generations.require_greenfield_working_generation(repo)

    def operation(descriptor):
        assert descriptor is None and not boundary.canonical_event_writer_admitted(repo)
        stream_state.append_intervention_event(
            repo_root=repo, kind="ambient_signal", summary="A read-only call cannot acquire event write authority.",
            session_id="read-only-session", host_family="claude",
        )
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["version"], operation=operation,
    ) == 0
    assert len(host_dirty_checkpoint.read_compass_events(repo_root=repo)) == 1
    assert generations.require_greenfield_working_generation(repo).write_set_hash == selected.write_set_hash


def test_custom_noncanonical_stream_keeps_direct_append_semantics(tmp_path, monkeypatch):
    repo, _ = _active_repository(tmp_path)
    target = repo / "custom-interventions.jsonl"
    monkeypatch.setattr(stream_state, "_agent_stream_path", lambda **kwargs: target)
    stream_state.append_intervention_event(
        repo_root=repo, kind="ambient_signal", summary="An explicit custom stream retains its contract.",
        session_id="custom-session", host_family="codex",
    )
    assert json.loads(target.read_text())["summary"] == "An explicit custom stream retains its contract."
    assert stream_state.load_recent_intervention_events(repo_root=repo)[0]["summary"] == "An explicit custom stream retains its contract."
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == []
    generations.require_greenfield_working_generation(repo)


def test_cross_process_pending_events_refresh_live_engines_and_deduplicate_publication(tmp_path):
    repo, _ = _active_repository(tmp_path)
    args = dict(repo_root=repo, session_id="cross-process", moment_key="queued-proposal")
    before = stream_state.event_cache_signature(repo_root=repo)
    assert stream_state.pending_proposal_state(repo_root=repo)["pending_count"] == 0
    assert continuity_runtime.moment_continuity_snapshot(**args)["proposal_pending"] is False
    assert delivery_ledger.delivery_snapshot(repo_root=repo, session_id="cross-process")["event_count"] == 0
    script = """
from pathlib import Path
import sys
from odylith.runtime.intervention_engine import stream_state
stream_state.append_intervention_event(repo_root=Path(sys.argv[1]), kind='capture_proposed',
 summary='A native checkpoint proposes one bounded follow-up.', session_id='cross-process',
 host_family='codex', intervention_key='queued-proposal', semantic_signature=['queued-proof'],
 display_markdown='A bounded proposal.', delivery_status='assistant_render_required')
"""
    subprocess.run([sys.executable, "-c", script, str(repo)], check=True)
    assert stream_state.event_cache_signature(repo_root=repo) != before
    record, = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    assert stream_state.pending_proposal_state(repo_root=repo)["pending_count"] == 1
    assert continuity_runtime.moment_continuity_snapshot(**args)["proposal_pending"] is True
    assert delivery_ledger.delivery_snapshot(repo_root=repo, session_id="cross-process")["event_count"] == 1
    assert stream_state.session_memory_snapshot(repo_root=repo, session_id="cross-process")["recent_event_count"] == 1

    def publish_exact(descriptor):
        path = repo / agent_runtime_contract.AGENT_STREAM_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(compass_host_events.event_bytes(record["event"]))
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-published-intervention"], operation=publish_exact,
    ) == 0
    generations.require_greenfield_working_generation(repo)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == [record["event"]]
    before_ack = stream_state.event_cache_signature(repo_root=repo)
    acknowledge = "from pathlib import Path; import sys; from odylith.runtime.common import compass_host_events; compass_host_events.acknowledge_retained(repo_root=Path(sys.argv[1]), event_id=sys.argv[2])"
    subprocess.run([sys.executable, "-c", acknowledge, str(repo), record["id"]], check=True)
    assert stream_state.event_cache_signature(repo_root=repo) != before_ack
    assert host_dirty_checkpoint.read_compass_events(repo_root=repo) == []
    assert stream_state.load_recent_intervention_events(repo_root=repo) == [record["event"]]
    memory = stream_state.session_memory_snapshot(repo_root=repo, session_id="cross-process")
    assert memory["pending_summary_count"] == 0 and memory["recent_event_count"] == 1


@pytest.mark.parametrize("publication_point", ["before_canonical_pick", "after_canonical_pick"])
def test_pending_snapshot_precedes_publication_pick_and_survives_publish_ack(tmp_path, monkeypatch, publication_point):
    repo, _ = _active_repository(tmp_path)
    old = generations.pin_active_greenfield_generation(repo)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == []
    stream_state.append_intervention_event(
        repo_root=repo, kind="capture_proposed", summary="This event remains visible through concurrent publication.",
        session_id="publication-race", host_family="codex", intervention_key="publication-race",
    )
    record, = host_dirty_checkpoint.read_compass_events(repo_root=repo)
    original_read = host_dirty_checkpoint.read_compass_events
    original_pick = stream_state._read_stream_path
    order = []
    selected = []

    def publish_and_ack():
        def publish_exact(descriptor):
            path = repo / agent_runtime_contract.AGENT_STREAM_PATH
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(compass_host_events.event_bytes(record["event"]))
            return 0

        assert boundary.run_with_greenfield_managed_mutation_boundary(
            repo_root=repo, command_tokens=["fixture-concurrent-publication"], operation=publish_exact,
        ) == 0
        compass_host_events.acknowledge_retained(repo_root=repo, event_id=record["id"])
        assert original_read(repo_root=repo) == []

    def read_pending(**kwargs):
        order.append("pending")
        return original_read(**kwargs)

    def pick_canonical(**kwargs):
        order.append("canonical")
        assert order[:2] == ["pending", "canonical"]
        if publication_point == "before_canonical_pick":
            publish_and_ack()
        path = original_pick(**kwargs)
        selected.append(path)
        if publication_point == "after_canonical_pick":
            publish_and_ack()
        return path

    monkeypatch.setattr(host_dirty_checkpoint, "read_compass_events", read_pending)
    monkeypatch.setattr(stream_state, "_read_stream_path", pick_canonical)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == [record["event"]]
    new = generations.pin_active_greenfield_generation(repo)
    assert new.write_set_hash != old.write_set_hash
    expected = new if publication_point == "before_canonical_pick" else old
    assert selected == [expected.repository_root / agent_runtime_contract.AGENT_STREAM_PATH]


def test_event_cache_signature_observes_inbox_before_canonical_selection(tmp_path, monkeypatch):
    repo, _ = _active_repository(tmp_path)
    ledger = host_dirty_checkpoint.event_store_path(repo)
    original_lstat = Path.lstat
    original_pick = stream_state._read_stream_path
    order = []

    def observe_inbox(path, *args, **kwargs):
        if path == ledger:
            order.append("pending_stat")
        return original_lstat(path, *args, **kwargs)

    def pick_canonical(**kwargs):
        order.append("canonical")
        assert order == ["pending_stat", "canonical"]
        return original_pick(**kwargs)

    monkeypatch.setattr(Path, "lstat", observe_inbox)
    monkeypatch.setattr(stream_state, "_read_stream_path", pick_canonical)
    stream_state.event_cache_signature(repo_root=repo)
    assert order == ["pending_stat", "canonical"]


def test_hot_stream_reads_and_signatures_do_not_scan_managed_trees(tmp_path, monkeypatch):
    repo, _ = _active_repository(tmp_path)
    events = []

    def publish_event(descriptor):
        events.append(stream_state.append_intervention_event(
            repo_root=repo, kind="ambient_signal", summary="A published event uses bounded read selection.",
            session_id="bounded-read", host_family="codex",
        ))
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-bounded-read"], operation=publish_event,
    ) == 0
    selected = generations.pin_active_greenfield_generation(repo)

    def forbid_scan(*args, **kwargs):
        pytest.fail("A hot stream read must not fingerprint managed trees")

    monkeypatch.setattr(greenfield_repository_write_set, "greenfield_managed_fingerprints", forbid_scan)
    for _ in range(2):
        assert stream_state.load_recent_intervention_events(repo_root=repo) == events
        assert stream_state.event_cache_signature(repo_root=repo)[0][0] == (
            selected.repository_root / agent_runtime_contract.AGENT_STREAM_PATH
        ).as_posix()


@pytest.mark.parametrize("corruption", ["noncanonical_manifest", "rebound_manifest", "repository_symlink"])
def test_hot_stream_reads_refuse_corrupt_selected_manifest_or_repository(tmp_path, corruption):
    repo, _ = _active_repository(tmp_path)
    selected = generations.pin_active_greenfield_generation(repo)
    assert stream_state.load_recent_intervention_events(repo_root=repo) == []
    manifest = selected.generation_root / "generation-manifest.v1.json"
    if corruption == "noncanonical_manifest":
        manifest.write_bytes(manifest.read_bytes() + b" ")
    elif corruption == "rebound_manifest":
        payload = json.loads(manifest.read_text())
        payload["byte_count"] += 1
        manifest.write_bytes(generations._canonical_manifest_bytes(payload))
    else:
        moved = selected.generation_root / "moved-repository"
        selected.repository_root.rename(moved)
        selected.repository_root.symlink_to(moved, target_is_directory=True)
    with pytest.raises(RuntimeError):
        stream_state.load_recent_intervention_events(repo_root=repo)
    with pytest.raises(RuntimeError):
        stream_state.event_cache_signature(repo_root=repo)


@pytest.mark.parametrize("unsafe", [
    "odylith_symlink", "compass_symlink", "runtime_symlink", "file_symlink",
    "file_hardlink", "file_directory", "file_fifo", "ancestor_file",
])
def test_hot_stream_reads_refuse_unsafe_selected_descendants(tmp_path, unsafe):
    repo, _ = _active_repository(tmp_path)
    selected = generations.pin_active_greenfield_generation(repo)
    path = selected.repository_root / agent_runtime_contract.AGENT_STREAM_PATH
    assert stream_state.load_recent_intervention_events(repo_root=repo) == []
    path.parent.mkdir(parents=True, exist_ok=True)
    if unsafe in {"odylith_symlink", "compass_symlink", "runtime_symlink"}:
        depth = {"odylith_symlink": 1, "compass_symlink": 2, "runtime_symlink": 3}[unsafe]
        ancestor = selected.repository_root.joinpath(*Path(agent_runtime_contract.AGENT_STREAM_PATH).parts[:depth])
        moved = tmp_path / "moved-ancestor"
        ancestor.rename(moved)
        ancestor.symlink_to(moved, target_is_directory=True)
    elif unsafe == "ancestor_file":
        path.parent.rmdir()
        path.parent.write_text("This ancestor is not a directory.")
    elif unsafe == "file_directory":
        path.mkdir()
    elif unsafe == "file_fifo":
        os.mkfifo(path)
    else:
        other = tmp_path / "other-event.jsonl"
        other.write_text("{}\n")
        if unsafe == "file_hardlink":
            os.link(other, path)
        else:
            path.symlink_to(other)
    with pytest.raises(RuntimeError, match="selected intervention stream path is unsafe"):
        stream_state.load_recent_intervention_events(repo_root=repo)
    with pytest.raises(RuntimeError, match="selected intervention stream path is unsafe"):
        stream_state.event_cache_signature(repo_root=repo)


def test_atomic_pending_replacement_invalidates_same_size_and_timestamp_cache(tmp_path):
    stream_state.append_intervention_event(
        repo_root=tmp_path, kind="ambient_signal", summary="First exact claim.",
        session_id="replace-session", host_family="codex", defer=True,
    )
    first = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="replace-session")
    path = host_dirty_checkpoint.event_store_path(tmp_path)
    before = stream_state.event_cache_signature(repo_root=tmp_path)
    metadata = path.stat()
    replacement = path.with_name("replacement.jsonl")
    replacement.write_bytes(path.read_bytes().replace(b"First exact claim.", b"Later exact claim."))
    assert replacement.stat().st_size == metadata.st_size
    os.utime(replacement, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    replacement.replace(path)
    assert stream_state.event_cache_signature(repo_root=tmp_path) != before
    second = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="replace-session")
    assert first["pending_summaries"][0]["summary"] == "First exact claim."
    assert second["pending_summaries"][0]["summary"] == "Later exact claim."


def test_corrupt_pending_intervention_keeps_canonical_memory_and_reports_gap(tmp_path):
    stream_state.append_intervention_event(
        repo_root=tmp_path, kind="ambient_signal", summary="Canonical history survives a pending read failure.",
        session_id="gap-session", host_family="codex", semantic_signature=["canonical-history"],
    )
    _pending_summary(tmp_path, session="gap-session")
    path = host_dirty_checkpoint.event_store_path(tmp_path)
    path.write_text("{corrupt\n")
    with pytest.raises(host_dirty_checkpoint.HostDirtyCheckpointError):
        stream_state.load_recent_intervention_events(repo_root=tmp_path)
    memory = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="gap-session")
    assert memory["recent_event_count"] == 1 and memory["recent_signatures"] == ["canonical-history"]
    assert memory["pending_summary_count"] == 0 and memory["pending_memory_error"]


def test_conflicting_pending_transaction_is_an_explicit_memory_gap(tmp_path):
    stream_state.append_intervention_event(
        repo_root=tmp_path, kind="ambient_signal", summary="The retained event must match exactly.",
        session_id="conflict-session", host_family="codex", defer=True,
    )
    row, = host_dirty_checkpoint.read_compass_events(repo_root=tmp_path)
    canonical = {**row["event"], "summary": "A different event reused the same transaction identity."}
    path = tmp_path / agent_runtime_contract.AGENT_STREAM_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(compass_host_events.event_bytes(canonical))
    with pytest.raises(host_dirty_checkpoint.HostDirtyCheckpointError, match="transaction identity"):
        stream_state.load_recent_intervention_events(repo_root=tmp_path)
    memory = stream_state.session_memory_snapshot(repo_root=tmp_path, session_id="conflict-session")
    assert memory["recent_event_count"] == 1 and memory["pending_memory_error"]
    assert stream_state.load_recent_intervention_events(repo_root=tmp_path, include_pending=False) == [canonical]
