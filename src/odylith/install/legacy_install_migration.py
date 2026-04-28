"""Legacy Odyssey-to-Odylith root migration owned by the install migration layer."""

from __future__ import annotations

import json
import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.install import bootstrap_assets
from odylith.install.fs import atomic_write_text
from odylith.install.gitignore_rules import ensure_odylith_gitignore_entry, rewrite_legacy_gitignore_entries
from odylith.install.migration_audit import LegacyReferenceAudit, audit_legacy_odyssey_references
from odylith.install.runtime import current_runtime_root, current_runtime_version, ensure_launcher
from odylith.install.state import (
    DEFAULT_REPO_SCHEMA_VERSION,
    append_install_ledger,
    install_integration_enabled,
    load_install_state,
    load_version_pin,
    write_install_state,
    write_version_pin,
)
from odylith.runtime.common.consumer_profile import consumer_profile_path, write_consumer_profile
from odylith.runtime.governance.legacy_backlog_normalization import normalize_legacy_backlog_index

LEGACY_ROOT_MIGRATION_ID = "legacy-odyssey-root-migration"

_LEGACY_TEXT_FILE_SUFFIXES = frozenset(
    {
        "",
        ".css",
        ".html",
        ".js",
        ".json",
        ".jsonl",
        ".md",
        ".mjs",
        ".mmd",
        ".py",
        ".sh",
        ".svg",
        ".toml",
        ".txt",
        ".yaml",
        ".yml",
    }
)


@dataclass(frozen=True)
class MigrationSummary:
    repo_root: Path
    odylith_root: Path
    state_root: Path
    launcher_path: Path
    consumer_profile_path: Path
    moved_paths: tuple[str, ...]
    removed_paths: tuple[str, ...]
    stale_reference_audit: LegacyReferenceAudit | None = None
    already_migrated: bool = False


def legacy_layout_present(*, repo_root: Path) -> bool:
    """Return whether the repo still carries legacy Odyssey install roots."""
    return (Path(repo_root) / "odyssey").exists() or (Path(repo_root) / ".odyssey").exists()


def legacy_operation_in_progress(*, repo_root: Path) -> bool:
    """Return whether a legacy or current install lock still carries an active owner."""
    root = Path(repo_root).resolve()
    for candidate in (
        root / ".odyssey" / "locks" / "install.lock",
        root / ".odylith" / "locks" / "install.lock",
    ):
        if not candidate.is_file():
            continue
        if str(candidate.read_text(encoding="utf-8") or "").strip():
            return True
    return False


def migrate_legacy_install_if_needed(*, repo_root: Path) -> MigrationSummary | None:
    """Apply the legacy root migration only when old roots are present."""
    root = Path(repo_root).expanduser().resolve()
    if not legacy_layout_present(repo_root=root):
        return None
    return migrate_legacy_install(repo_root=root)


def migrate_legacy_install(*, repo_root: str | Path) -> MigrationSummary:
    """Move legacy Odyssey roots into the Odylith install layout."""
    root = Path(repo_root).expanduser().resolve()
    old_product_root = root / "odyssey"
    old_state_root = root / ".odyssey"
    new_product_root = root / "odylith"
    new_state_root = root / ".odylith"

    if legacy_operation_in_progress(repo_root=root):
        raise RuntimeError("legacy install operation appears to be in progress; clear install locks before migrating")

    if not old_product_root.exists() and not old_state_root.exists():
        return MigrationSummary(
            repo_root=root,
            odylith_root=new_product_root,
            state_root=new_state_root,
            launcher_path=new_state_root / "bin" / "odylith",
            consumer_profile_path=consumer_profile_path(repo_root=root),
            moved_paths=(),
            removed_paths=(),
            stale_reference_audit=None,
            already_migrated=True,
        )

    moved_paths: list[str] = []
    removed_paths: list[str] = []
    if old_product_root.exists():
        if new_product_root.exists():
            _merge_legacy_tree(
                source_root=old_product_root,
                target_root=new_product_root,
                source_label="odyssey",
                target_label="odylith",
                moved_paths=moved_paths,
            )
            old_product_root.rmdir()
            moved_paths.append("odyssey/ -> odylith/")
        else:
            old_product_root.rename(new_product_root)
            moved_paths.append("odyssey/ -> odylith/")
    if old_state_root.exists():
        _absorb_legacy_state_root(old_state_root=old_state_root, new_state_root=new_state_root, moved_paths=moved_paths)

    new_state_root.mkdir(parents=True, exist_ok=True)
    for old_name, new_name in (("odyssey", "odylith"), ("odyssey-bootstrap", "odylith-bootstrap")):
        legacy_launcher = new_state_root / "bin" / old_name
        if legacy_launcher.exists():
            legacy_launcher.rename(new_state_root / "bin" / new_name)
            moved_paths.append(f".odyssey/bin/{old_name} -> .odylith/bin/{new_name}")

    purge_candidates = [
        new_state_root / "cache" / "odyssey-context-engine",
        new_state_root / "locks" / "odyssey-context-engine",
        new_state_root / "runtime" / "odyssey-memory",
        new_state_root / "runtime" / "odyssey-benchmarks",
        new_state_root / "runtime" / "odyssey-compiler",
        new_state_root / "runtime" / "release-upgrade-spotlight.v1.json",
    ]
    purge_candidates.extend((new_state_root / "runtime").glob("odyssey-context-engine*"))
    purge_candidates.extend((new_state_root / "runtime").glob("odyssey-vespa-sync*.json"))
    for candidate in purge_candidates:
        if not candidate.exists() and not candidate.is_symlink():
            continue
        removed_paths.append(str(candidate.relative_to(root)))
        if candidate.is_dir() and not candidate.is_symlink():
            shutil.rmtree(candidate)
        else:
            candidate.unlink()

    for path in (
        new_state_root / "install.json",
        new_state_root / "consumer-profile.json",
        new_product_root / "runtime" / "source" / "product-version.v1.json",
    ):
        _rewrite_json_file(path)
    _rewrite_jsonl_file(new_state_root / "install-ledger.v1.jsonl")
    _rewrite_legacy_text_tree(new_product_root)
    rewrite_legacy_gitignore_entries(repo_root=root)
    ensure_odylith_gitignore_entry(repo_root=root)
    normalize_legacy_backlog_index(repo_root=root)
    stale_reference_audit = audit_legacy_odyssey_references(repo_root=root)

    repo_role = bootstrap_assets.product_repo_role(repo_root=root)
    runtime_root = current_runtime_root(repo_root=root)
    fallback_python = _runtime_python(runtime_root) or Path(sys.executable)
    launcher_path = ensure_launcher(
        repo_root=root,
        fallback_python=fallback_python,
        allow_host_python_fallback=True,
    )
    written_profile = write_consumer_profile(repo_root=root)
    state = load_install_state(repo_root=root)
    if state:
        state["consumer_profile_path"] = str(written_profile)
        state["launcher_path"] = str(launcher_path)
        write_install_state(repo_root=root, payload=state)
    pin = load_version_pin(repo_root=root)
    if pin is not None:
        write_version_pin(
            repo_root=root,
            version=pin.odylith_version,
            repo_schema_version=pin.repo_schema_version,
            migration_required=False,
        )
    bootstrap_assets.ensure_repo_root_guidance_files(repo_root=root)
    bootstrap_assets.update_root_guidance_files(
        repo_root=root,
        install_active=install_integration_enabled(state),
        repo_role=repo_role,
    )
    append_install_ledger(
        repo_root=root,
        payload={
            "operation": "migrate-legacy-install",
            "status": "ready",
            "active_version": current_runtime_version(repo_root=root),
            "launcher_path": str(launcher_path),
            "removed_paths": removed_paths,
        },
    )
    return MigrationSummary(
        repo_root=root,
        odylith_root=new_product_root,
        state_root=new_state_root,
        launcher_path=launcher_path,
        consumer_profile_path=written_profile,
        moved_paths=tuple(moved_paths),
        removed_paths=tuple(removed_paths),
        stale_reference_audit=stale_reference_audit,
    )


def _runtime_python(runtime_root: Path | None) -> Path | None:
    if runtime_root is None:
        return None
    for candidate in (
        runtime_root / "bin" / "python3",
        runtime_root / "bin" / "python",
        runtime_root / "Scripts" / "python.exe",
    ):
        if candidate.exists():
            return candidate
    return None


def _rewrite_legacy_payload(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(_rewrite_legacy_payload(key)): _rewrite_legacy_payload(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_rewrite_legacy_payload(item) for item in value]
    if isinstance(value, str):
        return _rewrite_legacy_text(value)
    return value


def _rewrite_legacy_text(value: str) -> str:
    return (
        value.replace(".odyssey", ".odylith")
        .replace("odyssey/", "odylith/")
        .replace("/odyssey", "/odylith")
        .replace("Odyssey", "Odylith")
        .replace("odyssey", "odylith")
    )


def _rewrite_json_file(path: Path) -> None:
    if not path.is_file():
        return
    payload = json.loads(path.read_text(encoding="utf-8"))
    atomic_write_text(path, json.dumps(_rewrite_legacy_payload(payload), indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _rewrite_jsonl_file(path: Path) -> None:
    if not path.is_file():
        return
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        if not raw_line.strip():
            continue
        payload = json.loads(raw_line)
        lines.append(json.dumps(_rewrite_legacy_payload(payload), sort_keys=True))
    atomic_write_text(path, "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _rewrite_text_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        return
    if path.suffix.lower() not in _LEGACY_TEXT_FILE_SUFFIXES:
        return
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return
    updated = _rewrite_legacy_text(text)
    if updated != text:
        atomic_write_text(path, updated, encoding="utf-8")


def _rewrite_legacy_text_tree(root: Path) -> None:
    if not root.exists():
        return
    for path in sorted(root.rglob("*")):
        _rewrite_text_file(path)


def _merge_legacy_tree(
    *,
    source_root: Path,
    target_root: Path,
    source_label: str,
    target_label: str,
    moved_paths: list[str],
) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in sorted(source_root.iterdir(), key=lambda path: (not path.is_dir(), path.name.lower())):
        target_path = target_root / source_path.name
        if source_path.is_dir() and not source_path.is_symlink():
            if target_path.exists() and not target_path.is_dir():
                if target_path.is_symlink() or target_path.is_file():
                    target_path.unlink()
                else:
                    shutil.rmtree(target_path)
            if target_path.is_dir():
                _merge_legacy_tree(
                    source_root=source_path,
                    target_root=target_path,
                    source_label=f"{source_label}/{source_path.name}",
                    target_label=f"{target_label}/{source_path.name}",
                    moved_paths=moved_paths,
                )
                source_path.rmdir()
                continue
        elif target_path.exists():
            if target_path.is_dir() and not target_path.is_symlink():
                shutil.rmtree(target_path)
            else:
                target_path.unlink()
        source_path.rename(target_path)
        moved_paths.append(f"{source_label}/{source_path.name} -> {target_label}/{target_path.name}")


def _is_transient_odylith_state_root(path: Path) -> bool:
    if not path.exists():
        return False
    for candidate in path.rglob("*"):
        relative = candidate.relative_to(path)
        if candidate.is_dir():
            continue
        if relative == Path("locks/install.lock"):
            content = str(candidate.read_text(encoding="utf-8") or "").strip()
            if not content:
                continue
        return False
    return True


def _absorb_legacy_state_root(*, old_state_root: Path, new_state_root: Path, moved_paths: list[str]) -> None:
    if not new_state_root.exists() or _is_transient_odylith_state_root(new_state_root):
        if new_state_root.exists():
            shutil.rmtree(new_state_root)
        old_state_root.rename(new_state_root)
        _normalize_migrated_current_runtime_symlink(state_root=new_state_root)
        moved_paths.append(".odyssey/ -> .odylith/")
        return

    new_state_root.mkdir(parents=True, exist_ok=True)
    root_move_recorded = False
    legacy_bin_root = old_state_root / "bin"
    new_bin_root = new_state_root / "bin"
    for old_name, new_name in (("odyssey", "odylith"), ("odyssey-bootstrap", "odylith-bootstrap")):
        source_path = legacy_bin_root / old_name
        target_path = new_bin_root / new_name
        if source_path.exists() and not target_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(target_path)
            if not root_move_recorded:
                moved_paths.append(".odyssey/ -> .odylith/")
                root_move_recorded = True
            moved_paths.append(f".odyssey/bin/{old_name} -> .odylith/bin/{new_name}")

    legacy_versions_root = old_state_root / "runtime" / "versions"
    new_versions_root = new_state_root / "runtime" / "versions"
    if legacy_versions_root.is_dir():
        new_versions_root.mkdir(parents=True, exist_ok=True)
        for version_root in sorted(legacy_versions_root.iterdir(), key=lambda path: path.name):
            target_root = new_versions_root / version_root.name
            if target_root.exists():
                continue
            version_root.rename(target_root)
            if not root_move_recorded:
                moved_paths.append(".odyssey/ -> .odylith/")
                root_move_recorded = True
            moved_paths.append(
                f".odyssey/runtime/versions/{version_root.name} -> .odylith/runtime/versions/{version_root.name}"
            )

    legacy_current = old_state_root / "runtime" / "current"
    new_current = new_state_root / "runtime" / "current"
    if (legacy_current.exists() or legacy_current.is_symlink()) and not (new_current.exists() or new_current.is_symlink()):
        new_current.parent.mkdir(parents=True, exist_ok=True)
        legacy_current.rename(new_current)
        _normalize_migrated_current_runtime_symlink(state_root=new_state_root)
        if not root_move_recorded:
            moved_paths.append(".odyssey/ -> .odylith/")
            root_move_recorded = True
        moved_paths.append(".odyssey/runtime/current -> .odylith/runtime/current")

    for relative_path in (
        Path("install.json"),
        Path("consumer-profile.json"),
        Path("install-ledger.v1.jsonl"),
    ):
        source_path = old_state_root / relative_path
        target_path = new_state_root / relative_path
        if source_path.exists() and not target_path.exists():
            target_path.parent.mkdir(parents=True, exist_ok=True)
            source_path.rename(target_path)
            if not root_move_recorded:
                moved_paths.append(".odyssey/ -> .odylith/")
                root_move_recorded = True
            moved_paths.append(f".odyssey/{relative_path.as_posix()} -> .odylith/{relative_path.as_posix()}")
    shutil.rmtree(old_state_root)


def _normalize_migrated_current_runtime_symlink(*, state_root: Path) -> None:
    current_root = state_root / "runtime" / "current"
    if not current_root.is_symlink():
        return
    try:
        raw_target = Path(os.readlink(current_root))
    except OSError:
        return
    version_name = raw_target.name.strip()
    if not version_name:
        return
    candidate_root = state_root / "runtime" / "versions" / version_name
    if not candidate_root.is_dir():
        return
    normalized_target = Path("versions") / version_name
    if raw_target == normalized_target:
        return
    current_root.unlink()
    current_root.symlink_to(normalized_target)
