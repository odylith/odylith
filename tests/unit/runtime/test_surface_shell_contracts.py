from __future__ import annotations

from pathlib import Path
import re

import pytest

from odylith.runtime.surfaces import compass_dashboard_frontend_contract
from odylith.runtime.surfaces import dashboard_ui_primitives


REPO_ROOT = Path(__file__).resolve().parents[3]
_COMPASS_SHELL_ASSET_NAMES = tuple(
    asset.output_name
    for asset in (
        *compass_dashboard_frontend_contract.compass_shell_style_assets(),
        *compass_dashboard_frontend_contract.compass_shell_support_js_assets(),
    )
)
_SURFACE_LIVE_BUNDLE_MIRROR_PATHS = (
    ("odylith/index.html", "src/odylith/bundle/assets/odylith/index.html"),
    ("odylith/tooling-app.v1.js", "src/odylith/bundle/assets/odylith/tooling-app.v1.js"),
    ("odylith/tooling-payload.v1.js", "src/odylith/bundle/assets/odylith/tooling-payload.v1.js"),
    ("odylith/radar/radar.html", "src/odylith/bundle/assets/odylith/radar/radar.html"),
    ("odylith/radar/backlog-app.v1.js", "src/odylith/bundle/assets/odylith/radar/backlog-app.v1.js"),
    ("odylith/radar/backlog-payload.v1.js", "src/odylith/bundle/assets/odylith/radar/backlog-payload.v1.js"),
    ("odylith/radar/standalone-pages.v1.js", "src/odylith/bundle/assets/odylith/radar/standalone-pages.v1.js"),
    ("odylith/registry/registry.html", "src/odylith/bundle/assets/odylith/registry/registry.html"),
    ("odylith/registry/registry-app.v1.js", "src/odylith/bundle/assets/odylith/registry/registry-app.v1.js"),
    ("odylith/registry/registry-payload.v1.js", "src/odylith/bundle/assets/odylith/registry/registry-payload.v1.js"),
    (
        "odylith/registry/registry-detail-shard-001.v1.js",
        "src/odylith/bundle/assets/odylith/registry/registry-detail-shard-001.v1.js",
    ),
    ("odylith/casebook/casebook.html", "src/odylith/bundle/assets/odylith/casebook/casebook.html"),
    (
        "odylith/casebook/casebook-app.v1.js",
        "src/odylith/bundle/assets/odylith/casebook/casebook-app.v1.js",
    ),
    (
        "odylith/casebook/casebook-payload.v1.js",
        "src/odylith/bundle/assets/odylith/casebook/casebook-payload.v1.js",
    ),
    ("odylith/atlas/atlas.html", "src/odylith/bundle/assets/odylith/atlas/atlas.html"),
    ("odylith/atlas/mermaid-app.v1.js", "src/odylith/bundle/assets/odylith/atlas/mermaid-app.v1.js"),
    (
        "odylith/atlas/mermaid-payload.v1.js",
        "src/odylith/bundle/assets/odylith/atlas/mermaid-payload.v1.js",
    ),
    ("odylith/compass/compass.html", "src/odylith/bundle/assets/odylith/compass/compass.html"),
    ("odylith/compass/compass-app.v1.js", "src/odylith/bundle/assets/odylith/compass/compass-app.v1.js"),
    (
        "odylith/compass/compass-payload.v1.js",
        "src/odylith/bundle/assets/odylith/compass/compass-payload.v1.js",
    ),
)
_SURFACE_LIVE_BUNDLE_MIRROR_GLOBS = (
    (
        REPO_ROOT / "odylith" / "radar",
        "backlog-detail-shard-*.v1.js",
        REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "radar",
    ),
    (
        REPO_ROOT / "odylith" / "radar",
        "backlog-document-shard-*.v1.js",
        REPO_ROOT / "src" / "odylith" / "bundle" / "assets" / "odylith" / "radar",
    ),
)


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _has_versioned_script_tag(*, html: str, src: str, script_id: str | None = None) -> bool:
    attrs = [f'src="{re.escape(src)}(?:\\?v=[^"]+)?"']
    if script_id is not None:
        attrs.insert(0, f'id="{re.escape(script_id)}"')
    return re.search("<script " + " ".join(attrs) + "></script>", html) is not None


def test_shell_index_declares_all_surface_tabs_and_frames() -> None:
    html = _read("odylith/index.html")

    for tab in ("radar", "registry", "casebook", "atlas", "compass"):
        assert f'id="tab-{tab}"' in html

    for frame_id in ("frame-radar", "frame-registry", "frame-casebook", "frame-atlas", "frame-compass"):
        assert f'id="{frame_id}"' in html


@pytest.mark.parametrize(
    ("path", "tab", "frame_id", "payload_id", "payload_src", "app_src", "query_targets"),
    (
        (
            "odylith/radar/radar.html",
            "radar",
            "frame-radar",
            "backlogData",
            "backlog-payload.v1.js",
            "backlog-app.v1.js",
            ("view", "workstream"),
        ),
        (
            "odylith/registry/registry.html",
            "registry",
            "frame-registry",
            "registryData",
            "registry-payload.v1.js",
            "registry-app.v1.js",
            ("component",),
        ),
        (
            "odylith/casebook/casebook.html",
            "casebook",
            "frame-casebook",
            "casebookData",
            "casebook-payload.v1.js",
            "casebook-app.v1.js",
            ("bug", "severity", "status"),
        ),
        (
            "odylith/atlas/atlas.html",
            "atlas",
            "frame-atlas",
            "catalogData",
            "mermaid-payload.v1.js",
            "mermaid-app.v1.js",
            ("workstream", "diagram"),
        ),
        (
            "odylith/compass/compass.html",
            "compass",
            "frame-compass",
            "compassShellData",
            "compass-payload.v1.js",
            "compass-app.v1.js",
            ("scope", "window", "date", "audit_day"),
        ),
    ),
)
def test_standalone_surface_html_keeps_shell_embed_contract(
    path: str,
    tab: str,
    frame_id: str,
    payload_id: str,
    payload_src: str,
    app_src: str,
    query_targets: tuple[str, ...],
) -> None:
    html = _read(path)

    assert f'const expectedFrameId = "{frame_id}";' in html
    assert f'nextParams.set("tab", "{tab}");' in html
    assert _has_versioned_script_tag(html=html, src=payload_src, script_id=payload_id)
    assert _has_versioned_script_tag(html=html, src=app_src)

    for token in query_targets:
        assert f'"target":"{token}"' in html


@pytest.mark.parametrize(
    ("path", "assert_shell_max_width_rule"),
    (
        ("odylith/index.html", False),
        ("odylith/radar/radar.html", True),
        ("odylith/registry/registry.html", True),
        ("odylith/casebook/casebook.html", True),
    ),
)
def test_non_atlas_surfaces_share_standard_shell_width_contract(
    path: str,
    assert_shell_max_width_rule: bool,
) -> None:
    html = _read(path)
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH

    assert f"--surface-shell-max-width: {expected_width};" in html
    if assert_shell_max_width_rule:
        assert f"max-width: var(--surface-shell-max-width, {expected_width});" in html


def test_radar_standalone_pages_share_standard_shell_width_contract() -> None:
    js = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "odylith" / "radar").glob("backlog-document-shard-*.v1.js"))
    )
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH

    assert f"--surface-shell-max-width: {expected_width};" in js
    assert f"max-width: var(--surface-shell-max-width, {expected_width});" in js


def test_compass_shell_base_css_shares_standard_shell_width_contract() -> None:
    css = _read("odylith/compass/compass-style-base.v1.css")
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH
    expected_identifier_padding = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_CHIP_PADDING
    expected_identifier_size = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_FONT_SIZE
    expected_identifier_weight = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_FONT_WEIGHT
    expected_workstream_padding = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING
    expected_workstream_size = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE
    expected_workstream_weight = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT
    expected_deep_link_padding = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING
    expected_deep_link_size = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE
    expected_deep_link_weight = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT
    expected_stats_grid_css = dashboard_ui_primitives.kpi_grid_layout_css(container_selector=".stats")
    expected_stat_card_css = dashboard_ui_primitives.kpi_card_surface_css(card_selector=".stat")
    expected_stat_typography_css = dashboard_ui_primitives.governance_kpi_label_value_css(
        label_selector=".stat .kpi-label",
        value_selector=".stat .kpi-value",
    )
    expected_card_surface_css = dashboard_ui_primitives.panel_surface_css(
        selector=".card",
        padding="12px",
        radius_px=14,
        gap_px=8,
        border_color="#dbeafe",
        background="linear-gradient(180deg, #ffffff, #fbfdff)",
        shadow="0 6px 18px rgba(15, 23, 42, 0.04)",
    )

    assert "__ODYLITH_STANDARD_SURFACE_SHELL_MAX_WIDTH__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_CHIP_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_FONT_WEIGHT__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT__" not in css
    assert "__ODYLITH_COMPASS_DEEP_LINK_BUTTON_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_WORKSTREAM_BUTTON_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_KPI_GRID_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_KPI_CARD_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_KPI_TYPOGRAPHY_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_CARD_SURFACE_CONTRACT__" not in css
    assert expected_stats_grid_css in css
    assert expected_stat_card_css in css
    assert expected_stat_typography_css in css
    assert expected_card_surface_css in css
    assert f"--surface-shell-max-width: {expected_width};" in css
    assert f"--surface-identifier-chip-padding: {expected_identifier_padding};" in css
    assert f"--surface-identifier-font-size: {expected_identifier_size};" in css
    assert f"--surface-identifier-font-weight: {expected_identifier_weight};" in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}: "
        f"{expected_workstream_padding};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{expected_workstream_size};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{expected_workstream_weight};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}: "
        f"{expected_deep_link_padding};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{expected_deep_link_size};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{expected_deep_link_weight};"
    ) in css
    assert f"max-width: var(--surface-shell-max-width, {expected_width});" in css
    assert f"font-size: var(--surface-identifier-font-size, {expected_identifier_size});" in css
    assert f"font-weight: var(--surface-identifier-font-weight, {expected_identifier_weight});" in css
    assert (
        f"padding: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{expected_workstream_padding});"
    ) in css
    assert (
        f"font-size: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{expected_workstream_size});"
    ) in css
    assert (
        f"padding: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}, "
        f"{expected_deep_link_padding});"
    ) in css
    assert (
        f"font-size: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{expected_deep_link_size});"
    ) in css
    assert ".card.release-groups-card .execution-wave-board {" not in css
    assert (
        f"font-weight: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{expected_workstream_weight});"
    ) in css
    assert (
        f"font-weight: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{expected_deep_link_weight});"
    ) in css
    assert ".pill, .ws-id-btn, .chip-link {" not in css
    assert ".pill, .chip-link:not(.workstream-id-chip):not(.execution-wave-chip-link) {" in css
    assert ".ws-id-btn, .workstream-id-chip {" in css


@pytest.mark.parametrize(
    ("path", "assert_shell_max_width_rule"),
    (
        ("src/odylith/bundle/assets/odylith/index.html", False),
        ("src/odylith/bundle/assets/odylith/radar/radar.html", True),
        ("src/odylith/bundle/assets/odylith/registry/registry.html", True),
        ("src/odylith/bundle/assets/odylith/casebook/casebook.html", True),
    ),
)
def test_bundle_non_atlas_surfaces_share_standard_shell_width_contract(
    path: str,
    assert_shell_max_width_rule: bool,
) -> None:
    html = _read(path)
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH

    assert f"--surface-shell-max-width: {expected_width};" in html
    if assert_shell_max_width_rule:
        assert f"max-width: var(--surface-shell-max-width, {expected_width});" in html


def test_bundle_compass_shell_base_css_shares_standard_shell_width_contract() -> None:
    css = _read("src/odylith/bundle/assets/odylith/compass/compass-style-base.v1.css")
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH
    expected_identifier_padding = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_CHIP_PADDING
    expected_identifier_size = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_FONT_SIZE
    expected_identifier_weight = dashboard_ui_primitives.STANDARD_SURFACE_IDENTIFIER_FONT_WEIGHT
    expected_workstream_padding = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING
    expected_workstream_size = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE
    expected_workstream_weight = dashboard_ui_primitives.STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT
    expected_deep_link_padding = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING
    expected_deep_link_size = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE
    expected_deep_link_weight = dashboard_ui_primitives.STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT

    assert "__ODYLITH_STANDARD_SURFACE_SHELL_MAX_WIDTH__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_CHIP_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_IDENTIFIER_FONT_WEIGHT__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_PADDING__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_SIZE__" not in css
    assert "__ODYLITH_STANDARD_SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT__" not in css
    assert "__ODYLITH_COMPASS_DEEP_LINK_BUTTON_CONTRACT__" not in css
    assert "__ODYLITH_COMPASS_WORKSTREAM_BUTTON_CONTRACT__" not in css
    assert f"--surface-shell-max-width: {expected_width};" in css
    assert f"--surface-identifier-chip-padding: {expected_identifier_padding};" in css
    assert f"--surface-identifier-font-size: {expected_identifier_size};" in css
    assert f"--surface-identifier-font-weight: {expected_identifier_weight};" in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}: "
        f"{expected_workstream_padding};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{expected_workstream_size};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{expected_workstream_weight};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}: "
        f"{expected_deep_link_padding};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}: "
        f"{expected_deep_link_size};"
    ) in css
    assert (
        f"{dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}: "
        f"{expected_deep_link_weight};"
    ) in css
    assert f"max-width: var(--surface-shell-max-width, {expected_width});" in css
    assert f"font-size: var(--surface-identifier-font-size, {expected_identifier_size});" in css
    assert f"font-weight: var(--surface-identifier-font-weight, {expected_identifier_weight});" in css
    assert (
        f"padding: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_PADDING_CSS_VAR}, "
        f"{expected_workstream_padding});"
    ) in css
    assert (
        f"font-size: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{expected_workstream_size});"
    ) in css
    assert (
        f"padding: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_PADDING_CSS_VAR}, "
        f"{expected_deep_link_padding});"
    ) in css
    assert (
        f"font-size: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_SIZE_CSS_VAR}, "
        f"{expected_deep_link_size});"
    ) in css
    assert ".card.release-groups-card .execution-wave-board {" not in css
    assert (
        f"font-weight: var({dashboard_ui_primitives.SURFACE_WORKSTREAM_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{expected_workstream_weight});"
    ) in css
    assert (
        f"font-weight: var({dashboard_ui_primitives.SURFACE_DEEP_LINK_BUTTON_FONT_WEIGHT_CSS_VAR}, "
        f"{expected_deep_link_weight});"
    ) in css
    assert ".pill, .ws-id-btn, .chip-link {" not in css
    assert ".pill, .chip-link:not(.workstream-id-chip):not(.execution-wave-chip-link) {" in css
    assert ".ws-id-btn, .workstream-id-chip {" in css


@pytest.mark.parametrize(
    "path",
    (
        "odylith/radar/radar.html",
        "src/odylith/bundle/assets/odylith/radar/radar.html",
    ),
)
def test_radar_release_kpi_tile_keeps_shared_governance_stat_card_contract(path: str) -> None:
    html = _read(path)

    assert ".stat.stat-release-only {" not in html
    assert ".stat.stat-release-only .value {" not in html


@pytest.mark.parametrize("asset_name", _COMPASS_SHELL_ASSET_NAMES)
def test_live_compass_shell_assets_match_source_owned_frontend_contract(asset_name: str) -> None:
    expected = compass_dashboard_frontend_contract.load_compass_shell_asset_text(asset_name)

    assert _read(f"odylith/compass/{asset_name}") == expected


@pytest.mark.parametrize("asset_name", _COMPASS_SHELL_ASSET_NAMES)
def test_bundle_compass_shell_assets_match_source_owned_frontend_contract(asset_name: str) -> None:
    expected = compass_dashboard_frontend_contract.load_compass_shell_asset_text(asset_name)

    assert _read(f"src/odylith/bundle/assets/odylith/compass/{asset_name}") == expected


@pytest.mark.parametrize(("live_path", "bundle_path"), _SURFACE_LIVE_BUNDLE_MIRROR_PATHS)
def test_surface_bundle_mirror_artifacts_match_live_checked_in_outputs(
    live_path: str,
    bundle_path: str,
) -> None:
    assert _read(bundle_path) == _read(live_path)


@pytest.mark.parametrize(("live_dir", "pattern", "bundle_dir"), _SURFACE_LIVE_BUNDLE_MIRROR_GLOBS)
def test_globbed_surface_bundle_mirror_artifacts_match_live_checked_in_outputs(
    live_dir: Path,
    pattern: str,
    bundle_dir: Path,
) -> None:
    live_matches = sorted(live_dir.glob(pattern))
    bundle_matches = sorted(bundle_dir.glob(pattern))

    assert [path.name for path in bundle_matches] == [path.name for path in live_matches]
    for live_path, bundle_path in zip(live_matches, bundle_matches):
        assert bundle_path.read_text(encoding="utf-8") == live_path.read_text(encoding="utf-8")


def test_atlas_remains_the_wider_shell_width_exception() -> None:
    html = _read("odylith/atlas/atlas.html")
    expected_width = dashboard_ui_primitives.STANDARD_SURFACE_SHELL_MAX_WIDTH

    assert f"--surface-shell-max-width: {expected_width};" not in html
    assert "max-width: 1580px;" in html
