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

from greenfield_semantic_release_support import (
    canonical_sha256,
    greenfield_runtime_source_fingerprint,
)
from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan
from greenfield_semantic_pipeline_receipts import PIPELINE_VERSION
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
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    semantic_execution_evidence,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    standard_host_stage_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    SEMANTIC_PROMPT,
    semantic_clarification_packet,
    semantic_intent_packet,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture as _law_report,
    verified_transaction_receipt_fixture,
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
    assert report["resource_metrics"]["cohort_totals"]["model_calls"] == 9
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
    ["mechanism", "host", "calls", "packet", "assignment"],
)
def test_release_evaluation_rejects_unbound_mechanism_claims(
    tmp_path: Path,
    mutation: str,
) -> None:
    evidence = _evidence(tmp_path)
    mechanism = evidence["candidates"]["cases"][0]["mechanism_evidence"]
    if mutation == "mechanism":
        mechanism["mechanism_execution"]["mechanism_id"] = "retired-two-stage"
    elif mutation == "host":
        mechanism["final_graph_adjudication"]["host_profile"] = "other-host"
    elif mutation == "calls":
        mechanism["source_hypothesis"]["model_call_count"] = 1
    elif mutation == "packet":
        mechanism["packet"] = {**mechanism["packet"], "evidence_sha256": "0" * 64}
    else:
        mechanism["evidence_assignment"]["case_nonce"] = "changed"

    with pytest.raises(ValueError, match="execution evidence is invalid"):
        _evaluate(evidence)


def test_release_evaluation_rejects_missing_resource_telemetry(tmp_path: Path) -> None:
    evidence = _evidence(tmp_path)
    del evidence["candidates"]["cases"][0]["mechanism_evidence"]["total_tokens"]

    with pytest.raises(ValueError, match="fields do not match"):
        _evaluate(evidence)


def test_release_evaluation_rejects_missing_or_changed_review_package(
    tmp_path: Path,
) -> None:
    evidence = _evidence(tmp_path)
    evidence["candidates"]["cases"][0]["review_package"] = None
    with pytest.raises(ValueError, match="review package"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "changed")
    evidence["candidates"]["cases"][0]["review_package"]["case_id"] = "other-case"
    with pytest.raises(ValueError, match="does not match its transaction proof"):
        _evaluate(evidence)

    evidence = _evidence(tmp_path / "clarification")
    clarify = next(row for row in evidence["candidates"]["cases"] if row["outcome"] == "clarify")
    clarify["review_package"] = {"unexpected": "package"}
    with pytest.raises(ValueError, match="clarification carries a review package"):
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
    mechanism["total_tokens"] = 100_001
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


def test_v4_contract_preserves_v1_bytes_and_release_floors() -> None:
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
    prompt = SEMANTIC_PROMPT
    packet = semantic_intent_packet()
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
    plan = prepare_active_evidence_plan(
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
            packet=(deepcopy(packet) if index < 2 else semantic_clarification_packet()),
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
    *, case: dict, packet: dict, assignment: dict, law_sha: str,
) -> dict:
    case_id = case["case_id"]
    prompt = case["prompt"]
    packet["critic_run"] = {
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "critic_run_id": f"{case_id}:materiality-critic",
        "host_profile": assignment["host_profile"],
        "independent_context": True,
    }
    packet["author_run"] = {
        "capability_profile": SEMANTIC_REASONING_CAPABILITY_PROFILE,
        "author_run_id": f"{case_id}:terminal-author",
    }
    semantic_intent = packet["semantic_intent"]
    outcome = "clarify" if semantic_intent["status"] == "clarification_required" else "commit"
    wall_ms = 50_000
    host_profile = assignment["host_profile"]
    host_contract = standard_host_stage_profile(host_profile)
    transaction = (
        None
        if outcome == "clarify"
        else verified_transaction_receipt_fixture(packet, prompt=prompt)
    )
    transaction_sha = "" if transaction is None else transaction["transaction_hash"]
    execution = semantic_execution_evidence(
        host_profile=host_profile,
        tier="standard",
        status="completed",
        outcome=outcome,
        wall_ms=wall_ms,
        model_call_count=3,
        restart_count=0,
        implementation_fingerprint_sha256=greenfield_runtime_source_fingerprint(),
    )
    review_package = None if transaction is None else transaction["review_package"]
    return {
        "case_id": case_id,
        "prompt_sha256": _prompt_sha(prompt),
        "outcome": outcome,
        "semantic_artifact": packet,
        "mechanism_evidence": {
            "version": PIPELINE_VERSION,
            "case_id": case_id,
            "status": "completed",
            "outcome": outcome,
            "wall_ms": wall_ms,
            "budget": {"tier": "standard"},
            "materiality_critic": _critic_receipt(
                case_id=case_id,
                prompt=prompt,
                packet=packet,
                host_profile=host_profile,
                host_contract=host_contract,
            ),
            "source_hypothesis": {
                "stage": "source_hypothesis",
                "case_id": case_id,
                "host_profile": host_profile,
                "model": host_contract["source_hypothesis_model"],
                "reasoning_effort": host_contract["source_hypothesis_reasoning_effort"],
                "model_call_count": 2,
                "validation_status": "passed",
                "authority_used": False,
                "source": _empty_source_graph(),
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
                "case_id": case_id,
                "host_profile": host_profile,
                "model": host_contract["source_hypothesis_model"],
                "reasoning_effort": host_contract["source_hypothesis_reasoning_effort"],
                "model_call_count": 0,
                "validation_status": "passed",
                "source_status": "approved" if outcome == "commit" else "not_applicable",
                "compiled_author_output": (
                    {"typed_graph": True} if outcome == "commit" else None
                ),
            },
            "materiality_assessment": deepcopy(packet["materiality_assessment"]),
            "packet": deepcopy(packet),
            "transaction": deepcopy(transaction),
            "failed_stage": "",
            "failure": "",
            "model_call_count": 3,
            "restart_count": 0,
            "total_tokens": 200,
            "mechanism_execution": execution,
            "evidence_assignment": deepcopy(assignment),
        },
        "review_package": review_package,
        "transaction_proof": {
            "status": "not_applicable" if outcome == "clarify" else "passed",
            "transaction_sha256": transaction_sha,
            "package_sha256": (
                "" if review_package is None else canonical_sha256(review_package)
            ),
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_sha,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": outcome == "commit",
            "rollback_recovery_passed": outcome == "commit",
        },
    }


def _critic_receipt(
    *, case_id: str, prompt: str, packet: dict,
    host_profile: str, host_contract: dict,
) -> dict:
    decision = _parallel_materiality_decision(packet)
    return {
        "stage": "materiality_critic",
        "case_id": case_id,
        "host_profile": host_profile,
        "model": host_contract["critic_model"],
        "reasoning_effort": host_contract["critic_reasoning_effort"],
        "model_call_count": 1,
        "validation_status": "passed",
        "prompt_sha256": _prompt_sha(prompt),
        "decision": decision,
    }


def _parallel_materiality_decision(packet: dict) -> dict:
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


def _empty_source_graph() -> dict:
    return {
        "version": "odylith.greenfield.semantic-source-partitioned-authoring-graph.v24",
        "path": {
            "identities": [], "actors": [], "workflow_steps": [],
            "state_objects": [], "visible_outputs": [], "relations": {},
        },
        "boundary": {
            "external_systems": [], "policies": [], "relations": {},
            "discarded_evidence": [], "assumptions": [],
        },
    }


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
            / f"greenfield-semantic-{lane}-evaluation-contract.v5.json"
        ).read_text(encoding="utf-8")
    )


def _write_json(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _prompt_sha(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
