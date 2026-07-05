"""Structured narrative view for greenfield Registry component specs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from odylith.runtime.common.prose_grammar import looks_like_action_clause
from odylith.runtime.domain_intelligence.greenfield_component_terms import phrase_identity_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_text, visible_words


@dataclass(frozen=True)
class ComponentNarrativeView:
    """Component-local semantic view used by narrative spec rendering."""

    role: str
    owned_items: tuple[str, ...]
    accepted_items: tuple[str, ...]
    produced_items: tuple[str, ...]
    material_state_items: tuple[str, ...]
    blocker_state_items: tuple[str, ...]
    transition_items: tuple[str, ...]
    concrete_transition_items: tuple[str, ...]
    short_transition_items: tuple[str, ...]
    material_transition_count: int


@dataclass(frozen=True)
class _RoleProfile:
    role: str
    label_terms: frozenset[str]
    context_terms: frozenset[str]
    prefixes: tuple[str, ...] = ()
    bias: int = 0


_ROLE_PROFILES: tuple[_RoleProfile, ...] = (
    _RoleProfile("reference", frozenset({"catalog", "knowledge", "reference"}), frozenset()),
    _RoleProfile(
        "state_store",
        frozenset({"store", "repository", "record", "records", "profile", "registry", "history", "log", "logging", "tracking"}),
        frozenset({"persist", "saved", "stored"}),
    ),
    _RoleProfile(
        "evidence",
        frozenset({"audit", "evidence", "file", "ledger", "provenance", "trail"}),
        frozenset({"source", "replay", "retention", "version", "history", "attachment"}),
    ),
    _RoleProfile(
        "configuration",
        frozenset({"config", "configuration", "admin", "administrator", "policy", "setting"}),
        frozenset({"rule", "threshold", "template"}),
    ),
    _RoleProfile(
        "guardrail",
        frozenset({"safety", "stop", "recovery", "guard", "guardrail", "interlock", "limit", "override"}),
        frozenset({"unsafe", "invalid", "blocked"}),
    ),
    _RoleProfile(
        "validation",
        frozenset({"readiness", "validation", "verification", "check", "quality", "eligibility"}),
        frozenset({"validate", "validates", "validated", "complete", "completeness"}),
    ),
    _RoleProfile(
        "workflow",
        frozenset({"workflow", "sequence", "sequencer", "control", "controller", "runner", "scheduler", "coordination"}),
        frozenset({"ordered", "progress", "step", "handoff"}),
        prefixes=("orchestrat", "schedul"),
    ),
    _RoleProfile(
        "read_model",
        frozenset({"view", "timeline", "dashboard", "summary", "report", "export", "surface", "display", "history", "trend"}),
        frozenset({"render", "renders", "visible", "shown", "show"}),
    ),
    _RoleProfile(
        "decision",
        frozenset({"decision", "outcome", "reason", "approve", "approval", "decline", "explain", "rationale", "recommendation"}),
        frozenset({"qualified", "eligible", "accepted", "declined", "denied", "rejected"}),
    ),
    _RoleProfile(
        "calculation",
        frozenset({"compute", "calculation", "calculator", "engine", "score", "rank", "compare", "threshold", "ratio", "rule", "eligibility", "pricing"}),
        frozenset({"calculate", "calculated", "compute", "computed", "derive", "derived", "evaluate", "evaluated", "estimate", "number", "result"}),
        prefixes=("calculat", "comput", "evaluat"),
    ),
    _RoleProfile(
        "handoff",
        frozenset({"queue", "route", "routing", "handoff", "follow", "notification", "assignment", "case"}),
        frozenset({"next", "step", "downstream", "consumer"}),
    ),
    _RoleProfile(
        "entry",
        frozenset({"intake", "capture", "entry", "submit", "submitted", "upload", "log", "record", "draft"}),
        frozenset({"required", "field", "input", "command"}),
    ),
    _RoleProfile(
        "recovery",
        frozenset({"edit", "correction", "recover", "revision", "blocked", "blocker", "stale", "missing", "invalid"}),
        frozenset({"revise", "recoverable", "malformed"}),
    ),
    _RoleProfile(
        "integration",
        frozenset({"adapter", "provider", "external", "import", "feed", "integration", "sync"}),
        frozenset({"protocol", "translate", "source"}),
    ),
)

_FILLER_STATUS_TOKENS = frozenset(
    {
        "accepted",
        "confirmed",
        "needed",
        "received",
        "requested",
        "trusted",
        "visible",
    }
)

_LOW_SIGNAL_ITEMS = frozenset(
    {
        "blocker state",
        "blocked states",
        "correction marker",
        "handoff context",
        "next-step context",
        "reviewer explanation",
        "source evidence",
        "validation context",
    }
)

_NOUN_COMPATIBLE_ACTION_HEADS = frozenset(
    {"audit", "evidence", "input", "output", "proof", "record", "result", "review", "source", "state", "trace"}
)

_CONTEXTUAL_DUPLICATE_PREFIXES = frozenset({"scenario"})

_BOUNDARY_NOISE_TERMS = frozenset(
    {
        "adjacent",
        "approval",
        "boundary",
        "capture",
        "command",
        "component",
        "elsewhere",
        "forbidden",
        "guide",
        "local",
        "mutation",
        "original",
        "overwrite",
        "recovery",
        "release",
        "responsibilities",
        "runtime",
        "silent",
        "source",
        "truth",
        "upstream",
    }
)

_GENERATED_COMPONENT_SUFFIXES = frozenset(
    {"adapter", "client", "component", "engine", "queue", "service", "store", "surface", "system", "view"}
)

_MATERIAL_STATE_TERMS = frozenset(
    {
        "access",
        "attachment",
        "audit",
        "blocked",
        "blocker",
        "complete",
        "completeness",
        "consent",
        "correction",
        "deletion",
        "document",
        "evidence",
        "history",
        "invalid",
        "lifecycle",
        "missing",
        "permission",
        "privacy",
        "provenance",
        "recovery",
        "replay",
        "retention",
        "sensitive",
        "source",
        "status",
        "timeline",
        "traceable",
        "transition",
        "validated",
        "validation",
        "visible",
        "visibility",
    }
)

_TRANSITION_HIGH_TERMS = frozenset(
    {
        "accepted",
        "approved",
        "blocked",
        "closed",
        "completed",
        "corrected",
        "decided",
        "declined",
        "delivered",
        "denied",
        "eligible",
        "error",
        "failed",
        "final",
        "ineligible",
        "invalid",
        "missing",
        "published",
        "qualified",
        "received",
        "rejected",
        "returned",
        "revised",
        "scheduled",
        "sent",
        "stale",
    }
)

_TRANSITION_LOW_TERMS = frozenset({"created", "draft", "open", "ready", "reviewed", "started", "submitted"})


def component_narrative_view(
    *,
    label: str,
    owns: Sequence[str],
    accepts: Sequence[str],
    produces: Sequence[str],
    transitions: Sequence[str],
    outside: Sequence[str],
    proofs: Sequence[str],
) -> ComponentNarrativeView:
    """Derive the semantic view that the component spec renderer should narrate."""

    role = narrative_role(
        label=label,
        owns=owns,
        accepts=accepts,
        produces=produces,
        transitions=transitions,
        outside=outside,
        proofs=proofs,
    )
    owned_items = narrative_items(owns, limit=4)
    accepted_items = narrative_items(accepts, limit=3)
    produced_items = narrative_items(produces, limit=3)
    material_state_items = supplemental_state_items(owns, existing=owned_items, limit=5)
    blocker_state_items = supplemental_state_items(
        [*accepts, *produces],
        existing=(*owned_items, *accepted_items, *produced_items),
        limit=5,
    )
    transition_items = transition_narrative_items(transitions, limit=12)
    concrete_transition_items = tuple(
        row for row in transition_items if len(clean_text(row).split()) > 2 or "-" in clean_text(row)
    )
    short_transition_items = tuple(row for row in transition_items if len(clean_text(row).split()) <= 2)
    return ComponentNarrativeView(
        role=role,
        owned_items=owned_items,
        accepted_items=accepted_items,
        produced_items=produced_items,
        material_state_items=material_state_items,
        blocker_state_items=blocker_state_items,
        transition_items=transition_items,
        concrete_transition_items=concrete_transition_items,
        short_transition_items=short_transition_items,
        material_transition_count=sum(1 for row in transition_items if transition_material_score(row) >= 3),
    )


def narrative_role(
    *,
    label: str,
    owns: Sequence[str],
    accepts: Sequence[str],
    produces: Sequence[str],
    transitions: Sequence[str],
    outside: Sequence[str],
    proofs: Sequence[str],
) -> str:
    label_terms = _word_set(label)
    context_terms = _word_sequence([label, *owns, *accepts, *produces, *transitions, *outside, *proofs])
    best_label_role = "service"
    best_label_score = 0
    for profile in _ROLE_PROFILES:
        score = _profile_hits(label_terms, profile.label_terms, profile.prefixes)
        if score > best_label_score:
            best_label_role = profile.role
            best_label_score = score
    if best_label_score > 0:
        return best_label_role

    best_role = "service"
    best_score = 0
    for profile in _ROLE_PROFILES:
        score = profile.bias
        score += 2 * _profile_hits(context_terms, profile.label_terms | profile.context_terms, profile.prefixes)
        if score > best_score:
            best_role = profile.role
            best_score = score
    return best_role if best_score > 0 else "service"


def narrative_items(values: Sequence[str], *, limit: int, allow_status: bool = False) -> tuple[str, ...]:
    rows: list[str] = []
    material_values = [clean_text(value).strip(" .") for value in values if clean_text(value).strip(" .")]
    has_material_alternative = any(not generated_boundary_state_item(value) for value in material_values)
    for value in material_values:
        text = clean_text(value).strip(" .")
        if not text:
            continue
        lowered = text.casefold()
        if has_material_alternative and generated_boundary_state_item(text):
            continue
        if not allow_status and lowered in _FILLER_STATUS_TOKENS:
            continue
        if boundary_noise_item(lowered):
            continue
        if lowered in _LOW_SIGNAL_ITEMS:
            continue
        if action_led_state_noise_item(text):
            continue
        if contextual_duplicate_item(text, alternatives=material_values, selected=rows):
            continue
        if any(phrases_too_similar(text, existing) for existing in rows):
            continue
        rows.append(text)
        if len(rows) >= limit:
            break
    return tuple(rows)


def generated_boundary_state_item(value: str) -> bool:
    words = [word.casefold().strip(".,;:") for word in clean_text(value).split() if word.strip(".,;:")]
    if len(words) < 3 or len(words) > 9:
        return False
    return words[-1] == "state" and words[-2] in _GENERATED_COMPONENT_SUFFIXES


def boundary_noise_item(value: str) -> bool:
    terms = _word_set(value)
    return len(terms & _BOUNDARY_NOISE_TERMS) >= 2


def action_led_state_noise_item(value: str) -> bool:
    text = clean_text(value).strip(" .")
    if not text or not looks_like_action_clause(text):
        return False
    first = text.split(maxsplit=1)[0].casefold().strip(".,;:")
    return first not in _NOUN_COMPATIBLE_ACTION_HEADS


def contextual_duplicate_item(value: str, *, alternatives: Sequence[str], selected: Sequence[str]) -> bool:
    """Reject generated context-prefixed aliases when a real local item is present."""

    suffix = _contextual_suffix(value)
    if not suffix:
        return False
    candidates = [row for row in (*selected, *alternatives) if clean_text(row).casefold() != clean_text(value).casefold()]
    return any(_suffix_too_similar(suffix, candidate) for candidate in candidates)


def _contextual_suffix(value: str) -> str:
    words = [word.strip(".,;:") for word in clean_text(value).split() if word.strip(".,;:")]
    if len(words) < 3:
        return ""
    if words[0].casefold() not in _CONTEXTUAL_DUPLICATE_PREFIXES:
        return ""
    return " ".join(words[1:])


def _suffix_too_similar(suffix: str, candidate: str) -> bool:
    suffix_terms = phrase_identity_terms(clean_text(suffix).casefold())
    candidate_terms = phrase_identity_terms(clean_text(candidate).casefold())
    if len(suffix_terms) < 2 or not candidate_terms:
        return False
    return len(suffix_terms & candidate_terms) / max(1, len(suffix_terms)) >= 0.8


def supplemental_state_items(values: Sequence[str], *, existing: Sequence[str], limit: int) -> tuple[str, ...]:
    candidates: list[tuple[int, int, str]] = []
    for index, value in enumerate(values):
        text = clean_text(value).strip(" .")
        if not text:
            continue
        if any(phrases_too_similar(text, row) and not _materially_distinct_state_item(text, row) for row in existing):
            continue
        score = state_material_score(text)
        if score <= 0:
            continue
        candidates.append((score, index, text))
    candidates.sort(key=lambda row: (-row[0], row[1]))
    selected: list[tuple[int, int, str]] = []
    for _score, index, text in candidates:
        if any(
            phrases_too_similar(text, chosen) and not _materially_distinct_state_item(text, chosen)
            for _chosen_score, _chosen_index, chosen in selected
        ):
            continue
        selected.append((_score, index, text))
        if len(selected) >= limit:
            break
    return tuple(text for _score, _index, text in selected)


def _materially_distinct_state_item(value: str, other: str) -> bool:
    terms = _word_set(value)
    other_terms = _word_set(other)
    material_terms = terms & _MATERIAL_STATE_TERMS
    if not material_terms:
        return False
    return bool(material_terms - (other_terms & _MATERIAL_STATE_TERMS))


def transition_narrative_items(values: Sequence[str], *, limit: int) -> tuple[str, ...]:
    rows = narrative_items(values, limit=24, allow_status=True)
    if len(rows) <= limit:
        return rows
    selected: list[tuple[int, str]] = [(index, text) for index, text in enumerate(rows[: min(6, limit)])]
    for index, text in enumerate(rows[min(6, limit) :], start=min(6, limit)):
        if transition_material_score(text) <= 0:
            continue
        if any(phrases_too_similar(text, existing) for _existing_index, existing in selected):
            continue
        selected.append((index, text))
        if len(selected) >= limit:
            break
    if len(selected) < limit:
        for index, text in enumerate(rows):
            if any(index == existing_index or phrases_too_similar(text, existing) for existing_index, existing in selected):
                continue
            selected.append((index, text))
            if len(selected) >= limit:
                break
    return tuple(text for _index, text in sorted(selected))


def transition_material_score(value: str) -> int:
    terms = _word_set(value)
    return (3 if terms & _TRANSITION_HIGH_TERMS else 0) + (1 if terms & _TRANSITION_LOW_TERMS else 0)


def state_material_score(value: str) -> int:
    terms = _word_set(value)
    score = 0
    if terms & {"validation", "validated", "validates", "completeness", "complete"}:
        score += 3
    if terms & {"missing", "blocked", "blocker", "invalid", "correction", "recovery"}:
        score += 5
    if terms & {"provenance", "source", "evidence", "attachment", "uploaded", "document"}:
        score += 3
    if terms & {"access", "permission", "privacy", "sensitive", "retention", "deletion", "consent"}:
        score += 3
    if terms & {"lifecycle", "history", "timeline", "transition", "status"}:
        score += 2
    if terms & {"visibility", "visible", "reviewable", "audit", "traceable", "replay"}:
        score += 2
    if not score and terms & _MATERIAL_STATE_TERMS:
        score += 1
    return score


def phrases_too_similar(left: str, right: str) -> bool:
    left_terms = phrase_identity_terms(clean_text(left).casefold())
    right_terms = phrase_identity_terms(clean_text(right).casefold())
    if not left_terms or not right_terms:
        return False
    return len(left_terms & right_terms) / max(1, min(len(left_terms), len(right_terms))) >= 0.72


def _profile_hits(words: set[str], terms: frozenset[str], prefixes: tuple[str, ...]) -> int:
    direct_hits = len(words & terms)
    prefix_hits = sum(1 for word in words if any(word.startswith(prefix) for prefix in prefixes))
    return direct_hits + prefix_hits


def _word_set(value: str) -> set[str]:
    return set(_word_sequence([value]))


def _word_sequence(values: Sequence[str]) -> set[str]:
    words: set[str] = set()
    for value in values:
        for word in visible_words(clean_text(value).casefold().replace("-", " ")):
            token = word.casefold().strip(".,;:")
            if token:
                words.add(token)
    return words


__all__ = [
    "ComponentNarrativeView",
    "boundary_noise_item",
    "component_narrative_view",
    "contextual_duplicate_item",
    "generated_boundary_state_item",
    "narrative_items",
    "narrative_role",
    "phrases_too_similar",
    "state_material_score",
    "supplemental_state_items",
    "transition_material_score",
    "transition_narrative_items",
]
