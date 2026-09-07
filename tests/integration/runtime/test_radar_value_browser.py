from __future__ import annotations

import pytest

from odylith.runtime.surfaces import render_backlog_ui
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    browser_context,
)


def test_radar_html_escaping_preserves_values_and_missing_blanks(browser_context) -> None:  # noqa: ANN001
    _base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    html = render_backlog_ui._render_html(payload={"entries": []})  # noqa: SLF001
    escape_function = html[
        html.index("    function escapeHtml(value) {"):
        html.index("    function compactPlainText(value) {")
    ]
    cases = [
        (0, "0"), (False, "false"), (True, "true"), (3, "3"), (-2.5, "-2.5"),
        (None, ""), ("", ""), ("  ", "  "), ("0", "0"),
        ("<b title=\"café\">'&</b>", "&lt;b title=&quot;café&quot;&gt;&#039;&amp;&lt;/b&gt;"),
    ]
    for value, expected in cases:
        assert page.evaluate(f"value => {{ {escape_function} return escapeHtml(value); }}", value) == expected
    assert page.evaluate(f"() => {{ {escape_function} return escapeHtml(); }}") == ""
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


@pytest.mark.parametrize("viewport", [(1440, 1100), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "empty", "runtime-fallback"])
def test_radar_zero_counts_and_score_are_visible(
    browser_context, viewport: tuple[int, int], state: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
    entries = [] if state == "empty" else [{
        "idea_id": "B-001", "title": "Zero-score fixture", "section": "active",
        "status": "queued", "ordering_score": 0, "idea_age_days": "0",
        "priority": "P2", "sizing": "S", "complexity": "Low",
    }]
    payload = {
        "entries": entries,
        "execution_waves": {"summary": {"program_count": 1, "active_wave_count": 0}},
    }
    fallback_requests = []
    if state == "runtime-fallback":
        payload["data_source"] = {
            "preferred_backend": "runtime", "runtime_base_url": base_url + "/radar-runtime/",
        }

        def unavailable_runtime(route) -> None:  # noqa: ANN001
            fallback_requests.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body="invalid JSON")

        page.route("**/radar-runtime/**", unavailable_runtime)
    html = render_backlog_ui._render_html(payload=payload)  # noqa: SLF001
    page.route("**/radar-values.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html,
    ))
    response = page.goto(base_url + "/radar-values.html", wait_until="networkidle")
    assert response is not None and response.ok
    expected = {"Queued": str(len(entries)), "Execution": "0", "Parked": "0", "Finished": "0", "Active Waves": "0"}
    for label, value in expected.items():
        card = page.locator("#stats .stat").filter(has=page.locator(".label", has_text=label))
        number = card.locator(".value")
        number.scroll_into_view_if_needed()
        assert number.is_visible()
        assert number.inner_text() == value
    assert page.locator("#stats .stat").filter(has_text="Index Updated").locator(".value").inner_text() == "-"
    if entries:
        score = page.locator("#detail .kpi").filter(has=page.locator(".k", has_text="Ordering Score")).locator(".v")
        score.scroll_into_view_if_needed()
        assert score.is_visible()
        assert score.inner_text() == "0"
    else:
        assert page.locator("#detail").get_attribute("hidden") == ""
        assert page.locator("#detail").inner_text() == ""
        assert page.locator("#list button[data-idea-id]").count() == 0
    if state == "runtime-fallback":
        assert any("surfaces/backlog/list" in url for url in fallback_requests)
        assert any("surfaces/backlog/detail" in url for url in fallback_requests)
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
