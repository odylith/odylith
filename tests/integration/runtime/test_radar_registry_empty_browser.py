"""Absent records and filtered results must offer different, useful recovery paths."""

from pathlib import Path

import pytest

from odylith import __version__
from odylith.install.bootstrap_assets import ensure_customer_bootstrap
from odylith.runtime.surfaces import render_backlog_ui, render_registry_dashboard, render_tooling_dashboard
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)
from tests.unit.runtime.test_component_registry_categories import _seed_application_registry
from tests.unit.runtime.test_render_backlog_ui import _seed_backlog_render_repo


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("tab,query,row,empty", [
    ("radar", "#query", "button[data-idea-id]", "#detail-empty"),
    ("registry", "#search", "button[data-component]", "#detail [role=status]"),
])
@pytest.mark.parametrize("has_records", [False, True])
def test_empty_governance_distinguishes_absent_source_from_filtered_results(
    tmp_path: Path, width: int, tab: str, query: str, row: str, empty: str, has_records: bool,
) -> None:
    ensure_customer_bootstrap(repo_root=tmp_path, version=__version__)
    if has_records:
        _seed_backlog_render_repo(tmp_path)
        _seed_application_registry(tmp_path)
    assert render_backlog_ui.main(["--repo-root", str(tmp_path)]) == 0
    assert render_registry_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    assert render_tooling_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": width, "height": 1100 if width == 1440 else 932})
            try:
                with _new_page(context) as (page, observation):
                    response = page.goto(base_url+f"/odylith/index.html?tab={tab}", wait_until="domcontentloaded")
                    assert response and response.ok
                    page.get_by_role("button", name="Close starter guide").click()
                    frame = page.frame_locator(f"#frame-{tab}")
                    frame.locator(query).wait_for(timeout=15000)
                    if has_records:
                        frame.locator(row).first.wait_for(timeout=15000)
                        count = frame.locator(row).count()
                        frame.locator(query).fill("zz-no-record-matches-zz")
                    frame.locator(empty).wait_for(timeout=2000)
                    assert frame.locator(row).count() == 0
                    message = frame.locator(empty).inner_text()
                    if has_records:
                        assert "filters" in message.lower()
                        assert "yet" not in message.lower()
                        frame.locator(query).fill("")
                        frame.locator(row).first.wait_for(timeout=15000)
                        assert frame.locator(row).count() == count
                        assert not frame.locator(empty).is_visible()
                    else:
                        assert "yet" in message.lower()
                        assert "filters" not in message.lower()
                        link = frame.locator(empty).get_by_role("link", name="Open Project")
                        assert link.get_attribute("href") == "../index.html?tab=project"
                        link.click()
                        page.locator('#tab-project[aria-selected="true"]').wait_for(timeout=15000)
                        page.locator(".project-empty-panel").wait_for(timeout=15000)
                    assert page.locator("body").evaluate("node => node.scrollWidth <= node.clientWidth + 1")
                    _assert_clean_page(page, observation)
            finally:
                context.close()


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("component", ["", "missing-component"])
def test_registry_empty_heading_remains_readable_after_scroll(
    tmp_path: Path, width: int, component: str,
) -> None:
    ensure_customer_bootstrap(repo_root=tmp_path, version=__version__)
    assert render_registry_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    assert render_tooling_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 1100 if width == 1440 else 932}) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + f"/odylith/index.html?tab=registry&component={component}", wait_until="domcontentloaded")
                    page.get_by_role("button", name="Close starter guide").click()
                    registry = page.frame_locator("#frame-registry")
                    status = registry.locator("#detail [role=status]")
                    status.wait_for(timeout=15000)
                    registry.locator("#diagnostics > summary").wait_for()
                    status.scroll_into_view_if_needed()
                    heading = status.locator("h2")
                    geometry = heading.evaluate("""heading => {
                    const title = heading.getBoundingClientRect();
                    const chip = document.querySelector('#diagnostics > summary').getBoundingClientRect();
                    const hit = document.elementFromPoint(title.left + 5, title.top + 5);
                    return {
                        overlapWidth: Math.max(0, Math.min(chip.right, title.right) - Math.max(chip.left, title.left)),
                        overlapHeight: Math.max(0, Math.min(chip.bottom, title.bottom) - Math.max(chip.top, title.top)),
                        headingOwnsHit: hit === heading || heading.contains(hit),
                    };
                }""")
                    screenshot = _failure_screenshot_path(f"registry-empty-reading-{width}-{component or 'normal'}")
                    if screenshot is not None:
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot))
                    assert geometry["overlapWidth"] * geometry["overlapHeight"] == 0, geometry
                    assert geometry["headingOwnsHit"], geometry
                    status.get_by_role("link", name="Open Project").click()
                    page.locator('#tab-project[aria-selected="true"]').wait_for(timeout=15000)
                    _assert_clean_page(page, observation)
