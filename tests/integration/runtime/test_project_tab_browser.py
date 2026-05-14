from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.project_intelligence import assets
from odylith.runtime.project_intelligence import builder as project_intelligence_builder
from odylith.runtime.project_intelligence import presenter as project_intelligence_presenter
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _browser,
    _new_page,
    _static_server,
)
from tests.unit.runtime.test_greenfield_proposals import (
    _apply_ready_greenfield_fixture,
    _seed_empty_governance_repo,
)


def _write_greenfield_project_page(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(
        greenfield_proposals.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_proposals.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    proposal = _apply_ready_greenfield_fixture(tmp_path, "Build an ecommerce site with checkout recovery")
    greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    payload = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={},
    )
    assert payload["projection"]["origin"] == "greenfield proposal"
    assert payload["sections"][0] == "product_story"
    assert (tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json").is_file()

    page_path = tmp_path / "index.html"
    page_path.write_text(
        "\n".join(
            (
                "<!doctype html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="utf-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1">',
                "<style>",
                ":root {",
                "  --shell-bg: #eef6ff;",
                "  --ink: #1f2f46;",
                "  --ink-soft: #334155;",
                "  --muted: #52657f;",
                "  --line: #bfd7fe;",
                "  --panel: #ffffff;",
                "  --chip-bg: #eff6ff;",
                "  --chip-line: #bfd7fe;",
                "  --chip-active-ink: #1f3f8f;",
                "  --surface-shadow: 0 10px 24px rgba(23, 63, 131, 0.07);",
                "  --surface-shell-max-width: 1320px;",
                "  --surface-workstream-button-font-size: 12px;",
                "  --surface-workstream-button-font-weight: 500;",
                "  --surface-identifier-font-size: 14px;",
                "  --surface-identifier-font-weight: 500;",
                "}",
                "body { margin: 0; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #eef6ff; }",
                "</style>",
                "<style>",
                assets.load_project_tab_css(),
                "</style>",
                "</head>",
                "<body>",
                '<div class="project-pane">',
                project_intelligence_presenter.render_project_html({"project_intelligence": payload}),
                "</div>",
                '<script type="application/json" id="payload">',
                json.dumps(payload, sort_keys=True),
                "</script>",
                "</body>",
                "</html>",
            )
        ),
        encoding="utf-8",
    )
    return page_path


def _assert_greenfield_project_tab_layout(page, *, compact: bool) -> None:  # noqa: ANN001
    page.locator(".project-product-story").wait_for(timeout=15000)
    page.locator(".project-scenario").wait_for(timeout=15000)
    surface_text = page.locator(".project-surface").inner_text()
    assert "Product Story" in surface_text
    assert "Project not defined yet" not in surface_text
    assert "Current orienting work" not in surface_text
    assert "Mockrepo" not in surface_text
    assert "Proposed first-path scenario" in surface_text
    assert "Checkout" in surface_text or "checkout" in surface_text
    assert "How to continue in the host chat" in surface_text
    assert "Odylith, apply this greenfield proposal" in surface_text
    assert "Revise it" in surface_text
    assert "Reject it" in surface_text
    assert "Paste the chosen prompt into the same host chat" in surface_text
    assert "Topology spine" not in surface_text
    assert "How the story becomes governance" not in surface_text

    handoff_layout = page.locator(".project-host-handoff").evaluate(
        """(node) => {
            const cards = Array.from(node.querySelectorAll(".project-host-prompt"));
            const code = node.querySelector("code");
            const steps = Array.from(node.querySelectorAll("ol li"));
            return {
              cardCount: cards.length,
              stepCount: steps.length,
              codeFontSize: code ? window.getComputedStyle(code).fontSize : "",
              scrollDelta: node.scrollWidth - node.clientWidth,
              maxCardOverflow: cards.reduce((max, card) => Math.max(max, card.scrollWidth - card.clientWidth), 0),
              maxStepOverflow: steps.reduce((max, step) => Math.max(max, step.scrollWidth - step.clientWidth), 0),
            };
        }"""
    )
    assert handoff_layout["cardCount"] == 3
    assert handoff_layout["stepCount"] == 4
    assert handoff_layout["codeFontSize"] == "14px"
    assert int(handoff_layout["scrollDelta"]) <= 4
    assert int(handoff_layout["maxCardOverflow"]) <= 4
    assert int(handoff_layout["maxStepOverflow"]) <= 4

    story_layout = page.locator(".project-story-narrative").evaluate(
        """(node) => {
            const paragraph = node.querySelector("p");
            const list = node.querySelector(".project-story-records");
            const contract = node.querySelector(".project-story-contract dd");
            return {
              paragraphFontSize: paragraph ? window.getComputedStyle(paragraph).fontSize : "",
              paragraphLineHeight: paragraph ? window.getComputedStyle(paragraph).lineHeight : "",
              listFontSize: list ? window.getComputedStyle(list).fontSize : "",
              contractFontSize: contract ? window.getComputedStyle(contract).fontSize : "",
              scrollDelta: node.scrollWidth - node.clientWidth,
            };
        }"""
    )
    assert story_layout["paragraphFontSize"] == "14px"
    assert story_layout["listFontSize"] == "14px"
    assert story_layout["contractFontSize"] == "14px"
    assert int(story_layout["scrollDelta"]) <= 4

    scenario_layout = page.locator(".project-scenario").evaluate(
        """(node) => {
            const body = node.querySelector(".project-scenario-body");
            const cover = node.querySelector(".project-scenario-cover");
            const copy = node.querySelector(".project-scenario-copy");
            const prose = node.querySelector(".project-scenario-prose");
            const bodyBox = body ? body.getBoundingClientRect() : null;
            const coverBox = cover ? cover.getBoundingClientRect() : null;
            const copyBox = copy ? copy.getBoundingClientRect() : null;
            const proseBox = prose ? prose.getBoundingClientRect() : null;
            const copyStyle = copy ? window.getComputedStyle(copy) : null;
            return {
              bodyDisplay: body ? window.getComputedStyle(body).display : "",
              bodyColumns: body ? window.getComputedStyle(body).gridTemplateColumns : "",
              bodyWidth: bodyBox ? bodyBox.width : 0,
              coverWidth: coverBox ? coverBox.width : 0,
              copyWidth: copyBox ? copyBox.width : 0,
              proseWidth: proseBox ? proseBox.width : 0,
              copyFontSize: copyStyle ? copyStyle.fontSize : "",
              sectionScrollDelta: node.scrollWidth - node.clientWidth,
              bodyScrollDelta: body ? body.scrollWidth - body.clientWidth : 0,
            };
        }"""
    )
    assert scenario_layout["bodyDisplay"] == "grid"
    assert int(scenario_layout["sectionScrollDelta"]) <= 4
    assert int(scenario_layout["bodyScrollDelta"]) <= 4
    assert scenario_layout["copyFontSize"] == "18px"
    if compact:
        assert float(scenario_layout["copyWidth"]) >= 330
        assert abs(float(scenario_layout["proseWidth"]) - float(scenario_layout["copyWidth"])) <= 70
    else:
        assert float(scenario_layout["copyWidth"]) >= 640
        assert float(scenario_layout["coverWidth"]) >= 260
        assert float(scenario_layout["proseWidth"]) >= 600


def _run_greenfield_project_tab_browser_check(tmp_path: Path, monkeypatch, *, compact: bool) -> None:  # noqa: ANN001
    _write_greenfield_project_page(tmp_path, monkeypatch)
    viewport = {"width": 430, "height": 932} if compact else {"width": 1440, "height": 1100}
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport=viewport)
            page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
            try:
                response = page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                assert response is not None and response.ok
                _assert_greenfield_project_tab_layout(page, compact=compact)
                _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
            finally:
                context.close()


def test_project_tab_renders_accepted_greenfield_story_without_broken_layout(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _run_greenfield_project_tab_browser_check(tmp_path, monkeypatch, compact=False)


def test_project_tab_renders_accepted_greenfield_story_in_compact_browser(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _run_greenfield_project_tab_browser_check(tmp_path, monkeypatch, compact=True)
