"""A proposed checkpoint cannot substitute for a source-backed terminal result."""

from __future__ import annotations

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
