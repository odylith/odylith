"""Authored Radar previews stay complete, differentiated, and inert in the browser."""

from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_backlog_ui_html_runtime as html_runtime
from odylith.runtime.surfaces import backlog_detail_pages
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _click_visible_radar_row, _failure_screenshot_path, _new_page, browser_context,
)
from tests.unit.runtime.test_backlog_story_projection import AUTHORED_BLOCK, story_entry


MARKDOWN_STORY = (
    "**Proposed deliverable** — Preserve the original evidence.\n\n"
    "- Record the `__sample_id__` and observation.\n"
    "  - Keep `1. first 2. second` literally.\n"
    "- Keep the exception until [review evidence](docs/review_(draft).md) is complete.\n\n"
    "**Assumption:** this is a proposed acceptance check, not a passing result."
)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "runtime-fallback"])
def test_markdown_story_is_formatted_and_faithful_in_preview_and_detail(
    tmp_path: Path, browser_context, width: int, state: str,
) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 932})
    prose = "**Proposed result** — Keep `__sample_id__` and `1. first 2. second`, unless review finds an exception."
    entry = story_entry(tmp_path, {"Proposed Solution": MARKDOWN_STORY, "Problem": MARKDOWN_STORY},
                        prose_metadata={"implemented_summary": prose, "ordering_rationale": prose}, rationale=[prose])
    payload = {"entries": [entry]}
    if state == "runtime-fallback":
        payload["data_source"] = {"preferred_backend": "runtime", "runtime_base_url": base_url + "/markdown-runtime/"}
        page.route("**/markdown-runtime/**", lambda route: route.fulfill(status=200, content_type="application/json", body="invalid JSON"))
    page.route("**/radar-markdown.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload=payload),
    ))
    page.goto(base_url + "/radar-markdown.html", wait_until="networkidle")
    story = page.locator(".row-story")
    assert story.locator("strong").all_text_contents() == ["Proposed deliverable", "Assumption:"]
    assert story.locator("code").all_text_contents() == ["__sample_id__", "1. first 2. second"]
    assert story.locator("ul > li > ul > li").inner_text() == "Keep 1. first 2. second literally."
    assert "this is a proposed acceptance check, not a passing result." in story.inner_text()
    assert "**" not in story.inner_text() and "`" not in story.inner_text()
    assert story.locator("a, input, img, script, [id], [name]").count() == 0
    assert story.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    detail = page.locator("#detail .block-problem")
    assert detail.locator("a").get_attribute("href") == "docs/review_(draft).md"
    assert detail.locator("code").all_text_contents() == ["__sample_id__", "1. first 2. second"]
    for heading in ("Decision Basis", "Ordering Rationale", "Implemented Summary"):
        block = page.locator("#detail .split-card" if heading == "Decision Basis" else "#detail .block").filter(
            has=page.get_by_role("heading", name=heading, exact=True),
        )
        assert block.locator("code").all_text_contents() == ["__sample_id__", "1. first 2. second"]
        assert "unless review finds an exception." in block.inner_text()
    screenshot = _failure_screenshot_path(f"radar-markdown-{width}-{state}")
    if screenshot is not None:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.evaluate("""() => {
            const top = document.querySelector('.list-panel').getBoundingClientRect().top + window.scrollY;
            window.scrollTo(0, top - document.querySelector('.controls').getBoundingClientRect().height - 36);
        }""")
        page.screenshot(path=str(screenshot))
    standalone = backlog_detail_pages._render_idea_spec_html(
        repo_root=tmp_path, index_output_path=tmp_path / "radar.html", entry=entry,
    )
    page.route("**/standalone-markdown.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=standalone,
    ))
    page.goto(base_url + "/standalone-markdown.html", wait_until="networkidle")
    section = page.locator("section.block").filter(has=page.get_by_role("heading", name="Proposed Solution", exact=True))
    assert section.locator("strong").all_text_contents() == ["Proposed deliverable", "Assumption:"]
    assert section.locator("a").get_attribute("href") == "docs/review_(draft).md"
    assert section.locator("code").all_text_contents() == ["__sample_id__", "1. first 2. second"]
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "runtime-fallback"])
def test_plain_story_fallback_survives_list_delivery(
    tmp_path: Path, browser_context, width: int, state: str,
) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
    attack = '<img src="x" onerror="window.__storyInjected=true"> [link](javascript:alert(1))'
    blocks = [AUTHORED_BLOCK, "Proposed deliverable — Preserve failed-run observations; do not infer approval", attack, ""]
    entries = []
    for index, block in enumerate(blocks):
        sections = {"Problem": "Assumption — One reviewable project record.", "Proposed Solution": block} if block else {}
        entry = story_entry(tmp_path / str(index), sections)
        entry.pop("story_html", None)  # The rich payload can be absent on a fallback response.
        entry.update(idea_id=f"B-{index + 1:03}", title=f"Prove source block {index + 1}", rank=str(index + 1))
        entries.append(entry)
    payload = {"entries": entries}
    fallback_requests = []
    if state == "runtime-fallback":
        payload["data_source"] = {"preferred_backend": "runtime", "runtime_base_url": base_url + "/story-runtime/"}

        def unavailable_runtime(route) -> None:
            fallback_requests.append(route.request.url)
            route.fulfill(status=200, content_type="application/json", body="invalid JSON")

        page.route("**/story-runtime/**", unavailable_runtime)
    page.route("**/radar-stories.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload=payload),
    ))
    page.goto(base_url + "/radar-stories.html", wait_until="networkidle")
    for index, block in enumerate(blocks):
        story = page.locator(f'button[data-idea-id="B-{index + 1:03}"] .row-story')
        story.wait_for()
        assert story.locator(".row-story-text").inner_text() == (block or "No authored workstream summary yet.")
        if block:
            assert story.locator(".row-story-source").inner_text() == "Proposed Solution"
        assert story.locator("script, img, a, [onerror]").count() == 0
        assert story.evaluate("node => node.scrollWidth <= node.clientWidth + 1")
        assert story.locator(".row-story-text").evaluate("node => getComputedStyle(node).whiteSpace") == "pre-wrap"
    assert page.evaluate("window.__storyInjected === undefined")
    assert page.locator("body").evaluate("node => node.scrollWidth <= node.clientWidth + 1")
    if state == "runtime-fallback":
        assert any("surfaces/backlog/list" in url for url in fallback_requests)
    screenshot = _failure_screenshot_path(f"radar-authored-story-{width}-{state}")
    if screenshot is not None:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
        if width == 430:
            page.evaluate("""() => {
                const top = document.querySelector('.list-panel').getBoundingClientRect().top + window.scrollY;
                window.scrollTo(0, top - document.querySelector('.controls').getBoundingClientRect().height - 36);
            }""")
            assert page.locator("#list").bounding_box()["y"] > page.locator(".controls").bounding_box()["y"] + page.locator(".controls").bounding_box()["height"]
            page.screenshot(path=str(screenshot.with_stem(screenshot.stem + "-reading")))
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
def test_long_authored_block_remains_reachable_in_windowed_list(browser_context, width: int) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 932})
    source = (AUTHORED_BLOCK + "\n\n") * 40 + "Complete final condition remains here"
    entries = [{
        "idea_id": f"B-{index + 1:03}", "title": f"Authored workstream {index + 1}", "section": "active",
        "status": "queued", "rank": str(index + 1), "story_source": "Proposed Solution",
        "story_text": source if index == 0 else f"Proposed deliverable — Preserve record {index + 1}",
    } for index in range(185)]
    page.route("**/radar-long-stories.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload={"entries": entries}),
    ))
    page.goto(base_url + "/radar-long-stories.html", wait_until="networkidle")
    first = page.locator('button[data-idea-id="B-001"]')
    assert first.locator(".row-story-text").inner_text() == source
    first_height = first.evaluate("node => node.getBoundingClientRect().height")
    assert first_height > 640
    page.locator("#list").evaluate("(node, y) => {node.scrollTop = y;}", first_height - 300)
    page.wait_for_timeout(100)
    assert first.count() == 1
    last_text = first.locator(".row-story-text").evaluate("""node => {
        const range=document.createRange(); range.setStart(node.firstChild, node.textContent.lastIndexOf('Complete final'));
        range.setEnd(node.firstChild, node.textContent.length);
        const box=range.getBoundingClientRect(), clip=node.closest('#list').getBoundingClientRect();
        return {top:box.top,bottom:box.bottom,clipTop:clip.top,clipBottom:clip.bottom};
    }""")
    assert last_text["clipTop"] <= last_text["top"] < last_text["bottom"] <= last_text["clipBottom"], last_text
    page.set_viewport_size({"width": 430 if width == 1440 else 1440, "height": 932})
    page.wait_for_timeout(100)
    assert first.count() == 1
    assert first.evaluate("""node => {
        const box=node.getBoundingClientRect(), clip=node.closest('#list').getBoundingClientRect();
        return box.top < clip.bottom && box.bottom > clip.top;
    }""")
    page.locator("#list").evaluate("node => {node.scrollTop = 0;}")
    page.wait_for_timeout(100)
    assert first.locator(".row-story-text").inner_text() == source
    assert page.locator("#list .row").count() < len(entries)
    page.locator("#list").evaluate("node => {node.scrollTop = node.scrollHeight;}")
    page.wait_for_timeout(100)
    last = page.locator('button[data-idea-id="B-185"]')
    assert last.locator(".row-story-text").inner_text() == "Proposed deliverable — Preserve record 185"
    assert last.evaluate("""node => {
        const box=node.getBoundingClientRect(), clip=node.closest('#list').getBoundingClientRect();
        return box.top >= clip.top && box.bottom <= clip.bottom;
    }""")
    assert page.locator("#list .row").count() < len(entries)
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("select_visible", [True, False], ids=["visible-selection", "offscreen-selection"])
def test_resize_keeps_the_visible_workstream_anchored(browser_context, select_visible: bool) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": 1440, "height": 932})
    entries = [{
        "idea_id": f"B-{index + 1:03}", "title": f"Authored workstream {index + 1}", "section": "active",
        "status": "queued", "rank": str(index + 1), "story_source": "Proposed Solution",
        "story_text": AUTHORED_BLOCK * 15 if index == 0 else f"Proposed deliverable — Preserve record {index + 1}",
    } for index in range(185)]
    page.route("**/radar-resize-stories.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload={"entries": entries}),
    ))
    page.goto(base_url + "/radar-resize-stories.html", wait_until="networkidle")
    page.locator("#list").evaluate("node => {node.scrollTop = node.scrollHeight / 2;}")
    page.wait_for_timeout(100)
    selected_id = page.locator("#list").evaluate("""list => {
        const clip=list.getBoundingClientRect();
        return [...list.querySelectorAll('.row')].find(row => {
            const box=row.getBoundingClientRect(); return box.top >= clip.top && box.bottom <= clip.bottom;
        }).dataset.ideaId;
    }""")
    selected = page.locator(f'button[data-idea-id="{selected_id}"]')
    if select_visible:
        selected.click()
    assert ("active" in selected.get_attribute("class").split()) == select_visible
    offset = selected.evaluate("node => node.getBoundingClientRect().top - node.closest('#list').getBoundingClientRect().top")
    for width in (430, 1440):
        page.set_viewport_size({"width": width, "height": 932})
        page.wait_for_timeout(100)
        assert selected.count() == 1
        actual = selected.evaluate("""node => {
            const box=node.getBoundingClientRect(), clip=node.closest('#list').getBoundingClientRect();
            return {offset:box.top-clip.top, visible:box.top >= clip.top && box.bottom <= clip.bottom};
        }""")
        assert actual["visible"], actual
        assert abs(actual["offset"] - offset) <= 2, (offset, actual)
        assert ("active" in selected.get_attribute("class").split()) == select_visible
        assert page.locator("#list .row").count() < len(entries)
    _assert_clean_page(page, *errors)


def test_detail_fallback_preserves_complete_source_blocks(browser_context) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    entry = {
        "idea_id": "B-001", "title": "Full source detail", "section": "active", "status": "queued",
        "rank": "1", "story_source": "Proposed Solution", "story_text": AUTHORED_BLOCK,
        "problem": AUTHORED_BLOCK, "founder_pov": AUTHORED_BLOCK, "success_metrics": AUTHORED_BLOCK,
        "rationale_bullets": [AUTHORED_BLOCK],
    }
    page.route("**/radar-source-detail.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload={"entries": [entry]}),
    ))
    page.goto(base_url + "/radar-source-detail.html", wait_until="networkidle")
    detail = page.locator("#detail")
    for heading in ("Problem", "Product View", "Success Metrics", "Decision Basis"):
        block = detail.locator(".block").filter(has=page.get_by_role("heading", name=heading, exact=True))
        if heading in {"Product View", "Decision Basis"}:
            block = detail.locator(".split-card").filter(has=page.get_by_role("heading", name=heading, exact=True))
        assert block.locator("p.source-text").inner_text() == AUTHORED_BLOCK
    _assert_clean_page(page, *errors)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("count", [3, 185], ids=["complete-list", "windowed-list"])
@pytest.mark.parametrize("cover", ["surface", "shell"])
def test_visible_row_click_reaches_long_source_and_refuses_obstruction(
    browser_context, width: int, count: int, cover: str,
) -> None:
    base_url, context = browser_context
    page, *errors = _new_page(context)
    page.set_viewport_size({"width": width, "height": 932})
    source = (AUTHORED_BLOCK + "\n\n") * 40 + "The final condition is still required."
    entries = [{
        "idea_id": f"B-{index + 1:03}", "title": f"Authored workstream {index + 1}", "section": "active",
        "status": "queued", "rank": str(index + 1), "story_source": "Proposed Solution",
        "story_text": source if index == 1 else f"Preserve record {index + 1}",
    } for index in range(count)]
    page.route("**/radar-pointer.html", lambda route: route.fulfill(
        status=200, content_type="text/html", body=html_runtime._render_html(payload={"entries": entries}),
    ))
    page.route("**/pointer-shell.html", lambda route: route.fulfill(
        status=200, content_type="text/html",
        body='<html><body style="margin:0"><header style="height:100px">Governance</header>'
             '<iframe id="radar" src="radar-pointer.html" style="border:0;width:100%;height:800px"></iframe></body></html>',
    ))
    page.goto(base_url + "/pointer-shell.html", wait_until="networkidle")
    radar = page.frame_locator("#radar")
    button = radar.locator('button[data-idea-id="B-002"]')
    assert button.locator(".row-story-text").inner_text() == source
    assert button.evaluate("node => node.clientHeight > node.closest('#list').clientHeight")
    radar.locator("body").evaluate("""node => {
        window.__rowClicks = [];
        node.addEventListener('click', event => window.__rowClicks.push({
            trusted: event.isTrusted, id: event.target.closest('[data-idea-id]')?.dataset.ideaId,
        }), true);
    }""")
    _click_visible_radar_row(button)
    radar.locator('button[data-idea-id="B-002"].active').wait_for()
    assert radar.locator('#detail [data-kpi="workstream-id"] .v').inner_text() == "B-002"
    assert radar.locator("body").evaluate("() => window.__rowClicks") == [{"trusted": True, "id": "B-002"}]
    assert button.locator(".row-story-text").inner_text() == source
    covered_body = radar.locator("body") if cover == "surface" else page.locator("body")
    covered_body.evaluate("""node => {
        const obstruction = document.createElement('div');
        obstruction.id = 'pointer-obstruction';
        obstruction.style.cssText = 'position:fixed;inset:0;z-index:2147483647;background:white';
        node.append(obstruction);
    }""")
    with pytest.raises(AssertionError, match="clipped or obstructed"):
        _click_visible_radar_row(radar.locator('button[data-idea-id="B-001"]'))
    assert radar.locator("body").evaluate("() => window.__rowClicks") == [{"trusted": True, "id": "B-002"}]
    assert radar.locator('#detail [data-kpi="workstream-id"] .v').inner_text() == "B-002"
    covered_body.locator("#pointer-obstruction").evaluate("node => node.remove()")
    _click_visible_radar_row(radar.locator('button[data-idea-id="B-001"]'))
    radar.locator('button[data-idea-id="B-001"].active').wait_for()
    assert radar.locator('#detail [data-kpi="workstream-id"] .v').inner_text() == "B-001"
    assert radar.locator("body").evaluate("() => window.__rowClicks") == [
        {"trusted": True, "id": "B-002"}, {"trusted": True, "id": "B-001"},
    ]
    _assert_clean_page(page, *errors)
