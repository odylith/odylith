"""Run the active Greenfield mechanism after one typed standard failure."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import json
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_pipeline_receipts import (
    bounded_receipt,
    write_receipt,
)
from greenfield_semantic_standard_pipeline_experiment import (
    DETERMINISTIC_RESERVE_SECONDS,
    MIN_STANDARD_AUTHOR_SECONDS,
    run_standard_pipeline,
)
from greenfield_semantic_structured_host import elapsed_ms
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    RESCUE_COMPLETION_DEADLINE_SECONDS,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    require_typed_standard_failure,
)


RESCUE_PARALLEL_FIRST_WAVE_SECONDS = 48
RESCUE_AUTHORING_SHARED_SECONDS = 84


def rescue_budget_contract(*, prior_standard_failure_sha256: str) -> dict[str, Any]:
    """Return the one-attempt rescue allocation, with no semantic retry."""

    critical_path = RESCUE_AUTHORING_SHARED_SECONDS + DETERMINISTIC_RESERVE_SECONDS
    if critical_path > RESCUE_COMPLETION_DEADLINE_SECONDS:
        raise RuntimeError("rescue pipeline allocation exceeds 90 seconds")
    return {
        "tier": "rescue",
        "deadline_seconds": RESCUE_COMPLETION_DEADLINE_SECONDS,
        "comparison": "less_than_or_equal",
        "parallel_materiality_and_source_seconds": RESCUE_PARALLEL_FIRST_WAVE_SECONDS,
        "semantic_authoring_shared_seconds": RESCUE_AUTHORING_SHARED_SECONDS,
        "post_first_wave_completion_seconds": "remaining shared semantic budget",
        "packet_and_transaction_reserve_seconds": DETERMINISTIC_RESERVE_SECONDS,
        "critical_path_seconds": critical_path,
        "retries": 0,
        "automatic_deep_tier": False,
        "minimum_completion_seconds": MIN_STANDARD_AUTHOR_SECONDS,
        "completion_topology": "adaptive",
        "prior_standard_failure_sha256": prior_standard_failure_sha256,
    }


def run_rescue_pipeline(
    *,
    corpus_path: Path,
    case_id: str,
    output_path: Path,
    standard_failure_receipt: Mapping[str, Any],
    host_profile: str = "codex",
    critic_model: str = "",
    critic_reasoning_effort: str = "",
    source_model: str = "",
    source_reasoning_effort: str = "",
    author_model: str = "",
    author_reasoning_effort: str = "",
    evidence_assignment: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Run rescue once and preserve its typed standard-failure predecessor."""

    predecessor_sha256 = require_typed_standard_failure(
        standard_failure_receipt, case_id=case_id
    )
    started_ns = time.monotonic_ns()
    with tempfile.TemporaryDirectory(prefix="odylith-rescue-pipeline-") as temporary:
        attempt = run_standard_pipeline(
            corpus_path=corpus_path,
            case_id=case_id,
            output_path=Path(temporary) / "rescue-attempt.json",
            host_profile=host_profile,
            critic_model=critic_model,
            critic_reasoning_effort=critic_reasoning_effort,
            source_model=source_model,
            source_reasoning_effort=source_reasoning_effort,
            author_model=author_model,
            author_reasoning_effort=author_reasoning_effort,
            _first_wave_budget=RESCUE_PARALLEL_FIRST_WAVE_SECONDS,
            _semantic_budget=RESCUE_AUTHORING_SHARED_SECONDS,
            _deadline_seconds=RESCUE_COMPLETION_DEADLINE_SECONDS,
            _budget_contract=rescue_budget_contract(
                prior_standard_failure_sha256=predecessor_sha256
            ),
            _completion_topology="adaptive",
            _evidence_assignment=evidence_assignment,
        )
    wall_ms = elapsed_ms(started_ns)
    complete = attempt["status"] == "completed" and wall_ms <= 90_000
    return write_receipt(
        output_path,
        bounded_receipt(
            case_id=case_id,
            tier="rescue" if complete else "failed",
            wall_ms=wall_ms,
            attempt=attempt,
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--case-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--standard-failure", type=Path, required=True)
    parser.add_argument("--host-profile", choices=("codex", "claude"), default="codex")
    args = parser.parse_args(argv)
    receipt = run_rescue_pipeline(
        corpus_path=args.corpus,
        case_id=args.case_id,
        output_path=args.output,
        standard_failure_receipt=json.loads(
            args.standard_failure.read_text(encoding="utf-8")
        ),
        host_profile=args.host_profile,
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0 if receipt["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["rescue_budget_contract", "run_rescue_pipeline"]
