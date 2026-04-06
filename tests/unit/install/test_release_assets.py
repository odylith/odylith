from __future__ import annotations

import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest

from odylith.install import release_assets
from odylith.install.managed_runtime import managed_runtime_platform_by_slug


class _Response:
    def __init__(self, payload: bytes) -> None:
        self._stream = io.BytesIO(payload)

    def read(self, size: int = -1) -> bytes:
        return self._stream.read(size)

    def __enter__(self) -> "_Response":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        return None


def test_fetch_release_returns_api_assets_without_manifest_checksums(monkeypatch) -> None:
    api_payload = {
        "tag_name": "v1.2.3",
        "assets": [
            {"name": "odylith-1.2.3-py3-none-any.whl", "browser_download_url": "https://example.invalid/odylith.whl"},
            {"name": "release-manifest.json", "browser_download_url": "https://example.invalid/release-manifest.json"},
        ],
    }

    def _fake_urlopen(url: str, timeout: int | None = None):  # noqa: ANN001
        assert "api.github.com" in url
        assert timeout is not None
        return _Response(json.dumps(api_payload).encode("utf-8"))

    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    release = release_assets.fetch_release(
        repo_root=Path(__file__).resolve().parents[3],
        repo="odylith/odylith",
        version="latest",
    )

    assert release.version == "1.2.3"
    assert release.asset(r"odylith-1\.2\.3-.*\.whl").sha256 is None


def test_fetch_release_uses_github_token_for_api_requests(monkeypatch) -> None:
    api_payload = {
        "tag_name": "v1.2.3",
        "assets": [],
    }

    def _fake_urlopen(request, timeout: int | None = None):  # noqa: ANN001
        assert timeout is not None
        assert request.full_url == "https://api.github.com/repos/odylith/odylith/releases/latest"
        assert request.headers["Authorization"] == "Bearer token-value"
        assert request.headers["Accept"] == "application/vnd.github+json"
        return _Response(json.dumps(api_payload).encode("utf-8"))

    monkeypatch.setenv("GH_TOKEN", "token-value")
    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    release = release_assets.fetch_release(
        repo_root=Path(__file__).resolve().parents[3],
        repo="odylith/odylith",
        version="latest",
    )

    assert release.version == "1.2.3"


def test_fetch_release_with_local_base_url_exposes_manifest_and_sigstore_sidecars(monkeypatch) -> None:
    manifest_payload = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "assets": {
            "odylith-1.2.3-py3-none-any.whl": {"sha256": "wheel"},
            "build-provenance.v1.json": {"sha256": "prov"},
            "odylith.sbom.spdx.json": {"sha256": "sbom"},
            "odylith-runtime-darwin-arm64.tar.gz": {"sha256": "runtime"},
        },
    }

    def _fake_urlopen(url: str, timeout: int | None = None):  # noqa: ANN001
        assert url == "http://127.0.0.1:8123/release-manifest.json"
        assert timeout is not None
        return _Response(json.dumps(manifest_payload).encode("utf-8"))

    monkeypatch.setenv("ODYLITH_RELEASE_BASE_URL", "http://127.0.0.1:8123")
    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    repo_root = Path(__file__).resolve().parents[3]
    release = release_assets.fetch_release(repo_root=repo_root, repo="odylith/odylith", version="1.2.3")

    assert "release-manifest.json" in release.assets
    assert "release-manifest.json.sigstore.json" in release.assets
    assert "odylith-1.2.3-py3-none-any.whl.sigstore.json" in release.assets
    assert "build-provenance.v1.json.sigstore.json" in release.assets
    assert "odylith-runtime-darwin-arm64.tar.gz.sigstore.json" in release.assets


def test_fetch_release_allows_local_base_url_with_maintainer_root_override(monkeypatch, tmp_path: Path) -> None:
    manifest_payload = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "assets": {},
    }

    def _fake_urlopen(url: str, timeout: int | None = None):  # noqa: ANN001
        assert url == "http://127.0.0.1:8123/release-manifest.json"
        assert timeout is not None
        return _Response(json.dumps(manifest_payload).encode("utf-8"))

    monkeypatch.setenv("ODYLITH_RELEASE_BASE_URL", "http://127.0.0.1:8123")
    monkeypatch.setenv("ODYLITH_RELEASE_MAINTAINER_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    release = release_assets.fetch_release(repo_root=tmp_path, repo="odylith/odylith", version="1.2.3")

    assert release.version == "1.2.3"


def test_fetch_release_rejects_local_base_url_outside_product_repo(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ODYLITH_RELEASE_BASE_URL", "http://127.0.0.1:8123")

    with pytest.raises(ValueError, match="only supported in the Odylith product repo maintainer lane"):
        release_assets.fetch_release(repo_root=tmp_path, repo="odylith/odylith", version="1.2.3")


def test_download_asset_rejects_untrusted_or_insecure_urls(tmp_path: Path) -> None:
    asset = release_assets.ReleaseAsset(
        name="odylith.whl",
        download_url="http://example.invalid/odylith.whl",
    )

    with pytest.raises(ValueError, match="must use https"):
        release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=tmp_path / "odylith.whl")


def test_download_asset_refuses_symlink_destination(monkeypatch, tmp_path: Path) -> None:
    asset = release_assets.ReleaseAsset(
        name="odylith.whl",
        download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith.whl",
    )
    destination = tmp_path / "odylith.whl"
    destination.symlink_to(tmp_path / "elsewhere.whl")

    monkeypatch.setattr(
        release_assets.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _Response(b"wheel"),
    )

    with pytest.raises(ValueError, match="through symlink"):
        release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=destination)


def test_download_asset_rejects_localhost_override_outside_product_repo(monkeypatch, tmp_path: Path) -> None:
    asset = release_assets.ReleaseAsset(
        name="odylith.whl",
        download_url="http://127.0.0.1:8123/odylith.whl",
    )
    monkeypatch.setenv("ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST", "1")

    with pytest.raises(ValueError, match="only supported in the Odylith product repo maintainer lane"):
        release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=tmp_path / "odylith.whl")


def test_download_asset_allows_localhost_override_with_maintainer_root_override(
    monkeypatch, tmp_path: Path
) -> None:
    asset = release_assets.ReleaseAsset(
        name="odylith.whl",
        download_url="http://127.0.0.1:8123/odylith.whl",
    )
    monkeypatch.setenv("ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST", "1")
    monkeypatch.setenv("ODYLITH_RELEASE_MAINTAINER_ROOT", str(Path(__file__).resolve().parents[3]))
    monkeypatch.setattr(
        release_assets.urllib.request,
        "urlopen",
        lambda *args, **kwargs: _Response(b"wheel"),
    )

    observed = release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=tmp_path / "odylith.whl")

    assert observed.read_bytes() == b"wheel"


def test_download_asset_reuses_existing_sha_matched_payload_without_network(monkeypatch, tmp_path: Path) -> None:
    payload = b"runtime-bundle"
    destination = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    destination.write_bytes(payload)
    asset = release_assets.ReleaseAsset(
        name=destination.name,
        download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith-runtime-linux-x86_64.tar.gz",
        sha256=hashlib.sha256(payload).hexdigest(),
    )

    monkeypatch.setattr(
        release_assets.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network fetch should be skipped for matching cache")),
    )

    observed = release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=destination)

    assert observed == destination
    assert destination.read_bytes() == payload


def test_download_asset_retries_transient_network_failure(monkeypatch, tmp_path: Path) -> None:
    payload = b"runtime-bundle"
    destination = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    asset = release_assets.ReleaseAsset(
        name=destination.name,
        download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith-runtime-linux-x86_64.tar.gz",
        sha256=hashlib.sha256(payload).hexdigest(),
    )
    attempts = {"count": 0}

    def _fake_urlopen(url: str, timeout: int | None = None):  # noqa: ANN001
        del timeout
        assert url == asset.download_url
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise release_assets.urllib_error.URLError("temporary network issue")
        return _Response(payload)

    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(release_assets.time, "sleep", lambda *_: None)

    observed = release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=destination)

    assert observed == destination
    assert attempts["count"] == 2
    assert destination.read_bytes() == payload


def test_download_asset_uses_github_token_for_release_asset_requests(monkeypatch, tmp_path: Path) -> None:
    payload = b"runtime-bundle"
    destination = tmp_path / "odylith-runtime-linux-x86_64.tar.gz"
    asset = release_assets.ReleaseAsset(
        name=destination.name,
        download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith-runtime-linux-x86_64.tar.gz",
        sha256=hashlib.sha256(payload).hexdigest(),
    )

    def _fake_urlopen(request, timeout: int | None = None):  # noqa: ANN001
        assert timeout is not None
        assert request.full_url == asset.download_url
        assert request.headers["Authorization"] == "Bearer token-value"
        return _Response(payload)

    monkeypatch.setenv("GITHUB_TOKEN", "token-value")
    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    observed = release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=destination)

    assert observed == destination
    assert destination.read_bytes() == payload


def test_download_asset_cleans_temporary_files_after_failed_download(monkeypatch, tmp_path: Path) -> None:
    asset = release_assets.ReleaseAsset(
        name="odylith.whl",
        download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith.whl",
    )

    monkeypatch.setattr(
        release_assets.urllib.request,
        "urlopen",
        lambda *args, **kwargs: (_ for _ in ()).throw(release_assets.urllib_error.URLError("still broken")),
    )
    monkeypatch.setattr(release_assets.time, "sleep", lambda *_: None)

    with pytest.raises(ValueError, match="failed to download odylith.whl"):
        release_assets.download_asset(repo_root=tmp_path, asset=asset, destination=tmp_path / "odylith.whl")

    leftovers = sorted(path.name for path in tmp_path.glob(".odylith.whl*.tmp"))
    assert leftovers == []


def test_download_verified_release_validates_manifest_and_signed_assets(monkeypatch, tmp_path: Path) -> None:
    wheel_bytes = b"wheel-bytes"
    wheel_sha256 = hashlib.sha256(wheel_bytes).hexdigest()
    runtime_bundle_bytes = b"runtime-bundle-bytes"
    runtime_bundle_sha256 = hashlib.sha256(runtime_bundle_bytes).hexdigest()
    release = release_assets.ReleaseInfo(
        version="1.2.3",
        tag="v1.2.3",
        assets={
            "odylith-1.2.3-py3-none-any.whl": release_assets.ReleaseAsset(
                name="odylith-1.2.3-py3-none-any.whl",
                download_url="https://example.invalid/odylith.whl",
            ),
            "odylith-1.2.3-py3-none-any.whl.sigstore.json": release_assets.ReleaseAsset(
                name="odylith-1.2.3-py3-none-any.whl.sigstore.json",
                download_url="https://example.invalid/odylith.whl.sigstore.json",
            ),
            "release-manifest.json": release_assets.ReleaseAsset(
                name="release-manifest.json",
                download_url="https://example.invalid/release-manifest.json",
            ),
            "release-manifest.json.sigstore.json": release_assets.ReleaseAsset(
                name="release-manifest.json.sigstore.json",
                download_url="https://example.invalid/release-manifest.json.sigstore.json",
            ),
            "build-provenance.v1.json": release_assets.ReleaseAsset(
                name="build-provenance.v1.json",
                download_url="https://example.invalid/build-provenance.v1.json",
            ),
            "build-provenance.v1.json.sigstore.json": release_assets.ReleaseAsset(
                name="build-provenance.v1.json.sigstore.json",
                download_url="https://example.invalid/build-provenance.v1.json.sigstore.json",
            ),
            "odylith.sbom.spdx.json": release_assets.ReleaseAsset(
                name="odylith.sbom.spdx.json",
                download_url="https://example.invalid/odylith.sbom.spdx.json",
            ),
            "odylith.sbom.spdx.json.sigstore.json": release_assets.ReleaseAsset(
                name="odylith.sbom.spdx.json.sigstore.json",
                download_url="https://example.invalid/odylith.sbom.spdx.json.sigstore.json",
            ),
            "odylith-runtime-darwin-arm64.tar.gz": release_assets.ReleaseAsset(
                name="odylith-runtime-darwin-arm64.tar.gz",
                download_url="https://example.invalid/odylith-runtime-darwin-arm64.tar.gz",
            ),
            "odylith-runtime-darwin-arm64.tar.gz.sigstore.json": release_assets.ReleaseAsset(
                name="odylith-runtime-darwin-arm64.tar.gz.sigstore.json",
                download_url="https://example.invalid/odylith-runtime-darwin-arm64.tar.gz.sigstore.json",
            ),
            "odylith-runtime-linux-arm64.tar.gz": release_assets.ReleaseAsset(
                name="odylith-runtime-linux-arm64.tar.gz",
                download_url="https://example.invalid/odylith-runtime-linux-arm64.tar.gz",
            ),
            "odylith-runtime-linux-arm64.tar.gz.sigstore.json": release_assets.ReleaseAsset(
                name="odylith-runtime-linux-arm64.tar.gz.sigstore.json",
                download_url="https://example.invalid/odylith-runtime-linux-arm64.tar.gz.sigstore.json",
            ),
            "odylith-runtime-linux-x86_64.tar.gz": release_assets.ReleaseAsset(
                name="odylith-runtime-linux-x86_64.tar.gz",
                download_url="https://example.invalid/odylith-runtime-linux-x86_64.tar.gz",
            ),
            "odylith-runtime-linux-x86_64.tar.gz.sigstore.json": release_assets.ReleaseAsset(
                name="odylith-runtime-linux-x86_64.tar.gz.sigstore.json",
                download_url="https://example.invalid/odylith-runtime-linux-x86_64.tar.gz.sigstore.json",
            ),
        },
    )
    manifest_payload = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "repo_schema_version": 1,
        "migration_required": False,
        "supported_platforms": [
            "darwin-arm64",
            "linux-arm64",
            "linux-x86_64",
        ],
        "assets": {
            "odylith-1.2.3-py3-none-any.whl": {"sha256": wheel_sha256},
            "build-provenance.v1.json": {"sha256": "unused"},
            "odylith.sbom.spdx.json": {"sha256": "unused"},
            "odylith-runtime-darwin-arm64.tar.gz": {"sha256": runtime_bundle_sha256},
            "odylith-runtime-linux-arm64.tar.gz": {"sha256": runtime_bundle_sha256},
            "odylith-runtime-linux-x86_64.tar.gz": {"sha256": runtime_bundle_sha256},
        },
    }
    provenance_payload = {
        "version": "odylith-release-provenance.v1",
        "repo": "odylith/odylith",
        "actor": "freedom-research",
        "release_version": "1.2.3",
        "tag": "v1.2.3",
        "workflow": {
            "path": ".github/workflows/release.yml",
            "ref": "refs/heads/main",
        },
        "artifacts": {
            "wheel": {
                "name": "odylith-1.2.3-py3-none-any.whl",
                "sha256": wheel_sha256,
            },
            "runtime_bundles": {
                "darwin-arm64": {
                    "name": "odylith-runtime-darwin-arm64.tar.gz",
                    "sha256": runtime_bundle_sha256,
                },
                "linux-arm64": {
                    "name": "odylith-runtime-linux-arm64.tar.gz",
                    "sha256": runtime_bundle_sha256,
                },
                "linux-x86_64": {
                    "name": "odylith-runtime-linux-x86_64.tar.gz",
                    "sha256": runtime_bundle_sha256,
                },
            },
        },
    }
    sbom_payload = {
        "spdxVersion": "SPDX-2.3",
        "packages": [
            {
                "name": "odylith",
                "versionInfo": "1.2.3",
            }
        ],
    }
    verified_assets: list[str] = []

    def _fake_fetch_release(*, repo_root, repo: str, version: str = "latest"):  # noqa: ANN001
        assert repo_root == tmp_path
        assert repo == "odylith/odylith"
        assert version == "latest"
        return release

    def _fake_download_asset(*, repo_root, asset, destination: Path):  # noqa: ANN001
        assert repo_root == tmp_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        if asset.name == "release-manifest.json":
            destination.write_text(json.dumps(manifest_payload), encoding="utf-8")
        elif asset.name == "build-provenance.v1.json":
            destination.write_text(json.dumps(provenance_payload), encoding="utf-8")
        elif asset.name == "odylith.sbom.spdx.json":
            destination.write_text(json.dumps(sbom_payload), encoding="utf-8")
        elif asset.name.endswith(".tar.gz"):
            destination.write_bytes(runtime_bundle_bytes)
        elif asset.name.endswith(".sigstore.json"):
            destination.write_text("{}", encoding="utf-8")
        else:
            destination.write_bytes(wheel_bytes)
        return destination

    def _fake_verify_sigstore_asset(*, repo_root, asset_path: Path, bundle_path: Path, repo: str) -> None:
        assert repo_root == tmp_path
        assert repo == "odylith/odylith"
        assert bundle_path.name.endswith(".sigstore.json")
        verified_assets.append(asset_path.name)

    monkeypatch.setattr(release_assets, "fetch_release", _fake_fetch_release)
    monkeypatch.setattr(release_assets, "download_asset", _fake_download_asset)
    monkeypatch.setattr(release_assets, "verify_sigstore_asset", _fake_verify_sigstore_asset)
    monkeypatch.setattr(release_assets, "_validate_runtime_bundle_archive", lambda **kwargs: None)
    monkeypatch.setattr(
        release_assets,
        "detect_managed_runtime_platform",
        lambda: managed_runtime_platform_by_slug("darwin-arm64"),
    )

    verified = release_assets.download_verified_release(
        repo_root=tmp_path,
        repo="odylith/odylith",
        version="latest",
    )

    assert verified.version == "1.2.3"
    assert verified.manifest["repo_schema_version"] == 1
    assert verified.verification["wheel_sha256"] == wheel_sha256
    assert verified.verification["runtime_bundle_sha256"] == runtime_bundle_sha256
    assert verified.wheel_path.read_bytes() == wheel_bytes
    assert verified.runtime_platform.slug == "darwin-arm64"
    assert verified.runtime_bundle_path.read_bytes() == runtime_bundle_bytes
    assert verified_assets == [
        "release-manifest.json",
        "odylith-1.2.3-py3-none-any.whl",
        "build-provenance.v1.json",
        "odylith.sbom.spdx.json",
        "odylith-runtime-darwin-arm64.tar.gz",
    ]


def test_validate_provenance_rejects_untrusted_release_actor() -> None:
    with pytest.raises(ValueError, match="release provenance actor mismatch"):
        release_assets._validate_provenance(  # noqa: SLF001
            provenance={
                "version": "odylith-release-provenance.v1",
                "repo": "odylith/odylith",
                "actor": "someone-else",
                "release_version": "1.2.3",
                "tag": "v1.2.3",
                "workflow": {
                    "path": ".github/workflows/release.yml",
                    "ref": "refs/heads/main",
                },
                "artifacts": {
                    "wheel": {
                        "name": "odylith-1.2.3-py3-none-any.whl",
                        "sha256": "abc123",
                    },
                    "runtime_bundles": {
                        "darwin-arm64": {
                            "name": "odylith-runtime-darwin-arm64.tar.gz",
                            "sha256": "runtime-sha",
                        }
                    },
                },
            },
            repo="odylith/odylith",
            release=release_assets.ReleaseInfo(version="1.2.3", tag="v1.2.3", assets={}),
            runtime_bundle_name="odylith-runtime-darwin-arm64.tar.gz",
            runtime_bundle_sha256="runtime-sha",
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_name="odylith-1.2.3-py3-none-any.whl",
            wheel_sha256="abc123",
        )


def test_validate_manifest_rejects_partial_supported_platform_matrix() -> None:
    release = release_assets.ReleaseInfo(
        version="1.2.3",
        tag="v1.2.3",
        assets={
            "release-manifest.json": release_assets.ReleaseAsset("release-manifest.json", "https://example.invalid/release-manifest.json"),
            "release-manifest.json.sigstore.json": release_assets.ReleaseAsset("release-manifest.json.sigstore.json", "https://example.invalid/release-manifest.json.sigstore.json"),
            "build-provenance.v1.json": release_assets.ReleaseAsset("build-provenance.v1.json", "https://example.invalid/build-provenance.v1.json"),
            "build-provenance.v1.json.sigstore.json": release_assets.ReleaseAsset("build-provenance.v1.json.sigstore.json", "https://example.invalid/build-provenance.v1.json.sigstore.json"),
            "odylith.sbom.spdx.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json", "https://example.invalid/odylith.sbom.spdx.json"),
            "odylith.sbom.spdx.json.sigstore.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json.sigstore.json", "https://example.invalid/odylith.sbom.spdx.json.sigstore.json"),
            "odylith-1.2.3-py3-none-any.whl": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl", "https://example.invalid/odylith.whl"),
            "odylith-1.2.3-py3-none-any.whl.sigstore.json": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl.sigstore.json", "https://example.invalid/odylith.whl.sigstore.json"),
            "odylith-runtime-darwin-arm64.tar.gz": release_assets.ReleaseAsset("odylith-runtime-darwin-arm64.tar.gz", "https://example.invalid/odylith-runtime-darwin-arm64.tar.gz"),
            "odylith-runtime-darwin-arm64.tar.gz.sigstore.json": release_assets.ReleaseAsset("odylith-runtime-darwin-arm64.tar.gz.sigstore.json", "https://example.invalid/odylith-runtime-darwin-arm64.tar.gz.sigstore.json"),
        },
    )
    manifest = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "repo_schema_version": 1,
        "migration_required": False,
        "supported_platforms": ["darwin-arm64"],
        "assets": {
            "odylith-1.2.3-py3-none-any.whl": {"sha256": "wheel"},
            "odylith-runtime-darwin-arm64.tar.gz": {"sha256": "runtime"},
        },
    }

    with pytest.raises(ValueError, match="supported_platforms mismatch"):
        release_assets._validate_manifest(  # noqa: SLF001
            manifest=manifest,
            release=release,
            repo="odylith/odylith",
        )


def test_validate_manifest_rejects_sidecar_wheel_assets() -> None:
    release = release_assets.ReleaseInfo(
        version="1.2.3",
        tag="v1.2.3",
        assets={
            "release-manifest.json": release_assets.ReleaseAsset("release-manifest.json", "https://example.invalid/release-manifest.json"),
            "release-manifest.json.sigstore.json": release_assets.ReleaseAsset("release-manifest.json.sigstore.json", "https://example.invalid/release-manifest.json.sigstore.json"),
            "build-provenance.v1.json": release_assets.ReleaseAsset("build-provenance.v1.json", "https://example.invalid/build-provenance.v1.json"),
            "build-provenance.v1.json.sigstore.json": release_assets.ReleaseAsset("build-provenance.v1.json.sigstore.json", "https://example.invalid/build-provenance.v1.json.sigstore.json"),
            "odylith.sbom.spdx.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json", "https://example.invalid/odylith.sbom.spdx.json"),
            "odylith.sbom.spdx.json.sigstore.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json.sigstore.json", "https://example.invalid/odylith.sbom.spdx.json.sigstore.json"),
            "odylith-1.2.3-py3-none-any.whl": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl", "https://example.invalid/odylith.whl"),
            "odylith-1.2.3-py3-none-any.whl.sigstore.json": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl.sigstore.json", "https://example.invalid/odylith.whl.sigstore.json"),
            "odylith-tools-1.2.3-py3-none-any.whl": release_assets.ReleaseAsset("odylith-tools-1.2.3-py3-none-any.whl", "https://example.invalid/odylith-tools.whl"),
        },
    )
    manifest = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "repo_schema_version": 1,
        "migration_required": False,
        "assets": {
            "odylith-1.2.3-py3-none-any.whl": {"sha256": "wheel"},
        },
    }

    with pytest.raises(ValueError, match="must not expose sidecar wheel assets"):
        release_assets._validate_manifest(  # noqa: SLF001
            manifest=manifest,
            release=release,
            repo="odylith/odylith",
        )


def test_validate_manifest_rejects_missing_odylith_wheel_metadata() -> None:
    release = release_assets.ReleaseInfo(
        version="1.2.3",
        tag="v1.2.3",
        assets={
            "release-manifest.json": release_assets.ReleaseAsset("release-manifest.json", "https://example.invalid/release-manifest.json"),
            "release-manifest.json.sigstore.json": release_assets.ReleaseAsset("release-manifest.json.sigstore.json", "https://example.invalid/release-manifest.json.sigstore.json"),
            "build-provenance.v1.json": release_assets.ReleaseAsset("build-provenance.v1.json", "https://example.invalid/build-provenance.v1.json"),
            "build-provenance.v1.json.sigstore.json": release_assets.ReleaseAsset("build-provenance.v1.json.sigstore.json", "https://example.invalid/build-provenance.v1.json.sigstore.json"),
            "odylith.sbom.spdx.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json", "https://example.invalid/odylith.sbom.spdx.json"),
            "odylith.sbom.spdx.json.sigstore.json": release_assets.ReleaseAsset("odylith.sbom.spdx.json.sigstore.json", "https://example.invalid/odylith.sbom.spdx.json.sigstore.json"),
            "odylith-1.2.3-py3-none-any.whl": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl", "https://example.invalid/odylith.whl"),
            "odylith-1.2.3-py3-none-any.whl.sigstore.json": release_assets.ReleaseAsset("odylith-1.2.3-py3-none-any.whl.sigstore.json", "https://example.invalid/odylith.whl.sigstore.json"),
        },
    )
    manifest = {
        "schema_version": "odylith-release-manifest.v1",
        "version": "1.2.3",
        "tag": "v1.2.3",
        "repo": "odylith/odylith",
        "repo_schema_version": 1,
        "migration_required": False,
        "assets": {},
    }

    with pytest.raises(ValueError, match="missing Odylith wheel metadata"):
        release_assets._validate_manifest(  # noqa: SLF001
            manifest=manifest,
            release=release,
            repo="odylith/odylith",
        )


def test_verify_sigstore_asset_scrubs_python_environment(monkeypatch, tmp_path: Path) -> None:
    asset_path = tmp_path / "asset.txt"
    bundle_path = tmp_path / "asset.txt.sigstore.json"
    asset_path.write_text("payload\n", encoding="utf-8")
    bundle_path.write_text("{}\n", encoding="utf-8")
    captured: dict[str, object] = {}

    def _fake_run(command, check, capture_output, text, env):  # noqa: ANN001
        captured["command"] = command
        captured["env"] = env
        return type("Result", (), {"returncode": 0, "stdout": "", "stderr": ""})()

    monkeypatch.setattr(release_assets.subprocess, "run", _fake_run)

    release_assets.verify_sigstore_asset(
        repo_root=tmp_path,
        asset_path=asset_path,
        bundle_path=bundle_path,
        repo="odylith/odylith",
    )

    env = captured["env"]
    assert isinstance(env, dict)
    assert env["PYTHONNOUSERSITE"] == "1"
    assert "VIRTUAL_ENV" not in env
    assert "CONDA_PREFIX" not in env
    assert "CONDA_DEFAULT_ENV" not in env
    assert "PYTHONHOME" not in env
    assert "__PYVENV_LAUNCHER__" not in env
    assert "PYTHONPATH" not in env


def test_verify_sigstore_asset_rejects_skip_override_outside_product_repo(monkeypatch, tmp_path: Path) -> None:
    asset_path = tmp_path / "asset.txt"
    bundle_path = tmp_path / "asset.txt.sigstore.json"
    asset_path.write_text("payload\n", encoding="utf-8")
    bundle_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY", "1")

    with pytest.raises(ValueError, match="only supported in the Odylith product repo maintainer lane"):
        release_assets.verify_sigstore_asset(
            repo_root=tmp_path,
            asset_path=asset_path,
            bundle_path=bundle_path,
            repo="odylith/odylith",
        )


def test_verify_sigstore_asset_allows_skip_override_with_maintainer_root_override(
    monkeypatch, tmp_path: Path
) -> None:
    asset_path = tmp_path / "asset.txt"
    bundle_path = tmp_path / "asset.txt.sigstore.json"
    asset_path.write_text("payload\n", encoding="utf-8")
    bundle_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setenv("ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY", "1")
    monkeypatch.setenv("ODYLITH_RELEASE_MAINTAINER_ROOT", str(Path(__file__).resolve().parents[3]))

    release_assets.verify_sigstore_asset(
        repo_root=tmp_path,
        asset_path=asset_path,
        bundle_path=bundle_path,
        repo="odylith/odylith",
    )


def test_validate_runtime_bundle_archive_rejects_metadata_platform_mismatch(tmp_path: Path) -> None:
    bundle_path = tmp_path / "odylith-runtime-darwin-arm64.tar.gz"
    runtime_root = tmp_path / "runtime"
    (runtime_root / "bin").mkdir(parents=True, exist_ok=True)
    (runtime_root / "bin" / "python").write_text("", encoding="utf-8")
    (runtime_root / "bin" / "python3").write_text("", encoding="utf-8")
    (runtime_root / "bin" / "odylith").write_text("", encoding="utf-8")
    (runtime_root / "runtime-metadata.json").write_text(
        json.dumps(
            {
                "schema_version": "odylith-runtime-bundle.v1",
                "version": "1.2.3",
                "platform": "linux-x86_64",
            }
        ),
        encoding="utf-8",
    )
    with tarfile.open(bundle_path, "w:gz") as archive:
        archive.add(runtime_root, arcname="runtime")

    with pytest.raises(ValueError, match="metadata platform mismatch"):
        release_assets._validate_runtime_bundle_archive(  # noqa: SLF001
            runtime_bundle_path=bundle_path,
            release=release_assets.ReleaseInfo(version="1.2.3", tag="v1.2.3", assets={}),
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_name="odylith-1.2.3-py3-none-any.whl",
        )


def test_validate_runtime_bundle_archive_rejects_unsafe_member_path(tmp_path: Path) -> None:
    bundle_path = tmp_path / "odylith-runtime-darwin-arm64.tar.gz"
    with tarfile.open(bundle_path, "w:gz") as archive:
        metadata_bytes = json.dumps(
            {
                "schema_version": "odylith-runtime-bundle.v1",
                "version": "1.2.3",
                "platform": "darwin-arm64",
                "python_version": "3.13.12",
                "source_wheel": "odylith-1.2.3-py3-none-any.whl",
            }
        ).encode("utf-8")
        for name, payload in {
            "runtime/bin/python": b"",
            "runtime/bin/python3": b"",
            "runtime/bin/odylith": b"",
            "runtime/runtime-metadata.json": metadata_bytes,
            "../escape": b"bad",
        }.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))

    with pytest.raises(ValueError, match="unsafe member path"):
        release_assets._validate_runtime_bundle_archive(  # noqa: SLF001
            runtime_bundle_path=bundle_path,
            release=release_assets.ReleaseInfo(version="1.2.3", tag="v1.2.3", assets={}),
            runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
            wheel_name="odylith-1.2.3-py3-none-any.whl",
        )


def test_validate_runtime_bundle_archive_allows_in_tree_relative_symlink(tmp_path: Path) -> None:
    bundle_path = tmp_path / "odylith-runtime-darwin-arm64.tar.gz"
    metadata_bytes = json.dumps(
        {
            "schema_version": "odylith-runtime-bundle.v1",
            "version": "1.2.3",
            "platform": "darwin-arm64",
            "python_version": "3.13.12",
            "source_wheel": "odylith-1.2.3-py3-none-any.whl",
        }
    ).encode("utf-8")
    with tarfile.open(bundle_path, "w:gz") as archive:
        for name, payload in {
            "runtime/bin/python": b"",
            "runtime/bin/python3": b"",
            "runtime/bin/odylith": b"",
            "runtime/runtime-metadata.json": metadata_bytes,
            "runtime/lib/terminfo-target": b"ok",
        }.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        link = tarfile.TarInfo(name="runtime/share/terminfo/link")
        link.type = tarfile.SYMTYPE
        link.linkname = "../../lib/terminfo-target"
        archive.addfile(link)

    release_assets._validate_runtime_bundle_archive(  # noqa: SLF001
        runtime_bundle_path=bundle_path,
        release=release_assets.ReleaseInfo(version="1.2.3", tag="v1.2.3", assets={}),
        runtime_platform=managed_runtime_platform_by_slug("darwin-arm64"),
        wheel_name="odylith-1.2.3-py3-none-any.whl",
    )


def test_download_asset_rejects_checksum_mismatch(monkeypatch, tmp_path: Path) -> None:
    payload = b"wheel-bytes"

    def _fake_urlopen(url: str, timeout: int | None = None):  # noqa: ANN001
        assert url == "https://github.com/odylith/odylith/releases/download/v1.2.3/odylith.whl"
        assert timeout is not None
        return _Response(payload)

    monkeypatch.setattr(release_assets.urllib.request, "urlopen", _fake_urlopen)

    with pytest.raises(ValueError, match="sha256 mismatch"):
        release_assets.download_asset(
            repo_root=tmp_path,
            asset=release_assets.ReleaseAsset(
                name="odylith.whl",
                download_url="https://github.com/odylith/odylith/releases/download/v1.2.3/odylith.whl",
                sha256="deadbeef",
            ),
            destination=tmp_path / "odylith.whl",
        )
