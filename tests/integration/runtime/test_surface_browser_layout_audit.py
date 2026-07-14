from __future__ import annotations

import json
from pathlib import Path
import re
import shutil

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _browser,
    _select_casebook_bug_with_detail_selector,
    _select_radar_row_with_link,
    _select_radar_workstream_with_detail_selector,
    _select_registry_component_with_detail_selector,
    _new_page,
    _static_server,
    _wait_for_shell_query_param,
    browser_context,
    compact_browser_context,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]


def _casebook_header_layout(casebook) -> dict[str, object]:  # noqa: ANN001
    return casebook.locator("#detailPane .detail-head").evaluate(
        """(node) => {
            const factsNode = node.querySelector(".summary-facts");
            const summaryNode = node.querySelector(".detail-summary");
            const summaryCardNode = node.querySelector(".casebook-summary-card");
            const summaryTitleNode = summaryCardNode ? summaryCardNode.querySelector(".brief-card-title") : null;
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
              factFields: facts.map((fact) => fact.field),
              detailKickerCount: node.querySelectorAll(".detail-kicker").length,
              childOrder: children.map((child) => child.name),
              factsBeforeSummary: Boolean(!factsNode || !summaryNode || factsNode.compareDocumentPosition(summaryNode) & Node.DOCUMENT_POSITION_FOLLOWING),
              summaryInCard: Boolean(summaryCardNode && summaryNode && summaryCardNode.contains(summaryNode)),
              summaryCardWidth: summaryCardNode ? Number(summaryCardNode.getBoundingClientRect().width.toFixed(2)) : 0,
              detailHeadWidth: Number(node.getBoundingClientRect().width.toFixed(2)),
              summaryTitle: String(summaryTitleNode && summaryTitleNode.textContent || "").trim(),
              sequenceOverlaps,
              unstackedFields: facts.filter((fact) => !fact.stacked).map((fact) => fact.field),
            };
        }"""
    )


def _select_casebook_layout_stress_row(page):  # noqa: ANN001
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("button.bug-row").first.wait_for(timeout=15000)
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
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    _casebook, row, layout = _select_casebook_layout_stress_row(page)

    assert row["titleLength"] >= 80, "expected a long-title Casebook row to stress the header layout"
    assert "summary-facts" in layout["childOrder"]
    assert "brief-card casebook-summary-card" in layout["childOrder"]
    assert layout["childOrder"].index("summary-facts") < layout["childOrder"].index("brief-card casebook-summary-card")
    assert layout["factsBeforeSummary"], "Casebook primary fact cards should render before the supporting summary copy"
    assert layout["summaryInCard"], "Casebook summary copy should live inside the narrative card"
    assert layout["summaryTitle"] == "Summary"
    assert abs(float(layout["summaryCardWidth"]) - float(layout["detailHeadWidth"])) <= 4
    assert layout["detailKickerCount"] == 0, "Casebook detail should not render a standalone bug-id kicker above the title"
    assert "Bug ID" in layout["factFields"], "Casebook detail should keep Bug ID in the summary fact cards"
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
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    _casebook, _row, layout = _select_casebook_layout_stress_row(page)

    pane_layout = casebook.locator("#detailPane").evaluate(
        """(node) => ({
            clientWidth: node.clientWidth,
            scrollWidth: node.scrollWidth,
        })"""
    )

    assert "summary-facts" in layout["childOrder"]
    assert "brief-card casebook-summary-card" in layout["childOrder"]
    assert layout["childOrder"].index("summary-facts") < layout["childOrder"].index("brief-card casebook-summary-card")
    assert layout["factsBeforeSummary"], "Casebook primary fact cards should stay ahead of the supporting summary copy in compact view"
    assert layout["summaryInCard"], "Casebook summary copy should live inside the narrative card in compact view"
    assert layout["summaryTitle"] == "Summary"
    assert abs(float(layout["summaryCardWidth"]) - float(layout["detailHeadWidth"])) <= 4
    assert layout["detailKickerCount"] == 0, "Casebook detail should not render a standalone bug-id kicker above the title in compact view"
    assert "Bug ID" in layout["factFields"], "Casebook detail should keep Bug ID in the summary fact cards in compact view"
    assert layout["sequenceOverlaps"] == [], f"detail header rows overlapped in compact view: {layout['sequenceOverlaps']}"
    assert layout["unstackedFields"] == [], f"summary fact labels and values collapsed inline: {layout['unstackedFields']}"
    assert int(layout["detailHeadScrollWidth"]) - int(layout["detailHeadClientWidth"]) <= 4
    assert int(layout["summaryFactsScrollWidth"]) - int(layout["summaryFactsClientWidth"]) <= 4
    assert int(pane_layout["scrollWidth"]) - int(pane_layout["clientWidth"]) <= 16

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def _atlas_header_layout(atlas) -> dict[str, object]:  # noqa: ANN001
    return atlas.locator(".hero-copy").evaluate(
        """(node) => {
            const hero = node.closest(".hero");
            const factsNode = node.querySelector(".diagram-facts");
            const titleNode = node.querySelector("#diagramTitle");
            const controlsNode = hero ? hero.querySelector(".source-links-wrap") : null;
            const titleBox = titleNode ? titleNode.getBoundingClientRect() : null;
            const factsBox = factsNode ? factsNode.getBoundingClientRect() : null;
            const controlsBox = controlsNode ? controlsNode.getBoundingClientRect() : null;
            const facts = Array.from(node.querySelectorAll(".diagram-fact")).map((fact) => {
              const label = fact.querySelector(".diagram-fact-label");
              const value = fact.querySelector(".diagram-fact-value");
              const labelBox = label ? label.getBoundingClientRect() : null;
              const valueBox = value ? value.getBoundingClientRect() : null;
              return {
                field: String(fact.getAttribute("data-fact") || (label && label.textContent) || "").trim(),
                stacked: Boolean(labelBox && valueBox && valueBox.top >= labelBox.bottom - 1),
              };
            });
            return {
              heroClientWidth: hero ? hero.clientWidth : 0,
              heroScrollWidth: hero ? hero.scrollWidth : 0,
              heroCopyClientWidth: node.clientWidth,
              heroCopyScrollWidth: node.scrollWidth,
              factsClientWidth: factsNode ? factsNode.clientWidth : 0,
              factsScrollWidth: factsNode ? factsNode.scrollWidth : 0,
              factCount: facts.length,
              factFields: facts.map((fact) => fact.field),
              controlsBelowFacts: Boolean(factsBox && controlsBox && controlsBox.top >= factsBox.bottom - 1),
              heroUnusedWidth: hero ? Math.max(0, hero.clientWidth - node.clientWidth) : 0,
              headlineOverlap: Boolean(titleBox && factsBox && factsBox.top < titleBox.bottom - 1),
              unstackedFields: facts.filter((fact) => !fact.stacked).map((fact) => fact.field),
            };
        }"""
    )


def _select_atlas_layout_stress_diagram(page):  # noqa: ANN001
    atlas = page.frame_locator("#frame-atlas")
    candidates = atlas.locator("button[data-diagram]").evaluate_all(
        """nodes => nodes
          .map((node) => ({
            diagram: String(node.getAttribute("data-diagram") || "").trim(),
            title: String((node.querySelector(".diagram-name") || {}).textContent || "").trim(),
            titleLength: String((node.querySelector(".diagram-name") || {}).textContent || "").trim().length,
          }))
          .filter((row) => row.diagram && row.title)
          .sort((left, right) => right.titleLength - left.titleLength)
        """
    )
    assert candidates, "expected Atlas rows for layout audit"

    for row in candidates[:12]:
        atlas.locator(f'button[data-diagram="{row["diagram"]}"]').click()
        _wait_for_shell_query_param(page, tab="atlas", key="diagram", value=str(row["diagram"]))
        atlas.locator("#diagramTitle", has_text=str(row["title"])).wait_for(timeout=15000)
        layout = _atlas_header_layout(atlas)
        if int(layout["factCount"]) >= 6:
            return atlas, row, layout

    raise AssertionError("expected an Atlas detail with fact cards for layout audit")


def test_atlas_detail_header_uses_readable_fact_cards_on_desktop(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    _atlas, row, layout = _select_atlas_layout_stress_diagram(page)

    assert row["titleLength"] >= 20, "expected a non-trivial Atlas title for header layout audit"
    assert int(layout["factCount"]) == 6
    assert layout["factFields"][0] == "diagram-id"
    assert layout["controlsBelowFacts"], "Atlas controls still reserve a side lane instead of stacking under the fact cards"
    assert int(layout["heroUnusedWidth"]) <= 8
    assert not layout["headlineOverlap"], "Atlas title and fact cards overlapped on desktop"
    assert layout["unstackedFields"] == [], f"Atlas fact labels and values collapsed inline: {layout['unstackedFields']}"
    assert int(layout["heroCopyScrollWidth"]) - int(layout["heroCopyClientWidth"]) <= 4
    assert int(layout["factsScrollWidth"]) - int(layout["factsClientWidth"]) <= 4

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_detail_header_uses_readable_fact_cards_in_compact_view(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    _atlas, _row, layout = _select_atlas_layout_stress_diagram(page)

    assert int(layout["factCount"]) == 6
    assert layout["factFields"][0] == "diagram-id"
    assert layout["controlsBelowFacts"], "Atlas controls should stay stacked under the fact cards in compact view"
    assert int(layout["heroUnusedWidth"]) <= 8
    assert not layout["headlineOverlap"], "Atlas title and fact cards overlapped in compact view"
    assert layout["unstackedFields"] == [], f"Atlas fact labels and values collapsed inline: {layout['unstackedFields']}"
    assert int(layout["heroScrollWidth"]) - int(layout["heroClientWidth"]) <= 8
    assert int(layout["factsScrollWidth"]) - int(layout["factsClientWidth"]) <= 4

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def _atlas_viewer_layout(atlas) -> dict[str, object]:  # noqa: ANN001
    atlas.locator("#viewerImage").evaluate(
        """node => new Promise((resolve) => {
          if (node.complete && node.naturalWidth > 0) {
            resolve(true);
            return;
          }
          node.addEventListener("load", () => resolve(true), { once: true });
        })"""
    )
    return atlas.locator("#viewerStage").evaluate(
        """(stage) => {
          const image = stage.querySelector("#viewerImage");
          const stageBox = stage.getBoundingClientRect();
          const imageBox = image ? image.getBoundingClientRect() : null;
          const style = window.getComputedStyle(stage);
          const overflow = imageBox ? {
            left: Math.max(0, stageBox.left - imageBox.left),
            top: Math.max(0, stageBox.top - imageBox.top),
            right: Math.max(0, imageBox.right - stageBox.right),
            bottom: Math.max(0, imageBox.bottom - stageBox.bottom),
          } : { left: 9999, top: 9999, right: 9999, bottom: 9999 };
          const margins = imageBox ? {
            left: imageBox.left - stageBox.left,
            top: imageBox.top - stageBox.top,
            right: stageBox.right - imageBox.right,
            bottom: stageBox.bottom - imageBox.bottom,
          } : { left: 0, top: 0, right: 0, bottom: 0 };
          return {
            loaded: Boolean(image && image.complete && image.naturalWidth > 0),
            backgroundImage: style.backgroundImage,
            backgroundColor: style.backgroundColor,
            overflow,
            margins,
          };
        }"""
    )


def test_atlas_viewer_uses_plain_white_stage_and_fits_diagram_without_clipping(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    _select_atlas_layout_stress_diagram(page)
    layout = _atlas_viewer_layout(atlas)
    overflow = layout["overflow"]
    margins = layout["margins"]

    assert layout["loaded"], "Atlas viewer diagram image did not load"
    assert layout["backgroundImage"] == "none"
    assert layout["backgroundColor"] == "rgb(255, 255, 255)"
    assert max(float(value) for value in overflow.values()) <= 4, f"diagram clipped by viewer stage: {overflow}"
    assert min(float(value) for value in margins.values()) >= 18, f"diagram fit lacks readable padding: {margins}"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def _radar_detail_layout(radar) -> dict[str, object]:  # noqa: ANN001
    return radar.locator("#detail .detail-header").evaluate(
        """(node) => {
            const kpisNode = node.querySelector(".kpis");
            const chipsNode = node.querySelector(".chips");
            const kpis = Array.from(node.querySelectorAll(".kpi")).map((kpi) => {
              const label = kpi.querySelector(".k");
              const value = kpi.querySelector(".v");
              const labelBox = label ? label.getBoundingClientRect() : null;
              const valueBox = value ? value.getBoundingClientRect() : null;
              return {
                label: String((label && label.textContent) || "").trim(),
                value: String((value && value.textContent) || "").trim(),
                stacked: Boolean(labelBox && valueBox && valueBox.top >= labelBox.bottom - 1),
              };
            });
            const idCard = node.querySelector('[data-kpi="workstream-id"]');
            const idValue = idCard ? idCard.querySelector(".v") : null;
            return {
              headerClientWidth: node.clientWidth,
              headerScrollWidth: node.scrollWidth,
              kpisClientWidth: kpisNode ? kpisNode.clientWidth : 0,
              kpisScrollWidth: kpisNode ? kpisNode.scrollWidth : 0,
              kpiCount: kpis.length,
              kpiLabels: kpis.map((kpi) => kpi.label),
              childOrder: Array.from(node.children || []).map((child) => String(child.className || child.tagName || "").trim()),
              kpisBeforeChips: Boolean(!kpisNode || !chipsNode || kpisNode.compareDocumentPosition(chipsNode) & Node.DOCUMENT_POSITION_FOLLOWING),
              workstreamIdValue: String((idValue && idValue.textContent) || "").trim(),
              unstackedKpis: kpis.filter((kpi) => !kpi.stacked).map((kpi) => kpi.label),
            };
        }"""
    )


def _select_radar_layout_stress_row(page):  # noqa: ANN001
    radar = page.frame_locator("#frame-radar")
    candidates = radar.locator("button[data-idea-id]").evaluate_all(
        """nodes => nodes
          .map((node) => ({
            idea: String(node.getAttribute("data-idea-id") || "").trim(),
            title: String((node.querySelector(".row-title") || {}).textContent || "").trim(),
            titleLength: String((node.querySelector(".row-title") || {}).textContent || "").trim().length,
          }))
          .filter((row) => row.idea && row.title)
          .sort((left, right) => right.titleLength - left.titleLength)
        """
    )
    assert candidates, "expected Radar rows for layout audit"

    for row in candidates[:12]:
        radar.locator(f'button[data-idea-id="{row["idea"]}"]').click()
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=str(row["idea"]))
        radar.locator("#detail .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)
        layout = _radar_detail_layout(radar)
        if int(layout["kpiCount"]) >= 9:
            return radar, row, layout

    raise AssertionError("expected a Radar detail with the full KPI grid for layout audit")


def test_radar_detail_header_promotes_workstream_id_into_kpi_grid(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    _radar, row, layout = _select_radar_layout_stress_row(page)

    assert "Workstream ID" in layout["kpiLabels"]
    assert layout["kpiLabels"][0] == "Workstream ID"
    assert "kpis" in layout["childOrder"]
    assert layout["childOrder"].index("kpis") < layout["childOrder"].index("chips")
    assert layout["kpisBeforeChips"], "Radar KPI grid should render before the secondary chip row"
    assert layout["workstreamIdValue"] == row["idea"]
    assert layout["unstackedKpis"] == [], f"Radar KPI labels and values collapsed inline: {layout['unstackedKpis']}"
    assert int(layout["kpisScrollWidth"]) - int(layout["kpisClientWidth"]) <= 4

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_detail_header_keeps_kpi_grid_readable_in_compact_view(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    _radar, row, layout = _select_radar_layout_stress_row(page)

    assert "Workstream ID" in layout["kpiLabels"]
    assert layout["kpiLabels"][0] == "Workstream ID"
    assert "kpis" in layout["childOrder"]
    assert layout["childOrder"].index("kpis") < layout["childOrder"].index("chips")
    assert layout["kpisBeforeChips"], "Radar KPI grid should stay ahead of the secondary chip row in compact view"
    assert layout["workstreamIdValue"] == row["idea"]
    assert layout["unstackedKpis"] == [], f"Radar KPI labels and values collapsed inline: {layout['unstackedKpis']}"
    assert int(layout["headerScrollWidth"]) - int(layout["headerClientWidth"]) <= 16
    assert int(layout["kpisScrollWidth"]) - int(layout["kpisClientWidth"]) <= 4

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def _workstream_button_style(locator, selector: str) -> dict[str, str]:  # noqa: ANN001
    return locator.locator(selector).first.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              color: style.color,
              backgroundColor: style.backgroundColor,
              borderColor: style.borderColor,
              borderRadius: style.borderRadius,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
              paddingBottom: style.paddingBottom,
              paddingLeft: style.paddingLeft,
            };
        }"""
    )


def _synthetic_workstream_button_style(locator, host_selector: str, class_name: str) -> dict[str, str]:  # noqa: ANN001
    return locator.locator(host_selector).first.evaluate(
        """(node, className) => {
            const anchor = node.ownerDocument.createElement("a");
            anchor.href = "#";
            anchor.className = className;
            anchor.textContent = "B-000";
            node.appendChild(anchor);
            const style = window.getComputedStyle(anchor);
            const result = {
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              color: style.color,
              backgroundColor: style.backgroundColor,
              borderColor: style.borderColor,
              borderRadius: style.borderRadius,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
              paddingBottom: style.paddingBottom,
              paddingLeft: style.paddingLeft,
            };
            anchor.remove();
            return result;
        }""",
        class_name,
    )


def _deep_link_button_style(locator, selector: str) -> dict[str, str]:  # noqa: ANN001
    return locator.locator(selector).first.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
              paddingBottom: style.paddingBottom,
              paddingLeft: style.paddingLeft,
              borderRadius: style.borderRadius,
            };
        }"""
    )


def _synthetic_anchor_button_style(locator, host_selector: str, class_name: str) -> dict[str, str]:  # noqa: ANN001
    return locator.locator(host_selector).first.evaluate(
        """(node, className) => {
            const anchor = node.ownerDocument.createElement("a");
            anchor.href = "#";
            anchor.className = className;
            anchor.textContent = "Registry";
            node.appendChild(anchor);
            const style = window.getComputedStyle(anchor);
            const result = {
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
              paddingBottom: style.paddingBottom,
              paddingLeft: style.paddingLeft,
              borderRadius: style.borderRadius,
            };
            anchor.remove();
            return result;
        }""",
        class_name,
    )


def _governance_kpi_style(locator, card_selector: str, label_selector: str, value_selector: str) -> dict[str, str]:  # noqa: ANN001
    return locator.locator(card_selector).first.evaluate(
        """(node, selectors) => {
            const label = node.querySelector(selectors.label);
            const value = node.querySelector(selectors.value);
            const cardStyle = window.getComputedStyle(node);
            const labelStyle = label ? window.getComputedStyle(label) : null;
            const valueStyle = value ? window.getComputedStyle(value) : null;
            return {
              cardPaddingTop: cardStyle.paddingTop,
              cardPaddingRight: cardStyle.paddingRight,
              cardPaddingBottom: cardStyle.paddingBottom,
              cardPaddingLeft: cardStyle.paddingLeft,
              cardBorderRadius: cardStyle.borderRadius,
              cardDisplay: cardStyle.display,
              labelFontSize: labelStyle ? labelStyle.fontSize : "",
              labelFontWeight: labelStyle ? labelStyle.fontWeight : "",
              labelTextTransform: labelStyle ? labelStyle.textTransform : "",
              valueFontSize: valueStyle ? valueStyle.fontSize : "",
              valueFontWeight: valueStyle ? valueStyle.fontWeight : "",
              valueMarginTop: valueStyle ? valueStyle.marginTop : "",
            };
        }""",
        {"label": label_selector, "value": value_selector},
    )


def _select_radar_workstream_chip_for_style_audit(page):  # noqa: ANN001
    radar = page.frame_locator("#frame-radar")
    preferred_idea_id = "B-048"
    preferred_button = radar.locator(f'button[data-idea-id="{preferred_idea_id}"]').first
    if preferred_button.count():
        preferred_button.click()
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=preferred_idea_id)
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=preferred_idea_id).wait_for(timeout=15000)
        if _open_radar_topology_relations_for_style_audit(radar):
            chips = radar.locator("#detail button.execution-wave-chip-link, #detail button.entity-id-chip")
            if chips.count():
                chips.first.wait_for(timeout=15000)
                return radar

    radar, _idea_id = _select_radar_workstream_with_detail_selector(
        page,
        detail_selector="details.topology-relations-panel",
        failure_message="expected a Radar detail with a topology relations panel for workstream chip style audit",
        selector_timeout=15000,
    )
    assert _open_radar_topology_relations_for_style_audit(radar), "expected a Radar topology relations panel"
    chips = radar.locator("#detail button.execution-wave-chip-link, #detail button.entity-id-chip")
    chips.first.wait_for(timeout=15000)
    assert chips.count() > 0, "expected a Radar detail with at least one rendered workstream chip"
    return radar


def _open_radar_topology_relations_for_style_audit(radar) -> bool:  # noqa: ANN001
    panel = radar.locator("#detail details.topology-relations-panel").first
    if not panel.count():
        return False
    panel.wait_for(timeout=15000)
    if panel.get_attribute("open") is None:
        panel.evaluate("node => { node.open = true; }")
    panel.locator(".topology-relations").wait_for(timeout=15000)
    return True


def _select_radar_deep_link_chip_for_style_audit(page):  # noqa: ANN001
    radar = page.frame_locator("#frame-radar")
    row_buttons = radar.locator("button[data-idea-id]")
    count = row_buttons.count()
    for index in range(count):
        button = row_buttons.nth(index)
        idea_id = str(button.get_attribute("data-idea-id") or "").strip()
        if not idea_id:
            continue
        button.click()
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=idea_id)
        radar.locator("#detail .detail-title").wait_for(timeout=15000)
        if not _open_radar_topology_relations_for_style_audit(radar):
            continue
        links = radar.locator("#detail a.chip-topology-diagram, #detail a.chip-registry-component")
        if links.count():
            return radar
    raise AssertionError("expected a Radar detail with at least one deep-link chip")


def _select_atlas_workstream_pill_for_style_audit(page):  # noqa: ANN001
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    _select_atlas_layout_stress_diagram(page)
    pill_locator = atlas.locator(
        "#activeWorkstreamLinks a.workstream-pill-link, "
        "#ownerWorkstreamLinks a.workstream-pill-link, "
        "#historicalWorkstreamLinks a.workstream-pill-link"
    )
    assert pill_locator.count() > 0, "expected Atlas workstream pills for style audit"
    return atlas


def _select_compass_deep_link_chip_for_style_audit(page):  # noqa: ANN001
    compass = page.frame_locator("#frame-compass")
    rows = compass.locator("tr.ws-summary-row.ws-row-title")
    count = rows.count()
    for index in range(count):
        row = rows.nth(index)
        workstream = str(row.get_attribute("data-ws-id") or "").strip()
        if not workstream:
            continue
        row.evaluate("node => node.click()")
        detail = compass.locator(f'tr.ws-detail-row.is-open[data-ws-detail="{workstream}"]')
        detail.wait_for(timeout=15000)
        links = detail.locator("a.chip-link")
        if links.count():
            return detail
    raise AssertionError("expected a Compass workstream detail with at least one deep-link chip")


def _select_registry_deep_link_chip_for_style_audit(page):  # noqa: ANN001
    registry, _component_id = _select_registry_component_with_detail_selector(
        page,
        detail_selector="a.detail-action-chip",
        failure_message="expected a Registry detail with at least one deep-link chip",
    )
    return registry


def _load_registry_payload(path: Path) -> dict[str, object]:
    payload_text = path.read_text(encoding="utf-8")
    match = re.search(r"=\s*(\{.*\})\s*;\s*$", payload_text, flags=re.S)
    assert match is not None
    payload = json.loads(match.group(1))
    assert isinstance(payload, dict)
    return payload


def _write_registry_payload(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        'window["__ODYLITH_REGISTRY_DATA__"] = ' + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def test_registry_compacts_sentence_shaped_component_names_without_losing_identity(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    payload_path = fixture_root / "odylith" / "registry" / "registry-payload.v1.js"
    payload = _load_registry_payload(payload_path)
    components = payload.get("components")
    assert isinstance(components, list)
    long_name = "Evidence Review That Explains the Recommended Option and Orders the Alternatives Service"
    component_id = "evidence-review-that-explains-the-recommended-option-and-orders-the-alternatives"
    long_source = "src/generated/evidence_review_that_explains_the_recommended_option_and_orders_the_alternatives"
    components.append(
        {
            "component_id": component_id,
            "name": long_name,
            "kind": "service",
            "category": "governance_engine",
            "qualification": "candidate",
            "owner": "governance",
            "status": "planned",
            "what_it_is": (
                f"{long_name} is planned as a service boundary. "
                "It owns review state and prevents stale recommendation evidence from looking current. "
                f"Initial source boundary: {long_source}"
            ),
            "why_tracked": "Tracked from user-stated intent as a named ownership boundary.",
            "product_layer": "intelligence",
            "timeline_count": 1,
            "workstreams": [],
            "diagrams": [],
            "aliases": [],
            "sources": [],
            "path_prefixes": [long_source],
            "subcomponents": [],
            "forensic_coverage": {
                "status": "forensic_coverage_present",
                "timeline_event_count": 1,
                "explicit_event_count": 1,
                "recent_path_match_count": 0,
                "mapped_workstream_evidence_count": 1,
                "spec_history_event_count": 0,
            },
            "spec_ref": (
                "odylith/registry/source/components/"
                "evidence-review-that-explains-the-recommended-option-and-orders-the-alternatives/CURRENT_SPEC.md"
            ),
            "spec_markdown": "# Evidence Review Service\n\nCurrent spec placeholder.\n",
            "spec_feature_history": [],
            "spec_runbooks": [],
            "spec_developer_docs": [],
            "timeline": [],
        }
    )
    _write_registry_payload(payload_path, payload)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
                assert response is not None and response.ok

                registry = page.frame_locator("#frame-registry")
                registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
                registry.locator("#search").fill(component_id)
                registry.locator(f'button[data-component="{component_id}"]').wait_for(timeout=15000)
                registry.locator(f'button[data-component="{component_id}"]').click()
                _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
                registry.locator("#detail .component-name", has_text="Evidence Review Service").wait_for(timeout=15000)

                layout = registry.locator("body").evaluate(
                    """(body) => {
                      const title = body.querySelector("#detail .component-name");
                      const fullName = body.querySelector("#detail .component-full-name");
                      const idLine = body.querySelector("#detail .component-id-line");
                      const cardTitle = body.querySelector(".component-card-title");
                      const cardButton = body.querySelector(`button[data-component="${CSS.escape("evidence-review-that-explains-the-recommended-option-and-orders-the-alternatives")}"]`);
                      const summary = body.querySelector("#detail .summary-strip");
                      const sourceChip = body.querySelector("#detail .summary-artifact-row .artifact-compact");
                      const html = body.ownerDocument.documentElement;
                      const rowBox = cardButton ? cardButton.getBoundingClientRect() : { height: 0 };
                      return {
                        title: String(title && title.textContent || "").trim(),
                        fullName: String(fullName && fullName.textContent || "").trim(),
                        idLine: String(idLine && idLine.textContent || "").trim(),
                        cardTitle: String(cardTitle && cardTitle.textContent || "").trim(),
                        cardTitleHeight: cardTitle ? Number(cardTitle.getBoundingClientRect().height.toFixed(2)) : 0,
                        rowHeight: Number(rowBox.height.toFixed(2)),
                        summaryText: String(summary && summary.textContent || "").trim(),
                        sourceChipText: String(sourceChip && sourceChip.textContent || "").trim(),
                        sourceChipTooltip: String(sourceChip && sourceChip.getAttribute("data-tooltip") || "").trim(),
                        documentOverflow: html.scrollWidth > html.clientWidth + 4,
                        bodyOverflow: body.scrollWidth > body.clientWidth + 4,
                        detailOverflow: Boolean(summary && summary.scrollWidth > summary.clientWidth + 4),
                      };
                    }"""
                )

                assert layout["title"] == "Evidence Review Service"
                assert layout["cardTitle"] == "Evidence Review Service"
                assert layout["fullName"] == long_name
                assert layout["idLine"] == component_id
                assert long_name not in str(layout["summaryText"])
                assert long_source not in str(layout["summaryText"])
                assert layout["sourceChipText"] == "Source boundary"
                assert layout["sourceChipTooltip"] == long_source
                assert float(layout["cardTitleHeight"]) <= 40
                assert float(layout["rowHeight"]) <= 112
                assert not layout["documentOverflow"], layout
                assert not layout["bodyOverflow"], layout
                assert not layout["detailOverflow"], layout

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def _select_registry_forensic_digest_stress_component(page):  # noqa: ANN001
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    registry.locator('button[data-component="odylith"]').click()
    registry.locator('button[data-component="odylith"].active').wait_for(timeout=15000)
    registry.locator("#timeline .forensic-digest").wait_for(timeout=15000)
    return registry


def _registry_forensic_digest_layout(registry) -> dict[str, object]:  # noqa: ANN001
    return registry.locator("#timeline").evaluate(
        """(node) => {
            const documentElement = node.ownerDocument.documentElement;
            const timelineCount = String(node.ownerDocument.querySelector("#timelineCount")?.textContent || "");
            const rows = Array.from(node.querySelectorAll(".forensic-token-row")).map((row) => {
              const text = row.textContent || "";
              const workstreamOverflow = Number((text.match(/\\+(\\d+) workstreams/) || [null, "0"])[1]);
              return {
                workstreams: row.querySelectorAll(".forensic-workstream-chip").length,
                artifacts: row.querySelectorAll(":scope > .artifact").length,
                hiddenArtifacts: row.querySelectorAll(".forensic-artifact-disclosure-panel .artifact").length,
                workstreamOverflow,
                text,
              };
            });
            const overflowLabels = rows.flatMap((row) => row.text.match(/\\+\\d+ (?:workstreams|artifacts)/g) || []);
            const visibleWorkstreamCounts = rows.map((row) => row.workstreams);
            const visibleArtifactCounts = rows.map((row) => row.artifacts);
            const visibleNodeOverflow = Array.from(
              node.querySelectorAll(".forensic-summary, .artifact, .forensic-row-top, .forensic-token-row")
            ).some((child) => child.scrollWidth > child.clientWidth + 1);
            return {
              timelineText: node.textContent || "",
              eventCount: Number((timelineCount.match(/\\d+/) || ["0"])[0]),
              rawDetails: node.querySelectorAll(".forensic-raw-log, .forensic-raw-events").length,
              artifactDisclosureCount: node.querySelectorAll(".forensic-artifact-disclosure").length,
              hiddenArtifactCount: Math.max(0, ...rows.map((row) => row.hiddenArtifacts)),
              maxVisibleWorkstreams: Math.max(0, ...visibleWorkstreamCounts),
              maxVisibleArtifacts: Math.max(0, ...visibleArtifactCounts),
              maxLinkedWorkstreams: Math.max(0, ...rows.map((row) => row.workstreams + row.workstreamOverflow)),
              overflowLabels,
              documentOverflow: documentElement.scrollWidth > documentElement.clientWidth + 1,
              visibleNodeOverflow,
            };
        }"""
    )


def _assert_registry_forensic_digest_keeps_default_view_compact(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=registry&component=odylith", wait_until="domcontentloaded")
    assert response is not None and response.ok

    registry = _select_registry_forensic_digest_stress_component(page)
    registry.locator("#chronology-anchor").scroll_into_view_if_needed()
    layout = _registry_forensic_digest_layout(registry)

    assert int(layout["eventCount"]) >= 9, "expected a high-volume evidence component for the digest audit"
    assert int(layout["maxLinkedWorkstreams"]) >= 40, "expected many linked workstreams behind digest overflow"
    assert int(layout["rawDetails"]) == 0, "raw event logs should not be exposed in the Registry UI"
    assert "Raw event log" not in str(layout["timelineText"])
    assert "No scope" not in str(layout["timelineText"])
    assert "No artifacts" not in str(layout["timelineText"])
    assert int(layout["maxVisibleWorkstreams"]) <= 4
    assert int(layout["maxVisibleArtifacts"]) <= 2
    assert int(layout["artifactDisclosureCount"]) > 0, "artifact overflow should be expandable"
    assert int(layout["hiddenArtifactCount"]) > 0, "artifact disclosure should retain hidden artifact links"
    assert layout["overflowLabels"], "high-volume evidence should render compact overflow labels"
    assert layout["documentOverflow"] is False
    assert layout["visibleNodeOverflow"] is False

    workstream_style = _workstream_button_style(registry, "#timeline .forensic-workstream-chip")
    assert workstream_style["fontSize"] == "12px"
    assert workstream_style["fontWeight"] == "500"
    assert workstream_style["paddingTop"] == "1px"
    assert workstream_style["paddingRight"] == "8px"
    assert workstream_style["paddingBottom"] == "1px"
    assert workstream_style["paddingLeft"] == "8px"

    artifact_style = _deep_link_button_style(registry, "#timeline .artifact")
    assert artifact_style["fontSize"] == "11px"
    assert artifact_style["fontWeight"] == "700"
    assert artifact_style["paddingTop"] == "4px"
    assert artifact_style["paddingRight"] == "12px"
    assert artifact_style["paddingBottom"] == "4px"
    assert artifact_style["paddingLeft"] == "12px"
    assert artifact_style["borderRadius"] == "999px"

    artifact_disclosure_style = _deep_link_button_style(registry, "#timeline .forensic-artifact-overflow-summary")
    assert artifact_disclosure_style["fontSize"] == "11px"
    assert artifact_disclosure_style["fontWeight"] == "700"
    assert artifact_disclosure_style["paddingTop"] == "4px"
    assert artifact_disclosure_style["paddingRight"] == "12px"
    assert artifact_disclosure_style["paddingBottom"] == "4px"
    assert artifact_disclosure_style["paddingLeft"] == "12px"
    assert artifact_disclosure_style["borderRadius"] == "999px"

    artifact_disclosures = registry.locator("#timeline .forensic-artifact-disclosure")
    disclosure_index = artifact_disclosures.evaluate_all(
        """(nodes) => {
            const index = nodes.findIndex((node) => node.querySelector(
                '.forensic-artifact-disclosure-panel .artifact'
            ));
            if (index < 0) return index;
            for (let parent = nodes[index].parentElement; parent; parent = parent.parentElement) {
                if (parent.tagName === 'DETAILS') parent.open = true;
            }
            return index;
        }"""
    )
    assert disclosure_index >= 0
    artifact_disclosure = artifact_disclosures.nth(disclosure_index)
    artifact_disclosure.scroll_into_view_if_needed()
    hidden_artifacts = artifact_disclosure.locator(".forensic-artifact-disclosure-panel .artifact")
    assert hidden_artifacts.count() > 0
    assert hidden_artifacts.first.is_visible() is False
    artifact_disclosure.locator("summary").click()
    hidden_artifacts.first.wait_for(state="visible", timeout=15000)
    assert artifact_disclosure.evaluate("node => node.open") is True
    expanded_layout = _registry_forensic_digest_layout(registry)
    assert int(expanded_layout["maxVisibleArtifacts"]) <= 2
    assert expanded_layout["documentOverflow"] is False
    assert expanded_layout["visibleNodeOverflow"] is False

    coverage_style = _governance_kpi_style(
        registry,
        "#timeline .forensic-stat",
        ".forensic-stat-label",
        ".forensic-stat-value",
    )
    assert coverage_style["cardPaddingTop"] == "14px"
    assert coverage_style["cardPaddingRight"] == "16px"
    assert coverage_style["cardPaddingBottom"] == "14px"
    assert coverage_style["cardPaddingLeft"] == "16px"
    assert coverage_style["cardBorderRadius"] == "0px"
    assert coverage_style["labelFontSize"] == "10px"
    assert coverage_style["labelTextTransform"] == "uppercase"
    assert coverage_style["valueFontSize"] == "15px"
    assert coverage_style["valueFontWeight"] == "800"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_registry_forensic_digest_keeps_default_view_compact_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_registry_forensic_digest_keeps_default_view_compact(*browser_context)


def test_registry_forensic_digest_keeps_default_view_compact_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_registry_forensic_digest_keeps_default_view_compact(*compact_browser_context)


def _select_casebook_deep_link_chip_for_style_audit(page):  # noqa: ANN001
    casebook, _bug_route = _select_casebook_bug_with_detail_selector(
        page,
        detail_selector="a.action-chip",
        failure_message="expected a Casebook detail with at least one deep-link chip",
    )
    return casebook


def _assert_shared_workstream_buttons_keep_compact_style_contract(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    release_summary = compass.locator("#release-groups-host summary").first
    if release_summary.count():
        release_summary.evaluate(
            """(node) => {
                const details = node.closest("details");
                if (details && !details.open) node.click();
            }"""
        )
    compass_current_selector = "a.ws-id-btn, a.ws-covered-id-btn"
    if compass.locator(compass_current_selector).count():
        compass_current_style = _workstream_button_style(compass, compass_current_selector)
    else:
        compass_current_style = _synthetic_workstream_button_style(compass, "body", "ws-id-btn")
    compass_release_link = compass.locator("#release-groups-host a.execution-wave-chip-link").first
    if compass_release_link.count() and compass_release_link.is_visible():
        compass_release_style = _workstream_button_style(compass, "#release-groups-host a.execution-wave-chip-link")
    else:
        compass_release_style = _synthetic_workstream_button_style(
            compass,
            "body",
            "chip chip-link execution-wave-chip-link",
        )

    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok
    atlas = _select_atlas_workstream_pill_for_style_audit(page)
    atlas_style = _workstream_button_style(
        atlas,
        "#activeWorkstreamLinks a.workstream-pill-link, "
        "#ownerWorkstreamLinks a.workstream-pill-link, "
        "#historicalWorkstreamLinks a.workstream-pill-link",
    )

    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = _select_radar_workstream_chip_for_style_audit(page)
    radar_style = _workstream_button_style(
        radar,
        "#detail button.execution-wave-chip-link, #detail button.entity-id-chip",
    )

    response = page.goto(base_url + "/odylith/index.html?tab=registry&component=odylith", wait_until="domcontentloaded")
    assert response is not None and response.ok
    registry = _select_registry_forensic_digest_stress_component(page)
    registry_style = _workstream_button_style(registry, "#timeline .forensic-workstream-chip")

    for style in (compass_current_style, compass_release_style, atlas_style, radar_style, registry_style):
        assert style["fontSize"] == "12px"
        assert style["fontWeight"] == "500"
        assert style["paddingTop"] == "1px"
        assert style["paddingRight"] == "8px"
        assert style["paddingBottom"] == "1px"
        assert style["paddingLeft"] == "8px"

    for key in ("color", "backgroundColor", "borderColor", "borderRadius"):
        assert registry_style[key] == compass_current_style[key]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shared_workstream_buttons_keep_compact_style_contract_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_shared_workstream_buttons_keep_compact_style_contract(*browser_context)


def test_shared_workstream_buttons_keep_compact_style_contract_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_shared_workstream_buttons_keep_compact_style_contract(*compact_browser_context)


def _assert_shared_deep_link_buttons_keep_style_contract(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass_style = _synthetic_anchor_button_style(compass, "body", "chip chip-link")

    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_style = _synthetic_anchor_button_style(radar, "body", "chip chip-link chip-registry-component")

    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
    assert response is not None and response.ok
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    registry_style = _synthetic_anchor_button_style(registry, "body", "detail-action-chip")

    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook_style = _synthetic_anchor_button_style(casebook, "body", "action-chip")

    for style in (compass_style, radar_style, registry_style, casebook_style):
        assert style["fontSize"] == "11px"
        assert style["fontWeight"] == "700"
        assert style["paddingTop"] == "4px"
        assert style["paddingRight"] == "12px"
        assert style["paddingBottom"] == "4px"
        assert style["paddingLeft"] == "12px"
        assert style["borderRadius"] == "999px"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shared_deep_link_buttons_keep_style_contract_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_shared_deep_link_buttons_keep_style_contract(*browser_context)


def test_shared_deep_link_buttons_keep_style_contract_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_shared_deep_link_buttons_keep_style_contract(*compact_browser_context)


def _assert_shared_governance_kpi_cards_keep_compact_style_contract(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("#kpi-grid .stat").first.wait_for(timeout=15000)
    compass_style = _governance_kpi_style(compass, "#kpi-grid .stat", ".kpi-label", ".kpi-value")

    page.locator("#tab-radar").click()
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator(".stats .stat").first.wait_for(timeout=15000)
    radar_style = _governance_kpi_style(radar, ".stats .stat", ".label", ".value")
    radar_release_style = _governance_kpi_style(radar, ".stats .stat.stat-release-only", ".label", ".value")

    page.locator("#tab-registry").click()
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Registry").wait_for(timeout=15000)
    registry.locator(".kpis .kpi-card").first.wait_for(timeout=15000)
    registry_style = _governance_kpi_style(registry, ".kpis .kpi-card", ".kpi-label", ".kpi-value")

    page.locator("#tab-casebook").click()
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator(".kpis .kpi-card").first.wait_for(timeout=15000)
    casebook_style = _governance_kpi_style(casebook, ".kpis .kpi-card", ".kpi-label", ".kpi-value")

    for style in (compass_style, radar_style, radar_release_style, registry_style, casebook_style):
        assert style["cardDisplay"] == "grid"
        assert style["cardPaddingTop"] == "10px"
        assert style["cardPaddingRight"] == "12px"
        assert style["cardPaddingBottom"] == "10px"
        assert style["cardPaddingLeft"] == "12px"
        assert style["cardBorderRadius"] == "12px"
        assert style["labelFontSize"] == "12px"
        assert style["labelFontWeight"] == "400"
        assert style["labelTextTransform"] == "uppercase"
        assert style["valueFontSize"] == "23px"
        assert style["valueFontWeight"] == "700"
        assert style["valueMarginTop"] == "4px"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shared_governance_kpi_cards_keep_compact_style_contract_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_shared_governance_kpi_cards_keep_compact_style_contract(*browser_context)


def test_shared_governance_kpi_cards_keep_compact_style_contract_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_shared_governance_kpi_cards_keep_compact_style_contract(*compact_browser_context)


def _assert_compass_release_member_title_stays_on_second_row(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    release_section = compass.locator("#release-groups details.execution-wave-section").first
    release_section.wait_for(timeout=15000)
    if release_section.get_attribute("open") is None:
        release_section.locator("summary").first.click()
    release_section.locator(".execution-wave-panel").first.wait_for(timeout=15000)
    card = compass.locator("#release-groups .execution-wave-card").first
    card.wait_for(timeout=15000)
    layout = card.evaluate(
        """(node) => {
            const chips = node.querySelector(".execution-wave-member-title-chips");
            const title = node.querySelector(".execution-wave-title");
            const chipsBox = chips ? chips.getBoundingClientRect() : null;
            const titleBox = title ? title.getBoundingClientRect() : null;
            return {
              chipsBottom: chipsBox ? chipsBox.bottom : 0,
              titleTop: titleBox ? titleBox.top : 0,
            };
        }"""
    )

    assert float(layout["titleTop"]) >= float(layout["chipsBottom"]) - 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_release_member_title_stays_on_second_row_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_member_title_stays_on_second_row(*browser_context)


def test_compass_release_member_title_stays_on_second_row_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_member_title_stays_on_second_row(*compact_browser_context)


def _assert_compass_release_targets_keep_single_column_board_layout(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    release_section = compass.locator("#release-groups details.execution-wave-section").first
    release_section.wait_for(timeout=15000)
    if release_section.get_attribute("open") is None:
        release_section.locator("summary").first.click()
    release_section.locator(".execution-wave-panel").first.wait_for(timeout=15000)
    board = compass.locator("#release-groups .execution-wave-board").first
    board.wait_for(timeout=15000)
    layout = board.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            const panels = Array.from(node.querySelectorAll(":scope > .execution-wave-panel")).map((panel) => {
              const box = panel.getBoundingClientRect();
              return { top: box.top, bottom: box.bottom };
            });
            return {
              display: style.display,
              gridTemplateColumns: style.gridTemplateColumns,
              gridColumnCount: String(style.gridTemplateColumns || "none")
                .split(/\\s+/)
                .filter(Boolean)
                .length,
              panels,
            };
        }"""
    )

    assert layout["display"] == "grid"
    assert int(layout["gridColumnCount"]) == 1
    if len(layout["panels"]) >= 2:
        assert layout["panels"][1]["top"] >= layout["panels"][0]["bottom"] - 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_release_targets_keep_single_column_board_layout_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_targets_keep_single_column_board_layout(*browser_context)


def test_compass_release_targets_keep_single_column_board_layout_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_targets_keep_single_column_board_layout(*compact_browser_context)


def _assert_compass_program_and_release_cards_keep_distinct_surface_tints(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    program_section = compass.locator("#execution-waves-host .execution-wave-section").first
    release_section = compass.locator("#release-groups-host .execution-wave-section").first
    program_section.wait_for(timeout=15000)
    release_section.wait_for(timeout=15000)

    program_style = program_section.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderTopColor: style.borderTopColor,
              backgroundImage: style.backgroundImage,
            };
        }"""
    )
    release_style = release_section.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderTopColor: style.borderTopColor,
              backgroundImage: style.backgroundImage,
            };
        }"""
    )

    assert program_style["borderTopColor"] != release_style["borderTopColor"]
    assert program_style["backgroundImage"] != release_style["backgroundImage"]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_program_and_release_cards_keep_distinct_surface_tints_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_and_release_cards_keep_distinct_surface_tints(*browser_context)


def test_compass_program_and_release_cards_keep_distinct_surface_tints_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_and_release_cards_keep_distinct_surface_tints(*compact_browser_context)


def _assert_compass_default_hides_completed_only_programs(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("#release-groups-host h2", has_text="Release Targets").wait_for(timeout=15000)

    assert compass.locator("#execution-waves-host > .card.execution-waves-card").count() == 0
    assert compass.locator("#execution-waves-host", has_text="Completed Program History").count() == 0
    assert compass.locator("#execution-waves-host", has_text="Archived program lanes").count() == 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_default_hides_completed_only_programs_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_default_hides_completed_only_programs(*browser_context)


def test_compass_default_hides_completed_only_programs_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_default_hides_completed_only_programs(*compact_browser_context)


def _assert_compass_programs_render_release_like_inner_card_chrome(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    section = compass.locator("#execution-waves-host .execution-wave-section").first
    release_section = compass.locator("#release-groups-host .execution-wave-section").first
    section.wait_for(timeout=15000)
    release_section.wait_for(timeout=15000)

    style = section.evaluate(
        """(node) => {
            const sectionStyle = window.getComputedStyle(node);
            const summary = node.querySelector("summary");
            const summaryStyle = summary ? window.getComputedStyle(summary) : null;
            return {
              flatClass: node.classList.contains("execution-wave-section-flat"),
              programCardClass: node.classList.contains("execution-wave-section-program-card"),
              borderTopWidth: sectionStyle.borderTopWidth,
              backgroundImage: sectionStyle.backgroundImage,
              borderRadius: sectionStyle.borderRadius,
              summaryPaddingLeft: summaryStyle ? summaryStyle.paddingLeft : "",
              summaryPaddingRight: summaryStyle ? summaryStyle.paddingRight : "",
            };
        }"""
    )
    release_style = release_section.evaluate(
        """(node) => {
            const sectionStyle = window.getComputedStyle(node);
            return {
              borderTopWidth: sectionStyle.borderTopWidth,
              borderRadius: sectionStyle.borderRadius,
            };
        }"""
    )

    assert style["flatClass"] is False
    assert style["programCardClass"] is True
    assert style["borderTopWidth"] == release_style["borderTopWidth"] == "1px"
    assert style["backgroundImage"] != "none"
    assert style["borderRadius"] == release_style["borderRadius"]
    assert style["borderRadius"] != "0px"
    assert style["summaryPaddingLeft"] != "0px"
    assert style["summaryPaddingRight"] != "0px"
    assert section.locator(".execution-wave-focus").count() == 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_programs_render_release_like_inner_card_chrome_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_programs_render_release_like_inner_card_chrome(*browser_context)


def test_compass_programs_render_release_like_inner_card_chrome_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_programs_render_release_like_inner_card_chrome(*compact_browser_context)


def _assert_compass_wave_dependency_labels_stay_inside_group_panels(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    section = compass.locator("#execution-waves-host .execution-wave-section").first
    section.wait_for(timeout=15000)

    layout = section.evaluate(
        """(node) => {
            node.setAttribute("open", "");
            Array.from(node.querySelectorAll(".execution-wave-card")).forEach((card) => card.setAttribute("open", ""));
            const rows = [];
            Array.from(node.querySelectorAll(".execution-wave-panel")).forEach((panel) => {
              const groupLabel = String((panel.querySelector(".execution-wave-group-label") || {}).textContent || "").trim().toLowerCase();
              if (groupLabel !== "depends on") return;
              const body = panel.querySelector(".execution-wave-group-body");
              if (!body) return;
              const bodyBox = body.getBoundingClientRect();
              const panelBox = panel.getBoundingClientRect();
              Array.from(body.querySelectorAll(".label.execution-wave-label")).forEach((chip) => {
                const chipBox = chip.getBoundingClientRect();
                const style = window.getComputedStyle(chip);
                const text = String(chip.textContent || "").trim();
                rows.push({
                  text,
                  textLength: text.length,
                  whiteSpace: style.whiteSpace,
                  lineHeight: style.lineHeight,
                  panelLeft: panelBox.left,
                  panelRight: panelBox.right,
                  chipLeft: chipBox.left,
                  chipRight: chipBox.right,
                  chipHeight: chipBox.height,
                  bodyClientWidth: body.clientWidth,
                  bodyScrollWidth: body.scrollWidth,
                });
              });
            });
            return rows;
        }"""
    )

    long_labels = [row for row in layout if int(row["textLength"]) >= 24]
    assert long_labels, "expected at least one long dependency wave label in the Compass fixture"
    for row in long_labels:
        assert row["whiteSpace"] != "nowrap"
        assert float(row["chipLeft"]) >= float(row["panelLeft"]) - 1
        assert float(row["chipRight"]) <= float(row["panelRight"]) + 1
        assert int(row["bodyScrollWidth"]) - int(row["bodyClientWidth"]) <= 2

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_wave_dependency_labels_stay_inside_group_panels_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_wave_dependency_labels_stay_inside_group_panels(*browser_context)


def test_compass_wave_dependency_labels_stay_inside_group_panels_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_wave_dependency_labels_stay_inside_group_panels(*compact_browser_context)


def _assert_compass_program_box_does_not_highlight_active_inner_wave(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    section = compass.locator("#execution-waves-host .execution-wave-section").first
    section.wait_for(timeout=15000)

    if section.get_attribute("open") is None:
        section.locator("> summary").first.click()

    first_wave_card = section.locator(".execution-wave-card").first
    first_wave_card.wait_for(timeout=15000)
    initial_style = section.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            const openWaveCount = node.querySelectorAll(".execution-wave-card[open]").length;
            return {
              backgroundImage: style.backgroundImage,
              boxShadow: style.boxShadow,
              openWaveCount,
            };
        }"""
    )

    assert initial_style["openWaveCount"] == 0
    assert initial_style["boxShadow"] != "none"
    assert initial_style["backgroundImage"] != "none"

    first_wave_card.locator("> summary").first.click()

    expanded_style = section.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            const openWaveCount = node.querySelectorAll(".execution-wave-card[open]").length;
            return {
              backgroundImage: style.backgroundImage,
              boxShadow: style.boxShadow,
              openWaveCount,
            };
        }"""
    )

    assert expanded_style["openWaveCount"] >= 1
    assert expanded_style["boxShadow"] == initial_style["boxShadow"]
    assert expanded_style["backgroundImage"] == initial_style["backgroundImage"]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_program_box_does_not_highlight_active_inner_wave_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_box_does_not_highlight_active_inner_wave(*browser_context)


def test_compass_program_box_does_not_highlight_active_inner_wave_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_box_does_not_highlight_active_inner_wave(*compact_browser_context)


def _assert_compass_program_focus_does_not_repeat_outer_program_chip(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    section = compass.locator("#execution-waves-host .execution-wave-section").first
    section.wait_for(timeout=15000)
    summary = section.locator("> summary").first
    if section.get_attribute("open") is None:
        summary.click()
        expect_open = section
        expect_open.evaluate("""(node) => {
            if (!(node instanceof HTMLElement)) return false;
            return node.hasAttribute("open");
        }""")
    outer_program_chip = section.locator(".execution-wave-section-summary .wave-chip-program").first
    outer_program_chip.wait_for(timeout=15000)

    assert section.locator(".execution-wave-focus").count() == 0
    assert outer_program_chip.count() == 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_program_focus_does_not_repeat_outer_program_chip_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_focus_does_not_repeat_outer_program_chip(*browser_context)


def test_compass_program_focus_does_not_repeat_outer_program_chip_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_program_focus_does_not_repeat_outer_program_chip(*compact_browser_context)


def _assert_compass_governance_disclosures_survive_runtime_rerender(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    program_section = compass.locator("#execution-waves-host .execution-wave-section").first
    release_section = compass.locator("#release-groups-host .execution-wave-section").first
    program_section.wait_for(timeout=15000)
    release_section.wait_for(timeout=15000)

    if program_section.get_attribute("open") is None:
        program_section.locator("> summary").first.click()
    if release_section.get_attribute("open") is None:
        release_section.locator("> summary").first.click()

    assert program_section.evaluate("(node) => node.hasAttribute('open')") is True
    assert release_section.evaluate("(node) => node.hasAttribute('open')") is True

    compass.locator("body").evaluate(
        """async () => {
            const rawState = params();
            const runtime = await loadRuntime(rawState);
            await renderCompassRuntime(rawState, runtime);
        }"""
    )

    program_section = compass.locator("#execution-waves-host .execution-wave-section").first
    release_section = compass.locator("#release-groups-host .execution-wave-section").first
    program_section.wait_for(timeout=15000)
    release_section.wait_for(timeout=15000)

    assert program_section.evaluate("(node) => node.hasAttribute('open')") is True
    assert release_section.evaluate("(node) => node.hasAttribute('open')") is True

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_governance_disclosures_survive_runtime_rerender_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_governance_disclosures_survive_runtime_rerender(*browser_context)


def test_compass_governance_disclosures_survive_runtime_rerender_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_governance_disclosures_survive_runtime_rerender(*compact_browser_context)


def _assert_compass_outer_governance_section_titles(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("#execution-waves-host h2", has_text="Programs").wait_for(timeout=15000)
    compass.locator("#release-groups-host h2", has_text="Release Targets").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_outer_governance_section_titles_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_outer_governance_section_titles(*browser_context)


def test_compass_outer_governance_section_titles_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_outer_governance_section_titles(*compact_browser_context)


def _assert_compass_outer_governance_cards_keep_distinct_surface_tints(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    programs_card = compass.locator("#execution-waves-host > .card.execution-waves-card").first
    releases_card = compass.locator("#release-groups-host > .card.release-groups-card").first
    programs_card.wait_for(timeout=15000)
    releases_card.wait_for(timeout=15000)

    programs_style = programs_card.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderTopColor: style.borderTopColor,
              backgroundImage: style.backgroundImage,
            };
        }"""
    )
    releases_style = releases_card.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderTopColor: style.borderTopColor,
              backgroundImage: style.backgroundImage,
            };
        }"""
    )

    assert programs_style["borderTopColor"] != releases_style["borderTopColor"]
    assert programs_style["backgroundImage"] != releases_style["backgroundImage"]
    assert programs_style["borderTopColor"] == "rgb(191, 213, 243)"
    assert "237, 244, 255" in programs_style["backgroundImage"]
    assert "248, 251, 255" in programs_style["backgroundImage"]
    assert releases_style["borderTopColor"] == "rgb(207, 228, 209)"
    assert "242, 250, 241" in releases_style["backgroundImage"]
    assert "251, 254, 251" in releases_style["backgroundImage"]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_outer_governance_cards_keep_distinct_surface_tints_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_outer_governance_cards_keep_distinct_surface_tints(*browser_context)


def test_compass_outer_governance_cards_keep_distinct_surface_tints_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_outer_governance_cards_keep_distinct_surface_tints(*compact_browser_context)


def _assert_compass_governance_summaries_use_phrasing_content(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&scope=B-105", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    for selector in (
        "#execution-waves-host .execution-wave-section > summary",
        "#release-groups-host .execution-wave-section > summary",
    ):
        summary = compass.locator(selector).first
        summary.wait_for(timeout=15000)
        invalid_descendant_count = summary.evaluate("(node) => node.querySelectorAll('div').length")
        assert invalid_descendant_count == 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_governance_summaries_use_phrasing_content_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_governance_summaries_use_phrasing_content(*browser_context)


def test_compass_governance_summaries_use_phrasing_content_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_governance_summaries_use_phrasing_content(*compact_browser_context)


def _assert_radar_execution_wave_summary_avoids_dead_side_lane(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar, _idea_id = _select_radar_workstream_with_detail_selector(
        page,
        detail_selector=".execution-wave-section",
        failure_message="expected a Radar workstream with execution-wave detail for layout proof",
        selector_timeout=1500,
    )
    section = radar.locator("#detail .execution-wave-section").first
    section.wait_for(timeout=15000)
    if section.get_attribute("open") is None:
        section.evaluate("node => { node.open = true; }")
    section.locator(".execution-wave-focus").first.wait_for(timeout=15000)

    layout = section.evaluate(
        """(node) => {
            const focus = node.querySelector(".execution-wave-focus");
            const focusGrid = node.querySelector(".execution-wave-focus-grid");
            const focusCopy = node.querySelector(".execution-wave-focus-copy");
            const rail = node.querySelector(".execution-wave-focus-stat-rail");
            const sectionBox = node.getBoundingClientRect();
            const focusBox = focus ? focus.getBoundingClientRect() : null;
            const copyBox = focusCopy ? focusCopy.getBoundingClientRect() : null;
            const railStyle = rail ? window.getComputedStyle(rail) : null;
            return {
              sectionWidth: sectionBox.width,
              sectionScrollDelta: node.scrollWidth - node.clientWidth,
              focusWidth: focusBox ? focusBox.width : 0,
              copyWidth: copyBox ? copyBox.width : 0,
              focusGridDisplay: focusGrid ? window.getComputedStyle(focusGrid).display : "",
              railFloat: railStyle ? railStyle.cssFloat : "",
              railMaxWidth: railStyle ? railStyle.maxWidth : "",
            };
        }"""
    )

    assert int(layout["sectionScrollDelta"]) <= 4
    assert float(layout["focusWidth"]) >= float(layout["sectionWidth"]) * 0.88
    assert float(layout["copyWidth"]) >= float(layout["sectionWidth"]) * 0.58
    if float(layout["sectionWidth"]) < 760:
        assert layout["focusGridDisplay"] in {"block", "grid"}
    else:
        assert layout["focusGridDisplay"] == "block"
    if layout["railFloat"] and float(layout["sectionWidth"]) >= 760:
        assert layout["railFloat"] == "right"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_execution_wave_summary_avoids_dead_side_lane_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_radar_execution_wave_summary_avoids_dead_side_lane(*browser_context)


def test_radar_execution_wave_summary_avoids_dead_side_lane_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_radar_execution_wave_summary_avoids_dead_side_lane(*compact_browser_context)


def _assert_compass_release_targets_start_collapsed(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    release_section = compass.locator("#release-groups-host .execution-wave-section").first
    release_section.wait_for(timeout=15000)
    assert release_section.evaluate("(node) => node.hasAttribute('open')") is False

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_release_targets_start_collapsed_in_browser(browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_targets_start_collapsed(*browser_context)


def test_compass_release_targets_start_collapsed_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    _assert_compass_release_targets_start_collapsed(*compact_browser_context)
