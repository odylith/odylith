from __future__ import annotations

import re

import pytest

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _atlas_total,
    _first_non_default_option,
    _new_page,
    _wait_for_locator_count,
    _wait_for_compass_brief_state,
    _wait_for_shell_query_param,
    browser_context,
)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).strip().lower())


def test_radar_filter_audit_accepts_compact_ids_and_normalized_titles(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)

    target = radar.locator("button[data-idea-id]").first
    idea_id = str(target.get_attribute("data-idea-id") or "").strip()
    title = target.locator(".row-title").inner_text().strip()
    compact_query = idea_id.replace("-", "")
    normalized_title = _normalize_token(title)

    assert idea_id
    assert compact_query and compact_query != idea_id
    assert normalized_title

    radar.locator("#query").fill(compact_query.lower())
    _wait_for_locator_count(page, "#frame-radar", "button[data-idea-id]", 1)
    radar.locator(f'button[data-idea-id="{idea_id}"]').wait_for(timeout=15000)

    radar.locator("#query").fill(normalized_title)
    radar.locator(f'button[data-idea-id="{idea_id}"]').wait_for(timeout=15000)
    assert radar.locator(f'button[data-idea-id="{idea_id}"]').count() == 1

    radar.locator("#query").fill("")
    assert radar.locator("button[data-idea-id]").count() > 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_registry_filter_audit_accepts_punctuation_free_component_queries(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
    assert response is not None and response.ok

    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    baseline_count = registry.locator("button[data-component]").count()
    assert baseline_count > 1

    registry.locator("#search").fill("odylithmemorybackend")
    _wait_for_locator_count(page, "#frame-registry", "button[data-component]", 1)
    registry.locator('button[data-component="odylith-memory-backend"]').wait_for(timeout=15000)

    registry.locator("#search").fill("odylith remote retrieval")
    _wait_for_locator_count(page, "#frame-registry", "button[data-component]", 1)
    registry.locator('button[data-component="odylith-remote-retrieval"]').wait_for(timeout=15000)

    registry.locator("#resetFilters").click()
    page.wait_for_function(
        """() => {
            const frame = document.querySelector("#frame-registry");
            const doc = frame && frame.contentDocument;
            const search = doc && doc.querySelector("#search");
            return Boolean(search) && search.value === "";
        }""",
        timeout=15000,
    )
    assert registry.locator("button[data-component]").count() == baseline_count

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_filter_audit_accepts_compact_bug_ids_and_normalized_titles(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

    first_bug = casebook.locator("button.bug-row").first
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_id = first_bug.locator(".bug-row-kicker").inner_text().strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    compact_bug_id = bug_id.replace("-", "")
    normalized_title = _normalize_token(bug_title)

    assert bug_route
    assert bug_id
    assert compact_bug_id and compact_bug_id != bug_id
    assert normalized_title

    casebook.locator("#searchInput").fill(compact_bug_id.lower())
    _wait_for_locator_count(page, "#frame-casebook", "button.bug-row", 1)
    casebook.locator(f'button.bug-row[data-bug="{bug_route}"]').wait_for(timeout=15000)

    casebook.locator("#searchInput").fill(normalized_title)
    casebook.locator(f'button.bug-row[data-bug="{bug_route}"]').wait_for(timeout=15000)
    assert casebook.locator(f'button.bug-row[data-bug="{bug_route}"]').count() >= 1

    casebook.locator("#searchInput").fill("")
    assert casebook.locator("button.bug-row").count() > 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_filter_audit_accepts_compact_diagram_ids_and_normalized_titles(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas&diagram=D-025", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)
    baseline_total = _atlas_total(atlas)
    assert baseline_total > 1

    title = atlas.locator("#diagramTitle").inner_text().strip()
    normalized_title = _normalize_token(title)
    assert normalized_title

    atlas.locator("#search").fill("D025")
    page.wait_for_function(
        """() => {
            const frame = document.querySelector("#frame-atlas");
            const doc = frame && frame.contentDocument;
            const total = doc && doc.querySelector("#statTotal");
            const diagramId = doc && doc.querySelector("#diagramId");
            return Boolean(total && diagramId)
              && total.textContent.trim() === "1"
              && diagramId.textContent.trim() === "D-025";
        }""",
        timeout=15000,
    )

    atlas.locator("#search").fill(normalized_title)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)
    filtered_total = _atlas_total(atlas)
    assert 1 <= filtered_total <= baseline_total

    atlas.locator("#search").fill("")
    assert _atlas_total(atlas) == baseline_total

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_filter_audit_preserves_valid_audit_day_across_window_changes(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _wait_for_compass_brief_state(
        page,
        window_token="24h",
        scope_label="Global",
        statuses=("ready", "unavailable"),
    )

    audit_bounds = compass.locator("#audit-day-input").evaluate(
        """node => ({
            value: String(node.value || "").trim(),
            min: String(node.min || "").trim(),
            max: String(node.max || "").trim(),
        })"""
    )
    current_day = str(audit_bounds["value"] or "").strip()
    min_day = str(audit_bounds["min"] or "").strip()
    max_day = str(audit_bounds["max"] or "").strip()
    target_day = max_day if max_day and max_day != current_day else min_day if min_day and min_day != current_day else ""
    if not target_day:
        pytest.skip("Compass fixture does not currently expose multiple valid audit days.")

    compass.locator("#audit-day-input").evaluate(
        """(node, value) => {
            node.value = value;
            node.dispatchEvent(new Event("change", { bubbles: true }));
        }""",
        target_day,
    )
    _wait_for_shell_query_param(page, tab="compass", key="audit_day", value=target_day)
    page.wait_for_function(
        """(targetDay) => {
            const frame = document.querySelector("#frame-compass");
            const doc = frame && frame.contentDocument;
            const input = doc && doc.querySelector("#audit-day-input");
            return Boolean(input) && String(input.value || "").trim() === targetDay;
        }""",
        arg=target_day,
        timeout=15000,
    )

    compass.locator('button[data-window="48h"]').click()
    _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
    _wait_for_shell_query_param(page, tab="compass", key="audit_day", value=target_day)
    page.wait_for_function(
        """(targetDay) => {
            const frame = document.querySelector("#frame-compass");
            const doc = frame && frame.contentDocument;
            const input = doc && doc.querySelector("#audit-day-input");
            return Boolean(input) && String(input.value || "").trim() === targetDay;
        }""",
        arg=target_day,
        timeout=15000,
    )
    compass = page.frame_locator("#frame-compass")
    assert compass.locator("#audit-day-input").input_value() == target_day
    _wait_for_compass_brief_state(
        page,
        window_token="48h",
        scope_label="Global",
        statuses=("ready", "unavailable"),
    )

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
