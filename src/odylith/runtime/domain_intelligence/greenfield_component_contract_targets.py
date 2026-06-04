"""Repair-target parsing for differentiated Registry component specs."""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from odylith.runtime.common.value_coercion import dedupe_by_key


@dataclass(frozen=True)
class RepairTarget:
    index: int
    row: dict[str, Any]
    sibling: Mapping[str, Any] | None


def repair_targets_from_spec_issues(
    issues: Sequence[str],
    *,
    rows_by_label: Mapping[str, dict[str, Any]],
    indexes_by_label: Mapping[str, int],
) -> list[RepairTarget]:
    """Return component rows named by rendered spec quality issues."""

    targets: list[RepairTarget] = []
    for issue in issues:
        pair = re.search(
            r"component specs `(?P<left>[^`]+)` and `(?P<right>[^`]+)` are too interchangeable",
            issue,
        )
        if pair:
            left = pair.group("left")
            right = pair.group("right")
            for label, sibling in ((left, right), (right, left)):
                if label in rows_by_label:
                    targets.append(
                        RepairTarget(
                            index=indexes_by_label.get(label, 0),
                            row=rows_by_label[label],
                            sibling=rows_by_label.get(sibling),
                        )
                    )
            continue
        local = re.search(r"component spec `(?P<label>[^`]+)` does not contain", issue)
        if local and local.group("label") in rows_by_label:
            label = local.group("label")
            targets.append(RepairTarget(index=indexes_by_label.get(label, 0), row=rows_by_label[label], sibling=None))
    return _dedupe_targets(targets)


def operator_component_spec_issues(issues: Sequence[str]) -> list[str]:
    """Convert component spec quality failures into product-language blockers."""

    return [_operator_issue(issue) for issue in issues]


def _operator_issue(issue: str) -> str:
    pair = re.search(r"component specs `(?P<left>[^`]+)` and `(?P<right>[^`]+)` are too interchangeable", issue)
    if pair:
        return (
            "Odylith could not distinguish duplicate internal systems from the accepted intent after deterministic "
            f"repair: {pair.group('left')} and {pair.group('right')} remained interchangeable."
        )
    local = re.search(r"component spec `(?P<label>[^`]+)` does not contain", issue)
    if local:
        return (
            "Odylith could not derive enough component-local product terms from the accepted intent after deterministic "
            f"repair: {local.group('label')} remained too generic."
        )
    return issue


def _dedupe_targets(values: Sequence[RepairTarget]) -> list[RepairTarget]:
    return dedupe_by_key(values, lambda target: id(target.row))


__all__ = [
    "RepairTarget",
    "operator_component_spec_issues",
    "repair_targets_from_spec_issues",
]
