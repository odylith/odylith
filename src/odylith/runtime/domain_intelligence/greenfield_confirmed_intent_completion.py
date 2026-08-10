from __future__ import annotations

import copy
import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common.prose_grammar import action_verb_pattern
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import repair_infinitive_base_form_drift
from odylith.runtime.common.prose_grammar import repair_modal_base_form_drift
from odylith.runtime.domain_intelligence.greenfield_actor_terms import word_has_actor_role_signal
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import completed_actor_rows as _completed_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import inline_result_phrase as _inline_result_phrase, outcome_action_phrase as _outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_context_completion import complete_external_boundary as _complete_external_boundary
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent_context_completion import normalize_confirmed_actor_context as _normalize_confirmed_actor_context
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_completion import complete_product_posture as _complete_product_posture
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_completion import first_release_actor_labels as _first_release_actor_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_text import visible_outcome_phrase as _visible_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import completed_system_rows as _completed_system_rows, state_label as _state_label, system_labels as _system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item as _boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items as _join
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_canonical_meaning import canonical_state_object_is_meaningful
from odylith.runtime.domain_intelligence.greenfield_first_path_completeness import first_path_has_distinct_outcome
from odylith.runtime.domain_intelligence.greenfield_first_path_completeness import has_concise_coordinated_first_path
from odylith.runtime.domain_intelligence.greenfield_first_path_completeness import has_rich_material_first_path_action
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import derived_title as _derived_title, title as _title, title_needs_repair as _title_needs_repair
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase, first_path_capability_phrase, first_path_outcome_phrase, has_presentation_only_title_marker, material_first_path_action, normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import repair_confirmed_intent_semantic_projections
from odylith.runtime.domain_intelligence.greenfield_text import clean_text, normalize_confirmed_proof_boundary_sentence, normalize_visible_result_language as _normalize_visible_result_terms


CORE_FIELD_MIN_WORDS = {"product_story": 28, "state_object": 12, "first_path": 18, "proof_boundary": 18}
_ACTOR_MODAL_ROLE_WORDS = frozenset({"lead", "leads", "people", "person", "rep", "reps", "staff", "team", "teams", "user", "users"})
_UNPUNCTUATED_META_CONTROL_PHRASE_RE = re.compile(
    r"\b(?:in\s+)?(?:the\s+)?smallest\s+version\s+of\s+(?:the\s+)?whole\s+product\b",
    re.IGNORECASE,
)

def complete_confirmed_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(intent))
    title_normalization = normalize_project_title(_title(result), fallback="Greenfield Project")
    if title_normalization.changed:
        if has_presentation_only_title_marker(title_normalization.raw_title):
            result.pop("source_title", None)
        else:
            result["source_title"] = result.get("source_title") or title_normalization.raw_title
        result["title"] = title_normalization.canonical_title
    title = _title(result)
    if not _completion_seed_is_sufficient(result):
        return result
    if _title_needs_repair(title):
        result["title"] = _derived_title(result, fallback=title)
        title = _title(result)
    _normalize_confirmed_core_language(result)
    result["human_actors"] = _completed_actor_rows(result, title=title)
    _normalize_confirmed_actor_context(result, title=title)
    result["internal_systems"] = _completed_system_rows(result, title=title)
    _complete_external_boundary(result)
    _complete_core_fields(result, title=title)
    _normalize_confirmed_core_language(result)
    repair_confirmed_intent_semantic_projections(result)
    _complete_product_posture(result, title=title)
    _normalize_confirmed_core_language(result)
    _normalize_confirmed_actor_context(result, title=title)
    return result


def _normalize_confirmed_core_language(intent: dict[str, Any]) -> None:
    title = _clean(intent.get("title"))
    for key in ("product_story", "first_path", "problem", "product_view"):
        text = _clean(intent.get(key))
        if text:
            normalized = (
                normalize_first_path(text, product_title=title)
                if key == "first_path"
                else _normalize_visible_result_language(_strip_prompt_prefixes(text))
            )
            normalized = _normalize_understand_object_phrase(normalized)
            intent[key] = _sentence(normalized)
    state = _clean(intent.get("state_object"))
    if state:
        intent["state_object"] = _sentence(_normalize_visible_result_language(_normalize_state_object(state)))
    proof = _clean(intent.get("proof_boundary"))
    if proof:
        intent["proof_boundary"] = _sentence(_normalize_visible_result_language(_normalize_proof_boundary(proof)))
    metrics = confirmed_text_values(intent.get("success_metrics"))
    if metrics:
        intent["success_metrics"] = [_sentence(_normalize_visible_result_language(_normalize_proof_boundary(row))) for row in metrics]
    for key in ("assumptions", "ambiguities", "non_goals"):
        rows = confirmed_text_values(intent.get(key))
        if rows:
            intent[key] = [_sentence(_normalize_visible_result_language(_normalize_open_clause(row))) for row in rows]
    if external_systems := [
        row for row in confirmed_text_values(intent.get("external_systems")) if not _is_no_external_systems_placeholder(row)
    ]:
        intent["external_systems"] = [
            normalized
            for row in external_systems
            if (normalized := _boundary_clause_item(_normalize_external_system_language(row), limit=180))
        ]
    else:
        intent["external_systems"] = []


def _normalize_open_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(
        r"\bwhere\s+(?P<subject>[^.;:]{2,140}?)\s+comes\s+from$",
        lambda match: f"where {match.group('subject').strip()} is sourced",
        text,
        flags=re.IGNORECASE,
    )
    return text


def _normalize_understand_object_phrase(value: str) -> str:
    """Add a determiner and source casing when a state noun follows ``understand``."""

    def replacement(match: re.Match[str]) -> str:
        words = match.group("object").split()
        normalized = " ".join(
            word if word.isupper() else f"{word[:1].lower()}{word[1:]}"
            for word in words
        )
        return f"understand the {normalized}"

    return re.sub(
        r"\bunderstand\s+(?P<object>[A-Z][A-Za-z0-9/_-]*(?:\s+[A-Z][A-Za-z0-9/_-]*){0,3})"
        r"(?=\s+(?:and|or|but|before|after|when|where|while|to)\b|[.,;:]|$)",
        replacement,
        value,
    )


def _normalize_external_system_language(value: str) -> str:
    text = clean_text(value)
    text = re.sub(
        r"^(?:optional|optionally|deferred|future|later|if\s+needed|if\s+available)(?:\s*:\s*|\s+)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return _clean(text)


def _is_no_external_systems_placeholder(value: str) -> bool:
    text = clean_text(value).casefold().strip(" .")
    if text in {"no", "none", "not any", "not required"}:
        return True
    if text.startswith("required for the first proof path"):
        return True
    return bool(
        re.match(r"^(?:no|none|not any)\s+external systems?\b", text)
        or re.match(r"^external systems?\s*:\s*(?:no|none|not any)\b", text)
    )


def _strip_prompt_prefixes(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"^(?:problem\s+to\s+solve|product\s+view|first\s+path|state\s+object)\s*:\s*", "", text, flags=re.I)
    return text.strip()


def _normalize_proof_boundary(value: str) -> str:
    text = _strip_prompt_prefixes(value)
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if len(sentences) > 1 and re.search(
        r"\b(?:confirmation-only|confirmed?\s+draft|no\s+product\s+code\s+exists)\b",
        sentences[0],
        flags=re.IGNORECASE,
    ):
        text = " ".join(sentences[1:]).strip()
    text = re.sub(r"^(?:done\s+means?|proven\s+when|proof\s+means?)\s*:\s*", "Release 0.0.1 succeeds when ", text, flags=re.I)
    text = re.sub(r"^(?:done\s+means?|proven\s+when|proof\s+means?)\s+", "Release 0.0.1 succeeds when ", text, flags=re.I)
    return (normalize_confirmed_proof_boundary_sentence(text) or text).strip()


def _normalize_state_object(value: str) -> str:
    text = _strip_prompt_prefixes(value)
    text = re.sub(
        r"^(?:the\s+)?(?:product|system|app|application|workspace|service|platform|tool)\s+"
        r"(?:captures?|keeps?|records?|stores?|tracks?|holds?|manages?|maintains?|coordinates?|orchestrates?)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(
        r"^(?:the\s+)?[a-z][a-z0-9_'’/-]*(?:\s+[a-z][a-z0-9_'’/-]*){0,5}\s+"
        r"(?:captures?|keeps?|records?|stores?|tracks?|holds?|manages?|maintains?|coordinates?|orchestrates?)\s+"
        r"(?=(?:a|an|one)\s+)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    ).strip()
    text = re.sub(
        r"^(?:the\s+)?(?:unit|source)\s+of\s+truth\s+is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:the\s+)?(?:central|core|main|primary)\s+(?:thing|object|record|item|state)\s+"
        r"(?:the\s+product\s+|the\s+system\s+)?"
        r"(?:tracks|records|stores|captures|keeps|manages|maintains|coordinates|orchestrates)\s+is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:the\s+)?(?:central|core|main)\s+(?:product\s+)?(?:object|state|record)\s+is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:the\s+)?center\s+of\s+gravity\s+is\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^(?:the\s+)?state\s+object\s+is\s+", "", text, flags=re.IGNORECASE)
    text = _repair_terminal_hang_off_phrase(text)
    return text.strip()


def _repair_terminal_hang_off_phrase(value: str) -> str:
    text = _clean(value).strip()
    if not text:
        return ""
    return re.sub(
        r"\b(?P<subject>[A-Z][A-Za-z0-9 &'/-]{1,90}?)\s+(?P<copula>is|are)\s+"
        r"(?P<description>[^.!?]{1,120}?)\s+(?P<object>(?:the|a|an|those|these)\s+[^.!?]{1,80}?)\s+"
        r"hangs?\s+off\s+of(?P<end>[.!?]?)$",
        lambda match: (
            f"{match.group('subject')} {match.group('copula')} "
            f"{match.group('description').rstrip(' ,')} linked to {match.group('object').rstrip(' ,')}"
            f"{match.group('end') or '.'}"
        ),
        text,
        flags=re.IGNORECASE,
    )


def _normalize_visible_result_language(value: str) -> str:
    text = _clean(value)
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)[^.?!]*\bvisible[- ]result\s+event\b[^.?!]*[.?!]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = _normalize_visible_result_terms(text)
    text = repair_modal_base_form_drift(text)
    text = repair_infinitive_base_form_drift(text)
    return _clean(text)


def normalize_first_path(value: str, *, product_title: str = "") -> str:
    text = _strip_inline_meta_loop_clauses(
        _normalize_visible_result_language(_strip_prompt_prefixes(value))
    )
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if not sentences:
        return text
    kept = [
        _strip_unpunctuated_meta_control_phrases(sentence)
        for sentence in sentences
        if not _is_terminal_meta_loop_summary(sentence)
    ]
    normalized = _normalize_named_product_subjects(" ".join(kept or sentences).strip(), product_title=product_title)
    return _separate_distinct_actor_steps(normalized)


def _separate_distinct_actor_steps(value: str) -> str:
    """Make an actor-to-actor handoff readable without flattening one actor's action chain."""

    text = _clean(value).strip()
    if not text or re.search(r"(?<=[.!?])\s+", text):
        return text
    steps = first_path_model(text).steps
    if len(steps) < 2:
        return text
    subjects = [_first_path_step_subject(step) for step in steps]
    if (
        not all(subjects)
        or not all(_looks_like_explicit_handoff_subject(subject) for subject in subjects)
        or len({subject.casefold() for subject in subjects}) < 2
    ):
        return text
    return ". ".join(step.strip(" .") for step in steps) + "."


def _first_path_step_subject(step: str) -> str:
    match = re.match(
        rf"^(?P<subject>.+?)\s+(?:{action_verb_pattern()})\b",
        _clean(step).strip(" ."),
        flags=re.IGNORECASE,
    )
    return _clean(match.group("subject")) if match else ""


def _looks_like_explicit_handoff_subject(value: str) -> bool:
    words = re.findall(r"[A-Za-z]+", _clean(value).casefold())
    if not words:
        return False
    if words[0] in {"a", "an", "the"}:
        return len(words) > 1
    last = words[-1]
    return len(last) > 3 and last.endswith("s") and not last.endswith(("ics", "ss", "us"))


def _normalize_named_product_subjects(value: str, *, product_title: str) -> str:
    """Keep a known product identity out of a first-path action subject.

    The title is an accepted fact, but the path describes the person and product
    behavior, not a brand acting as a human participant. This is intentionally
    limited to the already accepted project title and a recognized action verb.
    """

    text = _clean(value)
    title = _clean(product_title).strip(" .")
    if not text or not title:
        return text
    labels = [title]
    if " — " in title:
        labels.append(title.split(" — ", 1)[0].strip())
    verb_pattern = action_verb_pattern()
    for label in sorted({label for label in labels if label}, key=len, reverse=True):
        text = re.sub(
            rf"\b{re.escape(label)}\s+(?=(?:{verb_pattern})\b)",
            "the product ",
            text,
            flags=re.IGNORECASE,
        )
    return text


def _strip_inline_meta_loop_clauses(value: str) -> str:
    def replacement(match: re.Match[str]) -> str:
        clause = _clean(match.group("clause"))
        return " " if is_first_path_meta_control_language(clause) else match.group(0)

    return re.sub(r",(?P<clause>[^,.;!?]+),", replacement, _clean(value))


def _strip_unpunctuated_meta_control_phrases(value: str) -> str:
    return _UNPUNCTUATED_META_CONTROL_PHRASE_RE.sub(" ", _clean(value))


def _is_terminal_meta_loop_summary(value: str) -> bool:
    text = _clean(value).strip()
    return bool(
        re.search(r"^(?:this|that)\s+(?:loop|path|journey|flow)\b", text, flags=re.IGNORECASE)
        and is_first_path_meta_control_language(text)
    )


def is_first_path_meta_control_language(value: str) -> bool:
    """Identify source framing about proving the whole product, not product behavior."""

    text = _clean(value)
    has_smallest_version = bool(re.search(r"\bsmallest\s+version\b", text, re.IGNORECASE))
    has_whole_product = bool(re.search(r"\bwhole\s+product\b", text, re.IGNORECASE))
    has_terminal_meta_subject = bool(
        re.search(r"^(?:this|that)\s+(?:loop|path|journey|flow)\b", text, re.IGNORECASE)
    )
    has_path_claim = bool(
        re.search(r"\b(?:complete\s+path|end\s+to\s+end|proven|works?|working)\b", text, re.IGNORECASE)
    )
    return bool(
        (has_smallest_version and (has_whole_product or has_path_claim))
        or (has_whole_product and has_path_claim)
        or (has_terminal_meta_subject and has_path_claim)
    )


def split_unpunctuated_first_path_meta_control(value: str) -> tuple[str, str, str] | None:
    """Return exact source fragments around one removable inline meta-control phrase."""

    match = _UNPUNCTUATED_META_CONTROL_PHRASE_RE.search(_clean(value))
    if match is None:
        return None
    text = _clean(value)
    return text[: match.start()].strip(" .,;:-"), match.group(0), text[match.end() :].strip(" .,;:-")


def is_terminal_first_path_meta_loop_summary(value: str) -> bool:
    return _is_terminal_meta_loop_summary(value)


def _completion_seed_is_sufficient(intent: Mapping[str, Any]) -> bool:
    core = " ".join(
        _clean(intent.get(key))
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "problem", "product_view")
        if _clean(intent.get(key))
    )
    if _word_count(core) < 24:
        return False
    return len(_semantic_terms(core)) >= 6


def _lower_initial_fragment(value: str) -> str:
    text = _clean(value)
    if not text:
        return ""
    first = text.split(maxsplit=1)[0]
    if first.isupper() and len(first) > 1:
        return text
    return f"{text[:1].lower()}{text[1:]}"


def _complete_core_fields(intent: dict[str, Any], *, title: str) -> None:
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    actors = _first_release_actor_labels(intent)
    systems = _system_labels(intent)

    if _story_needs_completion(story):
        actor_text = _join(actors[:2]) or f"{_focus_label(title)} users"
        story_head = _short(
            story,
            fallback=f"{title} helps {actor_text} complete the accepted first path",
            limit=220,
        )
        state_fragment = _story_state_fragment(state, title=title)
        path_fragment = _story_path_relation_fragment(first_path)
        intent["product_story"] = _sentence(
            f"{story_head}. It keeps {state_fragment} tied to "
            f"{path_fragment} so the outcome, blockers, and evidence can be explained."
        )
    if (
        _word_count(state) < CORE_FIELD_MIN_WORDS["state_object"]
        and not canonical_state_object_is_meaningful(state)
    ):
        state_label = _state_label(state, title=title)
        intent["state_object"] = _sentence(
            f"{state_label} records the current status, actor, source input, decision, blocked reason, evidence links, timestamp, and version history for the accepted first path."
        )
    if _word_count(first_path) < CORE_FIELD_MIN_WORDS["first_path"] and not _first_path_is_complete_enough(first_path):
        primary = actors[0] if actors else f"{_focus_label(title)} operator"
        source_text = ". ".join(value for value in (story, state, proof) if value)
        action = first_path_action_phrase(source_text, fallback="provide the required information", max_fragments=2)
        outcome = _visible_outcome_phrase(source_text, proof=proof)
        action = _clean(action).rstrip(" .") or "provide the required information"
        outcome = _clean(outcome).rstrip(" .") or "a clear result"
        intent["first_path"] = _sentence(
            f"{primary} {_modal_action_clause(action)}. The product uses the accepted information to return {outcome}, explains any missing input, and leaves the result reviewable."
        )
    if _word_count(proof) < CORE_FIELD_MIN_WORDS["proof_boundary"]:
        if _concise_proof_boundary_is_meaningful(proof):
            intent["proof_boundary"] = _sentence(_completed_concise_proof_boundary(proof, title=title))
        else:
            actor = _join(actors[:2]) or f"the first {_focus_label(title)} user"
            action = first_path_action_phrase(first_path or story, fallback="complete the first useful product action", max_fragments=1)
            outcome = _visible_outcome_phrase(first_path or story, proof=proof).rstrip(" .") or "a clear, useful result"
            outcome_action = _outcome_action_phrase(outcome)
            intent["proof_boundary"] = _sentence(
                f"The first release works when {actor} can {action}, the product confirms the user can {outcome_action}, and missing or invalid information leaves a clear correction path instead of a misleading result. "
                f"It must not claim live integrations, broad automation, regulated correctness, or production-scale operation beyond the confirmed {title.lower()} boundary."
            )


def _concise_proof_boundary_is_meaningful(value: str) -> bool:
    text = _clean(value).strip(" .")
    if not text:
        return False
    if _word_count(text) < 3 or _word_count(text) > 12:
        return False
    return len(_semantic_terms(text)) >= 3


def _story_state_fragment(state: str, *, title: str) -> str:
    label = _clean(_state_label(state, title=title)).strip(" .")
    if label:
        return _definite_relation_label(label)
    return _lower_initial_fragment(_short(state, fallback="the first release state"))


def _story_path_relation_fragment(first_path: str) -> str:
    capability = _clean(first_path_capability_phrase(first_path, fallback="", limit=220)).strip(" .")
    if capability and looks_like_action_clause(capability):
        return f"the user's ability to {base_action_clause(capability)}"
    return _lower_initial_fragment(_short(first_path, fallback="the first user journey"))


def _definite_relation_label(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the first release state"
    lowered = _lower_initial_fragment(text)
    first = lowered.split(maxsplit=1)[0].strip(".,:;").casefold()
    if first in {"a", "an", "the", "this", "that", "one"}:
        return lowered
    return f"the {lowered}"


def _completed_concise_proof_boundary(value: str, *, title: str) -> str:
    proof = _clean(value).strip(" .")
    proof_clause = _definite_proof_clause(proof[:1].lower() + proof[1:] if proof else "")
    return (
        f"Reviewable proof covers {proof_clause} for the accepted {title.lower()} path, "
        "and missing or invalid information is resolved before the result is trusted."
    )


def _definite_proof_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "the accepted proof boundary"
    first = text.split(maxsplit=1)[0].strip(".,;:").casefold()
    if first in {"a", "an", "the", "this", "that", "their", "one"}:
        return text
    return f"the {text}"


def _first_path_is_complete_enough(value: str) -> bool:
    text = _clean(value)
    if _word_count(text) < 6:
        return False
    if _actor_modal_path_is_complete(text):
        return True
    action = first_path_action_phrase(text, fallback="", max_fragments=2)
    outcome = first_path_outcome_phrase(text, fallback="", limit=160)
    if _clean(action) and _clean(outcome) and first_path_has_distinct_outcome(text, outcome) and len(_semantic_terms(text)) >= 4:
        return True
    material_action = material_first_path_action(text)
    model = first_path_model(text)
    if len(model.steps) == 1 and has_concise_coordinated_first_path(text):
        return True
    visible_outcome = _clean(model.visible_outcome)
    if (
        len(model.steps) >= 2
        and visible_outcome
        and _word_count(visible_outcome) >= 4
        and len(_semantic_terms(visible_outcome)) >= 3
        and len(_semantic_terms(text)) >= 7
    ):
        return True
    return has_rich_material_first_path_action(
        material_action,
        semantic_term_count=len(_semantic_terms(material_action)),
    )


def _actor_modal_path_is_complete(value: str) -> bool:
    words = [word.strip(".,:;!?()[]{}").casefold() for word in _clean(value).split()]
    if "can" not in words:
        return False
    can_index = words.index("can")
    actor_words = words[:can_index]
    if not actor_words or len(actor_words) > 5:
        return False
    if not any(word_has_actor_role_signal(word) or word in _ACTOR_MODAL_ROLE_WORDS for word in actor_words):
        return False
    return len(_semantic_terms(value)) >= 4


def _modal_action_clause(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return "can provide the required information"
    first = text.split(maxsplit=1)[0].strip(".,;:").casefold()
    if first in {"can", "could", "must", "should", "will"}:
        return text
    return f"can {text}"


def _story_needs_completion(value: str) -> bool:
    text = _clean(value)
    if not text:
        return True
    if _word_count(text) >= CORE_FIELD_MIN_WORDS["product_story"]:
        return False
    if _word_count(text) >= 12 and re.search(r"\b(?:needs?|wants?|helps?|gives?|lets?|makes?|turns?)\b", text, flags=re.I):
        return bool(
            re.search(
                r"\b(?:accepted\s+first\s+path|first\s+path\s+entry|source\s+evidence|visible\s+blockers|"
                r"systems?\s+that\s+own|proof\s+boundary|state\s+object)\b",
                text,
                flags=re.I,
            )
        )
    return True


__all__ = ["complete_confirmed_intent", "normalize_first_path"]
