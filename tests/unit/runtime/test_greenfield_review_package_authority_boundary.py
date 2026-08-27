"""Contract tests for the Greenfield review-package authority boundary."""

from __future__ import annotations

import ast
import copy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_create_transaction import (
    ProductCreateTransaction,
    product_create_transaction_from_dict,
    product_create_transaction_hash,
    product_create_transaction_to_dict,
)
from odylith.runtime.domain_intelligence.greenfield_product_intent_binding import (
    PRODUCT_INTENT_AUTHORITY_KEY,
    PRODUCT_INTENT_REVIEW_BINDING_KEY,
    product_intent_review_binding,
    require_product_intent_review_binding,
)
from odylith.runtime.domain_intelligence.greenfield_sealed_product_intent_authority import (
    product_intent_authority_snapshot_hash,
    require_product_intent_authority_structure,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_intent_with_authority,
)


_PRIVATE_LABEL = "Plum Sextant"


def test_review_package_contains_only_digest_binding_not_private_authority(
    tmp_path: Path,
) -> None:
    authority = _authority_with_private_evidence()
    proposal = _proposal(tmp_path, authority)
    serialized = _canonical_text(proposal)

    assert proposal[PRODUCT_INTENT_REVIEW_BINDING_KEY] == product_intent_review_binding(
        authority
    )
    assert set(proposal[PRODUCT_INTENT_REVIEW_BINDING_KEY]) == {
        "version",
        "authority_version",
        "authority_snapshot_sha256",
        "semantic_intent_sha256",
        "semantic_meaning_sha256",
        "product_facts_sha256",
    }
    assert PRODUCT_INTENT_AUTHORITY_KEY not in proposal
    assert "evidence_sources" not in serialized
    assert "semantic_source_meaning_graph" not in serialized
    assert _PRIVATE_LABEL not in serialized
    assert authority["evidence_sources"]["operator_prompt"] not in serialized


def test_review_binding_has_one_owner_and_no_proposal_authority_fallback() -> None:
    root = Path(__file__).resolve().parents[3]
    domain_root = root / "src/odylith/runtime/domain_intelligence"
    owners: list[str] = []
    stale_proposal_authority: list[str] = []
    for path in domain_root.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        if any(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "product_intent_review_binding"
            for node in ast.walk(tree)
        ):
            owners.append(path.name)
        if path.name != "greenfield_product_intent_binding.py" and any(
            token in source
            for token in (
                "proposal.get(PRODUCT_INTENT_AUTHORITY_KEY)",
                "proposal[PRODUCT_INTENT_AUTHORITY_KEY]",
            )
        ):
            stale_proposal_authority.append(path.name)

    assert owners == ["greenfield_product_intent_binding.py"]
    assert stale_proposal_authority == []


@pytest.mark.parametrize("mutation", ("missing", "extra", "digest", "embedded_authority"))
def test_review_binding_rejects_every_noncanonical_shape(
    tmp_path: Path, mutation: str
) -> None:
    authority = _authority_with_private_evidence()
    proposal = _proposal(tmp_path, authority)
    candidate = copy.deepcopy(proposal)
    if mutation == "missing":
        candidate.pop(PRODUCT_INTENT_REVIEW_BINDING_KEY)
    elif mutation == "extra":
        candidate[PRODUCT_INTENT_REVIEW_BINDING_KEY]["extra"] = "not allowed"
    elif mutation == "digest":
        candidate[PRODUCT_INTENT_REVIEW_BINDING_KEY]["product_facts_sha256"] = "0" * 64
    else:
        candidate[PRODUCT_INTENT_AUTHORITY_KEY] = authority

    with pytest.raises(ValueError, match="review (binding|package embeds)"):
        require_product_intent_review_binding(candidate, authority)


def test_transaction_keeps_one_exact_private_authority_while_all_writes_stay_clean(
    tmp_path: Path,
) -> None:
    authority = _authority_with_private_evidence()
    proposal = _proposal(tmp_path, authority)
    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )
    payload = product_create_transaction_to_dict(transaction)
    governed_previews = {
        "review_package": transaction.prewrite_package.proposal,
        "compiled_package_review": transaction.prewrite_package.proposal,
        "accepted_project": transaction.prewrite_package.accepted_project_preview,
        "project_brief": transaction.prewrite_package.project_brief_record_text,
        "component_specs": transaction.prewrite_package.rendered_component_specs,
        "atlas": transaction.prewrite_package.rendered_atlas_sources,
        "write_set": transaction.prewrite_package.repository_write_set,
    }
    governed_text = _canonical_text(governed_previews)

    assert transaction.intent_authority == authority
    assert payload["intent_authority"] == authority
    assert "proposal" not in payload
    assert "backlog_result" not in payload
    assert payload["prewrite_package"]["proposal"] == proposal
    payload_text = _canonical_text(payload)
    assert payload_text.count(_PRIVATE_LABEL) == 1
    assert payload_text.count('"evidence_sources":') == 1
    assert payload_text.count('"semantic_source_meaning_graph":') == 1
    assert _PRIVATE_LABEL not in governed_text
    assert authority["evidence_sources"]["operator_prompt"] not in governed_text
    assert "evidence_sources" not in _canonical_text(transaction.prewrite_package.proposal)
    assert "semantic_source_meaning_graph" not in governed_text


def test_transaction_v2_rejects_reintroduced_top_level_review_duplicates(
    tmp_path: Path,
) -> None:
    authority = _authority_with_private_evidence()
    proposal = _proposal(tmp_path, authority)
    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )
    payload = product_create_transaction_to_dict(transaction)
    payload["proposal"] = copy.deepcopy(payload["prewrite_package"]["proposal"])

    with pytest.raises(ValueError, match="v2 payload is malformed"):
        product_create_transaction_from_dict(payload)


@pytest.mark.parametrize("target", ("authority", "binding"))
def test_transaction_verifier_rejects_private_authority_or_review_binding_tampering(
    tmp_path: Path, target: str
) -> None:
    authority = _authority_with_private_evidence()
    proposal = _proposal(tmp_path, authority)
    transaction = compile_verified_semantic_transaction(
        repo_root=tmp_path,
        proposal=proposal,
        intent_authority=authority,
        release_selector="0.0.1",
    )
    candidate: ProductCreateTransaction
    if target == "authority":
        changed_authority = copy.deepcopy(transaction.intent_authority)
        changed_authority["authority_snapshot_sha256"] = "0" * 64
        candidate = replace(transaction, intent_authority=changed_authority)
    else:
        changed_proposal = copy.deepcopy(transaction.prewrite_package.proposal)
        changed_proposal[PRODUCT_INTENT_REVIEW_BINDING_KEY][
            "authority_snapshot_sha256"
        ] = "0" * 64
        candidate = replace(
            transaction,
            prewrite_package=replace(
                transaction.prewrite_package,
                proposal=changed_proposal,
            ),
        )
    candidate = replace(
        candidate,
        transaction_hash=product_create_transaction_hash(candidate),
    )
    payload = product_create_transaction_to_dict(candidate)

    with pytest.raises(ValueError, match="(snapshot hash mismatch|review binding)"):
        product_create_transaction_from_dict(payload)


def _authority_with_private_evidence() -> dict[str, object]:
    authority = copy.deepcopy(
        semantic_intent_with_authority()[PRODUCT_INTENT_AUTHORITY_KEY]
    )
    sources = authority["evidence_sources"]
    sources["operator_prompt"] += f" Retired editorial alias: {_PRIVATE_LABEL}."
    evidence_hash = semantic_evidence_sha256(sources)
    authority["evidence_sha256"] = evidence_hash
    authority["accepted_evidence_sha256"] = evidence_hash
    authority["operating_envelope"]["complexity"]["dimensions"]["evidence_bytes"] = len(
        sources["operator_prompt"].encode("utf-8")
    )
    authority["authority_snapshot_sha256"] = product_intent_authority_snapshot_hash(
        authority
    )
    require_product_intent_authority_structure(authority)
    return authority


def _proposal(repo_root: Path, authority: dict[str, object]) -> dict[str, object]:
    return build_verified_semantic_proposal_for_repo(
        repo_root=repo_root,
        authority=authority,
        release_selector="0.0.1",
    )


def _canonical_text(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
