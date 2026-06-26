"""Accessors for typed greenfield post-confirm repair context payloads."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from odylith.runtime.domain_intelligence.greenfield_post_confirm_engine import (
    GreenfieldPostConfirmRepairContext,
)


def repair_context_target_layers(repair_context: GreenfieldPostConfirmRepairContext | None) -> set[str]:
    return {
        str(operation.get("target_layer", "")).strip()
        for operation in repair_context_operations(repair_context)
        if str(operation.get("target_layer", "")).strip()
    }


def repair_context_sources(repair_context: GreenfieldPostConfirmRepairContext | None) -> set[str]:
    return {
        str(operation.get("source_finding", "")).strip()
        for operation in repair_context_operations(repair_context)
        if str(operation.get("source_finding", "")).strip()
    }


def repair_context_operations(repair_context: GreenfieldPostConfirmRepairContext | None) -> list[Mapping[str, Any]]:
    if repair_context is None:
        return []
    patchset = repair_context.patchset_request
    if not isinstance(patchset, Mapping):
        return []
    operations = patchset.get("operations")
    if not isinstance(operations, list):
        return []
    return [operation for operation in operations if isinstance(operation, Mapping)]


__all__ = ["repair_context_operations", "repair_context_sources", "repair_context_target_layers"]
