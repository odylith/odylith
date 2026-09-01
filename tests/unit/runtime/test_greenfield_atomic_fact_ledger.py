from __future__ import annotations

import copy
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_atomic_fact_ledger import (
    ATOMIC_FACT_LEDGER_VERSION,
    atomic_claim_units,
    atomic_fact_ledger_hash,
    require_atomic_fact_ledger,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_envelope import (
    PRODUCT_INTENT_AUTHORITY_KEY,
)
from tests.unit.runtime.greenfield_proposal_fixtures import (
    canonical_model_authored_intent_fixture,
)


def _ledger(tmp_path: Path) -> tuple[dict[str, object], list[dict[str, object]]]:
    intent = canonical_model_authored_intent_fixture(tmp_path)
    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    assert isinstance(authority, dict)
    atoms = copy.deepcopy(authority["atomic_facts"])
    assert isinstance(atoms, list)
    return intent, atoms


def test_atomic_fact_ledger_accepts_exact_authored_custody(tmp_path: Path) -> None:
    intent, atoms = _ledger(tmp_path)

    require_atomic_fact_ledger(atoms, facts=intent)

    authority = intent[PRODUCT_INTENT_AUTHORITY_KEY]
    assert authority["atomic_ledger_version"] == ATOMIC_FACT_LEDGER_VERSION
    assert authority["atomic_custody_sha256"] == atomic_fact_ledger_hash(atoms)
    assert all(row["custody_state"] == "accepted_fact" for row in atoms)
    assert all(row["entailment_relationship"] == "exact_source_span" for row in atoms)
    assert all(row["source_span_refs"] for row in atoms)
    assert all(row["projection_links"] for row in atoms)


def test_atomic_fact_ledger_rejects_projection_drift(tmp_path: Path) -> None:
    intent, atoms = _ledger(tmp_path)
    atoms[0]["normalized_value"] = "Invented replacement fact"

    with pytest.raises(ValueError, match="invalid atom id"):
        require_atomic_fact_ledger(atoms, facts=intent)


def test_atomic_fact_ledger_rejects_missing_exact_source_reference(tmp_path: Path) -> None:
    intent, atoms = _ledger(tmp_path)
    atoms[0]["source_span_refs"] = []

    with pytest.raises(ValueError, match="invalid atom id|lacks exact source custody"):
        require_atomic_fact_ledger(atoms, facts=intent)


def test_atomic_claim_units_never_reparse_or_split_authored_text() -> None:
    text = "A reviewer records one decision, preserves its evidence, and sees the receipt."

    assert atomic_claim_units(text) == (text,)
    assert atomic_claim_units("") == ()
    assert atomic_claim_units([text]) == ()
