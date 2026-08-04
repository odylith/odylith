from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
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
    commit_precompiled_greenfield_proposal,
    stub_preconfirm_surface_refresh,
)


def _write_greenfield_project_page(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    _seed_empty_governance_repo(tmp_path)
    stub_preconfirm_surface_refresh(monkeypatch)
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
        greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh,
        "raise_for_failed_refresh",
        lambda **_kwargs: None,
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {},
    )
    proposal = _apply_ready_greenfield_fixture(tmp_path, "Build an ecommerce site with checkout recovery")
    commit_precompiled_greenfield_proposal(
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

    return _write_project_page(tmp_path / "index.html", payload)


def _write_project_page(page_path: Path, payload: dict[str, object]) -> Path:
    """Write one static Project surface using the product presenter and CSS."""

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


def _degraded_project_payload() -> dict[str, object]:
    payload = project_intelligence_presenter._fallback_payload()
    payload.update(
        {
            "mode": "operating",
            "title": "Cross-Region Permit Review and Recovery Workspace",
            "intro": (
                "The source projection is partially degraded, but every visible explanation must remain readable "
                "through the final clause on both compact and desktop screens."
            ),
            "sections": ["scenario", "trust", "state", "next"],
            "answers": [
                (
                    "What changed?",
                    "Source projection degraded",
                    (
                        "The current readout preserves the complete operator explanation, including the final "
                        "recovery condition that used to disappear inside fixed-height summary cards."
                    ),
                )
            ],
            "scenario": [
                "Current work",
                "Permit Review",
                "Recover source-backed review state",
                "One source is unavailable.",
                (
                    "The operator can inspect the surviving evidence, identify the unavailable source, and keep "
                    "the recovery boundary visible without reconstructing the missing final clause."
                ),
            ],
            "scenario_title": "Current degraded work",
            "scenario_note": "The page must expose the degraded state without hiding its recovery boundary.",
            "scenario_details": [
                (
                    "Recovery boundary",
                    "Keep the last verified permit decision visible until the unavailable source is restored.",
                )
            ],
            "current": [
                "The last verified permit decision remains available with its complete evidence explanation."
            ],
            "desired": [
                "The unavailable source returns and the operator can reconcile the next decision without ambiguity."
            ],
            "host_handoff_title": "How to continue in the host chat",
            "host_handoff_note": "Use the bounded recovery prompt after reviewing the degraded evidence.",
            "host_handoff_steps": [
                "Review the complete degraded-state explanation before starting recovery.",
                "Stop when the source boundary and proof obligation are explicit.",
            ],
            "host_handoff_prompts": [
                {
                    "label": "Prepare bounded recovery",
                    "when": "Use after the unavailable source is identified.",
                    "prompt": (
                        "Odylith, prepare a bounded recovery plan that preserves the last verified decision and "
                        "names the exact source evidence required before replacement state is accepted."
                    ),
                    "result": "A reviewable recovery plan with a complete source and proof boundary.",
                    "stop": "Stop before changing product or governance truth.",
                }
            ],
        }
    )
    return payload


def _clipped_project_text(page) -> list[str]:  # noqa: ANN001
    return page.locator(".project-surface").evaluate(
        """(root) => Array.from(root.querySelectorAll("h1, h2, h3, h4, p, li, td, th, code, strong, span"))
          .filter((node) => {
            let current = node;
            while (current && root.contains(current)) {
              const style = window.getComputedStyle(current);
              if (style.display === "none" || style.visibility === "hidden") return false;
              const clipsX = style.overflowX === "hidden" || style.overflowX === "clip";
              const clipsY = style.overflowY === "hidden" || style.overflowY === "clip";
              const lineClamp = Number.parseInt(style.webkitLineClamp || "0", 10);
              if ((clipsX && current.scrollWidth > current.clientWidth + 1)
                || (clipsY && current.scrollHeight > current.clientHeight + 1)
                || lineClamp > 0) return true;
              current = current.parentElement;
            }
            return false;
          })
          .map((node) => String(node.innerText || node.textContent || "").trim().slice(0, 120))
          .filter(Boolean)"""
    )


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
            const bodies = rows.map((row) => String(row.querySelector("p")?.innerText || "").trim());
            return {
              narrativeParagraphCount: narrativeParagraphs.length,
              listFontSize: list ? window.getComputedStyle(list).fontSize : "",
              contractFontSize: contract ? window.getComputedStyle(contract).fontSize : "",
              rowCount: rows.length,
              distinctBodyCount: new Set(bodies.map((body) => body.toLocaleLowerCase())).size,
              semanticSlots: rows.map((row) => String(row.dataset.semanticSlot || "")),
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
    assert story_layout["distinctBodyCount"] == 5
    assert story_layout["semanticSlots"] == [
        "user_problem",
        "first_path",
        "product_boundary",
        "owned_capabilities",
        "proof",
    ]
    assert len(set(story_layout["rowLefts"])) == 1
    assert story_layout["rowTops"] == sorted(story_layout["rowTops"])
    assert story_layout["firstRowColumns"] != ""
    assert int(story_layout["scrollDelta"]) <= 4

    assert _clipped_project_text(page) == []


def _assert_project_sections_do_not_overflow(page, selectors: list[str]) -> None:  # noqa: ANN001
    assert _clipped_project_text(page) == []
    for selector in selectors:
        locator = page.locator(selector)
        assert locator.count() >= 1
        overflow = locator.evaluate_all(
            """(nodes) => nodes.map((node) => ({
              x: node.scrollWidth - node.clientWidth,
              clamp: (() => {
                const value = Number.parseInt(window.getComputedStyle(node).webkitLineClamp || "0", 10);
                return Number.isFinite(value) ? value : 0;
              })(),
            }))"""
        )
        assert all(int(row["x"]) <= 4 for row in overflow), (selector, overflow)
        assert all(int(row["clamp"]) == 0 for row in overflow), (selector, overflow)


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


def test_project_tab_clipping_probe_detects_a_clipping_parent(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _write_greenfield_project_page(tmp_path, monkeypatch)
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 430, "height": 932})
            page, _console_errors, _page_errors, _failed_requests, _bad_responses = _new_page(context)
            try:
                response = page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                assert response is not None and response.ok
                card = page.locator(".project-story-contract-card").first
                card.evaluate("(node) => { node.style.maxHeight = '24px'; node.style.overflow = 'hidden'; }")

                assert _clipped_project_text(page)
            finally:
                context.close()


def test_project_tab_blank_and_degraded_states_wrap_at_desktop_and_mobile_widths(tmp_path: Path) -> None:
    blank = project_intelligence_builder.build_project_intelligence_payload(
        repo_root=tmp_path / "blank-repo",
        shell_payload={"shell_repo_name": "blank-repo"},
    )
    assert blank["mode"] == "blank"
    _write_project_page(tmp_path / "blank.html", blank)
    _write_project_page(tmp_path / "degraded.html", _degraded_project_payload())

    cases = (
        (
            "blank.html",
            [".project-empty-panel", ".project-empty-action", ".project-empty-preview-card"],
            "What is included now, what is excluded, and what must be proven next.",
        ),
        (
            "degraded.html",
            [".project-scenario", ".project-answer-strip", ".project-state-grid", ".project-host-handoff"],
            "Keep the last verified permit decision visible until the unavailable source is restored.",
        ),
    )
    viewports = ({"width": 1440, "height": 1100}, {"width": 430, "height": 932})

    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            for filename, selectors, terminal_text in cases:
                for viewport in viewports:
                    context = browser.new_context(viewport=viewport)
                    page, console_errors, page_errors, failed_requests, bad_responses = _new_page(context)
                    try:
                        response = page.goto(f"{base_url}/{filename}", wait_until="domcontentloaded")
                        assert response is not None and response.ok
                        assert terminal_text in page.locator(".project-surface").inner_text()
                        _assert_project_sections_do_not_overflow(page, selectors)
                        _assert_clean_page(page, console_errors, page_errors, failed_requests, bad_responses)
                    finally:
                        context.close()
