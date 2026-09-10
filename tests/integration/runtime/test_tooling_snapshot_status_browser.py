"""Real shell status dependencies inside the production immutable publication.

Child pages are deliberately minimal; this proves shell dependency custody, not
complete governance content or installed-consumer release qualification.
"""

from contextlib import nullcontext
from pathlib import Path

import pytest

from odylith.install.state import write_install_state, write_version_pin
from odylith.runtime.context_engine import odylith_control_state as telemetry
from odylith.runtime.domain_intelligence import greenfield_create_baseline as baseline
from odylith.runtime.domain_intelligence import greenfield_generation_store as generations
from odylith.runtime.domain_intelligence import greenfield_managed_mutation_boundary as boundary
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)
from tests.integration.runtime.test_tooling_dashboard_onboarding_browser import (
    _render_shell, _seed_consumer_repo,
)
from tests.unit.runtime.test_render_tooling_dashboard import _seed_compass_runtime_snapshot


def _capture(page, name):
    target = _failure_screenshot_path(name)
    if target:
        target.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(target), full_page=True)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("protocol", ["file", "http"])
@pytest.mark.parametrize("status", ["current", "absent", "failed"])
def test_initial_publication_has_no_external_status_dependencies(tmp_path, monkeypatch, width, protocol, status):
    _seed_consumer_repo(tmp_path)
    if status != "absent":
        _seed_compass_runtime_snapshot(
            tmp_path, generated_utc="2026-09-09T18:00:00Z",
            last_refresh_attempt={"status": status, "attempted_utc": "2026-09-09T18:01:00Z"},
        )
    _render_shell(tmp_path, monkeypatch)
    baseline.activate_completed_greenfield_baseline(
        repo_root=tmp_path,
        required_surface_outputs=[Path("odylith/index.html")],
    )
    generation = generations.pin_active_greenfield_generation(tmp_path)
    entry = tmp_path / "odylith/index.html"
    server = _static_server(root=tmp_path) if protocol == "http" else nullcontext(None)
    with server as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": width, "height": 1000})
            try:
                with _new_page(context) as (page, observation):
                    requests = []
                    page.on("request", lambda request: requests.append(request.url))
                    page.clock.install()
                    entry_url = base_url + "/odylith/index.html" if base_url else entry.as_uri()
                    page.goto(entry_url + "?tab=compass")
                    page.locator(".toolbar-version").wait_for()
                    page.frame_locator("#frame-compass").get_by_role("heading", name="Executive Compass").wait_for()
                    assert generation.write_set_hash in page.url
                    pinned_url = page.url
                    page.clock.fast_forward(31000)
                    page.wait_for_load_state("networkidle")
                    assert not any("odylith-context-engine-state.v1.js" in url for url in requests)
                    assert not any("odylith-version-state.v1.js" in url for url in requests)
                    assert page.locator(".toolbar-version").inner_text() == "v1.2.3"
                    assert "Status captured" in page.locator(".shell-snapshot-note").inner_text()
                    assert not page.locator("body").evaluate("node => node.scrollWidth > innerWidth + 1")
                    assert page.locator("#shellRuntimeStatus").is_visible() == (status == "failed")
                    if status == "failed":
                        assert page.locator("#shellRuntimeStatusTitle").inner_text() == "Showing prior Compass snapshot"
                    page.locator("#welcomeDismiss").click(timeout=2000)
                    page.locator("#shellWelcomeState").wait_for(state="hidden")
                    _capture(page, f"snapshot-status-{protocol}-{width}-{status}-initial")

                    telemetry.write_state(repo_root=tmp_path, payload={"updated_utc": "2026-09-09T18:02:00Z"})
                    assert generations.require_greenfield_working_generation(tmp_path) == generation

                    def refresh(_fd):
                        write_install_state(repo_root=tmp_path, payload={"active_version": "1.2.4"})
                        write_version_pin(repo_root=tmp_path, version="1.2.4")
                        _seed_compass_runtime_snapshot(tmp_path, generated_utc="2026-09-09T18:02:00Z")
                        _render_shell(tmp_path, monkeypatch)
                        return 0

                    assert boundary.run_with_greenfield_managed_mutation_boundary(
                        repo_root=tmp_path, command_tokens=["dashboard", "refresh", "--force"], operation=refresh,
                    ) == 0
                    successor = generations.require_greenfield_working_generation(tmp_path)
                    assert successor.write_set_hash != generation.write_set_hash
                    page.clock.fast_forward(31000)
                    page.wait_for_load_state("networkidle")
                    assert page.url == pinned_url
                    assert page.locator(".toolbar-version").inner_text() == "v1.2.3"
                    assert page.locator("#shellRuntimeStatus").is_visible() == (status == "failed")

                    page.goto(entry_url + "?tab=compass")
                    page.frame_locator("#frame-compass").get_by_role("heading", name="Executive Compass").wait_for()
                    assert successor.write_set_hash in page.url
                    assert page.locator(".toolbar-version").inner_text() == "v1.2.4"
                    assert page.locator("#shellRuntimeStatus").is_hidden()
                    _capture(page, f"snapshot-status-{protocol}-{width}-{status}-successor")
                    page.goto(pinned_url)
                    page.frame_locator("#frame-compass").get_by_role("heading", name="Executive Compass").wait_for()
                    assert page.locator(".toolbar-version").inner_text() == "v1.2.3"
                    assert page.locator("#shellRuntimeStatus").is_visible() == (status == "failed")
                    _assert_clean_page(page, observation)
            finally:
                context.close()
