"""Strict sealed-write-set sink for ProductCreateTransaction commits."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction


def write_compiled_greenfield_package(
    *,
    root: Path,
    transaction: ProductCreateTransaction,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Apply only repository bytes and deletions sealed before confirmation."""

    _ = completion_priority_write_policy
    package = transaction.prewrite_package
    write_set = greenfield_repository_write_set.require_compiled_greenfield_repository_write_set(
        package.repository_write_set,
    )
    # Preview completeness and quality are compiler contracts. The confirmed
    # path reports the sealed preview without re-adjudicating product quality.
    result = deepcopy(dict(package.commit_result_preview or {}))
    expected_readback = {
        "version": str(write_set["version"]),
        "status": "passed",
        "write_set_hash": str(write_set["write_set_hash"]),
        "directory_count": int(write_set["directory_count"]),
        "directory_delete_count": int(write_set["directory_delete_count"]),
        "write_count": int(write_set["write_count"]),
        "delete_count": int(write_set["delete_count"]),
    }
    result["repository_write_set"] = expected_readback
    actual_readback = greenfield_repository_write_set.apply_compiled_greenfield_repository_write_set(
        repo_root=Path(root).expanduser().resolve(),
        write_set=write_set,
    )
    if actual_readback != expected_readback:
        raise RuntimeError("compiled repository write-set readback summary drifted after materialization")
    return result


__all__ = ["write_compiled_greenfield_package"]
