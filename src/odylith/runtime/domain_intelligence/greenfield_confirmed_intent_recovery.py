"""Synthetic Product Intent Confirmation recovery from host guidance envelopes."""

from __future__ import annotations

import re
from collections.abc import Sequence

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import base_gerund_clause
from odylith.runtime.common.prose_grammar import contains_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.domain_intelligence.greenfield_actor_led_prefix import looks_like_actor_led_subject_prefix
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
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
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_recovery_text import internal_system_rows_from_recovered_title as _internal_system_rows_from_recovered_title
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
from odylith.runtime.domain_intelligence.greenfield_operational_constraints import operational_constraint_phrases
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import first_path_has_action_signal
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import semantic_first_path_from_context
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import nominal_visible_result_object
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_sentence
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_model
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_text import lower_plain_title_subject_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import operator_review_lens_obligations
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import proof_boundary_with_first_release_requirements

_ACTORLESS_IMPERATIVE_ACTION_WORDS = frozenset({"release"})
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
        "device",
        "engine",
        "executor",
        "hardware",
        "ledger",
        "manager",
        "model",
        "monitor",
        "notebook",
        "platform",
        "policy",
        "product",
        "proof",
        "recommendation",
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
        "view",
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
_HUMAN_ROLE_SUFFIXES = ("ant", "ent", "er", "ian", "ist", "or", "ee", "owner")
_ACTOR_BOUNDARY_RE = re.compile(
    r",\s+(?=(?:the|a|an)\s+\S+(?:\s+\S+){0,3}\s+(?:is|are|can|must|will|should|[a-z]+s)\b)",
    flags=re.IGNORECASE,
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
            and not _actor_uses_where_workflow(prompt_source.actor, source=product_source)
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
    direct_actor_row = _prompt_actor_row(prompt_source.actor, first_path_source)
    actor_rows = _unique_actor_rows(
        [
            *([direct_actor_row] if direct_actor_row else []),
            *_human_actor_rows_from_first_path(first_path_source, title=title),
        ]
    )
    if not direct_actor_row:
        actor_rows = [
            localized
            for row in actor_rows
            if (localized := project_specific_actor_row(row, project_focus=title))
        ] or actor_rows
    lead_actor = _lead_actor_label(actor_rows) or _fallback_actor_label(title)
    lead_action = _lead_actor_action(actor_rows) or base_action_clause(first_path_source)
    outcome = _stable_outcome_phrase(
        first_path_outcome_phrase(first_path_source, fallback=""),
        title=title,
    )
    outcome_object = _object_result_phrase(outcome)
    lead_actor_ref = _actor_reference(lead_actor)
    lead_needs = _actor_verb(lead_actor, singular="needs", plural="need")
    force_actor_modal = bool(
        prompt_source.actor
        and prompt_source.command_led
        and _actor_matches_product_focus(prompt_source.actor, title=title)
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
    story = _recovered_story_text(
        title=title,
        lead_actor_ref=lead_actor_ref,
        first_path_inline=first_path_inline,
        outcome_object=outcome_object,
    )
    state_subject = _state_record_subject(outcome)
    state = (
        f"{_sentence_start(_indefinite_phrase(state_subject))} record tracks the actor, source input, current status, owner, "
        "blocker, handoff, evidence, and version history for the first path."
    )
    proof = _recovered_proof_text(first_path_inline=first_path_inline, outcome_object=outcome_object)
    if evaluation.story:
        story = evaluation.story
    story = _story_with_explicit_operator_context(story, context=prompt_source.operator_context)
    if evaluation.state_object:
        state = evaluation.state_object
    if evaluation.proof_boundary:
        proof = evaluation.proof_boundary
    proof = _proof_with_reviewer_obligations(proof, reviewer_obligations)
    proof = proof_boundary_with_first_release_requirements(proof, product_source)
    problem = (
        f"{lead_actor} {lead_needs} a dependable way to {lead_action.rstrip('.')} and trust the result without stitching "
        "together scattered context."
    )
    product_view = (
        f"{title} earns trust when {lead_actor_ref} can {lead_action.rstrip('.')}. "
        f"{_product_view_result_sentence(outcome_object, lead_action=lead_action)}"
        "The result remains visible, blocked when needed, and reviewable."
    )
    success_metrics = evaluation.success_metrics or (
        f"{lead_actor} can {lead_action.rstrip('.')} and see the visible result.",
        "Missing or invalid input produces a clear blocker instead of a false success.",
        f"Review evidence backs {outcome_object} with replayable proof.",
    )
    assumptions = _assumptions_with_reviewer_obligations(
        evaluation.assumptions or ("Release 0.0.1 proves the first path before broader automation or live integrations.",),
        reviewer_obligations,
    )
    ambiguities = evaluation.ambiguities
    evidence_requirements = evidence_anchor_phrases(product_source)
    operational_constraints = operational_constraint_phrases(product_source)
    hypothesis: dict[str, object] = {
        "title": title,
        "prompt": raw_source,
        "product_story": story,
        "state_object": state,
        "first_path": first_path.rstrip(".") + ".",
        "human_actors": tuple(actor_rows),
        "external_systems": (),
        "internal_systems": tuple(evaluation.internal_systems or tuple(_internal_system_rows_from_recovered_title(title))),
        "problem": problem,
        "opportunity": f"Prove the smallest complete {title.lower()} path before broader automation expands.",
        "product_view": product_view,
        "success_metrics": tuple(success_metrics),
        "assumptions": tuple(assumptions),
        "ambiguities": tuple(ambiguities),
        "proof_boundary": proof,
        "evidence_requirements": tuple(evidence_requirements),
        "operational_constraints": tuple(operational_constraints),
    }
    if as_mapping:
        return hypothesis
    actor_lines = "\n".join(f"- {row}" for row in actor_rows)
    system_lines = "\n".join(f"- {row}" for row in (evaluation.internal_systems or tuple(_internal_system_rows_from_recovered_title(title))))
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
        "External systems\n- No external systems are required for the first proof path unless the operator adds one during edit.",
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
    if _path_starts_with_non_human_workflow_subject(text):
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
            or _preserve_one_line_capability_source(text)
            or _preserve_one_line_action_source(text)
            or _preserve_one_line_sequence_source(text)
            or _preserve_one_line_relative_actor_source(text)
        ):
            return text
        return _first_path_source_from_steps(model.steps) or text
    if word_count(text) >= 6 and (model.material_action or model.visible_outcome or gerund_action):
        return text
    return ""


def _path_starts_with_non_human_workflow_subject(value: str) -> bool:
    words = _strip_leading_articles(_words(value))
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


def _prompt_actor_row(actor: str, first_path: str) -> str:
    actor_text = _clean(actor).strip(" .")
    path = _clean(first_path).strip(" .")
    if not actor_text or not path:
        return ""
    action = re.sub(
        rf"^(?:(?:a|an|the)\s+)?{re.escape(actor_text)}\s+",
        "",
        path,
        count=1,
        flags=re.IGNORECASE,
    ).strip(" .")
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


def _action_has_distinct_sequence(value: str) -> bool:
    model = first_path_model(value)
    return len(model.steps) >= 3


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
    return len(source_terms & compact_terms) < max(4, len(source_terms) // 2)


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
    return bool(re.match(rf"^{re.escape(prefix)}\s+(?:can|could|must|should|will)\b", text, flags=re.IGNORECASE))


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


def _human_actor_rows_from_first_path(value: str, *, title: str = "") -> list[str]:
    rows: list[str] = []
    seen_labels: set[str] = set()
    for clause in _first_path_actor_clauses(value):
        row = _human_actor_row_from_clause(
            clause,
            allow_subject_fallback=not rows,
            require_actor_signal=bool(rows),
        )
        label = row.split(":", 1)[0].casefold() if row else ""
        if row and label not in seen_labels:
            seen_labels.add(label)
            rows.append(row)
    if rows:
        return rows[:3]
    actor = _fallback_actor_label(title)
    action = (
        _actorless_modal_action(value)
        or (base_action_clause(value).strip(" .") if looks_like_action_clause(value) else "")
        or "complete the first path"
    )
    return [f"{actor}: needs the product to {action} and keep the result visible and reviewable"]


def _unique_actor_rows(rows: Sequence[str]) -> list[str]:
    unique: list[str] = []
    seen_labels: set[str] = set()
    for row in rows:
        text = _clean(row)
        label = text.split(":", 1)[0].casefold()
        if not text or not label or label in seen_labels:
            continue
        seen_labels.add(label)
        unique.append(text)
    return unique


def _proof_with_reviewer_obligations(proof: str, obligations: Sequence[str]) -> str:
    base = _clean(proof).strip(" .")
    obligation_text = "; ".join(_clean(row).strip(" .") for row in obligations if _clean(row).strip(" ."))
    if not obligation_text:
        return base
    if obligation_text.casefold() in base.casefold():
        return base
    return f"{base}. Reviewer obligations: {obligation_text}."


def _story_with_explicit_operator_context(story: str, *, context: str) -> str:
    """Keep a user-stated target context visible in product truth and projections."""

    clean_story = _clean(story).strip()
    clean_context = _clean(context).strip(" .")
    if not clean_context or clean_context.casefold() in clean_story.casefold():
        return clean_story
    return f"{clean_story.rstrip(' .')}. The initial product scope serves {clean_context}."


def _assumptions_with_reviewer_obligations(
    assumptions: Sequence[str],
    obligations: Sequence[str],
) -> tuple[str, ...]:
    rows = [_clean(row).strip(" .") for row in assumptions if _clean(row).strip(" .")]
    seen = {row.casefold() for row in rows}
    for obligation in obligations:
        cleaned = _clean(obligation).strip(" .")
        if cleaned and cleaned.casefold() not in seen:
            seen.add(cleaned.casefold())
            rows.append(cleaned)
    return tuple(rows)


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


def _actor_uses_where_workflow(actor: str, *, source: str) -> bool:
    value = _clean(actor).strip(" .")
    if not value:
        return False
    return bool(re.search(rf"\bwhere\s+(?:the\s+)?{re.escape(value)}\b", source, flags=re.IGNORECASE))


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
    relative = re.match(
        r"^(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+(?:who|that)\s+(?P<action>.+)$",
        _clean(clause),
        flags=re.IGNORECASE,
    )
    if relative:
        if require_actor_signal and not _looks_like_actor_subject(_words(relative.group("actor"))):
            return ""
        row = _human_actor_row(relative.group("actor"), relative.group("action"))
        if row:
            return row
    words = _words(clause)
    if len(words) < 2:
        return ""
    purpose_actor, purpose_action = _actor_purpose_parts(clause)
    if purpose_actor and purpose_action:
        if require_actor_signal and not _looks_like_actor_subject(_words(purpose_actor)):
            return ""
        return _human_actor_row(purpose_actor, purpose_action)
    gerund_actor, gerund_action = _actor_gerund_action_parts(clause)
    if gerund_actor and gerund_action:
        if require_actor_signal and not _looks_like_actor_subject(_words(gerund_actor)):
            return ""
        return _human_actor_row(gerund_actor, gerund_action, preserve_full_action=True)
    if _starts_with_action_without_actor(clause):
        return ""
    marker_index = _first_word_index(words, _MODAL_MARKERS)
    if marker_index > 0 and marker_index + 1 < len(words):
        actor_words = list(words[:marker_index])
        action = " ".join(words[marker_index + 1 :])
        if require_actor_signal and not _looks_like_actor_subject(actor_words):
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
    action_index = _action_start_index(words)
    if action_index > 0:
        actor_words = words[:action_index]
        action_words = words[action_index:]
        actor = " ".join(actor_words)
        action = " ".join(action_words)
        if require_actor_signal and not _looks_like_actor_subject(actor_words):
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
        if require_actor_signal and not _looks_like_actor_subject(actor_words):
            return ""
        if _looks_like_role_object_relation_fragment(actor_words, action_words):
            return ""
        return _human_actor_row(actor, action)
    return ""


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
    token = str(value or "").casefold().strip(".,:;")
    return len(token) >= 5 and token.endswith(_HUMAN_ROLE_SUFFIXES)


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
    actor_label = title_case_text(" ".join(actor_words))
    action_source = action if preserve_full_action else _primary_actor_action_segment(action)
    action_text = _base_actor_action_clause(action_source)
    if _starts_with_relation_word(actor_label) or _starts_with_relation_word(action_text):
        return ""
    if not actor_label or not action_text or _looks_like_non_human_actor(actor_label):
        return ""
    need_verb = _actor_verb(actor_label, singular="needs", plural="need")
    return f"{actor_label}: {need_verb} the product to {action_text} and keep the result visible and reviewable"


def _base_actor_action_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
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
    return re.split(r"[;,.]", text, maxsplit=1)[0].strip(" .")


def _looks_like_non_human_actor(value: str) -> bool:
    terms = {term.casefold() for term in label_terms(value)}
    role_terms = terms | {term[:-1] for term in terms if term.endswith("s")}
    if role_terms & (_HUMAN_ACTOR_TERMS | _ORGANIZATION_ACTOR_TERMS):
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


def _lead_actor_action(actor_rows: Sequence[str]) -> str:
    for row in actor_rows:
        _label, _separator, body = str(row).partition(":")
        for marker in ("needs the product to ", "need the product to "):
            if marker in body:
                return body.split(marker, 1)[1].split(" and keep ", 1)[0].strip(" .")
    return ""


def _state_record_subject(value: str) -> str:
    text = lower_plain_title_subject_fragment(_clean(value), action_offset=0).strip(" .")
    if not text:
        return "first visible result"
    text = _drop_terminal_result_action_participle(text)
    words = _strip_leading_articles(_words(text))
    if (
        2 <= len(words) <= 4
        and words[-1].casefold().strip(".,:;") == "result"
        and not looks_like_base_action_token(words[0].casefold().strip(".,:;"))
        and not looks_like_finite_action_token(words[0].casefold().strip(".,:;"))
    ):
        return " ".join(words).strip(" .")
    action_object = _actor_action_object(text)
    if action_object:
        text = nominal_visible_result_object(action_object).strip(" .") or action_object
    text = re.sub(r"\s+\b(?:after|before|during|when|where|while)\b.+$", "", text, flags=re.IGNORECASE).strip(" .")
    words = _strip_leading_articles(_words(text))
    if len(words) >= 3 and words[0].casefold() == "only":
        words = words[1:]
    if words and words[-1].casefold() == "record":
        words = words[:-1]
    return " ".join(words).strip(" .") or "first visible result"


def _drop_terminal_result_action_participle(value: str) -> str:
    words = _words(value)
    if len(words) < 2:
        return _clean(value).strip(" .")
    first = words[0].casefold().strip(".,:;")
    if first not in {"accepted", "approved", "captured", "cleaned", "completed", "generated", "published", "recorded", "saved"}:
        return _clean(value).strip(" .")
    return " ".join(words[1:]).strip(" .") or _clean(value).strip(" .")


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
    if any(singular.endswith(suffix) or last.endswith(suffix) for suffix in _HUMAN_ROLE_SUFFIXES):
        return True
    return False


__all__ = ["confirmation_from_operator_intent"]
