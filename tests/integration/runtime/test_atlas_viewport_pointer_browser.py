"""Reading-mode extraction preserves native drag, wheel and touch interactions."""

from __future__ import annotations

import pytest

from tests.integration.runtime.surface_browser_test_support import _assert_clean_page, browser_context
from tests.integration.runtime.test_atlas_viewport_keyboard_browser import _geometry, _open_viewer


def _stage_center(page, atlas):  # noqa: ANN001
    stage = atlas.locator("#viewerStage")
    stage.scroll_into_view_if_needed()
    box = stage.bounding_box()
    assert box
    left, top = max(0, box["x"]), max(190, box["y"])
    right = min(page.viewport_size["width"], box["x"] + box["width"])
    bottom = min(page.viewport_size["height"], box["y"] + box["height"])
    assert right - left > 150 and bottom - top > 150
    return (left + right) / 2, (top + bottom) / 2


def test_drag_and_trackpad_pinch_preserve_the_reading_view(browser_context) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, 1440, "normal")
    atlas.locator("#reset").click()
    x, y = _stage_center(page, atlas)
    initial = _geometry(atlas)
    page.mouse.move(x, y)
    page.mouse.down()
    page.mouse.move(x + 40, y + 20, steps=4)
    page.mouse.up()
    moved = _geometry(atlas)
    assert moved["scale"] == initial["scale"] == 1
    assert moved["x"] - initial["x"] == pytest.approx(40)
    assert moved["y"] - initial["y"] == pytest.approx(20)
    assert not atlas.locator("#viewerStage").evaluate("node => node.classList.contains('dragging')")
    page.mouse.wheel(0, 120)
    page.wait_for_timeout(50)
    assert _geometry(atlas)["scale"] == 1
    x, y = _stage_center(page, atlas)
    page.mouse.move(x, y)
    page.keyboard.down("Control")
    page.mouse.wheel(0, -120)
    page.keyboard.up("Control")
    page.wait_for_timeout(50)
    assert _geometry(atlas)["scale"] > 1
    atlas.locator("#fit").click()
    assert _geometry(atlas)["scale"] < 1
    _assert_clean_page(page, *errors)


def test_two_finger_pinch_then_keyboard_pan_keeps_the_same_diagram(browser_context) -> None:  # noqa: ANN001
    page, atlas, errors = _open_viewer(browser_context, 430, "normal")
    atlas.locator("#reset").click()
    selected = atlas.locator("#diagramId").inner_text()
    x, y = _stage_center(page, atlas)
    session = page.context.new_cdp_session(page)
    session.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [
        {"x": x - 30, "y": y, "id": 1}, {"x": x + 30, "y": y, "id": 2},
    ]})
    session.send("Input.dispatchTouchEvent", {"type": "touchMove", "touchPoints": [
        {"x": x - 60, "y": y, "id": 1}, {"x": x + 60, "y": y, "id": 2},
    ]})
    session.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    session.detach()
    assert _geometry(atlas)["scale"] == pytest.approx(2)
    atlas.locator("#reset").click()
    initial = _geometry(atlas)
    atlas.locator("#viewerStage").press("ArrowRight")
    assert _geometry(atlas)["x"] < initial["x"]
    assert _geometry(atlas)["scale"] == 1
    assert atlas.locator("#diagramId").inner_text() == selected
    _assert_clean_page(page, *errors)
