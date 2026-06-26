"""Apply typed greenfield post-confirm patch operations to proposal state."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.common import display_text
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_artifact_plan_patch_executor import (
    apply_artifact_plan_patch_operations,
)
from odylith.runtime.domain_intelligence.greenfield_apply_semantic import ensure_apply_semantic_model
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_first_path_repair import repair_proposal_first_path
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import GreenfieldPostConfirmRepairContext
from odylith.runtime.domain_intelligence.greenfield_post_confirm_repair_context import repair_context_operations
from odylith.runtime.domain_intelligence.greenfield_quality_lens_repair import repair_proposal_for_quality_lens_gaps
from odylith.runtime.domain_intelligence.greenfield_semantic_compiler import repair_greenfield_semantic_projections
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_executor import apply_semantic_patch_operations
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal


_MODEL_PATCH_LAYERS = frozenset({"semantic_model", "artifact_plan"})
_QUALITY_LENS_SOURCES = frozenset({"quality_lens", "quality_lens_contract"})
_QUALITY_LENS_CODES = frozenset({"quality_lens_gap"})


def apply_greenfield_patchset_repairs(
    proposal: Mapping[str, Any],
    *,
    release_selector: str,
    repair_context: GreenfieldPostConfirmRepairContext | None,
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
    repair_context: GreenfieldPostConfirmRepairContext,
) -> dict[str, Any]:
    operations = repair_context_operations(repair_context)
    if not operations:
        return proposal
    if not any(_target_layer(operation) in _MODEL_PATCH_LAYERS for operation in operations):
        return proposal

    repaired = proposal
    semantic_changed = apply_semantic_patch_operations(repaired, operations)
    plan_changed = apply_artifact_plan_patch_operations(repaired, operations)
    if semantic_changed or plan_changed:
        repaired = _normalized_proposal(repaired)
    repaired = _complete_confirmed_semantic_proposal(repaired, release_selector=release_selector)
    if any(_is_first_path_semantic_operation(operation) for operation in operations):
        if repair_proposal_first_path(repaired):
            repaired = _normalized_proposal(repaired)
            repaired = _complete_confirmed_semantic_proposal(repaired, release_selector=release_selector)
    if any(_is_quality_lens_operation(operation) for operation in operations):
        if repair_proposal_for_quality_lens_gaps(
            repaired,
            quality_lenses=repair_context.quality_lenses,
            release_selector=release_selector,
        ):
            repaired = _normalized_proposal(repaired)
            repaired = _complete_confirmed_semantic_proposal(repaired, release_selector=release_selector)
    return repaired


def complete_greenfield_semantic_apply_payload(proposal: dict[str, Any], *, release_selector: str) -> dict[str, Any]:
    """Complete proposal semantics and clear poisoned semantic projections."""

    repaired = ensure_apply_semantic_model(proposal, refresh=True)
    if repair_greenfield_semantic_projections(repaired):
        repaired = complete_confirmed_proposal(repaired, release_selector=release_selector)
        repaired = _normalized_proposal(repaired)
        repaired = ensure_apply_semantic_model(repaired, refresh=True)
    return repaired


def _complete_confirmed_semantic_proposal(proposal: dict[str, Any], *, release_selector: str) -> dict[str, Any]:
    repaired = complete_confirmed_proposal(proposal, release_selector=release_selector)
    repaired = _normalized_proposal(repaired)
    return complete_greenfield_semantic_apply_payload(repaired, release_selector=release_selector)


def _normalized_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    normalized = normalize_host_reasoned_proposal(proposal)
    return display_text.strip_inline_markdown_emphasis_tree(normalized)


def _target_layer(operation: Mapping[str, Any]) -> str:
    return normalize_token(operation.get("target_layer"))


def _is_quality_lens_operation(operation: Mapping[str, Any]) -> bool:
    return (
        normalize_token(operation.get("source_finding")) in _QUALITY_LENS_SOURCES
        or normalize_token(operation.get("issue_code")) in _QUALITY_LENS_CODES
    )


def _is_first_path_semantic_operation(operation: Mapping[str, Any]) -> bool:
    if _target_layer(operation) not in _MODEL_PATCH_LAYERS:
        return False
    semantic_node = normalize_token(operation.get("semantic_node_id"))
    target_path = normalize_token(operation.get("target_path"))
    rejected = str(operation.get("rejected_interpretation", "")).casefold()
    return bool(
        "first_path_contract" in semantic_node
        or "first_path_contract" in target_path
        or "first path" in rejected
        or "firstpathcontract" in rejected
    )


__all__ = ["apply_greenfield_patchset_repairs", "complete_greenfield_semantic_apply_payload"]
