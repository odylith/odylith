"""Compile sealed model-authored Greenfield intent into a governed transaction."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import (
    build_confirmed_greenfield_proposal,
    sealed_authored_projection,
)
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
    authored_source_custody,
    require_relation_authority_parity,
)
from odylith.runtime.domain_intelligence.greenfield_authored_radar_ordering import (
    authored_ordering_decision,
    render_authored_ordering_rationale,
)
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    product_create_transaction_to_dict as product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_create_transaction import write_compiled_product_create_transaction_file
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_FACTS_HASH_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_facts_hash
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    rebind_authoritative_product_facts,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority
from odylith.runtime.domain_intelligence import greenfield_model_profile_contract as model_profiles
from odylith.runtime.domain_intelligence.project_intelligence_binding import attach_project_intelligence_bindings
from odylith.runtime.domain_intelligence.proposal_tribunal import raise_for_failed_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import assert_greenfield_completion_ready
from odylith.runtime.domain_intelligence.greenfield_preconfirm_engine import (
    run_greenfield_preconfirm_engine,
)
from odylith.runtime.domain_intelligence.proposal_validation import (
    require_distinct_supplied_diagram_sources,
    validate_host_reasoned_proposal,
)


_DEFAULT_PRECONFIRM_REPAIR_TIER = "auto"
DEFAULT_PRECONFIRM_REPAIR_TIER = _DEFAULT_PRECONFIRM_REPAIR_TIER


def _confirmed_intent_source_evidence(repo_root: Path) -> dict[str, Any]:
    """Return pre-confirm repo evidence without scanning source files."""

    root = Path(repo_root).expanduser().resolve()
    return {
        "repo_name": root.name,
        "description": "",
        "languages": [],
        "frameworks": [],
        "monorepo": False,
        "source_posture": "confirmed_intent_only",
        "source_summary": dict(vars(SourceSummary())),
    }


def build_greenfield_proposal(
    *,
    repo_root: Path,
    prompt: str,
    release_selector: str = "",
    confirmed_intent: Mapping[str, Any] | None = None,
    require_completion_ready: bool = True,
) -> dict[str, Any]:
    """Return the governed proposal after Product Intent is confirmed.

    The no-write ``greenfield propose`` command treats prompt and edit text as
    evidence, compiles the complete validated transaction, and renders its sole
    confirmation view. A later CONFIRM only commits those sealed bytes.
    """

    root = Path(repo_root).expanduser().resolve()
    if not isinstance(confirmed_intent, Mapping):
        raise ValueError(
            "confirmed greenfield proposal requires accepted Product Intent Confirmation data; "
            "prompt-only confirmed proposal construction is disabled."
        )
    intent_title = str(confirmed_intent.get("title") or "").strip() or "Greenfield Project"
    intent_authority = confirmed_intent.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent_authority, Mapping):
        raise ValueError("confirmed Product Intent authority is missing; rebuild from a typed custody envelope")
    intent_authority = dict(intent_authority)
    require_product_intent_authority(intent_authority)
    model_authored = sealed_authored_projection(confirmed_intent)
    if not model_authored:
        raise ValueError(
            "confirmed Greenfield proposal requires sealed model-authored relation authority"
        )
    evidence = _confirmed_intent_source_evidence(root)
    proposal = build_confirmed_greenfield_proposal(
        prompt="",
        title=intent_title,
        observed_source=evidence,
        release_selector=release_selector,
        confirmed_intent=confirmed_intent,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    if sealed_authored_projection(proposal) != model_authored:
        raise ValueError("Greenfield proposal route drifted from sealed relation authority")
    proposal = attach_project_intelligence_bindings(proposal)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    proposal_intent = proposal.get("intent")
    if isinstance(proposal_intent, Mapping):
        proposal["intent"] = rebind_authoritative_product_facts(
            proposal_intent,
            authoritative_intent=confirmed_intent,
        )
    if sealed_authored_projection(proposal) != model_authored:
        raise ValueError("Greenfield proposal completion drifted from sealed relation authority")
    validate_host_reasoned_proposal(proposal)
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    raise_for_failed_greenfield_tribunal(run_greenfield_tribunal(proposal, release_selector=selector))
    if require_completion_ready:
        assert_greenfield_completion_ready(proposal, release_selector=selector)
    return proposal


def write_product_create_transaction_file(path: Path, transaction: ProductCreateTransaction) -> Path:
    return write_compiled_product_create_transaction_file(path, transaction)


def _backlog_section_overrides(proposal: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Return source-custodied Radar fields from the authored projection."""

    if not sealed_authored_projection(proposal):
        raise ValueError("Greenfield backlog compilation requires sealed model-authored relations")
    overrides: dict[str, dict[str, Any]] = {}
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    for row in backlog_rows:
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        success_metrics = list(row_text_tuple(row, "success_metrics"))
        ordering_decision = authored_ordering_decision(row.get("ordering_decision"))
        override = {
            "problem": str(row.get("problem", "")).strip(),
            "customer": str(row.get("customer", "")).strip(),
            "opportunity": str(row.get("opportunity", "")).strip(),
            "product_view": str(row.get("product_view", "")).strip(),
            "success_metrics": success_metrics,
            "domain_risk": "",
            "security_posture": "",
            "priority": str(row.get("priority", "P1")).strip() or "P1",
            "sizing": str(row.get("sizing", "M")).strip() or "M",
            "complexity": str(row.get("complexity", "Medium")).strip() or "Medium",
            "impacted_parts": _authored_impacted_parts(row, proposal),
            "ordering_rationale": ordering_decision["ranking_basis"],
            "rationale_lines": render_authored_ordering_rationale(ordering_decision),
        }
        supplied_sections = row.get("radar_sections")
        if not isinstance(supplied_sections, Mapping):
            raise ValueError("model-authored backlog row is missing its structural Radar projection")
        extra_sections = {
            str(section): str(body)
            for section, body in supplied_sections.items()
            if str(section) and str(body)
        }
        if extra_sections:
            override["extra_sections"] = extra_sections
        overrides[title] = override
        overrides[slugify(title)] = override
    return overrides


def _authored_impacted_parts(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    """Resolve typed component references without interpreting workstream prose."""

    raw_references = row.get("component_focus")
    if not isinstance(raw_references, Sequence) or isinstance(raw_references, (str, bytes)):
        raise ValueError("model-authored backlog row is missing typed component references")
    references = [str(value).strip() for value in raw_references]
    if not references or any(not value for value in references):
        raise ValueError("model-authored backlog row has invalid typed component references")
    components = [value for value in proposal.get("components", []) if isinstance(value, Mapping)]
    labels_by_id = {
        str(component.get("component_id") or "").strip(): str(component.get("label") or "").strip()
        for component in components
        if str(component.get("component_id") or "").strip()
    }
    labels: list[str] = []
    for reference in references:
        label = labels_by_id.get(reference, "")
        if not label:
            raise ValueError(
                f"model-authored backlog row references unknown component `{reference}`"
            )
        if label not in labels:
            labels.append(label)
    return ", ".join(labels)


def _backlog_apply_args(proposal: Mapping[str, Any], *, release_selector: str) -> argparse.Namespace:
    if not sealed_authored_projection(proposal):
        raise ValueError("Greenfield backlog compilation requires sealed model-authored relations")
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    if not rows:
        raise ValueError("model-authored Greenfield proposal has no backlog projection")
    first = rows[0]
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), Mapping) else {}
    ordering_decision = authored_ordering_decision(first.get("ordering_decision"))
    intent_authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent_authority, Mapping):
        raise ValueError("model-authored backlog projection is missing sealed Product Intent authority")
    return argparse.Namespace(
        workstream_type="standalone",
        problem=str(first.get("problem", "")).strip(),
        customer=str(first.get("customer", "")).strip(),
        opportunity=str(first.get("opportunity", "")).strip(),
        product_view=str(first.get("product_view", "")).strip(),
        success_metrics="\n".join(f"- {item}" for item in row_text_tuple(first, "success_metrics")),
        domain_risk="",
        security_posture="",
        priority=str(first.get("priority", "P1")).strip() or "P1",
        commercial_value=3,
        product_impact=4,
        market_value=3,
        impacted_parts=_authored_impacted_parts(first, proposal),
        sizing=str(first.get("sizing", "M")).strip() or "M",
        complexity=str(first.get("complexity", "Medium")).strip() or "Medium",
        ordering_score=None,
        ordering_rationale=ordering_decision["ranking_basis"],
        confidence="medium",
        founder_override=False,
        override_note="",
        override_review_date="",
        release=release_selector,
        update_existing_titles=True,
        source_custody=authored_source_custody(intent=intent, authority=intent_authority),
        section_overrides_by_title=_backlog_section_overrides(proposal),
    )


def _build_authored_prewrite_package(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    proposal_ready: bool = False,
    repair_tier: str = _DEFAULT_PRECONFIRM_REPAIR_TIER,
    preconfirm_elapsed_seconds: float = 0.0,
    model_authoring_tier: str = "",
    model_authoring_receipt: Mapping[str, Any] | None = None,
) -> tuple[Mapping[str, Any], Any, greenfield_apply_prewrite.GreenfieldPrewriteBuild, dict[str, Any]]:
    if not sealed_authored_projection(proposal):
        raise ValueError("Greenfield pre-confirm requires sealed model-authored relations")
    requested_tier = model_profiles.normalize_greenfield_model_repair_tier(repair_tier)
    selected_profile = model_profiles.get_greenfield_model_profile(
        model_profiles.model_profile_id_for_repair_tier(requested_tier)
    )
    normalized_authoring_tier = str(model_authoring_tier or "").strip().casefold()
    if normalized_authoring_tier and normalized_authoring_tier != selected_profile.repair_tier:
        raise ValueError("Greenfield model authoring receipt does not match the selected pre-call profile")
    model_authoring_tier = normalized_authoring_tier or selected_profile.repair_tier

    def build_prewrite(
        current_proposal: Mapping[str, Any],
        tribunal: Any,
    ) -> greenfield_apply_prewrite.GreenfieldPrewriteBuild:
        return greenfield_apply_prewrite.build_prewrite_completion_package(
            root=root,
            proposal=current_proposal,
            release_selector=release_selector,
            backlog_args=_backlog_apply_args(current_proposal, release_selector=release_selector),
            validation_gate=tribunal.to_dict(),
            release_assignment_note=greenfield_apply_prewrite.release_assignment_note(selector=release_selector),
        )

    result = run_greenfield_preconfirm_engine(
        proposal=proposal,
        release_selector=release_selector,
        build_prewrite=build_prewrite,
        proposal_ready=proposal_ready,
        repair_tier=repair_tier,
        elapsed_before_start_seconds=preconfirm_elapsed_seconds,
        model_authoring_tier=model_authoring_tier,
        model_authoring_receipt=model_authoring_receipt,
    )
    if not sealed_authored_projection(result.proposal):
        raise ValueError("Greenfield pre-confirm route drifted from sealed relation authority")
    return result.proposal, result.tribunal, result.prewrite_build, result.manifest


def compile_greenfield_create_transaction(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    proposal_ready: bool = False,
    repair_tier: str = _DEFAULT_PRECONFIRM_REPAIR_TIER,
    preconfirm_elapsed_seconds: float = 0.0,
    model_authoring_tier: str = "",
    model_authoring_receipt: Mapping[str, Any] | None = None,
) -> ProductCreateTransaction:
    """Compile and quality-gate the complete create package before commit."""

    root = Path(repo_root).expanduser().resolve()
    release_selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    intent_authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent_authority, Mapping):
        raise ValueError("ProductCreateTransaction is missing confirmed Product Intent authority")
    intent_authority = dict(intent_authority)
    require_product_intent_authority(intent_authority)
    authoritative_intent = proposal.get("intent")
    if not isinstance(authoritative_intent, Mapping):
        raise ValueError("ProductCreateTransaction proposal is missing typed Product Intent")
    authored_relations = require_relation_authority_parity(authoritative_intent, intent_authority)
    if not authored_relations:
        raise ValueError(
            "ProductCreateTransaction requires sealed model-authored relation authority"
        )
    authored_projection = proposal.get("projection_origin") == AUTHORED_PROJECTION_ORIGIN
    if bool(authored_relations) != authored_projection:
        raise ValueError(
            "ProductCreateTransaction authored projection origin does not match sealed relation authority"
        )
    authority_facts_hash = str(intent_authority.get(PRODUCT_FACTS_HASH_KEY, "")).strip()
    if product_facts_hash(authoritative_intent) != authority_facts_hash:
        raise ValueError(
            "ProductCreateTransaction proposal facts do not match its sealed Product Intent authority; "
            "rebuild the transaction before showing CONFIRM"
        )
    require_distinct_supplied_diagram_sources(proposal.get("diagrams"))
    proposal, tribunal, prewrite_build, quality_manifest = _build_authored_prewrite_package(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=proposal_ready,
        repair_tier=repair_tier,
        preconfirm_elapsed_seconds=preconfirm_elapsed_seconds,
        model_authoring_tier=model_authoring_tier,
        model_authoring_receipt=model_authoring_receipt,
    )
    package_proposal = prewrite_build.package.proposal
    if not isinstance(package_proposal, Mapping) or package_proposal != proposal:
        raise ValueError(
            "Greenfield pre-confirm package drifted from the sealed model-authored proposal"
        )
    proposal = package_proposal
    transaction = build_product_create_transaction(
        proposal=proposal,
        release_selector=release_selector,
        validation_gate=tribunal.to_dict() if hasattr(tribunal, "to_dict") else {},
        prewrite_package=prewrite_build.package,
        backlog_result=prewrite_build.backlog_result,
        intent_authority=intent_authority,
        quality_manifest=quality_manifest,
        repo_root=root,
    )
    require_product_create_transaction_verified(transaction)
    return transaction
