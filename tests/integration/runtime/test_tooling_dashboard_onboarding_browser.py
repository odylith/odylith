from __future__ import annotations

import contextlib
import shutil
from pathlib import Path
from typing import Iterator

from odylith import cli
from odylith.install.state import write_install_state
from odylith.install.state import write_upgrade_spotlight
from odylith.install.state import write_version_pin
from odylith.runtime.surfaces import render_tooling_dashboard as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _browser,
    _click_visible,
    _failure_screenshot_path,
    _new_page,
    _static_server,
    _wait_for_shell_tab,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
_SURFACE_HEADINGS = {
    "radar": "Backlog Workstream Radar",
    "registry": "Component Registry",
    "casebook": "Casebook",
    "atlas": "Atlas",
    "compass": "Executive Compass",
}


def _seed_shell_assets(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    shutil.copytree(
        REPO_ROOT / "odylith" / "surfaces" / "brand",
        repo_root / "odylith" / "surfaces" / "brand",
        dirs_exist_ok=True,
    )
    for surface, heading in _SURFACE_HEADINGS.items():
        output_path = repo_root / "odylith" / surface / f"{surface}.html"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            (
                "<!doctype html>\n"
                '<html lang="en">\n'
                "<head>\n"
                '  <meta charset="utf-8" />\n'
                f"  <title>{heading}</title>\n"
                "  <style>\n"
                "    body { margin: 0; padding: 32px; background: linear-gradient(180deg, #eef5ff 0%, #ffffff 100%);"
                ' color: #17324d; font-family: "Avenir Next", "Segoe UI", sans-serif; }\n'
                "    main { display: grid; gap: 10px; }\n"
                "    h1 { margin: 0; font-size: 42px; color: #12386f; }\n"
                "    p { margin: 0; color: #47627f; line-height: 1.6; }\n"
                "  </style>\n"
                "</head>\n"
                "<body>\n"
                "  <main>\n"
                f"    <h1>{heading}</h1>\n"
                f"    <p>{heading} preview surface.</p>\n"
                "  </main>\n"
                "</body>\n"
                "</html>\n"
            ),
            encoding="utf-8",
        )


def _seed_consumer_repo(
    repo_root: Path,
    *,
    focus_path: str = "src/billing",
    existing_truth: bool = False,
    active_version: str = "1.2.3",
    activation_history: list[str] | None = None,
) -> None:
    _seed_shell_assets(repo_root)
    (repo_root / ".git").mkdir(parents=True, exist_ok=True)
    if focus_path:
        (repo_root / Path(focus_path)).mkdir(parents=True, exist_ok=True)
    write_install_state(
        repo_root=repo_root,
        payload={
            "active_version": active_version,
            "activation_history": activation_history or [active_version],
            "installed_versions": {
                active_version: {
                    "runtime_root": str(repo_root / ".odylith" / "runtime" / "versions" / active_version),
                    "verification": {"wheel_sha256": f"wheel-{active_version}"},
                }
            },
            "last_known_good_version": active_version,
        },
    )
    write_version_pin(repo_root=repo_root, version=active_version)
    if not existing_truth:
        return
    ideas_root = repo_root / "odylith" / "radar" / "source" / "ideas"
    ideas_root.mkdir(parents=True, exist_ok=True)
    (ideas_root / "B-001-first-item.md").write_text("# First item\n", encoding="utf-8")
    component_root = repo_root / "odylith" / "registry" / "source" / "components" / "billing"
    component_root.mkdir(parents=True, exist_ok=True)
    (component_root / "CURRENT_SPEC.md").write_text("# Billing\n", encoding="utf-8")
    atlas_root = repo_root / "odylith" / "atlas" / "source"
    atlas_root.mkdir(parents=True, exist_ok=True)
    (atlas_root / "billing-boundary-map.mmd").write_text("graph TD\n  A[Billing]\n", encoding="utf-8")


def _render_shell(repo_root: Path, monkeypatch) -> None:  # noqa: ANN001
    monkeypatch.setattr(
        renderer.odylith_context_engine_store,
        "load_delivery_surface_payload",
        lambda **kwargs: {},
    )
    monkeypatch.setattr(renderer, "_build_self_host_payload", lambda **kwargs: {})
    rc = renderer.main(["--repo-root", str(repo_root), "--output", "odylith/index.html"])
    assert rc == 0


def _render_shell_without_monkeypatch(repo_root: Path) -> None:
    original_loader = renderer.odylith_context_engine_store.load_delivery_surface_payload
    original_self_host = renderer._build_self_host_payload
    renderer.odylith_context_engine_store.load_delivery_surface_payload = lambda **kwargs: {}
    renderer._build_self_host_payload = lambda **kwargs: {}
    try:
        rc = renderer.main(["--repo-root", str(repo_root), "--output", "odylith/index.html"])
    finally:
        renderer.odylith_context_engine_store.load_delivery_surface_payload = original_loader
        renderer._build_self_host_payload = original_self_host
    assert rc == 0


def _fake_first_run_shell_sync(repo_root: Path):
    def fake_sync(argv: list[str]) -> int:
        assert argv == ["--repo-root", str(repo_root), "--force", "--impact-mode", "full"]
        _render_shell_without_monkeypatch(repo_root)
        return 0

    return fake_sync


def _fake_dashboard_refresh_with_real_shell(
    repo_root: Path,
    *,
    refresh_capture: dict[str, object] | None = None,
):
    def fake_refresh_dashboard_surfaces(**kwargs):  # noqa: ANN003
        if refresh_capture is not None:
            refresh_capture.update(kwargs)
        _render_shell_without_monkeypatch(repo_root)
        return 0

    return fake_refresh_dashboard_surfaces


@contextlib.contextmanager
def _repo_browser_context(repo_root: Path) -> Iterator[tuple[str, object]]:
    with _static_server(root=repo_root) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                yield base_url, context
            finally:
                context.close()


def _install_clipboard_probe(page) -> None:  # noqa: ANN001
    page.add_init_script(
        """
        window.__odylithClipboardWrites = [];
        try {
          Object.defineProperty(navigator, "clipboard", {
            configurable: true,
            value: {
              writeText: async (text) => {
                window.__odylithClipboardWrites.push(String(text));
              },
            },
          });
        } catch (_error) {
          // Ignore environments that lock navigator.clipboard.
        }
        const originalExecCommand = document.execCommand ? document.execCommand.bind(document) : null;
        document.execCommand = (command) => {
          if (String(command || "").toLowerCase() === "copy") {
            const active = document.activeElement;
            const value = active && typeof active.value === "string" ? active.value : "";
            window.__odylithClipboardWrites.push(String(value));
            return true;
          }
          return originalExecCommand ? originalExecCommand(command) : false;
        };
        """
    )


def _clipboard_writes(page) -> list[str]:  # noqa: ANN001
    return [str(item) for item in page.evaluate("() => window.__odylithClipboardWrites.slice()")]


def _block_storage(page, *, block_local: bool, block_session: bool) -> None:  # noqa: ANN001
    snippets: list[str] = []
    if block_local:
        snippets.append(
            """
            Object.defineProperty(window, "localStorage", {
              configurable: true,
              get() { throw new Error("localStorage blocked for test"); },
            });
            """
        )
    if block_session:
        snippets.append(
            """
            Object.defineProperty(window, "sessionStorage", {
              configurable: true,
              get() { throw new Error("sessionStorage blocked for test"); },
            });
            """
        )
    if snippets:
        page.add_init_script("\n".join(snippets))


def test_first_install_launchpad_stays_primary_path_and_never_leaks_upgrade_popup(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "consumer-repo"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=False,
        active_version="1.2.3",
        activation_history=["1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="This stale payload must stay hidden on first install.",
        highlights=("Should not show.",),
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        _install_clipboard_probe(page)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        welcome = page.locator("#shellWelcomeState")
        welcome.wait_for(timeout=15000)
        assert welcome.get_attribute("aria-hidden") in {None, "false"}
        assert page.locator("#shellUpgradeSpotlight").count() == 0
        assert page.locator("#upgradeReopen").is_hidden()
        assert page.locator("#welcomeReopen").is_hidden()
        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.3"
        assert page.locator(".welcome-title").inner_text().strip() == "Start Odylith from one real code path"
        assert page.locator(".welcome-chip").count() == 0
        assert page.locator(".welcome-slice-path code").inner_text().strip() == "src/billing"
        assert "Open Radar view" in page.locator("#shellWelcomeState").inner_text()
        assert "Open Registry view" in page.locator("#shellWelcomeState").inner_text()
        assert "Open Atlas view" in page.locator("#shellWelcomeState").inner_text()

        handle_box = page.locator("#gridBriefToggle").bounding_box()
        welcome_box = welcome.bounding_box()
        assert handle_box is not None
        assert welcome_box is not None
        assert welcome_box["x"] >= (handle_box["x"] + handle_box["width"] - 1)

        _click_visible(page.locator("#welcomeCopyPrompt"))
        page.locator("#welcomeCopyStatus", has_text="Starter prompt copied. Paste it into your agent.").wait_for(
            timeout=15000
        )
        writes = _clipboard_writes(page)
        assert writes
        assert writes[-1].startswith("Use Odylith to start this repo from one real code path.")

        _click_visible(page.locator("#welcomeDismiss"))
        page.wait_for_function(
            "() => { const node = document.getElementById('shellWelcomeState'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)
        assert page.locator("#upgradeReopen").is_hidden()

        page.reload(wait_until="domcontentloaded")
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)
        page.wait_for_function(
            "() => { const node = document.getElementById('shellWelcomeState'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )
        assert page.locator("#upgradeReopen").is_hidden()

        _click_visible(page.locator("#welcomeReopen"))
        welcome.wait_for(timeout=15000)
        page.keyboard.press("Escape")
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)

        _click_visible(page.locator("#welcomeReopen"))
        _click_visible(page.locator('[data-welcome-tab="registry"]'))
        _wait_for_shell_tab(page, "registry")
        page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)

        _click_visible(page.locator("#welcomeReopen"))
        _click_visible(page.locator('[data-welcome-tab="atlas"]'))
        _wait_for_shell_tab(page, "atlas")
        page.frame_locator("#frame-atlas").locator("h1", has_text="Atlas").wait_for(timeout=15000)
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)

        _click_visible(page.locator("#welcomeReopen"))
        _click_visible(page.locator('[data-welcome-tab="radar"]'))
        _wait_for_shell_tab(page, "radar")
        page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_empty_repo_launchpad_stays_honest_and_never_invents_a_fake_path(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "empty-consumer"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="",
        existing_truth=False,
        active_version="1.2.3",
        activation_history=["1.2.3"],
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        assert page.locator(".welcome-card-slice .welcome-card-kicker", has_text="No starting path yet").count() == 1
        assert page.locator(".welcome-slice-empty", has_text="No path detected yet").count() == 1
        assert page.locator(".welcome-slice-path code").count() == 0
        assert "src/app" not in page.locator(".welcome-card-slice").inner_text()
        assert "empty-consumer" not in page.locator(".welcome-card-slice").inner_text()

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_cheatsheet_drawer_filters_and_copies_commands(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "consumer-cheatsheet"
    repo_root.mkdir()
    _seed_consumer_repo(repo_root, existing_truth=True)
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        _install_clipboard_probe(page)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        _click_visible(page.locator("#odylithToggle", has_text="Cheatsheet"))
        page.locator("#agentCheatsheetSearch").wait_for(timeout=15000)
        page.locator(".cheatsheet-card-title", has_text="Create a Radar backlog item").wait_for(timeout=15000)
        assert page.locator("#agentCheatsheetEmpty").is_hidden()

        search = page.locator("#agentCheatsheetSearch")
        search.fill("developer note")
        page.locator(".cheatsheet-card-title", has_text="Add a developer note").wait_for(timeout=15000)
        assert page.locator(".cheatsheet-card", has_text="Create a Radar backlog item").first.is_hidden()
        assert page.locator("#agentCheatsheetEmpty").is_hidden()

        note_card = page.locator(".cheatsheet-card", has_text="Add a developer note").first
        _click_visible(note_card.locator("button", has_text="Copy prompt"))
        page.locator("#agentCheatsheetCopyStatus", has_text="Prompt copied.").wait_for(timeout=15000)
        writes = _clipboard_writes(page)
        assert writes
        assert writes[-1] == 'Create a developer note titled "Compass refresh drift".'

        search.fill("watch-transactions")
        page.locator(".cheatsheet-card-title", has_text="Keep Compass warm").wait_for(timeout=15000)
        assert page.locator(".cheatsheet-card", has_text="Add a developer note").first.is_hidden()

        watch_card = page.locator(".cheatsheet-card", has_text="Keep Compass warm").first
        _click_visible(watch_card.locator("button", has_text="Copy CLI"))
        page.locator("#agentCheatsheetCopyStatus", has_text="CLI equivalent copied.").wait_for(timeout=15000)
        writes = _clipboard_writes(page)
        assert writes
        assert writes[-1] == "odylith compass watch-transactions --repo-root . --interval-seconds 10"

        search.fill("")
        _click_visible(page.locator('[data-cheatsheet-filter="validate"]'))
        page.locator(".cheatsheet-card-title", has_text="Check self-host posture").wait_for(timeout=15000)
        assert page.locator(".cheatsheet-card", has_text="Create a Radar backlog item").first.is_hidden()
        assert page.locator("#agentCheatsheetEmpty").is_hidden()

        search.fill("zzzzzz-no-cheatsheet-match")
        page.locator("#agentCheatsheetEmpty", has_text="No workflows match this search yet.").wait_for(timeout=15000)
        assert page.locator(".cheatsheet-card:visible").count() == 0

        page.keyboard.press("Escape")
        page.wait_for_function(
            "() => { const drawer = document.getElementById('odylithDrawer'); return Boolean(drawer && !drawer.classList.contains('open')); }",
            timeout=15000,
        )

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_incremental_upgrade_spotlight_has_clear_exits_and_clean_reopen_path(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-consumer"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body=(
            "Odylith now gives upgrades a cleaner upgrade handoff.\n\n"
            "The dashboard is already refreshed, so the repo is ready to use immediately."
        ),
        highlights=(
            "Cleaner upgrade messaging.",
            "Starter guide stays separate from release notes.",
            "Dashboard refresh lands before the user keeps working.",
        ),
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        spotlight = page.locator("#shellUpgradeSpotlight")
        spotlight.wait_for(timeout=15000)
        assert page.locator("#shellWelcomeState").count() == 0
        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.3"
        assert page.locator("#toolbarVersionStoryLink").count() == 0
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "Odylith v1.2.3 is ready here"
        assert (
            "Upgrade complete. v1.2.3 is live in this repo, and the full release note is ready on the right."
            in page.locator("#shellUpgradeSpotlight .upgrade-spotlight-main").inner_text()
        )
        assert (
            "The dashboard is already refreshed, so the repo is ready to use immediately."
            not in page.locator("#shellUpgradeSpotlight .upgrade-spotlight-main").inner_text()
        )
        assert "From v1.2.2" not in page.locator("#shellUpgradeSpotlight").inner_text()
        assert "Now v1.2.3" not in page.locator("#shellUpgradeSpotlight").inner_text()
        assert (
            page.locator("#shellUpgradeSpotlight .upgrade-spotlight-secondary-link").get_attribute("href")
            == "https://example.com/releases/v1.2.3"
        )
        assert (
            "Close this note with the X, click outside the card, or press Escape."
            in page.locator("#shellUpgradeSpotlight").inner_text()
        )

        _click_visible(page.locator("#upgradeSpotlightDismiss"))
        page.wait_for_function(
            "() => { const node = document.getElementById('shellUpgradeSpotlight'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)
        assert page.locator("#welcomeReopen").is_hidden()

        page.reload(wait_until="domcontentloaded")
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)
        page.wait_for_function(
            "() => { const node = document.getElementById('shellUpgradeSpotlight'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )

        _click_visible(page.locator("#upgradeReopen"))
        spotlight.wait_for(timeout=15000)
        page.keyboard.press("Escape")
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)

        _click_visible(page.locator("#upgradeReopen"))
        page.locator("#shellUpgradeSpotlight").click(position={"x": 12, "y": 12})
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)

        _click_visible(page.locator("#tab-registry"))
        _wait_for_shell_tab(page, "registry")
        page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        page.reload(wait_until="domcontentloaded")
        _wait_for_shell_tab(page, "registry")
        page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_incremental_upgrade_suppresses_starter_guide_until_the_user_reopens_it(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-without-truth"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=False,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="Upgrade first, starter guide second.",
        highlights=("Upgrade summary first.",),
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        page.wait_for_function(
            "() => { const node = document.getElementById('shellWelcomeState'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )
        assert page.locator("#welcomeReopen").is_hidden()

        _click_visible(page.locator("#upgradeSpotlightDismiss"))
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)
        page.locator("#upgradeReopen", has_text="Show v1.2.3 note").wait_for(timeout=15000)

        _click_visible(page.locator("#welcomeReopen"))
        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        assert page.locator(".welcome-title").inner_text().strip() == "Start Odylith from one real code path"

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_release_spotlight_and_release_note_links_work_in_browser(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-links"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body=(
            "Odylith now gives upgrades a cleaner upgrade handoff.\n\n"
            "The dashboard is already refreshed, so the repo is ready to use immediately."
        ),
        highlights=(
            "Cleaner upgrade messaging.",
            "Starter guide stays separate from release notes.",
            "Dashboard refresh lands before the user keeps working.",
        ),
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        context.route(
            "https://example.com/**",
            lambda route: route.fulfill(
                status=200,
                content_type="text/html",
                body="<!doctype html><html><body><h1>Mock release page</h1></body></html>",
            ),
        )
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        with page.expect_popup() as popup_info:
            _click_visible(page.locator("#shellUpgradeSpotlight .upgrade-spotlight-secondary-link"))
        popup = popup_info.value
        popup.wait_for_load_state("domcontentloaded")
        assert popup.locator("h1").inner_text().strip() == "Mock release page"
        popup.close()

        _click_visible(page.locator("#shellUpgradeSpotlight .upgrade-spotlight-link"))
        page.wait_for_function(
            "() => window.location.pathname.endsWith('/odylith/release-notes/1.2.3.html')",
            timeout=15000,
        )
        page.locator(".release-title", has_text="What's new in v1.2.3").wait_for(timeout=15000)

        with page.expect_popup() as popup_info:
            _click_visible(page.locator(".release-note-link"))
        popup = popup_info.value
        popup.wait_for_load_state("domcontentloaded")
        assert popup.locator("h1").inner_text().strip() == "Mock release page"
        popup.close()

        _click_visible(page.locator(".release-back"))
        page.wait_for_function(
            "() => window.location.pathname.endsWith('/odylith/index.html')",
            timeout=15000,
        )
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_persistent_version_story_does_not_render_a_toolbar_link(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "persistent-version-story"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    notes_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: Persistent version story.\n"
            "highlights:\n"
            "  - Highlight one.\n"
            "---\n\n"
            "Persistent version story.\n\n"
            "Keep this note available from the shell."
        ),
        encoding="utf-8",
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.reload(wait_until="domcontentloaded")
        assert page.locator("#toolbarVersionStoryLink").count() == 0
        href = "release-notes/1.2.3.html"
        response = page.goto(base_url + "/odylith/" + href, wait_until="domcontentloaded")
        assert response is not None and response.ok
        assert "Persistent version story." in page.locator("main").inner_text()

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_upgrade_recovery_pill_expires_after_ten_minutes_even_without_rerender(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-expiry-consumer"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="Upgrade note body.",
        highlights=("Upgrade highlight.",),
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        page.add_init_script(
            """
            (() => {
              const realDate = Date;
              const shiftedNow = realDate.now() + (11 * 60 * 1000);
              class MockDate extends realDate {
                constructor(...args) {
                  super(...(args.length ? args : [shiftedNow]));
                }
                static now() {
                  return shiftedNow;
                }
              }
              MockDate.parse = realDate.parse;
              MockDate.UTC = realDate.UTC;
              window.Date = MockDate;
            })();
            """
        )
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.wait_for_function(
            "() => { const node = document.getElementById('shellUpgradeSpotlight'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )
        assert page.locator("#upgradeReopen").is_hidden()
        assert page.locator("#toolbarVersionStoryLink").count() == 0

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_open_shell_auto_reloads_after_dashboard_refresh_and_updates_version_label(
    tmp_path: Path, monkeypatch
) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-auto-refresh"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.2",
        activation_history=["1.2.2"],
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.2"
        assert page.locator("#shellUpgradeSpotlight").count() == 0

        write_install_state(
            repo_root=repo_root,
            payload={
                "active_version": "1.2.3",
                "activation_history": ["1.2.2", "1.2.3"],
                "installed_versions": {
                    "1.2.3": {
                        "runtime_root": str(repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"),
                        "verification": {"wheel_sha256": "wheel-1.2.3"},
                    }
                },
                "last_known_good_version": "1.2.3",
            },
        )
        write_version_pin(repo_root=repo_root, version="1.2.3")
        write_upgrade_spotlight(
            repo_root=repo_root,
            from_version="1.2.2",
            to_version="1.2.3",
            release_tag="v1.2.3",
            release_url="https://example.com/releases/v1.2.3",
            release_published_at="2026-03-30T14:00:00Z",
            release_body="Upgrade note body.",
            highlights=("Cleaner upgrade messaging.", "Release note comes first."),
        )
        _render_shell(repo_root, monkeypatch)

        page.wait_for_function(
            "() => { const node = document.querySelector('.toolbar-version'); return Boolean(node && node.textContent.trim() === 'v1.2.3'); }",
            timeout=15000,
        )
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "Odylith v1.2.3 is ready here"

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_welcome_dismiss_persists_with_session_storage_fallback_when_local_storage_is_blocked(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "session-storage-fallback"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=False,
        active_version="1.2.3",
        activation_history=["1.2.3"],
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        _block_storage(page, block_local=True, block_session=False)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        _click_visible(page.locator("#welcomeDismiss"))
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)

        page.reload(wait_until="domcontentloaded")
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)
        page.wait_for_function(
            "() => { const node = document.getElementById('shellWelcomeState'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_welcome_dismiss_still_closes_immediately_when_all_storage_is_blocked(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "all-storage-blocked"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=False,
        active_version="1.2.3",
        activation_history=["1.2.3"],
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        _block_storage(page, block_local=True, block_session=True)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        _click_visible(page.locator("#welcomeDismiss"))
        page.locator("#welcomeReopen", has_text="Show starter guide").wait_for(timeout=15000)

        page.reload(wait_until="domcontentloaded")
        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        assert page.locator("#welcomeReopen").is_hidden()

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_cli_install_renders_a_browser_valid_first_run_launchpad(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "cli-install-consumer"
    repo_root.mkdir()
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"

    def fake_install_bundle(**kwargs):  # noqa: ANN003
        _seed_consumer_repo(
            repo_root,
            focus_path="src/billing",
            existing_truth=False,
            active_version="1.2.3",
            activation_history=["1.2.3"],
        )
        return type(
            "InstallSummary",
            (),
            {
                "version": "1.2.3",
                "repo_root": repo_root,
                "launcher_path": launcher_path,
                "repo_guidance_created": False,
                "git_repo_present": True,
                "gitignore_updated": True,
            },
        )()

    monkeypatch.setattr(cli, "install_bundle", fake_install_bundle)
    monkeypatch.setattr(cli.sync_workstream_artifacts, "main", _fake_first_run_shell_sync(repo_root))

    rc = cli.main(["install", "--repo-root", str(repo_root), "--no-open"])

    assert rc == 0
    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok
        page.locator("#shellWelcomeState").wait_for(timeout=15000)
        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.3"
        assert page.locator(".welcome-title").inner_text().strip() == "Start Odylith from one real code path"
        assert page.locator("#shellUpgradeSpotlight").count() == 0
        assert page.locator(".welcome-slice-path code").inner_text().strip() == "src/billing"
        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_cli_install_adopt_latest_renders_a_browser_valid_incremental_upgrade_note(
    tmp_path: Path, monkeypatch
) -> None:  # noqa: ANN001
    repo_root = tmp_path / "cli-install-adopt-latest-consumer"
    repo_root.mkdir()
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.2",
        activation_history=["1.2.2"],
    )
    _render_shell_without_monkeypatch(repo_root)

    def fake_install_bundle(**kwargs):  # noqa: ANN003
        return type(
            "InstallSummary",
            (),
            {
                "version": "1.2.2",
                "repo_root": repo_root,
                "launcher_path": launcher_path,
                "repo_guidance_created": False,
                "git_repo_present": True,
                "gitignore_updated": False,
            },
        )()

    def fake_upgrade_install(**kwargs):  # noqa: ANN003
        write_install_state(
            repo_root=repo_root,
            payload={
                "active_version": "1.2.3",
                "activation_history": ["1.2.2", "1.2.3"],
                "installed_versions": {
                    "1.2.3": {
                        "runtime_root": str(repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"),
                        "verification": {"wheel_sha256": "wheel-1.2.3"},
                    }
                },
                "last_known_good_version": "1.2.3",
            },
        )
        write_version_pin(repo_root=repo_root, version="1.2.3")
        return type(
            "UpgradeSummary",
            (),
            {
                "active_version": "1.2.3",
                "launcher_path": launcher_path,
                "pin_changed": True,
                "pinned_version": "1.2.3",
                "previous_version": "1.2.2",
                "repo_role": "consumer_repo",
                "followed_latest": True,
                "release_tag": "v1.2.3",
                "release_body": "Upgrade note body.",
                "release_highlights": ("Cleaner upgrade messaging.", "Release note comes first."),
                "release_published_at": "2026-03-30T14:00:00Z",
                "release_url": "https://example.com/releases/v1.2.3",
            },
        )()

    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(cli, "install_bundle", fake_install_bundle)
    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        _fake_dashboard_refresh_with_real_shell(repo_root, refresh_capture=refresh_capture),
    )

    rc = cli.main(["install", "--repo-root", str(repo_root), "--adopt-latest", "--no-open"])

    assert rc == 0
    assert refresh_capture["surfaces"] == ("tooling_shell", "radar", "compass")
    assert refresh_capture["runtime_mode"] == "auto"
    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.3"
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "Odylith v1.2.3 is ready here"
        assert page.locator("#upgradeReopen").is_hidden()
        assert page.locator("#shellWelcomeState").count() == 0
        assert (repo_root / "odylith" / "release-notes" / "1.2.3.html").is_file()
        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_cli_upgrade_renders_a_browser_valid_incremental_upgrade_note(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "cli-upgrade-consumer"
    repo_root.mkdir()
    launcher_path = repo_root / ".odylith" / "bin" / "odylith"
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.2",
        activation_history=["1.2.2"],
    )

    def fake_upgrade_install(**kwargs):  # noqa: ANN003
        write_install_state(
            repo_root=repo_root,
            payload={
                "active_version": "1.2.3",
                "activation_history": ["1.2.2", "1.2.3"],
                "installed_versions": {
                    "1.2.3": {
                        "runtime_root": str(repo_root / ".odylith" / "runtime" / "versions" / "1.2.3"),
                        "verification": {"wheel_sha256": "wheel-1.2.3"},
                    }
                },
                "last_known_good_version": "1.2.3",
            },
        )
        write_version_pin(repo_root=repo_root, version="1.2.3")
        return type(
            "UpgradeSummary",
            (),
            {
                "active_version": "1.2.3",
                "launcher_path": launcher_path,
                "pin_changed": False,
                "pinned_version": "1.2.3",
                "previous_version": "1.2.2",
                "repo_role": "consumer_repo",
                "followed_latest": False,
                "release_tag": "v1.2.3",
                "release_body": "Upgrade note body.",
                "release_highlights": ("Cleaner upgrade messaging.", "Release note comes first."),
                "release_published_at": "2026-03-30T14:00:00Z",
                "release_url": "https://example.com/releases/v1.2.3",
            },
        )()

    refresh_capture: dict[str, object] = {}

    monkeypatch.setattr(cli, "upgrade_install", fake_upgrade_install)
    monkeypatch.setattr(
        cli.sync_workstream_artifacts,
        "refresh_dashboard_surfaces",
        _fake_dashboard_refresh_with_real_shell(repo_root, refresh_capture=refresh_capture),
    )

    rc = cli.main(["upgrade", "--repo-root", str(repo_root), "--to", "1.2.3"])

    assert rc == 0
    assert refresh_capture["surfaces"] == ("tooling_shell", "radar", "compass")
    assert refresh_capture["runtime_mode"] == "auto"
    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator(".toolbar-version").inner_text().strip() == "v1.2.3"
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "Odylith v1.2.3 is ready here"
        assert page.locator("#upgradeReopen").is_hidden()
        assert page.locator("#shellWelcomeState").count() == 0
        assert (repo_root / "odylith" / "release-notes" / "1.2.3.html").is_file()
        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_release_note_page_stays_sanitized_and_navigates_back_to_dashboard(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    repo_root = tmp_path / "release-note-consumer"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.3",
        activation_history=["1.2.2", "1.2.3"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.2",
        to_version="1.2.3",
        release_tag="v1.2.3",
        release_url="https://example.com/releases/v1.2.3",
        release_published_at="2026-03-30T14:00:00Z",
        release_body="Fallback upgrade copy.",
        highlights=("Fallback highlight.",),
    )
    notes_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    notes_root.mkdir(parents=True, exist_ok=True)
    (notes_root / "v1.2.3.md").write_text(
        (
            "---\n"
            "version: 1.2.3\n"
            "published_at: 2026-03-30T14:00:00Z\n"
            "summary: <script>alert(1)</script> summary\n"
            "highlights:\n"
            "  - <script>alert(2)</script> highlight\n"
            "---\n\n"
            "First paragraph stays readable.\n\n"
            "<script>alert(3)</script> detail paragraph."
        ),
        encoding="utf-8",
    )
    _render_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/release-notes/1.2.3.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator(".release-title", has_text="What's new in v1.2.3").wait_for(timeout=15000)
        page_text = page.locator("body").inner_text()
        page_html = page.content()
        assert "alert(1) summary" in page_text
        assert "alert(2) highlight" in page_text
        assert "alert(3) detail paragraph." in page_text
        assert "What Odylith already did" not in page_text
        assert "How to use it" not in page_text
        assert "<script>alert(1)</script> summary" not in page_html
        assert "<script>alert(2)</script> highlight" not in page_html
        assert "<script>alert(3)</script> detail paragraph." not in page_html
        assert str(repo_root.resolve()) not in page_html

        _click_visible(page.locator(".release-back"))
        page.wait_for_function(
            "() => window.location.pathname.endsWith('/odylith/index.html')",
            timeout=15000,
        )
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)

        _assert_clean_page(
            page,
            console_errors,
            page_errors,
            failed_requests,
            bad_responses,
            screenshot_path=_failure_screenshot_path("release-note-page"),
        )
