"""Shell overlay focus must settle before the user's next input choice."""

from pathlib import Path

import pytest

from odylith.install.state import write_upgrade_spotlight
from odylith.runtime.surfaces import render_backlog_ui, render_registry_dashboard, render_tooling_dashboard, shell_onboarding
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)
from tests.integration.runtime.test_tooling_dashboard_onboarding_browser import _seed_consumer_repo
from tests.unit.runtime.test_component_registry_categories import _seed_application_registry
from tests.unit.runtime.test_render_backlog_ui import _seed_backlog_render_repo


def _render_governance_shell(root: Path, overlay: str) -> None:
    _seed_consumer_repo(
        root, focus_path="", active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"] if overlay == "upgrade" else ["1.2.3"],
    )
    _seed_backlog_render_repo(root, product_repo=False)
    _seed_application_registry(root)
    if overlay == "upgrade":
        write_upgrade_spotlight(
            repo_root=root, from_version="1.2.2", to_version="1.2.3",
            release_tag="v1.2.3", release_url="https://example.com/releases/v1.2.3",
            release_published_at="2026-03-30T14:00:00Z",
            release_body="Search preserves the user's input after closing the release note.",
            highlights=("Preserve search input after closing the release note.",),
        )
    assert bool(shell_onboarding.build_release_spotlight(repo_root=root)) == (overlay == "upgrade")
    assert render_backlog_ui.main(["--repo-root", str(root)]) == 0
    assert render_registry_dashboard.main(["--repo-root", str(root), "--runtime-mode", "standalone"]) == 0
    assert render_tooling_dashboard.main(["--repo-root", str(root), "--runtime-mode", "standalone"]) == 0


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("overlay", ["welcome", "upgrade"])
@pytest.mark.parametrize("tab,query,row,empty", [
    ("radar", "#query", "button[data-idea-id]", "#detail-empty"),
    ("registry", "#search", "button[data-component]", "#detail [role=status]"),
])
def test_overlay_dismissal_cannot_override_new_child_input_focus(
    tmp_path: Path, width: int, overlay: str, tab: str, query: str, row: str, empty: str,
) -> None:
    _render_governance_shell(tmp_path, overlay)
    dismiss = "welcomeDismiss" if overlay == "welcome" else "upgradeSpotlightDismiss"
    reopen = "welcomeReopen" if overlay == "welcome" else "upgradeReopen"
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 1100 if width == 1440 else 932}) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + f"/odylith/index.html?tab={tab}", wait_until="domcontentloaded")
                    page.locator(f"#{dismiss}").wait_for(timeout=15000)
                    frame = page.frame_locator(f"#frame-{tab}")
                    frame.locator(row).first.wait_for(timeout=15000)
                    count = frame.locator(row).count()
                    # Perform a new focus choice before the next native animation frame.
                    # No scheduler, filter, input handler or product callback is replaced.
                    focus = page.evaluate("""async ({dismiss, tab, query}) => {
                    document.getElementById(dismiss).click();
                    const child = document.getElementById(`frame-${tab}`).contentDocument;
                    child.querySelector(query).focus();
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    return {shell: document.activeElement.id, child: child.activeElement.id};
                }""", {"dismiss": dismiss, "tab": tab, "query": query})
                    assert focus == {"shell": f"frame-{tab}", "child": query[1:]}
                    page.keyboard.insert_text("zz-no-record-matches-zz")
                    assert frame.locator(query).input_value() == "zz-no-record-matches-zz"
                    frame.locator(empty).wait_for(timeout=2000)
                    assert frame.locator(row).count() == 0
                    capture = _failure_screenshot_path(f"settled-overlay-focus-{overlay}-{tab}-{width}")
                    if capture is not None:
                        capture.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(capture))
                    frame.locator(query).fill("")
                    frame.locator(row).first.wait_for(timeout=15000)
                    assert frame.locator(row).count() == count
                    page.locator(f"#{reopen}").click()
                    page.locator(f"#{dismiss}").wait_for(timeout=2000)
                    if overlay == "upgrade":
                        page.wait_for_function("id => document.activeElement.id === id", arg=dismiss, timeout=2000)
                    page.locator(f"#{dismiss}").click()
                    page.wait_for_function("id => document.activeElement.id === id", arg=reopen, timeout=2000)
                    _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("next_focus", ["child", "drawer"])
def test_cheatsheet_open_cannot_override_new_focus(
    tmp_path: Path, width: int, next_focus: str,
) -> None:
    _render_governance_shell(tmp_path, "welcome")
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 1100 if width == 1440 else 932}) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
                    page.locator("#welcomeDismiss").click()
                    page.frame_locator("#frame-radar").locator("button[data-idea-id]").first.wait_for(timeout=15000)
                    kept_focus = page.evaluate("""async nextFocus => {
                    document.getElementById('odylithToggle').click();
                    const child = document.getElementById('frame-radar').contentDocument;
                    const target = nextFocus === 'child'
                        ? child.getElementById('query') : document.getElementById('odylithClose');
                    target.focus();
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    return target.ownerDocument.activeElement === target
                        && (nextFocus !== 'child' || document.activeElement.id === 'frame-radar');
                }""", next_focus)
                    assert kept_focus
                    page.locator("#odylithClose").click()
                    page.wait_for_function("document.activeElement.id === 'odylithToggle'", timeout=2000)
                    page.locator("#odylithToggle").click()
                    page.wait_for_function("document.activeElement.id === 'agentCheatsheetSearch'", timeout=2000)
                    page.keyboard.press("Escape")
                    page.wait_for_function("document.activeElement.id === 'odylithToggle'", timeout=2000)
                    page.locator("#odylithToggle").click()
                    page.locator("#agentCheatsheetSearch").fill("release")
                    page.locator("#odylithClose").click()
                    page.locator("#odylithToggle").click()
                    page.wait_for_function("""() => {
                    const input = document.getElementById('agentCheatsheetSearch');
                    return input.value === 'release' && document.activeElement === input && input.selectionStart === 0
                        && input.selectionEnd === input.value.length;
                }""", timeout=2000)
                    page.keyboard.insert_text("atlas")
                    assert page.locator("#agentCheatsheetSearch").input_value() == "atlas"
                    _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430])
def test_upgrade_reopen_cannot_override_new_release_link_focus(tmp_path: Path, width: int) -> None:
    _render_governance_shell(tmp_path, "upgrade")
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 1100 if width == 1440 else 932}) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
                    page.locator("#upgradeSpotlightDismiss").click()
                    page.wait_for_function("document.activeElement.id === 'upgradeReopen'", timeout=2000)
                    kept_focus = page.evaluate("""async () => {
                    document.getElementById('upgradeReopen').click();
                    const link = document.querySelector('#shellUpgradeSpotlight .upgrade-spotlight-link');
                    link.focus();
                    await new Promise(resolve => requestAnimationFrame(resolve));
                    return document.activeElement === link;
                }""")
                    assert kept_focus
                    page.keyboard.press("Escape")
                    page.wait_for_function("document.activeElement.id === 'upgradeReopen'", timeout=2000)
                    _assert_clean_page(page, observation)
