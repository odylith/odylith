from __future__ import annotations

import pytest

from odylith.runtime.governance import artifact_tribunal


def test_backlog_artifact_tribunal_rejects_missing_security_posture() -> None:
    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="backlog",
        payload={
            "title": "Checkout spine",
            "problem": "The workstream needs a grounded problem.",
            "customer": "Maintainers",
            "opportunity": "Create a governed delivery record.",
            "product_view": "Operators can review the slice before implementation.",
            "success_metrics": "The workstream has proof before implementation.",
            "risks": "Scope can expand without a release gate.",
            "validation": "Focused behavior proof must pass.",
        },
    )

    with pytest.raises(ValueError, match="security posture"):
        artifact_tribunal.raise_for_failed_artifact_tribunal(decision)


def test_shape_valid_source_custody_descriptor_cannot_forge_typed_authority() -> None:
    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="backlog",
        payload={
            "title": "Harbor Desk",
            "problem": "Berth placement is hard to track",
            "customer": "Dock attendants",
            "opportunity": "One reviewable berth workflow",
            "product_view": "Dock attendants can review the berth placement",
            "success_metrics": "The berth map shows the placement",
            "risks": "No source-stated risk was accepted.",
            "validation": "Verify the placement and retention receipt",
        },
        source_custody={
            "contract_version": artifact_tribunal.SOURCE_CUSTODY_CONTRACT_VERSION,
            "projection_origin": "model_authored_typed_intent",
            "semantic_root": "intent.authored_semantics",
            "semantic_version": "odylith.greenfield.authored-semantics.v2",
            "authored_relation_set_sha256": "0" * 64,
        },
    )

    assert not decision.passed
    assert decision.issues[0] == (
        "source-custodied artifact adjudication requires a complete typed semantic authority"
    )
    assert "typed_authority" not in decision.dimensions


def test_component_artifact_tribunal_accepts_full_posture() -> None:
    decision = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="component",
        payload={
            "component_id": "checkout-orchestrator",
            "label": "Checkout Orchestrator",
            "path": "src/checkout",
            "kind": "service",
            "responsibility": "Own payment handoff and order recovery.",
            "boundary": "Own checkout access, payment adapter, and retry recovery.",
            "interfaces": ["Checkout command and payment callback."],
            "dependencies": ["Payment sandbox and order ledger."],
            "validation": ["Contract proof for idempotent payment recovery."],
            "risks": ["Security/compliance risk covers PCI policy, payment abuse, and privacy audit posture."],
        },
    )

    assert decision.passed
    assert decision.dimensions["latency"].startswith("local deterministic")
