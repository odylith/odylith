"""Provider-free execution proof for Atlas's route and asset-completion owners."""

import json
import re
import shutil
import subprocess

import pytest

from odylith.runtime.surfaces import atlas_viewer_asset_runtime as viewer
from odylith.runtime.surfaces import governance_frame_bridge
from odylith.runtime.surfaces import render_mermaid_catalog as catalog


def _html() -> str:
    return catalog._render_html(
        diagrams=[], stats={"total": 0, "fresh": 0, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-14T00:00:00Z",
        brand_head_html="", tooling_base_href="../index.html",
    )


def _run(script: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for Atlas owner execution proof")
    result = subprocess.run(
        [node, "--input-type=commonjs"], input='const assert = require("node:assert/strict");\n' + script,
        capture_output=True, text=True, timeout=20, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


_ELEMENT = """
function element() {
  return {
    hidden: false, dataset: {}, children: [], attributes: {}, textContent: "",
    classList: {values: new Set(), add(value) { this.values.add(value); },
      remove(value) { this.values.delete(value); },
      toggle(value, enabled) { if (enabled) this.values.add(value); else this.values.delete(value); },
      contains(value) { return this.values.has(value); }},
    setAttribute(name, value) { this.attributes[name] = value; },
    removeAttribute(name) { delete this[name]; }, addEventListener() {},
    appendChild(child) { this.children.push(child); },
    removeChild(child) { this.children.splice(this.children.indexOf(child), 1); },
    get firstChild() { return this.children[0] || null; },
    querySelectorAll() { return this.children; },
  };
}
"""


def test_atlas_embeds_only_the_shared_document_bridge_before_the_child() -> None:
    html = _html()
    assert html.index(governance_frame_bridge.runtime_js()) < html.index("const payload =")
    assert html.count("window.OdylithFrameBridge.surface({") == 1
    assert "odylith-atlas-navigate" not in html
    assert "window.parent.postMessage" not in html
    assert "replaceDocument: false" in html
    scripts = re.findall(r"<script>(.*?)</script>", html, re.DOTALL)
    assert len(scripts) == 2
    _run("\n".join(f"new Function({json.dumps(script)});" for script in scripts))


_VIEWER_SETUP = """
const nodes = new Map();
const document = {createElement: element, getElementById(id) {
  if (!nodes.has(id)) nodes.set(id, element());
  return nodes.get(id);
}};
const emptyEl = element();
emptyEl.querySelector = id => document.getElementById(id);
const mainEl = element(); mainEl.children = [element(), emptyEl];
mainEl.querySelector = () => emptyEl;
const viewerShellEl = element();
viewerShellEl.before = node => mainEl.children.push(node);
const stageEl = element(); stageEl.closest = () => viewerShellEl;
const imageEl = element();
const outcomes = [], effects = [];
const viewport = {clear() { effects.push("clear"); }, setDiagram() {}, imageLoaded() { effects.push("loaded"); }};
const instance = createAtlasViewer({mainEl, stageEl, imageEl, listEl: element(), viewport,
  catalogCount: 2, projectHref: "../index.html?tab=project", onOutcome: value => outcomes.push(value)});
const a = {source_svg_href: "a.svg", source_png_href: "a.png"};
const b = {source_svg_href: "b.svg", source_png_href: ""};
"""


def test_asset_outcomes_keep_fallback_and_reject_retired_callbacks() -> None:
    _run(_ELEMENT + viewer.VIEWER_RUNTIME_JS + _VIEWER_SETUP + """
instance.show(a);
assert.equal(outcomes.at(-1), "loading");
const oldLoad = imageEl.onload, oldError = imageEl.onerror;
imageEl.onerror();
assert.equal(imageEl.src, "a.png");
assert.equal(outcomes.at(-1), "loading");
imageEl.onload();
assert.equal(outcomes.at(-1), "ready");
assert.equal(imageEl.hidden, false);
instance.show(a);
assert.equal(outcomes.at(-1), "ready");
instance.show(b);
imageEl.onerror();
assert.equal(outcomes.at(-1), "degraded");
assert.equal(imageEl.hidden, true);
instance.show(b);
assert.equal(outcomes.at(-1), "loading", "reselecting an unavailable preview retains its retry path");
imageEl.onerror();
assert.equal(outcomes.at(-1), "degraded");
instance.show(a);
const before = outcomes.length;
oldLoad(); oldError();
assert.equal(outcomes.length, before, "A→B→A must not revive A's retired work");
assert.equal(imageEl.src, "a.svg");
imageEl.onerror(); imageEl.onerror();
assert.equal(outcomes.at(-1), "degraded");
const retiredLoad = imageEl.onload, retiredError = imageEl.onerror;
instance.clear();
assert.equal(outcomes.at(-1), "empty");
assert.equal(mainEl.dataset.selectionEmpty, "true");
const cleared = outcomes.length;
retiredLoad(); retiredError();
assert.equal(outcomes.length, cleared);
assert.equal(imageEl.hidden, true);
""")


@pytest.mark.parametrize("png_fallback", [False, True])
def test_selection_warning_degrades_loaded_preview_without_breaking_asset_recovery(png_fallback: bool) -> None:
    _run(_ELEMENT + viewer.VIEWER_RUNTIME_JS + _VIEWER_SETUP + f"""
instance.setSelectionWarning('Diagram D-001 is not linked to workstream B-002. Showing the diagram with All Workstreams.');
const warning = mainEl.children.find(node => node.id === 'viewerSelectionWarning');
assert.equal(warning.hidden, false);
assert.equal(warning.classList.contains('visible'), true);
assert.equal(warning.attributes.role, 'status');
assert.match(warning.textContent, /D-001.*B-002/);
assert.equal(outcomes.length, 0, 'a warning is not a render-completion event');
instance.show(a);
assert.equal(outcomes.at(-1), 'loading');
if ({str(png_fallback).lower()}) imageEl.onerror();
imageEl.onload();
assert.equal(outcomes.at(-1), 'degraded');
assert.equal(imageEl.hidden, false, 'the useful diagram remains visible');
const completedLoad = imageEl.onload;
instance.show(a);
assert.equal(imageEl.onload, completedLoad, 'selection degradation must not retry a loaded asset');
assert.equal(outcomes.at(-1), 'degraded');
instance.setSelectionWarning('');
assert.equal(warning.hidden, true);
assert.equal(warning.classList.contains('visible'), false);
instance.show(a);
assert.equal(outcomes.at(-1), 'ready');
assert.equal(imageEl.onload, completedLoad);
instance.setSelectionWarning('A selection conflict remains.');
instance.show(b);
imageEl.onerror();
assert.equal(outcomes.at(-1), 'degraded');
instance.clear();
assert.equal(outcomes.at(-1), 'empty');
assert.equal(warning.hidden, true);
assert.equal(warning.textContent, '');
""")


def _route_owner(query: str = "?v=cache&workstream=B-001&diagram=d001") -> str:
    html = _html()
    functions = (
        "canonicalizeDiagramId", "normalizeWorkstreamId", "normalizedWorkstreamList",
        "ownerWorkstreamsForDiagram", "activeWorkstreamsForDiagram", "historicalWorkstreamsForDiagram",
        "relatedWorkstreamsForDiagram", "allWorkstreamReferencesForDiagram", "diagramMatchesWorkstream",
        "normalizeSelectedDiagramWorkstreamFilter", "normalizeSearchToken", "diagramSearchTokens",
        "diagramMatchesExactSearchToken", "canonicalizeSortToken", "diagramSequence", "compareText",
        "firstNonZero", "sortDiagrams", "currentAtlasNavigationState", "syncAtlasNavigation",
        "clamp", "setActive", "renderList", "applyFilters", "diagramButtonTooltip", "clearNode",
    )
    declarations = []
    for name in functions:
        match = re.search(rf"^    function {name}\(", html, re.MULTILINE)
        assert match is not None, name
        start = match.start()
        first_line = html[start:html.index("\n", start)]
        end = start + len(first_line) if first_line.rstrip().endswith("}") else html.index("\n    }", start) + 6
        declarations.append(html[start:end])
    constants = re.findall(
        r"^    const (?:WORKSTREAM_ID_RE|DIAGRAM_ID_RE|DIAGRAM_COMPACT_RE|SORT_DEFAULT|SORT_TOKENS) = .*;$",
        html, flags=re.MULTILINE,
    )
    boot_start = re.search(r"^    const params = new URLSearchParams", html, re.MULTILINE)
    assert boot_start is not None
    boot = html[boot_start.start():html.index("    const viewer = createAtlasViewer")]
    return _ELEMENT + "\n".join(constants + declarations) + """
const events = [];
const document = {createElement: element};
const window = {
  location: {search: QUERY, pathname: "/atlas.html"},
  history: {replaceState(_state, _unused, href) {
    events.push("url"); window.location.search = new URL(href, "http://local").search;
  }},
  OdylithFrameBridge: {surface({readSnapshot}) {
    return {readSnapshot, publish() { events.push("publish"); },
      navigate(request) { events.push({navigate: request}); }};
  }},
};
const allDiagrams = [
  {diagram_id: "D-001", title: "One", related_workstreams: ["B-001"]},
  {diagram_id: "D-002", title: "Two", related_workstreams: ["B-002"]},
];
let activeList = allDiagrams.slice(), activeIndex = 0, selectedDiagramId = "D-001";
let activeDiagram = null, workstreamFilter = "B-001", kindFilter = "all", freshnessFilter = "all", sortFilter = "newest";
const listEl = element(), workstreamFilterEl = element(), searchEl = {value: ""};
const diagramTitleLookup = {};
let selectionWarning = '';
const viewer = {setResults() { events.push("results"); },
  setSelectionWarning(message) { selectionWarning = message; }};
function updateStats() { events.push("stats"); }
function clearActiveDiagram() { activeDiagram = null; atlasOutcome = "empty"; events.push("empty"); }
function applyMeta(diagram) { activeDiagram = diagram; atlasOutcome = "loading"; events.push("render"); }
""".replace("QUERY", json.dumps(query)) + boot


def test_requested_route_is_immutable_and_user_intent_precedes_render() -> None:
    _run(_route_owner() + """
assert.deepEqual(atlasBridge.readSnapshot(), {
  requested: {tab: "atlas", workstream: "B-001", diagram: "D-001"},
  rendered: {tab: "atlas", workstream: "B-001", diagram: ""}, outcome: "loading",
});
applyFilters();
assert.equal(events.some(event => event.navigate), false, "boot default is not user intent");
events.length = 0;
workstreamFilter = "B-002";
applyFilters({normalizeWorkstreamFilter: false, userIntent: true});
assert.deepEqual(events[0], {navigate: {
  route: {tab: "atlas", workstream: "B-002", diagram: "D-002"}, replaceDocument: false,
}});
assert.equal(activeDiagram.diagram_id, "D-002");
assert.deepEqual(atlasBridge.readSnapshot().requested, {tab: "atlas", workstream: "B-001", diagram: "D-001"});
events.length = 0;
activeList = allDiagrams.slice();
setActive(0, true);
assert.equal(events[0].navigate.route.diagram, "D-001");
assert.equal(events[1], "render");
assert.equal(new URLSearchParams(window.location.search).get("v"), "cache");
""")


def test_empty_catalog_and_mismatched_filter_retain_truthful_requested_route() -> None:
    _run(_route_owner("?v=cache&workstream=B-002&diagram=d001") + """
workstreamFilter = "B-002";
applyFilters();
assert.equal(workstreamFilter, "all", "an explicit diagram keeps the established mismatch normalization");
assert.equal(activeDiagram.diagram_id, "D-001");
assert.equal(atlasBridge.readSnapshot().rendered.workstream, "");
assert.equal(atlasBridge.readSnapshot().requested.workstream, "B-002");
assert.match(selectionWarning, /D-001.*B-002/);
assert.equal(events.some(event => event.navigate), false);
allDiagrams.length = 0;
events.length = 0;
applyFilters();
assert.equal(activeDiagram, null);
assert.equal(atlasBridge.readSnapshot().outcome, "empty");
assert.equal(atlasBridge.readSnapshot().rendered.diagram, "");
assert.equal(atlasBridge.readSnapshot().requested.diagram, "D-001");
assert.equal(events.some(event => event.navigate), false);
""")


def test_valid_workstream_and_explicit_diagram_selection_clear_no_unrelated_state() -> None:
    _run(_route_owner() + """
applyFilters();
assert.equal(selectionWarning, '', 'a matching explicit workstream needs no fallback warning');
workstreamFilter = 'B-002';
applyFilters();
assert.match(selectionWarning, /D-001.*B-002/);
const requested = atlasBridge.readSnapshot().requested;
events.length = 0;
setActive(activeIndex, true);
assert.equal(selectionWarning, '', 'the user explicitly chose the displayed diagram');
assert.equal(events[0].navigate.route.diagram, 'D-001');
assert.equal(events[0].navigate.route.workstream, '');
assert.deepEqual(atlasBridge.readSnapshot().requested, requested);
assert.equal(new URLSearchParams(window.location.search).get('v'), 'cache');
""")


def test_workstream_user_change_clears_old_warning_but_retains_new_fallback_warning() -> None:
    html = _html()
    start = html.index('    workstreamFilterEl.addEventListener("change",')
    handler = html[start:html.index('\n    });', start) + len('\n    });')]
    _run(_route_owner() + """
let changeWorkstream;
workstreamFilterEl.addEventListener = (_type, callback) => { changeWorkstream = callback; };
""" + handler + """
workstreamFilter = 'B-002';
applyFilters();
assert.notEqual(selectionWarning, '');
workstreamFilterEl.value = 'B-001';
events.length = 0;
changeWorkstream();
assert.equal(selectionWarning, '');
assert.equal(workstreamFilter, 'B-001');
assert.equal(events[0].navigate.route.workstream, 'B-001');
workstreamFilterEl.value = 'B-999';
events.length = 0;
changeWorkstream();
assert.equal(workstreamFilter, 'all');
assert.equal(activeDiagram.diagram_id, 'D-001');
assert.match(selectionWarning, /D-001.*B-999/);
assert.equal(events[0].navigate.route.workstream, '');
""")


@pytest.mark.parametrize("requested", ["D-999", "not-a-diagram"])
def test_unknown_explicit_diagram_does_not_become_default_success(requested: str) -> None:
    _run(_route_owner() + f'selectedDiagramId = {requested!r};\n' + """
applyFilters();
assert.equal(activeDiagram, null);
assert.equal(atlasBridge.readSnapshot().outcome, "empty");
assert.equal(events.includes("render"), false);
assert.equal(listEl.children.length, 1, "matching diagrams remain available for an explicit choice");
events.length = 0;
setActive(0, true);
assert.equal(events[0].navigate.route.diagram, "D-001");
assert.equal(activeDiagram.diagram_id, "D-001");
""")
