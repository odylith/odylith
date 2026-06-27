"""Schema-constrained repair planning for Tribunal callers.

Tribunal patch planning is a custody boundary, not a renderer. Callers provide
typed findings and an existing patch request. The optional reasoning provider
may fill replacement facts and decision-ledger details, but it may not invent
new targets or rewrite rendered artifacts.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_string_list
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.reasoning import odylith_reasoning


TRIBUNAL_PATCH_PLAN_VERSION = "odylith.tribunal.structured_patch_plan.v1"

_PATCHABLE_LAYERS = frozenset({"semantic_model", "artifact_plan"})
_PATCH_PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": ["version", "status", "operations", "decision_summary"],
    "properties": {
        "version": {"type": "string"},
        "status": {"type": "string", "enum": ["planned", "no_safe_patch"]},
        "decision_summary": {"type": "string"},
        "operations": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "operation_id",
                    "target_layer",
                    "target_path",
                    "semantic_node_id",
                    "replacement_fact",
                    "decision_ledger_entry",
                    "proof_obligation_delta",
                    "rejected_interpretation",
                    "confidence",
                ],
                "properties": {
                    "operation_id": {"type": "string"},
                    "target_layer": {"type": "string"},
                    "target_path": {"type": "string"},
                    "semantic_node_id": {"type": "string"},
                    "replacement_fact": {},
                    "decision_ledger_entry": {"type": "object"},
                    "proof_obligation_delta": {"type": "object"},
                    "rejected_interpretation": {"type": "string"},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                },
            },
        },
    },
}

_SYSTEM_PROMPT = (
    "You are Odylith Tribunal's structured repair planner. Work only from the "
    "typed findings, evidence, and PatchSet request in the JSON payload. Return "
    "formal semantic or artifact-plan patch operations only. Do not rewrite "
    "rendered prose. Do not invent target paths, operation ids, projections, "
    "domains, files, or facts outside the supplied evidence. If the safe repair "
    "is unclear, return status no_safe_patch with no operations."
)


def plan_structured_patch(
    *,
    provider: odylith_reasoning.ReasoningProvider | None,
    patchset_request: Mapping[str, Any],
    review_report: Mapping[str, Any] | None = None,
    evidence: Mapping[str, Any] | None = None,
    schema_name: str = "tribunal_patch_plan",
    model: str = "",
    reasoning_effort: str = "",
    timeout_seconds: float = 0.0,
) -> dict[str, Any]:
    """Ask an optional provider for a custody-checked structured patch plan."""

    operations = _request_operations(patchset_request)
    if provider is None:
        return _empty_plan(status="provider_unavailable", reason="no structured reasoning provider available")
    if not operations:
        return _empty_plan(status="no_operations", reason="patch request has no repairable operations")
    request = odylith_reasoning.StructuredReasoningRequest(
        system_prompt=_SYSTEM_PROMPT,
        schema_name=schema_name,
        output_schema=_PATCH_PLAN_SCHEMA,
        prompt_payload={
            "version": TRIBUNAL_PATCH_PLAN_VERSION,
            "patchset_request": dict(patchset_request),
            "review_report": dict(review_report or {}),
            "evidence": dict(evidence or {}),
            "instructions": [
                "Preserve operation_id, target_layer, target_path, and semantic_node_id from the request.",
                "Fill replacement_fact with the smallest semantic or artifact-plan fact that fixes the finding.",
                "Use decision_ledger_entry to record the chosen interpretation and why rejected interpretations were rejected.",
                "Use proof_obligation_delta only for proof obligations that change because of the patch.",
                "Return no_safe_patch when the evidence does not support a bounded repair.",
            ],
        },
        model=model,
        reasoning_effort=reasoning_effort,
        timeout_seconds=timeout_seconds,
    )
    raw = provider.generate_structured(request=request)
    if not isinstance(raw, Mapping):
        failure = odylith_reasoning.provider_failure_metadata(provider)
        return _empty_plan(
            status="provider_failed",
            reason=failure.get("detail") or failure.get("code") or "provider returned no structured patch plan",
            provider=failure,
        )
    return validate_structured_patch_plan(raw, patchset_request=patchset_request, provider=provider)


def validate_structured_patch_plan(
    plan: Mapping[str, Any],
    *,
    patchset_request: Mapping[str, Any],
    provider: Any | None = None,
) -> dict[str, Any]:
    """Return a normalized patch plan that cannot expand caller custody."""

    request_by_id = {
        normalize_string(operation.get("operation_id")): operation
        for operation in _request_operations(patchset_request)
        if normalize_string(operation.get("operation_id"))
    }
    accepted: list[dict[str, Any]] = []
    rejections: list[dict[str, str]] = []
    for raw_operation in _raw_plan_operations(plan):
        operation_id = normalize_string(raw_operation.get("operation_id"))
        requested = request_by_id.get(operation_id)
        if not requested:
            rejections.append({"operation_id": operation_id, "reason": "operation id is not in the PatchSet request"})
            continue
        accepted_operation, reason = _validated_operation(raw_operation, requested)
        if reason:
            rejections.append({"operation_id": operation_id, "reason": reason})
            continue
        accepted.append(accepted_operation)
    status = "planned" if accepted else "rejected"
    return {
        "version": TRIBUNAL_PATCH_PLAN_VERSION,
        "status": status,
        "decision_summary": normalize_string(plan.get("decision_summary")),
        "operation_count": len(accepted),
        "operations": accepted,
        "rejections": rejections,
        "provider": odylith_reasoning.provider_failure_metadata(provider) if provider is not None else {},
    }


def merge_patch_plan_into_request(
    patchset_request: Mapping[str, Any],
    patch_plan: Mapping[str, Any],
) -> dict[str, Any]:
    """Return a PatchSet request with validated planner fields merged in."""

    plan_by_id = {
        normalize_string(operation.get("operation_id")): operation
        for operation in _raw_plan_operations(patch_plan)
        if normalize_string(operation.get("operation_id"))
    }
    merged_operations: list[dict[str, Any]] = []
    for operation in _request_operations(patchset_request):
        operation_id = normalize_string(operation.get("operation_id"))
        patched = dict(operation)
        plan_operation = plan_by_id.get(operation_id)
        if plan_operation:
            for key in (
                "replacement_fact",
                "decision_ledger_entry",
                "proof_obligation_delta",
                "rejected_interpretation",
                "confidence",
            ):
                patched[key] = plan_operation.get(key)
        merged_operations.append(patched)
    payload = dict(patchset_request)
    payload["operations"] = merged_operations
    payload["operation_count"] = len(merged_operations)
    payload["tribunal_patch_plan"] = {
        "version": normalize_string(patch_plan.get("version")) or TRIBUNAL_PATCH_PLAN_VERSION,
        "status": normalize_string(patch_plan.get("status")),
        "operation_count": int(patch_plan.get("operation_count") or 0),
        "decision_summary": normalize_string(patch_plan.get("decision_summary")),
        "rejections": list(patch_plan.get("rejections", [])) if isinstance(patch_plan.get("rejections"), list) else [],
        "provider": dict(patch_plan.get("provider", {})) if isinstance(patch_plan.get("provider"), Mapping) else {},
    }
    return payload


def _validated_operation(raw_operation: Mapping[str, Any], requested: Mapping[str, Any]) -> tuple[dict[str, Any], str]:
    requested_layer = normalize_token(requested.get("target_layer"))
    if requested_layer not in _PATCHABLE_LAYERS:
        return {}, "requested operation is not a semantic or artifact-plan patch"
    if normalize_token(raw_operation.get("target_layer")) != requested_layer:
        return {}, "target_layer does not match the PatchSet request"
    if normalize_string(raw_operation.get("target_path")) != normalize_string(requested.get("target_path")):
        return {}, "target_path does not match the PatchSet request"
    if normalize_string(raw_operation.get("semantic_node_id")) != normalize_string(requested.get("semantic_node_id")):
        return {}, "semantic_node_id does not match the PatchSet request"
    replacement = raw_operation.get("replacement_fact")
    if _empty_patch_value(replacement):
        return {}, "replacement_fact is empty"
    confidence = _confidence(raw_operation.get("confidence"))
    if confidence <= 0:
        return {}, "confidence is not positive"
    requested_projections = _projection_rows(requested.get("affected_projections"))
    return (
        {
            "operation_id": normalize_string(requested.get("operation_id")),
            "target_layer": requested_layer,
            "target_path": normalize_string(requested.get("target_path")),
            "semantic_node_id": normalize_string(requested.get("semantic_node_id")),
            "issue_code": normalize_token(requested.get("issue_code")),
            "source_finding": normalize_token(requested.get("source_finding")),
            "affected_projections": requested_projections,
            "requested_action": normalize_string(requested.get("requested_action")),
            "replacement_fact": replacement,
            "decision_ledger_entry": _mapping_or_empty(raw_operation.get("decision_ledger_entry")),
            "proof_obligation_delta": _mapping_or_empty(raw_operation.get("proof_obligation_delta")),
            "rejected_interpretation": (
                normalize_string(raw_operation.get("rejected_interpretation"))
                or normalize_string(requested.get("rejected_interpretation"))
            ),
            "confidence": confidence,
        },
        "",
    )


def _request_operations(patchset_request: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    operations = patchset_request.get("operations")
    if not isinstance(operations, list):
        return []
    return [operation for operation in operations if isinstance(operation, Mapping)]


def _raw_plan_operations(plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    operations = plan.get("operations")
    if not isinstance(operations, list):
        return []
    return [operation for operation in operations if isinstance(operation, Mapping)]


def _projection_rows(value: Any) -> tuple[str, ...]:
    return tuple(normalize_string_list(value, limit=16))


def _mapping_or_empty(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _confidence(value: Any) -> float:
    try:
        return round(max(0.0, min(1.0, float(value))), 3)
    except (TypeError, ValueError):
        return 0.0


def _empty_patch_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return not normalize_string(value)
    if isinstance(value, Mapping):
        return not any(not _empty_patch_value(item) for item in value.values())
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return not any(not _empty_patch_value(item) for item in value)
    return False


def _empty_plan(
    *,
    status: str,
    reason: str,
    provider: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "version": TRIBUNAL_PATCH_PLAN_VERSION,
        "status": status,
        "decision_summary": normalize_string(reason),
        "operation_count": 0,
        "operations": [],
        "rejections": [],
        "provider": dict(provider or {}),
    }


__all__ = [
    "TRIBUNAL_PATCH_PLAN_VERSION",
    "merge_patch_plan_into_request",
    "plan_structured_patch",
    "validate_structured_patch_plan",
]
