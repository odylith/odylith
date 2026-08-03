from __future__ import annotations

import json
from pathlib import Path

import pytest

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_issues
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_completion import _first_path_is_complete_enough
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_validation import _first_path_is_clear_enough
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery import confirmation_from_operator_intent
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import product_intent_source_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_project_title_source
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    GreenfieldClarificationRequired,
)
from odylith.runtime.domain_intelligence.greenfield_prompt_intent_materialization import (
    materialize_prompt_intent_hypothesis,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patch_apply import (
    complete_greenfield_semantic_apply_payload,
)
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import evaluation_semantics_for_texts
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_quality_gate import greenfield_quality_issues
from odylith.runtime.domain_intelligence.proposal_memory import build_accepted_project_source_payload
from tests.unit.runtime.greenfield_proposal_fixtures import confirmed_mapping_with_authority


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


def test_prompt_source_recovers_sentence_style_title_and_release_path() -> None:
    prompt = (
        "Build a greenfield proposal for an orbital debris conjunction review workspace. "
        "The first release should let mission analysts capture predicted close approaches, "
        "sensor confidence, maneuver constraints, communications approvals, rejected interpretations, "
        "and review proof without commanding satellites or changing flight plans."
    )

    source = prompt_intent_source(prompt)

    assert source.title == "orbital debris conjunction review workspace"
    assert source.first_path.startswith("mission analysts capture predicted close approaches")
    assert "The first release should let" not in source.first_path
    assert "greenfield proposal" not in source.first_path


def test_prompt_materialization_projects_actor_state_and_responsibilities_from_the_full_path(tmp_path: Path) -> None:
    prompt = (
        "Build a generic dynamic router that lets an individual software engineer submit one software engineering "
        "request, decomposes and routes subtasks to appropriate models based on complexity and cost, and returns "
        "validated runnable Python code plus automated tests."
    )

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Generic Dynamic Router",
        edit_evidence=(
            "No change to the first complete path: an individual software engineer submits one software "
            "engineering request and receives runnable Python code plus automated tests."
        ),
    )

    actor_text = " ".join(intent["human_actors"]).casefold()
    system_text = " ".join(intent["internal_systems"]).casefold()
    assert "individual software engineer" in actor_text
    assert "router:" not in actor_text
    assert "generic dynamic router workspace user" not in actor_text
    assert "software engineering request" in intent["state_object"].casefold()
    assert "python code plus automated tests record" not in intent["state_object"].casefold()
    assert "decomposition" in system_text
    assert "routing" in system_text
    assert "intake register" not in system_text
    assert "review workspace" not in system_text
    assert "proof ledger" not in system_text
    assert "the product decomposes and routes" in intent["first_path"].casefold()


def test_canonical_meaning_bounds_state_and_preserves_mixed_human_ownership() -> None:
    intent = confirmation_from_operator_intent(
        "Build a review workspace that lets a reviewer submit evidence, and a supervisor approves the case.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["state_object"] == "The primary state object is an evidence record."
    assert "a supervisor approves the case" in intent["first_path"].casefold()
    assert "The product approves the case" not in intent["first_path"]
    system_text = " ".join(intent["internal_systems"]).casefold()
    assert "records the supervisor decision" in system_text
    assert "approves the case while" not in system_text
    assert "source input, current status, owner" not in intent["state_object"]


def test_canonical_meaning_keeps_actor_choice_out_of_product_ownership() -> None:
    intent = confirmation_from_operator_intent(
        "Build a cooking controller where a cook chooses a recipe and the controller sequences heat.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["state_object"] == "The primary state object is a recipe."
    system_text = " ".join(intent["internal_systems"]).casefold()
    assert "records the cook decision" in system_text
    assert "chooses a recipe and the controller" not in system_text
    assert "sequences heat" in system_text


def test_canonical_meaning_preserves_an_explicit_generic_user() -> None:
    intent = confirmation_from_operator_intent(
        "Build a decision workspace that lets a user submit a case and receive a decision.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["state_object"] == "The primary state object is a case."
    assert intent["human_actors"][0].startswith("User:")
    actor_text = " ".join(intent["human_actors"])
    assert "Decision user" not in actor_text
    assert "An user" not in actor_text


def test_unchanged_first_path_edit_still_applies_a_visible_result_correction(tmp_path: Path) -> None:
    prompt = "Build a permit desk where a clerk submits one permit and receives review status."
    baseline = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Permit Desk",
    )

    edited = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Permit Desk",
        edit_evidence=(
            "No change to the first complete path: a clerk submits one permit and receives review status. "
            "The visible result should be a signed permit receipt."
        ),
    )

    assert edited["first_path"] != baseline["first_path"]
    assert "signed permit receipt" in edited["first_path"].casefold()


def test_unchanged_first_path_edit_preserves_a_bulleted_visible_result_correction(tmp_path: Path) -> None:
    prompt = "Build a permit desk where a clerk submits one permit and receives review status."
    baseline = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Permit Desk",
    )

    edited = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Permit Desk",
        edit_evidence=(
            "No change to the first complete path: a clerk submits one permit and receives review status.\n"
            "- The visible result should be a signed permit receipt."
        ),
    )

    assert edited["first_path"] != baseline["first_path"]
    assert "signed permit receipt" in edited["first_path"].casefold()


def test_relative_clause_keeps_shared_subject_actor_actions_owned_by_the_actor() -> None:
    intent = confirmation_from_operator_intent(
        "Build a permit desk that lets a clerk submit one permit, review flagged issues, "
        "and receive a signed permit receipt.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["first_path"] == (
        "A clerk can submit one permit, review flagged issues, and receive a signed permit receipt."
    )
    assert "the product reviews" not in " ".join(intent["internal_systems"]).casefold()


def test_command_relative_clause_preserves_a_role_with_a_system_qualifier() -> None:
    intent = confirmation_from_operator_intent(
        "Create a greenfield product for platform operators who submit distributed agent jobs, "
        "track assigned worker progress, collect execution evidence, surface blockers, and publish "
        "a final run record with reviewer approval.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["first_path"] == (
        "Platform operators can submit distributed agent jobs, track assigned worker progress, "
        "collect execution evidence, surface blockers, and publish a final run record with reviewer approval."
    )
    assert intent["human_actors"][0].startswith("Platform Operators:")
    assert "representative user" not in intent["first_path"].casefold()


def test_actor_led_object_list_stays_one_path_without_fake_records() -> None:
    intent = confirmation_from_operator_intent(
        "Build an evidence review workspace where researchers compare evidence, exceptions, "
        "and signoff before release.",
        prefer_product_title=True,
        as_mapping=True,
    )

    assert intent["first_path"] == "Researchers compare evidence, exceptions, and signoff before release."
    systems = " ".join(intent["internal_systems"])
    assert "Signoff Record" not in systems
    assert "compare evidence, exceptions, and signoff before release" in systems.casefold()


def test_visible_confirmation_uses_the_same_canonical_internal_systems_as_typed_intent() -> None:
    prompt = (
        "Build a generic dynamic router that lets an individual software engineer submit one software engineering "
        "request, decomposes and routes subtasks to appropriate models based on complexity and cost, and returns "
        "validated runnable Python code plus automated tests."
    )

    intent = confirmation_from_operator_intent(prompt, prefer_product_title=True, as_mapping=True)
    rendered = confirmation_from_operator_intent(prompt, prefer_product_title=True)

    assert intent["internal_systems"]
    assert all(row in rendered for row in intent["internal_systems"])
    assert "Intake Register" not in rendered
    assert "Review Workspace" not in rendered
    assert "Proof Ledger" not in rendered


@pytest.mark.parametrize(
    ("prompt", "actor", "state_term", "forbidden_actor"),
    (
        (
            "Build a field service desk where a technician submits a repair request, a scheduler assigns a visit, "
            "and the technician receives a confirmed appointment.",
            "technician",
            "repair request",
            "scheduler service",
        ),
        (
            "Build a lesson review tool where a teacher uploads one lesson plan, reviews accessibility findings, "
            "and receives a revised lesson summary.",
            "teacher",
            "lesson plan",
            "tool",
        ),
    ),
)
def test_prompt_materialization_keeps_unfamiliar_people_separate_from_product_systems(
    tmp_path: Path,
    prompt: str,
    actor: str,
    state_term: str,
    forbidden_actor: str,
) -> None:
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title="Greenfield Product",
    )

    actor_text = " ".join(intent["human_actors"]).casefold()
    assert actor in actor_text
    assert forbidden_actor not in actor_text
    assert state_term in intent["state_object"].casefold()


def test_thin_wrapper_preserves_original_user_intent_as_product_evidence() -> None:
    prompt = (
        "Create a greenfield product for a decision coach that lets a user describe a difficult choice, "
        "compare options against stated values, record tradeoffs, and choose one next action with review evidence."
    )

    intent = parse_confirmed_intent_text(
        f"Product Intent Confirmation needed\n\nOriginal user intent\n{prompt}\n",
        prompt=prompt,
    )

    assert intent["title"] == "Decision Coach"
    assert intent["first_path"].startswith("User can describe a difficult choice")
    assert intent["human_actors"][0].startswith("User:")


def test_prompt_source_does_not_promote_source_metadata_to_a_product_first_path() -> None:
    source = prompt_intent_source(
        "Source evidence: Radix Primitives is an open-source UI component library for building accessible interfaces."
    )

    assert source.first_path == ""


def test_actorless_technical_list_does_not_invent_entanglement_as_a_human_actor() -> None:
    prompt = (
        "Build a Quantum Networking Lab Management App that coordinates lab devices, "
        "entanglement links, calibration, reservations, telemetry, and auditable proof results."
    )

    intent = confirmation_from_operator_intent(prompt, prefer_product_title=True, as_mapping=True)

    assert not any(row.casefold().startswith("entanglement:") for row in intent["human_actors"])
    assert not intent["problem"].casefold().startswith("entanglement")
    assert not intent["first_path"].casefold().startswith("an entanglement")


def test_prompt_source_keeps_explicit_path_and_excludes_following_source_metadata() -> None:
    source = prompt_intent_source(
        "Create an accessibility product. An accessibility operator reviews one evidence item, records a decision, "
        "and verifies the visible outcome. Source repository: tailwindlabs/headlessui. "
        "Source evidence: Accessible UI components for Tailwind CSS."
    )

    assert source.first_path.startswith("An accessibility operator reviews one evidence item")
    assert "tailwindlabs/headlessui" not in source.first_path


def test_prompt_source_stops_at_inline_source_metadata_label() -> None:
    source = prompt_intent_source(
        "Project brief for an accessibility team. An accessibility operator reviews one evidence item, records a "
        "decision, and verifies the visible outcome. Source repository: leongersen/noUiSlider. Source evidence: "
        "noUiSlider is a lightweight, ARIA-accessible JavaScript range slider with multi-touch and keyboard support. "
        "It also fits wonderfully in responsive designs and has no dependencies."
    )

    assert source.first_path.startswith("An accessibility operator reviews one evidence item")
    assert "leongersen/noUiSlider" not in source.first_path
    assert "responsive designs" not in source.first_path


@pytest.mark.parametrize(
    ("prompt", "title", "actor", "first_path", "forbidden_evidence"),
    (
        (
            "Create an accessibility product. User intent: A service coordinator opens an intake request, assigns a "
            "resolution owner, and verifies a decision receipt. Source repository: tailwindlabs/headlessui. "
            "Source evidence: Completely unstyled, fully accessible UI components, designed to integrate beautifully "
            "with Tailwind CSS.",
            "accessibility product",
            "service coordinator",
            "A service coordinator opens an intake request, assigns a resolution owner, and verifies a decision receipt",
            "Completely unstyled",
        ),
        (
            "Project brief for an accessibility team. User intent: A program lead registers a readiness dossier, "
            "selects a review disposition, and verifies a publication status. Source repository: radix-ui/primitives. "
            "Source evidence: Radix Primitives is an open-source UI component library for building high-quality, "
            "accessible design systems and web apps. Maintained by @workos.",
            "Project brief",
            "program lead",
            "A program lead registers a readiness dossier, selects a review disposition, and verifies a publication status",
            "Maintained by @workos",
        ),
        (
            "Create a reviewed accessibility product. User intent: A case manager creates an eligibility record, "
            "routes a service decision, and verifies a resolution notice. Source repository: unovue/reka-ui. "
            "Source evidence: An open-source UI component library for building high-quality, accessible design "
            "systems and web apps for Vue. Previously Radix Vue.",
            "reviewed accessibility product",
            "case manager",
            "A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice",
            "Previously Radix Vue",
        ),
    ),
)
def test_prompt_source_recovers_explicit_user_intent_before_source_evidence(
    prompt: str,
    title: str,
    actor: str,
    first_path: str,
    forbidden_evidence: str,
) -> None:
    source = prompt_intent_source(prompt)

    assert source.title == title
    assert source.actor == actor
    assert source.first_path == first_path
    assert "User intent:" not in source.actor
    assert "User intent:" not in source.first_path
    assert forbidden_evidence not in source.first_path


def test_preconfirm_semantic_completion_rerenders_the_first_path_tail(tmp_path: Path) -> None:
    prompt = (
        "Create a reviewed accessibility product. User intent: A case manager creates an eligibility record, "
        "routes a service decision, and verifies a resolution notice. Source repository: unovue/reka-ui. "
        "Source evidence: An open-source UI component library for building high-quality, accessible design systems "
        "and web apps for Vue. Previously Radix Vue"
    )
    edited_confirmation = """# Accessibility Source Product

## Product Story
This product helps accessibility teams carry out the explicitly supplied first path.

## Source Evidence
Repository: unovue/reka-ui
An open-source UI component library for building high-quality, accessible design systems and web apps for Vue. Previously Radix Vue

## First Complete Path
A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice.

## Proof Boundary
The source evidence, decision, and outcome remain traceable.
"""

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
        edit_evidence=edited_confirmation,
    )
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        confirmed_intent=intent,
    )
    sequence = next(row for row in proposal["diagrams"] if row["title"] == "First Path Sequence")
    first_path = proposal["semantic_model"]["first_path_contract"]

    assert first_path["raw_path"] == (
        "A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice."
    )
    assert first_path["visible_result"] == "A case manager verifies a resolution notice"
    assert first_path["events"][-1]["visible_result"] is True
    assert "accepted result for review" not in sequence["mermaid_source"].casefold()
    assert greenfield_quality_issues(proposal) == []

    for row, title in zip(
        proposal["backlog"],
        ("Current Program", "Current Workflow", "Current Boundary", "Current Proof"),
        strict=False,
    ):
        row["title"] = title
    refreshed = complete_greenfield_semantic_apply_payload(
        proposal,
        release_selector="",
        proposal_completed=True,
    )
    refreshed_sequence = next(row for row in refreshed["diagrams"] if row["title"] == "First Path Sequence")

    assert refreshed_sequence["related_workstream_titles"] == ["Current Workflow", "Current Boundary"]


def test_confirmation_recovery_keeps_sectioned_source_evidence_out_of_product_truth() -> None:
    prompt = """# Healthcare Source Product

## Product Story
This product helps healthcare teams carry out the explicitly supplied first path.

## Source Evidence
Medical Q&A with Deep Language Models evaluates model answers against medical benchmarks and reference methods.

## First Complete Path
A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice.

## Proof Boundary
The decision and resolution notice remain traceable for review.
"""

    source = product_intent_source_text(prompt)
    intent = confirmation_from_operator_intent(prompt, prefer_product_title=True, as_mapping=True)
    product_truth = {key: value for key, value in intent.items() if key != "prompt"}
    rendered = json.dumps(product_truth, sort_keys=True).casefold()

    assert "medical q&a" not in source.casefold()
    assert "method or model version" not in rendered
    assert "medical q&a" not in rendered
    assert "case manager creates an eligibility record" in str(intent["first_path"]).casefold()
    assert "routes a service decision" in str(intent["first_path"]).casefold()
    assert "verifies a resolution notice" in str(intent["first_path"]).casefold()


def test_prompt_source_keeps_sectioned_original_user_intent_out_of_source_evidence() -> None:
    prompt = """Host guidance

## Original User Intent
# Healthcare Source Product

## Source Evidence
Medical Q&A with Deep Language Models evaluates model answers against medical benchmarks and reference methods.

## First Complete Path
A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice.

## Next step
Render the confirmation.
"""

    source_text = product_intent_source_text(prompt)
    source = prompt_intent_source(prompt)

    assert "medical q&a" not in source_text.casefold()
    assert source.first_path.casefold().startswith("a case manager creates an eligibility record")
    assert "routes a service decision" in source.first_path.casefold()
    assert "verifies a resolution notice" in source.first_path.casefold()


def test_preconfirm_materialization_keeps_sectioned_source_evidence_out_of_product_truth(tmp_path: Path) -> None:
    prompt = (
        "Create a reviewed healthcare product. User intent: A case manager creates an eligibility record, "
        "routes a service decision, and verifies a resolution notice. Source evidence: Medical Q&A with Deep "
        "Language Models evaluates model answers against medical benchmarks and reference methods."
    )
    edited_confirmation = """# Healthcare Source Product

## Product Story
This product helps healthcare teams carry out the explicitly supplied first path.

## Source Evidence
Medical Q&A with Deep Language Models evaluates model answers against medical benchmarks and reference methods.

## First Complete Path
A case manager creates an eligibility record, routes a service decision, and verifies a resolution notice.

## Proof Boundary
The decision and resolution notice remain traceable for review.
"""

    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
        edit_evidence=edited_confirmation,
    )
    product_truth = {key: value for key, value in intent.items() if key != "prompt"}
    rendered = json.dumps(product_truth, sort_keys=True).casefold()

    assert "medical q&a" not in rendered
    assert "method or model version" not in rendered
    assert "case manager creates an eligibility record" in str(intent["first_path"]).casefold()
    assert "routes a service decision" in str(intent["first_path"]).casefold()
    assert "verifies a resolution notice" in str(intent["first_path"]).casefold()


def test_prompt_materialization_preserves_explicit_operator_context_before_source_evidence(tmp_path: Path) -> None:
    prompt = (
        "Project brief for an accessibility team. User intent: A program lead registers a readiness dossier, "
        "selects a review disposition, and verifies a publication status. Source repository: radix-ui/primitives. "
        "Source evidence: Radix Primitives is an open-source UI component library for building high-quality, "
        "accessible design systems and web apps."
    )

    source = prompt_intent_source(prompt)
    intent = materialize_prompt_intent_hypothesis(
        prompt=prompt,
        repo_root=tmp_path,
        fallback_title=greenfield_proposals.intent_title(prompt),
    )

    assert source.operator_context == "an accessibility team"
    assert "serves an accessibility team" in intent["product_story"]
    assert "Radix Primitives" not in intent["product_story"]


def test_research_evidence_wrapper_does_not_erase_a_material_first_path_gap(tmp_path: Path) -> None:
    prompt = (
        "Create an accessibility product from this research evidence. Source repository: radix-ui/primitives. "
        "Source evidence: accessibility. Repository description: Radix Primitives is an open-source UI component "
        "library for building high-quality, accessible design systems and web apps."
    )

    with pytest.raises(GreenfieldClarificationRequired):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title=greenfield_proposals.intent_title(prompt),
        )

    assert not (tmp_path / ".odylith" / "runtime" / "greenfield").exists()


@pytest.mark.parametrize(
    "source_evidence",
    (
        "Documentation states User intent: A service coordinator opens an intake request, assigns a resolution owner, "
        "and verifies a decision receipt.",
        "Documentation states an example. User intent: A service coordinator opens an intake request, assigns a "
        "resolution owner, and verifies a decision receipt.",
        "Documentation states an example. -- Product intent: A service coordinator opens an intake request, assigns a "
        "resolution owner, and verifies a decision receipt.",
    ),
)
def test_prompt_source_does_not_promote_an_intent_label_quoted_inside_source_evidence(source_evidence: str) -> None:
    source = prompt_intent_source(
        f"Source evidence: {source_evidence}"
    )

    assert source.title == ""
    assert source.actor == ""
    assert source.first_path == ""


def test_prompt_source_does_not_promote_a_delimiter_prefixed_intent_label_after_source_metadata() -> None:
    source = prompt_intent_source(
        "Create an evidence review workspace. Source evidence: a quoted example -- User intent: A service coordinator "
        "opens an intake request, assigns a resolution owner, and verifies a decision receipt."
    )

    assert source.title == "evidence review workspace"
    assert source.actor == ""
    assert source.first_path == "Create an evidence review workspace"
    assert "service coordinator" not in source.first_path


@pytest.mark.parametrize(
    ("label", "delimiter"),
    (
        ("User intent", " "),
        ("Product intent", " "),
    ),
)
def test_prompt_source_recovers_explicit_intent_before_source_metadata(label: str, delimiter: str) -> None:
    source = prompt_intent_source(
        f"Create an accessibility product.{delimiter}{label}: A program lead registers a readiness dossier, "
        "selects a review disposition, and verifies a publication status. "
        "Source evidence: Accessibility evidence only."
    )

    assert source.actor == "program lead"
    assert source.first_path == (
        "A program lead registers a readiness dossier, selects a review disposition, and verifies a publication status"
    )


def test_prompt_source_normalizes_a_standalone_explicit_intent_label() -> None:
    source = prompt_intent_source(
        "User intent: A waiver reviewer opens a waiver record, records a decision, and verifies a visible status."
    )

    assert source.actor == "waiver reviewer"
    assert source.first_path == "A waiver reviewer opens a waiver record, records a decision, and verifies a visible status"


@pytest.mark.parametrize(
    ("prompt", "actor"),
    (
        ("User intent: A waiver reviewer opens a waiver record, records a decision, and verifies a visible status.", "waiver reviewer"),
        ("User intent: A record owner opens a record, records a decision, and verifies a visible status.", "record owner"),
    ),
)
def test_prompt_source_keeps_role_qualified_nonhuman_nouns_as_human_actors(prompt: str, actor: str) -> None:
    assert prompt_intent_source(prompt).actor == actor


def test_source_evidence_tail_never_becomes_product_truth() -> None:
    for boundary in ("-", ";", ":", ","):
        for label_separator in (":", "-"):
            prompt = (
                "Create an evidence review workspace. An operator reviews one evidence item, records a decision, "
                f"and verifies the visible outcome {boundary} Source evidence {label_separator} accessible component "
                "library with keyboard support and ARIA patterns."
            )

            source = prompt_intent_source(prompt)
            intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

            assert source.first_path.startswith("An operator reviews one evidence item")
            assert "accessible component library" not in source.first_path
            assert "accessible component library" not in json.dumps(intent, sort_keys=True).casefold()


def test_repository_description_workflow_stays_evidence_not_product_truth() -> None:
    prompt = (
        "Create an evidence review workspace. Repository description: An operator reviews one evidence item, "
        "records a decision, and verifies the visible outcome."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.title == "evidence review workspace"
    assert "one evidence item" not in source.first_path
    rendered = json.dumps(intent, sort_keys=True)
    assert "one evidence item" not in rendered
    assert "Repository description" not in rendered


@pytest.mark.parametrize(
    "label",
    ("Source evidence", "Source repository", "Repository description"),
)
def test_source_metadata_only_requires_a_first_path_question(label: str, tmp_path) -> None:
    prompt = (
        f"{label}: An operator reviews one evidence item, records a decision, and verifies the visible outcome."
    )

    source = prompt_intent_source(prompt)

    assert source.title == ""
    assert source.first_path == ""
    with pytest.raises(GreenfieldClarificationRequired, match="first complete task"):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="",
        )


@pytest.mark.parametrize(
    "prompt",
    (
        "Create an evidence replay workspace where an operator can replay one recorded case.",
        "Create a case review workspace where an operator can inspect one case.",
        "Create a radiology review workspace where a reviewer verifies the visible case status.",
    ),
)
def test_one_step_actor_path_requires_a_first_path_question_before_staging(prompt: str, tmp_path) -> None:
    with pytest.raises(GreenfieldClarificationRequired, match="first complete task"):
        materialize_prompt_intent_hypothesis(
            prompt=prompt,
            repo_root=tmp_path,
            fallback_title="",
        )


def test_recovered_workable_prompt_does_not_invent_open_questions() -> None:
    prompt = (
        "Create an accessibility product. An accessibility operator reviews one evidence item, records a decision, "
        "and verifies the visible outcome."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )

    assert intent["ambiguities"] == []
    assert proposal["open_questions"] == []


def test_unstructured_prompt_parsing_keeps_source_metadata_out_of_accepted_fields() -> None:
    prompt = (
        "Create an accessibility product. An accessibility operator reviews one evidence item, records a decision, "
        "and verifies the visible outcome. Source repository: tailwindlabs/headlessui. "
        "Source evidence: Accessible UI components for Tailwind CSS."
    )

    intent = parse_confirmed_intent_text(prompt, prompt=prompt)

    assert all(
        "tailwindlabs/headlessui" not in str(intent[field])
        for field in ("product_story", "first_path", "prompt")
    )


def test_confirmed_first_path_keeps_evidence_review_without_raw_repository_identifier() -> None:
    intent = parse_confirmed_intent_text(
        """# Accessibility Review Workspace

## Product Story
This workspace helps accessibility operators turn component evidence into reviewable release decisions.

## State Object
An accessibility review records evidence, one decision, the resulting outcome, and traceable proof.

## First Complete Path
An operator reviews evidence from unovue/reka-ui, records one accessibility decision, and verifies the resulting outcome.

## Proof Boundary
The evidence, decision, and verified outcome remain traceable for release review.
"""
    )

    assert "unovue/reka-ui" not in intent["first_path"]
    assert "reviews source evidence" in intent["first_path"].casefold()


def test_confirmed_first_path_redacts_repository_after_review_verb() -> None:
    intent = parse_confirmed_intent_text(
        """# Accessibility Review Workspace

## Product Story
This workspace helps accessibility operators turn component evidence into reviewable release decisions.

## State Object
An accessibility review records evidence, one decision, the resulting outcome, and traceable proof.

## First Complete Path
An operator reviews repository tailwindlabs/headlessui, records one accessibility decision, and verifies the resulting outcome.

## Proof Boundary
The evidence, decision, and verified outcome remain traceable for release review.
"""
    )

    assert "tailwindlabs/headlessui" not in intent["first_path"]
    assert "reviews source evidence" in intent["first_path"].casefold()


def test_prompt_source_preserves_for_who_actor_role() -> None:
    prompt = (
        "Create a quantum tunneling lab planning workspace for experimental physicists who coordinate "
        "wafer batches, cryostat windows, calibration drift, and publication-ready anomaly evidence."
    )

    source = prompt_intent_source(prompt)

    assert source.title == "quantum tunneling lab planning workspace"
    assert source.first_path.startswith("experimental physicists who coordinate")
    assert "workspace user" not in source.first_path.casefold()


def test_host_guidance_recovery_keeps_for_who_actor_role_out_of_workspace_user_fallback(tmp_path) -> None:
    prompt = (
        "Create a quantum tunneling lab planning workspace for experimental physicists who coordinate "
        "wafer batches, cryostat windows, calibration drift, and publication-ready anomaly evidence."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"][0].startswith("Experimental Physicists:")
    assert "Experimental physicists can coordinate wafer batches" in rendered
    assert "Quantum Tunneling Lab Planning Workspace User" not in rendered
    assert "workspace user" not in rendered.casefold()
    assert greenfield_quality_issues(completed) == []


def test_host_guidance_recovery_rejects_action_chain_prefix_as_actor(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for water-rights hearing evidence preparation where legal aides organize "
        "diversion records, tribal consultation notes, drought restrictions, expert exhibits, and filing deadlines "
        "into a reviewable hearing packet."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"] == [
        "Legal Aides: need the product to organize diversion records, tribal consultation notes, drought restrictions, "
        "expert exhibits, and filing deadlines into a reviewable hearing packet and keep the result visible and reviewable"
    ]
    assert "Legal Aides Organize Diversion" not in rendered
    assert "can organizes" not in rendered
    assert greenfield_quality_issues(completed) == []


def test_host_guidance_recovery_isolates_original_intent_from_full_propose_envelope() -> None:
    prompt = (
        "Build a greenfield proposal for an orbital debris conjunction review workspace. "
        "The first release should let mission analysts capture predicted close approaches, "
        "sensor confidence, maneuver constraints, communications approvals, rejected interpretations, "
        "and review proof without commanding satellites or changing flight plans."
    )
    envelope = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
- Render the visible confirmation as sectioned Markdown in this order: Product story; State object; First complete path; Human actors; External systems; Internal product systems; Critical assumptions; Ambiguities; Proof boundary; Next step.

Write in chat
- product title, Product story, State object, and First complete path
- Human actors, External systems, and Internal product systems

Do not
- dump a generic template or domain catalog

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, compile the ProductCreateTransaction, then commit the matching hash.
Compile transaction: odylith greenfield compile-transaction --repo-root . --prompt '{prompt}' --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1
Commit transaction after hash confirmation: odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm
"""

    intent = parse_confirmed_intent_text(envelope, prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Orbital Debris Conjunction Review Workspace"
    assert "mission analysts capture predicted close approaches" in intent["first_path"].casefold()
    assert 2 <= len(intent["internal_systems"]) <= 4
    assert any("Close Approach" in row and "Intake" in row for row in intent["internal_systems"])
    assert any("Review" in row for row in intent["internal_systems"])
    assert "Next step" not in rendered
    assert "Confirmed CLI" not in rendered
    assert "visible format contract" not in rendered.casefold()
    assert "complete when" not in intent["proof_boundary"].casefold()
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_uses_user_actor_for_action_only_first_path() -> None:
    prompt = (
        "Create a greenfield product for wearable-informed lab recovery teams that ingest device data, "
        "lab measurements, training context, consent posture, and safety limits, then show a clear change "
        "explanation without making diagnosis claims."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert prompt_project_title_source(prompt) == "wearable-informed lab recovery teams"
    assert intent["title"] == "Wearable-informed Lab Recovery Teams Workspace"
    assert "The product ingest" not in intent["first_path"]
    assert "The product ingest" not in rendered
    assert "Product for Wearable-informed" not in rendered
    assert "can ingest device data" in intent["first_path"]
    assert "clear change explanation without making diagnosis claims" in rendered


def test_host_guidance_recovery_does_not_invent_modal_actor_from_can_path() -> None:
    prompt = (
        "Create a greenfield product for wearable-informed lab recovery teams that can ingest motion sensor recovery entries, "
        "therapist consent notes, and adverse symptom check-ins, then show clear what changed insights, access-safe escalation tasks, "
        "and a release evidence report without making medical diagnosis or personalized treatment claims."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Wearable-informed Lab Recovery Teams Workspace"
    assert intent["human_actors"][0].startswith("Wearable-informed Lab Recovery Teams:")
    assert "need the product to ingest motion sensor recovery entries" in intent["human_actors"][0]
    assert "Can:" not in rendered
    assert "a can can" not in rendered.casefold()
    assert "Can needs" not in rendered
    assert "where can ingest" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_carries_actor_across_coordinated_action_clauses(tmp_path) -> None:
    prompt = (
        "Create a wearable health escalation review app where care coordinators inspect patient-generated trend evidence, "
        "separate urgent review from routine coaching, preserve consent-aware notes, and give clinicians a clear escalation "
        "packet for review."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["first_path"] == (
        "Care coordinators inspect patient-generated trend evidence. "
        "Care coordinators separate urgent review from routine coaching. "
        "Care coordinators preserve consent-aware notes. "
        "Care coordinators give clinicians a clear escalation packet for review."
    )
    assert intent["human_actors"] == [
        "Care Coordinators: need the product to inspect patient-generated trend evidence and keep the result visible and reviewable"
    ]
    assert "Separate Urgent" not in rendered
    assert "Separate urgent preserves" not in rendered
    assert "Clear Escalation Packet Clear" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_keeps_open_source_out_of_adapter_classification(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for an open source security embargo room that receives vulnerability reports, "
        "coordinates maintainer triage, tracks affected package evidence, records disclosure approvals, and shows "
        "advisory readiness without sending public announcements in the first release."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
        require_completion_ready=False,
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Open Source Security Embargo Room"
    assert "The product receive" not in rendered
    assert "open source security embargo room user can receive vulnerability reports" in rendered.casefold()
    assert "an open source security embargo room can receive vulnerability reports" not in rendered.casefold()
    assert "normalized result" not in rendered.casefold()
    assert "normalized output" not in rendered.casefold()
    assert all(not str(row["label"]).endswith(" Adapter") for row in proposal["components"])
    assert greenfield_quality_issues(proposal) == []


def test_operator_intent_recovery_visible_confirmation_keeps_sequence_and_actor_readable() -> None:
    prompt = (
        "Create a greenfield product for wearable-informed lab recovery teams that ingest device data, "
        "lab measurements, training context, consent posture, and safety limits, then show a clear change "
        "explanation without making diagnosis claims."
    )

    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)

    assert "# Wearable-informed Lab Recovery Teams Workspace - Product Intent Confirmation" in text
    assert "Wearable-informed Lab Recovery Teams Workspace User" not in text
    assert "workspace user" not in text.casefold()
    assert ",. show" not in text
    assert "lab recovery teams can ingest device data" in text.casefold()
    assert "then show a clear change explanation without making diagnosis claims" in text


def test_operator_intent_recovery_splits_product_view_result_sentence_for_model_use_recommendation() -> None:
    prompt = (
        "Create a greenfield proposal for AI hiring model adverse impact. Focus on a governed workflow where the "
        "algorithmic accountability auditor turns an ambiguous hiring model review case into a review-ready record "
        "using selection-rate evidence, feature documentation, validation study, and accommodation notes, explicit "
        "expert review, auditable decisions, and a final model use recommendation."
    )

    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    intent = parse_confirmed_intent_text(text, prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    payload = build_accepted_project_source_payload(
        proposal=proposal,
        backlog_items=(),
        component_items=(),
        diagram_ids=(),
        release_selector="0.0.1",
        release_id="0.0.1",
        validation_gate={"status": "passed"},
    )

    assert "final model use recommendation. The result remains visible" in text
    assert "model use recommendation and the result" not in text
    assert generated_public_copy_issues("accepted-project final memory", payload) == ()


def test_operator_intent_recovery_does_not_canonize_actorless_action_chain_as_subject() -> None:
    prompt = (
        "Create a greenfield proposal for a space telescope calibration anomaly review tool that ingests "
        "observation runs, records instrument state, tracks calibration exceptions, routes science lead review, "
        "and publishes release readiness for validated image products."
    )

    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    lowered = text.casefold()

    assert "record instrument state" in lowered
    assert "track calibration exceptions" in lowered
    assert "route science lead review" in lowered
    assert "publish release readiness for validated image products" in lowered
    assert "ingest observation records" not in lowered
    assert "ingest observation tracks" not in lowered
    assert "ingest observation routes" not in lowered
    assert "routes science lead publishes" not in lowered


def test_scientific_model_prompt_recovery_preserves_evaluation_depth(tmp_path) -> None:
    prompt = "Draft a product-first greenfield proposal for building an AI-model that simulates gene expression prediction."

    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert "# Gene Expression Prediction Model Workspace - Product Intent Confirmation" in text
    assert "Building an AI Model Workspace" not in text
    for phrase in (
        "source data",
        "method or model version",
        "baseline or reference comparison",
        "uncertainty or confidence",
        "reproducibility evidence",
        "must not claim scientific truth",
    ):
        assert phrase in text
    assert intent["title"] == "Gene Expression Prediction Model Workspace"
    assert "gene expression prediction result with uncertainty and comparison evidence" in intent["first_path"]
    assert proposal["semantic_model"]["evaluation_semantics"]["focus"] == "Gene Expression Prediction Model"
    assert "baseline or comparison evidence" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_scientific_recovery_keeps_quantify_as_carried_actor_action() -> None:
    prompt = (
        "Create a greenfield proposal for a geophysics research platform where field scientists ingest "
        "seismic survey traces, compare inversion models against calibration wells, quantify uncertainty "
        "bands around subsurface velocity estimates, preserve parameter-set provenance, and let a principal "
        "investigator approve a reproducible interpretation package without claiming drilling certainty."
    )

    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    lowered = text.casefold()

    assert "field scientists ingest seismic survey traces" in lowered
    assert "quantify uncertainty bands around subsurface velocity estimates" in lowered
    assert "quantify uncertainty bands around subsurface velocity:" not in lowered
    assert "needs the product to preserve parameter-set provenance" not in lowered
    assert "product to quantify uncertainty bands around" not in lowered


def test_scientific_recovery_preserves_loaded_measurement_source_step() -> None:
    prompt = (
        "Create a greenfield proposal for a biomedical engineering review platform where researchers load "
        "orthopedic implant fatigue-test measurements, compare finite-element simulations against bench-test controls, "
        "track mesh and material parameters, capture tolerance bands and failure modes, and let a review board approve "
        "an evidence package without making clinical safety claims."
    )

    source = prompt_intent_source(prompt)
    model = first_path_model(source.first_path)
    text = confirmation_from_operator_intent(prompt, prefer_product_title=True)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()
    lowered = text.casefold()

    assert model.steps[0] == "Researchers load orthopedic implant fatigue-test measurements"
    assert source.first_path.casefold().startswith("researchers load orthopedic implant fatigue-test measurements")
    assert "load orthopedic implant fatigue-test measurements" in lowered
    assert "compare finite-element simulations against bench-test controls" in lowered
    assert "track mesh and material parameters" in lowered
    assert "capture tolerance bands and failure modes" in lowered
    assert "method version" not in lowered
    assert "reproducibility evidence" not in lowered
    assert "fatigue-test measurements" in rendered
    assert "finite-element simulations against bench-test controls" in rendered
    assert proposal["semantic_model"]["evaluation_semantics"]["focus"] == "Biomedical Engineering Review Platform"
    assert greenfield_quality_issues(proposal) == []


def test_operator_edited_confirmed_intent_wins_over_prompt_material_restore() -> None:
    prompt = (
        "Create a greenfield proposal for a biomedical engineering review platform where researchers load "
        "orthopedic implant fatigue-test measurements, compare finite-element simulations against bench-test controls, "
        "track mesh and material parameters, capture tolerance bands and failure modes, and let a review board approve "
        "an evidence package without making clinical safety claims."
    )
    edited_confirmation = """
# Biomedical Engineering Review Platform - Product Intent Confirmation

Product story
Biomedical Engineering Review Platform helps review boards compare simulation evidence against bench controls after source intake is handled elsewhere.

State object
A finite-element simulations against bench-test controls record tracks the actor, source input, status, owner, evidence, and version history.

First complete path
A biomedical engineering review platform user can compare finite-element simulations against bench-test controls. Track mesh and material parameters. Capture tolerance bands and failure modes. Let a review board approve an evidence package without making clinical safety claims.

Human actors
- Biomedical Engineering Review Platform User: needs the product to complete the first path and keep the result visible and reviewable

Internal product systems
- Biomedical Engineering Review Platform Intake Register — records source input and version history
- Biomedical Engineering Review Platform Review Workspace — presents current state and next action
- Biomedical Engineering Review Platform Proof Ledger — keeps validation results and replayable evidence

Proof boundary
Release 0.0.1 succeeds when the accepted first path is complete and the finite-element simulations against bench-test controls remain reviewable.
""".strip()

    intent = parse_confirmed_intent_text(edited_confirmation, prompt=prompt)

    assert "load orthopedic implant fatigue-test measurements" not in intent["first_path"].casefold()
    assert "compare finite-element simulations against bench-test controls" in intent["first_path"].casefold()
    assert "track mesh and material parameters" in intent["first_path"].casefold()


def test_evaluation_semantics_do_not_overfire_on_plain_research_or_benchmark_words() -> None:
    assert (
        evaluation_semantics_for_texts(
            title="Research recruitment workspace",
            state_object="Candidate outreach record",
            first_path="Recruiter reviews applicants and schedules interviews.",
            proof_boundary="One recruiter can review a candidate.",
            prompt="Create a research recruitment workspace for hiring coordinators.",
        )
        is None
    )
    assert (
        evaluation_semantics_for_texts(
            title="Clinical benchmark dashboard",
            state_object="Operations benchmark record",
            first_path="Coordinator opens a dashboard and reviews clinic throughput.",
            proof_boundary="One benchmark view opens for an operations reviewer.",
            prompt="Create a clinical benchmark dashboard for operations teams.",
        )
        is None
    )


def test_command_led_scientific_title_wrapper_returns_stripped_title() -> None:
    text = confirmation_from_operator_intent(
        "Draft a greenfield proposal for building an assay drift prediction model.",
        prefer_product_title=True,
    )

    assert "# Assay Drift Prediction Model Workspace - Product Intent Confirmation" in text
    assert "Building An Assay Drift Prediction Model" not in text


def test_prompt_title_source_recognizes_generic_product_containers() -> None:
    assert (
        prompt_project_title_source(
            "Create a greenfield product for field evidence coordinators that collect photos, notes, and review proof."
        )
        == "field evidence coordinators"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a cooking robot controller where a home cook chooses a recipe."
        )
        == "cooking robot controller"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a cooking robot controller")
        == "cooking robot controller"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a solar energy installation planning hub")
        == "solar energy installation planning hub"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a clinic follow-up coordination desk")
        == "clinic follow-up coordination desk"
    )
    assert (
        prompt_project_title_source("Draft a greenfield proposal for a warehouse slotting planner")
        == "warehouse slotting planner"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a contract redline review room where reviewers compare clauses."
        )
        == "contract redline review room"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a dispatch evidence console where coordinators review handoffs."
        )
        == "dispatch evidence console"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a classroom lab safety tracker where teachers prepare experiments."
        )
        == "classroom lab safety tracker"
    )
    assert (
        prompt_project_title_source(
            "Draft a greenfield proposal for a digestive health tracking notebook where a person records meals."
        )
        == "digestive health tracking notebook"
    )
    assert (
        prompt_project_title_source(
            "Create a greenfield product for tenant aid coordinators who intake housing requests and prepare approval packets."
        )
        == "tenant aid coordinators"
    )
    mrna_prompt = (
        "Create a greenfield proposal for mRNA stability batch comparison. Focus on a governed workflow where "
        "the formulation scientist turns an ambiguous mRNA stability batch comparison case into a review-ready record."
    )
    assert prompt_project_title_source(mrna_prompt) == "mRNA stability batch comparison"
    assert greenfield_proposals.intent_title(mrna_prompt) == "mRNA Stability Batch Comparison"
    planned = prompt_intent_source(
        "Plan a new exception review cockpit for operations teams that tracks evidence, review holds, "
        "decision outcomes, exception notes, and release proof."
    )
    assert planned.title == "exception review cockpit"
    assert planned.actor == "operations teams"
    assert planned.first_path == (
        "operations teams track evidence, review holds, decision outcomes, exception notes, and release proof"
    )
    rendered = confirmation_from_operator_intent(
        "Plan a new exception review cockpit for operations teams that tracks evidence, review holds, "
        "decision outcomes, exception notes, and release proof.",
        prefer_product_title=True,
    )
    assert "# Exception Review Cockpit Workspace - Product Intent Confirmation" in rendered
    assert (
        "Operations Teams: need the product to track evidence, review holds, decision outcomes, exception notes, and release proof"
        in rendered
    )
    assert "Review Holds:" not in rendered


def test_prompt_source_rejects_non_human_result_subject_before_transformation() -> None:
    prompt = "incident board where the final recommendation turns an ambiguous incident into a review-ready record"

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert source.actor == ""
    assert "Final Recommendation:" not in "\n".join(intent["human_actors"])


def test_single_step_action_only_paths_do_not_satisfy_completion_or_validation() -> None:
    weak_paths = (
        "reviewer capture notes, approvals, and status",
        "screening scientist record replicate, viability, and off-target evidence",
    )

    for first_path in weak_paths:
        intent = {
            "first_path": first_path,
            "product_story": first_path,
            "state_object": "A result record tracks evidence.",
            "proof_boundary": "Proof shows the accepted path.",
        }
        assert not _first_path_is_complete_enough(first_path)
        assert not _first_path_is_clear_enough(intent)


def test_command_led_sentence_target_preserves_domain_frame_without_container(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for weather radar calibration setup. "
        "The product should let a meteorologist manage a radar scan, preserve beam blockage evidence, "
        "route review, separate product-domain terms from platform governance language, and publish calibration decision."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "weather radar calibration setup"
    assert intent["title"] == "Weather Radar Calibration Setup Workspace"
    assert "weather radar calibration setup workspace" in rendered
    assert "meteorologist manage a radar scan" in rendered
    assert "beam blockage evidence" in rendered
    assert "Calibration Decision Workspace" not in json.dumps(proposal, sort_keys=True)
    assert greenfield_quality_issues(proposal) == []


def test_command_led_platform_homonym_target_preserves_project_domain_frame(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for geologic atlas field mapping setup. "
        "The product should let a field geologist manage a map sheet, preserve stratigraphy evidence, "
        "route review, separate product-domain terms from platform governance language, and publish mapping release."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "geologic atlas field mapping setup"
    assert intent["title"] == "Geologic Atlas Field Mapping Setup Workspace"
    assert "geologic atlas field mapping setup workspace" in rendered
    assert "field geologist manage a map sheet" in rendered
    assert "stratigraphy evidence" in rendered
    assert "Mapping Release Workspace" not in json.dumps(proposal, sort_keys=True)
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_preserves_infinitive_after_use_to_instead_of_can_rewrite() -> None:
    prompt = (
        "Create a greenfield product for kitchen robot controllers that home cooks use to choose recipes, "
        "adjust portions, and start cooking runs."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "kitchen robot controllers"
    assert "home cooks choose recipes" in source.first_path
    assert "use to choose" not in source.first_path
    assert "use can choose" not in source.first_path
    assert "home cooks choose recipes" in rendered
    assert "home cooks use can choose" not in rendered
    assert "home cooks use:" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_prompt_intent_source_splits_direct_product_title_from_first_path() -> None:
    source = prompt_intent_source(
        "factory line changeover readiness board where supervisors verify tooling, materials, safety checks, and restart approval"
    )

    assert source.title == "factory line changeover readiness board"
    assert source.first_path == "supervisors verify tooling, materials, safety checks, and restart approval"
    assert not source.command_led
    assert (
        prompt_project_title_source(
            "collaborative robot safety case builder where engineers map hazards, mitigations, validation tests, and release signoff evidence"
        )
        == "collaborative robot safety case builder"
    )
    assert (
        prompt_project_title_source(
            "customer data retention policy executor where privacy teams classify records, schedule deletions, and prove exceptions are approved"
        )
        == "customer data retention policy executor"
    )


def test_host_guidance_recovery_handles_direct_product_for_actor_gerund_path(tmp_path) -> None:
    prompt = (
        "orbital operations coordination for satellite operators receiving conjunction warnings, "
        "calculating maneuver options, recording operator signoff, fuel constraints, regulator notice evidence, "
        "and post-event readiness proof without autonomously commanding thrusters"
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "orbital operations coordination"
    assert source.first_path.startswith("satellite operators receiving conjunction warnings")
    assert intent["title"] == "Orbital Operations Coordination"
    assert intent["human_actors"][0].startswith("Satellite Operators:")
    assert "satellite operators can receive conjunction warnings" in rendered
    assert "representative user reviews satellite operators receiving" not in rendered
    assert "options recording operator" not in rendered
    assert "gerundized actor-role action leaked" not in "\n".join(greenfield_quality_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_handles_helper_relative_embedded_actor_path() -> None:
    prompt = (
        "Create a greenfield proposal for a performing arts safety rehearsal planner that lets a stage manager "
        "record stunt cues, map performer clearance evidence, track prop inspection exceptions, coordinate medical "
        "standby signoff, and publish rehearsal readiness before opening night."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "performing arts safety rehearsal planner"
    assert source.actor == "stage manager"
    assert source.first_path.startswith("stage manager record stunt cues")
    assert intent["human_actors"][0].startswith("Stage Manager:")
    assert "stage manager can record stunt cues" in rendered
    assert "performing arts safety rehearsal planner let a stage manager" not in rendered
    assert "gerundized actor-role action leaked" not in "\n".join(greenfield_quality_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_recovers_actor_from_complete_path_grant() -> None:
    prompt = (
        "Create a greenfield proposal for crispr screen reproducibility. The first release should give the "
        "screening scientist a complete path to open the guide RNA result set, record replicate, viability, "
        "and off-target evidence, escalate assay review, resolve exceptions, and publish the reproducibility "
        "decision without automating expert judgment."
    )

    source = prompt_intent_source(prompt)
    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert source.title == "crispr screen reproducibility"
    assert source.actor == "screening scientist"
    assert source.first_path.startswith("screening scientist open the guide RNA result set")
    assert "record replicate, viability, and off-target evidence" in source.first_path
    assert intent["human_actors"][0].startswith("Screening Scientist:")
    assert "Release Should:" not in "\n".join(intent["human_actors"])
    assert "Escalate Assay:" not in "\n".join(intent["human_actors"])
    assert "screening scientist can open the guide rna result set" in rendered
    assert "modal/base-form grammar drift" not in "\n".join(greenfield_quality_issues(proposal))
    assert greenfield_quality_issues(proposal) == []


def test_prompt_source_recovers_analyst_actor_from_complete_path_grant() -> None:
    prompts = (
        (
            "exoplanet transit vetting",
            "astronomy analyst",
            "candidate transit dossier",
            "science review",
            "planet-candidate disposition",
        ),
        (
            "seismic microtremor mapping",
            "geophysics analyst",
            "microtremor survey",
            "hazard review",
            "site amplification map",
        ),
        (
            "space debris conjunction",
            "orbital safety analyst",
            "conjunction assessment",
            "flight dynamics review",
            "avoidance recommendation",
        ),
    )

    for title, actor, entry_object, review, result in prompts:
        prompt = (
            f"Create a greenfield proposal for {title}. The first release should give the {actor} "
            f"a complete path to open the {entry_object}, record source, evidence, and review context, "
            f"escalate {review}, resolve exceptions, and publish the {result} without automating expert judgment."
        )

        source = prompt_intent_source(prompt)
        intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
        proposal = build_confirmed_greenfield_proposal(
            prompt=prompt,
            title=intent["title"],
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=confirmed_mapping_with_authority(intent),
        )
        rendered = json.dumps(proposal, sort_keys=True).casefold()

        assert source.title == title
        assert source.actor == actor
        assert source.first_path.startswith(f"{actor} open the {entry_object}")
        assert intent["human_actors"][0].startswith(" ".join(word.capitalize() for word in actor.split()) + ":")
        assert "Release Should:" not in "\n".join(intent["human_actors"])
        assert f"the {actor} can open the {entry_object}" in rendered
        assert "the release should can" not in rendered
        assert "the release should receives" not in rendered
        assert "modal/base-form grammar drift" not in "\n".join(greenfield_quality_issues(proposal))
        assert greenfield_quality_issues(proposal) == []


def test_shard06_workflow_prompts_prefer_complete_actor_role_before_action() -> None:
    prompts = [
        (
            "Create a greenfield proposal for municipal stormwater illicit discharge. Focus on a governed workflow where "
            "the stormwater inspector turns an ambiguous illicit discharge case into a review-ready record using outfall, "
            "sample, and rainfall evidence, explicit enforcement review, auditable decisions, and a final discharge "
            "resolution plan.",
            "stormwater inspector",
            ("stormwater can inspector", "can inspector turns"),
        ),
        (
            "Create a greenfield proposal for tribal consultation tracker. Focus on a governed workflow where the "
            "government liaison turns an ambiguous consultation commitment into a review-ready record using meeting, "
            "cultural-resource, and response evidence, explicit policy review, auditable decisions, and a final "
            "consultation status report.",
            "government liaison",
            ("government can liaison", "can liaison turns"),
        ),
    ]

    for prompt, actor, forbidden in prompts:
        source = prompt_intent_source(prompt)
        intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
        proposal = build_confirmed_greenfield_proposal(
            prompt=prompt,
            title=intent["title"],
            observed_source={},
            release_selector="0.0.1",
            confirmed_intent=confirmed_mapping_with_authority(intent),
        )
        rendered = json.dumps(proposal, sort_keys=True).casefold()

        assert source.actor == actor
        assert source.first_path.startswith(f"{actor} turn")
        assert actor.title() + ":" in "\n".join(intent["human_actors"])
        for phrase in forbidden:
            assert phrase not in rendered
        assert "modal/base-form grammar drift" not in "\n".join(greenfield_quality_issues(proposal))
        assert greenfield_quality_issues(proposal) == []


def test_confirmed_proposal_preserves_long_scientific_decision_phrase_without_dangling_tail() -> None:
    prompt = (
        "Create a greenfield proposal for rare disease variant board. Focus on a governed workflow where the "
        "genomics counselor turns an ambiguous variant interpretation case into a review-ready record using "
        "phenotype, segregation, and ACMG evidence, explicit variant board, auditable decisions, and a final "
        "classification recommendation."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert "final classification recommendation" in rendered
    assert "auditable decisions and a final." not in rendered
    assert "and a final. follow-up evidence" not in rendered
    assert "the genomics counselor can turn an ambiguous variant interpretation case" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_preserves_leading_purpose_context_before_actions() -> None:
    prompt = (
        "municipal water utility planner for lead service-line abatement; intake household records, "
        "prioritize vulnerable sites, coordinate contractor windows, preserve lab sample evidence, "
        "track resident access constraints, and publish block readiness without claiming regulatory certification"
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True).casefold()

    assert "lead service-line abatement" in intent["first_path"].casefold()
    assert "lead service-line abatement" in rendered
    assert "preserve lab sample evidence" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_keeps_direct_where_prompt_title_instead_of_terminal_outcome() -> None:
    prompt = (
        "factory line changeover readiness board where supervisors verify tooling, materials, "
        "safety checks, and restart approval"
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Factory Line Changeover Readiness Board"
    assert "supervisors verify tooling" in intent["first_path"].casefold()
    assert "the and restart approval" not in rendered
    assert "And Restart Approval Workspace" not in rendered
    assert "tooling record" in intent["state_object"].casefold()
    assert any("Tooling Workflow Support" in row for row in intent["internal_systems"])
    assert any("Restart Approval" in row for row in intent["internal_systems"])
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_uses_original_intent_over_visible_format_instructions() -> None:
    prompt = (
        "Draft a greenfield proposal for a digestive health tracking notebook where a person records meals, "
        "symptoms, timing, triggers, and a reviewable pattern summary without making diagnosis claims."
    )
    envelope = f"""Product Intent Confirmation needed
No files changed. Source posture: empty_or_no_app_source.

Host reasoning task: Infer the product shape live from the operator prompt and any observed repo source.

Visible format contract
Product story
State object
First complete path
Human actors
External systems
Internal product systems
Proof boundary

Original user intent
{prompt}
Next step
- Confirm: write this same visible Product Intent Confirmation to .odylith/runtime/greenfield/confirmed-intent.md, compile the ProductCreateTransaction, then commit the matching hash.
Compile transaction: odylith greenfield compile-transaction --repo-root . --prompt "{prompt}" --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release 0.0.1
Commit transaction after hash confirmation: odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm
"""

    intent = parse_confirmed_intent_text(envelope, prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Digestive Health Tracking Notebook"
    assert "record meals, symptoms" in intent["first_path"].casefold()
    assert len(intent["internal_systems"]) == 2
    assert any("Meals Recordkeeping" in row for row in intent["internal_systems"])
    assert any("Result Review" in row for row in intent["internal_systems"])
    assert all("visible format" not in row.casefold() for row in intent["internal_systems"])
    assert "post-confirm repair loop" not in rendered.casefold()
    assert "product intent confirmation needed" not in rendered.casefold()
    assert "Visible Format Contract" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_preserves_explicit_system_rows_through_completion() -> None:
    prompt = (
        "Create a greenfield proposal for a clinical trial consent and adverse-event triage workspace that lets "
        "research nurses verify participant consent, capture symptom evidence, route investigator safety review, "
        "preserve audit-ready decisions, and release a first-slice monitoring report without automating medical diagnosis."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Clinical Trial Consent and Adverse Event Triage Workspace"
    assert intent["human_actors"] == [
        "Research Nurses: need the product to verify participant consent and keep the result visible and reviewable"
    ]
    assert len(intent["internal_systems"]) == 5
    assert any("Participant Consent Workflow Support" in row for row in intent["internal_systems"])
    assert any("Symptom Evidence Intake" in row for row in intent["internal_systems"])
    assert any("Investigator Safety Review Workflow Support" in row for row in intent["internal_systems"])
    assert any("Audit-ready Decisions" in row for row in intent["internal_systems"])
    assert any("Monitoring Report Delivery" in row for row in intent["internal_systems"])
    assert "component responsibility named by the accepted intent" not in rendered
    assert "Release a First-slice Monitoring" not in rendered
    assert "medical diagnosis" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_builds_clean_confirmed_proposal_from_controller_prompt() -> None:
    prompt = (
        "Draft a greenfield proposal for a cooking robot controller where a home cook chooses a recipe, "
        "the controller sequences heat and motion, and safety proof must stop the run when sensors disagree."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Cooking Robot Controller"
    assert intent["human_actors"] == [
        "Home Cook: needs the product to choose a recipe and keep the result visible and reviewable"
    ]
    assert "Recovered Product Workspace" not in rendered
    assert "needs a dependable way to understand" not in rendered
    assert "Only accepted actors or systems can move first-path state: A." not in rendered
    assert "the cooking Robot Controller result" not in rendered
    assert "the cooking robot controller result" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_nominalizes_actor_led_state_outcomes() -> None:
    prompt = (
        "Build a research replication package tracker where a principal investigator registers datasets, "
        "analysts attach reproducibility evidence, reviewers flag missing methods, and the lab publishes "
        "a clean audit trail before submission."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    state = intent["state_object"]

    assert state.startswith("The primary state object is a dataset.")
    assert "A Reviewers flag" not in state
    assert "A reviewers flag" not in state


def test_host_guidance_recovery_lowercases_generated_state_article_body() -> None:
    prompt = (
        "Build a hospital equipment sterilization handoff board where technicians log tray readiness, "
        "nurses reserve urgent kits, supervisors verify failed-cycle evidence, and operating rooms see "
        "only safe release status."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)

    assert intent["state_object"].startswith("The primary state object is a tray readiness record.")
    assert "An Only" not in intent["state_object"]


def test_host_guidance_recovery_handles_broad_product_prompt_without_parser_debris() -> None:
    prompt = "Draft a greenfield proposal for a cooking robot controller"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Cooking Robot Controller"
    assert intent["first_path"] == (
        "A representative user reviews cooking robot controller details, records the current status, "
        "and sees a cooking robot controller result with blockers and evidence for review."
    )
    assert intent["human_actors"] == [
        "Representative User: needs the product to review cooking robot controller details and keep the result visible and reviewable"
    ]
    assert intent["state_object"].startswith("The primary state object is a cooking robot controller result.")
    assert "the cooking robot controller result" in rendered
    assert "A a " not in rendered
    assert "A the " not in rendered
    assert "where A " not in rendered
    assert "Provides:" not in rendered
    assert "Reviews:" not in rendered
    assert "First Participant" not in rendered
    assert "Recovered Product Workspace" not in rendered
    assert "Cooking Robot Controller Participant review" not in rendered
    assert "sequence/parser debris" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_rejects_long_title_noun_as_first_path() -> None:
    prompt = "Draft a greenfield proposal for a solar energy installation planning hub"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Solar Energy Installation Planning Hub"
    assert intent["first_path"].startswith(
        "A representative user reviews solar energy installation planning details"
    )
    assert "when a solar energy installation planning hub." not in intent["proof_boundary"]
    assert intent["human_actors"] == [
        "Representative User: needs the product to review solar energy installation planning details and keep the result visible and reviewable"
    ]
    assert "sequence/parser debris" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_strips_release_proof_tail_from_first_path() -> None:
    prompt = (
        "Draft a product-first greenfield proposal for a rooftop solar planning workspace where a homeowner "
        "captures roof details, utility constraints, installer options, incentive paperwork, design review, "
        "and installation readiness before release 0.0.1 proves one complete solar project planning path."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Rooftop Solar Planning Workspace"
    assert "roof details" in intent["first_path"].casefold()
    assert "installation readiness" in intent["first_path"].casefold()
    assert "0.0.1 proves" not in intent["first_path"]
    assert "one complete solar project planning path" not in intent["state_object"].casefold()
    assert [row.split(":", 1)[0] for row in intent["human_actors"]] == ["Homeowner"]
    assert "Installation Readiness Before Release" not in rendered
    assert "A 1 proves" not in rendered
    assert "and and" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_does_not_promote_verb_led_path_to_actor() -> None:
    prompt = (
        "Create a solar installation planning product that turns roof, utility, incentive, "
        "and installer constraints into a homeowner-ready installation plan, with review gates "
        "for feasibility, cost, and next actions."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Solar Installation Planning Product"
    assert intent["human_actors"]
    assert all("Installation Plan with" not in row for row in intent["human_actors"])
    assert "helps a with" not in rendered
    assert "With needs" not in rendered
    assert "where turns" not in rendered
    assert "when turns" not in rendered
    assert "can turn roof" in rendered
    assert "Turn Roof Utility Incentive and Installer Constraints Into a Homeowner Ready Installation Plan with" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_rejects_hyphenated_title_noun_as_first_path() -> None:
    prompt = "Draft a greenfield proposal for a clinic follow-up coordination desk"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Clinic Follow Up Coordination Desk"
    assert intent["first_path"].startswith(
        "A representative user reviews clinic follow-up coordination details"
    )
    assert "when a clinic follow-up coordination desk." not in intent["proof_boundary"]
    assert "sequence/parser debris" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_handles_bare_short_product_noun_phrase() -> None:
    prompt = "warehouse slotting planner"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Warehouse Slotting Planner"
    assert intent["first_path"].startswith(
        "A representative user reviews warehouse slotting details"
    )
    assert len(intent["internal_systems"]) == 3
    assert intent["internal_systems"][0].startswith("Warehouse Slotting Details Review ")
    assert "reviews warehouse slotting details" in intent["internal_systems"][0]
    assert intent["internal_systems"][1].startswith("Status Recordkeeping ")
    assert "records the current status" in intent["internal_systems"][1]
    assert intent["internal_systems"][2].startswith("Warehouse Slotting Result Delivery ")
    assert "visible result" in intent["internal_systems"][2]
    assert "Recovered Product Workspace" not in rendered
    assert "First Participant" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_keeps_audience_suffix_inside_product_title() -> None:
    prompt = "kitchen robot controller for home cooks"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Kitchen Robot Controller for Home Cooks"
    assert "Kitchen Robot Controller for Home Cooks Workspace" not in rendered
    assert "Recovered Product Workspace" not in rendered
    assert greenfield_quality_issues(proposal) == []


def test_host_guidance_recovery_handles_plural_actor_clauses_without_generic_workspace() -> None:
    prompt = (
        "Draft a greenfield proposal for a classroom lab safety tracker where teachers prepare experiments, "
        "students acknowledge hazards, and lab coordinators verify cleanup proof."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    proposal = build_confirmed_greenfield_proposal(
        prompt=prompt,
        title=intent["title"],
        observed_source={},
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(proposal, sort_keys=True)

    assert intent["title"] == "Classroom Lab Safety Tracker"
    assert intent["human_actors"] == [
        "Teachers: need the product to prepare experiments and keep the result visible and reviewable",
        "Students: need the product to acknowledge hazards and keep the result visible and reviewable",
        "Lab Coordinators: need the product to verify cleanup proof and keep the result visible and reviewable",
    ]
    assert "Recovered Product Workspace" not in rendered
    assert "a Teachers" not in rendered
    assert "Teachers needs" not in rendered
    assert "teachers can prepare experiments" in rendered
    assert greenfield_quality_issues(proposal) == []


def test_confirmed_completion_splits_finite_actor_sentences_before_domain_intelligence(tmp_path) -> None:
    prompt = (
        "specialty clinic referral tracker where coordinators triage referrals, flag missing documents, "
        "and review a ready-or-blocked status"
    )
    intent = parse_confirmed_intent_text(
        """
# Specialty Clinic Referral Tracker

## Product story
Specialty clinics need one shared referral tracker so coordinators can triage incoming referrals, see missing documents, and keep each referral in a ready-or-blocked state before it is reviewed.

## State object
A referral case records the patient-facing request, referral source, specialty destination, required documents, triage status, blocker reason, owner, timestamps, and review evidence.

## First complete path
Coordinators triage one new referral, flag any missing documents, resolve or document the blocker, and review a ready-or-blocked status that can be trusted by the clinic team.

## Actors
- Coordinators manage referral intake and document readiness.
- Clinic reviewers use the ready-or-blocked status to decide the next action.
- Referral sources supply missing documents when a blocker is raised.

## Systems
- Referral intake queue
- Document checklist service
- Status review workspace
- Audit evidence log

## Assumptions
- The first release focuses on one specialty clinic team and one referral source workflow.

## Ambiguities
- Which source system should send the initial referral payload first?

## Proof boundary
Release 0.0.1 is ready when one coordinator can triage a referral, mark missing documents, clear or preserve a blocker, and produce a ready-or-blocked review trail without relying on an external spreadsheet.
""",
        prompt=prompt,
    )

    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert "Clinic Reviewers Use the" not in rendered
    assert "Referral Sources Supply" not in rendered
    assert "Use the." not in rendered
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_uses_actor_subject_for_public_response_prompt(tmp_path) -> None:
    prompt = (
        "public comment response tracker where agency staff cluster comments, draft replies, "
        "and prove publication readiness"
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"][0].startswith("Agency Staff:")
    assert {row["workstream_type"] for row in completed["backlog"]} == {"standalone"}
    assert "program_parent" not in rendered
    assert "Public Comment Response Participant" not in rendered
    assert "First Participant" not in rendered
    assert "participant" not in next(
        row for row in completed["diagrams"] if row["title"] == "First Path Sequence"
    )["mermaid_source"].casefold()
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_keeps_instrument_objects_out_of_human_actors(tmp_path) -> None:
    prompt = (
        "Build a cryogenic microscope control-room console that coordinates vacuum pumps, stage motion, "
        "thermal drift readings, image capture windows, operator overrides, and recovery proof before "
        "a sample run is accepted."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)
    expected_path = (
        "coordinate vacuum pumps, stage motion, thermal drift readings, image capture windows, "
        "operator overrides, and recovery proof before a sample run is accepted"
    )

    assert not any(row.startswith("Image:") for row in intent["human_actors"])
    assert not any(row.startswith("Room Console User:") for row in intent["human_actors"])
    assert not any(row.startswith("Windows Operator:") for row in intent["human_actors"])
    assert len(intent["human_actors"]) == 1
    assert expected_path in intent["first_path"]
    assert "image can coordinate" not in rendered.casefold()
    assert "user can image coordinates" not in rendered.casefold()
    assert "image coordinates" not in rendered.casefold()
    assert "operator overrides. Recovery proof" not in rendered
    assert expected_path in rendered
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_keeps_operator_notes_out_of_human_actors(tmp_path) -> None:
    prompt = (
        "Create a greenfield proposal for a robotics warehouse near-miss lab where safety engineers replay "
        "robot paths, human proximity events, intervention thresholds, sensor occlusion, baseline routes, "
        "and operator notes before releasing a safety result. The first path must preserve parameter identity, "
        "reviewer decision history, and result explanation without asking for a second confirmation."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"] == [
        "Safety Engineers: need the product to replay robot paths and keep the result visible and reviewable"
    ]
    assert "Operator Notes:" not in rendered
    assert "Baseline:" not in rendered
    assert "generic actor label `Operator`" not in "\n".join(greenfield_quality_issues(completed))
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_keeps_anomalous_change_orders_as_object_phrase(tmp_path) -> None:
    prompt = (
        "Create a civic budget transparency analysis pipeline for city procurement data that detects "
        "vendor concentration, anomalous change orders, and publishes explainable dashboards for residents."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert not any(row.startswith("Anomalous:") for row in intent["human_actors"])
    assert not any(row.startswith("Anomalous Change:") for row in intent["human_actors"])
    assert "anomalous can change orders" not in rendered.casefold()
    assert "anomalous change publishes" not in rendered.casefold()
    assert "detect vendor concentration, anomalous change orders, and publish explainable dashboards" in rendered
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_keeps_organization_actor_and_including_context_readable(tmp_path) -> None:
    prompt = (
        "Design an end-to-end export-control and data-handling compliance workflow for a research lab "
        "processing mixed classified and unclassified files, including review gates, audit trail, "
        "incident response, and least-privilege automation."
    )

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert intent["human_actors"] == [
        "Research Lab: needs the product to process mixed classified and unclassified files with review gates, audit trail, incident response, and least-privilege automation and keep the result visible and reviewable"
    ]
    assert (
        "a research lab can process mixed classified and unclassified files with review gates, audit trail, incident response, and least-privilege automation"
        in rendered
    )
    assert (
        "The accepted product story names the user problem: End-to-end Export Control and Data-handling Compliance Workflow Workspace helps a research lab complete a first path where a research lab can process mixed classified and unclassified files with review gates, audit trail, incident response, and least-privilege automation."
        in rendered
    )
    assert "Research Lab Processing Mixed Classified" not in rendered
    assert "Files Including" not in rendered
    assert "process mixed classified and keep" not in rendered
    assert greenfield_quality_issues(completed) == []


def test_confirmed_recovery_fallback_actor_does_not_emit_participant(tmp_path) -> None:
    prompt = "incident intake console where analysts wrangle incoming reports"

    intent = parse_confirmed_intent_text(_guidance_envelope(prompt), prompt=prompt)
    completed = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt=prompt,
        release_selector="0.0.1",
        confirmed_intent=confirmed_mapping_with_authority(intent),
    )
    rendered = json.dumps(completed, sort_keys=True)

    assert "First Participant" not in rendered
    assert "Participant:" not in rendered
    assert "participant" not in next(
        row for row in completed["diagrams"] if row["title"] == "First Path Sequence"
    )["mermaid_source"].casefold()
    assert greenfield_quality_issues(completed) == []
