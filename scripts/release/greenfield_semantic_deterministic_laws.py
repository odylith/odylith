"""Produce revision-bound deterministic Greenfield law evidence from real tests."""

from __future__ import annotations

import argparse
from collections.abc import Callable, Mapping, Sequence
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from greenfield_semantic_development_cohort import CANDIDATE_BUNDLE_VERSION
from greenfield_semantic_development_evidence import AUTHOR_SEGMENT_VERSION
from greenfield_semantic_development_evidence import DETERMINISTIC_LAW_REPORT_VERSION
from greenfield_semantic_development_evidence import DEVELOPMENT_EVIDENCE_PLAN_VERSION
from greenfield_semantic_development_evidence import MECHANISM_EVIDENCE_VERSION
from greenfield_semantic_development_evidence import REQUIRED_DETERMINISTIC_LAW_IDS
from greenfield_semantic_development_evidence import canonical_sha256
from greenfield_semantic_development_evidence import exclusive_json
from greenfield_semantic_deterministic_law_contract import DETERMINISTIC_LAW_EVIDENCE_VERSION
from greenfield_semantic_deterministic_law_contract import deterministic_law_command
from greenfield_semantic_deterministic_law_contract import require_deterministic_law_report
from odylith.runtime.domain_intelligence.greenfield_semantic_authoring_contract import (
    semantic_intent_authoring_contract_sha256,
)
from odylith.runtime.domain_intelligence.greenfield_semantic_intent_contract import (
    SEMANTIC_INTENT_PACKET_VERSION,
)


def produce_deterministic_law_report(
    *,
    repo_root: Path,
    implementation_revision: str,
    output_path: Path,
    timeout_seconds: int = 300,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> dict[str, Any]:
    """Run every law once and write a report only after all seven pass."""

    root = Path(repo_root).expanduser().resolve()
    revision = _git_revision(root, runner=runner)
    if implementation_revision != revision:
        raise RuntimeError("deterministic law request does not match the checked-out revision")
    if timeout_seconds <= 0:
        raise RuntimeError("deterministic law timeout must be positive")
    _require_clean_revision(root, runner=runner)

    results: list[dict[str, Any]] = []
    for law_id in REQUIRED_DETERMINISTIC_LAW_IDS:
        command = deterministic_law_command(
            law_id=law_id, python_executable=sys.executable,
        )
        evidence = _run_law(
            root=root,
            revision=revision,
            law_id=law_id,
            command=command,
            timeout_seconds=timeout_seconds,
            runner=runner,
        )
        results.append(
            {
                "law_id": law_id,
                "status": "passed",
                "evidence": evidence,
                "evidence_sha256": canonical_sha256(evidence),
            }
        )

    report = {
        "version": DETERMINISTIC_LAW_REPORT_VERSION,
        "implementation_revision": revision,
        "contracts": {
            "authoring_contract_sha256": semantic_intent_authoring_contract_sha256(),
            "semantic_intent_packet_version": SEMANTIC_INTENT_PACKET_VERSION,
            "development_evidence_plan_version": DEVELOPMENT_EVIDENCE_PLAN_VERSION,
            "development_author_segment_version": AUTHOR_SEGMENT_VERSION,
            "mechanism_evidence_version": MECHANISM_EVIDENCE_VERSION,
            "candidate_bundle_version": CANDIDATE_BUNDLE_VERSION,
        },
        "required_law_ids": list(REQUIRED_DETERMINISTIC_LAW_IDS),
        "results": results,
    }
    verified = require_deterministic_law_report(
        report,
        implementation_revision=revision,
        candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
        development_evidence_plan_version=DEVELOPMENT_EVIDENCE_PLAN_VERSION,
        development_author_segment_version=AUTHOR_SEGMENT_VERSION,
        mechanism_evidence_version=MECHANISM_EVIDENCE_VERSION,
    )
    exclusive_json(Path(output_path).expanduser().resolve(), verified)
    return verified


def _run_law(
    *,
    root: Path,
    revision: str,
    law_id: str,
    command: Sequence[str],
    timeout_seconds: int,
    runner: Callable[..., subprocess.CompletedProcess[str]],
) -> dict[str, Any]:
    environment = dict(os.environ)
    environment["PYTHONPATH"] = "src:."
    started_ns = time.monotonic_ns()
    try:
        result = runner(
            list(command),
            cwd=str(root),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise RuntimeError(f"deterministic law timed out without retry: {law_id}") from error
    if result.returncode != 0:
        detail = "\n".join(
            part for part in (result.stderr.strip(), result.stdout.strip()) if part
        )[-3000:]
        raise RuntimeError(f"deterministic law failed: {law_id}: {detail}")
    duration_ms = max(1, (time.monotonic_ns() - started_ns + 999_999) // 1_000_000)
    return {
        "version": DETERMINISTIC_LAW_EVIDENCE_VERSION,
        "implementation_revision": revision,
        "law_id": law_id,
        "command": list(command),
        "returncode": 0,
        "duration_ms": duration_ms,
        "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8")).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8")).hexdigest(),
    }


def _git_revision(
    root: Path, *, runner: Callable[..., subprocess.CompletedProcess[str]]
) -> str:
    result = runner(
        ["git", "rev-parse", "HEAD"],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    revision = result.stdout.strip()
    if result.returncode != 0 or len(revision) != 40 or any(
        character not in "0123456789abcdef" for character in revision
    ):
        raise RuntimeError("deterministic law runner could not resolve a full Git revision")
    return revision


def _require_clean_revision(
    root: Path, *, runner: Callable[..., subprocess.CompletedProcess[str]]
) -> None:
    result = runner(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=str(root),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
        check=False,
    )
    if result.returncode != 0 or result.stdout.strip():
        raise RuntimeError("deterministic law evidence requires a clean revision")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--implementation-revision", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout-seconds", type=int, default=300)
    args = parser.parse_args(argv)
    produce_deterministic_law_report(
        repo_root=args.repo_root,
        implementation_revision=args.implementation_revision,
        output_path=args.output,
        timeout_seconds=args.timeout_seconds,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "DETERMINISTIC_LAW_EVIDENCE_VERSION",
    "produce_deterministic_law_report",
]
