"""Host-reasoned greenfield governance contracts for consumer repos.

Odylith should not pretend a small built-in catalog can understand every
possible project the operator may ask for. This module gives host models a
strict evidence, schema, validation, and apply contract; the host model supplies
the open-world project reasoning, and Odylith validates and writes only after
explicit confirmation.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
import contextlib
import datetime as dt
import io
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.runtime.domain_intelligence import greenfield_component_registry_scope
from odylith.runtime.domain_intelligence import greenfield_experience
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_cli_output import print_apply_result
from odylith.runtime.domain_intelligence.greenfield_experience import proposal_posture_tuple
from odylith.runtime.domain_intelligence.greenfield_experience import row_text_tuple
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import PROJECT_INTELLIGENCE_SECTION_TITLE
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import render_project_intelligence_section
from odylith.runtime.domain_intelligence.greenfield_text import join_sentence_text
from odylith.runtime.domain_intelligence.greenfield_text import text_values
from odylith.runtime.domain_intelligence.greenfield_text import unique_text
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import SECTION_TITLE
from odylith.runtime.domain_intelligence.greenfield_workstream_intelligence import render_domain_intelligence_section
from odylith.runtime.domain_intelligence.proposal_contract import build_proposal_contract
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_normalization import normalize_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
from odylith.runtime.domain_intelligence.proposal_scaffold import build_apply_ready_proposal
from odylith.runtime.domain_intelligence.proposal_tribunal import raise_for_failed_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_tribunal import run_greenfield_tribunal
from odylith.runtime.domain_intelligence.proposal_validation import validate_host_reasoned_proposal
from odylith.runtime.domain_intelligence.proposal_validation import validated_mermaid_source
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.governance import release_planning_contract
from odylith.runtime.surfaces import scaffold_mermaid_diagram

def _prompt_text(prompt: str) -> str:
    text = " ".join(str(prompt or "").split()).strip()
    text = re.sub(r"^odylith[,:\s-]+", "", text, flags=re.IGNORECASE).strip()
    return text or "new project"


def _intent_title(prompt: str) -> str:
    text = _prompt_text(prompt)
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
    text = re.sub(r"\b(for me|please|with backlog.*|and diagrams.*|and atlas.*)$", "", text, flags=re.IGNORECASE).strip(" .")
    if not text or len(text) < 4:
        return "Greenfield Project"
    words = [_title_token(word) for word in text.split()]
    return " ".join(words[:10])


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


def _title_token(token: str) -> str:
    parts = str(token).split("-")
    rendered: list[str] = []
    for index, part in enumerate(parts):
        key = part.casefold()
        if key in _TITLE_ACRONYMS:
            rendered.append(_TITLE_ACRONYMS[key])
        elif index > 0 and part.islower():
            rendered.append(part)
        else:
            rendered.append(part[:1].upper() + part[1:] if part else part)
    return "-".join(rendered)


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


def build_greenfield_proposal(*, repo_root: Path, prompt: str) -> dict[str, Any]:
    """Return the greenfield reasoning envelope with a validated canonical proposal."""

    root = Path(repo_root).expanduser().resolve()
    intent_title = _intent_title(prompt)
    project_slug = slugify(intent_title)
    evidence = _source_evidence(root)
    canonical_proposal = _build_apply_ready_greenfield_proposal(
        repo_root=root,
        prompt=prompt,
        release_selector=greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR,
    )
    canonical_tribunal = run_greenfield_tribunal(
        canonical_proposal,
        release_selector=greenfield_programs.DEFAULT_GREENFIELD_RELEASE_SELECTOR,
    )
    proposal: dict[str, Any] = {
        "schema_version": "odylith.greenfield.reasoning_request.v1",
        "mode": "host_reasoned_proposal_request",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "host_reason_first_confirm_before_apply",
        "intent": {
            "prompt": _prompt_text(prompt),
            "title": intent_title,
            "project_slug": project_slug,
            "reasoning_mode": "host_model_required",
            "evidence_tier": "user_intent",
        },
        "classification": {
            "method": "open_world_host_reasoning",
            "fit_policy": "The host model must infer the project family, boundaries, topology, validation, and release shape from prompt plus repo evidence.",
            "provider_calls": 0,
        },
        "observed_source": evidence,
        "greenfield_ux": {
            "mode": "consumer_greenfield_host_reasoned_proposal",
            "source_posture": evidence.get("source_posture", "unknown"),
            "operator_sequence": [
                "Odylith builds canonical apply-ready proposal JSON from prompt and repo evidence",
                "operator reviews the project-first brief, direction options, assumptions, boundaries, diagrams, waves, and release plan",
                "Odylith validates and applies the confirmed proposal only after explicit confirmation",
                "implementation planning starts only after the project-first coding readiness gates are accepted",
                "or run the one-command create path when the built scaffold and readiness gates are enough",
            ],
            "write_guardrail": "This command does not write proposal records; the same validated canonical object is rendered for review and emitted by --format json.",
            "next_best_action": f"Review or deepen the project-first scaffold for {intent_title}, choose direction options, then confirm create/apply.",
        },
        "reasoning_contract": build_proposal_contract(),
        "proposal_template": canonical_proposal,
        "canonical_proposal": canonical_proposal,
        "canonical_proposal_gate": canonical_tribunal.to_dict(),
        "accepted_aliases": {
            "mode": ["greenfield", "host_reasoned_proposal"],
            "component_id": ["id", "name"],
            "kind": ["type"],
            "validation": ["proof_expectations", "test_strategy"],
            "recommended_first_slice": ["first_slice_proof"],
            "release_plan": ["list of release rows", "default_release plus releases"],
            "project_intelligence": ["project_control_surface", "project_domain_intelligence"],
        },
        "host_instruction": (
            "Draft a concrete proposal for the operator now. Be specific to the prompt; "
            "do not use canned domain buckets. Label observed_source, user_intent, "
            "and odylith_assumption separately. Ask only the questions that materially "
            "change the project direction, first slice, or correctness gates. Include project-first "
            "customization options that work the same from CLI, Codex, and Claude Code. For every child backlog item, "
            "include topology hints such as component_focus and related_diagram_slugs, "
            "plus first-slice validation. For every component, include enough boundary, "
            "responsibility, dependencies, interfaces, and validation expectations to seed "
            "a useful component CURRENT_SPEC.md. Default the provisional release selector "
            "and release label to exactly 0.0.1 unless the operator explicitly asks for another release target; "
            "do not add project names or descriptive words to release targets, "
            "and identify the first-wave workstreams that should target that release."
            " The confirmed proposal will run through deterministic validation "
            "before writes and will refresh project records after "
            "the accepted artifacts are written. Include a domain-appropriate security, "
            "privacy, compliance, abuse, accessibility, data retention, and operational "
            "risk posture; keep it proportional, specific, and host-model agnostic."
        ),
        "apply_commands": [
            "odylith greenfield create --repo-root . --prompt "
            + json.dumps(_prompt_text(prompt))
            + " --release 0.0.1 --confirm",
            "odylith greenfield propose --repo-root . --prompt "
            + json.dumps(_prompt_text(prompt))
            + " --format json > odylith-greenfield-proposal.json",
            "odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1",
        ],
    }
    return proposal


def _build_apply_ready_greenfield_proposal(
    *,
    repo_root: Path,
    prompt: str,
    release_selector: str = "",
) -> dict[str, Any]:
    root = Path(repo_root).expanduser().resolve()
    raw = build_apply_ready_proposal(
        prompt=_prompt_text(prompt),
        intent_title=_intent_title(prompt),
        project_slug=slugify(_intent_title(prompt)),
        observed_source=_source_evidence(root),
        release_selector=release_selector,
    )
    normalized = normalize_host_reasoned_proposal(raw)
    validate_host_reasoned_proposal(normalized)
    tribunal = run_greenfield_tribunal(
        normalized,
        release_selector=greenfield_programs.proposal_release_selector(normalized, release_selector),
    )
    raise_for_failed_greenfield_tribunal(tribunal)
    return normalized


def _load_proposal(args: argparse.Namespace) -> dict[str, Any]:
    if str(getattr(args, "proposal_file", "") or "").strip():
        path = Path(str(args.proposal_file)).expanduser().resolve()
        return json.loads(path.read_text(encoding="utf-8"))
    raw = str(getattr(args, "proposal_json", "") or "").strip()
    if raw:
        return json.loads(raw)
    raise ValueError("provide --proposal-file or --proposal-json")


def _next_diagram_id(repo_root: Path) -> str:
    catalog = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    max_id = 0
    if catalog.is_file():
        try:
            payload = json.loads(catalog.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = {}
        for row in payload.get("diagrams", []) if isinstance(payload, Mapping) else []:
            match = re.fullmatch(r"D-(\d{3,})", str(row.get("diagram_id", "")).strip())
            if match:
                max_id = max(max_id, int(match.group(1)))
    return f"D-{max_id + 1:03d}"


def _allocated_diagram_ids(repo_root: Path, count: int) -> list[str]:
    first = int(_next_diagram_id(repo_root).split("-", 1)[1])
    return [f"D-{value:03d}" for value in range(first, first + max(0, count))]


def _proposal_posture_text(proposal: Mapping[str, Any], *keys: str) -> str:
    return " ".join(proposal_posture_tuple(proposal, *keys)).strip()


def _row_posture_text(row: Mapping[str, Any], proposal: Mapping[str, Any], *keys: str) -> str:
    local = row_text_tuple(row, *keys)
    if local:
        return " ".join(local).strip()
    return _proposal_posture_text(proposal, *keys)


def _domain_risk_for_row(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    return (
        _row_posture_text(row, proposal, "domain_risk", "risk_posture", "risks")
        or _proposal_posture_text(proposal, "risks", "security_compliance")
    )


def _security_posture_for_row(row: Mapping[str, Any], proposal: Mapping[str, Any]) -> str:
    return (
        _row_posture_text(row, proposal, "security_posture", "security_compliance", "compliance_posture")
        or _proposal_posture_text(proposal, "security_compliance")
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
            "domain_risk": _domain_risk_for_row(row, proposal),
            "security_posture": _security_posture_for_row(row, proposal),
            "priority": str(row.get("priority", "P1")).strip() or "P1",
            "sizing": str(row.get("sizing", "M")).strip() or "M",
            "complexity": str(row.get("complexity", "Medium")).strip() or "Medium",
            "ordering_rationale": "Created from a confirmed Odylith greenfield proposal.",
        }
        extra_sections: dict[str, str] = {}
        if title == parent_title:
            project_intelligence = render_project_intelligence_section(proposal.get("project_intelligence"))
            if project_intelligence:
                extra_sections[PROJECT_INTELLIGENCE_SECTION_TITLE] = project_intelligence
        domain_intelligence = render_domain_intelligence_section(row.get("domain_intelligence"))
        if domain_intelligence:
            extra_sections[SECTION_TITLE] = domain_intelligence
        if extra_sections:
            override["extra_sections"] = extra_sections
        overrides[title] = override
        overrides[slugify(title)] = override
    return overrides


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
        domain_risk=_domain_risk_for_row(first, proposal),
        security_posture=_security_posture_for_row(first, proposal),
        priority=str(first.get("priority", "P1")).strip() or "P1",
        commercial_value=3,
        product_impact=4,
        market_value=3,
        impacted_parts="application,registry,atlas,radar",
        sizing=str(first.get("sizing", "M")).strip() or "M",
        complexity=str(first.get("complexity", "Medium")).strip() or "Medium",
        ordering_score=None,
        ordering_rationale="Created from a confirmed Odylith greenfield proposal.",
        confidence="medium",
        founder_override=False,
        override_note="",
        override_review_date="",
        release=release_selector,
        section_overrides_by_title=_backlog_section_overrides(proposal),
    )


def _release_assignment_note(*, selector: str) -> str:
    return f"Target confirmed first-wave greenfield workstream(s) from `odylith greenfield apply --release {selector}`."


def _component_risk_lines(row: Mapping[str, Any], _proposal: Mapping[str, Any]) -> tuple[str, ...]:
    local = unique_text(
        [
            *_posture_lines(row, "risks", "domain_risk", "risk_posture"),
            *_posture_lines(row, "security_posture", "security_compliance", "compliance_posture"),
            *_posture_lines(row, "dependency_expectations"),
        ]
    )
    label = str(row.get("label", "") or row.get("component_id", "") or "Component").strip()
    values = list(local)
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_RISK_TOKENS):
        values.append(_component_operational_risk(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_SECURITY_TOKENS):
        values.append(_component_security_posture(row=row, label=label))
    posture_text = _component_posture_text(row=row, risk_lines=values)
    if not _has_component_posture(posture_text, _COMPONENT_POLICY_TOKENS):
        values.append(_component_policy_posture(row=row, label=label))
    return unique_text(values)


def _component_posture_text(*, row: Mapping[str, Any], risk_lines: Sequence[str]) -> str:
    values = [
        *risk_lines,
        *row_text_tuple(row, "responsibility"),
        *row_text_tuple(row, "boundary"),
        *row_text_tuple(row, "dependencies", "depends_on"),
        *row_text_tuple(row, "interfaces", "interface_changes"),
        *row_text_tuple(row, "validation", "test_strategy"),
    ]
    return " ".join(values).casefold()


def _has_component_posture(text: str, tokens: Sequence[str]) -> bool:
    return any(token in text for token in tokens)


def _component_operational_risk(*, row: Mapping[str, Any], label: str) -> str:
    boundary = str(row.get("boundary", "") or row.get("responsibility", "")).strip()
    boundary_hint = f" its stated boundary ({boundary})" if boundary else " its stated component boundary"
    return f"Operational risk: {label} must not expand beyond{boundary_hint} without a refreshed component spec and source-backed proof."


def _component_security_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Security posture: {label} uses secret-free fixtures, rejects production credentials, "
            "and keeps live network access outside its proof boundary."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Security posture: {label} gates operator access and audit identity at its own visible action boundary."
        )
    return (
        f"Security posture: {label} keeps authorization, data access, and ownership checks at its API or module boundary."
    )


def _component_policy_posture(*, row: Mapping[str, Any], label: str) -> str:
    kind = str(row.get("kind", "")).strip().casefold()
    if kind in {"tooling", "test", "harness"}:
        return (
            f"Compliance policy: {label} records deterministic audit evidence and rejects private production data in fixtures."
        )
    if kind in {"application", "ui", "frontend", "web"}:
        return (
            f"Policy posture: {label} preserves accessibility, privacy, audit, and safety semantics for the visible states it owns."
        )
    return (
        f"Compliance policy: {label} keeps audit, privacy, retention, and safety assumptions explicit in its contract tests."
    )


def _posture_lines(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    lines: list[str] = []
    for key in keys:
        lines.extend(_posture_value_lines(row.get(key)))
    return unique_text(lines)


def _posture_value_lines(value: Any) -> tuple[str, ...]:
    if isinstance(value, Mapping):
        if "statement" not in value and "mitigation" not in value:
            ignored = {"id", "evidence_tier", "kind"}
            return unique_text(
                line
                for nested_key, nested_value in value.items()
                if str(nested_key) not in ignored
                for line in _posture_value_lines(nested_value)
            )
        statement = join_sentence_text(
            value.get("statement")
            or value.get("risk")
            or value.get("detail")
            or value.get("domain")
            or value.get("security")
            or value.get("policy")
            or value.get("compliance")
        )
        mitigation = join_sentence_text(value.get("mitigation"))
        if statement and mitigation:
            return (f"{statement} Mitigation: {mitigation}",)
        if statement:
            return (statement,)
        ignored = {"id", "evidence_tier", "kind"}
        return unique_text(
            line
            for nested_key, nested_value in value.items()
            if str(nested_key) not in ignored
            for line in _posture_value_lines(nested_value)
        )
    if isinstance(value, (list, tuple, set)):
        return unique_text(line for nested in value for line in _posture_value_lines(nested))
    return text_values(value)


def _release_id_for_proposal(proposal: Mapping[str, Any], *, selector: str) -> str:
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_id = str(release_plan.get("provisional_release_id", "")).strip()
    if release_id:
        return slugify(release_id)
    if selector:
        return slugify(f"release-{selector}")
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    project_slug = slugify(str(intent.get("project_slug", "")).strip() or str(intent.get("title", "")).strip())
    return slugify(f"release-{project_slug}-first") if project_slug else "release-greenfield-first"


def _ensure_release_target(*, repo_root: Path, proposal: Mapping[str, Any], selector: str) -> dict[str, Any]:
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip() or "Greenfield Project"
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    version, tag = greenfield_programs.semver_release_metadata(selector=selector, release_plan=release_plan)
    registry_path = release_planning_contract.releases_registry_path(repo_root=repo_root)
    registry_document, _errors = release_planning_contract.load_registry_document(path=registry_path)
    aliases = dict(registry_document.get("aliases", {})) if isinstance(registry_document.get("aliases"), Mapping) else {}
    release_aliases = [selector]
    if release_planning_contract.canonical_alias_token("current") not in aliases:
        release_aliases.append("current")
    release_name = greenfield_programs.compact_release_target_label(version or selector)
    return release_planning_authoring.ensure_release_selector(
        repo_root=repo_root,
        selector=selector,
        release_id=_release_id_for_proposal(proposal, selector=selector),
        status="planning",
        version=version,
        tag=tag,
        name=release_name,
        notes=f"Greenfield release plan for {title}; created only after proposal confirmation.",
        aliases=tuple(release_aliases),
        dry_run=False,
    )


_GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass")
_COMPONENT_RISK_TOKENS = ("risk", "failure", "fallback", "mitigation", "recovery", "degraded", "operational")
_COMPONENT_SECURITY_TOKENS = (
    "security",
    "auth",
    "authorization",
    "credential",
    "permission",
    "session",
    "secret",
    "token",
    "access",
    "ownership",
    "private",
    "abuse",
    "payment",
    "pii",
    "data risk",
)
_COMPONENT_POLICY_TOKENS = (
    "compliance",
    "policy",
    "privacy",
    "retention",
    "audit",
    "regulated",
    "accessibility",
    "public",
    "private",
    "safety",
)


def _refresh_greenfield_dashboard(*, repo_root: Path) -> dict[str, Any]:
    owned_surface_refresh.raise_for_failed_refreshes(
        repo_root=repo_root,
        surfaces=_GREENFIELD_VISIBLE_SURFACES,
        operation_label="Greenfield apply dashboard visibility",
    )
    return {
        "status": "passed",
        "surfaces": list(_GREENFIELD_VISIBLE_SURFACES),
        "view": owned_surface_refresh.dashboard_handoff(surface="compass"),
    }


def apply_greenfield_proposal(
    *,
    repo_root: Path,
    proposal: Mapping[str, Any],
    confirm: bool,
    release_selector: str = "",
) -> dict[str, Any]:
    """Apply a confirmed proposal using owned governance authoring paths."""

    if not confirm:
        raise ValueError("--confirm is required before greenfield apply writes governance records")
    proposal = normalize_host_reasoned_proposal(proposal)
    validate_host_reasoned_proposal(proposal)
    root = Path(repo_root).expanduser().resolve()
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    if not backlog_rows:
        raise ValueError("proposal has no backlog records")
    release_selector = greenfield_programs.proposal_release_selector(proposal, release_selector)
    tribunal = run_greenfield_tribunal(proposal, release_selector=release_selector)
    raise_for_failed_greenfield_tribunal(tribunal)
    backlog_args = _backlog_apply_args(proposal, release_selector=release_selector)
    backlog_result = backlog_authoring.create_queued_backlog_items(
        repo_root=root,
        backlog_index_path=root / "odylith/radar/source/INDEX.md",
        ideas_root=root / "odylith/radar/source/ideas",
        titles=[str(row.get("title", "")).strip() for row in backlog_rows if str(row.get("title", "")).strip()],
        args=backlog_args,
    )
    with GreenfieldApplyTransaction(root) as transaction:
        result = _write_greenfield_proposal(
            root=root,
            proposal=proposal,
            release_selector=release_selector,
            tribunal=tribunal,
            backlog_result=backlog_result,
        )
        transaction.commit()
        return result


def _scaffold_proposal_diagram(
    *,
    root: Path,
    row: Mapping[str, Any],
    diagram_id: str,
    traceability_plan: Any,
    atlas_scaffold_logs: list[str],
) -> None:
    components: list[dict[str, str]] = []
    for component in row.get("components", []):
        if not isinstance(component, Mapping):
            continue
        name = str(component.get("name", "")).strip()
        description = str(component.get("description", "")).strip()
        if name and description:
            components.append({"name": name, "description": description})
    link = next((item for item in traceability_plan.diagram_links if item.diagram_id == diagram_id), None)
    related_backlog = list(link.related_backlog_paths) if link is not None else []
    watch_paths: list[str] = []
    for path in row.get("watch_paths", []):
        token = str(path).strip()
        if not token:
            continue
        candidate = (root / token).resolve() if not Path(token).is_absolute() else Path(token).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            watch_paths.append(token)
    rc, log_lines = scaffold_mermaid_diagram.scaffold_diagram(
        repo_root=root,
        catalog="odylith/atlas/source/catalog/diagrams.v1.json",
        diagram_id=diagram_id,
        slug=str(row.get("slug", "")).strip(),
        title=str(row.get("title", "")).strip(),
        kind=str(row.get("kind", "flowchart")).strip() or "flowchart",
        owner=str(row.get("owner", "repo")).strip() or "repo",
        summary=str(row.get("summary", "")).strip(),
        components=components,
        related_backlog=related_backlog,
        related_plans=[],
        related_docs=[],
        related_code=[],
        watch_paths=watch_paths,
        review_date=dt.date.today().isoformat(),
        starter_source=validated_mermaid_source(row),
        refresh=False,
    )
    log_text = "\n".join(log_lines).strip()
    if log_text:
        atlas_scaffold_logs.append(log_text)
    if rc != 0:
        detail = f": {log_text}" if log_text else ""
        raise RuntimeError(f"atlas scaffold failed for {row.get('slug')}{detail}")
    _update_scaffolded_diagram_link_state(
        root=root,
        slug=str(row.get("slug", "")).strip(),
        link_state=str(row.get("link_state", "")).strip(),
    )


def _update_scaffolded_diagram_link_state(*, root: Path, slug: str, link_state: str) -> None:
    if not slug or not link_state:
        return
    catalog_path = root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not catalog_path.is_file():
        return
    try:
        payload = json.loads(catalog_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return
    diagrams = payload.get("diagrams") if isinstance(payload, Mapping) else None
    if not isinstance(diagrams, list):
        return
    changed = False
    for item in diagrams:
        if not isinstance(item, dict):
            continue
        if str(item.get("slug", "")).strip() != slug:
            continue
        if str(item.get("link_state", "")).strip() != link_state:
            item["link_state"] = link_state
            changed = True
    if changed:
        catalog_path.write_text(f"{json.dumps(payload, indent=2)}\n", encoding="utf-8")


def _write_greenfield_proposal(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    tribunal: Any,
    backlog_result: Mapping[str, Any],
) -> dict[str, Any]:
    release_bootstrap = None
    release_targeting = None
    if release_selector:
        release_bootstrap = _ensure_release_target(repo_root=root, proposal=proposal, selector=release_selector)
    for raw_path, text in backlog_result["idea_files"].items():
        Path(raw_path).write_text(str(text), encoding="utf-8")
    Path(backlog_result["backlog_index"]).write_text(str(backlog_result["backlog_index_text"]), encoding="utf-8")
    program_result = greenfield_programs.create_greenfield_program(
        repo_root=root,
        proposal=proposal,
        backlog_result=backlog_result,
    )
    first_release_workstreams = greenfield_programs.first_release_workstream_ids(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        program_result=program_result,
    )
    if release_selector:
        release_targeting = release_planning_authoring.add_workstreams_to_release(
            repo_root=root,
            workstream_ids=first_release_workstreams,
            selector=release_selector,
            note=_release_assignment_note(selector=release_selector),
            idea_specs=backlog_result["_candidate_idea_specs"],
            dry_run=False,
        )
        if isinstance(release_targeting, dict) and isinstance(release_targeting.get("release"), Mapping):
            release_targeting.setdefault("release_id", str(release_targeting["release"].get("release_id", "")).strip())
    diagrams_created: list[str] = []
    atlas_scaffold_logs: list[str] = []
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, Mapping)]
    diagram_ids = _allocated_diagram_ids(root, len(diagram_rows))
    traceability_plan = greenfield_traceability.build_traceability_plan(
        proposal=proposal,
        created_backlog=backlog_result["created"],
        diagram_ids=diagram_ids,
    )
    for row, diagram_id in zip(diagram_rows, diagram_ids, strict=False):
        _scaffold_proposal_diagram(
            root=root,
            row=row,
            diagram_id=diagram_id,
            traceability_plan=traceability_plan,
            atlas_scaffold_logs=atlas_scaffold_logs,
        )
        diagrams_created.append(diagram_id)
    touched_backlog_paths = greenfield_traceability.apply_backlog_traceability(
        repo_root=root,
        proposal=proposal,
        plan=traceability_plan,
    )
    component_handoffs = greenfield_experience.build_component_handoffs(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        traceability_plan=traceability_plan,
        release_selector=release_selector,
    )
    component_diagram_scope = greenfield_component_registry_scope.build_component_diagram_scope(
        rows=diagram_rows,
        diagram_ids=diagram_ids,
    )

    components_created: list[dict[str, Any]] = []
    for row in proposal.get("components", []):
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
        handoff = component_handoffs.get(key, {})
        created = component_authoring.register_component(
            repo_root=root,
            component_id=str(row.get("component_id", "")).strip(),
            label=str(row.get("label", "")).strip(),
            path=str(row.get("intended_path", "")).strip(),
            kind=str(row.get("kind", "service")).strip() or "service",
            category="application",
            qualification=str(row.get("qualification", "candidate")).strip() or "candidate",
            owner="repo",
            status=str(row.get("status", "planned")).strip() or "planned",
            product_layer="application",
            sources=("user_intent",),
            workstreams=greenfield_component_registry_scope.registry_component_workstreams(
                handoff=handoff,
                fallback=traceability_plan.component_workstreams.get(key, ()),
            ),
            diagrams=greenfield_component_registry_scope.registry_component_diagrams(
                row=row,
                diagram_scope=component_diagram_scope,
                fallback=traceability_plan.component_diagrams.get(key, ()),
            ),
            responsibility=str(row.get("responsibility", "")).strip(),
            boundary=str(row.get("boundary", "")).strip(),
            dependencies=row_text_tuple(row, "dependencies", "depends_on"),
            interfaces=row_text_tuple(row, "interfaces", "interface_changes"),
            validation=row_text_tuple(row, "validation", "test_strategy"),
            risks=_component_risk_lines(row, proposal),
            implementation_handoff=handoff,
            dry_run=False,
            refresh=False,
        )
        components_created.append(created.as_dict())

    release_id = "none"
    if isinstance(release_targeting, Mapping):
        release_id = str(release_targeting.get("release_id", "")).strip() or "none"
    memory_record = record_greenfield_acceptance(
        repo_root=root,
        proposal=proposal,
        backlog_items=backlog_result["created"],
        component_items=components_created,
        diagram_ids=diagrams_created,
        release_selector=release_selector,
        release_id=release_id,
    )
    dashboard_refresh = _refresh_greenfield_dashboard(repo_root=root)
    next_steps = greenfield_experience.build_next_steps(
        proposal=proposal,
        backlog_result=backlog_result,
        first_release_workstreams=first_release_workstreams,
        program_result=program_result,
        release_selector=release_selector,
    )

    return {
        "mode": "applied",
        "tribunal": tribunal.to_dict(),
        "backlog": backlog_result["created"],
        "components": components_created,
        "diagrams": diagrams_created,
        "program": program_result,
        "backlog_topology": touched_backlog_paths,
        "atlas_scaffold_logs": atlas_scaffold_logs,
        "memory": memory_record,
        "dashboard_refresh": dashboard_refresh,
        "next_steps": next_steps,
        "release_bootstrap": release_bootstrap or {"created": False, "release": {}},
        "release_target": release_targeting or {"selector": release_selector, "release_id": "none", "events": []},
    }


def _parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="odylith greenfield", description="Draft and apply greenfield governance proposals.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    propose = subparsers.add_parser("propose", help="Draft a confirmation-gated greenfield proposal.")
    propose.add_argument("--repo-root", default=".")
    propose.add_argument("--prompt", required=True)
    propose.add_argument("--format", choices=("text", "json"), default="text", dest="output_format")
    apply = subparsers.add_parser("apply", help="Apply a confirmed greenfield proposal.")
    apply.add_argument("--repo-root", default=".")
    apply.add_argument("--proposal-file", default="")
    apply.add_argument("--proposal-json", default="")
    apply.add_argument("--confirm", action="store_true")
    apply.add_argument("--release", default="")
    apply.add_argument("--json", action="store_true", dest="as_json")
    create = subparsers.add_parser("create", help="Build and apply an Odylith-owned greenfield proposal in one confirmed command.")
    create.add_argument("--repo-root", default=".")
    create.add_argument("--prompt", required=True)
    create.add_argument("--confirm", action="store_true")
    create.add_argument("--release", default="")
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
        print(json.dumps({"mode": "error", "error": str(exc)}, indent=2, sort_keys=True))
        return
    print(str(exc))


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        proposal = build_greenfield_proposal(repo_root=repo_root, prompt=str(args.prompt))
        if args.output_format == "json":
            canonical = proposal.get("canonical_proposal") if isinstance(proposal.get("canonical_proposal"), Mapping) else proposal
            print(json.dumps(canonical, indent=2, sort_keys=True))
        else:
            print(format_proposal_text(proposal), end="")
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
        try:
            result, captured = _run_with_optional_stdout_capture(
                enabled=bool(args.as_json),
                action=lambda: apply_greenfield_proposal(
                    repo_root=repo_root,
                    proposal=_build_apply_ready_greenfield_proposal(
                        repo_root=repo_root,
                        prompt=str(args.prompt),
                        release_selector=str(args.release),
                    ),
                    confirm=bool(args.confirm),
                    release_selector=str(args.release),
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
