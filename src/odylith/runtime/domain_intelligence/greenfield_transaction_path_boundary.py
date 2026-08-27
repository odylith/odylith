"""Descriptor-relative filesystem boundary for Greenfield transaction custody."""

from __future__ import annotations

from dataclasses import dataclass
import errno
import os
from pathlib import Path
import secrets
import stat
from typing import Iterable


_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_CLOEXEC", 0)
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)


class GreenfieldTransactionPathError(ValueError):
    """A Greenfield transaction path crossed or targeted an unsafe filesystem entry."""


@dataclass(frozen=True)
class GreenfieldRepositoryEntry:
    path: str
    kind: str
    data: bytes = b""
    mode: int = 0


def list_directory(repo_root: Path, path: Path | str) -> tuple[GreenfieldRepositoryEntry, ...]:
    """List one safe directory without following or accepting any child symlink."""

    token = relative_token(repo_root, path)
    directory_fd = _open_directory(repo_root, Path(token).parts, create=False)
    try:
        rows: list[GreenfieldRepositoryEntry] = []
        for name in sorted(os.listdir(directory_fd)):
            child_token = f"{token}/{name}"
            metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
            rows.append(
                GreenfieldRepositoryEntry(
                    path=child_token,
                    kind=_metadata_kind(metadata, token=child_token),
                    mode=stat.S_IMODE(metadata.st_mode),
                )
            )
        return tuple(rows)
    finally:
        os.close(directory_fd)


def relative_token(repo_root: Path, path: Path | str) -> str:
    """Return a normalized lexical repo-relative token without following path entries."""

    root = Path(repo_root).expanduser().resolve()
    candidate = Path(path).expanduser()
    if candidate.is_absolute():
        try:
            candidate = candidate.relative_to(root)
        except ValueError as exc:
            raise GreenfieldTransactionPathError(
                "Greenfield transaction path escapes the managed repository root"
            ) from exc
    parts = candidate.parts
    if not parts or any(part in {"", ".", ".."} for part in parts):
        raise GreenfieldTransactionPathError(
            "Greenfield transaction path escapes the managed repository root"
        )
    return Path(*parts).as_posix()


def path_kind(repo_root: Path, path: Path | str) -> str:
    """Inspect one entry without following any component."""

    token = relative_token(repo_root, path)
    try:
        parent_fd, leaf = _open_parent(repo_root, token, create=False)
    except FileNotFoundError:
        return "missing"
    try:
        metadata = _stat_leaf(parent_fd, leaf)
        if metadata is None:
            return "missing"
        return _metadata_kind(metadata, token=token)
    finally:
        os.close(parent_fd)


def ensure_directory(repo_root: Path, path: Path | str) -> Path:
    """Create a directory chain while rejecting every symlinked component."""

    token = relative_token(repo_root, path)
    fd = _open_directory(repo_root, Path(token).parts, create=True)
    os.close(fd)
    return Path(repo_root).expanduser().resolve() / token


def read_bytes(repo_root: Path, path: Path | str) -> bytes:
    """Read one regular file through a no-follow descriptor chain."""

    token = relative_token(repo_root, path)
    parent_fd, leaf = _open_parent(repo_root, token, create=False)
    try:
        metadata = _stat_leaf(parent_fd, leaf)
        if metadata is None:
            raise FileNotFoundError(token)
        if _metadata_kind(metadata, token=token) != "file":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction file is not a regular file: {token}"
            )
        try:
            fd = os.open(leaf, os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=parent_fd)
        except OSError as exc:
            raise _path_error(token, exc) from exc
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or (opened.st_dev, opened.st_ino) != (
                metadata.st_dev,
                metadata.st_ino,
            ):
                raise GreenfieldTransactionPathError(
                    f"Greenfield transaction file changed during safe open: {token}"
                )
            chunks: list[bytes] = []
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    return b"".join(chunks)
                chunks.append(chunk)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def atomic_write_bytes(
    repo_root: Path,
    path: Path | str,
    data: bytes,
    *,
    mode: int = 0o644,
    temporary_directory: Path | str | None = None,
) -> Path:
    """Durably replace one file without following an ancestor or leaf symlink."""

    token = relative_token(repo_root, path)
    parent_fd, leaf = _open_parent(repo_root, token, create=True)
    temporary_fd = parent_fd
    owns_temporary_fd = False
    temporary_name = f".{leaf}.{secrets.token_hex(8)}.tmp"
    try:
        existing = _stat_leaf(parent_fd, leaf)
        if existing is not None and _metadata_kind(existing, token=token) != "file":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction write target is not a regular file: {token}"
            )
        if temporary_directory is not None:
            temporary_token = relative_token(repo_root, temporary_directory)
            temporary_fd = _open_directory(repo_root, Path(temporary_token).parts, create=True)
            owns_temporary_fd = True
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
        fd = os.open(temporary_name, flags, mode, dir_fd=temporary_fd)
        try:
            view = memoryview(data)
            while view:
                written = os.write(fd, view)
                view = view[written:]
            os.fchmod(fd, mode)
            os.fsync(fd)
        finally:
            os.close(fd)
        os.replace(
            temporary_name,
            leaf,
            src_dir_fd=temporary_fd,
            dst_dir_fd=parent_fd,
        )
        os.fsync(parent_fd)
        if temporary_fd != parent_fd:
            os.fsync(temporary_fd)
    except BaseException:
        try:
            os.unlink(temporary_name, dir_fd=temporary_fd)
        except FileNotFoundError:
            pass
        raise
    finally:
        if owns_temporary_fd:
            os.close(temporary_fd)
        os.close(parent_fd)
    return Path(repo_root).expanduser().resolve() / token


def open_lock_file(repo_root: Path, path: Path | str) -> int:
    """Open a repository lock file through the same no-follow boundary."""

    token = relative_token(repo_root, path)
    parent_fd, leaf = _open_parent(repo_root, token, create=True)
    try:
        existing = _stat_leaf(parent_fd, leaf)
        if existing is not None and _metadata_kind(existing, token=token) != "file":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction lock is not a regular file: {token}"
            )
        try:
            fd = os.open(
                leaf,
                os.O_RDWR | os.O_CREAT | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0),
                0o600,
                dir_fd=parent_fd,
            )
        except OSError as exc:
            raise _path_error(token, exc) from exc
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            os.close(fd)
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction lock is not a regular file: {token}"
            )
        return fd
    finally:
        os.close(parent_fd)


def make_temporary_directory(repo_root: Path, parent: Path | str, *, prefix: str) -> str:
    """Create one unpredictable child directory relative to a safe parent descriptor."""

    parent_token = relative_token(repo_root, parent)
    parent_fd = _open_directory(repo_root, Path(parent_token).parts, create=True)
    try:
        for _attempt in range(128):
            name = f"{prefix}{secrets.token_hex(8)}"
            try:
                os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            except FileExistsError:
                continue
            os.fsync(parent_fd)
            return f"{parent_token}/{name}"
    finally:
        os.close(parent_fd)
    raise RuntimeError("Greenfield transaction could not allocate a temporary directory")


def rename_directory(repo_root: Path, source: Path | str, destination: Path | str) -> None:
    """Rename one safe directory without resolving either pathname."""

    source_token = relative_token(repo_root, source)
    destination_token = relative_token(repo_root, destination)
    source_parent, source_leaf = _open_parent(repo_root, source_token, create=False)
    destination_parent, destination_leaf = _open_parent(repo_root, destination_token, create=True)
    try:
        source_state = _stat_leaf(source_parent, source_leaf)
        if source_state is None or _metadata_kind(source_state, token=source_token) != "directory":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction rename source is not a safe directory: {source_token}"
            )
        if _stat_leaf(destination_parent, destination_leaf) is not None:
            raise FileExistsError(destination_token)
        os.rename(
            source_leaf,
            destination_leaf,
            src_dir_fd=source_parent,
            dst_dir_fd=destination_parent,
        )
        os.fsync(source_parent)
        if destination_parent != source_parent:
            os.fsync(destination_parent)
    finally:
        os.close(destination_parent)
        os.close(source_parent)


def remove_tree(repo_root: Path, path: Path | str) -> None:
    """Remove one directory tree after a complete no-follow safety scan."""

    token = relative_token(repo_root, path)
    scan_tree(repo_root, token, require_present=True)
    parent_fd, leaf = _open_parent(repo_root, token, create=False)
    try:
        directory_fd = _open_child_directory(parent_fd, leaf, token=token)
        try:
            _remove_directory_contents(directory_fd, prefix=token)
        finally:
            os.close(directory_fd)
        os.rmdir(leaf, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def unlink_file(repo_root: Path, path: Path | str) -> None:
    token = relative_token(repo_root, path)
    parent_fd, leaf = _open_parent(repo_root, token, create=False)
    try:
        metadata = _stat_leaf(parent_fd, leaf)
        if metadata is None or _metadata_kind(metadata, token=token) != "file":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction delete target is not a regular file: {token}"
            )
        os.unlink(leaf, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def remove_directory(repo_root: Path, path: Path | str) -> None:
    token = relative_token(repo_root, path)
    parent_fd, leaf = _open_parent(repo_root, token, create=False)
    try:
        metadata = _stat_leaf(parent_fd, leaf)
        if metadata is None or _metadata_kind(metadata, token=token) != "directory":
            raise GreenfieldTransactionPathError(
                f"Greenfield transaction directory delete target is not a directory: {token}"
            )
        os.rmdir(leaf, dir_fd=parent_fd)
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def scan_tree(
    repo_root: Path,
    path: Path | str,
    *,
    require_present: bool = False,
) -> tuple[GreenfieldRepositoryEntry, ...]:
    """Capture one file tree through no-follow descriptors for verification and readback."""

    token = relative_token(repo_root, path)
    try:
        parent_fd, leaf = _open_parent(repo_root, token, create=False)
    except FileNotFoundError:
        if require_present:
            raise FileNotFoundError(token) from None
        return ()
    try:
        metadata = _stat_leaf(parent_fd, leaf)
        if metadata is None:
            if require_present:
                raise FileNotFoundError(token)
            return ()
        kind = _metadata_kind(metadata, token=token)
        if kind == "file":
            return (
                GreenfieldRepositoryEntry(
                    path=token,
                    kind="file",
                    data=read_bytes(repo_root, token),
                    mode=stat.S_IMODE(metadata.st_mode),
                ),
            )
        directory_fd = _open_child_directory(parent_fd, leaf, token=token)
        try:
            rows = [
                GreenfieldRepositoryEntry(
                    path=token,
                    kind="directory",
                    mode=stat.S_IMODE(metadata.st_mode),
                )
            ]
            rows.extend(_scan_directory(directory_fd, prefix=token))
            return tuple(rows)
        finally:
            os.close(directory_fd)
    finally:
        os.close(parent_fd)


def copy_tree(repo_root: Path, source: Path | str, destination: Path | str) -> None:
    """Copy one captured repository tree to a new safe repository-relative location."""

    source_token = relative_token(repo_root, source)
    destination_token = relative_token(repo_root, destination)
    entries = scan_tree(repo_root, source_token, require_present=True)
    if path_kind(repo_root, destination_token) != "missing":
        raise FileExistsError(destination_token)
    for entry in entries:
        suffix = Path(entry.path).relative_to(source_token)
        target = Path(destination_token, suffix).as_posix()
        if entry.kind == "directory":
            directory_fd = _open_directory(repo_root, Path(target).parts, create=True)
            try:
                os.fchmod(directory_fd, entry.mode or 0o755)
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        else:
            atomic_write_bytes(repo_root, target, entry.data, mode=entry.mode or 0o644)


def remove_path(repo_root: Path, path: Path | str, *, missing_ok: bool = False) -> None:
    """Remove one regular file or directory tree through the no-follow boundary."""

    kind = path_kind(repo_root, path)
    if kind == "missing":
        if missing_ok:
            return
        raise FileNotFoundError(relative_token(repo_root, path))
    if kind == "file":
        unlink_file(repo_root, path)
    else:
        remove_tree(repo_root, path)


def _open_parent(repo_root: Path, token: str, *, create: bool) -> tuple[int, str]:
    parts = Path(token).parts
    return _open_directory(repo_root, parts[:-1], create=create), parts[-1]


def _open_directory(repo_root: Path, parts: Iterable[str], *, create: bool) -> int:
    root = Path(repo_root).expanduser().resolve()
    try:
        current = os.open(root, _DIRECTORY_FLAGS | _NOFOLLOW)
    except OSError as exc:
        raise _path_error(".", exc) from exc
    prefix: list[str] = []
    try:
        for part in parts:
            prefix.append(part)
            try:
                child = os.open(part, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    raise
                os.mkdir(part, mode=0o755, dir_fd=current)
                os.fsync(current)
                child = os.open(part, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=current)
            except OSError as exc:
                raise _path_error("/".join(prefix), exc) from exc
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _open_child_directory(parent_fd: int, leaf: str, *, token: str) -> int:
    try:
        return os.open(leaf, _DIRECTORY_FLAGS | _NOFOLLOW, dir_fd=parent_fd)
    except OSError as exc:
        raise _path_error(token, exc) from exc


def _stat_leaf(parent_fd: int, leaf: str) -> os.stat_result | None:
    try:
        return os.stat(leaf, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return None


def _metadata_kind(metadata: os.stat_result, *, token: str) -> str:
    if stat.S_ISLNK(metadata.st_mode):
        raise GreenfieldTransactionPathError(
            f"Greenfield transaction path crosses or targets a symlink: {token}"
        )
    if stat.S_ISREG(metadata.st_mode):
        return "file"
    if stat.S_ISDIR(metadata.st_mode):
        return "directory"
    raise GreenfieldTransactionPathError(
        f"Greenfield transaction path targets an unsupported filesystem entry: {token}"
    )


def _scan_directory(directory_fd: int, *, prefix: str) -> list[GreenfieldRepositoryEntry]:
    rows: list[GreenfieldRepositoryEntry] = []
    for name in sorted(os.listdir(directory_fd)):
        token = f"{prefix}/{name}"
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        kind = _metadata_kind(metadata, token=token)
        if kind == "file":
            fd = os.open(name, os.O_RDONLY | _NOFOLLOW | getattr(os, "O_CLOEXEC", 0), dir_fd=directory_fd)
            try:
                opened = os.fstat(fd)
                if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
                    raise GreenfieldTransactionPathError(
                        f"Greenfield transaction file changed during safe open: {token}"
                    )
                chunks: list[bytes] = []
                while chunk := os.read(fd, 1024 * 1024):
                    chunks.append(chunk)
            finally:
                os.close(fd)
            rows.append(
                GreenfieldRepositoryEntry(
                    path=token,
                    kind="file",
                    data=b"".join(chunks),
                    mode=stat.S_IMODE(metadata.st_mode),
                )
            )
            continue
        rows.append(
            GreenfieldRepositoryEntry(
                path=token,
                kind="directory",
                mode=stat.S_IMODE(metadata.st_mode),
            )
        )
        child_fd = _open_child_directory(directory_fd, name, token=token)
        try:
            rows.extend(_scan_directory(child_fd, prefix=token))
        finally:
            os.close(child_fd)
    return rows


def _remove_directory_contents(directory_fd: int, *, prefix: str) -> None:
    for name in sorted(os.listdir(directory_fd)):
        token = f"{prefix}/{name}"
        metadata = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
        kind = _metadata_kind(metadata, token=token)
        if kind == "file":
            os.unlink(name, dir_fd=directory_fd)
            continue
        child_fd = _open_child_directory(directory_fd, name, token=token)
        try:
            _remove_directory_contents(child_fd, prefix=token)
        finally:
            os.close(child_fd)
        os.rmdir(name, dir_fd=directory_fd)
    os.fsync(directory_fd)


def _path_error(token: str, error: OSError) -> GreenfieldTransactionPathError:
    if error.errno in {errno.ELOOP, errno.ENOTDIR}:
        return GreenfieldTransactionPathError(
            f"Greenfield transaction path crosses or targets a symlink: {token}"
        )
    return GreenfieldTransactionPathError(
        f"Greenfield transaction path is unavailable or unsafe: {token}"
    )


__all__ = [
    "GreenfieldRepositoryEntry",
    "GreenfieldTransactionPathError",
    "atomic_write_bytes",
    "copy_tree",
    "ensure_directory",
    "list_directory",
    "make_temporary_directory",
    "open_lock_file",
    "path_kind",
    "read_bytes",
    "relative_token",
    "remove_directory",
    "remove_path",
    "remove_tree",
    "rename_directory",
    "scan_tree",
    "unlink_file",
]
