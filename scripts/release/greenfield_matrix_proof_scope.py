"""Proof-scope summaries for installed greenfield release simulations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from greenfield_matrix_types import GreenfieldMatrixResult


TEMP_CLEANUP_PATTERNS: tuple[str, ...] = (
    "odylith-greenfield-matrix-*",
    "odylith-greenfield-rescue-*",
    "odylith-source-*",
    "odylith-debug-*",
    "odylith-sim-*",
)


def post_confirm_manifest_summary(manifest: Mapping[str, Any]) -> dict[str, Any]:
    """Return the manifest facts needed for release-proof readback."""

    if not manifest:
        return {}
    patchset = _as_mapping(manifest.get("patchset_request"))
    tribunal_patch_plan = _as_mapping(patchset.get("tribunal_patch_plan"))
    provider = _as_mapping(tribunal_patch_plan.get("provider"))
    return {
        "status": str(manifest.get("status", "")).strip(),
        "validation_status": str(manifest.get("validation_status", "")).strip(),
        "requested_repair_tier": str(manifest.get("requested_repair_tier", "")).strip(),
        "repair_tier": str(manifest.get("repair_tier", "")).strip(),
        "rescue_activated": bool(manifest.get("rescue_activated")),
        "passes": int(manifest.get("passes") or 0),
        "issue_count": int(manifest.get("issue_count") or 0),
        "repaired_issue_codes": list(manifest.get("repaired_issue_codes") or []),
        "patchset_status": str(patchset.get("status", "")).strip(),
        "patchset_operation_count": int(patchset.get("operation_count") or 0),
        "tribunal_patch_plan_status": str(tribunal_patch_plan.get("status", "")).strip(),
        "tribunal_patch_plan_operation_count": int(tribunal_patch_plan.get("operation_count") or 0),
        "tribunal_patch_plan_provider": str(provider.get("provider", "")).strip(),
        "tribunal_patch_plan_provider_failure_code": str(provider.get("last_failure_code", "")).strip(),
    }


def natural_rescue_quality_proven(results: Sequence[GreenfieldMatrixResult]) -> bool:
    """Return true only when a real installed case proves provider-backed rescue."""

    for result in results:
        summary = dict(result.post_confirm_manifest_summary or {})
        if result.status != "passed":
            continue
        if summary.get("status") != "passed" or summary.get("validation_status") != "passed":
            continue
        if summary.get("repair_tier") not in {"rescue", "deep"} or not summary.get("rescue_activated"):
            continue
        repaired_codes = set(summary.get("repaired_issue_codes") or [])
        if "post_confirm_rescue_probe" in repaired_codes:
            continue
        if summary.get("tribunal_patch_plan_status") != "planned":
            continue
        if int(summary.get("tribunal_patch_plan_operation_count") or 0) <= 0:
            continue
        if not str(summary.get("tribunal_patch_plan_provider", "")).strip():
            continue
        return True
    return False


def temp_cleanup_proof(temp_parent: Path) -> dict[str, Any]:
    """Return cleanup proof for Odylith-created simulation temp roots."""

    parent = Path(temp_parent).expanduser().resolve()
    remaining = _remaining_temp_paths(parent)
    return {
        "status": "passed" if not remaining else "failed",
        "scope": "odylith_temp_simulation_roots",
        "temp_parent": str(parent),
        "patterns": list(TEMP_CLEANUP_PATTERNS),
        "remaining_paths": remaining,
    }


def _remaining_temp_paths(parent: Path) -> list[str]:
    if not parent.exists():
        return []
    paths: list[str] = []
    for pattern in TEMP_CLEANUP_PATTERNS:
        paths.extend(str(path) for path in parent.glob(pattern) if path.is_dir())
    return sorted(dict.fromkeys(paths))


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "natural_rescue_quality_proven",
    "post_confirm_manifest_summary",
    "temp_cleanup_proof",
]
