"""Watch prompt-transaction inputs and refresh Compass/Radar renders on change.

This utility is local-only and intentionally non-destructive. It fingerprints
the deterministic Compass/Radar source inputs (or daemon projection state when
explicitly requested) and reruns:

- `odylith sync --repo-root . --force`
- the focused Compass/Radar renderers

only when the fingerprint changes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
from pathlib import Path
import subprocess
import time
from typing import Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine
from odylith.runtime.context_engine import odylith_context_engine_store


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith compass watch-transactions",
        description="Poll prompt-transaction inputs and refresh Compass/Radar views on change.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=25,
        help="Polling interval in seconds (default: 25).",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one fingerprint cycle and exit (useful for smoke checks).",
    )
    parser.add_argument(
        "--runtime-mode",
        choices=("auto", "standalone", "daemon"),
        default="auto",
        help="Use the local runtime-backed in-process refresh path when available.",
    )
    return parser.parse_args(argv)


def _resolve(repo_root: Path, token: str) -> Path:
    path = Path(str(token or "").strip())
    if path.is_absolute():
        return path.resolve()
    return (repo_root / path).resolve()


def _path_fingerprint(repo_root: Path, token: str) -> str:
    path = _resolve(repo_root, token)
    if path.is_dir():
        return odylith_context_cache.fingerprint_tree(path, glob="*")
    return odylith_context_cache.fingerprint_paths([path])


def _fingerprint(repo_root: Path) -> str:
    digest = hashlib.sha256()
    for token in odylith_context_engine_store.watch_targets(repo_root=repo_root):
        rel_path = str(token).strip()
        if not rel_path:
            continue
        digest.update(rel_path.encode("utf-8"))
        digest.update(_path_fingerprint(repo_root, rel_path).encode("utf-8"))
    return digest.hexdigest()


def _run_command(repo_root: Path, command: Sequence[str]) -> int:
    completed = subprocess.run(list(command), cwd=str(repo_root), check=False)
    return int(completed.returncode)


def _refresh_outputs_runtime(repo_root: Path, *, runtime_mode: str) -> int:
    commands: tuple[tuple[str, ...], ...] = (
        (
            "odylith.runtime.surfaces.render_compass_dashboard",
            "--repo-root",
            str(repo_root),
            "--runtime-mode",
            str(runtime_mode),
        ),
        (
            "odylith.runtime.surfaces.render_backlog_ui",
            "--repo-root",
            str(repo_root),
            "--runtime-mode",
            str(runtime_mode),
        ),
    )
    for module_name, *argv in commands:
        module = importlib.import_module(module_name)
        main = getattr(module, "main", None)
        if not callable(main):
            print(f"prompt transaction watcher FAILED while importing: {module_name}")
            return 2
        rc = int(main(list(argv)))
        if rc != 0:
            print(f"prompt transaction watcher FAILED while running: {module_name}")
            return rc
    return 0


def _refresh_outputs(repo_root: Path, *, runtime_mode: str) -> int:
    if str(runtime_mode).strip().lower() != "standalone":
        return _refresh_outputs_runtime(repo_root, runtime_mode=runtime_mode)
    commands: tuple[tuple[str, ...], ...] = (
        ("python", "-m", "odylith.runtime.surfaces.render_compass_dashboard", "--repo-root", str(repo_root)),
        ("python", "-m", "odylith.runtime.surfaces.render_backlog_ui", "--repo-root", str(repo_root)),
    )
    for command in commands:
        rc = _run_command(repo_root, command)
        if rc != 0:
            print(f"prompt transaction watcher FAILED while running: {' '.join(command)}")
            return rc
    return 0


def _runtime_fingerprint(repo_root: Path, *, runtime_mode: str) -> str:
    normalized = str(runtime_mode).strip().lower()
    if normalized == "daemon":
        state = odylith_context_engine._daemon_request(  # noqa: SLF001
            repo_root=repo_root,
            command="status",
            payload={},
            required=True,
        )
        fingerprint = str((state or {}).get("projection_fingerprint", "")).strip()
        if fingerprint:
            return fingerprint
        raise RuntimeError("odylith context engine daemon state unavailable")
    if normalized == "auto" and odylith_context_engine._daemon_socket_available(repo_root=repo_root):  # noqa: SLF001
        state = odylith_context_engine._daemon_request(  # noqa: SLF001
            repo_root=repo_root,
            command="status",
            payload={},
            required=False,
        )
        fingerprint = str((state or {}).get("projection_fingerprint", "")).strip()
        if fingerprint:
            return fingerprint
    try:
        return odylith_context_engine_store.projection_input_fingerprint(repo_root=repo_root)
    except Exception:
        return _fingerprint(repo_root)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    interval_seconds = max(5, int(args.interval_seconds))
    run_once = bool(args.once)
    runtime_mode = str(args.runtime_mode).strip().lower()

    print("prompt transaction watcher started")
    print(f"- repo_root: {repo_root}")
    print(f"- interval_seconds: {interval_seconds}")
    if run_once:
        print("- mode: once")

    previous = ""
    try:
        while True:
            current = (
                _runtime_fingerprint(repo_root, runtime_mode=runtime_mode)
                if runtime_mode != "standalone"
                else _fingerprint(repo_root)
            )
            if current != previous:
                rc = _refresh_outputs(repo_root, runtime_mode=runtime_mode)
                if rc != 0:
                    return rc
                previous = current
                print("prompt transaction watcher refresh passed")
            else:
                print("prompt transaction watcher idle (no relevant changes)")

            if run_once:
                break
            time.sleep(interval_seconds)
    except KeyboardInterrupt:
        print("prompt transaction watcher stopped")
        return 130

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
