"""Odylith intervention engine package."""

from __future__ import annotations

from typing import Any

_EXPORTS: dict[str, tuple[str, str]] = {
    "apply_proposal_bundle": ("odylith.runtime.intervention_engine.apply", "apply_proposal_bundle"),
    "build_intervention_bundle": ("odylith.runtime.intervention_engine.engine", "build_intervention_bundle"),
    "compose_closeout_assist": ("odylith.runtime.intervention_engine.conversation_closeout", "compose_closeout_assist"),
    "compose_conversation_bundle": ("odylith.runtime.intervention_engine.conversation_runtime", "compose_conversation_bundle"),
    "compose_host_conversation_bundle": (
        "odylith.runtime.intervention_engine.host_surface_runtime",
        "compose_host_conversation_bundle",
    ),
}


def __getattr__(name: str) -> Any:
    """Keep package-level compatibility without importing the whole engine stack."""

    if name not in _EXPORTS:
        raise AttributeError(name)
    from importlib import import_module

    module_name, attr = _EXPORTS[name]
    value = getattr(import_module(module_name), attr)
    globals()[name] = value
    return value

__all__ = [
    "apply_proposal_bundle",
    "build_intervention_bundle",
    "compose_closeout_assist",
    "compose_conversation_bundle",
    "compose_host_conversation_bundle",
]
