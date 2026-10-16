"""Native shell admission must follow surface actors, not iframe load timing."""

import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import urlencode, urlsplit

import pytest
from playwright.sync_api import sync_playwright
from tests.unit.runtime import test_governance_frame_bridge as fixture


ROOT = Path(__file__).resolve().parents[3]
NAVIGATION = ROOT / 'src/odylith/runtime/surfaces/templates/tooling_dashboard/navigation.js'
navigation_source = NAVIGATION.read_text()
runtime = fixture.bridge.runtime_js()

parent = fixture.PARENT.replace('__RUNTIME__', runtime + '\n' + navigation_source)
owner_start = parent.index('window.owner = OdylithFrameBridge.frame(')
owner_end = parent.index("window.addEventListener('message'", owner_start)
parent = parent[:owner_start] + r'''
window.states = [];
window.shellOwner = createToolingShellNavigation({
  panes: {casebook: childElement, project: {}}, payload: {casebook_href: childURL},
  onState(state) { states.push(state); evidence.state = state; },
  localStorageRead() { return null; }, localStorageWrite() {},
});
''' + parent[owner_end:]
parent = parent.replace("  if (options.get('manual') !== '1') owner.bind();", '')
parent = parent.replace('  if (revoke) owner.revoke();', '')
parent = parent.replace("childElement.src = options.get('blank') === '1' ? 'about:blank' : childURL;", 'shellOwner.start();')

child = fixture.CHILD.replace('__RUNTIME__', runtime)
child = child.replace("window.snapshot = {documentId, requested: {route: '?default'}, rendered: {route: '?default'}, outcome: 'ready'};", "const requestedBug = new URLSearchParams(location.search).get('bug') || 'CB-305';\nwindow.snapshot = {documentId, requested: {bug: requestedBug}, rendered: {bug: requestedBug}, outcome: 'ready'};")
child += r'''<script>
window.inPlace = (bug, outcome) => {
  snapshot = {documentId, requested: {bug: requestedBug}, rendered: outcome === 'ready' ? {bug} : null, outcome};
  surface.navigate({route: {bug}, replaceDocument: false});
  surface.publish();
};
document.getElementById('user').onclick = () => inPlace('CB-999', 'ready');
</script>'''


class Handler(fixture._Handler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == '/parent.html':
            content, kind = parent.encode(), 'text/html'
        elif path == '/child.html':
            self.server.document_requests.append(self.path)
            html = child
            if self.server.gate_next:
                self.server.gate_next = False
                html += '<img src="/gate.svg" alt="native load barrier">'
            content, kind = html.encode(), 'text/html'
        elif path == '/gate.svg':
            self.server.gate_waiting.set()
            if not self.server.release.wait(8):
                self.send_error(503)
                return
            content, kind = b'<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"/>', 'image/svg+xml'
        else:
            self.send_error(404)
            return
        self.send_response(200)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(content)))
        self.end_headers()
        self.wfile.write(content)


def server():
    value = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    value.release = threading.Event()
    value.release.set()
    value.gate_waiting = threading.Event()
    value.gate_next = False
    value.document_requests = []
    thread = threading.Thread(target=value.serve_forever, daemon=True)
    thread.start()
    return value, thread


def evidence(page):
    return page.evaluate('({evidence: structuredClone(evidence), states: structuredClone(states), outcome: childElement.dataset.navigationOutcome})')


def run_case(browser, parent_server, child_server, mode, outcome):
    page = browser.new_page()
    native, errors = [], []
    page.on('framenavigated', lambda frame: native.append({'main': frame == page.main_frame, 'url': frame.url}))
    page.on('pageerror', lambda error: errors.append(str(error)))
    try:
        child_server.document_requests.clear()
        child_url = f'http://127.0.0.1:{child_server.server_port}/child.html?bug=CB-305'
        parent_url = f'http://127.0.0.1:{parent_server.server_port}/parent.html?' + urlencode({'child': child_url, 'tab': 'casebook', 'bug': 'CB-305'})
        page.goto(parent_url, wait_until='load')
        fixture._wait(page, 'evidence.loads === 1 && evidence.state.bug === "CB-305" && evidence.delivered.length >= 1')
        old_frame = page.frames[1]
        old_id = old_frame.evaluate('documentId')
        old_frame.evaluate('outcome => inPlace("CB-340", outcome)', outcome)
        fixture._wait(page, 'evidence.state.bug === "CB-340"')
        before = evidence(page)
        baseline_loads = before['evidence']['loads']

        if mode == 'same-document':
            page.evaluate('shellOwner.selectTab("project"); shellOwner.selectTab("casebook")')
            fixture._barrier(page, 'same-document')
            assert page.frames[1].evaluate('documentId') == old_id
            assert page.evaluate('evidence.state.bug') == 'CB-340'
            assert child_server.document_requests == ['/child.html?bug=CB-305']
            return {'mode': mode, 'outcome': outcome, 'result': 'pass', 'after': evidence(page), 'native': native, 'errors': errors}

        child_server.gate_waiting.clear()
        child_server.release.clear()
        child_server.gate_next = True
        page.frames[1].goto(child_url, wait_until='commit')
        new_frame = page.frames[1]
        new_frame.wait_for_function('typeof window.surface === "object"', timeout=5000)
        assert child_server.gate_waiting.wait(5)
        new_id = new_frame.evaluate('documentId')
        assert new_id != old_id
        assert page.evaluate('evidence.loads') == baseline_loads
        assert new_frame.url == child_url
        commit = {'oldDocument': old_id, 'newDocument': new_id, 'childReadyState': new_frame.evaluate('document.readyState'), 'parentLoadCount': page.evaluate('evidence.loads'), 'snapshot': new_frame.evaluate('snapshot')}

        if mode == 'wait-for-load':
            new_frame.evaluate('inPlace("CB-999", "ready")')
            assert page.evaluate('evidence.state.bug') == 'CB-340'
            child_server.release.set()
            fixture._wait(page, 'evidence.loads >= 3')
            fixture._wait(page, 'evidence.state.bug === "CB-340" && evidence.unguardedSnapshot.rendered.bug === "CB-340"')
            assert not any(row['bug'] == 'CB-999' for row in page.evaluate('states'))
            result = 'pass'
        else:
            # A real new-Document action is queued before the shell offers a port.
            new_frame.get_by_role('button', name='User selection', exact=True).click()
            assert page.evaluate('evidence.state.bug') == 'CB-340'
            if mode == 'return-rebind':
                page.evaluate('shellOwner.selectTab("project"); shellOwner.selectTab("casebook")')
            else:
                page.evaluate('shellOwner.selectTab("casebook")')
            fixture._wait(page, 'id => evidence.delivered.some(row => row.data.kind === "snapshot" && row.data.snapshot.documentId === id)', new_id)
            fixture._wait(page, 'evidence.state.bug === "CB-340" && evidence.unguardedSnapshot.rendered.bug === "CB-340"')
            assert not any(row['bug'] == 'CB-999' for row in page.evaluate('states'))
            assert child_server.document_requests[-1] == '/child.html?bug=CB-340'
            result = 'pass'
        return {'mode': mode, 'outcome': outcome, 'result': result, 'commit': commit, 'after': evidence(page), 'requests': list(child_server.document_requests), 'native': native, 'errors': errors}
    finally:
        child_server.release.set()
        page.close()


@pytest.mark.parametrize(("mode", "outcome"), [
    ("same-document", "loading"), ("same-document", "degraded"),
    ("active-rebind", "loading"), ("return-rebind", "degraded"),
    ("wait-for-load", "degraded"),
])
def test_native_document_admission(mode, outcome):
    servers = [server(), server()]
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                result = run_case(browser, servers[0][0], servers[1][0], mode, outcome)
                assert result["errors"] == []
                print(json.dumps(result))
            finally:
                browser.close()
    finally:
        for value, thread in servers:
            value.release.set()
            value.shutdown()
            value.server_close()
            thread.join(3)
            assert not thread.is_alive()
