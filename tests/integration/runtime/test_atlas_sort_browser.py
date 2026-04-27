from __future__ import annotations

from functools import cmp_to_key
import re

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
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
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

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_sort_and_workstream_filters_share_sidebar_row(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
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

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_header_action_buttons_are_right_aligned(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
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

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
