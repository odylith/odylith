from __future__ import annotations

from pathlib import Path
from typing import Any
from typing import Mapping
from typing import Sequence


def _normalized_changed_paths(changed_paths: Sequence[str]) -> list[str]:
    return [str(path).strip().replace("\\", "/") for path in changed_paths if str(path).strip()]


def _component_scope_prefix(component_id: str) -> str:
    token = str(component_id or "").strip().lower()
    return f"odylith/registry/source/components/{token}/" if token else ""


def _component_sort_key(
    row: Mapping[str, Any],
    *,
    changed_paths: Sequence[str],
    explicit_component: str,
) -> tuple[int, int, int, str]:
    component_id = str(row.get("component_id", "")).strip().lower()
    component_path = str(row.get("path", "")).strip().replace("\\", "/")
    scope_prefix = _component_scope_prefix(component_id)
    normalized_changed = _normalized_changed_paths(changed_paths)
    explicit_match = int(bool(component_id and component_id == str(explicit_component or "").strip().lower()))
    exact_scope_match = int(
        any(
            path == component_path
            or (scope_prefix and path.startswith(scope_prefix))
            for path in normalized_changed
        )
    )
    component_token_match = int(
        any(
            component_id and f"/{component_id}/" in f"/{path}/"
            for path in normalized_changed
        )
    )
    return (-explicit_match, -exact_scope_match, -component_token_match, component_id)


def prioritize_governance_components(
    *,
    rows: Sequence[Mapping[str, Any]],
    changed_paths: Sequence[str],
    explicit_component: str = "",
) -> list[dict[str, Any]]:
    return [
        dict(row)
        for row in sorted(
            (row for row in rows if isinstance(row, Mapping)),
            key=lambda row: _component_sort_key(
                row,
                changed_paths=changed_paths,
                explicit_component=explicit_component,
            ),
        )
    ]
