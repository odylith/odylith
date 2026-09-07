"""Update one existing Registry description without rewriting component ownership."""

from __future__ import annotations

import argparse
import json
import stat
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_bytes
from odylith.runtime.governance import owned_surface_refresh


_REGISTRY_PATH = Path("odylith/registry/source/component_registry.v1.json")


def _strict_registry(registry_path: Path) -> dict[str, Any]:
    if not registry_path.is_file():
        raise ValueError(f"Registry manifest does not exist: {registry_path}")
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Registry manifest is not valid JSON: {registry_path}: {exc.msg}") from exc
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Registry manifest could not be read: {registry_path}: {exc}") from exc
    if not isinstance(registry, dict):
        raise ValueError("Registry manifest must be a JSON object")
    components = registry.get("components")
    if not isinstance(components, list):
        raise ValueError("Registry manifest components must be a JSON array")

    seen: set[str] = set()
    for index, entry in enumerate(components):
        if not isinstance(entry, dict):
            raise ValueError(f"Registry component at index {index} must be a JSON object")
        component_id = entry.get("component_id")
        if not isinstance(component_id, str) or not component_id or component_id != component_id.strip():
            raise ValueError(f"Registry component at index {index} has an invalid component_id")
        if component_id in seen:
            raise ValueError(f"Registry manifest contains duplicate component_id: {component_id}")
        seen.add(component_id)
        description = entry.get("what_it_is")
        if not isinstance(description, str) or not description.strip():
            raise ValueError(f"Registry component '{component_id}' has an invalid what_it_is")
    return registry


def update_description(
    *,
    repo_root: Path,
    component_id: str,
    what_it_is: str,
    dry_run: bool = False,
) -> dict[str, str]:
    exact_id = str(component_id)
    description = str(what_it_is).strip()
    if not exact_id or exact_id != exact_id.strip():
        raise ValueError("Component ID must be a non-empty exact Registry component_id")
    if not description:
        raise ValueError("Component what_it_is must not be blank")

    root = Path(repo_root).expanduser().resolve()
    registry_path = root
    for part in _REGISTRY_PATH.parts:
        registry_path = registry_path / part
        if registry_path.is_symlink():
            raise ValueError(f"Registry path must not contain a symlink: {registry_path}")
    registry = _strict_registry(registry_path)
    try:
        registry_mode = stat.S_IMODE(registry_path.stat().st_mode)
    except OSError as exc:
        raise ValueError(f"Registry manifest metadata could not be read: {registry_path}: {exc}") from exc
    components = registry["components"]
    matches = [entry for entry in components if entry["component_id"] == exact_id]
    if not matches:
        raise ValueError(f"Unknown Registry component ID: {exact_id}")
    target = matches[0]
    previous = target["what_it_is"]
    target["what_it_is"] = description

    if not dry_run:
        atomic_write_bytes(
            registry_path,
            (json.dumps(registry, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
            mode=registry_mode,
        )
        owned_surface_refresh.raise_for_failed_refresh(
            repo_root=root,
            surface="registry",
            operation_label="Component description update",
        )
    return {
        "component_id": exact_id,
        "previous_what_it_is": previous,
        "what_it_is": description,
        "registry_path": str(registry_path),
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="odylith component update-description",
        description="Update only what_it_is for one existing Registry component.",
    )
    parser.add_argument("--repo-root", default=".", help="Repository root.")
    parser.add_argument("--id", required=True, action="append", dest="component_ids", help="Exact component ID.")
    parser.add_argument(
        "--what-it-is",
        required=True,
        action="append",
        dest="descriptions",
        help="Replacement Registry description.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing or refreshing Registry.")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Output as JSON.")
    args = parser.parse_args(argv)
    if len(args.component_ids) != 1:
        parser.error("--id must be provided exactly once")
    if len(args.descriptions) != 1:
        parser.error("--what-it-is must be provided exactly once")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = update_description(
            repo_root=Path(args.repo_root),
            component_id=args.component_ids[0],
            what_it_is=args.descriptions[0],
            dry_run=bool(args.dry_run),
        )
    except (ValueError, RuntimeError) as exc:
        print(str(exc))
        return 2 if isinstance(exc, ValueError) else 1

    mode = "dry-run" if args.dry_run else "updated"
    if args.as_json:
        print(json.dumps({"mode": mode, **result}, indent=2))
    else:
        print(f"odylith component update-description {mode}")
        print(f"  component_id: {result['component_id']}")
        print(f"  registry: {result['registry_path']}")
        owned_surface_refresh.print_dashboard_handoff(
            surface="registry",
            component=result["component_id"],
            dry_run=bool(args.dry_run),
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
