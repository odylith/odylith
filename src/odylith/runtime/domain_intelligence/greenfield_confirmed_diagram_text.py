"""Text and label model for confirmed greenfield Atlas diagrams."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common import mermaid_text
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.common.prose_grammar import looks_like_base_action_token
from odylith.runtime.common.prose_grammar import looks_like_finite_action_token
from odylith.runtime.common.prose_tail import strip_dangling_word_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import proof_claim_summary
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import rationale_deferred_focus
from odylith.runtime.domain_intelligence.greenfield_confirmed_backlog_text_model import semantic_words
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import strip_dangling_tail as strip_confirmed_dangling_tail
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_label
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import base_adverbial_note_action
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import balance_label
from odylith.runtime.domain_intelligence.greenfield_sequence_labeling import flow_label as wrapped_flow_label
from odylith.runtime.domain_intelligence.greenfield_text import clean_markdown_sentence
from odylith.runtime.domain_intelligence.greenfield_text import clip_text_at_word_boundary
from odylith.runtime.domain_intelligence.greenfield_text import normalize_proof_boundary_language
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language


def component_description(row: Mapping[str, Any]) -> str:
    source_description = str(row.get("source_system_description", "")).strip()
    responsibility = str(row.get("responsibility", "")).strip()
    boundary = str(row.get("boundary", "")).strip()
    label = str(row.get("label", "")).strip() or "Component"
    kind = _component_kind(row=row, label=label)
    responsibility_text = _responsibility_fragment(label=label, value=source_description or responsibility)
    boundary_text = _responsibility_fragment(label=label, value=boundary)
    subject = _component_subject(label=label, responsibility=responsibility_text, boundary=boundary_text)
    lead = _component_lead(label=label, subject=subject, kind=kind)
    review = _component_review_sentence(label=label, subject=subject, kind=kind)
    return f"{sentence(lead)} {sentence(review)}"


def sentence(value: str) -> str:
    return clean_markdown_sentence(value)


def brief_first_path(value: str) -> str:
    text = compact_text(value)
    if not text:
        return ""
    text = re.sub(
        r"^the first complete path to prove should be\s*:?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^first complete path to prove should be\s*:?\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^the first complete path (?:the product )?(?:must|should) prove (?:before broader scope )?is\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s+(?:flow|journey|path)\s*:\s*.*$", "", text, flags=re.IGNORECASE)
    text = re.split(r"\s+\d+\.\s+", text, maxsplit=1)[0]
    text = text.split(". ", 1)[0]
    text = base_adverbial_note_action(text)
    return trim(text.strip(" .:"), 300)


def brief_story(value: str, *, fallback: str) -> str:
    text = compact_text(value)
    if not text:
        return trim(fallback, 180)
    text = text.split(". ", 1)[0]
    text = re.sub(r"^product\s+story\s*:?\s*", "", text, flags=re.IGNORECASE).strip(" .:")
    return trim(text or fallback, 220)


def brief_proof_boundary(value: str) -> str:
    text = compact_text(value)
    if not text:
        return ""
    text = proof_claim_summary(normalize_proof_boundary_language(text), limit=180)
    text = text.split(". ", 1)[0]
    return trim(text.strip(" .:"), 150)


def component_phrase(components: list[dict[str, Any]]) -> str:
    names = [str(row.get("label", "")).strip() for row in components[:3] if str(row.get("label", "")).strip()]
    if not names:
        return "the product-owned boundary"
    if len(names) == 1:
        return names[0]
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def actor_phrase(actors: list[str], *, label: str) -> str:
    actor = str(actors[0] if actors else "").strip()
    actor = actor.split("—", 1)[0].split(":", 1)[0].strip()
    return actor or f"{label} user"


def semantic_proof_checkpoint(semantic_model: Mapping[str, Any] | None) -> str:
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if isinstance(contract, Mapping):
        visible = normalize_visible_result_language(compact_text(str(contract.get("visible_result") or "")))
        visible = _strip_dangling_tail(visible)
        visible = _proof_checkpoint_from_visible_result(visible)
        visible = _lower_leading_possessive_fragment(visible)
        if word_count(visible) >= 3:
            return trim(visible, 140)
    graph = semantic_model.get("diagram_event_graph")
    if isinstance(graph, Mapping):
        value = normalize_proof_boundary_language(compact_text(str(graph.get("proof_checkpoint") or "")))
        value = _strip_dangling_tail(value)
        if word_count(value) >= 4:
            return trim(value, 140)
    return ""


def semantic_visible_result_label(semantic_model: Mapping[str, Any] | None) -> str:
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    visible = normalize_visible_result_language(compact_text(str(contract.get("visible_result") or "")))
    return _lower_leading_possessive_fragment(_strip_dangling_tail(visible))


def proof_evidence_label(*, components: list[dict[str, Any]], fallback: str) -> str:
    for component in components:
        label = str(component.get("label", "")).strip()
        if _explicit_proof_owner_label(label):
            return _proof_record_label(label)
    accepted = _accepted_proof_record_label(fallback)
    if accepted:
        return accepted
    for component in components:
        label = str(component.get("label", "")).strip()
        if re.search(r"\b(record|log|attachment|source)\b", label, re.IGNORECASE):
            return _proof_record_label(label)
    return fallback


def _explicit_proof_owner_label(value: str) -> bool:
    return bool(re.search(r"\b(audit|trail|history|evidence|source-backed|version|provenance|proof|trace)\b", value, re.IGNORECASE))


def _accepted_proof_record_label(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text or word_count(text) > 10:
        return ""
    terms = semantic_words(text)
    if terms & {"audit", "evidence", "history", "proof", "trace"} and terms & {"ledger", "packet", "record", "trail"}:
        return title_label(text) or text
    return ""


def _proof_record_label(value: str) -> str:
    text = title_label(value) or compact_text(value)
    lowered = text.casefold()
    if lowered.endswith(" proof record"):
        return text
    if lowered.endswith(" record") and " proof " in f" {lowered} ":
        return text
    if lowered.endswith((" audit ledger", " evidence ledger", " history ledger", " proof ledger", " trace ledger", " ledger")):
        return f"{text} Record"
    if lowered.endswith(" proof"):
        return f"{text} Record"
    return f"{text} Proof Record"


def proof_checkpoint_label(value: str) -> str:
    text = normalize_proof_boundary_language(compact_text(value))
    if not text:
        return ""
    clauses = [
        clause.strip(" .")
        for clause in re.split(
            r";\s+|(?<=[.!?])\s+|\s+\band\b\s+|,\s+(?=(?:assign|assigns|receive|receives|see|sees|show|shows|view|views|leave|leaves|record|records|review|reviews|return|returns)\b)",
            text,
            flags=re.IGNORECASE,
        )
        if clause.strip(" .")
    ]
    for clause in clauses:
        if word_count(clause) >= 4:
            return trim(clause, 120)
    return ""


def diagram_sentence_label(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an|the|this|that)\b", text, flags=re.IGNORECASE):
        return f"{text[:1].upper()}{text[1:]}"
    return text


def release_proof_label(value: str) -> str:
    brief = brief_proof_boundary(value)
    if not brief:
        return ""
    label = proof_checkpoint_label(brief) or trim(brief, 80)
    return _strip_release_label_prefix(label)


def _strip_release_label_prefix(value: str) -> str:
    text = compact_text(value).strip(" .")
    text = _release_label_tail(text)
    complete_prefix = "is complete when "
    if text.casefold().startswith(complete_prefix):
        text = text[len(complete_prefix) :].strip(" .")
    release_prefix = "release "
    if text.casefold().startswith(release_prefix):
        text = text[len(release_prefix) :].strip(" .")
    return text


def _release_label_tail(value: str) -> str:
    text = compact_text(value).strip(" .")
    lowered = text.casefold()
    for prefix in ("release ", "version "):
        if not lowered.startswith(prefix):
            continue
        tail = text[len(prefix) :].strip()
        version, separator, rest = tail.partition(" ")
        if separator and _looks_like_release_selector(version):
            return rest.strip(" .")
    return text


def _looks_like_release_selector(value: str) -> bool:
    token = str(value or "").strip()
    return bool(token) and all(char.isalnum() or char in "._-" for char in token)


def _is_release_completion_label(value: str) -> bool:
    tail = _release_label_tail(value)
    if tail.casefold().startswith(("is complete when ", "is ready when ", "succeeds when ", "succeeds only when ")):
        return True
    return value.casefold() != tail.casefold() and tail.casefold().startswith(
        ("complete when ", "ready when ", "succeeds when ", "succeeds only when ")
    )


def deferred_scope_label(value: str, *, label: str = "", fallback: str = "beyond accepted first path") -> str:
    text = compact_text(value)
    if not text:
        return fallback
    if _is_release_completion_label(text):
        return fallback
    if _looks_like_deferred_component_label(text):
        return trim(text, 72) or fallback
    explicit = _explicit_deferred_scope(text)
    if explicit:
        return trim(explicit, 72) or fallback
    if re.match(r"^(?:avoid|do\s+not|don't|never)\s+expand\s+beyond\b", text, flags=re.IGNORECASE):
        return fallback
    focus = rationale_deferred_focus(value="", label=label or "product", fallback=fallback, deferred_scope=[text])
    if focus and focus.casefold() != text.casefold():
        return trim(focus, 72) or fallback
    return fallback


def workstream_titles(
    *,
    label: str,
    components: list[dict[str, Any]],
    provided: Mapping[str, str] | None,
) -> dict[str, str]:
    first_component = component_label(components, 0, fallback=label)
    second_component = component_label(components, 1, fallback=label)
    third_component = component_label(components, 2, fallback=label)
    titles = {
        "parent": f"Prove One Complete Path for {label}",
        "workflow": f"Prove {first_component}",
        "boundary": f"Define {second_component} Boundary",
        "proof": f"Prepare {third_component} Release Proof",
    }
    for key, value in (provided or {}).items():
        if key in titles and str(value).strip():
            titles[key] = str(value).strip()
    return titles


def brief_object_label(value: str, *, fallback: str) -> str:
    text = compact_text(value)
    if not text:
        return fallback
    shared_label = domain_object_label(text, fallback="")
    if shared_label:
        return trim(shared_label, 72)
    first = text.split("—", 1)[0].split(". ", 1)[0].strip(" .:")
    patterns = (
        r"\b(?:primary\s+)?state\s+object\s+is\s+(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+?)(?:\s+(?:that|which|who|where|tracks?|records?|stores?|captures?|moves?|starts?)\b|$)",
        r"^(?:the|an|a)\s+(?P<label>[A-Za-z][A-Za-z0-9 _/-]{2,80}?)\s+(?:tracks?|records?|stores?|captures?|moves?|starts?|keeps?)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, first, flags=re.IGNORECASE)
        if match:
            candidate = compact_text(match.group("label")).strip(" .:")
            if candidate:
                return trim(candidate, 72)
    first = re.sub(r"^(?:a|an|the)\s+", "", first, flags=re.IGNORECASE)
    return trim(first or fallback, 72)


def component_label(components: list[dict[str, Any]], index: int, *, fallback: str) -> str:
    if index < len(components):
        label = str(components[index].get("label", "")).strip()
        if label:
            return trim(label, 72)
    return fallback


def short_label(value: str) -> str:
    text = _role_or_short_label(value) or "Actor"
    return escape_label(trim(text, 72))


def flow_label(value: str, *, limit: int) -> str:
    text = _role_or_short_label(value) or "Item"
    return wrapped_flow_label(text, width=30, max_lines=4, limit=limit)


def escape_label(value: str) -> str:
    return mermaid_text.escape_mermaid_label(value)


def trim(value: str, limit: int) -> str:
    text = compact_text(value)
    if len(text) <= limit:
        return balance_label(_strip_dangling_tail(text))
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return balance_label(_strip_dangling_tail(clipped))


def compact_text(value: str) -> str:
    return mermaid_text.clean_mermaid_text(value)


def _component_kind(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    label_text = label.casefold()
    if re.search(r"\b(adapter|connector|integration|provider|import)\b", label_text):
        return "adapter"
    if re.search(r"\b(client|surface|ui|portal|dashboard|app|view)\b", label_text):
        return "client"
    if kind in {"adapter", "client", "service"}:
        return kind
    return "service"


def _component_subject(*, label: str, responsibility: str, boundary: str) -> str:
    for candidate in (responsibility, boundary):
        subject = _clean_component_subject(candidate)
        if subject and not _shallow_component_subject(subject, label=label):
            return subject
    return _label_subject(label)


def _component_lead(*, label: str, subject: str, kind: str) -> str:
    if _looks_like_action_clause(subject):
        clause = finite_action_clause(subject)
        if _component_clause_explains_boundary(clause):
            return clause
        return f"Owns product responsibility to {_base_initial_action_clause(clause)}"
    if re.match(
        r"^(?:maintains?|owns?|coordinates?|presents?|translates?|records?|tracks?|assembles?|computes?|"
        r"applies?|checks?|captures?|selects?|schedules?|summarizes?)\b",
        subject,
        flags=re.IGNORECASE,
    ):
        return finite_action_clause(subject)
    if kind == "adapter":
        if _is_workflow_like(label, subject):
            return f"Coordinates {subject} across outside systems and product-owned records while preserving provenance"
        return f"Translates {subject} inputs into product-owned records and preserves source provenance"
    if kind == "client":
        return f"Presents {subject} to users and captures the action or decision the product needs next"
    if _is_record_like(label, subject):
        return f"Maintains {subject} as a product-owned record with reviewable history"
    if _is_workflow_like(label, subject):
        return f"Coordinates {subject} so responsibility transfers, blocked states, and recovery paths stay visible"
    if _is_decision_like(label, subject):
        return f"Owns rules or calculations for {subject}"
    return f"Owns {subject}"


def _component_clause_explains_boundary(value: str) -> bool:
    return bool(
        re.search(
            r"\b(?:owns?|owned|responsible|authority|boundary|state|record|version|source of truth|"
            r"displays?|exposes?|presents?|publishes?|receives?|produces?|records?|shows?|stores?|tracks?|links?|assembles?|derives?|controls?|"
            r"protects?|coordinates?|maintains?|preserves?)\b",
            value,
            re.IGNORECASE,
        )
    )


def _base_initial_action_clause(value: str) -> str:
    text = str(value or "").strip(" .")
    first, separator, rest = text.partition(" ")
    if not first:
        return text
    base = base_action_clause(f"{first} placeholder").partition(" ")[0] or first
    return f"{base} {rest.strip()}" if separator else base


def _component_review_sentence(*, label: str, subject: str, kind: str) -> str:
    boundary_label = label if re.search(r"\bboundary$", label, flags=re.IGNORECASE) else f"{label} boundary"
    lead = f"The {boundary_label} must show"
    if kind == "adapter":
        return f"{lead} which source supplied the input, what result was accepted, and which error state blocked unsafe input"
    if kind == "client":
        return f"{lead} what the user saw, submitted, corrected, or approved and which product state changed after that action"
    if _is_workflow_like(label, subject):
        return f"{lead} responsibility transfers, failure states, recovery actions, and final outcomes"
    if _is_record_like(label, subject):
        if re.search(r"\b(?:audit|evidence|provenance|source|trail|version|versioned)\b", f"{label} {subject}", re.IGNORECASE):
            return f"{lead} versioned state, source evidence, and decisions that depended on this record"
        return f"{lead} saved state, important inputs, status changes, and decisions that depended on this record"
    if _is_decision_like(label, subject):
        return f"{lead} inputs, rule versions, results, and downstream decisions that depended on it"
    return f"{lead} what this boundary receives, produces, records, and makes available next"


def _clean_component_subject(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.split(r"\b(?:design pressure|domain evidence|relevant behavior)\s*:", text, maxsplit=1, flags=re.IGNORECASE)[0]
    text = text.split(";", 1)[0]
    text = re.sub(r"\bfor\s+the\s+accepted\s+first\s+(?:release\s+)?path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\band\s+proof\s+boundary\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bneeded\s+by\s+the\s+accepted\s+first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\bthe\s+accepted\s+first\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\baccepted\s+first\s+release\s+path\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .,:;")
    return _lower_domain_phrase(_strip_component_type_suffix(text), preserve_mixed_case=True)


def _shallow_component_subject(subject: str, *, label: str) -> bool:
    text = subject.casefold().strip(" .")
    if not text:
        return True
    if text == label.casefold():
        return True
    if re.fullmatch(r"(?:this\s+)?(?:component\s+)?responsibility", text):
        return True
    return not re.search(r"[a-z0-9]", text)


def _label_subject(label: str) -> str:
    text = compact_text(label).strip(" .")
    return _lower_domain_phrase(_strip_component_type_suffix(text) or label, preserve_mixed_case=False)


def _strip_component_type_suffix(value: str) -> str:
    return re.sub(
        r"\b(?:adapter|service|engine|surface|client|module|system|component)\b$",
        "",
        str(value or ""),
        flags=re.IGNORECASE,
    ).strip(" .")


def _lower_domain_phrase(value: str, *, preserve_mixed_case: bool) -> str:
    words = []
    for word in str(value or "").strip().split():
        if word.isupper() and len(word) > 1:
            words.append(word)
        elif preserve_mixed_case and any(char.isupper() for char in word[1:]):
            words.append(word)
        else:
            words.append(word[:1].lower() + word[1:])
    return " ".join(words)


def _is_record_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(records?|ledgers?|stores?|registr(?:y|ies)|trails?|histor(?:y|ies)|snapshots?|status|states?|logs?|index(?:es|)|indices)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _is_workflow_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(workflow|orchestrat\w*|queue|handoff|review|approval|coordination|routing)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _is_decision_like(label: str, subject: str) -> bool:
    return bool(
        re.search(
            r"\b(engine|scor\w*|rank\w*|pricing|detect\w*|classif\w*|estimate\w*|resolv\w*|deriv\w*|calculat\w*|rules?)\b",
            f"{label} {subject}",
            re.IGNORECASE,
        )
    )


def _responsibility_fragment(*, label: str, value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    text = _strip_leading_label(label=label, text=text)
    owns_index = text.casefold().find(" owns ")
    if 0 <= owns_index <= 70:
        text = text[owns_index + len(" owns ") :].strip()
    if text.casefold().startswith("owns "):
        text = text[5:].strip()
    if text.casefold().startswith("responsible for "):
        text = text[len("responsible for ") :].strip()
    return text.strip(" .")


def _strip_leading_label(*, label: str, text: str) -> str:
    words = str(label or "").strip().split()
    if not words:
        return text
    for keep in range(len(words), 0, -1):
        pattern = r"^\s*" + r"[\s,/-]+".join(re.escape(word) for word in words[:keep]) + r"\b\s*"
        stripped = re.sub(pattern, "", text, count=1, flags=re.IGNORECASE).strip()
        if stripped != text.strip():
            if re.match(r"^(?:for|of|in|with|to|by|from|through|into|on|at)\b", stripped, flags=re.IGNORECASE):
                return text
            return stripped or text
    return text


def _looks_like_action_clause(value: str) -> bool:
    text = str(value or "").strip()
    if re.match(
        r"^(?:review|approval|support)\s+(?:screen|view|surface|page|form|dashboard|queue|desk|center)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return looks_like_action_clause(value)


def _proof_checkpoint_from_visible_result(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    if re.match(r"^(?:a|an)\s+", text, flags=re.IGNORECASE) and re.search(
        r"\b(?:board|chart|dashboard|feed|list|map|page|screen|summary|table|timeline|view)\b",
        text,
        flags=re.IGNORECASE,
    ):
        if _looks_like_actor_led_visible_result(text):
            return sentence(text).rstrip(".")
        return f"The visible result shows {text[:1].lower()}{text[1:]}"
    return _lower_fragment_start(sentence(text).rstrip("."))


def _looks_like_actor_led_visible_result(value: str) -> bool:
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", compact_text(value))
    if len(words) < 3:
        return False
    start = 1 if words[0].casefold() in {"a", "an", "the"} else 0
    max_subject_words = min(start + 4, len(words) - 1)
    for verb_index in range(start + 1, max_subject_words + 1):
        token = words[verb_index].casefold().strip(".,:;")
        if looks_like_base_action_token(token) or looks_like_finite_action_token(token):
            return True
    return False


def _lower_fragment_start(value: str) -> str:
    text = compact_text(value).strip(" .")
    if re.match(r"^(?:A|An|The|Their|This|That)\b", text):
        return f"{text[:1].casefold()}{text[1:]}"
    return text


def _lower_leading_possessive_fragment(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    words = text.split(maxsplit=1)
    first = words[0].strip(".,:;").casefold() if words else ""
    if first in {"my", "your", "their", "his", "her", "our", "its"}:
        return f"{text[:1].casefold()}{text[1:]}"
    return text


def _explicit_deferred_scope(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    patterns = (
        r"\bwhether\s+(?P<scope>[^.;]+?)\s+(?:is|are)\s+in\s+scope\b",
        r"\bwithout\s+claiming\s+(?P<scope>[^.;]+)",
        r"\bwithout\s+including\s+(?P<scope>[^.;]+)",
        r"\bwhile\s+(?P<scope>[^.;]+?)\s+(?:is|are|stay|stays|remain|remains)\s+deferred\b",
        r"\bwhile\s+(?P<scope>[^.;]+?)\s+(?:is|are|stay|stays|remain|remains)\s+out\s+of\s+scope\b",
        r"\b(?:must\s+not|does\s+not|do\s+not|don't|never)\s+claim\s+(?P<scope>[^.;]+)",
        r"\b(?:no|not\s+including|exclude|excluding)\s+(?P<scope>[^.;]+)",
        r"\binto\s+(?P<scope>[^.;]+)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if match is None:
            continue
        scope = _scope_list_label(match.group("scope"))
        if scope:
            return scope
    out_of_scope = re.match(
        r"^(?P<scope>[^.;]+?)\s+(?:is|are|stays?|remains?)\s+(?:out\s+of\s+scope|outside\s+(?:the\s+)?(?:first\s+)?(?:release|proof|scope))\b",
        text,
        flags=re.IGNORECASE,
    )
    if out_of_scope is not None:
        return _scope_list_label(out_of_scope.group("scope"))
    deferred = re.match(
        r"^(?P<scope>[^.;]+?)\s+(?:is|are|stays?|remains?)\s+deferred\b",
        text,
        flags=re.IGNORECASE,
    )
    if deferred is not None:
        return _scope_list_label(deferred.group("scope"))
    return ""


def _looks_like_deferred_component_label(value: str) -> bool:
    text = compact_text(value)
    if not text or word_count(text) > 10:
        return False
    if re.search(
        r"\b(?:avoid|deferred|do\s+not|don't|future|later|must\s+not|never|no|not\s+included|out\s+of\s+scope|outside|whether)\b",
        text,
        flags=re.IGNORECASE,
    ):
        return False
    return not re.search(r"[.;:?!]", text)


def _scope_list_label(value: str) -> str:
    text = compact_text(value).strip(" .")
    if not text:
        return ""
    text = re.split(
        r"\s+(?:before|until|unless|while|when|because|so\s+that)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0].strip(" .")
    text = re.sub(r"^(?:any|all|the|a|an|one)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    if word_count(text) > 10:
        comma_items = [item.strip(" .") for item in re.split(r"\s*,\s*", text) if item.strip(" .")]
        if len(comma_items) > 1:
            selected = comma_items[:2]
            if len(comma_items) > 2:
                selected.append(comma_items[-1])
            text = ", ".join(selected)
    text = _deferred_scope_noun_list(text)
    return _strip_dangling_tail(text)


_DEFERRED_SCOPE_ACTION_LEADS = frozenset(
    {
        "automate", "automates", "connect", "connects", "export", "exports", "import", "imports",
        "notify", "notifies", "receive", "receives", "route", "routes", "send", "sends", "share",
        "shares", "sync", "syncs",
    }
)


def _deferred_scope_noun_list(value: str) -> str:
    parts = re.split(r"\s+\b(and|or)\b\s+", compact_text(value).strip(" ."), flags=re.IGNORECASE)
    if len(parts) < 3:
        return value
    rebuilt = [parts[0].strip(" .")]
    for connector, segment in zip(parts[1::2], parts[2::2]):
        first, separator, rest = segment.strip(" .").partition(" ")
        item = rest.strip(" .") if separator and first.casefold() in _DEFERRED_SCOPE_ACTION_LEADS else segment.strip(" .")
        if item:
            rebuilt.extend([connector.casefold(), item])
    return " ".join(part for part in rebuilt if part).strip(" .")


def _role_or_short_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"(?<!-)\bprimary\b(?!-)", "", text, flags=re.IGNORECASE)
    text = re.split(
        r"\b(?:who|that|where|when|while|with|filling|reading|reviewing|configuring|tracking|using|entering|submitting|following|managing|auditing|approving)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", text).strip(" ,.;:-")


def _strip_dangling_tail(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.-")
    while True:
        previous = text
        words = text.split()
        tail = [word.casefold().strip(" ,;:.-") for word in words[-2:]]
        if tail in (["product", "show"], ["product", "shows"]):
            text = " ".join(words[:-2]).rstrip(" ,;:.-")
        text = strip_confirmed_dangling_tail(text)
        text = _strip_clipped_terminal_action(text)
        text = strip_dangling_word_tail(text, dangling_words=("then",), rstrip_chars=" ,;:.-")
        if text == previous:
            return text


def _strip_clipped_terminal_action(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.-")
    if "," not in text:
        return text
    head, tail = text.rsplit(",", 1)
    token = tail.strip(" ,;:.-").casefold()
    if not token or " " in token:
        return text
    if token in {"assign", "check", "compare", "create", "deduplicate", "export", "import", "record", "resolve", "review", "screen", "submit"}:
        return head.rstrip(" ,;:.-")
    if token.endswith("ing") and len(token) > 5:
        return head.rstrip(" ,;:.-")
    if looks_like_action_clause(f"{token} placeholder") and not looks_like_finite_action(f"{token} placeholder"):
        return head.rstrip(" ,;:.-")
    return text


__all__ = [
    "actor_phrase",
    "brief_first_path",
    "brief_object_label",
    "brief_proof_boundary",
    "brief_story",
    "compact_text",
    "component_description",
    "component_label",
    "component_phrase",
    "deferred_scope_label",
    "diagram_sentence_label",
    "escape_label",
    "flow_label",
    "proof_checkpoint_label",
    "proof_evidence_label",
    "release_proof_label",
    "semantic_proof_checkpoint",
    "semantic_visible_result_label",
    "sentence",
    "short_label",
    "trim",
    "workstream_titles",
]
