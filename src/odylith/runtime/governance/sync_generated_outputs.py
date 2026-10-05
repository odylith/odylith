"""Generated-output inventory and git-state helpers for `odylith sync`."""

from __future__ import annotations

from pathlib import Path
import stat
import subprocess

from odylith.runtime.domain_intelligence.greenfield_repository_write_set import greenfield_repository_layout


def surface_render_outputs(surface: str, *, repo_root: Path) -> tuple[str, ...]:
    outputs = {
        "tooling_shell": ("odylith/index.html", "odylith/tooling-payload.v1.js", "odylith/tooling-app.v1.js"),
        "radar": (
            "odylith/radar/radar.html",
            "odylith/radar/backlog-payload.v1.js",
            "odylith/radar/backlog-app.v1.js",
            "odylith/radar/traceability-graph.v1.json",
        ),
        "compass": (
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
        ),
        "atlas": ("odylith/atlas/atlas.html", "odylith/atlas/mermaid-payload.v1.js", "odylith/atlas/mermaid-app.v1.js"),
        "registry": ("odylith/registry/registry.html", "odylith/registry/registry-payload.v1.js", "odylith/registry/registry-app.v1.js"),
        "casebook": ("odylith/casebook/casebook.html", "odylith/casebook/casebook-payload.v1.js", "odylith/casebook/casebook-app.v1.js"),
    }.get(surface, ())
    if surface != "tooling_shell":
        return outputs
    layout = greenfield_repository_layout(repo_root)
    return tuple(layout.target_path(path).relative_to(layout.repo_root).as_posix() for path in outputs)


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
        "odylith/tooling-shell.html",
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


def _verified_maintainer_shell_export(repo_root: Path) -> bool:
    """Accept only the exact published logical shell staged for a source checkpoint."""
    from odylith.install import manager
    from odylith.runtime.domain_intelligence import greenfield_generation_state as publication
    from odylith.runtime.domain_intelligence import greenfield_generation_store as generations

    try:
        status = manager.version_status(repo_root=repo_root, deep_integrity=False)
        if (status.repo_role != manager.PRODUCT_REPO_ROLE
                or status.posture != manager.DETACHED_SOURCE_LOCAL_POSTURE
                or status.runtime_source != manager.SOURCE_CHECKOUT_RUNTIME_SOURCE):
            return False
        before = publication.active_generation_identity(repo_root)
        generations.require_greenfield_working_generation(repo_root)
        shell = greenfield_repository_layout(repo_root).target_path("odylith/index.html")
        contents, mode = shell.read_bytes(), stat.S_IMODE(shell.stat().st_mode)
        staged = subprocess.run(
            ["git", "-C", str(repo_root), "show", ":odylith/index.html"],
            capture_output=True, check=False,
        )
        staged_mode = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "--format=%(objectmode)", "--", "odylith/index.html"],
            capture_output=True, check=False,
        )
        return (staged.returncode == staged_mode.returncode == 0
                and staged.stdout == contents
                and staged_mode.stdout == (b"100755\n" if mode & stat.S_IXUSR else b"100644\n")
                and shell.read_bytes() == contents and stat.S_IMODE(shell.stat().st_mode) == mode
                and publication.active_generation_identity(repo_root) == before)
    except (OSError, RuntimeError, ValueError):
        return False


def git_commit_ready_generated_outputs(*, repo_root: Path) -> str:
    lines = [
        line
        for line in git_status_generated_outputs(repo_root=repo_root)
        if _commit_ready_dirty_status_line(line)
    ]
    if (any(line[3:] == "odylith/index.html" or line == "?? odylith/tooling-shell.html" for line in lines)
            and _verified_maintainer_shell_export(repo_root)):
        lines = [line for line in lines if line[3:] != "odylith/index.html"
                 and line != "?? odylith/tooling-shell.html"]
    return "\n".join(lines).rstrip()
