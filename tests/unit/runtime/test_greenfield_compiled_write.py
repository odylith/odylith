from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import proposal_memory
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def test_write_compiled_greenfield_package_bypasses_legacy_proposal_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction()
    calls: set[str] = set()
    memory_kwargs: dict[str, Any] = {}
    refresh_kwargs: dict[str, Any] = {}

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("compiled transaction commits must not route through the legacy proposal writer")

    def fake_write_backlog_files(*_args: Any, **_kwargs: Any) -> None:
        calls.add("backlog")

    def fake_release_target(**_kwargs: Any) -> dict[str, Any]:
        calls.add("release_target")
        return {"created": False, "release": {"release_id": "release-0-0-1"}}

    def fake_program(**_kwargs: Any) -> dict[str, Any]:
        calls.add("program")
        return {"created": True, "umbrella_id": "B-001", "program_count": 1, "waves": []}

    def fake_release_assignment(**_kwargs: Any) -> dict[str, Any]:
        calls.add("release_assignment")
        return {"selector": "0.0.1", "release_id": "release-0-0-1", "events": []}

    def fake_diagrams(**_kwargs: Any) -> Any:
        calls.add("diagrams")
        return greenfield_apply_diagrams.GreenfieldDiagramWriteResult(diagram_ids=(), scaffold_logs=())

    def fake_memory(**_kwargs: Any) -> dict[str, Any]:
        calls.add("memory")
        memory_kwargs.update(_kwargs)
        return {"recorded": True, "event": {"ts_iso": "2026-07-07T00:00:00Z"}}

    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)
    monkeypatch.setattr(greenfield_compiled_write, "_remove_precompiled_stale_workstreams", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_backlog_commit,
        "write_backlog_files",
        fake_write_backlog_files,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_release_commit,
        "materialize_compiled_release_target",
        fake_release_target,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_programs,
        "materialize_compiled_greenfield_program",
        fake_program,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_release_commit,
        "materialize_compiled_release_assignment",
        fake_release_assignment,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_apply_diagrams,
        "materialize_apply_diagrams",
        fake_diagrams,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_compiled_readback,
        "raise_for_compiled_backlog_and_atlas_readback",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_component_commit,
        "raise_for_compiled_component_registry_readback",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(greenfield_compiled_write, "record_compiled_greenfield_acceptance", fake_memory)
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_compiled_memory_readback,
        "raise_for_compiled_memory_readback",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_compiled_write,
        "_refresh_compiled_greenfield_dashboard",
        lambda **_kwargs: refresh_kwargs.update(_kwargs) or {"status": "passed", "surfaces": []},
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed"},
    )

    result = greenfield_compiled_write.write_compiled_greenfield_package(
        root=tmp_path,
        transaction=transaction,
        completion_priority_write_policy={"status": "write_allowed_with_projection_quality_debt"},
    )

    assert result["mode"] == "applied"
    assert calls == {"backlog", "release_target", "program", "release_assignment", "diagrams", "memory"}
    assert result["completion_priority_quality_debt"] == []
    assert memory_kwargs["accepted_project_preview"] == transaction.prewrite_package.accepted_project_preview
    assert memory_kwargs["project_brief_record_text"] == transaction.prewrite_package.project_brief_record_text
    assert memory_kwargs["compass_memory_preview"] == transaction.prewrite_package.compass_memory_preview
    assert refresh_kwargs["surface_refresh_preview"] == transaction.prewrite_package.surface_refresh_preview


def test_write_compiled_greenfield_package_rejects_missing_surface_proof_before_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction()
    bad_transaction = replace(
        transaction,
        prewrite_package=replace(transaction.prewrite_package, surface_refresh_preview=None),
    )
    calls: list[str] = []

    monkeypatch.setattr(
        greenfield_compiled_write,
        "_remove_precompiled_stale_workstreams",
        lambda **_kwargs: calls.append("stale_cleanup"),
    )
    monkeypatch.setattr(
        greenfield_compiled_write.greenfield_backlog_commit,
        "write_backlog_files",
        lambda *_args, **_kwargs: calls.append("backlog"),
    )

    with pytest.raises(ValueError, match="missing compiled pre-confirm surface refresh proof"):
        greenfield_compiled_write.write_compiled_greenfield_package(
            root=tmp_path,
            transaction=bad_transaction,
        )

    assert calls == []


def test_record_compiled_greenfield_acceptance_does_not_reuse_timestamp_drift(tmp_path: Path) -> None:
    stream_path = tmp_path / "odylith/compass/runtime/agent-stream.v1.jsonl"
    stream_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "version": "v1",
        "kind": "decision",
        "summary": "Accepted greenfield proposal for Supplier Risk Board.",
        "ts_iso": "2026-07-07T00:00:00-07:00",
        "author": "odylith",
        "source": "domain-intelligence",
        "workstreams": ["B-001"],
        "artifacts": ["odylith/runtime/source/project-brief.v1.md"],
        "components": ["supplier-risk-service"],
        "evidence_tier": "user_intent",
        "work_category": "governance",
    }
    prior = {**event, "ts_iso": "2026-07-06T00:00:00-07:00"}
    stream_path.write_text(f"{json.dumps(prior, sort_keys=True)}\n", encoding="utf-8")
    accepted_project = {
        "schema_version": "odylith.accepted_project.v1",
        "accepted_at": event["ts_iso"],
        "title": "Supplier Risk Board",
    }
    project_brief = f"# Supplier Risk Board Project Brief\n\n- accepted_at: {event['ts_iso']}\n"

    result = proposal_memory.record_compiled_greenfield_acceptance(
        repo_root=tmp_path,
        accepted_project_preview=accepted_project,
        project_brief_record_text=project_brief,
        compass_memory_preview=event,
    )

    committed_project = json.loads((tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8"))
    committed_brief = (tmp_path / "odylith/runtime/source/project-brief.v1.md").read_text(encoding="utf-8")
    stream_events = [json.loads(line) for line in stream_path.read_text(encoding="utf-8").splitlines()]
    assert result["reused_existing"] is False
    assert result["event"] == event
    assert committed_project == accepted_project
    assert committed_brief == project_brief
    assert stream_events == [prior, event]
