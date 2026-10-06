"""Registry category fidelity across real desktop/mobile render states."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith import __version__
from odylith.install.bootstrap_assets import ensure_customer_bootstrap
from odylith.runtime.surfaces import render_registry_dashboard as renderer
from odylith.runtime.surfaces import render_tooling_dashboard
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server, browser_context,
)
from tests.unit.runtime.test_component_registry_categories import _seed_application_registry


def _assert_spec_reading_accessible(page, registry, *, width: int, with_table: bool, screenshot_name: str) -> None:  # noqa: ANN001
    registry.locator(".spec-expand > summary").click()
    doc = registry.locator(".spec-doc")
    paragraph = doc.get_by_text("Readers must see every word of this ordinary specification paragraph.", exact=True)
    paragraph.scroll_into_view_if_needed()
    geometry = doc.evaluate("""doc => {
        const disclosure = doc.closest('.spec-expand');
        const clip = disclosure.getBoundingClientRect();
        const prose = [...doc.querySelectorAll('p')];
        return {
            clientWidth: disclosure.clientWidth, scrollWidth: disclosure.scrollWidth,
            clipLeft: clip.left + disclosure.clientLeft,
            clipRight: clip.left + disclosure.clientLeft + disclosure.clientWidth,
            textRects: prose.flatMap(node => {
                const range = document.createRange(); range.selectNodeContents(node);
                return [...range.getClientRects()].map(rect => ({left: rect.left, right: rect.right}));
            }),
        };
    }""")
    screenshot = _failure_screenshot_path(screenshot_name)
    if screenshot is not None:
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot))
    assert geometry["textRects"]
    assert all(geometry["clipLeft"] - 1 <= rect["left"] and rect["right"] <= geometry["clipRight"] + 1
               for rect in geometry["textRects"]), geometry
    assert geometry["scrollWidth"] <= geometry["clientWidth"] + 1, geometry
    if with_table:
        scroller = doc.locator(".spec-table-scroll")
        assert scroller.evaluate("node => getComputedStyle(node).overflowX") == "auto"
        if width == 430:
            assert scroller.evaluate("node => node.scrollWidth > node.clientWidth")
            scroller.evaluate("node => { node.scrollLeft = node.scrollWidth; }")
            assert scroller.evaluate("node => node.scrollLeft > 0")
            assert scroller.evaluate("""node => {
                const clip = node.getBoundingClientRect();
                const last = node.querySelector('tr:last-child td:last-child').getBoundingClientRect();
                return last.right <= clip.right;
            }""")
            scroller.scroll_into_view_if_needed()
            assert scroller.evaluate("""node => {
                const range = document.createRange();
                range.selectNodeContents(node.querySelector('tr:last-child td:last-child'));
                const clip = node.getBoundingClientRect();
                node.scrollLeft += range.getBoundingClientRect().left - clip.left - 10;
                return [...range.getClientRects()].every(rect => rect.left >= clip.left && rect.right <= clip.right);
            }""")
            if screenshot is not None:
                page.screenshot(path=str(screenshot.with_stem(screenshot.stem + "-table-reading")))
    else:
        assert doc.locator(".spec-table-scroll").count() == 0
    registry.locator(".spec-expand > summary").click()


def _assert_topology_paragraph_accessible(page, registry, *, screenshot_name: str) -> None:  # noqa: ANN001
    paragraph = registry.locator(".context-row").filter(
        has=registry.get_by_text("Forensic Coverage", exact=True),
    ).locator(".context-values .desc")
    assert paragraph.inner_text() == (
        "Baseline forensic only: 1 documented spec history checkpoint. Live evidence gaps: "
        "no explicit event, no recent path match, and no mapped workstream evidence."
    )
    frame_box = page.locator("#frame-registry").bounding_box()
    filters_box = registry.locator(".registry-filters-shell").bounding_box()
    paragraph_box = paragraph.bounding_box()
    assert frame_box and filters_box and paragraph_box
    visible_top = max(frame_box["y"], filters_box["y"] + filters_box["height"]) + 16
    visible_bottom = frame_box["y"] + frame_box["height"] - 16
    target_top = (visible_top + visible_bottom - paragraph_box["height"]) / 2
    page.mouse.move(frame_box["x"] + frame_box["width"] - 8, visible_bottom)
    page.mouse.wheel(0, paragraph_box["y"] - target_top)
    page.wait_for_timeout(200)
    geometry = paragraph.evaluate("""element => {
        const section = element.closest('.context-section');
        const box = section.getBoundingClientRect();
        const range = document.createRange();
        range.selectNodeContents(element);
        return {
            clipLeft: box.left + section.clientLeft,
            clipRight: box.left + section.clientLeft + section.clientWidth,
            sectionClientWidth: section.clientWidth, sectionScrollWidth: section.scrollWidth,
            textRects: Array.from(range.getClientRects()).map(rect => ({left: rect.left, right: rect.right})),
        };
    }""")
    screenshot_path = _failure_screenshot_path(screenshot_name)
    if screenshot_path is not None:
        screenshot_path.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot_path))
    paragraph_box = paragraph.bounding_box()
    assert paragraph_box and paragraph_box["y"] >= visible_top - 1
    assert paragraph_box["y"] + paragraph_box["height"] <= visible_bottom + 1
    assert geometry["textRects"]
    assert all(
        row["left"] >= geometry["clipLeft"] - 1 and row["right"] <= geometry["clipRight"] + 1
        for row in geometry["textRects"]
    ), geometry


@pytest.mark.parametrize("viewport", [{"width": 1440, "height": 1100}, {"width": 430, "height": 932}])
@pytest.mark.parametrize("runtime_unavailable", [False, True])
@pytest.mark.parametrize("with_table", [False, True])
def test_registry_category_labels_survive_filter_empty_and_runtime_fallback(
    tmp_path: Path, viewport: dict[str, int], runtime_unavailable: bool, with_table: bool,
) -> None:
    ensure_customer_bootstrap(repo_root=tmp_path, version=__version__)
    manifest = _seed_application_registry(tmp_path)
    purpose = (
        "Maintain experiment-version bindings for consent material and supply the evidence used by the console and coordinator. "
        "Keep the experiment version, consent version, reviewer disposition and joint readiness state together for every approved dossier. "
        "Readers must retain the full responsibility, including this final boundary beyond a compact preview: "
        "either failed readiness check blocks the advertised-ready result without changing the independent approval gate."
    )
    rationale = "Consent readiness delivery: Both version and reviewer checks precede the readiness result."
    stored_purpose = (
        "Consent-material registry is a proposed logical component. Proposed responsibility: " + purpose
        if with_table else purpose
    )
    curated_description = "Odylith is a proposed logical component. Proposed responsibility: Preserve this user-authored description."
    manifest_data = json.loads(manifest.read_text())
    component = next(row for row in manifest_data["components"] if row["component_id"] == "radar")
    component.update(name="Consent-material registry", what_it_is=stored_purpose, why_tracked=rationale,
                     status="planned", qualification="candidate", sources=["intent.authored_semantics"])
    next(row for row in manifest_data["components"] if row["component_id"] == "odylith")["what_it_is"] = curated_description
    manifest.write_text(json.dumps(manifest_data, indent=2) + "\n")
    source_bytes = manifest.read_bytes()
    spec = tmp_path / "odylith/registry/source/components/radar/CURRENT_SPEC.md"
    if not with_table:
        before_triggers, trigger_section = spec.read_text().split("## Skill Triggers\n", 1)
        no_triggers = before_triggers + "## Requirements Trace\n" + trigger_section.split("## Requirements Trace\n", 1)[1]
        spec.write_text("\n".join(line for line in no_triggers.splitlines()
                                  if not line.startswith("Last updated:")) + "\n", encoding="utf-8")
    reading = (
        "\n## Reading boundary\n\nReaders must see every word of this ordinary specification paragraph.\n\n"
        + "Evidence identifier: `" + "retained_evidence_identifier_" * 8 + "`.\n"
    )
    if with_table:
        reading += "\n| Boundary | Evidence |\n| --- | --- |\n| Intake | receipt |\n"
    spec.write_text(spec.read_text() + reading, encoding="utf-8")
    spec_bytes = spec.read_bytes()
    assert renderer.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    assert render_tooling_dashboard.main(["--repo-root", str(tmp_path), "--runtime-mode", "standalone"]) == 0
    payload_script = (tmp_path / "odylith/registry/registry-payload.v1.js").read_text(encoding="utf-8")

    with _static_server(root=tmp_path) as base_url:
        for _playwright, browser in _browser():
            context = browser.new_context(viewport=viewport)
            try:
                with _new_page(context) as (page, observation):
                    unavailable_requests = []
                    payload = json.loads(payload_script.split(" = ", 1)[1].rsplit(";", 1)[0])
                    payload["counts"]["unmapped_meaningful_events"] = 2 if with_table else 0
                    if runtime_unavailable:
                        # Inject only backend availability; keep the production category payload unchanged.
                        payload["data_source"] = {
                            **payload["data_source"], "preferred_backend": "runtime",
                            "runtime_base_url": base_url + "/unavailable-runtime/",
                        }

                        def unavailable(route):  # noqa: ANN001
                            unavailable_requests.append(route.request.url)
                            route.fulfill(status=503, content_type="application/json", body='{"error":"unavailable"}')

                        page.route("**/unavailable-runtime/**", unavailable)
                    page.route("**/registry-payload.v1.js*", lambda route: route.fulfill(
                        status=200, content_type="application/javascript",
                        body='window["__ODYLITH_REGISTRY_DATA__"] = ' + json.dumps(payload) + ";",
                    ))
                    response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    page.get_by_role("button", name="Close starter guide").click()
                    registry = page.frame_locator("#frame-registry")
                    registry.locator('button[data-component="radar"]').wait_for(timeout=15000)
                    activity = registry.locator("#registryActivitySummary")
                    expected_summary = "Activity and coverage" + (" · 2 events need component links" if with_table else "")
                    assert activity.inner_text() == expected_summary
                    assert not registry.locator("#kpis").is_visible()
                    assert registry.locator("#search").evaluate("node => node.getBoundingClientRect().top < innerHeight - 40")
                    activity.focus(); activity.press("Enter")
                    assert registry.locator("#kpis").is_visible()
                    if with_table:
                        assert registry.locator(".kpi-card.warn .kpi-value").inner_text() == "2"
                    activity.press("Enter")
                    assert not registry.locator("#kpis").is_visible()
                    assert registry.locator('#categoryFilter option[value="application"]').inner_text() == "Application (1)"
                    assert registry.locator('#categoryFilter option[value="governance_engine"]').inner_text() == "Governance Engine (1)"
                    assert registry.locator('button[data-component="radar"] .label').first.inner_text() == "Application"
                    assert registry.locator('button[data-component="odylith"] .label').first.inner_text() == "Governance Engine"

                    registry.locator("#categoryFilter").select_option("application")
                    assert registry.locator("button[data-component]").count() == 1
                    assert registry.locator(".group-head").inner_text() == "APPLICATION · 1"
                    assert registry.locator(".component-name").inner_text() == "Consent-material registry"
                    assert registry.locator(".registry-subtitle").inner_text() == "Components and responsibilities"
                    assert registry.locator(".component-identity").get_by_text("Planned", exact=True).count() == 1
                    assert "radar" not in registry.locator(".component-identity").inner_text()
                    assert registry.locator(".component-purpose").inner_text() == purpose
                    assert registry.locator(".component-purpose").evaluate("""node => {
                        const box = node.getBoundingClientRect();
                        const range = document.createRange(); range.selectNodeContents(node);
                        return [...range.getClientRects()].every(rect =>
                            rect.left >= box.left - 1 && rect.right <= box.right + 1
                            && rect.top >= box.top - 1 && rect.bottom <= box.bottom + 1);
                    }""")
                    if with_table:
                        assert registry.locator(".trigger-expand").count() == 1
                        registry.locator(".trigger-expand > summary").click()
                        assert registry.locator(".trigger-list li").all_inner_texts() == [
                            "sync workstreams", "refresh backlog radar", "enforce critical odylith policies",
                        ]
                        registry.locator(".trigger-expand > summary").click()
                        assert "Last updated 2026-03-04" in registry.locator(".spec-summary-meta").inner_text()
                    else:
                        assert registry.locator(".summary-strip").inner_text() == purpose
                        assert registry.locator(".trigger-expand").count() == 0
                        assert "Last updated" not in registry.locator(".spec-summary-meta").inner_text()
                    assert "Unknown" not in registry.locator(".spec-summary-meta").inner_text()
                    registry.locator("details.context-section summary").wait_for(timeout=15000)
                    registry.locator("details.context-section summary").click()
                    registry.get_by_text("Category: Application", exact=True).wait_for(timeout=15000)
                    assert registry.get_by_text("ID: radar", exact=True).count() == 1
                    assert registry.get_by_text("Qualification: Candidate", exact=True).count() == 1
                    assert registry.get_by_text(rationale, exact=True).count() == 1
                    if with_table:
                        assert registry.get_by_text(stored_purpose, exact=True).count() == 1
                    assert registry.locator(".summary-strip").get_by_text("Forensic coverage", exact=False).count() == 0
                    _assert_topology_paragraph_accessible(
                        page, registry,
                        screenshot_name=f"registry-topology-{viewport['width']}-{'fallback' if runtime_unavailable else 'normal'}",
                    )
                    _assert_spec_reading_accessible(
                        page, registry, width=viewport["width"], with_table=with_table,
                        screenshot_name=f"registry-spec-{viewport['width']}-{'fallback' if runtime_unavailable else 'normal'}-{'table' if with_table else 'prose'}",
                    )
                    registry.locator(".spec-expand > summary").click()
                    assert registry.locator(".spec-expand-body").get_by_text("Last updated: Not documented.", exact=True).count() == (0 if with_table else 1)
                    registry.locator(".spec-expand > summary").click()

                    registry.locator("#search").fill("no-match-category-proof")
                    assert registry.locator("button[data-component]").count() == 0
                    assert registry.locator(".group-head").count() == 0
                    empty = registry.locator("#detail [role=status]")
                    assert "No matching components" in empty.inner_text()
                    assert "reset the filters" in empty.inner_text()
                    registry.locator("#resetFilters").click()
                    assert registry.locator("button[data-component]").count() == 2
                    assert registry.locator('button[data-component="radar"] .label').first.inner_text() == "Application"
                    registry.locator('button[data-component="odylith"]').click()
                    registry.get_by_text(curated_description, exact=True).wait_for(timeout=15000)
                    assert registry.locator(".component-purpose").inner_text() == curated_description
                    if runtime_unavailable:
                        assert any("/surfaces/registry/detail?component=radar" in url for url in unavailable_requests)
                        snapshot = observation.finish()
                        assert snapshot.complete and not snapshot.lifecycle_errors, snapshot
                        assert snapshot.native_result is not None and not snapshot.native_result.coverage_errors, snapshot
                        assert not snapshot.page_errors, snapshot.page_errors
                        expected_prefix = base_url + "/unavailable-runtime/"
                        assert snapshot.http_errors and all(error.status == 503 and error.url.startswith(expected_prefix)
                                                            for error in snapshot.http_errors), snapshot.http_errors
                        assert snapshot.native_failures and all(failure.http_status == 503 and failure.url.startswith(expected_prefix)
                                                                for failure in snapshot.native_failures), snapshot.native_failures
                        assert snapshot.console_errors and set(snapshot.console_errors) == {"Failed to load resource: the server responded with a status of 503 (Service Unavailable)"}, snapshot.console_errors
                    else:
                        _assert_clean_page(page, observation)
            finally:
                context.close()
    assert manifest.read_bytes() == source_bytes
    assert spec.read_bytes() == spec_bytes


@pytest.mark.parametrize("width", [1440, 430], ids=["desktop", "mobile"])
@pytest.mark.parametrize("state", ["normal", "empty-evidence", "degraded"])
def test_registry_evidence_is_optional_and_retains_exact_history(
    browser_context, width: int, state: str,
) -> None:  # noqa: ANN001
    base_url, context = browser_context
    purpose = "Keep the exact consent version and readiness disposition together before launch."
    summary = (
        "The reviewer retained the exact approved consent version, the reviewed dossier, and both launch checks. " * 4
        + "The final condition requires the coordinator's confirmation and preserves <version> & evidence."
    )
    earlier_summary = "The first spec records the experiment-version binding without changing reviewer authority."
    artifacts = [
        {"path": f"evidence/launch-check-{index}.json", "href": f"../evidence/launch-check-{index}.json"}
        for index in range(3)
    ]
    events = [
        {"kind": "validation", "summary": summary, "confidence": "high", "ts_iso": "2026-10-05T13:14:15Z",
         "workstreams": ["B-901"], "artifacts": artifacts},
        {"kind": "spec_history", "summary": earlier_summary, "confidence": "medium", "ts_iso": "2026-10-04T12:13:14Z",
         "workstreams": [], "artifacts": []},
    ] if state == "normal" else []
    component = {"component_id": "consent-registry", "name": "Consent material registry", "what_it_is": purpose,
                 "status": "planned", "qualification": "candidate", "category": "application"}
    detail = {**component, "timeline": events, "forensic_coverage": {
        "mapped_workstream_evidence_count": 1 if events else 0,
        "spec_history_event_count": 1 if events else 0, "recent_path_match_count": 0,
    }}
    with _new_page(context) as (page, observation):
        page.set_viewport_size({"width": width, "height": 1100 if width == 1440 else 932})
        requests = []

        def runtime_response(route) -> None:  # noqa: ANN001
            requests.append(route.request.url)
            if "/detail?" in route.request.url:
                route.fulfill(status=200, content_type="application/json",
                              body="invalid JSON" if state == "degraded" else json.dumps(detail))
            else:
                route.fulfill(status=200, content_type="application/json", json={"components": [component]})

        page.route("**/evidence-runtime/surfaces/**", runtime_response)
        payload = {"components": [component], "data_source": {
            "preferred_backend": "runtime", "runtime_base_url": base_url + "/evidence-runtime/",
        }}
        page.route("**/registry-evidence.html", lambda route: route.fulfill(
            status=200, content_type="text/html", body=renderer._render_html(payload=payload),  # noqa: SLF001
        ))
        response = page.goto(base_url + "/registry-evidence.html", wait_until="networkidle")
        assert response is not None and response.ok
        assert page.locator(".component-purpose").inner_text() == purpose
        assert page.locator(".component-purpose").is_visible()
        assert page.locator(".component-identity").get_by_text("Planned", exact=True).is_visible()
        warning = page.locator("#detail [role=status]")
        if state == "degraded":
            assert warning.inner_text() == "Component detail unavailable. The available summary is shown."
            assert warning.is_visible()
            assert warning.evaluate("node => node.closest('details') === null")
        else:
            assert warning.count() == 0
        evidence = page.locator("#chronology-anchor")
        assert evidence.evaluate("node => node.tagName") == "DETAILS"
        assert evidence.get_attribute("open") is None
        assert evidence.locator(":scope > summary > span").first.text_content() == "Evidence"
        assert evidence.locator("#timelineCount").text_content() == f"{len(events)} events"
        assert not page.locator("#timeline").is_visible()
        assert not page.locator(".forensic-health-card").is_visible()
        summary_control = evidence.locator(":scope > summary")
        summary_control.focus()
        summary_control.press("Enter")
        assert evidence.get_attribute("open") == ""
        assert page.locator("#timeline").is_visible()
        expected_counts = ["2", "2", "1", "1", "0"] if events else ["0"] * 5
        assert page.locator(".forensic-stat-value").all_inner_texts() == expected_counts
        if events:
            assert page.locator(".forensic-latest .forensic-summary").text_content() == summary
            assert "confidence high" in page.locator(".forensic-meta-row").inner_text()
            assert "2026-10-05T13:14:15Z" in page.locator(".forensic-meta-row").inner_text()
            assert page.locator(".forensic-workstream-chip").first.inner_text() == "B-901"
            assert "workstream=B-901" in page.locator(".forensic-workstream-chip").first.get_attribute("href")
            artifact_control = page.locator(".forensic-latest .forensic-artifact-disclosure > summary")
            artifact_control.focus()
            artifact_control.press("Enter")
            links = page.locator(".forensic-latest .artifact")
            assert links.all_inner_texts() == [item["path"] for item in artifacts]
            assert links.evaluate_all("nodes => nodes.map(node => node.getAttribute('href'))") == [item["href"] for item in artifacts]
            group_control = page.locator(".forensic-group-disclosure > summary")
            group_control.focus()
            group_control.press("Enter")
            assert page.locator(".forensic-group-row .forensic-summary").all_text_contents() == [summary, earlier_summary]
        else:
            assert page.locator("#timeline").inner_text().count("No mapped forensic evidence is attached yet.") == 1
            assert page.locator(".forensic-latest").count() == 0
        assert any("/surfaces/registry/detail?component=consent-registry" in url for url in requests)
        screenshot = _failure_screenshot_path(f"registry-evidence-{width}-{state}")
        if screenshot is not None:
            screenshot.parent.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(screenshot), full_page=True)
        _assert_clean_page(page, observation)
