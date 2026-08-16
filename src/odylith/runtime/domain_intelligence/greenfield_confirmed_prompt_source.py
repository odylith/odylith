"""Recover clean first-path source text from operator prompt wrappers."""

from __future__ import annotations

from dataclasses import dataclass
import re

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_action_context
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import has_non_human_actor_signal
from odylith.runtime.domain_intelligence.greenfield_actor_terms import is_automated_actor
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_patterns import direct_actor_action_match
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_patterns import leading_actor_action_match
from odylith.runtime.domain_intelligence.greenfield_confirmed_prompt_patterns import before_can_outcome_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_common import MATERIAL_ACTION_RE
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_requirement_control_tail
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import strip_trailing_requirement_control_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_release_evidence_requirement
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_release_visible_result_statement
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import actor_led_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_subjects import modal_actor_action_parts
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import is_contextual_path_step
from odylith.runtime.domain_intelligence.greenfield_external_boundary_semantics import is_external_dependency_clause
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import command_product_title
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import is_requester_product_framing
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import need_product_actor_action
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import product_focus_after_command_sentence
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import product_focus_after_need_sentence
from odylith.runtime.domain_intelligence.greenfield_need_product_focus import workflow_object_title
from odylith.runtime.domain_intelligence.greenfield_gerund_actions import GERUND_ACTION_VERBS
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import REQUEST_COMMAND_WORDS
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import confirmed_direction_evidence_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import is_source_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import looks_like_trailing_operator_instruction
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import markdown_section_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import operator_context_from_product_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import product_intent_source_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import rankable_prompt_evidence_text
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import request_words
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import sentence_fragments
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import strip_leading_contextual_gerund_sentence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import strip_trailing_operator_instruction_sentences
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import without_leading_explicit_intent_label
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import without_source_metadata_clauses
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_custody import word_key
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import ranked_first_path_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_actor_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import explicit_product_title_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import is_non_path_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import is_labeled_non_path_evidence
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_interpretation import structured_prompt_facts
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import prompt_field_mapping
from odylith.runtime.domain_intelligence.greenfield_prompt_evidence_fields import prompt_field_values
from odylith.runtime.domain_intelligence.greenfield_request_context_title import contextual_product_title
from odylith.runtime.domain_intelligence.greenfield_structured_first_path import source_owned_path_evidence
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_text
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import REQUEST_REPORTING_VERBS
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import WORD_SENSE_REPORTING_CONTENT_VERBS
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import strip_request_reporting_custody_tail
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import word_sense_content_clause_describes_comparison
from odylith.runtime.domain_intelligence.greenfield_word_sense_metadata import word_sense_tail_starts_content_clause


_REQUEST_TITLE_MAX_WORDS = 10
_REQUEST_EVIDENCE_LABELS = frozenset({"confirmed request", "edited request", "request"})
_REQUEST_PRODUCT_WORDS = frozenset(
    {
        "app",
        "application",
        "board",
        "builder",
        "dashboard",
        "desk",
        "experience",
        "console",
        "controller",
        "engine",
        "executor",
        "hub",
        "manager",
        "monitor",
        "notebook",
        "plan",
        "platform",
        "planner",
        "portal",
        "product",
        "project",
        "room",
        "service",
        "coach",
        "cockpit",
        "coordination",
        "studio",
        "system",
        "tool",
        "tracker",
        "journal",
        "logbook",
        "workbench",
        "workspace",
    }
)
_REQUEST_HELPER_WORDS = frozenset({"allow", "allows", "enable", "enables", "help", "helps", "let", "lets"})
_REQUEST_ACTOR_PURPOSE_TOKENS = frozenset({"people", "person", "rep", "reps", "staff", "team", "teams", "user", "users"})
_NON_HUMAN_SUBJECT_TERMS = frozenset(
    {
        "approval",
        "case",
        "claim",
        "data",
        "decision",
        "evidence",
        "finding",
        "handoff",
        "note",
        "notes",
        "proof",
        "recommendation",
        "record",
        "report",
        "result",
        "review",
        "state",
        "status",
        "summary",
        "view",
        "waiver",
        "workflow",
    }
)
_NON_HUMAN_SUBJECT_TERMINALS = frozenset(
    {
        "app",
        "application",
        "board",
        "builder",
        "console",
        "controller",
        "dashboard",
        "engine",
        "executor",
        "hub",
        "notebook",
        "platform",
        "portal",
        "service",
        "system",
        "tool",
        "tracker",
        "workbench",
        "workspace",
    }
)
_REQUEST_LEAD_CONNECTORS = ("where", "that", "who", "so", "for", "to", "with")
_MULTI_ROLE_MODAL_TOKENS = frozenset({"can", "could", "must", "should", "will"})
_OBSERVATION_ONLY_ACTIONS = frozenset({"check", "inspect", "replay", "review", "see", "verify", "view"})
_PATH_GRANT_PATH_MODIFIERS = frozenset(
    {
        "a",
        "an",
        "the",
        "clear",
        "complete",
        "end-to-end",
        "first",
        "full",
        "governed",
        "guided",
        "one",
        "review-ready",
        "single",
    }
)
_DIRECT_TITLE_BOUNDARY_CONNECTORS = frozenset({"where", "that", "who", "so"})
_RELEASE_PROOF_ACTION_WORDS = frozenset(
    {
        "complete",
        "completes",
        "completed",
        "pass",
        "passes",
        "prove",
        "proves",
        "proved",
        "succeed",
        "succeeds",
        "succeeded",
    }
)
@dataclass(frozen=True)
class PromptIntentSource:
    """Operator prompt interpretation before confirmed-intent recovery."""

    title: str
    first_path: str
    command_led: bool
    actor: str = ""
    actor_action: str = ""
    actor_label: str = ""
    actor_subject: str = ""
    state_action: str = ""
    operator_context: str = ""


def prompt_first_path_source(value: str) -> str:
    """Return product-path text without a host command or product wrapper."""

    return prompt_intent_source(value).first_path


def prompt_project_title_source(value: str) -> str:
    """Return the product noun phrase from an operator request."""

    return prompt_intent_source(value).title


def prompt_intent_source(value: str) -> PromptIntentSource:
    """Return shared title and first-path sources for thin prompt recovery."""

    original_intent = rankable_prompt_evidence_text(product_intent_source_text(value))
    structured_facts = structured_prompt_facts(original_intent)
    has_structured_fields = bool(prompt_field_mapping(original_intent))
    explicit_first_path = markdown_section_text(
        original_intent,
        headings=frozenset({"first complete path", "first path"}),
    )
    text = strip_trailing_operator_instruction_sentences(
        clean_markdown_text(original_intent).strip(" .")
    )
    text = without_leading_explicit_intent_label(text)
    product_text = without_source_metadata_clauses(text)
    ranked_first_path = strip_trailing_operator_instruction_sentences(ranked_first_path_evidence(original_intent))
    explicit_actor = explicit_actor_evidence(original_intent)
    source_owned = source_owned_path_evidence(product_text, ranked_first_path=ranked_first_path)
    explicit_title = explicit_product_title_evidence(original_intent)
    operator_context = operator_context_from_product_text(product_text)
    words = request_words(product_text)
    start, command_led = _request_content_start(words)
    command_focus = product_focus_after_command_sentence(product_text)
    command_title = command_product_title(product_text)
    need_actor, need_action = need_product_actor_action(product_text)
    need_first_path = f"{need_actor} can {need_action}" if need_actor and need_action else ""
    grant_actor, grant_first_path = _path_grant_actor_action(product_text)
    if grant_actor and not grant_first_path and not _first_path_actor_candidate(ranked_first_path):
        ranked_rows = sentence_fragments(ranked_first_path)
        if len(ranked_rows) > 1:
            ranked_first_path = ". ".join(ranked_rows[1:])
    workflow_actor, workflow_first_path = _workflow_where_actor_action(product_text)
    multi_role_actor, multi_role_first_path = _multi_role_modal_first_path(product_text)
    purpose_actor, purpose_first_path = _leading_role_purpose_action_path(product_text)
    role_bound_actor, role_bound_first_path = _role_bound_review_actor_action(product_text)
    direct_actor, direct_first_path = _direct_actor_action_sentence(ranked_first_path)
    if not direct_actor:
        direct_actor, direct_first_path = _direct_actor_action_sentence(product_text)
    release_actor, _release_first_path = _direct_actor_action_sentence(
        _release_action_sentence_source(product_text)
    )
    preferred_direct_first_path = direct_first_path
    ranked_step_count = sum(
        not is_contextual_path_step(step)
        for step in first_path_model(ranked_first_path).steps
    )
    direct_step_count = sum(
        not is_contextual_path_step(step)
        for step in first_path_model(direct_first_path).steps
    )
    if (
        ranked_first_path
        and direct_step_count < ranked_step_count
    ):
        preferred_direct_first_path = ""
    ranked_prefix, ranked_separator, _ = ranked_first_path.partition(",")
    preferred_context_first_path = (
        direct_first_path
        if ranked_separator
        and is_contextual_path_step(ranked_prefix)
        and direct_step_count == ranked_step_count
        else ""
    )
    context_actor, context_first_path = _for_role_actor_gerund_path(product_text)
    actor, actor_led_first_path = _actor_led_relative_clause(product_text)
    actor_led_model = first_path_model(actor_led_first_path)
    complete_actor_led_first_path = (
        actor_led_first_path
        if actor
        and actor_led_model.material_action
        and actor_led_model.visible_outcome
        else ""
    )
    non_human_relative_first_path = _non_human_subject_relative_action(product_text)
    ranked_rows = sentence_fragments(ranked_first_path)
    complete_ranked_first_path = (
        ranked_first_path
        if len(ranked_rows) > 1
        or (
            structured_facts.path_needs_enrichment
            and len(first_path_model(ranked_first_path).steps) > 1
        )
        else ""
    )
    complete_structured_first_path = (
        structured_facts.first_path
        if structured_facts.first_path_contract and structured_facts.first_path_contract.complete
        else ""
    )
    direct_actor_owns_output_path = bool(
        direct_actor
        and (
            has_human_actor_signal(direct_actor)
            or _single_proper_person_actor(direct_actor)
            or direct_actor.casefold() == explicit_actor.casefold()
        )
    )
    direct_actor_is_bounded = bool(direct_actor and _is_bounded_prompt_actor(direct_actor))
    ranked_has_human_lead = _starts_with_explicit_human_actor(ranked_first_path)
    preferred_role_context_path = context_first_path if context_actor and not ranked_has_human_lead else ""
    preferred_who_relative_path = (
        complete_actor_led_first_path
        if re.search(r"\bwho\b", complete_actor_led_first_path, flags=re.IGNORECASE)
        else ""
    )
    grant_handoff_first_path = direct_first_path if grant_actor and not grant_first_path and direct_first_path else ""
    explicit_owner_actors = tuple(
        candidate
        for candidate, owned_path in (
            (need_actor, need_first_path),
            (grant_actor, grant_first_path or grant_handoff_first_path),
            (role_bound_actor, role_bound_first_path),
            (context_actor, preferred_role_context_path),
            (actor, preferred_who_relative_path),
        )
        if candidate and owned_path
    )
    structured_actor = structured_facts.first_path_contract.actor if structured_facts.first_path_contract else ""
    preferred_complete_structured_path = (
        complete_structured_first_path
        if complete_structured_first_path
        and explicit_owner_actors
        and any(structured_actor.casefold() == candidate.casefold() for candidate in explicit_owner_actors)
        else ""
    )
    first_path_source = (
        (
            direct_first_path
            if direct_actor_owns_output_path
            and structured_facts.first_path_contract
            and structured_facts.first_path_contract.output_only
            and direct_step_count >= ranked_step_count
            else ""
        )
        or source_owned.first_path
        or complete_ranked_first_path
        or preferred_complete_structured_path
        or need_first_path
        or grant_handoff_first_path
        or role_bound_first_path
        or preferred_role_context_path
        or preferred_who_relative_path
        or complete_structured_first_path
        or explicit_first_path
        or grant_first_path
        or multi_role_first_path
        or preferred_context_first_path
        or complete_actor_led_first_path
        or ranked_first_path
        or workflow_first_path
        or purpose_first_path
        or preferred_direct_first_path
        or actor_led_first_path
        or context_first_path
        or non_human_relative_first_path
        or ("" if is_source_metadata_clause(product_text) else _first_path_source_from_text(product_text))
    )
    first_path_source = _with_release_visible_result(first_path_source, evidence=product_text)
    first_path = strip_leading_contextual_gerund_sentence(_strip_release_proof_tail(first_path_source))
    resolved_actor = next(
        (
            candidate
            for candidate in (
                grant_actor,
                source_owned.actor,
                structured_facts.actor,
                workflow_actor,
                multi_role_actor,
                need_actor,
                direct_actor if direct_actor_is_bounded else "",
                release_actor,
                explicit_actor,
                purpose_actor,
                actor,
                context_actor,
            )
            if _is_bounded_prompt_actor(candidate)
        ),
        "",
    )
    if not resolved_actor:
        first_path_actor, first_path_action = actor_led_action_parts(first_path)
        recovery_kind = "actor_led" if first_path_actor else ""
        if not first_path_actor:
            first_path_actor, first_path_action = modal_actor_action_parts(first_path)
            recovery_kind = "modal" if first_path_actor else ""
        if not first_path_actor:
            actor_action_match = leading_actor_action_match(first_path)
            if actor_action_match:
                first_path_actor, first_path_action = actor_action_match
                recovery_kind = "leading"
        recovered_actor = _strip_leading_actor_article(first_path_actor)
        if _is_bounded_prompt_actor(recovered_actor):
            resolved_actor = recovered_actor
            if first_path_action and _actor_recovery_needs_canonical_path(first_path, recovery_kind=recovery_kind):
                first_path = f"{recovered_actor} can {first_path_action}".strip(" .")
    path_actor = _first_path_actor_candidate(first_path)
    if not path_actor and (pronoun := re.match(r"^(?:he|she|they)\b", first_path, flags=re.IGNORECASE)):
        path_actor = pronoun.group(0)
    resolved_key = _strip_leading_actor_article(resolved_actor).casefold()
    explicit_key = _strip_leading_actor_article(explicit_actor).casefold()
    if resolved_key and "," not in explicit_actor and explicit_key.endswith(f" {resolved_key}"):
        resolved_actor = _strip_leading_actor_article(explicit_actor)
        resolved_key = resolved_actor.casefold()
    path_actor_key = _strip_leading_actor_article(path_actor).casefold()
    actor_is_shorthand = bool(
        path_actor_key
        and resolved_key
        and (
            path_actor_key in {"he", "she", "they"}
            or resolved_key == path_actor_key
            or resolved_key.endswith(f" {path_actor_key}")
        )
    )
    if actor_is_shorthand and resolved_key != path_actor_key:
        qualified_actor = _strip_leading_actor_article(resolved_actor)
        pronoun_actor = path_actor_key in {"he", "she", "they"}
        replacement = f"The {qualified_actor} can" if pronoun_actor else f"The {qualified_actor}"
        actor_pattern = (
            rf"^(?:(?:a|an|the)\s+)?{re.escape(path_actor)}(?:\s+can)?\b"
            if pronoun_actor
            else rf"^(?:(?:a|an|the)\s+)?{re.escape(path_actor)}\b"
        )
        first_path = re.sub(
            actor_pattern,
            replacement,
            first_path,
            count=1,
            flags=re.IGNORECASE,
        )
    elif (
        resolved_key
        and not path_actor
        and not has_human_actor_signal(first_path.partition(".")[0])
        and looks_like_action_clause(first_path)
    ):
        first_path = f"The {_strip_leading_actor_article(resolved_actor)} can {first_path}"
    structured_contract = structured_facts.first_path_contract
    structured_actor_owns_path = bool(
        structured_contract
        and structured_contract.complete
        and resolved_actor.casefold() == structured_contract.actor.casefold()
    )
    return PromptIntentSource(
        title=structured_facts.title
        or _labeled_request_title(original_intent)
        or _confirmed_direction_title(original_intent)
        or command_focus
        or command_title
        or explicit_title
        or ("" if has_structured_fields else product_focus_after_need_sentence(product_text))
        or ("" if has_structured_fields else workflow_object_title(product_text))
        or ("" if has_structured_fields else contextual_product_title(product_text))
        or (
            ""
            if has_structured_fields
            else _project_title_source_from_words(words, start=start, command_led=command_led)
        ),
        first_path=first_path,
        command_led=command_led,
        actor=resolved_actor,
        actor_action=structured_contract.primary_actor_action if structured_actor_owns_path else source_owned.action if resolved_actor.casefold() == source_owned.actor.casefold() else "",
        actor_label=(structured_contract.actor_label if structured_actor_owns_path else ""),
        actor_subject=(structured_contract.actor_subject if structured_actor_owns_path else ""),
        state_action=(structured_contract.primary_state_action if structured_actor_owns_path else ""),
        operator_context=operator_context,
    )


def _labeled_request_title(value: str) -> str:
    """Read the bounded target noun phrase from an explicit ``Request:`` line."""

    typed_candidates = tuple(
        f"request: {request}"
        for request in prompt_field_values(value, names=tuple(_REQUEST_EVIDENCE_LABELS))
    )
    candidates = tuple(
        dict.fromkeys((*typed_candidates, *str(value or "").splitlines(), *sentence_fragments(value)))
    )
    for candidate in candidates:
        label, separator, request = candidate.partition(":")
        if not separator or label.strip().casefold() not in _REQUEST_EVIDENCE_LABELS:
            continue
        words = request_words(request)
        start, command_led = _request_content_start(words)
        bounded_title = _project_title_source_from_words(words, start=start, command_led=command_led)
        if bounded_title:
            return bounded_title
        title_words = [word.strip(".,:;!? ") for word in words[start:] if word.strip(".,:;!? ")]
        title = " ".join(title_words).strip()
        if command_led and 1 <= len(title_words) <= _REQUEST_TITLE_MAX_WORDS and not looks_like_action_clause(title):
            return title
    return ""


def _confirmed_direction_title(value: str) -> str:
    """Read a product title from ``Confirmed direction Use <title>.`` evidence."""

    direction = confirmed_direction_evidence_text(value)
    first_sentence = direction.partition(".")[0].strip()
    words = request_words(first_sentence)
    if not words or word_key(words[0]) != "use":
        return ""
    title_words = [word.strip(".,:;!? ") for word in words[1:] if word.strip(".,:;!? ")]
    while title_words and word_key(title_words[0]) in {"a", "an", "the"}:
        title_words.pop(0)
    title = " ".join(title_words)
    if 1 <= len(title_words) <= _REQUEST_TITLE_MAX_WORDS and not looks_like_action_clause(title):
        return title
    return ""


def prompt_has_material_first_path_gap(value: str) -> bool:
    """Return whether an explicit actor path names only one material action."""

    product_text = product_intent_source_text(value)
    structured = structured_prompt_facts(product_text)
    if structured.first_path_contract and structured.first_path_contract.invalid_reasons:
        return True
    source = prompt_intent_source(product_text)
    need_actor, need_action = need_product_actor_action(product_text)
    model = first_path_model(source.first_path)
    actor, action = modal_actor_action_parts(source.first_path)
    if not actor or not action:
        actor, action = actor_led_action_parts(source.first_path)
    return bool(
        len(model.steps) < 2
        and (model.material_action or model.visible_outcome)
        and action
        and _starts_with_explicit_human_actor(actor)
        and not _contains_compound_action_path(source.first_path)
        and _is_observation_only_action(action)
        and not (need_actor and need_action)
    )


def prompt_has_material_actor_gap(value: str) -> bool:
    """Return whether action-rich evidence lacks a credible human first actor."""

    source = prompt_intent_source(value)
    model = first_path_model(source.first_path)
    if not model.material_action:
        return False
    actor = source.actor or _first_path_actor_candidate(source.first_path) or _first_path_actor_candidate(value)
    if actor:
        return is_automated_actor(actor) or not has_human_actor_signal(actor)
    return len(model.steps) >= 2


def _first_path_source_from_text(value: str) -> str:
    raw_text = strip_trailing_operator_instruction_sentences(clean_markdown_text(value).strip(" ."))
    if is_source_metadata_clause(raw_text):
        return ""
    text = _strip_operator_request_wrapper(raw_text)
    release_candidate = _release_action_sentence_source(raw_text) or _release_action_sentence_source(text)
    if word_count(release_candidate) >= 8 and _looks_like_recoverable_first_path(release_candidate):
        return _strip_release_proof_tail(release_candidate)
    ranked = ranked_first_path_evidence(text)
    if ranked:
        return _strip_release_proof_tail(ranked)
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        candidate = sentence.strip(" .")
        if (
            candidate
            and not is_labeled_non_path_evidence(candidate)
            and not _labeled_request_title(candidate)
            and not is_non_path_evidence(candidate)
            and not is_external_dependency_clause(candidate)
            and not is_source_metadata_clause(candidate)
            and word_count(candidate) >= 8
            and _looks_like_recoverable_first_path(candidate)
        ):
            return _strip_release_proof_tail(candidate)
    grant_actor, grant_first_path = _path_grant_actor_action(raw_text)
    if grant_actor and word_count(grant_first_path) >= 8 and _looks_like_recoverable_first_path(grant_first_path):
        return _strip_release_proof_tail(grant_first_path)
    workflow_actor, workflow_first_path = _workflow_where_actor_action(raw_text)
    if workflow_actor and word_count(workflow_first_path) >= 8 and _looks_like_recoverable_first_path(workflow_first_path):
        return _strip_release_proof_tail(workflow_first_path)
    actor_led_candidate = _actor_led_relative_clause_source(raw_text)
    if word_count(actor_led_candidate) >= 8 and _looks_like_recoverable_first_path(actor_led_candidate):
        return _strip_release_proof_tail(actor_led_candidate)
    for marker in ("where", "that", "for", "who"):
        candidate = _tail_after_word(raw_text, marker)
        if not candidate:
            continue
        candidate_rows = sentence_fragments(candidate)
        candidate = candidate_rows[0] if candidate_rows else candidate
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    if (
        not is_labeled_non_path_evidence(text)
        and not _labeled_request_title(text)
        and not is_non_path_evidence(text)
        and _looks_like_recoverable_first_path(text)
    ):
        return _strip_release_proof_tail(text)
    for marker in ("so",):
        candidate = _tail_after_word(raw_text, marker)
        if not candidate:
            continue
        candidate = _strip_operator_request_wrapper(candidate)
        if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
            return _strip_release_proof_tail(candidate)
    return (
        ""
        if is_labeled_non_path_evidence(text) or _labeled_request_title(text) or is_non_path_evidence(text)
        else _strip_release_proof_tail(text)
    )


def _direct_actor_action_sentence(value: str) -> tuple[str, str]:
    """Recover the first declarative user path before trailing proof constraints."""

    product_title = explicit_product_title_evidence(value).casefold()
    for sentence in sentence_fragments(value):
        text = _without_leading_context_clause(clean_markdown_text(sentence).strip(" ."))
        if _is_release_boundary_statement(text) or is_non_path_evidence(text):
            continue
        role_actor, role_first_path = _role_object_record_path(text)
        if role_actor and role_first_path:
            return role_actor, role_first_path
        explicit_actor, explicit_action, article = _explicit_human_actor_action(text)
        if _is_role_bound_review_statement(text):
            explicit_action = _strip_role_bound_review_requirement(explicit_action)
        if (
            explicit_actor
            and explicit_action
            and explicit_actor.casefold() != product_title
        ):
            if article:
                return explicit_actor, f"{article.capitalize()} {explicit_actor} {explicit_action}"
            canonical_action = base_action_clause(explicit_action, force_leading_finite=True).strip(" .") or explicit_action
            return explicit_actor, f"{explicit_actor} can {canonical_action}"
        match = direct_actor_action_match(text)
        if not match:
            continue
        actor = _strip_leading_actor_article(match.actor)
        action = match.action.strip(" .")
        if (
            not actor
            or not action
            or actor.casefold() == product_title
            or not _is_bounded_prompt_actor(actor)
            or not (
                has_human_actor_action_context(actor, action)
                or _single_proper_person_actor(actor)
            )
        ):
            continue
        if match.gerund:
            verb, _separator, tail = action.partition(" ")
            action = f"{_base_direct_gerund(verb) or verb} {tail}".strip(" .")
            return actor, f"{actor} can {action}"
        return actor, f"{actor} {action}"
    return "", ""


def _role_bound_review_actor_action(value: str) -> tuple[str, str]:
    """Recover the human owner of a role-object review requirement."""

    for sentence in sentence_fragments(value):
        text = _without_leading_context_clause(clean_markdown_text(sentence).strip(" ."))
        if _is_release_boundary_statement(text) or is_non_path_evidence(text):
            continue
        actor, first_path = _role_object_record_path(text)
        if actor and first_path:
            return actor, first_path
    return "", ""


def _without_leading_context_clause(value: str) -> str:
    prefix, separator, action = value.partition(",")
    if separator and is_contextual_path_step(prefix):
        return action.strip(" .")
    return value


def _leading_role_purpose_action_path(value: str) -> tuple[str, str]:
    """Recover an explicit `<role> for <purpose>; <actions>` first path."""

    text = clean_markdown_text(value).strip(" .")
    match = re.match(
        r"^(?P<actor>[A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z][A-Za-z0-9'/-]*){0,5})"
        r"\s+for\s+(?P<purpose>[^.;]{3,180});\s*(?P<actions>.+)$",
        text,
    )
    if not match:
        return "", ""
    actor = _strip_leading_actor_article(match.group("actor"))
    purpose = clean_markdown_text(match.group("purpose")).strip(" .")
    action_source = clean_markdown_text(match.group("actions")).strip(" .")
    if (
        not actor
        or not purpose
        or not has_human_actor_role_signal(actor)
        or not looks_like_action_clause(action_source)
    ):
        return "", ""
    action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
    if not action or not _looks_like_recoverable_first_path(action):
        return "", ""
    first_action, separator, remaining_actions = action.partition(",")
    action_with_purpose = f"{first_action.strip()} for {purpose}"
    if separator and remaining_actions.strip():
        action_with_purpose = f"{action_with_purpose}, {remaining_actions.strip()}"
    return actor, f"{actor} can {action_with_purpose}".strip(" .")


def _role_object_record_path(value: str) -> tuple[str, str]:
    """Keep a role's record object out of its actor label in a review constraint."""

    text = clean_markdown_text(value).strip(" .")
    match = re.match(
        r"^(?:the\s+)?(?P<actor>[A-Za-z][A-Za-z0-9'/-]*)\s+"
        r"(?P<object>[A-Za-z][A-Za-z0-9'/-]{1,80})\s+records?\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    if not _is_role_bound_review_statement(text):
        return "", ""
    actor = _strip_leading_actor_article(match.group("actor"))
    object_text = clean_markdown_text(match.group("object")).strip(" .")
    if not actor or not object_text or not has_human_actor_role_signal(actor):
        return "", ""
    return actor, f"{actor} can review {actor.casefold()} {object_text} records and release readiness"


def _explicit_human_actor_action(value: str) -> tuple[str, str, str]:
    """Recover a direct unfamiliar actor only from its own finite action clause."""

    words = request_words(clean_markdown_text(value).strip(" ."))
    for boundary in range(1, min(5, len(words) - 1) + 1):
        actor_words = words[:boundary]
        action_words = words[boundary:]
        if word_key(actor_words[-1]) in _MULTI_ROLE_MODAL_TOKENS:
            continue
        owned_action = re.split(
            r"\b(?:after|before|if|once|until|when|while)\b",
            " ".join(action_words),
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        owned_words = request_words(owned_action)
        if (
            len(owned_words) >= 2
            and word_key(owned_words[0]).endswith("ly")
            and looks_like_action_clause(" ".join(owned_words[1:]))
        ):
            owned_action = " ".join(owned_words[1:])
        actor_source = " ".join(actor_words)
        actor = _strip_leading_actor_article(actor_source)
        if not has_human_actor_action_context(actor_source, owned_action):
            continue
        action = " ".join(action_words).strip(" .")
        if actor and action and _looks_like_recoverable_first_path(action):
            article = word_key(actor_words[0]) if word_key(actor_words[0]) in {"a", "an", "the"} else ""
            return actor, action, article
    return "", "", ""


def _is_release_boundary_statement(value: str) -> bool:
    return is_release_evidence_requirement(value) or bool(
        re.match(
            r"^(?:the\s+)?first\s+release\s+(?:boundary|scope)\b",
            clean_markdown_text(value).strip(),
            flags=re.IGNORECASE,
        )
    )


def _is_role_bound_review_statement(value: str) -> bool:
    text = clean_markdown_text(value).strip()
    return bool(re.search(r"\bmust\s+be\s+reviewable\b", text, flags=re.IGNORECASE))


def _strip_role_bound_review_requirement(value: str) -> str:
    """Retain a preceding user action while excluding a trailing proof requirement."""

    text = clean_markdown_text(value).strip(" .")
    return re.sub(
        r"\s+(?:and|but)\s+[^.;]{0,120}?\bmust\s+be\s+reviewable\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")


def _multi_role_modal_first_path(value: str) -> tuple[str, str]:
    """Select one accountable role from a multi-role modal workflow sentence."""

    for sentence in sentence_fragments(value):
        text = clean_markdown_text(sentence).strip(" .")
        if not text or looks_like_trailing_operator_instruction(text):
            continue
        words = request_words(text)
        for modal_index, word in enumerate(words[1:], start=1):
            if word_key(word) not in _MULTI_ROLE_MODAL_TOKENS:
                continue
            if modal_index + 1 < len(words) and word_key(words[modal_index + 1]) == "not":
                continue
            actor_words = words[:modal_index]
            if any(word_key(actor_word) in {"if", "that", "what", "when", "where", "whether", "which", "who"} for actor_word in actor_words):
                continue
            comma_index = next(
                (index for index, actor_word in enumerate(actor_words) if str(actor_word).rstrip().endswith(",")),
                -1,
            )
            if comma_index <= 0:
                continue
            primary = _strip_leading_actor_article(" ".join(actor_words[: comma_index + 1])).strip(" ,.")
            if not primary or not _looks_like_actor_purpose_left(request_words(primary)):
                recovered = leading_actor_action_match(text)
                if recovered:
                    recovered_actor, recovered_action = recovered
                    candidate = f"{recovered_actor} can {recovered_action}".strip(" .")
                    if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
                        return recovered_actor, candidate
                continue
            action = " ".join(words[modal_index + 1 :]).strip(" .")
            candidate = f"{primary} can {action}".strip(" .")
            outcome_clause = before_can_outcome_clause(action)
            if outcome_clause:
                candidate = f"{primary} can {outcome_clause}"
            if word_count(candidate) >= 8 and _looks_like_recoverable_first_path(candidate):
                return primary, candidate
    return "", ""


def _base_direct_gerund(value: str) -> str:
    token = str(value or "").casefold().strip(".,:;")
    if not token.endswith("ing") or len(token) <= 5:
        return ""
    stem = token[:-3]
    if len(stem) >= 3 and stem[-1:] == stem[-2:-1]:
        return stem[:-1]
    if stem.endswith(("at", "it", "iz", "os", "v")):
        return f"{stem}e"
    return stem


def _request_content_start(words: list[str]) -> tuple[int, bool]:
    command_led = len(words) >= 3 and words[0].casefold() in REQUEST_COMMAND_WORDS
    start = 1 if command_led else 0
    if start < len(words) and words[start].casefold() in {"a", "an", "the"}:
        start += 1
    if command_led:
        start = _skip_proposal_wrapper(words, start)
    return start, command_led


def _project_title_source_from_words(words: list[str], *, start: int, command_led: bool) -> str:
    if start >= len(words):
        return ""
    lowered = [word.casefold().strip(",:;") for word in words]
    for index in range(start + 1, len(words)):
        connector = lowered[index]
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        if not command_led and connector not in _DIRECT_TITLE_BOUNDARY_CONNECTORS:
            tail = " ".join(words[index + 1 :]).strip(" .")
            if not _looks_like_recoverable_first_path(tail):
                continue
        lead = _lead_before_sentence_boundary(words[start:index]) or words[start:index]
        if _looks_like_product_title_phrase(lead):
            return " ".join(lead).strip(" .")
        tail = " ".join(words[index + 1 :]).strip(" .")
        if command_led and _looks_like_explicit_title_before_workflow_context(lead, tail=tail):
            return " ".join(lead).strip(" .")
        if command_led and _looks_like_target_focus_phrase(lead, tail=tail):
            return " ".join(lead).strip(" .")
    sentence_title = _project_title_before_sentence_boundary(words, start=start, command_led=command_led)
    if sentence_title:
        return sentence_title
    lead = words[start:]
    if _looks_like_product_title_phrase(lead):
        return " ".join(lead).strip(" .")
    return ""


def _lead_before_sentence_boundary(words: list[str]) -> list[str]:
    lead: list[str] = []
    for word in words:
        cleaned = str(word or "").strip()
        if not cleaned:
            continue
        lead.append(cleaned.strip(".,:;"))
        if cleaned.endswith((".", "!", "?")):
            break
    return lead if lead and len(lead) < len(words) else []


def _project_title_before_sentence_boundary(words: list[str], *, start: int, command_led: bool = False) -> str:
    lead: list[str] = []
    tail_start = start
    for offset, raw in enumerate(words[start:], start=start):
        tail_start = offset + 1
        token = raw.strip()
        cleaned = token.strip(".,:;")
        if cleaned.casefold() in _REQUEST_LEAD_CONNECTORS:
            return ""
        if cleaned:
            lead.append(cleaned)
        if token.endswith((".", "!", "?")):
            break
    if _looks_like_product_title_phrase(lead):
        return " ".join(lead).strip(" .")
    if command_led and _looks_like_explicit_title_before_workflow_context(
        lead,
        tail=" ".join(words[tail_start:]).strip(" ."),
    ):
        return " ".join(lead).strip(" .")
    if command_led and _looks_like_target_focus_phrase(lead, tail=" ".join(words[tail_start:]).strip(" .")):
        return " ".join(lead).strip(" .")
    return ""


def _skip_proposal_wrapper(words: list[str], start: int) -> int:
    index = start
    saw_request_wrapper = False
    while index < len(words) and words[index].casefold().strip(",:;") in {
        "greenfield",
        "new",
        "product-first",
    }:
        saw_request_wrapper = True
        index += 1
    if (
        index < len(words)
        and word_key(words[index]) == "same"
        and _contains_token_sequence(words[index + 1 :], ("this", "order", "of", "work"))
    ):
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") in {"proposal", "product"}:
        index += 1
    elif (
        index < len(words)
        and words[index].casefold().strip(",:;") == "project"
        and (
            saw_request_wrapper
            or (index + 1 < len(words) and words[index + 1].casefold().strip(",:;") == "for")
        )
    ):
        index += 1
    if index < len(words) and words[index].casefold().strip(",:;") == "for":
        index += 1
    if (
        index + 1 < len(words)
        and words[index].casefold().strip(",:;") == "product"
        and words[index + 1].casefold().strip(",:;") == "for"
    ):
        index += 2
    if index < len(words) and words[index].casefold().strip(",:;") in {"a", "an", "the"}:
        index += 1
    return index


def _contains_token_sequence(words: list[str], sequence: tuple[str, ...]) -> bool:
    lowered = [word_key(word) for word in words]
    width = len(sequence)
    return any(tuple(lowered[index : index + width]) == sequence for index in range(len(lowered) - width + 1))


def _tail_after_word(value: str, marker: str) -> str:
    words = request_words(value)
    for index, word in enumerate(words[:-1]):
        if word.casefold().strip(".,:;") != marker:
            continue
        return " ".join(words[index + 1 :]).strip(" .")
    return ""


def _actor_led_relative_clause_source(value: str) -> str:
    _actor, first_path = _actor_led_relative_clause(value)
    return first_path


def _workflow_where_actor_action(value: str) -> tuple[str, str]:
    words = request_words(value)
    lowered = [word_key(word) for word in words]
    for marker_index, token in enumerate(lowered[:-3]):
        if token != "where":
            continue
        tail_words = words[marker_index + 1 :]
        for action_index in range(1, min(len(tail_words), 5) + 1):
            actor_words = tail_words[:action_index]
            action_words = tail_words[action_index:]
            actor_words, action_words = _trim_actor_action_split(actor_words, action_words)
            recognized_actor = _looks_like_actor_split_left(
                actor_words,
                allow_bounded_workflow_phrase=True,
            )
            if not action_words or not (
                recognized_actor
                or has_human_actor_action_context(" ".join(actor_words), " ".join(action_words))
            ):
                continue
            action_source = _smooth_request_first_path_clause(" ".join(action_words))
            if not (
                looks_like_action_clause(action_source)
                or _looks_like_direct_transformation_workflow_action(action_source)
            ):
                continue
            action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
            if action and _looks_like_recoverable_first_path(action):
                article = word_key(actor_words[0]) if word_key(actor_words[0]) in {"a", "an", "the"} else ""
                actor = _strip_leading_actor_article(" ".join(actor_words))
                subject = actor if recognized_actor else f"{article.capitalize()} {actor}".strip()
                return actor, f"{subject} {action_source}".strip(" .")
    return "", ""


def _non_human_subject_relative_action(value: str) -> str:
    """Keep a supplied action when a product-relative `for <system> that` clause has no human actor."""

    words = request_words(value)
    for for_index, word in enumerate(words[:-3]):
        if word_key(word) != "for":
            continue
        tail = words[for_index + 1 :]
        for relative_index, relative_word in enumerate(tail[:-1]):
            if word_key(relative_word) != "that":
                continue
            subject_words = tail[:relative_index]
            action_words = tail[relative_index + 1 :]
            if not subject_words or not action_words or not _looks_like_non_human_subject(subject_words):
                continue
            action_source = _smooth_request_first_path_clause(" ".join(action_words))
            action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
            if _looks_like_recoverable_first_path(action):
                return action
    return ""


def _path_grant_actor_action(value: str) -> tuple[str, str]:
    audience = re.match(
        r"^(?:give|provide)\s+(?P<actor>(?:a|an|the)\s+[A-Za-z][A-Za-z0-9'/-]*)\s+"
        r"(?:a|an|the)\s+",
        clean_markdown_text(value).strip(),
        flags=re.IGNORECASE,
    )
    if audience and has_human_actor_role_signal(audience.group("actor")):
        return _strip_leading_actor_article(audience.group("actor")), ""
    words = request_words(value)
    lowered = [word_key(word) for word in words]
    actor_candidate = ""
    for grant_index, token in enumerate(lowered[:-4]):
        if token not in {"give", "gives", "grant", "grants", "provide", "provides"}:
            continue
        actor, action = _path_grant_tail_parts(words[grant_index + 1 :])
        actor_candidate = actor_candidate or actor
        if actor and action:
            return actor, f"{actor} {action}".strip(" .")
    return actor_candidate, ""


def _path_grant_tail_parts(words: list[str]) -> tuple[str, str]:
    lowered = [word_key(word) for word in words]
    for path_index, token in enumerate(lowered[:-1]):
        if token != "path":
            continue
        actor_stop = _path_grant_actor_stop(words, path_index)
        if actor_stop <= 0:
            continue
        actor_words = words[:actor_stop]
        if not _looks_like_actor_purpose_left(actor_words):
            continue
        action_start = path_index + 1
        actor = _strip_leading_actor_article(" ".join(actor_words))
        if action_start >= len(words) or word_key(words[action_start]) != "to":
            return actor, ""
        action_start += 1
        action_words = words[action_start:]
        if not action_words:
            continue
        action_source = _smooth_request_first_path_clause(" ".join(action_words))
        action = base_action_clause(action_source, force_leading_finite=True).strip(" .") or action_source
        if action and _looks_like_recoverable_first_path(action):
            return actor, action
    return "", ""


def _path_grant_actor_stop(words: list[str], path_index: int) -> int:
    stop = path_index
    while stop > 0 and word_key(words[stop - 1]) in _PATH_GRANT_PATH_MODIFIERS:
        stop -= 1
    if stop == path_index:
        stop = next(
            (
                index
                for index in range(path_index - 1, max(0, path_index - 4), -1)
                if word_key(words[index]) in {"a", "an", "the"}
            ),
            stop,
        )
    return stop


def _actor_led_relative_clause(value: str) -> tuple[str, str]:
    words = request_words(value)
    lowered = [word.casefold().strip(".,:;") for word in words]
    for for_index, token in enumerate(lowered[:-3]):
        if token != "for":
            continue
        for connector_index in range(for_index + 2, len(words) - 1):
            if lowered[connector_index] not in {"that", "who"}:
                continue
            raw_tail_words = words[connector_index + 1 :]
            embedded_actor, embedded_action = _helper_relative_actor_action(raw_tail_words)
            if embedded_actor and embedded_action:
                return embedded_actor, f"{embedded_actor} {embedded_action}".strip(" .")
            use_actor, use_action = _use_to_actor_action(raw_tail_words)
            if use_actor and use_action:
                return use_actor, f"{use_actor} {use_action}".strip(" .")
            actor_words = _actor_role_suffix(words[for_index + 1 : connector_index])
            actor_words, moved_action_words = _trim_actor_action_split(actor_words, [])
            tail_words = raw_tail_words
            if moved_action_words:
                tail_words = [*moved_action_words, *tail_words]
            actor_source = " ".join(actor_words)
            action_source = " ".join(tail_words)
            connector = lowered[connector_index]
            role_context = _looks_like_actor_purpose_left(actor_words)
            bounded_actor_context = bool(
                connector == "who" and _looks_like_bounded_workflow_actor_phrase(actor_words)
            )
            article_led_context = bool(
                actor_words
                and word_key(actor_words[0]) in {"a", "an", "the"}
                and not any(word.rstrip().endswith((".", ",", ";", ":", "!", "?")) for word in actor_words)
                and has_human_actor_action_context(actor_source, action_source)
            )
            if not actor_words or not tail_words or not (
                role_context or bounded_actor_context or article_led_context
            ):
                continue
            use_actor, use_action = _use_to_actor_action(tail_words)
            if use_actor and use_action:
                return use_actor, f"{use_actor} {use_action}".strip(" .")
            action = base_action_clause(_smooth_request_first_path_clause(action_source), force_leading_finite=True)
            if action:
                article = word_key(actor_words[0]) if word_key(actor_words[0]) in {"a", "an", "the"} else ""
                actor = _strip_leading_actor_article(actor_source)
                if connector == "who":
                    return actor, f"{actor} {connector} {action}".strip(" .")
                if article_led_context and not role_context and article:
                    return actor, f"{article.capitalize()} {actor} can {action}".strip(" .")
                return actor, f"{actor} {action}".strip(" .")
    return "", ""


def _actor_role_suffix(words: list[str]) -> list[str]:
    """Prefer the role-bearing suffix when a product title wraps a for-who clause."""

    for index, word in enumerate(words[:-1]):
        if word_key(word) != "for":
            continue
        suffix = words[index + 1 :]
        if suffix and _looks_like_actor_purpose_left(suffix):
            return suffix
    return words


def _trim_actor_action_split(actor_words: list[str], action_words: list[str]) -> tuple[list[str], list[str]]:
    words = list(actor_words)
    tokens = [word_key(word) for word in words]
    for index, token in enumerate(tokens[1:], start=1):
        if token in {"who", "that", "where"}:
            break
        if not (
            _looks_like_actor_purpose_left(words[:index])
            or _looks_like_bounded_workflow_actor_phrase(words[:index])
        ):
            continue
        action_tail = " ".join(words[index:]).strip(" .")
        if looks_like_action_clause(action_tail):
            return words[:index], [*words[index:], *action_words]
    return actor_words, action_words


def _use_to_actor_action(words: list[str]) -> tuple[str, str]:
    for use_index, word in enumerate(words[:-2]):
        if word_key(word) not in {"use", "uses", "used"} or word_key(words[use_index + 1]) != "to":
            continue
        actor_words = words[:use_index]
        action_words = words[use_index + 2 :]
        if not actor_words or not action_words or not _looks_like_use_to_actor_left(actor_words):
            continue
        action = base_action_clause(_smooth_request_first_path_clause(" ".join(action_words)), force_leading_finite=True)
        if action:
            return _strip_leading_actor_article(" ".join(actor_words)), action
    return "", ""


def _looks_like_use_to_actor_left(words: list[str]) -> bool:
    if _looks_like_actor_purpose_left(words):
        return True
    tail = _actor_purpose_tail(words)
    if not tail or len(tail) > 4:
        return False
    last = tail[-1].casefold().strip(".,:;")
    return len(last) > 3 and last.endswith("s") and last not in _REQUEST_PRODUCT_WORDS


def _looks_like_actor_split_left(words: list[str], *, allow_bounded_workflow_phrase: bool = False) -> bool:
    if _looks_like_non_human_subject(words):
        return False
    if not _looks_like_actor_purpose_left(words) and not (
        allow_bounded_workflow_phrase and _looks_like_bounded_workflow_actor_phrase(words)
    ):
        return False
    tokens = [word_key(word) for word in words if word_key(word)]
    if any(any(mark in str(word) for mark in (",", ";", ":")) for word in words):
        return False
    if any(token in {"and", "or", "then"} for token in tokens):
        return False
    return not looks_like_action_clause(" ".join(words))


def _looks_like_non_human_subject(words: list[str]) -> bool:
    content = [word_key(word) for word in words if word_key(word)]
    if not content:
        return False
    normalized = {
        token[:-1] if token.endswith("s") and len(token) > 3 else token
        for token in content
    }
    if content[-1] in _NON_HUMAN_SUBJECT_TERMINALS:
        return True
    if len(content) == 1 and (content[0] in _NON_HUMAN_SUBJECT_TERMS or normalized & _NON_HUMAN_SUBJECT_TERMS):
        return True
    if _looks_like_actor_purpose_left(words):
        return False
    return bool((set(content) | normalized) & _NON_HUMAN_SUBJECT_TERMS)


def _looks_like_bounded_workflow_actor_phrase(words: list[str]) -> bool:
    content = [word_key(word) for word in words if word_key(word)]
    while content and content[0] in {"a", "an", "the", "one"}:
        content = content[1:]
    if not 2 <= len(content) <= 4:
        return False
    if any(token in {"and", "or", "then"} for token in content):
        return False
    if any(token in REQUEST_COMMAND_WORDS for token in content):
        return False
    if set(content) <= _REQUEST_PRODUCT_WORDS:
        return False
    if looks_like_action_clause(" ".join(content)):
        return False
    return any(token not in {"case", "context", "record", "request", "review", "workflow"} for token in content)


def _looks_like_direct_transformation_workflow_action(value: str) -> bool:
    words = request_words(value)
    if not words:
        return False
    action = word_key(words[0])
    if action in {"capture", "captures", "record", "records", "register", "registers"}:
        return len(first_path_model(value).steps) == 1
    if action in {"replay", "replays"}:
        return _is_replay_workflow_action(value)
    if action in {"convert", "converts", "transform", "transforms", "translate", "translates", "turn", "turns"}:
        return " into " in f" {clean_markdown_text(value).casefold()} "
    model = first_path_model(value)
    return looks_like_action_clause(value) and len(model.steps) == 1 and bool(
        model.material_action or model.visible_outcome
    )


def _is_replay_workflow_action(value: str) -> bool:
    words = request_words(value)
    return len(words) >= 3 and word_key(words[0]) in {"replay", "replays"}


def _helper_relative_actor_action(words: list[str]) -> tuple[str, str]:
    if len(words) < 3 or word_key(words[0]) not in _REQUEST_HELPER_WORDS:
        return "", ""
    tail_words = words[1:]
    if tail_words and word_key(tail_words[0]) == "to":
        tail_words = tail_words[1:]
    role_candidates: list[tuple[str, str]] = []
    workflow_candidates: list[tuple[str, str]] = []
    for split_index in range(1, min(len(tail_words), 5) + 1):
        actor_words = tail_words[:split_index]
        action_words = tail_words[split_index:]
        if not action_words:
            continue
        explicit_role = _looks_like_actor_purpose_left(actor_words)
        article_led = bool(actor_words and word_key(actor_words[0]) in {"a", "an", "the"})
        explicit_actor_context = article_led and has_human_actor_action_context(
            " ".join(actor_words),
            " ".join(action_words),
        )
        bounded_workflow = _looks_like_bounded_workflow_actor_phrase(actor_words)
        if not explicit_role and not explicit_actor_context and not bounded_workflow:
            continue
        action_source = _smooth_request_first_path_clause(" ".join(action_words))
        if not looks_like_action_clause(action_source):
            continue
        action = base_action_clause(action_source, force_leading_finite=True)
        if action:
            candidate = (_strip_leading_actor_article(" ".join(actor_words)), action)
            if explicit_role or explicit_actor_context:
                role_candidates.append(candidate)
            else:
                workflow_candidates.append(candidate)
    if role_candidates:
        return role_candidates[0]
    if workflow_candidates:
        return workflow_candidates[0]
    return "", ""


def _strip_leading_actor_article(value: str) -> str:
    words = request_words(value)
    if words and word_key(words[0]) in {"a", "an", "the"}:
        words = words[1:]
    return " ".join(words).strip(" .")


def _strip_operator_request_wrapper(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return ""
    for candidate in _operator_request_tail_candidates(text):
        smoothed = _smooth_request_first_path_clause(_strip_leading_helper_word(candidate))
        if word_count(smoothed) >= 4 and _looks_like_recoverable_first_path(smoothed):
            return smoothed
    return _smooth_request_first_path_clause(_strip_leading_helper_word(text))


def _release_action_sentence_source(value: str) -> str:
    for sentence in sentence_fragments(value):
        candidate = _strip_release_helper_prefix(sentence)
        if candidate != clean_markdown_text(sentence).strip(" ."):
            return candidate
    return ""


def _is_bounded_prompt_actor(value: str) -> bool:
    words = request_words(value)
    return bool(
        words
        and len(words) <= 6
        and not any(word.endswith((".", "!", "?")) for word in words)
        and not _looks_like_non_human_subject(words)
    )


def _single_proper_person_actor(value: str) -> bool:
    words = request_words(value)
    return bool(
        len(words) == 1
        and words[0][:1].isupper()
        and not has_non_human_actor_signal(value)
    )


def _for_role_actor_gerund_path(value: str) -> tuple[str, str]:
    """Recover a bounded `for <role> <gerund>` product path."""

    words = request_words(value)
    for index, word in enumerate(words[:-2]):
        if word_key(word) != "for":
            continue
        tail = words[index + 1 :]
        for boundary in range(1, min(5, len(tail) - 1) + 1):
            actor_words = tail[:boundary]
            action_head = word_key(tail[boundary])
            if not action_head.endswith("ing") or not _looks_like_actor_purpose_left(actor_words):
                continue
            actor = _strip_leading_actor_article(" ".join(actor_words))
            action = _smooth_request_first_path_clause(" ".join(tail[boundary:]))
            followup = _contextual_gerund_followup_action(action)
            if actor and followup:
                return actor, f"{actor} can {followup}"
            if actor and action and _looks_like_recoverable_first_path(action):
                return actor, f"{actor} {action}"
    return "", ""


def _contextual_gerund_followup_action(value: str) -> str:
    """Use the next workflow sentence when a role-gerund phrase is audience context."""

    rows = sentence_fragments(value)
    if len(rows) < 2 or not word_key(rows[0].split(maxsplit=1)[0]).endswith("ing"):
        return ""
    followup = re.sub(r"^(?:each|the)\s+\w+\s+", "", rows[1].strip(), flags=re.IGNORECASE)
    action = base_action_clause(followup, force_leading_finite=True).strip(" .")
    return action if action and _looks_like_recoverable_first_path(action) else ""


def _strip_release_helper_prefix(value: str) -> str:
    words = request_words(value)
    lowered = [word_key(word) for word in words]
    for index, token in enumerate(lowered):
        if token not in _REQUEST_HELPER_WORDS:
            continue
        prefix = set(lowered[:index])
        if not (prefix & {"first", "product", "release", "should", "version"}):
            continue
        tail = words[index + 1 :]
        if tail and tail[0].casefold() == "to":
            tail = tail[1:]
        return _smooth_request_first_path_clause(" ".join(tail))
    return clean_markdown_text(value).strip(" .")


def _operator_request_tail_candidates(value: str) -> tuple[str, ...]:
    words = request_words(value)
    if len(words) < 3:
        return ()
    lowered = [word.casefold() for word in words]
    start = 1 if lowered[0] in REQUEST_COMMAND_WORDS else 0
    if start < len(lowered) and lowered[start] in {"a", "an", "the"}:
        start += 1
    if start >= len(words):
        return ()
    command_led = lowered[0] in REQUEST_COMMAND_WORDS
    candidates: list[str] = []
    lead_words = lowered[start:]
    for index in range(start, len(words) - 1):
        connector = lowered[index].strip(",:;")
        if connector not in _REQUEST_LEAD_CONNECTORS:
            continue
        if not command_led and connector in {"for", "to"}:
            continue
        lead = lead_words[: max(0, index - start)]
        if not command_led and not (set(lead) & _REQUEST_PRODUCT_WORDS):
            continue
        tail = " ".join(words[index + 1 :]).strip(" ,.;:")
        if tail:
            candidates.append(tail)
    if command_led:
        candidates.append(" ".join(words[start:]))
    return tuple(dict.fromkeys(candidates))


def _strip_leading_helper_word(value: str) -> str:
    words = request_words(value)
    if len(words) < 2:
        return clean_markdown_text(value).strip(" .")
    if words[0].casefold() not in _REQUEST_HELPER_WORDS:
        return clean_markdown_text(value).strip(" .")
    tail_words = words[1:]
    if tail_words and tail_words[0].casefold() == "to":
        tail_words = tail_words[1:]
    return " ".join(tail_words).strip(" .")


def _smooth_request_first_path_clause(value: str) -> str:
    normalized = _normalize_request_reporting_product_clauses(value)
    words = request_words(strip_trailing_requirement_control_steps(normalized))
    if not words:
        return ""
    while words and words[0].casefold() == "to":
        words = words[1:]
    words = _drop_relative_use_to_action(words)
    if len(words) < 3:
        return " ".join(words).strip(" .")
    smoothed: list[str] = []
    for index, word in enumerate(words):
        token = word.casefold().strip(".,:;")
        next_word = words[index + 1] if index + 1 < len(words) else ""
        previous = smoothed[-1].casefold().strip(".,:;") if smoothed else ""
        if (
            token == "to"
            and previous in _REQUEST_HELPER_WORDS
            and next_word
            and looks_like_action_clause(f"{next_word} result")
        ):
            smoothed.append("can")
            continue
        if (
            token == "to"
            and next_word
            and looks_like_action_clause(f"{next_word} result")
            and _looks_like_actor_purpose_left(smoothed)
        ):
            smoothed.append("can")
            continue
        smoothed.append(word)
    return " ".join(smoothed).strip(" .")


def _normalize_request_reporting_product_clauses(value: str) -> str:
    rows = sentence_fragments(clean_markdown_text(value).strip(" ."))
    if not rows:
        return ""
    normalized: list[str] = []
    for row in rows:
        product_clause = _request_reporting_product_clause(row)
        row_words = request_words(row)
        row_tokens = [word_key(word) for word in row_words]
        word_sense_subject = _request_reporting_word_sense_subject(row)
        has_recoverable_path = any(_looks_like_recoverable_first_path(previous) for previous in normalized)
        if has_recoverable_path and is_release_evidence_requirement(row):
            continue
        if word_sense_subject:
            if not has_recoverable_path:
                normalized.append(word_sense_subject)
            continue
        if _request_reporting_clause_is_word_sense(row):
            continue
        if product_clause and has_recoverable_path:
            continue
        if not product_clause and normalized and word_sense_content_clause_describes_comparison(row_tokens):
            continue
        normalized.append(product_clause or row)
    return ". ".join(row for row in normalized if row).strip(" .")


def _request_reporting_product_clause(value: str) -> str:
    words = request_words(value)
    if len(words) < 5:
        return ""
    lowered = [word_key(word) for word in words]
    subject_index = 1 if lowered[0] in {"a", "an", "the", "this", "that"} else 0
    if subject_index + 2 >= len(lowered):
        return ""
    if lowered[subject_index] not in {"instruction", "instructions", "prompt", "request"}:
        return ""
    if lowered[subject_index + 1] not in REQUEST_REPORTING_VERBS:
        return ""
    tail_words = words[subject_index + 2 :]
    if tail_words and word_key(tail_words[0]) == "that":
        tail_words = tail_words[1:]
    tail_keys = [word_key(word) for word in tail_words]
    if not word_sense_tail_starts_content_clause(tail_keys):
        return ""
    if word_sense_content_clause_describes_comparison(tail_keys):
        return ""
    return strip_request_reporting_custody_tail(clean_markdown_text(" ".join(tail_words))).strip(" .")


def _request_reporting_clause_is_word_sense(value: str) -> bool:
    subject_words, tail_words = _request_reporting_word_sense_tail(value)
    return bool(subject_words and tail_words)


def _request_reporting_word_sense_subject(value: str) -> str:
    parsed = _request_reporting_word_sense_tail(value)
    if not parsed:
        return ""
    subject_words, _tail_words = parsed
    subject = " ".join(subject_words).strip(" .")
    if len(subject_words) < 2:
        return ""
    return subject


def _request_reporting_word_sense_tail(value: str) -> tuple[list[str], list[str]]:
    words = request_words(value)
    if len(words) < 5:
        return [], []
    lowered = [word_key(word) for word in words]
    subject_index = 1 if lowered[0] in {"a", "an", "the", "this", "that"} else 0
    if subject_index + 2 >= len(lowered):
        return [], []
    if lowered[subject_index] not in {"instruction", "instructions", "prompt", "request"}:
        return [], []
    if lowered[subject_index + 1] not in REQUEST_REPORTING_VERBS:
        return [], []
    tail = words[subject_index + 2 :]
    if tail and word_key(tail[0]) == "that":
        tail = tail[1:]
    tail_keys = [word_key(word) for word in tail]
    if not word_sense_content_clause_describes_comparison(tail_keys):
        return [], []
    subject_words = _word_sense_content_subject_words(tail)
    if not subject_words:
        return [], []
    return subject_words, tail


def _word_sense_content_subject_words(words: list[str]) -> list[str]:
    tokens = [word_key(word) for word in words]
    index = 1 if tokens[:1] == ["that"] else 0
    if index < len(tokens) and tokens[index] in {"a", "an", "the", "this", "that"}:
        index += 1
    if index + 1 >= len(tokens):
        return []
    for verb_index in range(index + 1, min(len(tokens), index + 5)):
        token = tokens[verb_index]
        if token in {"as", "both"}:
            return []
        if token in WORD_SENSE_REPORTING_CONTENT_VERBS:
            return words[index:verb_index]
    return []


def _drop_relative_use_to_action(words: list[str]) -> list[str]:
    for index, word in enumerate(words[:-2]):
        token = word.casefold().strip(".,:;")
        next_token = words[index + 1].casefold().strip(".,:;")
        if token not in {"use", "uses", "used"} or next_token != "to":
            continue
        actor_words = words[:index]
        action_words = words[index + 2 :]
        if not actor_words or not action_words:
            continue
        if looks_like_action_clause(" ".join(action_words)):
            return [*actor_words, *action_words]
    return words


def _looks_like_actor_purpose_left(words: list[str]) -> bool:
    tail = _actor_purpose_tail(words)
    if not tail:
        return False
    last = tail[-1].casefold().strip(".,:;")
    singular = last[:-1] if last.endswith("s") else last
    return (
        last in _REQUEST_ACTOR_PURPOSE_TOKENS
        or singular in _REQUEST_ACTOR_PURPOSE_TOKENS
        or word_has_actor_role_signal(last)
        or word_has_actor_role_signal(singular)
        or has_human_actor_role_signal(" ".join(tail))
    )


def _actor_purpose_tail(words: list[str]) -> list[str]:
    start = 0
    for index, word in enumerate(words):
        token = word.casefold().strip(".,:;")
        if token in {"and", "or", "then"}:
            start = index + 1
    return [word for word in words[start:] if word.strip(".,:;")]


def _strip_release_proof_tail(value: str) -> str:
    text = clean_markdown_text(value).strip(" .")
    rows = sentence_fragments(text)
    visible_rows = [row for row in rows if is_release_visible_result_statement(row)]
    if visible_rows:
        base = ". ".join(row for row in rows if row not in visible_rows).strip(" .")
        preserved = [_release_visible_result_path_action(row) for row in visible_rows]
        return ". ".join(row for row in (_strip_release_proof_tail(base) if base else "", *preserved) if row)
    words = request_words(value)
    if len(words) < 5:
        return strip_requirement_control_tail(strip_trailing_requirement_control_steps(clean_markdown_text(value).strip(" .")))
    lowered = [word_key(word) for word in words]
    for index, word in enumerate(lowered[:-2]):
        if word not in {"before", "until", "when"}:
            continue
        if lowered[index + 1] not in {"release", "version"}:
            continue
        action_index = index + 2
        if action_index < len(words) and _looks_like_release_selector(words[action_index]):
            action_index += 1
        if _release_proof_tail_starts(lowered[action_index:]):
            return strip_requirement_control_tail(strip_trailing_requirement_control_steps(" ".join(words[:index]).strip(" ,.;:")))
    return strip_requirement_control_tail(strip_trailing_requirement_control_steps(clean_markdown_text(value).strip(" .")))


def _release_visible_result_path_action(value: str) -> str:
    match = re.search(
        r"\b(?P<action>(?:show|display|publish|produce|return)\s+.+)$",
        clean_markdown_text(value).strip(" ."),
        flags=re.IGNORECASE,
    )
    return match.group("action").strip(" .") if match else ""


def _with_release_visible_result(value: str, *, evidence: str) -> str:
    path_rows = sentence_fragments(clean_markdown_text(value).strip(" ."))
    embedded_release_rows = [row for row in path_rows if is_release_visible_result_statement(row)]
    path = ". ".join(row for row in path_rows if row not in embedded_release_rows).strip(" .")
    existing_action = _release_visible_result_path_action(path)
    existing_outcome = (
        _release_result_identity(existing_action)
        if existing_action
        else _visible_outcome_identity(first_path_model(path).visible_outcome)
    )
    known_outcomes = {existing_outcome}
    release_rows = [
        *embedded_release_rows,
        *(row for row in sentence_fragments(evidence) if is_release_visible_result_statement(row)),
    ]
    for row in release_rows:
        action = _release_visible_result_path_action(row)
        outcome = _release_result_identity(action)
        if not action or (outcome and outcome in known_outcomes):
            continue
        path = ". ".join(part for part in (path, action) if part)
        known_outcomes.add(outcome)
    return path


def _visible_outcome_identity(value: str) -> tuple[str, ...]:
    words = [word_key(word) for word in request_words(value)]
    while words and words[0] in {"a", "an", "one", "the"}:
        words.pop(0)
    return tuple(words)


def _release_result_identity(value: str) -> tuple[str, ...]:
    words = [word_key(word) for word in request_words(value)]
    if words:
        words.pop(0)
    while words and words[0] in {"a", "an", "one", "the"}:
        words.pop(0)
    return tuple(words)


def _release_proof_tail_starts(words: list[str]) -> bool:
    if not words:
        return False
    if words[0] in _RELEASE_PROOF_ACTION_WORDS:
        return True
    return len(words) >= 2 and words[0] == "is" and words[1] in {"complete", "completed", "ready"}


def _looks_like_release_selector(value: str) -> bool:
    token = str(value or "").strip(".,:;")
    return bool(token) and all(char.isalnum() or char in "._-" for char in token)


def _looks_like_product_title_phrase(words: list[str]) -> bool:
    if not words or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    if is_requester_product_framing(" ".join(words)):
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"} | _REQUEST_PRODUCT_WORDS:
        return False
    return bool(set(lowered) & _REQUEST_PRODUCT_WORDS) or any(word.isupper() and len(word) <= 6 for word in words)


def _looks_like_target_focus_phrase(words: list[str], *, tail: str) -> bool:
    if len(words) < 2 or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"}:
        return False
    if set(lowered) & REQUEST_COMMAND_WORDS:
        return False
    if set(lowered) & set(_REQUEST_LEAD_CONNECTORS):
        return False
    text = " ".join(words).strip(" .")
    if looks_like_action_clause(text):
        return False
    return _has_recoverable_first_path_context(tail)


def _looks_like_explicit_title_before_workflow_context(words: list[str], *, tail: str) -> bool:
    if len(words) < 2 or len(words) > _REQUEST_TITLE_MAX_WORDS:
        return False
    lowered = [word.casefold().strip(".,:;") for word in words]
    if set(lowered) <= {"new", "simple", "small", "greenfield"} | _REQUEST_PRODUCT_WORDS:
        return False
    if set(lowered) & set(_REQUEST_LEAD_CONNECTORS):
        return False
    return _has_recoverable_first_path_context(tail)


def _has_recoverable_first_path_context(value: str) -> bool:
    text = clean_markdown_text(value).strip(" .")
    if not text:
        return False
    if _looks_like_recoverable_first_path(text):
        return True
    source = _first_path_source_from_text(text)
    return bool(
        source
        and source.casefold() != text.casefold()
        and word_count(source) >= 8
        and _looks_like_recoverable_first_path(source)
    )


def _looks_like_recoverable_first_path(value: str) -> bool:
    model = first_path_model(value)
    return len(model.steps) >= 2 or bool(model.material_action or model.visible_outcome)


def _starts_with_explicit_human_actor(value: str) -> bool:
    text = clean_markdown_text(value).strip(" .")
    actor = _first_path_actor_candidate(text)
    if (
        actor
        and _is_bounded_prompt_actor(actor)
        and not has_non_human_actor_signal(actor)
    ):
        return True
    words = request_words(text)
    return bool(
        1 <= len(words) <= 6
        and has_human_actor_signal(text)
        and not has_non_human_actor_signal(text)
        and not looks_like_action_clause(text)
        and not first_path_model(text).material_action
    )


def _first_path_actor_candidate(value: str) -> str:
    text = clean_markdown_text(value)
    labeled_path = re.search(r"\bfirst\s+complete\s+path\s*:\s*(?P<path>.+)$", text, flags=re.IGNORECASE)
    if labeled_path:
        text = labeled_path.group("path")
    actor, _action = modal_actor_action_parts(text)
    if not actor:
        actor, _action = actor_led_action_parts(text)
    if not actor:
        leading = re.match(
            r"^(?:a|an|the)\s+(?P<actor>[A-Za-z][A-Za-z0-9 /&'()-]{1,80}?)\s+"
            r"(?:can|could|should|must|will|[A-Za-z]+s)\b",
            text,
            flags=re.IGNORECASE,
        )
        if leading:
            actor = leading.group("actor")
    return _strip_leading_actor_article(actor)


def _actor_recovery_needs_canonical_path(value: str, *, recovery_kind: str) -> bool:
    """Normalize only paths whose context or nested modal would otherwise corrupt actor recovery."""

    text = clean_markdown_text(value).strip(" .")
    return bool(
        len(first_path_model(text).steps) == 1
        and (
            recovery_kind == "leading"
            or re.search(
                r"\b(?:what|that|which|whether|who|when|where)\s+(?:can|could|must|should|will|would)\b",
                text,
                flags=re.IGNORECASE,
            )
        )
    )


def _contains_compound_action_path(value: str) -> bool:
    """Keep an explicitly rich first path out of the one-action clarification lane."""

    text = clean_markdown_text(value)
    material_actions = tuple(MATERIAL_ACTION_RE.finditer(text))
    if len(material_actions) >= 2:
        return True
    gerund_forms = set(GERUND_ACTION_VERBS.values())
    gerund_actions = [word for word in request_words(text) if word_key(word) in gerund_forms]
    return len(gerund_actions) >= 2


def _is_observation_only_action(value: str) -> bool:
    words = request_words(value)
    return bool(words and word_key(words[0]) in _OBSERVATION_ONLY_ACTIONS)


__all__ = [
    "PromptIntentSource",
    "product_intent_source_text",
    "prompt_first_path_source",
    "prompt_has_material_first_path_gap",
    "prompt_has_material_actor_gap",
    "prompt_intent_source",
    "prompt_project_title_source",
]
