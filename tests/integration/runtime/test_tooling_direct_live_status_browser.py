"""Direct-live exports retain version and release-note auto refresh."""

from pathlib import Path

from odylith.install.state import write_install_state, write_upgrade_spotlight, write_version_pin
from odylith.runtime.surfaces import render_tooling_dashboard as renderer
from tests.integration.runtime.surface_browser_test_support import _assert_clean_page, _click_visible, _new_page
from tests.integration.runtime.test_tooling_dashboard_onboarding_browser import (
    _repo_browser_context, _seed_consumer_repo, _wait_for_toolbar_version,
)


def _render_direct_shell(repo_root, monkeypatch):
    monkeypatch.setattr(renderer.delivery_surface_payload_runtime, "load_delivery_surface_payload", lambda **kwargs: {})
    monkeypatch.setattr(renderer, "_build_self_host_payload", lambda **kwargs: {})
    assert renderer.main(["--repo-root", str(repo_root), "--output", "odylith/export/index.html"]) == 0


def test_direct_live_shell_auto_reloads_after_dashboard_refresh_and_updates_version_label(
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
    _render_direct_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/export/index.html", wait_until="domcontentloaded")
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
        _render_direct_shell(repo_root, monkeypatch)

        _wait_for_toolbar_version(page, "v1.2.3")
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "v1.2.3"

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_direct_live_shell_auto_reload_reopens_new_upgrade_spotlight_after_prior_dismissal(
    tmp_path: Path, monkeypatch
) -> None:  # noqa: ANN001
    repo_root = tmp_path / "upgrade-auto-refresh-dismissal-scope"
    repo_root.mkdir()
    _seed_consumer_repo(
        repo_root,
        focus_path="src/billing",
        existing_truth=True,
        active_version="1.2.2",
        activation_history=["1.2.1", "1.2.2"],
    )
    write_upgrade_spotlight(
        repo_root=repo_root,
        from_version="1.2.1",
        to_version="1.2.2",
        release_tag="v1.2.2",
        release_url="https://example.com/releases/v1.2.2",
        release_published_at="2026-03-29T14:00:00Z",
        release_body="Prior upgrade note body.",
        highlights=("Prior release note.",),
    )
    _render_direct_shell(repo_root, monkeypatch)

    with _repo_browser_context(repo_root) as (base_url, context):
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + "/odylith/export/index.html", wait_until="domcontentloaded")
        assert response is not None and response.ok

        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "v1.2.2"

        _click_visible(page.locator("#upgradeSpotlightDismiss"))
        page.locator("#upgradeReopen", has_text="v1.2.2").wait_for(timeout=15000)
        page.reload(wait_until="domcontentloaded")
        page.locator("#upgradeReopen", has_text="v1.2.2").wait_for(timeout=15000)
        page.wait_for_function(
            "() => { const node = document.getElementById('shellUpgradeSpotlight'); return Boolean(node && node.hidden); }",
            timeout=15000,
        )

        write_install_state(
            repo_root=repo_root,
            payload={
                "active_version": "1.2.3",
                "activation_history": ["1.2.1", "1.2.2", "1.2.3"],
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
            release_body="New upgrade note body.",
            highlights=("New release note.",),
        )
        _render_direct_shell(repo_root, monkeypatch)

        _wait_for_toolbar_version(page, "v1.2.3")
        page.locator("#shellUpgradeSpotlight").wait_for(timeout=15000)
        assert page.locator("#upgradeSpotlightTitle").inner_text().strip() == "v1.2.3"
        assert page.locator("#upgradeReopen").is_hidden()

        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)

