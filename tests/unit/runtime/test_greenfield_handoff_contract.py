"""Focused structural proof for the authored Greenfield handoff contract."""

from __future__ import annotations

import inspect
from copy import deepcopy

import pytest

from odylith.runtime.domain_intelligence import greenfield_handoff_contract
from odylith.runtime.domain_intelligence.greenfield_handoff_contract import (
    CODING_READINESS_SCHEMA_VERSION,
    build_coding_readiness_contract,
    coding_readiness_contract_issues,
    render_coding_readiness_gates,
)


def _readiness_contract() -> dict[str, object]:
    return build_coding_readiness_contract(
        workstream_id="b-042",
        workstream_title="Dock Console Slice",
        release_selector="0.0.1",
        accepted_first_path=(
            "Dock attendant Ivo opens **`berth-α`** and records the reviewed placement."
        ),
        proof_boundary="Reviewer sees the signed café receipt",
        evidence_requirements=("Keep `audit.md`", "**Retain receipt**"),
        operational_constraints=("Latency ≤ 60 s",),
        non_goals=("Do **not** schedule vessels",),
    )


def test_coding_readiness_contract_preserves_exact_unicode_markdown_and_whitespace() -> None:
    first_path = (
        "  Mārtiņš opens **`berth-α`**\n"
        "\tand records the reviewed café placement.  "
    )
    proof_boundary = "\tReviewer sees **the signed receipt**.\n"
    evidence = (
        "  Keep `audit.md` byte-exact.  ",
        "\nPreserve **résumé** evidence.\t",
    )
    constraints = ("\tLatency ≤ 60 s.\n",)
    non_goals = ("  Do **not** schedule vessels.  ",)

    contract = build_coding_readiness_contract(
        workstream_id="B-042",
        workstream_title="Dock Console Slice",
        release_selector="0.0.1",
        accepted_first_path=first_path,
        proof_boundary=proof_boundary,
        evidence_requirements=evidence,
        operational_constraints=constraints,
        non_goals=non_goals,
    )

    assert contract["source_facts"] == {
        "accepted_first_path": first_path,
        "proof_boundary": proof_boundary,
        "evidence_requirements": evidence,
        "operational_constraints": constraints,
        "non_goals": non_goals,
    }


def test_coding_readiness_contract_has_exact_gate_policies_and_deterministic_rendering() -> None:
    contract = _readiness_contract()

    assert contract["schema_version"] == CODING_READINESS_SCHEMA_VERSION
    assert contract["gates"] == [
        {
            "gate_id": "implementation_environment",
            "policy": "decide_before_source_plan",
        },
        {"gate_id": "source_boundary", "policy": "bind_before_source_edit"},
        {"gate_id": "scope_boundary", "policy": "preserve_exact_source_facts"},
        {"gate_id": "proof_boundary", "policy": "prove_before_governance_refresh"},
    ]
    expected = [
        (
            "Choose and record the implementation language, runtime assumptions, dependency policy, "
            "and test toolchain before source planning."
        ),
        (
            "Bind B-042 Dock Console Slice to an explicit source boundary and target files while "
            "preserving the accepted first path exactly: Dock attendant Ivo opens "
            "**`berth-α`** and records the reviewed placement."
        ),
        (
            "Preserve the authored operating and scope boundary during planning and source edits: "
            "Latency ≤ 60 s; Do **not** schedule vessels"
        ),
        (
            "Require validation evidence before governed records refresh.\n"
            "Authored proof boundary:\n"
            "Reviewer sees the signed café receipt\n"
            "Evidence requirements:\n"
            "Keep `audit.md`; **Retain receipt**"
        ),
    ]

    assert coding_readiness_contract_issues(
        contract,
        expected_workstream_id="B-042",
    ) == ()
    assert render_coding_readiness_gates(contract) == expected
    assert render_coding_readiness_gates(contract) == expected


@pytest.mark.parametrize("terminal", (".", "!", "?"))
def test_coding_readiness_renderer_preserves_authored_terminal_punctuation_once(
    terminal: str,
) -> None:
    proof_boundary = f"Reviewer sees the signed café receipt{terminal}"
    contract = build_coding_readiness_contract(
        workstream_id="B-042",
        workstream_title="Dock Console Slice",
        release_selector="0.0.1",
        accepted_first_path="Dock attendant Ivo records the reviewed placement.",
        proof_boundary=proof_boundary,
    )

    assert contract["source_facts"]["proof_boundary"] == proof_boundary
    proof_gate = render_coding_readiness_gates(contract)[-1]
    assert (
        f"Authored proof boundary:\n{proof_boundary}\nEvidence requirements:"
        in proof_gate
    )
    assert f"{proof_boundary}." not in proof_gate


def test_coding_readiness_contract_fails_closed_when_missing_or_mistyped() -> None:
    assert coding_readiness_contract_issues(
        None,
        expected_workstream_id="B-042",
    ) == ("operator next-steps preview is missing its typed coding-readiness contract",)

    wrong_schema = deepcopy(_readiness_contract())
    wrong_schema["schema_version"] = "odylith.greenfield.coding-readiness.invalid"
    assert "operator next-steps preview has an unsupported coding-readiness contract" in (
        coding_readiness_contract_issues(
            wrong_schema,
            expected_workstream_id="B-042",
        )
    )

    wrong_policy = deepcopy(_readiness_contract())
    wrong_policy["gates"][2]["policy"] = "guess_from_prompt_words"  # type: ignore[index]
    issues = coding_readiness_contract_issues(
        wrong_policy,
        expected_workstream_id="B-042",
    )
    assert "operator next-steps readiness does not carry the exact gate contract" in issues
    with pytest.raises(ValueError, match="exact gate contract"):
        render_coding_readiness_gates(wrong_policy)


def test_coding_readiness_contract_rejects_workstream_drift() -> None:
    contract = _readiness_contract()

    assert coding_readiness_contract_issues(
        contract,
        expected_workstream_id="B-999",
    ) == (
        "operator next-steps readiness drifted from the first implementation workstream",
    )


def test_handoff_contract_owner_has_no_semantic_regex_or_vocabulary_machinery() -> None:
    source = inspect.getsource(greenfield_handoff_contract).casefold()

    for banned in (
        "import re",
        "re.compile",
        "re.search",
        "regex",
        "normalize_token",
        "tokenize",
        "stemmer",
        "keyword",
        "semantic_overlap",
        "casefold(",
    ):
        assert banned not in source
