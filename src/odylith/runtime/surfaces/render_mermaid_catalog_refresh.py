"""Lightweight Atlas-render refresh entrypoint for dashboard paths."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.common import generated_refresh_guard
from odylith.runtime.surfaces import dashboard_surface_bundle
from odylith.runtime.surfaces import source_bundle_mirror

_ATLAS_RENDER_GUARD_NAMESPACE = "generated-refresh-guards"
_ATLAS_RENDER_GUARD_KEY = "atlas-render"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Skip current Atlas rerenders before importing the full renderer.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--catalog", default="odylith/atlas/source/catalog/diagrams.v1.json")
    parser.add_argument("--output", default="odylith/atlas/atlas.html")
    parser.add_argument("--traceability-graph", default="odylith/radar/traceability-graph.v1.json")
    parser.add_argument("--max-review-age-days", type=int, default=21)
    parser.add_argument("--fail-on-stale", action="store_true")
    parser.add_argument("--check-only", action="store_true")
    parser.add_argument("--diagram-id", action="append", default=[])
    parser.add_argument("--runtime-mode", choices=("auto", "standalone", "daemon"), default="auto")
    return parser.parse_args(argv)


def _resolve(repo_root: Path, value: str) -> Path:
    raw = str(value or "").strip()
    path = Path(raw)
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(args.repo_root).resolve()
    output_path = _resolve(repo_root, args.output)
    if not args.check_only and not args.diagram_id:
        bundle_paths = dashboard_surface_bundle.build_paths(output_path=output_path, asset_prefix="mermaid")
        output_paths = [
            output_path,
            bundle_paths.payload_js_path,
            bundle_paths.control_js_path,
        ]
        if source_bundle_mirror.source_bundle_root(repo_root=repo_root).is_dir():
            for live_path in tuple(output_paths):
                output_paths.append(source_bundle_mirror.bundle_mirror_path(repo_root=repo_root, live_path=live_path))
        skip_rebuild, _fingerprint, cached_metadata = generated_refresh_guard.should_skip_rebuild(
            repo_root=repo_root,
            namespace=_ATLAS_RENDER_GUARD_NAMESPACE,
            key=_ATLAS_RENDER_GUARD_KEY,
            watched_paths=(
                "odylith/atlas/source",
                "odylith/radar/traceability-graph.v1.json",
                "odylith/runtime/delivery_intelligence.v4.json",
                "odylith/registry/source",
                "src/odylith/runtime/surfaces",
                "src/odylith/runtime/governance",
                "src/odylith/runtime/common",
            ),
            output_paths=tuple(output_paths),
            extra={
                "max_review_age_days": int(args.max_review_age_days),
                "runtime_mode": str(args.runtime_mode),
            },
        )
        if skip_rebuild:
            print("mermaid catalog render passed")
            print(f"- output: {output_path}")
            stale_count = int(cached_metadata.get("stale_count", 0) or 0) if cached_metadata else 0
            if cached_metadata:
                print(f"- diagrams: {int(cached_metadata.get('diagram_count', 0) or 0)}")
                print(f"- fresh: {int(cached_metadata.get('fresh_count', 0) or 0)}")
                print(f"- stale: {stale_count}")
            if args.fail_on_stale and stale_count > 0:
                print("mermaid catalog freshness FAILED")
                print("- at least one diagram is stale; update diagram source/metadata and rerun")
                return 3
            return 0

    from odylith.runtime.surfaces import render_mermaid_catalog

    return render_mermaid_catalog.main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
