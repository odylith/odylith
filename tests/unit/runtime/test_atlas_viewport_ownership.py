"""The catalog delegates viewport state instead of retaining a competing owner."""

import inspect

from odylith.runtime.surfaces import atlas_viewer_viewport_runtime as viewport
from odylith.runtime.surfaces import atlas_viewer_asset_runtime as viewer
from odylith.runtime.surfaces import render_mermaid_catalog as catalog


def test_catalog_has_one_explicit_viewport_owner() -> None:
    source = inspect.getsource(catalog)
    for declaration in (
        "let scale =", "let offsetX =", "let offsetY =", "let pinchState =",
        "const activePointers =", "function applyImageBoxSizing", "function zoomTo",
        'stageEl.addEventListener("pointerdown"', 'stageEl.addEventListener("wheel"',
    ):
        assert declaration not in source
        assert declaration in viewport.VIEWPORT_RUNTIME_JS
    assert "const viewport = createAtlasViewport({" in source
    html = catalog._render_html(
        diagrams=[], stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-07T00:00:00Z",
        brand_head_html="", tooling_base_href="../index.html",
    )
    assert html.count("function createAtlasViewport(") == 1
    assert "__ODYLITH_ATLAS_VIEWPORT_RUNTIME__" not in html
    assert "viewport.setDiagram(diagram);" in html
    assert "viewport.imageLoaded();" in html
    assert "viewport.clear();" in html


def test_catalog_delegates_selection_lifecycle_to_the_viewer_owner() -> None:
    source = inspect.getsource(catalog)
    assert "const viewer = createAtlasViewer({" in source
    assert "viewer.clear();" in source
    assert "viewer.show(diagram);" in source
    assert 'titleEl.textContent = "";' not in source
    for retired in ("VIEWER_ASSET_INITIALIZATION_JS", "VIEWER_ASSET_CLEAR_JS", "VIEWER_ASSET_LOAD_JS"):
        assert retired not in source
        assert not hasattr(viewer, retired)
    assert "function createAtlasViewer({" in viewer.VIEWER_RUNTIME_JS
    assert "imageEl.hidden = true;" in viewer.VIEWER_RUNTIME_JS
    assert "imageEl.onload = null;" in viewer.VIEWER_RUNTIME_JS
    assert 'mainEl.dataset.selectionEmpty = String(!available);' in viewer.VIEWER_RUNTIME_JS
    assert "activeDiagram" not in viewer.VIEWER_RUNTIME_JS
