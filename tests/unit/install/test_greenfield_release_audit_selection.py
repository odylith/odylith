from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPTS_ROOT = REPO_ROOT / "scripts" / "release"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_release_corpus as corpus  # noqa: E402
from greenfield_matrix_case_file import load_case_file  # noqa: E402
from greenfield_matrix_corpus_provenance import evaluate_release_corpus  # noqa: E402
from greenfield_matrix_corpus_provenance import load_release_audit_file  # noqa: E402


FIXTURE_ROOT = REPO_ROOT / "tests/fixtures/greenfield-release-corpus"
PARENT = FIXTURE_ROOT / "greenfield-release-source-provenanced.v4.json"
SELECTION = FIXTURE_ROOT / "live-subsets/greenfield-release-public-operating-envelope.v2.json"
AUDIT = FIXTURE_ROOT / "audit-evidence-v16/greenfield-release-audit.v9.json"
SOURCE_VERIFICATIONS = (
    FIXTURE_ROOT
    / "audit-source-verifications-v9-2026-09-27/source-verifications.v2.json"
)


def test_audit_plan_binds_parent_truth_and_exact_operating_envelope_selection(
    tmp_path: Path,
) -> None:
    output = tmp_path / "audit-plan.json"

    plan = corpus.build_release_audit_request_plan(
        source_case_file=PARENT,
        audit_selection_file=SELECTION,
        output_json=output,
        repo_root=REPO_ROOT,
        audit_count=40,
    )

    assert plan["source_case_file"] == PARENT.relative_to(REPO_ROOT).as_posix()
    assert plan["audit_selection_file"] == SELECTION.relative_to(REPO_ROOT).as_posix()
    assert plan["audit_selection_file_sha256"] == corpus.sha256_file(SELECTION)
    assert [row["case_id"] for row in plan["requests"]] == [
        case.case_id for case in load_case_file(SELECTION)
    ]
    assert json.loads(output.read_text(encoding="utf-8")) == plan


def test_repo_operating_envelope_audit_validates_against_its_parent_corpus() -> None:
    cases = load_case_file(PARENT)
    audits = load_release_audit_file(AUDIT, repo_root=REPO_ROOT)

    evaluation = evaluate_release_corpus(cases, audits, repo_root=REPO_ROOT)

    assert evaluation.passed, evaluation.issues
    assert evaluation.summary["case_count"] == 200
    assert evaluation.summary["audit_count"] == 40


def test_repo_source_verification_rebind_retains_its_immutable_predecessor() -> None:
    manifest = json.loads(SOURCE_VERIFICATIONS.read_text(encoding="utf-8"))
    predecessor = REPO_ROOT / str(manifest["rebound_from"])

    assert predecessor.resolve() != SOURCE_VERIFICATIONS.resolve()
    assert predecessor.is_file()
    assert corpus.sha256_file(predecessor) == manifest["rebound_from_sha256"]


@pytest.mark.parametrize("damage", ("claim", "parent", "case"))
def test_audit_plan_rejects_unbound_or_drifted_explicit_selection(
    tmp_path: Path,
    damage: str,
) -> None:
    parent = tmp_path / "parent.json"
    selection = tmp_path / "selection.json"
    parent.write_bytes(PARENT.read_bytes())
    payload = json.loads(SELECTION.read_text(encoding="utf-8"))
    payload["parent_corpus"] = "parent.json"
    if damage == "claim":
        payload["claim_class"] = "source-provenanced-discovery"
    elif damage == "parent":
        payload["parent_corpus"] = "other.json"
    else:
        payload["cases"][0]["prompt"] += " Drifted."
    selection.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="audit selection"):
        corpus.build_release_audit_request_plan(
            source_case_file=parent,
            audit_selection_file=selection,
            output_json=tmp_path / "audit-plan.json",
            repo_root=tmp_path,
            audit_count=40,
        )

    assert not (tmp_path / "audit-plan.json").exists()
