from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
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
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _apply_ready_greenfield_fixture,
    _seed_empty_governance_repo,
)


def _write_greenfield_project_page(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(
        greenfield_apply_write.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_component_commit.component_authoring.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_write,
        "_raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {},
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
    assert payload["projection"]["origin"] == "accepted greenfield project"
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
    page.locator(".project-host-handoff").wait_for(timeout=15000)
    surface_text = page.locator(".project-surface").inner_text()
    assert "Product Story" in surface_text
    assert "Risks" in surface_text
    assert "Project not defined yet" not in surface_text
    assert "Current orienting work" not in surface_text
    assert "Mockrepo" not in surface_text
    assert "Accepted first-path scenario" not in surface_text
    assert "Checkout" in surface_text or "checkout" in surface_text
    assert "Start source creation" in surface_text
    assert "Human " + "takeaway" not in surface_text
    assert "First source creation sequence" in surface_text
    assert "Choose implementation language" in surface_text
    assert "Create first implementation plan" in surface_text
    assert "Build smallest runnable slice" in surface_text
    assert "Add tests and proof" in surface_text
    assert "Refresh governed records" in surface_text
    assert "Do not edit source yet" in surface_text
    assert "Topology spine" not in surface_text
    assert "How the story becomes governance" not in surface_text
    assert "Status now" not in surface_text
    assert "Where does this stand" not in surface_text
    assert "Who uses it?" not in surface_text
    assert page.locator(".project-state-grid").count() == 0
    assert page.locator(".project-scenario").count() == 0
    assert page.locator(".project-risks").count() == 1
    assert page.locator(".project-risk-card").count() >= 1
    assert page.locator(".project-answer-strip").count() == 0
    assert page.locator('.project-job-card a[href*="tab=radar"][href*="workstream="]').count() >= 1
    assert page.locator(".project-job-card em").count() == 0

    chip_contract = page.locator(".project-job-card .project-workstream-chip").first.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderRadius: style.borderRadius,
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
            };
        }"""
    )
    assert chip_contract == {
        "borderRadius": "999px",
        "fontSize": "12px",
        "fontWeight": "500",
        "paddingTop": "1px",
        "paddingRight": "8px",
    }
    label_contract = page.locator(".project-job-card .project-label-chip").first.evaluate(
        """(node) => {
            const style = window.getComputedStyle(node);
            return {
              borderRadius: style.borderRadius,
              fontSize: style.fontSize,
              fontWeight: style.fontWeight,
              paddingTop: style.paddingTop,
              paddingRight: style.paddingRight,
            };
        }"""
    )
    assert label_contract == {
        "borderRadius": "4px",
        "fontSize": "12px",
        "fontWeight": "700",
        "paddingTop": "4px",
        "paddingRight": "10px",
    }

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
              promptLefts: cards.map((card) => Math.round(card.getBoundingClientRect().left)),
              promptTops: cards.map((card) => Math.round(card.getBoundingClientRect().top)),
            };
        }"""
    )
    assert handoff_layout["cardCount"] == 5
    assert handoff_layout["stepCount"] == 5
    assert handoff_layout["codeFontSize"] == "14px"
    assert int(handoff_layout["scrollDelta"]) <= 4
    assert int(handoff_layout["maxCardOverflow"]) <= 4
    assert int(handoff_layout["maxStepOverflow"]) <= 4
    assert len(set(handoff_layout["promptLefts"])) == 1
    assert handoff_layout["promptTops"] == sorted(handoff_layout["promptTops"])

    story_layout = page.locator(".project-story-narrative").evaluate(
        """(node) => {
            const narrativeParagraphs = Array.from(node.querySelectorAll(":scope > p"));
            const list = node.querySelector(".project-story-records");
            const contract = node.querySelector(".project-story-contract-card p");
            const rows = Array.from(node.querySelectorAll(".project-story-contract-card"));
            return {
              narrativeParagraphCount: narrativeParagraphs.length,
              listFontSize: list ? window.getComputedStyle(list).fontSize : "",
              contractFontSize: contract ? window.getComputedStyle(contract).fontSize : "",
              rowCount: rows.length,
              rowLefts: rows.map((row) => Math.round(row.getBoundingClientRect().left)),
              rowTops: rows.map((row) => Math.round(row.getBoundingClientRect().top)),
              firstRowColumns: rows[0] ? window.getComputedStyle(rows[0]).gridTemplateColumns : "",
              scrollDelta: node.scrollWidth - node.clientWidth,
            };
        }"""
    )
    assert story_layout["narrativeParagraphCount"] == 0
    assert story_layout["listFontSize"] == ""
    assert story_layout["contractFontSize"] == "14px"
    assert story_layout["rowCount"] == 5
    assert len(set(story_layout["rowLefts"])) == 1
    assert story_layout["rowTops"] == sorted(story_layout["rowTops"])
    assert story_layout["firstRowColumns"] != ""
    assert int(story_layout["scrollDelta"]) <= 4


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
