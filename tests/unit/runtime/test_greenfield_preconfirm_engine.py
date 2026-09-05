"""Authored-only contract proof for Greenfield pre-confirm validation."""

from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from odylith.runtime.domain_intelligence import greenfield_preconfirm_engine as engine
from odylith.runtime.domain_intelligence import greenfield_proposals as proposals
from odylith.runtime.domain_intelligence.greenfield_preconfirm_completion import (
    GreenfieldCompletionReport,
)
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


def _report(*, passed: bool, typed: bool = True) -> GreenfieldCompletionReport:
    message = "typed structural validation failed"
    findings = (
        review_finding(
            code="semantic_alignment",
            surface="radar",
            target_path="proposal.backlog[0]",
            projection_id="radar",
            semantic_node_id="intent.authored_semantics",
            severity="high",
            repairability="unrepairable",
            owner="typed_package_artifact_gate",
            source="semantic_projection_alignment",
            message=message,
        ),
    ) if typed and not passed else ()
    return GreenfieldCompletionReport(
        status="passed" if passed else "failed",
        version="greenfield-pre-confirm-completion-v1",
        semantic_model=True,
        artifact_counts={"workstreams": 1, "components": 1, "diagrams": 4},
        tribunal_status="passed",
        issues=() if passed else (message,),
        findings=findings,
    )


def _install_authored_gate(
    monkeypatch: pytest.MonkeyPatch,
    *,
    report: GreenfieldCompletionReport,
) -> None:
    monkeypatch.setattr(engine, "sealed_authored_projection", lambda _proposal: True)
    monkeypatch.setattr(engine, "run_greenfield_tribunal", lambda *_args, **_kwargs: _PassingTribunal())
    monkeypatch.setattr(
        engine,
        "build_greenfield_package_report",
        lambda _package, **_kwargs: report,
    )


def _prewrite(current: object, _tribunal: object) -> SimpleNamespace:
    return SimpleNamespace(package=SimpleNamespace(proposal=current), backlog_result={})


def _install_transaction_compile_seam(
    monkeypatch: pytest.MonkeyPatch,
    *,
    proposal: dict[str, Any],
    package_proposal: dict[str, Any],
) -> tuple[object, dict[str, Any]]:
    transaction = object()
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        proposals.greenfield_programs,
        "proposal_release_selector",
        lambda _proposal, selector: selector,
    )
    monkeypatch.setattr(proposals, "require_product_intent_authority", lambda _authority: None)
    monkeypatch.setattr(
        proposals,
        "require_relation_authority_parity",
        lambda _intent, _authority: True,
    )
    monkeypatch.setattr(proposals, "product_facts_hash", lambda _intent: "sealed-hash")
    monkeypatch.setattr(
        proposals,
        "require_distinct_supplied_diagram_sources",
        lambda _diagrams: None,
    )
    monkeypatch.setattr(
        proposals,
        "_build_authored_prewrite_package",
        lambda **_kwargs: (
            proposal,
            _PassingTribunal(),
            _prewrite(package_proposal, _PassingTribunal()),
            {"status": "passed"},
        ),
    )
    monkeypatch.setattr(
        proposals,
        "run_greenfield_tribunal",
        lambda *_args, **_kwargs: pytest.fail("transaction compiler reran the authored Tribunal"),
    )
    monkeypatch.setattr(
        proposals,
        "build_product_create_transaction",
        lambda **kwargs: captured.update(kwargs) or transaction,
    )
    monkeypatch.setattr(
        proposals,
        "require_product_create_transaction_verified",
        lambda _transaction: None,
    )
    return transaction, captured


def test_classifier_preserves_typed_finding_ownership() -> None:
    issue = engine.classify_greenfield_preconfirm_issues(_report(passed=False))[0]

    assert issue.code == "semantic_alignment"
    assert issue.path == "proposal.backlog[0]"
    assert issue.semantic_node_id == "intent.authored_semantics"
    assert issue.repairability == "unrepairable"
    assert issue.owner == "typed_package_artifact_gate"


def test_classifier_fails_closed_for_uncategorized_package_issue() -> None:
    issue = engine.classify_greenfield_preconfirm_issues(
        _report(passed=False, typed=False)
    )[0]

    assert issue.code == "uncategorized_quality_issue"
    assert issue.repairability == "unrepairable"
    assert issue.owner == "typed_package_artifact_gate"
    assert issue.source == "package_quality"


def test_relation_free_proposal_is_rejected_before_prewrite() -> None:
    calls: list[object] = []

    with pytest.raises(ValueError, match="sealed model-authored"):
        engine.run_greenfield_preconfirm_engine(
            proposal={"intent": {"title": "Unsupported"}},
            release_selector="0.0.1",
            build_prewrite=lambda *_args: calls.append(object()),
            proposal_ready=True,
        )

    assert calls == []


def test_transaction_compiler_seals_the_once_validated_package_without_reinterpretation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "projection_origin": "model_authored_typed_intent",
        "intent": {"title": "Harbor Desk"},
        "product_intent_authority": {"product_facts_sha256": "sealed-hash"},
        "diagrams": [],
    }
    package_proposal = dict(proposal)
    expected, captured = _install_transaction_compile_seam(
        monkeypatch,
        proposal=proposal,
        package_proposal=package_proposal,
    )

    result = proposals.compile_greenfield_create_transaction(
        repo_root=Path("."),
        proposal=proposal,
        release_selector="0.0.1",
    )

    assert result is expected
    assert captured["proposal"] is package_proposal


def test_transaction_compiler_rejects_package_drift_instead_of_rebinding(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    proposal = {
        "projection_origin": "model_authored_typed_intent",
        "intent": {"title": "Harbor Desk"},
        "product_intent_authority": {"product_facts_sha256": "sealed-hash"},
        "diagrams": [],
    }
    package_proposal = {**proposal, "intent": {"title": "Reinterpreted Harbor Desk"}}
    _expected, captured = _install_transaction_compile_seam(
        monkeypatch,
        proposal=proposal,
        package_proposal=package_proposal,
    )

    with pytest.raises(ValueError, match="drifted from the sealed model-authored proposal"):
        proposals.compile_greenfield_create_transaction(
            repo_root=Path("."),
            proposal=proposal,
            release_selector="0.0.1",
        )

    assert captured == {}


def test_authored_package_passes_in_one_validation_pass(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_authored_gate(monkeypatch, report=_report(passed=True))
    calls: list[object] = []
    report_calls: list[object] = []
    monkeypatch.setattr(
        engine,
        "build_greenfield_package_report",
        lambda package, **_kwargs: report_calls.append(package) or _report(passed=True),
    )

    result = engine.run_greenfield_preconfirm_engine(
        proposal={"projection_origin": "model_authored_typed_intent"},
        release_selector="0.0.1",
        build_prewrite=lambda current, tribunal: calls.append(current) or _prewrite(current, tribunal),
        proposal_ready=True,
        model_authoring_receipt={
            "authoring_version": "odylith.greenfield.model-intent-authoring.v1",
            "semantic_model_call_count": 2,
            "tier": "standard",
            "elapsed_seconds": 12.0,
        },
        clock=lambda: 0.0,
    )

    assert len(calls) == 1
    assert len(report_calls) == 1
    assert result.report.passed
    assert result.manifest["status"] == "passed"
    assert result.manifest["passes"] == 1
    assert result.manifest["validation_passes"] == 1
    assert "repaired_issue_codes" not in result.manifest
    assert "patchset_request" not in result.manifest
    assert result.manifest["semantic_compiler"] == {
        "version": "odylith.greenfield.authored-semantic-validation.v3",
        "status": "passed",
        "semantic_owner": "validated_model_authored_intent",
        "post_authoring_interpretation_calls": 0,
    }
    assert result.manifest["model_authoring"]["semantic_model_call_count"] == 2


def test_authored_quality_failure_is_immediate_and_unrepaired(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_authored_gate(monkeypatch, report=_report(passed=False))
    calls: list[object] = []

    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={"projection_origin": "model_authored_typed_intent"},
            release_selector="0.0.1",
            build_prewrite=lambda current, tribunal: calls.append(current) or _prewrite(current, tribunal),
            proposal_ready=True,
            clock=lambda: 0.0,
        )

    assert len(calls) == 1
    assert exc.value.manifest["stop_reason"] == "model_authored_validation_failed"
    assert exc.value.manifest["passes"] == 1
    assert exc.value.manifest["issue_codes"] == ["semantic_alignment"]


@pytest.mark.parametrize(
    ("requested", "authored", "budget", "rescue"),
    (
        ("auto", "standard", 60.0, False),
        ("standard", "standard", 60.0, False),
        ("rescue", "rescue", 90.0, True),
        ("deep", "deep", 120.0, True),
    ),
)
def test_profiles_keep_exact_consumer_budgets(
    monkeypatch: pytest.MonkeyPatch,
    requested: str,
    authored: str,
    budget: float,
    rescue: bool,
) -> None:
    _install_authored_gate(monkeypatch, report=_report(passed=True))

    result = engine.run_greenfield_preconfirm_engine(
        proposal={"projection_origin": "model_authored_typed_intent"},
        release_selector="0.0.1",
        build_prewrite=_prewrite,
        proposal_ready=True,
        repair_tier=requested,
        model_authoring_tier=authored,
        clock=lambda: 0.0,
    )

    assert result.manifest["budget_seconds"] == budget
    assert result.manifest["repair_tier"] == authored
    assert result.manifest["rescue_activated"] is rescue


def test_profile_mismatch_is_rejected_before_prewrite(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_authored_gate(monkeypatch, report=_report(passed=True))
    calls: list[object] = []

    with pytest.raises(ValueError, match="does not match"):
        engine.run_greenfield_preconfirm_engine(
            proposal={"projection_origin": "model_authored_typed_intent"},
            release_selector="0.0.1",
            build_prewrite=lambda *_args: calls.append(object()),
            proposal_ready=True,
            repair_tier="rescue",
            model_authoring_tier="standard",
        )

    assert calls == []


def test_budget_exhaustion_before_prewrite_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(engine, "sealed_authored_projection", lambda _proposal: True)
    calls: list[object] = []

    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={"projection_origin": "model_authored_typed_intent"},
            release_selector="0.0.1",
            build_prewrite=lambda *_args: calls.append(object()),
            proposal_ready=True,
            elapsed_before_start_seconds=60.0,
            clock=lambda: 0.0,
        )

    assert calls == []
    assert exc.value.manifest["stop_reason"] == "time_budget_exhausted"
    assert exc.value.manifest["budget_seconds"] == 60.0
    assert exc.value.manifest["pass_records"] == []


def test_budget_crossed_during_package_build_rejects_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_authored_gate(monkeypatch, report=_report(passed=True))
    now = {"seconds": 0.0}

    def build(current: object, tribunal: object) -> SimpleNamespace:
        now["seconds"] = 60.0
        return _prewrite(current, tribunal)

    with pytest.raises(engine.GreenfieldPreconfirmEngineError) as exc:
        engine.run_greenfield_preconfirm_engine(
            proposal={"projection_origin": "model_authored_typed_intent"},
            release_selector="0.0.1",
            build_prewrite=build,
            proposal_ready=True,
            clock=lambda: now["seconds"],
        )

    assert exc.value.manifest["stop_reason"] == "time_budget_exhausted"
    assert exc.value.manifest["elapsed_seconds"] == 60.0


def test_engine_surface_has_no_repair_or_rerender_callback() -> None:
    parameters = inspect.signature(engine.run_greenfield_preconfirm_engine).parameters
    assert "repair_proposal" not in parameters
    assert "prepare_repair_context" not in parameters
    assert "rerender_prewrite" not in parameters
    assert "max_passes" not in parameters


def test_engine_source_has_no_legacy_repair_imports() -> None:
    source = Path(engine.__file__).read_text(encoding="utf-8")
    for forbidden in (
        "greenfield_preconfirm_patch_apply",
        "greenfield_preconfirm_rescue_planner",
        "greenfield_semantic_compiler",
        "greenfield_quality_lenses",
        "tribunal_patch_planner",
    ):
        assert forbidden not in source
