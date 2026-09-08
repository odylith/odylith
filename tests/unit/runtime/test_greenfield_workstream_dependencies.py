"""Exact provisional prerequisites survive native Radar allocation and sealing."""

from __future__ import annotations

import base64
import copy
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import (
    greenfield_create_commit,
    greenfield_proposals,
    greenfield_traceability,
)
from odylith.runtime.domain_intelligence.greenfield_provisional_design import (
    provisional_design_from_intent,
)
from odylith.runtime.governance import backlog_authoring
from tests.unit.runtime import greenfield_model_authoring_fixtures as authoring_fixtures
from tests.unit.runtime.greenfield_authored_proposal_fixtures import (
    _canonical_model_authored_greenfield_fixture,
)
from tests.unit.runtime.greenfield_proposal_fixtures import (
    seal_compiled_greenfield_transaction,
)


def _proposal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, forward_references: bool = False,
) -> dict[str, Any]:
    if forward_references:
        original_design = authoring_fixtures.structural_design_fixture

        def reordered_design(event_orders: Any) -> dict[str, Any]:
            design = original_design(event_orders)
            design["workstreams"] = list(reversed(design["workstreams"]))
            return design

        # Change only the fixed provider's synthetic response, before custody is sealed.
        monkeypatch.setattr(authoring_fixtures, "structural_design_fixture", reordered_design)
    return _canonical_model_authored_greenfield_fixture(tmp_path)


def _allocated_plan(tmp_path: Path, proposal: dict[str, Any]) -> Any:
    created = []
    for row, idea_id in zip(proposal["backlog"], ("B-041", "B-009", "B-120", "B-007"), strict=True):
        path = tmp_path / f"{idea_id}.md"
        path.write_text(backlog_authoring._render_idea_text(
            metadata={
                "idea_id": idea_id, "title": row["title"],
                "workstream_depends_on": "B-999", "related_diagram_ids": "D-099",
            },
            sections={
                "Dependencies": "\n".join(row["dependencies"]),
                "Source evidence": proposal["intent"]["first_path"],
            },
        ), encoding="utf-8")
        created.append({"idea_id": idea_id, "title": row["title"], "idea_path": str(path)})
    return greenfield_traceability.build_traceability_plan(
        proposal=proposal, created_backlog=created,
        diagram_ids=[f"D-{index:03}" for index in range(1, len(proposal["diagrams"]) + 1)],
    )


@pytest.mark.parametrize("forward_references", [False, True])
def test_exact_dependency_keys_bind_allocated_ids_without_changing_source_prose(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forward_references: bool,
) -> None:
    proposal = _proposal(tmp_path, monkeypatch, forward_references=forward_references)
    original_proposal = copy.deepcopy(proposal)
    plan = _allocated_plan(tmp_path, proposal)
    before_sections = {
        row.idea_id: backlog_authoring._parse_metadata_and_sections(row.path)[1]
        for row in plan.workstreams
    }
    design = provisional_design_from_intent(proposal["intent"])
    ids_by_key = {
        row.row["provisional_workstream_contract"]["provisional_workstream"]["key"]: row.idea_id
        for row in plan.workstreams
    }

    greenfield_traceability.apply_backlog_traceability(repo_root=tmp_path, proposal=proposal, plan=plan)

    for workstream, canonical in zip(plan.workstreams, design["workstreams"], strict=True):
        metadata, sections = backlog_authoring._parse_metadata_and_sections(workstream.path)
        assert metadata["workstream_depends_on"] == ",".join(
            ids_by_key[key] for key in canonical["depends_on"]
        )
        assert metadata["related_diagram_ids"].split(",") == [
            "D-099", *plan.backlog_diagrams[workstream.idea_id],
        ]
        assert sections == before_sections[workstream.idea_id]
    assert proposal == original_proposal


@pytest.mark.parametrize("corruption", [
    "missing", "duplicate_key", "unknown_key", "duplicate_id", "duplicate_path",
    "wrong_contract", "wrong_title", "record_id", "record_title",
])
def test_incomplete_or_ambiguous_allocation_rejects_before_any_traceability_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corruption: str,
) -> None:
    proposal = _proposal(tmp_path, monkeypatch)
    plan = _allocated_plan(tmp_path, proposal)
    original_workstreams = plan.workstreams
    rows = list(plan.workstreams)
    last = rows[-1]
    if corruption == "missing":
        rows.pop()
    elif corruption == "duplicate_id":
        rows[-1] = replace(last, idea_id=rows[0].idea_id)
    elif corruption == "duplicate_path":
        rows[-1] = replace(last, path=rows[0].path)
    elif corruption == "wrong_title":
        rows[-1] = replace(last, title=rows[0].title)
    elif corruption.startswith("record_"):
        metadata, sections = backlog_authoring._parse_metadata_and_sections(last.path)
        metadata["idea_id" if corruption == "record_id" else "title"] = "wrong allocation"
        last.path.write_text(backlog_authoring._render_idea_text(
            metadata=metadata, sections=sections,
        ), encoding="utf-8")
    else:
        row = copy.deepcopy(last.row)
        contract = row["provisional_workstream_contract"]["provisional_workstream"]
        if corruption == "duplicate_key":
            row = copy.deepcopy(rows[0].row)
        elif corruption == "unknown_key":
            contract["key"] = "absent-workstream"
        else:
            contract["depends_on"] = []
        rows[-1] = replace(last, row=row)
    plan = replace(plan, workstreams=tuple(rows))
    before = {row.path: row.path.read_bytes() for row in original_workstreams}

    with pytest.raises(ValueError, match="workstream.*allocation|allocation.*workstream"):
        greenfield_traceability.apply_backlog_traceability(
            repo_root=tmp_path, proposal=proposal, plan=plan,
        )

    assert {path: path.read_bytes() for path in before} == before


@pytest.mark.parametrize("forward_references", [False, True])
def test_native_radar_dependency_topology_is_sealed_and_committed_without_rebuild(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, forward_references: bool,
) -> None:
    proposal = _proposal(tmp_path, monkeypatch, forward_references=forward_references)
    from tests.unit.runtime.greenfield_baseline_fixtures import activate_greenfield_baseline_fixture

    activate_greenfield_baseline_fixture(tmp_path)
    receipt = proposal.pop("_test_model_authoring_receipt")
    transaction = greenfield_proposals.compile_greenfield_create_transaction(
        repo_root=tmp_path, proposal=proposal, release_selector="0.0.1", proposal_ready=True,
        preconfirm_elapsed_seconds=float(receipt["elapsed_seconds"]),
        model_authoring_tier=str(receipt["tier"]), model_authoring_receipt=receipt,
    )
    files = {
        row["path"]: base64.b64decode(row["content_base64"])
        for row in transaction.prewrite_package.repository_write_set["after_image"]["files"]
    }
    design = provisional_design_from_intent(proposal["intent"])
    created = transaction.backlog_result["created"]
    ids_by_key = {
        row["key"]: record["idea_id"]
        for row, record in zip(design["workstreams"], created, strict=True)
    }
    expected = {
        ids_by_key[row["key"]]: [ids_by_key[key] for key in row["depends_on"]]
        for row in design["workstreams"]
    }
    radar_path = "odylith/radar/backlog-payload.v1.js"
    script = files[radar_path].decode("utf-8")
    radar = json.loads(script.split("=", 1)[1].strip().removesuffix(";"))
    assert {
        row["idea_id"]: row["workstream_depends_on"]
        for row in radar["traceability_index"]["workstreams"]
    } == expected
    assert {
        (edge["source"], edge["target"])
        for edge in radar["traceability_index"]["edges"]
        if edge["edge_type"] == "depends_on"
    } == {
        (dependency, idea_id)
        for idea_id, dependencies in expected.items()
        for dependency in dependencies
    }
    atlas = next(row for row in proposal["diagrams"] if row["slug"].endswith("delivery-dependencies"))
    atlas_source = files[f'odylith/atlas/source/{atlas["slug"]}.mmd'].decode("utf-8")
    nodes_by_key = {
        row["key"]: f"workstream{index}"
        for index, row in enumerate(design["workstreams"], start=1)
    }
    for row in design["workstreams"]:
        for dependency in row["depends_on"]:
            assert (
                f'{nodes_by_key[dependency]} -->|"proposed prerequisite"| {nodes_by_key[row["key"]]}'
                in atlas_source
            )
    for record in created:
        relative_path = str(Path(record["idea_path"]).relative_to(tmp_path))
        assert f'workstream_depends_on: {",".join(expected[record["idea_id"]])}\n' in files[relative_path].decode()

    sealed = seal_compiled_greenfield_transaction(repo_root=tmp_path, transaction=transaction)

    def no_postconfirm_rebuild(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("sealed dependency topology must not be rebuilt after CONFIRM")

    monkeypatch.setattr(greenfield_traceability, "apply_backlog_traceability", no_postconfirm_rebuild)
    monkeypatch.setattr(greenfield_traceability, "build_traceability_plan", no_postconfirm_rebuild)
    greenfield_create_commit.commit_greenfield_create_transaction(
        repo_root=tmp_path, transaction_file=sealed.transaction_file,
        transaction_hash=sealed.transaction_hash, confirm=True,
    )
    assert (tmp_path / radar_path).read_bytes() == files[radar_path]
    for record in created:
        path = Path(record["idea_path"])
        assert path.read_bytes() == files[str(path.relative_to(tmp_path))]
        metadata, _ = backlog_authoring._parse_metadata_and_sections(path)
        assert metadata["workstream_depends_on"] == ",".join(expected[record["idea_id"]])
