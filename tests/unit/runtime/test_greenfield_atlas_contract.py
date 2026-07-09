from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_apply_write
from odylith.runtime.domain_intelligence import greenfield_component_commit
from odylith.runtime.domain_intelligence import greenfield_proposals
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import PRODUCT_INTENT_AUTHORITY_KEY
from tests.unit.runtime.greenfield_proposal_fixtures import (
    CONFIRMED_INTENT_TEXT,
    _host_reasoned_ecommerce_proposal,
    _seed_empty_governance_repo,
    confirmed_intent_with_authority,
)


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


def _proposal_with_confirmed_authority(tmp_path) -> dict[str, object]:
    proposal = _host_reasoned_ecommerce_proposal()
    confirmed_intent = confirmed_intent_with_authority(
        CONFIRMED_INTENT_TEXT,
        prompt="Draft a governed ecommerce launch proposal",
        repo_root=tmp_path,
        write_files=True,
    )
    proposal[PRODUCT_INTENT_AUTHORITY_KEY] = confirmed_intent[PRODUCT_INTENT_AUTHORITY_KEY]
    return proposal


def test_greenfield_diagram_owner_validates_rendered_surface_custody(tmp_path) -> None:
    for relative_path in (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/atlas/source/demo.svg",
        "odylith/atlas/source/demo.png",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rendered\n", encoding="utf-8")
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "render_source_fingerprint": "sha256:demo",
                        "reviewed_watch_fingerprints": {"odylith/atlas/source/demo.mmd": "sha256:source"},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    result = greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
        repo_root=tmp_path,
        diagram_ids=("D-001",),
    )

    assert result == {"status": "passed", "atlas_surface_count": 3, "atlas_diagram_count": 1}


def test_greenfield_diagram_owner_reports_rendered_surface_custody_failures(tmp_path) -> None:
    for relative_path in (
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/atlas/source/demo.svg",
    ):
        path = tmp_path / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("rendered\n", encoding="utf-8")
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "source_svg": "odylith/atlas/source/demo.svg",
                        "source_png": "odylith/atlas/source/demo.png",
                        "render_source_fingerprint": "",
                        "reviewed_watch_fingerprints": {},
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError) as exc_info:
        greenfield_apply_diagrams.raise_for_greenfield_rendered_surface_custody(
            repo_root=tmp_path,
            diagram_ids=("D-001",),
        )

    message = str(exc_info.value)
    assert "D-001: missing rendered Atlas source_png" in message
    assert "D-001: missing Atlas render_source_fingerprint" in message
    assert "D-001: missing Atlas reviewed_watch_fingerprints" in message


def test_greenfield_diagram_owner_validates_compiled_ids_and_sources() -> None:
    package = SimpleNamespace(
        atlas_diagram_ids=("d-001", " D-002 "),
        atlas_catalog_rows=(
            {"diagram_id": "D-001", "source_mmd": "odylith/atlas/source/one.mmd"},
            {"diagram_id": "D-002", "source_mmd": "odylith/atlas/source/two.mmd"},
        ),
    )

    assert greenfield_apply_diagrams.compiled_atlas_diagram_ids(package, expected_count=2) == ["D-001", "D-002"]
    assert [
        row["source_mmd"]
        for row in greenfield_apply_diagrams.compiled_atlas_catalog_rows(package, expected_ids=("D-001", "D-002"))
    ] == ["odylith/atlas/source/one.mmd", "odylith/atlas/source/two.mmd"]
    assert (
        greenfield_apply_diagrams.prewrite_atlas_source(
            {"slug": "demo"},
            {"odylith/atlas/source/demo.mmd": "flowchart LR\n  a --> b\n"},
            required=True,
        )
        == "flowchart LR\n  a --> b"
    )
    with pytest.raises(ValueError, match="missing or incomplete"):
        greenfield_apply_diagrams.compiled_atlas_diagram_ids(package, expected_count=3)
    with pytest.raises(ValueError, match="is invalid"):
        greenfield_apply_diagrams.compiled_atlas_diagram_ids(
            SimpleNamespace(atlas_diagram_ids=("diagram-1",)),
            expected_count=1,
        )
    with pytest.raises(ValueError, match="missing for odylith/atlas/source/demo.mmd"):
        greenfield_apply_diagrams.prewrite_atlas_source({"slug": "demo"}, {}, required=True)
    with pytest.raises(ValueError, match="catalog rows missing or incomplete"):
        greenfield_apply_diagrams.compiled_atlas_catalog_rows(package, expected_ids=("D-001", "D-003"))


def test_greenfield_diagram_owner_materializes_existing_diagram_from_compiled_source(
    tmp_path,
    monkeypatch,
) -> None:
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True, exist_ok=True)
    catalog_path.write_text(
        json.dumps(
            {
                "diagrams": [
                    {
                        "diagram_id": "D-001",
                        "slug": "demo",
                        "source_mmd": "odylith/atlas/source/demo.mmd",
                    }
                ]
            }
        )
        + "\n",
        encoding="utf-8",
    )
    watch_path = tmp_path / "src/demo.py"
    watch_path.parent.mkdir(parents=True, exist_ok=True)
    watch_path.write_text("print('demo')\n", encoding="utf-8")

    def fake_scaffold_diagram(**_kwargs):
        raise AssertionError("compiled Atlas commit path must not scaffold diagrams")

    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram, "scaffold_diagram", fake_scaffold_diagram)
    compiled_row = {
        "diagram_id": "D-001",
        "slug": "demo",
        "title": "Compiled Demo Flow",
        "kind": "flowchart",
        "status": "draft",
        "owner": "repo",
        "last_reviewed_utc": "2026-07-08",
        "source_mmd": "odylith/atlas/source/demo.mmd",
        "source_svg": "odylith/atlas/source/demo.svg",
        "source_png": "odylith/atlas/source/demo.png",
        "change_watch_paths": ["src/demo.py"],
        "summary": "Compiled row owns the demo flow.",
        "read_guide": "Read the compiled row.",
        "components": [{"name": "Compiled Demo", "description": "Owns the compiled demo flow."}],
        "related_backlog": ["odylith/radar/source/ideas/demo.md"],
        "related_plans": [],
        "related_docs": [],
        "related_code": [],
        "link_state": "fresh",
    }

    result = greenfield_apply_diagrams.materialize_apply_diagrams(
        root=tmp_path,
        rows=(
            {
                "slug": "demo",
                "title": "Ignored Proposal Flow",
                "kind": "flowchart",
                "owner": "repo",
                "summary": "This proposal row must not be used.",
                "read_guide": "Ignored.",
                "components": [{"name": "Ignored", "description": "Must not be materialized."}],
                "watch_paths": [],
                "link_state": "ignored",
            },
        ),
        diagram_ids=("D-001",),
        traceability_plan=SimpleNamespace(
            diagram_links=(SimpleNamespace(diagram_id="D-001", related_backlog_paths=("odylith/radar/source/ideas/demo.md",)),)
        ),
        rendered_atlas_sources={"odylith/atlas/source/demo.mmd": "flowchart LR\n  compiled --> source\n"},
        review_date="2026-07-08",
        require_compiled_sources=True,
        compiled_catalog_rows=(compiled_row,),
    )

    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    row = catalog["diagrams"][0]
    assert result.diagram_ids == ("D-001",)
    assert any("materialized compiled diagram: demo" in item for item in result.scaffold_logs)
    assert row["title"] == "Compiled Demo Flow"
    assert row["summary"] == "Compiled row owns the demo flow."
    assert row["read_guide"] == "Read the compiled row."
    assert row["source_mmd"] == "odylith/atlas/source/demo.mmd"
    assert row["source_svg"] == "odylith/atlas/source/demo.svg"
    assert row["source_png"] == "odylith/atlas/source/demo.png"
    assert row["components"] == [{"name": "Compiled Demo", "description": "Owns the compiled demo flow."}]
    assert row["related_backlog"] == ["odylith/radar/source/ideas/demo.md"]
    assert row["change_watch_paths"] == ["src/demo.py"]
    assert row["link_state"] == "fresh"
    assert (tmp_path / "odylith/atlas/source/demo.mmd").read_text(encoding="utf-8") == (
        "flowchart LR\n  compiled --> source\n"
    )


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
    proposal = _proposal_with_confirmed_authority(tmp_path)
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
    monkeypatch.setattr(greenfield_apply_write.owned_surface_refresh, "raise_for_failed_refreshes", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_component_commit.component_authoring.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(greenfield_apply_diagrams.scaffold_mermaid_diagram.owned_surface_refresh, "raise_for_failed_refresh", lambda **_kwargs: None)
    monkeypatch.setattr(
        greenfield_apply_diagrams,
        "raise_for_greenfield_rendered_surface_custody",
        lambda **_kwargs: {"status": "skipped-unit-render"},
    )
    proposal = _proposal_with_confirmed_authority(tmp_path)
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
    proposal = _proposal_with_confirmed_authority(tmp_path)
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
    proposal = _proposal_with_confirmed_authority(tmp_path)
    proposal["diagrams"][0].pop("mermaid_source")

    with pytest.raises(ValueError, match="missing proposal mermaid_source"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_identical_diagram_sources(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _proposal_with_confirmed_authority(tmp_path)
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
    proposal = _proposal_with_confirmed_authority(tmp_path)
    proposal["backlog"][1].pop("component_focus")
    proposal["backlog"][1].pop("related_diagram_slugs")

    with pytest.raises(ValueError, match="greenfield proposal validation gate failed"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )


def test_greenfield_apply_rejects_component_without_ownership_contract(tmp_path) -> None:
    _seed_empty_governance_repo(tmp_path)
    proposal = _proposal_with_confirmed_authority(tmp_path)
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
    proposal = _proposal_with_confirmed_authority(tmp_path)
    proposal["diagrams"][0].pop("related_workstream_titles")

    with pytest.raises(ValueError, match="diagram `commerce-launch-system-context` must name related workstream"):
        greenfield_proposals.apply_greenfield_proposal(
            repo_root=tmp_path,
            proposal=proposal,
            confirm=True,
            release_selector="0.0.1",
        )
