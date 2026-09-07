"""Detailed Atlas diagrams remain readable through keyboard-owned navigation."""

from __future__ import annotations

import base64

import pytest

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)
from tests.integration.runtime.test_atlas_viewer_activation_browser import _viewer_html


_SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 1400">
<rect x="1" y="1" width="2398" height="1398" fill="white" stroke="teal"/>
<g font-size="22" fill="#24465b">
<text x="40" y="60">Operator submits the record.</text>
<text x="1900" y="60">Service validates the submission.</text>
<text x="40" y="1340">Rejected records retain their evidence.</text>
<text x="1900" y="1340">Operator reviews the visible result.</text>
</g></svg>'''


def _open_viewer(browser_context, width: int, state: str):  # noqa: ANN001
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
    )

    def asset(route):  # noqa: ANN001
        is_png = route.request.url.endswith(".png")
        body = png if is_png else _SVG
        if state == "error" or (state == "fallback" and not is_png):
            body = b"invalid image"
        route.fulfill(status=200, content_type="image/png" if is_png else "image/svg+xml", body=body)

    page.route("**/selection-*.svg", asset)
    page.route("**/selection-*.png", asset)
    page.route("**/odylith/atlas/atlas.html*", lambda route: route.fulfill(
        status=200, content_type="text/html",
        body=_viewer_html(width=2400, height=1400, count=0 if state == "empty" else 5),
    ))
    page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="networkidle")
    atlas = page.frame_locator("#frame-atlas")
    if state == "error":
        atlas.locator("#viewerAssetError").wait_for(state="visible")
    elif state != "empty":
        page.wait_for_function("""() => {
            const image = document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
            return image && image.complete && image.naturalWidth > 0;
        }""")
    return page, atlas, errors


def _geometry(atlas):  # noqa: ANN001
    return atlas.locator("#viewerStage").evaluate("""stage => {
        const image = stage.querySelector('img');
        const matrix = new DOMMatrixReadOnly(getComputedStyle(image).transform);
        const box = node => {
            const r = node.getBoundingClientRect();
            return {left:r.left, top:r.top, right:r.right, bottom:r.bottom};
        };
        return {scale:matrix.a, x:matrix.e, y:matrix.f, stage:box(stage), image:box(image)};
    }""")


def _assert_overview(atlas):  # noqa: ANN001
    geometry = _geometry(atlas)
    assert 0 < geometry["scale"] < 1
    for low, high in [("left", "right"), ("top", "bottom")]:
        assert geometry["image"][low] >= geometry["stage"][low] - 1
        assert geometry["image"][high] <= geometry["stage"][high] + 1


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback"])
def test_keyboard_reading_reaches_all_corners_and_restores_overview(
    browser_context, width: int, state: str,
) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, state)
    _assert_overview(atlas)
    selected = atlas.locator("#diagramId").inner_text()
    read = atlas.locator("#reset")
    assert read.inner_text() == "Read at 100%"
    read.scroll_into_view_if_needed()
    header = page.locator("header.toolbar").bounding_box()
    tabs = page.locator("nav.tabs").bounding_box()
    read.click()
    stage = atlas.locator("#viewerStage")
    assert stage.evaluate("node => document.activeElement === node")
    assert stage.get_attribute("tabindex") == "0"
    assert stage.get_attribute("aria-labelledby") == "diagramTitle"
    assert stage.get_attribute("aria-describedby")
    assert _geometry(atlas)["scale"] == 1
    assert stage.evaluate("""node => {
        const box = node.getBoundingClientRect();
        return box.top >= -1 && box.bottom <= window.innerHeight + 1;
    }"""), "Full-size reading must reveal the stage inside the actual iframe viewport"
    assert stage.evaluate("node => parseFloat(getComputedStyle(node).outlineWidth)") >= 2
    initial = _geometry(atlas)
    stage.press("ArrowRight")
    right = _geometry(atlas)
    assert right["x"] < initial["x"] and right["y"] == initial["y"]
    stage.press("ArrowDown")
    down = _geometry(atlas)
    assert down["y"] < right["y"] and down["x"] == right["x"]
    stage.press("ArrowLeft")
    stage.press("ArrowUp")
    assert _geometry(atlas) == initial

    # Reach every corner at native text scale, without switching diagrams.
    for horizontal, vertical in [("left", "top"), ("right", "top"), ("left", "bottom"), ("right", "bottom")]:
        for side, key in [(horizontal, "ArrowLeft" if horizontal == "left" else "ArrowRight"),
                          (vertical, "ArrowUp" if vertical == "top" else "ArrowDown")]:
            for _ in range(50):
                geometry = _geometry(atlas)
                delta = geometry["image"][side] - geometry["stage"][side]
                if (side in {"left", "top"} and delta >= 0) or (side in {"right", "bottom"} and delta <= 0):
                    break
                stage.press(key)
            else:
                pytest.fail(f"Keyboard navigation cannot reach the {side} of the diagram")
        assert atlas.locator("#diagramId").inner_text() == selected
        assert _geometry(atlas)["scale"] == 1
    screenshot = _failure_screenshot_path(f"atlas-read-{width}-{state}")
    if screenshot:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
    stage.press("f")
    _assert_overview(atlas)
    assert atlas.locator("#diagramId").inner_text() == selected
    assert page.locator("header.toolbar").bounding_box() == header
    assert page.locator("nav.tabs").bounding_box() == tabs
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_typing_and_selecting_filters_never_operates_the_viewer(browser_context, width: int) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, "normal")
    atlas.locator("#reset").click()
    initial = _geometry(atlas)
    selected = atlas.locator("#diagramId").inner_text()
    search = atlas.locator("#search")
    search.focus()
    search.press("f")
    search.press("0")
    search.press("-")
    search.press("+")
    search.press("ArrowDown")
    assert search.input_value() == "f0-+"
    assert {key: _geometry(atlas)[key] for key in ("scale", "x", "y")} == {
        key: initial[key] for key in ("scale", "x", "y")
    }
    assert atlas.locator("#diagramId").inner_text() == selected
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["error", "empty"])
def test_unavailable_diagram_does_not_offer_unusable_reading_controls(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, width, state)
    for control in ["reset", "fit", "zoomIn", "zoomOut"]:
        assert atlas.locator(f"#{control}").is_disabled()
        assert atlas.locator(f"#{control}").evaluate("node => Number(getComputedStyle(node).opacity)") < 1
    assert atlas.locator("#viewerStage").get_attribute("tabindex") == "-1"
    assert atlas.locator("#prevDiagram").is_disabled() == (state == "empty")
    assert atlas.locator("#nextDiagram").is_disabled() == (state == "empty")
    _assert_clean_page(page, *errors)
