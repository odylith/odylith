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
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    require_product_create_transaction_compiler_provenance,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    POST_CONFIRM_ENGINE_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    POST_CONFIRM_QUALITY_MANIFEST_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    finalize_greenfield_post_confirm_manifest,
)
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction


class GreenfieldCreateCommitError(RuntimeError):
    """Post-confirm commit failure after the compiled transaction entered the write boundary."""

    def __init__(
        self,
        message: str,
        *,
        rollback_status: str,
        rollback_error: str = "",
        root_cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.rollback_status = rollback_status
        self.rollback_error = rollback_error
        self.root_cause_type = type(root_cause).__name__ if root_cause is not None else ""

    def to_dict(self) -> dict[str, str]:
        payload = {
            "failure_kind": "post_confirm_commit_environment_or_runtime_failure",
            "rollback_status": self.rollback_status,
            "root_cause_type": self.root_cause_type,
        }
        if self.rollback_error:
            payload["rollback_error"] = self.rollback_error
        return payload


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
    root = Path(repo_root).expanduser().resolve()
    require_product_create_transaction_verified(transaction)
    require_product_create_transaction_compiler_provenance(transaction, repo_root=root)
    raise_for_unapproved_product_create_transaction(transaction)
    started = time.perf_counter() if started_at is None else float(started_at)
    completion_priority_write_policy = greenfield_apply_write.completion_priority_write_policy_from_manifest(
        transaction.quality_manifest
    )
    write_transaction = GreenfieldApplyTransaction(root)
    try:
        with write_transaction:
            ensure_greenfield_create_baseline(root)
            result = greenfield_compiled_write.write_compiled_greenfield_package(
                root=root,
                transaction=transaction,
                completion_priority_write_policy=completion_priority_write_policy,
            )
            write_transaction.commit()
    except (OSError, RuntimeError) as exc:
        if isinstance(exc, GreenfieldCreateCommitError):
            raise
        rollback_status = write_transaction.rollback_status
        rollback_phrase = (
            "rollback completed; no governed records were committed"
            if rollback_status == "rolled_back"
            else f"rollback_status={rollback_status}; commit did not complete"
        )
        raise GreenfieldCreateCommitError(
            "greenfield create failed while committing the verified ProductCreateTransaction; "
            f"{rollback_phrase}. "
            f"Root cause: {exc}",
            rollback_status=rollback_status,
            rollback_error=write_transaction.rollback_error,
            root_cause=exc,
        ) from exc
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
    write_transaction = (
        transaction.quality_manifest.get("write_transaction")
        if isinstance(transaction.quality_manifest.get("write_transaction"), Mapping)
        else {}
    )
    pre_confirm_write_sealed = (
        str(transaction.quality_manifest.get("version", "")).strip() == POST_CONFIRM_QUALITY_MANIFEST_VERSION
        and str(transaction.quality_manifest.get("engine", "")).strip() == POST_CONFIRM_ENGINE_VERSION
        and str(write_transaction.get("status", "")).strip() == "not_started"
        and str(write_transaction.get("rollback_guard", "")).strip() == "enabled"
        and write_transaction.get("prewrite_clean_before_commit") is True
        and "commit_only" not in write_transaction
    )
    if (
        quality_status == "passed"
        and validation_status in {"", "passed"}
        and not hard_blocker
        and issue_count == 0
        and pre_confirm_write_sealed
    ):
        return
    raise ValueError(
        "ProductCreateTransaction quality manifest is not approved for commit; "
        "rebuild the pre-confirm transaction before committing governed records"
    )


__all__ = [
    "GreenfieldCreateCommitError",
    "commit_greenfield_create_transaction",
    "raise_for_unapproved_product_create_transaction",
]
