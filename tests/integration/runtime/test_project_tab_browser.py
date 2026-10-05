from __future__ import annotations

import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import preview_project_dashboard_payload
from odylith.runtime.project_intelligence import assets
from odylith.runtime.project_intelligence import builder as project_intelligence_builder
from odylith.runtime.project_intelligence import presenter as project_intelligence_presenter
from tests.integration.runtime.surface_browser_test_support import (
    _assert_clean_page,
    _browser,
    _failure_screenshot_path,
    _new_page,
    _static_server,
)
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
)
from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import (
    _seed_empty_governance_repo,
    commit_precompiled_greenfield_proposal,
    stub_preconfirm_surface_refresh,
)
from tests.unit.runtime.test_greenfield_authored_project_dashboard import (
    PROPOSED_FIRST_RUN,
    _accepted_preview,
    _handoff_scope_proposal,
    _result_first_proposal,
    _source_launch_context,
)


def _write_greenfield_project_page(tmp_path: Path, monkeypatch) -> Path:  # noqa: ANN001
    _seed_empty_governance_repo(tmp_path)
    activate_greenfield_baseline_fixture(tmp_path)
    stub_preconfirm_surface_refresh(monkeypatch)
    monkeypatch.setattr(
        greenfield_component_commit.component_compiled_commit.owned_surface_refresh,
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
    proposal = _canonical_model_authored_greenfield_fixture(tmp_path)
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
    assert payload["projection"]["origin"] == AUTHORED_PROJECTION_ORIGIN
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
                "* { box-sizing: border-box; }",
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
    return {
            "mode": "operating",
            "title": "Cross-Region Permit Review and Recovery Workspace",
            "intro": (
                "The source projection is partially degraded, but every visible explanation must remain readable "
                "through the final clause on both compact and desktop screens."
            ),
            "sections": ["scenario", "trust", "state", "next"],
            "focus_label": "Current focus",
            "focus": "Recover the unavailable permit source.",
            "open_label": "Open risk",
            "open": ["The unavailable source cannot establish a replacement decision."],
            "trust_title": "Evidence boundary",
            "trust_note": "Available evidence remains valid; replacement state is unverified.",
            "delta_label": "Changes",
            "delta": ["One permit source became unavailable."],
            "contradictions_label": "Conflicts",
            "contradictions": [],
            "degraded_label": "Unavailable evidence",
            "degraded_state": ["The latest permit source could not be loaded."],
            "work_state_kicker": "Current status",
            "state_title": "Permit review",
            "state_note": "Keep the last verified decision until its replacement is supported.",
            "current_state_label": "Current state",
            "desired_state_label": "Recovery outcome",
            "next_title": "Next action",
            "next_note": "Identify the unavailable source before starting recovery.",
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
            "current": (
                "The last verified permit decision remains available with its complete evidence explanation."
            ),
            "desired": (
                "The unavailable source returns and the operator can reconcile the next decision without ambiguity."
            ),
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
    handoff = page.locator(".project-host-handoff")
    handoff.wait_for(timeout=15000)
    assert handoff.evaluate("node => node.tagName") == "DETAILS"
    assert handoff.get_attribute("open") is None
    assert handoff.locator(":scope > summary").inner_text() == "Implementation steps"
    assert not handoff.locator(".project-host-prompt-grid").is_visible()
    assert handoff.locator(":scope > ol").count() == 0
    compact_text = page.locator(".project-surface").inner_text()
    assert "Start source creation" in compact_text
    assert "Choose implementation language" not in compact_text
    handoff.locator(":scope > summary").focus()
    page.keyboard.press("Enter")
    assert handoff.get_attribute("open") is not None
    assert handoff.locator(".project-host-prompt-grid").is_visible()
    surface_text = page.locator(".project-surface").inner_text()
    assert "Project overview" in surface_text
    assert "Source evidence" in surface_text
    assert "Accepted evidence excerpt:" not in surface_text
    evidence = page.locator(".project-evidence-excerpt")
    assert evidence.locator("summary").inner_text() == "Source evidence"
    assert evidence.get_attribute("open") is None
    assert not evidence.locator("p").is_visible()
    assert "Risks" in surface_text
    assert "No material risk identified" in surface_text
    assert "This structural fixture carries no product-domain risk claim." in surface_text
    assert "Project not defined yet" not in surface_text
    assert "Current orienting work" not in surface_text
    assert "Mockrepo" not in surface_text
    assert "Accepted first-path scenario" not in surface_text
    assert "Checkout" in surface_text or "checkout" in surface_text
    assert "Start source creation" in surface_text
    assert "Human " + "takeaway" not in surface_text
    assert "First source creation sequence" in surface_text
    assert "Choose implementation language" in surface_text
    assert "Open first implementation plan" in surface_text
    assert "Implement first runnable slice" in surface_text
    assert "Run authored proof" in surface_text
    assert "Refresh governed records" in surface_text
    assert "Stop before source edits until the plan is accepted" in surface_text
    assert "Topology spine" not in surface_text
    assert "How the story becomes governance" not in surface_text
    assert "Status now" not in surface_text
    assert "Where does this stand" not in surface_text
    assert "Who uses it?" not in surface_text
    assert page.locator(".project-state-grid").count() == 0
    assert page.locator(".project-scenario").count() == 0
    assert page.locator(".project-risks").count() == 1
    assert page.locator(".project-risk-card").count() == 1
    assert page.locator(".project-hero-rail").count() == 0
    assert page.locator(".project-hero .project-chips").count() == 0
    assert page.locator(".project-hero .project-intro").inner_text() == (
        "This structural fixture supports test authors checking exact source and design custody."
    )
    assert "Accepted evidence excerpt:" not in page.locator(".project-hero").inner_text()
    assert page.locator(".project-hero-main").evaluate(
        "node => getComputedStyle(node).gridTemplateColumns.split(' ').length"
    ) == 1
    assert page.locator(".project-hero .project-status").inner_text() == (
        "Project direction accepted. Implementation has not been verified."
    )
    assert page.locator(".project-signal-grid").count() == 0
    trust = page.locator(".project-trust")
    assert trust.locator("h2").inner_text() == "Evidence boundary"
    assert trust.locator(".project-panel-head p").inner_text() == (
        "This page records project requirements and proposed design. "
        "Working behavior must be established through source and validation evidence."
    )
    handoff_box = page.locator(".project-host-handoff").bounding_box()
    overview_box = page.locator(".project-product-story").bounding_box()
    assert handoff_box is not None and overview_box is not None
    assert handoff_box["y"] < overview_box["y"]
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
    assert page.locator(".project-job-card .project-label-chip").count() == 0
    assert page.locator(".project-actor-card-name").count() >= 1
    assert page.locator(".project-actor-card-name").evaluate_all(
        "nodes => nodes.every(node => node.getBoundingClientRect().height < 112)"
    )

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
    assert handoff_layout["stepCount"] == 0
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
            const contract = node.querySelector(".project-story-contract-body");
            const rows = Array.from(node.querySelectorAll(".project-story-contract-card"));
            const capabilityCard = node.querySelector('[data-semantic-slot="owned_capabilities"]');
            const capabilityBody = capabilityCard?.querySelector(':scope > .project-story-contract-body');
            const capabilityHeading = capabilityCard?.querySelector(':scope > h3');
            const pathCard = node.querySelector('[data-semantic-slot="first_path"]');
            const pathBody = pathCard?.querySelector(':scope > .project-story-contract-body');
            const pathHeading = pathCard?.querySelector(':scope > h3');
            const bodies = rows.map(
              (row) => String(row.querySelector(".project-story-contract-body")?.innerText || "").trim()
            );
            return {
              narrativeParagraphCount: narrativeParagraphs.length,
              listFontSize: list ? window.getComputedStyle(list).fontSize : "",
              contractFontSize: contract ? window.getComputedStyle(contract).fontSize : "",
              rowCount: rows.length,
              capabilityChildCount: capabilityCard?.children.length || 0,
              capabilityBodyLeft: capabilityBody?.getBoundingClientRect().left || 0,
              capabilityHeadingRight: capabilityHeading?.getBoundingClientRect().right || 0,
              capabilityColumns: capabilityCard ? window.getComputedStyle(capabilityCard).gridTemplateColumns.split(' ').length : 0,
              pathChildCount: pathCard?.children.length || 0,
              pathBodyLeft: pathBody?.getBoundingClientRect().left || 0,
              pathHeadingRight: pathHeading?.getBoundingClientRect().right || 0,
              pathColumns: pathCard ? window.getComputedStyle(pathCard).gridTemplateColumns.split(' ').length : 0,
              distinctBodyCount: new Set(bodies.map((body) => body.toLocaleLowerCase())).size,
              focusEventCount: node.ownerDocument.querySelectorAll(
                '[data-authored-fact-list="focus"] [data-authored-fact-item]'
              ).length,
              firstPathEventCount: node.querySelectorAll(
                '[data-authored-fact-list="first_path"] [data-authored-fact-item]'
              ).length,
              actorEventCount: node.ownerDocument.querySelectorAll(
                '[data-authored-fact-list="actor"] [data-authored-fact-item]'
              ).length,
              capabilityCount: node.querySelectorAll(
                '[data-authored-fact-list="owned_capabilities"] [data-authored-fact-item]'
              ).length,
              boundaryGroupCount: node.querySelectorAll("[data-authored-boundary-group]").length,
              semanticSlots: rows.map((row) => String(row.dataset.semanticSlot || "")),
              rowLefts: rows.map((row) => Math.round(row.getBoundingClientRect().left)),
              rowTops: rows.map((row) => Math.round(row.getBoundingClientRect().top)),
              firstRowColumns: rows[0] ? window.getComputedStyle(rows[0]).gridTemplateColumns : "",
              scrollDelta: node.scrollWidth - node.clientWidth,
            };
        }"""
    )
    assert story_layout["narrativeParagraphCount"] == 0
    assert story_layout["listFontSize"] == "14px"
    assert story_layout["contractFontSize"] == "14px"
    assert story_layout["rowCount"] == 5
    assert story_layout["capabilityChildCount"] == 2
    assert story_layout["pathChildCount"] == 2
    if story_layout["capabilityColumns"] == 2:
        assert story_layout["capabilityBodyLeft"] > story_layout["capabilityHeadingRight"]
    if story_layout["pathColumns"] == 2:
        assert story_layout["pathBodyLeft"] > story_layout["pathHeadingRight"]
    assert story_layout["distinctBodyCount"] == 5
    assert story_layout["focusEventCount"] == 0
    assert story_layout["firstPathEventCount"] >= 1
    assert story_layout["actorEventCount"] == 0
    source_names = page.locator("#payload").evaluate("node => JSON.parse(node.textContent).authored_facts.human_actors")
    assert page.locator("[data-authored-actor] h3").all_inner_texts() == source_names
    assert story_layout["capabilityCount"] >= 1
    assert story_layout["boundaryGroupCount"] >= 1
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

    _assert_project_sections_do_not_overflow(
        page,
        [".project-product-story", ".project-trust", ".project-host-handoff"],
    )


def _assert_project_sections_do_not_overflow(page, selectors: list[str]) -> None:  # noqa: ANN001
    assert _clipped_project_text(page) == []
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
    assert page.locator(".project-pane").evaluate("node => node.scrollWidth <= node.clientWidth")
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
            try:
                with _new_page(context) as (page, observation):
                    response = page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    _assert_greenfield_project_tab_layout(page, compact=compact)
                    screenshot = _failure_screenshot_path(f"project-{viewport['width']}")
                    if screenshot is None:
                        screenshot = tmp_path / f"project-{viewport['width']}.png"
                    screenshot.parent.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshot), full_page=True)
                    _assert_clean_page(page, observation)
            finally:
                context.close()


def test_project_tab_renders_accepted_greenfield_story_without_broken_layout(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _run_greenfield_project_tab_browser_check(tmp_path, monkeypatch, compact=False)


def test_project_tab_renders_accepted_greenfield_story_in_compact_browser(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _run_greenfield_project_tab_browser_check(tmp_path, monkeypatch, compact=True)


def test_project_handoff_scope_is_visible_and_copyable_at_both_widths(tmp_path: Path) -> None:
    cases = (
        ("constraints", ("Preserve APIv7 casing",), ()),
        ("non-goals", (), ("Batch Æther migration",)),
        ("mixed", ("Preserve APIv7 casing",), ("Batch Æther migration",)),
        ("empty", (), ()),
    )
    payloads = {}
    for name, constraints, non_goals in cases:
        proposal = _handoff_scope_proposal(constraints=constraints, non_goals=non_goals)
        payload = preview_project_dashboard_payload(
            root=tmp_path,
            proposal=proposal,
            accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
            source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
        )
        payloads[name] = payload
        _write_project_page(tmp_path / f"{name}.html", payload)
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            for viewport in ({"width": 1440, "height": 1100}, {"width": 430, "height": 932}):
                for name, constraints, non_goals in cases:
                    context = browser.new_context(viewport=viewport)
                    try:
                        with _new_page(context) as (page, observation):
                            response = page.goto(base_url + f"/{name}.html", wait_until="domcontentloaded")
                            assert response is not None and response.ok
                            handoff_details = page.locator(".project-host-handoff")
                            assert handoff_details.get_attribute("open") is None
                            assert not handoff_details.locator(".project-host-prompt-grid").is_visible()
                            handoff_details.locator(":scope > summary").focus()
                            page.keyboard.press("Enter")
                            assert handoff_details.get_attribute("open") is not None
                            prompts = page.locator(".project-host-prompt code")
                            assert prompts.count() == 5
                            expected_block = (
                                "Operational constraints — preserve these requirements:\n"
                                + ("\n".join(constraints) if constraints else "None stated.")
                                + "\n\nExcluded scope — preserve these exclusions:\n"
                                + ("\n".join(non_goals) if non_goals else "None stated.")
                            )
                            for index, handoff in enumerate(payloads[name]["host_handoff_prompts"]):
                                prompt = prompts.nth(index)
                                assert not prompt.is_visible()
                                summary = page.locator(".project-host-prompt summary").nth(index)
                                summary.focus()
                                page.keyboard.press("Enter")
                                assert prompt.is_visible()
                                assert prompt.text_content() == handoff["prompt"]
                                copied_text = prompt.evaluate("""node => {
                              const range = document.createRange();
                              range.selectNodeContents(node);
                              const selection = window.getSelection();
                              selection.removeAllRanges();
                              selection.addRange(range);
                              return selection.toString();
                            }""")
                                assert copied_text == handoff["prompt"]
                                assert copied_text.startswith("Selected workstream: B-701")
                                assert copied_text.endswith(expected_block)
                            _assert_project_sections_do_not_overflow(page, [".project-host-handoff"])
                            page.evaluate("window.getSelection().removeAllRanges()")
                            page.locator(".project-host-prompt").first.screenshot(
                                path=str(tmp_path / f"handoff-{name}-{viewport['width']}.png"),
                            )
                            _assert_clean_page(page, observation)
                    finally:
                        context.close()


def test_project_tab_result_first_source_renders_labeled_proposed_order_at_both_widths(tmp_path: Path) -> None:
    proposal = _result_first_proposal()
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    _write_project_page(tmp_path / "index.html", payload)
    facts = payload["authored_facts"]
    relations = {
        row["order"]: row for row in facts["first_path_relations"]
    }
    proposed_orders = facts["provisional_design"]["first_run"]["event_orders"]
    expected_actors = [relations[order]["actor_fact_quote"] for order in proposed_orders]
    expected_events = [relations[order]["event_quote"] for order in proposed_orders]
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            for viewport in ({"width": 1440, "height": 1100}, {"width": 430, "height": 932}):
                context = browser.new_context(viewport=viewport)
                try:
                    with _new_page(context) as (page, observation):
                        response = page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                        assert response is not None and response.ok
                        for key in ("first_path",):
                            sequence = page.locator(f'[data-authored-fact-list="{key}"]')
                            assert sequence.get_attribute("data-authority-kind") == "provisional_design"
                            items = sequence.locator("[data-authored-fact-item]")
                            assert items.locator(
                                ":scope > [data-authored-event-actor] "
                                "> [data-authored-event-actor-label]"
                            ).all_text_contents() == ["Actor:"] * len(expected_events)
                            assert items.locator(
                                ":scope > [data-authored-event-actor] "
                                "> [data-authored-event-actor-value]"
                            ).all_text_contents() == expected_actors
                            assert items.locator(
                                ":scope > [data-authored-event-quote]"
                            ).all_text_contents() == expected_events
                            assert all(" — " not in text for text in items.all_text_contents())
                            assert items.evaluate_all("nodes => nodes.map(node => node.dataset.eventOrder)") == ["2", "1"]
                        assert page.locator("[data-proposed-first-run-label]").all_text_contents() == [
                            "Proposed first run:",
                        ]
                        card = page.locator('[data-semantic-slot="first_path"]')
                        assert card.locator(":scope > *").count() == 2
                        assert card.locator(":scope > .project-story-contract-body").count() == 1
                        _assert_project_sections_do_not_overflow(page, [".project-product-story", ".project-host-handoff"])
                        card.screenshot(path=str(tmp_path / f"proposed-first-run-{viewport['width']}.png"))
                        page.screenshot(path=str(tmp_path / f"project-{viewport['width']}.png"), full_page=True)
                        _assert_clean_page(page, observation)
                finally:
                    context.close()


def test_project_tab_clipping_probe_detects_a_clipping_parent(tmp_path: Path, monkeypatch) -> None:  # noqa: ANN001
    _write_greenfield_project_page(tmp_path, monkeypatch)
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            context = browser.new_context(viewport={"width": 430, "height": 932})
            try:
                with _new_page(context) as (page, observation):
                    response = page.goto(base_url + "/index.html", wait_until="domcontentloaded")
                    assert response is not None and response.ok
                    card = page.locator(".project-story-contract-card").first
                    card.evaluate("(node) => { node.style.maxHeight = '24px'; node.style.overflow = 'hidden'; }")

                    assert _clipped_project_text(page)
                    _assert_clean_page(page, observation)
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
    _write_project_page(tmp_path / "unavailable.html", project_intelligence_presenter._fallback_payload())

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
        (
            "unavailable.html",
            [".project-empty-panel", ".project-empty-action"],
            "odylith dashboard refresh --repo-root . --surfaces tooling_shell",
        ),
    )
    viewports = ({"width": 1440, "height": 1100}, {"width": 430, "height": 932})

    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            for filename, selectors, terminal_text in cases:
                for viewport in viewports:
                    context = browser.new_context(viewport=viewport)
                    try:
                        with _new_page(context) as (page, observation):
                            response = page.goto(f"{base_url}/{filename}", wait_until="domcontentloaded")
                            assert response is not None and response.ok
                            assert terminal_text in page.locator(".project-surface").inner_text()
                            assert "['The" not in page.locator(".project-surface").inner_text()
                            if filename == "unavailable.html":
                                assert "The Project view could not be loaded." in page.locator(".project-surface").inner_text()
                                assert page.locator(".project-empty-action").count() == 1
                                assert page.locator(".project-empty-preview, .project-signal-grid, .project-proof-grid").count() == 0
                            _assert_project_sections_do_not_overflow(page, selectors)
                            page.screenshot(path=str(tmp_path / f"{Path(filename).stem}-{viewport['width']}.png"), full_page=True)
                            _assert_clean_page(page, observation)
                    finally:
                        context.close()


def test_project_summary_and_structured_risks_are_readable_at_both_widths(tmp_path: Path) -> None:
    proposal = _result_first_proposal()
    design = proposal["intent"]["authored_semantics"]["provisional_design"]
    summary = "A receipt workspace helps reviewers preserve evidence through a complete custody path."
    design["project_summary"] = summary
    component = design["components"][0]
    event_order = component["supported_event_orders"][0]
    workstream = next(row for row in design["workstreams"]
                     if component["key"] in row["component_keys"]
                     and event_order in row["verification_event_orders"])
    risk = {
        "key": "retention-boundary", "category": "data_retention",
        "statement": "Evidence could outlive its stated review period.",
        "trigger": "The review period ends before deletion succeeds.",
        "mitigation": "Retain the pending deletion state until deletion is verified.",
        "verification": "An unavailable archive must not report a completed deletion.",
        "scope_paths": [{"event_order": event_order, "component_key": component["key"],
                         "workstream_key": workstream["key"]}],
    }
    design["risk_posture"] = {
        "status": "material_risks_identified", "rationale": "The review period constrains evidence custody.",
        "items": [risk],
    }
    payload = preview_project_dashboard_payload(
        root=tmp_path, proposal=proposal, accepted_project_preview=_accepted_preview(proposal=proposal, root=tmp_path),
        source_launch_context=_source_launch_context(proposal=proposal, root=tmp_path),
    )
    _write_project_page(tmp_path / "structured-risks.html", payload)
    with _static_server(root=tmp_path) as base_url:
        for _pw, browser in _browser():
            for viewport in ({"width": 1440, "height": 1100}, {"width": 430, "height": 932}):
                context = browser.new_context(viewport=viewport)
                try:
                    with _new_page(context) as (page, observation):
                        response = page.goto(base_url + "/structured-risks.html", wait_until="domcontentloaded")
                        assert response is not None and response.ok
                        evidence = page.locator(".project-evidence-excerpt")
                        assert evidence.get_attribute("open") is None
                        assert not evidence.locator("p").is_visible()
                        evidence.locator("summary").focus()
                        page.keyboard.press("Enter")
                        assert evidence.locator("p").is_visible()
                        assert evidence.locator("p").inner_text() == (
                            f"Accepted evidence excerpt: “{payload['authored_facts']['product_story']}”"
                        )
                        evidence.locator("summary").focus()
                        page.keyboard.press("Enter")
                        assert not evidence.locator("p").is_visible()
                        header = page.locator(".project-hero")
                        assert header.locator(".project-intro").inner_text() == summary
                        assert "Accepted evidence excerpt:" not in header.inner_text()
                        assert header.locator(".project-chips, .project-hero-rail").count() == 0
                        card = page.locator('[data-risk-key="retention-boundary"]')
                        assert card.locator("h3").inner_text() == "Data retention risk"
                        assert card.locator("[data-risk-statement]").inner_text() == risk["statement"]
                        assert card.locator("[data-risk-mitigation]").inner_text() == risk["mitigation"]
                        details = card.locator("details")
                        assert details.get_attribute("open") is None
                        assert not details.locator("dl").is_visible()
                        details.locator("summary").focus()
                        page.keyboard.press("Enter")
                        assert details.locator("dl").is_visible()
                        values = details.locator("dd").all_inner_texts()
                        assert values[0] == risk["trigger"]
                        assert values[1] == risk["verification"]
                        assert values[2] == payload["risk_items"][0]["scope"]
                        assert values[3] == (f"Source event {event_order} · Component {component['key']} · "
                                             f"Workstream {workstream['key']}")
                        details.locator("summary").focus()
                        page.keyboard.press("Enter")
                        assert not details.locator("dl").is_visible()
                        _assert_project_sections_do_not_overflow(page, [".project-hero", ".project-risks", ".project-product-story"])
                        screenshot = _failure_screenshot_path(f"summary-risks-{viewport['width']}") or tmp_path / f"summary-risks-{viewport['width']}.png"
                        screenshot.parent.mkdir(parents=True, exist_ok=True)
                        page.screenshot(path=str(screenshot), full_page=True)
                        _assert_clean_page(page, observation)
                finally:
                    context.close()
