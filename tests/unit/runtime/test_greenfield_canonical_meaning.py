from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import (
    _non_human_subject_prefix,
    canonical_state_object_is_meaningful,
    internal_system_rows_from_first_path,
    state_object_from_first_path,
)


def test_canonical_state_object_requires_a_durable_terminal_noun() -> None:
    assert not canonical_state_object_is_meaningful("The primary state object is a mixed classified.")
    assert canonical_state_object_is_meaningful(
        "The primary state object is a mixed classified and unclassified file."
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
    assert any(row.startswith("Decision Routing") for row in rows)
    assert not any(row.startswith("Reviewer Decisions") for row in rows)
    assert "the product validates" not in rendered
    assert "the product routes" not in rendered


def test_routing_label_keeps_a_domain_object_that_is_not_a_generic_actor_modifier() -> None:
    rows = internal_system_rows_from_first_path(
        title="Permit Packet Dispatch",
        first_path="Dispatch clerks route permit packets. Dispatch clerks see a delivery receipt.",
        state_object="The primary state object is a permit packet.",
        visible_result="a delivery receipt",
        human_actors=("Dispatch clerks: route permit packets and review the receipt.",),
    )

    assert any(row.startswith("Permit Packets Routing") for row in rows)


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


def test_non_human_subject_prefix_keeps_the_full_article_led_system_subject() -> None:
    assert _non_human_subject_prefix("the berth map displays the placement") == "the berth map"


def test_external_source_access_does_not_become_an_internal_system() -> None:
    rows = internal_system_rows_from_first_path(
        title="Trail Closure Bulletin",
        first_path=(
            "Route stewards maintain a trail closure bulletin. They read the forecast service, "
            "record closure reason and inspection evidence, and issue a reopening notice after ranger review."
        ),
        state_object="The primary state object is a trail closure bulletin.",
        visible_result="a reopening notice",
        human_actors=("Route stewards: maintain the closure bulletin.",),
        external_systems=("forecast service",),
    )

    rendered = "\n".join(rows).casefold()
    assert "forecast service record" not in rendered
    assert "closure reason and inspection evidence" in rendered
    assert "reopening notice" in rendered


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


def test_objectless_leading_action_stays_with_the_following_same_owner_action() -> None:
    rows = internal_system_rows_from_first_path(
        title="E91 Quantum Communication Run Workspace",
        first_path=(
            "Researchers configure and launch an E91 quantum communication run on real hardware, observe live "
            "coincidence counts, Bell inequality checks, CHSH, QBER, and established key bits, then compare the "
            "saved run against prior results."
        ),
        state_object="The primary state object is an E91 quantum communication run.",
        visible_result="the saved run against prior results",
        human_actors=("Researchers: configure and compare runs",),
    )

    labels = [row.split(" — ", 1)[0] for row in rows]
    rendered = "\n".join(rows)
    assert len(labels) == len(set(labels))
    assert "Researchers configure and launch an E91 quantum communication run" in rendered
    assert all("First-path Action Is" not in label for label in labels)


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


def test_modal_domain_actor_keeps_distinct_component_responsibilities() -> None:
    rows = internal_system_rows_from_first_path(
        title="Dependency Exception Desk",
        first_path=(
            "A package supply chain exception desk user can receive vulnerable dependency reports, "
            "track provenance and waiver evidence, coordinate package manager review, preserve release "
            "readiness proof, and block shipment until exceptions are approved."
        ),
        state_object="The primary state object is a vulnerable dependency report.",
        visible_result="a release readiness decision",
        human_actors=(
            "Package supply chain exception desk user: completes the accepted review path.",
        ),
    )

    rendered = "\n".join(rows).casefold()
    assert len(rows) >= 5
    assert "vulnerable dependency reports intake" in rendered
    assert "provenance and waiver evidence" in rendered
    assert "package manager review" in rendered
    assert "release readiness proof" in rendered
    assert "shipment" in rendered
    assert "supplies chain" not in rendered


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


def test_state_transition_subject_is_the_durable_object_not_a_clipped_predicate() -> None:
    first_path = (
        "Tuning leads can record a reed measurement. "
        "A route becomes ready after the venue custodian accepts the access window. "
        "The product shows a tuning itinerary."
    )

    assert state_object_from_first_path(first_path, fallback="tuning route") == (
        "The primary state object is a route."
    )


def test_hyphenated_actor_label_keeps_its_full_identity() -> None:
    rows = internal_system_rows_from_first_path(
        title="Coordinated Review Workspace",
        first_path="A multi-party council coordinates submitted reports and publishes readiness.",
        state_object="The primary state object is a submitted report.",
        visible_result="readiness",
        human_actors=("Multi-party council: coordinates the first path",),
    )

    assert any("First-path action is the multi-party council" in row for row in rows)
    assert any(row.startswith("Readiness Publication — publishes readiness") for row in rows)
    assert all("Multi-party Council Coordinates" not in row for row in rows)


def test_named_actor_handoff_keeps_state_and_system_responsibilities_distinct() -> None:
    first_path = (
        "Ivo starts by entering a vessel tag. On a match, the product records the berth as occupied "
        "and the berth map displays the placement."
    )

    assert state_object_from_first_path(first_path, fallback="harbor slate") == (
        "The primary state object is the berth."
    )
    rows = internal_system_rows_from_first_path(
        title="Harbor Slate",
        first_path=first_path,
        state_object="The primary state object is the berth.",
        visible_result="the placement",
        human_actors=("Ivo, a dock attendant: enters a vessel tag",),
    )

    rendered = " ".join(rows).casefold()
    assert "vessel tag intake" in rendered
    assert "berth as occupied recordkeeping" in rendered
    assert "first-path action is ivo enters a vessel tag" in rendered
    assert "berth maps displays" not in rendered


def test_passive_object_event_projects_specific_delivery_ownership() -> None:
    rows = internal_system_rows_from_first_path(
        title="District Heat Outage Ledger",
        first_path=(
            "Service operators open an incident. "
            "A restoration bulletin is published after a supervisor approves the reading."
        ),
        state_object="The primary state object is an incident.",
        visible_result="a restoration bulletin",
        human_actors=("Service operators: need the product to open an incident",),
    )

    assert any(row.startswith("Restoration Bulletin Publication — publishes a restoration bulletin") for row in rows)
    assert all("Workflow Support" not in row for row in rows)


def test_path_definition_does_not_create_a_duplicate_workflow_responsibility() -> None:
    rows = internal_system_rows_from_first_path(
        title="Outage Ledger",
        first_path="Service operators open an incident. The first path is incident intake.",
        state_object="The primary state object is an incident.",
        visible_result="an incident record",
        human_actors=("Service operators: need the product to open an incident",),
    )

    assert any(row.startswith("Incident Intake —") for row in rows)
    assert all(not row.startswith("Incident Intake Workflow —") for row in rows)


def test_actor_receiving_the_visible_result_projects_access_not_intake() -> None:
    rows = internal_system_rows_from_first_path(
        title="Outage Ledger",
        first_path="Tenant liaisons receive a restoration bulletin.",
        state_object="The primary state object is an incident.",
        visible_result="a restoration bulletin",
        human_actors=("Tenant liaisons: need the product to receive a restoration bulletin",),
    )

    assert any(row.startswith("Restoration Bulletin Access —") for row in rows)
    assert all(not row.startswith("Restoration Bulletin Intake —") for row in rows)


def test_carried_action_after_visible_result_keeps_a_distinct_responsibility() -> None:
    rows = internal_system_rows_from_first_path(
        title="Receipt Workspace",
        first_path="Tenant liaisons receive a receipt and archive it.",
        state_object="The primary state object is a request.",
        visible_result="a receipt",
        human_actors=("Tenant liaisons: receive a receipt and archive it",),
    )

    assert any(row.startswith("Receipt Access —") for row in rows)
    assert any(row.startswith("Receipt Recordkeeping —") for row in rows)
    assert all("Receipt And Archive It Access" not in row for row in rows)


@pytest.mark.parametrize(
    "first_path, rejected",
    (
        ("The product records a receipt as evidence and shows the receipt.", "a receipt"),
        ("The product sets a release receipt to PDF and shows it.", "a release receipt"),
    ),
)
def test_presentation_artifacts_are_not_promoted_to_state_transition_objects(
    first_path: str,
    rejected: str,
) -> None:
    assert state_object_from_first_path(first_path, fallback="request") != (
        f"The primary state object is {rejected}."
    )


def test_human_work_inside_an_external_system_is_not_claimed_as_owned_topology() -> None:
    rows = internal_system_rows_from_first_path(
        title="Archive Intake",
        first_path=(
            "Mara, an archive clerk, can complete manifest review. "
            "Mara stages accession crates in VaultLedger. The product generates an intake receipt."
        ),
        state_object="The primary state object is an accession crate.",
        visible_result="an intake receipt",
        human_actors=("Mara, an archive clerk: needs the product to complete manifest review",),
        external_systems=("VaultLedger",),
    )

    rendered = " ".join(rows).casefold()
    assert "manifest review" in rendered
    assert "accession crates in vaultledger" not in rendered
    assert "intake receipt" in rendered
    assert any(row.startswith("Intake Receipt Generation —") for row in rows)
    assert "the mara" not in rendered
    assert "first-path action is mara completes manifest review" in rendered


def test_coordinated_actor_label_is_not_split_into_fake_component_owners() -> None:
    rows = internal_system_rows_from_first_path(
        title="Alpine Refuge Cache",
        first_path=(
            "Refuge wardens and rescue dispatchers can inspect a cache, "
            "log emergency cache inspections, and receive a cache readiness slip."
        ),
        state_object="The primary state object is a cache.",
        visible_result="a cache readiness slip",
        human_actors=(
            "Refuge Wardens and Rescue Dispatchers: need the product to inspect a cache",
        ),
    )

    rendered = " ".join(rows).casefold()
    assert "refuge wardens workflow" not in rendered
    assert "cache inspection" in rendered
    assert "cache readiness slip access" in rendered
