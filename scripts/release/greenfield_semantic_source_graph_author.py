"""Author one immutable Greenfield source-meaning graph."""

from __future__ import annotations

from collections.abc import Mapping
import json
from threading import Event
from typing import Any

from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    apply_semantic_source_meaning_completeness_gate,
    bind_semantic_source_meaning_graph,
    semantic_source_meaning_contract,
    semantic_source_meaning_provider_schema,
    semantic_source_meaning_sha256,
)


def run_source_meaning_author(
    *,
    prompt_text: str,
    evidence_catalog: Mapping[str, Mapping[str, Any]],
    model: str,
    reasoning_effort: str,
    budget_seconds: int,
    host_profile: str = "codex",
    cancel_event: Event | None = None,
) -> dict[str, Any]:
    """Run the sole semantic-authority call and bind exact source custody."""

    contract = semantic_source_meaning_contract(evidence_catalog)
    provider_graph, usage, wall_ms = run_structured_host(
        schema=semantic_source_meaning_provider_schema(evidence_catalog),
        prompt=(
            "Author the final source-meaning graph directly from the complete exact "
            "evidence. Preserve the whole meaning and obey every fixed product law. "
            "Ask one focused question only when a material product decision is "
            "unsettled. Return JSON only.\n"
            + json.dumps(
                contract,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        ),
        model=model,
        reasoning_effort=reasoning_effort,
        budget_seconds=budget_seconds,
        cancel_event=cancel_event,
        temporary_prefix="odylith-source-meaning-author-",
        host_profile=host_profile,
    )
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    graph = apply_semantic_source_meaning_completeness_gate(
        bind_semantic_source_meaning_graph(
            provider_graph,
            evidence_catalog=evidence_catalog,
            evidence_sources=evidence_sources,
        )
    )
    return {
        "graph": graph,
        "graph_sha256": semantic_source_meaning_sha256(graph),
        "usage": dict(usage),
        "wall_ms": wall_ms,
    }


__all__ = ["run_source_meaning_author"]
