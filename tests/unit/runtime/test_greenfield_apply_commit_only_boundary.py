from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.common import display_text
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_post_confirm_patch_apply
from odylith.runtime.domain_intelligence import greenfield_prewrite_surface_stage
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from tests.unit.runtime.greenfield_proposal_fixtures import _governed_greenfield_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


def test_apply_confirm_is_disabled_before_compile_commit_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    compile_calls: list[dict[str, Any]] = []

    def forbidden_compile(**kwargs: Any) -> None:
        compile_calls.append(dict(kwargs))
        raise AssertionError("legacy apply must not compile after confirmation")

    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden_compile)

    proposal = {"backlog": [{"title": "Accepted package"}]}

    with pytest.raises(ValueError, match="greenfield apply is disabled"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert compile_calls == []


def test_create_confirm_cli_commits_transaction_without_post_confirm_generation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(
        greenfield_prewrite_surface_stage,
        "build_staged_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )
    proposal = _governed_greenfield_fixture(tmp_path, "plant sensor")
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        proposal_ready=True,
    )
    transaction_file = tmp_path / ".odylith/runtime/greenfield/product-create-transaction.v1.json"
    greenfield_proposals.write_product_create_transaction_file(transaction_file, transaction)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("post-confirm create must not compile, repair, clean, or rebuild package projections")

    monkeypatch.setattr(greenfield_proposals, "compile_greenfield_create_transaction", forbidden)
    monkeypatch.setattr(greenfield_proposals, "_build_repaired_prewrite_package", forbidden)
    monkeypatch.setattr(greenfield_proposals, "apply_greenfield_patchset_repairs", forbidden)
    monkeypatch.setattr(greenfield_post_confirm_patch_apply, "apply_greenfield_patchset_repairs", forbidden)
    monkeypatch.setattr(display_text, "strip_inline_markdown_emphasis_tree", forbidden)
    monkeypatch.setattr(greenfield_apply_prewrite, "build_prewrite_completion_package", forbidden)
    monkeypatch.setattr(greenfield_prewrite_surface_stage, "build_staged_surface_refresh_preview", forbidden)
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_component_commit.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped_in_commit_only_sentinel"},
    )

    rc = greenfield_proposals_cli.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--transaction-file",
            str(transaction_file),
            "--transaction-hash",
            transaction.transaction_hash,
            "--confirm",
            "--json",
        ]
    )
    output = capsys.readouterr().out

    assert rc == 0, output
    payload = json.loads(output)
    assert payload["post_confirm_quality_manifest"]["write_transaction"]["commit_only"] is True
    assert payload["product_create_transaction"]["transaction_hash"] == transaction.transaction_hash
