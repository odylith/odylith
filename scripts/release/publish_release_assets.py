"""Build and publish Odylith GitHub release assets.

This script publishes:
- `install.sh`
- `SHA256SUMS`
- `release-manifest.json`
- `build-provenance.v1.json`
- `odylith.sbom.spdx.json`
- `THIRD_PARTY_ATTRIBUTION.md`
- `odylith` wheel
- one `.sigstore.json` bundle per signed asset
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
import sysconfig
import tarfile
import tempfile
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from odylith.install.managed_runtime import (  # noqa: E402
    CONTEXT_ENGINE_FEATURE_PACK_ID,
    MANAGED_RUNTIME_ROOT_NAME,
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_FILENAME,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
    ManagedRuntimeFeaturePack,
    ManagedRuntimePlatform,
    supported_managed_runtime_feature_packs,
    supported_managed_runtime_platforms,
)
from odylith.install.python_env import PYTHON_ENV_SCRUB_LINES  # noqa: E402
from odylith.runtime import release_notes  # noqa: E402


DEFAULT_REPO_SCHEMA_VERSION = 1
MANIFEST_SCHEMA_VERSION = "odylith-release-manifest.v1"
PROVENANCE_SCHEMA_VERSION = "odylith-release-provenance.v1"
SBOM_LICENSE = "Apache-2.0"
AUTHORITATIVE_RELEASE_REPO = "odylith/odylith"
AUTHORITATIVE_RELEASE_ACTOR = "freedom-research"
WORKFLOW_PATH = ".github/workflows/release.yml"
WORKFLOW_REF = "refs/heads/main"
OIDC_ISSUER = "https://token.actions.githubusercontent.com"


def _sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _run(cmd: Sequence[str]) -> None:
    subprocess.run(list(cmd), check=True)


def _repo_signer_identity(repo: str) -> str:
    return f"https://github.com/{repo}/{WORKFLOW_PATH}@{WORKFLOW_REF}"


def _require_canonical_release_context(*, repo: str) -> None:
    if repo != AUTHORITATIVE_RELEASE_REPO:
        raise ValueError(
            f"release assets may only be published for the canonical repo `{AUTHORITATIVE_RELEASE_REPO}`, got `{repo}`"
        )
    if os.getenv("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise ValueError("release asset publishing is only allowed from the canonical GitHub Actions workflow")
    github_repo = str(os.getenv("GITHUB_REPOSITORY") or "").strip()
    if github_repo != AUTHORITATIVE_RELEASE_REPO:
        raise ValueError(
            f"release asset publishing requires GITHUB_REPOSITORY={AUTHORITATIVE_RELEASE_REPO}, got `{github_repo or '<empty>'}`"
        )
    github_actor = str(os.getenv("GITHUB_ACTOR") or "").strip()
    if github_actor != AUTHORITATIVE_RELEASE_ACTOR:
        raise ValueError(
            f"release asset publishing requires GITHUB_ACTOR={AUTHORITATIVE_RELEASE_ACTOR}, got `{github_actor or '<empty>'}`"
        )
    github_ref = str(os.getenv("GITHUB_REF") or "").strip()
    if github_ref != WORKFLOW_REF:
        raise ValueError(
            f"release asset publishing requires GITHUB_REF={WORKFLOW_REF}, got `{github_ref or '<empty>'}`"
        )


def _target_python_site_packages(*, runtime_root: Path) -> Path:
    return runtime_root / "lib" / f"python{MANAGED_PYTHON_VERSION.rsplit('.', 1)[0]}" / "site-packages"


def _download(url: str, destination: Path, *, sha256: str | None = None) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as response:  # noqa: S310 - trusted release asset url
        payload = response.read()
    if sha256:
        digest = hashlib.sha256(payload).hexdigest()
        if digest != sha256:
            raise ValueError(f"upstream asset sha256 mismatch for {destination.name}: {digest} != {sha256}")
    destination.write_bytes(payload)
    return destination


def _parse_wheel_filename(filename: str) -> tuple[str, str, str, str]:
    stem = filename.removesuffix(".whl")
    parts = stem.split("-")
    if len(parts) < 5:
        raise ValueError(f"unexpected wheel filename: {filename}")
    name, version, py_tag, abi_tag, platform_tag = parts[-5:]
    return name, version, py_tag, abi_tag, platform_tag


def _pip_platform_args(runtime_platform: ManagedRuntimePlatform) -> tuple[str, str]:
    mapping = {
        "darwin-arm64": ("macosx_12_0_arm64", "cp313"),
        "linux-arm64": ("manylinux_2_17_aarch64", "cp313"),
        "linux-x86_64": ("manylinux_2_17_x86_64", "cp313"),
    }
    try:
        return mapping[runtime_platform.slug]
    except KeyError as exc:  # pragma: no cover - defensive guard
        raise ValueError(f"unsupported managed runtime platform: {runtime_platform.slug}") from exc


def _download_runtime_wheels(
    *,
    wheel: Path,
    runtime_platform: ManagedRuntimePlatform,
    destination: Path,
) -> list[Path]:
    platform_tag, abi_tag = _pip_platform_args(runtime_platform)
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--implementation",
        "cp",
        "--python-version",
        "3.13",
        "--abi",
        abi_tag,
        "--platform",
        platform_tag,
        "--dest",
        str(destination),
        str(wheel),
    ]
    _run(command)
    wheels = sorted(destination.glob("*.whl"))
    if not wheels:
        raise ValueError(f"pip download produced no wheels for {runtime_platform.slug}")
    return wheels


def _download_feature_pack_wheels(
    *,
    requirements: Sequence[str],
    runtime_platform: ManagedRuntimePlatform,
    destination: Path,
) -> list[Path]:
    platform_tag, abi_tag = _pip_platform_args(runtime_platform)
    command = [
        sys.executable,
        "-m",
        "pip",
        "download",
        "--only-binary=:all:",
        "--implementation",
        "cp",
        "--python-version",
        "3.13",
        "--abi",
        abi_tag,
        "--platform",
        platform_tag,
        "--dest",
        str(destination),
        *list(requirements),
    ]
    _run(command)
    wheels = sorted(destination.glob("*.whl"))
    if not wheels:
        raise ValueError(f"pip download produced no feature-pack wheels for {runtime_platform.slug}")
    return wheels


def _extract_wheel_into_site_packages(*, wheel_path: Path, site_packages: Path) -> None:
    site_packages.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(wheel_path) as archive:
        archive.extractall(site_packages)


def _rewrite_archive_member_root(
    member: tarfile.TarInfo,
    *,
    source_root: str,
    target_root: str,
) -> tarfile.TarInfo:
    parts = PurePosixPath(member.name).parts
    if not parts or parts[0] != source_root:
        raise ValueError(f"unexpected upstream managed runtime member root: {member.name}")
    rewritten = copy.copy(member)
    rewritten.name = str(PurePosixPath(target_root, *parts[1:]))
    return rewritten


def _copy_upstream_archive_into_runtime_bundle(
    *,
    upstream_archive_path: Path,
    destination_archive: tarfile.TarFile,
    source_root: str,
    target_root: str,
) -> None:
    with tarfile.open(upstream_archive_path, "r:gz") as upstream_archive:
        members = upstream_archive.getmembers()
        from odylith.install.archive_safety import validate_archive_members  # noqa: PLC0415

        validate_archive_members(
            members=members,
            expected_root=source_root,
            label="managed python upstream archive",
        )
        for member in members:
            rewritten = _rewrite_archive_member_root(
                member,
                source_root=source_root,
                target_root=target_root,
            )
            if member.isreg():
                payload = upstream_archive.extractfile(member)
                if payload is None:
                    raise ValueError(f"managed python upstream archive missing payload for {member.name}")
                destination_archive.addfile(rewritten, payload)
                continue
            destination_archive.addfile(rewritten)


def _write_runtime_metadata(
    *,
    runtime_root: Path,
    runtime_platform: ManagedRuntimePlatform,
    version: str,
    source_wheel: Path,
) -> None:
    metadata = {
        "schema_version": MANAGED_RUNTIME_SCHEMA_VERSION,
        "version": version,
        "python_version": MANAGED_PYTHON_VERSION,
        "platform": runtime_platform.slug,
        "platform_display_name": runtime_platform.display_name,
        "source_wheel": source_wheel.name,
    }
    (runtime_root / "runtime-metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_runtime_odylith_wrapper(*, runtime_root: Path) -> None:
    odylith_path = runtime_root / "bin" / "odylith"
    odylith_path.parent.mkdir(parents=True, exist_ok=True)
    odylith_path.write_text(
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                *PYTHON_ENV_SCRUB_LINES,
                'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
                'exec "$script_dir/python" -m odylith.cli "$@"',
                "",
            ]
        ),
        encoding="utf-8",
    )
    odylith_path.chmod(0o755)


def _build_managed_runtime_bundle(
    *,
    wheel: Path,
    runtime_platform: ManagedRuntimePlatform,
    output_path: Path,
) -> Path:
    version = wheel.name.split("-")[1]
    with tempfile.TemporaryDirectory(prefix=f"odylith-runtime-{runtime_platform.slug}-") as tmpdir:
        tmp_root = Path(tmpdir)
        upstream_archive = _download(
            runtime_platform.upstream_asset_url,
            tmp_root / runtime_platform.upstream_asset_name,
            sha256=runtime_platform.upstream_asset_sha256,
        )
        runtime_root = tmp_root / MANAGED_RUNTIME_ROOT_NAME

        wheel_download_dir = tmp_root / "wheels"
        wheels = _download_runtime_wheels(wheel=wheel, runtime_platform=runtime_platform, destination=wheel_download_dir)
        site_packages = _target_python_site_packages(runtime_root=runtime_root)
        for dependency_wheel in wheels:
            _extract_wheel_into_site_packages(wheel_path=dependency_wheel, site_packages=site_packages)

        _write_runtime_metadata(
            runtime_root=runtime_root,
            runtime_platform=runtime_platform,
            version=version,
            source_wheel=wheel,
        )
        _write_runtime_odylith_wrapper(runtime_root=runtime_root)

        with tarfile.open(output_path, "w:gz") as archive:
            _copy_upstream_archive_into_runtime_bundle(
                upstream_archive_path=upstream_archive,
                destination_archive=archive,
                source_root="python",
                target_root=MANAGED_RUNTIME_ROOT_NAME,
            )
            archive.add(runtime_root, arcname=MANAGED_RUNTIME_ROOT_NAME)
    return output_path


def _build_managed_runtime_bundles(*, wheel: Path, dist_dir: Path) -> list[tuple[ManagedRuntimePlatform, Path]]:
    bundles: list[tuple[ManagedRuntimePlatform, Path]] = []
    for runtime_platform in supported_managed_runtime_platforms():
        bundle_path = dist_dir / runtime_platform.asset_name
        bundles.append(
            (
                runtime_platform,
                _build_managed_runtime_bundle(
                    wheel=wheel,
                    runtime_platform=runtime_platform,
                    output_path=bundle_path,
                ),
            )
        )
    return bundles


def _build_managed_runtime_feature_pack(
    *,
    feature_pack: ManagedRuntimeFeaturePack,
    runtime_platform: ManagedRuntimePlatform,
    output_path: Path,
) -> Path:
    with tempfile.TemporaryDirectory(prefix=f"odylith-feature-pack-{feature_pack.pack_id}-{runtime_platform.slug}-") as tmpdir:
        tmp_root = Path(tmpdir)
        overlay_root = tmp_root / MANAGED_RUNTIME_ROOT_NAME
        site_packages = _target_python_site_packages(runtime_root=overlay_root)
        wheel_download_dir = tmp_root / "wheels"
        wheels = _download_feature_pack_wheels(
            requirements=feature_pack.python_requirements_for_platform(runtime_platform),
            runtime_platform=runtime_platform,
            destination=wheel_download_dir,
        )
        for dependency_wheel in wheels:
            _extract_wheel_into_site_packages(wheel_path=dependency_wheel, site_packages=site_packages)
        metadata_path = overlay_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        metadata_path.write_text(
            json.dumps(
                {
                    "schema_version": "odylith-runtime-feature-packs.v1",
                    "version": "",
                    "packs": {
                        feature_pack.pack_id: {
                            "asset_name": feature_pack.asset_name(runtime_platform),
                            "display_name": feature_pack.display_name,
                            "platform": runtime_platform.slug,
                        }
                    },
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        with tarfile.open(output_path, "w:gz") as archive:
            archive.add(overlay_root, arcname=MANAGED_RUNTIME_ROOT_NAME)
    return output_path


def _build_managed_runtime_feature_packs(*, dist_dir: Path) -> list[tuple[ManagedRuntimeFeaturePack, ManagedRuntimePlatform, Path]]:
    bundles: list[tuple[ManagedRuntimeFeaturePack, ManagedRuntimePlatform, Path]] = []
    for feature_pack in supported_managed_runtime_feature_packs():
        for runtime_platform in supported_managed_runtime_platforms():
            bundle_path = dist_dir / feature_pack.asset_name(runtime_platform)
            bundles.append(
                (
                    feature_pack,
                    runtime_platform,
                    _build_managed_runtime_feature_pack(
                        feature_pack=feature_pack,
                        runtime_platform=runtime_platform,
                        output_path=bundle_path,
                    ),
                )
            )
    return bundles


def _write_install_script(*, output_path: Path, tag: str, repo: str, odylith_wheel: str) -> None:
    del tag, odylith_wheel
    runtime_asset_to_slug = {
        runtime_platform.asset_name: runtime_platform.slug for runtime_platform in supported_managed_runtime_platforms()
    }
    expected_supported_platforms = [runtime_platform.slug for runtime_platform in supported_managed_runtime_platforms()]
    validate_release_script = [
        "from __future__ import annotations",
        "import hashlib",
        "import json",
        "import re",
        "import sys",
        "import tarfile",
        "from pathlib import Path",
        "from pathlib import PurePosixPath",
        "tmpdir, runtime_asset_name, repo, requested_version, signer_identity = sys.argv[1:6]",
        "def _resolved_archive_link(member_name: str, link_name: str) -> PurePosixPath | None:",
        "    stack: list[str] = []",
        "    for part in (*PurePosixPath(member_name).parent.parts, *PurePosixPath(link_name).parts):",
        "        if part in ('', '.'):",
        "            continue",
        "        if part == '..':",
        "            if not stack:",
        "                return None",
        "            stack.pop()",
        "            continue",
        "        stack.append(part)",
        "    return PurePosixPath(*stack) if stack else PurePosixPath('.')",
        "manifest = json.loads((Path(tmpdir) / 'release-manifest.json').read_text(encoding='utf-8'))",
        "if str(manifest.get('schema_version') or '').strip() != 'odylith-release-manifest.v1':",
        "    raise SystemExit('unexpected release manifest schema version')",
        "if str(manifest.get('repo') or '').strip() != repo:",
        "    raise SystemExit('release manifest repo mismatch')",
        "if bool(manifest.get('migration_required')):",
        "    raise SystemExit('migration-marked releases require an explicit maintainer adoption flow')",
        "version = str(manifest.get('version') or '').strip()",
        "if requested_version != 'latest' and version != requested_version:",
        "    raise SystemExit(f'release manifest version mismatch: {version} != {requested_version}')",
        "supported_platforms = manifest.get('supported_platforms')",
        "if not isinstance(supported_platforms, list) or not supported_platforms:",
        "    raise SystemExit('release manifest missing supported_platforms')",
        f"expected_supported_platforms = {json.dumps(sorted(expected_supported_platforms))}",
        "observed_supported_platforms = sorted(str(platform or '').strip() for platform in supported_platforms)",
        "if observed_supported_platforms != expected_supported_platforms:",
        "    raise SystemExit(f'release manifest supported_platforms mismatch: {observed_supported_platforms} != {expected_supported_platforms}')",
        f"runtime_asset_to_slug = {json.dumps(runtime_asset_to_slug, sort_keys=True)}",
        "platform_slug = runtime_asset_to_slug.get(runtime_asset_name, '')",
        "if not platform_slug:",
        "    raise SystemExit('unsupported runtime bundle asset requested by installer')",
        "if platform_slug not in observed_supported_platforms:",
        "    raise SystemExit('release manifest does not support the detected runtime platform')",
        "assets = manifest.get('assets', {}) if isinstance(manifest.get('assets'), dict) else {}",
        "wheel_candidates = [name for name in assets if re.fullmatch(rf'odylith-{re.escape(version)}-.*\\.whl', name)]",
        "if len(wheel_candidates) != 1:",
        "    raise SystemExit('release manifest must contain exactly one Odylith wheel asset')",
        "expected = str(assets.get(runtime_asset_name, {}).get('sha256') or '').strip()",
        "if not expected:",
        "    raise SystemExit('release manifest missing runtime bundle digest')",
        "digest = hashlib.sha256((Path(tmpdir) / runtime_asset_name).read_bytes()).hexdigest()",
        "if digest != expected:",
        "    raise SystemExit(f'sha256 mismatch for {runtime_asset_name}: {digest} != {expected}')",
        "with tarfile.open(Path(tmpdir) / runtime_asset_name, 'r:gz') as archive:",
        "    members = archive.getmembers()",
        "    names = [member.name for member in members]",
        "    for member in members:",
        "        parts = [part for part in Path(member.name).parts if part not in ('', '.')]",
        "        if any(part == '..' for part in parts):",
        "            raise SystemExit(f'managed runtime bundle contains unsafe member path: {member.name}')",
        "        if Path(member.name).is_absolute():",
        "            raise SystemExit(f'managed runtime bundle contains absolute member path: {member.name}')",
        "        if member.name not in {'runtime'} and not member.name.startswith('runtime/'):",
        "            raise SystemExit(f'managed runtime bundle contains unexpected member path: {member.name}')",
        "        if member.issym() or member.islnk():",
        "            if (not member.linkname) or PurePosixPath(member.linkname).is_absolute():",
        "                raise SystemExit(f'managed runtime bundle contains unsafe link target: {member.name} -> {member.linkname}')",
        "            resolved_link = _resolved_archive_link(member.name, member.linkname)",
        "            resolved_parts = [part for part in resolved_link.parts if part not in ('', '.')] if resolved_link is not None else []",
        "            if (resolved_link is None) or (not resolved_parts) or (resolved_parts[0] != 'runtime'):",
        "                raise SystemExit(f'managed runtime bundle contains unsafe link target: {member.name} -> {member.linkname}')",
        "            continue",
        "        if member.ischr() or member.isblk() or member.isfifo():",
        "            raise SystemExit(f'managed runtime bundle contains unsupported member type: {member.name}')",
        "    required = {'runtime/bin/odylith', 'runtime/bin/python', 'runtime/bin/python3', 'runtime/runtime-metadata.json'}",
        "    missing = sorted(required.difference(names))",
        "    if missing:",
        "        raise SystemExit(f'managed runtime bundle missing required paths: {missing}')",
        "    metadata_member = archive.extractfile('runtime/runtime-metadata.json')",
        "    if metadata_member is None:",
        "        raise SystemExit('managed runtime bundle missing runtime metadata payload')",
        "    metadata = json.loads(metadata_member.read().decode('utf-8'))",
        "if not isinstance(metadata, dict):",
        "    raise SystemExit('managed runtime bundle metadata must be a JSON object')",
        "if str(metadata.get('schema_version') or '').strip() != 'odylith-runtime-bundle.v1':",
        "    raise SystemExit('managed runtime bundle metadata schema mismatch')",
        "if str(metadata.get('version') or '').strip() != version:",
        "    raise SystemExit('managed runtime bundle metadata version mismatch')",
        "if str(metadata.get('platform') or '').strip() != platform_slug:",
        "    raise SystemExit('managed runtime bundle metadata platform mismatch')",
        "if str(metadata.get('python_version') or '').strip() != '3.13.12':",
        "    raise SystemExit('managed runtime bundle metadata python version mismatch')",
        "if str(metadata.get('source_wheel') or '').strip() != wheel_candidates[0]:",
        "    raise SystemExit('managed runtime bundle metadata source wheel mismatch')",
        "verification = {",
        f"    'schema_version': {json.dumps(MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION)},",
        "    'version': version,",
        "    'verification': {",
        "        'manifest_sha256': hashlib.sha256((Path(tmpdir) / 'release-manifest.json').read_bytes()).hexdigest(),",
        "        'provenance_sha256': hashlib.sha256((Path(tmpdir) / 'build-provenance.v1.json').read_bytes()).hexdigest(),",
        "        'runtime_bundle_platform': platform_slug,",
        "        'runtime_bundle_sha256': digest,",
        "        'sbom_sha256': hashlib.sha256((Path(tmpdir) / 'odylith.sbom.spdx.json').read_bytes()).hexdigest(),",
        "        'signer_identity': signer_identity,",
        "        'wheel_sha256': str(assets.get(wheel_candidates[0], {}).get('sha256') or '').strip(),",
        "    },",
        "}",
        f"(Path(tmpdir) / {json.dumps(MANAGED_RUNTIME_VERIFICATION_FILENAME)}).write_text(",
        "    json.dumps(verification, indent=2, sort_keys=True) + '\\n',",
        "    encoding='utf-8',",
        ")",
        "print(version)",
    ]
    script_lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        *PYTHON_ENV_SCRUB_LINES,
        f"repo={json.dumps(repo)}",
        f"signer_identity={json.dumps(_repo_signer_identity(repo))}",
        f"oidc_issuer={json.dumps(OIDC_ISSUER)}",
        'local_release_base_url="${ODYLITH_RELEASE_BASE_URL:-}"',
        'skip_sigstore_verify="${ODYLITH_RELEASE_SKIP_SIGSTORE_VERIFY:-0}"',
        "say() {",
        "  printf 'odylith: %s\\n' \"$*\"",
        "}",
        "step() {",
        "  printf '\\n==> %s\\n' \"$*\"",
        "}",
        "banner() {",
        "  cat <<'EOF'",
        " ██████╗ ██████╗ ██╗   ██╗██╗     ██╗████████╗██╗  ██╗",
        "██╔═══██╗██╔══██╗╚██╗ ██╔╝██║     ██║╚══██╔══╝██║  ██║",
        "██║   ██║██║  ██║ ╚████╔╝ ██║     ██║   ██║   ███████║",
        "██║   ██║██║  ██║  ╚██╔╝  ██║     ██║   ██║   ██╔══██║",
        "╚██████╔╝██████╔╝   ██║   ███████╗██║   ██║   ██║  ██║",
        " ╚═════╝ ╚═════╝    ╚═╝   ╚══════╝╚═╝   ╚═╝   ╚═╝  ╚═╝",
        "EOF",
        "}",
        "require_command() {",
        "  if ! command -v \"$1\" >/dev/null 2>&1; then",
        "    echo \"Odylith install requires '$1' on PATH.\" >&2",
        "    exit 2",
        "  fi",
        "}",
        "detect_repo_root() {",
        "  local candidate git_candidate start_dir",
        "  start_dir=\"$(pwd)\"",
        "  candidate=\"$start_dir\"",
        "  repo_root=''",
        "  repo_root_reason=''",
        "  while true; do",
        "    if [[ -f \"$candidate/AGENTS.md\" ]]; then",
        "      repo_root=\"$candidate\"",
        "      repo_root_reason='agents'",
        "      return 0",
        "    fi",
        "    if [[ -z \"$git_candidate\" && ( -d \"$candidate/.git\" || -f \"$candidate/.git\" ) ]]; then",
        "      git_candidate=\"$candidate\"",
        "    fi",
        "    if [[ \"$candidate\" == \"/\" ]]; then",
        "      break",
        "    fi",
        "    candidate=\"$(dirname \"$candidate\")\"",
        "  done",
        "  if [[ -n \"$git_candidate\" ]]; then",
        "    repo_root=\"$git_candidate\"",
        "    repo_root_reason='git'",
        "    return 0",
        "  fi",
        "  repo_root=\"$start_dir\"",
        "  repo_root_reason='folder'",
        "}",
        "describe_repo_root_choice() {",
        "  say \"Working in repo: $repo_root.\"",
        "  case \"$repo_root_reason\" in",
        "    agents) ;;",
        "    git)",
        "      say \"No root AGENTS.md was found above this directory. Odylith will create one at the detected Git root.\"",
        "      ;;",
        "    folder)",
        "      say \"No enclosing AGENTS.md or .git was found. Odylith will treat the current folder as the repo root and create a root AGENTS.md here.\"",
        "      say \"Git-aware features stay limited until this folder is backed by Git.\"",
        "      say \"That means working-tree intelligence, background autospawn, and git-fsmonitor watcher help stay reduced for now.\"",
        "      ;;",
        "  esac",
        "}",
        "detect_runtime_asset() {",
        "  local system machine",
        "  system=\"$(uname -s)\"",
        "  machine=\"$(uname -m)\"",
        "  case \"$system-$machine\" in",
        "    Darwin-arm64|Darwin-aarch64) printf '%s\\n' 'odylith-runtime-darwin-arm64.tar.gz' ;;",
        "    Linux-aarch64|Linux-arm64) printf '%s\\n' 'odylith-runtime-linux-arm64.tar.gz' ;;",
        "    Linux-x86_64|Linux-amd64) printf '%s\\n' 'odylith-runtime-linux-x86_64.tar.gz' ;;",
        "    *)",
        "      echo 'Odylith currently supports macOS (Apple Silicon) and Linux (x86_64, ARM64). Intel macOS and Windows are not supported in this release.' >&2",
        "      return 2",
        "      ;;",
        "  esac",
        "}",
        "platform_display_name() {",
        "  case \"$1\" in",
        "    odylith-runtime-darwin-arm64.tar.gz) printf '%s\\n' 'macOS (Apple Silicon)' ;;",
        "    odylith-runtime-linux-arm64.tar.gz) printf '%s\\n' 'Linux (ARM64)' ;;",
        "    odylith-runtime-linux-x86_64.tar.gz) printf '%s\\n' 'Linux (x86_64)' ;;",
        "    *) printf '%s\\n' 'an unsupported platform' ;;",
        "  esac",
        "}",
        "allow_local_http_asset() {",
        "  case \"$1\" in",
        "    http://127.0.0.1/*|http://127.0.0.1:*/*|http://localhost/*|http://localhost:*/*|http://[::1]/*|http://[::1]:*/*) return 0 ;;",
        "    *) return 1 ;;",
        "  esac",
        "}",
        "fetch_asset() {",
        "  local url destination",
        "  url=\"$1\"",
        "  destination=\"$2\"",
        "  if allow_local_http_asset \"$url\"; then",
        "    curl --fail --show-error --silent --location --retry 3 --retry-connrefused --retry-delay 1 \"$url\" -o \"$destination\"",
        "    return",
        "  fi",
        "  curl --fail --show-error --silent --location --proto '=https' --tlsv1.2 --retry 3 --retry-connrefused --retry-delay 1 \"$url\" -o \"$destination\"",
        "}",
        "tmpdir=\"$(mktemp -d)\"",
        "cleanup() { rm -rf \"$tmpdir\"; }",
        "trap cleanup EXIT",
        "sigstore_stderr_is_benign() {",
        "  local line",
        "  line=\"$1\"",
        "  if printf '%s\\n' \"$line\" | grep -Eiq 'unsupported key type:[[:space:]]*7'; then",
        "    return 0",
        "  fi",
        "  if printf '%s\\n' \"$line\" | grep -Eiq 'tuf.*offline|offline.*tuf'; then",
        "    return 0",
        "  fi",
        "  return 1",
        "}",
        "verify_sigstore_identity() {",
        "  local asset_path bundle_path stderr_path line",
        "  asset_path=\"$1\"",
        "  bundle_path=\"$2\"",
        "  stderr_path=\"$tmpdir/sigstore-stderr.log\"",
        "  if ! \"$bootstrap_python\" -m sigstore verify identity \"$asset_path\" --bundle \"$bundle_path\" --offline --cert-identity \"$signer_identity\" --cert-oidc-issuer \"$oidc_issuer\" 2>\"$stderr_path\"; then",
        "    cat \"$stderr_path\" >&2",
        "    rm -f \"$stderr_path\"",
        "    exit 2",
        "  fi",
        "  while IFS= read -r line; do",
        "    [[ -z \"$line\" ]] && continue",
        "    if sigstore_stderr_is_benign \"$line\"; then",
        "      continue",
        "    fi",
        "    echo \"$line\" >&2",
        "  done < \"$stderr_path\"",
        "  rm -f \"$stderr_path\"",
        "}",
        'release_version="${ODYLITH_VERSION:-latest}"',
        "require_command curl",
        "require_command tar",
        "banner",
        "detect_repo_root",
        'runtime_asset_name="$(detect_runtime_asset)"',
        'platform_name="$(platform_display_name "$runtime_asset_name")"',
        'if [[ -n "$local_release_base_url" ]]; then',
        '  release_base_url="$local_release_base_url"',
        'elif [[ "$release_version" == "latest" ]]; then',
        '  release_base_url="https://github.com/${repo}/releases/latest/download"',
        "else",
        '  release_base_url="https://github.com/${repo}/releases/download/v${release_version}"',
        "fi",
        'say "Odylith is getting this repo ready."',
        "describe_repo_root_choice",
        'say "Detected platform: $platform_name."',
        'say "No setup questions. Odylith will pick the right managed assets for this machine."',
        'say "Your repo'"'"'s own Python toolchain stays untouched."',
        'if [[ "$release_version" == "latest" ]]; then',
        '  say "Resolving the latest Odylith release."',
        "else",
        '  say "Resolving Odylith release v$release_version."',
        "fi",
        'if [[ -n "$local_release_base_url" ]]; then',
        '  say "Using local hosted-style release assets from $local_release_base_url."',
        "fi",
        'if [[ -x "$repo_root/.odylith/bin/odylith" ]]; then',
        '  say "Existing Odylith runtime detected. This refresh keeps the handoff zero-friction and swaps in verified layers safely."',
        "fi",
        'manifest_url="$release_base_url/release-manifest.json"',
        'manifest_bundle_url="$release_base_url/release-manifest.json.sigstore.json"',
        'provenance_url="$release_base_url/build-provenance.v1.json"',
        'provenance_bundle_url="$release_base_url/build-provenance.v1.json.sigstore.json"',
        'sbom_url="$release_base_url/odylith.sbom.spdx.json"',
        'sbom_bundle_url="$release_base_url/odylith.sbom.spdx.json.sigstore.json"',
        'step "Fetching the secure bootstrap runtime"',
        "fetch_asset \"$release_base_url/$runtime_asset_name\" \"$tmpdir/$runtime_asset_name\"",
        "fetch_asset \"$release_base_url/$runtime_asset_name.sigstore.json\" \"$tmpdir/$runtime_asset_name.sigstore.json\"",
        "tar -tzf \"$tmpdir/$runtime_asset_name\" > \"$tmpdir/runtime-members.txt\"",
        "while IFS= read -r member; do",
        "  [[ -z \"$member\" ]] && continue",
        "  case \"$member\" in",
        "    /*|../*|*/../*|*/..|..)",
        "      echo \"managed runtime bundle contains unsafe member path: $member\" >&2",
        "      exit 2",
        "      ;;",
        "  esac",
        "  case \"$member\" in",
        "    runtime|runtime/*) ;;",
        "    *)",
        "      echo \"managed runtime bundle contains unexpected member path: $member\" >&2",
        "      exit 2",
        "      ;;",
        "  esac",
        "done < \"$tmpdir/runtime-members.txt\"",
        "mkdir -p \"$tmpdir/bootstrap\"",
        "tar -xzf \"$tmpdir/$runtime_asset_name\" -C \"$tmpdir/bootstrap\" runtime",
        "bootstrap_runtime=\"$tmpdir/bootstrap/runtime\"",
        "bootstrap_python=\"$bootstrap_runtime/bin/python\"",
        "if [[ ! -x \"$bootstrap_python\" ]]; then",
        "  echo \"managed runtime bundle missing bootstrap python\" >&2",
        "  exit 2",
        "fi",
        'step "Verifying signed release evidence"',
        "fetch_asset \"$manifest_url\" \"$tmpdir/release-manifest.json\"",
        "fetch_asset \"$manifest_bundle_url\" \"$tmpdir/release-manifest.json.sigstore.json\"",
        "fetch_asset \"$provenance_url\" \"$tmpdir/build-provenance.v1.json\"",
        "fetch_asset \"$provenance_bundle_url\" \"$tmpdir/build-provenance.v1.json.sigstore.json\"",
        "fetch_asset \"$sbom_url\" \"$tmpdir/odylith.sbom.spdx.json\"",
        "fetch_asset \"$sbom_bundle_url\" \"$tmpdir/odylith.sbom.spdx.json.sigstore.json\"",
        'if [[ "$skip_sigstore_verify" != "1" ]]; then',
        "  verify_sigstore_identity \"$tmpdir/release-manifest.json\" \"$tmpdir/release-manifest.json.sigstore.json\"",
        "  verify_sigstore_identity \"$tmpdir/$runtime_asset_name\" \"$tmpdir/$runtime_asset_name.sigstore.json\"",
        "  verify_sigstore_identity \"$tmpdir/build-provenance.v1.json\" \"$tmpdir/build-provenance.v1.json.sigstore.json\"",
        "  verify_sigstore_identity \"$tmpdir/odylith.sbom.spdx.json\" \"$tmpdir/odylith.sbom.spdx.json.sigstore.json\"",
        "fi",
        "cat > \"$tmpdir/validate_release.py\" <<'PY'",
        *validate_release_script,
        "PY",
        f'release_version="$("$bootstrap_python" "$tmpdir/validate_release.py" "$tmpdir" "$runtime_asset_name" "$repo" "$release_version" "$signer_identity")"',
        "state_root=\"$repo_root/.odylith\"",
        "version_root=\"$state_root/runtime/versions/$release_version\"",
        "rm -rf \"$version_root\"",
        "mkdir -p \"$state_root/runtime/versions\" \"$state_root/bin\"",
        'step "Activating Odylith"',
        "mv \"$bootstrap_runtime\" \"$version_root\"",
        f"mv \"$tmpdir/{MANAGED_RUNTIME_VERIFICATION_FILENAME}\" \"$version_root/{MANAGED_RUNTIME_VERIFICATION_FILENAME}\"",
        "cat > \"$tmpdir/write_runtime_trust.py\" <<'PY'",
        "import json",
        "import sys",
        "from pathlib import Path",
        "from odylith.install.runtime_integrity import write_managed_runtime_trust",
        "",
        "repo_root = Path(sys.argv[1]).resolve()",
        "version_root = Path(sys.argv[2]).resolve()",
        f"verification_path = version_root / '{MANAGED_RUNTIME_VERIFICATION_FILENAME}'",
        "payload = json.loads(verification_path.read_text(encoding='utf-8'))",
        "verification = payload.get('verification') if isinstance(payload, dict) else None",
        "if not isinstance(verification, dict):",
        "    raise SystemExit(f'managed runtime verification evidence missing: {verification_path}')",
        "write_managed_runtime_trust(repo_root=repo_root, version_root=version_root, verification=verification)",
        "PY",
        "\"$version_root/bin/python\" \"$tmpdir/write_runtime_trust.py\" \"$repo_root\" \"$version_root\"",
        "ln -sfn \"$version_root\" \"$state_root/runtime/current\"",
        "cat > \"$state_root/bin/odylith\" <<'EOF'",
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        *PYTHON_ENV_SCRUB_LINES,
        'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
        'state_root="$(cd "$script_dir/.." && pwd)"',
        'current_python="$state_root/runtime/current/bin/python"',
        'if [ -x "$current_python" ]; then',
        '  exec "$current_python" -m odylith.cli "$@"',
        "fi",
        "echo \"Odylith runtime missing: $current_python\" >&2",
        "exit 2",
        "EOF",
        "chmod +x \"$state_root/bin/odylith\"",
        'say "Finishing the full Odylith setup inside the managed runtime."',
        'say "First install may take a minute. Later upgrades reuse unchanged runtime layers so routine updates stay lean."',
        "\"$state_root/bin/odylith\" install --repo-root \"$repo_root\" --version \"$release_version\" --align-pin",
        'say "Odylith is live."',
        'say \'Quick posture check: ./.odylith/bin/odylith version --repo-root "$repo_root"\'',
        "",
    ]
    output_path.write_text("\n".join(script_lines), encoding="utf-8")
    output_path.chmod(output_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def _write_sha256sums(*, output_path: Path, files: list[Path]) -> None:
    rows = [f"{_sha256(path)}  {path.name}" for path in files]
    output_path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _write_release_manifest(
    *,
    output_path: Path,
    tag: str,
    repo: str,
    wheel: Path,
    install_sh: Path,
    provenance: Path,
    sbom: Path,
    third_party_attribution: Path,
    feature_packs: list[tuple[ManagedRuntimeFeaturePack, ManagedRuntimePlatform, Path]],
    runtime_bundles: list[tuple[ManagedRuntimePlatform, Path]],
    release_note: release_notes.ReleaseNotesSource | None = None,
) -> None:
    version = tag.removeprefix("v")
    payload = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "version": version,
        "tag": tag,
        "repo": repo,
        "repo_schema_version": DEFAULT_REPO_SCHEMA_VERSION,
        "migration_required": False,
        "supported_platforms": [runtime_platform.slug for runtime_platform, _ in runtime_bundles],
        "published_at": (
            str(release_note.published_at).strip()
            if release_note is not None and str(release_note.published_at).strip()
            else ""
        ),
        "release_notes": str(release_note.body).strip() if release_note is not None else "",
        "release_highlights": list(release_note.highlights) if release_note is not None else [],
        "release_notes_source": (
            str(release_note.source_path.relative_to(REPO_ROOT))
            if release_note is not None
            else ""
        ),
        "feature_packs": {
            feature_pack.pack_id: {
                "assets": {
                    runtime_platform.slug: bundle_path.name
                    for candidate_pack, runtime_platform, bundle_path in feature_packs
                    if candidate_pack.pack_id == feature_pack.pack_id
                },
                "display_name": feature_pack.display_name,
            }
            for feature_pack in supported_managed_runtime_feature_packs()
        },
        "assets": {
            wheel.name: {"sha256": _sha256(wheel)},
            install_sh.name: {"sha256": _sha256(install_sh)},
            provenance.name: {"sha256": _sha256(provenance)},
            sbom.name: {"sha256": _sha256(sbom)},
            third_party_attribution.name: {"sha256": _sha256(third_party_attribution)},
            **{
                bundle_path.name: {"sha256": _sha256(bundle_path)}
                for _, _, bundle_path in feature_packs
            },
            **{
                bundle_path.name: {"sha256": _sha256(bundle_path)}
                for _, bundle_path in runtime_bundles
            },
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_provenance(
    *,
    output_path: Path,
    tag: str,
    repo: str,
    allow_local: bool,
    feature_packs: list[tuple[ManagedRuntimeFeaturePack, ManagedRuntimePlatform, Path]],
    wheel: Path,
    runtime_bundles: list[tuple[ManagedRuntimePlatform, Path]],
) -> None:
    version = tag.removeprefix("v")
    actor = str(os.getenv("GITHUB_ACTOR") or "").strip()
    if allow_local and repo == AUTHORITATIVE_RELEASE_REPO and not actor:
        actor = AUTHORITATIVE_RELEASE_ACTOR
    payload: dict[str, Any] = {
        "version": PROVENANCE_SCHEMA_VERSION,
        "repo": repo,
        "actor": actor,
        "release_version": version,
        "tag": tag,
        "workflow": {
            "path": WORKFLOW_PATH,
            "ref": WORKFLOW_REF,
            "run_id": os.getenv("GITHUB_RUN_ID", ""),
            "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", ""),
            "sha": os.getenv("GITHUB_SHA", ""),
        },
        "artifacts": {
            "wheel": {
                "name": wheel.name,
                "sha256": _sha256(wheel),
            },
            "runtime_bundles": {
                runtime_platform.slug: {
                    "name": bundle_path.name,
                    "sha256": _sha256(bundle_path),
                }
                for runtime_platform, bundle_path in runtime_bundles
            },
            "feature_packs": {
                feature_pack.pack_id: {
                    runtime_platform.slug: {
                        "name": bundle_path.name,
                        "sha256": _sha256(bundle_path),
                    }
                    for candidate_pack, runtime_platform, bundle_path in feature_packs
                    if candidate_pack.pack_id == feature_pack.pack_id
                }
                for feature_pack in supported_managed_runtime_feature_packs()
            },
        },
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_sbom(*, output_path: Path, tag: str, repo: str, wheel: Path) -> None:
    version = tag.removeprefix("v")
    payload = {
        "SPDXID": "SPDXRef-DOCUMENT",
        "creationInfo": {
            "created": "1970-01-01T00:00:00Z",
            "creators": [f"Tool: odylith-release/{version}"],
        },
        "dataLicense": "CC0-1.0",
        "documentNamespace": f"https://github.com/{repo}/releases/{tag}/sbom",
        "name": f"odylith-{version}",
        "packages": [
            {
                "SPDXID": "SPDXRef-Package-odylith",
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": SBOM_LICENSE,
                "licenseDeclared": SBOM_LICENSE,
                "name": "odylith",
                "packageFileName": wheel.name,
                "supplier": "Organization: freedom-research",
                "versionInfo": version,
            }
        ],
        "relationships": [],
        "spdxVersion": "SPDX-2.3",
    }
    output_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sign_asset(path: Path) -> Path:
    bundle_path = path.with_name(f"{path.name}.sigstore.json")
    _run(
        [
            sys.executable,
            "-m",
            "sigstore",
            "sign",
            "--bundle",
            str(bundle_path),
            "--overwrite",
            str(path),
        ]
    )
    return bundle_path


def _write_placeholder_sigstore_bundle(path: Path) -> Path:
    bundle_path = path.with_name(f"{path.name}.sigstore.json")
    bundle_path.write_text("{}\n", encoding="utf-8")
    return bundle_path


def _release_upload_artifacts(
    *,
    wheel: Path,
    install_sh: Path,
    release_manifest: Path,
    provenance: Path,
    sbom: Path,
    sha256sums: Path,
    third_party_attribution: Path,
    feature_packs: list[tuple[ManagedRuntimeFeaturePack, ManagedRuntimePlatform, Path]],
    runtime_bundles: list[tuple[ManagedRuntimePlatform, Path]],
    signature_bundles: list[Path],
) -> list[Path]:
    return [
        wheel,
        install_sh,
        release_manifest,
        provenance,
        sbom,
        sha256sums,
        third_party_attribution,
        *(path for _, _, path in feature_packs),
        *(path for _, path in runtime_bundles),
        *signature_bundles,
    ]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Publish Odylith GitHub release assets.")
    parser.add_argument("--repo", default="odylith/odylith", help="GitHub repo.")
    parser.add_argument("--tag", required=True, help="Release tag, for example v0.1.0.")
    parser.add_argument("--dist-dir", default="dist", help="Directory containing built wheels.")
    parser.add_argument("--upload", action="store_true", help="Sign and upload the generated assets to GitHub Releases.")
    parser.add_argument(
        "--allow-local",
        action="store_true",
        help="Allow local asset generation outside the canonical GitHub Actions release context.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.upload:
        _require_canonical_release_context(repo=str(args.repo))
    elif not args.allow_local:
        raise ValueError("local asset generation requires --allow-local; canonical upload requires --upload")
    dist_dir = Path(args.dist_dir).expanduser().resolve()
    odylith_wheels = sorted(dist_dir.glob("odylith-*.whl"))
    if len(odylith_wheels) != 1:
        raise ValueError("expected exactly one odylith wheel in dist/")

    wheel = odylith_wheels[0]
    install_sh = dist_dir / "install.sh"
    sha256sums = dist_dir / "SHA256SUMS"
    release_manifest = dist_dir / "release-manifest.json"
    provenance = dist_dir / "build-provenance.v1.json"
    sbom = dist_dir / "odylith.sbom.spdx.json"
    third_party_attribution = dist_dir / "THIRD_PARTY_ATTRIBUTION.md"
    feature_packs = _build_managed_runtime_feature_packs(dist_dir=dist_dir)
    runtime_bundles = _build_managed_runtime_bundles(wheel=wheel, dist_dir=dist_dir)
    third_party_attribution.write_text(
        (REPO_ROOT / "THIRD_PARTY_ATTRIBUTION.md").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    authored_release_note = release_notes.load_release_notes_source(repo_root=REPO_ROOT, version=args.tag.removeprefix("v"))

    _write_install_script(
        output_path=install_sh,
        tag=args.tag,
        repo=args.repo,
        odylith_wheel=wheel.name,
    )
    _write_provenance(
        output_path=provenance,
        tag=args.tag,
        repo=args.repo,
        allow_local=bool(args.allow_local),
        feature_packs=feature_packs,
        wheel=wheel,
        runtime_bundles=runtime_bundles,
    )
    _write_sbom(output_path=sbom, tag=args.tag, repo=args.repo, wheel=wheel)
    _write_release_manifest(
        output_path=release_manifest,
        tag=args.tag,
        repo=args.repo,
        wheel=wheel,
        install_sh=install_sh,
        provenance=provenance,
        sbom=sbom,
        third_party_attribution=third_party_attribution,
        feature_packs=feature_packs,
        runtime_bundles=runtime_bundles,
        release_note=authored_release_note,
    )
    _write_sha256sums(
        output_path=sha256sums,
        files=[
            wheel,
            install_sh,
            release_manifest,
            provenance,
            sbom,
            third_party_attribution,
            *(path for _, _, path in feature_packs),
            *(path for _, path in runtime_bundles),
        ],
    )

    assets_to_publish = [
        wheel,
        install_sh,
        release_manifest,
        provenance,
        sbom,
        third_party_attribution,
        *(path for _, _, path in feature_packs),
        *(path for _, path in runtime_bundles),
    ]
    bundles = [_sign_asset(path) for path in assets_to_publish] if args.upload else [
        _write_placeholder_sigstore_bundle(path) for path in assets_to_publish
    ]

    if not args.upload:
        return 0

    upload_args = [
        "gh",
        "release",
        "upload",
        args.tag,
        *(
            str(path)
            for path in _release_upload_artifacts(
                wheel=wheel,
                install_sh=install_sh,
                release_manifest=release_manifest,
                provenance=provenance,
                sbom=sbom,
                sha256sums=sha256sums,
                third_party_attribution=third_party_attribution,
                feature_packs=feature_packs,
                runtime_bundles=runtime_bundles,
                signature_bundles=bundles,
            )
        ),
        "--repo",
        args.repo,
        "--clobber",
    ]
    _run(upload_args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
