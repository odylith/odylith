from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof


ROOT = Path(__file__).resolve().parents[3]


def _seed_rendered_artifacts(root: Path) -> None:
    for relative_path in greenfield_surface_refresh_proof.GREENFIELD_REQUIRED_SURFACE_ARTIFACTS:
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rendered artifact\n", encoding="utf-8")
    shutil.copyfile(
        ROOT / greenfield_surface_refresh_proof.GREENFIELD_DELIVERY_INTELLIGENCE_ARTIFACT,
        root / greenfield_surface_refresh_proof.GREENFIELD_DELIVERY_INTELLIGENCE_ARTIFACT,
    )


def test_greenfield_surface_refresh_proves_real_delivery_intelligence_artifact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_rendered_artifacts(tmp_path)
    monkeypatch.setattr(
        greenfield_surface_refresh_proof.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **_kwargs: None,
    )

    preview = greenfield_surface_refresh_proof.build_prewrite_surface_refresh_preview(
        repo_root=tmp_path,
    )

    evidence = preview["delivery_intelligence"]
    assert evidence["status"] == "passed"
    assert evidence["version"] == "v4"
    assert evidence["scope_count"] > 0


def test_greenfield_surface_refresh_fails_closed_on_invalid_delivery_intelligence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _seed_rendered_artifacts(tmp_path)
    (tmp_path / greenfield_surface_refresh_proof.GREENFIELD_DELIVERY_INTELLIGENCE_ARTIFACT).write_text(
        "{}\n", encoding="utf-8",
    )
    monkeypatch.setattr(
        greenfield_surface_refresh_proof.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **_kwargs: None,
    )

    with pytest.raises(RuntimeError, match="invalid Delivery Intelligence artifact"):
        greenfield_surface_refresh_proof.build_prewrite_surface_refresh_preview(repo_root=tmp_path)
