"""Real publication and append-once recovery for retained host summaries."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sqlite3

import pytest

from odylith import cli
from odylith.runtime.common import compass_host_events as events
from odylith.runtime.common import compass_log_continuation as continuation
from odylith.runtime.common import log_compass_timeline_event as log
from odylith.runtime.context_engine import memory_record_policy
from odylith.runtime.context_engine import odylith_context_engine_projection_entity_runtime as entity_runtime
from odylith.runtime.context_engine import odylith_context_engine_store as context_store
from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from odylith.runtime.intervention_engine import stream_state, visibility_broker
from odylith.runtime.surfaces import host_dirty_checkpoint as inbox
from odylith.runtime.surfaces import host_hook_execution
from tests.unit.runtime.test_compass_log_continuation import _actual_engine, _publish_prefix
from tests.unit.runtime.test_component_registry_intelligence import _seed_registry_repo
from tests.unit.runtime.test_greenfield_managed_mutation_boundary import _active_repository


@pytest.fixture
def active(tmp_path, monkeypatch):
    monkeypatch.setattr(continuation, "_runtime_identity", lambda root: {"code": "frozen"})
    repo, _ = _active_repository(tmp_path)
    monkeypatch.chdir(repo)
    _publish_prefix(repo)
    _actual_engine(repo, monkeypatch, lambda **kwargs: None)
    def prerequisites(descriptor):
        _seed_registry_repo(repo)
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-prerequisites"], operation=prerequisites,
    ) == 0
    return repo


def _retain(repo: Path, *, summary: str = "Validated the exact retained memory publication."):
    event_id = inbox.record_compass_event(repo_root=repo, event={
        "version": "v1", "kind": "implementation", "summary": summary,
        "ts_iso": "2026-10-14T22:00:00Z", "author": "assistant", "source": "assistant",
        "host_family": "codex", "session_id": "retained-session", "workstreams": [], "artifacts": [],
    })
    return next(row for row in inbox.read_compass_events(repo_root=repo) if row["id"] == event_id)


def _publish(repo):
    return events.publish_pending(repo_root=repo, dispatch=cli.main)


def test_retained_event_publishes_exact_bytes_and_retry_is_inert(active):
    repo = active
    prior = generations.require_greenfield_working_generation(repo)
    prefix = (repo / continuation.STREAM_PATH).read_bytes()
    record = _retain(repo)
    assert generations.require_greenfield_working_generation(repo).write_set_hash == prior.write_set_hash
    assert _publish(repo) == 0
    selected = generations.require_greenfield_working_generation(repo)
    expected = prefix + events.event_bytes(record["event"])
    assert (selected.repository_root / continuation.STREAM_PATH).read_bytes() == expected
    assert (repo / continuation.STREAM_PATH).read_bytes() == expected
    assert (repo / continuation.STREAM_PATH).stat().st_mode & 0o777 == 0o640
    assert (prior.repository_root / continuation.STREAM_PATH).read_bytes() == prefix
    assert inbox.read_compass_events(repo_root=repo) == []
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert _publish(repo) == 0
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--host-event", record["id"]]) == 0
    assert publication.active_generation_identity(repo)["write_set_hash"] == selected.write_set_hash
    assert (repo / continuation.STREAM_PATH).read_bytes() == expected


def test_memory_survives_stale_dirty_replacement_and_still_publishes_exactly(active):
    repo = active
    inbox.record_dirty_event(repo_root=repo, host_family="codex", source="checkpoint")
    dirty_path = inbox.event_store_path(repo)
    # An older hook has read its snapshot before the new summary is retained.
    snapshot = dirty_path.read_bytes()
    record = _retain(repo)
    replacement = dirty_path.with_name("old-hook-stale.tmp")
    replacement.write_bytes(snapshot)
    os.replace(replacement, dirty_path)
    assert _publish(repo) == 0
    assert events.event_is_published(repo_root=repo, event=record["event"])
    assert inbox.read_compass_events(repo_root=repo) == []
    assert dirty_path.read_bytes() == snapshot


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_published_stop_summary_remains_retrievable_after_ack(active, host):
    repo = active
    summary = "Validated exact retained memory publication for B-142."
    assert inbox.capture_stop_summary(
        repo_root=repo, host_family=host, session_id="retrieval-session",
        summary=summary, workstreams=["B-142"],
    )
    record, = inbox.read_compass_events(repo_root=repo)
    assert cli.main([
        "compass", "log", "--repo-root", str(repo), "--kind", "statement",
        "--summary", "Recorded the foreground publication checkpoint.",
    ]) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert events.event_is_published(repo_root=repo, event=record["event"])
    projected = [row for row in context_store._load_codex_event_projection(repo_root=repo)
                 if row["metadata"]["transaction_id"] == record["event"]["transaction_id"]]
    assert len(projected) == 1
    event, = projected
    assert event["summary"] == summary
    assert event["metadata"] == {
        "author": "assistant", "source": "assistant", "session_id": "retrieval-session",
        "transaction_id": record["event"]["transaction_id"],
    }
    selected = generations.pin_active_greenfield_generation(repo)
    assert context_store._compass_stream_path(repo_root=repo) == selected.repository_root / continuation.STREAM_PATH

    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("CREATE TABLE codex_events (event_id TEXT, ts_iso TEXT, kind TEXT, summary TEXT, workstreams_json TEXT, artifacts_json TEXT, components_json TEXT, metadata_json TEXT)")
        connection.execute("INSERT INTO codex_events VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (
            event["event_id"], event["ts_iso"], event["kind"], event["summary"],
            json.dumps(event["workstreams"]), json.dumps(event["artifacts"]),
            json.dumps(event["components"]), json.dumps(event["metadata"]),
        ))
        anchored = entity_runtime._recent_context_events(
            connection, entity={"kind": "workstream", "entity_id": "B-142"}, related={}, event_limit=10,
        )
        assert [row["summary"] for row in anchored] == [summary]
        assert entity_runtime._recent_context_events(
            connection, entity={"kind": "workstream", "entity_id": "B-143"}, related={}, event_limit=10,
        ) == []
    finally:
        connection.close()
    assert "memory_record" not in event
    assert memory_record_policy.assess(event.get("memory_record"))["use"] == "reference_only"
    assert memory_record_policy.record(event.get("memory_record"))["validity"] == "unknown"


def test_projection_reader_hides_failed_working_append(active):
    repo = active
    selected = generations.pin_active_greenfield_generation(repo)
    before = context_store._load_codex_event_projection(repo_root=repo)
    event = {
        "kind": "implementation", "summary": "An unpublished failed working append.",
        "ts_iso": "2026-10-14T22:00:00Z", "session_id": "failed-session",
        "author": "assistant", "source": "assistant", "transaction_id": "failed-retrieval",
        "workstreams": ["B-142"],
    }

    def fail_after_append(descriptor):
        with (repo / continuation.STREAM_PATH).open("ab") as stream:
            stream.write(events.event_bytes(event))
        return 1

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-failed-working-append"], operation=fail_after_append,
    ) == 1
    assert event["summary"].encode() in (repo / continuation.STREAM_PATH).read_bytes()
    assert context_store._compass_stream_path(repo_root=repo) == selected.repository_root / continuation.STREAM_PATH
    assert context_store._load_codex_event_projection(repo_root=repo) == before


@pytest.mark.parametrize("token", [continuation.STREAM_PATH, "odylith/compass/runtime/codex-stream.v1.jsonl"])
def test_projection_reader_uses_working_stream_without_active_publication(tmp_path, token):
    path = tmp_path / token
    path.parent.mkdir(parents=True)
    path.write_bytes(events.event_bytes({
        "kind": "implementation", "summary": "Retained legacy working history.",
        "ts_iso": "2026-10-14T22:00:00Z", "workstreams": ["B-142"],
    }))
    assert context_store._compass_stream_path(repo_root=tmp_path) == path
    assert [event["summary"] for event in context_store._load_codex_event_projection(repo_root=tmp_path)] == [
        "Retained legacy working history.",
    ]


@pytest.mark.parametrize("summary", ["", "Validated the delegated evidence for B-141."])
def test_subagent_lifecycle_metadata_survives_foreground_publication(active, summary):
    repo = active
    supplied = {
        "kind": "subagent_stop", "host_family": "claude", "source": "claude_hook",
        "summary": summary, "session_id": "claude-session", "agent_id": "delegated-agent",
        "agent_type": "odylith-workstream", "stop_reason": "completed",
        "ts_iso": "2026-10-14T22:00:00Z", "workstreams": ["B-141"],
    }
    event_id = inbox.record_compass_event(repo_root=repo, event=supplied)
    record = inbox.read_compass_events(repo_root=repo)[0]
    assert record["event"] == {**supplied, "transaction_id": "host-event-" + event_id}
    assert _publish(repo) == 0
    assert events.event_is_published(repo_root=repo, event=record["event"])
    assert inbox.read_compass_events(repo_root=repo) == []


def test_interruption_after_append_resumes_same_event_without_reappend(active, monkeypatch):
    repo = active
    record = _retain(repo)
    prefix = (repo / continuation.STREAM_PATH).read_bytes()
    original = continuation.CompassLogContinuation.render

    def interrupt(self):
        assert self.receipt["phase"] == "appended"
        assert json.loads(self.receipt["event"]) == record["event"]
        raise KeyboardInterrupt

    monkeypatch.setattr(continuation.CompassLogContinuation, "render", interrupt)
    with pytest.raises(KeyboardInterrupt):
        _publish(repo)
    assert inbox.read_compass_events(repo_root=repo) == [record]
    assert (repo / continuation.STREAM_PATH).read_bytes() == prefix + events.event_bytes(record["event"])
    monkeypatch.setattr(continuation.CompassLogContinuation, "render", original)
    assert events.resume_pending(repo_root=repo, dispatch=cli.main) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert (generations.require_greenfield_working_generation(repo).repository_root / continuation.STREAM_PATH).read_bytes() == prefix + events.event_bytes(record["event"])


def test_interruption_before_first_append_completes_exact_prepared_receipt(active, monkeypatch):
    repo = active
    record = _retain(repo)
    prefix = (repo / continuation.STREAM_PATH).read_bytes()
    append = continuation.append_prepared
    monkeypatch.setattr(continuation, "append_prepared", lambda admitted: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        _publish(repo)
    assert continuation.pending_event(repo_root=repo) == record["event"]
    assert (repo / continuation.STREAM_PATH).read_bytes() == prefix
    generations.require_greenfield_working_generation(repo)
    monkeypatch.setattr(continuation, "append_prepared", append)
    assert events.resume_pending(repo_root=repo, dispatch=cli.main) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert (generations.require_greenfield_working_generation(repo).repository_root / continuation.STREAM_PATH).read_bytes() == prefix + events.event_bytes(record["event"])


def test_publication_before_ack_is_observed_without_new_append(active, monkeypatch):
    repo = active
    record = _retain(repo)
    acknowledge = inbox.acknowledge_compass_event
    monkeypatch.setattr(inbox, "acknowledge_compass_event", lambda **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()))
    with pytest.raises(KeyboardInterrupt):
        _publish(repo)
    selected = publication.active_generation_identity(repo)
    stream = (repo / continuation.STREAM_PATH).read_bytes()
    assert inbox.read_compass_events(repo_root=repo) == [record]
    monkeypatch.setattr(inbox, "acknowledge_compass_event", acknowledge)
    assert _publish(repo) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert publication.active_generation_identity(repo) == selected
    assert (repo / continuation.STREAM_PATH).read_bytes() == stream


def test_failed_render_keeps_queue_and_completes_existing_receipt(active, monkeypatch):
    repo = active
    record = _retain(repo)
    original = continuation.CompassLogContinuation.render
    monkeypatch.setattr(continuation.CompassLogContinuation, "render", lambda self: (_ for _ in ()).throw(RuntimeError("render unavailable")))
    assert _publish(repo) == 1
    assert inbox.read_compass_events(repo_root=repo) == [record]
    monkeypatch.setattr(continuation.CompassLogContinuation, "render", original)
    assert events.resume_pending(repo_root=repo, dispatch=cli.main) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert (repo / continuation.STREAM_PATH).read_bytes().count(events.event_bytes(record["event"])) == 1


def test_hook_cannot_publish_or_drain_pending_memory(active, monkeypatch):
    repo = active
    record = _retain(repo)
    selected = publication.active_generation_identity(repo)
    monkeypatch.setenv(host_hook_execution._HOOK_COMMAND_ENV, "1")
    assert _publish(repo) == 0
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--host-event", record["id"]]) == 2
    assert publication.active_generation_identity(repo) == selected
    assert inbox.read_compass_events(repo_root=repo) == [record]
    assert not (repo / continuation.RECEIPT_PATH).exists()


@pytest.mark.parametrize("extra", [["--summary", "replacement"], ["--complete"], ["--stream", "elsewhere"], ["--host-event", "0" * 32]])
def test_host_event_mode_rejects_mixed_grammar_before_writes(active, extra):
    repo = active
    record = _retain(repo)
    selected = publication.active_generation_identity(repo)
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--host-event", record["id"], *extra]) == 1
    assert publication.active_generation_identity(repo) == selected
    assert inbox.read_compass_events(repo_root=repo) == [record]


def test_published_identity_with_different_bytes_is_not_acknowledged(active):
    repo = active
    record = _retain(repo)
    assert cli.main(["compass", "log", "--repo-root", str(repo), "--host-event", record["id"]]) == 0
    changed = dict(record["event"], summary="Different claim.")
    with pytest.raises(inbox.HostDirtyCheckpointError, match="differs"):
        events.event_is_published(repo_root=repo, event=changed)
    assert inbox.read_compass_events(repo_root=repo) == []


def test_foreground_normal_log_promotes_prior_host_memory(active):
    repo = active
    record = _retain(repo)
    # This case exercises the actual CLI hook-up rather than calling the drain.
    assert cli.main([
        "compass", "log", "--repo-root", str(repo), "--kind", "statement", "--summary", "An authored checkpoint.",
    ]) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert events.event_is_published(repo_root=repo, event=record["event"])


def test_new_arrival_during_ack_is_retained_for_next_foreground_pass(active, monkeypatch):
    repo = active
    first = _retain(repo)
    acknowledge = inbox.acknowledge_compass_event
    arrivals = []

    def arrive(**kwargs):
        if not arrivals:
            arrivals.append(_retain(repo, summary="Validated a later independent session result."))
        return acknowledge(**kwargs)

    monkeypatch.setattr(inbox, "acknowledge_compass_event", arrive)
    assert _publish(repo) == 0
    assert inbox.read_compass_events(repo_root=repo) == arrivals
    assert events.event_is_published(repo_root=repo, event=first["event"])


@pytest.mark.parametrize("host", ["codex", "claude"])
def test_deferred_confirmation_prevents_next_prompt_duplicate_and_publishes_exactly(active, host):
    repo = active
    display = "---\n**Odylith Observation:** The recorded result needs chat proof.\n---"

    def hidden(descriptor):
        stream_state.append_intervention_event(
            repo_root=repo, kind="intervention_card", summary="A result waiting for chat proof.",
            session_id="delivery-session", host_family=host, intervention_key="iv-pending",
            display_markdown=display, delivery_channel="assistant_visible_fallback",
            delivery_status="assistant_render_required", render_surface=host + "_prompt_context",
        )
        return 0

    assert boundary.run_with_greenfield_managed_mutation_boundary(
        repo_root=repo, command_tokens=["fixture-hidden-intervention"], operation=hidden,
    ) == 0
    before = (repo / continuation.STREAM_PATH).read_bytes()
    arguments = dict(
        repo_root=repo, host_family=host, session_id="delivery-session",
        last_assistant_message="Recorded result.\n\n" + display,
    )
    confirmed = visibility_broker.confirm_assistant_chat_delivery(
        **arguments, render_surface=host + "_stop", defer=True,
    )
    assert len(confirmed) == 1
    record, = inbox.read_compass_events(repo_root=repo)
    assert record["event"]["delivery_status"] == "assistant_chat_confirmed"
    assert (repo / continuation.STREAM_PATH).read_bytes() == before
    assert visibility_broker.confirm_assistant_chat_delivery(
        **arguments, render_surface=host + "_user_prompt_submit",
    ) == []
    assert inbox.read_compass_events(repo_root=repo) == [record]
    assert (repo / continuation.STREAM_PATH).read_bytes() == before
    generations.require_greenfield_working_generation(repo)
    assert _publish(repo) == 0
    assert (repo / continuation.STREAM_PATH).read_bytes() == before + events.event_bytes(record["event"])
    assert visibility_broker.confirm_assistant_chat_delivery(
        **arguments, render_surface=host + "_user_prompt_submit",
    ) == []


def test_foreground_writer_does_not_complete_an_unrelated_manual_receipt(active):
    from odylith.runtime.domain_intelligence import greenfield_repository_lock as leases

    repo = active
    record = _retain(repo)
    event = {"kind": "statement", "summary": "An unrelated admitted manual event."}
    with leases.greenfield_repository_lock(repo) as descriptor:
        admitted = continuation.prepare_append(repo_root=repo, event=events.event_bytes(event), repository_lock_fd=descriptor)
    before = (repo / continuation.RECEIPT_PATH).read_bytes()
    selected = publication.active_generation_identity(repo)
    with pytest.raises(continuation.CompassLogContinuationError, match="unrelated"):
        events.resume_pending(repo_root=repo, dispatch=cli.main)
    assert cli.main(["sync", "--repo-root", str(repo), "odylith/radar/source/keep.md"]) == 1
    assert cli.main([
        "compass", "log", "--repo-root", str(repo), "--kind", "statement", "--summary", "A later manual statement.",
    ]) == 1
    assert (repo / continuation.RECEIPT_PATH).read_bytes() == before
    assert publication.active_generation_identity(repo) == selected
    generations.require_greenfield_working_generation(repo)
    assert continuation.pending_event(repo_root=repo) == event
    assert inbox.read_compass_events(repo_root=repo) == [record]


@pytest.mark.parametrize("failed_upkeep", ["return_code", "corrupt_ledger"])
def test_saved_authored_log_stays_successful_when_later_memory_upkeep_fails(active, monkeypatch, capsys, failed_upkeep):
    repo = active
    record = _retain(repo)
    if failed_upkeep == "return_code":
        monkeypatch.setattr(events, "publish_pending", lambda **kwargs: 1)
    else:
        with inbox.compass_event_store_path(repo).open("ab") as handle:
            handle.write(b"not-json\n")
    assert cli.main([
        "compass", "log", "--repo-root", str(repo), "--kind", "statement", "--summary", "One completed authored statement.",
    ]) == 0
    assert "Requested change completed" in capsys.readouterr().err
    stream = (generations.require_greenfield_working_generation(repo).repository_root / continuation.STREAM_PATH).read_bytes()
    assert stream.count(b"One completed authored statement.") == 1
    assert not (repo / continuation.RECEIPT_PATH).exists()
    assert record["id"].encode() in inbox.compass_event_store_path(repo).read_bytes()


@pytest.mark.parametrize("equals", [False, True])
def test_direct_host_event_spellings_publish_and_acknowledge(active, equals):
    repo = active
    record = _retain(repo)
    arguments = [f"--repo-root={repo}", f"--host-event={record['id']}"] if equals else ["--repo-root", str(repo), "--host-event", record["id"]]
    assert cli.main(["compass", "log", *arguments]) == 0
    assert inbox.read_compass_events(repo_root=repo) == []
    assert events.event_is_published(repo_root=repo, event=record["event"])
    assert cli.main(["compass", "log", *arguments]) == 0


def test_automatic_pass_is_bounded_and_preserves_remaining_events(active):
    repo = active
    records = [_retain(repo, summary=f"Validated independent result {index}.") for index in range(5)]
    assert _publish(repo) == 0
    assert inbox.read_compass_events(repo_root=repo) == records[4:]
    assert all(events.event_is_published(repo_root=repo, event=row["event"]) for row in records[:4])
    assert _publish(repo) == 0
    assert inbox.read_compass_events(repo_root=repo) == []


@pytest.mark.parametrize("result", [0, 1])
def test_foreground_sync_retires_only_covered_preexisting_dirty_rows(active, monkeypatch, result):
    repo = active
    paths = ["odylith/radar/source/keep.md", "odylith/casebook/bugs/later.md"]
    covered, outside = [inbox.record_dirty_event(
        repo_root=repo, host_family="codex", session_id="dirty-sync", source="post_bash_checkpoint", governed_paths=[path],
    ) for path in paths]
    later = []

    def complete_sync(args):
        # Only the expensive independent sync body is replaced. CLI admission,
        # repository publication, captured scope and ledger acknowledgment run.
        later.append(inbox.record_dirty_event(
            repo_root=repo, host_family="codex", session_id="dirty-sync", source="post_bash_checkpoint", governed_paths=[paths[0]],
        ))
        return result

    monkeypatch.setattr(cli, "_cmd_sync", complete_sync)
    assert cli.main(["sync", "--repo-root", str(repo), paths[0]]) == result
    expected = [outside, *later] if result == 0 else [covered, outside, *later]
    assert [row["id"] for row in inbox.read_dirty_events(repo_root=repo)] == expected
