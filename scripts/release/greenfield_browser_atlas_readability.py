"""Browser interaction proof for one Atlas diagram's native-size reading state."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from greenfield_browser_authored_contract import atlas_readability_assertion_issues
from greenfield_browser_capture import capture_state_screenshot


def prove_atlas_native_reading(
    *,
    page: Any,
    frame: Any,
    expected_diagram: str,
    timeout_ms: int,
    screenshot_output_dir: Path | None,
    coverage_cell: tuple[str, str, str],
) -> tuple[str, ...]:
    """Switch to 100%, prove desktop keyboard or mobile touch pan, and retain it."""

    frame.locator("#reset").click()
    frame.locator("#zoomReadout", has_text="Zoom 100%").wait_for(timeout=timeout_ms)
    stage = frame.locator("#viewerStage").first
    image = frame.locator("#viewerImage").first
    before_transform = str(image.evaluate("element => element.style.transform"))
    pan_input = "touch-pointer" if coverage_cell[0] == "mobile" else "keyboard"
    if pan_input == "touch-pointer":
        box = stage.bounding_box()
        if box:
            start_x = float(box["x"]) + min(120.0, float(box["width"]) / 2)
            start_y = float(box["y"]) + min(120.0, float(box["height"]) / 2)
            cdp = page.context.new_cdp_session(page)
            cdp.send("Input.dispatchTouchEvent", {
                "type": "touchStart", "touchPoints": [{"x": start_x, "y": start_y}],
            })
            cdp.send("Input.dispatchTouchEvent", {
                "type": "touchMove",
                "touchPoints": [{"x": start_x - 80, "y": start_y - 24}],
            })
            cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
            cdp.detach()
    else:
        stage.press("ArrowRight")
    after_transform = str(image.evaluate("element => element.style.transform"))
    state = stage.evaluate(
        """(element) => ({
            focused: document.activeElement === element,
            tabIndex: element.tabIndex,
            zoomText: String(document.querySelector("#zoomReadout")?.textContent || ""),
            displayed: String(document.querySelector("#diagramId")?.textContent || "")
        })"""
    )
    issues = atlas_readability_assertion_issues(
        zoom_text=str(state.get("zoomText", "")),
        stage_tab_index=int(state.get("tabIndex", -1)),
        stage_focused=bool(state.get("focused", False)),
        displayed_diagram=str(state.get("displayed", "")),
        expected_diagram=expected_diagram,
        pan_input=pan_input,
        pan_changed_transform=before_transform != after_transform,
    )
    if pan_input == "keyboard":
        stage.press("ArrowLeft")
    if screenshot_output_dir is not None:
        capture_state_screenshot(
            page=page,
            output_dir=screenshot_output_dir,
            state_name="-".join((*coverage_cell, expected_diagram.casefold(), "read-100")),
        )
    return issues


__all__ = ["prove_atlas_native_reading"]
