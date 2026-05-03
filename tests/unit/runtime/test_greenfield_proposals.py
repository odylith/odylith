from __future__ import annotations

import argparse
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import archetypes
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
    assert proposal["catalog"]["catalog_source"] == "built_in_seed"
    assert proposal["catalog"]["marketplace_ready"] is True
    assert "commerce" in proposal["catalog"]["archetypes"]
    assert proposal["intent"]["archetype"] == "commerce"
    assert proposal["classification"]["method"] == "deterministic_keyword_archetype_scoring"
    assert proposal["classification"]["provider_calls"] == 0
    assert proposal["observed_source"]["source_posture"] == "empty_or_no_app_source"
    assert proposal["greenfield_ux"]["mode"] == "consumer_greenfield_proposal"
    assert proposal["greenfield_ux"]["operator_sequence"]
    assert proposal["backlog"]
    assert proposal["program"]["wave_count"] == len(proposal["program"]["waves"])
    assert proposal["program"]["recommended_first_wave"]
    assert proposal["program"]["blueprint"]["program_type"] == "greenfield_program"
    assert proposal["program"]["blueprint"]["parent_workstream"] == "Govern An Ecommerce Site"
    assert proposal["release_plan"]["selector"] == "next"
    assert proposal["release_plan"]["provisional_release_id"] == "release-an-ecommerce-site-first"
    assert proposal["release_plan"]["release_stages"]
    assert proposal["components"]
    assert proposal["diagrams"]
    assert all(row["evidence_tier"] == "user_intent" for row in proposal["components"])
    assert any(row["component_id"].endswith("payments") for row in proposal["components"])
    assert all(row["link_state"] == "atlas_first_draft" for row in proposal["diagrams"])
    assert all(row["intended_paths"] for row in proposal["diagrams"])
    assert all(row["watch_paths"] == [] for row in proposal["diagrams"])
    first_slice = proposal["backlog"][0]["recommended_first_slice"]
    assert "validation path" in first_slice
    assert "proof harness" not in first_slice
    assert "odylith greenfield apply" in proposal["apply_commands"][1]
    assert "--release 'next'" in proposal["apply_commands"][1]


def test_domain_catalog_api_accepts_future_external_archetype_pack() -> None:
    quantum_lab = archetypes.Archetype(
        archetype_id="quantum_lab",
        label="Quantum Lab Workflow",
        keywords=("quantum lab", "qubit calibration"),
        components=(
            archetypes.ComponentBlueprint("lab-control", "Lab Control", "service", "src/lab", "Experiment control boundary."),
        ),
        diagrams=(
            archetypes.DiagramBlueprint("lab-topology", "Lab Topology", "Show control, instruments, and validation boundaries."),
        ),
        waves=(
            archetypes.WaveBlueprint("Calibration", "Pin calibration scope.", "Reference runs are recorded."),
        ),
        validation_focus=("Calibration reference runs stay versioned.",),
        risks=("Instrument claims require observed lab evidence.",),
    )

    external_catalog = archetypes.DomainCatalog(
        catalog_id="example.domain_catalog.quantum_lab",
        version="2026.1",
        source="marketplace",
        archetypes=(quantum_lab,),
    )

    ranked = archetypes.rank_archetypes("govern a quantum lab", catalog=external_catalog)
    metadata = archetypes.catalog_metadata(external_catalog)

    assert ranked[0][0].archetype_id == "quantum_lab"
    assert metadata["catalog_id"] == "example.domain_catalog.quantum_lab"
    assert metadata["catalog_version"] == "2026.1"
    assert metadata["catalog_source"] == "marketplace"
    assert metadata["marketplace_ready"] is True
    assert metadata["archetypes"] == ["quantum_lab"]


def test_greenfield_science_math_prompt_adds_domain_validation_obligations(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create architecture for a differential equation solver research project",
    )

    assert proposal["intent"]["archetype"] == "simulation_modeling"
    labels = {row["label"] for row in proposal["components"]}
    assert {"Model Spec", "Solver Engine", "Reference Cases"} <= labels
    validation_text = " ".join(proposal["validation_strategy"]).lower()
    assert "tolerance" in validation_text
    assert "convergence" in validation_text
    assert "units" in validation_text
    assumptions = " ".join(proposal["assumptions"]).lower()
    assert "scientific" in assumptions and "claims are not inferred" in assumptions


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
    assert payload["intent"]["archetype"] == "computational_notebook"


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
    assert "Greenfield UX" in output
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


@pytest.mark.parametrize(
    ("prompt", "expected_archetype"),
    [
        ("Build an ecommerce site", "commerce"),
        ("Plan a B2B CRM", "saas_application"),
        ("Create an internal dashboard", "saas_application"),
        ("Govern an AI research assistant", "ai_agent"),
        ("Design a data ingestion platform", "data_platform"),
        ("Build a CLI library", "cli_library"),
        ("Create a physics simulation", "simulation_modeling"),
        ("Create a differential-equation solver", "simulation_modeling"),
        ("Build a computational biology pipeline", "scientific_pipeline"),
        ("Create a formal math proof library", "formal_proof"),
        ("Create a statistics econometrics notebook repo", "computational_notebook"),
        ("Design a math education app", "math_education"),
        ("Plan a geospatial climate data analysis platform", "geospatial_environmental"),
        ("Build an ML experiment platform for biology images", "ml_experiment_platform"),
        ("Design a robotics sensor calibration workflow", "iot_instrumentation"),
        ("Create a quantum lab calibration workflow", "iot_instrumentation"),
    ],
)
def test_greenfield_fixture_domains_are_specific_and_provider_free(tmp_path, prompt: str, expected_archetype: str) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(repo_root=tmp_path, prompt=prompt)

    assert proposal["intent"]["archetype"] == expected_archetype
    assert proposal["provider_calls"] == 0
    assert proposal["host_agnostic"] is True
    assert proposal["backlog"]
    assert proposal["components"]
    assert proposal["diagrams"]
    assert proposal["program"]["waves"]
    assert proposal["release_plan"]["release_stages"]


def test_greenfield_formal_proof_uses_checker_validation_not_numerical_tolerance(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create a formal math proof library for topology theorems",
    )

    assert proposal["intent"]["archetype"] == "formal_proof"
    validation_text = " ".join(proposal["validation_strategy"]).lower()
    assert "theorem" in validation_text
    assert "lemma" in validation_text
    assert "proof checker" in validation_text or "checker" in validation_text
    assert "tolerance" not in validation_text
    assert "floating" not in validation_text
    assert "random seed" not in validation_text
    assert "proof-checker harness" in proposal["backlog"][0]["recommended_first_slice"]


def test_greenfield_titles_preserve_domain_acronyms_and_program_formation(tmp_path) -> None:
    proposal = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create a NASA-style satellite simulation and API mission analysis platform",
    )

    assert proposal["intent"]["title"] == "A NASA-style Satellite Simulation And API Mission Analysis Platform"
    assert proposal["intent"]["archetype"] == "simulation_modeling"
    assert proposal["classification"]["primary"]["archetype"] == "simulation_modeling"
    assert proposal["classification"]["alternatives"]
    assert proposal["program"]["blueprint"]["wave_to_workstream_policy"]


def test_greenfield_notebook_math_education_and_geospatial_validation_fit_domain(tmp_path) -> None:
    notebook = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Create a statistics econometrics notebook repo",
    )
    notebook_validation = " ".join(notebook["validation_strategy"]).lower()
    assert notebook["intent"]["archetype"] == "computational_notebook"
    assert "notebook" in notebook_validation
    assert "statistical" in notebook_validation
    assert "reference outputs" in notebook_validation

    education = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Build topology exercises for undergraduates",
    )
    education_validation = " ".join(education["validation_strategy"]).lower()
    assert education["intent"]["archetype"] == "math_education"
    assert "exercise" in education_validation
    assert "accessibility" in education_validation
    assert "mathematical truth" in education_validation

    geospatial = greenfield_proposals.build_greenfield_proposal(
        repo_root=tmp_path,
        prompt="Plan a geospatial climate data analysis platform",
    )
    geospatial_validation = " ".join(geospatial["validation_strategy"]).lower()
    assert geospatial["intent"]["archetype"] == "geospatial_environmental"
    assert "coordinate reference systems" in geospatial_validation
    assert "temporal coverage" in geospatial_validation


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
    assert result["memory"]["recorded"] is True
    memory_event = result["memory"]["event"]
    assert memory_event["kind"] == "decision"
    assert memory_event["source"] == "domain-intelligence"
    assert memory_event["evidence_tier"] == "user_intent"
    assert "Accepted greenfield proposal for An Ecommerce Site" in memory_event["summary"]
    assert len(memory_event["workstreams"]) == 4
    assert len(memory_event["components"]) == 5
    assert "source_posture=empty_or_no_app_source" in memory_event["context"]
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
    assert payload["memory"]["recorded"] is True
    assert payload["memory"]["event"]["source"] == "domain-intelligence"
