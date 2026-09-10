"""Strict browser failure recording and selected Registry detail readiness."""

from types import SimpleNamespace

import pytest

from odylith.runtime.surfaces import registry_selection_ui
from tests.integration.runtime import surface_browser_test_support as support
from tests.unit.runtime.test_surface_browser_request_observer import PublicContext


_FORMERLY_EXEMPT_PATHS = (
    "/odylith/registry/registry.html",
    "/odylith/compass/runtime/history/index.v1.json",
    "/odylith/compass/runtime/current.v1.js",
    "/odylith/compass/compass-source-truth.v1.json",
    "/odylith/registry/registry-detail-shard-0.v1.js",
)


@pytest.fixture()
def context():
    for _pw, browser in support._browser():
        context = browser.new_context()
        try:
            yield context
        finally:
            context.close()


@pytest.mark.parametrize(
    ("error_code", "expected"),
    (("connectionreset", "net::ERR_CONNECTION_RESET"), ("aborted", "net::ERR_ABORTED")),
)
def test_real_request_failure_string_is_retained_and_fails(context, error_code, expected):
    with support._new_page(context) as (page, observation):
        url = "http://127.0.0.1:9876/odylith/registry/registry.html"
        page.route(url, lambda route: route.abort(error_code))
        with page.expect_event("requestfailed") as event:
            with pytest.raises(support.playwright_sync.Error):
                page.goto(url)
        assert event.value.failure == expected
        with pytest.raises(AssertionError, match="request failures"):
            support._assert_clean_page(page, observation)
        assert [(failure.url, failure.reason) for failure in observation.snapshot.failures] == [(url, expected)]


@pytest.mark.parametrize("path", _FORMERLY_EXEMPT_PATHS)
@pytest.mark.parametrize("failure", (None, "", "net::ERR_FILE_NOT_FOUND", "unrecognized failure"))
def test_unknown_and_file_errors_are_never_exempted(path, failure):
    context = PublicContext()
    url = "http://127.0.0.1:9876" + path
    with support._new_page(context) as (page, observation):
        context.native("Network.requestWillBeSent", requestId="request", frameId="main", loaderId="loader",
                       type="Document", request={"url": url})
        context.native("Network.loadingFailed", requestId="request", errorText=failure, canceled=True)
        with pytest.raises(AssertionError, match="request failures"):
            support._assert_clean_page(page, observation)
        expected = "<unknown failure>" if failure is None else failure
        assert [(row.url, row.reason) for row in observation.snapshot.failures] == [(url, expected)]


@pytest.mark.parametrize("path", _FORMERLY_EXEMPT_PATHS)
@pytest.mark.parametrize("status", (404, 503))
def test_http_errors_on_formerly_exempt_paths_still_fail(path, status):
    context = PublicContext()
    url = "http://127.0.0.1:9876" + path
    with support._new_page(context) as (page, observation):
        page.emit("response", SimpleNamespace(url=url, status=status))
        with pytest.raises(AssertionError, match="http error responses"):
            support._assert_clean_page(page, observation)
        assert [(row.status, row.url) for row in observation.snapshot.http_errors] == [(status, url)]


def _registry_page(context):
    page = context.new_page()
    page.set_content('<button id="tab-registry" aria-selected="true">Registry</button><iframe id="frame-registry" name="registry"></iframe>')
    frame = page.frame(name="registry")
    frame.set_content('''<h1>Component Registry</h1>
        <button data-component="wanted" class="active">Wanted</button>
        <div id="detail"></div><div id="timeline"></div><span id="count"></span>''')
    frame.add_script_tag(content=registry_selection_ui.runtime_js())
    frame.evaluate('''() => {
        window.select = createRegistrySelection({
            detail: document.querySelector('#detail'), timeline: document.querySelector('#timeline'),
            timelineCount: document.querySelector('#count'), sourceCount: 1,
            loadDetail: () => new Promise(resolve => { window.finishDetail = resolve; }),
            renderDetail: row => { document.querySelector('#detail').innerHTML =
                '<h2 class="component-name">' + row.component_id + '</h2>'; },
            renderTimeline: () => {},
        });
        window.select('wanted', [{ component_id: 'wanted' }]);
    }''')
    return page, frame


@pytest.mark.parametrize("helper", ("assert", "select"))
@pytest.mark.parametrize("state", ("pending", "wrong-component", "ready"))
def test_registry_readiness_requires_loaded_detail_owned_by_selection(context, monkeypatch, helper, state):
    page, frame = _registry_page(context)
    if state != "pending":
        frame.evaluate("() => window.finishDetail({ component_id: 'wanted' })")
        frame.locator("#detail .component-name").wait_for()
    if state == "wrong-component":
        frame.evaluate("() => { document.querySelector('#detail').dataset.selectedComponent = 'other'; }")
    assert frame.locator('button[data-component="wanted"].active').is_visible()
    monkeypatch.setattr(support, "_wait_for_shell_query_param", lambda *args, **kwargs: None)
    original_wait = support.playwright_sync.Locator.wait_for

    def bounded_wait(locator, **kwargs):
        return original_wait(locator, **{**kwargs, "timeout": 100})

    monkeypatch.setattr(support.playwright_sync.Locator, "wait_for", bounded_wait)

    def check():
        if helper == "assert":
            support._assert_registry_selection(page, "wanted")
        else:
            _registry, selected = support._select_registry_component_with_detail_selector(
                page, detail_selector=".component-name", failure_message="no loaded component",
            )
            assert selected == "wanted"

    if state == "ready":
        check()
    else:
        with pytest.raises(support.playwright_sync.TimeoutError):
            check()
    page.close()


@pytest.mark.parametrize("origin", (
    "http://127.0.0.1:9876", "https://127.0.0.1:9876",
    "http://localhost:9876", "https://localhost:9876",
    "http://[::1]:9876", "https://[::1]:9876",
))
@pytest.mark.parametrize("status", (404, 503))
def test_http_errors_are_retained_across_local_origins(origin, status):
    context = PublicContext()
    url = origin + "/missing.js"
    with support._new_page(context) as (page, observation):
        page.emit("response", SimpleNamespace(url=url, status=status))
        with pytest.raises(AssertionError, match="http error responses"):
            support._assert_clean_page(page, observation)
        assert [(row.status, row.url) for row in observation.snapshot.http_errors] == [(status, url)]
