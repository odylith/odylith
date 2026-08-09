from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import (
    internal_system_rows_from_first_path,
    state_object_from_first_path,
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
    assert "the permit clerks intake applications" in rendered
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


def test_explicit_exception_signoff_remains_a_distinct_product_responsibility() -> None:
    rows = internal_system_rows_from_first_path(
        title="Port Berth Carbon Tariff Planner",
        first_path=(
            "Port operations compare vessel schedules, berth windows, shore-power availability, emissions evidence, "
            "tariff exceptions, and operator signoff before publishing a daily berth plan."
        ),
        state_object="The primary state object is a vessel schedule.",
        visible_result="a published daily berth plan",
        human_actors=("Port operations: compare evidence, resolve exceptions, and sign off.",),
    )

    assert len(rows) >= 3
    assert any("exception review" in row.casefold() for row in rows)
    assert any("exception disposition and signoff" in row.casefold() for row in rows)


def test_leading_action_is_not_treated_as_a_system_subject() -> None:
    rows = internal_system_rows_from_first_path(
        title="Reliability Custody Platform",
        first_path="Record exposure conditions. Preserve custody evidence. Prepare release proof for review.",
        state_object="The primary state object is a sample.",
        visible_result="release proof",
    )

    assert any("records exposure conditions and keeps status" in row for row in rows)
    assert all("— record exposure conditions" not in row for row in rows)


def test_nominal_list_items_render_as_records_instead_of_fake_actions() -> None:
    rows = internal_system_rows_from_first_path(
        title="Research Run Workspace",
        first_path=(
            "Researchers configure a run, observe live counts, inequality checks, QBER, and established key bits, "
            "then compare the saved run against prior results."
        ),
        state_object="The primary state object is a run.",
        visible_result="a saved comparison",
        human_actors=("Researchers: configure and compare runs",),
    )

    rendered = "\n".join(rows)
    assert "Inequality Checks Record — maintains inequality checks, QBER and established key bits" in rendered
    assert "with provenance, status" in rendered
    assert "— checks, QBER" not in rendered


def test_chained_actions_choose_the_durable_object_after_the_final_verb() -> None:
    state_object = state_object_from_first_path(
        (
            "Researchers configure and launch an E91 communication run on real hardware, observe live counts, "
            "record quality checks, and compare the saved run against prior results."
        ),
        fallback="Communication Run Workspace",
    )

    assert state_object == "The primary state object is an E91 communication run."


def test_start_with_path_uses_the_started_item_as_durable_state() -> None:
    assert state_object_from_first_path(
        "Start with inspection tickets, then route a ticket to a mechanic, and produce a repair clearance.",
        fallback="Canal-lock Dispatch Board",
    ) == "The primary state object is an inspection ticket."


def test_complex_first_path_keeps_every_distinct_product_responsibility() -> None:
    rows = internal_system_rows_from_first_path(
        title="Reliability Lab Custody Platform",
        first_path=(
            "Receive wafer lot samples. Record chamber exposure conditions. Preserve chain-of-custody evidence. "
            "Track failed stress runs. Prepare release readiness proof for engineering review."
        ),
        state_object="The primary state object is a wafer lot sample.",
        visible_result="release readiness proof",
    )

    rendered = "\n".join(rows).casefold()
    assert len(rows) >= 5
    assert "failed stress runs" in rendered


def test_two_word_imperatives_remain_actions_instead_of_fake_records() -> None:
    for first_path, expected in (
        ("Approve request.", "approves request"),
        ("Track exceptions.", "tracks exceptions"),
        ("Launch simulation.", "launches simulation"),
    ):
        rows = internal_system_rows_from_first_path(
            title="Review Workspace",
            first_path=first_path,
            state_object="The primary state object is a request.",
            visible_result="a review result",
        )
        rendered = "\n".join(rows).casefold()
        assert expected in rendered
        assert f"{first_path.rstrip('.').casefold()} record" not in rendered


def test_decision_responsibility_names_singularize_plural_action_objects() -> None:
    rows = internal_system_rows_from_first_path(
        title="Customer Recovery Desk",
        first_path="Triage delayed orders. Assign owners. Prove every response path before launch.",
        state_object="The primary state object is a delayed order.",
        visible_result="a proven response path",
    )

    rendered = "\n".join(rows)
    assert "Owner Assignment —" in rendered
    assert "Owners Assignment" not in rendered


def test_explicit_human_subject_stays_human_when_actor_rows_are_missing() -> None:
    rows = internal_system_rows_from_first_path(
        title="Evidence Review Workspace",
        first_path="Researchers compare evidence, exceptions, and signoff before release.",
        state_object="The primary state object is an evidence package.",
        visible_result="a release decision",
        human_actors=(),
    )

    rendered = "\n".join(rows)
    assert "compares evidence" in rendered
    assert "Researchers Compare Evidence Record" not in rendered


def test_explicit_decision_and_signoff_get_a_distinct_review_boundary() -> None:
    rows = internal_system_rows_from_first_path(
        title="Coordinated Review Workspace",
        first_path=(
            "A council coordinates submitted reports, affected-party review, embargo decisions, evidence custody, "
            "legal signoff, and release readiness."
        ),
        state_object="The primary state object is a submitted report.",
        visible_result="release readiness",
        human_actors=("Council: coordinates the first path",),
    )

    assert rows[0].startswith("Submitted Reports Coordination —")
    assert "coordinates submitted reports, affected-party review" in rows[0]
    assert all(not row.startswith("Submitted Reports Delivery —") for row in rows)
    assert any(row.startswith("Decision and Signoff Review —") for row in rows)


def test_receive_and_coordinate_actions_keep_distinct_operational_boundaries() -> None:
    rows = internal_system_rows_from_first_path(
        title="Disclosure Council Workspace",
        first_path=(
            "A council receives reports, coordinates review, records evidence custody, decides embargo status, "
            "and publishes release readiness proof."
        ),
        state_object="The primary state object is a report.",
        visible_result="release readiness proof",
        human_actors=("Council: coordinates the first path",),
    )

    assert rows[0].startswith("Reports Intake —")
    assert rows[1].startswith("Review Coordination —")


def test_durable_on_qualifiers_remain_part_of_the_state_object() -> None:
    for first_path, expected in (
        ("A coordinator records charge on hold reason.", "The primary state object is a charge on hold reason."),
        ("A coordinator records proof on file.", "The primary state object is a proof on file."),
        ("A coordinator records inventory on hand.", "The primary state object is an inventory on hand."),
        ("A coordinator records decision on record.", "The primary state object is a decision on record."),
    ):
        assert state_object_from_first_path(first_path, fallback="case") == expected


def test_durable_on_qualifier_remains_in_responsibility_label() -> None:
    rows = internal_system_rows_from_first_path(
        title="Evidence Review Workspace",
        first_path="A coordinator records proof on file.",
        state_object="The primary state object is a proof on file.",
        visible_result="proof on file",
        human_actors=("Coordinator: records proof",),
    )

    assert any(row.startswith("Proof on File Recordkeeping —") for row in rows)


def test_hyphenated_actor_label_keeps_its_full_identity() -> None:
    rows = internal_system_rows_from_first_path(
        title="Coordinated Review Workspace",
        first_path="A multi-party council coordinates submitted reports and publishes readiness.",
        state_object="The primary state object is a submitted report.",
        visible_result="readiness",
        human_actors=("Multi-party council: coordinates the first path",),
    )

    assert any("to the multi-party council with status" in row for row in rows)
    assert all("Multi-party Council Coordinates" not in row for row in rows)
