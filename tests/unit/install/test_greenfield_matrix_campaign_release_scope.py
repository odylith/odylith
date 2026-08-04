from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from tests.greenfield_matrix_campaign_test_support import command_arg
from tests.greenfield_matrix_campaign_test_support import matrix_campaign_runner_module
from tests.greenfield_matrix_campaign_test_support import write_case_file
from tests.greenfield_matrix_campaign_test_support import write_payload
from tests.greenfield_matrix_campaign_test_support import write_semantic_release_fixture


def test_matrix_command_separates_discovery_and_release_policy(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_scope_test")
    discovery = module.CampaignShard(
        tier="volume-discovery",
        case_file=tmp_path / "shard-01.json",
        proof_tier="discovery",
        install_mode="seeded",
        include_browser_proof=False,
        include_rescue_smoke=False,
        include_natural_rescue_proof=False,
        stop_after_failures=1,
        stop_after_cluster_failures=2,
        require_high_variance_stressors=True,
        required_stressors=("modal-expert-lens",),
    )
    release = module.CampaignShard(
        tier="release-proof",
        case_file=tmp_path / "release.json",
        proof_tier="release",
        install_mode="full",
        include_browser_proof=True,
        include_rescue_smoke=True,
        include_natural_rescue_proof=True,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        require_high_variance_stressors=True,
        required_stressors=(),
        release_input_snapshot_root=tmp_path / "sealed-release-inputs",
    )

    discovery_command = module._matrix_command(  # noqa: SLF001
        shard=discovery,
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_json=tmp_path / "out.json",
        telemetry_jsonl=tmp_path / "out.jsonl",
    )
    release_command = module._matrix_command(  # noqa: SLF001
        shard=release,
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_json=tmp_path / "release.json",
        telemetry_jsonl=tmp_path / "release.jsonl",
    )

    assert command_arg(discovery_command, "--proof-tier") == "discovery"
    assert "--allow-skipped-browser-proof" in discovery_command
    assert "--skip-rescue-smoke" in discovery_command
    assert "--skip-natural-rescue-proof" in discovery_command
    assert "--skip-commit-recovery-proof" in discovery_command
    assert "--require-high-variance-stressors" not in discovery_command
    assert command_arg(discovery_command, "--required-stressor") == "modal-expert-lens"
    assert "--allow-partial-stressor-coverage" in discovery_command
    assert command_arg(discovery_command, "--install-mode") == "seeded"
    assert command_arg(release_command, "--proof-tier") == "release"
    assert "--include-browser-proof" in release_command
    assert "--include-rescue-smoke" in release_command
    assert "--include-natural-rescue-proof" in release_command
    assert "--include-commit-recovery-proof" in release_command
    assert command_arg(release_command, "--install-mode") == "full"
    assert "--stop-after-failures" not in release_command
    assert "--allow-partial-stressor-coverage" not in release_command
    assert command_arg(release_command, "--sealed-release-input-root") == str(
        (tmp_path / "sealed-release-inputs").resolve()
    )


def test_each_release_shard_requires_commit_recovery_proof(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_recovery_test")
    shards = module._release_tier(  # noqa: SLF001
        "release-proof",
        (tmp_path / "release-01.json", tmp_path / "release-02.json"),
        require_high_variance_stressors=True,
        required_stressors=(),
    )

    commands = [
        module._matrix_command(  # noqa: SLF001
            shard=shard,
            dist_dir=tmp_path / "dist",
            version="0.1.15",
            temp_parent=tmp_path / "tmp",
            output_json=tmp_path / f"{shard.name}.json",
            telemetry_jsonl=tmp_path / f"{shard.name}.jsonl",
        )
        for shard in shards
    ]

    assert len(commands) == 2
    assert all("--include-commit-recovery-proof" in command for command in commands)
    assert all("--skip-commit-recovery-proof" not in command for command in commands)


def test_campaign_never_promotes_release_without_an_audited_source_corpus(tmp_path: Path, monkeypatch) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_scope_missing_audit")
    calls: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        calls.append(command)
        write_payload(Path(command_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        volume_case_files=(tmp_path / "volume-01.json",),
        release_case_files=(tmp_path / "release.json",),
        discovery_max_workers=2,
    )

    assert payload["status"] == "failed"
    assert payload["execution_status"] == "failed"
    assert payload["release_proof_completed"] is False
    assert payload["release_readiness_status"] == "failed"
    assert [tier["tier"] for tier in payload["tiers"]] == ["volume-discovery", "release-proof"]
    assert [command_arg(command, "--proof-tier") for command in calls] == ["discovery"]
    assert payload["tiers"][-1]["stop_reason"].startswith("tier-release-corpus-invalid:")


def test_semantic_release_shard_does_not_require_a_source_corpus_audit(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_semantic_release_scope")
    shard_runner = sys.modules["greenfield_matrix_campaign_shard_runner"]
    holdout = tmp_path / "final-holdout.v1.json"
    write_case_file(holdout, name="semantic holdout", case_id="semantic-holdout", stressors=())
    shard = module.CampaignShard(
        tier="release-proof",
        case_file=holdout,
        proof_tier="release",
        install_mode="full",
        include_browser_proof=True,
        include_rescue_smoke=True,
        include_natural_rescue_proof=True,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        require_high_variance_stressors=False,
        required_stressors=(),
        release_input_snapshot_root=tmp_path / "sealed-release-inputs",
        semantic_annotations_file=holdout,
        evaluation_split_manifest=tmp_path / "evaluation-splits.v1.json",
        final_holdout_run_ledger=tmp_path / "final-holdout-run.v1.json",
        implementation_revision="a" * 40,
    )

    failure = shard_runner._tier_case_file_preflight_failure(  # noqa: SLF001
        shards=(shard,),
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        temp_parent=tmp_path / "tmp",
    )

    assert failure is None


def test_partial_semantic_release_contract_still_requires_a_source_corpus_audit(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_partial_semantic_release_scope")
    shard_runner = sys.modules["greenfield_matrix_campaign_shard_runner"]
    holdout = tmp_path / "final-holdout.v1.json"
    write_case_file(holdout, name="partial semantic holdout", case_id="partial-semantic-holdout", stressors=())
    shard = module.CampaignShard(
        tier="release-proof",
        case_file=holdout,
        proof_tier="release",
        install_mode="full",
        include_browser_proof=True,
        include_rescue_smoke=True,
        include_natural_rescue_proof=True,
        stop_after_failures=0,
        stop_after_cluster_failures=0,
        require_high_variance_stressors=False,
        required_stressors=(),
        release_input_snapshot_root=tmp_path / "sealed-release-inputs",
        semantic_annotations_file=holdout,
        evaluation_split_manifest=tmp_path / "evaluation-splits.v1.json",
        final_holdout_run_ledger=None,
        implementation_revision="a" * 40,
    )

    failure = shard_runner._tier_case_file_preflight_failure(  # noqa: SLF001
        shards=(shard,),
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        temp_parent=tmp_path / "tmp",
    )

    assert failure is not None
    assert failure.payload_status == "release-corpus-invalid"
    assert "release proof requires --release-audit-file" in failure.stderr_excerpt


def test_campaign_runs_a_sealed_semantic_release_without_a_source_corpus_audit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_sealed_semantic_release_scope")
    repo_root = tmp_path / "repo"
    holdout, manifest = write_semantic_release_fixture(repo_root=repo_root, temp_root=tmp_path)
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "build-provenance.v1.json").write_text(
        json.dumps(
            {
                "version": "odylith-release-provenance.v1",
                "source_tree": {"head": "a" * 40, "dirty": False},
                "workflow": {"sha": "a" * 40},
            }
        ),
        encoding="utf-8",
    )
    commands: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        commands.append(command)
        write_payload(Path(command_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    release_input_manifest = module._release_proof_input_manifest  # noqa: SLF001
    monkeypatch.setattr(module, "REPO_ROOT", repo_root)
    monkeypatch.setattr(
        module,
        "_release_proof_input_manifest",
        lambda **kwargs: release_input_manifest(**kwargs, repo_root=repo_root),
    )
    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=dist_dir,
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        release_case_files=(holdout,),
        semantic_annotations_file=holdout,
        evaluation_split_manifest=manifest,
        final_holdout_run_ledger=tmp_path / "final-holdout-run.v1.json",
        implementation_revision="a" * 40,
        require_release_readiness=True,
    )

    assert payload["status"] == "release-ready"
    assert payload["release_readiness_status"] == "proven"
    assert {
        "kind": "distribution-build-provenance",
        "implementation_revision": "a" * 40,
    }.items() <= next(
        reference
        for reference in payload["release_proof_inputs"]
        if reference["kind"] == "distribution-build-provenance"
    ).items()
    assert len(commands) == 1
    assert "--release-audit-file" not in commands[0]
    assert command_arg(commands[0], "--semantic-annotations-file") == command_arg(
        commands[0], "--case-file"
    )
    sealed_root = Path(command_arg(commands[0], "--sealed-release-input-root"))
    assert not sealed_root.exists()


def test_semantic_release_rejects_revision_not_bound_to_distribution_provenance(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_semantic_revision_scope")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "build-provenance.v1.json").write_text(
        json.dumps(
            {
                "version": "odylith-release-provenance.v1",
                "source_tree": {"head": "a" * 40, "dirty": False},
                "workflow": {"sha": "a" * 40},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="implementation revision does not match distribution build provenance"):
        module.run_campaign(
            dist_dir=dist_dir,
            version="0.1.15",
            temp_parent=tmp_path / "tmp",
            output_dir=tmp_path / "out",
            telemetry_dir=tmp_path / "telemetry",
            semantic_annotations_file=tmp_path / "final-holdout.v1.json",
            final_holdout_run_ledger=tmp_path / "final-holdout-run.v1.json",
            implementation_revision="b" * 40,
        )


@pytest.mark.parametrize(
    ("provenance_text", "message"),
    (
        (None, "safe distribution build provenance"),
        ("not-json\n", "distribution build provenance is unreadable"),
        ("{}\n", "supported distribution build provenance"),
    ),
)
def test_semantic_release_requires_supported_distribution_provenance(
    tmp_path: Path,
    provenance_text: str | None,
    message: str,
) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_semantic_provenance_scope")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    if provenance_text is not None:
        (dist_dir / "build-provenance.v1.json").write_text(provenance_text, encoding="utf-8")

    with pytest.raises(RuntimeError, match=message):
        module.verify_distribution_provenance(
            provenance_path=dist_dir / "build-provenance.v1.json",
            implementation_revision="a" * 40,
        )


def test_semantic_release_rejects_dirty_distribution_source_provenance(tmp_path: Path) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_dirty_semantic_provenance_scope")
    dist_dir = tmp_path / "dist"
    dist_dir.mkdir()
    (dist_dir / "build-provenance.v1.json").write_text(
        json.dumps(
            {
                "version": "odylith-release-provenance.v1",
                "source_tree": {"head": "a" * 40, "dirty": True},
                "workflow": {"sha": "a" * 40},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="clean distribution source provenance"):
        module.verify_distribution_provenance(
            provenance_path=dist_dir / "build-provenance.v1.json",
            implementation_revision="a" * 40,
        )


def test_campaign_rejects_individually_inadequate_release_case_files_before_union(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_scope_inadequate")
    shard_runner = sys.modules["greenfield_matrix_campaign_shard_runner"]
    first = tmp_path / "release-01.json"
    second = tmp_path / "release-02.json"
    write_case_file(
        first,
        name="release case one",
        case_id="release-one",
        stressors=("modal-expert-lens",),
    )
    write_case_file(
        second,
        name="release case two",
        case_id="release-two",
        stressors=("registry-contract-pressure",),
    )
    evaluated_case_counts: list[int] = []
    evaluated_audit_ids: list[tuple[str, ...]] = []

    def fake_evaluate(cases, audits):  # noqa: ANN001
        evaluated_case_counts.append(len(cases))
        evaluated_audit_ids.append(tuple(audit.case_id for audit in audits))
        return type("Evaluation", (), {"passed": len(cases) == 2, "issues": ("insufficient evidence",)})()

    def fake_run(**kwargs):  # noqa: ANN001
        raise AssertionError(f"release shard should not run when preflight fails: {kwargs['command']}")

    monkeypatch.setattr(
        shard_runner,
        "load_release_audit_file",
        lambda _path: (
            type("Audit", (), {"case_id": "release-one"})(),
            type("Audit", (), {"case_id": "release-two"})(),
        ),
    )
    monkeypatch.setattr(shard_runner, "evaluate_release_corpus", fake_evaluate)
    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)
    monkeypatch.setattr(module, "_seal_release_proof_inputs", lambda **_kwargs: None)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        release_case_files=(first, second),
        release_audit_file=tmp_path / "audit.json",
    )

    assert evaluated_case_counts == [1, 1]
    assert evaluated_audit_ids == [("release-one",), ("release-two",)]
    assert payload["status"] == "failed"
    assert payload["tiers"][0]["stop_reason"].startswith("tier-release-corpus-invalid:release-proof-release-01")


def test_campaign_filters_union_audits_for_each_release_shard_before_union_validation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_scope_union")
    shard_runner = sys.modules["greenfield_matrix_campaign_shard_runner"]
    first = tmp_path / "release-01.json"
    second = tmp_path / "release-02.json"
    audit_file = tmp_path / "audit.json"
    write_case_file(first, name="release case one", case_id="release-one", stressors=())
    write_case_file(second, name="release case two", case_id="release-two", stressors=())
    audit_file.write_text("{}\n", encoding="utf-8")
    evaluations: list[tuple[tuple[str, ...], tuple[str, ...]]] = []

    def fake_evaluate(cases, audits):  # noqa: ANN001
        evaluations.append(
            (
                tuple(case.case_id for case in cases),
                tuple(audit.case_id for audit in audits),
            )
        )
        return type("Evaluation", (), {"passed": True, "issues": ()})()

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        write_payload(Path(command_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(
        shard_runner,
        "load_release_audit_file",
        lambda _path: (
            type("Audit", (), {"case_id": "release-one"})(),
            type("Audit", (), {"case_id": "release-two"})(),
        ),
    )
    monkeypatch.setattr(shard_runner, "evaluate_release_corpus", fake_evaluate)
    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)
    monkeypatch.setattr(module, "_seal_release_proof_inputs", lambda **_kwargs: None)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        release_case_files=(first, second),
        release_audit_file=audit_file,
    )

    assert evaluations == [
        (("release-one",), ("release-one",)),
        (("release-two",), ("release-two",)),
        (("release-one", "release-two"), ("release-one", "release-two")),
    ]
    assert payload["status"] == "release-ready"


def test_campaign_finishes_discovery_tiers_before_rejecting_an_unproven_release(
    tmp_path: Path,
    monkeypatch,
) -> None:
    module = matrix_campaign_runner_module("greenfield_matrix_campaign_runner_release_scope_unproven")
    calls: list[list[str]] = []

    def fake_run(**kwargs):  # noqa: ANN001
        command = kwargs["command"]
        calls.append(command)
        write_payload(Path(command_arg(command, "--output-json")), status="passed")
        return subprocess.CompletedProcess(command, 0, "passed shard", ""), ""

    monkeypatch.setattr(module, "_run_command_with_progress", fake_run)

    payload = module.run_campaign(
        dist_dir=tmp_path / "dist",
        version="0.1.15",
        temp_parent=tmp_path / "tmp",
        output_dir=tmp_path / "out",
        telemetry_dir=tmp_path / "telemetry",
        regression_case_files=(tmp_path / "regression-01.json", tmp_path / "regression-02.json"),
        volume_case_files=(tmp_path / "volume-01.json",),
        deep_volume_case_files=(tmp_path / "deep-volume-01.json", tmp_path / "deep-volume-02.json"),
        release_case_files=(tmp_path / "release.json",),
        discovery_max_workers=1,
        regression_max_workers=2,
        volume_max_workers=3,
        deep_volume_max_workers=4,
    )

    assert payload["status"] == "failed"
    assert payload["execution_status"] == "failed"
    assert [tier["tier"] for tier in payload["tiers"]] == [
        "60-case-regression",
        "volume-discovery",
        "240-case-discovery",
        "release-proof",
    ]
    assert [tier["max_workers"] for tier in payload["tiers"]] == [2, 3, 4, 1]
    assert [command_arg(command, "--campaign-phase") for command in calls] == [
        "60-case-regression",
        "60-case-regression",
        "volume-discovery",
        "240-case-discovery",
        "240-case-discovery",
    ]
    assert payload["tiers"][-1]["stop_reason"].startswith("tier-release-corpus-invalid:")
