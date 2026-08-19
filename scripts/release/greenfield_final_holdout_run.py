"""One-shot Greenfield final-holdout preparation and scoring rail."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any

from greenfield_final_holdout_guard import claim_final_holdout_run
from greenfield_final_holdout_guard import complete_final_holdout_run
from greenfield_final_holdout_guard import read_final_holdout_run
from greenfield_semantic_release_support import canonical_sha256
from greenfield_semantic_pipeline_evidence import prepare_active_evidence_plan
from greenfield_semantic_pipeline_evidence import require_active_evidence_plan
from greenfield_semantic_release_evaluation import _contract as _require_evaluation_contract
from greenfield_semantic_release_evaluation import evaluate_semantic_release
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_execution_contract import (
    semantic_execution_contract_sha256,
)


FINAL_HOLDOUT_WORK_VERSION = "odylith.greenfield.final-holdout-work.v3"
FINAL_HOLDOUT_FAILURE_VERSION = "odylith.greenfield.final-holdout-failure.v3"


def prepare_final_holdout_run(
    *,
    repo_root: Path,
    ledger_path: Path,
    holdout_path: Path,
    evaluation_manifest_path: Path,
    evaluation_contract_path: Path,
    work_path: Path,
    implementation_revision: str,
    expected_holdout_sha256: str,
    expected_evaluation_manifest_sha256: str,
    expected_corpus_sha256: str,
) -> dict[str, Any]:
    """Validate the public contract, then claim before disclosing frozen cases."""

    contract, contract_hash = _validated_evaluation_contract(evaluation_contract_path)
    claimed = claim_final_holdout_run(
        ledger_path=ledger_path,
        holdout_path=holdout_path,
        evaluation_manifest_path=evaluation_manifest_path,
        implementation_revision=implementation_revision,
        expected_holdout_sha256=expected_holdout_sha256,
        expected_evaluation_manifest_sha256=expected_evaluation_manifest_sha256,
        evaluation_contract_sha256=contract_hash,
        authoring_contract_sha256=semantic_intent_authoring_contract_sha256(),
    )
    target = Path(work_path).expanduser().resolve()
    try:
        root = Path(repo_root).expanduser().resolve()
        holdout = _json_file(holdout_path, "final holdout")
        manifest = _json_file(evaluation_manifest_path, "evaluation manifest")
        tracked = _mapping(manifest.get("tracked_corpus"), "evaluation manifest tracked_corpus")
        tracked_relative = Path(_text(tracked.get("path"), "tracked corpus path"))
        if tracked_relative.is_absolute() or ".." in tracked_relative.parts:
            raise RuntimeError("evaluation manifest tracked corpus path escapes the repository")
        tracked_path = (root / tracked_relative).resolve()
        if root not in tracked_path.parents or not tracked_path.is_file() or tracked_path.is_symlink():
            raise RuntimeError("evaluation manifest tracked corpus is missing or unsafe")
        corpus_hash = _sha256_file(tracked_path)
        expected_corpus = _sha256(expected_corpus_sha256, "expected corpus hash")
        if corpus_hash != expected_corpus or tracked.get("sha256") != expected_corpus:
            raise RuntimeError("tracked evaluation corpus does not match the frozen expected hash")
        cases = _mapped_rows(holdout.get("cases"), "final holdout cases")
        annotations = _mapped_rows(holdout.get("annotations"), "final holdout annotations")
        case_ids = [_text(row.get("case_id"), "final holdout case_id") for row in cases]
        annotation_ids = [_text(row.get("case_id"), "final holdout annotation case_id") for row in annotations]
        if len(case_ids) != len(set(case_ids)) or set(case_ids) != set(annotation_ids):
            raise RuntimeError("final holdout cases and annotations are not one-to-one")
        hosts = _strings(contract.get("required_host_profiles"), "required host profiles")
        with tempfile.TemporaryDirectory(prefix="odylith-final-holdout-plan-") as temporary:
            plan = prepare_active_evidence_plan(
                corpus_path=_safe_file(holdout_path, "final holdout"),
                host_profiles=hosts,
                output_path=Path(temporary) / "evidence-plan.json",
            )
        plan_sha256 = canonical_sha256(plan)
        plan_cases = {
            str(row["case_id"]): row
            for row in _mapped_rows(plan.get("cases"), "development evidence assignments")
        }
        by_id = {str(row["case_id"]): row for row in cases}
        assigned = []
        for case_id in sorted(case_ids):
            prompt = _text(by_id[case_id].get("prompt"), f"{case_id} prompt")
            assignment = plan_cases[case_id]
            assigned.append(
                {
                    "case_id": case_id,
                    "prompt": prompt,
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "case_nonce": assignment["case_nonce"],
                    "assignment_sha256": assignment["assignment_sha256"],
                    "host_profile": assignment["host_profile"],
                }
            )
        work = {
            "version": FINAL_HOLDOUT_WORK_VERSION,
            "status": "ready_for_blinded_authoring",
            "implementation_revision": claimed["implementation_revision"],
            "holdout_sha256": claimed["holdout_sha256"],
            "evaluation_manifest_sha256": claimed["evaluation_manifest_sha256"],
            "tracked_corpus_sha256": corpus_hash,
            "evaluation_contract_sha256": claimed["evaluation_contract_sha256"],
            "authoring_contract_sha256": claimed["authoring_contract_sha256"],
            "mechanism_contract_sha256": semantic_execution_contract_sha256(),
            "active_evidence_plan_sha256": plan_sha256,
            "active_evidence_plan": plan,
            "cases": assigned,
        }
        _exclusive_json(target, work)
        return work
    except BaseException as error:
        failure = {
            "version": FINAL_HOLDOUT_FAILURE_VERSION,
            "status": "failed",
            "stage": "prepare",
            "error": str(error),
        }
        failure_path = _prepare_failure_artifact(
            ledger_path=ledger_path,
            preferred_path=target,
            payload=failure,
        )
        complete_final_holdout_run(
            ledger_path=ledger_path,
            result_path=failure_path,
            outcome="failed",
        )
        raise


def score_final_holdout_run(
    *,
    ledger_path: Path,
    holdout_path: Path,
    evaluation_contract_path: Path,
    work_path: Path,
    deterministic_law_report_path: Path,
    candidates_path: Path,
    review_paths: Sequence[Path],
    adjudication_path: Path,
    host_parity_report_path: Path,
    lower_capability_safety_report_path: Path,
    result_path: Path,
) -> dict[str, Any]:
    """Score only an already claimed run and terminalize its one-shot ledger."""

    ledger = read_final_holdout_run(ledger_path)
    if ledger.get("status") != "claimed":
        raise RuntimeError("final holdout scoring requires one active claimed ledger")
    target = Path(result_path).expanduser().resolve()
    try:
        contract, contract_hash = _validated_evaluation_contract(evaluation_contract_path)
        if contract_hash != ledger.get("evaluation_contract_sha256"):
            raise RuntimeError("evaluation contract bytes changed after final holdout preparation")
        if semantic_intent_authoring_contract_sha256() != ledger.get(
            "authoring_contract_sha256"
        ):
            raise RuntimeError("Semantic Intent authoring contract changed after final holdout preparation")
        holdout_file = _safe_file(holdout_path, "final holdout")
        if _sha256_file(holdout_file) != ledger.get("holdout_sha256"):
            raise RuntimeError("final holdout bytes changed after the one-shot claim")
        corpus = _json_file(holdout_file, "final holdout")
        work = _json_file(work_path, "final holdout work")
        _exact_keys(
            work,
            {
                "version", "status", "implementation_revision", "holdout_sha256",
                "evaluation_manifest_sha256", "tracked_corpus_sha256",
                "evaluation_contract_sha256", "authoring_contract_sha256",
                "mechanism_contract_sha256", "active_evidence_plan_sha256",
                "active_evidence_plan", "cases",
            },
            "final holdout work",
        )
        if work.get("version") != FINAL_HOLDOUT_WORK_VERSION or work.get("status") != (
            "ready_for_blinded_authoring"
        ):
            raise RuntimeError("final holdout work uses an unsupported or non-ready schema")
        if (
            work.get("implementation_revision") != ledger.get("implementation_revision")
            or work.get("evaluation_contract_sha256") != contract_hash
            or work.get("authoring_contract_sha256") != ledger.get("authoring_contract_sha256")
            or work.get("holdout_sha256") != ledger.get("holdout_sha256")
            or work.get("evaluation_manifest_sha256")
            != ledger.get("evaluation_manifest_sha256")
            or work.get("mechanism_contract_sha256")
            != semantic_execution_contract_sha256()
        ):
            raise RuntimeError("final holdout work changed after preparation")
        evidence_plan = _mapping(
            work.get("active_evidence_plan"),
            "final holdout active evidence plan",
        )
        try:
            normalized_plan = require_active_evidence_plan(
                evidence_plan,
                corpus=corpus,
                corpus_sha256=str(ledger["holdout_sha256"]),
            )
        except (RuntimeError, ValueError) as error:
            raise RuntimeError(f"final holdout evidence plan is invalid: {error}") from error
        if work.get("active_evidence_plan_sha256") != canonical_sha256(normalized_plan):
            raise RuntimeError("final holdout evidence plan changed after preparation")
        _require_work_case_bindings(work, corpus=corpus, plan=normalized_plan)
        candidates = _json_file(candidates_path, "candidate bundle")
        if candidates.get("implementation_revision") != ledger.get("implementation_revision"):
            raise RuntimeError("candidate bundle was not authored against the claimed revision")
        report = evaluate_semantic_release(
            corpus=corpus,
            corpus_sha256=str(ledger["holdout_sha256"]),
            contract=contract,
            active_evidence_plan=normalized_plan,
            deterministic_law_report=_json_file(
                deterministic_law_report_path,
                "deterministic law report",
            ),
            candidates=candidates,
            reviews=[_json_file(path, "independent review") for path in review_paths],
            adjudication=_json_file(adjudication_path, "independent adjudication"),
            auxiliary_reports={
                "host_parity": _json_file(host_parity_report_path, "host parity report"),
                "lower_capability_safety": _json_file(
                    lower_capability_safety_report_path,
                    "lower capability safety report",
                ),
            },
        )
        _exclusive_json(target, report)
        complete_final_holdout_run(
            ledger_path=ledger_path,
            result_path=target,
            outcome="passed" if report["passed"] else "failed",
        )
        return report
    except BaseException as error:
        failure_path = _run_owned_failure_artifact(
            ledger_path=ledger_path,
            payload={
                "version": FINAL_HOLDOUT_FAILURE_VERSION,
                "status": "failed",
                "stage": "score",
                "error": str(error),
            },
        )
        if read_final_holdout_run(ledger_path).get("status") == "claimed":
            complete_final_holdout_run(
                ledger_path=ledger_path,
                result_path=failure_path,
                outcome="failed",
            )
        raise


def _validated_evaluation_contract(path: Path | str) -> tuple[dict[str, Any], str]:
    candidate = _safe_file(path, "evaluation contract")
    try:
        raw = candidate.read_bytes()
        contract = _mapping(json.loads(raw), "evaluation contract")
        _require_evaluation_contract(contract)
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise RuntimeError(f"evaluation contract is invalid: {error}") from error
    return contract, hashlib.sha256(raw).hexdigest()


def _prepare_failure_artifact(
    *,
    ledger_path: Path,
    preferred_path: Path,
    payload: Mapping[str, Any],
) -> Path:
    try:
        _exclusive_json(preferred_path, payload)
        return preferred_path
    except (OSError, RuntimeError):
        return _run_owned_failure_artifact(ledger_path=ledger_path, payload=payload)


def _run_owned_failure_artifact(
    *,
    ledger_path: Path,
    payload: Mapping[str, Any],
) -> Path:
    ledger = Path(ledger_path).expanduser().resolve()
    ledger.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_path = tempfile.mkstemp(
        prefix=f".{ledger.name}.failure.",
        suffix=".json",
        dir=ledger.parent,
        text=True,
    )
    path = Path(raw_path)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(path.parent)
        return path
    except BaseException:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _json_file(path: Path | str, label: str) -> dict[str, Any]:
    candidate = _safe_file(path, label)
    try:
        return _mapping(json.loads(candidate.read_text(encoding="utf-8")), label)
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"{label} is unreadable: {error}") from error


def _safe_file(path: Path | str, label: str) -> Path:
    expanded = Path(path).expanduser()
    if expanded.is_symlink():
        raise RuntimeError(f"{label} is missing or unsafe")
    candidate = expanded.resolve()
    if not candidate.is_file():
        raise RuntimeError(f"{label} is missing or unsafe")
    return candidate


def _exclusive_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags, 0o600)
    except FileExistsError as error:
        raise RuntimeError(f"final holdout output already exists: {path}") from error
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(dict(payload), sort_keys=True, separators=(",", ":")) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        _fsync_directory(path.parent)
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256(value: Any, label: str) -> str:
    digest = str(value or "").strip().casefold()
    if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
        raise RuntimeError(f"{label} must be a full lowercase SHA-256 digest")
    return digest


def _mapping(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise RuntimeError(f"{label} must be a JSON object")
    return dict(value)


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise RuntimeError(f"{label} fields do not match the versioned contract")


def _require_work_case_bindings(
    work: Mapping[str, Any],
    *,
    corpus: Mapping[str, Any],
    plan: Mapping[str, Any],
) -> None:
    source_rows = _mapped_rows(corpus.get("cases"), "final holdout cases")
    assignment_rows = _mapped_rows(plan.get("cases"), "active evidence assignments")
    work_rows = _mapped_rows(work.get("cases"), "final holdout work cases")
    source_cases = {
        str(row["case_id"]): row
        for row in source_rows
    }
    assignments = {
        str(row["case_id"]): row
        for row in assignment_rows
    }
    work_cases = {
        str(row["case_id"]): row
        for row in work_rows
    }
    if (
        len(source_cases) != len(source_rows)
        or len(assignments) != len(assignment_rows)
        or len(work_cases) != len(work_rows)
        or set(work_cases) != set(source_cases)
        or set(assignments) != set(source_cases)
    ):
        raise RuntimeError("final holdout work does not cover every assigned case exactly once")
    for case_id in sorted(source_cases):
        row = _mapping(work_cases[case_id], f"final holdout work case {case_id}")
        _exact_keys(
            row,
            {
                "case_id", "prompt", "prompt_sha256", "case_nonce", "assignment_sha256",
                "host_profile",
            },
            f"final holdout work case {case_id}",
        )
        prompt = _text(source_cases[case_id].get("prompt"), f"{case_id} prompt")
        assignment = assignments[case_id]
        expected = {
            "case_id": case_id,
            "prompt": prompt,
            "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
            "case_nonce": assignment["case_nonce"],
            "assignment_sha256": assignment["assignment_sha256"],
            "host_profile": assignment["host_profile"],
        }
        if row != expected:
            raise RuntimeError(f"final holdout work case changed after preparation: {case_id}")


def _mapped_rows(value: Any, label: str) -> list[Mapping[str, Any]]:
    if not isinstance(value, list) or any(not isinstance(row, Mapping) for row in value):
        raise RuntimeError(f"{label} must be a JSON object array")
    return [dict(row) for row in value]


def _text(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise RuntimeError(f"{label} must be non-empty text")
    return text


def _strings(value: Any, label: str) -> list[str]:
    if not isinstance(value, list):
        raise RuntimeError(f"{label} must be a string array")
    rows = [_text(item, label) for item in value]
    if not rows or len(rows) != len(set(rows)):
        raise RuntimeError(f"{label} must be non-empty and unique")
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    prepare = subparsers.add_parser("prepare")
    for name in (
        "repo_root", "ledger", "holdout", "manifest", "contract", "work",
        "revision", "expected_holdout_sha256", "expected_manifest_sha256", "expected_corpus_sha256",
    ):
        prepare.add_argument(f"--{name.replace('_', '-')}", required=True)
    score = subparsers.add_parser("score")
    for name in (
        "ledger", "holdout", "contract", "work", "deterministic_law_report",
        "candidates", "adjudication", "host_parity_report",
        "lower_capability_safety_report", "result",
    ):
        score.add_argument(f"--{name.replace('_', '-')}", required=True)
    score.add_argument("--review", action="append", required=True)
    args = parser.parse_args(argv)
    if args.command == "prepare":
        prepare_final_holdout_run(
            repo_root=Path(args.repo_root), ledger_path=Path(args.ledger), holdout_path=Path(args.holdout),
            evaluation_manifest_path=Path(args.manifest), evaluation_contract_path=Path(args.contract),
            work_path=Path(args.work), implementation_revision=args.revision,
            expected_holdout_sha256=args.expected_holdout_sha256,
            expected_evaluation_manifest_sha256=args.expected_manifest_sha256,
            expected_corpus_sha256=args.expected_corpus_sha256,
        )
    else:
        score_final_holdout_run(
            ledger_path=Path(args.ledger), holdout_path=Path(args.holdout),
            evaluation_contract_path=Path(args.contract), work_path=Path(args.work),
            deterministic_law_report_path=Path(args.deterministic_law_report),
            candidates_path=Path(args.candidates),
            review_paths=[Path(path) for path in args.review], adjudication_path=Path(args.adjudication),
            host_parity_report_path=Path(args.host_parity_report),
            lower_capability_safety_report_path=Path(args.lower_capability_safety_report),
            result_path=Path(args.result),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
