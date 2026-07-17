from __future__ import annotations

from functools import cmp_to_key
import re

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    _wait_for_shell_query_param,
    browser_context,
)


def _visible_casebook_rows(casebook) -> list[dict[str, str]]:  # noqa: ANN001
    return casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes.map((node) => {
          const chips = Array.from(node.querySelectorAll(".list-chip"))
            .map((chip) => (chip.textContent || "").trim());
          return {
            bug_id: ((node.querySelector(".bug-row-kicker") && node.querySelector(".bug-row-kicker").textContent) || "").trim(),
            date: ((node.querySelector(".bug-row-date") && node.querySelector(".bug-row-date").textContent) || "").trim(),
            title: ((node.querySelector(".bug-row-title") && node.querySelector(".bug-row-title").textContent) || "").trim(),
            severity: chips[0] || "",
            status: chips[1] || "",
          };
        })"""
    )


def _bug_id_number(row: dict[str, str]) -> int:
    match = re.fullmatch(r"CB-(\d+)", str(row.get("bug_id") or "").strip())
    return int(match.group(1)) if match else 0


def _severity_rank(row: dict[str, str]) -> int:
    match = re.fullmatch(r"P(\d+)", str(row.get("severity") or "").strip(), flags=re.IGNORECASE)
    return int(match.group(1)) if match else 99


def _status_rank(row: dict[str, str]) -> int:
    token = re.sub(r"[^a-z0-9]+", "", str(row.get("status") or "").lower())
    return {
        "open": 0,
        "inprogress": 1,
        "mitigated": 2,
        "monitoring": 3,
        "resolved": 4,
        "fixedpendingrelease": 5,
        "closed": 6,
    }.get(token, 50)


def _compare_text(left: str, right: str) -> int:
    left_token = str(left or "").casefold()
    right_token = str(right or "").casefold()
    return (left_token > right_token) - (left_token < right_token)


def _first_non_zero(*values: int) -> int:
    return next((value for value in values if value != 0), 0)


def _compare_rows(sort_token: str):  # noqa: ANN202
    def _compare(left: dict[str, str], right: dict[str, str]) -> int:
        date_desc = _compare_text(str(right.get("date") or ""), str(left.get("date") or ""))
        date_asc = _compare_text(str(left.get("date") or ""), str(right.get("date") or ""))
        id_desc = _bug_id_number(right) - _bug_id_number(left)
        id_asc = _bug_id_number(left) - _bug_id_number(right)
        title_asc = _compare_text(str(left.get("title") or ""), str(right.get("title") or ""))
        if sort_token == "oldest":
            return _first_non_zero(date_asc, id_asc, title_asc)
        if sort_token == "bug-id":
            return _first_non_zero(id_desc, date_desc, title_asc)
        if sort_token == "priority":
            return _first_non_zero(
                _severity_rank(left) - _severity_rank(right),
                _status_rank(left) - _status_rank(right),
                date_desc,
                id_desc,
                title_asc,
            )
        if sort_token == "status":
            return _first_non_zero(
                _status_rank(left) - _status_rank(right),
                date_desc,
                _severity_rank(left) - _severity_rank(right),
                id_desc,
                title_asc,
            )
        return _first_non_zero(date_desc, id_desc, title_asc)

    return _compare


def _assert_sorted(rows: list[dict[str, str]], sort_token: str) -> None:
    assert rows, "expected visible Casebook rows"
    expected = sorted(rows, key=cmp_to_key(_compare_rows(sort_token)))
    assert rows == expected


def test_casebook_sort_control_orders_rows_and_round_trips_url_state(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator("#sortFilter").wait_for(timeout=15000)

    assert casebook.locator("#sortFilter").input_value() == "newest"
    newest_rows = _visible_casebook_rows(casebook)
    assert len(newest_rows) > 1
    _assert_sorted(newest_rows, "newest")

    for sort_token in ("oldest", "bug-id", "priority", "status"):
        casebook.locator("#sortFilter").select_option(sort_token)
        _wait_for_shell_query_param(page, tab="casebook", key="sort", value=sort_token)
        assert casebook.locator("#sortFilter").input_value() == sort_token
        _assert_sorted(_visible_casebook_rows(casebook), sort_token)

    casebook.locator("#sortFilter").select_option("newest")
    page.wait_for_function(
        """() => {
          const url = new URL(window.location.href);
          return url.searchParams.get("tab") === "casebook" && !url.searchParams.has("sort");
        }""",
        timeout=15000,
    )
    assert casebook.locator("#sortFilter").input_value() == "newest"
    _assert_sorted(_visible_casebook_rows(casebook), "newest")

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_discards_unknown_status_filter_and_humanizes_compact_status(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url
        + "/odylith/index.html?tab=casebook&bug=CB-150&status=ForwardFixUpdatedLocallyPendingPlatformReleaseDeploy",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator('button.bug-row.active[data-bug="CB-150"]').wait_for(timeout=15000)
    page.wait_for_function(
        """() => {
          const url = new URL(window.location.href);
          return url.searchParams.get("tab") === "casebook"
            && url.searchParams.get("bug") === "CB-150"
            && !url.searchParams.has("status");
        }""",
        timeout=15000,
    )

    assert casebook.locator("#statusFilter").input_value() == ""
    status_options = casebook.locator("#statusFilter option").evaluate_all(
        """nodes => nodes.map((node) => (node.textContent || "").trim())"""
    )
    assert status_options == ["All statuses", "Open", "In progress", "Fixed pending release", "Closed"]
    assert casebook.locator("#listMeta").inner_text().strip() != "0 visible"
    facts = casebook.locator("#detailPane .summary-fact").evaluate_all(
        """nodes => Object.fromEntries(nodes.map((node) => [
          (node.querySelector(".summary-fact-label")?.textContent || "").trim(),
          (node.querySelector(".summary-fact-value")?.textContent || "").trim(),
        ]))"""
    )
    assert facts["Status"] == "Fixed pending release"
    assert facts["Type"] == "Product"
    detail_chips = casebook.locator("#detailPane .detail-meta .meta-chip").evaluate_all(
        """nodes => nodes.map((node) => (node.textContent || "").trim())"""
    )
    assert "Fixed pending release" in detail_chips
    active_status = casebook.locator('button.bug-row.active[data-bug="CB-150"] .list-chip').nth(1).inner_text().strip()
    assert active_status == "Fixed pending release"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_empty_search_state_is_visible_and_honest(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator("button.bug-row").first.wait_for(timeout=15000)
    casebook.locator("#searchInput").fill("no-such-casebook-record-for-empty-state-proof")
    casebook.locator("#listMeta", has_text="0 visible").wait_for(timeout=15000)

    assert casebook.locator("#bugList .empty-state").inner_text().strip() == (
        "No Casebook entries match the current filters."
    )
    assert casebook.locator("#detailPane .empty-state").inner_text().strip() == (
        "Select a different filter or search term to inspect Casebook detail."
    )
    assert casebook.locator("button.bug-row").count() == 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_workstream_action_chips_omit_radar_prefix(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    rows = casebook.locator("button.bug-row")
    row_count = min(rows.count(), 40)
    found_workstream_chip = False

    for index in range(row_count):
        row = rows.nth(index)
        bug_route = str(row.get_attribute("data-bug") or "").strip()
        if not bug_route:
            continue
        row.click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
        casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
        labels = casebook.locator("#detailPane a.action-chip").evaluate_all(
            """nodes => nodes.map((node) => (node.textContent || "").trim()).filter(Boolean)"""
        )
        assert not any(re.fullmatch(r"Radar B-\d+", label) for label in labels)
        if any(re.fullmatch(r"B-\d+", label) for label in labels):
            found_workstream_chip = True
            break

    assert found_workstream_chip, "expected at least one Casebook workstream chip"
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_github_issue_signal_opens_in_new_browser_tab(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    context.route(
        "https://github.com/**",
        lambda route: route.fulfill(
            status=200,
            content_type="text/html",
            body="<!doctype html><html><body><h1>Mock GitHub issue</h1></body></html>",
        ),
    )
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook&bug=CB-136", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator('button.bug-row.active[data-bug="CB-136"]').wait_for(timeout=15000)
    head_actions = casebook.locator("#detailPane .detail-head .detail-links a.action-chip").evaluate_all(
        """nodes => nodes.map((node) => node.getAttribute("href") || "")"""
    )
    assert "https://github.com/odylith/odylith/issues/21" not in head_actions

    signal = casebook.locator(".brief-card", has_text="Signal")
    issue = signal.locator('a.action-chip[href="https://github.com/odylith/odylith/issues/21"]')
    issue.wait_for(timeout=15000)
    issue_attrs = issue.evaluate(
        """node => ({
          label: (node.textContent || "").trim(),
          href: node.getAttribute("href") || "",
          target: node.getAttribute("target") || "",
          rel: node.getAttribute("rel") || "",
        })"""
    )

    assert issue_attrs == {
        "label": "GitHub issue: odylith/odylith#21",
        "href": "https://github.com/odylith/odylith/issues/21",
        "target": "_blank",
        "rel": "noopener noreferrer",
    }
    with page.expect_popup() as popup_info:
        issue.click()
    popup = popup_info.value
    popup.wait_for_load_state("domcontentloaded")
    assert popup.locator("h1").inner_text().strip() == "Mock GitHub issue"
    assert popup.url == "https://github.com/odylith/odylith/issues/21"
    popup.close()

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
