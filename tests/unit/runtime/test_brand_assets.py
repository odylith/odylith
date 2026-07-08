from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.surfaces import brand_assets


def test_render_brand_head_html_uses_root_relative_paths(tmp_path: Path) -> None:
    html = brand_assets.render_brand_head_html(
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "index.html",
    )

    assert 'href="surfaces/brand/manifest.json"' in html
    assert 'href="surfaces/brand/favicon/favicon.ico"' in html
    assert 'href="surfaces/brand/favicon/favicon.svg"' in html
    assert 'href="surfaces/brand/icon/odylith-icon-256x256.png"' in html


def test_render_brand_head_html_uses_nested_relative_paths(tmp_path: Path) -> None:
    html = brand_assets.render_brand_head_html(
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "registry" / "registry.html",
    )

    assert 'href="../surfaces/brand/manifest.json"' in html
    assert 'href="../surfaces/brand/favicon/favicon.ico"' in html
    assert 'href="../surfaces/brand/favicon/favicon.svg"' in html
    assert 'href="../surfaces/brand/icon/odylith-icon-256x256.png"' in html


def test_tooling_shell_brand_payload_exposes_shell_assets(tmp_path: Path) -> None:
    payload = brand_assets.tooling_shell_brand_payload(
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "index.html",
    )

    assert payload["shell_brand_icon_href"] == "surfaces/brand/icon/odylith-icon.svg"
    assert payload["shell_brand_lockup_href"] == "surfaces/brand/lockup/odylith-lockup-horizontal.svg"


def test_ensure_brand_assets_seeds_missing_surface_dependencies(tmp_path: Path) -> None:
    copied = brand_assets.ensure_brand_assets(repo_root=tmp_path)

    assert copied
    assert (tmp_path / "odylith/surfaces/brand/manifest.json").is_file()
    assert (tmp_path / "odylith/surfaces/brand/lockup/odylith-lockup-horizontal.svg").is_file()
    assert (tmp_path / "odylith/surfaces/brand/icon/odylith-icon.svg").is_file()
    assert (tmp_path / "odylith/surfaces/brand/favicon/favicon.svg").is_file()


def test_ensure_brand_assets_preserves_existing_nonempty_local_assets(tmp_path: Path) -> None:
    manifest = tmp_path / "odylith/surfaces/brand/manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"custom": true}\n', encoding="utf-8")

    brand_assets.ensure_brand_assets(repo_root=tmp_path)

    assert manifest.read_text(encoding="utf-8") == '{"custom": true}\n'
    assert (tmp_path / "odylith/surfaces/brand/lockup/odylith-lockup-horizontal.svg").is_file()


def test_precompiled_brand_asset_writes_materialize_missing_assets(tmp_path: Path) -> None:
    writes = brand_assets.precompiled_brand_asset_writes(repo_root=tmp_path)

    assert "odylith/surfaces/brand/manifest.json" in writes
    assert writes["odylith/surfaces/brand/manifest.json"]["encoding"] == "base64"

    materialized = brand_assets.materialize_precompiled_brand_assets(
        repo_root=tmp_path,
        brand_asset_writes=writes,
    )

    assert materialized
    assert (tmp_path / "odylith/surfaces/brand/manifest.json").is_file()
    assert (tmp_path / "odylith/surfaces/brand/icon/odylith-icon.svg").is_file()


def test_precompiled_brand_assets_reject_missing_required_payload(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="missing precompiled brand asset writes"):
        brand_assets.require_precompiled_brand_assets(repo_root=tmp_path, brand_asset_writes={})


def test_precompiled_brand_assets_preserve_nonempty_local_asset(tmp_path: Path) -> None:
    manifest = tmp_path / "odylith/surfaces/brand/manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text('{"custom": true}\n', encoding="utf-8")

    writes = brand_assets.precompiled_brand_asset_writes(repo_root=tmp_path)
    assert "odylith/surfaces/brand/manifest.json" not in writes


def test_precompiled_brand_assets_reject_hash_mismatch(tmp_path: Path) -> None:
    writes = brand_assets.precompiled_brand_asset_writes(repo_root=tmp_path)
    payload = dict(writes["odylith/surfaces/brand/manifest.json"])
    payload["sha256"] = "not-the-asset-hash"

    with pytest.raises(ValueError, match="hash mismatch"):
        brand_assets.materialize_precompiled_brand_assets(
            repo_root=tmp_path,
            brand_asset_writes={"odylith/surfaces/brand/manifest.json": payload},
        )
