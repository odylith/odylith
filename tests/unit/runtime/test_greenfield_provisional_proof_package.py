"""A proposed checkpoint cannot substitute for a source-backed terminal result."""

from __future__ import annotations

from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import (
    GreenfieldClarificationRequired,
    materialize_model_authored_intent,
)
from odylith.runtime.domain_intelligence.greenfield_model_outcomes import (
    GreenfieldModelAuthoringError,
)
from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    STANDARD_PROFILE_ID,
)
from tests.unit.runtime.greenfield_model_authoring_fixtures import (
    AdmittingReviewProvider,
    RemainingCandidateProvider,
    StructuredAuthoringProvider,
)
from tests.unit.runtime.test_greenfield_provisional_proof_authoring import (
    provisional_proof_response,
)


def test_commit_only_version_admission_matches_preconfirm_custody() -> None:
    from odylith.runtime.domain_intelligence.greenfield_commit_transaction import (
        _CURRENT_SEALED_INTENT_VERSIONS,
    )
    from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
        ATOMIC_FACT_LEDGER_VERSION,
        PRODUCT_INTENT_AUTHORITY_VERSION,
        PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        PRODUCT_INTENT_LEDGER_VERSION,
    )

    assert _CURRENT_SEALED_INTENT_VERSIONS == {
        "version": PRODUCT_INTENT_AUTHORITY_VERSION,
        "envelope_schema_version": PRODUCT_INTENT_ENVELOPE_SCHEMA_VERSION,
        "ledger_version": PRODUCT_INTENT_LEDGER_VERSION,
        "atomic_ledger_version": ATOMIC_FACT_LEDGER_VERSION,
    }


def test_proposed_checkpoint_requires_first_path_clarification_before_packaging(
    tmp_path: Path,
) -> None:
    source, response = provisional_proof_response()
    provider = RemainingCandidateProvider(response)
    reviewer = StructuredAuthoringProvider({
        "outcome": "clarification_required",
        "issue": None,
        "clarification": {"material_dimension": "first_path"},
        "admission_witness": None,
    })

    with pytest.raises(GreenfieldClarificationRequired) as raised:
        materialize_model_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            authoring_provider=provider,
            participant_provider_factory=provider.participant_provider,
            review_provider_factory=lambda: reviewer,
            authoring_profile_id=STANDARD_PROFILE_ID,
            authoring_timeout_seconds=60,
        )

    assert raised.value.required_fields == ("first_path",)
    assert reviewer.calls == 1


def test_proposed_checkpoint_cannot_be_admitted_without_a_source_terminal(
    tmp_path: Path,
) -> None:
    source, response = provisional_proof_response()
    provider = RemainingCandidateProvider(response)

    with pytest.raises(GreenfieldModelAuthoringError, match="could not be verified"):
        materialize_model_authored_intent(
            prompt=source,
            repo_root=tmp_path,
            authoring_provider=provider,
            participant_provider_factory=provider.participant_provider,
            review_provider_factory=AdmittingReviewProvider,
            authoring_profile_id=STANDARD_PROFILE_ID,
            authoring_timeout_seconds=60,
        )
