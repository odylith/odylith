"""Atlas metadata preserves supplied text and explicit source-action lines."""

from __future__ import annotations

import base64
import json

import pytest

from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)
from tests.integration.runtime.test_atlas_viewport_keyboard_browser import _SVG


_METADATA = {
    "node_id": "source_metadata",
    "label": "Record café  intake — **verbatim**.\nInspect <tag> & keep `ID` + __state__.\nRecord café  intake — **verbatim**.",
    "role": "Source **operator** / `role` — <owner> & __literal__",
    "description": (
        "Preserve café  IDs and **evidence**.\n"
        "Show <img src=x onerror=window.__atlas_box_injected__=1> as literal text & keep `proof`.\n"
        "Do not remove __late restriction__: review must precede publication."
    ),
}
_ACTION_LINES = ["Record café intake.", "Inspect tag.", "Record café intake."]
_ACTIONS = {
    "node_id": "source_actions", "label": "\n".join(_ACTION_LINES),
    "role": "Grouped source actions", "description": "Listing order does not establish execution order.",
}


def _metadata_html(*, empty: bool) -> str:
    return renderer._render_html(
        diagrams=[] if empty else [{
            "diagram_id": "D-001", "slug": "metadata-custody", "title": "Source metadata custody",
            "kind": "architecture", "status": "draft", "owner": "record-service",
            "summary": "Read the supplied metadata without rewriting it.",
            "read_guide": "Separate source action lines remain separate.",
            "last_reviewed_utc": "2026-09-08", "review_age_days": 0, "freshness": "fresh",
            "source_svg_href": "/metadata-preview.svg", "source_png_href": "/metadata-preview.png",
            "svg_viewbox_width": 2400, "svg_viewbox_height": 1400, "initial_view_fit_factor": 1,
            "diagram_boxes": [_METADATA, _ACTIONS], "components": [],
        }],
        stats={"total": 0 if empty else 1, "fresh": 0 if empty else 1, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-08T00:00:00Z",
        brand_head_html="", tooling_base_href="/odylith/index.html",
    )


def _open_metadata(browser_context, width: int, state: str):  # noqa: ANN001
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

    page.route("**/metadata-preview.svg", asset)
    page.route("**/metadata-preview.png", asset)
    page.route("**/odylith/atlas/atlas.html*", lambda route: route.fulfill(
        status=200, content_type="text/html", body=_metadata_html(empty=state == "empty"),
    ))
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="networkidle")
    assert response is not None and response.ok
    assert page.locator("#tab-atlas").get_attribute("aria-selected") == "true"
    atlas = page.frame_locator("#frame-atlas")
    if state == "error":
        atlas.locator("#viewerAssetError").wait_for(state="visible")
        assert atlas.locator("#viewerImage").is_hidden()
        assert atlas.locator("#reset").is_disabled()
    elif state != "empty":
        page.wait_for_function("""() => {
            const image=document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
            return image && image.complete && image.naturalWidth > 0;
        }""")
        assert atlas.locator("#viewerImage").get_attribute("src").endswith(".png" if state == "fallback" else ".svg")
        assert atlas.locator("#viewerAssetError").is_hidden()
    return page, atlas, errors


def _capture(page, name: str, measurement: dict) -> None:  # noqa: ANN001
    screenshot = _failure_screenshot_path(name)
    if screenshot:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
        screenshot.with_suffix(".json").write_text(json.dumps(measurement, indent=2, ensure_ascii=False) + "\n")


def _text_bounds(target):  # noqa: ANN001
    return target.evaluate("""target => {
        const doc=target.ownerDocument, range=doc.createRange();range.selectNodeContents(target);
        const rects=Array.from(range.getClientRects()),clipped=[],hidden=[];
        for(let owner=target;owner;owner=owner.parentElement){
            const box=owner.getBoundingClientRect(),style=getComputedStyle(owner);
            if(style.display==='none'||style.visibility==='hidden'||parseInt(style.webkitLineClamp||'0',10)>0)
                hidden.push(owner.className);
            if(owner.scrollLeft)clipped.push({owner:owner.className,scrollLeft:owner.scrollLeft});
            for(const rect of rects){
                if(rect.left < -1 || rect.right > doc.documentElement.clientWidth+1)
                    clipped.push({left:rect.left,right:rect.right});
                if(['hidden','clip','auto','scroll'].includes(style.overflowX) &&
                    (rect.left<box.left-1||rect.right>box.right+1))clipped.push({owner:owner.className,axis:'x'});
                if(['hidden','clip'].includes(style.overflowY) &&
                    (rect.top<box.top-1||rect.bottom>box.bottom+1))clipped.push({owner:owner.className,axis:'y'});
            }
        }
        return {text:target.textContent,clipped,hidden};
    }""")


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback", "error"])
def test_box_metadata_keeps_exact_supplied_text_inert(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    page, atlas, errors = _open_metadata(browser_context, width, state)
    try:
        rows = atlas.locator(".diagram-box-row")
        assert rows.count() == 2
        row = rows.first
        row.scroll_into_view_if_needed()
        actual, geometry = {}, {}
        for field, selector in [("label", ".diagram-box-name strong"), ("role", ".diagram-box-role"),
                                ("description", ".diagram-box-description")]:
            target = row.locator(selector)
            target.scroll_into_view_if_needed()
            assert target.is_visible()
            actual[field] = target.text_content()
            geometry[field] = _text_bounds(target)
            assert target.locator("*").count() == 0, "Metadata must remain inert text, not injected markup"
        _capture(page, f"atlas-box-exact-{width}-{state}", {"actual": actual, "geometry": geometry})
        assert actual == {field: _METADATA[field] for field in actual}
        assert not atlas.locator("body").evaluate("() => Boolean(window.__atlas_box_injected__)")
        assert all(not row["clipped"] and not row["hidden"] for row in geometry.values()), geometry
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _assert_clean_page(page, *errors)
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback", "error"])
def test_source_action_lines_are_visually_separate_in_order(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    page, atlas, errors = _open_metadata(browser_context, width, state)
    try:
        heading = atlas.locator(".diagram-box-row").nth(1).locator(".diagram-box-name strong")
        heading.scroll_into_view_if_needed()
        measurement = heading.evaluate("""(target,lines) => {
            const text=target.textContent,node=target.firstChild,positions=[];
            let cursor=0;
            for(const line of lines){
                const start=text.indexOf(line,cursor);
                if(start<0||!node||node.nodeType!==Node.TEXT_NODE)return {text,missing:line};
                const range=target.ownerDocument.createRange();range.setStart(node,start);range.setEnd(node,start+line.length);
                positions.push({line,start,rects:Array.from(range.getClientRects()).filter(r=>r.width>0)
                    .map(r=>({top:r.top,bottom:r.bottom,left:r.left,right:r.right}))});
                cursor=start+line.length;
            }
            return {text,positions};
        }""", _ACTION_LINES)
        measurement["bounds"] = _text_bounds(heading)
        _capture(page, f"atlas-box-lines-{width}-{state}", measurement)
        assert "missing" not in measurement, measurement
        positions = measurement["positions"]
        assert len(positions) == len(_ACTION_LINES) and all(row["rects"] for row in positions)
        for previous, current in zip(positions, positions[1:]):
            assert min(rect["top"] for rect in current["rects"]) >= max(rect["bottom"] for rect in previous["rects"]) - 1, measurement
        assert measurement["text"] == _ACTIONS["label"]
        assert not measurement["bounds"]["clipped"] and not measurement["bounds"]["hidden"], measurement
        _assert_clean_page(page, *errors)
    finally:
        page.close()


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_empty_atlas_has_no_box_metadata_or_injected_action_rows(browser_context, width: int) -> None:  # noqa: ANN001
    page, atlas, errors = _open_metadata(browser_context, width, "empty")
    try:
        empty = atlas.locator("#atlasEmptyState")
        assert empty.is_visible() and "No diagrams yet" in empty.inner_text()
        assert atlas.locator(".diagram-box-row").count() == 0
        assert atlas.locator("#diagramBoxesSection").is_hidden()
        assert atlas.locator("#viewerImage").is_hidden()
        assert atlas.locator("#viewerAssetError").is_hidden()
        assert atlas.locator("#reset").is_disabled()
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _capture(page, f"atlas-box-empty-{width}", {"text": empty.inner_text(), "rows": 0})
        _assert_clean_page(page, *errors)
    finally:
        page.close()
