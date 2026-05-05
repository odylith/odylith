"""Generated-output inventory and git-state helpers for `odylith sync`."""

from __future__ import annotations

from pathlib import Path
import subprocess


def generated_output_targets() -> tuple[str, ...]:
    return (
        "odylith/radar/radar.html",
        "odylith/radar/backlog-payload.v1.js",
        "odylith/radar/backlog-app.v1.js",
        "odylith/radar/backlog-detail-shard-*.v1.js",
        "odylith/radar/backlog-document-shard-*.v1.js",
        "odylith/radar/standalone-pages.v1.js",
        "odylith/radar/traceability-graph.v1.json",
        "odylith/radar/traceability-autofix-report.v1.json",
        "odylith/atlas/atlas.html",
        "odylith/atlas/mermaid-payload.v1.js",
        "odylith/atlas/mermaid-app.v1.js",
        "odylith/compass/compass.html",
        "odylith/compass/compass-payload.v1.js",
        "odylith/compass/compass-app.v1.js",
        "odylith/compass/compass-style-base.v1.css",
        "odylith/compass/compass-style-execution-waves.v1.css",
        "odylith/compass/compass-style-surface.v1.css",
        "odylith/compass/compass-shared.v1.js",
        "odylith/compass/compass-state.v1.js",
        "odylith/compass/compass-summary.v1.js",
        "odylith/compass/compass-timeline.v1.js",
        "odylith/compass/compass-waves.v1.js",
        "odylith/compass/compass-workstreams.v1.js",
        "odylith/compass/compass-ui-runtime.v1.js",
        "odylith/registry/registry.html",
        "odylith/registry/registry-payload.v1.js",
        "odylith/registry/registry-app.v1.js",
        "odylith/casebook/casebook.html",
        "odylith/casebook/casebook-payload.v1.js",
        "odylith/casebook/casebook-app.v1.js",
        "odylith/casebook/casebook-detail-shard-*.v1.js",
        "odylith/index.html",
        "odylith/tooling-payload.v1.js",
        "odylith/tooling-app.v1.js",
        "odylith/runtime/delivery_intelligence.v4.json",
        "odylith/runtime/source/optimization-evaluation-corpus.v1.json",
        "odylith/atlas/source/catalog/diagrams.v1.json",
        "odylith/atlas/source/*.svg",
        "odylith/atlas/source/*.png",
        "odylith/registry/registry-detail-shard-*.v1.js",
    )


def git_status_generated_outputs(*, repo_root: Path) -> list[str]:
    completed = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "status",
            "--porcelain",
            "--untracked-files=all",
            "--",
            *generated_output_targets(),
        ],
        capture_output=True,
        check=False,
        text=True,
    )
    return [line for line in str(completed.stdout or "").splitlines() if line]


def git_dirty_generated_outputs(*, repo_root: Path) -> str:
    return "\n".join(git_status_generated_outputs(repo_root=repo_root)).rstrip()


def _commit_ready_dirty_status_line(line: str) -> bool:
    status = line[:2]
    if status == "??":
        return True
    if len(status) < 2:
        return True
    return status[1] != " "


def git_commit_ready_generated_outputs(*, repo_root: Path) -> str:
    lines = [
        line
        for line in git_status_generated_outputs(repo_root=repo_root)
        if _commit_ready_dirty_status_line(line)
    ]
    return "\n".join(lines).rstrip()
