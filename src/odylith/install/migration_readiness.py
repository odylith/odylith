"""Read-only migration-readiness evidence for repo-local managed runtimes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from odylith.install import runtime_integrity
from odylith.install.runtime import (
    current_runtime_root,
    load_runtime_feature_packs,
    load_runtime_verification,
)
from odylith.install.state import (
    current_activation_history,
    installed_version_entry,
    load_install_state,
)

_REQUIRED_VERIFICATION_FIELDS = (
    "manifest_sha256",
    "provenance_sha256",
    "runtime_bundle_sha256",
    "sbom_sha256",
    "wheel_sha256",
)
_HEX_SHA256_LENGTH = 64


@dataclass(frozen=True)
class MigrationFeaturePackEvidence:
    pack_id: str
    asset_name: str
    platform: str
    paths: tuple[str, ...]
    feature_pack_sha256: str


@dataclass(frozen=True)
class RuntimeMigrationReadiness:
    eligible: bool
    repo_root: Path
    version: str
    platform_slug: str
    active_runtime_root: Path | None
    state_runtime_root: Path | None
    runtime_bundle_sha256: str
    wheel_sha256: str
    manifest_sha256: str
    provenance_sha256: str
    sbom_sha256: str
    feature_packs: tuple[MigrationFeaturePackEvidence, ...]
    trust_env_path: Path | None
    trust_tree_path: Path | None
    trust_env_sha256: str
    trust_tree_sha256: str
    trust_tree_digest: str
    hot_file_count: int
    activation_history: tuple[str, ...]
    content_identity: str
    missing: tuple[str, ...]
    reasons: tuple[str, ...]


def inspect_runtime_migration_readiness(*, repo_root: str | Path) -> RuntimeMigrationReadiness:
    """Return whether the active repo-local runtime has enough evidence for future migration."""
    root = Path(repo_root).expanduser().resolve()
    state = load_install_state(repo_root=root)
    version = str(state.get("active_version") or "").strip()
    activation_history = tuple(current_activation_history(state))
    entry = installed_version_entry(state, version) if version else {}
    state_runtime_root = _path_or_none(entry.get("runtime_root"))
    active_runtime_root = current_runtime_root(repo_root=root) if version else None
    runtime_root = active_runtime_root or state_runtime_root

    missing: list[str] = []
    reasons: list[str] = []
    if not version:
        missing.append("install_state.active_version")
    if not activation_history:
        missing.append("install_state.activation_history")
    if state_runtime_root is None:
        missing.append("install_state.installed_versions.active.runtime_root")
    if active_runtime_root is None:
        missing.append("runtime.current.trusted_root")
    elif state_runtime_root is not None and active_runtime_root != state_runtime_root:
        reasons.append("runtime.current does not match install-state active runtime_root")

    metadata = _load_runtime_metadata(runtime_root)
    verification = _runtime_verification_evidence(runtime_root)
    feature_packs = _feature_pack_evidence(runtime_root)
    platform_slug = str(metadata.get("platform") or "").strip()

    if not platform_slug:
        missing.append("runtime_metadata.platform")
    if str(metadata.get("version") or "").strip() != version:
        reasons.append("runtime metadata version does not match install-state active version")
    if not feature_packs:
        missing.append("runtime_feature_packs")

    verification_values: dict[str, str] = {}
    for field in _REQUIRED_VERIFICATION_FIELDS:
        value = str(verification.get(field) or "").strip()
        verification_values[field] = value
        if not value:
            missing.append(f"runtime_verification.{field}")
        elif not _is_sha256(value):
            reasons.append(f"runtime verification field is not a sha256 digest: {field}")

    trust_env_path: Path | None = None
    trust_tree_path: Path | None = None
    trust_env_sha256 = ""
    trust_tree_sha256 = ""
    trust_tree_digest = ""
    hot_file_count = 0
    if version:
        selected_env, selected_tree = runtime_integrity.managed_runtime_trust_paths(repo_root=root, version=version)
        trust_env_path = selected_env
        trust_tree_path = selected_tree
        trust_env = runtime_integrity.load_managed_runtime_trust_env(repo_root=root, version=version)
        trust_tree = runtime_integrity.load_managed_runtime_trust_tree(repo_root=root, version=version)
        if trust_env:
            trust_env_sha256 = _file_sha256(selected_env)
            hot_file_count = _int_value(trust_env.get("HOT_FILE_COUNT"))
        else:
            missing.append("managed_runtime_trust.hot_file_receipt")
        if trust_tree:
            trust_tree_sha256 = _file_sha256(selected_tree)
            summary = trust_tree.get("summary")
            if isinstance(summary, Mapping):
                trust_tree_digest = str(summary.get("tree_sha256") or "").strip()
        else:
            missing.append("managed_runtime_trust.tree_receipt")
        if not trust_tree_digest:
            missing.append("managed_runtime_trust.tree_sha256")
        if hot_file_count <= 0:
            missing.append("managed_runtime_trust.hot_file_count")

    if runtime_root is not None:
        reasons.extend(runtime_integrity.managed_runtime_integrity_reasons(repo_root=root, runtime_root=runtime_root))

    missing_tuple = tuple(dict.fromkeys(missing))
    reasons_tuple = tuple(dict.fromkeys(reasons))
    content_identity = _content_identity(
        version=version,
        platform_slug=platform_slug,
        verification=verification_values,
        feature_packs=feature_packs,
        trust_tree_digest=trust_tree_digest,
    )
    return RuntimeMigrationReadiness(
        eligible=not missing_tuple and not reasons_tuple,
        repo_root=root,
        version=version,
        platform_slug=platform_slug,
        active_runtime_root=active_runtime_root,
        state_runtime_root=state_runtime_root,
        runtime_bundle_sha256=verification_values["runtime_bundle_sha256"],
        wheel_sha256=verification_values["wheel_sha256"],
        manifest_sha256=verification_values["manifest_sha256"],
        provenance_sha256=verification_values["provenance_sha256"],
        sbom_sha256=verification_values["sbom_sha256"],
        feature_packs=feature_packs,
        trust_env_path=trust_env_path,
        trust_tree_path=trust_tree_path,
        trust_env_sha256=trust_env_sha256,
        trust_tree_sha256=trust_tree_sha256,
        trust_tree_digest=trust_tree_digest,
        hot_file_count=hot_file_count,
        activation_history=activation_history,
        content_identity=content_identity,
        missing=missing_tuple,
        reasons=reasons_tuple,
    )


def _runtime_verification_evidence(runtime_root: Path | None) -> dict[str, object]:
    if runtime_root is None:
        return {}
    payload = load_runtime_verification(runtime_root)
    verification = payload.get("verification")
    return dict(verification) if isinstance(verification, Mapping) else {}


def _feature_pack_evidence(runtime_root: Path | None) -> tuple[MigrationFeaturePackEvidence, ...]:
    if runtime_root is None:
        return ()
    evidence: list[MigrationFeaturePackEvidence] = []
    for pack_id, details in sorted(load_runtime_feature_packs(runtime_root).items()):
        raw_paths = details.get("paths")
        paths = (
            tuple(str(path).strip() for path in raw_paths if str(path).strip())
            if isinstance(raw_paths, (list, tuple))
            else ()
        )
        verification = details.get("verification")
        feature_pack_sha256 = (
            str(verification.get("feature_pack_sha256") or "").strip() if isinstance(verification, Mapping) else ""
        )
        if feature_pack_sha256 and not _is_sha256(feature_pack_sha256):
            continue
        if not all(
            (
                str(pack_id).strip(),
                str(details.get("asset_name") or "").strip(),
                str(details.get("platform") or "").strip(),
                paths,
                feature_pack_sha256,
            )
        ):
            continue
        evidence.append(
            MigrationFeaturePackEvidence(
                pack_id=str(pack_id).strip(),
                asset_name=str(details.get("asset_name") or "").strip(),
                platform=str(details.get("platform") or "").strip(),
                paths=paths,
                feature_pack_sha256=feature_pack_sha256,
            )
        )
    return tuple(evidence)


def _load_runtime_metadata(runtime_root: Path | None) -> dict[str, object]:
    if runtime_root is None:
        return {}
    path = runtime_root / "runtime-metadata.json"
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _content_identity(
    *,
    version: str,
    platform_slug: str,
    verification: Mapping[str, str],
    feature_packs: tuple[MigrationFeaturePackEvidence, ...],
    trust_tree_digest: str,
) -> str:
    payload = {
        "feature_packs": [
            {
                "asset_name": item.asset_name,
                "feature_pack_sha256": item.feature_pack_sha256,
                "pack_id": item.pack_id,
                "paths": list(item.paths),
                "platform": item.platform,
            }
            for item in feature_packs
        ],
        "platform": platform_slug,
        "release": {
            field: verification.get(field, "")
            for field in _REQUIRED_VERIFICATION_FIELDS
        },
        "trust_tree_sha256": trust_tree_digest,
        "version": version,
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _path_or_none(value: object) -> Path | None:
    token = str(value or "").strip()
    return Path(token).expanduser().resolve() if token else None


def _file_sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        return ""
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _is_sha256(value: str) -> bool:
    token = str(value or "").strip().lower()
    return len(token) == _HEX_SHA256_LENGTH and all(character in "0123456789abcdef" for character in token)


def _int_value(value: object) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return 0
