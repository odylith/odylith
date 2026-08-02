from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import collect_rendered_package_artifacts
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_components
from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import proposal_memory
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import (
    build_greenfield_package_report,
    GreenfieldCompletionPackage,
    _component_preview_path_fidelity_issues,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_package_hygiene import prewrite_path_leak_issues
from odylith.runtime.domain_intelligence.greenfield_preconfirm_repair import repair_greenfield_package_until_clean
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import semantic_compiler_issues
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.project_intelligence.greenfield import build_greenfield_payload
from tests.unit.runtime.greenfield_proposal_fixtures import CONFIRMED_INTENT_TEXT
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_intent_with_authority
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import commit_precompiled_greenfield_proposal
from tests.unit.runtime.greenfield_proposal_fixtures import seal_compiled_greenfield_transaction
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


ROOT = Path(__file__).resolve().parents[3]
APPLY_PREWRITE_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_prewrite.py"
APPLY_COMPONENTS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_components.py"
APPLY_DIAGRAMS_PATH = ROOT / "src/odylith/runtime/domain_intelligence/greenfield_apply_diagrams.py"
CALORIE_BURN_CONFIRMED_INTENT_TEXT = """# Calorie Burn Optimizer

## Product story
Most people who want to lose fat or train for an event don't actually know how much energy they burn on a given day, so they guess at how much to eat and how hard to train. The Calorie Burn Optimizer turns the day's planned and logged activity into a trustworthy energy-out picture, then recommends the specific adjustments - workout intensity, session length, or activity mix - that move someone toward their goal without overtraining or under-fueling. The win is a clear daily answer to "did I burn enough, and what should I change tomorrow?"

## State object
The central object is a daily energy profile for one person: resting metabolic baseline, logged activities with their estimated calorie cost, a target burn for the day, and the running gap between actual and target. This profile accumulates over time into a trend the optimizer reasons against.

## First complete path
A person sets a goal and basic body stats, logs or imports a day's activities, and immediately sees their estimated total burn against target plus one concrete recommendation for the next day. That single loop — profile in, burn estimate out, actionable adjustment — is the first thing that must work end to end.

## Human actors
- The individual optimizing their own calorie burn (primary)
- A coach or trainer reviewing a client's burn trend and goals (secondary)

## External systems
- Wearable and fitness trackers as an activity-data source
- A reference calorie-cost dataset for activity types

## Internal product systems
- Burn estimation engine that converts body stats plus logged activity into an energy-out number
- Goal and target service that sets and tracks the daily burn target against the trend
- Recommendation engine that proposes the next adjustment
- Activity log and profile store

## Critical assumptions
- A single person optimizing their own burn is the launch user, not a multi-client coaching platform
- Estimates from standard formulas and MET tables are accurate enough for guidance, not medical precision
- Activity can be entered manually at first; live wearable sync is valuable but not required for the first path
- Calorie burn is the focus; full diet and intake tracking is out of scope for the first release

## Ambiguities
- Is the optimizer an active recommender that prescribes changes, or a passive estimator that only tracks burn?
- Whether goals are weight-loss driven, performance driven, or both
- Whether wearable integration is in scope for the first release or a later wave

## Proof boundary
Proven when one person can set a goal, log a day of activity, see an estimated total burn against target, and receive one next-day adjustment recommendation - using manual entry and standard estimation, no wearable sync required.
"""
SUN_BURN_CONFIRMED_INTENT_TEXT = """## SunRecover — sunburn relief and skin-recovery coach

### Product story
A person comes home from a day outside with a painful burn, an uneven tan they want gone, and worry about lasting skin damage. SunRecover meets them in that moment: they snap a photo of the affected skin and answer a few quick questions about pain, timing, and skin type, and the app returns a clear, staged recovery plan — what to do in the next hour, the next few days, and the next couple of weeks to calm the burn, fade the tan evenly, and support the skin's own repair. It tracks healing day over day, adjusts the plan as the skin changes, and flags when something looks serious enough to see a clinician rather than treat at home.

### State object
The unit of truth is a recovery episode: one sunburn or sun-exposure event for one person, holding the initial assessment (severity, body area, skin type, time since exposure), the staged care plan, the daily check-in log with photos and symptom scores, and the healing trajectory derived from those check-ins. An episode moves from assessed, to active recovery, to healed or escalated-to-care.

### First complete path
A user opens the app after a burn, captures a photo and answers the intake questions, and immediately receives a severity read and a first-24-hours action plan. Over the following days the app prompts daily check-ins, compares new photos and symptom scores against the baseline, updates the plan as the burn settles and the tan fades, and marks the episode healed — or surfaces a clear escalation warning if severity or warning signs cross a safety threshold.

### Human actors
- Sun-exposed individual recovering a burn, fading a tan, and minimizing skin damage
- Caregiver managing recovery on behalf of a child or family member
- Dermatology or primary-care clinician receiving an escalation hand-off or shared episode summary

### External systems
- Device camera and photo library for capturing and storing skin images
- A skin-assessment model or service that grades burn severity and tracks change from images
- UV index and location weather data to time care and warn about re-exposure
- Optional clinician or telehealth channel for escalation referrals

### Internal product systems
- Intake and severity assessment engine
- Staged recovery-plan generator (burn relief, even-tan fading, repair support)
- Daily check-in and healing-trajectory tracker
- Safety and escalation rules engine
- Episode history and reminder/notification service

### Critical assumptions
- Image-based severity grading is good enough to guide self-care and trigger escalation, but never replaces medical diagnosis
- Care guidance is grounded in established dermatology and sun-care evidence, not invented remedies
- Users will complete short daily check-ins for the recovery window
- "Remove tan quickly and optimally" means safe, evidence-based fading and repair, not aggressive or risky methods

### Ambiguities
- Scope of "skin damage": short-term burn recovery only, or also longer-term concerns like pigmentation, peeling, and aging signs?
- Regulatory posture: positioned as general wellness guidance, or pursuing a medical-device/clinical claim that changes the proof and compliance bar?
- Product recommendations: does the app suggest or sell specific products (aftercare, SPF), or stay vendor-neutral?
- Platform target: mobile-first native, or web?

### Proof boundary
This is a confirmation-only draft, so no product code exists yet. The first thing the product must prove is that the intake-to-first-plan path produces a safe, evidence-grounded recovery plan and correctly raises an escalation warning when severity or warning signs cross a safety threshold. A close second is that day-over-day check-ins reliably detect whether skin is healing or worsening.
"""
def test_greenfield_apply_prewrite_component_and_diagram_phases_stay_dedicated() -> None:
    parent_source = APPLY_PREWRITE_PATH.read_text(encoding="utf-8")
    component_source = APPLY_COMPONENTS_PATH.read_text(encoding="utf-8")
    diagram_source = APPLY_DIAGRAMS_PATH.read_text(encoding="utf-8")

    assert len(parent_source.splitlines()) < 800
    assert "greenfield_apply_components.render_prewrite_component_specs" in parent_source
    assert "greenfield_apply_components.preview_prewrite_components" in parent_source
    assert "greenfield_apply_diagrams.render_prewrite_atlas_sources" in parent_source
    assert "greenfield_apply_diagrams.allocated_diagram_ids" in parent_source
    for moved in (
        "def render_prewrite_component_specs",
        "def preview_prewrite_components",
        "def component_authoring_prewrite_inputs",
        "def component_dependency_lines",
        "def component_risk_lines",
        "def allocated_diagram_ids",
        "def render_prewrite_atlas_sources",
        "def _dependency_clause_phrase",
        "_COMPONENT_RISK_TOKENS",
    ):
        assert moved not in parent_source
    assert "def render_prewrite_component_specs" in component_source
    assert "def preview_prewrite_components" in component_source
    assert "def component_authoring_prewrite_inputs" in component_source
    assert "def component_dependency_lines" in component_source
    assert "def component_risk_lines" in component_source
    assert "def allocated_diagram_ids" in diagram_source
    assert "def render_prewrite_atlas_sources" in diagram_source


def test_prewrite_safety_evidence_records_dry_run_preview_before_commit() -> None:
    evidence = greenfield_apply_prewrite.prewrite_safety_evidence(
        validation_gate={"status": "passed"},
        release_target_result={"dry_run": True, "release_id": "release-0-0-1", "selector": "0.0.1"},
        release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
        release_selector="0.0.1",
    )

    assert evidence["status"] == "passed"
    assert evidence["checks"] == {
        "validation_gate_passed": True,
        "release_target_dry_run": True,
        "release_assignment_dry_run": True,
    }


def _proposal(tmp_path: Path) -> dict[str, object]:
    return greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(
            CONFIRMED_INTENT_TEXT,
            prompt="Draft a greenfield proposal for a municipal permit review workspace",
            repo_root=tmp_path,
            write_files=True,
        ),
    )


def test_confirmed_completion_reconciles_release_plan_to_repaired_backlog_titles(tmp_path: Path) -> None:
    confirmed_intent = confirmed_intent_with_authority(
        """# Product Intent Confirmation: Breakeven Solver Evaluation Workspace

## Product Story
PDE researchers need one reviewable workspace for turning neural and classical solver evidence into a bounded release decision without spreading assumptions across notes, spreadsheets, and ad hoc messages.

## State Object
A solver evaluation case tracks benchmark dataset, PDE family, neural solver run, classical solver run, error target, training budget, inference cost, breakeven solve count, reviewer note, invalid assumption flag, export status, and version history.

## Human Actors
Evaluation researcher; benchmark reviewer; release decision owner.

## First Complete Path
One evaluator can create a solver evaluation case, add neural and classical runs, match error targets, compute breakeven complexity, flag invalid assumptions, and export a reproducible evidence packet.

## Proof Boundary
Release 0.0.1 succeeds when one benchmark case can be created, reviewed, blocked for invalid assumptions, and exported with replayable evidence without claiming universal solver superiority.
""",
        prompt="Productize the PDE solver evaluation paper.",
        repo_root=tmp_path,
        write_files=True,
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Productize the PDE solver evaluation paper.",
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )

    completed = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    child_titles = [str(row["title"]) for row in completed["backlog"][1:]]
    release_plan = completed["release_plan"]
    assert release_plan["target_workstream_titles"] == child_titles
    assert release_plan["release_stages"][0]["workstream_titles"] == [child_titles[0]]


def test_confirmed_completion_repairs_slide_style_proof_metric_projection(tmp_path: Path) -> None:
    confirmed_intent = confirmed_intent_with_authority(
        """Slide 1 - Breakeven Solver Evaluation Workspace
- Why: PDE researchers need one reviewable workspace for turning neural and classical solver evidence into a bounded release decision without spreading assumptions across notes, spreadsheets, and ad hoc messages.
- People: Evaluation researcher; benchmark reviewer; release decision owner.

Slide 2 - Product Shape
- State: A solver evaluation case tracks benchmark dataset, PDE family, neural solver run, classical solver run, error target, training budget, inference cost, breakeven solve count, reviewer note, invalid assumption flag, export status, and version history.
- First workflow: One evaluator can create a solver evaluation case, add neural and classical runs, match error targets, compute breakeven complexity, flag invalid assumptions, and export a reproducible evidence packet.

Slide 3 - Release Proof
- Proof: Release 0.0.1 succeeds when one benchmark case can be created, reviewed, blocked for invalid assumptions, and exported with replayable evidence without claiming universal solver superiority.
- Out of scope: broad claims outside the first release.

Speaker Notes
Make it beautiful; this note is not product truth.
""",
        prompt="Productize the PDE solver evaluation slide deck.",
        repo_root=tmp_path,
        write_files=True,
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Productize the PDE solver evaluation slide deck.",
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent,
    )

    completed = complete_confirmed_proposal(proposal, release_selector="0.0.1")

    assert semantic_compiler_issues(completed) == []
    root_metrics = " ".join(str(row) for row in completed["backlog"][0]["success_metrics"])
    assert "exported with replayable evidence" not in root_metrics.casefold()
    assert "export a reproducible evidence packet" in root_metrics.casefold()
    assert "exported reproducible evidence packet" in root_metrics.casefold()
    assert "slide 3" not in root_metrics.casefold()
    assert "speaker notes" not in root_metrics.casefold()


def test_greenfield_prewrite_project_dashboard_uses_target_repo_language_signal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)
    (tmp_path / "package.json").write_text('{"scripts":{"test":"vitest"}}\n', encoding="utf-8")
    proposal = _proposal(tmp_path)
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")

    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    prompts = prewrite.package.project_dashboard_preview.get("host_handoff_prompts", [])
    first_prompt = str(prompts[0].get("prompt", "")) if prompts else ""

    assert prewrite.package.prewrite_safety_preview["status"] == "passed"
    assert prewrite.package.prewrite_safety_preview["checks"] == {
        "validation_gate_passed": True,
        "release_target_dry_run": True,
        "release_assignment_dry_run": True,
    }
    assert prewrite.package.surface_refresh_preview["status"] == "passed"
    assert prewrite.package.surface_refresh_preview["surfaces"] == [
        "radar",
        "registry",
        "atlas",
        "compass",
        "tooling_shell",
    ]
    assert prewrite.package.component_registry_preview
    assert prewrite.package.traceability_plan is not None
    assert prewrite.package.traceability_plan.workstreams
    assert prewrite.package.traceability_plan.workstreams[0].idea_id == "B-001"
    assert prewrite.package.traceability_plan.component_workstreams
    assert len(prewrite.package.atlas_review_date) == len("2026-07-07")
    assert len(prewrite.package.atlas_diagram_ids) == len(prewrite.package.rendered_atlas_sources)
    assert len(prewrite.package.atlas_catalog_rows) == len(prewrite.package.rendered_atlas_sources)
    assert {
        str(row.get("diagram_id", "")).strip()
        for row in prewrite.package.atlas_catalog_rows
    } == set(prewrite.package.atlas_diagram_ids)
    assert all(
        not Path(path).is_absolute()
        for row in prewrite.package.atlas_catalog_rows
        for path in row.get("related_backlog", [])
    )
    assert "odylith-greenfield-prewrite" not in json.dumps(prewrite.package.atlas_catalog_rows)
    accepted_at = str(prewrite.package.accepted_project_preview.get("accepted_at", "")).strip()
    assert accepted_at and accepted_at != "prewrite"
    assert prewrite.package.compass_memory_preview["ts_iso"] == accepted_at
    assert prewrite.package.project_brief_record_text.startswith("# Municipal Permit Review Workspace Project Brief")
    assert f"- accepted_at: {accepted_at}" in prewrite.package.project_brief_record_text
    assert all(not Path(str(token)).is_absolute() for token in prewrite.package.compass_memory_preview["artifacts"])
    assert all(
        isinstance(row.get("implementation_handoff"), dict) and row["implementation_handoff"]
        for row in prewrite.package.component_registry_preview
    )
    assert "Current signal: existing repo language signals point to TypeScript" in first_prompt


def _disable_refreshes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        lambda **_kwargs: surface_refresh_preview_fixture(),
    )
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "passed", "test_refresh_stub": True},
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


def _force_bad_rendered_specs(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        greenfield_apply_components,
        "render_prewrite_component_specs",
        lambda **_kwargs: {"Broken Component": "Broken Component owns maintains state."},
    )


def _prewrite_backlog_result(proposal: dict[str, object]) -> dict[str, object]:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, dict)]
    first_path = str(proposal["intent"]["first_path"])
    proof_boundary = str(proposal["intent"]["proof_boundary"])
    created = [
        {
            "idea_id": f"B-{index:03d}",
            "title": str(row.get("title", "")),
            "idea_path": f"odylith/radar/source/ideas/test-{index}.md",
        }
        for index, row in enumerate(rows, start=1)
    ]
    return {
        "created": created,
        "idea_files": {
            f"/tmp/test-{index}.md": (
                f"# {row['title']}\n\n"
                f"{_fixture_first_path_line(row['title'], first_path, index=index)}\n\n"
                f"{_fixture_proof_line(row['title'], proof_boundary, index=index, total=len(created))}\n"
            )
            for index, row in enumerate(created, start=1)
        },
        "backlog_index_text": "\n".join(str(row["title"]) for row in created),
        "validation_gate": {"status": "passed"},
    }


def _fixture_first_path_line(title: object, first_path: str, *, index: int) -> str:
    if index == 1:
        return f"Accepted first path: {first_path}"
    return f"{title} supports the accepted first path through its scoped state, handoff, or evidence responsibility."


def _fixture_proof_line(title: object, proof_boundary: str, *, index: int, total: int) -> str:
    if index == total:
        return f"Release proof for {title}: {proof_boundary}"
    return f"{title} contributes evidence toward the accepted proof boundary without restating every release condition."


def _prewrite_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "component_id": str(row.get("component_id", "")),
            "label": str(row.get("label", "")),
            "what_it_is": "Component preview keeps local state, blocked behavior, recovery evidence, release proof, and review context together.",
            "implementation_handoff": {
                "workstream_id": "B-001",
                "workstream_title": "Prove the accepted first path",
                "implementation_prompt": "Implement the accepted first path from the compiled transaction package.",
            },
            "authoring_input": {
                "component_id": str(row.get("component_id", "")),
                "label": str(row.get("label", "")),
                "path": str(row.get("intended_path", "")),
                "kind": str(row.get("kind", "service") or "service"),
                "category": "application",
                "qualification": str(row.get("qualification", "candidate") or "candidate"),
                "owner": "repo",
                "status": str(row.get("status", "planned") or "planned"),
                "product_layer": "application",
                "sources": ("user_intent",),
                "workstreams": ("B-001",),
                "diagrams": (),
                "responsibility": str(row.get("responsibility", "") or row.get("boundary", "")),
                "boundary": str(row.get("boundary", "")),
                "dependencies": (),
                "interfaces": (),
                "validation": tuple(row.get("validation", ()) if isinstance(row.get("validation"), list) else ()),
                "risks": (),
                "implementation_handoff": {
                    "workstream_id": "B-001",
                    "workstream_title": "Prove the accepted first path",
                    "implementation_prompt": "Implement the accepted first path from the compiled transaction package.",
                },
                "component_contract": row.get("component_contract") if isinstance(row.get("component_contract"), dict) else {},
            },
            "validation_gate": {"status": "passed"},
        }
        for row in proposal.get("components", [])
        if isinstance(row, dict) and str(row.get("release_scope", "")).casefold() not in {"deferred", "out_of_scope", "external"}
    )


def _staged_component_preview(proposal: dict[str, object]) -> tuple[dict[str, object], ...]:
    rows: list[dict[str, object]] = []
    for index, row in enumerate(_prewrite_component_preview(proposal), start=1):
        payload = dict(row)
        payload["registry_path"] = (
            f"/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/component_registry.v1.json"
        )
        payload["spec_path"] = (
            f"/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/components/c-{index}/CURRENT_SPEC.md"
        )
        rows.append(payload)
    return tuple(rows)


def _accepted_preview(proposal: dict[str, object]) -> dict[str, object]:
    return {
        "schema_version": "odylith.accepted_project.v1",
        "origin": "greenfield",
        "proposal": {"semantic_model": proposal["semantic_model"]},
        "validation_gate": {"status": "passed"},
        "created": {
            "workstreams": _prewrite_backlog_result(proposal)["created"],
            "components": list(_prewrite_component_preview(proposal)),
            "diagrams": [f"D-{index:03d}" for index, _row in enumerate(proposal["diagrams"], start=1)],
            "release_selector": "0.0.1",
        },
    }


def _compass_preview(
    proposal: dict[str, object],
    *,
    component_preview: tuple[dict[str, object], ...] | None = None,
) -> dict[str, object]:
    components = component_preview or _prewrite_component_preview(proposal)
    return {
        "kind": "decision",
        "summary": "Accepted greenfield proposal",
        "evidence_tier": "user_intent",
        "work_category": "governance",
        "workstreams": [str(row["idea_id"]) for row in _prewrite_backlog_result(proposal)["created"]],
        "components": [str(row["component_id"]) for row in components],
        "artifacts": [str(row["spec_path"]) for row in components if str(row.get("spec_path", "")).strip()],
    }


def _tribunal_preview() -> dict[str, object]:
    return {
        "status": "passed",
        "version": "greenfield-validation-gate-v1",
        "summary": "Accepted product direction is coherent enough to create project records.",
        "dimensions": {
            "semantic_model": "complete",
            "first_path": "covered",
            "component_contracts": "covered",
            "diagram_graph": "covered",
        },
        "issues": [],
    }


def _next_steps_preview() -> dict[str, object]:
    return {
        "project_workstream_id": "B-001",
        "start_workstream_id": "B-001",
        "start_workstream_title": "Municipal Permit Review First Slice",
        "release_selector": "0.0.1",
        "implementation_prompt": (
            "Start B-001 Municipal Permit Review First Slice from the accepted first-path workstream. Implement the "
            "smallest source-backed path where a coordinator imports one permit application, a zoning reviewer records "
            "a zoning check, the applicant submits one revision, and a supervisor reviews the traceable decision package "
            "with proof gates, blocked-input behavior, and replayable validation evidence."
        ),
        "operator_sequence": [
            "Review the accepted project brief.",
            "Open the first implementation workstream.",
            "Author the first technical plan from its proof obligations.",
        ],
        "coding_readiness_gates": [
            "Accepted first-path contract is understood.",
            "Release boundary is acknowledged.",
            "Verification commands are known.",
            "Excluded scope is explicitly preserved.",
        ],
        "verification_commands": [
            "./.odylith/bin/odylith context --repo-root . B-001",
            "./.odylith/bin/odylith validate plan-workstream-binding --repo-root .",
        ],
    }


def _project_dashboard_preview(
    proposal: dict[str, object],
    *,
    accepted_project_preview: dict[str, object],
    source_launch_context: dict[str, object],
) -> dict[str, object]:
    dashboard_proposal = dict(proposal)
    dashboard_proposal["_accepted_project"] = accepted_project_preview
    dashboard_proposal["_source_launch"] = source_launch_context
    return build_greenfield_payload(proposal=dashboard_proposal, repo_root=ROOT)


def _package_for_quality_report(
    proposal: dict[str, object],
    **overrides: object,
) -> GreenfieldCompletionPackage:
    next_steps_preview = (
        overrides.get("next_steps_preview")
        if isinstance(overrides.get("next_steps_preview"), dict)
        else _next_steps_preview()
    )
    accepted_project_preview = (
        overrides.get("accepted_project_preview")
        if isinstance(overrides.get("accepted_project_preview"), dict)
        else _accepted_preview(proposal)
    )
    values: dict[str, object] = {
        "release_selector": "0.0.1",
        "rendered_atlas_sources": greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
        "atlas_review_date": "2026-07-07",
        "atlas_diagram_ids": tuple(
            f"D-{index:03d}"
            for index, row in enumerate(proposal.get("diagrams", []), start=1)
            if isinstance(row, dict)
        ),
        "component_registry_preview": _prewrite_component_preview(proposal),
        "project_brief_preview": proposal["project_brief"],
        "tribunal_preview": _tribunal_preview(),
        "accepted_project_preview": accepted_project_preview,
        "project_dashboard_preview": _project_dashboard_preview(
            proposal,
            accepted_project_preview=accepted_project_preview,
            source_launch_context=next_steps_preview,
        ),
        "compass_memory_preview": _compass_preview(proposal),
        "next_steps_preview": next_steps_preview,
        "backlog_result": _prewrite_backlog_result(proposal),
        "surface_refresh_preview": surface_refresh_preview_fixture(),
        "prewrite_safety_preview": {
            "status": "passed",
            "checks": {
                "validation_gate_passed": True,
                "release_target_dry_run": True,
                "release_assignment_dry_run": True,
            },
        },
        "release_target_result": {"dry_run": True, "release": {"release_id": "release-test"}},
        "release_assignment_result": {"dry_run": True, "workstream_ids": ["B-001"]},
        "release_workstream_ids": ("B-001",),
    }
    values["atlas_catalog_rows"] = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=ROOT,
        rows=tuple(row for row in proposal.get("diagrams", []) if isinstance(row, dict)),
        diagram_ids=values["atlas_diagram_ids"],  # type: ignore[arg-type]
        traceability_plan=SimpleNamespace(diagram_links=()),
        review_date=str(values["atlas_review_date"]),
    )
    values.update(overrides)
    if "project_dashboard_preview" not in overrides:
        values["project_dashboard_preview"] = _project_dashboard_preview(
            proposal,
            accepted_project_preview=values["accepted_project_preview"],  # type: ignore[arg-type]
            source_launch_context=values["next_steps_preview"],  # type: ignore[arg-type]
        )
    return GreenfieldCompletionPackage(proposal=proposal, **values)


def test_confirmed_completion_varies_success_proof_metrics_before_package_gate(tmp_path: Path) -> None:
    proposal = complete_confirmed_proposal(_proposal(tmp_path), release_selector="0.0.1")
    rendered = "\n".join(
        "\n".join(str(item) for item in row.get("success_metrics", []))
        for row in proposal.get("backlog", [])
        if isinstance(row, dict)
    )
    report = build_greenfield_package_report(_package_for_quality_report(proposal))

    assert "The proof record explains blocked, missing, or invalid input before a result is presented" not in rendered
    assert "State responsibility, actor, source, status, result, and recovery context stay attached" not in rendered
    assert "repeats a noncanonical sentence" not in "\n".join(report.issues)


def test_greenfield_package_report_rejects_missing_surface_refresh_proof(tmp_path: Path) -> None:
    proposal = complete_confirmed_proposal(_proposal(tmp_path), release_selector="0.0.1")
    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, surface_refresh_preview=None)
    )

    assert report.status == "failed"
    assert "missing compiled pre-confirm surface refresh proof" in report.issues


def test_greenfield_prewrite_package_passes_calorie_burn_quality_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)
    prompt = "Draft a greenfield proposal for a calorie burn optimizer"
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(
            CALORIE_BURN_CONFIRMED_INTENT_TEXT,
            prompt=prompt,
            repo_root=tmp_path,
            write_files=True,
        ),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    encoded = json.dumps(proposal)
    report = build_greenfield_package_report(prewrite.package)
    recommendation_component = next(
        component
        for component in proposal["components"]
        if "Recommendation Engine" in str(component.get("label", ""))
    )
    idea_text = "\n".join(str(value) for value in prewrite.backlog_result.get("idea_files", {}).values())
    component_text = "\n".join(str(value) for value in (prewrite.package.rendered_component_specs or {}).values())
    activity_component_text = next(
        str(value)
        for key, value in (prewrite.package.rendered_component_specs or {}).items()
        if "Activity Log" in str(key)
    )
    rendered_text = "\n".join(
        [
            idea_text,
            component_text,
            "\n".join(str(value) for value in (prewrite.package.rendered_atlas_sources or {}).values()),
        ]
    )

    assert report.passed, "\n".join(report.issues)
    assert "can sets" not in encoded
    assert "central object is" not in encoded
    assert "The Individual Optimizing Their" not in encoded
    assert "Activity Log and Profile. External" not in encoded
    assert "Activity Log and Profile Store" in encoded
    assert "burn against target plus" not in encoded
    assert "estimated total burn against target" not in encoded
    assert "activity trustworthy energy-out picture" not in rendered_text
    assert "basic body stat on a successful path" not in rendered_text
    assert "reference calorie-cost dataset activity" not in activity_component_text
    assert "one concrete." not in rendered_text
    assert "seted" not in rendered_text
    assert "concrete recommendation next" not in rendered_text
    assert "for the first\"]" not in rendered_text
    assert "body stats plus logged activity, energy-out number, and burn estimation are calculated" not in component_text
    assert "If something is missing" not in rendered_text
    assert ", Whether wearable" not in rendered_text
    assert "Live wearable sync scope<br/>remains deferred" in rendered_text
    assert '?".' not in rendered_text
    assert "while Activity Log and Profile Store ownership" not in component_text
    assert " outside boundary" not in component_text
    assert "ownership over Activity Log and Profile Store local state" not in component_text
    assert (
        "Activity Log and Profile Store can consume next-day adjustment recommendation while Recommendation Engine keeps ownership of its state"
        in component_text
    )
    assert "## Proposed Solution\nBurn Estimation Engine should support" not in idea_text
    assert "Start with the smallest implementation slice" not in idea_text
    assert "\n- for " not in rendered_text
    assert ".. Impact" not in rendered_text
    assert "estimated total burn compared with the target and one concrete recommendation" in encoded
    assert "Proposes the next adjustment" in str(recommendation_component.get("responsibility", ""))
    assert "Maintains proposes" not in str(recommendation_component.get("responsibility", ""))
    assert "one concrete" not in str(recommendation_component.get("responsibility", "")).casefold()
    assert "It should explain how the energy-out number is calculated" in component_text
    assert "Successful path evidence for Burn Estimation Engine: energy-out number" in component_text
    assert "Successful path evidence for Recommendation Engine: next-day adjustment recommendation" in component_text
    assert "Successful path evidence for Activity Log and Profile Store" in activity_component_text
    assert "No explicit dependency recorded yet" not in idea_text
    assert "Run focused validation for the touched paths once implementation begins" not in idea_text
    assert "Queue now, then bind a technical plan when the implementation wave starts" not in idea_text


def test_greenfield_prewrite_package_passes_sun_burn_quality_regression(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)
    prompt = "Draft a greenfield proposal for a sunburn relief and skin-recovery coach"
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_intent_with_authority(
            SUN_BURN_CONFIRMED_INTENT_TEXT,
            prompt=prompt,
            repo_root=tmp_path,
            write_files=True,
        ),
    )
    tribunal = run_greenfield_tribunal(proposal, release_selector="0.0.1")
    prewrite = greenfield_apply_prewrite.build_prewrite_completion_package(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_args=greenfield_proposals._backlog_apply_args(proposal, release_selector="0.0.1"),
        validation_gate=tribunal.to_dict(),
        release_assignment_note=greenfield_apply_write.release_assignment_note(selector="0.0.1"),
    )

    report = build_greenfield_package_report(prewrite.package)
    encoded = json.dumps(proposal)
    artifact_encoded = json.dumps(
        {
            key: value
            for key, value in proposal.items()
            if key not in {"intent", "semantic_model"}
        }
    )
    idea_text = "\n".join(str(value) for value in prewrite.backlog_result.get("idea_files", {}).values())
    component_text = "\n".join(str(value) for value in (prewrite.package.rendered_component_specs or {}).values())
    atlas_text = "\n".join(str(value) for value in (prewrite.package.rendered_atlas_sources or {}).values())
    preview_text = "\n".join(
        [
            json.dumps(prewrite.package.project_brief_preview),
            json.dumps(prewrite.package.next_steps_preview),
        ]
    )
    narrative_text = "\n".join([idea_text, component_text, preview_text])
    rendered_text = "\n".join(
        [
            narrative_text,
            atlas_text,
        ]
    )

    assert report.passed, "\n".join(report.issues)
    assert "Recovery Episode" in encoded
    assert "Episode History, Reminder, and Notification" in rendered_text
    assert "safe, evidence-grounded recovery plan" in rendered_text
    assert "first-24-hours action plan" in rendered_text
    assert "warning when safety threshold" in rendered_text
    assert "is crossed" in rendered_text
    for forbidden in (
        "Unit of Truth Is A Recovery Episode",
        "Reminder/notification",
        "Dermatology or -care",
        "checking-ins",
        "against;",
        "returns a clear.",
        "produces a in the same release story",
        "the first thing the product must prove is that",
        "The accepted first path proves",
        "A close second is",
        "contributes information",
        "actor actor",
        "action action",
        "state state",
        "proof proof",
        "validation validation",
        "decision decision",
        "release release",
        "and and",
        "episode history and reminder and and",
        "Success proof covers answering the intake questions, receiving a severity read and a first-24-hours action plan, prompting daily check-ins, and comparing new photos and symptom scores against the baseline and a first-24-hours action plan",
        "confirmation-only draft",
        "Keep Keep",
        "That relationship is what makes the outcome reviewable instead of a black-box claim",
    ):
        assert forbidden not in rendered_text
        assert forbidden not in artifact_encoded


def test_greenfield_package_gate_requires_prewrite_atlas_sources(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "rendered Atlas Mermaid sources" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_component_authoring_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_component_specs={"Detached": "# Detached\n"},
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "component authoring previews" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_accepted_project_memory_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_compass_memory_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Compass memory event preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_project_brief_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "project brief preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_tribunal_evidence_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Tribunal evidence preview" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_operator_next_steps_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "operator next-steps preview" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_operator_next_steps(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    next_steps = _next_steps_preview()
    next_steps["implementation_prompt"] = (
        "Implement the first slice by accepting actor identity, validation context, and upstream handoff "
        "and producing blocker signal, review rationale, and downstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=next_steps,
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "operator next-steps preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_repair_does_not_rewrite_mixed_action_inflection(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    next_steps = _next_steps_preview()
    next_steps["coding_readiness_gates"] = [
        "The first path is accepted: mark the location, optionally notes context and save.",
        "Release boundary is acknowledged.",
        "Verification commands are known.",
    ]
    package = _package_for_quality_report(proposal, next_steps_preview=next_steps)

    initial = build_greenfield_package_report(package)
    result = repair_greenfield_package_until_clean(package)
    rendered = json.dumps(result.package.next_steps_preview, sort_keys=True)

    assert not initial.passed
    assert any("mixed finite/base action prose" in issue for issue in initial.issues)
    assert not result.changed
    assert not result.report.passed
    assert any(
        finding.code == "generated_copy_quality"
        and finding.repairability == "plan_patch"
        and finding.projection_id == "next_steps"
        for finding in result.report.findings
    )
    assert "optionally notes context and save" in rendered


def test_greenfield_package_repair_does_not_rewrite_malformed_responsibility_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    rendered_specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=backlog_result,
    )
    first_label = next(iter(rendered_specs))
    rendered_specs[first_label] = f"{rendered_specs[first_label]}\n\n{first_label} owns maintains state."
    package = _package_for_quality_report(
        proposal,
        rendered_component_specs=rendered_specs,
        backlog_result=backlog_result,
    )

    initial = build_greenfield_package_report(package)
    result = repair_greenfield_package_until_clean(package)
    rendered = json.dumps(result.package.rendered_component_specs, sort_keys=True)

    assert not initial.passed
    assert any("malformed ownership verb pair" in issue for issue in initial.issues)
    assert not result.changed
    assert result.initial_report == initial
    assert not result.report.passed
    assert any(
        finding.code == "component_contract_quality"
        and finding.repairability == "plan_patch"
        and finding.projection_id == "registry"
        for finding in result.report.findings
    )
    assert "owns maintains" in rendered


def test_greenfield_package_gate_rejects_structural_contract_tuple_variants(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    next_steps = _next_steps_preview()
    next_steps["implementation_prompt"] = (
        "Implement the first slice by accepting user identity, routing context, and source handoff "
        "and producing error signal, reviewer rationale, and delivery handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=next_steps,
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    issues = "\n".join(report.issues)
    assert not report.passed
    assert "operator next-steps preview leaked Registry contract tuple prose" in issues
    assert "operator next-steps preview leaked produced-output tuple prose" in issues


def test_greenfield_package_gate_rejects_mechanical_radar_gate_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    backlog_result["idea_files"] = {
        path: (
            f"{text}\n\nGate: Validate that Build Visit Capture First Path satisfies its local success criteria: "
            "Visit Capture accepts actor identity, validation context, and upstream handoff.\n"
        )
        for path, text in backlog_result["idea_files"].items()
    }

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=backlog_result,
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Radar package leaked raw success-metric gate prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_registry_preview_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = [dict(row) for row in _prewrite_component_preview(proposal)]
    component_preview[0]["what_it_is"] = (
        "Broken preview accepts actor identity, validation context, and upstream handoff and "
        "produces blocker signal, review rationale, and downstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=tuple(component_preview),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Registry preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_mechanical_accepted_project_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    accepted = _accepted_preview(proposal)
    accepted["created"]["components"][0]["summary"] = (
        "Generated memory accepts actor identity, validation context, and upstream handoff."
    )

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=accepted,
            compass_memory_preview=_compass_preview(proposal),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview leaked Registry contract tuple prose" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_rendered_modal_grammar_drift(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\n\nA representative user can sets a target and use the clear result to decide what to do next.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "modal/base-form grammar drift" in "\n".join(report.issues)


def test_greenfield_package_gate_allows_title_case_possessive_pronouns(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\n\n## Let Person On The GLP-1 Medication Set Up Their Medication Current Dose and Weekly Injection Day\n"
        "\nKeep validation gates tied to this workstream before expanding adjacent source ownership: "
        "Let Person On The GLP-1 Medication Set Up Their Medication.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert report.passed, "\n".join(report.issues)


def test_greenfield_package_gate_still_rejects_prose_capitalization_drift(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\nThe product records the injection and Their next due date stays visible.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "mid-sentence capitalization drift near `Their`" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_lowercase_fragment_bullets(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += "\n- for Review Workspace, access and audit obligations stay visible.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "sentence-fragment drift" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_doubled_punctuation(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += "\nOpen question.. Impact: unclear ownership.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "doubled sentence punctuation" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_quoted_question_doubled_punctuation(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += '\nThe prompt asks "what changed?".\n'

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "doubled sentence punctuation" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_clipped_terminal_modifier(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += "\nThe visible result ends with one concrete.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "clipped modifier phrase" in "\n".join(report.issues)


def test_next_steps_preview_trims_clipped_terminal_fragments() -> None:
    assert greenfield_experience._trim_preview_terminal_fragment(  # noqa: SLF001
        "Assemble denial reasons, reviewer objections, and final"
    ) == "Assemble denial reasons, reviewer objections"
    assert greenfield_experience._trim_preview_terminal_fragment(  # noqa: SLF001
        "Review source context and accepted participants without"
    ) == "Review source context and accepted participants"
    assert greenfield_experience._trim_preview_terminal_fragment(  # noqa: SLF001
        "The appeal status is final"
    ) == "The appeal status is final"
    assert greenfield_experience._first_slice_text(  # noqa: SLF001
        {"recommended_first_slice": "Do not expand beyond recording first entry and logging again until"}
    ) == "Do not expand beyond recording first entry and logging again"


def test_greenfield_package_inspection_preserves_operator_next_step_dangling_tail(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    next_steps = _next_steps_preview()
    next_steps["implementation_prompt"] = (
        "After project-first scope is accepted, start B-001 Municipal Permit Review First Slice: import one permit "
        "application, record a zoning check, capture one applicant revision, and prove the supervisor decision package "
        "with blocked-input and replay evidence until."
    )
    package = _package_for_quality_report(proposal, next_steps_preview=next_steps)

    initial = build_greenfield_package_report(package)
    inspected = repair_greenfield_package_until_clean(package)

    assert not initial.passed
    assert inspected.initial_report == initial
    assert not inspected.changed
    assert not inspected.report.passed
    rendered = json.dumps(inspected.package.next_steps_preview, sort_keys=True)
    assert "replay evidence until" in rendered
    assert "clipped or dangling phrase ending" in "\n".join(inspected.report.issues)


def test_greenfield_package_inspection_preserves_radar_clause_dangling_tails(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\n## Generated Clause Check\n"
        "- The path should not leave a clause dangling from, or another clause dangling into.\n"
    )
    package = _package_for_quality_report(proposal, backlog_result=backlog_result)

    initial = build_greenfield_package_report(package)
    inspected = repair_greenfield_package_until_clean(package)

    assert not initial.passed
    assert inspected.initial_report == initial
    assert not inspected.changed
    assert not inspected.report.passed
    rendered = "\n".join(str(value) for value in inspected.package.backlog_result["idea_files"].values())
    assert "dangling from," in rendered
    assert "dangling into." in rendered
    assert "clipped or dangling phrase ending" in "\n".join(inspected.report.issues)


def test_greenfield_package_gate_rejects_clipped_terminal_article(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += "\nThe ranking basis says this path produces a.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "clipped article phrase" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_invalid_lifecycle_inflection(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    rendered_specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=backlog_result,
    )
    first_key = next(iter(rendered_specs))
    rendered_specs[first_key] += "\n\nThe important lifecycle is requested, seted, flaging, and validated.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result, rendered_component_specs=rendered_specs)
    )

    assert not report.passed
    issues = "\n".join(report.issues)
    assert "invalid verb inflection" in issues
    assert "`seted`" in issues
    assert "`flaging`" in issues


def test_greenfield_package_gate_rejects_vague_missing_input_copy(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\nIf something is missing, it should explain the problem before it presents a result.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "vague missing-input copy" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_vague_missing_input_variants(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += "\nIf anything is absent, show a blocker before presenting a result.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "vague missing-input copy" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_comma_spliced_capitalized_clause(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\nKeep this slice inside the accepted scope: first release only, Whether integration is deferred.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "comma-spliced capitalized clause drift" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_open_scope_question_as_boundary(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    first_path = next(iter(backlog_result["idea_files"]))
    backlog_result["idea_files"][first_path] += (
        "\nOut of scope: core workflow only; whether integration is in scope until the first path holds.\n"
    )

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, backlog_result=backlog_result)
    )

    assert not report.passed
    assert "open scope question as a boundary clause" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_clipped_boundary_phrase(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    rendered_specs = greenfield_apply_components.render_prewrite_component_specs(
        root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
        backlog_result=_prewrite_backlog_result(proposal),
    )
    first_key = next(iter(rendered_specs))
    rendered_specs[first_key] += "\n\nSibling state remains outside boundary.\n"

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, rendered_component_specs=rendered_specs)
    )

    assert not report.passed
    assert "clipped boundary phrase" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_disconnected_mermaid_nodes(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    atlas_sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal)
    first_path = next(iter(atlas_sources))
    atlas_sources[first_path] = 'flowchart LR\n  A["Start"] --> B["End"]\n  C["Orphan"]\n'

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, rendered_atlas_sources=atlas_sources)
    )

    assert not report.passed
    assert "disconnected Mermaid node `C`" in "\n".join(report.issues)


def test_greenfield_package_gate_requires_compiled_atlas_review_date(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, atlas_review_date="")
    )

    assert not report.passed
    assert "prewrite Atlas package must include a compiled review date" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_repeated_noncanonical_rendered_sentences(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    repeated = (
        "The generated artifact repeats this planning statement across components without adding owned state, "
        "boundary detail, proof evidence, or a clear reader-specific decision."
    )
    rendered_specs = {
        f"Component {index}": f"# Component {index}\n\n{repeated}\n"
        for index in range(1, 4)
    }

    report = build_greenfield_package_report(
        _package_for_quality_report(proposal, rendered_component_specs=rendered_specs)
    )

    assert not report.passed
    assert "repeats noncanonical prose" in "\n".join(report.issues)


def test_greenfield_package_repetition_allows_component_labels_as_identifiers(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    label = "Kitchen Robot Controller for Home Cooks Intake Register Service"
    proposal["components"] = [{"component_id": "intake-register", "label": label}]
    rendered_specs = {
        f"Component {index}": f"# Component {index}\n\n{label}\n"
        for index in range(1, 4)
    }

    issues = greenfield_rendered_package_quality_issues(
        _package_for_quality_report(proposal, rendered_component_specs=rendered_specs)
    )

    assert "repeats a noncanonical sentence" not in "\n".join(issues)


def test_greenfield_package_repetition_rejects_repeated_proof_boundary_source_text(tmp_path: Path) -> None:
    repeated = (
        "Version 0.0.1 is proven when a record moves across its full lifecycle, appears as a scheduled item, "
        "shows a live status with an event timeline, and settles into a finished result that remains browsable."
    )
    package = SimpleNamespace(
        proposal={"intent": {"title": "Lifecycle Review", "proof_boundary": repeated}},
        backlog_result={
            "idea_files": {
                str(tmp_path / f"idea-{index}.md"): f"# Idea {index}\n\n{repeated}\n"
                for index in range(1, 4)
            }
        },
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_preview={},
        next_steps_preview={},
    )

    issues = greenfield_rendered_package_quality_issues(package)

    assert "repeats noncanonical prose" in "\n".join(issues)


def test_project_brief_record_quality_preserves_markdown_boundaries() -> None:
    project_brief = """# Film Festival Accessibility Screening Planner Project Brief

## Project Design Board
- First path: Programmers can publish accessible screening readiness
  - Why: A narrow first path keeps the first release testable and prevents broad platform drift.
"""
    package = SimpleNamespace(
        proposal={"intent": {"title": "Film Festival Accessibility Screening Planner"}},
        backlog_result={},
        rendered_component_specs={},
        rendered_atlas_sources={},
        project_brief_record_text=project_brief,
        project_brief_preview={},
        next_steps_preview={},
    )

    project_artifacts = [
        artifact
        for artifact in collect_rendered_package_artifacts(package)
        if artifact.surface == "Project brief"
    ]
    assert project_artifacts and "\n  - Why:" in project_artifacts[0].text
    assert not any(
        "coordinated modal grammar drift" in issue
        for issue in greenfield_rendered_package_quality_issues(package)
    )


def test_greenfield_package_gate_rejects_staged_paths_in_accepted_project_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = _staged_component_preview(proposal)
    accepted = _accepted_preview(proposal)
    accepted["created"]["components"] = list(component_preview)

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=component_preview,
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=accepted,
            compass_memory_preview=_compass_preview(proposal, component_preview=component_preview),
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "accepted-project memory preview contains staged prewrite temp path" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_staged_paths_in_compass_preview(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    component_preview = _prewrite_component_preview(proposal)
    compass = _compass_preview(proposal)
    compass["artifacts"] = [
        "/tmp/odylith-greenfield-prewrite-test/repo/odylith/registry/source/components/c-1/CURRENT_SPEC.md"
    ]

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=component_preview,
            project_brief_preview=proposal["project_brief"],
            tribunal_preview=_tribunal_preview(),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=compass,
            next_steps_preview=_next_steps_preview(),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "Compass memory event preview contains staged prewrite temp path" in "\n".join(report.issues)


def test_greenfield_prewrite_remaps_component_preview_paths_to_target_repo(tmp_path: Path) -> None:
    staged_root = tmp_path / "stage" / "repo"
    target_root = tmp_path / "target"
    component_items = (
        {
            "component_id": "c-001",
            "registry_path": staged_root / "odylith/registry/source/component_registry.v1.json",
            "spec_path": staged_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md",
        },
    )

    remapped = greenfield_apply_prewrite.remap_prewrite_component_items(
        component_items,
        source_root=staged_root,
        target_root=target_root,
    )

    assert remapped[0]["registry_path"] == "odylith/registry/source/component_registry.v1.json"
    assert remapped[0]["spec_path"] == "odylith/registry/source/components/c-001/CURRENT_SPEC.md"


def test_greenfield_accepted_project_preview_relativizes_target_paths_against_target_root(tmp_path: Path) -> None:
    staged_root = tmp_path / "stage" / "repo"
    target_root = tmp_path / "target"
    accepted = greenfield_apply_prewrite.preview_accepted_project_memory(
        root=staged_root,
        target_root=target_root,
        proposal={"intent": {"title": "Case Review Workspace"}, "diagrams": []},
        backlog_result={
            "created": [
                {
                    "idea_id": "B-001",
                    "idea_path": target_root / "odylith/radar/source/ideas/2026-08/case-review.md",
                }
            ]
        },
        component_items=(
            {
                "component_id": "case-review",
                "spec_path": target_root
                / "odylith/registry/source/components/case-review/CURRENT_SPEC.md",
            },
        ),
        release_selector="0.0.1",
        release_target_result=None,
        release_assignment_result=None,
        validation_gate={"status": "passed"},
    )

    assert accepted["created"]["workstreams"][0]["idea_path"] == (
        "odylith/radar/source/ideas/2026-08/case-review.md"
    )
    assert accepted["created"]["components"][0]["spec_path"] == (
        "odylith/registry/source/components/case-review/CURRENT_SPEC.md"
    )
    assert prewrite_path_leak_issues("accepted-project memory preview", accepted) == []


def test_greenfield_component_memory_path_fidelity_treats_alias_roots_as_same_path(tmp_path: Path) -> None:
    real_root = tmp_path / "real"
    alias_root = tmp_path / "alias"
    real_root.mkdir()
    alias_root.symlink_to(real_root, target_is_directory=True)
    component_id = "c-001"
    expected = (
        {
            "component_id": component_id,
            "registry_path": str(real_root / "odylith/registry/source/component_registry.v1.json"),
            "spec_path": str(real_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
        },
    )
    actual = (
        {
            "component_id": component_id,
            "registry_path": str(alias_root / "odylith/registry/source/component_registry.v1.json"),
            "spec_path": str(alias_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
        },
    )

    assert _component_preview_path_fidelity_issues(
        owner="accepted-project memory preview",
        expected=expected,
        actual=actual,
    ) == []

    foreign_root = tmp_path / "foreign"
    assert _component_preview_path_fidelity_issues(
        owner="accepted-project memory preview",
        expected=expected,
        actual=(
            {
                "component_id": component_id,
                "registry_path": str(foreign_root / "odylith/registry/source/component_registry.v1.json"),
                "spec_path": str(foreign_root / "odylith/registry/source/components/c-001/CURRENT_SPEC.md"),
            },
        ),
    ) == [
        "accepted-project memory preview component `c-001` registry_path drifted from Registry prewrite output",
        "accepted-project memory preview component `c-001` spec_path drifted from Registry prewrite output",
    ]


def test_greenfield_accepted_memory_preserves_structural_path_underscores(tmp_path: Path) -> None:
    proposal = {
        "intent": {
            "title": "Genomic Variant Triage Board",
            "reasoning_mode": "odylith_confirmed_governed_proposal",
        },
        "semantic_model": {},
    }
    component = {
        "component_id": "variant-case-ledger",
        "label": "Variant Case Ledger",
        "registry_path": str(tmp_path / "odylith/registry/source/component_registry.v1.json"),
        "spec_path": str(tmp_path / "odylith/registry/source/components/variant-case-ledger/CURRENT_SPEC.md"),
    }

    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=(),
        component_items=(component,),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-genomic-variant-triage-0-0-1",
        validation_gate={"status": "passed"},
        source_launch_context=None,
        accepted_at="prewrite",
        repo_root=tmp_path,
    )
    event = proposal_memory.build_greenfield_acceptance_event_preview(
        proposal=proposal,
        backlog_items=(),
        component_items=(component,),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-genomic-variant-triage-0-0-1",
        repo_root=tmp_path,
    )

    created_component = accepted["created"]["components"][0]
    assert created_component["registry_path"] == "odylith/registry/source/component_registry.v1.json"
    assert created_component["spec_path"] == "odylith/registry/source/components/variant-case-ledger/CURRENT_SPEC.md"
    assert created_component["spec_path"] in event["artifacts"]


def test_greenfield_prewrite_hygiene_rejects_all_ephemeral_absolute_paths() -> None:
    issues = prewrite_path_leak_issues(
        "accepted-project memory preview",
        {"source": "/private/tmp/odylith-quality-test/odylith/runtime/source/accepted-project.v1.json"},
    )

    assert issues == [
        "accepted-project memory preview contains staged prewrite temp path(s) instead of durable target paths"
    ]


def test_greenfield_accepted_memory_rebases_staged_workstream_paths(tmp_path: Path) -> None:
    proposal = {"intent": {"title": "Release Notes Workspace", "reasoning_mode": "odylith_confirmed_governed_proposal"}}
    accepted = proposal_memory.build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=(
            {
                "idea_id": "B-001",
                "idea_path": str(tmp_path / "odylith/radar/source/ideas/2026-07/release-notes.md"),
            },
        ),
        component_items=(),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="release-release-notes-0-0-1",
        validation_gate={"status": "passed"},
        accepted_at="prewrite",
        repo_root=tmp_path,
    )

    assert accepted["created"]["workstreams"][0]["idea_path"] == "odylith/radar/source/ideas/2026-07/release-notes.md"


def test_greenfield_package_gate_rejects_workstream_preview_without_semantic_proof(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    backlog_result = _prewrite_backlog_result(proposal)
    backlog_result["idea_files"] = {path: "# Detached\n\nUnrelated placeholder text.\n" for path in backlog_result["idea_files"]}

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal),
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=backlog_result,
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "prewrite Radar package missing semantic coverage" in "\n".join(report.issues)


def test_greenfield_package_gate_rejects_atlas_preview_without_proof_checkpoint(tmp_path: Path) -> None:
    proposal = _proposal(tmp_path)
    atlas_sources = {
        path: "flowchart LR\n  A[Detached placeholder]\n"
        for path in greenfield_apply_diagrams.render_prewrite_atlas_sources(proposal)
    }

    report = build_greenfield_package_report(
        GreenfieldCompletionPackage(
            proposal=proposal,
            release_selector="0.0.1",
            rendered_atlas_sources=atlas_sources,
            component_registry_preview=_prewrite_component_preview(proposal),
            accepted_project_preview=_accepted_preview(proposal),
            compass_memory_preview=_compass_preview(proposal),
            backlog_result=_prewrite_backlog_result(proposal),
            release_target_result={"dry_run": True, "release": {"release_id": "release-test"}},
            release_assignment_result={"dry_run": True, "workstream_ids": ["B-001"]},
            release_workstream_ids=("B-001",),
        )
    )

    assert not report.passed
    assert "proof checkpoint" in "\n".join(report.issues)


def test_greenfield_apply_blocks_bad_rendered_specs_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md")) == []
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd")) == []


def test_greenfield_apply_rerenders_prewrite_package_after_repairable_package_failure(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    original = greenfield_apply_components.render_prewrite_component_specs
    calls = 0

    def flaky_render(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"Broken Component": "Broken Component owns maintains state."}
        return original(**kwargs)

    monkeypatch.setattr(greenfield_apply_components, "render_prewrite_component_specs", flaky_render)

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert calls >= 2
    assert result["validation_gate"]["status"] == "passed"
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))


def test_greenfield_apply_commits_prewrite_atlas_source_not_regenerated_drift(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    original_allocated_diagram_ids = greenfield_apply_diagrams.allocated_diagram_ids
    target_allocation_calls = 0

    def fail_after_prewrite_allocation(*args, **kwargs):
        nonlocal target_allocation_calls
        call_root = Path(args[0]).resolve() if args else Path()
        if call_root == tmp_path.resolve():
            target_allocation_calls += 1
            raise AssertionError("post-confirm write must consume compiled diagram ids")
        return original_allocated_diagram_ids(*args, **kwargs)

    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "validated_mermaid_source",
        lambda _row: 'flowchart LR\n  external1["Optional"]\n',
    )
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "allocated_diagram_ids",
        fail_after_prewrite_allocation,
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    atlas_text = "\n".join(path.read_text(encoding="utf-8") for path in (tmp_path / "odylith/atlas/source").glob("*.mmd"))
    assert result["commit_manifest"]["status"] == "passed"
    assert target_allocation_calls == 0
    assert '["Optional"]' not in atlas_text


def test_greenfield_commit_does_not_rematerialize_component_specs_after_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    materialize_calls = 0

    def fail_materialization(**_kwargs):
        nonlocal materialize_calls
        materialize_calls += 1
        raise AssertionError("post-confirm commit must consume sealed component specs")

    monkeypatch.setattr(
        greenfield_component_commit,
        "materialize_compiled_component_from_preview",
        fail_materialization,
    )

    result = greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    specs = list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert result["commit_manifest"]["status"] == "passed"
    assert materialize_calls == 0
    assert specs
    assert all("owns maintains state" not in path.read_text(encoding="utf-8") for path in specs)


def test_greenfield_commit_does_not_regenerate_project_brief_after_confirmation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)
    writer_calls = 0

    def fail_project_brief_writer(**_kwargs):
        nonlocal writer_calls
        writer_calls += 1
        raise AssertionError("post-confirm commit must consume the sealed project brief")

    monkeypatch.setattr(
        proposal_memory,
        "_write_compiled_project_brief_source",
        fail_project_brief_writer,
    )

    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    project_brief_path = tmp_path / "odylith/runtime/source/project-brief.v1.md"
    assert writer_calls == 0
    assert project_brief_path.read_text(encoding="utf-8") == transaction.prewrite_package.project_brief_record_text


def test_greenfield_prewrite_failure_does_not_commit_governed_records(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _force_bad_rendered_specs(monkeypatch)

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_blocks_bad_accepted_project_preview_before_governed_writes(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    monkeypatch.setattr(
        greenfield_apply_prewrite,
        "preview_accepted_project_memory",
        lambda **_kwargs: {"schema_version": "broken", "validation_gate": {"status": "failed"}},
    )

    with pytest.raises(ValueError, match="could not prepare a creation-ready package"):
        commit_precompiled_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    assert not list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert not list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_commit_does_not_rebuild_release_target_after_confirmation(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)
    original = greenfield_apply_prewrite.release_planning_authoring.ensure_release_selector
    preconfirm_calls: list[bool] = []

    def capture_release_selector(**kwargs):
        preconfirm_calls.append(bool(kwargs.get("dry_run")))
        return original(**kwargs)

    monkeypatch.setattr(greenfield_apply_prewrite.release_planning_authoring, "ensure_release_selector", capture_release_selector)
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
    )
    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def fail_release_rebuild(**_kwargs):
        raise AssertionError("post-confirm commit must consume the sealed release target")

    monkeypatch.setattr(
        greenfield_apply_prewrite.release_planning_authoring,
        "ensure_release_selector",
        fail_release_rebuild,
    )
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path,
        transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash,
        confirm=True,
    )

    assert preconfirm_calls


def test_greenfield_apply_bootstraps_target_repo_only_after_package_gate(tmp_path: Path, monkeypatch) -> None:
    proposal = _proposal(tmp_path)
    _disable_refreshes(monkeypatch)

    result = commit_precompiled_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert result["validation_gate"]["status"] == "passed"
    assert (tmp_path / "odylith/radar/source/INDEX.md").is_file()
    project_brief_path = tmp_path / "odylith/runtime/source/project-brief.v1.md"
    assert project_brief_path.is_file()
    assert result["memory"]["project_brief"] == str(project_brief_path)
    project_brief_text = project_brief_path.read_text(encoding="utf-8")
    assert "## Brief" in project_brief_text
    assert "outcome:" in project_brief_text
    assert "\n## Brief\n" in project_brief_text
    assert "\n## Project Design Board\n" in project_brief_text
    assert "\n## Governance Package\n" in project_brief_text
    assert len(project_brief_text.splitlines()) >= 20
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))
    assert list((tmp_path / "odylith/registry/source/components").glob("*/CURRENT_SPEC.md"))
    assert list((tmp_path / "odylith/atlas/source").glob("*.mmd"))
