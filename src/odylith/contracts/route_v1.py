"""Versioned route contract for host and runtime handoff."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class AgentRouteV1:
    route_id: str
    execution_mode: str
    ownership: list[str]
    validation_commands: list[str] = field(default_factory=list)
    closeout_surfaces: list[str] = field(default_factory=list)
    reasons_to_stay_local: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["schema"] = "agent_route.v1"
        return payload
