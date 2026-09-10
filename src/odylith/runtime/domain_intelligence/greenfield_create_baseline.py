"""Precompiled governance baselines and complete first-publication activation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
import stat
from typing import Callable

from odylith.install.bootstrap_assets import customer_backlog_index_source
from odylith.install.bootstrap_assets import customer_diagram_catalog_source
from odylith.install.bootstrap_assets import customer_plan_index_source
from odylith.install.bootstrap_assets import customer_shell_index_placeholder_source
from odylith.install.fs import atomic_write_bytes
from odylith.install.fs import atomic_write_text
from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set
from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal


_BASELINE_DIRS = (
    "odylith/radar/source/ideas",
    "odylith/technical-plans/in-progress",
    "odylith/technical-plans/done",
    "odylith/technical-plans/parked",
    "odylith/atlas/source/catalog",
    "odylith/registry/source/components",
)
_BASELINE_FILES: Mapping[str, Callable[[Path], str]] = {
    "odylith/radar/source/INDEX.md": lambda root: customer_backlog_index_source(repo_root=root),
    "odylith/technical-plans/INDEX.md": lambda _root: customer_plan_index_source(),
    "odylith/atlas/source/catalog/diagrams.v1.json": lambda _root: customer_diagram_catalog_source(),
}


def activate_completed_greenfield_baseline(
    *, repo_root: Path, required_surface_outputs: Sequence[Path],
) -> dict[str, str]:
    """Activate an already rendered baseline, never render or generate during activation.

    The caller supplies the existing first-run surface contract. Publication precedes
    working-shell seeding so interruption cannot expose mutable project resources.
    """

    root = Path(repo_root).expanduser().resolve()
    with greenfield_repository_lock.greenfield_repository_lock(root):
        GreenfieldCommitJournal.recover_pending_journals(repo_root=root)
        return activate_completed_greenfield_baseline_locked(
            repo_root=root, required_surface_outputs=required_surface_outputs,
        )


def recover_published_greenfield_baseline(
    *, repo_root: Path, required_surface_outputs: Sequence[Path],
) -> dict[str, str] | None:
    """Repair only an existing publication; an unrendered install is not activated."""

    root = Path(repo_root).expanduser().resolve()
    with greenfield_repository_lock.greenfield_repository_lock(root):
        GreenfieldCommitJournal.recover_pending_journals(repo_root=root)
        if greenfield_generation_state.read_active_publication(root) is None:
            return None
        return activate_completed_greenfield_baseline_locked(
            repo_root=root, required_surface_outputs=required_surface_outputs,
        )


def activate_completed_greenfield_baseline_locked(
    *, repo_root: Path, required_surface_outputs: Sequence[Path],
) -> dict[str, str]:
    """Activate within a writer-owned lock, after its pending journals are settled."""

    root = Path(repo_root).expanduser().resolve()
    publication = greenfield_generation_state.read_active_publication(root)
    if publication is None:
        _require_completed_baseline_surfaces(root, required_surface_outputs)
        write_set = greenfield_repository_write_set.compile_greenfield_repository_write_set(
            source_root=root, staged_root=root,
        )
        manifest = greenfield_generation_store.compile_greenfield_generation_manifest(write_set)
        generation = greenfield_generation_store.materialize_immutable_greenfield_generation(
            repo_root=root, write_set=write_set, manifest_text=manifest,
        )
        entry = greenfield_generation_state.compile_greenfield_publication_entry(
            write_set_hash=generation.write_set_hash,
            generation_manifest_sha256=generation.manifest_sha256,
        )
        greenfield_repository_write_set.require_greenfield_repository_preconditions(
            repo_root=root, write_set=write_set,
        )
        publication = greenfield_generation_store.publish_greenfield_generation(
            repo_root=root, generation=generation, write_set=write_set,
            publication_entry_text=entry,
        )
    else:
        generation = greenfield_generation_store.pin_active_greenfield_generation(root)
        _require_completed_baseline_surfaces(generation.repository_root, required_surface_outputs)
    _restore_missing_baseline_shell(root, generation)
    return publication


def _require_completed_baseline_surfaces(root: Path, outputs: Sequence[Path]) -> None:
    if not outputs or Path("odylith/index.html") not in outputs:
        raise ValueError("Complete first-run surface outputs are required for baseline activation")
    layout = greenfield_repository_write_set.greenfield_repository_layout(root)
    for relative in outputs:
        path = layout.target_path(relative.as_posix())
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"Greenfield baseline requires a complete rendered surface: {relative}")
    shell = layout.target_path("odylith/index.html").read_bytes()
    if shell == customer_shell_index_placeholder_source(repo_root=root).encode("utf-8"):
        raise RuntimeError("Greenfield baseline cannot publish the installation placeholder")


def _restore_missing_baseline_shell(
    root: Path, generation: greenfield_generation_store.PinnedGreenfieldGeneration,
) -> None:
    expected = generation.manifest["after_fingerprints"]
    actual = greenfield_repository_write_set.greenfield_managed_fingerprints(root)
    working = greenfield_repository_write_set.greenfield_repository_layout(root).target_path("odylith/index.html")
    shell_missing = not working.exists() and not working.is_symlink()
    drift = [
        path for path in expected
        if expected[path] != actual[path] and not (shell_missing and path == "odylith/index.html")
    ]
    if drift:
        raise RuntimeError("Greenfield baseline working files differ from publication: " + ", ".join(drift))
    if shell_missing:
        source = generation.repository_root / "odylith/index.html"
        atomic_write_bytes(working, source.read_bytes(), mode=stat.S_IMODE(source.stat().st_mode))
    if greenfield_repository_write_set.greenfield_managed_fingerprints(root) != expected:
        raise RuntimeError("Greenfield baseline working files differ after exact shell restoration")


def ensure_greenfield_create_baseline(root: Path) -> None:
    """Create missing governance indexes needed by staged prewrite compilation."""

    target_root = Path(root).expanduser().resolve()
    for token in _BASELINE_DIRS:
        (target_root / token).mkdir(parents=True, exist_ok=True)
    for token, build in _BASELINE_FILES.items():
        path = target_root / token
        if not path.exists():
            atomic_write_text(path, build(target_root), encoding="utf-8")


def precompiled_greenfield_create_baseline_writes(root: Path) -> dict[str, str]:
    """Return missing baseline file writes that must be sealed before confirm."""

    target_root = Path(root).expanduser().resolve()
    writes: dict[str, str] = {}
    for token, build in _BASELINE_FILES.items():
        if not (target_root / token).exists():
            writes[token] = build(target_root)
    return writes


def require_precompiled_greenfield_create_baseline(root: Path, baseline_writes: Mapping[str, object]) -> None:
    """Fail before the write boundary if missing baseline files were not compiled."""

    target_root = Path(root).expanduser().resolve()
    approved = set(_BASELINE_FILES)
    for token in baseline_writes:
        if str(token) not in approved:
            raise ValueError(
                f"ProductCreateTransaction contains an unapproved baseline write {token!r}; "
                "rebuild the pre-confirm transaction before committing governed records"
            )
    missing = [
        token
        for token in _BASELINE_FILES
        if not (target_root / token).exists() and token not in baseline_writes
    ]
    if missing:
        raise ValueError(
            "ProductCreateTransaction is missing precompiled baseline writes for "
            + ", ".join(missing)
            + "; rebuild the pre-confirm transaction before committing governed records"
        )


def materialize_precompiled_greenfield_create_baseline(
    *,
    root: Path,
    baseline_writes: Mapping[str, object],
) -> None:
    """Write only baseline files already sealed inside the ProductCreateTransaction."""

    target_root = Path(root).expanduser().resolve()
    require_precompiled_greenfield_create_baseline(target_root, baseline_writes)
    for token in _BASELINE_DIRS:
        (target_root / token).mkdir(parents=True, exist_ok=True)
    for token, text in baseline_writes.items():
        relative = Path(str(token))
        if relative.is_absolute() or ".." in relative.parts:
            raise RuntimeError(f"compiled baseline write escapes repo root: {token}")
        path = (target_root / relative).resolve()
        if not str(path).startswith(str(target_root)):
            raise RuntimeError(f"compiled baseline write escapes repo root: {token}")
        if not isinstance(text, str):
            raise RuntimeError(f"compiled baseline write is not text: {token}")
        if path.exists():
            existing = path.read_text(encoding="utf-8")
            if existing != text:
                raise RuntimeError(
                    f"compiled baseline write target changed after confirmation: {token}"
                )
            continue
        atomic_write_text(path, text, encoding="utf-8")


__all__ = [
    "activate_completed_greenfield_baseline",
    "activate_completed_greenfield_baseline_locked",
    "ensure_greenfield_create_baseline",
    "materialize_precompiled_greenfield_create_baseline",
    "precompiled_greenfield_create_baseline_writes",
    "recover_published_greenfield_baseline",
    "require_precompiled_greenfield_create_baseline",
]
