"""Lightweight delivery-intelligence refresh entrypoint for dashboard paths."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.common import repo_path_resolver
from odylith.runtime.governance.delivery_intelligence_support import current_local_head as _current_local_head
from odylith.runtime.governance.delivery_intelligence_support import registry_delivery_watched_paths as _registry_delivery_watched_paths

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
    """Resolve one refresh path token against the repo root."""

    return repo_path_resolver.resolve_repo_path(repo_root=repo_root, value=token)


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
                *_registry_delivery_watched_paths(repo_root),
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
            extra={
                "max_review_age_days": int(args.max_review_age_days),
                "local_head": _current_local_head(repo_root),
            },
        )
        if skip_rebuild:
            print("delivery intelligence artifact is current")
            return 0

    from odylith.runtime.governance import delivery_intelligence_engine

    return delivery_intelligence_engine.main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
