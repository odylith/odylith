"""Author and independently reconcile one whole Greenfield source graph."""

from __future__ import annotations

from collections.abc import Mapping
from threading import Event
from typing import Any

from greenfield_semantic_standard_prompts import (
    partitioned_graph_hypothesis_prompt,
    unified_source_graph_prompt,
)
from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_layered_authoring import (
    SEMANTIC_PARTITIONED_AUTHOR_VERSION,
    semantic_partitioned_author_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION,
    compile_source_partitioned_graph,
    semantic_source_partitioned_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    resolved_semantic_source_refs,
    semantic_source_ref_schema,
)


class StructuredSourceHypothesisRejected(ValueError):
    """Carry one provider-valid source object rejected by typed semantic laws."""

    def __init__(
        self, message: str, *, source: Mapping[str, Any], usage: Mapping[str, Any],
        wall_ms: int, prompt_text: str,
    ) -> None:
        super().__init__(message)
        self.source = dict(source)
        self.usage = dict(usage)
        self.wall_ms = wall_ms
        self.prompt_text = prompt_text


def run_partitioned_graph_hypothesis(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model: str, reasoning_effort: str, budget_seconds: int,
    cancel_event: Event | None = None, host_profile: str = "codex",
) -> dict[str, Any]:
    """Return one full typed hypothesis authored independently at time zero."""

    prompt = partitioned_graph_hypothesis_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=budget_seconds,
    )
    candidate, usage, wall_ms = run_structured_host(
        schema=semantic_partitioned_author_schema(
            source_ref_schema=semantic_source_ref_schema(),
            system_count=1,
        ),
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        temporary_prefix="odylith-partitioned-graph-author-",
        cancel_event=cancel_event,
        host_profile=host_profile,
    )
    if (
        not isinstance(candidate, Mapping)
        or candidate.get("version") != SEMANTIC_PARTITIONED_AUTHOR_VERSION
    ):
        raise ValueError("partitioned graph hypothesis uses an unsupported version")
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    resolved_semantic_source_refs(candidate, evidence_sources=evidence_sources)
    source = _bound_source(
        candidate.get("source"), evidence_sources=evidence_sources
    )
    return {
        "candidate": {**dict(candidate), "source": source},
        "usage": dict(usage),
        "wall_ms": wall_ms,
        "prompt_text": prompt,
    }


def run_source_graph_hypothesis(
    *, prompt_text: str, evidence_catalog: Mapping[str, Mapping[str, Any]],
    model: str, reasoning_effort: str, budget_seconds: int,
    cancel_event: Event | None = None, host_profile: str = "codex",
) -> dict[str, Any]:
    """Return one whole-source hypothesis with no final semantic authority."""

    prompt = unified_source_graph_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=budget_seconds,
    )
    candidate, usage, wall_ms = run_structured_host(
        schema=semantic_source_partitioned_graph_schema(
            source_ref_schema=semantic_source_ref_schema()
        ),
        prompt=prompt,
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        temporary_prefix="odylith-unified-source-author-",
        cancel_event=cancel_event,
        host_profile=host_profile,
    )
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    if not isinstance(candidate, Mapping):
        raise ValueError("whole-source author did not return a source graph")
    resolved_semantic_source_refs(candidate, evidence_sources=evidence_sources)
    try:
        source = _bound_source(candidate, evidence_sources=evidence_sources)
    except ValueError as error:
        raise StructuredSourceHypothesisRejected(
            str(error),
            source=candidate,
            usage=usage,
            wall_ms=wall_ms,
            prompt_text=prompt,
        ) from error
    return {
        "source": source,
        "usage": dict(usage),
        "wall_ms": wall_ms,
        "prompt_text": prompt,
    }


def _bound_source(
    value: Any, *, evidence_sources: Mapping[str, str],
) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("whole-source author did not return a source graph")
    source = dict(value)
    if source.get("version") != SEMANTIC_SOURCE_PARTITIONED_GRAPH_VERSION:
        raise ValueError("whole-source graph uses an unsupported version")
    resolved_semantic_source_refs(source, evidence_sources=evidence_sources)
    compile_source_partitioned_graph(source)
    return dict(source)


__all__ = [
    "StructuredSourceHypothesisRejected",
    "run_partitioned_graph_hypothesis",
    "run_source_graph_hypothesis",
]
