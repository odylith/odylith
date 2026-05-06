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
