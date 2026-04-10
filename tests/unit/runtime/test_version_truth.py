from __future__ import annotations

from pathlib import Path

from odylith.install.state import write_version_pin
from odylith.runtime.governance import version_truth


def _seed_product_repo(
    repo_root: Path,
    *,
    source_version: str,
    package_version: str,
    pin_version: str,
) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n", encoding="utf-8")
    (repo_root / "pyproject.toml").write_text(
        f"[project]\nname='odylith'\nversion='{source_version}'\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "odylith" / "__init__.py").write_text(
        version_truth.render_package_init(version=package_version),
        encoding="utf-8",
    )
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    write_version_pin(repo_root=repo_root, version=pin_version)


def _seed_release_security_docs(repo_root: Path, *, release_tag: str) -> None:
    (repo_root / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "SECURITY.md").write_text(
        f"# Security Policy\n\nLatest published release: `{release_tag}`.\n",
        encoding="utf-8",
    )
    (repo_root / "odylith" / "SECURITY_POSTURE.md").write_text(
        f"# Security Posture\n\nCurrent shipped release: `{release_tag}`.\n",
        encoding="utf-8",
    )
    (repo_root / "src" / "odylith" / "bundle" / "assets" / "odylith" / "SECURITY_POSTURE.md").write_text(
        f"# Security Posture\n\nCurrent shipped release: `{release_tag}`.\n",
        encoding="utf-8",
    )


def test_validate_version_truth_reports_package_and_pin_drift(tmp_path: Path) -> None:
    _seed_product_repo(
        tmp_path,
        source_version="0.1.6",
        package_version="0.1.5",
        pin_version="0.1.4",
    )

    errors = version_truth.validate_version_truth(repo_root=tmp_path)

    assert "package version `0.1.5` does not match `pyproject.toml` version `0.1.6`" in errors
    assert "tracked product pin `0.1.4` does not match `pyproject.toml` version `0.1.6`" in errors


def test_sync_version_truth_regenerates_package_and_pin_from_pyproject(tmp_path: Path) -> None:
    _seed_product_repo(
        tmp_path,
        source_version="0.1.6",
        package_version="0.1.5",
        pin_version="0.1.4",
    )

    changed = version_truth.sync_version_truth(repo_root=tmp_path)

    changed_paths = {path.relative_to(tmp_path).as_posix() for path in changed}
    assert changed_paths == {
        "src/odylith/__init__.py",
        "odylith/runtime/source/product-version.v1.json",
    }
    assert version_truth.validate_version_truth(repo_root=tmp_path) == []
    assert version_truth.load_package_version(repo_root=tmp_path) == "0.1.6"
    assert version_truth.collect_version_truth(repo_root=tmp_path).pin_version == "0.1.6"


def test_validate_release_security_docs_reports_stale_release_mentions(tmp_path: Path) -> None:
    _seed_product_repo(
        tmp_path,
        source_version="0.1.10",
        package_version="0.1.10",
        pin_version="0.1.10",
    )
    _seed_release_security_docs(tmp_path, release_tag="v0.1.9")

    errors = version_truth.validate_release_security_docs(repo_root=tmp_path, expected_version="0.1.10")

    assert errors == [
        "release-facing security doc `SECURITY.md` does not mention expected release `v0.1.10`",
        "release-facing security doc `odylith/SECURITY_POSTURE.md` does not mention expected release `v0.1.10`",
        "release-facing security doc `src/odylith/bundle/assets/odylith/SECURITY_POSTURE.md` does not mention expected release `v0.1.10`",
    ]


def test_validate_release_security_docs_accepts_current_release_mentions(tmp_path: Path) -> None:
    _seed_product_repo(
        tmp_path,
        source_version="0.1.10",
        package_version="0.1.10",
        pin_version="0.1.10",
    )
    _seed_release_security_docs(tmp_path, release_tag="v0.1.10")

    assert version_truth.validate_release_security_docs(repo_root=tmp_path, expected_version="0.1.10") == []
