"""Repair known consumer Registry truth drift from released Odylith installs."""

from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from odylith.install.fs import atomic_write_text, display_path
from odylith.runtime.governance import component_registry_intelligence as registry

_COMPONENT_REGISTER_PHRASE = "registered through `odylith component register`"
_DETECTED = "detected"
_FEATURE_HISTORY_RE = re.compile(r"^-\s+\d{4}-\d{2}-\d{2}:")
_MANIFEST_RELATIVE = Path("odylith/registry/source/component_registry.v1.json")


@dataclass(frozen=True)
class ComponentRegisterDriftRepair:
    """Summary of a consumer Registry metadata repair pass."""

    changed_paths: tuple[str, ...] = ()
    repaired_components: tuple[str, ...] = ()
    repaired_specs: tuple[str, ...] = ()
    skipped_reason: str = ""

    @property
    def changed(self) -> bool:
        return bool(self.changed_paths)


def repair_component_register_registry_drift(
    *,
    repo_root: Path,
    consumer_repo: bool,
    today: dt.date | None = None,
) -> ComponentRegisterDriftRepair:
    """Repair 0.1.11 component-register output that fails current Registry validation."""

    root = Path(repo_root).expanduser().resolve()
    if not consumer_repo:
        return ComponentRegisterDriftRepair(skipped_reason="not a consumer repo")

    manifest_path = root / _MANIFEST_RELATIVE
    if not manifest_path.is_file():
        return ComponentRegisterDriftRepair(skipped_reason="component registry manifest missing")

    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return ComponentRegisterDriftRepair(skipped_reason=f"component registry manifest unreadable: {exc}")

    components = payload.get("components") if isinstance(payload, dict) else None
    if not isinstance(components, list):
        return ComponentRegisterDriftRepair(skipped_reason="component registry components list missing")

    repair_date = today or dt.date.today()
    repaired_components: list[str] = []
    repaired_specs: list[str] = []
    changed_paths: list[str] = []
    manifest_changed = False

    for raw in components:
        if not isinstance(raw, dict):
            continue
        component_id = str(raw.get("component_id", "")).strip()
        if not component_id:
            continue

        entry_changed = _repair_detected_taxonomy(raw)
        if entry_changed:
            manifest_changed = True
            repaired_components.append(component_id)

        if _is_component_register_entry(raw) and _repair_component_spec_history(
            repo_root=root,
            entry=raw,
            component_id=component_id,
            repair_date=repair_date,
        ):
            spec_ref = str(raw.get("spec_ref", "")).strip()
            if spec_ref:
                repaired_components.append(component_id)
                repaired_specs.append(spec_ref)
                changed_paths.append(spec_ref)

    if manifest_changed:
        atomic_write_text(
            manifest_path,
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        changed_paths.insert(0, display_path(repo_root=root, path=manifest_path))

    return ComponentRegisterDriftRepair(
        changed_paths=tuple(dict.fromkeys(changed_paths)),
        repaired_components=tuple(dict.fromkeys(repaired_components)),
        repaired_specs=tuple(dict.fromkeys(repaired_specs)),
    )


def _repair_detected_taxonomy(entry: dict[str, Any]) -> bool:
    changed = False
    kind = str(entry.get("kind", "")).strip()

    if _normalized_token(entry.get("category")) == _DETECTED:
        entry["category"] = registry.normalize_component_category("", fallback_kind=kind) or "governance_engine"
        changed = True

    if _normalized_token(entry.get("qualification")) == _DETECTED:
        entry["qualification"] = "candidate"
        changed = True

    return changed


def _is_component_register_entry(entry: dict[str, Any]) -> bool:
    if str(entry.get("owner", "")).strip().lower() != "product":
        return False
    if str(entry.get("product_layer", "")).strip() != "cli_bootstrap":
        return False
    evidence = " ".join(
        str(entry.get(key, "")).strip().lower()
        for key in ("what_it_is", "why_tracked")
    )
    return _COMPONENT_REGISTER_PHRASE in evidence


def _repair_component_spec_history(
    *,
    repo_root: Path,
    entry: dict[str, Any],
    component_id: str,
    repair_date: dt.date,
) -> bool:
    spec_ref = str(entry.get("spec_ref", "")).strip()
    if not spec_ref:
        return False
    spec_path = (repo_root / spec_ref).resolve()
    try:
        spec_path.relative_to(repo_root)
    except ValueError:
        return False
    if not spec_path.is_file():
        return False

    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if _has_dated_feature_history(lines):
        return False

    entry_line = (
        f"- {repair_date.isoformat()}: Repaired Odylith 0.1.11 component register "
        f"metadata drift for `{component_id}`."
    )
    updated = _insert_feature_history_entry(lines=lines, entry_line=entry_line)
    atomic_write_text(spec_path, updated, encoding="utf-8")
    return True


def _has_dated_feature_history(lines: list[str]) -> bool:
    in_history = False
    for line in lines:
        stripped = line.strip()
        if stripped == "## Feature History":
            in_history = True
            continue
        if in_history and stripped.startswith("## "):
            return False
        if in_history and _FEATURE_HISTORY_RE.match(stripped):
            return True
    return False


def _insert_feature_history_entry(*, lines: list[str], entry_line: str) -> str:
    for index, line in enumerate(lines):
        if line.strip() != "## Feature History":
            continue
        insert_at = index + 1
        while insert_at < len(lines) and not lines[insert_at].strip():
            insert_at += 1
        updated = list(lines)
        if insert_at == index + 1:
            updated.insert(insert_at, "")
            insert_at += 1
        updated.insert(insert_at, entry_line)
        return "\n".join(updated).rstrip() + "\n"

    contract_index = _first_section_index(lines, "## Contract")
    insert_at = contract_index if contract_index is not None else len(lines)
    block = ["## Feature History", "", entry_line, ""]
    updated = list(lines)
    if insert_at > 0 and updated[insert_at - 1].strip():
        block.insert(0, "")
    updated[insert_at:insert_at] = block
    return "\n".join(updated).rstrip() + "\n"


def _first_section_index(lines: list[str], heading: str) -> int | None:
    for index, line in enumerate(lines):
        if line.strip() == heading:
            return index
    return None


def _normalized_token(value: Any) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
