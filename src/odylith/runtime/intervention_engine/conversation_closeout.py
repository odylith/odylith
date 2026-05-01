"""Closeout Assist composition for intervention conversation bundles."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence

from odylith.runtime.common.value_coercion import normalize_string as _normalize_string
from odylith.runtime.common.value_coercion import normalize_token as _normalize_token
from odylith.runtime.intervention_engine import conversation_artifacts
from odylith.runtime.intervention_engine import conversation_common
from odylith.runtime.intervention_engine import conversation_metrics
from odylith.runtime.intervention_engine import prompt_signal_runtime


def visibility_feedback_phrase(*, request: Any, assistant_summary: str = "") -> tuple[str, str]:
    """Detect product-feedback turns where Assist should not stay silent.

    This is deliberately narrow: a generic short turn still suppresses Assist,
    but explicit feedback about Odylith visibility, hooks, interventions,
    ambient highlights, Observations, Proposals, or Assist deserves a grounded
    closeout even when no files changed.
    """

    return prompt_signal_runtime.visibility_feedback_phrase(
        prompt=conversation_common.field(request, "prompt"),
        assistant_summary=assistant_summary,
    )


def visibility_feedback_requested(*, prompt: Any = "", assistant_summary: str = "") -> bool:
    return prompt_signal_runtime.visibility_feedback_requested(
        prompt=prompt,
        assistant_summary=assistant_summary,
    )


def _assist_has_material_turn_evidence(
    *,
    metrics: Mapping[str, Any],
    artifact_markdown_phrase: str,
    contract_update_markdown_phrase: str,
    validation_phrase: str,
    visibility_markdown_phrase: str,
) -> bool:
    """Return whether the current turn earned a user-visible closeout line.

    Scope alone is not proof. A closeout beat needs current-turn evidence such
    as changed governed artifacts, focused validation, bounded delegated
    execution, or an explicit visibility complaint that should stay alive at
    closeout.
    """

    return bool(
        artifact_markdown_phrase
        or contract_update_markdown_phrase
        or validation_phrase
        or visibility_markdown_phrase
        or (
            bool(metrics.get("grounded_delegate"))
            and int(metrics.get("delegated_leaf_count") or 0) > 0
        )
    )


def _suppressed_assist_payload(
    *,
    metrics: Mapping[str, Any],
    reason: str,
    updated_artifacts: Sequence[Mapping[str, Any]],
    affected_contracts: Sequence[Mapping[str, Any]] = (),
    changed_path_source: str,
) -> dict[str, Any]:
    return {
        "eligible": False,
        "style": "",
        "label": conversation_common.label("assist", markdown=False),
        "preferred_markdown_label": conversation_common.label("assist", markdown=True),
        "text": "",
        "plain_text": "",
        "markdown_text": "",
        "user_win": "",
        "delta": "",
        "proof": "",
        "updated_artifacts": [dict(row) for row in updated_artifacts],
        "affected_contracts": [dict(row) for row in affected_contracts],
        "changed_path_source": changed_path_source,
        "suppressed_reason": reason,
        "metrics": dict(metrics),
    }


def compose_closeout_assist(
    *,
    request: Any,
    decision: Any,
    adoption: Mapping[str, Any],
    repo_root: Path | None = None,
    final_changed_paths: Sequence[str] | None = None,
    changed_path_source: str = "",
    metrics: Mapping[str, Any] | None = None,
    context_rows: Sequence[Mapping[str, Any]] | None = None,
    assistant_summary: str = "",
) -> dict[str, Any]:
    metrics = dict(metrics) if isinstance(metrics, Mapping) else conversation_metrics.evidence_metrics(
        request=request,
        decision=decision,
        adoption=adoption,
    )
    effective_changed_paths = list(final_changed_paths or [])
    if not effective_changed_paths:
        effective_changed_paths = [
            *(conversation_common.field(request, "candidate_paths") or []),
            *(conversation_common.field(request, "claimed_paths") or []),
        ]
        changed_path_source = changed_path_source or "request_seed_paths"
    else:
        changed_path_source = changed_path_source or "supplied_changed_paths"
    updated_artifacts = conversation_artifacts.resolve_updated_artifacts(
        repo_root=repo_root,
        request=request,
        final_changed_paths=effective_changed_paths,
        context_rows=context_rows,
    )
    affected_contracts = conversation_artifacts.affected_contract_rows(
        updated_artifacts=updated_artifacts,
        request=request,
        repo_root=repo_root,
        context_rows=list(context_rows or []),
    )
    if not metrics["grounded"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="not_grounded",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )
    if metrics["requires_widening"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="requires_widening",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )
    if not metrics["route_ready"] and not metrics["grounded_delegate"]:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="not_route_ready",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )

    focus_phrase = ""
    if metrics["focus_path_count"] > 0:
        focus_phrase = conversation_common.count_phrase(metrics["focus_path_count"], "candidate path")
    governance_bits: list[str] = []
    if metrics["workstream_count"] > 0:
        governance_bits.append(conversation_common.count_phrase(metrics["workstream_count"], "workstream"))
    if metrics["component_count"] > 0:
        governance_bits.append(conversation_common.count_phrase(metrics["component_count"], "component"))
    governance_phrase = conversation_common.join_items(governance_bits)
    validation_phrase = (
        conversation_common.count_phrase(metrics["validation_count"], "focused check")
        if metrics["validation_count"] > 0
        else ""
    )
    leaf_phrase = (
        conversation_common.count_phrase(metrics["delegated_leaf_count"], "bounded leaf", "bounded leaves")
        if metrics["delegated_leaf_count"] > 0
        else ""
    )
    bounded_execution_phrase = (
        "keeping execution bounded across "
        f"{conversation_common.count_phrase(metrics['delegated_leaf_count'], 'focused slice')}"
        if metrics["delegated_leaf_count"] > 0
        else ""
    )
    artifact_markdown_phrase, artifact_plain_phrase = conversation_artifacts.artifact_phrase(updated_artifacts)
    updated_contracts = [
        row
        for row in affected_contracts
        if any(
            _normalize_token(row.get("kind")) == _normalize_token(updated.get("kind"))
            and _normalize_string(row.get("id")) == _normalize_string(updated.get("id"))
            for updated in updated_artifacts
            if isinstance(updated, Mapping)
        )
    ]
    contract_update_markdown_phrase, contract_update_plain_phrase = conversation_artifacts.affected_contract_phrase(
        updated_contracts,
        verb="updating",
    )
    contract_scope_markdown_phrase, contract_scope_plain_phrase = conversation_artifacts.affected_contract_phrase(
        affected_contracts,
        verb="staying inside",
    )
    visibility_markdown_phrase, visibility_plain_phrase = visibility_feedback_phrase(
        request=request,
        assistant_summary=assistant_summary,
    )
    has_material_turn_evidence = _assist_has_material_turn_evidence(
        metrics=metrics,
        artifact_markdown_phrase=artifact_markdown_phrase,
        contract_update_markdown_phrase=contract_update_markdown_phrase,
        validation_phrase=validation_phrase,
        visibility_markdown_phrase=visibility_markdown_phrase,
    )

    style = ""
    proof_parts_markdown: list[str] = []
    proof_parts_plain: list[str] = []

    if metrics["grounded_delegate"] and metrics["delegated_leaf_count"] > 0 and focus_phrase:
        style = "grounded_bounded_execution"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"keeping the slice to {focus_phrase}")
        proof_parts_plain.append(f"keeping the slice to {focus_phrase}")
        if metrics["suppress_routing_receipts"]:
            proof_parts_markdown.append(bounded_execution_phrase)
            proof_parts_plain.append(bounded_execution_phrase)
        else:
            proof_parts_markdown.append(f"routing {leaf_phrase}")
            proof_parts_plain.append(f"routing {leaf_phrase}")
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
    elif visibility_markdown_phrase:
        style = "visibility_continuity"
        proof_parts_markdown.append(visibility_markdown_phrase)
        proof_parts_plain.append(visibility_plain_phrase)
    elif governance_phrase and has_material_turn_evidence:
        style = "governed_lane"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif validation_phrase and contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
        elif focus_phrase:
            proof_parts_markdown.append(f"keeping the slice to {focus_phrase}")
            proof_parts_plain.append(f"keeping the slice to {focus_phrase}")
    elif focus_phrase and has_material_turn_evidence:
        style = "shortest_safe_path"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif validation_phrase and contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"grounding the work to {focus_phrase}")
        proof_parts_plain.append(f"grounding the work to {focus_phrase}")
        if validation_phrase:
            proof_parts_markdown.append(f"closing with {validation_phrase}")
            proof_parts_plain.append(f"closing with {validation_phrase}")
    elif validation_phrase:
        style = "focused_validation"
        if contract_update_markdown_phrase or artifact_markdown_phrase:
            proof_parts_markdown.append(contract_update_markdown_phrase or artifact_markdown_phrase)
            proof_parts_plain.append(contract_update_plain_phrase or artifact_plain_phrase)
        elif contract_scope_markdown_phrase:
            proof_parts_markdown.append(contract_scope_markdown_phrase)
            proof_parts_plain.append(contract_scope_plain_phrase)
        proof_parts_markdown.append(f"closing with {validation_phrase}")
        proof_parts_plain.append(f"closing with {validation_phrase}")
    proof_markdown = conversation_common.join_phrases(proof_parts_markdown)
    proof_plain = conversation_common.join_phrases(proof_parts_plain)
    if not style or not proof_markdown or not proof_plain:
        return _suppressed_assist_payload(
            metrics=metrics,
            reason="missing_user_facing_delta",
            updated_artifacts=updated_artifacts,
            affected_contracts=affected_contracts,
            changed_path_source=changed_path_source,
        )

    markdown_text = f"{conversation_common.label('assist', markdown=True)} {proof_markdown}."
    plain_text = f"{conversation_common.label('assist', markdown=False)} {proof_plain}."

    return {
        "eligible": True,
        "style": style,
        "label": conversation_common.label("assist", markdown=False),
        "preferred_markdown_label": conversation_common.label("assist", markdown=True),
        "text": markdown_text,
        "plain_text": plain_text,
        "markdown_text": markdown_text,
        "user_win": "",
        "delta": "",
        "proof": proof_markdown,
        "updated_artifacts": updated_artifacts,
        "affected_contracts": affected_contracts,
        "changed_path_source": changed_path_source,
        "suppressed_reason": "",
        "metrics": metrics,
    }
