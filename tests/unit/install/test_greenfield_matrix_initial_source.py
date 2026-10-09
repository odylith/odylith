"""Initial document custody through the release harness, without lifecycle EDIT."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT

if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import greenfield_preconfirm_matrix as matrix
from greenfield_matrix_statistics import expected_case_evidence_format, expected_case_source_complexity
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase, case_evidence
from odylith.runtime.domain_intelligence.greenfield_model_intent_materialization import prepare_model_authoring_evidence
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import combined_prompt_evidence_source
from odylith.runtime.domain_intelligence import greenfield_proposals_cli


def _case() -> GreenfieldMatrixCase:
    return GreenfieldMatrixCase(
        name="reviewed initial evidence",
        prompt="  A reviewer records a café decision.\r\nPreserve the cited résumé.  ",
        confirmed_intent_markdown="\nReviewed first path: record → inspect → retain the decision.\n",
        required_terms=("decision",),
    )


def test_initial_source_preserves_both_documents_and_truthful_source_format() -> None:
    case = _case()
    original_identity = case_evidence(case)
    initial = case.initial_prompt
    assert initial == case.prompt.strip() + "\n\n# Operator edit evidence\n\n" + case.confirmed_intent_markdown.strip()
    prepared = prepare_model_authoring_evidence(prompt=initial)

    assert prepared.prompt == initial
    assert prepared.edit_evidence == ""
    assert prepared.source_format == "operator_prompt"
    assert prepared.source_document_count == 1
    assert expected_case_evidence_format(case) == prepared.source_format
    assert expected_case_source_complexity(case) == {
        "evidence_bytes": len(prepared.evidence_source.encode("utf-8")), "documents": 1,
    }
    assert case.initial_input_streams == {
        "input.prompt": initial, "input.initial-request": case.prompt,
        "input.confirmed-intent": case.confirmed_intent_markdown, "input.edit-evidence": "",
    }
    assert case_evidence(case) == original_identity
    assert original_identity["prompt_sha256"] == hashlib.sha256(case.prompt.encode()).hexdigest()


@pytest.mark.parametrize("prompt,confirmed", (
    ("Initial evidence.", "Reviewed first path."),
    ("  Café résumé → décision.\r\n ", "\n  Review preserves εvidence.\r\n "),
    ("\nFirst line.\n\nSecond line.\n", "\n# Reviewed source\n\nRetain all lines.\n"),
    ("\nPlain request.\r\n", ""),
))
def test_initial_normalization_retains_exact_frozen_model_source_frame(prompt: str, confirmed: str) -> None:
    case = GreenfieldMatrixCase(name="initial source", prompt=prompt, confirmed_intent_markdown=confirmed, required_terms=())
    assert combined_prompt_evidence_source(prompt=case.initial_prompt, edit_evidence="") == combined_prompt_evidence_source(
        prompt=prompt, edit_evidence=confirmed,
    )


def test_plain_initial_prompt_is_byte_preserving() -> None:
    case = GreenfieldMatrixCase(name="plain", prompt="\nUnicode é → evidence\r\n", required_terms=())
    assert case.initial_prompt == case.prompt


def test_initial_documents_reach_candidate_flow_and_retention_without_edit_authority(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    launcher = tmp_path / ".odylith/bin/odylith"
    launcher.parent.mkdir(parents=True)
    launcher.write_text("")
    calls = []

    class ReachedInitialBoundary(Exception):
        pass

    def invoke(**kwargs):
        calls.append(kwargs)
        argv = matrix._greenfield_propose_arguments(prompt=kwargs["prompt"], edit_evidence=kwargs["edit_evidence"])
        assert argv[argv.index("--prompt") + 1] == case.initial_prompt
        assert "--edit" not in argv and "--edit-evidence" not in argv
        return SimpleNamespace(returncode=0)

    def journey(**kwargs):
        assert kwargs["raw_streams"] == case.initial_input_streams
        assert kwargs["invoke_propose"](315).returncode == 0
        raise ReachedInitialBoundary

    monkeypatch.setattr(matrix, "_local_release_env", lambda **kwargs: {})
    monkeypatch.setattr(matrix, "_run_host_candidate_propose", invoke)
    monkeypatch.setattr(matrix, "run_compiled_greenfield_journey", journey)
    monkeypatch.setattr(matrix, "_run", lambda **kwargs: pytest.fail("Initial boundary test cannot execute commands"))
    with pytest.raises(ReachedInitialBoundary):
        matrix._run_case(
            case=case, repo_root=tmp_path, install_script=tmp_path / "unused",
            base_url="unused", version="0.1.15", skip_install=True,
        )
    assert len(calls) == 1
    assert calls[0]["prompt"] == case.initial_input_streams["input.prompt"]
    assert calls[0]["edit_evidence"] == ""


def test_retention_keeps_invocation_bytes_and_original_document_bytes(tmp_path: Path, monkeypatch) -> None:
    case = _case()
    observed = {}
    monkeypatch.setattr(matrix, "record_retained_case_text", lambda retained, path, value: observed.setdefault(path, value))
    monkeypatch.setattr(matrix, "record_retained_case_json", lambda *args, **kwargs: None)
    matrix._record_retained_execution(
        retained_case=SimpleNamespace(staging_root=tmp_path), proposal_payload={},
        dry_run_receipt={}, create_payload={}, raw_streams=case.initial_input_streams,
    )
    for name, value in case.initial_input_streams.items():
        assert observed[f"commands/{name}"] == value


def test_real_edit_flag_and_prior_custody_refusal_remain_intact(tmp_path: Path) -> None:
    correction = "Change the review policy."
    argv = matrix._greenfield_propose_arguments(prompt=_case().prompt, edit_evidence=correction)
    assert argv[argv.index("--edit") + 1] == correction
    with pytest.raises(ValueError, match="prior transaction hash"):
        greenfield_proposals_cli._edit_transaction_from_args(
            argparse.Namespace(transaction_hash=None, completion_receipt=None),
            repo_root=tmp_path, correction=correction,
        )
    assert list(tmp_path.iterdir()) == []
