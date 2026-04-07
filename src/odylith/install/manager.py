from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

from odylith import __version__
from odylith.install.fs import atomic_write_text
from odylith.install.managed_runtime import (
    CONTEXT_ENGINE_FEATURE_PACK_ID,
    MANAGED_RUNTIME_FEATURE_PACK_FILENAME,
    MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
)
from odylith.install.agents import has_managed_block, update_agents_file
from odylith.install.migration_audit import LegacyReferenceAudit
from odylith.install.migration_audit import audit_legacy_odyssey_references
from odylith.install.repair import reset_local_state as reset_install_local_state
from odylith.install.python_env import scrubbed_python_env
from odylith.install.release_assets import ReleaseInfo, fetch_release
from odylith.install.runtime import (
    clear_runtime_activation,
    current_runtime_root,
    current_runtime_version,
    doctor_runtime,
    ensure_launcher,
    install_release_feature_pack,
    ensure_source_runtime,
    ensure_wrapped_runtime,
    install_release_runtime,
    load_runtime_feature_packs,
    preferred_repair_entrypoint,
    runtime_context_engine_feature_pack_installed,
    runtime_verification_evidence,
    runtime_root_for_version,
    switch_runtime,
    write_managed_runtime_trust,
)
from odylith.install.runtime_status import inspect_runtime_source, trust_only_runtime_failure
from odylith.install.state import (
    AUTHORITATIVE_RELEASE_REPO,
    DEFAULT_REPO_SCHEMA_VERSION,
    append_install_ledger,
    current_activation_history,
    install_state_path,
    install_integration_enabled,
    install_lock,
    load_install_state as load_install_state_file,
    load_version_pin,
    record_activation,
    version_pin_path,
    write_install_state,
    write_version_pin,
)
from odylith.runtime.common.consumer_profile import consumer_profile_path, write_consumer_profile
from odylith.runtime.common.product_assets import bundled_product_root
from odylith.runtime.governance.legacy_backlog_normalization import normalize_legacy_backlog_index
from odylith.runtime.governance import sync_casebook_bug_index
from odylith.runtime.memory import odylith_memory_backend

_SEMVER_RE = re.compile(r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:[-+](?P<suffix>.+))?$")
PRODUCT_REPO_ROLE = "product_repo"
CONSUMER_REPO_ROLE = "consumer_repo"
PINNED_RELEASE_POSTURE = "pinned_release"
DETACHED_SOURCE_LOCAL_POSTURE = "detached_source_local"
DIVERGED_VERIFIED_VERSION_POSTURE = "diverged_verified_version"
UNINSTALLED_OR_INCOMPLETE_POSTURE = "uninstalled_or_incomplete"
PINNED_RUNTIME_SOURCE = "pinned_runtime"
SOURCE_CHECKOUT_RUNTIME_SOURCE = "source_checkout"
VERIFIED_RUNTIME_SOURCE = "verified_runtime"
WRAPPED_RUNTIME_SOURCE = "wrapped_runtime"
INSTALL_STATE_ONLY_RUNTIME_SOURCE = "install_state_only"
MISSING_RUNTIME_SOURCE = "missing_runtime"
_ODYLITH_GITIGNORE_ENTRY = "/.odylith/"
_ODYLITH_GITIGNORE_PATTERNS = {
    ".odylith",
    ".odylith/",
    "/.odylith",
    "/.odylith/",
}
_ODYLITH_GITIGNORE_ENTRIES = (_ODYLITH_GITIGNORE_ENTRY,)
_FIRST_RUN_SURFACE_TARGETS: tuple[str, ...] = (
    "odylith/index.html",
    "odylith/radar/radar.html",
    "odylith/atlas/atlas.html",
    "odylith/compass/compass.html",
    "odylith/registry/registry.html",
    "odylith/casebook/casebook.html",
)
_HOSTED_INSTALL_COMMAND = (
    "curl -fsSL https://odylith.ai/install.sh | bash"
)
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
class InstallSummary:
    repo_root: Path
    version: str
    odylith_root: Path
    state_root: Path
    launcher_path: Path
    consumer_profile_path: Path
    agents_updated: bool
    git_repo_present: bool
    repo_guidance_created: bool
    gitignore_updated: bool = False
    migration: MigrationSummary | None = None


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


@dataclass(frozen=True)
class UpgradeSummary:
    active_version: str
    launcher_path: Path
    pin_changed: bool
    pinned_version: str
    previous_version: str
    repo_root: Path
    repo_role: str
    followed_latest: bool
    release_body: str
    release_highlights: tuple[str, ...]
    release_published_at: str
    release_tag: str
    release_url: str
    verification: dict[str, object]
    repaired: bool = False
    migration: MigrationSummary | None = None


@dataclass(frozen=True)
class RollbackSummary:
    active_version: str
    diverged_from_pin: bool
    launcher_path: Path
    pinned_version: str
    previous_version: str
    repo_root: Path


@dataclass(frozen=True)
class VersionStatus:
    active_version: str
    available_versions: list[str]
    context_engine_mode: str
    context_engine_pack_installed: bool | None
    detached: bool
    diverged_from_pin: bool
    last_known_good_version: str
    pinned_version: str
    posture: str
    repo_root: Path
    repo_role: str
    release_eligible: bool | None
    runtime_source: str
    runtime_source_detail: str
    runtime_trust_degraded: bool
    runtime_trust_reasons: tuple[str, ...]


@dataclass(frozen=True)
class LifecycleStep:
    label: str
    mutation_classes: tuple[str, ...]
    paths: tuple[str, ...]
    detail: str = ""


@dataclass(frozen=True)
class LifecyclePlan:
    command: str
    headline: str
    steps: tuple[LifecycleStep, ...]
    dirty_overlap: tuple[str, ...]
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class StartPreflight:
    lane: str
    reason: str
    next_command: str
    healthy: bool
    launcher_exists: bool
    bootstrap_launcher_exists: bool
    install_shape_present: bool
    status: VersionStatus | None = None


def _repo_root(path: str | Path, *, require_agents: bool = True) -> Path:
    root = Path(path).expanduser().resolve()
    agents_file = root / "AGENTS.md"
    if require_agents and not agents_file.is_file():
        raise ValueError(f"repo root does not contain AGENTS.md: {root}")
    return root


def _git_repo_present(*, repo_root: Path) -> bool:
    return (Path(repo_root).resolve() / ".git").exists()


def _ensure_odylith_gitignore_entry(*, repo_root: Path, git_repo_present: bool | None = None) -> bool:
    root = Path(repo_root).resolve()
    del git_repo_present
    path = root / ".gitignore"
    if path.exists() and not path.is_file():
        return False
    existing = path.read_text(encoding="utf-8") if path.is_file() else ""
    normalized_lines = {line.strip() for line in existing.splitlines()}
    missing_entries: list[str] = []
    if not normalized_lines.intersection(_ODYLITH_GITIGNORE_PATTERNS):
        missing_entries.append(_ODYLITH_GITIGNORE_ENTRY)
    if not missing_entries:
        return False
    updated = existing
    if updated and not updated.endswith("\n"):
        updated += "\n"
    for entry in missing_entries:
        updated += f"{entry}\n"
    atomic_write_text(path, updated, encoding="utf-8")
    return True


def _rewrite_legacy_gitignore_entries(*, repo_root: Path) -> None:
    path = Path(repo_root).resolve() / ".gitignore"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    updated = text.replace("/.odyssey/", "/.odylith/").replace("/.odyssey", "/.odylith")
    if updated != text:
        atomic_write_text(path, updated, encoding="utf-8")


def _legacy_operation_in_progress(*, repo_root: Path) -> bool:
    for candidate in (
        repo_root / ".odyssey" / "locks" / "install.lock",
        repo_root / ".odylith" / "locks" / "install.lock",
    ):
        if not candidate.is_file():
            continue
        if str(candidate.read_text(encoding="utf-8") or "").strip():
            return True
    return False


def _rewrite_legacy_payload(value: Any) -> Any:
    if isinstance(value, Mapping):
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
        str(value)
        .replace("ODYSSEY", "ODYLITH")
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
    except (OSError, UnicodeDecodeError):
        return
    updated = _rewrite_legacy_text(text)
    if updated != text:
        atomic_write_text(path, updated, encoding="utf-8")


def _rewrite_legacy_text_tree(root: Path) -> None:
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        _rewrite_text_file(path)


def _legacy_layout_present(*, repo_root: Path) -> bool:
    return (repo_root / "odyssey").exists() or (repo_root / ".odyssey").exists()


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


def _migrate_legacy_install_if_needed(*, repo_root: Path) -> MigrationSummary | None:
    if not _legacy_layout_present(repo_root=repo_root):
        return None
    return migrate_legacy_install(repo_root=repo_root)


def _lifecycle_step(
    label: str,
    *mutation_classes: str,
    paths: Sequence[str],
    detail: str = "",
) -> LifecycleStep:
    normalized_paths = tuple(
        str(token).strip()
        for token in paths
        if str(token).strip()
    )
    normalized_classes = tuple(
        str(token).strip()
        for token in mutation_classes
        if str(token).strip()
    )
    return LifecycleStep(
        label=label,
        mutation_classes=normalized_classes,
        paths=normalized_paths,
        detail=str(detail).strip(),
    )


def _dirty_overlap_for_paths(*, repo_root: Path, paths: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(dict.fromkeys(str(token).strip() for token in paths if str(token).strip()))
    if not normalized or not _git_repo_present(repo_root=repo_root):
        return ()
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *normalized,
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    if completed.returncode != 0:
        return ()
    return tuple(line.rstrip() for line in str(completed.stdout or "").splitlines() if line.strip())


def _lifecycle_plan(
    *,
    command: str,
    headline: str,
    steps: Sequence[LifecycleStep],
    notes: Sequence[str] = (),
    repo_root: Path,
) -> LifecyclePlan:
    normalized_steps = tuple(steps)
    dirty_overlap = _dirty_overlap_for_paths(
        repo_root=repo_root,
        paths=[path for step in normalized_steps for path in step.paths],
    )
    return LifecyclePlan(
        command=str(command).strip(),
        headline=str(headline).strip(),
        steps=normalized_steps,
        dirty_overlap=dirty_overlap,
        notes=tuple(str(note).strip() for note in notes if str(note).strip()),
    )


def plan_install_lifecycle(
    *,
    repo_root: str | Path,
    adopt_latest: bool = False,
    target_version: str = "",
) -> LifecyclePlan:
    root = _repo_root(repo_root, require_agents=False)
    first_install = not load_install_state(repo_root=root)
    missing_surfaces = [
        token
        for token in _FIRST_RUN_SURFACE_TARGETS
        if not (root / token).is_file()
    ]
    steps: list[LifecycleStep] = []
    if _legacy_layout_present(repo_root=root):
        steps.append(
            _lifecycle_step(
                "Migrate any legacy repo roots into the Odylith layout before rematerializing the runtime.",
                "repo_owned_truth",
                "runtime_state",
                paths=("odyssey/", ".odyssey/", "odylith/", ".odylith/"),
                detail="This preserves repo-owned truth under the new root names and purges old volatile runtime state.",
            )
        )
    steps.extend(
        [
        _lifecycle_step(
            "Materialize the repo-owned Odylith bootstrap tree and managed guidance.",
            "managed_guidance",
            "repo_owned_truth",
            paths=(
                "AGENTS.md",
                ".gitignore",
                "odylith/AGENTS.md",
                "odylith/agents-guidelines/",
                "odylith/skills/",
                "odylith/runtime/source/",
                "odylith/radar/source/",
                "odylith/technical-plans/",
                "odylith/registry/source/",
                "odylith/atlas/source/",
            ),
            detail="First install seeds the repo-owned Odylith truth tree; later installs rematerialize the managed guidance layer.",
        ),
        _lifecycle_step(
            "Stage or reuse the Odylith-managed runtime and refresh the repo-local launchers.",
            "runtime_state",
            paths=(
                ".odylith/install.json",
                ".odylith/bin/odylith",
                ".odylith/bin/odylith-bootstrap",
                ".odylith/runtime/current",
                ".odylith/runtime/versions/",
                ".odylith/",
            ),
            detail="This keeps Odylith itself on the managed runtime without touching the repo's own application toolchain.",
        ),
        ]
    )
    if adopt_latest:
        steps.append(
            _lifecycle_step(
                "Adopt the latest verified release and align the tracked repo pin in the same step.",
                "runtime_state",
                "repo_pin",
                paths=(
                    ".odylith/runtime/current",
                    ".odylith/runtime/versions/",
                    "odylith/runtime/source/product-version.v1.json",
                ),
                detail=(
                    f"Target release: {target_version}."
                    if str(target_version).strip()
                    else "Target release: latest verified."
                ),
            )
        )
    if first_install or missing_surfaces:
        steps.append(
            _lifecycle_step(
                "Render the first-run Odylith shell surfaces so the local dashboard is immediately usable.",
                "generated_surfaces",
                paths=tuple(missing_surfaces or _FIRST_RUN_SURFACE_TARGETS),
            )
        )
    notes = [
        "Normal install/rematerialize does not rewrite repo-owned governance truth outside the initial bootstrap tree.",
    ]
    if adopt_latest:
        notes.append("`install --adopt-latest` keeps the active managed runtime and tracked repo pin aligned in one command.")
    return _lifecycle_plan(
        command="install",
        headline="Preview the Odylith install/rematerialize lifecycle.",
        steps=steps,
        notes=notes,
        repo_root=root,
    )


def plan_reinstall_lifecycle(
    *,
    repo_root: str | Path,
    target_version: str = "",
) -> LifecyclePlan:
    root = _repo_root(repo_root, require_agents=False)
    steps: list[LifecycleStep] = []
    if _legacy_layout_present(repo_root=root):
        steps.append(
            _lifecycle_step(
                "Migrate any legacy repo roots into the Odylith layout before reinstalling the managed runtime.",
                "repo_owned_truth",
                "runtime_state",
                paths=("odyssey/", ".odyssey/", "odylith/", ".odylith/"),
                detail="Legacy repo truth moves forward under `odylith/`; old volatile state is purged instead of preserved.",
            )
        )
    steps.extend(
        [
        _lifecycle_step(
            "Reaffirm the repo-owned Odylith bootstrap tree and managed guidance layer.",
            "managed_guidance",
            paths=(
                "AGENTS.md",
                ".gitignore",
                "odylith/AGENTS.md",
                "odylith/agents-guidelines/",
                "odylith/skills/",
            ),
        ),
        _lifecycle_step(
            "Restage the verified managed runtime and refresh both repo-local launchers.",
            "runtime_state",
            paths=(
                ".odylith/install.json",
                ".odylith/bin/odylith",
                ".odylith/bin/odylith-bootstrap",
                ".odylith/runtime/current",
                ".odylith/runtime/versions/",
            ),
            detail=(
                f"Target release: {target_version}."
                if str(target_version).strip()
                else "Target release: latest verified."
            ),
        ),
        _lifecycle_step(
            "Write the tracked Odylith repo pin so the active runtime and recorded pin land together.",
            "repo_pin",
            paths=("odylith/runtime/source/product-version.v1.json",),
        ),
        _lifecycle_step(
            "Refresh the shell-facing dashboard surfaces after the reinstall lands.",
            "generated_surfaces",
            paths=("odylith/index.html", "odylith/radar/radar.html", "odylith/compass/compass.html"),
        ),
        ]
    )
    return _lifecycle_plan(
        command="reinstall",
        headline="Preview the one-step Odylith reinstall flow.",
        steps=steps,
        notes=(
            "Reinstall stays on verified release assets only and does not widen into source-local posture.",
        ),
        repo_root=root,
    )


def plan_upgrade_lifecycle(
    *,
    repo_root: str | Path,
    version: str = "",
    source_repo: str | Path | None = None,
    write_pin: bool = False,
) -> LifecyclePlan:
    root = _repo_root(repo_root, require_agents=False)
    repo_role = product_repo_role(repo_root=root)
    source_repo_token = str(source_repo or "").strip()
    requested_version = str(version or "").strip()
    follow_latest = repo_role != PRODUCT_REPO_ROLE and not requested_version and not source_repo_token
    steps: list[LifecycleStep] = []
    if _legacy_layout_present(repo_root=root):
        steps.append(
            _lifecycle_step(
                "Migrate any legacy repo roots into the Odylith layout before changing the active runtime.",
                "repo_owned_truth",
                "runtime_state",
                paths=("odyssey/", ".odyssey/", "odylith/", ".odylith/"),
                detail="This rescue path lets the Odylith launcher recover a pre-rename install even if the old launcher can no longer upgrade itself.",
            )
        )
    steps.append(
        _lifecycle_step(
            "Refresh the consumer profile and managed guidance before changing the active runtime.",
            "managed_guidance",
            paths=("AGENTS.md", "odylith/AGENTS.md", "odylith/agents-guidelines/", "odylith/skills/"),
        )
    )
    if source_repo_token:
        steps.append(
            _lifecycle_step(
                "Switch the product repo into detached source-local runtime execution.",
                "runtime_state",
                paths=(
                    ".odylith/install.json",
                    ".odylith/bin/odylith",
                    ".odylith/bin/odylith-bootstrap",
                    ".odylith/runtime/current",
                ),
                detail="This lane is product-repo-only and leaves the tracked release pin unchanged.",
            )
        )
    else:
        steps.append(
            _lifecycle_step(
                "Stage the verified managed runtime, atomically activate it, and refresh the repo-local launchers.",
                "runtime_state",
                paths=(
                    ".odylith/install.json",
                    ".odylith/bin/odylith",
                    ".odylith/bin/odylith-bootstrap",
                    ".odylith/runtime/current",
                    ".odylith/runtime/versions/",
                ),
                detail=(
                    f"Target release: {requested_version}."
                    if requested_version
                    else "Target release: latest verified release."
                    if follow_latest
                    else "Target release: tracked repo pin."
                ),
            )
        )
        if write_pin or follow_latest:
            steps.append(
                _lifecycle_step(
                    "Update the tracked Odylith repo pin to match the requested verified release.",
                    "repo_pin",
                    paths=("odylith/runtime/source/product-version.v1.json",),
                )
            )
        steps.append(
            _lifecycle_step(
                "Refresh the shell-facing dashboard surfaces after the runtime upgrade settles.",
                "generated_surfaces",
                paths=("odylith/index.html", "odylith/radar/radar.html", "odylith/compass/compass.html"),
            )
        )
    notes = [
        "Consumer upgrades stay on verified release assets only.",
    ]
    if not source_repo_token:
        notes.append(
            "Normal upgrade may normalize legacy Casebook bug IDs and refresh the Casebook bug index when older bug markdown still lacks canonical IDs."
        )
    return _lifecycle_plan(
        command="upgrade",
        headline="Preview the Odylith upgrade lifecycle.",
        steps=steps,
        notes=notes,
        repo_root=root,
    )


def evaluate_start_preflight(
    *,
    repo_root: str | Path,
    status_only: bool = False,
) -> StartPreflight:
    root = _repo_root(repo_root, require_agents=False)
    launcher_path = root / ".odylith" / "bin" / "odylith"
    bootstrap_launcher_path = root / ".odylith" / "bin" / "odylith-bootstrap"
    install_shape_present = _has_customer_starter_tree(repo_root=root)
    launcher_exists = launcher_path.is_file()
    bootstrap_launcher_exists = bootstrap_launcher_path.is_file()
    state_file_present = install_state_path(repo_root=root).is_file()
    consumer_profile_present = consumer_profile_path(repo_root=root).is_file()
    version_pin_present = version_pin_path(repo_root=root).is_file()

    def _preferred_repair_command() -> str:
        preferred = preferred_repair_entrypoint(repo_root=root)
        if preferred:
            return preferred
        return _HOSTED_INSTALL_COMMAND

    status: VersionStatus | None
    try:
        status = version_status(repo_root=root)
    except Exception:
        status = None
    if not install_shape_present:
        repairable = launcher_exists or bootstrap_launcher_exists
        return StartPreflight(
            lane="repair" if repairable else "install",
            reason=(
                "The repo-local Odylith launchers exist, but the tracked Odylith install shape is incomplete."
                if repairable
                else "Odylith is not installed in this repository yet."
            ),
            next_command=_preferred_repair_command(),
            healthy=False,
            launcher_exists=launcher_exists,
            bootstrap_launcher_exists=bootstrap_launcher_exists,
            install_shape_present=False,
            status=status,
        )
    readiness_gaps: list[str] = []
    if not state_file_present:
        readiness_gaps.append("install state missing")
    if not consumer_profile_present:
        readiness_gaps.append("consumer profile missing")
    if not version_pin_present:
        readiness_gaps.append("product version pin missing")
    if readiness_gaps:
        return StartPreflight(
            lane="repair",
            reason=", ".join(readiness_gaps),
            next_command=_preferred_repair_command(),
            healthy=False,
            launcher_exists=launcher_exists,
            bootstrap_launcher_exists=bootstrap_launcher_exists,
            install_shape_present=True,
            status=status,
        )
    if not launcher_exists or not bootstrap_launcher_exists:
        return StartPreflight(
            lane="repair",
            reason="The repo-local Odylith launcher layer is incomplete.",
            next_command=_preferred_repair_command(),
            healthy=False,
            launcher_exists=launcher_exists,
            bootstrap_launcher_exists=bootstrap_launcher_exists,
            install_shape_present=True,
            status=status,
        )
    healthy, reasons = doctor_runtime(repo_root=root, repair=False)
    if not healthy:
        return StartPreflight(
            lane="repair",
            reason=", ".join(reasons) if reasons else "The active Odylith runtime is unhealthy.",
            next_command=_preferred_repair_command(),
            healthy=False,
            launcher_exists=launcher_exists,
            bootstrap_launcher_exists=bootstrap_launcher_exists,
            install_shape_present=True,
            status=status,
        )
    consumer_lane_violation = (
        _consumer_lane_violation_reason(
            repo_role=status.repo_role,
            posture=status.posture,
            runtime_source=status.runtime_source,
        )
        if status is not None
        else ""
    )
    if consumer_lane_violation:
        return StartPreflight(
            lane="repair",
            reason=consumer_lane_violation,
            next_command=_preferred_repair_command(),
            healthy=False,
            launcher_exists=launcher_exists,
            bootstrap_launcher_exists=bootstrap_launcher_exists,
            install_shape_present=True,
            status=status,
        )
    if status_only:
        return StartPreflight(
            lane="status",
            reason="Status-only preflight requested.",
            next_command="./.odylith/bin/odylith version --repo-root .",
            healthy=True,
            launcher_exists=True,
            bootstrap_launcher_exists=True,
            install_shape_present=True,
            status=status,
        )
    return StartPreflight(
        lane="bootstrap",
        reason="Odylith is healthy enough to start from the first-turn grounding path.",
        next_command="./.odylith/bin/odylith start --repo-root .",
        healthy=True,
        launcher_exists=True,
        bootstrap_launcher_exists=True,
        install_shape_present=True,
        status=status,
    )


def _release_summary_fields(release: object | None) -> dict[str, object]:
    if release is None:
        return {
            "release_body": "",
            "release_highlights": (),
            "release_published_at": "",
            "release_tag": "",
            "release_url": "",
        }
    highlights_value = getattr(release, "highlights", ()) or ()
    return {
        "release_body": str(getattr(release, "body", "") or "").strip(),
        "release_highlights": tuple(str(item).strip() for item in highlights_value if str(item).strip()),
        "release_published_at": str(getattr(release, "published_at", "") or "").strip(),
        "release_tag": str(getattr(release, "tag", "") or "").strip(),
        "release_url": str(getattr(release, "html_url", "") or "").strip(),
    }


def _repo_root_guidance_source() -> str:
    return "\n".join(
        [
            "# Repo Guidance",
            "",
            "This file defines repo-root guidance for this workspace.",
            "",
            "## Working Rule",
            "- Keep repo-root guidance here for paths outside `odylith/`.",
            "- When Odylith is installed, work under `odylith/` follows `odylith/AGENTS.md` first.",
            "- If this folder is not backed by Git yet, Odylith still installs here, but Git-aware features stay limited until `.git` exists.",
            "",
        ]
    )


def _ensure_repo_root_agents_file(*, repo_root: Path) -> bool:
    path = Path(repo_root).resolve() / "AGENTS.md"
    if path.is_file():
        return False
    atomic_write_text(path, _repo_root_guidance_source(), encoding="utf-8")
    return True


def _pyproject_payload(*, repo_root: Path) -> dict[str, object]:
    path = repo_root / "pyproject.toml"
    if not path.is_file():
        return {}
    try:
        payload = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return {}
    return dict(payload) if isinstance(payload, dict) else {}


def product_source_version(*, repo_root: str | Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    payload = _pyproject_payload(repo_root=root)
    project = payload.get("project")
    if not isinstance(project, Mapping):
        return ""
    return str(project.get("version") or "").strip()


def product_repo_role(*, repo_root: str | Path) -> str:
    root = Path(repo_root).expanduser().resolve()
    payload = _pyproject_payload(repo_root=root)
    project = payload.get("project")
    project_name = str(project.get("name") or "").strip().lower() if isinstance(project, Mapping) else ""
    has_product_shape = (
        project_name == "odylith"
        and (root / "src" / "odylith").is_dir()
        and (root / "odylith" / "registry" / "source" / "component_registry.v1.json").is_file()
        and (root / "odylith" / "radar" / "source" / "INDEX.md").is_file()
    )
    return PRODUCT_REPO_ROLE if has_product_shape else CONSUMER_REPO_ROLE


def _customer_bootstrap_guidance() -> str:
    return "\n".join(
        [
            "# Odylith Repo Guidance",
            "",
            "Scope: applies to the local customer-owned `odylith/` tree in this repository.",
            "",
            "## Ownership",
            "- This starter tree is local repo truth, not a copy of the Odylith product repo.",
            "- `odylith/runtime/source/product-version.v1.json` pins the intended Odylith product version.",
            "- `odylith/runtime/source/tooling_shell.v1.json` is local repo shell metadata and stays customer-owned.",
            "- `.odylith/trust/managed-runtime-trust/` is local Odylith runtime trust state and may be refreshed by install, upgrade, feature-pack activation, or doctor.",
            "- `odylith/surfaces/brand/` is an Odylith-managed starter asset set for local HTML surfaces; first install and explicit repair may restore it, but normal upgrades should not rewrite it.",
            "- `odylith/AGENTS.md`, `odylith/agents-guidelines/`, and `odylith/skills/` are Odylith-managed guidance assets and may be refreshed by install, upgrade, or doctor.",
            "- Truth under `odylith/radar/`, `odylith/technical-plans/`, `odylith/casebook/`, `odylith/registry/`, and `odylith/atlas/` belongs to this repository and must not be rewritten by normal upgrades.",
            "- Product runtime code and product-managed assets run from `.odylith/` and the installed Odylith runtime package.",
            "- Do not treat this folder as disposable cache; it belongs to the repository using Odylith.",
            "",
            "## Working Rule",
            "- For work under `odylith/`, read this file first.",
            "- Use `./.odylith/bin/odylith` for Odylith CLI workflows in this repository.",
            "- Before any substantive repo scan or code change outside trivial fixes, the agent must start from the repo-local Odylith entrypoint and keep the active workstream, component, or packet in scope before raw repo search, tests, or edits.",
            "- Direct repo scan before that start step is a policy violation unless the task is trivial or Odylith is unavailable.",
            "- Start substantive turns with `./.odylith/bin/odylith start --repo-root .`; it chooses the safe first lane and prints the exact next command when Odylith cannot narrow the slice yet.",
            "- When you already know the exact workstream, component, path, or id, use `./.odylith/bin/odylith context --repo-root . <ref>` before raw repo search. Use `./.odylith/bin/odylith query --repo-root . \"<terms>\"` only after concrete anchors already exist.",
            "- In Codex commentary, keep startup, fallback, routing, and packet-selection internals implicit. Describe progress in task terms like the exact file/workstream, the bug under test, or the validation in flight. If an earlier repo-local start attempt degraded but work can continue safely, do not narrate that history. Do not surface routine `odylith start`, `odylith context`, or `odylith query` commands in progress updates, and never prefix commentary with control-plane receipt labels. Mention Odylith during the work only when the user explicitly asks for the command, a real blocker requires it, or a consumer-versus-maintainer lane distinction matters.",
            "- Keep normal commentary task-first and human. Weave Odylith-grounded facts into ordinary updates when they change the next move, and reserve explicit `Odylith Insight:`, `Odylith History:`, or `Odylith Risks:` labels for rare high-signal moments. Pick the strongest one or stay quiet.",
            "- At closeout, you may add at most one short `Odylith Assist:` line if it helps the user understand what Odylith materially contributed. Prefer `**Odylith Assist:**` when Markdown formatting is available; otherwise use `Odylith Assist:`. Lead with the user win, link updated governance ids inline when they were actually changed, and frame the edge against `odylith_off` or the broader unguided path when the evidence supports it. Keep it crisp, authentic, clear, simple, insightful, erudite in thought, soulful, friendly, free-flowing, human, and factual. Ground the line in concrete observed counts, measured deltas, or validation outcomes. Humor is fine only when the evidence makes it genuinely funny. Silence is better than filler. At most one supplemental closeout line may appear, chosen from `Odylith Risks:`, `Odylith Insight:`, or `Odylith History:` when the signal is real.",
            "- For substantive tasks, follow this workflow check in order: read the nearest `AGENTS.md`; run the repo-local `odylith start`/`odylith context` step; identify the active workstream, component, or packet; then move into repo scan, tests, and edits.",
            "- In consumer repos, grounding Odylith is diagnosis authority, not blanket write authority: if the issue target is Odylith itself, stop at diagnosis and maintainer-ready feedback unless the operator explicitly authorizes Odylith mutation.",
            "- Treat `odylith upgrade`, `odylith reinstall`, `odylith doctor --repair`, `odylith sync`, and `odylith dashboard refresh` as writes when they change `odylith/` or `.odylith/`; do not run them autonomously as Odylith fixes in consumer repos.",
            "- Treat backlog/workstream, plan, Registry, Atlas, Casebook, Compass, and session upkeep as part of the same grounded Odylith workflow rather than as optional aftercare, but switch to evidence-and-handoff when the issue is Odylith itself in a consumer repo.",
            "- Queued backlog items, case queues, and shell or Compass queue previews are not implicit implementation instructions. Unless the user explicitly asks to work a queued item, do not pick it up automatically just because it appears in Radar, Compass, the shell, or another Odylith queue surface.",
            "- Search existing workstream, plan, bug, component, diagram, and recent session/Compass context first; for consumer Odylith-fix requests, cite that evidence and hand it off to the platform maintainer instead of extending or creating Odylith truth locally.",
            "- If the slice is genuinely new and it is repo-owned non-product work, create the missing workstream and bound plan before non-trivial implementation; if the issue is Odylith itself in a consumer repo, produce a maintainer-ready feedback packet instead.",
            "- Use Odylith packets and managed skills to narrow the slice, gather proof, and keep intent plus constraints alive across turns, but do not treat grounding as permission to patch `odylith/` for consumer Odylith-fix requests.",
            "- In Codex, treat routed or orchestrated native spawn as the default execution path for substantive grounded consumer-lane work unless Odylith explicitly keeps the slice local.",
            "- In Claude Code, use Odylith grounding, memory, surfaces, and local orchestration guidance, but do not assume native spawn support.",
            "- Treat the managed guidance files under `odylith/AGENTS.md`, `odylith/agents-guidelines/`, and `odylith/skills/` as the Odylith operating layer; keep repo-specific truth in the governance surfaces beside them.",
            "",
            "## Routing",
            "- Context engine behavior: `agents-guidelines/ODYLITH_CONTEXT_ENGINE.md`",
            "- Grounding and narrowing: `agents-guidelines/GROUNDING_AND_NARROWING.md`",
            "- Governance and delivery surfaces: `agents-guidelines/DELIVERY_AND_GOVERNANCE_SURFACES.md`",
            "- Product surfaces and runtime: `agents-guidelines/PRODUCT_SURFACES_AND_RUNTIME.md`",
            "- Security and trust boundaries: `agents-guidelines/SECURITY_AND_TRUST.md`",
            "- Subagent routing and execution posture: `agents-guidelines/SUBAGENT_ROUTING_AND_ORCHESTRATION.md`",
            "- Validation and testing: `agents-guidelines/VALIDATION_AND_TESTING.md`",
            "- Install, upgrade, and recovery: `agents-guidelines/UPGRADE_AND_RECOVERY.md`",
            "",
            "## Skills",
            "- `skills/delivery-governance-surface-ops/`",
            "- `skills/odylith-context-engine-operations/`",
            "- `skills/subagent-router/`",
            "- `skills/subagent-orchestrator/`",
            "- `skills/session-context/`",
            "- `skills/component-registry/`",
            "- `skills/diagram-catalog/`",
            "- `skills/casebook-bug-capture/`",
            "- `skills/casebook-bug-investigation/`",
            "- `skills/casebook-bug-preflight/`",
            "- `skills/compass-executive/`",
            "- `skills/compass-timeline-stream/`",
            "- `skills/registry-spec-sync/`",
            "- `skills/schema-registry-governance/`",
            "- `skills/security-hardening/`",
            "",
            "## Consumer Boundary",
            "- Consumer installs intentionally exclude Odylith product-maintainer release workflow from the local repo guidance and skill set.",
            "- Use the installed Odylith guidance and skills to power repo work here; do not mirror the Odylith product repo release process into this repository.",
            "",
        ]
    )


def _customer_shell_source(*, repo_root: Path) -> str:
    payload = {
        "shell_repo_label": f"Repo · {repo_root.name}",
        "maintainer_notes": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _customer_shell_index_placeholder_source(*, repo_root: Path) -> str:
    repo_label = repo_root.name or "repository"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Odylith | {repo_label}</title>
    <style>
      :root {{
        color-scheme: light;
        font-family: "SF Pro Display", "Segoe UI", sans-serif;
        background:
          radial-gradient(circle at top right, rgba(125, 211, 252, 0.18), transparent 34%),
          linear-gradient(180deg, #f6fbff 0%, #eef5ff 100%);
        color: #17324d;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        display: grid;
        place-items: center;
        padding: 24px;
      }}

      main {{
        width: min(760px, 100%);
        display: grid;
        gap: 16px;
        padding: 28px;
        border: 1px solid #cfe0f7;
        border-radius: 28px;
        background: rgba(255, 255, 255, 0.94);
        box-shadow: 0 28px 64px rgba(22, 48, 82, 0.16);
      }}

      p {{
        margin: 0;
        line-height: 1.55;
      }}

      .eyebrow {{
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #1f5d7a;
      }}

      h1 {{
        margin: 0;
        font-size: clamp(32px, 5vw, 46px);
        line-height: 1;
        letter-spacing: -0.04em;
        max-width: 12ch;
      }}

      .lede {{
        max-width: 62ch;
        color: #35557e;
      }}

      .card {{
        display: grid;
        gap: 10px;
        padding: 16px 18px;
        border: 1px solid #d8e5f8;
        border-radius: 20px;
        background: #f8fbff;
      }}

      code {{
        display: inline-block;
        padding: 5px 8px;
        border-radius: 10px;
        background: #edf4ff;
        border: 1px solid #d4e4fb;
        color: #17324d;
        overflow-wrap: anywhere;
      }}
    </style>
  </head>
  <body>
    <main>
      <p class="eyebrow">Odylith</p>
      <h1>The local shell is getting ready.</h1>
      <p class="lede">
        Odylith already created the repo-owned <code>odylith/</code> workspace for this {repo_label}. If the full shell
        has not rendered yet, rerun <code>./.odylith/bin/odylith sync --repo-root . --force --impact-mode full</code>
        from the repo root.
      </p>
      <section class="card">
        <p><strong>Local shell entrypoint</strong></p>
        <p><code>odylith/index.html</code></p>
      </section>
    </main>
  </body>
</html>
"""


def _customer_backlog_index_source(*, repo_root: Path) -> str:
    updated = datetime.now(UTC).date().isoformat()
    return "\n".join(
        [
            "# Backlog Index",
            "",
            f"Last updated (UTC): {updated}",
            "",
            "## Ranked Active Backlog",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## In Planning/Implementation (Linked to `odylith/technical-plans/in-progress`)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Parked (No Active Plan)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Finished (Linked to `odylith/technical-plans/done`)",
            "",
            "| rank | idea_id | title | priority | ordering_score | commercial_value | product_impact | market_value | sizing | complexity | impacted_lanes | status | link |",
            "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
            "",
            "## Reorder Rationale Log",
            "",
        ]
    ) + "\n"


def _customer_plan_index_source() -> str:
    return "\n".join(
        [
            "# Plan Index",
            "",
            "## Active Plans",
            "",
            "| Plan | Status | Created | Updated | Backlog |",
            "| --- | --- | --- | --- | --- |",
            "",
            "## Parked Plans",
            "",
            "| Plan | Status | Created | Updated | Backlog |",
            "| --- | --- | --- | --- | --- |",
            "",
        ]
    ) + "\n"


def _customer_component_registry_source() -> str:
    payload = {
        "version": "v1",
        "components": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _customer_diagram_catalog_source() -> str:
    payload = {
        "version": "v1",
        "diagrams": [],
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _refresh_consumer_managed_guidance(*, repo_root: Path, repo_role: str, include_brand: bool, version: str = "") -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    atomic_write_text(repo_root / "odylith" / "AGENTS.md", _customer_bootstrap_guidance(), encoding="utf-8")
    _sync_managed_agents_guidelines(repo_root=repo_root)
    _sync_managed_skills(repo_root=repo_root)
    _sync_managed_release_notes(repo_root=repo_root, version=version)
    if include_brand:
        _sync_managed_surface_brand(repo_root=repo_root)


def _sync_consumer_casebook_bug_index(*, repo_root: Path, repo_role: str) -> None:
    if str(repo_role).strip() == PRODUCT_REPO_ROLE:
        return
    sync_casebook_bug_index.sync_casebook_bug_index(repo_root=repo_root, migrate_bug_ids=True)


def _ensure_customer_bootstrap(*, repo_root: Path, version: str, repo_role: str = CONSUMER_REPO_ROLE) -> None:
    directories = (
        repo_root / "odylith",
        repo_root / "odylith" / "runtime" / "source",
        repo_root / "odylith" / "runtime" / "source" / "release-notes",
        repo_root / "odylith" / "agents-guidelines",
        repo_root / "odylith" / "skills",
        repo_root / "odylith" / "surfaces" / "brand",
        repo_root / "odylith" / "radar" / "source",
        repo_root / "odylith" / "radar" / "source" / "ideas",
        repo_root / "odylith" / "technical-plans",
        repo_root / "odylith" / "technical-plans" / "in-progress",
        repo_root / "odylith" / "technical-plans" / "done",
        repo_root / "odylith" / "technical-plans" / "parked",
        repo_root / "odylith" / "casebook" / "bugs",
        repo_root / "odylith" / "registry" / "source" / "components",
        repo_root / "odylith" / "atlas" / "source",
        repo_root / "odylith" / "atlas" / "source" / "catalog",
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    _refresh_consumer_managed_guidance(
        repo_root=repo_root,
        repo_role=repo_role,
        include_brand=True,
        version=version,
    )
    shell_source_path = repo_root / "odylith" / "runtime" / "source" / "tooling_shell.v1.json"
    if not shell_source_path.exists():
        atomic_write_text(shell_source_path, _customer_shell_source(repo_root=repo_root), encoding="utf-8")
    shell_index_path = repo_root / "odylith" / "index.html"
    if not shell_index_path.exists():
        atomic_write_text(
            shell_index_path,
            _customer_shell_index_placeholder_source(repo_root=repo_root),
            encoding="utf-8",
        )
    backlog_index_path = repo_root / "odylith" / "radar" / "source" / "INDEX.md"
    if not backlog_index_path.exists():
        atomic_write_text(backlog_index_path, _customer_backlog_index_source(repo_root=repo_root), encoding="utf-8")
    plan_index_path = repo_root / "odylith" / "technical-plans" / "INDEX.md"
    if not plan_index_path.exists():
        atomic_write_text(plan_index_path, _customer_plan_index_source(), encoding="utf-8")
    component_registry_path = repo_root / "odylith" / "registry" / "source" / "component_registry.v1.json"
    if not component_registry_path.exists():
        atomic_write_text(component_registry_path, _customer_component_registry_source(), encoding="utf-8")
    diagram_catalog_path = repo_root / "odylith" / "atlas" / "source" / "catalog" / "diagrams.v1.json"
    if not diagram_catalog_path.exists():
        atomic_write_text(diagram_catalog_path, _customer_diagram_catalog_source(), encoding="utf-8")
    if not version_pin_path(repo_root=repo_root).is_file():
        write_version_pin(repo_root=repo_root, version=version, repo_schema_version=DEFAULT_REPO_SCHEMA_VERSION)


def _sync_managed_agents_guidelines(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "agents-guidelines"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "agents-guidelines"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _sync_managed_skills(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "skills"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "skills"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _sync_managed_surface_brand(*, repo_root: Path) -> None:
    source_root = bundled_product_root() / "surfaces" / "brand"
    if not source_root.is_dir():
        return
    target_root = repo_root / "odylith" / "surfaces" / "brand"
    target_root.mkdir(parents=True, exist_ok=True)
    for source_path in source_root.rglob("*"):
        if not source_path.is_file() or source_path.name == ".DS_Store":
            continue
        target_path = target_root / source_path.relative_to(source_root)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_path)


def _sync_managed_release_notes(*, repo_root: Path, version: str = "") -> None:
    source_root = bundled_product_root() / "runtime" / "source" / "release-notes"
    target_root = repo_root / "odylith" / "runtime" / "source" / "release-notes"
    target_root.mkdir(parents=True, exist_ok=True)
    for candidate in target_root.iterdir():
        if candidate.is_symlink() or candidate.is_file():
            candidate.unlink()
        elif candidate.is_dir():
            shutil.rmtree(candidate)
    if not source_root.is_dir():
        return
    normalized_version = str(version or "").strip().lstrip("v")
    if not normalized_version:
        return
    source_path = source_root / f"v{normalized_version}.md"
    if not source_path.is_file() or source_path.name == ".DS_Store":
        return
    shutil.copy2(source_path, target_root / source_path.name)


def _has_customer_starter_tree(*, repo_root: Path) -> bool:
    odylith_root = repo_root / "odylith"
    return odylith_root.is_dir() and (odylith_root / "AGENTS.md").is_file()


def _runtime_python(runtime_root: Path | None) -> Path | None:
    if runtime_root is None:
        return None
    candidate = runtime_root / "bin" / "python"
    return candidate if candidate.is_file() else None


def _is_source_local_version(version: str) -> bool:
    return str(version or "").strip().lower() == "source-local"


def _effective_detached(*, state: Mapping[str, object], active_version: str) -> bool:
    if _is_source_local_version(active_version):
        return True
    installed_versions_payload = state.get("installed_versions")
    if isinstance(installed_versions_payload, Mapping):
        entry = installed_versions_payload.get(active_version)
        if isinstance(entry, Mapping):
            verification = entry.get("verification")
            if isinstance(verification, Mapping) and str(verification.get("mode") or "").strip().lower() == "source-local":
                return True
    return bool(state.get("detached")) and not install_integration_enabled(state)


def _preferred_bootstrap_version(*, repo_root: Path, state: Mapping[str, object], active_version: str) -> str:
    pin = load_version_pin(repo_root=repo_root, fallback_version=None)
    candidates: list[str] = []
    if pin is not None:
        candidates.append(pin.odylith_version)
    candidates.append(str(state.get("last_known_good_version") or "").strip())
    candidates.extend(reversed(current_activation_history(state)))
    installed_versions_payload = state.get("installed_versions")
    if isinstance(installed_versions_payload, Mapping):
        candidates.extend(str(version).strip() for version in installed_versions_payload)
    candidates.append(str(active_version or "").strip())
    candidates.append(__version__)
    for candidate in candidates:
        token = str(candidate or "").strip()
        if token and not _is_source_local_version(token):
            return token
    return __version__


def _effective_last_known_good(*, state: Mapping[str, object], active_version: str) -> str:
    candidates: list[str] = [str(state.get("last_known_good_version") or "").strip()]
    candidates.extend(reversed(current_activation_history(state)))
    installed_versions_payload = state.get("installed_versions")
    if isinstance(installed_versions_payload, Mapping):
        candidates.extend(str(version).strip() for version in installed_versions_payload)
    candidates.append(str(active_version or "").strip())
    for candidate in candidates:
        token = str(candidate or "").strip()
        if token and not _is_source_local_version(token):
            return token
    return str(active_version or "").strip()


def _observed_active_version(*, repo_root: Path, state: Mapping[str, object], fallback: str = "") -> str:
    runtime_version = str(current_runtime_version(repo_root=repo_root) or "").strip()
    if runtime_version:
        return runtime_version
    state_version = str(state.get("active_version") or "").strip()
    if state_version:
        return state_version
    return str(fallback or "").strip()


def _run_odylith_smoke(*, python: Path, repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(python), "-I", "-m", "odylith.cli", "version", "--repo-root", str(repo_root)],
        check=False,
        capture_output=True,
        text=True,
        env=scrubbed_python_env(),
    )


def _runtime_source(
    *,
    active_version: str,
    pinned_version: str,
    runtime_root: Path | None,
    verification: Mapping[str, object] | None,
) -> str:
    if runtime_root is None:
        return INSTALL_STATE_ONLY_RUNTIME_SOURCE if active_version else MISSING_RUNTIME_SOURCE
    if _is_source_local_version(active_version):
        return SOURCE_CHECKOUT_RUNTIME_SOURCE
    verified_runtime = bool(verification)
    if active_version and pinned_version and active_version == pinned_version and verified_runtime:
        return PINNED_RUNTIME_SOURCE
    if active_version and verified_runtime:
        return VERIFIED_RUNTIME_SOURCE
    if active_version:
        return WRAPPED_RUNTIME_SOURCE
    return MISSING_RUNTIME_SOURCE


def _self_host_posture(
    *,
    active_version: str,
    pinned_version: str,
    runtime_root: Path | None,
) -> str:
    if runtime_root is None or not active_version:
        return UNINSTALLED_OR_INCOMPLETE_POSTURE
    if _is_source_local_version(active_version):
        return DETACHED_SOURCE_LOCAL_POSTURE
    if pinned_version and active_version != pinned_version:
        return DIVERGED_VERIFIED_VERSION_POSTURE
    return PINNED_RELEASE_POSTURE


def _consumer_lane_violation_reason(
    *,
    repo_role: str,
    posture: str,
    runtime_source: str,
) -> str:
    if repo_role == PRODUCT_REPO_ROLE:
        return ""
    if posture == DETACHED_SOURCE_LOCAL_POSTURE or runtime_source == SOURCE_CHECKOUT_RUNTIME_SOURCE:
        return (
            "Consumer repos cannot activate the detached source-local maintainer lane; "
            "run `odylith doctor --repo-root . --repair` to restage the pinned release."
        )
    return ""


def _release_eligible(
    *,
    repo_root: Path,
    repo_role: str,
    posture: str,
    pin: Any,
    runtime_source: str,
) -> bool | None:
    if repo_role != PRODUCT_REPO_ROLE:
        return None
    if pin is None:
        return False
    pinned_version = str(pin.odylith_version or "").strip()
    if not pinned_version or _is_source_local_version(pinned_version) or bool(pin.migration_required):
        return False
    source_version = product_source_version(repo_root=repo_root)
    if not source_version or source_version != pinned_version or __version__ != pinned_version:
        return False
    return posture == PINNED_RELEASE_POSTURE and runtime_source == PINNED_RUNTIME_SOURCE


def _installed_version_verification(*, state: Mapping[str, object], active_version: str) -> dict[str, object]:
    if not active_version:
        return {}
    installed_versions_payload = state.get("installed_versions")
    if not isinstance(installed_versions_payload, Mapping):
        return {}
    entry = installed_versions_payload.get(active_version)
    if not isinstance(entry, Mapping):
        return {}
    verification = entry.get("verification")
    if not isinstance(verification, Mapping):
        return {}
    return {str(key): value for key, value in verification.items()}


def _append_self_host_timeline_event(
    *,
    repo_root: Path,
    summary: str,
    artifacts: Sequence[str],
) -> None:
    if product_repo_role(repo_root=repo_root) != PRODUCT_REPO_ROLE:
        return
    try:
        from odylith.runtime.common import log_compass_timeline_event as timeline_logger

        timeline_logger.append_event(
            repo_root=repo_root,
            stream_path=repo_root / "odylith" / "compass" / "runtime" / "codex-stream.v1.jsonl",
            kind="statement",
            summary=summary,
            workstream_values=[],
            artifact_values=list(artifacts),
            component_values=["odylith", "compass", "dashboard"],
            author="odylith",
            source="odylith.self_host",
        )
    except Exception:
        return


def _register_installed_version(
    *,
    state: Mapping[str, object],
    version: str,
    runtime_root: Path | None,
    verification: Mapping[str, object] | None,
) -> dict[str, object]:
    normalized = dict(state)
    installed_versions_payload = normalized.get("installed_versions")
    installed_versions = dict(installed_versions_payload) if isinstance(installed_versions_payload, Mapping) else {}
    entry_payload = installed_versions.get(version)
    entry = dict(entry_payload) if isinstance(entry_payload, Mapping) else {}
    entry["installed_utc"] = datetime.now(UTC).isoformat()
    if runtime_root is not None:
        entry["runtime_root"] = str(runtime_root)
    if verification:
        entry["verification"] = dict(verification)
    else:
        entry.setdefault("verification", {})
    installed_versions[version] = entry
    normalized["installed_versions"] = installed_versions
    return normalized


def _register_installed_feature_packs(
    *,
    state: Mapping[str, object],
    version: str,
    feature_packs: Mapping[str, object] | None,
) -> dict[str, object]:
    normalized = dict(state)
    installed_versions_payload = normalized.get("installed_versions")
    installed_versions = dict(installed_versions_payload) if isinstance(installed_versions_payload, Mapping) else {}
    entry_payload = installed_versions.get(version)
    entry = dict(entry_payload) if isinstance(entry_payload, Mapping) else {}
    entry["feature_packs"] = dict(feature_packs) if isinstance(feature_packs, Mapping) else {}
    installed_versions[version] = entry
    normalized["installed_versions"] = installed_versions
    return normalized


def _retained_version_pair(*, state: Mapping[str, object], active_version: str) -> tuple[str, str]:
    rollback_target = ""
    for candidate in reversed(current_activation_history(state)[:-1]):
        if candidate and candidate != active_version:
            rollback_target = candidate
            break
    return active_version, rollback_target


def _prune_runtime_retention(
    *,
    repo_root: Path,
    state: Mapping[str, object],
    active_version: str,
) -> dict[str, object]:
    if not active_version or _is_source_local_version(active_version):
        return dict(state)

    keep_active, keep_rollback = _retained_version_pair(state=state, active_version=active_version)
    keep_versions = {keep_active}
    if keep_rollback:
        keep_versions.add(keep_rollback)

    paths = repo_root / ".odylith" / "runtime" / "versions"
    if paths.is_dir():
        for candidate in paths.iterdir():
            if candidate.name in keep_versions:
                continue
            if candidate.is_symlink() or candidate.is_file():
                candidate.unlink()
            elif candidate.is_dir():
                shutil.rmtree(candidate)

    releases_cache_root = repo_root / ".odylith" / "cache" / "releases"
    if releases_cache_root.is_dir():
        for candidate in releases_cache_root.iterdir():
            if candidate.name in keep_versions:
                continue
            if candidate.is_symlink() or candidate.is_file():
                candidate.unlink()
            elif candidate.is_dir():
                shutil.rmtree(candidate)

    normalized = dict(state)
    installed_versions_payload = normalized.get("installed_versions")
    installed_versions = dict(installed_versions_payload) if isinstance(installed_versions_payload, Mapping) else {}
    normalized["installed_versions"] = {
        version: dict(entry)
        for version, entry in installed_versions.items()
        if version in keep_versions and isinstance(entry, Mapping)
    }
    history = []
    if keep_rollback:
        history.append(keep_rollback)
    history.append(keep_active)
    normalized["activation_history"] = history
    return normalized


def _runtime_context_engine_state(*, runtime_root: Path | None, runtime_source: str) -> tuple[str, bool | None]:
    if runtime_root is not None and (runtime_root / "runtime-metadata.json").is_file():
        installed = runtime_context_engine_feature_pack_installed(runtime_root)
        return ("full_local_memory" if installed else "base_fallback", installed)
    ready = odylith_memory_backend.backend_dependencies_available()
    if runtime_source in {SOURCE_CHECKOUT_RUNTIME_SOURCE, WRAPPED_RUNTIME_SOURCE}:
        return ("full_local_memory" if ready else "base_fallback", None)
    return ("base_fallback", None)


def _target_feature_pack_details(*, manifest: Mapping[str, object], runtime_root: Path, pack_id: str) -> tuple[str, str] | None:
    metadata = runtime_root / "runtime-metadata.json"
    if not metadata.is_file():
        return None
    try:
        payload = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, Mapping):
        return None
    platform_slug = str(payload.get("platform") or "").strip()
    if not platform_slug:
        return None
    feature_packs = manifest.get("feature_packs")
    if not isinstance(feature_packs, Mapping):
        return None
    pack_details = feature_packs.get(pack_id)
    if not isinstance(pack_details, Mapping):
        return None
    assets_by_platform = pack_details.get("assets")
    if not isinstance(assets_by_platform, Mapping):
        return None
    asset_name = str(assets_by_platform.get(platform_slug) or "").strip()
    if not asset_name:
        return None
    asset_manifest = manifest.get("assets")
    if not isinstance(asset_manifest, Mapping):
        return None
    asset_details = asset_manifest.get(asset_name)
    if not isinstance(asset_details, Mapping):
        return None
    asset_sha256 = str(asset_details.get("sha256") or "").strip()
    if not asset_sha256:
        return None
    return asset_name, asset_sha256


def _validated_runtime_relative_path(*, runtime_root: Path, relative_path: str) -> Path | None:
    token = str(relative_path or "").strip()
    if not token:
        return None
    relative = PurePosixPath(token)
    if relative.is_absolute():
        return None
    parts = tuple(part for part in relative.parts if part not in ("", "."))
    if not parts or any(part == ".." for part in parts):
        return None
    candidate = runtime_root.joinpath(*parts)
    try:
        candidate.relative_to(runtime_root)
    except ValueError:
        return None
    return candidate


def _runtime_symlink_target_is_safe(*, runtime_root: Path, source_path: Path) -> bool:
    if not source_path.is_symlink():
        return True
    try:
        link_target = os.readlink(source_path)
    except OSError:
        return False
    target = PurePosixPath(link_target)
    if target.is_absolute():
        return False
    source_relative = PurePosixPath(source_path.relative_to(runtime_root).as_posix())
    stack: list[str] = []
    for part in (*source_relative.parent.parts, *target.parts):
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                return False
            stack.pop()
            continue
        stack.append(part)
    return True


def _reuse_context_engine_feature_pack_from_previous_runtime(
    *,
    repo_root: Path,
    previous_runtime: Path | None,
    target_runtime: Path,
    target_version: str,
    manifest: Mapping[str, object],
) -> bool:
    if previous_runtime is None or not previous_runtime.is_dir():
        return False
    target_details = _target_feature_pack_details(
        manifest=manifest,
        runtime_root=target_runtime,
        pack_id=CONTEXT_ENGINE_FEATURE_PACK_ID,
    )
    if target_details is None:
        return False
    target_asset_name, target_asset_sha256 = target_details
    previous_feature_packs = load_runtime_feature_packs(previous_runtime)
    previous_pack = previous_feature_packs.get(CONTEXT_ENGINE_FEATURE_PACK_ID)
    if not isinstance(previous_pack, Mapping):
        return False
    previous_verification = previous_pack.get("verification")
    previous_paths = previous_pack.get("paths")
    if not isinstance(previous_verification, Mapping) or not isinstance(previous_paths, list):
        return False
    if str(previous_pack.get("asset_name") or "").strip() != target_asset_name:
        return False
    if str(previous_verification.get("feature_pack_sha256") or "").strip() != target_asset_sha256:
        return False

    for relative_path in previous_paths:
        relative = str(relative_path or "").strip()
        if not relative:
            continue
        source_path = _validated_runtime_relative_path(runtime_root=previous_runtime, relative_path=relative)
        destination_path = _validated_runtime_relative_path(runtime_root=target_runtime, relative_path=relative)
        if source_path is None or destination_path is None:
            return False
        if not source_path.exists() and not source_path.is_symlink():
            return False
        if not _runtime_symlink_target_is_safe(runtime_root=previous_runtime, source_path=source_path):
            return False
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.exists() or destination_path.is_symlink():
            if destination_path.is_dir() and not destination_path.is_symlink():
                shutil.rmtree(destination_path)
            else:
                destination_path.unlink()
        if source_path.is_symlink():
            os.symlink(os.readlink(source_path), destination_path)
        elif source_path.is_dir():
            shutil.copytree(source_path, destination_path)
        else:
            shutil.copy2(source_path, destination_path)

    target_feature_packs = load_runtime_feature_packs(target_runtime)
    target_feature_packs[CONTEXT_ENGINE_FEATURE_PACK_ID] = {
        **dict(previous_pack),
        "installed_utc": datetime.now(UTC).isoformat(),
        "verification": dict(previous_verification),
    }
    target_feature_packs[CONTEXT_ENGINE_FEATURE_PACK_ID]["asset_name"] = target_asset_name
    target_feature_packs[CONTEXT_ENGINE_FEATURE_PACK_ID]["verification"]["feature_pack_sha256"] = target_asset_sha256
    target_feature_packs[CONTEXT_ENGINE_FEATURE_PACK_ID]["version"] = target_version
    runtime_feature_packs_path = target_runtime / MANAGED_RUNTIME_FEATURE_PACK_FILENAME
    atomic_write_text(
        runtime_feature_packs_path,
        json.dumps(
            {
                "schema_version": MANAGED_RUNTIME_FEATURE_PACK_SCHEMA_VERSION,
                "version": target_version,
                "packs": target_feature_packs,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    write_managed_runtime_trust(
        repo_root=repo_root,
        version_root=target_runtime,
        verification=runtime_verification_evidence(target_runtime),
    )
    return True


def _persist_runtime_state(
    *,
    repo_root: Path,
    state: Mapping[str, object],
    active_version: str,
    launcher_path: Path,
    consumer_profile: Path,
    runtime_root: Path | None,
    verification: Mapping[str, object] | None,
    detached: bool,
    integration_enabled: bool,
    mark_last_known_good: bool = True,
) -> dict[str, object]:
    normalized = _register_installed_version(
        state=state,
        version=active_version,
        runtime_root=runtime_root,
        verification=verification,
    )
    normalized = _register_installed_feature_packs(
        state=normalized,
        version=active_version,
        feature_packs=load_runtime_feature_packs(runtime_root) if runtime_root is not None else {},
    )
    normalized = record_activation(
        state=normalized,
        version=active_version,
        mark_last_known_good=mark_last_known_good,
    )
    normalized["consumer_profile_path"] = str(consumer_profile)
    normalized["detached"] = bool(detached)
    normalized["installed_utc"] = datetime.now(UTC).isoformat()
    normalized["integration_enabled"] = bool(integration_enabled)
    normalized["launcher_path"] = str(launcher_path)
    normalized = _prune_runtime_retention(
        repo_root=repo_root,
        state=normalized,
        active_version=active_version,
    )
    write_install_state(repo_root=repo_root, payload=normalized)
    return normalized


def _version_sort_key(version: str) -> tuple[int, int, int, str]:
    token = str(version or "").strip()
    match = _SEMVER_RE.match(token)
    if match is None:
        return (-1, -1, -1, token)
    return (
        int(match.group("major")),
        int(match.group("minor")),
        int(match.group("patch")),
        str(match.group("suffix") or ""),
    )


def _is_downgrade(*, candidate: str, baseline: str) -> bool:
    if not candidate or not baseline:
        return False
    return _version_sort_key(candidate) < _version_sort_key(baseline)


def _discard_versions_newer_than(
    *,
    state: Mapping[str, object],
    ceiling_version: str,
) -> dict[str, object]:
    normalized = dict(state)
    ceiling = str(ceiling_version or "").strip()
    if not ceiling:
        return normalized

    installed_versions_payload = normalized.get("installed_versions")
    if isinstance(installed_versions_payload, Mapping):
        normalized["installed_versions"] = {
            str(version).strip(): dict(entry)
            for version, entry in installed_versions_payload.items()
            if (
                str(version).strip()
                and not _is_downgrade(candidate=ceiling, baseline=str(version).strip())
                and isinstance(entry, Mapping)
            )
        }

    normalized["activation_history"] = [
        version
        for version in current_activation_history(normalized)
        if not _is_downgrade(candidate=ceiling, baseline=version)
    ]
    return normalized


def _ensure_managed_context_engine_pack(
    *,
    repo_root: Path,
    version: str,
    runtime_root: Path | None = None,
    release_repo: str = AUTHORITATIVE_RELEASE_REPO,
) -> dict[str, object]:
    target_root = runtime_root or runtime_root_for_version(repo_root=repo_root, version=version)
    if not target_root.is_dir() or not (target_root / "runtime-metadata.json").is_file():
        return {}
    staged = install_release_feature_pack(
        repo_root=repo_root,
        repo=release_repo,
        version=version,
        runtime_root=target_root,
    )
    state = load_install_state(repo_root=repo_root)
    updated_state = _register_installed_feature_packs(
        state=state,
        version=version,
        feature_packs=load_runtime_feature_packs(target_root),
    )
    write_install_state(repo_root=repo_root, payload=updated_state)
    append_install_ledger(
        repo_root=repo_root,
        payload={
            "operation": "feature-pack",
            "status": "activated",
            "active_version": version,
            "pack_id": staged.pack_id,
            "asset_name": staged.asset_name,
        },
    )
    return dict(staged.verification)


def migrate_legacy_install(*, repo_root: str | Path) -> MigrationSummary:
    root = _repo_root(repo_root, require_agents=False)
    old_product_root = root / "odyssey"
    old_state_root = root / ".odyssey"
    new_product_root = root / "odylith"
    new_state_root = root / ".odylith"

    if _legacy_operation_in_progress(repo_root=root):
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
    _rewrite_legacy_gitignore_entries(repo_root=root)
    _ensure_odylith_gitignore_entry(repo_root=root)
    normalize_legacy_backlog_index(repo_root=root)
    stale_reference_audit = audit_legacy_odyssey_references(repo_root=root)

    repo_role = product_repo_role(repo_root=root)
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
    update_agents_file(
        root / "AGENTS.md",
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


def install_bundle(*, repo_root: str | Path, bundle_root: Path, version: str | None = None) -> InstallSummary:
    del bundle_root
    root = _repo_root(repo_root, require_agents=False)
    migration = _migrate_legacy_install_if_needed(repo_root=root)
    with install_lock(repo_root=root):
        repo_guidance_created = _ensure_repo_root_agents_file(repo_root=root)
        git_repo_present = _git_repo_present(repo_root=root)
        gitignore_updated = _ensure_odylith_gitignore_entry(repo_root=root, git_repo_present=git_repo_present)
        previous_state = load_install_state(repo_root=root)
        integration_enabled = install_integration_enabled(previous_state)
        resolved_version = str(version or previous_state.get("active_version") or __version__).strip() or __version__
        repo_role = product_repo_role(repo_root=root)
        _ensure_customer_bootstrap(repo_root=root, version=resolved_version, repo_role=repo_role)
        written_profile = write_consumer_profile(repo_root=root)
        update_agents_file(root / "AGENTS.md", install_active=integration_enabled, repo_role=repo_role)
        existing_runtime = current_runtime_root(repo_root=root)
        existing_version = current_runtime_version(repo_root=root)
        runtime_verification: dict[str, object] = (
            runtime_verification_evidence(existing_runtime) if existing_runtime is not None else {}
        )
        launcher_path: Path | None = None
        if existing_runtime is None or _is_source_local_version(existing_version):
            if repo_role == PRODUCT_REPO_ROLE:
                existing_runtime = ensure_wrapped_runtime(
                    repo_root=root,
                    version=resolved_version,
                    fallback_python=Path(sys.executable),
                    allow_host_python_fallback=True,
                )
                runtime_verification = runtime_verification_evidence(existing_runtime)
            else:
                previous_runtime = current_runtime_root(repo_root=root)
                previous_python = _runtime_python(previous_runtime)
                staged = install_release_runtime(
                    repo_root=root,
                    repo=AUTHORITATIVE_RELEASE_REPO,
                    version=resolved_version,
                    activate=False,
                )
                existing_runtime = staged.root
                runtime_verification = dict(staged.verification)
                _ensure_managed_context_engine_pack(
                    repo_root=root,
                    version=staged.version,
                    runtime_root=staged.root,
                    release_repo=AUTHORITATIVE_RELEASE_REPO,
                )
                launcher_path = ensure_launcher(
                    repo_root=root,
                    fallback_python=staged.python,
                )
                switch_runtime(repo_root=root, target=staged.root)
                smoke = _run_odylith_smoke(python=staged.python, repo_root=root)
                if smoke.returncode != 0:
                    if previous_runtime is not None:
                        switch_runtime(repo_root=root, target=previous_runtime)
                        if previous_python is not None:
                            launcher_path = ensure_launcher(repo_root=root, fallback_python=previous_python)
                    else:
                        clear_runtime_activation(repo_root=root, clear_launcher=True)
                    append_install_ledger(
                        repo_root=root,
                        payload={
                            "operation": "install",
                            "status": "failed",
                            "target_version": staged.version,
                            "stderr": smoke.stderr.strip(),
                            "stdout": smoke.stdout.strip(),
                        },
                    )
                    raise RuntimeError(
                        f"post-activation smoke check failed for {staged.version}: {(smoke.stderr or smoke.stdout).strip()}"
                    )
        runtime_root = current_runtime_root(repo_root=root) or existing_runtime
        if (
            repo_role != PRODUCT_REPO_ROLE
            and runtime_root is not None
            and (runtime_root / "runtime-metadata.json").is_file()
            and not runtime_context_engine_feature_pack_installed(runtime_root)
        ):
            _ensure_managed_context_engine_pack(
                repo_root=root,
                version=current_runtime_version(repo_root=root) or resolved_version,
                runtime_root=runtime_root,
                release_repo=AUTHORITATIVE_RELEASE_REPO,
            )
        fallback_python = _runtime_python(runtime_root)
        if fallback_python is None:
            if repo_role != PRODUCT_REPO_ROLE:
                raise ValueError("consumer install must activate a verified Odylith-managed runtime before creating the launcher")
            fallback_python = Path(sys.executable)
        if launcher_path is None:
            launcher_path = ensure_launcher(
                repo_root=root,
                fallback_python=fallback_python,
                allow_host_python_fallback=repo_role == PRODUCT_REPO_ROLE,
            )
        active_version = current_runtime_version(repo_root=root) or resolved_version
        if runtime_root is not None and not runtime_verification:
            runtime_verification = runtime_verification_evidence(runtime_root)
        _persist_runtime_state(
            repo_root=root,
            state=previous_state,
            active_version=active_version,
            launcher_path=launcher_path,
            consumer_profile=written_profile,
            runtime_root=runtime_root,
            verification=runtime_verification,
            detached=False,
            integration_enabled=integration_enabled,
        )
        _refresh_consumer_managed_guidance(
            repo_root=root,
            repo_role=repo_role,
            include_brand=False,
            version=active_version,
        )
        append_install_ledger(
            repo_root=root,
            payload={
                "operation": "install",
                "status": "ready",
                "active_version": active_version,
                "pinned_version": str(load_version_pin(repo_root=root, fallback_version=active_version).odylith_version),
            },
        )
        _append_self_host_timeline_event(
            repo_root=root,
            summary=f"Prepared Odylith self-host runtime {active_version or 'unknown'} in the current repository.",
            artifacts=[
                "odylith/runtime/source/product-version.v1.json",
                ".odylith/install.json",
            ],
        )
        return InstallSummary(
            repo_root=root,
            version=active_version,
            odylith_root=root / "odylith",
            state_root=root / ".odylith",
            launcher_path=launcher_path,
            consumer_profile_path=written_profile,
            agents_updated=True,
            git_repo_present=git_repo_present,
            repo_guidance_created=repo_guidance_created,
            gitignore_updated=gitignore_updated,
            migration=migration,
        )


def upgrade_install(
    *,
    repo_root: str | Path,
    release_repo: str,
    version: str = "",
    source_repo: str | Path | None = None,
    write_pin: bool = False,
) -> UpgradeSummary:
    root = _repo_root(repo_root)
    migration = _migrate_legacy_install_if_needed(repo_root=root)
    _ensure_odylith_gitignore_entry(repo_root=root)
    requested_version = str(version or "").strip()
    repo_role = product_repo_role(repo_root=root)
    auto_follow_latest = repo_role != PRODUCT_REPO_ROLE and not requested_version and not source_repo
    effective_write_pin = bool(write_pin or auto_follow_latest)
    with install_lock(repo_root=root):
        previous_state = load_install_state(repo_root=root)
        current_version = _observed_active_version(repo_root=root, state=previous_state)
        if not _has_customer_starter_tree(repo_root=root):
            raise ValueError("customer Odylith starter tree missing; run `odylith install --repo-root .` or `odylith doctor --repo-root . --repair`")
        written_profile = write_consumer_profile(repo_root=root)
        integration_enabled = install_integration_enabled(previous_state)
        update_agents_file(root / "AGENTS.md", install_active=integration_enabled, repo_role=repo_role)
        _refresh_consumer_managed_guidance(
            repo_root=root,
            repo_role=repo_role,
            include_brand=False,
            version=_preferred_bootstrap_version(
                repo_root=root,
                state=previous_state,
                active_version=current_version,
            ),
        )

        if source_repo:
            if repo_role != PRODUCT_REPO_ROLE:
                raise ValueError("--source-repo is only supported for the Odylith product repo self-host dev lane")
            if write_pin:
                raise ValueError("--write-pin is not supported with --source-repo")
            if requested_version:
                raise ValueError("--to is not supported with --source-repo; source checkouts always activate as source-local detached mode")
            source_root = Path(source_repo).expanduser().resolve()
            if not (source_root / "pyproject.toml").is_file() or not (source_root / "src" / "odylith").is_dir():
                raise ValueError(f"source repo is not a valid Odylith checkout: {source_root}")
            ensure_source_runtime(repo_root=root, fallback_python=Path(sys.executable), source_root=source_root)
            runtime_root = current_runtime_root(repo_root=root)
            launcher_path = ensure_launcher(
                repo_root=root,
                fallback_python=Path(sys.executable),
                fallback_source_root=source_root,
                allow_host_python_fallback=True,
            )
            active_version = "source-local"
            _persist_runtime_state(
                repo_root=root,
                state=previous_state,
                active_version=active_version,
                launcher_path=launcher_path,
                consumer_profile=written_profile,
                runtime_root=runtime_root,
                verification={"mode": "source-local"},
                detached=True,
                integration_enabled=integration_enabled,
                mark_last_known_good=False,
            )
            append_install_ledger(
                repo_root=root,
                payload={
                    "operation": "upgrade",
                    "status": "activated",
                    "active_version": active_version,
                    "pinned_version": str(load_version_pin(repo_root=root, fallback_version=active_version).odylith_version),
                    "previous_version": current_version,
                    "verification": {"mode": "source-local"},
                },
            )
            _append_self_host_timeline_event(
                repo_root=root,
                summary=(
                    "Switched the Odylith product repo into detached source-local self-host mode; "
                    "release gating stays blocked until the active runtime returns to the repo pin."
                ),
                artifacts=[
                    "odylith/runtime/source/product-version.v1.json",
                    ".odylith/install.json",
                ],
            )
            pin = load_version_pin(repo_root=root, fallback_version=active_version)
            return UpgradeSummary(
                active_version=active_version,
                launcher_path=launcher_path,
                pin_changed=False,
                pinned_version=pin.odylith_version if pin else "",
                previous_version=current_version,
                repo_root=root,
                repo_role=repo_role,
                followed_latest=False,
                release_body="",
                release_highlights=(),
                release_published_at="",
                release_tag="",
                release_url="",
                verification={"mode": "source-local"},
                migration=migration,
            )

        pin_path_exists = version_pin_path(repo_root=root).is_file()
        pin = load_version_pin(repo_root=root, fallback_version=None if not pin_path_exists else current_version or __version__)
        if not pin_path_exists and not write_pin:
            raise ValueError(
                "repo pin missing; run `odylith install --repo-root .`, `odylith doctor --repo-root . --repair`, or use `odylith upgrade --to X.Y.Z --write-pin`"
            )
        request_token = requested_version or ("latest" if auto_follow_latest else (pin.odylith_version if pin else "latest"))
        if requested_version and pin is not None and requested_version != pin.odylith_version and not write_pin:
            raise ValueError("explicit target differs from the repo pin; use --write-pin to adopt a new pinned version")

        resolved_release = fetch_release(repo_root=root, repo=release_repo, version=request_token)
        install_version = resolved_release.version if request_token == "latest" else request_token
        if current_version and resolved_release.version == current_version and not _is_source_local_version(current_version):
            current_runtime = current_runtime_root(repo_root=root)
            current_python = _runtime_python(current_runtime)
            current_verification = runtime_verification_evidence(current_runtime) if current_runtime is not None else {}
            if current_runtime is None or current_python is None or not current_verification:
                raise ValueError(
                    f"active Odylith runtime already targets {current_version}, but it is not in a reusable verified state; "
                    "run `odylith doctor --repo-root . --repair` to restage it safely"
                )
            if (current_runtime / "runtime-metadata.json").is_file() and not runtime_context_engine_feature_pack_installed(current_runtime):
                raise ValueError(
                    f"active Odylith runtime already targets {current_version}, but the full-stack context-engine pack is missing; "
                    "run `odylith doctor --repo-root . --repair` to restage it safely"
                )
            smoke = _run_odylith_smoke(python=current_python, repo_root=root)
            if smoke.returncode != 0:
                raise RuntimeError(
                    f"active runtime smoke check failed for {current_version}: {(smoke.stderr or smoke.stdout).strip()}"
                )
            pin_changed = False
            if effective_write_pin and (pin is None or pin.odylith_version != current_version):
                write_version_pin(
                    repo_root=root,
                    version=current_version,
                    repo_schema_version=pin.repo_schema_version if pin is not None else DEFAULT_REPO_SCHEMA_VERSION,
                    migration_required=False,
                )
                pin_changed = True
                pin = load_version_pin(repo_root=root, fallback_version=current_version)
            launcher_path = ensure_launcher(repo_root=root, fallback_python=current_python)
            _persist_runtime_state(
                repo_root=root,
                state=previous_state,
                active_version=current_version,
                launcher_path=launcher_path,
                consumer_profile=written_profile,
                runtime_root=current_runtime,
                verification=current_verification,
                detached=False,
                integration_enabled=integration_enabled,
            )
            _refresh_consumer_managed_guidance(
                repo_root=root,
                repo_role=repo_role,
                include_brand=False,
                version=current_version,
            )
            _sync_consumer_casebook_bug_index(repo_root=root, repo_role=repo_role)
            append_install_ledger(
                repo_root=root,
                payload={
                    "operation": "upgrade",
                    "status": "already-current",
                    "active_version": current_version,
                    "pin_changed": pin_changed,
                    "pinned_version": pin.odylith_version if pin else current_version,
                    "previous_version": current_version,
                    "verification": current_verification,
                },
            )
            return UpgradeSummary(
                active_version=current_version,
                launcher_path=launcher_path,
                pin_changed=pin_changed,
                pinned_version=pin.odylith_version if pin else current_version,
                previous_version=current_version,
                repo_root=root,
                repo_role=repo_role,
                followed_latest=request_token == "latest",
                **_release_summary_fields(resolved_release),
                verification=current_verification,
                migration=migration,
            )

        previous_runtime = current_runtime_root(repo_root=root)
        staged = install_release_runtime(repo_root=root, repo=release_repo, version=install_version, activate=False)
        manifest = dict(staged.manifest)
        repo_schema_version = int(manifest.get("repo_schema_version") or DEFAULT_REPO_SCHEMA_VERSION)
        migration_required = bool(manifest.get("migration_required"))
        if migration_required:
            raise ValueError(
                f"release {staged.version} is marked as migration_required and cannot be activated through the normal upgrade path"
            )
        if pin is not None and repo_schema_version != pin.repo_schema_version:
            raise ValueError(
                f"release {staged.version} expects repo_schema_version={repo_schema_version}, but the repo pin requires {pin.repo_schema_version}"
            )
        realigning_to_existing_pin = bool(
            current_version
            and not effective_write_pin
            and pin is not None
            and request_token == pin.odylith_version
            and _is_downgrade(candidate=staged.version, baseline=current_version)
        )
        if _is_downgrade(candidate=staged.version, baseline=current_version) and not realigning_to_existing_pin:
            raise ValueError(
                f"refusing to downgrade from {current_version} to {staged.version} during upgrade; use `odylith rollback --previous` instead"
            )
        reused_context_engine_pack = _reuse_context_engine_feature_pack_from_previous_runtime(
            repo_root=root,
            previous_runtime=previous_runtime,
            target_runtime=staged.root,
            target_version=staged.version,
            manifest=manifest,
        )
        if not reused_context_engine_pack:
            _ensure_managed_context_engine_pack(
                repo_root=root,
                version=staged.version,
                runtime_root=staged.root,
                release_repo=release_repo,
            )

        pin_changed = False
        if effective_write_pin:
            write_version_pin(
                repo_root=root,
                version=staged.version,
                repo_schema_version=repo_schema_version,
                migration_required=False,
            )
            pin_changed = True
            pin = load_version_pin(repo_root=root, fallback_version=staged.version)

        previous_python = _runtime_python(previous_runtime)
        launcher_path = ensure_launcher(repo_root=root, fallback_python=staged.python)
        switch_runtime(repo_root=root, target=staged.root)
        smoke = _run_odylith_smoke(python=staged.python, repo_root=root)
        if smoke.returncode != 0:
            if previous_runtime is not None:
                switch_runtime(repo_root=root, target=previous_runtime)
            if previous_python is not None:
                ensure_launcher(repo_root=root, fallback_python=previous_python)
            append_install_ledger(
                repo_root=root,
                payload={
                    "operation": "upgrade",
                    "status": "failed",
                    "previous_version": current_version,
                    "target_version": staged.version,
                    "stderr": smoke.stderr.strip(),
                    "stdout": smoke.stdout.strip(),
                },
            )
            raise RuntimeError(f"post-activation smoke check failed for {staged.version}: {(smoke.stderr or smoke.stdout).strip()}")

        state_for_persist = (
            _discard_versions_newer_than(state=previous_state, ceiling_version=staged.version)
            if realigning_to_existing_pin
            else previous_state
        )
        _persist_runtime_state(
            repo_root=root,
            state=state_for_persist,
            active_version=staged.version,
            launcher_path=launcher_path,
            consumer_profile=written_profile,
            runtime_root=staged.root,
            verification=staged.verification,
            detached=False,
            integration_enabled=integration_enabled,
        )
        _refresh_consumer_managed_guidance(
            repo_root=root,
            repo_role=repo_role,
            include_brand=False,
            version=staged.version,
        )
        _sync_consumer_casebook_bug_index(repo_root=root, repo_role=repo_role)
        append_install_ledger(
            repo_root=root,
            payload={
                "operation": "upgrade",
                "status": "activated",
                "active_version": staged.version,
                "pin_changed": pin_changed,
                "pinned_version": pin.odylith_version if pin else staged.version,
                "previous_version": current_version,
                "verification": staged.verification,
            },
        )
        _append_self_host_timeline_event(
            repo_root=root,
            summary=(
                f"Activated Odylith runtime {staged.version} for the current repository; "
                f"repo pin is {pin.odylith_version if pin else staged.version}."
            ),
            artifacts=[
                "odylith/runtime/source/product-version.v1.json",
                ".odylith/install.json",
            ],
        )
        return UpgradeSummary(
            active_version=staged.version,
            launcher_path=launcher_path,
            pin_changed=pin_changed,
            pinned_version=pin.odylith_version if pin else staged.version,
            previous_version=current_version,
            repo_root=root,
            repo_role=repo_role,
            followed_latest=request_token == "latest",
            **_release_summary_fields(resolved_release),
            verification=dict(staged.verification),
            migration=migration,
        )


def reinstall_install(
    *,
    repo_root: str | Path,
    release_repo: str,
    version: str = "",
) -> UpgradeSummary:
    root = _repo_root(repo_root, require_agents=False)
    migration = _migrate_legacy_install_if_needed(repo_root=root)
    repo_role = product_repo_role(repo_root=root)
    if repo_role == PRODUCT_REPO_ROLE:
        raise ValueError(
            "`odylith reinstall` is only supported for consumer repos; use `odylith upgrade` or `odylith doctor --repo-root . --repair` in the Odylith product repo"
        )
    _ensure_repo_root_agents_file(repo_root=root)
    _ensure_odylith_gitignore_entry(repo_root=root)
    request_token = str(version or "").strip() or "latest"
    resolved_release = fetch_release(repo_root=root, repo=release_repo, version=request_token)
    target_version = resolved_release.version if request_token == "latest" else request_token
    state_before = load_install_state(repo_root=root)
    previous_version = _observed_active_version(repo_root=root, state=state_before)
    pin_before = load_version_pin(repo_root=root, fallback_version=None)
    _ensure_customer_bootstrap(repo_root=root, version=target_version, repo_role=repo_role)
    try:
        return upgrade_install(
            repo_root=root,
            release_repo=release_repo,
            version=target_version,
            write_pin=True,
        )
    except ValueError as exc:
        message = str(exc)
        if "run `odylith doctor --repo-root . --repair`" not in message:
            raise

    staged = install_release_runtime(
        repo_root=root,
        repo=release_repo,
        version=target_version,
        activate=False,
    )
    manifest = dict(staged.manifest)
    repo_schema_version = int(manifest.get("repo_schema_version") or DEFAULT_REPO_SCHEMA_VERSION)
    if bool(manifest.get("migration_required")):
        raise ValueError(
            f"release {staged.version} is marked as migration_required and cannot be activated through reinstall"
        )
    write_version_pin(
        repo_root=root,
        version=staged.version,
        repo_schema_version=repo_schema_version,
        migration_required=False,
    )
    healthy, repair_message = doctor_bundle(
        repo_root=root,
        bundle_root=root,
        repair=True,
    )
    if not healthy:
        raise RuntimeError(repair_message)
    status = version_status(repo_root=root)
    active_version = str(status.active_version or "").strip() or staged.version
    pin = load_version_pin(repo_root=root, fallback_version=active_version)
    runtime_root = current_runtime_root(repo_root=root)
    verification = runtime_verification_evidence(runtime_root) if runtime_root is not None else {}
    pinned_version = pin.odylith_version if pin is not None else active_version
    pin_changed = pin_before is None or pin_before.odylith_version != pinned_version
    return UpgradeSummary(
        active_version=active_version,
        launcher_path=root / ".odylith" / "bin" / "odylith",
        pin_changed=pin_changed,
        pinned_version=pinned_version,
        previous_version=previous_version,
        repo_root=root,
        repo_role=repo_role,
        followed_latest=request_token == "latest",
        verification=verification,
        repaired=True,
        **_release_summary_fields(resolved_release),
        migration=migration,
    )


def rollback_install(*, repo_root: str | Path) -> RollbackSummary:
    root = _repo_root(repo_root)
    repo_role = product_repo_role(repo_root=root)
    with install_lock(repo_root=root):
        state = load_install_state(repo_root=root)
        active_version = _observed_active_version(repo_root=root, state=state)
        history = current_activation_history(state)
        target_version = ""
        for candidate in reversed(history[:-1]):
            if candidate and candidate != active_version and runtime_root_for_version(repo_root=root, version=candidate).is_dir():
                target_version = candidate
                break
        if not target_version:
            raise ValueError("no previous verified Odylith version is available for rollback")

        target_root = runtime_root_for_version(repo_root=root, version=target_version)
        target_python = _runtime_python(target_root)
        if target_python is None:
            raise ValueError(f"rollback target runtime is missing python: {target_root}")

        current_root = current_runtime_root(repo_root=root)
        current_python = _runtime_python(current_root)
        launcher_path = ensure_launcher(repo_root=root, fallback_python=target_python)
        switch_runtime(repo_root=root, target=target_root)
        smoke = _run_odylith_smoke(python=target_python, repo_root=root)
        if smoke.returncode != 0:
            if current_root is not None:
                switch_runtime(repo_root=root, target=current_root)
            if current_python is not None:
                ensure_launcher(repo_root=root, fallback_python=current_python)
            append_install_ledger(
                repo_root=root,
                payload={
                    "operation": "rollback",
                    "status": "failed",
                    "previous_version": active_version,
                    "target_version": target_version,
                    "stderr": smoke.stderr.strip(),
                    "stdout": smoke.stdout.strip(),
                },
            )
            raise RuntimeError(f"rollback smoke check failed for {target_version}: {(smoke.stderr or smoke.stdout).strip()}")

        written_profile = write_consumer_profile(repo_root=root)
        integration_enabled = install_integration_enabled(state)
        update_agents_file(root / "AGENTS.md", install_active=integration_enabled, repo_role=repo_role)
        verification = {}
        installed_versions_payload = state.get("installed_versions")
        if isinstance(installed_versions_payload, Mapping):
            entry = installed_versions_payload.get(target_version)
            if isinstance(entry, Mapping) and isinstance(entry.get("verification"), Mapping):
                verification = dict(entry["verification"])
        _persist_runtime_state(
            repo_root=root,
            state=state,
            active_version=target_version,
            launcher_path=launcher_path,
            consumer_profile=written_profile,
            runtime_root=target_root,
            verification=verification,
            detached=False,
            integration_enabled=integration_enabled,
        )
        _refresh_consumer_managed_guidance(
            repo_root=root,
            repo_role=repo_role,
            include_brand=False,
            version=target_version,
        )
        pin = load_version_pin(repo_root=root, fallback_version=target_version)
        diverged = bool(pin and target_version != pin.odylith_version)
        append_install_ledger(
            repo_root=root,
            payload={
                "operation": "rollback",
                "status": "activated",
                "active_version": target_version,
                "diverged_from_pin": diverged,
                "pinned_version": pin.odylith_version if pin else "",
                "previous_version": active_version,
            },
        )
        _append_self_host_timeline_event(
            repo_root=root,
            summary=(
                f"Rolled Odylith self-host runtime back to {target_version}; "
                + (
                    f"the runtime now diverges from repo pin {pin.odylith_version}."
                    if diverged and pin
                    else "the active runtime matches the tracked repo pin."
                )
            ),
            artifacts=[
                "odylith/runtime/source/product-version.v1.json",
                ".odylith/install.json",
            ],
        )
        return RollbackSummary(
            active_version=target_version,
            diverged_from_pin=diverged,
            launcher_path=launcher_path,
            pinned_version=pin.odylith_version if pin else "",
            previous_version=active_version,
            repo_root=root,
        )


def uninstall_bundle(*, repo_root: str | Path) -> None:
    root = _repo_root(repo_root)
    with install_lock(repo_root=root):
        state = load_install_state(repo_root=root)
        update_agents_file(root / "AGENTS.md", install_active=False, repo_role=product_repo_role(repo_root=root))
        if state:
            updated_state = dict(state)
            updated_state["detached"] = True
            updated_state["integration_enabled"] = False
            write_install_state(repo_root=root, payload=updated_state)
        append_install_ledger(
            repo_root=root,
            payload={
                "operation": "uninstall",
                "status": "detached",
                "active_version": _observed_active_version(repo_root=root, state=state),
            },
        )


def set_agents_integration(*, repo_root: str | Path, enabled: bool) -> tuple[bool, str]:
    root = _repo_root(repo_root)
    odylith_root = root / "odylith"
    if not odylith_root.is_dir():
        return False, "local customer odylith/ tree missing"

    with install_lock(repo_root=root):
        state = load_install_state(repo_root=root)
        write_consumer_profile(repo_root=root)
        update_agents_file(root / "AGENTS.md", install_active=enabled, repo_role=product_repo_role(repo_root=root))
        updated_state = dict(state)
        active_version = _observed_active_version(repo_root=root, state=updated_state)
        updated_state["detached"] = _effective_detached(state=updated_state, active_version=active_version)
        updated_state["integration_enabled"] = bool(enabled)
        write_install_state(repo_root=root, payload=updated_state)
        append_install_ledger(
            repo_root=root,
            payload={
                "operation": "agents-integration",
                "status": "enabled" if enabled else "disabled",
                "active_version": active_version,
            },
        )
    if enabled:
        return (
            True,
            f"Odylith is now on for coding agents in {root}. Repo-root Odylith guidance was restored so coding agents take Odylith as the default first path again.",
        )
    return (
        True,
        f"Odylith is now off for coding agents in {root}. Repo-root Odylith guidance was detached so coding agents fall back to the surrounding repo's default behavior.",
    )


def ensure_context_engine_pack(
    *,
    repo_root: str | Path,
    release_repo: str = AUTHORITATIVE_RELEASE_REPO,
) -> tuple[bool, str]:
    root = _repo_root(repo_root)
    with install_lock(repo_root=root):
        status = version_status(repo_root=root)
        runtime_root = current_runtime_root(repo_root=root)
        if not status.active_version or runtime_root is None:
            return False, "Odylith runtime is not installed."
        if not (runtime_root / "runtime-metadata.json").is_file():
            if odylith_memory_backend.backend_dependencies_available():
                return False, "Odylith is already running with full local memory support from the current Python environment."
            return False, "The active runtime is not a managed pinned runtime, so there is no installable managed context-engine pack."
        if status.context_engine_pack_installed:
            return False, f"Context-engine feature pack is already installed for {status.active_version}."
        _ensure_managed_context_engine_pack(
            repo_root=root,
            version=status.active_version,
            runtime_root=runtime_root,
            release_repo=release_repo,
        )
        return True, f"Installed context-engine feature pack for {status.active_version}."


def load_install_state(*, repo_root: str | Path) -> dict[str, object]:
    return load_install_state_file(repo_root=repo_root)


def version_status(*, repo_root: str | Path) -> VersionStatus:
    root = _repo_root(repo_root)
    state = load_install_state(repo_root=root)
    active_version = _observed_active_version(repo_root=root, state=state)
    pin_exists = version_pin_path(repo_root=root).is_file()
    pin = load_version_pin(repo_root=root, fallback_version=active_version or __version__)
    runtime_root = current_runtime_root(repo_root=root)
    installed_versions_payload = state.get("installed_versions")
    installed_versions = list(installed_versions_payload) if isinstance(installed_versions_payload, Mapping) else []
    if active_version and active_version not in installed_versions:
        installed_versions.append(active_version)
    installed_versions = sorted({version for version in installed_versions if version}, key=_version_sort_key)
    pinned_version = pin.odylith_version if pin_exists and pin else ""
    effective_detached = _effective_detached(state=state, active_version=active_version)
    repo_role = product_repo_role(repo_root=root)
    verification = _installed_version_verification(state=state, active_version=active_version)
    runtime_status = inspect_runtime_source(
        repo_root=root,
        active_version=active_version,
        pinned_version=pinned_version,
        runtime_root=runtime_root,
        verification=verification,
    )
    runtime_source = runtime_status.source
    context_engine_mode, context_engine_pack_installed = _runtime_context_engine_state(
        runtime_root=runtime_root,
        runtime_source=runtime_source,
    )
    posture = _self_host_posture(
        active_version=active_version,
        pinned_version=pinned_version,
        runtime_root=runtime_root,
    )
    return VersionStatus(
        active_version=active_version,
        available_versions=installed_versions,
        context_engine_mode=context_engine_mode,
        context_engine_pack_installed=context_engine_pack_installed,
        detached=effective_detached,
        diverged_from_pin=bool(pinned_version and active_version and pinned_version != active_version),
        last_known_good_version=_effective_last_known_good(state=state, active_version=active_version),
        pinned_version=pinned_version,
        posture=posture,
        repo_root=root,
        repo_role=repo_role,
        release_eligible=_release_eligible(
            repo_root=root,
            repo_role=repo_role,
            posture=posture,
            pin=pin if pin_exists else None,
            runtime_source=runtime_source,
        ),
        runtime_source=runtime_source,
        runtime_source_detail=runtime_status.detail,
        runtime_trust_degraded=runtime_status.trust_degraded,
        runtime_trust_reasons=runtime_status.trust_reasons,
    )


def doctor_bundle(
    *,
    repo_root: str | Path,
    bundle_root: Path,
    repair: bool,
    reset_local_state: bool = False,
) -> tuple[bool, str]:
    del bundle_root
    if reset_local_state and not repair:
        raise ValueError("reset_local_state requires repair=True")
    candidate_root = Path(repo_root).expanduser().resolve()
    if not (candidate_root / "AGENTS.md").is_file():
        return False, f"repo root does not contain AGENTS.md: {candidate_root}"

    root = _repo_root(candidate_root)
    cleared_paths: list[str] = []
    if repair and reset_local_state:
        cleared_paths = reset_install_local_state(repo_root=root)

    runtime_healthy, runtime_reasons = doctor_runtime(repo_root=root, repair=False)
    state = load_install_state(repo_root=root)
    active_version = _observed_active_version(repo_root=root, state=state, fallback=__version__) or __version__
    has_customer_tree = _has_customer_starter_tree(repo_root=root)
    has_consumer_profile = consumer_profile_path(repo_root=root).is_file()
    has_version_pin = version_pin_path(repo_root=root).is_file()
    agents_text = (root / "AGENTS.md").read_text(encoding="utf-8")
    has_managed = has_managed_block(agents_text)
    integration_enabled = install_integration_enabled(state)
    status = version_status(repo_root=root)
    repo_role = status.repo_role
    effective_detached = _effective_detached(state=state, active_version=status.active_version)
    runtime_root = current_runtime_root(repo_root=root)
    trust_only_runtime_issue = trust_only_runtime_failure(
        runtime_reasons=runtime_reasons,
        trust_reasons=status.runtime_trust_reasons,
        trust_degraded=status.runtime_trust_degraded,
    )
    if (
        runtime_healthy
        and runtime_root is not None
        and (runtime_root / "runtime-metadata.json").is_file()
        and not runtime_context_engine_feature_pack_installed(runtime_root)
    ):
        runtime_healthy = False
        runtime_reasons.append("full-stack context-engine pack missing")
    consumer_lane_violation = _consumer_lane_violation_reason(
        repo_role=status.repo_role,
        posture=status.posture,
        runtime_source=status.runtime_source,
    )
    if consumer_lane_violation:
        runtime_healthy = False
        runtime_reasons.append(consumer_lane_violation)
    healthy = runtime_healthy and has_customer_tree and has_consumer_profile and has_version_pin and has_managed == integration_enabled and bool(state)

    if repair:
        _ensure_customer_bootstrap(
            repo_root=root,
            version=_preferred_bootstrap_version(repo_root=root, state=state, active_version=active_version),
            repo_role=repo_role,
        )
        _ensure_odylith_gitignore_entry(repo_root=root)
        written_profile = write_consumer_profile(repo_root=root)
        update_agents_file(root / "AGENTS.md", install_active=integration_enabled, repo_role=repo_role)
        runtime_verification: dict[str, object] = runtime_verification_evidence(runtime_root) if runtime_root is not None else {}
        if not runtime_healthy:
            if repo_role == PRODUCT_REPO_ROLE:
                pin = load_version_pin(repo_root=root, fallback_version=None)
                if (
                    runtime_root is not None
                    and pin is not None
                    and not _is_source_local_version(pin.odylith_version)
                    and not bool(pin.migration_required)
                ):
                    try:
                        staged = install_release_runtime(
                            repo_root=root,
                            repo=AUTHORITATIVE_RELEASE_REPO,
                            version=pin.odylith_version,
                            activate=False,
                        )
                        _ensure_managed_context_engine_pack(
                            repo_root=root,
                            version=pin.odylith_version,
                            runtime_root=staged.root,
                            release_repo=AUTHORITATIVE_RELEASE_REPO,
                        )
                    except Exception:
                        pass
                repaired_runtime_healthy, _ = doctor_runtime(
                    repo_root=root,
                    repair=True,
                    allow_host_python_fallback=True,
                )
                if not repaired_runtime_healthy:
                    return False, "Odylith repair could not restore a valid local runtime."
                runtime_root = current_runtime_root(repo_root=root)
                runtime_verification = runtime_verification_evidence(runtime_root) if runtime_root is not None else {}
            else:
                if not has_version_pin:
                    return False, "Odylith repair requires a tracked pinned release before it can restage a verified runtime."
                pin = load_version_pin(repo_root=root, fallback_version=None)
                if pin is None or _is_source_local_version(pin.odylith_version) or bool(pin.migration_required):
                    return False, "Odylith repair requires a valid non-detached pinned release for consumer repos."
                try:
                    staged = install_release_runtime(
                        repo_root=root,
                        repo=AUTHORITATIVE_RELEASE_REPO,
                        version=pin.odylith_version,
                        activate=True,
                    )
                except Exception as exc:
                    return False, f"Odylith repair could not restage pinned runtime {pin.odylith_version}: {exc}"
                runtime_root = staged.root
                runtime_verification = dict(staged.verification)
                try:
                    _ensure_managed_context_engine_pack(
                        repo_root=root,
                        version=pin.odylith_version,
                        runtime_root=staged.root,
                        release_repo=AUTHORITATIVE_RELEASE_REPO,
                    )
                except Exception as exc:
                    return False, f"Odylith repair could not restage context-engine pack for {pin.odylith_version}: {exc}"
        repaired_active_version = current_runtime_version(repo_root=root) or active_version
        repaired_detached = _effective_detached(state=state, active_version=repaired_active_version)
        fallback_python = _runtime_python(runtime_root)
        if fallback_python is None:
            if repo_role != PRODUCT_REPO_ROLE:
                return False, "Odylith repair could not restore a verified repo-local runtime."
            fallback_python = Path(sys.executable)
        launcher_path = ensure_launcher(
            repo_root=root,
            fallback_python=fallback_python,
            allow_host_python_fallback=repo_role == PRODUCT_REPO_ROLE,
        )
        _persist_runtime_state(
            repo_root=root,
            state=state,
            active_version=repaired_active_version,
            launcher_path=launcher_path,
            consumer_profile=written_profile,
            runtime_root=runtime_root,
            verification=runtime_verification,
            detached=repaired_detached,
            integration_enabled=integration_enabled,
            mark_last_known_good=not _is_source_local_version(repaired_active_version),
        )
        _refresh_consumer_managed_guidance(
            repo_root=root,
            repo_role=repo_role,
            include_brand=False,
            version=repaired_active_version,
        )
        _sync_consumer_casebook_bug_index(repo_root=root, repo_role=repo_role)
        repaired_status = version_status(repo_root=root)
        reset_clause = ""
        if reset_local_state:
            reset_clause = (
                f" after resetting {len(cleared_paths)} local mutable path(s)"
                if cleared_paths
                else " after resetting local mutable state"
            )
        if repaired_status.detached and repaired_status.diverged_from_pin:
            return (
                True,
                f"Odylith repair completed for {root}{reset_clause}. Active version is still a detached local override and diverges from the repo pin.",
            )
        if repaired_status.detached:
            return True, f"Odylith repair completed for {root}{reset_clause}. Active version remains a detached local override."
        if repaired_status.diverged_from_pin:
            return True, f"Odylith repair completed for {root}{reset_clause}. Active version still diverges from the repo pin."
        return True, f"Odylith repair completed for {root}{reset_clause}."

    if (
        trust_only_runtime_issue
        and has_customer_tree
        and has_consumer_profile
        and has_version_pin
        and has_managed == integration_enabled
        and bool(state)
    ):
        if status.repo_role == PRODUCT_REPO_ROLE:
            return (
                True,
                f"Odylith runtime is healthy but trust-degraded and not release-eligible: {status.runtime_source_detail}",
            )
        return True, f"Odylith runtime is healthy but trust-degraded: {status.runtime_source_detail}"

    if healthy:
        if status.runtime_trust_degraded:
            if status.repo_role == PRODUCT_REPO_ROLE:
                return (
                    True,
                    f"Odylith runtime is healthy but trust-degraded and not release-eligible: {status.runtime_source_detail}",
                )
            return True, f"Odylith runtime is healthy but trust-degraded: {status.runtime_source_detail}"
        if effective_detached and status.diverged_from_pin:
            return True, (
                f"Odylith runtime is healthy, but active version {status.active_version or 'unknown'} "
                f"is a detached local override and diverges from repo pin {status.pinned_version or 'unknown'}."
            )
        if effective_detached:
            return True, "Odylith runtime is healthy and currently detached as a local override."
        if status.diverged_from_pin:
            return True, (
                f"Odylith runtime is healthy, but active version {status.active_version or 'unknown'} "
                f"diverges from repo pin {status.pinned_version or 'unknown'}."
            )
        if status.repo_role == PRODUCT_REPO_ROLE and status.release_eligible is False:
            if status.runtime_source == WRAPPED_RUNTIME_SOURCE:
                return True, (
                    f"Odylith runtime is healthy, but active version {status.active_version or 'unknown'} "
                    f"is only a local wrapped runtime and is not release-eligible until a verified staged runtime is active. "
                    f"{status.runtime_source_detail}"
                )
            return True, "Odylith runtime is healthy, but the product repo is not currently release-eligible."
        return True, "Odylith runtime and local customer bootstrap are healthy."

    reasons: list[str] = []
    reasons.extend(runtime_reasons)
    if not has_customer_tree:
        reasons.append("local customer odylith/ starter tree missing")
    if not state:
        reasons.append("install state missing")
    if not has_version_pin:
        reasons.append("product version pin missing")
    if integration_enabled and not has_managed:
        reasons.append("Odylith scope block missing from AGENTS.md")
    elif not integration_enabled and has_managed:
        reasons.append("Odylith scope block present while Odylith is off")
    if not has_consumer_profile:
        reasons.append("consumer profile missing")
    return False, "; ".join(reasons)
