from __future__ import annotations

from pathlib import Path

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
