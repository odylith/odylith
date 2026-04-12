from __future__ import annotations

from collections import deque
import re
from typing import Mapping
from typing import Sequence

from odylith.runtime.execution_engine.contract import ResourceClosure

_WORKSTREAM_RE = re.compile(r"^B-\d{3,}$")
_WAVE_RE = re.compile(r"^W\d+$")
_RELEASE_RE = re.compile(r"^(?:v)?\d+\.\d+\.\d+$")
_GENERATED_SURFACE_PREFIXES: tuple[str, ...] = (
    "odylith/compass/",
    "odylith/radar/",
    "odylith/registry/",
    "odylith/casebook/",
    "odylith/atlas/",
)
_SURFACE_SOURCE_PREFIXES: tuple[str, ...] = (
    "odylith/radar/source/",
    "odylith/technical-plans/",
    "odylith/registry/source/",
    "odylith/casebook/bugs/",
    "odylith/atlas/source/",
)


def _normalize_tokens(values: Sequence[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def _domains_for_requested(requested: Sequence[str]) -> tuple[str, ...]:
    domains: list[str] = []
    for token in requested:
        if token.startswith("src/"):
            domains.append("path_scope")
        if token.startswith("tests/"):
            domains.append("test_matrix")
        if _WORKSTREAM_RE.fullmatch(token):
            domains.append("workstream_set")
        if _WAVE_RE.fullmatch(token):
            domains.append("wave_membership")
        if _RELEASE_RE.fullmatch(token):
            domains.append("release_membership")
        if any(token.startswith(prefix) for prefix in _GENERATED_SURFACE_PREFIXES):
            domains.append("generated_surface_cone")
    return tuple(dict.fromkeys(domains))


def _implicit_dependency_graph(requested: Sequence[str]) -> dict[str, tuple[str, ...]]:
    graph: dict[str, tuple[str, ...]] = {}
    for token in requested:
        if any(token.startswith(prefix) for prefix in _GENERATED_SURFACE_PREFIXES):
            graph[token] = _SURFACE_SOURCE_PREFIXES
            continue
        if token.startswith("tests/"):
            graph[token] = ("src/",)
            continue
        if _WAVE_RE.fullmatch(token):
            graph[token] = ("B-",)
    return graph


def _merged_graph(
    requested_tokens: tuple[str, ...],
    dependency_graph: Mapping[str, Sequence[str]] | None,
) -> dict[str, tuple[str, ...]]:
    merged: dict[str, tuple[str, ...]] = {}
    for graph in (_implicit_dependency_graph(requested_tokens), dependency_graph or {}):
        for raw_key, raw_values in graph.items():
            key = str(raw_key).strip()
            if not key:
                continue
            existing = list(merged.get(key, ()))
            for raw_value in raw_values:
                value = str(raw_value).strip()
                if value and value not in existing:
                    existing.append(value)
            merged[key] = tuple(existing)
    return merged


def _resolved_dependency_members(
    requested_tokens: tuple[str, ...],
    graph: Mapping[str, Sequence[str]],
) -> tuple[str, ...]:
    requested_set = set(requested_tokens)
    visited: set[str] = set(requested_set)
    closure_members: list[str] = list(requested_tokens)
    queue = deque(requested_tokens)
    while queue:
        current = queue.popleft()
        for dependency in graph.get(current, ()):
            token = str(dependency).strip()
            if not token:
                continue
            if token in {"B-", "W-", "src/"}:
                continue
            if token in visited:
                continue
            visited.add(token)
            closure_members.append(token)
            queue.append(token)
    return tuple(dict.fromkeys(closure_members))


def _is_token_satisfied(token: str, requested_tokens: tuple[str, ...]) -> bool:
    if token in requested_tokens:
        return True
    if token == "B-":
        return any(_WORKSTREAM_RE.fullmatch(item) for item in requested_tokens)
    if token == "W-":
        return any(_WAVE_RE.fullmatch(item) for item in requested_tokens)
    if token == "src/":
        return any(item.startswith("src/") for item in requested_tokens)
    if token.endswith("/"):
        return any(item.startswith(token) for item in requested_tokens)
    return False


def classify_resource_closure(
    requested: Sequence[str],
    *,
    dependency_graph: Mapping[str, Sequence[str]] | None = None,
    destructive_groups: Sequence[Sequence[str]] | None = None,
) -> ResourceClosure:
    requested_tokens = _normalize_tokens(requested)
    requested_set = set(requested_tokens)
    domains = _domains_for_requested(requested_tokens)
    graph = _merged_graph(requested_tokens, dependency_graph)

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
            domains=domains,
            closure_members=_resolved_dependency_members(requested_tokens, graph),
            rationale="requested subset intersects a destructive closure group without including full closure",
        )

    missing: list[str] = []
    queue = deque(requested_tokens)
    visited: set[str] = set(requested_tokens)
    while queue:
        current = queue.popleft()
        for dependency in graph.get(current, ()):
            token = str(dependency).strip()
            if not token:
                continue
            if not _is_token_satisfied(token, requested_tokens) and token not in missing:
                missing.append(token)
            if token in visited or token in {"B-", "W-", "src/"} or token.endswith("/"):
                continue
            visited.add(token)
            queue.append(token)

    closure_members = _resolved_dependency_members(requested_tokens, graph)
    if missing:
        return ResourceClosure(
            classification="incomplete",
            requested=requested_tokens,
            missing_dependencies=tuple(dict.fromkeys(missing)),
            domains=domains,
            closure_members=closure_members,
            rationale="requested scope is missing required closure dependencies",
        )

    return ResourceClosure(
        classification="safe",
        requested=requested_tokens,
        domains=domains,
        closure_members=closure_members,
        rationale="requested scope covers the known dependency closure",
    )
