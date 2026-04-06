from __future__ import annotations

from pathlib import Path

from odylith import __version__ as PACKAGE_VERSION
from odylith.install.manager import version_status
from odylith.install.state import write_install_state, write_version_pin
from odylith.runtime.governance import validate_self_host_posture


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
        workflow_body
        or (
            "name: release\n"
            "on:\n"
            "  workflow_dispatch:\n"
            "    inputs:\n"
            "      tag:\n"
            "        required: true\n"
            "        type: string\n"
            "      expected_sha:\n"
            "        required: true\n"
            "        type: string\n"
            "jobs:\n"
            "  build:\n"
            "    env:\n"
            "      ODYLITH_RELEASE_REPO: freedom-research/odylith\n"
            "      ODYLITH_RELEASE_ACTOR: freedom-research\n"
            "      ODYLITH_RELEASE_REF: refs/heads/main\n"
            "    steps:\n"
            "      - run: |\n"
            "          if [[ \"${GITHUB_REPOSITORY}\" != \"${ODYLITH_RELEASE_REPO}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "          if [[ \"${GITHUB_ACTOR}\" != \"${ODYLITH_RELEASE_ACTOR}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "          if [[ \"${GITHUB_REF}\" != \"${ODYLITH_RELEASE_REF}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "      - run: |\n"
            "          tag_sha=\"$(git rev-parse \"${{ inputs.tag }}^{commit}\")\"\n"
            "          if [[ \"${GITHUB_SHA}\" != \"${{ inputs.expected_sha }}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "          if [[ \"${tag_sha}\" != \"${{ inputs.expected_sha }}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "      - run: PYTHONPATH=src python -m odylith.cli validate self-host-posture --repo-root . --mode release --expected-tag \"${{ inputs.tag }}\"\n"
        ),
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
        workflow_body=(
            "name: release\n"
            "on:\n"
            "  workflow_dispatch:\n"
            "    inputs:\n"
            "      tag:\n"
            "        required: true\n"
            "        type: string\n"
            "jobs:\n"
            "  build:\n"
            "    env:\n"
            "      ODYLITH_RELEASE_REPO: freedom-research/odylith\n"
            "      ODYLITH_RELEASE_ACTOR: freedom-research\n"
            "      ODYLITH_RELEASE_REF: refs/heads/main\n"
            "    steps:\n"
            "      - run: |\n"
            "          if [[ \"${GITHUB_REPOSITORY}\" != \"${ODYLITH_RELEASE_REPO}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "          if [[ \"${GITHUB_ACTOR}\" != \"${ODYLITH_RELEASE_ACTOR}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "          if [[ \"${GITHUB_REF}\" != \"${ODYLITH_RELEASE_REF}\" ]]; then\n"
            "            exit 2\n"
            "          fi\n"
            "      - run: PYTHONPATH=src python -m odylith.cli validate self-host-posture --repo-root . --mode release --expected-tag \"${{ inputs.tag }}\"\n"
        ),
    )

    errors = validate_self_host_posture.validate_release_contract(
        repo_root=repo_root,
        expected_tag=f"v{PACKAGE_VERSION}",
    )

    assert any("must bind the requested tag to the maintainer session commit" in item for item in errors)
