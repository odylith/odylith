"""Confirmed greenfield governance contracts for consumer repos.

Odylith should not pretend a small built-in catalog can understand every
possible project the operator may ask for. This module keeps the no-write
Product Intent Confirmation separate from the confirmed create path, then
builds, repairs, validates, gates, and writes the governed proposal without
pushing internal normalization or repair work back onto the host.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_completion import complete_confirmed_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_proposal import build_confirmed_greenfield_proposal
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import load_confirmed_intent_record
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence import greenfield_apply_prewrite
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_create_commit
from odylith.runtime.domain_intelligence import greenfield_prewrite_projection_rerender
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence.artifact_enrichment import build_artifact_enrichment
from odylith.runtime.domain_intelligence.greenfield_backlog_impact import derive_greenfield_impacted_parts
from odylith.runtime.domain_intelligence.greenfield_create_transaction import ProductCreateTransaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import build_product_create_transaction
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_from_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import product_create_transaction_to_dict
from odylith.runtime.domain_intelligence.greenfield_create_transaction import require_product_create_transaction_verified
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    product_intent_authority_from_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import require_product_intent_authority
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import domain_risk_for_row
from odylith.runtime.domain_intelligence.greenfield_workstream_risk_projection import proposal_posture_text
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
from odylith.runtime.domain_intelligence.proposal_tribunal import raise_for_failed_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import assert_greenfield_completion_ready
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmRepairContext,
)
from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    POST_CONFIRM_MAX_PASSES,
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


def prompt_text(prompt: str) -> str:
    text = " ".join(str(prompt or "").split()).strip()
    text = re.sub(r"^odylith[,:\s-]+", "", text, flags=re.IGNORECASE).strip()
    return text or "new project"


def intent_title(prompt: str) -> str:
    text = prompt_text(prompt)
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
DEFAULT_POST_CONFIRM_REPAIR_TIER = _DEFAULT_POST_CONFIRM_REPAIR_TIER


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


def source_evidence(repo_root: Path) -> dict[str, Any]:
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


def _accepted_intent_shaping_prompt(confirmed_intent: Mapping[str, Any], *, fallback_title: str) -> str:
    """Return proposal-shaping text from accepted intent facts only."""

    rows: list[str] = []
    for key, label in (
        ("title", "Product"),
        ("product_story", "Product story"),
        ("state_object", "State object"),
        ("first_path", "First complete path"),
        ("proof_boundary", "Proof boundary"),
        ("problem", "Problem"),
        ("customer", "Customer"),
        ("opportunity", "Opportunity"),
        ("product_view", "Product view"),
    ):
        value = " ".join(str(confirmed_intent.get(key) or "").split()).strip()
        if value:
            rows.append(f"{label}: {value}")
    for key, label in (
        ("human_actors", "Human actors"),
        ("external_systems", "External systems"),
        ("internal_systems", "Internal product systems"),
        ("assumptions", "Critical assumptions"),
        ("non_goals", "Non-goals"),
        ("success_metrics", "Success metrics"),
        ("evidence_requirements", "Evidence requirements"),
    ):
        values = confirmed_intent.get(key)
        if isinstance(values, Sequence) and not isinstance(values, (str, bytes)):
            text = "; ".join(" ".join(str(item).split()).strip() for item in values if str(item).strip())
            if text:
                rows.append(f"{label}: {text}")
    return ". ".join(rows).strip() or fallback_title


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
    intent_prompt = _accepted_intent_shaping_prompt(confirmed_intent, fallback_title=intent_title)
    intent_authority = confirmed_intent.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent_authority, Mapping):
        raise ValueError("confirmed Product Intent authority is missing; rebuild from a typed custody envelope")
    intent_authority = dict(intent_authority)
    require_product_intent_authority(intent_authority)
    evidence = _confirmed_intent_source_evidence(root)
    proposal = build_confirmed_greenfield_proposal(
        prompt=intent_prompt,
        title=intent_title,
        observed_source=evidence,
        release_selector=release_selector,
        confirmed_intent=confirmed_intent,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    proposal = complete_confirmed_proposal(proposal, release_selector=release_selector)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    proposal = display_text.strip_inline_markdown_emphasis_tree(normalize_host_reasoned_proposal(proposal))
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    proposal = complete_greenfield_semantic_apply_payload(proposal, release_selector=release_selector)
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
    validate_host_reasoned_proposal(proposal)
    selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    raise_for_failed_greenfield_tribunal(run_greenfield_tribunal(proposal, release_selector=selector))
    if require_completion_ready:
        assert_greenfield_completion_ready(proposal, release_selector=selector)
    return proposal


def load_proposal(args: argparse.Namespace) -> dict[str, Any]:
    if str(getattr(args, "proposal_file", "") or "").strip():
        path = Path(str(args.proposal_file)).expanduser().resolve()
        return json.loads(path.read_text(encoding="utf-8"))
    raw = str(getattr(args, "proposal_json", "") or "").strip()
    if raw:
        return json.loads(raw)
    raise ValueError("provide --proposal-file or --proposal-json")


def load_confirmed_intent_args(args: argparse.Namespace, *, repo_root: Path) -> dict[str, Any]:
    intent_file = str(getattr(args, "intent_file", "") or "").strip()
    if not intent_file:
        raise ValueError(
            "confirmed Product Intent file is required before proposal preview or ProductCreateTransaction compile. "
            "Run `odylith greenfield propose --repo-root . --prompt <request>`, save the accepted visible "
            "Product Intent Confirmation to `.odylith/runtime/greenfield/confirmed-intent.md`, then rerun "
            "`odylith greenfield compile-transaction --intent-file .odylith/runtime/greenfield/confirmed-intent.md`. "
            "Prompt-only transaction compilation is disabled so raw prompts cannot become product truth after confirmation."
        )
    path = Path(intent_file).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    record = load_confirmed_intent_record(
        path,
        prompt=str(getattr(args, "prompt", "") or ""),
        fallback_title=intent_title(str(getattr(args, "prompt", "") or "")),
    )
    structured_path = write_structured_confirmed_intent_file(path, record.product_facts, envelope=record.envelope)
    markdown_path = _confirmed_intent_markdown_source_path(record.envelope, fallback=path)
    authority = product_intent_authority_from_envelope(
        record.envelope,
        structured_intent_path=structured_path,
        markdown_source_path=markdown_path,
    )
    require_product_intent_authority(authority)
    intent = dict(record.product_facts)
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = authority
    return intent

def _confirmed_intent_markdown_source_path(envelope: Mapping[str, Any], *, fallback: Path) -> Path:
    source_evidence = envelope.get("source_evidence") if isinstance(envelope.get("source_evidence"), Mapping) else {}
    source_path = str(source_evidence.get("source_path", "")).strip()
    if not source_path:
        return fallback
    candidate = Path(source_path).expanduser()
    return candidate if candidate.is_absolute() else fallback.parent / candidate


def load_product_create_transaction_args(
    args: argparse.Namespace,
    *,
    repo_root: Path,
) -> ProductCreateTransaction | None:
    transaction_file = str(getattr(args, "transaction_file", "") or "").strip()
    if not transaction_file:
        return None
    path = Path(transaction_file).expanduser()
    if not path.is_absolute():
        path = repo_root / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    transaction = product_create_transaction_from_dict(payload)
    expected_hash = str(getattr(args, "transaction_hash", "") or "").strip()
    if not expected_hash:
        raise ValueError("greenfield create with a ProductCreateTransaction requires --transaction-hash")
    if expected_hash != transaction.transaction_hash:
        raise ValueError("ProductCreateTransaction hash does not match --transaction-hash")
    return transaction


def write_product_create_transaction_file(path: Path, transaction: ProductCreateTransaction) -> Path:
    target = Path(path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = product_create_transaction_to_dict(transaction)
    atomic_write_text(target, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


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


def compile_greenfield_create_transaction(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    proposal_ready: bool = False,
    repair_tier: str = _DEFAULT_POST_CONFIRM_REPAIR_TIER,
) -> ProductCreateTransaction:
    """Compile and quality-gate the complete create package before commit."""

    root = Path(repo_root).expanduser().resolve()
    release_selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    intent_authority = proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)
    if not isinstance(intent_authority, Mapping):
        raise ValueError("ProductCreateTransaction is missing confirmed Product Intent authority")
    intent_authority = dict(intent_authority)
    require_product_intent_authority(intent_authority)
    proposal, tribunal, prewrite_build, quality_manifest = _build_repaired_prewrite_package(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        proposal_ready=proposal_ready,
        repair_tier=repair_tier,
    )
    package_proposal = prewrite_build.package.proposal
    if isinstance(package_proposal, Mapping):
        proposal = dict(package_proposal)
        proposal[PRODUCT_INTENT_AUTHORITY_KEY] = intent_authority
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
    proposal_ready: bool = True,
    repair_tier: str = _DEFAULT_POST_CONFIRM_REPAIR_TIER,
) -> dict[str, Any]:
    """Reject the removed post-confirm proposal-apply path."""

    if not confirm:
        raise ValueError("--confirm is required before greenfield apply writes accepted product records")
    _ = (repo_root, proposal, release_selector, proposal_ready, repair_tier)
    raise ValueError(
        "greenfield apply is disabled for confirmed writes. "
        "Run greenfield compile-transaction before confirmation, then commit the verified "
        "ProductCreateTransaction with greenfield create --transaction-file --transaction-hash --confirm."
    )

def main(argv: Sequence[str] | None = None) -> int:
    from odylith.runtime.domain_intelligence.greenfield_proposals_cli import main as _main

    return _main(argv)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
