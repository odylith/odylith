"""Synthetic Product Intent Confirmation recovery from host guidance envelopes."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_action_verb
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_action_homonym_actor_role
from odylith.runtime.domain_intelligence.greenfield_actor_roles import has_actor_role_word
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_action_context
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_actor_obligation_noun_phrase
from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import internal_system_rows_from_first_path
from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import product_handoff_first_path
from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import state_object_from_first_path
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_first_path_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import prompt_intent_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_source import product_intent_source_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import LEADING_ARTICLES as _LEADING_ARTICLES
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import MODAL_MARKERS as _MODAL_MARKERS
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import PRODUCT_CONTAINER_TERMS as _PRODUCT_CONTAINER_TERMS
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import actor_reference as _actor_reference
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import actor_verb as _actor_verb
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import clean_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import indefinite_phrase as _indefinite_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import lower_leading_word as _lower_leading_word
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import object_result_phrase as _object_result_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import recovered_title as _recovered_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import recovered_proof_text as _recovered_proof_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import recovered_story_text as _recovered_story_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import recover_title_source as _recover_title_source
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import sentence_start as _sentence_start
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import stable_outcome_phrase as _stable_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import strip_leading_articles as _strip_leading_articles
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import word_spans as _word_spans
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import words as _words
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import product_view_result_sentence as _product_view_result_sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import evidence_anchor_phrases
from odylith.runtime.domain_intelligence.greenfield_evaluation_semantics import recovered_evaluation_context
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_phrases
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import prohibited_product_phrases
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import structured_prompt_facts
from odylith.runtime.domain_intelligence.greenfield_recovered_intent_context import assumptions_with_reviewer_obligations
from odylith.runtime.domain_intelligence.greenfield_recovered_intent_context import localize_direct_actor
from odylith.runtime.domain_intelligence.greenfield_recovered_intent_context import proof_with_reviewer_obligations
from odylith.runtime.domain_intelligence.greenfield_recovered_intent_context import story_with_operator_context
from odylith.runtime.domain_intelligence.greenfield_recovered_intent_context import unique_actor_rows
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import semantic_first_path_from_context
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_sentence
from odylith.runtime.domain_intelligence.greenfield_first_path_temporal import source_state_transition
from odylith.runtime.domain_intelligence.greenfield_first_path_temporal import source_state_transition_subject
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import structured_actor_aliases
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import path_entry_action
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import passive_event_parts
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import structured_actor_subject
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import operator_review_lens_obligations
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import proof_boundary_with_first_release_requirements
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import source_boundary_facts_from_evidence
from odylith.runtime.domain_intelligence.greenfield_text import unique_text

_ACTORLESS_IMPERATIVE_ACTION_WORDS = frozenset({"release"})
_SOURCE_RELATION_ACTIONS = frozenset({"accept", "collect", "import", "receive"})
_NON_HUMAN_ACTOR_TERMS = frozenset(
    {
        "api",
        "application",
        "board",
        "builder",
        "controller",
        "database",
        "data",
        "decision",
        "depot",
        "device",
        "drift",
        "engine",
        "executor",
        "finding",
        "hardware",
        "inspection",
        "ledger",
        "manager",
        "model",
        "monitor",
        "notebook",
        "platform",
        "path",
        "policy",
        "product",
        "proof",
        "recommendation",
        "reading",
        "record",
        "register",
        "report",
        "result",
        "sensor",
        "service",
        "software",
        "state",
        "status",
        "summary",
        "system",
        "tool",
        "unit",
        "view",
        "window",
        "workbench",
        "workspace",
    }
)
_HUMAN_ACTOR_TERMS = frozenset(
    {
        "admin",
        "analyst",
        "approver",
        "coordinator",
        "customer",
        "designer",
        "employee",
        "guest",
        "lead",
        "manager",
        "member",
        "operator",
        "owner",
        "participant",
        "person",
        "planner",
        "reviewer",
        "staff",
        "supervisor",
        "team",
        "user",
        "worker",
    }
)
_ORGANIZATION_ACTOR_TERMS = frozenset(
    {
        "agency",
        "association",
        "clinic",
        "company",
        "department",
        "firm",
        "group",
        "institution",
        "lab",
        "office",
        "organization",
        "school",
        "unit",
    }
)
_ACTOR_BOUNDARY_RE = re.compile(
    r",\s+(?=(?:(?:and|or|then)\s+)?(?:the|a|an)\s+\S+(?:\s+\S+){0,3}\s+"
    r"(?:is|are|can|must|will|should|[a-z]+s)\b)",
    flags=re.IGNORECASE,
)
_APPOSITIVE_PATH_ACTOR_RE = re.compile(
    r"\b(?P<name>[A-Z][A-Za-z0-9'/-]*),\s+(?P<article>a|an|the)\s+"
    r"(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,70}?),\s+",
)
_MATERIAL_FRAGMENT_ACTION_WORDS = frozenset(
    {
        "approval",
        "capture",
        "context",
        "decision",
        "design",
        "details",
        "documentation",
        "evidence",
        "paperwork",
        "plan",
        "readiness",
        "record",
        "report",
        "review",
        "status",
        "summary",
    }
)
_ROLE_OBJECT_ACTION_NOUNS = _MATERIAL_FRAGMENT_ACTION_WORDS - {"review"}
_STATE_REVIEW_PREDICATES = frozenset(
    {
        "auditable",
        "available",
        "blocked",
        "inspectable",
        "reviewable",
        "trusted",
        "visible",
    }
)


def intent_hypothesis_from_operator_evidence(
    intent_text: str,
    *,
    prefer_product_title: bool = False,
) -> dict[str, object]:
    """Build typed candidate facts directly from untrusted operator evidence."""

    return confirmation_from_operator_intent(
        intent_text,
        prefer_product_title=prefer_product_title,
        as_mapping=True,
    )


def confirmation_from_operator_intent(
    intent_text: str,
    *,
    prefer_product_title: bool = False,
    as_mapping: bool = False,
) -> str | dict[str, object]:
    """Return a structured confirmation when the host passed guidance instead of the visible answer."""

    raw_source = str(intent_text or "")
    source = product_intent_source_text(raw_source)
    product_source = _clean(source).strip(" .")
    prompt_source = prompt_intent_source(source)
    recovered_first_path_source = prompt_source.first_path or prompt_first_path_source(source)
    title_source = _canonical_recovered_title_source(_recover_title_source(product_source)) if prefer_product_title else ""
    prompt_title_source = _canonical_recovered_title_source(prompt_source.title)
    evaluation = recovered_evaluation_context(
        source=product_source,
        title_source=prompt_title_source or title_source,
        first_path_source=recovered_first_path_source,
    )
    title = normalize_project_title(
        _recovered_title(
            evaluation.title_source
            or prompt_title_source
            or title_source
            or first_path_outcome_phrase(recovered_first_path_source, fallback="")
        ),
        fallback="Recovered Product Workspace",
    ).canonical_title
    device_owner_first_path = _device_owner_first_path(product_source, title=title)
    recovered_source_has_non_human_subject = _path_starts_with_non_human_workflow_subject(recovered_first_path_source)
    recovered_source_is_title_constraint = _path_is_title_qualified_product_constraint(
        recovered_first_path_source,
        title=title,
    )
    usable_first_path_source = _usable_first_path_source(
        recovered_first_path_source,
        title=title,
        preserve_one_line=bool(
            prompt_source.command_led
            and prompt_source.title
            and prompt_source.actor
        ),
        require_explicit_action=prompt_source.command_led,
    )
    generic_context_source = title
    if not recovered_source_is_title_constraint:
        generic_context_source = (
            (prompt_title_source or title_source or title)
            if recovered_source_has_non_human_subject
            else recovered_first_path_source
        )
    first_path_source = (
        device_owner_first_path
        or usable_first_path_source
        or evaluation.first_path_source
        or _generic_first_path_source(title, source=generic_context_source)
    )
    reviewer_obligations = operator_review_lens_obligations(product_source)
    recovered_path_is_metadata = contains_word_sense_metadata_clause(recovered_first_path_source)
    actor_fact_source = (
        recovered_first_path_source
        if first_path_has_action_signal(recovered_first_path_source) and not recovered_path_is_metadata
        else first_path_source
    )
    direct_actor_row = _prompt_actor_row(
        ""
        if recovered_path_is_metadata
        else prompt_source.actor_label or prompt_source.actor,
        actor_fact_source,
        actor_action=prompt_source.actor_action,
    )
    recovered_actor_rows = _human_actor_rows_from_first_path(
        actor_fact_source,
        title=title,
        include_fallback=not bool(direct_actor_row),
    )
    actor_rows = unique_actor_rows(
        [direct_actor_row, *recovered_actor_rows] if direct_actor_row else recovered_actor_rows
    )
    preserve_direct_actor = bool(
        direct_actor_row
        and _clean(prompt_source.actor).casefold() not in {"individual", "people", "person"}
    )
    actor_rows = [
        (
            row
            if preserve_direct_actor and row.casefold() == direct_actor_row.casefold()
            else project_specific_actor_row(row, project_focus=title) or row
        )
        for row in actor_rows
    ]
    actor_rows = _without_actor_label_fragments(actor_rows)
    lead_actor = _lead_actor_label(actor_rows) or _fallback_actor_label(title)
    direct_actor_label = _lead_actor_label([direct_actor_row])
    first_path_source = localize_direct_actor(
        first_path_source,
        original=direct_actor_label,
        localized=lead_actor,
    )
    lead_action = _lead_actor_action(actor_rows) or base_action_clause(first_path_source)
    structured_contract = structured_prompt_facts(source).first_path_contract
    declared_visible_result = (
        next((event.source_text for event in structured_contract.events if event.kind == "output" and event.valid), "")
        if structured_contract and structured_contract.explicit_output
        else ""
    )
    outcome = _stable_outcome_phrase(
        declared_visible_result or first_path_outcome_phrase(first_path_source, fallback=""),
        title=title,
    )
    outcome_object = _object_result_phrase(outcome)
    typed_actor_subject = _clean(prompt_source.actor_subject).strip(" .")
    typed_actor_label = _clean(prompt_source.actor_label).strip(" .")
    typed_actor_is_lead = bool(
        typed_actor_label
        and typed_actor_label.casefold() == lead_actor.casefold()
    )
    lead_actor_ref = typed_actor_subject if typed_actor_is_lead else _actor_reference(lead_actor)
    lead_actor_sentence_subject = (
        _sentence_start(lead_actor_ref)
        if typed_actor_is_lead
        else structured_actor_subject(lead_actor)
    )
    lead_needs = _actor_verb(lead_actor, singular="needs", plural="need")
    prompt_actor_is_generic = _clean(prompt_source.actor).casefold() in {"individual", "people", "person", "user"}
    force_actor_modal = bool(
        prompt_source.actor
        and prompt_source.command_led
        and (
            prompt_actor_is_generic
            or _actor_matches_product_focus(prompt_source.actor, title=title)
            or _prompt_actor_requires_modal(prompt_source.actor, first_path_source)
        )
    )
    actor_words = _words(prompt_source.actor)
    if (
        force_actor_modal
        and actor_words
        and _looks_plural(actor_words[-1])
        and first_path_source.casefold().startswith(f"{prompt_source.actor.casefold()} ")
        and re.search(rf"\b{re.escape(prompt_source.actor)}\s+uses?\s+to\b", product_source, flags=re.IGNORECASE)
    ):
        force_actor_modal = False
    first_path_inline = _embedded_first_path_clause(
        first_path_source.rstrip("."),
        actor=lead_actor_ref,
        force_actor_modal=force_actor_modal,
    )
    first_path = _sentence_start(first_path_inline)
    if _command_product_owns_following_actions(product_source, actor=prompt_source.actor):
        first_path = product_handoff_first_path(actor=lead_actor_ref, first_path=first_path_source) or first_path
        first_path_inline = first_path.rstrip(" .")
    story = _recovered_story_text(
        title=title,
        lead_actor_ref=lead_actor_ref,
        first_path_inline=first_path_inline,
        outcome_object=outcome_object,
        lead_action=lead_action,
        preserve_leading_case=typed_actor_is_lead,
    )
    state = state_object_from_first_path(
        actor_fact_source or first_path,
        fallback=title,
        preferred_action=(
            ""
            if recovered_source_has_non_human_subject
            else prompt_source.state_action or lead_action
        ),
    )
    proof = _recovered_proof_text(
        first_path_inline=first_path_inline,
        outcome_object=outcome_object,
        preserve_leading_case=typed_actor_is_lead,
        lead_actor_ref=lead_actor_ref,
        lead_action=lead_action,
    )
    if evaluation.story:
        story = evaluation.story
    story = story_with_operator_context(story, context=prompt_source.operator_context)
    if evaluation.state_object:
        state = evaluation.state_object
    transition = source_state_transition(source)
    transition_subject = source_state_transition_subject(source)
    if transition_subject and re.search(
        r"\bstate\s+object\s+is\s+(?:a|an|the)\s+(?:it|them|they)(?:\s|\.)",
        state,
        flags=re.IGNORECASE,
    ):
        state = state_object_from_first_path(first_path, fallback=title)
        if re.search(r"\bstate\s+object\s+is\s+(?:a|an|the)\s+(?:it|them|they)(?:\s|\.)", state, flags=re.IGNORECASE):
            state = f"The primary state object is {_indefinite_phrase(transition_subject)}."
    if transition and transition.casefold() not in state.casefold():
        arrow = re.fullmatch(r"(?P<before>.+?)\s*->\s*(?P<after>.+)", transition)
        relative = f"that moves from {arrow.group('before')} to {arrow.group('after')}" if arrow else re.sub(
            rf"^(?:a|an|the)\s+{re.escape(transition_subject)}\s+",
            "that ",
            transition,
            flags=re.IGNORECASE,
        )
        state = f"{state.rstrip('.')} {relative.strip(' .')}."
    if evaluation.proof_boundary:
        proof = evaluation.proof_boundary
    proof = proof_with_reviewer_obligations(proof, reviewer_obligations)
    proof = proof_boundary_with_first_release_requirements(proof, product_source)
    problem = (
        f"{lead_actor_sentence_subject} {lead_needs} a dependable way to {lead_action.rstrip('.')} and trust the result without stitching "
        "together scattered context."
    )
    product_view = (
        f"{title} earns trust when {lead_actor_ref} can {lead_action.rstrip('.')}. "
        f"{_product_view_result_sentence(outcome_object, lead_action=lead_action)}"
        "The result remains visible, blocked when needed, and reviewable."
    )
    success_metrics = evaluation.success_metrics or (
        f"{lead_actor_sentence_subject} can {lead_action.rstrip('.')} and see the visible result.",
        "Missing or invalid input produces a clear blocker instead of a false success.",
        f"Review evidence backs {outcome_object} with replayable proof.",
    )
    assumptions = assumptions_with_reviewer_obligations(
        evaluation.assumptions or ("Release 0.0.1 proves the first path before broader automation or live integrations.",),
        reviewer_obligations,
    )
    ambiguities = list(evaluation.ambiguities)
    evidence_requirements = evidence_anchor_phrases(product_source)
    operational_constraints = operational_constraint_phrases(product_source)
    non_goals = prohibited_product_phrases(product_source)
    boundary_facts = source_boundary_facts_from_evidence(
        raw_source,
        excluded_labels=(title, prompt_source.title),
    )
    external_systems = tuple(fact.label for fact in boundary_facts if fact.confidence == "source")
    ambiguities.extend(fact.ambiguity for fact in boundary_facts if fact.confidence == "ambiguous")
    internal_systems = tuple(
        evaluation.internal_systems
        or internal_system_rows_from_first_path(
            title=title,
            first_path=first_path,
            state_object=state,
            visible_result=outcome,
            human_actors=actor_rows,
            external_systems=external_systems,
        )
    )
    hypothesis: dict[str, object] = {
        "title": title,
        "prompt": raw_source,
        "product_story": story,
        "state_object": state,
        "first_path": first_path.rstrip(".") + ".",
        "human_actors": tuple(actor_rows),
        "external_systems": external_systems,
        "internal_systems": internal_systems,
        "problem": problem,
        "opportunity": f"Prove the smallest complete {title.lower()} path before broader automation expands.",
        "product_view": product_view,
        "success_metrics": tuple(success_metrics),
        "assumptions": tuple(assumptions),
        "ambiguities": tuple(unique_text(ambiguities)),
        "proof_boundary": proof,
        "evidence_requirements": tuple(evidence_requirements),
        "operational_constraints": tuple(operational_constraints),
        "non_goals": tuple(non_goals),
    }
    if as_mapping:
        return hypothesis
    actor_lines = "\n".join(f"- {row}" for row in actor_rows)
    external_lines = "\n".join(f"- {row}" for row in external_systems) or (
        "- No external systems are required for the first proof path unless the operator adds one during edit."
    )
    system_lines = "\n".join(f"- {row}" for row in internal_systems)
    sections = [
        f"# {title} - Product Intent Confirmation",
        "Product story\n" + story,
        "State object\n" + state,
        "First complete path\n" + first_path.rstrip(".") + ".",
    ]
    if operational_constraints:
        sections.append("Operational constraints\n" + "\n".join(f"- {row}" for row in operational_constraints))
    sections.extend(
        (
        "Human actors\n" + actor_lines,
        "External systems\n" + external_lines,
        "Internal product systems\n" + system_lines,
        "Problem\n" + problem,
        "Opportunity\n" + f"Prove the smallest complete {title.lower()} path before broader automation expands.",
        "Product view\n" + product_view,
        "Success metrics\n" + "\n".join(f"- {row}" for row in success_metrics),
        "Critical assumptions\n" + "\n".join(f"- {row}" for row in assumptions),
        )
    )
    if evidence_requirements:
        sections.append("Evidence requirements\n" + "\n".join(f"- {row}" for row in evidence_requirements))
    if non_goals:
        sections.append("Non-goals\n" + "\n".join(f"- {row}" for row in non_goals))
    sections.extend(
        (
            "Ambiguities\n" + "\n".join(f"- {row}" for row in ambiguities),
            "Proof boundary\n" + proof,
        )
    )
    return "\n\n".join(sections)


def _usable_first_path_source(
    value: str,
    *,
    title: str,
    preserve_one_line: bool = False,
    require_explicit_action: bool = False,
) -> str:
    text = _clean(value).strip(" .")
    if not text or _path_source_restates_title(text, title=title):
        return ""
    if _path_is_title_qualified_product_constraint(text, title=title):
        return ""
    if (
        _path_starts_with_non_human_workflow_subject(text)
        and not _human_actor_rows_from_first_path(text, title=title, include_fallback=False)
    ):
        return ""
    model = first_path_model(text)
    gerund_actor, gerund_action = _actor_gerund_action_parts(text)
    if require_explicit_action and not first_path_has_action_signal(text) and not (gerund_actor and gerund_action):
        return ""
    if not first_path_has_action_signal(text) and not model.material_action and not (gerund_actor and gerund_action):
        return ""
    if len(model.steps) >= 2:
        if (
            preserve_one_line
            or _preserve_complete_source_sequence(text)
            or _preserve_explicit_actor_action_chain(text)
            or _preserve_one_line_capability_source(text)
            or _preserve_one_line_action_source(text)
            or _preserve_one_line_sequence_source(text)
            or _preserve_one_line_relative_actor_source(text)
            or _preserve_one_line_actor_source(text)
        ):
            return text
        return _first_path_source_from_steps(model.steps) or text
    if word_count(text) >= 6 and (model.material_action or model.visible_outcome or gerund_action):
        return text
    return ""


def _preserve_complete_source_sequence(value: str) -> bool:
    """Keep a short, source-grounded multi-sentence path intact."""

    text = _clean(value).strip(" .")
    rows = [row.strip(" .") for row in re.split(r"(?<=[.!?])\s+", text) if row.strip(" .")]
    if not 2 <= len(rows) <= 8:
        return False
    if not has_human_actor_signal(text):
        return False
    if re.search(
        r"\b(?:must\s+not|may\s+not|cannot|can't|do\s+not|never|proof\s+boundary|"
        r"out\s+of\s+scope|unrelated)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return all(first_path_has_action_signal(row) for row in rows)


def _preserve_explicit_actor_action_chain(value: str) -> bool:
    text = _clean(value).strip(" .")
    actor_match = re.match(
        r"^[A-Z][A-Za-z0-9'/-]*(?:,\s+(?:a|an|the)\s+(?P<appositive_role>[^,]{2,80}),|"
        r"\s+is\s+(?:a|an|the)\s+(?P<copular_role>[^:]{2,100}):)",
        text,
    )
    role = ""
    if actor_match:
        role = str(actor_match.group("appositive_role") or actor_match.group("copular_role") or "").strip()
    if (
        not text
        or not actor_match
        or not has_human_actor_role_signal(role)
        or len(first_path_model(text).steps) < 2
    ):
        return False
    return not re.search(
        r"\b(?:must\s+not|may\s+not|cannot|can't|do\s+not|never|proof\s+boundary|"
        r"out\s+of\s+scope|unrelated)\b",
        text,
        flags=re.IGNORECASE,
    )

def _path_starts_with_non_human_workflow_subject(value: str) -> bool:
    text = _clean(value).strip(" .")
    relative = re.match(
        r"^(?P<subject>[A-Za-z][A-Za-z0-9 /&'()-]{1,100}?)\s+(?:who|that)\s+.+$",
        text,
        flags=re.IGNORECASE,
    )
    if relative and _looks_like_actor_subject(_words(relative.group("subject"))):
        return False
    words = _strip_leading_articles(_words(text))
    candidates = [words]
    candidates.extend(words[index + 1 :] for index, word in enumerate(words[:-1]) if word.casefold() == "where")
    for candidate in candidates:
        if len(candidate) < 3:
            continue
        max_subject_words = min(5, len(candidate) - 1)
        for action_index in range(1, max_subject_words + 1):
            token = candidate[action_index].casefold().strip(".,:;")
            if not (looks_like_base_action_token(token) or looks_like_finite_action_token(token)):
                continue
            subject_words = candidate[:action_index]
            if _looks_like_actor_subject(subject_words):
                break
            subject_terms = _semantic_terms(" ".join(subject_words))
            if subject_terms & _NON_HUMAN_ACTOR_TERMS:
                return True
    return False


def _prompt_actor_row(actor: str, first_path: str, *, actor_action: str = "") -> str:
    actor_text = _clean(actor).strip(" .")
    path = _clean(first_path).strip(" .")
    if not actor_text or not path:
        return ""
    action = _clean(actor_action).strip(" .") or _source_action_after_actor(
        actor=actor_text,
        first_path=path,
    )
    action = _strip_relative_action_prefix(action)
    if not action:
        return ""
    return _human_actor_row(
        actor_text,
        action,
        preserve_full_action=not (
            _action_has_distinct_sequence(action)
            or _ACTOR_BOUNDARY_RE.search(action)
            or re.search(r"[.;]", action)
        ),
    )


def _source_action_after_actor(*, actor: str, first_path: str) -> str:
    matches = [
        match
        for alias in structured_actor_aliases(actor)
        for match in re.finditer(rf"\b{re.escape(alias)}\b", first_path, flags=re.IGNORECASE)
    ]
    matches.sort(key=lambda item: item.start())
    for match in matches:
        action = first_path[match.end() :].strip(" ,.;:")
        normalized = _normalized_actor_tail(action)
        if normalized:
            return normalized
    return first_path


def _normalized_actor_tail(value: str) -> str:
    action = _clean(value).strip(" .")
    if not action:
        return ""
    action = re.sub(r"^(?:who|that)\s+", "", action, count=1, flags=re.IGNORECASE)
    action = re.sub(r"^to\s+", "", action, count=1, flags=re.IGNORECASE)
    action = re.sub(
        r"^(?:can|could|may|might|must|should|will|would)\s+",
        "",
        action,
        count=1,
        flags=re.IGNORECASE,
    )
    need = re.match(
        r"^(?:needs?|wants?)\s+(?P<article>a|an|the)\s+(?P<product>[^,.;!?]{1,100}?)\s+"
        r"(?P<connector>to|where)\s+(?P<action>.+)$",
        action,
        flags=re.IGNORECASE,
    )
    if need:
        if need.group("connector").casefold() == "to":
            return need.group("action").strip(" .")
        product = " ".join(need.group("product").split()).strip(" .")
        return f"use {need.group('article').casefold()} {product} where {need.group('action').strip(' .')}"
    action_words = _words(action)
    action_head = action_words[0].casefold().strip(".,:;") if action_words else ""
    if (
        looks_like_action_clause(action)
        or looks_like_base_action_token(action_head)
        or looks_like_finite_action_token(action_head)
    ):
        return action
    using = re.match(r"^using\s+(?P<object>.+)$", action, flags=re.IGNORECASE)
    if using:
        return f"use {using.group('object').strip(' .')}"
    path = re.match(r"^from\s+(?P<path>.+)$", action, flags=re.IGNORECASE)
    if path:
        return f"process {path.group('path').strip(' .')}"
    return ""


def _prompt_actor_requires_modal(actor: str, first_path: str) -> bool:
    """Repair a singular actor followed by a source infinitive such as ``lets an engineer submit``."""

    actor_words = _strip_leading_articles(_words(actor))
    if not actor_words or _looks_plural(actor_words[-1]):
        return False
    action = re.sub(
        rf"^(?:(?:a|an|the)\s+)?{re.escape(_clean(actor).strip(' .'))}\s+",
        "",
        _clean(first_path).strip(" ."),
        count=1,
        flags=re.IGNORECASE,
    )
    first = _words(action)
    return bool(first and looks_like_base_action_token(first[0]) and not looks_like_finite_action_token(first[0]))


def _command_product_owns_following_actions(source: str, *, actor: str) -> bool:
    actor_text = _clean(actor).strip(" .")
    if not actor_text:
        return False
    match = re.search(
        rf"\b(?:that|which)\s+(?:allows?|enables?|helps?|lets?)\s+"
        rf"(?:(?:a|an|the|one)\s+)?{re.escape(actor_text)}\b",
        _clean(source),
        flags=re.IGNORECASE,
    )
    if not match:
        return False
    following_clauses = re.split(r"\s*,\s*(?:and\s+)?", _clean(source)[match.end() :])
    for clause in following_clauses[1:]:
        first_word = next(iter(_words(clause)), "")
        if looks_like_finite_action_token(first_word) and not looks_like_base_action_token(first_word):
            return True
    return False


def _action_has_distinct_sequence(value: str) -> bool:
    model = first_path_model(value)
    if len(model.steps) >= 3:
        return True
    if len(model.steps) != 2:
        return False
    text = _clean(value).strip(" .")
    words = [word.casefold().strip("()[]{}\"'.,:;") for word in text.split()]
    has_temporal_gerund = any(
        word in {"after", "before"} and words[index + 1].endswith("ing")
        for index, word in enumerate(words[:-1])
    )
    return bool(
        has_temporal_gerund
        or "then" in words
        or any(mark in text for mark in ".;")
    )


def _first_path_source_from_steps(steps: Sequence[str]) -> str:
    rows = [_clean(step).strip(" .") for step in steps if _clean(step).strip(" .")]
    return ". ".join(rows)


def _preserve_one_line_capability_source(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    return "can" in {word.casefold().strip(".,:;") for word in text.split()}


def _preserve_one_line_sequence_source(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    tokens = {word.casefold().strip(".,:;") for word in text.split()}
    return "then" in tokens and first_path_has_action_signal(text)


def _preserve_one_line_action_source(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    return first_path_has_action_signal(text) and _starts_with_action_without_actor(text)


def _preserve_one_line_relative_actor_source(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    return bool(_relative_actor_action(text))


def _preserve_one_line_actor_source(value: str) -> bool:
    """Keep one grammatical actor-led path from becoming sentence fragments."""

    text = _clean(value).strip(" .")
    if not text or any(mark in text for mark in ".!?"):
        return False
    actor, action = _actor_led_base_action_parts(text)
    if not actor or not action or not _looks_like_actor_subject(_words(actor)):
        return False
    steps = first_path_model(text).steps
    actor_actions = [_actor_led_base_action_parts(step) for step in steps]
    same_actor = bool(
        actor_actions
        and all(step_actor and step_action for step_actor, step_action in actor_actions)
        and len({_clean(step_actor).casefold() for step_actor, _step_action in actor_actions}) == 1
    )
    return len(steps) >= 2 and (
        same_actor or any(not step_action for _step_actor, step_action in actor_actions[1:])
    )


def _path_source_restates_title(value: str, *, title: str) -> bool:
    value_terms = _semantic_terms(value)
    title_terms = _semantic_terms(title)
    return bool(value_terms and title_terms and value_terms <= title_terms)


def _path_is_title_qualified_product_constraint(value: str, *, title: str) -> bool:
    """Reject product descriptions that express release boundaries, not user actions."""

    text = _clean(value).strip(" .")
    title_text = _clean(title).strip(" .")
    if not text or not title_text:
        return False
    return bool(
        re.match(
            rf"^(?:a|an|the)\s+{re.escape(title_text)}\s+(?:that|which)\s+"
            r"(?:avoids?|does\s+not|never|only\s+helps?|without)\b",
            text,
            flags=re.IGNORECASE,
        )
    )


def _canonical_recovered_title_source(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return normalize_project_title(text, fallback=text).canonical_title


def _semantic_terms(value: str) -> set[str]:
    terms: set[str] = set()
    for term in label_terms(value):
        for token in str(term).casefold().replace("-", " ").replace("/", " ").split():
            if token not in _LEADING_ARTICLES:
                terms.add(token)
    return terms


def _generic_first_path_source(title: str, *, source: str = "") -> str:
    return semantic_first_path_from_context(title=title, source=source)


def _device_owner_first_path(value: str, *, title: str) -> str:
    """Recover a usable owner journey when a prompt describes device behavior, not a user flow."""

    source = _clean(value).casefold()
    if not re.search(r"\b(?:device|controller|sensor|monitor)\b[^.!?]{0,120}\bthat\s+", source):
        return ""
    device_label = _title_without_terminal_container(title).casefold() or "device"
    status_subject = "plant status" if re.search(r"\bhouseplants?|plants?\b", source) else "device status"
    outcome_parts: list[str] = []
    if re.search(r"\bwater(?:s|ing)?\b", source):
        outcome_parts.append("watering")
    if re.search(r"\bmonitor(?:s|ing)?\b", source):
        outcome_parts.append("monitoring")
    if outcome_parts == ["watering", "monitoring"]:
        visible_result = "current watering status and sensor status"
    elif outcome_parts:
        visible_result = f"current {outcome_parts[0]} status"
    else:
        visible_result = "current device status"
    return (
        f"A device owner can configure one {device_label}, review the {status_subject}, "
        f"and see {visible_result}"
    )


def _embedded_first_path_clause(value: str, *, actor: str, force_actor_modal: bool = False) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if (
        _preserve_complete_source_sequence(text)
        or _preserve_explicit_actor_action_chain(text)
        or (not force_actor_modal and _preserve_one_line_actor_source(text))
    ):
        return _sentence_case(text)
    relative_action = _relative_actor_action(text)
    if relative_action:
        action = _recovered_action_clause(relative_action)
        return f"{_clean(actor) or 'the representative user'} can {action}"
    purpose_action = _actor_purpose_action(text)
    if purpose_action:
        action = _recovered_action_clause(purpose_action)
        return f"{_clean(actor) or 'the representative user'} can {action}"
    gerund_actor, gerund_action = _actor_gerund_action_parts(text)
    if gerund_actor and gerund_action:
        return f"{_clean(gerund_actor) or _clean(actor) or 'the representative user'} can {gerund_action}"
    actor_prefix, actor_action = _actor_led_base_action_parts(text)
    prefix_words = _words(actor_prefix)
    article_led_prefix = bool(prefix_words and prefix_words[0].casefold().strip(".,:;") in _LEADING_ARTICLES)
    if actor_prefix and actor_action and (
        force_actor_modal or (not article_led_prefix and text.casefold().startswith(f"{actor_prefix.casefold()} "))
    ):
        if force_actor_modal and not _looks_like_actor_subject(_words(actor_prefix)):
            return f"{_clean(actor) or 'the representative user'} can {actor_action}"
        if force_actor_modal or _actor_led_clause_has_modal(text, actor_prefix):
            return f"{_clean(actor_prefix) or _clean(actor) or 'the representative user'} can {actor_action}"
        return _sentence_case(text)
    clause = _lower_leading_word(text)
    actorless_modal_action = _actorless_modal_action(clause)
    if actorless_modal_action:
        clause = f"{_clean(actor) or 'the representative user'} can {actorless_modal_action}"
    elif looks_like_action_clause(clause):
        action = base_action_clause(clause).strip(" .") or clause
        clause = f"{_clean(actor) or 'the representative user'} can {action}"
    return clause


def _recovered_action_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    compact = (
        readable_action_chain_sentence(
            text,
            fallback=base_action_clause(text).strip(" .") or text,
            limit=280,
            max_steps=6,
            include_visible_results=True,
        ).strip(" .")
        or base_action_clause(text).strip(" .")
        or text
    )
    if _action_compaction_loses_material_terms(source=text, compact=compact):
        return text
    return compact


def _action_compaction_loses_material_terms(*, source: str, compact: str) -> bool:
    source_text = _clean(source).strip(" .")
    compact_text = _clean(compact).strip(" .")
    if not source_text or not compact_text or "," not in source_text:
        return False
    source_terms = _semantic_terms(source_text)
    compact_terms = _semantic_terms(compact_text)
    if len(source_terms) < 5:
        return False
    missing = source_terms - compact_terms
    return len(missing) > max(1, len(source_terms) // 5)


def _relative_actor_action(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(
        r"^[A-Za-z][A-Za-z0-9 /&'()-]{1,100}?\s+(?:who|that)\s+(?P<action>.+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    action = _strip_leading_can_action(_clean(match.group("action")).strip(" ."))
    return action if looks_like_action_clause(action) else ""


def _actor_led_base_action_parts(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    if not text:
        return "", ""
    words = text.split()
    for index in range(1, min(len(words), 6)):
        prefix = " ".join(words[:index]).strip(" .")
        if not looks_like_actor_led_subject_prefix(prefix, text):
            continue
        candidate = _strip_leading_can_action(" ".join(words[index:]).strip(" ."))
        if looks_like_action_clause(candidate):
            return prefix, base_action_clause(candidate, force_leading_finite=True).strip(" .") or candidate
    return "", ""


def _actor_led_clause_has_modal(value: str, actor_prefix: str) -> bool:
    text = _clean(value).strip(" .")
    prefix = _clean(actor_prefix).strip(" .")
    if not text or not prefix:
        return False
    tail = text[len(prefix) :].strip() if text.casefold().startswith(prefix.casefold()) else ""
    marker = tail.split(maxsplit=1)[0].casefold() if tail else ""
    return marker in _MODAL_MARKERS


def _sentence_case(value: str) -> str:
    text = _clean(value).strip(" .")
    return text[:1].upper() + text[1:] if text else ""


def _strip_relative_action_prefix(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(r"^(?:who|that)\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")
    return _strip_leading_can_action(text)


def _strip_leading_can_action(value: str) -> str:
    text = _clean(value).strip(" .")
    match = re.match(r"^can\s+(?P<action>.+)$", text, flags=re.IGNORECASE)
    if not match:
        return text
    action = _clean(match.group("action")).strip(" .")
    return action if looks_like_action_clause(action) else text


def _actor_purpose_action(value: str) -> str:
    _actor, action = _actor_purpose_parts(value)
    return action


def _actor_purpose_parts(value: str) -> tuple[str, str]:
    text = _clean(value).strip(" .")
    match = re.match(r"^(?P<actor>.+?)\s+to\s+(?P<action>.+)$", text, flags=re.IGNORECASE)
    if not match:
        return ("", "")
    actor = _clean(match.group("actor")).strip(" .")
    action = _clean(match.group("action")).strip(" .")
    if not actor or not action:
        return ("", "")
    if _looks_like_actor_subject(_words(actor)) and looks_like_action_clause(action):
        return actor, action
    return ("", "")


def _human_actor_rows_from_first_path(
    value: str,
    *,
    title: str = "",
    include_fallback: bool = True,
) -> list[str]:
    rows = _appositive_actor_rows_from_first_path(value)
    seen_labels = {row.split(":", 1)[0].casefold() for row in rows}
    for clause in _first_path_actor_clauses(value):
        row = _human_actor_row_from_clause(
            clause,
            allow_subject_fallback=not rows,
            require_actor_signal=True,
        )
        label = row.split(":", 1)[0].casefold() if row else ""
        if row and label not in seen_labels:
            seen_labels.add(label)
            rows.append(row)
    if rows:
        return rows[:3]
    if not include_fallback:
        return []
    actor = _fallback_actor_label(title)
    action = (
        _actorless_modal_action(value)
        or (base_action_clause(value).strip(" .") if looks_like_action_clause(value) else "")
        or "complete the first path"
    )
    return [f"{actor}: needs the product to {action} and keep the result visible and reviewable"]


def _appositive_actor_rows_from_first_path(value: str) -> list[str]:
    rows: list[str] = []
    for match in _APPOSITIVE_PATH_ACTOR_RE.finditer(_clean(value)):
        actor = f"{match.group('name')}, {match.group('article')} {match.group('role').strip()}"
        action = _source_action_after_actor(actor=actor, first_path=value)
        row = _human_actor_row(actor, action) if action and action != value else ""
        if row:
            rows.append(row)
    return rows


def _fallback_actor_label(title: str) -> str:
    label = _clean(title).strip(" .") or "Product"
    candidate = _title_without_terminal_container(label)
    if candidate and _looks_like_actor_subject(_words(candidate)):
        return title_case_text(candidate)
    return f"{label} User"


def _actor_matches_product_focus(actor: str, *, title: str) -> bool:
    actor_words = [word.casefold().strip(".,:;") for word in _words(actor)]
    title_words = [word.casefold().strip(".,:;") for word in _words(title)]
    if title_words and title_words[-1] in _PRODUCT_CONTAINER_TERMS:
        title_words.pop()
    return bool(actor_words) and actor_words == title_words


def _title_without_terminal_container(value: str) -> str:
    words = _words(value)
    if len(words) < 3:
        return ""
    last = words[-1].casefold().strip(".,:;")
    if last not in _PRODUCT_CONTAINER_TERMS:
        return ""
    return " ".join(words[:-1]).strip(" .")


def _first_path_actor_clauses(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    clauses = [text] if _actor_gerund_action_parts(text)[0] else []
    clauses.extend(_split_actor_candidate_clauses(text))
    model_steps = [_clean(step) for step in first_path_model(text).steps if _clean(step)]
    if model_steps:
        clauses.extend(model_steps)
    return _unique_clauses(clauses)


def _split_actor_candidate_clauses(text: str) -> list[str]:
    clauses: list[str] = []
    for part in re.split(r";\s+|,\s+|(?<=[.!?])\s+", text):
        part = _clean(part)
        if not part:
            continue
        for subpart in part.split(" and "):
            cleaned = _clean(subpart)
            clauses.extend(_purpose_split_actor_clauses(cleaned))
    return clauses


def _purpose_split_actor_clauses(value: str) -> list[str]:
    text = _clean(value)
    if not text:
        return []
    parts = [part for part in re.split(r"\s+so\s+", text, maxsplit=1, flags=re.IGNORECASE) if _clean(part)]
    if len(parts) != 2:
        return [text]
    prefix, suffix = (_clean(parts[0]), _clean(parts[1]))
    suffix_words = _words(suffix)
    if _first_word_index(suffix_words, _MODAL_MARKERS) > 0:
        rows = []
        if prefix:
            rows.append(prefix)
        rows.append(suffix)
        return rows
    return [text]


def _unique_clauses(values: Sequence[str]) -> list[str]:
    rows: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _clean(value)
        key = text.casefold()
        if not text or key in seen:
            continue
        seen.add(key)
        rows.append(text)
    return rows


def _human_actor_row_from_clause(
    clause: str,
    *,
    allow_subject_fallback: bool,
    require_actor_signal: bool = False,
) -> str:
    if is_actor_obligation_noun_phrase(clause):
        return ""
    delegated = re.search(
        r"\b(?:asks?|directs?|requires?)\s+(?:a|an|the)\s+"
        r"(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,70}?)\s+to\s+(?P<action>.+)$",
        _clean(clause),
        flags=re.IGNORECASE,
    )
    if delegated and _has_actor_action_signal(
        _words(delegated.group("actor")),
        _words(delegated.group("action")),
    ):
        return _human_actor_row(delegated.group("actor"), delegated.group("action"))
    relative = re.match(
        r"^(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+(?:who|that)\s+(?P<action>.+)$",
        _clean(clause),
        flags=re.IGNORECASE,
    )
    if relative:
        if require_actor_signal and not _has_actor_action_signal(
            _words(relative.group("actor")),
            _words(relative.group("action")),
        ):
            return ""
        row = _human_actor_row(relative.group("actor"), relative.group("action"))
        if row:
            return row
    words = _words(clause)
    if len(words) < 2:
        return ""
    source_actor, source_action = _human_source_actor_event(words)
    if source_actor and source_action:
        return _human_actor_row(source_actor, source_action)
    purpose_actor, purpose_action = _actor_purpose_parts(clause)
    if purpose_actor and purpose_action:
        if require_actor_signal and not _has_actor_action_signal(_words(purpose_actor), _words(purpose_action)):
            return ""
        return _human_actor_row(purpose_actor, purpose_action)
    gerund_actor, gerund_action = _actor_gerund_action_parts(clause)
    if gerund_actor and gerund_action:
        if require_actor_signal and not _has_actor_action_signal(_words(gerund_actor), _words(gerund_action)):
            return ""
        return _human_actor_row(gerund_actor, gerund_action, preserve_full_action=True)
    explicit_split = _explicit_actor_action_split(words)
    homonym_actor_split = bool(
        explicit_split
        and has_action_homonym_actor_role(
            " ".join(explicit_split[0]),
            " ".join(explicit_split[1]),
        )
    )
    if _starts_with_action_without_actor(clause) and not homonym_actor_split:
        return ""
    marker_index = _first_word_index(words, _MODAL_MARKERS)
    if marker_index > 0 and marker_index + 1 < len(words):
        actor_words = list(words[:marker_index])
        action = " ".join(words[marker_index + 1 :])
        if require_actor_signal and not _has_actor_action_signal(actor_words, _words(action)):
            return ""
        if _looks_like_state_review_predicate(action):
            role_actor, role_action = _state_review_actor_action(actor_words)
            if role_actor and role_action:
                return _human_actor_row(role_actor, role_action)
            return ""
        if _actor_prefix_contains_embedded_action(actor_words):
            return ""
        if _looks_like_passive_object_subject(actor_words, _words(action)):
            return ""
        if _looks_like_material_actor_fragment(actor_words, _words(action)):
            return ""
        return _human_actor_row(" ".join(actor_words), action)
    if explicit_split:
        actor_words, action_words = explicit_split
        actor = " ".join(actor_words)
        action = " ".join(action_words)
        if require_actor_signal and not _has_actor_action_signal(actor_words, action_words):
            return ""
        if _actor_prefix_contains_embedded_action(actor_words):
            return ""
        if _looks_like_material_actor_fragment(actor_words, action_words):
            return ""
        if _looks_like_passive_object_subject(actor_words, action_words):
            return ""
        if _looks_like_role_object_relation_fragment(actor_words, action_words):
            return ""
        return _human_actor_row(actor, action)
    action_index = _action_start_index(words)
    if action_index > 0:
        actor_words = words[:action_index]
        action_words = words[action_index:]
        actor = " ".join(actor_words)
        action = " ".join(action_words)
        if require_actor_signal and not _has_actor_action_signal(actor_words, action_words):
            return ""
        if _actor_prefix_contains_embedded_action(actor_words):
            return ""
        if _looks_like_material_actor_fragment(actor_words, action_words):
            return ""
        if _looks_like_passive_object_subject(actor_words, action_words):
            return ""
        if _looks_like_role_object_relation_fragment(actor_words, action_words):
            return ""
        return _human_actor_row(actor, action)
    fallback = _plural_subject_fallback(words, allow_single_subject=allow_subject_fallback)
    if fallback:
        actor, action = fallback
        actor_words = _words(actor)
        action_words = _words(action)
        if require_actor_signal and not _has_actor_action_signal(actor_words, action_words):
            return ""
        if _looks_like_role_object_relation_fragment(actor_words, action_words):
            return ""
        return _human_actor_row(actor, action)
    return ""


def _human_source_actor_event(words: Sequence[str]) -> tuple[str, str]:
    """Project explicit ``receives <object> from <human role>`` evidence as a human event."""

    lowered = [word.casefold().strip(".,:;") for word in words]
    for relation_index, token in enumerate(lowered):
        if token != "from" or relation_index < 2 or relation_index + 1 >= len(words):
            continue
        action_index = next(
            (
                index
                for index, word in enumerate(words[:relation_index])
                if base_action_verb(word) in _SOURCE_RELATION_ACTIONS
            ),
            -1,
        )
        if action_index < 0:
            continue
        object_words = list(words[action_index + 1 : relation_index])
        actor_words = list(words[relation_index + 1 :])
        boundary_index = next(
            (
                index
                for index, word in enumerate(actor_words[1:], start=1)
                if word.casefold().strip(".,:;") in _RELATION_BOUNDARY_WORDS
            ),
            len(actor_words),
        )
        actor_words = _strip_leading_articles(actor_words[:boundary_index])
        actor = " ".join(actor_words).strip(" .")
        object_text = " ".join(object_words).strip(" .")
        if (
            actor
            and object_text
            and len(actor_words) <= 5
            and has_actor_role_word(actor)
            and not has_non_human_actor_signal(actor)
        ):
            return actor, f"provide {object_text}"
    return "", ""


def _explicit_actor_action_split(words: Sequence[str]) -> tuple[list[str], list[str]] | None:
    """Find an unambiguous actor/action split in a source clause."""

    for index in range(1, min(5, len(words) - 1) + 1):
        actor_words = list(words[:index])
        action_words = list(words[index:])
        if (
            _actor_prefix_contains_embedded_action(actor_words)
            or _looks_like_material_actor_fragment(actor_words, action_words)
            or _looks_like_passive_object_subject(actor_words, action_words)
            or _looks_like_role_object_relation_fragment(actor_words, action_words)
        ):
            continue
        if has_human_actor_action_context(" ".join(actor_words), " ".join(action_words)):
            return actor_words, action_words
        actor = _strip_leading_articles(actor_words)
        if not actor or not (
            _looks_like_actor_subject(actor)
            or has_action_homonym_actor_role(" ".join(actor), " ".join(action_words))
        ):
            continue
        if not _looks_plural(actor[-1]) or not looks_like_base_action_token(action_words[0]):
            continue
        return actor_words, action_words
    return None


_RELATION_BOUNDARY_WORDS = frozenset(
    {
        "after",
        "before",
        "during",
        "for",
        "from",
        "through",
        "until",
        "when",
        "where",
        "while",
        "with",
        "without",
    }
)


def _looks_like_role_object_relation_fragment(actor_words: Sequence[str], action_words: Sequence[str]) -> bool:
    """Reject object-list tails such as "operator notes before release" as actors."""

    subject = _strip_leading_articles(actor_words)
    action = _strip_leading_articles(action_words)
    if not subject or len(action) < 1:
        return False
    subject_head = subject[0].casefold().strip(".,:;")
    if subject_head not in _HUMAN_ACTOR_TERMS:
        return False
    subject_tail = [word.casefold().strip(".,:;") for word in subject[1:]]
    if any(tail in _HUMAN_ACTOR_TERMS or _looks_like_human_actor_token(tail) for tail in subject_tail):
        return False
    action_head = action[0].casefold().strip(".,:;")
    if len(subject) > 1:
        return action_head in _RELATION_BOUNDARY_WORDS
    if len(action) < 2:
        return False
    relation = action[1].casefold().strip(".,:;")
    return (
        relation in _RELATION_BOUNDARY_WORDS
        and _looks_plural(action_head)
        and not _looks_like_human_actor_token(action_head)
    )


def _looks_like_material_actor_fragment(actor_words: Sequence[str], action_words: Sequence[str]) -> bool:
    cleaned_actor = _strip_leading_articles(actor_words)
    if not cleaned_actor or not action_words:
        return False
    if len(cleaned_actor) != 1:
        return False
    raw_actor_has_article = bool(actor_words and actor_words[0].casefold() in _LEADING_ARTICLES)
    actor_token = cleaned_actor[0].casefold().strip(".,:;")
    action_token = action_words[0].casefold().strip(".,:;")
    if raw_actor_has_article or _looks_plural(actor_token):
        return False
    if _semantic_terms(actor_token) & _HUMAN_ACTOR_TERMS or _looks_like_human_actor_token(actor_token):
        return False
    return action_token in _MATERIAL_FRAGMENT_ACTION_WORDS


_PASSIVE_OBJECT_AUXILIARIES = frozenset({"are", "be", "been", "being", "is", "was", "were"})
_OBJECT_STATE_RELATIONS = frozenset({"after", "before", "during", "when", "where", "while"})
_OBJECT_STATE_TERMS = frozenset(
    {
        "approval",
        "claim",
        "claims",
        "decision",
        "evidence",
        "procedure",
        "record",
        "records",
        "risk",
        "state",
        "status",
    }
)


def _looks_like_passive_object_subject(actor_words: Sequence[str], action_words: Sequence[str]) -> bool:
    """Reject object-state clauses that look grammatical but are not actors."""

    subject = _strip_leading_articles(actor_words)
    action = _strip_leading_articles(action_words)
    if not subject or len(action) < 2:
        return False
    subject_terms = {word.casefold().strip(".,:;") for word in subject}
    if subject_terms & _HUMAN_ACTOR_TERMS or any(_looks_like_human_actor_token(word) for word in subject):
        return False
    passive_subject, _active_action = passive_event_parts(" ".join([*actor_words, *action_words]))
    if passive_subject:
        return True
    action_head = action[0].casefold().strip(".,:;")
    if action_head not in _PASSIVE_OBJECT_AUXILIARIES:
        return False
    return bool(subject_terms & (_OBJECT_STATE_RELATIONS | _OBJECT_STATE_TERMS))


def _actor_prefix_contains_embedded_action(actor_words: Sequence[str]) -> bool:
    """Reject recovered actor labels that already contain an actor/action/object clause."""

    cleaned = _strip_leading_articles(actor_words)
    if len(cleaned) < 3:
        return False
    if _actor_action_object(" ".join(cleaned)):
        return True
    for index in range(1, len(cleaned) - 1):
        if index < 2 and not _looks_like_actor_subject(cleaned[:index]):
            continue
        if looks_like_action_clause(" ".join(cleaned[index:])):
            return True
    return False


def _looks_like_human_actor_token(value: str) -> bool:
    return has_human_actor_signal(value)


def _starts_with_action_without_actor(clause: str) -> bool:
    text = re.sub(r"^(?:and|or|then)\s+", "", _clean(clause), flags=re.IGNORECASE)
    words = _strip_leading_articles(_words(text))
    if len(words) < 2:
        return False
    first = words[0].casefold().strip(".,:;")
    if first in _MODAL_MARKERS and looks_like_action_clause(" ".join(words[1:])):
        return True
    if (
        len(words) >= 3
        and first in {"need", "needs"}
        and words[1].casefold().strip(".,:;") == "to"
        and looks_like_action_clause(" ".join(words[2:]))
    ):
        return True
    if not looks_like_action_clause(text) and words[0].casefold() not in _ACTORLESS_IMPERATIVE_ACTION_WORDS:
        return False
    if _first_word_index(words, _MODAL_MARKERS) > 0:
        return False
    leading_terms = {term.casefold() for term in label_terms(words[0])}
    if leading_terms & _HUMAN_ACTOR_TERMS:
        return False
    if _looks_plural(words[0]) and not looks_like_finite_action_token(words[0]) and not contains_finite_action(words[0]):
        return False
    return True


def _actorless_modal_action(value: str) -> str:
    words = _strip_leading_articles(_words(_clean(value)))
    if len(words) < 2:
        return ""
    first = words[0].casefold().strip(".,:;")
    if first in _MODAL_MARKERS and looks_like_action_clause(" ".join(words[1:])):
        return base_action_clause(" ".join(words[1:])).strip(" .")
    if (
        len(words) >= 3
        and first in {"need", "needs"}
        and words[1].casefold().strip(".,:;") == "to"
        and looks_like_action_clause(" ".join(words[2:]))
    ):
        return base_action_clause(" ".join(words[2:])).strip(" .")
    return ""


def _action_start_index(words: Sequence[str]) -> int:
    for index in range(1, max(1, len(words) - 1)):
        if looks_like_action_clause(" ".join(words[index:])):
            return index
    return -1


def _actor_gerund_action_parts(value: str) -> tuple[str, str]:
    """Return an actor plus base-action clause for noun-led gerund paths."""

    text = _clean(value).strip(" .")
    spans = _word_spans(text)
    if len(spans) < 3:
        return ("", "")
    words = [word for word, _start, _end in spans]
    max_actor_words = min(5, len(spans) - 1)
    for index in range(1, max_actor_words + 1):
        actor_words = words[:index]
        if not _looks_like_actor_subject(actor_words):
            continue
        action_source = text[spans[index][1] :].strip(" ,.;:")
        action = _gerund_action_clause(action_source)
        if action:
            return (" ".join(actor_words), action)
    return ("", "")


def _gerund_action_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    converted = base_gerund_clause(text).strip(" .")
    if not converted or converted.casefold() == text.casefold():
        return ""
    if re.search(r",\s+including\b", text, flags=re.IGNORECASE):
        converted = re.sub(r",\s+include\b", " with", converted, count=1, flags=re.IGNORECASE)
    return converted


def _first_word_index(words: Sequence[str], targets: set[str] | frozenset[str]) -> int:
    for index, word in enumerate(words):
        if word.casefold() in targets:
            return index
    return -1


def _human_actor_row(actor: str, action: str, *, preserve_full_action: bool = False) -> str:
    actor_words = _strip_leading_articles(_words(actor))
    actor_words, action = _repair_role_object_actor_split(actor_words, action)
    terminal_actor_word = actor_words[-1].casefold().strip(".,:;") if actor_words else ""
    if (
        terminal_actor_word in _PRODUCT_CONTAINER_TERMS
        and terminal_actor_word not in _HUMAN_ACTOR_TERMS | _ORGANIZATION_ACTOR_TERMS
    ):
        return ""
    actor_label = _source_preserving_actor_label(actor, actor_words=actor_words)
    action_source = (
        action
        if preserve_full_action and _coordinated_actor_boundary_index(action) < 0
        else _primary_actor_action_segment(action)
    )
    action_text = _base_actor_action_clause(action_source)
    if (
        _starts_with_relation_word(actor_label)
        or _starts_with_relation_word(action_text)
        or (
            not (has_human_actor_signal(actor_label) or has_human_actor_role_signal(actor_label))
            and re.search(r"\b(?:state|status)\b", action_text, flags=re.IGNORECASE)
        )
    ):
        return ""
    if not actor_label or not action_text or _looks_like_non_human_actor(actor_label):
        return ""
    need_verb = _actor_verb(actor_label, singular="needs", plural="need")
    return f"{actor_label}: {need_verb} the product to {action_text} and keep the result visible and reviewable"


def _source_preserving_actor_label(actor: str, *, actor_words: Sequence[str]) -> str:
    source = _clean(actor).strip(" .")
    appositive = re.fullmatch(
        r"(?P<name>[A-Z][A-Za-z0-9'/-]*),\s+(?P<article>a|an|the)\s+"
        r"(?P<role>[A-Za-z][A-Za-z0-9 /&'()-]{1,80})",
        source,
        flags=re.IGNORECASE,
    )
    if appositive and not has_non_human_actor_signal(appositive.group("role")):
        return (
            f"{appositive.group('name')}, {appositive.group('article').casefold()} "
            f"{appositive.group('role').casefold()}"
        )
    return title_case_text(" ".join(actor_words))


def _base_actor_action_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    entry_action = path_entry_action(text)
    if entry_action.casefold() != text.casefold():
        return entry_action
    action = base_action_clause(text).strip(" .")
    if action and action.casefold() != text.casefold():
        return action
    gerund_action = _gerund_action_clause(text)
    return gerund_action or action


def _repair_role_object_actor_split(actor_words: list[str], action: str) -> tuple[list[str], str]:
    """Keep object modifiers out of recovered actor labels."""

    cleaned = [word for word in actor_words if str(word).strip()]
    if len(cleaned) < 2:
        return actor_words, action
    role = cleaned[0].casefold().strip(".,:;")
    modifier_words = cleaned[1:]
    if role not in _HUMAN_ACTOR_TERMS:
        return actor_words, action
    if any(word.casefold().strip(".,:;") in _HUMAN_ACTOR_TERMS for word in modifier_words):
        return actor_words, action
    action_words = _words(action)
    if len(action_words) < 2:
        return actor_words, action
    first_action = action_words[0].casefold().strip(".,:;")
    singular = first_action[:-1] if first_action.endswith("s") else first_action
    if singular not in _ROLE_OBJECT_ACTION_NOUNS:
        return actor_words, action
    repaired_action = " ".join([singular, *modifier_words, *action_words]).strip(" .")
    return [cleaned[0]], repaired_action


def _looks_like_state_review_predicate(action: str) -> bool:
    words = _words(action)
    if len(words) < 2 or words[0].casefold() != "be":
        return False
    return any(word.casefold().strip(".,:;") in _STATE_REVIEW_PREDICATES for word in words[1:4])


def _state_review_actor_action(subject_words: Sequence[str]) -> tuple[str, str]:
    cleaned = _strip_leading_articles(subject_words)
    if len(cleaned) < 2:
        return ("", "")
    role = cleaned[0].casefold().strip(".,:;")
    if role not in _HUMAN_ACTOR_TERMS:
        return ("", "")
    modifier_words = cleaned[1:]
    if any(word.casefold().strip(".,:;") in _HUMAN_ACTOR_TERMS for word in modifier_words):
        return ("", "")
    object_text = " ".join(modifier_words).strip(" .")
    if not object_text:
        return ("", "")
    return (cleaned[0], f"review {object_text}")


def _starts_with_relation_word(value: str) -> bool:
    words = _words(value)
    return bool(
        words
        and words[0].casefold()
        in {"and", "as", "at", "by", "for", "from", "in", "into", "of", "on", "or", "then", "to", "with", "without"}
    )


def _primary_actor_action_segment(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    text = _ACTOR_BOUNDARY_RE.split(text, maxsplit=1)[0]
    boundary = _coordinated_actor_boundary_index(text)
    if boundary >= 0:
        text = text[:boundary].strip(" .")
    return re.split(r"[;,.]", text, maxsplit=1)[0].strip(" .")


def _coordinated_actor_boundary_index(value: str) -> int:
    text = _clean(value)
    for match in re.finditer(r"\s+(?:and|or|then)\s+", text, flags=re.IGNORECASE):
        tail = text[match.end() :].strip(" .")
        words = _words(tail)
        if not words:
            continue
        for subject_end in range(1, min(5, len(words))):
            subject = " ".join(words[:subject_end])
            action = " ".join(words[subject_end:])
            if has_non_human_actor_signal(subject) or has_human_actor_action_context(subject, action):
                return match.start()
    return -1


def _looks_like_non_human_actor(value: str) -> bool:
    terms = {term.casefold() for term in label_terms(value)}
    role_terms = terms | {term[:-1] for term in terms if term.endswith("s")}
    if has_human_actor_role_signal(value) or role_terms & (_HUMAN_ACTOR_TERMS | _ORGANIZATION_ACTOR_TERMS):
        return False
    return bool(terms & _NON_HUMAN_ACTOR_TERMS)


def _plural_subject_fallback(words: Sequence[str], *, allow_single_subject: bool) -> tuple[str, str]:
    cleaned = _strip_leading_articles(words)
    if len(cleaned) < 3:
        return ("", "")
    if len(cleaned) >= 4 and _looks_plural(cleaned[1]):
        return (" ".join(cleaned[:2]), " ".join(cleaned[2:]))
    if allow_single_subject and _looks_plural(cleaned[0]):
        return (cleaned[0], " ".join(cleaned[1:]))
    if _looks_plural(cleaned[0]) and len(cleaned) >= 3:
        return (cleaned[0], " ".join(cleaned[1:]))
    return ("", "")


def _looks_plural(value: str) -> bool:
    token = str(value or "").casefold().strip(".,:;")
    return len(token) > 3 and token.endswith("s") and not token.endswith(("ous", "ss"))


def _lead_actor_label(actor_rows: Sequence[str]) -> str:
    for row in actor_rows:
        label, _, _body = str(row).partition(":")
        label = _clean(label)
        if label:
            return label
    return ""


def _without_actor_label_fragments(actor_rows: Sequence[str]) -> list[str]:
    rows: list[str] = []
    kept_terms: list[set[str]] = []
    for row in actor_rows:
        label = str(row).partition(":")[0].strip()
        terms = {term.casefold() for term in label_terms(label) if term.casefold() not in _LEADING_ARTICLES}
        if terms and any(terms <= existing or existing <= terms for existing in kept_terms):
            continue
        rows.append(str(row))
        kept_terms.append(terms)
    return rows


def _lead_actor_action(actor_rows: Sequence[str]) -> str:
    for row in actor_rows:
        _label, _separator, body = str(row).partition(":")
        for marker in ("needs the product to ", "need the product to "):
            if marker in body:
                return body.split(marker, 1)[1].split(" and keep ", 1)[0].strip(" .")
    return ""


def _actor_action_object(value: str) -> str:
    words = _words(value)
    if len(words) < 3:
        return ""
    max_subject_words = min(4, len(words) - 2)
    for verb_index in range(1, max_subject_words + 1):
        verb = words[verb_index].casefold().strip(".,:;")
        if not (looks_like_base_action_token(verb) or looks_like_finite_action_token(verb)):
            continue
        subject = words[:verb_index]
        if not _looks_like_actor_subject(subject):
            continue
        obj = " ".join(words[verb_index + 1 :]).strip(" .")
        if obj.casefold().startswith("when "):
            obj = obj[5:].strip(" .")
        return obj
    return ""


def _looks_like_actor_subject(words: Sequence[str]) -> bool:
    cleaned = _strip_leading_articles(words)
    if not cleaned:
        return False
    last = cleaned[-1].casefold().strip(".,:;")
    singular = last[:-1] if last.endswith("s") else last
    actor_terms = _HUMAN_ACTOR_TERMS | _ORGANIZATION_ACTOR_TERMS
    if singular in actor_terms or last in actor_terms:
        return True
    return has_human_actor_role_signal(" ".join(cleaned))


def _has_actor_action_signal(actor_words: Sequence[str], action_words: Sequence[str]) -> bool:
    actor = _strip_leading_articles(actor_words)
    actor_tokens = {word.casefold().strip(".,:;") for word in actor}
    if actor_tokens & {"for", "helps", "lets", "needs", "supports", "wants"}:
        return False
    terminal = actor[-1].casefold().strip(".,:;") if actor else ""
    terminal = terminal[:-1] if terminal.endswith("s") else terminal
    if terminal in _NON_HUMAN_ACTOR_TERMS and terminal not in _HUMAN_ACTOR_TERMS:
        return False
    if action_words and has_non_human_actor_signal(f"{' '.join(actor)} {action_words[0]}"):
        return False
    if (
        len(action_words) >= 2
        and looks_like_base_action_token(action_words[0])
        and looks_like_finite_action_token(action_words[1])
        and not _looks_like_actor_subject(actor_words)
    ):
        return False
    return (
        _looks_like_actor_subject(actor_words)
        or has_action_homonym_actor_role(" ".join(actor_words), " ".join(action_words))
        or has_human_actor_action_context(" ".join(actor_words), " ".join(action_words))
    )


__all__ = ["confirmation_from_operator_intent"]
