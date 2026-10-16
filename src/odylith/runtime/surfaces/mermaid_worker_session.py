"""Mermaid Worker Session helpers for the Odylith surfaces layer."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import select
import subprocess
import time
from typing import Any, Mapping, Sequence, TextIO

_MERMAID_WORKER_SCRIPT = Path(__file__).with_name("assets") / "mermaid_cli_worker.mjs"
_MERMAID_PACKAGE_ROOT_CACHE: dict[str, Path] = {}
_HEARTBEAT_INTERVAL_SECONDS = 10.0
_NPX_RESOLUTION_TIMEOUT_SECONDS = 12.0


class MermaidDiagramValidationError(RuntimeError):
    def __init__(
        self,
        *,
        diagram_id: str,
        source_mmd: str,
        line: int | None = None,
        line_context: str = "",
        detail: str = "",
    ) -> None:
        self.diagram_id = str(diagram_id or "").strip() or "unknown-diagram"
        self.source_mmd = str(source_mmd or "").strip()
        self.line = int(line) if line is not None else None
        self.line_context = str(line_context or "").rstrip()
        self.detail = str(detail or "").strip()
        location = self.source_mmd
        if self.line is not None and self.line > 0:
            location = f"{location}:{self.line}"
        super().__init__(f"{self.diagram_id} failed: {location}")


def _resolve_mermaid_cli_root(*, repo_root: Path, cli_version: str) -> Path:
    cache_key = str(cli_version).strip() or "default"
    cached = _MERMAID_PACKAGE_ROOT_CACHE.get(cache_key)
    if cached is not None and cached.is_dir():
        return cached
    for candidate in _local_mermaid_package_candidates(repo_root=repo_root, cli_version=cli_version):
        _MERMAID_PACKAGE_ROOT_CACHE[cache_key] = candidate
        return candidate
    if os.environ.get("ODYLITH_ALLOW_MERMAID_NPX_INSTALL", "").strip().lower() not in {"1", "true", "yes"}:
        raise RuntimeError(
            f"Mermaid CLI {cli_version} is not available from ODYLITH_MERMAID_CLI_ROOT, local node_modules, "
            "global mmdc, or the npm cache; set ODYLITH_ALLOW_MERMAID_NPX_INSTALL=1 to allow an online npx install."
        )
    cmd = [
        "npx",
        "-y",
        "-p",
        f"@mermaid-js/mermaid-cli@{cli_version}",
        "sh",
        "-lc",
        'realpath "$(command -v mmdc)"',
    ]
    result = subprocess.run(
        cmd,
        cwd=str(repo_root),
        check=True,
        capture_output=True,
        text=True,
        timeout=_NPX_RESOLUTION_TIMEOUT_SECONDS,
    )
    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    if not lines:
        raise RuntimeError(f"unable to resolve Mermaid CLI root for version {cli_version}")
    cli_entry = Path(lines[-1]).resolve()
    package_root = cli_entry.parent.parent
    if not package_root.is_dir():
        raise RuntimeError(f"Mermaid CLI package root missing: {package_root}")
    _MERMAID_PACKAGE_ROOT_CACHE[cache_key] = package_root
    return package_root


def resolve_mermaid_cli_bin(*, repo_root: Path, cli_version: str) -> Path:
    package_root = _resolve_mermaid_cli_root(repo_root=repo_root, cli_version=cli_version)
    local_bin = package_root.parent.parent / ".bin" / "mmdc"
    if local_bin.is_file():
        return local_bin
    source_bin = package_root / "src" / "cli.js"
    if source_bin.is_file():
        return source_bin
    raise RuntimeError(f"Mermaid CLI executable missing under {package_root}")


def _local_mermaid_package_candidates(*, repo_root: Path, cli_version: str) -> tuple[Path, ...]:
    requested_version = str(cli_version or "").strip()
    candidates: list[Path] = []
    env_root = os.environ.get("ODYLITH_MERMAID_CLI_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())
    root = Path(repo_root).resolve()
    candidates.extend(
        [
            root / "node_modules" / "@mermaid-js" / "mermaid-cli",
            root / "odylith" / "node_modules" / "@mermaid-js" / "mermaid-cli",
        ]
    )
    global_bin = shutil.which("mmdc")
    if global_bin:
        global_root = _package_root_from_path(Path(global_bin).resolve())
        if global_root is not None:
            candidates.append(global_root)
    cache_root = Path(os.environ.get("npm_config_cache", "") or Path.home() / ".npm").expanduser()
    candidates.extend(_npm_cache_mermaid_roots(cache_root=cache_root, cli_version=requested_version))
    seen: set[Path] = set()
    exact: list[Path] = []
    compatible: list[Path] = []
    for candidate in candidates:
        path = Path(candidate).expanduser().resolve()
        if path in seen:
            continue
        seen.add(path)
        version = _mermaid_package_version(path)
        if not version:
            continue
        if requested_version and version == requested_version:
            exact.append(path)
        elif not requested_version:
            compatible.append(path)
    return tuple(exact or compatible)


def _npm_cache_mermaid_roots(*, cache_root: Path, cli_version: str) -> tuple[Path, ...]:
    npx_root = Path(cache_root) / "_npx"
    if not npx_root.is_dir():
        return ()
    rows: list[tuple[float, Path]] = []
    for package_json in npx_root.glob("*/node_modules/@mermaid-js/mermaid-cli/package.json"):
        root = package_json.parent
        version = _mermaid_package_version(root)
        if cli_version and version != cli_version:
            continue
        try:
            mtime = package_json.stat().st_mtime
        except OSError:
            mtime = 0.0
        rows.append((mtime, root))
    rows.sort(key=lambda item: item[0], reverse=True)
    return tuple(root for _mtime, root in rows)


def _package_root_from_path(path: Path) -> Path | None:
    for candidate in [path, *path.parents]:
        if _mermaid_package_version(candidate):
            return candidate
    return None


def _mermaid_package_version(path: Path) -> str:
    package_json = Path(path) / "package.json"
    if not package_json.is_file():
        return ""
    try:
        payload = json.loads(package_json.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ""
    if str(payload.get("name", "")).strip() != "@mermaid-js/mermaid-cli":
        return ""
    return str(payload.get("version", "")).strip()


def _worker_job(job: Mapping[str, str]) -> dict[str, str]:
    return {
        "diagram_id": str(job.get("diagram_id", "")).strip(),
        "source_mmd": str(job.get("source_mmd", "")).strip(),
        "source_svg": str(job.get("source_svg", "")).strip(),
        "source_png": str(job.get("source_png", "")).strip(),
    }


class _MermaidWorkerSession:
    """Keep one Node/Chromium worker alive for a whole diagram batch."""

    def __init__(self, *, repo_root: Path, cli_version: str) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.cli_version = str(cli_version).strip()
        self.process: subprocess.Popen[str] | None = None

    def __enter__(self) -> _MermaidWorkerSession:
        package_root = _resolve_mermaid_cli_root(repo_root=self.repo_root, cli_version=self.cli_version)
        worker_script = Path(_MERMAID_WORKER_SCRIPT).resolve()
        if not worker_script.is_file():
            raise RuntimeError(f"Mermaid worker script missing: {worker_script}")
        self.process = subprocess.Popen(
            [
                "node",
                str(worker_script),
                "--mermaid-cli-root",
                str(package_root),
            ],
            cwd=str(self.repo_root),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return self

    def __exit__(self, exc_type, exc, tb) -> None:  # type: ignore[no-untyped-def]
        self._shutdown()

    def _ensure_stream(self, stream: TextIO | None, *, name: str) -> TextIO:
        if stream is None:
            raise RuntimeError(f"Mermaid worker missing {name} stream")
        return stream

    def _request(
        self,
        payload: Mapping[str, Any],
        *,
        timeout_seconds: float = 60.0,
        heartbeat_label: str = "",
    ) -> dict[str, Any]:
        process = self.process
        if process is None:
            raise RuntimeError("Mermaid worker is not running")
        stdin = self._ensure_stream(process.stdin, name="stdin")
        stdout = self._ensure_stream(process.stdout, name="stdout")
        stdin.write(json.dumps(payload) + "\n")
        stdin.flush()
        started_at = time.monotonic()
        elapsed = 0.0
        while True:
            remaining = float(timeout_seconds) - elapsed
            if remaining <= 0:
                raise RuntimeError(f"Mermaid worker timed out after {int(timeout_seconds)}s")
            ready, _unused_write, _unused_error = select.select(
                [stdout],
                [],
                [],
                min(_HEARTBEAT_INTERVAL_SECONDS, remaining),
            )
            if ready:
                break
            elapsed = time.monotonic() - started_at
            label = heartbeat_label or "Mermaid worker"
            print(f"- heartbeat: waiting on {label} ({int(elapsed)}s)")
        response_line = stdout.readline()
        if response_line:
            response = json.loads(response_line)
            if not isinstance(response, dict):
                raise RuntimeError("Mermaid worker returned a non-object response")
            if not bool(response.get("ok", False)):
                if str(response.get("name", "")).strip() == "MermaidValidationError":
                    line_value = response.get("line")
                    line = None
                    if isinstance(line_value, int):
                        line = line_value
                    elif isinstance(line_value, str) and line_value.strip().isdigit():
                        line = int(line_value.strip())
                    raise MermaidDiagramValidationError(
                        diagram_id=str(response.get("diagram_id", "")).strip(),
                        source_mmd=str(response.get("source_mmd", "")).strip(),
                        line=line,
                        line_context=str(response.get("line_context", "")).rstrip(),
                        detail=str(response.get("detail", "")).strip(),
                    )
                raise RuntimeError(str(response.get("error", "Mermaid worker failed")))
            return response
        if process.poll() is None:
            raise RuntimeError("Mermaid worker stopped responding")
        stderr = self._read_stderr()
        raise RuntimeError(stderr or "Mermaid worker exited without a response")

    def _read_stderr(self) -> str:
        process = self.process
        if process is None or process.stderr is None:
            return ""
        try:
            return process.stderr.read().strip()
        except OSError:
            return ""

    def render_one(self, *, job: Mapping[str, str], label: str = "", timeout_seconds: float = 60.0) -> None:
        resolved_label = label or str(job.get("diagram_id", "")).strip() or str(job.get("source_mmd", "")).strip()
        self._request(
            {
                "command": "render",
                "jobs": [_worker_job(job)],
            },
            timeout_seconds=timeout_seconds,
            heartbeat_label=f"Mermaid worker render for {resolved_label or 'unknown-diagram'}",
        )

    def validate_many(self, *, jobs: Sequence[Mapping[str, str]]) -> None:
        self._request(
            {
                "command": "validate",
                "jobs": [_worker_job(job) for job in jobs],
            },
            heartbeat_label="Mermaid worker syntax preflight",
        )

    def _shutdown(self) -> None:
        process = self.process
        self.process = None
        if process is None:
            return
        try:
            if process.stdin is not None and process.poll() is None:
                process.stdin.write(json.dumps({"command": "shutdown"}) + "\n")
                process.stdin.flush()
        except OSError:
            pass
        try:
            process.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
