"""Brand Assets helpers for the Odylith surfaces layer."""

from __future__ import annotations

import html
from importlib import resources
import os
from pathlib import Path

_BRAND_ROOT = Path("odylith/surfaces/brand")
_FAVICON_ROOT = _BRAND_ROOT / "favicon"
_ICON_ROOT = _BRAND_ROOT / "icon"
_LOCKUP_ROOT = _BRAND_ROOT / "lockup"
_PACKAGED_BRAND_ROOT = "bundle/assets/odylith/surfaces/brand"


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


def ensure_brand_assets(*, repo_root: Path) -> tuple[Path, ...]:
    """Seed missing managed brand assets referenced by rendered Odylith surfaces."""

    target_root = Path(repo_root).expanduser().resolve() / _BRAND_ROOT
    copied: list[Path] = []
    source_root = resources.files("odylith").joinpath(_PACKAGED_BRAND_ROOT)
    for relative, source in _resource_files(source_root):
        if relative.name == ".DS_Store":
            continue
        target = target_root / relative
        if target.is_file() and target.stat().st_size > 0:
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
        copied.append(target)
    return tuple(copied)


def _resource_files(
    root: resources.abc.Traversable,
    prefix: Path = Path(),
) -> tuple[tuple[Path, resources.abc.Traversable], ...]:
    rows: list[tuple[Path, resources.abc.Traversable]] = []
    for child in root.iterdir():
        relative = prefix / child.name
        if child.is_dir():
            rows.extend(_resource_files(child, relative))
        elif child.is_file():
            rows.append((relative, child))
    return tuple(rows)


__all__ = [
    "asset_href",
    "ensure_brand_assets",
    "render_brand_head_html",
    "tooling_shell_brand_payload",
]
