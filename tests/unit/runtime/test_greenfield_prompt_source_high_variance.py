from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import (
    intent_hypothesis_from_operator_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import evidence_anchor_phrases
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_is_present
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_kind
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_phrases
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraints_after_first_path_edit
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import prohibited_product_phrases
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import drop_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_operator_review_lens_step
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import first_release_boundary_requirements
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import first_release_boundary_summary
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import operator_review_lens_obligations
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import (
    proof_boundary_with_first_release_requirements,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import select_visible_result_candidate
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_sections import confirmed_intent_sections
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import (
    explicit_actor_has_human_grammar,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import _explicit_edit_overrides
from odylith.runtime.project_intelligence.intent_confirmation import _fallback_confirmation_markdown


ROOT = Path(__file__).resolve().parents[3]
PORT_OPERATIONS_PROMPT = json.loads(
    (ROOT / "tests/fixtures/greenfield-volume/logistics-infrastructure.v1.json").read_text(encoding="utf-8")
)["cases"][0]["prompt"]


def _guidance_envelope(prompt: str) -> str:
    return f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
- Render the visible confirmation as sectioned Markdown in this order.

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, compile the ProductCreateTransaction, then commit the matching hash.
Compile transaction: odylith greenfield compile-transaction --repo-root . --prompt '{prompt}' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1
Commit transaction after hash confirmation: odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm
"""


def test_first_release_boundary_requirements_keep_in_scope_capabilities() -> None:
    prompt = (
        "The first release boundary is one workspace per extension, a review queue, and an exportable release brief; "
        "marketplace publishing, telemetry, and code scanning are outside this release."
    )

    assert first_release_boundary_requirements(prompt) == (
        "one workspace per extension",
        "a review queue",
        "an exportable release brief",
    )


def test_where_clause_keeps_action_words_out_of_the_actor() -> None:
    prompt = (
        "Draft a greenfield proposal for a lab app where researchers configure and launch an E91 quantum "
        "communication run on real hardware, observe live coincidence counts, Bell inequality checks, CHSH, "
        "QBER, and established key bits, then compare the saved run against prior results."
    )
    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.actor == "researchers"
    assert source.first_path.casefold().startswith("researchers configure and launch")
    assert "researchers configure and can" not in source.first_path.casefold()
    assert intent["title"] == "E91 Quantum Communication Run Workspace"
    assert intent["state_object"] == "The primary state object is an E91 quantum communication run."


def test_first_release_boundary_requirements_drop_natural_language_exclusions() -> None:
    prompt = (
        "The first release boundary is one workspace per extension, a review queue, and an exportable release brief "
        "while marketplace publishing and telemetry are out of scope."
    )

    assert first_release_boundary_requirements(prompt) == (
        "one workspace per extension",
        "a review queue",
        "an exportable release brief",
    )
    assert proof_boundary_with_first_release_requirements("Release proof.", prompt) == (
        "Release proof. The first release includes one workspace per extension, a review queue, and an "
        "exportable release brief."
    )
    assert first_release_boundary_summary(prompt) == (
        "The first release includes one workspace per extension, a review queue, and an exportable release brief."
    )


def test_first_release_boundary_requirements_drop_active_exclusions() -> None:
    prefixes = (
        "and excludes marketplace publishing and telemetry",
        "but does not include marketplace publishing and telemetry",
        "with marketplace publishing and telemetry excluded",
    )

    for suffix in prefixes:
        prompt = (
            "The first release boundary is one workspace per extension, a review queue, and an exportable release "
            f"brief {suffix}."
        )
        assert first_release_boundary_requirements(prompt) == (
            "one workspace per extension",
            "a review queue",
            "an exportable release brief",
        )


def test_first_release_requirements_accept_plain_includes_framing() -> None:
    prompt = (
        "The first release includes one workspace per extension, a review queue, and an exportable release brief "
        "while marketplace publishing and telemetry are out of scope."
    )

    assert first_release_boundary_requirements(prompt) == (
        "one workspace per extension",
        "a review queue",
        "an exportable release brief",
    )


def test_first_release_requirements_accept_colon_scope_framing() -> None:
    prompt = (
        "First release: one workspace per extension, a review queue, and an exportable release brief; "
        "marketplace publishing and telemetry are out of scope."
    )

    assert first_release_boundary_requirements(prompt) == (
        "one workspace per extension",
        "a review queue",
        "an exportable release brief",
    )


def test_prompt_source_keeps_domain_expert_modal_clause_out_of_actor_label() -> None:
    prompt = (
        "Create a greenfield proposal for wearable arrhythmia episode review. Focus on a governed workflow "
        "where the cardiac monitoring specialist turns an ambiguous arrhythmia episode into a review-ready "
        "record using ECG strip evidence, motion artifact flags, medication context, clinician review notes, "
        "explicit expert review, auditable decision ledger, and a final episode classification recommendation. "
        "The request mentions review, approval, and release in the same sentence, so the workflow must keep those "
        "states separate. A domain expert must see the evidence vocabulary preserved accurately with no unsafe "
        "overclaiming. The post-confirm create must finish all project and governance artifacts under the "
        "standard budget."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert "Domain Expert:" not in "\n".join(intent["human_actors"])
    assert any(
        "Domain Expert review must verify the evidence vocabulary preserved accurately without unsafe overclaiming"
        in row
        for row in [intent["proof_boundary"], *intent["assumptions"]]
    )
    assert "Domain Expert Must" not in rendered
    assert "must uses" not in rendered.casefold()
    assert "modal/base-form grammar drift" not in "\n".join(greenfield_quality_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_semantic_slop_gate_rejects_word_sense_metadata_as_visible_result() -> None:
    issues = generated_semantic_slop_issues(
        {
            "product_view": "The computational biologist can reach an action and as a governed object.",
            "release_note": "The reviewer can reach a noun and a governed object.",
            "registry_note": "The analyst can reach a verb and a governed object.",
            "source_note": "The request uses record both as an action and as a governed object.",
            "visible_object": "an action and as a governed object, so ownership must be explicit.",
        }
    )

    assert sum("word-sense metadata leaked as visible result" in issue for issue in issues) >= 5


def test_word_sense_metadata_does_not_reject_grammar_product_language() -> None:
    text = "The sentence treats record as a noun and verb in the lesson."
    request_framed_text = "The request says the lesson shows record as both a noun and a governed object in English grammar."
    descriptor_subject_text = (
        "The request says the record lesson shows record as both a noun and a governed object in English grammar."
    )
    custody_subject_text = (
        "The request says the ownership report shows record as both a noun and a governed object in English grammar."
    )
    mixed_request_framed_text = (
        "The request says the lesson shows record as both a noun and a governed object in English grammar, "
        "so ownership must be explicit."
    )

    assert not contains_word_sense_metadata_clause(text)
    assert generated_semantic_slop_issues({"lesson_copy": text}) == []
    assert not contains_word_sense_metadata_clause("The sentence treats record as both a noun and a governed object in the lesson.")
    assert not contains_word_sense_metadata_clause(request_framed_text)
    assert not contains_word_sense_metadata_clause(descriptor_subject_text)
    assert not contains_word_sense_metadata_clause(custody_subject_text)
    assert generated_semantic_slop_issues({"request_framed_lesson_copy": request_framed_text}) == []
    assert generated_semantic_slop_issues({"descriptor_subject_lesson_copy": descriptor_subject_text}) == []
    assert generated_semantic_slop_issues({"custody_subject_lesson_copy": custody_subject_text}) == []
    assert contains_word_sense_metadata_clause(mixed_request_framed_text)
    assert generated_semantic_slop_issues({"mixed_request_framed_copy": mixed_request_framed_text})
    assert (
        generated_semantic_slop_issues(
            {
                "lesson_copy": "The lesson explains noun and object ownership in English grammar.",
                "tutorial_copy": "The tutorial reviews a noun and a governed object in the sentence.",
            }
        )
        == []
    )


def test_visible_result_object_ignores_word_sense_metadata_tail() -> None:
    result = visible_result_object(
        "A final ranked perturbation interpretation The request uses record both as an action "
        "and as a governed object, so ownership must be explicit"
    )

    assert result == "A final ranked perturbation interpretation"


def test_visible_result_object_rejects_leading_word_sense_metadata() -> None:
    assert (
        visible_result_object("The request uses record both as an action and as a governed object, so ownership must be explicit")
        == ""
    )
    assert (
        visible_result_object("The request uses record as an action and as a governed object, so ownership must be explicit")
        == ""
    )
    assert visible_result_object("Record is both an action and a governed object, so ownership must be explicit") == ""
    assert (
        visible_result_object("The request uses record as both a verb and a governed object, so ownership must be explicit")
        == ""
    )
    assert (
        visible_result_object("The request uses record as both a noun and a governed object, so ownership must be explicit")
        == ""
    )
    assert (
        visible_result_object("The request says record is both a noun and a governed object, so ownership must be explicit")
        == ""
    )
    request_framed_result = visible_result_object(
        "The request says the lesson shows record as both a noun and a governed object in English grammar."
    )
    assert request_framed_result == ""
    short_prefix_result = visible_result_object(
        "A classroom-ready record. The request says the lesson shows record as both a noun and a governed object in "
        "English grammar."
    )
    assert short_prefix_result == "A classroom-ready record"
    assert visible_result_object("Record is both a verb and a governed object, so ownership must be explicit") == ""
    assert visible_result_object("Record is both a noun and a governed object, so ownership must be explicit") == ""
    assert visible_result_object("The visible result is The request uses record both as an action and as a governed object") == ""


def test_semantic_compiler_ignores_declared_word_sense_visible_result() -> None:
    candidate = select_visible_result_candidate(
        "Computational biologist reviews a final ranked perturbation interpretation",
        product_view="The visible result is The request uses record both as an action and as a governed object.",
    )

    assert candidate.source_kind != "intent.product_view.visible_result"
    assert candidate.text == "a final ranked perturbation interpretation"


def test_semantic_compiler_ignores_word_sense_proof_boundary_fallback() -> None:
    candidate = select_visible_result_candidate(
        "Computational biologist submits the study inputs",
        proof_boundary="The request uses record both as an action and as a governed object, so ownership must be explicit.",
        fallback="the promised user-visible result",
    )

    assert candidate.source_kind != "proof_boundary"
    assert "action and as" not in candidate.text


def test_prompt_source_rejects_synonym_word_sense_metadata_escape() -> None:
    _assert_prompt_word_sense_phrase_is_metadata(
        "The request uses record as both a verb and a governed object, so ownership must be explicit.",
        "verb and a governed object",
    )


def test_prompt_source_rejects_noun_object_word_sense_metadata_escape() -> None:
    _assert_prompt_word_sense_phrase_is_metadata(
        "The request uses record as both a noun and a governed object, so ownership must be explicit.",
        "noun and a governed object",
    )


def test_prompt_source_rejects_reporting_verb_word_sense_metadata_escape() -> None:
    _assert_prompt_word_sense_phrase_is_metadata(
        "The request says record is both a noun and a governed object, so ownership must be explicit.",
        "request says",
        leaked_phrase="noun and a governed object",
    )


def test_prompt_source_preserves_request_framed_grammar_product_content() -> None:
    prompt = (
        "Create a greenfield proposal for English grammar ambiguity lesson. Focus on a governed workflow where the "
        "teacher turns a confusing sentence analysis into a classroom-ready record using examples, answer keys, "
        "student misconceptions, grammar evidence, explicit review, and a final lesson explanation. The request says "
        "the lesson shows record as both a noun and a governed object in English grammar. A product manager must see "
        "the first complete path, actor value, non-goals, and success metrics. The post-confirm create must finish "
        "all project and governance artifacts under the standard budget."
    )

    source = prompt_intent_source(prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=source.title,
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    semantic_visible_result = proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()

    assert "the request says" not in source.first_path.casefold()
    assert "the request says" not in rendered
    assert "ownership must be explicit" not in source.first_path.casefold()
    assert "ownership must be explicit" not in rendered
    assert "english grammar" in rendered or "grammar ambiguity" in rendered
    assert "lesson" in rendered
    assert "noun and a governed object" not in semantic_visible_result
    assert "final lesson explanation" in semantic_visible_result or "classroom-ready record" in semantic_visible_result
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_preserves_request_framed_product_subjects_with_descriptor_terms() -> None:
    for subject in ("record lesson", "ownership report"):
        prompt = (
            "Create a greenfield proposal for English grammar ambiguity lesson. Focus on a governed workflow where the "
            "teacher turns a confusing sentence analysis into a classroom-ready record using examples, answer keys, "
            f"student misconceptions, grammar evidence, explicit review, and a final lesson explanation. The request says the "
            f"{subject} shows record as both a noun and a governed object in English grammar. A product manager must see "
            "the first complete path, actor value, non-goals, and success metrics. The post-confirm create must finish "
            "all project and governance artifacts under the standard budget."
        )

        source = prompt_intent_source(prompt)
        proposal = build_confirmed_greenfield_proposal(
            prompt=prompt,
            title=source.title,
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
        )
        rendered = json.dumps(proposal, sort_keys=True).casefold()
        semantic_visible_result = proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()

        assert "the request says" not in source.first_path.casefold()
        assert "the request says" not in rendered
        assert "ownership must be explicit" not in rendered
        assert not source.first_path.casefold().endswith(subject)
        assert "english grammar" in rendered or "grammar ambiguity" in rendered
        assert "noun and a governed object" not in semantic_visible_result
        assert "final lesson explanation" in semantic_visible_result
        assert greenfield_quality_issues(proposal) == []


def test_prompt_source_preserves_sparse_request_framed_product_subjects() -> None:
    for subject in ("record lesson", "ownership report"):
        prompt = (
            "Create a greenfield proposal for grammar lesson. The request says the "
            f"{subject} shows record as both a noun and a governed object in English grammar."
        )

        source = prompt_intent_source(prompt)
        proposal = build_confirmed_greenfield_proposal(
            prompt=prompt,
            title=source.title,
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
        )
        rendered = json.dumps(proposal, sort_keys=True).casefold()
        semantic_visible_result = proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()

        assert "the request says" not in source.first_path.casefold()
        assert "the request says" not in rendered
        assert subject in source.first_path.casefold() or subject in rendered
        assert "noun and a governed object" not in semantic_visible_result
        assert "governed object in english grammar" not in rendered
        assert greenfield_quality_issues(proposal) == []


def test_prompt_source_strips_request_framed_grammar_custody_tail() -> None:
    prompt = (
        "Create a greenfield proposal for English grammar ambiguity lesson. Focus on a governed workflow where the "
        "teacher turns a confusing sentence analysis into a classroom-ready record using examples, answer keys, "
        "student misconceptions, grammar evidence, explicit review, and a final lesson explanation. The request says "
        "the lesson shows record as both a noun and a governed object in English grammar, so ownership must be explicit. "
        "A product manager must see the first complete path, actor value, non-goals, and success metrics. The "
        "post-confirm create must finish all project and governance artifacts under the standard budget."
    )

    source = prompt_intent_source(prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=source.title,
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    semantic_visible_result = proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()

    assert "the request says" not in source.first_path.casefold()
    assert "the request says" not in rendered
    assert "ownership must be explicit" not in source.first_path.casefold()
    assert "ownership must be explicit" not in rendered
    assert "english grammar" in rendered or "grammar ambiguity" in rendered
    assert "noun and a governed object" not in semantic_visible_result
    assert "final lesson explanation" in semantic_visible_result or "classroom-ready record" in semantic_visible_result
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_does_not_promote_sparse_request_framed_grammar_as_visible_result() -> None:
    prompt = (
        "Create a greenfield proposal for grammar lesson. The request says the lesson shows record as both a noun "
        "and a governed object in English grammar, so ownership must be explicit."
    )

    source = prompt_intent_source(prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=source.title,
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    semantic_visible_result = proposal["semantic_model"]["first_path_contract"]["visible_result"].casefold()

    assert "the request says" not in source.first_path.casefold()
    assert "the request says" not in rendered
    assert "ownership must be explicit" not in source.first_path.casefold()
    assert "ownership must be explicit" not in rendered
    assert "noun and a governed object" not in semantic_visible_result
    assert "governed object in english grammar" not in rendered
    assert greenfield_quality_issues(proposal) == []


def _assert_prompt_word_sense_phrase_is_metadata(
    control_sentence: str,
    stub_phrase: str,
    *,
    leaked_phrase: str | None = None,
) -> None:
    leaked = leaked_phrase or stub_phrase
    prompt = (
        "Create a greenfield proposal for pathology slide discrepancy board. Focus on a governed workflow where the "
        "pathology quality lead turns an ambiguous slide discrepancy case into a review-ready record using stain "
        "quality metrics, scanner metadata, pathologist annotations, specimen custody, explicit expert review, "
        f"auditable decision ledger, and a final discrepancy resolution recommendation. {control_sentence} "
        "An engineer must see implementable prompts, data contracts, validations, and error states. The post-confirm "
        "create must finish all project and governance artifacts under the standard budget."
    )

    source = prompt_intent_source(prompt)
    outcome = first_path_outcome_phrase(source.first_path)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=source.title,
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert stub_phrase not in source.first_path.casefold()
    assert leaked not in source.first_path.casefold()
    assert stub_phrase not in outcome.casefold()
    assert leaked not in outcome.casefold()
    assert stub_phrase not in outcome_action_phrase(outcome).casefold()
    assert leaked not in outcome_action_phrase(outcome).casefold()
    assert stub_phrase not in rendered
    assert leaked not in rendered
    assert "word-sense metadata leaked" not in "\n".join(generated_semantic_slop_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_evidence_anchors_ignore_word_sense_metadata_requirements() -> None:
    prompt = (
        "Create a greenfield proposal for single cell perturbation atlas. The request uses record "
        "both as an action and as a governed object, so ownership must be explicit. "
        "A product manager must see actor value, non-goals, and success metrics."
    )

    anchors = evidence_anchor_phrases(prompt)

    assert "both as an action and as a governed object" not in anchors
    assert "so ownership must be explicit" not in anchors


def test_evidence_anchors_preserve_coordinated_action_objects() -> None:
    prompt = (
        "A mining company needs to allocate one critical haul-truck hydraulic pump between two sites after both "
        "report failures. The maintenance planner verifies the part number, the reliability engineer compares "
        "failure analysis, and the site superintendent approves the transport priority."
    )

    anchors = evidence_anchor_phrases(prompt)

    assert {"part number", "failure analysis"} <= set(anchors)
    assert all("maintenance planner verifies" not in anchor for anchor in anchors)


def test_evidence_anchors_do_not_promote_generic_coordinated_workflow_objects() -> None:
    prompt = (
        "Create a greenfield proposal for quality review. The analyst reviews the exception record, the supervisor "
        "approves the release decision, and the operator sees a signed audit receipt."
    )

    assert evidence_anchor_phrases(prompt) == ()


def test_evidence_anchors_keep_command_context_nouns_without_source_prose() -> None:
    prompt = (
        "Make a wedding weekend guide for guests traveling to a small town with limited taxis, a rehearsal dinner, "
        "and an accessibility request. A guest RSVPs with a dietary choice and reserves a shuttle seat."
    )

    anchors = evidence_anchor_phrases(prompt)

    assert anchors == ("limited taxis", "rehearsal dinner", "accessibility request")
    assert all("guests traveling to a small town" not in anchor for anchor in anchors)


def test_evidence_anchors_exclude_first_path_action_fragments() -> None:
    prompt = (
        "Build a berth turnaround control workspace where a terminal coordinator opens the morning vessel call "
        "at Pier 7, reconciles carrier manifests with berth assignments, records an exception, and sees a signed "
        "handoff receipt."
    )

    anchors = evidence_anchor_phrases(prompt)

    assert anchors == ("berth assignments",)
    assert "sees a signed handoff receipt" not in anchors


def test_multi_role_port_prompt_separates_product_path_from_evidence_directives() -> None:
    source = prompt_intent_source(PORT_OPERATIONS_PROMPT)
    anchors = evidence_anchor_phrases(PORT_OPERATIONS_PROMPT)

    assert source.title == "morning vessel call"
    assert source.actor == "berth planner"
    assert source.first_path == (
        "berth planner can reconcile container discharge, quay crane availability, tug window, and berth occupancy, "
        "then see whether the vessel can sail"
    )
    assert anchors == ("carrier manifests",)
    assert "carrier manifests" not in source.first_path
    assert "weather holds" not in source.first_path
    assert "customs clearance" not in source.first_path


def test_operational_constraints_keep_site_identifiers_separate_from_evidence() -> None:
    prompt = (
        "A terminal coordinator needs a product for the morning vessel call at Pier 7, "
        "the secondary handoff at Terminal A, and the review in Room 12. "
        "Keep carrier manifests as evidence."
    )

    assert operational_constraint_phrases(prompt) == (
        "morning vessel call",
        "Pier 7",
        "Terminal A",
        "Room 12",
        "Keep carrier manifests as evidence",
    )
    assert operational_constraint_phrases("The owner reviews the vessel call on Pier 7 for Terminal A.") == (
        "Pier 7",
        "Terminal A",
    )
    assert operational_constraint_phrases("The coordinator works for the morning shift only and closes before noon.") == (
        "morning shift",
        "before noon",
    )
    assert "Pier 7" not in evidence_anchor_phrases(prompt)


def test_operational_constraints_capture_positive_policy_without_absorbing_evidence() -> None:
    prompt = (
        "A vendor coordinator publishes an opening roster. Retain waitlist order. "
        "The first release must preserve source versions. Keep carrier manifests as evidence."
    )

    assert operational_constraint_phrases(prompt) == (
        "Retain waitlist order",
        "The first release must preserve source versions",
        "Keep carrier manifests as evidence",
    )
    assert prompt_intent_source(prompt).first_path == "A vendor coordinator publishes an opening roster"


def test_first_path_edit_deduplicates_sequence_connectors_from_constraints() -> None:
    assert operational_constraints_after_first_path_edit(
        ("match household needs to shelter capacity", "preserve consent evidence"),
        (
            "Shelter coordinators register displaced residents; then match household needs to shelter capacity; "
            "then preserve consent evidence; then publish a placement result."
        ),
    ) == (
        "match household needs to shelter capacity",
        "preserve consent evidence",
    )
    assert operational_constraint_kind("and then preserve consent evidence") == "preserve consent evidence"
    assert operational_constraint_is_present(
        "then preserve consent evidence",
        "The release must preserve consent evidence before placement.",
    )


def test_policy_classifier_keeps_complete_paths_and_atomizes_compound_obligations() -> None:
    valid_path = "Create a workflow tool where keep the shift log updated and show the open queue."
    actor_policy = "A vendor coordinator publishes an opening roster. A vendor coordinator must retain waitlist order."
    compound_policy = "The first release must preserve source versions and retain waitlist order."

    assert prompt_intent_source(valid_path).first_path == "keep the shift log updated and show the open queue"
    assert "must retain waitlist order" not in prompt_intent_source(actor_policy).first_path.casefold()
    assert operational_constraint_phrases(actor_policy) == (
        "A vendor coordinator must retain waitlist order",
    )
    assert operational_constraint_phrases(compound_policy) == (
        "The first release must preserve source versions",
        "retain waitlist order",
    )
    assert operational_constraint_phrases(
        "Retain geotagged photos for seven years; do not score neighborhoods in the first release."
    ) == ("Retain geotagged photos for seven years",)
    assert operational_constraint_phrases(
        "Do not score neighborhoods in the first release; retain geotagged photos for seven years."
    ) == ("retain geotagged photos for seven years",)


def test_operational_constraints_preserve_explicit_gate_and_noun_list_clauses() -> None:
    prompt = (
        "Brief // Rule: a reviewer approves the result after an operator uploads the reading // "
        "First path: upload a reading. Store reagent lot and calibration time. "
        "The notice needs a cleared analysis from AquaLedger."
    )

    assert operational_constraint_phrases(prompt) == (
        "a reviewer approves the result after an operator uploads the reading",
        "Store reagent lot and calibration time",
        "The notice needs a cleared analysis from AquaLedger",
    )


def test_prohibited_constraints_preserve_the_complete_leading_no_clause() -> None:
    assert prohibited_product_phrases(
        "No release may proceed without reviewer approval."
    ) == ("No release may proceed without reviewer approval",)


def test_prohibited_constraints_isolate_compact_negative_fields() -> None:
    prompt = (
        "Brief // Product: trace review // System: GaugeMesh stream // "
        "Non-goal: never turn a missing trace into a normal reading // First path: ingest a trace."
    )

    assert prohibited_product_phrases(prompt) == (
        "never turn a missing trace into a normal reading",
    )


def test_restatement_keeps_product_title_and_dependency_out_of_user_path() -> None:
    prompt = (
        "Plan the same tree-canopy ledger with this order of work: arborists verify species plans, "
        "neighborhood stewards submit planting sites, then finance clerks release microgrants only after "
        "inspection receipts. It relies on the mapping gateway. Retain geotagged photos for seven years; "
        "do not score neighborhoods in the first release."
    )

    source = prompt_intent_source(prompt)

    assert source.title == "tree-canopy ledger"
    assert source.first_path == (
        "arborists verify species plans, neighborhood stewards submit planting sites, then finance clerks "
        "release microgrants only after inspection receipts"
    )
    assert operational_constraint_phrases(prompt) == (
        "Retain geotagged photos for seven years",
    )


def test_same_remains_part_of_a_real_product_title() -> None:
    source = prompt_intent_source(
        "Plan the Same Day Ledger where a coordinator records a request and sees a receipt."
    )

    assert source.title == "Same Day Ledger"


def test_operational_constraints_are_editable_and_rendered_in_host_independent_fallback() -> None:
    overrides = _explicit_edit_overrides(
        confirmed_intent_sections(
            "## Operational constraints\n- Pier 7\n\n## Evidence requirements\n- Carrier manifests"
        )
    )
    fallback = _fallback_confirmation_markdown(
        prompt="A berth planner coordinates the vessel call at Pier 7.",
        title="Berth Turnaround Control",
    )

    assert overrides["operational_constraints"] == ["Pier 7"]
    assert overrides["evidence_requirements"] == ["Carrier manifests"]
    assert "Operational constraints\n- Pier 7" in fallback
    assert fallback.index("Operational constraints") < fallback.index("Human actors")


def test_prompt_source_prioritizes_where_workflow_over_expert_lens_sentence() -> None:
    prompt = (
        "Create a greenfield proposal for maternal health referral priority. Focus on a governed workflow "
        "where the care coordination nurse turns an ambiguous referral case into a review-ready record using "
        "risk-screening answers, appointment capacity, transport barriers, clinician review, explicit expert "
        "review, auditable decision ledger, and a final referral priority recommendation. The request uses record "
        "both as an action and as a governed object, so ownership must be explicit. An architect must see bounded "
        "components, state ownership, events, and projection boundaries. The post-confirm create must finish all "
        "project and governance artifacts under the standard budget."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    outcome = first_path_outcome_phrase(source.first_path, fallback="")

    assert source.actor == "care coordination nurse"
    assert source.first_path.startswith("care coordination nurse turns an ambiguous referral case")
    assert "record both as an action" not in source.first_path
    assert "as a governed object" not in source.first_path
    assert "action and as" not in outcome
    assert "action and as" not in outcome_action_phrase(outcome)
    assert "appointment capacity" in rendered
    assert "architect can see bounded components" not in rendered
    assert "reach an action and as a governed object" not in rendered
    assert "see an action and as a governed object" not in rendered
    assert "modal/base-form grammar drift" not in "\n".join(greenfield_quality_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_public_records_radio_and_privacy_prompts_keep_identity_out_of_quality_gates() -> None:
    public_prompt = (
        "Create a greenfield proposal for public records redaction. Focus on a governed workflow where "
        "the records officer turns an ambiguous redaction request into a review-ready record using statute, "
        "exemption, and requester evidence, explicit legal review, auditable decisions, and a final disclosure package."
    )
    radio_prompt = (
        "Create a greenfield proposal for emergency radio channel plan. The first release should give the public "
        "safety communications planner a complete path to open the radio channel plan, record coverage, interference, "
        "and mutual-aid evidence, escalate incident review, resolve exceptions, and publish the channel assignment "
        "plan without automating expert judgment."
    )
    privacy_prompt = (
        "Create a greenfield proposal for library privacy request review. Focus on a governed workflow where the "
        "library privacy officer turns an ambiguous patron data request into a review-ready record using requester "
        "authority, retention schedule, legal basis, and disclosure log evidence, explicit expert review, auditable "
        "decisions, and a final disclosure decision recommendation."
    )

    public_source = prompt_intent_source(public_prompt)
    radio_source = prompt_intent_source(radio_prompt)

    assert public_source.title == "public records redaction"
    assert public_source.actor == "records officer"
    assert public_source.first_path.startswith("records officer turns an ambiguous redaction request")
    assert radio_source.title == "emergency radio channel plan"
    assert radio_source.actor == "public safety communications planner"

    public_intent = parse_confirmed_intent_text(_guidance_envelope(public_prompt), prompt=public_prompt)
    radio_intent = parse_confirmed_intent_text(_guidance_envelope(radio_prompt), prompt=radio_prompt)
    privacy_intent = parse_confirmed_intent_text(_guidance_envelope(privacy_prompt), prompt=privacy_prompt)
    public_proposal = build_confirmed_greenfield_proposal(
        prompt=public_prompt,
        title=public_intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=public_intent,
    )
    radio_proposal = build_confirmed_greenfield_proposal(
        prompt=radio_prompt,
        title=radio_intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=radio_intent,
    )
    privacy_proposal = build_confirmed_greenfield_proposal(
        prompt=privacy_prompt,
        title=privacy_intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=privacy_intent,
    )
    public_rendered = json.dumps(public_proposal, sort_keys=True)
    radio_rendered = json.dumps(radio_proposal, sort_keys=True)
    privacy_rendered = json.dumps(privacy_proposal, sort_keys=True)

    assert "Records Officer:" in "\n".join(public_intent["human_actors"])
    assert "Explicit Legal:" not in "\n".join(public_intent["human_actors"])
    assert "Using Requester:" not in "\n".join(privacy_intent["human_actors"])
    assert "Explicit Expert:" not in "\n".join(privacy_intent["human_actors"])
    assert '"customer": "Library Privacy Officer needs' in privacy_rendered
    assert '"customer": "Using Requester' not in privacy_rendered
    assert '"customer": "Explicit Expert' not in privacy_rendered
    assert "The Channel Assignment Plan Without Automating Expert Judgment Workspace" not in radio_rendered
    assert "without automating expert judgment workspace" not in radio_rendered.casefold()
    assert "Channel Assignment Plan Without" not in radio_rendered
    assert greenfield_quality_issues(public_proposal) == []
    assert greenfield_quality_issues(radio_proposal) == []
    assert greenfield_quality_issues(privacy_proposal) == []


def test_prompt_source_preserves_short_command_title_before_focus_workflow() -> None:
    prompt = (
        "Create a greenfield proposal for protein design wetlab handoff. Focus on a governed workflow "
        "where the synthetic biology lead turns an ambiguous protein candidate into a review-ready record "
        "using structure confidence, expression yield, stability assay, safety review, explicit expert review, "
        "auditable decision ledger, and a final wetlab handoff recommendation."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert source.title == "protein design wetlab handoff"
    assert intent["title"] == "Protein Design Wetlab Handoff Workspace"
    assert "Recorded Using Structure" not in rendered
    assert "Protein Design Wetlab Handoff Workspace" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_prefers_labeled_request_over_evidence_envelope() -> None:
    clinic = prompt_intent_source(
        "PASTED CLINIC BRIEF\n"
        "Intake nurses capture referral requests. Social workers verify eligibility. "
        "Partner pharmacies confirm pickup.\n"
        "Request: propose the mobile-clinic referral ledger."
    )
    radio = prompt_intent_source(
        "RESEARCH PACKET: COMMUNITY RADIO\n"
        "Producers submit episode metadata, editors verify music licenses, and archivists retain master files.\n"
        "Keep license evidence for seven years. Request: propose a community-radio archive."
    )

    assert clinic.title == "mobile-clinic referral ledger"
    assert clinic.first_path.startswith("Intake nurses capture referral requests")
    assert radio.title == "community-radio archive"
    assert radio.first_path.startswith("Producers submit episode metadata")


def test_prompt_source_separates_narrative_product_identity_workflow_and_deliverable() -> None:
    prompt = (
        "PASTED DISTRIBUTION BRIEF\n"
        "The cold-chain pantry ledger receives donated lots from intake clerks. "
        "Nutrition leads verify allergen labels before dispatch drivers hand out parcels. "
        "Temperature checks are the release gate. "
        "The refrigeration telemetry API is the source for readings.\n"
        "Deliverable: a proposal with the custody path and release record."
    )

    source = prompt_intent_source(prompt)

    assert source.title == "cold-chain pantry ledger"
    assert source.actor == "Nutrition leads"
    assert "dispatch drivers hand out parcels" in source.first_path
    assert "refrigeration telemetry API" not in source.first_path
    assert "deliverable" not in source.first_path.casefold()
    assert "a proposal with" not in source.first_path.casefold()


def test_prompt_source_does_not_promote_source_or_deliverable_evidence_to_product_truth() -> None:
    source = prompt_intent_source(
        "Deliverable: a proposal with the custody path and release record. "
        "The payment system is the source for balances."
    )

    assert source.title == ""
    assert source.first_path == ""
    assert source.actor == ""


def test_prompt_source_keeps_compact_confirmed_direction_title_out_of_dependencies() -> None:
    prompt = (
        "## Confirmed direction Use the tree-canopy ledger. "
        "Keep: arborists verify species plans, inspection receipts gate microgrants, "
        "and the mapping gateway supplies site context. "
        "Changed: neighborhood stewards may correct site text. "
        "Retain geotagged photos for seven years. Do not score neighborhoods."
    )
    source = prompt_intent_source(prompt)
    intent = intent_hypothesis_from_operator_evidence(prompt, prefer_product_title=True)

    assert source.title == "tree-canopy ledger"
    assert "arborists verify species plans" in source.first_path.casefold()
    assert "tree-canopy ledger" not in source.first_path.casefold()
    assert "mapping gateway" not in source.first_path.casefold()
    assert "Neighborhood stewards may correct site text" in source.first_path
    assert intent["external_systems"] == ("mapping gateway",)
    assert {row.split(":", 1)[0] for row in intent["human_actors"]} == {
        "Arborists",
        "Neighborhood Stewards",
    }
    assert intent["operational_constraints"] == ("Retain geotagged photos for seven years",)


def test_prompt_source_rejects_action_bearing_multi_role_actor_label() -> None:
    prompt = (
        "Draft a greenfield proposal for a federated agent incident command ledger. "
        "Human operators assign investigation cases, review model-generated hypotheses, record state changes, "
        "route cross-team claims, maintain audit evidence, and decide what can be released to partners "
        "after legal approval."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "Human operators"
    assert source.first_path.startswith("Human operators assign investigation cases")
    assert source.actor != "Human operators assign investigation cases"
    assert "assign investigation cases can be released" not in source.first_path


def test_prompt_source_keeps_a_reservation_workflow_actor_before_the_first_action() -> None:
    prompt = (
        "Build a Quantum Networking Lab Management App where lab operators reserve a calibrated entanglement link "
        "for an experiment, confirm device and calibration availability, record either a conflict or an accepted "
        "reservation, and see an auditable ready-to-run reservation."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "lab operators"
    assert source.first_path.startswith("lab operators reserve a calibrated entanglement link for an experiment")
    assert "lab operators reserve a calibrated entanglement confirms" not in source.first_path.casefold()
    assert "record either a conflict or an accepted reservation" in source.first_path
    assert source.first_path.endswith("see an auditable ready-to-run reservation")


def test_prompt_source_keeps_modal_verbs_out_of_explicit_actor_labels() -> None:
    prompt = (
        "Create a tool for extension publishers to assemble release notes from approved changelog fragments, "
        "breaking-change notices, and compatibility windows."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "extension publishers"
    assert source.first_path.startswith("extension publishers can assemble release notes")
    assert "can can" not in source.first_path.casefold()


def test_prompt_source_preserves_actor_after_leading_contextual_clause() -> None:
    prompt = (
        "Draft a greenfield proposal for a release board. During incident review, human operators assign "
        "investigation cases, record state changes, and decide what can be released to partners after legal approval."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "human operators"
    assert source.first_path.startswith("human operators can assign investigation cases")
    assert "during incident can" not in source.first_path.casefold()


def test_prompt_source_strips_multi_role_review_lens_bundle_from_first_path() -> None:
    prompt = (
        "Create a greenfield proposal for protein design wetlab handoff where a synthetic biology lead turns "
        "an ambiguous protein candidate into a review-ready record using structure confidence, expression yield, "
        "stability assay, safety review, explicit expert review, auditable decision ledger, and a final wetlab "
        "handoff recommendation. A product manager must see the first complete path, actor value, non-goals, "
        "and success metrics. An architect must see component ownership and boundaries. An engineer must see "
        "implementable records, states, validation, and testable acceptance criteria. A domain expert must see "
        "scientific depth, uncertainty handling, review constraints, and no unsupported biological claims."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert is_operator_review_lens_step(
        "A product manager must see the first complete path, actor value, non-goals, and success metrics"
    )
    assert is_operator_review_lens_step(
        "A domain expert must see scientific depth, uncertainty handling, review constraints, and no unsupported biological claims"
    )
    assert operator_review_lens_obligations(prompt) == [
        "Product Manager review must verify the first complete path, actor value, non-goals, and success metrics",
        "Architect review must verify component ownership and boundaries",
        "Engineer review must verify implementable records, states, validation, and testable acceptance criteria",
        "Domain Expert review must verify scientific depth, uncertainty handling, review constraints, and no unsupported biological claims",
    ]
    assert drop_requirement_control_steps(
        [
            "Synthetic biology lead turns an ambiguous protein candidate into a review-ready record",
            "A product manager must see the first complete path, actor value, non-goals, and success metrics",
            "An architect must see component ownership and boundaries",
            "An engineer must see implementable records, states, validation, and testable acceptance criteria",
            "A domain expert must see scientific depth, uncertainty handling, review constraints, and no unsupported biological claims",
        ]
    ) == ["Synthetic biology lead turns an ambiguous protein candidate into a review-ready record"]
    assert source.title == "protein design wetlab handoff"
    assert source.first_path.startswith("A synthetic biology lead turns an ambiguous protein candidate")
    assert "product manager must see" not in source.first_path.casefold()
    assert "domain expert must see" not in source.first_path.casefold()
    assert not any(
        row.startswith(("Product Manager:", "Architect:", "Engineer:", "Domain Expert:"))
        for row in intent["human_actors"]
    )
    assumption_text = "\n".join(intent["assumptions"])
    assert "Product Manager review must verify the first complete path" in assumption_text
    assert "Architect review must verify component ownership and boundaries" in assumption_text
    assert "Engineer review must verify implementable records, states, validation" in assumption_text
    assert "Domain Expert review must verify scientific depth" in assumption_text
    assert "recorded using" not in rendered.casefold()
    assert "workspace result" not in intent["product_view"].casefold()
    assert "visible result is a final wetlab handoff recommendation" in intent["product_view"].casefold()
    assert "review-ready record" in rendered.casefold()
    assert "Product Manager Must" not in rendered
    assert "Domain Expert Must" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_rejects_non_human_workflow_subject_as_actor() -> None:
    prompt = (
        "Create a greenfield proposal for waiver review where the decision summary turns an ambiguous waiver packet "
        "into a reviewable status."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=intent,
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.actor == ""
    assert intent["first_path"].startswith("A representative user reviews waiver review details")
    assert "Decision Summary:" not in "\n".join(intent["human_actors"])
    assert "decision summary turns" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_preserves_inline_source_evidence_field_content() -> None:
    prompt = (
        "Create an evidence review workspace where an operator records a Source Evidence: verified status, "
        "records a decision, and verifies the visible outcome."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.actor == "operator"
    assert "Source Evidence: verified status" in source.first_path
    assert any("Source Evidence: verified status" in row for row in intent["human_actors"])


def test_prompt_source_strips_standalone_source_evidence_tail() -> None:
    prompt = (
        "Project brief for an accessibility team. An accessibility operator reviews one evidence item, "
        "records a decision, and verifies the visible outcome. Source repository: owner/example. "
        "Source evidence: an accessible component library with keyboard support."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.first_path.casefold().startswith("an accessibility operator reviews one evidence item")
    assert "Source repository" not in source.first_path
    assert "accessible component library" not in source.first_path
    assert any(row.startswith("Accessibility Operator:") for row in intent["human_actors"])


def test_prompt_source_strips_delimiter_bound_source_repository_tail() -> None:
    for delimiter in ("-", ";", ":", ","):
        prompt = (
            "Create an accessibility product. An accessibility operator reviews one evidence item, records a "
            f"decision, and verifies the visible outcome {delimiter} Source repository: tailwindlabs/headlessui. "
            "Source evidence: an accessible component library with keyboard support."
        )

        source = prompt_intent_source(prompt)

        assert source.first_path.casefold().startswith("an accessibility operator reviews one evidence item")
        assert "tailwindlabs" not in source.first_path
        assert "accessible component library" not in source.first_path


def test_prompt_source_strips_delimiter_bound_source_evidence_tail() -> None:
    for delimiter in ("-", ";", ":", ","):
        for label_separator in (":", "-"):
            prompt = (
                "Create an accessibility product. An accessibility operator reviews one evidence item, records a "
                f"decision, and verifies the visible outcome {delimiter} Source evidence {label_separator} an accessible "
                "component library with keyboard support."
            )

            source = prompt_intent_source(prompt)

            assert source.first_path.casefold().startswith("an accessibility operator reviews one evidence item")
            assert "accessible component library" not in source.first_path


def test_prompt_source_ignores_standalone_source_evidence_field_as_an_actor() -> None:
    prompt = (
        "Create an evidence review workspace. User intent: An operator records a decision and verifies the visible "
        "outcome. Source Evidence: verified status appears in the case header."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.first_path.startswith("An operator records a decision")
    assert source.actor == "operator"
    assert "verified status appears in the case header" not in source.first_path
    assert intent["first_path"].startswith("An operator records a decision")
    assert len(intent["human_actors"]) == 1
    assert intent["human_actors"][0].startswith("Operator:")
    assert "evidence operator" not in intent["human_actors"][0].casefold()
    assert not any(row.startswith("Appears:") for row in intent["human_actors"])


def test_prompt_source_rejects_non_human_product_surfaces_as_where_actors() -> None:
    prompts = (
        ("care team dashboard", "Care Team:"),
        ("analyst dashboard", "Analyst:"),
        ("operations console", "Operations:"),
    )

    for subject, forbidden_actor in prompts:
        prompt = (
            f"Create a triage workspace where the {subject} shows blocked cases, pending evidence, "
            "and escalation status."
        )
        source = prompt_intent_source(prompt)
        intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

        assert source.actor == ""
        assert not any(row.startswith(forbidden_actor) for row in intent["human_actors"])


def test_edited_request_keeps_history_and_state_descriptions_out_of_the_first_path() -> None:
    prompt = (
        "Edited request: make the canal-lock dispatch board for lock tenders. "
        "Start with inspection tickets, then route a ticket to a mechanic, and produce a repair clearance. "
        "The ticket state is queued, assigned, repaired, or cleared. "
        "The earlier draft said a tender may clear a repair alone; replace that rule: "
        "a hydraulic inspector must clear every repair."
    )

    source = prompt_intent_source(prompt)

    assert source.title == "canal-lock dispatch board"
    assert source.first_path == (
        "Start with inspection tickets, then route a ticket to a mechanic, and produce a repair clearance"
    )


def test_plural_users_and_need_fields_form_an_explicit_complete_path() -> None:
    prompt = """Pasted field brief
- Users: refuge wardens and rescue dispatchers
- Need: log emergency cache inspections in CairnSignal
- Output: a cache readiness slip
- First path: inspect a cache"""

    source = prompt_intent_source(prompt)

    assert source.actor == "refuge wardens and rescue dispatchers"
    assert source.first_path == (
        "Refuge wardens and rescue dispatchers can inspect a cache, log emergency cache inspections "
        "in CairnSignal, and receive a cache readiness slip"
    )
    assert operational_constraint_phrases(prompt) == ()


def test_structured_brief_rule_is_the_only_positive_obligation() -> None:
    prompt = """Pasted field brief
- Users: refuge wardens and rescue dispatchers
- Need: log emergency cache inspections in CairnSignal
- Rule: dispatchers release a resupply request after a warden records seal condition
- First path: inspect a cache"""

    assert operational_constraint_phrases(prompt) == (
        "dispatchers release a resupply request after a warden records seal condition",
    )


def test_state_description_cannot_supply_a_missing_user_path() -> None:
    source = prompt_intent_source(
        "Edited request: build the audit board for lock tenders. "
        "The ticket state is synchronized to the audit log after approval."
    )

    assert source.title == "audit board"
    assert source.first_path == ""


def test_json_edited_request_uses_typed_title_and_path_fields() -> None:
    prompt = json.dumps(
        {
            "edited request": "make the canal-lock dispatch board for lock tenders",
            "first path": "inspect a ticket and receive a repair clearance",
        }
    )

    source = prompt_intent_source(prompt)

    assert source.title == "canal-lock dispatch board"
    assert source.first_path == "inspect a ticket and receive a repair clearance"
    assert operational_constraint_phrases(prompt) == ()


@pytest.mark.parametrize("actor", ("SAP ECC", "CI jobs"))
def test_nonhuman_users_field_does_not_establish_human_actor_grammar(actor: str) -> None:
    prompt = json.dumps(
        {
            "users": actor,
            "need": "sync invoices",
            "first path": "review an invoice",
            "output": "a sync receipt",
        }
    )

    assert not explicit_actor_has_human_grammar(prompt)


def test_structured_multi_actor_rule_orders_the_grounded_handoff() -> None:
    prompt = """Pasted request
**Goal:** schedule light exposure for fragile display pages.
**Actors:** exhibit conservators, gallery technicians.
**Output:** exposure allowance card.
**Rule:** a conservator approves an allowance after a technician uploads the lux reading.
**First path:** upload a lux reading."""

    source = prompt_intent_source(prompt)

    assert source.actor == "gallery technicians"
    assert source.first_path == (
        "Gallery technicians upload the lux reading. "
        "Exhibit conservators approve an allowance. "
        "The product shows the exposure allowance card"
    )


def test_temporal_rule_matches_the_unrendered_start_action() -> None:
    prompt = """Pasted request
**Actors:** quality reviewers, release coordinators.
**Output:** a release receipt.
**Rule:** a quality reviewer requests correction before a release coordinator issues a receipt.
**First path:** starts with request review."""

    source = prompt_intent_source(prompt)

    assert "Quality reviewers request correction" in source.first_path
    assert "Release coordinators issue a receipt" in source.first_path
    assert "release receipt" in source.first_path


def test_temporal_rule_does_not_repeat_an_output_already_issued_by_an_actor() -> None:
    prompt = """Pasted request
**Actors:** intake clerks, supervisors.
**Output:** a receipt.
**Rule:** an intake clerk submits a packet before a supervisor issues a receipt.
**First path:** starts with submit a packet."""

    source = prompt_intent_source(prompt)

    assert source.first_path.casefold().count("receipt") == 1
    assert "the product shows a receipt" not in source.first_path.casefold()


def test_command_audience_owns_an_explicit_start_before_a_state_gate() -> None:
    prompt = (
        "Source notes say traveling organ tuners need routes for municipal instruments. "
        "Build the service for tuning leads. "
        "A route becomes ready after the venue custodian accepts the access window, "
        "and it produces a tuning itinerary. "
        "States are drafted, measured, awaiting access, ready, and completed. "
        "Begin by recording a reed measurement."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "tuning leads"
    assert source.first_path == (
        "Tuning leads can record a reed measurement. "
        "A route becomes ready after the venue custodian accepts the access window. "
        "The product shows a tuning itinerary"
    )


def test_nested_human_constraint_does_not_turn_an_artifact_into_the_user() -> None:
    prompt = (
        "Service operators open an incident, field crews log isolation work, and tenant liaisons receive a bulletin. "
        "A bulletin is published after a control-room supervisor approves the restoration reading."
    )

    source = prompt_intent_source(prompt)

    assert source.actor == "Service operators"
    assert source.actor.casefold() != "bulletin"


def test_short_first_path_hint_does_not_replace_a_complete_grounded_workflow() -> None:
    prompt = (
        "Create a safety register. "
        "Captains record prop serials, stage managers request activation, and operators issue an activation card. "
        "First path: catalog a prop."
    )

    source = prompt_intent_source(prompt)

    assert source.first_path == (
        "Captains record prop serials, stage managers request activation, and operators issue an activation card"
    )
