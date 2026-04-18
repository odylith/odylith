from __future__ import annotations

import re
from urllib.parse import quote

import pytest

from tests.integration.runtime.surface_browser_test_support import (
    _assert_atlas_selection,
    _assert_casebook_selection,
    _assert_clean_page,
    _assert_radar_selection,
    _assert_registry_selection,
    _extract_query_param,
    _new_page,
    _open_radar_topology_relations,
    _wait_for_compass_ready,
    _wait_for_shell_query_param,
    _wait_for_shell_tab,
    browser_context,
)

_WORKSTREAM_ID_RE = re.compile(r"^B-\d{3,}$")


def _frame_anchor_actions(frame, selector: str) -> list[dict[str, str]]:  # noqa: ANN001
    return frame.locator(selector).evaluate_all(
        """nodes => nodes
          .map((node) => ({
            href: String(node.getAttribute("href") || "").trim(),
            label: String(node.textContent || "").trim(),
          }))
          .filter((item) => item.href.includes("index.html?tab="))
        """
    )


def _click_frame_anchor_by_href(frame, container_selector: str, anchor_selector: str, href: str) -> None:  # noqa: ANN001
    frame.locator(container_selector).evaluate(
        """(node, payload) => {
            const selector = String(payload.selector || "");
            const href = String(payload.href || "").trim();
            const link = Array.from(node.querySelectorAll(selector)).find(
              (candidate) => String(candidate.getAttribute("href") || "").trim() === href
            );
            if (!link) {
              throw new Error(`missing anchor for href ${href}`);
            }
            link.click();
        }""",
        {"selector": anchor_selector, "href": href},
    )


def _assert_compass_target(page, href: str) -> None:  # noqa: ANN001
    scope = _extract_query_param(href, "scope") or _extract_query_param(href, "workstream")
    page.wait_for_function(
        """(scope) => {
            try {
              const url = new URL(window.location.href);
              if (!url.pathname.endsWith("/odylith/index.html")) return false;
              if (url.searchParams.get("tab") !== "compass") return false;
              if (!scope) return true;
              return (url.searchParams.get("scope") || url.searchParams.get("workstream")) === scope;
            } catch (_error) {
              return false;
            }
        }""",
        arg=scope,
        timeout=15000,
    )
    assert page.locator("#tab-compass").get_attribute("aria-selected") == "true"
    compass = page.frame_locator("#frame-compass")
    _wait_for_compass_ready(compass)
    if scope:
        compass.locator("#scope-pill", has_text=scope).wait_for(timeout=15000)


def _assert_shell_target_from_href(page, href: str) -> None:  # noqa: ANN001
    tab = _extract_query_param(href, "tab")
    assert tab in {"radar", "registry", "atlas", "compass", "casebook"}, f"unexpected shell tab in href: {href}"
    if tab == "radar":
        workstream = _extract_query_param(href, "workstream")
        if workstream:
            _assert_radar_selection(page, workstream)
            _wait_for_shell_query_param(page, tab="radar", key="workstream", value=workstream)
            return
        _wait_for_shell_tab(page, "radar")
        page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
        return
    if tab == "registry":
        component = _extract_query_param(href, "component")
        if component:
            _assert_registry_selection(page, component)
            return
        _wait_for_shell_tab(page, "registry")
        page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        return
    if tab == "atlas":
        diagram_id = _extract_query_param(href, "diagram")
        workstream = _extract_query_param(href, "workstream")
        _wait_for_shell_tab(page, "atlas")
        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        if diagram_id:
            atlas.locator("#diagramId", has_text=diagram_id).wait_for(timeout=15000)
        if workstream:
            page.wait_for_function(
                """(workstream) => {
                    try {
                      const url = new URL(window.location.href);
                      if (url.searchParams.get("tab") !== "atlas") return false;
                      if (!url.searchParams.has("workstream")) return true;
                      return url.searchParams.get("workstream") === workstream;
                    } catch (_error) {
                      return false;
                    }
                }""",
                arg=workstream,
                timeout=15000,
            )
        return
    if tab == "compass":
        _assert_compass_target(page, href)
        return

    bug_route = _extract_query_param(href, "bug")
    if bug_route:
        _assert_casebook_selection(page, bug_route)
        return
    _wait_for_shell_tab(page, "casebook")
    page.frame_locator("#frame-casebook").locator("h1", has_text="Casebook").wait_for(timeout=15000)


def _casebook_agent_link_blocks(casebook) -> list[dict[str, object]]:  # noqa: ANN001
    return casebook.locator("#detailPane").evaluate(
        """(node) => Array.from(node.querySelectorAll('.agent-band-block')).map((block) => ({
            title: String((block.querySelector('.agent-band-title') || {}).textContent || '').trim(),
            hrefs: Array.from(new Set(
              Array.from(block.querySelectorAll('a.ref-link'))
                .map((link) => String(link.getAttribute('href') || '').trim())
                .filter(Boolean)
            )),
            labels: Array.from(new Set(
              Array.from(block.querySelectorAll('a.ref-link'))
                .map((link) => String(link.textContent || '').trim())
                .filter(Boolean)
            )),
          }))"""
    )


def _select_registry_component_with_actions(registry) -> str:  # noqa: ANN001
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
            return component_id
    raise AssertionError("expected a Registry component with detail action chips")


def _open_atlas_diagram(atlas, diagram_id: str) -> None:  # noqa: ANN001
    button = atlas.locator(f'button[data-diagram="{diagram_id}"]').first
    if button.count():
        button.evaluate("node => node.click()")
    atlas.locator("#diagramId", has_text=diagram_id).wait_for(timeout=15000)


def _collect_compass_component_actions(compass, *, limit: int = 3) -> list[dict[str, str]]:  # noqa: ANN001
    actions: list[dict[str, str]] = []
    rows = compass.locator("tr.ws-summary-row")
    count = rows.count()
    seen_workstreams: set[str] = set()
    for index in range(count):
        row = rows.nth(index)
        workstream = str(row.get_attribute("data-ws-id") or "").strip()
        if not workstream or workstream in seen_workstreams:
            continue
        seen_workstreams.add(workstream)
        row.evaluate("node => node.click()")
        detail = compass.locator(f'tr.ws-detail-row.is-open[data-ws-detail="{workstream}"]')
        detail.wait_for(timeout=15000)
        links = _frame_anchor_actions(detail, "a.chip-link")
        if not links:
            continue
        actions.append(
            {
                "workstream": workstream,
                "href": str(links[0]["href"]),
            }
        )
        if len(actions) >= limit:
            break
    return actions


def test_radar_b048_brutal_topology_and_surface_link_audit(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    source_id = "B-048"
    source_url = base_url + f"/odylith/index.html?tab=radar&workstream={quote(source_id, safe='')}"
    response = page.goto(source_url, wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=source_id).wait_for(timeout=15000)
    _open_radar_topology_relations(radar)

    relation_ids = radar.locator("#detail").evaluate(
        """(node) => Array.from(
            new Set(
              Array.from(node.querySelectorAll('details.topology-relations-panel .topology-relations [data-link-idea]'))
                .map((chip) => String(chip.getAttribute('data-link-idea') || '').trim())
                .filter(Boolean)
            )
        )"""
    )
    assert relation_ids, "expected B-048 topology relations"

    for target_id in relation_ids:
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=source_id).wait_for(timeout=15000)
        _open_radar_topology_relations(radar)
        radar.locator(f'#detail [data-link-idea="{target_id}"]').first.evaluate("node => node.click()")
        _assert_radar_selection(page, str(target_id))
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=str(target_id))

    response = page.goto(source_url, wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=source_id).wait_for(timeout=15000)
    _open_radar_topology_relations(radar)
    surface_actions = _frame_anchor_actions(radar, "#detail a.chip-topology-diagram, #detail a.chip-registry-component")
    assert surface_actions, "expected B-048 cross-surface shell links"
    for href in dict.fromkeys(str(action["href"]) for action in surface_actions):
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=source_id).wait_for(timeout=15000)
        _open_radar_topology_relations(radar)
        selector = "a.chip-topology-diagram" if "tab=atlas" in href else "a.chip-registry-component"
        _click_frame_anchor_by_href(radar, "#detail", selector, href)
        _assert_shell_target_from_href(page, href)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_default_warning_cards_hide_maintainer_traceability_diagnostics(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    diagnostic = radar.locator("body").evaluate(
        """() => {
            const data = window.__ODYLITH_BACKLOG_DATA__ || {};
            const rows = Array.isArray(data.warning_items) ? data.warning_items : [];
            const match = rows.find((entry) => {
              const ideaId = String(entry.idea_id || '').trim();
              const audience = String(entry.audience || '').trim().toLowerCase();
              const visibility = String(entry.surface_visibility || '').trim().toLowerCase();
              return ideaId && audience === 'maintainer' && visibility === 'diagnostics';
            });
            if (!match) return null;
            return {
              idea_id: String(match.idea_id || '').trim(),
              message: String(match.message || '').trim(),
              source: String(match.source || '').trim(),
            };
        }"""
    )
    if not diagnostic:
        pytest.skip("Radar fixture does not currently expose maintainer-only traceability diagnostics.")

    source_id = str(diagnostic["idea_id"])
    response = page.goto(
        base_url + f"/odylith/index.html?tab=radar&workstream={quote(source_id, safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=source_id).wait_for(timeout=15000)

    warning_text = " ".join(radar.locator("#detail .warning-item").all_inner_texts())
    assert str(diagnostic["message"]) not in warning_text
    if diagnostic.get("source"):
        assert str(diagnostic["source"]) not in warning_text
    assert "severity: info" not in warning_text
    assert "autofix skipped" not in warning_text.lower()

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_registry_detail_action_chip_audit_round_trips_cleanly(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
    assert response is not None and response.ok

    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    component_id = _select_registry_component_with_actions(registry)
    source_url = base_url + f"/odylith/index.html?tab=registry&component={quote(component_id, safe='')}"
    actions = _frame_anchor_actions(registry, "#detail a.detail-action-chip")
    assert actions, "expected Registry detail action chips"
    workstream_actions = [
        action
        for action in actions
        if _WORKSTREAM_ID_RE.fullmatch(str(action["label"]).strip())
    ]
    assert workstream_actions, "expected Registry detail workstream chips"
    for action in workstream_actions:
        assert _extract_query_param(str(action["href"]), "tab") == "radar"

    for href in dict.fromkeys(str(action["href"]) for action in actions):
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        _click_frame_anchor_by_href(registry, "#detail", "a.detail-action-chip", href)
        _assert_shell_target_from_href(page, href)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


@pytest.mark.parametrize("source_diagram_id", ["D-018", "D-025"])
def test_atlas_surface_links_and_context_pills_round_trip_cleanly(browser_context, source_diagram_id: str) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    source_url = base_url + f"/odylith/index.html?tab=atlas&diagram={quote(source_diagram_id, safe='')}"
    response = page.goto(source_url, wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    _open_atlas_diagram(atlas, source_diagram_id)

    actions = []
    actions.extend(_frame_anchor_actions(atlas, "#surfaceLinks a"))
    actions.extend(_frame_anchor_actions(atlas, "#registryLinks a"))
    workstream_actions = []
    workstream_actions.extend(_frame_anchor_actions(atlas, "#activeWorkstreamLinks a.workstream-pill-link"))
    workstream_actions.extend(_frame_anchor_actions(atlas, "#ownerWorkstreamLinks a.workstream-pill-link"))
    workstream_actions.extend(_frame_anchor_actions(atlas, "#historicalWorkstreamLinks a.workstream-pill-link"))
    actions.extend(workstream_actions)
    unique_hrefs = list(dict.fromkeys(str(action["href"]) for action in actions))
    assert unique_hrefs, "expected Atlas shell/context links"
    assert workstream_actions, "expected Atlas workstream pills"
    for action in workstream_actions:
        assert _extract_query_param(str(action["href"]), "tab") == "radar"

    for href in unique_hrefs:
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        atlas.locator("#diagramId", has_text=source_diagram_id).wait_for(timeout=15000)
        selector = (
            "#surfaceLinks a, #registryLinks a, #activeWorkstreamLinks a.workstream-pill-link, "
            "#ownerWorkstreamLinks a.workstream-pill-link, #historicalWorkstreamLinks a.workstream-pill-link"
        )
        _click_frame_anchor_by_href(atlas, "body", selector, href)
        _assert_shell_target_from_href(page, href)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_cross_surface_links_round_trip_cleanly(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    source_url = base_url + "/odylith/index.html?tab=compass"
    response = page.goto(source_url, wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    _wait_for_compass_ready(compass)
    workstream_link_specs = [
        ("a.ws-id-btn", "expected Compass current workstream deeplinks"),
    ]
    optional_workstream_link_specs = [
        ("#execution-waves-host a.execution-wave-chip-link", "expected Compass execution-wave workstream deeplinks"),
        ("#release-groups-host a.execution-wave-chip-link", "expected Compass release workstream deeplinks"),
        ("a.workstream-id-chip", "expected Compass timeline workstream deeplinks"),
    ]

    for selector, failure_message in workstream_link_specs + optional_workstream_link_specs:
        if selector.startswith("#release-groups-host"):
            release_summary = compass.locator("#release-groups-host summary").first
            if release_summary.count():
                release_summary.evaluate(
                    """(node) => {
                        const details = node.closest("details");
                        if (details && !details.open) node.click();
                    }"""
                )
        if selector.startswith("#execution-waves-host"):
            wave_summary = compass.locator("#execution-waves-host summary").first
            if wave_summary.count():
                wave_summary.evaluate(
                    """(node) => {
                        const details = node.closest("details");
                        if (details && !details.open) node.click();
                    }"""
                )
        hrefs = list(
            dict.fromkeys(
                str(action["href"])
                for action in _frame_anchor_actions(compass, selector)[:5]
            )
        )
        if selector in {spec[0] for spec in optional_workstream_link_specs} and not hrefs:
            continue
        assert hrefs, failure_message
        for href in hrefs:
            assert _extract_query_param(href, "tab") == "radar"
            response = page.goto(source_url, wait_until="domcontentloaded")
            assert response is not None and response.ok
            _wait_for_compass_ready(compass)
            compass.locator(f'{selector}[href="{href}"]').first.wait_for(timeout=15000)
            _click_frame_anchor_by_href(compass, "body", selector, href)
            _assert_shell_target_from_href(page, href)

    response = page.goto(source_url, wait_until="domcontentloaded")
    assert response is not None and response.ok
    _wait_for_compass_ready(compass)
    component_actions = _collect_compass_component_actions(compass)
    if not component_actions:
        pytest.skip("Compass fixture does not currently expose row detail component links.")

    for action in component_actions:
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        compass.locator(f'tr.ws-summary-row[data-ws-id="{action["workstream"]}"]').first.evaluate("node => node.click()")
        compass.locator(f'tr.ws-detail-row.is-open[data-ws-detail="{action["workstream"]}"]').wait_for(timeout=15000)
        _click_frame_anchor_by_href(
            compass,
            f'tr.ws-detail-row.is-open[data-ws-detail="{action["workstream"]}"]',
            "a.chip-link",
            str(action["href"]),
        )
        _assert_shell_target_from_href(page, str(action["href"]))

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_direct_bug_routes_and_reload_keep_selection_truthful(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    sample_rows = casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes.slice(0, 4).map((node) => ({
          bug: String(node.getAttribute("data-bug") || "").trim(),
          title: String((node.querySelector(".bug-row-title") || {}).textContent || "").trim(),
        }))"""
    )
    bug_routes = [row for row in sample_rows if row["bug"] and row["title"]]
    assert len(bug_routes) >= 3, "expected several Casebook rows for history audit"

    for row in bug_routes[:3]:
        casebook.locator(f'button.bug-row[data-bug="{row["bug"]}"]').click()
        _assert_casebook_selection(page, str(row["bug"]))
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=str(row["bug"]))
        casebook.locator("#detailPane .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)

    for row in bug_routes[:3]:
        direct_url = base_url + f"/odylith/index.html?tab=casebook&bug={quote(str(row['bug']), safe='')}"
        response = page.goto(direct_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        _assert_casebook_selection(page, str(row["bug"]))
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=str(row["bug"]))
        casebook.locator("#detailPane .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)
        response = page.reload(wait_until="domcontentloaded")
        assert response is not None and response.ok
        _assert_casebook_selection(page, str(row["bug"]))
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=str(row["bug"]))
        casebook.locator("#detailPane .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_agent_band_links_stay_distinct_and_non_repetitive(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    sample_routes = casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes.slice(0, 10).map((node) => ({
          bug: String(node.getAttribute("data-bug") || "").trim(),
          title: String((node.querySelector(".bug-row-title") || {}).textContent || "").trim(),
        })).filter((row) => row.bug && row.title)"""
    )
    assert sample_routes, "expected Casebook rows for agent-band audit"

    inspected_blocks = 0
    for row in sample_routes:
        casebook.locator(f'button.bug-row[data-bug="{row["bug"]}"]').click()
        _assert_casebook_selection(page, str(row["bug"]))
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=str(row["bug"]))
        casebook.locator("#detailPane .detail-title", has_text=str(row["title"])).wait_for(timeout=15000)
        casebook.locator("#detailPane .section-heading", has_text="Odylith Agent Learnings").wait_for(timeout=15000)

        blocks = [block for block in _casebook_agent_link_blocks(casebook) if block.get("title")]
        if not blocks:
            continue
        inspected_blocks += 1

        seen_hrefs: dict[str, str] = {}
        duplicates: list[tuple[str, str, str]] = []
        for block in blocks:
            title = str(block.get("title") or "").strip()
            hrefs = [str(token).strip() for token in block.get("hrefs", []) if str(token).strip()]
            assert len(hrefs) == len(set(hrefs)), f"duplicate hrefs inside Casebook block {title}: {hrefs}"
            for href in hrefs:
                if href in seen_hrefs:
                    duplicates.append((href, seen_hrefs[href], title))
                else:
                    seen_hrefs[href] = title
        assert duplicates == [], f"duplicate agent-band links across Casebook blocks: {duplicates}"

    assert inspected_blocks >= 1, "expected at least one Casebook detail with agent-band blocks"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
