from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from tests.unit.runtime.test_greenfield_create_transaction import _transaction


def test_greenfield_apply_transaction_rolls_back_tooling_shell_outputs(tmp_path) -> None:
    shell_root = tmp_path / "odylith"
    shell_root.mkdir()
    index_path = shell_root / "index.html"
    payload_path = shell_root / "tooling-payload.v1.js"
    app_path = shell_root / "tooling-app.v1.js"
    index_path.write_text("old index\n", encoding="utf-8")
    payload_path.write_text("old payload\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="late refresh failure"):
        with GreenfieldApplyTransaction(tmp_path):
            index_path.write_text("new index\n", encoding="utf-8")
            payload_path.unlink()
            app_path.write_text("new app\n", encoding="utf-8")
            raise RuntimeError("late refresh failure")

    assert index_path.read_text(encoding="utf-8") == "old index\n"
    assert payload_path.read_text(encoding="utf-8") == "old payload\n"
    assert not app_path.exists()


def test_commit_transaction_rolls_back_partial_writes_when_write_boundary_fails(tmp_path, monkeypatch) -> None:
    transaction = _transaction(repo_root=tmp_path)

    def partial_write_then_fail(**_kwargs: object) -> dict[str, object]:
        (tmp_path / "odylith/radar/source").mkdir(parents=True, exist_ok=True)
        (tmp_path / "odylith/radar/source/INDEX.md").write_text("partial radar\n", encoding="utf-8")
        (tmp_path / "odylith/runtime").mkdir(parents=True, exist_ok=True)
        (tmp_path / "odylith/runtime/delivery_intelligence.v4.json").write_text("{}\n", encoding="utf-8")
        (tmp_path / "odylith/index.html").write_text("partial shell\n", encoding="utf-8")
        raise RuntimeError("synthetic commit-boundary failure")

    monkeypatch.setattr(
        greenfield_create_commit.greenfield_create_baseline,
        "materialize_precompiled_greenfield_create_baseline",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_create_commit.greenfield_compiled_write,
        "write_compiled_greenfield_package",
        partial_write_then_fail,
    )

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc_info:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction=transaction,
            confirm=True,
            started_at=0.0,
        )

    assert exc_info.value.rollback_status == "rolled_back"
    assert exc_info.value.root_cause_type == "RuntimeError"
    assert "rollback completed; no governed records were committed" in str(exc_info.value)
    assert not (tmp_path / "odylith/radar").exists()
    assert not (tmp_path / "odylith/runtime/delivery_intelligence.v4.json").exists()
    assert not (tmp_path / "odylith/index.html").exists()
