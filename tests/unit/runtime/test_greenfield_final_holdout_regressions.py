from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_findings
from odylith.runtime.artifact_quality.greenfield_package_quality import greenfield_rendered_package_quality_issues
from odylith.runtime.artifact_quality.greenfield_project_judgment import project_story_semantic_issues
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_proposals import build_greenfield_proposal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from tests.unit.runtime.greenfield_proposal_fixtures import stub_preconfirm_surface_refresh


@pytest.fixture(autouse=True)
def _preconfirm_surface_fixture(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_preconfirm_surface_refresh(monkeypatch)


@pytest.mark.parametrize(
    ("name", "prompt", "required_path_terms", "excluded_path_terms", "expected_external_terms"),
    (
        (
            "reordered orchard evidence",
            (
                "A note about old orchard fence paint is out of scope. The Grove Roster supplies lot names and "
                "must not be changed. At the packing shed, inspection notes are visible only to that shed. Mara is "
                "the packing-shed clerk using the Orchard Bin Ledger: she records a returned crate, chooses its "
                "orchard lot, marks it inspected, then sees the daily return tally. Success means that one record "
                "produces that tally."
            ),
            ("records a returned crate", "daily return tally"),
            ("fence paint", "grove roster supplies"),
            ("grove roster",),
        ),
        (
            "quiet room evidence",
            (
                "Niko, a library host, reserves a quiet-room slot in the Lantern Desk. Niko chooses a room and "
                "marks the slot held; the visitor-facing board then shows the room and time. Room availability is "
                "read from the Hall Calendar. Do not promise a reservation until the calendar returns availability."
            ),
            ("marks the slot held", "shows the room and time"),
            ("room availability is read",),
            ("hall calendar",),
        ),
        (
            "tool loan JSON",
            (
                '{"operator":"Sana","role":"workshop steward","product":"Bench Borrower",'
                '"path":["scan tool tag","set loan state to checked out","show return due date"],'
                '"source":"Tool Shelf Index","constraint":"never mark unavailable tools checked out"}'
            ),
            ("scan tool tag", "show return due date"),
            ('{"operator"',),
            ("tool shelf index",),
        ),
        (
            "marina evidence",
            (
                "Harbor Slate is for dock attendant Ivo. Ivo starts by entering a vessel tag. On a match, the "
                "product records the berth as occupied and the berth map displays the placement. Tide Ledger "
                "supplies assignments; Harbor Slate cannot edit it."
            ),
            ("entering a vessel tag", "berth map displays"),
            ("tide ledger supplies",),
            ("tide ledger",),
        ),
        (
            "museum evidence",
            (
                "Uma, an exhibit preparer, drafts a label request in Gallery Slip. Uma selects an object code, sets "
                "the request to awaiting review, and sees a curator queue number. Object codes come from Collection "
                "Shelf. Gallery Slip must not authenticate provenance, appraise value, or publish a label."
            ),
            ("awaiting review", "curator queue number"),
            ("collection shelf",),
            ("collection shelf",),
        ),
        (
            "unseen acoustic workflow vocabulary",
            (
                "Ari, an acoustic technician, uses Fathom Console to calibrate a sensor, compare a reference trace, "
                "and receive a variance report. Reference traces come from the Anechoic Archive. Fathom Console "
                "cannot certify that a device is safe."
            ),
            ("calibrate a sensor", "variance report"),
            ("anechoic archive", "certify"),
            ("anechoic archive",),
        ),
    ),
)
def test_ranked_evidence_compiles_the_complete_path_without_false_clarification(
    tmp_path: Path,
    name: str,
    prompt: str,
    required_path_terms: tuple[str, ...],
    excluded_path_terms: tuple[str, ...],
    expected_external_terms: tuple[str, ...],
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=name,
    )

    first_path = str(intent["first_path"]).casefold()
    external_systems = " ".join(str(row) for row in intent["external_systems"]).casefold()
    assert all(term in first_path for term in required_path_terms)
    assert all(term not in first_path for term in excluded_path_terms)
    assert all(term in external_systems for term in expected_external_terms)
    if name == "unseen acoustic workflow vocabulary":
        assert intent["title"] == "Fathom Console"


@pytest.mark.parametrize(
    ("prompt", "expected_fields"),
    (
        (
            "Dara uses Stall Signal to record a stall arrival. One note says the display is for vendors only; "
            "another says the same display must be public. The display audience is unresolved.",
            ("display_audience",),
        ),
        (
            "Noel records a sample card. One sentence says it is an observation record only; another says it must "
            "declare the water safe to drink. Those proof boundaries conflict.",
            ("proof_boundary",),
        ),
        (
            "Build Quay Token for ferry kiosk helper Pia to log paper tokens.",
            ("visible_result", "dependency_source"),
        ),
        (
            "Create Kite List for youth-club coordinator Lea to note member arrivals.",
            ("visible_result", "state_transition", "proof_boundary"),
        ),
    ),
)
def test_material_clarification_is_field_specific_and_write_free(
    tmp_path: Path,
    prompt: str,
    expected_fields: tuple[str, ...],
) -> None:
    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Focused Product",
        )

    assert error.value.required_fields == expected_fields
    assert str(error.value).endswith("?")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_unresolved_domain_state_does_not_invent_a_material_contradiction(tmp_path: Path) -> None:
    prompt = (
        "Create a dashboard for unresolved service tickets where an operator reviews source logs, assigns an owner, "
        "and sees a resolution queue."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Service Ticket Dashboard",
    )

    assert "resolution queue" in str(intent["first_path"]).casefold()


def test_domain_conflict_outcome_does_not_invent_a_material_contradiction(tmp_path: Path) -> None:
    prompt = (
        "Build a Quantum Networking Lab Management App where lab operators reserve a calibrated entanglement "
        "link for an experiment, confirm device and calibration availability, record either a conflict or an "
        "accepted reservation, and see an auditable ready-to-run reservation."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Quantum Networking Lab Management App",
    )

    first_path = str(intent["first_path"]).casefold()
    assert "record either a conflict or an accepted reservation" in first_path
    assert "auditable ready-to-run reservation" in first_path


@pytest.mark.parametrize(
    "edit_evidence",
    (
        "Only change the actor name.",
        "Preserve the existing flow and add a calendar sync.",
    ),
)
def test_vague_edit_directives_require_a_concrete_correction(
    tmp_path: Path,
    edit_evidence: str,
) -> None:
    prompt = (
        "Rae, a service coordinator, reviews one support case, assigns an owner, and sees a resolution summary."
    )

    with pytest.raises(ValueError, match="What should change about the first complete path"):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Service Resolution",
            edit_evidence=edit_evidence,
        )

    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    ("prompt", "edit_evidence", "path_term", "boundary_term"),
    (
        (
            (
                "Rae, a seed-library volunteer, prepares a pickup packet in Sprout Counter. Rae searches a member "
                "code, reserves one seed packet, and sees a pickup label."
            ),
            (
                "## Confirmed edit\nKeep the Circle Register and Packet Shelf availability checks. Make the "
                "existing boundary explicit: Sprout Counter prepares the pickup label but does not send messages."
            ),
            "pickup label",
            "does not send messages",
        ),
        (
            (
                "Oren, the prop-room keeper, uses Cue Crate to receive a returned prop. The keeper scans the prop "
                "label, selects sound or repair-needed, and gets a shelf-return card."
            ),
            (
                "## Confirmed edit\nKeep the sound and repair-needed choices. Preserve the boundary that "
                "repair-needed props stay off the ready shelf."
            ),
            "shelf-return card",
            "stay off the ready shelf",
        ),
    ),
)
def test_additive_edit_rebuild_preserves_path_and_boundary(
    tmp_path: Path,
    prompt: str,
    edit_evidence: str,
    path_term: str,
    boundary_term: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Edited Product",
        edit_evidence=edit_evidence,
    )

    assert path_term in str(intent["first_path"])
    assert boundary_term in " ".join(intent["operational_constraints"]).casefold()


@pytest.mark.parametrize(
    ("prompt", "external_source"),
    (
        (
            (
                "Mara, a packing-shed clerk, records each returned crate in the Orchard Bin Ledger. She selects the "
                "orchard lot, marks the crate inspected, and sees a daily return tally. The ledger imports lot names "
                "from the Grove Roster. Keep inspection notes visible only to the packing shed."
            ),
            "grove roster",
        ),
        (
            (
                "Tomas, an aviary volunteer, logs a feeder refill in Perch Note. Tomas selects an enclosure, records the "
                "feeder refilled state, and receives a shift summary. Enclosure names come from Roost Index. Perch Note "
                "must never diagnose an animal, prescribe feed, or state that an enclosure is healthy."
            ),
            "roost index",
        ),
    ),
)
def test_project_and_radar_copy_is_complete_and_nonrepetitive(
    tmp_path: Path,
    prompt: str,
    external_source: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Complete Copy Product",
    )
    proposal = build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=intent,
        require_completion_ready=False,
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
    package = prewrite.package
    package_issues = greenfield_rendered_package_quality_issues(package)
    rendered = "\n".join(
        [
            *package.backlog_result["idea_files"].values(),
            *package.rendered_component_specs.values(),
            *package.rendered_atlas_sources.values(),
            package.project_brief_record_text,
        ]
    ).casefold()
    copy_debt = ("adjacent duplicate", "clipped", "repeats noncanonical", "semantically repetitive")

    assert not [issue for issue in package_issues if any(term in issue for term in copy_debt)]
    assert external_source in rendered
    for scope, value in (
        ("project dashboard preview", package.project_dashboard_preview),
        ("prewrite Radar package", package.backlog_result),
    ):
        categories = {finding.category for finding in generated_public_copy_findings(scope, value)}
        assert "adjacent_duplicate_word" not in categories
        assert "clipped_public_copy" not in categories

    story = package.project_dashboard_preview["product_story"]["release_contract"]
    assert project_story_semantic_issues(story) == []
    bodies = [str(row["body"]).strip() for row in story]
    assert len(bodies) == len(set(body.casefold() for body in bodies))
    assert all(body.endswith((".", "?", "!")) for body in bodies)
    assert all(not body.casefold().endswith(("such as.", "plus.")) for body in bodies)
