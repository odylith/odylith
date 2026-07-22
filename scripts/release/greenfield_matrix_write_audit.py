"""Audit installed clarification proposals for attempted repository mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
import errno
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence


AUDIT_ROOT_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_ROOT"
AUDIT_FD_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_FD"


@dataclass(frozen=True)
class WriteAuditEvidence:
    """Redacted outcome from one installed-process filesystem audit."""

    active: bool
    write_attempts: tuple[str, ...] = ()
    subprocess_attempts: tuple[str, ...] = ()
    error: str = ""


@dataclass
class InstalledWriteAudit:
    """Own the parent pipe consumed after one isolated managed-Python process exits."""

    repo_root: Path
    read_fd: int
    write_fd: int
    _finished: WriteAuditEvidence | None = field(default=None, init=False, repr=False)

    def environment(self) -> dict[str, str]:
        return {
            AUDIT_ROOT_ENV: str(self.repo_root),
            AUDIT_FD_ENV: str(self.write_fd),
        }

    @property
    def pass_fds(self) -> tuple[int, ...]:
        return (self.write_fd,)

    def command(self, *, runtime_python: Path, arguments: Sequence[str]) -> list[str]:
        python = Path(runtime_python).expanduser().resolve()
        if not python.is_file():
            raise FileNotFoundError(f"managed runtime python is missing: {python}")
        return [str(python), "-I", "-c", AUDIT_CLI_WRAPPER, *[str(argument) for argument in arguments]]

    def finish(self) -> WriteAuditEvidence:
        if self._finished is not None:
            return self._finished
        try:
            self._close_write_fd()
            self._finished = _read_trace(_read_all(self.read_fd))
        finally:
            _close_fd(self.read_fd)
        return self._finished

    def _close_write_fd(self) -> None:
        if self.write_fd >= 0:
            _close_fd(self.write_fd)
            self.write_fd = -1


def begin_installed_write_audit(*, repo_root: Path) -> InstalledWriteAudit:
    """Create a parent-owned audit pipe for one isolated managed-Python process."""

    root = Path(repo_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"clarification repository does not exist: {root}")
    read_fd, write_fd = os.pipe()
    return InstalledWriteAudit(repo_root=root, read_fd=read_fd, write_fd=write_fd)


def _read_all(read_fd: int) -> bytes:
    chunks: list[bytes] = []
    while chunk := os.read(read_fd, 65536):
        chunks.append(chunk)
    return b"".join(chunks)


def _close_fd(descriptor: int) -> None:
    if descriptor < 0:
        return
    try:
        os.close(descriptor)
    except OSError as exc:
        if exc.errno != errno.EBADF:
            raise


def _read_trace(raw_trace: bytes) -> WriteAuditEvidence:
    try:
        lines = raw_trace.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        return WriteAuditEvidence(active=False, error=f"invalid write-audit trace encoding: {exc.reason}")
    records: list[Mapping[str, Any]] = []
    for index, line in enumerate(lines, start=1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            return WriteAuditEvidence(active=False, error=f"invalid write-audit trace line {index}: {exc.msg}")
        if not isinstance(record, dict):
            return WriteAuditEvidence(active=False, error=f"invalid write-audit trace record {index}")
        records.append(record)
    if not any(record.get("kind") == "ready" for record in records):
        return WriteAuditEvidence(active=False, error="installed write audit did not activate")
    writes = tuple(
        _record_summary(record)
        for record in records
        if record.get("kind") == "write"
    )
    subprocesses = tuple(
        _record_summary(record)
        for record in records
        if record.get("kind") == "subprocess"
    )
    return WriteAuditEvidence(active=True, write_attempts=writes, subprocess_attempts=subprocesses)


def _record_summary(record: Mapping[str, Any]) -> str:
    event = str(record.get("event") or "unknown")
    path = str(record.get("path") or "")
    return f"{event}:{path}" if path else event


AUDIT_PREAMBLE = r'''
import json
import os
from pathlib import Path
import sys

_root = Path(os.environ["ODYLITH_GREENFIELD_WRITE_AUDIT_ROOT"]).resolve()
_audit_fd = int(os.environ["ODYLITH_GREENFIELD_WRITE_AUDIT_FD"])
_write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC | os.O_EXCL
_audit_write = os.write
_audit_json_dumps = json.dumps
_audit_fsdecode = os.fsdecode


def _emit(kind, event, path=""):
    record = {"kind": kind, "event": str(event)}
    if path:
        record["path"] = str(path)
    _audit_write(_audit_fd, (_audit_json_dumps(record, sort_keys=True) + "\n").encode("utf-8"))


def _resolved_path(value, directory_fd=None):
    if isinstance(value, int):
        return None
    try:
        candidate = Path(_audit_fsdecode(value))
    except (TypeError, ValueError):
        return None
    if not candidate.is_absolute():
        if directory_fd not in (None, -1):
            return "dir-fd"
        return "relative-path"
    try:
        resolved = candidate.resolve(strict=False)
        return resolved.relative_to(_root).as_posix()
    except ValueError:
        return None


def _record_path(event, value, directory_fd=None):
    path = _resolved_path(value, directory_fd)
    if path is not None:
        _emit("write", event, path)


def _audit(event, arguments):
    if event == "open":
        path, _mode, flags = arguments
        if isinstance(flags, int) and flags & _write_flags:
            _record_path(event, path, "unknown-relative-dir-fd")
        return
    if event in {"os.remove", "os.rmdir", "os.mkdir", "os.chmod", "os.chown", "os.utime"}:
        _record_path(event, arguments[0], arguments[-1] if len(arguments) > 2 else None)
        return
    if event in {"os.rename", "os.replace"}:
        _record_path(event, arguments[0], arguments[2] if len(arguments) > 2 else None)
        _record_path(event, arguments[1], arguments[3] if len(arguments) > 3 else None)
        return
    if event == "os.link":
        _record_path(event, arguments[0], arguments[2] if len(arguments) > 2 else None)
        _record_path(event, arguments[1], arguments[3] if len(arguments) > 3 else None)
        return
    if event == "os.symlink":
        _record_path(event, arguments[1], arguments[2] if len(arguments) > 2 else None)
        return
    if event == "os.truncate":
        _emit("write", event, "fd")
        return
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
        _emit("subprocess", event)


sys.dont_write_bytecode = True
sys.addaudithook(_audit)
_emit("ready", "ready")
'''


AUDIT_CLI_WRAPPER = AUDIT_PREAMBLE + r'''

from odylith.cli import main

raise SystemExit(main(sys.argv[1:]))
'''


def audited_program(program: str) -> str:
    """Return isolated Python source with the same audit hook used by the CLI proof."""

    return AUDIT_PREAMBLE + "\n" + str(program)


__all__ = [
    "AUDIT_CLI_WRAPPER",
    "AUDIT_PREAMBLE",
    "AUDIT_FD_ENV",
    "AUDIT_ROOT_ENV",
    "InstalledWriteAudit",
    "WriteAuditEvidence",
    "audited_program",
    "begin_installed_write_audit",
]
