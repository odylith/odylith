"""Apply typed greenfield pre-confirm patch operations to proposal state."""

from __future__ import annotations

from collections.abc import Mapping
from collections.abc import Sequence
import json
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_artifact_plan import artifact_plan_operation_affected_projections
from odylith.runtime.domain_intelligence.greenfield_artifact_plan_patch_executor import (
    apply_artifact_plan_patch_operations,
)
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_diagram_projection import (
    refresh_confirmed_diagram_projection,
)
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import patch_expand_projection_scope
from odylith.runtime.domain_intelligence.greenfield_patch_projection_scope import patch_scope_requires_full_prewrite
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import GreenfieldPreconfirmRepairContext
from odylith.runtime.domain_intelligence.greenfield_preconfirm_repair_context import repair_context_operations
from odylith.runtime.domain_intelligence.greenfield_preconfirm_rescue_probe import (
    apply_rescue_probe_operations,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import repair_greenfield_semantic_projections
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_executor import SemanticPatchApplication
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_executor import (
    apply_semantic_patch_operations_detailed,
)
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal


_MODEL_PATCH_LAYERS = frozenset({"semantic_model", "artifact_plan"})
_PATCH_APPLICATION_LEDGER_KEY = "preconfirm_patch_application_ledger"


def apply_greenfield_patchset_repairs(
    proposal: Mapping[str, Any],
    *,
    release_selector: str,
    repair_context: GreenfieldPreconfirmRepairContext | None,
) -> Mapping[str, Any]:
    """Execute typed semantic or artifact-plan repairs before rerender."""

    repaired = _normalized_proposal(proposal)
    if repair_context is None:
        repaired = _complete_confirmed_semantic_proposal(repaired, release_selector=release_selector)
    else:
        repaired = _apply_operations(
            repaired,
            release_selector=release_selector,
            repair_context=repair_context,
        )
    validate_host_reasoned_proposal(repaired)
    return repaired


def _apply_operations(
    proposal: dict[str, Any],
    *,
    release_selector: str,
    repair_context: GreenfieldPreconfirmRepairContext,
) -> dict[str, Any]:
    operations = repair_context_operations(repair_context)
    if not operations:
        return proposal
    if not any(_target_layer(operation) in _MODEL_PATCH_LAYERS for operation in operations):
        return proposal

    repaired = proposal
    semantic_application = apply_semantic_patch_operations_detailed(repaired, operations)
    semantic_changed = semantic_application.changed
    plan_changed = apply_artifact_plan_patch_operations(repaired, operations)
    probe_changed = apply_rescue_probe_operations(repaired, operations)
    if semantic_changed or plan_changed or probe_changed:
        repaired = _normalized_proposal(repaired)
    completion_required = semantic_application.completion_required
    if completion_required:
        repaired = _complete_confirmed_semantic_proposal(repaired, release_selector=release_selector)
    if semantic_changed or plan_changed or probe_changed or completion_required:
        _append_patch_application_ledger(
            repaired,
            operations=operations,
            semantic_application=semantic_application,
            semantic_changed=semantic_changed,
            plan_changed=plan_changed,
            internal_probe_changed=probe_changed,
            completion_required=completion_required,
        )
    return repaired


def complete_greenfield_semantic_apply_payload(
    proposal: dict[str, Any],
    *,
    release_selector: str,
    proposal_completed: bool = False,
) -> dict[str, Any]:
    """Complete proposal semantics and clear poisoned semantic projections."""

    first_path_before = _first_path_contract_fingerprint(proposal)
    repaired = ensure_apply_semantic_model(proposal, refresh=True)
    semantic_changed = first_path_before != _first_path_contract_fingerprint(repaired)
    projection_changed = repair_greenfield_semantic_projections(repaired)
    _refresh_semantic_diagrams(repaired, semantic_changed=semantic_changed)
    if proposal_completed and not projection_changed:
        return repaired
    completed = complete_confirmed_proposal(repaired, release_selector=release_selector)
    if projection_changed or completed != repaired:
        repaired = completed
        repaired = _normalized_proposal(repaired)
        first_path_before = _first_path_contract_fingerprint(repaired)
        repaired = ensure_apply_semantic_model(repaired, refresh=True)
        _refresh_semantic_diagrams(
            repaired,
            semantic_changed=first_path_before != _first_path_contract_fingerprint(repaired),
        )
    return repaired


def _refresh_semantic_diagrams(proposal: dict[str, Any], *, semantic_changed: bool) -> None:
    """Keep Atlas projections aligned after semantic or backlog facts change."""

    rows = proposal.get("diagrams")
    if isinstance(rows, list) and (semantic_changed or _diagram_links_are_stale(proposal, rows)):
        refresh_confirmed_diagram_projection(proposal, rows)


def _first_path_contract_fingerprint(proposal: Mapping[str, Any]) -> str:
    semantic_model = proposal.get("semantic_model")
    if not isinstance(semantic_model, Mapping):
        return ""
    contract = semantic_model.get("first_path_contract")
    if not isinstance(contract, Mapping):
        return ""
    return json.dumps(contract, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def _diagram_links_are_stale(proposal: Mapping[str, Any], rows: Sequence[Any]) -> bool:
    current_titles = {
        normalize_string(row.get("title"))
        for row in proposal.get("backlog", [])
        if isinstance(row, Mapping) and normalize_string(row.get("title"))
    }
    if not current_titles:
        return False
    return any(
        normalize_string(title) not in current_titles
        for row in rows
        if isinstance(row, Mapping)
        for title in row.get("related_workstream_titles", [])
        if normalize_string(title)
    )


def _complete_confirmed_semantic_proposal(proposal: dict[str, Any], *, release_selector: str) -> dict[str, Any]:
    repaired = complete_confirmed_proposal(proposal, release_selector=release_selector)
    repaired = _normalized_proposal(repaired)
    return complete_greenfield_semantic_apply_payload(
        repaired,
        release_selector=release_selector,
        proposal_completed=True,
    )


def _normalized_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_host_reasoned_proposal(proposal)
    return display_text.strip_inline_markdown_emphasis_tree(normalized)


def _target_layer(operation: Mapping[str, Any]) -> str:
    return normalize_token(operation.get("target_layer"))


def _is_first_path_semantic_operation(operation: Mapping[str, Any]) -> bool:
    if _target_layer(operation) not in _MODEL_PATCH_LAYERS:
        return False
    if normalize_token(operation.get("operation_kind")) == "semantic_first_path":
        return True
    return _has_legacy_structured_first_path_target(operation)


def _has_legacy_structured_first_path_target(operation: Mapping[str, Any]) -> bool:
    target_path = str(operation.get("target_path") or "").strip()
    semantic_node = str(operation.get("semantic_node_id") or "").strip()
    return target_path in {
        "semantic_model.first_path_contract",
        "semantic_model.first_path_contract.raw_path",
        "proposal.semantic_model.first_path_contract",
    } or semantic_node in {
        "SemanticModelIR.first_path_contract",
        "SemanticModelIR.first_path_contract.raw_path",
    }


def _append_patch_application_ledger(
    proposal: dict[str, Any],
    *,
    operations: Sequence[Mapping[str, Any]],
    semantic_application: SemanticPatchApplication,
    semantic_changed: bool,
    plan_changed: bool,
    internal_probe_changed: bool,
    completion_required: bool,
) -> None:
    affected_projections = tuple(
        dict.fromkeys(
            (
                *semantic_application.affected_projections,
                *(
                    projection
                    for operation in operations
                    for projection in _artifact_plan_operation_scope(operation)
                ),
            )
        )
    )
    rerender_projections = patch_expand_projection_scope(affected_projections)
    full_prewrite_required = completion_required or patch_scope_requires_full_prewrite(affected_projections)
    operation_ids = tuple(
        operation_id
        for operation_id in (normalize_string(operation.get("operation_id")) for operation in operations)
        if operation_id
    )
    target_layers = tuple(
        dict.fromkeys(layer for layer in (_target_layer(operation) for operation in operations) if layer)
    )
    ledger = proposal.setdefault(_PATCH_APPLICATION_LEDGER_KEY, [])
    entry = {
        "operation_ids": operation_ids,
        "target_layers": target_layers,
        "affected_projections": affected_projections,
        "rerender_projections": rerender_projections,
        "semantic_changed": bool(semantic_changed),
        "artifact_plan_changed": bool(plan_changed),
        "internal_probe_changed": bool(internal_probe_changed),
        "completion_required": bool(completion_required),
        "full_prewrite_required": bool(full_prewrite_required),
        "rerender_scope": "full_prewrite" if full_prewrite_required else "affected_projections",
    }
    if isinstance(ledger, list):
        ledger.append(entry)
    else:
        proposal[_PATCH_APPLICATION_LEDGER_KEY] = [entry]


def _artifact_plan_operation_scope(operation: Mapping[str, Any]) -> tuple[str, ...]:
    if _target_layer(operation) != "artifact_plan":
        return ()
    return artifact_plan_operation_affected_projections(operation)


__all__ = ["apply_greenfield_patchset_repairs", "complete_greenfield_semantic_apply_payload"]
