"""Selection owners publish only their current, actually rendered outcome."""

import shutil
import subprocess
import json
import re

import pytest

from odylith.runtime.surfaces import (
    backlog_detail_pages, backlog_selection_ui, casebook_selection_ui,
    registry_selection_ui, render_backlog_ui_html_runtime,
    render_casebook_dashboard, render_registry_dashboard,
)


def _run_js(source: str, body: str) -> None:
    node = shutil.which("node")
    assert node, "Node is required for selection-owner controls"
    program = (
        source + "\nlet completed = false;\n"
        "process.on('beforeExit', () => { if (!completed) { console.error('control did not complete'); process.exitCode = 1; } });\n"
        "(async () => {\n" + body + "\n})().then(() => { completed = true; }).catch(error => { completed = true; console.error(error); process.exitCode = 1; });"
    )
    result = subprocess.run(
        [node, "-e", program],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("surface", ["radar", "registry"])
def test_selection_completion_rejects_late_detail_and_reports_empty_and_degraded(surface: str) -> None:
    radar = surface == "radar"
    source = (backlog_selection_ui if radar else registry_selection_ui).runtime_js()
    factory = "createBacklogSelection" if radar else "createRegistrySelection"
    key = "idea_id" if radar else "component_id"
    _run_js(source, f"""
      const assert = require('node:assert/strict');
      const detail = {{innerHTML:'', hidden:false, dataset:{{}}}};
      const empty = {{innerHTML:'', hidden:false, setAttribute(){{}}}};
      const completions = [], renders = [], pending = new Map();
      const select = {factory}({{
        detail, empty, timeline:{{innerHTML:''}}, timelineCount:{{textContent:''}}, sourceCount:2,
        loadDetail:id => new Promise(resolve => pending.set(id, resolve)),
        renderDetail:row => renders.push(row.{key}), renderTimeline(){{}},
        onOutcome:value => completions.push(value),
      }});
      const rows = [{{{key}:'a'}}, {{{key}:'b'}}];
      const older = select('a', rows);
      const newer = select('b', rows);
      assert.equal(completions.at(-1).outcome, 'loading');
      pending.get('b')({{{key}:'b'}}); await newer;
      assert.deepEqual(completions.at(-1), {{id:'b', outcome:'ready'}});
      const count = completions.length;
      pending.get('a')({{{key}:'a'}}); await older;
      assert.equal(completions.length, count);
      assert.deepEqual(renders, ['b']);
      const abandoned = select('a', rows);
      await select('unknown', rows);
      assert.deepEqual(completions.at(-1), {{id:'', outcome:'empty'}});
      const emptyCount = completions.length;
      pending.get('a')({{{key}:'a'}}); await abandoned;
      assert.equal(completions.length, emptyCount);
      const missing = select('b', rows); pending.get('b')(null); await missing;
      assert.deepEqual(completions.at(-1), {{id:'b', outcome:'degraded'}});
      assert.match(detail.innerHTML, /unavailable/i);
    """)


def test_casebook_selection_owns_empty_cancellation_and_missing_detail() -> None:
    _run_js(casebook_selection_ui.runtime_js(), """
      const assert = require('node:assert/strict');
      const detail = {innerHTML:''}, results = [], renders = [], pending = new Map();
      const select = createCasebookSelection({detail,
        loadDetail:id => new Promise((resolve, reject) => pending.set(id, {resolve, reject})),
        renderDetail:row => renders.push(row.bug_route), onOutcome:result => results.push(result),
      });
      const older = select({bug_route:'a'});
      const newer = select({bug_route:'b'});
      pending.get('b').resolve({bug_route:'b'}); await newer;
      assert.deepEqual(results.at(-1), {id:'b', outcome:'ready'});
      const count = results.length;
      pending.get('a').resolve({bug_route:'a'}); await older;
      assert.equal(results.length, count); assert.deepEqual(renders, ['b']);
      const abandoned = select({bug_route:'a'});
      await select(null, '<p>No matching bugs</p>');
      pending.get('a').resolve({bug_route:'a'}); await abandoned;
      assert.equal(detail.innerHTML, '<p>No matching bugs</p>');
      assert.deepEqual(results.at(-1), {id:'', outcome:'empty'});
      const failed = select({bug_route:'b'});
      pending.get('b').reject(new Error('missing shard')); await failed;
      assert.deepEqual(results.at(-1), {id:'b', outcome:'degraded'});
      assert.match(detail.innerHTML, /unavailable/);
    """)


@pytest.mark.parametrize("renderer", [
    render_backlog_ui_html_runtime, render_casebook_dashboard, render_registry_dashboard,
])
def test_composed_record_surfaces_use_bridge_and_parse(renderer) -> None:  # noqa: ANN001
    html = renderer._render_html(payload={})
    scripts = [body for attributes, body in re.findall(r"<script([^>]*)>(.*?)</script>", html, re.S)
               if 'application/json' not in attributes]
    assert html.count("function surface({readSnapshot})") == 1
    assert "__GOVERNANCE_FRAME_BRIDGE__" not in html
    for legacy in ("odylith-radar-navigate", "odylith-casebook-navigate", "odylith-registry-navigate"):
        assert legacy not in html
    assert html.index("window.OdylithFrameBridge =") < html.index("OdylithFrameBridge.surface(")
    result = subprocess.run([shutil.which("node"), "--check"], input="\n".join(scripts), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("mode", ["empty", "ready", "script-failure", "missing-runtime", "render-failure"])
def test_radar_document_completion_waits_for_actual_mermaid_and_preserves_source(mode: str) -> None:
    _run_js("", f"""
      const assert = require('node:assert/strict');
      const mode = {json.dumps(mode)}, notices = [], original = 'graph TD; A-->B';
      let script, finishRender;
      const node = {{textContent:original, before:notice => notices.push(notice)}};
      const document = {{
        querySelectorAll:() => mode === 'empty' ? [] : [node],
        createElement:() => ({{setAttribute(){{}}}}), head:{{appendChild:value => {{script=value;}}}},
      }};
      const window = {{mermaid: mode === 'missing-runtime' ? null : {{
        initialize:options => assert.equal(options.securityLevel, 'strict'),
        run:() => {{node.textContent='render in progress'; return mode === 'render-failure'
          ? Promise.reject(new Error('bad diagram')) : new Promise(resolve => {{finishRender=resolve;}});}},
      }}}};
      eval({json.dumps(backlog_detail_pages._document_completion_js())});
      let completed = false;
      window.OdylithRadarDocumentCompletion.then(() => {{completed=true;}});
      if (mode !== 'empty') {{
        assert.equal(completed, false);
        if (mode === 'script-failure') script.onerror(); else script.onload();
        await Promise.resolve(); await Promise.resolve();
        if (mode === 'ready') {{assert.equal(completed,false); finishRender();}}
      }}
      const outcome = await window.OdylithRadarDocumentCompletion;
      assert.equal(outcome, ['empty','ready'].includes(mode) ? 'ready' : 'degraded');
      if (outcome === 'degraded') {{assert.equal(node.textContent,original); assert.equal(notices.length,1);}}
    """)


def test_registry_explicit_unknown_does_not_select_default() -> None:
    html = render_registry_dashboard._render_html(payload={})
    source = html.split("    function selectDefault(", 1)[1].split("    function registryListItemHeight", 1)[0]
    _run_js("function selectDefault(" + source, """
      const assert = require('node:assert/strict');
      const rows = [{component_id:'known'}];
      assert.equal(selectDefault(rows,''),'known');
      assert.equal(selectDefault(rows,'KNOWN'),'known');
      assert.equal(selectDefault(rows,'unknown'),'');
    """)


def test_casebook_explicit_unknown_reaches_empty_owner_without_defaulting() -> None:
    html = render_casebook_dashboard._render_html(payload={})
    source = html.split("    function renderList(state, rows)", 1)[1].split("    function render()", 1)[0]
    _run_js("", f"""
      const assert = require('node:assert/strict');
      const rows = [{{bug_route:'known'}}], bugSummaries = rows, selected = [], writes = [];
      const bugList = {{querySelectorAll:() => []}}, listMeta = {{}};
      const resolveBugRoute = (items, id) => items.find(row => row.bug_route === id)?.bug_route || '';
      const casebookListPresentation = ({{rows}}) => ({{listHtml:'list', meta:'', detailHtml:rows.length ? null : 'empty'}});
      const renderSelectedBug = (row, empty) => selected.push({{row, empty}});
      const writeState = state => writes.push(state);
      const escapeHtml = value => value, displayTokenLabel = value => value;
      const casebookDataSource = {{prefetch(){{}}}};
      eval({json.dumps('function renderList(state, rows)' + source)});
      renderList({{bug:'unknown'}}, rows);
      assert.equal(selected.at(-1).row, undefined); assert.match(selected.at(-1).empty, /unavailable/);
      assert.deepEqual(writes, []);
      renderList({{bug:''}}, rows); assert.equal(selected.at(-1).row.bug_route,'known');
      renderList({{bug:'known'}}, []); assert.equal(selected.at(-1).row,null);
    """)


def test_casebook_request_echo_precedes_data_backed_filter_resolution() -> None:
    html = render_casebook_dashboard._render_html(payload={})
    spans = (
        ("    function canonicalizeBugToken(", "    function displayTokenLabel("),
        ("    function canonicalizeSortToken(", "    function normalizeSearchToken("),
        ("    function readRequestedState(", "    let frameSnapshot ="),
    )
    source = "\n".join(start + html.split(start, 1)[1].split(end, 1)[0] for start, end in spans)
    _run_js("", f"""
      const assert = require('node:assert/strict');
      const DATA = {{filters:{{severity_tokens:['p2'],status_tokens:['open']}}}};
      const SORT_DEFAULT='newest', SORT_TOKENS=new Set(['newest','priority']);
      const window={{location:{{search:'?bug=CB-150&severity=unknown&status=obsolete'}}}};
      {source}
      assert.deepEqual(requestedRoute, {{tab:'casebook',bug:'CB-150',severity:'unknown',status:'obsolete',sort:''}});
      assert.deepEqual(readState(), {{bug:'CB-150',severity:'',status:'',sort:'newest'}});
      window.location.search='?bug=CB-150&severity=P2&status=OPEN&sort=priority';
      assert.deepEqual(readState(), {{bug:'CB-150',severity:'p2',status:'open',sort:'priority'}});
      assert.equal(requestedRoute.status,'obsolete');
    """)


def test_casebook_user_intent_precedes_local_url_write_but_default_is_not_intent() -> None:
    html = render_casebook_dashboard._render_html(payload={})
    source = html.split("    function writeState(", 1)[1].split("    function fillSelect(", 1)[0]
    _run_js("", f"""
      const assert = require('node:assert/strict'), events = [];
      const frameBridge = {{navigate:request => {{events.push(['intent',request]); return false;}}}};
      const window = {{location:{{pathname:'/casebook.html',search:'?v=cache'}},
        history:{{replaceState:(_state,_title,url) => events.push(['write',url])}}}};
      const SORT_DEFAULT = 'newest', canonicalizeSortToken = value => value || SORT_DEFAULT;
      eval({json.dumps('function writeState(' + source)});
      const state = {{bug:'known',severity:'',status:'',sort:'newest'}};
      writeState(state,true);
      assert.deepEqual(events.map(row => row[0]), ['intent','write']);
      assert.deepEqual(events[0][1], {{route:{{tab:'casebook',...state}},replaceDocument:false}});
      events.length = 0; writeState(state); assert.deepEqual(events.map(row => row[0]), ['write']);
    """)


def test_registry_user_intent_precedes_local_write_and_render() -> None:
    html = render_registry_dashboard._render_html(payload={})
    source = html.split("    function applyState(", 1)[1].split('    searchEl.addEventListener', 1)[0]
    _run_js("", f"""
      const assert = require('node:assert/strict'), events = [];
      const frameBridge = {{navigate:request => events.push(['intent',request])}};
      const writeState = id => events.push(['write',id]);
      const renderFilterControls = () => events.push(['render']);
      const filteredComponents = () => [], renderKpis = () => {{}}, selectDefault = (_rows,id) => id;
      const renderList = () => {{}}, renderSelectedComponent = () => {{}};
      eval({json.dumps('function applyState(' + source)});
      applyState('known',{{push:true}});
      assert.deepEqual(events.map(row => row[0]),['intent','write','render']);
      assert.deepEqual(events[0][1],{{route:{{tab:'registry',component:'known'}},replaceDocument:false}});
    """)


def test_radar_user_intent_precedes_in_place_selection() -> None:
    html = render_backlog_ui_html_runtime._render_html(payload={})
    source = html.split("    function selectIdea(", 1)[1].split("    function escapeHtml(", 1)[0]
    _run_js("", f"""
      const assert = require('node:assert/strict'), events = [], state = {{selectedIdeaId:'old'}};
      const allIdeaIds = new Set(['known']), canonicalizeIdeaId = id => id;
      const frameBridge = {{navigate:request => {{assert.equal(state.selectedIdeaId,'old'); events.push(request);}}}};
      const revealIdeaSelection = () => {{}};
      eval({json.dumps('function selectIdea(' + source)});
      assert.equal(selectIdea('unknown',{{userIntent:true}}),false); assert.equal(events.length,0);
      assert.equal(selectIdea('known',{{userIntent:true}}),true);
      assert.deepEqual(events,[{{route:{{tab:'radar',workstream:'known',view:''}},replaceDocument:false}}]);
      assert.equal(state.selectedIdeaId,'known');
    """)
