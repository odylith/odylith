from __future__ import annotations

from datetime import datetime
from datetime import timezone
import json
from pathlib import Path
import pytest
import re
import shutil
import time
from urllib.parse import quote

from tests.integration.runtime.surface_browser_test_support import (
    _assert_atlas_selection,
    _assert_casebook_counts,
    _assert_casebook_selection,
    _assert_clean_page,
    _assert_compass_live_state,
    _assert_compass_selection,
    _assert_radar_selection,
    _assert_registry_selection,
    _atlas_related_workstreams,
    _atlas_selected_diagram,
    _atlas_total,
    _atlas_workstream_filter_value,
    _atlas_workstream_options,
    _browser,
    browser_context,
    _casebook_index_counts,
    _click_visible,
    _collect_sample_tokens,
    _discard_external_mermaid_cdn_failures,
    _new_page,
    _run_in_browser_thread,
    _select_radar_row_with_link,
    _static_server,
    _wait_for_shell_query_param,
    _wait_for_shell_tab,
)


_REPO_ROOT = Path(__file__).resolve().parents[3]
_RADAR_REDIRECT_ABORT_RE = re.compile(
    r"^GET http://127\.0\.0\.1:\d+/odylith/radar/backlog-(?:app|payload)\.v1\.js(?:\?[^ ]*)?$"
)


def _current_release_label() -> str:
    payload = json.loads((_REPO_ROOT / "odylith" / "radar" / "traceability-graph.v1.json").read_text(encoding="utf-8"))
    current = payload.get("current_release")
    if isinstance(current, dict):
        label = str(current.get("version") or current.get("tag") or current.get("display_label") or "").strip()
        if label.startswith("v") and len(label) > 1 and label[1].isdigit():
            label = label[1:]
        if label:
            return label
    return "current"


def test_browser_thread_preserves_skip_outcomes() -> None:
    with pytest.raises(pytest.skip.Exception):
        _run_in_browser_thread(lambda: pytest.skip("Playwright Chromium is not installed"))


def _ready_compass_fixture_root(tmp_path: Path) -> Path:
    fixture_root = tmp_path / "fixture"
    shutil.copytree(_REPO_ROOT / "odylith", fixture_root / "odylith")
    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    generated_instant = datetime.now(timezone.utc).replace(microsecond=0)
    generated_utc = generated_instant.isoformat().replace("+00:00", "Z")
    now_local_iso = generated_instant.astimezone().isoformat()

    def _ready_brief(fingerprint: str) -> dict[str, object]:
        return {
            "status": "ready",
            "source": "provider",
            "fingerprint": fingerprint,
            "generated_utc": generated_utc,
            "sections": [
                {
                    "key": "completed_in_window",
                    "label": "Completed in this window",
                    "bullets": [{"text": "A real standup brief is ready for this view.", "fact_ids": []}],
                },
                {
                    "key": "current_execution",
                    "label": "Current execution",
                    "bullets": [{"text": "Compass is showing a seeded live brief for browser proof.", "fact_ids": []}],
                },
                {
                    "key": "next_planned",
                    "label": "Next planned",
                    "bullets": [{"text": "This keeps the copy and layout checks deterministic.", "fact_ids": []}],
                },
                {
                    "key": "risks_to_watch",
                    "label": "Risks to watch",
                    "bullets": [{"text": "No extra risk callout for this seeded browser case.", "fact_ids": []}],
                },
            ],
            "evidence_lookup": {},
        }

    payload["generated_utc"] = generated_utc
    payload["now_local_iso"] = now_local_iso
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    standup_brief["24h"] = _ready_brief("seeded-ready-24h")
    standup_brief["48h"] = _ready_brief("seeded-ready-48h")
    payload["standup_brief"] = standup_brief
    payload["standup_brief_scoped"] = {"24h": {}, "48h": {}}
    runtime_json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    version_state_dir = fixture_root / ".odylith" / "runtime"
    version_state_dir.mkdir(parents=True, exist_ok=True)
    version_state_payload = {
        "schema_version": "odylith.dashboard.version_state.v1",
        "generated_utc": generated_utc,
        "source": "browser fixture",
        "active_version": "0.1.14",
        "pinned_version": "0.1.14",
        "authoritative_version": "0.1.14",
        "authoritative_label": "v0.1.14",
    }
    (version_state_dir / "odylith-version-state.v1.json").write_text(
        json.dumps(version_state_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    (version_state_dir / "odylith-version-state.v1.js").write_text(
        "window.__ODYLITH_VERSION_STATE__ = "
        + json.dumps(version_state_payload, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    return fixture_root


def _write_compass_fixture_runtime_payloads(
    fixture_root: Path,
    *,
    runtime_payload: dict[str, object],
    source_truth_payload: dict[str, object] | None = None,
) -> None:
    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    runtime_js_path = runtime_dir / "current.v1.js"
    runtime_json_path.write_text(json.dumps(runtime_payload, indent=2) + "\n", encoding="utf-8")
    runtime_js_path.write_text(
        "window.__ODYLITH_COMPASS_RUNTIME__ = " + json.dumps(runtime_payload, separators=(",", ":")) + ";\n",
        encoding="utf-8",
    )
    if source_truth_payload is not None:
        source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"
        source_truth_path.write_text(json.dumps(source_truth_payload, indent=2) + "\n", encoding="utf-8")


def _first_backlog_document_workstream_id(view: str) -> str:
    pattern = re.compile(rf"{re.escape(view)}:(B-\d{{3,}})")
    text = "".join(
        path.read_text(encoding="utf-8")
        for path in sorted((_REPO_ROOT / "odylith" / "radar").glob("backlog-document-shard-*.v1.js"))
    )
    match = pattern.search(text)
    assert match is not None, f"expected at least one Radar standalone document for view={view!r}"
    return str(match.group(1))


def _load_backlog_document_shard(path: Path) -> dict[str, object]:
    text = path.read_text(encoding="utf-8")
    payload = text.split(" || {}, ", 1)[1].rsplit(");", 1)[0]
    loaded = json.loads(payload)
    assert isinstance(loaded, dict)
    return loaded


def _first_traceable_plan_workstream_id() -> str:
    for path in sorted((_REPO_ROOT / "odylith" / "radar").glob("backlog-document-shard-*.v1.js")):
        for key, raw_document in _load_backlog_document_shard(path).items():
            html = (
                str(raw_document.get("html", ""))
                if isinstance(raw_document, dict)
                else str(raw_document or "")
            )
            if (
                key.startswith("plan:")
                and 'class="trace-groups"' in html
                and 'class="trace-link"' in html
                and 'class="trace-link trace-link-missing"' in html
            ):
                return key.split(":", 1)[1]
    raise AssertionError("expected at least one Radar plan document with existing and missing traceability cards")


def _wait_for_radar_standalone_document(page, *, workstream_id: str, view: str, timeout: int = 15000) -> None:  # noqa: ANN001
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=workstream_id, timeout=timeout)
    _wait_for_shell_query_param(page, tab="radar", key="view", value=view, timeout=timeout)
    deadline = time.monotonic() + (timeout / 1000)
    while time.monotonic() < deadline:
        frame_handle = page.locator("#frame-radar").element_handle()
        frame = frame_handle.content_frame() if frame_handle is not None else None
        if frame is not None:
            back_link = frame.locator("a.back")
            workstream_label = frame.locator("p.id")
            if back_link.count() and workstream_label.count():
                back_text = back_link.first.inner_text().strip()
                workstream_text = workstream_label.first.inner_text().strip()
                if back_text.startswith("Back to Backlog") and "Radar" in back_text and workstream_text == workstream_id:
                    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"
                    return
        page.wait_for_timeout(200)
    raise AssertionError(f"expected Radar standalone {view!r} document for {workstream_id}")


def _discard_radar_redirect_abort_failures(failed_requests: list[str]) -> None:
    failed_requests[:] = [entry for entry in failed_requests if not _RADAR_REDIRECT_ABORT_RE.match(entry)]


def test_registry_detail_hides_default_live_status_card(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(
        base_url + "/odylith/index.html?tab=registry&component=casebook",
        wait_until="domcontentloaded",
    )
    assert response and response.ok
    _assert_registry_selection(page, "casebook")
    registry = page.frame_locator("#frame-registry")
    registry.locator("#detail .component-name").wait_for(timeout=15000)
    assert registry.locator("#detail .operator-readout-shell").count() == 0
    detail_text = registry.locator("#detail").inner_text()
    assert "LIVE STATUS" not in detail_text
    assert "PRODUCT SUMMARY" not in detail_text
    assert "Proof Control" not in detail_text
    assert "Live Blocker" not in detail_text
    assert "Current blocker:" not in detail_text
    assert "Fingerprint:" not in detail_text
    assert "Frontier:" not in detail_text
    assert "Evidence tier:" not in detail_text
    assert "Truthful claim:" not in detail_text
    assert "Deployment truth:" not in detail_text
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_surface_entrypoints_redirect_into_shell_and_load_requested_surface(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    surfaces = (
        ("/odylith/radar/radar.html", "radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
        ("/odylith/registry/registry.html", "registry", "#frame-registry", "h1", "Component Registry"),
        ("/odylith/casebook/casebook.html", "casebook", "#frame-casebook", ".hero-title", "Casebook"),
        ("/odylith/atlas/atlas.html", "atlas", "#frame-atlas", "h1", "Atlas"),
        ("/odylith/compass/compass.html", "compass", "#frame-compass", "h1", "Executive Compass"),
    )
    for route, tab, frame_selector, heading_selector, heading_text in surfaces:
        page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
        response = page.goto(base_url + route, wait_until="domcontentloaded")
        assert response is not None and response.ok, route
        page.wait_for_url(re.compile(rf".*/odylith/index\.html\?tab={tab}([&#].*|$)"), timeout=15000)
        assert page.locator(f"#tab-{tab}").get_attribute("aria-selected") == "true"
        page.frame_locator(frame_selector).locator(heading_selector, has_text=heading_text).wait_for(timeout=15000)
        failed_requests.clear()
        bad_responses.clear()
        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_tooling_shell_routes_into_all_child_surfaces(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html", wait_until="domcontentloaded")
    assert response is not None and response.ok

    page.locator("#tab-radar").wait_for(timeout=15000)

    tab_expectations = (
        ("#tab-radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
        ("#tab-registry", "#frame-registry", "h1", "Component Registry"),
        ("#tab-casebook", "#frame-casebook", ".hero-title", "Casebook"),
        ("#tab-atlas", "#frame-atlas", "h1", "Atlas"),
        ("#tab-compass", "#frame-compass", "h1", "Executive Compass"),
    )

    for tab_selector, frame_selector, heading_selector, heading_text in tab_expectations:
        page.locator(tab_selector).click()
        frame = page.frame_locator(frame_selector)
        frame.locator(heading_selector, has_text=heading_text).wait_for(timeout=15000)
        assert page.locator(tab_selector).get_attribute("aria-selected") == "true"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_defaults_to_date_sort(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok

    radar = page.frame_locator("#frame-radar")
    radar.locator("#sort").wait_for(timeout=15000)
    assert radar.locator("#sort").input_value() == "date"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_window_switches_keep_brief_visible(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    page.locator("#tab-compass").wait_for(timeout=15000)
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator('button[data-window="48h"].active').wait_for(timeout=15000)
    compass.get_by_role("button", name="24h Window").click()
    _wait_for_shell_query_param(page, tab="compass", key="window", value="24h")
    _assert_compass_live_state(compass, window_token="24h")

    compass.get_by_role("button", name="48h Window").click()
    _wait_for_shell_query_param(page, tab="compass", key="window", value="48h")
    _assert_compass_live_state(compass, window_token="48h")

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_desktop_layout_keeps_main_and_right_rail_separated(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=48h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="48h")

    layout = compass.locator(".layout").evaluate(
        """(node) => {
            const stacks = Array.from(node.querySelectorAll(':scope > .stack'));
            const firstBox = stacks[0] ? stacks[0].getBoundingClientRect() : null;
            const secondBox = stacks[1] ? stacks[1].getBoundingClientRect() : null;
            return {
              stackCount: stacks.length,
              horizontalGap: firstBox && secondBox ? (secondBox.left - firstBox.right) : 0,
              gridTemplateColumns: getComputedStyle(node).gridTemplateColumns,
            };
        }"""
    )
    assert layout["stackCount"] >= 2
    assert layout["horizontalGap"] >= 38

    release_targets = compass.locator("#release-groups-host .release-groups-card").evaluate(
        """(node) => {
            const title = node.querySelector('h2');
            const section = node.querySelector('.execution-wave-section');
            const body = node.querySelector('.execution-wave-section-body');
            const board = node.querySelector('.execution-wave-board');
            const cardBox = node.getBoundingClientRect();
            const titleBox = title ? title.getBoundingClientRect() : null;
            const sectionBox = section ? section.getBoundingClientRect() : null;
            const bodyBox = body ? body.getBoundingClientRect() : null;
            const boardBox = board ? board.getBoundingClientRect() : null;
            return {
              topGap: sectionBox && titleBox ? sectionBox.top - titleBox.bottom : 0,
              bottomGap: sectionBox ? cardBox.bottom - sectionBox.bottom : 0,
              bodyTopGap: bodyBox && boardBox ? boardBox.top - bodyBox.top : 0,
              bodyBottomGap: bodyBox && boardBox ? bodyBox.bottom - boardBox.bottom : 0,
            };
        }"""
    )
    assert 14 <= release_targets["topGap"] <= 18
    assert abs(release_targets["bodyTopGap"] - release_targets["bodyBottomGap"]) <= 1

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_and_radar_target_release_cards_show_labeled_release_version(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    current_release_label = _current_release_label()
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=48h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok
    page.wait_for_function(
        """() => {
            const node = document.querySelector("#shellRuntimeStatus");
            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
        }""",
        timeout=15000,
    )

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="48h")
    compass_release_label = compass.locator(".stat.stat-release-only .kpi-label").first.inner_text().strip()
    compass_release = compass.locator(".stat.stat-release-only .kpi-value").first.inner_text().strip()
    assert compass_release_label == "TARGET RELEASE"
    assert compass_release == current_release_label
    assert compass.locator(".stat .kpi-label", has_text="NEXT RELEASE").count() == 0
    assert compass.locator("#release-groups .execution-wave-section").count() >= 1
    release_targets_text = compass.locator("#release-groups").inner_text().strip()
    assert "Target Release" in release_targets_text
    assert current_release_label in release_targets_text
    assert "release target across active workstreams." in release_targets_text

    page.locator("#tab-radar").click()
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_release_label = radar.locator(".stats .stat.stat-release-only .label").first.inner_text().strip()
    radar_release = radar.locator(".stats .stat.stat-release-only .value").first.inner_text().strip()
    assert radar_release_label == "TARGET RELEASE"
    assert radar_release == current_release_label

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_standup_brief_title_row_keeps_button_close_and_optically_aligned(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=48h&date=live", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    page.wait_for_function(
                        """() => {
                            const node = document.querySelector("#shellRuntimeStatus");
                            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
                        }""",
                        timeout=15000,
                    )

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="48h")

                    alignment = compass.locator(".standup-brief-title-row").evaluate(
                        """(node) => {
                            const title = node.querySelector("h2");
                            const button = node.querySelector("#copy-brief");
                            const titleBox = title ? title.getBoundingClientRect() : null;
                            const buttonBox = button ? button.getBoundingClientRect() : null;
                            return {
                              gap: titleBox && buttonBox ? buttonBox.left - titleBox.right : null,
                              centerDelta: titleBox && buttonBox
                                ? (buttonBox.top + buttonBox.height / 2) - (titleBox.top + titleBox.height / 2)
                                : null,
                            };
                        }"""
                    )
                    assert alignment["gap"] is not None and 6 <= alignment["gap"] <= 14
                    assert alignment["centerDelta"] is not None and abs(alignment["centerDelta"]) <= 1.5

                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_copy_brief_notice_stays_below_brief_title_instead_of_header(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=48h&date=live", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    page.wait_for_function(
                        """() => {
                            const node = document.querySelector("#shellRuntimeStatus");
                            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
                        }""",
                        timeout=15000,
                    )

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="48h")
                    compass.locator("body").evaluate(
                        """() => {
                            navigator.clipboard.writeText = async (payload) => {
                                window.__ODYLITH_COPIED_BRIEF__ = String(payload || "");
                            };
                        }"""
                    )

                    compass.get_by_role("button", name="Copy Brief").click()
                    brief_notice = compass.locator("#brief-copy-status")
                    brief_notice.wait_for(timeout=15000)
                    assert "Standup brief copied to clipboard." in brief_notice.inner_text().strip()

                    layout = compass.locator(".card:has(.standup-brief-title-row)").evaluate(
                        """(node) => {
                            const titleRow = node.querySelector(".standup-brief-title-row");
                            const notice = node.querySelector("#brief-copy-status");
                            const banner = document.getElementById("status-banner");
                            const titleBox = titleRow ? titleRow.getBoundingClientRect() : null;
                            const noticeBox = notice ? notice.getBoundingClientRect() : null;
                            return {
                              noticeTopGap: titleBox && noticeBox ? noticeBox.top - titleBox.bottom : null,
                              bannerHidden: Boolean(banner && banner.classList.contains("hidden")),
                              bannerText: banner ? String(banner.textContent || "").trim() : "",
                            };
                        }"""
                    )
                    assert layout["noticeTopGap"] is not None and 0 <= layout["noticeTopGap"] <= 16
                    assert layout["bannerHidden"] is True, layout
                    assert layout["bannerText"] == ""

                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_skipped_narration_notice_uses_header_status_not_brief_body(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    brief = standup_brief.get("24h") if isinstance(standup_brief.get("24h"), dict) else {}
    brief["source"] = "cache"
    brief["cache_mode"] = "fallback"
    brief["provider_decision"] = "skipped_not_worth_calling"
    brief["notice"] = {
        "title": "Brief reused last validated narration",
        "message": "Compass skipped a fresh narrator call because the winning narrative facts did not materially change.",
        "reason": "skipped_not_worth_calling",
    }
    standup_brief["24h"] = brief
    payload["standup_brief"] = standup_brief
    _write_compass_fixture_runtime_payloads(fixture_root, runtime_payload=payload)

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    status_banner = compass.locator("#status-banner")
                    status_banner.wait_for(timeout=15000)
                    status_text = status_banner.inner_text().strip()
                    assert status_banner.evaluate("(node) => node.classList.contains('warn')") is True
                    assert "Brief reused last validated narration" in status_text
                    assert "Reused last validated brief." in status_text
                    assert "winning narrative facts did not materially change" not in status_text
                    assert compass.locator("#digest-list .brief-status-card").count() == 0
                    assert compass.locator("#digest-list .standup-brief-sections").count() == 1

                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_failed_global_brief_uses_header_status_and_previous_brief(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    ready_48h = standup_brief.get("48h") if isinstance(standup_brief.get("48h"), dict) else {}
    ready_sections = ready_48h.get("sections") if isinstance(ready_48h.get("sections"), list) else []
    assert ready_sections
    ready_sections[1]["bullets"][0]["text"] = "A previous standup brief stays visible while narration retries."
    ready_48h["sections"] = ready_sections
    standup_brief["48h"] = ready_48h
    standup_brief["24h"] = {
        "status": "unavailable",
        "source": "provider",
        "diagnostics": {
            "title": "Brief needs another provider pass",
            "message": (
                "Compass received a narration reply for this brief, but the result was not usable yet. "
                "It will retry on backoff."
            ),
            "reason": "invalid_batch",
            "next_retry_utc": "2026-05-04T14:31:00Z",
        },
    }
    payload["standup_brief"] = standup_brief
    payload["now_local_iso"] = "2026-05-04T14:30:00-07:00"
    payload["generated_utc"] = "2026-05-04T14:30:00Z"
    _write_compass_fixture_runtime_payloads(fixture_root, runtime_payload=payload)

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    status_banner = compass.locator("#status-banner")
                    status_banner.wait_for(timeout=15000)
                    status_text = status_banner.inner_text().strip()
                    assert status_banner.evaluate("(node) => node.classList.contains('warn')") is True
                    assert "Brief needs another provider pass" in status_text
                    assert "latest narration unusable" in status_text
                    assert "showing last ready brief until retry succeeds" in status_text
                    assert "result was not usable yet" not in status_text
                    assert "Will retry after" not in status_text
                    digest_text = compass.locator("#digest-list").inner_text().strip()
                    assert "A previous standup brief stays visible while narration retries." in digest_text
                    assert "Brief needs another provider pass" not in digest_text
                    assert compass.locator("#digest-list .brief-status-card").count() == 0
                    assert compass.locator("#digest-list .standup-brief-sections").count() == 1
                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_failed_same_window_brief_uses_header_status_and_keeps_last_ready_body(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_json_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    ready_24h = standup_brief.get("24h") if isinstance(standup_brief.get("24h"), dict) else {}
    ready_sections = ready_24h.get("sections") if isinstance(ready_24h.get("sections"), list) else []
    assert ready_sections
    ready_sections[1]["bullets"][0]["text"] = "The last known standup brief stays intact in the body."
    ready_24h["sections"] = ready_sections
    ready_24h["notice"] = {
        "title": "Brief unavailable right now",
        "message": (
            "The narration provider failed on the last attempt. "
            "Showing the last known standup brief while Compass retries."
        ),
        "reason": "global_provider_error_showing_previous",
        "next_retry_utc": "2026-05-04T22:22:00Z",
    }
    standup_brief["24h"] = ready_24h
    payload["standup_brief"] = standup_brief
    _write_compass_fixture_runtime_payloads(fixture_root, runtime_payload=payload)

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    status_banner = compass.locator("#status-banner")
                    status_banner.wait_for(timeout=15000)
                    status_text = status_banner.inner_text().strip()
                    assert status_banner.evaluate("(node) => node.classList.contains('warn')") is True
                    assert "Brief unavailable right now" in status_text
                    assert "provider failed" in status_text
                    assert "showing last ready brief until retry succeeds" in status_text
                    assert "Will retry after" not in status_text
                    digest_text = compass.locator("#digest-list").inner_text().strip()
                    assert "The last known standup brief stays intact in the body." in digest_text
                    assert "Brief unavailable right now" not in digest_text
                    assert compass.locator("#digest-list .brief-status-card").count() == 0
                    assert compass.locator("#digest-list .standup-brief-sections").count() == 1
                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_failed_live_brief_uses_retained_history_brief_not_body_notice(
    tmp_path: Path,
) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_dir = fixture_root / "odylith" / "compass" / "runtime"
    runtime_json_path = runtime_dir / "current.v1.json"
    payload = json.loads(runtime_json_path.read_text(encoding="utf-8"))
    standup_brief = payload.get("standup_brief") if isinstance(payload.get("standup_brief"), dict) else {}
    history_ready = dict(standup_brief.get("24h") if isinstance(standup_brief.get("24h"), dict) else {})
    history_sections = history_ready.get("sections") if isinstance(history_ready.get("sections"), list) else []
    assert history_sections
    history_sections[1]["bullets"][0]["text"] = "The retained historical standup brief stays visible after live narration fails."
    history_ready["sections"] = history_sections
    history_ready["fingerprint"] = "retained-history-ready-24h"

    fallback_date = "2026-04-20"
    history_payload = dict(payload)
    history_payload["generated_utc"] = "2026-04-20T17:00:00Z"
    history_payload["standup_brief"] = {"24h": history_ready, "48h": history_ready}
    history_payload["standup_brief_scoped"] = {"24h": {}, "48h": {}}
    history_payload["digest"] = {"24h": ["history ready"], "48h": ["history ready"]}
    history_payload["history"] = {"retention_days": 15, "dates": [fallback_date], "restored_dates": []}
    history_path = runtime_dir / "history" / f"{fallback_date}.v1.json"
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history_payload, indent=2) + "\n", encoding="utf-8")

    payload["history"] = {"retention_days": 15, "dates": [fallback_date], "restored_dates": []}
    standup_brief["24h"] = {
        "status": "unavailable",
        "source": "unavailable",
        "fingerprint": "failed-live-24h",
        "generated_utc": "2026-05-04T22:30:00Z",
        "sections": [],
        "diagnostics": {
            "title": "Brief unavailable right now",
            "message": "The narration provider failed on the last attempt. Compass will retry on backoff.",
            "reason": "provider_error",
            "next_retry_utc": "2026-05-05T01:30:00Z",
        },
        "evidence_lookup": {},
    }
    standup_brief["48h"] = {
        **standup_brief["24h"],
        "fingerprint": "failed-live-48h",
    }
    payload["standup_brief"] = standup_brief
    payload["now_local_iso"] = "2026-05-04T14:30:00-07:00"
    payload["generated_utc"] = "2026-05-04T14:30:00Z"
    _write_compass_fixture_runtime_payloads(fixture_root, runtime_payload=payload)

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    status_banner = compass.locator("#status-banner")
                    status_banner.wait_for(timeout=15000)
                    status_text = status_banner.inner_text().strip()
                    assert status_banner.evaluate("(node) => node.classList.contains('warn')") is True
                    assert "Compass snapshot is" in status_text
                    assert "timeline pinned" in status_text
                    assert "Brief unavailable right now" in status_text
                    assert "showing last ready brief until retry succeeds" in status_text
                    assert "last ready standup brief from 2026-04-20" not in status_text
                    banner_metrics = status_banner.evaluate(
                        """(node) => ({
                          clientWidth: node.clientWidth,
                          scrollWidth: node.scrollWidth,
                          textLength: (node.textContent || "").trim().length,
                          whiteSpace: getComputedStyle(node).whiteSpace
                        })"""
                    )
                    assert banner_metrics["scrollWidth"] - banner_metrics["clientWidth"] <= 2
                    assert banner_metrics["textLength"] <= 160
                    assert banner_metrics["whiteSpace"] != "nowrap"
                    digest_text = compass.locator("#digest-list").inner_text().strip()
                    assert "The retained historical standup brief stays visible after live narration fails." in digest_text
                    assert "Brief unavailable right now" not in digest_text
                    assert compass.locator("#digest-list .brief-status-card").count() == 0
                    assert compass.locator("#digest-list .standup-brief-sections").count() == 1
                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_current_workstreams_excludes_rows_already_represented_in_programs_or_release_targets(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=48h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok
    page.wait_for_function(
        """() => {
            const node = document.querySelector("#shellRuntimeStatus");
            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
        }""",
        timeout=15000,
    )

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="48h")

    represented_ids = set(
        compass.locator(
            "#execution-waves-host .execution-wave-section-title, "
            "#execution-waves-host a.execution-wave-chip-link, "
            "#release-groups-host a.execution-wave-chip-link"
        ).evaluate_all(
            """(nodes) => {
                const seen = new Set();
                nodes.forEach((node) => {
                    const text = String(node.textContent || "");
                    const matches = text.match(/\\bB-\\d{3,}\\b/g) || [];
                    matches.forEach((token) => seen.add(token));
                });
                return Array.from(seen).sort();
            }"""
        )
    )
    current_ids = set(
        compass.locator("#current-workstreams a.ws-id-btn").evaluate_all(
            """(nodes) => Array.from(new Set(
                nodes
                  .map((node) => String(node.textContent || "").trim())
                  .filter((token) => /^B-\\d{3,}$/.test(token))
            )).sort()"""
        )
    )
    current_hrefs = compass.locator("#current-workstreams a.ws-id-btn").evaluate_all(
        """(nodes) => nodes.map((node) => String(node.getAttribute("href") || "").trim())"""
    )
    assert all("tab=radar" in href and "workstream=B-" in href and "view=plan" not in href for href in current_hrefs)

    assert represented_ids, "expected Compass Programs or Release Targets to represent at least one workstream"
    assert represented_ids.isdisjoint(current_ids), (
        f"Current Workstreams still duplicates ids already represented above: {sorted(represented_ids & current_ids)}"
    )

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_current_workstreams_membership_follows_selected_window(tmp_path: Path) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_payload_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"
    runtime_payload = json.loads(runtime_payload_path.read_text(encoding="utf-8"))
    source_truth_payload = json.loads(source_truth_path.read_text(encoding="utf-8"))
    base_row = {
        "priority": "P1",
        "activity": {"24h": {"event_count": 1}, "48h": {"event_count": 1}},
        "plan": {"display_progress_ratio": 0.5, "display_progress_label": "50%"},
        "links": {},
        "timeline": {},
        "why": {},
        "registry_components": [],
        "execution_wave_programs": [],
    }
    current_rows = [
        {
            **base_row,
            "idea_id": "B-201",
            "title": "Window Scoped Membership Primary",
            "status": "implementation",
        },
        {
            **base_row,
            "idea_id": "B-202",
            "title": "Window Scoped Membership Secondary",
            "status": "implementation",
        },
    ]
    runtime_payload["workstream_catalog"] = current_rows
    runtime_payload["current_workstreams"] = current_rows
    runtime_payload["current_workstreams_by_window"] = {
        "24h": current_rows[:1],
        "48h": current_rows,
    }
    source_truth_payload["workstream_catalog"] = current_rows
    source_truth_payload["current_workstreams"] = current_rows
    source_truth_payload["current_workstreams_by_window"] = {
        "24h": current_rows[:1],
        "48h": current_rows,
    }
    _write_compass_fixture_runtime_payloads(
        fixture_root,
        runtime_payload=runtime_payload,
        source_truth_payload=source_truth_payload,
    )

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 1440, "height": 1100})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=24h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok
                    page.wait_for_function(
                        """() => {
                            const node = document.querySelector("#shellRuntimeStatus");
                            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
                        }""",
                        timeout=15000,
                    )

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    _assert_compass_live_state(compass, window_token="24h")
                    compass.locator("#current-workstreams a.ws-id-btn", has_text="B-201").wait_for(timeout=15000)

                    current_ids_24h = compass.locator("#current-workstreams a.ws-id-btn").evaluate_all(
                        """(nodes) => Array.from(new Set(
                            nodes
                              .map((node) => String(node.textContent || "").trim())
                              .filter((token) => /^B-\\d{3,}$/.test(token))
                        )).sort()"""
                    )
                    assert current_ids_24h == ["B-201"]

                    compass.get_by_role("button", name="48h Window").click()
                    page.wait_for_url(
                        re.compile(r".*/odylith/index\.html\?tab=compass(&.*)?window=48h(&.*|$)"),
                        timeout=15000,
                    )
                    _assert_compass_live_state(compass, window_token="48h")
                    compass.locator("#current-workstreams a.ws-id-btn", has_text="B-202").wait_for(timeout=15000)

                    current_ids_48h = compass.locator("#current-workstreams a.ws-id-btn").evaluate_all(
                        """(nodes) => Array.from(new Set(
                            nodes
                              .map((node) => String(node.textContent || "").trim())
                              .filter((token) => /^B-\\d{3,}$/.test(token))
                        )).sort()"""
                    )
                    assert current_ids_48h == ["B-201", "B-202"]

                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_compass_current_workstreams_progress_header_fits_constrained_width(tmp_path: Path) -> None:
    fixture_root = _ready_compass_fixture_root(tmp_path)
    runtime_payload_path = fixture_root / "odylith" / "compass" / "runtime" / "current.v1.json"
    source_truth_path = fixture_root / "odylith" / "compass" / "compass-source-truth.v1.json"
    runtime_payload = json.loads(runtime_payload_path.read_text(encoding="utf-8"))
    source_truth_payload = json.loads(source_truth_path.read_text(encoding="utf-8"))
    current_row = {
        "idea_id": "B-310",
        "title": "Managed Delivery Runtime for OSW Technical Failure Handling",
        "status": "implementation",
        "priority": "P1",
        "activity": {"24h": {"event_count": 1}, "48h": {"event_count": 1}},
        "plan": {"display_progress_ratio": 0.4, "display_progress_label": "40%"},
        "links": {},
        "timeline": {},
        "why": {},
        "registry_components": [],
        "execution_wave_programs": [],
    }
    runtime_payload["workstream_catalog"] = [current_row]
    runtime_payload["current_workstreams"] = [current_row]
    runtime_payload["current_workstreams_by_window"] = {"24h": [current_row], "48h": [current_row]}
    source_truth_payload["workstream_catalog"] = [current_row]
    source_truth_payload["current_workstreams"] = [current_row]
    source_truth_payload["current_workstreams_by_window"] = {"24h": [current_row], "48h": [current_row]}
    _write_compass_fixture_runtime_payloads(
        fixture_root,
        runtime_payload=runtime_payload,
        source_truth_payload=source_truth_payload,
    )

    def _exercise() -> None:
        with _static_server(root=fixture_root) as base_url:
            for _pw, browser in _browser():
                context = browser.new_context(viewport={"width": 820, "height": 760})
                try:
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    response = page.goto(
                        base_url + "/odylith/index.html?tab=compass&window=48h&date=live",
                        wait_until="domcontentloaded",
                    )
                    assert response is not None and response.ok
                    page.wait_for_function(
                        """() => {
                            const node = document.querySelector("#shellRuntimeStatus");
                            return Boolean(node && node.hidden && node.getAttribute("aria-hidden") === "true");
                        }""",
                        timeout=15000,
                    )

                    compass = page.frame_locator("#frame-compass")
                    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
                    compass.locator("#current-workstreams a.ws-id-btn", has_text="B-310").wait_for(timeout=15000)
                    header_metrics = compass.locator("#current-workstreams th.ws-col-progress").evaluate(
                        """(node) => {
                            const rect = node.getBoundingClientRect();
                            const wrap = node.closest(".ws-table-wrap").getBoundingClientRect();
                            const style = window.getComputedStyle(node);
                            return {
                                text: String(node.textContent || "").trim(),
                                width: rect.width,
                                scrollWidth: node.scrollWidth,
                                clientWidth: node.clientWidth,
                                right: rect.right,
                                wrapRight: wrap.right,
                                letterSpacing: Number.parseFloat(style.letterSpacing) || 0,
                            };
                        }"""
                    )

                    assert header_metrics["text"] == "Progress"
                    assert header_metrics["width"] >= 120
                    assert header_metrics["scrollWidth"] <= header_metrics["clientWidth"] + 1
                    assert header_metrics["right"] <= header_metrics["wrapRight"] + 1
                    assert header_metrics["letterSpacing"] <= 0.5
                    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                finally:
                    context.close()

    _run_in_browser_thread(_exercise)


def test_shell_cross_tab_hops_keep_compass_global_runtime_fresh(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")

    for tab_selector, frame_selector, heading_selector, heading_text in (
        ("#tab-registry", "#frame-registry", "h1", "Component Registry"),
        ("#tab-casebook", "#frame-casebook", ".hero-title", "Casebook"),
        ("#tab-atlas", "#frame-atlas", "h1", "Atlas"),
        ("#tab-radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
    ):
        page.locator(tab_selector).click()
        page.frame_locator(frame_selector).locator(heading_selector, has_text=heading_text).wait_for(timeout=15000)

    page.locator("#tab-compass").click()
    _wait_for_shell_tab(page, "compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")

    compass.get_by_role("button", name="48h Window").click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=compass(&.*)?window=48h(&.*|$)"), timeout=15000)
    _assert_compass_live_state(compass, window_token="48h")

    page.reload(wait_until="domcontentloaded")
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="48h")

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_deeplinks_into_radar_and_registry_contexts(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    release_section = compass.locator("#release-groups-host details.execution-wave-section").first
    release_section.wait_for(state="attached", timeout=15000)
    release_section.evaluate("node => { node.open = true; }")
    release_member_card = compass.locator("#release-groups-host .execution-wave-card").first
    release_member_card.wait_for(timeout=15000)
    before_blank_click_url = page.url
    blank_click_result = release_member_card.evaluate(
        """(node) => {
            const box = node.getBoundingClientRect();
            const probes = [
              [0.58, 0.62],
              [0.48, 0.62],
              [0.42, 0.50],
              [0.70, 0.50],
            ];
            for (const [xRatio, yRatio] of probes) {
              const x = box.left + box.width * xRatio;
              const y = box.top + box.height * yRatio;
              const target = document.elementFromPoint(x, y);
              if (!target || !node.contains(target)) continue;
              if (target.closest("a, button")) continue;
              target.dispatchEvent(new MouseEvent("click", {
                bubbles: true,
                cancelable: true,
                view: window,
                clientX: x,
                clientY: y,
              }));
              return { clicked: true, tag: target.tagName, className: String(target.className || "") };
            }
            return { clicked: false };
        }"""
    )
    assert blank_click_result["clicked"] is False, blank_click_result
    page.wait_for_timeout(150)
    assert page.url == before_blank_click_url
    assert compass.locator("#release-groups-host a.execution-wave-card-link").count() == 0

    release_workstream_chip = compass.locator("#release-groups-host a.execution-wave-chip-link").first
    release_workstream_chip.wait_for(timeout=15000)
    release_workstream_id = release_workstream_chip.inner_text().strip()
    assert re.fullmatch(r"B-\d{3,}", release_workstream_id), release_workstream_id
    release_workstream_chip.click()
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(release_workstream_id)}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    first_workstream_link = compass.locator("a.ws-id-btn, a.ws-covered-id-btn").first
    first_workstream_id = first_workstream_link.inner_text().strip()
    assert re.fullmatch(r"B-\d{3,}", first_workstream_id), first_workstream_id
    first_workstream_link.click()
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(first_workstream_id)}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"
    page.frame_locator("#frame-radar").locator("h1").first.wait_for(timeout=15000)
    assert first_workstream_id in str(page.locator("#frame-radar").get_attribute("src") or "")

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    compass.locator("tr.ws-summary-row.ws-row-title").first.click()
    first_component_link = compass.locator("tr.ws-detail-row.is-open a.chip-link").first
    first_component_link.wait_for(timeout=15000)
    first_component_id = first_component_link.inner_text().strip()
    assert first_component_id, "expected at least one registry component chip in selected workstream detail"
    first_component_link.click()
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=registry(&.*)?component={re.escape(first_component_id.lower())}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-registry").get_attribute("aria-selected") == "true"
    page.frame_locator("#frame-registry").locator("h1", has_text="Component Registry").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_history_and_cross_surface_deeplinks_round_trip_cleanly(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("a.ws-id-btn, a.ws-covered-id-btn").first.click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=radar(&.*)?workstream=B-\d{3,}(&.*|$)"), timeout=15000)
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"

    radar = page.frame_locator("#frame-radar")
    radar.locator("h1").first.wait_for(timeout=15000)
    left_compass_plan_view = False
    if "view=plan" in page.url:
        left_compass_plan_view = True
        match = re.search(r"(?:\?|&)workstream=(B-\d{3,})(?:&|$)", page.url)
        assert match, page.url
        response = page.goto(base_url + f"/odylith/index.html?tab=radar&workstream={quote(match.group(1), safe='')}", wait_until="domcontentloaded")
        assert response is not None and response.ok
        radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    idea_id, component_id, _component_href = _select_radar_row_with_link(
        radar,
        "a.chip-registry-component",
        "expected at least one Radar workstream with a registry deeplink",
        query_key="component",
    )
    _wait_for_shell_query_param(
        page,
        tab="radar",
        key="workstream",
        value=idea_id,
    )

    radar.locator("#detail details.topology-relations-panel").first.evaluate("node => { node.open = true; }")
    _click_visible(radar.locator("#detail .topology-relations a.chip-registry-component:visible").first)
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=registry(&.*)?component={re.escape(component_id.lower())}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-registry").get_attribute("aria-selected") == "true"
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)

    page.go_back(wait_until="domcontentloaded")
    _wait_for_shell_query_param(
        page,
        tab="radar",
        key="workstream",
        value=idea_id,
    )
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)

    idea_id, diagram_id, diagram_href = _select_radar_row_with_link(
        radar,
        "a.chip-topology-diagram",
        "expected at least one Radar workstream with an atlas deeplink",
        query_key="diagram",
    )
    _wait_for_shell_query_param(
        page,
        tab="radar",
        key="workstream",
        value=idea_id,
    )
    radar.locator("#detail details.topology-relations-panel").first.evaluate("node => { node.open = true; }")
    radar.locator(f'#detail a.chip-topology-diagram[href="{diagram_href}"]').first.evaluate("node => node.click()")
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=atlas(&.*)?diagram={re.escape(diagram_id)}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-atlas").get_attribute("aria-selected") == "true"
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text=diagram_id).wait_for(timeout=15000)

    page.go_back(wait_until="domcontentloaded")
    _wait_for_shell_query_param(
        page,
        tab="radar",
        key="workstream",
        value=idea_id,
    )
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)
    page.go_back(wait_until="domcontentloaded")
    if left_compass_plan_view:
        page.go_back(wait_until="domcontentloaded")
    _wait_for_shell_tab(page, "compass")
    assert page.locator("#tab-compass").get_attribute("aria-selected") == "true"
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_selection_and_shell_history_stay_routable(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok

    assert page.locator("#tab-casebook").get_attribute("aria-selected") == "true"
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)

    first_bug = casebook.locator("button.bug-row").first
    first_bug.wait_for(timeout=15000)
    bug_route = str(first_bug.get_attribute("data-bug") or "").strip()
    bug_title = first_bug.locator(".bug-row-title").inner_text().strip()
    assert bug_route, "expected casebook bug route"
    assert bug_title, "expected casebook bug title"
    first_bug.click()

    _wait_for_shell_query_param(
        page,
        tab="casebook",
        key="bug",
        value=bug_route,
    )
    casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)

    page.locator("#tab-radar").click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=radar([&#].*|$)"), timeout=15000)
    page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)

    page.go_back(wait_until="domcontentloaded")
    _wait_for_shell_query_param(
        page,
        tab="casebook",
        key="bug",
        value=bug_route,
    )
    assert page.locator("#tab-casebook").get_attribute("aria-selected") == "true"
    casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-title", has_text=bug_title).wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_counts_match_bug_index_after_shell_navigation(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    expected_open_total, expected_total_cases = _casebook_index_counts()
    assert expected_open_total > 0
    assert expected_total_cases >= expected_open_total

    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator("button[data-idea-id]").first.click()

    page.locator("#tab-casebook").click()
    _wait_for_shell_tab(page, "casebook")
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    _assert_casebook_counts(
        casebook,
        expected_open_total=expected_open_total,
        expected_total_cases=expected_total_cases,
    )

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_entrypoint_counts_match_bug_index_after_reload(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    expected_open_total, expected_total_cases = _casebook_index_counts()
    response = page.goto(base_url + "/odylith/casebook/casebook.html", wait_until="domcontentloaded")
    assert response is not None and response.ok
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=casebook([&#].*|$)"), timeout=15000)

    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    _assert_casebook_counts(
        casebook,
        expected_open_total=expected_open_total,
        expected_total_cases=expected_total_cases,
    )


def test_radar_standalone_spec_route_survives_reload(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    workstream_id = _first_backlog_document_workstream_id("spec")

    response = page.goto(
        base_url + f"/odylith/index.html?tab=radar&workstream={quote(workstream_id, safe='')}&view=spec",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="spec")

    page.reload(wait_until="domcontentloaded")
    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="spec")

    _discard_external_mermaid_cdn_failures(failed_requests)
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_plan_entrypoint_redirects_into_shell_standalone_plan_view(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    workstream_id = _first_backlog_document_workstream_id("plan")

    response = page.goto(
        base_url + f"/odylith/radar/radar.html?workstream={quote(workstream_id, safe='')}&view=plan",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="plan")

    page.reload(wait_until="domcontentloaded")
    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="plan")

    _discard_external_mermaid_cdn_failures(failed_requests)
    _discard_radar_redirect_abort_failures(failed_requests)
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_radar_plan_traceability_cards_stay_bounded_on_mobile_and_desktop(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    workstream_id = _first_traceable_plan_workstream_id()
    page.set_viewport_size({"width": 390, "height": 844})

    response = page.goto(
        base_url + f"/odylith/index.html?tab=radar&workstream={quote(workstream_id, safe='')}&view=plan",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok

    def _assert_traceability_cards_fit() -> None:
        radar = page.frame_locator("#frame-radar")
        radar.locator(".trace-groups").wait_for(timeout=15000)
        assert radar.locator(".trace-group").count() >= 1
        assert radar.locator(".trace-link").count() >= 2
        assert radar.locator(".trace-link-missing").count() >= 1
        trace_paths = [text.strip() for text in radar.locator(".trace-path").all_inner_texts()]
        assert trace_paths
        assert not [text for text in trace_paths if ".." in text or text.startswith(("http://", "https://"))]
        style_rows = radar.locator(".trace-path").evaluate_all(
            """nodes => nodes.map((node) => {
              const style = window.getComputedStyle(node);
              return {
                overflow: style.overflow,
                textOverflow: style.textOverflow,
                whiteSpace: style.whiteSpace
              };
            })"""
        )
        assert style_rows
        assert all(row["overflow"] == "hidden" for row in style_rows)
        assert all(row["textOverflow"] == "ellipsis" for row in style_rows)
        assert all(row["whiteSpace"] == "nowrap" for row in style_rows)
        overflow_rows = radar.locator(".trace-link").evaluate_all(
            """nodes => nodes
              .map((node) => {
                const parent = node.closest(".trace-group").getBoundingClientRect();
                const box = node.getBoundingClientRect();
                return {left: box.left, right: box.right, parentLeft: parent.left, parentRight: parent.right};
              })
              .filter((row) => row.left < row.parentLeft - 1 || row.right > row.parentRight + 1)"""
        )
        assert overflow_rows == []

    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="plan")
    _assert_traceability_cards_fit()

    page.set_viewport_size({"width": 1440, "height": 920})
    page.reload(wait_until="domcontentloaded")
    _wait_for_radar_standalone_document(page, workstream_id=workstream_id, view="plan")
    _assert_traceability_cards_fit()

    _discard_external_mermaid_cdn_failures(failed_requests)
    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_direct_query_routes_restore_selected_context_after_reload(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    response = page.goto(
        base_url + f"/odylith/index.html?tab=radar&workstream={quote(tokens['radar_workstream'], safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    _assert_radar_selection(page, tokens["radar_workstream"])
    page.reload(wait_until="domcontentloaded")
    _assert_radar_selection(page, tokens["radar_workstream"])

    response = page.goto(
        base_url + f"/odylith/index.html?tab=registry&component={quote(tokens['registry_component'], safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    _assert_registry_selection(page, tokens["registry_component"])
    page.reload(wait_until="domcontentloaded")
    _assert_registry_selection(page, tokens["registry_component"])

    atlas_route = (
        f"/odylith/index.html?tab=atlas&diagram={quote(tokens['atlas_diagram'], safe='')}"
        if not tokens["atlas_workstream"]
        else (
            f"/odylith/index.html?tab=atlas&workstream={quote(tokens['atlas_workstream'], safe='')}"
            f"&diagram={quote(tokens['atlas_diagram'], safe='')}"
        )
    )
    response = page.goto(base_url + atlas_route, wait_until="domcontentloaded")
    assert response is not None and response.ok
    _assert_atlas_selection(
        page,
        workstream=tokens["atlas_workstream"],
        diagram_id=tokens["atlas_diagram"],
    )
    page.reload(wait_until="domcontentloaded")
    _assert_atlas_selection(
        page,
        workstream=tokens["atlas_workstream"],
        diagram_id=tokens["atlas_diagram"],
    )

    response = page.goto(
        base_url + f"/odylith/index.html?tab=casebook&bug={quote(tokens['casebook_bug'], safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    _assert_casebook_selection(page, tokens["casebook_bug"])
    page.reload(wait_until="domcontentloaded")
    _assert_casebook_selection(page, tokens["casebook_bug"])

    response = page.goto(
        base_url
        + f"/odylith/index.html?tab=compass&scope={quote(tokens['compass_workstream'], safe='')}"
        + "&window=48h&date=live",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    _assert_compass_selection(page, workstream=tokens["compass_workstream"], window_token="48h")
    page.reload(wait_until="domcontentloaded")
    _assert_compass_selection(page, workstream=tokens["compass_workstream"], window_token="48h")

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_direct_query_routes_restore_selected_context_after_tab_round_trip(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    routes = (
        (
            base_url + f"/odylith/index.html?tab=radar&workstream={quote(tokens['radar_workstream'], safe='')}",
            "#tab-casebook",
            "#tab-radar",
            lambda: _assert_radar_selection(page, tokens["radar_workstream"]),
        ),
        (
            base_url + f"/odylith/index.html?tab=registry&component={quote(tokens['registry_component'], safe='')}",
            "#tab-radar",
            "#tab-registry",
            lambda: _assert_registry_selection(page, tokens["registry_component"]),
        ),
        (
            base_url
            + (
                f"/odylith/index.html?tab=atlas&diagram={quote(tokens['atlas_diagram'], safe='')}"
                if not tokens["atlas_workstream"]
                else (
                    f"/odylith/index.html?tab=atlas&workstream={quote(tokens['atlas_workstream'], safe='')}"
                    f"&diagram={quote(tokens['atlas_diagram'], safe='')}"
                )
            ),
            "#tab-compass",
            "#tab-atlas",
            lambda: _assert_atlas_selection(page, workstream=tokens["atlas_workstream"], diagram_id=tokens["atlas_diagram"]),
        ),
        (
            base_url + f"/odylith/index.html?tab=casebook&bug={quote(tokens['casebook_bug'], safe='')}",
            "#tab-radar",
            "#tab-casebook",
            lambda: _assert_casebook_selection(page, tokens["casebook_bug"]),
        ),
        (
            base_url
            + f"/odylith/index.html?tab=compass&scope={quote(tokens['compass_workstream'], safe='')}"
            + "&window=48h&date=live",
            "#tab-radar",
            "#tab-compass",
            lambda: _assert_compass_selection(page, workstream=tokens["compass_workstream"], window_token="48h"),
        ),
    )

    for route, detour_tab, return_tab, assertion in routes:
        response = page.goto(route, wait_until="domcontentloaded")
        assert response is not None and response.ok
        assertion()
        page.locator(detour_tab).click()
        page.locator(return_tab).click()
        assertion()

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_standalone_surface_entrypoints_preserve_query_state_into_shell(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    routes = (
        (
            f"/odylith/radar/radar.html?workstream={quote(tokens['radar_workstream'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(tokens['radar_workstream'])}(&.*|$)"),
            lambda: _assert_radar_selection(page, tokens["radar_workstream"]),
        ),
        (
            f"/odylith/registry/registry.html?component={quote(tokens['registry_component'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=registry(&.*)?component={re.escape(tokens['registry_component'])}(&.*|$)"),
            lambda: _assert_registry_selection(page, tokens["registry_component"]),
        ),
            (
                (
                    f"/odylith/atlas/atlas.html?diagram={quote(tokens['atlas_diagram'], safe='')}"
                    if not tokens["atlas_workstream"]
                    else f"/odylith/atlas/atlas.html?workstream={quote(tokens['atlas_workstream'], safe='')}&diagram={quote(tokens['atlas_diagram'], safe='')}"
                ),
                re.compile(rf".*/odylith/index\.html\?tab=atlas(&.*)?diagram={re.escape(tokens['atlas_diagram'])}(&.*|$)"),
                lambda: _assert_atlas_selection(page, workstream=tokens["atlas_workstream"], diagram_id=tokens["atlas_diagram"]),
            ),
        (
            f"/odylith/casebook/casebook.html?bug={quote(tokens['casebook_bug'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=casebook(&.*)?bug={re.escape(quote(tokens['casebook_bug'], safe=''))}(&.*|$)"),
            lambda: _assert_casebook_selection(page, tokens["casebook_bug"]),
        ),
        (
            f"/odylith/compass/compass.html?scope={quote(tokens['compass_workstream'], safe='')}&window=48h&date=live",
            re.compile(rf".*/odylith/index\.html\?tab=compass(&.*)?scope={re.escape(tokens['compass_workstream'])}(&.*)?window=48h(&.*|$)"),
            lambda: _assert_compass_selection(page, workstream=tokens["compass_workstream"], window_token="48h"),
        ),
    )

    for route, pattern, assertion in routes:
        response = page.goto(base_url + route, wait_until="domcontentloaded")
        assert response is not None and response.ok, route
        page.wait_for_url(pattern, timeout=15000)
        assertion()
        failed_requests.clear()
        bad_responses.clear()

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_standalone_surface_entrypoints_restore_query_state_after_shell_reload(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    routes = (
        (
            f"/odylith/radar/radar.html?workstream={quote(tokens['radar_workstream'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(tokens['radar_workstream'])}(&.*|$)"),
            lambda: _assert_radar_selection(page, tokens["radar_workstream"]),
        ),
        (
            f"/odylith/registry/registry.html?component={quote(tokens['registry_component'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=registry(&.*)?component={re.escape(tokens['registry_component'])}(&.*|$)"),
            lambda: _assert_registry_selection(page, tokens["registry_component"]),
        ),
        (
            (
                f"/odylith/atlas/atlas.html?diagram={quote(tokens['atlas_diagram'], safe='')}"
                if not tokens["atlas_workstream"]
                else f"/odylith/atlas/atlas.html?workstream={quote(tokens['atlas_workstream'], safe='')}&diagram={quote(tokens['atlas_diagram'], safe='')}"
            ),
            re.compile(rf".*/odylith/index\.html\?tab=atlas(&.*)?diagram={re.escape(tokens['atlas_diagram'])}(&.*|$)"),
            lambda: _assert_atlas_selection(page, workstream=tokens["atlas_workstream"], diagram_id=tokens["atlas_diagram"]),
        ),
        (
            f"/odylith/casebook/casebook.html?bug={quote(tokens['casebook_bug'], safe='')}",
            re.compile(rf".*/odylith/index\.html\?tab=casebook(&.*)?bug={re.escape(quote(tokens['casebook_bug'], safe=''))}(&.*|$)"),
            lambda: _assert_casebook_selection(page, tokens["casebook_bug"]),
        ),
        (
            f"/odylith/compass/compass.html?scope={quote(tokens['compass_workstream'], safe='')}&window=48h&date=live",
            re.compile(rf".*/odylith/index\.html\?tab=compass(&.*)?scope={re.escape(tokens['compass_workstream'])}(&.*)?window=48h(&.*|$)"),
            lambda: _assert_compass_selection(page, workstream=tokens["compass_workstream"], window_token="48h"),
        ),
    )

    for route, pattern, assertion in routes:
        response = page.goto(base_url + route, wait_until="domcontentloaded")
        assert response is not None and response.ok, route
        page.wait_for_url(pattern, timeout=15000)
        assertion()
        page.reload(wait_until="domcontentloaded")
        assertion()
        failed_requests.clear()
        bad_responses.clear()

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_invalid_surface_routes_fall_back_to_valid_detail_selection(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    invalid_radar = "B-999999"
    response = page.goto(base_url + f"/odylith/index.html?tab=radar&workstream={invalid_radar}", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_active = radar.locator("button[data-idea-id].active")
    radar_active.wait_for(timeout=15000)
    radar_active_id = str(radar_active.first.get_attribute("data-idea-id") or "").strip()
    assert radar_active_id and radar_active_id != invalid_radar
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=radar_active_id).wait_for(timeout=15000)

    invalid_component = "does-not-exist"
    response = page.goto(base_url + f"/odylith/index.html?tab=registry&component={invalid_component}", wait_until="domcontentloaded")
    assert response is not None and response.ok
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    registry_active = registry.locator("button[data-component].active")
    registry_active.wait_for(timeout=15000)
    registry_active_id = str(registry_active.first.get_attribute("data-component") or "").strip()
    assert registry_active_id and registry_active_id != invalid_component
    registry.locator("#detail .component-name").wait_for(timeout=15000)

    invalid_bug = "missing-bug-route"
    response = page.goto(base_url + f"/odylith/index.html?tab=casebook&bug={invalid_bug}", wait_until="domcontentloaded")
    assert response is not None and response.ok
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator(".hero-title", has_text="Casebook").wait_for(timeout=15000)
    casebook_active = casebook.locator("button.bug-row.active")
    casebook_active.wait_for(timeout=15000)
    casebook_active_bug = str(casebook_active.first.get_attribute("data-bug") or "").strip()
    assert casebook_active_bug and casebook_active_bug != invalid_bug
    casebook.locator("#detailPane .detail-title").wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="casebook", key="bug", value=casebook_active_bug)

    response = page.goto(
        base_url + "/odylith/index.html?tab=compass&scope=B-999999&window=48h&date=live",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator('button[data-window="48h"].active').wait_for(timeout=15000)
    compass.locator("#scope-pill", has_text="Global").wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_shell_unknown_tab_self_heals_to_radar_selection(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    response = page.goto(
        base_url + f"/odylith/index.html?tab=not-a-tab&workstream={quote(tokens['radar_workstream'], safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(tokens['radar_workstream'])}(&.*|$)"),
        timeout=15000,
    )
    _assert_radar_selection(page, tokens["radar_workstream"])

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_invalid_window_and_date_queries_are_dropped_on_load(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    response = page.goto(
        base_url
        + f"/odylith/index.html?tab=compass&scope={quote(tokens['compass_workstream'], safe='')}"
        + "&window=999h&date=tomorrow&audit_day=banana",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    page.wait_for_function(
        """({ scope }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "compass"
                && url.searchParams.get("scope") === scope
                && !url.searchParams.has("window")
                && !url.searchParams.has("date")
                && !url.searchParams.has("audit_day");
            } catch (_error) {
              return false;
            }
        }""",
        arg={"scope": tokens["compass_workstream"]},
        timeout=15000,
    )
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator("#scope-pill", has_text=tokens["compass_workstream"]).wait_for(timeout=15000)
    compass.locator('button[data-window].active').first.wait_for(timeout=15000)

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_casebook_invalid_sort_query_reverts_to_default_sort(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)

    response = page.goto(
        base_url
        + f"/odylith/index.html?tab=casebook&bug={quote(tokens['casebook_bug'], safe='')}"
        + "&sort=sideways",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    page.wait_for_function(
        """({ bug }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "casebook"
                && url.searchParams.get("bug") === bug
                && !url.searchParams.has("sort");
            } catch (_error) {
              return false;
            }
        }""",
        arg={"bug": tokens["casebook_bug"]},
        timeout=15000,
    )
    _assert_casebook_selection(page, tokens["casebook_bug"])
    casebook = page.frame_locator("#frame-casebook")
    assert casebook.locator("#sortFilter").input_value() == "newest"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_compact_diagram_route_is_canonicalized(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    tokens = _collect_sample_tokens(page, base_url)
    compact_diagram = tokens["atlas_diagram"].replace("-", "")
    route = (
        base_url
        + (
            f"/odylith/index.html?tab=atlas&diagram={quote(compact_diagram, safe='')}"
            if not tokens["atlas_workstream"]
            else (
                f"/odylith/index.html?tab=atlas&workstream={quote(tokens['atlas_workstream'], safe='')}"
                f"&diagram={quote(compact_diagram, safe='')}"
            )
        )
    )

    response = page.goto(route, wait_until="domcontentloaded")
    assert response is not None and response.ok
    page.wait_for_function(
        """({ diagram }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "atlas"
                && url.searchParams.get("diagram") === diagram;
            } catch (_error) {
              return false;
            }
        }""",
        arg={"diagram": tokens["atlas_diagram"]},
        timeout=15000,
    )
    _assert_atlas_selection(page, workstream=tokens["atlas_workstream"], diagram_id=tokens["atlas_diagram"])

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_bad_cross_surface_route_self_heals_to_full_catalog(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)

    baseline_total = _atlas_total(atlas)
    assert baseline_total > 1
    selected_diagram = _atlas_selected_diagram(atlas)
    related_workstreams = set(_atlas_related_workstreams(atlas))
    candidate_workstreams = [token for token in _atlas_workstream_options(atlas) if token not in {"all", *related_workstreams}]
    if not candidate_workstreams:
        pytest.skip("Atlas fixture does not currently expose a mismatched workstream route scenario.")
    mismatched_workstream = candidate_workstreams[0]

    response = page.goto(
        base_url
        + f"/odylith/index.html?tab=atlas&workstream={quote(mismatched_workstream, safe='')}"
        + f"&diagram={quote(selected_diagram, safe='')}",
        wait_until="domcontentloaded",
    )
    assert response is not None and response.ok
    atlas.locator("#diagramId", has_text=selected_diagram).wait_for(timeout=15000)
    page.wait_for_function(
        """({ diagram }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "atlas"
                && !url.searchParams.has("workstream")
                && url.searchParams.get("diagram") === diagram;
            } catch (_error) {
              return false;
            }
        }""",
        arg={"diagram": selected_diagram},
        timeout=15000,
    )
    assert _atlas_workstream_filter_value(atlas) == "all"
    assert _atlas_total(atlas) == baseline_total

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_atlas_tab_switch_restores_atlas_state_instead_of_leaking_radar_scope(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)

    response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="domcontentloaded")
    assert response is not None and response.ok
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)

    baseline_total = _atlas_total(atlas)
    assert baseline_total > 1
    selected_diagram = _atlas_selected_diagram(atlas)
    related_workstreams = set(_atlas_related_workstreams(atlas))
    candidate_workstreams = [token for token in _atlas_workstream_options(atlas) if token not in {"all", *related_workstreams}]
    if not candidate_workstreams:
        pytest.skip("Atlas fixture does not currently expose a mismatched workstream route scenario.")
    mismatched_workstream = candidate_workstreams[0]

    page.locator("#tab-radar").click()
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_row = radar.locator(f'button[data-idea-id="{mismatched_workstream}"]')
    if radar_row.count() == 0:
        pytest.skip(f"Radar fixture does not currently expose workstream {mismatched_workstream}.")
    radar_row.first.click()
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=mismatched_workstream).wait_for(timeout=15000)
    _wait_for_shell_query_param(page, tab="radar", key="workstream", value=mismatched_workstream)

    page.locator("#tab-atlas").click()
    atlas.locator("#diagramId", has_text=selected_diagram).wait_for(timeout=15000)
    page.wait_for_function(
        """({ diagram }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === "atlas"
                && !url.searchParams.has("workstream")
                && url.searchParams.get("diagram") === diagram;
            } catch (_error) {
              return false;
            }
        }""",
        arg={"diagram": selected_diagram},
        timeout=15000,
    )
    assert _atlas_workstream_filter_value(atlas) == "all"
    assert _atlas_total(atlas) == baseline_total

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
