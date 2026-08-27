"""Pre-confirm surface refresh proof for greenfield create transactions."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.governance import owned_surface_refresh
from odylith.runtime.surfaces import compass_refresh_contract


GREENFIELD_SURFACE_REFRESH_PROOF_VERSION = "greenfield.prewrite_surface_refresh.v1"
GREENFIELD_SURFACE_REFRESH_PROOF_PHASE = "pre_confirm_compile"
GREENFIELD_SURFACE_REFRESH_PROOF_KIND = "staged_owned_surface_refresh"
GREENFIELD_VISIBLE_SURFACES = ("radar", "registry", "atlas", "compass", "tooling_shell")
GREENFIELD_REQUIRED_SURFACE_ARTIFACTS = (
    "odylith/radar/radar.html",
    "odylith/radar/backlog-payload.v1.js",
    "odylith/registry/registry.html",
    "odylith/registry/registry-payload.v1.js",
    "odylith/atlas/atlas.html",
    "odylith/atlas/mermaid-payload.v1.js",
    "odylith/compass/compass.html",
    "odylith/compass/compass-payload.v1.js",
    "odylith/index.html",
    "odylith/tooling-payload.v1.js",
)


def build_prewrite_surface_refresh_preview(
    *,
    repo_root: Path,
) -> dict[str, Any]:
    """Run the staged refresh and return the sealed proof copied into the transaction."""

    root = Path(repo_root).expanduser().resolve()
    owned_surface_refresh.raise_for_failed_refreshes(
        repo_root=root,
        surfaces=GREENFIELD_VISIBLE_SURFACES,
        operation_label="Greenfield pre-confirm staged surface refresh",
        atlas_sync=False,
        compass_refresh_profile=(
            compass_refresh_contract.SEALED_PRECONFIRM_REFRESH_PROFILE
        ),
    )
    missing = [path for path in GREENFIELD_REQUIRED_SURFACE_ARTIFACTS if _missing_or_empty(root / path)]
    if missing:
        raise RuntimeError(
            "Greenfield pre-confirm staged surface refresh did not render required artifacts: "
            + ", ".join(missing)
        )
    preview = {
        "version": GREENFIELD_SURFACE_REFRESH_PROOF_VERSION,
        "status": "passed",
        "phase": GREENFIELD_SURFACE_REFRESH_PROOF_PHASE,
        "proof": GREENFIELD_SURFACE_REFRESH_PROOF_KIND,
        "surfaces": list(GREENFIELD_VISIBLE_SURFACES),
        "artifact_paths": list(GREENFIELD_REQUIRED_SURFACE_ARTIFACTS),
        "view": owned_surface_refresh.dashboard_handoff(surface="project"),
    }
    issues = surface_refresh_preview_issues(preview)
    if issues:
        raise RuntimeError(
            "Greenfield pre-confirm staged surface refresh proof is invalid: "
            + "; ".join(issues)
        )
    return preview


def failed_prewrite_surface_refresh_preview(*, reason: object) -> dict[str, Any]:
    """Return a reportable failed proof that cannot pass transaction build."""

    return {
        "version": GREENFIELD_SURFACE_REFRESH_PROOF_VERSION,
        "status": "failed",
        "phase": GREENFIELD_SURFACE_REFRESH_PROOF_PHASE,
        "proof": GREENFIELD_SURFACE_REFRESH_PROOF_KIND,
        "surfaces": list(GREENFIELD_VISIBLE_SURFACES),
        "artifact_paths": list(GREENFIELD_REQUIRED_SURFACE_ARTIFACTS),
        "view": owned_surface_refresh.dashboard_handoff(surface="project"),
        "reason": str(reason or "").strip(),
    }


def require_compiled_surface_refresh_preview(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Return a normalized proof mapping or fail the compiled transaction contract."""

    issues = surface_refresh_preview_issues(value)
    if issues:
        raise ValueError(
            "compiled greenfield package is incomplete; rebuild the ProductCreateTransaction before commit: "
            + "; ".join(issues)
        )
    return dict(value or {})


def surface_refresh_preview_issues(value: Mapping[str, Any] | None) -> list[str]:
    """Validate the stable proof facts used by package reports and transactions."""

    if not isinstance(value, Mapping) or not value:
        return ["missing compiled pre-confirm surface refresh proof"]
    issues: list[str] = []
    if str(value.get("version", "")).strip() != GREENFIELD_SURFACE_REFRESH_PROOF_VERSION:
        issues.append("compiled surface refresh proof has an unsupported version")
    if str(value.get("status", "")).strip() != "passed":
        reason = str(value.get("reason", "")).strip()
        issues.append(
            "compiled surface refresh proof did not pass"
            + (f": {reason}" if reason else "")
        )
    if str(value.get("phase", "")).strip() != GREENFIELD_SURFACE_REFRESH_PROOF_PHASE:
        issues.append("compiled surface refresh proof is not from pre-confirm compile")
    if str(value.get("proof", "")).strip() != GREENFIELD_SURFACE_REFRESH_PROOF_KIND:
        issues.append("compiled surface refresh proof has an unsupported proof kind")
    if _string_tuple(value.get("surfaces")) != GREENFIELD_VISIBLE_SURFACES:
        issues.append("compiled surface refresh proof surfaces drifted from required greenfield surfaces")
    if _string_tuple(value.get("artifact_paths")) != GREENFIELD_REQUIRED_SURFACE_ARTIFACTS:
        issues.append("compiled surface refresh proof artifacts drifted from required rendered surfaces")
    view = str(value.get("view", "")).strip()
    if not view.startswith("odylith/index.html"):
        issues.append("compiled surface refresh proof missing dashboard handoff view")
    return issues


def _missing_or_empty(path: Path) -> bool:
    return not path.is_file() or path.stat().st_size <= 0


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(str(item).strip() for item in value if str(item).strip())


__all__ = [
    "GREENFIELD_REQUIRED_SURFACE_ARTIFACTS",
    "GREENFIELD_SURFACE_REFRESH_PROOF_KIND",
    "GREENFIELD_SURFACE_REFRESH_PROOF_PHASE",
    "GREENFIELD_SURFACE_REFRESH_PROOF_VERSION",
    "GREENFIELD_VISIBLE_SURFACES",
    "build_prewrite_surface_refresh_preview",
    "failed_prewrite_surface_refresh_preview",
    "require_compiled_surface_refresh_preview",
    "surface_refresh_preview_issues",
]
