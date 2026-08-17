from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_create_baseline
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_radar_write import (
    SEMANTIC_RADAR_WRITE_VERSION,
    compile_semantic_radar_prewrite,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    _backlog_args,
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_intent_packet,
)


def test_semantic_radar_write_preserves_typed_rows_and_exact_title_updates(
    tmp_path: Path,
) -> None:
    greenfield_create_baseline.ensure_greenfield_create_baseline(tmp_path)
    proposal = _proposal(tmp_path)
    first = _compile(tmp_path, proposal)

    assert first["validation_gate"]["version"] == SEMANTIC_RADAR_WRITE_VERSION
    assert [row["idea_id"] for row in first["created"]] == [
        f"B-{index:03d}" for index in range(1, len(proposal["backlog"]) + 1)
    ]
    for projected, created in zip(proposal["backlog"], first["created"], strict=True):
        for key in (
            "title",
            "problem",
            "customer",
            "opportunity",
            "product_view",
            "custody_state",
            "evidence_tier",
            "semantic_fact_refs",
            "semantic_fact_custody",
        ):
            assert created[key] == projected[key]
    _materialize(first)

    changed = copy.deepcopy(proposal)
    changed["backlog"][0]["problem"] = "Updated exact typed problem evidence."
    second = _compile(tmp_path, changed)
    assert second["created"][0]["idea_id"] == "B-001"
    assert second["created"][0]["idea_path"] == first["created"][0]["idea_path"]
    updated_path = str(second["created"][0]["idea_path"])
    assert "Updated exact typed problem evidence." in second["idea_files"][updated_path]
    custody = {
        "custody_state": changed["backlog"][0]["custody_state"],
        "evidence_tier": changed["backlog"][0]["evidence_tier"],
        "semantic_fact_custody": changed["backlog"][0]["semantic_fact_custody"],
        "semantic_fact_refs": changed["backlog"][0]["semantic_fact_refs"],
    }
    assert json.dumps(custody, sort_keys=True, separators=(",", ":")) in second[
        "idea_files"
    ][updated_path]
    _materialize(second)
    repeated = _compile(tmp_path, changed)
    assert repeated["backlog_index_text"] == second["backlog_index_text"]
    assert repeated["idea_files"] == second["idea_files"]


def test_semantic_radar_write_does_not_merge_token_near_duplicate_titles(
    tmp_path: Path,
) -> None:
    greenfield_create_baseline.ensure_greenfield_create_baseline(tmp_path)
    proposal = _proposal(tmp_path)
    initial = _compile(tmp_path, proposal)
    _materialize(initial)
    expanded = copy.deepcopy(proposal)
    near = copy.deepcopy(expanded["backlog"][0])
    near["title"] = "Deliver Claim Desk First Path Evidence"
    expanded["backlog"].append(near)
    planned_near = copy.deepcopy(expanded["projection_plan"]["workstreams"][0])
    planned_near["title"] = near["title"]
    expanded["projection_plan"]["workstreams"].append(planned_near)

    result = _compile(tmp_path, expanded)

    assert [row["title"] for row in result["created"]][-2:] == [
        proposal["backlog"][-1]["title"],
        "Deliver Claim Desk First Path Evidence",
    ]
    expected_id = f"B-{len(proposal['backlog']) + 1:03d}"
    assert result["created"][-1]["idea_id"] == expected_id
    assert result["created"][-1]["idea_path"] != result["created"][0]["idea_path"]
    assert expected_id in result["backlog_index_text"]
    assert result["stale_idea_ids"] == []


def test_verified_semantic_compile_bypasses_generic_radar_semantic_admission(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from odylith.runtime.governance import artifact_tribunal
    from odylith.runtime.governance import backlog_authoring
    from odylith.runtime.governance import backlog_title_contract
    from odylith.runtime.governance import validate_backlog_contract

    def forbidden(*_args: object, **_kwargs: object) -> object:
        raise AssertionError("v7 Semantic Intent entered generic Radar semantic admission")

    monkeypatch.setattr(backlog_authoring, "create_queued_backlog_items", forbidden)
    monkeypatch.setattr(artifact_tribunal, "run_governed_artifact_tribunal", forbidden)
    monkeypatch.setattr(validate_backlog_contract, "_jaccard_similarity", forbidden)
    monkeypatch.setattr(backlog_title_contract, "normalize_workstream_title", forbidden)
    proposal = _proposal(tmp_path)

    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        release_selector="0.0.1",
    )

    created = transaction.prewrite_package.backlog_result["created"]
    assert [row["title"] for row in created] == [
        row["title"] for row in proposal["backlog"]
    ]


def _proposal(repo_root: Path) -> dict[str, Any]:
    verified = require_semantic_intent_packet(
        semantic_intent_packet(),
        prompt=SEMANTIC_PROMPT,
    )
    return build_verified_semantic_proposal_for_repo(
        repo_root=repo_root,
        authority=semantic_intent_authority(verified, prompt=SEMANTIC_PROMPT),
        release_selector="0.0.1",
    )


def _compile(repo_root: Path, proposal: dict[str, Any]) -> dict[str, Any]:
    return compile_semantic_radar_prewrite(
        repo_root=repo_root,
        backlog_index_path=repo_root / "odylith/radar/source/INDEX.md",
        ideas_root=repo_root / "odylith/radar/source/ideas",
        proposal=proposal,
        policy=_backlog_args(proposal, release_selector="0.0.1"),
    )


def _materialize(result: dict[str, Any]) -> None:
    Path(str(result["backlog_index"])).write_text(
        str(result["backlog_index_text"]),
        encoding="utf-8",
    )
    for path, text in result["idea_files"].items():
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(str(text), encoding="utf-8")
