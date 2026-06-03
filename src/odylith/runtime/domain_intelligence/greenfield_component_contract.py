"""Component-local contracts for confirmed greenfield governance records."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import (
    CONTRACT_KEYS,
    component_contract_issues,
    contract_is_complete,
    normalize_contract,
    ordered_domain_terms,
    public_prose_quality_issues,
    rendered_component_spec_quality_issues,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


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
        contract = _document_context_contract(
            label=label,
            state_label=state_label,
            context=local_context or context,
            previous_label=previous_label,
            next_label=next_label,
        )
    elif profile == "status_view":
        contract = _status_view_contract(
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
            f"Maintains {_lower_clause(owned)} and produces {_lower_clause(outputs)}"
        )
    subject = _component_subject(label)
    if primary and failure:
        return _sentence(f"Maintains {_lower_clause(primary)}. Failure avoided: {_lower_clause(failure)}")
    if owned:
        return _sentence(f"Maintains {_lower_clause(primary or owned)} for {subject}")
    return _sentence(f"Maintains the {subject} state, recovery context, and local proof boundary")


def boundary_from_contract(label: str, contract: Mapping[str, Any]) -> str:
    owned = _clause(contract.get("owned_state"))
    primary = _first_contract_item(owned) or f"{_component_subject(label)} state"
    return _sentence(
        f"{label} owns a {_lower_clause(primary)} boundary; accepted inputs, produced outputs, transitions, and refusals stay as separate contract fields"
    )


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


def _document_context_contract(
    *,
    label: str,
    state_label: str,
    context: str,
    previous_label: str,
    next_label: str,
) -> dict[str, Any]:
    object_name = _object_phrase(state_label)
    packet = _packet_phrase(context, object_name=object_name)
    object_base = _object_base(object_name)
    identity = _identity_phrase(context, object_name=object_name)
    context_label = _context_label(context, object_name=object_name)
    reason = _reason_phrase(context)
    docs = _document_phrase(context)
    required_docs = _required_document_phrase(docs)
    upload_docs = _uploaded_document_phrase(docs)
    missing = _missing_document_phrase(context)
    sensitive = _sensitive_material_phrase(context)
    recipient = _recipient_actor(context)
    downstream = next_label or _downstream_from_context(context, fallback="lifecycle tracking")
    outside = _document_outside_boundary(context)
    local_proof = _document_local_proof(
        object_base=object_base,
        context_label=context_label,
        docs=docs,
        missing=missing,
        sensitive=sensitive,
        recipient=recipient,
    )
    return {
        "owned_state": (
            f"{packet} creation, {identity} attachment, {reason} capture, {required_docs} completeness, uploaded {upload_docs} "
            f"validation, {missing} states, {context_label} provenance, sensitive access control, and lifecycle history"
        ),
        "accepted_inputs": (
            f"{identity}, source actor, {reason}, urgency, {required_docs} selections, uploaded files, provenance notes, "
            f"and access actor from {previous_label or 'the intake workspace'}"
        ),
        "produced_outputs": (
            f"validated {packet}, {missing} blockers, uploaded-context metadata, access decisions, and handoff context for {downstream}"
        ),
        "states_or_transitions": (
            f"no-context, incomplete, missing-required-{_state_token(docs)}, {missing} blocking, uploaded, validation-failed, access-restricted, ready-for-review, "
            f"and made available to {downstream}"
        ),
        "outside_boundary": outside,
        "local_proof": local_proof,
        "upstream_truth": previous_label or f"{object_base} creation and intake workspace",
        "downstream_consumers": downstream,
        "unique_failure": (
            f"{context_label.capitalize()} can be attached to the wrong {object_base}, missing required {docs} can pass as complete, "
            f"or unauthorized users can view or mutate {sensitive}."
        ),
    }


def _status_view_contract(
    *,
    label: str,
    state_label: str,
    context: str,
    previous_label: str,
    next_label: str,
) -> dict[str, Any]:
    transitions = _status_transitions(context)
    object_name = _object_phrase(state_label)
    object_base = _status_object_base(context, object_name=object_name)
    timeline = f"{object_base} status timeline"
    role_scope = _role_scope_phrase(context)
    stale_indicator = f"stale or blocked {object_base} indicators"
    upstream = previous_label or _upstream_from_context(context, fallback=f"{object_base} lifecycle tracking")
    local_proof = _status_local_proof(object_base=object_base, role_scope=role_scope, stale_indicator=stale_indicator)
    return {
        "owned_state": (
            f"{timeline}, current next-action owner, {role_scope}, transition history, blocked or stale indicators, "
            "notification freshness marker, and audit trail"
        ),
        "accepted_inputs": (
            f"lifecycle events, actor identity, source timestamps, notification delivery markers, role context, and outcome updates from {upstream}"
        ),
        "produced_outputs": (
            f"role-appropriate status views, current owner, transition-validation display, {stale_indicator}, and audit history entries"
        ),
        "states_or_transitions": ", ".join(transitions),
        "outside_boundary": _status_outside_boundary(context, object_base=object_base),
        "local_proof": local_proof,
        "upstream_truth": upstream,
        "downstream_consumers": next_label or _status_downstream_consumers(context),
        "unique_failure": (
            f"An invalid transition can look valid, the wrong role can see private status, a stale or blocked {object_base} can look healthy, "
            "or status history can lose its source event."
        ),
    }


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
    focused_words = _word_set(focused)
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
    first = re.split(r"[.;]", text, maxsplit=1)[0].strip(" .")
    match = re.search(
        r"\b(?:state\s+object\s+is|primary\s+state\s+object\s+is|core\s+state\s+object\s+is|is)\s+(?:a|an|the)?\s*(?P<label>[^.;:]+)",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    match = re.search(
        r"^(?:a|an|the)\s+(?P<label>.+?)\s+(?:tracks|records|stores|moves|captures|keeps|contains)\b",
        first,
        re.IGNORECASE,
    )
    if match:
        return _clean(match.group("label")).strip(" .") or fallback
    if len(first.split()) <= 10:
        return first
    return fallback


def _object_phrase(value: str) -> str:
    text = _clean(value).casefold()
    if not text:
        return "domain record"
    words = [word for word in re.findall(r"[A-Za-z0-9-]+", text) if word not in {"the", "primary", "core"}]
    return " ".join(words[:4]) or "domain record"


def _object_base(object_name: str) -> str:
    words = [
        word
        for word in _clean(object_name).casefold().split()
        if word not in {"record", "file", "case", "item", "profile", "object"}
    ]
    return " ".join(words[:3]) or _clean(object_name).casefold() or "domain item"


def _packet_phrase(context: str, *, object_name: str) -> str:
    lowered = context.casefold()
    packet = _context_packet_phrase(lowered)
    if packet:
        return packet
    return f"{object_name} context bundle"


def _context_packet_phrase(lowered_context: str) -> str:
    for pattern in (
        r"\b([a-z][a-z-]+)\s+packets?\b",
        r"\b([a-z][a-z-]+)\s+evidence\s+packets?\b",
    ):
        for match in re.finditer(pattern, lowered_context):
            subject = match.group(1)
            if subject in {"a", "an", "the"}:
                continue
            if "evidence packet" in match.group(0):
                return f"{subject} evidence packet"
            return f"{subject} packet"
    return ""


def _identity_phrase(context: str, *, object_name: str) -> str:
    lowered = context.casefold()
    match = re.search(r"\b(?P<identity>[a-z][a-z-]+\s+identity)\b", lowered)
    if match:
        return match.group("identity")
    return f"{_object_base(object_name)} identity"


def _context_label(context: str, *, object_name: str) -> str:
    lowered = context.casefold()
    for match in re.finditer(r"\b(?P<context>[a-z][a-z-]+\s+context)\b", lowered):
        subject = match.group("context").split()[0]
        if subject in {"and", "or", "the", "a", "an"}:
            continue
        return match.group("context")
    return f"{_object_base(object_name)} context"


def _reason_phrase(context: str) -> str:
    lowered = context.casefold()
    match = re.search(r"\b(?P<reason>[a-z][a-z-]+\s+reason)\b", lowered)
    if match:
        return match.group("reason")
    if "reason" in lowered:
        return "domain reason"
    return "submission rationale"


def _document_phrase(context: str) -> str:
    lowered = context.casefold()
    if "documentation" in lowered:
        return "documentation"
    if "document" in lowered:
        return "document"
    if "evidence" in lowered:
        return "evidence"
    return "context material"


def _missing_document_phrase(context: str) -> str:
    docs = _document_phrase(context)
    if docs == "document":
        return "missing document"
    if docs == "documentation":
        return "missing document"
    if docs == "evidence":
        return "missing evidence"
    return "missing required context"


def _required_document_phrase(docs: str) -> str:
    if docs in {"documentation", "document", "evidence"}:
        return f"required {docs}"
    return f"required {docs}"


def _uploaded_document_phrase(docs: str) -> str:
    if docs == "documentation":
        return "document"
    return docs


def _sensitive_material_phrase(context: str) -> str:
    lowered = context.casefold()
    match = re.search(r"\b(?P<materials>sensitive\s+[a-z][a-z-]+\s+materials?)\b", lowered)
    if match:
        return match.group("materials")
    if "private" in lowered or "sensitive" in lowered:
        return "sensitive materials"
    return "sensitive context materials"


def _recipient_actor(context: str) -> str:
    lowered = context.casefold()
    for pattern in (
        r"\b(destination\s+[a-z][a-z-]+)\b",
        r"\b(approving\s+[a-z][a-z-]+)\b",
        r"\b(reviewing\s+[a-z][a-z-]+)\b",
    ):
        match = re.search(pattern, lowered)
        if match:
            return match.group(1)
    return "downstream actor"


def _document_outside_boundary(context: str) -> str:
    lowered = context.casefold()
    outside = [
        "sibling product responsibilities",
        "downstream decision ownership",
        "status or lifecycle state",
        "original input facts",
        "release approval",
    ]
    if "scheduling" in lowered or "scheduled" in lowered:
        outside.insert(3, "scheduling outcome")
    return ", ".join(outside)


def _document_local_proof(
    *,
    object_base: str,
    context_label: str,
    docs: str,
    missing: str,
    sensitive: str,
    recipient: str,
) -> list[str]:
    return [
        f"User can attach required {context_label} to the correct {object_base}.",
        f"{missing.capitalize()} blocks submission.",
        f"Uploaded context remains associated with the correct {object_base}.",
        f"Unauthorized users cannot view or mutate {context_label}.",
        f"{recipient.capitalize()} can see the {context_label} needed to complete local review or request more information.",
    ]


def _state_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", _clean(value).casefold()).strip("-") or "context"


def _status_transitions(context: str) -> list[str]:
    lowered = context.casefold()
    rows: list[str] = []
    rules = (
        ("draft", "draft"),
        ("create", "draft"),
        ("sent", "sent"),
        ("send", "sent"),
        ("receiv", "received"),
        ("accept", "accepted"),
        ("declin", "declined"),
        ("more information", "more-info-requested"),
        ("more-info", "more-info-requested"),
        ("schedule", "scheduled"),
        ("complete", "completed"),
        ("block", "blocked"),
        ("stale", "stale"),
    )
    for needle, label in rules:
        if needle in lowered:
            rows.append(label)
    defaults = ["draft", "submitted", "in-review", "blocked", "accepted", "rejected", "completed"]
    return list(unique_text(rows or defaults))


def _status_object_base(context: str, *, object_name: str) -> str:
    lowered = context.casefold()
    for pattern in (
        r"\b([a-z][a-z-]+)\s+status\s+timeline\b",
        r"\b([a-z][a-z-]+)\s+lifecycle\b",
    ):
        match = re.search(pattern, lowered)
        if match:
            return match.group(1)
    return _object_base(object_name)


def _role_scope_phrase(context: str) -> str:
    lowered = context.casefold()
    match = re.search(r"\b(?P<scope>role-(?:appropriate|specific)\s+[a-z][a-z-]+\s+visibility)\b", lowered)
    if match:
        return match.group("scope").replace("role-appropriate", "role-specific")
    return "role-specific actor visibility"


def _status_local_proof(*, object_base: str, role_scope: str, stale_indicator: str) -> list[str]:
    return [
        f"Valid {object_base} transitions are displayed correctly.",
        "Invalid transitions are rejected or hidden.",
        f"{role_scope.capitalize()} is enforced.",
        f"{stale_indicator.capitalize()} are visible.",
        "Status history is traceable to source events.",
    ]


def _status_outside_boundary(context: str, *, object_base: str) -> str:
    rows = [f"{object_base} creation", "matching or context validation", "notification delivery", "final release approval"]
    return ", ".join(rows)


def _status_downstream_consumers(context: str) -> str:
    return "authorized status viewers and release proof review"


def _state_terms_from_context(context: str) -> tuple[str, ...]:
    terms = []
    for token in re.findall(r"\b(?:draft|submitted|sent|received|accepted|declined|blocked|stale|scheduled|completed|reviewed|approved|rejected|ready|unavailable|available|failed|recovered)\b", context.casefold()):
        terms.append(token)
    return tuple(unique_text(terms)[:8])


def _upstream_from_context(context: str, *, fallback: str) -> str:
    lowered = context.casefold()
    lifecycle = _lifecycle_tracking_phrase(lowered)
    if lifecycle:
        return lifecycle
    if "lifecycle" in lowered:
        return "lifecycle tracking"
    if "intake" in lowered:
        return "intake workspace"
    return fallback


def _downstream_from_context(context: str, *, fallback: str) -> str:
    lowered = context.casefold()
    lifecycle = _lifecycle_tracking_phrase(lowered)
    if lifecycle:
        return lifecycle
    if "lifecycle" in lowered:
        return "lifecycle tracking"
    if "status" in lowered:
        return "status view"
    return fallback


def _lifecycle_tracking_phrase(lowered_context: str) -> str:
    match = re.search(r"\b([a-z][a-z-]+)\s+lifecycle\s+tracking\b", lowered_context)
    return match.group(0) if match else ""


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
    label_compounds = _label_compound_focus(label)
    if label_compounds:
        return ", ".join(label_compounds[:4])
    label_terms = _label_semantic_terms(label)
    if label_terms:
        return _term_phrase(label_terms[:4])
    terms = ordered_domain_terms(" ".join([label, _clean_focus_context(description), context]))
    if not terms:
        return _component_subject(label)
    return _term_phrase(terms[:5])


def _label_compound_focus(label: str) -> list[str]:
    terms = _literal_label_terms(label)
    rows: list[str] = []
    for index in range(max(0, len(terms) - 1)):
        left = terms[index]
        right = terms[index + 1]
        if left == right:
            continue
        rows.append(f"{left} {right}")
    return unique_text(rows)


def _literal_label_terms(label: str) -> list[str]:
    drop = {
        "adapter",
        "and",
        "client",
        "component",
        "engine",
        "for",
        "in",
        "of",
        "on",
        "service",
        "store",
        "surface",
        "system",
        "the",
        "to",
        "view",
        "with",
        "workspace",
    }
    return [
        word
        for word in re.findall(r"[a-z0-9][a-z0-9'-]*", _clean(label).casefold())
        if word not in drop
    ]


def _action_object_phrase(description: str) -> str:
    action = _action_phrase(description, fallback="")
    if not action:
        return ""
    visible = _visible_action_object(action)
    if visible:
        return visible
    text = re.sub(
        r"^(?:accepts?|assembles?|captures?|creates?|displays?|exposes?|handles?|helps?|imports?|keeps?|links?|maintains?|owns?|produces?|records?|renders?|shows?|stores?|tracks?|validates?)\s+",
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
    text = _clean(value).strip(" .")
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


def _term_phrase(terms: Sequence[str]) -> str:
    rows = [str(term or "").strip() for term in terms if str(term or "").strip()]
    if not rows:
        return ""
    if len(rows) == 1:
        return rows[0]
    if len(rows) == 2:
        return f"{rows[0]} and {rows[1]}"
    return f"{', '.join(rows[:-1])}, and {rows[-1]}"


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
        return "original input facts, product decisions, presentation, and release approval"
    return "presentation, original input facts, adjacent product decisions, and release approval unless explicitly assigned"


def _component_subject(label: str) -> str:
    text = _clean(label)
    text = re.sub(r"\b(surface|service|adapter|engine|view|workspace|component)\b", "", text, flags=re.IGNORECASE)
    return _clean(text).casefold() or "component"


def _context_text(values: Sequence[str]) -> str:
    return ". ".join(_clean(value).strip(" .") for value in values if _clean(value))


def _clean(value: Any) -> str:
    text = clean_text(value).replace("`", "")
    text = re.sub(r"\s+([,.;:?!])", r"\1", text)
    return re.sub(r"\s+", " ", text).strip()


def _sentence(value: Any) -> str:
    text = _clean(value).strip(" .")
    if not text:
        return ""
    return text[:1].upper() + text[1:] + "."


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


def _word_set(text: str) -> set[str]:
    return {word for word in re.findall(r"[a-z0-9][a-z0-9_-]*", _clean(text).casefold()) if word}


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
