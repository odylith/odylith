from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence import greenfield_surface_refresh_proof
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    combined_prompt_evidence_source,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    StructuredAuthoringProvider,
    authored_response,
)
from tests.unit.runtime.greenfield_proposal_fixtures import _seed_empty_governance_repo
from tests.unit.runtime.greenfield_proposal_fixtures import surface_refresh_preview_fixture


_SLOP_PHRASES = (
    "working title",
    "owns maintains",
    "first path entry",
    "proof-token",
    "access grant or denial",
    "recorded daily log",
    "case identity",
    "workspace status",
    "checklist progress",
)

_SOURCE_DOMAIN_LEAK_TERMS = (
    "biomarker",
    "calorie",
    "checkout",
    "clinician",
    "ecommerce",
    "fare",
    "grant decision",
    "home repair",
    "longevity",
    "medication",
    "municipal permit",
    "pain",
    "plant sensor",
    "protocol outcome",
    "stomach fat",
    "symptom",
    "transport",
)


def _intent(
    *,
    title: str,
    product_story: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
    problem: str,
    customer: str,
    opportunity: str,
    product_view: str,
    success_metrics: list[str],
    evidence_requirements: list[str],
    operational_constraints: list[str],
    component_responsibilities: list[str],
    human_actors: list[str],
    external_systems: list[str],
    internal_systems: list[str],
    non_goals: list[str],
) -> dict[str, Any]:
    return {
        "title": title,
        "product_story": product_story,
        "state_object": state_object,
        "first_path": first_path,
        "proof_boundary": proof_boundary,
        "problem": problem,
        "customer": customer,
        "opportunity": opportunity,
        "product_view": product_view,
        "success_metrics": success_metrics,
        "evidence_requirements": evidence_requirements,
        "operational_constraints": operational_constraints,
        "component_responsibilities": component_responsibilities,
        "human_actors": human_actors,
        "external_systems": external_systems,
        "internal_systems": internal_systems,
        "assumptions": [],
        "ambiguities": [],
        "non_goals": non_goals,
    }


_CASES = (
    pytest.param(
        "protocol-outcome",
        _intent(
            title="Protocol Outcome Notebook",
            product_story="Self-directed researchers need one reviewable protocol and outcome record.",
            state_object="protocol outcome record",
            first_path=(
                "Self-directed researcher creates a protocol, records an intervention, adds baseline and "
                "follow-up measurements, and sees a reviewable outcome review."
            ),
            proof_boundary=(
                "Replay one protocol, intervention, baseline measurement, follow-up measurement, and "
                "outcome review with source notes and visible blockers."
            ),
            problem="Protocol evidence is fragmented and hard to review without implying scientific certainty.",
            customer="Self-directed researchers and study collaborators",
            opportunity="Keep protocol setup, intervention records, measurements, and outcome review aligned.",
            product_view="Protocol Outcome Notebook preserves one evidence-linked outcome review.",
            success_metrics=["A researcher sees a replayable outcome review."],
            evidence_requirements=["Retain baseline measurement and follow-up measurement source notes."],
            operational_constraints=["Do not claim causal or medical correctness."],
            component_responsibilities=[
                "Record protocol setup and required-source blockers.",
                "Record intervention timing and amount-as-recorded.",
                "Align baseline measurement, follow-up measurement, and outcome review.",
            ],
            human_actors=["Self-directed researcher", "Study collaborator"],
            external_systems=["Measurement spreadsheet", "Source document folder"],
            internal_systems=["Protocol Builder", "Intervention Log", "Outcome Review Surface"],
            non_goals=["Scientific or medical certainty is outside the first release."],
        ),
        "Self-directed researcher",
        "creates",
        "protocol",
        "outcome review",
        ("protocol", "intervention", "baseline measurement", "follow-up measurement", "outcome review"),
        ("fare option", "symptom episode", "service address", "application packet"),
        id="protocol-outcome",
    ),
    pytest.param(
        "symptom-relief",
        _intent(
            title="Symptom Relief Journal",
            product_story="People managing recurring symptoms need a private, reviewable episode timeline.",
            state_object="symptom episode",
            first_path=(
                "Journal owner records one symptom episode, adds body area and a relief action, edits the "
                "entry, and sees the corrected timeline with a safety notice."
            ),
            proof_boundary=(
                "Replay one symptom episode with relief action, edit history, timeline evidence, and safety notice intact."
            ),
            problem="Symptom and relief history is hard to review consistently over time.",
            customer="People tracking recurring symptoms",
            opportunity="Preserve the episode, relief action, correction, and safety context together.",
            product_view="Symptom Relief Journal shows a corrected, non-clinical episode timeline.",
            success_metrics=["A journal owner sees the corrected symptom timeline."],
            evidence_requirements=["Retain body area, relief action, edit history, and safety notice."],
            operational_constraints=["Do not diagnose, prescribe, or recommend medication dosing."],
            component_responsibilities=[
                "Record symptom episode fields and edit history.",
                "Record relief action and non-advice boundaries.",
                "Show the corrected timeline and safety notice.",
            ],
            human_actors=["Journal owner", "Care partner"],
            external_systems=["User-supplied exported notes"],
            internal_systems=["Episode Capture", "Relief Action Ledger", "Timeline View"],
            non_goals=["Clinical diagnosis and dosing advice are outside the first release."],
        ),
        "Journal owner",
        "records",
        "symptom episode",
        "corrected timeline",
        ("symptom episode", "body area", "relief action", "timeline", "safety notice"),
        ("fare option", "baseline measurement", "service address", "application packet"),
        id="symptom-relief",
    ),
    pytest.param(
        "fare-choice",
        _intent(
            title="Fare Choice Assistant",
            product_story="Trip planners need a reviewable comparison of travel options for one trip.",
            state_object="trip comparison record",
            first_path=(
                "Trip planner enters origin and destination, compares each fare option, selects one option, "
                "and sees the saved rationale with a stale-quote blocker."
            ),
            proof_boundary=(
                "Replay one trip from origin and destination through ranked fare options, selected option, "
                "saved rationale, and visible stale-quote evidence."
            ),
            problem="Travel price, timing, and constraint evidence is difficult to compare and retain.",
            customer="Trip planners and budget approvers",
            opportunity="Keep the selected option and the reason for choosing it reviewable.",
            product_view="Fare Choice Assistant preserves ranked fare evidence and the final decision note.",
            success_metrics=["A trip planner sees the selected option and saved rationale."],
            evidence_requirements=["Retain origin, destination, fare option timestamps, and stale-quote state."],
            operational_constraints=["Do not make the cheapest option final when user constraints disagree."],
            component_responsibilities=[
                "Record origin, destination, and required-field blockers.",
                "Record fare option, travel time, and stale-quote evidence.",
                "Show the selected option and saved rationale.",
            ],
            human_actors=["Trip planner", "Budget approver"],
            external_systems=["Transit fare feed", "Rideshare quote export"],
            internal_systems=["Trip Intake", "Fare Option Collector", "Decision Note View"],
            non_goals=["Live provider booking is outside the first release."],
        ),
        "Trip planner",
        "enters",
        "origin and destination",
        "saved rationale",
        ("origin", "destination", "fare option", "selected option", "stale-quote"),
        ("symptom episode", "baseline measurement", "service address", "application packet"),
        id="fare-choice",
    ),
    pytest.param(
        "service-visit",
        _intent(
            title="Home Repair Visit Planner",
            product_story="Home repair teams need one reviewable path from service request to scheduled visit.",
            state_object="service visit record",
            first_path=(
                "Service coordinator verifies the service address, selects a visit window, assigns a technician, "
                "creates a quote estimate, and sees the confirmed visit with readiness blockers."
            ),
            proof_boundary=(
                "Replay one service request through verified service address, visit window, technician assignment, "
                "quote estimate, confirmation, and readiness evidence."
            ),
            problem="Service requests lose readiness and estimate context across scheduling handoffs.",
            customer="Home repair coordinators and technician leads",
            opportunity="Keep visit scheduling, quote context, and readiness blockers together.",
            product_view="Home Repair Visit Planner shows the confirmed visit and its readiness state.",
            success_metrics=["A coordinator sees the confirmed visit with readiness blockers."],
            evidence_requirements=["Retain service address, visit window, technician, quote estimate, and readiness state."],
            operational_constraints=["Quote estimates are planning context, not binding contracts."],
            component_responsibilities=[
                "Record service address and missing-detail blockers.",
                "Record visit window and technician assignment.",
                "Show quote estimate, confirmation, and readiness blockers.",
            ],
            human_actors=["Service coordinator", "Technician lead"],
            external_systems=["Calendar availability export", "Parts catalog fixture"],
            internal_systems=["Service Request Intake", "Visit Scheduler", "Readiness Review View"],
            non_goals=["Binding quotes and live scheduling integrations are outside the first release."],
        ),
        "Service coordinator",
        "verifies",
        "service address",
        "confirmed visit",
        ("service address", "visit window", "technician", "quote estimate", "readiness"),
        ("fare option", "symptom episode", "baseline measurement", "application packet"),
        id="service-visit",
    ),
    pytest.param(
        "decision-review",
        _intent(
            title="Grant Decision Review Desk",
            product_story="Funding programs need application evidence, scoring, rationale, and outcome kept together.",
            state_object="grant decision record",
            first_path=(
                "Program officer opens an application packet, checks eligibility, records a score and rationale, "
                "and sees the published outcome notice with unresolved conflicts visible."
            ),
            proof_boundary=(
                "Replay one application packet through eligibility, score, rationale, conflict state, and outcome notice."
            ),
            problem="Grant decision evidence and rationale become fragmented across reviewers.",
            customer="Program officers, applicant representatives, and appeal assessors",
            opportunity="Keep the application packet and every decision fact reviewable.",
            product_view="Grant Decision Review Desk publishes an evidence-linked outcome notice.",
            success_metrics=["A program officer sees the outcome notice with conflict state and rationale."],
            evidence_requirements=["Retain application packet, eligibility rule version, score, and rationale."],
            operational_constraints=["Do not hide unresolved conflicts or missing rationale."],
            component_responsibilities=[
                "Record application packet identity and missing-packet blockers.",
                "Record eligibility, score, rationale, and conflict state.",
                "Show the outcome notice and appeal blocker context.",
            ],
            human_actors=["Program officer", "Applicant representative", "Appeal assessor"],
            external_systems=["Application intake export", "Eligibility policy document"],
            internal_systems=["Packet Intake", "Scoring Ledger", "Outcome Publication View"],
            non_goals=["Appeal adjudication is outside the first release."],
        ),
        "Program officer",
        "opens",
        "application packet",
        "published outcome notice",
        ("application packet", "eligibility", "score", "rationale", "outcome notice"),
        ("fare option", "symptom episode", "baseline measurement", "service address"),
        id="decision-review",
    ),
)


def _source(intent: dict[str, Any]) -> str:
    return ". ".join(
        str(item)
        for value in intent.values()
        for item in (value if isinstance(value, list) else [value])
        if str(item)
    )


def _run_confirmed_transaction_create(
    *,
    repo_root: Path,
    prompt: str,
    capsys: Any,
) -> tuple[int, str]:
    compile_rc = greenfield_proposals_cli.main(
        ["propose", "--repo-root", str(repo_root), "--prompt", prompt, "--format", "json"]
    )
    compile_output = capsys.readouterr().out
    assert compile_rc == 0, compile_output
    compile_payload = json.loads(compile_output)
    transaction_hash = str(compile_payload["product_create_transaction"]["transaction_hash"])
    transaction_file = str(compile_payload["transaction_file"])
    create_rc = greenfield_proposals_cli.main(
        [
            "create",
            "--repo-root",
            str(repo_root),
            "--transaction-file",
            transaction_file,
            "--transaction-hash",
            transaction_hash,
            "--confirm",
        ]
    )
    return create_rc, capsys.readouterr().out


@pytest.mark.parametrize(
    ("name", "intent", "actor", "action", "target", "visible_result", "expected_terms", "forbidden_terms"),
    _CASES,
)
def test_greenfield_create_confirm_completes_cross_domain_projects(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: Any,
    name: str,
    intent: dict[str, Any],
    actor: str,
    action: str,
    target: str,
    visible_result: str,
    expected_terms: tuple[str, ...],
    forbidden_terms: tuple[str, ...],
) -> None:
    del name
    _seed_empty_governance_repo(tmp_path)
    source = _source(intent)
    staged_evidence = combined_prompt_evidence_source(prompt=source, edit_evidence="")
    provider = StructuredAuthoringProvider(
        authored_response(
            intent,
            evidence_text=staged_evidence,
            first_path_relations=[
                {
                    "actor_kind": "human",
                    "actor_fact_quote": actor,
                    "event_quote": intent["first_path"],
                    "action_verb_quote": action,
                    "target_quote": target,
                    "visible_result_quote": visible_result,
                }
            ],
            component_responsibility_owners=intent["internal_systems"],
        )
    )
    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        lambda **_kwargs: (provider, "test-model", "low"),
    )

    def render_preconfirm_surfaces(*, repo_root: Path) -> dict[str, Any]:
        for relative_path in greenfield_surface_refresh_proof.GREENFIELD_REQUIRED_SURFACE_ARTIFACTS:
            path = Path(repo_root) / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("stubbed pre-confirm surface\n", encoding="utf-8")
        return surface_refresh_preview_fixture()

    monkeypatch.setattr(
        greenfield_surface_refresh_proof,
        "build_prewrite_surface_refresh_preview",
        render_preconfirm_surfaces,
    )
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
        lambda **_kwargs: {"status": "skipped"},
    )

    rc, output = _run_confirmed_transaction_create(
        repo_root=tmp_path,
        prompt=source,
        capsys=capsys,
    )

    assert rc == 0, output
    assert provider.calls == 2
    assert "- validation gate: passed" in output
    accepted = json.loads(
        (tmp_path / "odylith/runtime/source/accepted-project.v1.json").read_text(encoding="utf-8")
    )
    registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    compass_events = (
        tmp_path / "odylith/compass/runtime/agent-stream.v1.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    release_events = (
        tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl"
    ).read_text(encoding="utf-8").splitlines()
    assert accepted["validation_gate"]["status"] == "passed"
    assert isinstance(accepted["proposal"]["semantic_model"], dict)
    assert len(list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))) >= 2
    assert len(registry["components"]) == len(intent["component_responsibilities"])
    diagram_names = [path.name for path in (tmp_path / "odylith/atlas/source").glob("*.mmd")]
    assert len(diagram_names) == 3
    assert all(not name.endswith("-first-path.mmd") for name in diagram_names)
    for role in ("system-context", "state-evidence", "component-boundaries"):
        assert any(name.endswith(f"-{role}.mmd") for name in diagram_names)
    assert release_events
    assert compass_events and json.loads(compass_events[-1])["kind"] == "decision"
    rendered = _rendered_greenfield_text(tmp_path)
    for expected in expected_terms:
        assert expected in rendered
    for banned in (*_SLOP_PHRASES, *forbidden_terms):
        assert banned not in rendered


def _rendered_greenfield_text(root: Path) -> str:
    suffixes = {".md", ".json", ".jsonl", ".mmd"}
    return "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in root.rglob("*")
        if path.is_file() and path.suffix in suffixes
    ).casefold()


def test_greenfield_generator_source_does_not_bake_fixture_domain_terms() -> None:
    root = Path(__file__).resolve().parents[3]
    source_roots = [
        root / "src/odylith/runtime/domain_intelligence",
        root / "src/odylith/runtime/project_intelligence",
    ]
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for source_root in source_roots
        for path in source_root.rglob("*.py")
    ).casefold()

    leaked = [term for term in _SOURCE_DOMAIN_LEAK_TERMS if term in source_text]

    assert leaked == []
