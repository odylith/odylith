"""Timeline density must not trade audit access for filename guesses."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import pytest

from tests.integration.runtime.surface_browser_test_support import browser_context


_REPO_ROOT = Path(__file__).resolve().parents[3]
_SOURCE_ASSET = (
    _REPO_ROOT / "src/odylith/runtime/surfaces/templates/compass_dashboard/compass-workstreams.v1.js"
)


def _open_timeline(base_url, context, width=1440):
    page = context.new_page()
    page.set_viewport_size({"width": width, "height": 1000})
    errors: list[str] = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/compass-workstreams.v1.js*", lambda route: route.fulfill(
        body=_SOURCE_ASSET.read_text(encoding="utf-8"), content_type="application/javascript",
    ))
    page.route("**/compass-style-surface.v1.css*", lambda route: route.fulfill(
        body=_SOURCE_ASSET.with_name("compass-style-surface.v1.css").read_text(encoding="utf-8"),
        content_type="text/css",
    ))
    page.goto(f"{base_url}/odylith/index.html?tab=compass", wait_until="networkidle")
    frame = page.locator("#frame-compass").element_handle().content_frame()
    frame.wait_for_function("typeof renderTimeline === 'function'")
    return page, frame, errors


@pytest.mark.parametrize("width", [1440, 390])
@pytest.mark.parametrize("placement", ["standalone", "transaction", "mixed", "internal"])
def test_dense_workspace_changes_preserve_every_event(browser_context, width, placement) -> None:
    base_url, context = browser_context
    page, frame, errors = _open_timeline(base_url, context, width)
    timestamp = datetime.now(timezone.utc).isoformat()
    paths = [f"unfamiliar/assets/item-{index}.json" for index in range(240)] + [
        "odylith/casebook/bugs/customer-owned.md",
        "odylith/registry/source/components/customer/CURRENT_SPEC.md",
        "odylith/compass/compass.html",
    ]
    events = [{
        "id": f"local:{index}", "kind": "local_change", "ts_iso": timestamp,
        "summary": f"Changed {path}", "files": [path], "author": "local", "workstreams": [],
    } for index, path in enumerate(paths)]
    signals = [{
        "id": f"signal:{kind}", "kind": kind, "ts_iso": timestamp,
        "summary": summary, "files": [], "workstreams": [], "author": "local",
    } for kind, summary in [
        ("decision", "Keep the source-grounded scope"),
        ("failure", "The review deadline was exceeded"),
    ]]
    transactions = []
    if placement != "standalone":
        attached = events + signals if placement == "transaction" else events[:120]
        transactions = [{
            "id": "txn:test", "transaction_id": "txn:test", "headline": "Consumer work",
            "start_ts_iso": timestamp, "end_ts_iso": timestamp, "events": attached,
            "event_count": len(attached), "files": [], "workstreams": [],
        }]
        if placement == "internal":
            transactions[0].update({
                "id": "txn:global:auto-global-test",
                "transaction_id": "txn:global:auto-global-test",
                "headline": "Closed the active slice and synced the governance surfaces",
            })
    frame.evaluate("""({events, transactions, timestamp}) => {
        renderTimeline({generated_utc: timestamp, now_local_iso: timestamp},
            {date: 'live', window: '24h', workstream: ''}, events, transactions);
    }""", {"events": events + signals, "transactions": transactions, "timestamp": timestamp})
    if placement in {"transaction", "mixed"}:
        frame.locator("#timeline .tx-card:not(.workspace-change-group) > summary").first.click()
    groups = frame.locator("#timeline details.workspace-change-group")
    assert groups.count() == (2 if placement == "mixed" else 1)
    assert frame.locator("#timeline .hour-event:visible").count() == 2
    assert frame.get_by_text(signals[0]["summary"], exact=True).is_visible()
    assert frame.get_by_text(signals[1]["summary"], exact=True).is_visible()
    for group in groups.all():
        group.locator(":scope > summary").focus()
        page.keyboard.press("Enter")
        assert group.get_attribute("open") is not None
    assert frame.locator("#timeline .hour-event:visible").count() == 245
    for path in paths[-3:]:
        assert frame.get_by_text(f"Changed {path}", exact=True).is_visible()
    assert frame.locator("#timeline .hour-event-title").evaluate_all(
        """nodes => nodes.every(node => {
            const bounds = node.getBoundingClientRect();
            const card = node.parentElement.getBoundingClientRect();
            return node.scrollWidth <= node.clientWidth && bounds.right <= card.right
                && bounds.left >= card.left;
        })"""
    )
    assert "Showing 24" not in frame.locator("#timeline").inner_text()
    assert frame.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
    assert not errors
    page.close()


@pytest.mark.parametrize("count", [0, 1])
@pytest.mark.parametrize("width", [1440, 390])
def test_empty_and_single_change_timelines_need_no_group(browser_context, count, width) -> None:
    base_url, context = browser_context
    page, frame, errors = _open_timeline(base_url, context, width)
    frame.evaluate("""(count) => {
        const now = new Date().toISOString();
        const events = count ? [{id: 'local:one', kind: 'local_change', ts_iso: now,
            summary: 'Changed customer source', files: ['customer.py'], workstreams: []}] : [];
        renderTimeline({generated_utc: now, now_local_iso: now},
            {date: 'live', window: '24h', workstream: ''}, events, []);
    }""", count)
    assert frame.locator("#timeline details.workspace-change-group").count() == 0
    assert frame.locator("#timeline .hour-event").count() == count
    expected = "Changed customer source" if count else "No audit events in this window."
    assert frame.get_by_text(expected, exact=True).is_visible()
    assert not errors
    page.close()
