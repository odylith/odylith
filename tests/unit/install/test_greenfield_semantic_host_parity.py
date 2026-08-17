from __future__ import annotations

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence import greenfield_pending_transaction_store
from scripts.release import greenfield_semantic_host_parity as host_parity
from tests.unit.runtime.greenfield_proposal_fixtures import compiled_graph_transaction


def _sha(character: str) -> str:
    return hashlib.sha256(character.encode("utf-8")).hexdigest()


def _candidate(host: str, outcome: str, seed: str) -> dict[str, object]:
    return {
        "host_profile": host,
        "outcome": outcome,
        "candidate_sha256": _sha(seed),
        "mechanism_evidence_sha256": _sha(chr(ord(seed) + 1)),
        "semantic_artifact_sha256": _sha(chr(ord(seed) + 2)),
    }


def _case(case_id: str, outcome: str, seed: str) -> dict[str, object]:
    ordinal = int(case_id.rsplit("-", 1)[-1])
    return {
        "case_id": case_id,
        "prompt_sha256": _sha(seed),
        "assignment_sha256": _sha(chr(ord(seed) + 1)),
        "codex": _candidate("codex", outcome, chr(ord(seed) + 2)),
        "claude": _candidate("claude", outcome, chr(ord(seed) + 5)),
        "independent_adjudication": {
            "review_a_sha256": _sha(chr(ord(seed) + 8)),
            "review_b_sha256": _sha(chr(ord(seed) + 9)),
            "adjudication_sha256": _sha(chr(ord(seed) + 10)),
            "review_a_run_nonce": f"review-a-{ordinal}",
            "review_b_run_nonce": f"review-b-{ordinal}",
            "adjudicator_run_nonce": f"adjudicator-{ordinal}",
            "meaning_equivalent": True,
            "consumer_utility_equivalent": True,
            "material_decision_equivalent": True,
            "unresolved_p0_count": 0,
            "unresolved_p1_count": 0,
        },
    }


def _semantic_work() -> dict[str, object]:
    cases = [
        _case("parity-1", "commit", "1"),
        _case("parity-2", "clarify", "2"),
    ]
    return {
        "version": host_parity.HOST_PARITY_WORK_VERSION,
        "assignment_manifest_sha256": _sha("a"),
        "authoring_contract_sha256": _sha("b"),
        "evaluation_contract_sha256": _sha("c"),
        "required_case_ids": [row["case_id"] for row in cases],
        "cases": cases,
    }


def _callback_proof() -> dict[str, object]:
    host = {
        "status": "CLOSED",
        "decision_sha256": _sha("d"),
        "receipt_sha256": _sha("e"),
    }
    return {
        "version": host_parity.HOST_CALLBACK_PROOF_VERSION,
        "callback_version": "odylith.greenfield.host-confirmation-callback.v1",
        "transaction_hash": _sha("f"),
        "write_set_hash": _sha("0"),
        "codex": dict(host),
        "claude": dict(host),
    }


def test_host_parity_report_requires_independently_adjudicated_same_case_evidence() -> None:
    report = host_parity.compile_host_parity_report(_semantic_work(), _callback_proof())

    assert report["version"] == host_parity.HOST_PARITY_REPORT_VERSION
    assert report["status"] == "passed"
    assert report["passed"] is True
    assert report["semantic_parity"]["case_count"] == 2
    assert report["semantic_parity"]["commit_count"] == 1
    assert report["semantic_parity"]["clarify_count"] == 1
    assert report["callback_parity"]["passed"] is True


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda work: work["cases"][0]["claude"].update(outcome="clarify"),
            "different material outcomes",
        ),
        (
            lambda work: work["cases"][0]["independent_adjudication"].update(
                consumer_utility_equivalent=False
            ),
            "consumer_utility_equivalent",
        ),
        (
            lambda work: work["cases"][1]["independent_adjudication"].update(
                review_a_run_nonce="review-a-1"
            ),
            "reused or invalid",
        ),
        (
            lambda work: work["cases"][0]["independent_adjudication"].update(
                unresolved_p1_count=1
            ),
            "unresolved priority findings",
        ),
    ],
)
def test_host_parity_report_fails_closed_on_semantic_or_review_drift(mutate, message: str) -> None:
    work = deepcopy(_semantic_work())
    mutate(work)

    with pytest.raises(RuntimeError, match=message):
        host_parity.compile_host_parity_report(work, _callback_proof())


def test_callback_parity_commits_and_replays_one_sealed_hash_through_both_hosts(
    tmp_path: Path,
) -> None:
    compiled = compiled_graph_transaction(tmp_path)
    greenfield_pending_transaction_store.stage_pending_transaction(
        repo_root=tmp_path,
        transaction=compiled,
    )
    (tmp_path / ".odylith-host-parity-rehearsal.v1.json").write_text(
        json.dumps(
            {
                "version": host_parity.HOST_PARITY_REHEARSAL_VERSION,
                "transaction_hash": compiled.transaction_hash,
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    proof = host_parity.run_callback_parity(
        repo_root=tmp_path,
        transaction_hash=compiled.transaction_hash,
    )

    assert proof["status"] == "passed"
    assert proof["passed"] is True
    assert proof["transaction_hash"] == compiled.transaction_hash
    assert proof["hosts"]["codex"] == proof["hosts"]["claude"]
    assert proof["hosts"]["codex"]["status"] == "CLOSED"


def test_callback_parity_rejects_a_non_disposable_repository(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="rehearsal marker"):
        host_parity.run_callback_parity(
            repo_root=tmp_path,
            transaction_hash=_sha("f"),
        )


def test_host_parity_owner_has_no_parser_or_fuzzy_authority() -> None:
    source_path = Path(host_parity.__file__)
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection(
        {"re", "regex", "difflib", "rapidfuzz", "nltk", "spacy", "tokenize"}
    )
