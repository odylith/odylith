"""Project-level judgment checks for confirmed greenfield artifact packages."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_rows import mapping_rows
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import active_release_components
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.project_intelligence.product_story_contract import PRODUCT_STORY_CARD_SLOTS
from odylith.runtime.project_intelligence.product_story_contract import PRODUCT_STORY_SLOT_BY_LABEL


_SCOPE_BOUNDARY_RE = re.compile(
    r"\bDo\s+not\s+expand\s+beyond\s+(?P<body>.+?)\s+until\s+the\s+first\s+outcome\s+works\b",
    re.IGNORECASE,
)
_STATE_OBJECT_PREDICATE_RE = re.compile(
    r"\b(?:accepted\s+change|state\s+change|versioned\s+state\s+object|state\s+object)\s*"
    r"(?:to|is|:)\s+(?:the\s+)?(?:product|system|app|application|workspace|service|platform|tool)\s+"
    r"(?:captures?|keeps?|records?|stores?|tracks?|holds?|manages?|maintains?|coordinates?|orchestrates?)\b",
    re.IGNORECASE,
)
_COMPONENT_SUMMARY_RE = re.compile(
    r"\bcomponents\s+come\s+from\s+product\s+systems\s+named\s+in\s+the\s+accepted\s+product\s+direction\s*:\s*"
    r"(?P<body>[^.!?]+[.!?])",
    re.IGNORECASE,
)
_TERM_STOPWORDS = frozenset(
    {
        "accepted",
        "action",
        "after",
        "before",
        "component",
        "components",
        "complete",
        "first",
        "from",
        "path",
        "product",
        "proof",
        "record",
        "release",
        "service",
        "state",
        "system",
        "that",
        "their",
        "then",
        "this",
        "user",
        "when",
        "with",
        "without",
    }
)
def greenfield_project_judgment_issues(package: Any) -> list[str]:
    """Return human-quality failures that structural package gates cannot see."""

    proposal = _as_mapping(getattr(package, "proposal", None))
    text = _package_text(package)
    issues: list[str] = []
    issues.extend(_mixed_case_drift_issues(proposal, text))
    issues.extend(_state_object_predicate_issues(proposal, text))
    issues.extend(_component_summary_clip_issues(proposal, text))
    issues.extend(_scope_boundary_tail_issues(proposal, text))
    issues.extend(_project_story_repetition_issues(package))
    issues.extend(_accepted_assumption_coverage_issues(proposal, _rendered_artifact_text(package)))
    return unique_text(issues)


def _project_story_repetition_issues(package: Any) -> list[str]:
    preview = _as_mapping(getattr(package, "project_dashboard_preview", None))
    story = _as_mapping(preview.get("product_story"))
    cards = [row for row in mapping_rows(story.get("release_contract")) if normalize_string(row.get("body"))]
    return project_story_semantic_issues(cards)


def project_story_semantic_issues(cards: Sequence[Mapping[str, Any]]) -> list[str]:
    """Return role-ownership and repetition failures for rendered story cards."""

    if not cards:
        return []
    issues = _project_story_role_issues(cards)
    signatures = [
        (
            normalize_string(row.get("label")) or f"card {index + 1}",
            set(
                ordered_terms(
                    normalize_string(row.get("body")),
                    stopwords=_TERM_STOPWORDS,
                    minimum=4,
                    stem_ing=True,
                )
            ),
        )
        for index, row in enumerate(cards)
    ]
    for index, (left_label, left_terms) in enumerate(signatures):
        if len(left_terms) < 8:
            continue
        for right_label, right_terms in signatures[index + 1 :]:
            if len(right_terms) < 8:
                continue
            shared = left_terms & right_terms
            if len(shared) < 8:
                continue
            containment = len(shared) / min(len(left_terms), len(right_terms))
            similarity = len(shared) / len(left_terms | right_terms)
            if containment >= 0.82 and similarity >= 0.68:
                issues.append(
                    "greenfield Project Product Story cards are semantically repetitive: "
                    f"`{left_label}` and `{right_label}` restate the same user meaning"
                )
    return issues


def _project_story_role_issues(cards: Sequence[Mapping[str, Any]]) -> list[str]:
    issues: list[str] = []
    label_counts: dict[str, int] = {}
    slot_owners: dict[str, str] = {}
    for row in cards:
        label = normalize_string(row.get("label"))
        expected_slot = PRODUCT_STORY_SLOT_BY_LABEL.get(label)
        if not expected_slot:
            issues.append(
                "greenfield Project Product Story card has an unexpected semantic label: "
                f"`{label or 'unlabeled card'}`"
            )
            continue
        label_counts[label] = label_counts.get(label, 0) + 1
        semantic_slot = normalize_string(row.get("semantic_slot"))
        if not semantic_slot:
            issues.append(
                "greenfield Project Product Story card is missing its owned semantic slot: "
                f"`{label}` expects `{expected_slot}`"
            )
            continue
        if semantic_slot != expected_slot:
            issues.append(
                "greenfield Project Product Story card is bound to the wrong semantic slot: "
                f"`{label}` uses `{semantic_slot}` instead of `{expected_slot}`"
            )
        previous_owner = slot_owners.get(semantic_slot)
        if previous_owner and previous_owner != label:
            issues.append(
                "greenfield Project Product Story cards reuse one semantic slot: "
                f"`{previous_owner}` and `{label}` both use `{semantic_slot}`"
            )
        else:
            slot_owners[semantic_slot] = label
    for label, _semantic_slot in PRODUCT_STORY_CARD_SLOTS:
        count = label_counts.get(label, 0)
        if count == 0:
            issues.append(f"greenfield Project Product Story is missing its `{label}` card")
        elif count > 1:
            issues.append(f"greenfield Project Product Story repeats its `{label}` card")
    return issues


def _mixed_case_drift_issues(proposal: Mapping[str, Any], text: str) -> list[str]:
    tokens = _source_mixed_case_tokens(proposal)
    issues: list[str] = []
    for token in sorted(tokens):
        lowered_first = f"{token[:1].lower()}{token[1:]}"
        if lowered_first != token and re.search(rf"\b{re.escape(lowered_first)}\b", text):
            issues.append(f"greenfield artifacts drift mixed-case source token `{token}` into `{lowered_first}`")
    return issues


def _source_mixed_case_tokens(proposal: Mapping[str, Any]) -> set[str]:
    source = _source_casing_authority_text(proposal)
    return {
        token
        for token in re.findall(r"\b[A-Z][A-Za-z0-9_/-]*[A-Z][A-Za-z0-9_/-]*\b", source)
        if len(token) >= 3 and not _source_contains_lower_first_variant(source, token)
    }


def _source_contains_lower_first_variant(source: str, token: str) -> bool:
    lowered_first = f"{token[:1].lower()}{token[1:]}"
    return lowered_first != token and bool(re.search(rf"\b{re.escape(lowered_first)}\b", source))


def _source_casing_authority_text(proposal: Mapping[str, Any]) -> str:
    accepted_source = " ".join(
        text_values(
            {
                "intent": proposal.get("intent"),
                "confirmed_intent": proposal.get("confirmed_intent"),
            }
        )
    )
    if _has_source_casing_token(accepted_source):
        return accepted_source
    return " ".join(
        text_values(
            {
                "intent": proposal.get("intent"),
                "semantic_model": proposal.get("semantic_model"),
                "confirmed_intent": proposal.get("confirmed_intent"),
            }
        )
    )


def _has_source_casing_token(value: str) -> bool:
    return bool(
        re.search(
            r"\b[A-Z]{2,}(?:[/-][A-Za-z0-9]+)*\b|"
            r"\b[A-Za-z][A-Za-z0-9_/-]*[A-Z][A-Za-z0-9_/-]*\b",
            value,
        )
    )


def _state_object_predicate_issues(proposal: Mapping[str, Any], text: str) -> list[str]:
    issues: list[str] = []
    if _STATE_OBJECT_PREDICATE_RE.search(text):
        issues.append("greenfield artifacts leak a product/system predicate instead of a state-object noun phrase")
    intent = _as_mapping(proposal.get("intent"))
    raw_state = normalize_string(intent.get("state_object"))
    if not raw_state:
        return issues
    state_label = domain_object_label(raw_state, fallback="")
    if not state_label:
        return issues
    raw_predicate = re.match(
        r"^(?:the\s+)?(?:product|system|app|application|workspace|service|platform|tool)\s+"
        r"(?:captures?|keeps?|records?|stores?|tracks?|holds?|manages?|maintains?|coordinates?|orchestrates?)\s+",
        raw_state,
        flags=re.IGNORECASE,
    )
    if raw_predicate and raw_state.casefold() in text.casefold():
        issues.append(
            f"greenfield artifacts should use state-object label `{state_label}` instead of the raw tracking predicate"
        )
    return issues


def _component_summary_clip_issues(proposal: Mapping[str, Any], text: str) -> list[str]:
    labels = _component_labels(proposal)
    if not labels:
        return []
    issues: list[str] = []
    for match in _COMPONENT_SUMMARY_RE.finditer(text):
        body = match.group("body")
        for label in labels:
            words = _words(label)
            if len(words) < 2:
                continue
            head = words[0]
            if _component_summary_label(label).casefold() == head.casefold():
                continue
            if re.search(rf"\b{re.escape(head)}\s*[.!?]", body) and not re.search(
                rf"\b{re.escape(label)}\b",
                body,
                flags=re.IGNORECASE,
            ):
                issues.append(f"greenfield project brief clips component label `{label}` to `{head}`")
        if len(labels) <= 8:
            body_terms = _summary_label_terms(body)
            for label in labels:
                label_terms = _summary_label_terms(_component_summary_label(label))
                if label_terms and not label_terms.issubset(body_terms):
                    issues.append(f"greenfield project brief component summary omits `{label}`")
    return issues


def _component_labels(proposal: Mapping[str, Any]) -> list[str]:
    labels: list[str] = []
    rows = [row for row in mapping_rows(proposal.get("components"))]
    for row in active_release_components(rows):
        label = normalize_string(row.get("label"))
        if label:
            labels.append(label)
    return labels


def _component_summary_label(value: str) -> str:
    text = re.sub(
        r"\s+\b(?:Adapter|Dashboard|Engine|Flow|Library|Model|Portal|Service|Store|Surface|Tracker|View)\b\s*$",
        "",
        normalize_string(value),
        flags=re.IGNORECASE,
    ).strip() or normalize_string(value)
    text = re.sub(r"\s+\b(?:with|grouping)\b.+$", "", text, flags=re.IGNORECASE).strip() or text
    return text


def _summary_label_terms(value: str) -> set[str]:
    return {
        term
        for term in ordered_terms(
            value,
            stopwords=_TERM_STOPWORDS,
            minimum=3,
            preserve_terms={"ui", "ux", "ai", "ml"},
            stem_ing=True,
            stem_ing_minimum_length=5,
        )
    }


def _scope_boundary_tail_issues(proposal: Mapping[str, Any], text: str) -> list[str]:
    semantic = _as_mapping(proposal.get("semantic_model"))
    first_path = _as_mapping(semantic.get("first_path_contract"))
    events = [row for row in first_path.get("events", []) if isinstance(row, Mapping)]
    if len(events) < 4:
        return []
    issues: list[str] = []
    tail_events = events[max(1, len(events) - 3) :]
    visible_result = normalize_string(first_path.get("visible_result"))
    for match in _SCOPE_BOUNDARY_RE.finditer(text):
        body = match.group("body")
        if _tail_events_covered(body, tail_events=tail_events, visible_result=visible_result):
            continue
        issues.append("greenfield scope boundary truncates the accepted first-path tail")
    return issues


def _accepted_assumption_coverage_issues(proposal: Mapping[str, Any], rendered_text: str) -> list[str]:
    """Require high-risk accepted assumptions to survive into generated artifacts."""

    if not rendered_text:
        return []
    rendered_terms = _terms(rendered_text)
    if not rendered_terms:
        return []
    issues: list[str] = []
    for row in mapping_rows(proposal.get("assumptions")):
        if normalize_string(row.get("tier")).casefold() != "user_intent":
            continue
        statement = normalize_string(row.get("statement"))
        if not statement or not _assumption_needs_artifact_coverage(statement):
            continue
        terms = _terms(statement)
        if not terms:
            continue
        required = min(3, max(2, round(len(terms) * 0.35)))
        if len(terms & rendered_terms) < required:
            label = normalize_string(row.get("id")) or "accepted assumption"
            issues.append(f"greenfield domain-expert lens omits accepted assumption `{label}` from generated artifacts")
    return issues


def _assumption_needs_artifact_coverage(value: str) -> bool:
    text = normalize_string(value).casefold()
    return bool(
        re.search(
            r"\b(?:authorized|certified|compliance|diagnosis|legal|must|no|not|only|override|privacy|reject|"
            r"retention|safety|security|scope|strict|unauthorized)\b",
            text,
        )
    )


def _tail_events_covered(
    body: str,
    *,
    tail_events: Sequence[Mapping[str, Any]],
    visible_result: str,
) -> bool:
    body_terms = _terms(body)
    if not body_terms:
        return False
    covered_events = 0
    for event in tail_events:
        event_terms = _terms(" ".join(text_values([event.get("text"), event.get("mutation"), event.get("target_entity")])))
        action = normalize_string(event.get("action")).casefold()
        action_covered = bool(action and _term_variants(action) & body_terms)
        term_covered = bool(event_terms and len(event_terms & body_terms) >= min(2, len(event_terms)))
        if action_covered or term_covered:
            covered_events += 1
    visible_terms = _terms(visible_result)
    visible_covered = not visible_terms or len(visible_terms & body_terms) >= min(2, len(visible_terms))
    if not visible_covered:
        visible_covered = len(_terms_with_variants(visible_result) & body_terms) >= min(2, len(visible_terms))
    return visible_covered and covered_events >= max(1, len(tail_events) - 1)


def _terms(value: str) -> set[str]:
    return set(ordered_terms(value, stopwords=_TERM_STOPWORDS, minimum=4, stem_ing=True, stem_ing_minimum_length=5))


def _term_variants(value: str) -> set[str]:
    text = normalize_string(value).casefold()
    variants = {text}
    if text.endswith("s") and len(text) > 4:
        variants.add(text[:-1])
    if text.endswith("ing") and len(text) > 6:
        variants.add(text[:-3])
    variants.update(_action_inflection_variants(text))
    return {term for variant in variants for term in _terms(variant)} | {variant for variant in variants if len(variant) >= 3}


def _terms_with_variants(value: str) -> set[str]:
    rows: set[str] = set()
    for term in _terms(value):
        rows.add(term)
        rows.update(_term_variants(term))
    return rows


def _action_inflection_variants(value: str) -> set[str]:
    text = normalize_string(value).casefold().strip(" .")
    if not text or not re.fullmatch(r"[a-z]+", text):
        return set()
    roots = {text}
    if text.endswith("ies") and len(text) > 4:
        roots.add(f"{text[:-3]}y")
    elif text.endswith("ied") and len(text) > 5:
        roots.add(f"{text[:-3]}y")
    elif text.endswith("ed") and len(text) > 4:
        roots.update(_past_tense_roots(text))
    elif text.endswith("es") and len(text) > 4:
        roots.add(text[:-2])
    elif text.endswith("s") and len(text) > 3:
        roots.add(text[:-1])
    variants: set[str] = set()
    for root in roots:
        variants.add(root)
        variants.add(f"{root}s")
        variants.add(_regular_ing(root))
    return variants


def _past_tense_roots(value: str) -> set[str]:
    root = normalize_string(value).casefold()[:-2]
    roots = {root} if root else set()
    if root and not root.endswith("e"):
        roots.add(f"{root}e")
    return roots


def _regular_ing(value: str) -> str:
    if value.endswith("ie"):
        return f"{value[:-2]}ying"
    if value.endswith("e") and not value.endswith(("ee", "oe", "ye")):
        return f"{value[:-1]}ing"
    if _ends_consonant_vowel_consonant(value):
        return f"{value}{value[-1]}ing"
    return f"{value}ing"


def _ends_consonant_vowel_consonant(value: str) -> bool:
    if len(value) < 3 or value[-1] in {"w", "x", "y"}:
        return False
    vowels = set("aeiou")
    return value[-3] not in vowels and value[-2] in vowels and value[-1] not in vowels


def _package_text(package: Any) -> str:
    values = [
        getattr(package, "proposal", None),
        getattr(package, "rendered_component_specs", None),
        getattr(package, "rendered_atlas_sources", None),
        getattr(package, "component_registry_preview", None),
        getattr(package, "project_brief_preview", None),
        getattr(package, "accepted_project_preview", None),
        getattr(package, "compass_memory_preview", None),
        getattr(package, "next_steps_preview", None),
        getattr(package, "backlog_result", None),
        getattr(package, "release_target_result", None),
        getattr(package, "release_assignment_result", None),
    ]
    return "\n".join(text_values(values))


def _rendered_artifact_text(package: Any) -> str:
    values = [
        getattr(package, "rendered_component_specs", None),
        getattr(package, "rendered_atlas_sources", None),
        getattr(package, "component_registry_preview", None),
        getattr(package, "project_brief_preview", None),
        getattr(package, "accepted_project_preview", None),
        getattr(package, "compass_memory_preview", None),
        getattr(package, "next_steps_preview", None),
        getattr(package, "backlog_result", None),
        getattr(package, "release_target_result", None),
        getattr(package, "release_assignment_result", None),
    ]
    return "\n".join(text_values(values))


def _words(value: str) -> list[str]:
    return [word for word in re.findall(r"[A-Za-z0-9][A-Za-z0-9'-]*", normalize_string(value)) if word]


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["greenfield_project_judgment_issues", "project_story_semantic_issues"]
