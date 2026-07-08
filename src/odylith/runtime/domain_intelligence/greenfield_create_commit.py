"""Commit-only executor for verified greenfield create transactions."""

from __future__ import annotations

import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_compiled_write
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import ensure_greenfield_create_baseline
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    finalize_greenfield_post_confirm_manifest,
)
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


def commit_greenfield_create_transaction(
    *,
    repo_root: Path,
    transaction: ProductCreateTransaction,
    confirm: bool,
    started_at: float | None = None,
) -> dict[str, Any]:
    """Verify and commit an already compiled ProductCreateTransaction."""

    if not confirm:
        raise ValueError("--confirm is required before greenfield apply writes accepted product records")
    require_product_create_transaction_verified(transaction)
    raise_for_unapproved_product_create_transaction(transaction)
    root = Path(repo_root).expanduser().resolve()
    started = time.perf_counter() if started_at is None else float(started_at)
    completion_priority_write_policy = greenfield_apply_write.completion_priority_write_policy_from_manifest(
        transaction.quality_manifest
    )
    with GreenfieldApplyTransaction(root) as write_transaction:
        ensure_greenfield_create_baseline(root)
        result = greenfield_compiled_write.write_compiled_greenfield_package(
            root=root,
            transaction=transaction,
            completion_priority_write_policy=completion_priority_write_policy,
        )
        write_transaction.commit()
    final_manifest = finalize_greenfield_post_confirm_manifest(
        transaction.quality_manifest,
        whole_project_elapsed_seconds=time.perf_counter() - started,
        write_transaction_status="committed",
    )
    final_manifest["product_create_transaction"] = transaction.summary()
    write_manifest = dict(final_manifest.get("write_transaction") or {})
    write_manifest["product_create_transaction_hash"] = transaction.transaction_hash
    write_manifest["commit_only"] = True
    final_manifest["write_transaction"] = write_manifest
    final_write_debt = result.get("completion_priority_quality_debt")
    if final_write_debt:
        final_manifest["status"] = "passed_with_quality_debt"
        final_manifest["stop_reason"] = "completion_priority_quality_debt"
        completion_priority = (
            dict(final_manifest["completion_priority"])
            if isinstance(final_manifest.get("completion_priority"), Mapping)
            else dict(completion_priority_write_policy or {})
        )
        completion_priority["final_write_quality_debt"] = list(final_write_debt)
        completion_priority["final_write_quality_debt_count"] = len(final_write_debt)
        completion_priority.setdefault("status", "write_allowed_with_projection_quality_debt")
        completion_priority.setdefault("hard_blocker_count", 0)
        final_manifest["completion_priority"] = completion_priority
    result["post_confirm_quality_manifest"] = final_manifest
    result["product_create_transaction"] = transaction.summary()
    return result


def raise_for_unapproved_product_create_transaction(transaction: ProductCreateTransaction) -> None:
    quality_status = str(transaction.quality_manifest.get("status", "")).strip()
    validation_status = str(transaction.quality_manifest.get("validation_status", "")).strip()
    hard_blocker = transaction.quality_manifest.get("hard_blocker")
    issue_count = int(transaction.quality_manifest.get("issue_count", 0) or 0)
    if quality_status == "passed" and validation_status in {"", "passed"} and not hard_blocker and issue_count == 0:
        return
    raise ValueError(
        "ProductCreateTransaction quality manifest is not approved for commit; "
        "rebuild the transaction before committing governed records"
    )


__all__ = [
    "commit_greenfield_create_transaction",
    "raise_for_unapproved_product_create_transaction",
]
