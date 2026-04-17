from __future__ import annotations

import re
from urllib.parse import quote

import pytest

from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _new_page,
    _wait_for_compass_ready,
    _wait_for_shell_query_param,
    browser_context,
    compact_browser_context,
)


def _wait_for_frame_locator_count(page, frame_selector: str, selector: str, expected: int) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ frameSelector, selector, expected }) => {
          const frame = document.querySelector(frameSelector);
          const doc = frame && frame.contentDocument;
          if (!doc) return false;
          return doc.querySelectorAll(selector).length === expected;
        }""",
        arg={"frameSelector": frame_selector, "selector": selector, "expected": expected},
        timeout=15000,
    )


def _assert_frame_has_no_horizontal_overflow(frame, *, max_slack_px: int = 8) -> None:  # noqa: ANN001
    metrics = frame.locator("body").evaluate(
        """() => ({
          htmlClientWidth: document.documentElement.clientWidth,
          htmlScrollWidth: document.documentElement.scrollWidth,
          bodyClientWidth: document.body.clientWidth,
          bodyScrollWidth: document.body.scrollWidth,
        })"""
    )
    max_client_width = max(int(metrics["htmlClientWidth"]), int(metrics["bodyClientWidth"]))
    max_scroll_width = max(int(metrics["htmlScrollWidth"]), int(metrics["bodyScrollWidth"]))
    assert max_scroll_width <= max_client_width + max_slack_px, metrics


def _assert_atlas_viewer_image_loaded(page) -> None:  # noqa: ANN001
    page.wait_for_function(
        """() => {
          const frame = document.querySelector("#frame-atlas");
          const doc = frame && frame.contentDocument;
          const image = doc && doc.querySelector("#viewerImage");
          if (!image || !image.complete) return false;
          const rect = image.getBoundingClientRect();
          return image.naturalWidth > 0
            && image.naturalHeight > 0
            && rect.width > 120
            && rect.height > 80;
        }""",
        timeout=15000,
    )


def test_registry_execution_engine_hard_cut_is_visible_and_alias_free(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + "/odylith/index.html?tab=registry&component=execution-engine",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="registry", key="component", value="execution-engine")
    registry.locator('button[data-component="execution-engine"].active').wait_for(timeout=15000)
    registry.locator("#detail .component-name", has_text="Execution Engine").wait_for(timeout=15000)

    detail_text = registry.locator("#detail").inner_text().strip()
    assert "Constraint-aware execution runtime" in detail_text
    active_button_text = registry.locator('button[data-component="execution-engine"].active').inner_text().lower()
    assert "execution-engine" in active_button_text
    assert "execution-governance" not in detail_text.lower()

    diagnostics = registry.locator("#diagnostics")
    if diagnostics.count() and not diagnostics.evaluate("(node) => node.hidden"):
        assert "execution-governance" not in diagnostics.inner_text().lower()

    registry.locator("#search").fill("execution-engine")
    _wait_for_frame_locator_count(page, "#frame-registry", "button[data-component]", 1)
    registry.locator('button[data-component="execution-engine"].active').wait_for(timeout=15000)

    registry.locator("#search").fill("execution-governance")
    _wait_for_frame_locator_count(page, "#frame-registry", "button[data-component]", 0)
    assert registry.locator("#detail").inner_text().strip() == ""

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_context_execution_diagrams_render_assets_and_canonical_links(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + "/odylith/index.html?tab=atlas&diagram=D-030",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text="D-030").wait_for(timeout=15000)
    atlas.locator("#diagramTitle", has_text="Execution Engine Stack").wait_for(timeout=15000)
    atlas.locator("#diagramFreshness", has_text="Fresh").wait_for(timeout=15000)
    _assert_atlas_viewer_image_loaded(page)
    registry_links_text = atlas.locator("#registryLinks").inner_text().lower()
    assert "execution-engine" in registry_links_text
    visible_contract_text = "\n".join(
        [
            atlas.locator("#diagramTitle").inner_text(),
            atlas.locator("#diagramSummary").inner_text(),
            atlas.locator("#componentList").inner_text(),
            atlas.locator("#registryLinks").inner_text(),
        ]
    ).lower()
    assert "execution-governance" not in visible_contract_text

    response = page.goto(
        base_url + "/odylith/index.html?tab=atlas&diagram=D-002",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    atlas.locator("#diagramId", has_text="D-002").wait_for(timeout=15000)
    atlas.locator("#diagramTitle", has_text=re.compile(r"Context And Agent Execution Stack", re.I)).wait_for(
        timeout=15000
    )
    _assert_atlas_viewer_image_loaded(page)
    d002_registry_text = atlas.locator("#registryLinks").inner_text().lower()
    assert "execution-engine" in d002_registry_text
    assert "odylith-context-engine" in d002_registry_text

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


@pytest.mark.parametrize(
    ("diagram_id", "required_phrases"),
    [
        (
            "D-004",
            ("execution engine snapshot", "visible intervention broker", "benchmark closure proof"),
        ),
        (
            "D-005",
            ("context engine packet", "execution engine snapshot", "visible intervention", "benchmark proof"),
        ),
        (
            "D-006",
            ("execution engine snapshots", "chat-visible intervention decisions", "benchmark proof routes"),
        ),
        (
            "D-009",
            ("execution engine snapshot", "visibility ledgers", "benchmark proof"),
        ),
        (
            "D-018",
            ("governed memory/session streams", "execution engine snapshots", "visible intervention broker"),
        ),
        (
            "D-020",
            ("intervention visibility ledgers", "benchmark proof", "runtime/write/validation boundaries"),
        ),
        (
            "D-024",
            ("full-product odylith-on versus raw-agent proof", "execution engine snapshot accuracy"),
        ),
        (
            "D-025",
            ("session streams", "delivery-ledger visibility proof", "visible intervention decisions"),
        ),
        (
            "D-026",
            ("execution engine snapshots", "visible intervention warnings", "benchmark acceptance"),
        ),
        (
            "D-028",
            ("execution engine posture", "visibility-ledger proof", "benchmark risk"),
        ),
        (
            "D-029",
            ("execution engine profile selection", "visible-intervention fail-visible policy", "benchmark cost gates"),
        ),
        (
            "D-036",
            ("execution engine snapshots", "visibility ledgers", "benchmark checks"),
        ),
        (
            "D-037",
            ("execution engine snapshot reuse", "visibility-status cache", "benchmark latency"),
        ),
    ],
)
def test_atlas_cross_stack_topology_diagrams_render_and_expose_alignment_language(
    browser_context,
    diagram_id: str,
    required_phrases: tuple[str, ...],
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + f"/odylith/index.html?tab=atlas&diagram={diagram_id}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text=diagram_id).wait_for(timeout=15000)
    atlas.locator("#diagramFreshness", has_text="Fresh").wait_for(timeout=15000)
    _assert_atlas_viewer_image_loaded(page)

    visible_text = "\n".join(
        [
            atlas.locator("#diagramTitle").inner_text(),
            atlas.locator("#diagramSummary").inner_text(),
            atlas.locator("#componentList").inner_text(),
            atlas.locator("#registryLinks").inner_text(),
        ]
    ).lower()
    for phrase in required_phrases:
        assert phrase in visible_text
    assert "execution-governance" not in visible_text

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_and_radar_expose_b099_context_execution_release_truth(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + "/odylith/index.html?tab=compass&scope=B-099&date=live",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    _wait_for_compass_ready(compass)
    compass.locator("#scope-pill", has_text="B-099").wait_for(timeout=15000)
    compass.locator(
        "#execution-waves-host",
        has_text="Context Engine and Execution Engine Seamless Alignment Program",
    ).wait_for(timeout=15000)
    compass.locator("#execution-waves-host", has_text="5-wave program").wait_for(timeout=15000)
    for workstream_id in ("B-100", "B-101", "B-102", "B-103", "B-104"):
        assert compass.locator(f'#execution-waves-host [data-execution-wave-scope="{workstream_id}"]').count() >= 1
    compass.locator("#release-groups-host", has_text="0.1.11").wait_for(timeout=15000)
    compass.locator("#release-groups-host", has_text="B-099").wait_for(timeout=15000)

    response = page.goto(
        base_url + "/odylith/index.html?tab=radar&workstream=B-099",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text="B-099").wait_for(timeout=15000)
    radar_detail_text = radar.locator("#detail").inner_text().lower()
    assert "context engine" in radar_detail_text
    assert "execution engine" in radar_detail_text
    registry_targets = radar.locator("#detail a.chip-registry-component").evaluate_all(
        """nodes => nodes.map((node) => {
          try {
            return new URL(node.href).searchParams.get("component") || "";
          } catch (_error) {
            return "";
          }
        }).map((token) => String(token || "").trim().toLowerCase()).filter(Boolean)"""
    )
    assert "execution-engine" in registry_targets
    assert "odylith-context-engine" in registry_targets

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_context_execution_surfaces_hold_in_compact_browser(compact_browser_context) -> None:  # noqa: ANN001
    base_url, context = compact_browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(
        base_url + "/odylith/index.html?tab=registry&component=execution-engine",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    registry = page.frame_locator("#frame-registry")
    registry.locator("#detail .component-name", has_text="Execution Engine").wait_for(timeout=15000)
    _assert_frame_has_no_horizontal_overflow(registry)

    response = page.goto(
        base_url + "/odylith/index.html?tab=atlas&diagram=D-030",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("#diagramTitle", has_text="Execution Engine Stack").wait_for(timeout=15000)
    _assert_atlas_viewer_image_loaded(page)
    _assert_frame_has_no_horizontal_overflow(atlas, max_slack_px=14)

    response = page.goto(
        base_url + f"/odylith/index.html?tab=compass&scope={quote('B-099')}&date=live",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    _wait_for_compass_ready(compass)
    compass.locator("#scope-pill", has_text="B-099").wait_for(timeout=15000)
    compass.locator("#execution-waves-host", has_text="Context Engine and Execution Engine").wait_for(timeout=15000)
    _assert_frame_has_no_horizontal_overflow(compass, max_slack_px=18)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
