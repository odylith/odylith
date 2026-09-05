"""Characterization of the sealed model-authored Greenfield Atlas view."""

from __future__ import annotations

from copy import deepcopy
import datetime as dt
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_apply_diagrams
from odylith.runtime.domain_intelligence import greenfield_authored_atlas_view
from odylith.runtime.domain_intelligence import greenfield_confirmed_text
from odylith.runtime.domain_intelligence import greenfield_deferral_predicates
from odylith.runtime.domain_intelligence import greenfield_text
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_PROJECTION_ORIGIN,
)
from odylith.runtime.surfaces import atlas_box_explanations
from odylith.runtime.surfaces import atlas_diagram_intelligence
from odylith.runtime.surfaces import render_mermaid_catalog
from tests.unit.runtime.test_greenfield_authored_lexical_isolation import (
    _authored_intent,
    _public_propose,
)


def _authored_diagrams(
    *,
    title: str = "Harbor Desk",
    component_label: str = "Berth map",
    visible_result: str = "the berth map shows the placement",
    proof_boundary: str = "Verify the placement and retention receipt",
) -> list[dict[str, Any]]:
    return greenfield_authored_atlas_view.build_authored_atlas_diagrams(
        title=title,
        diagram_slugs={
            "context": "harbor-desk-context",
            "sequence": "harbor-desk-sequence",
            "state_evidence": "harbor-desk-state",
            "component_boundaries": "harbor-desk-boundaries",
        },
        human_actors=("Dock attendant Ivo",),
        external_systems=("Harbor Ledger",),
        non_goals=("Do not manage vessel scheduling",),
        state_object="berth occupancy",
        visible_result=visible_result,
        proof_boundary=proof_boundary,
        components=(
            {
                "component_id": "berth-map",
                "label": component_label,
                "responsibility": "Record berth occupancy",
                "dependencies": ["Harbor Ledger"],
            },
        ),
        backlog=({"title": "Deliver Harbor Desk"},),
        relations=(
            {
                "order": 1,
                "actor_kind": "human",
                "actor_quote": "Dock attendant Ivo",
                "actor_fact_quote": "Dock attendant Ivo",
                "event_quote": "Dock attendant Ivo enters a vessel tag",
                "owner_system_quote": "",
            },
            {
                "order": 2,
                "actor_kind": "product",
                "actor_quote": "the product",
                "actor_fact_quote": "Berth map",
                "event_quote": "the product records berth occupancy",
                "owner_system_quote": "Berth map",
            },
            {
                "order": 3,
                "actor_kind": "product",
                "actor_quote": "the berth map",
                "actor_fact_quote": "Berth map",
                "event_quote": "the berth map shows the placement",
                "owner_system_quote": "Berth map",
            },
        ),
        context_relations=(
            {
                "context_kind": "state_object",
                "fact_quote": "berth occupancy",
                "first_path_event_order": 2,
            },
            {
                "context_kind": "external_system",
                "fact_quote": "Harbor Ledger",
                "first_path_event_order": 0,
            },
        ),
    )


def test_context_view_represents_a_sole_title_owned_product_once() -> None:
    rows = _authored_diagrams(component_label="Harbor Desk")
    context = next(row for row in rows if row["slug"] == "harbor-desk-context")

    assert context["mermaid_source"].count('["Harbor Desk"]') == 1
    assert 'subgraph product["Harbor Desk"]' not in context["mermaid_source"]
    assert "component1" not in context["mermaid_source"]
    assert [
        (box["node_id"], box["label"], box["role"])
        for box in context["diagram_boxes"]
        if box["label"] == "Harbor Desk"
    ] == [("product", "Harbor Desk", "Product boundary")]


def _traceability_plan() -> SimpleNamespace:
    return SimpleNamespace(diagram_links=())


def test_authored_atlas_view_seals_exact_versioned_display_custody() -> None:
    rows = _authored_diagrams()

    assert len(rows) == 4
    for row in rows:
        authority = row[greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY]
        assert set(authority) == {
            "version",
            "projection_origin",
            "source_sha256",
            "surface_sha256",
            "node_order",
        }
        assert authority["version"] == greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_VERSION
        assert authority["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
        assert authority["source_sha256"] == hashlib.sha256(
            row["mermaid_source"].encode("utf-8")
        ).hexdigest()
        view = greenfield_authored_atlas_view.validate_authored_atlas_view(
            row,
            source_text=row["mermaid_source"],
        )
        assert view == {
            "summary": row["summary"],
            "read_guide": row["read_guide"],
            "diagram_boxes": row["diagram_boxes"],
            "components": row["components"],
        }
        assert authority["node_order"] == [box["node_id"] for box in row["diagram_boxes"]]


def test_authored_atlas_depth_is_four_distinct_semantic_views_not_a_count_floor() -> None:
    rows = _authored_diagrams()

    assert [(row["slug"], row["title"]) for row in rows] == [
        ("harbor-desk-context", "System Context View"),
        ("harbor-desk-sequence", "First Path Sequence"),
        ("harbor-desk-state", "State and Evidence View"),
        ("harbor-desk-boundaries", "Component Boundary View"),
    ]
    node_ids_by_slug = {
        row["slug"]: {box["node_id"] for box in row["diagram_boxes"]}
        for row in rows
    }
    assert {"people", "product", "external_systems"} <= node_ids_by_slug["harbor-desk-context"]
    assert {"event1", "event2", "event3", "owner1"} <= node_ids_by_slug["harbor-desk-sequence"]
    assert node_ids_by_slug["harbor-desk-state"] == {
        "accepted_facts",
        "state",
        "state_event",
        "result",
        "proof",
    }
    assert {"product", "component1", "external_systems", "outside_scope"} <= node_ids_by_slug[
        "harbor-desk-boundaries"
    ]
    assert len({row["summary"] for row in rows}) == 4
    assert len({row["mermaid_source"] for row in rows}) == 4
    source_by_slug = {row["slug"]: row["mermaid_source"] for row in rows}
    assert "actor1 --> product" in source_by_slug["harbor-desk-context"]
    assert "actor1 --> component1" not in source_by_slug["harbor-desk-context"]
    assert "external1 -.-> component1" in source_by_slug["harbor-desk-context"]
    assert "state -. exact source overlap .-> state_event" in source_by_slug["harbor-desk-state"]
    assert "state_event --> result" not in source_by_slug["harbor-desk-state"]
    assert "result --> proof" not in source_by_slug["harbor-desk-state"]
    assert "external1 -.-> component1" in source_by_slug["harbor-desk-boundaries"]
    assert "product -.-> non_goal1" in source_by_slug["harbor-desk-boundaries"]


def test_state_view_links_result_to_proof_only_for_exact_source_containment() -> None:
    contained = _authored_diagrams(
        visible_result="exception review",
        proof_boundary="care-plan readiness, visit evidence, and exception review",
    )
    separate = _authored_diagrams(
        visible_result="exception review",
        proof_boundary="care-plan readiness and visit evidence",
    )
    contained_source = next(
        row["mermaid_source"] for row in contained if row["slug"] == "harbor-desk-state"
    )
    separate_source = next(
        row["mermaid_source"] for row in separate if row["slug"] == "harbor-desk-state"
    )

    assert "result -. exact source containment .-> proof" in contained_source
    assert "result -. exact source containment .-> proof" not in separate_source
    assert "result --> proof" not in contained_source


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("missing", "missing"),
        ("duplicate", "duplicate"),
        ("reordered", "reordered"),
        ("unmatched", "unmatched"),
    ),
)
def test_authored_atlas_view_rejects_box_custody_drift_before_staging(
    mutation: str,
    message: str,
) -> None:
    row = deepcopy(_authored_diagrams()[0])
    if mutation == "missing":
        row["diagram_boxes"].pop()
    elif mutation == "duplicate":
        row["diagram_boxes"].append(deepcopy(row["diagram_boxes"][0]))
    elif mutation == "reordered":
        row["diagram_boxes"][0], row["diagram_boxes"][1] = (
            row["diagram_boxes"][1],
            row["diagram_boxes"][0],
        )
    else:
        row["diagram_boxes"][-1]["node_id"] = "unmatched-node"

    with pytest.raises(ValueError, match=message):
        greenfield_apply_diagrams.render_prewrite_atlas_sources({"diagrams": [row]})


def test_authored_atlas_origin_cannot_fall_back_to_legacy_when_marker_is_missing() -> None:
    row = deepcopy(_authored_diagrams()[0])
    row.pop(greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY)

    with pytest.raises(ValueError, match="authority must be an object"):
        greenfield_apply_diagrams.render_prewrite_atlas_sources({"diagrams": [row]})


def test_authored_atlas_catalog_and_source_survive_compilation_and_readback_exactly(
    tmp_path: Path,
) -> None:
    proposal_row = _authored_diagrams()[0]
    sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(
        {"diagrams": [proposal_row]}
    )
    compiled_row = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        review_date="2026-08-31",
    )[0]
    authority_key = greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY
    assert compiled_row["projection_origin"] == proposal_row["projection_origin"]
    assert compiled_row[authority_key] == proposal_row[authority_key]
    assert compiled_row["diagram_boxes"] == proposal_row["diagram_boxes"]
    assert compiled_row["summary"] == proposal_row["summary"]
    assert compiled_row["read_guide"] == proposal_row["read_guide"]
    assert compiled_row["components"] == proposal_row["components"]

    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    catalog_path.parent.mkdir(parents=True)
    catalog_path.write_text('{"version":"v1","diagrams":[]}\n', encoding="utf-8")
    result = greenfield_apply_diagrams.materialize_apply_diagrams(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        rendered_atlas_sources=sources,
        review_date="2026-08-31",
        require_compiled_sources=True,
        compiled_catalog_rows=(compiled_row,),
    )

    assert result.diagram_ids == ("D-001",)
    written_row = json.loads(catalog_path.read_text(encoding="utf-8"))["diagrams"][0]
    canonical = lambda value: json.dumps(  # noqa: E731 - compact byte comparison helper
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    assert canonical(written_row) == canonical(compiled_row)
    source_path = tmp_path / compiled_row["source_mmd"]
    assert source_path.read_bytes() == sources[compiled_row["source_mmd"]].encode("utf-8")
    greenfield_authored_atlas_view.validate_authored_atlas_view(
        written_row,
        source_text=source_path.read_text(encoding="utf-8"),
    )


def test_marked_authored_atlas_catalog_direct_renders_exact_rows_without_legacy_parsers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal_row = _authored_diagrams()[0]
    sources = greenfield_apply_diagrams.render_prewrite_atlas_sources(
        {"diagrams": [proposal_row]}
    )
    compiled_row = greenfield_apply_diagrams.render_prewrite_atlas_catalog_rows(
        root=tmp_path,
        rows=(proposal_row,),
        diagram_ids=("D-001",),
        traceability_plan=_traceability_plan(),
        review_date=dt.date.today().isoformat(),
    )[0]
    source_path = tmp_path / compiled_row["source_mmd"]
    svg_path = tmp_path / compiled_row["source_svg"]
    png_path = tmp_path / compiled_row["source_png"]
    catalog_path = tmp_path / "odylith/atlas/source/catalog/diagrams.v1.json"
    for path in (source_path, svg_path, png_path, catalog_path):
        path.parent.mkdir(parents=True, exist_ok=True)
    source_path.write_text(sources[compiled_row["source_mmd"]], encoding="utf-8")
    svg_path.write_text("<svg viewBox='0 0 1200 800'></svg>\n", encoding="utf-8")
    png_path.write_bytes(b"png")
    catalog_path.write_text(
        f"{json.dumps({'version': 'v1', 'diagrams': [compiled_row]}, indent=2)}\n",
        encoding="utf-8",
    )

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("marked authored Atlas row entered a legacy semantic parser")

    monkeypatch.setattr(atlas_box_explanations, "normalize_catalog_diagram_boxes", forbidden)
    monkeypatch.setattr(atlas_box_explanations, "clean_component_description", forbidden)
    monkeypatch.setattr(atlas_box_explanations, "merge_diagram_box_explanations", forbidden)
    monkeypatch.setattr(atlas_diagram_intelligence, "build_diagram_narrative", forbidden)

    diagrams, errors, stats = render_mermaid_catalog._load_catalog(  # noqa: SLF001
        repo_root=tmp_path,
        catalog_path=catalog_path,
        output_path=tmp_path / "odylith/atlas/atlas.html",
        max_review_age_days=21,
        component_index={},
    )

    assert errors == []
    assert stats == {"total": 1, "fresh": 1, "stale": 0}
    assert diagrams[0]["summary"] == proposal_row["summary"]
    assert diagrams[0]["read_guide"] == proposal_row["read_guide"]
    assert diagrams[0]["diagram_boxes"] == proposal_row["diagram_boxes"]
    assert diagrams[0]["components"] == proposal_row["components"]


def test_public_authored_propose_never_calls_legacy_semantic_rule_families(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    family_calls = {
        "terminal_deferral": 0,
        "source_casing": 0,
        "connector": 0,
        "action_target": 0,
    }
    def trap(family: str, module: object, name: str) -> None:
        original = getattr(module, name)

        def guarded(*args: object, **kwargs: object) -> object:
            family_calls[family] += 1
            return original(*args, **kwargs)

        monkeypatch.setattr(module, name, guarded)

    trap(
        "terminal_deferral",
        greenfield_deferral_predicates,
        "terminal_deferral_subject",
    )
    trap(
        "source_casing",
        greenfield_confirmed_text,
        "capitalize_sentence_start_preserving_source_terms",
    )
    trap("connector", greenfield_confirmed_text, "normalize_connector_sequence")
    trap("action_target", greenfield_text, "normalize_action_target_language")

    rc, payload, provider = _public_propose(
        tmp_path=tmp_path,
        monkeypatch=monkeypatch,
        capsys=capsys,
        intent=_authored_intent(),
    )

    assert rc == 0, payload
    assert provider.calls == 2
    assert family_calls["terminal_deferral"] == 0
    assert family_calls["source_casing"] == 0
    assert family_calls["connector"] == 0
    assert family_calls["action_target"] == 0

    transaction = json.loads(
        (tmp_path / payload["transaction_file"]).read_text(encoding="utf-8")
    )
    proposal_rows = transaction["proposal"]["diagrams"]
    compiled_rows = transaction["prewrite_package"]["atlas_catalog_rows"]
    authority_key = greenfield_authored_atlas_view.AUTHORED_ATLAS_AUTHORITY_KEY
    assert len(proposal_rows) == len(compiled_rows) == 4
    for proposal_row, compiled_row in zip(proposal_rows, compiled_rows, strict=True):
        assert compiled_row["projection_origin"] == AUTHORED_PROJECTION_ORIGIN
        assert compiled_row[authority_key] == proposal_row[authority_key]
        assert compiled_row["diagram_boxes"] == proposal_row["diagram_boxes"]
        assert compiled_row["summary"] == proposal_row["summary"]
        assert compiled_row["read_guide"] == proposal_row["read_guide"]
        assert compiled_row["components"] == proposal_row["components"]
