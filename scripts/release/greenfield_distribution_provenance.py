"""Validate the distribution identity consumed by Greenfield release proof."""

from __future__ import annotations

from collections.abc import Mapping
import json
from pathlib import Path

from greenfield_matrix_release_artifacts import sha256_file


PROVENANCE_VERSION = "odylith-release-provenance.v1"


def verify_distribution_provenance(
    *,
    provenance_path: Path,
    implementation_revision: str,
) -> dict[str, str]:
    """Require clean package provenance for the exact claimed revision."""

    path = Path(provenance_path).expanduser()
    if path.is_symlink():
        raise RuntimeError("semantic release proof requires safe distribution build provenance")
    path = path.resolve()
    if not path.is_file():
        raise RuntimeError("semantic release proof requires safe distribution build provenance")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"distribution build provenance is unreadable: {error}") from error
    if not isinstance(payload, Mapping) or payload.get("version") != PROVENANCE_VERSION:
        raise RuntimeError("semantic release proof requires supported distribution build provenance")
    source_tree = payload.get("source_tree")
    workflow = payload.get("workflow")
    source_head = str(source_tree.get("head") or "").strip().casefold() if isinstance(source_tree, Mapping) else ""
    workflow_sha = str(workflow.get("sha") or "").strip().casefold() if isinstance(workflow, Mapping) else ""
    revision = str(implementation_revision or "").strip().casefold()
    if not isinstance(source_tree, Mapping) or source_tree.get("dirty") is not False:
        raise RuntimeError("semantic release proof requires clean distribution source provenance")
    if source_head != workflow_sha or source_head != revision:
        raise RuntimeError("implementation revision does not match distribution build provenance")
    return {
        "path": str(path),
        "sha256": sha256_file(path),
        "implementation_revision": source_head,
    }


__all__ = ["PROVENANCE_VERSION", "verify_distribution_provenance"]
