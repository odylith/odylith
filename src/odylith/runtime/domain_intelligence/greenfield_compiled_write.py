"""Strict compiled-package sink for ProductCreateTransaction commits."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction


def write_compiled_greenfield_package(
    *,
    root: Path,
    transaction: ProductCreateTransaction,
    completion_priority_write_policy: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write a verified transaction package through the compiled-only boundary."""

    return greenfield_apply_write.write_greenfield_proposal(
        root=root,
        proposal=transaction.proposal,
        release_selector=transaction.release_selector,
        tribunal=transaction.validation_gate,
        backlog_result=transaction.backlog_result,
        prewrite_package=transaction.prewrite_package,
        completion_priority_write_policy=completion_priority_write_policy,
    )


__all__ = ["write_compiled_greenfield_package"]
