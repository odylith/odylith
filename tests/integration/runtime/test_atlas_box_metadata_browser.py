"""Atlas metadata preserves supplied text and explicit source-action lines."""

from __future__ import annotations

import base64
import json
from contextlib import contextmanager

import pytest

from odylith.runtime.surfaces import render_mermaid_catalog as renderer
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _failure_screenshot_path, _new_page, browser_context,
)
from tests.integration.runtime.test_atlas_viewport_keyboard_browser import _SVG


_METADATA = {
    "node_id": "source_metadata",
    "label": "Record café  intake — **verbatim**.\nInspect <tag> & keep `ID` + __state__.\nRecord café  intake — **verbatim**.",
    "role": "Source **operator** / `role` — <owner> & __literal__",
    "description": (
        "Preserve café  IDs and **evidence**.\n"
        "Show <img src=x onerror=window.__atlas_box_injected__=1> as literal text & keep `proof`.\n"
        "Do not remove __late restriction__: review must precede publication."
    ),
}
_METADATA["details"] = [
    {"label": "Proposed boundary verification — café", "text": "Preserve **exact** <img src=x onerror=window.__atlas_box_injected__=1> & `proof`.\nKeep the final 日本語 condition."},
    {"label": "Source actions", "text": "Source action 1 · human\nThe named steward registers cited datasets.\n" + "UnbrokenSourceIdentifier" * 35},
]
_RESPONSIBILITY = "Retain the steward's cited datasets and authorization boundaries. Preserve café  IDs and the final 日本語 condition."
_ACTION_LINES = ["Record café intake.", "Inspect tag.", "Record café intake."]
_ACTIONS = {
    "node_id": "source_actions", "label": "\n".join(_ACTION_LINES),
    "role": "Grouped source actions", "description": "Listing order does not establish execution order.",
}


def _metadata_html(*, empty: bool, related: dict | None = None) -> str:
    return renderer._render_html(
        diagrams=[] if empty else [{
            "diagram_id": "D-001", "slug": "metadata-custody", "title": "Source metadata custody",
            "kind": "architecture", "status": "draft", "owner": "record-service",
            "summary": "Read the supplied metadata without rewriting it.",
            "read_guide": "Separate source action lines remain separate.",
            "last_reviewed_utc": "2026-09-08", "review_age_days": 0, "freshness": "fresh",
            "source_svg_href": "/metadata-preview.svg", "source_png_href": "/metadata-preview.png",
            "svg_viewbox_width": 2400, "svg_viewbox_height": 1400, "initial_view_fit_factor": 1,
            "diagram_boxes": [_METADATA, _ACTIONS],
            "components": [{"name": "Dataset support", "description": _RESPONSIBILITY}],
            **(related or {}),
        }],
        stats={"total": 0 if empty else 1, "fresh": 0 if empty else 1, "stale": 0},
        max_review_age_days=21, tooltip_lookup={}, generated_utc="2026-09-08T00:00:00Z",
        brand_head_html="", tooling_base_href="/odylith/index.html",
    )


@contextmanager
def _open_metadata(browser_context, width: int, state: str, *, related: dict | None = None):  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII="
        )

        def asset(route):  # noqa: ANN001
            is_png = route.request.url.endswith(".png")
            body = png if is_png else _SVG
            if state == "error" or (state == "fallback" and not is_png):
                body = b"invalid image"
            route.fulfill(status=200, content_type="image/png" if is_png else "image/svg+xml", body=body)

        page.route("**/metadata-preview.svg", asset)
        page.route("**/metadata-preview.png", asset)
        page.route("**/odylith/atlas/atlas.html*", lambda route: route.fulfill(
            status=200, content_type="text/html", body=_metadata_html(empty=state == "empty", related=related),
        ))
        response = page.goto(base_url + "/odylith/index.html?tab=atlas", wait_until="networkidle")
        assert response is not None and response.ok
        assert page.locator("#tab-atlas").get_attribute("aria-selected") == "true"
        atlas = page.frame_locator("#frame-atlas")
        if state == "error":
            atlas.locator("#viewerAssetError").wait_for(state="visible")
            assert atlas.locator("#viewerImage").is_hidden()
            assert atlas.locator("#reset").is_disabled()
        elif state != "empty":
            page.wait_for_function("""() => {
            const image=document.querySelector('#frame-atlas').contentDocument.querySelector('#viewerImage');
            return image && image.complete && image.naturalWidth > 0;
        }""")
            assert atlas.locator("#viewerImage").get_attribute("src").endswith(".png" if state == "fallback" else ".svg")
            assert atlas.locator("#viewerAssetError").is_hidden()
        yield page, atlas, observation


def _capture(page, name: str, measurement: dict) -> None:  # noqa: ANN001
    screenshot = _failure_screenshot_path(name)
    if screenshot:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
        screenshot.with_suffix(".json").write_text(json.dumps(measurement, indent=2, ensure_ascii=False) + "\n")


def _text_bounds(target):  # noqa: ANN001
    return target.evaluate("""target => {
        const doc=target.ownerDocument, range=doc.createRange();range.selectNodeContents(target);
        const rects=Array.from(range.getClientRects()),clipped=[],hidden=[];
        for(let owner=target;owner;owner=owner.parentElement){
            const box=owner.getBoundingClientRect(),style=getComputedStyle(owner);
            if(style.display==='none'||style.visibility==='hidden'||parseInt(style.webkitLineClamp||'0',10)>0)
                hidden.push(owner.className);
            if(owner.scrollLeft)clipped.push({owner:owner.className,scrollLeft:owner.scrollLeft});
            for(const rect of rects){
                if(rect.left < -1 || rect.right > doc.documentElement.clientWidth+1)
                    clipped.push({left:rect.left,right:rect.right});
                if(['hidden','clip','auto','scroll'].includes(style.overflowX) &&
                    (rect.left<box.left-1||rect.right>box.right+1))clipped.push({owner:owner.className,axis:'x'});
                if(['hidden','clip'].includes(style.overflowY) &&
                    (rect.top<box.top-1||rect.bottom>box.bottom+1))clipped.push({owner:owner.className,axis:'y'});
            }
        }
        return {text:target.textContent,clipped,hidden};
    }""")


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback", "error"])
def test_box_metadata_keeps_exact_supplied_text_inert(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    with _open_metadata(browser_context, width, state) as (page, atlas, observation):
        rows = atlas.locator(".diagram-box-row")
        assert rows.count() == 2
        row = rows.first
        row.scroll_into_view_if_needed()
        disclosure = row.locator('details.diagram-box-details')
        assert disclosure.get_attribute('open') is None
        assert disclosure.locator('dd').first.is_hidden()
        disclosure.locator('summary').focus()
        disclosure.locator('summary').press('Enter')
        actual, geometry = {}, {}
        for field, selector in [("label", ".diagram-box-name strong"), ("role", ".diagram-box-details dd:first-of-type"),
                                ("description", ".diagram-box-description")]:
            target = row.locator(selector)
            target.scroll_into_view_if_needed()
            assert target.is_visible()
            actual[field] = target.text_content()
            geometry[field] = _text_bounds(target)
            assert target.locator("*").count() == 0, "Metadata must remain inert text, not injected markup"
        _capture(page, f"atlas-box-exact-{width}-{state}", {"actual": actual, "geometry": geometry})
        assert actual == {field: _METADATA[field] for field in actual}
        assert not atlas.locator("body").evaluate("() => Boolean(window.__atlas_box_injected__)")
        assert all(not row["clipped"] and not row["hidden"] for row in geometry.values()), geometry
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "fallback", "error"])
def test_source_action_lines_are_visually_separate_in_order(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    with _open_metadata(browser_context, width, state) as (page, atlas, observation):
        heading = atlas.locator(".diagram-box-row").nth(1).locator(".diagram-box-name strong")
        heading.scroll_into_view_if_needed()
        measurement = heading.evaluate("""(target,lines) => {
            const text=target.textContent,node=target.firstChild,positions=[];
            let cursor=0;
            for(const line of lines){
                const start=text.indexOf(line,cursor);
                if(start<0||!node||node.nodeType!==Node.TEXT_NODE)return {text,missing:line};
                const range=target.ownerDocument.createRange();range.setStart(node,start);range.setEnd(node,start+line.length);
                positions.push({line,start,rects:Array.from(range.getClientRects()).filter(r=>r.width>0)
                    .map(r=>({top:r.top,bottom:r.bottom,left:r.left,right:r.right}))});
                cursor=start+line.length;
            }
            return {text,positions};
        }""", _ACTION_LINES)
        measurement["bounds"] = _text_bounds(heading)
        _capture(page, f"atlas-box-lines-{width}-{state}", measurement)
        assert "missing" not in measurement, measurement
        positions = measurement["positions"]
        assert len(positions) == len(_ACTION_LINES) and all(row["rects"] for row in positions)
        for previous, current in zip(positions, positions[1:]):
            assert min(rect["top"] for rect in current["rects"]) >= max(rect["bottom"] for rect in previous["rects"]) - 1, measurement
        assert measurement["text"] == _ACTIONS["label"]
        assert not measurement["bounds"]["clipped"] and not measurement["bounds"]["hidden"], measurement
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_empty_atlas_has_no_box_metadata_or_injected_action_rows(browser_context, width: int) -> None:  # noqa: ANN001
    with _open_metadata(browser_context, width, "empty") as (page, atlas, observation):
        empty = atlas.locator("#atlasEmptyState")
        assert empty.is_visible() and "No diagrams yet" in empty.inner_text()
        assert atlas.locator(".diagram-box-row").count() == 0
        assert atlas.locator("#diagramBoxesSection").is_hidden()
        assert atlas.locator("#viewerImage").is_hidden()
        assert atlas.locator("#viewerAssetError").is_hidden()
        assert atlas.locator("#reset").is_disabled()
        assert atlas.locator('.engineering-context-empty').is_hidden()
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _capture(page, f"atlas-box-empty-{width}", {"text": empty.inner_text(), "rows": 0})
        _assert_clean_page(page, observation)


@pytest.mark.parametrize('width', [1440, 430], ids=['desktop', 'mobile'])
@pytest.mark.parametrize('state', ['normal', 'fallback', 'error'])
def test_box_supporting_details_are_keyboard_accessible_exact_and_unclipped(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    with _open_metadata(browser_context, width, state) as (page, atlas, observation):
        row = atlas.locator('.diagram-box-row').first
        disclosure = row.locator('details.diagram-box-details')
        summary = disclosure.locator('summary')
        assert summary.inner_text() == 'Supporting details'
        assert disclosure.get_attribute('open') is None
        assert disclosure.locator('dd').first.is_hidden()
        assert row.locator('.diagram-box-description').text_content() == _METADATA['description']
        summary.scroll_into_view_if_needed()
        summary.focus()
        assert summary.evaluate('node => node === node.ownerDocument.activeElement')
        summary.press('Space')
        assert disclosure.get_attribute('open') is not None
        actual, geometry = [], []
        for index, expected in enumerate([{'label': 'Role', 'text': _METADATA['role']}, *_METADATA['details']]):
            actual.append({})
            for field, selector in [('label', 'dt'), ('text', 'dd')]:
                target = disclosure.locator(selector).nth(index)
                target.scroll_into_view_if_needed()
                assert target.is_visible()
                actual[-1][field] = target.text_content()
                assert actual[-1][field] == expected[field]
                assert target.locator('*').count() == 0
                geometry.append(_text_bounds(target))
        assert all(not bounds['clipped'] and not bounds['hidden'] for bounds in geometry), geometry
        assert not atlas.locator('body').evaluate('() => Boolean(window.__atlas_box_injected__)')
        assert not atlas.locator('body').evaluate('body => body.scrollWidth > innerWidth+1')
        assert atlas.locator('.diagram-box-row').nth(1).locator('details').count() == 0
        assert atlas.locator('body').evaluate('() => allDiagrams[0].diagram_boxes[1].role') == _ACTIONS['role']
        ownership = atlas.locator('details.ownership-section')
        assert ownership.get_attribute('open') is None
        component = atlas.locator('.component-description')
        assert component.is_hidden()
        ownership.locator('summary').focus()
        ownership.locator('summary').press('Enter')
        component.scroll_into_view_if_needed()
        assert component.text_content() == _RESPONSIBILITY
        assert component.locator('*').count() == 0
        bounds = _text_bounds(component)
        assert not bounds['clipped'] and not bounds['hidden'], bounds
        _capture(page, f'atlas-box-details-{width}-{state}', {'actual': actual, 'geometry': geometry})
        sizing = atlas.locator('.diagram-explanation-section').evaluate('''node => {
            const section=node.getBoundingClientRect(), last=node.lastElementChild.getBoundingClientRect();
            return {unusedBottom:section.bottom-last.bottom, padding:parseFloat(getComputedStyle(node).paddingBottom)};
        }''')
        assert abs(sizing['unusedBottom'] - sizing['padding'] - 1) <= 1, sizing
        summary.scroll_into_view_if_needed()
        summary.press('Enter')
        assert disclosure.get_attribute('open') is None
        assert disclosure.locator('dd').first.is_hidden()
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "error"])
@pytest.mark.parametrize("context_kind", ["absent", "partial", "complete"])
def test_engineering_context_omits_empty_categories_and_preserves_links(
    browser_context, width: int, state: str, context_kind: str,
) -> None:  # noqa: ANN001
    categories = {
        "backlog": "backlogLinks", "plans": "planLinks", "docs": "docLinks",
        "code": "codeLinks", "registry": "registryLinks", "surfaces": "surfaceLinks",
    }
    populated = set(categories) if context_kind == "complete" else (
        {"plans", "code"} if context_kind == "partial" else set()
    )
    related = {f"related_{name}": [{
        "file": f"Exact {name} reference — café", "href": f"/odylith/index.html?context={name}",
        "target": "_top" if name == "plans" else "_blank",
    }] for name in populated}
    with _open_metadata(browser_context, width, state, related=related) as (page, atlas, observation):
        section = atlas.locator(".linked-context-section")
        assert section.evaluate("node => node.tagName") == "DETAILS"
        assert section.get_attribute("open") is None
        assert section.locator('.artifact-group:visible').count() == 0
        summary = section.locator(':scope > summary')
        summary.focus()
        summary.press('Enter')
        assert section.get_attribute('open') is not None
        availability = section.locator(".engineering-context-empty")
        assert section.locator(".artifact-group:visible").count() == len(populated)
        if populated:
            assert availability.is_hidden()
        else:
            availability.scroll_into_view_if_needed()
            assert availability.is_visible() and availability.get_attribute("role") == "status"
            assert availability.inner_text() == "No engineering context is linked to this diagram yet."
            bounds = _text_bounds(availability)
            assert not bounds["clipped"] and not bounds["hidden"], bounds
        for name, node_id in categories.items():
            links = atlas.locator(f"#{node_id}")
            if name not in populated:
                assert links.is_hidden() and links.locator("a").count() == 0
                continue
            link = links.locator("a")
            link.scroll_into_view_if_needed()
            assert link.is_visible() and link.count() == 1
            assert {field: link.get_attribute(field) for field in ("href", "target")} == {
                field: related[f"related_{name}"][0][field] for field in ("href", "target")
            }
            assert link.text_content() == related[f"related_{name}"][0]["file"]
            bounds = _text_bounds(link)
            assert not bounds["clipped"] and not bounds["hidden"], bounds
        assert atlas.locator("#viewerAssetError").is_visible() if state == "error" else atlas.locator("#viewerAssetError").is_hidden()
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _capture(page, f"atlas-context-{width}-{state}-{context_kind}", {"populated": sorted(populated)})
        summary.focus()
        summary.press('Enter')
        assert section.get_attribute('open') is None and section.locator('.artifact-group:visible').count() == 0
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("generated_role", [
    "Container", "Proposed component", "Proposed component support",
    "Proposed logical component", "Proposed workstream",
])
def test_box_roles_are_folded_without_changing_supplied_values(
    browser_context, monkeypatch, width: int, generated_role: str,
) -> None:  # noqa: ANN001
    custom_role = "Source steward — café <owner> & **exact** authority"
    proposed_title = "Proposed Capability Support and Source Facts"
    monkeypatch.setitem(_METADATA, "role", generated_role)
    monkeypatch.setitem(_ACTIONS, "role", custom_role)
    monkeypatch.setitem(_ACTIONS, "details", [])
    with _open_metadata(browser_context, width, "normal", related={"title": proposed_title}) as (page, atlas, observation):
        rows = atlas.locator(".diagram-box-row")
        assert rows.count() == 2 and rows.first.locator(".diagram-box-role").count() == 0
        assert rows.locator('.diagram-box-role').count() == 0
        disclosure = rows.first.locator('details.diagram-box-details')
        role = disclosure.locator('dd').first
        assert disclosure.get_attribute('open') is None and role.is_hidden()
        disclosure.locator('summary').focus()
        disclosure.locator('summary').press('Enter')
        role.scroll_into_view_if_needed()
        assert role.is_visible() and role.text_content() == generated_role
        assert role.locator('*').count() == 0
        bounds = _text_bounds(role)
        assert not bounds['clipped'] and not bounds['hidden'], bounds
        assert rows.nth(1).locator('details').count() == 0
        assert custom_role not in rows.nth(1).inner_text()
        assert atlas.locator("#diagramTitle").text_content() == proposed_title
        supplied = json.loads(atlas.locator("#catalogData").text_content())["diagrams"][0]["diagram_boxes"]
        assert supplied == [_METADATA, _ACTIONS]
        assert atlas.locator("body").evaluate("() => allDiagrams[0].diagram_boxes") == supplied
        assert rows.first.locator(".diagram-box-description").text_content() == _METADATA["description"]
        assert not atlas.locator("body").evaluate("body => body.scrollWidth > innerWidth+1")
        _capture(page, f"atlas-generic-badge-{width}-{generated_role}", {"raw_role": generated_role, "retained_custom_role": custom_role})
        _assert_clean_page(page, observation)


@pytest.mark.parametrize('width', [1440, 430], ids=['desktop', 'mobile'])
@pytest.mark.parametrize('state', ['normal', 'fallback', 'error'])
def test_authored_views_preserve_every_narrative_and_detail(browser_context, width: int, state: str) -> None:  # noqa: ANN001
    from tests.unit.runtime.test_greenfield_authored_atlas_view import _authored_diagrams, _source_lifecycle

    for diagram in _authored_diagrams(source_lifecycle=_source_lifecycle()):
        display = {**diagram, 'diagram_boxes': [*diagram['diagram_boxes'],
            {'label': 'Legacy empty inventory', 'role': 'Container', 'description': ''},
            {'node_id': 'whitespace-inventory', 'label': 'Whitespace inventory', 'role': 'Container', 'description': ' \n'},
        ]}
        with _open_metadata(browser_context, width, state, related=display) as (page, atlas, observation):
            rows = atlas.locator('.diagram-box-row')
            assert rows.count() == len(diagram['diagram_boxes'])
            supplied_boxes = atlas.locator('body').evaluate(
                '(_body, slug) => allDiagrams.find(diagram => diagram.slug === slug).diagram_boxes', diagram['slug'],
            )
            assert supplied_boxes == display['diagram_boxes']
            assert atlas.locator('#diagramSummary').text_content() == diagram['summary']
            assert atlas.locator('#diagramReadGuide').text_content() == diagram['read_guide']
            assert atlas.locator('.read-guide').get_attribute('open') is None
            assert not any('Legacy empty inventory' in text for text in rows.all_text_contents())
            assert not any('Whitespace inventory' in text for text in rows.all_text_contents())
            assert 'Actor:' not in atlas.locator('#diagramBoxList').inner_text()
            assert 'Source event:' not in atlas.locator('#diagramBoxList').inner_text()
            if diagram['slug'] == 'harbor-desk-context':
                responsibilities = {component['name']: component['description'] for component in diagram['components']}
                assert all(box['description'] == responsibilities[box['label']] for box in diagram['diagram_boxes'] if box['role'] == 'Product-owned component')
            for index, box in enumerate(diagram['diagram_boxes']):
                row = rows.nth(index)
                fields = [('.diagram-box-name strong', box['label'])]
                if box['description']:
                    fields.append(('.diagram-box-description', box['description']))
                else:
                    assert row.locator('.diagram-box-description').count() == 0
                for selector, expected in fields:
                    value = row.locator(selector)
                    value.scroll_into_view_if_needed()
                    assert value.is_visible() and value.text_content() == expected
                    bounds = _text_bounds(value)
                    assert not bounds['clipped'] and not bounds['hidden'], bounds
                detail = row.locator('details.diagram-box-details')
                if not box.get('details'):
                    assert detail.count() == 0
                    assert supplied_boxes[index]['role'] == box['role']
                    continue
                assert detail.count() == 1
                assert detail.get_attribute('open') is None and detail.locator('dd').first.is_hidden()
                detail.locator('summary').focus()
                detail.locator('summary').press('Enter')
                assert detail.get_attribute('open') is not None and detail.locator('dd').first.is_visible()
                expected = [{'label': 'Role', 'text': box['role']}, *box.get('details', [])]
                assert detail.locator('dt').all_text_contents() == [value['label'] for value in expected]
                assert detail.locator('dd').all_text_contents() == [value['text'] for value in expected]
                for value in detail.locator('dd').all():
                    value.scroll_into_view_if_needed()
                    bounds = _text_bounds(value)
                    assert not bounds['clipped'] and not bounds['hidden'], bounds
                detail.locator('summary').focus()
                detail.locator('summary').press('Enter')
                assert detail.get_attribute('open') is None and detail.locator('dd').first.is_hidden()
            assert not atlas.locator('body').evaluate('body => body.scrollWidth > innerWidth+1')
            _capture(page, f"atlas-authored-{diagram['slug']}-{width}-{state}", {'boxes': diagram['diagram_boxes']})
            _assert_clean_page(page, observation)
