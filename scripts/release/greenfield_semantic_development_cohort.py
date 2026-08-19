"""Compile active Greenfield pipeline receipts into a release candidate bundle."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
from pathlib import Path
from typing import Any

from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_release_support import exclusive_json
from greenfield_semantic_deterministic_law_contract import (
    require_deterministic_law_report,
)
from greenfield_semantic_pipeline_evidence import ACTIVE_EVIDENCE_PLAN_VERSION
from greenfield_semantic_pipeline_evidence import require_active_evidence_plan
from greenfield_semantic_pipeline_evidence import require_successful_pipeline_evidence
from greenfield_semantic_pipeline_receipts import BOUNDED_PIPELINE_VERSION
from greenfield_semantic_pipeline_receipts import PIPELINE_VERSION
from greenfield_semantic_release_evidence import CANDIDATE_BUNDLE_VERSION
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    SEMANTIC_EXECUTION_EVIDENCE_VERSION,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_packet import (
    require_semantic_intent_packet,
)


def compile_development_candidate_bundle(
    *,
    corpus_path: Path,
    active_evidence_plan_path: Path,
    receipt_paths: Sequence[Path],
    deterministic_law_evidence_path: Path,
    implementation_revision: str,
    output_path: Path,
) -> dict[str, Any]:
    """Bind each frozen assignment to one successful active-mechanism receipt."""

    revision = _git_revision(implementation_revision)
    corpus_file, corpus = _json_file(corpus_path, "development corpus")
    corpus_sha256 = _sha256_file(corpus_file)
    cases = _case_index(corpus)
    _, raw_plan = _json_file(active_evidence_plan_path, "active evidence plan")
    plan = require_active_evidence_plan(
        raw_plan,
        corpus=corpus,
        corpus_sha256=corpus_sha256,
    )
    plan_sha256 = canonical_sha256(plan)
    assignments = _unique_index(plan["cases"], "case_id", "active assignments")
    _, raw_laws = _json_file(
        deterministic_law_evidence_path, "deterministic law report"
    )
    law_report = require_deterministic_law_report(
        raw_laws,
        implementation_revision=revision,
        candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
        development_evidence_plan_version=ACTIVE_EVIDENCE_PLAN_VERSION,
        development_author_segment_version=PIPELINE_VERSION,
        mechanism_evidence_version=SEMANTIC_EXECUTION_EVIDENCE_VERSION,
    )
    law_sha256 = canonical_sha256(law_report)
    receipts = _receipt_index(receipt_paths)
    if set(receipts) != set(cases):
        raise RuntimeError("active pipeline receipts must cover every case exactly once")
    compiled = [
        _compile_case(
            case_id=case_id,
            prompt=_text(cases[case_id].get("prompt"), f"{case_id} prompt"),
            assignment=assignments[case_id],
            receipt=receipts[case_id],
            law_report_sha256=law_sha256,
        )
        for case_id in sorted(cases)
    ]
    bundle = {
        "version": CANDIDATE_BUNDLE_VERSION,
        "corpus_sha256": corpus_sha256,
        "implementation_revision": revision,
        "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
        "active_evidence_plan_sha256": plan_sha256,
        "deterministic_law_report_sha256": law_sha256,
        "cohort_nonce": plan["cohort_nonce"],
        "cases": compiled,
    }
    exclusive_json(Path(output_path).expanduser().resolve(), bundle)
    return bundle


def _compile_case(
    *,
    case_id: str,
    prompt: str,
    assignment: Mapping[str, Any],
    receipt: Mapping[str, Any],
    law_report_sha256: str,
) -> dict[str, Any]:
    attempt = _attempt(receipt)
    packet = _mapping(attempt.get("packet"), f"{case_id} semantic packet")
    try:
        verified = require_semantic_intent_packet(packet, prompt=prompt)
        evidence, metadata = require_successful_pipeline_evidence(
            receipt,
            case_id=case_id,
            prompt=prompt,
            semantic_artifact=packet,
            assignment=assignment,
        )
    except (RuntimeError, ValueError) as error:
        raise RuntimeError(f"{case_id} active pipeline evidence is invalid: {error}") from error
    outcome = str(attempt["outcome"])
    status = str(verified.semantic_intent.get("status"))
    if (outcome, status) not in {
        ("commit", "complete"),
        ("clarify", "clarification_required"),
    }:
        raise RuntimeError(f"{case_id} active outcome disagrees with its semantic packet")
    if outcome == "commit":
        review_package = metadata["review_package"]
        transaction_proof = {
            "status": "passed",
            "transaction_sha256": metadata["transaction_sha256"],
            "package_sha256": metadata["review_package_sha256"],
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_report_sha256,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": True,
            "rollback_recovery_passed": True,
        }
    else:
        review_package = None
        transaction_proof = {
            "status": "not_applicable",
            "transaction_sha256": "",
            "package_sha256": "",
            "deterministic_law_failures": [],
            "deterministic_law_evidence_sha256": law_report_sha256,
            "post_confirm_semantic_calls": 0,
            "sealed_readback_equal": False,
            "rollback_recovery_passed": False,
        }
    return {
        "case_id": case_id,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "outcome": outcome,
        "semantic_artifact": packet,
        "mechanism_evidence": evidence,
        "review_package": review_package,
        "transaction_proof": transaction_proof,
    }


def _receipt_index(paths: Sequence[Path]) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for path in paths:
        _, receipt = _json_file(path, "active pipeline receipt")
        case_id = _text(receipt.get("case_id"), "receipt case id")
        if case_id in result:
            raise RuntimeError(f"active pipeline receipt is duplicated: {case_id}")
        result[case_id] = receipt
    return result


def _attempt(receipt: Mapping[str, Any]) -> dict[str, Any]:
    version = receipt.get("version")
    if version == PIPELINE_VERSION:
        return dict(receipt)
    if version == BOUNDED_PIPELINE_VERSION:
        return _mapping(receipt.get("attempt"), "rescue pipeline attempt")
    raise RuntimeError("active pipeline receipt uses an unsupported version")


def _case_index(corpus: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = corpus.get("cases")
    if not isinstance(rows, list) or any(not isinstance(row, Mapping) for row in rows):
        raise RuntimeError("development corpus cases must be a JSON object array")
    return _unique_index(rows, "case_id", "development corpus cases")


def _unique_index(
    rows: Sequence[Mapping[str, Any]], key: str, label: str
) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for row in rows:
        value = _text(row.get(key), f"{label}.{key}")
        if value in result:
            raise RuntimeError(f"{label} contains duplicate {key}: {value}")
        result[value] = dict(row)
    return result


def _json_file(path: Path, label: str) -> tuple[Path, dict[str, Any]]:
    target = Path(path).expanduser().resolve()
    if not target.is_file():
        raise RuntimeError(f"{label} does not exist: {target}")
    try:
        value = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} is not readable JSON") from error
    return target, _mapping(value, label)


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{label} must be non-empty text")
    return text


def _git_revision(value: Any) -> str:
    revision = _text(value, "implementation revision")
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
    parser.add_argument("--active-evidence-plan", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, action="append", required=True)
    parser.add_argument("--deterministic-law-evidence", type=Path, required=True)
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    compile_development_candidate_bundle(
        corpus_path=args.corpus,
        active_evidence_plan_path=args.active_evidence_plan,
        receipt_paths=args.receipt,
        deterministic_law_evidence_path=args.deterministic_law_evidence,
        implementation_revision=args.implementation_revision,
        output_path=args.output,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ["CANDIDATE_BUNDLE_VERSION", "compile_development_candidate_bundle"]
