"""Claude Code PostToolUse hook: governance refresh after Write/Edit/MultiEdit.

When Claude Code finishes a ``Write``, ``Edit``, or ``MultiEdit`` tool
call, the ``PostToolUse`` hook fires with the file path that was
edited. This baked module mirrors the legacy
``.claude/hooks/refresh-governance-after-edit.py`` script. If the edited
path is inside one of the governed Odylith source-of-truth subtrees
(``odylith/radar/source/``, ``odylith/technical-plans/``,
``odylith/casebook/bugs/``, ``odylith/registry/source/``,
``odylith/atlas/source/``), it runs ``odylith sync --impact-mode
selective <path>`` to keep the derived dashboards aligned and emits a
``systemMessage`` payload describing the result.

The hook never blocks the edit. It always exits 0; on failure it emits
a fail-soft ``systemMessage`` describing the exit code so the operator
can recover manually if needed.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any
from typing import Mapping

from odylith.runtime.intervention_engine import conversation_surface
from odylith.runtime.intervention_engine import host_surface_runtime
from odylith.runtime.intervention_engine import surface_runtime as intervention_surface_runtime
from odylith.runtime.surfaces import claude_host_shared


# Kept as module-level aliases for tests and call-sites that imported these
# names before the governed-edit predicate was promoted to shared host state.
# New code should use ``claude_host_shared.GOVERNED_SOURCE_PREFIXES`` and
# ``claude_host_shared.GOVERNED_IGNORED_BASENAMES`` directly.
_GOVERNANCE_PREFIXES: tuple[str, ...] = claude_host_shared.GOVERNED_SOURCE_PREFIXES
_IGNORED_BASENAMES: frozenset[str] = claude_host_shared.GOVERNED_IGNORED_BASENAMES


def edited_path(*, payload: dict, project_dir: Path | str) -> str:
    """Return the path-relative-to-project of the edited file, or ``""``."""
    if not isinstance(payload, dict):
        return ""
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    raw = str(tool_input.get("file_path", "")).strip()
    if not raw:
        return ""
    project = Path(project_dir).expanduser().resolve()
    candidate = Path(raw)
    resolved = candidate.resolve() if candidate.is_absolute() else (project / candidate).resolve()
    try:
        return resolved.relative_to(project).as_posix()
    except ValueError:
        return ""


def should_refresh(path_token: str) -> bool:
    """Return True if the edited path is inside a governed Odylith subtree."""
    return claude_host_shared.should_refresh_governed_edit(path_token)


def refresh_governance(*, project_dir: Path | str, path_token: str) -> dict[str, str]:
    """Run ``odylith sync --impact-mode selective <path>`` and return the systemMessage."""
    project = Path(project_dir).expanduser().resolve()
    completed = claude_host_shared.run_odylith(
        project_dir=project,
        args=[
            "sync",
            "--repo-root",
            str(project),
            "--impact-mode",
            "selective",
            path_token,
        ],
        timeout=180,
    )
    if completed is None:
        return {
            "systemMessage": (
                f"Odylith governance refresh skipped after editing {path_token}: "
                "the repo-local launcher was not available."
            )
        }
    if completed.returncode == 0:
        return {"systemMessage": f"Odylith governance refresh completed after editing {path_token}."}
    detail = "\n".join(
        line.strip()
        for line in (completed.stderr or completed.stdout or "").splitlines()[-8:]
        if line.strip()
    )
    if not detail:
        detail = f"exit code {completed.returncode}"
    return {"systemMessage": f"Odylith governance refresh failed after editing {path_token}: {detail}"}


def _post_edit_bundle(
    *,
    project_dir: Path,
    path_token: str,
    session_id: str = "",
    bundle_override: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(bundle_override, Mapping):
        return dict(bundle_override)
    if not _normalize_string(path_token):
        return {}
    return host_surface_runtime.compose_host_conversation_bundle(
        repo_root=project_dir,
        host_family="claude",
        turn_phase="post_edit_checkpoint",
        session_id=session_id,
        changed_paths=[path_token],
    )


def _normalize_string(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith claude post-edit-checkpoint",
        description="Refresh Odylith governance dashboards after a Claude Write/Edit/MultiEdit tool call.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for Odylith governance refresh.")
    parser.add_argument(
        "--payload",
        default="",
        help="Optional explicit Claude PostToolUse payload JSON (defaults to stdin).",
    )
    args = parser.parse_args(list(argv or sys.argv[1:]))
    repo_root = claude_host_shared.resolve_repo_root(args.repo_root)
    raw = args.payload if args.payload else None
    payload = claude_host_shared.load_payload(raw)
    path_token = edited_path(payload=payload, project_dir=repo_root)
    session_id = claude_host_shared.hook_session_id(payload)
    governance_result = refresh_governance(project_dir=repo_root, path_token=path_token) if should_refresh(path_token) else {}
    bundle = _post_edit_bundle(
        project_dir=repo_root,
        path_token=path_token,
        session_id=session_id,
    )
    developer_context = host_surface_runtime.render_developer_context(
        bundle,
        markdown=True,
        include_proposal=True,
        include_closeout=True,
    ) if bundle else ""
    live_intervention = host_surface_runtime.render_visible_live_intervention(
        bundle,
        markdown=True,
        include_proposal=True,
    ) if bundle else ""
    if bundle and developer_context:
        conversation_surface.append_intervention_events(
            repo_root=repo_root,
            bundle=bundle,
            include_proposal=True,
            delivery_channel="system_message_and_assistant_fallback",
            delivery_status="assistant_fallback_ready",
            render_surface="claude_post_tool_use",
        )
    payload_out = host_surface_runtime.claude_post_tool_payload(
        developer_context=developer_context,
        system_message=host_surface_runtime.compose_checkpoint_system_message(
            live_intervention=live_intervention,
            governance_status=_normalize_string(governance_result.get("systemMessage")),
        ),
    )
    if payload_out:
        sys.stdout.write(json.dumps(payload_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
