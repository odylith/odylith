"""Codex Stop hook logger for meaningful Odylith implementation summaries."""

from __future__ import annotations

import argparse

from odylith.runtime.surfaces import codex_host_shared


def log_codex_stop_summary(repo_root: str = ".", *, message: str) -> bool:
    summary = codex_host_shared.meaningful_stop_summary(message)
    if not summary:
        return False
    return codex_host_shared.run_compass_log(
        project_dir=repo_root,
        summary=summary,
        workstreams=codex_host_shared.extract_workstreams(summary),
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="odylith codex stop-summary",
        description="Log a meaningful Codex stop summary to Compass when present.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root for launcher resolution.")
    args = parser.parse_args(list(argv or []))
    payload = codex_host_shared.load_payload()
    log_codex_stop_summary(args.repo_root, message=str(payload.get("last_assistant_message", "")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
