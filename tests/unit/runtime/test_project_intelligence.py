from __future__ import annotations

import ast
import json
from pathlib import Path

from odylith.runtime.project_intelligence import assets, builder, deeplinks, focus, presenter, product_story
from odylith.runtime.project_intelligence.greenfield import _risk_classes
from odylith.runtime.surfaces import dashboard_shell_links
from tests.unit.runtime.greenfield_proposal_fixtures import _apply_ready_greenfield_fixture as _host_greenfield_fixture


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


def test_project_answer_summary_renders_as_full_table_without_markdown_noise() -> None:
    long_body = (
        "The project owner needs the system to keep the full operational explanation visible, including the "
        "last sentence that used to disappear when the answer strip was rendered as fixed-width cards."
    )
    html = presenter.render_project_html(
        {
            "project_intelligence": {
                "mode": "greenfield",
                "title": "Example Project",
                "eyebrow": "Project type: example",
                "intro": "A small project summary.",
                "chips": [],
                "product_story_title": "Product Story",
                "product_story": {"headline": "Example story", "paragraphs": ["Example story body."]},
                "sections": ["product_story"],
                "answers": [
                    ("Who uses it?", "**Account owner**", long_body),
                    ("What proves it?", "Reviewer-visible release evidence", "Evidence stays visible in the table."),
                ],
            }
        }
    )

    assert 'class="project-panel project-answer-strip"' in html
    assert 'class="project-answer-table"' in html
    assert "<table><tbody>" in html
    assert "project-answer-card" not in html
    assert "**" not in html
    assert "Who uses it?" in html
    assert "Account owner" in html
    assert "last sentence that used to disappear" in html
    assert "title=" not in html


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
    assert payload["product_story"]["paragraphs"][0].startswith("Odylith helps repository operators")
    assert any("first usable workflow" in row for row in payload["product_story"]["paragraphs"])
    assert any("Release 0.2.0: Human Project Entry is coherent" in row for row in payload["product_story"]["paragraphs"])
    assert any("Evidence stays bounded" in row for row in payload["product_story"]["paragraphs"])
    source_records = payload["product_story"]["supporting_records"]
    assert any("Radar carries" in row and "B-201" in row for row in source_records)
    assert any("Registry names the owned boundaries" in row for row in source_records)
    assert any("Atlas gives reviewers" in row for row in source_records)
    assert payload["answers"][0] == (
        "Who uses it?",
        "repository operators and coding agents",
        "Operators request repo work; agents execute it under Odylith controls.",
    )
    assert payload["answers"][1] == (
        "What changes?",
        "coding-agent work",
        "Work moves from request to action with grounding, governance, and memory.",
    )
    assert payload["answers"][2][0] == "What matters now?"
    assert payload["answers"][4] == (
        "What proves it?",
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
    assert payload["claim_evidence_title"] == "What can be trusted right now?"
    assert payload["state_title"] == "Where does this stand?"
    assert payload["next_title"] == "What should move next?"
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
    assert "What should move next?" in html
    assert "What can be trusted about Odylith right now?" not in html
    assert "Observed now" not in html
    assert "Proof gaps" not in html
    assert "View claim audit" not in html
    assert "Is the Odylith governance spine healthy?" not in html
    assert "What source coverage exists for Odylith?" not in html
    assert "What changed or conflicts?" in html
    assert "What risk matters?" in html
    assert "What is inside the current implementing boundary?" not in html
    assert "In current slice" not in html
    assert "What matters now?" in html
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
        '<a class="project-workstream-chip project-deeplink project-id-deeplink" target="_top" href="?tab=radar&amp;workstream=B-201" '
        'data-tooltip="Dynamic Project intelligence" aria-label="Open B-201 in Radar">B-201</a>'
    ) in html
    assert "<em>" not in html
    assert '<a class="project-deeplink" target="_top" href="?tab=casebook">Casebook</a>' not in html
    assert '<a class="project-deeplink" target="_top" href="?tab=registry">Registry</a>' not in html
    assert "Casebook" in html
    assert "Registry" in html
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


def test_project_intelligence_source_greenfield_story_uses_product_identity_before_artifacts(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "odylith" / "registry" / "source" / "component_registry.v1.json",
        {
            "version": "v1",
            "components": [
                {
                    "component_id": "parcel-records",
                    "name": "Forest Parcel Records Service",
                    "kind": "service",
                    "category": "developer_tooling",
                    "status": "active",
                    "what_it_is": (
                        "Forest Parcel Records Service is a `service` component that owns forest parcel records "
                        "and versioned boundary geometry. Initial evidence anchor: `src/parcel_records/`."
                    ),
                },
                {
                    "component_id": "observation-ledger",
                    "name": "Forest Observation Ledger",
                    "kind": "service",
                    "category": "developer_tooling",
                    "status": "active",
                    "what_it_is": "Append-only observations for field and remote-sensing evidence.",
                },
                {
                    "component_id": "evidence-linker",
                    "name": "Forest Evidence Linker",
                    "kind": "service",
                    "category": "developer_tooling",
                    "status": "active",
                    "what_it_is": "Connects observations to parcel condition claims.",
                },
                {
                    "component_id": "condition-deriver",
                    "name": "Forest Condition State Deriver",
                    "kind": "service",
                    "category": "developer_tooling",
                    "status": "active",
                    "what_it_is": "Derives condition state from cited evidence.",
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
                "",
                "## In Planning/Implementation",
                "| rank | idea_id | title | priority | status | link |",
                "| --- | --- | --- | --- | --- | --- |",
                "| - | B-001 | Govern Forest Preservation Tracker Program | P0 | implementation | [item](b001.md) |",
                "| - | B-002 | Forest Parcel Records Service with Versioned Boundary | P0 | implementation | [item](b002.md) |",
                "| - | B-003 | Append-Only Forest Observation Ledger | P0 | implementation | [item](b003.md) |",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    _write_json(
        tmp_path / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json",
        {
            "version": "v1",
            "diagrams": [
                {"diagram_id": "D-001", "title": "Forest Tracker System Context", "status": "active"},
                {"diagram_id": "D-002", "title": "Forest First Slice Sequence", "status": "active"},
            ],
        },
    )
    _write_json(
        tmp_path / "odylith" / "compass" / "runtime" / "current.v1.json",
        {
            "generated_utc": "2026-05-14T15:53:00Z",
            "execution_focus": {
                "global": {
                    "headline": "Greenfield proposal accepted for Forest Preservation Tracker",
                    "workstreams": ["B-001", "B-002", "B-003"],
                }
            },
            "release_summary": {
                "current_release": {
                    "version": "0.0.1",
                    "display_label": "0.0.1",
                    "effective_name": "Forest core evidence primitive",
                    "active_workstreams": ["B-001", "B-002", "B-003"],
                }
            },
            "next_actions": [
                {
                    "idea_id": "B-002",
                    "title": "Forest Parcel Records Service with Versioned Boundary",
                    "action": "Prepare promotion plan and implementation breakdown.",
                    "source": "radar",
                }
            ],
        },
    )

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"shell_repo_name": "save-forest"})
    html = presenter.render_project_html({"project_intelligence": payload})
    story = payload["product_story"]
    leading_story = " ".join(story["paragraphs"][:3])

    assert payload["title"] == "Forest Preservation Tracker"
    assert payload["intro"].startswith("Forest Preservation Tracker helps product owners")
    assert "responsible for Own" not in html
    assert "as its initial" not in html
    assert story["paragraphs"][0].startswith("Forest Preservation Tracker helps product owners")
    assert "forest parcel records service" in story["paragraphs"][0].casefold()
    assert "first usable workflow" in story["paragraphs"][1].casefold()
    assert "Radar" not in leading_story
    assert "Registry" not in leading_story
    assert "Atlas" not in leading_story
    assert "operational state" in payload["desired"]
    assert "implementation-only context" in payload["desired"]
    assert all(term not in payload["desired"] for term in ("Radar", "Registry", "Atlas", "Compass", "Casebook"))
    assert payload["answers"][4] == (
        "What proves it?",
        "Reviewer-visible product evidence",
        "A reviewer can follow the current state, active workflow, ownership boundary, risks, and validation evidence without relying on implementation-only context.",
    )
    assert any(row.startswith("After the product story is clear, Radar") for row in story["paragraphs"])
    assert 'data-tooltip="Forest Parcel Records Service with Versioned Boundary"' in html
    assert 'title="Forest Parcel Records Service with Versioned Boundary"' not in html


def test_project_intelligence_accepted_greenfield_story_uses_product_narrative_before_artifacts(tmp_path: Path) -> None:
    _write_json(
        tmp_path / "odylith" / "runtime" / "source" / "accepted-project.v1.json",
        {
            "schema_version": "odylith.accepted_project.v1",
            "origin": "greenfield",
            "created": {
                "workstreams": [
                    {"idea_id": "B-001", "title": "Govern Forest Preservation Tracker Program"},
                    {"idea_id": "B-002", "title": "Forest Parcel Records Service with Versioned Boundary"},
                    {"idea_id": "B-003", "title": "Append-Only Forest Observation Ledger"},
                ],
                "components": [
                    {"component_id": "parcel-records", "label": "Forest Parcel Records Service"},
                    {"component_id": "observation-ledger", "label": "Forest Observation Ledger"},
                ],
                "diagrams": [
                    {"diagram_id": "D-001", "title": "System Context View"},
                    {"diagram_id": "D-002", "title": "First Slice Sequence View"},
                ],
            },
            "proposal": {
                "schema_version": "odylith.greenfield.proposal.v1",
                "mode": "host_reasoned_proposal",
                "intent": {
                    "title": "Forest Preservation Tracker",
                    "project_slug": "forest-preservation-tracker",
                    "prompt": "Draft a greenfield proposal for a forest preservation tracker",
                    "evidence_tier": "user_intent",
                },
                "observed_source": {"source_posture": "docs_only"},
                "project_brief": {
                    "summary": (
                        "Forest Preservation Tracker is a record-keeping and evidence-derivation product for "
                        "conservation stewards. It binds parcels, field observations, and remote-sensing snapshots "
                        "into one auditable timeline so threats can be defended against in court, with funders, and "
                        "with regulators."
                    ),
                    "operator_value": (
                        "Stewards get one place to record what is standing today, watch for changes, and produce "
                        "defensible evidence when a parcel is challenged. Program coordinators see across many parcels."
                    ),
                    "project_outcome": (
                        "Stewards can produce a signed, replayable evidence bundle for any parcel on any date, "
                        "with provenance for every observation."
                    ),
                    "operating_principle": (
                        "Every condition assertion about a forest parcel cites the specific observations that produced it."
                    ),
                },
                "project_intelligence": {
                    "purpose": (
                        "Make forest preservation defensible by binding parcels, observations, and imagery into one "
                        "auditable timeline."
                    ),
                    "intent": [
                        "Make every parcel-condition claim defensible by tying it to dated, source-attributed observations."
                    ],
                },
                "validation_strategy": [
                    (
                        "first_slice_proof: A steward registers a forest parcel with boundary and baseline condition, "
                        "files one field observation with source attribution, ingests one remote-sensing snapshot for "
                        "the same date range, and the tracker renders a single dated current-state view that cites both observations."
                    )
                ],
                "risks": [
                    {
                        "title": "Observer safety leakage",
                        "description": "Parcel coordinates and observer identity can endanger land defenders if leaked.",
                    }
                ],
                "backlog": [
                    {
                        "title": "Govern Forest Preservation Tracker Program",
                        "customer": "Program coordinator running a conservation monitoring program.",
                        "recommended_first_slice": "Confirm the first path and release proof gates.",
                    },
                    {
                        "title": "Forest Parcel Records Service with Versioned Boundary",
                        "customer": "Steward registering and maintaining forest parcels at the conservation organization.",
                        "recommended_first_slice": "Steward registers a forest parcel with a closed-polygon boundary.",
                    },
                    {
                        "title": "Append-Only Forest Observation Ledger",
                        "customer": "Field observer and community monitor filing forest observations; verifier reading them later.",
                        "recommended_first_slice": "Field observer files one source-attributed observation for the parcel.",
                    },
                ],
                "components": [
                    {"component_id": "parcel-records", "label": "Forest Parcel Records Service"},
                    {"component_id": "observation-ledger", "label": "Forest Observation Ledger"},
                ],
                "diagrams": [
                    {"diagram_id": "D-001", "title": "System Context View"},
                    {"diagram_id": "D-002", "title": "First Slice Sequence View"},
                ],
                "release_plan": {
                    "label": "0.0.1",
                    "strategy": "Release 0.0.1 proves the first forest parcel evidence path before broader buildout.",
                },
                "program": {
                    "waves": [
                        {
                            "label": "Forest evidence primitive",
                            "validation": "Release proof reproduces the current-state view from cited observations.",
                        }
                    ]
                },
            },
        },
    )

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"shell_repo_name": "save-forest"})
    html = presenter.render_project_html({"project_intelligence": payload})
    story = payload["product_story"]
    leading_story = " ".join(story["paragraphs"][:3])

    assert payload["title"] == "Forest Preservation Tracker"
    assert payload["projection"]["origin"] == "accepted greenfield project"
    assert "accepted greenfield project" in payload["chips"]
    assert payload["focus_label"] == "Accepted focus"
    assert payload["open_label"] == "Open questions"
    assert "Forest Preservation Tracker focus" not in html
    assert "Open Forest Preservation Tracker questions" not in html
    assert story["paragraphs"][0].startswith("The steward")
    assert "keeps the work focused" in story["paragraphs"][0]
    assert "forest parcel" in story["paragraphs"][0]
    assert story["paragraphs"][1].startswith("Bottom line: release 0.0.1 succeeds")
    assert "leaves enough evidence for review" in story["paragraphs"][1]
    assert not any("The first path is straightforward:" in row for row in story["paragraphs"])
    assert "Radar" not in leading_story
    assert "Registry" not in leading_story
    assert "Atlas" not in leading_story
    assert "Target reality:" in payload["desired"]
    assert "User capability:" in payload["desired"]
    assert "Release trust:" in payload["desired"]
    assert "Stewards get one place" in payload["desired"]
    assert "Observer safety leakage" not in payload["desired"]
    assert "first complete path" not in payload["desired"].casefold()
    assert all(term not in payload["desired"] for term in ("Radar", "Registry", "Atlas", "Compass", "Casebook"))
    assert not any(row.startswith("After the product path is clear") for row in story["paragraphs"])
    assert story["supporting_records"] == []
    assert payload["answers"] == []
    assert "risks" in payload["sections"]
    assert 'class="project-panel project-risks"' in html
    assert "Who uses it?" not in html
    assert "Steward" in html
    assert "Field observer and community monitor" in html
    assert "Verifier" in html
    assert "Observer safety leakage" in html
    assert "Release 0.0.1 proof boundary" not in html
    assert "Planning can continue" not in html
    assert "Build is still blocked" not in html
    assert "Risks that block build" not in html
    assert "What is the first release boundary?" not in html
    assert "Inside first release" not in html
    assert "Outside until resolved" not in html
    assert payload["next_title"] == "Start implementation planning"
    assert "Open the first implementation plan first" in html
    assert "Human " + "takeaway" not in html
    assert "proof_title" not in payload
    assert "Planning facts" not in html
    assert "Build trust blockers" not in html
    assert "Planning confidence" not in html
    assert "Medium means the direction is usable for planning" not in html
    assert not any("A steward registers a forest parcel" in row for row in payload["known"])
    assert not any("The first complete path" in row for row in payload["known"])
    assert "Product direction accepted for planning." in payload["known"]
    assert any(row.startswith("Planned shape:") for row in payload["known"])
    assert payload["host_handoff_title"] == "Prompts to use next"
    assert "Use the first prompt to open the implementation plan" in html
    assert "Start the first implementation plan" not in html
    assert "Product decision owner and implementation owner" not in html
    assert "Expected output" not in html
    assert "Risk if delayed" not in html
    assert "Start implementation plan" in html
    assert "Implement first coding slice" in html
    assert html.index("Start implementation plan") < html.index("Implement first coding slice")
    assert "Revise project direction" in html
    assert "Forest Parcel Records Service is a `service`" not in html
    assert "Who uses Forest Parcel Records Service" not in html
    assert "repository operators" not in html
    assert "responsible for Own" not in html
    assert "Odylith, apply this greenfield proposal" not in html
    assert "Accept it" not in html
    assert 'title="Forest Parcel Records Service with Versioned Boundary"' not in html


def test_greenfield_product_story_does_not_repeat_hero_intro_or_numbered_first_path() -> None:
    intro = (
        "A musician or ensemble plays live. A laptop, phone, or tablet running LiveScore listens through its microphone. "
        "As the performance progresses, LiveScore transcribes what is being played and, at the end of the take, produces "
        "a clean, human-readable sheet-music PDF and MusicXML file. The wedge is the single-instrument live take: a solo "
        "player wants the score back without re-playing it into notation software."
    )
    first_path = (
        "The first complete path the product must prove is the solo monophonic instrument single take, offline analysis "
        "flow: 1. User opens the app and taps Record. 2. User plays a roughly 30-second line. 3. User taps Stop. "
        "4. The app shows the rendered score and offers downloadable files."
    )
    proof = (
        "Proof must show the accepted first path passes end to end: "
        "1. User opens the app and taps Record. 2. User plays a roughly 30-second line. 3. User taps Stop."
    )

    story = product_story.build_greenfield_product_story(
        title="- LiveScore: Live Performance",
        intro=intro,
        project={
            "intent": [
                f"Project objective: {intro}",
                "User or stakeholder outcome: The performer can hand the result to another player and get a recognizable reproduction of the take.",
                f"Success condition: {proof}",
                "Non-goals: live streaming notation, noisy-stage transcription, and cloud accounts in the first release.",
            ]
        },
        project_brief={
            "summary": intro,
            "operating_principle": "Every release claim stays attached to the user capability, source evidence, and proof boundary accepted in the product direction.",
        },
        first_path=first_path,
        release="0.0.1",
        release_plan={"strategy": proof},
        validation=[proof],
        accepted={},
        backlog=[],
        components=[
            {"label": "Audio Capture and Pre-processing Service"},
            {"label": "Pitch and Onset Detection Engine"},
            {"label": "Notation Export Service"},
        ],
        diagrams=[],
        actors=[],
    )
    story_json = json.dumps(story, sort_keys=True)

    assert story["headline"] == "Release 0.0.1 proves one usable first path"
    assert story["paragraphs"][0].startswith("A musician or ensemble plays live")
    assert story_json.count("A musician or ensemble plays live") == 1
    assert "1. User" not in story_json
    assert "2. User" not in story_json
    assert not any("The first path is straightforward" in row for row in story["paragraphs"])
    assert {row["label"] for row in story["release_contract"]} >= {
        "User problem",
        "First path",
        "Product boundary",
        "Owned capabilities",
        "Proof",
    }
    assert "1. User" not in json.dumps(story["release_contract"])


def test_greenfield_product_story_strips_markdown_prefaces_and_generic_proof_fallback() -> None:
    first_path = (
        "The first complete path to prove should be: user imports activity history, the product finds a likely recurring item, "
        "shows evidence for that item, guides the user through a decision, records the outcome, and checks the next cycle."
    )

    story = product_story.build_greenfield_product_story(
        title="Cleanup Assistant",
        intro="A user wants to reduce recurring waste without losing services they still need.",
        project={
            "intent": [
                "Project objective: A user wants to reduce recurring waste without losing services they still need.",
                "User or stakeholder outcome: The user can review one recurring item, understand the evidence, and decide safely.",
                "Success condition: Proof must show the accepted first path passes end to end.",
            ]
        },
        project_brief={},
        first_path=first_path,
        release="0.0.1",
        release_plan={"strategy": "Proof must show the accepted first path passes end to end."},
        validation=["Proof must show the accepted first path passes end to end."],
        accepted={},
        backlog=[],
        components=[{"label": "Activity Ingestion Service"}],
        diagrams=[],
        actors=[("", "**Account owner**", "**wants to reduce waste without losing important services.")],
    )
    rendered = json.dumps(story, sort_keys=True)

    assert story["headline"] == "Release 0.0.1 proves one usable first path"
    assert "**" not in rendered
    assert "complete path to prove should be" not in rendered.casefold()
    assert "Reviewer can compare the scenario result" not in rendered
    assert any(row["label"] == "First path" for row in story["release_contract"])
    assert any("representative input" in row["body"] for row in story["release_contract"] if row["label"] == "Proof")


def test_greenfield_project_sections_do_not_reuse_first_path_as_page_filler(tmp_path: Path) -> None:
    first_path = (
        "The first complete path the product must prove is the solo monophonic instrument single take, offline analysis "
        "flow: 1. User opens the app and taps Record. 2. User plays a roughly 30-second line. 3. User taps Stop. "
        "4. The app shows a rendered score and downloadable MusicXML."
    )
    proposal = {
        "mode": "greenfield_apply_ready",
        "intent": {"title": "Practice Score Assistant"},
        "observed_source": {"source_posture": "docs_only"},
        "project_brief": {
            "purpose": "A musician records a short practice take and gets a readable score they can review.",
            "operator_value": "The performer can inspect the take, score, and export without replaying the music into notation software.",
            "operating_principle": "Every release claim stays tied to the take state, evidence, and explicit non-goals.",
        },
        "project_intelligence": {
            "state": [
                (
                    "The product's primary state object is the Take. A Take moves through these states during the first journey: "
                    "idle: no audio capture active. capturing: sound detected. transcribed: note events resolved. "
                    "scored: renderable notation produced. exported: score artifacts written. A Take owns: raw audio, note events, score model, rendered score, export artifacts."
                )
            ],
        },
        "validation_strategy": [f"first_slice_proof: {first_path}"],
        "open_questions": [
            {"question": "Does the first release need live notation or post-take export?"}
        ],
        "release_plan": {"label": "0.0.1", "strategy": "Release 0.0.1 proves the accepted score-capture boundary."},
        "backlog": [
            {
                "title": "Establish Practice Score Assistant Program",
                "recommended_first_slice": first_path,
                "evidence_tier": "user_intent",
            },
            {
                "title": "Prove Audio Capture Service",
                "problem": f"The first user path must be built around the accepted product path: {first_path}",
                "product_view": "Audio Capture Service owns microphone input and take buffering.",
                "recommended_first_slice": first_path,
                "evidence_tier": "odylith_assumption",
            },
            {
                "title": "Define Pitch And Onset Detection Engine Boundary",
                "product_view": "Pitch engine owns pitch tracking and onset segmentation.",
                "recommended_first_slice": first_path,
                "evidence_tier": "odylith_assumption",
            },
        ],
        "components": [
            {
                "label": "Audio Capture Service",
                "responsibility": "Audio capture owns microphone input and take buffering.",
            }
        ],
        "diagrams": [{"title": "System Context View"}],
    }

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})
    html = presenter.render_project_html({"project_intelligence": payload})
    first_path_summary = "The solo monophonic instrument single take, offline analysis flow."
    repeated_surfaces = json.dumps(
        {
            "answers": payload["answers"],
            "jobs": payload["jobs"],
            "known": payload["known"],
            "claim_evidence": payload["claim_evidence"],
        },
        sort_keys=True,
    )
    release_contract_json = json.dumps(payload["product_story"]["release_contract"], sort_keys=True)

    assert ("First path", first_path_summary) not in payload["answers"]
    assert first_path_summary not in repeated_surfaces
    assert "The first complete path the product must prove" not in repeated_surfaces
    assert "User opens the app" not in repeated_surfaces
    assert "User opens the app" not in release_contract_json
    assert payload["scenario_details"][0] == ("First path", first_path_summary)
    assert payload["jobs"][0][0] == "Establish Program"
    assert "Establish Practice Score Assistant Program" not in html
    assert payload["jobs"][0][1].startswith("Sets the accepted product story")
    assert payload["answers"] == []
    assert 'class="project-panel project-answer-strip"' not in html
    assert payload["jobs"][1][1] == "Owns microphone input and take buffering."
    assert payload["jobs"][2][0] == "Define Pitch and Onset Detection Engine Boundary"
    assert len({row[1] for row in payload["jobs"]}) == len(payload["jobs"])
    assert all("odylith" not in row[2].casefold() for row in payload["jobs"])
    assert "boundary_title" not in payload
    assert "included_label" not in payload
    assert "excluded_label" not in payload
    assert "included" not in payload
    assert "excluded" not in payload
    assert not any("First accepted path:" in row or "First proposed path:" in row for row in payload["known"])


def test_greenfield_project_participants_collapse_role_description_duplicates(tmp_path: Path) -> None:
    proposal = {
        "mode": "greenfield_apply_ready",
        "intent": {"title": "Practice Score Assistant"},
        "observed_source": {"source_posture": "docs_only"},
        "project_brief": {
            "purpose": "A musician records a short take and gets a readable score they can review.",
            "operator_value": "The performer can inspect the take and score without replaying the music into notation software.",
            "operating_principle": "Every release claim stays tied to the accepted user capability and evidence.",
        },
        "project_intelligence": {
            "owners": [
                "Solo performer (primary): the musician who plays the take and reads the resulting score.",
                "Solo performer (primary): The musician who plays the take and reads the resulting score.",
            ],
        },
        "validation_strategy": [
            "first_slice_proof: A solo performer records one take and reviews the generated score."
        ],
        "release_plan": {"label": "0.0.1"},
        "backlog": [
            {
                "title": "Establish Practice Score Assistant Program",
                "customer": (
                    "Solo performer (primary): the musician who plays the take and reads the resulting score; "
                    "Solo performer (primary); "
                    "Practicing student: uses the score later."
                ),
                "recommended_first_slice": "A solo performer records one take and reviews the generated score.",
                "domain_intelligence": {
                    "actors": [
                        "Solo performer (primary): the musician who plays the take and reads the resulting score.",
                        "Practicing student: uses the score later.",
                    ],
                },
            }
        ],
        "components": [],
        "diagrams": [],
    }

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})
    titles = [row[1] for row in payload["actors"]]

    assert titles.count("Solo performer (primary)") == 1
    assert titles.count("Practicing student") == 1
    assert not any(": the musician" in title.casefold() for title in titles)


def test_greenfield_project_copy_does_not_splice_first_path_sentences_into_actor_cards(tmp_path: Path) -> None:
    first_path = (
        "A field team submits a request that needs review. "
        "The workspace suggests an accountable owner and records the final decision."
    )
    proposal = {
        "mode": "greenfield_apply_ready",
        "intent": {"title": "Request Handoff App"},
        "observed_source": {"source_posture": "docs_only"},
        "project_brief": {
            "purpose": "Field teams need one place to hand off a request, understand ownership, and see the decision.",
            "operator_value": "The requester and reviewer can see the same request state without reconstructing context from chat.",
        },
        "project_intelligence": {
            "intent": [
                "Project objective: Field teams need one place to hand off a request, understand ownership, and see the decision.",
                "User or stakeholder outcome: The requester and reviewer can see who owns the next action and what evidence supports the decision.",
                "Success condition: Proof must show that one request moves through review with visible state, evidence, and outcome.",
            ],
            "owners": [
                (
                    "Request coordinator: uses Request Handoff App to complete "
                    "A field team submits a request that needs review. The workspace suggests an accountable owner."
                ),
                "Review lead: verifies that The proof is strong enough before broader scope is accepted.",
            ],
        },
        "validation_strategy": [f"first_slice_proof: {first_path}"],
        "release_plan": {"label": "0.0.1"},
        "backlog": [
            {
                "title": "Establish Request Handoff Program",
                "customer": (
                    "Request coordinator: uses Request Handoff App to complete "
                    "A field team submits a request that needs review. The workspace suggests an accountable owner."
                ),
                "recommended_first_slice": first_path,
            }
        ],
        "components": [
            {"label": "Request Intake Surface"},
            {"label": "Owner Assignment Service"},
            {"label": "Decision Review Workspace"},
            {"label": "Evidence Attachment Store"},
            {"label": "Notification Freshness Worker"},
        ],
        "diagrams": [],
    }

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})
    rendered = json.dumps(payload, sort_keys=True)
    actor_bodies = [row[2] for row in payload["actors"]]
    release_contract = json.dumps(payload["product_story"]["release_contract"], sort_keys=True)

    assert any("to complete the accepted first path" in body for body in actor_bodies)
    assert "to complete A field team" not in rendered
    assert "when the path is." not in rendered
    assert "verifies that The" not in rendered
    assert "plus 2 more" not in release_contract
    assert "plus 1 more" not in rendered
    assert "with additional accepted capabilities tracked separately" in release_contract


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

    assert 'href="?tab=radar&amp;workstream=B-321" data-tooltip="Customer intake workflow"' in html
    assert 'href="?tab=casebook&amp;bug=CB-654" data-tooltip="Rollback owner missing"' in html
    assert 'href="?tab=atlas&amp;diagram=D-987" data-tooltip="First slice flow"' in html
    assert 'title="Customer intake workflow"' not in html
    assert 'href="?tab=registry">Registry</a>' not in html
    assert 'href="?tab=radar">radar</a>' not in html
    assert "Registry, radar" in html
    assert 'href="technical-plans/in-progress/demo.md"' in html
    assert 'href="?tab=registry" data-tooltip=' not in html


def test_shell_text_linkifier_keeps_surface_names_plain_and_links_ids(tmp_path: Path) -> None:
    html = dashboard_shell_links.linkify_shell_text(
        "Radar and Registry mention B-321, D-987, and odylith/technical-plans/in-progress/demo.md.",
        repo_root=tmp_path,
        output_path=tmp_path / "odylith" / "index.html",
        preferred_scope_key="demo",
    )

    assert "Radar and Registry mention" in html
    assert 'href="?tab=radar">Radar</a>' not in html
    assert 'href="?tab=registry">Registry</a>' not in html
    assert 'href="?tab=radar&amp;workstream=B-321">B-321</a>' in html
    assert 'href="?tab=atlas&amp;workstream=B-321&amp;diagram=D-987">D-987</a>' in html


def test_project_intelligence_presenter_links_project_jobs_to_radar_workstreams() -> None:
    html = presenter.render_project_html(
        {
            "project_intelligence": {
                "title": "Fixture project",
                "intro": "Fixture intro.",
                "chips": [],
                "sections": ["jobs"],
                "jobs_title": "What is proposed?",
                "jobs_note": "Fixture jobs note.",
                "jobs": [
                    ("Prove first capability", "Owns the first release capability.", "Inferred", "B-321"),
                ],
                "governance_titles": {"B-321": "Prove first capability"},
            }
        }
    )

    assert 'class="project-job-title-link" target="_top" href="?tab=radar&amp;workstream=B-321"' in html
    assert 'href="?tab=radar&amp;workstream=B-321" data-tooltip="Prove first capability"' in html
    assert 'title="Prove first capability"' not in html


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


def test_project_intelligence_hero_rail_labels_do_not_repeat_project_title() -> None:
    project_title = "Long Consumer Product Title That Already Appears In The Hero"
    payload = {
        "project_intelligence": {
            "eyebrow": "fixture lens",
            "title": project_title,
            "intro": "Fixture project intro.",
            "chips": ["fixture"],
            "focus_label": f"Accepted {project_title} focus",
            "focus": "Promote only after proof passes.",
            "open_label": f"Open {project_title} questions",
            "open": ["Which input path proves the first release?"],
            "sections": [],
        }
    }

    html = presenter.render_project_html(payload)

    assert f"Accepted {project_title} focus" not in html
    assert f"Open {project_title} questions" not in html
    assert "<p>Accepted focus</p>" in html
    assert "<p>Open questions</p>" in html


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
    assert "claim_evidence" not in payload["sections"]
    assert "Proposed first-path scenario" not in html
    assert "Accepted first-path scenario" not in html
    assert "What can be trusted about" not in html
    assert "Direction accepted" not in html
    assert "Shape to build" not in html
    assert "Proof to earn" not in html
    assert "software behavior is not trusted yet" not in html
    assert "View claim audit" not in html
    assert "Can " not in html
    assert "move into implementation planning" not in html
    assert "Human " + "takeaway" not in html
    assert "Planning can continue" not in html
    assert "Build is still blocked" not in html
    assert "Risks that block build" not in html
    assert "What is the first release boundary?" not in html
    assert "Inside first release" not in html
    assert "Outside until resolved" not in html
    assert "What must be controlled before" not in html
    assert "Build trust blockers" not in html
    assert "Proposal confidence" not in html
    assert "state" not in payload["sections"]
    assert "Status now" not in html
    assert "Where does this stand" not in html
    assert "project-state-grid" not in html
    assert "Source-backed runtime" not in payload["chips"]
    assert "Target reality:" in payload["desired"]
    assert "User capability:" in payload["desired"]
    assert "Release trust:" in payload["desired"]
    assert " before." not in payload["desired"]
    assert "Release" in payload["desired"]
    assert all(term not in payload["desired"] for term in ("Radar", "Registry", "Atlas", "Compass", "Casebook"))
    assert any(row["evidence"] in {"user-stated", "inferred", "needs validation"} for row in payload["claim_evidence"])
    assert payload["sections"][0] == "product_story"
    assert payload["product_story_title"] == "Product Story"
    story = payload["product_story"]
    assert isinstance(story, dict)
    assert "the team can prove" not in story["headline"]
    assert "accept the" not in story["headline"].casefold()
    assert story["headline"].startswith("Release 0.0.1 proves")
    assert story["release_contract"]
    assert {row["label"] for row in story["release_contract"]} >= {"User problem", "First path", "Product boundary", "Proof"}
    assert not any(row["label"] in {"First accepted path", "User value", "Release boundary", "Operating rule"} for row in story["release_contract"])
    assert len(story["paragraphs"]) >= 2
    assert any("keeps the work focused" in row for row in story["paragraphs"])
    assert any("Bottom line: release" in row for row in story["paragraphs"])
    assert not any("After the product path is clear" in row for row in story["paragraphs"])
    assert story["supporting_records"] == []
    assert all(term not in json.dumps(story) for term in ("Radar", "Registry", "Atlas", "Compass"))
    assert "Product Story" in html
    assert payload["answers"] == []
    assert "risks" in payload["sections"]
    assert html.index("project-product-story") < html.index("project-participants") < html.index("project-risks")
    assert 'class="project-panel project-risks"' in html
    assert 'class="project-panel project-answer-strip"' not in html
    assert "Who uses it?" not in html
    assert "the team can prove" not in html
    assert "project-story-contract" in html
    assert payload["host_handoff_title"] == "How to continue in the host chat"
    assert "Odylith, apply this greenfield proposal" in html
    assert "Revise it" in html
    assert "Reject it" in html
    assert "Paste the chosen prompt into the same host chat" in html
    assert "proposal JSON" in html
    assert "Radar" not in html
    assert "Registry" not in html
    assert "Atlas" not in html
    assert "Topology spine" not in html
    assert "Story root" not in html
    assert "How the story becomes governance" not in html


def test_greenfield_risk_posture_uses_readable_categories() -> None:
    risks = [
        "Unsafe action can harm people or property if release safeguards do not block the change.",
        "Repeated commands can exceed configured thresholds when the limit check is bypassed.",
        "Measurement drift or poor signal placement can make an invalid state appear stable.",
        "External provider downtime can block the handoff when retry and recovery behavior is unclear.",
    ]

    rows = _risk_classes(risks)

    assert [row["risk"] for row in rows] == [
        "Safety boundary",
        "Control limits",
        "Measurement reliability",
        "External dependency",
    ]
    for row, risk in zip(rows, risks, strict=True):
        assert row["meaning"] == risk
        assert row["risk"] not in row["meaning"]


def test_greenfield_risk_posture_does_not_echo_numbered_first_path() -> None:
    risks = [
        (
            "If the accepted first path is ambiguous, users cannot tell which state changed or which source produced "
            "the evidence: The first complete path the product must prove is the solo take flow: 1. User opens the app. "
            "2. User records audio. 3. User exports the result."
        )
    ]

    rows = _risk_classes(risks)

    assert rows[0]["meaning"] == (
        "If the accepted first path is ambiguous, users cannot tell which state changed or which source produced the evidence."
    )
    assert "1. User" not in rows[0]["meaning"]
    assert "first complete path" not in rows[0]["meaning"].casefold()


def test_project_intelligence_greenfield_story_skips_meta_acceptance_path(tmp_path: Path) -> None:
    proposal = {
        "mode": "greenfield_apply_ready",
        "intent": {"title": "Knowledge Base Assistant"},
        "project_intelligence": {
            "intent": [
                "Project objective: Help support teams answer customer questions with reviewed citations.",
                "User or stakeholder outcome: A support agent uploads an article, asks a question, reviews the answer, and keeps a citation record.",
                "Success condition: one article answer review path is proven with reviewer-visible citation evidence.",
                "Non-goals: autonomous customer replies, production data ingestion, and unreviewed answer publication.",
            ],
            "owners": ["Support agent owns answer review and citation acceptance."],
        },
        "program": {"waves": []},
        "release_plan": {"label": "0.0.1", "strategy": "Promote only after answer review proof exists."},
        "observed_source": {"source_posture": "docs_only"},
        "backlog": [
            {
                "title": "Guide knowledge assistant program",
                "recommended_first_slice": (
                    "Accept the answer-review path, component boundaries, release 0.0.1 proof gates, "
                    "and explicit non-goals before implementation planning starts."
                ),
                "evidence_tier": "proposal",
            },
            {
                "title": "Prove article ingestion and answer review",
                "recommended_first_slice": (
                    "Prove one article from upload through extracted answer, reviewer approval, and citation record."
                ),
                "evidence_tier": "proposal",
            },
        ],
        "components": [
            {"label": "Article Intake", "responsibility": "Owns upload and parsing."},
            {"label": "Answer Review Core", "responsibility": "Owns answer review and citation evidence."},
        ],
        "diagrams": [{"title": "Article Answer Flow", "slug": "article-answer-flow"}],
        "_accepted_project": {
            "created": {
                "workstreams": [
                    {"idea_id": "B-001", "title": "Guide knowledge assistant program"},
                    {"idea_id": "B-002", "title": "Prove article ingestion and answer review"},
                ],
                "diagrams": ["D-001"],
            }
        },
    }

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})
    html = presenter.render_project_html({"project_intelligence": payload})

    assert "one article from upload" in payload["scenario"][4].casefold()
    assert "accept the answer-review path" not in payload["product_story"]["headline"].casefold()
    assert payload["product_story"]["headline"] == "Release 0.0.1 proves one usable first path"
    assert payload["governance_titles"]["B-002"] == "Prove article ingestion and answer review"
    assert 'class="project-job-title-link" target="_top" href="?tab=radar&amp;workstream=B-002"' in html
    assert 'data-tooltip="Prove article ingestion and answer review"' in html


def test_project_intelligence_greenfield_title_drops_operator_instructions(tmp_path: Path) -> None:
    proposal = _apply_ready_greenfield_fixture(
        tmp_path,
        prompt=(
            "Draft a product-first greenfield proposal for a plant monitor that checks the status of my plants "
            "and tells me when water or nutrients are needed. "
            "The goal is to keep my plants healthy, optimal and alive. "
            "Show the interpretation and direction choices first. Do not write records until I confirm."
        ),
    )

    payload = builder.build_project_intelligence_payload(repo_root=tmp_path, shell_payload={"greenfield_proposal": proposal})

    assert "draft a product" not in payload["title"].casefold()
    assert "show the interpretation" not in payload["title"].casefold()
    assert "do not write" not in payload["title"].casefold()


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
    assert "--project-type-title-size: 42px;" in css
    assert "--project-type-intro-size: 22px;" in css
    assert "--project-type-hero-eyebrow-size: 15px;" in css
    assert ".project-answer-table table" in css
    assert ".project-answer-table th" in css
    assert ".project-answer-table td strong" in css
    assert ".project-answer-table td p" in css
    assert ".project-risk-card" in css
    assert ".project-risk-grid" in css
    assert ".project-workstream-chip" in css
    assert "var(--surface-workstream-button-padding, 1px 8px)" in css
    assert "var(--surface-workstream-button-font-size, 12px)" in css
    assert ".project-label-chip" in css
    assert ".project-label-chip-success" in css
    assert ".project-label-chip-warning" in css
    assert ".project-job-card em" not in css
    assert ".project-chips span:nth-child" not in css
    assert ".project-job-workstream .project-deeplink" not in css
    assert "-webkit-line-clamp" not in css
    assert "repeat(auto-fit, minmax(190px, 1fr))" in css
    assert "grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) minmax(240px, 0.58fr);" in css
    assert ".project-proof-grid article > p" in css
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
    assert ".project-host-prompt-grid {\n  display: grid;\n  grid-template-columns: minmax(0, 1fr);" in css
    assert ".project-host-prompt {\n  display: grid;\n  grid-template-columns: minmax(180px, 0.28fr) minmax(0, 1fr);" in css
    assert "font-size: 22px;" in css
    assert "font-size: 18px;" in css
    assert ".project-actor-grid" in css
    assert ".project-system-grid" not in css
    assert ".project-flow-grid" not in css
    assert "font-size: var(--project-type-content-size);" in css
    assert "font-weight: 800" not in css
    assert "clamp(" not in css
    assert "letter-spacing: -" not in css
