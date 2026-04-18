"""Capture operator narrative updates into Compass and refresh runtime snapshots.

This wrapper provides a higher-level "Update Compass" command contract on top of
the Compass timeline event logger. It is designed for concise operator
statements that should appear in timeline audits and standup digest narratives.

Invariants:
- Timeline events remain local-only runtime artifacts.
- Input validation is fail-closed for empty summaries and invalid workstream IDs.
- Compass refresh is enabled by default so updates become visible immediately.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from odylith.runtime.common import agent_runtime_contract
from odylith.runtime.common import log_compass_timeline_event as timeline_logger
from odylith.runtime.surfaces import compass_refresh_runtime
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.surfaces import surface_path_helpers


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    default_author, default_source = agent_runtime_contract.default_event_metadata()
    parser = argparse.ArgumentParser(
        prog="odylith compass update",
        description="Capture Update Compass statements into timeline + standup inputs.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--stream",
        default=agent_runtime_contract.AGENT_STREAM_PATH,
        help="Compass local timeline stream path.",
    )
    parser.add_argument(
        "--decision",
        action="append",
        default=[],
        help="Decision narrative (repeatable).",
    )
    parser.add_argument(
        "--implementation",
        action="append",
        default=[],
        help="Implementation narrative (repeatable).",
    )
    parser.add_argument(
        "--statement",
        action="append",
        default=[],
        help="General narrative statement (repeatable).",
    )
    parser.add_argument(
        "--update",
        action="append",
        default=[],
        help="Alias for --statement (repeatable).",
    )
    parser.add_argument(
        "--workstream",
        action="append",
        default=[],
        help="Linked workstream ID (`B-xxx`). Repeatable.",
    )
    parser.add_argument(
        "--artifact",
        action="append",
        default=[],
        help="Linked artifact path (repeatable).",
    )
    parser.add_argument(
        "--component",
        action="append",
        default=[],
        help="Linked component id/alias (repeatable).",
    )
    parser.add_argument(
        "--manifest",
        default=timeline_logger.component_registry.DEFAULT_MANIFEST_PATH,
        help="Component registry manifest path.",
    )
    parser.add_argument(
        "--catalog",
        default=timeline_logger.component_registry.DEFAULT_CATALOG_PATH,
        help="Mermaid catalog path for component inference.",
    )
    parser.add_argument(
        "--ideas-root",
        default=timeline_logger.component_registry.DEFAULT_IDEAS_ROOT,
        help="Backlog ideas root for impacted-component inference.",
    )
    parser.add_argument("--author", default=default_author, help="Author label.")
    parser.add_argument("--source", default=default_source, help="Source label.")
    parser.add_argument(
        "--session-id",
        default="",
        help="Optional session identifier for grouping prompt transactions.",
    )
    parser.add_argument(
        "--transaction-id",
        default="",
        help="Optional prompt transaction identifier shared across appended events.",
    )
    parser.add_argument(
        "--transaction-seq-start",
        type=int,
        default=None,
        help="Optional starting sequence number; increments for each appended event.",
    )
    parser.add_argument(
        "--context",
        default="",
        help="Optional prompt/execution context text for transaction cards.",
    )
    parser.add_argument(
        "--headline-hint",
        default="",
        help="Optional concise transaction headline hint shared across appended events.",
    )
    parser.add_argument(
        "--transaction-boundary",
        choices=("", "start", "end"),
        default="",
        help="Optional transaction boundary marker applied to first/last appended event.",
    )
    parser.add_argument(
        "--ts-iso",
        default="",
        help="Optional ISO timestamp shared across appended events.",
    )
    parser.add_argument("--proof-lane", default="", help="Optional proof lane id shared across appended events.")
    parser.add_argument("--proof-fingerprint", default="", help="Optional live failure fingerprint shared across appended events.")
    parser.add_argument("--proof-phase", default="", help="Optional proof frontier or phase label shared across appended events.")
    parser.add_argument("--evidence-tier", default="", help="Optional proof evidence tier shared across appended events.")
    parser.add_argument("--proof-status", default="", choices=("", *timeline_logger.PROOF_STATUSES), help="Optional proof status shared across appended events.")
    parser.add_argument("--work-category", default="", choices=("", *timeline_logger.WORK_CATEGORIES), help="Optional proof work category shared across appended events.")
    parser.add_argument("--local-head", default="", help="Optional deployment-truth local HEAD shared across appended events.")
    parser.add_argument("--pushed-head", default="", help="Optional deployment-truth pushed branch HEAD shared across appended events.")
    parser.add_argument("--published-source-commit", default="", help="Optional deployment-truth published source commit shared across appended events.")
    parser.add_argument("--runner-fingerprint", default="", help="Optional deployment-truth runner fingerprint shared across appended events.")
    parser.add_argument("--last-live-failing-commit", default="", help="Optional deployment-truth last live failing commit shared across appended events.")
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Skip compass render refresh after appending events.",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use incremental runtime refresh when available for local Compass updates.",
    )
    return parser.parse_args(argv)


def _normalize_messages(values: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in values:
        token = " ".join(str(raw or "").split()).strip()
        if not token or token in seen:
            continue
        seen.add(token)
        normalized.append(token)
    return normalized


def _event_requests(args: argparse.Namespace) -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    rows.extend(("decision", item) for item in _normalize_messages(list(args.decision)))
    rows.extend(("implementation", item) for item in _normalize_messages(list(args.implementation)))
    statement_values = _normalize_messages(list(args.statement) + list(args.update))
    rows.extend(("statement", item) for item in statement_values)
    return rows


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    stream_path = surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=str(args.stream))
    manifest_token = str(args.manifest).strip()
    manifest_path = (
        timeline_logger.component_registry.default_manifest_path(repo_root=repo_root)
        if manifest_token == timeline_logger.component_registry.DEFAULT_MANIFEST_PATH
        else surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=manifest_token)
    )

    requests = _event_requests(args)
    if not requests:
        print("update compass FAILED")
        print("- provide at least one of: --decision, --implementation, --statement, --update")
        return 2

    appended: list[dict[str, object]] = []
    seq_start = args.transaction_seq_start
    for idx, (kind, summary) in enumerate(requests):
        seq_value = (seq_start + idx) if isinstance(seq_start, int) else None
        boundary_value = ""
        if str(args.transaction_boundary) in {"start", "end"}:
            boundary_token = str(args.transaction_boundary)
            if boundary_token == "start" and idx == 0:
                boundary_value = "start"
            elif boundary_token == "end" and idx == (len(requests) - 1):
                boundary_value = "end"
        try:
            payload = timeline_logger.append_event(
                repo_root=repo_root,
                stream_path=stream_path,
                kind=kind,
                summary=summary,
                workstream_values=list(args.workstream),
                artifact_values=list(args.artifact),
                component_values=list(args.component),
                author=str(args.author),
                source=str(args.source),
                manifest_path=manifest_path,
                catalog_path=surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=str(args.catalog)),
                ideas_root=surface_path_helpers.resolve_repo_path(repo_root=repo_root, token=str(args.ideas_root)),
                session_id=str(args.session_id),
                transaction_id=str(args.transaction_id),
                transaction_seq=seq_value,
                context=str(args.context),
                headline_hint=str(args.headline_hint),
                transaction_boundary=boundary_value,
                ts_iso=str(args.ts_iso),
                proof_lane=str(args.proof_lane),
                proof_fingerprint=str(args.proof_fingerprint),
                proof_phase=str(args.proof_phase),
                evidence_tier=str(args.evidence_tier),
                proof_status=str(args.proof_status),
                work_category=str(args.work_category),
                deployment_truth={
                    "local_head": str(args.local_head),
                    "pushed_head": str(args.pushed_head),
                    "published_source_commit": str(args.published_source_commit),
                    "runner_fingerprint": str(args.runner_fingerprint),
                    "last_live_failing_commit": str(args.last_live_failing_commit),
                },
            )
        except ValueError as exc:
            print("update compass FAILED")
            print(f"- {exc}")
            return 2
        appended.append(payload)

    odylith_context_engine_store.append_runtime_event(
        repo_root=repo_root,
        event_type="compass_update",
        payload={
            "events_appended": len(appended),
            "stream": str(stream_path.relative_to(repo_root)) if stream_path.is_absolute() else str(stream_path),
        },
    )

    if not args.no_render:
        refresh_result = compass_refresh_runtime.run_refresh(
            repo_root=repo_root,
            requested_profile="shell-safe",
            requested_runtime_mode=str(args.runtime_mode),
            wait=True,
            status_only=False,
            emit_output=True,
        )
        rc = int(refresh_result.get("rc", 0) or 0)
        if rc != 0:
            print("update compass FAILED")
            print("- timeline events were appended, but Compass render failed")
            return rc

    kinds = ", ".join(str(row.get("kind", "")).strip() for row in appended)
    print("update compass passed")
    print(f"- stream: {stream_path}")
    print(f"- events_appended: {len(appended)}")
    print(f"- kinds: {kinds}")
    print(f"- render_refreshed: {'no' if args.no_render else 'yes'}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
