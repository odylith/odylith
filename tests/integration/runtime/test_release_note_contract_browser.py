"""Current authored and installed-mirror notes must reach the upgrade spotlight intact."""

from pathlib import Path
import shutil

import pytest

from odylith.install.state import write_upgrade_spotlight
from odylith.install.release_assets import _release_highlights
from odylith.runtime import release_notes
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
)
from tests.integration.runtime.test_tooling_dashboard_onboarding_browser import (
    REPO_ROOT, _render_shell, _seed_consumer_repo,
)


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("source", ["authored", "bundle"])
def test_v0_1_15_spotlight_preserves_sealed_confirmation_highlight(
    tmp_path: Path, monkeypatch, width: int, source: str,
) -> None:
    _seed_consumer_repo(
        tmp_path, active_version="0.1.15", activation_history=["0.1.14", "0.1.15"],
    )
    write_upgrade_spotlight(
        repo_root=tmp_path, from_version="0.1.14", to_version="0.1.15",
        release_tag="v0.1.15", release_url="https://example.com/releases/v0.1.15",
        release_published_at="", release_body="Release details are unavailable.",
        highlights=("Release details are unavailable.",),
    )
    origin = REPO_ROOT if source == "authored" else REPO_ROOT / "src/odylith/bundle/assets"
    relative = Path("odylith/runtime/source/release-notes/v0.1.15.md")
    (tmp_path / relative).parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(origin / relative, tmp_path / relative)
    note = release_notes.load_release_notes_source(repo_root=origin, version="0.1.15")
    assert note is not None
    _render_shell(tmp_path, monkeypatch)

    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 932}) as context:
                with _new_page(context) as (page, observation):
                    response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    spotlight = page.locator("#shellUpgradeSpotlight")
                    spotlight.wait_for(timeout=15000)
                    copy = spotlight.inner_text()
                    assert note.highlights[0] in copy
                    assert "Greenfield apply" not in copy
                    assert "CONFIRM publishes only the exact reviewed package" in copy
                    highlight = spotlight.get_by_text(note.highlights[0], exact=True)
                    assert highlight.count() == 1
                    highlight.scroll_into_view_if_needed()
                    assert highlight.is_visible()
                    assert highlight.evaluate("""element => {
                    const box = element.getBoundingClientRect();
                    return element.scrollWidth <= element.clientWidth + 1
                        && box.left >= 0 && box.right <= window.innerWidth + 1;
                }""")
                    capture = _failure_screenshot_path(f"release-note-current-{source}-{width}")
                    if capture is not None:
                        capture.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(capture), full_page=True)
                    last_highlight = spotlight.get_by_text(note.highlights[-1], exact=True)
                    last_highlight.scroll_into_view_if_needed()
                    assert last_highlight.evaluate("""element => {
                    const box = element.getBoundingClientRect();
                    const viewport = element.closest('.upgrade-spotlight-main').getBoundingClientRect();
                    return box.top >= viewport.top - 1 && box.bottom <= viewport.bottom + 1
                        && box.left >= viewport.left - 1 && box.right <= viewport.right + 1;
                }""")
                    notes_link = spotlight.get_by_role("link", name=note.note_link_label, exact=True)
                    notes_link.scroll_into_view_if_needed()
                    assert notes_link.is_visible()
                    if capture is not None:
                        page.screenshot(path=str(capture.with_stem(capture.stem + "-end")), full_page=True)
                    page.locator("#upgradeSpotlightDismiss").click(timeout=5000)
                    page.locator("#upgradeReopen").click()
                    assert note.highlights[0] in spotlight.inner_text()
                    page.keyboard.press("Escape")
                    assert not spotlight.is_visible()
                    page.locator("#upgradeReopen").click()
                    assert note.highlights[-1] in spotlight.inner_text()
                    _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430])
@pytest.mark.parametrize("explicit", [True, False])
def test_installer_fallback_keeps_complete_copy_without_authored_note(
    tmp_path: Path, monkeypatch, width: int, explicit: bool,
) -> None:
    _seed_consumer_repo(
        tmp_path, active_version="7.2.1", activation_history=["7.2.0", "7.2.1"],
    )
    complete_copy = (
        "Operators can review component responsibilities, inspect retained source references, "
        "compare the proposed changes, and verify the result before starting the next workstream. "
        "The release preserves consumer-authored records, including records outside the first "
        "visible view; it does not grant permission to replace them."
    )
    body = "# Release details\n\n- " + complete_copy
    highlights = _release_highlights(explicit=[complete_copy] if explicit else None, body=body)
    write_upgrade_spotlight(
        repo_root=tmp_path, from_version="7.2.0", to_version="7.2.1",
        release_tag="v7.2.1", release_url="https://example.invalid/releases/v7.2.1",
        release_published_at="", release_body=body, highlights=highlights,
    )
    assert release_notes.load_release_notes_source(repo_root=tmp_path, version="7.2.1") is None
    _render_shell(tmp_path, monkeypatch)
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            with browser.new_context(viewport={"width": width, "height": 932}) as context:
                with _new_page(context) as (page, observation):
                    page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
                    spotlight = page.locator("#shellUpgradeSpotlight")
                    spotlight.wait_for(timeout=15000)
                    assert complete_copy in spotlight.inner_text()
                    point = spotlight.get_by_text(complete_copy, exact=True)
                    assert point.count() == 1
                    point.scroll_into_view_if_needed()
                    assert point.evaluate("element => element.scrollWidth <= element.clientWidth + 1")
                    page.locator("#upgradeSpotlightDismiss").click(timeout=5000)
                    assert not spotlight.is_visible()
                    page.locator("#upgradeReopen").click()
                    assert complete_copy in spotlight.inner_text()
                    _assert_clean_page(page, observation)
