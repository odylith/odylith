"""Host-reasoned greenfield governance contracts for consumer repos.

Odylith should not pretend a small built-in catalog can understand every
possible project the operator may ask for. This module gives host models a
strict evidence, schema, validation, and apply contract; the host model supplies
the open-world project reasoning, and Odylith validates and writes only after
explicit confirmation.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.analysis_engine import repo_analysis
from odylith.runtime.analysis_engine.types import SourceSummary, slugify
from odylith.runtime.domain_intelligence import greenfield_programs
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.proposal_memory import record_greenfield_acceptance
from odylith.runtime.domain_intelligence.proposal_rendering import format_proposal_text
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


def _proposal_contract() -> dict[str, Any]:
    return {
        "required_top_level_keys": [
            "schema_version",
            "mode",
            "intent",
            "observed_source",
            "assumptions",
            "open_questions",
            "risks",
            "validation_strategy",
            "program",
            "release_plan",
            "backlog",
            "components",
            "diagrams",
        ],
        "evidence_rules": [
            "Use observed_source only for facts found in the repo.",
            "Use user_intent for facts stated or directly implied by the operator prompt.",
            "Use odylith_assumption for useful architecture choices that need confirmation.",
            "Never mark source-backed ownership or scientific/math correctness from prompt text alone.",
        ],
        "minimum_content": {
            "backlog": "parent workstream plus child workstreams when the project has multiple meaningful boundaries; every child should carry first-slice, validation, component_focus, and related_diagram_slugs or enough specific language for Odylith to infer the topology",
            "components": "candidate Registry components with component_id, label, intended_path, responsibility, boundary/interfaces/dependencies where known, evidence_tier, status, and qualification",
            "diagrams": "purposeful Atlas drafts such as system context, program waves, runtime/data/validation topology, or a better domain-specific set; each diagram must name related components and workstream/backlog focus, and flowcharts must use subtle diagram-internal colors plus wrapped labels",
            "program": "wave plan with goals, validation gates, component focus, and evidence tier",
            "release_plan": "provisional release selector, first-target workstreams, stages, milestones, and promotion criteria; default selector is 0.0.1 unless the operator supplies a different release target",
            "tribunal": "apply runs a deterministic proposal Tribunal before writes; proposals fail if Radar, Registry, Atlas, program waves, or release targeting do not form a coherent topology",
        },
        "quality_bar": [
            "Reason from the actual prompt, not from a fixed in-code domain list.",
            "Prefer fewer high-quality boundaries over many generic buckets.",
            "Choose diagram types because they clarify the project, not because every project gets the same set.",
            "Each diagram must include host-authored mermaid_source; Odylith validates it but does not invent topology.",
            "For flowchart mermaid_source, use classDef/style colors inside the diagram for semantic grouping and <br/> to wrap long labels so text stays readable. Use subgraph lanes only where they clarify the topology; never rely on viewer background treatment.",
            "Child workstreams must not be title-only tickets; include concrete first-slice proof, impacted candidate components, topology/dependency hints, and validation gates.",
            "Registry components must read like planned ownership specs, not labels; include boundary, responsibility, interface, dependency, and proof expectations where the prompt supports them.",
            "Atlas diagrams and Radar workstreams must be mutually traceable through related workstream/component hints.",
            "For science and math, propose validation obligations and review gates; do not invent claims or results.",
            "For simple projects, keep the plan small; for complex projects, form waves and release gates.",
            "Default the first greenfield release target to 0.0.1 unless the operator explicitly asks for another release selector.",
            "Name the first release target workstreams from the first wave so Compass can show a concrete release lane without pretending every child belongs to the first release.",
            "Make the proposal easy to operate: name the program, waves, release selector, first target workstreams, impacted components, diagrams, and proof gates in plain language.",
            "Expect a Tribunal gate: child workstreams need component and diagram references, components need boundary/interface/dependency/proof expectations, and diagrams need workstream plus component traceability.",
        ],
    }


def build_greenfield_proposal(*, repo_root: Path, prompt: str) -> dict[str, Any]:
    """Return the host-reasoning contract for an open-world greenfield prompt."""

    root = Path(repo_root).expanduser().resolve()
    intent_title = _intent_title(prompt)
    project_slug = slugify(intent_title)
    evidence = _source_evidence(root)
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
                "host model drafts the concrete proposal from prompt and repo evidence",
                "operator reviews or edits assumptions, boundaries, diagrams, waves, and release plan",
                "Odylith validates and applies the confirmed proposal only after explicit confirmation",
            ],
            "write_guardrail": "This command does not write proposal records; host reasoning produces the draft, apply validates and writes after confirmation.",
            "next_best_action": f"Use host reasoning to draft backlog, Registry, Atlas, waves, release plan, validation, and open questions for {intent_title}.",
        },
        "reasoning_contract": _proposal_contract(),
        "host_instruction": (
            "Draft a concrete proposal for the operator now. Be specific to the prompt; "
            "do not use canned domain buckets. Label observed_source, user_intent, "
            "and odylith_assumption separately. Ask only the questions that materially "
            "change the first slice or correctness gates. For every child backlog item, "
            "include topology hints such as component_focus and related_diagram_slugs, "
            "plus first-slice validation. For every component, include enough boundary, "
            "responsibility, dependencies, interfaces, and validation expectations to seed "
            "a useful Registry CURRENT_SPEC.md. Default the provisional release selector "
            "to 0.0.1 unless the operator explicitly asks for another release target, "
            "and identify the first-wave workstreams that should target that release."
            " Odylith will run the confirmed proposal through a deterministic Tribunal "
            "before writes and will refresh Radar, Registry, Atlas, and Compass after "
            "the accepted artifacts are written."
        ),
        "apply_commands": [
            "Save the host-reasoned proposal JSON to odylith-greenfield-proposal.json after operator review.",
            "odylith greenfield apply --repo-root . --proposal-file odylith-greenfield-proposal.json --confirm --release 0.0.1",
        ],
    }
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


def _allocated_diagram_ids(repo_root: Path, count: int) -> list[str]:
    first = int(_next_diagram_id(repo_root).split("-", 1)[1])
    return [f"D-{value:03d}" for value in range(first, first + max(0, count))]


def _row_text_tuple(row: Mapping[str, Any], *keys: str) -> tuple[str, ...]:
    for key in keys:
        value = row.get(key)
        if value is None:
            continue
        if isinstance(value, (list, tuple, set)):
            values = tuple(str(item).strip() for item in value if str(item).strip())
            if values:
                return values
            continue
        token = str(value).strip()
        if token:
            return (token,)
    return ()


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
    return f"Target confirmed first-wave greenfield workstream(s) from `odylith greenfield apply --release {selector}`."


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
    return release_planning_authoring.ensure_release_selector(
        repo_root=repo_root,
        selector=selector,
        release_id=_release_id_for_proposal(proposal, selector=selector),
        status="planning",
        version=version,
        tag=tag,
        name=str(release_plan.get("label", "")).strip() or f"{title} {selector}",
        notes=f"Greenfield release plan for {title}; created only after proposal confirmation.",
        aliases=tuple(release_aliases),
        dry_run=False,
    )


_GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass")


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
        diagrams_created.append(diagram_id)
    touched_backlog_paths = greenfield_traceability.apply_backlog_traceability(
        repo_root=root,
        proposal=proposal,
        plan=traceability_plan,
    )

    components_created: list[dict[str, Any]] = []
    for row in proposal.get("components", []):
        if not isinstance(row, Mapping):
            continue
        key = greenfield_traceability.component_key(row)
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
            workstreams=traceability_plan.component_workstreams.get(key, ()),
            diagrams=traceability_plan.component_diagrams.get(key, ()),
            responsibility=str(row.get("responsibility", "")).strip(),
            boundary=str(row.get("boundary", "")).strip(),
            dependencies=_row_text_tuple(row, "dependencies", "depends_on"),
            interfaces=_row_text_tuple(row, "interfaces", "interface_changes"),
            validation=_row_text_tuple(row, "validation", "test_strategy"),
            risks=_row_text_tuple(row, "risks"),
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
            tribunal = result.get("tribunal", {})
            if isinstance(tribunal, Mapping):
                print(f"- tribunal: {tribunal.get('status', 'unknown')}")
            print(f"- backlog: {len(result['backlog'])}")
            print(f"- components: {len(result['components'])}")
            print(f"- diagrams: {len(result['diagrams'])}")
            program = result.get("program", {})
            if isinstance(program, Mapping) and bool(program.get("created")):
                print(f"- program: {program.get('umbrella_id')} ({len(program.get('waves', []))} waves)")
            release_target = result.get("release_target", {})
            if isinstance(release_target, Mapping) and str(release_target.get("release_id", "none")).strip() != "none":
                workstreams = release_target.get("workstream_ids", [])
                count = len(workstreams) if isinstance(workstreams, list) else 0
                print(f"- release: {release_target.get('release_id')} ({count} targeted workstreams)")
            dashboard = result.get("dashboard_refresh", {})
            if isinstance(dashboard, Mapping):
                surfaces = ", ".join(str(item) for item in dashboard.get("surfaces", []))
                print(f"- dashboard: refreshed {surfaces}")
                print(f"- view: {dashboard.get('view')}")
        return 0
    return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
