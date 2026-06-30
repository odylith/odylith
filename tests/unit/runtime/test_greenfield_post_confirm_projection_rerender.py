from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from typing import Mapping

import pytest

from odylith.runtime.domain_intelligence import greenfield_post_confirm_engine as engine
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_post_confirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_post_confirm_patchset import patchset_request_from_findings
from odylith.runtime.domain_intelligence.greenfield_post_confirm_review import review_finding


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


def _projection_rerender_finding() -> Any:
    return review_finding(
        code="component_contract_quality",
        surface="registry",
        target_path="prewrite_package.rendered_component_specs",
        projection_id="registry",
        semantic_node_id="ArtifactPlanIR.registry",
        severity="medium",
        repairability="projection_rerender",
        owner="registry_renderer",
        source="rendered_spec_alignment",
        message="prewrite Registry package rendered component spec(s) outside active release scope: Broken Component",
    )


def test_projection_rerender_findings_stay_out_of_patchset() -> None:
    report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"component_registry_previews": 1},
        tribunal_status="passed",
        issues=("prewrite Registry package rendered component spec(s) outside active release scope: Broken Component",),
        findings=(_projection_rerender_finding(),),
    )

    issue = engine.classify_greenfield_post_confirm_issues(report)[0]
    patchset = patchset_request_from_findings(report.findings).to_dict()

    assert issue.code == "component_contract_quality"
    assert issue.path == "prewrite_package.rendered_component_specs"
    assert issue.projection_id == "registry"
    assert issue.repairability == "projection_rerender"
    assert patchset["status"] == "no_repairable_operations"


def test_post_confirm_engine_uses_direct_projection_rerender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="passed",
        issues=(_projection_rerender_finding().message,),
        findings=(_projection_rerender_finding(),),
    )
    passed_report = GreenfieldCompletionReport(
        status="passed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="passed",
        issues=(),
        findings=(),
    )
    reports = iter((failed_report, passed_report))
    build_calls: list[Mapping[str, Any]] = []
    rerender_calls: list[tuple[str, ...]] = []

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: passed_report)
    monkeypatch.setattr(engine, "build_greenfield_quality_lens_report", lambda _package: {"status": "passed"})
    monkeypatch.setattr(
        engine,
        "compile_greenfield_semantics",
        lambda _proposal: SimpleNamespace(to_dict=lambda: {"status": "passed"}),
    )

    def fake_build_prewrite(current: Mapping[str, Any], _tribunal: Any) -> SimpleNamespace:
        build_calls.append(current)
        return SimpleNamespace(
            package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
            backlog_result={"created": []},
        )

    def fake_package_repair(package: GreenfieldCompletionPackage) -> SimpleNamespace:
        report = next(reports)
        return SimpleNamespace(
            package=package,
            initial_report=report,
            report=report,
            passes=0,
            changed=False,
        )

    monkeypatch.setattr(engine, "inspect_greenfield_package", fake_package_repair)

    def fake_rerender_prewrite(
        *,
        current_proposal: Mapping[str, Any],
        tribunal: Any,
        previous_prewrite_build: Any,
        projections: tuple[str, ...],
    ) -> SimpleNamespace:
        assert tribunal.passed is True
        rerender_calls.append(tuple(projections))
        return SimpleNamespace(
            package=GreenfieldCompletionPackage(
                proposal=current_proposal,
                release_selector="0.0.1",
                rendered_component_specs={"Expected Component": "Rendered."},
            ),
            backlog_result=previous_prewrite_build.backlog_result,
        )

    result = engine.run_greenfield_post_confirm_engine(
        proposal={"intent": {"title": "Scoped Rerender"}},
        release_selector="0.0.1",
        build_prewrite=fake_build_prewrite,
        repair_proposal=lambda current, _context: current,
        rerender_prewrite=fake_rerender_prewrite,
        repair_tier="auto",
        max_passes=3,
    )

    assert result.manifest["status"] == "passed"
    assert len(build_calls) == 1
    assert rerender_calls == [("registry", "project_brief", "accepted_project", "compass", "next_steps")]


def test_post_confirm_engine_requires_rerender_callback_for_projection_rerender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-post-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="passed",
        issues=(_projection_rerender_finding().message,),
        findings=(_projection_rerender_finding(),),
    )

    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(engine, "assert_greenfield_completion_ready", lambda *_args, **_kwargs: failed_report)
    monkeypatch.setattr(engine, "build_greenfield_quality_lens_report", lambda _package: {"status": "failed"})
    monkeypatch.setattr(
        engine,
        "compile_greenfield_semantics",
        lambda _proposal: SimpleNamespace(to_dict=lambda: {"status": "failed"}),
    )
    monkeypatch.setattr(
        engine,
        "inspect_greenfield_package",
        lambda package: SimpleNamespace(
            package=package,
            initial_report=failed_report,
            report=failed_report,
            passes=0,
            changed=False,
        ),
    )

    with pytest.raises(engine.GreenfieldPostConfirmEngineError) as error:
        engine.run_greenfield_post_confirm_engine(
            proposal={"intent": {"title": "Missing Rerender Callback"}},
            release_selector="0.0.1",
            build_prewrite=lambda current, _tribunal: SimpleNamespace(
                package=GreenfieldCompletionPackage(proposal=current, release_selector="0.0.1"),
                backlog_result={"created": []},
            ),
            repair_proposal=lambda current, _context: current,
            repair_tier="auto",
            max_passes=2,
        )

    assert error.value.manifest["stop_reason"] == "missing_projection_rerender_callback"
    assert error.value.manifest["hard_blocker"]["source"] == "projection_rerender_contract"
    assert "no rerender_prewrite callback was configured" in str(error.value)
