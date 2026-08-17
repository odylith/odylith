"""Compile sealed ProductCreateTransactions without changing Product Intent."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    ProductCreateTransaction,
    build_product_create_transaction,
    require_product_create_transaction_verified,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_binding import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    rebind_authoritative_product_facts,
    require_authoritative_intent_binding,
    require_product_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_release_contract import (
    DEFAULT_GREENFIELD_RELEASE_SELECTOR,
)


PrewriteBuilder = Callable[..., tuple[Mapping[str, Any], Any, Any, dict[str, Any]]]


def compile_sealed_greenfield_transaction(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    verified_semantic_prewrite: PrewriteBuilder,
) -> ProductCreateTransaction:
    """Validate one v7 graph authority and compile its exact staged write set."""

    root = Path(repo_root).expanduser().resolve()
    authority_value = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(authority_value, Mapping):
        raise ValueError("ProductCreateTransaction is missing confirmed Product Intent authority")
    intent_authority = dict(authority_value)
    require_product_intent_authority(intent_authority)
    release_selector = _semantic_release_selector(proposal, release_selector)
    authoritative_intent = proposal.get("intent")
    if not isinstance(authoritative_intent, Mapping):
        raise ValueError("ProductCreateTransaction proposal is missing typed Product Intent")
    require_authoritative_intent_binding(authoritative_intent, intent_authority)
    proposal, _prewrite_report, prewrite_build, quality_manifest = verified_semantic_prewrite(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
    )
    package_proposal = prewrite_build.package.proposal
    if not isinstance(package_proposal, Mapping):
        raise ValueError("verified Semantic Intent prewrite lacks a typed proposal")
    proposal = dict(package_proposal)
    proposal["intent"] = rebind_authoritative_product_facts(
        proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {},
        authoritative_intent=authoritative_intent,
        authority=intent_authority,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    from odylith.runtime.domain_intelligence.greenfield_semantic_package_validation import (
        require_verified_semantic_package,
    )

    rebound_package = replace(prewrite_build.package, proposal=proposal)
    validation_report = require_verified_semantic_package(
        rebound_package,
        release_selector=release_selector,
    )
    rebound_package = replace(
        rebound_package,
        tribunal_preview=validation_report.to_dict(),
    )
    prewrite_build = replace(prewrite_build, package=rebound_package)
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector=release_selector,
        validation_gate=validation_report.to_dict(),
        prewrite_package=prewrite_build.package,
        backlog_result=prewrite_build.backlog_result,
        intent_authority=intent_authority,
        quality_manifest=quality_manifest,
        repo_root=root,
    )
    require_product_create_transaction_verified(transaction)
    return transaction


def _semantic_release_selector(proposal: Mapping[str, Any], explicit_selector: str) -> str:
    explicit = str(explicit_selector or "").strip()
    if explicit:
        return explicit
    plan = proposal.get("release_plan")
    selector = str(plan.get("selector") or "").strip() if isinstance(plan, Mapping) else ""
    return selector or DEFAULT_GREENFIELD_RELEASE_SELECTOR


__all__ = ["compile_sealed_greenfield_transaction"]
