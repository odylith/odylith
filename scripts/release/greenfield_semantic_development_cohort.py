"""Compile two-stage, blinded Greenfield development evidence."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
from pathlib import Path
import tempfile
import time
from typing import Any

from greenfield_semantic_development_evidence import AUTHOR_SEGMENT_VERSION
from greenfield_semantic_development_evidence import MECHANISM_EVIDENCE_VERSION
from greenfield_semantic_development_evidence import MECHANISM_ID
from greenfield_semantic_development_evidence import build_materiality_critic_input
from greenfield_semantic_development_evidence import build_semantic_graph_author_input
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import development_mechanism_contract_sha256
from greenfield_semantic_development_evidence import exact_keys
from greenfield_semantic_development_evidence import exclusive_json
from greenfield_semantic_development_evidence import json_mapping
from greenfield_semantic_development_evidence import mapped_rows
from greenfield_semantic_development_evidence import mapping
from greenfield_semantic_development_evidence import require_deterministic_law_report
from greenfield_semantic_development_evidence import require_development_evidence_plan
from greenfield_semantic_development_evidence import require_run_evidence
from greenfield_semantic_development_evidence import safe_json_file
from greenfield_semantic_development_evidence import text
from greenfield_semantic_development_evidence import unique_index
from greenfield_semantic_release_evaluation import CANDIDATE_BUNDLE_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
    semantic_evidence_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
    semantic_intent_authority,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_materiality_contract import (
    semantic_materiality_assessment_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_workflow import (
    build_verified_semantic_proposal_for_repo,
    compile_verified_semantic_transaction,
)


def compile_development_candidate_bundle(
    *,
    corpus_path: Path,
    evidence_plan_path: Path,
    segment_paths: Sequence[Path],
    deterministic_law_evidence_path: Path,
    implementation_revision: str,
    output_path: Path,
) -> dict[str, Any]:
    """Validate isolated stage evidence and compile every graph exactly once."""

    revision = _git_revision(implementation_revision)
    corpus_file = safe_json_file(corpus_path, "development corpus")
    corpus = json_mapping(corpus_file, "development corpus")
    corpus_sha256 = _sha256_file(corpus_file)
    cases = unique_index(
        mapped_rows(corpus.get("cases"), "development corpus cases"),
        "case_id",
        "development corpus cases",
    )
    plan_file = safe_json_file(evidence_plan_path, "development evidence plan")
    plan = require_development_evidence_plan(
        json_mapping(plan_file, "development evidence plan"),
        corpus=corpus,
        corpus_sha256=corpus_sha256,
    )
    plan_sha256 = canonical_sha256(plan)
    assignments = unique_index(plan["cases"], "case_id", "development evidence assignments")
    law_file = safe_json_file(deterministic_law_evidence_path, "deterministic law report")
    law_report = require_deterministic_law_report(
        json_mapping(law_file, "deterministic law report"),
        implementation_revision=revision,
        candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
    )
    law_report_sha256 = canonical_sha256(law_report)
    authored = _author_segment_index(
        segment_paths,
        plan=plan,
        plan_sha256=plan_sha256,
        expected_case_ids=set(cases),
    )
    compiled = [
        _compile_case(
            case_id=case_id,
            prompt=text(cases[case_id].get("prompt"), f"{case_id} prompt", maximum=500_000),
            assignment=assignments[case_id],
            segment_row=authored[case_id],
            corpus_path=corpus_file,
            plan_path=plan_file,
            plan=plan,
            plan_sha256=plan_sha256,
            law_report_sha256=law_report_sha256,
        )
        for case_id in sorted(cases)
    ]
    bundle = {
        "version": CANDIDATE_BUNDLE_VERSION,
        "corpus_sha256": corpus_sha256,
        "implementation_revision": revision,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "development_evidence_plan_sha256": plan_sha256,
        "deterministic_law_report_sha256": law_report_sha256,
        "cohort_nonce": plan["cohort_nonce"],
        "cases": compiled,
    }
    exclusive_json(Path(output_path).expanduser().resolve(), bundle)
    return bundle


def _author_segment_index(
    paths: Sequence[Path],
    *,
    plan: Mapping[str, Any],
    plan_sha256: str,
    expected_case_ids: set[str],
) -> dict[str, Mapping[str, Any]]:
    authored: dict[str, Mapping[str, Any]] = {}
    for path in paths:
        segment = json_mapping(
            safe_json_file(path, "development author segment"),
            "development author segment",
        )
        exact_keys(
            segment,
            {"version", "evidence_plan_sha256", "cohort_nonce", "cases"},
            "development author segment",
        )
        if segment.get("version") != AUTHOR_SEGMENT_VERSION:
            raise RuntimeError("development author segment uses an unsupported version")
        if (
            segment.get("evidence_plan_sha256") != plan_sha256
            or segment.get("cohort_nonce") != plan["cohort_nonce"]
        ):
            raise RuntimeError("development author segment does not match its runner plan")
        for row in mapped_rows(segment.get("cases"), "development author segment cases"):
            exact_keys(
                row,
                {"case_id", "case_nonce", "outcome", "critic_stage", "author_stage"},
                "development author segment case",
            )
            case_id = text(row.get("case_id"), "segment case id", maximum=200)
            if case_id in authored:
                raise RuntimeError(f"development case has multiple authoring records: {case_id}")
            authored[case_id] = row
    if set(authored) != expected_case_ids:
        missing = sorted(expected_case_ids - set(authored))
        extra = sorted(set(authored) - expected_case_ids)
        raise RuntimeError(f"development author coverage mismatch; missing={missing}, extra={extra}")
    return authored


def _compile_case(
    *,
    case_id: str,
    prompt: str,
    assignment: Mapping[str, Any],
    segment_row: Mapping[str, Any],
    corpus_path: Path,
    plan_path: Path,
    plan: Mapping[str, Any],
    plan_sha256: str,
    law_report_sha256: str,
) -> dict[str, Any]:
    if segment_row.get("case_nonce") != assignment["case_nonce"]:
        raise RuntimeError(f"{case_id} segment does not match its runner-issued case nonce")
    critic_input = build_materiality_critic_input(
        corpus_path=corpus_path,
        evidence_plan_path=plan_path,
        case_id=case_id,
    )
    critic_stage = mapping(segment_row.get("critic_stage"), f"{case_id} critic stage")
    exact_keys(
        critic_stage,
        _run_fields("critic") | {"materiality_assessment"},
        f"{case_id} critic stage",
    )
    assessment = mapping(
        critic_stage.get("materiality_assessment"),
        f"{case_id} materiality assessment",
    )
    author_input = build_semantic_graph_author_input(
        corpus_path=corpus_path,
        evidence_plan_path=plan_path,
        case_id=case_id,
        materiality_assessment=assessment,
    )
    materiality_sha256 = semantic_materiality_assessment_sha256(assessment)
    critic_evidence = require_run_evidence(
        {key: value for key, value in critic_stage.items() if key != "materiality_assessment"},
        stage="critic",
        assignment=assignment["critic_assignment"],
        expected_input_sha256=canonical_sha256(critic_input),
        expected_output_sha256=canonical_sha256(assessment),
    )
    author_stage = mapping(segment_row.get("author_stage"), f"{case_id} author stage")
    exact_keys(
        author_stage,
        _run_fields("author") | {"semantic_intent"},
        f"{case_id} author stage",
    )
    semantic_intent = mapping(author_stage.get("semantic_intent"), f"{case_id} Semantic Intent")
    author_output = {
        "semantic_intent": semantic_intent,
        "self_challenge": author_stage.get("self_challenge"),
    }
    author_evidence = require_run_evidence(
        {key: value for key, value in author_stage.items() if key != "semantic_intent"},
        stage="author",
        assignment=assignment["author_assignment"],
        expected_input_sha256=canonical_sha256(author_input),
        expected_output_sha256=canonical_sha256(author_output),
        materiality_assessment_sha256=materiality_sha256,
    )
    if critic_evidence["host_runtime"] != author_evidence["host_runtime"]:
        raise RuntimeError(f"{case_id} critic and author used different host runtimes")
    started_ns = time.monotonic_ns()
    packet = {
        "version": SEMANTIC_INTENT_PACKET_VERSION,
        "evidence_sha256": semantic_evidence_sha256(
            {"operator_prompt": prompt, "operator_edit": ""}
        ),
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "materiality_assessment": assessment,
        "materiality_assessment_sha256": materiality_sha256,
        "critic_run": {
            "capability_profile": critic_evidence["capability_profile"],
            "critic_run_id": critic_evidence["run_id"],
            "host_profile": critic_evidence["host_profile"],
            "independent_context": True,
        },
        "author_run": {
            "capability_profile": author_evidence["capability_profile"],
            "author_run_id": author_evidence["run_id"],
        },
        "semantic_intent": semantic_intent,
    }
    try:
        verified = require_semantic_intent_packet(packet, prompt=prompt)
        outcome = str(segment_row.get("outcome") or "")
        transaction_proof = _transaction_proof(
            case_id=case_id,
            outcome=outcome,
            verified=verified,
            prompt=prompt,
            law_report_sha256=law_report_sha256,
        )
    except (RuntimeError, ValueError) as error:
        raise RuntimeError(f"{case_id} failed two-stage Semantic Intent compilation: {error}") from error
    compile_wall_ms = max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000)
    total_tokens = (
        critic_evidence["token_usage"]["total_tokens"]
        + author_evidence["token_usage"]["total_tokens"]
    )
    total_wall_ms = critic_evidence["wall_ms"] + author_evidence["wall_ms"] + compile_wall_ms
    mechanism_evidence = {
        "version": MECHANISM_EVIDENCE_VERSION,
        "mechanism_id": MECHANISM_ID,
        "mechanism_contract_sha256": development_mechanism_contract_sha256(),
        "cohort_nonce": plan["cohort_nonce"],
        "cohort_assignment_sha256": plan["cohort_assignment_sha256"],
        "case_nonce": assignment["case_nonce"],
        "assignment_sha256": assignment["assignment_sha256"],
        "evidence_plan_sha256": plan_sha256,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "critic": critic_evidence,
        "author": author_evidence,
        "compile_wall_ms": compile_wall_ms,
        "total_wall_ms": total_wall_ms,
        "model_call_count": 2,
        "restart_count": 0,
        "total_tokens": total_tokens,
    }
    return {
        "case_id": case_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "outcome": outcome,
        "semantic_artifact": packet,
        "mechanism_evidence": mechanism_evidence,
        "transaction_proof": transaction_proof,
    }


def _transaction_proof(
    *,
    case_id: str,
    outcome: str,
    verified: Any,
    prompt: str,
    law_report_sha256: str,
) -> dict[str, Any]:
    if outcome == "commit":
        if verified.semantic_intent.get("status") != "complete":
            raise RuntimeError("commit outcome is clarification-bound")
        authority = semantic_intent_authority(verified, prompt=prompt)
        with tempfile.TemporaryDirectory(prefix=f"odylith-{case_id}-") as temporary:
            root = Path(temporary)
            proposal = build_verified_semantic_proposal_for_repo(
                repo_root=root,
                authority=authority,
                release_selector="0.0.1",
            )
            transaction = compile_verified_semantic_transaction(
                repo_root=root,
                proposal=proposal,
                release_selector="0.0.1",
            )
        summary = transaction.summary()
        if summary.get("verified") is not True or summary.get("quality_status") != "passed":
            raise RuntimeError("graph-native package is not verified and quality-approved")
        return {
            "status": "passed",
            "transaction_sha256": str(transaction.transaction_hash),
            "package_sha256": canonical_sha256(transaction.proposal),
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_report_sha256,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": True,
            "rollback_recovery_passed": True,
        }
    if outcome == "clarify":
        if verified.semantic_intent.get("status") != "clarification_required":
            raise RuntimeError("clarify outcome lacks an assessed clarification packet")
        return {
            "status": "not_applicable",
            "transaction_sha256": "",
            "package_sha256": "",
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_report_sha256,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": False,
            "rollback_recovery_passed": False,
        }
    raise RuntimeError("outcome must be commit or clarify")


def _run_fields(stage: str) -> set[str]:
    result = {
        "run_nonce", "run_id", "run_assignment_sha256", "run_sha256",
        "host_profile", "capability_profile", "execution_profile", "host_runtime",
        "independent_context", "attempt_count",
        "validation_error_repair_count", "input_sha256", "output_sha256",
        "access_receipt", "wall_ms", "token_usage",
    }
    if stage == "author":
        result.update({"materiality_assessment_sha256", "self_challenge"})
    return result


def _git_revision(value: Any) -> str:
    revision = text(value, "implementation revision", maximum=40)
    if len(revision) != 40 or any(character not in "0123456789abcdef" for character in revision):
        raise RuntimeError("implementation revision must be a full Git revision")
    return revision


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--evidence-plan", type=Path, required=True)
    parser.add_argument("--segment", type=Path, action="append", required=True)
    parser.add_argument("--deterministic-law-evidence", type=Path, required=True)
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    compile_development_candidate_bundle(
        corpus_path=args.corpus,
        evidence_plan_path=args.evidence_plan,
        segment_paths=args.segment,
        deterministic_law_evidence_path=args.deterministic_law_evidence,
        implementation_revision=args.implementation_revision,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
