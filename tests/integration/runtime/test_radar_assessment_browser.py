"""Real Radar rendering keeps unassessed records visibly unknown in every state."""

from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_backlog_ui_html_runtime
from tests.unit.runtime.test_radar_assessment_views import DEPENDENCY_REASON, assessment_entry
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["unassessed", "mixed", "empty", "runtime-fallback"])
def test_radar_assessment_states(tmp_path: Path, browser_context, width: int, state: str) -> None:
    base_url, context = browser_context
    unknown = assessment_entry(tmp_path / "unknown")
    unknown["idea_id"] = "B-999"
    dependent = {**unknown, "idea_id": "B-1000", "workstream_depends_on": ["B-999"]}
    known = assessment_entry(tmp_path / "known", unassessed=False)
    known.update(idea_id="B-001", rank="1", rank_num=1)
    zero = {**known, "idea_id": "B-002", "ordering_score": 0, "rank": "2", "rank_num": 2}
    entries = [] if state == "empty" else [unknown, dependent]
    if state in {"mixed", "runtime-fallback"}:
        entries.extend([zero, known])
    payload = {"entries": entries}
    fallback_requests = []
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        if state == "runtime-fallback":
            payload["data_source"] = {"preferred_backend": "runtime", "runtime_base_url": base_url + "/assessment-runtime/"}

            def unavailable_runtime(route):
                fallback_requests.append(route.request.url)
                route.fulfill(status=200, content_type="application/json", body="invalid JSON")

            page.route("**/assessment-runtime/**", unavailable_runtime)
        page.route("**/radar-assessments.html*", lambda route: route.fulfill(
            status=200, content_type="text/html",
            body=render_backlog_ui_html_runtime._render_html(payload=payload),
        ))
        page.goto(base_url + "/radar-assessments.html?workstream=B-999", wait_until="networkidle")
        if state == "empty":
            assert page.get_by_text("No workstreams yet", exact=True).is_visible()
            assert page.locator("#detail").get_attribute("hidden") == ""
        else:
            detail = page.locator("#detail")
            assessment = detail.locator(".detail-header > details > summary")
            assessment.focus()
            assessment.press("Enter")
            score = detail.locator(".kpi").filter(has=page.locator(".k", has_text="Ordering Score")).locator(".v")
            assert score.inner_text() == "Not assessed"
            assert detail.locator(".chip-priority").inner_text() == "Not assessed"
            assert detail.locator(".chip-sizing").inner_text() == "Not assessed"
            assert detail.locator(".meter .bar").count() == 0
            assert detail.locator(".assessment-provenance").inner_text() == "Provisional Greenfield design"
            assert detail.locator(".score-ordered").count() == 0
            assert DEPENDENCY_REASON in detail.inner_text()
            assert page.locator('[data-idea-id="B-999"] .rank-chip').inner_text() == "Not assessed"
            assert page.locator('#priority option[value="unassessed"]').inner_text() == "Not assessed"
            assert detail.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
            page.locator("#sort").select_option("score")
            expected_order = ["B-999", "B-1000"]
            if state in {"mixed", "runtime-fallback"}:
                expected_order = ["B-001", "B-002", *expected_order]
            for sort in ("score", "rank", "date"):
                page.locator("#sort").select_option(sort)
                assert page.locator("#list button[data-idea-id]").evaluate_all(
                    "nodes => nodes.map(node => node.dataset.ideaId)"
                ) == expected_order
            if state in {"mixed", "runtime-fallback"}:
                page.locator('[data-idea-id="B-002"]').click()
                assessment.focus()
                assessment.press("Enter")
                assert score.inner_text() == "0"
                page.locator('[data-idea-id="B-001"]').click()
                assessment.focus()
                assessment.press("Enter")
                assert score.inner_text() == "88"
            page.locator("#priority").select_option("unassessed")
            assert page.locator("#list button[data-idea-id]").evaluate_all(
                "nodes => nodes.map(node => node.dataset.ideaId)"
            ) == ["B-999", "B-1000"]
            page.locator('[data-idea-id="B-999"]').click()
            assessment.focus()
            assessment.press("Enter")
            assert score.inner_text() == "Not assessed"
            assert detail.locator(".meter .bar").count() == 0
            if state == "runtime-fallback":
                assert any("surfaces/backlog/list" in url for url in fallback_requests)
                assert any("surfaces/backlog/detail" in url for url in fallback_requests)
        screenshot = _failure_screenshot_path(f"radar-assessment-{state}-{width}")
        if screenshot:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot))
        _assert_clean_page(page, observation)
