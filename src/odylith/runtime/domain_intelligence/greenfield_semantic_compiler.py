"""Semantic compiler checks for confirmed greenfield generation.

The compiler separates product-result facts from proof-boundary facts before
renderers project Radar, Registry, Atlas, and Compass artifacts. That boundary
is the invariant that keeps a release proof sentence from becoming the user
visible result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clean_first_path_text
from odylith.runtime.domain_intelligence.greenfield_first_path_common import clip_first_path_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_common import lowercase_leading_article
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    action_chain_fragment,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    actor_signature,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    nominal_visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_fragments import (
    visible_result_object,
)
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_visible_result_language
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import word_count

SEMANTIC_COMPILER_VERSION = "odylith.greenfield.semantic_compiler.v1"


@dataclass(frozen=True)
class GreenfieldSemanticCandidate:
    role: str
    text: str
    source_kind: str
    source_path: str
    confidence: float
    provenance: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldSemanticCounterexample:
    code: str
    path: str
    message: str
    severity: str
    repair_hint: str

    def to_issue(self) -> str:
        return f"GreenfieldSemanticCompiler {self.path}: {self.message}"

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class GreenfieldSemanticCompilerReport:
    version: str
    status: str
    visible_result: GreenfieldSemanticCandidate
    counterexamples: tuple[GreenfieldSemanticCounterexample, ...]
    quality_scores: Mapping[str, float]

    @property
    def passed(self) -> bool:
        return self.status == "passed"

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "status": self.status,
            "visible_result": self.visible_result.to_dict(),
            "counterexamples": [item.to_dict() for item in self.counterexamples],
            "quality_scores": dict(self.quality_scores),
        }


def select_visible_result_candidate(
    first_path: Any,
    *,
    proof_boundary: Any = "",
    model: FirstPathModel | None = None,
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> GreenfieldSemanticCandidate:
    """Choose the product result from first-path events before proof text."""

    path_model = model or first_path_model(first_path)
    proof = clean_first_path_text(proof_boundary)
    candidates: list[GreenfieldSemanticCandidate] = []
    proof_candidate: GreenfieldSemanticCandidate | None = None
    visible = _product_result_from_visible_outcome(path_model.visible_outcome)
    if visible:
        candidates.append(
            _candidate(
                text=visible,
                source_kind="first_path_event",
                source_path="first_path.visible_result",
                confidence=_candidate_confidence(visible, source_kind="first_path_event")
                + _terminal_visible_outcome_bonus(visible),
                provenance=(path_model.visible_outcome,),
                limit=limit,
            )
        )
    for index, step in reversed(tuple(enumerate(path_model.steps, start=1))):
        result = _product_result_from_visible_outcome(step)
        if not result:
            continue
        candidates.append(
            _candidate(
                text=result,
                source_kind="first_path_event",
                source_path=f"first_path.events.{index}",
                confidence=_step_visible_result_confidence(result, step=step, path_model=path_model),
                provenance=(step,),
                limit=limit,
            )
        )
    proof_result = _product_result_from_proof_boundary(proof)
    if proof_result:
        proof_candidate = _candidate(
            text=proof_result,
            source_kind="proof_boundary",
            source_path="proof_boundary",
            confidence=_candidate_confidence(proof_result, source_kind="proof_boundary"),
            provenance=(proof,),
            limit=limit,
        )
        candidates.append(proof_candidate)
    accepted = [candidate for candidate in candidates if _candidate_is_product_result(candidate.text)]
    if accepted:
        accepted.sort(key=lambda item: item.confidence, reverse=True)
        best = accepted[0]
        if proof_candidate and _proof_candidate_refines_pronoun_result(best, proof_candidate, path_model=path_model):
            return _refined_pronoun_result_candidate(best, proof_candidate)
        return best
    return _candidate(
        text=clean_first_path_text(fallback),
        source_kind="fallback",
        source_path="fallback",
        confidence=0.1,
        provenance=(),
        limit=limit,
    )


def select_visible_result_text(
    first_path: Any,
    *,
    proof_boundary: Any = "",
    model: FirstPathModel | None = None,
    fallback: str = "the promised user-visible result",
    limit: int = 220,
) -> str:
    return select_visible_result_candidate(
        first_path,
        proof_boundary=proof_boundary,
        model=model,
        fallback=fallback,
        limit=limit,
    ).text


def compile_greenfield_semantics(proposal: Mapping[str, Any]) -> GreenfieldSemanticCompilerReport:
    intent = _intent_mapping(proposal)
    semantic = proposal.get("semantic_model") if isinstance(proposal.get("semantic_model"), Mapping) else {}
    first_path = _first_nonempty(intent.get("first_path"), _project_brief_value(proposal, "first_path"))
    proof = _first_nonempty(intent.get("proof_boundary"), _project_brief_value(proposal, "proof"))
    visible = select_visible_result_candidate(first_path, proof_boundary=proof)
    counterexamples: list[GreenfieldSemanticCounterexample] = []
    counterexamples.extend(_visible_result_counterexamples(semantic, visible, proof=proof))
    counterexamples.extend(_projection_counterexamples(proposal, visible, proof=proof))
    counterexamples = list(_unique_counterexamples(counterexamples))
    return GreenfieldSemanticCompilerReport(
        version=SEMANTIC_COMPILER_VERSION,
        status="failed" if counterexamples else "passed",
        visible_result=visible,
        counterexamples=tuple(counterexamples),
        quality_scores=_quality_scores(visible, counterexamples),
    )


def semantic_compiler_issues(proposal: Mapping[str, Any]) -> list[str]:
    return [counterexample.to_issue() for counterexample in compile_greenfield_semantics(proposal).counterexamples]


def repair_greenfield_semantic_projections(proposal: dict[str, Any]) -> bool:
    """Clear poisoned generated fields so existing completion owners rebuild them."""

    changed = False
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), dict) else proposal
    if isinstance(intent, dict):
        changed |= repair_confirmed_intent_semantic_projections(intent)
    if isinstance(proposal.get("backlog"), list):
        first_path = _first_nonempty(_intent_mapping(proposal).get("first_path"), _project_brief_value(proposal, "first_path"))
        proof = _first_nonempty(_intent_mapping(proposal).get("proof_boundary"), _project_brief_value(proposal, "proof"))
        visible = select_visible_result_candidate(first_path, proof_boundary=proof)
        for row in proposal["backlog"]:
            if isinstance(row, dict):
                changed |= _clear_bad_projection_fields(row, visible=visible, proof=proof)
    return changed


def repair_confirmed_intent_semantic_projections(intent: dict[str, Any]) -> bool:
    first_path = clean_text(intent.get("first_path"))
    proof = clean_text(intent.get("proof_boundary"))
    if not first_path:
        return False
    visible = select_visible_result_candidate(first_path, proof_boundary=proof)
    return _clear_bad_projection_fields(intent, visible=visible, proof=proof)


def projection_uses_proof_boundary_as_result(value: Any, *, visible_result: str, proof_boundary: str) -> bool:
    text = clean_text(value)
    proof = clean_text(proof_boundary)
    visible = clean_text(visible_result)
    if not text or not proof:
        return "visible result produced by" in text.casefold()
    lowered = text.casefold()
    if "visible result produced by" in lowered:
        return True
    if _contains_proof_control_claim(text) and _term_overlap_ratio(proof, text) >= 0.42:
        return not visible or _term_overlap_ratio(visible, text) < _term_overlap_ratio(proof, text)
    return False


def _candidate(
    *,
    text: str,
    source_kind: str,
    source_path: str,
    confidence: float,
    provenance: tuple[str, ...],
    limit: int,
) -> GreenfieldSemanticCandidate:
    return GreenfieldSemanticCandidate(
        role="visible_result",
        text=clip_first_path_phrase(text, limit=limit) or clean_first_path_text(text),
        source_kind=source_kind,
        source_path=source_path,
        confidence=round(max(0.0, min(1.0, confidence)), 3),
        provenance=tuple(clean_first_path_text(value) for value in provenance if clean_first_path_text(value)),
    )


def _product_result_from_visible_outcome(value: Any) -> str:
    text = clean_first_path_text(value)
    if not text:
        return ""
    candidate = visible_result_object(text) or nominal_visible_result_object(text) or text
    candidate = _confirmed_result_object(source=text, result=candidate)
    candidate = _binary_actor_action_result_object(candidate) or candidate
    candidate = _resolve_result_anaphora(candidate)
    candidate = nominal_visible_result_object(candidate) or candidate
    candidate = normalize_visible_result_language(candidate) or candidate
    return lowercase_leading_article(candidate).strip(" .")


def _product_result_from_proof_boundary(value: Any) -> str:
    text = clean_first_path_text(value)
    if not text:
        return ""
    candidate = visible_result_object(text) or action_chain_fragment(text) or text
    candidate = _strip_proof_leading_clause(candidate)
    candidate = _binary_actor_action_result_object(candidate) or candidate
    candidate = _resolve_result_anaphora(candidate)
    return lowercase_leading_article(nominal_visible_result_object(candidate) or candidate).strip(" .")


_BINARY_RESULT_PARTICIPLES = {
    "accept": "accepted",
    "accepts": "accepted",
    "approve": "approved",
    "approves": "approved",
    "block": "blocked",
    "blocks": "blocked",
    "decline": "declined",
    "declines": "declined",
    "deny": "denied",
    "denies": "denied",
    "dismiss": "dismissed",
    "dismisses": "dismissed",
    "reject": "rejected",
    "rejects": "rejected",
}


def _binary_actor_action_result_object(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    action = "|".join(re.escape(verb) for verb in sorted(_BINARY_RESULT_PARTICIPLES, key=len, reverse=True))
    match = re.match(
        rf"^(?:(?:a|an|the)\s+)?[A-Za-z][A-Za-z0-9'-]*(?:\s+[A-Za-z][A-Za-z0-9'-]*){{0,4}}\s+"
        rf"(?P<left>{action})\s+or\s+(?P<right>{action})\s+(?P<object>[^.;]+)$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    left = _BINARY_RESULT_PARTICIPLES.get(match.group("left").casefold(), "")
    right = _BINARY_RESULT_PARTICIPLES.get(match.group("right").casefold(), "")
    result_object = re.sub(r"^(?:a|an|the)\s+", "", match.group("object").strip(" ."), flags=re.IGNORECASE)
    if not left or not right or not result_object:
        return ""
    return f"the {left} or {right} {result_object}".strip(" .")


def _resolve_result_anaphora(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    if not text:
        return ""
    had_demonstrative = bool(re.match(r"^(?:that|this|it|they|them)\b", text, flags=re.IGNORECASE))
    text = re.sub(r"^(?:that|this)\s+same\s+", "same ", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"^(?:that|this|it|they|them)\s+", "", text, count=1, flags=re.IGNORECASE).strip(" .")
    if had_demonstrative:
        text = _nominalize_result_state_transition(text)
        text = _strip_trailing_completion_time(text)
    return text


_RESULT_STATE_PAST = {
    "advance": "advanced",
    "advances": "advanced",
    "become": "became",
    "becomes": "became",
    "change": "changed",
    "changes": "changed",
    "finish": "finished",
    "finishes": "finished",
    "move": "moved",
    "moves": "moved",
    "remain": "remained",
    "remains": "remained",
    "settle": "settled",
    "settles": "settled",
    "turn": "turned",
    "turns": "turned",
}


def _nominalize_result_state_transition(value: str) -> str:
    words = clean_first_path_text(value).split()
    if len(words) < 3:
        return " ".join(words)
    for index, word in enumerate(words[:7]):
        verb = _RESULT_STATE_PAST.get(word.casefold().strip(".,:;"))
        if verb:
            return " ".join([*words[:index], verb, *words[index + 1 :]]).strip(" .")
    return " ".join(words)


def _strip_trailing_completion_time(value: str) -> str:
    words = clean_first_path_text(value).split()
    if len(words) >= 3 and [word.casefold().strip(".,:;") for word in words[-2:]] == ["after", "completion"]:
        return " ".join(words[:-2]).strip(" .")
    return " ".join(words)


def _strip_proof_leading_clause(value: str) -> str:
    text = clean_first_path_text(value).strip(" .")
    text = re.sub(
        r"^(?:release|version)\s+[A-Za-z0-9_.-]+\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+(?:only\s+)?when\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"^(?:the\s+)?(?:release|first\s+release)\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+(?:only\s+)?when\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    return text.strip(" .")


def _candidate_confidence(value: str, *, source_kind: str) -> float:
    if not value:
        return 0.0
    score = 0.72 if source_kind == "first_path_event" else 0.38
    if _candidate_is_product_result(value):
        score += 0.18
    if _contains_proof_control_claim(value):
        score -= 0.35
    if "confirmed" in clean_text(value).casefold().split():
        score += 0.08
    if re.search(r"\bavailable\s+for\s+[^.]{0,60}\breview\b", clean_text(value), flags=re.IGNORECASE):
        score -= 0.18
    if _is_supporting_evidence_artifact(value):
        score -= 0.12
    if _is_capability_action_candidate(value):
        score -= 0.12
    if word_count(value) >= 4:
        score += 0.05
    return score


def _step_visible_result_confidence(result: str, *, step: str, path_model: FirstPathModel) -> float:
    score = _candidate_confidence(result, source_kind="first_path_event") - 0.05
    if (
        clean_first_path_text(path_model.visible_outcome)
        and clean_first_path_text(step).casefold() != clean_first_path_text(path_model.visible_outcome).casefold()
        and actor_signature(step)
    ):
        score -= 0.3
    return score


def _terminal_visible_outcome_bonus(value: str) -> float:
    text = clean_text(value).casefold()
    if not text or text in {"next action", "next step", "what happens next", "what happened next"}:
        return 0.0
    if re.search(r"\bavailable\s+for\s+[^.]{0,60}\breview\b", text):
        return 0.0
    if _is_supporting_evidence_artifact(text):
        return 0.0
    return 0.12


def _is_supporting_evidence_artifact(value: str) -> bool:
    text = clean_text(value).casefold()
    if not text:
        return False
    if any(term in text for term in ("summary", "report", "decision", "recommendation", "route", "result", "status", "view")):
        return False
    return bool(
        re.search(
            r"\b(?:audit\s+trail|comparison\s+evidence|evidence\s+packet|evidence\s+record|proof\s+record|replay\s+output)\b",
            text,
        )
        or re.search(r"\b(?:audit|evidence|proof|replay)\b", text)
    )


def _is_capability_action_candidate(value: str) -> bool:
    text = clean_text(value).casefold()
    return bool(
        re.search(
            r"\b(?:allows?|enables?|lets?)\b.{0,80}\b(?:choose|enter|open|select|submit|update)\b",
            text,
        )
    )


def _confirmed_result_object(*, source: str, result: str) -> str:
    if not re.search(r"\bconfirms?\b", clean_first_path_text(source), flags=re.IGNORECASE):
        return result
    text = clean_first_path_text(result).strip(" .")
    if not text:
        return ""
    text = re.sub(r"^(?:a|an|the)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    return f"a confirmed {text}" if text else result


def _candidate_is_product_result(value: str) -> bool:
    text = clean_text(value)
    if word_count(text) < 2:
        return False
    if _starts_with_connector(text):
        return False
    if _starts_with_result_modifier(text):
        return False
    if _contains_proof_control_claim(text):
        return False
    lowered = text.casefold()
    if lowered in {"next action", "next step", "what happens next", "what happened next"}:
        return False
    return True


def _starts_with_connector(value: str) -> bool:
    words = clean_text(value).split()
    return bool(words and words[0].casefold().strip(".,:;") in {"and", "or", "then"})


def _starts_with_result_modifier(value: str) -> bool:
    return bool(
        re.match(
            r"^(?:alongside|as|at|by|during|for|from|including|inside|into|on|through|to|toward|towards|using|via|while|with|without)\b",
            clean_text(value),
            flags=re.IGNORECASE,
        )
    )


def _refined_pronoun_result_candidate(
    best: GreenfieldSemanticCandidate,
    proof_candidate: GreenfieldSemanticCandidate,
) -> GreenfieldSemanticCandidate:
    return GreenfieldSemanticCandidate(
        role=best.role,
        text=proof_candidate.text,
        source_kind="first_path_event_refined_by_proof_boundary",
        source_path=f"{best.source_path}+proof_boundary",
        confidence=round(max(proof_candidate.confidence, best.confidence - 0.02), 3),
        provenance=tuple(dict.fromkeys((*best.provenance, *proof_candidate.provenance))),
    )


def _proof_candidate_refines_pronoun_result(
    best: GreenfieldSemanticCandidate,
    proof_candidate: GreenfieldSemanticCandidate,
    *,
    path_model: FirstPathModel,
) -> bool:
    if best.source_kind != "first_path_event" or proof_candidate.source_kind != "proof_boundary":
        return False
    if not _visible_outcome_uses_pronoun(path_model.visible_outcome):
        return False
    best_terms = _terms(best.text)
    proof_terms = _terms(proof_candidate.text)
    if len(best_terms) > 3 and word_count(best.text) > 6:
        return False
    if len(proof_terms) < len(best_terms) + 2:
        return False
    if best_terms and len(best_terms & proof_terms) / max(1, len(best_terms)) < 0.5:
        return False
    return _candidate_is_product_result(proof_candidate.text)


def _visible_outcome_uses_pronoun(value: Any) -> bool:
    text = clean_text(value).casefold()
    if not text:
        return False
    return bool(re.search(r"\b(?:it|its|them|they|that|this|those|these|both points)\b", text))


def _contains_proof_control_claim(value: Any) -> bool:
    text = clean_text(value)
    if not text:
        return False
    lowered = text.casefold()
    if re.search(r"\b(?:release|version)\s+[a-z0-9_.-]+\s+(?:succeeds|works|is\s+proven|is\s+trusted)\s+when\b", lowered):
        return True
    if re.search(r"\b(?:is\s+proven|proven\s+when|succeeds\s+when|trusted\s+when|proof\s+boundary)\b", lowered):
        return True
    if lowered.startswith(("release proof", "version proof")):
        return True
    return bool(re.match(r"^release\s+readiness\s+(?:depends|fails|passes|requires?|when|is\s+blocked)\b", lowered))


def _visible_result_counterexamples(
    semantic: Mapping[str, Any],
    visible: GreenfieldSemanticCandidate,
    *,
    proof: str,
) -> list[GreenfieldSemanticCounterexample]:
    issues: list[GreenfieldSemanticCounterexample] = []
    first_path = semantic.get("first_path_contract") if isinstance(semantic.get("first_path_contract"), Mapping) else {}
    model_visible = clean_text(first_path.get("visible_result") if isinstance(first_path, Mapping) else "")
    if model_visible and projection_uses_proof_boundary_as_result(model_visible, visible_result=visible.text, proof_boundary=proof):
        issues.append(
            _counterexample(
                code="visible_result.proof_boundary_source",
                path="semantic_model.first_path_contract.visible_result",
                message="uses proof-boundary language as the product visible result",
                repair_hint="select the visible result from a FirstPathEvent, then let proof obligations reference it",
            )
        )
    if visible.source_kind == "proof_boundary":
        issues.append(
            _counterexample(
                code="visible_result.missing_event_source",
                path="semantic_model.first_path_contract.visible_result",
                message="fell back to the proof boundary because no product-result event was selected",
                repair_hint="compile a visible-result event from the accepted first path before rendering artifacts",
            )
        )
    return issues


def _projection_counterexamples(
    proposal: Mapping[str, Any],
    visible: GreenfieldSemanticCandidate,
    *,
    proof: str,
) -> list[GreenfieldSemanticCounterexample]:
    issues: list[GreenfieldSemanticCounterexample] = []
    for path, value in _projection_values(proposal):
        if projection_uses_proof_boundary_as_result(value, visible_result=visible.text, proof_boundary=proof):
            issues.append(
                _counterexample(
                    code="projection.proof_boundary_source",
                    path=path,
                    message="uses proof-boundary language as a product-result projection",
                    repair_hint="rebuild the field from the compiled visible result and keep release proof in proof-only fields",
                )
            )
    return issues


def _projection_values(proposal: Mapping[str, Any]) -> list[tuple[str, Any]]:
    values: list[tuple[str, Any]] = []
    intent = _intent_mapping(proposal)
    for key in ("problem", "opportunity", "product_view", "success_metrics"):
        values.append((f"intent.{key}", intent.get(key)))
    for index, row in enumerate(mapping_rows(proposal.get("backlog"))):
        for key in ("problem", "opportunity", "product_view", "success_metrics"):
            values.append((f"backlog.{index}.{key}", row.get(key)))
    return values


def _clear_bad_projection_fields(row: dict[str, Any], *, visible: GreenfieldSemanticCandidate, proof: str) -> bool:
    changed = False
    for key in ("problem", "opportunity", "product_view"):
        if projection_uses_proof_boundary_as_result(row.get(key), visible_result=visible.text, proof_boundary=proof):
            row[key] = ""
            changed = True
    metrics = row.get("success_metrics")
    if any(projection_uses_proof_boundary_as_result(value, visible_result=visible.text, proof_boundary=proof) for value in text_values(metrics)):
        row["success_metrics"] = []
        changed = True
    return changed


def _counterexample(*, code: str, path: str, message: str, repair_hint: str) -> GreenfieldSemanticCounterexample:
    return GreenfieldSemanticCounterexample(
        code=code,
        path=path,
        message=message,
        severity="error",
        repair_hint=repair_hint,
    )


def _unique_counterexamples(
    values: Sequence[GreenfieldSemanticCounterexample],
) -> tuple[GreenfieldSemanticCounterexample, ...]:
    seen: set[tuple[str, str, str]] = set()
    rows: list[GreenfieldSemanticCounterexample] = []
    for item in values:
        key = (item.code, item.path, item.message)
        if key in seen:
            continue
        seen.add(key)
        rows.append(item)
    return tuple(rows)


def _quality_scores(
    visible: GreenfieldSemanticCandidate,
    counterexamples: Sequence[GreenfieldSemanticCounterexample],
) -> dict[str, float]:
    hard_penalty = min(1.0, len(counterexamples) * 0.25)
    return {
        "visible_result_confidence": visible.confidence,
        "semantic_soundness": round(max(0.0, 1.0 - hard_penalty), 3),
        "proof_result_separation": 0.0 if visible.source_kind == "proof_boundary" else 1.0,
    }


def _term_overlap_ratio(left: str, right: str) -> float:
    left_terms = _terms(left)
    if not left_terms:
        return 0.0
    right_terms = _terms(right)
    return len(left_terms & right_terms) / max(1, len(left_terms))


def _terms(value: str) -> set[str]:
    return set(ordered_terms(clean_text(value), minimum=4, stem_ing=True, stopwords=_SEMANTIC_STOPWORDS))


def _intent_mapping(proposal: Mapping[str, Any]) -> Mapping[str, Any]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return intent if intent else proposal


def _project_brief_value(proposal: Mapping[str, Any], key: str) -> str:
    brief = proposal.get("project_brief") if isinstance(proposal.get("project_brief"), Mapping) else {}
    return clean_text(brief.get(key) if isinstance(brief, Mapping) else "")


def _first_nonempty(*values: Any) -> str:
    for value in values:
        text = clean_text(value)
        if text:
            return text
    return ""


_SEMANTIC_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "boundary",
        "complete",
        "evidence",
        "first",
        "product",
        "proof",
        "release",
        "result",
        "state",
        "that",
        "this",
        "user",
        "version",
        "visible",
    }
)


__all__ = [
    "GreenfieldSemanticCandidate",
    "GreenfieldSemanticCompilerReport",
    "GreenfieldSemanticCounterexample",
    "compile_greenfield_semantics",
    "projection_uses_proof_boundary_as_result",
    "repair_confirmed_intent_semantic_projections",
    "repair_greenfield_semantic_projections",
    "select_visible_result_candidate",
    "select_visible_result_text",
    "semantic_compiler_issues",
]
