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
    # Locate visible ink in the actual loaded SVG or fallback PNG, rather than
    # assuming the centre of a large diagram contains a label.
    reading = image.evaluate(
        """async image => {
            const box = image.getBoundingClientRect();
            const stage = document.querySelector('#viewerStage').getBoundingClientRect();
            const src = image.currentSrc || image.src;
            if (src.includes('.svg') || src.startsWith('data:image/svg+xml')) {
              const documentSvg = new DOMParser().parseFromString(await (await fetch(src)).text(), 'image/svg+xml');
              const svg = document.importNode(documentSvg.documentElement, true);
              svg.style.cssText = `position:fixed;left:-100000px;top:0;width:${box.width}px;height:${box.height}px;max-width:none;pointer-events:none`;
              document.body.append(svg);
              try {
                const bounds = svg.getBoundingClientRect();
                const nodes = svg.querySelectorAll('g.node foreignObject, g.node text');
                const label = [...(nodes.length ? nodes : svg.querySelectorAll('foreignObject, text'))].find(node => {
                  const rect = node.getBoundingClientRect();
                  return node.textContent.trim() && rect.width > 0 && rect.height > 0;
                });
                if (!label) throw new Error('Atlas native-size SVG has no readable label');
                const rect = label.getBoundingClientRect();
                const x = rect.left + rect.width / 2 - bounds.left;
                const y = rect.top + rect.height / 2 - bounds.top;
                return {x, y, dx: stage.left + stage.width / 2 - box.left - x,
                        dy: stage.top + stage.height / 2 - box.top - y};
              } finally { svg.remove(); }
            }
            const factor = Math.min(1, 1024 / Math.max(box.width, box.height));
            const canvas = document.createElement('canvas');
            canvas.width = Math.max(1, Math.ceil(box.width * factor));
            canvas.height = Math.max(1, Math.ceil(box.height * factor));
            const context = canvas.getContext('2d');
            context.drawImage(image, 0, 0, canvas.width, canvas.height);
            const pixels = context.getImageData(0, 0, canvas.width, canvas.height).data;
            const columns = Math.ceil(canvas.width / 32);
            const scores = new Map();
            for (let y = 0; y < canvas.height; y++) {
              for (let x = 0; x < canvas.width; x++) {
                const i = (y * canvas.width + x) * 4;
                if (pixels[i + 3] < 128 || pixels[i] + pixels[i + 1] + pixels[i + 2] > 480) continue;
                const key = Math.floor(y / 32) * columns + Math.floor(x / 32);
                scores.set(key, (scores.get(key) || 0) + 1);
              }
            }
            const best = [...scores].sort((a, b) => b[1] - a[1])[0];
            if (!best) throw new Error('Atlas native-size image has no visible ink');
            const x = Math.min(canvas.width - 1, (best[0] % columns) * 32 + 16) / factor;
            const y = Math.min(canvas.height - 1, Math.floor(best[0] / columns) * 32 + 16) / factor;
            return {x, y, dx: stage.left + stage.width / 2 - box.left - x,
                    dy: stage.top + stage.height / 2 - box.top - y};
        }"""
    )
    # The following 80px pan proves the input and leaves the chosen label centred.
    for delta, positive, negative in (
        (reading["dx"] + 80, "ArrowLeft", "ArrowRight"),
        (reading["dy"], "ArrowUp", "ArrowDown"),
    ):
        for _ in range(round(abs(delta) / 80)):
            stage.press(positive if delta > 0 else negative)
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
    point_visible = image.evaluate(
        """(image, point) => {
            const box = image.getBoundingClientRect();
            const stage = document.querySelector('#viewerStage').getBoundingClientRect();
            const x = box.left + point.x, y = box.top + point.y;
            return x > stage.left && x < stage.right && y > stage.top && y < stage.bottom;
        }""", reading,
    )
    if not point_visible:
        issues += ("browser surface atlas native-size reading position is blank",)
    if screenshot_output_dir is not None:
        capture_state_screenshot(
            page=page,
            output_dir=screenshot_output_dir,
            state_name="-".join((*coverage_cell, expected_diagram.casefold(), "read-100")),
            expand_pane=False,
        )
        if (image.evaluate("element => element.style.transform") != after_transform
                or frame.locator("#zoomReadout").inner_text() != state.get("zoomText")):
            issues += ("browser surface atlas capture changed the checked native-size state",)
    return issues


__all__ = ["prove_atlas_native_reading"]
