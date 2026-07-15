from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from typing import Mapping

import pytest

from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_prewrite_projection_rerender
from odylith.runtime.domain_intelligence.greenfield_apply_prewrite import GreenfieldPrewriteBuild
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionPackage
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import GreenfieldCompletionReport
from odylith.runtime.domain_intelligence.greenfield_preconfirm_patchset import patchset_request_from_findings
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
        version="greenfield-preconfirm-completion-v1",
        semantic_model=True,
        artifact_counts={"component_registry_previews": 1},
        tribunal_status="passed",
        issues=("prewrite Registry package rendered component spec(s) outside active release scope: Broken Component",),
        findings=(_projection_rerender_finding(),),
    )

    issue = engine.classify_greenfield_preconfirm_issues(report)[0]
    patchset = patchset_request_from_findings(report.findings).to_dict()

    assert issue.code == "component_contract_quality"
    assert issue.path == "prewrite_package.rendered_component_specs"
    assert issue.projection_id == "registry"
    assert issue.repairability == "projection_rerender"
    assert patchset["status"] == "no_repairable_operations"


def test_preconfirm_engine_uses_direct_projection_rerender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-preconfirm-completion-v1",
        semantic_model=True,
        artifact_counts={},
        tribunal_status="passed",
        issues=(_projection_rerender_finding().message,),
        findings=(_projection_rerender_finding(),),
    )
    passed_report = GreenfieldCompletionReport(
        status="passed",
        version="greenfield-preconfirm-completion-v1",
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

    result = engine.run_greenfield_preconfirm_engine(
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
    assert rerender_calls == [
        ("registry", "project_brief", "accepted_project", "project_dashboard", "compass", "next_steps")
    ]


def test_scoped_projection_rerender_rebuilds_project_dashboard_from_source_previews(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_dashboard_payload(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        return {"schema_version": "project-dashboard", "rebuilt": True}

    def fake_next_steps(**_kwargs: Any) -> dict[str, Any]:
        return {"implementation_prompt": "fresh launch prompt"}

    monkeypatch.setattr(
        greenfield_prewrite_projection_rerender.greenfield_apply_prewrite,
        "preview_project_dashboard_payload",
        fake_dashboard_payload,
    )
    monkeypatch.setattr(
        greenfield_prewrite_projection_rerender.greenfield_experience,
        "build_next_steps",
        fake_next_steps,
    )
    previous = GreenfieldPrewriteBuild(
        package=GreenfieldCompletionPackage(
            proposal={"intent": {"title": "Dashboard Rerender"}},
            release_selector="0.0.1",
            accepted_project_preview={"accepted_at": "old", "source_launch": {"implementation_prompt": "old"}},
            next_steps_preview={"implementation_prompt": "fresh launch prompt"},
            backlog_result={"created": []},
        ),
        backlog_result={"created": []},
    )

    result = greenfield_prewrite_projection_rerender.rerender_prewrite_package_projections(
        root=tmp_path,
        previous_prewrite_build=previous,
        proposal={"intent": {"title": "Dashboard Rerender"}},
        release_selector="0.0.1",
        validation_gate={"status": "passed"},
        projections=("project_dashboard",),
        release_assignment_note="release assignment",
    )

    assert result.package.project_dashboard_preview == {"schema_version": "project-dashboard", "rebuilt": True}
    assert calls[0]["accepted_project_preview"] == {"accepted_at": "old", "source_launch": {"implementation_prompt": "old"}}
    assert calls[0]["source_launch_context"] == {"implementation_prompt": "fresh launch prompt"}


def test_scoped_projection_rerender_passes_fresh_source_launch_to_accepted_project(
    tmp_path: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_next_steps(**_kwargs: Any) -> dict[str, Any]:
        return {"implementation_prompt": "fresh accepted-project launch prompt"}

    def fake_accepted_project_memory(**kwargs: Any) -> dict[str, Any]:
        calls.append(dict(kwargs))
        return {
            "schema_version": "accepted-project",
            "source_launch": kwargs.get("source_launch_context"),
        }

    monkeypatch.setattr(
        greenfield_prewrite_projection_rerender.greenfield_experience,
        "build_next_steps",
        fake_next_steps,
    )
    monkeypatch.setattr(
        greenfield_prewrite_projection_rerender.greenfield_apply_prewrite,
        "preview_accepted_project_memory",
        fake_accepted_project_memory,
    )
    previous = GreenfieldPrewriteBuild(
        package=GreenfieldCompletionPackage(
            proposal={"intent": {"title": "Accepted Project Rerender"}},
            release_selector="0.0.1",
            accepted_project_preview={"accepted_at": "old", "source_launch": {"implementation_prompt": "stale"}},
            next_steps_preview={"implementation_prompt": "stale"},
            backlog_result={"created": []},
        ),
        backlog_result={"created": []},
    )

    result = greenfield_prewrite_projection_rerender.rerender_prewrite_package_projections(
        root=tmp_path,
        previous_prewrite_build=previous,
        proposal={"intent": {"title": "Accepted Project Rerender"}},
        release_selector="0.0.1",
        validation_gate={"status": "passed"},
        projections=("accepted_project",),
        release_assignment_note="release assignment",
    )

    assert result.package.accepted_project_preview == {
        "schema_version": "accepted-project",
        "source_launch": {"implementation_prompt": "fresh accepted-project launch prompt"},
    }
    assert calls[0]["source_launch_context"] == {"implementation_prompt": "fresh accepted-project launch prompt"}
    assert calls[0]["accepted_at"] == "old"
    assert result.package.next_steps_preview == {"implementation_prompt": "stale"}


def test_scoped_projection_rerender_refreshes_project_brief_record_text(tmp_path: Any) -> None:
    previous = GreenfieldPrewriteBuild(
        package=GreenfieldCompletionPackage(
            proposal={"intent": {"title": "Old Brief"}},
            release_selector="0.0.1",
            project_brief_record_text="# Old Brief Project Brief\n- accepted_at: prewrite\n",
            backlog_result={"created": []},
        ),
        backlog_result={"created": []},
    )

    result = greenfield_prewrite_projection_rerender.rerender_prewrite_package_projections(
        root=tmp_path,
        previous_prewrite_build=previous,
        proposal={
            "intent": {"title": "Fresh Brief"},
            "project_brief": {"project_outcome": "Fresh brief outcome."},
        },
        release_selector="0.0.1",
        validation_gate={"status": "passed"},
        projections=("project_brief",),
        release_assignment_note="release assignment",
    )

    assert result.package.project_brief_record_text.startswith("# Fresh Brief Project Brief")
    assert "- accepted_at: prewrite" in result.package.project_brief_record_text
    assert "Fresh brief outcome." in result.package.project_brief_record_text


def test_preconfirm_engine_requires_rerender_callback_for_projection_rerender(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_report = GreenfieldCompletionReport(
        status="failed",
        version="greenfield-preconfirm-completion-v1",
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

    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as error:
        engine.run_greenfield_preconfirm_engine(
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
