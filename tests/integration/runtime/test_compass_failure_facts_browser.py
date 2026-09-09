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
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _assert_compass_live_state, _browser, _new_page, _run_in_browser_thread, _static_server,
)


@pytest.mark.parametrize("width", [1440, 390], ids=["desktop", "mobile"])
def test_batch_provider_failure_keeps_local_facts_visible_without_history(tmp_path: Path, width: int) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    payload = json.loads((fixture_root / "odylith/compass/runtime/current.v1.json").read_text())
    payload["standup_brief"] = {}
    payload["standup_brief_scoped"] = {}
    payload["history"] = {"retention_days": 0, "dates": [], "restored_dates": []}
    fact = "Project publication awaits source-grounded acceptance checks."
    packet = {"facts": [{"section_key": "current_execution", "text": fact}]}

    class UnavailableProvider:
        last_failure_code = "credits_exhausted"
        last_failure_detail = "Provider budget unavailable in this deterministic control."

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
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live")
                    assert response is not None and response.ok
                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    facts = compass.locator("#digest-list .brief-fallback-digest")
                    facts.wait_for(state="visible", timeout=15000)
                    assert facts.locator(".brief-fallback-title").text_content() == "Local runtime facts"
                    assert facts.locator(".brief-fallback-title").inner_text() == "LOCAL RUNTIME FACTS"
                    assert facts.locator("li").all_text_contents() == ["Current: " + fact]
                    assert compass.locator("#digest-list .standup-brief-sections").count() == 0
                    assert facts.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                    facts.scroll_into_view_if_needed()
                    page.screenshot(path=str(tmp_path / "fallback-visible.png"), full_page=True)
                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(exercise)
