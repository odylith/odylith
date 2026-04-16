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
        "blocked": 1,
        "inprogress": 2,
        "resolved": 3,
        "closed": 4,
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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
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


def test_casebook_workstream_action_chips_omit_radar_prefix(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
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
