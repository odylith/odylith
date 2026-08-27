from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from greenfield_semantic_development_cohort import (
    compile_development_candidate_bundle,
)
from greenfield_semantic_release_support import (
    canonical_sha256,
)
from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan
from greenfield_semantic_release_evidence import CANDIDATE_BUNDLE_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import ACTIVE_SEMANTIC_MECHANISM_ID
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture,
    pipeline_receipt_fixture,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_clarification_packet,
    semantic_intent_packet,
)


REVISION = "a" * 40


@pytest.mark.parametrize("outcome", ["commit", "clarify"])
def test_development_cohort_compiles_active_pipeline_receipts(
    tmp_path: Path, outcome: str
) -> None:
    context = _context(tmp_path, outcome=outcome)

    bundle = _compile(context, output=tmp_path / "candidates.json")

    assert set(bundle) == {
        "version",
        "corpus_sha256",
        "implementation_revision",
        "authoring_contract_sha256",
        "active_evidence_plan_sha256",
        "deterministic_law_report_sha256",
        "cohort_nonce",
        "cases",
    }
    assert bundle["version"] == CANDIDATE_BUNDLE_VERSION
    assert bundle["authoring_contract_sha256"] == (
        semantic_intent_authoring_contract_sha256()
    )
    row = bundle["cases"][0]
    assert row["outcome"] == outcome
    assert row["mechanism_evidence"] == context["receipt"]
    assert row["mechanism_evidence"]["mechanism_execution"]["mechanism_id"] == (
        ACTIVE_SEMANTIC_MECHANISM_ID
    )
    if outcome == "commit":
        assert canonical_sha256(row["review_package"]) == row["transaction_proof"][
            "package_sha256"
        ]
        assert row["transaction_proof"]["transaction_sha256"] == context["receipt"][
            "transaction"
        ]["transaction_hash"]
    else:
        assert row["review_package"] is None
        assert row["transaction_proof"]["status"] == "not_applicable"


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (
            lambda context: context["receipt"]["mechanism_execution"].__setitem__(
                "mechanism_id", "retired-two-stage"
            ),
            "active pipeline evidence is invalid",
        ),
        (
            lambda context: context["receipt"]["evidence_assignment"].__setitem__(
                "case_nonce", "changed"
            ),
            "changes its frozen assignment",
        ),
        (
            lambda context: context["receipt"]["transaction"].__setitem__(
                "review_package", {"case_id": "other"}
            ),
            "review package",
        ),
    ],
)
def test_development_cohort_rejects_mechanism_assignment_and_package_drift(
    tmp_path: Path, mutation: object, message: str
) -> None:
    context = _context(tmp_path, outcome="commit")
    mutation(context)  # type: ignore[operator]
    context["receipt_path"] = _write(
        tmp_path / "drifted-receipt.json", context["receipt"]
    )

    with pytest.raises(RuntimeError, match=message):
        _compile(context, output=tmp_path / "rejected.json")


def test_development_cohort_requires_exact_case_coverage(tmp_path: Path) -> None:
    context = _context(tmp_path, outcome="commit")

    with pytest.raises(RuntimeError, match="cover every case exactly once"):
        compile_development_candidate_bundle(
            corpus_path=context["corpus_path"],
            active_evidence_plan_path=context["plan_path"],
            receipt_paths=[],
            deterministic_law_evidence_path=context["laws_path"],
            implementation_revision=REVISION,
            output_path=tmp_path / "missing.json",
        )


def test_development_cohort_has_no_prose_matcher_or_retired_mechanism() -> None:
    source = Path("scripts/release/greenfield_semantic_development_cohort.py")
    tree = ast.parse(source.read_text(encoding="utf-8"))
    imported = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    text = source.read_text(encoding="utf-8").casefold()

    assert imported.isdisjoint(
        {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    )
    assert "two-stage" not in text
    assert "development-author-segment" not in text
    assert "similarity" not in text


def _context(tmp_path: Path, *, outcome: str) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    corpus = {"cases": [{"case_id": "claim-desk", "prompt": SEMANTIC_PROMPT}]}
    corpus_path = _write(tmp_path / "corpus.json", corpus)
    plan_path = tmp_path / "active-plan.json"
    plan = prepare_active_evidence_plan(
        corpus_path=corpus_path,
        host_profiles=["codex"],
        output_path=plan_path,
    )
    packet = (
        semantic_intent_packet()
        if outcome == "commit"
        else semantic_clarification_packet()
    )
    receipt = pipeline_receipt_fixture(
        packet,
        prompt=SEMANTIC_PROMPT,
        case_id="claim-desk",
        assignment=plan["cases"][0],
    )
    receipt_path = _write(tmp_path / "receipt.json", receipt)
    laws_path = _write(
        tmp_path / "deterministic-laws.json",
        deterministic_law_report_fixture(REVISION),
    )
    return {
        "corpus_path": corpus_path,
        "plan_path": plan_path,
        "receipt": receipt,
        "receipt_path": receipt_path,
        "laws_path": laws_path,
    }


def _compile(context: dict, *, output: Path) -> dict:
    return compile_development_candidate_bundle(
        corpus_path=context["corpus_path"],
        active_evidence_plan_path=context["plan_path"],
        receipt_paths=[context["receipt_path"]],
        deterministic_law_evidence_path=context["laws_path"],
        implementation_revision=REVISION,
        output_path=output,
    )


def _write(path: Path, value: object) -> Path:
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path
