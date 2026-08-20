from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from greenfield_semantic_development_cohort import (
    compile_development_candidate_bundle,
)
from greenfield_semantic_release_support import (
    canonical_sha256,
    greenfield_runtime_source_fingerprint,
)
from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan
from greenfield_semantic_pipeline_receipts import PIPELINE_VERSION
from greenfield_semantic_release_evidence import CANDIDATE_BUNDLE_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    ACTIVE_SEMANTIC_MECHANISM_ID,
    semantic_execution_evidence,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture,
    verified_transaction_receipt_fixture,
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
    packet["critic_run"] = {
        **packet["critic_run"],
        "critic_run_id": "claim-desk:critic",
    }
    packet["author_run"] = {
        **packet["author_run"],
        "author_run_id": "claim-desk:author",
    }
    receipt = _receipt(
        packet=packet,
        assignment=plan["cases"][0],
        outcome=outcome,
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


def _receipt(*, packet: dict, assignment: dict, outcome: str) -> dict:
    wall_ms = 50_000
    transaction = (
        verified_transaction_receipt_fixture(packet, prompt=SEMANTIC_PROMPT)
        if outcome == "commit"
        else None
    )
    return {
        "version": PIPELINE_VERSION,
        "case_id": "claim-desk",
        "status": "completed",
        "outcome": outcome,
        "wall_ms": wall_ms,
        "budget": {"tier": "standard"},
        "materiality_critic": _critic_run(packet),
        "source_hypothesis": {
            "stage": "source_hypothesis",
            "case_id": "claim-desk",
            "host_profile": "codex",
            "model": "gpt-5.5",
            "reasoning_effort": "low",
            "model_call_count": 2,
            "validation_status": "passed",
            "authority_used": False,
            "source": {},
            "selected_run_index": 1,
            "hypothesis_runs": [
                {
                    "run_index": 0,
                    "hypothesis_mode": "full_graph",
                    "status": "comparison_passed",
                    "wall_ms": 20_000,
                    "usage": {},
                },
                {
                    "run_index": 1,
                    "hypothesis_mode": "source_only",
                    "status": "selected",
                    "wall_ms": 19_000,
                    "usage": {},
                },
            ],
        },
        "final_graph_adjudication": {
            "stage": "partitioned_graph_admission",
            "case_id": "claim-desk",
            "host_profile": "codex",
            "model": "gpt-5.5",
            "reasoning_effort": "low",
            "model_call_count": 0,
            "validation_status": "passed",
            "source_status": "approved" if outcome == "commit" else "not_applicable",
            "compiled_author_output": (
                {"typed_graph": True} if outcome == "commit" else None
            ),
        },
        "materiality_assessment": deepcopy(packet["materiality_assessment"]),
        "packet": deepcopy(packet),
        "transaction": transaction,
        "failed_stage": "",
        "failure": "",
        "model_call_count": 3,
        "restart_count": 0,
        "total_tokens": 200,
        "mechanism_execution": semantic_execution_evidence(
            host_profile="codex",
            tier="standard",
            status="completed",
            outcome=outcome,
            wall_ms=wall_ms,
            model_call_count=3,
            restart_count=0,
            implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
        ),
        "evidence_assignment": deepcopy(assignment),
    }


def _critic_run(packet: dict) -> dict:
    return {
        "stage": "materiality_critic",
        "case_id": "claim-desk",
        "host_profile": "codex",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "low",
        "model_call_count": 1,
        "validation_status": "passed",
        "prompt_sha256": hashlib.sha256(
            SEMANTIC_PROMPT.encode("utf-8")
        ).hexdigest(),
        "decision": _materiality_decision(packet),
    }


def _materiality_decision(packet: dict) -> dict:
    assessment = packet["materiality_assessment"]
    fields = {
        row["field"]: {
            key: deepcopy(value) for key, value in row.items() if key != "field"
        }
        for row in assessment["fields"]
    }
    if assessment["decision"] == "clarification_required":
        clarification = assessment["clarification"]
        fields[clarification["field"]] = {
            "status": "explicit",
            "source_refs": deepcopy(clarification["source_refs"]),
            "alternatives": [],
        }
    return {
        "version": "odylith.greenfield.parallel-materiality-decision.v3",
        "outcome": {
            "decision": assessment["decision"],
            "clarification": deepcopy(assessment["clarification"]),
        },
        "fields": fields,
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
