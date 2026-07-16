"""Generic evaluation-depth semantics for research, model, and simulation requests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_confirmed_text import title_case_text
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_requirement_control_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_requirement_control_step
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import is_release_evidence_requirement
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import dedupe_adjacent_words
from odylith.runtime.domain_intelligence.greenfield_text import word_count


_EVALUATION_SIGNAL_TERMS = frozenset(
    """
    algorithm baseline benchmark calibration dataset experiment
    experimental inference lab measurement method metric model modeling prediction predictive protocol research researcher
    scientific simulate simulation simulator solver tolerance uncertainty variable
    """.split()
)
_EVALUATION_STRONG_TERMS = _EVALUATION_SIGNAL_TERMS - {"benchmark", "research", "researcher"}
_PRODUCT_REQUEST_VERBS = frozenset(
    {
        "build",
        "create",
        "design",
        "draft",
        "generate",
        "make",
        "plan",
        "propose",
        "scaffold",
        "write",
    }
)
_CONTEXTUAL_EVIDENCE_CONNECTORS = frozenset({"with", "including", "featuring"})
_CONTEXTUAL_EVIDENCE_ACTION_TOKENS = frozenset({"can", "must", "should", "that", "to", "where", "who", "will"})
_EVALUATION_CONTEXT_TERMS = frozenset(
    """
    baseline benchmark calibration confidence dataset experiment experimental inference lab measurement method metric model
    modeling prediction predictive protocol research researcher scientific simulate simulation simulator solver tolerance uncertainty variable
    """.split()
)
_MODEL_ACTION_TERMS = frozenset(
    """
    analyze analyzes classify classifies estimate estimates evaluate evaluates infer infers modeling predict predicts
    simulate simulates solve solves
    """.split()
)
_GENERIC_MODEL_TITLES = frozenset({"ai model", "ai-model", "ml model", "model", "simulation model"})
_TRAILING_BOUNDARIES = frozenset(
    {"after", "before", "but", "using", "while", "when", "where", "which", "who", "without"}
)


@dataclass(frozen=True)
class EvaluationSemantics:
    schema_version: str
    applicability: str
    focus: str
    observed_quantities: tuple[str, ...]
    evidence_sources: tuple[str, ...]
    source_anchors: tuple[str, ...]
    method_or_protocol: str
    reference_or_baseline: str
    uncertainty_or_tolerance: str
    reproducibility: str
    excluded_claims: tuple[str, ...]


@dataclass(frozen=True)
class RecoveredEvaluationContext:
    title_source: str = ""
    first_path_source: str = ""
    story: str = ""
    state_object: str = ""
    proof_boundary: str = ""
    internal_systems: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    ambiguities: tuple[str, ...] = ()
    success_metrics: tuple[str, ...] = ()


def evaluation_semantics_for_texts(
    *,
    title: str,
    state_object: str,
    first_path: str,
    proof_boundary: str,
    prompt: str = "",
    source_anchors: Sequence[str] = (),
) -> EvaluationSemantics | None:
    """Return an optional generic evidence/evaluation IR for R&D-heavy prompts."""

    anchors = evidence_anchor_phrases(prompt, source_anchors=source_anchors)
    source = " ".join(clean_text(value) for value in (prompt, title, state_object, first_path, proof_boundary, " ".join(anchors)))
    if not source or not evaluation_depth_required(source):
        return None
    focus = evaluation_focus_label(source, fallback=title or "evaluation result")
    focus_ref = _lower_focus(focus)
    anchor_summary = _anchor_summary(anchors)
    return EvaluationSemantics(
        schema_version="odylith.greenfield.evaluation_semantics.v1",
        applicability="evidence_backed_model_or_research_evaluation",
        focus=focus,
        observed_quantities=_unique(
            (
                *anchors[:4],
                f"{focus_ref} inputs",
                f"{focus_ref} outputs",
                "reviewable uncertainty or confidence",
            )
        ),
        evidence_sources=_unique(
            (
                *((f"prompt-grounded evidence anchors: {anchor_summary}",) if anchor_summary else ()),
                "source data or observation provenance",
                "evaluation context and constraints",
                "saved run record",
            )
        ),
        source_anchors=anchors,
        method_or_protocol="method, protocol, model, solver, rule, or analysis version used for the accepted run",
        reference_or_baseline="baseline, reference, fixture, expected range, or comparison evidence when the result is reviewed",
        uncertainty_or_tolerance="uncertainty, confidence, tolerance, calibration, or limitation boundary visible with the result",
        reproducibility="same inputs, context, method version, and parameters can replay the accepted result",
        excluded_claims=(
            "unproven scientific truth",
            "broader model performance beyond the accepted evidence",
            "production, clinical, safety, or regulatory authority without separate proof",
        ),
    )


def recovered_evaluation_context(*, source: str, title_source: str, first_path_source: str) -> RecoveredEvaluationContext:
    """Return richer recovered confirmation text for model/research prompts."""

    source_text = clean_text(source)
    if not _evaluation_recovery_needed(
        source=source_text,
        title_source=title_source,
        first_path_source=first_path_source,
    ):
        return RecoveredEvaluationContext()
    focus_seed = _drop_generic_title_wrapper(title_source) or _drop_generic_title_wrapper(first_path_source)
    focus = (
        evaluation_focus_label(focus_seed, fallback="")
        if focus_seed
        else evaluation_focus_label(source_text, fallback=title_source or first_path_source)
    )
    if word_count(focus) < 2:
        focus = evaluation_focus_label(" ".join([first_path_source, title_source]), fallback=title_source)
    if word_count(focus) < 2:
        return RecoveredEvaluationContext()
    title = _evaluation_title_source(focus, existing=title_source)
    focus_ref = _lower_focus(focus)
    recovered_first_path = (
        f"A researcher provides source data, defines the evaluation context and target, runs the model or simulation, "
        f"reviews the {focus_ref} result with uncertainty and comparison evidence, and saves a reproducible run record."
    )
    first_path = _preserved_evaluation_first_path(first_path_source) or recovered_first_path
    story = (
        f"{title} helps researchers complete a bounded {focus_ref} evaluation from source evidence to a reviewable result. "
        "It keeps inputs, context, method version, assumptions, uncertainty, comparison evidence, and excluded claims visible "
        "so the result can be trusted without overstating what the model proves."
    )
    state = (
        f"A {focus_ref} run record tracks source data, domain context, variables or parameters, method or model version, "
        "baseline or reference comparison, predicted or simulated output, uncertainty or confidence, validation status, "
        "review notes, and reproducibility evidence."
    )
    proof = (
        f"Release 0.0.1 succeeds when a researcher can complete one bounded {focus_ref} run, review inputs, method version, "
        "baseline comparison, uncertainty or tolerance, and reproduce the saved result. It must not claim scientific truth, "
        "production validity, clinical or safety authority, or broader model performance beyond the accepted proof evidence."
    )
    return RecoveredEvaluationContext(
        title_source=title,
        first_path_source=first_path,
        story=story,
        state_object=state,
        proof_boundary=proof,
        internal_systems=(
            f"{title} Evidence Intake — captures source data, provenance, evaluation context, variables, and constraints for each run",
            f"{title} Method Execution Record — records method or model version, parameters, assumptions, and run status",
            f"{title} Review and Reproducibility Workspace — shows outputs, uncertainty, baseline comparison, review notes, and replay evidence",
        ),
        assumptions=(
            "Release 0.0.1 proves one bounded evaluation path before broader automation, integrations, or production authority.",
            "The first release treats model or method outputs as evidence-backed estimates, not final truth.",
        ),
        ambiguities=(
            "Exact data sources, reference baselines, evaluation metrics, and tolerance thresholds can be refined after the first proof path is accepted.",
            "Any production, clinical, safety, compliance, or regulatory claim needs separate validation beyond this first release.",
        ),
        success_metrics=(
            "A researcher can complete the accepted evaluation path and see the reviewable result with input provenance.",
            "The result names method or model version, variables or parameters, baseline comparison, and uncertainty or tolerance.",
            "A saved run can be reproduced from the same inputs, context, method version, and review evidence.",
        ),
    )


def evaluation_depth_required(value: Any) -> bool:
    tokens = {_word_key(word) for word in clean_text(value).replace("/", " ").split()}
    signals = tokens & _EVALUATION_SIGNAL_TERMS
    if len(signals) >= 2 and signals & _EVALUATION_STRONG_TERMS:
        return True
    return bool(tokens & {"model", "prediction", "predictive", "simulate", "simulation", "simulator", "solver"} and tokens & _EVALUATION_CONTEXT_TERMS)


def evidence_anchor_phrases(value: Any, *, source_anchors: Sequence[str] = ()) -> tuple[str, ...]:
    """Return prompt-grounded evidence phrases that must survive projection."""

    rows: list[str] = []
    for source in source_anchors:
        normalized = _normalize_anchor(source)
        if _meaningful_anchor(normalized):
            rows.append(normalized)
    for sentence in _sentences(value):
        if contains_word_sense_metadata_clause(sentence):
            continue
        for anchor in (
            *_contextual_product_evidence_anchors(sentence),
            *_explicit_evidence_anchors(sentence),
            *_contextual_difference_anchors(sentence),
            *_preservation_list_anchors(sentence),
        ):
            normalized = _normalize_anchor(anchor)
            if _meaningful_anchor(normalized):
                rows.append(normalized)
        if not (
            is_requirement_control_step(sentence)
            or contains_requirement_control_clause(sentence)
            or is_release_evidence_requirement(sentence)
        ):
            continue
        tail = _requirement_tail(sentence)
        if not tail:
            continue
        for anchor in _anchor_list_items(tail):
            normalized = _normalize_anchor(anchor)
            if _meaningful_anchor(normalized):
                rows.append(normalized)
    return tuple(dict.fromkeys(rows))[:12]


def _contextual_product_evidence_anchors(value: str) -> tuple[str, ...]:
    """Keep concise setup nouns without turning setup prose into the first path."""

    text = clean_text(value).strip(" .")
    words = text.split()
    command_led = bool(words and _word_key(words[0]) in _PRODUCT_REQUEST_VERBS)
    for match in re.finditer(r"\b(with|including|featuring)\b", text, flags=re.IGNORECASE):
        if _word_key(match.group(1)) not in _CONTEXTUAL_EVIDENCE_CONNECTORS:
            continue
        tail = text[match.end() :]
        anchors = _contextual_difference_anchors(tail) if not command_led else _anchor_list_items(tail)
        if not anchors and command_led:
            anchors = _anchor_list_items(tail)
        if not anchors:
            continue
        return tuple(
            anchor
            for anchor in anchors
            if not ({_word_key(word) for word in anchor.split()} & _CONTEXTUAL_EVIDENCE_ACTION_TOKENS)
            and not looks_like_finite_action(anchor)
        )
    return ()


def _contextual_difference_anchors(value: str) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    match = re.search(
        r"\b(?:whether\s+)?differences?\s+in\s+(?P<items>.+?)\s+"
        r"(?:prevent|prevents|block|blocks|change|changes|affect|affects)\b",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ()
    return tuple(
        item.strip(" .")
        for item in re.split(r"\s+(?:and|or)\s+", match.group("items"), flags=re.IGNORECASE)
        if item.strip(" .")
    )


def _explicit_evidence_anchors(value: str) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    match = re.search(
        r"\b(?:keep|preserve|retain)\s+(?P<items>.+?)\s+as\s+evidence\b",
        text,
        flags=re.IGNORECASE,
    )
    return _anchor_list_items(match.group("items")) if match else ()


def _preservation_list_anchors(value: str) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    match = re.search(
        r"\b(?:keep|preserve|separate|distinguish)\s+(?P<items>.+?)\s+"
        r"(?:distinct|separate|separately)\b",
        text,
        flags=re.IGNORECASE,
    )
    if match and re.search(r"\bas\s+evidence\b", match.group("items"), flags=re.IGNORECASE):
        return ()
    return _anchor_list_items(match.group("items")) if match else ()


def _evaluation_recovery_needed(*, source: str, title_source: str, first_path_source: str) -> bool:
    text = " ".join(clean_text(value) for value in (source, title_source, first_path_source))
    tokens = {_word_key(word) for word in text.replace("/", " ").split()}
    if not (tokens & {"model", "predict", "prediction", "simulate", "simulation"}):
        return False
    raw_title = clean_text(title_source).strip(" .")
    title = _drop_generic_title_wrapper(raw_title).casefold()
    first_path = clean_text(first_path_source).casefold().strip(" .")
    if title in _GENERIC_MODEL_TITLES:
        return True
    if raw_title and title and title != raw_title.casefold() and word_count(title) >= 2:
        return True
    path_title = _drop_generic_title_wrapper(first_path)
    if path_title and path_title != first_path and word_count(path_title) >= 2:
        return True
    if re.match(
        r"^(?:building|creating|designing|drafting|generating|making|planning|proposing|scaffolding|writing)\s+"
        r"(?:a|an|the)?\s*(?:ai[- ]?model|ml[- ]?model|model|simulation|simulator)\b",
        first_path,
    ):
        return True
    return bool(
        re.match(r"^(?:a|an|the)?\s*(?:ai[- ]?model|ml[- ]?model|model|simulation|simulator)\b", first_path)
        and re.search(r"\b(?:simulate|simulates|predict|predicts)\b", first_path)
    ) or bool(evaluation_depth_required(text) and len(first_path_model(first_path_source).steps) >= 2)


def _anchor_summary(values: Sequence[str]) -> str:
    rows = [dedupe_adjacent_words(value).strip(" .") for value in values if dedupe_adjacent_words(value).strip(" .")]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    return "; ".join(rows)


def _requirement_tail(value: str) -> str:
    text = clean_text(value).strip(" .")
    for match in re.finditer(r"[A-Za-z][A-Za-z0-9'-]*", text):
        token = _word_key(match.group(0))
        if token in {"preserve", "include", "includes", "capture", "captures", "show", "shows", "name", "names", "record", "records"}:
            return text[match.end() :].strip(" .")
    return ""


def _anchor_list_items(value: str) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    if not text:
        return ()
    text = re.sub(r"\b(?:as well as|plus)\b", ",", text, flags=re.IGNORECASE)
    text = re.sub(r"\b(?:before|so that|while)\b.+$", "", text, flags=re.IGNORECASE).strip(" .")
    chunks: list[str] = []
    for part in re.split(r"\s*[,;]\s*", text):
        part = part.strip(" .")
        if not part:
            continue
        if "," not in text and re.search(r"\s+and\s+", part, flags=re.IGNORECASE):
            chunks.extend(row.strip(" .") for row in re.split(r"\s+and\s+", part, flags=re.IGNORECASE) if row.strip(" ."))
        else:
            chunks.append(part)
    result: list[str] = []
    for chunk in chunks:
        cleaned = re.sub(r"^(?:and|or)\s+", "", chunk, flags=re.IGNORECASE).strip(" .")
        if cleaned:
            result.append(cleaned)
    return tuple(result)


def _normalize_anchor(value: Any) -> str:
    text = dedupe_adjacent_words(value).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:the|a|an|this|that)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(
        r"^(?:avoid|capture|captures|include|includes|make|name|names|preserve|record|records|show|shows)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
    text = re.sub(r"^(?:unsupported\s+)?operational\s+claims?\b", "unsupported operational claims", text, flags=re.IGNORECASE)
    return text


def _meaningful_anchor(value: str) -> bool:
    text = dedupe_adjacent_words(value).strip(" .")
    if not text:
        return False
    words = [_word_key(word) for word in re.split(r"[-/\s]+", text)]
    words = [word for word in words if word]
    if len(words) < 2 or len(words) > 9:
        return False
    generic = {
        "architecture",
        "artifact",
        "domain",
        "engineer",
        "engineering",
        "expert",
        "product",
        "project",
        "review",
    }
    return bool(set(words) - generic)


def _sentences(value: Any) -> tuple[str, ...]:
    text = clean_text(value).strip(" .")
    if not text:
        return ()
    return tuple(row.strip(" .") for row in re.split(r"(?<=[.!?])\s+", text) if row.strip(" ."))


def _unique(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(dedupe_adjacent_words(value).strip(" .") for value in values if dedupe_adjacent_words(value).strip(" .")))


def _preserved_evaluation_first_path(value: str) -> str:
    text = clean_text(value).strip(" .")
    if word_count(text) < 10:
        return ""
    if re.match(
        r"^[A-Za-z][A-Za-z0-9 /&'()-]{1,80}\s+who\s+",
        text,
        flags=re.IGNORECASE,
    ):
        return text
    model = first_path_model(text)
    if len(model.steps) < 2:
        return ""
    if _drop_generic_title_wrapper(text).casefold() in _GENERIC_MODEL_TITLES:
        return ""
    return text


def evaluation_focus_label(value: Any, *, fallback: str = "") -> str:
    text = clean_text(value).strip(" .")
    action_tail = _focus_after_model_action(text)
    candidate = action_tail or _remove_generic_model_title(fallback) or _remove_generic_model_title(text)
    candidate = _clean_focus(candidate)
    return candidate or clean_text(fallback).strip(" .") or "evaluation result"


def _evaluation_title_source(focus: str, *, existing: str) -> str:
    current = _drop_generic_title_wrapper(clean_text(existing).strip(" ."))
    if current and current.casefold() not in _GENERIC_MODEL_TITLES and word_count(current) >= 3:
        return title_case_text(current)
    label = title_case_text(_clean_focus(focus))
    if not label:
        return "Evaluation Model Workspace"
    lowered = label.casefold()
    if lowered.endswith((" workspace", " workbench", " lab", " notebook", " model", " simulator")):
        return label
    return f"{label} Model Workspace"


def _drop_generic_title_wrapper(value: str) -> str:
    text = clean_text(value).strip(" .")
    stripped = re.sub(
        r"^(?:building|creating|designing|drafting|generating|making|planning|proposing|scaffolding|writing)\s+",
        "",
        text,
        flags=re.IGNORECASE,
    ).strip(" .")
    stripped = re.sub(r"^(?:a|an|the)\s+", "", stripped, flags=re.IGNORECASE).strip(" .")
    return "" if stripped.casefold() in _GENERIC_MODEL_TITLES else stripped


def _focus_after_model_action(value: str) -> str:
    words = [word for word in clean_text(value).replace("/", " ").split() if word.strip("()[]{}\"'")]
    lowered = [_word_key(word) for word in words]
    for index, token in enumerate(lowered[:-1]):
        if token not in _MODEL_ACTION_TERMS:
            continue
        tail = _bounded_tail(words[index + 1 :])
        if word_count(tail) >= 2:
            return tail
    return ""


def _bounded_tail(words: list[str]) -> str:
    kept: list[str] = []
    for word in words:
        token = _word_key(word)
        if token in _TRAILING_BOUNDARIES:
            break
        terminal = str(word).rstrip(")]}\"'").endswith((".", "!", "?"))
        if token in {"and", "or", "then"} and len(kept) >= 3:
            break
        kept.append(str(word).strip("()[]{}\"'.,:;"))
        if terminal:
            break
        if len(kept) >= 7:
            break
    return " ".join(kept).strip(" .")


def _remove_generic_model_title(value: str) -> str:
    text = clean_text(value).strip(" .")
    lowered = text.casefold()
    for prefix in ("ai model", "ai-model", "ml model", "model"):
        if lowered.startswith(prefix + " "):
            return text[len(prefix) :].strip(" .")
    return text if lowered not in _GENERIC_MODEL_TITLES else ""


def _clean_focus(value: str) -> str:
    text = clean_text(value).strip(" .")
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    text = re.sub(r"\b(?:workspace|product|proposal|project)$", "", text, flags=re.IGNORECASE).strip(" .")
    return text


def _lower_focus(value: str) -> str:
    text = _clean_focus(value)
    words = text.split()
    if not words:
        return text
    return " ".join(word if word.isupper() and len(word) <= 6 else word.casefold() for word in words)


def _word_key(value: str) -> str:
    token = str(value or "").casefold().strip(".,:;()[]{}\"'")
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("s") and len(token) > 4:
        return token[:-1]
    return token


__all__ = [
    "EvaluationSemantics",
    "RecoveredEvaluationContext",
    "evidence_anchor_phrases",
    "evaluation_depth_required",
    "evaluation_focus_label",
    "evaluation_semantics_for_texts",
    "recovered_evaluation_context",
]
