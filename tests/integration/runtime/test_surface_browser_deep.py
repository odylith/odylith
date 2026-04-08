from __future__ import annotations

import datetime as dt
import gzip
import json
import re
import shutil
from zoneinfo import ZoneInfo

import pytest
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.surfaces import render_compass_dashboard
from odylith.runtime.surfaces import render_tooling_dashboard as tooling_dashboard_renderer
from tests.integration.runtime.surface_browser_test_support import (
    _REPO_ROOT,
    _assert_clean_page,
    _assert_compass_live_state,
    _browser,
    _static_server,
    _atlas_total,
    _click_visible,
    _compass_brief_metadata,
    _new_page,
    _select_radar_row_with_link,
    _wait_for_compass_brief_state,
    _wait_for_shell_query_param,
    _wait_for_shell_tab,
    browser_context,
    compact_browser_context,
)


class _CompassProvider:
    def __init__(self) -> None:
        self.calls = 0

    @staticmethod
    def _pick_fact_id(section: dict[str, object], *, preferred_kinds: tuple[str, ...]) -> str:
        facts = section.get("facts")
        if isinstance(facts, list):
            for fact in facts:
                if not isinstance(fact, dict):
                    continue
                kind = str(fact.get("kind", "")).strip().lower()
                fact_id = str(fact.get("id", "")).strip()
                if fact_id and kind in preferred_kinds:
                    return fact_id
            for fact in facts:
                if isinstance(fact, dict):
                    fact_id = str(fact.get("id", "")).strip()
                    if fact_id:
                        return fact_id
        return ""

    def generate_structured(self, *, request):  # noqa: ANN001
        self.calls += 1
        prompt_payload = request.prompt_payload if isinstance(request.prompt_payload, dict) else {}
        fact_packet = prompt_payload.get("fact_packet") if isinstance(prompt_payload.get("fact_packet"), dict) else {}
        sections = fact_packet.get("sections") if isinstance(fact_packet.get("sections"), list) else []
        section_map = {
            str(section.get("key", "")).strip(): section
            for section in sections
            if isinstance(section, dict) and str(section.get("key", "")).strip()
        }

        completed_id = self._pick_fact_id(section_map.get("completed", {}), preferred_kinds=("plan_completion", "execution_highlight"))
        direction_id = self._pick_fact_id(section_map.get("current_execution", {}), preferred_kinds=("direction",))
        operator_id = self._pick_fact_id(section_map.get("current_execution", {}), preferred_kinds=("signal", "timeline", "freshness"))
        forcing_id = self._pick_fact_id(section_map.get("next_planned", {}), preferred_kinds=("forcing_function", "fallback_next"))
        impact_id = self._pick_fact_id(section_map.get("why_this_matters", {}), preferred_kinds=("executive_impact",))
        leverage_id = self._pick_fact_id(section_map.get("why_this_matters", {}), preferred_kinds=("operator_leverage",))
        risk_id = self._pick_fact_id(section_map.get("risks_to_watch", {}), preferred_kinds=("risk_posture",))

        return {
            "sections": [
                {
                    "key": "completed",
                    "label": "Completed in this window",
                    "bullets": [
                        {
                            "voice": "operator",
                            "text": "Verified movement landed in this window, so Compass should read as current work instead of recycled fallback.",
                            "fact_ids": [completed_id],
                        }
                    ],
                },
                {
                    "key": "current_execution",
                    "label": "Current execution",
                    "bullets": [
                        {
                            "voice": "executive",
                            "text": "Execution direction stays on the live Compass contract rather than a deterministic shell-safe placeholder.",
                            "fact_ids": [direction_id],
                        },
                        {
                            "voice": "operator",
                            "text": "The current packet still carries enough signal to justify provider-backed global narration in the bounded path.",
                            "fact_ids": [operator_id],
                        },
                    ],
                },
                {
                    "key": "next_planned",
                    "label": "Next planned",
                    "bullets": [
                        {
                            "voice": "operator",
                            "text": "Next work keeps shell-safe bounded while preserving a live global brief when the provider is reachable.",
                            "fact_ids": [forcing_id],
                        }
                    ],
                },
                {
                    "key": "why_this_matters",
                    "label": "Why this matters",
                    "bullets": [
                        {
                            "voice": "executive",
                            "text": "Compass trust breaks quickly when maintainers reopen it and see deterministic fallback despite an available local provider.",
                            "fact_ids": [impact_id],
                        },
                        {
                            "voice": "operator",
                            "text": "The operator consequence is less time second-guessing whether the brief is current and less need to rerun refresh blindly.",
                            "fact_ids": [leverage_id],
                        },
                    ],
                },
                {
                    "key": "risks_to_watch",
                    "label": "Risks to watch",
                    "bullets": [
                        {
                            "voice": "operator",
                            "text": "No blocking Compass risk is surfaced in this synthetic proof run.",
                            "fact_ids": [risk_id],
                        }
                    ],
                },
            ]
        }

    def generate_finding(self, *, prompt_payload):  # noqa: ANN001, ARG002
        raise AssertionError("Compass browser proof should use structured generation only.")


def _pane_hidden(page, frame_selector: str) -> bool:  # noqa: ANN001
    return bool(page.locator(frame_selector).evaluate("node => Boolean(node.hidden)"))


def _assert_single_visible_pane(page, active_frame_selector: str) -> None:  # noqa: ANN001
    panes = (
        "#frame-radar",
        "#frame-registry",
        "#frame-casebook",
        "#frame-atlas",
        "#frame-compass",
    )
    visible = [selector for selector in panes if not _pane_hidden(page, selector)]
    assert visible == [active_frame_selector]


def _render_tooling_shell_fixture(fixture_root) -> None:  # noqa: ANN001
    rc = tooling_dashboard_renderer.main(["--repo-root", str(fixture_root), "--output", "odylith/index.html"])
    assert rc == 0


def _first_non_default_option(frame, selector: str, excluded: set[str] | None = None) -> str:  # noqa: ANN001
    excluded_tokens = {"all", ""}
    if excluded:
        excluded_tokens |= {str(token) for token in excluded}
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => token.length > 0)
        """
    )
    for token in options:
        if token not in excluded_tokens:
            return str(token)
    return ""


def _first_filter_value_with_results(frame, selector: str, item_selector: str) -> tuple[str, int]:  # noqa: ANN001
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => token.length > 0 && token !== "all")
        """
    )
    for token in options:
        frame.locator(selector).select_option(token)
        count = frame.locator(item_selector).count()
        if count > 0:
            return str(token), count
    return "", 0


def _reset_select_to_first_option(frame, selector: str) -> None:  # noqa: ANN001
    values = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || ""))
        """
    )
    assert values, f"expected at least one option for {selector}"
    frame.locator(selector).select_option(str(values[0]))


def _select_registry_component_with_detail_actions(registry) -> tuple[str, str]:  # noqa: ANN001
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
            component_name = registry.locator("#detail .component-name").inner_text().strip()
            return component_id, component_name
    raise AssertionError("expected at least one Registry component with detail action chips")


def _select_radar_row_with_cross_surface_links(radar) -> str:  # noqa: ANN001
    row_buttons = radar.locator("button[data-idea-id]")
    count = row_buttons.count()
    for index in range(count):
        button = row_buttons.nth(index)
        idea_id = str(button.get_attribute("data-idea-id") or "").strip()
        if not idea_id:
            continue
        button.click()
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)
        registry_links = radar.locator("#detail a.chip-registry-component")
        diagram_links = radar.locator("#detail a.chip-topology-diagram")
        if registry_links.count() and diagram_links.count():
            return idea_id
    raise AssertionError("expected a Radar workstream with both Registry and Atlas detail links")


def _reset_radar_filters(radar) -> None:  # noqa: ANN001
    radar.locator("#query").fill("")
    for selector in ("#section", "#phase", "#activity", "#lane", "#priority"):
        radar.locator(selector).select_option("all")


def _select_radar_workstream(radar, idea_id: str) -> None:  # noqa: ANN001
    _reset_radar_filters(radar)
    radar.locator("#query").fill(idea_id)
    radar.locator(f'button[data-idea-id="{idea_id}"]').wait_for(timeout=15000)
    radar.locator(f'button[data-idea-id="{idea_id}"]').first.click()
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)
    radar.locator("#query").fill("")
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)


def _open_radar_topology_relations(radar) -> None:  # noqa: ANN001
    panel = radar.locator("#detail details.topology-relations-panel").first
    panel.wait_for(timeout=15000)
    if panel.get_attribute("open") is None:
        panel.evaluate("node => { node.open = true; }")
    panel.locator(".topology-relations").wait_for(timeout=15000)


def _wait_for_locator_count(page, frame_selector: str, locator_selector: str, expected: int) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ frameSelector, locatorSelector, expected }) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            if (!doc) return false;
            return doc.querySelectorAll(locatorSelector).length === expected;
        }""",
        arg={"frameSelector": frame_selector, "locatorSelector": locator_selector, "expected": expected},
        timeout=15000,
    )


def test_shell_tab_matrix_keeps_single_visible_pane_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
    assert response is not None and response.ok

    expectations = (
        ("radar", "#tab-radar", "#frame-radar", "Backlog Workstream Radar", "radar/radar.html"),
        ("registry", "#tab-registry", "#frame-registry", "Component Registry", "registry/registry.html"),
        ("casebook", "#tab-casebook", "#frame-casebook", "Casebook", "casebook/casebook.html"),
        ("atlas", "#tab-atlas", "#frame-atlas", "Atlas", "atlas/atlas.html"),
        ("compass", "#tab-compass", "#frame-compass", "Executive Compass", "compass/compass.html"),
    )

    for tab, tab_selector, frame_selector, heading_text, route_fragment in expectations:
        _click_visible(page.locator(tab_selector))
        _wait_for_shell_tab(page, tab)
        assert page.locator(tab_selector).get_attribute("aria-selected") == "true"
        _assert_single_visible_pane(page, frame_selector)
        page.frame_locator(frame_selector).locator("h1", has_text=heading_text).wait_for(timeout=15000)
        src = str(page.locator(frame_selector).get_attribute("src") or "")
        assert route_fragment in src

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_runtime_status_stays_hidden_across_tab_switches(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    page.frame_locator("#frame-atlas").locator("h1", has_text="Atlas").wait_for(timeout=15000)
    page.wait_for_function(
        """() => {
            const status = document.querySelector("#shellRuntimeStatus");
            return Boolean(status && status.hidden);
        }""",
        timeout=20000,
    )
    assert page.evaluate(
        """() => getComputedStyle(document.querySelector(".viewport"))
            .getPropertyValue("--runtime-status-offset")
            .trim()"""
    ) == "0px"

    page.locator("#tab-registry").click()
    page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    page.wait_for_function(
        """() => {
            const status = document.querySelector("#shellRuntimeStatus");
            return Boolean(status && status.hidden);
        }""",
        timeout=10000,
    )
    assert page.evaluate(
        """() => getComputedStyle(document.querySelector(".viewport"))
            .getPropertyValue("--runtime-status-offset")
            .trim()"""
    ) == "0px"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_compass_tab_dedupes_stale_runtime_status_to_compass_notice(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2020-01-02T17:06:12Z"
    payload["now_local_iso"] = "2020-01-02T09:06:12-08:00"
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
                assert response is not None and response.ok

                assert page.locator("#runtimeStatusReopen").count() == 0
                page.wait_for_function(
                    """() => {
                        const status = document.querySelector("#shellRuntimeStatus");
                        return Boolean(status && status.hidden && status.getAttribute("aria-hidden") === "true");
                    }""",
                    timeout=15000,
                )

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(
                          banner
                          && !banner.classList.contains("hidden")
                          && (banner.textContent || "").includes("Compass snapshot")
                        );
                    }""",
                    timeout=15000,
                )
                assert "ask agent `Refresh Compass runtime for this repo.`" in compass.locator("#status-banner").inner_text()

                page.locator("#tab-radar").click()
                _wait_for_shell_tab(page, "radar")
                page.wait_for_function(
                    """() => {
                        const node = document.querySelector("#shellRuntimeStatus");
                        return Boolean(node && node.hidden);
                    }""",
                    timeout=15000,
                )

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_shell_compass_tab_surfaces_failed_full_refresh_warning(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    payload["generated_utc"] = "2026-04-07T17:06:12Z"
    payload["warning"] = (
        "Requested Compass full refresh did not finish before the dashboard timeout. "
        "Showing the last successful shell-safe runtime snapshot from 2026-04-07T17:06:12Z."
    )
    runtime_contract = dict(payload.get("runtime_contract") or {})
    runtime_contract["refresh_profile"] = "shell-safe"
    runtime_contract["last_refresh_attempt"] = {
        "status": "failed",
        "requested_profile": "full",
        "applied_profile": "shell-safe",
        "attempted_utc": "2026-04-07T17:17:57Z",
        "reason": "timeout",
        "runtime_mode": "auto",
        "fallback_used": True,
    }
    payload["runtime_contract"] = runtime_contract
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
                assert response is not None and response.ok

                page.locator("#shellRuntimeStatus").wait_for(timeout=15000)
                assert page.locator("#shellRuntimeStatus").get_attribute("aria-hidden") == "false"
                assert page.locator("#shellRuntimeStatusTitle").inner_text().strip() == "Showing prior Compass snapshot"
                assert "Requested Compass full refresh did not finish before the dashboard timeout." in page.locator(
                    "#shellRuntimeStatusBody"
                ).inner_text()
                assert "--compass-refresh-profile full" in page.locator("#shellRuntimeStatusMeta").inner_text()

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_registry_search_filters_reset_and_detail_actions(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
    assert response is not None and response.ok

    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    baseline_count = registry.locator("button[data-component]").count()
    assert baseline_count > 1

    component_id, component_name = _select_registry_component_with_detail_actions(registry)
    _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
    assert component_name
    assert registry.locator("#detail a.detail-action-chip").count() > 0

    registry.locator("#search").fill(component_id.lower())
    _wait_for_locator_count(page, "#frame-registry", "button[data-component]", 1)
    registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
    assert registry.locator("#detail .component-name").inner_text().strip() == component_name

    registry.locator("#resetFilters").click()
    page.wait_for_function(
        """(frameSelector) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const search = doc && doc.querySelector("#search");
            return Boolean(doc) && search && search.value === "";
        }""",
        arg="#frame-registry",
        timeout=15000,
    )
    reset_count = registry.locator("button[data-component]").count()
    assert reset_count == baseline_count

    qualification_value = _first_non_default_option(registry, "#qualificationFilter")
    if not qualification_value:
        pytest.skip("Registry fixture does not currently expose non-default qualification filters.")
    registry.locator("#qualificationFilter").select_option(qualification_value)
    qualification_count = registry.locator("button[data-component]").count()
    assert 0 < qualification_count <= baseline_count

    registry.locator("#resetFilters").click()
    category_value = _first_non_default_option(registry, "#categoryFilter")
    if not category_value:
        pytest.skip("Registry fixture does not currently expose non-default category filters.")
    registry.locator("#categoryFilter").select_option(category_value)
    category_count = registry.locator("button[data-component]").count()
    assert 0 < category_count <= baseline_count

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_registry_memory_substrate_deep_links_select_the_right_component_detail(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    registry = page.frame_locator("#frame-registry")
    memory_components = (
        ("odylith-projection-bundle", "Odylith Projection Bundle"),
        ("odylith-projection-snapshot", "Odylith Projection Snapshot"),
        ("odylith-memory-backend", "Odylith Memory Backend"),
        ("odylith-remote-retrieval", "Odylith Remote Retrieval"),
        ("odylith-memory-contracts", "Odylith Memory Contracts"),
    )

    for component_id, component_name in memory_components:
        response = page.goto(
            base_url + f"/odylith/index.html?tab=registry&component={component_id}",
            wait_until="domcontentloaded",
        )
        assert response is not None and response.ok
        registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        registry.locator("#detail .component-name", has_text=component_name).wait_for(timeout=15000)
        assert registry.locator("#detail a.detail-action-chip").count() > 0

    registry.locator("#search").fill("memory")
    filtered_components = {
        str(component_id)
        for component_id in registry.locator("button[data-component]").evaluate_all(
            """nodes => nodes
              .map((node) => String(node.getAttribute("data-component") || "").trim())
              .filter(Boolean)
            """
        )
    }
    assert {
        "odylith-projection-bundle",
        "odylith-projection-snapshot",
        "odylith-memory-backend",
        "odylith-remote-retrieval",
        "odylith-memory-contracts",
    }.issubset(filtered_components)

    registry.locator("#search").fill("remote retrieval")
    registry.locator('button[data-component="odylith-remote-retrieval"]').wait_for(timeout=15000)
    assert registry.locator("button[data-component]").count() == 1
    registry.locator('button[data-component="odylith-remote-retrieval"]').click()
    _wait_for_shell_query_param(page, tab="registry", key="component", value="odylith-remote-retrieval")
    registry.locator("#detail .component-name", has_text="Odylith Remote Retrieval").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_search_selection_and_cross_surface_detail_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    baseline_count = radar.locator("button[data-idea-id]").count()
    assert baseline_count > 1

    idea_id = _select_radar_row_with_cross_surface_links(radar)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=idea_id)
    radar.locator("#detail .detail-title").wait_for(timeout=15000)
    assert radar.locator("#detail a.chip-registry-component").count() > 0
    assert radar.locator("#detail a.chip-topology-diagram").count() > 0

    radar.locator("#query").fill(idea_id)
    _wait_for_locator_count(page, "#frame-radar", "button[data-idea-id]", 1)
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)

    radar.locator("#query").fill("")
    phase_value, phase_count = _first_filter_value_with_results(radar, "#phase", "button[data-idea-id]")
    if not phase_value:
        pytest.skip("Radar fixture does not currently expose non-default phase filters with results.")
    assert 0 < phase_count <= baseline_count

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_topology_relation_chips_route_to_their_own_workstream_ids(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    source_id = "B-048"
    _select_radar_workstream(radar, source_id)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
    _open_radar_topology_relations(radar)
    relation_ids = [
        str(token)
        for token in radar.locator("#detail").evaluate(
            """(node) => Array.from(
                new Set(
                  Array.from(node.querySelectorAll('details.topology-relations-panel .topology-relations [data-link-idea]'))
                    .map((chip) => String(chip.getAttribute('data-link-idea') || '').trim())
                    .filter(Boolean)
                )
            )"""
        )
    ]
    if not relation_ids:
        pytest.skip("Radar fixture does not currently expose B-048 relation chips.")

    for target_id in relation_ids:
        _select_radar_workstream(radar, source_id)
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
        _open_radar_topology_relations(radar)
        chip = radar.locator(f'#detail [data-link-idea="{target_id}"]').first
        chip.wait_for(timeout=15000)
        chip.evaluate("node => node.click()")
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=target_id).wait_for(timeout=15000)
        radar.locator(f'button[data-idea-id="{target_id}"].active').wait_for(timeout=15000)
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=target_id)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_topology_relation_clicks_self_heal_incompatible_filters(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    source_id = "B-048"
    source_section = "execution"
    _select_radar_workstream(radar, source_id)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=source_id)
    _open_radar_topology_relations(radar)
    target_id = str(
        radar.locator("#detail").evaluate(
            """(node) => {
                const rows = Array.from(node.querySelectorAll('details.topology-relations-panel .topology-rel-row'));
                const childrenRow = rows.find(
                  (row) => String(row.querySelector('.topology-rel-title')?.textContent || '').trim().toLowerCase() === 'children'
                );
                const chip = childrenRow?.querySelector('[data-link-idea]');
                return chip ? String(chip.getAttribute('data-link-idea') || '').trim() : '';
            }"""
        )
        or ""
    ).strip()
    if not target_id:
        pytest.skip("Radar fixture does not currently expose a B-048 child relation chip.")

    radar.locator("#section").select_option(source_section)
    radar.locator("#query").fill(source_id)
    _open_radar_topology_relations(radar)
    radar.locator(f'#detail [data-link-idea="{target_id}"]').first.wait_for(timeout=15000)
    assert radar.locator(f'button[data-idea-id="{target_id}"]').count() == 0

    radar.locator(f'#detail [data-link-idea="{target_id}"]').first.evaluate("node => node.click()")
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=target_id).wait_for(timeout=15000)
    radar.locator(f'button[data-idea-id="{target_id}"].active').wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=target_id)
    assert radar.locator("#query").input_value() == ""
    assert radar.locator("#section").input_value() == "all"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_b058_memory_diagram_chip_routes_to_d025(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar&workstream=B-058", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text="B-058").wait_for(timeout=15000)
    radar.locator("#detail").evaluate(
        """(node) => {
            const link = Array.from(
              node.querySelectorAll('a.chip-topology-diagram[href*="diagram=D-025"]')
            ).find((candidate) => candidate instanceof HTMLElement && candidate.offsetParent !== null);
            if (!link) {
              throw new Error("missing visible D-025 topology chip");
            }
            link.click();
        }"""
    )

    _wait_for_shell_tab(page, "atlas")
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-025")
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_search_filters_and_empty_state(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    filter_geometry = casebook.locator(".filters-bar").evaluate(
        """node => {
            const bar = node.getBoundingClientRect();
            const search = node.querySelector('#searchInput').getBoundingClientRect();
            const severity = node.querySelector('#severityFilter').getBoundingClientRect();
            const status = node.querySelector('#statusFilter').getBoundingClientRect();
            return {
              barLeft: bar.left,
              barRight: bar.right,
              searchWidth: search.width,
              severityWidth: severity.width,
              statusWidth: status.width,
              rightSlack: bar.right - status.right,
            };
        }"""
    )
    assert abs(filter_geometry["searchWidth"] - filter_geometry["severityWidth"]) <= 2
    assert abs(filter_geometry["severityWidth"] - filter_geometry["statusWidth"]) <= 2
    assert filter_geometry["rightSlack"] <= 16

    baseline_count = casebook.locator("button.bug-row").count()
    assert baseline_count > 1

    first_bug = casebook.locator("button.bug-row").first
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    assert bug_route
    assert bug_title
    first_bug.click()
    _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)
    casebook.locator("#detailPane .section-heading", has_text="Odylith Agent Learnings").wait_for(timeout=15000)
    assert casebook.locator("#detailPane").get_by_text("Human Readout", exact=True).count() == 0
    assert casebook.locator("#detailPane").get_by_text("Nearby Change Guidance", exact=True).count() == 0
    assert casebook.locator("#detailPane").get_by_text("Inspect Next", exact=True).count() == 0

    severity_value = _first_non_default_option(casebook, "#severityFilter")
    if not severity_value:
        pytest.skip("Casebook fixture does not currently expose non-default severity filters.")
    casebook.locator("#severityFilter").select_option(severity_value)
    severity_count = casebook.locator("button.bug-row").count()
    assert 0 < severity_count <= baseline_count

    _reset_select_to_first_option(casebook, "#severityFilter")
    status_value = _first_non_default_option(casebook, "#statusFilter")
    if not status_value:
        pytest.skip("Casebook fixture does not currently expose non-default status filters.")
    casebook.locator("#statusFilter").select_option(status_value)
    status_count = casebook.locator("button.bug-row").count()
    assert 0 < status_count <= baseline_count

    _reset_select_to_first_option(casebook, "#statusFilter")
    casebook.locator("#searchInput").fill("zzzzzz-no-casebook-match")
    casebook.locator("#listMeta", has_text="Visible: 0").wait_for(timeout=15000)
    assert casebook.locator("button.bug-row").count() == 0
    assert casebook.locator("#listMeta").inner_text().strip() == "Visible: 0"
    assert casebook.locator("#detailPane").inner_text().strip() == ""

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_first_bug_rows_load_details_without_dead_shards(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

    sample_rows = casebook.locator("button.bug-row").evaluate_all(
        """nodes => nodes.slice(0, 6).map((node) => ({
          route: (node.getAttribute('data-bug') || '').trim(),
          title: ((node.querySelector('.bug-row-title') && node.querySelector('.bug-row-title').textContent) || '').trim(),
        }))"""
    )
    assert sample_rows, "expected visible Casebook bug rows"

    for item in sample_rows:
        bug_route = str(item.get("route") or "").strip()
        bug_title = str(item.get("title") or "").strip()
        assert bug_route
        assert bug_title
        casebook.locator(f'button.bug-row[data-bug="{bug_route}"]').click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
        casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
        casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_navigation_filters_and_context_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    baseline_total = _atlas_total(atlas)
    assert baseline_total > 1

    initial_diagram = atlas.locator("#diagramId").inner_text().strip()
    initial_title = atlas.locator("#diagramTitle").inner_text().strip()
    assert initial_diagram
    assert initial_title

    atlas.locator("#nextDiagram").click()
    atlas.locator("#diagramId").wait_for(timeout=15000)
    next_diagram = atlas.locator("#diagramId").inner_text().strip()
    assert next_diagram
    assert next_diagram != initial_diagram

    atlas.locator("#prevDiagram").click()
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)
    atlas.locator("#search").fill(initial_title)
    page.wait_for_function(
        """(frameSelector) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const total = doc && doc.querySelector("#statTotal");
            return Boolean(total) && total.textContent.trim() === "1";
        }""",
        arg="#frame-atlas",
        timeout=15000,
    )
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)

    title_tokens = [token for token in re.findall(r"[A-Za-z0-9]+", initial_title) if len(token) >= 4]
    short_title = (max(title_tokens, key=len)[:6] if title_tokens else initial_title[:6]).strip()
    atlas.locator("#search").fill(short_title)
    page.wait_for_function(
        """({ frameSelector, baselineTotal }) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            const total = doc && doc.querySelector("#statTotal");
            if (!total) return false;
            const value = Number.parseInt(total.textContent.trim(), 10);
            return Number.isFinite(value) && value >= 1 && value < baselineTotal;
        }""",
        arg={"frameSelector": "#frame-atlas", "baselineTotal": baseline_total},
        timeout=15000,
    )
    atlas.locator("#diagramId", has_text=initial_diagram).wait_for(timeout=15000)

    diagram_ids = atlas.locator("button[data-diagram]").evaluate_all(
        """nodes => nodes
          .map((node) => (node.getAttribute("data-diagram") || "").trim())
          .filter((token) => token.length > 0)
        """
    )
    searchable_diagram = initial_diagram
    short_diagram_token = ""
    for token in diagram_ids:
        match = re.search(r"-(\d+)$", str(token))
        if not match:
            continue
        suffix = match.group(1)
        stripped = str(int(suffix))
        if len(stripped) < 2 or stripped == suffix:
            continue
        if sum(1 for other in diagram_ids if stripped in str(other)) != 1:
            continue
        searchable_diagram = str(token)
        short_diagram_token = stripped
        break

    if searchable_diagram != initial_diagram:
        atlas.locator(f'button[data-diagram="{searchable_diagram}"]').click()
        atlas.locator("#diagramId", has_text=searchable_diagram).wait_for(timeout=15000)

    diagram_suffix = searchable_diagram.split("-", 1)[-1].strip()
    id_queries = [diagram_suffix, f"-{diagram_suffix}"]
    if short_diagram_token and short_diagram_token not in id_queries:
        id_queries.insert(0, short_diagram_token)
        for query in id_queries:
            atlas.locator("#search").fill(query)
            page.wait_for_function(
                """({ frameSelector, baselineTotal }) => {
                    const frame = document.querySelector(frameSelector);
                    const doc = frame && frame.contentDocument;
                    const total = doc && doc.querySelector("#statTotal");
                    if (!total) return false;
                    const value = Number.parseInt(total.textContent.trim(), 10);
                    return Number.isFinite(value) && value >= 1 && value < baselineTotal;
                }""",
                arg={"frameSelector": "#frame-atlas", "baselineTotal": baseline_total},
                timeout=15000,
            )
            atlas.locator("#diagramId", has_text=searchable_diagram).wait_for(timeout=15000)

    atlas.locator("#search").fill("")
    workstream_value = _first_non_default_option(atlas, "#workstreamFilter")
    if not workstream_value:
        pytest.skip("Atlas fixture does not currently expose non-default workstream filters.")
    atlas.locator("#workstreamFilter").select_option(workstream_value)
    filtered_total = _atlas_total(atlas)
    assert 0 < filtered_total <= baseline_total
    _wait_for_shell_query_param(page, tab="atlas", key="workstream", value=workstream_value)

    active_workstream_links = atlas.locator("#activeWorkstreamLinks a.workstream-pill-link").count()
    owner_workstream_links = atlas.locator("#ownerWorkstreamLinks a.workstream-pill-link").count()
    assert active_workstream_links > 0 or owner_workstream_links > 0
    assert atlas.locator("#registryLinks a").count() > 0

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_d025_memory_substrate_route_exposes_governed_registry_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=atlas&diagram=D-025", wait_until="domcontentloaded")
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-025").wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="atlas", key="diagram", value="D-025")

    registry_hrefs = [
        str(href)
        for href in atlas.locator("#registryLinks a").evaluate_all(
            """nodes => nodes
              .map((node) => String(node.getAttribute("href") || "").trim())
              .filter(Boolean)
            """
        )
    ]
    assert registry_hrefs, "expected D-025 to expose Registry component links"
    for component_id in (
        "odylith-projection-bundle",
        "odylith-projection-snapshot",
        "odylith-memory-backend",
        "odylith-remote-retrieval",
        "odylith-memory-contracts",
    ):
        assert any(f"component={component_id}" in href for href in registry_hrefs), (
            f"expected D-025 registry links to include {component_id}"
        )

    workstream_tokens = {
        str(token)
        for token in atlas.locator(
            "#activeWorkstreamLinks a.workstream-pill-link, "
            "#ownerWorkstreamLinks a.workstream-pill-link, "
            "#historicalWorkstreamLinks a.workstream-pill-link"
        ).evaluate_all(
            """nodes => nodes
              .map((node) => String(node.textContent || "").trim())
              .filter(Boolean)
            """
        )
    }
    assert {"B-058", "B-059"}.issubset(workstream_tokens)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_scope_window_and_detail_behavior_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")
    _wait_for_compass_brief_state(page, window_token="24h", scope_label="Global")
    global_24h_meta = _compass_brief_metadata(compass)
    assert global_24h_meta["source"] in {"provider", "cache", "deterministic"}
    assert global_24h_meta["hasNotice"] == ("true" if global_24h_meta["source"] == "deterministic" else "false")
    assert global_24h_meta["fingerprint"]

    scope_value = _first_non_default_option(compass, "#scope-select", excluded={""})
    if not scope_value or not re.fullmatch(r"B-\d{3,}", scope_value):
        pytest.skip("Compass fixture does not currently expose non-global workstream scope options.")
    compass.locator("#scope-select").select_option(scope_value)
    _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
    compass.locator("#scope-pill", has_text=scope_value).wait_for(timeout=15000)
    _wait_for_compass_brief_state(page, window_token="24h", scope_label=scope_value)
    scoped_24h_meta = _compass_brief_metadata(compass)
    assert scoped_24h_meta["source"] in {"provider", "cache", "deterministic"}
    assert scoped_24h_meta["hasNotice"] == ("true" if scoped_24h_meta["source"] == "deterministic" else "false")
    assert scoped_24h_meta["fingerprint"]
    assert scoped_24h_meta["fingerprint"] != global_24h_meta["fingerprint"]

    summary_rows = compass.locator("tr.ws-summary-row")
    assert summary_rows.count() > 0
    target_row = compass.locator(f'tr.ws-summary-row[data-ws-id="{scope_value}"]').first
    if target_row.count() == 0:
        target_row = summary_rows.first
    target_workstream = str(target_row.get_attribute("data-ws-id") or "").strip()
    assert target_workstream
    target_row.click()
    compass.locator(f'tr.ws-detail-row.is-open[data-ws-detail="{target_workstream}"]').wait_for(timeout=15000)

    compass.locator('button[data-window="48h"]').click()
    _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
    _assert_compass_live_state(compass, window_token="48h")
    _wait_for_compass_brief_state(page, window_token="48h", scope_label=scope_value)
    scoped_48h_meta = _compass_brief_metadata(compass)
    assert scoped_48h_meta["source"] in {"provider", "cache", "deterministic"}
    assert scoped_48h_meta["hasNotice"] == ("true" if scoped_48h_meta["source"] == "deterministic" else "false")
    assert scoped_48h_meta["fingerprint"]
    assert scoped_48h_meta["fingerprint"] != scoped_24h_meta["fingerprint"]

    compass.locator("#scope-global").click()
    page.wait_for_function(
        """() => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "compass"
                && !url.searchParams.has("scope");
            } catch (_error) {
              return false;
            }
        }""",
        timeout=15000,
    )
    compass.locator("#scope-pill", has_text="Global").wait_for(timeout=15000)
    _wait_for_compass_brief_state(page, window_token="48h", scope_label="Global")
    global_48h_meta = _compass_brief_metadata(compass)
    assert global_48h_meta["source"] in {"provider", "cache", "deterministic"}
    assert global_48h_meta["hasNotice"] == ("true" if global_48h_meta["source"] == "deterministic" else "false")
    assert global_48h_meta["fingerprint"]
    assert global_48h_meta["fingerprint"] != global_24h_meta["fingerprint"]
    assert global_48h_meta["fingerprint"] != scoped_48h_meta["fingerprint"]

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_explicit_full_compass_refresh_artifacts_do_not_show_deterministic_brief(
    tmp_path,
) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    baseline_payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    stale_payload = json.loads(json.dumps(baseline_payload))
    stale_payload["generated_utc"] = "2020-01-02T16:45:00Z"
    stale_payload["standup_brief"] = {
        "24h": {
            "status": "ready",
            "source": "deterministic",
            "fingerprint": "stale-24h",
            "generated_utc": "2020-01-02T16:45:00Z",
            "sections": [],
            "notice": {
                "reason": "provider_deferred",
                "title": "Showing deterministic local brief",
                "message": "Compass rendered a deterministic local brief from the current fact packet because live AI narration stayed deferred during this refresh.",
            },
            "evidence_lookup": {},
        },
        "48h": {
            "status": "ready",
            "source": "deterministic",
            "fingerprint": "stale-48h",
            "generated_utc": "2020-01-02T16:45:00Z",
            "sections": [],
            "notice": {
                "reason": "provider_deferred",
                "title": "Showing deterministic local brief",
                "message": "Compass rendered a deterministic local brief from the current fact packet because live AI narration stayed deferred during this refresh.",
            },
            "evidence_lookup": {},
        },
    }
    stale_payload["standup_brief_scoped"] = {"24h": {}, "48h": {}}
    runtime_json_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(stale_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    fresh_payload = json.loads(json.dumps(baseline_payload))
    fresh_payload["generated_utc"] = "2026-04-08T01:00:00Z"
    fresh_payload["now_local_iso"] = "2026-04-07T18:00:00-07:00"
    runtime_contract = fresh_payload.get("runtime_contract") if isinstance(fresh_payload.get("runtime_contract"), dict) else {}
    runtime_contract["refresh_profile"] = "full"
    runtime_contract["last_refresh_attempt"] = {
        "status": "passed",
        "requested_profile": "full",
        "applied_profile": "full",
        "runtime_mode": "auto",
        "reason": "",
        "attempted_utc": fresh_payload["generated_utc"],
        "fallback_used": False,
    }
    fresh_payload["runtime_contract"] = runtime_contract

    def _normalize_brief(brief: dict[str, object], *, source: str, generated_utc: str) -> dict[str, object]:
        normalized = dict(brief)
        normalized["status"] = "ready"
        normalized["source"] = source
        normalized["generated_utc"] = generated_utc
        normalized.pop("notice", None)
        normalized.pop("diagnostics", None)
        return normalized

    standup_brief = fresh_payload.get("standup_brief") if isinstance(fresh_payload.get("standup_brief"), dict) else {}
    for window in ("24h", "48h"):
        brief = standup_brief.get(window)
        if isinstance(brief, dict):
            standup_brief[window] = _normalize_brief(brief, source="provider", generated_utc=fresh_payload["generated_utc"])
    fresh_payload["standup_brief"] = standup_brief

    standup_brief_scoped = (
        fresh_payload.get("standup_brief_scoped")
        if isinstance(fresh_payload.get("standup_brief_scoped"), dict)
        else {}
    )
    for window in ("24h", "48h"):
        scoped_map = standup_brief_scoped.get(window)
        if not isinstance(scoped_map, dict):
            continue
        for ws_id, brief in list(scoped_map.items()):
            if isinstance(brief, dict):
                scoped_map[ws_id] = _normalize_brief(brief, source="cache", generated_utc=fresh_payload["generated_utc"])
    fresh_payload["standup_brief_scoped"] = standup_brief_scoped
    runtime_json_path.write_text(json.dumps(fresh_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(fresh_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    assert fresh_payload["standup_brief"]["24h"]["source"] in {"provider", "cache"}
    assert "notice" not in fresh_payload["standup_brief"]["24h"]
    assert fresh_payload["standup_brief"]["48h"]["source"] in {"provider", "cache"}
    assert "notice" not in fresh_payload["standup_brief"]["48h"]

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(page, window_token="24h", scope_label="Global")
                meta_24h = _compass_brief_metadata(compass)
                assert meta_24h["source"] in {"provider", "cache"}
                assert meta_24h["hasNotice"] == "false"
                assert "deterministic local brief" not in compass.locator("#digest-list").inner_text().lower()

                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                _assert_compass_live_state(compass, window_token="48h")
                _wait_for_compass_brief_state(page, window_token="48h", scope_label="Global")
                meta_48h = _compass_brief_metadata(compass)
                assert meta_48h["source"] in {"provider", "cache"}
                assert meta_48h["hasNotice"] == "false"

                scope_value = _first_non_default_option(compass, "#scope-select", excluded={""})
                if scope_value and re.fullmatch(r"B-\d{3,}", scope_value):
                    compass.locator("#scope-select").select_option(scope_value)
                    _wait_for_shell_query_param(page, tab="compass", key="scope", value=scope_value)
                    _wait_for_compass_brief_state(page, window_token="48h", scope_label=scope_value)
                    scoped_meta = _compass_brief_metadata(compass)
                    assert scoped_meta["source"] in {"provider", "cache"}
                    assert scoped_meta["hasNotice"] == "false"
                    assert "deterministic local brief" not in compass.locator("#digest-list").inner_text().lower()

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_shell_safe_compass_refresh_artifacts_use_provider_backed_global_briefs_when_available(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    shutil.rmtree(runtime_dir / "history", ignore_errors=True)
    for path in (runtime_dir / "current.v1.json", runtime_dir / "current.v1.js"):
        path.unlink(missing_ok=True)

    provider = _CompassProvider()

    def _provider_from_config(  # noqa: ANN001
        config: odylith_reasoning.ReasoningConfig,
        *,
        repo_root=None,
        require_auto_mode=True,
        allow_implicit_local_provider=False,
    ):
        assert repo_root == fixture_root
        assert require_auto_mode is False
        assert allow_implicit_local_provider is True
        return provider

    monkeypatch.setattr(odylith_reasoning, "provider_from_config", _provider_from_config)

    rc = render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
            "--refresh-profile",
            "shell-safe",
        ]
    )
    assert rc == 0
    assert provider.calls >= 2
    _render_tooling_shell_fixture(fixture_root)

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                _assert_compass_live_state(compass, window_token="24h")
                _wait_for_compass_brief_state(page, window_token="24h", scope_label="Global")
                meta_24h = _compass_brief_metadata(compass)
                assert meta_24h["source"] == "provider"
                assert meta_24h["hasNotice"] == "false"
                assert "deterministic local brief" not in compass.locator("#digest-list").inner_text().lower()

                compass.locator('button[data-window="48h"]').click()
                _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
                _assert_compass_live_state(compass, window_token="48h")
                _wait_for_compass_brief_state(page, window_token="48h", scope_label="Global")
                meta_48h = _compass_brief_metadata(compass)
                assert meta_48h["source"] == "provider"
                assert meta_48h["hasNotice"] == "false"
                assert "deterministic local brief" not in compass.locator("#digest-list").inner_text().lower()

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_casebook_detail_stacks_cleanly_in_compact_viewport(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

    first_bug = casebook.locator("button.bug-row").first
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    assert bug_route
    assert bug_title

    first_bug.click()
    _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-section-human").wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-section-agent").wait_for(timeout=15000)

    layout = casebook.locator("#detailPane").evaluate(
        """(node) => {
            const human = node.querySelector('.detail-section-human');
            const agent = node.querySelector('.detail-section-agent');
            const humanBox = human ? human.getBoundingClientRect() : null;
            const agentBox = agent ? agent.getBoundingClientRect() : null;
            return {
              clientWidth: node.clientWidth,
              scrollWidth: node.scrollWidth,
              humanTop: humanBox ? humanBox.top : 0,
              humanBottom: humanBox ? humanBox.bottom : 0,
              agentTop: agentBox ? agentBox.top : 0,
              briefCardCount: node.querySelectorAll('.brief-card').length,
              agentBlockCount: node.querySelectorAll('.agent-band-block').length,
            };
        }"""
    )
    assert layout["briefCardCount"] >= 1
    assert layout["agentBlockCount"] >= 1
    assert layout["scrollWidth"] - layout["clientWidth"] <= 16
    assert layout["agentTop"] >= layout["humanBottom"] - 2

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_live_window_anchors_to_loaded_snapshot_time(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    history_dir = fixture_root / "odylith" / "compass" / "runtime" / "history"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    event = dict((payload.get("timeline_events") or [])[0])
    event["id"] = "stale-anchor:event"
    event["kind"] = "implementation"
    event["summary"] = "Stale-anchor implementation event."
    event["ts_iso"] = "2020-01-02T08:45:00-08:00"
    event["author"] = "assistant"
    event["files"] = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]
    event["workstreams"] = []

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "stale-anchor:tx"
    transaction["transaction_id"] = "stale-anchor:tx"
    transaction["headline"] = "Stale-anchor transaction"
    transaction["start_ts_iso"] = "2020-01-02T08:00:00-08:00"
    transaction["end_ts_iso"] = "2020-01-02T08:45:00-08:00"
    transaction["event_count"] = 1
    transaction["files_count"] = 1
    transaction["files"] = list(event["files"])
    transaction["workstreams"] = []
    transaction["events"] = [event]

    payload["generated_utc"] = "2020-01-02T16:45:00Z"
    payload["now_local_iso"] = "2020-01-02T08:45:00-08:00"
    payload["timeline_events"] = [event]
    payload["timeline_transactions"] = [transaction]
    history = payload.get("history") if isinstance(payload.get("history"), dict) else {}
    history["dates"] = ["2020-01-02", "2020-01-01", "2019-12-31"]
    history["restored_dates"] = []
    payload["history"] = history

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    for token in ("2020-01-01", "2019-12-31"):
        snapshot = dict(payload)
        snapshot["timeline_events"] = []
        snapshot["timeline_transactions"] = []
        snapshot["history"] = {
            "retention_days": 15,
            "dates": ["2020-01-02", "2020-01-01", "2019-12-31"],
            "restored_dates": [],
            "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
        }
        (history_dir / f"{token}.v1.json").write_text(json.dumps(snapshot, indent=2) + "\n", encoding="utf-8")

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(
                          banner
                          && !banner.classList.contains("hidden")
                          && (banner.textContent || "").includes("Compass snapshot")
                        );
                    }""",
                    timeout=15000,
                )
                assert "ask agent `Refresh Compass runtime for this repo.`" in compass.locator("#status-banner").inner_text()
                assert compass.locator("#status-banner").evaluate("node => getComputedStyle(node).whiteSpace") == "nowrap"
                assert compass.locator("#timeline").evaluate("node => getComputedStyle(node).minHeight") == "0px"
                assert compass.locator("#timeline").evaluate("node => getComputedStyle(node).alignContent") == "start"
                assert compass.locator("#timeline .timeline-day").first.evaluate("node => getComputedStyle(node).alignContent") == "start"
                compass.locator("#timeline .tx-headline", has_text="Stale-anchor implementation event.").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2020-01-02").wait_for(timeout=15000)
                compass.locator("#timeline .empty", has_text="No audit events in this scope and window.").wait_for(state="detached", timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_archived_timeline_day_loads_from_embedded_history(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    history_dir = runtime_dir / "history"
    archive_dir = history_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)

    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    history_js_path = history_dir / "embedded.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    archived_day = "2026-04-04"
    live_day = "2026-04-05"
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    archived_event = dict((payload.get("timeline_events") or [])[0])
    archived_event["id"] = "archived:event"
    archived_event["kind"] = "implementation"
    archived_event["summary"] = "Archived Compass timeline event."
    archived_event["ts_iso"] = "2026-04-04T11:20:00-07:00"
    archived_event["author"] = "assistant"
    archived_event["files"] = list(files)
    archived_event["workstreams"] = []

    archived_tx = dict((payload.get("timeline_transactions") or [])[0])
    archived_tx["id"] = "archived:tx"
    archived_tx["transaction_id"] = "archived:tx"
    archived_tx["headline"] = "Archived Compass timeline transaction"
    archived_tx["start_ts_iso"] = "2026-04-04T11:00:00-07:00"
    archived_tx["end_ts_iso"] = "2026-04-04T11:20:00-07:00"
    archived_tx["event_count"] = 1
    archived_tx["files_count"] = len(files)
    archived_tx["files"] = list(files)
    archived_tx["workstreams"] = []
    archived_tx["events"] = [archived_event]

    live_payload = dict(payload)
    live_payload["generated_utc"] = "2026-04-05T20:20:00Z"
    live_payload["now_local_iso"] = "2026-04-05T13:20:00-07:00"
    live_payload["history"] = {
        "retention_days": 1,
        "dates": [live_day],
        "restored_dates": [],
        "archive": {
            "compressed": True,
            "path": "archive",
            "count": 1,
            "dates": [archived_day],
            "newest_date": archived_day,
            "oldest_date": archived_day,
        },
    }

    archived_payload = dict(payload)
    archived_payload["generated_utc"] = "2026-04-04T18:20:00Z"
    archived_payload["now_local_iso"] = "2026-04-04T11:20:00-07:00"
    archived_payload["timeline_events"] = [archived_event]
    archived_payload["timeline_transactions"] = [archived_tx]
    archived_payload["history"] = dict(live_payload["history"])

    runtime_json_path.write_text(json.dumps(live_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(live_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    (archive_dir / f"{archived_day}.v1.json.gz").write_bytes(
        gzip.compress((json.dumps(archived_payload, indent=2) + "\n").encode("utf-8"), compresslevel=9)
    )
    history_js_path.write_text(
        "window.__ODYLITH_COMPASS_HISTORY__ = " + json.dumps(
            {
                "version": "v1",
                "generated_utc": live_payload["generated_utc"],
                "retention_days": 1,
                "dates": [live_day],
                "restored_dates": [],
                "archive": live_payload["history"]["archive"],
                "snapshots": {
                    archived_day: archived_payload,
                },
            },
            separators=(",", ":"),
        ) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=24h&date={archived_day}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text=archived_day).wait_for(timeout=15000)
                assert compass.locator("#timeline .hour-row").count() > 0
                compass.locator("#timeline .empty", has_text="No snapshot available for this day.").wait_for(
                    state="detached",
                    timeout=15000,
                )

                bad_responses[:] = [
                    entry for entry in bad_responses
                    if not entry.endswith(f"/odylith/compass/runtime/history/{archived_day}.v1.json")
                ]
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_timeline_mixed_local_batch_falls_back_to_transaction_headline(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    scope_id = "B-020"
    scope_row = dict((payload.get("current_workstreams") or [])[0])
    scope_row["idea_id"] = scope_id
    scope_row["status"] = "implementation"
    scope_row["title"] = "Timeline audit headline trust"
    payload["current_workstreams"] = [scope_row]

    files = [
        "src/odylith/runtime/evaluation/odylith_benchmark_runner.py",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js",
        "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-surface.v1.css",
        "tests/integration/runtime/test_surface_browser_deep.py",
    ]
    event_specs = (
        ("mixed-local:event:1", "Modified src/odylith/runtime/evaluation/odylith_benchmark_runner.py", "2026-04-02T13:59:34-07:00", files[0]),
        ("mixed-local:event:2", "Modified src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js", "2026-04-02T13:59:44-07:00", files[1]),
        ("mixed-local:event:3", "Modified src/odylith/runtime/surfaces/templates/compass_dashboard/compass-style-surface.v1.css", "2026-04-02T13:59:52-07:00", files[2]),
        ("mixed-local:event:4", "Modified tests/integration/runtime/test_surface_browser_deep.py", "2026-04-02T14:00:05-07:00", files[3]),
    )
    events = []
    base_event = dict((payload.get("timeline_events") or [])[0])
    for event_id, summary, ts_iso, file_path in event_specs:
        event = dict(base_event)
        event["id"] = event_id
        event["kind"] = "local_change"
        event["summary"] = summary
        event["ts_iso"] = ts_iso
        event["author"] = "local"
        event["files"] = [file_path]
        event["workstreams"] = [scope_id]
        events.append(event)

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "mixed-local:tx"
    transaction["transaction_id"] = "mixed-local:tx"
    transaction["headline"] = "Updated product code + integration tests for B-020"
    transaction["start_ts_iso"] = "2026-04-02T13:59:34-07:00"
    transaction["end_ts_iso"] = "2026-04-02T14:00:05-07:00"
    transaction["event_count"] = len(events)
    transaction["files_count"] = len(files)
    transaction["files"] = list(files)
    transaction["workstreams"] = [scope_id]
    transaction["events"] = list(reversed(events))

    payload["generated_utc"] = "2026-04-02T21:00:22Z"
    payload["now_local_iso"] = "2026-04-02T14:00:22-07:00"
    payload["timeline_events"] = list(reversed(events))
    payload["timeline_transactions"] = [transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": ["2026-04-02"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline .tx-headline", has_text=transaction["headline"]).wait_for(timeout=15000)
                timeline_text = compass.locator("#timeline").inner_text()
                assert "Advanced shared infra and env-manifest wiring in the latest audit." not in timeline_text
                assert "Reworked Compass's inline audit narrative." not in timeline_text

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_scoped_live_view_prefers_latest_non_empty_audit_day(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    scope_id = "B-777"
    scope_row = dict((payload.get("current_workstreams") or [])[0])
    scope_row["idea_id"] = scope_id
    scope_row["status"] = "implementation"
    scope_row["title"] = "Scoped audit-day fallback regression"
    payload["current_workstreams"] = [scope_row]

    event = dict((payload.get("timeline_events") or [])[0])
    event["id"] = "scoped-fallback:event"
    event["kind"] = "implementation"
    event["summary"] = "Scoped fallback implementation event."
    event["ts_iso"] = "2026-04-01T10:15:00-07:00"
    event["author"] = "assistant"
    event["workstreams"] = [scope_id]
    event["files"] = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js"]

    transaction = dict((payload.get("timeline_transactions") or [])[0])
    transaction["id"] = "scoped-fallback:tx"
    transaction["transaction_id"] = "scoped-fallback:tx"
    transaction["headline"] = "Scoped fallback transaction"
    transaction["start_ts_iso"] = "2026-04-01T10:00:00-07:00"
    transaction["end_ts_iso"] = "2026-04-01T10:15:00-07:00"
    transaction["event_count"] = 1
    transaction["files_count"] = 1
    transaction["files"] = list(event["files"])
    transaction["workstreams"] = [scope_id]
    transaction["events"] = [event]

    payload["generated_utc"] = "2026-04-02T19:13:23Z"
    payload["now_local_iso"] = "2026-04-02T12:13:23-07:00"
    payload["timeline_events"] = [event]
    payload["timeline_transactions"] = [transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": ["2026-04-02", "2026-04-01", "2026-03-31"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&scope={scope_id}&window=48h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#scope-pill", has_text=scope_id).wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2026-04-01").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text="2026-04-02").wait_for(state="detached", timeout=15000)
                compass.locator("#timeline", has_text="Scoped fallback implementation event.").wait_for(timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_live_selected_audit_day_hides_future_hours(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    current_day = "2026-04-05"
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    event = dict((payload.get("timeline_events") or [0])[0] if (payload.get("timeline_events") or []) else {})
    if not event:
        event = {"id": "", "kind": "", "summary": "", "ts_iso": "", "author": "", "files": [], "workstreams": []}
    event["id"] = "live-horizon:event"
    event["kind"] = "implementation"
    event["summary"] = "Live current-day hour horizon event."
    event["ts_iso"] = "2026-04-05T00:29:00-07:00"
    event["author"] = "assistant"
    event["files"] = list(files)
    event["workstreams"] = ["B-004"]

    transaction = dict((payload.get("timeline_transactions") or [0])[0] if (payload.get("timeline_transactions") or []) else {})
    if not transaction:
        transaction = {
            "id": "",
            "transaction_id": "",
            "headline": "",
            "start_ts_iso": "",
            "end_ts_iso": "",
            "event_count": 0,
            "files_count": 0,
            "files": [],
            "workstreams": [],
            "events": [],
        }
    transaction["id"] = "live-horizon:tx"
    transaction["transaction_id"] = "live-horizon:tx"
    transaction["headline"] = "Live current-day Compass horizon transaction"
    transaction["start_ts_iso"] = "2026-04-05T00:17:00-07:00"
    transaction["end_ts_iso"] = "2026-04-05T00:29:00-07:00"
    transaction["event_count"] = 1
    transaction["files_count"] = len(files)
    transaction["files"] = list(files)
    transaction["workstreams"] = ["B-004"]
    transaction["events"] = [event]

    payload["generated_utc"] = "2026-04-05T07:29:00Z"
    payload["now_local_iso"] = "2026-04-05T00:29:00-07:00"
    payload["timeline_events"] = [event]
    payload["timeline_transactions"] = [transaction]
    payload["history"] = {
        "retention_days": 15,
        "dates": [current_day, "2026-04-04"],
        "restored_dates": [],
        "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
    }

    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + f"/odylith/index.html?tab=compass&window=48h&date=live&audit_day={current_day}",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline .timeline-day-title", has_text=current_day).wait_for(timeout=15000)
                compass.locator("#timeline .hour-label", has_text="00:00").wait_for(timeout=15000)
                compass.locator("#timeline .hour-label", has_text="01:00").wait_for(state="detached", timeout=15000)
                compass.locator("#timeline .hour-label", has_text="23:00").wait_for(state="detached", timeout=15000)
                compass.locator("#timeline", has_text=event["summary"]).wait_for(timeout=15000)

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_compass_reload_prefers_fresher_runtime_json_over_stale_preloaded_js(tmp_path) -> None:  # noqa: ANN001
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")

    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    runtime_js_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))

    compass_tz = ZoneInfo("America/Los_Angeles")
    now_utc = dt.datetime.now(tz=dt.timezone.utc).replace(microsecond=0)
    old_utc = now_utc - dt.timedelta(hours=4)
    fresh_local = now_utc.astimezone(compass_tz)
    old_local = old_utc.astimezone(compass_tz)
    day_token = fresh_local.date().isoformat()

    base_event = dict((payload.get("timeline_events") or [])[0])
    base_transaction = dict((payload.get("timeline_transactions") or [])[0])
    files = ["src/odylith/runtime/surfaces/templates/compass_dashboard/compass-state.v1.js"]

    def _payload_variant(*, label: str, event_time: dt.datetime, generated_time: dt.datetime) -> dict[str, object]:
        event = dict(base_event)
        event["id"] = f"{label}:event"
        event["kind"] = "implementation"
        event["summary"] = f"{label} Compass runtime event."
        event["ts_iso"] = event_time.isoformat()
        event["author"] = "assistant"
        event["files"] = list(files)
        event["workstreams"] = []

        transaction = dict(base_transaction)
        transaction["id"] = f"{label}:tx"
        transaction["transaction_id"] = f"{label}:tx"
        transaction["headline"] = f"{label} Compass runtime transaction"
        transaction["start_ts_iso"] = (event_time - dt.timedelta(minutes=10)).isoformat()
        transaction["end_ts_iso"] = event_time.isoformat()
        transaction["event_count"] = 1
        transaction["files_count"] = len(files)
        transaction["files"] = list(files)
        transaction["workstreams"] = []
        transaction["events"] = [event]

        variant = dict(payload)
        variant["generated_utc"] = generated_time.isoformat().replace("+00:00", "Z")
        variant["now_local_iso"] = generated_time.astimezone(compass_tz).isoformat()
        variant["timeline_events"] = [event]
        variant["timeline_transactions"] = [transaction]
        variant["history"] = {
            "retention_days": 15,
            "dates": [day_token],
            "restored_dates": [],
            "archive": {"compressed": True, "path": "archive", "count": 0, "dates": [], "newest_date": "", "oldest_date": ""},
        }
        return variant

    stale_payload = _payload_variant(label="Stale JS", event_time=old_local, generated_time=old_utc)
    fresh_payload = _payload_variant(label="Fresh JSON", event_time=fresh_local, generated_time=now_utc)

    runtime_json_path.write_text(json.dumps(stale_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(stale_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )

    with _static_server(root=fixture_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                response = page.goto(
                    base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                    wait_until="domcontentloaded",
                )
                assert response is not None and response.ok

                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Stale JS Compass runtime event.").wait_for(timeout=15000)

                runtime_json_path.write_text(json.dumps(fresh_payload, indent=2) + "\n", encoding="utf-8")

                page.reload(wait_until="domcontentloaded")
                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Fresh JSON Compass runtime event.").wait_for(timeout=15000)
                compass.locator("#timeline", has_text="Stale JS Compass runtime event.").wait_for(state="detached", timeout=15000)
                page.wait_for_function(
                    """() => {
                        const frame = document.querySelector("#frame-compass");
                        const doc = frame && frame.contentDocument;
                        const banner = doc && doc.querySelector("#status-banner");
                        return Boolean(banner && (banner.classList.contains("hidden") || !(banner.textContent || "").includes("Compass snapshot")));
                    }""",
                    timeout=15000,
                )

                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()
