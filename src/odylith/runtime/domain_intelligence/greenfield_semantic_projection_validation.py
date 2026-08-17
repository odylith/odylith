"""Exact canonical validation for Semantic Intent proposal projections."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    require_semantic_intent_ir,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_proposal import (
    build_verified_semantic_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    require_product_intent_authority_structure,
)


def semantic_projection_issues(proposal: Mapping[str, Any]) -> tuple[str, ...]:
    """Return exact disagreements with a fresh immutable graph projection."""

    authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(authority, Mapping) or authority.get("origin") != "verified_semantic_intent_packet":
        return ("proposal lacks verified Semantic Intent authority",)
    try:
        require_product_intent_authority_structure(authority)
        evidence_sources = authority.get("evidence_sources")
        if not isinstance(evidence_sources, Mapping):
            return ("Semantic Intent authority lacks evidence sources",)
        require_semantic_intent_ir(
            authority.get("semantic_intent"),
            evidence_sources=evidence_sources,
        )
        observed_source = proposal.get("observed_source")
        if not isinstance(observed_source, Mapping):
            return ("proposal lacks observed-source allocation facts",)
        plan = proposal.get("release_plan")
        release_selector = str(plan.get("selector") or "").strip() if isinstance(plan, Mapping) else ""
        expected = build_verified_semantic_proposal(
            authority=authority,
            observed_source=observed_source,
            release_selector=release_selector,
        )
    except ValueError as exc:
        return (str(exc),)
    return _canonical_projection_differences(expected, proposal)


def semantic_projection_report(proposal: Mapping[str, Any]) -> dict[str, Any]:
    """Return the pre-confirm semantic evidence report for a v7 proposal."""

    issues = semantic_projection_issues(proposal)
    return {
        "version": "odylith.greenfield.semantic-projection-report.v1",
        "status": "failed" if issues else "passed",
        "issues": list(issues),
        "quality_scores": {
            "semantic_graph_alignment": 0.0 if issues else 1.0,
            "proof_result_separation": 0.0 if issues else 1.0,
        },
    }


def _canonical_projection_differences(
    expected: Any,
    actual: Any,
    *,
    path: str = "proposal",
) -> tuple[str, ...]:
    """Compare canonical structures without deriving meaning from their text."""

    issues: list[str] = []
    if isinstance(expected, Mapping):
        if not isinstance(actual, Mapping):
            return (f"{path} differs from the canonical Semantic Intent projection",)
        expected_keys = set(expected)
        actual_keys = set(actual)
        for key in sorted(expected_keys - actual_keys):
            issues.append(f"{path}.{key} is missing from the canonical Semantic Intent projection")
        for key in sorted(actual_keys - expected_keys):
            issues.append(f"{path}.{key} is not part of the canonical Semantic Intent projection")
        for key in sorted(expected_keys & actual_keys):
            issues.extend(
                _canonical_projection_differences(
                    expected[key],
                    actual[key],
                    path=f"{path}.{key}",
                )
            )
        return tuple(issues)
    if isinstance(expected, Sequence) and not isinstance(expected, (str, bytes, bytearray)):
        if not isinstance(actual, Sequence) or isinstance(actual, (str, bytes, bytearray)):
            return (f"{path} differs from the canonical Semantic Intent projection",)
        if len(expected) != len(actual):
            issues.append(f"{path} length differs from the canonical Semantic Intent projection")
        for index, (expected_row, actual_row) in enumerate(zip(expected, actual)):
            issues.extend(
                _canonical_projection_differences(
                    expected_row,
                    actual_row,
                    path=f"{path}.{index}",
                )
            )
        return tuple(issues)
    if type(actual) is not type(expected) or actual != expected:
        return (f"{path} differs from the canonical Semantic Intent projection",)
    return ()


__all__ = ["semantic_projection_issues", "semantic_projection_report"]
