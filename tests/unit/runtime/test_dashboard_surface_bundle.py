from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.surfaces import dashboard_surface_bundle


def test_standard_surface_bundle_spec_builds_expected_bootstrap_contract() -> None:
    spec = dashboard_surface_bundle.standard_surface_bundle_spec(
        asset_prefix="tooling",
        payload_global_name="__ODYLITH_TOOLING_DATA__",
        embedded_json_script_id="toolingDashboardData",
        bootstrap_binding_name="payload",
    )

    assert spec.asset_prefix == "tooling"
    assert spec.payload_global_name == "__ODYLITH_TOOLING_DATA__"
    assert spec.embedded_json_script_id == "toolingDashboardData"
    assert spec.control_bootstrap_snippet == (
        'const payload = JSON.parse(document.getElementById("toolingDashboardData").textContent);'
    )
    assert spec.control_bootstrap_replacement == (
        'const payload = window["__ODYLITH_TOOLING_DATA__"] || {};'
    )
    assert spec.shell_embed_only is None


def test_standard_surface_bundle_spec_can_build_shell_embed_surface_contract() -> None:
    spec = dashboard_surface_bundle.standard_surface_bundle_spec(
        asset_prefix="registry",
        payload_global_name="__ODYLITH_REGISTRY_DATA__",
        embedded_json_script_id="registryData",
        bootstrap_binding_name="DATA",
        allow_missing_embedded_json=True,
        shell_tab="registry",
        shell_frame_id="frame-registry",
        query_passthrough=(("component", ("component",)),),
    )

    assert spec.control_bootstrap_snippet == (
        'const DATA = JSON.parse(document.getElementById("registryData").textContent || "{}");'
    )
    assert spec.control_bootstrap_replacement == (
        'const DATA = window["__ODYLITH_REGISTRY_DATA__"] || {};'
    )
    assert spec.shell_embed_only == dashboard_surface_bundle.ShellEmbedOnlySpec(
        shell_tab="registry",
        shell_frame_id="frame-registry",
        shell_href="../index.html",
        query_passthrough=(("component", ("component",)),),
    )


def test_standard_surface_bundle_spec_requires_complete_shell_embed_pair() -> None:
    with pytest.raises(ValueError, match="shell_tab and shell_frame_id"):
        dashboard_surface_bundle.standard_surface_bundle_spec(
            asset_prefix="registry",
            payload_global_name="__ODYLITH_REGISTRY_DATA__",
            embedded_json_script_id="registryData",
            bootstrap_binding_name="DATA",
            shell_tab="registry",
        )


def test_append_query_param_preserves_existing_query_and_overwrites_same_key() -> None:
    href = dashboard_surface_bundle.append_query_param(
        href="compass.html?v=old&workstream=B-027",
        name="v",
        value="fresh",
    )

    assert href == "compass.html?workstream=B-027&v=fresh"


def test_externalize_surface_bundle_versions_payload_and_control_hrefs() -> None:
    spec = dashboard_surface_bundle.standard_surface_bundle_spec(
        asset_prefix="tooling",
        payload_global_name="__ODYLITH_TOOLING_DATA__",
        embedded_json_script_id="toolingDashboardData",
        bootstrap_binding_name="payload",
    )
    html_text = """
<html><body>
  <script id="toolingDashboardData" type="application/json">{}</script>
  <script>const payload = JSON.parse(document.getElementById("toolingDashboardData").textContent); init(payload);</script>
</body></html>
""".strip()
    bundled_html, payload_js, control_js = dashboard_surface_bundle.externalize_surface_bundle(
        html_text=html_text,
        payload={"generated_utc": "2026-04-05T20:00:00Z", "radar_href": "radar/radar.html"},
        paths=dashboard_surface_bundle.SurfaceBundlePaths(
            html_path=Path("tooling.html"),
            payload_js_path=Path("tooling-payload.v1.js"),
            control_js_path=Path("tooling-app.v1.js"),
        ),
        spec=spec,
    )

    assert 'src="tooling-payload.v1.js?v=' in bundled_html
    assert 'src="tooling-app.v1.js?v=' in bundled_html
    assert 'textContent' not in control_js
    assert '__ODYLITH_TOOLING_DATA__' in payload_js
