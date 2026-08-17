"""One-pass pre-confirm validation for sealed Semantic Intent proposals.

The host-authored Semantic Intent graph is authoritative before this module is
called.  Validation may reject a graph projection, but it must never repair or
reinterpret that meaning.  Legacy proposals retain their separate compatibility
engine.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
import time
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_create_manifest import (
    PRECONFIRM_ENGINE_VERSION,
    PRECONFIRM_QUALITY_MANIFEST_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_package_validation import (
    require_verified_semantic_package,
    require_verified_semantic_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_projection_validation import (
    semantic_projection_report,
)


@dataclass(frozen=True)
class VerifiedSemanticPreconfirmResult:
    proposal: Mapping[str, Any]
    tribunal: Any
    prewrite_build: Any
    manifest: dict[str, Any]


def validate_verified_semantic_prewrite(
    *,
    proposal: Mapping[str, Any],
    release_selector: str,
    build_prewrite: Callable[[Mapping[str, Any], Any], Any],
) -> VerifiedSemanticPreconfirmResult:
    """Render and validate one immutable graph projection before confirmation."""

    started = time.perf_counter()
    proposal_report = require_verified_semantic_proposal(
        proposal,
        release_selector=release_selector,
    )
    prewrite_build = build_prewrite(proposal, proposal_report)
    package_report = require_verified_semantic_package(
        prewrite_build.package,
        release_selector=release_selector,
    )
    semantic_compiler = semantic_projection_report(prewrite_build.package.proposal)
    if semantic_compiler.get("status") != "passed":
        raise ValueError("verified Semantic Intent projection failed its pre-confirm quality evidence")
    elapsed = round(max(0.0, time.perf_counter() - started), 3)
    manifest = {
        "version": PRECONFIRM_QUALITY_MANIFEST_VERSION,
        "engine": PRECONFIRM_ENGINE_VERSION,
        "mode": "verified_semantic_graph",
        "status": "passed",
        "validation_status": package_report.status,
        "stop_reason": "verified_semantic_graph",
        "budget_seconds": 0.0,
        "requested_repair_tier": "none",
        "repair_tier": "none",
        "rescue_activated": False,
        "repair_tier_policy": {
            "verified_semantic_graph": "reject invalid projections; never repair sealed meaning",
        },
        "elapsed_seconds": elapsed,
        "passes": 1,
        "max_passes": 1,
        "artifact_counts": dict(package_report.artifact_counts),
        "issue_count": 0,
        "issue_codes": [],
        "issues": [],
        "review_report": {
            "version": "odylith.greenfield.preconfirm.review_report.v1",
            "status": "passed",
            "finding_count": 0,
            "findings": [],
        },
        "patchset_request": {
            "version": "odylith.greenfield.preconfirm.patchset_request.v1",
            "status": "no_repairable_operations",
            "operation_count": 0,
            "operations": [],
        },
        "repaired_issue_codes": [],
        "hard_blocker": None,
        "pass_records": [
            {
                "pass_index": 0,
                "status": package_report.status,
                "elapsed_seconds": elapsed,
                "package_repair_passes": 0,
                "package_changed": False,
                "issue_count": 0,
                "issue_codes": [],
            }
        ],
        "quality_lenses": {
            "version": "odylith.greenfield.typed-quality-evidence.v1",
            "status": "passed",
            "lenses": {
                "source_semantics": "exact source citations and graph relations",
                "artifact_bindings": "exact Registry, Radar, Atlas, and memory identities",
                "transaction_integrity": "sealed write set, refresh proof, and commit preview",
            },
            "issues": [],
        },
        "semantic_compiler": semantic_compiler,
        "write_transaction": {
            "status": "not_started",
            "rollback_guard": "enabled",
            "prewrite_clean_before_commit": True,
        },
    }
    return VerifiedSemanticPreconfirmResult(
        proposal=proposal,
        tribunal=package_report,
        prewrite_build=prewrite_build,
        manifest=manifest,
    )


__all__ = ["VerifiedSemanticPreconfirmResult", "validate_verified_semantic_prewrite"]
