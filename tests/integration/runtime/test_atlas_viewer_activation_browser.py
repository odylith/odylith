"""Explicit Atlas selection must reveal its preview or recovery controls."""

from __future__ import annotations

import base64

import pytest

from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)


def _viewer_html() -> str:
    return renderer._render_html(
        diagrams=[{
            "diagram_id": f"D-{index:03}", "slug": f"selection-{index}",
            "title": f"Record lifecycle {index}", "kind": "architecture",
            "status": "draft", "owner": "record-service",
            "summary": "An operator submits a record and reviews its validation result.",
            "read_guide": "Follow the record from submission to its visible result.",
            "last_reviewed_utc": "2026-09-07", "review_age_days": 0, "freshness": "fresh",
            "source_svg_href": f"/selection-{index}.svg",
            "source_png_href": f"/selection-{index}.png",
            "svg_viewbox_width": 300, "svg_viewbox_height": 100,
            "initial_view_fit_factor": 1,
            "components": [{"name": "Record service", "description": "Validates submitted records."}],
        } for index in range(1, 6)],
        stats={"total": 5, "fresh": 5, "stale": 0}, max_review_age_days=21,
        tooltip_lookup={}, generated_utc="2026-09-07T00:00:00Z",
        brand_head_html="", tooling_base_href="/odylith/index.html",
    )


def _assert_in_frame(page, locator) -> None:  # noqa: ANN001
    box = locator.bounding_box()
    frame = page.locator("#frame-atlas").bounding_box()
    assert box and frame
    assert box["y"] >= max(0, frame["y"]) - 1, (box, frame)
    assert box["y"] + box["height"] <= min(
        page.viewport_size["height"], frame["y"] + frame["height"],
    ) + 1, (box, frame)
    assert box["x"] >= frame["x"] - 1
    assert box["x"] + box["width"] <= frame["x"] + frame["width"] + 1


@pytest.mark.parametrize("width,height", [(1440, 1100), (430, 932)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback", "error"])
def test_explicit_selection_reveals_viewer_without_load_or_filter_focus_theft(
    browser_context, width: int, height: int, state: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    page.set_viewport_size({"width": width, "height": height})
    asset_requests = []
    asset_state = state
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 100"><text x="10" y="50">Record validated</text></svg>'
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )

    def asset(route):  # noqa: ANN001
        asset_requests.append(route.request.url)
        is_png = route.request.url.endswith(".png")
        body = png if is_png else svg
        if asset_state == "error" or (asset_state == "fallback" and not is_png):
            body = b"invalid image"
        route.fulfill(status=200, content_type="image/png" if is_png else "image/svg+xml", body=body)

    page.route("**/selection-*.svg", asset)
    page.route("**/selection-*.png", asset)
    page.route("**/odylith/atlas/atlas.html*", lambda route: route.fulfill(
        status=200, content_type="text/html", body=_viewer_html(),
    ))
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="networkidle")
    assert response is not None and response.ok
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator('button[data-diagram="D-002"]').wait_for()
    assert atlas.locator("body").evaluate("() => window.scrollY") == 0
    assert not atlas.locator(".viewer-shell").evaluate("node => document.activeElement === node")
    header = page.locator("header.toolbar").bounding_box()
    tabs = page.locator("nav.tabs").bounding_box()
    outer_scroll = page.evaluate("window.scrollY")

    for activation, diagram_id in [("click", "D-002"), ("keyboard", "D-001")]:
        button = atlas.locator(f'button[data-diagram="{diagram_id}"]')
        button.scroll_into_view_if_needed()
        before_scroll = atlas.locator("body").evaluate("() => window.scrollY")
        if activation == "click":
            button.click()
        else:
            button.focus()
            button.press("Enter")
        atlas.locator("#diagramId", has_text=diagram_id).wait_for()
        image = atlas.locator("#viewerImage")
        error = atlas.locator("#viewerAssetError")
        if state == "error":
            error.wait_for(state="visible")
        else:
            page.wait_for_function("""() => {
                const image = document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
                return image.complete && image.naturalWidth > 0;
            }""")
            assert error.is_hidden()
            assert image.get_attribute("src").endswith(".png" if state == "fallback" else ".svg")

        screenshot = _failure_screenshot_path(f"atlas-{width}-{state}-{activation}")
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot))
        _assert_in_frame(page, atlas.locator(".viewer-toolbar"))
        assert page.locator("header.toolbar").bounding_box() == header
        assert page.locator("nav.tabs").bounding_box() == tabs
        assert page.evaluate("window.scrollY") == outer_scroll
        if state == "error":
            _assert_in_frame(page, error)
            assert "source links below" not in error.inner_text()
        else:
            _assert_in_frame(page, image)
        if width == 430:
            assert atlas.locator(".viewer-shell").evaluate("node => document.activeElement === node")
            assert atlas.locator(".viewer-shell").get_attribute("aria-labelledby") == "diagramTitle"
            page.keyboard.press("Tab")
            assert atlas.locator("#prevDiagram").evaluate("node => document.activeElement === node")
        else:
            assert button.evaluate("node => document.activeElement === node")
            assert atlas.locator("body").evaluate("() => window.scrollY") == before_scroll

    assert any(url.endswith(".png") for url in asset_requests) == (state != "normal")
    if state == "error":
        asset_state = "normal"
        previous = atlas.locator("#prevDiagram")
        previous.click()
        scroll = atlas.locator("body").evaluate("() => window.scrollY")
        page.wait_for_function("""() => {
            const image = document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
            return image.complete && image.naturalWidth > 0;
        }""")
        assert atlas.locator("#viewerAssetError").is_hidden()
        assert previous.evaluate("node => document.activeElement === node")
        assert atlas.locator("body").evaluate("() => window.scrollY") == scroll
    # The existing no-match contract preserves selection, but not viewer focus.
    atlas.locator("#search").fill("no-match-selection-control")
    assert atlas.locator("button[data-diagram]").count() == 1
    assert atlas.locator("#search").evaluate("node => document.activeElement === node")
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
