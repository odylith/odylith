"""Audit installed clarification proposals for attempted repository mutations."""

from __future__ import annotations

from dataclasses import dataclass, field
import errno
import json
import os
from pathlib import Path
import threading
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
AUDIT_DASHBOARD_ENV = "ODYLITH_GREENFIELD_WRITE_AUDIT_DASHBOARD"
_GREENFIELD_MUTATION_ROOTS = (*GREENFIELD_REPOSITORY_WRITE_PATHS, GREENFIELD_RUNTIME_ROOT)


@dataclass(frozen=True)
class WriteAuditEvidence:
    """Redacted outcome from one installed-process filesystem audit."""

    active: bool
    write_attempts: tuple[str, ...] = ()
    subprocess_attempts: tuple[str, ...] = ()
    error: str = ""
    process_observations: tuple[Mapping[str, Any], ...] = ()


@dataclass
class InstalledWriteAudit:
    """Drain one isolated process's audit pipe while that process is running."""

    repo_root: Path
    read_fd: int
    write_fd: int
    dashboard_opener: Mapping[str, str] | None = None
    _finished: WriteAuditEvidence | None = field(default=None, init=False, repr=False)
    _reader: threading.Thread = field(init=False, repr=False)
    _trace_chunks: list[bytes] = field(default_factory=list, init=False, repr=False)
    _reader_error: str = field(default="", init=False, repr=False)

    def __post_init__(self) -> None:
        reader = None
        try:
            reader = threading.Thread(target=self._drain, name="greenfield-write-audit", daemon=True)
            self._reader = reader
            reader.start()
        except BaseException:
            self._close_write_fd()
            if reader is not None and reader.ident is not None:
                reader.join()
            else:
                _close_fd(self.read_fd)
                self.read_fd = -1
            raise

    def _drain(self) -> None:
        try:
            while chunk := os.read(self.read_fd, 65536):
                self._trace_chunks.append(chunk)
        except Exception as exc:
            self._reader_error = f"installed write audit reader failed: {type(exc).__name__}: {exc}"
        finally:
            try:
                _close_fd(self.read_fd)
            except OSError as exc:
                self._reader_error = f"installed write audit reader failed: {type(exc).__name__}: {exc}"
            self.read_fd = -1

    def environment(self) -> dict[str, str]:
        values = {
            AUDIT_ROOT_ENV: str(self.repo_root),
            AUDIT_FD_ENV: str(self.write_fd),
            AUDIT_MUTATION_ROOTS_ENV: json.dumps(_GREENFIELD_MUTATION_ROOTS),
        }
        if self.dashboard_opener is not None:
            values[AUDIT_DASHBOARD_ENV] = json.dumps(dict(self.dashboard_opener), sort_keys=True)
        return values

    @property
    def pass_fds(self) -> tuple[int, ...]:
        return (self.write_fd,)

    def command(self, *, runtime_python: Path, arguments: Sequence[str]) -> list[str]:
        python = Path(runtime_python).expanduser().resolve()
        if not python.is_file():
            raise FileNotFoundError(f"managed runtime python is missing: {python}")
        return [str(python), "-I", "-c", AUDIT_CLI_WRAPPER, *[str(argument) for argument in arguments]]

    def finish(self) -> WriteAuditEvidence:
        """Collect the complete trace after the child and its writers have exited."""

        if self._finished is not None:
            return self._finished
        try:
            self._close_write_fd()
            self._reader.join()
            raw_trace = b"".join(self._trace_chunks)
            if self._reader_error and not raw_trace.endswith(b"\n"):
                raw_trace = raw_trace[:raw_trace.rfind(b"\n") + 1]
            evidence = _read_trace(raw_trace)
            self._finished = (
                WriteAuditEvidence(
                    active=False,
                    write_attempts=evidence.write_attempts,
                    subprocess_attempts=evidence.subprocess_attempts,
                    error=self._reader_error + (f"; {evidence.error}" if evidence.error else ""),
                    process_observations=evidence.process_observations,
                )
                if self._reader_error
                else evidence
            )
        finally:
            self._trace_chunks.clear()
        return self._finished

    def _close_write_fd(self) -> None:
        if self.write_fd >= 0:
            _close_fd(self.write_fd)
            self.write_fd = -1


def begin_installed_write_audit(
    *, repo_root: Path, dashboard_opener: Mapping[str, str] | None = None,
) -> InstalledWriteAudit:
    """Create a parent-owned audit pipe for one isolated managed-Python process."""

    root = Path(repo_root).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"clarification repository does not exist: {root}")
    read_fd, write_fd = os.pipe()
    return InstalledWriteAudit(repo_root=root, read_fd=read_fd, write_fd=write_fd,
                               dashboard_opener=dashboard_opener)


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
        if record.get("kind") == "subprocess" and not isinstance(record.get("process", {}), dict):
            return WriteAuditEvidence(active=False, error=f"invalid process detail record {index}")
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
        process_observations=tuple(dict(record.get("process") or {}) for record in records
                                   if record.get("kind") == "subprocess"),
    )


def dashboard_opener_issues(
    evidence: WriteAuditEvidence, *, expected: Mapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Qualify at most one observed canonical opener; never hide process attempts."""

    if not evidence.active or evidence.error:
        return ("installed process audit is inactive or failed",)
    if len(evidence.process_observations) != len(evidence.subprocess_attempts):
        return ("process detail count differs from actual event count",)
    if len(evidence.subprocess_attempts) > 1:
        return ("more than one process attempt occurred",)
    for event, record in zip(evidence.subprocess_attempts, evidence.process_observations):
        if event != "subprocess.Popen" or record.get("classification") != "post_closed_dashboard_opener":
            return ("unattributed or forbidden process attempt occurred",)
        if (set(record) != {"classification", "event", "executable", "argv", "transaction_hash",
                            "write_set_hash", "project_url", "journal_state", "lifecycle_state", "journal_sha256",
                            "canonical_call_context", "owner_sha256"}
                or record.get("event") != event
                or record.get("executable") != "/bin/sh"
                or record.get("argv") != ["/bin/sh", "-c", "osascript"]
                or record.get("journal_state") != "closed"
                or record.get("lifecycle_state") != "CLOSED"
                or not record.get("journal_sha256") or not record.get("project_url")):
            return ("canonical opener evidence is incomplete",)
        if expected is None:
            return ("canonical opener has no sealed expected binding",)
        try:
            url = (Path(expected["repo_root"]) / ".odylith/runtime/greenfield/generations"
                   / expected["write_set_hash"] / "repository/odylith/index.html").as_uri() + "?tab=project"
            if (record["transaction_hash"] != expected["transaction_hash"]
                    or record["write_set_hash"] != expected["write_set_hash"] or record["project_url"] != url
                    or record["canonical_call_context"] != ["_confirm_pending_transaction", "open_committed_dashboard",
                                                             "MacOSXOSAScript.open", "os.popen"]
                    or record["owner_sha256"] != {key: expected[key] for key in (
                        "navigation_source_sha256", "confirmation_source_sha256", "webbrowser_source_sha256",
                        "os_source_sha256", "shell_sha256", "osascript_sha256")}
                    or len(record["journal_sha256"]) != 64
                    or any(character not in "0123456789abcdef" for character in record["journal_sha256"])):
                return ("canonical opener differs from sealed expected binding",)
        except (KeyError, TypeError, ValueError):
            return ("canonical opener expected binding is invalid",)
    return ()


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
import hashlib
import shutil

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
_dashboard = json.loads(os.environ.get("ODYLITH_GREENFIELD_WRITE_AUDIT_DASHBOARD", "null"))
_browser_context = threading.local()
if _dashboard is not None:
    from odylith.runtime.domain_intelligence import greenfield_post_confirm_handoff as _navigation_owner
    from odylith.runtime.surfaces import greenfield_host_confirmation as _confirmation_owner
    import webbrowser
    _navigation_code = _navigation_owner.open_committed_dashboard.__code__
    _confirmation_code = _confirmation_owner._confirm_pending_transaction.__code__
    _browser_code = getattr(webbrowser, "MacOSXOSAScript", None)
    _browser_code = _browser_code.open.__code__ if _browser_code is not None else None
    _popen_code = os.popen.__code__
    _owner_files = ((_navigation_owner.__file__, "navigation_source_sha256"),
                    (_confirmation_owner.__file__, "confirmation_source_sha256"),
                    (webbrowser.__file__, "webbrowser_source_sha256"),
                    (os.__file__, "os_source_sha256"))


def _emit(kind, event, path=""):
    record = {"kind": kind, "event": str(event)}
    if path:
        record["path"] = str(path)
    _audit_write(_audit_fd, (_audit_json_dumps(record, sort_keys=True) + "\n").encode("utf-8"))


def _dashboard_process(event, arguments):
    # Unknown arguments may contain secrets: compare in RAM, retain digests only.
    facts = {"classification": "unattributed", "event": event}
    try:
        facts["arguments_sha256"] = hashlib.sha256(repr(arguments[:2]).encode()).hexdigest()
        if event != "subprocess.Popen" or _dashboard is None or sys.platform != "darwin":
            return facts
        executable, argv, _cwd, child_env = arguments
        if executable != "/bin/sh" or argv != ["/bin/sh", "-c", "osascript"]:
            return facts
        frames = []
        frame = sys._getframe(1)
        while frame is not None:
            frames.append(frame)
            frame = frame.f_back
        navigation = next(frame for frame in frames if frame.f_code is _navigation_code)
        confirmation = next(frame for frame in frames if frame.f_code is _confirmation_code)
        if not any(frame.f_code is _browser_code for frame in frames):
            return facts
        if not any(frame.f_code is _popen_code for frame in frames):
            return facts
        if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != _dashboard[key]
               for path, key in _owner_files):
            return facts
        transaction = _dashboard["transaction_hash"]
        write_set = _dashboard["write_set_hash"]
        if confirmation.f_locals["transaction_hash"] != transaction or confirmation.f_locals["root"].resolve() != _root:
            return facts
        entry = _root / ".odylith/runtime/greenfield/generations" / write_set / "repository/odylith/index.html"
        url = entry.as_uri() + "?tab=project"
        nav = navigation.f_locals["navigation"]
        if (entry.is_symlink() or nav.get("project_url") != url
                or nav.get("dashboard_path") != str(entry)
                or getattr(_browser_context, "url", None) != url):
            return facts
        journal_path = _root / ".odylith/runtime/greenfield/create-journal" / transaction / "state.v1.json"
        raw = journal_path.read_bytes()
        journal = json.loads(raw)
        if (journal.get("state") != "closed" or journal.get("lifecycle_state") != "CLOSED"
                or journal.get("transaction_hash") != transaction
                or journal.get("repository_write_set_hash") != write_set):
            return facts
        from odylith.runtime.domain_intelligence.greenfield_commit_journal import GreenfieldCommitJournal
        pinned = GreenfieldCommitJournal.pin_reviewed_generation(repo_root=_root, transaction_hash=transaction)
        if (pinned.repository_root / "odylith/index.html" != entry
                or pinned.manifest_sha256 != journal["generation_manifest_sha256"]
                or journal_path.read_bytes() != raw
                or hashlib.sha256((_root / "odylith/index.html").read_bytes()).hexdigest() != _dashboard["publication_sha256"]):
            return facts
        effective_env = os.environ if child_env is None else child_env
        if shutil.which("osascript", path=effective_env.get("PATH", "")) != "/usr/bin/osascript":
            return facts
        if any(hashlib.sha256(Path(path).read_bytes()).hexdigest() != _dashboard[key]
               for path, key in (("/bin/sh", "shell_sha256"), ("/usr/bin/osascript", "osascript_sha256"))):
            return facts
        return {"classification": "post_closed_dashboard_opener", "event": event,
                "executable": executable, "argv": argv, "transaction_hash": transaction,
                "write_set_hash": write_set, "project_url": url,
                "journal_state": "closed", "lifecycle_state": "CLOSED",
                "journal_sha256": hashlib.sha256(raw).hexdigest(),
                "canonical_call_context": ["_confirm_pending_transaction", "open_committed_dashboard",
                                           "MacOSXOSAScript.open", "os.popen"],
                "owner_sha256": {key: _dashboard[key] for _path, key in (
                    *_owner_files, ("/bin/sh", "shell_sha256"), ("/usr/bin/osascript", "osascript_sha256"))}}
    except Exception:
        return facts
    finally:
        _browser_context.url = None


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
    if event == "webbrowser.open":
        _browser_context.url = arguments[0] if arguments else None
        return
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
        record = {"kind": "subprocess", "event": event, "process": _dashboard_process(event, arguments)}
        _audit_write(_audit_fd, (_audit_json_dumps(record, sort_keys=True) + "\n").encode("utf-8"))


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
    "dashboard_opener_issues",
]
