"""Maintainer-only proof trigger for host-planned greenfield rescue repair."""

from __future__ import annotations

from collections.abc import Mapping
import os
from typing import Any

from odylith.runtime.common.value_coercion import normalize_string
from odylith.runtime.common.value_coercion import normalize_token
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import (
    GreenfieldReviewFinding,
)
from odylith.runtime.domain_intelligence.greenfield_preconfirm_review import review_finding


STRUCTURED_RESCUE_PROOF_ENV = "ODYLITH_INTERNAL_GREENFIELD_STRUCTURED_RESCUE_PROOF"
STRUCTURED_RESCUE_PROOF_TOKEN = "host-structured-semantic-repair-v1"
STRUCTURED_RESCUE_PROOF_CODE = "structured_rescue_semantic_patch"
STRUCTURED_RESCUE_PROOF_SOURCE = "release_structured_rescue_proof"
STRUCTURED_RESCUE_PROOF_TARGET_PATH = "semantic_model.domain_ontology.external_systems"
STRUCTURED_RESCUE_PROOF_NODE = "SemanticModelIR.domain_ontology.external_systems"


def structured_rescue_proof_env(env: Mapping[str, str]) -> dict[str, str]:
    """Return an env that asks the installed path to prove host-planned rescue."""

    values = dict(env)
    values[STRUCTURED_RESCUE_PROOF_ENV] = STRUCTURED_RESCUE_PROOF_TOKEN
    return values


def structured_rescue_proof_enabled(environ: Mapping[str, str] | None = None) -> bool:
    """Return true only for the exact maintainer proof token."""

    values = environ if environ is not None else os.environ
    return normalize_string(values.get(STRUCTURED_RESCUE_PROOF_ENV)) == STRUCTURED_RESCUE_PROOF_TOKEN


def structured_rescue_proof_findings(package: Any) -> tuple[GreenfieldReviewFinding, ...]:
    """Emit a semantic PatchSet finding that requires host-planned replacement facts."""

    if not structured_rescue_proof_enabled():
        return ()
    proposal = getattr(package, "proposal", {}) if isinstance(getattr(package, "proposal", {}), Mapping) else {}
    if structured_rescue_proof_repaired(proposal):
        return ()
    return (
        review_finding(
            code=STRUCTURED_RESCUE_PROOF_CODE,
            surface="preconfirm",
            target_path=STRUCTURED_RESCUE_PROOF_TARGET_PATH,
            projection_id="review_report",
            semantic_node_id=STRUCTURED_RESCUE_PROOF_NODE,
            severity="high",
            repairability="semantic_patch",
            owner="host_structured_rescue_proof",
            source=STRUCTURED_RESCUE_PROOF_SOURCE,
            message=(
                "maintainer release proof requires one host-planned semantic repair for the accepted "
                "external system boundary before governed write"
            ),
        ),
    )


def structured_rescue_proof_repaired(proposal: Mapping[str, Any]) -> bool:
    """Return true once the semantic patch ledger proves this host-planned repair."""

    ledger = proposal.get("semantic_patch_ledger")
    if not isinstance(ledger, list):
        return False
    for entry in ledger:
        if not isinstance(entry, Mapping):
            continue
        if normalize_token(entry.get("issue_code")) != STRUCTURED_RESCUE_PROOF_CODE:
            continue
        if normalize_string(entry.get("target_path")) != STRUCTURED_RESCUE_PROOF_TARGET_PATH:
            continue
        if normalize_string(entry.get("applied_field")) != STRUCTURED_RESCUE_PROOF_TARGET_PATH:
            continue
        return True
    return False


__all__ = [
    "STRUCTURED_RESCUE_PROOF_CODE",
    "STRUCTURED_RESCUE_PROOF_ENV",
    "STRUCTURED_RESCUE_PROOF_SOURCE",
    "STRUCTURED_RESCUE_PROOF_TARGET_PATH",
    "STRUCTURED_RESCUE_PROOF_TOKEN",
    "structured_rescue_proof_enabled",
    "structured_rescue_proof_env",
    "structured_rescue_proof_findings",
    "structured_rescue_proof_repaired",
]
