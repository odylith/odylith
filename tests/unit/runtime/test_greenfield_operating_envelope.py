from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    DEEP_COMPLETION_DEADLINE_SECONDS,
    GREENFIELD_OPERATING_ENVELOPE_VERSION,
    LOWER_CAPABILITY_SAFETY_PROFILE,
    RESCUE_COMPLETION_DEADLINE_SECONDS,
    STANDARD_COMPLETION_DEADLINE_SECONDS,
    greenfield_operating_envelope_receipt,
    require_supported_greenfield_operating_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    semantic_authority_execution_profiles,
)


def test_greenfield_operating_envelope_accepts_one_bounded_governance_product() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={
            "human_actors": ["Operator"],
            "external_systems": [],
            "internal_systems": ["Intake", "Review"],
        },
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )

    require_supported_greenfield_operating_envelope(receipt)

    assert receipt["version"] == GREENFIELD_OPERATING_ENVELOPE_VERSION == (
        "odylith.greenfield-operating-envelope.v20"
    )
    assert receipt["status"] == "supported"
    assert receipt["scope"]["write_boundary"] == "repo_local_governance_package"
    assert receipt["host_contract"]["confirmation_hosts"] == ["codex", "claude"]
    assert receipt["completion_contract"] == {
        "scope": "every_request_within_the_declared_operating_envelope",
        "terminal_consumer_outcomes": [
            "sealed_reviewable_preview",
            "one_material_question",
            "actionable_unsupported_evidence_notice",
            "explicit_environment_or_transaction_outcome",
        ],
        "quality_required_for_success": True,
        "partial_package_is_success": False,
        "generic_product_intent_failure_allowed": False,
        "timeout_is_success": False,
        "post_confirm_semantic_or_model_work_allowed": False,
    }
    assert receipt["latency_contract"] == {
        "measurement": "consumer_request_to_preview_or_one_material_question",
        "standard": {
            "deadline_seconds": STANDARD_COMPLETION_DEADLINE_SECONDS,
            "comparison": "strictly_less_than",
            "activation": "default",
        },
        "rescue": {
            "deadline_seconds": RESCUE_COMPLETION_DEADLINE_SECONDS,
            "comparison": "less_than_or_equal",
            "activation": "typed_semantic_or_quality_failure_only",
        },
        "deep": {
            "deadline_seconds": DEEP_COMPLETION_DEADLINE_SECONDS,
            "comparison": "less_than_or_equal",
            "activation": "explicit_consumer_or_ci_opt_in_only",
        },
        "overrun_policy": "fail_closed_with_clear_timeout_outcome",
        "unbounded_retry_allowed": False,
    }
    assert receipt["evidence_contract"]["languages"] == ["en"]
    assert receipt["evidence_contract"]["formats"] == ["semantic_intent_packet"]
    assert receipt["evidence_contract"]["semantic_intent_packet_versions"] == [
        SEMANTIC_INTENT_PACKET_VERSION
    ]
    assert receipt["complexity"]["band"] == "bounded"
    assert receipt["complexity"]["dimensions"]["actors"] == 1
    assert receipt["filesystem_contract"]["package_visibility"] == (
        "journaled_recovery_not_atomic_generation_pointer"
    )
    assert receipt["model_contract"]["semantic_authority_profiles"] == [
        SEMANTIC_REASONING_CAPABILITY_PROFILE
    ]
    assert receipt["model_contract"]["semantic_authority_execution_profiles"] == (
        semantic_authority_execution_profiles()
    )
    assert receipt["model_contract"]["non_authority_safety_profiles"] == [
        LOWER_CAPABILITY_SAFETY_PROFILE
    ]
    assert receipt["model_contract"]["lower_capability_probe"] == {
        "profile": LOWER_CAPABILITY_SAFETY_PROFILE,
        "authority_eligible": False,
        "prompt_only": True,
        "allowed_outcomes": ["clarify", "fail_safe"],
        "proof_contract": "runner_bound_independently_reviewed_safety_report_v1",
    }
    assert set(receipt["model_contract"]["semantic_authority_profiles"]).isdisjoint(
        receipt["model_contract"]["non_authority_safety_profiles"]
    )


@pytest.mark.parametrize(
    "legacy_format",
    [
        "compiled_proposal_intent",
        "in_memory_confirmed_intent",
        "json",
        "legacy_json",
        "markdown",
        "operator_prompt",
        "operator_prompt_with_edit_evidence",
        "typed_envelope_json",
    ],
)
def test_greenfield_operating_envelope_rejects_legacy_evidence_formats(legacy_format: str) -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={},
        source_format=legacy_format,
        source_size_bytes=120,
    )

    with pytest.raises(ValueError, match="outside the declared operating envelope"):
        require_supported_greenfield_operating_envelope(receipt)

    assert receipt["status"] == "unsupported"
    assert receipt["issues"] == ["unsupported_evidence_format"]


def test_greenfield_operating_envelope_rejects_unbounded_actor_fanout() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"human_actors": [f"Actor {index}" for index in range(65)]},
        source_format="semantic_intent_packet",
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
            "policy_boundaries": ["No production authority", "Preserve consent", "Audit every change"],
        },
        source_format="semantic_intent_packet",
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


def test_greenfield_operating_envelope_rejects_legacy_receipt_versions() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"internal_systems": ["Intake"]},
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )
    receipt["version"] = "odylith.greenfield-operating-envelope.v3"

    with pytest.raises(ValueError, match="version is unsupported"):
        require_supported_greenfield_operating_envelope(receipt)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("semantic_authority_profiles",), [LOWER_CAPABILITY_SAFETY_PROFILE]),
        (("non_authority_safety_profiles",), [SEMANTIC_REASONING_CAPABILITY_PROFILE]),
        (("semantic_authority_execution_profiles",), []),
        (("lower_capability_probe", "authority_eligible"), True),
        (("lower_capability_probe", "prompt_only"), False),
        (("lower_capability_probe", "allowed_outcomes"), ["commit"]),
    ],
)
def test_greenfield_operating_envelope_rejects_model_authority_boundary_mutation(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"internal_systems": ["Intake"]},
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )
    target = receipt["model_contract"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError, match="model contract is unsupported"):
        require_supported_greenfield_operating_envelope(receipt)


def test_greenfield_operating_envelope_rejects_mutated_packet_version_contract() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"internal_systems": ["Intake"]},
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )
    receipt["evidence_contract"]["semantic_intent_packet_versions"] = [
        "odylith.greenfield.semantic-intent-packet.v1"
    ]

    with pytest.raises(ValueError, match="packet version is unsupported"):
        require_supported_greenfield_operating_envelope(receipt)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("scope",), "most_requests"),
        (("terminal_consumer_outcomes",), ["sealed_reviewable_preview"]),
        (("quality_required_for_success",), False),
        (("partial_package_is_success",), True),
        (("generic_product_intent_failure_allowed",), True),
        (("timeout_is_success",), True),
        (("post_confirm_semantic_or_model_work_allowed",), True),
    ],
)
def test_greenfield_operating_envelope_rejects_completion_contract_drift(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"internal_systems": ["Intake"]},
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )
    target = receipt["completion_contract"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError, match="completion contract is unsupported"):
        require_supported_greenfield_operating_envelope(receipt)


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("standard", "deadline_seconds"), 61),
        (("standard", "comparison"), "less_than_or_equal"),
        (("rescue", "activation"), "automatic"),
        (("deep", "activation"), "automatic"),
        (("deep", "deadline_seconds"), 121),
        (("unbounded_retry_allowed",), True),
    ],
)
def test_greenfield_operating_envelope_rejects_latency_contract_drift(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"internal_systems": ["Intake"]},
        source_format="semantic_intent_packet",
        source_size_bytes=120,
    )
    target = receipt["latency_contract"]
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    with pytest.raises(ValueError, match="latency contract is unsupported"):
        require_supported_greenfield_operating_envelope(receipt)


def test_public_greenfield_copy_does_not_claim_atomic_package_visibility() -> None:
    root = Path(__file__).resolve().parents[3]
    surfaces = (
        root / "docs" / "OPERATOR_INSTRUCTIONS.md",
        root / "odylith" / "skills" / "odylith-greenfield-governance" / "SKILL.md",
        root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "skills"
        / "odylith-greenfield-governance" / "SKILL.md",
        root / "src" / "odylith" / "runtime" / "analysis_engine" / "capability_inventory.py",
        root / "src" / "odylith" / "runtime" / "domain_intelligence" / "greenfield_create_commit.py",
    )

    combined = "\n".join(path.read_text(encoding="utf-8") for path in surfaces).casefold()

    assert "commits its sealed bytes atomically" not in combined
    assert "commits records atomically" not in combined
    assert "sealed bytes atomically under rollback guard" not in combined
    assert "atomically commit the user-confirmed precompiled package" not in combined
    assert "active-generation pointer" in combined
    assert "arbitrary filesystem readers are outside this visibility guarantee" in combined
