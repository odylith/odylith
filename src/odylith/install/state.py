"""Persistent install state records and update helpers."""

from __future__ import annotations

import json
import os
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator, Mapping, Sequence

import fcntl

from odylith.install.fs import atomic_write_text

INSTALL_STATE_SCHEMA_VERSION = "v2"
PRODUCT_VERSION_PIN_SCHEMA_VERSION = "odylith-product.v1"
UPGRADE_SPOTLIGHT_SCHEMA_VERSION = "odylith-upgrade-spotlight.v1"
DEFAULT_REPO_SCHEMA_VERSION = 1
AUTHORITATIVE_RELEASE_REPO = "odylith/odylith"
AUTHORITATIVE_RELEASE_ACTOR = "freedom-research"
SIGNER_WORKFLOW_PATH = ".github/workflows/release.yml"
SIGNER_WORKFLOW_REF = "refs/heads/main"
SIGNER_OIDC_ISSUER = "https://token.actions.githubusercontent.com"


@dataclass(frozen=True)
class ProductVersionPin:
    odylith_version: str
    repo_schema_version: int = DEFAULT_REPO_SCHEMA_VERSION
    migration_required: bool = False

    def as_dict(self) -> dict[str, object]:
        return {
            "schema_version": PRODUCT_VERSION_PIN_SCHEMA_VERSION,
            "migration_required": bool(self.migration_required),
            "odylith_version": self.odylith_version,
            "repo_schema_version": int(self.repo_schema_version),
        }


def install_state_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ".odylith" / "install.json"


def install_ledger_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ".odylith" / "install-ledger.v1.jsonl"


def version_pin_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / "odylith" / "runtime" / "source" / "product-version.v1.json"


def upgrade_spotlight_path(*, repo_root: str | Path) -> Path:
    return Path(repo_root).expanduser().resolve() / ".odylith" / "runtime" / "release-upgrade-spotlight.v1.json"


def load_version_pin(
    *,
    repo_root: str | Path,
    fallback_version: str | None = None,
) -> ProductVersionPin | None:
    path = version_pin_path(repo_root=repo_root)
    if not path.is_file():
        version = str(fallback_version or "").strip()
        if not version:
            return None
        return ProductVersionPin(odylith_version=version)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        version = str(fallback_version or "").strip()
        if not version:
            return None
        return ProductVersionPin(odylith_version=version)
    version = str(payload.get("odylith_version") or payload.get("odyssey_version") or fallback_version or "").strip()
    if not version:
        return None
    repo_schema_version = payload.get("repo_schema_version", DEFAULT_REPO_SCHEMA_VERSION)
    try:
        resolved_schema_version = int(repo_schema_version)
    except (TypeError, ValueError):
        resolved_schema_version = DEFAULT_REPO_SCHEMA_VERSION
    return ProductVersionPin(
        odylith_version=version,
        repo_schema_version=resolved_schema_version,
        migration_required=bool(payload.get("migration_required")),
    )


def write_version_pin(
    *,
    repo_root: str | Path,
    version: str,
    repo_schema_version: int = DEFAULT_REPO_SCHEMA_VERSION,
    migration_required: bool = False,
) -> Path:
    path = version_pin_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = ProductVersionPin(
        odylith_version=str(version).strip(),
        repo_schema_version=int(repo_schema_version),
        migration_required=bool(migration_required),
    ).as_dict()
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_upgrade_spotlight(*, repo_root: str | Path) -> dict[str, object]:
    path = upgrade_spotlight_path(repo_root=repo_root)
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(payload, Mapping):
        return {}
    raw_highlights = payload.get("highlights")
    highlights = (
        [
            str(item).strip()
            for item in raw_highlights
            if str(item).strip()
        ]
        if isinstance(raw_highlights, Sequence) and not isinstance(raw_highlights, (str, bytes, bytearray))
        else []
    )
    return {
        "schema_version": str(payload.get("schema_version") or "").strip(),
        "recorded_utc": str(payload.get("recorded_utc") or "").strip(),
        "from_version": str(payload.get("from_version") or "").strip(),
        "to_version": str(payload.get("to_version") or "").strip(),
        "release_tag": str(payload.get("release_tag") or "").strip(),
        "release_url": str(payload.get("release_url") or "").strip(),
        "release_published_at": str(payload.get("release_published_at") or "").strip(),
        "release_body": str(payload.get("release_body") or "").strip(),
        "highlights": highlights[:3],
    }


def write_upgrade_spotlight(
    *,
    repo_root: str | Path,
    from_version: str,
    to_version: str,
    release_tag: str = "",
    release_url: str = "",
    release_published_at: str = "",
    release_body: str = "",
    highlights: Sequence[str] = (),
) -> Path:
    path = upgrade_spotlight_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_highlights = [
        str(item).strip()
        for item in highlights
        if str(item).strip()
    ][:3]
    payload = {
        "schema_version": UPGRADE_SPOTLIGHT_SCHEMA_VERSION,
        "recorded_utc": datetime.now(UTC).isoformat(),
        "from_version": str(from_version or "").strip(),
        "to_version": str(to_version or "").strip(),
        "release_tag": str(release_tag or "").strip(),
        "release_url": str(release_url or "").strip(),
        "release_published_at": str(release_published_at or "").strip(),
        "release_body": str(release_body or "").strip(),
        "highlights": normalized_highlights,
    }
    atomic_write_text(path, json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def clear_upgrade_spotlight(*, repo_root: str | Path) -> None:
    path = upgrade_spotlight_path(repo_root=repo_root)
    if path.is_file() or path.is_symlink():
        path.unlink()


def load_install_state(*, repo_root: str | Path) -> dict[str, object]:
    path = install_state_path(repo_root=repo_root)
    if not path.is_file():
        return _default_install_state()
    try:
        payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    except (OSError, json.JSONDecodeError):
        return _default_install_state()
    if not isinstance(payload, Mapping):
        return _default_install_state()
    return _normalize_install_state(repo_root=Path(repo_root).expanduser().resolve(), payload=payload)


def write_install_state(*, repo_root: str | Path, payload: Mapping[str, object]) -> None:
    path = install_state_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = _normalize_install_state(
        repo_root=Path(repo_root).expanduser().resolve(),
        payload=payload,
    )
    atomic_write_text(path, json.dumps(normalized, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def append_install_ledger(*, repo_root: str | Path, payload: Mapping[str, object]) -> None:
    path = install_ledger_path(repo_root=repo_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    event = dict(payload)
    event.setdefault("recorded_utc", datetime.now(UTC).isoformat())
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True) + "\n")


@contextmanager
def install_lock(*, repo_root: str | Path) -> Iterator[None]:
    root = Path(repo_root).expanduser().resolve()
    lock_path = root / ".odylith" / "locks" / "install.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        handle.seek(0)
        handle.truncate()
        handle.write(f"{os.getpid()}\n")
        handle.flush()
        try:
            yield
        finally:
            handle.seek(0)
            handle.truncate()
            handle.flush()
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def install_integration_enabled(state: Mapping[str, object] | None) -> bool:
    if not isinstance(state, Mapping):
        return True
    value = state.get("integration_enabled")
    if value is None:
        return True
    return bool(value)


def current_activation_history(state: Mapping[str, object]) -> list[str]:
    history = state.get("activation_history")
    if not isinstance(history, list):
        return []
    return [str(value).strip() for value in history if str(value).strip()]


def record_activation(
    *,
    state: Mapping[str, object],
    version: str,
    mark_last_known_good: bool = True,
) -> dict[str, object]:
    normalized = dict(state)
    history = current_activation_history(normalized)
    resolved_version = str(version).strip()
    if not resolved_version:
        return normalized
    if not history or history[-1] != resolved_version:
        history.append(resolved_version)
    normalized["activation_history"] = history
    normalized["active_version"] = resolved_version
    if mark_last_known_good or not str(normalized.get("last_known_good_version") or "").strip():
        normalized["last_known_good_version"] = resolved_version
    return normalized


def installed_version_entry(state: Mapping[str, object], version: str) -> dict[str, object]:
    versions = state.get("installed_versions")
    if not isinstance(versions, Mapping):
        return {}
    entry = versions.get(version)
    return dict(entry) if isinstance(entry, Mapping) else {}


def installed_feature_packs(state: Mapping[str, object], version: str) -> dict[str, object]:
    entry = installed_version_entry(state, version)
    feature_packs = entry.get("feature_packs")
    if not isinstance(feature_packs, Mapping):
        return {}
    return {
        str(pack_id).strip(): dict(details)
        for pack_id, details in feature_packs.items()
        if str(pack_id).strip() and isinstance(details, Mapping)
    }


def _default_install_state() -> dict[str, object]:
    return {
        "schema_version": INSTALL_STATE_SCHEMA_VERSION,
        "active_version": "",
        "activation_history": [],
        "consumer_profile_path": "",
        "detached": False,
        "installed_utc": "",
        "installed_versions": {},
        "integration_enabled": True,
        "last_known_good_version": "",
        "launcher_path": "",
    }


def _normalize_install_state(*, repo_root: Path, payload: Mapping[str, object]) -> dict[str, object]:
    normalized = _default_install_state()
    normalized["schema_version"] = INSTALL_STATE_SCHEMA_VERSION
    normalized["integration_enabled"] = install_integration_enabled(payload)
    normalized["detached"] = bool(payload.get("detached"))
    active_version = str(payload.get("active_version") or "").strip()
    normalized["active_version"] = active_version
    normalized["installed_utc"] = str(payload.get("installed_utc") or "").strip()
    normalized["consumer_profile_path"] = str(payload.get("consumer_profile_path") or "").strip()
    normalized["launcher_path"] = str(payload.get("launcher_path") or "").strip()
    normalized["last_known_good_version"] = str(payload.get("last_known_good_version") or active_version).strip()

    versions_payload = payload.get("installed_versions")
    installed_versions: dict[str, object] = {}
    if isinstance(versions_payload, Mapping):
        for version, entry in versions_payload.items():
            resolved_version = str(version).strip()
            if not resolved_version or not isinstance(entry, Mapping):
                continue
            installed_versions[resolved_version] = {
                "installed_utc": str(entry.get("installed_utc") or payload.get("installed_utc") or "").strip(),
                "runtime_root": str(entry.get("runtime_root") or "").strip(),
                "verification": dict(entry.get("verification", {})) if isinstance(entry.get("verification"), Mapping) else {},
                "feature_packs": {
                    str(pack_id).strip(): dict(details)
                    for pack_id, details in dict(entry.get("feature_packs", {})).items()
                    if str(pack_id).strip() and isinstance(details, Mapping)
                }
                if isinstance(entry.get("feature_packs"), Mapping)
                else {},
            }
    elif active_version:
        installed_versions[active_version] = {
            "installed_utc": str(payload.get("installed_utc") or "").strip(),
            "runtime_root": str(repo_root / ".odylith" / "runtime" / "versions" / active_version),
            "verification": {},
            "feature_packs": {},
        }
    normalized["installed_versions"] = installed_versions

    activation_history = payload.get("activation_history")
    if isinstance(activation_history, list):
        normalized["activation_history"] = [str(value).strip() for value in activation_history if str(value).strip()]
    elif active_version:
        normalized["activation_history"] = [active_version]

    for legacy_key in ("bundle_root", "installed_paths"):
        if legacy_key in payload:
            normalized[legacy_key] = payload.get(legacy_key)
    return normalized
