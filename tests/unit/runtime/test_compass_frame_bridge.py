"""Provider-free controls for Compass navigation and committed render snapshots."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from odylith.runtime.surfaces import compass_dashboard_frontend_contract
from odylith.runtime.surfaces import governance_frame_bridge


_TEMPLATES = Path(__file__).resolve().parents[3] / "src/odylith/runtime/surfaces/templates/compass_dashboard"
_NODE_RUNNER = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
let input = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { input += chunk; });
process.stdin.on('end', async () => {
  const args = JSON.parse(input);
  const published = [];
  const intents = [];
  const nodes = new Map();
  let readSnapshot;
  const plain = value => JSON.parse(JSON.stringify(value));
  const window = {
    location: {pathname: '/odylith/compass/index.html', search: args.query},
    history: {replaceState(_state, _title, href) {
      window.location.search = new URL(href, 'http://localhost').search;
    }},
    clearTimeout() {},
    OdylithFrameBridge: {surface(options) {
      readSnapshot = options.readSnapshot;
      return {
        publish() { published.push(plain(readSnapshot())); },
        navigate(route) { intents.push(plain(route)); return args.embedded; },
        dispose() {},
      };
    }},
  };
  Object.defineProperty(window, 'parent', {get() { throw Error('Compass accessed its parent directly'); }});
  const document = {
    body: {dataset: {}},
    getElementById(id) {
      if (!nodes.has(id)) nodes.set(id, {
        innerHTML: '', dataset: {},
        classList: {add() {}, remove() {}, toggle() {}},
        setAttribute() {},
      });
      return nodes.get(id);
    },
  };
  const context = vm.createContext({
    assert: {...assert, deepEqual: (actual, expected) => assert.deepStrictEqual(plain(actual), plain(expected))},
    plain, window, document, URLSearchParams, URL, console,
    published, intents, snapshot: () => plain(readSnapshot()),
  });
  vm.runInContext('const WORKSTREAM_RE = /^B-\\d{3,}$/; const DATE_RE = /^\\d{4}-\\d{2}-\\d{2}$/; let CURRENT_STANDUP_BRIEF = null;', context);
  vm.runInContext(args.state, context);
  vm.runInContext(args.ui, context);
  try {
    await vm.runInContext(`(async () => { ${args.body}\n })()`, context);
  } catch (error) {
    console.error(error.stack);
    process.exitCode = 1;
  }
});
"""


def _run_compass_js(body: str, *, query: str = "", embedded: bool = True) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.fail("Node.js is required for Compass frame-bridge controls")
    result = subprocess.run(
        [node, "-e", _NODE_RUNNER],
        input=json.dumps(
            {
                "state": (_TEMPLATES / "compass-state.v1.js").read_text(encoding="utf-8"),
                "ui": (_TEMPLATES / "compass-ui-runtime.v1.js").read_text(encoding="utf-8"),
                "body": body,
                "query": query,
                "embedded": embedded,
            }
        ),
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_compass_asset_composes_shared_bridge_before_surface_registration() -> None:
    state_source = (_TEMPLATES / "compass-state.v1.js").read_text(encoding="utf-8")
    composed = compass_dashboard_frontend_contract.load_compass_shell_asset_text("compass-state.v1.js")
    assert composed == f"{governance_frame_bridge.runtime_js()}\n{state_source}"
    assert "window.OdylithFrameBridge.surface(" in state_source
    assert "window.parent" not in state_source
    assert "postMessage" not in state_source
    assert "syncParentShellCompassUrl" not in state_source


def test_compass_snapshot_preserves_original_request_before_runtime_defaults() -> None:
    _run_compass_js(
        r"""
        const requested = snapshot().requested;
        assert.deepEqual(requested, {
          tab: 'compass', workstream: 'B-999', window: '', date: '', audit_day: '',
        });
        assert.equal(snapshot().outcome, 'loading');
        assert.equal(snapshot().rendered, null);
        rollingThirtyDayBounds = () => ({min: '2026-08-16', max: '2026-09-14'});
        calendarMaxDateToken = () => '2026-09-14';
        knownHistoryDateTokens = () => [];
        filterEventsByWindow = filterTransactionsByWindow = () => [];
        collectScopedWorkstreamIds = workstreamRowsForLookup = () => [];
        const normalized = normalizeStateWithPayload(params(), {});
        assert.equal(normalized.state.workstream, '');
        assert.equal(normalized.state.window, '48h');
        assert.equal(normalized.state.date, 'live');
        assert.equal(normalized.state.audit_day, '2026-09-14');
        assert.deepEqual(snapshot().requested, requested);
        assert.equal(snapshot().rendered, null);
        assert.equal(published.length, 0);
        assert.equal(intents.length, 0);
        const query = new URLSearchParams(window.location.search);
        assert.equal(query.has('local_panel'), false);
        assert.equal(query.has('v'), false);
        assert.equal(query.has('scope'), false);
        """,
        query="?scope=B-999&local_panel=risks&v=cache-token",
    )


def test_compass_state_query_rebuilds_only_supported_canonical_fields() -> None:
    _run_compass_js(
        """
        const state = {workstream: 'B-007', window: '24h', date: 'live',
          audit_day: '2026-09-11', audit_day_pinned: true};
        assert.deepEqual([...new URLSearchParams(stateToQuery(state))], [
          ['tab', 'compass'], ['window', '24h'], ['scope', 'B-007'],
          ['date', 'live'], ['audit_day', '2026-09-11'],
        ]);
        state.date = state.audit_day;
        assert.equal(new URLSearchParams(stateToQuery(state)).has('audit_day'), false);
        state.date = 'live';
        state.audit_day_pinned = false;
        assert.equal(new URLSearchParams(stateToQuery(state)).has('audit_day'), false);
        assert.deepEqual([...new URLSearchParams(stateToQuery({
          workstream: 'invalid', window: 'invalid', date: 'invalid',
          audit_day: 'invalid', audit_day_pinned: true,
        }))], [['tab', 'compass'], ['window', '48h']]);
        assert.equal(intents.length, 0);
        assert.equal(published.length, 0);
        """,
        query="?tab=other&workstream=B-099&scope=B-098&window=48h&date=2026-09-01&audit_day=2026-08-31&local_panel=risks&v=cache-token",
    )


def test_compass_original_request_uses_existing_scope_alias_and_token_rules() -> None:
    _run_compass_js(
        """
        assert.deepEqual(snapshot().requested, {
          tab: 'compass', workstream: 'B-005', window: '24h',
          date: '2026-09-10', audit_day: '2026-09-09',
        });
        assert.equal(Object.isFrozen(compassRequestedRoute), true);
        assert.equal(published.length, 0);
        """,
        query="?workstream=B-005&scope=invalid&window=24H&date=2026-09-10&audit_day=2026-09-09&v=cache-token",
    )


@pytest.mark.parametrize("embedded", [True, False], ids=["embedded-intent", "standalone-local"])
def test_compass_navigation_has_one_owner_and_exact_shell_route(embedded: bool) -> None:
    _run_compass_js(
        f"""
        const before = window.location.search;
        const original = snapshot().requested;
        navigateCompass(new URLSearchParams('scope=B-007&window=24h&date=2026-09-12&audit_day=2026-09-11&local_panel=risks'));
        assert.deepEqual(intents, [{{route: {{
          tab: 'compass', workstream: 'B-007', window: '24h',
          date: '2026-09-12', audit_day: '2026-09-11',
        }}, replaceDocument: true}}]);
        assert.equal(window.location.search === before, {str(embedded).lower()});
        assert.deepEqual(snapshot().requested, original);
        assert.equal(published.length, 0);
        """,
        query="?scope=B-005",
        embedded=embedded,
    )


def test_compass_navigation_retains_existing_token_guards() -> None:
    _run_compass_js(
        """
        navigateCompass('scope=invalid&window=bad&date=not-a-date&audit_day=invalid');
        assert.deepEqual(intents[0], {route: {
          tab: 'compass', workstream: '', window: '48h', date: 'live', audit_day: '',
        }, replaceDocument: true});
        """
    )


_RENDER_SETUP = """
const stages = [];
let resolveView;
resolveCompassRuntimeView = () => new Promise(resolve => { resolveView = resolve; });
filterEventsByWindow = filterTransactionsByWindow = () => [];
syncControls = () => stages.push('controls');
staleRuntimeNotice = () => '';
renderKpis = () => stages.push('kpis');
renderDigest = () => stages.push('digest');
renderExecutionWaves = () => stages.push('waves');
renderReleaseGroups = () => stages.push('releases');
renderCurrentWorkstreams = () => stages.push('workstreams');
renderTimeline = () => stages.push('timeline');
renderRisks = () => stages.push('risks');
const actual = {workstream: '', window: '48h', date: 'live', audit_day: '2026-09-14'};
"""


@pytest.mark.parametrize("warning", ["", "Runtime unavailable for the requested day."])
def test_compass_publishes_only_after_actual_render_completion(warning: str) -> None:
    expected_outcome = "degraded" if warning else "ready"
    _run_compass_js(
        _RENDER_SETUP
        + f"""
        const pending = renderCompassRuntime(params(), {{payload: {{}}, source: 'runtime-json', warning: {json.dumps(warning)}}});
        assert.equal(snapshot().outcome, 'loading');
        assert.equal(published.length, 0);
        assert.equal(document.body.dataset.surfaceReady, 'loading');
        resolveView({{payload: {{}}, normalized: {{warnings: []}}, state: actual, summaryState: actual, summaryEvents: []}});
        await pending;
        assert.deepEqual(stages, ['controls', 'kpis', 'digest', 'waves', 'releases', 'workstreams', 'timeline', 'risks']);
        assert.equal(published.length, 1);
        assert.equal(published[0].outcome, {json.dumps(expected_outcome)});
        assert.deepEqual(published[0].rendered, {{tab: 'compass', ...actual}});
        assert.equal(published[0].requested.workstream, 'B-999');
        assert.equal(published[0].requested.audit_day, '');
        assert.equal(document.body.dataset.surfaceReady, 'ready');
        assert.equal(intents.length, 0);
        const nextRender = renderCompassRuntime(params(), {{payload: {{}}, source: 'runtime-json', warning: ''}});
        assert.equal(snapshot().outcome, 'loading');
        assert.equal(published.length, 1);
        resolveView({{payload: {{}}, normalized: {{warnings: []}}, state: actual, summaryState: actual, summaryEvents: []}});
        await nextRender;
        assert.equal(published.length, 2);
        """,
        query="?scope=B-999",
    )


def test_compass_unavailable_runtime_publishes_degraded_without_fabricated_selection() -> None:
    _run_compass_js(
        """
        await renderCompassRuntime(params(), {payload: null, source: 'none'});
        assert.equal(published.length, 1);
        assert.equal(published[0].outcome, 'degraded');
        assert.equal(published[0].rendered, null);
        assert.equal(published[0].requested.workstream, 'B-007');
        assert.match(document.getElementById('kpi-grid').innerHTML, /Runtime Unavailable/);
        assert.equal(document.body.dataset.surfaceReady, 'ready');
        assert.equal(intents.length, 0);
        """,
        query="?scope=B-007&window=24h",
    )


def test_compass_failed_render_does_not_publish_ready() -> None:
    _run_compass_js(
        _RENDER_SETUP
        + """
        renderRisks = () => { throw Error('risk rendering failed'); };
        const pending = renderCompassRuntime(params(), {payload: {}, source: 'runtime-json', warning: ''});
        resolveView({payload: {}, normalized: {warnings: []}, state: actual, summaryState: actual, summaryEvents: []});
        await assert.rejects(pending, /risk rendering failed/);
        assert.equal(published.length, 0);
        assert.equal(snapshot().outcome, 'loading');
        assert.equal(snapshot().rendered, null);
        assert.equal(document.body.dataset.surfaceReady, 'loading');
        """
    )
