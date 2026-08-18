from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_semantic_development_cohort import EVIDENCE_REPOSITORY_NAME
from greenfield_semantic_development_cohort import compile_development_candidate_bundle
from greenfield_semantic_development_evidence import AUTHOR_SEGMENT_VERSION
from greenfield_semantic_development_evidence import MECHANISM_EVIDENCE_VERSION
from greenfield_semantic_development_evidence import MECHANISM_ID
from greenfield_semantic_development_evidence import build_materiality_critic_input
from greenfield_semantic_development_evidence import build_semantic_graph_author_input
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import expected_access_receipt
from greenfield_semantic_development_evidence import prepare_development_evidence_plan
from greenfield_semantic_development_evidence import require_development_evidence_plan
from greenfield_semantic_development_evidence import run_evidence_sha256
from greenfield_semantic_release_evidence import CANDIDATE_BUNDLE_VERSION
from greenfield_semantic_host_execution_contract import HOST_RUNTIME_RECEIPT_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_host_profiles import (
    host_execution_profile,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    SEMANTIC_INTENT_MANDATORY_CHALLENGES,
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    SEMANTIC_REASONING_CAPABILITY_PROFILE,
    semantic_materiality_assessment_sha256,
)
from tests.unit.runtime.greenfield_semantic_intent_fixtures import (
    semantic_clarification_packet,
    semantic_graph_extension_from_intent,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (
    deterministic_law_report_fixture as _law_report,
)


REVISION = "a" * 40


@pytest.mark.parametrize("outcome", ["commit", "clarify"])
def test_development_cohort_compiles_exact_two_stage_evidence(
    tmp_path: Path,
    outcome: str,
) -> None:
    context = _context(tmp_path, outcome=outcome)

    bundle = _compile(context, output=tmp_path / f"{outcome}-candidates.json")

    assert set(bundle) == {
        "version", "corpus_sha256", "implementation_revision",
        "authoring_contract_sha256", "development_evidence_plan_sha256",
        "deterministic_law_report_sha256", "cohort_nonce", "cases",
    }
    row = bundle["cases"][0]
    assert set(row) == {
        "case_id", "prompt_sha256", "outcome", "semantic_artifact",
        "mechanism_evidence", "review_package", "transaction_proof",
    }
    assert row["semantic_artifact"]["version"] == SEMANTIC_INTENT_PACKET_VERSION
    mechanism = row["mechanism_evidence"]
    assert set(mechanism) == {
        "version", "mechanism_id", "mechanism_contract_sha256", "cohort_nonce",
        "cohort_assignment_sha256", "case_nonce", "assignment_sha256",
        "evidence_plan_sha256", "authoring_contract_sha256", "critic", "author",
        "compile_wall_ms", "total_wall_ms", "model_call_count", "restart_count",
        "total_tokens",
    }
    assert mechanism["version"] == MECHANISM_EVIDENCE_VERSION
    assert mechanism["mechanism_id"] == MECHANISM_ID
    assert mechanism["model_call_count"] == 2
    assert mechanism["restart_count"] == 0
    assert mechanism["compile_wall_ms"] > 0
    assert mechanism["total_wall_ms"] == (
        mechanism["critic"]["wall_ms"]
        + mechanism["author"]["wall_ms"]
        + mechanism["compile_wall_ms"]
    )
    assert mechanism["total_tokens"] == (
        mechanism["critic"]["token_usage"]["total_tokens"]
        + mechanism["author"]["token_usage"]["total_tokens"]
    )
    assert row["outcome"] == outcome
    expected_proof = "passed" if outcome == "commit" else "not_applicable"
    assert row["transaction_proof"]["status"] == expected_proof
    if outcome == "commit":
        assert canonical_sha256(row["review_package"]) == row["transaction_proof"][
            "package_sha256"
        ]
        assert row["review_package"]["observed_source"]["repo_name"] == (
            EVIDENCE_REPOSITORY_NAME
        )
    else:
        assert row["review_package"] is None


def test_development_cohort_review_package_is_reproducible(tmp_path: Path) -> None:
    context = _context(tmp_path, outcome="commit")

    first = _compile(context, output=tmp_path / "first-candidates.json")["cases"][0]
    second = _compile(context, output=tmp_path / "second-candidates.json")["cases"][0]

    assert first["review_package"] == second["review_package"]
    assert first["transaction_proof"]["package_sha256"] == second["transaction_proof"][
        "package_sha256"
    ]


def test_phase_inputs_are_exact_and_annotation_blind(tmp_path: Path) -> None:
    context = _context(tmp_path, outcome="commit", include_annotations=True)
    critic_input = build_materiality_critic_input(
        corpus_path=context["corpus"],
        evidence_plan_path=context["plan_path"],
        case_id="claim-desk",
    )
    author_input = build_semantic_graph_author_input(
        corpus_path=context["corpus"],
        evidence_plan_path=context["plan_path"],
        case_id="claim-desk",
        materiality_assessment=context["assessment"],
    )

    common = {
        "version", "cohort_nonce", "case_id", "case_nonce", "assignment_sha256",
        "run_nonce", "run_id", "run_assignment_sha256", "host_profile",
        "capability_profile", "execution_profile", "independent_context", "attempt_limit", "evidence",
        "evidence_sha256", "authoring_contract", "authoring_contract_sha256",
    }
    assert set(critic_input) == common
    assert set(author_input) == common | {
        "materiality_assessment", "materiality_assessment_sha256", "citation_catalog",
    }
    assert author_input["citation_catalog"]
    assert all(
        row["ref_id"].startswith("source_ref_")
        for row in author_input["citation_catalog"]
    )
    assert critic_input["evidence"] == {
        "operator_prompt": context["prompt"],
        "operator_edit": "",
    }
    assert "annotations" not in critic_input
    assert "materiality_assessment" not in critic_input
    assert author_input["materiality_assessment"] == context["assessment"]
    assert critic_input["run_id"] != author_input["run_id"]
    assert critic_input["host_profile"] == author_input["host_profile"] == "codex"
    assert critic_input["execution_profile"] == author_input["execution_profile"] == {
        "version": "odylith.greenfield.host-execution-profile.v1",
        "host_profile": "codex",
        "provider": "openai",
        "model": "gpt-5.6-sol",
        "reasoning_effort": "high",
        "runner_family": "codex_exec",
        "structured_output_mode": "provider_json_schema",
        "tool_event_policy": "reject",
        "session_persistence": "disabled",
    }
    assert context["plan"]["host_execution_profiles"] == [
        host_execution_profile("codex")
    ]


def test_development_cohort_rejects_v1_and_caller_assembled_packet(tmp_path: Path) -> None:
    old = _context(tmp_path / "v1", outcome="commit")
    segment = deepcopy(old["segment"])
    segment["version"] = "odylith.greenfield.development-author-segment.v1"
    old["segment_path"] = _write(tmp_path / "v1-segment.json", segment)
    with pytest.raises(RuntimeError, match="unsupported version"):
        _compile(old, output=tmp_path / "v1-output.json")

    raw = _context(tmp_path / "raw", outcome="commit")
    segment = deepcopy(raw["segment"])
    segment["cases"][0]["semantic_artifact"] = _smoke_packet()
    raw["segment_path"] = _write(tmp_path / "raw-segment.json", segment)
    with pytest.raises(RuntimeError, match="fields do not match"):
        _compile(raw, output=tmp_path / "raw-output.json")


def test_development_plan_rejects_reused_runner_nonce(tmp_path: Path) -> None:
    context = _context(tmp_path, outcome="commit")
    plan = deepcopy(context["plan"])
    assignment = plan["cases"][0]
    assignment["author_assignment"]["run_nonce"] = assignment["critic_assignment"][
        "run_nonce"
    ]
    corpus = json.loads(context["corpus"].read_text(encoding="utf-8"))

    with pytest.raises(RuntimeError, match="reuses a nonce"):
        require_development_evidence_plan(
            plan,
            corpus=corpus,
            corpus_sha256=hashlib.sha256(context["corpus"].read_bytes()).hexdigest(),
        )

    drifted = deepcopy(context["plan"])
    drifted["cases"][0]["assignment_sha256"] = "f" * 64
    with pytest.raises(RuntimeError, match="assignment hash mismatch"):
        require_development_evidence_plan(
            drifted,
            corpus=corpus,
            corpus_sha256=hashlib.sha256(context["corpus"].read_bytes()).hexdigest(),
        )


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        (lambda row: row["critic_stage"].__setitem__("input_sha256", "f" * 64), "input hash mismatch"),
        (lambda row: row["author_stage"].__setitem__("output_sha256", "f" * 64), "output hash mismatch"),
        (
            lambda row: row["critic_stage"]["access_receipt"].__setitem__(
                "prior_candidates", True
            ),
            "forbidden or missing evidence access",
        ),
        (
            lambda row: row["author_stage"].__setitem__(
                "capability_profile", "lower_capability"
            ),
            "does not match its assignment: capability_profile",
        ),
        (
            lambda row: row["author_stage"].__setitem__("host_profile", "claude"),
            "does not match its assignment: host_profile",
        ),
        (
            lambda row: row["author_stage"]["execution_profile"].__setitem__(
                "model", "unpinned-model"
            ),
            "pinned contract",
        ),
        (
            lambda row: row["author_stage"]["host_runtime"].__setitem__(
                "host_profile", "claude"
            ),
            "assigned host",
        ),
        (lambda row: row["critic_stage"].__setitem__("attempt_count", 2), "attempt, or repair"),
        (lambda row: row["critic_stage"].__setitem__("wall_ms", 0), "positive integer"),
        (
            lambda row: row["author_stage"]["token_usage"].__setitem__("total_tokens", 0),
            "positive integer",
        ),
        (
            lambda row: row["author_stage"].__setitem__(
                "validation_error_repair_count", 1
            ),
            "attempt, or repair",
        ),
    ],
)
def test_development_cohort_rejects_execution_receipt_drift(
    tmp_path: Path,
    mutation: Any,
    message: str,
) -> None:
    context = _context(tmp_path, outcome="commit")
    segment = deepcopy(context["segment"])
    mutation(segment["cases"][0])
    context["segment_path"] = _write(tmp_path / "drifted-segment.json", segment)

    with pytest.raises(RuntimeError, match=message):
        _compile(context, output=tmp_path / "drift-output.json")


def test_development_cohort_rejects_missing_challenge_and_run_hash_drift(
    tmp_path: Path,
) -> None:
    missing = _context(tmp_path / "missing", outcome="commit")
    segment = deepcopy(missing["segment"])
    author_stage = segment["cases"][0]["author_stage"]
    author_stage["self_challenge"].pop()
    author_stage["output_sha256"] = canonical_sha256(
        {
            "source_candidate_adjudication": author_stage[
                "source_candidate_adjudication"
            ],
            "semantic_extension": author_stage["semantic_extension"],
            "self_challenge": author_stage["self_challenge"],
        }
    )
    author_stage["run_sha256"] = run_evidence_sha256(
        {
            key: value
            for key, value in author_stage.items()
            if key
            not in {
                "source_candidate_adjudication",
                "semantic_extension",
                "semantic_intent",
            }
        }
    )
    missing["segment_path"] = _write(tmp_path / "missing-challenge.json", segment)
    with pytest.raises(RuntimeError, match="mandatory self-challenge coverage"):
        _compile(missing, output=tmp_path / "missing-output.json")

    drift = _context(tmp_path / "hash", outcome="commit")
    segment = deepcopy(drift["segment"])
    segment["cases"][0]["critic_stage"]["run_sha256"] = "f" * 64
    drift["segment_path"] = _write(tmp_path / "run-hash-drift.json", segment)
    with pytest.raises(RuntimeError, match="run evidence hash mismatch"):
        _compile(drift, output=tmp_path / "hash-output.json")


def test_development_cohort_rejects_stale_deterministic_law_report(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, outcome="commit")
    laws = _law_report("b" * 40)
    context["laws"] = _write(tmp_path / "stale-laws.json", laws)

    with pytest.raises(RuntimeError, match="stale for the implementation revision"):
        _compile(context, output=tmp_path / "stale-law-output.json")


def test_development_evidence_has_no_semantic_matcher_dependency() -> None:
    for source in (
        SCRIPTS_ROOT / "greenfield_semantic_development_evidence.py",
        SCRIPTS_ROOT / "greenfield_semantic_development_cohort.py",
        SCRIPTS_ROOT / "greenfield_semantic_host_execution.py",
        SCRIPTS_ROOT / "greenfield_semantic_host_execution_contract.py",
    ):
        tree = ast.parse(source.read_text(encoding="utf-8"))
        imported = {
            alias.name.split(".")[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in node.names
        }
        assert imported.isdisjoint(
            {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
        )
    text = (SCRIPTS_ROOT / "greenfield_semantic_development_cohort.py").read_text(
        encoding="utf-8"
    )
    assert 'corpus.get("annotations")' not in text
    assert "similarity" not in text.casefold()


def _context(
    tmp_path: Path,
    *,
    outcome: str,
    include_annotations: bool = False,
) -> dict[str, Any]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    fixture = _smoke_packet() if outcome == "commit" else semantic_clarification_packet()
    prompt = _smoke_prompt()
    corpus_value: dict[str, Any] = {
        "cases": [{"case_id": "claim-desk", "prompt": prompt}],
    }
    if include_annotations:
        corpus_value["annotations"] = [{"private": "must never reach a phase input"}]
    corpus = _write(tmp_path / "corpus.json", corpus_value)
    plan_path = tmp_path / "plan.json"
    plan = prepare_development_evidence_plan(
        corpus_path=corpus,
        host_profiles=["codex"],
        output_path=plan_path,
    )
    assessment = deepcopy(fixture["materiality_assessment"])
    assessment["authoring_contract_sha256"] = semantic_intent_authoring_contract_sha256()
    semantic_intent = deepcopy(fixture["semantic_intent"])
    semantic_extension = _extension_from_intent(semantic_intent)
    source_candidate_adjudication = deepcopy(
        fixture["source_candidate_adjudication"]
    )
    assignment = plan["cases"][0]
    critic_input = build_materiality_critic_input(
        corpus_path=corpus,
        evidence_plan_path=plan_path,
        case_id="claim-desk",
    )
    author_input = build_semantic_graph_author_input(
        corpus_path=corpus,
        evidence_plan_path=plan_path,
        case_id="claim-desk",
        materiality_assessment=assessment,
    )
    materiality_sha = semantic_materiality_assessment_sha256(assessment)
    critic = _run_receipt(
        assignment["critic_assignment"],
        stage="critic",
        input_value=critic_input,
        output_value=assessment,
    )
    critic["materiality_assessment"] = assessment
    author = _run_receipt(
        assignment["author_assignment"],
        stage="author",
        input_value=author_input,
        output_value={
            "source_candidate_adjudication": source_candidate_adjudication,
            "semantic_extension": semantic_extension,
        },
        materiality_sha256=materiality_sha,
    )
    author["source_candidate_adjudication"] = source_candidate_adjudication
    author["semantic_extension"] = semantic_extension
    author["semantic_intent"] = semantic_intent
    segment = {
        "version": AUTHOR_SEGMENT_VERSION,
        "evidence_plan_sha256": canonical_sha256(plan),
        "cohort_nonce": plan["cohort_nonce"],
        "cases": [
            {
                "case_id": "claim-desk",
                "case_nonce": assignment["case_nonce"],
                "outcome": outcome,
                "critic_stage": critic,
                "author_stage": author,
            }
        ],
    }
    segment_path = _write(tmp_path / "segment.json", segment)
    laws = _write(tmp_path / "laws.json", _law_report(REVISION))
    return {
        "prompt": prompt,
        "corpus": corpus,
        "plan": plan,
        "plan_path": plan_path,
        "assessment": assessment,
        "segment": segment,
        "segment_path": segment_path,
        "laws": laws,
    }


def _extension_from_intent(semantic_intent: dict[str, Any]) -> dict[str, Any]:
    return semantic_graph_extension_from_intent(semantic_intent)


def _run_receipt(
    assignment: dict[str, Any],
    *,
    stage: str,
    input_value: dict[str, Any],
    output_value: dict[str, Any],
    materiality_sha256: str = "",
) -> dict[str, Any]:
    self_challenge = [
        {"challenge": challenge, "status": "passed"}
        for challenge in SEMANTIC_INTENT_MANDATORY_CHALLENGES
    ]
    exact_output = (
        {**output_value, "self_challenge": self_challenge}
        if stage == "author"
        else output_value
    )
    row: dict[str, Any] = {
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
            "runtime_binary_sha256": "d" * 64,
        },
        "independent_context": True,
        "attempt_count": 1,
        "validation_error_repair_count": 0,
        "input_sha256": canonical_sha256(input_value),
        "output_sha256": canonical_sha256(exact_output),
        "access_receipt": expected_access_receipt(stage),
        "wall_ms": 10,
        "token_usage": {
            "input_tokens": 10,
            "output_tokens": 20,
            "total_tokens": 30,
            "measurement_basis": "provider_usage_receipt",
        },
    }
    if stage == "author":
        row["materiality_assessment_sha256"] = materiality_sha256
        row["self_challenge"] = self_challenge
    row["run_sha256"] = run_evidence_sha256(row)
    return row


def _compile(context: dict[str, Any], *, output: Path) -> dict[str, Any]:
    return compile_development_candidate_bundle(
        corpus_path=context["corpus"],
        evidence_plan_path=context["plan_path"],
        segment_paths=[context["segment_path"]],
        deterministic_law_evidence_path=context["laws"],
        implementation_revision=REVISION,
        output_path=output,
    )


def _smoke_packet() -> dict[str, Any]:
    fixture = json.loads(
        (SCRIPTS_ROOT / "fixtures" / "greenfield-semantic-smoke.v12.json").read_text(
            encoding="utf-8"
        )
    )
    return fixture["packet"]


def _smoke_prompt() -> str:
    fixture = json.loads(
        (SCRIPTS_ROOT / "fixtures" / "greenfield-semantic-smoke.v12.json").read_text(
            encoding="utf-8"
        )
    )
    return fixture["prompt"]


def _write(path: Path, value: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, sort_keys=True) + "\n", encoding="utf-8")
    return path
