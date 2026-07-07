from __future__ import annotations

import json

from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import evidence_anchor_phrases
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import drop_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_operator_review_lens_step
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import operator_review_lens_obligations
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import visible_result_object
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import select_visible_result_candidate
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import generated_semantic_slop_issues


def _guidance_envelope(prompt: str) -> str:
    return f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
- Render the visible confirmation as sectioned Markdown in this order.

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md.
Confirmed CLI after confirmation: odylith greenfield create --repo-root . --prompt '{prompt}' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --confirm --release 0.0.1
"""


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
        assert subject in rendered or subject in source.first_path.casefold()
        assert "english grammar" in rendered or "grammar ambiguity" in rendered
        assert "noun and a governed object" not in semantic_visible_result
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
    assert source.first_path.startswith("care coordination nurse turn an ambiguous referral case")
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
    assert public_source.first_path.startswith("records officer turn an ambiguous redaction request")
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
    assert source.first_path.startswith("synthetic biology lead turn an ambiguous protein candidate")
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
