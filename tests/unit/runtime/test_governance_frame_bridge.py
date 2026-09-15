"""Native channel custody across HTTP/file documents, navigation gaps, and disposal."""

from __future__ import annotations

import json
import os
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlencode, urlsplit

import pytest
from playwright.sync_api import sync_playwright

from odylith.runtime.surfaces import governance_frame_bridge as bridge


OFFER = "odylith.frame-bridge.offer.v1"
PARENT = r"""<!doctype html><meta charset="utf-8"><link rel="icon" href="data:,">
<title>Frame transport owner</title><iframe id="child" title="Child"></iframe>
<script>__RUNTIME__</script><script>
const options = new URLSearchParams(location.search);
const childURL = options.get('child');
const childElement = document.getElementById('child');
window.evidence = {snapshots: [], navigations: [], actors: [], callbacks: [], delivered: [], receipts: [], barriers: [], closes: [], loads: 0};
window.channels = [];
const NativeChannel = MessageChannel;
window.MessageChannel = function () {
  const channel = new NativeChannel();
  const index = channels.length;
  channels.push(channel);
  const start = channel.port1.start.bind(channel.port1);
  const close = channel.port1.close.bind(channel.port1);
  channel.port1.addEventListener('message', event => {
    evidence.delivered.push({binding: index, data: event.data});
    if (event.data.kind === 'snapshot') evidence.unguardedSnapshot = event.data.snapshot;
    if (event.data.probe === 'barrier-reply') evidence.barriers.push(event.data.value);
  });
  if (index === 0 && options.get('hold') === '1') {
    channel.port1.start = () => {};
    window.startHeldQueue = start;
  }
  channel.port1.close = () => {
    evidence.closes.push(index);
    if (!(index === 0 && options.get('retain') === '1')) close();
  };
  return channel;
};
window.owner = OdylithFrameBridge.frame({
  frame: childElement,
  onActor(actor) {
    evidence.actors.push(actor);
    evidence.callbacks.push({kind: 'actor', actor});
    evidence.admitted = false;
    const action = options.get('actorAction');
    if (action) owner[action]();
  },
  onSnapshot(snapshot) {
    evidence.callbacks.push({kind: 'snapshot', admitted: evidence.admitted});
    evidence.snapshots.push(snapshot); evidence.state = snapshot;
  },
  onNavigate(route) { evidence.callbacks.push({kind: 'navigate'}); evidence.navigations.push(route); }
});
window.addEventListener('message', event => {
  if (event.source === childElement.contentWindow && event.data && event.data.probe)
    evidence.receipts.push(event.data);
});
childElement.addEventListener('load', () => {
  evidence.loads++;
  if (options.get('manual') !== '1') owner.bind();
});
window.replaceChild = revoke => {
  if (revoke) owner.revoke();
  childElement.contentWindow.location.replace(childURL);
};
window.probeChild = data => childElement.contentWindow.postMessage(data, '*');
window.barrier = value => channels[channels.length - 1].port1.postMessage({probe: 'barrier', value});
childElement.src = options.get('blank') === '1' ? 'about:blank' : childURL;
</script>"""

CHILD = r"""<!doctype html><meta charset="utf-8"><link rel="icon" href="data:,">
<title>Surface transport owner</title><button id="user">User selection</button>
<script>__RUNTIME__</script><script>
window.documentId = crypto.randomUUID();
window.snapshot = {documentId, requested: {route: '?default'}, rendered: {route: '?default'}, outcome: 'ready'};
window.reads = 0;
window.childEvidence = {offers: 0, navigated: []};
window.surface = OdylithFrameBridge.surface({readSnapshot() { reads++; return snapshot; }});
window.publishValue = value => { snapshot = value; return surface.publish(); };
document.getElementById('user').onclick = () => publishValue({documentId, selection: 'user', outcome: 'ready'});
function receipt(probe) { parent.postMessage({probe, documentId}, '*'); }
window.addEventListener('message', event => {
  if (event.source !== parent) return;
  if (event.data && event.data.type === 'odylith.frame-bridge.offer.v1' && event.ports.length === 1) {
    childEvidence.offers++;
    const port = event.ports[0];
    window.diagnosticPort = port;
    port.addEventListener('message', message => {
      if (message.data.probe === 'barrier') port.postMessage({probe: 'barrier-reply', value: message.data.value});
    });
    port.start();
    receipt('offered');
  } else if (event.data && event.data.probe === 'during-navigation') {
    publishValue({documentId, selection: 'old-during-navigation'});
    surface.navigate({documentId, route: 'old-during-navigation'});
    receipt('sent-during-navigation');
  }
});
if (new URLSearchParams(location.search).get('pending') === '1') {
  childEvidence.navigated.push(surface.navigate({documentId, route: 'superseded'}));
  childEvidence.navigated.push(surface.navigate({documentId, route: 'latest'}));
}
const loadGate = new URLSearchParams(location.search).get('loadGate');
if (loadGate) {
  const image = document.createElement('img');
  image.src = loadGate;
  document.body.append(image);
}
</script>"""


class _Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/gate.svg":
            self.server.gate_waiting.set()
            if not self.server.gate_release.wait(8):
                self.send_error(503)
                return
            body = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>'
            self.send_response(200)
            self.send_header("Content-Type", "image/svg+xml")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path not in {"/parent.html", "/child.html"}:
            self.send_error(404)
            return
        if path == "/child.html" and self.server.hold_next:
            self.server.hold_next = False
            self.server.waiting.set()
            if not self.server.release.wait(8):
                self.send_error(503)
                return
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    retained = os.environ.get("ODYLITH_FRAME_BRIDGE_PROOF_ROOT")
    root = Path(retained) / "fixtures" if retained else tmp_path_factory.mktemp("frame-bridge")
    root.mkdir(parents=True, exist_ok=True)
    (root / "parent.html").write_text(PARENT.replace("__RUNTIME__", bridge.runtime_js()))
    (root / "child.html").write_text(CHILD.replace("__RUNTIME__", bridge.runtime_js()))
    servers = []
    try:
        for _ in range(2):
            server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Handler, directory=str(root)))
            server.hold_next = False
            server.waiting = threading.Event()
            server.release = threading.Event()
            server.release.set()
            server.gate_waiting = threading.Event()
            server.gate_release = threading.Event()
            server.gate_release.set()
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            servers.append((server, thread))
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                print(json.dumps({"browser": browser.version, "extra_browser_args": [], "fixture": str(root)}))
                yield browser, root, servers[0][0], servers[1][0]
            finally:
                browser.close()
    finally:
        for server, thread in servers:
            server.release.set()
            server.gate_release.set()
            server.shutdown()
            server.server_close()
            thread.join(3)
            assert not thread.is_alive()


@pytest.fixture
def page(native):
    page = native[0].new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("console", lambda message: errors.append(message.text) if message.type == "error" else None)
    try:
        yield page
        assert errors == []
    finally:
        page.close()


def _wait(page, expression, arg=None):
    page.wait_for_function(expression, arg=arg, timeout=5000)


def _urls(native, scheme, pending=False):
    _, root, parent_server, child_server = native
    if scheme == "file":
        parent, child = (root / "parent.html").as_uri(), (root / "child.html").as_uri()
    else:
        parent = f"http://127.0.0.1:{parent_server.server_port}/parent.html"
        child = f"http://127.0.0.1:{child_server.server_port}/child.html"
    return parent, child + ("?pending=1" if pending else "")


def _open(page, native, scheme, **options):
    parent, child = _urls(native, scheme, pending=options.pop("pending", False))
    page.goto(parent + "?" + urlencode({"child": child, **options}), wait_until="load")
    return child


def _barrier(page, value):
    page.evaluate("value => barrier(value)", value)
    _wait(page, "value => evidence.barriers.includes(value)", value)


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_native_opaque_snapshot_and_navigation(page, native, scheme):
    _open(page, native, scheme)
    _wait(page, "evidence.snapshots.length === 1")
    child = page.frames[1]
    assert child.evaluate("reads") == 1
    for value in (None, {"route": {"unchanged": [0, False, ""]}, "outcome": "empty"}, ["opaque", 7]):
        assert child.evaluate("value => publishValue(value)", value) is True
        _barrier(page, str(value))
        assert page.evaluate("evidence.state") == value
    route = {"route": "?surface=registry&component=receipt", "replaceDocument": True}
    assert child.evaluate("route => surface.navigate(route)", route) is True
    _wait(page, "evidence.navigations.length === 1")
    assert page.evaluate("evidence.navigations[0]") == route


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_latest_pending_navigation_flushes_once_and_rebind_reads_owner(page, native, scheme):
    _open(page, native, scheme, pending=True, manual="1")
    child = page.frames[1]
    assert child.evaluate("childEvidence.navigated") == [True, True]
    assert child.evaluate("surface.publish()") is False
    assert child.evaluate("reads") == 0
    assert page.evaluate("owner.bind()") is True
    _wait(page, "evidence.navigations.length === 1")
    assert page.evaluate("evidence.navigations[0].route") == "latest"
    child.evaluate("snapshot = {outcome: 'error', untouched: true}")
    assert page.evaluate("owner.bind()") is True
    _wait(page, "evidence.snapshots.length === 2")
    _barrier(page, "rebound")
    assert page.evaluate("evidence.state") == {"outcome": "error", "untouched": True}
    assert page.evaluate("evidence.navigations.length") == 1
    assert page.evaluate("evidence.closes") == [0]


@pytest.mark.parametrize("scheme", ["http", "file"])
@pytest.mark.parametrize("retain_retired", [False, True], ids=["close-retired", "drain-retired"])
def test_actual_queued_old_document_messages_cannot_cross_same_url_replacement(page, native, scheme, retain_retired):
    url = _open(page, native, scheme, hold="1", retain=str(int(retain_retired)), pending=True)
    _wait(page, "evidence.receipts.some(row => row.probe === 'offered')")
    old_id = page.frames[1].evaluate("documentId")
    assert page.evaluate("evidence.snapshots") == []
    assert page.evaluate("evidence.navigations") == []
    page.evaluate("replaceChild(true)")
    _wait(page, "old => evidence.state && evidence.state.documentId !== old", old_id)
    child = page.frames[1]
    assert child.url == url
    new_id = child.evaluate("documentId")
    assert old_id != new_id
    child.get_by_role("button", name="User selection", exact=True).click()
    _wait(page, "evidence.state.selection === 'user'")
    before = page.evaluate("({state: evidence.state, navigations: evidence.navigations})")
    page.evaluate("startHeldQueue()")
    if retain_retired:
        _wait(page, "evidence.delivered.filter(row => row.binding === 0).length === 2")
    for value in range(3):
        _barrier(page, value)
    after = page.evaluate("structuredClone(evidence)")
    old_messages = [row for row in after["delivered"] if row["binding"] == 0]
    assert len(old_messages) == (2 if retain_retired else 0)
    assert after["state"] == before["state"]
    assert after["navigations"] == before["navigations"]
    if retain_retired:
        assert {row["data"]["kind"] for row in old_messages} == {"snapshot", "navigate"}
        assert after["unguardedSnapshot"]["documentId"] == old_id
    print(json.dumps({"control": "actual-retired-queue", "scheme": scheme,
                      "retain_retired": retain_retired, "old_document": old_id,
                      "new_document": new_id, "evidence": after}))


@pytest.mark.parametrize("revoke", [False, True], ids=["load-only-counterexample", "intent-revoked"])
def test_pending_native_navigation_needs_preload_revocation(page, native, revoke):
    _open(page, native, "http")
    _wait(page, "evidence.snapshots.length === 1")
    before = page.evaluate("evidence.state")
    child_server = native[3]
    child_server.waiting.clear()
    child_server.release.clear()
    child_server.hold_next = True
    try:
        page.evaluate("revoke => replaceChild(revoke)", revoke)
        assert child_server.waiting.wait(5)
        page.evaluate("probeChild({probe: 'during-navigation'})")
        _wait(page, "evidence.receipts.some(row => row.probe === 'sent-during-navigation')")
        if not revoke:
            _wait(page, "evidence.navigations.some(row => row.route === 'old-during-navigation')")
            assert page.evaluate("evidence.state.selection") == "old-during-navigation"
        else:
            assert page.evaluate("evidence.state") == before
            assert page.evaluate("evidence.navigations") == []
        child_server.release.set()
        _wait(page, "old => evidence.state.documentId !== old", before["documentId"])
        _barrier(page, "after-replacement")
        if revoke:
            assert page.evaluate("evidence.navigations") == []
        print(json.dumps({"control": "navigation-gap", "revoke": revoke,
                          "evidence": page.evaluate("structuredClone(evidence)")}))
    finally:
        child_server.release.set()


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_window_messages_have_no_state_authority_and_invalid_offers_cannot_rotate(page, native, scheme):
    _open(page, native, scheme)
    _wait(page, "evidence.snapshots.length === 1")
    child = page.frames[1]
    original = page.evaluate("evidence.state")
    child.evaluate("""() => {
      parent.postMessage({kind: 'snapshot', snapshot: {forged: true}}, '*');
      parent.postMessage({kind: 'navigate', route: 'forged'}, '*');
    }""")
    page.evaluate("""type => {
      const first = new MessageChannel(), second = new MessageChannel();
      childElement.contentWindow.postMessage({type}, '*');
      childElement.contentWindow.postMessage({type}, '*', [first.port2, second.port2]);
      first.port1.close(); second.port1.close();
      const sibling = document.createElement('iframe');
      sibling.id = 'sibling'; document.body.append(sibling);
    }""", OFFER)
    page.frames[2].evaluate("""type => {
      const channel = new MessageChannel();
      parent.frames[0].postMessage({type}, '*', [channel.port2]);
      channel.port1.close();
    }""", OFFER)
    # The original channel's native response proves invalid offers did not rotate it.
    page.evaluate("channels[0].port1.postMessage({probe: 'barrier', value: 'authority'})")
    _wait(page, "evidence.barriers.includes('authority')")
    assert child.evaluate("reads") == 1
    assert page.evaluate("evidence.state") == original
    assert page.evaluate("evidence.navigations") == []


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_revoke_and_dispose_are_terminal_for_their_owned_ports(page, native, scheme):
    _open(page, native, scheme)
    _wait(page, "evidence.snapshots.length === 1")
    child = page.frames[1]
    child.evaluate("surface.dispose()")
    assert child.evaluate("surface.publish()") is False
    assert child.evaluate("surface.navigate({route: 'disposed'})") is False
    page.evaluate("owner.bind()")
    _wait(page, "evidence.receipts.filter(row => row.probe === 'offered').length === 2")
    assert child.evaluate("reads") == 1
    assert page.evaluate("evidence.snapshots.length") == 1
    page.evaluate("owner.revoke(); owner.dispose(); owner.dispose()")
    assert page.evaluate("owner.bind()") is False
    assert page.evaluate("channels.length") == 2
    assert page.evaluate("evidence.closes") == [0, 1]


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_dispose_rejects_genuinely_queued_state_and_navigation(page, native, scheme):
    _open(page, native, scheme, hold="1", retain="1", pending=True)
    _wait(page, "evidence.receipts.some(row => row.probe === 'offered')")
    page.evaluate("owner.dispose(); startHeldQueue()")
    _wait(page, "evidence.delivered.filter(row => row.binding === 0).length === 2")
    assert page.evaluate("evidence.snapshots") == []
    assert page.evaluate("evidence.navigations") == []
    assert page.evaluate("owner.bind()") is False
    assert page.evaluate("evidence.closes") == [0]


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_standalone_surface_never_claims_navigation_or_self_offer(page, native, scheme):
    _, child_url = _urls(native, scheme)
    page.goto(child_url, wait_until="load")
    assert page.evaluate("surface.navigate({route: '?standalone'})") is False
    assert page.evaluate("surface.publish()") is False
    page.evaluate("""type => {
      const channel = new MessageChannel();
      postMessage({type}, '*', [channel.port2]);
      channel.port1.close();
    }""", OFFER)
    _wait(page, "childEvidence.offers === 1")
    assert page.evaluate("reads") == 0
    page.evaluate("surface.dispose()")
    assert page.evaluate("surface.navigate('after-dispose')") is False


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_blank_load_and_missing_window_do_not_manufacture_readiness(page, native, scheme):
    _open(page, native, scheme, blank="1")
    _wait(page, "evidence.loads >= 1")
    assert page.evaluate("evidence.snapshots") == []
    page.evaluate("replaceChild(true)")
    _wait(page, "evidence.snapshots.length === 1")
    assert page.evaluate("evidence.state.documentId") == page.frames[1].evaluate("documentId")
    assert page.evaluate("""() => OdylithFrameBridge.frame({
      frame: {contentWindow: null}, onSnapshot() { throw Error('snapshot'); },
      onNavigate() { throw Error('navigation'); }
    }).bind()""") is False


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_actor_is_stable_across_same_document_rebind_and_opaque_packets(page, native, scheme):
    _open(page, native, scheme, pending=True)
    _wait(page, "evidence.navigations.length === 1")
    first = page.evaluate("structuredClone(evidence)")
    assert [row["kind"] for row in first["callbacks"]] == ["actor", "snapshot", "navigate"]
    actor = first["actors"][0]
    assert len(actor) == 32 and len(bytes.fromhex(actor)) == 16
    page.evaluate("evidence.admitted = true; owner.revoke(); owner.bind()")
    _wait(page, "evidence.snapshots.length === 2")
    child = page.frames[1]
    # Same-Document DOM replacement retains the existing surface actor (Radar's lifecycle).
    child.evaluate("document.body.replaceChildren(); publishValue(null); surface.navigate(['opaque', false])")
    _wait(page, "evidence.navigations.length === 2")
    after = page.evaluate("structuredClone(evidence)")
    assert after["actors"] == [actor]
    assert after["admitted"] is True
    assert after["state"] is None
    assert after["navigations"][-1] == ["opaque", False]
    assert {row["data"]["actor"] for row in after["delivered"]} == {actor}
    assert "randomUUID" not in bridge.runtime_js()


@pytest.mark.parametrize("scheme", ["http", "file"])
def test_new_actor_same_url_is_reported_before_snapshot_before_load(page, native, scheme):
    parent_url, child_url = _urls(native, scheme)
    server = native[3]
    child_url += "?" + urlencode({"loadGate": f"http://127.0.0.1:{server.server_port}/gate.svg"})
    page.goto(parent_url + "?" + urlencode({"child": child_url}), wait_until="load")
    _wait(page, "evidence.snapshots.length === 1")
    old_id = page.frames[1].evaluate("documentId")
    page.evaluate("evidence.admitted = true")
    server.gate_waiting.clear()
    server.gate_release.clear()
    try:
        page.frames[1].goto(child_url, wait_until="commit")
        _wait(page.frames[1], "window.surface !== undefined")
        assert server.gate_waiting.wait(5)
        assert page.frames[1].url == child_url
        assert page.frames[1].evaluate("documentId") != old_id
        assert page.evaluate("evidence.loads") == 1
        page.evaluate("owner.bind()")
        _wait(page, "evidence.snapshots.length === 2")
        after = page.evaluate("structuredClone(evidence)")
        assert after["loads"] == 1
        assert after["callbacks"][-1]["admitted"] is False
        assert [row["kind"] for row in after["callbacks"]] == ["actor", "snapshot", "actor", "snapshot"]
        assert len(set(after["actors"])) == 2
        print(json.dumps({"control": "new-actor-before-load", "scheme": scheme, "evidence": after}))
    finally:
        server.gate_release.set()
    _wait(page, "evidence.loads === 2 && evidence.snapshots.length === 3")
    assert page.evaluate("evidence.actors.length") == 2


@pytest.mark.parametrize("scheme", ["http", "file"])
@pytest.mark.parametrize("kind", ["snapshot", "navigate"])
def test_actor_switch_revokes_port_and_rejects_later_original_actor(page, native, scheme, kind):
    _open(page, native, scheme, retain="1")
    _wait(page, "evidence.snapshots.length === 1")
    actor = page.evaluate("evidence.delivered[0].data.actor || 'a'.repeat(32)")
    other = ("b" if actor[0] != "b" else "c") + actor[1:]
    packet = {"kind": kind, "actor": other, "snapshot": {"forged": True}, "route": ["forged"]}
    child = page.frames[1]
    child.evaluate("packet => diagnosticPort.postMessage(packet)", packet)
    _wait(page, "evidence.delivered.length === 2")
    assert page.evaluate("evidence.snapshots.length") == 1
    assert page.evaluate("evidence.navigations") == []
    assert page.evaluate("evidence.closes") == [0]
    packet["actor"] = actor
    child.evaluate("packet => diagnosticPort.postMessage(packet)", packet)
    _wait(page, "evidence.delivered.length === 3")
    assert page.evaluate("evidence.snapshots.length") == 1
    assert page.evaluate("evidence.navigations") == []
    assert page.evaluate("evidence.actors") == [actor]


@pytest.mark.parametrize("actor", [None, 17, "", "short"])
def test_malformed_first_actor_cannot_establish_binding(page, native, actor):
    _open(page, native, "http", manual="1", retain="1")
    child = page.frames[1]
    child.evaluate("surface.dispose()")
    page.evaluate("owner.bind()")
    _wait(child, "childEvidence.offers === 1")
    child.evaluate("actor => diagnosticPort.postMessage({kind: 'snapshot', actor, snapshot: 'forged'})", actor)
    _wait(page, "evidence.delivered.length === 1")
    assert page.evaluate("evidence.snapshots") == []
    assert page.evaluate("evidence.actors") == []
    assert page.evaluate("evidence.closes") == [0]


@pytest.mark.parametrize("action", ["revoke", "dispose", "bind"])
def test_actor_callback_can_retire_binding_before_opaque_callback(page, native, action):
    _open(page, native, "http", actorAction=action, retain="1")
    _wait(page, "evidence.delivered.length >= 1")
    if action == "bind":
        _wait(page, "evidence.delivered.length === 2")
    after = page.evaluate("structuredClone(evidence)")
    assert after["closes"] == [0]
    assert len(after["actors"]) == 1
    assert len(after["snapshots"]) == (1 if action == "bind" else 0)
    assert [row["kind"] for row in after["callbacks"]] == ["actor"] + (["snapshot"] if action == "bind" else [])
