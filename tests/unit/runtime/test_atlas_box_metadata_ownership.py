"""Atlas box metadata has one literal-text presentation owner."""

import inspect

from odylith.runtime.surfaces import atlas_detail_layout as details
from odylith.runtime.surfaces import render_mermaid_catalog as catalog


def test_catalog_delegates_box_metadata_without_a_second_text_interpreter() -> None:
    source = inspect.getsource(catalog)
    assert "function renderDiagramBoxes(" not in source
    assert "renderDiagramBoxes(diagram, diagramBoxesSectionEl, diagramBoxListEl);" in source
    runtime = details.DETAIL_RUNTIME_HELPERS_JS
    assert "function renderDiagramBoxes(diagram, sectionEl, listEl)" in runtime
    assert "displayText(box." not in runtime
    for field in ("label", "role", "description"):
        assert f"String(box.{field} ?? \"\")" in runtime
    html = catalog._render_html(
        diagrams=[], stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-08T00:00:00Z",
        brand_head_html="", tooling_base_href="../index.html",
    )
    assert html.count("function renderDiagramBoxes(") == 1
    assert "__ODYLITH_ATLAS_DETAIL_RUNTIME_HELPERS__" not in html
