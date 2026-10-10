"""Exercise release Atlas custody through the real collapsed-metadata DOM."""

import pytest

from odylith.runtime.surfaces import render_mermaid_catalog, tooling_dashboard_shell_presenter
from tests.unit.install.test_greenfield_browser_surface_proof import _module, authored_contract_browser


@pytest.mark.parametrize("viewport", ["desktop", "mobile"])
def test_generated_atlas_checker_preserves_collapsed_metadata_identity(
    authored_contract_browser, tmp_path_factory: pytest.TempPathFactory, viewport: str,
) -> None:
    module = _module()
    tmp_path = tmp_path_factory.mktemp(f"atlas-collapsed-{viewport}")
    atlas_root = tmp_path / "odylith" / "atlas"
    source = atlas_root / "source"
    source.mkdir(parents=True)
    icon = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg'/>"
    shell = tooling_dashboard_shell_presenter.render_html({
        "atlas_href": "atlas/atlas.html", "shell_brand_lockup_href": icon,
        "brand_head_html": f'<link rel="icon" href="{icon}">',
    })
    (tmp_path / "odylith" / "index.html").write_text(shell, encoding="utf-8")
    diagrams = []
    for sequence, title in ((1, "Dataset Review Flow"), (2, "Records Approval Flow")):
        name = f"diagram-{sequence}.svg"
        (source / name).write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1200" '
            'viewBox="0 0 1800 1200"><rect width="1800" height="1200" fill="white"/>'
            f'<text x="40" y="60" font-size="30">{title}</text></svg>', encoding="utf-8",
        )
        diagrams.append({
            "diagram_id": f"D-{sequence:03}", "title": title, "kind": "flowchart",
            "owner": "Records team", "status": "proposed", "freshness": "fresh",
            "source_svg_href": f"source/{name}", "svg_viewbox_width": 1800,
            "svg_viewbox_height": 1200, "summary": f"Inspect the complete {title.lower()}.",
        })
    html = render_mermaid_catalog._render_html(  # noqa: SLF001
        diagrams=diagrams, stats={"total": 2, "fresh": 2, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-10-09T00:00:00Z",
        brand_head_html=f'<link rel="icon" href="{icon}">', tooling_base_href="../index.html",
    )
    (atlas_root / "atlas.html").write_text(html, encoding="utf-8")
    mobile = viewport == "mobile"
    context = authored_contract_browser.new_context(
        viewport=module.BROWSER_VIEWPORTS[viewport], has_touch=mobile, is_mobile=mobile,
    )
    server, base_url = module._serve_directory(tmp_path)
    try:
        page = context.new_page()
        try:
            response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="networkidle")
            assert response is not None and response.ok
            frame = page.frame_locator("#frame-atlas")
            frame.locator("#viewerImage").wait_for(state="visible")
            assert frame.locator("button[data-diagram]").evaluate_all(
                "nodes => nodes.map(node => node.dataset.diagram)",
            ) == ["D-002", "D-001"]
            metadata = frame.locator("details.diagram-metadata")
            identity = frame.locator("#diagramId")
            assert metadata.get_attribute("open") is None
            assert not identity.is_visible()
            assert identity.inner_text() == ""
            assert identity.text_content() == "D-002"
            assert frame.locator("#diagramTitle").is_visible()
            assert frame.locator("#diagramTitle").inner_text() == "Records Approval Flow"
            page.screenshot(path=str(tmp_path / "collapsed-metadata.png"), full_page=True)
            metadata.locator(":scope > summary").focus()
            metadata.locator(":scope > summary").press("Enter")
            assert identity.is_visible()
            assert identity.inner_text() == "D-002"
            metadata.locator(":scope > summary").press("Enter")
            assert metadata.get_attribute("open") is None
        finally:
            page.close()
        covered = set()
        cell = (viewport, "atlas", "normal")
        issues = module._atlas_generated_state_issues(
            context=context, base_url=base_url, timeout_ms=5000,
            screenshot_output_dir=tmp_path / "checker-screenshots",
            coverage_cell=cell, covered=covered,
        )
        assert issues == ()
        assert covered == {cell}
        expected_names = {
            f"{viewport}-atlas-normal{suffix}.png" for suffix in ("", "-d-002-read-100", "-d-001-read-100")
        }
        if mobile:
            expected_names |= {name.removesuffix(".png") + "-viewport.png" for name in expected_names}
        assert {path.name for path in (tmp_path / "checker-screenshots").glob("*.png")} == expected_names
    finally:
        context.close()
        server.shutdown()
        server.server_close()


@pytest.mark.parametrize("displayed, expected_issue", [
    ("", "browser surface atlas did not hydrate the selected diagram id"),
    ("D-999", "browser surface atlas selected diagram id disagrees with active list state"),
])
def test_atlas_state_still_refuses_missing_or_mismatched_identity(displayed: str, expected_issue: str) -> None:
    issues = _module()._atlas_state_assertion_issues(
        diagram_count=2, stat_total_text="2", active_diagram="D-002", displayed_diagram=displayed,
        displayed_title="Records Approval Flow", image_src="http://localhost/odylith/atlas/source/diagram-2.svg",
        image_loaded=True,
    )
    assert issues == (expected_issue,)


@pytest.mark.parametrize("visited", [("D-002",), ("D-002", "D-002"), ("D-001", "D-002")])
def test_atlas_coverage_still_refuses_missing_duplicate_or_reordered_visits(visited: tuple[str, ...]) -> None:
    assert _module()._atlas_diagram_coverage_issues(("D-002", "D-001"), visited) == (
        "browser surface atlas did not visit every emitted diagram in list order",
    )
