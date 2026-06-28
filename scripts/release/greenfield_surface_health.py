"""Rendered governance surface health checks for greenfield release proof."""

from __future__ import annotations

from html.parser import HTMLParser
import json
from pathlib import Path
from typing import Any


REQUIRED_RENDERED_SURFACES = (
    "odylith/radar/radar.html",
    "odylith/registry/registry.html",
    "odylith/atlas/atlas.html",
    "odylith/compass/compass.html",
    "odylith/casebook/casebook.html",
    "odylith/index.html",
)
SURFACE_PAYLOAD_CONTRACTS = {
    "odylith/radar/radar.html": (
        "backlog-app.v1.js",
        "backlog-payload.v1.js",
    ),
    "odylith/registry/registry.html": (
        "registry-app.v1.js",
        "registry-payload.v1.js",
    ),
    "odylith/atlas/atlas.html": (
        "mermaid-app.v1.js",
        "mermaid-payload.v1.js",
    ),
    "odylith/compass/compass.html": (
        "compass-app.v1.js",
        "compass-payload.v1.js",
    ),
    "odylith/casebook/casebook.html": (
        "casebook-app.v1.js",
        "casebook-payload.v1.js",
    ),
    "odylith/index.html": (
        "tooling-app.v1.js",
        "tooling-payload.v1.js",
    ),
}
INDEX_SHELL_TAB_CONTRACTS = {
    "radar": ("frame-radar", "radar_href", "radar/radar.html"),
    "registry": ("frame-registry", "registry_href", "registry/registry.html"),
    "atlas": ("frame-atlas", "atlas_href", "atlas/atlas.html"),
    "compass": ("frame-compass", "compass_href", "compass/compass.html"),
    "casebook": ("frame-casebook", "casebook_href", "casebook/casebook.html"),
}
SHELL_PAYLOAD_SCRIPT_ID = "toolingDashboardData"
SHELL_PAYLOAD_GLOBAL = "__ODYLITH_TOOLING_DATA__"


def rendered_surface_health_issues(*, repo_root: Path) -> tuple[str, ...]:
    """Return rendered-surface health issues that a nonempty file check misses."""

    root = Path(repo_root)
    issues: list[str] = []
    for relative in REQUIRED_RENDERED_SURFACES:
        path = root / relative
        if not _nonempty(path):
            issues.append(f"rendered surface {relative} is missing or empty")
            continue
        links = _html_asset_links(path)
        for asset_name in SURFACE_PAYLOAD_CONTRACTS.get(relative, ()):
            if asset_name not in links:
                issues.append(f"rendered surface {relative} does not load {asset_name}")
                continue
            asset_path = path.parent / asset_name
            if not _nonempty(asset_path):
                issues.append(f"rendered surface payload {asset_path.relative_to(root)} is missing or empty")
    index_path = root / "odylith/index.html"
    if _nonempty(index_path):
        index_contract = _parse_html(index_path)
        for tab, (frame_id, payload_key, expected_href_prefix) in INDEX_SHELL_TAB_CONTRACTS.items():
            if tab not in index_contract.data_tabs:
                issues.append(f"odylith/index.html is missing shell tab {tab}")
            if frame_id not in index_contract.iframe_ids:
                issues.append(f"odylith/index.html is missing shell frame {frame_id}")
            payload = _shell_payload(repo_root=root, index_contract=index_contract)
            if payload:
                href = str(payload.get(payload_key) or "").strip()
                if not href:
                    issues.append(f"odylith/index.html shell payload is missing {payload_key}")
                elif not href.split("?", 1)[0].split("#", 1)[0].endswith(expected_href_prefix):
                    issues.append(
                        f"odylith/index.html shell payload {payload_key} does not target {expected_href_prefix}"
                    )
            else:
                issues.append("odylith/index.html shell payload is missing or invalid")
    for source in sorted((root / "odylith/atlas/source").glob("*.mmd")):
        for suffix in (".svg", ".png"):
            rendered = source.with_suffix(suffix)
            if not _nonempty(rendered):
                issues.append(f"Atlas diagram {source.relative_to(root)} is missing rendered {suffix[1:]} output")
    return tuple(dict.fromkeys(issues))


def rendered_surface_payload_count(repo_root: Path) -> int:
    root = Path(repo_root)
    count = 0
    for relative, assets in SURFACE_PAYLOAD_CONTRACTS.items():
        html_path = root / relative
        if not _nonempty(html_path):
            continue
        links = _html_asset_links(html_path)
        for asset_name in assets:
            if asset_name in links and _nonempty(html_path.parent / asset_name):
                count += 1
    return count


def atlas_rendered_asset_count(repo_root: Path) -> int:
    source_root = Path(repo_root) / "odylith/atlas/source"
    if not source_root.is_dir():
        return 0
    return sum(
        1
        for source in source_root.glob("*.mmd")
        for suffix in (".svg", ".png")
        if _nonempty(source.with_suffix(suffix))
    )


class _SurfaceAssetParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.assets: set[str] = set()
        self.data_tabs: set[str] = set()
        self.iframe_ids: set[str] = set()
        self.script_sources_by_id: dict[str, str] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {str(key): str(value or "") for key, value in attrs}
        data_tab = attr_map.get("data-tab", "").strip()
        if data_tab:
            self.data_tabs.add(data_tab)
        if tag == "iframe":
            frame_id = attr_map.get("id", "").strip()
            if frame_id:
                self.iframe_ids.add(frame_id)
        if tag == "script" and attr_map.get("id", "").strip() and attr_map.get("src", "").strip():
            self.script_sources_by_id[attr_map["id"].strip()] = attr_map["src"].strip()
        if tag not in {"script", "link"}:
            return
        for key, value in attrs:
            if key not in {"src", "href"} or not value:
                continue
            asset = _normalize_asset_ref(value)
            if asset:
                self.assets.add(asset)


def _html_asset_links(path: Path) -> set[str]:
    return set(_parse_html(path).assets)


def _normalize_asset_ref(value: str) -> str:
    asset = str(value).split("?", 1)[0].split("#", 1)[0].strip()
    while asset.startswith("./"):
        asset = asset[2:]
    return asset


def _parse_html(path: Path) -> _SurfaceAssetParser:
    parser = _SurfaceAssetParser()
    try:
        parser.feed(_read_text(path))
    except Exception:
        return _SurfaceAssetParser()
    return parser


def _shell_payload(*, repo_root: Path, index_contract: _SurfaceAssetParser) -> dict[str, Any]:
    script_src = index_contract.script_sources_by_id.get(SHELL_PAYLOAD_SCRIPT_ID, "")
    asset_name = Path(script_src.split("?", 1)[0].split("#", 1)[0].strip()).name
    if not asset_name:
        return {}
    payload_path = repo_root / "odylith" / asset_name
    text = _read_text(payload_path).strip()
    if not text:
        return {}
    if SHELL_PAYLOAD_GLOBAL not in text:
        return {}
    json_start = text.find("{")
    if json_start < 0:
        return {}
    json_text = text[json_start:].strip()
    try:
        payload, _end = json.JSONDecoder().raw_decode(json_text)
    except json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(errors="replace")
    except FileNotFoundError:
        return ""


def _nonempty(path: Path) -> bool:
    return path.is_file() and path.stat().st_size > 0


__all__ = [
    "INDEX_SHELL_TAB_CONTRACTS",
    "REQUIRED_RENDERED_SURFACES",
    "SHELL_PAYLOAD_SCRIPT_ID",
    "SURFACE_PAYLOAD_CONTRACTS",
    "atlas_rendered_asset_count",
    "rendered_surface_health_issues",
    "rendered_surface_payload_count",
]
