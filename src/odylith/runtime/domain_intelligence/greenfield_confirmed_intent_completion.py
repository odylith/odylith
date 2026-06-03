"""Deterministic completion for accepted greenfield Product Intent."""

from __future__ import annotations

import copy
import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import actor_labels as _actor_labels
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import actor_row_description as _actor_row_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import completed_actor_rows as _completed_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import GENERIC_TITLE_WORDS as _GENERIC_TITLE_WORDS
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label as _focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items as _join
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_overlap as _semantic_overlap
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import semantic_terms as _semantic_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text as _sentence
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import short_confirmed_text as _short
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text as _title_case
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count as _word_count
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import material_first_path_action
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


CORE_FIELD_MIN_WORDS = {
    "product_story": 28,
    "state_object": 12,
    "first_path": 18,
    "proof_boundary": 18,
}

_SYSTEM_SUFFIXES = (
    "product record",
    "experience guide",
    "evidence log",
    "release guardrail",
)


def complete_confirmed_intent(intent: Mapping[str, Any]) -> dict[str, Any]:
    """Fill reviewable fields that can be inferred from accepted intent text."""

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
    result["internal_systems"] = _completed_system_rows(result, title=title)
    _complete_core_fields(result, title=title)
    _normalize_confirmed_core_language(result)
    _complete_product_posture(result, title=title)
    _normalize_confirmed_core_language(result)
    return result


def _normalize_confirmed_core_language(intent: dict[str, Any]) -> None:
    """Keep accepted operator wording but remove known non-spec prefixes."""

    for key in ("product_story", "state_object", "first_path", "problem", "product_view"):
        text = _clean(intent.get(key))
        if text:
            intent[key] = _sentence(_normalize_visible_result_language(_strip_prompt_prefixes(text)))
    proof = _clean(intent.get("proof_boundary"))
    if proof:
        intent["proof_boundary"] = _sentence(_normalize_visible_result_language(_normalize_proof_boundary(proof)))
    metrics = _strings(intent.get("success_metrics"))
    if metrics:
        intent["success_metrics"] = [_sentence(_normalize_visible_result_language(_normalize_proof_boundary(row))) for row in metrics]


def _strip_prompt_prefixes(value: str) -> str:
    text = _clean(value)
    text = re.sub(r"^(?:problem\s+to\s+solve|product\s+view|first\s+path|state\s+object)\s*:\s*", "", text, flags=re.I)
    return text.strip()


def _normalize_proof_boundary(value: str) -> str:
    text = _strip_prompt_prefixes(value)
    text = re.sub(r"^(?:done\s+means?|proven\s+when|proof\s+means?)\s*:\s*", "Release 0.0.1 succeeds when ", text, flags=re.I)
    text = re.sub(r"^(?:done\s+means?|proven\s+when|proof\s+means?)\s+", "Release 0.0.1 succeeds when ", text, flags=re.I)
    return text.strip()


def _normalize_visible_result_language(value: str) -> str:
    text = _clean(value)
    text = re.sub(
        r"(?:^|(?<=[.!?])\s+)[^.?!]*\bvisible[- ]result\s+event\b[^.?!]*[.?!]?",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\bvisible[- ]result\s+event\b", "visible result", text, flags=re.IGNORECASE)
    text = re.sub(r"\breadout\s+plus\b", "readout and", text, flags=re.IGNORECASE)
    return _clean(text)


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
    actors = _actor_labels(intent)
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
    if _word_count(first_path) < CORE_FIELD_MIN_WORDS["first_path"]:
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
        intent["proof_boundary"] = _sentence(
            f"The first release works when a representative user can {action}, the product shows {outcome}, and missing or invalid information leaves a clear correction path instead of a misleading result. "
            f"It must not claim live integrations, broad automation, regulated correctness, or production-scale operation beyond the confirmed {title.lower()} boundary."
        )


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


def _complete_product_posture(intent: dict[str, Any], *, title: str) -> None:
    actors = _actor_labels(intent)
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
    needs_verb = _needs_verb(customer_text)

    if not _clean(intent.get("problem")):
        intent["problem"] = _sentence(
            _story_problem_sentence(story)
            or (
                f"{customer_text} {needs_verb} a dependable way to understand {state_phrase} and decide what to do from {outcome_text}; "
                "without it, the work stays scattered, hard to interpret, and easy to act on too late or for the wrong reason."
            )
        )
    elif _problem_needs_repair(intent.get("problem")):
        intent["problem"] = _sentence(
            f"{customer_text} {needs_verb} a dependable way to understand {state_phrase} and decide what to do from {outcome_text}; "
            "without it, the work stays scattered, hard to interpret, and easy to act on too late or for the wrong reason."
        )
    if not _clean(intent.get("customer")) or _customer_needs_repair(intent.get("customer")):
        intent["customer"] = _sentence(_customer_sentence(actors, title=title, first_path=first_path))
    if not _clean(intent.get("opportunity")):
        intent["opportunity"] = _sentence(
            f"Make the first version valuable by proving the smallest complete outcome: {path_capability}, ending in {outcome_text}."
        )
    if not _clean(intent.get("product_view")) or _product_view_needs_repair(intent.get("product_view")):
        intent["product_view"] = _sentence(
            f"{title} is useful when {customer_text} can {path_capability} and confidently use {outcome_text} to decide the next action."
        )
    metrics = _strings(intent.get("success_metrics"))
    if len(metrics) < 3 or any(_metric_needs_repair(metric) for metric in metrics):
        intent["success_metrics"] = [
            f"The first release proves the first path when {customer_text} can {path_capability} and reach {outcome_text} without manual interpretation outside the product.",
            f"The product handles missing or incorrect input by explaining what must be fixed before {outcome_text} is treated as real.",
            _proof_boundary_metric(proof, outcome=outcome_text),
        ]
    if not _strings(intent.get("assumptions")):
        intent["assumptions"] = [
            f"The first release proves one concrete {title.lower()} path before broader scope or automation.",
            "External integrations can start as deterministic fixtures unless the accepted path cannot be proven without a live source.",
            f"Security, privacy, accessibility, safety, audit, and retention obligations scale with the {focus.lower()} data and decisions involved.",
        ]
    if not _strings(intent.get("ambiguities")):
        intent["ambiguities"] = [
            f"Which {focus.lower()} actor has final release authority when evidence is incomplete or disputed?",
            f"Which source, device, document, dataset, or external service is authoritative for the first {title.lower()} proof?",
            "Which privacy, safety, compliance, or access rule would change the first path if it is stricter than assumed?",
        ]
    current_non_goals = _strings(intent.get("non_goals"))
    if not current_non_goals or _sequence_has_generic_non_goals(current_non_goals):
        extracted_non_goals = _non_goal_rows(intent, title=title)
        intent["non_goals"] = extracted_non_goals or [
            f"Do not expand beyond {path_capability} until the first outcome works for a representative user.",
            f"Do not claim adjacent automation, live dependency behavior, or broader operational scale until those outcomes are described and proven separately.",
        ]
    if not story:
        intent["product_story"] = _sentence(
            f"{title} helps {_join(actors[:2]) or f'{focus} users'} complete one accountable path with state, evidence, and decision context visible."
        )


def _story_problem_sentence(value: str) -> str:
    """Use accepted story language when it already states the user need."""

    text = _clean(value).strip(" .")
    if not text or not re.search(r"\bneeds?\b", text, flags=re.IGNORECASE):
        return ""
    first = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    return first if _word_count(first) >= 10 else ""


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
    text = re.sub(r"^(?:the\s+)?(?:core|main|primary)\s+state\s+(?:is|object\s+is)\s+", "", text, flags=re.I)
    text = re.sub(r"^a\s+", "the ", text, flags=re.I)
    first_clause = re.split(r";|(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    first_clause = re.split(r":\s*", first_clause, maxsplit=1)[-1].strip(" .")
    return _short(first_clause, fallback=f"{_focus_label(title).lower()} state", limit=160).rstrip(".")


def _visible_outcome_phrase(first_path: str, *, proof: str = "") -> str:
    text = first_path_outcome_phrase(first_path, proof_boundary=proof, fallback="a visible, useful result", limit=190).rstrip(".")
    if not re.search(r"\b(?:answer|appointment|booking|card|confirmation|decision|outcome|readout|recommendation|report|result|status|summary|view)\b", text, re.I):
        text = f"a visible outcome from {text}"
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
            if re.search(r"\b(?:out\s+of\s+scope|defer(?:red)?|later|future|not\s+claim|not\s+cover|without\s+claiming|beyond\s+the\s+first)\b", sentence, re.I):
                candidates.append(_sentence(sentence))
    rows = [row for row in unique_text(candidates) if _word_count(row) >= 5]
    return rows[:4]


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


def _completed_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    rows = _strings(intent.get("internal_systems")) or _strings(intent.get("component_responsibilities"))
    context = _context(intent)
    completed = [_system_row(row, context=context, title=title, explicit=bool(rows)) for row in rows]
    completed = [row for row in completed if row]
    if not completed:
        completed = _derived_system_rows(intent, title=title)
    return list(unique_text(completed))[:8]


def _system_row(row: str, *, context: str, title: str, explicit: bool = False) -> str:
    raw = _clean(row)
    if not raw:
        return ""
    if "—" in raw or ":" in raw:
        name, description = re.split(r"\s+—\s+|:\s*", raw, maxsplit=1)
        description = _clean_system_description(description)
        if _system_description_is_enough(description):
            return f"{_title_case(name)} — {description.rstrip('.')}"
    name = _system_label(raw, title=title)
    if not name:
        return ""
    clause = _best_context_clause(name, context)
    if explicit:
        if clause:
            return f"{name} — {_short(clause, limit=180)}"
        return name
    if clause:
        return (
            f"{name} — owns its accepted inputs, blocked states, produced outputs, and handoff evidence. "
            f"Context: {_short(clause, limit=180)}"
        )
    return f"{name} — owns input capture, state change, validation evidence, blocked states, and handoff for the accepted {title.lower()} path"


def _system_description_is_enough(value: str) -> bool:
    text = _clean(value)
    if _word_count(text) >= 5:
        return True
    return bool(
        _word_count(text) >= 3
        and re.search(
            r"\b(?:captures?|capturing|validates?|validating|computes?|computing|evaluates?|evaluating|"
            r"produces?|producing|returns?|returning|routes?|routing|records?|recording|stores?|storing|"
            r"configures?|configuring|owned\s+by|keeps?)\b",
            text,
            re.IGNORECASE,
        )
    )


def _derived_system_rows(intent: Mapping[str, Any], *, title: str) -> list[str]:
    focus = _focus_label(title)
    state = _state_label(_clean(intent.get("state_object")), title=title)
    proof = _short(_clean(intent.get("proof_boundary")), fallback="the release proof")
    names = [f"{focus} {suffix}" for suffix in _SYSTEM_SUFFIXES]
    descriptions = [
        f"owns identity, current status, version history, and traceable changes for {state}",
        "presents the current state, missing-information guidance, user-facing confirmation, and next useful action without owning source records",
        f"records the result, validation status, release decision, failure reason, and reviewable proof: {proof}",
        "shows the visible result, known limits, and recovery conditions before broader rollout",
    ]
    return [f"{_title_case(name)} — {description.rstrip('.')}" for name, description in zip(names, descriptions)]


def _clean_system_description(value: str) -> str:
    text = _clean(value).strip(" .")
    text = re.sub(
        r"\b(?:captures?|capturing)\s+user\s+actions?\b",
        "captures the product interaction",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:explains?|explaining)\s+blocked\s+states?\b",
        "explains missing or invalid information",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*(?:,?\s*and\s+)?(?:keeps?|keeping)\s+the\s+next\s+visible\s+step\s+tied\s+to\s*:\s*[^.]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*,\s*,\s*", ", ", text)
    text = re.sub(r"\s*,\s*(?:and\s*)?$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .,;:")


def _system_labels(intent: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    for row in _strings(intent.get("internal_systems")):
        labels.append(_system_label_head(row))
    return [label for label in labels if label]


def _system_label_head(value: str) -> str:
    head = _clean(value.split("—", 1)[0].split(":", 1)[0])
    split = re.search(
        r"\s+(?=(?:owned\s+by|captures?|capturing|validates?|validating|computes?|computing|evaluates?|evaluating|"
        r"produces?|producing|returns?|returning|routes?|routing|records?|recording|stores?|storing|"
        r"shows?|showing|renders?|rendering|generates?|generating|calculates?|calculating|"
        r"configures?|configuring|groups?|grouping|aligns?|aligning|tracks?|tracking|manages?|managing)\b)",
        head,
        flags=re.IGNORECASE,
    )
    if split:
        head = head[: split.start()].strip(" .:-")
    return head


def _system_label(row: str, *, title: str) -> str:
    raw = _clean(row)
    raw = re.sub(r"^(?:a|an|the)\s+", "", raw, flags=re.IGNORECASE)
    raw = _repair_system_label_tail(raw)
    if _word_count(raw) > 14:
        raw = _compact_system_label(raw)
    return _title_case(raw or f"{_focus_label(title)} system")


def _repair_system_label_tail(value: str) -> str:
    text = _clean(value).strip(" ,;:.")
    words = text.split()
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words).strip(" ,;:.")


def _compact_system_label(value: str) -> str:
    text = _repair_system_label_tail(value)
    if _word_count(text) <= 12:
        return text
    match = re.match(r"(?P<head>.+?\b(?:flow|capture|tracking|tracker|analytics|explanations|guardrails|controls|viewer|dashboard|workspace|workflow|service|engine|ledger|registry|store|journal|planner|generation|management|intake|versioning))\b", text, flags=re.IGNORECASE)
    if match and _word_count(match.group("head")) >= 2:
        return _repair_system_label_tail(match.group("head"))
    words = text.split()[:12]
    while words and words[-1].casefold().strip(".,;:") in {"and", "or", "for", "of", "the", "to", "with"}:
        words.pop()
    return " ".join(words)


def _state_label(value: str, *, title: str) -> str:
    text = _clean(value)
    if text:
        first = re.split(r"[.;]", text, maxsplit=1)[0]
        match = re.search(r"\b(?:state object is|primary state object is|is)\s+(?:a|an|the)?\s*(?P<label>[^.;:]+)", first, re.IGNORECASE)
        if match:
            return _title_case(match.group("label"))
        match = re.match(
            r"^(?:a|an|the)\s+(?P<label>[A-Za-z][A-Za-z0-9 _-]{1,90}?)\s+"
            r"(?:tracks|records|stores|captures|moves|starts|changes)\b",
            first,
            flags=re.IGNORECASE,
        )
        if match:
            return _title_case(match.group("label"))
        if _word_count(first) <= 8:
            return _title_case(first)
    return f"{_focus_label(title)} state"


def _title(intent: Mapping[str, Any]) -> str:
    return _clean(intent.get("title")) or "Greenfield Project"


def _title_needs_repair(value: str) -> bool:
    text = _clean(value)
    if normalize_project_title(text).changed:
        return True
    if not text or text.casefold() == "greenfield project":
        return True
    words = re.findall(r"[A-Za-z0-9]+", text)
    if not words:
        return True
    tail = words[-1].casefold()
    if tail in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        return True
    lowered = text.casefold()
    return len(words) > 10 and bool(
        re.search(r"\b(?:that|what|so|because|captures?|follows?|makes?|buying|using|needs?|wants?)\b", lowered)
    )


def _derived_title(intent: Mapping[str, Any], *, fallback: str) -> str:
    system_labels = [_clean(label) for label in _system_labels(intent) if _clean(label)]
    context = _title_context(intent)
    noun = _title_noun(context, system_labels)
    qualifier = _title_qualifier(context, system_labels, noun=noun)
    if qualifier and noun:
        return _title_case(f"{qualifier} {noun}")
    for label in system_labels:
        if 2 <= _word_count(label) <= 7:
            return _title_case(label)
    state_label = _state_label(_clean(intent.get("state_object")), title=fallback)
    if 2 <= _word_count(state_label) <= 7:
        return _title_case(state_label)
    return _focus_label(fallback)


def _title_context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("product_story")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(_strings(intent.get("internal_systems"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _title_noun(context: str, system_labels: Sequence[str]) -> str:
    nouns = (
        "workbench",
        "workspace",
        "watchlist",
        "journal",
        "dashboard",
        "tracker",
        "registry",
        "ledger",
        "portal",
        "planner",
        "viewer",
        "console",
        "list",
        "profile",
        "record",
        "workflow",
    )
    combined = " ".join([context, *system_labels]).casefold()
    for noun in nouns:
        if re.search(rf"\b{re.escape(noun)}s?\b", combined):
            return noun
    return "workspace"


def _title_qualifier(context: str, system_labels: Sequence[str], *, noun: str) -> str:
    candidates: list[tuple[int, str]] = []
    sources = [*system_labels, context]
    for source in sources:
        text = _clean(source)
        for match in re.finditer(
            r"\b(?P<phrase>[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){0,2})\s+"
            r"(?P<noun>activity|signal|signals|case|cases|record|records|item|items|request|requests|submission|submissions|evidence|data|profile|profiles)\b",
            text,
        ):
            phrase = _clean(f"{match.group('phrase')} {match.group('noun')}")
            phrase = re.sub(r"^(?:a|an|the)\s+", "", phrase, flags=re.IGNORECASE)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    for label in system_labels:
        words = [
            word
            for word in re.findall(r"[A-Za-z0-9]+", label)
            if word.casefold() not in _GENERIC_TITLE_WORDS and word.casefold() != noun.casefold()
        ]
        if 1 <= len(words) <= 3:
            phrase = " ".join(words)
            if _usable_title_phrase(phrase, noun=noun):
                candidates.append((_semantic_overlap(phrase, context), phrase))
    candidates.sort(key=lambda item: (-item[0], len(item[1])))
    return candidates[0][1] if candidates else ""


def _usable_title_phrase(value: str, *, noun: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    lowered = text.casefold()
    banned_words = {
        "can",
        "adds",
        "chooses",
        "compare",
        "compares",
        "could",
        "decide",
        "deserves",
        "doing",
        "each",
        "follow",
        "make",
        "makes",
        "needs",
        "only",
        "records",
        "reviews",
        "sees",
        "selected",
        "should",
        "that",
        "those",
        "whether",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "will",
        "wants",
    }
    if any(word in banned_words for word in lowered.split()):
        return False
    if noun.casefold() in lowered:
        return False
    if any(word in _GENERIC_TITLE_WORDS for word in lowered.split()):
        return False
    return _word_count(text) <= 4


def _context(intent: Mapping[str, Any]) -> str:
    parts = [
        _clean(intent.get("title")),
        _clean(intent.get("product_story")),
        _clean(intent.get("problem")),
        _clean(intent.get("customer")),
        _clean(intent.get("opportunity")),
        _clean(intent.get("product_view")),
        _clean(intent.get("state_object")),
        _clean(intent.get("first_path")),
        _clean(intent.get("proof_boundary")),
        " ".join(_strings(intent.get("human_actors"))),
        " ".join(_strings(intent.get("external_systems"))),
        " ".join(_strings(intent.get("assumptions"))),
        " ".join(_strings(intent.get("ambiguities"))),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _best_context_clause(name: str, context: str) -> str:
    terms = _semantic_terms(name)
    scored: list[tuple[int, int, str]] = []
    for index, sentence in enumerate(re.split(r"(?<=[.!?])\s+", context)):
        clause = _clean(sentence).strip(" .")
        if _word_count(clause) < 6:
            continue
        overlap = len(terms & _semantic_terms(clause))
        if overlap:
            scored.append((overlap, -index, clause))
    scored.sort(reverse=True)
    return scored[0][2] if scored else ""


def _strings(value: object) -> list[str]:
    return list(text_values(value))


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
