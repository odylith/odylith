"""Project-facing text helpers for greenfield Project dashboards."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import (
    capitalize_sentence_start_preserving_source_terms,
)
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import first_path_outcome_phrase
from odylith.runtime.project_intelligence.greenfield_sources import _first_slice_from_validation
from odylith.runtime.project_intelligence.greenfield_sources import _is_meta_first_path
from odylith.runtime.project_intelligence.greenfield_sources import _labeled_text_parts
from odylith.runtime.project_intelligence.product_story import project_intent_line
from odylith.runtime.project_intelligence.product_story import summarize_first_path
from odylith.runtime.project_intelligence.product_story import summarize_proof
from odylith.runtime.project_intelligence.utils import dict_value, display_text, list_value, sentence, short, strings, tidy_fragment

def _project_intro(*, title: str, intent: Mapping[str, Any], project: Mapping[str, Any]) -> str:
    candidates = [
        sentence(intent.get("product_story")),
        project_intent_line(project, "project objective"),
        project_intent_line(project, "user or stakeholder outcome"),
        sentence(intent.get("summary")),
        sentence(project.get("purpose")),
    ]
    for candidate in candidates:
        cleaned = _clean_objective_sentence(candidate)
        if cleaned and not _looks_meta_project_line(cleaned):
            return cleaned
    display = _title_case(_project_name_candidate(title) or sentence(title, "Project"))
    return f"{display} is a proposed product; the first path, actors, systems, and proof boundary need product-owner confirmation."


def _looks_meta_project_line(value: str) -> bool:
    lowered = sentence(value).casefold()
    if not lowered:
        return False
    if any(
        marker in lowered
        for marker in (
            "accepted product truth",
            "accepted project truth",
            "before backlog",
            "before any generated artifact",
            "governable as one product spine",
            "governance artifact",
            "proposal expansion",
            "source boundary",
        )
    ):
        return True
    if lowered.startswith("make ") and any(
        marker in lowered
        for marker in (
            "readable and governable",
            "before any generated artifact",
            "governable as one product spine",
            "source boundary",
        )
    ):
        return True
    return lowered.startswith(("capture ", "turn the operator request into"))

def _clean_objective_sentence(value: str) -> str:
    text = sentence(value)
    lowered = text.lower()
    if lowered.startswith("govern "):
        text = text[len("govern "):].strip()
    return _capitalize_first(text)


def _display_title(*, raw_title: str, intro: str) -> str:
    intro_text = sentence(intro)
    candidates = []
    if raw_title:
        candidates.append(raw_title)
    if intro_text.lower().startswith("govern "):
        candidates.append(intro_text[len("govern "):].strip())
    for article in ("A ", "An ", "The "):
        if intro_text.startswith(article):
            candidates.append(intro_text[len(article):].strip())
            break
    candidates.append(intro_text)
    candidates.append(raw_title)
    for candidate in candidates:
        head = _project_name_candidate(candidate)
        if 8 <= len(head) <= 64:
            return _title_case(head)
    return _clean_display_title(sentence(raw_title, "Greenfield project"))


def _project_name_candidate(value: str) -> str:
    text = _clean_display_title(_strip_prompt_directives(sentence(value)))
    lowered = text.casefold()
    if any(
        marker in lowered
        for marker in (
            "accepted product story",
            "accepted project",
            "source boundary",
            "governable",
            "before any generated artifact",
        )
    ):
        return ""
    for prefix in (
        "draft a greenfield proposal for ",
        "draft a product-first greenfield proposal for ",
        "draft a product first greenfield proposal for ",
        "build an ",
        "build a ",
        "build ",
        "create an ",
        "create a ",
        "create ",
    ):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].strip()
            break
    return _clean_display_title(_title_head(text))


def _title_head(value: str) -> str:
    text = _clean_display_title(sentence(value))
    that_head, that_sep, that_tail = _partition_casefold(text, " that ")
    if that_sep and _is_generic_product_noun(that_head):
        tail_head = _clause_head(that_tail)
        if tail_head:
            return _clean_display_title(f"{that_head.strip()} that {tail_head}")
    for marker in (" that ", " around ", " before ", " with ", " by ", " to "):
        head, sep, tail = _partition_casefold(text, marker)
        if sep:
            if marker == " with " and _should_keep_with_clause(head, tail):
                return _clean_display_title(f"{head.strip(' .')} with {_clause_head(tail)}")
            return _clean_display_title(head)
    return _clean_display_title(text)


def _should_keep_with_clause(head: str, tail: str) -> bool:
    """Keep short product names specific when their differentiator follows ``with``."""

    head_words = sentence(head).split()
    tail_head = _clause_head(tail)
    if not tail_head or len(head_words) > 3:
        return False
    generic_terms = {"app", "application", "platform", "product", "service", "site", "system", "tool"}
    return bool(head_words and head_words[-1].casefold() in generic_terms)


def _strip_prompt_directives(value: str) -> str:
    text = sentence(value)
    if not text:
        return ""
    command_starts = (
        "show ",
        "do not ",
        "don't ",
        "please ",
        "think of ",
        "make sure ",
        "use ",
    )
    kept: list[str] = []
    for raw in re.split(r"(?<=[.!?])\s+", text):
        clause = raw.strip()
        if not clause:
            continue
        lowered = clause.casefold()
        if kept and lowered.startswith(command_starts):
            continue
        kept.append(clause)
    return " ".join(kept) or text


def _is_generic_product_noun(value: str) -> bool:
    normalized = sentence(value).casefold().strip(" .")
    normalized = re.sub(r"^(?:a|an|the)\s+", "", normalized)
    return normalized in {
        "app",
        "application",
        "assistant",
        "platform",
        "product",
        "service",
        "system",
        "tool",
        "workflow",
    }


def _clause_head(value: str) -> str:
    text = sentence(value).strip(" .")
    for marker in (",", ";", ". ", " and ", " while ", " so ", " before "):
        head, sep, _tail = _partition_casefold(text, marker)
        if sep and head.strip():
            return head.strip(" .")
    return text


def _partition_casefold(value: str, marker: str) -> tuple[str, str, str]:
    index = value.casefold().find(marker.casefold())
    if index < 0:
        return value, "", ""
    return value[:index], value[index : index + len(marker)], value[index + len(marker) :]


def _title_case(value: str) -> str:
    return title_label(_clean_display_title(value))


def _clean_display_title(value: str) -> str:
    text = " ".join(sentence(value).split())
    text = re.sub(r"^[\s\-–—:·|]+", "", text)
    text = re.sub(r"[\s\-–—:·|]+$", "", text)
    return text.strip()


def _dashboard_open_items(*, questions: Sequence[str], risks: Sequence[str]) -> list[str]:
    rows: list[str] = []
    for item in [*questions[:3], *risks[:2]]:
        excerpt = _dashboard_excerpt(item, limit=150)
        if excerpt and excerpt not in rows:
            rows.append(excerpt)
    return rows[:4]


def _dashboard_excerpt(value: str, *, limit: int = 210) -> str:
    text = summarize_first_path(value) if re.search(r"\b\d+[.)]\s+[A-Z]", sentence(value)) else sentence(value).strip()
    if not text:
        return ""
    for separator in (". ", "; ", ": "):
        head, sep, _tail = text.partition(separator)
        if sep and 42 <= len(head) <= limit:
            return head.rstrip(" ,;:") + ("." if separator == ". " else "")
    return short(text, limit=limit)


def _capitalize_first(value: str) -> str:
    return capitalize_sentence_start_preserving_source_terms(value)


def _join_titles(values: Sequence[str]) -> str:
    items = [sentence(value) for value in values if sentence(value)]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} and {items[1]}"
    return f"{', '.join(items[:-1])}, and {items[-1]}"


def _state_object_change(project: Mapping[str, Any]) -> str:
    for row in strings(project.get("state")):
        obj = _state_object_name(row)
        if not obj:
            continue
        states = _state_names(row)
        if len(states) >= 2:
            return short(f"{obj} moves from {states[0]} to {states[-1]}", limit=80)
        return short(f"{obj} becomes the reviewable state object", limit=80)
    return ""


def _state_change_body(project: Mapping[str, Any]) -> str:
    for row in strings(project.get("state")):
        obj = _state_object_name(row)
        owned = _state_owned_pieces(row)
        if obj and owned:
            return short(f"The {obj} is the reviewable domain object: {_join_titles(owned[:4])}.", limit=180)
        if obj:
            return short(f"The {obj} is the state object reviewers should be able to understand, replay, and trust.", limit=180)
    return ""


def _state_object_name(value: object) -> str:
    text = sentence(value)
    patterns = (
        r"(?:primary\s+)?state object is (?:the\s+)?([A-Z][A-Za-z0-9 _/-]{1,48}?)(?:\.|;|,|\s+moves|\s+that|\s+through)",
        r"\bA\s+([A-Z][A-Za-z0-9 _/-]{1,48}?)\s+moves\s+through",
        r"\bAn\s+([A-Z][A-Za-z0-9 _/-]{1,48}?)\s+moves\s+through",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return sentence(match.group(1)).strip(" .")
    return ""


def _state_names(value: object) -> list[str]:
    text = sentence(value)
    names: list[str] = []
    blocked = {"evidence", "flow", "journey", "owns", "path", "proof", "state", "states"}
    for match in re.finditer(r"\b([a-z][a-z0-9_-]{1,32})\s*:", text):
        name = match.group(1).replace("_", " ").replace("-", " ").strip()
        if name.casefold() in blocked or name in names:
            continue
        names.append(name)
    return names[:8]


def _state_owned_pieces(value: object) -> list[str]:
    text = sentence(value)
    match = re.search(r"\bowns\s*:\s*(.+?)(?:\.\s+[A-Z][^.]*(?:changes|moves|must|should)\b|$)", text, flags=re.IGNORECASE)
    if not match:
        return []
    tail = match.group(1).strip(" .")
    pieces = [piece.strip(" .") for piece in re.split(r",|\s+and\s+", tail) if piece.strip(" .")]
    return [piece for piece in pieces if len(piece.split()) <= 8][:6]


def _desired_state(
    *,
    title: str,
    project: Mapping[str, Any],
    project_brief: Mapping[str, Any],
    first_path: str,
    validation: Sequence[str],
    risks: Sequence[str],
    release: str,
) -> str:
    reality = _desired_reality(title=title, project=project, project_brief=project_brief)
    capability = _desired_capability(project=project, project_brief=project_brief, first_path=first_path)
    proof = _desired_proof_summary(validation=validation, first_path=first_path, release=release)
    rows = [
        f"Target reality: {_desired_sentence(reality)}",
        f"User capability: {_desired_sentence(capability)}",
        f"Release trust: {_desired_sentence(proof)}",
    ]
    return " ".join(row for row in rows if row)


def _desired_reality(*, title: str, project: Mapping[str, Any], project_brief: Mapping[str, Any]) -> str:
    explicit = _clean_desired_state(strings(project.get("state")))
    if explicit:
        return _compact_desired_text(explicit)
    state_change = _state_object_change(project)
    if state_change:
        return f"{state_change} with supporting evidence visible."
    purpose = sentence(project_brief.get("purpose") or project_brief.get("summary") or project.get("purpose"))
    if purpose and not _looks_meta_project_line(purpose):
        body = _desired_reality_excerpt(purpose)
        body = _purpose_as_reality(body)
        return _compact_desired_text(body)
    return (
        f"People using {title} can understand the current product state without reconstructing context from scattered inputs."
    )


def _purpose_as_reality(value: str) -> str:
    text = sentence(value).rstrip(".")
    if not text.casefold().startswith("make "):
        return text
    remainder = text[5:].strip()
    head, sep, tail = _partition_casefold(remainder, " by ")
    if sep and head.strip() and tail.strip():
        words = head.strip().split()
        if len(words) >= 2:
            subject = " ".join(words[:-1])
            predicate = words[-1]
            return f"{_capitalize_first(subject)} is {predicate} through {tail.strip()}"
    return f"the team can {text[0].lower() + text[1:] if text else text}"


def _desired_reality_excerpt(value: object) -> str:
    text = sentence(value).rstrip(".")
    if not text:
        return ""
    sentences = [row.rstrip(".") for row in re.split(r"(?<=[.!?])\s+", text) if row.strip()]
    if not sentences:
        return text
    selected: list[str] = []
    for row in sentences:
        if len(" ".join(selected + [row])) > 180:
            break
        selected.append(row)
        if len(selected) >= 1:
            break
    return ". ".join(selected or sentences[:1]).rstrip(".")


def _clean_desired_state(rows: Sequence[str]) -> str:
    for row in rows:
        label, body = _labeled_text_parts(row)
        if label.replace("_", " ").replace("-", " ").casefold() == "desired state" and body:
            cleaned = sentence(body).rstrip(".")
            if cleaned and not _looks_meta_project_line(cleaned):
                return f"{cleaned}."
    return ""


def _desired_capability(*, project: Mapping[str, Any], project_brief: Mapping[str, Any], first_path: str) -> str:
    operator_value = sentence(project_brief.get("operator_value") or project_brief.get("project_outcome"))
    if operator_value and not _looks_proof_or_scope_line(operator_value):
        return _compact_desired_text(operator_value)
    state_body = _state_change_body(project)
    if state_body:
        return _compact_desired_text(state_body)
    path = summarize_first_path(first_path).rstrip(".") or sentence(first_path).rstrip(".")
    if path:
        return "The accepted first-path scenario works as the first usable product capability."
    return "The user can see the relevant object, current state, supporting evidence, and next decision in one place."


def _desired_risk(*, risks: Sequence[str], project: Mapping[str, Any]) -> str:
    risk = _risk_without_embedded_path(risks[0]) if risks else ""
    if risk:
        return f"The system reduces this domain risk first: {risk.rstrip('.')}."
    failure = project_intent_line(project, "what breaks if it fails")
    if failure:
        return f"The system reduces the failure mode where {failure[0].lower() + failure[1:] if failure else failure}."
    return "The system reduces the risk that product claims drift away from their source, time, owner, and evidence."


def _desired_proof(*, validation: Sequence[str], first_path: str, release: str) -> str:
    evidence = _proof_answer_body(validation=validation, first_path=first_path).rstrip(".")
    release_label = sentence(release, "the first release")
    if evidence:
        return f"Release {release_label} succeeds when a reviewer can follow the evidence needed to trust that first release: {evidence}."
    return (
        f"Release {release_label} succeeds when a reviewer can see the active object, current state, source evidence, "
        "changes since the prior state, and the audit trail that explains the result."
    )


def _desired_proof_summary(*, validation: Sequence[str], first_path: str, release: str) -> str:
    release_label = sentence(release, "the first release")
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof and not _looks_path_echo(proof, first_path=first_path):
        return _compact_desired_text(proof)
    return f"Release {release_label} is not trusted until source evidence and validation output prove the accepted scenario."


def _desired_sentence(value: object) -> str:
    text = _compact_desired_text(value)
    return text.rstrip(".") + "." if text else ""


def _compact_desired_text(value: object) -> str:
    text = sentence(value).strip()
    text = re.sub(r"\b\d+[.)]\s+[A-Z].*", "", text).strip(" .")
    text = text.replace("The desired operational reality is that ", "")
    text = text.replace("the desired operational reality is that ", "")
    text = text.replace("The first thing the product must prove is that ", "The accepted scenario is ")
    text = text.replace("the first thing the product must prove is that ", "the accepted scenario is ")
    text = text.replace("The first complete path the product must prove is ", "The accepted scenario is ")
    text = text.replace("The accepted first path passes end to end:", "")
    text = _dashboard_excerpt(text, limit=150)
    return tidy_fragment(text)


def _looks_proof_or_scope_line(value: object) -> bool:
    text = sentence(value).casefold()
    if not text:
        return False
    return any(
        marker in text
        for marker in (
            "what would count as evidence",
            "proof must show",
            "release proof",
            "first thing the product must prove",
            "must not be claimed",
            "no accuracy numbers",
            "passes end to end",
            "product must prove",
        )
    )


def _risk_without_embedded_path(value: object) -> str:
    text = sentence(value)
    if not text:
        return ""
    head, sep, _tail = text.partition(":")
    if sep and len(head) >= 48:
        return head.rstrip(" .") + "."
    if re.search(r"\b\d+[.)]\s+[A-Z]", text):
        return summarize_first_path(text)
    return text


def _clean_project_purpose(value: object) -> str:
    text = sentence(value)
    lowered = text.casefold()
    if lowered.startswith("explain why ") and "what stays outside the first release" in lowered:
        return ""
    if lowered.startswith("make ") and "concrete product program before implementation starts" in lowered:
        return ""
    if _looks_generated_project_purpose(text):
        return ""
    if "project object captures intent" in lowered:
        return ""
    return text


def _looks_generated_project_purpose(value: object) -> bool:
    lowered = sentence(value).casefold()
    return any(
        marker in lowered
        for marker in (
            "problem, first path, owned state, and proof boundary",
            "operating reality clear enough that a user can understand",
            "governable as one product spine",
            "before any generated artifact",
        )
    )


def _clean_proof_summary(value: object, *, first_path: str) -> str:
    text = sentence(value).strip()
    lowered = text.casefold()
    accepted_match = re.match(r"^(?:the\s+)?accepted\s+first\s+path\s+proves\s+(?P<body>.+)$", text, flags=re.IGNORECASE)
    if accepted_match:
        return f"The release proof covers {accepted_match.group('body').strip(' .')}."
    if (
        "success proof:" in lowered
        or "letting a representative user" in lowered
        or re.search(r"\b(?:check|ask|route|return|display|show)\s*[.]$", lowered)
    ):
        outcome = first_path_outcome_phrase(first_path, fallback="", limit=120)
        if outcome:
            return f"The first release must show that the first user can complete the scenario and receive {outcome}."
        return "The first release must show that the first user can complete the scenario and receive the promised result."
    return text


def _non_goal_rows(project: Mapping[str, Any]) -> list[str]:
    raw = project_intent_line(project, "non-goals")
    if not raw:
        return []
    pieces = [
        re.sub(r"^(?:and|or)\s+", "", piece.strip(" ."), flags=re.IGNORECASE)
        for piece in raw.split(",")
        if piece.strip(" .")
    ]
    if len(pieces) <= 1:
        pieces = [raw.strip(" .")]
    return [f"Not in the first release: {piece}." for piece in pieces[:4]]


def _host_handoff_prompts(*, title: str, accepted: bool = False) -> list[dict[str, str]]:
    if accepted:
        return [
            {
                "label": "Start implementation plan",
                "when": "Use this now when the product story and first release boundary look right.",
                "prompt": (
                    "Odylith, open the first implementation plan. Show the first source boundary, "
                    "files or modules likely to change, proof gates, blockers, and the exact first coding slice before editing source."
                ),
                "result": "Creates the plan that turns accepted direction into a source-editable slice.",
            },
            {
                "label": "Implement first coding slice",
                "when": "Use this only after the first implementation plan is accepted.",
                "prompt": (
                    "Odylith, implement the first coding slice from the accepted implementation plan. "
                    "Before editing, restate the target files, proof gates, validation commands, and stop conditions."
                ),
                "result": "Starts source edits for the first bounded slice.",
            },
            {
                "label": "Revise project direction",
                "when": "Use this when the accepted product story, actor, first path, or proof boundary is wrong.",
                "prompt": (
                    "Odylith, revise the accepted project direction: change <what is wrong> "
                    "to <what should be true>. Keep the product story, first path, component ownership, release gates, and proof boundary aligned."
                ),
                "result": "Updates the accepted project direction so the dashboard tells the corrected product story.",
            },
            {
                "label": "Pause",
                "when": "Use this when the accepted project should not proceed into planning yet.",
                "prompt": "Odylith, pause implementation planning; keep the accepted project visible but do not start source work.",
                "result": "Keeps project direction visible without implying implementation readiness.",
            },
        ]
    return [
        {
            "label": "Accept it",
            "when": "Use this when the story, first path, actors, open questions, and proof boundary look right.",
            "prompt": "Odylith, apply this greenfield proposal as-is and write the accepted project plan.",
            "result": "Writes the accepted product story, component boundaries, architecture views, release boundary, and proof gates.",
        },
        {
            "label": "Revise it",
            "when": "Use this when the project is close, but the first path, actor, system boundary, proof bar, or exclusions need correction.",
            "prompt": (
                "Odylith, revise this greenfield proposal before applying it: change <what is wrong> to <what should be true>. "
                "Keep the product story, first path, components, risks, and proof gates aligned with the correction. "
                "Do not write project records until I confirm."
            ),
            "result": "Produces a revised proposal for review without mutating accepted project records.",
        },
        {
            "label": "Reject it",
            "when": "Use this when the interpretation is the wrong product or the user intent is not clear enough.",
            "prompt": "Odylith, reject this greenfield proposal. Do not write project records.",
            "result": "Leaves the repo in proposal or blank state so a new intent can be supplied.",
        },
    ]


def _proof_title(validation: Sequence[str], *, first_path: str = "") -> str:
    text = sentence(validation[0] if validation else "")
    if "implementation-backed behavior proof" in text.casefold():
        return "First-slice behavior proof"
    proof = summarize_proof(text, first_path=first_path)
    if proof.casefold().startswith("the accepted first path passes end to end"):
        return "Accepted first path passes end to end"
    return short(proof, limit=70, fallback="First validation path")


def _proof_body(*, validation: Sequence[str], first_path: str) -> str:
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof:
        proof = _clean_proof_summary(proof, first_path=first_path)
        if proof.casefold().startswith("proof must show "):
            return proof.rstrip(".") + "."
        return proof.rstrip(".") + "."
    path = summarize_first_path(first_path)
    if path:
        return f"{path.rstrip('.')} must pass with reviewer-visible evidence."
    return "Validation path must be confirmed before source-backed claims."


def _proof_answer_body(*, validation: Sequence[str], first_path: str) -> str:
    proof = summarize_proof(validation[0] if validation else "", first_path=first_path)
    if proof and not _looks_path_echo(proof, first_path=first_path):
        proof = _clean_proof_summary(proof, first_path=first_path)
        return proof.rstrip(".") + "."
    return (
        "Release proof should show the accepted path running end to end with reviewer-visible source evidence, "
        "validation output, explicit non-goals, failure or recovery handling, and an explicit release decision."
    )


def _looks_path_echo(value: object, *, first_path: str) -> bool:
    text = _repeat_key(sentence(value))
    path = _repeat_key(summarize_first_path(first_path) or sentence(first_path))
    if not text:
        return False
    return (
        "first path" in text
        or "first complete path" in text
        or bool(path and (path in text or text in path))
    )


def _repeat_key(value: object) -> str:
    text = sentence(value).casefold()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _scenario_body(*, project: Mapping[str, Any], first_path: str, validation: Sequence[str]) -> str:
    purpose = short(
        _clean_project_purpose(project.get("purpose")) or _clean_objective_sentence(project_intent_line(project, "project objective")),
        limit=260,
        fallback="",
    )
    path = (summarize_first_path(first_path) or sentence(first_path)).rstrip(".")
    proof_text = _proof_body(validation=validation, first_path=first_path).rstrip(".")
    if _looks_generated_project_purpose(purpose):
        purpose = ""
    rows = []
    if purpose:
        rows.append(purpose.rstrip(".") + ".")
    if path:
        rows.append(f"First scenario: {path}.")
    if proof_text:
        rows.append(f"Proof needed: {proof_text}.")
    return " ".join(rows) or "The accepted product direction still needs implementation proof."


def _scenario_details(*, first_path: str, validation: Sequence[str], accepted: bool) -> list[tuple[str, str]]:
    path = (summarize_first_path(first_path) or sentence(first_path)).rstrip(".")
    proof = _proof_body(validation=validation, first_path=first_path).rstrip(".")
    evidence = (
        "Accepted direction only; implementation still needs source and validation evidence."
        if accepted
        else "Proposal direction only; the operator still needs to accept or revise it."
    )
    rows = []
    if path:
        rows.append(("First path", path + "."))
    if proof:
        rows.append(("Proof", proof + "."))
    rows.append(("Evidence state", evidence))
    return rows
