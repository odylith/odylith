"""Render the hash-bound command rail for a compiled Greenfield transaction."""

from __future__ import annotations

from collections.abc import Sequence


def format_confirmation_choice_lines(choices: Sequence[tuple[str, str]]) -> list[str]:
    """Return the canonical visible command block for Greenfield confirmation."""

    lines = [
        "## Choose one command",
        "",
        "Use one complete command below. Copy CONFIRM or REJECT exactly. For EDIT, replace `<corrections>` with "
        "your changes. The approval code binds your choice to this reviewed package.",
    ]
    for label, detail in choices:
        command = _single_line(label)
        text = _single_line(detail)
        if not command or not text:
            continue
        lines.extend(
            [
                "",
                f"### {command.partition(' ')[0].upper()}",
                f"```text\n{command}\n```",
                text,
            ]
        )
    return lines


def _single_line(value: object) -> str:
    return " ".join(str(value or "").split())


__all__ = ["format_confirmation_choice_lines"]
