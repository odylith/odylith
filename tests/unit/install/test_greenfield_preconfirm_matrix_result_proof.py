from __future__ import annotations

import time
from dataclasses import replace
from pathlib import Path

import pytest

from odylith.runtime.domain_intelligence.greenfield_model_profile_contract import (
    DEEP_PROFILE_ID,
)
from tests.unit.install.test_greenfield_preconfirm_matrix_proof_scope import (
    _module,
    _passing_clarification_profile_result,
    _passing_profile_result,
    _stage_observation,
    _write,
)


def test_temp_cleanup_proof_finds_leftover_files_and_symlinks(tmp_path: Path) -> None:
    module = _module()
    leftover_file = tmp_path / "odylith-greenfield-matrix-leftover-file"
    leftover_file.write_text("stale temp payload", encoding="utf-8")
    leftover_target = tmp_path / "target"
    leftover_target.mkdir()
    leftover_link = tmp_path / "odylith-greenfield-unavailable-leftover-link"
    leftover_link.symlink_to(leftover_target, target_is_directory=True)

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover_file) in proof["remaining_paths"]
    assert str(leftover_link) in proof["remaining_paths"]


def test_temp_cleanup_proof_finds_installed_recovery_leftovers(tmp_path: Path) -> None:
    module = _module()
    leftover = tmp_path / "odylith-greenfield-commit-recovery-leftover"
    leftover.mkdir()

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover) in proof["remaining_paths"]


def test_temp_cleanup_proof_finds_unavailable_provider_leftovers(tmp_path: Path) -> None:
    module = _module()
    leftover = tmp_path / "odylith-greenfield-unavailable-leftover"
    leftover.mkdir()

    proof = module.temp_cleanup_proof(tmp_path)

    assert proof["status"] == "failed"
    assert str(leftover) in proof["remaining_paths"]


def test_model_profile_release_proof_requires_astra_and_a_separate_luna_control() -> None:
    module = _module()
    standard_id = module.model_profile_id_for_repair_tier("standard")
    results = (
        _passing_profile_result(module, standard_id, 89.9),
    )

    positives_only = module.model_profile_release_proof(results, require_complete=True)
    assert positives_only["status"] == "failed"
    assert positives_only["lower_capability_scope"]["status"] == "unproven"
    assert any("clarification/no-write case" in issue for issue in positives_only["issues"])
    breached = replace(
        results[0],
        proposal_seconds=module.get_greenfield_model_profile(
            standard_id
        ).operational_timeout_seconds,
    )
    assert module.model_profile_release_proof(
        (breached,), require_complete=False,
    )["status"] == "failed"


def test_model_profile_release_proof_rejects_stale_runtime_reviewer_fields() -> None:
    module = _module()
    profile_id = module.model_profile_id_for_repair_tier("standard")
    results = (
        _passing_profile_result(module, profile_id, 20.0),
        _passing_clarification_profile_result(module, profile_id, 20.0),
    )
    clarification = results[1]
    evidence = dict(clarification.evidence)
    profile_evidence = dict(evidence["model_profile"])
    profile_evidence["observed"] = {
        **profile_evidence["observed"],
        "candidate_" + "review": {"status": "admitted"},
    }
    evidence["model_profile"] = profile_evidence

    proof = module.model_profile_release_proof(
        (results[0], replace(clarification, evidence=evidence)),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 1
    assert proof["profiles"][profile_id]["clarification_no_write_control_count"] == 0


def test_model_profile_release_proof_reports_missing_lower_profile_as_unproven() -> None:
    module = _module()
    results = (
        _passing_profile_result(
            module, module.model_profile_id_for_repair_tier("standard"), 20.0,
        ),
    )

    proof = module.model_profile_release_proof(results, require_complete=False)

    assert proof["status"] == "passed"
    assert proof["coverage_status"] == "incomplete"
    assert proof["lower_capability_scope"] == {
        "status": "unproven",
        "observed_profiles": [],
        "role": "authority_gate",
        "requirement": "source_bound_clarification_no_write_only",
    }
    assert module.model_profile_release_proof(results, require_complete=True)["status"] == "failed"


def test_model_profile_release_proof_rejects_sol_as_an_unsupported_diagnostic() -> None:
    module = _module()
    diagnostic = _passing_profile_result(module, DEEP_PROFILE_ID, 80.0)

    discovery = module.model_profile_release_proof((diagnostic,), require_complete=False)

    assert discovery["status"] == "failed"
    assert DEEP_PROFILE_ID not in discovery["profiles"]
    assert "diagnostics" not in discovery
    assert any("unsupported diagnostic" in issue for issue in discovery["issues"])
    assert discovery["profiles"][module.STANDARD_PROFILE_ID]["committed_positive_case_count"] == 0

    release = module.model_profile_release_proof((diagnostic,), require_complete=True)

    assert release["status"] == "failed"
    assert any("unsupported diagnostic" in issue for issue in release["issues"])
    assert any("committed positive case" in issue for issue in release["issues"])


@pytest.mark.parametrize(
    "mutation",
    ["missing", "host_model", "host_count", "post_receipt_call", "outcome"],
)
def test_model_profile_aggregate_rechecks_single_authority_despite_passed_label(
    mutation: str,
) -> None:
    module = _module()
    profile_id = module.model_profile_id_for_repair_tier("standard")
    result = _passing_profile_result(module, profile_id, 20.0)
    evidence = dict(result.evidence)
    profile_evidence = dict(evidence["model_profile"])
    stages = _stage_observation(profile_id)
    if mutation == "missing":
        stages = {}
    elif mutation == "host_model":
        stages["host_request"]["model"] = "gpt-5.6-sol"
    elif mutation == "host_count":
        stages["host_invocations"] = 3
    elif mutation == "post_receipt_call":
        stages["post_receipt_provider_invocations"] = 1
    else:
        stages = _stage_observation(profile_id, clarification=True)
    profile_evidence["stage_observation"] = stages
    evidence["model_profile"] = profile_evidence

    proof = module.model_profile_release_proof(
        (replace(result, evidence=evidence),), require_complete=False,
    )

    assert profile_evidence["status"] == "passed"
    assert proof["status"] == "failed"
    assert proof["profiles"][profile_id]["committed_positive_case_count"] == 0


@pytest.mark.parametrize("tier", ["standard"])
def test_model_profile_release_proof_ignores_forged_lower_metadata_and_missing_provider(tier) -> None:
    module = _module()
    profile_id = module.model_profile_id_for_repair_tier(tier)
    forged = _passing_profile_result(module, profile_id, 20.0)
    evidence = dict(forged.evidence or {})
    evidence["model_profile"] = {**evidence["model_profile"], "lower_capability": True}

    forged_proof = module.model_profile_release_proof(
        (replace(forged, evidence=evidence),),
        require_complete=False,
    )
    assert forged_proof["status"] == "passed"
    assert forged_proof["coverage_status"] == "incomplete"
    assert forged_proof["lower_capability_scope"]["observed_profiles"] == []

    unavailable = replace(
        forged,
        evidence={
            **dict(forged.evidence or {}),
            "model_profile": {
                **dict(forged.evidence["model_profile"]),
                "profile_id": module.UNAVAILABLE_PROVIDER_PROFILE,
                "observed": {
                    **dict(forged.evidence["model_profile"]["observed"]),
                    "profile_id": module.UNAVAILABLE_PROVIDER_PROFILE,
                },
            },
        },
    )
    unavailable_proof = module.model_profile_release_proof(
        (unavailable,),
        require_complete=False,
    )
    assert unavailable_proof["status"] == "failed"
    assert unavailable_proof["lower_capability_scope"]["observed_profiles"] == []


def test_model_profile_release_proof_rejects_unbound_or_writeful_lower_control() -> None:
    module = _module()
    rescue_id = module.LOWER_CAPABILITY_CONTROL_PROFILES[0]
    control = _passing_clarification_profile_result(module, rescue_id, 20.0)
    evidence = dict(control.evidence or {})
    evidence["case"] = {**evidence["case"], "prompt_sha256": "not-source-bound"}
    evidence["no_write"] = {**evidence["no_write"], "write_attempts": ["open"]}

    proof = module.model_profile_release_proof(
        (replace(control, evidence=evidence),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert proof["lower_capability_scope"]["status"] == "unproven"
    assert any("source-bound no-write proof" in issue for issue in proof["issues"])


def test_model_profile_release_proof_rejects_elapsed_tier_relabeling() -> None:
    module = _module()
    standard_id = module.model_profile_id_for_repair_tier("standard")
    result = _passing_profile_result(module, standard_id, 30.0)
    evidence = dict(result.evidence or {})
    profile_evidence = dict(evidence["model_profile"])
    profile_evidence["stage_observation"]["model_profile_id"] = (
        module.LOWER_CAPABILITY_CONTROL_PROFILES[0]
    )
    evidence["model_profile"] = profile_evidence

    proof = module.model_profile_release_proof(
        (replace(result, evidence=evidence),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert any("gate/candidate call and zero-runtime-call proof" in issue for issue in proof["issues"])


def test_model_profile_release_proof_requires_a_passed_terminal_result() -> None:
    module = _module()
    result = _passing_profile_result(
        module,
        module.model_profile_id_for_repair_tier("standard"),
        18.0,
    )

    proof = module.model_profile_release_proof(
        (replace(result, status="failed"),),
        require_complete=False,
    )

    assert proof["status"] == "failed"
    assert any("gate/candidate call and zero-runtime-call proof" in issue for issue in proof["issues"])


def test_unavailable_provider_proof_requires_success_without_runtime_provider_use() -> None:
    module = _module()
    values = {
        "returncode": 0,
        "proposal_seconds": 1.0,
        "detail": "Greenfield model authoring is unavailable; no records were created.",
        "write_audit_active": True,
        "write_audit_error": "",
        "write_attempts": (),
        "subprocess_attempts": ("subprocess.Popen",),
        "changed_records": (),
        "staged_transaction_present": True,
    }

    assert module.unavailable_provider_proof_issues(**values) == ()
    assert module.unavailable_provider_proof_issues(**{**values, "returncode": 1})
    assert module.unavailable_provider_proof_issues(**{**values, "write_attempts": ("open",)})


def test_unavailable_provider_proof_admits_one_candidate_without_runtime_provider(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = _module()
    dist_dir = tmp_path / "dist"
    _write(dist_dir / "install.sh", "#!/bin/sh\nexit 0\n")
    host_argv = ("codex", "exec", "--model", "gpt-6-astra")
    servers: list[object] = []
    host_flows: list[object] = []
    proposals: list[dict[str, object]] = []

    class Server:
        shutdown_called = False
        close_called = False

        def shutdown(self) -> None:
            self.shutdown_called = True

        def server_close(self) -> None:
            self.close_called = True

    class Audit:
        pass_fds: tuple[int, ...] = ()

        def environment(self) -> dict[str, str]:
            return {"ODYLITH_GREENFIELD_WRITE_AUDIT_TEST": "active"}

        def command(self, **_kwargs) -> list[str]:
            return ["audit-python"]

        def finish(self):
            return module.SimpleNamespace(
                active=True,
                write_attempts=(),
                subprocess_attempts=("subprocess.Popen",),
                error="",
            )

    def serve_directory(_release_dir: Path):
        server = Server()
        servers.append(server)
        return server, "http://127.0.0.1:12345"

    def run_command(**_kwargs):
        return module.SimpleNamespace(returncode=0, stdout="", stderr="")

    def run_propose(**kwargs):
        proposals.append(kwargs)
        time.sleep(0.005)
        pending = kwargs["repo_root"] / ".odylith/runtime/greenfield/pending/proof.json"
        pending.parent.mkdir(parents=True, exist_ok=True)
        pending.write_text("{}\n", encoding="utf-8")
        return module.SimpleNamespace(
            returncode=0,
            stdout='{"mode":"product_create_transaction","transaction_file":"proof.json"}',
            stderr="",
        )

    def run_host_flow(flow):
        host_flows.append(flow)
        gate_path = flow.temp_parent / "authority-gate.json"
        gate_path.write_text('{"decision":"admit"}\n', encoding="utf-8")
        candidate_path = flow.temp_parent / "candidate.json"
        candidate_path.write_text('{"result":{"status":"authored"}}\n', encoding="utf-8")
        completed = flow.invoke_propose(candidate_path, gate_path, 90.0)
        assert completed.returncode == 0
        return completed

    monkeypatch.setattr(module, "_serve_directory", serve_directory)
    monkeypatch.setattr(module, "_local_release_env", lambda **_kwargs: {"PATH": "/trusted"})
    monkeypatch.setattr(module, "_run", run_command)
    monkeypatch.setattr(module, "begin_installed_write_audit", lambda **_kwargs: Audit())
    monkeypatch.setattr(module, "resolve_trusted_codex_executable", lambda **_kwargs: "/trusted/codex")
    monkeypatch.setattr(module, "_run_greenfield_propose", run_propose)
    monkeypatch.setattr(module, "run_host_candidate_flow", run_host_flow)

    proof = module.run_unavailable_provider_proof(
        dist_dir=dist_dir,
        version="0.0.0",
        temp_parent=tmp_path / "work",
        case=module.GreenfieldMatrixCase(
            name="provider negative control",
            prompt="Create one source-grounded product proposal.",
            required_terms=(),
        ),
        host_candidate_argv=host_argv,
    )

    assert proof["status"] == "passed"
    assert proof["returncode"] == 0
    assert proof["no_write"] == {
        "before_record_count": 0,
        "after_record_count": 1,
        "changed_records": [".odylith/runtime/greenfield/pending/proof.json"],
        "staged_transaction_present": True,
        "write_audit_active": True,
        "write_attempts": [],
        "subprocess_attempts": ["subprocess.Popen"],
        "write_audit_error": "",
    }
    assert len(host_flows) == 1
    assert host_flows[0].host_argv == host_argv
    assert host_flows[0].env["ODYLITH_GREENFIELD_MODEL_PROFILE"] == module.STANDARD_PROFILE_ID
    assert "ODYLITH_REASONING_CODEX_BIN" not in host_flows[0].env
    assert len(proposals) == 1
    assert proposals[0]["repair_tier"] == "standard"
    assert proposals[0]["candidate_file"]
    assert (
        proposals[0]["env"]["ODYLITH_GREENFIELD_MODEL_PROFILE"]
        == module.UNAVAILABLE_PROVIDER_PROFILE
    )
    assert proposals[0]["env"]["ODYLITH_REASONING_CODEX_BIN"] == "/usr/bin/false"
    assert proposals[0]["env"]["ODYLITH_REASONING_MODE"] == "disabled"
    assert servers[0].shutdown_called is True
    assert servers[0].close_called is True


def test_commit_manifest_summary_uses_last_repair_patchset_for_clean_final_pass() -> None:
    module = _module()

    summary = module.commit_manifest_summary(
        {
            "status": "passed",
            "validation_status": "passed",
            "requested_repair_tier": "auto",
            "repair_tier": "rescue",
            "rescue_activated": True,
            "passes": 2,
            "issue_count": 0,
            "repaired_issue_codes": ["semantic_alignment"],
            "create_elapsed_seconds": 0.125,
            "write_transaction": {
                "status": "committed",
                "commit_only": True,
                "prewrite_clean_before_commit": True,
                "rollback_guard": "enabled",
                "product_create_transaction_hash": "a" * 64,
                "product_facts_sha256": "c" * 64,
                "repository_write_set_hash": "b" * 64,
            },
            "product_create_transaction": {
                "transaction_hash": "a" * 64,
                "product_facts_sha256": "c" * 64,
                "repository_write_set_hash": "b" * 64,
            },
            "patchset_request": {
                "status": "no_repairable_operations",
                "operation_count": 0,
                "operations": [],
            },
            "last_repair_patchset_request": {
                "status": "repairable",
                "operation_count": 1,
                "operations": [
                    {
                        "operation_id": "GF-PATCH-001",
                        "target_layer": "semantic_model",
                        "replacement_fact": {"external_systems": ["accepted source"]},
                    }
                ],
                "tribunal_patch_plan": {
                    "status": "planned",
                    "operation_count": 1,
                    "provider": {"provider": "codex-cli", "last_failure_code": ""},
                },
                "structured_patch_fallback": {
                    "status": "applied",
                    "source": "source_anchored_semantic_fact",
                    "operation_count": 1,
                    "provider_failure": {"provider": "codex-cli", "code": "timeout"},
                },
            },
        }
    )

    assert summary["patchset_summary_source"] == "last_repair_patchset_request"
    assert summary["patchset_status"] == "repairable"
    assert summary["patchset_operation_count"] == 1
    assert summary["tribunal_patch_plan_status"] == "planned"
    assert summary["tribunal_patch_plan_operation_count"] == 1
    assert summary["tribunal_patch_plan_provider"] == "codex-cli"
    assert summary["structured_patch_fallback_status"] == "applied"
    assert summary["structured_patch_fallback_source"] == "source_anchored_semantic_fact"
    assert summary["structured_patch_fallback_operation_count"] == 1
    assert summary["structured_patch_fallback_provider"] == "codex-cli"
    assert summary["structured_patch_fallback_provider_failure_code"] == "timeout"
    assert summary["create_elapsed_seconds"] == 0.125
    assert summary["write_transaction"] == {
        "status": "committed",
        "commit_only": True,
        "prewrite_clean_before_commit": True,
        "rollback_guard": "enabled",
        "product_create_transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }
    assert summary["product_create_transaction"] == {
        "transaction_hash": "a" * 64,
        "product_facts_sha256": "c" * 64,
        "repository_write_set_hash": "b" * 64,
    }


def test_commit_manifest_summary_does_not_invent_missing_elapsed_time() -> None:
    module = _module()

    summary = module.commit_manifest_summary({"status": "passed"})

    assert summary["create_elapsed_seconds"] is None
