"""Deterministic greenfield governance proposals for consumer repos.

This module turns user-stated project intent into confirmation-gated Radar,
Registry, and Atlas drafts. It deliberately separates observed repository
evidence from user intent and Odylith assumptions so empty consumer repos can
receive useful guidance without fabricated source evidence.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.runtime.domain_intelligence.archetypes import Archetype
from odylith.runtime.domain_intelligence.archetypes import ComponentBlueprint
from odylith.runtime.domain_intelligence.archetypes import catalog_metadata
from odylith.runtime.domain_intelligence.archetypes import rank_archetypes
from odylith.runtime.domain_intelligence.proposal_planning import build_greenfield_ux
from odylith.runtime.domain_intelligence.proposal_planning import build_program_blueprint
from odylith.runtime.domain_intelligence.proposal_planning import build_program_waves
from odylith.runtime.domain_intelligence.proposal_planning import build_release_plan
from odylith.runtime.domain_intelligence.proposal_planning import first_slice_validation_instruction
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_rendering import build_apply_commands
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import component_authoring
from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.governance import release_planning_authoring
from odylith.runtime.surfaces import scaffold_mermaid_diagram


_RESEARCH_ARCHETYPE_IDS = {
    "science_math",
    "formal_proof",
    "computational_notebook",
    "simulation_modeling",
    "scientific_pipeline",
    "geospatial_environmental",
    "ml_experiment_platform",
}


def _prompt_text(prompt: str) -> str:
    text = " ".join(str(prompt or "").split()).strip()
    text = re.sub(r"^odylith[,:\s-]+", "", text, flags=re.IGNORECASE).strip()
    return text or "new project"


def _intent_title(prompt: str, archetype: Archetype) -> str:
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
        return archetype.label
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


def _complexity(prompt: str) -> str:
    text = _prompt_text(prompt).casefold()
    if any(token in text for token in ("simple", "tiny", "small", "single page", "minimal")):
        return "simple"
    if any(token in text for token in ("complex", "enterprise", "platform", "multi-service", "marketplace", "research", "simulation")):
        return "complex"
    return "medium"


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


def _component_path(project_slug: str, blueprint: ComponentBlueprint) -> str:
    suffix = blueprint.path_suffix.strip("/")
    repo_roots = ("apps/", "src/", "tests/", "docs/", "data/", "notebooks", "reports", "env", "reproducibility")
    if suffix.startswith(repo_roots):
        return suffix
    return f"src/{project_slug}/{suffix}".strip("/")


def _component_drafts(project_slug: str, archetype: Archetype, complexity: str) -> list[dict[str, Any]]:
    limit = 4 if complexity == "simple" else 5 if complexity == "medium" else len(archetype.components)
    rows: list[dict[str, Any]] = []
    for blueprint in archetype.components[:limit]:
        component_id = slugify(f"{project_slug}-{blueprint.component_id}")
        rows.append(
            {
                "component_id": component_id,
                "label": blueprint.label,
                "kind": blueprint.kind,
                "intended_path": _component_path(project_slug, blueprint),
                "responsibility": blueprint.responsibility,
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            }
        )
    return rows


def _workstream_drafts(intent_title: str, archetype: Archetype, components: Sequence[Mapping[str, Any]], complexity: str) -> list[dict[str, Any]]:
    parent_title = f"Govern {intent_title}"
    component_labels = [str(row.get("label", "")).strip() for row in components if str(row.get("label", "")).strip()]
    first_slice = component_labels[0] if component_labels else archetype.label
    first_slice_proof = first_slice_validation_instruction(archetype)
    problem = (
        f"The repo has a user-stated intent to build {intent_title}, but no confirmed governance plan yet. "
        "Without a first proposal, backlog, component ownership, and topology would be invented ad hoc by later sessions."
    )
    customer = "Product builders, maintainers, and future agent sessions that need a shared project map before implementation."
    opportunity = (
        f"Create a confirmation-gated Odylith proposal for {intent_title} so delivery can start with explicit "
        "workstreams, planned components, draft topology, assumptions, and validation obligations."
    )
    product_view = (
        f"Odylith should hand-hold the operator with a concrete {archetype.label.lower()} proposal while labeling "
        "every assumption and preserving the difference between user intent and observed source evidence."
    )
    metrics = [
        "A parent workstream records the project intent and the first implementation slice.",
        "Planned Registry components carry intended paths and user-intent evidence only.",
        "Atlas contains draft topology before implementation starts.",
        "Open assumptions are captured so future sessions can refine instead of re-asking from scratch.",
    ]
    rows = [
        {
            "title": parent_title,
            "problem": problem,
            "customer": customer,
            "opportunity": opportunity,
            "product_view": product_view,
            "success_metrics": metrics,
            "priority": "P1",
            "sizing": "L" if complexity == "complex" else "M",
            "complexity": "High" if complexity == "complex" else "Medium",
            "recommended_first_slice": f"Start with {first_slice} and {first_slice_proof}.",
            "evidence_tier": "user_intent",
        }
    ]
    if complexity != "simple":
        child_limit = 5 if complexity == "complex" else 3
        for label in component_labels[:child_limit]:
            rows.append(
                {
                    "title": f"Define {label} boundary",
                    "problem": f"{label} needs a named ownership boundary before implementation work fans out.",
                    "customer": customer,
                    "opportunity": f"Make {label} independently reviewable, testable, and diagrammable.",
                    "product_view": f"{label} should have clear responsibility, intended paths, validation, and topology links.",
                    "success_metrics": [
                        f"{label} has a Registry component with user-intent evidence.",
                        f"{label} appears in at least one Atlas topology draft.",
                        f"{label} has a validation obligation before source-backed status is claimed.",
                    ],
                    "priority": "P1",
                    "sizing": "M",
                    "complexity": "Medium",
                    "recommended_first_slice": f"Write the first {label} contract and {first_slice_proof}.",
                    "evidence_tier": "user_intent",
                }
            )
    return rows


def _diagram_drafts(project_slug: str, intent_title: str, archetype: Archetype, components: Sequence[Mapping[str, Any]], complexity: str) -> list[dict[str, Any]]:
    limit = 1 if complexity == "simple" else 2 if complexity == "medium" else len(archetype.diagrams)
    component_rows = [
        {
            "name": str(row.get("label", "")).strip(),
            "description": str(row.get("responsibility", "")).strip(),
        }
        for row in components
        if str(row.get("label", "")).strip()
    ]
    intended_paths = [str(row.get("intended_path", "")).strip() for row in components if str(row.get("intended_path", "")).strip()]
    rows: list[dict[str, Any]] = []
    for blueprint in archetype.diagrams[:limit]:
        rows.append(
            {
                "slug": slugify(f"{project_slug}-{blueprint.slug_suffix}"),
                "title": f"{intent_title} {blueprint.title_suffix}",
                "kind": blueprint.kind,
                "summary": blueprint.summary,
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": component_rows,
                "intended_paths": intended_paths[:6],
                "watch_paths": [],
                "evidence_tier": "user_intent",
            }
        )
    return rows


def _assumptions(intent_title: str, archetype: Archetype, evidence: Mapping[str, Any]) -> list[str]:
    rows = [
        f"The project name and first boundaries are inferred from the prompt as `{intent_title}`.",
        "The proposed paths are intended starting points and can be changed before apply.",
        "Registry components are planned candidates until source files or stronger design docs exist.",
    ]
    if not evidence.get("languages"):
        rows.append("No language/runtime was inferred from repo metadata, so paths stay framework-neutral.")
    if archetype.archetype_id == "formal_proof":
        rows.append("Mathematical truth is not inferred; proof obligations stay draft until a proof checker or human review verifies them.")
    elif archetype.archetype_id in _RESEARCH_ARCHETYPE_IDS:
        rows.append("Scientific, statistical, environmental, or model claims are not inferred; only structure, evidence tracking, and validation obligations are proposed.")
    return rows


def _questions(archetype: Archetype, complexity: str) -> list[str]:
    rows = [
        "Which stack or runtime should own the first implementation slice?",
        "Which user, operator, or reviewer should be treated as the primary customer?",
    ]
    if complexity == "complex":
        rows.append("Which subsystem should be implemented first so the rest of the proposal can be validated against real code?")
    if archetype.archetype_id == "formal_proof":
        rows.extend(
            [
                "Which proof assistant, source text, or theorem collection should anchor the first formalization wave?",
                "Which definitions, admitted lemmas, or counterexample checks are non-negotiable before proof status is claimed?",
            ]
        )
    elif archetype.archetype_id == "computational_notebook":
        rows.extend(
            [
                "Which datasets, notebooks, and report outputs should become the first reproducibility oracle?",
                "Which statistical assumptions, cleaning rules, and random seeds must be locked before publication claims?",
            ]
        )
    elif archetype.archetype_id == "simulation_modeling":
        rows.extend(
            [
                "What reference datasets, derivations, or benchmark results should become the first correctness oracle?",
                "Which tolerances, units, and reproducibility constraints are non-negotiable?",
            ]
        )
    elif archetype.archetype_id == "scientific_pipeline":
        rows.extend(
            [
                "Which raw datasets, instruments, or external archives should anchor provenance for the first pipeline wave?",
                "Which stage-level quality-control checks should block promoted outputs?",
            ]
        )
    elif archetype.archetype_id == "geospatial_environmental":
        rows.extend(
            [
                "Which coordinate reference systems, spatial extents, and temporal coverage windows are authoritative?",
                "Which reference maps or sample regions should prove the first geospatial output?",
            ]
        )
    elif archetype.archetype_id == "ml_experiment_platform":
        rows.extend(
            [
                "Which dataset versions, splits, metrics, and promotion thresholds define the first accepted model candidate?",
                "Which latency, cost, drift, or safety checks must block release promotion?",
            ]
        )
    elif archetype.archetype_id == "math_education":
        rows.extend(
            [
                "Which learner level, curriculum sequence, and prerequisite model should shape the first lesson wave?",
                "Who reviews mathematical correctness for exercises, hints, and worked examples?",
            ]
        )
    return rows


def build_greenfield_proposal(*, repo_root: Path, prompt: str) -> dict[str, Any]:
    """Compile a provider-free greenfield proposal from prompt and shallow repo evidence."""

    root = Path(repo_root).expanduser().resolve()
    ranked_archetypes = rank_archetypes(prompt, limit=3)
    archetype, _raw_score, confidence = ranked_archetypes[0]
    intent_title = _intent_title(prompt, archetype)
    project_slug = slugify(intent_title)
    complexity = _complexity(prompt)
    evidence = _source_evidence(root)
    components = _component_drafts(project_slug, archetype, complexity)
    workstreams = _workstream_drafts(intent_title, archetype, components, complexity)
    diagrams = _diagram_drafts(project_slug, intent_title, archetype, components, complexity)
    waves = build_program_waves(archetype, components)
    proposal = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "catalog": catalog_metadata(),
        "intent": {
            "prompt": _prompt_text(prompt),
            "title": intent_title,
            "project_slug": project_slug,
            "archetype": archetype.archetype_id,
            "archetype_label": archetype.label,
            "complexity": complexity,
            "confidence": round(confidence, 2),
            "evidence_tier": "user_intent",
        },
        "classification": {
            "method": "deterministic_keyword_archetype_scoring",
            "primary": {
                "archetype": archetype.archetype_id,
                "archetype_label": archetype.label,
                "confidence": round(confidence, 2),
            },
            "alternatives": [
                {
                    "archetype": candidate.archetype_id,
                    "archetype_label": candidate.label,
                    "confidence": round(candidate_confidence, 2),
                }
                for candidate, _candidate_score, candidate_confidence in ranked_archetypes[1:]
            ],
            "fit_policy": "Use the primary fit by default; ask the operator before switching when alternate fits would change topology or validation.",
            "provider_calls": 0,
        },
        "observed_source": evidence,
        "greenfield_ux": build_greenfield_ux(
            intent_title=intent_title,
            source_posture=str(evidence.get("source_posture", "unknown")),
            complexity=complexity,
        ),
        "assumptions": _assumptions(intent_title, archetype, evidence),
        "open_questions": _questions(archetype, complexity),
        "risks": list(archetype.risks),
        "validation_strategy": list(archetype.validation_focus),
        "program": {
            "shape": "program_with_waves" if len(workstreams) > 1 else "single_slice_with_wave_plan",
            "wave_count": len(waves),
            "recommended_first_wave": str(waves[0].get("label", "Discovery")).strip() if waves else "Discovery",
            "blueprint": build_program_blueprint(
                intent_title=intent_title,
                archetype=archetype,
                workstreams=workstreams,
                waves=waves,
            ),
            "waves": waves,
        },
        "release_plan": build_release_plan(intent_title, archetype, waves),
        "backlog": workstreams,
        "components": components,
        "diagrams": diagrams,
    }
    proposal["apply_commands"] = build_apply_commands(proposal)
    return proposal


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


def _backlog_section_overrides(proposal: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    overrides: dict[str, dict[str, Any]] = {}
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    parent_title = str(backlog_rows[0].get("title", "")).strip() if backlog_rows else ""
    for row in backlog_rows:
        title = str(row.get("title", "")).strip()
        if not title:
            continue
        success_metrics = [str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()]
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
            "priority": str(row.get("priority", "P1")).strip() or "P1",
            "sizing": str(row.get("sizing", "M")).strip() or "M",
            "complexity": str(row.get("complexity", "Medium")).strip() or "Medium",
            "ordering_rationale": "Created from a confirmed Odylith greenfield proposal.",
        }
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
        success_metrics="\n".join(f"- {item}" for item in first.get("success_metrics", []) if str(item).strip()),
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
    return f"Target confirmed greenfield workstream(s) from `odylith greenfield apply --release {selector}`."


def _release_id_for_proposal(proposal: Mapping[str, Any]) -> str:
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    release_id = str(release_plan.get("provisional_release_id", "")).strip()
    if release_id:
        return slugify(release_id)
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    project_slug = slugify(str(intent.get("project_slug", "")).strip() or str(intent.get("title", "")).strip())
    return slugify(f"release-{project_slug}-first") if project_slug else "release-greenfield-first"


def _ensure_release_target(*, repo_root: Path, proposal: Mapping[str, Any], selector: str) -> dict[str, Any]:
    intent = proposal.get("intent", {}) if isinstance(proposal.get("intent"), Mapping) else {}
    title = str(intent.get("title", "Greenfield Project")).strip() or "Greenfield Project"
    release_plan = proposal.get("release_plan", {}) if isinstance(proposal.get("release_plan"), Mapping) else {}
    return release_planning_authoring.ensure_release_selector(
        repo_root=repo_root,
        selector=selector,
        release_id=_release_id_for_proposal(proposal),
        status="planning",
        name=str(release_plan.get("label", "")).strip() or "First governed release",
        notes=f"Greenfield release plan for {title}; created only after proposal confirmation.",
        aliases=(selector,),
        dry_run=False,
    )


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
    root = Path(repo_root).expanduser().resolve()
    backlog_rows = [row for row in proposal.get("backlog", []) if isinstance(row, Mapping)]
    if not backlog_rows:
        raise ValueError("proposal has no backlog records")
    release_selector = str(release_selector or "").strip()
    backlog_args = _backlog_apply_args(proposal, release_selector=release_selector)
    backlog_result = backlog_authoring.create_queued_backlog_items(
        repo_root=root,
        backlog_index_path=root / "odylith/radar/source/INDEX.md",
        ideas_root=root / "odylith/radar/source/ideas",
        titles=[str(row.get("title", "")).strip() for row in backlog_rows if str(row.get("title", "")).strip()],
        args=backlog_args,
    )
    release_bootstrap = None
    release_targeting = None
    if release_selector:
        release_bootstrap = _ensure_release_target(repo_root=root, proposal=proposal, selector=release_selector)
        release_targeting = release_planning_authoring.add_workstreams_to_release(
            repo_root=root,
            workstream_ids=[str(item["idea_id"]) for item in backlog_result["created"]],
            selector=release_selector,
            note=_release_assignment_note(selector=release_selector),
            idea_specs=backlog_result["_candidate_idea_specs"],
            dry_run=True,
        )
    for raw_path, text in backlog_result["idea_files"].items():
        Path(raw_path).write_text(str(text), encoding="utf-8")
    Path(backlog_result["backlog_index"]).write_text(str(backlog_result["backlog_index_text"]), encoding="utf-8")
    if release_selector:
        release_targeting = release_planning_authoring.add_workstreams_to_release(
            repo_root=root,
            workstream_ids=[str(item["idea_id"]) for item in backlog_result["created"]],
            selector=release_selector,
            note=_release_assignment_note(selector=release_selector),
            idea_specs=backlog_result["_candidate_idea_specs"],
            dry_run=False,
        )
    owned_surface_refresh.raise_for_failed_refresh(
        repo_root=root,
        surface="radar",
        operation_label="Greenfield apply backlog",
    )
    if release_selector:
        owned_surface_refresh.raise_for_failed_refresh(
            repo_root=root,
            surface="compass",
            operation_label="Greenfield apply release targeting",
        )

    components_created: list[dict[str, Any]] = []
    for row in proposal.get("components", []):
        if not isinstance(row, Mapping):
            continue
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
            workstreams=tuple(str(item["idea_id"]) for item in backlog_result["created"][:1]),
            dry_run=False,
        )
        components_created.append(created.as_dict())

    diagrams_created: list[str] = []
    atlas_scaffold_logs: list[str] = []
    for row in proposal.get("diagrams", []):
        if not isinstance(row, Mapping):
            continue
        diagram_id = _next_diagram_id(root)
        argv = [
            "--repo-root",
            str(root),
            "--diagram-id",
            diagram_id,
            "--slug",
            str(row.get("slug", "")).strip(),
            "--title",
            str(row.get("title", "")).strip(),
            "--kind",
            str(row.get("kind", "flowchart")).strip() or "flowchart",
            "--owner",
            str(row.get("owner", "repo")).strip() or "repo",
            "--summary",
            str(row.get("summary", "")).strip(),
        ]
        for component in row.get("components", []):
            if not isinstance(component, Mapping):
                continue
            name = str(component.get("name", "")).strip()
            description = str(component.get("description", "")).strip()
            if name and description:
                argv.extend(["--component", f"{name}::{description}"])
        for created in backlog_result["created"][:1]:
            argv.extend(["--backlog", str(created["idea_path"])])
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
                argv.extend(["--watch", token])
        scaffold_output = io.StringIO()
        with contextlib.redirect_stdout(scaffold_output):
            rc = scaffold_mermaid_diagram.main(argv)
        log_text = scaffold_output.getvalue().strip()
        if log_text:
            atlas_scaffold_logs.append(log_text)
        if rc != 0:
            detail = f": {log_text}" if log_text else ""
            raise RuntimeError(f"atlas scaffold failed for {row.get('slug')}{detail}")
        diagrams_created.append(diagram_id)

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

    return {
        "mode": "applied",
        "backlog": backlog_result["created"],
        "components": components_created,
        "diagrams": diagrams_created,
        "atlas_scaffold_logs": atlas_scaffold_logs,
        "memory": memory_record,
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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    if args.command == "propose":
        proposal = build_greenfield_proposal(repo_root=repo_root, prompt=str(args.prompt))
        if args.output_format == "json":
            print(json.dumps(proposal, indent=2, sort_keys=True))
        else:
            print(format_proposal_text(proposal), end="")
        return 0
    if args.command == "apply":
        try:
            proposal = _load_proposal(args)
            result = apply_greenfield_proposal(
                repo_root=repo_root,
                proposal=proposal,
                confirm=bool(args.confirm),
                release_selector=str(args.release),
            )
        except (ValueError, RuntimeError, json.JSONDecodeError) as exc:
            print(str(exc))
            return 2
        if args.as_json:
            print(json.dumps(result, indent=2, sort_keys=True))
        else:
            print("odylith greenfield apply wrote confirmed proposal")
            print(f"- backlog: {len(result['backlog'])}")
            print(f"- components: {len(result['components'])}")
            print(f"- diagrams: {len(result['diagrams'])}")
            release_target = result.get("release_target", {})
            if isinstance(release_target, Mapping) and str(release_target.get("release_id", "none")).strip() != "none":
                print(f"- release: {release_target.get('release_id')}")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
