from __future__ import annotations

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    browser_context,
    compact_browser_context,
)


_CASEBOOK_URL = "/odylith/index.html?tab=casebook"


def _stress_casebook_list_row(casebook) -> dict[str, object]:  # noqa: ANN001
    row = casebook.locator("button.bug-row").first
    row.wait_for(timeout=15000)
    return row.evaluate(
        """(button) => {
            const title = button.querySelector(".bug-row-title");
            const summary = button.querySelector(".bug-row-summary");
            const meta = button.querySelector(".bug-row-meta");
            if (!title || !summary || !meta) {
              throw new Error("Casebook row is missing title, summary, or metadata");
            }
            title.textContent = [
              "Casebook selector keeps a consumer regression readable while long",
              "status evidence and source details try to escape the list column"
            ].join(" ");
            summary.textContent = [
              "The generated selector row must wrap prose from consumer Casebook records instead of inheriting",
              "native button whitespace and clipping text at the panel edge.",
              "The stress payload also includes one deliberately long unbroken token:",
              "casebook_selector_wrapping_contract_should_not_clip_valid_bug_memory_evidence"
            ].join(" ");
            meta.innerHTML = [
              '<span class="list-chip critical-chip">P1</span>',
              '<span class="list-chip warn-chip">Mitigated locally; pending platform release, consumer upgrade rerun, and browser proof</span>',
              '<span class="list-chip archive-chip">Investigation bucket with a long visible label</span>',
              '<span class="list-chip">Intel 23/23</span>'
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
              describe("summary", summary),
              describe("meta", meta),
              ...chips.map((chip, index) => describe(`chip-${index}`, chip)),
            ];
            return {
              row: targets[0],
              title: targets[1],
              summary: targets[2],
              meta: targets[3],
              metaFlexWrap: window.getComputedStyle(meta).flexWrap,
              titleLines: lineCount(title),
              summaryLines: lineCount(summary),
              chipLines: chips.map((chip) => lineCount(chip)),
              chipRows: new Set(chips.map((chip) => Math.round(chip.getBoundingClientRect().top))).size,
              overflowTargets: targets.filter((item) => item.overflowX > 4).map((item) => item.name),
              escapingTargets: targets.filter((item) => item.escapesRow).map((item) => item.name),
            };
        }"""
    )


def _assert_casebook_list_layout_stress(base_url: str, context) -> None:  # noqa: ANN001
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + _CASEBOOK_URL, wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    layout = _stress_casebook_list_row(casebook)

    assert layout["row"]["whiteSpace"] == "normal"
    assert layout["title"]["whiteSpace"] == "normal"
    assert layout["summary"]["whiteSpace"] == "normal"
    assert layout["metaFlexWrap"] == "wrap"
    assert int(layout["titleLines"]) >= 2
    assert int(layout["summaryLines"]) >= 2
    assert int(layout["chipRows"]) >= 2
    assert any(int(line_count) >= 2 for line_count in layout["chipLines"])
    assert layout["overflowTargets"] == []
    assert layout["escapingTargets"] == []

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def _assert_casebook_detail_left_gutter(base_url: str, context, *, compact: bool = False) -> None:  # noqa: ANN001
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
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
          if (!shell || !panel || !detail || !summary) {
            throw new Error("Casebook detail layout nodes are missing");
          }
          const box = (node) => node.getBoundingClientRect();
          const shellBox = box(shell);
          const panelBox = box(panel);
          const detailBox = box(detail);
          const summaryBox = box(summary);
          return {
            shellLeft: Number(shellBox.left.toFixed(2)),
            panelLeft: Number(panelBox.left.toFixed(2)),
            detailLeft: Number(detailBox.left.toFixed(2)),
            summaryLeft: Number(summaryBox.left.toFixed(2)),
            detailPaddingLeft: Number.parseFloat(window.getComputedStyle(detail).paddingLeft) || 0,
          };
        }"""
    )

    expected_padding = 10 if compact else 12
    assert layout["detailPaddingLeft"] <= expected_padding
    assert layout["detailLeft"] - layout["panelLeft"] <= expected_padding + 2
    assert layout["summaryLeft"] - layout["panelLeft"] <= expected_padding + 2

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


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
