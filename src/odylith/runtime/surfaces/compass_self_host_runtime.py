"""Self-host posture helpers extracted from Compass runtime."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from collections.abc import Callable, Mapping

from odylith.install.manager import (
    DETACHED_SOURCE_LOCAL_POSTURE,
    DIVERGED_VERIFIED_VERSION_POSTURE,
    PINNED_RELEASE_POSTURE,
    PINNED_RUNTIME_SOURCE,
    PRODUCT_REPO_ROLE,
    UNINSTALLED_OR_INCOMPLETE_POSTURE,
    WRAPPED_RUNTIME_SOURCE,
    version_status,
)


def self_host_snapshot(*, repo_root: Path) -> dict[str, Any]:
    launcher_path = (Path(repo_root).resolve() / ".odylith" / "bin" / "odylith").resolve()
    try:
        status = version_status(repo_root=repo_root)
    except Exception:
        return {}
    return {
        "repo_role": status.repo_role,
        "posture": status.posture,
        "runtime_source": status.runtime_source,
        "release_eligible": status.release_eligible,
        "pinned_version": status.pinned_version,
        "active_version": status.active_version,
        "detached": status.detached,
        "diverged_from_pin": status.diverged_from_pin,
        "launcher_present": launcher_path.is_file(),
    }


def self_host_risk_rows(*, snapshot: Mapping[str, Any], local_date: str) -> list[dict[str, Any]]:
    if str(snapshot.get("repo_role", "")).strip() != PRODUCT_REPO_ROLE:
        return []
    posture = str(snapshot.get("posture", "")).strip()
    runtime_source = str(snapshot.get("runtime_source", "")).strip()
    release_eligible = snapshot.get("release_eligible")
    pinned_version = str(snapshot.get("pinned_version", "")).strip()
    active_version = str(snapshot.get("active_version", "")).strip()
    if posture not in {
        DETACHED_SOURCE_LOCAL_POSTURE,
        DIVERGED_VERIFIED_VERSION_POSTURE,
        UNINSTALLED_OR_INCOMPLETE_POSTURE,
    } and release_eligible is not False:
        return []

    message = ""
    severity = "warning"
    if posture == DETACHED_SOURCE_LOCAL_POSTURE:
        severity = "error"
        message = (
            f"Odylith product repo is running detached source-local runtime `{active_version or 'unknown'}`; "
            f"release gating stays blocked until the active runtime returns to repo pin `{pinned_version or 'unknown'}`."
        )
    elif posture == DIVERGED_VERIFIED_VERSION_POSTURE:
        message = (
            f"Odylith product repo active runtime `{active_version or 'unknown'}` diverges from repo pin "
            f"`{pinned_version or 'unknown'}`."
        )
    elif posture == UNINSTALLED_OR_INCOMPLETE_POSTURE:
        severity = "error"
        message = "Odylith product repo local runtime is incomplete; pinned dogfood posture is not currently available."
    elif runtime_source == WRAPPED_RUNTIME_SOURCE:
        severity = "error"
        message = (
            f"Odylith product repo is running a local wrapped runtime for `{active_version or pinned_version or 'unknown'}`; "
            "release gating stays blocked until a verified staged runtime is activated."
        )
    elif release_eligible is False:
        message = (
            f"Odylith product repo is not release eligible while source and pin posture disagree on "
            f"`{pinned_version or active_version or 'unknown'}`."
        )
    if not message:
        return []
    return [
        {
            "severity": severity,
            "kind": "self_host_posture",
            "message": message,
            "date": str(local_date or "").strip(),
            "idea_id": "",
            "workstreams": [],
        }
    ]


def self_host_release_eligibility_label(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "n/a"


def self_host_status_fact(
    snapshot: Mapping[str, Any],
    *,
    standup_fact_builder: Callable[..., dict[str, Any]],
) -> dict[str, Any] | None:
    repo_role = str(snapshot.get("repo_role", "")).strip()
    if not repo_role:
        return None
    posture = str(snapshot.get("posture", "")).strip() or "unknown"
    runtime_source = str(snapshot.get("runtime_source", "")).strip() or "unknown"
    pinned_version = str(snapshot.get("pinned_version", "")).strip() or "unknown"
    active_version = str(snapshot.get("active_version", "")).strip() or "unknown"
    launcher_present = bool(snapshot.get("launcher_present"))
    release_eligible = self_host_release_eligibility_label(snapshot.get("release_eligible"))

    if (
        repo_role == PRODUCT_REPO_ROLE
        and posture == PINNED_RELEASE_POSTURE
        and runtime_source == PINNED_RUNTIME_SOURCE
        and active_version == pinned_version
        and snapshot.get("release_eligible") is True
    ):
        return standup_fact_builder(
            section_key="current_execution",
            voice_hint="operator",
            priority=92,
            text=(
                f"Live self-host posture check passed: Odylith product repo is on pinned dogfood runtime "
                f"`{active_version}` with repo pin `{pinned_version}`, and the repo-local launcher is "
                f"{'present' if launcher_present else 'missing'}."
            ),
            source="self_host",
            kind="self_host_status",
        )

    repo_label = "Odylith product repo" if repo_role == PRODUCT_REPO_ROLE else "Current repo"
    return standup_fact_builder(
        section_key="current_execution",
        voice_hint="operator",
        priority=92,
        text=(
            f"Live install posture check: {repo_label} reports repo role `{repo_role}`, posture `{posture}`, "
            f"runtime source `{runtime_source}`, active `{active_version}`, repo pin `{pinned_version}`, "
            f"launcher {'present' if launcher_present else 'missing'}, and release eligibility `{release_eligible}`."
        ),
        source="self_host",
        kind="self_host_status",
    )
