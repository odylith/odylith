"""Host-agnostic completion handoff for a committed Greenfield transaction."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
import webbrowser

from odylith.runtime.domain_intelligence import greenfield_generation_store


POST_CONFIRM_NAVIGATION = {
    "project": "odylith/index.html?tab=project",
    "radar": "odylith/index.html?tab=radar",
    "registry": "odylith/index.html?tab=registry",
    "atlas": "odylith/index.html?tab=atlas",
    "compass": "odylith/index.html?tab=compass&date=live",
}


def post_confirm_navigation(repo_root: Path, *, transaction_hash: str = "") -> dict[str, str]:
    """Return stable routes after a confirmed create."""

    root = Path(repo_root).expanduser().resolve()
    pinned = (
        greenfield_generation_store.pin_active_greenfield_generation(root)
        if str(transaction_hash or "").strip()
        else None
    )
    if pinned is not None and pinned.transaction_hash != str(transaction_hash).strip():
        raise RuntimeError("committed Greenfield dashboard generation does not match the transaction")
    dashboard_path = (
        (pinned.repository_root / "odylith" / "index.html")
        if pinned is not None
        else (root / "odylith" / "index.html")
    ).resolve()
    navigation = dict(POST_CONFIRM_NAVIGATION)
    navigation["dashboard_path"] = str(dashboard_path)
    navigation["project_url"] = f"{dashboard_path.as_uri()}?tab=project"
    navigation["compatibility_dashboard_path"] = str((root / "odylith" / "index.html").resolve())
    if pinned is not None:
        navigation["generation_transaction_hash"] = pinned.transaction_hash
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
    "completion_markdown",
    "open_committed_dashboard",
    "post_confirm_navigation",
]
