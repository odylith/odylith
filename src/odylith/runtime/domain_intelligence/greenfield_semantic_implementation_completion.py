"""Complete graph-required implementation edges for one release-system boundary."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


def single_release_system_targets(
    facts: Mapping[str, Sequence[Mapping[str, Any]]],
) -> dict[str, dict[str, list[str]]]:
    """Return all source-backed edges owned by a sole release system."""

    return {
        relation_kind: {
            str(row["fact_id"]): list(row["candidate_ids"])
            for name in collections
            for row in facts[name]
        }
        for relation_kind, collections in {
            "implements": ("workflow_steps", "state_objects", "visible_outputs"),
            "depends_on": ("external_systems",),
            "constrained_by": ("operational_constraints",),
            "excludes": ("non_goals",),
        }.items()
    }


def complete_single_release_system(
    relations: Mapping[str, list[dict[str, Any]]],
    *,
    release_system_ids: Sequence[str],
    targets: Mapping[str, Mapping[str, list[str]]],
) -> None:
    """Close deterministic coverage only when one active system owns the release."""

    if len(release_system_ids) != 1:
        return
    subject_id = release_system_ids[0]
    for relation_kind, relation_targets in targets.items():
        rows = relations[relation_kind]
        implemented = {
            row["object_id"] for row in rows if row["subject_id"] == subject_id
        }
        rows.extend(
            {
                "subject_id": subject_id,
                "object_id": object_id,
                "custody": "bounded_interpretation",
                "candidate_ids": list(candidate_ids),
            }
            for object_id, candidate_ids in relation_targets.items()
            if object_id not in implemented
        )


__all__ = ["complete_single_release_system", "single_release_system_targets"]
