from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row


def test_generic_composite_actor_label_gets_project_focus() -> None:
    row = project_specific_actor_row(
        "Reviewer or collaborator",
        project_focus="Protocol outcome notebook",
    )

    assert row == "Protocol Outcome Notebook Reviewer or Collaborator"
    assert not row.startswith("Reviewer")


def test_generic_person_actor_uses_accepted_activity_not_project_fallback() -> None:
    assert accepted_actor_label(
        "Person managing their own discomfort (primary user, self-tracking)",
        project_focus="Pattern Relief",
    ) == "Person Managing Discomfort"
    assert accepted_actor_label(
        "Optionally, a coach or clinician the person shares a summary with (read-only, later)",
        project_focus="Pattern Relief",
    ) == "Coach or Clinician"


def test_actor_label_keeps_comma_gerund_descriptions_out_of_visible_actor_names() -> None:
    assert accepted_actor_label(
        "The person on the GLP-1 medication, tracking their own treatment (the only first-class user)",
        project_focus="Medication Companion",
    ) == "Person on the GLP-1 Medication"
    assert accepted_actor_label(
        "Optionally, a caregiver helping that person stay on schedule (later, not in the first path)",
        project_focus="Medication Companion",
    ) == "Caregiver"
    assert "Tracking Their Own Treatment" not in project_specific_actor_row(
        "The person on the GLP-1 medication, tracking their own treatment (the only first-class user)",
        project_focus="Medication Companion",
    )
    assert "Caregiver Helping" not in project_specific_actor_row(
        "Optionally, a caregiver helping that person stay on schedule (later, not in the first path)",
        project_focus="Medication Companion",
    )


def test_actor_label_splits_inline_activity_from_role_head() -> None:
    row = "Discomfort sufferer logging and reviewing their own episodes"

    assert accepted_actor_label(row, project_focus="Personal tracker") == "Discomfort Sufferer"
    assert project_specific_actor_row(row, project_focus="Personal tracker") == (
        "Discomfort Sufferer: logging and reviewing their own episodes"
    )
