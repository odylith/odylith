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
    _assert_clean_page, _browser, _failure_screenshot_path, _new_page, _static_server,
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
    source_bytes = manifest.read_bytes()
    spec = tmp_path / "odylith/registry/source/components/radar/CURRENT_SPEC.md"
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
                page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                unavailable_requests = []
                if runtime_unavailable:
                    payload = json.loads(payload_script.split(" = ", 1)[1].rsplit(";", 1)[0])
                    # Inject only backend availability; keep the production category payload unchanged.
                    payload["data_source"] = {
                        **payload["data_source"], "preferred_backend": "runtime",
                        "runtime_base_url": base_url + "/unavailable-runtime/",
                    }
                    page.route("**/registry-payload.v1.js*", lambda route: route.fulfill(
                        status=200, content_type="application/javascript",
                        body='window["__ODYLITH_REGISTRY_DATA__"] = ' + json.dumps(payload) + ";",
                    ))

                    def unavailable(route):  # noqa: ANN001
                        unavailable_requests.append(route.request.url)
                        route.fulfill(status=503, content_type="application/json", body='{"error":"unavailable"}')

                    page.route("**/unavailable-runtime/**", unavailable)
                response = page.goto(base_url + "/odylith/index.html?tab=registry", wait_until="domcontentloaded")
                assert response is not None and response.ok
                page.get_by_role("button", name="Close starter guide").click()
                registry = page.frame_locator("#frame-registry")
                registry.locator('button[data-component="radar"]').wait_for(timeout=15000)
                assert registry.locator('#categoryFilter option[value="application"]').inner_text() == "Application (1)"
                assert registry.locator('#categoryFilter option[value="governance_engine"]').inner_text() == "Governance Engine (1)"
                assert registry.locator('button[data-component="radar"] .label').first.inner_text() == "Application"
                assert registry.locator('button[data-component="odylith"] .label').first.inner_text() == "Governance Engine"

                registry.locator("#categoryFilter").select_option("application")
                assert registry.locator("button[data-component]").count() == 1
                assert registry.locator(".group-head").inner_text() == "APPLICATION · 1"
                registry.locator("details.context-section summary").wait_for(timeout=15000)
                registry.locator("details.context-section summary").click()
                registry.get_by_text("Category: Application", exact=True).wait_for(timeout=15000)
                _assert_topology_paragraph_accessible(
                    page, registry,
                    screenshot_name=f"registry-topology-{viewport['width']}-{'fallback' if runtime_unavailable else 'normal'}",
                )
                _assert_spec_reading_accessible(
                    page, registry, width=viewport["width"], with_table=with_table,
                    screenshot_name=f"registry-spec-{viewport['width']}-{'fallback' if runtime_unavailable else 'normal'}-{'table' if with_table else 'prose'}",
                )

                registry.locator("#search").fill("no-match-category-proof")
                assert registry.locator("button[data-component]").count() == 0
                assert registry.locator(".group-head").count() == 0
                empty = registry.locator("#detail [role=status]")
                assert "No matching components" in empty.inner_text()
                assert "reset the filters" in empty.inner_text()
                registry.locator("#resetFilters").click()
                assert registry.locator("button[data-component]").count() == 2
                assert registry.locator('button[data-component="radar"] .label').first.inner_text() == "Application"
                if runtime_unavailable:
                    assert any("/surfaces/registry/detail?component=radar" in url for url in unavailable_requests)
                    assert all("/unavailable-runtime/" in row and row.startswith("503 ") for row in bad_responses)
                    bad_responses.clear()
                    console_errors[:] = [
                        row for row in console_errors
                        if not row.startswith("Failed to load resource: the server responded with a status of 503")
                    ]
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()
    assert manifest.read_bytes() == source_bytes
    assert spec.read_bytes() == spec_bytes
