from __future__ import annotations

import argparse
import json
from pathlib import Path

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


def test_greenfield_ecommerce_prompt_proposes_backlog_components_and_topology(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Odylith, build an ecommerce site for me",
    )

    assert proposal["mode"] == "greenfield_proposal"
    assert proposal["provider_calls"] == 0
    assert proposal["write_policy"] == "proposal_first_confirm_before_apply"
    assert proposal["intent"]["archetype"] == "commerce"
    assert proposal["observed_source"]["source_posture"] == "empty_or_no_app_source"
    assert proposal["backlog"]
    assert proposal["program"]["waves"]
    assert proposal["release_plan"]["selector"] == "next"
    assert proposal["components"]
    assert proposal["diagrams"]
    assert all(row["evidence_tier"] == "user_intent" for row in proposal["components"])
    assert any(row["component_id"].endswith("payments") for row in proposal["components"])
    assert all(row["link_state"] == "atlas_first_draft" for row in proposal["diagrams"])
    assert all(row["intended_paths"] for row in proposal["diagrams"])
    assert all(row["watch_paths"] == [] for row in proposal["diagrams"])
    assert "odylith greenfield apply" in proposal["apply_commands"][1]
    assert "--release 'next'" in proposal["apply_commands"][1]


def test_greenfield_science_math_prompt_adds_domain_validation_obligations(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create architecture for a differential equation solver research project",
    )

    assert proposal["intent"]["archetype"] == "science_math"
    labels = {row["label"] for row in proposal["components"]}
    assert {"Model Core", "Solver Engine", "Validation Suite"} <= labels
    validation_text = " ".join(proposal["validation_strategy"]).lower()
    assert "tolerance" in validation_text
    assert "reference outputs" in validation_text or "benchmark datasets" in validation_text
    assumptions = " ".join(proposal["assumptions"]).lower()
    assert "scientific and mathematical claims are not inferred" in assumptions


def test_greenfield_cli_json_is_deterministic_and_provider_free(tmp_path, capsys) -> None:
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
    assert payload["provider_calls"] == 0
    assert payload["host_agnostic"] is True
    assert payload["intent"]["archetype"] == "science_math"


def test_greenfield_text_keeps_no_write_boundary_visible(tmp_path, capsys) -> None:
    rc = greenfield_proposals.main(
        [
            "propose",
            "--repo-root",
            str(tmp_path),
            "--prompt",
            "Design a CLI library",
        ]
    )

    assert rc == 0
    output = capsys.readouterr().out
    assert "No files changed." in output
    assert "Planned Registry components" in output
    assert "Draft Atlas diagrams" in output
    assert "Program waves" in output
    assert "Release plan" in output
    assert "provider_calls: 0" in output


def test_greenfield_catalog_covers_infra_security_and_instrument_workflows(tmp_path) -> None:
    cases = {
        "Build a Kubernetes observability platform": "cloud_infra",
        "Create a SOC2 audit evidence workflow": "security_compliance",
        "Design an IoT sensor calibration workflow": "iot_instrumentation",
    }

    for prompt, archetype in cases.items():
        proposal = greenfield_proposals.build_greenfield_proposal(repo_root=tmp_path, prompt=prompt)

        assert proposal["intent"]["archetype"] == archetype
        assert proposal["provider_calls"] == 0
        assert proposal["program"]["waves"]
        assert proposal["diagrams"]


def test_greenfield_backlog_overrides_preserve_child_specific_sections(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build an ecommerce marketplace",
    )
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
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "print_dashboard_handoff", lambda **_kwargs: None)
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build an ecommerce site",
    )

    result = greenfield_proposals.apply_greenfield_proposal(
        repo_root=tmp_path,
        proposal=proposal,
        confirm=True,
        release_selector="next",
    )

    registry = json.loads((tmp_path / "odylith/radar/source/releases/releases.v1.json").read_text(encoding="utf-8"))
    events = (tmp_path / "odylith/radar/source/releases/release-assignment-events.v1.jsonl").read_text(encoding="utf-8")
    assert result["release_bootstrap"]["created"] is True
    assert registry["aliases"]["next"] == "release-an-ecommerce-site-first"
    assert len(result["backlog"]) == 4
    assert len(result["components"]) == 5
    assert len(result["diagrams"]) == 2
    assert '"release_id": "release-an-ecommerce-site-first"' in events


def test_greenfield_apply_json_output_is_machine_clean(tmp_path, monkeypatch, capsys) -> None:
    _seed_empty_governance_repo(tmp_path)
    monkeypatch.setattr(greenfield_proposals.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_proposals.scaffold_mermaid_diagram.owned_surface_refresh, "print_dashboard_handoff", lambda **_kwargs: None)
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps(greenfield_proposals.build_greenfield_proposal(repo_root=tmp_path, prompt="Build an ecommerce site")),
        encoding="utf-8",
    )

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
