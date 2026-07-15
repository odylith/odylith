from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import review_finding


class _PassingTribunal:
    status = "passed"
    issues: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return True

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": "passed",
            "version": "greenfield-validation-gate-v1",
            "issues": [],
            "summary": "Passed.",
            "dimensions": {"intent": {}, "artifacts": {}, "governance": {}, "release": {}},
        }


def test_rescue_stops_before_repair_callback_when_patchset_has_no_executable_fact(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-preconfirm-completion-v1",
        semantic_model=True,
        artifact_counts={"review_report": 1},
        tribunal_status="passed",
        issues=("quality lens domain_expert missing high-risk accepted assumption coverage",),
        findings=(
            review_finding(
                code="quality_lens_gap",
                surface="domain_expert",
                target_path="proposal.assumptions",
                projection_id="review_report",
                semantic_node_id="ArtifactPlanIR.assumptions",
                severity="high",
                repairability="plan_patch",
                owner="artifact_plan_projector",
                source="quality_lens",
                lens="domain_expert",
                message="quality lens domain_expert missing high-risk accepted assumption coverage",
            ),
        ),
    )
    repair_calls: list[engine.GreenfieldPreconfirmRepairContext] = []

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        engine,
        "inspect_greenfield_package",
        lambda package: SimpleNamespace(package=package, initial_report=report, report=report, passes=0, changed=False),
    )
    monkeypatch.setattr(engine, "build_greenfield_quality_lens_report", lambda _package: {"status": "failed"})
    monkeypatch.setattr(engine, "compile_greenfield_semantics", lambda _proposal: SimpleNamespace(to_dict=lambda: {}))

    def repair_callback(
        current: dict[str, object],
        context: engine.GreenfieldPreconfirmRepairContext,
    ) -> dict[str, object]:
        repair_calls.append(context)
        return {**current, "unexpected_repair": True}

    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={"intent": {"title": "Assumption Rescue"}},
            release_selector="0.0.1",
            build_prewrite=lambda current, _tribunal: SimpleNamespace(
                package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
                backlog_result={},
            ),
            repair_proposal=repair_callback,
            proposal_ready=True,
            repair_tier="auto",
            max_passes=3,
        )

    manifest = exc.value.manifest
    assert repair_calls == []
    assert manifest["stop_reason"] == "no_executable_patchset"
    assert manifest["repair_tier"] == "rescue"
    assert manifest["rescue_activated"] is True
    patchset = manifest["last_repair_patchset_request"]
    assert patchset["status"] == "repairable"
    assert patchset["operations"][0]["target_layer"] == "artifact_plan"
    assert patchset["operations"][0]["target_path"] == "assumptions"
    assert patchset["operations"][0]["replacement_fact"] == ""


def test_executable_patchset_accepts_explicit_empty_semantic_list_fact() -> None:
    patchset = {
        "operations": [
            {
                "target_layer": "semantic_model",
                "target_path": "semantic_model.domain_ontology.external_systems",
                "operation_kind": "semantic_external_systems",
                "replacement_fact": {"external_systems": []},
            }
        ]
    }

    assert engine._patchset_has_executable_operations(patchset) is True
