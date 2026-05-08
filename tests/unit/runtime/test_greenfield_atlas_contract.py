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
        "robot-swarm-logistics-app-system-overview",
        "robot-swarm-logistics-app-first-slice-flow",
        "robot-swarm-logistics-app-component-ownership-map",
        "robot-swarm-logistics-app-domain-state-model",
        "robot-swarm-logistics-app-validation-release-topology",
        "robot-swarm-logistics-app-multi-robot-conflict",
        "robot-swarm-logistics-app-safety-envelope",
        "robot-swarm-logistics-app-telemetry-contract",
        "robot-swarm-logistics-app-deployment-boundaries",
        "robot-swarm-logistics-app-observability-audit-loop",
    } == diagram_slugs
    sources = {row["slug"]: row["mermaid_source"] for row in proposal["diagrams"]}
    assert "bounded wait queued" in sources["robot-swarm-logistics-app-multi-robot-conflict"]
    assert "Hardware -. blocked until HIL proof .-> Agent" in sources["robot-swarm-logistics-app-deployment-boundaries"]
    assert "Atlas diagram<br/>render proof" in sources["robot-swarm-logistics-app-observability-audit-loop"]
    assert set(proposal["backlog"][0]["related_diagram_slugs"]) == diagram_slugs
    assert "robot-swarm-logistics-app-safety-envelope" in proposal["components"][1]["related_diagram_slugs"]
    greenfield_proposals.validate_host_reasoned_proposal(proposal)
    assert greenfield_proposals.run_greenfield_tribunal(proposal, release_selector="0.0.1").passed


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


def test_greenfield_apply_rejects_unstyled_flowchart_diagram_sources(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _host_reasoned_ecommerce_proposal()
    proposal["diagrams"][0]["mermaid_source"] = (
        "flowchart LR\n"
        "    shopper[Shopper]\n"
        "    checkout[Checkout]\n"
        "    shopper --> checkout\n"
    )

    with pytest.raises(ValueError, match="subtle classDef/style colors"):
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
        "    classDef actor fill:#e8fbf7,stroke:#5bbfb2,color:#062f2b,stroke-width:1px;\n"
        "    classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f,stroke-width:1px;\n"
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
        "    classDef service fill:#eaf3ff,stroke:#77a9ef,color:#102f5f,stroke-width:1px;\n"
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
