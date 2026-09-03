from __future__ import annotations

import argparse
import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_model_intent_authoring
from odylith.runtime.domain_intelligence import greenfield_proposals_cli
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    author_greenfield_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    prepare_model_authoring_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    AUTHORED_LIST_FIELDS,
    GREENFIELD_OPERATING_ENVELOPE_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_CITATIONS,
    greenfield_operating_envelope_receipt,
)
from odylith.runtime.domain_intelligence.greenfield_operating_envelope import (
    MAX_AUTHORED_LIST_ITEMS,
    MAX_CONTRADICTIONS,
    MAX_EVIDENCE_BYTES,
    MAX_STATE_OBJECTS,
    SUPPORTED_PUBLIC_INPUT_FORMATS,
    require_supported_greenfield_operating_envelope,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
    RESCUE_PROFILE_ID,
    STANDARD_PROFILE_ID,
    get_greenfield_model_profile,
)


def _model_observation(profile_id: str = STANDARD_PROFILE_ID) -> dict[str, object]:
    profile = get_greenfield_model_profile(profile_id)
    return {
        "profile_id": profile.profile_id,
        "provider": profile.provider,
        "model": profile.model,
        "reasoning_effort": profile.reasoning_effort,
        "effective_timeout_seconds": profile.model_timeout_seconds,
        "authoring_tier": "standard",
    }


def test_published_operating_envelope_matches_the_runtime_contract() -> None:
    root = Path(__file__).resolve().parents[3]
    published = (root / "docs/specs/greenfield-operating-envelope.md").read_text(
        encoding="utf-8"
    )

    assert GREENFIELD_OPERATING_ENVELOPE_VERSION in published
    assert "64 KiB" in published
    assert "8 MiB" not in published
    assert "journaled crash recovery, not package-level atomic" in published
    for profile_id in (STANDARD_PROFILE_ID, RESCUE_PROFILE_ID, DEEP_PROFILE_ID):
        profile = get_greenfield_model_profile(profile_id)
        assert profile_id in published
        assert f"{int(profile.consumer_budget_seconds)}-second" in published


def test_greenfield_operating_envelope_accepts_one_bounded_governance_product() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={
            "human_actors": ["Operator"],
            "external_systems": [],
            "internal_systems": ["Intake", "Review"],
        },
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
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
    assert RESCUE_PROFILE_ID in receipt["model_contract"]["profiles"]
    assert receipt["evidence_contract"]["public_input_formats"] == list(SUPPORTED_PUBLIC_INPUT_FORMATS)
    assert set(receipt["evidence_contract"]["public_input_formats"]).isdisjoint(
        receipt["evidence_contract"]["internal_custody_formats"]
    )


def test_receipt_mutation_cannot_change_the_canonical_host_contract() -> None:
    first = greenfield_operating_envelope_receipt(
        facts={},
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
    )
    first["host_contract"]["confirmation_hosts"].append("untrusted-host")

    second = greenfield_operating_envelope_receipt(
        facts={},
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
    )

    assert second["host_contract"]["confirmation_hosts"] == ["codex", "claude"]


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
        facts={"human_actors": [f"Actor {index}" for index in range(MAX_AUTHORED_LIST_ITEMS + 1)]},
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
    )

    assert receipt["status"] == "unsupported"
    assert receipt["issues"] == ["too_many_human_actors"]


def test_greenfield_operating_envelope_measures_structural_complexity() -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={
            "human_actors": [f"Actor {index}" for index in range(12)],
            "state_object": "Review state",
            "first_path": "An operator completes one path.",
            "external_systems": [f"System {index}" for index in range(8)],
            "ambiguities": [f"Ambiguity {index}" for index in range(3)],
            "operational_constraints": ["No production authority", "Preserve consent", "Audit every change"],
        },
        source_format="operator_prompt_with_edit_evidence",
        source_size_bytes=48 * 1024,
        source_document_count=2,
        model_authoring=_model_observation(),
    )

    require_supported_greenfield_operating_envelope(receipt)

    assert receipt["complexity"]["band"] == "high"
    assert receipt["complexity"]["dimensions"] == {
        "evidence_bytes": 48 * 1024,
        "documents": 2,
        "actors": 12,
        "state_objects": 1,
        "paths": 1,
        "external_systems": 8,
        "internal_systems": 0,
        "contradictions": 0,
        "ambiguities": 3,
        "safety_boundaries": 3,
        "success_metrics": 0,
        "evidence_requirements": 0,
        "component_responsibilities": 0,
        "assumptions": 0,
        "non_goals": 0,
    }


def test_authored_caps_are_truthful_for_singular_state_and_unsupported_contradictions() -> None:
    assert MAX_STATE_OBJECTS == 1
    assert MAX_CONTRADICTIONS == 0
    assert MAX_EVIDENCE_BYTES == 64 * 1024

    receipt = greenfield_operating_envelope_receipt(
        facts={"state_objects": ["one", "two"], "contradictions": ["conflict"]},
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
    )

    assert receipt["status"] == "unsupported"
    assert "too_many_state_objects" in receipt["issues"]
    assert "contradictions_not_supported" in receipt["issues"]


class _ProviderThatMustNotRun:
    provider_name = "codex-cli"

    def __init__(self) -> None:
        self.calls = 0

    def generate_structured(self, *, request: object) -> None:
        del request
        self.calls += 1
        raise AssertionError("structurally unsupported evidence reached the provider")


def test_max_plus_one_model_input_is_rejected_before_provider_call() -> None:
    provider = _ProviderThatMustNotRun()

    with pytest.raises(ValueError, match="evidence_too_large"):
        author_greenfield_intent(
            evidence_text="x" * (MAX_EVIDENCE_BYTES + 1),
            provider=provider,
            source_format="operator_prompt",
            source_document_count=1,
            source_language="en",
        )

    assert provider.calls == 0


def test_timeout_never_invents_a_missing_model_profile_before_the_call() -> None:
    provider = _ProviderThatMustNotRun()

    with pytest.raises(ValueError, match="unsupported Greenfield model profile: <empty>"):
        author_greenfield_intent(
            evidence_text="Create one bounded product.",
            provider=provider,
            model_profile_id="",
            timeout_seconds=84.0,
        )

    assert provider.calls == 0


def test_public_compile_rejects_oversize_before_provider_discovery(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    provider_discovery_calls = 0

    def forbidden_provider_discovery(**_kwargs: object) -> None:
        nonlocal provider_discovery_calls
        provider_discovery_calls += 1
        raise AssertionError("oversize evidence reached provider discovery")

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        forbidden_provider_discovery,
    )

    with pytest.raises(ValueError, match="evidence_too_large"):
        greenfield_proposals_cli._compile_prompt_evidence_transaction(
            repo_root=tmp_path,
            prompt="x" * (MAX_EVIDENCE_BYTES + 1),
            edit_evidence="",
            release_selector="",
        )

    assert provider_discovery_calls == 0


def test_edit_read_time_reduces_the_provider_window_before_discovery(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    provider_discovery_calls = 0

    def forbidden_provider_discovery(**_kwargs: object) -> None:
        nonlocal provider_discovery_calls
        provider_discovery_calls += 1
        raise AssertionError("expired evidence-read budget reached provider discovery")

    monkeypatch.setattr(
        greenfield_proposals_cli,
        "_greenfield_authoring_provider",
        forbidden_provider_discovery,
    )
    monkeypatch.setattr(greenfield_proposals_cli.time, "perf_counter", lambda: 84.0)

    with pytest.raises(RuntimeError, match="while reading evidence"):
        greenfield_proposals_cli._compile_prompt_evidence_transaction(
            repo_root=tmp_path,
            prompt="Create one bounded product.",
            edit_evidence="A bounded edit.",
            release_selector="",
            repair_tier="rescue",
            started_at=0.0,
        )

    assert provider_discovery_calls == 0


def test_late_pending_stage_is_retired_before_the_deadline_error_returns(
    monkeypatch,
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    now = [59.0]
    confirmable = False
    transaction_hash = "a" * 64
    transaction = argparse.Namespace(
        transaction_hash=transaction_hash,
        quality_manifest={"budget_seconds": 60.0},
    )

    def stage_pending_transaction(**_kwargs: object) -> Path:
        nonlocal confirmable
        confirmable = True
        now[0] = 60.0
        return tmp_path / "pending.json"

    def discard_pending_transaction(**_kwargs: object) -> None:
        nonlocal confirmable
        confirmable = False

    store = greenfield_proposals_cli.greenfield_pending_transaction_store
    monkeypatch.setattr(store, "stage_pending_transaction", stage_pending_transaction)
    monkeypatch.setattr(store, "discard_pending_transaction", discard_pending_transaction)

    with pytest.raises(RuntimeError, match="no records were created"):
        greenfield_proposals_cli._stage_pending_transaction_with_deadline(
            repo_root=tmp_path,
            transaction=transaction,
            started_at=0.0,
            clock=lambda: now[0],
        )

    assert confirmable is False


def test_non_english_contract_is_rejected_without_lexical_detection_or_provider_call() -> None:
    provider = _ProviderThatMustNotRun()

    with pytest.raises(ValueError, match="unsupported_evidence_language"):
        author_greenfield_intent(
            evidence_text="A structurally valid project description.",
            provider=provider,
            source_format="operator_prompt",
            source_document_count=1,
            source_language="fr",
        )

    assert provider.calls == 0


def test_prompt_and_edit_are_counted_as_one_and_two_exact_documents() -> None:
    prompt_only = prepare_model_authoring_evidence(prompt="Create one bounded product.")
    with_edit = prepare_model_authoring_evidence(
        prompt="Create one bounded product.",
        edit_evidence="Use a visible completion receipt.",
    )

    assert prompt_only.source_format == "operator_prompt"
    assert prompt_only.source_document_count == 1
    assert prompt_only.admission["documents"] == 1
    assert prompt_only.admission["bytes"] == len(prompt_only.evidence_source.encode("utf-8"))
    assert with_edit.source_format == "operator_prompt_with_edit_evidence"
    assert with_edit.source_document_count == 2
    assert with_edit.admission["documents"] == 2
    assert with_edit.admission["bytes"] == len(with_edit.evidence_source.encode("utf-8"))


def test_edit_file_reader_requests_only_max_plus_one_bytes(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    requested_sizes: list[int] = []

    class _BoundedReader:
        def __enter__(self) -> "_BoundedReader":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            requested_sizes.append(size)
            return b"x" * size

    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: _BoundedReader())
    args = argparse.Namespace(edit="", edit_evidence="large-edit.md")

    with pytest.raises(ValueError, match="exceeds the declared model-input bound"):
        greenfield_proposals_cli._edit_evidence_from_args(args, repo_root=tmp_path)

    assert requested_sizes == [MAX_EVIDENCE_BYTES + 1]


def test_edit_file_reader_rejects_invalid_utf8(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    class _InvalidUtf8Reader:
        def __enter__(self) -> "_InvalidUtf8Reader":
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self, size: int) -> bytes:
            assert size == MAX_EVIDENCE_BYTES + 1
            return b"\xff"

    monkeypatch.setattr(Path, "open", lambda *_args, **_kwargs: _InvalidUtf8Reader())
    args = argparse.Namespace(edit="", edit_evidence="invalid-edit.md")

    with pytest.raises(ValueError, match="valid UTF-8"):
        greenfield_proposals_cli._edit_evidence_from_args(args, repo_root=tmp_path)


def test_authoring_schema_and_operating_receipt_use_the_same_caps() -> None:
    schema_properties = greenfield_model_intent_authoring._AUTHORING_SCHEMA["properties"]
    typed_facts = schema_properties["facts"]["anyOf"][0]

    assert tuple(greenfield_model_intent_authoring._LIST_FIELDS) == AUTHORED_LIST_FIELDS
    assert all(
        typed_facts["properties"][field]["maxItems"] == MAX_AUTHORED_LIST_ITEMS
        for field in greenfield_model_intent_authoring._REPEATED_SOURCE_FIELDS
    )
    assert MAX_AUTHORED_CITATIONS == 256
    assert schema_properties["assumptions"]["maxItems"] == MAX_AUTHORED_LIST_ITEMS
    assert schema_properties["ambiguities"]["maxItems"] == MAX_AUTHORED_LIST_ITEMS
    assert MAX_AUTHORED_LIST_ITEMS == 32


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (("evidence_contract", "maximum_bytes"), MAX_EVIDENCE_BYTES + 1),
        (("complexity", "dimensions", "actors"), MAX_AUTHORED_LIST_ITEMS + 1),
        (("complexity", "limits", "actors"), MAX_AUTHORED_LIST_ITEMS + 1),
        (("scope", "product_count"), 2),
        (("filesystem_contract", "locking"), "best_effort"),
        (("host_contract", "other_hosts"), "unrestricted"),
        (("model_contract", "lower_capability_behavior"), "invent_and_continue"),
        (("model_contract", "observed", "authoring_tier"), "deep"),
    ),
)
def test_validator_rejects_mutated_supported_contract_sections(
    path: tuple[str, ...],
    replacement: object,
) -> None:
    receipt = greenfield_operating_envelope_receipt(
        facts={"human_actors": ["Operator"], "first_path": "Complete one task."},
        source_format="operator_prompt",
        source_size_bytes=120,
        model_authoring=_model_observation(),
    )
    mutated = copy.deepcopy(receipt)
    owner: dict[str, object] = mutated
    for key in path[:-1]:
        nested = owner[key]
        assert isinstance(nested, dict)
        owner = nested
    owner[path[-1]] = replacement

    with pytest.raises(ValueError):
        require_supported_greenfield_operating_envelope(mutated)
