"""An empty Atlas explains absent records instead of showing a broken selection."""

from urllib.parse import parse_qs, urlparse

import pytest

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, browser_context,
)
from tests.integration.runtime.test_atlas_viewport_keyboard_browser import _open_viewer


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_empty_catalog_offers_project_next_step_without_a_broken_selection(browser_context, width: int) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, "empty")
    empty = atlas.locator("#atlasEmptyState")
    assert empty.is_visible()
    assert "No diagrams yet" in empty.inner_text()
    assert "Project" in empty.inner_text()
    assert atlas.locator("#viewerImage").is_hidden()
    assert atlas.locator("#viewerAssetError").is_hidden()
    assert atlas.locator(".diagram-facts").is_hidden()
    assert atlas.locator(".viewer-shell").is_hidden()
    assert atlas.locator(".details-grid").is_hidden()
    assert atlas.locator("button[data-diagram]").count() == 0
    assert atlas.locator("#statTotal").inner_text() == "0"
    for control in ("prevDiagram", "nextDiagram", "reset", "fit", "zoomIn", "zoomOut"):
        assert atlas.locator(f"#{control}").is_disabled()
    assert atlas.locator("#viewerStage").get_attribute("tabindex") == "-1"
    assert not atlas.locator("body").evaluate("node => node.scrollWidth > innerWidth + 1")
    screenshot = _failure_screenshot_path(f"atlas-empty-{width}")
    if screenshot:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
    project = empty.get_by_role("link", name="Open Project")
    project.click()
    page.wait_for_url("**tab=project*")
    assert parse_qs(urlparse(page.url).query)["tab"] == ["project"]
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_filtered_zero_explains_retained_selection_without_claiming_empty_catalog(browser_context, width: int) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, "normal")
    selected = atlas.locator("#diagramId").inner_text()
    search = atlas.locator("#search")
    search.fill("no-matching-diagram-in-catalog")
    status = atlas.locator("#diagramListStatus")
    assert status.is_visible()
    assert status.inner_text() == "No diagrams match these filters. The selected diagram is still shown."
    assert atlas.locator("#atlasEmptyState").is_hidden()
    assert atlas.locator("#diagramId").inner_text() == selected
    assert atlas.locator("#viewerImage").is_visible()
    assert atlas.locator("button[data-diagram]").count() == 1
    assert search.evaluate("node => document.activeElement === node")
    search.fill("")
    assert status.is_hidden()
    assert atlas.locator("button[data-diagram]").count() == 5
    assert atlas.locator("#diagramId").inner_text() == selected
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_filtered_empty_without_selection_recovers_existing_catalog(browser_context, width: int) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, "normal")
    page.goto(page.url.split("?")[0] + "?tab=atlas&workstream=B-999", wait_until="networkidle")
    empty = atlas.locator("#atlasEmptyState")
    assert empty.is_visible()
    assert empty.inner_text() == "No matching diagrams\n\nChange or clear the filters to browse diagrams."
    assert empty.get_by_role("link", name="Open Project").is_hidden()
    assert atlas.locator("#viewerImage").is_hidden()
    assert atlas.locator("#viewerAssetError").is_hidden()
    assert atlas.locator("#prevDiagram").is_disabled()
    atlas.locator("#workstreamFilter").select_option("all")
    page.wait_for_function("""() => {
        const image = document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
        return image.complete && image.naturalWidth > 0 && !image.hidden;
    }""")
    assert empty.is_hidden()
    assert atlas.locator("button[data-diagram]").count() == 5
    assert atlas.locator("#prevDiagram").is_enabled()
    assert atlas.locator("#reset").is_enabled()
    _assert_clean_page(page, *errors)
