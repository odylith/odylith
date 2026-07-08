from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority


_PROMPT = "Draft a greenfield proposal for a municipal permit review workspace"


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "test_refresh_stub": True},
    )
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


def _proposal(repo_root: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=repo_root,
        prompt=_PROMPT,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(
            CONFIRMED_INTENT_TEXT,
            prompt=_PROMPT,
            repo_root=repo_root,
            write_files=True,
        ),
    )


def _compiled_transaction(repo_root: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    _disable_refreshes(monkeypatch)
    return greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=repo_root,
        proposal=_proposal(repo_root),
        release_selector="0.0.1",
    )


def test_compile_greenfield_create_transaction_precompiles_missing_baseline_writes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    transaction = _compiled_transaction(tmp_path, monkeypatch)

    baseline = transaction.prewrite_package.baseline_writes or {}
    assert "odylith/radar/source/INDEX.md" in baseline
    assert "odylith/technical-plans/INDEX.md" in baseline
    assert "odylith/atlas/source/catalog/diagrams.v1.json" in baseline
    assert not (tmp_path / "odylith/radar/source/INDEX.md").exists()


def test_commit_product_create_transaction_rejects_missing_precompiled_baseline_before_write(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    base = _compiled_transaction(tmp_path, monkeypatch)
    package = replace(base.prewrite_package, baseline_writes={})
    transaction = build_product_create_transaction(
        proposal=base.proposal,
        release_selector=base.release_selector,
        validation_gate=base.validation_gate,
        prewrite_package=package,
        backlog_result=base.backlog_result,
        intent_authority=base.intent_authority,
        quality_manifest=base.quality_manifest,
        repo_root=tmp_path,
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("missing baseline writes must fail before rollback guard or compiled writes")

    monkeypatch.setattr(greenfield_create_commit, "GreenfieldApplyTransaction", forbidden)
    monkeypatch.setattr(
        greenfield_create_commit.greenfield_create_baseline,
        "materialize_precompiled_greenfield_create_baseline",
        forbidden,
    )
    monkeypatch.setattr(greenfield_compiled_write, "write_compiled_greenfield_package", forbidden)

    with pytest.raises(ValueError, match="missing precompiled baseline writes"):
        greenfield_create_commit.commit_greenfield_create_transaction(
            repo_root=tmp_path,
            transaction=transaction,
            confirm=True,
            started_at=0.0,
        )


def test_materialize_precompiled_baseline_rejects_non_text_payload(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="not text"):
        greenfield_create_baseline.materialize_precompiled_greenfield_create_baseline(
            root=tmp_path,
            baseline_writes={
                "odylith/radar/source/INDEX.md": object(),
                "odylith/technical-plans/INDEX.md": "# Plans\n",
                "odylith/atlas/source/catalog/diagrams.v1.json": "{}\n",
            },
        )
