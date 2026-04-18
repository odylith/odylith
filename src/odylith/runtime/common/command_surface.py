"""Command Surface helpers for the Odylith common layer."""

from __future__ import annotations

import shlex
import sys
from pathlib import Path
from typing import Sequence


def display_command(*parts: str) -> str:
    tokens = ["odylith", *(str(part).strip() for part in parts if str(part).strip())]
    return " ".join(shlex.quote(token) for token in tokens)


def module_invocation(*parts: str, python_path: str | Path | None = None) -> list[str]:
    interpreter = str(Path(python_path or sys.executable))
    return [interpreter, "-m", "odylith.cli", *(str(part).strip() for part in parts if str(part).strip())]


def _validate_repo_root_arg(*, argv: Sequence[str]) -> bool:
    tokens = [str(token) for token in argv]
    for index, token in enumerate(tokens):
        if token == "--":
            break
        if token == "--repo-root":
            if index + 1 >= len(tokens):
                raise SystemExit("--repo-root requires a value")
            value = str(tokens[index + 1])
            if value == "--" or not value.strip():
                raise SystemExit("--repo-root requires a value")
            return True
        if token.startswith("--repo-root="):
            value = token.partition("=")[2]
            if not str(value).strip():
                raise SystemExit("--repo-root requires a value")
            return True
    return False


def has_repo_root_arg(*, argv: Sequence[str]) -> bool:
    return _validate_repo_root_arg(argv=argv)


def ensure_repo_root_args(*, repo_root: str | Path, argv: Sequence[str]) -> list[str]:
    tokens = [str(token) for token in argv]
    if has_repo_root_arg(argv=tokens):
        return tokens
    return ["--repo-root", str(repo_root), *tokens]


def ensure_nested_subcommand_repo_root_args(*, repo_root: str | Path, argv: Sequence[str]) -> list[str]:
    tokens = [str(token) for token in argv]
    if has_repo_root_arg(argv=tokens):
        return tokens
    if not tokens:
        return tokens
    first = str(tokens[0]).strip()
    if first in {"-h", "--help"}:
        return tokens
    if first.startswith("-"):
        return ["--repo-root", str(repo_root), *tokens]
    return [tokens[0], "--repo-root", str(repo_root), *tokens[1:]]
