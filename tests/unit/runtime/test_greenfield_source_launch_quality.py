from __future__ import annotations

import json
from pathlib import Path
import re

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.artifact_quality.greenfield_project_prompt_quality import project_implementation_prompt_issues
from odylith.runtime.artifact_quality.greenfield_rendered_artifacts import RenderedArtifact
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_action_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.project_intelligence.source_launch import build_source_launch_handoff


def test_greenfield_source_launch_prompts_keep_sun_burn_copy_complete(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"sunrecover\"\n", encoding="utf-8")
    first_path = (
        "A user opens the app after a burn, captures a photo and answers the intake questions, and immediately receives "
        "a severity read and a first-24-hours action plan. Over the following days the app prompts daily check-ins, "
        "compares new photos and symptom scores against the baseline, updates the plan as the burn settles and the tan "
        "fades, and marks the episode healed — or surfaces a clear escalation warning if severity or warning signs cross "
        "a safety threshold."
    )
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="SunRecover — sunburn relief and skin-recovery coach",
        first_path=first_path,
        actors=(
            ("", "Sun-exposed Individual: contributes information, review, or action needed", ""),
            ("", "Caregiver: reviews the result", ""),
        ),
        components=(
            {"label": "Intake and Severity Assessment Engine", "responsibility": "Captures intake and severity state."},
            {"label": "Staged Recovery-plan Generator", "responsibility": "Returns the first care plan."},
        ),
        risks=(
            {
                "statement": (
                    "A first-24-hours action plan can be wrong or misleading when the information behind it is incomplete, "
                    "stale, inconsistent, or interpreted incorrectly. The weak inputs are a photo and the intake questions; "
                    "Sun-exposed Individual may then act on a result that does not match the real situation."
                )
            },
        ),
        validation=(
            "The accepted first path proves answering the intake questions, receiving a severity read and a first-24-hours "
            "action plan, prompting daily check-ins, and comparing new photos and symptom scores against the baseline.",
        ),
        non_goals=(),
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "Current signal: existing repo language signals point to Python. Confirm that Python is still" in encoded
    assert "Sun-exposed Individual changes or reads" in encoded
    assert "Caregiver" in encoded
    assert "compare new photos and symptom scores against the baseline" in encoded
    assert "receive a user updates" not in encoded
    assert "return a user updates" not in encoded
    assert "clear.." not in encoded
    assert "a photo and answers" not in encoded
    assert "a photo and the intake." not in encoded
    assert "contributes information" not in encoded
    assert "proof gates for the accepted first path proves" not in encoded
    assert "comparing new photos." not in encoded


def test_greenfield_source_launch_prompts_keep_fragments_clause_safe(tmp_path: Path) -> None:
    (tmp_path / "pyproject.toml").write_text("[project]\nname = \"therapy-workspace\"\n", encoding="utf-8")
    first_path = (
        "A pediatric therapy agency practice workspace user can coordinate referral intake, guardian consent, "
        "therapist assignment, care-plan readiness. Visit evidence. Exception review for children served across "
        "multiple schools."
    )

    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Pediatric Therapy Agency Practice Workspace",
        first_path=first_path,
        actors=(
            ("", "Pediatric Therapy Agency Practice Workspace User: coordinates the work", ""),
            ("", "Pediatric Therapy Agency proof reviewer: reviews the result", ""),
        ),
        components=(
            {
                "label": "Pediatric Therapy Agency Practice Workspace Intake",
                "responsibility": "Captures intake evidence and result visibility.",
            },
        ),
        risks=("Exception review for children served across multiple schools can be wrong or misleading.",),
        validation=("Success proof includes coordinating referral intake, guardian consent, therapist assignment, care-plan readiness, visiting evidence, and reviewing for children served across multiple schools.",),
        non_goals=("Authentication, billing, full UI, database persistence, and external APIs.",),
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "., validation points" not in encoded
    assert "., input validation" not in encoded
    assert "and receive Pediatric therapy agency practice workspace user coordinates" not in encoded
    for row in handoff["prompts"]:
        assert generated_public_copy_issues(f"Project implementation prompt `{row['label']}`", row) == ()


def test_greenfield_source_launch_prompts_suppress_repeated_action_outcome(tmp_path: Path) -> None:
    cases = (
        (
            "Security Disclosure Council",
            "A security disclosure council user can receive a disclosure and receive a disclosure.",
            "receive a disclosure and receive a disclosure",
            "capture the information needed to receive a disclosure and return a disclosure",
        ),
        (
            "Port Berth Carbon Tariff",
            "A port berth carbon tariff user can review compliance exceptions and receive compliance exceptions.",
            "review compliance exceptions and receive compliance exceptions",
            "capture the information needed to review compliance exceptions and return compliance exceptions",
        ),
    )
    for title, first_path, duplicated_path, duplicated_capability in cases:
        handoff = build_source_launch_handoff(
            repo_root=tmp_path,
            title=title,
            first_path=first_path,
            actors=(("", f"{title} User: coordinates the work", ""),),
            components=(),
            risks=(),
            validation=(),
            non_goals=(),
        )
        encoded = json.dumps(handoff, sort_keys=True).casefold()

        assert duplicated_path not in encoded
        assert duplicated_capability not in encoded
        for row in handoff["prompts"]:
            assert generated_public_copy_issues(f"Project implementation prompt `{row['label']}`", row) == ()


def test_greenfield_source_launch_prompt_accepts_request_shaped_product_titles(tmp_path: Path) -> None:
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Build an ecommerce checkout recovery product",
        first_path=(
            "A shopper starts checkout, sees a failed payment reason, edits payment details, "
            "and receives a recovered order confirmation."
        ),
        actors=(("", "Shopper: reviews checkout status", ""), ("", "Support coordinator: reviews recovery evidence", "")),
        components=(
            {"label": "Checkout Recovery", "responsibility": "Recover failed checkouts."},
        ),
        risks=(
            {"statement": "A shopper may lose trust if the recovery path creates duplicate charge confusion."},
        ),
        validation=("A recovered checkout is shown with replayable evidence.",),
        non_goals=("Payment processor integration.",),
        source_launch_context={
            "start_workstream_id": "B-001",
            "start_workstream_title": "Recover failed checkout",
            "release_selector": "0.0.1",
        },
    )
    encoded = json.dumps(handoff, sort_keys=True).casefold()

    assert "product product" not in encoded
    assert "smallest runnable build an ecommerce checkout recovery product slice" in encoded
    for row in handoff["prompts"]:
        artifact = RenderedArtifact(
            "Project implementation prompt",
            row["label"],
            "\n".join(str(row.get(key, "")) for key in ("label", "when", "prompt", "result", "stop")),
            fields={**row, "position": str(handoff["prompts"].index(row) + 1)},
        )
        assert generated_public_copy_issues(f"Project implementation prompt `{row['label']}`", row) == ()
        assert project_implementation_prompt_issues(artifact) == []


def test_greenfield_source_launch_prompts_render_proof_from_base_actions(tmp_path: Path) -> None:
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Package Manager Supply Chain Exception Desk",
        first_path=(
            "A package-manager supply-chain exception desk receives vulnerable dependency reports, "
            "maps affected package owners, records waiver rationale, tracks provenance and build evidence, "
            "and publishes release readiness without auto-upgrading production dependencies."
        ),
        actors=(
            ("", "Package Manager Supply Chain Exception Desk User: reviews the result", ""),
            ("", "Security Reviewer: approves exceptions", ""),
        ),
        components=(),
        risks=("Release readiness without auto-upgrading production dependencies can be wrong or misleading.",),
        validation=(
            "Success proof includes supplying chain exception desk user receives vulnerable dependency reports, "
            "mapping affected package owners, recording waiver rationale, and tracking provenance and building evidence.",
        ),
        non_goals=("Authentication, billing, full UI, database persistence, and external APIs.",),
        source_launch_context={
            "start_workstream_id": "B-002",
            "start_workstream_title": "Map affected package owners",
            "release_selector": "0.0.1",
            "coding_readiness_gates": (
                "The accepted product story names the user problem.",
                "The first implementation lane is ready.",
            ),
            "validation_gates": (
                "Validate one successful path.",
                "Validate one missing-input path.",
                "Validate one corrected path.",
            ),
            "verification_commands": (
                "odylith context --repo-root . B-002",
                "odylith validate plan-workstream-binding --repo-root .",
                "odylith validate plan-traceability --repo-root .",
            ),
        },
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "receive vulnerable dependency reports" in encoded
    assert "track provenance and build evidence" in encoded
    assert "receive release readiness without auto-upgrading production dependencies" in encoded
    assert "Tests and validation evidence that the accepted path can receive vulnerable dependency reports" in encoded
    assert "supplying chain exception desk user receives" not in encoded
    assert "tracking provenance and building evidence" not in encoded
    assert "Tests and validation evidence covering" not in encoded
    assert "receive Release readiness" not in encoded
    assert "package Manager" not in encoded
    for row in handoff["prompts"]:
        artifact = RenderedArtifact(
            "Project implementation prompt",
            row["label"],
            "\n".join(str(row.get(key, "")) for key in ("label", "when", "prompt", "result", "stop")),
            fields={**row, "position": str(handoff["prompts"].index(row) + 1)},
        )
        assert project_implementation_prompt_issues(artifact) == []


def test_greenfield_source_launch_refresh_prompt_uses_consumer_safe_governed_record_names(tmp_path: Path) -> None:
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Regional Drone Corridor Safety Console",
        first_path=(
            "Municipal airspace coordinator records a corridor request, route constraint reviewer checks blocked constraints, "
            "and public information officer publishes a safe operating status."
        ),
        actors=(("", "Municipal airspace coordinator: reviews corridor readiness", ""),),
        components=(
            {"label": "Corridor Readiness Console", "responsibility": "Records corridor request evidence."},
        ),
        risks=("A safe operating status can be wrong when constraints are stale.",),
        validation=("Validate one successful corridor request and one blocked constraint path.",),
        non_goals=("Live aviation integration.",),
        source_launch_context={
            "start_workstream_id": "B-002",
            "start_workstream_title": "Record corridor request",
            "release_selector": "0.0.1",
        },
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "Project dashboard" in encoded
    assert "workstream records" in encoded
    assert "component records" in encoded
    assert "architecture diagrams" in encoded
    assert "Radar workstreams" not in encoded
    assert "Registry components" not in encoded
    assert "Atlas diagrams" not in encoded
    for row in handoff["prompts"]:
        artifact = RenderedArtifact(
            "Project implementation prompt",
            row["label"],
            "\n".join(str(row.get(key, "")) for key in ("label", "when", "prompt", "result", "stop")),
            fields={**row, "position": str(handoff["prompts"].index(row) + 1)},
        )
        assert project_implementation_prompt_issues(artifact) == []


def test_greenfield_source_launch_prompts_render_single_step_proof_from_base_action(tmp_path: Path) -> None:
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Release Readiness Gate",
        first_path="A release readiness gate publishes release readiness without shipment.",
        actors=(("", "Release Manager: reviews release readiness", ""),),
        components=(),
        risks=("Release readiness without shipment can be wrong or misleading.",),
        validation=("Success proof includes publishing release readiness without shipment.",),
        non_goals=("Authentication, billing, full UI, database persistence, and external APIs.",),
        source_launch_context={
            "start_workstream_id": "B-002",
            "start_workstream_title": "Publish release readiness",
            "release_selector": "0.0.1",
            "validation_gates": ("Validate one successful path.", "Validate one missing-input path."),
        },
    )
    encoded = json.dumps(handoff, sort_keys=True)

    assert "Tests and validation evidence that the accepted path can publish release readiness without shipment." in encoded
    assert "publishing release readiness without shipment" not in encoded
    assert "Tests and validation evidence covering" not in encoded
    for row in handoff["prompts"]:
        artifact = RenderedArtifact(
            "Project implementation prompt",
            row["label"],
            "\n".join(str(row.get(key, "")) for key in ("label", "when", "prompt", "result", "stop")),
            fields={**row, "position": str(handoff["prompts"].index(row) + 1)},
        )
        assert project_implementation_prompt_issues(artifact) == []


def test_greenfield_source_launch_actor_led_path_uses_modal_base_grammar(tmp_path: Path) -> None:
    first_path = (
        "Materials intake coordinator records one lab batch and precursor lot, safety reviewer checks blocking observations, "
        "process engineer records exception rationale, compliance reviewer approves or rejects manufacturing readiness, "
        "and release owner publishes a manufacturing-readiness status with replay evidence."
    )
    handoff = build_source_launch_handoff(
        repo_root=tmp_path,
        title="Battery Materials Release Evidence Desk",
        first_path=first_path,
        actors=(
            ("", "Materials intake coordinator: records lab batch evidence", ""),
            ("", "Safety reviewer: checks safety constraints", ""),
        ),
        components=(
            {"label": "Batch Evidence Console Service", "responsibility": "Records lab batch evidence."},
            {"label": "Safety Constraint Ledger", "responsibility": "Checks blocking observations."},
        ),
        risks=("Manufacturing readiness can be wrong when the review evidence is incomplete.",),
        validation=("Validate success, blocked input, replay, and handoff evidence.",),
        non_goals=("No automated chemistry approval.",),
        source_launch_context={
            "start_workstream_id": "B-002",
            "start_workstream_title": "Record lab batch evidence",
            "release_selector": "0.0.1",
            "coding_readiness_gates": (
                "The accepted product story names the user problem: materials teams need clear release evidence before manufacturing readiness.",
                "The first implementation lane is ready when it covers: intake coordinator records one lab batch, safety reviewer checks blocking observations, and compliance reviewer approves or rejects manufacturing readiness.",
            ),
            "verification_commands": (
                "odylith context --repo-root . B-002",
                "odylith validate plan-workstream-binding --repo-root .",
                "odylith validate plan-traceability --repo-root .",
            ),
        },
    )
    encoded = json.dumps(handoff, sort_keys=True)
    model = first_path_model(first_path)

    assert model.visible_outcome == "Compliance reviewer approves or rejects manufacturing readiness"
    assert (
        "the materials intake coordinator can record one lab batch and precursor lot "
        "and receive the approved or rejected manufacturing readiness"
    ) in encoded
    assert "the user can intake coordinator records" not in encoded
    assert "can record one lab batch and precursor lot and receives" not in encoded
    assert not re.search(r"\bapproves\s+or\s+reject\b(?!s)", encoded, flags=re.IGNORECASE)
    assert "governed workstream" not in encoded
    assert "accepted first-release work item lookup" in encoded
    assert "accepted work item binding check" in encoded
    assert "implementation traceability check" in encoded
    assert "preserve," not in encoded
    for row in handoff["prompts"]:
        artifact = RenderedArtifact(
            "Project implementation prompt",
            row["label"],
            "\n".join(str(row.get(key, "")) for key in ("label", "when", "prompt", "result", "stop")),
            fields={**row, "position": str(handoff["prompts"].index(row) + 1)},
        )
        assert project_implementation_prompt_issues(artifact) == []


def test_greenfield_backlog_proof_subject_strips_actor_role_before_gerund() -> None:
    subject = proof_action_subject(
        "intake coordinator records one lab batch and precursor lot; "
        "check blocking observations; process engineer records exception rationale; "
        "approve or reject manufacturing readiness"
    )

    assert "intaking coordinator" not in subject
    assert "recording one lab batch and precursor lot" in subject
    assert "checking blocking observations" in subject
    assert "approving or rejecting manufacturing readiness" in subject


def test_greenfield_project_prompt_quality_rejects_gerundized_actor_drift() -> None:
    artifact = RenderedArtifact(
        "Project implementation prompt",
        "Add tests and proof",
        "",
        fields={
            "label": "Add tests and proof",
            "when": "Use this after the first runnable slice exists.",
            "prompt": (
                "Odylith, add behavior proof for the accepted product. Test the accepted path with validation. "
                "Bind the proof to governed workstream B-002."
            ),
            "result": (
                "Tests and validation evidence covering supplying chain exception desk user receives vulnerable "
                "dependency reports, mapping affected package owners, recording waiver rationale, and tracking "
                "provenance and building evidence."
            ),
            "stop": "Stop if validation fails.",
            "position": "4",
        },
    )

    issues = project_implementation_prompt_issues(artifact)

    assert any("gerundized actor" in issue for issue in issues)
    assert not any("proof-action chain" in issue for issue in issues)


def test_greenfield_project_prompt_quality_accepts_noun_heavy_covering_results() -> None:
    artifact = RenderedArtifact(
        "Project implementation prompt",
        "Add tests and proof",
        "",
        fields={
            "label": "Add tests and proof",
            "when": "Use this after the first runnable slice exists.",
            "prompt": (
                "Odylith, add behavior proof for the accepted product. Test valid input, missing required input, "
                "blocked outcomes, and validation evidence for governed workstream B-002 without widening scope."
            ),
            "result": "Tests and validation evidence covering screening intake, staffing review, and packaging approval.",
            "stop": "Stop if validation fails.",
            "position": "4",
        },
    )

    assert project_implementation_prompt_issues(artifact) == []
