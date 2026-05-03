"""Prepare Compass dashboard prerequisites before running the refresh engine."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path
from typing import Any

from odylith.runtime.common.command_surface import display_command
from odylith.runtime.surfaces import compass_refresh_contract
from odylith.runtime.surfaces import compass_refresh_runtime


def run_compass_dashboard_refresh(
    *,
    repo_root: Path,
    normalized_runtime_mode: str,
) -> dict[str, Any]:
    prerequisite_result = ensure_compass_dashboard_inputs(repo_root=repo_root)
    if int(prerequisite_result.get("rc", 0) or 0) != 0:
        return prerequisite_result
    return compass_refresh_runtime.run_refresh(
        repo_root=repo_root,
        requested_profile=compass_refresh_contract.DEFAULT_REFRESH_PROFILE,
        requested_runtime_mode=normalized_runtime_mode,
        wait=True,
        status_only=False,
        emit_output=True,
        skip_settlement=True,
    )


def ensure_compass_dashboard_inputs(*, repo_root: Path) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    bug_index = root / "odylith" / "casebook" / "bugs" / "INDEX.md"
    if not bug_index.is_file():
        try:
            from odylith.runtime.governance import sync_casebook_bug_index

            sync_casebook_bug_index.sync_casebook_bug_index(repo_root=root)
        except Exception as exc:
            return {
                "rc": 1,
                "status": "failed",
                "next_command": display_command("casebook", "refresh", "--repo-root", "."),
                "failed_step": "Create the Casebook bug index required by Compass.",
                "detail": f"{type(exc).__name__}: {exc}".strip(),
            }

    traceability_graph = root / "odylith" / "radar" / "traceability-graph.v1.json"
    if traceability_graph.is_file():
        return {"rc": 0, "status": "passed"}

    try:
        from odylith.runtime.governance import build_traceability_graph

        captured = io.StringIO()
        with contextlib.redirect_stdout(captured):
            rc = build_traceability_graph.main(
                [
                    "--repo-root",
                    str(root),
                    "--output",
                    "odylith/radar/traceability-graph.v1.json",
                ]
            )
    except Exception as exc:
        return {
            "rc": 1,
            "status": "failed",
            "next_command": display_command("radar", "refresh", "--repo-root", "."),
            "failed_step": "Create the Radar traceability graph required by Compass.",
            "detail": f"{type(exc).__name__}: {exc}".strip(),
        }
    if int(rc or 0) != 0:
        detail = " ".join(captured.getvalue().split())
        return {
            "rc": int(rc or 1),
            "status": "failed",
            "next_command": display_command("radar", "refresh", "--repo-root", "."),
            "failed_step": "Create the Radar traceability graph required by Compass.",
            "detail": detail,
        }
    print("- compass preflight: generated missing Radar traceability graph")
    return {"rc": 0, "status": "passed"}
