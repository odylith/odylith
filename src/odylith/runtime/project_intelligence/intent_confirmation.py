"""Render the canonical Greenfield confirmation command rail."""

from __future__ import annotations

from collections.abc import Sequence


def format_confirmation_choice_lines(choices: Sequence[tuple[str, str]]) -> list[str]:
    """Return the canonical visible command block for greenfield confirmations."""

    lines = [
        "## Choose one command",
        "",
        "Use one complete command below. Copy CONFIRM or REJECT exactly. For EDIT, replace `<corrections>` with "
        "your changes. The approval code binds your choice to this reviewed package.",
    ]
    for label, detail in choices:
        command = _clean(label)
        verb = command.partition(" ")[0].upper()
        text = _clean(detail)
        if command and text:
            lines.extend(
                [
                    "",
                    f"### {verb}",
                    f"```text\n{command}\n```",
                    text,
                ]
            )
    return lines


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())
