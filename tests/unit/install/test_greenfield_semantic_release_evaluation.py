from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan
from greenfield_semantic_release_evaluation import (
    ADJUDICATION_VERSION,
    CANDIDATE_BUNDLE_VERSION,
    EVALUATION_CONTRACT_VERSION,
    REPORT_VERSION,
    REVIEW_VERSION,
    _corpus_indexes,
    _floor_checks,
    _rate,
    evaluate_semantic_release,
    wilson_interval,
)
from greenfield_semantic_release_support import canonical_sha256
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture,
    pipeline_receipt_fixture,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_clarification_packet,
    semantic_intent_packet,
)


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
ANNOTATION_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "policy_boundaries",
    "dependencies",
    "assumptions",
    "ambiguities",
    "material_questions",
)


def test_release_evaluation_requires_independent_exact_id_custody(
    tmp_path: Path,
) -> None:
    report = _evaluate(_evidence(tmp_path))

    assert report["version"] == REPORT_VERSION
    assert report["passed"] is True
    assert report["reviewer_count"] == 2
    assert report["metrics"]["accepted_fact_custody"] == 1.0
    assert report["metrics"]["fact_precision"] == 1.0
    assert report["metrics"]["material_question_recall"] == 1.0
    assert report["metrics"]["equivalent_source_convergence"] == 1.0
    assert report["metrics"]["worst_slice"]["point_estimate"] == 1.0
    assert report["resource_metrics"]["cohort_totals"]["model_calls"] == 3
    assert set(report["auxiliary_report_bindings"]) == {
        "host_parity",
        "lower_capability_safety",
    }


def test_release_evaluation_fails_an_adjudicated_unsupported_addition(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    fact_id = evidence["candidates"]["cases"][0]["semantic_artifact"][
        "semantic_intent"
    ]["facts"][0]["fact_id"]
    for review in evidence["reviews"]:
        review["cases"][0]["unsupported_fact_ids"] = [fact_id]
    evidence["adjudication"]["cases"][0]["unsupported_fact_ids"] = [fact_id]
    evidence["adjudication"]["review_sha256s"] = sorted(
        canonical_sha256(review) for review in evidence["reviews"]
    )

    report = _evaluate(evidence)

    assert report["passed"] is False
    assert report["metrics"]["fact_precision"] < 1.0
    assert report["metrics"]["failed_case_count"] == 1


@pytest.mark.parametrize("mutation", ["mechanism", "host", "calls", "packet", "assignment"])
def test_release_evaluation_rejects_unbound_mechanism_claims(
    tmp_path: Path, mutation: str
) -> None:
    evidence = _evidence(tmp_path)
    mechanism = evidence["candidates"]["cases"][0]["mechanism_evidence"]
    if mutation == "mechanism":
        mechanism["mechanism_execution"]["mechanism_id"] = "retired-two-stage"
    elif mutation == "host":
        mechanism["source_meaning_author"]["author_run"]["host_profile"] = "claude"
    elif mutation == "calls":
        mechanism["source_meaning_author"]["model_call_count"] = 2
    elif mutation == "packet":
        mechanism["packet"] = {
            **mechanism["packet"],
            "evidence_sha256": "0" * 64,
        }
    else:
        mechanism["evidence_assignment"]["case_nonce"] = "changed"

    with pytest.raises(ValueError, match="execution evidence is invalid"):
        _evaluate(evidence)


def test_release_evaluation_rejects_missing_resource_telemetry(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    del evidence["candidates"]["cases"][0]["mechanism_evidence"]["total_tokens"]

    with pytest.raises(ValueError, match="fields do not match"):
        _evaluate(evidence)


def test_release_evaluation_rejects_changed_review_package(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    evidence["candidates"]["cases"][0]["review_package"] = None
    with pytest.raises(ValueError, match="review package"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "clarification")
    clarify = next(
        row for row in evidence["candidates"]["cases"] if row["outcome"] == "clarify"
    )
    clarify["review_package"] = {"unexpected": "package"}
    with pytest.raises(ValueError, match="clarification carries a review package"):
        _evaluate(evidence)


def test_release_evaluation_rejects_stale_contract_and_candidate_bundle(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    evidence["candidates"]["version"] = "odylith.greenfield.semantic-release-candidates.v6"
    with pytest.raises(ValueError, match="unsupported version"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "v12-contract")
    evidence["contract"] = {
        **_fixture_contract("release"),
        "version": "odylith.greenfield.semantic-release-evaluation-contract.v12",
    }
    with pytest.raises(ValueError, match="unsupported version"):
        _evaluate(evidence)


def test_release_evaluation_enforces_resource_ceilings(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    evidence["candidates"]["cases"][0]["mechanism_evidence"]["total_tokens"] = 100_001
    _rebind_review_evidence(evidence)

    report = _evaluate(evidence)

    assert report["passed"] is False
    assert any(
        row["ceiling"] == "maximum_case_total_tokens" and row["passed"] is False
        for row in report["resource_ceiling_checks"]
    )


def test_release_evaluation_requires_passed_auxiliary_gates(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    evidence["auxiliary_reports"]["host_parity"]["passed"] = False
    evidence["auxiliary_reports"]["host_parity"]["status"] = "failed"

    with pytest.raises(ValueError, match="host_parity did not pass"):
        _evaluate(evidence)


def test_release_evaluation_rejects_self_adjudication(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    evidence["adjudication"]["adjudicator_id"] = evidence["reviews"][0]["reviewer_id"]
    with pytest.raises(ValueError, match="distinct from reviewers"):
        _evaluate(evidence)


def test_required_zero_denominator_is_unproven_and_fails() -> None:
    metrics = {
        "p0_findings": 0,
        "p1_findings": 0,
        "fact_precision": 1.0,
        "accepted_fact_custody": 1.0,
        "policy_boundary_recall": 1.0,
        "explicit_system_recall": 1.0,
        "material_question_recall": _rate(0, 0),
        "unnecessary_question_rate": 0.0,
        "first_path_comprehension": 1.0,
        "package_utility": 1.0,
        "equivalent_source_convergence": 1.0,
        "overall_success": 1.0,
        "worst_slice": {"point_estimate": 1.0},
        "deterministic_law_failures": 0,
    }

    checks = _floor_checks(metrics, _fixture_contract("release")["floors"])

    question_check = next(
        row for row in checks if row["floor"] == "minimum_material_question_recall"
    )
    assert metrics["material_question_recall"] is None
    assert question_check["evidence_status"] == "unproven"
    assert question_check["passed"] is False


def test_release_evaluator_has_no_prose_matching_or_nlp_dependency() -> None:
    sources = [
        SCRIPTS_ROOT / "greenfield_semantic_release_evaluation.py",
        SCRIPTS_ROOT / "greenfield_semantic_release_evidence.py",
    ]
    imported = {
        alias.name.split(".")[0]
        for source in sources
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8")))
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    assert imported.isdisjoint(
        {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    )
    assert wilson_interval(2, 2)["lower"] < 1.0


def test_v18_contract_preserves_v17_and_pins_the_active_mechanism() -> None:
    development = _fixture_contract("development")
    release = _fixture_contract("release")
    prior = {
        **release,
        "version": "odylith.greenfield.semantic-release-evaluation-contract.v17",
        "mechanism_id": (
            "parallel_holistic_canonical_actor_node_effect_source_meaning_profiled_failover"
        ),
    }

    assert development["version"] == release["version"] == EVALUATION_CONTRACT_VERSION
    assert development["floors"] == release["floors"] == prior["floors"]
    assert development["required_model_profiles"] == [
        SEMANTIC_REASONING_CAPABILITY_PROFILE
    ]
    assert development["required_host_profiles"] == ["codex"]
    assert release["required_host_profiles"] == ["codex", "claude"]
    assert release["mechanism_id"] == (
        "holistic_tagged_entity_effect_source_meaning"
    )
    assert prior["mechanism_id"] == (
        "parallel_holistic_canonical_actor_node_effect_source_meaning_profiled_failover"
    )
    assert prior["mechanism_id"] != release["mechanism_id"]
    assert prior["version"] != release["version"]


def test_annotation_spans_are_exact_utf8_byte_custody() -> None:
    prompt = "Build a café résumé board."
    quote = "café résumé"
    start = prompt.encode("utf-8").index(quote.encode("utf-8"))
    corpus = {
        "cases": [{"case_id": "unicode-1", "prompt": prompt}],
        "annotations": [
            {
                "case_id": "unicode-1",
                "prompt_sha256": _prompt_sha(prompt),
                **{category: [] for category in ANNOTATION_CATEGORIES},
                "outputs": [
                    {
                        "id": "output-1",
                        "category": "outputs",
                        "value": quote,
                        "materiality": "material",
                        "expected_custody": "accepted_fact",
                        "source_start": start,
                        "source_end": start + len(quote.encode("utf-8")),
                        "source_quote": quote,
                    }
                ],
            }
        ],
    }

    _, annotations, _ = _corpus_indexes(corpus)

    assert annotations["unicode-1"]["output-1"]["source_quote"] == quote


def _evidence(tmp_path: Path) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    cases = [
        {
            "case_id": "dev-001",
            "prompt": SEMANTIC_PROMPT,
            "input_style": "direct_request",
            "tags": ["simple"],
            "metamorphic_group": "claim-desk-equivalent",
        },
        {
            "case_id": "dev-002",
            "prompt": SEMANTIC_PROMPT,
            "input_style": "reordered_evidence",
            "tags": ["simple"],
            "metamorphic_group": "claim-desk-equivalent",
        },
        {
            "case_id": "dev-003",
            "prompt": SEMANTIC_PROMPT,
            "input_style": "material_ambiguity",
            "tags": ["clarification"],
            "metamorphic_group": "",
        },
    ]
    annotations = [
        _commit_annotation("dev-001"),
        _commit_annotation("dev-002"),
        _clarify_annotation("dev-003"),
    ]
    corpus = {"version": "development-corpus.v1", "cases": cases, "annotations": annotations}
    corpus_path = tmp_path / "corpus.json"
    corpus_path.write_text(json.dumps(corpus, sort_keys=True) + "\n", encoding="utf-8")
    contract = _fixture_contract("release")
    plan = prepare_active_evidence_plan(
        corpus_path=corpus_path,
        host_profiles=contract["required_host_profiles"],
        output_path=tmp_path / "plan.json",
    )
    revision = "c" * 40
    law_report = deterministic_law_report_fixture(revision)
    law_sha = canonical_sha256(law_report)
    packets = [semantic_intent_packet(), semantic_intent_packet(), semantic_clarification_packet()]
    candidate_rows = [
        _candidate(
            case=case,
            packet=packets[index],
            assignment=plan["cases"][index],
            law_sha=law_sha,
        )
        for index, case in enumerate(cases)
    ]
    candidates = {
        "version": CANDIDATE_BUNDLE_VERSION,
        "corpus_sha256": plan["corpus_sha256"],
        "implementation_revision": revision,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "active_evidence_plan_sha256": canonical_sha256(plan),
        "deterministic_law_report_sha256": law_sha,
        "cohort_nonce": plan["cohort_nonce"],
        "cases": candidate_rows,
    }
    bundle_hash = canonical_sha256(candidates)
    decisions = [
        _decision(case["case_id"], candidate_rows[index], annotations[index])
        for index, case in enumerate(cases)
    ]
    reviews = [
        {
            "version": REVIEW_VERSION,
            "reviewer_id": reviewer,
            "independent": True,
            "candidate_bundle_sha256": bundle_hash,
            "cases": deepcopy(decisions),
        }
        for reviewer in ("reviewer-a", "reviewer-b")
    ]
    adjudication = {
        "version": ADJUDICATION_VERSION,
        "adjudicator_id": "adjudicator-c",
        "independent": True,
        "candidate_bundle_sha256": bundle_hash,
        "review_sha256s": sorted(canonical_sha256(review) for review in reviews),
        "cases": deepcopy(decisions),
        "resolved_disagreements": [],
    }
    return {
        "corpus": corpus,
        "corpus_sha256": plan["corpus_sha256"],
        "contract": contract,
        "active_evidence_plan": plan,
        "deterministic_law_report": law_report,
        "candidates": candidates,
        "reviews": reviews,
        "adjudication": adjudication,
        "auxiliary_reports": {
            "host_parity": {
                "version": "odylith.greenfield.host-parity-report.v1",
                "status": "passed",
                "passed": True,
                "proof_sha256": "a" * 64,
            },
            "lower_capability_safety": {
                "version": "odylith.greenfield.lower-capability-safety-evaluation.v1",
                "status": "passed",
                "report_sha256": "b" * 64,
            },
        },
    }


def _candidate(*, case: dict, packet: dict, assignment: dict, law_sha: str) -> dict:
    receipt = pipeline_receipt_fixture(
        packet,
        prompt=case["prompt"],
        case_id=case["case_id"],
        assignment=assignment,
        host_profile=assignment["host_profile"],
    )
    artifact = deepcopy(receipt["packet"])
    outcome = receipt["outcome"]
    transaction = receipt["transaction"]
    review_package = None if transaction is None else transaction["review_package"]
    return {
        "case_id": case["case_id"],
        "prompt_sha256": _prompt_sha(case["prompt"]),
        "outcome": outcome,
        "semantic_artifact": artifact,
        "mechanism_evidence": receipt,
        "review_package": review_package,
        "transaction_proof": {
            "status": "not_applicable" if outcome == "clarify" else "passed",
            "transaction_sha256": "" if transaction is None else transaction["transaction_hash"],
            "package_sha256": "" if review_package is None else canonical_sha256(review_package),
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_sha,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": outcome == "commit",
            "rollback_recovery_passed": outcome == "commit",
        },
    }


def _commit_annotation(case_id: str) -> dict:
    rows = {
        "actors": ("actor-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "actions": ("action-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "states": ("state-1", "The card moves from ready to claimed."),
        "outputs": ("output-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "policy_boundaries": ("policy-1", "Never reassign a card automatically."),
        "dependencies": ("dependency-1", "Read the local duty roster."),
    }
    annotation = _annotation_shell(case_id, expected_outcome="commit")
    annotation["explicit_systems"] = [{"value": "local duty roster"}]
    for category in ANNOTATION_CATEGORIES:
        annotation[category] = (
            [_annotation_row(*rows[category], category=category)] if category in rows else []
        )
    return annotation


def _clarify_annotation(case_id: str) -> dict:
    annotation = _annotation_shell(case_id, expected_outcome="clarify")
    annotation["explicit_systems"] = []
    for category in ANNOTATION_CATEGORIES:
        annotation[category] = []
    row = _annotation_row(
        "question-1",
        "A shift coordinator claims one ready card and receives a claim receipt.",
        category="material_questions",
    )
    row["expected_custody"] = "question"
    annotation["material_questions"] = [row]
    return annotation


def _annotation_shell(case_id: str, *, expected_outcome: str) -> dict:
    return {
        "case_id": case_id,
        "prompt_sha256": _prompt_sha(SEMANTIC_PROMPT),
        "expected_outcome": expected_outcome,
        "complexity": {
            "actors": 1,
            "state_objects": 1,
            "paths": 1,
            "external_systems": 0,
            "contradictions": 0,
            "ambiguities": int(expected_outcome == "clarify"),
            "safety_boundaries": 1,
        },
    }


def _annotation_row(item_id: str, quote: str, *, category: str) -> dict:
    start = SEMANTIC_PROMPT.encode("utf-8").index(quote.encode("utf-8"))
    return {
        "id": item_id,
        "category": category,
        "value": quote,
        "materiality": "material",
        "expected_custody": "accepted_fact",
        "source_start": start,
        "source_end": start + len(quote.encode("utf-8")),
        "source_quote": quote,
    }


def _decision(case_id: str, candidate: dict, annotation: dict) -> dict:
    matched = [
        row["id"]
        for category in ANNOTATION_CATEGORIES
        for row in annotation[category]
    ]
    clarify = annotation["expected_outcome"] == "clarify"
    return {
        "case_id": case_id,
        "candidate_sha256": canonical_sha256(candidate),
        "outcome_correct": True,
        "matched_annotation_ids": matched,
        "unsupported_fact_ids": [],
        "unsupported_relation_ids": [],
        "matched_explicit_system_indexes": [] if clarify else [0],
        "first_path_comprehensible": True,
        "package_concise": True,
        "package_reviewable": True,
        "surfaces_differentiated": True,
        "question_necessary": clarify,
        "equivalent_source_consistent": True,
        "p0_findings": [],
        "p1_findings": [],
    }


def _evaluate(evidence: dict) -> dict:
    return evaluate_semantic_release(**evidence)


def _rebind_review_evidence(evidence: dict) -> None:
    bundle_sha = canonical_sha256(evidence["candidates"])
    candidate_shas = {
        row["case_id"]: canonical_sha256(row) for row in evidence["candidates"]["cases"]
    }
    for review in evidence["reviews"]:
        review["candidate_bundle_sha256"] = bundle_sha
        for decision in review["cases"]:
            decision["candidate_sha256"] = candidate_shas[decision["case_id"]]
    adjudication = evidence["adjudication"]
    adjudication["candidate_bundle_sha256"] = bundle_sha
    for decision in adjudication["cases"]:
        decision["candidate_sha256"] = candidate_shas[decision["case_id"]]
    adjudication["review_sha256s"] = sorted(
        canonical_sha256(review) for review in evidence["reviews"]
    )


def _fixture_contract(lane: str) -> dict:
    return json.loads(
        (
            SCRIPTS_ROOT
            / "fixtures"
            / f"greenfield-semantic-{lane}-evaluation-contract.v18.json"
        ).read_text(encoding="utf-8")
    )


def _prompt_sha(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
