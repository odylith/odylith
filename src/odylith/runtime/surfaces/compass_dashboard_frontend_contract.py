"""Load the source-owned Compass shell frontend contract."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import execution_wave_ui_runtime_primitives


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
        output_name="compass-runtime-truth.v1.js",
        template_name="compass-runtime-truth.v1.js",
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
        output_name="compass-releases.v1.js",
        template_name="compass-releases.v1.js",
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
_COMPASS_DEEP_LINK_BUTTON_CONTRACT_TOKEN = "__ODYLITH_COMPASS_DEEP_LINK_BUTTON_CONTRACT__"
_COMPASS_WORKSTREAM_BUTTON_CONTRACT_TOKEN = "__ODYLITH_COMPASS_WORKSTREAM_BUTTON_CONTRACT__"
_COMPASS_KPI_GRID_CONTRACT_TOKEN = "__ODYLITH_COMPASS_KPI_GRID_CONTRACT__"
_COMPASS_KPI_CARD_CONTRACT_TOKEN = "__ODYLITH_COMPASS_KPI_CARD_CONTRACT__"
_COMPASS_KPI_TYPOGRAPHY_CONTRACT_TOKEN = "__ODYLITH_COMPASS_KPI_TYPOGRAPHY_CONTRACT__"
_COMPASS_CARD_SURFACE_CONTRACT_TOKEN = "__ODYLITH_COMPASS_CARD_SURFACE_CONTRACT__"


def _template_asset_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "templates" / "compass_dashboard" / filename


def compass_shell_style_assets() -> tuple[CompassShellAsset, ...]:
    return _STYLE_ASSETS


def compass_shell_support_js_assets() -> tuple[CompassShellAsset, ...]:
    return _SUPPORT_JS_ASSETS


def _resolved_template_text(filename: str) -> str:
    return dashboard_ui_primitives.resolve_surface_shell_template_tokens(
        _template_asset_path(filename).read_text(encoding="utf-8")
    )


def _load_compass_shell_base_css() -> str:
    resolved = _resolved_template_text("compass-style-base.v1.css")
    replacements = {
        _COMPASS_DEEP_LINK_BUTTON_CONTRACT_TOKEN: dashboard_ui_primitives.detail_action_chip_css(
            selector=".pill, .chip-link:not(.workstream-id-chip):not(.execution-wave-chip-link)"
        ),
        _COMPASS_WORKSTREAM_BUTTON_CONTRACT_TOKEN: dashboard_ui_primitives.surface_workstream_button_chip_css(
            selector=".ws-id-btn, .workstream-id-chip"
        ),
        _COMPASS_KPI_GRID_CONTRACT_TOKEN: dashboard_ui_primitives.kpi_grid_layout_css(
            container_selector=".stats",
        ),
        _COMPASS_KPI_CARD_CONTRACT_TOKEN: dashboard_ui_primitives.kpi_card_surface_css(
            card_selector=".stat",
        ),
        _COMPASS_KPI_TYPOGRAPHY_CONTRACT_TOKEN: dashboard_ui_primitives.governance_kpi_label_value_css(
            label_selector=".stat .kpi-label",
            value_selector=".stat .kpi-value",
        ),
        _COMPASS_CARD_SURFACE_CONTRACT_TOKEN: dashboard_ui_primitives.panel_surface_css(
            selector=".card",
            padding="12px",
            radius_px=14,
            gap_px=8,
            border_color="#dbeafe",
            background="linear-gradient(180deg, #ffffff, #fbfdff)",
            shadow="0 6px 18px rgba(15, 23, 42, 0.04)",
        ),
    }
    for token in replacements:
        if token not in resolved:
            raise ValueError(f"could not locate Compass shell contract marker {token} in base CSS")
    for token, css in replacements.items():
        resolved = resolved.replace(token, css)
    return resolved


def _load_compass_execution_wave_css() -> str:
    shared_css = execution_wave_ui_runtime_primitives.execution_wave_component_css().strip()
    override_css = _resolved_template_text("compass-style-execution-waves.v1.css").strip()
    if override_css:
        return f"{shared_css}\n\n{override_css}\n"
    return f"{shared_css}\n"


@lru_cache(maxsize=None)
def load_compass_shell_asset_text(filename: str) -> str:
    if filename == "compass-style-base.v1.css":
        return _load_compass_shell_base_css()
    if filename == "compass-style-execution-waves.v1.css":
        return _load_compass_execution_wave_css()
    return _resolved_template_text(filename)


@lru_cache(maxsize=1)
def load_compass_shell_control_js() -> str:
    source_js = load_compass_shell_asset_text("compass-control.js").rstrip()
    if _INLINE_JSON_BOOTSTRAP not in source_js:
        raise ValueError("could not locate Compass payload bootstrap in shell control source")
    return source_js
