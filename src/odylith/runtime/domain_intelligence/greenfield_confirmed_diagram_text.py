"""Text and label model for confirmed greenfield Atlas diagrams."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common import mermaid_text
from odylith.runtime.common.prose_grammar import base_action_clause
from odylith.runtime.common.prose_grammar import finite_action_clause
from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import word_count
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
    text = display_text.strip_inline_markdown_emphasis_tokens(value).replace("`", "")
    text = " ".join(text.strip().split()).rstrip(".")
    if text:
        text = text[:1].upper() + text[1:]
    return f"{text}." if text else ""


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
    text = normalize_proof_boundary_language(text)
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
        if word_count(visible) >= 3:
            return trim(visible, 80)
    graph = semantic_model.get("diagram_event_graph")
    if isinstance(graph, Mapping):
        value = normalize_proof_boundary_language(compact_text(str(graph.get("proof_checkpoint") or "")))
        value = _strip_dangling_tail(value)
        if word_count(value) >= 4:
            return trim(value, 80)
    return ""


def semantic_visible_result_label(semantic_model: Mapping[str, Any] | None) -> str:
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    visible = normalize_visible_result_language(compact_text(str(contract.get("visible_result") or "")))
    return _strip_dangling_tail(visible)


def proof_evidence_label(*, components: list[dict[str, Any]], fallback: str) -> str:
    for component in components:
        label = str(component.get("label", "")).strip()
        if re.search(r"\b(audit|trail|history|evidence|source-backed|version|provenance)\b", label, re.IGNORECASE):
            return f"{label} proof record"
    for component in components:
        label = str(component.get("label", "")).strip()
        if re.search(r"\b(record|log|attachment|source)\b", label, re.IGNORECASE):
            return f"{label} proof record"
    return fallback


def proof_checkpoint_label(value: str) -> str:
    text = normalize_proof_boundary_language(compact_text(value))
    if not text:
        return ""
    clauses = [
        clause.strip(" .")
        for clause in re.split(
            r";\s+|(?<=[.!?])\s+|\s+\band\b\s+|,\s+(?=(?:receive|receives|see|sees|show|shows|view|views|leave|leaves|record|records|review|reviews|return|returns)\b)",
            text,
            flags=re.IGNORECASE,
        )
        if clause.strip(" .")
    ]
    for clause in clauses:
        if word_count(clause) >= 4:
            return trim(clause, 82)
    return ""


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
        "program": f"Establish {label} Program",
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
    first = text.split("—", 1)[0].split(". ", 1)[0].strip(" .:")
    patterns = (
        r"\b(?:primary\s+)?state\s+object\s+is\s+(?:a|an|the)?\s*(?P<label>[^.;:]+?)(?:\s+(?:that|which|who|where|tracks?|records?|stores?|captures?|moves?|starts?)\b|$)",
        r"^(?:a|an|the)\s+(?P<label>[A-Za-z][A-Za-z0-9 _/-]{2,80}?)\s+(?:tracks?|records?|stores?|captures?|moves?|starts?|keeps?)\b",
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
    return _without_ellipsis(mermaid_text.wrap_mermaid_label(text, width=30, max_lines=4, limit=limit))


def escape_label(value: str) -> str:
    return mermaid_text.escape_mermaid_label(value)


def trim(value: str, limit: int) -> str:
    text = compact_text(value)
    if len(text) <= limit:
        return text
    clipped = clip_text_at_word_boundary(text, limit=limit)
    return _balance_label(_strip_dangling_tail(clipped))


def compact_text(value: str) -> str:
    return mermaid_text.clean_mermaid_text(value)


def _component_kind(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    label_text = label.casefold()
    if re.search(r"\b(adapter|connector|integration|provider|import|source)\b", label_text):
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
            r"receives?|produces?|records?|stores?|tracks?|links?|assembles?|derives?|controls?|"
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
    if kind == "adapter":
        return "Reviewers need to see which source supplied the input and what normalized result entered the product"
    if kind == "client":
        return "Reviewers need to see what the user saw, submitted, corrected, or approved and which product state changed after that action"
    if _is_workflow_like(label, subject):
        return "Reviewers need to see each responsibility transfer, failure state, recovery action, and final outcome"
    if _is_record_like(label, subject):
        if re.search(r"\b(?:audit|evidence|provenance|source|trail|version|versioned)\b", f"{label} {subject}", re.IGNORECASE):
            return "Reviewers need to see the versioned state, source evidence, and decisions that depended on this record"
        return "Reviewers need to see the saved state, important inputs, status changes, and decisions that depended on this record"
    if _is_decision_like(label, subject):
        return "Reviewers need to see the inputs, rule version, result, and downstream decision that depended on it"
    return "Reviewers need to see what this boundary receives, produces, records, and makes available next"


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
        return f"The result on {text[:1].lower()}{text[1:]}"
    return text


def _without_ellipsis(value: str) -> str:
    return str(value or "").replace("…", "").replace("...", "").rstrip(" ,;:")


def _role_or_short_label(value: str) -> str:
    text = str(value or "").split("—", 1)[0].split(":", 1)[0].strip()
    text = text.replace("(", " ").replace(")", " ")
    text = re.sub(r"\bprimary\b", "", text, flags=re.IGNORECASE)
    text = re.split(
        r"\b(?:who|that|where|when|while|with|filling|reading|reviewing|configuring|tracking|using|entering|submitting|following|managing|auditing|approving)\b",
        text,
        maxsplit=1,
        flags=re.IGNORECASE,
    )[0]
    return re.sub(r"\s+", " ", text).strip(" ,.;:-")


def _balance_label(value: str) -> str:
    text = compact_text(value).strip(" ,;:.")
    if text.count("(") > text.count(")"):
        text = text.rsplit("(", 1)[0].rstrip(" ,;:.")
    if text.count("[") > text.count("]"):
        text = text.rsplit("[", 1)[0].rstrip(" ,;:.")
    return text


def _strip_dangling_tail(value: str) -> str:
    text = compact_text(value).rstrip(" ,;:.")
    while True:
        cleaned = re.sub(
            r"\b(?:a|an|and|as|at|because|by|can|for|from|if|in|into|its|lets|must|of|on|or|should|that|the|their|this|through|tied|to|when|while|with|without)$",
            "",
            text,
            flags=re.IGNORECASE,
        ).rstrip(" ,;:.")
        if cleaned == text:
            return cleaned
        text = cleaned


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
    "escape_label",
    "flow_label",
    "proof_checkpoint_label",
    "proof_evidence_label",
    "semantic_proof_checkpoint",
    "semantic_visible_result_label",
    "sentence",
    "short_label",
    "trim",
    "workstream_titles",
]
