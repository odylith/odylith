from __future__ import annotations

import hashlib
import json
from argparse import Namespace
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_intent_authority
from odylith.runtime.domain_intelligence.greenfield_proposals import load_confirmed_intent_args
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_ENGINE_VERSION
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import PRECONFIRM_QUALITY_MANIFEST_VERSION
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_confirmed_intent,
    materialize_prompt_intent_hypothesis,
    render_product_intent_preview,
)
from odylith.runtime.domain_intelligence import greenfield_prompt_intent_materialization
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_snapshot_hash,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_greenfield_package_fixture


_CONFIRMED_INTENT = """# Lab Evidence Review Workspace - Product Intent Confirmation

## Product story
Research coordinators need one accountable workspace for turning dense lab submission notes into a reviewed evidence package without treating planning notes or implementation guidance as product truth. The product keeps intake, review, custody, and release-readiness decisions understandable before broader automation exists.

## State object
The lab evidence package records submitted sample context, reviewer notes, custody status, method constraints, evidence gaps, release-readiness status, and the reviewer decision that must stay visible across the evidence review path.

## First complete path
A research coordinator opens a new lab evidence package, records the submitted sample context, attaches method constraints, assigns a reviewer, resolves evidence gaps, saves custody status, and sees a release-readiness decision with the accepted proof trail.

## Human actors
- Research Coordinator: needs the product to record sample context, route review, resolve evidence gaps, and keep the accepted release-readiness decision visible.
- Evidence Reviewer: needs the product to review method constraints, add proof notes, and confirm the evidence package is ready or blocked.

## External systems
- Existing laboratory submission notes and sample tracking exports.

## Internal product systems
- Evidence Intake Workspace: receives lab submission details and keeps package state available for review.
- Custody Review Ledger: records reviewer decisions, evidence gaps, custody status, and proof trail changes.
- Release Readiness View: shows the accepted decision, blocked-path evidence, and visible proof summary.

## Critical assumptions
- Release 0.0.1 records evidence review and custody proof only.

## Ambiguities
- Live laboratory integrations can wait until the first package review path is proven.

## Proof boundary
Release 0.0.1 is proven only when the same lab evidence package can be opened, reviewed, updated with custody proof, and read back with the release-readiness decision and blocked evidence intact.
"""


def _approved_quality_manifest() -> dict[str, Any]:
    return {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "status": "passed",
        "validation_status": "passed",
        "hard_blocker": False,
        "issue_count": 0,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }


def _recorded_authority(tmp_path: Path) -> tuple[Path, dict[str, Any], dict[str, Any]]:
    path = tmp_path / "confirmed-intent.md"
    path.write_text(_CONFIRMED_INTENT, encoding="utf-8")
    record = load_confirmed_intent_record(path, prompt="Build the lab evidence review workspace.")
    structured_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=path,
    )
    return path, record.product_facts, authority


def _transaction(tmp_path: Path, *, authority: dict[str, Any] | None = None) -> Any:
    path, facts, file_authority = _recorded_authority(tmp_path)
    intent_authority = authority or file_authority
    proposal = {
        "intent": facts,
        PRODUCT_INTENT_AUTHORITY_KEY: intent_authority,
        "backlog": [{"title": "Prove lab evidence review path"}],
        "components": [],
        "diagrams": [],
    }
    package = compiled_greenfield_package_fixture(
        proposal=proposal,
        repo_root=tmp_path,
    )
    return build_product_create_transaction(
        proposal=proposal,
        release_selector="0.0.1",
        validation_gate={"status": "passed", "issues": []},
        prewrite_package=package,
        backlog_result=package.backlog_result or {},
        intent_authority=intent_authority,
        quality_manifest=_approved_quality_manifest(),
        repo_root=tmp_path,
    )


def test_product_create_transaction_carries_confirmed_intent_authority_block(tmp_path: Path) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    payload = product_create_transaction_to_dict(transaction)

    persisted = payload["intent_authority"]
    assert persisted["version"] == "odylith.product-intent-authority.v2"
    assert persisted["origin"] == "verified_typed_envelope"
    assert persisted["decision"] == "confirmed_intent_accepted"
    assert persisted["fact_authority"] == "product_facts"
    assert persisted["markdown_authority"] == "ingest_only"
    assert persisted[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert persisted["markdown_source_sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()
    assert persisted["markdown_source_path"] == str(path)
    assert persisted["structured_intent_path"] == str(path.with_suffix(".json"))
    assert persisted["source_format"] == "markdown"
    assert persisted["materiality_status"] == "passed"
    assert persisted["material_custody_sha256"]
    assert persisted["authority_snapshot_sha256"] == product_intent_authority_snapshot_hash(persisted)
    assert persisted["material_fields"]["first_path"]["custody_state"] == "accepted_fact"
    assert payload["transaction_hash"] == transaction.transaction_hash

    restored = product_create_transaction_from_dict(payload)

    assert restored.intent_authority[PRODUCT_FACTS_HASH_KEY] == authority[PRODUCT_FACTS_HASH_KEY]
    assert restored.summary()["product_facts_sha256"] == authority[PRODUCT_FACTS_HASH_KEY]


def test_product_create_transaction_rejects_missing_intent_authority_payload(tmp_path: Path) -> None:
    payload = product_create_transaction_to_dict(_transaction(tmp_path))
    payload.pop("intent_authority")

    with pytest.raises(ValueError, match="Product Intent authority"):
        product_create_transaction_from_dict(payload)


def test_product_create_transaction_rejects_blocked_materiality_authority(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    blocked = {
        **authority,
        "materiality_status": "clarification_required",
        "blocked_material_fields": ["first_path"],
    }
    blocked["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(blocked)

    with pytest.raises(ValueError, match="did not pass materiality"):
        _transaction(tmp_path, authority=blocked)


def test_product_create_transaction_rejects_inferred_material_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "custody_state": "inferred_fact",
        "derivation": "normalization_or_completion",
        "confidence": "medium",
        "source_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="unresolved material custody"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_accepted_material_fact_without_source_custody(tmp_path: Path) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "source_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="missing material source custody"):
        _transaction(tmp_path, authority=mutated)


def test_product_create_transaction_rejects_markdown_material_fact_without_product_claim_custody(
    tmp_path: Path,
) -> None:
    _path, _facts, authority = _recorded_authority(tmp_path)
    material_fields = {key: dict(value) for key, value in authority["material_fields"].items()}
    material_fields["first_path"] = {
        **material_fields["first_path"],
        "product_claim_span_ids": [],
    }
    mutated = {
        **authority,
        "material_fields": material_fields,
        "material_custody_sha256": _stable_hash(material_fields),
    }
    mutated["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(mutated)

    with pytest.raises(ValueError, match="missing material product-claim custody"):
        _transaction(tmp_path, authority=mutated)


@pytest.mark.parametrize(
    ("prompt", "fallback_title"),
    (
        (
            "Build an urban pavement emergency repair workspace where public works staff complete path for the "
            "whole product from hazard report through verified street reopening.",
            "Urban Pavement Emergency Repair Workspace",
        ),
        (
            "Build a thrift consignment payout workspace where consignment managers complete path for the whole "
            "product from item sale through approved seller payout.",
            "Thrift Consignment Payout Workspace",
        ),
    ),
)
def test_prompt_only_materialization_preserves_concrete_first_path_claim_custody(
    tmp_path: Path,
    prompt: str,
    fallback_title: str,
) -> None:
    intent = materialize_prompt_confirmed_intent(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=fallback_title,
    )

    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]

    require_product_intent_authority(authority)
    first_path = authority["material_fields"]["first_path"]
    assert first_path["custody_state"] == "accepted_fact"
    assert first_path["product_claim_span_ids"] == ["first_path:1"]


def test_prompt_materialization_persists_operational_constraints_through_preview_round_trip(
    tmp_path: Path,
) -> None:
    prompt = (
        "Build a berth turnaround control workspace where a terminal coordinator opens the morning vessel call "
        "at Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a signed "
        "handoff receipt."
    )

    intent = materialize_prompt_confirmed_intent(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Berth Turnaround Control",
    )
    path = tmp_path / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    persisted = load_confirmed_intent_record(path, prompt=prompt, fallback_title="Berth Turnaround Control")
    markdown = path.read_text(encoding="utf-8")

    assert "Pier 7" in intent["operational_constraints"]
    assert "Pier 7" in persisted.product_facts["operational_constraints"]
    assert "## Operational constraints\n- Pier 7" in markdown
    assert markdown.index("## Operational constraints") < markdown.index("## Human actors")


def test_product_intent_preview_lists_operational_constraints_before_human_actors() -> None:
    preview = render_product_intent_preview(
        {
            "title": "Berth Turnaround Control",
            "first_path": "A berth planner reviews one vessel call and sees the handoff receipt.",
            "operational_constraints": ["Pier 7"],
            "human_actors": ["Berth planner"],
        }
    )

    assert "## Operational constraints\n- Pier 7" in preview
    assert preview.index("## Operational constraints") < preview.index("## Human actors")


def test_prompt_intent_hypothesis_stages_typed_candidate_without_markdown_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        greenfield_prompt_intent_materialization,
        "parse_confirmed_intent_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("Markdown parsing is forbidden")),
    )
    intent = materialize_prompt_intent_hypothesis(
        prompt=(
            "Build a lab evidence review workspace where research coordinators record submitted sample context, "
            "route an evidence reviewer, resolve custody gaps, and see a release-readiness decision with proof."
        ),
        repo_root=tmp_path,
        fallback_title="Lab Evidence Review Workspace",
    )

    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    require_product_intent_authority(authority)
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.md").is_file()
    assert authority["source_format"] == "operator_prompt"
    assert authority["markdown_source_path"].endswith("candidate-evidence.md")


@pytest.mark.parametrize(
    "prompt",
    (
        "Create assay review.",
        "Build a review workspace.",
        "Create a booking workspace for repairs and scheduling.",
        "Create a tool for extension publishers to use for release notes.",
        "Create a cell therapy proposal with several possible operating paths.",
        "An AI agent can assemble release notes from approved changelog fragments.",
        "An AI assistant can assemble release notes from approved changelog fragments.",
        "An AI-powered assistant can assemble release notes from approved changelog fragments.",
        "An artificial intelligence assistant can assemble release notes from approved changelog fragments.",
        "An autonomous agent can assemble release notes from approved changelog fragments.",
        "An LLM assistant can assemble release notes from approved changelog fragments.",
        "A workflow assistant can assemble release notes from approved changelog fragments.",
        "A coordinator bot can assemble release notes from approved changelog fragments.",
    ),
)
def test_thin_prompt_asks_one_first_path_question_without_staging_artifacts(tmp_path: Path, prompt: str) -> None:
    with pytest.raises(ValueError, match="first complete task the product should help a person finish"):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title=(
                "Assay Review"
                if "assay" in prompt
                else "Repair Booking Workspace"
                if "booking" in prompt
                else "Review Workspace"
            ),
        )

    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


@pytest.mark.parametrize(
    ("prompt", "fallback_title", "first_path_term"),
    (
        (
            "Draft a greenfield proposal for a city zoning permit review app.",
            "City Zoning Permit Review App",
            "city zoning permit review",
        ),
        (
            "Draft a greenfield proposal for a food safety recall traceability system.",
            "Food Safety Recall Traceability System",
            "food safety recall traceability",
        ),
        (
            "Draft a greenfield proposal for a quantum chemistry catalyst screening platform.",
            "Quantum Chemistry Catalyst Screening Platform",
            "quantum chemistry catalyst screening",
        ),
    ),
)
def test_domain_anchored_title_compiles_with_a_visible_preconfirm_assumption(
    tmp_path: Path,
    prompt: str,
    fallback_title: str,
    first_path_term: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=fallback_title,
    )

    assert "initial first-path hypothesis" in " ".join(intent["assumptions"])
    assert first_path_term in intent["first_path"].casefold()
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.md").is_file()


@pytest.mark.parametrize(
    "prompt",
    (
        (
            "Create a tool for extension publishers to assemble release notes from approved changelog fragments, "
            "breaking-change notices, and compatibility windows."
        ),
        (
            "Extension publishers assemble release notes from approved changelog fragments and see a final "
            "release note package."
        ),
    ),
)
def test_explicit_single_step_actor_action_compiles_without_a_clarification(tmp_path: Path, prompt: str) -> None:

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Release Notes Workspace",
    )

    assert "extension publishers" in str(intent["first_path"]).casefold()
    assert "assemble release notes" in str(intent["first_path"]).casefold()
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.md").is_file()


@pytest.mark.parametrize(
    "prompt",
    (
        "A machine learning engineer can assemble release notes from approved changelog fragments.",
        "An AI research assistant can assemble release notes from approved changelog fragments.",
    ),
)
def test_human_technical_roles_do_not_trigger_nonhuman_actor_clarification(tmp_path: Path, prompt: str) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Release Notes Workspace",
    )

    assert "assemble release notes" in str(intent["first_path"]).casefold()
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.md").is_file()


def test_structured_edit_supplies_a_missing_first_path_without_a_second_question(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a learner choice practice journal.",
        repo_root=tmp_path,
        fallback_title="Learner Choice Practice Journal",
        edit_evidence=(
            "## First complete path\n"
            "A learner chooses one scenario, records a reflection, and sees a concise progress recap."
        ),
    )

    assert "learner" in intent["first_path"].casefold()
    assert "progress recap" in intent["first_path"].casefold()


def test_structured_edit_resolves_a_one_step_prompt_before_staging(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt="Create a radiology review product where a reviewer verifies the visible case status.",
        repo_root=tmp_path,
        fallback_title="Radiology Review Product",
        edit_evidence=(
            "## First complete path\n"
            "A reviewer opens one case, records a disposition, and sees the visible case status with its evidence."
        ),
    )

    assert "records a disposition" in intent["first_path"].casefold()
    assert "visible case status" in intent["first_path"].casefold()


def test_edit_rebuilds_an_unusable_prompt_path_from_the_accepted_first_path(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt="Create a tool for extension publishers to use for release notes.",
        repo_root=tmp_path,
        fallback_title="Release Notes Workspace",
        edit_evidence=(
            "## First complete path\n"
            "Extension publishers assemble approved changelog fragments into release notes and see a review-ready package."
        ),
    )

    rendered = render_product_intent_preview(intent).casefold()

    assert "assemble approved changelog fragments" in str(intent["prompt"]).casefold()
    assert "use for release notes" not in rendered
    assert "a review-ready package workspace" not in rendered
    assert "release notes workspace" in str(intent["product_story"]).casefold()
    assert "release notes workspace" in str(intent["product_view"]).casefold()
    assert all("release notes" in row.casefold() for row in intent["internal_systems"])
    assert any("extension publishers" in row.casefold() for row in intent["human_actors"])
    assert any("review-ready package" in row.casefold() for row in intent["success_metrics"])
    assert "review-ready package" in rendered


def test_edit_rebuilds_all_title_dependent_facts_from_the_accepted_title(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt="Create a tool for extension publishers to use for release notes.",
        repo_root=tmp_path,
        fallback_title="Release Notes Workspace",
        edit_evidence=(
            "## Title\nRelease Brief Builder\n\n## First complete path\n"
            "Extension publishers assemble approved changelog fragments into release notes and see a review-ready package."
        ),
    )

    rendered = render_product_intent_preview(intent).casefold()

    assert intent["title"] == "Release Brief Builder"
    assert "release brief builder" in str(intent["product_story"]).casefold()
    assert "release brief builder" in str(intent["product_view"]).casefold()
    assert all("release brief builder" in row.casefold() for row in intent["internal_systems"])
    assert "release notes workspace" not in rendered


def test_edit_preserves_an_accepted_release_boundary_without_leaking_exclusions(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=(
            "Create a tool for extension publishers to use for release notes. The first release boundary is one "
            "workspace per extension, a review queue, and an exportable release brief while marketplace publishing "
            "and telemetry are out of scope."
        ),
        repo_root=tmp_path,
        fallback_title="Release Notes Workspace",
        edit_evidence=(
            "## First complete path\n"
            "Extension publishers assemble approved changelog fragments into release notes and see a review-ready package."
        ),
    )

    rendered = render_product_intent_preview(intent).casefold()

    assert "review queue" in str(intent["proof_boundary"]).casefold()
    assert "marketplace publishing" not in str(intent["proof_boundary"]).casefold()
    assert "telemetry" not in str(intent["proof_boundary"]).casefold()
    assert "use for release notes" not in rendered
    assert "a review-ready package workspace" not in rendered


@pytest.mark.parametrize(
    ("prompt", "fallback_title"),
    (
        (
            "Create a repair booking workspace where residents select an appointment window, coordinators confirm "
            "the appointment, and the appointment is approved.",
            "Repair Booking Workspace",
        ),
        (
            "Create a release review workspace where reviewers collect evidence, resolve blockers, and approve the release.",
            "Release Review Workspace",
        ),
    ),
)
def test_concrete_multistep_prompt_compiles_without_a_keyword_specific_outcome(
    tmp_path: Path,
    prompt: str,
    fallback_title: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=fallback_title,
    )

    assert intent["first_path"]
    assert (tmp_path / ".odylith/runtime/greenfield/candidate-intent.md").is_file()


def test_anaphoric_headed_actor_edit_preserves_the_prompt_first_path(tmp_path: Path) -> None:
    prompt = (
        "Build a flood shelter intake workspace where city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Flood Shelter Intake Workspace",
        edit_evidence="## First complete path\nShelter coordinators should complete it.",
    )

    assert "shelter coordinators" in intent["first_path"].casefold()
    assert "placement readiness" in intent["first_path"].casefold()


def test_edit_evidence_rebuilds_typed_candidate_with_separate_raw_custody(tmp_path: Path) -> None:
    prompt = (
        "Build a flood shelter intake workspace where city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )
    initial = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Flood Shelter Intake Workspace",
    )
    edited = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Flood Shelter Intake Workspace",
        edit_evidence=(
            "EDIT\n\n## First complete path\n"
            "A shelter coordinator registers a displaced household, records accessibility needs, matches an available "
            "bed, obtains consent, and sees a confirmed placement receipt with the household's readiness status."
        ),
    )

    initial_authority = initial[PRODUCT_INTENT_AUTHORITY_KEY]
    edited_authority = edited[PRODUCT_INTENT_AUTHORITY_KEY]
    require_product_intent_authority(edited_authority)
    assert initial_authority[PRODUCT_FACTS_HASH_KEY] != edited_authority[PRODUCT_FACTS_HASH_KEY]
    assert "shelter coordinator" in edited["first_path"].casefold()
    assert edited_authority["source_format"] == "operator_prompt_with_edit_evidence"
    assert (tmp_path / ".odylith/runtime/greenfield/operator-prompt.txt").is_file()
    assert (tmp_path / ".odylith/runtime/greenfield/edit-evidence.md").is_file()
    evidence = (tmp_path / ".odylith/runtime/greenfield/candidate-evidence.md").read_text(encoding="utf-8")
    assert "Operator prompt evidence" in evidence
    assert "Operator edit evidence" in evidence
    preview = render_product_intent_preview(edited)
    assert "Product Intent Preview" in preview
    assert "shelter coordinator" in preview.casefold()


def test_rich_edit_rebuilds_prompt_derived_product_projections(tmp_path: Path) -> None:
    edited = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a learner choice practice journal.",
        repo_root=tmp_path,
        fallback_title="Learner Choice Practice Journal",
        edit_evidence=(
            "# Choice Practice Journal\n\n"
            "## Product story\n"
            "The journal gives a learner one short scenario and gives a parent a concise recap.\n\n"
            "## State object\n"
            "A learner practice record tracks the selected scenario, choice, reflection, recap status, and privacy boundary.\n\n"
            "## First complete path\n"
            "A parent creates an account, adds a learner profile, and selects one scenario. The learner makes a choice, "
            "sees a short reflection, and the parent opens the recap.\n\n"
            "## Human actors\n"
            "- Parent: creates the account and reviews the recap.\n"
            "- Learner: makes the scenario choice and sees the reflection.\n\n"
            "## Proof boundary\n"
            "Release 0.0.1 succeeds when the learner completes one scenario and the parent can review the recap."
        ),
    )

    derived_text = " ".join(
        str(edited.get(field) or "")
        for field in ("customer", "problem", "opportunity", "product_view", "success_metrics")
    ).casefold()

    assert "representative user" not in derived_text
    assert "parent" in str(edited["product_view"]).casefold()


def test_plain_language_edit_rebuilds_the_typed_candidate_without_a_schema_prompt(tmp_path: Path) -> None:
    prompt = (
        "Build a flood shelter intake workspace where city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )

    edited = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Flood Shelter Intake Workspace",
        edit_evidence="EDIT\nMake shelter coordinators the people who complete the first placement handoff.",
    )

    assert edited["first_path"] == (
        "Shelter coordinators can complete the first placement handoff, then register displaced residents, match "
        "household needs to shelter capacity; then preserve consent evidence; then publish a daily placement readiness result."
    )
    assert edited["human_actors"] == [
        "Shelter coordinators: can complete the first placement handoff and review the visible result"
    ]
    preview = render_product_intent_preview(edited).casefold()
    assert "shelter coordinators" in preview
    assert "city staff" not in preview


def test_sentence_form_first_path_actor_correction_rebuilds_without_schema_terms(tmp_path: Path) -> None:
    prompt = (
        "Build a flood shelter intake workspace where city staff register displaced residents, match household needs "
        "to shelter capacity, preserve consent evidence, and publish a daily placement readiness result."
    )

    edited = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Flood Shelter Intake Workspace",
        edit_evidence="EDIT\nThe first path should be completed by shelter coordinators rather than city staff.",
    )

    assert edited["first_path"].startswith("Shelter coordinators can register displaced residents")
    assert edited["human_actors"] == [
        "Shelter coordinators: can complete the first path and review the visible result"
    ]
    assert "city staff" not in render_product_intent_preview(edited).casefold()


def test_device_description_compiles_a_usable_owner_path_without_a_product_intent_failure(tmp_path: Path) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt="Draft a greenfield proposal for a plant-care irrigation device that waters and monitors houseplants.",
        repo_root=tmp_path,
        fallback_title="Plant-care Irrigation Device Workspace",
    )

    assert intent["first_path"] == (
        "A device owner can configure one plant-care irrigation device, review the plant status, and see current "
        "watering status and sensor status."
    )
    assert "device owner" in " ".join(intent["human_actors"]).casefold()
    assert "device that waters" not in intent["product_story"].casefold()


@pytest.mark.parametrize(
    "text",
    (
        "Field inspectors record pavement findings, attach photos, route traffic engineer review, and publish an approval packet with proof.",
        "Product Intent Confirmation needed\n\nHost reasoning task\n\nVisible format contract\n\nOriginal user intent\nField inspectors record pavement findings, attach photos, route traffic engineer review, and publish an approval packet with proof.",
    ),
)
def test_confirmed_intent_file_rejects_raw_prompt_and_host_guidance(tmp_path: Path, text: str) -> None:
    path = tmp_path / "intent.md"
    path.write_text(text, encoding="utf-8")
    args = Namespace(
        intent_file=str(path),
        prompt="Field inspectors record pavement findings, attach photos, route traffic engineer review, and publish an approval packet with proof.",
    )

    with pytest.raises(ValueError, match="cannot treat"):
        load_confirmed_intent_args(args, repo_root=tmp_path)


def test_confirmed_intent_file_accepts_rich_unheaded_confirmation_as_markdown(tmp_path: Path) -> None:
    path = tmp_path / "intent.md"
    path.write_text(
        """# Neighborhood Repair Booking

Residents need a simple way to get small home repairs scheduled without repeated calls or unclear availability.

The central record keeps a repair request, contact details, category, appointment windows, reviewer decision, and confirmation status.

A resident describes a repair, selects appointment windows, and submits the request. A repair coordinator reviews the same request and the resident sees a scheduling decision with next steps.

Release 0.0.1 succeeds when the resident can submit one request, see the decision, and the coordinator can reopen the same evidence.
""",
        encoding="utf-8",
    )
    args = Namespace(intent_file=str(path), prompt="Create a neighborhood repair booking workspace.")

    intent = load_confirmed_intent_args(args, repo_root=tmp_path)

    assert intent[PRODUCT_INTENT_AUTHORITY_KEY]["source_format"] == "markdown"
    assert intent["first_path"].startswith("A resident describes a repair")


@pytest.mark.parametrize("damage", ("missing_sidecar", "invalid_sidecar", "source_drift", "envelope_drift"))
def test_product_create_transaction_intent_authority_uses_sealed_snapshot(
    tmp_path: Path,
    damage: str,
) -> None:
    path, _facts, authority = _recorded_authority(tmp_path)
    transaction = _transaction(tmp_path, authority=authority)
    structured_path = path.with_suffix(".json")
    if damage == "missing_sidecar":
        structured_path.unlink()
    elif damage == "invalid_sidecar":
        structured_path.write_text("{not-json", encoding="utf-8")
    elif damage == "source_drift":
        path.write_text(_CONFIRMED_INTENT + "\n## Product story\nDrifted after compile.\n", encoding="utf-8")
    elif damage == "envelope_drift":
        payload = json.loads(structured_path.read_text(encoding="utf-8"))
        payload["decision_record"] = {
            **dict(payload["decision_record"]),
            "fact_authority": "markdown_projection",
        }
        structured_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    require_product_create_transaction_intent_authority(transaction, repo_root=tmp_path)


def test_product_create_transaction_hash_rejects_intent_authority_mutation(tmp_path: Path) -> None:
    transaction = _transaction(tmp_path)
    mutated = replace(
        transaction,
        intent_authority={**dict(transaction.intent_authority), PRODUCT_FACTS_HASH_KEY: "forged"},
    )

    assert not mutated.verified
    with pytest.raises(ValueError, match="hash mismatch"):
        require_product_create_transaction_verified(mutated)


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
