"""Authority and quality carry-forward for pre-confirm greenfield transactions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_candidate_intent_stage import restage_compiled_candidate_intent
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_facts_hash


def merge_recompiled_quality_manifests(
    initial: Mapping[str, Any],
    final: Mapping[str, Any],
) -> dict[str, Any]:
    """Keep pre-confirm repair evidence when final facts require one clean recompile."""

    merged = dict(final)
    initial_records = initial.get("pass_records") if isinstance(initial.get("pass_records"), list) else []
    final_records = final.get("pass_records") if isinstance(final.get("pass_records"), list) else []
    merged["pass_records"] = [*initial_records, *final_records]
    merged["passes"] = len(merged["pass_records"])
    merged["repaired_issue_codes"] = sorted(
        {
            *[str(value) for value in initial.get("repaired_issue_codes", []) if str(value)],
            *[str(value) for value in final.get("repaired_issue_codes", []) if str(value)],
        }
    )
    merged["rescue_activated"] = bool(initial.get("rescue_activated") or final.get("rescue_activated"))
    merged["repair_tier"] = _highest_repair_tier(
        str(initial.get("repair_tier") or "standard"),
        str(final.get("repair_tier") or "standard"),
    )
    merged["budget_seconds"] = max(float(initial.get("budget_seconds") or 0), float(final.get("budget_seconds") or 0))
    merged["max_passes"] = max(int(initial.get("max_passes") or 0), int(final.get("max_passes") or 0))
    merged["elapsed_seconds"] = round(
        float(initial.get("elapsed_seconds") or 0) + float(final.get("elapsed_seconds") or 0),
        3,
    )
    if initial.get("last_repair_patchset_request") and not final.get("last_repair_patchset_request"):
        merged["last_repair_patchset_request"] = initial["last_repair_patchset_request"]
    return merged


def finalize_repaired_product_intent(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    intent_authority: Mapping[str, Any],
) -> tuple[Mapping[str, Any], Mapping[str, Any], bool]:
    """Restage final pre-confirm facts once before the transaction is sealed."""

    intent = proposal.get("intent") if isinstance(proposal, Mapping) else None
    if not isinstance(intent, Mapping):
        return proposal, intent_authority, False
    if product_facts_hash(intent) == str(intent_authority.get(PRODUCT_FACTS_HASH_KEY) or ""):
        return proposal, intent_authority, False
    finalized_intent = restage_compiled_candidate_intent(
        repo_root=root,
        intent=intent,
        previous_authority=intent_authority,
    )
    finalized_proposal = dict(proposal)
    finalized_proposal["intent"] = finalized_intent
    finalized_proposal[PRODUCT_INTENT_AUTHORITY_KEY] = finalized_intent[PRODUCT_INTENT_AUTHORITY_KEY]
    return finalized_proposal, finalized_intent[PRODUCT_INTENT_AUTHORITY_KEY], True


def _highest_repair_tier(*tiers: str) -> str:
    order = {"standard": 0, "rescue": 1, "deep": 2}
    return max(tiers, key=lambda tier: order.get(tier, 0))


__all__ = ["finalize_repaired_product_intent", "merge_recompiled_quality_manifests"]
