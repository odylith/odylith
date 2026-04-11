from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentHostAdapter:
    adapter_id: str
    host_family: str
    model_family: str
    delegation_style: str
    supports_native_spawn: bool
    supports_interrupt: bool
    supports_artifact_paths: bool
    supports_local_structured_reasoning: bool
    supports_explicit_model_selection: bool

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
