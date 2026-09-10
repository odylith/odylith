"""Public release comparison and registry coverage remain separate evidence."""

import json
from pathlib import Path
import subprocess

import pytest

from odylith import cli
from odylith.install import migration_release_gate, migration_runtime


def test_missing_baseline_blocks_without_hiding_registered_coverage(capsys) -> None:
    repo_root = Path(__file__).resolve().parents[2]

    rc = cli.main([
        "release",
        "migration-gate",
        "--repo-root",
        str(repo_root),
        "--target-version",
        "0.1.15",
        "--json",
    ])
    payload = json.loads(capsys.readouterr().out)

    assert rc == 1
    assert payload["ok"] is False
    assert payload["schema_version"] == "odylith.release-migration-gate.v1"
    assert payload["fixture_matrix"]["v0.1.11-visible-intervention-value-engine"]["dry_run"] is True
    assert payload["destructive_write_matrix"]["host.claude.preverified-settings"][
        "test_install_bundle_preserves_host_settings_when_runtime_download_fails"
    ] is True
    assert payload["destructive_write_scenarios"]
    assert payload["ungated_lifecycle_paths"] == []
    assert payload["surface_migration_observer"]["schema_version"] == "odylith.surface-migration-observer.v1"
    assert payload["surface_migration_observer"]["ok"] is False

    scope = payload["surface_migration_observer"]["scope"]
    assert scope["kind"] == "unavailable"
    assert scope["assessment_status"] == "unproven"
    assert "--base-ref" in scope["error"]
    assert scope["error"] in payload["blocked_manual_migrations"]


@pytest.mark.parametrize("json_output", [False, True])
def test_cli_observes_committed_scope_with_resolved_provenance(tmp_path, monkeypatch, capsys, json_output) -> None:
    def git(*args):
        return subprocess.run(
            ["git", "-C", str(tmp_path), *args], check=True,
            capture_output=True, text=True,
        ).stdout.strip()

    git("init", "-q")
    git("config", "user.name", "freedom-research")
    git("config", "user.email", "freedom@freedompreetham.org")
    (tmp_path / "README.md").write_text("Published\n", encoding="utf-8")
    git("add", "--all")
    git("commit", "-qm", "Published fixture")
    base = git("rev-parse", "HEAD")
    git("tag", "v1.0.0")
    (tmp_path / "README.md").write_text("Candidate\n", encoding="utf-8")
    git("add", "--all")
    git("commit", "-qm", "Candidate fixture")
    candidate = git("rev-parse", "HEAD")
    monkeypatch.setattr(cli, "repo_role_from_local_shape", lambda **kwargs: "product_repo")
    args = [
        "release", "migration-gate", "--repo-root", str(tmp_path),
        "--target-version", "1.0.1", "--base-ref", "v1.0.0",
    ]
    rc = cli.main(args + (["--json"] if json_output else []))
    output = capsys.readouterr().out
    assert rc == 1  # No completed assessment or release proof files in this fixture.
    if json_output:
        observer = json.loads(output)["surface_migration_observer"]
        assert observer["changed_paths"] == ["README.md"]
        assert observer["scope"]["kind"] == "release_comparison"
        assert observer["scope"]["base_commit"] == base
        assert observer["scope"]["candidate_commit"] == candidate
        assert not observer["ok"]
    else:
        assert f"base={base}; candidate={candidate}" in output
        assert "surface migration assessment incomplete" in output


def test_release_gate_has_one_owner_without_runtime_forwarder() -> None:
    assert not hasattr(migration_runtime, "validate_release_migration_gate")
    assert not hasattr(migration_runtime, "ReleaseMigrationGateReport")
    assert migration_release_gate.validate_release_migration_gate.__module__ == migration_release_gate.__name__
    assert migration_release_gate.ReleaseMigrationGateReport.__module__ == migration_release_gate.__name__


def test_release_gate_help_names_baseline(capsys) -> None:
    with pytest.raises(SystemExit) as result:
        cli.main(["release", "migration-gate", "--help"])
    assert result.value.code == 0
    output = capsys.readouterr().out
    assert "--base-ref" in output
    assert "previous published release" in output
