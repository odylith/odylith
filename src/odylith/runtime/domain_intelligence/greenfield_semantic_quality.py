"""Shared semantic hygiene helpers for confirmed greenfield generation."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from odylith.runtime.artifact_quality.generated_copy_quality import generated_public_copy_findings
from odylith.runtime.artifact_quality.generated_copy_quality import has_inline_role_casing_drift
from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.common.prose_grammar import modal_base_form_drift_phrases
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import actor_led_finite_action_inside_user_can
from odylith.runtime.domain_intelligence.greenfield_generated_prose_shape import gerund_actor_role_finite_action_splice
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_action_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_capability_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_clauses
from odylith.runtime.domain_intelligence.greenfield_first_path_clauses import first_path_outcome_phrase
from odylith.runtime.domain_intelligence.greenfield_first_path_control_steps import contains_word_sense_metadata_clause
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_model
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import first_path_steps
from odylith.runtime.domain_intelligence.greenfield_first_path_semantics import material_first_path_action
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathClauses
from odylith.runtime.domain_intelligence.greenfield_first_path_types import FirstPathModel


_PROVISIONAL_TITLE_RE = re.compile(
    r"""
    (?:\s*[\(\[\{]\s*
        (?:
            working\s+title|
            draft|
            placeholder|
            tbd|
            t\.b\.d\.|
            temporary\s+title|
            title\s+tbd|
            name\s+tbd
        )
        \s*[\)\]\}]\s*)+
    |
    (?:\s*(?:[-:;]|[–—])\s*
        (?:
            working\s+title|
            placeholder|
            tbd|
            temporary\s+title|
            title\s+tbd|
            name\s+tbd
        )
        \s*)$
    """,
    re.IGNORECASE | re.VERBOSE,
)
_NGRAM_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "be",
    "by",
    "for",
    "from",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
}

_DEFERRED_MARKERS = (
    "defer",
    "deferred",
    "later",
    "later wave",
    "future",
    "out of scope",
    "outside scope",
    "not claim",
    "without claiming",
    "without claim",
)
_OUT_OF_SCOPE_MARKERS = ("out of scope", "must not claim", "should not claim", "without claiming", "not included", "not in release")
_FIRST_PATH_REQUIRED_MARKERS = ("must", "required", "need", "needs", "first path", "first release", "succeeds when")
_HEAD_SCOPED_MARKERS = frozenset({"deferred", "out of scope", "outside scope", "not included", "not in release"})
_SINGLE_TERM_SCOPE_TERMS = frozenset(
    {
        "integration",
        "lifecycle",
        "live",
        "multi",
        "reminder",
        "share",
        "sharing",
        "triage",
    }
)

_SEMANTIC_QUALITY_TERM_STOPWORDS = {
    "accepted",
    "action",
    "adjacent",
    "actor",
    "app",
    "application",
    "assigned",
    "boundary",
    "component",
    "data",
    "decision",
    "deferred",
    "depend",
    "evidence",
    "explicitly",
    "first",
    "handoff",
    "input",
    "internal",
    "other",
    "output",
    "outside",
    "path",
    "presentation",
    "product",
    "produce",
    "proof",
    "record",
    "release",
    "responsibility",
    "review",
    "rule",
    "scope",
    "service",
    "source",
    "state",
    "stay",
    "system",
    "this",
    "truth",
    "unless",
    "user",
}
_SEMANTIC_QUALITY_TERM_PREFIX_ALIASES = {
    "remind": "reminder",
    "shar": "share",
}

_SAFETY_RE = re.compile(
    r"\b(?:safety|safe|sensitive|protected|regulated|compliance|consent|private|privacy|"
    r"emergency|critical|restricted|retention|audit|access)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class TitleNormalization:
    raw_title: str
    canonical_title: str
    changed: bool



def normalize_project_title(value: Any, *, fallback: str = "Greenfield Project") -> TitleNormalization:
    """Strip provisional qualifiers from the canonical project title."""

    raw = _clean(value).strip(" .")
    if not raw:
        raw = _clean(fallback).strip(" .") or "Greenfield Project"
    canonical = raw
    previous = ""
    while canonical != previous:
        previous = canonical
        canonical = _PROVISIONAL_TITLE_RE.sub(" ", canonical)
        canonical = _collapse_title_boundary_duplicates(canonical)
        canonical = re.sub(r"\s+", " ", canonical).strip(" .:-–—")
    if not canonical:
        canonical = _clean(fallback).strip(" .") or "Greenfield Project"
    return TitleNormalization(raw_title=raw, canonical_title=canonical, changed=canonical != raw)


def contains_provisional_title_marker(value: Any) -> bool:
    return bool(_PROVISIONAL_TITLE_RE.search(_clean(value)))


def _collapse_title_boundary_duplicates(value: str) -> str:
    """Collapse duplicate lexical title boundaries before projections fan out."""

    words = str(value or "").split()
    if len(words) < 2:
        return str(value or "")
    result: list[str] = []
    for word in words:
        key = _title_boundary_key(word)
        prefix_key = _title_compound_prefix_key(word)
        if result and key:
            previous_key = _title_boundary_key(result[-1])
            if previous_key == key:
                _carry_title_duplicate_terminal_punctuation(result, word)
                continue
            if prefix_key and previous_key == prefix_key and prefix_key != key:
                result[-1] = word
                continue
        result.append(word)
    return " ".join(result)


def _title_boundary_key(value: str) -> str:
    token = str(value or "").strip("`'\"“”‘’.,;:!?()[]{}<>")
    if not token or not any(char.isalnum() for char in token):
        return ""
    return token.casefold()


def _title_compound_prefix_key(value: str) -> str:
    token = _title_boundary_key(value)
    if not token:
        return ""
    parts = re.split(r"[-/]+", token, maxsplit=1)
    if len(parts) < 2:
        return ""
    prefix = parts[0].strip("`'\"“”‘’.,;:!?()[]{}<>")
    return prefix if len(prefix) >= 2 and any(char.isalnum() for char in prefix) else ""


def _carry_title_duplicate_terminal_punctuation(output: list[str], duplicate: str) -> None:
    if not output:
        return
    suffix = str(duplicate or "")[-1:]
    if suffix in ".!?" and output[-1][-1:] not in ".!?":
        output[-1] = f"{output[-1].rstrip(',;:')}{suffix}"




def release_scope_for_component(
    component: Mapping[str, Any],
    *,
    first_path: str,
    proof_boundary: str,
    non_goals: Sequence[str] = (),
) -> str:
    """Classify a greenfield component's first-release relationship."""

    label = _clean(component.get("label") or component.get("name") or component.get("component_id"))
    body = _clean(
        " ".join(
            text_values(
                [
                    label,
                    component.get("source_system_description"),
                    component.get("responsibility"),
                    component.get("boundary"),
                ]
            )
        )
    )
    terms = _terms(body)
    if not terms:
        return "supporting"
    deferred_text = _scope_text(proof_boundary, *non_goals)
    path_terms = _terms(" ".join((first_path, material_first_path_action(first_path))))
    affirmative_proof_terms = _affirmative_scope_terms(proof_boundary)
    proof_terms = _terms(proof_boundary)
    visible_terms = _terms(first_path_outcome_phrase(first_path, proof_boundary=proof_boundary))
    out_of_scope_match = _scope_context_matches(deferred_text, terms, markers=_OUT_OF_SCOPE_MARKERS)
    deferred_match = _scope_context_matches(deferred_text, terms, markers=_DEFERRED_MARKERS)
    if _material_overlap(terms, visible_terms) >= 2:
        return "first_path_required"
    if _material_overlap(terms, affirmative_proof_terms) >= 2 and (out_of_scope_match or deferred_match):
        return "supporting"
    if out_of_scope_match:
        return "out_of_scope"
    if deferred_match:
        return "deferred"
    if _material_overlap(terms, path_terms) >= 2:
        return "first_path_required"
    if len(terms) == 1 and terms & path_terms:
        return "first_path_required"
    if _material_overlap(terms, affirmative_proof_terms) >= 2:
        return "supporting"
    if _ambiguous_first_release_scope_matches(deferred_text, terms):
        return "deferred"
    if terms & proof_terms:
        return "supporting"
    if _scope_context_matches(_scope_text(*non_goals), terms, markers=_DEFERRED_MARKERS + _OUT_OF_SCOPE_MARKERS):
        return "deferred"
    return "supporting"


def _affirmative_scope_terms(value: Any) -> set[str]:
    """Return proof terms after bounded negative-scope clauses are removed."""

    text = _clean(value)
    sentences = re.split(r"(?<=[.!?])\s+|;\s+|\n+", text)
    cleaned = [_remove_negative_scope_segments(sentence) for sentence in sentences]
    return _terms(". ".join(part for part in cleaned if part.strip()))


def _remove_negative_scope_segments(value: str) -> str:
    text = _clean(value)
    lowered = text.casefold()
    for marker in sorted(_DEFERRED_MARKERS + _OUT_OF_SCOPE_MARKERS, key=len, reverse=True):
        index = lowered.find(marker)
        if index < 0:
            continue
        head = text[:index].strip(" ,")
        tail = text[index + len(marker) :].strip(" ,")
        retained_tail = _tail_after_negative_scope_phrase(tail)
        text = f"{head}. {retained_tail}".strip(" .")
        lowered = text.casefold()
    return text


def _tail_after_negative_scope_phrase(value: str) -> str:
    segments = [segment.strip(" ,") for segment in _clean(value).split(",")]
    for index, segment in enumerate(segments):
        if index == 0 or not looks_like_finite_action(segment):
            continue
        return ", ".join(segments[index:]).strip(" ,")
    return ""


def active_release_components(components: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows = [
        row
        for row in components
        if str(row.get("release_scope", "")).strip() not in {"deferred", "out_of_scope", "external"}
    ]
    return rows or list(components)


def health_safety_obligations(*values: Any) -> tuple[str, ...]:
    """Return generic safety obligations when the accepted intent raises safety pressure."""

    text = _clean(" ".join(str(value or "") for value in values))
    if not _SAFETY_RE.search(text):
        return ()
    return (
        "Safety posture: the product records accepted user-entered facts without expanding into advice, authority, or decisions outside the confirmed boundary.",
        "Escalation posture: high-risk or explicitly restricted states must block ordinary readiness and route to the owner or external authority named by the accepted intent.",
        "Sensitive-data posture and privacy posture: protected state, lifecycle actions, retention, consent, and access require explicit policy and audit evidence when the accepted intent names them.",
    )


def generated_semantic_slop_issues(value: Any, *, root: str = "artifact") -> list[str]:
    """Detect visible generated prose that should never pass a greenfield gate."""

    issues: list[str] = []
    actor_labels = _semantic_actor_labels(value)
    for path, text in _text_leaves(value):
        location = f"{root}.{path}" if path else root
        lowered = text.casefold()
        if contains_provisional_title_marker(text):
            issues.append(f"provisional title qualifier leaked at {location}")
        if re.fullmatch(r"TBD\.?", text.strip(), flags=re.IGNORECASE):
            issues.append(f"placeholder TBD copy leaked at {location}")
        if re.search(r"\bvalidation\s+gates\s+pass\b", lowered):
            issues.append(f"generic validation-gate copy leaked at {location}")
        if has_inline_role_casing_drift(text):
            issues.append(f"inline actor casing drift leaked at {location}")
        issues.extend(
            finding.message
            for finding in generated_public_copy_findings(location, text)
            if finding.category in {"mixed_role_case", "prepositional_visible_result", "unbalanced_quote"}
        )
        if modal_base_form_drift_phrases(text):
            issues.append(f"modal/base-form grammar drift leaked at {location}")
        if re.search(r"\bowns\s+maintains\b", lowered):
            issues.append(f"malformed ownership verb pair leaked at {location}")
        if re.search(r"\bprevents\s+[^.]{1,120}\bcan\s+\w+", lowered):
            issues.append(f"malformed prevents/can clause leaked at {location}")
        if re.search(r"\bdone,\s*path,\s*mean,\s*person,\s*create,\s*view,\s*edit\b", lowered):
            issues.append(f"token-soup proof language leaked at {location}")
        if re.search(r"\bfirst\s+accepted\s+action\b", lowered):
            issues.append(f"mechanical first-action scaffold leaked at {location}")
        if re.search(r"\bfirst\s+path\s+entry\b", lowered):
            issues.append(f"mechanical first-path-entry scaffold leaked at {location}")
        if re.search(r"\brelease\s+[A-Za-z0-9_.-]+\s+is\s+trusted\s+only\s+when\s+the\s+accepted\s+path\b", text, flags=re.IGNORECASE):
            issues.append(f"mechanical release-proof scaffold leaked at {location}")
        if re.search(r"\baccepted\s+path\s+can\s+be\s+replayed\s+from\s+input\s+through\s+state\s+change\b", lowered):
            issues.append(f"mechanical accepted-path replay scaffold leaked at {location}")
        if re.search(r"\bis\s+not\s+trustworthy\s+when\b", lowered):
            issues.append(f"mechanical trust scaffold leaked at {location}")
        if _has_mechanical_need_to_turn(text):
            issues.append(f"mechanical need-to-turn problem scaffold leaked at {location}")
        if re.search(r"\bfirst\s+release\s+can\s+collect\s+activity\b", lowered):
            issues.append(f"mechanical activity-without-result scaffold leaked at {location}")
        if re.search(r"\baccepted\s+path\s+lets\s+users\b", lowered):
            issues.append(f"mechanical success-metric scaffold leaked at {location}")
        if actor_led_finite_action_inside_user_can(text):
            issues.append(f"actor-led finite action leaked inside user-can clause at {location}")
        if gerund_actor_role_finite_action_splice(text, actor_labels=actor_labels):
            issues.append(f"gerundized actor-role action leaked at {location}")
        if re.search(r"\bsource\s+evidence,\s+visible\s+blockers,\s+and\s+the\s+systems?\s+that\s+own\b", lowered):
            issues.append(f"governance-scaffold problem language leaked at {location}")
        if re.search(r"\bmetrics?\s+trended\s+with\b", lowered):
            issues.append(f"malformed metric-trend phrase leaked at {location}")
        if re.search(r"\bthis\s+stays\s+narrow\s+so\s+the\s+team\s+can\s+prove\b", lowered):
            issues.append(f"generic narrow-scope rationale leaked at {location}")
        if re.search(r"\banything\s+not\s+needed\s+for\s+this\s+reviewed\s+behavior\s+waits\b", lowered):
            issues.append(f"generic deferred-scope rationale leaked at {location}")
        if re.search(r"\bfor\s+each\s+the\s+accepted\s+state\s+change\b", lowered):
            issues.append(f"malformed accepted-state-change phrase leaked at {location}")
        if re.search(r"\bkeep\s+keep\s+", lowered):
            issues.append(f"duplicated scope-control verb leaked at {location}")
        if re.search(r"\brisk:\s+(?:and|or)\s+[a-z]", lowered):
            issues.append(f"connector-clipped risk subject leaked at {location}")
        if re.search(r"\bsecurity\s+posture:\s+(?:and|or)\s+[a-z]", lowered):
            issues.append(f"connector-clipped security subject leaked at {location}")
        if re.search(r"\bservice\s+boundary\s+for\s+(?:combines?|evaluates?)\b", lowered):
            issues.append(f"action clause leaked into registry boundary summary at {location}")
        if re.search(r"\bmetrics?\s+changed\s+usage\b", lowered):
            issues.append(f"malformed metric-change artifact phrase leaked at {location}")
        if re.search(r"\bkeeps?\s+the\s+accepted\s+path\s+step\s+reviewable\b", lowered):
            issues.append(f"mechanical path-review scaffold leaked at {location}")
        if re.search(r"\bproves\s+one\s+successful\s+local\s+state\s+transition\b", lowered):
            issues.append(f"mechanical local-transition metric leaked at {location}")
        if re.search(r"\bcan\s+act\s+where\s+the\s+accepted\s+path\s+requires\b", lowered):
            issues.append(f"mechanical actor-path scaffold leaked at {location}")
        if re.search(r"\b(?:keeps?|guides?)\s+(?:authorization|the\s+first\s+path)\s+(?:reaches|is|state|input|result)\b", lowered):
            issues.append(f"verb phrase leaked as component artifact at {location}")
        if re.search(r"\bthe\s+local\s+contract\s+centers\s+on\b", lowered):
            issues.append(f"mechanical component-contract narration leaked at {location}")
        if re.search(r"\bkeeps\s+the\s+project\s+honest\b", lowered):
            issues.append(f"mechanical evidence narration leaked at {location}")
        if re.search(r"\bexpected\s+local\s+output\s*:", lowered):
            issues.append(f"generic local-output scaffold leaked at {location}")
        if re.search(r"\bit\s+owns\s+for\b", lowered) or re.search(r"\bit\s+owns\s+the\s+central\s+object\s+is\b", lowered):
            issues.append(f"malformed ownership sentence leaked at {location}")
        if re.search(r"\bevidence\s+evidence\b", lowered):
            issues.append(f"duplicated evidence word leaked at {location}")
        if re.search(r"\b[a-z][a-z-]*\b(?:metrics?|state|input|output|record|proof)[)](?:\s|[.,;:]|$)", lowered):
            issues.append(f"dangling close-parenthesis token leaked at {location}")
        if re.search(r"\bmulti-user\s+roles\s+are\s*[.]?$", lowered):
            issues.append(f"clipped out-of-scope sentence leaked at {location}")
        if re.search(r"\bhand\s+[a-z][a-z-]*(?:\s+[a-z][a-z-]*){0,4}\s+(?:identity|state|evidence|result|record)\b", lowered):
            issues.append(f"handoff verb leaked as an artifact noun at {location}")
        if re.search(r"\buses\s+the\s+product\s+to\s+(?:a|an|the\s+)?[a-z][a-z '-]{0,80}\s+(?:adds|creates|makes|opens|picks|sees)\b", lowered):
            issues.append(f"actor/action splice leaked at {location}")
        if re.search(r"\badd\s+[^.;]{1,100}\band\s+picks\b", lowered) or re.search(
            r"\bcreate\s+[^.;]{1,100}\band\s+adds\b", lowered
        ) or re.search(r"\bmake\s+[^.;]{1,100}\band\s+sees\b", lowered):
            issues.append(f"mixed infinitive/finite action chain leaked at {location}")
        if re.search(r"\b(?:reflection|result|summary|view|readout|outcome|consequence)\s+and\s+(?:completes?|ends?|finishes?)\b", lowered):
            issues.append(f"terminal action leaked into visible result noun at {location}")
        if re.search(r"\bunderstand\s+[A-Z]", text):
            issues.append(f"sentence fragment leaked after understand at {location}")
        if re.search(r"\b(?:reach|use)\s+(?:a|an|the\s+)?(?:reflection|result|summary|view|readout|outcome|consequence)\b", lowered):
            issues.append(f"awkward visible-result action leaked at {location}")
        if contains_word_sense_metadata_clause(text) or re.search(
            r"\b(?:(?:reach|see|review|show|use)\s+)?(?:(?:a|an|the)\s+)?(?:act|action|operation|verb)s?\s+(?:and\s+)?(?:as\s+)?(?:(?:a|an|the)\s+)?(?:governed\s+)?(?:artifact|entity|noun|object|record)s?\b",
            lowered,
        ):
            issues.append(f"word-sense metadata leaked as visible result at {location}")
        if re.search(
            r"\b(?:that|this)\s+(?:path|loop|journey|flow)\s+[–—-][^.]{0,160}\b(?:smallest\s+version\s+of\s+the\s+whole\s+product|working\s+end\s+to\s+end)\b",
            lowered,
        ) or re.search(r"\bthe\s+pattern\s+[–—-]\s+is\s+the\s+smallest\s+version\s+of\s+the\s+whole\s+product\b", lowered):
            issues.append(f"meta loop summary leaked as product outcome at {location}")
        if re.search(r"\bmaintains\s+(?:continue|keep|maintain|sustain)\b", lowered):
            issues.append(f"malformed component responsibility leaked at {location}")
        if re.search(r"\b[a-z][a-z0-9'-]*s\s+are\s+meant\s+to\b", lowered):
            issues.append(f"malformed relative-clause split leaked at {location}")
        if (
            re.search(r"\bas a later\s*[.]?$", lowered)
            or re.search(r"\bvalid\s+transition\s+display,\s*stale\b", lowered)
            or re.search(r"\brejected\s+or\s+blocked\s+cases,\s*evidence\s*[.;:]?$", lowered)
        ):
            issues.append(f"clipped generated sentence leaked at {location}")
    return _unique(issues)


def _semantic_actor_labels(value: Any) -> frozenset[str]:
    if not isinstance(value, Mapping):
        return frozenset()
    labels: list[str] = []
    intent = value.get("intent")
    if isinstance(intent, Mapping):
        human_actors = intent.get("human_actors")
        if isinstance(human_actors, list):
            labels.extend(_actor_label_from_row(actor) for actor in human_actors)
    model = value.get("semantic_model")
    if isinstance(model, Mapping):
        labels.extend(_actor_labels_from_semantic_model(model))
    return frozenset(_clean(label).casefold() for label in labels if _clean(label))


def _actor_labels_from_semantic_model(model: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    contract = model.get("first_path_contract")
    if isinstance(contract, Mapping):
        actor = _clean(contract.get("actor"))
        if actor:
            labels.append(actor)
        labels.extend(_actor_labels_from_events(contract.get("events")))
    graph = model.get("diagram_event_graph")
    if isinstance(graph, Mapping):
        labels.extend(_actor_labels_from_events(graph.get("events")))
    ontology = model.get("domain_ontology")
    if isinstance(ontology, Mapping):
        actors = ontology.get("actors")
        if isinstance(actors, list):
            labels.extend(_actor_label_from_row(actor) for actor in actors)
    return [label for label in labels if label]


def _actor_labels_from_events(events: Any) -> list[str]:
    if not isinstance(events, list):
        return []
    labels: list[str] = []
    for event in events:
        if isinstance(event, Mapping):
            actor = _clean(event.get("actor"))
            if actor:
                labels.append(actor)
    return labels


def _actor_label_from_row(row: Any) -> str:
    if isinstance(row, Mapping):
        for key in ("label", "actor", "name", "role"):
            label = _clean(row.get(key))
            if label:
                return label
        return ""
    text = _clean(row)
    if ":" in text:
        return text.split(":", 1)[0].strip()
    return text


def _has_mechanical_need_to_turn(value: Any) -> bool:
    """Reject product-name scaffolds without banning ordinary product-story language."""

    text = _clean(value)
    for match in re.finditer(r"\bneed(?:s)?\s+(?P<object>[^.;]{1,120}?)\s+to\s+turn\b", text):
        object_text = re.sub(r"\s+", " ", str(match.group("object") or "")).strip(" ,")
        if not object_text:
            continue
        lowered = object_text.casefold()
        if re.search(
            r"\b(?:way|place|method|path|workflow|workspace|console|tool|experience|process|ability|capacity)\b",
            lowered,
        ):
            continue
        if re.match(r"^(?:a|an|one|the|this|that|their|our|your)\b", lowered):
            continue
        if re.match(r"^[A-Z][A-Za-z0-9_-]*(?:\s+[A-Z][A-Za-z0-9_-]*){0,6}$", object_text):
            return True
        if re.search(
            r"\b(?:product|app|application|platform|tracker|companion|dashboard|engine|service|system)\s*$",
            lowered,
        ):
            return True
    return False


def sentence_overlap_ratio(left: str, right: str, *, ngram: int = 5) -> float:
    left_grams = _ngrams(left, ngram=ngram)
    right_grams = _ngrams(right, ngram=ngram)
    if not left_grams or not right_grams:
        return 0.0
    return len(left_grams & right_grams) / max(1, min(len(left_grams), len(right_grams)))


def _scope_context_matches(text: str, terms: set[str], *, markers: Sequence[str]) -> bool:
    if not terms:
        return False
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+|\n+", _clean(text)):
        lowered = sentence.casefold()
        for marker in markers:
            if marker not in lowered:
                continue
            head, tail = lowered.split(marker, 1)
            tail_terms = _terms(tail)
            if _material_overlap(terms, tail_terms) >= 2 or terms & tail_terms & _SINGLE_TERM_SCOPE_TERMS:
                return True
            head_terms = _terms(head)
            if (
                marker in _HEAD_SCOPED_MARKERS
                and _looks_like_head_scoped_clause(head)
                and (_material_overlap(terms, head_terms) >= 2 or terms & head_terms & _SINGLE_TERM_SCOPE_TERMS)
            ):
                return True
    return False


def _scope_text(*values: Any) -> str:
    parts = [_clean(value).strip(" .") for value in values if _clean(value).strip(" .")]
    return ". ".join(parts)


def _ambiguous_first_release_scope_matches(text: str, terms: set[str]) -> bool:
    if not terms:
        return False
    component_terms = _scope_alias_terms(terms)
    for sentence in re.split(r"(?<=[.!?])\s+|;\s+|\n+", _clean(text)):
        lowered = sentence.casefold()
        if "whether" not in lowered:
            continue
        if not re.search(r"\b(?:first\s+release|first\s+path|core|belongs?|include|included|scope|later)\b", lowered):
            continue
        sentence_terms = _scope_alias_terms(_terms(sentence))
        if _material_overlap(component_terms, sentence_terms) >= 2:
            return True
    return False


def _scope_alias_terms(values: set[str]) -> set[str]:
    terms = set(values)
    for value in values:
        if len(value) > 5 and value.endswith("er"):
            terms.add(value[:-2])
            terms.add(value[:-1])
        if len(value) > 5 and value.endswith("ing"):
            terms.add(value[:-3])
    return {term for term in terms if term}


def _material_overlap(left: set[str], right: set[str]) -> int:
    return len(left & right)


def _looks_like_head_scoped_clause(value: str) -> bool:
    text = _clean(value)
    if not text:
        return False
    words = label_terms(text)
    if len(words) > 14:
        return False
    if re.search(r"\b(?:is|are|stays?|remains?|keeps?|kept|explicitly|currently)\s*$", text, re.IGNORECASE):
        return True
    if re.search(r"[:,-]\s*$", text):
        return True
    if len(words) <= 6:
        return True
    return False


def _text_leaves(value: Any, *, path: tuple[str, ...] = ()) -> tuple[tuple[str, str], ...]:
    if isinstance(value, Mapping):
        rows: list[tuple[str, str]] = []
        for key, nested in value.items():
            if str(key).casefold() in {"source_title"}:
                continue
            rows.extend(_text_leaves(nested, path=(*path, str(key))))
        return tuple(rows)
    if isinstance(value, (list, tuple, set)):
        rows: list[tuple[str, str]] = []
        for index, nested in enumerate(value):
            rows.extend(_text_leaves(nested, path=(*path, str(index))))
        return tuple(rows)
    text = _clean(value)
    return ((".".join(path), text),) if text else ()


def _terms(value: Any) -> set[str]:
    return set(
        ordered_terms(
            _clean(value),
            stopwords=_SEMANTIC_QUALITY_TERM_STOPWORDS,
            stem_ing=True,
            prefix_aliases=_SEMANTIC_QUALITY_TERM_PREFIX_ALIASES,
        )
    )


def _ngrams(value: str, *, ngram: int) -> set[tuple[str, ...]]:
    tokens = [token.casefold() for token in label_terms(value, stopwords=_NGRAM_STOPWORDS)]
    return {tuple(tokens[index : index + ngram]) for index in range(max(0, len(tokens) - ngram + 1))}




def _clean(value: Any) -> str:
    return clean_artifact_text(value)


def _unique(values: Sequence[str]) -> list[str]:
    return list(unique_text(_clean(value) for value in values))


__all__ = [
    "FirstPathClauses",
    "FirstPathModel",
    "TitleNormalization",
    "active_release_components",
    "contains_provisional_title_marker",
    "first_path_action_phrase",
    "first_path_clauses",
    "first_path_capability_phrase",
    "first_path_model",
    "first_path_outcome_phrase",
    "first_path_steps",
    "generated_semantic_slop_issues",
    "health_safety_obligations",
    "material_first_path_action",
    "normalize_project_title",
    "release_scope_for_component",
    "sentence_overlap_ratio",
]
