"""Tar archive safety checks for Odylith release extraction."""

from __future__ import annotations

import tarfile
from pathlib import Path, PurePosixPath
from typing import Iterable


def _member_parts(name: str) -> tuple[str, ...]:
    return tuple(part for part in PurePosixPath(name).parts if part not in ("", "."))


def _resolved_link_target(*, member_name: str, link_name: str) -> PurePosixPath | None:
    stack: list[str] = []
    for part in (*PurePosixPath(member_name).parent.parts, *PurePosixPath(link_name).parts):
        if part in ("", "."):
            continue
        if part == "..":
            if not stack:
                return None
            stack.pop()
            continue
        stack.append(part)
    return PurePosixPath(*stack) if stack else PurePosixPath(".")


def validate_archive_members(
    *,
    members: Iterable[tarfile.TarInfo],
    expected_root: str,
    label: str,
) -> None:
    for member in members:
        parts = _member_parts(member.name)
        if any(part == ".." for part in parts):
            raise ValueError(f"{label} contains unsafe member path: {member.name}")
        if PurePosixPath(member.name).is_absolute():
            raise ValueError(f"{label} contains absolute member path: {member.name}")
        if not parts or parts[0] != expected_root:
            raise ValueError(f"{label} contains unexpected member path: {member.name}")
        if member.issym() or member.islnk():
            if not member.linkname or PurePosixPath(member.linkname).is_absolute():
                raise ValueError(f"{label} contains unsafe link target: {member.name} -> {member.linkname}")
            resolved_link = _resolved_link_target(member_name=member.name, link_name=member.linkname)
            resolved_parts = (
                tuple(part for part in resolved_link.parts if part not in ("", "."))
                if resolved_link is not None
                else ()
            )
            if not resolved_parts or resolved_parts[0] != expected_root:
                raise ValueError(f"{label} contains unsafe link target: {member.name} -> {member.linkname}")
            continue
        if member.ischr() or member.isblk() or member.isfifo():
            raise ValueError(f"{label} contains unsupported member type: {member.name}")


def extract_validated_archive(
    *,
    archive_path: Path,
    destination: Path,
    expected_root: str,
    label: str,
) -> None:
    with tarfile.open(archive_path, "r:gz") as archive:
        members = archive.getmembers()
        validate_archive_members(members=members, expected_root=expected_root, label=label)
        archive.extractall(path=destination, filter="fully_trusted")
