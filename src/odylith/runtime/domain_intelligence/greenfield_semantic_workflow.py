"""Public Greenfield orchestration for one source-cited semantic packet."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_semantic_proposal import (
    build_verified_semantic_proposal,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_identifiers import (
    semantic_artifact_identifier,
)


def build_verified_semantic_proposal_for_repo(
    *,
    repo_root: Path,
    authority: Mapping[str, Any],
    release_selector: str = "",
) -> dict[str, Any]:
    """Build a graph-native proposal without loading a legacy interpreter."""

    root = Path(repo_root).expanduser().resolve()
    return build_verified_semantic_proposal(
        authority=authority,
        observed_source={
            "repo_name": root.name,
            "description": "",
            "languages": [],
            "frameworks": [],
            "monorepo": False,
            "source_posture": "confirmed_intent_only",
            "source_summary": {
                "total_files": 0,
                "app_modules": 0,
                "support_modules": 0,
                "test_modules": 0,
                "infra_files": 0,
                "managed_files": 0,
                "generated_files": 0,
                "root_noise_files": 0,
                "docs_files": 0,
                "metadata_files": 0,
                "other_files": 0,
            },
        },
        release_selector=release_selector,
    )


def compile_verified_semantic_transaction(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    intent_authority: Mapping[str, Any],
    release_selector: str,
) -> Any:
    """Compile a graph-native transaction through one read-only pre-confirm pass."""

    from odylith.runtime.domain_intelligence.greenfield_transaction_compiler import (
        compile_sealed_greenfield_transaction,
    )

    return compile_sealed_greenfield_transaction(
        repo_root=repo_root,
        proposal=proposal,
        intent_authority=intent_authority,
        release_selector=release_selector,
        verified_semantic_prewrite=_verified_prewrite,
    )


def _verified_prewrite(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    intent_authority: Mapping[str, Any],
    release_selector: str,
) -> tuple[Mapping[str, Any], Any, Any, dict[str, Any]]:
    from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
    from odylith.runtime.domain_intelligence.greenfield_release_contract import (
        release_assignment_note,
    )
    from odylith.runtime.domain_intelligence.greenfield_semantic_preconfirm import (
        validate_verified_semantic_prewrite,
    )

    result = validate_verified_semantic_prewrite(
        proposal=proposal,
        intent_authority=intent_authority,
        release_selector=release_selector,
        build_prewrite=lambda current, validation_report: greenfield_apply_prewrite.build_prewrite_completion_package(
            root=root,
            proposal=current,
            release_selector=release_selector,
            backlog_args=_backlog_args(current, release_selector=release_selector),
            validation_gate=validation_report.to_dict(),
            release_assignment_note=release_assignment_note(selector=release_selector),
        ),
    )
    return result.proposal, result.tribunal, result.prewrite_build, result.manifest


def _backlog_args(proposal: Mapping[str, Any], *, release_selector: str) -> argparse.Namespace:
    rows = [row for row in proposal.get("backlog", ()) if isinstance(row, Mapping)]
    if not rows:
        raise ValueError("verified semantic proposal lacks graph-projected workstreams")
    first = rows[0]
    components = [
        str(row.get("label") or "").strip()
        for row in proposal.get("components", ())
        if isinstance(row, Mapping) and str(row.get("label") or "").strip()
    ]
    security = proposal.get("security_compliance")
    security_posture = " ".join(
        str(value).strip()
        for value in security.values()
        if str(value).strip()
    ) if isinstance(security, Mapping) else ""
    return argparse.Namespace(
        workstream_type="standalone",
        problem=str(first["problem"]),
        customer=str(first["customer"]),
        opportunity=str(first["opportunity"]),
        product_view=str(first["product_view"]),
        success_metrics="\n".join(f"- {value}" for value in _strings(first.get("success_metrics"))),
        domain_risk=" ".join(_strings(first.get("risks"))),
        security_posture=security_posture,
        priority=str(first.get("priority") or "P1"),
        commercial_value=3,
        product_impact=4,
        market_value=3,
        impacted_parts=", ".join(components),
        sizing=str(first.get("sizing") or "M"),
        complexity=str(first.get("complexity") or "Medium"),
        ordering_score=None,
        ordering_rationale=str(first["rationale_lines"][-1]).removeprefix("- ranking basis: "),
        confidence="medium",
        founder_override=False,
        override_note="",
        override_review_date="",
        release=release_selector,
        update_existing_titles=True,
        section_overrides_by_title=_section_overrides(
            rows,
            security_posture=security_posture,
        ),
    )


def _section_overrides(
    rows: Sequence[Mapping[str, Any]],
    *,
    security_posture: str,
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        title = str(row["title"])
        risks = _strings(row.get("risks"))
        metrics = _strings(row.get("success_metrics"))
        while len(metrics) < 4:
            metrics.append(
                (
                    f"{title} preserves every cited semantic fact and relation."
                    if len(metrics) == 2
                    else f"{title} remains inside its typed component and release boundary."
                )
            )
        override = {
            "problem": str(row["problem"]),
            "customer": str(row["customer"]),
            "opportunity": str(row["opportunity"]),
            "product_view": str(row["product_view"]),
            "success_metrics": metrics,
            "domain_risk": " ".join(risks),
            "security_posture": security_posture,
            "priority": str(row.get("priority") or "P1"),
            "sizing": str(row.get("sizing") or "M"),
            "complexity": str(row.get("complexity") or "Medium"),
            "impacted_parts": ", ".join(_strings(row.get("component_focus"))),
            "ordering_rationale": str(row["rationale_lines"][-1]).removeprefix("- ranking basis: "),
            "rationale_lines": _strings(row.get("rationale_lines")),
            "extra_sections": {
                "First Path And Boundary": f"- First path: {title} — {row['recommended_first_slice']}"
            },
        }
        result[title] = override
        result[semantic_artifact_identifier(title)] = override
    return result


def _strings(value: Any) -> list[str]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        return []
    return [str(row).strip() for row in value if str(row).strip()]


__all__ = [
    "build_verified_semantic_proposal_for_repo",
    "compile_verified_semantic_transaction",
]
