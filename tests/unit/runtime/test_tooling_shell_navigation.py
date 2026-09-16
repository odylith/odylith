"""Characterize shell route ownership independently of native channel transport."""

import json
from pathlib import Path
import shutil
import subprocess

import pytest


SOURCE = (Path(__file__).resolve().parents[3] / "src/odylith/runtime/surfaces"
          / "templates/tooling_dashboard/navigation.js")

HARNESS = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const events = [], listeners = {}, bridges = {}, storage = new Map(), shown = [];
let href = 'file:///project/odylith/index.html' + SEARCH;
const location = {
  get href() {return href;}, get pathname() {return new URL(href).pathname;},
  get search() {return new URL(href).search;},
};
const window = {location,
  history: {
    pushState(_state, _title, url) {events.push(['push',url]); href = new URL(url,href).href;},
    replaceState(_state, _title, url) {events.push(['historyReplace',url]); href = new URL(url,href).href;},
  },
  addEventListener(name, fn) {(listeners[name] ||= new Set()).add(fn);},
  removeEventListener(name, fn) {listeners[name]?.delete(fn);},
  OdylithFrameBridge: {frame({frame,onActor,onSnapshot,onNavigate}) {
    let actor = null;
    const bridge = {
      active:false,
      bind() {
        this.active=true; events.push(['bind',frame.tab]);
        if (actor !== frame.actor) {actor = frame.actor; onActor?.(actor);}
      },
      revoke() {this.active=false; events.push(['revoke',frame.tab]);},
      dispose() {this.revoke();},
      snapshot(value) {if(this.active) onSnapshot(value);},
      navigate(value) {if(this.active) onNavigate(value);},
    };
    bridges[frame.tab] = bridge;
    return bridge;
  }},
};
const document = {readyState:'loading'};
const panes = {project:{}}, payload = {};
for (const tab of ['radar','atlas','compass','registry','casebook']) {
  const frame = {tab,actor:0,dataset:{},contentDocument:{URL:'about:blank'}, handlers:new Set(),
    contentWindow:{location:{replace(url) {events.push(['documentReplace',tab,url]);}}},
    addEventListener(name,fn) {assert.equal(name,'load'); this.handlers.add(fn);},
    removeEventListener(name,fn) {assert.equal(name,'load'); this.handlers.delete(fn);},
  };
  panes[tab] = frame; payload[tab + '_href'] = tab + '/' + tab + '.html?v=asset';
}
const sandbox = {window,document,URL,URLSearchParams,Set,Object,String};
vm.createContext(sandbox);
vm.runInContext(SOURCE_TEXT,sandbox);
const navigation = sandbox.createToolingShellNavigation({panes,payload,
  onState:state=>shown.push(JSON.parse(JSON.stringify(state))),
  localStorageRead:key=>storage.get(key), localStorageWrite:(key,value)=>storage.set(key,value),
});
function event(name, value={}) {for(const fn of listeners[name] || []) fn(value);}
function loaded(tab, opaque=true) {
  panes[tab].actor++;
  panes[tab].contentDocument = opaque ? null : {URL:'http://localhost/' + tab};
  for(const fn of panes[tab].handlers) fn();
}
function complete(tab,requested,rendered,outcome='ready') {
  bridges[tab].snapshot({requested:{tab,...requested},rendered:rendered===null?null:{tab,...rendered},outcome});
}
function topLoaded() {document.readyState='complete';event('load');}
function last() {return shown.at(-1);}
function replacements() {return events.filter(row=>row[0]==='documentReplace');}
navigation.start();
"""


CASES = {
    "history_filter_change_before_top_load_remains_pending": ("?tab=casebook&bug=CB-305&sort=oldest", r"""
      loaded('casebook');
      href='file:///project/odylith/index.html?tab=casebook&bug=CB-305&sort=priority'; event('popstate');
      complete('casebook',{bug:'CB-305',sort:'priority'},{bug:'CB-305',sort:'oldest'});
      assert.equal(replacements().length,0); assert.equal(last().sort,'priority');
      topLoaded();
      complete('casebook',{bug:'CB-305',sort:'priority'},{bug:'CB-305',sort:'oldest'});
      assert.equal(last().sort,'priority'); assert.equal(replacements().length,1);
      loaded('casebook'); complete('casebook',{bug:'CB-305',sort:'priority'},{bug:'CB-305',sort:'priority'});
      assert.equal(last().sort,'priority');
    """),
    "history_target_waits_for_in_flight_document_before_replacing": ("?tab=casebook&bug=CB-305&sort=oldest", r"""
      topLoaded(); assert.equal(replacements().length,1);
      href='file:///project/odylith/index.html?tab=casebook&bug=CB-305&sort=priority'; event('popstate');
      assert.equal(replacements().length,1);
      loaded('casebook');
      complete('casebook',{bug:'CB-305',sort:'oldest'},{bug:'CB-305',sort:'oldest'});
      assert.equal(last().sort,'priority'); assert.equal(replacements().length,2);
      loaded('casebook'); complete('casebook',{bug:'CB-305',sort:'priority'},{bug:'CB-305',sort:'priority'});
      assert.equal(last().sort,'priority'); assert.equal(replacements().length,2);
    """),
    "history_filter_change_does_not_readmit_original_request_echo": ("?tab=casebook&bug=CB-305&sort=oldest", r"""
      const original={bug:'CB-305',sort:'oldest'};
      topLoaded(); loaded('casebook'); complete('casebook',original,original);
      navigation.selectTab('project'); navigation.selectTab('casebook');
      complete('casebook',original,original);
      bridges.casebook.navigate({route:{bug:'CB-305',sort:'priority'},replaceDocument:false});
      complete('casebook',original,{bug:'CB-305',sort:'priority'});
      href='file:///project/odylith/index.html?tab=project'; event('popstate');
      const before = replacements().length;
      href='file:///project/odylith/index.html?tab=casebook&bug=CB-305&sort=oldest'; event('popstate');
      complete('casebook',original,{bug:'CB-305',sort:'priority'});
      assert.equal(last().sort,'oldest');
      assert.equal(replacements().length,before+1);
      loaded('casebook'); complete('casebook',original,original);
      assert.equal(last().sort,'oldest'); assert.equal(last().bug,'CB-305');
    """),
    "child_canonical_filters_do_not_reload_or_rename_selection": ("?tab=casebook&bug=CB-150&status=obsolete&severity=unknown", r"""
      const requested={bug:'CB-150',status:'obsolete',severity:'unknown'};
      topLoaded(); loaded('casebook'); complete('casebook',requested,null,'loading');
      complete('casebook',requested,{bug:'CB-150'});
      assert.equal(replacements().length,1);
      assert.equal(last().bug,'CB-150');
      assert.equal(new URL(href).searchParams.has('status'),false);
      assert.equal(new URL(href).searchParams.has('severity'),false);
    """),
    "unknown_record_survives_canonical_filter_removal": ("?tab=casebook&bug=missing&status=obsolete", r"""
      const requested={bug:'missing',status:'obsolete'};
      topLoaded(); loaded('casebook'); complete('casebook',requested,{bug:''},'empty');
      assert.equal(last().bug,'missing'); assert.equal(last().status,'');
      assert.equal(replacements().length,1);
      complete('casebook',requested,{bug:'CB-150'});
      assert.equal(last().bug,'missing');
    """),
    "atlas_keeps_diagram_while_child_clears_conflicting_filter": ("?tab=atlas&diagram=D-047&workstream=B-001", r"""
      const requested={diagram:'D-047',workstream:'B-001'};
      topLoaded(); loaded('atlas'); complete('atlas',requested,{diagram:'D-047'},'degraded');
      assert.equal(last().diagram,'D-047'); assert.equal(last().workstream,'');
      assert.equal(replacements().length,1);
      assert.equal(panes.atlas.dataset.navigationOutcome,'degraded');
      complete('atlas',requested,{diagram:'D-001'});
      assert.equal(last().diagram,'D-047');
    """),
    "radar_child_resolves_view_without_changing_workstream": ("?tab=radar&workstream=B-048&view=plan", r"""
      const requested={workstream:'B-048',view:'plan'};
      topLoaded(); loaded('radar'); complete('radar',requested,{workstream:'B-048',view:'spec'});
      assert.equal(last().workstream,'B-048'); assert.equal(last().view,'spec');
      assert.equal(replacements().length,1);
      bridges.radar.navigate({route:{workstream:'B-049'},replaceDocument:false});
      complete('radar',requested,{workstream:'B-048'});
      assert.equal(last().workstream,'B-049');
    """),
    "compass_child_canonicalizes_dates_without_changing_scope": ("?tab=compass&scope=B-142&window=24h&date=2020-01-01", r"""
      const requested={workstream:'B-142',window:'24h',date:'2020-01-01'};
      topLoaded(); loaded('compass'); complete('compass',requested,{workstream:'B-142',window:'48h',date:'live'});
      assert.equal(last().workstream,'B-142'); assert.equal(last().date,'live');
      assert.equal(last().window,'48h'); assert.equal(replacements().length,1);
      complete('compass',requested,{workstream:'B-001',window:'24h',date:'live'});
      assert.equal(last().workstream,'B-142'); assert.equal(last().window,'48h');
    """),
    "casebook_sort_remains_canonical_and_tab_local": ("?tab=casebook&sort=priority", r"""
      assert.equal(navigation.readState().sort,'priority');
      topLoaded(); loaded('casebook'); complete('casebook',{sort:'priority'},{bug:'CB-305',sort:'priority'});
      navigation.selectTab('project'); navigation.selectTab('casebook');
      complete('casebook',{sort:'priority'},{bug:'CB-305',sort:'priority'});
      assert.equal(last().sort,'priority'); assert.equal(last().bug,'CB-305');
      bridges.casebook.navigate({route:{bug:'CB-305',sort:'newest'},replaceDocument:false});
      complete('casebook',{sort:'priority'},{bug:'CB-305',sort:'newest'});
      assert.equal(new URL(href).searchParams.has('sort'),false);
    """),
    "default_after_native_load": ("?tab=casebook", r"""
      assert.equal(replacements().length,0); assert.equal(last().tab,'casebook');
      topLoaded(); assert.equal(replacements().length,1);
      loaded('casebook'); complete('casebook',{}, {bug:'CB-340'});
      assert.equal(last().bug,'CB-340'); assert.equal(replacements().length,1);
      assert.equal(new URL(href).searchParams.get('bug'),'CB-340');
    """),
    "restored_route_waits_for_top_load": ("?tab=radar&workstream=B-145", r"""
      loaded('radar'); complete('radar',{workstream:'B-005'},{workstream:'B-005'});
      assert.equal(replacements().length,0); assert.equal(last().workstream,'B-145');
      topLoaded(); complete('radar',{workstream:'B-005'},{workstream:'B-005'});
      assert.equal(replacements().length,1);
      assert.equal(new URL(replacements()[0][2]).searchParams.get('workstream'),'B-145');
      loaded('radar'); complete('radar',{workstream:'B-145'},{workstream:'B-145'});
      assert.equal(last().workstream,'B-145'); assert.equal(replacements().length,1);
    """),
    "in_place_user_intent": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},null,'loading');
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      assert.equal(last().bug,'CB-340'); assert.equal(replacements().length,1);
      complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      assert.equal(last().bug,'CB-340');
      complete('casebook',{bug:'CB-305'},{bug:'CB-340'});
      assert.equal(last().bug,'CB-340');
    """),
    "revoke_before_document_navigation": ("?tab=compass", r"""
      topLoaded(); loaded('compass'); complete('compass',{}, {window:'48h',date:'live'});
      bridges.compass.navigate({route:{window:'24h',date:'live'},replaceDocument:true});
      const index=events.findLastIndex(row=>row[0]==='documentReplace');
      assert.deepEqual(events[index-1],['revoke','compass']);
      complete('compass',{}, {window:'48h',date:'live'});
      assert.equal(last().window,'24h'); assert.equal(replacements().length,2);
    """),
    "unknown_and_degraded_do_not_invent_selection": ("?tab=registry&component=missing", r"""
      topLoaded(); loaded('registry'); complete('registry',{component:'missing'},null,'degraded');
      assert.equal(last().component,'missing'); assert.equal(panes.registry.dataset.navigationOutcome,'degraded');
      complete('registry',{component:'missing'},{component:''},'empty');
      assert.equal(last().component,'missing'); assert.equal(replacements().length,1);
      assert.equal(panes.registry.dataset.navigationOutcome,'empty');
    """),
    "history_replay_does_not_push": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      navigation.selectTab('radar'); loaded('radar'); complete('radar',{}, {workstream:'B-005'});
      const pushes=events.filter(row=>row[0]==='push').length;
      href='file:///project/odylith/index.html?tab=casebook&bug=CB-305'; event('popstate');
      complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      assert.equal(last().bug,'CB-305'); assert.equal(events.filter(row=>row[0]==='push').length,pushes);
      assert.equal(bridges.radar.active,false);
    """),
    "restored_current_selection_is_not_initial_url": ("?tab=radar&workstream=B-145", r"""
      loaded('radar',false); topLoaded();
      complete('radar',{workstream:'B-005'},{workstream:'B-145'});
      assert.equal(replacements().length,0); assert.equal(last().workstream,'B-145');
    """),
    "inactive_late_load_does_not_revive_navigation": ("?tab=radar&workstream=B-145", r"""
      topLoaded(); loaded('radar'); complete('radar',{workstream:'B-145'},{workstream:'B-145'});
      navigation.selectTab('project');
      const before = replacements().length;
      loaded('radar'); complete('radar',{workstream:'B-005'},{workstream:'B-005'});
      assert.equal(replacements().length,before);
      assert.equal(bridges.radar.active,false);
      assert.equal(last().tab,'project');
    """),
    "same_tab_preserves_pending_in_place_intent": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      complete('casebook',{bug:'CB-305'},null,'loading');
      const before = replacements().length;
      navigation.selectTab('casebook');
      complete('casebook',{bug:'CB-305'},null,'loading');
      assert.equal(replacements().length,before);
      complete('casebook',{bug:'CB-305'},{bug:'CB-340'});
      assert.equal(last().bug,'CB-340');
    """),
    "tab_return_preserves_pending_in_place_intent": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      complete('casebook',{bug:'CB-305'},null,'loading');
      const before = replacements().length;
      navigation.selectTab('project'); navigation.selectTab('casebook');
      complete('casebook',{bug:'CB-305'},null,'loading');
      assert.equal(replacements().length,before);
      complete('casebook',{bug:'CB-305'},{bug:'CB-340'});
      assert.equal(last().bug,'CB-340');
    """),
    "tab_return_does_not_retry_terminal_degraded_result": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      complete('casebook',{bug:'CB-305'},null,'degraded');
      const before = replacements().length;
      navigation.selectTab('project'); navigation.selectTab('casebook');
      complete('casebook',{bug:'CB-305'},null,'degraded');
      assert.equal(replacements().length,before);
      assert.equal(panes.casebook.dataset.navigationOutcome,'degraded');
      assert.equal(last().bug,'CB-340');
    """),
    "native_load_invalidates_previous_document_admission": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      navigation.selectTab('project'); loaded('casebook');
      const before = replacements().length;
      navigation.selectTab('casebook');
      complete('casebook',{bug:'CB-305'},null,'loading');
      assert.equal(replacements().length,before+1);
      assert.equal(bridges.casebook.active,false);
      loaded('casebook'); complete('casebook',{bug:'CB-340'},{bug:'CB-340'});
      assert.equal(last().bug,'CB-340');
    """),
    "history_target_change_requires_new_admission": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      complete('casebook',{bug:'CB-305'},{bug:'CB-340'});
      const before = replacements().length;
      href='file:///project/odylith/index.html?tab=casebook&bug=CB-339'; event('popstate');
      complete('casebook',{bug:'CB-305'},{bug:'CB-340'});
      assert.equal(replacements().length,before+1);
      assert.equal(last().bug,'CB-339');
    """),
    "new_actor_before_load_cannot_inherit_in_place_admission": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-340'},replaceDocument:false});
      complete('casebook',{bug:'CB-305'},null,'degraded');
      const before = replacements().length;
      panes.casebook.actor++;
      navigation.selectTab('casebook');
      complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      bridges.casebook.navigate({route:{bug:'CB-999'},replaceDocument:false});
      assert.equal(last().bug,'CB-340');
      assert.equal(replacements().length,before+1);
      assert.equal(bridges.casebook.active,false);
    """),
    "dispose_and_bfcache_restore": ("?tab=casebook&bug=CB-305", r"""
      topLoaded(); loaded('casebook'); complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      event('pagehide'); assert.equal(bridges.casebook.active,false);
      event('pageshow',{persisted:true}); assert.equal(bridges.casebook.active,true);
      complete('casebook',{bug:'CB-305'},{bug:'CB-305'});
      navigation.dispose(); assert.equal(bridges.casebook.active,false);
      assert.ok(Object.values(listeners).every(group=>group.size===0));
      assert.ok(Object.values(panes).filter(p=>p.handlers).every(p=>p.handlers.size===0));
    """),
}


@pytest.mark.parametrize("name", CASES)
def test_shell_navigation_ownership(name: str) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node is required for shell ownership unit controls")
    search, assertions = CASES[name]
    script = ("const SEARCH=" + json.dumps(search) + "; const SOURCE_TEXT="
              + json.dumps(SOURCE.read_text()) + ";\n" + HARNESS + assertions)
    result = subprocess.run([node, "-e", script], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
