"""Activity filters shared by component Registry intelligence paths."""

from __future__ import annotations

from pathlib import Path

_UNIT_RUNTIME_TEST_PREFIX = "tests/unit/runtime/"
_RETIRED_SURFACE_MARKER = "sentinel"
_ACTIVE_SURFACE_MODULE_STEMS: frozenset[str] = frozenset(
    {
        "compass_standup_brief_batch",
        "compass_standup_brief_maintenance",
        "compass_standup_brief_narrator",
        "compass_standup_brief_runtime_patch",
        "compass_standup_brief_substrate",
        "compass_standup_brief_voice_validation",
        "tooling_dashboard_cheatsheet_presenter",
        "tooling_dashboard_release_presenter",
        "tooling_dashboard_shell_presenter",
        "tooling_dashboard_welcome_presenter",
    }
)
_HOST_VISIBILITY_EVENT_KINDS: frozenset[str] = frozenset(
    {
        "ambient_signal",
        "assist_closeout",
        "capture_applied",
        "capture_declined",
        "capture_proposed",
        "intervention_card",
        "proposal",
    }
)


def is_host_visibility_event(kind: str) -> bool:
    return str(kind or "").strip().lower() in _HOST_VISIBILITY_EVENT_KINDS


def is_retired_surface_module_path(path: str) -> bool:
    stem = _surface_module_stem_from_activity_path(path)
    if not stem:
        return False
    governed_family = stem.startswith("compass_standup_brief_")
    shell_presenter_family = stem.startswith("tooling_dashboard_") and stem.endswith("_presenter")
    if not governed_family and not shell_presenter_family:
        return False
    return stem not in _ACTIVE_SURFACE_MODULE_STEMS


def hides_retired_surface_marker(path: str) -> bool:
    return _RETIRED_SURFACE_MARKER in str(path or "").lower()


def _surface_module_stem_from_activity_path(path: str) -> str:
    token = str(path or "").strip().replace("\\", "/").lower()
    if token.startswith("src/odylith/runtime/surfaces/") and token.endswith(".py"):
        return Path(token).stem
    if token.startswith(_UNIT_RUNTIME_TEST_PREFIX) and token.endswith(".py"):
        stem = Path(token).stem
        if stem.startswith("test_"):
            return stem.removeprefix("test_")
    return ""
