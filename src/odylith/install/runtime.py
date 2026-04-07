from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from datetime import UTC, datetime
from dataclasses import dataclass
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any

from odylith.install.archive_safety import extract_validated_archive, validate_archive_members
from odylith.install.fs import atomic_write_text, fsync_directory, remove_path
from odylith.install.managed_runtime import MANAGED_RUNTIME_ROOT_NAME
from odylith.install.managed_runtime import (
    CONTEXT_ENGINE_FEATURE_PACK_ID,
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
    MANAGED_PYTHON_VERSION,
    MANAGED_RUNTIME_SCHEMA_VERSION,
    MANAGED_RUNTIME_VERIFICATION_FILENAME,
    MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
    managed_runtime_feature_pack_by_id,
)
from odylith.install.paths import repo_runtime_paths
from odylith.install.python_env import PYTHON_ENV_SCRUB_LINES
from odylith.install.release_assets import download_verified_feature_pack
from odylith.install.release_assets import download_verified_release
from odylith.install.runtime_integrity import managed_runtime_integrity_reasons
from odylith.install.runtime_integrity import managed_runtime_launcher_verifier_lines
from odylith.install.runtime_integrity import managed_runtime_trust_matches_verification
from odylith.install.runtime_integrity import write_managed_runtime_trust
from odylith.install.runtime_tree_policy import cleanup_runtime_versions_residue
from odylith.install.runtime_tree_policy import scrub_runtime_tree_metadata

_FALLBACK_PYTHON_RE = re.compile(r'^\s*exec "(?P<python>/[^"]+)"(?: -I)? -m odylith\.cli "\$@"$', re.MULTILINE)
_FALLBACK_SOURCE_ROOT_RE = re.compile(
    r'^\s*export PYTHONPATH="(?P<source>[^"$]+)(?:\$\{PYTHONPATH:\+\:\$PYTHONPATH\})?"$',
    re.MULTILINE,
)
_RUNTIME_WRAPPER_EXEC_RE = re.compile(r'^\s*exec "(?P<python>/[^"]+)"(?: -I)? "\$@"$', re.MULTILINE)
_BOOTSTRAP_LAUNCHER_NAME = "odylith-bootstrap"
_LEGACY_COMPAT_RUNTIME_VERSIONS = {"0.1.0", "0.1.1"}


@dataclass(frozen=True)
class StagedRuntime:
    version: str
    manifest: dict[str, object]
    python: Path
    root: Path
    verification: dict[str, object]


@dataclass(frozen=True)
class StagedRuntimeFeaturePack:
    asset_name: str
    manifest: dict[str, object]
    pack_id: str
    root: Path
    verification: dict[str, object]
    version: str


def _path_within(base: Path, candidate: Path) -> bool:
    try:
        candidate.relative_to(base)
    except ValueError:
        return False
    return True


def _trusted_runtime_root(*, repo_root: str | Path, target: Path | None) -> Path | None:
    if target is None:
        return None
    paths = repo_runtime_paths(repo_root)
    resolved_target = target.expanduser().resolve()
    resolved_versions_dir = paths.versions_dir.expanduser().resolve()
    if not resolved_target.is_dir():
        return None
    if not _path_within(resolved_versions_dir, resolved_target):
        return None
    return resolved_target


def _trusted_runtime_python(*, repo_root: str | Path, python: Path | None) -> Path | None:
    if python is None:
        return None
    candidate = python.expanduser()
    if not candidate.is_absolute():
        candidate = Path(os.path.abspath(candidate))
    if not candidate.is_file():
        return None

    runtime_root = candidate.parent.parent
    trusted_root = _trusted_runtime_root(repo_root=repo_root, target=runtime_root)
    if trusted_root is not None:
        if candidate.parent.name == "bin" and candidate.parent.parent == runtime_root:
            return trusted_root / "bin" / candidate.name

    resolved_python = candidate.resolve()
    resolved_runtime_root = resolved_python.parent.parent
    resolved_trusted_root = _trusted_runtime_root(repo_root=repo_root, target=resolved_runtime_root)
    if resolved_trusted_root is None:
        return None
    expected = resolved_trusted_root / "bin" / resolved_python.name
    if expected != resolved_python or not resolved_python.is_file():
        return None
    return resolved_python


def _normalize_python_path(python: Path | None) -> Path:
    candidate = Path(python or sys.executable).expanduser()
    if not candidate.is_absolute():
        candidate = Path(os.path.abspath(candidate))
    return candidate


def _validated_source_root(source_root: Path | None) -> Path | None:
    if source_root is None:
        return None
    candidate = Path(source_root).expanduser()
    if not candidate.is_absolute():
        candidate = Path(os.path.abspath(candidate))
    try:
        resolved = candidate.resolve()
    except OSError:
        return None
    if not (resolved / "pyproject.toml").is_file():
        return None
    if not (resolved / "src" / "odylith").is_dir():
        return None
    return resolved


def _runtime_wrapper_exec_target(python: Path) -> Path | None:
    if not python.is_file():
        return None
    try:
        text = python.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None
    match = _RUNTIME_WRAPPER_EXEC_RE.search(text)
    if match is None:
        return None
    return _normalize_python_path(Path(str(match.group("python"))))


def _runtime_root_for_python(*, repo_root: str | Path, python: Path | None) -> Path | None:
    trusted = _trusted_runtime_python(repo_root=repo_root, python=python)
    if trusted is None:
        return None
    try:
        return trusted.parent.parent.resolve()
    except OSError:
        return trusted.parent.parent


def _managed_runtime_verification_reasons(runtime_root: Path) -> list[str]:
    metadata = _load_runtime_metadata(runtime_root)
    if not metadata:
        return []
    reasons: list[str] = []
    if str(metadata.get("schema_version") or "").strip() != MANAGED_RUNTIME_SCHEMA_VERSION:
        reasons.append(f"managed runtime metadata schema invalid: {runtime_root}")
        return reasons
    version = str(metadata.get("version") or "").strip()
    runtime_verification = load_runtime_verification(runtime_root)
    if str(runtime_verification.get("schema_version") or "").strip() != MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION:
        reasons.append(f"managed runtime verification missing or invalid: {runtime_root}")
        return reasons
    if str(runtime_verification.get("version") or "").strip() != version:
        reasons.append(f"managed runtime verification version drifted: {runtime_root}")
        return reasons
    evidence = runtime_verification.get("verification")
    if not isinstance(evidence, dict) or not evidence:
        reasons.append(f"managed runtime verification evidence missing: {runtime_root}")
    return reasons


def _managed_runtime_is_verified(runtime_root: Path) -> bool:
    return not _managed_runtime_verification_reasons(runtime_root)


def _managed_runtime_version(runtime_root: Path) -> str:
    metadata = _load_runtime_metadata(runtime_root)
    version = str(metadata.get("version") or "").strip()
    return version or runtime_root.name.strip()


def _legacy_managed_runtime_compatibility_reasons(runtime_root: Path) -> list[str]:
    metadata = _load_runtime_metadata(runtime_root)
    if not metadata:
        return [f"managed runtime metadata missing: {runtime_root}"]
    version = _managed_runtime_version(runtime_root)
    if version not in _LEGACY_COMPAT_RUNTIME_VERSIONS:
        return [f"managed runtime version is not eligible for legacy compatibility: {runtime_root}"]
    if str(metadata.get("schema_version") or "").strip() != MANAGED_RUNTIME_SCHEMA_VERSION:
        return [f"managed runtime metadata schema invalid: {runtime_root}"]
    if str(metadata.get("version") or "").strip() != version:
        return [f"managed runtime metadata version drifted: {runtime_root}"]
    runtime_verification = load_runtime_verification(runtime_root)
    if str(runtime_verification.get("schema_version") or "").strip() != MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION:
        return [f"managed runtime verification missing or invalid: {runtime_root}"]
    if str(runtime_verification.get("version") or "").strip() != version:
        return [f"managed runtime verification version drifted: {runtime_root}"]
    evidence = runtime_verification.get("verification")
    if not isinstance(evidence, dict) or not evidence:
        return [f"managed runtime verification evidence missing: {runtime_root}"]
    python = runtime_root / "bin" / "python"
    if not python.exists():
        return [f"managed runtime python missing: {python}"]
    return []


def _managed_runtime_is_legacy_compatible(runtime_root: Path) -> bool:
    return not _legacy_managed_runtime_compatibility_reasons(runtime_root)


def _managed_runtime_health_reasons(*, repo_root: str | Path, runtime_root: Path) -> list[str]:
    scrub_runtime_tree_metadata(runtime_root)
    if not (runtime_root / "runtime-metadata.json").is_file():
        return []
    reasons = [
        *_managed_runtime_verification_reasons(runtime_root),
        *managed_runtime_integrity_reasons(repo_root=repo_root, runtime_root=runtime_root),
    ]
    if reasons and _managed_runtime_is_legacy_compatible(runtime_root):
        return []
    return reasons


def _managed_runtime_candidate_rank(*, repo_root: str | Path, runtime_root: Path) -> int:
    if not (runtime_root / "runtime-metadata.json").is_file():
        return 2
    if not _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=runtime_root):
        if _managed_runtime_is_legacy_compatible(runtime_root):
            return 1
        return 0
    return 3


def _runtime_candidate_sort_key(*, repo_root: str | Path, runtime_root: Path) -> tuple[int, int, int, int, int, str]:
    has_metadata = (runtime_root / "runtime-metadata.json").is_file()
    has_pyvenv = (runtime_root / "pyvenv.cfg").is_file()
    has_wrapper = _runtime_wrapper_exec_target(runtime_root / "bin" / "python") is not None
    return (
        _managed_runtime_candidate_rank(repo_root=repo_root, runtime_root=runtime_root),
        0 if has_metadata else 1,
        0 if has_pyvenv else 1,
        1 if runtime_root.name == "source-local" else 0,
        1 if has_wrapper else 0,
        runtime_root.name,
    )


def _runtime_root_is_candidate(*, repo_root: str | Path, runtime_root: Path) -> bool:
    python = runtime_root / "bin" / "python"
    if not python.is_file():
        return False
    has_metadata = (runtime_root / "runtime-metadata.json").is_file()
    has_pyvenv = (runtime_root / "pyvenv.cfg").is_file()
    has_wrapper = _runtime_wrapper_exec_target(python) is not None
    if not (has_metadata or has_pyvenv or has_wrapper):
        return False
    if has_metadata and _managed_runtime_candidate_rank(repo_root=repo_root, runtime_root=runtime_root) == 3:
        return False
    return True


def _unwrap_runtime_wrapper_python(*, repo_root: str | Path, python: Path | None) -> Path | None:
    current = _normalize_python_path(python)
    visited: set[tuple[str, str]] = set()
    while True:
        trusted = _trusted_runtime_python(repo_root=repo_root, python=current)
        if trusted is not None:
            current = trusted
        try:
            resolved = str(current.resolve())
        except OSError:
            resolved = str(current)
        key = (str(current), resolved)
        if key in visited:
            return None
        visited.add(key)
        target = _runtime_wrapper_exec_target(current)
        if target is None:
            return current
        current = target


def _preferred_wrapped_runtime_fallback(
    *,
    repo_root: str | Path,
    version_root: Path | None,
    fallback_python: Path | None,
    allow_host_python_fallback: bool = False,
) -> Path:
    candidate = _normalize_python_path(fallback_python)
    trusted_candidate = _trusted_runtime_python(repo_root=repo_root, python=candidate)
    if trusted_candidate is not None:
        trusted_root = _runtime_root_for_python(repo_root=repo_root, python=trusted_candidate)
        if trusted_root is not None and _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=trusted_root):
            trusted_candidate = None
    if trusted_candidate is not None:
        trusted_unwrapped = _unwrap_runtime_wrapper_python(
            repo_root=repo_root,
            python=trusted_candidate,
        )
        if trusted_unwrapped is not None:
            trusted_target = _runtime_wrapper_exec_target(trusted_candidate)
            if trusted_target is not None and version_root is not None:
                try:
                    resolved_version_root = version_root.expanduser().resolve()
                except OSError:
                    resolved_version_root = version_root.expanduser()
                try:
                    resolved_trusted_root = trusted_candidate.parent.parent.resolve()
                except OSError:
                    resolved_trusted_root = trusted_candidate.parent.parent
                if resolved_trusted_root == resolved_version_root and not (
                    resolved_version_root / "runtime-metadata.json"
                ).is_file():
                    unwrapped_runtime_root = _runtime_root_for_python(repo_root=repo_root, python=trusted_unwrapped)
                    if unwrapped_runtime_root is None or not (unwrapped_runtime_root / "runtime-metadata.json").is_file() or not _managed_runtime_health_reasons(
                        repo_root=repo_root,
                        runtime_root=unwrapped_runtime_root,
                    ):
                        return trusted_unwrapped
            return trusted_candidate

    unwrapped = _unwrap_runtime_wrapper_python(repo_root=repo_root, python=candidate)
    if unwrapped is not None:
        unwrapped_runtime_root = _runtime_root_for_python(repo_root=repo_root, python=unwrapped)
        if unwrapped_runtime_root is None or not (unwrapped_runtime_root / "runtime-metadata.json").is_file() or not _managed_runtime_health_reasons(
            repo_root=repo_root,
            runtime_root=unwrapped_runtime_root,
        ):
            if allow_host_python_fallback or _trusted_runtime_python(repo_root=repo_root, python=unwrapped) is not None:
                return unwrapped

    excluded_roots: set[Path] = set()
    if version_root is not None:
        try:
            excluded_roots.add(version_root.expanduser().resolve())
        except OSError:
            pass

    paths = repo_runtime_paths(repo_root)
    roots = sorted(
        (
            path
            for path in paths.versions_dir.glob("*")
            if path.is_dir() and _runtime_root_is_candidate(repo_root=repo_root, runtime_root=path)
        ),
        key=lambda candidate_root: _runtime_candidate_sort_key(repo_root=repo_root, runtime_root=candidate_root),
    )
    for root in roots:
        try:
            resolved_root = root.expanduser().resolve()
        except OSError:
            continue
        if resolved_root in excluded_roots:
            continue
        preferred = _unwrap_runtime_wrapper_python(
            repo_root=repo_root,
            python=resolved_root / "bin" / "python",
        )
        if preferred is not None:
            trusted_preferred = _trusted_runtime_python(
                repo_root=repo_root,
                python=resolved_root / "bin" / "python",
            )
            return trusted_preferred or preferred

    if allow_host_python_fallback:
        host_candidate = _unwrap_runtime_wrapper_python(repo_root=repo_root, python=Path(sys.executable))
        if host_candidate is not None:
            return host_candidate
        return candidate

    raise ValueError(
        "wrapped runtime fallback python must stay inside `.odylith/runtime/versions/` unless host-python fallback is explicitly allowed"
    )


def _venv_python(venv_root: Path) -> Path:
    candidate = venv_root / "bin" / "python"
    if not candidate.is_file():
        raise ValueError(f"runtime python missing: {candidate}")
    return candidate


def _runtime_python(runtime_root: Path | None) -> Path | None:
    if runtime_root is None:
        return None
    candidate = runtime_root / "bin" / "python"
    return candidate if candidate.is_file() else None


def runtime_verification_path(version_root: Path) -> Path:
    return version_root / MANAGED_RUNTIME_VERIFICATION_FILENAME


def load_runtime_verification(version_root: Path) -> dict[str, object]:
    path = runtime_verification_path(version_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def runtime_verification_evidence(version_root: Path) -> dict[str, object]:
    payload = load_runtime_verification(version_root)
    verification = payload.get("verification")
    return dict(verification) if isinstance(verification, dict) else {}


def runtime_feature_packs_path(version_root: Path) -> Path:
    return version_root / MANAGED_RUNTIME_FEATURE_PACK_FILENAME


def load_runtime_feature_packs(version_root: Path) -> dict[str, dict[str, object]]:
    path = runtime_feature_packs_path(version_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if str(payload.get("schema_version") or "").strip() != MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION:
        return {}
    packs_payload = payload.get("packs")
    if not isinstance(packs_payload, dict):
        return {}
    packs: dict[str, dict[str, object]] = {}
    for pack_id, details in packs_payload.items():
        resolved_pack_id = str(pack_id or "").strip()
        if not resolved_pack_id or not isinstance(details, dict):
            continue
        packs[resolved_pack_id] = dict(details)
    return packs


def runtime_feature_pack_installed(*, version_root: Path, pack_id: str) -> bool:
    return str(pack_id).strip() in load_runtime_feature_packs(version_root)


def runtime_context_engine_feature_pack_installed(version_root: Path | None) -> bool:
    if version_root is None:
        return False
    return runtime_feature_pack_installed(version_root=version_root, pack_id=CONTEXT_ENGINE_FEATURE_PACK_ID)


def _write_runtime_feature_packs(
    version_root: Path,
    *,
    version: str,
    packs: dict[str, dict[str, object]],
) -> Path:
    path = runtime_feature_packs_path(version_root)
    payload = {
        "schema_version": MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
        "version": str(version).strip(),
        "packs": packs,
    }
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _load_runtime_metadata(version_root: Path) -> dict[str, object]:
    path = version_root / "runtime-metadata.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def _write_runtime_verification(
    version_root: Path,
    *,
    version: str,
    verification: dict[str, object],
) -> Path:
    path = runtime_verification_path(version_root)
    payload = {
        "schema_version": MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION,
        "version": str(version).strip(),
        "verification": dict(verification),
    }
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _runtime_matches_verified_release(*, repo_root: str | Path, version_root: Path, verified_release) -> bool:  # noqa: ANN001
    python = version_root / "bin" / "python"
    python3 = version_root / "bin" / "python3"
    odylith = version_root / "bin" / "odylith"
    if not python.is_file() or not python3.is_file() or not odylith.is_file():
        return False
    metadata = _load_runtime_metadata(version_root)
    if not metadata:
        return False
    if str(metadata.get("schema_version") or "").strip() != MANAGED_RUNTIME_SCHEMA_VERSION:
        return False
    if str(metadata.get("version") or "").strip() != verified_release.version:
        return False
    if str(metadata.get("platform") or "").strip() != verified_release.runtime_platform.slug:
        return False
    if str(metadata.get("python_version") or "").strip() != MANAGED_PYTHON_VERSION:
        return False
    if str(metadata.get("source_wheel") or "").strip() != verified_release.wheel_path.name:
        return False
    runtime_verification = load_runtime_verification(version_root)
    if str(runtime_verification.get("schema_version") or "").strip() != MANAGED_RUNTIME_VERIFICATION_SCHEMA_VERSION:
        return False
    if str(runtime_verification.get("version") or "").strip() != verified_release.version:
        return False
    stored_verification = runtime_verification.get("verification")
    if not isinstance(stored_verification, dict):
        return False
    if stored_verification != verified_release.verification:
        return False
    if not managed_runtime_trust_matches_verification(
        repo_root=repo_root,
        version=version_root.name,
        verification=verified_release.verification,
    ):
        return False
    return not managed_runtime_integrity_reasons(repo_root=repo_root, runtime_root=version_root)


def _runtime_feature_pack_matches_verified_release(*, version_root: Path, verified_feature_pack) -> bool:  # noqa: ANN001
    packs = load_runtime_feature_packs(version_root)
    details = packs.get(verified_feature_pack.pack_id)
    if not isinstance(details, dict):
        return False
    if str(details.get("asset_name") or "").strip() != verified_feature_pack.asset_name:
        return False
    if str(details.get("platform") or "").strip() != verified_feature_pack.runtime_platform.slug:
        return False
    stored_verification = details.get("verification")
    if not isinstance(stored_verification, dict):
        return False
    return stored_verification == verified_feature_pack.verification


def _write_runtime_wrapper(
    *,
    version_root: Path,
    fallback_python: Path,
    source_root: Path | None = None,
) -> Path:
    fallback = Path(fallback_python).expanduser()
    if not fallback.is_absolute():
        fallback = Path(os.path.abspath(fallback))
    resolved_source_root = _validated_source_root(source_root)
    if source_root is not None and resolved_source_root is None:
        raise ValueError(f"source root is not a valid Odylith checkout: {source_root}")
    python_wrapper = version_root / "bin" / "python"
    python_wrapper.parent.mkdir(parents=True, exist_ok=True)
    export_line = ""
    if resolved_source_root is not None:
        source_src = resolved_source_root / "src"
        export_line = f'export PYTHONPATH="{source_src}${{PYTHONPATH:+:$PYTHONPATH}}"'
    exec_line = f'exec "{fallback}" "$@"'
    if source_root is None:
        exec_line = f'exec "{fallback}" -I "$@"'
    atomic_write_text(
        python_wrapper,
        "\n".join(
            [
                "#!/usr/bin/env bash",
                "set -euo pipefail",
                *PYTHON_ENV_SCRUB_LINES,
                *([export_line] if export_line else []),
                exec_line,
                "",
            ]
        ),
    )
    python_wrapper.chmod(0o755)
    return version_root


def _discover_source_root() -> Path | None:
    return _validated_source_root(Path(__file__).resolve().parents[3])


def _repo_local_source_root(*, repo_root: str | Path) -> Path | None:
    return _validated_source_root(Path(repo_root).expanduser().resolve())


def _launcher_shell_common_lines(*, fallback_source_root: Path | None) -> list[str]:
    resolved_source_root = _validated_source_root(fallback_source_root)
    source_src = str(resolved_source_root / "src") if resolved_source_root is not None else ""
    return [
        f'fallback_source_root="{source_src}"',
        "odylith_valid_source_root() {",
        '  local candidate="${1:-}"',
        '  [[ -n "$candidate" ]] || return 1',
        '  candidate="${candidate%/}"',
        '  if [[ "$candidate" == */src ]]; then',
        '    candidate="${candidate%/src}"',
        "  fi",
        '  [[ -f "$candidate/pyproject.toml" ]] && [[ -d "$candidate/src/odylith" ]]',
        "}",
        "odylith_repo_source_python() {",
        "  odylith_is_product_repo || return 1",
        '  if [[ -x "$repo_root/.venv/bin/python" ]]; then',
        '    printf "%s\\n" "$repo_root/.venv/bin/python"',
        "    return 0",
        "  fi",
        "  if command -v python3 >/dev/null 2>&1; then",
        '    command -v python3',
        "    return 0",
        "  fi",
        "  if command -v python >/dev/null 2>&1; then",
        '    command -v python',
        "    return 0",
        "  fi",
        "  return 1",
        "}",
        "odylith_runtime_root_for_python() {",
        '  local python_path="${1:-}"',
        '  [[ -n "$python_path" ]] || return 1',
        '  (cd "$(dirname "$python_path")/.." && pwd -P)',
        "}",
        "odylith_resolved_versions_dir() {",
        '  [[ -d "$state_root/runtime/versions" ]] || return 1',
        '  (cd "$state_root/runtime/versions" && pwd -P)',
        "}",
        "odylith_path_within() {",
        '  local base="${1:-}" candidate="${2:-}"',
        '  [[ -n "$base" ]] && [[ -n "$candidate" ]] || return 1',
        '  [[ "$candidate" == "$base" || "$candidate" == "$base/"* ]]',
        "}",
        "odylith_managed_runtime_trusted() {",
        '  local runtime_root="${1:-}"',
        '  [[ -n "$runtime_root" ]] || return 1',
        f'  [[ -f "$runtime_root/runtime-metadata.json" ]] && [[ -f "$runtime_root/{MANAGED_RUNTIME_VERIFICATION_FILENAME}" ]]',
        "}",
        "odylith_legacy_managed_runtime_compatible() {",
        '  local runtime_root="${1:-}" version_name=""',
        '  [[ -n "$runtime_root" ]] || return 1',
        '  [[ -f "$runtime_root/runtime-metadata.json" ]] && [[ ! -L "$runtime_root/runtime-metadata.json" ]] || return 1',
        f'  [[ -f "$runtime_root/{MANAGED_RUNTIME_VERIFICATION_FILENAME}" ]] && [[ ! -L "$runtime_root/{MANAGED_RUNTIME_VERIFICATION_FILENAME}" ]] || return 1',
        '  version_name="$(basename "$runtime_root")"',
        '  case "$version_name" in',
        "    0.1.0|0.1.1) return 0 ;;",
        "    *) return 1 ;;",
        "  esac",
        "}",
        "odylith_sha256_file() {",
        '  local candidate="${1:-}"',
        '  [[ -f "$candidate" ]] || return 1',
        '  if command -v shasum >/dev/null 2>&1; then',
        '    shasum -a 256 "$candidate" | awk \'{print $1}\'',
        "    return 0",
        "  fi",
        '  if command -v sha256sum >/dev/null 2>&1; then',
        '    sha256sum "$candidate" | awk \'{print $1}\'',
        "    return 0",
        "  fi",
        "  return 1",
        "}",
        "odylith_runtime_trust_file() {",
        '  local runtime_root="${1:-}" version_name="" primary="" legacy=""',
        '  [[ -n "$runtime_root" ]] || return 1',
        '  version_name="$(basename "$runtime_root")"',
        '  [[ -n "$version_name" ]] || return 1',
        '  primary="$repo_root/.odylith/trust/managed-runtime-trust/$version_name.env"',
        '  legacy="$repo_root/odylith/runtime/source/managed-runtime-trust/$version_name.env"',
        '  if [[ -f "$primary" ]] && [[ ! -L "$primary" ]]; then',
        '    printf "%s\\n" "$primary"',
        "    return 0",
        "  fi",
        '  if [[ -f "$legacy" ]] && [[ ! -L "$legacy" ]]; then',
        '    printf "%s\\n" "$legacy"',
        "    return 0",
        "  fi",
        '  printf "%s\\n" "$primary"',
        "}",
        "odylith_runtime_trust_value() {",
        '  local trust_file="${1:-}" key="${2:-}"',
        '  [[ -f "$trust_file" ]] && [[ ! -L "$trust_file" ]] || return 1',
        '  [[ -n "$key" ]] || return 1',
        '  sed -n "s/^${key}=//p" "$trust_file" | head -n 1',
        "}",
        "odylith_wrapper_target() {",
        '  local python_path="${1:-}"',
        '  [[ -f "$python_path" ]] || return 1',
        "  LC_ALL=C sed -n 's#^[[:space:]]*exec \"\\([^\"]*\\)\".*#\\1#p' \"$python_path\" | head -n 1",
        "}",
        "odylith_wrapper_source_root() {",
        '  local python_path="${1:-}"',
        '  [[ -f "$python_path" ]] || return 1',
        "  LC_ALL=C sed -n 's#^[[:space:]]*export PYTHONPATH=\"\\([^$\"]*\\).*#\\1#p' \"$python_path\" | head -n 1",
        "}",
        "odylith_wrapper_python_trusted() {",
        '  local python_path="${1:-}"',
        '  local target="" target_root="" wrapper_root="" wrapper_source=""',
        '  [[ -x "$python_path" ]] || return 1',
        '  target="$(odylith_wrapper_target "$python_path")"',
        '  [[ -n "$target" ]] || return 1',
        '  [[ "$target" != "$python_path" ]] || return 1',
        '  [[ "$target" != "$current_python" ]] || return 1',
        '  [[ "$target" != "$state_root/runtime/current/bin/python" ]] || return 1',
        '  [[ -x "$target" ]] || return 1',
        '  target_root="$(odylith_runtime_root_for_python "$target")"',
        '  wrapper_root="$(odylith_runtime_root_for_python "$python_path")"',
        '  if ! odylith_managed_runtime_trusted "$target_root"; then',
        '    if ! odylith_is_product_repo || [[ -z "$wrapper_root" ]] || [[ -f "$wrapper_root/runtime-metadata.json" ]]; then',
        "      return 1",
        "    fi",
        "  fi",
        '  wrapper_source="$(odylith_wrapper_source_root "$python_path")"',
        '  [[ -z "$wrapper_source" ]] || odylith_valid_source_root "$wrapper_source"',
        "}",
        "odylith_managed_runtime_launch_ready() {",
        '  local runtime_root="${1:-}" python_path="${2:-}" trust_file="" expected_python=""',
        '  [[ -n "$runtime_root" ]] || return 1',
        '  [[ -n "$python_path" ]] || return 1',
        '  odylith_managed_runtime_trusted "$runtime_root" || return 1',
        '  trust_file="$(odylith_runtime_trust_file "$runtime_root")"',
        '  [[ -f "$trust_file" ]] && [[ ! -L "$trust_file" ]] || return 1',
        '  expected_python="$(odylith_runtime_trust_value "$trust_file" "BIN_PYTHON_SHA256")"',
        '  [[ -n "$expected_python" ]] || return 1',
        '  [[ "$(odylith_sha256_file "$python_path")" == "$expected_python" ]] || return 1',
        '  "$python_path" -I - "$runtime_root" "$trust_file" <<'"'"'PY'"'"'',
        *managed_runtime_launcher_verifier_lines(),
        "PY",
        "}",
        "odylith_current_python_trusted() {",
        '  local current_root_resolved=""',
        '  [[ -x "$current_python" ]] || return 1',
        '  current_root_resolved="$(odylith_runtime_root_for_python "$current_python" || true)"',
        '  [[ -n "$current_root_resolved" ]] || current_root_resolved="$current_root"',
        '  if odylith_managed_runtime_trusted "$current_root_resolved"; then',
        '    odylith_managed_runtime_launch_ready "$current_root_resolved" "$current_python" && return 0',
        '    odylith_legacy_managed_runtime_compatible "$current_root_resolved" && return 0',
        "    return 1",
        "  fi",
        '  odylith_wrapper_python_trusted "$current_python"',
        "}",
        "odylith_fallback_python_trusted() {",
        '  local fallback_root="" versions_dir=""',
        '  [[ -x "$fallback_python" ]] || return 1',
        '  if [[ -n "$fallback_source_root" ]]; then',
        '    odylith_valid_source_root "$fallback_source_root" || return 1',
        "    return 0",
        "  fi",
        '  fallback_root="$(odylith_runtime_root_for_python "$fallback_python" || true)"',
        '  versions_dir="$(odylith_resolved_versions_dir || true)"',
        '  if [[ -n "$fallback_root" ]] && [[ -n "$versions_dir" ]] && odylith_path_within "$versions_dir" "$fallback_root"; then',
        '    if [[ -f "$fallback_root/runtime-metadata.json" ]]; then',
        '      odylith_managed_runtime_launch_ready "$fallback_root" "$fallback_python" || odylith_legacy_managed_runtime_compatible "$fallback_root" || return 1',
        "    fi",
        "    return 0",
        "  fi",
        '  odylith_wrapper_python_trusted "$fallback_python"',
        '  if odylith_is_product_repo; then',
        "    return 0",
        "  fi",
        "  return 1",
        "}",
    ]


def _launcher_script(*, fallback_python: Path, fallback_source_root: Path | None = None) -> str:
    fallback_path = fallback_python.expanduser()
    if not fallback_path.is_absolute():
        fallback_path = Path(os.path.abspath(fallback_path))
    fallback = str(fallback_path)
    resolved_source_root = _validated_source_root(fallback_source_root)
    export_line = ""
    if resolved_source_root is not None:
        source_src = str(resolved_source_root / "src")
        export_line = f'export PYTHONPATH="{source_src}${{PYTHONPATH:+:$PYTHONPATH}}"'
    fallback_exec = f'exec "{fallback}" -I -m odylith.cli "$@"'
    if resolved_source_root is not None:
        fallback_exec = f'exec "{fallback}" -m odylith.cli "$@"'
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            *PYTHON_ENV_SCRUB_LINES,
            'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'state_root="$(cd "$script_dir/.." && pwd)"',
            'repo_root="$(cd "$state_root/.." && pwd)"',
            'current_root="$state_root/runtime/current"',
            'current_python="$state_root/runtime/current/bin/python"',
            f'fallback_python="{fallback}"',
            *_launcher_shell_common_lines(fallback_source_root=resolved_source_root),
            "odylith_is_product_repo() {",
            '  [[ -f "$repo_root/pyproject.toml" ]] && [[ -d "$repo_root/src/odylith" ]] && [[ -f "$repo_root/odylith/registry/source/component_registry.v1.json" ]] && [[ -f "$repo_root/odylith/radar/source/INDEX.md" ]]',
            "}",
            "odylith_upgrade_bootstrap_required() {",
            '  if [[ "${ODYLITH_LAUNCHER_SKIP_BOOTSTRAP_UPGRADE:-}" == "1" ]]; then',
            "    return 1",
            "  fi",
            '  if [[ "${ODYLITH_LAUNCHER_BOOTSTRAPPED:-}" == "1" ]]; then',
            "    return 1",
            "  fi",
            '  if [[ "${ODYLITH_FORCE_BOOTSTRAP_UPGRADE:-}" == "1" ]]; then',
            "    return 0",
            "  fi",
            '  if [[ "${1:-}" != "upgrade" ]]; then',
            "    return 1",
            "  fi",
            "  if odylith_is_product_repo; then",
            "    return 1",
            "  fi",
            "  shift",
            '  while (($#)); do',
            '    case "$1" in',
            "      --to|--version|--release-repo|--source-repo|--write-pin)",
            "        return 1",
            "        ;;",
            "    esac",
            "    shift",
            "  done",
            '  if [[ ! -f "$current_root/runtime-metadata.json" ]]; then',
            "    return 1",
            "  fi",
            '  bootstrap_python="$fallback_python"',
            '  if odylith_current_python_trusted; then',
            '    bootstrap_python="$current_python"',
            "  fi",
            '  if [[ ! -x "$bootstrap_python" ]]; then',
            "    return 1",
            "  fi",
            '  if [[ "$bootstrap_python" == "$fallback_python" ]] && ! odylith_fallback_python_trusted; then',
            "    return 1",
            "  fi",
            '  current_version="$("$bootstrap_python" - "$current_root/runtime-metadata.json" <<'"'"'PY'"'"'\n'
            "import json\n"
            "import sys\n"
            "from pathlib import Path\n"
            "path = Path(sys.argv[1])\n"
            "try:\n"
            "    payload = json.loads(path.read_text(encoding='utf-8'))\n"
            "except Exception:\n"
            "    print('')\n"
            "    raise SystemExit(0)\n"
            "print(str(payload.get('version') or '').strip())\n"
            "PY\n"
            ')"',
            '  case "$current_version" in',
            "    0.1.0|0.1.1) return 0 ;;",
            "    *) return 1 ;;",
            "  esac",
            "}",
            "odylith_bootstrap_upgrade_via_installer() {",
            '  if ! command -v curl >/dev/null 2>&1; then',
            '    echo "Odylith safe-upgrade bootstrap requires curl. Rerun the hosted installer manually." >&2',
            "    exit 2",
            "  fi",
            '  local install_url local_release_base_url tmp_install',
            '  local_release_base_url="${ODYLITH_RELEASE_BASE_URL:-}"',
            '  if [[ -n "$local_release_base_url" ]]; then',
            '    install_url="${local_release_base_url%/}/install.sh"',
            "  else",
            '    install_url="https://odylith.ai/install.sh"',
            "  fi",
            '  tmp_install="$(mktemp "${TMPDIR:-/tmp}/odylith-install.XXXXXX.sh")"',
            '  case "$install_url" in',
            '    http://127.0.0.1/*|http://127.0.0.1:*/*|http://localhost/*|http://localhost:*/*|http://[::1]/*|http://[::1]:*/*)',
            '      curl --fail --show-error --silent --location --retry 3 --retry-connrefused --retry-delay 1 "$install_url" -o "$tmp_install"',
            "      ;;",
            "    *)",
            '      curl --fail --show-error --silent --location --proto "=https" --tlsv1.2 --retry 3 --retry-connrefused --retry-delay 1 "$install_url" -o "$tmp_install"',
            "      ;;",
            "  esac",
            '  echo "Odylith is bootstrapping a safe upgrade path for this older consumer install." >&2',
            "  (",
            '    cd "$repo_root"',
            '    ODYLITH_NO_BROWSER=1 ODYLITH_VERSION=latest bash "$tmp_install"',
            "  )",
            '  rm -f "$tmp_install"',
            '  exec env ODYLITH_LAUNCHER_BOOTSTRAPPED=1 "$state_root/bin/odylith" "$@"',
            "}",
            'if odylith_upgrade_bootstrap_required "$@"; then',
            '  odylith_bootstrap_upgrade_via_installer "$@"',
            "fi",
            'if odylith_current_python_trusted; then',
            '  if odylith_managed_runtime_trusted "$current_root"; then',
            '    exec "$current_python" -I -m odylith.cli "$@"',
            "  fi",
            '  exec "$current_python" -m odylith.cli "$@"',
            "fi",
            'if odylith_fallback_python_trusted; then',
            *([export_line] if export_line else []),
            f"  {fallback_exec}",
            "fi",
            'if odylith_is_product_repo && odylith_valid_source_root "$repo_root"; then',
            '  repo_source_python="$(odylith_repo_source_python || true)"',
            '  if [[ -n "$repo_source_python" ]] && [[ -x "$repo_source_python" ]]; then',
            '    export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"',
            '    exec "$repo_source_python" -m odylith.cli "$@"',
            "  fi",
            "fi",
            """printf '%s\\n' 'Odylith launcher detected untrusted or unhealthy runtime state. From the repo root, try `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`.' >&2""",
            "exit 1",
            "",
        ]
    )


def _bootstrap_launcher_script(*, fallback_python: Path, fallback_source_root: Path | None = None) -> str:
    fallback_path = fallback_python.expanduser()
    if not fallback_path.is_absolute():
        fallback_path = Path(os.path.abspath(fallback_path))
    fallback = str(fallback_path)
    resolved_source_root = _validated_source_root(fallback_source_root)
    export_line = ""
    if resolved_source_root is not None:
        source_src = str(resolved_source_root / "src")
        export_line = f'export PYTHONPATH="{source_src}${{PYTHONPATH:+:$PYTHONPATH}}"'
    fallback_exec = f'exec "{fallback}" -I -m odylith.cli "$@"'
    if resolved_source_root is not None:
        fallback_exec = f'exec "{fallback}" -m odylith.cli "$@"'
    return "\n".join(
        [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            *PYTHON_ENV_SCRUB_LINES,
            'script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"',
            'state_root="$(cd "$script_dir/.." && pwd)"',
            'repo_root="$(cd "$state_root/.." && pwd)"',
            'current_root="$state_root/runtime/current"',
            'current_python="$state_root/runtime/current/bin/python"',
            f'fallback_python="{fallback}"',
            *_launcher_shell_common_lines(fallback_source_root=resolved_source_root),
            'candidate_python=""',
            'candidate_root=""',
            "odylith_is_product_repo() {",
            '  [[ -f "$repo_root/pyproject.toml" ]] && [[ -d "$repo_root/src/odylith" ]] && [[ -f "$repo_root/odylith/registry/source/component_registry.v1.json" ]] && [[ -f "$repo_root/odylith/radar/source/INDEX.md" ]]',
            "}",
            'if odylith_current_python_trusted; then',
            '  if odylith_managed_runtime_trusted "$current_root"; then',
            '    exec "$current_python" -I -m odylith.cli "$@"',
            "  fi",
            '  exec "$current_python" -m odylith.cli "$@"',
            "fi",
            'if odylith_fallback_python_trusted; then',
            *([export_line] if export_line else []),
            f"  {fallback_exec}",
            "fi",
            'if odylith_is_product_repo && odylith_valid_source_root "$repo_root"; then',
            '  repo_source_python="$(odylith_repo_source_python || true)"',
            '  if [[ -n "$repo_source_python" ]] && [[ -x "$repo_source_python" ]]; then',
            '    export PYTHONPATH="$repo_root/src${PYTHONPATH:+:$PYTHONPATH}"',
            '    exec "$repo_source_python" -m odylith.cli "$@"',
            "  fi",
            "fi",
            'shopt -s nullglob',
            'candidates=("$state_root"/runtime/versions/*/bin/python)',
            'for candidate_python in "${candidates[@]}"; do',
            '  candidate_root="$(cd "$(dirname "$candidate_python")/.." && pwd)"',
            '  if odylith_managed_runtime_launch_ready "$candidate_root" "$candidate_python"; then',
                '    exec "$candidate_python" -I -m odylith.cli "$@"',
            "  fi",
            "done",
            'for candidate_python in "${candidates[@]}"; do',
            '  candidate_root="$(cd "$(dirname "$candidate_python")/.." && pwd)"',
            '  if odylith_legacy_managed_runtime_compatible "$candidate_root"; then',
                '    exec "$candidate_python" -I -m odylith.cli "$@"',
            "  fi",
            "done",
            'if odylith_is_product_repo; then',
            '  for candidate_python in "${candidates[@]}"; do',
            '    candidate_root="$(cd "$(dirname "$candidate_python")/.." && pwd)"',
            '    if [[ "$candidate_root" == "$state_root/runtime/versions/source-local" ]] && odylith_wrapper_python_trusted "$candidate_python"; then',
            '      exec "$candidate_python" -m odylith.cli "$@"',
            "    fi",
            "  done",
            "fi",
            """printf '%s\\n' 'Odylith bootstrap could not find a trusted repo-local runtime. From the repo root, try `./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair`; rerun the hosted installer only if no trusted repo-local runtime is left.' >&2""",
            "exit 1",
            "",
        ]
    )


def _launcher_fallback_python(launcher_path: Path) -> Path | None:
    if not launcher_path.is_file():
        return None
    match = _FALLBACK_PYTHON_RE.search(launcher_path.read_text(encoding="utf-8"))
    if match is None:
        return None
    candidate = Path(str(match.group("python"))).expanduser().resolve()
    return candidate


def _launcher_fallback_source_root_from_path(launcher_path: Path) -> Path | None:
    if not launcher_path.is_file():
        return None
    match = _FALLBACK_SOURCE_ROOT_RE.search(launcher_path.read_text(encoding="utf-8"))
    if match is None:
        return None
    candidate = Path(str(match.group("source"))).expanduser()
    return _validated_source_root(candidate.parent if candidate.name == "src" else candidate)


def _launcher_health_reasons(*, repo_root: str | Path, launcher_path: Path, label: str) -> list[str]:
    reasons: list[str] = []
    if not launcher_path.is_file():
        reasons.append(f"{label} missing")
        return reasons
    launcher_body = launcher_path.read_text(encoding="utf-8")
    if "runtime/current/bin/python" not in launcher_body:
        reasons.append(f"{label} target drifted")
    repo_source_root = _repo_local_source_root(repo_root=repo_root)
    fallback_python = _launcher_fallback_python(launcher_path)
    if fallback_python is None:
        if repo_source_root is None:
            reasons.append(f"{label} fallback missing")
    elif not fallback_python.is_file():
        if repo_source_root is None:
            reasons.append(f"{label} fallback target missing")
    else:
        fallback_source_root = _launcher_fallback_source_root_from_path(launcher_path)
        trusted_fallback = _trusted_runtime_python(repo_root=repo_root, python=fallback_python)
        if fallback_source_root is None and trusted_fallback is None and repo_source_root is None:
            reasons.append(f"{label} fallback target untrusted")
        if trusted_fallback is not None:
            trusted_root = _runtime_root_for_python(repo_root=repo_root, python=trusted_fallback)
            if trusted_root is not None:
                reasons.extend(
                    f"{label} {reason}"
                    for reason in _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=trusted_root)
                )
    return reasons


def preferred_repair_entrypoint(*, repo_root: str | Path) -> str:
    paths = repo_runtime_paths(repo_root)
    bootstrap_path = paths.bin_dir / _BOOTSTRAP_LAUNCHER_NAME
    if paths.launcher_path.is_file() and not _launcher_health_reasons(
        repo_root=repo_root,
        launcher_path=paths.launcher_path,
        label="repo launcher",
    ):
        return "./.odylith/bin/odylith doctor --repo-root . --repair"
    if bootstrap_path.is_file() and not _launcher_health_reasons(
        repo_root=repo_root,
        launcher_path=bootstrap_path,
        label="bootstrap launcher",
    ):
        return "./.odylith/bin/odylith-bootstrap doctor --repo-root . --repair"
    return ""


def current_runtime_root(*, repo_root: str | Path) -> Path | None:
    paths = repo_runtime_paths(repo_root)
    if not paths.current_runtime.is_symlink():
        return None
    try:
        target = paths.current_runtime.resolve(strict=True)
    except FileNotFoundError:
        return None
    return _trusted_runtime_root(repo_root=repo_root, target=target)


def current_runtime_version(*, repo_root: str | Path) -> str:
    runtime_root = current_runtime_root(repo_root=repo_root)
    if runtime_root is None:
        return ""
    return runtime_root.name.strip()


def runtime_root_for_version(*, repo_root: str | Path, version: str) -> Path:
    return repo_runtime_paths(repo_root).versions_dir / str(version).strip()


def ensure_source_runtime(
    *,
    repo_root: str | Path,
    fallback_python: Path | None = None,
    source_root: Path | None = None,
) -> Path | None:
    resolved_source_root = _validated_source_root(source_root) if source_root is not None else _discover_source_root()
    if resolved_source_root is None:
        return None
    return ensure_wrapped_runtime(
        repo_root=repo_root,
        version="source-local",
        fallback_python=fallback_python or Path(sys.executable),
        source_root=resolved_source_root,
        allow_host_python_fallback=True,
    )


def ensure_wrapped_runtime(
    *,
    repo_root: str | Path,
    version: str,
    fallback_python: Path | None = None,
    source_root: Path | None = None,
    allow_host_python_fallback: bool = False,
) -> Path:
    paths = repo_runtime_paths(repo_root)
    resolved_version = str(version or "").strip()
    if not resolved_version:
        raise ValueError("runtime wrapper version is required")
    version_root = paths.versions_dir / resolved_version
    cleanup_runtime_versions_residue(paths.versions_dir, version=resolved_version)
    fallback = _preferred_wrapped_runtime_fallback(
        repo_root=repo_root,
        version_root=version_root,
        fallback_python=fallback_python,
        allow_host_python_fallback=allow_host_python_fallback,
    )
    _write_runtime_wrapper(
        version_root=version_root,
        fallback_python=fallback,
        source_root=source_root,
    )
    switch_runtime(repo_root=repo_root, target=version_root)
    return version_root


def ensure_launcher(
    *,
    repo_root: str | Path,
    fallback_python: Path | None = None,
    fallback_source_root: Path | None = None,
    allow_host_python_fallback: bool = False,
) -> Path:
    paths = repo_runtime_paths(repo_root)
    try:
        fallback = _preferred_wrapped_runtime_fallback(
            repo_root=repo_root,
            version_root=current_runtime_root(repo_root=repo_root),
            fallback_python=fallback_python,
            allow_host_python_fallback=allow_host_python_fallback,
        )
    except ValueError as exc:
        raise ValueError(
            "launcher fallback python must stay inside `.odylith/runtime/versions/` unless host-python fallback is explicitly allowed"
        ) from exc
    trusted_runtime_python = _trusted_runtime_python(repo_root=repo_root, python=fallback)
    if fallback_source_root is None and trusted_runtime_python is None and not allow_host_python_fallback:
        raise ValueError(
            "launcher fallback python must stay inside `.odylith/runtime/versions/` unless host-python fallback is explicitly allowed"
        )
    if trusted_runtime_python is not None:
        trusted_runtime_root = _runtime_root_for_python(repo_root=repo_root, python=trusted_runtime_python)
        if trusted_runtime_root is not None:
            health_reasons = _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=trusted_runtime_root)
            if health_reasons:
                raise ValueError(
                    "launcher fallback managed runtime failed integrity validation: "
                    + "; ".join(health_reasons)
                )
    resolved_source_root = _validated_source_root(fallback_source_root) if fallback_source_root is not None else None
    if resolved_source_root is None and allow_host_python_fallback:
        resolved_source_root = _discover_source_root()
    launcher_body = _launcher_script(
        fallback_python=trusted_runtime_python or fallback,
        fallback_source_root=resolved_source_root,
    )
    bootstrap_body = _bootstrap_launcher_script(
        fallback_python=trusted_runtime_python or fallback,
        fallback_source_root=resolved_source_root,
    )
    paths.bin_dir.mkdir(parents=True, exist_ok=True)
    if paths.launcher_path.exists() and paths.launcher_path.is_dir():
        raise ValueError(f"launcher path is a directory: {paths.launcher_path}")
    atomic_write_text(paths.launcher_path, launcher_body, encoding="utf-8")
    paths.launcher_path.chmod(0o755)
    bootstrap_path = paths.bin_dir / _BOOTSTRAP_LAUNCHER_NAME
    if bootstrap_path.exists() and bootstrap_path.is_dir():
        raise ValueError(f"bootstrap launcher path is a directory: {bootstrap_path}")
    atomic_write_text(bootstrap_path, bootstrap_body, encoding="utf-8")
    bootstrap_path.chmod(0o755)
    return paths.launcher_path


def launcher_fallback_source_root(*, repo_root: str | Path) -> Path | None:
    paths = repo_runtime_paths(repo_root)
    return _launcher_fallback_source_root_from_path(paths.launcher_path)


def doctor_runtime(
    *,
    repo_root: str | Path,
    repair: bool,
    allow_host_python_fallback: bool = True,
) -> tuple[bool, list[str]]:
    paths = repo_runtime_paths(repo_root)
    reasons: list[str] = []
    runtime_root = current_runtime_root(repo_root=repo_root)
    bootstrap_path = paths.bin_dir / _BOOTSTRAP_LAUNCHER_NAME
    reasons.extend(_launcher_health_reasons(repo_root=repo_root, launcher_path=paths.launcher_path, label="repo launcher"))
    reasons.extend(_launcher_health_reasons(repo_root=repo_root, launcher_path=bootstrap_path, label="bootstrap launcher"))
    if runtime_root is None:
        reasons.append("active runtime symlink missing or invalid")
    else:
        reasons.extend(_managed_runtime_health_reasons(repo_root=repo_root, runtime_root=runtime_root))
        reasons.extend(_runtime_wrapper_health_reasons(repo_root=repo_root, runtime_root=runtime_root))
    healthy = not reasons
    if healthy or not repair:
        return healthy, reasons
    repaired = _repair_runtime(repo_root=repo_root, allow_host_python_fallback=allow_host_python_fallback)
    return doctor_runtime(repo_root=repo_root, repair=False) if repaired else (False, reasons)


def _runtime_wrapper_health_reasons(*, repo_root: str | Path, runtime_root: Path) -> list[str]:
    python = _runtime_python(runtime_root)
    if python is None:
        return []
    exec_target = _runtime_wrapper_exec_target(python)
    if exec_target is None:
        return []
    unwrapped = _unwrap_runtime_wrapper_python(repo_root=repo_root, python=python)
    if unwrapped is None:
        return [f"active runtime wrapper loops back into itself: {python}"]
    unwrapped_runtime_root = _runtime_root_for_python(repo_root=repo_root, python=unwrapped)
    if unwrapped_runtime_root is not None and (unwrapped_runtime_root / "runtime-metadata.json").is_file():
        runtime_reasons = _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=unwrapped_runtime_root)
        if runtime_reasons:
            return [f"active runtime wrapper targets unverified managed runtime: {python}"]
    return []


def _repair_runtime(*, repo_root: str | Path, allow_host_python_fallback: bool) -> bool:
    paths = repo_runtime_paths(repo_root)
    target = current_runtime_root(repo_root=repo_root)
    fallback_python = _launcher_fallback_python(paths.launcher_path)
    source_root = (
        launcher_fallback_source_root(repo_root=repo_root)
        or _repo_local_source_root(repo_root=repo_root)
        or _discover_source_root()
    )
    target_wrapper_reasons = _runtime_wrapper_health_reasons(repo_root=repo_root, runtime_root=target) if target is not None else []
    target_verification_reasons = _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=target) if target is not None else []

    trusted_fallback_python = _trusted_runtime_python(repo_root=repo_root, python=fallback_python)
    if trusted_fallback_python is not None:
        trusted_fallback_root = _runtime_root_for_python(repo_root=repo_root, python=trusted_fallback_python)
        if trusted_fallback_root is not None and _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=trusted_fallback_root):
            trusted_fallback_python = None

    if target is None or target_verification_reasons:
        executable_root = Path((trusted_fallback_python or Path(sys.executable)).resolve()).parent.parent
        if (
            executable_root.parent == paths.versions_dir
            and (executable_root / "bin" / "python").is_file()
            and _runtime_root_is_candidate(repo_root=repo_root, runtime_root=executable_root)
        ):
            target = executable_root
        else:
            candidates = sorted(
                path
                for path in paths.versions_dir.glob("*")
                if _runtime_root_is_candidate(repo_root=repo_root, runtime_root=path)
            )
            if candidates:
                target = candidates[0]
    if target is not None:
        cleanup_runtime_versions_residue(paths.versions_dir, version=target.name)
    if target is None:
        if not allow_host_python_fallback:
            return False
        version = current_runtime_version(repo_root=repo_root) or "repaired-local"
        cleanup_runtime_versions_residue(paths.versions_dir, version=version)
        target = ensure_wrapped_runtime(
            repo_root=repo_root,
            version=version,
            fallback_python=trusted_fallback_python or Path(sys.executable),
            source_root=source_root,
            allow_host_python_fallback=allow_host_python_fallback,
        )
    elif target_wrapper_reasons:
        target = ensure_wrapped_runtime(
            repo_root=repo_root,
            version=target.name,
            fallback_python=trusted_fallback_python or Path(sys.executable),
            source_root=source_root,
            allow_host_python_fallback=allow_host_python_fallback,
        )
    launcher_fallback = _runtime_python(target)
    if launcher_fallback is None:
        if not allow_host_python_fallback:
            return False
        launcher_fallback = fallback_python or Path(sys.executable)
    ensure_launcher(
        repo_root=repo_root,
        fallback_python=launcher_fallback,
        fallback_source_root=source_root,
        allow_host_python_fallback=allow_host_python_fallback,
    )
    if target is not None:
        switch_runtime(repo_root=repo_root, target=target)
    return True


def install_release_runtime(
    *,
    repo_root: str | Path,
    repo: str,
    version: str = "latest",
    activate: bool = True,
) -> StagedRuntime:
    verified_release = download_verified_release(repo_root=repo_root, repo=repo, version=version)
    paths = repo_runtime_paths(repo_root)
    version_root = paths.versions_dir / verified_release.version
    cleanup_runtime_versions_residue(paths.versions_dir, version=verified_release.version)
    scrub_runtime_tree_metadata(version_root)
    version_root.parent.mkdir(parents=True, exist_ok=True)
    if version_root.exists() and _runtime_matches_verified_release(
        repo_root=repo_root,
        version_root=version_root,
        verified_release=verified_release,
    ):
        python = _venv_python(version_root)
        write_managed_runtime_trust(
            repo_root=repo_root,
            version_root=version_root,
            verification=verified_release.verification,
        )
        if activate:
            switch_runtime(repo_root=repo_root, target=version_root)
            ensure_launcher(repo_root=repo_root, fallback_python=python)
        return StagedRuntime(
            version=verified_release.version,
            manifest=verified_release.manifest,
            python=python,
            root=version_root,
            verification=verified_release.verification,
        )
    version_root.parent.mkdir(parents=True, exist_ok=True)
    stage_parent = Path(tempfile.mkdtemp(dir=str(version_root.parent), prefix=f".{version_root.name}.stage-"))
    staged_root = stage_parent / version_root.name
    try:
        _extract_runtime_bundle(bundle_path=verified_release.runtime_bundle_path, destination=staged_root)
        _write_runtime_verification(
            staged_root,
            version=verified_release.version,
            verification=verified_release.verification,
        )
        _venv_python(staged_root)
        _replace_runtime_tree(staged_root=staged_root, version_root=version_root)
    finally:
        remove_path(stage_parent)
    write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=version_root,
        verification=verified_release.verification,
    )
    python = _venv_python(version_root)
    if activate:
        switch_runtime(repo_root=repo_root, target=version_root)
        ensure_launcher(repo_root=repo_root, fallback_python=python)
    return StagedRuntime(
        version=verified_release.version,
        manifest=verified_release.manifest,
        python=python,
        root=version_root,
        verification=verified_release.verification,
    )


def _replace_runtime_tree(*, staged_root: Path, version_root: Path) -> None:
    backup_root: Path | None = None
    try:
        if version_root.exists() or version_root.is_symlink():
            backup_root = version_root.parent / f".{version_root.name}.backup-{os.getpid()}"
            if backup_root.exists() or backup_root.is_symlink():
                remove_path(backup_root)
            version_root.replace(backup_root)
            fsync_directory(version_root.parent)
        staged_root.replace(version_root)
        fsync_directory(version_root.parent)
    except Exception:
        if backup_root is not None and backup_root.exists() and not version_root.exists():
            backup_root.replace(version_root)
            fsync_directory(version_root.parent)
        raise
    finally:
        if backup_root is not None and backup_root.exists():
            remove_path(backup_root)
            fsync_directory(version_root.parent)


def install_release_feature_pack(
    *,
    repo_root: str | Path,
    repo: str,
    version: str,
    pack_id: str = CONTEXT_ENGINE_FEATURE_PACK_ID,
    runtime_root: Path | None = None,
) -> StagedRuntimeFeaturePack:
    verified_feature_pack = download_verified_feature_pack(
        repo_root=repo_root,
        repo=repo,
        version=version,
        pack_id=pack_id,
    )
    target_root = runtime_root or runtime_root_for_version(repo_root=repo_root, version=verified_feature_pack.version)
    if not target_root.is_dir():
        raise ValueError(f"managed runtime target missing for feature pack install: {target_root}")
    if not (target_root / "runtime-metadata.json").is_file():
        raise ValueError(f"feature packs can only be applied to a managed Odylith runtime: {target_root}")
    scrub_runtime_tree_metadata(target_root)
    integrity_reasons = _managed_runtime_health_reasons(repo_root=repo_root, runtime_root=target_root)
    if integrity_reasons:
        raise ValueError(
            f"feature packs can only be applied to a trusted Odylith runtime: {integrity_reasons[0]}"
        )
    if _runtime_feature_pack_matches_verified_release(version_root=target_root, verified_feature_pack=verified_feature_pack):
        write_managed_runtime_trust(
            repo_root=repo_root,
            version_root=target_root,
            verification=runtime_verification_evidence(target_root),
        )
        return StagedRuntimeFeaturePack(
            asset_name=verified_feature_pack.asset_name,
            manifest=verified_feature_pack.manifest,
            pack_id=verified_feature_pack.pack_id,
            root=target_root,
            verification=verified_feature_pack.verification,
            version=verified_feature_pack.version,
        )

    _extract_runtime_overlay(bundle_path=verified_feature_pack.bundle_path, destination=target_root)
    pack_paths = _runtime_overlay_paths(bundle_path=verified_feature_pack.bundle_path)
    packs = load_runtime_feature_packs(target_root)
    packs[verified_feature_pack.pack_id] = {
        "asset_name": verified_feature_pack.asset_name,
        "display_name": managed_runtime_feature_pack_by_id(verified_feature_pack.pack_id).display_name,
        "installed_utc": datetime.now(UTC).isoformat(),
        "platform": verified_feature_pack.runtime_platform.slug,
        "paths": pack_paths,
        "verification": dict(verified_feature_pack.verification),
    }
    _write_runtime_feature_packs(
        target_root,
        version=verified_feature_pack.version,
        packs=packs,
    )
    write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=target_root,
        verification=runtime_verification_evidence(target_root),
    )
    return StagedRuntimeFeaturePack(
        asset_name=verified_feature_pack.asset_name,
        manifest=verified_feature_pack.manifest,
        pack_id=verified_feature_pack.pack_id,
        root=target_root,
        verification=verified_feature_pack.verification,
        version=verified_feature_pack.version,
    )


def _extract_runtime_bundle(*, bundle_path: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="odylith-runtime-bundle-") as tmpdir:
        extract_root = Path(tmpdir)
        extract_validated_archive(
            archive_path=bundle_path,
            destination=extract_root,
            expected_root=MANAGED_RUNTIME_ROOT_NAME,
            label="managed runtime bundle",
        )
        runtime_root = extract_root / MANAGED_RUNTIME_ROOT_NAME
        if not runtime_root.is_dir():
            raise ValueError(f"managed runtime bundle missing root directory: {MANAGED_RUNTIME_ROOT_NAME}")
        shutil.move(str(runtime_root), destination)


def _validate_runtime_overlay_archive(*, bundle_path: Path) -> None:
    with tarfile.open(bundle_path, "r:gz") as archive:
        members = archive.getmembers()
        validate_archive_members(
            members=members,
            expected_root=MANAGED_RUNTIME_ROOT_NAME,
            label="managed runtime overlay",
        )


def _runtime_overlay_paths(*, bundle_path: Path) -> list[str]:
    with tarfile.open(bundle_path, "r:gz") as archive:
        paths: list[str] = []
        for member in archive.getmembers():
            if member.isdir():
                continue
            if not member.name.startswith(f"{MANAGED_RUNTIME_ROOT_NAME}/"):
                continue
            relative = member.name.removeprefix(f"{MANAGED_RUNTIME_ROOT_NAME}/").strip()
            if relative:
                paths.append(relative)
    return sorted(set(paths))


def _extract_runtime_overlay(*, bundle_path: Path, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    _validate_runtime_overlay_archive(bundle_path=bundle_path)
    with tempfile.TemporaryDirectory(prefix="odylith-runtime-overlay-") as tmpdir:
        extract_root = Path(tmpdir)
        extract_validated_archive(
            archive_path=bundle_path,
            destination=extract_root,
            expected_root=MANAGED_RUNTIME_ROOT_NAME,
            label="managed runtime overlay",
        )
        runtime_root = extract_root / MANAGED_RUNTIME_ROOT_NAME
        if not runtime_root.is_dir():
            raise ValueError(f"managed runtime overlay missing root directory: {MANAGED_RUNTIME_ROOT_NAME}")
        shutil.copytree(runtime_root, destination, dirs_exist_ok=True)


def current_runtime_python() -> Path:
    return Path(sys.executable).resolve()


def switch_runtime(*, repo_root: str | Path, target: Path | None) -> Path | None:
    paths = repo_runtime_paths(repo_root)
    current_target = current_runtime_root(repo_root=repo_root)
    if target is None:
        return current_target
    resolved_target = _trusted_runtime_root(repo_root=repo_root, target=target)
    if resolved_target is None:
        raise ValueError(f"runtime target must stay inside {paths.versions_dir}: {target}")
    paths.current_runtime.parent.mkdir(parents=True, exist_ok=True)
    temp_link = paths.current_runtime.parent / ".current.tmp"
    if temp_link.exists() or temp_link.is_symlink():
        temp_link.unlink()
    os.symlink(resolved_target, temp_link)
    temp_link.replace(paths.current_runtime)
    fsync_directory(paths.current_runtime.parent)
    return current_target


def clear_runtime_activation(*, repo_root: str | Path, clear_launcher: bool = False) -> None:
    paths = repo_runtime_paths(repo_root)
    remove_path(paths.current_runtime)
    fsync_directory(paths.current_runtime.parent)
    if clear_launcher:
        remove_path(paths.launcher_path)
        remove_path(paths.bin_dir / _BOOTSTRAP_LAUNCHER_NAME)
        fsync_directory(paths.launcher_path.parent)
