from __future__ import annotations

from typing import Any
from typing import Mapping
from typing import Sequence


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalize_token(value: Any) -> str:
    return _normalize_string(value).lower().replace("-", "_").replace(" ", "_")


def _sequence_count(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len([item for item in value if _normalize_string(item)])
    return 1 if _normalize_string(value) else 0


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        return value.get(name)
    return getattr(value, name, None)


def _count_phrase(count: int, singular: str, plural: str | None = None) -> str:
    noun = singular if count == 1 else (plural or f"{singular}s")
    return f"{count} {noun}"


def _join_phrases(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]}, then {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def _join_items(parts: Sequence[str]) -> str:
    filtered = [_normalize_string(part) for part in parts if _normalize_string(part)]
    if not filtered:
        return ""
    if len(filtered) == 1:
        return filtered[0]
    if len(filtered) == 2:
        return f"{filtered[0]} and {filtered[1]}"
    return ", ".join(filtered[:-1]) + f", and {filtered[-1]}"


def _suppressed_payload(
    *,
    metrics: Mapping[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "eligible": False,
        "style": "",
        "label": "Odylith assist:",
        "preferred_markdown_label": "**Odylith assist:**",
        "text": "",
        "plain_text": "",
        "markdown_text": "",
        "user_win": "",
        "delta": "",
        "proof": "",
        "suppressed_reason": reason,
        "metrics": dict(metrics),
    }


def _evidence_metrics(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_path_count = _sequence_count(_field(request, "candidate_paths"))
    claimed_path_count = _sequence_count(_field(request, "claimed_paths"))
    workstream_count = _sequence_count(_field(request, "workstreams"))
    component_count = _sequence_count(_field(request, "components"))
    validation_count = _sequence_count(_field(request, "validation_commands"))
    delegated_leaf_count = _sequence_count(_field(decision, "subtasks"))
    main_thread_followup_count = _sequence_count(_field(decision, "main_thread_followups"))
    grounded = bool(adoption.get("grounded"))
    route_ready = bool(adoption.get("route_ready"))
    grounded_delegate = bool(adoption.get("grounded_delegate"))
    requires_widening = bool(adoption.get("requires_widening"))
    return {
        "candidate_path_count": candidate_path_count,
        "claimed_path_count": claimed_path_count,
        "focus_path_count": candidate_path_count or claimed_path_count,
        "workstream_count": workstream_count,
        "component_count": component_count,
        "governance_anchor_count": workstream_count + component_count,
        "validation_count": validation_count,
        "delegated_leaf_count": delegated_leaf_count,
        "main_thread_followup_count": main_thread_followup_count,
        "grounded": grounded,
        "route_ready": route_ready,
        "grounded_delegate": grounded_delegate,
        "requires_widening": requires_widening,
        "mode": _normalize_token(_field(decision, "mode")),
    }


def compose_closeout_assist(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
) -> dict[str, Any]:
    metrics = _evidence_metrics(request=request, decision=decision, adoption=adoption)
    if not metrics["grounded"]:
        return _suppressed_payload(metrics=metrics, reason="not_grounded")
    if metrics["requires_widening"]:
        return _suppressed_payload(metrics=metrics, reason="requires_widening")
    if not metrics["route_ready"] and not metrics["grounded_delegate"]:
        return _suppressed_payload(metrics=metrics, reason="not_route_ready")

    markdown_label = "**Odylith assist:**"
    plain_label = "Odylith assist:"
    odylith_off_token_markdown = "`odylith_off`"
    odylith_off_token_plain = "odylith_off"

    focus_phrase = ""
    if metrics["focus_path_count"] > 0:
        focus_phrase = _count_phrase(metrics["focus_path_count"], "candidate path")
    governance_bits: list[str] = []
    if metrics["workstream_count"] > 0:
        governance_bits.append(_count_phrase(metrics["workstream_count"], "workstream"))
    if metrics["component_count"] > 0:
        governance_bits.append(_count_phrase(metrics["component_count"], "component"))
    governance_phrase = _join_items(governance_bits)
    validation_phrase = (
        _count_phrase(metrics["validation_count"], "focused check")
        if metrics["validation_count"] > 0
        else ""
    )
    leaf_phrase = (
        _count_phrase(metrics["delegated_leaf_count"], "bounded leaf", "bounded leaves")
        if metrics["delegated_leaf_count"] > 0
        else ""
    )

    style = ""
    user_win = ""
    delta_markdown = ""
    delta_plain = ""
    proof_parts: list[str] = []

    if metrics["grounded_delegate"] and metrics["delegated_leaf_count"] > 0 and focus_phrase:
        style = "grounded_bounded_execution"
        user_win = "kept the work moving"
        delta_markdown = f"without the usual broader {odylith_off_token_markdown} hunt"
        delta_plain = f"without the usual broader {odylith_off_token_plain} hunt"
        proof_parts.append(f"keeping the slice to {focus_phrase}")
        proof_parts.append(f"routing {leaf_phrase}")
        if validation_phrase:
            proof_parts.append(f"finishing with {validation_phrase}")
    elif governance_phrase:
        style = "governed_lane"
        user_win = "kept this change in the right governed lane"
        delta_markdown = "instead of a broader unguided repo hunt"
        delta_plain = delta_markdown
        proof_parts.append(f"reusing {governance_phrase}")
        if validation_phrase:
            proof_parts.append(f"finishing with {validation_phrase}")
        elif focus_phrase:
            proof_parts.append(f"keeping the slice to {focus_phrase}")
    elif focus_phrase:
        style = "shortest_safe_path"
        user_win = "kept this on the shortest safe path"
        delta_markdown = f"instead of an {odylith_off_token_markdown}-style broader repo sweep"
        delta_plain = f"instead of an {odylith_off_token_plain}-style broader repo sweep"
        proof_parts.append(f"grounding the work to {focus_phrase}")
        if validation_phrase:
            proof_parts.append(f"finishing with {validation_phrase}")
    elif validation_phrase:
        style = "focused_validation"
        user_win = "kept this from turning into a broader unguided repo hunt"
        delta_markdown = ""
        delta_plain = ""
        proof_parts.append(f"finishing with {validation_phrase}")

    proof = _join_phrases(proof_parts)
    if not style or not proof:
        return _suppressed_payload(metrics=metrics, reason="missing_user_facing_delta")

    markdown_text = f"{markdown_label} {user_win}"
    plain_text = f"{plain_label} {user_win}"
    if delta_markdown:
        markdown_text += f" {delta_markdown}"
    if delta_plain:
        plain_text += f" {delta_plain}"
    markdown_text += f" by {proof}."
    plain_text += f" by {proof.replace(odylith_off_token_markdown, odylith_off_token_plain)}."

    return {
        "eligible": True,
        "style": style,
        "label": plain_label,
        "preferred_markdown_label": markdown_label,
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "user_win": user_win,
        "delta": delta_markdown,
        "proof": proof,
        "suppressed_reason": "",
        "metrics": metrics,
    }
