from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class AgentHostAdapter:
    adapter_id: str
    host_family: str
    supports_native_spawn: bool
    supports_interrupt: bool
    supports_artifact_paths: bool

    def to_payload(self) -> dict[str, Any]:
        return asdict(self)
