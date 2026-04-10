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
            const summaryNode = node.querySelector(".detail-summary");
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
    assert "summary-facts" in layout["childOrder"]
    assert layout["childOrder"].index("summary-facts") < layout["childOrder"].index("detail-summary")
    assert layout["factsBeforeSummary"], "Casebook primary fact cards should render before the supporting summary copy"
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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    _casebook, _row, layout = _select_casebook_layout_stress_row(page)

    pane_layout = casebook.locator("#detailPane").evaluate(
        """(node) => ({
            clientWidth: node.clientWidth,
            scrollWidth: node.scrollWidth,
        })"""
    )

    assert "summary-facts" in layout["childOrder"]
    assert layout["childOrder"].index("summary-facts") < layout["childOrder"].index("detail-summary")
    assert layout["factsBeforeSummary"], "Casebook primary fact cards should stay ahead of the supporting summary copy in compact view"
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
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
              paddingBottom: style.paddingBottom,
              paddingLeft: style.paddingLeft,
            };
        }"""
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
        chips = radar.locator("#detail button.execution-wave-chip-link, #detail button.entity-id-chip")
        if chips.count():
            return radar
    raise AssertionError("expected a Radar detail with at least one rendered workstream chip")


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
    registry = page.frame_locator("#frame-registry")
    buttons = registry.locator("button[data-component]")
    count = buttons.count()
    for index in range(count):
        button = buttons.nth(index)
        component_id = str(button.get_attribute("data-component") or "").strip()
        if not component_id:
            continue
        button.click()
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        registry.locator("#detail .component-name").wait_for(timeout=15000)
        if registry.locator("#detail a.detail-action-chip").count():
            return registry
    raise AssertionError("expected a Registry detail with at least one deep-link chip")


def _select_casebook_deep_link_chip_for_style_audit(page):  # noqa: ANN001
    casebook = page.frame_locator("#frame-casebook")
    rows = casebook.locator("button.bug-row")
    count = rows.count()
    for index in range(count):
        row = rows.nth(index)
        bug_id = str(row.get_attribute("data-bug") or "").strip()
        if not bug_id:
            continue
        row.click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_id)
        casebook.locator("#detailPane .detail-title").wait_for(timeout=15000)
        if casebook.locator("#detailPane a.action-chip").count():
            return casebook
    raise AssertionError("expected a Casebook detail with at least one deep-link chip")


def _assert_shared_workstream_buttons_keep_compact_style_contract(  # noqa: ANN001
    base_url: str,
    context,
) -> None:
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("a.ws-id-btn").first.wait_for(timeout=15000)
    compass.locator("#release-groups-host a.execution-wave-chip-link").first.wait_for(timeout=15000)

    compass_current_style = _workstream_button_style(compass, "a.ws-id-btn")
    compass_release_style = _workstream_button_style(compass, "#release-groups-host a.execution-wave-chip-link")

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

    for style in (compass_current_style, compass_release_style, atlas_style, radar_style):
        assert style["fontSize"] == "12px"
        assert style["fontWeight"] == "500"
        assert style["paddingTop"] == "1px"
        assert style["paddingRight"] == "8px"
        assert style["paddingBottom"] == "1px"
        assert style["paddingLeft"] == "8px"

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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
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
