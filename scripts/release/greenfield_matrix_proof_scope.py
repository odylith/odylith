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
    patchset = _summary_patchset(manifest)
    tribunal_patch_plan = _as_mapping(patchset.get("tribunal_patch_plan"))
    provider = _as_mapping(tribunal_patch_plan.get("provider"))
    fallback = _as_mapping(patchset.get("structured_patch_fallback"))
    fallback_provider = _as_mapping(fallback.get("provider_failure"))
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
        "structured_patch_fallback_status": str(fallback.get("status", "")).strip(),
        "structured_patch_fallback_source": str(fallback.get("source", "")).strip(),
        "structured_patch_fallback_operation_count": int(fallback.get("operation_count") or 0),
        "structured_patch_fallback_provider": str(fallback_provider.get("provider", "")).strip(),
        "structured_patch_fallback_provider_failure_code": str(
            fallback_provider.get("code") or fallback_provider.get("last_failure_code") or ""
        ).strip(),
        "patchset_summary_source": _patchset_summary_source(manifest),
        "issue_codes": _manifest_issue_values(manifest, "code"),
        "issue_owners": _manifest_issue_values(manifest, "owner"),
        "issue_surfaces": _manifest_issue_values(manifest, "surface"),
        "issue_signatures": _manifest_issue_signatures(manifest),
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
        if not _structured_rescue_plan_or_fallback_proven(summary):
            continue
        return True
    return False


def _structured_rescue_plan_or_fallback_proven(summary: Mapping[str, Any]) -> bool:
    if (
        summary.get("tribunal_patch_plan_status") == "planned"
        and int(summary.get("tribunal_patch_plan_operation_count") or 0) > 0
        and str(summary.get("tribunal_patch_plan_provider", "")).strip()
    ):
        return True
    return (
        summary.get("structured_patch_fallback_status") == "applied"
        and summary.get("structured_patch_fallback_source") == "source_anchored_semantic_fact"
        and int(summary.get("structured_patch_fallback_operation_count") or 0) > 0
        and str(summary.get("structured_patch_fallback_provider", "")).strip()
        and str(summary.get("structured_patch_fallback_provider_failure_code", "")).strip()
    )


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
        paths.extend(str(path) for path in parent.glob(pattern) if path.exists() or path.is_symlink())
    return sorted(dict.fromkeys(paths))


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _summary_patchset(manifest: Mapping[str, Any]) -> Mapping[str, Any]:
    repaired = _as_mapping(manifest.get("last_repair_patchset_request"))
    if repaired:
        return repaired
    return _as_mapping(manifest.get("patchset_request"))


def _patchset_summary_source(manifest: Mapping[str, Any]) -> str:
    if _as_mapping(manifest.get("last_repair_patchset_request")):
        return "last_repair_patchset_request"
    if _as_mapping(manifest.get("patchset_request")):
        return "patchset_request"
    return ""


def _manifest_issue_values(manifest: Mapping[str, Any], key: str) -> list[str]:
    values: list[str] = []
    for issue in _manifest_issue_rows(manifest):
        value = str(issue.get(key) or "").strip()
        if value:
            values.append(value)
    return list(dict.fromkeys(values))


def _manifest_issue_signatures(manifest: Mapping[str, Any]) -> list[str]:
    signatures: list[str] = []
    for issue in _manifest_issue_rows(manifest):
        code = _slug(issue.get("code"))
        owner = _slug(issue.get("owner"))
        surface = _slug(issue.get("surface") or issue.get("projection_id"))
        semantic_node = _slug(issue.get("semantic_node_id"))
        parts = [part for part in (code, owner, surface, semantic_node) if part]
        if parts:
            signatures.append(".".join(parts[:4]))
    return list(dict.fromkeys(signatures))


def _manifest_issue_rows(manifest: Mapping[str, Any]) -> tuple[Mapping[str, Any], ...]:
    issues = manifest.get("issues")
    if not isinstance(issues, Sequence) or isinstance(issues, (str, bytes, bytearray)):
        return ()
    return tuple(issue for issue in issues if isinstance(issue, Mapping))


def _slug(value: Any) -> str:
    parts: list[str] = []
    last_dash = False
    for char in str(value or "").strip().casefold().replace("_", "-"):
        if char.isalnum():
            parts.append(char)
            last_dash = False
        elif not last_dash:
            parts.append("-")
            last_dash = True
    return "".join(parts).strip("-")


__all__ = [
    "natural_rescue_quality_proven",
    "post_confirm_manifest_summary",
    "temp_cleanup_proof",
]
