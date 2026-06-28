"""Internal release proof probe for greenfield post-confirm rescue wiring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import os
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import (
    GreenfieldReviewFinding,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import review_finding


RESCUE_PROBE_ENV = "ODYLITH_INTERNAL_GREENFIELD_RESCUE_PROBE"
RESCUE_PROBE_TOKEN = "typed-post-confirm-rescue-v1"
RESCUE_PROBE_CODE = "post_confirm_rescue_probe"
RESCUE_PROBE_SOURCE = "release_rescue_probe"
RESCUE_PROBE_MARKER_KEY = "post_confirm_rescue_probe"
RESCUE_PROBE_MARKER_STATUS = "semantic_patch_applied"


def rescue_probe_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return an env with the internal typed rescue probe enabled."""

    values = dict(env)
    values[RESCUE_PROBE_ENV] = RESCUE_PROBE_TOKEN
    return values


def rescue_probe_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return true only for the exact internal release-proof token."""

    values = environ if environ is not None else os.environ
    return normalize_string(values.get(RESCUE_PROBE_ENV)) == RESCUE_PROBE_TOKEN


def rescue_probe_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    """Emit one typed repairable finding when the internal rescue probe is active."""

    if not rescue_probe_enabled():
        return ()
    proposal = getattr(package, "proposal", {}) if isinstance(getattr(package, "proposal", {}), Mapping) else {}
    if rescue_probe_repaired(proposal):
        return ()
    return (
        review_finding(
            code=RESCUE_PROBE_CODE,
            surface="post_confirm",
            target_path=f"proposal.{RESCUE_PROBE_MARKER_KEY}",
            projection_id="review_report",
            semantic_node_id="PostConfirmEngine.rescue_probe",
            severity="high",
            repairability="semantic_patch",
            owner="post_confirm_rescue_probe",
            source=RESCUE_PROBE_SOURCE,
            message="internal release rescue probe requires one typed semantic repair before governed write",
        ),
    )


def rescue_probe_repaired(proposal: Mapping[str, Any]) -> bool:
    marker = proposal.get(RESCUE_PROBE_MARKER_KEY)
    if not isinstance(marker, Mapping):
        return False
    return normalize_string(marker.get("status")) == RESCUE_PROBE_MARKER_STATUS


def rescue_probe_patch_values(finding: GreenfieldReviewFinding) -> Mapping[str, Any]:
    """Return deterministic PatchSet payload values for the internal probe."""

    if finding.code != RESCUE_PROBE_CODE or finding.source != RESCUE_PROBE_SOURCE:
        return {}
    return {
        "operation_kind": RESCUE_PROBE_CODE,
        "replacement_fact": {
            RESCUE_PROBE_MARKER_KEY: {
                "status": RESCUE_PROBE_MARKER_STATUS,
                "version": "v1",
                "source": RESCUE_PROBE_SOURCE,
            }
        },
        "decision_ledger_entry": {
            "chosen_interpretation": "internal release proof exercised typed semantic repair before governed write",
            "rationale": "release matrix enabled the deterministic post-confirm rescue probe",
            "rejected_interpretations": ["treating source-local rescue tests as installed CLI proof"],
        },
        "proof_obligation_delta": {
            "release_rescue_probe": "packaged CLI must auto-escalate to rescue, repair, and commit governed records"
        },
        "confidence": 1.0,
    }


def apply_rescue_probe_operations(
    proposal: dict[str, Any],
    operations: Sequence[Mapping[str, Any]],
) -> bool:
    """Apply the deterministic internal probe marker from a typed PatchSet."""

    changed = False
    for operation in operations:
        if normalize_string(operation.get("issue_code")) != RESCUE_PROBE_CODE:
            continue
        if normalize_string(operation.get("source_finding")) != RESCUE_PROBE_SOURCE:
            continue
        replacement = operation.get("replacement_fact")
        if not isinstance(replacement, Mapping):
            continue
        marker = replacement.get(RESCUE_PROBE_MARKER_KEY)
        if not isinstance(marker, Mapping):
            continue
        next_marker = {
            "status": normalize_string(marker.get("status")) or RESCUE_PROBE_MARKER_STATUS,
            "version": normalize_string(marker.get("version")) or "v1",
            "source": normalize_string(marker.get("source")) or RESCUE_PROBE_SOURCE,
        }
        if proposal.get(RESCUE_PROBE_MARKER_KEY) == next_marker:
            continue
        proposal[RESCUE_PROBE_MARKER_KEY] = next_marker
        changed = True
    return changed


__all__ = [
    "RESCUE_PROBE_CODE",
    "RESCUE_PROBE_ENV",
    "RESCUE_PROBE_MARKER_KEY",
    "RESCUE_PROBE_MARKER_STATUS",
    "RESCUE_PROBE_SOURCE",
    "RESCUE_PROBE_TOKEN",
    "apply_rescue_probe_operations",
    "rescue_probe_enabled",
    "rescue_probe_env",
    "rescue_probe_findings",
    "rescue_probe_patch_values",
    "rescue_probe_repaired",
]
