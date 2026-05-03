from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.governance import backlog_authoring


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
                "release_strategy": "Target the accepted first checkout slice to the provisional next release.",
                "recommended_wave_order": ["Checkout spine", "Catalog integrity", "Payment recovery", "Operational hardening"],
                "evidence_tier": "odylith_assumption",
            },
            "waves": [
                {
                    "wave": 1,
                    "label": "Checkout spine",
                    "goal": "Prove browse, cart, checkout handoff, and order draft.",
                    "validation": "Browser proof covers happy path and failed payment recovery.",
                    "component_focus": ["commerce-storefront", "commerce-checkout"],
                    "evidence_tier": "odylith_assumption",
                },
                {
                    "wave": 2,
                    "label": "Catalog integrity",
                    "goal": "Make product, price, inventory, and merchandising reviewable.",
                    "validation": "Price and inventory snapshot rules are explicit.",
                    "component_focus": ["commerce-catalog"],
                    "evidence_tier": "odylith_assumption",
                },
            ],
        },
        "release_plan": {
            "selector": "next",
            "label": "First governed commerce release",
            "provisional_release_id": "release-commerce-launch-first",
            "strategy": "Promote only after checkout validation and refreshed governance surfaces.",
            "release_stages": [
                {"stage": "wave-1", "label": "Checkout spine", "release_gate": "Browser and recovery proof pass."},
            ],
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
                "customer": "Product builders and future agent sessions that need shared commerce scope before implementation.",
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
                "customer": "Product builders and future agent sessions.",
                "opportunity": "Keep storefront behavior independently reviewable and testable.",
                "product_view": "Storefront should own browse, cart entry, checkout entry, and user-visible errors.",
                "success_metrics": ["Storefront appears in Registry and Atlas with user_intent evidence."],
                "priority": "P1",
                "sizing": "M",
                "complexity": "Medium",
                "recommended_first_slice": "Define the route and state contract for browse-to-cart.",
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
                ],
                "intended_paths": ["apps/web", "src/checkout"],
                "watch_paths": [],
                "evidence_tier": "user_intent",
                "mermaid_source": (
                    "flowchart LR\n"
                    "    shopper[Shopper]\n"
                    "    storefront[Storefront UI]\n"
                    "    checkout[Checkout orchestrator]\n"
                    "    payment[Payment sandbox]\n"
                    "    order[Order ledger]\n"
                    "    governance[Odylith governance spine]\n"
                    "    shopper --> storefront --> checkout\n"
                    "    checkout --> payment\n"
                    "    checkout --> order\n"
                    "    order --> governance\n"
                    "    payment -. failure recovery .-> checkout\n"
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
                    {"name": "Storefront", "description": "Browse-to-cart proof."},
                    {"name": "Checkout Orchestrator", "description": "Payment recovery proof."},
                ],
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
    assert "mermaid_source" in " ".join(proposal["reasoning_contract"]["quality_bar"])


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
    assert "host model reasoning required" in output
    assert "do not use canned domain buckets" in output
    assert "Evidence rules" in output
    assert "No files changed." in output


def test_greenfield_cli_json_is_host_reasoning_contract(tmp_path, capsys) -> None:
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
    assert payload["mode"] == "host_reasoned_proposal_request"
    assert payload["classification"]["method"] == "open_world_host_reasoning"
    assert payload["provider_calls"] == 0


def test_greenfield_atlas_sources_differ_by_host_reasoned_diagram_purpose() -> None:
    proposal = _host_reasoned_ecommerce_proposal()

    sources = {
        row["slug"]: row["mermaid_source"]
        for row in proposal["diagrams"]
    }

    context = sources["commerce-launch-system-context"]
    waves = sources["commerce-launch-program-waves"]
    assert context.startswith("flowchart LR")
    assert "Payment sandbox" in context
    assert waves.startswith("timeline")
    assert "Order reliability" in waves
    assert context != waves


def test_greenfield_apply_rejects_missing_host_authored_diagram_source(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0].pop("mermaid_source")

    with pytest.raises(ValueError, match="missing host-authored mermaid_source"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="next",
        )


def test_greenfield_apply_rejects_identical_diagram_sources(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][1]["mermaid_source"] = proposal["diagrams"][0]["mermaid_source"]

    with pytest.raises(ValueError, match="must not reuse identical Mermaid source"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="next",
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
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="next",
    )

    registry = json.loads((tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8"))
    events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    system_context = (tmp_path / "odylith/atlas/source/commerce-launch-system-context.mmd").read_text(encoding="utf-8")
    program_waves = (tmp_path / "odylith/atlas/source/commerce-launch-program-waves.mmd").read_text(encoding="utf-8")
    assert result["release_bootstrap"]["created"] is True
    assert registry["aliases"]["next"] == "release-commerce-launch-first"
    assert len(result["backlog"]) == 2
    assert len(result["components"]) == 2
    assert len(result["diagrams"]) == 2
    assert "Payment sandbox" in system_context
    assert "Order reliability" in program_waves
    assert system_context != program_waves
    assert result["memory"]["recorded"] is True
    assert result["memory"]["event"]["source"] == "domain-intelligence"
    assert '"release_id": "release-commerce-launch-first"' in events


def test_greenfield_apply_requires_confirmation(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)

    with pytest.raises(ValueError, match="--confirm is required"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=_host_reasoned_ecommerce_proposal(),
            confirm=False,
            release_selector="next",
        )


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
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
            "--release",
            "next",
            "--json",
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert rc == 0
    assert payload["mode"] == "applied"
    assert payload["atlas_scaffold_logs"]
    assert payload["memory"]["recorded"] is True
    assert payload["memory"]["event"]["source"] == "domain-intelligence"
