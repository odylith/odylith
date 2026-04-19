"""Shared headless-browser support for Odylith integration surface tests."""

from __future__ import annotations

import contextlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import threading
import traceback
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_SURFACE_HTML_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/(radar|registry|casebook|atlas|compass)/[^?#]+\.html(?:[?#].*)?$"
)
_LOCAL_COMPASS_HISTORY_JSON_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/compass/runtime/history/(?:index|\d{4}-\d{2}-\d{2})\.v1\.json(?:[?#].*)?$"
)
_LOCAL_COMPASS_RUNTIME_JSON_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/compass/runtime/current\.v1\.(?:json|js)(?:[?#].*)?$"
)
_LOCAL_COMPASS_SOURCE_TRUTH_JSON_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/compass/compass-source-truth\.v1\.json(?:[?#].*)?$"
)
_EXTERNAL_MERMAID_CDN_REQUEST_RE = re.compile(
    r"^GET https://cdn\.jsdelivr\.net/npm/mermaid@11/dist/mermaid\.min\.js(?:\s+.*)?$"
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


@pytest.fixture()
def browser_context() -> Iterator[tuple[str, object]]:
    with _static_server(root=_REPO_ROOT) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 1440, "height": 1100})
            try:
                yield base_url, context
            finally:
                context.close()


@pytest.fixture()
def compact_browser_context() -> Iterator[tuple[str, object]]:
    with _static_server(root=_REPO_ROOT) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 430, "height": 932})
            try:
                yield base_url, context
            finally:
                context.close()


def _new_page(context) -> tuple[object, list[str], list[str], list[str], list[str]]:  # noqa: ANN001
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
        if _LOCAL_COMPASS_HISTORY_JSON_RE.match(url) and (
            not lowered_error or "err_aborted" in lowered_error or "abort" in lowered_error
        ):
            return
        if _LOCAL_COMPASS_RUNTIME_JSON_RE.match(url) and (
            not lowered_error or "err_aborted" in lowered_error or "abort" in lowered_error
        ):
            return
        if _LOCAL_COMPASS_SOURCE_TRUTH_JSON_RE.match(url) and (
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


def _failure_screenshot_path(name: str) -> Path | None:
    root = str(os.environ.get("ODYLITH_BROWSER_FAILURE_SCREENSHOTS") or "").strip()
    if not root:
        return None
    slug = re.sub(r"[^a-z0-9._-]+", "-", str(name).strip().lower()).strip("-") or "browser-failure"
    return Path(root).expanduser().resolve() / f"{slug}.png"


def _assert_clean_page(
    page,
    console_errors: list[str],
    page_errors: list[str],
    failed_requests: list[str],
    bad_responses: list[str],
    *,
    screenshot_path: Path | None = None,
) -> None:  # noqa: ANN001
    if any((console_errors, page_errors, failed_requests, bad_responses)) and screenshot_path is not None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        with contextlib.suppress(Exception):
            page.screenshot(path=str(screenshot_path), full_page=True)
    assert console_errors == [], f"console errors: {console_errors}"
    assert page_errors == [], f"page errors: {page_errors}"
    assert failed_requests == [], f"request failures: {failed_requests}"
    assert bad_responses == [], f"http error responses: {bad_responses}"
    page.close()


def _discard_external_mermaid_cdn_failures(failed_requests: list[str]) -> None:
    """Drop known standalone-doc Mermaid CDN misses from route-integrity assertions."""
    failed_requests[:] = [
        entry for entry in failed_requests if not _EXTERNAL_MERMAID_CDN_REQUEST_RE.match(entry)
    ]


def _extract_query_param(href: str, key: str) -> str:
    values = parse_qs(urlparse(href).query).get(key, ())
    return str(values[0]).strip() if values else ""


def _casebook_index_counts() -> tuple[int, int]:
    """Return the open-case count and total case count from the Casebook index."""
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
        if line.startswith("| Bug ID |") or line.startswith("| Date |") or line.startswith("| --- |"):
            continue
        if section == "open":
            open_total += 1
        elif section == "closed":
            closed_total += 1
    return open_total, open_total + closed_total


def _assert_casebook_counts(casebook, *, expected_open_total: int, expected_total_cases: int) -> None:  # noqa: ANN001
    """Assert the visible Casebook counters and row count stay aligned."""
    assert casebook.locator("#kpiOpenTotal").inner_text().strip() == str(expected_open_total)
    assert casebook.locator("#kpiTotalCases").inner_text().strip() == str(expected_total_cases)
    assert casebook.locator("button.bug-row").count() == expected_total_cases
    assert casebook.locator("#listMeta").inner_text().strip() == f"Visible: {expected_total_cases}"


def _pane_hidden(page, frame_selector: str) -> bool:  # noqa: ANN001
    """Return whether a shell iframe pane is currently hidden."""
    return bool(page.locator(frame_selector).evaluate("node => Boolean(node.hidden)"))


def _assert_single_visible_pane(page, active_frame_selector: str) -> None:  # noqa: ANN001
    """Assert the shell hides every iframe pane except the active one."""
    panes = (
        "#frame-radar",
        "#frame-registry",
        "#frame-casebook",
        "#frame-atlas",
        "#frame-compass",
    )
    visible = [selector for selector in panes if not _pane_hidden(page, selector)]
    assert visible == [active_frame_selector]


def _run_in_browser_thread(callback) -> None:  # noqa: ANN001
    """Run a browser proof in a worker thread and forward any failure with traceback."""
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


def _select_radar_row_with_link(
    radar,
    link_selector: str,
    failure_message: str,
    *,
    query_key: str,
) -> tuple[str, str, str]:  # noqa: ANN001
    """Return the first Radar workstream whose detail pane renders a deep link."""
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


def _locator_appears(locator, *, timeout: int = 1000) -> bool:  # noqa: ANN001
    """Return whether a locator attaches within a short bounded timeout."""
    with contextlib.suppress(Exception):
        locator.first.wait_for(state="attached", timeout=timeout)
        return True
    return False


def _first_non_default_option(frame, selector: str, excluded: set[str] | None = None) -> str:  # noqa: ANN001
    """Return the first non-default select option value, excluding explicit tokens."""
    excluded_tokens = {"all", ""}
    if excluded:
        excluded_tokens |= {str(token) for token in excluded}
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => String(node.value || "").trim())
          .filter((token) => token.length > 0)
        """
    )
    for token in options:
        if token not in excluded_tokens:
            return str(token)
    return ""


def _first_filter_value_with_results(frame, selector: str, item_selector: str) -> tuple[str, int]:  # noqa: ANN001
    """Return the first filter option that leaves at least one visible result."""
    options = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => String(node.value || "").trim())
          .filter((token) => token.length > 0 && token !== "all")
        """
    )
    for token in options:
        frame.locator(selector).select_option(token)
        count = frame.locator(item_selector).count()
        if count > 0:
            return str(token), count
    return "", 0


def _reset_select_to_first_option(frame, selector: str) -> None:  # noqa: ANN001
    """Reset a select control back to its first defined option value."""
    values = frame.locator(f"{selector} option").evaluate_all(
        """nodes => nodes
          .map((node) => String(node.value || ""))
        """
    )
    assert values, f"expected at least one option for {selector}"
    frame.locator(selector).select_option(str(values[0]))


def _select_radar_workstream_with_detail_selector(
    page,
    *,
    detail_selector: str,
    failure_message: str,
    detail_ready_selector: str = "#detail .detail-title",
    selector_timeout: int = 1000,
) -> tuple[object, str]:  # noqa: ANN001
    """Select the first Radar workstream whose detail pane renders a selector."""
    radar = page.frame_locator("#frame-radar")
    row_buttons = radar.locator("button[data-idea-id]")
    count = row_buttons.count()
    for index in range(count):
        button = row_buttons.nth(index)
        idea_id = str(button.get_attribute("data-idea-id") or "").strip()
        if not idea_id:
            continue
        button.click()
        _wait_for_shell_query_param(page, tab="radar", key="workstream", value=idea_id)
        radar.locator(detail_ready_selector).wait_for(timeout=15000)
        if _locator_appears(radar.locator(f"#detail {detail_selector}"), timeout=selector_timeout):
            return radar, idea_id
    raise AssertionError(failure_message)


def _wait_for_radar_detail_id(radar, idea_id: str) -> None:  # noqa: ANN001
    """Wait for the Radar detail pane to settle on the requested workstream id."""
    radar.locator(f'button[data-idea-id="{idea_id}"].active').wait_for(timeout=15000)
    radar.locator("#detail .detail-title").wait_for(timeout=15000)
    radar.locator("#detail").filter(has_text=idea_id).wait_for(timeout=15000)


def _open_radar_topology_relations(radar) -> None:  # noqa: ANN001
    """Expand the Radar topology-relations panel if it is present but still closed."""
    panel = radar.locator("#detail details.topology-relations-panel").first
    panel.wait_for(timeout=15000)
    if panel.get_attribute("open") is None:
        panel.evaluate("node => { node.open = true; }")
    panel.locator(".topology-relations").wait_for(timeout=15000)


def _select_radar_workstream(radar, idea_id: str) -> None:  # noqa: ANN001
    """Focus one Radar workstream by id while clearing filters that would hide it."""
    radar.locator("#query").fill("")
    for selector in ("#section", "#phase", "#activity", "#lane", "#priority"):
        radar.locator(selector).select_option("all")
    radar.locator("#query").fill(idea_id)
    radar.locator(f'button[data-idea-id="{idea_id}"]').wait_for(timeout=15000)
    radar.locator(f'button[data-idea-id="{idea_id}"]').first.click()
    _wait_for_radar_detail_id(radar, idea_id)
    radar.locator("#query").fill("")
    _wait_for_radar_detail_id(radar, idea_id)


def _select_registry_component_with_detail_selector(
    page,
    *,
    detail_selector: str,
    failure_message: str,
    detail_ready_selector: str = "#detail .component-name",
    selector_timeout: int = 1000,
) -> tuple[object, str]:  # noqa: ANN001
    """Select the first Registry component whose detail pane renders a selector."""
    registry = page.frame_locator("#frame-registry")
    buttons = registry.locator("button[data-component]")
    count = buttons.count()
    for index in range(count):
        button = buttons.nth(index)
        component_id = str(button.get_attribute("data-component") or "").strip()
        if not component_id:
            continue
        button.click()
        _wait_for_shell_query_param(page, tab="registry", key="component", value=component_id)
        registry.locator(f'button[data-component="{component_id}"].active').wait_for(timeout=15000)
        registry.locator(detail_ready_selector).wait_for(timeout=15000)
        if _locator_appears(registry.locator(f"#detail {detail_selector}"), timeout=selector_timeout):
            return registry, component_id
    raise AssertionError(failure_message)


def _wait_for_locator_count(page, frame_selector: str, locator_selector: str, expected: int) -> None:  # noqa: ANN001
    """Wait until a frame document exposes an exact locator count."""
    page.wait_for_function(
        """({ frameSelector, locatorSelector, expected }) => {
            const frame = document.querySelector(frameSelector);
            const doc = frame && frame.contentDocument;
            if (!doc) return false;
            return doc.querySelectorAll(locatorSelector).length === expected;
        }""",
        arg={"frameSelector": frame_selector, "locatorSelector": locator_selector, "expected": expected},
        timeout=15000,
    )


def _select_casebook_bug_with_detail_selector(
    page,
    *,
    detail_selector: str,
    failure_message: str,
    detail_ready_selector: str = "#detailPane .detail-title",
    selector_timeout: int = 1000,
) -> tuple[object, str]:  # noqa: ANN001
    """Select the first Casebook bug whose detail pane renders a selector."""
    casebook = page.frame_locator("#frame-casebook")
    rows = casebook.locator("button.bug-row")
    count = rows.count()
    for index in range(count):
        row = rows.nth(index)
        bug_route = str(row.get_attribute("data-bug") or "").strip()
        if not bug_route:
            continue
        row.click()
        _wait_for_shell_query_param(page, tab="casebook", key="bug", value=bug_route)
        casebook.locator(f'button.bug-row.active[data-bug="{bug_route}"]').wait_for(timeout=15000)
        casebook.locator(detail_ready_selector).wait_for(timeout=15000)
        if _locator_appears(casebook.locator(f"#detailPane {detail_selector}"), timeout=selector_timeout):
            return casebook, bug_route
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


def _wait_for_compass_brief_state(
    page,
    *,
    window_token: str,
    scope_label: str,
    statuses: tuple[str, ...] = ("ready",),
    timeout: int = 15000,
) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ windowToken, scopeLabel, statuses }) => {
            const frame = document.querySelector("#frame-compass");
            const doc = frame && frame.contentDocument;
            const target = doc && doc.querySelector("#digest-list");
            if (!target || !target.dataset) return false;
            const status = String((target.dataset.briefStatus || "")).trim().toLowerCase();
            const allowed = Array.isArray(statuses)
              ? statuses.map((value) => String(value || "").trim().toLowerCase()).filter(Boolean)
              : [];
            return allowed.includes(status)
              && (target.dataset.briefWindow || "") === windowToken
              && (target.dataset.briefScope || "") === scopeLabel;
        }""",
        arg={"windowToken": window_token, "scopeLabel": scope_label, "statuses": list(statuses)},
        timeout=timeout,
    )


def _click_visible(locator) -> None:  # noqa: ANN001
    locator.scroll_into_view_if_needed(timeout=15000)
    locator.click()


def _compass_brief_metadata(compass) -> dict[str, str]:  # noqa: ANN001
    return compass.locator("#digest-list").evaluate(
        """node => ({
          status: String((node.dataset && node.dataset.briefStatus) || "").trim(),
          source: String((node.dataset && node.dataset.briefSource) || "").trim(),
          fingerprint: String((node.dataset && node.dataset.briefFingerprint) || "").trim(),
          generatedUtc: String((node.dataset && node.dataset.briefGeneratedUtc) || "").trim(),
          cacheMode: String((node.dataset && node.dataset.briefCacheMode) || "").trim(),
          window: String((node.dataset && node.dataset.briefWindow) || "").trim(),
          scope: String((node.dataset && node.dataset.briefScope) || "").trim(),
          hasNotice: String((node.dataset && node.dataset.briefHasNotice) || "").trim(),
          noticeReason: String((node.dataset && node.dataset.briefNoticeReason) || "").trim(),
        })"""
    )


def _collect_sample_tokens(page, base_url: str) -> dict[str, str]:  # noqa: ANN001
    response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
    assert response is not None and response.ok
    radar = page.frame_locator("#frame-radar")
    radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
    try:
        radar_workstream, component_id, _component_href = _select_radar_row_with_link(
            radar,
            "a.chip-registry-component",
            "expected a Radar workstream with a registry deeplink",
            query_key="component",
        )
    except AssertionError:
        _radar, radar_workstream = _select_radar_workstream_with_detail_selector(
            page,
            detail_selector=".detail-title",
            failure_message="expected a Radar workstream with a detail pane",
        )
        response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
        assert response is not None and response.ok
        registry = page.frame_locator("#frame-registry")
        registry.locator("h1", has_text="Component Registry").wait_for(timeout=15000)
        _registry, component_id = _select_registry_component_with_detail_selector(
            page,
            detail_selector=".component-name",
            failure_message="expected a Registry component for route token sampling",
        )
        response = page.goto(base_url + "/odylith/index.html?tab=radar", wait_until="domcontentloaded")
        assert response is not None and response.ok
        radar = page.frame_locator("#frame-radar")
        radar.locator("h1", has_text="Backlog Workstream Radar").wait_for(timeout=15000)
        _select_radar_workstream(radar, radar_workstream)

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
    """Return the distinct workstreams linked across Atlas detail sections."""
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
    _wait_for_compass_ready(compass)
    compass.locator(f'button[data-window="{window_token}"].active').wait_for(timeout=15000)
    compass.locator("#scope-pill", has_text=workstream).wait_for(timeout=15000)
    compass.get_by_role("heading", name="Standup Brief").wait_for(timeout=15000)


def _wait_for_compass_ready(compass) -> None:  # noqa: ANN001
    compass.locator("h1", has_text="Executive Compass").wait_for(timeout=15000)
    compass.locator('body[data-surface-ready="ready"]').wait_for(timeout=15000)


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
