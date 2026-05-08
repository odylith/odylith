from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_transaction import GreenfieldApplyTransaction
from odylith.runtime.governance import backlog_authoring
from odylith.runtime.governance import build_traceability_graph
from odylith.runtime.governance import release_planning_view_model


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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


def _host_reasoned_ecommerce_proposal() -> dict[str, object]:
    return {
        "schema_version": "odylith.greenfield.proposal.v1",
        "mode": "host_reasoned_greenfield_proposal",
        "provider_calls": 0,
        "host_agnostic": True,
        "write_policy": "proposal_first_confirm_before_apply",
        "intent": {
            "prompt": "Build an ecommerce site",
            "title": "Commerce Launch System",
            "project_slug": "commerce-launch-system",
            "reasoning_mode": "host_model_reasoned",
            "evidence_tier": "user_intent",
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
            "strategy": "Promote only after checkout validation and refreshed governance surfaces.",
            "release_stages": [
                {"stage": "wave-1", "label": "Checkout spine", "release_gate": "Browser and recovery proof pass."},
            ],
            "target_workstream_titles": ["Define Storefront boundary"],
            "milestones": [
                {
                    "name": "Proposal accepted",
                    "exit_criteria": "Operator accepts assumptions, first slice, components, topology, and validation.",
                }
            ],
            "evidence_tier": "odylith_assumption",
        },
        "backlog": [
            {
                "title": "Govern Commerce Launch System",
                "problem": "The operator wants to build an ecommerce site, but the repo has no confirmed plan, boundaries, topology, or validation spine.",
                "customer": "Builders",
                "opportunity": "Create a confirmed commerce launch plan with a checkout-first implementation spine and explicit recovery gates.",
                "product_view": "Odylith should turn broad commerce intent into reviewable workstreams, components, topology, and release gates without claiming source exists.",
                "success_metrics": [
                    "The checkout spine has a parent workstream and first child boundary.",
                    "Candidate components are user_intent until source evidence exists.",
                    "Atlas carries distinct system-context and program-wave drafts.",
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
                "customer": "Builders",
                "opportunity": "Keep storefront behavior independently reviewable and testable.",
                "product_view": "Storefront should own browse, cart entry, checkout entry, and user-visible errors.",
                "success_metrics": [
                    "Storefront appears in Registry and Atlas with user_intent evidence.",
                    "Browse-to-cart entry has a first-slice validation gate before implementation.",
                ],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the route and state contract for browse-to-cart.",
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
                    "Catalog appears in Registry and Atlas with user_intent evidence.",
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
                "title": "Commerce Launch System Context",
                "kind": "flowchart",
                "summary": "Show shopper, storefront, checkout, order, payment, and governance boundaries.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {"name": "Storefront", "description": "Browse, cart, checkout entry, and user-visible errors."},
                    {"name": "Checkout Orchestrator", "description": "Payment handoff, order draft, and retry safety."},
                    {"name": "Catalog Boundary", "description": "Product, price, inventory, and merchandising review."},
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
                    "    subgraph governance_lane[\"Governance lane\"]\n"
                    "      governance[\"Odylith<br/>governance spine\"]\n"
                    "    end\n"
                    "    shopper --> storefront --> checkout\n"
                    "    checkout --> payment\n"
                    "    checkout --> order\n"
                    "    order --> governance\n"
                    "    payment -. failure recovery .-> checkout\n"
                    "    classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b,stroke-width:1px;\n"
                    "    classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f,stroke-width:1px;\n"
                    "    classDef evidence fill:#ffece7,stroke:#df8f7d,color:#5c2418,stroke-width:1px;\n"
                    "    class shopper,storefront actor;\n"
                    "    class checkout,payment,order service;\n"
                    "    class governance evidence;\n"
                    "    style experience_lane fill:#fafffe,stroke:#d8f2ed,stroke-width:1px,color:#062f2b\n"
                    "    style transaction_lane fill:#f9fcff,stroke:#dceaff,stroke-width:1px,color:#102f5f\n"
                    "    style governance_lane fill:#fff9f8,stroke:#f6d8d0,stroke-width:1px,color:#5c2418\n"
                ),
            },
            {
                "slug": "commerce-launch-program-waves",
                "title": "Commerce Launch Program Waves",
                "kind": "flowchart",
                "summary": "Show checkout spine, catalog integrity, payment recovery, and hardening waves.",
                "owner": "repo",
                "status": "draft",
                "link_state": "atlas_first_draft",
                "components": [
                    {"name": "Storefront", "description": "Browse-to-cart proof and shopper-facing route ownership."},
                    {"name": "Checkout Orchestrator", "description": "Payment recovery proof and order-state handoff."},
                    {"name": "Catalog Boundary", "description": "Price snapshot and inventory review ownership."},
                ],
                "related_workstream_titles": ["Govern Commerce Launch System", "Define Storefront boundary", "Define Catalog boundary"],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "timeline\n"
                    "    title Commerce Launch Program Waves\n"
                    "    Checkout spine : Browse-to-cart proof : Payment failure recovery\n"
                    "    Catalog integrity : Price snapshot rules : Inventory review\n"
                    "    Order reliability : Idempotent creation : Webhook replay proof\n"
                    "    Operational hardening : Observability : Release gate\n"
                ),
            },
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
                "exit_criteria": "Golden-path browser E2E, HTTP contract tests, and Atlas render proof all pass.",
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
                    "Registry and Atlas records are linked to the created workstreams.",
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
                    "  classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b;\n"
                    "  classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f;\n"
                    "  classDef data fill:#fff1ed,stroke:#df8f7d,color:#5c2418;\n"
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


def test_greenfield_prompt_returns_host_reasoning_contract(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Odylith, build an ecommerce site for me",
    )

    assert proposal["mode"] == "host_reasoned_proposal_request"
    assert proposal["provider_calls"] == 0
    assert proposal["host_agnostic"] is True
    assert proposal["intent"]["reasoning_mode"] == "host_model_required"
    assert proposal["classification"]["method"] == "open_world_host_reasoning"
    assert "catalog" not in proposal
    assert "backlog" not in proposal
    assert "components" not in proposal
    assert "diagrams" not in proposal
    assert proposal["observed_source"]["source_posture"] == "empty_or_no_app_source"
    assert "do not use canned domain buckets" in proposal["host_instruction"]
    assert "backlog" in proposal["reasoning_contract"]["required_top_level_keys"]
    assert "security_compliance" in proposal["reasoning_contract"]["required_top_level_keys"]
    assert "project_brief" in proposal["reasoning_contract"]["required_top_level_keys"]
    assert "project_intelligence" in proposal["reasoning_contract"]["required_top_level_keys"]
    activation_layers = [
        row["layer"]
        for row in proposal["reasoning_contract"]["engine_activation_layers"]
    ]
    assert activation_layers == [
        "context_engine",
        "execution_engine",
        "tribunal",
        "intervention_engine",
        "governance",
        "subagent_orchestration",
        "discipline",
        "surface_dags",
        "delivery",
        "analysis",
        "memory_substrate",
        "topology",
        "taxonomies_fsms",
        "greenfield_domain_intelligence",
        "overall_ux",
    ]
    assert "mermaid_source" in " ".join(proposal["reasoning_contract"]["quality_bar"])
    quality_bar = " ".join(proposal["reasoning_contract"]["quality_bar"])
    assert "colors inside the diagram" in quality_bar
    assert "never rely on viewer background treatment" in quality_bar
    assert "Tribunal gate" in quality_bar
    assert "Surface DAGs" in quality_bar
    assert "security, privacy, abuse, accessibility" in quality_bar
    assert "project-first" in quality_bar
    assert "odylith greenfield propose" in proposal["apply_commands"][1]
    assert "--release 0.0.1" in proposal["apply_commands"][2]
    assert "Default the first greenfield release target to exactly 0.0.1" in " ".join(
        proposal["reasoning_contract"]["quality_bar"]
    )
    assert "do not add project names or descriptive words to release targets" in proposal["host_instruction"]
    assert proposal["proposal_template"]["mode"] == "host_reasoned_greenfield_proposal"
    assert proposal["proposal_template"]["release_plan"]["label"] == "0.0.1"
    assert proposal["proposal_template"]["project_brief"]["customization_options"]
    assert proposal["proposal_template"]["project_intelligence"]["control_surface_summary"]
    assert "Do not start coding" in proposal["proposal_template"]["project_intelligence"]["coding_posture"]
    assert "Do not treat greenfield apply as permission to code immediately" in proposal["proposal_template"]["project_brief"]["operating_principle"]
    assert proposal["canonical_proposal_gate"]["status"] == "passed"
    greenfield_proposals.validate_host_reasoned_proposal(proposal["proposal_template"])
    assert greenfield_proposals.run_greenfield_tribunal(proposal["proposal_template"], release_selector="0.0.1").passed
    assert proposal["accepted_aliases"]["validation"] == ["proof_expectations", "test_strategy"]
    assert "project_control_surface" in proposal["accepted_aliases"]["project_intelligence"]


def test_greenfield_text_keeps_host_reasoning_and_no_write_boundary_visible(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Design a mathematics research workspace for spectral graph theory",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "apply-ready JSON: built, normalized, validated, Tribunal passed" in output
    assert "shared artifact: this text and `--format json` are rendered from the same canonical proposal" in output
    assert "No files changed." in output
    assert "mode: host_reasoned_greenfield_proposal" in output
    assert "active host reasoning required" not in output
    assert "Canonical apply JSON shape" not in output
    assert "odylith greenfield create --repo-root ." in output
    assert "odylith greenfield propose --repo-root ." in output
    assert "Project intelligence control surface" in output
    assert "Project-first blueprint" in output
    assert "choose before coding" in output
    assert output.index("Project intelligence control surface") < output.index("Project-first blueprint")
    assert output.index("Project-first blueprint") < output.index("Backlog proposal")
    assert "proposal Tribunal must pass before any source-truth writes" in output
    assert "Radar, Registry, Atlas, and Compass visible after writes" in output


def test_greenfield_cli_json_is_apply_ready_proposal(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Build a statistics notebook repo",
            "--format",
            "json",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["mode"] == "host_reasoned_greenfield_proposal"
    assert payload["provider_calls"] == 0
    assert payload["release_plan"]["selector"] == "0.0.1"
    assert payload["project_brief"]["customization_options"]
    assert payload["project_brief"]["coding_readiness_gates"]
    assert payload["project_intelligence"]["operators"]
    assert payload["project_intelligence"]["validation_obligations"]
    assert payload["project_intelligence"]["transfer_priors"]
    greenfield_proposals.validate_host_reasoned_proposal(payload)
    assert greenfield_proposals.run_greenfield_tribunal(payload, release_selector="0.0.1").passed


def test_defi_greenfield_workstreams_capture_domain_intelligence(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="DeFi risk sentinel app",
    )["proposal_template"]
    brief = proposal["project_brief"]

    workflow = next(row for row in proposal["backlog"] if row["title"] == "Define first operator workflow")
    intelligence = workflow["domain_intelligence"]
    rendered = greenfield_proposals.render_domain_intelligence_section(intelligence)
    project_intelligence = proposal["project_intelligence"]
    project_rendered = greenfield_proposals.render_project_intelligence_section(project_intelligence)

    assert "non-custodial DeFi risk sentinel" in project_rendered
    assert "No custody" in project_rendered
    assert intelligence["family"] == "defi_risk"
    assert "Risk subject" in rendered
    assert "Exposure snapshot" in rendered
    assert "stale oracle" in rendered
    assert "missing-indexer" in rendered
    assert "No live RPC" in rendered
    assert "financial advice" in rendered
    assert "idempotent acknowledgement" in rendered
    assert "source_of_truth_map" in intelligence
    assert "validation_obligations" in intelligence
    assert "conflict_model" in intelligence
    assert "transfer_priors" in intelligence
    assert "non-custodial" in json.dumps(brief)
    assert "first implementation plan" in " ".join(brief["coding_readiness_gates"]).casefold()
    assert "first operator-visible workflow" not in rendered.lower()
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_apply_writes_domain_intelligence_into_radar_specs(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="DeFi risk sentinel app",
    )["proposal_template"]

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    child_specs = [
        Path(row["idea_path"]).read_text(encoding="utf-8")
        for row in result["backlog"]
        if row["title"] != "Govern DeFi Risk Sentinel App"
    ]
    joined = "\n".join(child_specs)

    assert "## Domain Intelligence" in joined
    assert "### Domain Ontology" in joined
    assert "### Allowed Operators" in joined
    assert "### Source Of Truth Map" in joined
    assert "### Evidence Model" in joined
    assert "### Change Model" in joined
    assert "### Invalidation Rules" in joined
    assert "Risk subject: wallet, protocol, pool, strategy" in joined
    assert "No live RPC" in joined
    assert "stale oracle" in joined
    assert "liquidity shock" in joined
    assert "financial advice" in joined
    assert "title-only Radar items" in joined
    parent_spec = next(
        Path(row["idea_path"]).read_text(encoding="utf-8")
        for row in result["backlog"]
        if row["title"] == "Govern DeFi Risk Sentinel App"
    )
    assert "## Project Intelligence" in parent_spec
    assert "### Operators" in parent_spec
    assert "### Conflicts" in parent_spec
    assert "Do not start coding from the proposal closeout" in parent_spec


def test_greenfield_normalization_enriches_legacy_proposals_with_domain_intelligence() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_ecommerce_proposal())
    child = next(row for row in proposal["backlog"] if row["title"] == "Define Storefront boundary")
    intelligence = child["domain_intelligence"]
    rendered = greenfield_proposals.render_domain_intelligence_section(intelligence)
    brief = proposal["project_brief"]
    project_intelligence = proposal["project_intelligence"]

    assert intelligence["family"] == "commerce"
    assert "Shopper" in rendered
    assert "Payment callback" in rendered
    assert "idempotent" in rendered
    assert "failed payment" in rendered
    assert "Payment and order recovery model" in json.dumps(brief)
    assert len(brief["customization_options"]) >= 6
    assert len(brief["coding_readiness_gates"]) >= 4
    assert "Payment callback" in "\n".join(project_intelligence["ontology"])
    assert len(project_intelligence["change_model"]) >= 2
    greenfield_proposals.validate_host_reasoned_proposal(proposal)


def test_greenfield_normalization_enriches_transcript_dependency_gaps() -> None:
    proposal = _host_reasoned_crispr_without_parent()
    proposal["backlog"][0].pop("dependencies")
    proposal["backlog"][0].pop("interfaces")
    proposal["components"][0]["dependencies"] = []

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    identity = next(row for row in normalized["backlog"] if row.get("id") == "WS-IA")
    component = next(row for row in normalized["components"] if row.get("component_id") == "identity-access")

    assert identity["dependencies"]
    assert identity["interfaces"]
    assert "planned boundary" in identity["dependencies"][0]
    assert component["dependencies"]
    assert "No upstream component dependency is claimed" in component["dependencies"][0]


def test_greenfield_normalization_compacts_verbose_release_plan_label_to_selector() -> None:
    proposal = greenfield_proposals.normalize_host_reasoned_proposal(_host_reasoned_recipe_legacy_shape())

    assert proposal["release_plan"]["selector"] == "0.0.1"
    assert proposal["release_plan"]["label"] == "0.0.1"


def test_greenfield_normalization_splits_scalar_quality_fields() -> None:
    proposal = _host_reasoned_crispr_without_parent()
    identity = proposal["backlog"][0]
    identity["success_metrics"] = (
        "Authorization coverage measured by endpoint instrumentation; "
        "COI access blocking measured by role-matrix integration tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Role matrix proof passes at the API boundary.",
        "COI negative proof blocks conflicted reads.",
    ]
    proposal["release_plan"]["target_workstreams"] = "WS-IA, WS-WORKFLOW"
    proposal["program"]["waves"][0].pop("validation_gate")
    proposal["program"]["waves"][0]["validation"] = [
        "End-to-end protocol proof passes",
        "Audit completeness proof passes",
    ]

    normalized = greenfield_proposals.normalize_host_reasoned_proposal(proposal)
    normalized_identity = next(
        row for row in normalized["backlog"] if row.get("id") == "WS-IA"
    )
    tribunal = greenfield_proposals.run_greenfield_tribunal(normalized, release_selector="0.0.1")

    assert normalized_identity["success_metrics"] == [
        "Authorization coverage measured by endpoint instrumentation",
        "COI access blocking measured by role-matrix integration tests",
    ]
    assert normalized_identity["recommended_first_slice"] == (
        "Role matrix proof passes at the API boundary. COI negative proof blocks conflicted reads."
    )
    assert normalized["release_plan"]["target_workstreams"] == ["WS-IA", "WS-WORKFLOW"]
    assert normalized["program"]["waves"][0]["validation_gate"] == (
        "End-to-end protocol proof passes; Audit completeness proof passes"
    )
    assert "['" not in normalized_identity["recommended_first_slice"]
    assert "['" not in normalized["program"]["waves"][0]["validation_gate"]
    greenfield_proposals.validate_host_reasoned_proposal(normalized)
    assert tribunal.passed


def test_greenfield_apply_scalar_wave_validation_dedupes_handoff_gates(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_crispr_without_parent()
    identity = proposal["backlog"][0]
    identity["success_metrics"] = (
        "Authorization coverage measured by endpoint instrumentation; "
        "COI access blocking measured by role-matrix integration tests"
    )
    identity.pop("recommended_first_slice")
    identity["validation"] = [
        "Role matrix proof passes at the API boundary",
        "COI negative proof blocks conflicted reads",
    ]
    proposal["program"]["waves"][0].pop("validation_gate")
    proposal["program"]["waves"][0]["validation"] = [
        "End-to-end protocol proof passes",
        "Audit completeness proof passes",
    ]

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )
    first_wave = result["program"]["waves"][0]
    joined_wave_gate = "End-to-end protocol proof passes; Audit completeness proof passes"

    assert first_wave["exit_gate"] == joined_wave_gate
    assert first_wave["validation"] == [
        "End-to-end protocol proof passes",
        "Audit completeness proof passes",
    ]
    assert joined_wave_gate not in result["next_steps"]["validation_gates"]
    assert result["next_steps"]["validation_gates"][-2:] == first_wave["validation"]


def test_greenfield_release_target_label_extracts_numeric_selector_from_custom_text() -> None:
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("Recipe-sharing 0.0.1") == "0.0.1"
    assert greenfield_proposals.greenfield_programs.compact_release_target_label("launch candidate release target") == (
        "launch candidat..."
    )


def test_greenfield_apply_rejects_shallow_child_backlog_metrics(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1]["success_metrics"] = ["Registry linked."]

    with pytest.raises(ValueError, match="at least two success_metrics"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_reports_validation_issues_in_one_batch(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("problem")
    proposal["backlog"][2]["success_metrics"] = ["Too shallow."]
    proposal["components"][0]["responsibility"] = "UI"

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )

    message = str(excinfo.value)
    assert "greenfield proposal validation failed with" in message
    assert "backlog row 2 `problem` must be non-empty" in message
    assert "backlog row 3 must include at least two success_metrics" in message
    assert "component row 1 `responsibility` must contain at least 6 meaningful words" in message
    assert "auto-enrichment:" in message
    assert "needs operator/proposal input:" in message


def test_greenfield_validation_rejects_missing_project_first_brief(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="robot swarm logistics app",
    )["proposal_template"]
    proposal.pop("project_brief")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_brief` must be an object" in str(excinfo.value)


def test_greenfield_validation_rejects_missing_project_intelligence(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="robot swarm logistics app",
    )["proposal_template"]
    proposal.pop("project_intelligence")

    with pytest.raises(ValueError) as excinfo:
        greenfield_proposals.validate_host_reasoned_proposal(proposal)

    assert "proposal `project_intelligence` must be an object" in str(excinfo.value)


def test_robot_swarm_project_brief_blocks_coding_rush(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="robot swarm logistics app",
    )["proposal_template"]
    brief = proposal["project_brief"]
    rendered = greenfield_proposals.format_proposal_text(proposal)

    assert "Simulation and hardware boundary" in json.dumps(brief)
    assert "safety envelope" in json.dumps(brief)
    assert "Project intelligence control surface" in rendered
    assert "Do not treat greenfield apply as permission to code immediately" in rendered
    assert rendered.index("Project intelligence control surface") < rendered.index("Project-first blueprint")
    assert rendered.index("Project-first blueprint") < rendered.index("Backlog proposal")
    assert "host-independent customization paths" in rendered


def test_greenfield_apply_rejects_shallow_component_responsibility(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["components"][0]["responsibility"] = "UI stuff."

    with pytest.raises(ValueError, match="responsibility"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_missing_security_compliance_posture(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal.pop("security_compliance")

    with pytest.raises(ValueError, match="security_compliance"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_backlog_overrides_preserve_child_specific_sections() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    child = next(row for row in proposal["backlog"] if row["title"].startswith("Define "))
    args = argparse.Namespace(
        problem="parent",
        customer="parent",
        opportunity="parent",
        product_view="parent",
        success_metrics="parent",
        domain_risk="parent domain risk",
        security_posture="parent security posture",
        priority="P1",
        sizing="M",
        complexity="Medium",
        ordering_rationale="parent",
        section_overrides_by_title=greenfield_proposals._backlog_section_overrides(proposal),
    )

    resolved = backlog_authoring._title_specific_args(title=child["title"], args=args)

    assert resolved.problem == child["problem"]
    assert resolved.product_view == child["product_view"]
    assert child["success_metrics"][0] in resolved.success_metrics


def test_greenfield_apply_bootstraps_first_release_selector(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    refresh_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        greenfield_proposals.owned_surface_refresh,
        "raise_for_failed_refreshes",
        lambda **kwargs: refresh_calls.append(dict(kwargs)),
    )
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["release_plan"].pop("selector")

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="",
    )

    registry = json.loads((tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8"))
    events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    system_context = (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").read_text(encoding="utf-8")
    program_waves = (tmp_path / "odylith/atlas/source/commerce-launch-program-waves.mmd").read_text(encoding="utf-8")
    execution_program = json.loads(
        (tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json").read_text(encoding="utf-8")
    )
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    parent_idea = Path(result["backlog"][0]["idea_path"]).read_text(encoding="utf-8")
    child_idea = Path(result["backlog"][1]["idea_path"]).read_text(encoding="utf-8")
    storefront_spec = (
        tmp_path / "odylith/registry/source/components/commerce-storefront/CURRENT_SPEC.md"
    ).read_text(encoding="utf-8")
    component_registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    assert result["release_bootstrap"]["created"] is True
    assert registry["aliases"]["0.0.1"] == "release-commerce-launch-first"
    assert registry["aliases"]["current"] == "release-commerce-launch-first"
    assert registry["releases"][0]["name"] == "0.0.1"
    assert len(result["backlog"]) == 3
    assert len(result["components"]) == 3
    assert len(result["diagrams"]) == 2
    assert result["tribunal"]["status"] == "passed"
    assert result["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass"]
    assert refresh_calls == [
        {
            "repo_root": tmp_path.resolve(),
            "surfaces": ("radar", "registry", "atlas", "compass"),
            "operation_label": "Greenfield apply dashboard visibility",
        }
    ]
    assert result["program"]["created"] is True
    assert result["program"]["umbrella_id"] == "B-001"
    assert len(result["program"]["waves"]) == 2
    assert result["program"]["waves"][0]["wave_id"] == "W1"
    assert result["program"]["waves"][0]["primary_workstreams"] == ["B-002"]
    assert result["program"]["waves"][1]["wave_id"] == "W2"
    assert result["program"]["waves"][1]["primary_workstreams"] == ["B-003"]
    assert execution_program["waves"][0]["label"] == "Checkout spine"
    assert execution_program["waves"][0]["primary_workstreams"] == ["B-002"]
    assert execution_program["waves"][1]["label"] == "Catalog integrity"
    assert execution_program["waves"][1]["primary_workstreams"] == ["B-003"]
    assert result["release_bootstrap"]["release"]["version"] == "0.0.1"
    assert result["release_bootstrap"]["release"]["tag"] == "v0.0.1"
    assert result["release_bootstrap"]["release"]["name"] == "0.0.1"
    assert result["release_target"]["workstream_ids"] == ["B-001", "B-002"]
    release_payload, release_errors, _release_state = release_planning_view_model.build_release_view_from_repo(
        repo_root=tmp_path,
        idea_specs=None,
    )
    assert release_errors == []
    assert release_payload["current_release"]["release_id"] == "release-commerce-launch-first"
    assert release_payload["current_release"]["display_label"] == "0.0.1"
    assert release_payload["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert build_traceability_graph.main(["--repo-root", str(tmp_path)]) == 0
    traceability_graph = json.loads((tmp_path / "odylith/radar/traceability-graph.v1.json").read_text(encoding="utf-8"))
    assert traceability_graph["current_release"]["release_id"] == "release-commerce-launch-first"
    assert traceability_graph["current_release"]["active_workstreams"] == ["B-001", "B-002"]
    assert result["backlog_topology"] == [
        Path(result["backlog"][0]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][1]["idea_path"]).relative_to(tmp_path).as_posix(),
        Path(result["backlog"][2]["idea_path"]).relative_to(tmp_path).as_posix(),
    ]
    assert "Payment sandbox" in system_context
    assert "Order reliability" in program_waves
    assert system_context != program_waves
    assert "related_diagram_ids: D-001,D-002" in parent_idea
    assert "related_diagram_ids: D-001,D-002" in child_idea
    assert "## Impacted Components" in child_idea
    assert "`commerce-storefront`" in child_idea
    assert any(result["backlog"][1]["idea_path"] in row["related_backlog"] for row in atlas_catalog["diagrams"])
    storefront = next(row for row in component_registry["components"] if row["component_id"] == "commerce-storefront")
    assert storefront["workstreams"] == ["B-002"]
    assert storefront["diagrams"] == []
    assert "responsible for Browse, cart entry, checkout entry, and user-facing errors" in storefront["what_it_is"]
    assert "Browse, cart entry, checkout entry, and user-facing errors" in storefront_spec
    assert "| Workstreams | `B-002` |" in storefront_spec
    assert "| Diagrams | none yet |" in storefront_spec
    assert "Browser smoke proof for browse-to-cart and failed-checkout messaging" in storefront_spec
    assert result["memory"]["recorded"] is True
    assert result["memory"]["event"]["source"] == "domain-intelligence"
    assert '"release_id": "release-commerce-launch-first"' in events


def test_greenfield_apply_normalizes_common_host_authored_recipe_shape(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_host_reasoned_recipe_legacy_shape(),
        confirm=True,
        release_selector="0.0.1",
    )

    component_registry = json.loads(
        (tmp_path / "odylith/registry/source/component_registry.v1.json").read_text(encoding="utf-8")
    )
    atlas_catalog = json.loads((tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json").read_text(encoding="utf-8"))
    assert result["tribunal"]["status"] == "passed"
    assert len(result["backlog"]) == 5
    assert result["program"]["waves"][0]["primary_workstreams"] == ["B-002", "B-003", "B-004"]
    assert result["release_target"]["workstream_ids"] == ["B-001", "B-002", "B-003", "B-004"]
    assert all(row["qualification"] == "candidate" for row in component_registry["components"])
    assert (tmp_path / "odylith/atlas/source/recipe-sharing-app-system-context.mmd").is_file()
    assert not (tmp_path / "odylith/atlas/source/system-context.mmd").exists()
    auth_sequence = (tmp_path / "odylith/atlas/source/recipe-sharing-app-auth-sequence.mmd").read_text(
        encoding="utf-8"
    )
    assert "Set-Cookie session and 302 /" in auth_sequence
    assert "Set-Cookie session; 302 /" not in auth_sequence
    assert {row["slug"] for row in atlas_catalog["diagrams"]} >= {
        "recipe-sharing-app-system-context",
        "recipe-sharing-app-auth-sequence",
        "recipe-sharing-app-recipe-domain-er",
    }


def test_greenfield_apply_synthesizes_parent_and_polishes_component_specs(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_host_reasoned_crispr_without_parent(),
        confirm=True,
        release_selector="0.0.1",
    )

    spec = (tmp_path / "odylith/registry/source/components/identity-access/CURRENT_SPEC.md").read_text(
        encoding="utf-8"
    )
    workflow_spec = (
        tmp_path / "odylith/registry/source/components/review-workflow-engine/CURRENT_SPEC.md"
    ).read_text(encoding="utf-8")
    execution_program = json.loads(
        (tmp_path / "odylith/radar/source/programs/B-001.execution-waves.v1.json").read_text(encoding="utf-8")
    )

    assert result["backlog"][0]["title"] == "Govern CRISPR Ethics Review App"
    assert result["program"]["umbrella_id"] == "B-001"
    assert result["program"]["waves"][0]["primary_workstreams"] == ["B-002"]
    assert result["program"]["waves"][1]["primary_workstreams"] == ["B-003"]
    assert execution_program["waves"][0]["primary_workstreams"] == ["B-002"]
    assert execution_program["waves"][0]["exit_gate"]
    assert execution_program["waves"][0]["validation"]
    assert result["release_target"]["workstream_ids"] == ["B-001", "B-002"]
    assert result["next_steps"]["project_workstream_id"] == "B-001"
    assert result["next_steps"]["start_workstream_id"] == "B-002"
    assert result["next_steps"]["first_wave"] == "Foundations"
    assert "Deepen B-001" in result["next_steps"]["project_first_prompt"]
    assert result["next_steps"]["customization_options"]
    assert result["next_steps"]["coding_readiness_gates"]
    assert "After project-first gates pass" in result["next_steps"]["implementation_prompt"]
    assert "Treat `Identity, sessions, and COI-aware authorization` as the first coding scope" in result["next_steps"]["implementation_prompt"]
    assert "## Component Snapshot" in spec
    assert "## Identity Access Runtime Boundary" in spec
    assert "## Identity Access First Runtime Slice" in spec
    assert "Use `B-002` (Identity, sessions, and COI-aware authorization) as the implementation-plan anchor" in spec
    assert (
        "Use `B-003` (Review workflow phase state machine) as the implementation-plan anchor"
        in workflow_spec
    )
    assert (
        "Use `B-002` (Identity, sessions, and COI-aware authorization) as the implementation-plan anchor"
        not in workflow_spec
    )
    assert "./.odylith/bin/odylith context --repo-root . B-003" in workflow_spec
    assert "First coding slice:" in spec
    assert "Definition Of Done" in spec
    assert "Operator Verification" in spec
    assert "Runtime Failure Modes" in spec
    assert "Authorization enforced at API read boundary, not UI" in spec
    assert "NIH Guidelines for nucleic acid research" not in spec
    assert "USG DURC oversight policy" not in spec
    assert "CRISPR Ethics Review App" not in spec
    assert "['" not in spec
    assert "']" not in spec
    assert "['" not in workflow_spec
    assert "']" not in workflow_spec


def test_greenfield_apply_writes_bespoke_domain_component_specs(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="DeFi risk sentinel app",
    )["canonical_proposal"]

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    spec_root = tmp_path / "odylith/registry/source/components"
    console_spec = (spec_root / "defi-risk-sentinel-app-risk-console/CURRENT_SPEC.md").read_text(encoding="utf-8")
    engine_spec = (spec_root / "defi-risk-sentinel-app-risk-signal-engine/CURRENT_SPEC.md").read_text(
        encoding="utf-8"
    )
    harness_spec = (spec_root / "defi-risk-sentinel-app-scenario-replay-harness/CURRENT_SPEC.md").read_text(
        encoding="utf-8"
    )

    assert result["tribunal"]["status"] == "passed"
    assert [row["label"] for row in proposal["components"]] == [
        "Risk Sentinel Console",
        "Risk Signal Engine",
        "Scenario Replay Harness",
    ]
    assert "wallet/protocol watchlist setup" in console_spec
    assert "stale oracle" in console_spec
    assert "| Workstreams | `B-002` |" in console_spec
    assert "| Diagrams | `D-002`, `D-003` |" in console_spec
    assert "Exposure snapshot query" in engine_spec
    assert "liquidity" in engine_spec
    assert "| Workstreams | `B-003` |" in engine_spec
    assert "| Diagrams | `D-002`, `D-003`, `D-004` |" in engine_spec
    assert "Use `B-003` (Define domain contract and ownership) as the implementation-plan anchor" in engine_spec
    assert "Use `B-002` (Define first operator workflow) as the implementation-plan anchor" not in engine_spec
    assert "Scenario runner command" in harness_spec
    assert "live chain calls" in harness_spec
    assert "| Workstreams | `B-004` |" in harness_spec
    assert "| Diagrams | `D-005` |" in harness_spec
    assert "Use `B-004` (Add release proof and operations harness) as the implementation-plan anchor" in harness_spec
    assert "## Risk Sentinel Console Interaction Boundary" in console_spec
    assert "## Risk Signal Engine Runtime Boundary" in engine_spec
    assert "## Scenario Replay Harness Proof Harness Boundary" not in harness_spec
    assert "## Scenario Replay Harness Proof Boundary" in harness_spec
    assert "Risk scoring math" in console_spec
    assert "Chain indexing" in console_spec
    assert "Presentation" in engine_spec
    assert "External notification delivery" in engine_spec
    assert "Production keys" in harness_spec
    assert "Real trade execution" in harness_spec
    for text in (console_spec, engine_spec, harness_spec):
        assert "Experience Boundary" not in text
        assert "registered through `odylith component register`" not in text
        assert "first operator-visible workflow, view or command entrypoint" not in text
        assert "Source-backed runtime behavior until implementation proof lands" not in text
        assert "Production readiness, storage ownership, or external-provider guarantees" not in text
        assert "Starting implementation without a named product spine" not in text
        assert "Security, privacy, accessibility, and operational risks can be under-modeled" not in text
        assert "Security posture starts with authentication or operator access boundaries" not in text
        assert "Policy posture tracks privacy, retention, accessibility" not in text
        assert "The first workstream has a technical plan" not in text
        assert "The workflow boundary appears in Registry and Atlas" not in text
        assert "| Diagrams | `D-001`" not in text
        assert "R1." not in text
        assert "odylith_assumption" not in text
    assert console_spec != engine_spec
    assert engine_spec != harness_spec


def test_greenfield_apply_cli_prints_operator_handoff(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_crispr_without_parent()), encoding="utf-8")

    rc = greenfield_proposals.main(
        ["apply", "--repo-root", str(tmp_path), "--proposal-file", str(proposal_path), "--confirm", "--release", "0.0.1"]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "- project-first workstream: B-001 Govern CRISPR Ethics Review App" in out
    assert "- current project lane: wave Foundations | release 0.0.1" in out
    assert "- choose before coding:" in out
    assert "- coding readiness gates:" in out
    assert "- eventual first coding workstream: B-002 Identity, sessions, and COI-aware authorization" in out
    assert "- operator handoff:" in out
    assert "./.odylith/bin/odylith validate plan-workstream-binding --repo-root ." in out


def test_greenfield_create_cli_owns_apply_ready_path(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "robot swarm logistics app",
            "--release",
            "0.0.1",
            "--confirm",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 0
    assert "odylith greenfield create wrote confirmed proposal" in out
    assert "- tribunal: passed" in out
    assert "- project-first workstream: B-001 Govern Robot Swarm Logistics App" in out
    assert "- next project prompt: Deepen B-001" in out
    assert "- eventual first coding workstream: B-002 Dispatch and observe one simulated logistics task" in out
    assert "- choose before coding:" in out
    assert "- coding readiness gates:" in out
    assert "Simulation and hardware boundary" in out
    assert "- validation already run:" in out
    assert "- created governance files:" in out
    assert "greenfield proposal validation failed" not in out
    assert "greenfield proposal Tribunal failed" not in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md"))


def test_greenfield_create_cli_requires_confirmation_before_writes(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "create",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "robot swarm logistics app",
            "--release",
            "0.0.1",
        ]
    )

    out = capsys.readouterr().out
    assert rc == 2
    assert "--confirm is required before greenfield apply writes governance records" in out
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not list((tmp_path / "odylith/atlas/source").glob("*.mmd"))


def test_greenfield_apply_namespaces_partial_project_diagram_slugs_before_scaffold(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    atlas_catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    atlas_catalog_path.write_text(
        json.dumps(
            {
                "schema_version": "odylith.diagrams.v1",
                "diagrams": [{"diagram_id": "D-001", "slug": "recipe-domain-er"}],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=_host_reasoned_recipe_legacy_shape(),
        confirm=True,
        release_selector="0.0.1",
    )

    atlas_catalog = json.loads(atlas_catalog_path.read_text(encoding="utf-8"))
    assert result["tribunal"]["status"] == "passed"
    assert "recipe-domain-er" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert "recipe-sharing-app-recipe-domain-er" in {row["slug"] for row in atlas_catalog["diagrams"]}
    assert (tmp_path / "odylith/atlas/source/recipe-sharing-app-recipe-domain-er.mmd").is_file()


def test_greenfield_apply_rolls_back_partial_writes_when_late_step_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_scaffold(**_kwargs: object) -> tuple[int, list[str]]:
        return 1, ["FAILED: synthetic scaffold failure"]

    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram, "scaffold_diagram", fail_scaffold)

    with pytest.raises(RuntimeError, match="synthetic scaffold failure"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert list((tmp_path / "odylith/radar/source/ideas").glob("**/*.md")) == []
    assert not (tmp_path / "odylith/radar/source/releases").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_apply_rolls_back_generated_surfaces_when_refresh_fails(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    original_index = (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8")

    def fail_refreshes(**_kwargs: object) -> None:
        _write(tmp_path / "odylith/radar/radar.html", "partial dashboard\n")
        _write(tmp_path / "odylith/runtime/delivery_intelligence.v4.json", "{}\n")
        raise RuntimeError("synthetic dashboard refresh failure")

    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", fail_refreshes)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)

    with pytest.raises(RuntimeError, match="synthetic dashboard refresh failure"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=True,
            release_selector="0.0.1",
        )

    assert (tmp_path / "odylith/radar/source/INDEX.md").read_text(encoding="utf-8") == original_index
    assert not (tmp_path / "odylith/radar/radar.html").exists()
    assert not (tmp_path / "odylith/runtime/delivery_intelligence.v4.json").exists()
    assert not (tmp_path / "odylith/registry/source/component_registry.v1.json").exists()
    assert not (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").exists()


def test_greenfield_transaction_restores_symlinked_snapshot_root_without_traversal(tmp_path) -> None:
    external_radar = tmp_path / "external-radar"
    external_radar.mkdir()
    _write(external_radar / "outside.md", "external truth\n")
    radar_link = tmp_path / "odylith/radar"
    radar_link.parent.mkdir(parents=True)
    try:
        radar_link.symlink_to(external_radar, target_is_directory=True)
    except OSError as exc:
        pytest.skip(f"directory symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            radar_link.unlink()
            _write(tmp_path / "odylith/radar/partial.md", "partial write\n")
            raise RuntimeError("synthetic failure")

    assert radar_link.is_symlink()
    assert radar_link.resolve() == external_radar.resolve()
    assert (external_radar / "outside.md").read_text(encoding="utf-8") == "external truth\n"
    assert not (tmp_path / "odylith/radar/partial.md").exists()


def test_greenfield_transaction_restores_nested_symlink_without_copying_target(tmp_path) -> None:
    radar_root = tmp_path / "odylith/radar"
    radar_root.mkdir(parents=True)
    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside\n", encoding="utf-8")
    nested_link = radar_root / "linked.txt"
    try:
        nested_link.symlink_to(outside_file)
    except OSError as exc:
        pytest.skip(f"file symlink unavailable: {exc}")

    with pytest.raises(RuntimeError, match="synthetic failure"):
        with GreenfieldApplyTransaction(tmp_path):
            nested_link.unlink()
            nested_link.write_text("regular replacement\n", encoding="utf-8")
            raise RuntimeError("synthetic failure")

    assert nested_link.is_symlink()
    assert nested_link.resolve() == outside_file.resolve()
    assert outside_file.read_text(encoding="utf-8") == "outside\n"


def test_greenfield_apply_requires_confirmation(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)

    with pytest.raises(ValueError, match="--confirm is required"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=False,
            release_selector="0.0.1",
        )


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    def noisy_refresh(**_kwargs: object) -> None:
        print("refresh progress that must not contaminate JSON stdout", flush=True)
        os.write(1, b"fd-level refresh progress must not contaminate JSON stdout\n")

    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", noisy_refresh)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(json.dumps(_host_reasoned_ecommerce_proposal()), encoding="utf-8")

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-file",
            str(proposal_path),
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "applied"
    assert payload["atlas_scaffold_logs"]
    assert payload["memory"]["recorded"] is True
    assert payload["memory"]["event"]["source"] == "domain-intelligence"
    assert payload["tribunal"]["status"] == "passed"
    assert payload["dashboard_refresh"]["surfaces"] == ["radar", "registry", "atlas", "compass"]
    assert payload["release_target"]["release_id"] == "release-commerce-launch-first"
    assert payload["operator_output"] == [
        "refresh progress that must not contaminate JSON stdout",
        "fd-level refresh progress must not contaminate JSON stdout",
    ]


def test_greenfield_apply_json_error_is_machine_clean(tmp_path, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)

    rc = greenfield_proposals.main(
        [
            "apply",
            "--repo-root",
            str(tmp_path),
            "--proposal-json",
            "{not-json",
            "--confirm",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 2
    assert payload["mode"] == "error"
    assert "Expecting property name enclosed in double quotes" in payload["error"]
