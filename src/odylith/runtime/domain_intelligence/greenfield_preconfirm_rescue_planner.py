"""Rescue-tier structured patch planning for greenfield pre-confirm repair."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import replace
import os
from pathlib import Path
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_component_contract_quality import normalize_contract
from odylith.runtime.domain_intelligence.greenfield_component_contract_fields import produced_outputs_text
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import (
    GreenfieldPreconfirmRepairContext,
)
from odylith.runtime.domain_intelligence.greenfield_projection_repair_targets import (
    projection_repair_target_value,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_targets import (
    SemanticPatchTarget,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_patch_targets import (
    semantic_patch_target_for_operation,
)
from odylith.runtime.domain_intelligence.greenfield_text import clean_artifact_sentence
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.reasoning import odylith_reasoning
from odylith.runtime.reasoning import tribunal_patch_planner


def enrich_rescue_patchset_with_structured_plan(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPreconfirmRepairContext | None,
    repo_root: Path | None,
) -> GreenfieldPreconfirmRepairContext | None:
    """Fill PatchSet replacement facts only through a bounded rescue planner."""

    if repair_context is None or repo_root is None:
        return repair_context
    if repair_context.repair_tier not in {"rescue", "deep"}:
        return repair_context
    patchset = repair_context.patchset_request if isinstance(repair_context.patchset_request, Mapping) else {}
    patchset = _with_deterministic_source_patch_facts(proposal, patchset)
    if patchset is not repair_context.patchset_request:
        repair_context = replace(repair_context, patchset_request=patchset)
    if isinstance(patchset.get("tribunal_patch_plan"), Mapping):
        return repair_context
    if not _needs_structured_patch_plan(patchset):
        return repair_context
    planner_patchset = _planner_patchset_request(patchset)
    source_fallback_ready = _source_anchored_patchset_candidate(proposal, planner_patchset)
    timeout_seconds = _structured_patch_timeout_seconds(
        repair_context.budget_seconds - repair_context.elapsed_seconds,
        source_fallback_ready=source_fallback_ready,
    )
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
    planner_profile = _structured_patch_profile(config, provider)
    patch_plan = tribunal_patch_planner.plan_structured_patch(
        provider=provider,
        patchset_request=planner_patchset,
        review_report=_structured_patch_review_report(repair_context),
        evidence=_structured_patch_evidence(proposal, repair_context=repair_context),
        model=planner_profile.model or config.model,
        reasoning_effort=_provider_reasoning_effort(config, provider, patchset=planner_patchset, profile=planner_profile),
        timeout_seconds=timeout_seconds,
    )
    if patch_plan.get("status") != "planned":
        fallback_patchset = _with_source_anchored_semantic_patch_facts(
            proposal,
            patchset,
            patch_plan=patch_plan,
        )
        if fallback_patchset is not patchset:
            return replace(repair_context, patchset_request=fallback_patchset)
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


def _with_source_anchored_semantic_patch_facts(
    proposal: Mapping[str, Any],
    patchset: Mapping[str, Any],
    *,
    patch_plan: Mapping[str, Any],
) -> Mapping[str, Any]:
    if normalize_string(patch_plan.get("status")) != "provider_failed":
        return patchset
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return patchset
    changed = False
    patched_count = 0
    next_operations: list[Any] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            next_operations.append(operation)
            continue
        if not tribunal_patch_planner.replacement_fact_missing(operation.get("replacement_fact"), operation):
            next_operations.append(operation)
            continue
        replacement = _source_anchored_semantic_replacement_fact(proposal, operation)
        if not replacement:
            next_operations.append(operation)
            continue
        updated = dict(operation)
        updated["replacement_fact"] = replacement
        updated["decision_ledger_entry"] = _source_anchored_decision_ledger(operation)
        updated["proof_obligation_delta"] = {
            "summary": (
                "No proof obligation change; the fallback preserves the current schema-owned SemanticModelIR fact "
                "after the configured host provider failed to return in the rescue budget."
            ),
            "added_obligations": [],
            "removed_obligations": [],
            "unchanged_obligations": ["final pre-confirm quality gate still validates the rerendered governed records"],
        }
        updated["confidence"] = max(_float_or_zero(operation.get("confidence")), 0.74)
        next_operations.append(updated)
        changed = True
        patched_count += 1
    if not changed:
        return patchset
    provider = _provider_failure_mapping(patch_plan)
    return {
        **dict(patchset),
        "operations": next_operations,
        "operation_count": len(next_operations),
        "tribunal_patch_plan": _patch_plan_summary(patch_plan),
        "structured_patch_fallback": {
            "version": "odylith.greenfield.preconfirm.structured_patch_fallback.v1",
            "status": "applied",
            "source": "source_anchored_semantic_fact",
            "operation_count": patched_count,
            "provider_failure": provider,
        },
    }


def _source_anchored_patchset_candidate(
    proposal: Mapping[str, Any],
    patchset: Mapping[str, Any],
) -> bool:
    operations = patchset.get("operations")
    if not isinstance(operations, list) or not operations:
        return False
    for operation in operations:
        if not isinstance(operation, Mapping):
            return False
        if not tribunal_patch_planner.replacement_fact_missing(operation.get("replacement_fact"), operation):
            continue
        if not _source_anchored_semantic_replacement_fact(proposal, operation):
            return False
    return True


def _source_anchored_semantic_replacement_fact(
    proposal: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> dict[str, Any]:
    if normalize_string(operation.get("target_layer")) != "semantic_model":
        return {}
    target = semantic_patch_target_for_operation(operation)
    if target is None:
        return {}
    value = _source_anchored_semantic_value(proposal, target)
    key = target.replacement_keys[0] if target.replacement_keys else ""
    if not key:
        return {}
    if target.value_kind == "list":
        rows = [normalize_string(row) for row in text_values(value) if normalize_string(row)]
        if rows or (isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray))):
            return {key: rows}
        return {}
    text = normalize_string(value)
    return {key: text} if text else {}


def _source_anchored_semantic_value(
    proposal: Mapping[str, Any],
    target: SemanticPatchTarget,
) -> Any:
    for address in (target.canonical_path, *target.address_aliases):
        value = projection_repair_target_value(proposal, address)
        if _source_value_present(value):
            return value
    intent = proposal.get("intent")
    if isinstance(intent, Mapping):
        value = intent.get(target.intent_key)
        if _source_value_present(value):
            return value
    return ""


def _source_value_present(value: Any) -> bool:
    if isinstance(value, str):
        return bool(normalize_string(value))
    if isinstance(value, Mapping):
        return bool(value)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return True
    return value not in (None, "")


def _source_anchored_decision_ledger(operation: Mapping[str, Any]) -> dict[str, Any]:
    evidence_ids = [
        value
        for value in (
            normalize_string(operation.get("semantic_node_id")),
            normalize_string(operation.get("target_path")),
            normalize_string(operation.get("source_finding")),
        )
        if value
    ]
    return {
        "chosen_interpretation": "preserve the accepted schema-owned semantic fact",
        "rationale": (
            "the typed pre-confirm finding identified an exact SemanticModelIR target, and the current proposal "
            "already carries a source-owned value for that target while the configured host provider failed"
        ),
        "rejected_interpretations": [
            "blocking governed writes solely because the host provider timed out",
            "rewriting rendered prose directly instead of repairing the semantic model",
            normalize_string(operation.get("rejected_interpretation")) or "inventing unsupported semantic facts",
        ],
        "evidence_ids": evidence_ids,
    }


def _provider_failure_mapping(patch_plan: Mapping[str, Any]) -> dict[str, str]:
    provider = patch_plan.get("provider")
    if not isinstance(provider, Mapping):
        return {}
    return {str(key): str(value) for key, value in dict(provider).items() if str(value).strip()}


def _with_deterministic_source_patch_facts(
    proposal: Mapping[str, Any],
    patchset: Mapping[str, Any],
) -> Mapping[str, Any]:
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return patchset
    changed = False
    next_operations: list[Any] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            next_operations.append(operation)
            continue
        if not tribunal_patch_planner.replacement_fact_missing(operation.get("replacement_fact"), operation):
            next_operations.append(operation)
            continue
        replacement = _deterministic_source_replacement_fact(proposal, operation)
        if not replacement:
            next_operations.append(operation)
            continue
        updated = dict(operation)
        updated["replacement_fact"] = replacement
        updated["decision_ledger_entry"] = _deterministic_patch_decision_ledger(operation, replacement)
        updated["proof_obligation_delta"] = _deterministic_patch_proof_delta(replacement)
        updated["confidence"] = max(_float_or_zero(operation.get("confidence")), 0.86)
        next_operations.append(updated)
        changed = True
    if not changed:
        return patchset
    return {**dict(patchset), "operations": next_operations}


def _deterministic_patch_decision_ledger(
    operation: Mapping[str, Any],
    replacement: Mapping[str, Any],
) -> dict[str, Any]:
    if normalize_string(replacement.get("path")) == "assumptions":
        return {
            "chosen_interpretation": "assumption coverage repaired from accepted assumptions and proof boundary",
            "rationale": (
                "the typed quality-lens finding identified ArtifactPlanIR.assumptions and the current proposal "
                "carried accepted assumptions or proof-boundary source facts"
            ),
            "rejected_interpretations": [
                "rewriting rendered project brief prose directly",
                "inventing unsupported domain assumptions",
            ],
        }
    return {
        "chosen_interpretation": "component contract output repaired from the localized component source fact",
        "rationale": "the typed package finding already identified an executable ArtifactPlanIR component contract path",
        "rejected_interpretations": ["rewriting rendered component spec prose directly"],
    }


def _deterministic_patch_proof_delta(replacement: Mapping[str, Any]) -> dict[str, str]:
    if normalize_string(replacement.get("path")) == "assumptions":
        return {
            "summary": "No proof obligation change; this patch clarifies accepted assumption coverage before rerender."
        }
    return {"summary": "No proof obligation change; this patch only corrects the component contract projection source."}


def _deterministic_source_replacement_fact(
    proposal: Mapping[str, Any],
    operation: Mapping[str, Any],
) -> dict[str, Any]:
    if normalize_string(operation.get("target_layer")) != "artifact_plan":
        return {}
    target_path = normalize_string(operation.get("target_path"))
    if _assumptions_target(target_path):
        value = _assumptions_patch_value(proposal)
        return {"path": "assumptions", "value": value} if value else {}
    if not _component_contract_output_target(target_path):
        return {}
    value = _component_contract_output_patch_value(proposal, target_path)
    if not value:
        return {}
    return {"path": target_path, "value": value}


def _assumptions_target(target_path: str) -> bool:
    return target_path == "assumptions" or target_path.startswith("assumptions[")


def _assumptions_patch_value(proposal: Mapping[str, Any]) -> list[str]:
    statements = _assumption_statements(proposal)
    if not statements:
        return []
    boundary = _accepted_boundary_statement(proposal)
    if boundary:
        statement = (
            "High-risk proof remains review-only until authorized reviewers confirm "
            f"{boundary} from accepted records."
        )
    else:
        statement = ""
    if statement and not _statement_already_present(statement, statements):
        statements.append((f"ASM-{len(statements) + 1:03d}", statement))
    return [f"{identifier}: {statement.strip(' .')}." for identifier, statement in statements if statement.strip()]


def _assumption_statements(proposal: Mapping[str, Any]) -> list[tuple[str, str]]:
    assumptions = proposal.get("assumptions")
    if not isinstance(assumptions, Sequence) or isinstance(assumptions, (str, bytes, bytearray)):
        return []
    rows: list[tuple[str, str]] = []
    for index, row in enumerate(assumptions, 1):
        identifier = f"ASM-{index:03d}"
        statement = ""
        if isinstance(row, Mapping):
            identifier = normalize_string(row.get("id")) or identifier
            statement = normalize_string(row.get("statement") or row.get("value") or row.get("text"))
        else:
            statement = normalize_string(row)
        if statement:
            rows.append((identifier, statement.strip(" .")))
    return rows


def _accepted_boundary_statement(proposal: Mapping[str, Any]) -> str:
    for path in (
        "semantic_model.domain_ontology.proof_boundary",
        "intent.proof_boundary",
        "project_brief.proof_boundary",
        "intent.state_object",
    ):
        text = normalize_string(_nested_value(proposal, path)).strip(" .")
        if text:
            return _compact_boundary_statement(text)
    return ""


def _nested_value(source: Mapping[str, Any], path: str) -> Any:
    current: Any = source
    for part in path.split("."):
        if not isinstance(current, Mapping):
            return ""
        current = current.get(part)
    return current


def _compact_boundary_statement(value: str) -> str:
    words = normalize_string(value).strip(" .").split()
    if len(words) <= 14:
        return " ".join(words)
    return " ".join(words[:14])


def _statement_already_present(statement: str, rows: Sequence[tuple[str, str]]) -> bool:
    normalized = normalize_string(statement).strip(" .").casefold()
    return any(normalize_string(existing).strip(" .").casefold() == normalized for _identifier, existing in rows)


def _component_contract_output_target(target_path: str) -> bool:
    return target_path.startswith("components[") and target_path.endswith(".component_contract.produced_outputs")


def _component_contract_output_patch_value(proposal: Mapping[str, Any], target_path: str) -> str:
    index = _component_index_from_path(target_path)
    if index is None:
        return ""
    components = proposal.get("components")
    if not isinstance(components, list) or index < 0 or index >= len(components):
        return ""
    row = components[index]
    if not isinstance(row, Mapping):
        return ""
    current = normalize_string(projection_repair_target_value(proposal, target_path))
    for candidate in (_component_source_sentence(row), current):
        normalized = normalize_contract({"produced_outputs": candidate})
        output = normalize_string(normalized.get("produced_outputs")).strip(" .")
        if output:
            completed = produced_outputs_text(output)
            return clean_artifact_sentence(completed)
    return ""


def _component_source_sentence(row: Mapping[str, Any]) -> str:
    for key in ("source_system_description", "responsibility", "description", "boundary"):
        value = normalize_string(row.get(key))
        if value:
            return value
    return ""


def _component_index_from_path(target_path: str) -> int | None:
    prefix = "components["
    if not target_path.startswith(prefix):
        return None
    raw_index = target_path[len(prefix) :].split("]", 1)[0]
    if not raw_index.isdecimal():
        return None
    return int(raw_index)


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


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


def _structured_patch_timeout_seconds(
    remaining_seconds: float,
    *,
    source_fallback_ready: bool = False,
) -> float:
    try:
        remaining = float(remaining_seconds)
    except (TypeError, ValueError):
        return 0.0
    if remaining <= 12.0:
        return 0.0
    cap = 12.0 if source_fallback_ready else 60.0
    return round(min(cap, max(0.0, remaining - 8.0)), 3)


_PLANNER_OPERATION_KEYS = frozenset(
    {
        "operation_id",
        "target_layer",
        "target_path",
        "semantic_node_id",
        "issue_code",
        "source_finding",
        "operation_kind",
        "repair_owner",
        "projection_kind",
        "affected_projections",
        "requested_action",
        "rejected_interpretation",
        "replacement_fact",
        "confidence",
    }
)


def _planner_patchset_request(patchset: Mapping[str, Any]) -> dict[str, Any]:
    """Return the smallest PatchSet request a provider needs to plan a patch."""

    operations = patchset.get("operations")
    compact_operations: list[dict[str, Any]] = []
    if isinstance(operations, list):
        for operation in operations:
            if not isinstance(operation, Mapping):
                continue
            compact_operations.append(
                {
                    key: operation.get(key)
                    for key in _PLANNER_OPERATION_KEYS
                    if key in operation and operation.get(key) not in (None, "")
                }
            )
    return {
        "version": str(patchset.get("version") or "").strip(),
        "status": str(patchset.get("status") or "").strip(),
        "operation_count": len(compact_operations),
        "operations": compact_operations,
    }


def _structured_patch_review_report(
    repair_context: GreenfieldPreconfirmRepairContext,
) -> dict[str, Any]:
    return {
        "version": "odylith.greenfield.preconfirm.review_report.v1",
        "status": str(getattr(repair_context.report, "status", "") or "").strip(),
        "findings": [issue.to_dict() for issue in repair_context.issues],
    }


def _structured_patch_evidence(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPreconfirmRepairContext,
) -> dict[str, Any]:
    return {
        "intent": _selected_intent_evidence(proposal),
        "semantic_model_targets": _semantic_model_target_evidence(proposal, repair_context=repair_context),
        "quality_lens_status": str(repair_context.quality_lenses.get("status") or "").strip()
        if isinstance(repair_context.quality_lenses, Mapping)
        else "",
        "semantic_compiler_status": str(repair_context.semantic_compiler.get("status") or "").strip()
        if isinstance(repair_context.semantic_compiler, Mapping)
        else "",
        "visible_result": dict(repair_context.semantic_compiler.get("visible_result", {}))
        if isinstance(repair_context.semantic_compiler, Mapping)
        and isinstance(repair_context.semantic_compiler.get("visible_result"), Mapping)
        else {},
        "issues": [issue.to_dict() for issue in repair_context.issues],
        "patch_targets": _patch_target_evidence(proposal, repair_context=repair_context),
    }


def _selected_intent_evidence(proposal: Mapping[str, Any]) -> dict[str, Any]:
    intent = proposal.get("intent")
    if not isinstance(intent, Mapping):
        return {}
    keys = (
        "title",
        "product_story",
        "state_object",
        "first_path",
        "proof_boundary",
        "human_actors",
        "external_systems",
        "internal_systems",
        "non_goals",
    )
    return {key: intent.get(key) for key in keys if intent.get(key) not in (None, "", [], {})}


def _semantic_model_target_evidence(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPreconfirmRepairContext,
) -> list[dict[str, Any]]:
    patchset = repair_context.patchset_request if isinstance(repair_context.patchset_request, Mapping) else {}
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return []
    evidence: list[dict[str, Any]] = []
    for operation in operations:
        if not isinstance(operation, Mapping):
            continue
        if normalize_string(operation.get("target_layer")) != "semantic_model":
            continue
        target_path = normalize_string(operation.get("target_path"))
        if not target_path:
            continue
        evidence.append(
            {
                "operation_id": normalize_string(operation.get("operation_id")),
                "target_path": target_path,
                "semantic_node_id": normalize_string(operation.get("semantic_node_id")),
                "current_value": projection_repair_target_value(proposal, target_path),
            }
        )
    return evidence


def _patch_target_evidence(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPreconfirmRepairContext,
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


def _structured_patch_profile(
    config: odylith_reasoning.ReasoningConfig,
    provider: Any,
) -> odylith_reasoning.StructuredReasoningProfile:
    provider_name = odylith_reasoning.provider_failure_metadata(provider).get("provider", "")
    if provider_name in {"codex-cli", "claude-cli", "openai-compatible"}:
        return odylith_reasoning.cheap_structured_reasoning_profile(config)
    return odylith_reasoning.StructuredReasoningProfile(
        provider=provider_name,
        model=str(getattr(config, "model", "") or "").strip(),
        reasoning_effort="",
    )


def _provider_reasoning_effort(
    config: odylith_reasoning.ReasoningConfig,
    provider: Any,
    *,
    patchset: Mapping[str, Any] | None = None,
    profile: odylith_reasoning.StructuredReasoningProfile | None = None,
) -> str:
    provider_name = odylith_reasoning.provider_failure_metadata(provider).get("provider", "")
    if provider_name == "codex-cli":
        return _patch_planner_effort(
            config.codex_reasoning_effort,
            explicit_env_key="ODYLITH_REASONING_CODEX_REASONING_EFFORT",
            patchset=patchset,
            default_effort=str(getattr(profile, "reasoning_effort", "") or ""),
        )
    if provider_name == "claude-cli":
        return _patch_planner_effort(
            config.claude_reasoning_effort,
            explicit_env_key="ODYLITH_REASONING_CLAUDE_REASONING_EFFORT",
            patchset=patchset,
            default_effort=str(getattr(profile, "reasoning_effort", "") or ""),
        )
    return ""


def _patch_planner_effort(
    configured: str,
    *,
    explicit_env_key: str,
    patchset: Mapping[str, Any] | None = None,
    default_effort: str = "",
) -> str:
    if str(os.environ.get(explicit_env_key, "")).strip():
        return configured
    if _single_semantic_patch_operation(patchset):
        return "low"
    return str(default_effort or "").strip() or "medium"


def _single_semantic_patch_operation(patchset: Mapping[str, Any] | None) -> bool:
    if not isinstance(patchset, Mapping):
        return False
    operations = patchset.get("operations")
    if not isinstance(operations, list) or len(operations) != 1:
        return False
    operation = operations[0]
    return isinstance(operation, Mapping) and normalize_string(operation.get("target_layer")) == "semantic_model"


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
