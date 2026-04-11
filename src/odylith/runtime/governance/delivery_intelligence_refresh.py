"""Lightweight delivery-intelligence refresh entrypoint for dashboard paths."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import generated_refresh_guard

DEFAULT_OUTPUT_PATH = "odylith/runtime/delivery_intelligence.v4.json"
DEFAULT_CONTROL_POSTURE_PATH = "odylith/runtime/control-posture.v4.json"
DEFAULT_ODYLITH_REASONING_PATH = "odylith/runtime/odylith_reasoning.v4.json"
DEFAULT_MAX_REVIEW_AGE_DAYS = 21
_DELIVERY_INTELLIGENCE_GUARD_NAMESPACE = "generated-refresh-guards"
_DELIVERY_INTELLIGENCE_GUARD_KEY = "delivery-intelligence"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith delivery-intelligence-refresh",
        description="Skip current delivery-intelligence rebuilds before importing the full engine.",
    )
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output", default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--max-review-age-days", type=int, default=DEFAULT_MAX_REVIEW_AGE_DAYS)
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    output_path = _resolve(repo_root, args.output)
    if not args.check_only:
        skip_rebuild, _fingerprint, _cached = generated_refresh_guard.should_skip_rebuild(
            repo_root=repo_root,
            namespace=_DELIVERY_INTELLIGENCE_GUARD_NAMESPACE,
            key=_DELIVERY_INTELLIGENCE_GUARD_KEY,
            watched_paths=(
                "odylith/radar/source",
                "odylith/technical-plans",
                "odylith/casebook/bugs",
                "odylith/registry/source",
                "odylith/atlas/source/catalog/diagrams.v1.json",
                "odylith/radar/traceability-graph.v1.json",
                *agent_runtime_contract.candidate_stream_tokens(),
                DEFAULT_CONTROL_POSTURE_PATH,
                DEFAULT_ODYLITH_REASONING_PATH,
                "src/odylith/runtime/governance",
                "src/odylith/runtime/reasoning",
                "src/odylith/runtime/common",
            ),
            output_paths=(output_path,),
            extra={"max_review_age_days": int(args.max_review_age_days)},
        )
        if skip_rebuild:
            print("delivery intelligence artifact is current")
            return 0

    from odylith.runtime.governance import delivery_intelligence_engine

    return delivery_intelligence_engine.main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
