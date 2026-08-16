from __future__ import annotations

import json
import subprocess
import sys

from tests.greenfield_matrix_campaign_test_support import SCRIPTS_ROOT


if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from greenfield_matrix_case_file import load_case_file
from greenfield_matrix_case_file import required_term_present
from greenfield_matrix_corpus_provenance import GreenfieldCaseProvenance
from greenfield_matrix_metamorphic import evaluate_metamorphic_outputs
from greenfield_matrix_terminal_reporting import upstream_stop_quality_verdict
from greenfield_matrix_terminal_reporting import upstream_stop_stage_evidence
from greenfield_preconfirm_matrix_cases import GreenfieldMatrixCase
from tests.unit.install.test_greenfield_matrix_metamorphic import _result
from tests.unit.install.test_greenfield_preconfirm_matrix import _clarification_payload
from tests.unit.install.test_greenfield_preconfirm_matrix import _full_counts
from tests.unit.install.test_greenfield_preconfirm_matrix import _module
from tests.unit.install.test_greenfield_preconfirm_matrix import _proposed_transaction_payload
from tests.unit.install.test_greenfield_preconfirm_matrix import _substantive_package
from tests.unit.install.test_greenfield_preconfirm_matrix import _write_compiled_transaction


def test_required_term_matching_accepts_bounded_inflection_without_accepting_an_omission() -> None:
    generated = "A reviewer chooses one candidate record and accepts it."

    assert required_term_present(generated, "candidate to accepted") is True
    assert required_term_present("The candidate was accepted.", "candidate accepted") is True
    assert required_term_present("The candidate was not accepted.", "candidate accepted") is False
    assert required_term_present("The record is marked claimed.", "claim receipt") is False
    assert required_term_present("A claim receipt remains visible.", "claim receipt") is True


def test_untrusted_file_header_does_not_self_attest_synthetic_provenance(tmp_path) -> None:  # noqa: ANN001
    case_file = tmp_path / "sealed-cases.json"
    case_file.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout.v1",
                "claim_class": "blinded-independent-synthetic-holdout",
                "authoring_method": "independent deterministic authoring",
                "cases": [
                    _case_row("sealed-a", "A reviewer accepts one candidate record.", "direct"),
                    _case_row("sealed-b", "One candidate record is accepted by a reviewer.", "reordered"),
                ],
            }
        ),
        encoding="utf-8",
    )

    cases = load_case_file(case_file)

    assert {case.provenance.corpus_tier for case in cases} == {"synthetic_regression"}
    assert all(case.provenance.derivation_method == "" for case in cases)
    assert all(case.provenance.derivation_author == "" for case in cases)
    assert all(case.provenance.derived_prompt_sha256 == "" for case in cases)
    assert evaluate_metamorphic_outputs(
        cases=cases,
        results=tuple(_result(case) for case in cases),
    )["status"] == "failed"


def test_file_claim_does_not_override_explicit_source_provenance(tmp_path) -> None:  # noqa: ANN001
    case_file = tmp_path / "mixed-cases.json"
    source = GreenfieldCaseProvenance(
        corpus_tier="source_provenanced",
        source_id="source-1",
        source_artifact_sha256="a" * 64,
    )
    row = _case_row("source-a", "A reviewer accepts one source record.", "direct")
    row["provenance"] = {
        "corpus_tier": source.corpus_tier,
        "source_id": source.source_id,
        "source_artifact_sha256": source.source_artifact_sha256,
    }
    case_file.write_text(
        json.dumps(
            {
                "version": "odylith.greenfield.final-holdout.v1",
                "claim_class": "blinded-independent-synthetic-holdout",
                "authoring_method": "independent deterministic authoring",
                "cases": [row],
            }
        ),
        encoding="utf-8",
    )

    case = load_case_file(case_file)[0]

    assert case.provenance.corpus_tier == "source_provenanced"
    assert case.provenance.source_id == "source-1"


def test_upstream_stop_reports_downstream_checks_as_not_applicable() -> None:
    verdict = upstream_stop_quality_verdict(
        receipt_status="proposal_failed",
        create_payload={
            "commit_manifest": {
                "issues": [{"message": "accepted semantic path did not compile"}],
            }
        },
        failure_detail="",
        score_dimensions=("completion", "semantic_manifest", "browser_surface_proof"),
    )
    stages = upstream_stop_stage_evidence(
        receipt_status="proposal_failed",
        primary_issue=verdict.issues[0],
    )

    assert verdict.issues == (
        "pre-confirm compilation stopped: accepted semantic path did not compile",
    )
    assert verdict.scores == {
        "completion": -1,
        "semantic_manifest": 0,
        "browser_surface_proof": -1,
    }
    assert stages["stages"]["preconfirm_compilation"]["status"] == "failed"
    assert {
        row["status"]
        for name, row in stages["stages"].items()
        if name != "preconfirm_compilation"
    } == {"not_applicable"}


def test_unexpected_clarification_integration_reports_only_the_upstream_stop(
    monkeypatch,
    tmp_path,
) -> None:
    module = _module()
    commands: list[list[str]] = []

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        commands.append(list(command))
        if "propose" in command:
            return subprocess.CompletedProcess(command, 0, json.dumps(_clarification_payload()), "")
        return subprocess.CompletedProcess(command, 0, "", "")

    monkeypatch.setattr(module, "_run", fake_run)
    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="unannotated ambiguity",
            prompt="Create a product with several possible operating paths.",
            required_terms=("product",),
        ),
        repo_root=tmp_path / "transaction-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.quality.issues == (
        "unexpected material clarification stopped pre-confirm compilation: "
        "What is the first complete task the product should help a person finish, and what result should they see?",
    )
    assert result.quality.score_basis == "upstream_preconfirm_stop"
    assert result.evidence["confirmation_contract"]["status"] == "not_applicable"
    stages = result.evidence["evaluation_stages"]["stages"]
    assert stages["preconfirm_compilation"]["status"] == "failed"
    assert stages["transaction_commit"]["status"] == "not_applicable"
    assert stages["generated_artifact_readback"]["status"] == "not_applicable"
    assert stages["browser_surface_proof"]["status"] == "not_applicable"
    assert not any(command[1:3] == ["greenfield", "create"] for command in commands)


def test_compiled_receipt_with_failed_create_remains_an_attempted_transaction(
    monkeypatch,
    tmp_path,
) -> None:
    module = _module()

    def fake_run(*, cwd, env, command, timeout):  # noqa: ANN001
        if "propose" in command:
            proposal = _proposed_transaction_payload()
            _write_compiled_transaction(cwd, proposal)
            return subprocess.CompletedProcess(command, 0, json.dumps(proposal), "")
        if "create" in command:
            return subprocess.CompletedProcess(command, 2, "", "commit-only create failed")
        return subprocess.CompletedProcess(command, 0, "", "")

    def failed_quality(**kwargs):  # noqa: ANN003
        assert kwargs["create_returncode"] == 2
        return module.GreenfieldQualityVerdict(
            passed=False,
            issues=("commit-only create exited with code 2",),
            lenses={
                lens: False
                for lens in ("product_manager", "architect", "engineer", "domain_expert")
            },
            scores={dimension: 0 for dimension in module.QUALITY_SCORE_DIMENSIONS},
            score=0,
            score_explanation=("the commit-ready transaction was attempted and failed",),
        )

    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "collect_artifact_package", lambda **_kwargs: _substantive_package())
    monkeypatch.setattr(module, "collect_artifact_counts", lambda **_kwargs: _full_counts(module))
    monkeypatch.setattr(module, "rendered_surface_health_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "post_confirm_navigation_issues", lambda **_kwargs: ())
    monkeypatch.setattr(module, "build_quality_verdict", failed_quality)

    result = module._run_case(  # noqa: SLF001
        case=module.GreenfieldMatrixCase(
            name="failed commit attempt",
            prompt="Create a review workspace for one governed record.",
            required_terms=("review", "record"),
        ),
        repo_root=tmp_path / "transaction-repo",
        install_script=tmp_path / "install.sh",
        base_url="http://127.0.0.1:8123",
        version="0.1.15",
    )

    assert result.status == "failed"
    assert result.create_returncode == 2
    assert result.quality.score_basis == "release"
    assert result.evidence["preconfirm_dry_run"]["status"] == "compiled"
    assert result.evidence["confirmation_contract"]["status"] == "passed"
    assert "evaluation_stages" not in result.evidence
    assert -1 not in result.quality.scores.values()


def _case_row(case_id: str, prompt: str, transform: str) -> dict[str, object]:
    return {
        "case_id": case_id,
        "name": case_id,
        "prompt": prompt,
        "required_terms": ["reviewer", "record"],
        "leakage_terms": ["source record" if "source" in prompt else "candidate record"],
        "metamorphic_group": "sealed-pair",
        "metamorphic_transform": transform,
    }
