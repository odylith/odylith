"""Finish one already-authored Greenfield transaction inside the 90-second tier."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_pipeline_receipts import pipeline_receipt, write_receipt
from greenfield_semantic_case_evidence import case_prompt
from greenfield_semantic_release_support import (
    greenfield_runtime_source_fingerprint,
    mapping,
)
from greenfield_semantic_standard_pipeline_experiment import (
    _compile_packet,
)
from greenfield_semantic_structured_host import elapsed_ms
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    RESCUE_COMPLETION_DEADLINE_SECONDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    require_reusable_standard_handoff,
)


def rescue_budget_contract(
    *, prior_standard_failure_sha256: str, prior_standard_wall_ms: int
) -> dict[str, Any]:
    """Expose only the remaining deterministic portion of the cumulative 90 seconds."""

    remaining_ms = RESCUE_COMPLETION_DEADLINE_SECONDS * 1000 - prior_standard_wall_ms
    if remaining_ms <= 0:
        raise ValueError("standard continuation already exhausted the 90-second envelope")
    return {
        "tier": "rescue",
        "deadline_seconds": RESCUE_COMPLETION_DEADLINE_SECONDS,
        "comparison": "less_than_or_equal",
        "semantic_calls": 0,
        "graph_authorship": 0,
        "candidate_selection": 0,
        "deterministic_continuation_ms": remaining_ms,
        "cumulative_prior_standard_wall_ms": prior_standard_wall_ms,
        "retries": 0,
        "automatic_deep_tier": False,
        "prior_standard_failure_sha256": prior_standard_failure_sha256,
    }


def run_rescue_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    standard_failure_receipt: Mapping[str, Any],
    host_profile: str = "codex",
    evidence_assignment: Mapping[str, Any] | None = None,
    **retired_stage_overrides: str,
) -> dict[str, Any]:
    """Complete deterministic packet/transaction work without semantic authorship."""

    if any(retired_stage_overrides.values()):
        raise ValueError("rescue cannot run a model, select a candidate, or repair meaning")
    predecessor = dict(standard_failure_receipt)
    predecessor_sha256 = require_reusable_standard_handoff(
        predecessor, case_id=case_id
    )
    prior_execution = mapping(
        predecessor.get("mechanism_execution"), "standard execution evidence"
    )
    if prior_execution.get(
        "implementation_fingerprint_sha256"
    ) != greenfield_runtime_source_fingerprint():
        raise ValueError("rescue handoff was produced by different implementation bytes")
    if prior_execution.get("host_profile") != host_profile:
        raise ValueError("rescue host profile differs from its standard handoff")
    prior_wall_ms = int(predecessor.get("wall_ms") or -1)
    if prior_wall_ms != int(prior_execution.get("wall_ms") or -2):
        raise ValueError("rescue predecessor wall time is inconsistent")
    budget = rescue_budget_contract(
        prior_standard_failure_sha256=predecessor_sha256,
        prior_standard_wall_ms=prior_wall_ms,
    )
    if evidence_assignment is not None:
        budget["evidence_assignment"] = dict(evidence_assignment)

    author = mapping(
        predecessor.get("source_meaning_author"), "source-meaning author"
    )
    packet = mapping(predecessor.get("packet"), "Semantic Intent packet")
    prompt = case_prompt(corpus_path=corpus_path, case_id=case_id)
    started_ns = time.monotonic_ns()
    transaction_value = predecessor.get("transaction")
    transaction: dict[str, Any] | None = None
    failure_kind = ""
    failure = ""
    try:
        if isinstance(transaction_value, Mapping):
            transaction = dict(transaction_value)
        else:
            with tempfile.TemporaryDirectory(
                prefix="odylith-deterministic-rescue-"
            ) as temporary:
                transaction = _compile_packet(
                    packet=packet,
                    prompt=prompt,
                    repo_root=Path(temporary) / "consumer",
                )
    except ValueError as error:
        failure_kind = "typed_rescue_failure"
        failure = str(error)
    except (ImportError, OSError, RuntimeError) as error:
        failure_kind = "environment_failure"
        failure = f"{type(error).__name__}: {error}"

    wall_ms = prior_wall_ms + elapsed_ms(started_ns)
    if not failure and wall_ms > RESCUE_COMPLETION_DEADLINE_SECONDS * 1000:
        failure_kind = "rescue_deadline_exceeded"
        failure = "deterministic continuation completed after 90 seconds"
    completed = not failure_kind
    return write_receipt(
        output_path,
        pipeline_receipt(
            case_id=case_id,
            status="completed" if completed else "failed",
            outcome="commit" if completed else failure_kind,
            wall_ms=wall_ms,
            host_profile=host_profile,
            budget=budget,
            author=author,
            packet=packet,
            transaction=transaction,
            failed_stage="" if completed else "deterministic_continuation",
            failure=failure,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--standard-failure", type=Path, required=True)
    parser.add_argument("--host-profile", default="codex")
    args = parser.parse_args(argv)
    predecessor = mapping(
        json.loads(args.standard_failure.read_text(encoding="utf-8")),
        "standard failure receipt",
    )
    result = run_rescue_pipeline(
        corpus_path=args.corpus,
        case_id=args.case_id,
        output_path=args.output,
        standard_failure_receipt=predecessor,
        host_profile=args.host_profile,
    )
    return 0 if result["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["rescue_budget_contract", "run_rescue_pipeline"]
