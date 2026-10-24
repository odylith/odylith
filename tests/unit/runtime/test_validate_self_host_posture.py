from __future__ import annotations

from pathlib import Path
import os
import subprocess

import pytest

from odylith import __version__ as PACKAGE_VERSION
from odylith.install.manager import version_status
from odylith.install.state import write_install_state, write_version_pin
from odylith.runtime.governance import validate_self_host_posture


REPO_ROOT = Path(__file__).resolve().parents[3]


def _next_patch_version(version: str) -> str:
    major, minor, patch = version.split(".", 2)
    return f"{major}.{minor}.{int(patch) + 1}"


def _seed_product_repo(
    repo_root: Path,
    *,
    pin_version: str = PACKAGE_VERSION,
    active_version: str = PACKAGE_VERSION,
    verified: bool = True,
    workflow_body: str | None = None,
) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text(
        f"[project]\nname='odylith'\nversion='{pin_version}'\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "odylith" / "__init__.py").write_text(
        f'"""Odylith CLI and public contracts."""\n\n__all__ = ["__version__"]\n\n__version__ = "{pin_version}"\n',
        encoding="utf-8",
    )
    (repo_root / ".github" / "workflows").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    (repo_root / ".github" / "workflows" / "release.yml").write_text(
        workflow_body or (REPO_ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    write_version_pin(repo_root=repo_root, version=pin_version)

    version_root = repo_root / ".odylith" / "runtime" / "versions" / active_version / "bin"
    version_root.mkdir(parents=True, exist_ok=True)
    python_path = version_root / "python"
    python_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    python_path.chmod(0o755)

    current_link = repo_root / ".odylith" / "runtime" / "current"
    current_link.parent.mkdir(parents=True, exist_ok=True)
    if current_link.exists() or current_link.is_symlink():
        current_link.unlink()
    current_link.symlink_to(version_root.parent)
    write_install_state(
        repo_root=repo_root,
        payload={
            "active_version": active_version,
            "activation_history": [active_version],
            "installed_versions": {
                active_version: {
                    "runtime_root": str(version_root.parent),
                    "verification": (
                        {"mode": "source-local"}
                        if active_version == "source-local"
                        else ({"wheel_sha256": "abc123"} if verified else {})
                    ),
                }
            },
            "last_known_good_version": pin_version if active_version == "source-local" else active_version,
            "detached": active_version == "source-local",
        },
    )


def test_release_contract_passes_when_source_pin_and_tag_align(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root)

    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{PACKAGE_VERSION}",
    )

    assert errors == []


def test_release_contract_fails_when_expected_tag_does_not_match_pin(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root)

    expected_version = _next_patch_version(PACKAGE_VERSION)
    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{expected_version}",
    )

    assert any(
        f"expected release tag version `{expected_version}` does not match tracked product pin `{PACKAGE_VERSION}`"
        in item
        for item in errors
    )


def test_local_runtime_validation_passes_for_pinned_release_posture(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root)

    errors = validate_self_host_posture.validate_local_runtime(repo_root=repo_root)

    assert errors == []


def test_local_runtime_validation_fails_for_detached_source_local_posture(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root, active_version="source-local")

    errors = validate_self_host_posture.validate_local_runtime(repo_root=repo_root)

    assert any("pinned_release" in item for item in errors)
    assert any("pinned_runtime" in item for item in errors)


def test_local_runtime_validation_fails_for_unverified_wrapped_runtime(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root, verified=False)

    status = version_status(repo_root=repo_root)
    errors = validate_self_host_posture.validate_local_runtime(repo_root=repo_root)

    assert status.posture == "pinned_release"
    assert status.runtime_source == "wrapped_runtime"
    assert status.release_eligible is False
    assert any("not release eligible" in item for item in errors)
    assert any("pinned_runtime" in item for item in errors)


def test_release_contract_fails_when_release_workflow_drops_the_gate(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(repo_root, workflow_body="name: release\n")

    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{PACKAGE_VERSION}",
    )

    assert any("release workflow must invoke `odylith validate self-host-posture" in item for item in errors)


def test_release_contract_fails_when_release_workflow_drops_authority_guard(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(
        repo_root,
        workflow_body=(
            "name: release\n"
            "jobs:\n"
            "  build:\n"
            "    steps:\n"
            "      - run: PYTHONPATH=src python -m odylith.cli validate self-host-posture --repo-root . --mode release --expected-tag \"${{ inputs.tag }}\"\n"
        ),
    )

    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{PACKAGE_VERSION}",
    )

    assert any("release workflow must enforce canonical release authority" in item for item in errors)


def test_release_contract_fails_when_release_workflow_drops_commit_guard(tmp_path: Path) -> None:
    repo_root = tmp_path / "repo"
    repo_root.mkdir()
    _seed_product_repo(
        repo_root,
        workflow_body=(REPO_ROOT / ".github/workflows/release.yml").read_text().replace(
            '          [[ "$GITHUB_SHA" == "$RELEASE_EXPECTED_SHA" ]]', ''),
    )

    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{PACKAGE_VERSION}",
    )

    assert any("must bind the requested tag to the maintainer session commit" in item for item in errors)


@pytest.mark.parametrize('guard', [
    '[[ "$GITHUB_REPOSITORY" == "$ODYLITH_RELEASE_REPO" ]]',
    '[[ "$GITHUB_ACTOR" == "$ODYLITH_RELEASE_ACTOR" ]]',
    '[[ "$GITHUB_REF" == "$ODYLITH_RELEASE_REF" ]]',
    '[[ "$GITHUB_SHA" == "$RELEASE_EXPECTED_SHA" ]]',
    '[[ "$(git rev-parse "${RELEASE_TAG}^{commit}")" == "$RELEASE_EXPECTED_SHA" ]]',
    '[[ "$(git rev-parse HEAD)" == "$RELEASE_EXPECTED_SHA" ]]',
    '[[ -z "$(git status --porcelain)" ]]',
    '[[ "$RELEASE_EXPECTED_SHA" =~ ^[0-9a-f]{40}$ ]]',
    r'[[ "$RELEASE_TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]',
    '[[ "$RELEASE_OPERATION" == candidate || "$RELEASE_OPERATION" == promote ]]',
])
def test_release_posture_rejects_commented_out_real_guard(tmp_path, guard):
    text = (REPO_ROOT / '.github/workflows/release.yml').read_text()
    assert guard in text
    _seed_product_repo(tmp_path, workflow_body=text.replace(guard, '# ' + guard))
    errors = validate_self_host_posture.validate_release_contract(repo_root=tmp_path,
        expected_tag=f'v{PACKAGE_VERSION}')
    assert any('canonical release authority' in item or 'must bind the requested tag' in item for item in errors)


@pytest.mark.parametrize('field,value', [
    ('GITHUB_REPOSITORY', 'untrusted/repo'), ('GITHUB_ACTOR', 'someone-else'),
    ('GITHUB_REF', 'refs/heads/other'), ('GITHUB_SHA', 'b' * 40),
    ('RELEASE_TAG', 'v0.1.15; touch injected'), ('RELEASE_EXPECTED_SHA', 'HEAD'),
    ('RELEASE_OPERATION', 'rebuild'), (None, None),
])
def test_actual_workflow_authorization_shell_fails_before_later_actions(field, value, tmp_path):
    workflow = (REPO_ROOT / '.github/workflows/release.yml').read_text()
    block = workflow.split('        run: |\n', 1)[1].split('      - uses:', 1)[0]
    script = '\n'.join(line.removeprefix('          ') for line in block.splitlines())
    marker = tmp_path / 'authorized'
    environment = dict(os.environ, GITHUB_REPOSITORY='odylith/odylith', GITHUB_ACTOR='freedom-research',
        GITHUB_REF='refs/heads/main', GITHUB_SHA='a' * 40, ODYLITH_RELEASE_REPO='odylith/odylith',
        ODYLITH_RELEASE_ACTOR='freedom-research', ODYLITH_RELEASE_REF='refs/heads/main',
        RELEASE_EXPECTED_SHA='a' * 40, RELEASE_TAG='v0.1.15', RELEASE_OPERATION='candidate', MARKER=str(marker))
    if field:
        environment[field] = value
    result = subprocess.run(['bash', '-e', '-o', 'pipefail', '-c', script + '\ntouch "$MARKER"'],
        env=environment, cwd=tmp_path, capture_output=True, text=True)
    assert result.returncode == (0 if field is None else 2)
    assert marker.exists() is (field is None)
    assert not (tmp_path / 'injected').exists()


def test_hosted_checkout_detaches_canonical_h_before_governance(tmp_path, capsys):
    from odylith import cli

    _seed_product_repo(tmp_path)

    def git(*args):
        return subprocess.check_output([
            'git', '-C', str(tmp_path), '-c', 'core.hooksPath=/dev/null',
            '-c', 'user.name=freedom-research', '-c', 'user.email=freedom@freedompreetham.org',
            *args,
        ], text=True).strip()

    git('init', '--initial-branch=main')
    git('add', '--all')
    git('commit', '-m', 'Synthetic hosted checkout')
    revision = git('rev-parse', 'HEAD')
    assert cli._guard_product_repo_main_branch(repo_root=tmp_path) == 2
    assert 'Maintainer authoring on `main` is forbidden' in capsys.readouterr().err

    workflow = (REPO_ROOT / '.github/workflows/release.yml').read_text()
    checkout = workflow.split('- uses: actions/checkout@', 1)[1].split('      - ', 1)[0]
    # A main workflow dispatch defaults checkout to the attached main branch.
    checkout_ref = next((line.strip().removeprefix('ref: ') for line in checkout.splitlines()
                         if line.strip().startswith('ref: ')), 'main')
    git('checkout', checkout_ref.replace('${{ inputs.expected_sha }}', revision).removeprefix('refs/heads/'))

    assert cli._guard_product_repo_main_branch(repo_root=tmp_path) == 0, capsys.readouterr().err
    assert git('rev-parse', 'HEAD') == revision
    assert git('branch', '--show-current') == ''
    assert git('status', '--porcelain') == ''
