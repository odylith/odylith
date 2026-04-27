"""Brand Assets helpers for the Odylith surfaces layer."""

from __future__ import annotations

import html
import os
from pathlib import Path

_BRAND_ROOT = Path("odylith/surfaces/brand")
_FAVICON_ROOT = _BRAND_ROOT / "favicon"
_ICON_ROOT = _BRAND_ROOT / "icon"
_LOCKUP_ROOT = _BRAND_ROOT / "lockup"


def asset_href(*, repo_root: Path, output_path: Path, asset_path: str | Path) -> str:
    target = Path(repo_root).resolve() / Path(asset_path)
    rel = os.path.relpath(str(target), start=str(Path(output_path).resolve().parent))
    return Path(rel).as_posix()


def render_brand_head_html(*, repo_root: Path, output_path: Path) -> str:
    manifest_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_BRAND_ROOT / "manifest.json")
    favicon_svg_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_FAVICON_ROOT / "favicon.svg")
    favicon_32_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_FAVICON_ROOT / "favicon-32.png")
    favicon_16_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_FAVICON_ROOT / "favicon-16.png")
    favicon_ico_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_FAVICON_ROOT / "favicon.ico")
    apple_touch_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_ICON_ROOT / "odylith-icon-256x256.png")
    safari_pinned_href = asset_href(repo_root=repo_root, output_path=output_path, asset_path=_ICON_ROOT / "odylith-icon-monochrome.svg")
    lines = (
        '<meta name="application-name" content="Odylith" />',
        '<meta name="theme-color" content="#edf4ff" />',
        f'<link rel="manifest" href="{html.escape(manifest_href)}" />',
        f'<link rel="icon" href="{html.escape(favicon_ico_href)}" sizes="any" />',
        f'<link rel="icon" type="image/svg+xml" href="{html.escape(favicon_svg_href)}" />',
        f'<link rel="icon" type="image/png" sizes="32x32" href="{html.escape(favicon_32_href)}" />',
        f'<link rel="icon" type="image/png" sizes="16x16" href="{html.escape(favicon_16_href)}" />',
        f'<link rel="apple-touch-icon" sizes="256x256" href="{html.escape(apple_touch_href)}" />',
        f'<link rel="mask-icon" href="{html.escape(safari_pinned_href)}" color="#173f83" />',
    )
    return "\n  ".join(lines)


def tooling_shell_brand_payload(*, repo_root: Path, output_path: Path) -> dict[str, str]:
    return {
        "brand_head_html": render_brand_head_html(repo_root=repo_root, output_path=output_path),
        "shell_brand_lockup_href": asset_href(
            repo_root=repo_root,
            output_path=output_path,
            asset_path=_LOCKUP_ROOT / "odylith-lockup-horizontal.svg",
        ),
        "shell_brand_icon_href": asset_href(
            repo_root=repo_root,
            output_path=output_path,
            asset_path=_ICON_ROOT / "odylith-icon.svg",
        ),
    }


__all__ = [
    "asset_href",
    "render_brand_head_html",
    "tooling_shell_brand_payload",
]
