from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence import proposal_memory
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def test_write_compiled_greenfield_package_bypasses_legacy_proposal_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(repo_root=tmp_path)
    staged_root = tmp_path / "staged"
    staged_index = staged_root / "odylith/index.html"
    staged_index.parent.mkdir(parents=True, exist_ok=True)
    staged_index.write_text("sealed project surface\n", encoding="utf-8")
    write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
        source_root=tmp_path,
        staged_root=staged_root,
    )
    transaction = replace(
        transaction,
        prewrite_package=replace(transaction.prewrite_package, repository_write_set=write_set),
    )

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("compiled transaction commits must not route through the legacy proposal writer")

    monkeypatch.setattr(greenfield_apply_write, "write_greenfield_proposal", forbidden)

    result = greenfield_compiled_write.write_compiled_greenfield_package(
        root=tmp_path,
        transaction=transaction,
        completion_priority_write_policy={"status": "write_allowed_with_projection_quality_debt"},
    )

    assert result["mode"] == "applied"
    assert (tmp_path / "odylith/index.html").read_text(encoding="utf-8") == "sealed project surface\n"
    assert result["repository_write_set"]["write_set_hash"] == write_set["write_set_hash"]
    assert result["completion_priority_quality_debt"] == []


def test_write_compiled_greenfield_package_rejects_missing_write_set_before_writes(
    tmp_path: Path,
) -> None:
    transaction = _transaction(repo_root=tmp_path)
    bad_transaction = replace(
        transaction,
        prewrite_package=replace(transaction.prewrite_package, repository_write_set=None),
    )

    with pytest.raises(ValueError, match="missing a compiled repository write set"):
        greenfield_compiled_write.write_compiled_greenfield_package(
            root=tmp_path,
            transaction=bad_transaction,
        )

    assert not (tmp_path / "odylith/index.html").exists()


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
