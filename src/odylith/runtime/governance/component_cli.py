"""Own the Component CLI family parser and backend routing."""

from __future__ import annotations

import argparse
import importlib
from collections.abc import Sequence

from odylith.runtime.common.command_surface import ensure_repo_root_args


_COMMAND_MODULES = {
    "register": "odylith.runtime.governance.component_authoring",
    "update-description": "odylith.runtime.governance.component_description_update",
}
_COMMAND_HELP = {
    "register": "Register a new component in the Odylith registry and scaffold its CURRENT_SPEC.md.",
    "update-description": "Update only an existing Registry component description.",
}


def configure_parser(subparsers: argparse._SubParsersAction) -> argparse.ArgumentParser:
    component = subparsers.add_parser("component", help="Create and maintain Registry component records.")
    component_subparsers = component.add_subparsers(dest="component_command", required=True)
    for command, help_text in _COMMAND_HELP.items():
        child = component_subparsers.add_parser(command, help=help_text)
        child.add_argument("--repo-root", default=".", help="Consumer repository root.")
        child.add_argument("forwarded", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return component


def is_command(command: str) -> bool:
    return str(command) in _COMMAND_MODULES


def dispatch(*, repo_root: str, command: str, forwarded: Sequence[str]) -> int:
    module_name = _COMMAND_MODULES.get(str(command))
    if module_name is None:
        raise ValueError(f"unsupported component command: {command}")
    module = importlib.import_module(module_name)
    return int(
        module.main(
            ensure_repo_root_args(
                repo_root=repo_root,
                argv=[str(token) for token in forwarded],
            )
        )
    )


__all__ = ["configure_parser", "dispatch", "is_command"]
