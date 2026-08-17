from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_graph_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction


def _transaction(repo_root: Path) -> Any:
    return compiled_graph_transaction(repo_root)


def test_commit_product_create_transaction_rolls_back_when_compiled_write_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _transaction(tmp_path)
    transaction = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def fail_after_precompiled_writes(**_kwargs: Any) -> dict[str, Any]:
        raise OSError("simulated compiled write failure")

    monkeypatch.setattr(
        greenfield_compiled_write,
        "write_compiled_greenfield_package",
        fail_after_precompiled_writes,
    )

    with pytest.raises(greenfield_create_commit.GreenfieldCreateCommitError) as exc:
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction_file=transaction.transaction_file,
            transaction_hash=transaction.transaction_hash,
            confirm=True,
            started_at=0.0,
        )

    assert exc.value.rollback_status == "rolled_back"
    assert not (tmp_path / "odylith/radar/source/INDEX.md").exists()
    assert not (tmp_path / "odylith/technical-plans/INDEX.md").exists()
    assert not (tmp_path / "odylith/surfaces/brand/manifest.json").exists()
