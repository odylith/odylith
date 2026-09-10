from __future__ import annotations

from functools import cmp_to_key
import re

import pytest

from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    browser_context,
)


def _visible_atlas_rows(atlas) -> list[dict[str, str]]:  # noqa: ANN001
    return atlas.locator("button[data-diagram]").evaluate_all(
        """nodes => nodes.map((node) => ({
          diagram_id: String(node.getAttribute("data-diagram") || "").trim(),
          reviewed: String(node.getAttribute("data-diagram-reviewed") || "").trim(),
          freshness: String(node.getAttribute("data-diagram-freshness") || "").trim(),
          review_age: String(node.getAttribute("data-diagram-review-age") || "").trim(),
          title: String((node.querySelector(".diagram-name") || {}).textContent || "").trim(),
        }))"""
    )


def _diagram_number(row: dict[str, str]) -> int:
    match = re.fullmatch(r"D-(\d+)", str(row.get("diagram_id") or "").strip())
    return int(match.group(1)) if match else 0


def _compare_text(left: str, right: str) -> int:
    left_token = str(left or "").casefold()
    right_token = str(right or "").casefold()
    return (left_token > right_token) - (left_token < right_token)


def _review_age(row: dict[str, str]) -> int:
    try:
        return int(str(row.get("review_age") or "0").strip())
    except ValueError:
        return 0


def _first_non_zero(*values: int) -> int:
    return next((value for value in values if value != 0), 0)


def _compare_rows(sort_token: str):  # noqa: ANN202
    def _compare(left: dict[str, str], right: dict[str, str]) -> int:
        newest = _diagram_number(right) - _diagram_number(left)
        oldest = _diagram_number(left) - _diagram_number(right)
        reviewed_desc = _compare_text(str(right.get("reviewed") or ""), str(left.get("reviewed") or ""))
        reviewed_asc = _compare_text(str(left.get("reviewed") or ""), str(right.get("reviewed") or ""))
        title_asc = _compare_text(str(left.get("title") or ""), str(right.get("title") or ""))
        if sort_token == "oldest":
            return _first_non_zero(oldest, reviewed_asc, title_asc)
        if sort_token == "reviewed":
            return _first_non_zero(reviewed_desc, newest, title_asc)
        if sort_token == "title":
            return _first_non_zero(title_asc, newest)
        if sort_token == "freshness":
            stale_rank = (0 if left.get("freshness") == "stale" else 1) - (
                0 if right.get("freshness") == "stale" else 1
            )
            return _first_non_zero(stale_rank, _review_age(right) - _review_age(left), newest, title_asc)
        return _first_non_zero(newest, reviewed_desc, title_asc)

    return _compare


def _assert_sorted(rows: list[dict[str, str]], sort_token: str) -> None:
    assert rows, "expected visible Atlas rows"
    expected = sorted(rows, key=cmp_to_key(_compare_rows(sort_token)))
    assert rows == expected


def test_atlas_sort_filter_orders_rows_and_preserves_selection(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
        assert response is not None and response.ok

        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        atlas.locator("#sortFilter").wait_for(timeout=15000)

        assert atlas.locator("#sortFilter").input_value() == "newest"
        rows = _visible_atlas_rows(atlas)
        assert len(rows) > 1
        _assert_sorted(rows, "newest")
        assert rows[0]["diagram_id"] == max(rows, key=_diagram_number)["diagram_id"]
        selected_diagram = atlas.locator("#diagramId").inner_text().strip()

        for sort_token in ("oldest", "reviewed", "title", "freshness", "newest"):
            atlas.locator("#sortFilter").select_option(sort_token)
            assert atlas.locator("#sortFilter").input_value() == sort_token
            _assert_sorted(_visible_atlas_rows(atlas), sort_token)
            atlas.locator("#diagramId", has_text=selected_diagram).wait_for(timeout=15000)

        _assert_clean_page(page, observation)


@pytest.mark.parametrize("viewport", [(1440, 1100), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("preview_available", [True, False], ids=["normal", "preview-error"])
def test_atlas_component_descriptions_retain_complete_text(
    browser_context, viewport: tuple[int, int], preview_available: bool,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        descriptions = [
            "Payment Engine records the payment receipt. The first path depends on preserving the replay token.",
            "Proposed responsibility: Retry checkout. Reviewers trust it only when duplicate charges are prevented.",
            "Owns records café  IDs.\nProof must stay inside the current checkout; preserve <token> & **receipt**",
            "",
            "  \n  ",
        ]
        html = renderer._render_html(  # noqa: SLF001
            diagrams=[{
                "diagram_id": "D-001", "slug": "responsibility-custody", "title": "Responsibility custody",
                "kind": "architecture", "status": "draft", "owner": "payment-engine",
                "summary": "Description rendering fixture.", "read_guide": "Read the complete descriptions.",
                "last_reviewed_utc": "2026-09-06", "review_age_days": 0, "freshness": "fresh",
                "source_svg_href": "/responsibility-preview.svg", "svg_viewbox_width": 120,
                "svg_viewbox_height": 80, "initial_view_fit_factor": 1,
                "components": [{"name": "Payment Engine", "description": text} for text in descriptions],
            }],
            stats={"total": 1, "fresh": 1, "stale": 0},
            max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-06T00:00:00Z",
            brand_head_html="", tooling_base_href="/odylith/index.html",
        )
        page.route("**/responsibility-custody.html", lambda route: route.fulfill(
            status=200, content_type="text/html", body=html,
        ))
        page.route("**/responsibility-preview.svg", lambda route: route.fulfill(
            status=200, content_type="image/svg+xml",
            body='<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 80"><rect width="120" height="80"/></svg>'
            if preview_available else "invalid image data",
        ))
        response = page.goto(base_url + "/responsibility-custody.html", wait_until="networkidle")
        assert response is not None and response.ok
        if preview_available:
            assert page.locator("#viewerImage").evaluate("image => image.complete && image.naturalWidth > 0")
            assert page.locator("#viewerAssetError").is_hidden()
        else:
            page.locator("#viewerAssetError").wait_for(state="visible")
            assert "Diagram preview unavailable." in page.locator("#viewerAssetError").inner_text()
        rendered = page.locator("#componentList .component-description")
        assert rendered.all_text_contents() == [
            text if text.strip() else "Named responsibility in this diagram." for text in descriptions
        ]
        assert rendered.locator("*").count() == 0
        for description in rendered.all():
            description.scroll_into_view_if_needed()
            assert description.is_visible()
        _assert_clean_page(page, observation)


def test_atlas_search_matches_partial_diagram_number(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
        assert response is not None and response.ok

        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        atlas.locator("#search").fill("003")
        atlas.locator('button[data-diagram="D-003"]').wait_for(timeout=15000)

        rows = _visible_atlas_rows(atlas)
        assert rows
        assert any(row["diagram_id"] == "D-003" for row in rows)
        atlas.locator("#diagramId", has_text="D-003").wait_for(timeout=15000)

        _assert_clean_page(page, observation)


def test_atlas_sort_and_workstream_filters_share_sidebar_row(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
        assert response is not None and response.ok

        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        atlas.locator("#sortWorkstreamFilters").wait_for(timeout=15000)

        layout = atlas.locator("#sortWorkstreamFilters").evaluate(
            """(node) => {
          const sidebar = document.getElementById("sidebarPanel");
          const sort = document.getElementById("sortFilter").getBoundingClientRect();
          const workstream = document.getElementById("workstreamFilter").getBoundingClientRect();
          return {
            sidebarWidth: Math.round(sidebar.getBoundingClientRect().width),
            pairClientWidth: node.clientWidth,
            pairScrollWidth: node.scrollWidth,
            sortTop: Math.round(sort.top),
            workstreamTop: Math.round(workstream.top),
            sortRight: Math.round(sort.right),
            workstreamLeft: Math.round(workstream.left),
          };
        }"""
        )

        assert layout["sidebarWidth"] >= 398
        assert layout["pairScrollWidth"] - layout["pairClientWidth"] <= 4
        assert abs(layout["sortTop"] - layout["workstreamTop"]) <= 2
        assert layout["sortRight"] < layout["workstreamLeft"]

        _assert_clean_page(page, observation)


def test_atlas_header_action_buttons_are_right_aligned(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
        assert response is not None and response.ok

        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        atlas.locator("#sourceLinks .source-link").first.wait_for(timeout=15000)

        layout = atlas.locator(".source-links-wrap").evaluate(
            """(node) => {
          const controls = Array.from(node.children).filter((child) => {
            const box = child.getBoundingClientRect();
            return box.width > 0 && box.height > 0;
          });
          const wrapper = node.getBoundingClientRect();
          const first = controls[0].getBoundingClientRect();
          const last = controls[controls.length - 1].getBoundingClientRect();
          return {
            controlCount: controls.length,
            wrapperLeft: Math.round(wrapper.left),
            wrapperRight: Math.round(wrapper.right),
            firstLeft: Math.round(first.left),
            lastRight: Math.round(last.right),
            scrollDelta: node.scrollWidth - node.clientWidth,
          };
        }"""
        )

        assert layout["controlCount"] >= 2
        assert layout["scrollDelta"] <= 4
        assert layout["firstLeft"] - layout["wrapperLeft"] >= 16
        assert abs(layout["wrapperRight"] - layout["lastRight"]) <= 2

        _assert_clean_page(page, observation)
