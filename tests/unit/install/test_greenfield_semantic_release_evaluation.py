from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_semantic_development_evidence import MECHANISM_EVIDENCE_VERSION
from greenfield_semantic_development_evidence import MECHANISM_ID
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import development_mechanism_contract_sha256
from greenfield_semantic_development_evidence import materiality_critic_input_for_case
from greenfield_semantic_development_evidence import prepare_development_evidence_plan
from greenfield_semantic_development_evidence import run_evidence_sha256
from greenfield_semantic_development_evidence import semantic_graph_author_input_for_case
from greenfield_semantic_release_evaluation import ADJUDICATION_VERSION
from greenfield_semantic_release_evaluation import CANDIDATE_BUNDLE_VERSION
from greenfield_semantic_release_evaluation import EVALUATION_CONTRACT_VERSION
from greenfield_semantic_release_evaluation import REPORT_VERSION
from greenfield_semantic_release_evaluation import REVIEW_VERSION
from greenfield_semantic_release_evaluation import _corpus_indexes
from greenfield_semantic_release_evaluation import _floor_checks
from greenfield_semantic_release_evaluation import _rate
from greenfield_semantic_release_evaluation import evaluate_semantic_release
from greenfield_semantic_release_evaluation import wilson_interval
from greenfield_semantic_host_execution_contract import HOST_RUNTIME_RECEIPT_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    semantic_materiality_assessment_sha256,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_clarification_packet,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture as _law_report,
)


def test_release_evaluation_requires_independent_exact_id_custody(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)

    report = _evaluate(evidence)

    assert report["version"] == REPORT_VERSION
    assert report["passed"] is True
    assert report["reviewer_count"] == 2
    assert report["metrics"]["accepted_fact_custody"] == 1.0
    assert report["metrics"]["fact_precision"] == 1.0
    assert report["metrics"]["material_question_recall"] == 1.0
    assert report["metrics"]["equivalent_source_convergence"] == 1.0
    assert report["metrics"]["worst_slice"]["point_estimate"] == 1.0
    assert report["metrics"]["overall_confidence_interval_95"]["lower"] < 1.0
    assert report["resource_metrics"]["cohort_totals"]["model_calls"] == 6
    assert set(report["auxiliary_report_bindings"]) == {
        "host_parity",
        "lower_capability_safety",
    }


def test_release_evaluation_fails_an_adjudicated_unsupported_addition(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    fact_id = evidence["candidates"]["cases"][0]["semantic_artifact"]["semantic_intent"][
        "facts"
    ][0]["fact_id"]
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


@pytest.mark.parametrize(
    "mutation",
    ["host", "capability", "run_nonce", "input_hash", "self_challenge"],
)
def test_release_evaluation_rejects_unbound_mechanism_claims(
    tmp_path: Path,
    mutation: str,
) -> None:
    evidence = _evidence(tmp_path)
    mechanism = evidence["candidates"]["cases"][0]["mechanism_evidence"]
    if mutation == "host":
        mechanism["author"]["host_profile"] = "other-host"
    elif mutation == "capability":
        mechanism["author"]["capability_profile"] = "lower_capability"
    elif mutation == "run_nonce":
        mechanism["author"]["run_nonce"] = mechanism["critic"]["run_nonce"]
    elif mutation == "input_hash":
        mechanism["critic"]["input_sha256"] = "0" * 64
    else:
        mechanism["author"]["self_challenge"] = mechanism["author"][
            "self_challenge"
        ][:-1]

    with pytest.raises(ValueError, match="execution evidence is invalid"):
        _evaluate(evidence)


def test_release_evaluation_rejects_missing_resource_telemetry(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    del evidence["candidates"]["cases"][0]["mechanism_evidence"]["total_tokens"]

    with pytest.raises(ValueError, match="fields do not match"):
        _evaluate(evidence)


def test_release_evaluation_rejects_v1_contract_and_candidate_bundle(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    evidence["candidates"]["version"] = "odylith.greenfield.semantic-release-candidates.v1"
    with pytest.raises(ValueError, match="candidate bundle uses an unsupported version"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "v1-contract")
    evidence["contract"] = json.loads(
        (
            SCRIPTS_ROOT
            / "fixtures"
            / "greenfield-semantic-release-evaluation-contract.v1.json"
        ).read_text(encoding="utf-8")
    )
    with pytest.raises(ValueError, match="fields do not match|unsupported version"):
        _evaluate(evidence)


def test_release_evaluation_enforces_resource_ceilings(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    mechanism = evidence["candidates"]["cases"][0]["mechanism_evidence"]
    author = mechanism["author"]
    author["token_usage"] = {
        "input_tokens": 100_000,
        "output_tokens": 1,
        "total_tokens": 100_001,
        "measurement_basis": "provider_usage_receipt",
    }
    author["run_sha256"] = run_evidence_sha256(author)
    mechanism["total_tokens"] = (
        mechanism["critic"]["token_usage"]["total_tokens"]
        + author["token_usage"]["total_tokens"]
    )
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


def test_release_evaluation_rejects_unresolved_or_self_adjudicated_reviews(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    evidence["reviews"][1]["cases"][0]["first_path_comprehensible"] = False
    evidence["adjudication"]["review_sha256s"] = sorted(
        canonical_sha256(review) for review in evidence["reviews"]
    )
    with pytest.raises(ValueError, match="resolve every and only"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "self-adjudication")
    evidence["adjudication"]["adjudicator_id"] = evidence["reviews"][0]["reviewer_id"]
    with pytest.raises(ValueError, match="distinct from reviewers"):
        _evaluate(evidence)


def test_required_zero_denominator_is_unproven_and_fails() -> None:
    metrics = {
        "p0_findings": 0,
        "p1_findings": 0,
        "fact_precision": 1.0,
        "accepted_fact_custody": 1.0,
        "constraint_recall": 1.0,
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
    floors = _fixture_contract("release")["floors"]

    checks = _floor_checks(metrics, floors)

    assert metrics["material_question_recall"] is None
    question_check = next(
        row for row in checks if row["floor"] == "minimum_material_question_recall"
    )
    assert question_check["observed"] is None
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
    text = "\n".join(source.read_text(encoding="utf-8") for source in sources)
    assert "similarity" not in text.casefold()
    assert "token overlap" not in text.casefold()
    assert wilson_interval(2, 2)["lower"] < 1.0


def test_v2_contract_preserves_v1_bytes_and_release_floors() -> None:
    v1_development = SCRIPTS_ROOT / "fixtures" / (
        "greenfield-semantic-development-evaluation-contract.v1.json"
    )
    v1_release = SCRIPTS_ROOT / "fixtures" / (
        "greenfield-semantic-release-evaluation-contract.v1.json"
    )
    development = _fixture_contract("development")
    release = _fixture_contract("release")
    old_development = json.loads(v1_development.read_text(encoding="utf-8"))
    old_release = json.loads(v1_release.read_text(encoding="utf-8"))

    assert hashlib.sha256(v1_development.read_bytes()).hexdigest() == (
        "fd21d30d77c056805bb6fe483f43d3894e0279dc705e77eaa7990f5fbe69cfae"
    )
    assert hashlib.sha256(v1_release.read_bytes()).hexdigest() == (
        "e7c86a2280ac1bc2b841ea5a2ebbc904706a81a5757057d7c1bf22e77f02d0be"
    )
    assert development["version"] == release["version"] == EVALUATION_CONTRACT_VERSION
    assert development["floors"] == release["floors"] == old_release["floors"]
    assert old_development["floors"] == old_release["floors"]
    assert development["required_model_profiles"] == [SEMANTIC_REASONING_CAPABILITY_PROFILE]
    assert release["required_model_profiles"] == [SEMANTIC_REASONING_CAPABILITY_PROFILE]
    assert development["required_host_profiles"] == ["codex"]
    assert release["required_host_profiles"] == ["codex", "claude"]
    assert development["resource_ceilings"] == release["resource_ceilings"]


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
                **{category: [] for category in _ANNOTATION_CATEGORIES},
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


_ANNOTATION_CATEGORIES = (
    "actors",
    "actions",
    "states",
    "outputs",
    "constraints",
    "dependencies",
    "assumptions",
    "ambiguities",
    "non_goals",
    "material_questions",
)


def _evidence(tmp_path: Path) -> dict:
    tmp_path.mkdir(parents=True, exist_ok=True)
    fixture = json.loads(
        (SCRIPTS_ROOT / "fixtures" / "greenfield-semantic-smoke.v7.json").read_text(
            encoding="utf-8"
        )
    )
    prompt = fixture["prompt"]
    cases = [
        {
            "case_id": "dev-001",
            "prompt": prompt,
            "input_style": "direct_request",
            "tags": ["simple"],
            "metamorphic_group": "claim-desk-equivalent",
        },
        {
            "case_id": "dev-002",
            "prompt": prompt,
            "input_style": "reordered_evidence",
            "tags": ["simple"],
            "metamorphic_group": "claim-desk-equivalent",
        },
        {
            "case_id": "dev-003",
            "prompt": prompt,
            "input_style": "material_ambiguity",
            "tags": ["clarification"],
            "metamorphic_group": "",
        },
    ]
    annotations = [
        _commit_annotation("dev-001", prompt),
        _commit_annotation("dev-002", prompt),
        _clarify_annotation("dev-003", prompt),
    ]
    corpus = {
        "version": "development-corpus.v1",
        "cases": cases,
        "annotations": annotations,
    }
    corpus_path = _write_json(tmp_path / "corpus.json", corpus)
    contract = _fixture_contract("release")
    plan = prepare_development_evidence_plan(
        corpus_path=corpus_path,
        host_profiles=contract["required_host_profiles"],
        output_path=tmp_path / "plan.json",
    )
    revision = "c" * 40
    law_report = _law_report(revision)
    law_sha = canonical_sha256(law_report)
    candidate_rows = [
        _candidate(
            case=case,
            packet=(deepcopy(fixture["packet"]) if index < 2 else semantic_clarification_packet()),
            corpus=corpus,
            plan=plan,
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
        "development_evidence_plan_sha256": canonical_sha256(plan),
        "deterministic_law_report_sha256": law_sha,
        "cohort_nonce": plan["cohort_nonce"],
        "cases": candidate_rows,
    }
    bundle_hash = canonical_sha256(candidates)
    decision_rows = [
        _decision(case["case_id"], candidate_rows[index], annotations[index])
        for index, case in enumerate(cases)
    ]
    reviews = [
        {
            "version": REVIEW_VERSION,
            "reviewer_id": reviewer,
            "independent": True,
            "candidate_bundle_sha256": bundle_hash,
            "cases": deepcopy(decision_rows),
        }
        for reviewer in ("reviewer-a", "reviewer-b")
    ]
    adjudication = {
        "version": ADJUDICATION_VERSION,
        "adjudicator_id": "adjudicator-c",
        "independent": True,
        "candidate_bundle_sha256": bundle_hash,
        "review_sha256s": sorted(canonical_sha256(review) for review in reviews),
        "cases": deepcopy(decision_rows),
        "resolved_disagreements": [],
    }
    return {
        "corpus": corpus,
        "corpus_sha256": plan["corpus_sha256"],
        "contract": contract,
        "development_evidence_plan": plan,
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


def _candidate(
    *, case: dict, packet: dict, corpus: dict, plan: dict, assignment: dict, law_sha: str,
) -> dict:
    case_id = case["case_id"]
    prompt = case["prompt"]
    packet["critic_run"] = {
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "critic_run_id": assignment["critic_assignment"]["run_id"],
        "host_profile": assignment["critic_assignment"]["host_profile"],
        "independent_context": True,
    }
    packet["author_run"] = {
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "author_run_id": assignment["author_assignment"]["run_id"],
    }
    assessment = packet["materiality_assessment"]
    assessment["authoring_contract_sha256"] = semantic_intent_authoring_contract_sha256()
    packet["authoring_contract_sha256"] = semantic_intent_authoring_contract_sha256()
    packet["materiality_assessment_sha256"] = semantic_materiality_assessment_sha256(
        assessment
    )
    semantic_intent = packet["semantic_intent"]
    critic_input = materiality_critic_input_for_case(
        corpus=corpus, plan=plan, case_id=case_id,
    )
    author_input = semantic_graph_author_input_for_case(
        corpus=corpus,
        plan=plan,
        case_id=case_id,
        materiality_assessment=assessment,
    )
    critic = _run_receipt(
        assignment["critic_assignment"],
        input_sha=canonical_sha256(critic_input),
        output_sha=canonical_sha256(assessment),
        stage="critic",
    )
    author = _run_receipt(
        assignment["author_assignment"],
        input_sha=canonical_sha256(author_input),
        output_sha=canonical_sha256(
            {
                "semantic_intent": semantic_intent,
                "self_challenge": [
                    {"challenge": challenge, "status": "passed"}
                    for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
                ],
            }
        ),
        stage="author",
        materiality_sha=packet["materiality_assessment_sha256"],
    )
    compile_wall_ms = 1
    total_wall_ms = critic["wall_ms"] + author["wall_ms"] + compile_wall_ms
    total_tokens = (
        critic["token_usage"]["total_tokens"] + author["token_usage"]["total_tokens"]
    )
    outcome = "clarify" if semantic_intent["status"] == "clarification_required" else "commit"
    return {
        "case_id": case_id,
        "prompt_sha256": _prompt_sha(prompt),
        "outcome": outcome,
        "semantic_artifact": packet,
        "mechanism_evidence": {
            "version": MECHANISM_EVIDENCE_VERSION,
            "mechanism_id": MECHANISM_ID,
            "mechanism_contract_sha256": development_mechanism_contract_sha256(),
            "cohort_nonce": plan["cohort_nonce"],
            "cohort_assignment_sha256": plan["cohort_assignment_sha256"],
            "case_nonce": assignment["case_nonce"],
            "assignment_sha256": assignment["assignment_sha256"],
            "evidence_plan_sha256": canonical_sha256(plan),
            "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
            "critic": critic,
            "author": author,
            "compile_wall_ms": compile_wall_ms,
            "total_wall_ms": total_wall_ms,
            "model_call_count": 2,
            "restart_count": 0,
            "total_tokens": total_tokens,
        },
        "transaction_proof": {
            "status": "not_applicable" if outcome == "clarify" else "passed",
            "transaction_sha256": "" if outcome == "clarify" else "a" * 64,
            "package_sha256": "" if outcome == "clarify" else "b" * 64,
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_sha,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": outcome == "commit",
            "rollback_recovery_passed": outcome == "commit",
        },
    }


def _run_receipt(
    assignment: dict,
    *, input_sha: str, output_sha: str, stage: str, materiality_sha: str = "",
) -> dict:
    receipt = {
        "run_nonce": assignment["run_nonce"],
        "run_id": assignment["run_id"],
        "run_assignment_sha256": assignment["run_assignment_sha256"],
        "host_profile": assignment["host_profile"],
        "capability_profile": assignment["capability_profile"],
        "execution_profile": assignment["execution_profile"],
        "host_runtime": {
            "version": HOST_RUNTIME_RECEIPT_VERSION,
            "host_profile": assignment["host_profile"],
            "runtime_name": (
                "codex-cli" if assignment["host_profile"] == "codex" else "claude-code"
            ),
            "runtime_version": "test-runtime-v1",
            "runtime_binary_sha256": "e" * 64,
        },
        "independent_context": True,
        "attempt_count": 1,
        "validation_error_repair_count": 0,
        "input_sha256": input_sha,
        "output_sha256": output_sha,
        "access_receipt": {
            "prompt": True,
            "authoring_contract": True,
            "materiality_assessment": stage == "author",
            "annotations": False,
            "prior_candidates": False,
            "semantic_reviews": False,
            "validator_errors": False,
        },
        "wall_ms": 10,
        "token_usage": {
            "input_tokens": 40,
            "output_tokens": 20,
            "total_tokens": 60,
            "measurement_basis": "provider_usage_receipt",
        },
    }
    if stage == "author":
        receipt["materiality_assessment_sha256"] = materiality_sha
        receipt["self_challenge"] = [
            {"challenge": challenge, "status": "passed"}
            for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
        ]
    receipt["run_sha256"] = run_evidence_sha256(receipt)
    return receipt


def _commit_annotation(case_id: str, prompt: str) -> dict:
    rows = {
        "actors": ("actor-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "actions": ("action-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "states": ("state-1", "The card moves from ready to claimed."),
        "outputs": ("output-1", "A shift coordinator claims one ready card and receives a claim receipt."),
        "constraints": ("constraint-1", "Never reassign a card automatically."),
        "dependencies": ("dependency-1", "Read the local duty roster."),
    }
    annotation = _annotation_shell(case_id, prompt, expected_outcome="commit")
    annotation["explicit_systems"] = [{"value": "local duty roster"}]
    for category in _ANNOTATION_CATEGORIES:
        if category not in rows:
            annotation[category] = []
            continue
        item_id, quote = rows[category]
        annotation[category] = [_annotation_row(item_id, category, quote, prompt)]
    return annotation


def _clarify_annotation(case_id: str, prompt: str) -> dict:
    annotation = _annotation_shell(case_id, prompt, expected_outcome="clarify")
    annotation["expected_question_fields"] = ["visible_result"]
    annotation["explicit_systems"] = []
    for category in _ANNOTATION_CATEGORIES:
        annotation[category] = []
    quote = "A shift coordinator claims one ready card and receives a claim receipt."
    row = _annotation_row("question-1", "material_questions", quote, prompt)
    row["expected_custody"] = "question"
    annotation["material_questions"] = [row]
    return annotation


def _annotation_shell(case_id: str, prompt: str, *, expected_outcome: str) -> dict:
    return {
        "case_id": case_id,
        "prompt_sha256": _prompt_sha(prompt),
        "expected_outcome": expected_outcome,
        "expected_question_fields": [],
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


def _annotation_row(item_id: str, category: str, quote: str, prompt: str) -> dict:
    start = prompt.encode("utf-8").index(quote.encode("utf-8"))
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
        for category in _ANNOTATION_CATEGORIES
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
        "question_fields": ["visible_result"] if clarify else [],
        "equivalent_source_consistent": True,
        "p0_findings": [],
        "p1_findings": [],
    }


def _fixture_contract(lane: str) -> dict:
    return json.loads(
        (
            SCRIPTS_ROOT
            / "fixtures"
            / f"greenfield-semantic-{lane}-evaluation-contract.v2.json"
        ).read_text(encoding="utf-8")
    )


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _prompt_sha(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
