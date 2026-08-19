"""Execute one assignment-bound standard Greenfield development cohort."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
from typing import Any

from greenfield_semantic_pipeline_evidence import require_active_evidence_plan
from greenfield_semantic_release_support import (
    canonical_sha256,
    exclusive_json,
    json_mapping,
    mapped_rows,
    safe_json_file,
    unique_index,
)
from greenfield_semantic_standard_pipeline_experiment import run_standard_pipeline


DEVELOPMENT_RUN_VERSION = "odylith.greenfield.standard-development-run.v1"


def run_development_standard_cohort(
    *,
    corpus_path: Path,
    active_evidence_plan_path: Path,
    output_directory: Path,
) -> dict[str, Any]:
    """Run every frozen assignment once through the strict standard tier."""

    corpus_file = safe_json_file(corpus_path, "development corpus")
    corpus = json_mapping(corpus_file, "development corpus")
    plan_file = safe_json_file(active_evidence_plan_path, "active evidence plan")
    plan = require_active_evidence_plan(
        json_mapping(plan_file, "active evidence plan"),
        corpus=corpus,
        corpus_sha256=hashlib.sha256(corpus_file.read_bytes()).hexdigest(),
    )
    cases = unique_index(
        mapped_rows(corpus.get("cases"), "development corpus cases"),
        "case_id",
        "development corpus cases",
    )
    assignments = unique_index(
        mapped_rows(plan.get("cases"), "active evidence assignments"),
        "case_id",
        "active evidence assignments",
    )
    destination = Path(output_directory).expanduser().resolve()
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError as error:
        raise RuntimeError("development run output directory already exists") from error

    results: list[dict[str, Any]] = []
    for case_id in sorted(cases):
        assignment = dict(assignments[case_id])
        receipt_file = f"{case_id}.standard.json"
        receipt = run_standard_pipeline(
            corpus_path=corpus_file,
            case_id=case_id,
            output_path=destination / receipt_file,
            host_profile=str(assignment["host_profile"]),
            _evidence_assignment=assignment,
        )
        results.append(_result(receipt, receipt_file=receipt_file))

    completed = all(row["status"] == "completed" for row in results)
    manifest = {
        "version": DEVELOPMENT_RUN_VERSION,
        "status": "completed" if completed else "incomplete",
        "active_evidence_plan_sha256": canonical_sha256(plan),
        "case_count": len(results),
        "standard_success_count": sum(
            row["status"] == "completed" for row in results
        ),
        "typed_rescue_required_count": sum(
            row["outcome"] == "typed_standard_failure" for row in results
        ),
        "environment_failure_count": sum(
            row["outcome"] == "environment_failure" for row in results
        ),
        "deadline_failure_count": sum(
            row["outcome"] in {
                "standard_deadline_exceeded",
                "standard_deadline_exhausted",
            }
            for row in results
        ),
        "model_call_count": sum(row["model_call_count"] for row in results),
        "restart_count": sum(row["restart_count"] for row in results),
        "total_wall_ms": sum(row["wall_ms"] for row in results),
        "cases": results,
    }
    exclusive_json(destination / "manifest.json", manifest)
    return manifest


def _result(receipt: Mapping[str, Any], *, receipt_file: str) -> dict[str, Any]:
    return {
        "case_id": str(receipt.get("case_id") or ""),
        "status": str(receipt.get("status") or ""),
        "outcome": str(receipt.get("outcome") or ""),
        "wall_ms": int(receipt.get("wall_ms") or 0),
        "model_call_count": int(receipt.get("model_call_count") or 0),
        "restart_count": int(receipt.get("restart_count") or 0),
        "receipt_file": receipt_file,
        "receipt_sha256": canonical_sha256(receipt),
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--active-evidence-plan", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = run_development_standard_cohort(
        corpus_path=args.corpus,
        active_evidence_plan_path=args.active_evidence_plan,
        output_directory=args.output_directory,
    )
    return 0 if manifest["status"] == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["DEVELOPMENT_RUN_VERSION", "run_development_standard_cohort"]
