from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _live_commands_dir() -> Path:
    return _repo_root() / ".claude" / "commands"


def _bundled_commands_dir() -> Path:
    return (
        _repo_root()
        / "src"
        / "odylith"
        / "bundle"
        / "assets"
        / "project-root"
        / ".claude"
        / "commands"
    )


def _command_files(directory: Path) -> list[Path]:
    return sorted(directory.glob("*.md"))


def _frontmatter_block(path: Path) -> str | None:
    match = _FRONTMATTER.match(path.read_text(encoding="utf-8"))
    return None if match is None else match.group(1)


def test_command_frontmatter_parses_as_yaml_and_argument_hint_is_a_string() -> None:
    directories = (_live_commands_dir(), _bundled_commands_dir())
    checked_hints = 0

    for directory in directories:
        command_files = _command_files(directory)
        assert command_files, directory

        for path in command_files:
            block = _frontmatter_block(path)
            if block is None:
                # A command without frontmatter is allowed; there is nothing to validate.
                continue

            try:
                parsed = yaml.safe_load(block)
            except yaml.YAMLError as error:  # pragma: no cover - failure detail only
                pytest.fail(f"{path} has frontmatter that is not valid YAML: {error}")

            assert isinstance(parsed, dict), path

            if "argument-hint" not in parsed:
                continue

            hint = parsed["argument-hint"]
            assert isinstance(hint, str), (
                f"{path} declares argument-hint as {type(hint).__name__}; "
                "loaders that validate the field as a string drop the command"
            )
            checked_hints += 1

    # Guard against the assertions above passing vacuously if the layout ever moves.
    assert checked_hints > 0


def test_bundled_command_copies_stay_aligned_with_live_commands() -> None:
    live_dir = _live_commands_dir()
    bundled_dir = _bundled_commands_dir()

    live_names = {path.name for path in _command_files(live_dir)}
    bundled_names = {path.name for path in _command_files(bundled_dir)}
    assert live_names == bundled_names

    for name in sorted(live_names):
        live_text = (live_dir / name).read_text(encoding="utf-8")
        bundled_text = (bundled_dir / name).read_text(encoding="utf-8")
        assert live_text == bundled_text, name
