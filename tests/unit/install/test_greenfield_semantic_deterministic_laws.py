from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_semantic_development_cohort import CANDIDATE_BUNDLE_VERSION  # noqa: E402
from greenfield_semantic_development_evidence import (  # noqa: E402
    AUTHOR_SEGMENT_VERSION,
    DEVELOPMENT_EVIDENCE_PLAN_VERSION,
    MECHANISM_EVIDENCE_VERSION,
    REQUIRED_DETERMINISTIC_LAW_IDS,
    canonical_sha256,
)
from greenfield_semantic_deterministic_law_contract import (  # noqa: E402
    require_deterministic_law_report,
)
from greenfield_semantic_deterministic_laws import (  # noqa: E402
    produce_deterministic_law_report,
)
from tests.unit.install.greenfield_semantic_release_test_fixtures import (  # noqa: E402
    deterministic_law_report_fixture,
)


REVISION = "a" * 40


def test_real_law_owner_emits_one_revision_bound_report_after_every_pass(
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return _result(command, stdout=REVISION + "\n")
        if command[:2] == ["git", "status"]:
            return _result(command)
        law_id = REQUIRED_DETERMINISTIC_LAW_IDS[len(calls) - 3]
        return _result(command, stdout=f"{law_id}: passed\n")

    output = tmp_path / "laws.json"
    report = produce_deterministic_law_report(
        repo_root=ROOT,
        implementation_revision=REVISION,
        output_path=output,
        runner=runner,
    )

    assert output.is_file()
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert [row["law_id"] for row in report["results"]] == list(
        REQUIRED_DETERMINISTIC_LAW_IDS
    )
    assert all(row["status"] == "passed" for row in report["results"])
    assert all(row["evidence"]["command"] for row in report["results"])
    assert all(row["evidence"]["returncode"] == 0 for row in report["results"])
    assert all(row["evidence"]["duration_ms"] > 0 for row in report["results"])
    assert len(calls) == 2 + len(REQUIRED_DETERMINISTIC_LAW_IDS)
    require_deterministic_law_report(
        report,
        implementation_revision=REVISION,
        candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
        development_evidence_plan_version=DEVELOPMENT_EVIDENCE_PLAN_VERSION,
        development_author_segment_version=AUTHOR_SEGMENT_VERSION,
        mechanism_evidence_version=MECHANISM_EVIDENCE_VERSION,
    )


def test_dirty_revision_fails_before_any_law_or_output(tmp_path: Path) -> None:
    calls: list[list[str]] = []

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(command)
        if command[:2] == ["git", "rev-parse"]:
            return _result(command, stdout=REVISION + "\n")
        return _result(command, stdout=" M source.py\n")

    output = tmp_path / "laws.json"
    try:
        produce_deterministic_law_report(
            repo_root=ROOT,
            implementation_revision=REVISION,
            output_path=output,
            runner=runner,
        )
    except RuntimeError as error:
        assert "clean revision" in str(error)
    else:
        raise AssertionError("dirty revision unexpectedly produced law evidence")

    assert not output.exists()
    assert len(calls) == 2


def test_failed_law_has_no_retry_and_no_partial_output(tmp_path: Path) -> None:
    law_calls = 0

    def runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        nonlocal law_calls
        if command[:2] == ["git", "rev-parse"]:
            return _result(command, stdout=REVISION + "\n")
        if command[:2] == ["git", "status"]:
            return _result(command)
        law_calls += 1
        return _result(command, returncode=1, stderr="concrete law failure")

    output = tmp_path / "laws.json"
    try:
        produce_deterministic_law_report(
            repo_root=ROOT,
            implementation_revision=REVISION,
            output_path=output,
            runner=runner,
        )
    except RuntimeError as error:
        assert "concrete law failure" in str(error)
    else:
        raise AssertionError("failed law unexpectedly produced evidence")

    assert law_calls == 1
    assert not output.exists()


def test_law_contract_rejects_hash_rebound_to_the_wrong_test_owner() -> None:
    report = deterministic_law_report_fixture(REVISION)
    tampered = deepcopy(report)
    first = tampered["results"][0]
    first["evidence"]["command"][-2] = "tests/unit/runtime/test_unrelated.py"
    first["evidence_sha256"] = canonical_sha256(first["evidence"])

    with pytest.raises(RuntimeError, match="does not match its test owner"):
        require_deterministic_law_report(
            tampered,
            implementation_revision=REVISION,
            candidate_bundle_version=CANDIDATE_BUNDLE_VERSION,
            development_evidence_plan_version=DEVELOPMENT_EVIDENCE_PLAN_VERSION,
            development_author_segment_version=AUTHOR_SEGMENT_VERSION,
            mechanism_evidence_version=MECHANISM_EVIDENCE_VERSION,
        )


def test_law_owner_contains_no_semantic_parser_or_retry_loop() -> None:
    prohibited = {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    for name in (
        "greenfield_semantic_deterministic_laws.py",
        "greenfield_semantic_deterministic_law_contract.py",
    ):
        path = SCRIPTS_ROOT / name
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports = {
            alias.name.split(".", 1)[0]
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
            for alias in (
                node.names
                if isinstance(node, ast.Import)
                else [ast.alias(name=node.module or "")]
            )
        }
        assert imports.isdisjoint(prohibited)

    path = SCRIPTS_ROOT / "greenfield_semantic_deterministic_laws.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    assert not any(isinstance(node, ast.While) for node in ast.walk(tree))
    loops = [node for node in ast.walk(tree) if isinstance(node, ast.For)]
    assert len(loops) == 1
    assert isinstance(loops[0].target, ast.Name)
    assert loops[0].target.id == "law_id"
    assert isinstance(loops[0].iter, ast.Name)
    assert loops[0].iter.id == "REQUIRED_DETERMINISTIC_LAW_IDS"
    assert not any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and "retry" in node.name.lower()
        for node in ast.walk(tree)
    )


def _result(
    command: list[str],
    *,
    returncode: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(command, returncode, stdout, stderr)
