"""Independently adjudicate source relations and architecture once."""

from __future__ import annotations

from collections.abc import Mapping
from threading import Event
from typing import Any

from greenfield_semantic_standard_prompts import final_graph_adjudication_prompt
from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    semantic_architecture_edge_object_ids,
    semantic_completion_citation_registry,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_final_adjudication import (
    SEMANTIC_FINAL_ADJUDICATION_VERSION,
    apply_final_adjudication,
    remove_discarded_materiality_refs,
    resolve_final_materiality_decision,
    semantic_candidate_relation_catalog,
    semantic_final_adjudication_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    admit_source_candidates_by_materiality,
    align_source_policy_kinds_to_materiality,
    canonical_parallel_materiality_decision,
    require_materiality_source_coverage,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    compile_source_partitioned_graph,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolved_semantic_source_refs,
    semantic_source_ref_schema,
)


def run_final_graph_adjudication(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    materiality_hypothesis: Mapping[str, Any], source_hypothesis: Mapping[str, Any],
    evidence_sources: Mapping[str, str], model: str, reasoning_effort: str,
    budget_seconds: int, topology_mode: str,
    cancel_event: Event | None = None, host_profile: str = "codex",
) -> dict[str, Any]:
    """Return one admitted relation graph and typed implementation completion."""

    source_admission = admit_source_candidates_by_materiality(
        materiality_hypothesis,
        source_hypothesis,
        evidence_sources=evidence_sources,
    )
    admitted_source = _mapping(
        source_admission.get("source"), "admitted source candidates"
    )
    clarification_only = _clarification_predicted(materiality_hypothesis)
    if not clarification_only:
        admitted_source = align_source_policy_kinds_to_materiality(
            admitted_source, materiality_hypothesis
        )
    candidate_source = compile_source_partitioned_graph(admitted_source)
    boundary = source_hypothesis.get("boundary")
    discarded_hypothesis = (
        boundary.get("discarded_evidence", []) if isinstance(boundary, Mapping) else []
    )
    citations = semantic_completion_citation_registry(candidate_source)
    edge_object_ids = semantic_architecture_edge_object_ids(candidate_source)
    relation_catalog = semantic_candidate_relation_catalog(candidate_source)
    prompt = final_graph_adjudication_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        materiality_hypothesis=materiality_hypothesis,
        source_hypothesis=candidate_source,
        discarded_hypothesis=discarded_hypothesis,
        relation_catalog=relation_catalog,
        citation_registry=citations,
        model_budget_seconds=budget_seconds,
        topology_mode=topology_mode,
        clarification_only=clarification_only,
    )
    candidate, usage, wall_ms = run_structured_host(
        schema=semantic_final_adjudication_schema(
            source=candidate_source,
            source_citation_ids=tuple(citations),
            source_ref_schema=semantic_source_ref_schema(),
            edge_object_ids=edge_object_ids,
            topology_mode=topology_mode,
            clarification_only=clarification_only,
        ),
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        temporary_prefix="odylith-final-graph-adjudicator-",
        cancel_event=cancel_event,
        host_profile=host_profile,
    )
    bound = candidate
    if isinstance(bound, Mapping):
        resolved_semantic_source_refs(bound, evidence_sources=evidence_sources)
    if (
        not isinstance(bound, Mapping)
        or bound.get("version") != SEMANTIC_FINAL_ADJUDICATION_VERSION
    ):
        raise ValueError("final graph adjudicator uses an unsupported version")
    result = _mapping(bound.get("result"), "final graph result")
    decision = resolve_final_materiality_decision(
        result.get("materiality_resolution"),
        hypothesis=materiality_hypothesis,
    )
    discarded_refs = [] if clarification_only else bound.get("discarded_source_refs")
    if not isinstance(discarded_refs, list):
        raise ValueError("final graph discarded evidence is malformed")
    decision = remove_discarded_materiality_refs(
        decision,
        discarded_source_refs=discarded_refs,
        evidence_sources=evidence_sources,
    )
    canonical_parallel_materiality_decision(decision)
    if clarification_only and not _clarification_predicted(decision):
        raise ValueError("clarification-only final adjudication cannot authorize a graph")
    applied = apply_final_adjudication(
        bound,
        source=candidate_source,
        citation_registry=citations,
        clarification_only=clarification_only,
    )
    if applied.get("source_status") == "approved":
        _require_discarded_separation(
            decision=decision,
            adjudication=applied,
            discarded_refs=applied.get("discarded_source_refs"),
        )
        if not clarification_only:
            admitted_source = _mapping(applied.get("source"), "admitted source graph")
            require_materiality_source_coverage(
                decision, admitted_source, evidence_sources=evidence_sources
            )
    return {
        "decision": decision,
        "adjudication": applied,
        "source_candidate_rejections": list(
            source_admission.get("rejected_candidates") or []
        ),
        "usage": dict(usage),
        "wall_ms": wall_ms,
        "prompt_text": prompt,
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a JSON object")
    return dict(value)


def _clarification_predicted(value: Mapping[str, Any]) -> bool:
    outcome = value.get("outcome")
    return (
        isinstance(outcome, Mapping)
        and outcome.get("decision") == "clarification_required"
    )


def _require_discarded_separation(
    *, decision: Mapping[str, Any], adjudication: Mapping[str, Any],
    discarded_refs: Any,
) -> None:
    if not isinstance(discarded_refs, list):
        raise ValueError("final graph discarded evidence is malformed")
    discarded = {_source_ref_key(row) for row in discarded_refs}
    if any(key is None for key in discarded):
        raise ValueError("final graph discarded evidence is malformed")
    if discarded & _nested_source_ref_keys(decision):
        raise ValueError("final materiality admits discarded evidence")
    product_adjudication = {
        key: value for key, value in adjudication.items() if key != "discarded_source_refs"
    }
    if discarded & _nested_source_ref_keys(product_adjudication):
        raise ValueError("final graph admits discarded evidence")


def _nested_source_ref_keys(value: Any) -> set[tuple[str, str, int]]:
    result: set[tuple[str, str, int]] = set()
    if isinstance(value, Mapping):
        if set(value) >= {"source_id", "quote", "occurrence"}:
            key = _source_ref_key(value)
            if key is not None:
                result.add(key)
        for nested in value.values():
            result.update(_nested_source_ref_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            result.update(_nested_source_ref_keys(nested))
    return result


def _source_ref_key(value: Any) -> tuple[str, str, int] | None:
    if not isinstance(value, Mapping) or not isinstance(value.get("occurrence"), int):
        return None
    source_id = str(value.get("source_id") or "")
    quote = str(value.get("quote") or "")
    return (source_id, quote, int(value["occurrence"])) if source_id and quote else None


__all__ = ["run_final_graph_adjudication"]
