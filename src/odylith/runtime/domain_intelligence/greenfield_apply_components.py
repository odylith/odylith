"""Authored Registry component previews for Greenfield prewrite gates."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from odylith.runtime.domain_intelligence import greenfield_authored_component_spec
from odylith.runtime.domain_intelligence.greenfield_authored_semantics import AUTHORED_PROJECTION_ORIGIN
from odylith.runtime.governance import artifact_tribunal


def render_prewrite_component_specs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
) -> dict[str, str]:
    """Render sealed authored Registry specs in memory before confirmation."""

    specs: dict[str, str] = {}
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
    ):
        if row.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
            raise ValueError("Greenfield Registry rendering requires an authored component projection")
        specs[str(row["label"])] = greenfield_authored_component_spec.build_authored_component_spec(row)
    return specs


def preview_prewrite_components(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Run component Tribunals over the sealed authored projection."""

    preview_rows: list[dict[str, Any]] = []
    for row in component_authoring_prewrite_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
    ):
        if row.get("projection_origin") != AUTHORED_PROJECTION_ORIGIN:
            raise ValueError("Greenfield Registry preview requires an authored component projection")
        preview_rows.append(_preview_authored_component(root=root, row=row))
    return tuple(preview_rows)


def component_authoring_prewrite_inputs(
    *,
    root: Path,
    proposal: Mapping[str, Any],
    release_selector: str,
    backlog_result: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    """Build Registry inputs only from the sealed authored projection."""

    if not greenfield_authored_component_spec.is_authored_component_projection(proposal):
        raise ValueError("Greenfield component authoring requires a sealed authored projection")
    return greenfield_authored_component_spec.build_authored_component_authoring_inputs(
        root=root,
        proposal=proposal,
        release_selector=release_selector,
        backlog_result=backlog_result,
    )


def _preview_authored_component(*, root: Path, row: Mapping[str, Any]) -> dict[str, Any]:
    component_id = str(row.get("component_id") or "").strip()
    registry_entry = greenfield_authored_component_spec.build_authored_component_registry_entry(row)
    source_custody = row.get("source_custody")
    if not isinstance(source_custody, Mapping):
        raise ValueError(f"authored component `{component_id}` is missing source custody")
    tribunal = artifact_tribunal.run_governed_artifact_tribunal(
        artifact_kind="component",
        payload={
            "component_id": component_id,
            "label": str(row.get("label") or ""),
            "path": str(row.get("path") or ""),
            "kind": str(row.get("kind") or ""),
            "responsibility": str(row.get("responsibility") or ""),
            "boundary": str(row.get("boundary") or ""),
            "interfaces": tuple(row.get("interfaces") or ()),
            "dependencies": tuple(row.get("dependencies") or ()),
            "validation": tuple(row.get("validation") or ()),
            "risks": tuple(row.get("risks") or ()),
            "component_contract": dict(row.get("component_contract") or {}),
        },
        source_custody=source_custody,
    )
    artifact_tribunal.raise_for_failed_artifact_tribunal(tribunal)
    spec_ref = str(registry_entry["spec_ref"])
    public_authoring_input = dict(row)
    public_authoring_input.pop("source_custody", None)
    return {
        "component_id": component_id,
        "label": str(row.get("label") or ""),
        "path": str(row.get("path") or ""),
        "registry_path": str((root / "odylith/registry/source/component_registry.v1.json").resolve()),
        "spec_path": str((root / spec_ref).resolve()),
        "validation_gate": tribunal.to_dict(),
        "implementation_handoff": dict(row.get("implementation_handoff") or {}),
        "authoring_input": public_authoring_input,
        "registry_entry": registry_entry,
        "what_it_is": str(registry_entry["what_it_is"]),
    }


def first_release_component_rows(proposal: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    """Return authored component rows that belong to the first release."""

    raw_rows = [row for row in proposal.get("components", []) if isinstance(row, Mapping)]
    return [row for row in raw_rows if is_first_release_component(row)]


def is_first_release_component(row: Mapping[str, Any]) -> bool:
    return str(row.get("release_scope", "")).strip().casefold() not in {
        "deferred",
        "out_of_scope",
        "external",
    }
