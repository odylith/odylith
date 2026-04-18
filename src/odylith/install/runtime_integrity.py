"""Integrity hashing and drift detection for managed runtimes."""

from __future__ import annotations

from contextlib import suppress
import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable, Mapping

from odylith.install.fs import atomic_write_text
from odylith.install.managed_runtime import (
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_VERIFICATION_FILENAME,
    managed_runtime_site_packages_roots,
)
from odylith.install.runtime_tree_policy import is_ignored_runtime_tree_entry

MANAGED_RUNTIME_TRUST_SCHEMA_VERSION = "odylith-managed-runtime-trust.v1"
MANAGED_RUNTIME_TREE_SCHEMA_VERSION = "odylith-managed-runtime-tree.v1"
_TRUST_DIRNAME = "managed-runtime-trust"
_PRIMARY_TRUST_DIR = Path(".odylith") / "trust" / _TRUST_DIRNAME
_LEGACY_TRUST_DIR = Path("odylith") / "runtime" / "source" / _TRUST_DIRNAME
_TRUST_ENV_SUFFIX = ".env"
_TRUST_TREE_SUFFIX = ".tree.v1.json"
_MAX_DRIFT_EXAMPLES = 5


@dataclass(frozen=True)
class RuntimeEntry:
    kind: str
    path: str
    sha256: str = ""
    size: int = 0
    target: str = ""


def write_managed_runtime_trust(
    *,
    repo_root: str | Path,
    version_root: Path,
    verification: dict[str, object],
) -> tuple[Path, Path]:
    trust_root = _trust_dir(repo_root=repo_root)
    trust_root.mkdir(parents=True, exist_ok=True)
    hot_entries = _hot_entries(version_root)
    tree_entries = _tree_entries(version_root)
    verification_sha256 = _verification_sha256(verification)
    tree_digest = _tree_digest(tree_entries)
    trust_env_path = _trust_env_path(repo_root=repo_root, version=version_root.name)
    trust_tree_path = _trust_tree_path(repo_root=repo_root, version=version_root.name)

    env_lines = [
        f"SCHEMA_VERSION={MANAGED_RUNTIME_TRUST_SCHEMA_VERSION}",
        f"VERSION={version_root.name}",
        f"GENERATED_UTC={datetime.now(UTC).isoformat()}",
        f"VERIFICATION_SHA256={verification_sha256}",
        f"TREE_SHA256={tree_digest}",
        f"HOT_FILE_COUNT={len(hot_entries)}",
        f"BIN_PYTHON_SHA256={_runtime_file_sha256(version_root, 'bin/python')}",
        f"BIN_PYTHON3_SHA256={_runtime_file_sha256(version_root, 'bin/python3')}",
        f"BIN_ODYLITH_SHA256={_runtime_file_sha256(version_root, 'bin/odylith')}",
        f"PYVENV_CFG_SHA256={_runtime_file_sha256(version_root, 'pyvenv.cfg')}",
        f"RUNTIME_METADATA_SHA256={_runtime_file_sha256(version_root, 'runtime-metadata.json')}",
        f"RUNTIME_VERIFICATION_SHA256={_runtime_file_sha256(version_root, MANAGED_RUNTIME_VERIFICATION_FILENAME)}",
        f"RUNTIME_FEATURE_PACKS_SHA256={_runtime_file_sha256(version_root, MANAGED_RUNTIME_FEATURE_PACK_FILENAME)}",
    ]
    for index, entry in enumerate(hot_entries):
        prefix = f"HOT_FILE_{index:04d}"
        env_lines.append(f"{prefix}_PATH={entry.path}")
        env_lines.append(f"{prefix}_SHA256={entry.sha256}")
    atomic_write_text(trust_env_path, "\n".join(env_lines) + "\n", encoding="utf-8")

    payload = {
        "schema_version": MANAGED_RUNTIME_TREE_SCHEMA_VERSION,
        "version": version_root.name,
        "generated_utc": datetime.now(UTC).isoformat(),
        "verification_sha256": verification_sha256,
        "summary": {
            "entry_count": len(tree_entries),
            "tree_sha256": tree_digest,
        },
        "entries": [
            {
                "kind": entry.kind,
                "path": entry.path,
                **({"sha256": entry.sha256, "size": entry.size} if entry.kind == "file" else {"target": entry.target}),
            }
            for entry in tree_entries
        ],
    }
    atomic_write_text(trust_tree_path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    _cleanup_legacy_trust(repo_root=repo_root, version=version_root.name)
    return trust_env_path, trust_tree_path


def managed_runtime_trust_matches_verification(
    *,
    repo_root: str | Path,
    version: str,
    verification: Mapping[str, object],
) -> bool:
    payload = _load_trust_env(repo_root=repo_root, version=version)
    if not payload:
        return False
    return payload.get("VERIFICATION_SHA256", "").strip() == _verification_sha256(verification)


def managed_runtime_integrity_reasons(*, repo_root: str | Path, runtime_root: Path) -> list[str]:
    trust_payload = _load_trust_env(repo_root=repo_root, version=runtime_root.name)
    if not trust_payload:
        return [f"managed runtime trust file missing or unreadable: {_trust_env_path(repo_root=repo_root, version=runtime_root.name)}"]
    reasons: list[str] = []
    if trust_payload.get("SCHEMA_VERSION", "").strip() != MANAGED_RUNTIME_TRUST_SCHEMA_VERSION:
        reasons.append(f"managed runtime trust schema invalid: {_trust_env_path(repo_root=repo_root, version=runtime_root.name)}")
        return reasons
    if trust_payload.get("VERSION", "").strip() != runtime_root.name:
        reasons.append(f"managed runtime trust version drifted: {_trust_env_path(repo_root=repo_root, version=runtime_root.name)}")
        return reasons
    if trust_payload.get("VERIFICATION_SHA256", "").strip() != _runtime_verification_sha256(runtime_root):
        reasons.append(f"managed runtime trust verification drifted: {_trust_env_path(repo_root=repo_root, version=runtime_root.name)}")
        return reasons
    reasons.extend(_hot_manifest_reasons(runtime_root=runtime_root, trust_payload=trust_payload))
    if reasons:
        return reasons
    return _tree_manifest_reasons(repo_root=repo_root, runtime_root=runtime_root, trust_payload=trust_payload)


def managed_runtime_launcher_verifier_lines() -> list[str]:
    return [
        "import hashlib",
        "import json",
        "import sys",
        "from pathlib import Path",
        "",
        "runtime_root = Path(sys.argv[1])",
        "trust_file = Path(sys.argv[2])",
        "",
        "def fail(message: str) -> None:",
        "    print(message, file=sys.stderr)",
        "    raise SystemExit(1)",
        "",
        "def load_env(path: Path) -> dict[str, str]:",
        "    payload: dict[str, str] = {}",
        "    try:",
        "        lines = path.read_text(encoding='utf-8').splitlines()",
        "    except OSError as exc:",
        "        fail(f'managed runtime trust file unreadable: {exc}')",
        "    for raw_line in lines:",
        "        line = str(raw_line or '').strip()",
        "        if not line or line.startswith('#') or '=' not in line:",
        "            continue",
        "        key, value = line.split('=', 1)",
        "        payload[key.strip()] = value.strip()",
        "    return payload",
        "",
        "def sha256_file(path: Path) -> str:",
        "    hasher = hashlib.sha256()",
        "    with path.open('rb') as handle:",
        "        while True:",
        "            chunk = handle.read(1024 * 1024)",
        "            if not chunk:",
        "                break",
        "            hasher.update(chunk)",
        "    return hasher.hexdigest()",
        "",
        "payload = load_env(trust_file)",
        f"if payload.get('SCHEMA_VERSION', '').strip() != '{MANAGED_RUNTIME_TRUST_SCHEMA_VERSION}':",
        "    fail(f'managed runtime trust schema invalid: {trust_file}')",
        "if payload.get('VERSION', '').strip() != runtime_root.name:",
        "    fail(f'managed runtime trust version drifted: {trust_file}')",
        "verification_path = runtime_root / 'runtime-verification.v1.json'",
        "try:",
        "    verification_payload = json.loads(verification_path.read_text(encoding='utf-8'))",
        "except Exception as exc:  # noqa: BLE001",
        "    fail(f'managed runtime verification unreadable: {exc}')",
        "verification = verification_payload.get('verification') if isinstance(verification_payload, dict) else None",
        "if not isinstance(verification, dict):",
        "    fail(f'managed runtime verification evidence missing: {verification_path}')",
        "observed_verification_sha = hashlib.sha256(json.dumps(verification, sort_keys=True, separators=(',', ':')).encode('utf-8')).hexdigest()",
        "if payload.get('VERIFICATION_SHA256', '').strip() != observed_verification_sha:",
        "    fail(f'managed runtime trust verification drifted: {trust_file}')",
        "count_raw = payload.get('HOT_FILE_COUNT', '').strip()",
        "try:",
        "    count = int(count_raw)",
        "except ValueError:",
        "    fail(f'managed runtime hot manifest count invalid: {trust_file}')",
        "if count <= 0:",
        "    fail(f'managed runtime hot manifest empty: {trust_file}')",
        "for index in range(count):",
        "    prefix = f'HOT_FILE_{index:04d}'",
        "    relative_path = payload.get(f'{prefix}_PATH', '').strip()",
        "    expected_sha = payload.get(f'{prefix}_SHA256', '').strip().lower()",
        "    if not relative_path or len(expected_sha) != 64:",
        "        fail(f'managed runtime hot manifest malformed: {trust_file}')",
        "    candidate = runtime_root / relative_path",
        "    if candidate.is_symlink() or not candidate.is_file():",
        "        fail(f'managed runtime hot path missing or symlinked: {candidate}')",
        "    actual_sha = sha256_file(candidate)",
        "    if actual_sha != expected_sha:",
        "        fail(f'managed runtime hot integrity drifted: {candidate}')",
    ]


def _trust_dir(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / _PRIMARY_TRUST_DIR


def _legacy_trust_dir(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / _LEGACY_TRUST_DIR


def _trust_env_path(*, repo_root: str | Path, version: str) -> Path:
    return _trust_dir(repo_root=repo_root) / f"{str(version).strip()}{_TRUST_ENV_SUFFIX}"


def _legacy_trust_env_path(*, repo_root: str | Path, version: str) -> Path:
    return _legacy_trust_dir(repo_root=repo_root) / f"{str(version).strip()}{_TRUST_ENV_SUFFIX}"


def _trust_tree_path(*, repo_root: str | Path, version: str) -> Path:
    return _trust_dir(repo_root=repo_root) / f"{str(version).strip()}{_TRUST_TREE_SUFFIX}"


def _legacy_trust_tree_path(*, repo_root: str | Path, version: str) -> Path:
    return _legacy_trust_dir(repo_root=repo_root) / f"{str(version).strip()}{_TRUST_TREE_SUFFIX}"


def _selected_trust_paths(*, repo_root: str | Path, version: str) -> tuple[Path, Path]:
    primary_env = _trust_env_path(repo_root=repo_root, version=version)
    primary_tree = _trust_tree_path(repo_root=repo_root, version=version)
    if primary_env.exists() or primary_tree.exists():
        return primary_env, primary_tree
    legacy_env = _legacy_trust_env_path(repo_root=repo_root, version=version)
    legacy_tree = _legacy_trust_tree_path(repo_root=repo_root, version=version)
    if legacy_env.exists() or legacy_tree.exists():
        return legacy_env, legacy_tree
    return primary_env, primary_tree


def _load_trust_env(*, repo_root: str | Path, version: str) -> dict[str, str]:
    path, _tree_path = _selected_trust_paths(repo_root=repo_root, version=version)
    if path.is_symlink() or not path.is_file():
        return {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    payload: dict[str, str] = {}
    for raw_line in lines:
        line = str(raw_line or "").strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        payload[key.strip()] = value.strip()
    return payload


def _hot_manifest_reasons(*, runtime_root: Path, trust_payload: Mapping[str, str]) -> list[str]:
    count_raw = str(trust_payload.get("HOT_FILE_COUNT") or "").strip()
    try:
        count = int(count_raw)
    except ValueError:
        return ["managed runtime hot manifest count invalid"]
    if count <= 0:
        return ["managed runtime hot manifest empty"]
    reasons: list[str] = []
    for index in range(count):
        prefix = f"HOT_FILE_{index:04d}"
        relative_path = str(trust_payload.get(f"{prefix}_PATH") or "").strip()
        expected_sha256 = str(trust_payload.get(f"{prefix}_SHA256") or "").strip().lower()
        if not relative_path or len(expected_sha256) != 64:
            return ["managed runtime hot manifest malformed"]
        candidate = runtime_root / relative_path
        if candidate.is_symlink() or not candidate.is_file():
            reasons.append(f"managed runtime hot path missing or symlinked: {candidate}")
            continue
        if _sha256_file(candidate) != expected_sha256:
            reasons.append(f"managed runtime hot integrity drifted: {candidate}")
        if len(reasons) >= _MAX_DRIFT_EXAMPLES:
            break
    return reasons


def _tree_manifest_reasons(
    *,
    repo_root: str | Path,
    runtime_root: Path,
    trust_payload: Mapping[str, str],
) -> list[str]:
    _trust_env_path_selected, trust_tree_path = _selected_trust_paths(repo_root=repo_root, version=runtime_root.name)
    if trust_tree_path.is_symlink() or not trust_tree_path.is_file():
        return [f"managed runtime tree manifest missing or unreadable: {trust_tree_path}"]
    try:
        payload = json.loads(trust_tree_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [f"managed runtime tree manifest unreadable: {trust_tree_path}"]
    if not isinstance(payload, dict):
        return [f"managed runtime tree manifest malformed: {trust_tree_path}"]
    if str(payload.get("schema_version") or "").strip() != MANAGED_RUNTIME_TREE_SCHEMA_VERSION:
        return [f"managed runtime tree manifest schema invalid: {trust_tree_path}"]
    if str(payload.get("version") or "").strip() != runtime_root.name:
        return [f"managed runtime tree manifest version drifted: {trust_tree_path}"]
    if str(payload.get("verification_sha256") or "").strip() != str(trust_payload.get("VERIFICATION_SHA256") or "").strip():
        return [f"managed runtime tree manifest verification drifted: {trust_tree_path}"]
    expected_entries_payload = payload.get("entries")
    if not isinstance(expected_entries_payload, list) or not expected_entries_payload:
        return [f"managed runtime tree manifest entries missing: {trust_tree_path}"]
    expected_entries: dict[str, RuntimeEntry] = {}
    for item in expected_entries_payload:
        if not isinstance(item, dict):
            return [f"managed runtime tree manifest entry malformed: {trust_tree_path}"]
        kind = str(item.get("kind") or "").strip()
        relative_path = str(item.get("path") or "").strip()
        if kind not in {"file", "symlink"} or not relative_path or relative_path.startswith("/") or ".." in Path(relative_path).parts:
            return [f"managed runtime tree manifest entry invalid: {trust_tree_path}"]
        if kind == "file":
            expected_entries[relative_path] = RuntimeEntry(
                kind="file",
                path=relative_path,
                sha256=str(item.get("sha256") or "").strip().lower(),
                size=int(item.get("size") or 0),
            )
        else:
            expected_entries[relative_path] = RuntimeEntry(
                kind="symlink",
                path=relative_path,
                target=str(item.get("target") or "").strip(),
            )
    actual_entries = {entry.path: entry for entry in _tree_entries(runtime_root)}
    reasons: list[str] = []
    missing = sorted(set(expected_entries).difference(actual_entries))
    unexpected = sorted(set(actual_entries).difference(expected_entries))
    for relative_path in missing[:_MAX_DRIFT_EXAMPLES]:
        reasons.append(f"managed runtime tree entry missing: {runtime_root / relative_path}")
    for relative_path in unexpected[: max(0, _MAX_DRIFT_EXAMPLES - len(reasons))]:
        reasons.append(f"managed runtime tree entry unexpected: {runtime_root / relative_path}")
    if reasons:
        return reasons
    for relative_path in sorted(expected_entries):
        expected = expected_entries[relative_path]
        actual = actual_entries[relative_path]
        if expected.kind != actual.kind:
            reasons.append(f"managed runtime tree entry kind drifted: {runtime_root / relative_path}")
        elif expected.kind == "file":
            if expected.sha256 != actual.sha256 or expected.size != actual.size:
                reasons.append(f"managed runtime tree entry drifted: {runtime_root / relative_path}")
        elif expected.target != actual.target:
            reasons.append(f"managed runtime symlink target drifted: {runtime_root / relative_path}")
        if len(reasons) >= _MAX_DRIFT_EXAMPLES:
            break
    if reasons:
        return reasons
    expected_tree_sha = str(payload.get("summary", {}).get("tree_sha256") or "").strip() if isinstance(payload.get("summary"), dict) else ""
    actual_tree_sha = _tree_digest(actual_entries.values())
    if expected_tree_sha and expected_tree_sha != actual_tree_sha:
        return [f"managed runtime tree digest drifted: {trust_tree_path}"]
    return []


def _hot_entries(version_root: Path) -> list[RuntimeEntry]:
    hot_paths: list[str] = []
    for relative_path in (
        "bin/python",
        "bin/python3",
        "bin/odylith",
        "pyvenv.cfg",
        "runtime-metadata.json",
        MANAGED_RUNTIME_VERIFICATION_FILENAME,
        MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    ):
        candidate = version_root / relative_path
        if candidate.is_file() and not candidate.is_symlink():
            hot_paths.append(relative_path)
    for site_packages_root in managed_runtime_site_packages_roots(version_root):
        for candidate_root in (site_packages_root / "odylith", *site_packages_root.glob("odylith-*.dist-info")):
            if not candidate_root.exists():
                continue
            for candidate in sorted(candidate_root.rglob("*")):
                if candidate.is_file() and not candidate.is_symlink():
                    relative_path = candidate.relative_to(version_root).as_posix()
                    if _is_generated_python_cache(relative_path):
                        continue
                    hot_paths.append(relative_path)
    unique_paths = sorted(dict.fromkeys(hot_paths))
    return [
        RuntimeEntry(
            kind="file",
            path=relative_path,
            sha256=_sha256_file(version_root / relative_path),
            size=(version_root / relative_path).stat().st_size,
        )
        for relative_path in unique_paths
    ]


def _tree_entries(version_root: Path) -> list[RuntimeEntry]:
    entries: list[RuntimeEntry] = []
    for candidate in sorted(version_root.rglob("*")):
        relative_path = candidate.relative_to(version_root).as_posix()
        if _is_generated_python_cache(relative_path):
            continue
        if is_ignored_runtime_tree_entry(version_root=version_root, candidate=candidate):
            continue
        if candidate.is_symlink():
            entries.append(
                RuntimeEntry(
                    kind="symlink",
                    path=relative_path,
                    target=str(candidate.readlink()),
                )
            )
            continue
        if candidate.is_file():
            entries.append(
                RuntimeEntry(
                    kind="file",
                    path=relative_path,
                    sha256=_sha256_file(candidate),
                    size=candidate.stat().st_size,
                )
            )
    return entries


def _is_generated_python_cache(relative_path: str) -> bool:
    normalized = str(relative_path).strip()
    if not normalized:
        return False
    path = Path(normalized)
    return "__pycache__" in path.parts or path.suffix in {".pyc", ".pyo"}


def _tree_digest(entries: Iterable[RuntimeEntry]) -> str:
    hasher = hashlib.sha256()
    for entry in sorted(entries, key=lambda candidate: candidate.path):
        if entry.kind == "file":
            line = f"{entry.kind}\t{entry.path}\t{entry.sha256}\t{entry.size}\n"
        else:
            line = f"{entry.kind}\t{entry.path}\t{entry.target}\n"
        hasher.update(line.encode("utf-8"))
    return hasher.hexdigest()


def _verification_sha256(verification: Mapping[str, object]) -> str:
    return hashlib.sha256(json.dumps(dict(verification), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def _runtime_verification_sha256(runtime_root: Path) -> str:
    verification_path = runtime_root / MANAGED_RUNTIME_VERIFICATION_FILENAME
    if not verification_path.is_file() or verification_path.is_symlink():
        return ""
    try:
        payload = json.loads(verification_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    verification = payload.get("verification")
    if not isinstance(verification, dict):
        return ""
    return _verification_sha256(verification)


def _runtime_file_sha256(version_root: Path, relative_path: str) -> str:
    candidate = version_root / str(relative_path).strip()
    if not candidate.is_file():
        return ""
    return _sha256_file(candidate)


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _cleanup_legacy_trust(*, repo_root: str | Path, version: str) -> None:
    legacy_dir = _legacy_trust_dir(repo_root=repo_root)
    for candidate in (
        _legacy_trust_env_path(repo_root=repo_root, version=version),
        _legacy_trust_tree_path(repo_root=repo_root, version=version),
    ):
        with suppress(OSError):
            candidate.unlink()
    current = legacy_dir
    repo_root_path = Path(repo_root).expanduser().resolve()
    while current != repo_root_path and current != current.parent:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent
