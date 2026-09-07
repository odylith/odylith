"""Real detail requests cannot revive filtered rows or overwrite a newer selection."""

from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_backlog_ui, render_backlog_ui_html_runtime, render_registry_dashboard
from tests.integration.runtime.surface_browser_test_support import _assert_clean_page, _new_page, browser_context
from tests.unit.runtime.test_component_registry_categories import _seed_application_registry
from tests.unit.runtime.test_render_backlog_ui import _load_backlog_payload, _seed_backlog_render_repo
from tests.unit.runtime.test_render_registry_dashboard import _load_registry_payload


def _payload(tmp_path: Path, tab: str):
    if tab == "radar":
        _seed_backlog_render_repo(tmp_path)
        assert render_backlog_ui.main(["--repo-root", str(tmp_path)]) == 0
        return _load_backlog_payload(tmp_path), render_backlog_ui_html_runtime._render_html
    _seed_application_registry(tmp_path)
    assert render_registry_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    return _load_registry_payload(tmp_path), render_registry_dashboard._render_html


def _release_detail(page, frame, route, marker: str) -> None:  # noqa: ANN001
    with page.expect_response(lambda response: response.url == route.request.url) as response:
        route.fulfill(status=200, content_type="application/json", json={
            "title": marker, "name": marker,
            "timeline": [{"ts_iso": "2026-09-07T12:00:00Z", "kind": "implementation", "summary": marker + " event"}],
        })
    response.value.body()
    # Let the real fetch/json continuation and resulting DOM update finish.
    frame.locator("body").evaluate("() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))")


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("tab,query,row", [
    ("radar", "#query", "button[data-idea-id]"),
    ("registry", "#search", "button[data-component]"),
])
def test_late_detail_cannot_replace_filtered_state_or_newer_same_id_selection(
    tmp_path: Path, browser_context, width: int, tab: str, query: str, row: str,
) -> None:  # noqa: ANN001
    payload, render_html = _payload(tmp_path, tab)
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
    payload["data_source"] = {"preferred_backend": "runtime", "runtime_base_url": base_url + "/selection-race/"}
    pending = []

    def runtime_response(route):  # noqa: ANN001
        if "/detail?" in route.request.url:
            pending.append(route)
        else:
            route.fulfill(status=200, content_type="application/json", json={"entries": payload.get("entries", [])})

    page.route("**/selection-race/surfaces/**", runtime_response)
    html_name = "radar.html" if tab == "radar" else "registry.html"
    page.route(f"**/odylith/{tab}/{html_name}*", lambda route: route.fulfill(
        status=200, content_type="text/html", body=render_html(payload=payload),
    ))
    detail_request = lambda request: "/selection-race/surfaces/" in request.url and "/detail?" in request.url
    with page.expect_request(detail_request):
        page.goto(base_url + f"/odylith/index.html?tab={tab}", wait_until="domcontentloaded")
    frame = page.frame_locator(f"#frame-{tab}")
    frame.locator(row).first.wait_for()
    assert len(pending) == 1
    selected_url = pending[0].request.url
    frame.locator(query).fill("zz-no-record-matches-zz")
    assert frame.locator(row).count() == 0
    filtered_detail = frame.locator("#detail").inner_html()
    filtered_timeline = frame.locator("#timeline").inner_html() if tab == "registry" else ""
    _release_detail(page, frame, pending[0], "Stale filtered detail")
    assert frame.locator("#detail").inner_html() == filtered_detail
    assert "Stale filtered detail" not in frame.locator("#detail").inner_text()
    empty = frame.locator("#detail-empty" if tab == "radar" else "#detail [role=status]")
    if tab == "registry":
        assert frame.locator("#timeline").inner_html() == filtered_timeline

    # Re-enter the same selection twice while both actual detail requests remain pending.
    with page.expect_request(detail_request):
        frame.locator(query).fill("")
    assert len(pending) == 2
    frame.locator(query).fill("zz-no-record-matches-zz")
    with page.expect_request(detail_request):
        frame.locator(query).fill("")
    assert len(pending) == 3
    assert all(route.request.url == selected_url for route in pending)
    _release_detail(page, frame, pending[2], "Newest selected detail")
    assert "Newest selected detail" in frame.locator("#detail").inner_text()
    if tab == "registry":
        assert "Newest selected detail event" in frame.locator("#timeline").inner_text()
    _release_detail(page, frame, pending[1], "Older same-id detail")
    assert "Newest selected detail" in frame.locator("#detail").inner_text()
    assert "Older same-id detail" not in frame.locator("#detail").inner_text()
    if tab == "registry":
        assert "Newest selected detail event" in frame.locator("#timeline").inner_text()
        assert "Older same-id detail" not in frame.locator("#timeline").inner_text()
    assert not empty.is_visible()
    _assert_clean_page(page, *errors)
