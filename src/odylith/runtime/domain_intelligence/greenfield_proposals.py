"""Confirmed greenfield governance contracts for consumer repos.

Odylith should not pretend a small built-in catalog can understand every
possible project the operator may ask for. This module keeps the no-write
Product Intent Confirmation separate from the confirmed create path, then
builds, repairs, validates, gates, and writes the governed proposal without
pushing internal normalization or repair work back onto the host.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import contextlib
import io
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_prewrite_projection_rerender
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import ensure_greenfield_create_baseline
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.artifact_enrichment import build_artifact_enrichment
from odylith.runtime.domain_intelligence.greenfield_cli_output import print_apply_result
from odylith.runtime.domain_intelligence.greenfield_backlog_impact import derive_greenfield_impacted_parts
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import domain_risk_for_row
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import proposal_posture_text
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
from odylith.runtime.domain_intelligence.proposal_tribunal import raise_for_failed_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import assert_greenfield_completion_ready
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmEngineError,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmRepairContext,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    finalize_greenfield_post_confirm_manifest,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    POST_CONFIRM_MAX_PASSES,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    POST_CONFIRM_REPAIR_TIERS,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    run_greenfield_post_confirm_engine,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patch_apply import (
    apply_greenfield_patchset_repairs,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patch_apply import (
    complete_greenfield_semantic_apply_payload,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_rescue_planner import (
    enrich_rescue_patchset_with_structured_plan,
)
from odylith.runtime.domain_intelligence.greenfield_phrase_quality import collapse_adjacent_duplicate_terms
from odylith.runtime.domain_intelligence.greenfield_semantic_quality import normalize_project_title
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal
from odylith.runtime.common import display_text
from odylith.runtime.project_intelligence.intent_confirmation import build_product_intent_confirmation
from odylith.runtime.project_intelligence.intent_confirmation import format_product_intent_confirmation_text


def _prompt_text(prompt: str) -> str:
    text = " ".join(str(prompt or "").split()).strip()
    text = re.sub(r"^odylith[,:\s-]+", "", text, flags=re.IGNORECASE).strip()
    return text or "new project"


def _intent_title(prompt: str) -> str:
    text = _prompt_text(prompt)
    lowered = text.casefold()
    for prefix in (
        "draft a product-first greenfield proposal for ",
        "draft product-first greenfield proposal for ",
        "draft a greenfield proposal for ",
        "draft greenfield proposal for ",
        "create a product-first greenfield proposal for ",
        "create product-first greenfield proposal for ",
        "create a greenfield proposal for ",
        "create greenfield proposal for ",
        "draft a proposal for ",
        "draft proposal for ",
        "greenfield proposal for ",
        "product-first greenfield proposal for ",
        "proposal for ",
    ):
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    lowered = text.casefold()
    for prefix in (
        "build ",
        "create ",
        "make ",
        "help me govern ",
        "govern ",
        "design ",
        "draft ",
    ):
        if lowered.startswith(prefix):
            text = text[len(prefix):].strip()
            break
    text = re.sub(r"^(?:a|an)\s+", "", text, flags=re.IGNORECASE).strip()
    text = _strip_greenfield_directives(text).strip(" .")
    text = _strip_instruction_sentence_tail(text)
    text = _strip_title_target_context(text)
    if not text or len(text) < 4:
        return "Greenfield Project"
    words = [_title_token(word) for word in text.split()]
    clipped = words[:16]
    while clipped and clipped[-1].casefold().strip(".,;:") in {"a", "an", "and", "for", "from", "in", "of", "on", "or", "the", "to", "with"}:
        clipped.pop()
    return normalize_project_title(" ".join(clipped or words[:1]), fallback="Greenfield Project").canonical_title


_GREENFIELD_DIRECTIVE_RE = re.compile(
    r"(?is)(?:"
    r"\bshow\s+(?:the\s+)?interpretation\b|"
    r"\bshow\s+(?:the\s+)?direction\s+choices\b|"
    r"\bdo\s+not\s+write\b|"
    r"\bdon['’]?t\s+write\b|"
    r"\bno\s+files?\s+changed\b|"
    r"\buntil\s+i\s+confirm\b|"
    r"\bbefore\s+i\s+confirm\b|"
    r"\bwhen\s+i\s+confirm\b|"
    r"\bwith\s+backlog\b|"
    r"\band\s+backlog\b|"
    r"\bwith\s+registry\b|"
    r"\band\s+registry\b|"
    r"\bwith\s+atlas\b|"
    r"\band\s+atlas\b|"
    r"\bwith\s+diagrams?\b|"
    r"\band\s+diagrams?\b|"
    r"\bgenerate\s+governance\b|"
    r"\bcreate\s+governance\b"
    r").*$"
)


def _strip_greenfield_directives(text: str) -> str:
    """Remove operator instructions that should not become the product title."""

    stripped = _GREENFIELD_DIRECTIVE_RE.sub("", text).strip()
    stripped = re.sub(r"\b(for me|please)\b\.?$", "", stripped, flags=re.IGNORECASE).strip()
    return stripped or text


def _strip_instruction_sentence_tail(text: str) -> str:
    head, separator, tail = str(text or "").partition(". ")
    if not separator:
        return text
    head = head.strip(" .")
    tail = tail.strip()
    if not head or len(head.split()) > 12:
        return text
    if re.match(r"^(?:focus|use|include|ensure|make|keep|it|the\s+first|release)\b", tail, flags=re.IGNORECASE):
        return head
    return text


def _strip_title_target_context(text: str) -> str:
    """Remove target-context tails from command-derived fallback titles."""

    product_containers = (
        "app",
        "application",
        "assistant",
        "board",
        "console",
        "dashboard",
        "desk",
        "engine",
        "hub",
        "pipeline",
        "platform",
        "portal",
        "service",
        "tool",
        "tracker",
        "workflow",
        "workspace",
    )
    container_pattern = "|".join(re.escape(term) for term in product_containers)
    match = re.match(
        rf"^(?P<head>.+?\b(?:{container_pattern}))\s+for\s+(?:a|an|the)\s+.+?\b(?:including|with|[A-Za-z]+ing)\b.*$",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return text
    head = match.group("head").strip(" .")
    return head if len(head.split()) >= 3 else text


_TITLE_ACRONYMS = {
    "ai": "AI",
    "api": "API",
    "b2b": "B2B",
    "cli": "CLI",
    "crm": "CRM",
    "gis": "GIS",
    "iot": "IoT",
    "llm": "LLM",
    "ml": "ML",
    "nasa": "NASA",
    "ode": "ODE",
    "pde": "PDE",
    "rag": "RAG",
    "sdk": "SDK",
    "soc2": "SOC2",
    "ui": "UI",
    "ux": "UX",
}

_MAX_PACKAGE_REPAIR_PASSES = POST_CONFIRM_MAX_PASSES
_DEFAULT_POST_CONFIRM_REPAIR_TIER = "auto"


def _title_token(token: str) -> str:
    parts = str(token).split("-")
    rendered: list[str] = []
    for index, part in enumerate(parts):
        key = part.casefold()
        if key in _TITLE_ACRONYMS:
            rendered.append(_TITLE_ACRONYMS[key])
        elif _looks_like_source_mixed_case_token(part):
            rendered.append(part)
        elif index > 0 and part.islower():
            rendered.append(part)
        else:
            rendered.append(part[:1].upper() + part[1:] if part else part)
    return "-".join(rendered)


def _looks_like_source_mixed_case_token(value: str) -> bool:
    letters = [char for char in str(value or "") if char.isalpha()]
    return bool(len(letters) >= 2 and any(char.islower() for char in letters) and any(char.isupper() for char in letters[1:]))


def _source_evidence(repo_root: Path) -> dict[str, Any]:
    identity = repo_analysis.read_project_identity(repo_root)
    summary = repo_analysis.summarize_source_inventory(repo_root)
    if summary.app_modules >= 3:
        posture = "app_ready"
    elif summary.app_modules:
        posture = "thin_app"
    elif summary.metadata_files:
        posture = "metadata_only"
    elif summary.docs_files:
        posture = "docs_only"
    else:
        posture = "empty_or_no_app_source"
    return {
        "repo_name": identity.name or repo_root.name,
        "description": identity.description,
        "languages": list(identity.languages),
        "frameworks": list(identity.frameworks),
        "monorepo": bool(identity.monorepo),
        "source_posture": posture,
        "source_summary": dict(vars(summary if isinstance(summary, SourceSummary) else SourceSummary())),
    }


def _confirmed_intent_source_evidence(repo_root: Path) -> dict[str, Any]:
    """Return post-confirm repo evidence without scanning source files."""

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

    The no-write ``greenfield propose`` command still asks the host to narrate a
    human Product Intent Confirmation first. After that confirmation, Odylith
    owns the schema-shaped proposal artifact itself: it builds a prompt-general
    proposal, normalizes it, validates it, and runs the deterministic proposal
    gate before any write command sees it.
    """

    root = Path(repo_root).expanduser().resolve()
    if not isinstance(confirmed_intent, Mapping):
        raise ValueError(
            "confirmed greenfield proposal requires accepted Product Intent Confirmation data; "
            "prompt-only confirmed proposal construction is disabled."
        )
    intent_title = str(confirmed_intent.get("title") or "").strip() or "Greenfield Project"
    intent_prompt = str(prompt or confirmed_intent.get("prompt") or intent_title).strip() or intent_title
    evidence = _confirmed_intent_source_evidence(root)
    proposal = build_confirmed_greenfield_proposal(
        prompt=intent_prompt,
        title=intent_title,
        observed_source=evidence,
        release_selector=release_selector,
        confirmed_intent=confirmed_intent,
    )
    proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
    proposal = complete_confirmed_proposal(proposal, release_selector=release_selector)
    proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
    proposal = complete_greenfield_semantic_apply_payload(proposal, release_selector=release_selector)
    validate_host_reasoned_proposal(proposal)
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    raise_for_failed_greenfield_tribunal(run_greenfield_tribunal(proposal, release_selector=selector))
    if require_completion_ready:
        assert_greenfield_completion_ready(proposal, release_selector=selector)
    return proposal


def _load_proposal(args: argparse.Namespace) -> dict[str, Any]:
    if str(getattr(args, "proposal_file", "") or "").strip():
        path = Path(str(args.proposal_file)).expanduser().resolve()
        return json.loads(path.read_text(encoding="utf-8"))
    raw = str(getattr(args, "proposal_json", "") or "").strip()
    if raw:
        return json.loads(raw)
    raise ValueError("provide --proposal-file or --proposal-json")


def _load_confirmed_intent_args(args: argparse.Namespace, *, repo_root: Path) -> dict[str, Any]:
    intent_file = str(getattr(args, "intent_file", "") or "").strip()
    if not intent_file:
        raise ValueError(
            "confirmed greenfield create requires --intent-file with the operator-confirmed Product Intent Confirmation. "
            "Write the same product story, actors, systems, first path, assumptions, ambiguities, and proof boundary "
            "that the operator confirmed to .odylith/runtime/greenfield/confirmed-intent.md, then rerun with "
            "--intent-file .odylith/runtime/greenfield/confirmed-intent.md. Odylith will not write records from a thin prompt."
        )
    path = Path(intent_file).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    intent = load_confirmed_intent_file(
        path,
        prompt=str(getattr(args, "prompt", "") or ""),
        fallback_title=_intent_title(str(getattr(args, "prompt", "") or "")),
    )
    if path.suffix.lower() != ".json":
        write_structured_confirmed_intent_file(path, intent)
    return intent


def _row_posture_text(row: Mapping[str, Any], proposal: Mapping[str, Any], *keys: str) -> str:
    local = row_text_tuple(row, *keys)
    if local:
        return " ".join(local).strip()
    return proposal_posture_text(proposal, *keys)


def _security_posture_for_row(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    return (
        _row_posture_text(row, proposal, "security_posture", "security_compliance", "compliance_posture")
        or proposal_posture_text(proposal, "security_compliance")
    )


def _backlog_section_overrides(proposal: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    parent_title = str(backlog_rows[0].get("title", "")).strip() if backlog_rows else ""
    for row in backlog_rows:
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        success_metrics = list(row_text_tuple(row, "success_metrics"))
        if title == parent_title:
            success_metrics.extend(
                [
                    "Program waves are captured before implementation starts.",
                    "The provisional release plan is reviewed before release targeting writes occur.",
                ]
            )
        override = {
            "problem": str(row.get("problem", "")).strip(),
            "customer": str(row.get("customer", "")).strip(),
            "opportunity": str(row.get("opportunity", "")).strip(),
            "product_view": str(row.get("product_view", "")).strip(),
            "success_metrics": success_metrics,
            "domain_risk": domain_risk_for_row(row, proposal),
            "security_posture": _security_posture_for_row(row, proposal),
            "priority": str(row.get("priority", "P1")).strip() or "P1",
            "sizing": str(row.get("sizing", "M")).strip() or "M",
            "complexity": str(row.get("complexity", "Medium")).strip() or "Medium",
            "impacted_parts": derive_greenfield_impacted_parts(row, proposal),
            "ordering_rationale": _greenfield_ordering_rationale(row),
            "rationale_lines": _greenfield_rationale_lines(row),
        }
        enrichment = build_artifact_enrichment(row=row, proposal=proposal)
        extra_sections: dict[str, str] = {}
        extra_sections.update(enrichment.radar_sections)
        if extra_sections:
            override["extra_sections"] = extra_sections
        override = _clean_greenfield_backlog_override(override)
        overrides[title] = override
        overrides[slugify(title)] = override
    return overrides


def _clean_greenfield_backlog_override(value: Any) -> Any:
    if isinstance(value, str):
        return collapse_adjacent_duplicate_terms(value)
    if isinstance(value, list):
        return [_clean_greenfield_backlog_override(item) for item in value]
    if isinstance(value, dict):
        return {key: _clean_greenfield_backlog_override(item) for key, item in value.items()}
    return value


def _greenfield_ordering_rationale(row: Mapping[str, Any]) -> str:
    first_slice = str(row.get("recommended_first_slice", "")).strip()
    opportunity = str(row.get("opportunity", "")).strip()
    return opportunity or first_slice


def _greenfield_rationale_lines(row: Mapping[str, Any]) -> list[str]:
    explicit = list(row_text_tuple(row, "rationale_lines"))
    if _has_required_rationale_bullets(explicit):
        return explicit
    return []


def _has_required_rationale_bullets(lines: Sequence[str]) -> bool:
    text = "\n".join(str(line).casefold() for line in lines)
    return all(
        bullet in text
        for bullet in (
            "- why now:",
            "- expected outcome:",
            "- tradeoff:",
            "- deferred for now:",
            "- ranking basis:",
        )
    )


def _backlog_apply_args(proposal: Mapping[str, Any], *, release_selector: str) -> argparse.Namespace:
    rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    first = rows[0]
    return argparse.Namespace(
        workstream_type="umbrella" if len(rows) > 1 else "standalone",
        problem=str(first.get("problem", "")).strip(),
        customer=str(first.get("customer", "")).strip(),
        opportunity=str(first.get("opportunity", "")).strip(),
        product_view=str(first.get("product_view", "")).strip(),
        success_metrics="\n".join(f"- {item}" for item in row_text_tuple(first, "success_metrics")),
        domain_risk=domain_risk_for_row(first, proposal),
        security_posture=_security_posture_for_row(first, proposal),
        priority=str(first.get("priority", "P1")).strip() or "P1",
        commercial_value=3,
        product_impact=4,
        market_value=3,
        impacted_parts=derive_greenfield_impacted_parts(first, proposal),
        sizing=str(first.get("sizing", "M")).strip() or "M",
        complexity=str(first.get("complexity", "Medium")).strip() or "Medium",
        ordering_score=None,
        ordering_rationale=_greenfield_ordering_rationale(first),
        confidence="medium",
        founder_override=False,
        override_note="",
        override_review_date="",
        release=release_selector,
        update_existing_titles=True,
        section_overrides_by_title=_backlog_section_overrides(proposal),
    )


def _build_repaired_prewrite_package(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    proposal_ready: bool = False,
    repair_tier: str = _DEFAULT_POST_CONFIRM_REPAIR_TIER,
) -> tuple[Mapping[str, Any], Any, greenfield_apply_prewrite.GreenfieldPrewriteBuild, dict[str, Any]]:
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
            release_assignment_note=greenfield_apply_write.release_assignment_note(selector=release_selector),
        )

    result = run_greenfield_post_confirm_engine(
        proposal=proposal,
        release_selector=release_selector,
        build_prewrite=build_prewrite,
        rerender_prewrite=lambda current_proposal, tribunal, previous_prewrite_build, projections: (
            greenfield_prewrite_projection_rerender.rerender_prewrite_package_projections(
                root=root,
                previous_prewrite_build=previous_prewrite_build,
                proposal=current_proposal,
                release_selector=release_selector,
                validation_gate=tribunal.to_dict(),
                projections=projections,
                release_assignment_note=greenfield_apply_write.release_assignment_note(selector=release_selector),
            )
        ),
        repair_proposal=lambda current, context: _repair_confirmed_apply_payload(
            current,
            release_selector=release_selector,
            repair_context=context,
            repo_root=root,
        ),
        prepare_repair_context=lambda current, context: _prepare_confirmed_apply_repair_context(
            current,
            repair_context=context,
            repo_root=root,
        ),
        proposal_ready=proposal_ready,
        max_passes=_MAX_PACKAGE_REPAIR_PASSES,
        repair_tier=repair_tier,
    )
    return result.proposal, result.tribunal, result.prewrite_build, result.manifest


def _repair_confirmed_apply_payload(
    proposal: Mapping[str, Any],
    *,
    release_selector: str,
    repair_context: GreenfieldPostConfirmRepairContext | None = None,
    repo_root: Path | None = None,
) -> Mapping[str, Any]:
    repair_context = enrich_rescue_patchset_with_structured_plan(
        proposal,
        repair_context=repair_context,
        repo_root=repo_root,
    )
    return apply_greenfield_patchset_repairs(
        proposal,
        release_selector=release_selector,
        repair_context=repair_context,
    )


def _prepare_confirmed_apply_repair_context(
    proposal: Mapping[str, Any],
    *,
    repair_context: GreenfieldPostConfirmRepairContext,
    repo_root: Path | None,
) -> GreenfieldPostConfirmRepairContext:
    """Attach bounded structured repair evidence before the engine records custody."""

    enriched = enrich_rescue_patchset_with_structured_plan(
        proposal,
        repair_context=repair_context,
        repo_root=repo_root,
    )
    return enriched or repair_context


def apply_greenfield_proposal(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    confirm: bool,
    release_selector: str = "",
    proposal_ready: bool = False,
    repair_tier: str = _DEFAULT_POST_CONFIRM_REPAIR_TIER,
) -> dict[str, Any]:
    """Apply a confirmed proposal using owned governance authoring paths."""

    post_confirm_started = time.perf_counter()
    if not confirm:
        raise ValueError("--confirm is required before greenfield apply writes accepted product records")
    if not proposal_ready:
        proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
        proposal = complete_confirmed_proposal(proposal, release_selector=release_selector)
        proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
        proposal = complete_greenfield_semantic_apply_payload(proposal, release_selector=release_selector)
        validate_host_reasoned_proposal(proposal)
    root = Path(repo_root).expanduser().resolve()
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    if not backlog_rows:
        raise ValueError("proposal has no backlog records")
    release_selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    proposal, tribunal, prewrite_build, post_confirm_manifest = _build_repaired_prewrite_package(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=proposal_ready,
        repair_tier=repair_tier,
    )
    if isinstance(prewrite_build.package.proposal, Mapping):
        proposal = prewrite_build.package.proposal
    backlog_result = prewrite_build.backlog_result
    completion_priority_write_policy = greenfield_apply_write.completion_priority_write_policy_from_manifest(post_confirm_manifest)
    with GreenfieldApplyTransaction(root) as transaction:
        ensure_greenfield_create_baseline(root)
        result = greenfield_apply_write.write_greenfield_proposal(
            root=root,
            proposal=proposal,
            release_selector=release_selector,
            tribunal=tribunal,
            backlog_result=backlog_result,
            prewrite_package=prewrite_build.package,
            completion_priority_write_policy=completion_priority_write_policy,
        )
        transaction.commit()
        final_manifest = finalize_greenfield_post_confirm_manifest(
            post_confirm_manifest,
            whole_project_elapsed_seconds=time.perf_counter() - post_confirm_started,
            write_transaction_status="committed",
        )
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
        return result

def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="odylith greenfield", description="Preview and apply confirmation-gated greenfield product records.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Preview a confirmation-gated greenfield product proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--prompt", required=True)
    propose.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    propose.add_argument(
        "--detail",
        choices=("brief", "full"),
        default="brief",
        help="Text preview depth after intent is confirmed. Default propose shows only Product Intent Confirmation.",
    )
    propose.add_argument(
        "--confirm-intent",
        action="store_true",
        help="Build the full proposal preview or JSON after the operator confirms the Product Intent Confirmation.",
    )
    propose.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help="Markdown/text/JSON file containing the operator-confirmed Product Intent Confirmation.",
    )
    apply = subparsers.add_parser("apply", help="Apply a confirmed greenfield product proposal.")
    apply.add_argument("--repo-root", default=".")
    apply.add_argument("--proposal-file", default="")
    apply.add_argument("--proposal-json", default="")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--release", default="")
    apply.add_argument(
        "--repair-tier",
        choices=POST_CONFIRM_REPAIR_TIERS,
        default=_DEFAULT_POST_CONFIRM_REPAIR_TIER,
        help=(
            "Post-confirm repair budget: auto keeps the standard path under 60s and enters 90s rescue only "
            "after a repairable final semantic or quality gate failure; deep is explicit 120s premium/CI repair."
        ),
    )
    apply.add_argument("--json", action="store_true", dest="as_json")
    create = subparsers.add_parser("create", help="Create confirmed greenfield records from Product Intent.")
    create.add_argument("--repo-root", default=".")
    create.add_argument("--prompt", required=True)
    create.add_argument(
        "--intent-file",
        "--confirmed-intent-file",
        default="",
        dest="intent_file",
        help="Markdown/text/JSON file containing the operator-confirmed Product Intent Confirmation.",
    )
    create.add_argument("--confirm", action="store_true")
    create.add_argument("--release", default="")
    create.add_argument(
        "--repair-tier",
        choices=POST_CONFIRM_REPAIR_TIERS,
        default=_DEFAULT_POST_CONFIRM_REPAIR_TIER,
        help=(
            "Post-confirm repair budget: auto keeps the standard path under 60s and enters 90s rescue only "
            "after a repairable final semantic or quality gate failure; deep is explicit 120s premium/CI repair."
        ),
    )
    create.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def _run_with_optional_stdout_capture(
    *,
    enabled: bool,
    action: Callable[[], dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    if not enabled:
        return action(), []
    stdout_fd = 1
    try:
        probe_fd = os.dup(stdout_fd)
    except OSError:
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            result = action()
        return result, _captured_lines(captured_output.getvalue())
    else:
        os.close(probe_fd)
    with tempfile.TemporaryFile(mode="w+t", encoding="utf-8") as captured_output:
        sys.stdout.flush()
        saved_fd = os.dup(stdout_fd)
        try:
            os.dup2(captured_output.fileno(), stdout_fd)
            with contextlib.redirect_stdout(captured_output):
                result = action()
                captured_output.flush()
        finally:
            os.dup2(saved_fd, stdout_fd)
            os.close(saved_fd)
        captured_output.seek(0)
        return result, _captured_lines(captured_output.read())


def _captured_lines(text: str) -> list[str]:
    return [line.rstrip() for line in str(text or "").splitlines() if line.strip()]


def _with_operator_output(result: Mapping[str, Any], captured: Sequence[str]) -> dict[str, Any]:
    payload = dict(result)
    if captured:
        payload["operator_output"] = list(captured)
    return payload


def _print_greenfield_error(exc: Exception, *, as_json: bool) -> None:
    if as_json:
        payload: dict[str, Any] = {"mode": "error", "error": str(exc)}
        if isinstance(exc, GreenfieldPostConfirmEngineError):
            payload["post_confirm_quality_manifest"] = exc.manifest
        print(json.dumps(payload, indent=2, sort_keys=True))
        return
    print(str(exc))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        if not bool(args.confirm_intent):
            confirmation = build_product_intent_confirmation(
                prompt=str(args.prompt),
                title=_intent_title(str(args.prompt)),
                repo_name=repo_root.name,
                observed_source=_source_evidence(repo_root),
            )
            if args.output_format == "json":
                print(json.dumps(confirmation, indent=2, sort_keys=True))
            else:
                print(format_product_intent_confirmation_text(confirmation), end="")
            return 0
        try:
            confirmed_intent = _load_confirmed_intent_args(args, repo_root=repo_root)
            proposal = build_greenfield_proposal(
                repo_root=repo_root,
                prompt=str(args.prompt),
                confirmed_intent=confirmed_intent,
            )
        except (ValueError, RuntimeError) as exc:
            _print_greenfield_error(exc, as_json=args.output_format == "json")
            return 2
        if args.output_format == "json":
            print(json.dumps(proposal, indent=2, sort_keys=True))
        else:
            print(format_proposal_text(proposal, detail=str(args.detail)), end="")
        return 0
    if args.command == "apply":
        try:
            proposal = _load_proposal(args)
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: apply_greenfield_proposal(
                    repo_root=repo_root,
                    proposal=proposal,
                    confirm=bool(args.confirm),
                    release_selector=str(args.release),
                    repair_tier=str(args.repair_tier),
                ),
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=bool(args.as_json))
            return 2
        if args.as_json:
            result = _with_operator_output(result, captured)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_apply_result(result, verb="apply")
        return 0
    if args.command == "create":
        if not bool(args.confirm):
            message = (
                "greenfield create requires --confirm after the Product Intent Confirmation is accepted. "
                "Run `odylith greenfield propose --repo-root . --prompt "
                + json.dumps(_prompt_text(str(args.prompt)))
                + "` first, then rerun create with --confirm when the interpretation is correct."
            )
            if args.as_json:
                print(json.dumps({"mode": "error", "error": message}, indent=2, sort_keys=True))
            else:
                print(message)
            return 2
        try:
            confirmed_intent = _load_confirmed_intent_args(args, repo_root=repo_root)
            proposal = build_greenfield_proposal(
                repo_root=repo_root,
                prompt=str(args.prompt),
                release_selector=str(args.release),
                confirmed_intent=confirmed_intent,
                require_completion_ready=False,
            )
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: apply_greenfield_proposal(
                    repo_root=repo_root,
                    proposal=proposal,
                    confirm=True,
                    release_selector=str(args.release),
                    proposal_ready=True,
                    repair_tier=str(args.repair_tier),
                ),
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            _print_greenfield_error(exc, as_json=bool(args.as_json))
            return 2
        if args.as_json:
            result = _with_operator_output(result, captured)
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print_apply_result(result, verb="create")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
