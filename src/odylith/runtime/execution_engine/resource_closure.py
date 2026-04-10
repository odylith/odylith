from __future__ import annotations

from collections import deque
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine.contract import ResourceClosure


def classify_resource_closure(
    requested: Sequence[str],
    *,
    dependency_graph: Mapping[str, Sequence[str]] | None = None,
    destructive_groups: Sequence[Sequence[str]] | None = None,
) -> ResourceClosure:
    requested_tokens = tuple(dict.fromkeys(str(item).strip() for item in requested if str(item).strip()))
    requested_set = set(requested_tokens)
    graph = {str(key).strip(): tuple(str(item).strip() for item in values if str(item).strip()) for key, values in (dependency_graph or {}).items()}

    destructive_overlap: list[str] = []
    for raw_group in destructive_groups or ():
        group = {str(item).strip() for item in raw_group if str(item).strip()}
        if not group:
            continue
        if requested_set & group and not group.issubset(requested_set):
            destructive_overlap.extend(sorted(requested_set & group))
    if destructive_overlap:
        return ResourceClosure(
            classification="destructive",
            requested=requested_tokens,
            destructive_overlap=tuple(dict.fromkeys(destructive_overlap)),
            rationale="requested subset intersects a destructive closure group without including full closure",
        )

    missing: list[str] = []
    visited: set[str] = set(requested_set)
    queue = deque(requested_tokens)
    while queue:
        current = queue.popleft()
        for dependency in graph.get(current, ()):
            if dependency in visited:
                continue
            visited.add(dependency)
            missing.append(dependency)
            queue.append(dependency)

    if missing:
        return ResourceClosure(
            classification="incomplete",
            requested=requested_tokens,
            missing_dependencies=tuple(dict.fromkeys(missing)),
            rationale="requested scope is missing required closure dependencies",
        )

    return ResourceClosure(
        classification="safe",
        requested=requested_tokens,
        rationale="requested scope covers the known dependency closure",
    )
