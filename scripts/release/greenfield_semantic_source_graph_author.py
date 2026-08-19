"""Author one source-only Greenfield graph under a bounded host turn."""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from threading import Event
import time
from typing import Any

from greenfield_semantic_standard_prompts import (
    source_boundary_prompt,
    source_path_prompt,
)
from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_atomic_source_custody import (
    atomic_source_candidates_from_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_authoring import (
    combine_source_authoring_partitions,
    compile_source_partitioned_graph,
    semantic_source_boundary_graph_schema,
    semantic_source_path_graph_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    bind_semantic_evidence_blocks,
    semantic_evidence_block_schema,
)


def run_source_graph_author(
    *,
    prompt_text: str,
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    model: str,
    reasoning_effort: str,
    budget_seconds: int,
    cancel_event: Event | None = None,
    host_profile: str = "codex",
) -> dict[str, Any]:
    """Return source truth without materiality or implementation authority."""

    path_prompt = source_path_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=budget_seconds,
    )
    boundary_prompt = source_boundary_prompt(
        prompt_text=prompt_text,
        evidence_catalog=evidence_catalog,
        model_budget_seconds=budget_seconds,
    )
    source_ref_schema = semantic_evidence_block_schema(evidence_catalog)
    stop_event = cancel_event or Event()
    started_ns = time.monotonic_ns()
    with ThreadPoolExecutor(max_workers=2) as executor:
        path_future = executor.submit(
            run_structured_host,
            schema=semantic_source_path_graph_schema(
                source_ref_schema=source_ref_schema
            ),
            prompt=path_prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            temporary_prefix="odylith-source-path-author-",
            cancel_event=stop_event,
            host_profile=host_profile,
        )
        boundary_future = executor.submit(
            run_structured_host,
            schema=semantic_source_boundary_graph_schema(
                source_ref_schema=source_ref_schema
            ),
            prompt=boundary_prompt,
            model=model,
            reasoning_effort=reasoning_effort,
            budget_seconds=budget_seconds,
            temporary_prefix="odylith-source-boundary-author-",
            cancel_event=stop_event,
            host_profile=host_profile,
        )
        try:
            path, path_usage, path_wall_ms = path_future.result()
            boundary, boundary_usage, boundary_wall_ms = boundary_future.result()
        except Exception:
            stop_event.set()
            raise
    path = bind_semantic_evidence_blocks(path, catalog=evidence_catalog)
    boundary = bind_semantic_evidence_blocks(boundary, catalog=evidence_catalog)
    if not isinstance(path, Mapping) or not isinstance(boundary, Mapping):
        raise ValueError("source-author partition must be a mapping")
    source = combine_source_authoring_partitions(path, boundary)
    compile_source_partitioned_graph(source)
    wall_ms = (time.monotonic_ns() - started_ns) // 1_000_000
    return {
        "candidates": atomic_source_candidates_from_catalog(evidence_catalog),
        "source": dict(source),
        "usage_rows": [dict(path_usage), dict(boundary_usage)],
        "wall_ms": wall_ms,
        "phase_wall_ms": {
            "source_path": path_wall_ms,
            "source_boundary": boundary_wall_ms,
        },
        "prompt_text": f"{path_prompt}\n{boundary_prompt}",
    }


__all__ = ["run_source_graph_author"]
