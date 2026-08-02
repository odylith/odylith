"""Host-agnostic completion handoff for a committed Greenfield transaction."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import webbrowser

from odylith.runtime.domain_intelligence import greenfield_generation_state
from odylith.runtime.domain_intelligence import greenfield_generation_store
from odylith.runtime.domain_intelligence import greenfield_repository_lock
from odylith.runtime.domain_intelligence import greenfield_repository_write_set


POST_CONFIRM_NAVIGATION = {
    "project": "odylith/index.html?tab=project",
    "radar": "odylith/index.html?tab=radar",
    "registry": "odylith/index.html?tab=registry",
    "atlas": "odylith/index.html?tab=atlas",
    "compass": "odylith/index.html?tab=compass&date=live",
}


class GreenfieldCanonicalViewUnavailableError(RuntimeError):
    """The current governed view cannot be resolved without exposing uncertain bytes."""


def canonical_current_project_root(repo_root: Path) -> tuple[Path, str]:
    """Resolve one coherent current view through the active-generation state."""

    root = Path(repo_root).expanduser().resolve()
    try:
        with greenfield_repository_lock.greenfield_repository_read_lock(root):
            return _canonical_current_project_root_while_locked(root)
    except greenfield_repository_lock.GreenfieldRepositoryBusyError as exc:
        state = greenfield_generation_state.read_active_generation_state(root)
        if state is not None and str(state.get("status") or "") == greenfield_generation_state.ACTIVE:
            pinned = greenfield_generation_store.pin_active_greenfield_generation(root)
            return pinned.repository_root, "active_generation_during_managed_write"
        raise GreenfieldCanonicalViewUnavailableError(
            "The current project view is temporarily unavailable while a governed write is publishing."
        ) from exc


def _canonical_current_project_root_while_locked(root: Path) -> tuple[Path, str]:
    state = greenfield_generation_state.read_active_generation_state(root)
    if state is None:
        return root, "live_without_generation"
    if str(state.get("status") or "") == greenfield_generation_state.SUPERSEDED:
        return root, "live_after_supersession"
    pinned = greenfield_generation_store.pin_active_greenfield_generation(root)
    expected = {str(key): str(value) for key, value in dict(pinned.manifest["after_fingerprints"]).items()}
    actual = greenfield_repository_write_set.greenfield_managed_fingerprints(root)
    if actual != expected:
        raise GreenfieldCanonicalViewUnavailableError(
            "The active Greenfield generation no longer matches the managed repository tree. "
            "No potentially partial live view was opened."
        )
    return pinned.repository_root, "active_generation"


def post_confirm_navigation(repo_root: Path, *, transaction_hash: str = "") -> dict[str, str]:
    """Return stable routes after a confirmed create."""

    root = Path(repo_root).expanduser().resolve()
    transaction = str(transaction_hash or "").strip()
    if transaction:
        pinned = greenfield_generation_store.pin_greenfield_generation(
            repo_root=root,
            transaction_hash=transaction,
        )
        repository_root = pinned.repository_root
        view_status = "reviewed_generation"
    else:
        pinned = None
        repository_root, view_status = canonical_current_project_root(root)
    dashboard_path = (repository_root / "odylith" / "index.html").resolve()
    navigation = dict(POST_CONFIRM_NAVIGATION)
    navigation["dashboard_path"] = str(dashboard_path)
    navigation["project_url"] = f"{dashboard_path.as_uri()}?tab=project"
    navigation["view_status"] = view_status
    navigation["compatibility_dashboard_path"] = str((root / "odylith" / "index.html").resolve())
    if pinned is not None:
        navigation["generation_transaction_hash"] = pinned.transaction_hash
        navigation["reviewed_generation_path"] = str(pinned.generation_root)
    return navigation


def open_committed_dashboard(navigation: Mapping[str, str]) -> dict[str, Any]:
    """Open the committed Project view without changing transaction success."""

    url = str(navigation.get("project_url") or "").strip()
    try:
        opened = bool(url and webbrowser.open(url, new=2))
    except Exception as error:  # pragma: no cover - browser integrations vary by host
        return {"status": "unavailable", "url": url, "reason": f"{type(error).__name__}: {error}"}
    return {
        "status": "opened" if opened else "unavailable",
        "url": url,
        "reason": "" if opened else "no browser accepted the local dashboard URL",
    }


def completion_markdown(
    *,
    transaction_hash: str,
    result: Mapping[str, Any],
    navigation: Mapping[str, str],
    browser_result: Mapping[str, Any],
) -> str:
    """Render one concise, branded success result from sealed commit evidence."""

    summary = result.get("product_create_transaction")
    summary = dict(summary) if isinstance(summary, Mapping) else {}
    opened = browser_result.get("status") == "opened"
    destination = (
        f"Opened the committed [Project dashboard]({navigation['project_url']})."
        if opened
        else (
            "The package is committed. Open the "
            f"[Project dashboard]({navigation['project_url']}) or use `{navigation['dashboard_path']}`."
        )
    )
    return "\n".join(
        (
            "**Odylith Greenfield published**",
            "",
            f"Transaction `{transaction_hash}` was committed from the exact reviewed bytes and passed readback.",
            f"{destination}",
            "",
            f"- Sealed writes: {int(summary.get('repository_write_count', 0) or 0)}",
            f"- Quality gate: `{str(summary.get('quality_status') or 'passed')}`",
            f"- Validation gate: `{str(summary.get('validation_status') or 'passed')}`",
            "",
            "Next: Review Product Story and the first workstream before beginning implementation. No application code was generated.",
        )
    )


__all__ = [
    "POST_CONFIRM_NAVIGATION",
    "GreenfieldCanonicalViewUnavailableError",
    "canonical_current_project_root",
    "completion_markdown",
    "open_committed_dashboard",
    "post_confirm_navigation",
]
