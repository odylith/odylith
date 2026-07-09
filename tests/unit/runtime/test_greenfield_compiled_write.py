from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def test_write_compiled_greenfield_package_bypasses_legacy_proposal_writer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction()
    calls: set[str] = set()

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
        lambda **_kwargs: {"status": "passed", "surfaces": []},
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
