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
