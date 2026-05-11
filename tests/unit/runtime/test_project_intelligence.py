from __future__ import annotations

import ast
import json
from pathlib import Path

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.project_intelligence import assets, builder, deeplinks, focus, presenter


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def test_project_intelligence_compiles_current_repo_state_from_sources(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json",
        {
            "version": "v1",
            "components": [
                {
                    "component_id": "odylith",
                    "name": "Odylith",
                    "category": "governance_engine",
                    "status": "active",
                    "what_it_is": "Source-backed governance product for coding agents.",
                    "subcomponents": ["dashboard", "odylith-context-engine", "execution-engine"],
                },
                {
                    "component_id": "odylith-context-engine",
                    "name": "Context Engine",
                    "category": "governance_engine",
                    "product_layer": "memory_retrieval",
                    "status": "active",
                    "what_it_is": "Narrows repo truth before work starts.",
                },
                {
                    "component_id": "execution-engine",
                    "name": "Execution Engine",
                    "category": "governance_engine",
                    "product_layer": "agent_execution",
                    "status": "active",
                    "what_it_is": "Admits or defers the next bounded move.",
                },
            ],
        },
    )
    (tmp_path / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "radar" / "source" / "INDEX.md").write_text(
        "\n".join(
            (
                "# Backlog Index",
                "## Ranked Active Backlog",
                "| rank | idea_id | title | priority | status | link |",
                "| --- | --- | --- | --- | --- | --- |",
                "| 1 | B-200 | Source-backed Project tab | P0 | queued | [item](item.md) |",
                "",
                "## In Planning/Implementation",
                "| rank | idea_id | title | priority | status | link |",
                "| --- | --- | --- | --- | --- | --- |",
                "| - | B-201 | Dynamic Project intelligence | P0 | implementation | [item](item.md) |",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (tmp_path / "odylith" / "technical-plans" / "INDEX.md").parent.mkdir(parents=True, exist_ok=True)
    (tmp_path / "odylith" / "technical-plans" / "INDEX.md").write_text(
        "\n".join(
            (
                "# Plan Index",
                "## Active Plans",
                "| Plan | Status | Created | Updated | Backlog |",
                "| --- | --- | --- | --- | --- |",
                "| `plan.md` | In progress | 2026-05-09 | 2026-05-09 | `B-201` |",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
        {"version": "v1", "diagrams": [{"diagram_id": "D-001", "status": "active"}]},
    )
    _write_json(
        tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json",
        {
            "generated_utc": "2026-05-09T22:00:00Z",
            "execution_focus": {
                "global": {
                    "headline": "Project tab now compiles from source records",
                    "last_event_iso": "2026-05-09T15:00:00-07:00",
                    "workstreams": ["B-201"],
                }
            },
            "release_summary": {
                "current_release": {
                    "version": "0.2.0",
                    "display_label": "0.2.0",
                    "effective_name": "Human Project Entry",
                    "active_workstreams": ["B-201"],
                    "active_workstream_count": 1,
                    "completed_workstream_count": 0,
                }
            },
            "next_actions": [
                {
                    "idea_id": "B-201",
                    "title": "Dynamic Project intelligence",
                    "action": "Bind Project tab content to current source records.",
                    "source": "plan",
                }
            ],
            "risks": {
                "bugs": [
                    {
                        "title": "Project tab can drift from evidence",
                        "severity": "P1",
                        "status": "Open",
                        "components": "dashboard",
                        "is_open_critical": True,
                    }
                ]
            },
        },
    )
    _write_json(
        tmp_path / "odylith" / "compass" / "runtime" / "history" / "index.v1.json",
        {"dates": ["2026-05-09", "2026-05-08"]},
    )
    _write_json(
        tmp_path / "odylith" / "compass" / "runtime" / "history" / "2026-05-08.v1.json",
        {
            "generated_utc": "2026-05-08T22:00:00Z",
            "execution_focus": {"global": {"headline": "Project tab was still static", "workstreams": []}},
        },
    )

    payload = builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={
            "shell_repo_name": "odylith",
            "self_host": {
                "repo_role": "product_repo",
                "posture": "detached_source_local",
                "active_version": "source-local",
                "pinned_version": "0.1.15",
            },
            "live_refresh": {"worktree": {"status": "mixed", "meaningful_changed_count": 2, "generated_changed_count": 1}},
        },
    )

    assert payload["title"] == "Odylith"
    assert payload["intro"] == (
        "Odylith helps repository operators keep coding-agent work grounded, "
        "governed, and remembered across sessions."
    )
    assert "packages" not in payload["intro"]
    assert "behind one CLI" not in payload["intro"]
    assert payload["eyebrow"] == "Project type: coding-agent governance"
    assert "Project tab now compiles from source records" in payload["focus"]
    assert payload["chips"][:2] == ["coding-agent governance", "Source-backed runtime"]
    assert payload["chips"][2].endswith("complexity")
    assert payload["answers"][0] == (
        "Who uses Odylith?",
        "repository operators and coding agents",
        "Operators request repo work; agents execute it under Odylith controls.",
    )
    assert payload["answers"][1] == (
        "What changes in Odylith?",
        "coding-agent work",
        "Work moves from request to action with grounding, governance, and memory.",
    )
    assert payload["answers"][2][0] == "What matters now for Odylith?"
    assert payload["answers"][4] == (
        "What proves Odylith?",
        "State, work, shape, and risk evidence",
        "Compass shows state; Radar shows active work; Registry and Atlas show shape and topology; Casebook shows open risks.",
    )
    assert all("Governance Engine" not in " ".join(card) for card in payload["answers"])
    assert all("Source role:" not in " ".join(card) for card in payload["answers"])
    assert all("back the current claims" not in " ".join(card) for card in payload["answers"])
    assert "decision" not in payload
    assert "decision_label" not in payload
    assert payload["recommendation"] == "Bind Project tab content to current source records."
    assert "build" not in payload
    assert any("Project tab can drift from evidence" in item for item in payload["unknown"])
    assert any("Focus" in item for item in payload["known"])
    assert payload["projection"]["origin"] == "source-local"
    assert payload["projection"]["work_mode"] == "Implementing"
    assert payload["projection"]["refreshed_at"] == "2026-05-09T22:00:00Z"
    assert any(row["claim"] == "Current focus" and row["evidence"] == "operational" for row in payload["claim_evidence"])
    assert any(row["surface"] == "Registry" and row["coverage"] == "covered" for row in payload["artifact_coverage"])
    assert any(row["link"] == "Radar -> Plans" and row["health"] == "covered" for row in payload["topology_spine"])
    assert any("Focus changed" in item for item in payload["delta"])
    assert any("missing subcomponent dashboard" in item for item in payload["contradictions"])
    assert any(row["posture"] == "Recommendation proof" for row in payload["validation_posture"])
    assert any(row["risk"] == "Uncommitted change" for row in payload["risk_classes"])
    assert any(row["role"] == "Maintainer" for row in payload["audience_emphasis"])
    assert any("missing subcomponent dashboard" in item for item in payload["degraded_state"])
    assert payload["actors"] == [
        ("", "Operator", "Moves implementing work forward by choosing the next action and clearing blockers."),
        ("", "Maintainer", "Changes source or governance records only after checking Registry, Radar, Compass, Atlas, and Casebook evidence."),
        ("", "Reviewer", "Checks risk ownership, validation gaps, and contradiction paths."),
    ]
    assert any(row[1] == "Maintainer" for row in payload["actors"])
    assert any(row[0] == "Dynamic Project intelligence" and row[2] == "Current release" for row in payload["jobs"])
    assert any(row[2] == "Open risk" for row in payload["jobs"])
    assert payload["scenario"][0] == "Current work"
    assert payload["scenario"][1] == "Odylith"
    assert payload["scenario"][2] == "0.2.0: Human Project Entry implementing work"
    assert payload["scenario"][3] == "1 active workstream; 1 runtime action; 1 critical blocker."
    assert payload["scenario"][4] == (
        "For 0.2.0: Human Project Entry, Odylith is in implementing mode; the active focus is project tab now compiles from "
        "source records. The next move is to bind Project tab content to current source records. "
        "1 critical blocker remains open, so proof must stay attached to source records."
    )
    assert "Focus:" not in payload["scenario"][4]
    assert "Next action:" not in payload["scenario"][4]
    assert "Evidence:" not in payload["scenario"][4]
    assert "..." not in payload["scenario"][4]
    assert payload["scenario_details"] == [
        ("Active work", "Project tab now compiles from source records"),
        ("Next move", "Bind Project tab content to current source records."),
        ("Proof boundary", "Compass runtime state, Radar workstreams, Registry component records, Atlas topology records, and Casebook risk records"),
        ("Open risk", "1 critical blocker remains open."),
    ]
    assert payload["scenario_title"] == "Current implementing work"
    assert payload["jobs_title"] == "What is active for 0.2.0: Human Project Entry?"
    assert payload["boundary_title"] == "What is inside the current implementing boundary?"
    assert payload["claim_evidence_title"] == "What supports the current Odylith claims?"
    assert payload["state_title"] == "Where does Odylith stand?"
    assert payload["next_title"] == "What should move next for Odylith?"
    assert payload["included_label"] == "In current slice"
    assert any("B-201: Dynamic Project intelligence" in item for item in payload["included"])
    assert any("missing subcomponent dashboard" in item for item in payload["excluded"])

    html = presenter.render_project_html({"project_intelligence": payload})
    assert "project-focus-card" in html
    assert "project-open-card" in html
    assert "project-decision-card" not in html
    assert "project-decision-grid" not in html
    assert "Decision now" not in html
    assert "What must be decided?" not in html
    assert "What should move next for Odylith?" in html
    assert "What supports the current Odylith claims?" in html
    assert "Is the Odylith governance spine healthy?" not in html
    assert "What source coverage exists for Odylith?" not in html
    assert "What changed or conflicts in Odylith?" in html
    assert "What risk matters for Odylith?" in html
    assert "What matters now for Odylith?" in html
    assert "What decision matters for Odylith?" not in html
    assert "Governance Engine" not in html
    assert "Source role:" not in html
    assert "AI agent governance scenario" not in html
    assert "0.2.0: Human Project Entry. Evidence:" not in html
    assert "Evidence boundary: Registry" not in html
    assert '<article class="project-scenario-cover"><strong>' in html
    assert '<article class="project-scenario-cover"><p>' not in html
    assert "Current implementing work" in html
    assert "Current focus:" not in html
    assert "Evidence boundary:" not in html
    assert '<div class="project-prose-lines"><p>Project tab now compiles from source records.</p><p>Current release: 0.2.0: Human Project Entry.</p><p>Worktree: mixed with 2 meaningful and 1 generated changed paths.</p></div>' in html
    assert '<a class="project-deeplink" target="_top" href="?tab=radar&amp;workstream=B-201">B-201</a>' in html
    assert '<a class="project-deeplink" target="_top" href="?tab=casebook">Casebook</a>' in html
    assert '<a class="project-deeplink" target="_top" href="?tab=registry">Registry</a>' in html
    assert "<b>Active work</b>" in html
    assert "<b>Next move</b>" in html
    assert "<b>Proof boundary</b>" in html
    assert "Human-first comprehension" not in html
    assert "A maintainer opens" not in html
    assert "How does Odylith move work from request to proof?" not in html
    assert "Ground request" not in html
    assert "Replacing Radar, Registry, Atlas, Compass, or Casebook" not in html
    assert "Showing a generic intake template" not in html
    assert "Running background sync from the Project page" not in html
    assert "Systems and evidence surfaces" not in html
    assert "Maintainer" in html
    assert "AUDIENCE" not in html
    assert "Systems and evidence surfaces" not in html
    assert "Context Engine" not in html
    assert "Summarized from 0.2.0: Human Project Entry, 1 active workstream, 1 runtime action, and 5 evidence sources." in html
    assert "project-projection-strip" not in html
    assert '<article class="project-card"><p></p>' not in html


def test_project_focus_uses_release_workstreams_when_runtime_headline_is_generic() -> None:
    backlog = {
        "execution": [
            {"idea_id": "B-100", "title": "Discharge checklist review", "priority": "P1", "status": "implementation"},
            {"idea_id": "B-101", "title": "Follow-up ownership proof", "priority": "P1", "status": "implementation"},
        ]
    }

    assert focus.project_focus_text(
        "Updated product code and 3 other areas",
        active_workstreams=["B-100", "B-101"],
        backlog=backlog,
        release_label="0.3.0",
        fallback="Fallback focus",
    ) == "Discharge checklist review; Follow-up ownership proof"


def test_project_intelligence_presenter_renders_fallback_without_payload() -> None:
    html = presenter.render_project_html({})

    assert "No project projection is available yet." in html
    assert "Project source payload missing" in html
    assert "project-side" not in html
    assert "Main blockers" not in html


def test_project_intelligence_deeplink_renderer_links_governance_references() -> None:
    html = deeplinks.inline_deeplink_html(
        "Use B-321, CB-654, D-987, Registry, radar, and odylith/technical-plans/in-progress/demo.md."
    )

    assert 'href="?tab=radar&amp;workstream=B-321">B-321</a>' in html
    assert 'href="?tab=casebook&amp;bug=CB-654">CB-654</a>' in html
    assert 'href="?tab=atlas&amp;diagram=D-987">D-987</a>' in html
    assert 'href="?tab=registry">Registry</a>' in html
    assert 'href="?tab=radar">radar</a>' in html
    assert 'href="technical-plans/in-progress/demo.md"' in html


def test_project_intelligence_presenter_uses_payload_narration_labels() -> None:
    payload = {
        "project_intelligence": {
            "eyebrow": "fixture lens",
            "title": "Fixture project",
            "intro": "Fixture project intro.",
            "chips": ["fixture"],
            "focus_label": "Fixture focus label",
            "focus": "Fixture focus",
            "open_label": "Fixture open label",
            "open": ["Fixture open item"],
            "answers": [],
            "scenario": ["Fixture scenario", "Fixture project", "Fixture headline", "Fixture caption", "Fixture body"],
            "scenario_title": "Fixture scenario title",
            "scenario_note": "Fixture scenario note",
            "participants_title": "Fixture participant title",
            "participants_note": "Fixture participant note",
            "actors": [],
            "jobs_title": "Fixture jobs title",
            "jobs_note": "Fixture jobs note",
            "jobs": [],
            "claim_evidence_title": "Fixture claim evidence title",
            "claim_evidence_note": "Fixture claim evidence note",
            "claim_evidence_columns": [("claim", "Fixture claim column")],
            "claim_evidence": [{"claim": "Fixture claim row"}],
            "topology_spine_title": "Fixture spine title",
            "topology_spine_note": "Fixture spine note",
            "topology_spine_columns": [("link", "Fixture link column")],
            "topology_spine": [{"link": "Fixture spine row"}],
            "artifact_coverage_title": "Fixture coverage title",
            "artifact_coverage_note": "Fixture coverage note",
            "artifact_coverage_columns": [("surface", "Fixture surface column")],
            "artifact_coverage": [{"surface": "Fixture coverage row"}],
            "trust_title": "Fixture trust title",
            "trust_note": "Fixture trust note",
            "delta_label": "Fixture delta label",
            "contradictions_label": "Fixture contradiction label",
            "degraded_label": "Fixture degraded label",
            "delta": [],
            "contradictions": [],
            "degraded_state": [],
            "posture_title": "Fixture posture title",
            "posture_note": "Fixture posture note",
            "validation_label": "Fixture validation label",
            "risk_label": "Fixture risk label",
            "validation_posture": [],
            "risk_classes": [],
            "audience_emphasis": [],
            "boundary_title": "Fixture boundary title",
            "boundary_note": "Fixture boundary note",
            "included_label": "Fixture included label",
            "excluded_label": "Fixture excluded label",
            "included": [],
            "excluded": [],
            "work_state_kicker": "Fixture status kicker",
            "state_title": "Fixture state title",
            "state_note": "Fixture state note",
            "current_state_label": "Fixture current label",
            "desired_state_label": "Fixture desired label",
            "current": "Fixture current state",
            "desired": "Fixture desired state",
            "next_title": "Fixture next title",
            "next_note": "Fixture next note",
            "next_owner_label": "Fixture owner label",
            "next_output_label": "Fixture output label",
            "next_precondition_label": "Fixture precondition label",
            "next_risk_label": "Fixture risk-if-delayed label",
            "next": ["Fixture next item", "Fixture detail", "Fixture owner", "Fixture output", "Fixture precondition", "Fixture delay risk"],
            "proof_title": "Fixture proof title",
            "proof_note": "Fixture proof note",
            "known_label": "Fixture known label",
            "unknown_label": "Fixture unknown label",
            "confidence_label": "Fixture confidence label",
            "known": [],
            "unknown": [],
            "confidence": "Medium",
            "sections": ["next", "proof"],
        }
    }

    html = presenter.render_project_html(payload)

    assert "Fixture claim evidence title" not in html
    assert "Fixture participant title" not in html
    assert "Fixture jobs title" not in html
    assert "Fixture state title" not in html
    assert "Fixture spine title" not in html
    assert "Fixture coverage title" not in html
    assert "Fixture next title" in html
    assert "Fixture known label" in html
    assert "What is the evidence maturity per claim?" not in html
    assert "Where does the project stand?" not in html


def test_project_intelligence_renders_greenfield_origin_from_proposal(tmp_path: Path) -> None:
    envelope = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build an ecommerce site with checkout recovery",
    )
    proposal = envelope["proposal_template"]

    payload = builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={"greenfield_proposal": proposal},
    )
    html = presenter.render_project_html({"project_intelligence": payload})

    assert payload["projection"]["origin"] == "greenfield proposal"
    assert "greenfield proposal" in payload["chips"]
    assert "User-stated and inferred" in payload["chips"]
    assert "claim_evidence" in payload["sections"]
    assert "Proposed first-path scenario" in html
    assert "What evidence state does" in html
    assert "Unproven before build" in html
    assert "Source-backed runtime" not in payload["chips"]
    assert "accepted project truth" in payload["desired"].lower()
    assert any(row["evidence"] in {"user-stated", "inferred", "needs validation"} for row in payload["claim_evidence"])
    assert payload["sections"][0] == "product_story"
    assert payload["product_story_title"] == "Product Story"
    story = payload["product_story"]
    assert isinstance(story, dict)
    assert "provable journey" in story["headline"]
    assert any(row["label"] == "First proof" for row in story["narrative"])
    assert story["topology_title"] == "Topology spine"
    assert [row["label"] for row in story["topology_spine"]] == [
        "Story root",
        "First path",
        "Radar",
        "Registry",
        "Atlas",
        "Release proof",
    ]
    assert "topology spine ties" in story["artifact_intro"].lower()
    assert any(group["label"] == "Workstreams" and group["items"] for group in story["artifacts"])
    assert any(group["label"] == "Workstreams" for group in story["groups"])
    assert "Product Story" in html
    assert "Topology spine" in html
    assert "Story root" in html
    assert "Release proof" in html
    assert "Workstreams" in html
    assert "Registry</a> components" in html
    assert "Atlas</a> views" in html


def test_greenfield_workstream_body_does_not_repeat_full_project_title(tmp_path: Path) -> None:
    envelope = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="SMB lending application pulling stable coins from DeFi protocols into a merchant on Shopify",
    )
    proposal = envelope["proposal_template"]
    title = proposal["intent"]["title"]
    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})

    assert title
    assert payload["title"] == "Merchant Capital Product"
    assert payload["title"] != title
    for row in proposal["backlog"]:
        assert row["title"]
        assert title not in row["problem"]
        assert title not in row["product_view"]
        assert not row["problem"].startswith(title)

    problems = [row["problem"] for row in proposal["backlog"]]
    assert any(problem.startswith("Merchants need a trustworthy path") for problem in problems)
    assert any(problem.startswith("Merchants cannot trust a capital product") for problem in problems)
    assert any(problem.startswith("Funding offers cannot be trustworthy") for problem in problems)
    assert all("accepted execution spine" not in problem for problem in problems)
    assert any("Merchant advocate" == row[1] for row in payload["actors"])
    assert any("Underwriting operator" == row[1] for row in payload["actors"])
    assert not any("Project tooling" in row[1] for row in payload["actors"])
    project_owners = "\n".join(proposal["project_intelligence"]["owners"])
    assert "Merchant advocate" in project_owners
    assert "Project tooling owns" not in project_owners
    component_ids = {row["component_id"] for row in proposal["components"]}
    diagram_slugs = {row["slug"] for row in proposal["diagrams"]}
    assert "merchant-capital-merchant-funding-workspace" in component_ids
    assert "merchant-capital-first-slice-flow" in diagram_slugs
    assert all("smb-lending-application" not in item for item in component_ids | diagram_slugs)


def test_project_intelligence_source_does_not_embed_demo_project_language() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith" / "runtime" / "project_intelligence"
    banned = {
        "AI agent governance",
        "Shopify",
        "merchant lending",
        "Human-first comprehension",
        "Product scenario journey",
        "A maintainer opens",
        "Ground request",
        "Evidence: Registry",
        "Existing product repo",
        "governance engine lens",
    }
    strings: list[str] = []
    for path in source_root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        strings.extend(node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str))

    leaked = [text for text in strings for phrase in banned if phrase in text]

    assert leaked == []


def test_project_intelligence_css_uses_shared_surface_typography() -> None:
    css = assets.load_project_tab_css()

    assert "font-family: inherit;" in css
    assert "--project-type-label-size: var(--surface-workstream-button-font-size, 12px);" in css
    assert "--project-type-label-weight: var(--surface-workstream-button-font-weight, 500);" in css
    assert "--project-type-chip-size: var(--surface-identifier-font-size, 14px);" in css
    assert "--project-type-chip-weight: var(--surface-identifier-font-weight, 500);" in css
    assert "--project-type-content-size: var(--project-type-body-size);" in css
    assert "--project-type-title-size: 52px;" in css
    assert "--project-type-intro-size: 28px;" in css
    assert "--project-type-hero-eyebrow-size: 15px;" in css
    assert ".project-answer-card p" in css
    assert ".project-answer-card h3,\n.project-answer-card b" in css
    assert ".project-answer-card span" in css
    assert ".project-proof-grid li" in css
    assert ".project-orientation" not in css
    assert ".project-build-card" not in css
    assert ".project-next-grid" not in css
    assert ".project-scenario .project-panel-head h2" in css
    assert ".project-scenario-cover strong" in css
    assert ".project-prose-lines" in css
    assert "font-size: 22px;" in css
    assert "font-size: 18px;" in css
    assert ".project-actor-grid" in css
    assert ".project-system-grid" not in css
    assert ".project-flow-grid" not in css
    assert "font-size: var(--project-type-content-size);" in css
    assert "font-weight: 800" not in css
    assert "clamp(" not in css
    assert "letter-spacing: -" not in css
