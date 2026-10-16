"""Strict browser failure recording and selected Registry detail readiness."""

from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from odylith.runtime.surfaces import casebook_list_presentation_runtime, registry_selection_ui
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
        window.selectionOutcomes = [];
        window.select = createRegistrySelection({
            detail: document.querySelector('#detail'), timeline: document.querySelector('#timeline'),
            timelineCount: document.querySelector('#count'), sourceCount: 1,
            loadDetail: () => new Promise(resolve => { window.finishDetail = resolve; }),
            renderDetail: row => { document.querySelector('#detail').innerHTML =
                '<h2 class="component-name">' + row.component_id + '</h2>'; },
            renderTimeline: () => {},
            onOutcome: outcome => window.selectionOutcomes.push(outcome),
        });
        window.selectionPromise = window.select('wanted', [{ component_id: 'wanted' }]);
    }''')
    assert frame.evaluate("() => typeof window.finishDetail") == "function"
    assert frame.evaluate("() => window.selectionOutcomes") == [{"id": "", "outcome": "loading"}]
    return page, frame


@pytest.mark.parametrize("helper", ("assert", "select"))
@pytest.mark.parametrize("state", ("pending", "wrong-component", "ready"))
def test_registry_readiness_requires_loaded_detail_owned_by_selection(context, monkeypatch, helper, state):
    page, frame = _registry_page(context)
    if state != "pending":
        frame.evaluate("async () => { window.finishDetail({ component_id: 'wanted' }); await window.selectionPromise; }")
        assert frame.evaluate("() => window.selectionOutcomes") == [
            {"id": "", "outcome": "loading"}, {"id": "wanted", "outcome": "ready"},
        ]
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
    if state == "pending":
        assert frame.evaluate("() => window.selectionOutcomes") == [{"id": "", "outcome": "loading"}]
        frame.evaluate("async () => { window.finishDetail({ component_id: 'wanted' }); await window.selectionPromise; }")
        assert frame.evaluate("() => window.selectionOutcomes.at(-1)") == {"id": "wanted", "outcome": "ready"}
    page.close()


@pytest.mark.parametrize(("open_total", "total"), ((2, 3), (0, 0)))
def test_casebook_count_assertions_wait_for_rendered_observations(monkeypatch, open_total, total):
    selectors = ("#kpiOpenTotal", "#kpiTotalCases", "button.bug-row", "#listMeta")
    locators = {selector: Mock(name=selector) for selector in selectors}
    locators[selectors[0]].inner_text.return_value = str(open_total)
    locators[selectors[1]].inner_text.return_value = str(total)
    locators[selectors[2]].count.return_value = total
    locators[selectors[3]].inner_text.return_value = f"{total} visible"
    if total == 0:
        for pane in ("#bugList", "#detailPane"):
            locators[f'{pane} .empty-state[role="status"]'] = Mock()
    assertions = {locator: Mock() for locator in locators.values()}
    expect = Mock(side_effect=assertions.__getitem__)
    monkeypatch.setattr(support.playwright_sync, "expect", expect)

    support._assert_casebook_counts(
        SimpleNamespace(locator=locators.__getitem__),
        expected_open_total=open_total, expected_total_cases=total,
    )

    assert expect.call_args_list == [call(locator) for locator in locators.values()]
    for selector, text in ((selectors[0], str(open_total)), (selectors[1], str(total)),
                           (selectors[3], f"{total} visible")):
        assertions[locators[selector]].to_have_text.assert_called_once_with(text, timeout=15000)
    assertions[locators[selectors[2]]].to_have_count.assert_called_once_with(total, timeout=15000)
    if total == 0:
        for pane in ("#bugList", "#detailPane"):
            assertions[locators[f'{pane} .empty-state[role="status"]']].to_be_visible.assert_called_once_with(timeout=15000)


@pytest.mark.parametrize("state", ("delayed-correct", "wrong", "missing", "empty-placeholder", "empty-ready"))
def test_casebook_counts_require_completed_values_not_static_placeholders(context, monkeypatch, state):
    page = context.new_page()
    page.set_content('''<h1>Casebook</h1><span id="kpiOpenTotal">0</span>
        <span id="kpiTotalCases">0</span><span id="listMeta">0 visible</span>
        <div id="bugList"></div><div id="detailPane"></div>''')
    page.add_script_tag(content=casebook_list_presentation_runtime.LIST_PRESENTATION_JS)
    page.evaluate('''state => {
        window.completeCounts = () => {
            const empty = state.startsWith('empty');
            const rows = empty ? [] : [{bug_route:'one'}, {bug_route:'two'}];
            const presentation = casebookListPresentation({rows, totalCount:rows.length,
                selectedRoute:'', escapeHtml:String, displayTokenLabel:String});
            document.querySelector('#kpiOpenTotal').textContent = empty ? '0' : '1';
            document.querySelector('#kpiTotalCases').textContent = String(rows.length);
            document.querySelector('#listMeta').textContent = presentation.meta;
            document.querySelector('#bugList').innerHTML = presentation.listHtml;
            document.querySelector('#detailPane').innerHTML = presentation.detailHtml || '';
        };
        if (state === 'missing') document.querySelector('#kpiOpenTotal').remove();
        if (state === 'empty-ready') window.completeCounts();
        if (state === 'delayed-correct') requestAnimationFrame(() => requestAnimationFrame(window.completeCounts));
    }''', state)
    original_expect = support.playwright_sync.expect

    def bounded_expect(locator):
        assertion = original_expect(locator)
        if state in {"delayed-correct", "empty-ready"}:
            return assertion
        return SimpleNamespace(**{
            name: lambda *args, _method=getattr(assertion, name), **kwargs:
                _method(*args, **{**kwargs, "timeout": 100})
            for name in ("to_have_text", "to_have_count", "to_be_visible")
        })

    monkeypatch.setattr(support.playwright_sync, "expect", bounded_expect)
    empty = state.startswith("empty")
    try:
        if state in {"delayed-correct", "empty-ready"}:
            support._assert_casebook_counts(page, expected_open_total=0 if empty else 1,
                                            expected_total_cases=0 if empty else 2)
        else:
            with pytest.raises(AssertionError):
                support._assert_casebook_counts(page, expected_open_total=0 if empty else 1,
                                                expected_total_cases=0 if empty else 2)
    finally:
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
