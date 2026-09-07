"""The catalog delegates viewport state instead of retaining a competing owner."""

import inspect

from odylith.runtime.surfaces import atlas_viewer_viewport_runtime as viewport
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
