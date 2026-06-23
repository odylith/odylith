from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_actor_labels import localize_leading_actor_reference
from odylith.runtime.domain_intelligence.greenfield_actor_labels import project_specific_actor_row
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import actor_row_description as _actor_row_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import completed_actor_rows as _completed_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import first_release_actor_rows as _first_release_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase as _outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import completed_system_rows as _completed_system_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import state_label as _state_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_system_completion import system_labels as _system_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import boundary_clause_item as _boundary_clause_item
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items as _join
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import derived_title as _derived_title
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import title as _title
from odylith.runtime.domain_intelligence.greenfield_confirmed_title_completion import title_needs_repair as _title_needs_repair
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import material_first_path_action
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import (
    repair_confirmed_intent_semantic_projections,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language as _normalize_visible_result_terms
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


CORE_FIELD_MIN_WORDS = {"product_story": 28, "state_object": 12, "first_path": 18, "proof_boundary": 18}

def complete_confirmed_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(intent))
    title_normalization = normalize_project_title(_title(result), fallback="Greenfield Project")
    if title_normalization.changed:
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
    _complete_core_fields(result, title=title)
    _normalize_confirmed_core_language(result)
    repair_confirmed_intent_semantic_projections(result)
    _complete_product_posture(result, title=title)
    _normalize_confirmed_core_language(result)
    _normalize_confirmed_actor_context(result, title=title)
    return result


def _normalize_confirmed_core_language(intent: dict[str, Any]) -> None:
    for key in ("product_story", "first_path", "problem", "product_view"):
        text = _clean(intent.get(key))
        if text:
            normalized = _normalize_first_path(text) if key == "first_path" else _normalize_visible_result_language(_strip_prompt_prefixes(text))
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
    if external_systems := confirmed_text_values(intent.get("external_systems")):
        intent["external_systems"] = [
            normalized
            for row in external_systems
            if (normalized := _boundary_clause_item(_normalize_external_system_language(row), limit=180))
        ]


def _normalize_confirmed_actor_context(intent: dict[str, Any], *, title: str) -> None:
    actor_rows = confirmed_text_values(intent.get("human_actors"))
    if actor_rows:
        intent["human_actors"] = [
            normalized
            for row in actor_rows
            if (normalized := project_specific_actor_row(row, project_focus=title))
        ]
    first_path = _clean(intent.get("first_path"))
    if first_path:
        intent["first_path"] = _sentence(
            localize_leading_actor_reference(
                first_path,
                actor_rows=confirmed_text_values(intent.get("human_actors")),
                project_focus=title,
                fallback=f"{_focus_label(title)} user",
            )
        )


def _normalize_external_system_language(value: str) -> str:
    text = _normalize_visible_result_language(value)
    text = re.sub(
        r"^(?:optional|optionally|deferred|future|later|if\s+needed|if\s+available)(?:\s*:\s*|\s+)",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return _clean(text)


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
    summarized = proof_claim_summary(text, limit=420)
    return (summarized or text).strip()


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
        r"^(?:the\s+)?(?:central|core|main)\s+(?:object|state|record)\s+is\s+",
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
    return _clean(_normalize_visible_result_terms(text))


def _normalize_first_path(value: str) -> str:
    text = _normalize_visible_result_language(_strip_prompt_prefixes(value))
    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", text)
        if sentence.strip()
    ]
    if not sentences:
        return text
    kept = [sentence for sentence in sentences if not _is_terminal_meta_loop_summary(sentence)]
    return " ".join(kept or sentences).strip()


def _is_terminal_meta_loop_summary(value: str) -> bool:
    text = _clean(value).strip()
    return bool(
        re.search(r"^(?:this|that)\s+(?:loop|path|journey|flow)\b", text, flags=re.IGNORECASE)
        and re.search(r"\b(?:smallest\s+version|whole\s+product|end\s+to\s+end|working)\b", text, flags=re.IGNORECASE)
    )


def _completion_seed_is_sufficient(intent: Mapping[str, Any]) -> bool:
    core = " ".join(
        _clean(intent.get(key))
        for key in ("product_story", "state_object", "first_path", "proof_boundary", "problem", "product_view")
        if _clean(intent.get(key))
    )
    if _word_count(core) < 24:
        return False
    return len(_semantic_terms(core)) >= 6


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
        intent["product_story"] = _sentence(
            f"{story_head}. It keeps {_short(state, fallback='the first release state')} tied to "
            f"{_short(first_path, fallback='the first user journey')} so the outcome, blockers, and evidence can be explained."
        )
    if _word_count(state) < CORE_FIELD_MIN_WORDS["state_object"]:
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
            f"{primary} {action}. The product uses the accepted information to return {outcome}, explains any missing input, and leaves the result reviewable."
        )
    if _word_count(proof) < CORE_FIELD_MIN_WORDS["proof_boundary"]:
        action = first_path_action_phrase(first_path or story, fallback="complete the first useful product action", max_fragments=1)
        outcome = _visible_outcome_phrase(first_path or story, proof=proof).rstrip(" .") or "a clear, useful result"
        outcome_action = _outcome_action_phrase(outcome)
        intent["proof_boundary"] = _sentence(
            f"The first release works when a representative user can {action}, the product confirms the user can {outcome_action}, and missing or invalid information leaves a clear correction path instead of a misleading result. "
            f"It must not claim live integrations, broad automation, regulated correctness, or production-scale operation beyond the confirmed {title.lower()} boundary."
        )


def _first_path_is_complete_enough(value: str) -> bool:
    text = _clean(value)
    if _word_count(text) < 6:
        return False
    action = first_path_action_phrase(text, fallback="", max_fragments=2)
    outcome = first_path_outcome_phrase(text, fallback="", limit=160)
    return bool(_clean(action) and _clean(outcome) and len(_semantic_terms(text)) >= 4)


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


def _first_release_actor_rows_for_intent(intent: Mapping[str, Any]) -> list[str]:
    rows = confirmed_text_values(intent.get("human_actors"))
    return _first_release_actor_rows(rows)


def _first_release_actor_labels(intent: Mapping[str, Any]) -> list[str]:
    return _actor_labels_from_rows(_first_release_actor_rows_for_intent(intent))


def _actor_labels_from_rows(rows: Sequence[str]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        label = _clean(str(row).split("—", 1)[0].split(":", 1)[0]).strip(" .")
        if label:
            labels.append(label)
    return labels


def _complete_product_posture(intent: dict[str, Any], *, title: str) -> None:
    actor_rows = _first_release_actor_rows_for_intent(intent)
    actors = _actor_labels_from_rows(actor_rows)
    systems = _system_labels(intent)
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    focus = _focus_label(title)
    customer_text = _customer_summary(actors, title=title)
    outcome_text = _visible_outcome_phrase(first_path, proof=proof)
    state_phrase = _state_focus_phrase(state, title=title)
    path_capability = _path_capability(first_path, fallback=f"the first {title.lower()} path")
    proof_capability = first_path_capability_phrase(
        first_path,
        fallback=path_capability,
        limit=340,
        gerund=True,
        max_fragments=8,
    )
    needs_verb = _needs_verb(customer_text)
    decision_phrase = _decision_problem_phrase(outcome_text)

    if not _clean(intent.get("problem")):
        intent["problem"] = _sentence(
            _story_problem_sentence(story)
            or (
                f"{customer_text} {needs_verb} a dependable way to understand {state_phrase} and {decision_phrase}; "
                "without it, the work stays scattered, hard to interpret, and easy to misuse."
            )
        )
    elif _problem_needs_repair(intent.get("problem")):
        intent["problem"] = _sentence(
            f"{customer_text} {needs_verb} a dependable way to understand {state_phrase} and {decision_phrase}; "
            "without it, the work stays scattered, hard to interpret, and easy to misuse."
        )
    if not _clean(intent.get("customer")) or _customer_needs_repair(intent.get("customer")):
        intent["customer"] = _sentence(_customer_sentence(actor_rows, title=title, first_path=first_path))
    if not _clean(intent.get("opportunity")):
        intent["opportunity"] = _sentence(
            f"Make the first version valuable by proving the smallest complete outcome: {path_capability}, ending in {outcome_text}."
        )
    if not _clean(intent.get("product_view")) or _product_view_needs_repair(intent.get("product_view")):
        outcome_action = _outcome_action_phrase(outcome_text)
        intent["product_view"] = _sentence(
            f"{title} is useful when {customer_text} can {path_capability} and confidently {outcome_action} to decide the next action."
        )
    metrics = confirmed_text_values(intent.get("success_metrics"))
    if len(metrics) < 3 or any(_metric_needs_repair(metric) for metric in metrics):
        metric_outcome_action = _outcome_action_phrase(outcome_text)
        intent["success_metrics"] = [
            f"The first release proves the first path: {proof_capability}.",
            f"Users can {metric_outcome_action} without manual interpretation outside the product.",
            f"The product handles missing or incorrect input by explaining what must be fixed before {outcome_text} is treated as real.",
            _proof_boundary_metric(proof, outcome=outcome_text),
        ]
    if not confirmed_text_values(intent.get("assumptions")):
        intent["assumptions"] = [
            f"The first release proves one concrete {title.lower()} path before broader scope or automation.",
            "External integrations can start as deterministic fixtures unless the accepted path cannot be proven without a live source.",
            f"Security, privacy, accessibility, safety, audit, and retention obligations scale with the {focus.lower()} data and decisions involved.",
        ]
    if not confirmed_text_values(intent.get("ambiguities")):
        intent["ambiguities"] = [
            f"Which {focus.lower()} actor has final release authority when evidence is incomplete or disputed?",
            f"Which source, device, document, dataset, or external service is authoritative for the first {title.lower()} proof?",
            "Which privacy, safety, compliance, or access rule would change the first path if it is stricter than assumed?",
        ]
    current_non_goals = confirmed_text_values(intent.get("non_goals"))
    if not current_non_goals or _sequence_has_generic_non_goals(current_non_goals):
        extracted_non_goals = _non_goal_rows(intent, title=title)
        intent["non_goals"] = extracted_non_goals or [
            "Do not expand into adjacent workflows, personalized automation, or broader operational scale until the first outcome works for a representative user.",
            f"Do not claim adjacent automation, live dependency behavior, or broader operational scale until those outcomes are described and proven separately.",
        ]
    if not story:
        intent["product_story"] = _sentence(
            f"{title} helps {_join(actors[:2]) or f'{focus} users'} complete one accountable path with state, evidence, and decision context visible."
        )


def _story_problem_sentence(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or not re.search(r"\bneeds?\b", text, flags=re.IGNORECASE):
        return ""
    first = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    return first if _word_count(first) >= 10 else ""


def _decision_problem_phrase(outcome_text: str) -> str:
    outcome = _clean(outcome_text).rstrip(" .") or "the product result"
    if outcome.casefold().startswith("the usage-linked metric change view"):
        return "act on the metric-change view"
    return f"decide what to do using {outcome}"


def _product_view_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return False
    return bool(
        re.search(r"\binspect\s+(?:the\s+)?(?:core\s+)?state\s+is\b", text, re.IGNORECASE)
        or re.search(r"\baccepted\s+first\s+path\b", text, re.IGNORECASE)
        or re.search(r"\bsource\s+evidence|visible\s+blockers|systems?\s+that\s+own\b", text, re.IGNORECASE)
        or re.search(r"\bto\s+complete\s+(?:A|The)\b", text)
        or re.search(r"\b(?:use|reach)\s+(?:a|an|the|[A-Z][A-Za-z0-9/-]*)\s+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?)\b", text)
        or re.search(r"\b(?:active\s+and\s+decide|from\s+(?:A|An|The)\s+[A-Za-z0-9/-]+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?))\b", text)
        or re.search(r"\.\s*,", text)
    )


def _problem_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    return bool(
        re.search(r"\bis\s+not\s+trustworthy\s+when\b", text, re.I)
        or re.search(r"\bunderstand\s+(?:A|An|The)\b", text)
        or re.search(r"\bsource\s+evidence|visible\s+blockers|systems?\s+that\s+own\s+the\s+handoff\b", text, re.I)
        or re.search(r"\bfirst\s+path\s+entry\b", text, re.I)
        or re.search(r"\bactive\s+and\s+decide\b", text, re.I)
        or re.search(r"\bfrom\s+(?:A|An|The)\s+[A-Za-z0-9/-]+[^.]{0,100}\b(?:sees?|views?|receives?|reads?|gets?)\b", text)
        or re.search(r"\b(?:use|reach)\s+(?:a|an|the|[A-Z][A-Za-z0-9/-]*)\s+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?)\b", text)
    )


def _customer_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    return bool(re.search(r"\bneed\s+the\s+accepted\s+outcome\b|\baccepted\s+path\b", text, re.I))


def _sequence_has_generic_non_goals(values: Sequence[str]) -> bool:
    text = " ".join(_clean(value) for value in values)
    return bool(
        re.search(r"\bstays\s+limited\s+to\s+the\s+accepted\b", text, re.I)
        or re.search(r"\bbroader\s+users,\s+integrations,\s+datasets,\s+edge\s+cases\b", text, re.I)
        or re.search(r"\bseparately\s+accepted\s+proof\s+boundary\b", text, re.I)
    )


def _metric_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    if re.search(r"[,:]\.$", text):
        return True
    if re.search(r"\baccepted\s+path\s+lets\s+users\b|\bproof\s+boundary\b|\bevidence\s+context\b", text, re.I):
        return True
    if re.search(r"\b(?:use|reach)\s+(?:a|an|the|[A-Z][A-Za-z0-9/-]*)\s+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?)\b", text):
        return True
    if text.rstrip().endswith(","):
        return True
    tail = text.rstrip(".;:, ").split()[-1].casefold() if text.split() else ""
    return tail in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an", "required"}


def _customer_summary(actors: Sequence[str], *, title: str) -> str:
    labels = [_clean(value).split("—", 1)[0].split(":", 1)[0].strip(" .") for value in actors]
    labels = [label for label in labels if label]
    if not labels:
        return f"{_focus_label(title)} users"
    if len(labels) == 1:
        return labels[0]
    if _secondary_role_is_supporting(labels[1]):
        return labels[0]
    return _join(labels[:2])


def _secondary_role_is_supporting(label: str) -> bool:
    text = _clean(label).casefold()
    return bool(
        re.search(
            r"\b(?:admin|administrator|advisor|analyst|approver|auditor|coach|coordinator|evaluator|expert|inspector|"
            r"lead|manager|officer|operator|reviewer|specialist|supervisor|support)\b",
            text,
        )
    )


def _customer_sentence(actors: Sequence[str], *, title: str, first_path: str) -> str:
    rows = []
    for value in actors[:4]:
        label = _clean(value).split(":", 1)[0].split("—", 1)[0].strip(" .")
        description = _actor_row_description(value)
        if label and description:
            rows.append(f"{label} {description}")
        elif label:
            rows.append(f"{label} participates in the product outcome")
    if rows:
        return "; ".join(rows)
    return f"{_focus_label(title)} users need to {first_path_capability_phrase(first_path)} and understand the outcome."


def _needs_verb(label: str) -> str:
    text = _clean(label).casefold()
    if not text:
        return "need"
    if " and " in text or "," in text or text.endswith(("s", "team", "teams")):
        return "need"
    return "needs"


def _state_focus_phrase(state: str, *, title: str) -> str:
    text = _clean(state)
    if not text:
        return f"{_focus_label(title).lower()} state"
    state_label = _state_label(text, title=title)
    if 2 <= _word_count(state_label) <= 8:
        label = state_label.casefold()
        if not label.startswith(("a ", "an ", "the ")):
            label = f"the {label}"
        return label
    text = re.sub(r"^(?:the\s+)?(?:core|main|primary)\s+state\s+(?:is|object\s+is)\s+", "", text, flags=re.I)
    text = re.sub(r"^a\s+", "the ", text, flags=re.I)
    first_clause = re.split(r";|(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    first_clause = re.split(r":\s*", first_clause, maxsplit=1)[-1].strip(" .")
    return _short(first_clause, fallback=f"{_focus_label(title).lower()} state", limit=160).rstrip(".")


def _visible_outcome_phrase(first_path: str, *, proof: str = "") -> str:
    text = first_path_outcome_phrase(first_path, proof_boundary=proof, fallback="a visible, useful result", limit=190).rstrip(".")
    if re.match(r"^why\b", text, flags=re.I):
        text = f"the explanation for {text}"
    if not re.search(
        r"\b(?:answer|appointment|booking|card|confirmation|consequence|decision|entry|explanation|history|"
        r"metrics?|outcome|plan|readout|recommendation|reflection|report|result|schedule|session|status|summary|"
        r"timeline|trend|view|workout)\b",
        text,
        re.I,
    ):
        text = _nominal_visible_outcome_phrase(text)
    return text


def _nominal_visible_outcome_phrase(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an|the|both|each|one)\b", text, flags=re.I):
        return text
    if re.match(r"^(?:accepted|approved|completed|confirmed|persisted|recorded|saved)\b", text, flags=re.I):
        return f"the {text[:1].lower() + text[1:]}"
    return text


def _non_goal_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    candidates: list[str] = []
    for value in text_values(
        [
            intent.get("proof_boundary"),
            intent.get("assumptions"),
            intent.get("ambiguities"),
        ]
    ):
        for sentence in re.split(r"(?<=[.!?])\s+|;\s+", _clean(value)):
            row = _non_goal_row_from_sentence(sentence)
            if row:
                candidates.append(row)
    rows = [row for row in unique_text(candidates) if _word_count(row) >= 5]
    return rows[:4]


def _non_goal_row_from_sentence(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    lowered = text.casefold()
    for marker in ("without claiming", "without claim"):
        index = lowered.find(marker)
        if index >= 0:
            tail = text[index + len(marker) :].strip(" ,.;:")
            return _sentence(f"Do not claim {tail}") if tail else ""
    for marker in ("not claim", "not cover"):
        index = lowered.find(marker)
        if index >= 0:
            tail = text[index + len(marker) :].strip(" ,.;:")
            verb = "claim" if "claim" in marker else "cover"
            return _sentence(f"Do not {verb} {tail}") if tail else ""
    if any(marker in lowered for marker in ("out of scope", "deferred", "defer ", "later", "future", "beyond the first")):
        return _sentence(text)
    return ""


def _proof_boundary_metric(proof_boundary: str, *, outcome: str = "") -> str:
    """Summarize proof scope without clipping confirmed proof prose mid-claim."""

    proof = _clean(proof_boundary)
    if not proof:
        target = outcome or "the promised user outcome"
        return f"Release readiness requires evidence that {target} is correct, visible, and limited to the first release."
    non_goal_hint = ""
    if re.search(r"\b(?:must not|without claiming|does not claim|no claim|non-goals?)\b", proof, re.IGNORECASE):
        non_goal_hint = " and keeps deferred or forbidden claims outside release readiness"
    target = outcome or "the promised user outcome"
    return f"Release readiness requires evidence that {target} is correct, visible, and reproducible{non_goal_hint}."


def _path_headline(value: str, *, fallback: str, limit: int = 140) -> str:
    material = material_first_path_action(value)
    text = _clean(material) or _clean(value)
    if not text:
        return fallback
    text = re.sub(
        r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^the first complete path to prove should be\s*:?\s*", "", text, flags=re.IGNORECASE)
    text = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .:")
    action_pattern = (
        r"the\s+product\s+(?:fetches?|calculates?|ranks?|highlights?|lets?|stores?|shows?|records?|routes?)|"
        r"(?:receives?|logs?|reviews?|records?|stores?|fetches?|calculates?|ranks?|highlights?|lets?|chooses?|selects?)\b"
    )
    text = re.split(rf",\s+(?=(?:and\s+)?(?:{action_pattern}))", text, maxsplit=1, flags=re.IGNORECASE)[0].strip(" .:")
    return _short(text, fallback=fallback, limit=limit)


def _path_capability(value: str, *, fallback: str, limit: int = 180) -> str:
    action = first_path_action_phrase(value, fallback=fallback, limit=limit, max_fragments=1)
    return _short(_capability_action_clause(action), fallback=fallback, limit=limit)


def _capability_action_clause(value: str) -> str:
    text = clean_text(value).strip(" .")
    if not text:
        return "complete the accepted path"
    if looks_like_action_clause(text):
        return base_action_clause(text)
    actor_action = _actor_action_clause(text)
    if actor_action:
        return actor_action
    converted = base_action_clause(text)
    if converted and converted != text.casefold():
        return converted
    return text[:1].lower() + text[1:]


def _actor_action_clause(value: str) -> str:
    text = re.sub(r"^(?:a|an|the)\s+", "", clean_text(value).strip(" ."), flags=re.IGNORECASE)
    words = text.split()
    for index in range(1, min(len(words), 6)):
        verb = words[index].strip(".,;:")
        base = _base_action_verb(verb)
        if base != verb.casefold():
            tail = " ".join(words[index + 1 :]).strip(" .")
            return base_action_clause(" ".join(part for part in (base, tail) if part))
    return ""


def _base_action_verb(value: str) -> str:
    token = str(value or "").casefold()
    overrides = {
        "chooses": "choose",
        "does": "do",
        "goes": "go",
        "has": "have",
        "is": "be",
        "receives": "receive",
        "sees": "see",
        "uses": "use",
    }
    if token in overrides:
        return overrides[token]
    if len(token) > 4 and token.endswith("ies"):
        return f"{token[:-3]}y"
    if len(token) > 4 and token.endswith(("ches", "shes", "sses", "xes", "zes")):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token

__all__ = ["complete_confirmed_intent"]
