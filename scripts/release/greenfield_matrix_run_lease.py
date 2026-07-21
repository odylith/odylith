"""Own temporary space and the output destination for one matrix invocation."""

from __future__ import annotations

from dataclasses import dataclass
import fcntl
import json
import os
from pathlib import Path
import uuid

from local_release_smoke import _cleanup_smoke_temp_root


@dataclass
class MatrixRunLease:
    """Exclusive proof output lease with a private temporary namespace."""

    run_id: str
    temp_namespace: Path
    output_path: Path | None
    lock_path: Path | None
    lock_descriptor: int | None
    released: bool = False

    def to_dict(self) -> dict[str, str]:
        return {
            "run_id": self.run_id,
            "temporary_namespace": str(self.temp_namespace),
            "output_path": str(self.output_path) if self.output_path is not None else "",
        }

    def release(self) -> None:
        """Remove only this run's temporary data and its exclusive output lock."""

        if self.released:
            return
        cleanup_error: OSError | None = None
        try:
            _cleanup_smoke_temp_root(self.temp_namespace)
        except OSError as exc:
            cleanup_error = exc
        if self.temp_namespace.exists() or self.temp_namespace.is_symlink():
            detail = f"matrix proof run namespace was not removed: {self.temp_namespace}"
            if cleanup_error is not None:
                detail = f"{detail}: {cleanup_error}"
            _mark_cleanup_failure(
                descriptor=self.lock_descriptor,
                run_id=self.run_id,
                detail=detail,
            )
            _unlock_and_close(self.lock_descriptor)
            self.released = True
            raise RuntimeError(detail)
        if cleanup_error is not None:
            detail = f"matrix proof run namespace cleanup failed: {cleanup_error}"
            _mark_cleanup_failure(
                descriptor=self.lock_descriptor,
                run_id=self.run_id,
                detail=detail,
            )
            _unlock_and_close(self.lock_descriptor)
            self.released = True
            raise RuntimeError(detail)
        _release_output_lock(lock_path=self.lock_path, descriptor=self.lock_descriptor)
        self.released = True


def acquire_matrix_run_lease(*, temp_parent: Path, output_path: Path | None) -> MatrixRunLease:
    """Create a private namespace and reject concurrent writers of one proof record."""

    parent = Path(temp_parent).expanduser().resolve()
    parent.mkdir(parents=True, exist_ok=True)
    run_id = uuid.uuid4().hex
    namespace = parent / f"odylith-greenfield-proof-run-{run_id}"
    namespace.mkdir(mode=0o700)
    normalized_output = Path(output_path).expanduser().resolve() if output_path is not None else None
    try:
        lock_path, lock_descriptor = _acquire_output_lock(output_path=normalized_output, run_id=run_id)
    except Exception:
        _cleanup_smoke_temp_root(namespace)
        raise
    return MatrixRunLease(
        run_id=run_id,
        temp_namespace=namespace,
        output_path=normalized_output,
        lock_path=lock_path,
        lock_descriptor=lock_descriptor,
    )


def write_matrix_payload(*, output_path: Path | None, payload: dict[str, object]) -> None:
    """Persist one complete proof payload without exposing a truncated JSON record."""

    if output_path is None:
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_name(f".{output_path.name}.{uuid.uuid4().hex}.tmp")
    try:
        temporary_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary_path, output_path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _acquire_output_lock(*, output_path: Path | None, run_id: str) -> tuple[Path | None, int | None]:
    if output_path is None:
        return None, None
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output_path.with_name(f".{output_path.name}.lock")
    descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(descriptor)
        raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}") from exc
    try:
        _assert_output_lock_is_reclaimable(descriptor=descriptor, output_path=output_path)
    except Exception:
        _unlock_and_close(descriptor)
        raise
    try:
        _write_output_lock(descriptor=descriptor, run_id=run_id, state="active")
    except Exception:
        _unlock_and_close(descriptor)
        raise
    return lock_path, descriptor


def _assert_output_lock_is_reclaimable(*, descriptor: int, output_path: Path) -> None:
    os.lseek(descriptor, 0, os.SEEK_SET)
    contents = os.read(descriptor, 4096).decode("utf-8")
    if not contents.strip():
        return
    try:
        record = json.loads(contents)
        holder_pid = record["pid"]
    except (ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}") from exc
    if not isinstance(holder_pid, int) or holder_pid <= 0:
        raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}")
    state = record.get("state", "active")
    if state == "cleanup_failed":
        raise RuntimeError(f"matrix proof output is blocked by unresolved cleanup failure: {output_path}")
    if state != "active":
        raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}")
    try:
        os.kill(holder_pid, 0)
    except ProcessLookupError:
        raise RuntimeError(f"matrix proof output is blocked by an incomplete prior run: {output_path}")
    except PermissionError as exc:
        raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}") from exc
    raise RuntimeError(f"matrix proof output is already owned by another active run: {output_path}")


def _write_output_lock(*, descriptor: int, run_id: str, state: str, detail: str = "") -> None:
    record: dict[str, object] = {"pid": os.getpid(), "run_id": run_id, "state": state}
    if detail:
        record["detail"] = detail
    payload = (json.dumps(record, sort_keys=True) + "\n").encode("utf-8")
    os.ftruncate(descriptor, 0)
    os.lseek(descriptor, 0, os.SEEK_SET)
    os.write(descriptor, payload)
    os.fsync(descriptor)


def _mark_cleanup_failure(*, descriptor: int | None, run_id: str, detail: str) -> None:
    if descriptor is None:
        return
    _write_output_lock(
        descriptor=descriptor,
        run_id=run_id,
        state="cleanup_failed",
        detail=detail,
    )


def _unlock_and_close(descriptor: int | None) -> None:
    if descriptor is None:
        return
    fcntl.flock(descriptor, fcntl.LOCK_UN)
    os.close(descriptor)


def _release_output_lock(*, lock_path: Path | None, descriptor: int | None) -> None:
    if lock_path is None or descriptor is None:
        return
    _unlock_and_close(descriptor)
    lock_path.unlink(missing_ok=True)


__all__ = ["MatrixRunLease", "acquire_matrix_run_lease", "write_matrix_payload"]
