"""The Atlas producer, not an edited generated mirror, owns asset recovery."""

import inspect

from odylith.runtime.surfaces import atlas_viewer_asset_runtime
from odylith.runtime.surfaces import render_mermaid_catalog


def test_fresh_atlas_render_contains_accessible_asset_failure_and_reset() -> None:
    html = render_mermaid_catalog._render_html(
        diagrams=[],
        stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21,
        tooltip_lookup={},
        generated_utc="2026-09-04T00:00:00Z",
        brand_head_html="",
        tooling_base_href="../index.html",
    )

    assert 'imageErrorEl.id = "viewerAssetError"' in html
    assert 'imageErrorEl.setAttribute("role", "alert")' in html
    assert 'if (!fallback || imageEl.dataset.fallbackApplied === "1")' in html
    assert 'imageEl.hidden = true;' in html
    assert 'Diagram preview unavailable.' in html
    assert 'imageEl.src = fallback;' in html
    assert 'imageEl.onload = () => {' in html
    assert 'imageErrorEl.classList.remove("visible")' in html
    assert 'imageEl.hidden = false;' in html


def test_atlas_viewer_asset_lifecycle_stays_in_its_template_owner() -> None:
    renderer_source = inspect.getsource(render_mermaid_catalog)

    assert "__ODYLITH_ATLAS_VIEWER_ASSET_INITIALIZATION__" in renderer_source
    assert "__ODYLITH_ATLAS_VIEWER_ASSET_CLEAR__" in renderer_source
    assert "__ODYLITH_ATLAS_VIEWER_ASSET_LOAD__" in renderer_source
    assert 'imageErrorEl.id = "viewerAssetError"' not in renderer_source
    assert 'imageEl.src = fallback;' not in renderer_source
    assert (
        'imageErrorEl.id = "viewerAssetError"'
        in atlas_viewer_asset_runtime.VIEWER_ASSET_INITIALIZATION_JS
    )
    assert 'imageEl.src = fallback;' in atlas_viewer_asset_runtime.VIEWER_ASSET_LOAD_JS
    assert "Diagram preview unavailable." in atlas_viewer_asset_runtime.VIEWER_ASSET_LOAD_JS
