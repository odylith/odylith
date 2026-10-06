"""Read local facts after a real batch failure result reaches Compass rendering."""

import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import compass_standup_brief_batch as batch
from odylith.runtime.surfaces import compass_standup_brief_runtime_patch as runtime_patch
from tests.integration.runtime.test_surface_browser_smoke import (
    _ready_compass_fixture_root,
    _write_compass_fixture_runtime_payloads,
)
from tests.integration.runtime.compass_browser_regression_support import (
    clone_odylith_fixture, render_compass_fixture,
)
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _assert_compass_live_state, _browser, _new_page, _run_in_browser_thread, _static_server,
)


@pytest.mark.parametrize("width", [1440, 390], ids=["desktop", "mobile"])
@pytest.mark.parametrize("reason", ["credits_exhausted", "provider_deferred"])
def test_batch_provider_failure_keeps_local_facts_visible_without_history(tmp_path: Path, width: int, reason: str) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    payload = json.loads((fixture_root / "odylith/compass/runtime/current.v1.json").read_text())
    payload["standup_brief"] = {}
    payload["standup_brief_scoped"] = {}
    payload["history"] = {"retention_days": 0, "dates": [], "restored_dates": []}
    fact = "Project publication awaits source-grounded acceptance checks."
    next_fact = "Review source-grounded acceptance checks before publication."
    watch_fact = "Source acceptance remains unverified."
    packet = {"facts": [
        {"section_key": "current_execution", "text": fact},
        {"section_key": "next_planned", "text": next_fact},
        {"section_key": "risks_to_watch", "text": watch_fact},
    ]}

    class UnavailableProvider:
        last_failure_code = reason
        last_failure_detail = "Provider budget unavailable in this deterministic control."

        def generate_structured(self, **_kwargs):
            pytest.fail("The deferred brief must not call a provider.")

    if reason == "provider_deferred":
        failure = batch.narrator.build_standup_brief(
            repo_root=tmp_path, fact_packet=packet, generated_utc=payload["generated_utc"],
            provider=UnavailableProvider(), allow_provider=False,
        )
    else:
        failure = batch._provider_failure_brief_for_packet(
            fact_packet=packet, generated_utc=payload["generated_utc"], provider=UnavailableProvider(),
        )
    payload, changed = runtime_patch.runtime_payload_with_brief_results(
        payload=payload, global_results={}, scoped_results={},
        global_failures={"24h": failure, "48h": failure},
    )
    assert changed and payload["standup_brief"]["24h"]["status"] == "unavailable"
    _write_compass_fixture_runtime_payloads(fixture_root, runtime_payload=payload)

    def exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": width, "height": 1100})
                try:
                    with _new_page(context) as (page, observation):
                        page.route("**/compass-summary.v1.js*", lambda route: route.fulfill(
                            body=(Path(__file__).resolve().parents[3] / "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-summary.v1.js").read_text(),
                            content_type="application/javascript",
                        ))
                        response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live")
                        assert response is not None and response.ok
                        compass = page.frame_locator("#frame-compass")
                        compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                        _assert_compass_live_state(compass, window_token="24h")
                        facts = compass.locator("#digest-list .brief-fallback-digest")
                        facts.wait_for(state="visible", timeout=15000)
                        card = compass.locator("#digest-list .brief-status-card")
                        assert card.locator(".brief-status-title").all_text_contents() == [failure["diagnostics"]["title"]]
                        assert card.locator(".brief-status-copy").all_text_contents() == [failure["diagnostics"]["message"]]
                        assert card.get_attribute("role") == "status"
                        assert card.get_attribute("aria-live") == "polite"
                        if reason == "provider_deferred":
                            assert card.get_by_text("Local runtime facts", exact=True).count() == 1
                            assert facts.locator(".brief-fallback-title").count() == 0
                            assert failure["diagnostics"]["message"] == "A summary is not available for this view."
                        else:
                            assert facts.locator(".brief-fallback-title").text_content() == "Local runtime facts"
                            assert facts.locator(".brief-fallback-title").inner_text() == "LOCAL RUNTIME FACTS"
                        assert facts.locator("li").all_text_contents() == [
                            "Current: " + fact, "Next: " + next_fact, "Watch: " + watch_fact,
                        ]
                        assert compass.locator("#digest-list .standup-brief-sections").count() == 0
                        assert facts.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                        facts.scroll_into_view_if_needed()
                        page.screenshot(path=str(tmp_path / "fallback-visible.png"), full_page=True)
                        _assert_clean_page(page, observation)
                finally:
                    context.close()

    _run_in_browser_thread(exercise)


@pytest.mark.parametrize("width", [1440, 390], ids=["desktop", "mobile"])
@pytest.mark.parametrize("degraded", [False, True], ids=["normal", "runtime-unavailable"])
def test_activity_counts_keep_brief_primary_and_runtime_failure_visible(tmp_path: Path, width: int, degraded: bool) -> None:
    fixture_root = clone_odylith_fixture(tmp_path)
    render_compass_fixture(fixture_root)

    def exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": width, "height": 1100})
                try:
                    with _new_page(context) as (page, observation):
                        missing_runtime_reads = []
                        if degraded:
                            def absent_runtime(route):
                                missing_runtime_reads.append(route.request.url)
                                is_script = ".js" in route.request.url
                                route.fulfill(body="window.__ODYLITH_COMPASS_RUNTIME__ = null;" if is_script else "null",
                                              content_type="application/javascript" if is_script else "application/json")
                            page.route("**/compass/runtime/current.v1.js*", absent_runtime)
                            page.route("**/compass/runtime/current.v1.json*", absent_runtime)
                        response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live")
                        assert response is not None and response.ok
                        compass = page.frame_locator("#frame-compass")
                        compass.locator('body[data-surface-ready="ready"]').wait_for(timeout=15000)
                        disclosure = compass.locator("details:has(> #kpi-grid)")
                        assert disclosure.count() == 1
                        assert disclosure.locator(":scope > summary").text_content() == "Activity and counts"
                        assert disclosure.locator("#controls, #risk-list").count() == 0
                        if degraded:
                            assert len(missing_runtime_reads) == 2
                            assert disclosure.get_attribute("open") is not None
                            assert compass.get_by_text("Runtime Unavailable", exact=True).is_visible()
                            assert compass.locator("#kpi-grid .muted").inner_text() == "Compass information could not be loaded. Refresh it with `odylith sync --repo-root . --force`."
                            assert compass.get_by_text("Current information is unavailable.", exact=True).is_visible()
                            assert compass.get_by_text("Risk information is unavailable.", exact=True).is_visible()
                        else:
                            assert disclosure.get_attribute("open") is None
                            assert not compass.locator("#kpi-grid").is_visible()
                            assert compass.locator("#standup-brief-card").bounding_box()["y"] < 1100
                            page.screenshot(path=str(tmp_path / f"activity-counts-normal-{width}.png"), full_page=True)
                            controls = compass.locator("#controls").evaluate("node => node.outerHTML")
                            compass.locator("body").evaluate("""() => {
                                const state = {date: 'live', window: '24h', workstream: ''};
                                const payload = {
                                    kpis: {'24h': {commits: 7, local_changes: 9, active_workstreams: 3, recent_completed_plans: 4}},
                                    verified_scoped_workstreams: {'24h': ['B-072', 'B-073']},
                                    release_summary: {current_release: {version: '0.1.15'}},
                                    risks: {bugs: [{is_open_critical: true, status: 'open', severity: 'critical',
                                                   title: 'Source acceptance remains unverified.'}]},
                                };
                                renderKpis(payload, state, []);
                                renderRisks(payload, state);
                            }""")
                            expected = ["7", "9", "2", "3", "1", "4", "0.1.15"]
                            assert compass.locator("#kpi-grid .kpi-label").all_text_contents() == [
                                "Commits", "Local Changes", "Touched Workstreams", "Active Workstreams",
                                "Critical Risks", "Completed Plans", "Target Release",
                            ]
                            assert compass.locator("#kpi-grid .kpi-value").all_text_contents() == expected
                            assert compass.locator("#kpi-grid .kpi-value").evaluate_all("nodes => nodes.map(node => node.title)") == expected
                            assert compass.get_by_text("Source acceptance remains unverified.", exact=True).is_visible()
                            disclosure.locator(":scope > summary").focus()
                            page.keyboard.press("Enter")
                            assert disclosure.get_attribute("open") is not None
                            assert compass.locator("#kpi-grid").is_visible()
                            assert compass.locator("#kpi-grid .kpi-value").all_text_contents() == expected
                            page.keyboard.press("Enter")
                            assert disclosure.get_attribute("open") is None
                            assert not compass.locator("#kpi-grid").is_visible()
                            assert compass.locator("#kpi-grid .kpi-value").all_text_contents() == expected
                            assert compass.get_by_text("Source acceptance remains unverified.", exact=True).is_visible()
                            assert compass.locator("#controls").evaluate("node => node.outerHTML") == controls
                        assert compass.locator("body").evaluate("document.documentElement.scrollWidth <= window.innerWidth")
                        page.screenshot(path=str(tmp_path / f"activity-counts-{'degraded' if degraded else 'closed'}-{width}.png"), full_page=True)
                        _assert_clean_page(page, observation)
                finally:
                    context.close()

    _run_in_browser_thread(exercise)
