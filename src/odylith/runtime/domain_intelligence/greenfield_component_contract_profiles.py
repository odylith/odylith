"""Specialized component contract profiles for generated Registry specs."""

from __future__ import annotations

import re
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_domain_term_index import label_terms
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_text
from odylith.runtime.domain_intelligence.greenfield_text import unique_text


def document_context_contract(
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


def status_view_contract(
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


def _object_phrase(value: str) -> str:
    text = _clean(value).casefold().replace("_", " ")
    if not text:
        return "domain record"
    words = label_terms(text, stopwords={"the", "primary", "core"})
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


def _clean(value: Any) -> str:
    return clean_artifact_text(value)


__all__ = ["document_context_contract", "status_view_contract"]
