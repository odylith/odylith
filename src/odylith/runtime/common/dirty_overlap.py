from __future__ import annotations

from typing import Sequence


def summarize_dirty_overlap(
    lines: Sequence[str],
    *,
    verbose: bool,
    sample_size: int = 4,
) -> tuple[str, ...]:
    normalized = tuple(str(line).rstrip() for line in lines if str(line).strip())
    if not normalized:
        return ()
    if verbose or len(normalized) <= sample_size:
        return normalized
    sample = normalized[:sample_size]
    hidden = len(normalized) - len(sample)
    return (
        f"{len(normalized)} local worktree entries overlap this mutation plan.",
        *sample,
        f"... {hidden} more overlap entries hidden; rerun with --verbose to show the full set.",
    )
