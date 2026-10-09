"""Fail-closed approval of one-pass host-candidate receipts."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_authored_semantics import (
    AUTHORED_RELATION_SET_SHA256_KEY,
)
from odylith.runtime.domain_intelligence.greenfield_host_candidate import (
    HOST_CANDIDATE_CONTRACT_VERSION,
    HOST_CANDIDATE_RECEIPT_VERSION,
    PASSIVE_HOST_CANDIDATE_CONTRACT_VERSIONS,
)
from odylith.runtime.domain_intelligence.greenfield_model_intent_authoring import (
    GREENFIELD_INTENT_AUTHORING_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    get_greenfield_model_profile,
    model_profile_id_for_repair_tier,
)


def greenfield_model_authoring_receipt_approved(
    *,
    model_authoring: Mapping[str, Any],
    semantic_compiler: Mapping[str, Any],
    requested_repair_tier: str,
) -> bool:
    """Validate canonical host custody and prove zero post-receipt semantic calls."""

    expected_fields = {
        "authoring_origin",
        "authoring_version",
        "runtime_semantic_model_call_count",
        "tier",
        "elapsed_seconds",
        "effective_model_window_seconds",
        "host_candidate",
        "canonical_authority",
    }
    host = model_authoring.get("host_candidate")
    canonical = model_authoring.get("canonical_authority")
    try:
        profile = get_greenfield_model_profile(
            model_profile_id_for_repair_tier(requested_repair_tier)
        )
        elapsed = float(model_authoring.get("elapsed_seconds"))
        window = float(model_authoring.get("effective_model_window_seconds"))
    except (TypeError, ValueError, OverflowError):
        return False
    return bool(
        set(model_authoring) == expected_fields
        and model_authoring.get("authoring_origin") == "host_native"
        and isinstance(host, Mapping)
        and model_authoring.get("authoring_version") == host.get("canonical_version")
        and type(model_authoring.get("runtime_semantic_model_call_count")) is int
        and model_authoring.get("runtime_semantic_model_call_count") == 0
        and model_authoring.get("tier") == profile.repair_tier
        and math.isfinite(elapsed)
        and math.isfinite(window)
        and 0.0 <= elapsed <= window <= profile.model_timeout_seconds
        and semantic_compiler.get("version")
        == "odylith.greenfield.authored-semantic-validation.v5"
        and semantic_compiler.get("status") == "passed"
        and semantic_compiler.get("semantic_owner")
        == "host_canonical_candidate"
        and type(semantic_compiler.get("post_candidate_receipt_semantic_calls")) is int
        and semantic_compiler.get("post_candidate_receipt_semantic_calls") == 0
        and isinstance(host, Mapping)
        and set(host)
        == {
            "version",
            "contract_version",
            "canonical_version",
            "source_sha256",
            "raw_candidate_sha256",
            "canonical_candidate_sha256",
            "source_duty_ledger_sha256",
            "source_duty_verifier_task_sha256",
            "source_duty_decision_set_sha256",
            "source_duty_binding_sha256",
        }
        and host.get("version") == HOST_CANDIDATE_RECEIPT_VERSION
        and host.get("contract_version") in (
            HOST_CANDIDATE_CONTRACT_VERSION, *PASSIVE_HOST_CANDIDATE_CONTRACT_VERSIONS)
        and host.get("canonical_version") == (GREENFIELD_INTENT_AUTHORING_VERSION if host.get("contract_version") in {HOST_CANDIDATE_CONTRACT_VERSION, "odylith.greenfield.host-candidate-contract.v57"} else "odylith.greenfield.intent-authoring.v79")
        and all(
            _is_sha256(host.get(key))
            for key in (
                "source_sha256",
                "raw_candidate_sha256",
                "canonical_candidate_sha256",
                "source_duty_ledger_sha256",
                "source_duty_verifier_task_sha256",
                "source_duty_decision_set_sha256",
                "source_duty_binding_sha256",
            )
        )
        and isinstance(canonical, Mapping)
        and set(canonical)
        == {
            "canonical_candidate_sha256",
            "source_sha256",
            "product_facts_sha256",
            AUTHORED_RELATION_SET_SHA256_KEY,
        }
        and all(_is_sha256(value) for value in canonical.values())
        and canonical.get("canonical_candidate_sha256")
        == host.get("canonical_candidate_sha256")
        and canonical.get("source_sha256") == host.get("source_sha256")
    )


def _is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and not set(value) - set("0123456789abcdef")
    )


__all__ = ["greenfield_model_authoring_receipt_approved"]
