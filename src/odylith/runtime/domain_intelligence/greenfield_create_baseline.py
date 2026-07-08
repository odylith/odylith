"""Precompiled baseline files for greenfield create transactions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Callable

from odylith.install.bootstrap_assets import customer_backlog_index_source
from odylith.install.bootstrap_assets import customer_diagram_catalog_source
from odylith.install.bootstrap_assets import customer_plan_index_source
from odylith.install.fs import atomic_write_text


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
    "ensure_greenfield_create_baseline",
    "materialize_precompiled_greenfield_create_baseline",
    "precompiled_greenfield_create_baseline_writes",
    "require_precompiled_greenfield_create_baseline",
]
