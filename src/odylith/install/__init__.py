from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORTS: dict[str, tuple[str, str]] = {
    "current_runtime_python": ("odylith.install.runtime", "current_runtime_python"),
    "consumer_profile_path": ("odylith.runtime.common.consumer_profile", "consumer_profile_path"),
    "doctor_bundle": ("odylith.install.manager", "doctor_bundle"),
    "doctor_runtime": ("odylith.install.runtime", "doctor_runtime"),
    "evaluate_start_preflight": ("odylith.install.manager", "evaluate_start_preflight"),
    "ensure_context_engine_pack": ("odylith.install.manager", "ensure_context_engine_pack"),
    "ensure_launcher": ("odylith.install.runtime", "ensure_launcher"),
    "ensure_source_runtime": ("odylith.install.manager", "ensure_source_runtime"),
    "ensure_wrapped_runtime": ("odylith.install.runtime", "ensure_wrapped_runtime"),
    "install_bundle": ("odylith.install.manager", "install_bundle"),
    "install_integration_enabled": ("odylith.install.manager", "install_integration_enabled"),
    "install_release_runtime": ("odylith.install.runtime", "install_release_runtime"),
    "load_consumer_profile": ("odylith.runtime.common.consumer_profile", "load_consumer_profile"),
    "load_install_state": ("odylith.install.manager", "load_install_state"),
    "migrate_legacy_install": ("odylith.install.manager", "migrate_legacy_install"),
    "plan_install_lifecycle": ("odylith.install.manager", "plan_install_lifecycle"),
    "plan_reinstall_lifecycle": ("odylith.install.manager", "plan_reinstall_lifecycle"),
    "plan_upgrade_lifecycle": ("odylith.install.manager", "plan_upgrade_lifecycle"),
    "preferred_repair_entrypoint": ("odylith.install.runtime", "preferred_repair_entrypoint"),
    "product_repo_role": ("odylith.install.manager", "product_repo_role"),
    "reinstall_install": ("odylith.install.manager", "reinstall_install"),
    "reset_local_state": ("odylith.install.repair", "reset_local_state"),
    "rollback_install": ("odylith.install.manager", "rollback_install"),
    "set_agents_integration": ("odylith.install.manager", "set_agents_integration"),
    "switch_runtime": ("odylith.install.runtime", "switch_runtime"),
    "uninstall_bundle": ("odylith.install.manager", "uninstall_bundle"),
    "upgrade_install": ("odylith.install.manager", "upgrade_install"),
    "version_status": ("odylith.install.manager", "version_status"),
    "write_consumer_profile": ("odylith.runtime.common.consumer_profile", "write_consumer_profile"),
}

__all__ = sorted(_EXPORTS)


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORTS[name]
    except KeyError as exc:  # pragma: no cover
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc
    value = getattr(import_module(module_name), attr_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
