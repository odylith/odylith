"""Load the source-owned Compass shell frontend contract."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True)
class CompassShellAsset:
    output_name: str
    template_name: str


_STYLE_ASSETS = (
    CompassShellAsset(
        output_name="compass-style-base.v1.css",
        template_name="compass-style-base.v1.css",
    ),
    CompassShellAsset(
        output_name="compass-style-execution-waves.v1.css",
        template_name="compass-style-execution-waves.v1.css",
    ),
    CompassShellAsset(
        output_name="compass-style-surface.v1.css",
        template_name="compass-style-surface.v1.css",
    ),
)

_SUPPORT_JS_ASSETS = (
    CompassShellAsset(
        output_name="compass-shared.v1.js",
        template_name="compass-shared.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-state.v1.js",
        template_name="compass-state.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-summary.v1.js",
        template_name="compass-summary.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-timeline.v1.js",
        template_name="compass-timeline.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-waves.v1.js",
        template_name="compass-waves.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-workstreams.v1.js",
        template_name="compass-workstreams.v1.js",
    ),
    CompassShellAsset(
        output_name="compass-ui-runtime.v1.js",
        template_name="compass-ui-runtime.v1.js",
    ),
)

_INLINE_JSON_BOOTSTRAP = 'const SHELL = JSON.parse(document.getElementById("compassShellData").textContent);'


def _template_asset_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "templates" / "compass_dashboard" / filename


def compass_shell_style_assets() -> tuple[CompassShellAsset, ...]:
    return _STYLE_ASSETS


def compass_shell_support_js_assets() -> tuple[CompassShellAsset, ...]:
    return _SUPPORT_JS_ASSETS


@lru_cache(maxsize=None)
def load_compass_shell_asset_text(filename: str) -> str:
    return _template_asset_path(filename).read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def load_compass_shell_control_js() -> str:
    source_js = load_compass_shell_asset_text("compass-control.js").rstrip()
    if _INLINE_JSON_BOOTSTRAP not in source_js:
        raise ValueError("could not locate Compass payload bootstrap in shell control source")
    return source_js
