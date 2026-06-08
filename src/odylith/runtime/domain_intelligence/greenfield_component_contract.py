"""Component-local contracts for confirmed greenfield governance records."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.prose_grammar import looks_like_finite_action
from odylith.runtime.domain_intelligence import greenfield_component_contract_profiles as contract_profiles
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    CONTRACT_KEYS,
    component_contract_issues,
    contract_is_complete,
    normalize_contract,
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_component_term_index import ordered_domain_terms
from odylith.runtime.domain_intelligence.greenfield_component_term_windows import literal_label_compounds
from odylith.runtime.domain_intelligence.greenfield_component_terms import natural_phrase
from odylith.runtime.domain_intelligence.greenfield_domain_term_index import ordered_terms
from odylith.runtime.domain_intelligence.greenfield_confirmed_text import domain_object_label as _domain_object_label
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_sentence
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import normalize_action_target_language
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_text import visible_words


_STATE_TERMS = {
    "accepted",
    "approved",
    "available",
    "blocked",
    "completed",
    "declined",
    "draft",
    "failed",
    "ready",
    "received",
    "recovered",
    "rejected",
    "reviewed",
    "scheduled",
    "sent",
    "stale",
    "submitted",
    "unavailable",
}


def ensure_component_contract(
    row: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any] | None = None,
    previous_label: str = "",
    next_label: str = "",
    workstream_title: str = "",
) -> dict[str, Any]:
    """Return a complete component-local ownership contract for one row."""

    existing = row.get("component_contract") if isinstance(row, Mapping) else None
    if isinstance(existing, Mapping):
        normalized = normalize_contract(existing)
        if contract_is_complete(normalized):
            return normalized
    return build_component_contract(
        row,
        proposal=proposal or {},
        previous_label=previous_label,
        next_label=next_label,
        workstream_title=workstream_title,
    )


def build_component_contract(
    row: Mapping[str, Any],
    *,
    proposal: Mapping[str, Any],
    previous_label: str = "",
    next_label: str = "",
    workstream_title: str = "",
) -> dict[str, Any]:
    """Build a deterministic, project-specific component contract."""

    label = _label(row)
    kind = _clean(row.get("kind"))
    state_object = _proposal_text(proposal, "state_object", "intent.state_object") or _clean(row.get("state_object"))
    first_path = _proposal_text(proposal, "first_path", "intent.first_path")
    proof_boundary = _proposal_text(proposal, "proof_boundary", "intent.proof_boundary")
    description = _component_description(row)
    local_context = _context_text(
        [
            label,
            description,
            _clean(row.get("boundary")),
            " ".join(text_values(row.get("interfaces"))),
            " ".join(text_values(row.get("validation"))),
            workstream_title,
        ]
    )
    context = _context_text(
        [
            _proposal_title(proposal),
            state_object,
            first_path,
            proof_boundary,
            description,
            _clean(row.get("boundary")),
            " ".join(text_values(row.get("interfaces"))),
            " ".join(text_values(row.get("validation"))),
            workstream_title,
        ]
    )
    state_label = _state_label(state_object, fallback=f"{_component_subject(label)} state")
    profile = _profile(label=label, kind=kind, context=context)
    if profile == "document_context":
        contract = contract_profiles.document_context_contract(
            label=label,
            state_label=state_label,
            context=local_context or context,
            previous_label=previous_label,
            next_label=next_label,
        )
    elif profile == "status_view":
        contract = contract_profiles.status_view_contract(
            label=label,
            state_label=state_label,
            context=context,
            previous_label=previous_label,
            next_label=next_label,
        )
    else:
        contract = _generic_contract(
            label=label,
            kind=kind,
            state_label=state_label,
            description=description,
            context=context,
            previous_label=previous_label,
            next_label=next_label,
        )
    return normalize_contract(contract)


def responsibility_from_contract(label: str, contract: Mapping[str, Any]) -> str:
    owned = _clause(contract.get("owned_state"))
    inputs = _clause(contract.get("accepted_inputs"))
    outputs = _clause(contract.get("produced_outputs"))
    failure = _clause(contract.get("unique_failure"))
    primary = _first_contract_item(owned)
    if _is_document_context(label, owned):
        return _sentence(
            f"Assembles context packets, accepts {inputs}, validates required evidence, protects sensitive context, and passes complete context to the next product step"
        )
    if _is_status_view(label, owned):
        return _sentence(
            f"Presents {_component_subject(label)}, review status, blocker context, and handoff evidence without rewriting source records"
        )
    subject = _component_subject(label)
    if primary and failure:
        if looks_like_finite_action(primary):
            return _sentence(
                f"{_lower_clause(primary)}, preserves reviewable evidence, and explains missing or stale inputs before handoff"
            )
        return _sentence(
            f"Maintains {_lower_clause(primary)}, preserves reviewable evidence, and explains missing or stale inputs before handoff"
        )
    if owned:
        return _sentence(f"Maintains {_lower_clause(primary or owned)} for {subject}")
    return _sentence(f"Maintains the {subject} state, recovery context, and local proof boundary")


def boundary_from_contract(label: str, contract: Mapping[str, Any]) -> str:
    owned = _clause(contract.get("owned_state"))
    primary = _boundary_primary(label, owned)
    return _sentence(f"{label} owns {_lower_clause(primary)}, validation evidence, and local handoff decisions")


def interfaces_from_contract(contract: Mapping[str, Any]) -> list[str]:
    return [
        _sentence(f"Accepts {contract.get('accepted_inputs')}"),
        _sentence(f"Produces {contract.get('produced_outputs')}"),
        _sentence(f"Renders, emits, or transitions {contract.get('states_or_transitions')}"),
    ]


def dependencies_from_contract(contract: Mapping[str, Any]) -> list[str]:
    return [
        _sentence(f"Upstream truth: {contract.get('upstream_truth')}"),
        _sentence(f"Downstream consumer: {contract.get('downstream_consumers')}"),
    ]


def validation_from_contract(contract: Mapping[str, Any]) -> list[str]:
    return [_sentence(item) for item in text_values(contract.get("local_proof")) if _clean(item)]


def risks_from_contract(label: str, contract: Mapping[str, Any]) -> list[str]:
    owned = _first_contract_item(_clause(contract.get("owned_state"))) or _component_subject(label)
    outside = _first_contract_item(_clause(contract.get("outside_boundary"))) or "adjacent product authority"
    return [
        _sentence(
            f"Domain risk: missing proof for {owned} can let blockers, recovery evidence, or next-step rules promote without behavior"
        ),
        _sentence(
            f"Security and policy posture: {label} must enforce access control, privacy, retention, and safety handling for {owned}, preserve recovery evidence, and prevent {outside} from silently changing local state"
        ),
    ]


def _generic_contract(
    *,
    label: str,
    kind: str,
    state_label: str,
    description: str,
    context: str,
    previous_label: str,
    next_label: str,
) -> dict[str, Any]:
    subject = _component_subject(label)
    verbs = _action_phrase(description, fallback=f"{subject} state and evidence")
    focus = _focus_phrase(label=label, description=description, context=context)
    states = _state_terms_from_context(context) or ("normal", "empty", "invalid-input", "blocked", "degraded", "recovered")
    upstream = previous_label or "accepted first-path input and state object"
    downstream = next_label or "the next product boundary and release proof review"
    interface_kind = "visible state" if kind.casefold() in {"client", "surface", "ui", "web"} else "command or event"
    input_focus = _accepted_input_focus(focus, kind=kind)
    evidence_reference = "source evidence reference" if re.search(r"\b(?:source|evidence|provenance|attachment|audit)\b", context, re.IGNORECASE) else "evidence reference"
    return {
        "owned_state": f"{focus}, local blockers, recovery state, {evidence_reference}, and next-step history for {state_label}",
        "accepted_inputs": f"{upstream}, authorized actor, prior state, and {input_focus}",
        "produced_outputs": f"{subject} {interface_kind} result, state update, blocked or recovery marker, explanation, and next-step context",
        "states_or_transitions": ", ".join(states),
        "outside_boundary": _outside_boundary(kind=kind),
        "local_proof": [
            f"{label} proves the happy path for {focus} with a visible result and persisted explanation.",
            f"{label} rejects or blocks invalid input covering {focus} before it creates a misleading result.",
            f"{label} exposes recovery context and next-step history for {focus}.",
        ],
        "upstream_truth": upstream,
        "downstream_consumers": downstream,
        "unique_failure": (
            f"{label} can make the product unsafe or misleading if input covering {focus} is incomplete, output is untraceable, "
            "or a blocker is hidden as a successful next step."
        ),
    }


def _accepted_input_focus(focus: str, *, kind: str) -> str:
    text = _clean(focus).strip(" .")
    if kind.casefold() not in {"client", "surface", "ui", "web"}:
        return text
    if re.match(r"^(?:candidate|visible)\b", text, flags=re.IGNORECASE):
        return text
    if re.match(r"^(?:ranked|ordered|selected|eligible|comparable)\b", text, flags=re.IGNORECASE):
        return f"candidate {text[:1].lower()}{text[1:]}"
    return text


def _profile(*, label: str, kind: str, context: str) -> str:
    focused = f"{label} {kind}".casefold()
    focused_words = set(ordered_terms(focused, minimum=1))
    text = f"{focused} {context}".casefold()
    if focused_words & {"document", "attachment", "upload", "packet", "file"} or "context handling" in focused:
        return "document_context"
    if focused_words & {"access", "permission", "rbac", "audit", "retention"}:
        return "generic"
    analytic_timeline = focused_words & {"correlation", "metric", "measurement", "activity", "overlay", "trend"}
    lifecycle_view = focused_words & {"status", "notification", "stale"} or "current owner" in focused
    lifecycle_timeline = focused_words & {"timeline", "history"} and bool(
        focused_words & {"status", "lifecycle", "notification", "audit", "owner", "readiness"}
    )
    if (lifecycle_view or lifecycle_timeline) and not analytic_timeline:
        return "status_view"
    if (
        "context" in focused_words
        and focused_words & {"handling", "handler", "bundle", "packet"}
        and any(token in text for token in ("document", "attachment", "packet", "upload", "file"))
    ):
        return "document_context"
    if (
        "view" in focused_words
        and any(token in text for token in ("status", "current owner", "notification", "stale"))
        and not analytic_timeline
    ):
        return "status_view"
    return "generic"


def _is_document_context(label: str, text: str) -> bool:
    focused = str(label or "").casefold()
    return any(token in focused for token in ("document", "attachment", "upload", "packet", "context"))


def _is_status_view(label: str, text: str) -> bool:
    focused = str(label or "").casefold()
    return any(token in focused for token in ("status", "timeline", "history"))


def _proposal_text(proposal: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        current: Any = proposal
        for part in key.split("."):
            if not isinstance(current, Mapping):
                current = None
                break
            current = current.get(part)
        text = _clean(current)
        if text:
            return text
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    for key in keys:
        text = _clean(intent.get(key))
        if text:
            return text
    return ""


def _proposal_title(proposal: Mapping[str, Any]) -> str:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    return _clean(intent.get("title")) or _clean(proposal.get("title"))


def _component_description(row: Mapping[str, Any]) -> str:
    parts = [
        _clean(row.get("source_system_description")),
        _clean(row.get("description")),
        _clean(row.get("responsibility")),
        _clean(row.get("boundary")),
    ]
    return ". ".join(part.strip(" .") for part in parts if part)


def _label(row: Mapping[str, Any]) -> str:
    return _clean(row.get("label")) or _clean(row.get("name")) or _clean(row.get("component_id")) or "Component"


def _state_label(value: str, *, fallback: str) -> str:
    text = _clean(value)
    if not text:
        return fallback
    shared_label = _domain_object_label(text, fallback="")
    if shared_label:
        return shared_label
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    match = re.search(
        r"\b(?:state\s+object\s+is|primary\s+state\s+object\s+is|core\s+state\s+object\s+is|is)\s+"
        r"(?:(?:the|an|a)\s+)?(?P<label>[^.;:]+)",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    match = re.search(
        r"^(?:the|an|a)\s+(?P<label>.+?)\s+(?:tracks|records|stores|moves|captures|keeps|contains)\b",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    if len(first.split()) <= 10:
        return first
    return fallback


def _state_terms_from_context(context: str) -> tuple[str, ...]:
    terms = []
    for token in visible_words(context):
        normalized = token.casefold()
        if normalized in _STATE_TERMS:
            terms.append(normalized)
    return tuple(unique_text(terms)[:8])


def _action_phrase(description: str, *, fallback: str) -> str:
    text = _clean(description).strip(" .")
    if not text:
        return fallback
    text = re.sub(r"\bowns\s+the\s+(.+?)\s+responsibility\s+and\s+keeps\s+it\s+tied\s+to\s+this\s+product\s+behavior:?\s*", r"\1 ", text, flags=re.IGNORECASE)
    text = re.sub(r"\brelevant\s+evidence\s*:\s*", "", text, flags=re.IGNORECASE)
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    if len(first.split()) > 22:
        first = " ".join(first.split()[:22]).rstrip(" ,;:")
    return first or fallback


def _focus_phrase(*, label: str, description: str, context: str) -> str:
    action_object = _action_object_phrase(description)
    action_object = _clean_focus_object(action_object)
    if action_object and not _generic_action_object(action_object):
        return action_object
    label_compounds = literal_label_compounds(label, noise_terms=set())
    if label_compounds:
        return ", ".join(label_compounds[:4])
    label_terms = _label_semantic_terms(label)
    if label_terms:
        return natural_phrase(label_terms[:4])
    terms = ordered_domain_terms(" ".join([label, _clean_focus_context(description), context]))
    if not terms:
        return _component_subject(label)
    return natural_phrase(terms[:5])


def _action_object_phrase(description: str) -> str:
    action = _action_phrase(description, fallback="")
    if not action:
        return ""
    visible = _visible_action_object(action)
    if visible:
        return visible
    text = re.sub(
        r"^(?:accepts?|assembles?|captures?|computes?|creates?|displays?|exposes?|forecasts?|handles?|helps?|imports?|issues?|keeps?|links?|maintains?|normalizes?|optimizes?|owns?|predicts?|produces?|pulls?|records?|renders?|shows?|stores?|tracks?|validates?)\s+",
        "",
        action,
        flags=re.IGNORECASE,
    ).strip(" .")
    text = re.sub(r"^(?:which|what)\s+", "", text, flags=re.IGNORECASE).strip(" .")
    words = text.split()
    if len(words) > 18:
        text = " ".join(words[:18]).rstrip(" ,;:")
    text = _clean_focus_object(text)
    return "" if _generic_action_object(text) else text


def _clean_focus_object(value: str) -> str:
    text = normalize_action_target_language(_clean(value)).strip(" .")
    text = re.sub(
        r"\b(?:captures?|capturing)\s+user\s+actions?\b",
        "product interaction",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:explains?|explaining)\s+blocked\s+states?\b",
        "missing or invalid information",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\s*(?:,?\s*and\s+)?(?:keeps?|keeping)\s+the\s+next\s+visible\s+step\s+tied\s+to\s*:\s*[^.]+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\b(?:user\s+actions?|next[- ]step\s+context)\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"(?:,\s*){2,}", ", ", text)
    text = re.sub(r"^\s*(?:and|or|,)+\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*(?:and|or|,)+\s*$", "", text, flags=re.IGNORECASE)
    return _clean(text).strip(" .,;:")


def _clean_focus_context(value: str) -> str:
    text = _clean_focus_object(value)
    if _generic_action_object(text):
        return ""
    return text


def _visible_action_object(action: str) -> str:
    match = re.match(
        r"^(?:shows?|displays?|renders?)\s+(?:which|what)\s+(?P<object>[a-z0-9][a-z0-9 -]{1,80}?)\s+"
        r"(?:can|are|is|has|have)\b(?P<rest>.*)$",
        _clean(action).casefold(),
    )
    if not match:
        return ""
    object_phrase = _singular_phrase(match.group("object"))
    rest = match.group("rest")
    if any(token in rest for token in ("available", "unavailable", "blocked", "borrowed", "reserved")):
        return f"{object_phrase} availability, unavailable state, and blocking reason"
    return f"{object_phrase} visibility and allowed action state"


def _generic_action_object(text: str) -> bool:
    lowered = _clean(text).casefold()
    if not lowered:
        return True
    if re.search(r"\btied\s+to\s*:", lowered):
        return True
    if re.search(r"\b(?:user\s+actions?|blocked\s+states?|next[- ]step\s+context)\b", lowered):
        return True
    generic_markers = (
        "inputs, state changes, outputs",
        "this product behavior",
        "input, state change, output",
        "review evidence",
    )
    return any(marker in lowered for marker in generic_markers)


def _singular_phrase(value: str) -> str:
    words = _clean(value).casefold().split()
    if not words:
        return "item"
    last = words[-1]
    if last.endswith("ies") and len(last) > 3:
        words[-1] = f"{last[:-3]}y"
    elif last.endswith("s") and not last.endswith("ss") and len(last) > 3:
        words[-1] = last[:-1]
    return " ".join(words)


def _label_semantic_terms(label: str) -> tuple[str, ...]:
    text = _clean(label).casefold()
    terms: list[str] = []
    if any(token in text for token in ("intake", "submission", "submitted")):
        terms.extend(["submitted request", "source observation", "intake status", "contact route"])
    if any(token in text for token in ("review", "quality", "eligibility")):
        terms.extend(["quality rule", "uncertainty check", "reviewer note", "blocking reason"])
    if any(token in text for token in ("ledger", "record", "history", "trail")):
        terms.extend(["timestamped entry", "version history", "reviewer rationale", "audit replay"])
    if any(token in text for token in ("publication", "publish", "result")):
        terms.extend(["published result", "final status", "caveat", "supporting link"])
    if any(token in text for token in ("queue", "assignment", "escalation")):
        terms.extend(["assignment", "queue state", "escalation owner", "blocked item"])
    if any(token in text for token in ("matching", "routing")):
        terms.extend(["candidate match", "fit signal", "capacity signal", "routing choice"])
    if any(token in text for token in ("notification", "freshness")):
        terms.extend(["delivery marker", "freshness check", "recipient role", "retry state"])
    return tuple(terms)


def _outside_boundary(*, kind: str) -> str:
    if kind.casefold() in {"client", "surface", "ui", "web"}:
        return "domain derivation, persistence, original input facts, and release approval unless a later plan assigns them here"
    if kind.casefold() == "adapter":
        return "original input facts, product decisions, and release approval"
    return "original input facts, adjacent product decisions, and release approval unless explicitly assigned"


def _component_subject(label: str) -> str:
    text = _clean(label)
    text = re.sub(r"\b(surface|service|adapter|engine|view|workspace|component)\b", "", text, flags=re.IGNORECASE)
    return _clean(text).casefold() or "component"


def _context_text(values: Sequence[str]) -> str:
    return ". ".join(_clean(value).strip(" .") for value in values if _clean(value))


def _clean(value: Any) -> str:
    return clean_artifact_text(value)


def _sentence(value: Any) -> str:
    return clean_artifact_sentence(value)


def _clause(value: Any) -> str:
    return _clean(value).strip(" .")


def _lower_clause(value: str) -> str:
    text = _clause(value)
    return text[:1].lower() + text[1:] if text else ""


def _first_contract_item(value: str) -> str:
    text = _clause(value)
    if not text:
        return ""
    segment = re.split(r",|;", text, maxsplit=1)[0]
    segment = re.sub(r"^(?:and|or)\s+", "", segment, flags=re.IGNORECASE).strip(" .")
    return segment


def _boundary_primary(label: str, owned: str) -> str:
    subject = _component_subject(label)
    items = [part.strip(" .") for part in re.split(r",|;", _clause(owned)) if part.strip(" .")]
    subject_terms = set(ordered_domain_terms(subject))
    for item in items:
        if subject_terms and not (set(ordered_domain_terms(item)) & subject_terms):
            continue
        if re.match(r"^(?:user|actor|customer|client)\s+\w+", item, flags=re.IGNORECASE):
            continue
        if item.casefold() in {"source evidence", "blocker state", "next-step context"}:
            continue
        return item
    for item in items:
        if re.match(r"^(?:user|actor|customer|client)\s+\w+", item, flags=re.IGNORECASE):
            continue
        if item.casefold() in {"source evidence", "blocker state", "next-step context"}:
            continue
        return item
    return f"{subject} state"


__all__ = [
    "CONTRACT_KEYS",
    "boundary_from_contract",
    "component_contract_issues",
    "dependencies_from_contract",
    "ensure_component_contract",
    "interfaces_from_contract",
    "public_prose_quality_issues",
    "rendered_component_spec_quality_issues",
    "responsibility_from_contract",
    "risks_from_contract",
    "validation_from_contract",
]
