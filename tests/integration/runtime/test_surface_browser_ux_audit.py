from __future__ import annotations

import json
import re
from urllib.parse import quote

import pytest

from odylith.runtime.surfaces import render_casebook_dashboard as casebook_renderer
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
    _wait_for_registry_detail_id,
    _wait_for_radar_detail_id,
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
    for link in frame.locator(container_selector).locator(anchor_selector).all():
        if str(link.get_attribute("href") or "").strip() == href:
            link.click()
            return
    raise AssertionError(f"missing anchor for href {href}")


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
            _wait_for_shell_tab(page, "radar")
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
        if workstream or diagram_id:
            page.wait_for_function(
                """({ workstream, diagram }) => {
                    try {
                      const url = new URL(window.location.href);
                      if (url.searchParams.get("tab") !== "atlas") return false;
                      if (diagram) {
                        const frame = document.querySelector("#frame-atlas");
                        if (!["ready", "degraded"].includes(frame?.dataset.navigationOutcome)) return false;
                        if (url.searchParams.get("diagram") !== diagram) return false;
                        const doc = frame.contentDocument;
                        if (doc?.querySelector("#diagramId")?.textContent.trim() !== diagram) return false;
                        const filter = doc.querySelector("#workstreamFilter");
                        if (!filter) return false;
                        const renderedWorkstream = filter.value === "all" ? "" : filter.value;
                        if ((url.searchParams.get("workstream") || "") !== renderedWorkstream) return false;
                      }
                      if (!url.searchParams.has("workstream")) return true;
                      return url.searchParams.get("workstream") === workstream;
                    } catch (_error) {
                      return false;
                    }
                }""",
                arg={"workstream": workstream, "diagram": diagram_id},
                timeout=15000,
            )
        if diagram_id:
            _assert_atlas_selection(
                page, workstream=_extract_query_param(page.url, "workstream"), diagram_id=diagram_id,
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
    page.frame_locator("#frame-casebook").locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)


@pytest.mark.parametrize("normalize_filter", [True, False], ids=["normalized", "compatible"])
def test_atlas_action_oracle_waits_for_exact_diagram_handoff(browser_context, normalize_filter: bool) -> None:  # noqa: ANN001
    base_url, context = browser_context
    href = base_url + "/odylith/index.html?tab=atlas&workstream=B-999&diagram=D-998"
    child_url = base_url + "/oracle-atlas.html"
    parent_html = """<!doctype html><button id="tab-atlas" aria-selected="true">Atlas</button>
      <iframe id="frame-atlas" data-navigation-outcome="ready" src="/oracle-atlas.html"></iframe>
      <script>
        window.probe = {events: ['previous-ready'], queued: false};
        window.completeHandoff = () => {
          if (probe.queued) return;
          probe.queued = true;
          queueMicrotask(() => {
            const frame = document.querySelector('#frame-atlas');
            frame.dataset.navigationOutcome = 'loading';
            probe.events.push('loading');
            frame.contentWindow.applyTarget();
            queueMicrotask(() => {
              const url = new URL(location.href);
              if (__NORMALIZE__) url.searchParams.delete('workstream');
              history.replaceState(null, '', url.pathname + url.search);
              frame.dataset.navigationOutcome = __NORMALIZE__ ? 'degraded' : 'ready';
              probe.events.push(frame.dataset.navigationOutcome);
            });
          });
        };
      </script>""".replace("__NORMALIZE__", json.dumps(normalize_filter))
    child_html = """<!doctype html><h1>Atlas</h1>
      <span id="diagramId">D-997</span><h2 id="diagramTitle">Previous diagram</h2>
      <select id="workstreamFilter"><option value="all">All Workstreams</option>
        <option value="B-999" selected>B-999</option></select>
      <div class="diagram-item active"><button data-diagram="D-997">
        <span class="diagram-name">Previous diagram</span></button></div>
      <img id="viewerImage" alt="Diagram" width="120" height="80"
        src="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='120' height='80'%3E%3C/svg%3E">
      <script>
        const identity = document.querySelector('#diagramId');
        const text = identity.firstChild;
        const content = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
        let diagram = 'D-997';
        // Force the old-document read before delivery of the new rendered snapshot.
        const readIdentity = () => { parent.completeHandoff(); return diagram; };
        Object.defineProperty(identity, 'textContent', {get: readIdentity});
        Object.defineProperty(text, 'nodeValue', {get: readIdentity});
        window.applyTarget = () => {
          diagram = 'D-998';
          content.set.call(identity, diagram);
          document.querySelector('#diagramTitle').textContent = 'Oracle handoff diagram';
          document.querySelector('button').dataset.diagram = diagram;
          document.querySelector('.diagram-name').textContent = 'Oracle handoff diagram';
          document.querySelector('#workstreamFilter').value = __NORMALIZE__ ? 'all' : 'B-999';
        };
      </script>""".replace("__NORMALIZE__", json.dumps(normalize_filter))
    with _new_page(context) as (page, observation):
        page.route(href, lambda route: route.fulfill(status=200, content_type="text/html", body=parent_html))
        page.route(child_url, lambda route: route.fulfill(status=200, content_type="text/html", body=child_html))
        response = page.goto(href, wait_until="domcontentloaded")
        assert response is not None and response.ok
        _assert_shell_target_from_href(page, href)
        terminal = "degraded" if normalize_filter else "ready"
        assert page.evaluate("probe.events") == ["previous-ready", "loading", terminal]
        assert _extract_query_param(page.url, "diagram") == "D-998"
        assert _extract_query_param(page.url, "workstream") == ("" if normalize_filter else "B-999")
        assert page.frame_locator("#frame-atlas").locator("#workstreamFilter").input_value() == (
            "all" if normalize_filter else "B-999"
        )
        _assert_clean_page(page, observation)


def _casebook_agent_link_blocks(casebook) -> list[dict[str, object]]:  # noqa: ANN001
    return casebook.locator("#detailPane").evaluate(
        """(node) => Array.from(node.querySelectorAll('.agent-band-block')).map((block) => ({
            title: String((block.querySelector('.agent-band-title') || {}).textContent || '').trim(),
            hrefs: Array.from(block.querySelectorAll('a.ref-link'))
              .map((link) => String(link.getAttribute('href') || '').trim())
              .filter(Boolean),
            labels: Array.from(block.querySelectorAll('a.ref-link'))
              .map((link) => String(link.textContent || '').trim())
              .filter(Boolean),
          }))"""
    )


def _assert_casebook_lessons_content(casebook) -> None:  # noqa: ANN001
    section = casebook.locator("#detailPane .detail-section-agent")
    heading = casebook.locator("#detailPane .section-heading", has_text="Lessons and evidence")
    assert section.count() <= 1
    if not section.count():
        assert heading.count() == 0
        return
    assert heading.count() == 1
    bodies = section.locator(".agent-band-block, .detail-disclosure-body")
    assert bodies.count() > 0, "Lessons and evidence has a heading without content"
    for body in bodies.all():
        content = body.evaluate(
            """node => {
              const copy = node.cloneNode(true);
              copy.querySelectorAll('.agent-band-title, .signal-label, .coverage-strip, .coverage-note')
                .forEach(label => label.remove());
              return String(copy.textContent || '').trim();
            }"""
        )
        assert content, "Casebook lesson block or disclosure has no substantive body"


def _assert_casebook_agent_links_distinct(blocks: list[dict[str, object]]) -> None:
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
        _wait_for_registry_detail_id(registry, component_id)
        if registry.locator("#detail a.detail-action-chip").count():
            return component_id
    raise AssertionError("expected a Registry component with detail action chips")


def _open_atlas_diagram(page, atlas, diagram_id: str) -> None:  # noqa: ANN001
    _assert_atlas_selection(page, workstream="", diagram_id=diagram_id)
    metadata = atlas.locator("details.diagram-metadata")
    assert metadata.get_attribute("open") is None
    assert atlas.locator("#diagramId").is_visible() is False
    metadata.locator(":scope > summary").focus()
    metadata.locator(":scope > summary").press("Enter")
    assert metadata.get_attribute("open") is not None
    atlas.locator("#diagramId").wait_for(state="visible", timeout=15000)
    assert atlas.locator("#diagramId").inner_text().strip() == diagram_id


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
    with _new_page(context) as (page, observation):
        source_id = "B-048"
        source_url = base_url + f"/odylith/index.html?tab=radar&workstream={quote(source_id, safe='')}"
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok

        radar = page.frame_locator("#frame-radar")
        radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
        _wait_for_radar_detail_id(radar, source_id)
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
            _wait_for_radar_detail_id(radar, source_id)
            _open_radar_topology_relations(radar)
            radar.locator(f'#detail [data-link-idea="{target_id}"]').first.evaluate("node => node.click()")
            _assert_radar_selection(page, str(target_id))
            _wait_for_shell_query_param(page, tab="radar", key="workstream", value=str(target_id))

        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok
        _wait_for_radar_detail_id(radar, source_id)
        _open_radar_topology_relations(radar)
        surface_actions = _frame_anchor_actions(radar, "#detail a.chip-topology-diagram, #detail a.chip-registry-component")
        assert surface_actions, "expected B-048 cross-surface shell links"
        for href in dict.fromkeys(str(action["href"]) for action in surface_actions):
            response = page.goto(source_url, wait_until="domcontentloaded")
            assert response is not None and response.ok
            _wait_for_radar_detail_id(radar, source_id)
            _open_radar_topology_relations(radar)
            selector = "a.chip-topology-diagram" if "tab=atlas" in href else "a.chip-registry-component"
            _click_frame_anchor_by_href(radar, "#detail", selector, href)
            _assert_shell_target_from_href(page, href)

        _assert_clean_page(page, observation)


def test_radar_default_warning_cards_hide_maintainer_traceability_diagnostics(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
        assert response is not None and response.ok

        radar = page.frame_locator("#frame-radar")
        radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
        diagnostic = radar.locator("body").evaluate(
            """() => {
            const data = window.__ODYLITH_BACKLOG_DATA__ || {};
            const traceability = data.traceability_index || data.traceability_graph || {};
            const rows = Array.isArray(traceability.warning_items) ? traceability.warning_items : [];
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
        assert diagnostic, "Populated Radar audit requires a workstream-scoped maintainer-only traceability diagnostic."

        source_id = str(diagnostic["idea_id"])
        response = page.goto(
            base_url + f"/odylith/index.html?tab=radar&workstream={quote(source_id, safe='')}",
            wait_until="domcontentloaded",
        )
        assert response is not None and response.ok
        _wait_for_radar_detail_id(radar, source_id)

        warning_text = " ".join(radar.locator("#detail .warning-item").all_inner_texts())
        assert str(diagnostic["message"]) not in warning_text
        if diagnostic.get("source"):
            assert str(diagnostic["source"]) not in warning_text
        assert "severity: info" not in warning_text
        assert "autofix skipped" not in warning_text.lower()

        _assert_clean_page(page, observation)


def test_registry_detail_action_chip_audit_round_trips_cleanly(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
        assert response is not None and response.ok

        registry = page.frame_locator("#frame-registry")
        registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        component_id = _select_registry_component_with_actions(registry)
        _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
        source_url = base_url + f"/odylith/index.html?tab=registry&component={quote(component_id, safe='')}"
        topology = registry.locator("#detail details.context-section")
        assert topology.get_attribute("open") is None
        assert registry.locator("#detail a.detail-action-chip").first.is_visible() is False
        topology.locator(":scope > summary").focus()
        topology.locator(":scope > summary").press("Enter")
        registry.locator("#detail a.detail-action-chip").first.wait_for(state="visible", timeout=15000)
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
            _wait_for_registry_detail_id(registry, component_id)
            topology = registry.locator("#detail details.context-section")
            assert topology.get_attribute("open") is None
            topology.locator(":scope > summary").focus()
            topology.locator(":scope > summary").press("Enter")
            assert href in {str(action["href"]) for action in _frame_anchor_actions(registry, "#detail a.detail-action-chip")}
            _click_frame_anchor_by_href(registry, "#detail", "a.detail-action-chip", href)
            _assert_shell_target_from_href(page, href)

        _assert_clean_page(page, observation)


@pytest.mark.parametrize("source_diagram_id", ["D-018", "D-025"])
def test_atlas_surface_links_and_context_pills_round_trip_cleanly(browser_context, source_diagram_id: str) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        source_url = base_url + f"/odylith/index.html?tab=atlas&diagram={quote(source_diagram_id, safe='')}"
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok

        atlas = page.frame_locator("#frame-atlas")
        atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
        _open_atlas_diagram(page, atlas, source_diagram_id)

        linked_context = atlas.locator("details.linked-context-section")
        assert linked_context.get_attribute("open") is None
        assert atlas.locator("#surfaceLinks").is_visible() is False
        linked_context.locator("summary").focus()
        linked_context.locator("summary").press("Enter")
        atlas.locator("#surfaceLinks").wait_for(state="visible", timeout=15000)
        historical = atlas.locator("#historicalWorkstreamDisclosure")
        if historical.is_visible():
            assert historical.get_attribute("open") is None
            historical.locator("summary").focus()
            historical.locator("summary").press("Enter")

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
            _open_atlas_diagram(page, atlas, source_diagram_id)
            linked_context = atlas.locator("details.linked-context-section")
            assert linked_context.get_attribute("open") is None
            linked_context.locator("summary").focus()
            linked_context.locator("summary").press("Enter")
            historical = atlas.locator("#historicalWorkstreamDisclosure")
            if historical.is_visible():
                assert historical.get_attribute("open") is None
                historical.locator("summary").focus()
                historical.locator("summary").press("Enter")
            selector = (
                "#surfaceLinks a, #registryLinks a, #activeWorkstreamLinks a.workstream-pill-link, "
                "#ownerWorkstreamLinks a.workstream-pill-link, #historicalWorkstreamLinks a.workstream-pill-link"
            )
            _click_frame_anchor_by_href(atlas, "body", selector, href)
            _assert_shell_target_from_href(page, href)

        _assert_clean_page(page, observation)


def test_compass_cross_surface_links_round_trip_cleanly(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        source_url = base_url + "/odylith/index.html?tab=compass"
        response = page.goto(source_url, wait_until="domcontentloaded")
        assert response is not None and response.ok

        compass = page.frame_locator("#frame-compass")
        _wait_for_compass_ready(compass)
        workstream_link_specs = [
            ("a.ws-id-btn, a.ws-covered-id-btn", "expected Compass workstream deeplinks"),
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
            _assert_clean_page(page, observation)
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

        _assert_clean_page(page, observation)


def test_casebook_direct_bug_routes_and_reload_keep_selection_truthful(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
        assert response is not None and response.ok

        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
        casebook.locator("button.bug-row").first.wait_for(timeout=15000)
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

        _assert_clean_page(page, observation)


def test_casebook_agent_band_links_stay_distinct_and_non_repetitive(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
        assert response is not None and response.ok

        casebook = page.frame_locator("#frame-casebook")
        casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
        casebook.locator("button.bug-row").first.wait_for(timeout=15000)
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
            page.wait_for_function(
                """({ route, title }) => {
                  const view = document.querySelector('#frame-casebook')?.contentWindow;
                  const entry = (view?.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ || {})[route];
                  const selected = view?.document.querySelector('button.bug-row.active');
                  const renderedTitle = view?.document.querySelector('#detailPane .detail-title');
                  return Boolean(entry && typeof entry === 'object'
                    && selected?.getAttribute('data-bug') === route
                    && String(renderedTitle?.textContent || '').trim() === title
                    && !view.document.querySelector('#detailPane [role=status]'));
                }""",
                arg={"route": str(row["bug"]), "title": str(row["title"])},
                timeout=15000,
            )
            _assert_casebook_lessons_content(casebook)
            blocks = _casebook_agent_link_blocks(casebook)
            if not blocks:
                continue
            inspected_blocks += 1
            _assert_casebook_agent_links_distinct(blocks)

        assert inspected_blocks >= 1, "expected at least one Casebook detail with agent-band blocks"

        _assert_clean_page(page, observation)


@pytest.mark.parametrize("content_state", ["links", "text", "gaps", "empty", "missing-detail"])
def test_casebook_lessons_preserve_content_and_explain_missing_detail(browser_context, content_state: str) -> None:  # noqa: ANN001
    base_url, context = browser_context
    coverage = {
        "captured_count": 1, "total_fields": 2,
        "missing_fields": ["Regression Tests Added"], "required_missing_fields": [],
    } if content_state in {"gaps", "missing-detail"} else {}
    summary = {
        "bug_id": "CB-999", "bug_route": "CB-999", "bug_key": "CB-999",
        "title": "Preserve Casebook evidence", "summary": "The saved summary remains available.",
        "status": "Open", "status_token": "open", "severity": "P2", "severity_token": "p2",
        "date": "2026-10-15", "intelligence_coverage": coverage,
    }
    detail = {"title": "Loaded Casebook evidence"}
    proof_href = "../../src/odylith/runtime/evaluation/benchmark_compare.py"
    if content_state == "links":
        detail["code_ref_links"] = [{"path": "benchmark_compare.py", "href": proof_href}]
    elif content_state == "text":
        detail["detail_sections"] = [{"field": "Lesson", "value": "Retain the original comparison evidence."}]
    payload = {
        "bugs": [summary], "counts": {"total_cases": 1},
        "filters": {"severity_tokens": ["p2"], "status_tokens": ["open"]},
        "detail_manifest": {"CB-999": "/casebook-audit-detail.v1.js"},
    }
    shard = {} if content_state == "missing-detail" else {"CB-999": detail}
    with _new_page(context) as (page, observation):
        page.route("**/odylith/casebook/casebook.html*", lambda route: route.fulfill(
            status=200, content_type="text/html", body=casebook_renderer._render_html(payload=payload),
        ))
        page.route("**/casebook-audit-detail.v1.js", lambda route: route.fulfill(
            status=200, content_type="application/javascript",
            body="window.__ODYLITH_CASEBOOK_DETAIL_SHARDS__ = " + json.dumps(shard) + ";",
        ))
        response = page.goto(base_url + "/odylith/index.html?tab=casebook&bug=CB-999", wait_until="domcontentloaded")
        assert response is not None and response.ok
        casebook = page.frame_locator("#frame-casebook")
        _assert_casebook_selection(page, "CB-999")
        status = casebook.locator("#detailPane [role=status]")
        if content_state == "missing-detail":
            status.wait_for(timeout=15000)
            assert status.inner_text() == "Bug detail unavailable. The available summary is shown."
            assert casebook.locator("#detailPane .detail-summary").inner_text() == summary["summary"]
        else:
            casebook.locator("#detailPane .detail-title", has_text="Loaded Casebook evidence").wait_for(timeout=15000)
            assert status.count() == 0
        _assert_casebook_lessons_content(casebook)
        section = casebook.locator("#detailPane .detail-section-agent")
        assert section.count() == (0 if content_state == "empty" else 1)
        if content_state == "text":
            assert section.locator(".disclosure-title").inner_text() == "Additional Captured Detail"
            assert "Retain the original comparison evidence." in section.locator(".detail-disclosure-body").text_content()
        elif content_state in {"gaps", "missing-detail"}:
            assert section.locator(".disclosure-title").inner_text() == "Capture Gaps"
            assert "Regression Tests Added" in section.locator(".detail-disclosure-body").text_content()
        blocks = _casebook_agent_link_blocks(casebook)
        _assert_casebook_agent_links_distinct(blocks)
        if content_state == "links":
            assert [block["hrefs"] for block in blocks] == [[proof_href]]
            block = section.locator(".agent-band-block")
            block.locator("a.ref-link").evaluate("node => node.after(node.cloneNode(true))")
            with pytest.raises(AssertionError, match="duplicate hrefs inside Casebook block"):
                _assert_casebook_agent_links_distinct(_casebook_agent_link_blocks(casebook))
            block.locator("a.ref-link").last.evaluate("node => node.remove()")
            block.evaluate("node => node.after(node.cloneNode(true))")
            with pytest.raises(AssertionError, match="duplicate agent-band links across Casebook blocks"):
                _assert_casebook_agent_links_distinct(_casebook_agent_link_blocks(casebook))
        else:
            assert blocks == []
        _assert_clean_page(page, observation)
