from __future__ import annotations

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    _wait_for_shell_query_param,
    browser_context,
    compact_browser_context,
)


def _casebook_header_layout(casebook) -> dict[str, object]:  # noqa: ANN001
    return casebook.locator("#detailPane .detail-head").evaluate(
        """(node) => {
            const factsNode = node.querySelector(".summary-facts");
            const children = Array.from(node.children || []).map((child) => {
              const box = child.getBoundingClientRect();
              return {
                name: String(child.className || child.tagName || "").trim(),
                top: box.top,
                bottom: box.bottom,
              };
            });
            const sequenceOverlaps = [];
            for (let index = 1; index < children.length; index += 1) {
              const previous = children[index - 1];
              const current = children[index];
              if (current.top < previous.bottom - 1) {
                sequenceOverlaps.push({
                  previous: previous.name,
                  current: current.name,
                  overlapPx: Number((previous.bottom - current.top).toFixed(2)),
                });
              }
            }
            const facts = Array.from(node.querySelectorAll(".summary-fact")).map((fact) => {
              const label = fact.querySelector(".summary-fact-label");
              const value = fact.querySelector(".summary-fact-value");
              const labelBox = label ? label.getBoundingClientRect() : null;
              const valueBox = value ? value.getBoundingClientRect() : null;
              return {
                field: String(fact.getAttribute("data-summary-field") || (label && label.textContent) || "").trim(),
                stacked: Boolean(labelBox && valueBox && valueBox.top >= labelBox.bottom - 1),
              };
            });
            return {
              detailHeadClientWidth: node.clientWidth,
              detailHeadScrollWidth: node.scrollWidth,
              summaryFactsClientWidth: factsNode ? factsNode.clientWidth : 0,
              summaryFactsScrollWidth: factsNode ? factsNode.scrollWidth : 0,
              summaryFactCount: facts.length,
              sequenceOverlaps,
              unstackedFields: facts.filter((fact) => !fact.stacked).map((fact) => fact.field),
            };
        }"""
    )


def _select_casebook_layout_stress_row(page):  # noqa: ANN001
    casebook = page.frame_locator("#frame-casebook")
    candidates = casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes
          .map((node) => ({
            bug: String(node.getAttribute("data-bug") || "").trim(),
            title: String((node.querySelector(".bug-row-title") || {}).textContent || "").trim(),
            titleLength: String((node.querySelector(".bug-row-title") || {}).textContent || "").trim().length,
          }))
          .filter((row) => row.bug && row.title)
          .sort((left, right) => right.titleLength - left.titleLength)
        """
    )
    assert candidates, "expected Casebook rows for layout audit"

    for row in candidates[:12]:
        casebook.locator(f'button.bug-row[data-bug="{row["bug"]}"]').click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=str(row["bug"]))
        casebook.locator("#detailPane .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)
        layout = _casebook_header_layout(casebook)
        if int(layout["summaryFactCount"]) >= 4:
            return casebook, row, layout

    raise AssertionError("expected a Casebook detail with several summary facts for layout audit")


def test_casebook_detail_header_stays_readable_in_desktop_view(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    _casebook, row, layout = _select_casebook_layout_stress_row(page)

    assert row["titleLength"] >= 80, "expected a long-title Casebook row to stress the header layout"
    assert layout["sequenceOverlaps"] == [], f"detail header rows overlapped on desktop: {layout['sequenceOverlaps']}"
    assert layout["unstackedFields"] == [], f"summary fact labels and values collapsed inline: {layout['unstackedFields']}"
    assert int(layout["detailHeadScrollWidth"]) - int(layout["detailHeadClientWidth"]) <= 4
    assert int(layout["summaryFactsScrollWidth"]) - int(layout["summaryFactsClientWidth"]) <= 4

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_detail_header_stays_readable_in_compact_view(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    _casebook, _row, layout = _select_casebook_layout_stress_row(page)

    pane_layout = casebook.locator("#detailPane").evaluate(
        """(node) => ({
            clientWidth: node.clientWidth,
            scrollWidth: node.scrollWidth,
        })"""
    )

    assert layout["sequenceOverlaps"] == [], f"detail header rows overlapped in compact view: {layout['sequenceOverlaps']}"
    assert layout["unstackedFields"] == [], f"summary fact labels and values collapsed inline: {layout['unstackedFields']}"
    assert int(layout["detailHeadScrollWidth"]) - int(layout["detailHeadClientWidth"]) <= 4
    assert int(layout["summaryFactsScrollWidth"]) - int(layout["summaryFactsClientWidth"]) <= 4
    assert int(pane_layout["scrollWidth"]) - int(pane_layout["clientWidth"]) <= 16

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
