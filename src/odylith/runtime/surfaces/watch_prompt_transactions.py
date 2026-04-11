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
from typing import Mapping, Sequence

from odylith.runtime.context_engine import odylith_context_cache
from odylith.runtime.context_engine import odylith_context_engine
from odylith.runtime.context_engine import odylith_context_engine_store
from odylith.runtime.surfaces import compass_refresh_runtime

_DEFAULT_INTERVAL_SECONDS = 25
_DAEMON_WAIT_TIMEOUT_SECONDS = 60.0
_LOCAL_WATCHER_POLL_SECONDS = 25
_LOCAL_WATCHER_STOP_FILE = ".odylith/runtime/watch-prompt-transactions.stop"


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith compass watch-transactions",
        description="Refresh Compass/Radar views when the projection fingerprint changes.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument(
        "--interval-seconds",
        type=int,
        default=_DEFAULT_INTERVAL_SECONDS,
        help="Last-resort coarse poll interval in seconds when no push-backed watcher is available (default: 25).",
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
    refresh_result = compass_refresh_runtime.run_refresh(
        repo_root=repo_root,
        requested_profile="shell-safe",
        requested_runtime_mode=runtime_mode,
        wait=True,
        status_only=False,
        emit_output=True,
    )
    if int(refresh_result.get("rc", 0) or 0) != 0:
        print("prompt transaction watcher FAILED while refreshing Compass")
        return int(refresh_result.get("rc", 0) or 0)
    commands: tuple[tuple[str, ...], ...] = (
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
    refresh_result = compass_refresh_runtime.run_refresh(
        repo_root=repo_root,
        requested_profile="shell-safe",
        requested_runtime_mode=runtime_mode,
        wait=True,
        status_only=False,
        emit_output=True,
    )
    if int(refresh_result.get("rc", 0) or 0) != 0:
        print("prompt transaction watcher FAILED while refreshing Compass")
        return int(refresh_result.get("rc", 0) or 0)
    commands: tuple[tuple[str, ...], ...] = (
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


def _wait_for_runtime_change(
    repo_root: Path,
    *,
    runtime_mode: str,
    since_fingerprint: str,
    interval_seconds: int,
    local_watcher: object | None,
) -> tuple[bool, str]:
    normalized = str(runtime_mode).strip().lower()
    daemon_available = normalized == "daemon" or (
        normalized == "auto" and odylith_context_engine._daemon_socket_available(repo_root=repo_root)  # noqa: SLF001
    )
    if daemon_available:
        response = odylith_context_engine._daemon_request(  # noqa: SLF001
            repo_root=repo_root,
            command="wait-projection-change",
            payload={
                "since_fingerprint": str(since_fingerprint or "").strip(),
                "timeout_seconds": _DAEMON_WAIT_TIMEOUT_SECONDS,
            },
            required=normalized == "daemon",
            timeout_seconds=_DAEMON_WAIT_TIMEOUT_SECONDS + 5.0,
        )
        if isinstance(response, Mapping):
            fingerprint = str(response.get("projection_fingerprint", "")).strip()
            changed = bool(response.get("changed")) or (bool(fingerprint) and fingerprint != str(since_fingerprint or "").strip())
            return changed, fingerprint
    if local_watcher is not None:
        changed = bool(
            local_watcher.wait_for_change(
                stop_file=(repo_root / _LOCAL_WATCHER_STOP_FILE).resolve(),
                poll_seconds=max(5, int(_LOCAL_WATCHER_POLL_SECONDS)),
            )
        )
        return changed, ""
    time.sleep(max(5, int(interval_seconds)))
    return False, ""


def _build_local_runtime_watcher(repo_root: Path) -> object | None:
    report = odylith_context_engine_store.watcher_backend_report(repo_root=repo_root)
    backend = str(report.get("preferred_backend", "")).strip().lower() or "poll"
    if backend == "poll" and not bool(report.get("bootstrap_recommended")):
        return None
    requested_backend = "git-fsmonitor" if backend == "poll" and bool(report.get("bootstrap_recommended")) else "auto"
    try:
        return odylith_context_engine._build_runtime_watcher(repo_root=repo_root, backend=requested_backend)  # noqa: SLF001
    except Exception:
        return None


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    repo_root = Path(str(args.repo_root)).expanduser().resolve()
    interval_seconds = max(5, int(args.interval_seconds))
    run_once = bool(args.once)
    runtime_mode = str(args.runtime_mode).strip().lower()
    local_watcher = _build_local_runtime_watcher(repo_root) if runtime_mode != "daemon" else None

    print("prompt transaction watcher started")
    print(f"- repo_root: {repo_root}")
    print(f"- coarse_poll_seconds: {interval_seconds}")
    if run_once:
        print("- mode: once")

    previous = ""
    hinted_current = ""
    try:
        while True:
            current = str(hinted_current or "").strip()
            hinted_current = ""
            if not current:
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

            if run_once:
                break
            _changed, hinted_current = _wait_for_runtime_change(
                repo_root,
                runtime_mode=runtime_mode,
                since_fingerprint=previous,
                interval_seconds=interval_seconds,
                local_watcher=local_watcher,
            )
    except KeyboardInterrupt:
        print("prompt transaction watcher stopped")
        return 130
    finally:
        if local_watcher is not None:
            close = getattr(local_watcher, "close", None)
            if callable(close):
                close()

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
