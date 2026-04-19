"""Release asset discovery, verification, and download helpers."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.request
from urllib import error as urllib_error
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from odylith.common.json_objects import JsonObjectLoadError, read_json_object
from odylith.common.release_text import normalize_release_text
from odylith.install.archive_safety import validate_archive_members
from odylith.install.fs import fsync_directory
from odylith.install.managed_runtime import (
    CONTEXT_ENGINE_FEATURE_PACK_ID,
    MANAGED_PYTHON_VERSION,
    MANAGED_RUNTIME_ROOT_NAME,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    ManagedRuntimePlatform,
    managed_runtime_feature_pack_by_id,
    managed_runtime_platform_by_slug,
    require_managed_runtime_platform,
    supported_feature_pack_ids,
    supported_platform_slugs,
)
from odylith.install.paths import repo_runtime_paths
from odylith.install.python_env import scrubbed_python_env
from odylith.install.state import (
    AUTHORITATIVE_RELEASE_ACTOR,
    AUTHORITATIVE_RELEASE_REPO,
    SIGNER_OIDC_ISSUER,
    SIGNER_WORKFLOW_PATH,
    SIGNER_WORKFLOW_REF,
)

_TAG_RE = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.\-]+)?)$")
_ALLOWED_RELEASE_URL_HOSTS = {
    "api.github.com",
    "github.com",
    "objects.githubusercontent.com",
    "release-assets.githubusercontent.com",
}
_LOCAL_RELEASE_BASE_URL_ENV = "ODYLITH_RELEASE_BASE_URL"
_ALLOW_INSECURE_LOCAL_RELEASES_ENV = "ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST"
_SKIP_SIGSTORE_VERIFY_ENV = "ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY"
_MAINTAINER_ROOT_ENV = "ODYLITH_RELEASE_MAINTAINER_ROOT"
_GITHUB_TOKEN_ENV_NAMES = ("GH_TOKEN", "GITHUB_TOKEN")
_URL_TIMEOUT_SECONDS = 30
_DOWNLOAD_CHUNK_BYTES = 1024 * 1024
_DOWNLOAD_RETRY_ATTEMPTS = 3
_DOWNLOAD_RETRYABLE_HTTP_CODES = {408, 429, 500, 502, 503, 504}
_BENIGN_SIGSTORE_WARNING_PATTERNS = (
    re.compile(r"unsupported(?:\s+\S+:\d+)?\s+key type:\s*7", re.IGNORECASE),
    re.compile(r"\btuf\b.*\boffline\b", re.IGNORECASE),
    re.compile(r"\boffline\b.*\btuf\b", re.IGNORECASE),
)


@dataclass(frozen=True)
class ReleaseAsset:
    name: str
    download_url: str
    sha256: str | None = None


@dataclass(frozen=True)
class ReleaseInfo:
    version: str
    tag: str
    assets: dict[str, ReleaseAsset]
    body: str = ""
    html_url: str = ""
    published_at: str = ""
    highlights: tuple[str, ...] = ()

    def asset(self, pattern: str) -> ReleaseAsset:
        compiled = re.compile(pattern)
        for name, asset in self.assets.items():
            if compiled.fullmatch(name):
                return asset
        raise ValueError(f"release asset matching {pattern!r} not found for {self.tag}")


@dataclass(frozen=True)
class SigstoreVerificationResult:
    warnings_suppressed: bool = False


@dataclass(frozen=True)
class VerifiedRelease:
    version: str
    tag: str
    manifest: dict[str, Any]
    provenance: dict[str, Any]
    sbom: dict[str, Any]
    runtime_bundle_path: Path
    runtime_platform: ManagedRuntimePlatform
    wheel_path: Path
    verification: dict[str, object]


@dataclass(frozen=True)
class VerifiedFeaturePack:
    asset_name: str
    bundle_path: Path
    manifest: dict[str, Any]
    pack_id: str
    runtime_platform: ManagedRuntimePlatform
    tag: str
    verification: dict[str, object]
    version: str


def _release_highlights(*, explicit: Any = None, body: str = "", limit: int = 3) -> tuple[str, ...]:
    highlights: list[str] = []
    if isinstance(explicit, (list, tuple)):
        for item in explicit:
            token = normalize_release_text(item, limit=180, strip_html=False)
            if token and token not in highlights:
                highlights.append(token)
            if len(highlights) >= limit:
                return tuple(highlights[:limit])
    body_text = str(body or "").strip()
    if not body_text:
        return tuple(highlights[:limit])
    for raw_line in body_text.splitlines():
        line = str(raw_line or "").strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith(("- ", "* ", "+ ")):
            line = line[2:].strip()
        else:
            numbered = re.match(r"^\d+\.\s+(?P<text>.+)$", line)
            if numbered:
                line = str(numbered.group("text") or "").strip()
        token = normalize_release_text(line, limit=180, strip_html=False)
        if token and token not in highlights:
            highlights.append(token)
        if len(highlights) >= limit:
            break
    if highlights:
        return tuple(highlights[:limit])
    paragraphs = [segment.strip() for segment in re.split(r"\n\s*\n", body_text) if segment.strip()]
    for paragraph in paragraphs:
        token = normalize_release_text(paragraph, limit=180, strip_html=False)
        if token and token not in highlights:
            highlights.append(token)
        if len(highlights) >= limit:
            break
    return tuple(highlights[:limit])


def _is_product_repo(repo_root: str | Path) -> bool:
    root = Path(repo_root).expanduser().resolve()
    return (
        (root / "pyproject.toml").is_file()
        and (root / "src" / "odylith").is_dir()
        and (root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
        and (root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    )


def _is_maintainer_release_lane(repo_root: str | Path) -> bool:
    if _is_product_repo(repo_root):
        return True
    maintainer_root = str(os.environ.get(_MAINTAINER_ROOT_ENV) or "").strip()
    if not maintainer_root:
        return False
    return _is_product_repo(maintainer_root)


def fetch_release(*, repo_root: str | Path, repo: str, version: str = "latest") -> ReleaseInfo:
    local_release_base_url = str(os.environ.get(_LOCAL_RELEASE_BASE_URL_ENV) or "").strip().rstrip("/")
    if local_release_base_url:
        if not _is_maintainer_release_lane(repo_root):
            raise ValueError("ODYLITH_RELEASE_BASE_URL is only supported in the Odylith product repo maintainer lane")
        manifest_url = f"{local_release_base_url}/release-manifest.json"
        with urllib.request.urlopen(manifest_url, timeout=_URL_TIMEOUT_SECONDS) as response:  # noqa: S310 - explicit local maintainer preflight override
            manifest = json.loads(response.read().decode("utf-8"))
        if not isinstance(manifest, dict):
            raise ValueError("local release manifest must be a JSON object")
        tag = str(manifest.get("tag") or "").strip()
        match = _TAG_RE.match(tag)
        if not match:
            raise ValueError(f"unexpected local release tag format: {tag!r}")
        resolved_version = match.group("version")
        if version != "latest" and resolved_version != str(version).strip():
            raise ValueError(f"local release manifest version mismatch: {resolved_version!r} != {version!r}")
        asset_manifest = manifest.get("assets")
        if not isinstance(asset_manifest, dict):
            raise ValueError("local release manifest assets must be an object")
        release_body = str(manifest.get("release_notes") or "").strip()
        published_at = str(manifest.get("published_at") or "").strip()
        html_url = str(manifest.get("html_url") or "").strip()
        explicit_highlights = manifest.get("release_highlights")
        asset_names = {
            "release-manifest.json",
            "release-manifest.json.sigstore.json",
            *(str(name).strip() for name in asset_manifest),
        }
        asset_names.update(
            f"{name}.sigstore.json"
            for name in list(asset_names)
            if name and not name.endswith(".sigstore.json")
        )
        assets = {
            name: ReleaseAsset(
                name=name,
                download_url=f"{local_release_base_url}/{name}",
            )
            for name in sorted(asset_names)
        }
        return ReleaseInfo(
            version=resolved_version,
            tag=tag,
            assets=assets,
            body=release_body,
            html_url=html_url,
            published_at=published_at,
            highlights=_release_highlights(explicit=explicit_highlights, body=release_body),
        )

    api_path = "latest" if version == "latest" else f"tags/v{version}"
    url = f"https://api.github.com/repos/{repo}/releases/{api_path}"
    with _urlopen_release_url(url, timeout=_URL_TIMEOUT_SECONDS) as response:  # noqa: S310 - trusted GitHub API endpoint
        payload = json.loads(response.read().decode("utf-8"))
    tag = str(payload.get("tag_name") or "").strip()
    match = _TAG_RE.match(tag)
    if not match:
        raise ValueError(f"unexpected release tag format: {tag!r}")
    auth_token = _github_auth_token()
    assets = {
        str(asset["name"]): ReleaseAsset(
            name=str(asset["name"]),
            download_url=_preferred_release_asset_url(asset=asset, auth_token=auth_token),
        )
        for asset in payload.get("assets", [])
    }
    body = str(payload.get("body") or "").strip()
    return ReleaseInfo(
        version=match.group("version"),
        tag=tag,
        assets=assets,
        body=body,
        html_url=str(payload.get("html_url") or "").strip(),
        published_at=str(payload.get("published_at") or "").strip(),
        highlights=_release_highlights(body=body),
    )


def download_verified_release(*, repo_root: str | Path, repo: str, version: str = "latest") -> VerifiedRelease:
    release = fetch_release(repo_root=repo_root, repo=repo, version=version)
    runtime_platform = require_managed_runtime_platform()
    cache_dir = release_cache_dir(repo_root=repo_root, version=release.version)
    cache_dir.mkdir(parents=True, exist_ok=True)

    verification_results: list[SigstoreVerificationResult] = []
    manifest_path = download_asset(
        repo_root=repo_root,
        asset=release.assets["release-manifest.json"],
        destination=cache_dir / "release-manifest.json",
    )
    manifest_bundle_path = download_asset(
        repo_root=repo_root,
        asset=release.assets["release-manifest.json.sigstore.json"],
        destination=cache_dir / "release-manifest.json.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=manifest_path, bundle_path=manifest_bundle_path, repo=repo)
        )
    )
    manifest = _load_json(manifest_path)
    _validate_manifest(manifest=manifest, release=release, repo=repo)

    verified_assets = _assets_from_manifest(release=release, manifest=manifest)
    wheel_asset = verified_assets.assets[_odylith_wheel_asset_name(release=verified_assets)]
    provenance_asset = verified_assets.assets["build-provenance.v1.json"]
    sbom_asset = verified_assets.assets["odylith.sbom.spdx.json"]
    runtime_bundle_asset = verified_assets.assets[runtime_platform.asset_name]

    wheel_path = download_asset(repo_root=repo_root, asset=wheel_asset, destination=cache_dir / wheel_asset.name)
    wheel_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{wheel_asset.name}.sigstore.json"],
        destination=cache_dir / f"{wheel_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=wheel_path, bundle_path=wheel_bundle_path, repo=repo)
        )
    )

    provenance_path = download_asset(repo_root=repo_root, asset=provenance_asset, destination=cache_dir / provenance_asset.name)
    provenance_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{provenance_asset.name}.sigstore.json"],
        destination=cache_dir / f"{provenance_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=provenance_path, bundle_path=provenance_bundle_path, repo=repo)
        )
    )
    provenance = _load_json(provenance_path)

    sbom_path = download_asset(repo_root=repo_root, asset=sbom_asset, destination=cache_dir / sbom_asset.name)
    sbom_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{sbom_asset.name}.sigstore.json"],
        destination=cache_dir / f"{sbom_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=sbom_path, bundle_path=sbom_bundle_path, repo=repo)
        )
    )
    sbom = _load_json(sbom_path)

    runtime_bundle_path = download_asset(repo_root=repo_root, asset=runtime_bundle_asset, destination=cache_dir / runtime_bundle_asset.name)
    runtime_bundle_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{runtime_bundle_asset.name}.sigstore.json"],
        destination=cache_dir / f"{runtime_bundle_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(
                repo_root=repo_root,
                asset_path=runtime_bundle_path,
                bundle_path=runtime_bundle_bundle_path,
                repo=repo,
            )
        )
    )
    _emit_sigstore_success_notice(verification_results, context="release")

    wheel_sha256 = _sha256_file(wheel_path)
    expected_wheel_sha = str(manifest["assets"][wheel_asset.name]["sha256"]).strip()
    if wheel_sha256 != expected_wheel_sha:
        raise ValueError(f"wheel sha256 mismatch for {wheel_asset.name}: {wheel_sha256} != {expected_wheel_sha}")
    runtime_bundle_sha256 = _sha256_file(runtime_bundle_path)
    expected_runtime_bundle_sha = str(manifest["assets"][runtime_bundle_asset.name]["sha256"]).strip()
    if runtime_bundle_sha256 != expected_runtime_bundle_sha:
        raise ValueError(
            f"runtime bundle sha256 mismatch for {runtime_bundle_asset.name}: {runtime_bundle_sha256} != {expected_runtime_bundle_sha}"
        )
    _validate_provenance(
        provenance=provenance,
        repo=repo,
        release=release,
        runtime_bundle_name=runtime_bundle_asset.name,
        runtime_bundle_sha256=runtime_bundle_sha256,
        runtime_platform=runtime_platform,
        wheel_name=wheel_asset.name,
        wheel_sha256=wheel_sha256,
    )
    _validate_sbom(sbom=sbom, release=release)
    _validate_runtime_bundle_archive(
        runtime_bundle_path=runtime_bundle_path,
        release=release,
        runtime_platform=runtime_platform,
        wheel_name=wheel_asset.name,
    )

    verification = {
        "manifest_sha256": _sha256_file(manifest_path),
        "oidc_issuer": SIGNER_OIDC_ISSUER,
        "provenance_sha256": _sha256_file(provenance_path),
        "runtime_bundle_platform": runtime_platform.slug,
        "runtime_bundle_sha256": runtime_bundle_sha256,
        "sbom_sha256": _sha256_file(sbom_path),
        "signer_identity": expected_signer_identity(repo=repo),
        "wheel_sha256": wheel_sha256,
    }
    return VerifiedRelease(
        version=release.version,
        tag=release.tag,
        manifest=manifest,
        provenance=provenance,
        sbom=sbom,
        runtime_bundle_path=runtime_bundle_path,
        runtime_platform=runtime_platform,
        wheel_path=wheel_path,
        verification=verification,
    )


def download_verified_feature_pack(
    *,
    repo_root: str | Path,
    repo: str,
    version: str,
    pack_id: str = CONTEXT_ENGINE_FEATURE_PACK_ID,
) -> VerifiedFeaturePack:
    release = fetch_release(repo_root=repo_root, repo=repo, version=version)
    runtime_platform = require_managed_runtime_platform()
    cache_dir = release_cache_dir(repo_root=repo_root, version=release.version)
    cache_dir.mkdir(parents=True, exist_ok=True)

    verification_results: list[SigstoreVerificationResult] = []
    manifest_path = download_asset(
        repo_root=repo_root,
        asset=release.assets["release-manifest.json"],
        destination=cache_dir / "release-manifest.json",
    )
    manifest_bundle_path = download_asset(
        repo_root=repo_root,
        asset=release.assets["release-manifest.json.sigstore.json"],
        destination=cache_dir / "release-manifest.json.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=manifest_path, bundle_path=manifest_bundle_path, repo=repo)
        )
    )
    manifest = _load_json(manifest_path)
    _validate_manifest(manifest=manifest, release=release, repo=repo)

    verified_assets = _assets_from_manifest(release=release, manifest=manifest)
    provenance_asset = verified_assets.assets["build-provenance.v1.json"]
    sbom_asset = verified_assets.assets["odylith.sbom.spdx.json"]
    feature_pack_asset = _feature_pack_asset(
        release=verified_assets,
        manifest=manifest,
        pack_id=pack_id,
        runtime_platform=runtime_platform,
    )

    provenance_path = download_asset(repo_root=repo_root, asset=provenance_asset, destination=cache_dir / provenance_asset.name)
    provenance_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{provenance_asset.name}.sigstore.json"],
        destination=cache_dir / f"{provenance_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=provenance_path, bundle_path=provenance_bundle_path, repo=repo)
        )
    )
    provenance = _load_json(provenance_path)

    sbom_path = download_asset(repo_root=repo_root, asset=sbom_asset, destination=cache_dir / sbom_asset.name)
    sbom_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{sbom_asset.name}.sigstore.json"],
        destination=cache_dir / f"{sbom_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=sbom_path, bundle_path=sbom_bundle_path, repo=repo)
        )
    )

    feature_pack_path = download_asset(repo_root=repo_root, asset=feature_pack_asset, destination=cache_dir / feature_pack_asset.name)
    feature_pack_bundle_path = download_asset(
        repo_root=repo_root,
        asset=verified_assets.assets[f"{feature_pack_asset.name}.sigstore.json"],
        destination=cache_dir / f"{feature_pack_asset.name}.sigstore.json",
    )
    verification_results.append(
        _normalize_sigstore_result(
            verify_sigstore_asset(repo_root=repo_root, asset_path=feature_pack_path, bundle_path=feature_pack_bundle_path, repo=repo)
        )
    )
    _emit_sigstore_success_notice(verification_results, context="feature-pack")

    feature_pack_sha256 = _sha256_file(feature_pack_path)
    expected_feature_pack_sha = str(manifest["assets"][feature_pack_asset.name]["sha256"]).strip()
    if feature_pack_sha256 != expected_feature_pack_sha:
        raise ValueError(
            f"feature pack sha256 mismatch for {feature_pack_asset.name}: {feature_pack_sha256} != {expected_feature_pack_sha}"
        )
    _validate_feature_pack_provenance(
        provenance=provenance,
        pack_id=pack_id,
        repo=repo,
        release=release,
        runtime_platform=runtime_platform,
        feature_pack_name=feature_pack_asset.name,
        feature_pack_sha256=feature_pack_sha256,
    )
    _validate_feature_pack_archive(bundle_path=feature_pack_path)
    verification = {
        "feature_pack_id": pack_id,
        "feature_pack_sha256": feature_pack_sha256,
        "manifest_sha256": _sha256_file(manifest_path),
        "oidc_issuer": SIGNER_OIDC_ISSUER,
        "provenance_sha256": _sha256_file(provenance_path),
        "runtime_bundle_platform": runtime_platform.slug,
        "sbom_sha256": _sha256_file(sbom_path),
        "signer_identity": expected_signer_identity(repo=repo),
    }
    return VerifiedFeaturePack(
        asset_name=feature_pack_asset.name,
        bundle_path=feature_pack_path,
        manifest=manifest,
        pack_id=pack_id,
        runtime_platform=runtime_platform,
        tag=release.tag,
        verification=verification,
        version=release.version,
    )


def expected_signer_identity(*, repo: str) -> str:
    return f"https://github.com/{repo}/{SIGNER_WORKFLOW_PATH}@{SIGNER_WORKFLOW_REF}"


def verify_sigstore_asset(*, repo_root: str | Path, asset_path: Path, bundle_path: Path, repo: str) -> SigstoreVerificationResult:
    if str(os.environ.get(_SKIP_SIGSTORE_VERIFY_ENV, "")).strip() == "1":
        if not _is_maintainer_release_lane(repo_root):
            raise ValueError("ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY is only supported in the Odylith product repo maintainer lane")
        return SigstoreVerificationResult(warnings_suppressed=False)
    command = [
        sys.executable,
        "-I",
        "-m",
        "sigstore",
        "verify",
        "identity",
        str(asset_path),
        "--bundle",
        str(bundle_path),
        "--cert-identity",
        expected_signer_identity(repo=repo),
        "--cert-oidc-issuer",
        SIGNER_OIDC_ISSUER,
    ]
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=scrubbed_python_env(),
    )
    if completed.returncode != 0:
        stderr = completed.stderr.strip()
        stdout = completed.stdout.strip()
        details = stderr or stdout or "sigstore verification failed"
        raise ValueError(f"failed to verify {asset_path.name}: {details}")
    stderr = completed.stderr.strip()
    if not stderr:
        return SigstoreVerificationResult(warnings_suppressed=False)
    stderr_lines = _fold_sigstore_warning_lines(stderr)
    if all(_is_benign_sigstore_warning(line) for line in stderr_lines):
        return SigstoreVerificationResult(warnings_suppressed=True)
    print(stderr, file=sys.stderr)
    return SigstoreVerificationResult(warnings_suppressed=False)


def _fold_sigstore_warning_lines(stderr: str) -> list[str]:
    folded: list[str] = []
    for raw_line in str(stderr or "").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if folded and raw_line[:1].isspace():
            folded[-1] = f"{folded[-1]} {stripped}"
            continue
        folded.append(stripped)
    return folded


def _is_benign_sigstore_warning(line: str) -> bool:
    normalized = re.sub(r"\s+", " ", str(line or "").strip())
    return any(pattern.search(normalized) is not None for pattern in _BENIGN_SIGSTORE_WARNING_PATTERNS)


def _normalize_sigstore_result(result: SigstoreVerificationResult | None) -> SigstoreVerificationResult:
    if isinstance(result, SigstoreVerificationResult):
        return result
    return SigstoreVerificationResult(warnings_suppressed=False)


def _emit_sigstore_success_notice(results: list[SigstoreVerificationResult], *, context: str) -> None:
    suppressed_count = sum(1 for result in results if result.warnings_suppressed)
    if suppressed_count <= 0:
        return
    print(
        f"Sigstore verification succeeded for the {context} assets; suppressed {suppressed_count} expected non-fatal warning stream(s)."
    )


def download_asset(*, repo_root: str | Path, asset: ReleaseAsset, destination: Path) -> Path:
    _validate_release_asset_url(repo_root=repo_root, url=asset.download_url)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise ValueError(f"refusing to write release asset through symlink: {destination}")
    if destination.is_file() and asset.sha256:
        existing_digest = _sha256_file(destination)
        if existing_digest == asset.sha256:
            return destination
    last_error: Exception | None = None
    for attempt in range(1, _DOWNLOAD_RETRY_ATTEMPTS + 1):
        try:
            return _download_asset_once(asset=asset, destination=destination)
        except ValueError:
            raise
        except Exception as exc:
            last_error = exc
            if attempt >= _DOWNLOAD_RETRY_ATTEMPTS or not _is_retryable_download_error(exc):
                raise ValueError(f"failed to download {asset.name}: {exc}") from exc
            time.sleep(float(attempt))
    raise ValueError(f"failed to download {asset.name}: {last_error}")


def _validate_release_asset_url(*, repo_root: str | Path, url: str) -> None:
    parsed = urlparse(str(url))
    allow_local_http = (
        str(os.environ.get(_ALLOW_INSECURE_LOCAL_RELEASES_ENV, "")).strip() == "1"
        and _is_maintainer_release_lane(repo_root)
    )
    if (
        str(os.environ.get(_ALLOW_INSECURE_LOCAL_RELEASES_ENV, "")).strip() == "1"
        and not _is_maintainer_release_lane(repo_root)
    ):
        raise ValueError("ODYLITH_RELEASE_ALLOW_INSECURE_LOCALHOST is only supported in the Odylith product repo maintainer lane")
    hostname = str(parsed.hostname or "").strip().lower()
    if parsed.scheme != "https":
        if not (allow_local_http and parsed.scheme == "http" and hostname in {"127.0.0.1", "localhost", "::1"}):
            raise ValueError(f"release asset URL must use https: {url}")
    if not hostname:
        raise ValueError(f"release asset URL host missing: {url}")
    if allow_local_http and hostname in {"127.0.0.1", "localhost", "::1"}:
        return
    if hostname in _ALLOWED_RELEASE_URL_HOSTS:
        return
    if hostname.endswith(".githubusercontent.com"):
        return
    raise ValueError(f"release asset URL host is not trusted: {url}")


def _download_asset_once(*, asset: ReleaseAsset, destination: Path) -> Path:
    fd, temp_name = tempfile.mkstemp(prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent))
    temporary_destination = Path(temp_name)
    try:
        hasher = hashlib.sha256() if asset.sha256 else None
        with _urlopen_release_url(asset.download_url, timeout=_URL_TIMEOUT_SECONDS) as response:  # noqa: S310 - trusted GitHub release asset URL
            with os.fdopen(fd, "wb") as handle:
                while True:
                    chunk = response.read(_DOWNLOAD_CHUNK_BYTES)
                    if not chunk:
                        break
                    handle.write(chunk)
                    if hasher is not None:
                        hasher.update(chunk)
                handle.flush()
                os.fsync(handle.fileno())
        if hasher is not None:
            digest = hasher.hexdigest()
            if digest != asset.sha256:
                raise ValueError(f"sha256 mismatch for {asset.name}: {digest} != {asset.sha256}")
        temporary_destination.replace(destination)
        fsync_directory(destination.parent)
        return destination
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        temporary_destination.unlink(missing_ok=True)
        raise


def _is_retryable_download_error(exc: Exception) -> bool:
    if isinstance(exc, urllib_error.HTTPError):
        return int(exc.code) in _DOWNLOAD_RETRYABLE_HTTP_CODES
    return isinstance(exc, (urllib_error.URLError, TimeoutError, OSError))


def _urlopen_release_url(
    url: str,
    *,
    timeout: int,
):
    request_or_url: str | urllib.request.Request = str(url)
    auth_token = _github_auth_token()
    if auth_token or _github_api_request_headers(url=str(url)):
        request_or_url = _github_request(url=str(url), token=auth_token)
    return urllib.request.urlopen(request_or_url, timeout=timeout)


def _github_auth_token() -> str:
    for env_name in _GITHUB_TOKEN_ENV_NAMES:
        token = str(os.environ.get(env_name) or "").strip()
        if token:
            return token
    return ""


def _preferred_release_asset_url(*, asset: dict[str, Any], auth_token: str) -> str:
    browser_download_url = str(asset.get("browser_download_url") or "").strip()
    api_download_url = str(asset.get("url") or "").strip()
    if auth_token:
        return api_download_url or browser_download_url
    return browser_download_url or api_download_url


def _github_request(*, url: str, token: str = "") -> urllib.request.Request:
    parsed = urlparse(str(url))
    hostname = str(parsed.hostname or "").strip().lower()
    headers = _github_api_request_headers(url=str(url))
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(str(url), headers=headers)


def _github_api_request_headers(*, url: str) -> dict[str, str]:
    parsed = urlparse(str(url))
    hostname = str(parsed.hostname or "").strip().lower()
    if hostname != "api.github.com":
        return {}
    headers = {"X-GitHub-Api-Version": "2022-11-28"}
    if "/releases/assets/" in parsed.path:
        headers["Accept"] = "application/octet-stream"
    else:
        headers["Accept"] = "application/vnd.github+json"
    return headers


def release_cache_dir(*, repo_root: str | Path, version: str) -> Path:
    return repo_runtime_paths(repo_root).cache_dir / "releases" / version


def _odylith_wheel_asset_name(*, release: ReleaseInfo) -> str:
    wheel_asset_names = sorted(name for name in release.assets if name.endswith(".whl"))
    odylith_wheel_asset_names = [
        name for name in wheel_asset_names if re.fullmatch(rf"odylith-{re.escape(release.version)}-.*\.whl", name)
    ]
    if len(odylith_wheel_asset_names) != 1:
        raise ValueError("release manifest must contain exactly one Odylith wheel asset")
    extra_wheels = sorted(set(wheel_asset_names).difference(odylith_wheel_asset_names))
    if extra_wheels:
        raise ValueError(f"release manifest must not expose sidecar wheel assets: {extra_wheels}")
    return odylith_wheel_asset_names[0]


def _feature_pack_asset(*, release: ReleaseInfo, manifest: dict[str, Any], pack_id: str, runtime_platform: ManagedRuntimePlatform) -> ReleaseAsset:
    feature_packs = manifest.get("feature_packs")
    if not isinstance(feature_packs, dict):
        raise ValueError("release manifest feature_packs must be an object")
    pack_details = feature_packs.get(pack_id)
    if not isinstance(pack_details, dict):
        raise ValueError(f"release manifest missing feature pack {pack_id!r}")
    assets_by_platform = pack_details.get("assets")
    if not isinstance(assets_by_platform, dict):
        raise ValueError(f"release manifest feature pack {pack_id!r} assets must be an object")
    asset_name = str(assets_by_platform.get(runtime_platform.slug) or "").strip()
    if not asset_name:
        raise ValueError(f"release manifest feature pack {pack_id!r} missing asset for {runtime_platform.slug}")
    try:
        return release.assets[asset_name]
    except KeyError as exc:
        raise ValueError(f"release asset missing for feature pack {pack_id!r}: {asset_name}") from exc


def _assets_from_manifest(*, release: ReleaseInfo, manifest: dict[str, Any]) -> ReleaseInfo:
    asset_manifest = manifest.get("assets")
    if not isinstance(asset_manifest, dict):
        raise ValueError("release manifest assets must be an object")
    assets = {}
    for name, asset in release.assets.items():
        details = asset_manifest.get(name, {})
        sha256 = ""
        if isinstance(details, dict):
            sha256 = str(details.get("sha256") or "").strip()
        assets[name] = ReleaseAsset(
            name=asset.name,
            download_url=asset.download_url,
            sha256=sha256 or None,
        )
    return ReleaseInfo(version=release.version, tag=release.tag, assets=assets)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return read_json_object(path)
    except JsonObjectLoadError as exc:
        raise ValueError(f"{path.name} must be a JSON object") from exc


def _validate_manifest(*, manifest: dict[str, Any], release: ReleaseInfo, repo: str) -> None:
    if str(manifest.get("schema_version") or "").strip() != "odylith-release-manifest.v1":
        raise ValueError("unexpected release manifest schema version")
    asset_manifest = manifest.get("assets")
    if not isinstance(asset_manifest, dict):
        raise ValueError("release manifest assets must be an object")
    version_token = str(manifest.get("version") or "").strip()
    tag_token = str(manifest.get("tag") or "").strip()
    repo_token = str(manifest.get("repo") or "").strip()
    if version_token != release.version:
        raise ValueError(f"release manifest version mismatch: {version_token!r} != {release.version!r}")
    if tag_token != release.tag:
        raise ValueError(f"release manifest tag mismatch: {tag_token!r} != {release.tag!r}")
    if not repo_token:
        raise ValueError("release manifest repo is required")
    if repo_token != repo:
        raise ValueError(f"release manifest repo mismatch: {repo_token!r} != {repo!r}")
    repo_schema_version = manifest.get("repo_schema_version")
    if not isinstance(repo_schema_version, int):
        raise ValueError("release manifest repo_schema_version must be an integer")
    for required_name in (
        "build-provenance.v1.json",
        "odylith.sbom.spdx.json",
        "release-manifest.json",
    ):
        if required_name not in release.assets:
            raise ValueError(f"required release asset missing: {required_name}")
        if f"{required_name}.sigstore.json" not in release.assets:
            raise ValueError(f"required release signature missing: {required_name}.sigstore.json")
    wheel_name = _odylith_wheel_asset_name(release=release)
    wheel_metadata = asset_manifest.get(wheel_name)
    if not isinstance(wheel_metadata, dict) or not str(wheel_metadata.get("sha256") or "").strip():
        raise ValueError("release manifest missing Odylith wheel metadata")
    if f"{wheel_name}.sigstore.json" not in release.assets:
        raise ValueError(f"required release signature missing: {wheel_name}.sigstore.json")
    supported_platforms = manifest.get("supported_platforms")
    if not isinstance(supported_platforms, list) or not supported_platforms:
        raise ValueError("release manifest supported_platforms must be a non-empty array")
    expected_supported_platforms = set(supported_platform_slugs())
    observed_supported_platforms = {str(platform_slug or "").strip() for platform_slug in supported_platforms}
    if observed_supported_platforms != expected_supported_platforms:
        raise ValueError(
            "release manifest supported_platforms mismatch: "
            f"{sorted(observed_supported_platforms)} != {sorted(expected_supported_platforms)}"
        )
    for platform_slug in supported_platforms:
        platform_token = str(platform_slug or "").strip()
        runtime_platform = managed_runtime_platform_by_slug(platform_token)
        if runtime_platform.asset_name not in release.assets:
            raise ValueError(f"required managed runtime asset missing: {runtime_platform.asset_name}")
        if f"{runtime_platform.asset_name}.sigstore.json" not in release.assets:
            raise ValueError(f"required managed runtime signature missing: {runtime_platform.asset_name}.sigstore.json")
    feature_packs = manifest.get("feature_packs", {})
    if feature_packs and not isinstance(feature_packs, dict):
        raise ValueError("release manifest feature_packs must be an object")
    if isinstance(feature_packs, dict):
        supported_pack_ids = set(supported_feature_pack_ids())
        for pack_id, details in feature_packs.items():
            resolved_pack_id = str(pack_id or "").strip()
            if resolved_pack_id not in supported_pack_ids:
                raise ValueError(f"unsupported managed runtime feature pack in release manifest: {resolved_pack_id!r}")
            if not isinstance(details, dict):
                raise ValueError(f"feature pack details must be an object: {resolved_pack_id!r}")
            assets_by_platform = details.get("assets")
            if not isinstance(assets_by_platform, dict) or not assets_by_platform:
                raise ValueError(f"feature pack {resolved_pack_id!r} assets must be a non-empty object")
            for platform_slug, asset_name in assets_by_platform.items():
                runtime_platform = managed_runtime_platform_by_slug(str(platform_slug or "").strip())
                resolved_asset_name = str(asset_name or "").strip()
                if not resolved_asset_name:
                    raise ValueError(f"feature pack {resolved_pack_id!r} missing asset for {runtime_platform.slug}")
                if resolved_asset_name not in release.assets:
                    raise ValueError(f"missing release asset for feature pack {resolved_pack_id!r}: {resolved_asset_name}")
                if f"{resolved_asset_name}.sigstore.json" not in release.assets:
                    raise ValueError(f"missing feature pack signature for {resolved_asset_name}")
                asset_details = asset_manifest.get(resolved_asset_name)
                if not isinstance(asset_details, dict) or not str(asset_details.get("sha256") or "").strip():
                    raise ValueError(f"release manifest missing sha256 for feature pack asset {resolved_asset_name}")
    if not isinstance(manifest.get("migration_required"), bool):
        raise ValueError("release manifest migration_required must be a boolean")


def _validate_provenance(
    *,
    provenance: dict[str, Any],
    repo: str,
    release: ReleaseInfo,
    runtime_bundle_name: str,
    runtime_bundle_sha256: str,
    runtime_platform: ManagedRuntimePlatform,
    wheel_name: str,
    wheel_sha256: str,
) -> None:
    if str(provenance.get("version") or "").strip() != "odylith-release-provenance.v1":
        raise ValueError("unexpected provenance schema version")
    if str(provenance.get("repo") or "").strip() != repo:
        raise ValueError("release provenance repo mismatch")
    actor_token = str(provenance.get("actor") or "").strip()
    if repo == AUTHORITATIVE_RELEASE_REPO and actor_token != AUTHORITATIVE_RELEASE_ACTOR:
        raise ValueError("release provenance actor mismatch")
    if str(provenance.get("release_version") or "").strip() != release.version:
        raise ValueError("release provenance version mismatch")
    if str(provenance.get("tag") or "").strip() != release.tag:
        raise ValueError("release provenance tag mismatch")
    workflow = provenance.get("workflow")
    if not isinstance(workflow, dict):
        raise ValueError("release provenance workflow block missing")
    if str(workflow.get("path") or "").strip() != SIGNER_WORKFLOW_PATH:
        raise ValueError("release provenance workflow path mismatch")
    if str(workflow.get("ref") or "").strip() != SIGNER_WORKFLOW_REF:
        raise ValueError("release provenance workflow ref mismatch")
    artifacts = provenance.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("release provenance artifacts block missing")
    wheel = artifacts.get("wheel")
    if not isinstance(wheel, dict):
        raise ValueError("release provenance wheel artifact missing")
    if str(wheel.get("name") or "").strip() != wheel_name:
        raise ValueError("release provenance wheel name mismatch")
    if str(wheel.get("sha256") or "").strip() != wheel_sha256:
        raise ValueError("release provenance wheel digest mismatch")
    runtime_bundles = artifacts.get("runtime_bundles")
    if not isinstance(runtime_bundles, dict):
        raise ValueError("release provenance runtime_bundles block missing")
    runtime_entry = runtime_bundles.get(runtime_platform.slug)
    if not isinstance(runtime_entry, dict):
        raise ValueError("release provenance managed runtime entry missing")
    if str(runtime_entry.get("name") or "").strip() != runtime_bundle_name:
        raise ValueError("release provenance managed runtime name mismatch")
    if str(runtime_entry.get("sha256") or "").strip() != runtime_bundle_sha256:
        raise ValueError("release provenance managed runtime digest mismatch")


def _validate_feature_pack_provenance(
    *,
    provenance: dict[str, Any],
    pack_id: str,
    repo: str,
    release: ReleaseInfo,
    runtime_platform: ManagedRuntimePlatform,
    feature_pack_name: str,
    feature_pack_sha256: str,
) -> None:
    if str(provenance.get("version") or "").strip() != "odylith-release-provenance.v1":
        raise ValueError("unexpected provenance schema version")
    if str(provenance.get("repo") or "").strip() != repo:
        raise ValueError("release provenance repo mismatch")
    if str(provenance.get("release_version") or "").strip() != release.version:
        raise ValueError("release provenance version mismatch")
    artifacts = provenance.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValueError("release provenance artifacts block missing")
    feature_packs = artifacts.get("feature_packs")
    if not isinstance(feature_packs, dict):
        raise ValueError("release provenance feature_packs block missing")
    pack_entry = feature_packs.get(pack_id)
    if not isinstance(pack_entry, dict):
        raise ValueError(f"release provenance feature pack missing: {pack_id}")
    platform_entry = pack_entry.get(runtime_platform.slug)
    if not isinstance(platform_entry, dict):
        raise ValueError(f"release provenance feature pack platform missing: {pack_id}/{runtime_platform.slug}")
    if str(platform_entry.get("name") or "").strip() != feature_pack_name:
        raise ValueError("release provenance feature pack name mismatch")
    if str(platform_entry.get("sha256") or "").strip() != feature_pack_sha256:
        raise ValueError("release provenance feature pack digest mismatch")


def _validate_sbom(*, sbom: dict[str, Any], release: ReleaseInfo) -> None:
    if str(sbom.get("spdxVersion") or "").strip() != "SPDX-2.3":
        raise ValueError("unexpected SBOM SPDX version")
    packages = sbom.get("packages")
    if not isinstance(packages, list) or not packages:
        raise ValueError("SBOM must contain at least one package")
    odylith_package = next((pkg for pkg in packages if isinstance(pkg, dict) and str(pkg.get("name") or "").strip() == "odylith"), None)
    if odylith_package is None:
        raise ValueError("SBOM missing odylith package")
    if str(odylith_package.get("versionInfo") or "").strip() != release.version:
        raise ValueError("SBOM version mismatch")


def _validate_feature_pack_archive(*, bundle_path: Path) -> None:
    saw_runtime_payload = False
    with tarfile.open(bundle_path, "r:gz") as archive:
        members = archive.getmembers()
        validate_archive_members(
            members=members,
            expected_root=MANAGED_RUNTIME_ROOT_NAME,
            label="managed runtime feature pack",
        )
        for member in members:
            if member.name.startswith(f"{MANAGED_RUNTIME_ROOT_NAME}/lib/"):
                saw_runtime_payload = True
    if not saw_runtime_payload:
        raise ValueError("managed runtime feature pack archive does not contain a runtime/lib payload")


def _validate_runtime_bundle_archive(
    *,
    runtime_bundle_path: Path,
    release: ReleaseInfo,
    runtime_platform: ManagedRuntimePlatform,
    wheel_name: str,
) -> None:
    with tarfile.open(runtime_bundle_path, "r:gz") as archive:
        members = archive.getmembers()
        names = [member.name for member in members]
        validate_archive_members(
            members=members,
            expected_root=MANAGED_RUNTIME_ROOT_NAME,
            label="managed runtime bundle",
        )
        metadata_member = archive.extractfile(f"{MANAGED_RUNTIME_ROOT_NAME}/runtime-metadata.json")
        if metadata_member is None:
            raise ValueError("managed runtime bundle missing runtime metadata payload")
        metadata = json.loads(metadata_member.read().decode("utf-8"))
    if not isinstance(metadata, dict):
        raise ValueError("managed runtime bundle metadata must be a JSON object")
    required = {
        f"{MANAGED_RUNTIME_ROOT_NAME}/bin/odylith",
        f"{MANAGED_RUNTIME_ROOT_NAME}/bin/python",
        f"{MANAGED_RUNTIME_ROOT_NAME}/bin/python3",
        f"{MANAGED_RUNTIME_ROOT_NAME}/runtime-metadata.json",
    }
    missing = sorted(required.difference(names))
    if missing:
        raise ValueError(f"managed runtime bundle missing required paths: {missing}")
    if str(metadata.get("schema_version") or "").strip() != MANAGED_RUNTIME_SCHEMA_VERSION:
        raise ValueError("managed runtime bundle metadata schema mismatch")
    if str(metadata.get("version") or "").strip() != release.version:
        raise ValueError("managed runtime bundle metadata version mismatch")
    if str(metadata.get("platform") or "").strip() != runtime_platform.slug:
        raise ValueError("managed runtime bundle metadata platform mismatch")
    if str(metadata.get("python_version") or "").strip() != MANAGED_PYTHON_VERSION:
        raise ValueError("managed runtime bundle metadata python version mismatch")
    if str(metadata.get("source_wheel") or "").strip() != wheel_name:
        raise ValueError("managed runtime bundle metadata source wheel mismatch")


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_DOWNLOAD_CHUNK_BYTES), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
