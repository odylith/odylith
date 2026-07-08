"""Brand Assets helpers for the Odylith surfaces layer."""

from __future__ import annotations

import base64
import hashlib
import html
import os
from collections.abc import Mapping
from importlib import resources
from pathlib import Path

_BRAND_ROOT = Path("odylith/surfaces/brand")
_FAVICON_ROOT = _BRAND_ROOT / "favicon"
_ICON_ROOT = _BRAND_ROOT / "icon"
_LOCKUP_ROOT = _BRAND_ROOT / "lockup"
_PACKAGED_BRAND_ROOT = "bundle/assets/odylith/surfaces/brand"
_BRAND_PAYLOAD_ENCODING = "base64"


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


def precompiled_brand_asset_writes(*, repo_root: Path) -> dict[str, dict[str, str]]:
    """Return missing managed brand asset writes for ProductCreateTransaction sealing."""

    root = Path(repo_root).expanduser().resolve()
    writes: dict[str, dict[str, str]] = {}
    for token, payload in _packaged_brand_asset_payloads().items():
        target = root / token
        if not target.is_file() or target.stat().st_size <= 0:
            writes[token] = payload
    return writes


def require_precompiled_brand_assets(*, repo_root: Path, brand_asset_writes: object) -> None:
    """Fail before the write boundary when required brand assets were not sealed."""

    root = Path(repo_root).expanduser().resolve()
    writes = _brand_asset_write_mapping(brand_asset_writes)
    packaged = _packaged_brand_asset_payloads()
    for token, payload in writes.items():
        if token not in packaged:
            raise ValueError(
                f"ProductCreateTransaction contains an unapproved brand asset write {token!r}; "
                "rebuild the pre-confirm transaction before committing governed records"
            )
        _brand_asset_bytes(token=token, payload=payload, packaged_payload=packaged[token])
    missing = [
        token
        for token in packaged
        if (not (root / token).is_file() or (root / token).stat().st_size <= 0) and token not in writes
    ]
    if missing:
        raise ValueError(
            "ProductCreateTransaction is missing precompiled brand asset writes for "
            + ", ".join(missing)
            + "; rebuild the pre-confirm transaction before committing governed records"
        )


def materialize_precompiled_brand_assets(*, repo_root: Path, brand_asset_writes: object) -> tuple[Path, ...]:
    """Write only managed brand assets already sealed inside the transaction."""

    root = Path(repo_root).expanduser().resolve()
    writes = _brand_asset_write_mapping(brand_asset_writes)
    packaged = _packaged_brand_asset_payloads()
    require_precompiled_brand_assets(repo_root=root, brand_asset_writes=writes)
    materialized: list[Path] = []
    for token, payload in writes.items():
        target = _brand_asset_target(root=root, token=token)
        data = _brand_asset_bytes(token=token, payload=payload, packaged_payload=packaged[token])
        if target.is_file() and target.stat().st_size > 0:
            if target.read_bytes() != data:
                raise RuntimeError(f"compiled brand asset target changed after confirmation: {token}")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        materialized.append(target)
    return tuple(materialized)


def _packaged_brand_asset_payloads() -> dict[str, dict[str, str]]:
    source_root = resources.files("odylith").joinpath(_PACKAGED_BRAND_ROOT)
    payloads: dict[str, dict[str, str]] = {}
    for relative, source in _resource_files(source_root):
        if relative.name == ".DS_Store":
            continue
        data = source.read_bytes()
        token = (_BRAND_ROOT / relative).as_posix()
        payloads[token] = {
            "encoding": _BRAND_PAYLOAD_ENCODING,
            "sha256": hashlib.sha256(data).hexdigest(),
            "content_base64": base64.b64encode(data).decode("ascii"),
        }
    return payloads


def _brand_asset_write_mapping(value: object) -> dict[str, dict[str, str]]:
    if not isinstance(value, Mapping):
        return {}
    writes: dict[str, dict[str, str]] = {}
    for raw_token, raw_payload in value.items():
        if isinstance(raw_payload, Mapping):
            writes[str(raw_token)] = {str(key): str(item) for key, item in raw_payload.items()}
        else:
            raise ValueError(f"ProductCreateTransaction brand asset write {raw_token!r} is not a payload")
    return writes


def _brand_asset_bytes(*, token: str, payload: dict[str, str], packaged_payload: dict[str, str]) -> bytes:
    if payload.get("encoding") != _BRAND_PAYLOAD_ENCODING:
        raise ValueError(f"ProductCreateTransaction brand asset write has unsupported encoding: {token}")
    try:
        data = base64.b64decode(payload.get("content_base64", ""), validate=True)
    except ValueError as exc:
        raise ValueError(f"ProductCreateTransaction brand asset write is not valid base64: {token}") from exc
    digest = hashlib.sha256(data).hexdigest()
    if digest != payload.get("sha256") or digest != packaged_payload.get("sha256"):
        raise ValueError(f"ProductCreateTransaction brand asset write hash mismatch: {token}")
    return data


def _brand_asset_target(*, root: Path, token: str) -> Path:
    relative = Path(token)
    if relative.is_absolute() or ".." in relative.parts or not token.startswith(_BRAND_ROOT.as_posix() + "/"):
        raise RuntimeError(f"compiled brand asset write escapes managed brand root: {token}")
    target = (root / relative).resolve()
    try:
        target.relative_to(root)
    except ValueError as exc:
        raise RuntimeError(f"compiled brand asset write escapes repo root: {token}") from exc
    return target


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
    "materialize_precompiled_brand_assets",
    "precompiled_brand_asset_writes",
    "render_brand_head_html",
    "require_precompiled_brand_assets",
    "tooling_shell_brand_payload",
]
