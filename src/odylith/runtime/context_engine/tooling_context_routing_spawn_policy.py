"""Native-spawn policy field helpers for context routing handoffs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from odylith.runtime.common import host_runtime as host_runtime_contract


@dataclass(frozen=True)
class NativeSpawnPolicyFields:
    supported: bool = False
    transport_supported: bool = False
    policy: str = ""
    policy_status: str = ""
    effective: bool = False

    def policy_fields(self) -> dict[str, Any]:
        return {
            "native_spawn_transport_supported": self.transport_supported,
            "native_spawn_policy": self.policy,
            "native_spawn_policy_status": self.policy_status,
            "native_spawn_effective": self.effective,
        }

    def handoff_fields(self) -> dict[str, Any]:
        return {
            "native_spawn_supported": self.supported,
            **self.policy_fields(),
        }


def from_capabilities(capabilities: Mapping[str, Any]) -> NativeSpawnPolicyFields:
    supported = bool(capabilities.get("supports_native_spawn"))
    return NativeSpawnPolicyFields(
        supported=supported,
        transport_supported=bool(capabilities.get("native_spawn_transport_supported") or supported),
        policy=str(capabilities.get("native_spawn_policy", "")).strip(),
        policy_status=str(capabilities.get("native_spawn_policy_status", "")).strip(),
        effective=bool(capabilities.get("native_spawn_effective")),
    )


def probe(
    host_runtime_value: Any,
    *,
    enabled: bool,
) -> tuple[str, NativeSpawnPolicyFields]:
    """Resolve host runtime and native-spawn policy fields only when the route earned a probe."""
    if not enabled:
        return str(host_runtime_value or "").strip(), NativeSpawnPolicyFields()
    resolved_host_runtime = host_runtime_contract.resolve_host_runtime(host_runtime_value)
    return (
        resolved_host_runtime,
        from_capabilities(
            host_runtime_contract.host_capabilities(
                resolved_host_runtime,
                default_when_unknown=False,
            )
        ),
    )
