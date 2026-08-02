from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import (
    internal_system_rows_from_first_path,
)


def test_human_actions_keep_domain_state_without_transferring_ownership_to_product() -> None:
    rows = internal_system_rows_from_first_path(
        title="Municipal Permit Review Workspace",
        first_path=(
            "Permit clerks intake applications. Permit clerks validate zoning attachments. "
            "Permit clerks route reviewer decisions. Permit clerks show applicants a clear approval packet."
        ),
        state_object="The primary state object is an application.",
        visible_result="a clear approval packet",
        human_actors=("Permit clerks: complete the first path and review the visible result.",),
    )

    rendered = "\n".join(rows).casefold()
    assert "applications intake" in rendered
    assert "input and required context provided by the permit clerks" in rendered
    assert "zoning attachments validation performed by the permit clerks" in rendered
    assert "routing of reviewer decisions performed by the permit clerks" in rendered
    assert "the product validates" not in rendered
    assert "the product routes" not in rendered


def test_human_record_action_is_not_misclassified_as_a_nonhuman_record_subject() -> None:
    rows = internal_system_rows_from_first_path(
        title="Lab Reservation Workspace",
        first_path=(
            "Lab operators confirm device availability. "
            "Lab operators record either a conflict or an accepted reservation."
        ),
        state_object="The primary state object is a reservation.",
        visible_result="an accepted reservation",
        human_actors=("Lab operators: complete the first path and review the visible result.",),
    )

    assert any(row.startswith("Conflict or Accepted Reservation Recordkeeping") for row in rows)
    assert any("lab operators record either a conflict" in row.casefold() for row in rows)
