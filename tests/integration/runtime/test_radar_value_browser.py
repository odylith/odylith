from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.surfaces import render_backlog_ui
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _failure_screenshot_path,
    _new_page,
    browser_context,
)


def test_radar_html_escaping_preserves_values_and_missing_blanks(browser_context) -> None:  # noqa: ANN001
    _base_url, context = browser_context
    with _new_page(context) as (page, observation):
        html = render_backlog_ui._render_html(payload={"entries": []})  # noqa: SLF001
        escape_function = html[
            html.index("    function escapeHtml(value) {"):
            html.index("    function rowStorySummary(row) {")
        ]
        cases = [
            (0, "0"), (False, "false"), (True, "true"), (3, "3"), (-2.5, "-2.5"),
            (None, ""), ("", ""), ("  ", "  "), ("0", "0"),
            ("<b title=\"café\">'&</b>", "&lt;b title=&quot;café&quot;&gt;&#039;&amp;&lt;/b&gt;"),
        ]
        for value, expected in cases:
            assert page.evaluate(f"value => {{ {escape_function} return escapeHtml(value); }}", value) == expected
        assert page.evaluate(f"() => {{ {escape_function} return escapeHtml(); }}") == ""
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "runtime-fallback"])
def test_radar_selected_detail_text_fits_its_clipping_ancestors(
    browser_context, width: int, state: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        final_sentence = "The reader can reach the complete final sentence without hidden horizontal scrolling."
        payload = {"entries": [{
            "idea_id": "B-001", "title": "Review complete project proposals before publication",
            "section": "execution", "status": "implementation", "ordering_score": 100,
            "idea_date": "2026-05-02", "execution_start_date": "2026-06-25",
            "execution_duration_days": 74, "idea_age_days": 128, "confidence": "high",
            "priority": "P1", "sizing": "L", "complexity": "High",
            "impacted_parts": "web,planner,catalog,reporting,notifications,publication,review,coordination",
            "registry_components": [{"component_id": "publication-coordination", "name": "Publication Coordination Engine"}],
            "promoted_to_plan_ui_href": "../plans/publication-review.html",
            "rationale_bullets": [
                "why now: readers need complete source-grounded evidence before publication",
                "expected outcome: independent review preserves the complete governance contract",
                "tradeoff: release waits until the reviewed package is verified",
                "deferred for now: optional integrations wait until the core reading experience is reliable",
            ],
            "execution_state": "active", "execution_state_meta": {"source_ts_iso": "2026-09-07T12:15:00Z"},
            "problem": "Readers must be able to inspect the complete proposal before deciding whether to publish it.",
            "product_view": "A selected workstream presents its intent, evidence and success criteria together.",
            "success_metrics": (
                "Every supported request produces a faithful and reviewable proposal or an explicit failure. "
                "The entire success criterion remains readable in the selected workstream detail. " + final_sentence
            ),
        }]}
        fallback_requests = []
        if state == "runtime-fallback":
            payload["data_source"] = {"preferred_backend": "runtime", "runtime_base_url": base_url + "/reading-runtime/"}

            def unavailable_runtime(route) -> None:  # noqa: ANN001
                fallback_requests.append(route.request.url)
                route.fulfill(status=200, content_type="application/json", body="invalid JSON")

            page.route("**/reading-runtime/**", unavailable_runtime)
        html = render_backlog_ui._render_html(payload=payload)  # noqa: SLF001
        page.route("**/odylith/radar/radar.html*", lambda route: route.fulfill(
            status=200, content_type="text/html", body=html,
        ))
        page.goto(base_url + "/odylith/index.html?tab=radar&workstream=B-001", wait_until="networkidle")
        for selector in ("#upgradeSpotlightDismiss", "#welcomeDismiss", "#gridBriefClose", "#odylithClose"):
            control = page.locator(selector)
            if control.count() and control.first.is_visible():
                control.first.click()
        frame = page.frame_locator("#frame-radar")
        detail = frame.locator("#detail")
        metrics = detail.locator(".block").filter(has=frame.get_by_role("heading", name="Success Metrics", exact=True))
        paragraph = metrics.locator("p").first
        paragraph.wait_for(state="attached")
        # Only vertical wheel input: scrollIntoView can conceal clipping by scrolling a hidden-overflow ancestor.
        page.mouse.move(width - 110, 650)
        for _ in range(40):
            bounds = paragraph.bounding_box()
            if bounds and 410 <= bounds["y"] and bounds["y"] + bounds["height"] < page.viewport_size["height"] - 12:
                break
            page.mouse.wheel(0, min(650, bounds["y"] - 490) if bounds else 650)
            page.wait_for_timeout(70)
        assert bounds and 410 <= bounds["y"] and bounds["y"] + bounds["height"] < page.viewport_size["height"] - 12, bounds
        assert final_sentence in metrics.inner_text()
        geometry = detail.evaluate("""detail => {
        const rect = node => {const r = node.getBoundingClientRect(); return {left:r.left, right:r.right, width:r.width};};
        const panel = detail.closest('.detail-panel');
        const style = getComputedStyle(detail);
        const clipping = [];
        for (let node=detail; node; node=node.parentElement) {
            if (['hidden','clip','auto','scroll'].includes(getComputedStyle(node).overflowX)) clipping.push(node);
        }
        const blockOverflows = Array.from(detail.children).filter(node => {
            const box=rect(node); return clipping.some(owner => box.left < rect(owner).left-1 || box.right > rect(owner).right+1);
        }).map(node => ({class:node.className, ...rect(node)}));
        const textOverflows = [];
        for (const p of detail.querySelectorAll('.block p')) {
            const range=document.createRange(); range.selectNodeContents(p);
            for (const box of range.getClientRects()) for (let owner=p.parentElement; owner; owner=owner.parentElement) {
                if (['hidden','clip','auto','scroll'].includes(getComputedStyle(owner).overflowX)) {
                    const clip=rect(owner);
                    if (box.left < clip.left-1 || box.right > clip.right+1) textOverflows.push({text:p.innerText,left:box.left,right:box.right,clip});
                }
            }
        }
        return {blockOverflows,textOverflows,panelClient:panel.clientWidth,panelScroll:panel.scrollWidth,
            track:parseFloat(style.gridTemplateColumns),budget:detail.clientWidth-parseFloat(style.paddingLeft)-parseFloat(style.paddingRight),
            ancestorScrollLeft:clipping.map(node => node.scrollLeft)};
    }""")
        screenshot = _failure_screenshot_path(f"radar-detail-reading-{width}-{state}")
        if screenshot is not None:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot))
            screenshot.with_suffix(".json").write_text(json.dumps(geometry, indent=2) + "\n")
        assert not geometry["blockOverflows"], geometry
        assert not geometry["textOverflows"], geometry
        assert geometry["panelScroll"] <= geometry["panelClient"] + 1, geometry
        assert geometry["track"] <= geometry["budget"] + 1, geometry
        assert not any(geometry["ancestorScrollLeft"]), geometry
        if state == "runtime-fallback":
            assert any("surfaces/backlog/list" in url for url in fallback_requests)
            assert any("surfaces/backlog/detail" in url for url in fallback_requests)
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("viewport", [(1440, 1100), (390, 844)], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "empty", "runtime-fallback"])
def test_radar_zero_counts_and_score_are_visible(
    browser_context, viewport: tuple[int, int], state: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": viewport[0], "height": viewport[1]})
        entries = [] if state == "empty" else [{
            "idea_id": "B-001", "title": "Zero-score fixture", "section": "active",
            "status": "queued", "ordering_score": 0, "idea_age_days": "0",
            "priority": "P2", "sizing": "S", "complexity": "Low",
        }]
        payload = {
            "entries": entries,
            "execution_waves": {"summary": {"program_count": 1, "active_wave_count": 0}},
        }
        fallback_requests = []
        if state == "runtime-fallback":
            payload["data_source"] = {
                "preferred_backend": "runtime", "runtime_base_url": base_url + "/radar-runtime/",
            }

            def unavailable_runtime(route) -> None:  # noqa: ANN001
                fallback_requests.append(route.request.url)
                route.fulfill(status=200, content_type="application/json", body="invalid JSON")

            page.route("**/radar-runtime/**", unavailable_runtime)
        html = render_backlog_ui._render_html(payload=payload)  # noqa: SLF001
        page.route("**/radar-values.html", lambda route: route.fulfill(
            status=200, content_type="text/html", body=html,
        ))
        response = page.goto(base_url + "/radar-values.html", wait_until="networkidle")
        assert response is not None and response.ok
        expected = {"Queued": str(len(entries)), "Execution": "0", "Parked": "0", "Finished": "0", "Active Waves": "0"}
        for label, value in expected.items():
            card = page.locator("#stats .stat").filter(has=page.locator(".label", has_text=label))
            number = card.locator(".value")
            number.scroll_into_view_if_needed()
            assert number.is_visible()
            assert number.inner_text() == value
        assert page.locator("#stats .stat").filter(has_text="Index Updated").locator(".value").inner_text() == "-"
        if entries:
            score = page.locator("#detail .kpi").filter(has=page.locator(".k", has_text="Ordering Score")).locator(".v")
            score.scroll_into_view_if_needed()
            assert score.is_visible()
            assert score.inner_text() == "0"
        else:
            assert page.locator("#detail").get_attribute("hidden") == ""
            assert page.locator("#detail").inner_text() == ""
            assert page.locator("#list button[data-idea-id]").count() == 0
        if state == "runtime-fallback":
            assert any("surfaces/backlog/list" in url for url in fallback_requests)
            assert any("surfaces/backlog/detail" in url for url in fallback_requests)
        _assert_clean_page(page, observation)


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("document_kind", ["plan", "spec"])
def test_radar_standalone_documents_wrap_complete_unbroken_text(
    browser_context, tmp_path: Path, width: int, document_kind: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        opaque_reference = "aB7" * 80
        paragraph = f"Reference {opaque_reference} must remain readable in full."
        checkbox = f"Verify {opaque_reference} before recording success."
        source = tmp_path / "reading.md"
        source.write_text(
            "---\nidea_id: B-995\ntitle: Reading record\nstatus: queued\n---\n\n"
            f"## Validation\n{paragraph}\n\n## Rollout\n- [ ] {checkbox}\n",
            encoding="utf-8",
        )
        entry = {"idea_id": "B-995", "title": "Reading record",
                 "idea_file": "reading.md", "promoted_to_plan_file": "reading.md"}
        renderer = (render_backlog_ui._render_plan_html if document_kind == "plan"
                    else render_backlog_ui._render_idea_spec_html)
        html = renderer(repo_root=tmp_path, index_output_path=tmp_path / "radar.html", entry=entry)
        page.route("**/standalone-radar.html", lambda route: route.fulfill(
            status=200, content_type="text/html", body=html,
        ))
        response = page.goto(base_url + "/standalone-radar.html", wait_until="networkidle")
        assert response is not None and response.ok
        paragraph_node = page.locator(".block").filter(
            has=page.get_by_role("heading", name="Validation", exact=True),
        ).locator("p")
        checkbox_node = page.locator(".check-text")
        assert paragraph_node.count() == checkbox_node.count() == 1
        assert paragraph_node.inner_text() == paragraph
        assert checkbox_node.inner_text() == checkbox
        assert page.locator('input[type="checkbox"]').count() == 1
        geometry = page.locator("body").evaluate("""body => {
        const doc=body.ownerDocument, viewport=doc.documentElement.clientWidth;
        const targets=Array.from(body.querySelectorAll('.block p,.check-text'));
        const textOverflows=[], hiddenText=[], horizontalScroll=[];
        for (const target of targets) {
            const style=getComputedStyle(target);
            if (style.display==='none'||style.visibility==='hidden'||parseInt(style.webkitLineClamp||'0',10)>0)
                hiddenText.push(target.innerText);
            const range=doc.createRange(); range.selectNodeContents(target);
            for (const box of range.getClientRects()) {
                if (box.left < -1 || box.right > viewport+1)
                    textOverflows.push({text:target.innerText,left:box.left,right:box.right,viewport});
                for (let owner=target;owner;owner=owner.parentElement) {
                    const clip=owner.getBoundingClientRect(), css=getComputedStyle(owner);
                    if (['hidden','clip','auto','scroll'].includes(css.overflowX) &&
                        (box.left<clip.left-1||box.right>clip.right+1))
                        hiddenText.push({text:target.innerText,owner:owner.className,axis:'x'});
                    if (['hidden','clip'].includes(css.overflowY) &&
                        (box.top<clip.top-1||box.bottom>clip.bottom+1))
                        hiddenText.push({text:target.innerText,owner:owner.className,axis:'y'});
                }
            }
            for (let owner=target;owner;owner=owner.parentElement) horizontalScroll.push(owner.scrollLeft);
        }
        return {viewport,bodyScrollWidth:body.scrollWidth,textOverflows,hiddenText,horizontalScroll};
    }""")
        screenshot = _failure_screenshot_path(f"radar-standalone-{document_kind}-{width}")
        if screenshot is not None:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot), full_page=True)
            screenshot.with_suffix(".json").write_text(json.dumps(geometry, indent=2) + "\n")
        assert not geometry["textOverflows"], geometry
        assert not geometry["hiddenText"], geometry
        assert geometry["bodyScrollWidth"] <= geometry["viewport"] + 1, geometry
        assert not any(geometry["horizontalScroll"]), geometry
        _assert_clean_page(page, observation)
