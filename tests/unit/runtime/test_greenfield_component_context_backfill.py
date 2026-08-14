from __future__ import annotations

from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import context_object_phrases
from odylith.runtime.domain_intelligence.greenfield_component_semantic_context import needs_context_backfill


def test_rich_local_component_description_does_not_import_whole_path_context() -> None:
    assert not needs_context_backfill(
        description=(
            "records when the user receives a qualified report and keeps report status, blockers, evidence, "
            "and visible handoff context"
        ),
        description_phrases=(
            "qualified report",
            "report status",
            "blockers",
            "visible handoff context",
        ),
        context_required_phrases=(
            "provenance decision",
            "manager approval",
            "shipment blocker",
        ),
    )
    assert not needs_context_backfill(
        description="owns supporting facts review records, status, blockers, evidence, and handoff context",
        description_phrases=("supporting facts review records", "blockers", "handoff context"),
        context_required_phrases=("bring request", "readiness decision", "rationale record"),
    )
    assert not needs_context_backfill(
        description="owns review coordination records, status, blockers, evidence, and handoff context",
        description_phrases=("review coordination records", "blockers", "handoff context"),
        context_required_phrases=("invalid clear blocker", "primary object report"),
    )


def test_sparse_or_generated_component_description_still_receives_context_backfill() -> None:
    assert needs_context_backfill(
        description="keeps request context visible",
        description_phrases=("request context",),
        context_required_phrases=("request deadline", "approval state"),
    )
    assert needs_context_backfill(
        description=(
            "keeps required inputs, blocked-case evidence, and handoff boundaries for the confirmed first path"
        ),
        description_phrases=("required input record", "blocked-case evidence", "handoff boundary"),
        context_required_phrases=("request deadline", "approval state"),
    )


def test_broad_local_detail_uses_anchored_first_path_fields() -> None:
    assert needs_context_backfill(
        description=(
            "records episode details, validates required fields, stores correction history, and blocks incomplete entries"
        ),
        description_phrases=("episode details", "correction history", "incomplete entries"),
        context_required_phrases=("entry intensity", "entry body area"),
    )


def test_measurement_component_keeps_context_needed_to_define_values() -> None:
    assert needs_context_backfill(
        description="records measurement data, measurement status, and source context",
        description_phrases=("measurement data", "measurement status", "source context"),
        context_required_phrases=("baseline measurement", "follow-up value", "unit source"),
    )


def test_generic_proof_behavior_does_not_become_an_owned_object_phrase() -> None:
    phrases = context_object_phrases(
        (
            "An operator records an incident report. The product explains missing or invalid input with a clear blocker "
            "and keeps replayable evidence for review."
        ),
        label_terms=("incident", "report", "intake"),
        description_terms=("incident", "report", "record"),
    )

    rendered = " ".join(phrases).casefold()
    assert "invalid clear blocker" not in rendered
    assert "clear blocker replayable" not in rendered
