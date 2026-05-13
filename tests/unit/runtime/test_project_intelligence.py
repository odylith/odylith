from __future__ import annotations

import ast
import json
from pathlib import Path

from odylith.runtime.project_intelligence import assets, builder, deeplinks, focus, presenter
from tests.unit.runtime.test_greenfield_proposals import _apply_ready_greenfield_fixture as _host_greenfield_fixture


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _apply_ready_greenfield_fixture(repo_root: Path, prompt: str) -> dict[str, object]:
    return _host_greenfield_fixture(repo_root, prompt)


def test_project_intelligence_blank_install_starts_with_minimal_project_state(tmp_path: Path) -> None:
    payload = builder.build_project_intelligence_payload(
        repo_root=tmp_path,
        shell_payload={
            "shell_repo_name": "mockrepo",
            "welcome_state": {
                "starter_prompt": "Odylith, show me what you can do.",
                "repo_readout": ["Odylith has not inferred one grounded slice yet."],
            },
        },
    )
    html = presenter.render_project_html({"project_intelligence": payload})

    assert payload["mode"] == "blank"
    assert payload["sections"] == ["empty_state"]
    assert payload["title"] == "Mockrepo"
    assert payload.get("answers", []) == []
    assert "Project not defined yet" in html
    assert "Start with the project" in html
    assert "odylith greenfield propose --repo-root ." in html
    assert "Odylith, show me what you can do." in html
    assert "Product story" in html
    assert "Governance spine" in html
    assert "Execution boundary" in html
    assert "Who participates" not in html
    assert "Current orienting work" not in html
    assert "No active release detected" not in html
    assert "State evidence" not in html
    assert "Evidence gap" not in html
    assert "Compass shows state" not in html
    assert "Operator" not in html
    assert "Maintainer" not in html
    assert "Reviewer" not in html


def test_project_intelligence_blank_install_ignores_generic_orienting_next_action(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json",
        {
            "generated_utc": "2026-05-11T17:13:00Z",
            "next_actions": [
                {
                    "title": "Define the project first",
                    "action": "Define the project before implementation starts.",
                    "source": "compass",
                }
            ],
        },
    )

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"shell_repo_name": "mockrepo"})
    html = presenter.render_project_html({"project_intelligence": payload})

    assert payload["mode"] == "blank"
    assert "Project not defined yet" in html
    assert "Current orienting work" not in html
    assert "Define the project first" not in html


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
        {"version": "v1", "diagrams": [{"diagram_id": "D-001", "title": "Human Project Entry Map", "status": "active"}]},
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
    assert payload["sections"][0] == "product_story"
    assert payload["governance_titles"]["B-201"] == "Dynamic Project intelligence"
    assert payload["governance_titles"]["D-001"] == "Human Project Entry Map"
    assert payload["product_story_title"] == "Product Story"
    assert payload["product_story_note"] == ""
    assert payload["product_story"]["headline"].startswith("How Odylith helps")
    assert payload["product_story"]["standfirst"] == ""
    assert any("Odylith is in implementing mode" in row for row in payload["product_story"]["paragraphs"])
    assert any("Evidence stays bounded" in row for row in payload["product_story"]["paragraphs"])
    source_records = payload["product_story"]["supporting_records"]
    assert any("Radar carries" in row and "B-201" in row for row in source_records)
    assert any("Registry names the owned boundaries" in row for row in source_records)
    assert any("Atlas gives reviewers" in row for row in source_records)
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
    assert (
        '<a class="project-deeplink project-id-deeplink" target="_top" href="?tab=radar&amp;workstream=B-201" '
        'data-tooltip="B-201: Dynamic Project intelligence" aria-label="B-201: Dynamic Project intelligence" '
        'title="B-201: Dynamic Project intelligence">B-201</a>'
    ) in html
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
    assert "<h3>Odylith helps repository operators" not in html
    assert "Showing a generic intake template" not in html
    assert "Running background sync from the Project page" not in html
    assert "Systems and evidence surfaces" not in html
    assert "Maintainer" in html
    assert "AUDIENCE" not in html
    assert "Systems and evidence surfaces" not in html
    assert "Context Engine" in html
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
        "Use B-321, CB-654, D-987, Registry, radar, and odylith/technical-plans/in-progress/demo.md.",
        titles={
            "B-321": "Customer intake workflow",
            "CB-654": "Rollback owner missing",
            "D-987": "First slice flow",
        },
    )

    assert 'href="?tab=radar&amp;workstream=B-321" data-tooltip="B-321: Customer intake workflow"' in html
    assert 'href="?tab=casebook&amp;bug=CB-654" data-tooltip="CB-654: Rollback owner missing"' in html
    assert 'href="?tab=atlas&amp;diagram=D-987" data-tooltip="D-987: First slice flow"' in html
    assert 'title="B-321: Customer intake workflow"' in html
    assert 'href="?tab=registry">Registry</a>' in html
    assert 'href="?tab=radar">radar</a>' in html
    assert 'href="technical-plans/in-progress/demo.md"' in html
    assert 'href="?tab=registry" data-tooltip=' not in html


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
    proposal = _apply_ready_greenfield_fixture(tmp_path, "Build an ecommerce site with checkout recovery")

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
    assert "accepted project direction" in payload["desired"].lower()
    assert any(row["evidence"] in {"user-stated", "inferred", "needs validation"} for row in payload["claim_evidence"])
    assert payload["sections"][0] == "product_story"
    assert payload["product_story_title"] == "Product Story"
    story = payload["product_story"]
    assert isinstance(story, dict)
    assert "the team can prove" in story["headline"]
    assert len(story["paragraphs"]) >= 3
    assert any("the product narrows to" in row for row in story["paragraphs"])
    assert any("outside the first proof" in row for row in story["paragraphs"])
    assert any("Together, those records keep release" in row for row in story["paragraphs"])
    source_records = story["supporting_records"]
    assert any("Radar carries" in row for row in source_records)
    assert any("Registry gives ownership" in row for row in source_records)
    assert any("Atlas gives reviewers" in row for row in source_records)
    assert any("Release 0.0.1 stays tied" in row for row in source_records)
    assert "Product Story" in html
    assert "the team can prove" in html
    assert "Radar" in html
    assert "Registry" in html
    assert "Atlas" in html
    assert "Topology spine" not in html
    assert "Story root" not in html
    assert "How the story becomes governance" not in html


def test_greenfield_workstream_body_does_not_repeat_full_project_title(tmp_path: Path) -> None:
    proposal = _apply_ready_greenfield_fixture(
        tmp_path,
        "Build an ecommerce site with checkout recovery",
    )
    title = proposal["intent"]["title"]
    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})

    assert title
    assert payload["title"]
    assert payload["title"] != title
    for row in proposal["backlog"]:
        assert row["title"]
        assert title not in row["problem"]
        assert title not in row["product_view"]
        assert not row["problem"].startswith(title)

    problems = [row["problem"] for row in proposal["backlog"]]
    assert any("ecommerce site" in problem for problem in problems)
    assert any("browse and checkout UI" in problem for problem in problems)
    assert any("Product, price, and inventory rules" in problem for problem in problems)
    assert all("accepted execution spine" not in problem for problem in problems)
    assert any("Shopper advocate" == row[1] for row in payload["actors"])
    assert any("Commerce operator" == row[1] for row in payload["actors"])
    assert not any("Project tooling" in row[1] for row in payload["actors"])
    project_actors = "\n".join(proposal["backlog"][1]["domain_intelligence"]["actors"])
    assert "Shopper advocate" in project_actors
    assert "Project tooling owns" not in project_actors
    component_ids = {row["component_id"] for row in proposal["components"]}
    diagram_slugs = {row["slug"] for row in proposal["diagrams"]}
    assert "commerce-storefront" in component_ids
    assert any(slug.endswith("commerce-launch-system-context") for slug in diagram_slugs)
    assert all("an-ecommerce-site-with-checkout-recovery" not in item for item in component_ids)


def test_project_intelligence_source_does_not_embed_demo_project_language() -> None:
    source_root = Path(__file__).resolve().parents[3] / "src" / "odylith" / "runtime" / "project_intelligence"
    banned = {
        "AI agent governance",
        "demo lending",
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
    assert ".project-scenario-copy .project-scenario-prose" in css
    assert ".project-hero-main-empty" in css
    assert ".project-empty-action-grid" in css
    assert ".project-empty-preview-grid" in css
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
