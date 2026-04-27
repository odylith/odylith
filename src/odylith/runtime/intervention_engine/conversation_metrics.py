"""Evidence metric extraction for intervention conversation rendering."""

from __future__ import annotations

from typing import Any
from typing import Mapping

from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.intervention_engine import conversation_common


def presentation_policy_snapshot(*, request: Any, adoption: Mapping[str, Any]) -> dict[str, Any]:
    context_payload = conversation_common.request_context_payload(request)
    execution_engine_summary = conversation_common.nested_mapping(context_payload, "execution_engine_summary")
    packet_summary = conversation_common.nested_mapping(context_payload, "packet_summary")
    presentation_policy = conversation_common.nested_mapping(context_payload, "presentation_policy")
    context_packet_presentation_policy = conversation_common.nested_mapping(
        context_payload,
        "context_packet",
        "presentation_policy",
    )
    return {
        "commentary_mode": _normalize_token(
            conversation_common.first_present(
                adoption.get("execution_engine_commentary_mode"),
                conversation_common.mapping_lookup(
                    execution_engine_summary,
                    "execution_engine_commentary_mode",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "execution_engine_commentary_mode",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "latest_execution_engine_commentary_mode",
                ),
                conversation_common.mapping_lookup(
                    packet_summary,
                    "presentation_policy_commentary_mode",
                ),
                conversation_common.mapping_lookup(presentation_policy, "commentary_mode"),
                conversation_common.mapping_lookup(
                    context_packet_presentation_policy,
                    "commentary_mode",
                ),
            )
        ),
        "suppress_routing_receipts": conversation_common.bool_value(
            conversation_common.first_present(
                adoption.get("execution_engine_suppress_routing_receipts"),
                conversation_common.mapping_lookup(
                    execution_engine_summary,
                    "execution_engine_suppress_routing_receipts",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "execution_engine_suppress_routing_receipts",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "latest_execution_engine_suppress_routing_receipts",
                ),
                conversation_common.mapping_lookup(
                    packet_summary,
                    "presentation_policy_suppress_routing_receipts",
                ),
                conversation_common.mapping_lookup(
                    presentation_policy,
                    "suppress_routing_receipts",
                ),
                conversation_common.mapping_lookup(
                    context_packet_presentation_policy,
                    "suppress_routing_receipts",
                ),
            )
        ),
        "surface_fast_lane": conversation_common.bool_value(
            conversation_common.first_present(
                adoption.get("execution_engine_surface_fast_lane"),
                conversation_common.mapping_lookup(
                    execution_engine_summary,
                    "execution_engine_surface_fast_lane",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "execution_engine_surface_fast_lane",
                ),
                conversation_common.mapping_lookup(
                    context_payload,
                    "latest_execution_engine_surface_fast_lane",
                ),
                conversation_common.mapping_lookup(
                    packet_summary,
                    "presentation_policy_surface_fast_lane",
                ),
                conversation_common.mapping_lookup(presentation_policy, "surface_fast_lane"),
                conversation_common.mapping_lookup(
                    context_packet_presentation_policy,
                    "surface_fast_lane",
                ),
            )
        ),
    }


def evidence_metrics(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
) -> dict[str, Any]:
    presentation_policy = presentation_policy_snapshot(request=request, adoption=adoption)
    candidate_path_count = conversation_common.sequence_count(conversation_common.field(request, "candidate_paths"))
    claimed_path_count = conversation_common.sequence_count(conversation_common.field(request, "claimed_paths"))
    workstream_count = conversation_common.sequence_count(conversation_common.field(request, "workstreams"))
    component_count = conversation_common.sequence_count(conversation_common.field(request, "components"))
    validation_count = conversation_common.sequence_count(conversation_common.field(request, "validation_commands"))
    delegated_leaf_count = conversation_common.sequence_count(conversation_common.field(decision, "subtasks"))
    main_thread_followup_count = conversation_common.sequence_count(
        conversation_common.field(decision, "main_thread_followups")
    )
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
        "mode": _normalize_token(conversation_common.field(decision, "mode")),
        "commentary_mode": str(presentation_policy.get("commentary_mode", "")).strip(),
        "suppress_routing_receipts": bool(presentation_policy.get("suppress_routing_receipts")),
        "surface_fast_lane": bool(presentation_policy.get("surface_fast_lane")),
    }
