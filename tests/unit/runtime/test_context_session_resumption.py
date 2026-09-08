"""Session resumption preserves context without replaying an operator command."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3

import pytest

from odylith.runtime.context_engine import odylith_context_engine_packet_session_runtime as packets
from odylith.runtime.context_engine import odylith_context_engine_store as store
from odylith.runtime.execution_engine.runtime_surface_governance import build_packet_execution_engine_snapshot


@pytest.fixture
def session_repo(tmp_path: Path, monkeypatch):
    """Use real canonical lookup and session persistence; isolate impact retrieval."""
    database = tmp_path / "projection.sqlite"

    def connect(_root):
        connection = sqlite3.connect(database)
        connection.row_factory = sqlite3.Row
        return connection

    with connect(tmp_path) as connection:
        connection.execute(
            "CREATE TABLE workstreams (idea_id TEXT PRIMARY KEY, title TEXT, status TEXT, "
            "source_path TEXT, section TEXT, priority TEXT, promoted_to_plan TEXT, "
            "idea_file TEXT, metadata_json TEXT)"
        )
        connection.executemany(
            "INSERT INTO workstreams VALUES (?, ?, 'queued', '', '', 'P1', '', '', '{}')",
            [("B-001", "Review accepted scope"), ("B-002", "Different workstream")],
        )
    monkeypatch.setattr(store, "_connect", connect)
    monkeypatch.setattr(store, "_load_judgment_workstream_hint", lambda **kwargs: {})
    monkeypatch.setattr(store, "load_context_dossier", lambda **kwargs: {"resolved": True})
    monkeypatch.setattr(packets, "build_impact_report", lambda **kwargs: {
        "changed_paths": list(kwargs["changed_paths"]), "candidate_workstreams": [],
        "context_packet_state": "gated_ambiguous", "components": [], "diagrams": [],
    })
    monkeypatch.setattr(packets.tooling_context_packet_builder, "finalize_packet", lambda **kwargs: dict(kwargs["payload"]))
    store.clear_runtime_process_caches(repo_root=tmp_path)
    return tmp_path, connect


def brief(root, **kwargs):
    return packets.build_session_brief(
        repo_root=root, session_id="resume-proof", runtime_mode="local",
        compact_delivery=False, **kwargs,
    )


def saved(root):
    return store._load_session_state(repo_root=root, session_id="resume-proof", include_stale=True)


@pytest.mark.parametrize("intent", ["Review the accepted scope. Do not implement.", "Implement the selected scope."])
def test_input_free_resume_retains_context_without_reissuing_instruction(session_repo, intent):
    root, _ = session_repo
    first = brief(root, workstream="B-001", intent=intent)
    assert first["inferred_workstream"] == "B-001"
    assert saved(root)["intent"] == intent

    for _ in range(2):
        resumed = brief(root)
        assert resumed["inferred_workstream"] == "B-001"
        assert saved(root)["workstream"] == "B-001"
        assert saved(root)["intent"] == intent
        assert "retained" in resumed["selection_reason"].lower()
        assert resumed["selection_state"] != "explicit"
        assert not resumed["turn_context"].get("intent")
        assert not saved(root)["turn_context"].get("intent")
        execution = build_packet_execution_engine_snapshot(resumed)
        assert not execution["contract"].get("turn_context", {}).get("intent")
        assert "implement.target_scope" not in execution["contract"]["allowed_moves"]
        compact = packets.session_bootstrap_payload_compactor.compact_finalized_session_brief_payload(resumed)
        assert compact["session"]["intent"] == intent
        assert compact["inferred_workstream"] == "B-001"


@pytest.mark.parametrize("new_input", [
    {"workstream": "B-002"},
    {"intent": "Explain the current status only."},
    {"changed_paths": ["src/new.py"]},
    {"claimed_paths": ["src/new.py"]},
    {"generated_surfaces": ["radar"]},
    {"visible_text": ["Different evidence"]},
    {"active_tab": "registry"},
    {"user_turn_id": "new-turn"},
    {"supersedes_turn_id": "old-turn"},
    {"use_working_tree": True},
    {"family_hint": "guidance_behavior"},
    {"validation_command_hints": ["odylith validate discipline --repo-root ."]},
    {"impact_override": {}},
])
def test_new_scope_does_not_inherit_previous_instruction(session_repo, new_input):
    root, _ = session_repo
    brief(root, workstream="B-001", intent="Old scope. Do not implement.")
    resumed = brief(root, **new_input)
    assert resumed["inferred_workstream"] == new_input.get("workstream", "")
    assert saved(root)["intent"] == new_input.get("intent", "")
    assert "retained" not in resumed["selection_reason"].lower()


@pytest.mark.parametrize("boundary", ["missing", "expired_lease", "stale_update", "missing_anchor", "unavailable_projection"])
def test_resume_does_not_restore_ineligible_context(session_repo, monkeypatch, boundary):
    root, connect = session_repo
    if boundary != "missing":
        brief(root, workstream="B-001", intent="Prior work. Do not implement.")
    if boundary in {"expired_lease", "stale_update"}:
        record = saved(root)
        field = "lease_expires_utc" if boundary == "expired_lease" else "updated_utc"
        record[field] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        path = store._session_record_path(repo_root=root, session_id="resume-proof")
        path.write_text(json.dumps(record), encoding="utf-8")
    elif boundary == "missing_anchor":
        with connect(root) as connection:
            connection.execute("DELETE FROM workstreams WHERE idea_id = 'B-001'")
    elif boundary == "unavailable_projection":
        def unavailable(_root):
            raise RuntimeError("projection unavailable")
        monkeypatch.setattr(store, "_connect", unavailable)

    resumed = brief(root)
    assert resumed["inferred_workstream"] == ""
    assert saved(root)["workstream"] == ""
    assert saved(root)["intent"] == ""


def test_hot_path_does_not_expand_into_resume_projection_lookup(session_repo, monkeypatch):
    root, _ = session_repo
    brief(root, workstream="B-001", intent="Prior read-only context.")
    monkeypatch.setattr(packets, "build_impact_report", lambda **kwargs: {
        "changed_paths": [], "workstream_selection": {"state": "none"},
        "context_packet_state": "gated_ambiguous",
    })
    monkeypatch.setattr(store, "_connect", lambda _root: pytest.fail("hot path expanded into projection lookup"))
    brief(root, delivery_profile="agent_hot_path")


def test_retained_intent_never_enters_current_impact_request(session_repo, monkeypatch):
    root, _ = session_repo
    brief(root, workstream="B-001", intent="Implement src/old_scope.py now.")
    captured = {}

    def impact(**kwargs):
        captured.update(kwargs)
        return {"changed_paths": [], "candidate_workstreams": []}

    monkeypatch.setattr(packets, "build_impact_report", impact)
    resumed = brief(root)
    assert resumed["inferred_workstream"] == "B-001"
    assert captured["intent"] == ""
    assert captured["workstream_hint"] == ""
    assert captured["changed_paths"] == []


def test_retention_selection_uses_its_phase_owner(session_repo, monkeypatch):
    root, _ = session_repo
    owner = packets.session_workstream_selection
    original = owner.select_session_workstream
    calls = []

    def select(**kwargs):
        calls.append(kwargs)
        return original(**kwargs)

    monkeypatch.setattr(owner, "select_session_workstream", select)
    brief(root, workstream="B-001", intent="Read only.")
    brief(root)
    assert [call["retained_workstream"] for call in calls] == ["", "B-001"]
