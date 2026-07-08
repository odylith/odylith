from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence import greenfield_traceability
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import parse_confirmed_intent_text
from odylith.runtime.domain_intelligence.greenfield_confirmed_intent import write_structured_confirmed_intent_file
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import build_product_intent_envelope
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import product_intent_authority_from_envelope
from odylith.runtime.domain_intelligence.greenfield_project_intelligence import PROJECT_INTELLIGENCE_LAYERS
from odylith.runtime.governance import validate_backlog_contract as backlog_contract


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _markdown_section(text: str, heading: str) -> str:
    start = text.index(heading)
    end = text.find("\n## ", start + len(heading))
    return text[start:] if end == -1 else text[start:end]


CONFIRMED_INTENT_TEXT = """Municipal Permit Review Workspace — Product Intent Confirmation

Product story
A city permitting team uses the Municipal Permit Review Workspace to review building permit submissions without losing the connection between applicant documents, zoning checks, reviewer comments, and approval decisions. The product gives permit coordinators and reviewers one place to see what was submitted, what changed, which checks passed, and why a permit is ready, blocked, or rejected.

State object that changes through the first journey
A Permit Review File tracks the permit application, submitted documents, zoning status, reviewer comments, applicant revisions, decision state, and evidence that supports each approval or rejection.

First complete path the product should prove before broader scope
A permit coordinator imports one permit application, a zoning reviewer records a zoning check, the applicant submits one revision, and a supervisor reviews the decision package with traceable documents, comments, checks, and final status.

Human actors
- Permit coordinator — intakes applications and keeps review work moving.
- Zoning reviewer — evaluates parcel, use, setback, and code-check evidence.
- Applicant — submits documents and revisions.
- Review supervisor — approves, blocks, or rejects a decision package.

External systems
- Document intake portal — supplies application packets and revision uploads.
- Parcel zoning data — supplies zoning district, parcel attributes, and rule references.
- Payment ledger — supplies fee status without owning review decisions.

Internal product systems
- Permit file registry — owns permit identity, applicant metadata, submitted documents, and decision state.
- Zoning check ledger — records zoning checks, reviewer comments, rule references, and pass or block outcomes.
- Revision tracker — links applicant revisions to the documents and checks they are meant to address.
- Decision package review — assembles evidence, reviewer notes, unresolved blockers, and final approval state.

Critical assumptions
- Release 0.0.1 is an internal reviewer workspace, not a public application portal.
- Payment status can be referenced but does not decide review readiness.
- Review evidence must remain understandable to permitting staff and applicants.

Ambiguities that would change the first path
1. Does the first release need applicant self-service, or only internal staff review?
2. Are zoning rules imported from a live GIS source, or referenced manually by reviewers?
3. Does final approval require one supervisor or multiple department sign-offs?

Proof boundary
Release 0.0.1 succeeds when a supervisor can inspect one permit review file, see the active submitted documents, zoning check result, applicant revision, reviewer comments, unresolved blockers, and final decision state, and trace every decision back to source documents and reviewer evidence.
"""


HIIT_CONFIRMED_INTENT_TEXT = """PulseHIIT - guided high-intensity interval training

## Product story
PulseHIIT helps a trainee start a guided high-intensity interval workout, follow hands-free timing and cues, and review the completed session afterward.

## State object
The core state is a workout session: selected workout, interval plan, current interval, elapsed and remaining time, audio and on-screen cue state, pause/resume state, completion state, and saved history entry.

## First complete path
A trainee chooses a workout, starts it, the timer drives each work and rest interval with audio and on-screen cues, keeps the screen awake, marks the session complete, and saves the session to history with date, workout, and total time.

## Human actors
- Trainee following a guided workout.
- Workout author creating preset interval workouts.

## External systems
- Optional: device wake-lock so the screen stays on mid-workout.

## Internal product systems
- Workout library.
- Interval timer engine.
- Session history.
- Workout builder.

## Critical assumptions
- Release 0.0.1 starts with preset interval workouts before complex custom programming.
- The workout can run locally without live coaching or wearable integrations.
- Audio cues and on-screen cues must both be visible in the proof boundary.

## Ambiguities
- Whether custom workout building belongs in the first release or a later release.
- Whether streak tracking is core to the first proof or a fast-follow.

## Proof boundary
Release 0.0.1 succeeds when a trainee can choose a preset interval workout, start it, follow each interval without touching the screen, complete the workout, and see the completed session in history with its date, workout, and total time.
"""


def _confirmed_intent() -> dict[str, object]:
    return confirmed_intent_with_authority(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a greenfield proposal for a municipal permit review workspace",
    )


def confirmed_intent_with_authority(
    text: str,
    *,
    prompt: str,
    repo_root: Path | None = None,
    write_files: bool = False,
) -> dict[str, object]:
    intent = parse_confirmed_intent_text(
        text,
        prompt=prompt,
    )
    root = Path("/repo") if repo_root is None else Path(repo_root)
    markdown_path = root / ".odylith/runtime/greenfield/confirmed-intent.md"
    envelope = build_product_intent_envelope(
        intent,
        source_text=text,
        source_path=markdown_path,
        source_format="markdown",
    )
    if write_files:
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(text, encoding="utf-8")
        write_structured_confirmed_intent_file(markdown_path, intent, envelope=envelope)
    intent[PRODUCT_INTENT_AUTHORITY_KEY] = product_intent_authority_from_envelope(
        envelope,
        structured_intent_path=markdown_path.with_suffix(".json"),
        markdown_source_path=markdown_path,
    )
    return intent


def compiled_greenfield_package_fixture(
    proposal: dict[str, Any],
    *,
    repo_root: Path,
    release_selector: str = "0.0.1",
    baseline_writes: dict[str, str] | None = None,
    brand_asset_writes: dict[str, dict[str, str]] | None = None,
) -> GreenfieldCompletionPackage:
    idea_id = "B-001"
    title = "Prove first accepted path"
    idea_path = Path(repo_root) / "odylith/radar/source/ideas/B-001.md"
    created_backlog = [{"title": title, "idea_id": idea_id, "idea_path": str(idea_path)}]
    diagram_rows = [row for row in proposal.get("diagrams", []) if isinstance(row, dict)]
    diagram_ids = tuple(f"D-{index:03d}" for index, _row in enumerate(diagram_rows, start=1))
    rendered_atlas_sources = {
        f"odylith/atlas/source/{str(row.get('slug', f'diagram-{index}')).strip() or f'diagram-{index}'}.mmd": (
            "flowchart TD\n  A[\"Accepted input\"] --> B[\"Reviewed result\"]\n"
        )
        for index, row in enumerate(diagram_rows, start=1)
    }
    backlog_result = {
        "created": created_backlog,
        "idea_files": {str(idea_path): f"{title}\n"},
        "backlog_index": str(Path(repo_root) / "odylith/radar/source/INDEX.md"),
        "backlog_index_text": f"| {idea_id} | {title} |\n",
        "_candidate_idea_specs": {
            idea_id: backlog_contract.IdeaSpec(
                path=idea_path,
                metadata={"idea_id": idea_id, "status": "candidate"},
                sections={"Problem", "Product View"},
                section_bodies={
                    "Problem": "The first accepted path needs a durable proof record.",
                    "Product View": "The product exposes the accepted first path.",
                },
            )
        },
    }
    release_id = "release-0-0-1"
    return GreenfieldCompletionPackage(
        proposal=proposal,
        release_selector=release_selector,
        rendered_atlas_sources=rendered_atlas_sources,
        atlas_review_date="2026-07-07",
        atlas_diagram_ids=diagram_ids,
        backlog_result=backlog_result,
        project_brief_record_text="# Compiled Greenfield Project Brief\n\n- accepted_at: prewrite\n",
        accepted_project_preview={
            "schema_version": "odylith.accepted_project.v1",
            "origin": "greenfield",
            "evidence_tier": "user_intent",
            "accepted_at": "prewrite",
            "title": str(proposal.get("intent", {}).get("title", "Compiled Greenfield Project")),
            "source_launch": {"implementation_prompt": f"Start {idea_id} from the compiled transaction package."},
            "created": {"workstreams": [{"idea_id": idea_id}], "components": [], "diagrams": list(diagram_ids)},
            "validation_gate": {"status": "passed", "issues": []},
        },
        compass_memory_preview={
            "version": "v1",
            "kind": "decision",
            "summary": "Accepted compiled greenfield transaction package.",
            "ts_iso": "prewrite",
            "author": "odylith",
            "source": "domain-intelligence",
            "workstreams": [idea_id],
            "artifacts": ["odylith/runtime/source/project-brief.v1.md"],
            "components": [],
            "evidence_tier": "user_intent",
            "work_category": "governance",
        },
        next_steps_preview={
            "project_workstream_id": idea_id,
            "start_workstream_id": idea_id,
            "start_workstream_title": title,
            "release_selector": release_selector,
            "implementation_prompt": f"Start {idea_id} from the compiled transaction package.",
            "operator_sequence": [f"Open {idea_id}.", "Implement the first accepted path."],
            "coding_readiness_gates": ["Transaction package accepted."],
            "verification_commands": [f"odylith context --repo-root . {idea_id}"],
        },
        program_result={
            "created": True,
            "dry_run": True,
            "umbrella_id": idea_id,
            "program_path": str(Path(repo_root) / f"odylith/radar/source/programs/{idea_id}.execution-waves.v1.json"),
            "waves": [
                {
                    "wave_id": "W1",
                    "label": "First accepted path",
                    "status": "active",
                    "summary": "Deliver the first accepted path.",
                    "exit_gate": "The first accepted path is proven.",
                    "validation": [],
                    "depends_on": [],
                    "primary_workstreams": [idea_id],
                    "carried_workstreams": [],
                    "in_band_workstreams": [],
                    "gate_refs": [],
                }
            ],
            "program_count": 0,
        },
        traceability_plan=greenfield_traceability.build_traceability_plan(
            proposal=proposal,
            created_backlog=created_backlog,
            diagram_ids=diagram_ids,
        ),
        baseline_writes=baseline_writes,
        brand_asset_writes=brand_asset_writes,
        prewrite_safety_preview={"status": "passed"},
        release_target_result={
            "dry_run": True,
            "selector": release_selector,
            "release": {
                "release_id": release_id,
                "status": "planning",
                "version": release_selector,
                "tag": f"v{release_selector}",
                "name": f"Release {release_selector}",
                "notes": "First compiled greenfield release.",
                "created_utc": "2026-07-07T00:00:00Z",
            },
        },
        release_assignment_result={
            "dry_run": True,
            "workstream_ids": [idea_id],
            "events": [],
            "release": {"release_id": release_id},
        },
        release_workstream_ids=(idea_id,),
    )


def _write_confirmed_intent(repo_root: Path) -> Path:
    path = repo_root / ".odylith" / "runtime" / "greenfield" / "confirmed-intent.md"
    _write(path, CONFIRMED_INTENT_TEXT)
    return path


def _ontology_term_labels(rows: object) -> list[str]:
    values = rows if isinstance(rows, list) else []
    labels: list[str] = []
    for row in values:
        text = str(row or "").strip()
        if not text:
            continue
        labels.append(text.split(":", 1)[0].strip().casefold())
    return labels


def _seed_empty_governance_repo(repo_root: Path) -> None:
    empty_backlog_table = (
        "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | status | link |\n"
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n\n"
    )
    _write(
        repo_root / "odylith/radar/source/INDEX.md",
        (
            "# Backlog Index\n\n"
            "Last updated (UTC): 2026-05-03\n\n"
            "## Ranked Active Backlog\n\n"
            f"{empty_backlog_table}"
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)\n\n"
            f"{empty_backlog_table}"
            "## Finished (Linked to `odylith/technical-plans/done`)\n\n"
            f"{empty_backlog_table}"
            "## Reorder Rationale Log\n\n"
        ),
    )
    (repo_root / "odylith/radar/source/ideas").mkdir(parents=True, exist_ok=True)
    _write(
        repo_root / "odylith/atlas/source/catalog/diagrams.v1.json",
        json.dumps({"schema_version": "odylith.diagrams.v1", "diagrams": []}, indent=2) + "\n",
    )


def _governed_greenfield_fixture(repo_root: Path, prompt: str) -> dict[str, object]:
    _ = repo_root
    proposal = copy.deepcopy(_host_reasoned_ecommerce_proposal())
    title = " ".join(part[:1].upper() + part[1:] for part in greenfield_proposals.slugify(prompt).split("-"))
    title = title or "Host Authored Greenfield Project"
    slug = greenfield_proposals.slugify(title)
    intent = proposal["intent"]
    assert isinstance(intent, dict)
    intent.update({"prompt": prompt, "title": title, "project_slug": slug})
    proposal["project_brief"] = _host_project_brief(title=title, prompt=prompt, release="0.0.1")
    proposal["project_intelligence"] = _host_project_intelligence(title=title, release="0.0.1")
    release_focus = _host_release_focus_for_prompt(prompt)
    release_plan = proposal.get("release_plan")
    if isinstance(release_plan, dict):
        release_plan.update(
            {
                "label": f"{title} first governed release",
                "provisional_release_id": f"release-{slug}-first",
                "strategy": f"Promote the {release_focus} only after validation proof and refreshed release evidence.",
            }
        )
        milestones = release_plan.get("milestones")
        if isinstance(milestones, list):
            for milestone in milestones:
                if isinstance(milestone, dict):
                    milestone["exit_criteria"] = (
                        f"The named product operator accepts the {release_focus}, components, topology, and validation."
                    )
    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        actor_lines = _host_actor_lines_for_prompt(prompt)
        for row in backlog:
            if isinstance(row, dict):
                row["domain_intelligence"] = _host_domain_intelligence(
                    title=title,
                    row_title=str(row.get("title") or title),
                    actors=actor_lines,
                )
    return greenfield_proposals.normalize_host_reasoned_proposal(proposal)


_apply_ready_greenfield_fixture = _governed_greenfield_fixture


def _host_reasoned_ecommerce_proposal() -> dict[str, object]:
    proposal: dict[str, object] = {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "confirmed_intent_before_confirmed_create",
        "intent": {
            "prompt": "Build an ecommerce site",
            "title": "Commerce Launch System",
            "project_slug": "commerce-launch-system",
            "reasoning_mode": "host_model_reasoned",
            "evidence_tier": "user_intent",
            "product_story": (
                "Commerce Launch System helps a shopper and commerce operator prove browse-to-checkout recovery "
                "before production payment readiness is claimed."
            ),
            "state_object": (
                "The commerce checkout record tracks shopper session, cart items, checkout status, payment sandbox "
                "result, order draft, retry state, and release proof."
            ),
            "first_path": (
                "A shopper opens the storefront, adds one product to the cart, starts checkout, handles one failed "
                "sandbox payment response, retries checkout, and sees the order draft with recovery status."
            ),
            "proof_boundary": (
                "Release 0.0.1 succeeds when one shopper can browse to cart, enter checkout, recover from one failed "
                "sandbox payment, and review the order draft without claiming production payment readiness."
            ),
        },
        "observed_source": {"source_posture": "empty_or_no_app_source"},
        "assumptions": [
            "The first slice should prove browse-to-checkout without claiming payment production readiness.",
            "Inventory, payment, and order state remain separate until source evidence says otherwise.",
        ],
        "open_questions": [
            "Which stack owns the storefront?",
            "Which payment provider or sandbox should shape the first proof?",
        ],
        "risks": [
            "Combining cart, payment, and order state would hide failure recovery.",
        ],
        "security_compliance": {
            "domain": "Ecommerce checkout domain with payment sandbox, order, inventory, and shopper data risk.",
            "security": "Security posture covers payment handoff, session access, retry abuse, and idempotent order recovery.",
            "policy": "Compliance posture keeps PCI/provider policy, privacy, auditability, and accessibility explicit before production payment claims.",
        },
        "validation_strategy": [
            "Checkout happy path and payment failure recovery must both pass.",
            "Order creation must be idempotent under retry and webhook replay.",
        ],
        "program": {
            "shape": "program_with_waves",
            "wave_count": 4,
            "recommended_first_wave": "Checkout spine",
            "blueprint": {
                "program_type": "greenfield_program",
                "parent_workstream": "Govern Commerce Launch System",
                "child_workstream_strategy": "Create child boundaries for storefront, catalog, checkout, and order reliability.",
                "child_workstreams": ["Define Storefront boundary", "Define Checkout boundary"],
                "wave_to_workstream_policy": "Waves are delivery checkpoints; workstreams remain user_intent until source evidence exists.",
                "release_strategy": "Target the accepted first checkout slice to the provisional 0.0.1 release.",
                "recommended_wave_order": ["Checkout spine", "Catalog integrity", "Payment recovery", "Operational hardening"],
                "evidence_tier": "odylith_assumption",
            },
            "waves": [
                {
                    "wave": 1,
                    "label": "Checkout spine",
                    "goal": "Prove browse, cart, checkout handoff, and order draft.",
                    "validation": "Browser proof covers happy path and failed payment recovery.",
                    "workstream_titles": ["Define Storefront boundary"],
                    "component_focus": ["commerce-storefront", "commerce-checkout"],
                    "evidence_tier": "odylith_assumption",
                },
                {
                    "wave": 2,
                    "label": "Catalog integrity",
                    "goal": "Make product, price, inventory, and merchandising reviewable.",
                    "validation": "Price and inventory snapshot rules are explicit.",
                    "workstream_titles": ["Define Catalog boundary"],
                    "component_focus": ["commerce-catalog"],
                    "evidence_tier": "odylith_assumption",
                },
            ],
        },
        "release_plan": {
            "selector": "0.0.1",
            "label": "First governed commerce release",
            "provisional_release_id": "release-commerce-launch-first",
            "strategy": "Promote only after checkout validation and refreshed release evidence.",
            "release_stages": [
                {"stage": "wave-1", "label": "Checkout spine", "release_gate": "Browser and recovery proof pass."},
            ],
            "target_workstream_titles": ["Define Storefront boundary"],
            "milestones": [
                {
                    "name": "Proposal accepted",
                    "exit_criteria": "The commerce operator accepts assumptions, first slice, components, topology, and validation.",
                }
            ],
            "evidence_tier": "odylith_assumption",
        },
        "backlog": [
            {
                "title": "Govern Commerce Launch System",
                "problem": "Commerce builders launching an ecommerce site and shoppers cannot trust checkout until browse, cart, payment handoff, order draft, and recovery evidence are separated.",
                "customer": "Commerce builders and shoppers",
                "opportunity": "Let commerce builders review one checkout-first path with explicit recovery gates before source work expands.",
                "product_view": "Commerce Launch System should let shoppers browse, enter a cart, attempt checkout, and see recoverable payment failure while builders inspect the supporting state and evidence.",
                "success_metrics": [
                    "The checkout spine has a parent workstream and first child boundary.",
                    "Candidate components are user_intent until source evidence exists.",
                    "Architecture diagrams carry distinct system-context and program-wave drafts.",
                ],
                "priority": "P1",
                "sizing": "L",
                "complexity": "High",
                "recommended_first_slice": "Start with checkout spine proof and failed-payment recovery.",
                "evidence_tier": "user_intent",
            },
            {
                "title": "Define Storefront boundary",
                "problem": "The user-facing browse and checkout UI needs a named owner before implementation.",
                "customer": "Shoppers and commerce builders",
                "opportunity": "Keep storefront behavior independently reviewable and testable.",
                "product_view": "Storefront should own browse, cart entry, checkout entry, and user-visible errors.",
                "success_metrics": [
                    "Storefront appears in component specs and architecture diagrams with user_intent evidence.",
                    "Browse-to-cart entry has a first-slice validation gate before implementation.",
                ],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the checkout route and state contract for browse-to-cart.",
                "component_focus": ["commerce-storefront", "commerce-checkout"],
                "related_diagram_slugs": ["commerce-launch-system-context", "commerce-launch-program-waves"],
                "dependencies": [
                    "Depends on checkout handoff semantics and a catalog read model being explicit before source implementation.",
                ],
                "interfaces": [
                    "Defines browse, cart-entry, checkout-entry, and error-state contracts before code exists.",
                ],
                "validation": [
                    "Browser proof must cover browse-to-cart and failed-checkout messaging before implementation starts.",
                ],
                "evidence_tier": "user_intent",
            },
            {
                "title": "Define Catalog boundary",
                "problem": "Product, price, and inventory rules need a named owner before checkout can be evaluated honestly.",
                "customer": "Builders",
                "opportunity": "Keep product facts and inventory snapshots separate from checkout orchestration.",
                "product_view": "Catalog should own product reads, price snapshots, inventory visibility, and merchandising review boundaries.",
                "success_metrics": [
                    "Catalog appears in component specs and architecture diagrams with user_intent evidence.",
                    "Price and inventory snapshot rules have a first-slice validation gate.",
                ],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the product, price, and inventory snapshot contract.",
                "component_focus": ["commerce-catalog"],
                "related_diagram_slugs": ["commerce-launch-system-context", "commerce-launch-program-waves"],
                "dependencies": [
                    "Depends on source-backed implementation planning to choose the actual catalog storage boundary.",
                ],
                "interfaces": [
                    "Defines read-only product, price, and inventory snapshot interfaces for checkout.",
                ],
                "validation": [
                    "Contract proof must show checkout reads immutable price and inventory snapshots.",
                ],
                "evidence_tier": "user_intent",
            },
        ],
        "components": [
            {
                "component_id": "commerce-storefront",
                "label": "Storefront",
                "kind": "application",
                "intended_path": "apps/web",
                "responsibility": "Browse, cart entry, checkout entry, and user-facing errors.",
                "boundary": "Owns shopper-facing browse, cart-entry, checkout-entry, and user-visible error states.",
                "dependencies": ["Depends on catalog reads and checkout handoff contracts."],
                "interfaces": ["Browser routes, cart-entry command, checkout-entry command, and error presentation contract."],
                "validation": ["Browser smoke proof for browse-to-cart and failed-checkout messaging."],
                "workstream_titles": ["Define Storefront boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
            {
                "component_id": "commerce-checkout",
                "label": "Checkout Orchestrator",
                "kind": "service",
                "intended_path": "src/checkout",
                "responsibility": "Payment handoff, order draft, idempotency, and recovery boundaries.",
                "boundary": "Owns checkout handoff, payment sandbox interaction, order draft creation, and retry recovery.",
                "dependencies": ["Depends on storefront checkout entry and catalog price snapshot reads."],
                "interfaces": ["Checkout command, payment provider sandbox adapter, order-draft writer, and retry contract."],
                "validation": ["Contract proof for idempotent order draft creation and failed payment recovery."],
                "workstream_titles": ["Define Storefront boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
            {
                "component_id": "commerce-catalog",
                "label": "Catalog Boundary",
                "kind": "service",
                "intended_path": "src/catalog",
                "responsibility": "Product facts, price snapshots, inventory visibility, and merchandising review.",
                "boundary": "Owns product facts, price snapshots, inventory visibility, and merchandising review semantics.",
                "dependencies": ["No source dependency is claimed until implementation planning chooses storage."],
                "interfaces": ["Product-read query, price-snapshot query, and inventory-availability query."],
                "validation": ["Contract proof that checkout uses immutable price and inventory snapshots."],
                "workstream_titles": ["Define Catalog boundary"],
                "evidence_tier": "user_intent",
                "status": "planned",
                "qualification": "candidate",
            },
        ],
        "diagrams": [
            {
                "slug": "commerce-launch-system-context",
                "title": "System Context",
                "kind": "flowchart",
                "summary": "Show shopper, storefront, checkout, order, payment, and release-evidence boundaries.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {
                        "name": "Storefront",
                        "description": "Owns shopper-facing browse, cart entry, checkout entry, and user-visible error evidence.",
                    },
                    {
                        "name": "Checkout Orchestrator",
                        "description": "Owns payment handoff, order draft creation, retry recovery, and validation evidence.",
                    },
                    {
                        "name": "Catalog Boundary",
                        "description": "Owns product facts, price snapshots, inventory visibility, and merchandising review evidence.",
                    },
                ],
                "related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront boundary", "Define Catalog boundary"],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "flowchart LR\n"
                    "    subgraph experience_lane[\"Experience lane\"]\n"
                    "      shopper[\"Shopper\"]\n"
                    "      storefront[\"Storefront UI\"]\n"
                    "    end\n"
                    "    subgraph transaction_lane[\"Transaction lane\"]\n"
                    "      checkout[\"Checkout<br/>orchestrator\"]\n"
                    "      payment[\"Payment sandbox\"]\n"
                    "      order[\"Order ledger\"]\n"
                    "    end\n"
                    "    subgraph evidence_lane[\"Evidence lane\"]\n"
                    "      release_proof[\"Release<br/>evidence spine\"]\n"
                    "    end\n"
                    "    shopper --> storefront --> checkout\n"
                    "    checkout --> payment\n"
                    "    checkout --> order\n"
                    "    order --> release_proof\n"
                    "    payment -. failure recovery .-> checkout\n"
                    "    classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;\n"
                    "    classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
                    "    classDef evidence fill:#F5F3FF,stroke:#DDD6FE,color:#17233A,stroke-width:1px;\n"
                    "    class shopper,storefront actor;\n"
                    "    class checkout,payment,order service;\n"
                    "    class release_proof evidence;\n"
                    "    style experience_lane fill:#FBFDFF,stroke:#BFD7FE,stroke-width:1px,color:#334155\n"
                    "    style transaction_lane fill:#FBFDFF,stroke:#A7E9E3,stroke-width:1px,color:#334155\n"
                    "    style evidence_lane fill:#FBFDFF,stroke:#DDD6FE,stroke-width:1px,color:#334155\n"
                ),
            },
            {
                "slug": "commerce-launch-program-waves",
                "title": "Program Waves",
                "kind": "flowchart",
                "summary": "Show checkout spine, catalog integrity, payment recovery, and hardening waves.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {"name": "Storefront", "description": "Owns browse-to-cart proof, shopper-facing route ownership, and error evidence."},
                    {"name": "Checkout Orchestrator", "description": "Payment recovery proof and order-state handoff."},
                    {"name": "Catalog Boundary", "description": "Owns price snapshot, inventory review, and checkout validation evidence."},
                ],
                "related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront boundary", "Define Catalog boundary"],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "timeline\n"
                    "    title Program Waves\n"
                    "    Checkout spine : Browse-to-cart proof : Payment failure recovery\n"
                    "    Catalog integrity : Price snapshot rules : Inventory review\n"
                    "    Order reliability : Idempotent creation : Webhook replay proof\n"
                    "    Operational hardening : Observability : Release gate\n"
                ),
            },
        ],
    }
    return _complete_host_reasoned_proposal(proposal)


def _complete_host_reasoned_proposal(proposal: dict[str, object]) -> dict[str, object]:
    intent = proposal.get("intent") if isinstance(proposal.get("intent"), dict) else {}
    title = str(intent.get("title") or "Host Authored Greenfield Project")
    prompt = str(intent.get("prompt") or title)
    release = "0.0.1"
    proposal["project_brief"] = _host_project_brief(title=title, prompt=prompt, release=release)
    proposal["project_intelligence"] = _host_project_intelligence(title=title, release=release)
    backlog = proposal.get("backlog")
    if isinstance(backlog, list):
        actor_lines = _host_actor_lines_for_prompt(prompt)
        for index, row in enumerate(backlog):
            if not isinstance(row, dict):
                continue
            if index == 0:
                row.setdefault("workstream_type", "program_parent")
            row.setdefault("rationale_lines", _host_rationale_lines(row, prompt=prompt))
            row.setdefault(
                "domain_intelligence",
                _host_domain_intelligence(
                    title=title,
                    row_title=str(row.get("title") or title),
                    actors=actor_lines,
                ),
            )
    return proposal


def _host_actor_lines_for_prompt(prompt: str) -> list[str]:
    if "ecommerce" in prompt.casefold() or "checkout" in prompt.casefold():
        return [
            "Shopper advocate: represents the buyer moving through browse, cart, checkout, failure recovery, and order confirmation.",
            "Commerce operator: owns catalog readiness, checkout handoff, and day-to-day order workflow movement.",
            "Payment risk reviewer: owns payment failure, duplicate order, retry abuse, and provider-policy exposure.",
            "Checkout proof reviewer: decides whether browser, contract, and recovery proof are strong enough to advance release.",
            "Commerce build owner: owns storefront, checkout, catalog, source paths, implementation sequence, and validation commands after planning.",
        ]
    if "plant" in prompt.casefold() or "sensor" in prompt.casefold():
        return [
            "Plant owner advocate: represents the person depending on the monitor to surface plant health before neglect or over-care causes damage.",
            "Care routine operator: owns watering schedule, sensor review, refill workflow, and day-to-day plant-care movement.",
            "Plant safety reviewer: owns overwatering, dry-soil, alert failure, electrical, and unattended-device exposure.",
            "Care proof reviewer: decides whether sensor, watering, alert, and recovery proof is strong enough to advance release.",
            "Plant monitor build owner: owns device controller, plant-state model, source paths, implementation sequence, and validation commands after planning.",
        ]
    return [
        "Product beneficiary advocate: represents the person who receives value from the first path.",
        "Product workflow operator: owns day-to-day movement through the proposed workflow.",
        "Product risk reviewer: owns the unresolved harm, loss, compliance, or operational exposure.",
        "Product proof reviewer: decides whether evidence is strong enough to advance the release.",
        "Product build owner: owns source paths, implementation sequence, and validation commands after planning.",
    ]


def _host_release_focus_for_prompt(prompt: str) -> str:
    lowered = prompt.casefold()
    if "ecommerce" in lowered or "checkout" in lowered:
        return "commerce checkout recovery path"
    if "plant" in lowered or "sensor" in lowered:
        return "plant-care monitoring path"
    if "defi" in lowered or "risk" in lowered:
        return "DeFi risk-monitoring path"
    return "first product path"


def _host_rationale_lines(row: dict[str, object], *, prompt: str) -> list[str]:
    title = str(row.get("title") or "proposed work").strip()
    opportunity = str(row.get("opportunity") or row.get("product_view") or title).strip()
    first_slice = str(row.get("recommended_first_slice") or row.get("product_view") or title).strip()
    metric = next((str(item).strip() for item in row.get("success_metrics", []) if str(item).strip()), first_slice)
    release_focus = _host_release_focus_for_prompt(prompt)
    return [
        f"- why now: {opportunity}",
        f"- expected outcome: {first_slice}",
        f"- tradeoff: {title} keeps the {release_focus} visible while delaying wider automation.",
        f"- deferred for now: broad integrations, irreversible actions, and unrelated platform work wait until {release_focus} proof exists.",
        f"- ranking basis: {metric}",
    ]


def _host_project_brief(*, title: str, prompt: str, release: str) -> dict[str, object]:
    return {
        "schema_version": "odylith.greenfield.project_brief.v1",
        "purpose": f"{title} helps the first user complete one reviewable product path without losing state, owner, failure, or evidence context.",
        "operating_principle": f"Every release {release} claim must connect the user action, state change, owning boundary, validation result, and reviewer-visible evidence.",
        "project_outcome": f"A reviewer can inspect the {title} first path, state change, evidence, non-goals, and release decision before implementation expands scope.",
        "blueprint_sections": [
            {
                "section": "Product story",
                "must_capture": "The user outcome, first path, business value, boundaries, and excluded production claims.",
                "why_it_matters": "It keeps the project understandable before expert records and implementation details appear.",
            },
            {
                "section": "Actors and systems",
                "must_capture": "Human actors, external systems, internal systems, owners, and approval responsibilities.",
                "why_it_matters": "It prevents arbitrary personas and clarifies who changes or absorbs risk.",
            },
            {
                "section": "Owned product boundaries",
                "must_capture": "Which product capability owns each state change, external handoff, evidence source, and release decision.",
                "why_it_matters": "It keeps product understanding ahead of implementation detail and prevents disconnected ownership.",
            },
            {
                "section": "Proof boundary",
                "must_capture": "Evidence tiers, validation commands, failure modes, unresolved assumptions, and promotion gates.",
                "why_it_matters": "It prevents proposal prose from becoming source-backed implementation evidence.",
            },
        ],
        "customization_options": [
            {
                "id": "D1",
                "decision": "First user and job",
                "recommended": "Name the first person who must succeed and the single job that proves value.",
                "choices": ["end user", "operator", "reviewer", "administrator"],
                "impact": "Changes the first path, actors, UI or command surface, access model, and proof target.",
            },
            {
                "id": "D2",
                "decision": "Source and integration boundary",
                "recommended": "Keep integrations fixture-backed until credentials, contracts, and proof requirements are explicit.",
                "choices": ["fixture only", "sandbox provider", "read-only live source", "production integration later"],
                "impact": "Changes security posture, validation harness, architecture diagrams, and release risk.",
            },
            {
                "id": "D3",
                "decision": "Runtime and delivery shape",
                "recommended": "Choose the smallest runtime that can prove the first product journey honestly.",
                "choices": ["local CLI", "web app", "API service", "hybrid surface"],
                "impact": "Changes source paths, validation commands, deployment assumptions, and operator experience.",
            },
            {
                "id": "D4",
                "decision": "Proof bar",
                "recommended": "Require concrete behavior proof before any source-backed or release-ready claim.",
                "choices": ["unit proof", "contract proof", "browser proof", "scenario replay"],
                "impact": "Changes validation obligations, evidence maturity, and release promotion criteria.",
            },
            {
                "id": "D5",
                "decision": "First release ambition",
                "recommended": f"Keep {release} focused on one complete journey and defer broad platform capability.",
                "choices": ["one path", "one path plus audit", "one vertical slice", "multi-lane program"],
                "impact": "Changes backlog depth, component boundaries, wave count, and delivery risk.",
            },
        ],
        "customization_prompts": [
            f"Confirm the primary actor, first journey, and proof bar for the accepted project before writing records.",
            "Revise the external systems, source boundary, or release ambition before proposal apply if any assumption is wrong.",
            "Reject this proposal when the story does not match the business problem or first value path.",
        ],
        "pre_coding_checkpoints": [
            {
                "checkpoint": "Product story accepted",
                "operator_question": "Does the story match the business problem, first user, and first journey?",
                "done_when": "The accepted proposal names the product promise, first path, actors, systems, and non-goals.",
            },
            {
                "checkpoint": "Governance topology aligned",
                "operator_question": "Do workstreams, components, diagrams, release plan, and proof all describe the same project?",
                "done_when": "Workstreams, components, diagrams, release, and validation records share one topology spine.",
            },
            {
                "checkpoint": "Evidence boundary explicit",
                "operator_question": "Which claims are user intent, assumptions, source backed, validated, or operational?",
                "done_when": "Every major claim has a visible evidence tier and unresolved claims remain blocked.",
            },
            {
                "checkpoint": "Implementation lane ready",
                "operator_question": "Which child workstream can start source work without broadening the project?",
                "done_when": "The first child lane has source paths, owners, tests, rollback or recovery posture, and proof commands.",
            },
        ],
        "coding_readiness_gates": [
            f"{title} has an accepted product story with actors, systems, first path, and unresolved assumptions.",
            "The first implementation lane maps to one workstream, one component boundary, one diagram path, and one proof gate.",
            "Every external dependency is fixture-backed, sandboxed, source-backed, or explicitly deferred before source edits start.",
            "The release plan names promotion criteria and does not claim production readiness beyond the accepted first path.",
        ],
        "host_independent_paths": [
            {
                "path": "Confirm product intent",
                "command": f"odylith greenfield propose --repo-root . --prompt {json.dumps(prompt)}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use before proposal expansion so the operator can confirm, edit, or reject the interpretation.",
            },
            {
                "path": "Compile create transaction",
                "command": f"odylith greenfield compile-transaction --repo-root . --prompt {json.dumps(prompt)} --intent-file .odylith/runtime/greenfield/confirmed-intent.md --output .odylith/runtime/greenfield/product-create-transaction.v1.json --release {release}",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use after intent confirmation so Odylith builds, repairs, validates, gates, and hashes the complete create transaction before writes.",
            },
            {
                "path": "Commit confirmed transaction",
                "command": "odylith greenfield create --repo-root . --transaction-file .odylith/runtime/greenfield/product-create-transaction.v1.json --transaction-hash <hash> --confirm",
                "works_in": "shell, Codex, Claude Code",
                "use_when": "Use after hash confirmation so Odylith verifies and commits the already compiled package.",
            },
        ],
    }


def _host_project_intelligence(*, title: str, release: str) -> dict[str, object]:
    layers = {
        key: [
            f"{key.replace('_', ' ').title()} row one keeps {title} tied to the accepted product story and source boundary.",
            f"{key.replace('_', ' ').title()} row two names the owner, evidence tier, and invalidation trigger for the release.",
        ]
        for key in PROJECT_INTELLIGENCE_LAYERS
    }
    layers["intent"].append(f"Intent row three states the first complete path for the accepted project before broad platform scope.")
    layers["ontology"].append(f"Ontology row three keeps user, state object, evidence record, and release gate distinct for the accepted project.")
    layers["operators"].append(f"Operators row three allows promotion only after validation proof and topology refresh pass.")
    layers["validation_obligations"].append(f"Validation row three blocks release movement when source, fixture, or diagram proof is missing.")
    layers["topology"].append(f"Topology row three links backlog, components, diagrams, release plan, and proof artifacts together.")
    return {
        "schema_version": "odylith.greenfield.project_intelligence.v1",
        "purpose": f"Make {title} readable and governable as one product spine before any generated artifact drives implementation.",
        "coding_posture": "Coding starts only after the accepted project story, first child workstream, component boundary, source paths, and validation commands agree.",
        "control_surface_summary": [
            f"{title} begins as user intent and must not claim source-backed behavior until implementation proof exists.",
            "Backlog records carry product workstreams and the first implementation lane.",
            "Component records carry ownership, interfaces, invariants, and proof obligations.",
            "Diagram records carry topology, state movement, handoffs, controls, and evidence boundaries.",
            f"Release {release} carries only the first path that has accepted validation criteria.",
        ],
        "customization_flow": [
            "Confirm the product story and material ambiguities before proposal expansion.",
            "Review the confirmed proposal for actors, systems, topology, risks, and proof.",
            "Create accepted records only after deterministic validation and the governed write gate pass.",
            "Start source work only from the accepted child lane with source paths and proof commands.",
        ],
        **layers,
    }


def _host_domain_intelligence(*, title: str, row_title: str, actors: list[str] | None = None) -> dict[str, object]:
    return {
        "schema_version": "odylith.greenfield.workstream_intelligence.v1",
        "family": "host_reasoned_project",
        "summary": f"{row_title} comes from the accepted project story, with proof and topology kept explicit.",
        "actors": actors or _host_actor_lines_for_prompt(title),
        "intent": [
            f"{row_title} expresses a specific part of the accepted product story for the accepted project.",
            "The row must preserve user value, source boundary, proof gate, and unresolved assumptions.",
        ],
        "scope": [
            f"{row_title} owns its named project slice and does not expand into unrelated implementation scope.",
            "The boundary stays user-intent until source paths, tests, and refreshed evidence exist.",
        ],
        "ontology": [
            f"Actor: the person or team whose job this workstream must make successful for the accepted project.",
            "State object: the project object that changes through the first accepted journey.",
            "Evidence record: the proof artifact that decides whether the claim can advance.",
            "Release gate: the condition that blocks promotion when proof or ownership is missing.",
        ],
        "state": [
            f"Current state is accepted proposal intent for {row_title}, not implementation evidence.",
            "Desired state is source-backed proof with matching workstream, component, diagram, and release records.",
        ],
        "operators": [
            "Accept product intent only after the operator confirms story, actors, systems, and assumptions.",
            "Open implementation work only after the child lane names source paths and proof commands.",
            "Promote evidence only after validation passes and generated surfaces refresh from source truth.",
        ],
        "constraints": [
            "Do not claim production readiness, operational maturity, or source-backed behavior from proposal prose.",
            "Do not let diagrams, components, or releases drift away from the accepted product story.",
        ],
        "source_of_truth_map": [
            "Backlog records own workstream intent, priority, dependencies, risks, and success metrics for this row.",
            "Component records own boundaries, interfaces, invariants, and proof obligations connected to this row.",
            "Diagram records own topology views and must stay linked to the row and component ownership.",
        ],
        "evidence_model": [
            "User intent supports proposal truth but not source-backed implementation claims.",
            "Source-backed evidence requires files, tests, renders, or explicit operational records.",
        ],
        "decisions": [
            "The first decision is whether the operator accepts the story and first path.",
            "The next decision is which child workstream can safely start implementation planning.",
        ],
        "assumptions": [
            "Unanswered product choices remain visible and cannot silently become implementation facts.",
            "External systems are deferred or fixture-backed unless the proposal explicitly proves otherwise.",
        ],
        "topology": [
            f"{row_title} must connect to the project story, component ownership, diagram views, and release proof.",
            "Workstream, component, diagram, validation, and release records form one topology spine.",
        ],
        "invariants": [
            "Every source-backed claim must name its source path or proof artifact.",
            "Every component boundary must have owner, interface, failure mode, and validation obligation.",
        ],
        "risks": [
            "Generic workstream language can hide the real business problem and confuse implementation owners.",
            "Unbound artifacts can make implementation appear ready while the first path remains unproven.",
        ],
        "validation_obligations": [
            "Validate that the story, workstreams, components, diagrams, and release plan describe the same first path.",
            "Validate that missing proof blocks promotion instead of becoming a dashboard claim.",
            "Validate that source edits start only after a child technical plan names paths and tests.",
        ],
        "artifacts": [
            "Backlog row captures the native workstream contract for this slice.",
            "Component records capture ownership, interfaces, and proof obligations for this slice.",
            "Diagram records capture topology and flow claims that reviewers can inspect.",
        ],
        "authority": [
            "The operator owns accepted product intent and any correction to assumptions.",
            "The implementation owner owns source paths only after technical planning is accepted.",
        ],
        "owners": [
            "Product owner owns whether this row still matches the project story.",
            "Proof owner owns whether validation evidence is strong enough to promote the claim.",
        ],
        "execution_memory": [
            "Future agents must start from the accepted story and topology before editing source.",
            "Past proposal prose does not outrank source-backed proof or explicit operator corrections.",
        ],
        "metrics": [
            "Zero orphaned workstreams, components, diagrams, or release gates after apply.",
            "Every first-path claim has a visible evidence tier and validation obligation.",
        ],
        "change_model": [
            "Changing the first path invalidates dependent workstreams, components, diagrams, and release criteria.",
            "Changing an external dependency invalidates source boundary, risk, proof, and topology claims.",
        ],
        "invalidation_rules": [
            "If source proof is missing, the claim stays user-intent or assumption rather than source-backed.",
            "If operator corrections contradict the proposal, governance artifacts must be regenerated or repaired.",
        ],
        "conflict_model": [
            "Accepted product intent beats generated fallback language.",
            "Source-backed tests beat generated dashboard projections when they disagree.",
        ],
        "transfer_priors": [
            "Keep the first path small enough to prove with concrete validation.",
            "Prefer artifact-native enrichment over dumping generic domain-intelligence sections everywhere.",
        ],
    }


def _host_reasoned_recipe_legacy_shape() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "greenfield",
        "intent": {
            "title": "Recipe-sharing app",
            "summary": "A web app where home cooks publish, browse, and search recipes.",
        },
        "observed_source": {"evidence_tier": "docs_only", "notes": "Empty repo."},
        "assumptions": ["Web-first delivery.", "Relational data store."],
        "open_questions": ["Which runtime should own the first implementation?"],
        "risks": ["Photo upload can expand scope if it is pulled into the first release."],
        "security_compliance": {
            "domain": "Recipe-sharing consumer app with account, recipe visibility, comments, and user-generated content policy risk.",
            "security": "Security posture covers auth sessions, ownership checks, private edits, abuse prevention, and moderation hooks.",
            "policy": "Privacy, public publishing, data retention, accessibility, and moderation policy must be explicit before implementation.",
        },
        "validation_strategy": {
            "release_gate": ["Golden path from sign-up to recipe detail must pass."],
        },
        "program": {
            "waves": [
                {
                    "id": "W1",
                    "title": "Core authoring and browsing",
                    "goal": "Ship account, authoring, browsing, and shared UI shell.",
                    "release": "0.0.1",
                    "workstreams": ["WS-01", "WS-02", "WS-03"],
                },
                {
                    "id": "W2",
                    "title": "Social layer",
                    "goal": "Add favorites and comments after the first release is stable.",
                    "release": "0.1.0",
                    "workstreams": ["WS-04"],
                },
            ]
        },
        "release_plan": [
            {
                "release": "0.0.1",
                "label": "Recipe-sharing 0.0.1",
                "first_target_workstreams": ["WS-01", "WS-02", "WS-03"],
                "exit_criteria": "Golden-path browser E2E, HTTP contract tests, and architecture render proof all pass.",
            },
            {
                "release": "0.1.0",
                "label": "Social layer",
                "first_target_workstreams": ["WS-04"],
                "exit_criteria": "Favorite and comment flows pass with moderation hooks.",
            },
        ],
        "backlog": [
            {
                "id": "WS-00",
                "title": "Recipe-sharing app program",
                "problem": "The repo has no confirmed program, release target, component boundaries, topology, or proof gates.",
                "customer": "Cooks",
                "opportunity": "Create a governed recipe-sharing plan with explicit first release behavior and proof.",
                "product_view": "A browser app where cooks can sign in, publish recipes, browse, and search.",
                "recommended_first_slice": "Create the first governed release lane for accounts, recipe authoring, browsing, and UI shell.",
                "success_metrics": [
                    "First release target includes the wave-one workstreams.",
                    "Component and architecture records are linked to the created workstreams.",
                ],
            },
            {
                "id": "WS-01",
                "title": "Accounts and sessions",
                "problem": "Recipes need an owner before authoring and private edits can be governed.",
                "customer": "Cooks",
                "opportunity": "Account sessions create the ownership claim used by every recipe write.",
                "product_view": "Users can sign up, sign in, sign out, and reach protected routes.",
                "first_slice_proof": "Sign-up, sign-in, sign-out, and protected-route access work in browser and contract tests.",
                "success_metrics": [
                    "Authentication contract tests pass for sign-up, sign-in, sign-out, and current-user endpoints.",
                    "Protected route returns 401 without a session and 200 with a valid session.",
                ],
                "component_focus": ["AccountService", "WebUI"],
                "related_diagram_slugs": ["system-context", "auth-sequence"],
                "dependencies": ["Relational user and session tables."],
                "interfaces": ["HTTP /auth/sign-up, /auth/sign-in, /auth/sign-out, and /auth/me."],
                "validation": ["Browser sign-up to protected route passes."],
            },
            {
                "id": "WS-02",
                "title": "Recipe authoring CRUD",
                "problem": "Signed-in cooks need a safe way to create and edit their own recipes.",
                "customer": "Cooks",
                "opportunity": "Recipe authoring gives the product its durable content spine.",
                "product_view": "Authenticated CRUD over recipes with ingredients, steps, and tags.",
                "first_slice_proof": "A signed-in user creates, edits, and deletes only their own recipe.",
                "success_metrics": [
                    "Recipe CRUD contract tests pass for create, read, update, and delete.",
                    "Cross-user edit and delete attempts return 403.",
                ],
                "component_focus": ["RecipeStore", "AccountService", "WebUI"],
                "related_diagram_slugs": ["system-context", "recipe-domain-er"],
                "dependencies": ["Accounts and sessions must provide ownership claims."],
                "interfaces": ["HTTP /recipes and /recipes/{id} CRUD endpoints."],
                "validation": ["Ownership and CRUD tests pass."],
            },
            {
                "id": "WS-03",
                "title": "Recipe browsing and search",
                "problem": "Anonymous visitors need a way to discover recipes that have been published.",
                "customer": "Readers",
                "opportunity": "Browsing and title search make the first release useful without social features.",
                "product_view": "Anonymous list, detail, pagination, and title-substring search over recipes.",
                "first_slice_proof": "Visitor searches by title and opens a recipe detail page.",
                "success_metrics": [
                    "List, detail, pagination, and search contract tests pass.",
                    "Browser search-to-detail flow passes with seeded data.",
                ],
                "component_focus": ["RecipeStore", "WebUI"],
                "related_diagram_slugs": ["system-context", "recipe-domain-er"],
                "dependencies": ["Recipe authoring seeds published recipe data."],
                "interfaces": ["HTTP /recipes list and search plus /recipes/{id} detail."],
                "validation": ["Browser search-to-detail flow passes."],
            },
            {
                "id": "WS-04",
                "title": "Favorites and comments",
                "problem": "The product needs social signals after the first release is stable.",
                "customer": "Cooks",
                "opportunity": "Favorites and comments create lightweight engagement without disrupting release 0.0.1.",
                "product_view": "Users favorite recipes and comment with moderation hooks.",
                "first_slice_proof": "A user favorites a recipe and comments on it.",
                "success_metrics": [
                    "Favorite contract tests pass.",
                    "Comment moderation smoke test passes.",
                ],
                "component_focus": ["SocialGraph", "WebUI"],
                "related_diagram_slugs": ["system-context"],
                "dependencies": ["Accounts, recipes, and browsing are already live."],
                "interfaces": ["HTTP /favorites and /comments endpoints."],
                "validation": ["Favorite and comment browser path passes."],
            },
        ],
        "components": [
            {
                "id": "AccountService",
                "label": "AccountService",
                "kind": "service",
                "intended_path": "src/services/account_service",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own identity, credentials, sessions, and ownership claims for recipe writes.",
                "boundary": "Identity, credentials, sessions, and user ownership claims only.",
                "interfaces": ["HTTP /auth endpoints and internal session validation."],
                "dependencies": ["Relational data store and password hashing library."],
                "proof_expectations": ["Auth contract tests and session expiry tests pass."],
            },
            {
                "id": "RecipeStore",
                "label": "RecipeStore",
                "kind": "service",
                "intended_path": "src/services/recipe_store",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own recipe persistence, ownership enforcement, ingredients, steps, and tags.",
                "boundary": "Recipe CRUD, child recipe rows, and ownership-scoped writes.",
                "interfaces": ["HTTP /recipes CRUD and read interfaces."],
                "dependencies": ["AccountService ownership claims and relational data store."],
                "proof_expectations": ["CRUD, ownership, and schema migration tests pass."],
            },
            {
                "id": "WebUI",
                "label": "WebUI",
                "kind": "ui",
                "intended_path": "src/web/ui",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own browser routes, forms, navigation, error states, and empty states.",
                "boundary": "Browser rendering and form interaction only; no persistence ownership.",
                "interfaces": ["Browser routes for auth, recipes, search, and future social flows."],
                "dependencies": ["AccountService and RecipeStore HTTP interfaces."],
                "proof_expectations": ["Headless browser normal, empty, and error state matrix passes."],
            },
            {
                "id": "SocialGraph",
                "label": "SocialGraph",
                "kind": "service",
                "intended_path": "src/services/social_graph",
                "qualification": "greenfield",
                "status": "planned",
                "responsibility": "Own favorites, comments, social engagement state, and moderation hooks.",
                "boundary": "Social edges, comments, and moderation records only.",
                "interfaces": ["HTTP /favorites and /comments endpoints."],
                "dependencies": ["AccountService users and RecipeStore recipe identifiers."],
                "proof_expectations": ["Favorite, comment, and moderation hook tests pass."],
            },
        ],
        "diagrams": [
            {
                "slug": "system-context",
                "title": "Recipe system context",
                "type": "flowchart",
                "summary": "Top-level flow between browser, services, and data store.",
                "related_workstreams": ["WS-01", "WS-02", "WS-03", "WS-04"],
                "related_components": ["AccountService", "RecipeStore", "WebUI", "SocialGraph"],
                "mermaid_source": (
                    "flowchart LR\n"
                    "  User[Home cook<br/>browser] --> WebUI[WebUI<br/>routes]\n"
                    "  WebUI --> Account[AccountService<br/>sessions]\n"
                    "  WebUI --> Store[RecipeStore<br/>recipe CRUD]\n"
                    "  WebUI --> Social[SocialGraph<br/>favorites]\n"
                    "  Store --> DB[(Relational store)]\n"
                    "  Account --> DB\n"
                    "  Social --> DB\n"
                    "  classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A;\n"
                    "  classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
                    "  classDef data fill:#ECFDFB,stroke:#A7E9E3,color:#17233A;\n"
                    "  class User actor;\n"
                    "  class WebUI,Account,Store,Social service;\n"
                    "  class DB data;\n"
                ),
            },
            {
                "slug": "auth-sequence",
                "title": "Authentication sequence",
                "type": "sequenceDiagram",
                "summary": "Sign-in path through browser, WebUI, AccountService, and data store.",
                "related_workstreams": ["WS-01"],
                "related_components": ["AccountService", "WebUI"],
                "mermaid_source": (
                    "sequenceDiagram\n"
                    "  participant U as Browser\n"
                    "  participant W as WebUI\n"
                    "  participant A as AccountService\n"
                    "  U->>W: POST /sign-in\n"
                    "  W->>A: validate credentials\n"
                    "  A-->>W: session token\n"
                    "  W-->>U: Set-Cookie session; 302 /\n"
                ),
            },
            {
                "slug": "recipe-domain-er",
                "title": "Recipe domain ER",
                "type": "erDiagram",
                "summary": "Recipe ownership and child rows for ingredients, steps, and tags.",
                "related_workstreams": ["WS-02", "WS-03"],
                "related_components": ["RecipeStore"],
                "mermaid_source": (
                    "erDiagram\n"
                    "  USER ||--o{ RECIPE : authors\n"
                    "  RECIPE ||--|{ INGREDIENT : has\n"
                    "  RECIPE ||--|{ STEP : has\n"
                    "  RECIPE }o--o{ TAG : tagged_with\n"
                ),
            },
        ],
    }


def _host_reasoned_crispr_without_parent() -> dict[str, object]:
    return {
        "schema_version": 1,
        "mode": "host_reasoned_greenfield_proposal",
        "intent": {"title": "CRISPR Ethics Review App", "project_slug": "crispr-ethics-review-app"},
        "observed_source": {"summary": "No application source found."},
        "assumptions": ["Single-institution deployment.", "No PHI stored in the first release."],
        "open_questions": ["Are decisions advisory or legally binding later?"],
        "risks": ["DURC protocol details require strict access control and auditability."],
        "security_compliance": {
            "frameworks": ["NIH Guidelines for nucleic acid research.", "USG DURC oversight policy."],
            "scope": ["HIPAA not in 0.0.1 because no PHI is stored.", "WCAG 2.2 AA baseline."],
            "controls": ["Append-only decision ledger.", "Role and COI-aware authorization at read boundary."],
            "risk": "Domain risk centers on sensitive DURC protocol details, audit recovery, and access-control failure.",
        },
        "validation_strategy": ["Role matrix, FSM, ledger, audit, and browser proof gates must pass."],
        "program": {
            "waves": [
                {
                    "id": "W1",
                    "label": "Foundations",
                    "goal": "Prove attributable protocol review through a decision ledger.",
                    "validation_gate": "End-to-end protocol submit, transition, decision, and audit proof passes.",
                    "workstreams": ["WS-IA"],
                },
                {
                    "id": "W2",
                    "label": "Review intelligence",
                    "goal": "Add CRISPR-specific review workflow gates.",
                    "validation_gate": "FSM transition and DURC negative tests pass.",
                    "workstreams": ["WS-WORKFLOW"],
                },
            ]
        },
        "release_plan": {
            "selector": "0.0.1",
            "label": "0.0.1",
            "provisional_release_id": "release-crispr-ethics-0-0-1",
            "target_workstreams": ["WS-IA"],
            "promotion_criteria": ["First-wave authorization and audit gates pass."],
        },
        "backlog": [
            {
                "id": "WS-IA",
                "title": "Identity, sessions, and COI-aware authorization",
                "problem": "Reviewers with conflicts must be blocked at the API read boundary, not only in UI.",
                "customer": "Board chair, reviewers, PI submitters, admins, and regulator read-only users.",
                "opportunity": "Make COI a first-class authorization input before sensitive CRISPR packets exist.",
                "product_view": "Single authorize(actor, action, resource) choke point consumed by every component.",
                "recommended_first_slice": "PI can submit; conflicted reviewer cannot read; regulator can read but not write.",
                "success_metrics": [
                    "Every write endpoint routes through authorize(actor, action, resource) in CI instrumentation.",
                    "Zero conflicted reviewer reads succeed in the API role-matrix integration suite.",
                ],
                "component_focus": ["identity-access"],
                "related_diagram_slugs": ["atlas-topology"],
                "dependencies": ["Audit trail records COI declarations and session events."],
                "interfaces": ["authenticate, authorize, and declare_coi service contracts."],
                "validation": ["Role-matrix and COI negative tests pass at the API boundary."],
            },
            {
                "id": "WS-WORKFLOW",
                "title": "Review workflow phase state machine",
                "problem": "CRISPR reviews need legal transitions and explicit DURC gate enforcement.",
                "customer": "Board chair, reviewers, and auditors reconstructing phase history.",
                "opportunity": "Replace ad-hoc phase updates with deterministic, auditable workflow transitions.",
                "product_view": "Phase FSM exposes transition() and writes audit events for every legal transition.",
                "recommended_first_slice": "Protocol moves from intake through decision; illegal transitions are rejected.",
                "success_metrics": [
                    "Every phase mutation routes through transition() with no direct setter path.",
                    "Every illegal transition leaves state unchanged and returns a structured error.",
                ],
                "component_focus": ["review-workflow-engine"],
                "related_diagram_slugs": ["atlas-topology"],
                "dependencies": ["identity-access authorizes transitions; audit-trail records transition events."],
                "interfaces": ["transition and current_phase service contracts."],
                "validation": ["FSM legal and illegal transition tests pass."],
            },
        ],
        "components": [
            {
                "component_id": "identity-access",
                "label": "Identity Access",
                "kind": "service",
                "intended_path": "src/identity-access",
                "status": "planned",
                "qualification": "candidate",
                "responsibility": "Authentication, sessions, roles, and COI-aware authorization for all review data.",
                "boundary": "Owns identity and authorization checks; no downstream component can bypass authorize().",
                "dependencies": ["audit-trail records declaration events; persistence stores users and roles."],
                "interfaces": ["authenticate, authorize, and declare_coi service contracts."],
                "validation": ["Role-matrix, COI negative, and session-lifecycle tests."],
                "security_posture": ["Authorization enforced at API read boundary, not UI."],
            },
            {
                "component_id": "review-workflow-engine",
                "label": "Review Workflow Engine",
                "kind": "service",
                "intended_path": "src/review-workflow",
                "status": "planned",
                "qualification": "candidate",
                "responsibility": "Authorization-aware phase state machine for CRISPR protocol reviews.",
                "boundary": "Owns legal phase transitions and emits audit events for each transition.",
                "dependencies": ["identity-access authorizes transitions; audit-trail records transition events."],
                "interfaces": ["transition and current_phase service contracts."],
                "validation": ["FSM legal, illegal, idempotency, and authorization tests."],
            },
        ],
        "diagrams": [
            {
                "slug": "atlas-topology",
                "title": "CRISPR Review Topology",
                "kind": "flowchart",
                "summary": "Show authorization and workflow ownership for the first governed release.",
                "link_state": "atlas_first_draft",
                "related_workstreams": ["WS-IA", "WS-WORKFLOW"],
                "components": [
                    {"name": "identity-access", "description": "Auth, sessions, roles, and COI-aware authorization."},
                    {"name": "review-workflow-engine", "description": "Legal phase transitions and audit events."},
                ],
                "mermaid_source": (
                    "flowchart LR\n"
                    "  IA[\"identity-access<br/>COI-aware auth\"] --> WF[\"review-workflow-engine<br/>phase FSM\"]\n"
                    "  classDef auth fill:#eef9f1,stroke:#2f9e44,color:#163d22;\n"
                    "  classDef workflow fill:#f4f7ff,stroke:#3b5bdb,color:#1c2c5b;\n"
                    "  class IA auth;\n"
                    "  class WF workflow;\n"
                ),
            }
        ],
    }
