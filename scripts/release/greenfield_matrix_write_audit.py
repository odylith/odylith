"""Audit installed clarification proposals for attempted repository mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
import errno
import json
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from odylith.runtime.domain_intelligence.greenfield_pending_transaction_store import (
    GREENFIELD_RUNTIME_ROOT,
)
from odylith.runtime.domain_intelligence.greenfield_repository_write_set import (
    GREENFIELD_REPOSITORY_WRITE_PATHS,
)


AUDIT_ROOT_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_ROOT"
AUDIT_FD_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_FD"
AUDIT_MUTATION_ROOTS_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_MUTATION_ROOTS"
_GREENFIELD_MUTATION_ROOTS = (*GREENFIELD_REPOSITORY_WRITE_PATHS, GREENFIELD_RUNTIME_ROOT)


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
            AUDIT_MUTATION_ROOTS_ENV: json.dumps(_GREENFIELD_MUTATION_ROOTS),
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
    audit_errors = tuple(
        _record_summary(record)
        for record in records
        if record.get("kind") == "error"
    )
    return WriteAuditEvidence(
        active=not audit_errors,
        write_attempts=writes,
        subprocess_attempts=subprocesses,
        error=("installed write audit could not resolve a write target: " + ", ".join(audit_errors))
        if audit_errors
        else "",
    )


def _record_summary(record: Mapping[str, Any]) -> str:
    event = str(record.get("event") or "unknown")
    path = str(record.get("path") or "")
    return f"{event}:{path}" if path else event


AUDIT_PREAMBLE = r'''
import json
import os
from pathlib import Path
import stat
import sys
import threading

try:
    import fcntl
except ImportError:
    fcntl = None

sys.dont_write_bytecode = True

_root = Path(os.environ["ODYLITH_GREENFIELD_WRITE_AUDIT_ROOT"]).resolve()
_cwd = Path.cwd().resolve()
_audit_fd = int(os.environ["ODYLITH_GREENFIELD_WRITE_AUDIT_FD"])
_mutation_roots = tuple(
    Path(value).as_posix().rstrip("/")
    for value in json.loads(os.environ["ODYLITH_GREENFIELD_WRITE_AUDIT_MUTATION_ROOTS"])
)
_write_flags = os.O_WRONLY | os.O_RDWR | os.O_APPEND | os.O_CREAT | os.O_TRUNC | os.O_EXCL
_audit_write = os.write
_audit_json_dumps = json.dumps
_audit_fsdecode = os.fsdecode
_audit_os_open = os.open
_audit_readlink = os.readlink
_open_context = threading.local()


def _emit(kind, event, path=""):
    record = {"kind": kind, "event": str(event)}
    if path:
        record["path"] = str(path)
    _audit_write(_audit_fd, (_audit_json_dumps(record, sort_keys=True) + "\n").encode("utf-8"))


def _relative_to_root(candidate):
    try:
        return candidate.relative_to(_root).as_posix()
    except ValueError:
        return None


def _owned_mutation_path(candidate):
    lexical = Path(os.path.abspath(candidate))
    for concrete in (lexical.resolve(strict=False), lexical):
        relative = _relative_to_root(concrete)
        if relative is not None and any(
            relative == root or relative.startswith(root + "/")
            for root in _mutation_roots
        ):
            return relative
    return None


def _directory_fd_path(directory_fd):
    if directory_fd in (None, -1):
        return _cwd
    if not isinstance(directory_fd, int):
        return None
    if fcntl is not None and hasattr(fcntl, "F_GETPATH"):
        try:
            raw_path = fcntl.fcntl(directory_fd, fcntl.F_GETPATH, bytes(1024))
            return Path(raw_path.split(b"\0", 1)[0].decode()).resolve(strict=False)
        except (OSError, UnicodeDecodeError, ValueError):
            pass
    for descriptor_root in (Path("/proc/self/fd"), Path("/dev/fd")):
        descriptor = descriptor_root / str(directory_fd)
        try:
            target = Path(_audit_readlink(descriptor))
            if not target.is_absolute():
                target = descriptor.parent / target
            return target.resolve(strict=False)
        except (OSError, RuntimeError, ValueError):
            continue
    return None


def _resolved_path(value, directory_fd=None):
    if isinstance(value, int):
        try:
            descriptor_mode = os.fstat(value).st_mode
        except OSError:
            return "unresolved-fd"
        if not (stat.S_ISREG(descriptor_mode) or stat.S_ISDIR(descriptor_mode)):
            return None
        target = _directory_fd_path(value)
        return _owned_mutation_path(target) if target is not None else "unresolved-fd"
    try:
        candidate = Path(_audit_fsdecode(value))
    except (TypeError, ValueError):
        return None
    if not candidate.is_absolute():
        directory = _directory_fd_path(directory_fd)
        if directory is None:
            return "unresolved-dir-fd"
        candidate = directory / candidate
    return _owned_mutation_path(candidate)


def _record_path(event, value, directory_fd=None):
    path = _resolved_path(value, directory_fd)
    if path in {"unresolved-fd", "unresolved-dir-fd"}:
        _emit("error", event, path)
    elif path is not None:
        _emit("write", event, path)


def _audited_os_open(path, flags, mode=0o777, *, dir_fd=None):
    previous = getattr(_open_context, "directory_fd", None)
    _open_context.directory_fd = dir_fd
    try:
        return _audit_os_open(path, flags, mode, dir_fd=dir_fd)
    finally:
        _open_context.directory_fd = previous


def _audit(event, arguments):
    if event == "open":
        path, _mode, flags = arguments
        if isinstance(flags, int) and flags & _write_flags:
            _record_path(event, path, getattr(_open_context, "directory_fd", None))
        return
    if event in {"os.remove", "os.rmdir"}:
        _record_path(event, arguments[0], arguments[1] if len(arguments) > 1 else None)
        return
    if event in {"os.mkdir", "os.chmod", "os.chown", "os.utime"}:
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
        _record_path(event, arguments[0])
        return
    if event in {"subprocess.Popen", "os.system", "os.posix_spawn", "os.exec"}:
        _emit("subprocess", event)


sys.addaudithook(_audit)
os.open = _audited_os_open
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
    "AUDIT_MUTATION_ROOTS_ENV",
    "AUDIT_ROOT_ENV",
    "InstalledWriteAudit",
    "WriteAuditEvidence",
    "audited_program",
    "begin_installed_write_audit",
]
