from __future__ import annotations

import contextlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
import re
import threading
from typing import Iterator
from urllib.parse import parse_qs, urlparse

import pytest

playwright_sync = pytest.importorskip("playwright.sync_api")


_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_SURFACE_HTML_RE = re.compile(
    r"^http://127\.0\.0\.1:\d+/odylith/(radar|registry|casebook|atlas|compass)/[^?#]+\.html(?:[?#].*)?$"
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
        if line.startswith("| Date |") or line.startswith("| --- |"):
            continue
        if section == "open":
            open_total += 1
        elif section == "closed":
            closed_total += 1
    return open_total, open_total + closed_total


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


def _wait_for_compass_brief_state(
    page,
    *,
    window_token: str,
    scope_label: str,
    timeout: int = 15000,
) -> None:  # noqa: ANN001
    page.wait_for_function(
        """({ windowToken, scopeLabel }) => {
            const frame = document.querySelector("#frame-compass");
            const doc = frame && frame.contentDocument;
            const target = doc && doc.querySelector("#digest-list");
            if (!target || !target.dataset) return false;
            return (target.dataset.briefStatus || "") === "ready"
              && (target.dataset.briefWindow || "") === windowToken
              && (target.dataset.briefScope || "") === scopeLabel;
        }""",
        arg={"windowToken": window_token, "scopeLabel": scope_label},
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
    assert compass.locator("#timeline .tx-card, #timeline .empty").count() > 0
