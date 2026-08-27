"""Own the single whole-candidate Greenfield semantic author call."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import time
from typing import Any

from greenfield_semantic_case_evidence import case_prompt
from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_source_graph_author import run_source_meaning_author
from greenfield_semantic_structured_host import (
    HostStageTimeout,
    elapsed_ms,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_source_meaning_author_run,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_author_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_meaning import (
    SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
)


AUTHOR_MAX_SECONDS = 54
AUTHOR_COUNT = 1


@dataclass(frozen=True)
class AuthoringWaveBudget:
    """Time and topology available to the zero-retry semantic wave."""

    author_seconds: int
    topology_mode: str


def run_authoring_wave(
    *,
    corpus_path: Path,
    case_id: str,
    host_profile: str,
    budget: AuthoringWaveBudget,
) -> tuple[dict[str, Any] | None, tuple[str, str, str] | None]:
    """Return one unchanged typed graph from one holistic author call."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_catalog = semantic_evidence_block_catalog(
        {"operator_prompt": prompt_text, "operator_edit": ""}
    )
    model_budget = min(AUTHOR_MAX_SECONDS, budget.author_seconds)
    started_ns = time.monotonic_ns()
    profile = standard_author_profile(host_profile, 0)
    try:
        result = run_source_meaning_author(
            prompt_text=prompt_text,
            evidence_catalog=evidence_catalog,
            model=profile["model"],
            reasoning_effort=profile["reasoning_effort"],
            budget_seconds=model_budget,
            host_profile=host_profile,
        )
    except HostStageTimeout as error:
        author = _failed_author(
            case_id, host_profile, profile, "deadline", str(error), started_ns
        )
        return author, ("deadline", "source_meaning_author", str(error))
    except ValueError as error:
        author = _failed_author(
            case_id, host_profile, profile, "typed", str(error), started_ns
        )
        return author, ("typed", "source_meaning_author", str(error))
    except RuntimeError as error:
        author = _failed_author(
            case_id, host_profile, profile, "environment", str(error), started_ns
        )
        return author, ("environment", "source_meaning_author", str(error))
    return _successful_author(
        case_id=case_id,
        host_profile=host_profile,
        model=profile["model"],
        reasoning_effort=profile["reasoning_effort"],
        model_budget=model_budget,
        result=result,
    ), None


def _successful_author(
    *,
    case_id: str,
    host_profile: str,
    model: str,
    reasoning_effort: str,
    model_budget: int,
    result: dict[str, Any],
) -> dict[str, Any]:
    run_seed = {
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "budget_seconds": model_budget,
        "wall_ms": int(result["wall_ms"]),
        "graph_sha256": str(result["graph_sha256"]),
    }
    run = {
        "version": SEMANTIC_SOURCE_MEANING_AUTHOR_RUN_VERSION,
        "capability_profile": "frontier_semantic_reasoning",
        "run_id": (
            "standard:source-meaning-author:"
            + canonical_sha256(run_seed)
        ),
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "budget_seconds": model_budget,
        "wall_ms": int(result["wall_ms"]),
        "usage": dict(result["usage"]),
        "graph_sha256": str(result["graph_sha256"]),
        "model_call_count": 1,
        "restart_count": 0,
    }
    require_semantic_source_meaning_author_run(
        run, graph_sha256=str(result["graph_sha256"])
    )
    return {
        "stage": "source_meaning_author",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "status": "completed",
        "failure_kind": "",
        "failure": "",
        "graph": dict(result["graph"]),
        "graph_sha256": str(result["graph_sha256"]),
        "author_run": run,
        "usage": dict(result["usage"]),
        "wall_ms": int(result["wall_ms"]),
        "model_call_count": AUTHOR_COUNT,
    }


def _failed_author(
    case_id: str,
    host_profile: str,
    profile: dict[str, str],
    failure_kind: str,
    message: str,
    started_ns: int,
) -> dict[str, Any]:
    return {
        "stage": "source_meaning_author",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": profile["model"],
        "reasoning_effort": profile["reasoning_effort"],
        "status": "failed",
        "failure_kind": failure_kind,
        "failure": message,
        "graph": None,
        "graph_sha256": "",
        "author_run": None,
        "usage": {},
        "wall_ms": elapsed_ms(started_ns),
        "model_call_count": AUTHOR_COUNT,
    }


__all__ = [
    "AUTHOR_COUNT",
    "AUTHOR_MAX_SECONDS",
    "AuthoringWaveBudget",
    "run_authoring_wave",
]
