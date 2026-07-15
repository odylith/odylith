"""Stable manifest contract shared by pre-confirm compilation and commit-only create."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


PRECONFIRM_ENGINE_VERSION = "greenfield-pre-confirm-fixpoint-v1"
PRECONFIRM_QUALITY_MANIFEST_VERSION = "greenfield-pre-confirm-quality-manifest-v1"


def finalize_greenfield_commit_manifest(
    manifest: Mapping[str, Any],
    *,
    whole_project_elapsed_seconds: float,
    write_transaction_status: str,
) -> dict[str, Any]:
    """Attach commit evidence without invoking the pre-confirm compiler."""

    payload = dict(manifest)
    payload["whole_project_elapsed_seconds"] = round(float(whole_project_elapsed_seconds), 3)
    transaction = dict(payload.get("write_transaction") if isinstance(payload.get("write_transaction"), Mapping) else {})
    transaction["status"] = write_transaction_status
    transaction["rollback_guard"] = "enabled"
    payload["write_transaction"] = transaction
    return payload


__all__ = [
    "PRECONFIRM_ENGINE_VERSION",
    "PRECONFIRM_QUALITY_MANIFEST_VERSION",
    "finalize_greenfield_commit_manifest",
]
