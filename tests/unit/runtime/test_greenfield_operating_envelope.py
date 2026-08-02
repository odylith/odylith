from __future__ import annotations

import pytest

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    GREENFIELD_OPERATING_ENVELOPE_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    require_supported_greenfield_operating_envelope,
)


def test_greenfield_operating_envelope_accepts_one_bounded_governance_product() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={
            "human_actors": ["Operator"],
            "external_systems": [],
            "internal_systems": ["Intake", "Review"],
        },
        source_format="operator_prompt",
        source_size_bytes=120,
    )

    require_supported_greenfield_operating_envelope(receipt)

    assert receipt["version"] == GREENFIELD_OPERATING_ENVELOPE_VERSION
    assert receipt["status"] == "supported"
    assert receipt["scope"]["write_boundary"] == "repo_local_governance_package"
    assert receipt["host_contract"]["confirmation_hosts"] == ["codex", "claude"]
    assert receipt["evidence_contract"]["languages"] == ["en"]
    assert receipt["complexity"]["band"] == "bounded"
    assert receipt["complexity"]["dimensions"]["actors"] == 1
    assert receipt["filesystem_contract"]["package_visibility"] == (
        "journaled_recovery_not_atomic_generation_pointer"
    )
    assert "lower-capability-safe-v1" in receipt["model_contract"]["profiles"]


def test_greenfield_operating_envelope_rejects_unknown_evidence_format() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={},
        source_format="host_private_chain_of_thought",
        source_size_bytes=120,
    )

    with pytest.raises(ValueError, match="outside the declared operating envelope"):
        require_supported_greenfield_operating_envelope(receipt)

    assert receipt["status"] == "unsupported"
    assert receipt["issues"] == ["unsupported_evidence_format"]


def test_greenfield_operating_envelope_rejects_unbounded_actor_fanout() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"human_actors": [f"Actor {index}" for index in range(65)]},
        source_format="markdown",
        source_size_bytes=120,
    )

    assert receipt["status"] == "unsupported"
    assert receipt["issues"] == ["too_many_human_actors"]


def test_greenfield_operating_envelope_measures_structural_complexity() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={
            "human_actors": [f"Actor {index}" for index in range(12)],
            "state_objects": [f"State {index}" for index in range(4)],
            "first_path": "An operator completes one path.",
            "external_systems": [f"System {index}" for index in range(8)],
            "ambiguities": [f"Ambiguity {index}" for index in range(3)],
            "operational_constraints": ["No production authority", "Preserve consent", "Audit every change"],
        },
        source_format="operator_prompt_with_edit_evidence",
        source_size_bytes=80 * 1024,
        source_document_count=2,
    )

    require_supported_greenfield_operating_envelope(receipt)

    assert receipt["complexity"]["band"] == "high"
    assert receipt["complexity"]["dimensions"] == {
        "evidence_bytes": 80 * 1024,
        "documents": 2,
        "actors": 12,
        "state_objects": 4,
        "paths": 1,
        "external_systems": 8,
        "internal_systems": 0,
        "contradictions": 0,
        "ambiguities": 3,
        "safety_boundaries": 3,
    }
