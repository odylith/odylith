"""Run one source challenge followed by immutable-source graph completion."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from pathlib import Path
from threading import Event
import time
from typing import Any

from greenfield_semantic_source_graph_author import run_source_graph_author
from greenfield_semantic_standard_prompts import completion_graph_prompt
from greenfield_semantic_structured_host import HostStageTimeout, run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    require_atomic_source_candidates,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_completion_partitions import (
    apply_semantic_implementation_assignments,
    semantic_architecture_edge_object_ids,
    semantic_completion_citation_registry,
    semantic_graph_completion_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    canonical_parallel_materiality_decision,
    require_authorized_source_assumptions,
    source_with_authorized_assumptions,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_partition_custody import (
    accepted_partitioned_evidence_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
    SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
    combine_source_authoring_partitions,
    compile_source_partitioned_graph,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    bind_semantic_evidence_blocks,
    semantic_evidence_block_catalog,
)


EXPERIMENT_VERSION = "odylith.greenfield.production-standard-stage.v5"


class CompletionStageIncomplete(ValueError):
    """Carry an admitted source graph into a completion-only failure receipt."""

    def __init__(self, message: str, *, receipt: Mapping[str, Any]) -> None:
        super().__init__(message)
        self.receipt = dict(receipt)


def run_source_graph_case(
    *, corpus_path: Path, case_id: str, model: str, reasoning_effort: str,
    output_path: Path, model_budget_seconds: int,
    cancel_event: Event | None = None,
    host_profile: str = "codex",
) -> dict[str, Any]:
    """Author one source-only graph for the parallel first wave."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
    reasoning = run_source_graph_author(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=model_budget_seconds,
        cancel_event=cancel_event,
        host_profile=host_profile,
    )
    usage = _combined_usage(*reasoning["usage_rows"])
    source = reasoning["source"]
    raw_source = {
        "source_candidates": reasoning["candidates"],
        "source_path": {
            "version": SEMANTIC_SOURCE_PATH_GRAPH_VERSION,
            "path": source["path"],
        },
        "source_boundary": {
            "version": SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION,
            "boundary": source["boundary"],
        },
    }
    source_receipt = _mapping(
        bind_semantic_evidence_blocks(raw_source, catalog=evidence_catalog),
        "semantic source author",
    )
    receipt = _stage_receipt(
        stage="source_graph",
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        model_budget_seconds=model_budget_seconds,
        wall_ms=int(reasoning["wall_ms"]),
        usage=usage,
        prompt_text=str(reasoning["prompt_text"]),
        candidate=_mapping(source_receipt.get("source_candidates"), "source candidates"),
    )
    receipt["phase_wall_ms"] = reasoning["phase_wall_ms"]
    receipt["model_call_count"] = len(reasoning["usage_rows"])
    receipt["source_path"] = _require_source_path(source_receipt.get("source_path"))
    receipt["source_boundary"] = _require_source_boundary(
        source_receipt.get("source_boundary")
    )
    try:
        receipt["candidate"] = require_atomic_source_candidates(
            source_receipt.get("source_candidates"), evidence_sources=evidence_sources
        )
        receipt["validation_status"] = "passed"
        receipt["validation_error"] = ""
    except ValueError as error:
        receipt["validation_status"] = "failed"
        receipt["validation_error"] = str(error)
    _write(output_path, receipt)
    if receipt["validation_status"] != "passed":
        raise ValueError(str(receipt["validation_error"]))
    return receipt


def run_graph_completion_case(
    *, corpus_path: Path, case_id: str, model: str, reasoning_effort: str,
    output_path: Path, model_budget_seconds: int,
    resume_source: Mapping[str, Any], materiality_decision: Mapping[str, Any],
    completion_topology: str,
    cancel_event: Event | None = None,
    host_profile: str = "codex",
) -> dict[str, Any]:
    """Complete one immutable source graph after independent materiality review."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
    raw_materiality = _mapping(materiality_decision, "materiality decision")
    validated_materiality = canonical_parallel_materiality_decision(raw_materiality)
    started_ns = time.monotonic_ns()
    source = _mapping(resume_source, "resumed semantic source graph")
    source = source_with_authorized_assumptions(source, validated_materiality)
    require_authorized_source_assumptions(source, validated_materiality)
    completion_source = compile_source_partitioned_graph(source)
    citation_registry = semantic_completion_citation_registry(completion_source)
    edge_object_ids = semantic_architecture_edge_object_ids(completion_source)
    prompt = completion_graph_prompt(
        source=completion_source,
        citation_registry=citation_registry,
        edge_object_ids=edge_object_ids,
        model_budget_seconds=model_budget_seconds,
        topology_mode=completion_topology,
    )
    try:
        completion_candidate, usage, wall_ms = run_structured_host(
            schema=semantic_graph_completion_schema(
                source_citation_ids=tuple(citation_registry),
                edge_object_ids=edge_object_ids,
                topology_mode=completion_topology,
            ),
            prompt=prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=model_budget_seconds,
            temporary_prefix="odylith-standard-graph-completion-",
            cancel_event=cancel_event,
            host_profile=host_profile,
        )
    except HostStageTimeout as error:
        source_candidate = _mapping(
            bind_semantic_evidence_blocks(source, catalog=evidence_catalog),
            "semantic source graph",
        )
        receipt = _stage_receipt(
            stage="graph_completion",
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            model_budget_seconds=model_budget_seconds,
            wall_ms=max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000),
            usage={},
            prompt_text=prompt,
            candidate=source_candidate,
        )
        receipt.update(
            {
                "model_call_count": 1,
                "source_candidate": source_candidate,
                "failed_phase": "completion",
                "validation_status": "partial_source_graph",
                "validation_error": str(error),
            }
        )
        _write(output_path, receipt)
        raise CompletionStageIncomplete(
            "typed completion stage exceeded its budget", receipt=receipt
        ) from error
    completion_candidate = _mapping(completion_candidate, "Semantic graph completion")
    try:
        completion = apply_semantic_implementation_assignments(
            completion_candidate,
            edge_object_ids=edge_object_ids,
            citation_registry=citation_registry,
        )
    except ValueError as error:
        receipt = _stage_receipt(
            stage="graph_completion",
            case_id=case_id,
            host_profile=host_profile,
            model=model,
            reasoning_effort=reasoning_effort,
            model_budget_seconds=model_budget_seconds,
            wall_ms=wall_ms,
            usage=usage,
            prompt_text=prompt,
            candidate=completion_candidate,
        )
        receipt.update(
            {
                "model_call_count": 1,
                "validation_status": "failed",
                "validation_error": str(error),
            }
        )
        _write(output_path, receipt)
        raise
    completion["clarification"] = {
        "question": "",
        "fields": [],
        "source_refs": [],
    }
    candidate = {
        "version": SEMANTIC_PARTITIONED_AUTHOR_VERSION,
        "source": source,
        "completion": completion,
    }
    accepted_partitioned_evidence_catalog(candidate, catalog=evidence_catalog)
    candidate = _mapping(
        bind_semantic_evidence_blocks(candidate, catalog=evidence_catalog),
        "partitioned author",
    )
    receipt = _stage_receipt(
        stage="graph_completion",
        case_id=case_id,
        host_profile=host_profile,
        model=model,
        reasoning_effort=reasoning_effort,
        model_budget_seconds=model_budget_seconds,
        wall_ms=wall_ms,
        usage=usage,
        prompt_text=prompt,
        candidate=candidate,
    )
    receipt.update(
        {
            "model_call_count": 1,
            "phase_wall_ms": {"source_graph": 0, "graph_completion": wall_ms},
            "validation_status": "passed",
            "validation_error": "",
        }
    )
    _write(output_path, receipt)
    return receipt


def case_prompt(*, corpus_path: Path, case_id: str) -> str:
    """Load one development prompt without reading expected annotations."""

    corpus = _mapping(json.loads(corpus_path.read_text(encoding="utf-8")), "corpus")
    cases = _rows(corpus.get("cases"), "corpus cases")
    matches = [row for row in cases if row.get("case_id") == case_id]
    if len(matches) != 1:
        raise RuntimeError(f"development corpus does not contain one case: {case_id}")
    prompt = str(matches[0].get("prompt") or "").strip()
    if not prompt:
        raise RuntimeError("development case prompt is empty")
    return prompt


def source_graph(value: Mapping[str, Any]) -> dict[str, Any]:
    """Combine accepted source partitions without reinterpreting them."""

    return combine_source_authoring_partitions(
        _require_source_path(value.get("source_path")),
        _require_source_boundary(value.get("source_boundary")),
    )


def _combined_usage(*rows: Mapping[str, Any]) -> dict[str, int]:
    keys = {key for row in rows for key, value in row.items() if isinstance(value, int)}
    return {key: sum(int(row.get(key, 0)) for row in rows) for key in sorted(keys)}


def _stage_receipt(
    *, stage: str, case_id: str, host_profile: str, model: str,
    reasoning_effort: str,
    model_budget_seconds: int, wall_ms: int, usage: Mapping[str, Any],
    prompt_text: str, candidate: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "version": EXPERIMENT_VERSION,
        "stage": stage,
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": wall_ms,
        "usage": dict(usage),
        "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
        "candidate": dict(candidate),
    }


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _require_source_path(value: Any) -> dict[str, Any]:
    source_path = _mapping(value, "semantic source path")
    if (
        set(source_path) != {"version", "path"}
        or source_path.get("version") != SEMANTIC_SOURCE_PATH_GRAPH_VERSION
    ):
        raise ValueError("Semantic critic source path is invalid")
    return source_path


def _require_source_boundary(value: Any) -> dict[str, Any]:
    source_boundary = _mapping(value, "semantic source boundary")
    if (
        set(source_boundary) != {"version", "boundary"}
        or source_boundary.get("version") != SEMANTIC_SOURCE_BOUNDARY_GRAPH_VERSION
    ):
        raise ValueError("Semantic critic source boundary is invalid")
    return source_boundary


def _rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


__all__ = [
    "CompletionStageIncomplete", "case_prompt", "run_graph_completion_case",
    "run_source_graph_case", "source_graph",
]
