"""Measure a prompt-only Greenfield materiality screen against the standard tier."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from threading import Event
from typing import Any

from greenfield_semantic_standard_path_experiment import case_prompt
from greenfield_semantic_structured_host import run_structured_host
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_protocol,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_parallel_materiality import (
    canonical_parallel_materiality_decision,
    parallel_materiality_decision_schema,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_source_citations import (
    semantic_evidence_block_catalog,
    resolved_semantic_source_refs,
    semantic_source_ref_schema,
)


SCREEN_VERSION = "odylith.greenfield.materiality-screen.v3"


def run_screen(
    *, corpus_path: Path, case_id: str, model: str, reasoning_effort: str,
    output_path: Path, model_budget_seconds: int, cancel_event: Event | None = None,
    host_profile: str = "codex",
) -> dict[str, Any]:
    """Run one no-retry prompt-only materiality screen."""

    prompt_text = case_prompt(corpus_path=corpus_path, case_id=case_id)
    evidence_sources = {"operator_prompt": prompt_text, "operator_edit": ""}
    evidence_catalog = semantic_evidence_block_catalog(evidence_sources)
    authoring = semantic_intent_authoring_protocol()
    contract = {
        "deadline": {"stage_seconds": model_budget_seconds, "standard_seconds": 60, "retries": 0},
        "materiality_field_semantics": authoring["materiality_field_semantics"],
        "materiality_decision_rules": authoring["materiality_decision_rules"],
        "materiality_field_output": (
            "Return every canonical field key with its evidence status. The separate outcome "
            "object records either authorization or exactly one material clarification; field "
            "rows never choose among the clarification alternatives."
        ),
        "semantic_kind_disambiguation": authoring["semantic_kind_disambiguation"],
        "policy_kind_authority": (
            "Classify negative evidence by its relationship to the accepted path. A limit on the "
            "accepted path's execution, access, or side effects belongs only to constraint. A separate "
            "capability or outcome that the product must not provide belongs only to non_goal. Never "
            "duplicate one statement across both kinds, and never decide by wording, grammar, tokens, "
            "or a downstream graph proposal."
        ),
        "outcome_requirements": authoring["outcome_requirements"],
        "forbidden_mechanisms": authoring["forbidden_mechanisms"],
        "evidence": (
            "Use only the operator prompt. Cite the smallest exact source substring that contains "
            "one complete semantic proposition; return source_id, the byte-exact quote, and its "
            "one-based occurrence. Never reuse one compound citation across constraint and "
            "non_goal. Deterministic code validates every citation against the source bytes. "
            "Ignore discarded or superseded labels."
        ),
        "evidence_blocks": {
            ref_id: {"source_id": row["source_id"], "quote": row["quote"]}
            for ref_id, row in evidence_catalog.items()
        },
    }
    prompt = (
        "Decide materiality only. Do not author facts, relations, components, or prose. Use no "
        "tools, files, retries, validator feedback, regex, or token heuristics.\n"
        f"OPERATOR_PROMPT\n{prompt_text}\nCONTRACT\n"
        f"{json.dumps(contract, ensure_ascii=False, separators=(',', ':'), sort_keys=True)}"
    )
    candidate, usage, wall_ms = run_structured_host(
        schema=parallel_materiality_decision_schema(
            source_ref_schema=semantic_source_ref_schema()
        ), prompt=prompt, model=model,
        reasoning_effort=reasoning_effort, budget_seconds=model_budget_seconds,
        temporary_prefix="odylith-materiality-screen-",
        cancel_event=cancel_event,
        host_profile=host_profile,
    )
    if not isinstance(candidate, dict):
        raise ValueError("materiality screen output must be a JSON object")
    resolved_semantic_source_refs(candidate, evidence_sources=evidence_sources)
    canonical_parallel_materiality_decision(candidate)
    receipt = {
        "version": SCREEN_VERSION,
        "stage": "materiality_critic",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": model,
        "reasoning_effort": reasoning_effort,
        "model_budget_seconds": model_budget_seconds,
        "wall_ms": wall_ms,
        "usage": usage,
        "model_call_count": 1,
        "validation_status": "passed",
        "validation_error": "",
        "prompt_sha256": hashlib.sha256(prompt_text.encode()).hexdigest(),
        "decision": candidate,
    }
    output_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    return receipt


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--model", default="gpt-5.6-luna")
    parser.add_argument("--reasoning-effort", default="low")
    parser.add_argument("--host-profile", choices=("codex", "claude"), default="codex")
    parser.add_argument("--model-budget-seconds", type=int, default=10)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = run_screen(
        corpus_path=args.corpus, case_id=args.case_id, model=args.model,
        reasoning_effort=args.reasoning_effort, output_path=args.output,
        model_budget_seconds=args.model_budget_seconds,
        host_profile=args.host_profile,
    )
    print(json.dumps({"case_id": receipt["case_id"], "wall_ms": receipt["wall_ms"],
                      "decision": receipt["decision"]}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
