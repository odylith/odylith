from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from odylith.runtime.surfaces import render_compass_dashboard
from odylith.runtime.surfaces import render_tooling_dashboard as tooling_dashboard_renderer
from tests.integration.runtime.surface_browser_test_support import (
    _REPO_ROOT,
    _copy_logical_working_fixture,
    _new_page,
    _static_server,
)


def clone_odylith_fixture(tmp_path: Path) -> Path:
    fixture_root = tmp_path / "fixture"
    _copy_logical_working_fixture(_REPO_ROOT, fixture_root)
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
    current_rows = payload.get("current_workstreams", [])
    if isinstance(current_rows, list):
        payload["current_workstreams_by_window"] = {
            "24h": list(current_rows),
            "48h": list(current_rows),
        }
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


def covered_workstream_ids(compass) -> list[str]:  # noqa: ANN001
    return compass.locator("tr.ws-summary-row[data-covered-ws-id]").evaluate_all(
        """nodes => Array.from(new Set(
          nodes
            .map((node) => String(node.getAttribute("data-covered-ws-id") || "").trim())
            .filter((token) => /^B-\\d{3,}$/.test(token))
        ))"""
    )


def wait_for_current_workstreams(compass) -> None:  # noqa: ANN001
    compass.locator("tr.ws-summary-row[data-ws-id]").first.wait_for(timeout=15000)


def wait_for_current_workstreams_or_empty(compass) -> None:  # noqa: ANN001
    current_section = compass.locator("#current-workstreams")
    current_section.wait_for(timeout=15000)
    current_section.locator(
        "tr.ws-summary-row[data-ws-id], tr.ws-summary-row[data-covered-ws-id], .empty"
    ).first.wait_for(timeout=15000)


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


@contextmanager
def open_compass_page(fixture_root: Path, browser, *, query: str = "tab=compass&window=24h&date=live"):  # noqa: ANN001
    with _static_server(root=fixture_root) as base_url:
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        try:
            with _new_page(context) as (page, observation):
                response = page.goto(f"{base_url}/odylith/index.html?{query}", wait_until="domcontentloaded")
                assert response is not None and response.ok
                compass = page.frame_locator("#frame-compass")
                compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                yield page, compass, observation
        finally:
            context.close()
