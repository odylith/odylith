"""Contract tests for typed structured first-path composition."""

from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import (
    structured_prompt_facts,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import (
    compile_structured_first_path,
)
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import compile_temporal_first_path
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import path_start_action
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import structured_actor_aliases
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import structured_actor_subject
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import named_actor_phrase
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import passive_event_parts
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import path_entry_action


def test_typed_start_action_and_output_compile_as_distinct_events() -> None:
    contract = compile_structured_first_path(
        actor="archive clerks",
        actor_is_human=True,
        path_value="start with intake review",
        action_value="reconcile intake packets",
        output_value="an intake receipt",
    )
    path = contract.text

    model = first_path_model(path)

    assert contract.complete
    assert contract.primary_actor_action == "complete intake review"
    assert contract.primary_state_action == "reconcile intake packets"
    assert contract.actor_subject == "Archive clerks"
    assert contract.actor_label == "Archive clerks"
    assert len(model.steps) == 3
    assert model.steps[0].casefold() == "archive clerks can complete intake review"
    assert "reconcile intake packets" in model.steps[1].casefold()
    assert "intake receipt" in model.steps[2].casefold()


def test_output_already_generated_by_a_coordinated_action_is_not_rendered_twice() -> None:
    contract = compile_structured_first_path(
        actor="dispatch coordinators",
        actor_is_human=True,
        path_value="",
        action_value="monitor samples, verify seal states, and generate a packet",
        output_value="a packet in AtlasBay",
    )

    assert contract.text.casefold().count("packet") == 1
    assert "finally" not in contract.text.casefold()


def test_temporal_path_does_not_repeat_an_output_already_issued_by_an_actor() -> None:
    contract = compile_temporal_first_path(
        events=(("intake clerks", "submit a packet"), ("supervisors", "issue a receipt")),
        output_value="a receipt",
    )

    assert contract.text.casefold().count("receipt") == 1
    assert "the product shows a receipt" not in contract.text.casefold()


def test_complete_structured_contract_outranks_obligation_prose() -> None:
    prompt = (
        "Domain label: intake reconciliation. Create a product for archive clerks to reconcile intake packets "
        "in VaultLine. It must preserve notes, generate an intake receipt, and track packet states. "
        "The first path is fixed: start with intake review."
    )

    facts = structured_prompt_facts(prompt)
    source = prompt_intent_source(prompt)

    assert not facts.path_needs_enrichment
    assert source.first_path == facts.first_path
    assert "archive clerks" in source.first_path.casefold()
    assert "reconcile intake packets" in source.first_path.casefold()
    assert "complete intake review" in source.first_path.casefold()
    assert "intake receipt" in source.first_path.casefold()
    assert "preserve notes" not in source.first_path.casefold()


def test_complete_typed_contract_outranks_a_shorter_need_clause() -> None:
    prompt = (
        "Domain label: textile calibration. Create a product for calibration technicians who need to calibrate "
        "woven batches in GaugeDesk. The product must generate a signed spool ledger. "
        "The first path is fixed: the first calibration path is the signed batch receipt."
    )

    source = prompt_intent_source(prompt)

    assert source.first_path == (
        "Calibration technicians can calibrate woven batches, receive the signed batch receipt, "
        "and receive a signed spool ledger"
    )


def test_actor_owned_enriched_path_outranks_the_compact_typed_contract() -> None:
    prompt = (
        "Niko, a library host, reserves a quiet-room slot in the Lantern Desk. Niko chooses a room and "
        "marks the slot held; the visitor-facing board then shows the room and time. Room availability is "
        "read from the Hall Calendar. Do not promise a reservation until the calendar returns availability."
    )

    source = prompt_intent_source(prompt)

    assert "marks the slot held" in source.first_path
    assert "board then shows the room and time" in source.first_path
    assert "Room availability is read" not in source.first_path


def test_complete_contract_absorbs_only_rows_owned_by_the_typed_actor() -> None:
    contract = compile_structured_first_path(
        actor="Niko, a library host",
        actor_is_human=True,
        path_value="reserves a quiet-room slot in the Lantern Desk",
        action_value="",
        output_value="the room and time",
        actor_owned_action=True,
    )

    merged = contract.actor_owned_path_from_rows(
        (
            "Niko reserves a quiet-room slot in the Lantern Desk",
            "Niko marks the slot held; the visitor-facing board then shows the room and time",
            "It must preserve calendar notes",
        )
    )

    assert "marks the slot held" in merged
    assert "shows the room and time" in merged
    assert "preserve calendar notes" not in merged


def test_output_contract_preserves_a_named_actor_to_product_handoff() -> None:
    contract = compile_structured_first_path(
        actor="",
        actor_is_human=False,
        path_value="",
        action_value="",
        output_value="the placement",
    )

    merged = contract.actor_handoff_path_from_rows(
        (
            "Ivo starts by entering a vessel tag",
            "On a match, the product records the berth as occupied and the berth map displays the placement",
            "The release must retain source notes for seven years",
        ),
        actor="dock attendant Ivo",
    )

    assert merged.startswith("Ivo starts by entering a vessel tag")
    assert "berth map displays the placement" in merged
    assert "retain source notes" not in merged


def test_handoff_does_not_consume_required_path_control_after_the_visible_outcome() -> None:
    contract = compile_structured_first_path(
        actor="Mara, an archive clerk",
        actor_is_human=True,
        path_value="starts with manifest review",
        action_value="stages accession crates in VaultLedger",
        output_value="an intake receipt",
        actor_owned_action=True,
    )

    merged = contract.actor_handoff_path_from_rows(
        (
            "An archive clerk named Mara stages accession crates in VaultLedger",
            "The product generates an intake receipt",
            "The first path starts with manifest review",
        ),
        actor="Mara, an archive clerk",
    )

    assert merged == ""


def test_inferred_intermediate_output_does_not_hide_a_later_visible_result() -> None:
    contract = compile_structured_first_path(
        actor="Oren, a prop-room keeper",
        actor_is_human=True,
        path_value="uses Cue Crate to receive a returned prop",
        action_value="",
        output_value="",
        actor_owned_action=True,
    )

    merged = contract.actor_handoff_path_from_rows(
        (
            "Oren, the prop-room keeper, uses Cue Crate to receive a returned prop",
            "The keeper scans the prop label, selects sound or repair-needed, and gets a shelf-return card",
        ),
        actor="Oren, a prop-room keeper",
    )

    assert "shelf-return card" in merged


def test_named_actor_alias_does_not_require_a_domain_role_dictionary() -> None:
    assert structured_actor_aliases("dock attendant Ivo") == (
        "dock attendant ivo",
        "ivo",
        "dock attendant",
        "attendant",
    )


def test_title_cased_coordinated_roles_are_not_treated_as_a_role_plus_person_name() -> None:
    assert structured_actor_subject("Refuge Wardens and Rescue Dispatchers") == (
        "Refuge Wardens and Rescue Dispatchers"
    )
    assert structured_actor_aliases("Refuge Wardens and Rescue Dispatchers") == (
        "refuge wardens and rescue dispatchers",
        "refuge wardens",
        "rescue dispatchers",
    )


def test_named_actor_role_alias_preserves_anaphoric_owned_rows() -> None:
    contract = compile_structured_first_path(
        actor="Oren, a prop-room keeper",
        actor_is_human=True,
        path_value="uses Cue Crate to receive a returned prop",
        action_value="",
        output_value="a returned prop",
        actor_owned_action=True,
    )

    merged = contract.actor_owned_path_from_rows(
        (
            "Oren uses Cue Crate to receive a returned prop",
            "The keeper scans the prop label, selects sound or repair-needed, and gets a shelf-return card",
        )
    )

    assert "gets a shelf-return card" in merged


def test_named_actor_and_entry_action_use_structural_grammar() -> None:
    assert named_actor_phrase(name="Ivo", role="dock attendant") == "Ivo, a dock attendant"
    assert path_entry_action("starts by entering a vessel tag") == "enter a vessel tag"


def test_actor_owned_entry_action_is_normalized_before_contract_ranking() -> None:
    contract = compile_structured_first_path(
        actor="Mara, an archive clerk",
        actor_is_human=True,
        path_value="",
        action_value="starts by staging accession crates in VaultLedger",
        output_value="an intake receipt",
        actor_owned_action=True,
    )

    assert contract.primary_actor_action == "stage accession crates in VaultLedger"
    assert contract.text == (
        "Mara, an archive clerk, can stage accession crates in VaultLedger. "
        "Mara can receive an intake receipt"
    )
    assert "can start by" not in contract.text


def test_passive_event_parts_preserve_the_affected_object_and_control_context() -> None:
    assert passive_event_parts(
        "A restoration bulletin is published after a supervisor approves the reading"
    ) == (
        "A restoration bulletin",
        "publish a restoration bulletin after a supervisor approves the reading",
    )


def test_structurally_complete_automated_path_still_requires_human_owner(tmp_path: Path) -> None:
    prompt = (
        "Create a product for the batch scheduler to reconcile settlement files in LedgerForge. "
        "It must preserve audit notes, generate a variance receipt, and track settlement states. "
        "The first path is fixed: start with intake review."
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Settlement Reconciliation",
        )

    assert error.value.required_fields == ("human_actors", "first_path")
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_negative_output_scope_never_becomes_a_positive_event() -> None:
    contract = compile_structured_first_path(
        actor="review coordinators",
        actor_is_human=True,
        path_value="begins with source review",
        action_value="record a disposition",
        output_value="must not generate a public receipt",
    )
    path = contract.text

    assert "record a disposition" in path.casefold()
    assert "public receipt" not in path.casefold()
    assert not contract.complete


def test_typed_path_lists_remain_events_instead_of_stringified_data() -> None:
    contract = compile_structured_first_path(
        actor="intake clerks",
        actor_is_human=True,
        path_value=["record a donated lot", "review its condition"],
        action_value="",
        output_value="a custody receipt",
    )
    path = contract.text

    model = first_path_model(path)

    assert len(model.steps) == 3
    assert "[" not in path and "]" not in path
    assert "record a donated lot" in path.casefold()
    assert "review its condition" in path.casefold()
    assert "custody receipt" in path.casefold()


def test_explicit_start_discards_trailing_path_control_sentence() -> None:
    assert path_start_action(
        "the first path begins with condition-note intake. The first path is fixed."
    ) == "complete condition-note intake"


def test_malformed_explicit_start_cannot_claim_typed_completeness() -> None:
    contract = compile_structured_first_path(
        actor="archive clerks",
        actor_is_human=True,
        path_value="starts with",
        action_value="reconcile intake packets",
        output_value="an intake receipt",
    )

    assert not contract.complete
    assert contract.invalid_reasons == ("explicit path start has no action",)
    assert "start with" not in contract.text.casefold()


def test_malformed_start_asks_one_plain_material_question(tmp_path: Path) -> None:
    prompt = (
        "Create a product for archive clerks to reconcile intake packets in VaultLine. "
        "Output: an intake receipt. First path: starts with."
    )

    with pytest.raises(GreenfieldClarificationRequired) as error:
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="Intake Reconciliation",
        )

    assert str(error.value) == "What should the user complete first, and what result should they see?"
    assert error.value.required_fields == ("first_path",)
    assert not (tmp_path / ".odylith/runtime/greenfield").exists()


def test_mixed_output_scope_keeps_only_the_positive_clause() -> None:
    contract = compile_structured_first_path(
        actor="inspection coordinators",
        actor_is_human=True,
        path_value="review a shipment",
        action_value="record an inspection decision",
        output_value="must not generate a customs release; generate an inspection notice",
    )

    assert contract.complete
    assert "customs release" not in contract.text.casefold()
    assert "inspection notice" in contract.text.casefold()
    assert "receive must not" not in contract.text.casefold()


def test_article_variation_deduplicates_an_action_owned_output() -> None:
    contract = compile_structured_first_path(
        actor="intake clerks",
        actor_is_human=True,
        path_value="review an intake packet",
        action_value="generate intake receipt",
        output_value="an intake receipt",
    )

    assert contract.complete
    assert contract.text.casefold().count("intake receipt") == 1
    assert len([event for event in contract.events if event.kind == "output"]) == 1


def test_structured_objects_are_rejected_instead_of_serialized() -> None:
    contract = compile_structured_first_path(
        actor="review coordinators",
        actor_is_human=True,
        path_value={"actor": "review coordinators", "action": "review a request"},
        action_value="record a decision",
        output_value="a decision receipt",
    )

    assert not contract.complete
    assert "actor" not in contract.text.casefold()
    assert contract.invalid_reasons == ("structured field contains an object instead of text",)
