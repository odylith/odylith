from __future__ import annotations

from pathlib import Path
import shutil

from odylith.runtime.domain_intelligence import greenfield_prewrite_transaction_seal
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_graph_transaction


def test_graph_prewrite_materializes_and_seals_staged_surfaces_once(
    tmp_path: Path,
    monkeypatch,
) -> None:
    """The final exact-byte seal is the sole staged materialization pass."""

    repo_root = tmp_path / "consumer"
    shutil.copytree(
        Path("src/odylith/bundle/assets/odylith"),
        repo_root / "odylith",
    )
    original = greenfield_prewrite_transaction_seal.seal_staged_greenfield_create
    calls = []

    def counted(request):  # noqa: ANN001, ANN202
        calls.append(request)
        return original(request)

    monkeypatch.setattr(
        greenfield_prewrite_transaction_seal,
        "seal_staged_greenfield_create",
        counted,
    )
    transaction = compiled_graph_transaction(repo_root)

    assert transaction.quality_manifest["status"] == "passed"
    assert len(calls) == 1
