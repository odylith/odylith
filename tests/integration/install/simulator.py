from __future__ import annotations

import json
import shutil
import sys
import tarfile
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from odylith import cli
from odylith.install import manager as install_manager_module
from odylith.install import release_assets as release_assets_module
from odylith.install import runtime as install_runtime_module
from odylith.install.managed_runtime import (
    CONTEXT_ENGINE_FEATURE_PACK_ID,
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
    MANAGED_RUNTIME_ROOT_NAME,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
    managed_runtime_platform_by_slug,
)
from odylith.install.manager import load_install_state, version_status
from odylith.install.paths import repo_runtime_paths
from odylith.install.state import load_version_pin, write_version_pin

REPO_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class FakeRelease:
    version: str
    repo_schema_version: int = 1
    migration_required: bool = False
    verification: dict[str, object] = field(default_factory=dict)


def _write_repo_root(repo_root: Path) -> None:
    (repo_root / "AGENTS.md").write_text("# Repo Root\n\nBody\n", encoding="utf-8")


def _write_product_repo_shape(repo_root: Path, *, version: str) -> None:
    (repo_root / "pyproject.toml").write_text(f"[project]\nname='odylith'\nversion='{version}'\n", encoding="utf-8")
    (repo_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "radar" / "source").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "maintainer").mkdir(parents=True, exist_ok=True)
    (repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json").write_text(
        '{"version":"v1","components":[]}\n',
        encoding="utf-8",
    )
    (repo_root / "odylith" / "radar" / "source" / "INDEX.md").write_text("# Backlog Index\n", encoding="utf-8")
    shutil.copy2(REPO_ROOT / "odylith" / "AGENTS.md", repo_root / "odylith" / "AGENTS.md")
    shutil.copy2(REPO_ROOT / "odylith" / "maintainer" / "AGENTS.md", repo_root / "odylith" / "maintainer" / "AGENTS.md")


def _seed_first_run_surfaces(repo_root: Path) -> None:
    for relative_path in (
        Path("odylith/index.html"),
        Path("odylith/radar/radar.html"),
        Path("odylith/atlas/atlas.html"),
        Path("odylith/compass/compass.html"),
        Path("odylith/registry/registry.html"),
        Path("odylith/casebook/casebook.html"),
    ):
        output_path = repo_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("<!doctype html>\n", encoding="utf-8")


def _version_sort_key(version: str) -> tuple[int, int, int, str]:
    token = str(version or "").strip()
    major, minor, patch = -1, -1, -1
    suffix = token
    core, sep, tail = token.partition("-")
    try:
        parts = [int(piece) for piece in core.split(".")]
    except ValueError:
        return (-1, -1, -1, token)
    if len(parts) != 3:
        return (-1, -1, -1, token)
    major, minor, patch = parts
    suffix = tail if sep else ""
    return (major, minor, patch, suffix)


class InstallLifecycleSimulator:
    def __init__(self, *, tmp_path: Path, monkeypatch) -> None:
        self.repo_root = tmp_path / "repo"
        self.repo_root.mkdir()
        _write_repo_root(self.repo_root)

        self.source_root = tmp_path / "odylith-source"
        (self.source_root / "src" / "odylith").mkdir(parents=True, exist_ok=True)
        (self.source_root / "pyproject.toml").write_text(
            "[project]\nname='odylith'\nversion='0.0.0'\n",
            encoding="utf-8",
        )

        self._releases: dict[str, FakeRelease] = {}
        self._smoke_failures: dict[str, str] = {}

        monkeypatch.setattr(install_manager_module, "fetch_release", self._fake_fetch_release)
        monkeypatch.setattr(install_manager_module, "install_release_runtime", self._fake_install_release_runtime)
        monkeypatch.setattr(install_manager_module, "install_release_feature_pack", self._fake_install_release_feature_pack)
        monkeypatch.setattr(install_manager_module.subprocess, "run", self._fake_smoke_run)
        monkeypatch.setattr(cli.sync_workstream_artifacts, "main", self._fake_first_run_sync)

    def register_release(
        self,
        version: str,
        *,
        repo_schema_version: int = 1,
        migration_required: bool = False,
        verification: Mapping[str, object] | None = None,
    ) -> FakeRelease:
        release = FakeRelease(
            version=version,
            repo_schema_version=repo_schema_version,
            migration_required=migration_required,
            verification=dict(verification or {"wheel_sha256": f"sha256-{version}"}),
        )
        self._releases[version] = release
        return release

    def fail_smoke_for(self, version: str, *, stderr: str = "simulated smoke failure") -> None:
        self._smoke_failures[str(version).strip()] = stderr

    def install(self, version: str) -> int:
        token = str(version).strip()
        if token not in self._releases:
            self.register_release(token)
        return cli.main(["install", "--repo-root", str(self.repo_root), "--version", str(version)])

    def upgrade(self) -> int:
        return cli.main(["upgrade", "--repo-root", str(self.repo_root)])

    def upgrade_to(self, version: str, *, write_pin: bool = False) -> int:
        argv = ["upgrade", "--repo-root", str(self.repo_root), "--to", str(version)]
        if write_pin:
            argv.append("--write-pin")
        return cli.main(argv)

    def upgrade_source_local(self) -> int:
        return cli.main(
            [
                "upgrade",
                "--repo-root",
                str(self.repo_root),
                "--source-repo",
                str(self.source_root),
            ]
        )

    def rollback_previous(self) -> int:
        return cli.main(["rollback", "--repo-root", str(self.repo_root), "--previous"])

    def doctor(self, *, repair: bool = False, reset_local_state: bool = False) -> int:
        argv = ["doctor", "--repo-root", str(self.repo_root)]
        if repair:
            argv.append("--repair")
        if reset_local_state:
            argv.append("--reset-local-state")
        return cli.main(argv)

    def version(self) -> int:
        return cli.main(["version", "--repo-root", str(self.repo_root)])

    def write_pin(self, version: str, *, repo_schema_version: int = 1, migration_required: bool = False) -> None:
        write_version_pin(
            repo_root=self.repo_root,
            version=version,
            repo_schema_version=repo_schema_version,
            migration_required=migration_required,
        )

    def promote_to_product_repo(self, *, version: str) -> None:
        _write_product_repo_shape(self.repo_root, version=version)

    def state(self) -> dict[str, object]:
        return load_install_state(repo_root=self.repo_root)

    def status(self):
        return version_status(repo_root=self.repo_root)

    def pin(self):
        return load_version_pin(repo_root=self.repo_root, fallback_version=None)

    def active_runtime_name(self) -> str:
        current = self.repo_root / ".odylith" / "runtime" / "current"
        return current.resolve().name if current.is_symlink() else ""

    def install_ledger(self) -> list[dict[str, Any]]:
        ledger_path = self.repo_root / ".odylith" / "install-ledger.v1.jsonl"
        if not ledger_path.is_file():
            return []
        return [
            json.loads(line)
            for line in ledger_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _fake_install_release_runtime(
        self,
        *,
        repo_root: str | Path,
        repo: str,
        version: str = "latest",
        activate: bool = True,
    ) -> SimpleNamespace:
        del repo
        release = self._resolve_release(version)
        version_root = Path(repo_root).expanduser().resolve() / ".odylith" / "runtime" / "versions" / release.version
        python_path = version_root / "bin" / "python"
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_text(
            f'#!/usr/bin/env bash\nexec "{Path(sys.executable).resolve()}" "$@"\n',
            encoding="utf-8",
        )
        python_path.chmod(0o755)
        python3_path = version_root / "bin" / "python3"
        python3_path.write_text(
            f'#!/usr/bin/env bash\nexec "{Path(sys.executable).resolve()}" "$@"\n',
            encoding="utf-8",
        )
        python3_path.chmod(0o755)
        odylith_path = version_root / "bin" / "odylith"
        odylith_path.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
        odylith_path.chmod(0o755)
        (version_root / "pyvenv.cfg").write_text(f"version = {MANAGED_PYTHON_VERSION}\n", encoding="utf-8")
        (version_root / "runtime-metadata.json").write_text(
            json.dumps(
                {
                    "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
                    "version": release.version,
                    "platform": "darwin-arm64",
                    "python_version": MANAGED_PYTHON_VERSION,
                    "source_wheel": f"odylith-{release.version}-py3-none-any.whl",
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        install_runtime_module.runtime_verification_path(version_root).write_text(
            json.dumps(
                {
                    "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
                    "version": release.version,
                    "verification": dict(release.verification),
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        install_runtime_module.write_managed_runtime_trust(
            repo_root=repo_root,
            version_root=version_root,
            verification=dict(release.verification),
        )
        if activate:
            install_runtime_module.switch_runtime(repo_root=repo_root, target=version_root)
            install_runtime_module.ensure_launcher(repo_root=repo_root, fallback_python=python_path)
        return SimpleNamespace(
            version=release.version,
            manifest={
                "repo_schema_version": release.repo_schema_version,
                "migration_required": release.migration_required,
            },
            python=python_path,
            root=version_root,
            verification=dict(release.verification),
        )

    def _fake_fetch_release(self, *, repo_root, repo: str, version: str = "latest"):
        del repo_root, repo
        release = self._resolve_release(version)
        return SimpleNamespace(version=release.version)

    def _fake_install_release_feature_pack(
        self,
        *,
        repo_root,
        repo: str,
        version: str,
        runtime_root=None,
        pack_id: str = CONTEXT_ENGINE_FEATURE_PACK_ID,
    ) -> SimpleNamespace:
        del repo
        release = self._resolve_release(version)
        target_root = (
            Path(runtime_root).expanduser().resolve()
            if runtime_root is not None
            else Path(repo_root).expanduser().resolve() / ".odylith" / "runtime" / "versions" / release.version
        )
        payload_relative_path = "lib/python3.13/site-packages/watchdog/__init__.py"
        payload_path = target_root / payload_relative_path
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        payload_path.write_text(f"watchdog-from-{release.version}\n", encoding="utf-8")
        feature_pack_sha256 = str(release.verification.get("feature_pack_sha256") or f"feature-pack-{release.version}")
        metadata_path = target_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME
        metadata_path.write_text(
            json.dumps(
                {
                    "schema_version": MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
                    "version": release.version,
                    "packs": {
                        pack_id: {
                            "asset_name": f"{pack_id}-darwin-arm64.tar.gz",
                            "display_name": "Odylith Context Engine memory pack",
                            "installed_utc": "2026-04-01T00:00:00+00:00",
                            "paths": [payload_relative_path],
                            "platform": "darwin-arm64",
                            "verification": {
                                "feature_pack_id": pack_id,
                                "feature_pack_sha256": feature_pack_sha256,
                            },
                        }
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        install_runtime_module.write_managed_runtime_trust(
            repo_root=repo_root,
            version_root=target_root,
            verification=install_runtime_module.runtime_verification_evidence(target_root),
        )
        return SimpleNamespace(
            asset_name=f"{pack_id}-darwin-arm64.tar.gz",
            manifest={
                "repo_schema_version": release.repo_schema_version,
                "migration_required": release.migration_required,
            },
            pack_id=pack_id,
            root=target_root,
            verification={
                "feature_pack_id": pack_id,
                "feature_pack_sha256": feature_pack_sha256,
            },
            version=release.version,
        )

    def _fake_smoke_run(self, command, *, check=False, capture_output=False, text=False, **kwargs):  # noqa: ANN001
        del check, capture_output, text, kwargs
        version = Path(str(command[0])).expanduser().resolve().parent.parent.name
        stderr = self._smoke_failures.get(version, "")
        return SimpleNamespace(returncode=1 if stderr else 0, stdout="", stderr=stderr)

    def _fake_first_run_sync(self, argv: list[str]) -> int:
        del argv
        _seed_first_run_surfaces(self.repo_root)
        return 0

    def _resolve_release(self, version: str) -> FakeRelease:
        token = str(version or "").strip()
        if token == "latest":
            if not self._releases:
                raise ValueError("no fake releases registered")
            return max(self._releases.values(), key=lambda release: _version_sort_key(release.version))
        try:
            return self._releases[token]
        except KeyError as exc:  # pragma: no cover - defensive guard for future sims
            raise ValueError(f"fake release {token!r} is not registered") from exc


class VerifiedReleaseLifecycleSimulator(InstallLifecycleSimulator):
    def __init__(self, *, tmp_path: Path, monkeypatch) -> None:
        super().__init__(tmp_path=tmp_path, monkeypatch=monkeypatch)
        self._verified_asset_store = tmp_path / "verified-release-assets"
        self._verified_asset_store.mkdir(parents=True, exist_ok=True)
        self._verified_releases: dict[str, release_assets_module.VerifiedRelease] = {}
        self._verified_feature_packs: dict[str, release_assets_module.VerifiedFeaturePack] = {}
        monkeypatch.setattr(install_manager_module, "install_release_runtime", install_runtime_module.install_release_runtime)
        monkeypatch.setattr(install_runtime_module, "download_verified_feature_pack", self._fake_download_verified_feature_pack)
        monkeypatch.setattr(install_runtime_module, "download_verified_release", self._fake_download_verified_release)
        monkeypatch.setattr(install_manager_module.subprocess, "run", self._fake_runtime_subprocess_run)

    def register_verified_release(
        self,
        version: str,
        *,
        repo_schema_version: int = 1,
        migration_required: bool = False,
        verification: Mapping[str, object] | None = None,
    ) -> release_assets_module.VerifiedRelease:
        release = self.register_release(
            version,
            repo_schema_version=repo_schema_version,
            migration_required=migration_required,
            verification=verification,
        )
        source_dir = self._verified_asset_store / release.version
        source_dir.mkdir(parents=True, exist_ok=True)
        wheel_path = source_dir / f"odylith-{release.version}-py3-none-any.whl"
        wheel_path.write_bytes(f"wheel-{release.version}".encode("utf-8"))
        runtime_bundle_path = source_dir / "odylith-runtime-darwin-arm64.tar.gz"
        self._write_runtime_bundle(runtime_bundle_path, marker=f"odylith-{release.version}-py3-none-any.whl")
        feature_pack_path = source_dir / "odylith-context-engine-memory-darwin-arm64.tar.gz"
        feature_pack_sha256 = str(release.verification.get("feature_pack_sha256") or f"feature-pack-{release.version}")
        self._write_feature_pack_bundle(feature_pack_path)
        verified = release_assets_module.VerifiedRelease(
            version=release.version,
            tag=f"v{release.version}",
            manifest={
                "schema_version": "odylith-release-manifest.v1",
                "version": release.version,
                "tag": f"v{release.version}",
                "repo": "freedom-research/odylith",
                "repo_schema_version": release.repo_schema_version,
                "migration_required": release.migration_required,
                "supported_platforms": ["darwin-arm64"],
                "feature_packs": {
                    CONTEXT_ENGINE_FEATURE_PACK_ID: {
                        "assets": {
                            "darwin-arm64": feature_pack_path.name,
                        },
                        "display_name": "Odylith Context Engine memory pack",
                    }
                },
                "assets": {
                    wheel_path.name: {
                        "sha256": str(release.verification.get("wheel_sha256") or f"sha256-{release.version}"),
                    },
                    runtime_bundle_path.name: {
                        "sha256": str(release.verification.get("runtime_bundle_sha256") or f"runtime-sha256-{release.version}"),
                    },
                    feature_pack_path.name: {
                        "sha256": feature_pack_sha256,
                    },
                },
            },
            provenance={
                "version": "odylith-release-provenance.v1",
                "repo": "freedom-research/odylith",
                "actor": "freedom-research",
                "release_version": release.version,
                "tag": f"v{release.version}",
                "workflow": {"path": ".github/workflows/release.yml", "ref": "refs/heads/main"},
                "artifacts": {
                    "wheel": {"name": wheel_path.name, "sha256": str(release.verification.get("wheel_sha256") or f"sha256-{release.version}")},
                    "runtime_bundles": {
                        "darwin-arm64": {
                            "name": runtime_bundle_path.name,
                            "sha256": str(release.verification.get("runtime_bundle_sha256") or f"runtime-sha256-{release.version}"),
                        }
                    },
                    "feature_packs": {
                        CONTEXT_ENGINE_FEATURE_PACK_ID: {
                            "darwin-arm64": {
                                "name": feature_pack_path.name,
                                "sha256": feature_pack_sha256,
                            }
                        }
                    },
                },
            },
            sbom={
                "spdxVersion": "SPDX-2.3",
                "packages": [{"name": "odylith", "versionInfo": release.version}],
            },
            runtime_bundle_path=runtime_bundle_path,
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_path=wheel_path,
            verification=dict(release.verification),
        )
        self._verified_releases[release.version] = verified
        self._verified_feature_packs[release.version] = release_assets_module.VerifiedFeaturePack(
            asset_name=feature_pack_path.name,
            bundle_path=feature_pack_path,
            version=release.version,
            tag=f"v{release.version}",
            manifest=verified.manifest,
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            pack_id=CONTEXT_ENGINE_FEATURE_PACK_ID,
            verification={
                "feature_pack_id": CONTEXT_ENGINE_FEATURE_PACK_ID,
                "feature_pack_sha256": feature_pack_sha256,
                "manifest_sha256": f"manifest-{release.version}",
                "provenance_sha256": f"provenance-{release.version}",
                "sbom_sha256": f"sbom-{release.version}",
                "signer_identity": "https://github.com/freedom-research/odylith/.github/workflows/release.yml@refs/heads/main",
            },
        )
        return verified

    def install(self, version: str) -> int:
        token = str(version).strip()
        if token not in self._verified_releases:
            self.register_verified_release(token)
        return super().install(token)

    def _fake_download_verified_release(
        self,
        *,
        repo_root: str | Path,
        repo: str,
        version: str = "latest",
    ) -> release_assets_module.VerifiedRelease:
        if repo != "freedom-research/odylith":
            raise ValueError(f"unexpected fake release repo: {repo}")
        token = str(version or "").strip()
        if token == "latest":
            if not self._verified_releases:
                raise ValueError("no fake verified releases registered")
            source_release = max(self._verified_releases.values(), key=lambda release: _version_sort_key(release.version))
        else:
            try:
                source_release = self._verified_releases[token]
            except KeyError as exc:  # pragma: no cover - defensive guard for future sims
                raise ValueError(f"fake verified release {token!r} is not registered") from exc
        cache_dir = release_assets_module.release_cache_dir(repo_root=repo_root, version=source_release.version)
        cache_dir.mkdir(parents=True, exist_ok=True)
        wheel_path = cache_dir / source_release.wheel_path.name
        runtime_bundle_path = cache_dir / source_release.runtime_bundle_path.name
        shutil.copyfile(source_release.wheel_path, wheel_path)
        shutil.copyfile(source_release.runtime_bundle_path, runtime_bundle_path)
        return release_assets_module.VerifiedRelease(
            version=source_release.version,
            tag=source_release.tag,
            manifest=source_release.manifest,
            provenance=source_release.provenance,
            sbom=source_release.sbom,
            runtime_bundle_path=runtime_bundle_path,
            runtime_platform=source_release.runtime_platform,
            wheel_path=wheel_path,
            verification=source_release.verification,
        )

    def _fake_runtime_subprocess_run(self, command, *, check=False, capture_output=False, text=False, **kwargs):  # noqa: ANN001
        del kwargs
        argv = [str(token) for token in command]
        return self._fake_smoke_run(command, check=check, capture_output=capture_output, text=text)

    def _fake_download_verified_feature_pack(
        self,
        *,
        repo_root: str | Path,
        repo: str,
        version: str,
        pack_id: str = CONTEXT_ENGINE_FEATURE_PACK_ID,
    ) -> release_assets_module.VerifiedFeaturePack:
        if repo != "freedom-research/odylith":
            raise ValueError(f"unexpected fake release repo: {repo}")
        if pack_id != CONTEXT_ENGINE_FEATURE_PACK_ID:
            raise ValueError(f"unexpected fake feature pack id: {pack_id}")
        try:
            source_pack = self._verified_feature_packs[str(version).strip()]
        except KeyError as exc:  # pragma: no cover - defensive guard for future sims
            raise ValueError(f"fake verified feature pack {version!r} is not registered") from exc
        cache_dir = release_assets_module.release_cache_dir(repo_root=repo_root, version=source_pack.version)
        cache_dir.mkdir(parents=True, exist_ok=True)
        bundle_path = cache_dir / source_pack.bundle_path.name
        shutil.copyfile(source_pack.bundle_path, bundle_path)
        return release_assets_module.VerifiedFeaturePack(
            asset_name=source_pack.asset_name,
            bundle_path=bundle_path,
            manifest=source_pack.manifest,
            pack_id=source_pack.pack_id,
            runtime_platform=source_pack.runtime_platform,
            tag=source_pack.tag,
            verification=source_pack.verification,
            version=source_pack.version,
        )

    def runtime_install_marker(self, version: str) -> str:
        marker = repo_runtime_paths(self.repo_root).versions_dir / str(version).strip() / "installed-wheel.txt"
        return marker.read_text(encoding="utf-8").strip() if marker.is_file() else ""

    def _write_runtime_bundle(self, bundle_path: Path, *, marker: str) -> None:
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_root = bundle_path.parent / MANAGED_RUNTIME_ROOT_NAME
        python_path = runtime_root / "bin" / "python"
        python_path.parent.mkdir(parents=True, exist_ok=True)
        python_path.write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        python_path.chmod(0o755)
        (runtime_root / "bin" / "python3").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
        (runtime_root / "bin" / "python3").chmod(0o755)
        (runtime_root / "bin" / "odylith").write_text(
            "#!/usr/bin/env bash\nexec \"$(cd \"$(dirname \"$0\")\" && pwd)/python\" -m odylith.cli \"$@\"\n",
            encoding="utf-8",
        )
        (runtime_root / "bin" / "odylith").chmod(0o755)
        (runtime_root / "installed-wheel.txt").write_text(marker, encoding="utf-8")
        (runtime_root / "runtime-metadata.json").write_text(
            json.dumps(
                {
                    "schema_version": "odylith-runtime-bundle.v1",
                    "version": marker.removeprefix("odylith-").removesuffix("-py3-none-any.whl"),
                    "platform": "darwin-arm64",
                    "python_version": "3.13.12",
                    "source_wheel": marker,
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with tarfile.open(bundle_path, "w:gz") as archive:
            archive.add(runtime_root, arcname=MANAGED_RUNTIME_ROOT_NAME)
        for path in sorted(runtime_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        runtime_root.rmdir()

    def _write_feature_pack_bundle(self, bundle_path: Path) -> None:
        bundle_path.parent.mkdir(parents=True, exist_ok=True)
        runtime_root = bundle_path.parent / MANAGED_RUNTIME_ROOT_NAME
        feature_file = runtime_root / "lib" / "python3.13" / "site-packages" / "watchdog" / "__init__.py"
        feature_file.parent.mkdir(parents=True, exist_ok=True)
        feature_file.write_text("watchdog = True\n", encoding="utf-8")
        (runtime_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME).write_text(
            json.dumps(
                {
                    "schema_version": "odylith-runtime-feature-packs.v1",
                    "version": "",
                    "packs": {
                        CONTEXT_ENGINE_FEATURE_PACK_ID: {
                            "asset_name": bundle_path.name,
                            "display_name": "Odylith Context Engine memory pack",
                            "platform": "darwin-arm64",
                        }
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        with tarfile.open(bundle_path, "w:gz") as archive:
            archive.add(runtime_root, arcname=MANAGED_RUNTIME_ROOT_NAME)
        for path in sorted(runtime_root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            else:
                path.rmdir()
        runtime_root.rmdir()
