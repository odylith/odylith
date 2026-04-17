from __future__ import annotations

import contextlib
from datetime import datetime
from datetime import timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import shutil
import threading
import traceback
from typing import Iterator
from urllib.parse import parse_qs, quote, urlparse

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_SURFACE_HTML_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/(radar|registry|casebook|atlas|compass)/[^?#]+\.html(?:[?#].*)?$"
)
_LOCAL_COMPASS_RUNTIME_CURRENT_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/compass/runtime/current\.v1\.(?:json|js)(?:[?#].*)?$"
)


@contextlib.contextmanager
def _static_server(*, root: Path) -> Iterator[str]:
    class _QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):  # noqa: ANN002, ANN003
            super().__init__(*args, directory=str(root), **kwargs)

        def copyfile(self, source, outputfile) -> None:  # noqa: ANN001
            with contextlib.suppress(BrokenPipeError, ConnectionResetError):
                super().copyfile(source, outputfile)

        def log_message(self, format: str, *args) -> None:  # noqa: A003, ANN001
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), _QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _browser() -> Iterator[tuple[object, object]]:
    with playwright_sync.sync_playwright() as pw:
        try:
            browser = pw.chromium.launch(headless=True)
        except Exception as exc:  # pragma: no cover - environment-specific
            pytest.skip(f"Playwright Chromium is not installed: {exc}")
        try:
            yield pw, browser
        finally:
            browser.close()


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


@pytest.fixture(scope="module")
def browser_context() -> Iterator[tuple[str, object]]:
    with _static_server(root=_REPO_ROOT) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                yield base_url, context
            finally:
                context.close()


def _run_in_browser_thread(callback) -> None:  # noqa: ANN001
    error: dict[str, object] = {}

    def _worker() -> None:
        try:
            callback()
        except BaseException as exc:  # pragma: no cover - assertion forwarding
            error["exc"] = exc
            error["traceback"] = traceback.format_exc()

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    thread.join(timeout=60)
    if thread.is_alive():  # pragma: no cover - defensive timeout guard
        raise TimeoutError("browser proof thread did not finish within 60 seconds")
    if "exc" in error:
        raise AssertionError(str(error.get("traceback") or error["exc"])) from error["exc"]


def _new_page(context) -> tuple[object, list[str], list[str]]:  # noqa: ANN001
    page = context.new_page()
    console_errors: list[str] = []
    page_errors: list[str] = []
    failed_requests: list[str] = []
    bad_responses: list[str] = []

    def _on_console(message) -> None:  # noqa: ANN001
        if message.type == "error":
            console_errors.append(message.text)

    def _on_page_error(error) -> None:  # noqa: ANN001
        page_errors.append(str(error))

    def _on_request_failed(request) -> None:  # noqa: ANN001
        url = str(getattr(request, "url", "") or "")
        if not url or url.startswith(("about:", "data:", "blob:")):
            return
        resource_type = str(getattr(request, "resource_type", "") or "").strip().lower()
        failure = getattr(request, "failure", None)
        error_text = ""
        if callable(failure):
            payload = failure() or {}
            if isinstance(payload, dict):
                error_text = str(payload.get("errorText") or "").strip()
        lowered_error = error_text.lower()
        if (
            resource_type == "document"
            and _LOCAL_SURFACE_HTML_RE.match(url)
            and (not lowered_error or "err_aborted" in lowered_error or "abort" in lowered_error)
        ):
            return
        if _LOCAL_COMPASS_RUNTIME_CURRENT_RE.match(url) and (
            not lowered_error or "err_aborted" in lowered_error or "abort" in lowered_error
        ):
            return
        failed_requests.append(f"{request.method} {url} {error_text}".strip())

    def _on_response(response) -> None:  # noqa: ANN001
        url = str(getattr(response, "url", "") or "")
        if not url.startswith("http://127.0.0.1:"):
            return
        status = int(getattr(response, "status", 0) or 0)
        if status >= 400:
            bad_responses.append(f"{status} {url}")

    page.on("console", _on_console)
    page.on("pageerror", _on_page_error)
    page.on("requestfailed", _on_request_failed)
    page.on("response", _on_response)
    return page, console_errors, page_errors, failed_requests, bad_responses


def _assert_clean_page(
    page,
    console_errors: list[str],
    page_errors: list[str],
    failed_requests: list[str],
    bad_responses: list[str],
) -> None:  # noqa: ANN001
    assert console_errors == [], f"console errors: {console_errors}"
    assert page_errors == [], f"page errors: {page_errors}"
    assert failed_requests == [], f"request failures: {failed_requests}"
    assert bad_responses == [], f"http error responses: {bad_responses}"
    page.close()


def _extract_query_param(href: str, key: str) -> str:
    values = parse_qs(urlparse(href).query).get(key, ())
    return str(values[0]).strip() if values else ""


def _casebook_index_counts() -> tuple[int, int]:
    text = (_REPO_ROOT / "odylith" / "casebook" / "bugs" / "INDEX.md").read_text(encoding="utf-8")
    section = ""
    open_total = 0
    closed_total = 0
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if line == "## Open Bugs":
            section = "open"
            continue
        if line == "## Closed Bugs":
            section = "closed"
            continue
        if not section or not line.startswith("| "):
            continue
        if (
            line.startswith("| Bug ID |")
            or line.startswith("| Date |")
            or line.startswith("| --- |")
        ):
            continue
        if section == "open":
            open_total += 1
        elif section == "closed":
            closed_total += 1
    return open_total, open_total + closed_total


def _assert_casebook_counts(casebook, *, expected_open_total: int, expected_total_cases: int) -> None:  # noqa: ANN001
    assert casebook.locator("#kpiOpenTotal").inner_text().strip() == str(expected_open_total)
    assert casebook.locator("#kpiTotalCases").inner_text().strip() == str(expected_total_cases)
    assert casebook.locator("button.bug-row").count() == expected_total_cases
    assert casebook.locator("#listMeta").inner_text().strip() == f"Visible: {expected_total_cases}"


def _select_radar_row_with_link(
    radar,
    link_selector: str,
    failure_message: str,
    *,
    query_key: str,
) -> tuple[str, str, str]:  # noqa: ANN001
    row_buttons = radar.locator("button[data-idea-id]")
    count = row_buttons.count()
    for index in range(count):
        button = row_buttons.nth(index)
        idea_id = str(button.get_attribute("data-idea-id") or "").strip()
        if not idea_id:
            continue
        button.click()
        radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=idea_id).wait_for(timeout=15000)
        links = radar.locator(f"#detail {link_selector}")
        if links.count():
            href = str(links.first.get_attribute("href") or "").strip()
            token = _extract_query_param(href, query_key)
            if token:
                return idea_id, token, href
    raise AssertionError(failure_message)


def _wait_for_shell_query_param(
    page,
    *,
    tab: str,
    key: str,
    value: str,
    timeout: int = 15000,
) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ tab, key, value }) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === tab
                && url.searchParams.get(key) === value;
            } catch (_error) {
              return false;
            }
        }""",
        arg={"tab": tab, "key": key, "value": value},
        timeout=timeout,
    )


def _wait_for_shell_tab(page, tab: str, timeout: int = 15000) -> None:  # noqa: ANN001
    page.wait_for_function(
        """(tab) => {
            try {
              const url = new URL(window.location.href);
              return url.pathname.endsWith("/odylith/index.html")
                && url.searchParams.get("tab") === tab;
            } catch (_error) {
              return false;
            }
        }""",
        arg=tab,
        timeout=timeout,
    )


def _click_visible(locator) -> None:  # noqa: ANN001
    locator.scroll_into_view_if_needed(timeout=15000)
    locator.click()


def _collect_sample_tokens(page, base_url: str) -> dict[str, str]:  # noqa: ANN001
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_workstream, component_id, _component_href = _select_radar_row_with_link(
        radar,
        "a.chip-registry-component",
        "expected a Radar workstream with a registry deeplink",
        query_key="component",
    )

    _atlas_row_workstream, diagram_id, diagram_href = _select_radar_row_with_link(
        radar,
        "a.chip-topology-diagram",
        "expected a Radar workstream with an atlas deeplink",
        query_key="diagram",
    )
    atlas_workstream = _extract_query_param(diagram_href, "workstream")

    response = page.goto(base_url + "/odylith/index.html?tab=casebook", wait_until="domcontentloaded")
    assert response is not None and response.ok
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    bug_route = str(casebook.locator("button.bug-row").first.get_attribute("data-bug") or "").strip()
    assert bug_route, "expected casebook bug route"

    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass_workstream = compass.locator("a.ws-id-btn").first.inner_text().strip()
    assert re.fullmatch(r"B-\d{3,}", compass_workstream), compass_workstream

    return {
        "radar_workstream": radar_workstream,
        "registry_component": component_id,
        "atlas_workstream": atlas_workstream,
        "atlas_diagram": diagram_id,
        "casebook_bug": bug_route,
        "compass_workstream": compass_workstream,
    }


def _assert_radar_selection(page, workstream: str) -> None:  # noqa: ANN001
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar.locator('#detail [data-kpi="workstream-id"] .v', has_text=workstream).wait_for(timeout=15000)


def _assert_registry_selection(page, component_id: str) -> None:  # noqa: ANN001
    assert page.locator("#tab-registry").get_attribute("aria-selected") == "true"
    registry = page.frame_locator("#frame-registry")
    registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
    registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)


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


def _assert_atlas_selection(page, *, workstream: str, diagram_id: str) -> None:  # noqa: ANN001
    assert page.locator("#tab-atlas").get_attribute("aria-selected") == "true"
    atlas = page.frame_locator("#frame-atlas")
    atlas.locator("h1", has_text="Atlas").wait_for(timeout=15000)
    atlas.locator("#diagramId", has_text=diagram_id).wait_for(timeout=15000)
    if workstream:
        _wait_for_shell_query_param(page, tab="atlas", key="workstream", value=workstream)
    else:
        _wait_for_shell_tab(page, "atlas")
        page.wait_for_function(
            """() => {
                try {
                  const url = new URL(window.location.href);
                  return !url.searchParams.has("workstream");
                } catch (_error) {
                  return false;
                }
            }""",
            timeout=15000,
        )


def _atlas_total(atlas) -> int:  # noqa: ANN001
    return int(atlas.locator("#statTotal").inner_text().strip())


def _atlas_workstream_filter_value(atlas) -> str:  # noqa: ANN001
    return atlas.locator("#workstreamFilter").input_value().strip()


def _atlas_selected_diagram(atlas) -> str:  # noqa: ANN001
    return atlas.locator("#diagramId").inner_text().strip()


def _atlas_owner_workstreams(atlas) -> list[str]:  # noqa: ANN001
    return atlas.locator("#ownerWorkstreamLinks a.workstream-pill-link").evaluate_all(
        """nodes => nodes
          .map((node) => (node.textContent || "").trim())
          .filter((token) => token.length > 0)
        """
    )


def _atlas_related_workstreams(atlas) -> list[str]:  # noqa: ANN001
    return atlas.locator(
        "#ownerWorkstreamLinks a.workstream-pill-link, "
        "#activeWorkstreamLinks a.workstream-pill-link, "
        "#historicalWorkstreamLinks a.workstream-pill-link"
    ).evaluate_all(
        """nodes => Array.from(new Set(nodes
          .map((node) => (node.textContent || "").trim())
          .filter((token) => token.length > 0)))"""
    )


def _atlas_workstream_options(atlas) -> list[str]:  # noqa: ANN001
    return atlas.locator("#workstreamFilter option").evaluate_all(
        """nodes => nodes
          .map((node) => (node.value || "").trim())
          .filter((token) => token.length > 0)
        """
    )


def _assert_casebook_selection(page, bug_route: str) -> None:  # noqa: ANN001
    assert page.locator("#tab-casebook").get_attribute("aria-selected") == "true"
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
    casebook.locator("#detailPane .detail-title").wait_for(timeout=15000)


def _assert_compass_selection(page, *, workstream: str, window_token: str) -> None:  # noqa: ANN001
    assert page.locator("#tab-compass").get_attribute("aria-selected") == "true"
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator(f'button[data-window="{window_token}"].active').wait_for(timeout=15000)
    compass.locator("#scope-pill", has_text=workstream).wait_for(timeout=15000)
    compass.get_by_role("heading", name="Standup Brief").wait_for(timeout=15000)


def _compass_kpi_value(compass, label: str) -> int:  # noqa: ANN001
    raw = compass.locator(".stat").evaluate_all(
        """(nodes, targetLabel) => {
          const match = nodes.find((node) => {
            const labelNode = node.querySelector(".kpi-label");
            return ((labelNode && labelNode.textContent) || "").trim() === targetLabel;
          });
          const valueNode = match ? match.querySelector(".kpi-value") : null;
          return ((valueNode && valueNode.textContent) || "").trim();
        }""",
        label,
    )
    match = re.search(r"\d+", str(raw))
    assert match, f"expected numeric Compass KPI for {label!r}, got {raw!r}"
    return int(match.group(0))


def _assert_compass_live_state(compass, *, window_token: str) -> None:  # noqa: ANN001
    compass.locator(f'button[data-window="{window_token}"].active').wait_for(timeout=15000)
    compass.get_by_role("heading", name="Standup Brief").wait_for(timeout=15000)
    brief_chip = ""
    if compass.locator("#digest-list .standup-brief-chip").count():
        brief_chip = compass.locator("#digest-list .standup-brief-chip").first.inner_text().strip().lower()
    brief_notice = ""
    if compass.locator("#digest-list .brief-status-title").count():
        brief_notice = compass.locator("#digest-list .brief-status-title").first.inner_text().strip().lower()
    assert "last known good cache" not in brief_chip
    assert "stale last known good" not in brief_notice
    assert _compass_kpi_value(compass, "Critical Risks") >= 0
    assert compass.locator("#risk-list .risk, #risk-list .empty").count() > 0
    assert compass.locator(
        "#timeline .tx-card, #timeline .empty, #timeline .timeline-day-title, #timeline .hour-empty"
    ).count() > 0


def test_surface_entrypoints_redirect_into_shell_and_load_requested_surface(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    surfaces = (
        ("/odylith/radar/radar.html", "radar", "#frame-radar", "h1", "Backlog Workstream Radar"),
        ("/odylith/registry/registry.html", "registry", "#frame-registry", "h1", "Component Registry"),
        ("/odylith/casebook/casebook.html", "casebook", "#frame-casebook", "h1", "Casebook"),
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
        ("#tab-casebook", "#frame-casebook", "h1", "Casebook"),
        ("#tab-atlas", "#frame-atlas", "h1", "Atlas"),
        ("#tab-compass", "#frame-compass", "h1", "Executive Compass"),
    )

    for tab_selector, frame_selector, heading_selector, heading_text in tab_expectations:
        page.locator(tab_selector).click()
        frame = page.frame_locator(frame_selector)
        frame.locator(heading_selector, has_text=heading_text).wait_for(timeout=15000)
        assert page.locator(tab_selector).get_attribute("aria-selected") == "true"

    _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)


def test_compass_window_switches_keep_brief_visible(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass", wait_until="domcontentloaded")
    assert response is not None and response.ok

    page.locator("#tab-compass").wait_for(timeout=15000)
    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.get_by_role("button", name="24h Window").click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=compass(&.*)?window=24h(&.*|$)"), timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")

    compass.get_by_role("button", name="48h Window").click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=compass(&.*)?window=48h(&.*|$)"), timeout=15000)
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
    assert compass_release == "0.1.11"
    assert compass.locator(".stat .kpi-label", has_text="NEXT RELEASE").count() == 0
    assert compass.locator("#release-groups .execution-wave-section").count() >= 2
    release_targets_text = compass.locator("#release-groups").inner_text().strip()
    assert "Target Release" in release_targets_text
    assert "0.1.12" in release_targets_text
    assert "Next release target across active workstreams." in release_targets_text

    page.locator("#tab-radar").click()
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    radar_release_label = radar.locator(".stats .stat.stat-release-only .label").first.inner_text().strip()
    radar_release = radar.locator(".stats .stat.stat-release-only .value").first.inner_text().strip()
    assert radar_release_label == "TARGET RELEASE"
    assert radar_release == "0.1.11"

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


def test_shell_cross_tab_hops_keep_compass_global_runtime_fresh(browser_context) -> None:  # noqa: ANN001
    base_url, context = browser_context
    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
    response = page.goto(base_url + "/odylith/index.html?tab=compass&window=24h&date=live", wait_until="domcontentloaded")
    assert response is not None and response.ok

    compass = page.frame_locator("#frame-compass")
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    _assert_compass_live_state(compass, window_token="24h")

    for tab_selector, frame_selector, heading_text in (
        ("#tab-registry", "#frame-registry", "Component Registry"),
        ("#tab-casebook", "#frame-casebook", "Casebook"),
        ("#tab-atlas", "#frame-atlas", "Atlas"),
        ("#tab-radar", "#frame-radar", "Backlog Workstream Radar"),
    ):
        page.locator(tab_selector).click()
        page.frame_locator(frame_selector).locator("h1", has_text=heading_text).wait_for(timeout=15000)

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

    first_workstream_link = compass.locator("a.ws-id-btn").first
    first_workstream_id = first_workstream_link.inner_text().strip()
    assert re.fullmatch(r"B-\d{3,}", first_workstream_id), first_workstream_id
    first_workstream_link.click()
    page.wait_for_url(
        re.compile(rf".*/odylith/index\.html\?tab=radar(&.*)?workstream={re.escape(first_workstream_id)}(&.*|$)"),
        timeout=15000,
    )
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"
    page.frame_locator("#frame-radar").locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)

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
    compass.locator("a.ws-id-btn").first.click()
    page.wait_for_url(re.compile(r".*/odylith/index\.html\?tab=radar(&.*)?workstream=B-\d{3,}(&.*|$)"), timeout=15000)
    assert page.locator("#tab-radar").get_attribute("aria-selected") == "true"

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

    _click_visible(radar.locator("#detail a.chip-registry-component:visible").first)
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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)

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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
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
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    _assert_casebook_counts(
        casebook,
        expected_open_total=expected_open_total,
        expected_total_cases=expected_total_cases,
    )

    page.reload(wait_until="domcontentloaded")
    casebook = page.frame_locator("#frame-casebook")
    casebook.locator("h1", has_text="Casebook").wait_for(timeout=15000)
    _assert_casebook_counts(
        casebook,
        expected_open_total=expected_open_total,
        expected_total_cases=expected_total_cases,
    )

    failed_requests.clear()
    bad_responses.clear()
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
