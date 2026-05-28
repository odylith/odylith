from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row


def test_generic_composite_actor_label_gets_project_focus() -> None:
    row = project_specific_actor_row(
        "Reviewer or collaborator",
        project_focus="Protocol outcome notebook",
    )

    assert row == "Protocol Outcome Notebook Reviewer Or Collaborator"
    assert not row.startswith("Reviewer")
