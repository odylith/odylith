"""Casebook distinguishes an empty repository from a filtered populated list."""

from __future__ import annotations

import json
from contextlib import contextmanager

import pytest

from odylith.runtime.surfaces import render_casebook_dashboard as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)


@contextmanager
def _open_casebook(browser_context, *, width: int, populated: bool, invalid: bool = False):  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        bugs = [{
            "bug_id": "CB-901", "bug_route": "CB-901", "bug_key": "CB-901",
            "title": "Preserve <record> evidence", "summary": "The saved evidence must remain readable.",
            "search_text": "preserve record evidence", "status": "Open", "status_token": "open",
            "severity": "P2", "severity_token": "p2", "date": "2026-09-07",
        }] if populated else []
        payload = {
            "bugs": bugs, "counts": {"total_cases": len(bugs)},
            "filters": {"severity_tokens": ["p2"] if populated else [], "status_tokens": ["open"] if populated else []},
            "detail_manifest": {"CB-901": "/casebook-proof-detail.v1.js"} if populated else {},
        }
        pending = []
        page.route("**/casebook-proof-detail.v1.js", lambda route: pending.append(route))
        page.route("**/odylith/casebook/casebook.html*", lambda route: route.fulfill(
            status=200, content_type="text/html", body=renderer._render_html(payload=payload),
        ))
        page.goto(base_url + "/odylith/index.html?tab=casebook" + ("&bug=CB-999999" if invalid else ""),
                  wait_until="domcontentloaded")
        casebook = page.frame_locator("#frame-casebook")
        casebook.locator("#listMeta").wait_for()
        yield page, casebook, observation, pending


def _assert_readable(node):  # noqa: ANN001
    node.scroll_into_view_if_needed()
    assert node.evaluate("""node => {
        const box = node.getBoundingClientRect();
        const range = document.createRange();
        range.selectNodeContents(node);
        return Array.from(range.getClientRects()).every(rect =>
            rect.left >= box.left - 1 && rect.right <= box.right + 1 &&
            rect.top >= box.top - 1 && rect.bottom <= box.bottom + 1);
    }""")


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("invalid", [False, True], ids=["unselected", "invalid-route"])
def test_empty_repository_explains_absent_cases_without_filter_advice(browser_context, width: int, invalid: bool) -> None:  # noqa: ANN001
    with _open_casebook(browser_context, width=width, populated=False, invalid=invalid) as (page, casebook, observation, pending):
        casebook.locator("#bugList .empty-state").wait_for()
        assert casebook.locator("#bugList .empty-state").inner_text().strip() == "No Casebook cases have been recorded yet."
        detail = casebook.locator("#detailPane .empty-state")
        assert detail.inner_text().strip() == (
            "When you find a defect, ask Odylith to capture it with the expected behavior, "
            "actual behavior, and reproduction steps."
        )
        assert casebook.locator("#listMeta").inner_text() == "0 visible"
        assert casebook.locator(".bug-row").count() == 0
        assert not pending
        _assert_readable(casebook.locator("#bugList .empty-state"))
        _assert_readable(detail)
        screenshot = _failure_screenshot_path(f"casebook-empty-{width}-{invalid}")
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot))
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_filtered_cases_keep_recovery_and_ignore_late_detail(browser_context, width: int) -> None:  # noqa: ANN001
    with _open_casebook(browser_context, width=width, populated=True, invalid=True) as (page, casebook, observation, pending):
        casebook.locator('button.bug-row.active[data-bug="CB-901"]').wait_for()
        assert casebook.locator(".bug-row-title").inner_text() == "Preserve <record> evidence"
        assert casebook.locator(".bug-row-title record").count() == 0
        page.wait_for_function("() => new URL(location.href).searchParams.get('bug') === 'CB-901'")
        assert len(pending) == 1
        casebook.locator("#searchInput").fill("no matching record")
        assert casebook.locator("#bugList .empty-state").inner_text().strip() == "No Casebook entries match the current filters."
        recovery = "Select a different filter or search term to inspect Casebook detail."
        assert casebook.locator("#detailPane .empty-state").inner_text().strip() == recovery
        detail = {"CB-901": {"title": "Loaded evidence detail", "summary": "The retained detail arrives asynchronously."}}
        pending[0].fulfill(status=200, content_type="application/javascript",
                           body="window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ = " + json.dumps(detail) + ";")
        page.wait_for_function("() => !!document.querySelector('#frame-casebook').contentWindow.__ODYLITH_CASEBOOK_DETAIL_SHARDS__")
        assert casebook.locator("#detailPane .empty-state").inner_text().strip() == recovery
        _assert_readable(casebook.locator("#detailPane .empty-state"))
        casebook.locator("#searchInput").fill("")
        casebook.locator("#detailPane .detail-title", has_text="Loaded evidence detail").wait_for()
        assert casebook.locator('button.bug-row.active[data-bug="CB-901"]').count() == 1
        assert casebook.locator("#detailPane .empty-state").count() == 0
        _assert_clean_page(page, observation)
