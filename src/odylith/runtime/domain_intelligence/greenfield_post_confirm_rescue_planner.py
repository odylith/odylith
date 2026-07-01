"""Rescue-tier structured patch planning for greenfield post-confirm repair."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import os
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmRepairContext,
)
from odylith.runtime.domain_intelligence.greenfield_projection_repair_targets import (
    projection_repair_target_value,
)
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.reasoning import tribunal_patch_planner


def enrich_rescue_patchset_with_structured_plan(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPostConfirmRepairContext | None,
    repo_root: Path | None,
) -> GreenfieldPostConfirmRepairContext | None:
    """Fill PatchSet replacement facts only through a bounded rescue planner."""

    if repair_context is None or repo_root is None:
        return repair_context
    if repair_context.repair_tier not in {"rescue", "deep"}:
        return repair_context
    patchset = repair_context.patchset_request if isinstance(repair_context.patchset_request, Mapping) else {}
    if isinstance(patchset.get("tribunal_patch_plan"), Mapping):
        return repair_context
    if not _needs_structured_patch_plan(patchset):
        return repair_context
    timeout_seconds = _structured_patch_timeout_seconds(repair_context.budget_seconds - repair_context.elapsed_seconds)
    if timeout_seconds <= 0:
        return repair_context
    root = Path(repo_root).expanduser().resolve()
    config = odylith_reasoning.reasoning_config_from_env(repo_root=root)
    provider = odylith_reasoning.provider_from_config(
        config,
        repo_root=root,
        allow_implicit_local_provider=True,
    )
    if provider is None:
        return repair_context
    patch_plan = tribunal_patch_planner.plan_structured_patch(
        provider=provider,
        patchset_request=patchset,
        review_report=repair_context.review_report,
        evidence=_structured_patch_evidence(proposal, repair_context=repair_context),
        model=config.model,
        reasoning_effort=_provider_reasoning_effort(config, provider),
        timeout_seconds=timeout_seconds,
    )
    if patch_plan.get("status") != "planned":
        return replace(
            repair_context,
            patchset_request={
                **dict(patchset),
                "tribunal_patch_plan": _patch_plan_summary(patch_plan),
            },
        )
    return replace(
        repair_context,
        patchset_request=tribunal_patch_planner.merge_patch_plan_into_request(patchset, patch_plan),
    )


def _needs_structured_patch_plan(patchset: Mapping[str, Any]) -> bool:
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return False
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        if str(operation.get("target_layer", "")).strip() not in {"semantic_model", "artifact_plan"}:
            continue
        if tribunal_patch_planner.replacement_fact_missing(operation.get("replacement_fact"), operation):
            return True
    return False


def _structured_patch_timeout_seconds(remaining_seconds: float) -> float:
    try:
        remaining = float(remaining_seconds)
    except (TypeError, ValueError):
        return 0.0
    if remaining <= 12.0:
        return 0.0
    return round(min(45.0, max(0.0, remaining - 10.0)), 3)


def _structured_patch_evidence(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPostConfirmRepairContext,
) -> dict[str, Any]:
    return {
        "intent": dict(proposal.get("intent", {})) if isinstance(proposal.get("intent"), Mapping) else {},
        "semantic_model": dict(proposal.get("semantic_model", {}))
        if isinstance(proposal.get("semantic_model"), Mapping)
        else {},
        "quality_lenses": dict(repair_context.quality_lenses),
        "semantic_compiler": dict(repair_context.semantic_compiler),
        "issues": [issue.to_dict() for issue in repair_context.issues],
        "patch_targets": _patch_target_evidence(proposal, repair_context=repair_context),
    }


def _patch_target_evidence(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPostConfirmRepairContext,
) -> list[dict[str, Any]]:
    patchset = repair_context.patchset_request if isinstance(repair_context.patchset_request, Mapping) else {}
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return []
    evidence: list[dict[str, Any]] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        target_path = str(operation.get("target_path", "")).strip()
        if not target_path:
            continue
        evidence.append(
            {
                "operation_id": str(operation.get("operation_id", "")).strip(),
                "target_layer": str(operation.get("target_layer", "")).strip(),
                "target_path": target_path,
                "semantic_node_id": str(operation.get("semantic_node_id", "")).strip(),
                "affected_projections": _sequence_strings(operation.get("affected_projections")),
                "current_value": projection_repair_target_value(proposal, target_path),
            }
        )
    return evidence


def _sequence_strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _provider_reasoning_effort(config: odylith_reasoning.ReasoningConfig, provider: Any) -> str:
    provider_name = odylith_reasoning.provider_failure_metadata(provider).get("provider", "")
    if provider_name == "codex-cli":
        return _patch_planner_effort(
            config.codex_reasoning_effort,
            explicit_env_key="ODYLITH_REASONING_CODEX_REASONING_EFFORT",
        )
    if provider_name == "claude-cli":
        return _patch_planner_effort(
            config.claude_reasoning_effort,
            explicit_env_key="ODYLITH_REASONING_CLAUDE_REASONING_EFFORT",
        )
    return ""


def _patch_planner_effort(configured: str, *, explicit_env_key: str) -> str:
    if str(os.environ.get(explicit_env_key, "")).strip():
        return configured
    return "medium"


def _patch_plan_summary(patch_plan: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "version": str(patch_plan.get("version", "")).strip(),
        "status": str(patch_plan.get("status", "")).strip(),
        "operation_count": int(patch_plan.get("operation_count") or 0),
        "decision_summary": str(patch_plan.get("decision_summary", "")).strip(),
        "rejections": list(patch_plan.get("rejections", [])) if isinstance(patch_plan.get("rejections"), list) else [],
        "provider": dict(patch_plan.get("provider", {})) if isinstance(patch_plan.get("provider"), Mapping) else {},
    }


__all__ = ["enrich_rescue_patchset_with_structured_plan"]
