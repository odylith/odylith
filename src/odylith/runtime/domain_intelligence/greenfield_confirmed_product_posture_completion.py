"""Complete product posture fields from accepted Greenfield intent."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import actor_row_description
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import customer_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_actor_completion import needs_verb
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import first_release_actor_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import inline_result_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion_text_model import outcome_action_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_non_goals import non_goal_rows
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_text import path_capability
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_text import proof_boundary_metric
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_text import state_focus_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_product_posture_text import visible_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import clean_confirmed_text as _clean
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import confirmed_text_values
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import focus_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import join_confirmed_items
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import sentence_confirmed_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import readable_action_chain_sentence
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import action_chain_fragment
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_step_roles import is_supporting_setup_step
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_capability_phrase


def first_release_actor_labels(intent: Mapping[str, Any]) -> list[str]:
    return _actor_labels(first_release_actor_rows(confirmed_text_values(intent.get("human_actors"))))


def complete_product_posture(intent: dict[str, Any], *, title: str) -> None:
    actor_rows = first_release_actor_rows(confirmed_text_values(intent.get("human_actors")))
    actors = _actor_labels(actor_rows)
    story = _clean(intent.get("product_story"))
    state = _clean(intent.get("state_object"))
    first_path = _clean(intent.get("first_path"))
    proof = _clean(intent.get("proof_boundary"))
    focus = focus_label(title)
    customer_text = customer_summary(actors, title=title)
    outcome_text = visible_outcome_phrase(first_path, proof=proof)
    state_phrase = state_focus_phrase(state, title=title)
    path = path_capability(first_path, fallback=f"the first {title.lower()} path")
    proof_capability = first_path_capability_phrase(
        first_path,
        fallback=path,
        limit=340,
        gerund=True,
        max_fragments=8,
    )
    proof_capability = readable_action_chain_phrase(
        first_path,
        fallback=proof_capability,
        limit=240,
        max_steps=4,
    )
    metric_proof_capability = _metric_first_path_proof_capability(
        first_path,
        fallback=proof_capability,
    )
    if len(metric_proof_capability) > 240:
        metric_proof_capability = readable_action_chain_sentence(
            first_path,
            fallback=proof_capability,
            limit=240,
            max_steps=5,
            include_visible_results=True,
        )
    customer_needs_verb = needs_verb(customer_text)
    decision_phrase = _decision_problem_phrase(outcome_text)
    outcome_inline = inline_result_phrase(outcome_text)

    if not _clean(intent.get("problem")):
        intent["problem"] = sentence_confirmed_text(
            _story_problem_sentence(story)
            or (
                f"{customer_text} {customer_needs_verb} a dependable way to understand {state_phrase} and {decision_phrase}; "
                "without it, the work stays scattered, hard to interpret, and easy to misuse."
            )
        )
    elif _problem_needs_repair(intent.get("problem")):
        intent["problem"] = sentence_confirmed_text(
            f"{customer_text} {customer_needs_verb} a dependable way to understand {state_phrase} and {decision_phrase}; "
            "without it, the work stays scattered, hard to interpret, and easy to misuse."
        )
    if not _clean(intent.get("customer")) or _customer_needs_repair(intent.get("customer")):
        intent["customer"] = sentence_confirmed_text(
            _customer_sentence(actor_rows, title=title, first_path=first_path)
        )
    if not _clean(intent.get("opportunity")):
        intent["opportunity"] = sentence_confirmed_text(
            f"Make the first version valuable by proving the smallest complete outcome: {path}, ending in {outcome_inline}."
        )
    if not _clean(intent.get("product_view")) or _product_view_needs_repair(intent.get("product_view")):
        outcome_action = outcome_action_phrase(outcome_text)
        intent["product_view"] = sentence_confirmed_text(
            f"{title} is release-ready when {customer_text} can {path}, confidently {outcome_action}, and recover when required context is missing."
        )
    metrics = confirmed_text_values(intent.get("success_metrics"))
    if len(metrics) < 3 or any(_metric_needs_repair(metric) for metric in metrics):
        metric_outcome_action = outcome_action_phrase(outcome_text)
        intent["success_metrics"] = [
            f"The first release proves the first path: {metric_proof_capability or proof_capability}.",
            f"Users can {metric_outcome_action} without manual interpretation outside the product.",
            f"The product handles missing or incorrect input by explaining what must be fixed before {outcome_inline} is treated as real.",
            proof_boundary_metric(proof, outcome=outcome_inline),
        ]
    if not confirmed_text_values(intent.get("assumptions")):
        intent["assumptions"] = [
            f"The first release proves one concrete {title.lower()} path before broader scope or automation.",
            "External integrations can start as deterministic fixtures unless the accepted path cannot be proven without a live source.",
            f"Security, privacy, accessibility, safety, audit, and retention obligations scale with the {focus.lower()} data and decisions involved.",
        ]
    current_non_goals = confirmed_text_values(intent.get("non_goals"))
    if not current_non_goals or _sequence_has_generic_non_goals(current_non_goals):
        extracted_non_goals = non_goal_rows(intent, title=title)
        intent["non_goals"] = extracted_non_goals or [
            "Do not expand into adjacent workflows, broader automation, or operational scale until the first outcome works for a representative user.",
            "Do not claim adjacent automation, live dependency behavior, or broader operational scale until those outcomes are described and proven separately.",
        ]
    if not story:
        actor_summary = join_confirmed_items(actors[:2]) or f"{focus} users"
        intent["product_story"] = sentence_confirmed_text(
            f"{title} helps {actor_summary} complete one accountable path with state, evidence, and decision context visible."
        )


def _actor_labels(rows: Sequence[str]) -> list[str]:
    labels: list[str] = []
    for row in rows:
        label = _clean(str(row).split("—", 1)[0].split(":", 1)[0]).strip(" .")
        if label:
            labels.append(label)
    return labels


def _metric_first_path_proof_capability(value: str, *, fallback: str) -> str:
    model = first_path_model(value)
    if any(is_supporting_setup_step(step) for step in model.steps):
        return fallback
    return action_chain_fragment(value) or fallback


def _story_problem_sentence(value: str) -> str:
    text = _clean(value).strip(" .")
    if not text or not re.search(r"\bneeds?\b", text, flags=re.IGNORECASE):
        return ""
    first = re.split(r"(?<=[.!?])\s+", text, maxsplit=1)[0].strip(" .")
    return first if word_count(first) >= 10 else ""


def _decision_problem_phrase(outcome_text: str) -> str:
    outcome = inline_result_phrase(_clean(outcome_text).rstrip(" .") or "the product result")
    if outcome.casefold().startswith("the tracked metric trend view"):
        return "act on the tracked metric trend view"
    return f"decide the next step from {outcome}"


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
        re.search(r"\bis\s+not\s+trustworthy\s+when\b", text, re.IGNORECASE)
        or re.search(r"\bunderstand\s+(?:A|An|The)\b", text)
        or re.search(r"\bsource\s+evidence|visible\s+blockers|systems?\s+that\s+own\s+the\s+handoff\b", text, re.IGNORECASE)
        or re.search(r"\bfirst\s+path\s+entry\b", text, re.IGNORECASE)
        or re.search(r"\bactive\s+and\s+decide\b", text, re.IGNORECASE)
        or re.search(r"\bfrom\s+(?:A|An|The)\s+[A-Za-z0-9/-]+[^.]{0,100}\b(?:sees?|views?|receives?|reads?|gets?)\b", text)
        or re.search(r"\b(?:use|reach)\s+(?:a|an|the|[A-Z][A-Za-z0-9/-]*)\s+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?)\b", text)
    )


def _customer_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    return bool(re.search(r"\bneed\s+the\s+accepted\s+outcome\b|\baccepted\s+path\b", text, re.IGNORECASE))


def _sequence_has_generic_non_goals(values: Sequence[str]) -> bool:
    text = " ".join(_clean(value) for value in values)
    return bool(
        re.search(r"\bstays\s+limited\s+to\s+the\s+accepted\b", text, re.IGNORECASE)
        or re.search(r"\bbroader\s+users,\s+integrations,\s+datasets,\s+edge\s+cases\b", text, re.IGNORECASE)
        or re.search(r"\bseparately\s+accepted\s+proof\s+boundary\b", text, re.IGNORECASE)
    )


def _metric_needs_repair(value: Any) -> bool:
    text = _clean(value)
    if not text:
        return True
    if re.search(r"[,:]\.$", text):
        return True
    if re.search(r"\baccepted\s+path\s+lets\s+users\b|\bproof\s+boundary\b|\bevidence\s+context\b", text, re.IGNORECASE):
        return True
    if re.search(r"\b(?:use|reach)\s+(?:a|an|the|[A-Z][A-Za-z0-9/-]*)\s+[^.]{0,80}\b(?:sees?|views?|receives?|reads?|gets?)\b", text):
        return True
    if text.rstrip().endswith(","):
        return True
    tail = text.rstrip(".;:, ").split()[-1].casefold() if text.split() else ""
    return tail in {"and", "or", "to", "with", "for", "from", "of", "the", "a", "an", "required"}


def _customer_sentence(actors: Sequence[str], *, title: str, first_path: str) -> str:
    rows = []
    for value in actors[:4]:
        label = _clean(value).split(":", 1)[0].split("—", 1)[0].strip(" .")
        description = actor_row_description(value)
        if label and description:
            rows.append(f"{label} {description}")
        elif label:
            rows.append(f"{label} participates in the product outcome")
    if rows:
        return "; ".join(rows)
    path = readable_action_chain_phrase(first_path, fallback=first_path_capability_phrase(first_path))
    return f"{focus_label(title)} users need to {path} and understand the outcome."


__all__ = ["complete_product_posture", "first_release_actor_labels"]
