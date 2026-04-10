from __future__ import annotations

import json
import shutil
from pathlib import Path

from odylith.runtime.surfaces import render_compass_dashboard
from odylith.runtime.surfaces import render_tooling_dashboard as tooling_dashboard_renderer
from tests.integration.runtime.surface_browser_test_support import (
    _REPO_ROOT,
    _new_page,
    _static_server,
)


class _ManagedBrowserContext:
    def __init__(self, context, server_context) -> None:  # noqa: ANN001
        self._context = context
        self._server_context = server_context
        self._closed = False

    def __getattr__(self, name: str):  # noqa: ANN001
        return getattr(self._context, name)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._context.close()
        finally:
            self._server_context.__exit__(None, None, None)


def clone_odylith_fixture(tmp_path: Path) -> Path:
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")
    return fixture_root


def render_compass_fixture(fixture_root: Path) -> None:
    assert render_compass_dashboard.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/compass/compass.html",
        ]
    ) == 0
    assert tooling_dashboard_renderer.main(
        [
            "--repo-root",
            str(fixture_root),
            "--output",
            "odylith/index.html",
        ]
    ) == 0


def runtime_paths(fixture_root: Path) -> tuple[Path, Path, Path]:
    runtime_root = fixture_root / "odylith" / "compass" / "runtime"
    return (
        runtime_root / "current.v1.json",
        runtime_root / "current.v1.js",
        fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json",
    )


def load_runtime_payload(fixture_root: Path) -> dict[str, object]:
    current_json_path, _current_js_path, _source_truth_path = runtime_paths(fixture_root)
    return json.loads(current_json_path.read_text(encoding="utf-8"))


def write_runtime_payload(fixture_root: Path, payload: dict[str, object]) -> None:
    current_json_path, current_js_path, _source_truth_path = runtime_paths(fixture_root)
    current_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    current_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )


def current_workstream_ids(compass) -> list[str]:  # noqa: ANN001
    return compass.locator("tr.ws-summary-row[data-ws-id]").evaluate_all(
        """nodes => Array.from(new Set(
          nodes
            .map((node) => String(node.getAttribute("data-ws-id") || "").trim())
            .filter((token) => /^B-\\d{3,}$/.test(token))
        ))"""
    )


def wait_for_current_workstreams(compass) -> None:  # noqa: ANN001
    compass.locator("tr.ws-summary-row[data-ws-id]").first.wait_for(timeout=15000)


def wait_for_current_workstreams_or_empty(compass) -> None:  # noqa: ANN001
    current_section = compass.locator("#current-workstreams")
    current_section.wait_for(timeout=15000)
    current_section.locator("tr.ws-summary-row[data-ws-id], .empty").first.wait_for(timeout=15000)


def release_target_ids(compass) -> list[str]:  # noqa: ANN001
    return compass.locator("#release-groups .execution-wave-chip-link").evaluate_all(
        """nodes => Array.from(new Set(
          nodes
            .map((node) => (node.textContent || "").trim())
            .filter((token) => /^B-\\d{3,}$/.test(token))
        ))"""
    )


def program_member_ids(compass) -> list[str]:  # noqa: ANN001
    return compass.locator("#execution-waves-host .execution-wave-chip-link").evaluate_all(
        """nodes => Array.from(new Set(
          nodes
            .map((node) => (node.textContent || "").trim())
            .filter((token) => /^B-\\d{3,}$/.test(token))
        ))"""
    )


def scope_option_values(compass) -> list[str]:  # noqa: ANN001
    return compass.locator("#scope-select option").evaluate_all(
        """nodes => nodes.map((node) => String(node.value || "").trim())"""
    )


def selected_scope_value(compass) -> str:  # noqa: ANN001
    return str(compass.locator("#scope-select").input_value() or "").strip()


def open_compass_page(fixture_root: Path, browser, *, query: str = "tab=compass&window=24h&date=live"):  # noqa: ANN001
    server_context = _static_server(root=fixture_root)
    base_url = server_context.__enter__()
    context = browser.new_context(viewport={"width": 1440, "height": 1100})
    managed_context = _ManagedBrowserContext(context, server_context)
    try:
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(f"{base_url}/odylith/index.html?{query}", wait_until="domcontentloaded")
        assert response is not None and response.ok
        compass = page.frame_locator("#frame-compass")
        compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
        return managed_context, page, compass, console_errors, page_errors, failed_requests, bad_responses
    except Exception:
        managed_context.close()
        raise
