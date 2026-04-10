"""Load the source-owned tooling-shell frontend contract.

The tooling shell keeps its exact visible browser contract, and its bundled
template assets live under `odylith.runtime.surfaces.templates/tooling_dashboard/`
instead of being read back out of generated artifacts.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Literal

from odylith.runtime.surfaces import dashboard_ui_primitives
from odylith.runtime.surfaces import dashboard_ui_runtime_primitives

_PAYLOAD_GLOBAL_BOOTSTRAP = 'const payload = window["__ODYLITH_TOOLING_DATA__"] || {};'
_INLINE_JSON_BOOTSTRAP = 'const payload = JSON.parse(document.getElementById("toolingDashboardData").textContent);'
_FROZEN_HEADER_TEMPLATE_SHA256 = "3955d604fde8797cba2101e88561e219a386228d67f7d2ec7690cd6ee71d1532"
_FROZEN_HEADER_STYLE_SHA256 = "e707ffbe06ac51f66feaef225af8af0a2a5db93af3b0aaac4822c8b784d44c34"


def _template_asset_path(filename: str) -> Path:
    return Path(__file__).resolve().parent / "templates" / "tooling_dashboard" / filename


def _normalized_template_asset_text(filename: str) -> str:
    return _template_asset_path(filename).read_text(encoding="utf-8").replace("\r\n", "\n")


def _extract_frozen_block(
    source: str,
    *,
    start_token: str,
    end_token: str,
    label: str,
    include_end_token: bool,
) -> str:
    start = source.find(start_token)
    if start < 0:
        raise ValueError(f"could not locate frozen {label} start token")
    end = source.find(end_token, start + len(start_token))
    if end < 0:
        raise ValueError(f"could not locate frozen {label} end token")
    block = source[start : end + len(end_token)] if include_end_token else source[start:end]
    return block.rstrip("\n")


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def assert_tooling_shell_header_contract() -> None:
    """Fail closed when the frozen tooling-shell header contract drifts."""

    page_source = _normalized_template_asset_text("page.html.j2")
    header_template = _extract_frozen_block(
        page_source,
        start_token='<header class="toolbar">',
        end_token="    </header>",
        label="tooling shell header template",
        include_end_token=True,
    )
    if _sha256(header_template) != _FROZEN_HEADER_TEMPLATE_SHA256:
        raise ValueError(
            "tooling shell header contract drifted in page.html.j2; "
            "refusing to render a mutated dashboard header"
        )

    style_source = _normalized_template_asset_text("style.css")
    header_style = _extract_frozen_block(
        style_source,
        start_token=".toolbar {",
        end_token=".viewport {",
        label="tooling shell header style",
        include_end_token=False,
    )
    if _sha256(header_style) != _FROZEN_HEADER_STYLE_SHA256:
        raise ValueError(
            "tooling shell header contract drifted in style.css; "
            "refusing to render a mutated dashboard header"
        )


@lru_cache(maxsize=1)
def load_tooling_shell_style_css() -> str:
    base_css = dashboard_ui_primitives.resolve_surface_shell_template_tokens(
        _template_asset_path("style.css").read_text(encoding="utf-8")
    ).rstrip("\n")
    cheatsheet_css = dashboard_ui_primitives.resolve_surface_shell_template_tokens(
        _template_asset_path("cheatsheet_drawer.css").read_text(encoding="utf-8")
    ).rstrip("\n")
    tooltip_surface_css, _tooltip_runtime_js = _tooling_shell_quick_tooltip_bundle()
    return "\n\n".join(
        (
            base_css,
            cheatsheet_css,
            _tooling_shell_shared_typography_css(),
            tooltip_surface_css,
        )
    ).rstrip("\n")


@lru_cache(maxsize=2)
def load_tooling_shell_control_js(
    *,
    payload_mode: Literal["inline_json", "window_global"] = "inline_json",
) -> str:
    source_js = _template_asset_path("control.js").read_text(encoding="utf-8").rstrip()
    if _INLINE_JSON_BOOTSTRAP not in source_js:
        raise ValueError(
            "could not locate tooling payload bootstrap in tooling shell control source"
        )
    if payload_mode == "inline_json":
        resolved_js = source_js
    elif payload_mode == "window_global":
        resolved_js = source_js.replace(_INLINE_JSON_BOOTSTRAP, _PAYLOAD_GLOBAL_BOOTSTRAP, 1)
    else:
        raise ValueError(f"unsupported tooling shell payload mode `{payload_mode}`")
    cheatsheet_js = _template_asset_path("cheatsheet_drawer.js").read_text(encoding="utf-8").rstrip()
    _tooltip_surface_css, tooltip_runtime_js = _tooling_shell_quick_tooltip_bundle()
    return "\n\n".join((resolved_js, tooltip_runtime_js, cheatsheet_js)).rstrip()


@lru_cache(maxsize=1)
def _tooling_shell_quick_tooltip_bundle() -> tuple[str, str]:
    return dashboard_ui_runtime_primitives.quick_tooltip_bundle(
        binding_guard_dataset_key="odylithToolingQuickTooltipBound",
        function_name="initToolingShellQuickTooltips",
    )


def _tooling_shell_shared_typography_css() -> str:
    return "\n\n".join(
        (
            dashboard_ui_primitives.page_body_typography_css(
                selector="html, body",
                color="var(--ink, #203047)",
            ),
            dashboard_ui_primitives.header_typography_css(
                kicker_selector=".toolbar .hero-overline-unused",
                title_selector=".title",
                subtitle_selector=".subtitle",
                title_size_px=26,
                title_margin="0 0 6px",
                subtitle_size_px=14,
                subtitle_line_height=1.5,
            ),
            dashboard_ui_primitives.operator_readout_host_heading_css(
                selector=".brief-drawer-title, .system-status-hero-kicker, .telemetry-section-title",
                color="#27445e",
                size_px=11,
                letter_spacing_em=0.07,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".brief-drawer-note",
                color="#51647f",
                size_px=12,
                line_height=1.35,
            ),
            dashboard_ui_primitives.card_title_typography_css(
                selector=".system-status-hero-title",
                color="#0b1324",
                size_px=16,
                line_height=1.25,
                letter_spacing_em=-0.01,
            ),
            dashboard_ui_primitives.content_copy_css(
                selectors=(
                    ".system-status-hero-note",
                    ".system-status-copy",
                    ".telemetry-bullet-list",
                    ".telemetry-empty",
                ),
                size_px=14,
                line_height=1.55,
                color="#27445e",
            ),
            dashboard_ui_primitives.governance_kpi_label_value_css(
                label_selector=".system-status-label, .telemetry-stat-label",
                value_selector=".system-status-value, .telemetry-stat-value",
                label_color="var(--ink-muted, #64748b)",
                label_weight=400,
                label_size_px=11,
                label_line_height=1.15,
                label_letter_spacing_em=0.06,
                value_color="var(--ink, #0b1324)",
                value_margin="4px 0 0",
                value_size_px=18,
                value_line_height=1.05,
                value_letter_spacing_em=-0.01,
            ),
            dashboard_ui_primitives.auxiliary_heading_css(
                selector=".telemetry-snapshot-label, .telemetry-meter-label, .telemetry-distribution-label, .telemetry-index-label",
                color="#475569",
                size_px=10,
                line_height=1.2,
                letter_spacing_em=0.07,
                weight=700,
            ),
            dashboard_ui_primitives.value_emphasis_typography_css(
                selector=".telemetry-meter-value, .telemetry-snapshot-primary, .telemetry-index-count",
                color="#16324f",
                size_px=13,
                line_height=1.3,
                weight=700,
            ),
            dashboard_ui_primitives.supporting_copy_typography_css(
                selector=".telemetry-snapshot-secondary, .telemetry-stat-note, .telemetry-index-updated",
                color="#64748b",
                size_px=11,
                line_height=1.35,
                weight=500,
            ),
            dashboard_ui_primitives.label_badge_typography_css(
                selector=".system-status-meta, .system-status-hero-chip, .telemetry-capability",
                color="#334155",
                size_px=10,
                line_height=1.0,
                letter_spacing_em=0.04,
                weight=700,
            ),
            dashboard_ui_primitives.mono_identifier_typography_css(
                selector=".telemetry-stat-value-mono",
                color="#16324f",
                size_px=12,
                line_height=1.25,
                weight=700,
            ),
            dashboard_ui_primitives.surface_identifier_link_css(
                selector=".operator-readout .operator-readout-copy a.brief-inline-link",
                color="#1b4e9f",
                hover_color="#173b74",
                border_color="#b9cff7",
                hover_border_color="#5f95e6",
                line_height="inherit",
            ),
        )
    )
