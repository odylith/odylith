"""Semantic drift checks for post-confirm greenfield package artifacts."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import term_frequencies
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import word_count


def contrastive_domain_drift_issues(proposal: Mapping[str, Any], semantic: Mapping[str, Any]) -> list[str]:
    """Flag repeated high-signal terms not grounded in this intent or model."""

    intent_signature_text = _intent_signature_text(proposal)
    component_signature_text = _component_signature_text(proposal)
    signature_terms = _term_signature(intent_signature_text, minimum=4)
    ontology = semantic.get("domain_ontology") if isinstance(semantic.get("domain_ontology"), Mapping) else {}
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    signature_terms.update(_term_signature(" ".join(text_values(ontology)), minimum=4))
    signature_terms.update(_term_signature(" ".join(text_values(first_path)), minimum=4))
    signature_terms.update(_term_signature(component_signature_text, minimum=4))
    signature_terms.update(_grounded_equivalent_terms(f"{intent_signature_text} {component_signature_text}", signature_terms))
    generated_text = _generated_artifact_text(proposal)
    generated_counts: dict[str, int] = {}
    for term, count in term_frequencies(
        _signature_text(generated_text),
        minimum=5,
        stopwords=(*_CONTRASTIVE_GENERIC_TERMS, *_CONTRASTIVE_STOPWORDS),
    ).items():
        if term in _CONTRASTIVE_GENERIC_TERMS:
            continue
        if term in signature_terms:
            continue
        generated_counts[term] = count
    leaked = sorted(
        term
        for term, count in generated_counts.items()
        if count >= _CONTRASTIVE_REPEAT_THRESHOLD and len(term) >= _CONTRASTIVE_MIN_UNGROUNDED_TERM_LENGTH
    )
    if leaked:
        return [
            "contrastive domain drift: generated artifact terms are not grounded in accepted intent: "
            f"{', '.join(leaked[:8])}"
        ]
    return []


def semantic_repetition_issues(proposal: Mapping[str, Any]) -> list[str]:
    """Cluster near-duplicate public sentences across generated surfaces."""

    sentences = _generated_artifact_sentences(proposal)
    signatures: list[tuple[str, set[str]]] = []
    for sentence in sentences:
        signature = _sentence_signature(sentence)
        if len(signature) >= 8:
            signatures.append((sentence, signature))
    if len(signatures) < _REPETITION_CLUSTER_SIZE:
        return []
    for left_index, (sentence, left_terms) in enumerate(signatures):
        near_duplicate_count = 1
        for right_index in range(left_index + 1, len(signatures)):
            right_terms = signatures[right_index][1]
            overlap = len(left_terms & right_terms)
            if overlap < _REPETITION_MIN_SHARED_TERMS:
                continue
            union_size = len(left_terms | right_terms)
            similarity = overlap / max(1, union_size)
            if similarity >= _REPETITION_SIMILARITY_THRESHOLD:
                near_duplicate_count += 1
        if near_duplicate_count >= _REPETITION_CLUSTER_SIZE:
            sample = clean_text(sentence)
            return [
                "semantic repetition: generated artifacts repeat the same sentence shape across "
                f"{near_duplicate_count} surfaces; sample `{sample[:140]}`"
            ]
    return []


def semantic_overlap_ratio(source: str, target: str) -> float:
    """Return how much of the source semantic signature appears in the target."""

    source_terms = _term_signature(source, minimum=5)
    if not source_terms:
        return 1.0
    target_terms = _term_signature(target, minimum=5)
    if not target_terms:
        return 0.0
    return len(source_terms & target_terms) / max(1, len(source_terms))


def _generated_artifact_sentences(proposal: Mapping[str, Any]) -> list[str]:
    sentences: list[str] = []
    for text in _generated_repetition_value_texts(proposal):
        for sentence in re.split(r"(?<=[.!?])\s+|\n+|;\s+", text):
            cleaned = clean_text(sentence).strip(" -•")
            if word_count(cleaned) >= 10:
                sentences.append(cleaned)
    return sentences


def _sentence_signature(value: str) -> set[str]:
    return set(
        ordered_terms(
            value,
            minimum=4,
            stopwords=(*_CONTRASTIVE_GENERIC_TERMS, *_CONTRASTIVE_STOPWORDS),
        )
    )


def _intent_signature_text(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    rows = [
        intent.get("title"),
        intent.get("product_story"),
        intent.get("state_object"),
        intent.get("first_path"),
        intent.get("proof_boundary"),
        *text_values(intent.get("human_actors")),
        *text_values(intent.get("external_systems")),
        *text_values(intent.get("internal_systems")),
        *text_values(intent.get("critical_assumptions")),
        *text_values(intent.get("ambiguities")),
        *text_values(intent.get("non_goals")),
    ]
    return " ".join(clean_text(row) for row in rows if clean_text(row))


def _component_signature_text(proposal: Mapping[str, Any]) -> str:
    rows: list[Any] = []
    for row in mapping_rows(proposal.get("components")):
        rows.extend([row.get("label"), row.get("source_system_description")])
    return " ".join(clean_text(row) for row in rows if clean_text(row))


def _generated_artifact_text(proposal: Mapping[str, Any]) -> str:
    return " ".join(_generated_artifact_value_texts(proposal))


def _generated_artifact_value_texts(proposal: Mapping[str, Any]) -> list[str]:
    rows: list[Any] = []
    for row in mapping_rows(proposal.get("backlog")):
        rows.extend(
            [
                row.get("title"),
                row.get("problem"),
                row.get("opportunity"),
                row.get("product_view"),
                row.get("recommended_first_slice"),
                row.get("success_metrics"),
                row.get("validation"),
            ]
        )
    for row in mapping_rows(proposal.get("components")):
        rows.extend([row.get("label"), row.get("source_system_description"), row.get("component_contract")])
    for row in mapping_rows(proposal.get("diagrams")):
        rows.extend([row.get("title"), row.get("summary"), row.get("read_guide"), row.get("components")])
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    rows.extend([release_plan.get("strategy"), release_plan.get("promotion_criteria")])
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    rows.extend([brief.get("story"), brief.get("first_path"), brief.get("proof")])
    return [clean_text(value) for item in rows for value in text_values(item) if clean_text(value)]


def _generated_repetition_value_texts(proposal: Mapping[str, Any]) -> list[str]:
    rows: list[Any] = []
    for row in mapping_rows(proposal.get("backlog")):
        rows.extend(
            [
                row.get("problem"),
                row.get("opportunity"),
                row.get("product_view"),
                row.get("recommended_first_slice"),
                row.get("success_metrics"),
                row.get("validation"),
            ]
        )
    for row in mapping_rows(proposal.get("components")):
        rows.extend([row.get("source_system_description"), row.get("component_contract")])
    for row in mapping_rows(proposal.get("diagrams")):
        rows.extend([row.get("summary"), row.get("read_guide")])
    release_plan = proposal.get("release_plan") if isinstance(proposal.get("release_plan"), Mapping) else {}
    rows.extend([release_plan.get("strategy"), release_plan.get("promotion_criteria")])
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    rows.extend([brief.get("story"), brief.get("first_path"), brief.get("proof")])
    return [clean_text(value) for item in rows for value in text_values(item) if clean_text(value)]


def _term_signature(value: str, *, minimum: int) -> set[str]:
    return set(
        ordered_terms(
            _signature_text(value),
            minimum=minimum,
            stopwords=(*_CONTRASTIVE_GENERIC_TERMS, *_CONTRASTIVE_STOPWORDS),
        )
    )


def _grounded_equivalent_terms(source_text: str, signature_terms: set[str]) -> set[str]:
    text = _signature_text(source_text)
    terms: set[str] = set()
    if signature_terms & {"recommend", "recommended", "suggest", "suggested"} or re.search(
        r"\b(?:recommend|recommended|suggest|suggested)\b",
        text,
    ):
        terms.add("recommendation")
    if signature_terms & {"propose", "proposed"} or re.search(r"\b(?:propose|proposed)\b", text):
        terms.add("proposal")
    return terms


def _signature_text(value: str) -> str:
    return clean_text(value).casefold().replace("-", " ").replace("_", " ")


_CONTRASTIVE_GENERIC_TERMS = {
    "accepted",
    "action",
    "access",
    "active",
    "adjacent",
    "against",
    "actor",
    "artifact",
    "assertion",
    "approval",
    "approved",
    "authorized",
    "assigned",
    "automation",
    "avoided",
    "backlog",
    "before",
    "behavior",
    "blocked",
    "blocker",
    "boundary",
    "build",
    "built",
    "candidate",
    "calculate",
    "calculated",
    "calculation",
    "central",
    "changed",
    "classification",
    "claim",
    "command",
    "component",
    "complete",
    "completed",
    "completion",
    "context",
    "contract",
    "correction",
    "created",
    "current",
    "decision",
    "deferred",
    "dependency",
    "depend",
    "depended",
    "depends",
    "description",
    "derived",
    "detail",
    "details",
    "diagram",
    "domain",
    "downstream",
    "external",
    "evidence",
    "explanation",
    "failure",
    "final",
    "first",
    "forbidden",
    "follow",
    "gate",
    "generic",
    "governance",
    "greenfield",
    "handoff",
    "history",
    "identity",
    "implementation",
    "implement",
    "implemented",
    "implements",
    "incomplete",
    "input",
    "inside",
    "interface",
    "interfaces",
    "internal",
    "intent",
    "invalid",
    "issue",
    "local",
    "marker",
    "missing",
    "mutation",
    "named",
    "output",
    "outside",
    "own",
    "owned",
    "owner",
    "ownership",
    "owns",
    "package",
    "planned",
    "policy",
    "privacy",
    "proof",
    "proposal",
    "produce",
    "produced",
    "product",
    "rationale",
    "ready",
    "readiness",
    "record",
    "recovery",
    "refused",
    "release",
    "released",
    "require",
    "required",
    "requirement",
    "responsibility",
    "rendered",
    "replay",
    "request",
    "representative",
    "result",
    "review",
    "reviewable",
    "reviewer",
    "runtime",
    "scope",
    "sibling",
    "signal",
    "source",
    "state",
    "status",
    "stream",
    "stale",
    "success",
    "successful",
    "system",
    "target",
    "technical",
    "trace",
    "traceable",
    "transition",
    "truth",
    "upstream",
    "understand",
    "understandable",
    "validation",
    "validated",
    "valid",
    "versioned",
    "visible",
    "workstream",
    "wrong",
}

_CONTRASTIVE_REPEAT_THRESHOLD = 8
_CONTRASTIVE_MIN_UNGROUNDED_TERM_LENGTH = 10
_REPETITION_CLUSTER_SIZE = 6
_REPETITION_SIMILARITY_THRESHOLD = 0.88
_REPETITION_MIN_SHARED_TERMS = 8

_CONTRASTIVE_STOPWORDS = {
    "about",
    "after",
    "again",
    "against",
    "among",
    "around",
    "because",
    "before",
    "being",
    "between",
    "could",
    "every",
    "from",
    "their",
    "there",
    "these",
    "those",
    "through",
    "until",
    "where",
    "which",
    "while",
    "within",
    "without",
    "would",
}


__all__ = [
    "contrastive_domain_drift_issues",
    "semantic_repetition_issues",
]
