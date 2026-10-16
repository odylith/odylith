from __future__ import annotations

import json

from odylith.runtime.surfaces import render_casebook_dashboard as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    browser_context,
    compact_browser_context,
)


_CASEBOOK_URL = "/odylith/index.html?tab=casebook"
_FULL_SUMMARY = (
    "The complete source summary remains in the selected detail after the sidebar is simplified; "
    "summaryonlycustodycue also keeps this record searchable without duplicating prose in the list."
)


def _stress_casebook_list_row(casebook) -> dict[str, object]:  # noqa: ANN001
    row = casebook.locator("button.bug-row").first
    row.wait_for(timeout=15000)
    return row.evaluate(
        """(button) => {
            const title = button.querySelector(".bug-row-title");
            const meta = button.querySelector(".bug-row-meta");
            if (!title || !meta || button.querySelector(".bug-row-summary")) {
              throw new Error("Casebook row lost its title or metadata, or repeated the detail summary");
            }
            title.textContent = [
              "Casebook selector keeps a consumer regression readable while long",
              "status evidence and source details try to escape the list column"
            ].join(" ");
            meta.innerHTML = [
              '<span class="list-chip critical-chip">P1</span>',
              '<span class="list-chip warn-chip">Mitigated locally; pending platform release, consumer upgrade rerun, and browser proof</span>',
              '<span class="list-chip archive-chip">Investigation bucket with a long visible label</span>'
            ].join("");

            const rowBox = button.getBoundingClientRect();
            const rowRight = rowBox.right + 1;
            const lineCount = (node) => {
              const style = window.getComputedStyle(node);
              const lineHeight = Number.parseFloat(style.lineHeight) || Number.parseFloat(style.fontSize) || 16;
              return Math.round(node.getBoundingClientRect().height / lineHeight);
            };
            const describe = (name, node) => {
              const box = node.getBoundingClientRect();
              return {
                name,
                clientWidth: node.clientWidth,
                scrollWidth: node.scrollWidth,
                right: Number(box.right.toFixed(2)),
                rowRight: Number(rowRight.toFixed(2)),
                overflowX: node.scrollWidth - node.clientWidth,
                escapesRow: box.right > rowRight,
                whiteSpace: window.getComputedStyle(node).whiteSpace,
              };
            };
            const chips = Array.from(meta.querySelectorAll(".list-chip"));
            const targets = [
              describe("row", button),
              describe("title", title),
              describe("meta", meta),
              ...chips.map((chip, index) => describe(`chip-${index}`, chip)),
            ];
            return {
              row: targets[0],
              title: targets[1],
              meta: targets[2],
              metaFlexWrap: window.getComputedStyle(meta).flexWrap,
              titleLines: lineCount(title),
              chipLines: chips.map((chip) => lineCount(chip)),
              chipRows: new Set(chips.map((chip) => Math.round(chip.getBoundingClientRect().top))).size,
              overflowTargets: targets.filter((item) => item.overflowX > 4).map((item) => item.name),
              escapingTargets: targets.filter((item) => item.escapesRow).map((item) => item.name),
            };
        }"""
    )


def _assert_casebook_list_layout_stress(base_url: str, context) -> None:  # noqa: ANN001
    with _new_page(context) as (page, observation):
        payload = {
            "bugs": [{
                "bug_id": "CB-901", "bug_route": "CB-901", "bug_key": "CB-901",
                "title": "Preserve Casebook source custody", "summary": _FULL_SUMMARY,
                "search_text": "preserve Casebook source custody", "status": "Open", "status_token": "open",
                "severity": "P1", "severity_token": "p1", "date": "2026-10-06",
                "intelligence_coverage": {"captured_count": 22, "total_fields": 23,
                                          "missing_fields": ["Verification"], "required_missing_fields": ["Verification"]},
            }],
            "counts": {"total_cases": 1},
            "filters": {"severity_tokens": ["p1"], "status_tokens": ["open"]},
            "detail_manifest": {"CB-901": "/casebook-sidebar-detail.v1.js"},
        }
        page.route("**/odylith/casebook/casebook.html*", lambda route: route.fulfill(
            status=200, content_type="text/html", body=renderer._render_html(payload=payload),
        ))
        page.route("**/casebook-sidebar-detail.v1.js", lambda route: route.fulfill(
            status=200, content_type="application/javascript",
            body="window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ = " + json.dumps({
                "CB-901": {"title": "Preserve Casebook source custody", "summary": _FULL_SUMMARY,
                           "severity": "P1", "status": "Open",
                           "intelligence_coverage": {"captured_count": 22, "total_fields": 23,
                                                     "missing_fields": ["Verification"],
                                                     "required_missing_fields": ["Verification"]}},
            }) + ";",
        ))
        response = page.goto(base_url + _CASEBOOK_URL, wait_until="domcontentloaded")
        assert response is not None and response.ok

        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
        row = casebook.locator('button.bug-row[data-bug="CB-901"]')
        row.wait_for(timeout=15000)
        assert row.locator(".bug-row-kicker").inner_text() == "CB-901"
        assert row.locator(".bug-row-title").inner_text() == "Preserve Casebook source custody"
        assert row.locator(".bug-row-date").inner_text() == "2026-10-06"
        assert [chip.inner_text() for chip in row.locator(".list-chip").all()] == ["P1", "Open"]
        assert row.locator(".bug-row-summary").count() == 0
        assert _FULL_SUMMARY not in row.inner_text()
        casebook.locator("#searchInput").fill("summaryonlycustodycue")
        assert casebook.locator("#listMeta").inner_text() == "1 visible"
        assert row.count() == 1
        row.click()
        detail = casebook.locator("#detailPane .detail-summary")
        detail.wait_for(timeout=15000)
        assert detail.inner_text() == _FULL_SUMMARY
        assert detail.evaluate("node => window.getComputedStyle(node).webkitLineClamp") == "none"
        assert "Intel" not in casebook.locator("#detailPane .detail-meta").inner_text()
        gaps = casebook.locator("#detailPane details", has=casebook.get_by_text("Capture Gaps", exact=True))
        assert gaps.count() == 1
        assert gaps.get_attribute("open") is None
        assert "22 of 23 recommended fields captured" in (gaps.text_content() or "")
        layout = _stress_casebook_list_row(casebook)

        assert layout["row"]["whiteSpace"] == "normal"
        assert layout["title"]["whiteSpace"] == "normal"
        assert layout["metaFlexWrap"] == "wrap"
        assert int(layout["titleLines"]) >= 2
        assert int(layout["chipRows"]) >= 2
        assert any(int(line_count) >= 2 for line_count in layout["chipLines"])
        assert layout["overflowTargets"] == []
        assert layout["escapingTargets"] == []

        _assert_clean_page(page, observation)


def _assert_casebook_detail_left_gutter(base_url: str, context, *, compact: bool = False) -> None:  # noqa: ANN001
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + _CASEBOOK_URL, wait_until="domcontentloaded")
        assert response is not None and response.ok

        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
        casebook.locator("#detailPane .detail-summary").wait_for(timeout=15000)
        layout = casebook.locator("body").evaluate(
            """() => {
          const shell = document.querySelector(".shell");
          const panel = document.querySelector(".detail-panel");
          const detail = document.querySelector("#detailPane");
          const summary = document.querySelector("#detailPane .detail-summary");
          const summaryCard = document.querySelector("#detailPane .casebook-summary-card");
          if (!shell || !panel || !detail || !summary || !summaryCard) {
            throw new Error("Casebook detail layout nodes are missing");
          }
          summary.textContent = [
            "The summary body must use the full Casebook card width even when one consumer record carries",
            "casebook_summary_width_contract_should_wrap_this_long_unbroken_migration_token_without_clipping"
          ].join(" ");
          const box = (node) => node.getBoundingClientRect();
          const shellBox = box(shell);
          const panelBox = box(panel);
          const detailBox = box(detail);
          const summaryCardBox = box(summaryCard);
          const summaryBox = box(summary);
          const detailStyle = window.getComputedStyle(detail);
          const detailContentWidth = detailBox.width
            - (Number.parseFloat(detailStyle.paddingLeft) || 0)
            - (Number.parseFloat(detailStyle.paddingRight) || 0);
          const summaryCardTitle = summaryCard.querySelector(".brief-card-title");
          return {
            shellLeft: Number(shellBox.left.toFixed(2)),
            panelLeft: Number(panelBox.left.toFixed(2)),
            detailLeft: Number(detailBox.left.toFixed(2)),
            summaryCardLeft: Number(summaryCardBox.left.toFixed(2)),
            summaryCardWidth: Number(summaryCardBox.width.toFixed(2)),
            detailContentWidth: Number(detailContentWidth.toFixed(2)),
            summaryLeft: Number(summaryBox.left.toFixed(2)),
            summaryWidth: Number(summaryBox.width.toFixed(2)),
            summaryMaxWidth: window.getComputedStyle(summary).maxWidth,
            summaryOverflowX: summary.scrollWidth - summary.clientWidth,
            summaryCardTitle: String(summaryCardTitle && summaryCardTitle.textContent || "").trim(),
            detailPaddingLeft: Number.parseFloat(window.getComputedStyle(detail).paddingLeft) || 0,
          };
        }"""
        )

        expected_padding = 10 if compact else 12
        assert layout["detailPaddingLeft"] <= expected_padding
        assert layout["detailLeft"] - layout["panelLeft"] <= expected_padding + 2
        assert layout["summaryCardLeft"] - layout["panelLeft"] <= expected_padding + 2
        assert abs(float(layout["summaryCardWidth"]) - float(layout["detailContentWidth"])) <= 4
        assert layout["summaryCardTitle"] == "Summary"
        assert 12 <= layout["summaryLeft"] - layout["summaryCardLeft"] <= 24
        assert layout["summaryMaxWidth"] == "none"
        assert float(layout["summaryWidth"]) >= float(layout["summaryCardWidth"]) - 48
        assert int(layout["summaryOverflowX"]) <= 4

        _assert_clean_page(page, observation)


def test_casebook_list_long_content_wraps_on_desktop(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    _assert_casebook_list_layout_stress(base_url, context)


def test_casebook_list_long_content_wraps_in_compact_view(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    _assert_casebook_list_layout_stress(base_url, context)


def test_casebook_detail_uses_compact_left_gutter_on_desktop(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    _assert_casebook_detail_left_gutter(base_url, context)


def test_casebook_detail_uses_compact_left_gutter_in_compact_view(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    _assert_casebook_detail_left_gutter(base_url, context, compact=True)
