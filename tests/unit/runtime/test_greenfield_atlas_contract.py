from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence import greenfield_proposals
from tests.unit.runtime.test_greenfield_proposals import (
    _host_reasoned_ecommerce_proposal,
    _seed_empty_governance_repo,
)


def test_greenfield_apply_ready_scaffold_has_multi_view_architecture_suite(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build a statistics notebook repo",
    )["proposal_template"]

    diagram_slugs = {row["slug"] for row in proposal["diagrams"]}
    assert len(proposal["diagrams"]) == 5
    assert diagram_slugs == {
        "a-statistics-notebook-repo-system-overview",
        "a-statistics-notebook-repo-first-slice-flow",
        "a-statistics-notebook-repo-component-ownership-map",
        "a-statistics-notebook-repo-domain-state-model",
        "a-statistics-notebook-repo-validation-release-topology",
    }
    assert any(row["kind"] == "sequenceDiagram" for row in proposal["diagrams"])
    assert any(row["kind"] == "stateDiagram" for row in proposal["diagrams"])
    assert all(row["components"] for row in proposal["diagrams"])
    assert all(row.get("review_focus") for row in proposal["diagrams"])
    assert all(row.get("operator_question") for row in proposal["diagrams"])
    assert all(row.get("proof_gate") for row in proposal["diagrams"])
    assert [row["title"] for row in proposal["diagrams"]] == [
        "System Overview",
        "First Slice Flow",
        "Component Ownership Map",
        "Domain State Model",
        "Validation And Release Topology",
    ]
    _assert_greenfield_diagram_titles_are_view_names(proposal)
    sources = {row["slug"]: row["mermaid_source"] for row in proposal["diagrams"]}
    assert "Evidence boundary<br/>intent not source-backed" in sources["a-statistics-notebook-repo-system-overview"]
    assert "Code gate<br/>plan paths tests rollback" in sources["a-statistics-notebook-repo-system-overview"]
    assert "Note over Operator,Harness: Project review and direction choices happen before source edits" in sources["a-statistics-notebook-repo-first-slice-flow"]
    assert "Decision lens<br/>split by owner evidence risk gate" in sources["a-statistics-notebook-repo-component-ownership-map"]
    assert "Proposal state, not source proof" in sources["a-statistics-notebook-repo-domain-state-model"]
    assert "Blocked if risks<br/>or choices unresolved" in sources["a-statistics-notebook-repo-validation-release-topology"]
    _assert_greenfield_diagram_sources_do_not_model_odylith_surfaces(proposal)
    proposal_text = greenfield_proposals.format_proposal_text(proposal)
    _assert_greenfield_text_does_not_leak_odylith_surfaces(proposal_text)
    assert "review: Use this view to confirm the project spine" in proposal_text
    assert "question: Does this show the right first user" in proposal_text
    assert "gate: No source-backed claim until the first child plan" in proposal_text
    assert {
        "a-statistics-notebook-repo-component-ownership-map",
        "a-statistics-notebook-repo-domain-state-model",
        "a-statistics-notebook-repo-validation-release-topology",
    } <= set(proposal["backlog"][0]["related_diagram_slugs"])
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


def test_robot_swarm_greenfield_scaffold_expands_domain_specific_atlas_suite(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="robot swarm logistics app",
    )["proposal_template"]

    diagram_slugs = {row["slug"] for row in proposal["diagrams"]}
    assert len(proposal["diagrams"]) == 10
    assert {
        "robot-swarm-logistics-system-overview",
        "robot-swarm-logistics-first-slice-flow",
        "robot-swarm-logistics-component-ownership-map",
        "robot-swarm-logistics-domain-state-model",
        "robot-swarm-logistics-validation-release-topology",
        "robot-swarm-logistics-multi-robot-conflict",
        "robot-swarm-logistics-safety-envelope",
        "robot-swarm-logistics-telemetry-contract",
        "robot-swarm-logistics-deployment-boundaries",
        "robot-swarm-logistics-observability-audit-loop",
    } == diagram_slugs
    assert not any("-app-" in slug for slug in diagram_slugs)
    sources = {row["slug"]: row["mermaid_source"] for row in proposal["diagrams"]}
    assert {
        row["title"]
        for row in proposal["diagrams"]
    } == {
        "Simulation-First Architecture Overview",
        "Dispatch And Telemetry Flow",
        "Component Responsibility Map",
        "Robot Task State Machine",
        "Release Proof Topology",
        "Multi-Robot Conflict Resolution",
        "Safety Envelope And E-Stop Flow",
        "Telemetry Contract And Data Flow",
        "Cloud Edge Simulation Boundaries",
        "Observability And Audit Loop",
    }
    _assert_greenfield_diagram_titles_are_view_names(proposal)
    assert "bounded wait queued" in sources["robot-swarm-logistics-multi-robot-conflict"]
    assert "Hardware -. blocked until HIL proof .-> Agent" in sources["robot-swarm-logistics-deployment-boundaries"]
    assert "Release evidence<br/>normal degraded blocked" in sources["robot-swarm-logistics-observability-audit-loop"]
    _assert_greenfield_diagram_sources_do_not_model_odylith_surfaces(proposal)
    _assert_greenfield_text_does_not_leak_odylith_surfaces(greenfield_proposals.format_proposal_text(proposal))
    assert set(proposal["backlog"][0]["related_diagram_slugs"]) == diagram_slugs
    assert "robot-swarm-logistics-safety-envelope" in proposal["components"][1]["related_diagram_slugs"]
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


def _assert_greenfield_diagram_sources_do_not_model_odylith_surfaces(proposal: dict[str, object]) -> None:
    forbidden_tokens = (
        "Odylith",
        "Radar",
        "Registry",
        "Compass",
        "Surface refresh",
        "Surfaces",
    )
    for row in proposal["diagrams"]:
        source = str(row["mermaid_source"])
        for token in forbidden_tokens:
            assert token not in source, f"{row['slug']} leaked {token!r} into project topology"


def _assert_greenfield_diagram_titles_are_view_names(proposal: dict[str, object]) -> None:
    project_title = str(proposal["intent"]["title"])
    for row in proposal["diagrams"]:
        title = str(row["title"])
        assert not title.startswith(project_title), f"{row['slug']} repeated the project title"
        assert len(title.split()) <= 6, f"{row['slug']} title is not a concise architecture view name"


def _assert_greenfield_text_does_not_leak_odylith_surfaces(text: str) -> None:
    for token in (
        "Radar",
        "Registry",
        "Atlas",
        "Compass",
        "Odylith surfaces",
        "governance surfaces",
        "surface refresh",
        "refreshed surfaces",
    ):
        assert token not in text, f"proposal text leaked {token!r} into project review"


def test_greenfield_atlas_sources_differ_by_host_reasoned_diagram_purpose() -> None:
    proposal = _host_reasoned_ecommerce_proposal()

    sources = {
        row["slug"]: row["mermaid_source"]
        for row in proposal["diagrams"]
    }

    context = sources["commerce-launch-system-context"]
    waves = sources["commerce-launch-program-waves"]
    assert context.startswith("flowchart LR")
    assert "subgraph experience_lane" in context
    assert "classDef actor fill:" in context
    assert "Payment sandbox" in context
    assert waves.startswith("timeline")
    assert "Order reliability" in waves
    assert context != waves


def test_greenfield_tribunal_rejects_project_title_prefixed_diagram_titles() -> None:
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["title"] = f"{proposal['intent']['title']} System Context"

    decision = greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1")

    assert not decision.passed
    assert any("title must name the architecture view" in issue for issue in decision.issues)


def test_greenfield_apply_rejects_unstyled_flowchart_diagram_sources(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["mermaid_source"] = (
        "flowchart LR\n"
        "    shopper[Shopper]\n"
        "    checkout[Checkout]\n"
        "    shopper --> checkout\n"
    )

    with pytest.raises(ValueError, match="semantic classDef/style colors"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_allows_styled_flowchart_without_forced_lanes(tmp_path, monkeypatch) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["mermaid_source"] = (
        "flowchart LR\n"
        "    shopper[\"Shopper\"]\n"
        "    checkout[\"Checkout<br/>orchestrator\"]\n"
        "    payment[\"Payment sandbox\"]\n"
        "    shopper --> checkout --> payment\n"
        "    classDef actor fill:#EFF6FF,stroke:#BFD7FE,color:#17233A,stroke-width:1px;\n"
        "    classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
        "    class shopper actor;\n"
        "    class checkout,payment service;\n"
    )

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="0.0.1",
    )

    assert len(result["diagrams"]) == 2


def test_greenfield_apply_rejects_overlong_unwrapped_flowchart_labels(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["mermaid_source"] = (
        "flowchart LR\n"
        "    subgraph transaction_lane[\"Transaction lane\"]\n"
        "      checkout[\"Checkout orchestrator that owns payment handoff order draft idempotency retry recovery and user visible repair state\"]\n"
        "    end\n"
        "    classDef service fill:#ECFDFB,stroke:#A7E9E3,color:#17233A,stroke-width:1px;\n"
        "    class checkout service;\n"
    )

    with pytest.raises(ValueError, match="wrap long labels"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_missing_host_authored_diagram_source(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0].pop("mermaid_source")

    with pytest.raises(ValueError, match="missing host-authored mermaid_source"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
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
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_child_without_topology(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["backlog"][1].pop("component_focus")
    proposal["backlog"][1].pop("related_diagram_slugs")

    with pytest.raises(ValueError, match="greenfield proposal Tribunal failed"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_component_without_ownership_contract(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["components"][0].pop("interfaces")

    with pytest.raises(ValueError, match="component `commerce-storefront` must describe planned interfaces"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_diagram_without_workstream_traceability(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0].pop("related_workstream_titles")

    with pytest.raises(ValueError, match="diagram `commerce-launch-system-context` must name related workstream"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )
