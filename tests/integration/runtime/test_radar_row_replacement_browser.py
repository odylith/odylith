"""Radar row replacement preserves identity and refuses invalid final targets.

The ordinal-prepend fixture is a reflow/clipping negative. These controls do
not establish a successful click after a visible, layout-preserving ordinal change.
"""

import json

import pytest

from odylith.runtime.surfaces import render_backlog_ui_html_runtime as html_runtime
from tests.integration.runtime import surface_browser_test_support as support
from tests.integration.runtime.surface_browser_test_support import browser_context
from tests.unit.runtime.test_backlog_story_projection import AUTHORED_BLOCK


class PreparedRow:
    """Force the proved interleaving only if the helper asks for row geometry."""

    def __init__(self, locator, frame):
        self.locator = locator
        self.frame = frame
        self.stale_box_calls = 0

    def __getattr__(self, name):
        return getattr(self.locator, name)

    def bounding_box(self):
        self.stale_box_calls += 1
        handle = self.locator.element_handle()
        self.frame.evaluate("""() => new Promise(resolve => {
            const proof = window.__pointerProof;
            proof.nativeRAF(timestamp => {
                proof.flush(timestamp);
                proof.nativeRAF(resolve);
            });
        })""")
        try:
            return handle.bounding_box()
        finally:
            handle.dispose()


def prepare(browser_context, mode="replace"):
    base_url, context = browser_context
    page = context.new_page()
    page.set_viewport_size({"width": 1440, "height": 932})
    source = (AUTHORED_BLOCK + "\n\n") * 40 + "The final condition is still required."
    entries = [{
        "idea_id": f"B-{index + 1:03}", "title": f"Authored workstream {index + 1}",
        "section": "active", "status": "queued", "rank": str(index + 1),
        "story_source": "Proposed Solution",
        "story_text": source if index == 1 else f"Preserve record {index + 1}",
    } for index in range(185)]
    page.route("**/radar-pointer.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload={"entries": entries}),
    ))
    page.route("**/pointer-shell.html", lambda route: route.fulfill(
        status=200, content_type="text/html",
        body='<html><body style="margin:0"><header style="height:100px">Governance</header>'
             '<iframe id="radar" src="radar-pointer.html" style="border:0;width:100%;height:800px"></iframe></body></html>',
    ))
    page.goto(base_url + "/pointer-shell.html", wait_until="networkidle")
    frame = page.frame(url=base_url + "/radar-pointer.html")
    assert frame is not None
    button = frame.locator('button[data-idea-id="B-002"]')
    assert button.locator(".row-story-text").inner_text() == source
    assert button.evaluate("node => node.clientHeight > node.closest('#list').clientHeight")
    frame.evaluate("""mode => {
        const nativeRAF = window.requestAnimationFrame.bind(window);
        const list = document.querySelector('#list');
        const proof = window.__pointerProof = {
            nativeRAF, queued: [], released: 0, replacements: 0, clicks: [],
            original: list.querySelector('[data-idea-id="B-002"]'),
        };
        proof.flush = timestamp => {
            const callbacks = proof.queued.splice(0);
            for (const callback of callbacks) {
                proof.released += 1;
                callback(timestamp);
                const fresh = list.querySelector('[data-idea-id="B-002"]');
                proof.replacement = {
                    old_connected: proof.original.isConnected,
                    fresh_connected: fresh?.isConnected || false,
                    fresh_box: fresh?.getBoundingClientRect().toJSON(),
                    row_ids: [...list.querySelectorAll('.row')].map(node => node.dataset.ideaId),
                };
                if (mode === 'absent') fresh.remove();
                if (mode === 'duplicate') list.append(fresh.cloneNode(true));
                if (mode === 'ordinal') list.prepend(fresh);
                if (mode === 'clip') list.style.cssText += ';height:0;min-height:0;max-height:0;padding:0';
                if (mode === 'overlay') {
                    const cover = document.createElement('div');
                    cover.id = 'pointer-obstruction';
                    cover.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:white';
                    document.body.append(cover);
                }
            }
        };
        new MutationObserver(records => {
            proof.replacements += records.filter(record =>
                [...record.removedNodes].some(node => node.matches?.('.row')) &&
                [...record.addedNodes].some(node => node.matches?.('.row'))).length;
        }).observe(list, {childList: true});
        window.requestAnimationFrame = callback => {
            if (String(callback).includes('renderList(latestRenderedRows')) {
                proof.queued.push(callback);
                return -1;
            }
            return nativeRAF(timestamp => {proof.flush(timestamp); callback(timestamp);});
        };
        document.body.addEventListener('click', event => {
            if (!proof.clicks.length) proof.replacementsBeforeClick = proof.replacements;
            proof.clicks.push({trusted: event.isTrusted, id: event.target.closest('[data-idea-id]')?.dataset.ideaId});
        }, true);
    }""", mode)
    return page, frame, PreparedRow(button, frame)


def receipt(frame, row, record_property):
    evidence = frame.evaluate("""() => {
        const proof = window.__pointerProof;
        const matches = document.querySelectorAll('#list button[data-idea-id="B-002"]');
        const list = document.querySelector('#list'), clip = list.getBoundingClientRect();
        const controls = document.querySelector('.controls').getBoundingClientRect();
        const node = matches[0], box = node?.getBoundingClientRect();
        let finalSample = {count: matches.length, scroll_top: list.scrollTop, reachable: false};
        if (box) {
            const left = Math.max(box.left, clip.left, 0), right = Math.min(box.right, clip.right, innerWidth);
            const top = Math.max(box.top, clip.top, controls.bottom, 0);
            const bottom = Math.min(box.bottom, clip.bottom, innerHeight);
            const x = (left + right) / 2, y = (top + bottom) / 2;
            const hit = document.elementFromPoint(x, y);
            finalSample = {...finalSample, box: box.toJSON(), clip: clip.toJSON(), controls_bottom: controls.bottom,
                x, y, hit_id: hit?.id || '', hit_row: hit?.closest('[data-idea-id]')?.dataset.ideaId || '',
                reachable: matches.length === 1 && node.isConnected && right > left && bottom > top && node.contains(hit)};
        }
        return {released: proof.released, replacements: proof.replacements,
            replacements_before_click: proof.replacementsBeforeClick,
            replacement: proof.replacement, clicks: proof.clicks, final_sample: finalSample};
    }""")
    evidence["stale_box_calls"] = row.stale_box_calls
    record_property("pointer_evidence", json.dumps(evidence, sort_keys=True))
    return evidence


@pytest.mark.parametrize("mode", ["replace"])
def test_pointer_replacement(browser_context, record_property, mode):
    page, frame, row = prepare(browser_context, mode)
    try:
        support._click_visible_radar_row(row)
        assert frame.locator('#detail [data-kpi="workstream-id"] .v').inner_text() == "B-002"
    finally:
        evidence = receipt(frame, row, record_property)
    assert evidence["released"] == 1
    assert evidence["replacement"]["old_connected"] is False
    assert evidence["replacement"]["fresh_connected"] is True
    assert evidence["replacement"]["row_ids"] == ["B-001", "B-002"]
    assert evidence["replacements_before_click"] == 1
    assert evidence["clicks"] == [{"trusted": True, "id": "B-002"}]
    assert evidence["stale_box_calls"] == 0
    page.close()


@pytest.mark.parametrize("mode", ["ordinal", "absent", "clip", "overlay", "duplicate"])
def test_pointer_refuses_invalid_final_sample(browser_context, record_property, mode):
    page, frame, row = prepare(browser_context, mode)
    if mode == "ordinal":
        row.locator = frame.locator("#list .row").nth(1)
    with pytest.raises(AssertionError, match="clipped or obstructed"):
        support._click_visible_radar_row(row)
    evidence = receipt(frame, row, record_property)
    assert evidence["released"] == (2 if mode == "ordinal" else 1)
    assert evidence["replacement"]["old_connected"] is False
    assert evidence["replacement"]["fresh_connected"] is True
    assert evidence["clicks"] == []
    assert evidence["stale_box_calls"] == 0
    assert evidence["final_sample"]["reachable"] is False
    assert frame.locator('#detail [data-kpi="workstream-id"] .v').inner_text() == "B-001"
    page.close()
