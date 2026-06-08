from odylith.runtime.domain_intelligence.greenfield_actor_labels import accepted_actor_label
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row


def test_generic_composite_actor_label_gets_project_focus() -> None:
    row = project_specific_actor_row(
        "Reviewer or collaborator",
        project_focus="Protocol outcome notebook",
    )

    assert row == "Protocol Outcome Notebook Reviewer Or Collaborator"
    assert not row.startswith("Reviewer")


def test_generic_person_actor_uses_accepted_activity_not_project_fallback() -> None:
    assert accepted_actor_label(
        "Person managing their own discomfort (primary user, self-tracking)",
        project_focus="Pattern Relief",
    ) == "Person Managing Discomfort"
    assert accepted_actor_label(
        "Optionally, a coach or clinician the person shares a summary with (read-only, later)",
        project_focus="Pattern Relief",
    ) == "Coach Or Clinician"
